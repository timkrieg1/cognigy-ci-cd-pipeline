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
flow_ids = CognigyAPIClientDev.get_flow_ids()
lexicon_ids = CognigyAPIClientDev.get_lexicon_ids()
connection_ids = CognigyAPIClientDev.get_connection_ids()
nlu_connector_ids = CognigyAPIClientDev.get_nluconnector_ids()
ai_agent_ids = CognigyAPIClientDev.get_aiagent_ids()
large_language_model_ids = CognigyAPIClientDev.get_largelanguagemodel_ids()
knowledge_store_ids = CognigyAPIClientDev.get_knowledgestore_ids()
function_ids = CognigyAPIClientDev.get_function_ids()
locale_ids = CognigyAPIClientDev.get_locale_ids()

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
""" 
#Create package
CognigyAPIClientDev.create_package(
    resource_ids=package_ressource_ids
)

CognigyAPIClientDev.download_package()

snapshot_name = CognigyAPIClientDev.download_snapshot(
    release_description=release_description
) """

# --- Extract all agent ressources by ids ---
CognigyAPIClientDev.extract_agent_resources_by_ids(
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
