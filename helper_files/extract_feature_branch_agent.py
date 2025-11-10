from cognigy_client import CognigyAPIClient
from helper_functions import read_json_files_in_directory, replace_ids_in_json_files
from dotenv import load_dotenv
import os
import sys
import shutil
import subprocess
from datetime import datetime, timezone
import json
import zipfile

# --- Load environment variables ---
load_dotenv(override=True)

# --- Check for required environment variables ---
required_vars = [
    "COGNIGY_BASE_URL_DEV",
    "COGNIGY_API_KEY_DEV",
    "BOT_NAME",
    "BRANCH_NAME"
]

# --- Find missing environment variables ---
missing_vars = [var for var in required_vars if os.getenv(var) is None]
if missing_vars:
    raise EnvironmentError(f"Missing required environment variable(s): {', '.join(missing_vars)}")

# --- Assign environment variables ---
base_url_dev = os.getenv("COGNIGY_BASE_URL_DEV")
api_key_dev = os.getenv("COGNIGY_API_KEY_DEV")
bot_name = os.getenv("BOT_NAME")
branch_name = os.getenv("BRANCH_NAME")

# --- Prepare agent folder structure ---
feature_agent_folder = "feature_agent"
if os.path.exists(feature_agent_folder):
    shutil.rmtree(feature_agent_folder)

# --- Read feature_branch_agent_id.json ---
with open("feature_branch_agent_id.json", "r") as json_file:
    feature_branch_agent_info = json.load(json_file)
    dev_branch_agent_id = feature_branch_agent_info["dev_branch_agent_id"]
# --- Read bot_mapping.json ---
with open("bot_mapping.json", "r") as json_file:
    bot_mapping = json.load(json_file)
    main_branch_agent_id = bot_mapping["dev"]

# --- Instantiate Cognigy Client with feature branch project ID ---
CognigyAPIClientFeature = CognigyAPIClient(
    base_url=base_url_dev,
    api_key=api_key_dev,
    project_id=dev_branch_agent_id,
    bot_name=bot_name,
    locales=None,
    playbook_prefixes=None,
    playbook_flows=None,
    max_snapshots=None,
    folder_name=feature_agent_folder
)

#Start fetching data for package creation
flow_ids = CognigyAPIClientFeature.get_flow_ids()
lexicon_ids = CognigyAPIClientFeature.get_lexicon_ids()
connection_ids = CognigyAPIClientFeature.get_connection_ids()
nlu_connector_ids = CognigyAPIClientFeature.get_nluconnector_ids()
ai_agent_ids = CognigyAPIClientFeature.get_aiagent_ids()
large_language_model_ids = CognigyAPIClientFeature.get_largelanguagemodel_ids()
knowledge_store_ids = CognigyAPIClientFeature.get_knowledgestore_ids()
function_ids = CognigyAPIClientFeature.get_function_ids()
locale_ids = CognigyAPIClientFeature.get_locale_ids()

#Combine to package ressource list
package_ressource_ids = [
    *flow_ids,
    *lexicon_ids,
    *connection_ids,
    *nlu_connector_ids,
    *ai_agent_ids,
    *large_language_model_ids,
    *knowledge_store_ids
]

# --- Extract all agent ressources by ids ---
CognigyAPIClientFeature.extract_agent_resources_by_ids(
    flow_ids=flow_ids,
    lexicon_ids=lexicon_ids,
    connection_ids=connection_ids,
    nlu_connector_ids=nlu_connector_ids,
    ai_agent_ids=ai_agent_ids,
    large_language_model_ids=large_language_model_ids,
    knowledge_store_ids=knowledge_store_ids,
    function_ids=function_ids,
    locale_ids=locale_ids
)

# --- Replace the feature bot specific ids with the original ids of the main agent ---
mapping = read_json_files_in_directory("agent", main=True)
mapping = read_json_files_in_directory("feature_agent copy", main=False, mapping=mapping)
mapping[dev_branch_agent_id] = main_branch_agent_id
replace_ids_in_json_files("feature_agent copy", mapping)

# --- Git branch validation and commit logic ---
try:
    # Attempt to switch to the specified branch
    subprocess.run(["git", "checkout", branch_name], check=True)
    print(f"Switched to branch '{branch_name}'.")
except subprocess.CalledProcessError:
    # Fail if the branch does not exist
    raise EnvironmentError(f"Branch '{branch_name}' does not exist. Ensure the branch is created before running this script.")

# Add the folder and commit changes
try:
    subprocess.run(["git", "add", feature_agent_folder], check=True)
    commit_message = f"Add extracted resources in '{feature_agent_folder}' folder"
    subprocess.run(["git", "commit", "-m", commit_message], check=True)

    # Push the changes to the branch
    subprocess.run(["git", "push", "-u", "origin", branch_name], check=True)
    print(f"Successfully committed and pushed the folder '{feature_agent_folder}' to the branch '{branch_name}'.")
except subprocess.CalledProcessError as e:
    print(f"An error occurred while committing or pushing the folder: {e}")