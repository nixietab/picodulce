import json
import logging
import os
import shutil
import requests
from PyQt5.QtWidgets import QMessageBox

class UpdateChecker:
    def __init__(self, parent=None):
        self.parent = parent

    def check_for_update_start(self):
        try:
            with open("version.json") as f:
                local_version_info = json.load(f)
                local_version = local_version_info.get("version")
                local_version_bleeding = local_version_info.get("versionBleeding")
                logging.info(f"Local version: {local_version}")
                logging.info(f"Local bleeding version: {local_version_bleeding}")

                with open("config.json") as config_file:
                    config = json.load(config_file)
                    is_bleeding = config.get("IsBleeding", False)

                if local_version:
                    remote_version_info = self.fetch_remote_version()
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
                            # Download and apply the update
                            self.download_update(remote_version_info)
                    else:
                        print(f"You already have the latest version!")
                else:
                    logging.error("Failed to read local version information.")
                    QMessageBox.critical(self.parent, "Error", "Failed to check for updates.")
        except Exception as e:
            logging.error("Error checking for updates: %s", str(e))
            QMessageBox.critical(self.parent, "Error", "Failed to check for updates.")

    def check_for_update(self):
        try:
            with open("version.json") as f:
                local_version_info = json.load(f)
                local_version = local_version_info.get("version")
                local_version_bleeding = local_version_info.get("versionBleeding")
                logging.info(f"Local version: {local_version}")
                logging.info(f"Local bleeding version: {local_version_bleeding}")

                with open("config.json") as config_file:
                    config = json.load(config_file)
                    is_bleeding = config.get("IsBleeding", False)

                if local_version:
                    remote_version_info = self.fetch_remote_version()
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
                            # Download and apply the update
                            self.download_update(remote_version_info)
                    else:
                        QMessageBox.information(self.parent, "Up to Date", "You already have the latest version!")
                else:
                    logging.error("Failed to read local version information.")
                    QMessageBox.critical(self.parent, "Error", "Failed to check for updates.")
        except Exception as e:
            logging.error("Error checking for updates: %s", str(e))
            QMessageBox.critical(self.parent, "Error", "Failed to check for updates.")

    def fetch_remote_version(self):
        try:
            update_url = "https://raw.githubusercontent.com/nixietab/picodulce/main/version.json"
            response = requests.get(update_url)
            if response.status_code == 200:
                remote_version_info = response.json()
                return remote_version_info
            else:
                logging.error("Failed to fetch update information.")
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
                filename = os.path.basename(link)
                response = requests.get(link, stream=True)
                if response.status_code == 200:
                    with open(os.path.join(update_folder, filename), 'wb') as f:
                        for chunk in response.iter_content(chunk_size=1024):
                            f.write(chunk)
                else:
                    QMessageBox.critical(self.parent, "Error", f"Failed to download update file: {filename}")
            
            # Move downloaded files one directory up
            for file in os.listdir(update_folder):
                src = os.path.join(update_folder, file)
                dst = os.path.join(os.path.dirname(update_folder), file)
                shutil.move(src, dst)
            
            # Remove the update folder
            shutil.rmtree(update_folder)
            
            QMessageBox.information(self.parent, "Update", "Updates downloaded successfully.")
        except Exception as e:
            logging.error("Error downloading updates: %s", str(e))
            QMessageBox.critical(self.parent, "Error", "Failed to download updates.")
