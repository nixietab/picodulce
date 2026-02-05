import os
import json
import shutil
import modulecli
from PyQt5.QtWidgets import QApplication, QDialog, QVBoxLayout, QLabel, QProgressBar
from PyQt5.QtCore import Qt, QThread, pyqtSignal
import sys

class CopyThread(QThread):
    progress_changed = pyqtSignal(int)
    finished = pyqtSignal()

    def __init__(self, src_dir, dst_dir):
        super().__init__()
        self.src_dir = src_dir
        self.dst_dir = dst_dir

    def run(self):
        # Gather all files recursively
        files_to_copy = []
        for root, dirs, files in os.walk(self.src_dir):
            for f in files:
                full_path = os.path.join(root, f)
                relative_path = os.path.relpath(full_path, self.src_dir)
                files_to_copy.append(relative_path)

        total_files = len(files_to_copy)
        copied_files = 0

        for relative_path in files_to_copy:
            src_path = os.path.join(self.src_dir, relative_path)
            dst_path = os.path.join(self.dst_dir, relative_path)
            dst_folder = os.path.dirname(dst_path)

            if not os.path.exists(dst_folder):
                try:
                    os.makedirs(dst_folder)
                except PermissionError:
                    print(f"Skipping folder {dst_folder} (permission denied)")
                    continue

            try:
                shutil.copy2(src_path, dst_path)
            except PermissionError:
                print(f"Skipping file {dst_path} (permission denied)")

            copied_files += 1
            progress_percent = int((copied_files / total_files) * 100)
            self.progress_changed.emit(progress_percent)

        self.finished.emit()


class HealthCheck:
    def __init__(self):
        self.config = None

    def check_config_file(self):
        config_path = "config.json"
        default_config = {
            "IsRCPenabled": False,
            "CheckUpdate": False,
            "IsBleeding": False,
            "LastPlayed": "",
            "TotalPlaytime": 0,
            "IsFirstLaunch": True,
            "Instance": "default",
            "Theme": "Dark.json",
            "ThemeBackground": True,
            "ThemeRepository": ["https://raw.githubusercontent.com/nixietab/picodulce-themes/main/repo.json"],
            "Locale": "en",
            "ManageJava": False,
            "MaxRAM": "2G",
            "JavaPath": "",
            "ZucaroCheck": False,
            "KeyboardShortcuts": {
                "Screenshots": "Ctrl+A",
                "Play": "Ctrl+P",
                "VersionManager": "Ctrl+M",
                "ModManager": "Ctrl+O",
                "Settings": "Ctrl+S",
                "SettingsAlt": "Ctrl+,",
                "About": "Ctrl+I",
                "Refresh": "Ctrl+R",
                "RefreshAlt": "F5",
                "Quit": "Ctrl+Q",
                "SaveSettings": "Ctrl+S",
                "CloseDialog": "Ctrl+W",
                "CancelDialog": "Escape",
                "NextTab": "Ctrl+Tab",
                "PrevTab": "Ctrl+Shift+Tab"
            }
        }

        if not os.path.exists(config_path):
            print("Config file not found. Creating default.")
            with open(config_path, "w") as config_file:
                json.dump(default_config, config_file, indent=4)
            self.config = default_config
            return

        try:
            with open(config_path, "r") as config_file:
                self.config = json.load(config_file)
        except (json.JSONDecodeError, ValueError) as e:
            print(f"Error loading config.json: {e}")
            backup_path = "config.json.bak"
            print(f"Backing up broken config to {backup_path}")
            shutil.copy2(config_path, backup_path)
            
            # Try to preserve at least the TotalPlaytime if possible by simple string search
            # as a last resort before wiping everything
            extracted_playtime = 0
            try:
                with open(config_path, "r") as f:
                    content = f.read()
                    import re
                    match = re.search(r'"TotalPlaytime":\s*(\d+(?:\.\d+)?)', content)
                    if match:
                        extracted_playtime = float(match.group(1))
                        print(f"Recovered TotalPlaytime from broken JSON: {extracted_playtime}")
            except Exception:
                pass

            print("Resetting to default config due to corruption.")
            self.config = default_config.copy()
            if extracted_playtime > 0:
                self.config["TotalPlaytime"] = extracted_playtime
            
            with open(config_path, "w") as config_file:
                json.dump(self.config, config_file, indent=4)
            return

        updated = False
        
        # Migrate old singular ThemeRepository to list
        if "ThemeRepository" in self.config and isinstance(self.config["ThemeRepository"], str):
            print("Migrating ThemeRepository to list.")
            self.config["ThemeRepository"] = [self.config["ThemeRepository"]]
            updated = True

        for key, value in default_config.items():
            if key not in self.config:
                print(f"Adding missing config key: {key}")
                self.config[key] = value
                updated = True

        if updated:
            with open(config_path, "w") as config_file:
                json.dump(self.config, config_file, indent=4)


    def get_folder_size(self, folder_path):
        total_size = 0
        for dirpath, dirnames, filenames in os.walk(folder_path):
            for f in filenames:
                fp = os.path.join(dirpath, f)
                if os.path.isfile(fp):
                    total_size += os.path.getsize(fp)
        return total_size

    def zucaro_health_check(self):
        if self.config.get("ZucaroCheck"):
            return

        output = modulecli.run_command("instance dir").strip()
        instance_dir = os.path.abspath(output)
        base_dir = os.path.abspath(os.path.join(instance_dir, "..", ".."))

        possible_zucaro = [os.path.join(base_dir, "zucaro"), os.path.join(base_dir, ".zucaro")]
        possible_picomc = [os.path.join(base_dir, "picomc"), os.path.join(base_dir, ".picomc")]

        zucaro_dir = next((d for d in possible_zucaro if os.path.exists(d)), None)
        picomc_dir = next((d for d in possible_picomc if os.path.exists(d)), None)

        if picomc_dir is None or zucaro_dir is None:
            print("Required directories not found. Skipping copy.")
            # Mark the check as done so it wont run again
            self.config["ZucaroCheck"] = True
            with open("config.json", "w") as f:
                json.dump(self.config, f, indent=4)
            return

        picomc_size = self.get_folder_size(picomc_dir)
        zucaro_size = self.get_folder_size(zucaro_dir)

        if picomc_size <= zucaro_size:
            print("No action needed. Zucaro folder is not smaller than Picomc.")
            # Update config so the check is considered done
            self.config["ZucaroCheck"] = True
            with open("config.json", "w") as f:
                json.dump(self.config, f, indent=4)
            return

        print(f"Copying Picomc ({picomc_size} bytes) to Zucaro ({zucaro_size} bytes)...")

        QApplication.instance() or QApplication(sys.argv)
        dialog = QDialog()
        dialog.setWindowTitle("Working...")
        dialog.setWindowModality(Qt.ApplicationModal)
        layout = QVBoxLayout()
        label = QLabel("Working on the updates, please wait...")
        progress = QProgressBar()
        progress.setValue(0)
        layout.addWidget(label)
        layout.addWidget(progress)
        dialog.setLayout(layout)

        # Setup copy thread
        thread = CopyThread(picomc_dir, zucaro_dir)
        thread.progress_changed.connect(progress.setValue)
        thread.finished.connect(dialog.accept)
        thread.start()

        dialog.exec_()  # Runs the modal event loop

        # Mark as done
        self.config["ZucaroCheck"] = True
        with open("config.json", "w") as f:
            json.dump(self.config, f, indent=4)

        print("Copy completed.")

    def themes_integrity(self):
        themes_folder = "themes"
        dark_theme_file = os.path.join(themes_folder, "Dark.json")
        native_theme_file = os.path.join(themes_folder, "Native.json")

        dark_theme_content = {
            "manifest": {
                "name": "Dark",
                "description": "The default picodulce launcher theme",
                "author": "Nixietab",
                "license": "MIT"
            },
            "palette": {
                "Window": "#353535",
                "WindowText": "#ffffff",
                "Base": "#191919",
                "AlternateBase": "#353535",
                "ToolTipBase": "#ffffff",
                "ToolTipText": "#ffffff",
                "Text": "#ffffff",
                "Button": "#353535",
                "ButtonText": "#ffffff",
                "BrightText": "#ff0000",
                "Link": "#2a82da",
                "Highlight": "#4bb679",
                "HighlightedText": "#ffffff"
            },
            "background_image_base64": ""
        }

        native_theme_content = {
            "manifest": {
                "name": "Native",
                "description": "The native looks of your OS",
                "author": "Your Qt Style",
                "license": "Any"
            },
            "palette": {}
        }

        if not os.path.exists(themes_folder):
            print(f"Creating folder: {themes_folder}")
            os.makedirs(themes_folder)

        if not os.path.isfile(dark_theme_file):
            print(f"Creating file: {dark_theme_file}")
            with open(dark_theme_file, "w", encoding="utf-8") as file:
                json.dump(dark_theme_content, file, indent=2)
            print("Dark.json has been created successfully.")

        if not os.path.isfile(native_theme_file):
            print(f"Creating file: {native_theme_file}")
            with open(native_theme_file, "w", encoding="utf-8") as file:
                json.dump(native_theme_content, file, indent=2)
            print("Native.json has been created successfully.")

        if os.path.isfile(dark_theme_file) and os.path.isfile(native_theme_file):
            print("Theme Integrity OK")
