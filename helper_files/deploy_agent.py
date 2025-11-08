import requests
import os
from dotenv import load_dotenv
import json
from cognigy_client import CognigyAPIClient

# --- Load environment variables ---
load_dotenv(override=True)

# --- Get environment variables ---
base_url_prod = os.getenv("COGNIGY_BASE_URL_PROD")
api_key_prod = os.getenv("COGNIGY_API_KEY_PROD")
bot_name = os.getenv("BOT_NAME")
max_snapshots = int(os.getenv("MAX_SNAPSHOTS"))

# --- Get bot mappings ---
with open("bot_mapping.json", "r") as f:
    bot_mappings = json.load(f)
project_id_prod = bot_mappings["prod"]
locales = bot_mappings["locales"]

# --- Instantiate Cognigy Prod Client ---
CognigyAPIClientProd = CognigyAPIClient(
    base_url=base_url_prod,
    api_key=api_key_prod,
    project_id=project_id_prod,
    bot_name=bot_name,
    max_snapshots=max_snapshots,
    locales=locales
)

# --- Deploy agent to production ---
CognigyAPIClientProd.deploy_agent()