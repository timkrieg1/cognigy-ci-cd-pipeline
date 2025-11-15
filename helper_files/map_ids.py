import os
import json
from collections import defaultdict

def traverse_directory(directory):
    """Recursively traverse a directory and collect all JSON files."""
    json_files = []
    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith('.json'):
                json_files.append(os.path.join(root, file))
    return json_files

def load_json_files(file_paths):
    """Load JSON files and create a mapping by referenceId."""
    def extract_objects(data):
        """Recursively extract objects with a referenceId from nested structures."""
        objects = []
        if isinstance(data, dict):
            if 'referenceId' in data:
                objects.append(data)
            for value in data.values():
                objects.extend(extract_objects(value))
        elif isinstance(data, list):
            for item in data:
                objects.extend(extract_objects(item))
        return objects

    mapping = {}
    for file_path in file_paths:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            objects = extract_objects(data)
            for obj in objects:
                reference_id = obj.get('referenceId')
                if reference_id and reference_id not in mapping:
                    mapping[reference_id] = obj
    return mapping

def create_id_mapping(main_mapping, feature_mapping):
    """Create a mapping of feature _id to main _id by referenceId."""
    id_mapping = {}
    for ref_id, main_obj in main_mapping.items():
        feature_obj = feature_mapping.get(ref_id)
        if feature_obj and '_id' in main_obj and '_id' in feature_obj:
            id_mapping[feature_obj['_id']] = main_obj['_id']
    return id_mapping

def replace_ids(data, id_mapping):
    """Replace all occurrences of feature _id with main _id in the data."""
    if isinstance(data, dict):
        for key, value in data.items():
            if isinstance(value, str) and value in id_mapping:
                data[key] = id_mapping[value]
            else:
                replace_ids(value, id_mapping)
    elif isinstance(data, list):
        for item in data:
            replace_ids(item, id_mapping)

def compare_and_replace_metadata(main_mapping, feature_mapping):
    """Compare objects and replace metadata fields if objects are otherwise identical."""
    metadata_keys = {'createdAt', 'lastChanged', 'createdBy', 'lastChangedBy'}
    for ref_id, main_obj in main_mapping.items():
        feature_obj = feature_mapping.get(ref_id)
        if feature_obj:
            # Remove metadata fields for comparison
            main_copy = {k: v for k, v in main_obj.items() if k not in metadata_keys}
            feature_copy = {k: v for k, v in feature_obj.items() if k not in metadata_keys}
            if main_copy == feature_copy:
                # Replace metadata fields in the main object
                for key in metadata_keys:
                    if key in feature_obj and key in main_obj:
                        feature_obj[key] = main_obj[key]

def replace_ids_in_feature_directory(main_dir, feature_dir, feature_project_id, main_project_id):
    # Step 1: Traverse directories and load JSON files
    main_files = traverse_directory(main_dir)
    feature_files = traverse_directory(feature_dir)

    main_mapping = load_json_files(main_files)
    feature_mapping = load_json_files(feature_files)

    # Step 2: Create ID mapping
    id_mapping = create_id_mapping(main_mapping, feature_mapping)
    id_mapping[feature_project_id] = main_project_id  # Add project ID mapping

    # Step 3: Replace IDs in feature mapping
    for obj in feature_mapping.values():
        replace_ids(obj, id_mapping)

    # Step 4: Compare and replace metadata
    compare_and_replace_metadata(main_mapping, feature_mapping)

    # Step 5: Save updated feature mapping back to files
    metadata_keys = {'createdAt', 'lastChanged', 'createdBy', 'lastChangedBy'}
    for file_path in feature_files:
        with open(file_path, 'r+', encoding='utf-8') as f:
            data = json.load(f)
            if isinstance(data, list):  # Ensure data is a list of objects
                for obj in data:
                    ref_id = obj.get('referenceId')
                    if ref_id and ref_id in feature_mapping:
                        feature_obj = feature_mapping[ref_id]
                        # Replace only metadata keys
                        for key in metadata_keys:
                            if key in feature_obj:
                                obj[key] = feature_obj[key]
            elif isinstance(data, dict):  # Handle single object files
                ref_id = data.get('referenceId')
                if ref_id and ref_id in feature_mapping:
                    feature_obj = feature_mapping[ref_id]
                    # Replace only metadata keys
                    for key in metadata_keys:
                        if key in feature_obj:
                            data[key] = feature_obj[key]
            f.seek(0)
            json.dump(data, f, indent=4)
            f.truncate()


