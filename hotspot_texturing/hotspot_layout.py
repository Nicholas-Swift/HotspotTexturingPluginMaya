import maya.cmds as cmds
import json
import os


def normalize_uv_pairs(uv_pairs):
    """
    Normalize UV pairs to ensure no negative zeros.
    """
    normalized_uvs = []
    for u, v in uv_pairs:
        # Convert -0.0 to 0.0
        u = 0.0 if u == -0.0 else u
        v = 0.0 if v == -0.0 else v
        normalized_uvs.append((u, v))
    return normalized_uvs

def get_uv_bounds(uv_coords):
    """
    Calculate the min and max U and V values of UV coordinates.
    Returns (min_u, max_u, min_v, max_v).
    """
    u_values = [uv[0] for uv in uv_coords]
    v_values = [uv[1] for uv in uv_coords]
    return min(u_values), max(u_values), min(v_values), max(v_values)

def align_uv_to_hotspot(uv_coords, hotspot_uv_coords):
    """
    Align UV coordinates to match the hotspot UV coordinates.
    This scales and translates uv_coords so they match the bounding box of hotspot_uv_coords.
    """
    # Normalize first
    uv_coords = normalize_uv_pairs(uv_coords)
    hotspot_uv_coords = normalize_uv_pairs(hotspot_uv_coords)

    # Calculate bounds
    island_min_u, island_max_u, island_min_v, island_max_v = get_uv_bounds(uv_coords)
    hotspot_min_u, hotspot_max_u, hotspot_min_v, hotspot_max_v = get_uv_bounds(hotspot_uv_coords)

    island_width = island_max_u - island_min_u
    island_height = island_max_v - island_min_v
    hotspot_width = hotspot_max_u - hotspot_min_u
    hotspot_height = hotspot_max_v - hotspot_min_v

    # Avoid division-by-zero errors
    if island_width == 0 or island_height == 0:
        cmds.warning("UV island has zero width or height. Cannot align.")
        return uv_coords  # Return original to avoid further errors

    scale_u = hotspot_width / island_width
    scale_v = hotspot_height / island_height

    aligned_uvs = []
    for u, v in uv_coords:
        aligned_u = hotspot_min_u + (u - island_min_u) * scale_u
        aligned_v = hotspot_min_v + (v - island_min_v) * scale_v
        aligned_uvs.append((aligned_u, aligned_v))

    return aligned_uvs

def apply_uv_mapping(uvs, aligned_uvs):
    """
    Apply aligned UV coordinates back to the model as absolute positions (relative=False).
    """
    for uv, (new_u, new_v) in zip(uvs, aligned_uvs):
        cmds.polyEditUV(uv, u=new_u, v=new_v, relative=False)


def load_hotspots_file(file_path):
    """
    Load the hotspots data from the JSON file.
    Returns a dictionary of hotspots if successful, or None if not found or invalid.
    """
    if not os.path.exists(file_path):
        msg = f"Hotspots file not found at {file_path}"
        cmds.warning(msg)
        cmds.inViewMessage(amg=msg, pos="midCenter", fade=True)
        return None

    with open(file_path, 'r') as f:
        hotspots = json.load(f)
    return hotspots


def find_closest_hotspot(island_bounds, hotspots):
    """
    Identify the hotspot that best matches the UV island bounds by comparing width/height differences.
    island_bounds is a tuple (min_u, max_u, min_v, max_v).
    hotspots is a dict containing "hotspot_x": { "uv_coords": [...] } plus possibly "texture_path".
    
    Returns the name of the best matched hotspot, or None if none found.
    """
    best_match = None
    min_difference = float('inf')

    island_width = island_bounds[1] - island_bounds[0]
    island_height = island_bounds[3] - island_bounds[2]

    for hotspot_name, data in hotspots.items():
        # Skip any non-hotspot entries like "texture_path"
        if not hotspot_name.startswith("hotspot_"):
            continue

        if not isinstance(data, dict) or "uv_coords" not in data:
            cmds.warning(f"Invalid hotspot data: {hotspot_name} -> {data}")
            continue

        hotspot_uv_coords = normalize_uv_pairs(data["uv_coords"])
        hotspot_min_u, hotspot_max_u, hotspot_min_v, hotspot_max_v = get_uv_bounds(hotspot_uv_coords)

        hotspot_width = hotspot_max_u - hotspot_min_u
        hotspot_height = hotspot_max_v - hotspot_min_v

        # Calculate dimension difference
        width_difference = abs(island_width - hotspot_width)
        height_difference = abs(island_height - hotspot_height)
        total_difference = width_difference + height_difference

        if total_difference < min_difference:
            min_difference = total_difference
            best_match = hotspot_name

    return best_match

def map_faces_to_hotspots(hotspots_file):
    """
    Main function to map each face's UVs to the closest hotspot from hotspots_file.
    1) Loads hotspots,
    2) Grabs the selected object,
    3) For each face, calculates UV bounds,
    4) Finds a matching hotspot,
    5) Aligns and applies the UVs.

    Usage:
        1) Select an object,
        2) run map_faces_to_hotspots("path/to/hotspots.json").
    """
    hotspots = load_hotspots_file(hotspots_file)
    if not hotspots:
        msg = "Failed to layout. Hotspot file failed to load."
        cmds.inViewMessage(amg=msg, pos="midCenter", fade=True, backColor=0x00FF0000)
        cmds.error(msg)
        return

    selected_objects = cmds.ls(selection=True)
    if not selected_objects:
        msg = "Failed to layout. No faces were selected. Please select faces before trying again."
        cmds.inViewMessage(amg=msg, pos="midCenter", fade=True, backColor=0x00FF0000)
        cmds.error(msg)
        return

    selected_object = selected_objects[0]
    faces = cmds.polyListComponentConversion(selected_object, toFace=True)
    faces = cmds.ls(faces, flatten=True)

    if not faces:
        msg = "Failed to layout. No faces found on object {selected_object}. Nothing to map."
        cmds.inViewMessage(amg=msg, pos="midCenter", fade=True, backColor=0x00FF0000)
        cmds.error(msg)
        return

    for face in faces:
        # Convert face to UVs
        face_uvs = cmds.polyListComponentConversion(face, fromFace=True, toUV=True)
        face_uvs = cmds.ls(face_uvs, flatten=True)

        # Flatten the UV coordinate array into pairs
        uv_coords_flat = cmds.polyEditUV(face_uvs, query=True)
        uv_coords = [(uv_coords_flat[i], uv_coords_flat[i + 1])
                     for i in range(0, len(uv_coords_flat), 2)]

        # Get the bounding box of the current face's UV island
        min_u, max_u, min_v, max_v = get_uv_bounds(uv_coords)
        island_bounds = (min_u, max_u, min_v, max_v)

        # Find the best hotspot to match
        matched_hotspot = find_closest_hotspot(island_bounds, hotspots)
        if not matched_hotspot:
            cmds.warning(f"Could not find a matching hotspot for face {face}. Skipping...")
            continue

        # Align and apply
        hotspot_uv_coords = hotspots[matched_hotspot]["uv_coords"]
        aligned_uvs = align_uv_to_hotspot(uv_coords, hotspot_uv_coords)
        apply_uv_mapping(face_uvs, aligned_uvs)

    cmds.inViewMessage(amg="Faces mapped to hotspots successfully!", pos="midCenter", fade=True)
