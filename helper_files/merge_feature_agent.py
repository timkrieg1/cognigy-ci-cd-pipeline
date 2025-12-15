from cognigy_client import CognigyAPIClient
from merge_logic import CognigyMergeClient
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

# --- Prepare directories ---
merge_base_dir = "merge_base_dir"
if os.path.exists(merge_base_dir):
    shutil.rmtree(merge_base_dir)
os.makedirs(merge_base_dir)

def get_merge_base(base_branch, feature_branch):
    """
    Get the merge base (common ancestor commit) between the base branch and the feature branch.

    Args:
        base_branch (str): The name of the base branch.
        feature_branch (str): The name of the feature branch.

    Returns:
        str: The merge base commit hash.
    """
    result = subprocess.run(
        ["git", "merge-base", base_branch, feature_branch],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=True
    )
    return result.stdout.strip()

def checkout_merge_base(merge_base_commit, target_dir):
    """
    Check out the repository at the merge base commit into the target directory.

    Args:
        merge_base_commit (str): The merge base commit hash.
        target_dir (str): The directory where the files will be checked out.
    """
    subprocess.run(["git", "checkout", merge_base_commit], check=True)
    subprocess.run(["cp", "-r", ".", target_dir], check=True)

def commit_merge_base_dir(target_dir):
    """
    Commit the merge_base_dir to the repository.

    Args:
        target_dir (str): The directory to commit.
    """
    subprocess.run(["git", "add", target_dir], check=True)
    subprocess.run(["git", "commit", "-m", f"Save merge base directory: {target_dir}"], check=True)
    print(f"Committed {target_dir} to the repository.")

# --- Get the merge base commit ---
merge_base_commit = get_merge_base(base_branch, branch_name)
print(f"Merge base commit: {merge_base_commit}")

# --- Check out the merge base ---
checkout_merge_base(merge_base_commit, merge_base_dir)
print(f"Checked out merge base into {merge_base_dir}")

# Commit the merge_base_dir
commit_merge_base_dir(merge_base_dir)

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

FeatureMergeClient = CognigyMergeClient(
    feature_dir=feature_agent_folder,
    base_dir=merge_base_dir,
    main_dir=agent_folder
)