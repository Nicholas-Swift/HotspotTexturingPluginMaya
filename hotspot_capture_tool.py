import maya.cmds as cmds
import json
import os

def is_rectangle(uv_coords):
    """Check if the UV coordinates form a perfect rectangle and standardize their order."""
    # Ensure we have exactly four points (8 values for U and V combined)
    if len(uv_coords) != 8:
        return False, []

    # Separate and round U and V coordinates to 4 decimal places, store as pairs
    uv_pairs = [(round(uv_coords[i], 4), round(uv_coords[i + 1], 4)) for i in range(0, len(uv_coords), 2)]

    # Extract unique U and V values
    u_values = sorted({uv[0] for uv in uv_pairs})
    v_values = sorted({uv[1] for uv in uv_pairs})

    # Check for exactly 2 unique U and 2 unique V values
    if len(u_values) != 2 or len(v_values) != 2:
        return False, []

    # Standardize UV coordinate order (lower-left, lower-right, upper-right, upper-left)
    standardized_uvs = [
        (u_values[0], v_values[0]),  # Lower-left
        (u_values[1], v_values[0]),  # Lower-right
        (u_values[1], v_values[1]),  # Upper-right
        (u_values[0], v_values[1]),  # Upper-left
    ]

    return True, standardized_uvs

def capture_uv_data():
    """Capture UV data for each selected face if it forms a perfect rectangle."""
    hotspots = {}
    selection = cmds.ls(selection=True, flatten=True)

    if not selection:
        print("No faces selected.")
        return False

    print("Capturing UV hotspots for selected faces:")
    validation_failed = False

    for i, face in enumerate(selection):
        uvs = cmds.polyListComponentConversion(face, toUV=True)
        uv_coords = cmds.polyEditUV(uvs, query=True)

        # Check if the UVs form a rectangle and standardize them
        is_rect, standardized_uvs = is_rectangle(uv_coords)
        if not is_rect:
            validation_failed = True
            print(f"{face} failed validation: Not a perfect rectangle.")
            continue

        hotspots[f"hotspot_{i+1}"] = {
            "face": face,
            "uv_coords": standardized_uvs
        }
        print(f"{face} captured as hotspot_{i+1}.")

    if validation_failed:
        print("Validation failed for one or more faces. Hotspot data not captured.")
        cmds.error("Validation failed for one or more faces. Hotspot data not captured.")
        return False

    return hotspots

def save_hotspots(hotspots, file_path):
    """Save the hotspots dictionary to a JSON file."""
    if not hotspots:
        print("No hotspots to save.")
        return

    # Ensure the directory exists
    directory = os.path.dirname(file_path)
    if not os.path.exists(directory):
        os.makedirs(directory)

    with open(file_path, 'w') as f:
        json.dump(hotspots, f, indent=4)
    print(f"Hotspots saved to {file_path}")

def get_project_path():
    """Retrieve the current Maya project path."""
    return cmds.workspace(query=True, rootDirectory=True)

# Main Script Execution for Saving Hotspots
def main_save_hotspots():
    project_path = get_project_path()
    file_path = os.path.join(project_path, "data", "trim_hotspots.json")

    hotspot_data = capture_uv_data()
    if hotspot_data:
        save_hotspots(hotspot_data, file_path)
        cmds.inViewMessage(amg="Hotspot data captured successfully!", pos='topCenter', fade=True)

# Run the script
main_save_hotspots()
