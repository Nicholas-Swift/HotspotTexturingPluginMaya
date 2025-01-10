import maya.cmds as cmds
import webbrowser
from hotspot_texturing.hotspot_create import (
    set_file_node_texture_path,
    load_hotspot,
    create_hotspot
)
from hotspot_texturing.hotspot_save import save_hotspot
from hotspot_texturing.hotspot_layout import map_faces_to_hotspots


hotspotCurrentHotspotPath = ""
hotspotCurrentTexturePath = ""

def load_new_hotspot():
    """
    Function to load a hotspot file (JSON).
    Updates the global hotspot/texture paths if successful.
    """
    global hotspotCurrentHotspotPath, hotspotCurrentTexturePath
    result = load_hotspot()
    if not result:
        return

    (file_path, texture_path) = result
    if file_path:
        hotspotCurrentHotspotPath = file_path
        hotspotCurrentTexturePath = texture_path if texture_path else ""
        cmds.inViewMessage(amg=f"Loaded hotspot from: {file_path}", pos="midCenter", fade=True)
        update_text_inputs()
    else:
        msg = "Failed to load hotspot. Loaded hotspot did not provide a valid file."
        cmds.inViewMessage(amg=msg, pos="midCenter", fade=True, backColor=0x00FF0000)
        cmds.error(msg)

def update_texture(file_path_field):
    """
    Function to update the texture file (image).
    Opens a file dialog for the user to pick a new texture.
    """
    file_path = cmds.fileDialog2(
        fileFilter="Images (*.png *.jpg *.jpeg *.bmp *.tga)", 
        dialogStyle=2, 
        fileMode=1
    )
    if file_path:
        set_file_node_texture_path(file_path)  # from create_hotspot
        cmds.textField(file_path_field, edit=True, text=file_path[0])
        cmds.inViewMessage(amg=f"Texture updated to: {file_path[0]}", pos="midCenter", fade=True)

def layout_faces():
    """
    Layout faces according to the currently loaded hotspot JSON file.
    """
    if hotspotCurrentHotspotPath:
        map_faces_to_hotspots(hotspotCurrentHotspotPath)
    else:
        msg = "No hotspot file to read from. Cannot layout faces."
        cmds.inViewMessage(amg=msg, pos="midCenter", fade=True, backColor=0x00FF0000)
        cmds.error(msg)

def open_help():
    """Open the help documentation in a web browser."""
    webbrowser.open("https://www.google.com")

def update_text_inputs():
    """
    Update both text fields for hotspot path and texture path, 
    reflecting the current global variables.
    """
    update_text_input("currentHotspotTextField", hotspotCurrentHotspotPath)
    update_text_input("currentTextureTextField", hotspotCurrentTexturePath)

def update_text_input(field_name, text_value):
    """
    Safely update a textField UI element if it exists.
    """
    if cmds.textField(field_name, query=True, exists=True):
        cmds.textField(field_name, edit=True, text=text_value)
    else:
        cmds.error(f"No text field named '{field_name}' exists.")

def create_new_hotspot():
    """
    Create a new hotspot plane with user-chosen texture.
    Updates the global texture path on success.
    """
    global hotspotCurrentHotspotPath, hotspotCurrentTexturePath
    texture_path = create_hotspot()
    if texture_path:
        hotspotCurrentHotspotPath = ""  # No associated JSON yet
        hotspotCurrentTexturePath = texture_path
        cmds.inViewMessage(amg=f"New hotspot created with texture: {texture_path}", pos="midCenter", fade=True)
        update_text_inputs()

def save_current_hotspot():
    """
    Saves the currently selected faces as a hotspot JSON file.
    On success, updates the global hotspotCurrentHotspotPath.
    """
    global hotspotCurrentHotspotPath
    file_path = save_hotspot()
    if file_path:
        hotspotCurrentHotspotPath = file_path
        cmds.inViewMessage(amg=f"Hotspot saved to: {file_path}", pos="midCenter", fade=True)
        update_text_inputs()

def create_hotspot_texturing_window():
    """
    Create the dockable window with a single tab for hotspot texturing tools.
    """
    workspace_name = "Hotspot Texturing Workspace"
    if cmds.workspaceControl(workspace_name, exists=True):
        cmds.deleteUI(workspace_name)

    workspace_control = cmds.workspaceControl(
        workspace_name,
        label="Hotspot Texturing",
        floating=True,
        widthProperty="free",    # Allow user to freely resize in width
        initialWidth=300,
        initialHeight=350,
        retain=True
    )

    # Enforce minimum size of 50x50
    cmds.workspaceControl(
        workspace_name, edit=True,
        minimumWidth=50,
        minimumHeight=50,
        resizeWidth=50,
        resizeHeight=50
    )

    menu_bar = cmds.menuBarLayout(parent=workspace_control)

    # Add the Help menu
    cmds.menu(label="Help", parent=menu_bar)
    cmds.menuItem(label="How to Use", command=lambda _: open_help())

    # Main scroll layout for content
    main_layout = cmds.scrollLayout(
        parent=workspace_control,
        horizontalScrollBarThickness=0,
        childResizable=True
    )

    #
    # CURRENT HOTSPOT SECTION
    #
    current_hotspot_frame = cmds.frameLayout(
        label="Current Hotspot",
        collapsable=True,
        collapse=False,
        parent=main_layout,
        marginHeight=10
    )
    cmds.columnLayout(adjustableColumn=True, parent=current_hotspot_frame)
    cmds.rowLayout(
        parent=current_hotspot_frame,
        numberOfColumns=2,
        adjustableColumn=1,
        columnAttach=[(1, "both", 0), (2, "both", 0)]
    )
    cmds.textField("currentHotspotTextField", editable=False, height=25)
    cmds.iconTextButton(
        style="iconAndTextHorizontal",
        image="loadPreset.png",
        label="Load",
        height=25,
        width=80,
        flat=False,
        command=lambda: load_new_hotspot()
    )
    cmds.setParent("..")

    #
    # CREATE SECTION
    #
    create_frame = cmds.frameLayout(
        label="Create",
        collapsable=True,
        collapse=False,
        parent=main_layout,
        marginHeight=10
    )
    cmds.columnLayout(adjustableColumn=True, parent=create_frame)

    # Create New Hotspot
    cmds.iconTextButton(
        style="iconAndTextHorizontal",
        image="polyCreateUVShell.png",
        label="Create New Hotspot",
        height=25,
        flat=False,
        command=lambda *_: create_new_hotspot()
    )

    # Save Hotspot
    cmds.iconTextButton(
        style="iconAndTextHorizontal",
        image="polyOptimizeUV.png",
        label="Save Hotspot As...",
        height=25,
        flat=False,
        command=lambda *_: save_current_hotspot()
    )

    # Update Texture label
    cmds.text(label="Update Texture", align="left", parent=create_frame)

    # Update Texture row
    cmds.rowLayout(
        parent=create_frame,
        numberOfColumns=2,
        adjustableColumn=1,
        columnAttach=[(1, "both", 0), (2, "both", 0)]
    )
    texture_path = cmds.textField("currentTextureTextField", editable=False, height=25)
    cmds.iconTextButton(
        style="iconAndTextHorizontal",
        image="UVEditorImage.png",
        label="Browse",
        height=25,
        width=80,
        flat=False,
        command=lambda: update_texture(texture_path)
    )
    cmds.setParent("..")

    #
    # LAYOUT SECTION
    #
    layout_frame = cmds.frameLayout(
        label="Layout",
        collapsable=True,
        collapse=False,
        parent=main_layout,
        marginHeight=10
    )
    cmds.columnLayout(adjustableColumn=True, parent=layout_frame)

    cmds.iconTextButton(
        style="iconAndTextHorizontal",
        image="UV_Unfold_Brush.png",
        label="Layout Faces",
        height=25,
        flat=False,
        command=lambda *_: layout_faces()
    )
