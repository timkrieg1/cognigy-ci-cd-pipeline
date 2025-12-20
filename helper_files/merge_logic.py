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
        """Extract agent folder without changing working directory."""
        # Use git show to extract files without checkout
        subprocess.run([
            "git", "archive", source, "agent/", 
            "--format=tar", f"--output={target_folder}.tar"
        ], check=True)
        
        # Extract tar to target folder
        subprocess.run(["tar", "-xf", f"{target_folder}.tar"], check=True)
        os.rename("agent", target_folder)
        os.remove(f"{target_folder}.tar")

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