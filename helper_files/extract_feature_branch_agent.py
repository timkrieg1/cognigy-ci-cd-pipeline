from cognigy_client import CognigyAPIClient
from helper_functions import replace_ids_in_feature_directory
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
agent_folder = "agent"
feature_agent_folder = "feature_agent"
if os.path.exists(feature_agent_folder):
    shutil.rmtree(feature_agent_folder)

# --- Read feature_branch_agent_id.json ---
with open("feature_branch_agent_id.json", "r") as json_file:
    feature_branch_agent_info = json.load(json_file)
    feature_branch_agent_id = feature_branch_agent_info["feature_branch_agent_id"]
# --- Read bot_mapping.json ---
with open("bot_mapping.json", "r") as json_file:
    bot_mapping = json.load(json_file)
    main_branch_agent_id = bot_mapping["dev"]

# --- Instantiate Cognigy Client with feature branch project ID ---
CognigyAPIClientFeature = CognigyAPIClient(
    base_url=base_url_dev,
    api_key=api_key_dev,
    project_id=feature_branch_agent_id,
    bot_name=bot_name,
    locales=None,
    playbook_prefixes=None,
    playbook_flows=None,
    max_snapshots=None,
    folder_name=feature_agent_folder
)

#Start fetching data for package creation
resource_endpoints = [
    "flows",
    "lexicons",
    "connections",
    "nluconnectors",
    "aiagents",
    "largelanguagemodels",
    "knowledgestores",
    "functions",
    "locales",
    "extensions"
]

resource_ids = {}
for endpoint in resource_endpoints:
    if endpoint != "functions" and endpoint != "extenisons":
        resource_ids[endpoint] = CognigyAPIClientFeature.get_resource_ids(endpoint)

# Flatten resource IDs for package resource list
package_ressource_ids = [
    resource_id
    for endpoint_ids in resource_ids.values()
    for resource_id in endpoint_ids
]

# --- Extract all agent ressources by ids ---
CognigyAPIClientFeature.extract_agent_resources_by_ids(
    flow_ids=resource_ids.get("flows", []),
    lexicon_ids=resource_ids.get("lexicons", []),
    connection_ids=resource_ids.get("connections", []),
    nlu_connector_ids=resource_ids.get("nluConnectors", []),
    ai_agent_ids=resource_ids.get("aiAgents", []),
    large_language_model_ids=resource_ids.get("largeLanguageModels", []),
    knowledge_store_ids=resource_ids.get("knowledgeStores", []),
    function_ids=resource_ids.get("functions", []),
    locale_ids=resource_ids.get("locales", []),
    extension_ids=resource_ids.get("extensions", [])
)

# --- Replace the feature bot specific ids with the original ids of the main agent ---
replace_ids_in_feature_directory(agent_folder, feature_agent_folder, feature_branch_agent_id, main_branch_agent_id)

# --- Replace the agent folder with the feature_agent folder ---
if os.path.exists(agent_folder):
    shutil.rmtree(agent_folder)  # Remove the existing agent folder
shutil.copytree(feature_agent_folder, agent_folder)  # Copy feature_agent to agent
shutil.rmtree(feature_agent_folder)  # Remove the feature_agent folder after copying
print(f"Replaced the '{agent_folder}' folder with the contents of the '{feature_agent_folder}' folder.")

# --- Git branch validation and commit logic ---
try:
    # Attempt to switch to the specified branch
    subprocess.run(["git", "checkout", branch_name], check=True)
    print(f"Switched to branch '{branch_name}'.")
except subprocess.CalledProcessError:
    # Fail if the branch does not exist
    raise EnvironmentError(f"Branch '{branch_name}' does not exist. Ensure the branch is created before running this script.")

# Add all changes (including deletions) and commit
try:
    subprocess.run(["git", "add", "--all"], check=True)  # Stage all changes
    commit_message = f"Replace '{agent_folder}' folder with updated contents"
    subprocess.run(["git", "commit", "-m", commit_message], check=True)

    # Push the changes to the branch
    subprocess.run(["git", "push", "-u", "origin", branch_name], check=True)
    print(f"Successfully committed and pushed all changes to the branch '{branch_name}'.")
except subprocess.CalledProcessError as e:
    print(f"An error occurred while committing or pushing changes: {e}")

