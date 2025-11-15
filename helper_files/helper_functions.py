import functools
import requests 
import re  
import time  
import os
import json

# --- Decorator for retrying on 500 server errors ---
def retry_on_500(max_retries=3, wait_seconds=5):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            retries = 0
            while True:
                try:
                    return func(*args, **kwargs)
                except requests.HTTPError as e:
                    if e.response is not None and e.response.status_code == 500:
                        retries += 1
                        if retries > max_retries:
                            print(f"Max retries reached for {func.__name__}. Raising error.", flush=True)
                            raise
                        print(f"500 Server Error encountered in {func.__name__}, retrying in {wait_seconds} seconds... (Attempt {retries}/{max_retries})", flush=True)
                        time.sleep(wait_seconds)
                    else:
                        raise
        return wrapper
    return decorator

def clean_base_url(base_url: str) -> str:
    """
    Cleans the base URL by removing trailing slashes.
    """
    # --- Remove trailing slashes and '/new' from base URL ---
    return re.sub(r'/new/?$|/$', '', base_url.strip())

def extract_reference_id_mapping(json_obj, mapping, main, processed_ids):
    """
    Recursively iterates over a JSON object or list to find subobjects containing 'referenceId' and '_id'.
    Updates the mapping based on the 'main' parameter. If 'main' is False and both 'mainId' and 'featureId'
    are present, the mapping is transformed to include metadata fields and the entire object.
    
    Args:
        json_obj (dict or list): The JSON object or list to iterate over.
        mapping (dict): The dictionary to store referenceId -> {"mainId": "", "featureId": "", "createdAt": "", ...} mappings.
        main (bool): If True, assigns the '_id' to 'mainId'. Otherwise, assigns it to 'featureId'.
        processed_ids (set): A set to track referenceIds that have already been transformed.
    """
    if isinstance(json_obj, dict):
        if "referenceId" in json_obj and "_id" in json_obj:
            ref_id = json_obj["referenceId"]
            # Ensure ref_id is a hashable type (e.g., string)
            if isinstance(ref_id, str):
                if ref_id not in processed_ids:
                    if ref_id not in mapping:
                        mapping[ref_id] = {
                            "mainId": "",
                            "featureId": "",
                            "createdAt": "",
                            "createdBy": "",
                            "lastChanged": "",
                            "lastChangedBy": "",
                            "originalObject": {}
                        }
                    if main:
                        mapping[ref_id]["mainId"] = json_obj["_id"]
                    else:
                        mapping[ref_id]["featureId"] = json_obj["_id"]
                    for key in ["createdAt", "createdBy", "lastChanged", "lastChangedBy"]:
                        if key in json_obj:
                            mapping[ref_id][key] = json_obj[key]
        for key, value in json_obj.items():
            extract_reference_id_mapping(value, mapping, main, processed_ids)
    elif isinstance(json_obj, list):
        for item in json_obj:
            extract_reference_id_mapping(item, mapping, main, processed_ids)

def read_json_files_in_directory(folder_path: str, main: bool, mapping=None):
    """
    Recursively iterates over a directory and reads all JSON files inside it.
    Extracts 'referenceId' and '_id' mappings from the JSON content.
    Updates the mapping based on the 'main' parameter. If 'main' is False and both 'mainId' and 'featureId'
    are present, the mapping is transformed to use 'featureId' as the key and 'mainId' as the value.
    
    Args:
        folder_path (str): Path to the folder to iterate over.
        main (bool): If True, assigns '_id' to 'mainId'. Otherwise, assigns it to 'featureId'.
        mapping (dict, optional): An existing dictionary to store referenceId -> {"mainId": "", "featureId": ""} mappings.
                                   If None, a new dictionary will be created.
    
    Returns:
        dict: A dictionary of featureId -> mainId mappings if 'main' is False and both IDs are present.
              Otherwise, a dictionary of referenceId -> {"mainId": "", "featureId": ""}.
    """
    if mapping is None:
        mapping = {}
    processed_ids = set()  # Track processed referenceIds
    for root, _, files in os.walk(folder_path):
        for file in files:
            if file.endswith(".json"):
                file_path = os.path.join(root, file)
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        # Handle both dict and list as the top-level JSON structure
                        extract_reference_id_mapping(data, mapping, main, processed_ids)
                except json.JSONDecodeError:
                    print(f"Skipping invalid JSON file: {file_path}")
    return mapping

def replace_feature_ids(obj, id_mapping):
    """
    Recursively replaces all occurrences of featureIds with mainIds in a JSON object, regardless of the key name.
    
    Args:
        obj (dict or list): The JSON object to process.
        id_mapping (dict): The mapping of featureIds to mainIds and metadata.
    
    Returns:
        The updated JSON object with featureIds replaced.
    """
    if isinstance(obj, dict):
        for key, value in obj.items():
            if isinstance(value, (dict, list)):
                obj[key] = replace_feature_ids(value, id_mapping)
            elif isinstance(value, str) and value in id_mapping and id_mapping[value]["mainId"]:
                obj[key] = id_mapping[value]["mainId"]  # Replace featureId with mainId
    elif isinstance(obj, list):
        for i in range(len(obj)):
            obj[i] = replace_feature_ids(obj[i], id_mapping)
    return obj


def replace_metadata(obj, id_mapping):
    """
    Recursively replaces metadata fields (createdAt, createdBy, lastChanged, lastChangedBy) for objects with _id values.
    
    Args:
        obj (dict or list): The JSON object to process.
        id_mapping (dict): The mapping of featureIds to mainIds and metadata.
    
    Returns:
        The updated JSON object with metadata fields replaced.
    """
    if isinstance(obj, dict):
        if "_id" in obj:
            feature_id = obj["_id"]
            if feature_id in id_mapping:
                mapping_entry = id_mapping[feature_id]
                # Check if all other properties are unchanged
                unchanged = all(
                    key not in ["_id", "referenceId", "createdAt", "createdBy", "lastChanged", "lastChangedBy"]
                    and obj.get(key) == mapping_entry.get(key)
                    for key in obj
                )
                if unchanged:
                    # Replace metadata fields
                    for key in ["createdAt", "createdBy", "lastChanged", "lastChangedBy"]:
                        if key in mapping_entry:
                            obj[key] = mapping_entry[key]
        # Recursively process all keys in the object
        for key, value in obj.items():
            obj[key] = replace_metadata(value, id_mapping)
    elif isinstance(obj, list):
        for i in range(len(obj)):
            obj[i] = replace_metadata(obj[i], id_mapping)
    return obj


def replace_ids_in_json_files(folder_path: str, id_mapping: dict):
    """
    Iterates over all JSON files in a directory and replaces featureIds with mainIds and updates metadata fields.
    
    Args:
        folder_path (str): Path to the folder containing JSON files.
        id_mapping (dict): A dictionary where keys are featureIds and values are dictionaries with mainId and metadata.
    """
    for root, _, files in os.walk(folder_path):
        for file in files:
            if file.endswith(".json"):
                file_path = os.path.join(root, file)
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    
                    # Step 1: Replace metadata fields first
                    data = replace_metadata(data, id_mapping)
                    
                    # Step 2: Replace featureIds with mainIds
                    data = replace_feature_ids(data, id_mapping)
                    
                    # Write the updated JSON back to the file
                    with open(file_path, 'w', encoding='utf-8') as f:
                        json.dump(data, f, indent=4)
                
                except json.JSONDecodeError:
                    print(f"Skipping invalid JSON file: {file_path}")
                except Exception as e:
                    print(f"An error occurred while processing file {file_path}: {e}")

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