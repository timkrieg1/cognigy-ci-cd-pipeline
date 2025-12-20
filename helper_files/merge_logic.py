import os
import shutil
import subprocess

class MergeLogic:
    def __init__(self, bot_name, branch_name, merge_into_branch="development"):
        self.bot_name = bot_name
        self.branch_name = branch_name
        self.merge_into_branch = merge_into_branch

    def get_current_branch(self):
        """
        Get the name of the current Git branch.

        Returns:
            str: The name of the current branch.
        """
        result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=True
        )
        return result.stdout.strip()

    def extract_agent(self, source, target_folder):
        """
        Extract the 'agent' folder from a specific commit or branch.

        Args:
            source (str): The commit hash or branch name to extract from.
            target_folder (str): The folder to save the extracted 'agent' folder.
        """
        # Save the current branch
        current_branch = self.get_current_branch()
        print(f"[INFO] Current branch before checkout: {current_branch}")

        try:
            # Checkout the source branch/commit
            print(f"[INFO] Checking out source: {source}")
            subprocess.run(["git", "checkout", source], check=True)

            # Restore the 'agent' folder to its state in the specified commit
            print(f"[INFO] Restoring 'agent' folder from source: {source}")
            subprocess.run(["git", "restore", "--source", source, "--staged", "--worktree", "agent"], check=True)

            # Ensure the 'agent' folder exists and copy it to the target folder
            if os.path.exists("agent"):
                shutil.copytree("agent", target_folder)
                print(f"[INFO] Copied 'agent' folder from '{source}' to '{target_folder}'.")
            else:
                raise FileNotFoundError(f"[ERROR] 'agent' folder does not exist in '{source}'.")
        finally:
            # Switch back to the original branch
            print(f"[INFO] Switching back to the original branch: {current_branch}")
            subprocess.run(["git", "checkout", current_branch], check=True)

    def create_empty_folder(self, folder_name):
        """
        Create an empty folder.

        Args:
            folder_name (str): The name of the folder to create.
        """
        if os.path.exists(folder_name):
            shutil.rmtree(folder_name)
        os.makedirs(folder_name)
        print(f"[INFO] Created empty folder '{folder_name}'.")

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