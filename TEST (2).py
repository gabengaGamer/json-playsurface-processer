import bpy
import os
import json
import mathutils

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
    return blender_matrix

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
        obj.matrix_world = l2w_matrix

def build_scene():
    models = parse_json_file(JSON_FILE_PATH)

    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)

    for model in models:
        import_and_position_model(model)

build_scene()
