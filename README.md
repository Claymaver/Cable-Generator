# Cable Generator for Blender

![Blender](https://img.shields.io/badge/Blender-4.5%2B-orange?logo=blender)
![Version](https://img.shields.io/badge/version-1.1.0-blue)
![License](https://img.shields.io/badge/license-MIT-green)

A powerful Blender addon for generating realistic cables between selected faces or objects with full control over thickness, sag, end caps, and array modifiers.

##  Features

### Core Functionality
- **Smart Cable Generation** - Create cables between selected faces or objects
- **Face-to-Face Cables** - Select faces in Edit Mode for precise cable placement
- **Object-to-Object Cables** - Connect object centers in Object Mode
- **Sequential or Hub Connection** - Chain objects or connect all to first selected

### Cable Customization
- **Live Editable Properties** - Adjust thickness, resolution, and sag after creation
- **Cable Sag Control** - Add natural droop to cables with adjustable sag
- **Smooth Bezier Curves** - Intelligent handle placement for natural cable routing
- **Preset System** - Quick presets for Thin, Medium, Thick, and Power cables

### End Caps & Connectors
- **Toggle End Caps** - Add or remove caps after cable creation
- **Multiple Cap Types** - Cylinder plugs, sphere caps, or custom meshes
- **Auto-Scaling** - Caps automatically scale with cable thickness
- **Auto-Orient** - Caps follow curve tangents, even with sag adjustments
- **Smooth Shading** - Auto-smooth at 35° for professional appearance

### Array Modifiers
- **Array Along Curve** - Repeat meshes along cable paths
- **Fit to Curve or Fixed Count** - Auto-fit or specify exact count
- **Live Controls** - Adjust scale, count, and merge settings
- **Z-Axis Forward** - Standard orientation for easy mesh preparation

### Organization & Workflow
- **Auto Collections** - Group multiple cables in organized collections
- **Cable Info Display** - View length and thickness at a glance
- **Reverse Direction** - Flip cable start/end with one click
- **Select All Cables** - Quickly find all cables in scene
- **Convert to Mesh** - Finalize cables for export
- **Collapsible UI** - Clean, organized panel system

##  Installation

### Method 1: Download Release
1. Download the latest `cable_generator-v1.1.0.zip` from [Releases](../../releases)
2. Open Blender → Edit → Preferences → Add-ons
3. Click "Install..." and select the downloaded ZIP file
4. Enable "Cable Generator" in the add-ons list

### Method 2: Manual Installation
1. Download `cable_generator.py`
2. Copy to your Blender addons folder:
   - **Windows**: `%APPDATA%\Blender Foundation\Blender\[version]\scripts\addons\`
   - **macOS**: `~/Library/Application Support/Blender/[version]/scripts/addons/`
   - **Linux**: `~/.config/blender/[version]/scripts/addons/`
3. Restart Blender
4. Enable "Cable Generator" in Edit → Preferences → Add-ons

##  Quick Start

### Creating Your First Cable

**Face-to-Face Mode:**
1. Enter Edit Mode on a mesh object
2. Select 2 or more faces
3. Open sidebar (N key) → Cable Gen tab
4. Expand "Create New Cable"
5. Adjust thickness and resolution if needed
6. Click "Generate Cable"

**Object-to-Object Mode:**
1. Select 2 or more objects in Object Mode
2. Open sidebar (N key) → Cable Gen tab
3. Choose connection mode (Sequential or All to First)
4. Click "Generate Cable"

### Using Presets
1. Expand the "Presets" panel
2. Click Thin, Med, Thick, or Power
3. Settings automatically adjust
4. Generate your cable

### Adding End Caps
1. Expand "End Caps" panel
2. Enable the checkbox in the panel header
3. Choose cap type (Cylinder, Sphere, or Custom)
4. Generate cable (caps are added automatically)

**Or add to existing cable:**
1. Select a cable
2. In "Edit Selected Cable" panel
3. Click "Add Caps"

### Applying Array Mesh
1. Create a small mesh object (oriented with Z-axis forward)
2. Select your cable(s)
3. Expand "Array Mesh" panel
4. Choose your mesh in "Array Mesh" field
5. Set initial scale
6. Click "Apply Array Mesh"
7. Select the array object to adjust count and fit mode

##  Usage Tips

### Cable Routing
- **Normals Matter**: Cables extend from face normals for natural routing
- **Handle Direction**: Addon automatically adjusts handles to avoid objects
- **Sag Control**: Use sag slider for hanging cables or wire droop
- **Reverse Direction**: Flip cable if it's going the wrong way

### End Caps
- **Scale with Thickness**: Caps automatically resize when you change cable thickness
- **Cap Scale Multiplier**: Fine-tune cap size independently
- **Follow Curve**: Caps rotate to match curve tangents at endpoints
- **Custom Meshes**: Use any mesh as a connector or plug

### Array Modifiers
- **Mesh Orientation**: Orient your mesh with Z-axis pointing forward
- **Fit to Curve**: Automatically spaces instances along cable length
- **Fixed Count**: Specify exact number of instances
- **Merge Vertices**: Enable to connect instances seamlessly

### Organization
- **Collections**: Enable "Organize in Collection" for automatic organization
- **Naming**: Cables are automatically named Cable_1, Cable_2, etc.
- **Batch Operations**: Use "Select All Cables" for scene-wide adjustments

##  Preferences

Access addon preferences in Edit → Preferences → Add-ons → Cable Generator:

- **Default Thickness**: Starting thickness for new cables (0.05m)
- **Default Resolution**: Starting curve resolution (12)
- **Show Cable Info**: Toggle length/thickness display
- **Auto Smooth Angle**: Smoothing angle for end caps (35°)

##  Panel Reference

### Create New Cable (Collapsible)
- Thickness, Resolution, Connection Mode
- Generate Cable button

### Presets (Collapsible)
- Thin (0.01m) - Med (0.05m) - Thick (0.1m) - Power (0.08m)

### End Caps (Collapsible)
- Enable toggle in header
- Type: Cylinder, Sphere, Custom
- Custom mesh selector

### Array Mesh (Collapsible)
- Mesh selector
- Initial scale
- Apply button

### Edit Selected Cable (Auto-shows when cable selected)
- Length and thickness info
- Thickness, Resolution, Sag sliders
- Add/Remove Caps button
- Cap Scale (when caps present)
- Reverse Direction tool

### Edit Selected Array (Auto-shows when array selected)
- Scale slider
- Array Mode: Fit to Curve / Fixed Count buttons
- Count slider (in fixed mode)
- Merge Vertices options

### Utilities (Collapsible)
- Organize in Collection toggle
- Select All Cables
- Convert to Mesh

##  Technical Details

- **Blender Version**: 4.5 or higher
- **Curve Type**: Bezier curves with FREE handles
- **Bevel Depth**: Controlled via custom property with driver
- **End Caps**: Parented to cable with auto-orientation
- **Arrays**: Use Array + Curve modifiers for deformation
- **Auto Smooth**: Applied at 35° (configurable) using shade_auto_smooth operator

##  Troubleshooting

**Addon doesn't appear after installation:**
- Make sure you enabled it in Preferences → Add-ons
- Check the zip contains `cable_generator.py` at the top level
- Try restarting Blender

**Cables go through objects:**
- Check face normals (they should point outward)
- Try selecting faces in different order
- Use Reverse Direction tool if needed

**Array mesh not following curve:**
- Ensure mesh is oriented with Z-axis pointing forward
- Check that mesh origin is at the base
- Try adjusting initial scale

**End caps not appearing:**
- Make sure "Add End Caps" is enabled before generating
- For existing cables, use "Add Caps" button in Edit Cable panel
- Check that cap type is selected (not on Custom with no mesh)

**Properties not updating:**
- Make sure the cable is selected
- Check that you're adjusting properties in the correct panel
- Try moving the slider to trigger the update handler

##  License

MIT License - see [LICENSE](LICENSE) file for details


##  Acknowledgments

- Built for the Blender community
- Thanks to all who provided feedback and testing

##  Changelog

### v1.1.0 (Current)
- Initial public release
- Face-to-face and object-to-object cable generation
- Live editable properties (thickness, resolution, sag)
- End caps with auto-scaling and orientation
- Array modifier support with fit/count modes
- Preset system for common cable types
- Organized collapsible UI
- Batch operations and utilities
- Comprehensive preferences panel

---

**Enjoy creating cables! 🔌**