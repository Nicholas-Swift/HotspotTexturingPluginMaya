import maya.cmds as cmds
import json
from hotspot_texturing.hotspot_layout import (
    align_uv_to_hotspot,
    apply_uv_mapping
)


file_node = ""

def set_file_node_texture_path(texture_path):
    """Update the global file_node's texture path."""
    cmds.setAttr(f"{file_node}.fileTextureName", texture_path[0], type="string")

def get_file_node_texture_path():
    """Get the global file_node's texture path."""
    return cmds.getAttr(f"{file_node}.fileTextureName")

def create_plane(plane_name, sub_x=8, sub_y=8, width=10, height=10):
    """
    Create a polygon plane, deleting any existing one with the same name.
    Returns the newly created plane.
    """
    if cmds.objExists(plane_name):
        cmds.delete(plane_name)
    plane = cmds.polyPlane(
        name=plane_name,
        subdivisionsX=sub_x,
        subdivisionsY=sub_y,
        width=width,
        height=height
    )[0]
    return plane

def create_material_with_texture(material_name, texture_path):
    """
    Create a Lambert material, file node, and shading group.
    Connect them together and set the file node texture path.
    Returns (material, file_node, shading_group).
    """
    global file_node

    # Delete existing material if it exists
    if cmds.objExists(material_name):
        cmds.delete(material_name)

    material = cmds.shadingNode("lambert", asShader=True, name=material_name)
    file_node = cmds.shadingNode("file", asTexture=True, name=f"{material_name}_texture")
    shading_group = cmds.sets(
        renderable=True, 
        noSurfaceShader=True, 
        empty=True, 
        name=f"{material_name}_SG"
    )
    cmds.connectAttr(f"{material}.outColor", f"{shading_group}.surfaceShader")
    cmds.connectAttr(f"{file_node}.outColor", f"{material}.color")

    # Set the file texture path
    if (texture_path is not None and len(texture_path) is not 0):
        cmds.setAttr(f"{file_node}.fileTextureName", texture_path, type="string")
    else:
        cmds.warning("No material assigned due to invalid texture path.")

    return material, file_node, shading_group

def assign_material_to_object(obj_name, material_name):
    """Assign the given material to the specified object."""
    cmds.select(obj_name)
    cmds.hyperShade(assign=material_name)

def open_uv_editor():
    """Open the UV Editor if not open, or bring it to the foreground if it is."""
    if not cmds.window("UVTextureEditor", exists=True):
        cmds.TextureViewWindow()
    else:
        cmds.showWindow("UVTextureEditor")

def cut_uvs(obj_name):
    """
    Perform a UV cut on all faces of the given object.
    """
    cmds.select(f"{obj_name}.f[*]")
    cmds.polyMapCut()
    cmds.select(obj_name)

def create_hotspot():
    """Create a new hotspot with the selected texture."""
    # Prompt user to select an image
    file_path = cmds.fileDialog2(
        fileFilter="Images (*.png *.jpg *.jpeg *.bmp *.tga)", 
        dialogStyle=2, 
        fileMode=1
    )
    if not file_path:
        return

    plane_name = "hotspot_temp"
    plane = create_plane(plane_name, sub_x=8, sub_y=8, width=10, height=10)

    material_name = f"{plane_name}_mat"
    create_material_with_texture(material_name, file_path[0])
    assign_material_to_object(plane, material_name)

    cut_uvs(plane)
    open_uv_editor()

    cmds.inViewMessage(
        amg=f"Created new hotspot with texture: {file_path[0]}",
        pos="midCenter",
        fade=True
    )

    return file_path[0]

def load_hotspot():
    """
    Load a hotspot from a JSON file, create and layout the plane 
    based on hotspot data (texture, UV locations, etc.).
    """
    file_path = cmds.fileDialog2(
        fileFilter="JSON Files (*.json)", 
        dialogStyle=2, 
        fileMode=1
    )
    if not file_path:
        return

    with open(file_path[0], 'r') as file:
        hotspot_data = json.load(file)

    texture_path = hotspot_data["texture_path"] if "texture_path" in hotspot_data else None
    hotspots = [key for key in hotspot_data.keys() if key.startswith("hotspot_")]
    num_hotspots = len(hotspots)

    if num_hotspots == 0:
        cmds.error("No hotspots found in the JSON file.")
        return

    plane_name = "hotspot_temp"
    plane = create_plane(plane_name, sub_x=num_hotspots, sub_y=1, width=10, height=10)

    material_name = f"{plane_name}_mat"
    create_material_with_texture(material_name, texture_path)
    assign_material_to_object(plane, material_name)

    cut_uvs(plane)

    # Align each face's UV to the hotspot's UV
    for i, hotspot_key in enumerate(hotspots):
        face_name = f"{plane}.f[{i}]"
        hotspot_info = hotspot_data[hotspot_key]
        hotspot_uv_coords = hotspot_info["uv_coords"]

        face_uvs = cmds.polyListComponentConversion(face_name, fromFace=True, toUV=True)
        face_uvs = cmds.ls(face_uvs, flatten=True)

        uv_coords_flat = cmds.polyEditUV(face_uvs, query=True)
        uv_coords = [(uv_coords_flat[j], uv_coords_flat[j + 1]) 
                     for j in range(0, len(uv_coords_flat), 2)]

        aligned_uvs = align_uv_to_hotspot(uv_coords, hotspot_uv_coords)
        apply_uv_mapping(face_uvs, aligned_uvs)

    open_uv_editor()
    cmds.inViewMessage(
        amg="Hotspot plane created and UVs aligned successfully!",
        pos="midCenter",
        fade=True
    )

    return file_path[0], texture_path
