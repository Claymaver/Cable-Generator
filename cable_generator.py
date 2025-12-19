bl_info = {
    "name": "Cable Generator",
    "author": "Clay MacDonald",
    "version": (1, 1, 0),
    "blender": (3, 0, 0),
    "location": "View3D > Sidebar > Cable Gen",
    "description": "Generate cables between selected faces or objects with customizable thickness, sag, end caps, and array modifiers",
    "category": "Object",
    "doc_url": "",
    "tracker_url": "",
    "support": "COMMUNITY",
}

import bpy
import bmesh
from math import radians
from mathutils import Vector, Matrix
from bpy.props import FloatProperty, IntProperty, EnumProperty, PointerProperty, BoolProperty
from bpy.types import Operator, Panel, PropertyGroup, AddonPreferences
from bpy.app.handlers import persistent


def get_face_center_and_normal(obj, face):
    """Get world space center and normal of a face"""
    matrix = obj.matrix_world
    center = matrix @ face.calc_center_median()
    normal = (matrix.to_3x3() @ face.normal).normalized()
    return center, normal


def get_selected_faces(context):
    """Get all selected faces from selected objects in edit mode"""
    faces_data = []
    
    for obj in context.selected_objects:
        if obj.type == 'MESH' and obj.mode == 'EDIT':
            bm = bmesh.from_edit_mesh(obj.data)
            for face in bm.faces:
                if face.select:
                    center, normal = get_face_center_and_normal(obj, face)
                    faces_data.append({
                        'object': obj,
                        'center': center,
                        'normal': normal
                    })
    
    return faces_data


def get_object_centers(context):
    """Get centers of selected objects"""
    centers_data = []
    
    for obj in context.selected_objects:
        if obj.type == 'MESH':
            center = obj.matrix_world.translation
            # Use Z-up as default normal for objects
            normal = Vector((0, 0, 1))
            centers_data.append({
                'object': obj,
                'center': center,
                'normal': normal
            })
    
    return centers_data


def apply_smooth_shading(obj, angle=35):
    """Apply smooth shading to object"""
    if obj and obj.type == 'MESH':
        # Set smooth shading on all faces
        for poly in obj.data.polygons:
            poly.use_smooth = True
        
        # Try to apply auto smooth with operator if context allows
        try:
            # Check if we're in the right context
            if bpy.context.mode == 'OBJECT':
                # Store original selection
                original_active = bpy.context.view_layer.objects.active
                original_selection = [o for o in bpy.context.selected_objects]
                
                # Select only this object
                bpy.ops.object.select_all(action='DESELECT')
                obj.select_set(True)
                bpy.context.view_layer.objects.active = obj
                
                # Apply auto smooth with angle (convert degrees to radians)
                angle_radians = radians(angle)
                bpy.ops.object.shade_auto_smooth(angle=angle_radians)
                
                # Restore original selection
                bpy.ops.object.select_all(action='DESELECT')
                for o in original_selection:
                    if o and o.name in bpy.data.objects:
                        o.select_set(True)
                if original_active and original_active.name in bpy.data.objects:
                    bpy.context.view_layer.objects.active = original_active
        except Exception as e:
            # Fallback: just smooth shading is fine
            pass


def create_end_cap(context, position, normal, cap_type, custom_mesh, scale, name="Cap"):
    """Create an end cap at the specified position"""
    cap_obj = None
    
    if cap_type == 'CUSTOM' and custom_mesh:
        # Duplicate custom mesh
        cap_obj = custom_mesh.copy()
        cap_obj.data = custom_mesh.data.copy()
        cap_obj.name = name
        context.collection.objects.link(cap_obj)
    elif cap_type == 'CYLINDER':
        # Create cylinder mesh data
        mesh = bpy.data.meshes.new(name + "_mesh")
        bm = bmesh.new()
        bmesh.ops.create_cone(
            bm,
            cap_ends=True,
            cap_tris=False,
            segments=16,
            radius1=0.02,
            radius2=0.02,
            depth=0.05
        )
        bm.to_mesh(mesh)
        bm.free()
        cap_obj = bpy.data.objects.new(name, mesh)
        context.collection.objects.link(cap_obj)
    elif cap_type == 'SPHERE':
        # Create sphere mesh data
        mesh = bpy.data.meshes.new(name + "_mesh")
        bm = bmesh.new()
        bmesh.ops.create_uvsphere(
            bm,
            u_segments=16,
            v_segments=8,
            radius=0.03
        )
        bm.to_mesh(mesh)
        bm.free()
        cap_obj = bpy.data.objects.new(name, mesh)
        context.collection.objects.link(cap_obj)
    else:
        return None
    
    # Get smooth angle from preferences
    try:
        prefs = context.preferences.addons[__name__].preferences
        smooth_angle = prefs.auto_smooth_angle
    except:
        smooth_angle = 35.0
    
    # Apply smooth shading
    apply_smooth_shading(cap_obj, angle=smooth_angle)
    
    # Position and orient the cap
    cap_obj.location = position
    
    # Align to normal
    z_axis = normal.normalized()
    x_axis = Vector((1, 0, 0))
    if abs(z_axis.dot(x_axis)) > 0.9:
        x_axis = Vector((0, 1, 0))
    y_axis = z_axis.cross(x_axis).normalized()
    x_axis = y_axis.cross(z_axis).normalized()
    
    rot_matrix = Matrix((x_axis, y_axis, z_axis)).transposed().to_4x4()
    cap_obj.matrix_world = Matrix.Translation(position) @ rot_matrix
    
    # Scale
    cap_obj.scale = (scale, scale, scale)
    
    # Mark as end cap
    cap_obj["is_end_cap"] = 1
    
    return cap_obj


def update_end_cap_orientations(curve_obj):
    """Update end cap orientations to match curve tangents"""
    if len(curve_obj.data.splines) == 0:
        return
    
    spline = curve_obj.data.splines[0]
    if len(spline.bezier_points) < 2:
        return
    
    # Get children that are end caps
    for child in curve_obj.children:
        if child.name.startswith("Cap_Start"):
            # Calculate tangent at start
            start_point = spline.bezier_points[0]
            tangent = (start_point.handle_right - start_point.co).normalized()
            
            # Create rotation matrix from tangent
            z_axis = tangent
            x_axis = Vector((1, 0, 0))
            if abs(z_axis.dot(x_axis)) > 0.9:
                x_axis = Vector((0, 1, 0))
            y_axis = z_axis.cross(x_axis).normalized()
            x_axis = y_axis.cross(z_axis).normalized()
            
            rot_matrix = Matrix((x_axis, y_axis, z_axis)).transposed().to_4x4()
            
            # Update cap orientation (keep position and scale)
            position = child.location.copy()
            scale = child.scale.copy()
            child.matrix_world = Matrix.Translation(position) @ rot_matrix
            child.scale = scale
            
        elif child.name.startswith("Cap_End"):
            # Calculate tangent at end
            end_point = spline.bezier_points[1]
            tangent = (end_point.co - end_point.handle_left).normalized()
            
            # Create rotation matrix from tangent
            z_axis = tangent
            x_axis = Vector((1, 0, 0))
            if abs(z_axis.dot(x_axis)) > 0.9:
                x_axis = Vector((0, 1, 0))
            y_axis = z_axis.cross(x_axis).normalized()
            x_axis = y_axis.cross(z_axis).normalized()
            
            rot_matrix = Matrix((x_axis, y_axis, z_axis)).transposed().to_4x4()
            
            # Update cap orientation (keep position and scale)
            position = child.location.copy()
            scale = child.scale.copy()
            child.matrix_world = Matrix.Translation(position) @ rot_matrix
            child.scale = scale


def update_cable_handles(curve_obj):
    """Update cable curve handles based on stored properties"""
    if "start_pos" not in curve_obj or len(curve_obj.data.splines) == 0:
        return
    
    spline = curve_obj.data.splines[0]
    if len(spline.bezier_points) < 2:
        return
    
    start_pos = Vector(curve_obj["start_pos"])
    end_pos = Vector(curve_obj["end_pos"])
    start_normal = Vector(curve_obj["start_normal"]).normalized()
    end_normal = Vector(curve_obj["end_normal"]).normalized()
    
    # Ensure we have valid normals
    if start_normal.length < 0.001:
        start_normal = Vector((0, 0, 1))
    if end_normal.length < 0.001:
        end_normal = Vector((0, 0, 1))
    
    distance = (end_pos - start_pos).length
    handle_length = distance * 0.4
    sag = curve_obj.get("cable_sag", 0.0)
    
    # Calculate direction from start to end
    direction = (end_pos - start_pos).normalized()
    
    # Calculate how much the normals align with the connection direction
    start_alignment = start_normal.dot(direction)
    end_alignment = end_normal.dot(-direction)
    
    # Use original normals as base - they point "out" from the surface
    start_handle_dir = start_normal.copy()
    end_handle_dir = end_normal.copy()
    
    # Only flip if the normal is strongly pointing AWAY from target (< -0.3 means pointing away)
    if start_alignment < -0.3:
        start_handle_dir = -start_handle_dir
    
    if end_alignment < -0.3:
        end_handle_dir = -end_handle_dir
    
    # Calculate sag vector (downward)
    sag_vector = Vector((0, 0, -1)) * distance * sag
    
    # Update handle positions for start point
    spline.bezier_points[0].handle_left = start_pos - start_handle_dir * (handle_length * 0.3)
    spline.bezier_points[0].handle_right = start_pos + start_handle_dir * handle_length + sag_vector * 0.5
    
    # Update handle positions for end point
    spline.bezier_points[1].handle_left = end_pos + end_handle_dir * handle_length + sag_vector * 0.5
    spline.bezier_points[1].handle_right = end_pos - end_handle_dir * (handle_length * 0.3)
    
    # Update end cap orientations to match new curve tangents
    update_end_cap_orientations(curve_obj)


def create_curve_between_points(context, start_pos, start_normal, end_pos, end_normal, name="Cable"):
    """Create a bezier curve between two points with normals"""
    # Ensure normals are normalized
    start_normal = start_normal.normalized()
    end_normal = end_normal.normalized()
    
    # Ensure we have valid normals
    if start_normal.length < 0.001:
        start_normal = Vector((0, 0, 1))
    if end_normal.length < 0.001:
        end_normal = Vector((0, 0, 1))
    
    # Create curve data
    curve_data = bpy.data.curves.new(name=name, type='CURVE')
    curve_data.dimensions = '3D'
    curve_data.fill_mode = 'FULL'
    curve_data.bevel_depth = 0.05
    
    # Create spline
    spline = curve_data.splines.new(type='BEZIER')
    spline.bezier_points.add(1)  # Add one more point (total 2)
    
    # Set start point
    spline.bezier_points[0].co = start_pos
    spline.bezier_points[0].handle_right_type = 'FREE'
    spline.bezier_points[0].handle_left_type = 'FREE'
    
    # Set end point
    spline.bezier_points[1].co = end_pos
    spline.bezier_points[1].handle_right_type = 'FREE'
    spline.bezier_points[1].handle_left_type = 'FREE'
    
    # Create object
    curve_obj = bpy.data.objects.new(name, curve_data)
    context.collection.objects.link(curve_obj)
    
    # Store original data for updates
    curve_obj["is_cable"] = 1
    curve_obj["cable_thickness"] = 0.05
    curve_obj["cable_resolution"] = 12
    curve_obj["cable_sag"] = 0.0
    curve_obj["start_pos"] = start_pos[:]
    curve_obj["end_pos"] = end_pos[:]
    curve_obj["start_normal"] = start_normal[:]
    curve_obj["end_normal"] = end_normal[:]
    curve_obj["has_end_caps"] = 0
    curve_obj["end_cap_scale"] = 1.0
    
    # Set up property UI with proper ranges
    ui = curve_obj.id_properties_ui("is_cable")
    ui.update(description="This object is a generated cable")
    
    ui = curve_obj.id_properties_ui("cable_thickness")
    ui.update(min=0.001, max=1.0, soft_min=0.01, soft_max=0.5, description="Cable thickness")
    
    ui = curve_obj.id_properties_ui("cable_resolution")
    ui.update(min=1, max=64, description="Curve resolution")
    
    ui = curve_obj.id_properties_ui("cable_sag")
    ui.update(min=0.0, max=1.0, soft_max=0.5, description="Cable sag amount")
    
    ui = curve_obj.id_properties_ui("end_cap_scale")
    ui.update(min=0.01, max=10.0, soft_min=0.1, soft_max=5.0, description="End cap scale multiplier")
    
    # Initial handle setup
    update_cable_handles(curve_obj)
    
    # Set up driver for thickness
    setup_cable_drivers(curve_obj)
    
    return curve_obj


def setup_cable_drivers(curve_obj):
    """Setup drivers to update curve properties"""
    curve_data = curve_obj.data
    
    # Driver for bevel_depth (thickness)
    driver = curve_data.driver_add("bevel_depth").driver
    driver.type = 'SCRIPTED'
    var = driver.variables.new()
    var.name = "thickness"
    var.targets[0].id_type = 'OBJECT'
    var.targets[0].id = curve_obj
    var.targets[0].data_path = '["cable_thickness"]'
    driver.expression = "thickness"


@persistent
def cable_update_handler(scene):
    """Handler to update cable properties on scene changes"""
    for obj in scene.objects:
        # Update cable curves
        if obj.type == 'CURVE' and "is_cable" in obj.keys():
            # Update resolution
            if "cable_resolution" in obj.keys():
                res = int(obj["cable_resolution"])
                if obj.data.resolution_u != res:
                    obj.data.resolution_u = res
            
            # Update sag (handles)
            if "cable_sag" in obj.keys():
                update_cable_handles(obj)
            
            # Update end cap scales based on cable thickness
            if "cable_thickness" in obj.keys() and "end_cap_scale" in obj.keys():
                thickness = obj["cable_thickness"]
                cap_scale_mult = obj["end_cap_scale"]
                base_scale = thickness * 20.0 * cap_scale_mult
                
                for child in obj.children:
                    if child.get("is_end_cap"):
                        target_scale = Vector((base_scale, base_scale, base_scale))
                        if (child.scale - target_scale).length > 0.001:
                            child.scale = target_scale
        
        # Update array objects
        elif obj.type == 'MESH' and "has_array" in obj.keys():
            if "array_scale" in obj.keys():
                scale = obj["array_scale"]
                current_scale = Vector((scale, scale, scale))
                if (obj.scale - current_scale).length > 0.001:
                    obj.scale = current_scale
            
            # Update array count and fit mode
            for mod in obj.modifiers:
                if mod.type == 'ARRAY':
                    if "array_fit_curve" in obj.keys():
                        fit_curve = int(obj["array_fit_curve"])
                        if fit_curve:
                            if mod.fit_type != 'FIT_CURVE':
                                mod.fit_type = 'FIT_CURVE'
                        else:
                            if mod.fit_type != 'FIXED_COUNT':
                                mod.fit_type = 'FIXED_COUNT'
                            if "array_count" in obj.keys():
                                count = int(obj["array_count"])
                                if mod.count != count:
                                    mod.count = count
                    break


class CABLEGEN_OT_GenerateCable(Operator):
    """Generate cables between selected faces or objects"""
    bl_idname = "object.generate_cable"
    bl_label = "Generate Cable"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        props = context.scene.cable_gen_props
        selected_objects = context.selected_objects
        
        if not selected_objects:
            self.report({'WARNING'}, "No objects selected")
            return {'CANCELLED'}
        
        edit_mode_objects = [obj for obj in selected_objects if obj.type == 'MESH' and obj.mode == 'EDIT']
        created_cables = []
        
        if edit_mode_objects:
            faces_data = get_selected_faces(context)
            
            if len(faces_data) < 2:
                self.report({'WARNING'}, "Select at least 2 faces")
                return {'CANCELLED'}
            
            for i in range(len(faces_data) - 1):
                face1 = faces_data[i]
                face2 = faces_data[i + 1]
                
                curve_obj = create_curve_between_points(
                    context,
                    face1['center'],
                    face1['normal'],
                    face2['center'],
                    face2['normal'],
                    f"Cable_{i+1}"
                )
                
                curve_obj["cable_thickness"] = props.thickness
                curve_obj["cable_resolution"] = props.resolution
                curve_obj.data.resolution_u = props.resolution
                
                created_cables.append(curve_obj)
                
                if props.add_end_caps:
                    start_cap = create_end_cap(
                        context, face1['center'], face1['normal'],
                        props.end_cap_type, props.end_cap_mesh,
                        props.thickness * 20.0, f"Cap_Start_{i+1}"
                    )
                    if start_cap:
                        start_cap.parent = curve_obj
                        curve_obj["has_end_caps"] = 1
                    
                    end_cap = create_end_cap(
                        context, face2['center'], face2['normal'],
                        props.end_cap_type, props.end_cap_mesh,
                        props.thickness * 20.0, f"Cap_End_{i+1}"
                    )
                    if end_cap:
                        end_cap.parent = curve_obj
                
        else:
            centers_data = get_object_centers(context)
            
            if len(centers_data) < 2:
                self.report({'WARNING'}, "Select at least 2 objects")
                return {'CANCELLED'}
            
            if props.connection_mode == 'SEQUENTIAL':
                for i in range(len(centers_data) - 1):
                    obj1 = centers_data[i]
                    obj2 = centers_data[i + 1]
                    
                    curve_obj = create_curve_between_points(
                        context,
                        obj1['center'],
                        obj1['normal'],
                        obj2['center'],
                        obj2['normal'],
                        f"Cable_{i+1}"
                    )
                    
                    curve_obj["cable_thickness"] = props.thickness
                    curve_obj["cable_resolution"] = props.resolution
                    curve_obj.data.resolution_u = props.resolution
                    
                    created_cables.append(curve_obj)
                    
                    if props.add_end_caps:
                        start_cap = create_end_cap(
                            context, obj1['center'], obj1['normal'],
                            props.end_cap_type, props.end_cap_mesh,
                            props.thickness * 20.0, f"Cap_Start_{i+1}"
                        )
                        if start_cap:
                            start_cap.parent = curve_obj
                            curve_obj["has_end_caps"] = 1
                        
                        end_cap = create_end_cap(
                            context, obj2['center'], obj2['normal'],
                            props.end_cap_type, props.end_cap_mesh,
                            props.thickness * 20.0, f"Cap_End_{i+1}"
                        )
                        if end_cap:
                            end_cap.parent = curve_obj
                    
            elif props.connection_mode == 'ALL_TO_FIRST':
                first = centers_data[0]
                for i in range(1, len(centers_data)):
                    obj = centers_data[i]
                    
                    curve_obj = create_curve_between_points(
                        context,
                        first['center'],
                        first['normal'],
                        obj['center'],
                        obj['normal'],
                        f"Cable_to_{obj['object'].name}"
                    )
                    
                    curve_obj["cable_thickness"] = props.thickness
                    curve_obj["cable_resolution"] = props.resolution
                    curve_obj.data.resolution_u = props.resolution
                    
                    created_cables.append(curve_obj)
                    
                    if props.add_end_caps:
                        start_cap = create_end_cap(
                            context, first['center'], first['normal'],
                            props.end_cap_type, props.end_cap_mesh,
                            props.thickness * 20.0, f"Cap_Start_to_{obj['object'].name}"
                        )
                        if start_cap:
                            start_cap.parent = curve_obj
                            curve_obj["has_end_caps"] = 1
                        
                        end_cap = create_end_cap(
                            context, obj['center'], obj['normal'],
                            props.end_cap_type, props.end_cap_mesh,
                            props.thickness * 20.0, f"Cap_End_to_{obj['object'].name}"
                        )
                        if end_cap:
                            end_cap.parent = curve_obj
        
        if len(created_cables) > 1 and props.organize_collections:
            cable_collection = bpy.data.collections.get("Cables")
            if not cable_collection:
                cable_collection = bpy.data.collections.new("Cables")
                context.scene.collection.children.link(cable_collection)
            
            for cable in created_cables:
                for coll in cable.users_collection:
                    coll.objects.unlink(cable)
                cable_collection.objects.link(cable)
        
        self.report({'INFO'}, f"{len(created_cables)} cable(s) generated successfully")
        return {'FINISHED'}


class CABLEGEN_OT_ToggleEndCaps(Operator):
    """Toggle end caps on selected cable"""
    bl_idname = "object.cable_toggle_caps"
    bl_label = "Toggle End Caps"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        props = context.scene.cable_gen_props
        cable = context.active_object
        
        if not cable or cable.type != 'CURVE' or "is_cable" not in cable.keys():
            self.report({'WARNING'}, "Select a cable")
            return {'CANCELLED'}
        
        has_caps = cable.get("has_end_caps", 0)
        
        if has_caps:
            caps_removed = 0
            for child in list(cable.children):
                if child.get("is_end_cap"):
                    bpy.data.objects.remove(child, do_unlink=True)
                    caps_removed += 1
            cable["has_end_caps"] = 0
            self.report({'INFO'}, f"Removed {caps_removed} end caps")
        else:
            if "start_pos" not in cable.keys() or "end_pos" not in cable.keys():
                self.report({'WARNING'}, "Cable missing position data")
                return {'CANCELLED'}
            
            start_pos = Vector(cable["start_pos"])
            end_pos = Vector(cable["end_pos"])
            start_normal = Vector(cable["start_normal"])
            end_normal = Vector(cable["end_normal"])
            thickness = cable.get("cable_thickness", 0.05)
            cap_scale = cable.get("end_cap_scale", 1.0)
            
            try:
                start_cap = create_end_cap(
                    context, start_pos, start_normal,
                    props.end_cap_type, props.end_cap_mesh,
                    thickness * 20.0 * cap_scale, f"Cap_Start_{cable.name}"
                )
                if start_cap:
                    start_cap.parent = cable
                
                end_cap = create_end_cap(
                    context, end_pos, end_normal,
                    props.end_cap_type, props.end_cap_mesh,
                    thickness * 20.0 * cap_scale, f"Cap_End_{cable.name}"
                )
                if end_cap:
                    end_cap.parent = cable
                
                cable["has_end_caps"] = 1
                update_end_cap_orientations(cable)
                self.report({'INFO'}, "End caps added")
            except Exception as e:
                self.report({'ERROR'}, f"Failed to create end caps: {str(e)}")
                return {'CANCELLED'}
        
        return {'FINISHED'}


class CABLEGEN_OT_ApplyArrayMesh(Operator):
    """Apply array mesh to selected curves"""
    bl_idname = "object.cable_apply_array"
    bl_label = "Apply Array Mesh"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        props = context.scene.cable_gen_props
        
        if not props.array_mesh:
            self.report({'WARNING'}, "Select an array mesh first")
            return {'CANCELLED'}
        
        curves = [obj for obj in context.selected_objects if obj.type == 'CURVE']
        
        if not curves:
            self.report({'WARNING'}, "Select at least one curve")
            return {'CANCELLED'}
        
        for curve in curves:
            array_obj = props.array_mesh.copy()
            array_obj.data = props.array_mesh.data.copy()
            context.collection.objects.link(array_obj)
            array_obj.name = f"Array_{curve.name}"
            
            array_obj.modifiers.clear()
            
            array_mod = array_obj.modifiers.new(name="Array", type='ARRAY')
            array_mod.fit_type = 'FIT_CURVE'
            array_mod.curve = curve
            array_mod.use_merge_vertices = True
            array_mod.merge_threshold = 0.01
            array_mod.relative_offset_displace[0] = 0.0
            array_mod.relative_offset_displace[1] = 0.0
            array_mod.relative_offset_displace[2] = 1.0
            array_mod.count = 10
            
            curve_mod = array_obj.modifiers.new(name="Curve", type='CURVE')
            curve_mod.object = curve
            curve_mod.deform_axis = 'POS_Z'
            
            array_obj.location = curve.location
            array_obj.scale = (props.array_scale, props.array_scale, props.array_scale)
            array_obj.parent = curve
            array_obj.matrix_parent_inverse = Matrix.Identity(4)
            
            array_obj["has_array"] = 1
            array_obj["array_scale"] = props.array_scale
            array_obj["array_count"] = 10
            array_obj["array_fit_curve"] = 1
            
            ui = array_obj.id_properties_ui("has_array")
            ui.update(description="This object has array modifiers")
            
            ui = array_obj.id_properties_ui("array_scale")
            ui.update(min=0.001, max=100.0, soft_min=0.1, soft_max=10.0, description="Scale of array mesh")
            
            ui = array_obj.id_properties_ui("array_count")
            ui.update(min=1, max=1000, soft_min=5, soft_max=100, description="Number of array instances")
            
            ui = array_obj.id_properties_ui("array_fit_curve")
            ui.update(description="Fit to curve length (1) or use fixed count (0)")
            
        self.report({'INFO'}, f"Array applied to {len(curves)} curve(s)")
        return {'FINISHED'}


class CABLEGEN_OT_SetArrayFitCurve(Operator):
    """Set array to fit curve mode"""
    bl_idname = "object.array_fit_curve"
    bl_label = "Fit to Curve"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        obj = context.active_object
        if obj and "array_fit_curve" in obj.keys():
            obj["array_fit_curve"] = 1
        return {'FINISHED'}


class CABLEGEN_OT_SetArrayFixedCount(Operator):
    """Set array to fixed count mode"""
    bl_idname = "object.array_fixed_count"
    bl_label = "Fixed Count"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        obj = context.active_object
        if obj and "array_fit_curve" in obj.keys():
            obj["array_fit_curve"] = 0
        return {'FINISHED'}


class CABLEGEN_OT_ConvertToMesh(Operator):
    """Convert selected cables to mesh"""
    bl_idname = "object.cable_convert_mesh"
    bl_label = "Convert to Mesh"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        cables = [obj for obj in context.selected_objects if obj.type == 'CURVE' and obj.get("is_cable")]
        
        if not cables:
            self.report({'WARNING'}, "Select at least one cable")
            return {'CANCELLED'}
        
        converted = 0
        for cable in cables:
            mesh = cable.to_mesh()
            mesh_obj = bpy.data.objects.new(cable.name + "_mesh", mesh)
            mesh_obj.matrix_world = cable.matrix_world
            context.collection.objects.link(mesh_obj)
            converted += 1
        
        self.report({'INFO'}, f"Converted {converted} cable(s) to mesh")
        return {'FINISHED'}


class CABLEGEN_OT_ApplyPreset(Operator):
    """Apply cable preset"""
    bl_idname = "object.cable_apply_preset"
    bl_label = "Apply Preset"
    bl_options = {'REGISTER', 'UNDO'}
    
    preset_type: EnumProperty(
        name="Preset",
        items=[
            ('THIN', "Thin", "Thin data cable (0.01)"),
            ('MEDIUM', "Medium", "Standard cable (0.05)"),
            ('THICK', "Thick", "Heavy cable (0.1)"),
            ('POWER', "Power", "Power cord (0.08)"),
        ]
    )
    
    def execute(self, context):
        props = context.scene.cable_gen_props
        
        if self.preset_type == 'THIN':
            props.thickness = 0.01
            props.resolution = 8
        elif self.preset_type == 'MEDIUM':
            props.thickness = 0.05
            props.resolution = 12
        elif self.preset_type == 'THICK':
            props.thickness = 0.1
            props.resolution = 16
        elif self.preset_type == 'POWER':
            props.thickness = 0.08
            props.resolution = 12
        
        self.report({'INFO'}, f"Applied {self.preset_type} preset")
        return {'FINISHED'}


class CABLEGEN_OT_SelectAllCables(Operator):
    """Select all cables in the scene"""
    bl_idname = "object.cable_select_all"
    bl_label = "Select All Cables"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        bpy.ops.object.select_all(action='DESELECT')
        
        count = 0
        for obj in context.scene.objects:
            if obj.type == 'CURVE' and obj.get("is_cable"):
                obj.select_set(True)
                count += 1
        
        if count > 0:
            context.view_layer.objects.active = context.selected_objects[0]
        
        self.report({'INFO'}, f"Selected {count} cable(s)")
        return {'FINISHED'}


class CABLEGEN_OT_ReverseCable(Operator):
    """Reverse cable direction"""
    bl_idname = "object.cable_reverse"
    bl_label = "Reverse Direction"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        cable = context.active_object
        
        if not cable or cable.type != 'CURVE' or "is_cable" not in cable.keys():
            self.report({'WARNING'}, "Select a cable")
            return {'CANCELLED'}
        
        if "start_pos" in cable.keys() and "end_pos" in cable.keys():
            start_pos = cable["start_pos"][:]
            end_pos = cable["end_pos"][:]
            start_normal = cable["start_normal"][:]
            end_normal = cable["end_normal"][:]
            
            cable["start_pos"] = end_pos
            cable["end_pos"] = start_pos
            cable["start_normal"] = end_normal
            cable["end_normal"] = start_normal
            
            update_cable_handles(cable)
            
            start_caps = []
            end_caps = []
            
            for child in cable.children:
                if child.name.startswith("Cap_Start"):
                    start_caps.append(child)
                elif child.name.startswith("Cap_End"):
                    end_caps.append(child)
            
            for cap in start_caps:
                cap.name = cap.name.replace("Cap_Start", "Cap_End_temp")
            for cap in end_caps:
                cap.name = cap.name.replace("Cap_End", "Cap_Start")
            for cap in start_caps:
                cap.name = cap.name.replace("Cap_End_temp", "Cap_End")
            
            update_end_cap_orientations(cable)
            
            self.report({'INFO'}, "Cable direction reversed")
        else:
            self.report({'WARNING'}, "Cable missing position data")
            return {'CANCELLED'}
        
        return {'FINISHED'}


class CABLEGEN_PT_MainPanel(Panel):
    """Cable Generator Panel"""
    bl_label = "Cable Generator"
    bl_idname = "CABLEGEN_PT_main_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Cable Gen'
    
    def draw(self, context):
        layout = self.layout
        layout.label(text="Select faces or objects", icon='INFO')


class CABLEGEN_PT_CreateCablePanel(Panel):
    """Create Cable Sub-Panel"""
    bl_label = "Create New Cable"
    bl_idname = "CABLEGEN_PT_create_cable_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Cable Gen'
    bl_parent_id = "CABLEGEN_PT_main_panel"
    bl_options = {'DEFAULT_CLOSED'}
    
    def draw(self, context):
        layout = self.layout
        props = context.scene.cable_gen_props
        
        layout.prop(props, "thickness")
        layout.prop(props, "resolution")
        layout.prop(props, "connection_mode")
        
        layout.separator()
        layout.operator("object.generate_cable", icon='CURVE_DATA', text="Generate Cable")


class CABLEGEN_PT_PresetsPanel(Panel):
    """Presets Sub-Panel"""
    bl_label = "Presets"
    bl_idname = "CABLEGEN_PT_presets_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Cable Gen'
    bl_parent_id = "CABLEGEN_PT_main_panel"
    bl_options = {'DEFAULT_CLOSED'}
    
    def draw(self, context):
        layout = self.layout
        
        layout.label(text="Quick Apply:", icon='PRESET')
        
        row = layout.row(align=True)
        op = row.operator("object.cable_apply_preset", text="Thin")
        op.preset_type = 'THIN'
        op = row.operator("object.cable_apply_preset", text="Med")
        op.preset_type = 'MEDIUM'
        
        row = layout.row(align=True)
        op = row.operator("object.cable_apply_preset", text="Thick")
        op.preset_type = 'THICK'
        op = row.operator("object.cable_apply_preset", text="Power")
        op.preset_type = 'POWER'


class CABLEGEN_PT_EndCapsPanel(Panel):
    """End Caps Sub-Panel"""
    bl_label = "End Caps"
    bl_idname = "CABLEGEN_PT_endcaps_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Cable Gen'
    bl_parent_id = "CABLEGEN_PT_main_panel"
    bl_options = {'DEFAULT_CLOSED'}
    
    def draw_header(self, context):
        self.layout.prop(context.scene.cable_gen_props, "add_end_caps", text="")
    
    def draw(self, context):
        layout = self.layout
        props = context.scene.cable_gen_props
        
        layout.enabled = props.add_end_caps
        layout.prop(props, "end_cap_type", text="Type")
        if props.end_cap_type == 'CUSTOM':
            layout.prop(props, "end_cap_mesh", text="Mesh")


class CABLEGEN_PT_ArrayPanel(Panel):
    """Array Sub-Panel"""
    bl_label = "Array Mesh"
    bl_idname = "CABLEGEN_PT_array_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Cable Gen'
    bl_parent_id = "CABLEGEN_PT_main_panel"
    bl_options = {'DEFAULT_CLOSED'}
    
    def draw(self, context):
        layout = self.layout
        props = context.scene.cable_gen_props
        
        layout.prop(props, "array_mesh")
        layout.prop(props, "array_scale", text="Initial Scale")
        
        col = layout.column()
        col.scale_y = 0.7
        col.label(text="Tip: Z-axis = forward", icon='INFO')
        
        layout.operator("object.cable_apply_array", icon='LINKED')


class CABLEGEN_PT_EditCablePanel(Panel):
    """Edit Cable Sub-Panel"""
    bl_label = "Edit Selected Cable"
    bl_idname = "CABLEGEN_PT_edit_cable_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Cable Gen'
    bl_parent_id = "CABLEGEN_PT_main_panel"
    
    @classmethod
    def poll(cls, context):
        active = context.active_object
        return active and active.type == 'CURVE' and "is_cable" in active.keys()
    
    def draw(self, context):
        layout = self.layout
        active = context.active_object
        
        # Get preferences
        prefs = context.preferences.addons[__name__].preferences
        
        if prefs.show_cable_info:
            if "start_pos" in active.keys() and "end_pos" in active.keys():
                start = Vector(active["start_pos"])
                end = Vector(active["end_pos"])
                length = (end - start).length
                
                box = layout.box()
                col = box.column(align=True)
                col.scale_y = 0.8
                col.label(text=f"Length: {length:.3f}m", icon='DRIVER_DISTANCE')
                col.label(text=f"Thickness: {active.get('cable_thickness', 0.05):.3f}m")
        
        layout.separator()
        
        layout.prop(active, '["cable_thickness"]', text="Thickness")
        layout.prop(active, '["cable_resolution"]', text="Resolution")
        layout.prop(active, '["cable_sag"]', text="Sag")
        
        layout.separator()
        
        has_caps = active.get("has_end_caps", 0)
        row = layout.row()
        row.operator("object.cable_toggle_caps", 
                     text="Remove Caps" if has_caps else "Add Caps",
                     icon='X' if has_caps else 'ADD')
        
        if has_caps:
            layout.prop(active, '["end_cap_scale"]', text="Cap Scale")
        
        layout.separator()
        layout.label(text="Tools:", icon='TOOL_SETTINGS')
        layout.operator("object.cable_reverse", icon='FILE_REFRESH')


class CABLEGEN_PT_EditArrayPanel(Panel):
    """Edit Array Sub-Panel"""
    bl_label = "Edit Selected Array"
    bl_idname = "CABLEGEN_PT_edit_array_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Cable Gen'
    bl_parent_id = "CABLEGEN_PT_main_panel"
    
    @classmethod
    def poll(cls, context):
        active = context.active_object
        return active and active.type == 'MESH' and "has_array" in active.keys()
    
    def draw(self, context):
        layout = self.layout
        active = context.active_object
        
        layout.prop(active, '["array_scale"]', text="Scale")
        
        layout.separator()
        layout.label(text="Array Mode:")
        
        fit_curve = active.get("array_fit_curve", 1)
        row = layout.row(align=True)
        row.scale_y = 1.2
        
        op = row.operator("object.array_fit_curve", depress=(fit_curve == 1))
        op = row.operator("object.array_fixed_count", depress=(fit_curve == 0))
        
        if not fit_curve:
            layout.prop(active, '["array_count"]', text="Count")
        
        array_mod = None
        for mod in active.modifiers:
            if mod.type == 'ARRAY':
                array_mod = mod
                break
        
        if array_mod:
            layout.separator()
            col = layout.column()
            col.label(text="Advanced:")
            col.prop(array_mod, "use_merge_vertices", text="Merge Vertices")
            if array_mod.use_merge_vertices:
                col.prop(array_mod, "merge_threshold", text="Distance")


class CABLEGEN_PT_UtilitiesPanel(Panel):
    """Utilities Sub-Panel"""
    bl_label = "Utilities"
    bl_idname = "CABLEGEN_PT_utilities_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Cable Gen'
    bl_parent_id = "CABLEGEN_PT_main_panel"
    bl_options = {'DEFAULT_CLOSED'}
    
    def draw(self, context):
        layout = self.layout
        props = context.scene.cable_gen_props
        
        layout.label(text="Organization:", icon='OUTLINER')
        layout.prop(props, "organize_collections", text="Use Collections")
        
        layout.separator()
        layout.label(text="Batch Operations:", icon='MOD_ARRAY')
        layout.operator("object.cable_select_all", icon='RESTRICT_SELECT_OFF')
        layout.operator("object.cable_convert_mesh", icon='MESH_DATA')


class CableGenProperties(PropertyGroup):
    thickness: FloatProperty(
        name="Thickness",
        description="Cable thickness",
        default=0.05,
        min=0.001,
        max=10.0,
        step=0.01
    )
    
    resolution: IntProperty(
        name="Resolution",
        description="Curve resolution",
        default=12,
        min=1,
        max=64
    )
    
    connection_mode: EnumProperty(
        name="Connection Mode",
        description="How to connect objects",
        items=[
            ('SEQUENTIAL', "Sequential", "Connect objects in selection order"),
            ('ALL_TO_FIRST', "All to First", "Connect all objects to the first selected"),
        ],
        default='SEQUENTIAL'
    )
    
    add_end_caps: BoolProperty(
        name="Add End Caps",
        description="Add caps/plugs to cable ends",
        default=False
    )
    
    end_cap_type: EnumProperty(
        name="Cap Type",
        description="Type of end cap to add",
        items=[
            ('CYLINDER', "Cylinder", "Simple cylinder plug"),
            ('SPHERE', "Sphere", "Rounded sphere cap"),
            ('CUSTOM', "Custom Mesh", "Use custom mesh object"),
        ],
        default='CYLINDER'
    )
    
    end_cap_mesh: PointerProperty(
        name="Custom Cap",
        description="Custom mesh for cable ends",
        type=bpy.types.Object,
        poll=lambda self, obj: obj.type == 'MESH'
    )
    
    organize_collections: BoolProperty(
        name="Organize in Collection",
        description="Put multiple cables in a 'Cables' collection",
        default=True
    )
    
    array_mesh: PointerProperty(
        name="Array Mesh",
        description="Mesh object to array along curve (should point along Z-axis)",
        type=bpy.types.Object,
        poll=lambda self, obj: obj.type == 'MESH'
    )
    
    array_scale: FloatProperty(
        name="Array Scale",
        description="Scale of arrayed mesh",
        default=1.0,
        min=0.001,
        max=100.0
    )


class CableGenPreferences(AddonPreferences):
    bl_idname = __name__
    
    default_thickness: FloatProperty(
        name="Default Thickness",
        description="Default cable thickness for new cables",
        default=0.05,
        min=0.001,
        max=1.0
    )
    
    default_resolution: IntProperty(
        name="Default Resolution",
        description="Default curve resolution for new cables",
        default=12,
        min=1,
        max=64
    )
    
    auto_smooth_angle: FloatProperty(
        name="Auto Smooth Angle",
        description="Angle for auto smooth shading on end caps (degrees)",
        default=35.0,
        min=0.0,
        max=180.0
    )
    
    show_cable_info: BoolProperty(
        name="Show Cable Info",
        description="Display cable length and thickness info when editing",
        default=True
    )
    
    def draw(self, context):
        layout = self.layout
        
        box = layout.box()
        box.label(text="Default Settings:", icon='SETTINGS')
        box.prop(self, "default_thickness")
        box.prop(self, "default_resolution")
        
        box = layout.box()
        box.label(text="Display Options:", icon='WINDOW')
        box.prop(self, "show_cable_info")
        
        box = layout.box()
        box.label(text="Mesh Options:", icon='MESH_DATA')
        box.prop(self, "auto_smooth_angle")
        
        layout.separator()
        
        box = layout.box()
        box.label(text="About:", icon='INFO')
        col = box.column(align=True)
        col.scale_y = 0.8
        col.label(text="Cable Generator v1.1")
        col.label(text="Author: Clay MacDonald")
        col.label(text="Generate cables between faces or objects")
        col.label(text="with customizable properties and end caps")


classes = (
    CableGenProperties,
    CableGenPreferences,
    CABLEGEN_OT_GenerateCable,
    CABLEGEN_OT_ToggleEndCaps,
    CABLEGEN_OT_ApplyArrayMesh,
    CABLEGEN_OT_SetArrayFitCurve,
    CABLEGEN_OT_SetArrayFixedCount,
    CABLEGEN_OT_ConvertToMesh,
    CABLEGEN_OT_ApplyPreset,
    CABLEGEN_OT_SelectAllCables,
    CABLEGEN_OT_ReverseCable,
    CABLEGEN_PT_MainPanel,
    CABLEGEN_PT_CreateCablePanel,
    CABLEGEN_PT_PresetsPanel,
    CABLEGEN_PT_EndCapsPanel,
    CABLEGEN_PT_ArrayPanel,
    CABLEGEN_PT_EditCablePanel,
    CABLEGEN_PT_EditArrayPanel,
    CABLEGEN_PT_UtilitiesPanel,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.Scene.cable_gen_props = PointerProperty(type=CableGenProperties)
    
    if cable_update_handler not in bpy.app.handlers.depsgraph_update_post:
        bpy.app.handlers.depsgraph_update_post.append(cable_update_handler)


def unregister():
    if cable_update_handler in bpy.app.handlers.depsgraph_update_post:
        bpy.app.handlers.depsgraph_update_post.remove(cable_update_handler)
    
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
    del bpy.types.Scene.cable_gen_props


if __name__ == "__main__":
    register()
