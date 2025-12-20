import os
import shutil
import subprocess

class MergeLogic:
    def __init__(self, bot_name, branch_name, merge_into_branch="development"):
        self.bot_name = bot_name
        self.branch_name = branch_name
        self.merge_into_branch = merge_into_branch

    def clear_agent_folder(self):
        """Clear the 'agent' folder if it exists."""
        agent_folder = "agent"
        if os.path.exists(agent_folder):
            shutil.rmtree(agent_folder)
            print(f"Cleared '{agent_folder}' folder.")

    def extract_agent(self, source, target_folder):
        """
        Extract the 'agent' folder from a specific commit or branch.

        Args:
            source (str): The commit hash or branch name to extract from.
            target_folder (str): The folder to save the extracted 'agent' folder.
        """
        subprocess.run(["git", "checkout", source], check=True)
        if os.path.exists("agent"):
            shutil.copytree("agent", target_folder)
            print(f"Copied 'agent' folder from '{source}' to '{target_folder}'.")
        else:
            raise FileNotFoundError(f"'agent' folder does not exist in '{source}'.")

    def create_empty_folder(self, folder_name):
        """
        Create an empty folder.

        Args:
            folder_name (str): The name of the folder to create.
        """
        if os.path.exists(folder_name):
            shutil.rmtree(folder_name)
        os.makedirs(folder_name)
        print(f"Created empty folder '{folder_name}'.")


    def find_original_commit(self):
        """
        Find the commit where the feature branch was created.

        Returns:
            str: The commit hash of the common ancestor between the feature branch and the parent branch.
        """
        result = subprocess.run(
            ["git", "merge-base", self.branch_name, self.merge_into_branch],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=True
        )
        return result.stdout.strip()