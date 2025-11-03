from helper_functions import CognigyAPIClient
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

# --- Download snapshot from base environment ---
CognigyAPIClientBase.download_snapshot(release_description="Export Snapshot for Dev Branch Agent.")

# --- Create new development branch agent ---
dev_branch_agent_id = CognigyAPIClientBase.create_dev_branch_agent(branch_desc=branch_desc, bot_name=bot_name, locale=locale)

# --- Instantiate new api client for Branch Agent ---
CognigyAPIClientBranch = CognigyAPIClient(
    base_url=base_url_dev,
    api_key=api_key_dev,
    project_id=dev_branch_agent_id,
    bot_name=f"Dev-Branch[{bot_name}][{branch_desc}]",
    max_snapshots=max_snapshots,
    locales=locales
)

# --- Upload snapshot to newly create agent ---
CognigyAPIClientBranch.deploy_agent()