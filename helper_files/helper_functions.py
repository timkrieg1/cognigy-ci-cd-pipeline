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
    # --- Remove trailing slashes and "/new" from base URL ---
    return re.sub(r"/new/?$|/$", "", base_url.strip())

def replace_metadata_in_files(directory, main_mapping):
    """
    Iterates over all JSON files in a directory and replaces metadata fields if objects are identical
    (except for metadata keys) when compared to the main_mapping.

    Args:
        directory (str): Path to the directory containing JSON files.
        main_mapping (dict): A dictionary where keys are referenceIds and values are dictionaries with "objectData".
    """
    metadata_keys = {"lastChanged", "lastChangedBy"}

    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith(".json"):
                file_path = os.path.join(root, file)
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        data = json.load(f)

                    # Process the JSON data
                    updated_data = replace_metadata_in_object(data, main_mapping, metadata_keys)

                    # Write the updated data back to the file
                    with open(file_path, "w", encoding="utf-8") as f:
                        json.dump(updated_data, f, indent=4, ensure_ascii=False)

                except json.JSONDecodeError:
                    print(f"Skipping invalid JSON file: {file_path}")
                except Exception as e:
                    print(f"An error occurred while processing file {file_path}: {e}")


def replace_metadata_in_object(obj, main_mapping, metadata_keys):
    """
    Recursively processes a JSON object or list to replace metadata fields if objects are identical
    (except for metadata keys) when compared to the main_mapping.

    Args:
        obj (dict or list): The JSON object or list to process.
        main_mapping (dict): A dictionary where keys are referenceIds and values are dictionaries with "objectData".
        metadata_keys (set): A set of metadata keys to replace.

    Returns:
        The updated JSON object with metadata fields replaced where applicable.
    """
    if isinstance(obj, dict):
        # Check if the object has a referenceId
        reference_id = obj.get("referenceId")
        if reference_id and reference_id in main_mapping:

            main_object = main_mapping[reference_id].get("objectData")

            if main_object:
                if "createdAt" in main_object:
                    obj["createdAt"] = main_object["createdAt"]
                if "createdBy" in main_object:
                    obj["createdBy"] = main_object["createdBy"]
                if "chartReference" in main_object:
                    obj["chartReference"] = main_object["chartReference"]
                if "intentTrainGroupReference" in main_object:
                    obj["intentTrainGroupReference"] = main_object["intentTrainGroupReference"]
                # Compare the object with the main object, excluding metadata keys
                obj_without_metadata = {k: v for k, v in obj.items() if k not in metadata_keys}
                main_object_without_metadata = {k: v for k, v in main_object.items() if k not in metadata_keys}

                if obj_without_metadata == main_object_without_metadata:
                    # Replace metadata keys in the object
                    for key in metadata_keys:
                        if key in main_object:
                            obj[key] = main_object[key]


        # Recursively process all keys in the object
        for key, value in obj.items():
            obj[key] = replace_metadata_in_object(value, main_mapping, metadata_keys)

    elif isinstance(obj, list):
        # Recursively process each item in the list
        for i in range(len(obj)):
            obj[i] = replace_metadata_in_object(obj[i], main_mapping, metadata_keys)

    return obj

def traverse_directory(directory):
    """Recursively traverse a directory and collect all JSON files."""
    json_files = []
    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith(".json"):
                json_files.append(os.path.join(root, file))
    return json_files

def load_json_files(file_paths):
    """Load JSON files and create a mapping by referenceId."""
    def extract_objects(data):
        """Recursively extract objects with a referenceId from nested structures."""
        objects = []
        if isinstance(data, dict):
            if "referenceId" in data:
                objects.append(data)
            for value in data.values():
                objects.extend(extract_objects(value))
        elif isinstance(data, list):
            for item in data:
                objects.extend(extract_objects(item))
        return objects

    mapping = {}
    for file_path in file_paths:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            objects = extract_objects(data)
            for obj in objects:
                reference_id = obj.get("referenceId")
                if reference_id and reference_id not in mapping:
                    extracted_values = {
                        "_id": obj.get("_id"),
                        "objectData": obj
                    }
                    mapping[reference_id] = extracted_values
    return mapping

def extract_flow_setting_ids(flows_file_path):
    """Extract flow metadata IDs from a flows.json file."""
    flow_setting_ids = {}
    for flow in os.listdir(flows_file_path):
        flow_metadata_file_path = os.path.join(flows_file_path, flow, "metadata/metadata.json")
        with open(flow_metadata_file_path, "r", encoding="utf-8") as flow_metadata_file:
            flow_metadata = json.load(flow_metadata_file)
            flow_ref_id = flow_metadata.get("referenceId")

        flow_settings_file_path = os.path.join(flows_file_path, flow, "settings/settings.json")
        with open(flow_settings_file_path, "r", encoding="utf-8") as flow_settings_file:
            flow_settings = json.load(flow_settings_file)
            flow_setting_id = flow_settings.get("_id")
        flow_setting_ids[flow_ref_id] = flow_setting_id

    return flow_setting_ids

def create_id_mapping(main_mapping, feature_mapping):
    """Create a mapping of feature _id to main _id by referenceId."""
    id_mapping = {}
    for ref_id, main_obj in main_mapping.items():
        feature_obj = feature_mapping.get(ref_id)
        if feature_obj and "_id" in main_obj and "_id" in feature_obj:
            id_mapping[feature_obj["_id"]] = main_obj["_id"]
    return id_mapping

def replace_ids(data, id_mapping):
    """
    Replace all occurrences of feature _id with main _id in the data.

    Args:
        data (dict, list, or str): The JSON data to process.
        id_mapping (dict): A dictionary where keys are feature IDs and values are main IDs.
    """
    if isinstance(data, dict):
        for key, value in data.items():
            if isinstance(value, str) and value in id_mapping:
                # Replace string value if it matches an ID in the mapping
                data[key] = id_mapping[value]
            else:
                # Recursively process nested structures
                replace_ids(value, id_mapping)
    elif isinstance(data, list):
        for i in range(len(data)):
            if isinstance(data[i], str) and data[i] in id_mapping:
                # Replace string value in the list if it matches an ID in the mapping
                data[i] = id_mapping[data[i]]
            else:
                # Recursively process nested structures
                replace_ids(data[i], id_mapping)

def compare_and_replace_metadata(main_mapping, feature_mapping):
    """Compare objects and replace metadata fields if objects are otherwise identical."""
    metadata_keys = {"createdAt", "lastChanged", "createdBy", "lastChangedBy"}
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

    # --- Extract flow setting IDs and add to mappings ---
    flow_settings_main_mapping = extract_flow_setting_ids(os.path.join(main_dir, "flows"))
    flow_settings_feature_mapping = extract_flow_setting_ids(os.path.join(feature_dir, "flows"))
    idx = 0
    for ref_id in flow_settings_main_mapping:
        flow_ref_id_mock = f"{ref_id}_FlowSetting{idx}"
        main_mapping[flow_ref_id_mock] = {"_id": flow_settings_main_mapping[ref_id]}
        feature_mapping[flow_ref_id_mock] = {"_id": flow_settings_feature_mapping[ref_id]}
        idx += 1

    # Step 2: Create ID mapping
    
    id_mapping = create_id_mapping(main_mapping, feature_mapping)
    id_mapping[feature_project_id] = main_project_id  # Add project ID mapping

    # Step 3: Replace IDs in feature mapping
    replace_ids_in_files(feature_dir, id_mapping)

    # Step 4: Replace IDs in Lexicons according to custom logic
    replace_lexicon_ids(feature_dir, main_dir)

    # Step 5: Replace intent slot ids according to custom logic
    replace_slot_ids(feature_dir, main_dir)

    # Step 6: Replace ids in extenions according to custom logic
    replace_extension_ids(feature_dir, main_dir)

    # Step 6: Compare and replace metadata
    replace_metadata_in_files(feature_dir, main_mapping)

def replace_ids_in_files(directory, id_mapping):
    """
    Iterates over all JSON files in a directory and replaces occurrences of feature IDs with main IDs.

    Args:
        directory (str): Path to the directory containing JSON files.
        id_mapping (dict): A dictionary where keys are feature IDs and values are main IDs.
    """
    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith(".json"):
                file_path = os.path.join(root, file)
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        data = json.load(f)

                    # Replace IDs in the file"s data
                    replace_ids(data, id_mapping)

                    # Write the updated data back to the file
                    with open(file_path, "w", encoding="utf-8") as f:
                        json.dump(data, f, indent=4, ensure_ascii=False)

                except json.JSONDecodeError:
                    print(f"Skipping invalid JSON file: {file_path}")
                except Exception as e:
                    print(f"An error occurred while processing file {file_path}: {e}")

def replace_lexicon_ids(feature_dir, main_dir):
    """
    Replaces lexicon value IDs in the feature directory with matching IDs from the main directory
    based on keyphrase comparison.

    Args:
        feature_dir (str): Path to the feature agent directory containing lexicons.
        main_dir (str): Path to the main agent directory containing lexicons.
    """
    feature_lexicons_path = os.path.join(feature_dir, "lexicons")
    main_lexicons_path = os.path.join(main_dir, "lexicons")

    # Load lexicons from both directories by referenceId
    feature_lexicons = load_lexicons_by_reference_id(feature_lexicons_path)
    main_lexicons = load_lexicons_by_reference_id(main_lexicons_path)

    # Iterate over feature lexicons and compare with main lexicons
    for reference_id, feature_lexicon in feature_lexicons.items():
        main_lexicon = main_lexicons.get(reference_id)
        if not main_lexicon:
            continue  # Skip if no matching referenceId in main lexicons

        # Compare values in both lexicons
        feature_values = feature_lexicon.get("values", [])
        main_values = main_lexicon.get("values", [])

        for feature_value in feature_values:
            feature_keyphrase = feature_value.get("keyphrase")
            if not feature_keyphrase:
                continue  # Skip if no keyphrase in the feature value

            # Find a matching keyphrase in the main lexicon
            for main_value in main_values:
                if main_value.get("keyphrase") == feature_keyphrase:
                    # Replace the _id in the feature lexicon with the _id from the main lexicon
                    feature_value["_id"] = main_value["_id"]
                    break

    # Save the updated feature lexicons back to their files
    for reference_id, feature_lexicon in feature_lexicons.items():
        feature_lexicon_path = os.path.join(feature_lexicons_path, f"{feature_lexicon['name']}.json")
        with open(feature_lexicon_path, "w", encoding="utf-8") as f:
            json.dump(feature_lexicon, f, indent=4, ensure_ascii=False)


def load_lexicons_by_reference_id(directory):
    """
    Loads all lexicons from a directory and organizes them by referenceId.

    Args:
        directory (str): Path to the directory containing lexicon JSON files.

    Returns:
        dict: A dictionary where keys are referenceIds and values are lexicon objects.
    """
    lexicons = {}
    if not os.path.exists(directory):
        return lexicons

    for file_name in os.listdir(directory):
        if file_name.endswith(".json"):
            file_path = os.path.join(directory, file_name)
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    lexicon = json.load(f)
                    reference_id = lexicon.get("referenceId")
                    if reference_id:
                        lexicons[reference_id] = lexicon
            except json.JSONDecodeError:
                print(f"Skipping invalid JSON file: {file_path}")
    return lexicons

def replace_slot_ids(feature_dir, main_dir):
    """
    Replaces slot IDs in the feature directory with matching IDs from the main directory
    if the slot objects are identical (excluding the _id).

    Args:
        feature_dir (str): Path to the feature agent directory containing flows.
        main_dir (str): Path to the main agent directory containing flows.
    """
    flows_path_feature = os.path.join(feature_dir, "flows")
    flows_path_main = os.path.join(main_dir, "flows")

    for flow_name in os.listdir(flows_path_feature):
        feature_intents_path = os.path.join(flows_path_feature, flow_name, "intents/intents.json")
        main_intents_path = os.path.join(flows_path_main, flow_name, "intents/intents.json")

        if not os.path.exists(feature_intents_path) or not os.path.exists(main_intents_path):
            continue  # Skip if intents.json is missing in either directory

        with open(feature_intents_path, "r", encoding="utf-8") as f:
            feature_intents = json.load(f)

        with open(main_intents_path, "r", encoding="utf-8") as f:
            main_intents = json.load(f)

        # Iterate over intents in the feature directory
        for intent_name, feature_intent_data in feature_intents.items():
            main_intent_data = main_intents.get(intent_name)
            if not main_intent_data:
                continue  # Skip if the intent does not exist in the main directory

            # Iterate over training sentences in the feature intent
            for feature_sentence in feature_intent_data.get("training_sentences", []):
                reference_id = feature_sentence.get("referenceId")
                if not reference_id:
                    continue  # Skip if no referenceId is present

                # Find the corresponding training sentence in the main intent
                main_sentence = next(
                    (s for s in main_intent_data.get("training_sentences", []) if s.get("referenceId") == reference_id),
                    None
                )
                if not main_sentence:
                    continue  # Skip if no matching training sentence is found

                # Compare slots in the training sentences
                feature_slots = feature_sentence.get("slots", [])
                main_slots = main_sentence.get("slots", [])

                for feature_slot in feature_slots:
                    # Find a matching slot in the main slots (excluding _id)
                    matching_main_slot = next(
                        (main_slot for main_slot in main_slots if {k: v for k, v in main_slot.items() if k != "_id"} ==
                         {k: v for k, v in feature_slot.items() if k != "_id"}),
                        None
                    )
                    if matching_main_slot:
                        # Replace the _id in the feature slot with the _id from the main slot
                        feature_slot["_id"] = matching_main_slot["_id"]

        # Save the updated intents.json back to the feature directory
        with open(feature_intents_path, "w", encoding="utf-8") as f:
            json.dump(feature_intents, f, indent=4, ensure_ascii=False)

def replace_extension_ids(feature_dir, main_dir):
    """
    Replaces extension IDs in the feature directory with matching IDs from the main directory
    based on name comparison. Also updates _id in nodes and connections recursively.

    Args:
        feature_dir (str): Path to the feature agent directory containing extensions.
        main_dir (str): Path to the main agent directory containing extensions.
    """
    feature_extensions_path = os.path.join(feature_dir, "extensions")
    main_extensions_path = os.path.join(main_dir, "extensions")

    # Load extensions from both directories by name
    feature_extensions = load_extensions_by_name(feature_extensions_path)
    main_extensions = load_extensions_by_name(main_extensions_path)

    # Iterate over feature extensions and compare with main extensions
    for name, feature_extension in feature_extensions.items():
        main_extension = main_extensions.get(name)
        if not main_extension:
            continue  # Skip if no matching name in main extensions

        # Replace the _id in the feature extension with the _id from the main extension
        feature_extension["_id"] = main_extension["_id"]
        feature_extension["imageUrlToken"] = main_extension["imageUrlToken"]

        # Check if lastChanged is within 10 minutes (600 seconds) of createdAt -> assume no code change was done this was just snapshot restoring
        if feature_extension.get("lastChanged") - 600 < feature_extension.get("createdAt")  :
            feature_extension["lastChangedBy"] = main_extension["lastChangedBy"]
            feature_extension["lastChanged"] = main_extension["lastChanged"]

        # Replace createdBy and createdAt
        feature_extension["createdBy"] = main_extension["createdBy"]
        feature_extension["createdAt"] = main_extension["createdAt"]

        # Recursively update _id in nodes and connections
        if "nodes" in feature_extension and "nodes" in main_extension:
            update_ids_recursively(
                feature_extension["nodes"],
                main_extension["nodes"],
                key_to_match="defaultLabel"
            )
        if "connections" in feature_extension and "connections" in main_extension:
            update_ids_recursively(
                feature_extension["connections"],
                main_extension["connections"],
                key_to_match="fieldName"
            )

    # Save the updated feature extensions back to their files
    for name, feature_extension in feature_extensions.items():
        feature_extension_path = os.path.join(feature_extensions_path, f"{name}.json")
        with open(feature_extension_path, "w", encoding="utf-8") as f:
            json.dump(feature_extension, f, indent=4, ensure_ascii=False)


def update_ids_recursively(feature_objects, main_objects, key_to_match):
    """
    Recursively updates _id in feature objects based on matching key values in main objects.

    Args:
        feature_objects (list or dict): The feature objects to update.
        main_objects (list or dict): The main objects to compare against.
        key_to_match (str): The key to use for matching (e.g., "defaultLabel" or "fieldName").

    Returns:
        The modified feature_objects with updated _id values.
    """
    def find_matching_object(main_objects, key, value):
        """
        Recursively searches for an object in main_objects where the given key matches the given value.

        Args:
            main_objects (list or dict): The main objects to search.
            key (str): The key to match.
            value: The value to match.

        Returns:
            dict or None: The matching object, or None if no match is found.
        """
        if isinstance(main_objects, list):
            for obj in main_objects:
                if isinstance(obj, dict):
                    if obj.get(key) == value:
                        return obj
                    # Recursively search in nested structures
                    result = find_matching_object(obj, key, value)
                    if result:
                        return result
        elif isinstance(main_objects, dict):
            for k, v in main_objects.items():
                if isinstance(v, dict) and v.get(key) == value:
                    return v
                elif isinstance(v, (dict, list)):
                    # Recursively search in nested structures
                    result = find_matching_object(v, key, value)
                    if result:
                        return result
        return None

    if isinstance(feature_objects, list):
        for i in range(len(feature_objects)):
            if isinstance(feature_objects[i], (dict, list)):
                # Recursively process each item in the list
                feature_objects[i] = update_ids_recursively(feature_objects[i], main_objects, key_to_match)
    elif isinstance(feature_objects, dict):
        # Check if the object has an _id and the matching key
        if "_id" in feature_objects and key_to_match in feature_objects:
            matching_main_obj = find_matching_object(main_objects, key_to_match, feature_objects[key_to_match])
            if matching_main_obj:
                # Replace the _id if a match is found
                feature_objects["_id"] = matching_main_obj["_id"]

        # Recursively process all keys in the object
        for key, value in feature_objects.items():
            if isinstance(value, (dict, list)):
                feature_objects[key] = update_ids_recursively(value, main_objects, key_to_match)

    return feature_objects


def load_extensions_by_name(directory):
    """
    Loads all extensions from a directory and organizes them by name.

    Args:
        directory (str): Path to the directory containing extension JSON files.

    Returns:
        dict: A dictionary where keys are extension names and values are extension objects.
    """
    extensions = {}
    if not os.path.exists(directory):
        return extensions

    for file_name in os.listdir(directory):
        if file_name.endswith(".json"):
            file_path = os.path.join(directory, file_name)
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    extension = json.load(f)
                    name = extension.get("name")
                    if name:
                        extensions[name] = extension
            except json.JSONDecodeError:
                print(f"Skipping invalid JSON file: {file_path}")
    return extensions