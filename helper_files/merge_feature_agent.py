from cognigy_client import CognigyAPIClient
from merge_logic import MergeLogic
from helper_functions import replace_ids_in_feature_directory
from dotenv import load_dotenv
import os
import shutil
import subprocess
import json
import sys
from datetime import datetime, timezone
import zipfile

# --- Load environment variables ---
load_dotenv(override=True)

# --- Check for required environment variables ---
required_vars = [
    "COGNIGY_BASE_URL_DEV",
    "COGNIGY_API_KEY_DEV",
    "BOT_NAME",
    "BRANCH_NAME",
    "MAX_SNAPSHOTS"
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
max_snapshots = int(os.getenv("MAX_SNAPSHOTS"))
merge_into_branch = "development"  # Default branch where the merge is going

# --- Initialize MergeLogic ---
merge_logic = MergeLogic(bot_name, branch_name, merge_into_branch)

# --- Main Logic ---
# Clear the 'agent' folder
agent_folder = "agent"
if os.path.exists(agent_folder):
    shutil.rmtree(agent_folder)

# Extract the 'agent' folder from the original commit to 'base_agent'
original_commit = merge_logic.find_original_commit()
merge_logic.extract_agent(original_commit, "base_agent")

# Extract the 'agent' folder from the 'development' branch to 'dev_agent'
merge_logic.extract_agent(merge_into_branch, "dev_agent")


# --- Prepare agent folder structure ---
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
    max_snapshots=max_snapshots,
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
    resource_ids[endpoint] = CognigyAPIClientFeature.get_resource_ids(endpoint)

# Flatten resource IDs for package resource list excluding functions, extensions, and locales
package_ressource_ids = [
    resource_id
    for endpoint, endpoint_ids in resource_ids.items()
    if endpoint not in ["functions", "extensions", "locales"]
    for resource_id in endpoint_ids
]

#Create package
CognigyAPIClientFeature.create_package(
    resource_ids=package_ressource_ids
)

CognigyAPIClientFeature.download_package()

# --- Extract all agent ressources by ids ---
CognigyAPIClientFeature.extract_agent_resources_by_ids(
    flow_ids=resource_ids.get("flows", []),
    lexicon_ids=resource_ids.get("lexicons", []),
    connection_ids=resource_ids.get("connections", []),
    nlu_connector_ids=resource_ids.get("nluConnectors", []),
    ai_agent_ids=resource_ids.get("aiagents", []),
    large_language_model_ids=resource_ids.get("largelanguagemodels", []),
    knowledge_store_ids=resource_ids.get("knowledgestores", []),
    function_ids=resource_ids.get("functions", []),
    locale_ids=resource_ids.get("locales", []),
    extension_ids=resource_ids.get("extensions", [])
)

if not resource_ids.get("knowledgestores", []) is None and len(resource_ids.get("knowledgestores", [])) > 0:
    # --- Download knowledge store package ---
    knowledge_store_package = CognigyAPIClientFeature.create_package(
        resource_ids=resource_ids.get("knowledgestores", [])
    )

    CognigyAPIClientFeature.download_package(knowledge_store=True)

# --- Download snapshot from base environment ---
snapshot_name = CognigyAPIClientFeature.download_snapshot(
    release_description="Export Snapshot for Feature Branch Agent."
)

""" FeatureMergeClient = CognigyMergeClient(
    feature_dir=feature_agent_folder,
    base_dir=merge_base_dir,
    main_dir=agent_folder
) """

# Detect CI/CD environment and configure git/remote dynamically
if os.getenv("GITHUB_ACTIONS", "").lower() == "true":
    print("Running in GitHub Actions environment.")
    remote_name = "origin"
    user_email = "actions@github.com"
    user_name = "github-actions"
elif os.getenv("TF_BUILD", "").lower() == "true":
    print("Running in Azure DevOps environment.")
    remote_name = "origin"
    user_email = "azure-pipelines@devops.com"
    user_name = "azure-pipelines"
else:
    print("Running in local environment.")
    remote_name = "origin"
    user_email = "local@user.com"
    user_name = "local-user"

# Git config
subprocess.run(["git", "config", "--global", "user.email", user_email], check=True)
subprocess.run(["git", "config", "--global", "user.name", user_name], check=True)

subprocess.run(["git", "fetch", "--all"], check=True)
try:
    subprocess.run(["git", "checkout", branch_name], check=True)
except subprocess.CalledProcessError:
    print(f"Branch {branch_name} not found")
subprocess.run(["git", "pull", remote_name, branch_name], check=True)

# Stage and commit new agent export
subprocess.run(["git", "add", "--all"], check=True)  # Stage all changes
subprocess.run(["git", "commit", "-m", f"Update agent export for {bot_name}"], check=True)

# Push changes to the existing branch
subprocess.run(["git", "push", remote_name, branch_name], check=True)
