import maya.cmds as cmds
import json
import os
import math
import maya.api.OpenMaya as om
import re


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


def find_corner_uv_points(uv_coords, uv_names):
    """
    Find the 4 corner UV points from the UV coordinates.
    Returns (corner_dict, corner_indices_dict) where corner_dict contains the coordinates
    and corner_indices_dict contains the indices in the uv_coords list.
    """
    if not uv_coords:
        return {}, {}
    
    # Get extreme values
    u_values = [uv[0] for uv in uv_coords]
    v_values = [uv[1] for uv in uv_coords]
    
    min_u, max_u = min(u_values), max(u_values)
    min_v, max_v = min(v_values), max(v_values)
    
    # Find closest UV points to each corner
    corners = {}
    corner_indices = {}
    corner_names = ['top_left', 'top_right', 'bottom_left', 'bottom_right']
    target_corners = [
        (min_u, max_v),  # top_left
        (max_u, max_v),  # top_right
        (min_u, min_v),  # bottom_left
        (max_u, min_v)   # bottom_right
    ]
    
    for corner_name, (target_u, target_v) in zip(corner_names, target_corners):
        min_distance = float('inf')
        best_coord = None
        best_index = -1
        
        for i, (u, v) in enumerate(uv_coords):
            distance = ((u - target_u) ** 2 + (v - target_v) ** 2) ** 0.5
            if distance < min_distance:
                min_distance = distance
                best_coord = (u, v)
                best_index = i
        
        corners[corner_name] = best_coord
        corner_indices[corner_name] = best_index
    
    return corners, corner_indices

def calculate_relative_positions(uv_coords, uv_names, corner_uvs, corner_indices):
    """
    Calculate relative positions of all UVs based on the corner rectangle.
    Returns a list of dictionaries with UV name, original position, and relative position.
    """
    # Get corner bounds
    tl = corner_uvs['top_left']
    tr = corner_uvs['top_right'] 
    bl = corner_uvs['bottom_left']
    br = corner_uvs['bottom_right']
    
    min_u = min(tl[0], tr[0], bl[0], br[0])
    max_u = max(tl[0], tr[0], bl[0], br[0])
    min_v = min(tl[1], tr[1], bl[1], br[1])
    max_v = max(tl[1], tr[1], bl[1], br[1])
    
    width = max_u - min_u
    height = max_v - min_v
    
    if width == 0 or height == 0:
        cmds.warning("Corner rectangle has zero width or height")
        return []
    
    relative_positions = []
    
    for i, (u, v) in enumerate(uv_coords):
        # Calculate relative position (0.0 to 1.0)
        rel_u = (u - min_u) / width
        rel_v = (v - min_v) / height
        
        # Determine if this is a corner UV
        is_corner = i in corner_indices.values()
        corner_type = None
        if is_corner:
            for corner_name, corner_idx in corner_indices.items():
                if corner_idx == i:
                    corner_type = corner_name
                    break
        
        relative_positions.append({
            'uv_name': uv_names[i],
            'original_pos': (u, v),
            'relative_pos': (rel_u, rel_v),
            'is_corner': is_corner,
            'corner_type': corner_type
        })
    
    return relative_positions

def get_bounds_from_corners(corner_uvs):
    """
    Get bounds tuple from corner UV dictionary.
    """
    all_u = [coord[0] for coord in corner_uvs.values()]
    all_v = [coord[1] for coord in corner_uvs.values()]
    return min(all_u), max(all_u), min(all_v), max(all_v)

def reposition_uvs_with_relative_distances(relative_positions, hotspot_uv_coords):
    """
    Reposition UVs based on relative distances to the new hotspot bounds.
    """
    # Get hotspot bounds
    hotspot_coords = normalize_uv_pairs(hotspot_uv_coords)
    hotspot_min_u, hotspot_max_u, hotspot_min_v, hotspot_max_v = get_uv_bounds(hotspot_coords)
    
    hotspot_width = hotspot_max_u - hotspot_min_u
    hotspot_height = hotspot_max_v - hotspot_min_v
    
    new_positions = []
    
    for uv_data in relative_positions:
        rel_u, rel_v = uv_data['relative_pos']
        
        # Apply relative position to hotspot bounds
        new_u = hotspot_min_u + rel_u * hotspot_width
        new_v = hotspot_min_v + rel_v * hotspot_height
        
        new_positions.append({
            'uv_name': uv_data['uv_name'],
            'new_pos': (new_u, new_v),
            'is_corner': uv_data['is_corner'],
            'corner_type': uv_data['corner_type']
        })
    
    return new_positions

def apply_uv_positions(new_positions):
    """
    Apply the new UV positions to the model.
    """
    for uv_data in new_positions:
        uv_name = uv_data['uv_name']
        new_u, new_v = uv_data['new_pos']
        
        try:
            cmds.polyEditUV(uv_name, u=new_u, v=new_v, relative=False)
        except Exception as e:
            cmds.warning(f"Failed to set UV {uv_name} to ({new_u}, {new_v}): {e}")

def find_closest_hotspot(island_bounds, hotspots):
    """
    Identify the hotspot that best matches the UV island bounds by comparing width/height differences.
    island_bounds is a tuple (min_u, max_u, min_v, max_v).
    hotspots is a dict containing "hotspot_x": { "uv_coords": [...] } plus possibly "texture_path".
    
    Returns the name of the best matched hotspot, or None if none found.
    """
    best_match = None
    min_scale_diff = float('inf')
    best_location_diff = float('inf')

    island_min_u, island_max_u, island_min_v, island_max_v = island_bounds
    island_width = island_max_u - island_min_u
    island_height = island_max_v - island_min_v

    island_center_u = (island_min_u + island_max_u) / 2.0
    island_center_v = (island_min_v + island_max_v) / 2.0

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

        width_diff = abs(island_width - hotspot_width)
        height_diff = abs(island_height - hotspot_height)
        scale_diff = width_diff + height_diff

        # Calculate center distance (location difference)
        hotspot_center_u = (hotspot_min_u + hotspot_max_u) / 2.0
        hotspot_center_v = (hotspot_min_v + hotspot_max_v) / 2.0
        location_diff = math.sqrt(
            (hotspot_center_u - island_center_u)**2 +
            (hotspot_center_v - island_center_v)**2
        )

        if scale_diff < min_scale_diff:
            min_scale_diff = scale_diff
            best_location_diff = location_diff
            best_match = hotspot_name
        elif math.isclose(scale_diff, min_scale_diff, rel_tol=1e-6, abs_tol=1e-9):
            # Tie on scale difference, compare location
            if location_diff < best_location_diff:
                best_location_diff = location_diff
                best_match = hotspot_name

    return best_match


def find_closest_trim_hotspot(island_bounds, hotspots):
    """
    Find the closest hotspot for trim mapping based on Y-axis distance.
    island_bounds is a tuple (min_u, max_u, min_v, max_v).
    hotspots is a dict containing "hotspot_x": { "uv_coords": [...] } plus possibly "texture_path".
    
    Returns the name of the closest hotspot based on Y-axis center distance, or None if none found.
    """
    best_match = None
    min_y_distance = float('inf')

    island_min_u, island_max_u, island_min_v, island_max_v = island_bounds
    island_center_v = (island_min_v + island_max_v) / 2.0

    for hotspot_name, data in hotspots.items():
        # Skip any non-hotspot entries like "texture_path"
        if not hotspot_name.startswith("hotspot_"):
            continue

        if not isinstance(data, dict) or "uv_coords" not in data:
            cmds.warning(f"Invalid hotspot data: {hotspot_name} -> {data}")
            continue

        hotspot_uv_coords = normalize_uv_pairs(data["uv_coords"])
        hotspot_min_u, hotspot_max_u, hotspot_min_v, hotspot_max_v = get_uv_bounds(hotspot_uv_coords)

        # Calculate Y-axis center distance
        hotspot_center_v = (hotspot_min_v + hotspot_max_v) / 2.0
        y_distance = abs(hotspot_center_v - island_center_v)

        if y_distance < min_y_distance:
            min_y_distance = y_distance
            best_match = hotspot_name

    return best_match


def align_uv_to_trim(uv_coords, hotspot_uv_coords):
    """
    Align UV coordinates to a trim hotspot with special trim mapping rules:
    1. Scale uniformly until the vertical height matches the hotspot
    2. Position to match Y-axis but preserve X-axis positioning
    3. Only consider topmost and bottommost points for bounding box
    """
    # Normalize first
    uv_coords = normalize_uv_pairs(uv_coords)
    hotspot_uv_coords = normalize_uv_pairs(hotspot_uv_coords)

    # For trim mapping, we only care about the vertical bounds (topmost and bottommost points)
    v_values = [uv[1] for uv in uv_coords]
    island_min_v, island_max_v = min(v_values), max(v_values)
    island_height = island_max_v - island_min_v

    # Get hotspot vertical bounds
    hotspot_v_values = [uv[1] for uv in hotspot_uv_coords]
    hotspot_min_v, hotspot_max_v = min(hotspot_v_values), max(hotspot_v_values)
    hotspot_height = hotspot_max_v - hotspot_min_v

    # Avoid division-by-zero errors
    if island_height == 0:
        cmds.warning("UV island has zero height. Cannot align to trim.")
        return uv_coords  # Return original to avoid further errors

    # Calculate uniform scale based on height matching
    uniform_scale = hotspot_height / island_height

    # Calculate the center points for vertical alignment
    island_center_v = (island_min_v + island_max_v) / 2.0
    hotspot_center_v = (hotspot_min_v + hotspot_max_v) / 2.0
    
    # Calculate translation needed to align centers vertically
    v_translation = hotspot_center_v - island_center_v

    aligned_uvs = []
    for u, v in uv_coords:
        # Apply uniform scaling around the island center
        island_center_u = sum(coord[0] for coord in uv_coords) / len(uv_coords)
        
        # Scale uniformly around the center point
        scaled_u = island_center_u + (u - island_center_u) * uniform_scale
        scaled_v = island_center_v + (v - island_center_v) * uniform_scale
        
        # Apply vertical translation only (preserve X positioning)
        final_u = scaled_u  # No X translation
        final_v = scaled_v + v_translation
        
        aligned_uvs.append((final_u, final_v))

    return aligned_uvs

_comp_re = re.compile(r'^(?P<mesh>.+?)\.(?:map|uv)\[(?P<idx>\d+)\]$')

def _mesh_fn(mesh_or_shape):
    sel = om.MSelectionList()
    sel.add(mesh_or_shape)
    dag = sel.getDagPath(0)
    # ensure we’re on the shape
    if dag.apiType() != om.MFn.kMesh:
        dag.extendToShape()
    return om.MFnMesh(dag)

def _current_uvset(mesh_or_shape):
    uvset = cmds.polyUVSet(mesh_or_shape, q=True, cuv=True)
    # polyUVSet may return a single string or a list depending on context
    return uvset[0] if isinstance(uvset, (list, tuple)) else uvset

def group_uvs_by_selected_shells_from_faces(selected_faces, uv_set=None):
    """
    Returns: List[List[str]]
      e.g. [
        ['pCubeShape1.map[0]', 'pCubeShape1.map[1]', ...],  # shell A
        ['pCubeShape1.map[42]', 'pCubeShape1.map[43]', ...],# shell B
        ['otherShape.map[7]', ...],                         # shell C (another mesh)
      ]
    """
    # Faces -> UV components
    uv_comps = cmds.polyListComponentConversion(selected_faces, fromFace=True, toUV=True)
    uv_comps = cmds.ls(uv_comps, flatten=True) or []
    if not uv_comps:
        return []

    # De-dupe and bucket selected UV indices per mesh/shape
    by_mesh_selected_uv_idx = {}
    for comp in set(uv_comps):
        m = _comp_re.match(comp)
        if not m:
            continue
        mesh = m.group('mesh')  # usually a shape name like pCubeShape1
        idx = int(m.group('idx'))
        by_mesh_selected_uv_idx.setdefault(mesh, set()).add(idx)

    shells_2d = []

    # For each mesh, compute shell IDs once, then gather all UVs in touched shells
    for mesh, sel_idxs in by_mesh_selected_uv_idx.items():
        fn = _mesh_fn(mesh)
        uvset_name = uv_set or _current_uvset(mesh)

        sehll_count, shell_ids = fn.getUvShellsIds(uvset_name)  # MIntArray, int
        # Map: shellId -> [all uv indices in that shell]
        shell_to_all = {}
        for uv_idx, sh_id in enumerate(shell_ids):
            shell_to_all.setdefault(sh_id, []).append(uv_idx)

        # Which shells are touched by the selection?
        touched_shells = { shell_ids[i] for i in sel_idxs if 0 <= i < len(shell_ids) }

        # Collect ALL UVs from each touched shell
        for sh_id in touched_shells:
            full_shell_uv_indices = shell_to_all.get(sh_id, [])
            shells_2d.append([f"{mesh}.map[{i}]" for i in full_shell_uv_indices])

    return shells_2d

def map_faces_to_hotspots(hotspots_file):
    """
    Direct UV-based approach to map selected UVs to hotspot.
    1) Gets all UV points from selection (split by shells)
    2) Finds the 4 corner UVs (top-left, top-right, bottom-left, bottom-right)
    3) Calculates relative distances of internal UVs to corners
    4) Repositions corners to fit hotspot bounds
    5) Repositions internal UVs based on relative distances
    """
    hotspots = load_hotspots_file(hotspots_file)
    if not hotspots:
        msg = "Failed to layout. Hotspot file failed to load."
        cmds.inViewMessage(amg=msg, pos="midCenter", fade=True, backColor=0x00FF0000)
        cmds.error(msg)
        return

    # Get all selected faces
    selected_faces = cmds.ls(selection=True, flatten=True)
    if not selected_faces:
        msg = "Failed to layout. No faces were selected. Please select faces before trying again."
        cmds.inViewMessage(amg=msg, pos="midCenter", fade=True, backColor=0x00FF0000)
        cmds.error(msg)
        return

    # Split all UVs by shells
    all_uvs_two_array = group_uvs_by_selected_shells_from_faces(selected_faces)

    num_success = 0

    for all_uvs in all_uvs_two_array:
        # Remove duplicates while preserving order
        unique_uvs = []
        seen = set()
        for uv in all_uvs:
            if uv not in seen:
                unique_uvs.append(uv)
                seen.add(uv)

        if not unique_uvs:
            msg = "Failed to layout. No UV components found in selection."
            cmds.inViewMessage(amg=msg, pos="midCenter", fade=True, backColor=0x00FF0000)
            cmds.error(msg)
            break

        # Get UV coordinates
        uv_coords_flat = cmds.polyEditUV(unique_uvs, query=True)
        uv_coords = [(uv_coords_flat[i], uv_coords_flat[i + 1])
                    for i in range(0, len(uv_coords_flat), 2)]

        # Find the 4 corner UVs
        corner_uvs, corner_indices = find_corner_uv_points(uv_coords, unique_uvs)

        if not all(corner_uvs.values()):
            msg = "Could not find all 4 corner UV points. Skipping..."
            cmds.warning(msg)
            break

        # Calculate relative distances for internal UVs
        relative_positions = calculate_relative_positions(uv_coords, unique_uvs, corner_uvs, corner_indices)

        # Find best matching hotspot
        corner_bounds = get_bounds_from_corners(corner_uvs)
        matched_hotspot = find_closest_hotspot(corner_bounds, hotspots)
        if not matched_hotspot:
            cmds.warning("Could not find a matching hotspot. Skipping...")
            break

        # Reposition all UVs
        hotspot_uv_coords = hotspots[matched_hotspot]["uv_coords"]
        new_positions = reposition_uvs_with_relative_distances(relative_positions, hotspot_uv_coords)
        
        # Apply the new positions
        apply_uv_positions(new_positions)

        num_success += 1

    # Show success message
    if num_success == 0:
        msg = "Failed to layout. No UVs were mapped to a hotspot."
        cmds.inViewMessage(amg=msg, pos="midCenter", fade=True, backColor=0x00FF0000)
        cmds.error(msg)
        return
    elif num_success == len(all_uvs_two_array):
        msg = "All UVs were mapped to a hotspot successfully!"
        cmds.inViewMessage(amg=msg, pos="midCenter", fade=True)
    else:
        msg = f"Some UVs were not mapped to a hotspot. {num_success} of {len(all_uvs_two_array)} UVs were mapped to a hotspot."
        cmds.inViewMessage(amg=msg, pos="midCenter", fade=True)


def map_faces_to_trim(hotspots_file):
    """
    Map selected UV shells to horizontally tiling trim hotspots.
    This function differs from map_faces_to_hotspots in several ways:
    1. Finds the closest hotspot based on Y-axis distance (vertically closest)
    2. Scales uniformly until vertical height matches the hotspot
    3. Positions to match Y-axis but preserves X-axis positioning
    4. Only considers topmost and bottommost points for bounding calculations
    """
    hotspots = load_hotspots_file(hotspots_file)
    if not hotspots:
        msg = "Failed to layout. Hotspot file failed to load."
        cmds.inViewMessage(amg=msg, pos="midCenter", fade=True, backColor=0x00FF0000)
        cmds.error(msg)
        return

    # Get all selected faces
    selected_faces = cmds.ls(selection=True, flatten=True)
    if not selected_faces:
        msg = "Failed to layout. No faces were selected. Please select faces before trying again."
        cmds.inViewMessage(amg=msg, pos="midCenter", fade=True, backColor=0x00FF0000)
        cmds.error(msg)
        return

    # Split all UVs by shells
    all_uvs_two_array = group_uvs_by_selected_shells_from_faces(selected_faces)

    num_success = 0

    for all_uvs in all_uvs_two_array:
        # Remove duplicates while preserving order
        unique_uvs = []
        seen = set()
        for uv in all_uvs:
            if uv not in seen:
                unique_uvs.append(uv)
                seen.add(uv)

        if not unique_uvs:
            msg = "Failed to layout. No UV components found in selection."
            cmds.inViewMessage(amg=msg, pos="midCenter", fade=True, backColor=0x00FF0000)
            cmds.error(msg)
            break

        # Get UV coordinates
        uv_coords_flat = cmds.polyEditUV(unique_uvs, query=True)
        uv_coords = [(uv_coords_flat[i], uv_coords_flat[i + 1])
                    for i in range(0, len(uv_coords_flat), 2)]

        # For trim mapping, we only need the overall bounds (not perfect rectangles)
        island_bounds = get_uv_bounds(uv_coords)

        # Find closest trim hotspot based on Y-axis distance
        matched_hotspot = find_closest_trim_hotspot(island_bounds, hotspots)
        if not matched_hotspot:
            cmds.warning("Could not find a matching trim hotspot. Skipping...")
            break

        # Align UVs to trim hotspot using special trim rules
        hotspot_uv_coords = hotspots[matched_hotspot]["uv_coords"]
        aligned_uvs = align_uv_to_trim(uv_coords, hotspot_uv_coords)
        
        # Apply the aligned UV coordinates
        apply_uv_mapping(unique_uvs, aligned_uvs)

        num_success += 1

    # Show success message
    if num_success == 0:
        msg = "Failed to layout. No UVs were mapped to a trim hotspot."
        cmds.inViewMessage(amg=msg, pos="midCenter", fade=True, backColor=0x00FF0000)
        cmds.error(msg)
        return
    elif num_success == len(all_uvs_two_array):
        msg = "All UVs were mapped to trim hotspots successfully!"
        cmds.inViewMessage(amg=msg, pos="midCenter", fade=True)
    else:
        msg = f"Some UVs were not mapped to trim hotspots. {num_success} of {len(all_uvs_two_array)} UVs were mapped to trim hotspots."
        cmds.inViewMessage(amg=msg, pos="midCenter", fade=True)
