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
    are present, the mapping is transformed to use 'featureId' as the key and 'mainId' as the value.
    
    Args:
        json_obj (dict or list): The JSON object or list to iterate over.
        mapping (dict): The dictionary to store referenceId -> {"mainId": "", "featureId": ""} mappings.
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
                        mapping[ref_id] = {"mainId": "", "featureId": ""}
                    if main:
                        mapping[ref_id]["mainId"] = json_obj["_id"]
                    else:
                        mapping[ref_id]["featureId"] = json_obj["_id"]
                        # If both mainId and featureId are present, transform the mapping
                        if mapping[ref_id]["mainId"] and mapping[ref_id]["featureId"]:
                            feature_id = mapping[ref_id]["featureId"]
                            main_id = mapping[ref_id]["mainId"]
                            mapping.pop(ref_id)  # Remove the referenceId entry
                            mapping[feature_id] = main_id  # Use featureId as key and mainId as value
                            processed_ids.add(ref_id)  # Mark this referenceId as processed
            else:
                print(f"Skipping unhashable referenceId: {ref_id}")
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

def replace_ids_in_json_files(folder_path: str, id_mapping: dict):
    """
    Iterates over all JSON files in a directory and replaces featureId with mainId using the provided mapping.
    
    Args:
        folder_path (str): Path to the folder containing JSON files.
        id_mapping (dict): A dictionary where keys are featureIds and values are mainIds.
    """
    def replace_ids_in_object(obj, id_mapping):
        """
        Recursively replaces featureIds with mainIds in a JSON object.
        
        Args:
            obj (dict or list): The JSON object to process.
            id_mapping (dict): The mapping of featureIds to mainIds.
        
        Returns:
            The updated JSON object with IDs replaced.
        """
        if isinstance(obj, dict):
            for key, value in obj.items():
                if isinstance(value, (dict, list)):
                    obj[key] = replace_ids_in_object(value, id_mapping)
                elif isinstance(value, str) and value in id_mapping:
                    obj[key] = id_mapping[value]  # Replace featureId with mainId
        elif isinstance(obj, list):
            for i in range(len(obj)):
                obj[i] = replace_ids_in_object(obj[i], id_mapping)
        return obj

    for root, _, files in os.walk(folder_path):
        for file in files:
            if file.endswith(".json"):
                file_path = os.path.join(root, file)
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    
                    # Replace IDs in the JSON data
                    updated_data = replace_ids_in_object(data, id_mapping)
                    
                    # Write the updated JSON back to the file
                    with open(file_path, 'w', encoding='utf-8') as f:
                        json.dump(updated_data, f, indent=4)
                
                except json.JSONDecodeError:
                    print(f"Skipping invalid JSON file: {file_path}")
                except Exception as e:
                    print(f"An error occurred while processing file {file_path}: {e}")