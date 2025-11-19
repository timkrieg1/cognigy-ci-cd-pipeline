import requests
import os
from dotenv import load_dotenv
import json
from cognigy_client import CognigyAPIClient

# --- Load environment variables ---
load_dotenv(override=True)

# --- Get bot mappings ---
with open("bot_mapping.json", "r") as f:
    bot_mappings = json.load(f)
locales = bot_mappings["locales"]

# --- Get environment variables ---
bot_name = os.getenv("BOT_NAME")
max_snapshots = int(os.getenv("MAX_SNAPSHOTS"))
head_branch = os.getenv("HEAD_BRANCH")
base_branch = os.getenv("BASE_BRANCH")
if head_branch == "development" and base_branch == "integration":
    project_id = bot_mappings["test"]
    base_url = os.getenv("COGNIGY_BASE_URL_TEST")
    api_key = os.getenv("COGNIGY_API_KEY_TEST")
elif head_branch == "integration" and base_branch == "production":
    project_id = bot_mappings["prod"]
    base_url = os.getenv("COGNIGY_BASE_URL_PROD")
    api_key = os.getenv("COGNIGY_API_KEY_PROD")
else:
    raise EnvironmentError(f"Invalid branch configuration for deployment. HEAD_BRANCH: {head_branch}, BASE_BRANCH: {base_branch}")

# --- Instantiate Cognigy Prod Client ---
CognigyAPIClient = CognigyAPIClient(
    base_url=base_url,
    api_key=api_key,
    project_id=project_id,
    bot_name=bot_name,
    max_snapshots=max_snapshots,
    locales=locales
)

# --- Deploy agent to production ---
CognigyAPIClient.deploy_agent()

print(f"Agent successfully deployed to {'integration' if base_branch == 'integration' else 'production'} environment.")