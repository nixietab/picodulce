import json
import logging
import os
import shutil
import requests
from PyQt5.QtWidgets import QMessageBox

class UpdateChecker:
    def __init__(self, parent=None):
        self.parent = parent
        # Base repo URL for raw content
        self.base_url = "https://raw.githubusercontent.com/nixietab/picodulce/updates-v2/"
        # Default paths for version and config files
        self.version_path = "assets/data.json"  # New default path for version info
        self.config_path = "config.json"

    def check_for_update_start(self):
        try:
            # First try to read from the assets/data.json path
            local_version_info = self.read_local_version()
            if not local_version_info:
                # If not found, try the root version.json as fallback
                self.version_path = "version.json"
                local_version_info = self.read_local_version()

            if local_version_info:
                local_version = local_version_info.get("version")
                local_version_bleeding = local_version_info.get("versionBleeding")
                logging.info(f"Local version: {local_version}")
                logging.info(f"Local bleeding version: {local_version_bleeding}")

                config = self.read_config()
                is_bleeding = config.get("IsBleeding", False)

                if local_version:
                    remote_version_info = self.fetch_remote_version()
                    if remote_version_info:
                        remote_version = remote_version_info.get("version")
                        remote_version_bleeding = remote_version_info.get("versionBleeding")
                        logging.info(f"Remote version: {remote_version}")
                        logging.info(f"Remote bleeding version: {remote_version_bleeding}")

                        if is_bleeding:
                            remote_version_to_check = remote_version_bleeding
                            local_version_to_check = local_version_bleeding
                        else:
                            remote_version_to_check = remote_version
                            local_version_to_check = local_version
                        
                        if remote_version_to_check and (remote_version_to_check != local_version_to_check):
                            if is_bleeding:
                                update_message = f"Do you want to update to the bleeding edge version ({remote_version_bleeding})?"
                            else:
                                update_message = f"A new version ({remote_version}) is available!\nDo you want to download it now?"
                            update_dialog = QMessageBox.question(self.parent, "Update Available", update_message, 
                                                              QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
                            if update_dialog == QMessageBox.Yes:
                                self.download_update(remote_version_info)
                        else:
                            print(f"You already have the latest version!")
                    else:
                        logging.error("Failed to fetch remote version information.")
                else:
                    logging.error("Failed to read local version information.")
                    QMessageBox.critical(self.parent, "Error", "Failed to check for updates.")
            else:
                logging.error("Failed to read local version information from any location.")
                QMessageBox.critical(self.parent, "Error", "Failed to read version information.")
        except Exception as e:
            logging.error("Error checking for updates: %s", str(e))
            QMessageBox.critical(self.parent, "Error", "Failed to check for updates.")

    def check_for_update(self):
        try:
            # First try to read from the assets/data.json path
            local_version_info = self.read_local_version()
            if not local_version_info:
                # If not found, try the root version.json as fallback
                self.version_path = "version.json"
                local_version_info = self.read_local_version()

            if local_version_info:
                local_version = local_version_info.get("version")
                local_version_bleeding = local_version_info.get("versionBleeding")
                logging.info(f"Local version: {local_version}")
                logging.info(f"Local bleeding version: {local_version_bleeding}")

                config = self.read_config()
                is_bleeding = config.get("IsBleeding", False)

                if local_version:
                    remote_version_info = self.fetch_remote_version()
                    if remote_version_info:
                        remote_version = remote_version_info.get("version")
                        remote_version_bleeding = remote_version_info.get("versionBleeding")
                        logging.info(f"Remote version: {remote_version}")
                        logging.info(f"Remote bleeding version: {remote_version_bleeding}")

                        if is_bleeding:
                            remote_version_to_check = remote_version_bleeding
                            local_version_to_check = local_version_bleeding
                        else:
                            remote_version_to_check = remote_version
                            local_version_to_check = local_version
                        
                        if remote_version_to_check and (remote_version_to_check != local_version_to_check):
                            if is_bleeding:
                                update_message = f"Do you want to update to the bleeding edge version ({remote_version_bleeding})?"
                            else:
                                update_message = f"A new version ({remote_version}) is available!\nDo you want to download it now?"
                            update_dialog = QMessageBox.question(self.parent, "Update Available", update_message, 
                                                              QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
                            if update_dialog == QMessageBox.Yes:
                                self.download_update(remote_version_info)
                        else:
                            QMessageBox.information(self.parent, "Up to Date", "You already have the latest version!")
                    else:
                        logging.error("Failed to fetch remote version information.")
                        QMessageBox.critical(self.parent, "Error", "Failed to fetch update information.")
                else:
                    logging.error("Failed to read local version information.")
                    QMessageBox.critical(self.parent, "Error", "Failed to check for updates.")
            else:
                logging.error("Failed to read local version information from any location.")
                QMessageBox.critical(self.parent, "Error", "Failed to read version information.")
        except Exception as e:
            logging.error("Error checking for updates: %s", str(e))
            QMessageBox.critical(self.parent, "Error", "Failed to check for updates.")

    def read_local_version(self):
        """Read local version information from file."""
        try:
            if os.path.exists(self.version_path):
                with open(self.version_path) as f:
                    return json.load(f)
            return None
        except Exception as e:
            logging.error(f"Error reading local version file: {str(e)}")
            return None

    def read_config(self):
        """Read configuration from file."""
        try:
            if os.path.exists(self.config_path):
                with open(self.config_path) as config_file:
                    return json.load(config_file)
            return {}
        except Exception as e:
            logging.error(f"Error reading config file: {str(e)}")
            return {}

    def fetch_remote_version(self):
        try:
            update_url = self.base_url + self.version_path
            response = requests.get(update_url)
            if response.status_code == 200:
                return response.json()
            else:
                # If the custom path fails, try the default version.json
                fallback_url = self.base_url + "version.json"
                response = requests.get(fallback_url)
                if response.status_code == 200:
                    return response.json()
                logging.error("Failed to fetch update information from both locations.")
                return None
        except Exception as e:
            logging.error("Error fetching remote version: %s", str(e))
            return None

    def download_update(self, version_info):
        try:
            update_folder = "update"
            if not os.path.exists(update_folder):
                os.makedirs(update_folder)
            
            for link in version_info.get("links", []):
                # Extract the relative path from the URL
                relative_path = link.replace(self.base_url, "")
                filename = os.path.basename(relative_path)
                target_dir = os.path.join(update_folder, os.path.dirname(relative_path))
                
                # Create necessary subdirectories
                if not os.path.exists(target_dir):
                    os.makedirs(target_dir)
                
                response = requests.get(link, stream=True)
                if response.status_code == 200:
                    target_path = os.path.join(target_dir, filename)
                    with open(target_path, 'wb') as f:
                        for chunk in response.iter_content(chunk_size=1024):
                            f.write(chunk)
                else:
                    QMessageBox.critical(self.parent, "Error", f"Failed to download update file: {filename}")
            
            # Move downloaded files while preserving directory structure
            for root, dirs, files in os.walk(update_folder):
                for file in files:
                    src = os.path.join(root, file)
                    relative_path = os.path.relpath(src, update_folder)
                    dst = os.path.join(os.path.dirname(update_folder), relative_path)
                    
                    # Create destination directory if it doesn't exist
                    dst_dir = os.path.dirname(dst)
                    if not os.path.exists(dst_dir):
                        os.makedirs(dst_dir)
                    
                    shutil.move(src, dst)
            
            # Remove the update folder
            shutil.rmtree(update_folder)
            
            QMessageBox.information(self.parent, "Update", "Updates downloaded successfully.")
        except Exception as e:
            logging.error("Error downloading updates: %s", str(e))
            QMessageBox.critical(self.parent, "Error", "Failed to download updates.")
