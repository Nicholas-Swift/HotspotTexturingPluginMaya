import maya.cmds as cmds
import json
import os

def load_hotspots(file_path):
    """Load the hotspots data from the JSON file."""
    if not os.path.exists(file_path):
        print(f"Hotspots file not found at {file_path}")
        return None
    with open(file_path, 'r') as f:
        hotspots = json.load(f)
    return hotspots

def normalize_uv_pairs(uv_pairs):
    """Normalize UV pairs to ensure no negative zeros or negative values."""
    normalized_uvs = []
    for u, v in uv_pairs:
        u = 0.0 if u == -0.0 else u
        v = 0.0 if v == -0.0 else v
        normalized_uvs.append((u, v))
    return normalized_uvs

def get_uv_bounds(uv_coords):
    """Calculate the min and max U and V values of UV coordinates."""
    u_values = [uv[0] for uv in uv_coords]
    v_values = [uv[1] for uv in uv_coords]
    return min(u_values), max(u_values), min(v_values), max(v_values)

def find_closest_hotspot(island_bounds, hotspots):
    """Identify the hotspot that best matches the UV island bounds."""
    best_match = None
    min_difference = float('inf')

    island_width = island_bounds[1] - island_bounds[0]
    island_height = island_bounds[3] - island_bounds[2]

    for hotspot_name, data in hotspots.items():
        hotspot_uv_coords = data["uv_coords"]
        hotspot_uv_coords = normalize_uv_pairs(hotspot_uv_coords)
        hotspot_bounds = get_uv_bounds(hotspot_uv_coords)
        hotspot_width = hotspot_bounds[1] - hotspot_bounds[0]
        hotspot_height = hotspot_bounds[3] - hotspot_bounds[2]

        # Calculate the difference in dimensions
        width_difference = abs(island_width - hotspot_width)
        height_difference = abs(island_height - hotspot_height)
        total_difference = width_difference + height_difference

        if total_difference < min_difference:
            min_difference = total_difference
            best_match = hotspot_name

    return best_match

def align_uv_to_hotspot(uv_coords, hotspot_uv_coords):
    """Align UV coordinates to match the hotspot UV coordinates."""
    # Normalize UV coordinates
    uv_coords = normalize_uv_pairs(uv_coords)
    hotspot_uv_coords = normalize_uv_pairs(hotspot_uv_coords)

    # Calculate bounds
    island_min_u, island_max_u, island_min_v, island_max_v = get_uv_bounds(uv_coords)
    hotspot_min_u, hotspot_max_u, hotspot_min_v, hotspot_max_v = get_uv_bounds(hotspot_uv_coords)

    # Calculate scaling factors
    island_width = island_max_u - island_min_u
    island_height = island_max_v - island_min_v
    hotspot_width = hotspot_max_u - hotspot_min_u
    hotspot_height = hotspot_max_v - hotspot_min_v

    # Avoid division by zero
    if island_width == 0 or island_height == 0:
        print("Error: UV island has zero width or height.")
        return uv_coords  # Return original UVs to avoid further errors

    scale_u = hotspot_width / island_width
    scale_v = hotspot_height / island_height

    # Scale and translate each UV point
    aligned_uvs = []
    for u, v in uv_coords:
        aligned_u = hotspot_min_u + (u - island_min_u) * scale_u
        aligned_v = hotspot_min_v + (v - island_min_v) * scale_v
        aligned_uvs.append((aligned_u, aligned_v))

    return aligned_uvs

def apply_uv_mapping(uvs, aligned_uvs):
    """Apply the aligned UV coordinates back to the model."""
    # Apply UVs as absolute positions
    for uv, (new_u, new_v) in zip(uvs, aligned_uvs):
        cmds.polyEditUV(uv, u=new_u, v=new_v, relative=False)

def map_faces_to_hotspots(hotspots_file):
    """Main function to map faces' UVs to hotspots."""
    # Load hotspots from file
    hotspots = load_hotspots(hotspots_file)
    if not hotspots:
        return

    # Get the selected object
    selected_objects = cmds.ls(selection=True)
    if not selected_objects:
        print("No object selected.")
        return

    selected_object = selected_objects[0]

    # Get all faces of the selected object
    faces = cmds.polyListComponentConversion(selected_object, toFace=True)
    faces = cmds.ls(faces, flatten=True)

    # Process each face individually
    for face in faces:
        # Get the UVs associated with the face
        face_uvs = cmds.polyListComponentConversion(face, fromFace=True, toUV=True)
        face_uvs = cmds.ls(face_uvs, flatten=True)
        # Get the UV coordinates
        uv_coords_flat = cmds.polyEditUV(face_uvs, query=True)
        uv_coords = [(uv_coords_flat[i], uv_coords_flat[i + 1]) for i in range(0, len(uv_coords_flat), 2)]

        # Calculate UV bounds
        min_u, max_u, min_v, max_v = get_uv_bounds(uv_coords)
        island_bounds = (min_u, max_u, min_v, max_v)

        # Find the closest matching hotspot for the face
        matched_hotspot = find_closest_hotspot(island_bounds, hotspots)
        if not matched_hotspot:
            print(f"Failed to find a matching hotspot for face {face}.")
            continue

        # Align the UVs to the matched hotspot's UV coordinates
        hotspot_uv_coords = hotspots[matched_hotspot]["uv_coords"]
        aligned_uvs = align_uv_to_hotspot(uv_coords, hotspot_uv_coords)

        # Apply the aligned UV coordinates back to the model
        apply_uv_mapping(face_uvs, aligned_uvs)

        print(f"Mapped face {face} to hotspot {matched_hotspot}.")

# Main Script Execution
def main_map_faces_to_hotspots():
    project_path = cmds.workspace(query=True, rootDirectory=True)
    hotspots_file = os.path.join(project_path, "data", "trim_hotspots.json")
    map_faces_to_hotspots(hotspots_file)

# Run the script
main_map_faces_to_hotspots()
