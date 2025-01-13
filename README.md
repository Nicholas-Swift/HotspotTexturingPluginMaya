# Hotspot Texturing Plugin for Maya

This Maya plugin is designed to streamline the UV mapping process in Maya for trim sheets and texture atlases. Inspired by tools used in industry at companies like [Valve](https://developer.valvesoftware.com/wiki/Half-Life:_Alyx_Workshop_Tools/Level_Design/Hotspot_Texturing) and [Naughty Dog](https://www.artstation.com/artwork/qQGK6y).

Key Features:
- Automate UV mapping for trims and atlas textures.
- Manage several different hotspot files for different textures.

Check out a [video demo of the plugin in action here](https://www.youtube.com/watch?v=UMgLn1B00sg&ab_channel=NicholasSwift).

Learn more at the [ArtStation blog post here](https://www.artstation.com/blogs/wnswift/3ZEVN/hotspot-texturing-plugin-for-maya).

---

## Installation

Follow these steps to install and set up the Hotspot Texturing plugin for Maya.

### Step 1: Quit Maya
Before proceeding with the installation, ensure that Maya is closed.

### Step 2: Copy the Plugin Folder
1. Download this repo as a zip file, and unzip.
2. Locate the `hotspot_texturing` folder that contains the `.py` files.
3. Copy the folder.
4. Paste it into the following directory on your computer:
   - **Windows**: `C:\Users\<yourusername>\Documents\maya\2025\scripts`
   - **Mac**: `/Users/<yourusername>/Library/Preferences/Autodesk/maya/2025/scripts`

   If your Maya version differs, replace `2025` with your specific version number.
   
   **Note for Mac users**: If you can't find `/Library`, open Terminal and type `open ./Library/Preferences`, then navigate to the correct directory.

### Step 3: Open Maya
Restart Maya to make sure it recognizes the newly added script folder.

### Step 4: Add the Script to the Toolbar
1. Open the **Script Editor** in Maya.
   - Found in the bottom-right corner of the Maya interface or under the `Windows > General Editors > Script Editor` menu.
2. In the **Python** tab, paste the following code:

   ```python
   from hotspot_texturing.hotspot_ui import create_hotspot_texturing_window

   create_hotspot_texturing_window()
   ```

3. Press **Ctrl + A** to select all (or **Command + A** on Mac).
4. Drag and drop the selected code to your Maya Shelf to create a custom button.

---

## Feedback and Contributions
If you encounter any issues or have suggestions for improvements, feel free to open an issue or submit a pull request. Contributions welcome!
