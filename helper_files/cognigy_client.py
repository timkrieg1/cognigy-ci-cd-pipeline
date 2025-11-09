import requests
import os
import zipfile
from datetime import datetime
import re
from helper_functions import clean_base_url, retry_on_500
from typing import List, Literal
import time
from tqdm import tqdm
import json

class CognigyAPIClient:

    """A client for interacting with the Cognigy API.
    Attributes:
        base_url (str): The base URL for the Cognigy API.
        api_key (dict): The API key for authentication.
        project_id (str): The ID of the Cognigy project.
        bot_name (str): The name of the bot.
    
    Returns:
        Instance of CognigyAPIClient
    
    Methods:
        get(endpoint: str, params: dict = None) -> List[dict]:
            Sends a GET request to the specified endpoint with optional parameters.
        post(endpoint: str, data: dict = None) -> List[dict]:
            Sends a POST request to the specified endpoint with optional data.
    """

    def __init__(self,base_url: str = None, api_key: dict = None, project_id: str = None, bot_name: str = None, playbook_prefixes: List[str] = None, locales: dict = None, playbook_flows: dict = None, max_snapshots: int = None, folder_name: str = "agent"):
        # --- Validate required parameters ---
        if (not base_url or not api_key or not project_id or not bot_name):
            raise ValueError("Cannot instantiate Cognigy API Client. Base URL, API Key, and Project ID and Bot Name must be provided.")
        # --- Clean bot_name for branch safety ---
        cleaned_bot_name = re.sub(r'[^A-Za-z0-9._-]', '', bot_name.replace(' ', '-'))
        self.base_url = f"{clean_base_url(base_url)}/new/v2.0"
        self.api_key = api_key
        self.project_id = project_id
        self.bot_name = cleaned_bot_name
        self.package_name = ""
        self.snapshot_name = ""
        self.locales = locales
        self.playbook_prefixes = playbook_prefixes
        self.playbook_flows = playbook_flows
        self.max_snapshots = max_snapshots
        self.folder_name = folder_name

        # --- Set up request headers and session ---
        self.headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "X-API-KEY": self.api_key,
        }
        self.session = requests.Session()
        self.session.headers.update(self.headers)
        # --- Default query parameters for API requests ---
        self.params = {
            "limit": 100,
            "projectId": self.project_id
        }

    @retry_on_500()
    def get(self, endpoint: str, params: dict = None) -> List[dict]:
        # --- Generic GET request with pagination support ---
        url = f"{self.base_url}/{endpoint}"
        next_cursor = None
        current_params = self.params.copy() if not params else params.copy()
        all_items = []

        while True:
            if next_cursor:
                current_params["next"] = next_cursor

            # --- Fetch data from the API ---
            response = self.session.get(url = url, params=current_params)
            response.raise_for_status()  # --- Raise an error for bad responses ---
            data = response.json()
            
            items = data.get("items", [])
            all_items.extend(items)
            total = data.get("total", 0)
            next_cursor = data.get("nextCursor")

            # --- End the loop when no more pages ---
            if not next_cursor or len(items) >= total:
                break

        return all_items
        
    def get_flow_ids(self) -> List[dict]:
        """
        Fetches all flows from the Cognigy API.
        """
        flow_ids = []
        flows = self.get("flows")
        # --- Collect all flow IDs ---
        for flow in flows:
            flow_ids.append(flow["_id"])
        return flow_ids

    
    def get_lexicon_ids(self) -> List[dict]:
        """
        Fetches all lexicons from the Cognigy API.
        """
        lexcion_ids = []
        lexcions = self.get("lexicons")
        # --- Collect all lexicon IDs ---
        for lexcion in lexcions:
            lexcion_ids.append(lexcion["_id"])
        return lexcion_ids
    
    def get_nluconnector_ids(self) -> List[dict]:
        """
        Fetches all NLU connectors from the Cognigy API.
        """
        nluconnector_ids = []
        nluconnectors = self.get("nluconnectors")
        # --- Collect all NLU connector IDs ---
        for nluconnector in nluconnectors:
            nluconnector_ids.append(nluconnector["_id"])
        return nluconnector_ids

    def get_connection_ids(self) -> List[dict]:
        """
        Fetches all connections from the Cognigy API.
        """
        connection_ids = []
        connections = self.get("connections")
        # --- Collect all connection IDs ---
        for connection in connections:
            connection_ids.append(connection["_id"])
        return connection_ids

    def get_aiagent_ids(self) -> List[dict]:
        """
        Fetches all AI agents from the Cognigy API.
        """
        aiagent_ids = []
        aiagents = self.get("aiagents")
        # --- Collect all AI agent IDs ---
        for aiagent in aiagents:
            aiagent_ids.append(aiagent["_id"])
        return aiagent_ids

    def get_largelanguagemodel_ids(self) -> List[dict]:
        """
        Fetches all large language models from the Cognigy API.
        """
        llm_ids = []
        llms = self.get("largelanguagemodels")
        # --- Collect all large language model IDs ---
        for llm in llms:
            llm_ids.append(llm["_id"])
        return llm_ids

    def get_knowledgestore_ids(self) -> List[dict]:
        """
        Fetches all knowledge stores from the Cognigy API.
        """
        knowledgestore_ids = []
        knowledgestores = self.get("knowledgestores")
        # --- Collect all knowledge store IDs ---
        for knowledgestore in knowledgestores:
            knowledgestore_ids.append(knowledgestore["_id"])
        return knowledgestore_ids

    def get_function_ids(self) -> List[dict]:
        """
        Fetches all functions from the Cognigy API.
        """
        function_ids = []
        functions = self.get("functions")
        # --- Collect all function IDs ---
        for function in functions:
            function_ids.append(function["_id"])
        return function_ids

    def get_locale_ids(self) -> List[dict]:
        """
        Fetches all locales from the Cognigy API.
        """
        function_ids = []
        functions = self.get("locales")
        # --- Collect all function IDs ---
        for function in functions:
            function_ids.append(function["_id"])
        return function_ids
    
    @retry_on_500()
    def create_package(self, resource_ids: List[str]) -> dict:
        """
        Creates a new package with the specified resources.
        """
        print("Starting package creation...", flush=True)
        # --- Generate package name with timestamp ---
        now = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.package_name = f"Cognigy-CI-CD-Package_{self.bot_name}_{now}"
        payload = {
            "name": self.package_name,
            "description": "Automated package creation by CI/CD pipeline",
            "resourceIds": resource_ids,
            "projectId": self.project_id
        }

        # --- Create package via API ---
        response = self.session.post(f"{self.base_url}/packages", json=payload)
        response.raise_for_status()
        return response.json
    
    @retry_on_500()
    def download_package(self, knowledge_store: bool = False) -> dict:
        """
        Downloads the package created by the CI/CD pipeline.
        """
        # --- Fetch the latest package to get the package ID ---
        params = {
            "limit": 1,
            "projectId": self.project_id
        }
        package_id = ""

        print(f"Starting {'knowledge_store ' if knowledge_store else ''}package download", flush=True)
        while True:
            response = self.session.get(
                url=f"{self.base_url}/packages",
                params=params
            )

            response.raise_for_status()
            data = response.json().get("items", [])
            package_name = data[0].get("name", "") if len(data) > 0 else ""

            if package_name == self.package_name:
                package_id = data[0]["_id"]
                break
        # --- Download the package file with retry logic ---
        prev_size = 0
        while True:
            # --- Create download link ---
            response = self.session.post(
            url=f"{self.base_url}/packages/{package_id}/downloadLink",
            json={
                "packageId": package_id
            }
            )

            response.raise_for_status()
            download_link = response.json().get("downloadLink", "")
            # --- Download the file ---
            target_dir = os.path.join(self.folder_name, "package") if not knowledge_store else "knowledge_store_package"
            os.makedirs(target_dir, exist_ok=True)
            package_path = os.path.join(target_dir, f"{self.package_name}.zip")
            with self.session.get(download_link, stream=True) as r:
                r.raise_for_status()
                with open(package_path, "wb") as f:
                    for chunk in r.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)

            curr_size = os.path.getsize(package_path) / 1000
            print(f"Downloaded zip size: {curr_size} kilobytes")
            if curr_size == 0:
                print("Downloaded zip is empty, retrying in 5 seconds...")
                time.sleep(5)
                continue

            if prev_size == 0:
                # --- First non-empty download, check again ---
                prev_size = curr_size
                print("Zip file is not empty, checking again in 5 seconds to validate full package...")
                time.sleep(5)
                continue

            if curr_size != prev_size:
                # --- Size changed, possible background loading ---
                prev_size = curr_size
                print("Zip file size changed, checking again in 5 seconds...")
                time.sleep(5)
                continue

            print("Finished package download")
            break
            
    @retry_on_500()
    def ensure_snapshot_limit(self) -> None:
        """
        Ensures the number of snapshots does not exceed max_snapshots.
        Deletes the oldest snapshot if the limit is reached.
        """
        response = self.session.get(url=f"{self.base_url}/snapshots", params=self.params)
        response.raise_for_status()
        snapshots = response.json().get("items", [])
        print(f"Current number of snapshots: {len(snapshots)}", flush=True)
        print(f"Max allowed snapshots: {self.max_snapshots}", flush=True)

        if len(snapshots) >= int(self.max_snapshots):
            # --- Delete the oldest snapshot ---
            oldest_snapshot = snapshots[-1]
            snapshot_id = oldest_snapshot["_id"]
            delete_response = self.session.delete(url=f"{self.base_url}/snapshots/{snapshot_id}")
            delete_response.raise_for_status()
            # --- Poll until the number of snapshots is less than max_snapshots ---
            while True:
                poll_response = self.session.get(url=f"{self.base_url}/snapshots", params=self.params)
                poll_response.raise_for_status()
                poll_snapshots = poll_response.json().get("items", [])
                if len(poll_snapshots) < int(self.max_snapshots):
                    break
                time.sleep(2)
            print(f"Deleted oldest snapshot: {snapshot_id}", flush=True)

    @retry_on_500()
    def download_snapshot(self, release_description: str) -> str:
        """
        Prepares the snapshot for download.

        Args:
            release_description (str): Description for the snapshot.
        Returns:
            str: The name of the created snapshot.
        """
        print("Preparing snapshot for download...", flush=True)
        self.ensure_snapshot_limit()
        response = self.session.get(url=f"{self.base_url}/snapshots", params=self.params)
        response.raise_for_status()
        snapshots = response.json().get("items", [])

        # --- Determine the new snapshot name ---
        today_str = datetime.now().strftime("%d_%m_%Y")
        base_snapshot_name = f"{self.bot_name}_{today_str}"
        new_snapshot_name = ""
        existing_names = [s["name"] for s in snapshots if s["name"].startswith(base_snapshot_name)]
        if not existing_names:
            new_snapshot_name = base_snapshot_name
        else:
            # --- Find the next available suffix ---
            suffix = 1
            while f"{base_snapshot_name}_{suffix}" in existing_names:
                suffix += 1
            new_snapshot_name = f"{base_snapshot_name}_{suffix}"
        self.snapshot_name = new_snapshot_name
        # --- Create a new snapshot ---
        response = self.session.post(
            url=f"{self.base_url}/snapshots",
            json={
                "name": self.snapshot_name,
                "description": release_description,
                "projectId": self.project_id
            }
        )
        response.raise_for_status()
        print("Created task to create new snapshot", flush=True)
        print("Polling for snapshot to be created...", flush=True)

        # --- Get all snapshots again to get snapshot id ---
        snapshot_id = None
        while snapshot_id is None:
            response = self.session.get(url=f"{self.base_url}/snapshots", params=self.params)
            response.raise_for_status()
            snapshots = response.json().get("items", [])
            snapshot_id = next((snapshot["_id"] for snapshot in snapshots if snapshot["name"] == self.snapshot_name), None)
            if snapshot_id is None:
                print("Snapshot not found, retrying in 5 seconds...", flush=True)
                time.sleep(5)
        print(f"Snapshot was found, preparing download...", flush=True)

        # --- Package snapshot ---
        response = self.session.post(url=f"{self.base_url}/snapshots/{snapshot_id}/package")
        response.raise_for_status()

        # --- Poll for the snapshot to be packaged and download the actual snapshot file ---
        download_link_url = f"{self.base_url}/snapshots/{snapshot_id}/downloadLink"
        target_dir = os.path.join(self.folder_name, "snapshot")
        os.makedirs(target_dir, exist_ok=True)
        snapshot_path = os.path.join(target_dir, f"{self.snapshot_name}.csnap")

        while True:
            response = self.session.post(download_link_url)
            retries = 0
            max_retries = 5
            while retries < max_retries:
                try:
                    response.raise_for_status()
                    break
                except requests.exceptions.HTTPError as e:
                    if response.status_code == 409:
                        retries += 1
                        print(f"Conflict error (409) encountered. Retrying {retries}/{max_retries} in 5 seconds...", flush=True)
                        time.sleep(5)
                    else:
                        raise
            else:
                print("Max retries reached for 409 Conflict error. Raising exception.", flush=True)
                raise
            download_link = response.json().get("downloadLink", "")
            print("Attempting to download snapshot...", flush=True)

            with self.session.get(download_link, stream=True) as r:
                r.raise_for_status()
                with open(snapshot_path, "wb") as f:
                    for chunk in r.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)

                # --- Check if the file only contains the text 'csnap' ---
                with open(snapshot_path, "rb") as f:
                    content = f.read()
                    if content.strip() == b"csnap":
                        print("Downloaded file is placeholder 'csnap', retrying in 5 seconds...", flush=True)
                        time.sleep(5)
                        continue
                    else:
                        print("Snapshot downloaded successfully.", flush=True)
                        break
        return self.snapshot_name
    
    @retry_on_500()
    def run_automated_tests(self) -> None:
        """
        Runs automated tests (Cognigy Playbooks) using a predefined prefix.
        """
        print("Running automated tests...")
        # Fetch all playbooks with the specified prefix
        playbook_ids = self.fetch_playbooks_with_prefix()

        # Schedule all playbook runs
        playbook_runs = {}
        for locale, playbooks in playbook_ids.items():
            playbook_runs[locale] = []
            for playbook in playbooks:
                r = self.session.post(
                    url=f"{self.base_url}/playbooks/{playbook['playbook_id']}/schedule",
                    json={
                        "entrypoint": self.project_id,
                        "flowId": self.playbook_flows[locale],
                        "localeId": self.locales[locale],
                    }
                )
                r.raise_for_status()
                task_id = r.json().get("_id")
                
                r = self.session.get(
                    url=f"{self.base_url}/tasks/{task_id}"
                )
                r.raise_for_status()
                # Retry mechanism to get playbookRunId if not present
                retries = 0
                playbook_run_id = None
                while retries < 5:
                    playbook_run_id = r.json().get("data", {}).get("playbookRunId")
                    if playbook_run_id:
                        break
                    time.sleep(2)
                    r = self.session.get(
                        url=f"{self.base_url}/tasks/{task_id}"
                    )
                    r.raise_for_status()
                    retries += 1
                if not playbook_run_id:
                    raise RuntimeError(f"Could not retrieve playbookRunId for playbook {playbook['playbook_name']} after {retries} retries.")
                playbook_runs[locale].append({"playbook_run_id": playbook_run_id,"playbook_name": playbook["playbook_name"], "playbook_id": playbook["playbook_id"]})
                
        # Get playbook run results
        for locale, runs in playbook_runs.items():
            index = 0
            for run in runs:
                playbook_id = run["playbook_id"]
                playbook_run_id = run["playbook_run_id"]
                retries = 0
                while retries < 10:
                    r = self.session.get(
                    url=f"{self.base_url}/playbooks/{playbook_id}/runs/{playbook_run_id}"
                    )
                    
                    playbook_status = r.json().get("status", "pending")
                    
                    if playbook_status in ["successful", "failed"]:
                        playbook_runs[locale][index]["status"] = playbook_status
                        break
                    else:
                        time.sleep(2)
                        retries += 1
                if retries == 10:
                    print(f"Playbook run {playbook_run_id} for playbook {playbook_id} did not finish after 10 retries.")
                index += 1

        # Check if all playbooks passed
        all_passed = True
        for locale, runs in playbook_runs.items():
            for run in runs:
                if run.get("status") != "successful":
                    all_passed = False
                    print(f"Playbook {run['playbook_name']} ({run['playbook_id']}) failed with status: {run['status']}")
        
        return all_passed

    @retry_on_500()
    def fetch_playbooks_with_prefix(self) -> List[dict]:
        """
        Fetches playbooks with a specific prefix.

        Args:
            prefix (str): The prefix to filter playbooks by.
        Returns:
            List[dict]: A list of playbook IDs that match the prefix.
        """
        playbook_ids = {}
        playbooks = self.get("playbooks")
        
        # Iterate through all locales
        for locale in self.locales:
            playbook_ids_temp = []
            locale_prefixes = self.playbook_prefixes[locale]
            for playbook in playbooks:
                if any(sub in playbook["name"] for sub in locale_prefixes):
                    playbook_ids_temp.append({"playbook_name": playbook["name"], "playbook_id": playbook["_id"]})   
            playbook_ids[locale] = playbook_ids_temp     
        
        return playbook_ids

    def extract_agent_resources_by_ids(
        self,
        flow_ids: list[str] = [],
        lexicon_ids: list[str]= [],
        connection_ids: list[str]= [],
        nlu_connector_ids: list[str]= [],
        ai_agent_ids: list[str] = [],
        large_language_model_ids: list[str] = [],
        knowledge_store_ids: list[str] = [],
        function_ids: list[str] = [],
        locale_ids: list[str] = []
    ) -> dict:
        """
        Extracts agent resources by their IDs and returns them in a dictionary.
        """

        if len(flow_ids) > 0:
            print(f"Extracting {len(flow_ids)} flows...", flush=True)
            self.extract_flow_data(flow_ids, output_path=f"{self.folder_name}/flows")
            print("Flows extraction complete.", flush=True)
        if len(lexicon_ids) > 0:
            print(f"Extracting {len(lexicon_ids)} lexicons...", flush=True)
            self.extract_resource_data(lexicon_ids, output_path=f"{self.folder_name}/lexicons", endpoint="lexicons")
            print("Lexicons extraction complete.", flush=True)
        if len(connection_ids) > 0:
            print(f"Extracting {len(connection_ids)} connections...", flush=True)
            self.extract_resource_data(connection_ids, output_path=f"{self.folder_name}/connections", endpoint="connections")
            print("Connections extraction complete.", flush=True)
        if len(nlu_connector_ids) > 0:
            print(f"Extracting {len(nlu_connector_ids)} NLU connectors...", flush=True)
            self.extract_resource_data(nlu_connector_ids, output_path=f"{self.folder_name}/nluconnectors", endpoint="nluconnectors")
            print("NLU connectors extraction complete.", flush=True)
        if len(ai_agent_ids) > 0:
            print(f"Extracting {len(ai_agent_ids)} AI agents...", flush=True)
            self.extract_ai_agents(ai_agent_ids, output_path=f"{self.folder_name}/aiagents")
            print("AI agents extraction complete.", flush=True)
        if len(large_language_model_ids) > 0:
            print(f"Extracting {len(large_language_model_ids)} large language models...", flush=True)
            self.extract_resource_data(large_language_model_ids, output_path=f"{self.folder_name}/largelanguagemodels", endpoint="largelanguagemodels")
            print("Large language models extraction complete.", flush=True)
        if len(knowledge_store_ids) > 0:
            print(f"Extracting {len(knowledge_store_ids)} knowledge stores...", flush=True)
            self.extract_knowledge_store_data(knowledge_store_ids, output_path=f"{self.folder_name}/knowledgestores")
            print("Knowledge stores extraction complete.", flush=True)
        if len(function_ids) > 0:
            print(f"Extracting {len(function_ids)} functions...", flush=True)
            self.extract_resource_data(function_ids, output_path=f"{self.folder_name}/functions", endpoint="functions")
            print("Functions extraction complete.", flush=True)
        if len(locale_ids) > 0:
            print(f"Extracting {len(locale_ids)} locales...", flush=True)
            self.extract_resource_data(locale_ids, output_path=f"{self.folder_name}/locales", endpoint="locales")
            print("Locales extraction complete.", flush=True)

        print("All agent resources have been extracted successfully.", flush=True)
    
    @retry_on_500()
    def extract_flow_data(self, flow_ids: list[str], output_path: str) -> list[dict]:
        """
        Extracts detailed flow data for each flow ID, including metadata, chart nodes, settings, intents, and states.
        For each flow, fetches the chart and replaces each chart node with its individual node content.
        Saves the extracted data to the specified output path, organized by flow name and subdirectories.
        Args:
            flow_ids (list[str]): List of flow IDs to extract.
            output_path (str): Directory path to save the extracted flow data.
        Returns:
            None
        """
        all_flow_data = {}
        # --- Iterate over flows with progress bar for extraction ---
        for flow_id in tqdm(flow_ids, desc="Extracting flows", unit="flow"):
            flow_data = {
                "metadata": {},
                "chart": [],
                "settings": {},
                "intents": {},
                "states": {},
            }

            # --- Flow metadata ---
            r = self.session.get(
                url=f"{self.base_url}/flows/{flow_id}"
            )
            r.raise_for_status()
            flow_data["metadata"] = r.json()

            # --- Flow settings ---
            r = self.session.get(
                url=f"{self.base_url}/flows/{flow_id}/settings"
            )
            r.raise_for_status()
            flow_data["settings"] = r.json()

            # --- Flow Chart ---
            r = self.session.get(
                url=f"{self.base_url}/flows/{flow_id}/chart"
            )
            r.raise_for_status()
            chart = r.json().get("relations")

            # --- Rename node to _id because _id key does not show the real node id ---
            for subobject in chart:
                if "_id" in subobject:
                    del subobject["_id"]
                if "node" in subobject:
                    subobject["_id"] = subobject.pop("node")
            

            # --- Fetch each node in the chart and add it to the chart data ---
            chart_nodes_data = []
            for node in chart:
                r = self.session.get(
                    url=f"{self.base_url}/flows/{flow_id}/chart/nodes/{node['node']}"
                )
                r.raise_for_status()
                node_data = r.json()
                node["_data"] = node_data
                chart_nodes_data.append(node)
            flow_data["chart"] = chart_nodes_data

            # --- Flow Intents ---
            all_intents = {}
            intents = self.get(f"flows/{flow_id}/intents")
            # --- Get intent training data ---
            for intent in intents:
                training_sentences = self.get(f"flows/{flow_id}/intents/{intent['_id']}/sentences")
                all_intents[intent["name"]] = {
                    "metadata": intent,
                    "training_sentences": training_sentences
                }
            flow_data["intents"] = all_intents

            # --- Flow States ---
            all_states = {}
            states = self.get(f"flows/{flow_id}/states", params={"limit": 100})
            for state in states:
                r = self.session.get(url=f"{self.base_url}/flows/{flow_id}/states/{state['_id']}")
                r.raise_for_status()
                state_data = r.json()
                all_states[state_data["name"]] = state_data
            flow_data["states"] = all_states
            
            all_flow_data[flow_data["metadata"]["name"]] = flow_data
        
        # --- Write to output dictionary ---
        for flow_name, flow_data in all_flow_data.items():
            flow_main_folder_path = os.path.join(output_path, flow_name)
            os.makedirs(flow_main_folder_path, exist_ok=True)
            for sub_directory, content in flow_data.items():
                flow_sub_dir_path = os.path.join(flow_main_folder_path, sub_directory)
                os.makedirs(flow_sub_dir_path, exist_ok=True)
                file_path = os.path.join(flow_sub_dir_path, f"{sub_directory}.json")
                with open(file_path, "w", encoding="utf-8") as f:
                    json.dump(content, f, indent=4, ensure_ascii=False)

    @retry_on_500()
    def extract_resource_data(self, resource_ids: list[str], output_path: str, endpoint: str) -> None:
        """
        Extracts resource data by their IDs and saves them to the specified output path.

        Args:
            resource_ids (list[str]): List of resource IDs to extract.
            output_path (str): Directory path to save the extracted resource data.
            endpoint (str): API endpoint for the resource type (e.g., 'lexicons', 'connections').
        """
        all_resource_data = {}
        # --- Iterate over resources with progress bar for extraction ---
        for resource_id in tqdm(resource_ids, desc=f"Extracting {endpoint}", unit=endpoint[:-1] if endpoint.endswith('s') else endpoint):
            r = self.session.get(
                url=f"{self.base_url}/{endpoint}/{resource_id}"
            )
            r.raise_for_status()
            resource_data = r.json()
            all_resource_data[resource_data["name"]] = resource_data

        os.makedirs(output_path, exist_ok=True)
        for resource_name, resource_data in all_resource_data.items():
            file_path = os.path.join(output_path, f"{resource_name}.json")
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(resource_data, f, indent=4, ensure_ascii=False)
    
    @retry_on_500()
    def extract_knowledge_store_data(self, knowledge_store_ids: list[str], output_path: str) -> None:
        """
        Extracts knowledge store data by their IDs and saves them to the specified output path.

        Args:
            knowledge_store_ids (list[str]): List of knowledge store IDs to extract.
            output_path (str): Directory path to save the extracted knowledge store data.
        """

        all_knowledge_store_data = {}
        # --- Iterate over knowledge stores with progress bar for extraction ---
        for knowledge_store_id in tqdm(knowledge_store_ids, desc="Extracting knowledge stores", unit="store"):
            # --- Fetch knowledge store metadata ---
            knowledge_store_data = {
                "metadata": {},
                "knowledge_sources": {}
            }

            r = self.session.get(
                url=f"{self.base_url}/knowledgestores/{knowledge_store_id}"
            )
            r.raise_for_status()
            knowledge_store_data_metadata = r.json()
            knowledge_store_data["metadata"] = knowledge_store_data_metadata

            # --- Fetch knowledge sources ---
            knowledge_sources = self.get(f"knowledgestores/{knowledge_store_id}/sources", params={"limit": 100})
            for source in knowledge_sources:
                # --- Fetch content for each source ---
                chunks = self.get(f"knowledgestores/{knowledge_store_id}/sources/{source['_id']}/chunks", params={"limit": 100})
                source["chunks"] = chunks
                knowledge_store_data["knowledge_sources"][source["name"]] = source

            # --- Save knowledge store data ---
            all_knowledge_store_data[knowledge_store_data["metadata"]["name"]] = knowledge_store_data

        # --- Write to output dictionary ---
        output_path = f"{self.folder_name}/knowledgestores"
        os.makedirs(output_path, exist_ok=True)
        for store_name, store_data in all_knowledge_store_data.items():
            # --- Create a subdirectory for each knowledge store ---
            store_sub_dir = os.path.join(output_path, store_name)
            os.makedirs(store_sub_dir, exist_ok=True)
            # --- Save the metadata of the knowledge store ---
            metadata_file_path = os.path.join(store_sub_dir, "metadata.json")
            with open(metadata_file_path, "w", encoding="utf-8") as f:
                json.dump(store_data["metadata"], f, indent=4, ensure_ascii=False)
            # --- Save each knowledge source in its own file ---
            for knowledge_source_name, source_data in store_data["knowledge_sources"].items():
                source_file_path = os.path.join(store_sub_dir, f"{knowledge_source_name}.json")
                with open(source_file_path, "w", encoding="utf-8") as f:
                    json.dump(source_data, f, indent=4, ensure_ascii=False)

    @retry_on_500()
    def extract_ai_agents(self, ai_agent_ids: list[str], output_path: str) -> None:
        """
        Extracts aiAgents and all jobs by their IDs and saves them to the specified output path.

        Args:
            ai_agent_ids (list[str]): List of aiAgent IDs to extract.
            output_path (str): Directory path to save the aiAgent store data.
        """

        all_ai_agent_data = {}
        # --- Iterate over aiAgents with progress bar for extraction ---
        for ai_agent_id in tqdm(ai_agent_ids, desc="Extracting aiAgents", unit="aiAgent"):
            r = self.session.get(
                url=f"{self.base_url}/aiagents/{ai_agent_id}"
            )
            r.raise_for_status()
            ai_agent_data = r.json()
            all_ai_agent_data[ai_agent_data["name"]] = {"config": ai_agent_data}

            # --- Fetch jobs for each aiAgent ---
            r = self.session.get(
                url=f"{self.base_url}/aiagents/{ai_agent_id}/jobs"
            )
            r.raise_for_status()
            jobs = r.json()
            all_ai_agent_data[ai_agent_data["name"]]["jobs"] = jobs
            

        os.makedirs(output_path, exist_ok=True)
        for ai_agent_name, ai_agent_data in all_ai_agent_data.items():
            # --- Save aiAgent config to json file ---
            ai_agent_path = os.path.join(output_path, ai_agent_name)
            os.makedirs(ai_agent_path, exist_ok=True)
            with open(f"{ai_agent_path}/config.json", "w", encoding="utf-8") as f:
                json.dump(ai_agent_data, f, indent=4, ensure_ascii=False)
            # --- Create subdirectory for jobs ---
            ai_agent_jobs_path = os.path.join(output_path, f"{ai_agent_name}", "jobs")
            os.makedirs(ai_agent_jobs_path, exist_ok=True)
            
            index = 0
            for job in ai_agent_data.get("jobs", []):
                # --- Create subdirectory for each job ---
                job_name = f"{job['config']['name']}_{index}"
                job_path = os.path.join(ai_agent_jobs_path, job_name)
                os.makedirs(job_path, exist_ok=True)
                # --- Create job config json ---
                job_config_file_path = os.path.join(job_path, "config.json")
                with open(job_config_file_path, "w", encoding="utf-8") as f:
                    json.dump(job["config"], f, indent=4, ensure_ascii=False)

                # --- Create tools subdirectory ---
                job_tools_path = os.path.join(job_path, "tools")
                os.makedirs(job_tools_path, exist_ok=True)
                # --- Save each tool to a json file ---
                tool_index = 0
                for tool in job.get("tools", []):
                    tool_file_path = os.path.join(job_tools_path, f"{tool['config']['toolId']}_{tool_index}.json")
                    with open(tool_file_path, "w", encoding="utf-8") as f:
                        json.dump(tool, f, indent=4, ensure_ascii=False)

                    tool_index += 1

                index += 1


    
    @retry_on_500()
    def deploy_agent(self) -> None:
        """
        Deploys the agent to prod.
        Snapshot from agent directory is used
        """
        print("Deploying agent...")

        # --- Ensure snapshot exists in agent directory exists ---
        snapshot_dir = os.path.join(self.folder_name, "snapshot")
        csnap_files = [f for f in os.listdir(snapshot_dir) if f.endswith('.csnap')]
        if not csnap_files:
            raise FileNotFoundError(f"No .csnap file found in the {self.folder_name}/snapshot directory.")
        if len(csnap_files) > 1:
            raise RuntimeError(f"Multiple .csnap files found in the {self.folder_name}/snapshot directory. There should be only one.")

        # --- Check if max snapshots is reached, else delete oldest snapshot ---
        self.ensure_snapshot_limit()

        # --- Deploy snapshot to prod ---
        csnap_file_path = os.path.join(snapshot_dir, csnap_files[0])
        files = {
            'file': open(csnap_file_path, "rb")
        }

        data = {
            'projectId': self.project_id,
        }

        r = requests.post(
            url=f"{self.base_url}/snapshots/upload",
            data=data,
            files=files,
            headers={"X-API-KEY": self.api_key}
        )
        r.raise_for_status()

        print("Agent deployed successfully.")

    def create_dev_branch_agent(self, branch_desc: str, bot_name: str, locale: Literal["de-DE", "en-US"]) -> str:
        """
        Creates a dev branch agent

        Args:
            dev_branch_name (str): The name of the development branch.
            bot_name (str): The name of the bot.

        Returns:
            project_id (str): The ID of the created development branch agent.
        """
        branch_agent_name = f"Dev-Branch[{bot_name}][{branch_desc}]"

        url = f"{self.base_url}/projects"
        post_body = {
            "name": branch_agent_name,
            "color": "purple",
            "locale": locale
        }

        r = self.session.post(
            url=url,
            json=post_body
        )

        r.raise_for_status()
        project_id = r.json().get("_id", "")

        if (not project_id):
            raise RuntimeError("Could not create development branch agent.")
        
        return project_id

    def restore_snapshot(self, snapshot_name: str) -> None:
        """
        Restores a snapshot in the current project.

        Args:
            snapshot_name (str): The name of the snapshot to restore.
        """
        print(f"Restoring snapshot: {snapshot_name}")

        # --- Fetch all snapshots to get snapshot id ---
        snapshot_id = None
        while snapshot_id is None:
            response = self.session.get(url=f"{self.base_url}/snapshots", params=self.params)
            response.raise_for_status()
            snapshots = response.json().get("items", [])
            snapshot_id = next((snapshot["_id"] for snapshot in snapshots if snapshot["name"] == snapshot_name), None)
            if snapshot_id is None:
                print("Waiting for snapshot upload, retrying in 5 seconds...", flush=True)
                time.sleep(5)
        
        # --- Restore the snapshot ---
        response = self.session.post(
            url=f"{self.base_url}/snapshots/{snapshot_id}/restore",
            json={
                "projectId": self.project_id
            }
        )
        response.raise_for_status()
        print("Snapshot restore initiated successfully.", flush=True)