from helper_files.cognigy_client import CognigyAPIClient
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
    "COGNIGY_BASE_URL_PROD",
    "COGNIGY_API_KEY_DEV",
    "COGNIGY_API_KEY_PROD",
    "MAX_SNAPSHOTS",
    "BOT_NAME",
    "RELEASE_DESCRIPTION",
    "RUN_AUTOMATED_TEST",
]

# --- Find missing environment variables ---
missing_vars = [var for var in required_vars if os.getenv(var) is None]
if missing_vars:
    raise EnvironmentError(f"Missing required environment variable(s): {', '.join(missing_vars)}")

# --- Assign environment variables ---
base_url_dev = os.getenv("COGNIGY_BASE_URL_DEV")
base_url_test = os.getenv("COGNIGY_BASE_URL_TEST")
api_key_dev = os.getenv("COGNIGY_API_KEY_DEV")
api_key_test = os.getenv("COGNIGY_API_KEY_TEST")
bot_name = os.getenv("BOT_NAME")
max_snapshots = int(os.getenv("MAX_SNAPSHOTS"))
release_description = os.getenv("RELEASE_DESCRIPTION")
run_automated_test = os.getenv("RUN_AUTOMATED_TEST").lower() == "true"

print(f"Automated Testing: {run_automated_test}")
# --- Get bot mappings ---
with open("bot_mapping.json", "r") as f:
    bot_mappings = json.load(f)

project_id_dev = bot_mappings["dev"]
project_id_test = bot_mappings["test"]
locales = bot_mappings["locales"]
playbook_prefixes = bot_mappings.get("playbook_prefixes", None)
playbook_flows = bot_mappings.get("playbook_flow", None)

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
    playbook_prefixes=playbook_prefixes if run_automated_test else None,
    playbook_flows=playbook_flows if run_automated_test else None,
    max_snapshots=max_snapshots,
)

# --- Run automated tests ---
if run_automated_test:
    automated_tests_passed = CognigyAPIClientDev.run_automated_tests()
    try:
        if not automated_tests_passed:
            raise RuntimeError("Automated tests failed. Agent extraction aborted.")
    except RuntimeError as e:
        print(e)
        sys.exit(1)

    print("Automated tests passed successfully.")

#Start fetching data for package creation
flow_ids = CognigyAPIClientDev.get_flow_ids()
lexicon_ids = CognigyAPIClientDev.get_lexicon_ids()
connection_ids = CognigyAPIClientDev.get_connection_ids()
nlu_connector_ids = CognigyAPIClientDev.get_nluconnector_ids()
ai_agent_ids = CognigyAPIClientDev.get_aiagent_ids()
large_language_model_ids = CognigyAPIClientDev.get_largelanguagemodel_ids()
knowledge_store_ids = CognigyAPIClientDev.get_knowledgestore_ids()
function_ids = CognigyAPIClientDev.get_function_ids()

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
    flow_ids=flow_ids,
    lexicon_ids=lexicon_ids,
    connection_ids=connection_ids,
    nlu_connector_ids=nlu_connector_ids,
    ai_agent_ids=ai_agent_ids,
    large_language_model_ids=large_language_model_ids,
    knowledge_store_ids=knowledge_store_ids,
    function_ids=function_ids
)

# --- Git branch creation and commit logic ---
branch_name = snapshot_name

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

