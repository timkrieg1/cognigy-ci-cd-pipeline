from cognigy_client import CognigyAPIClient
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
    "MAX_SNAPSHOTS",
    "BOT_NAME"
]

# --- Find missing environment variables ---
missing_vars = [var for var in required_vars if os.getenv(var) is None]
if missing_vars:
    raise EnvironmentError(f"Missing required environment variable(s): {', '.join(missing_vars)}")

# --- Assign environment variables ---
base_url_dev = os.getenv("COGNIGY_BASE_URL_DEV")
api_key_dev = os.getenv("COGNIGY_API_KEY_DEV")
max_snapshots = int(os.getenv("MAX_SNAPSHOTS"))
bot_name = os.getenv("BOT_NAME")
branch_desc = os.getenv("BRANCH_DESC")
locale = os.getenv("LOCALE")

# --- Prepare agent folder structure ---
agent_folder = "agent"
if os.path.exists(agent_folder):
    shutil.rmtree(agent_folder)

# --- Get bot mappings ---
with open("bot_mapping.json", "r") as f:
    bot_mappings = json.load(f)

project_id_dev = bot_mappings["dev"]
locales = bot_mappings["locales"]

print(base_url_dev, api_key_dev, project_id_dev, bot_name, max_snapshots, branch_desc, locale)
# --- Instantiate Cognigy Base Client ---
CognigyAPIClientBase = CognigyAPIClient(
    base_url=base_url_dev,
    api_key=api_key_dev,
    project_id=project_id_dev,
    bot_name=bot_name,
    max_snapshots=max_snapshots,
    locales=locales
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
    resource_ids[endpoint] = CognigyAPIClientBase.get_resource_ids(endpoint)

# Flatten resource IDs for package resource list excluding functions, extensions, and locales
package_ressource_ids = [
    resource_id
    for endpoint, endpoint_ids in resource_ids.items()
    if endpoint not in ["functions", "extensions", "locales"]
    for resource_id in endpoint_ids
]

#Create package
CognigyAPIClientBase.create_package(
    resource_ids=package_ressource_ids
)

CognigyAPIClientBase.download_package()


# --- Extract all agent ressources by ids ---
CognigyAPIClientBase.extract_agent_resources_by_ids(
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
    knowledge_store_package = CognigyAPIClientBase.create_package(
        resource_ids=resource_ids.get("knowledgestores", [])
    )

    CognigyAPIClientBase.download_package(knowledge_store=True)

    CognigyAPIClientBase.download_package(knowledge_store=True)

# --- Download snapshot from base environment ---
snapshot_name = CognigyAPIClientBase.download_snapshot(
    release_description="Export Snapshot for Dev Branch Agent."
)

# --- Create new development branch agent ---
feature_branch_agent_id = CognigyAPIClientBase.create_feature_branch_agent(
    branch_desc=branch_desc,
    bot_name=bot_name,
    locale=locale
)

# --- Save feature_branch_agent_id to a JSON file ---
feature_branch_agent_info = {
    "feature_branch_agent_id": feature_branch_agent_id
}
with open("feature_branch_agent_id.json", "w") as json_file:
    json.dump(feature_branch_agent_info, json_file, indent=4)

# --- Instantiate new api client for Branch Agent ---
CognigyAPIClientFeature = CognigyAPIClient(
    base_url=base_url_dev,
    api_key=api_key_dev,
    project_id=feature_branch_agent_id,
    bot_name=f"Dev-Branch[{bot_name}][{branch_desc}]",
    max_snapshots=max_snapshots,
    locales=locales
)

# --- Upload knowledge store package ---
if os.path.exists(f"{agent_folder}/knowledge_store_package"):
    CognigyAPIClientFeature.upload_knowledge_store_package(
        knowledge_store_package_path=f"{agent_folder}/knowledge_store_package"
    )

# --- Upload snapshot to newly create agent ---
CognigyAPIClientFeature.deploy_agent()

# --- Restore snapshot in the dev branch agent ---
CognigyAPIClientFeature.restore_snapshot(
    snapshot_name=snapshot_name
)

# --- Git branch creation and commit logic ---
branch_name = f"Feature/{bot_name}-{branch_desc.replace(' ', '-')}"

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

# Ensure we are on main and up to date
subprocess.run(["git", "fetch", "--all"], check=True)
try:
    subprocess.run(["git", "checkout", "main"], check=True)
except subprocess.CalledProcessError:
    print("Branch 'main' not found, trying 'master'...")
    subprocess.run(["git", "checkout", "master"], check=True)
subprocess.run(["git", "pull", remote_name, "main"], check=True)

# Create new branch from main
subprocess.run(["git", "checkout", "-b", branch_name], check=True)

# Stage and commit new agent export and feature_branch_agent_info.json
subprocess.run(["git", "add", agent_folder, "feature_branch_agent_id.json"], check=True)
subprocess.run(["git", "commit", "-m", f"Created feature agent - {branch_name}"], check=True)

# Push the new branch
subprocess.run(["git", "push", "-u", remote_name, branch_name], check=True)
