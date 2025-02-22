import bpy
import os
import json
import mathutils
import math
import re

MODEL_DIRECTORY = r"E:\InevitableProject\mp\2tango" # Put here your gltf models from DFSViewer.

PLAYSURFACE_FILE_PATH = r"E:\InevitableProject\mp\2tango.json" # Put here exported playsurface .json from DFSViewer.

imported_models_cache = {} # Model cache allow speed up import by 20 times!

def parse_playsurface_file(file_path):
    with open(file_path, "r") as file:
        data = json.load(file)

    models = []
    for zone in data.get("zones", []):
        for surface in zone.get("surfaces", []):
            model_data = {
                "geom_name": surface["geomName"].replace(".rigidgeom", ".gltf"),
                "l2w": [surface["localToWorld"][i:i+4] for i in range(0, 16, 4)],
            }
            models.append(model_data)
    return models

def create_blender_playsurface_matrix(l2w):
    blender_matrix = mathutils.Matrix(l2w).transposed()

    z_up_to_y_up = mathutils.Matrix.Rotation(math.pi / 2, 4, 'X')
    rotate_minus_180_x = mathutils.Matrix.Rotation(math.radians(-180), 4, 'X') # For some reason objects have wrong rotation, i just adjust and as result fix it!
    corrected_matrix = blender_matrix @ z_up_to_y_up @ rotate_minus_180_x

    return corrected_matrix

def apply_decomposed_playsurface_transformations(obj, matrix):
    translation, rotation, scale = matrix.decompose()
    
    obj.rotation_mode = 'QUATERNION'
    obj.rotation_quaternion = rotation
    obj.location = translation
    obj.scale = scale
    
def rename_and_deduplicate_playsurface_materials(obj, gltf_path):
    with open(gltf_path, "r") as file:
        gltf_data = json.load(file)

    images = gltf_data.get("images", [])
    if not images:
        return

    texture_uris = {}
    for index, image in enumerate(images):
        uri = os.path.basename(image.get("uri", f"Texture_{index}"))
        texture_name = os.path.splitext(uri)[0]
        if index not in texture_uris:
            texture_uris[index] = texture_name

    if obj.type == 'MESH':
        for slot in obj.material_slots:
            if slot.material:
                linked_texture = None
                for node in slot.material.node_tree.nodes:
                    if node.type == 'TEX_IMAGE' and node.image:
                        linked_texture = node.image
                        break
                    elif node.type == 'GROUP' and node.node_tree:
                        for group_node in node.node_tree.nodes:
                            if group_node.type == 'TEX_IMAGE' and group_node.image:
                                linked_texture = group_node.image
                                break
                
                if linked_texture:
                    texture_name = os.path.splitext(os.path.basename(linked_texture.filepath))[0]
                    existing_material = bpy.data.materials.get(texture_name)
                    
                    if existing_material:
                        slot.material = existing_material
                    else:
                        slot.material.name = texture_name

def import_and_position_playsurface_model(model_data):
    geom_path = os.path.join(MODEL_DIRECTORY, model_data["geom_name"])
    if not os.path.exists(geom_path):
        return

    l2w_matrix = create_blender_playsurface_matrix(model_data["l2w"])
    base_name = os.path.splitext(os.path.basename(model_data["geom_name"]))[0]
    name_counter = 0  

    def get_unique_name(base_name):
        nonlocal name_counter
        while f"{base_name}_{name_counter:02d}" in bpy.data.objects:
            name_counter += 1
        return f"{base_name}_{name_counter:02d}"

    if model_data["geom_name"] in imported_models_cache:
        imported_object = imported_models_cache[model_data["geom_name"]]
        new_instance = imported_object.copy()
        new_instance.data = imported_object.data.copy()
        new_instance.name = get_unique_name(base_name)
        bpy.context.collection.objects.link(new_instance)
        new_instance.matrix_world = l2w_matrix
    else:
        bpy.ops.import_scene.gltf(filepath=geom_path, merge_vertices=True)

        imported_objects = bpy.context.selected_objects
        if not imported_objects:
            return

        meshes_to_join = [obj for obj in imported_objects if obj.type == 'MESH']
        if meshes_to_join:
            for obj in meshes_to_join:
                obj.select_set(True)

            bpy.context.view_layer.objects.active = meshes_to_join[0]
            bpy.ops.object.join()

            unified_object = meshes_to_join[0]
            unified_object.name = get_unique_name(base_name)
            unified_object.matrix_world = l2w_matrix
            rename_and_deduplicate_playsurface_materials(unified_object, geom_path)
            imported_models_cache[model_data["geom_name"]] = unified_object
        else:
            for obj in imported_objects:
                obj.name = get_unique_name(base_name)
                obj.matrix_world = l2w_matrix
                rename_and_deduplicate_playsurface_materials(obj, geom_path)
                imported_models_cache[model_data["geom_name"]] = obj

def rotate_entire_scene():
    mesh_rotation = mathutils.Matrix.Rotation(math.radians(90), 4, 'X')
    
    for obj in bpy.data.objects:
        if obj.type in {'MESH'}:
            obj.matrix_world = mesh_rotation @ obj.matrix_world           

def build_scene():
    models = parse_playsurface_file(PLAYSURFACE_FILE_PATH)
    
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)
    
    for model_data in models:
        import_and_position_playsurface_model(model_data)
                      
    rotate_entire_scene()

build_scene()