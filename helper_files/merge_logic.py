import os
import filecmp
import shutil
import zipfile
import subprocess

class CognigyMergeClient:
    def __init__(self, feature_dir, base_dir, main_dir):
        self.feature_dir = feature_dir
        self.base_dir = base_dir
        self.main_dir = main_dir

        dirs = [self.feature_dir, self.base_dir, self.main_dir]
        for dir in dirs:
            if not os.path.exists(dir):
                raise FileNotFoundError(f"The directory {dir} does not exist.")
            # Extract the package zip folder
            self.extract_zip(os.path.join(dir, "package"), os.path.join(dir, "extractedPackage"))
        

    def extract_zip(self, directory, extract_to):
        """
        Finds a single zip file in the directory and extracts it to the specified location.

        Args:
            directory (str): Directory to search for the zip file.
            extract_to (str): Directory where the contents will be extracted.
        """
        if not os.path.exists(directory):
            raise FileNotFoundError(f"The directory {directory} does not exist.")
        
        zip_files = [f for f in os.listdir(directory) if f.endswith('.zip')]
        
        if len(zip_files) == 0:
            raise FileNotFoundError("No zip files found in the directory.")
        elif len(zip_files) > 1:
            raise ValueError("Multiple zip files found in the directory. Ensure only one zip file is present.")
        
        zip_path = os.path.join(directory, zip_files[0])
        
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(extract_to)
        print(f"Extracted {zip_path} to {extract_to}")


    # Fetch package folder from the base branch
    def fetch_package_from_base(base_branch, save_to):
        """
        Fetches the package folder from the base branch and saves to a specified directory.

        Args:
            base_branch (str): The name of the base branch.
            save_to (str): Directory where the fetched files will be saved.
        """
        if not os.path.exists(save_to):
            os.makedirs(save_to)

        try:
            subprocess.run(["git", "checkout", base_branch, "--", "package"], check=True)
            print(f"Fetched package folder from {base_branch}")
            # Copy the fetched file to the save_to directory
            shutil.copy("package", save_to)
            print(f"Saved package folder to {save_to}")
        except subprocess.CalledProcessError as e:
            print(f"Failed to fetch package folder from {base_branch}: {e}")
        except FileNotFoundError as e:
            print(f"Failed to save package folder to {save_to}: {e}")