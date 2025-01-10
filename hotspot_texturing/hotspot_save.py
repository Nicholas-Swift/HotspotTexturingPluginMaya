import maya.cmds as cmds
import json
import os
from hotspot_texturing.hotspot_create import get_file_node_texture_path


def is_rectangle(uv_coords):
    """
    Check if the UV coordinates form a perfect rectangle and standardize
    their order to a known (u_min, v_min) -> (u_max, v_min) -> (u_max, v_max) -> (u_min, v_max).
    
    Returns (bool is_rect, list standardized_uvs).
    """
    if len(uv_coords) != 8:
        return False, []

    uv_pairs = [(round(uv_coords[i], 4), round(uv_coords[i + 1], 4)) 
                for i in range(0, len(uv_coords), 2)]

    u_values = sorted({uv[0] for uv in uv_pairs})
    v_values = sorted({uv[1] for uv in uv_pairs})

    if len(u_values) != 2 or len(v_values) != 2:
        return False, []

    # Standardized order of rectangle corners
    standardized_uvs = [
        (u_values[0], v_values[0]),
        (u_values[1], v_values[0]),
        (u_values[1], v_values[1]),
        (u_values[0], v_values[1]),
    ]
    return True, standardized_uvs

def get_texture_path(mesh_name):
    """
    Retrieve the texture path from the material assigned to the specified mesh.
    This relies on the externally defined get_file_node_texture_path().
    """
    texture_path = get_file_node_texture_path()
    return texture_path

def capture_uv_data():
    """
    Capture UV data for each selected face if it forms a perfect rectangle.
    
    Returns a dictionary of hotspots:
        {
            "texture_path": <path>,
            "hotspot_1": {"face": <face_name>, "uv_coords": [...]},
            ...
        }
    If any face fails validation or if there's no selection, returns None.
    """
    selection = cmds.ls(selection=True, flatten=True)
    if not selection:
        msg = "No faces selected. Select all relevant faces before saving."
        cmds.warning(msg)
        return []

    hotspots = {}
    failed_faces = []
    validation_failed = False

    for i, face in enumerate(selection):
        # Convert face to its corresponding UVs
        uvs = cmds.polyListComponentConversion(face, toUV=True)
        uv_coords = cmds.polyEditUV(uvs, query=True)

        is_rect, standardized_uvs = is_rectangle(uv_coords)
        if not is_rect:
            validation_failed = True
            cmds.warning(f"{face} failed validation: Not a perfect rectangle.")
            failed_faces.append(face)
            continue

        hotspot_key = f"hotspot_{i + 1}"
        hotspots[hotspot_key] = {
            "face": face,
            "uv_coords": standardized_uvs
        }

    if validation_failed:
        # Since at least one face is invalid, treat this as a blocking error
        cmds.select(failed_faces, replace=True)
        cmds.warning("Validation failed for one or more faces. Failed to save.")
        return None

    # Get the texture path from the selected mesh (assumes all faces belong to the same mesh)
    mesh_name = selection[0].split(".")[0]
    texture_path = get_texture_path(mesh_name)
    if texture_path:
        hotspots["texture_path"] = texture_path
    else:
        cmds.warning("Texture path not saved to hotspot file due to no texture path found")

    return hotspots

def save_hotspots_to_json(hotspots):
    """
    Save the hotspots dictionary to a JSON file in the 'hotspots' folder
    under the current Maya project directory.
    
    Returns the file path if saved successfully, or None if canceled.
    """
    if not hotspots:
        cmds.warning("No hotspots to save.")
        return None

    project_path = cmds.workspace(query=True, rootDirectory=True)
    hotspots_folder = os.path.join(project_path, "hotspots")
    if not os.path.exists(hotspots_folder):
        os.makedirs(hotspots_folder)

    # Prompt for save location
    file_path = cmds.fileDialog2(
        dialogStyle=2,
        fileMode=0,
        fileFilter="JSON Files (*.json)",
        startingDirectory=hotspots_folder
    )
    if not file_path:
        return None

    file_path = file_path[0]
    with open(file_path, 'w') as f:
        json.dump(hotspots, f, indent=4)

    cmds.inViewMessage(amg="Hotspot data saved successfully!",
                       pos='topCenter', fade=True)
    return file_path

def save_hotspot():
    """
    Orchestrates the capturing of UV data and saving it to a file.
    
    Returns the file path if successful, or None if canceled or failed.
    """
    hotspot_data = capture_uv_data()
    if not hotspot_data or len(hotspot_data) == 0:
        # Either user canceled or some error occurred
        msg = "Failed to save hotspot. " + "Could not capture UV data, save aborted." if hotspot_data is None else "No faces selected, please select relevant faces before saving."
        cmds.inViewMessage(
            amg=msg,
            pos="midCenter",
            fade=True,
            backColor=0x00FF0000
        )
        cmds.error(msg)
        return None

    file_path = save_hotspots_to_json(hotspot_data)
    return file_path
