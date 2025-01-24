import bpy
import os
import json
import mathutils
import math
import re

MODEL_DIRECTORY = r"C:\Users\GameSpy\Downloads\IneV\rigidgeom" # Put here your gltf models.

JSON_FILE_PATH = r"C:\Users\GameSpy\Downloads\IneV\data.json" # Put here exported playsurface .json from DFSViewer.

imported_models_cache = {}

def parse_json_file(file_path):
    with open(file_path, "r") as file:
        data = json.load(file)

    models = []
    for zone in data.get("zones", []):
        for surface in zone.get("surfaces", []):
            model = {
                "geom_name": surface["geomName"].replace(".rigidgeom", ".gltf"),
                "l2w": [surface["localToWorld"][i:i+4] for i in range(0, 16, 4)],
            }
            models.append(model)
    return models

def create_blender_matrix(l2w):
    blender_matrix = mathutils.Matrix(l2w).transposed()

    z_up_to_y_up = mathutils.Matrix.Rotation(math.pi / 2, 4, 'X')
    rotate_minus_180_x = mathutils.Matrix.Rotation(math.radians(-180), 4, 'X')
    corrected_matrix = blender_matrix @ z_up_to_y_up @ rotate_minus_180_x

    return corrected_matrix

def apply_decomposed_transformations(obj, matrix):
    translation, rotation, scale = matrix.decompose()
    
    obj.rotation_mode = 'QUATERNION'
    obj.rotation_quaternion = rotation
    obj.location = translation
    obj.scale = scale
    
def rename_and_deduplicate_materials(obj, gltf_path):
    with open(gltf_path, "r") as file:
        gltf_data = json.load(file)

    images = gltf_data.get("images", [])
    if not images:
        return

    texture_names = {
        index: os.path.splitext(os.path.basename(image.get("uri", f"Texture_{index}")))[0]
        for index, image in enumerate(images)
    }

    material_index_pattern = re.compile(r"Material[._]?(\d+)?")

    if obj.type == 'MESH':
        for slot in obj.material_slots:
            if slot.material:
                match = material_index_pattern.search(slot.material.name)
                if match:
                    texture_index = int(match.group(1) or 0)
                    if texture_index in texture_names:
                        new_name = texture_names[texture_index]

                        existing_material = bpy.data.materials.get(new_name)
                        if existing_material:
                            slot.material = existing_material
                        else:
                            slot.material.name = new_name

def import_and_position_model(model):
    geom_path = os.path.join(MODEL_DIRECTORY, model["geom_name"])
    if not os.path.exists(geom_path):
        return

    l2w_matrix = create_blender_matrix(model["l2w"])

    if model["geom_name"] in imported_models_cache:
        imported_object = imported_models_cache[model["geom_name"]]
        new_instance = imported_object.copy()
        new_instance.data = imported_object.data.copy()
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
            unified_object.matrix_world = l2w_matrix
            rename_and_deduplicate_materials(unified_object, geom_path)
            imported_models_cache[model["geom_name"]] = unified_object
        else:
            for obj in imported_objects:
                obj.matrix_world = l2w_matrix
                rename_and_deduplicate_materials(obj, geom_path)
                imported_models_cache[model["geom_name"]] = obj


def rotate_entire_scene():
    scene_rotation = mathutils.Matrix.Rotation(math.radians(90), 4, 'X')
    
    for obj in bpy.data.objects:
        if obj.type in {'MESH', 'EMPTY'}:
            obj.matrix_world = scene_rotation @ obj.matrix_world

def build_scene():
    models = parse_json_file(JSON_FILE_PATH)

    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)

    for model in models:
        import_and_position_model(model)

    rotate_entire_scene()

build_scene()
