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
bot_name = os.getenv("BOT_NAME")
max_snapshots = int(os.getenv("MAX_SNAPSHOTS"))
release_description = f"Syncing Repository - {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S %Z')}"

# --- Get bot mappings ---
with open("bot_mapping.json", "r") as f:
    bot_mappings = json.load(f)

project_id_dev = bot_mappings["dev"]
locales = bot_mappings["locales"]

# --- Prepare agent folder structure ---
agent_folder = "agent"
if os.path.exists(agent_folder):
    shutil.rmtree(agent_folder)

# --- Instantiate Cognigy Dev Client ---
CognigyAPIClientDev = CognigyAPIClient(
    base_url=base_url_dev,
    api_key=api_key_dev,
    project_id=project_id_dev,
    bot_name=bot_name,
    locales=locales,
    playbook_prefixes=None,
    playbook_flows=None,
    max_snapshots=max_snapshots,
)

#Start fetching data for package creation
resource_endpoints = [
    "flows",
    "lexicons",
    "connections",
    "nluconnectors",
    "aiagents",
    "largelanguagemodels",
    "knowledgestores"
    "functions",
    "locales",
    "extensions"
]

resource_ids = {}
for endpoint in resource_endpoints:
    resource_ids[endpoint] = CognigyAPIClientDev.get_resource_ids(endpoint)

# Flatten resource IDs for package resource list
package_ressource_ids = [
    resource_id
    for endpoint_ids in resource_ids.values()
    for resource_id in endpoint_ids
]

#Create package
CognigyAPIClientDev.create_package(
    resource_ids=package_ressource_ids
)

CognigyAPIClientDev.download_package()

snapshot_name = CognigyAPIClientDev.download_snapshot(
    release_description=release_description
)

# --- Extract all agent ressources by ids ---
CognigyAPIClientDev.extract_agent_resources_by_ids(
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

# --- Git branch creation and commit logic ---
# Replace spaces with hyphens in the branch name
branch_name = f"{snapshot_name}_Repo_Sync".replace(" ", "-")

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

# Stage and commit new agent export
subprocess.run(["git", "add", agent_folder], check=True)
subprocess.run(["git", "commit", "-m", f"Update agent export for {bot_name}"], check=True)

# Push the new branch
subprocess.run(["git", "push", "-u", remote_name, branch_name], check=True)

