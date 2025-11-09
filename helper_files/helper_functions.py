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

def extract_reference_id_mapping(json_obj, mapping, main):
    """
    Recursively iterates over a JSON object to find subobjects containing 'referenceId' and '_id'.
    Assigns the '_id' to either 'mainId' or 'featureId' based on the 'main' parameter.
    
    Args:
        json_obj (dict or list): The JSON object to iterate over.
        mapping (dict): The dictionary to store referenceId -> {"mainId": "", "featureId": ""} mappings.
        main (bool): If True, assigns the '_id' to 'mainId'. Otherwise, assigns it to 'featureId'.
    """
    if isinstance(json_obj, dict):
        if "referenceId" in json_obj and "_id" in json_obj:
            ref_id = json_obj["referenceId"]
            if ref_id not in mapping:
                mapping[ref_id] = {"mainId": "", "featureId": ""}
            if main:
                mapping[ref_id]["mainId"] = json_obj["_id"]
            else:
                mapping[ref_id]["featureId"] = json_obj["_id"]
        for key, value in json_obj.items():
            extract_reference_id_mapping(value, mapping, main)
    elif isinstance(json_obj, list):
        for item in json_obj:
            extract_reference_id_mapping(item, mapping, main)

def read_json_files_in_directory(folder_path: str, main: bool, mapping=None):
    """
    Recursively iterates over a directory and reads all JSON files inside it.
    Extracts 'referenceId' and '_id' mappings from the JSON content.
    
    Args:
        folder_path (str): Path to the folder to iterate over.
        main (bool): If True, assigns '_id' to 'mainId'. Otherwise, assigns it to 'featureId'.
        mapping (dict, optional): An existing dictionary to store referenceId -> {"mainId": "", "featureId": ""} mappings.
                                   If None, a new dictionary will be created.
    
    Returns:
        dict: A dictionary of referenceId -> {"mainId": "", "featureId": ""} mappings.
    """
    if mapping is None:
        mapping = {}
    for root, _, files in os.walk(folder_path):
        for file in files:
            if file.endswith(".json"):
                file_path = os.path.join(root, file)
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        extract_reference_id_mapping(data, mapping, main)
                except json.JSONDecodeError:
                    print(f"Skipping invalid JSON file: {file_path}")
    return mapping