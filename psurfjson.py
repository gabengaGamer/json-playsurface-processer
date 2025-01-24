import bpy
import os
import json
import mathutils
import math

MODEL_DIRECTORY = r"C:\Users\GameSpy\Downloads\IneV\rigidgeom"

JSON_FILE_PATH = r"C:\Users\GameSpy\Downloads\IneV\data.json"

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

def import_and_position_model(model):
    geom_path = os.path.join(MODEL_DIRECTORY, model["geom_name"])
    if not os.path.exists(geom_path):
        return

    bpy.ops.import_scene.gltf(filepath=geom_path)

    imported_objects = bpy.context.selected_objects
    if not imported_objects:
        return

    l2w_matrix = create_blender_matrix(model["l2w"])

    for obj in imported_objects:
        apply_decomposed_transformations(obj, l2w_matrix)

def rotate_entire_scene():
    scene_rotation = mathutils.Matrix.Rotation(math.radians(-90), 4, 'X')
    
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
