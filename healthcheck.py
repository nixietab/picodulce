import os
import json
import requests


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
            "ThemeRepository": "https://raw.githubusercontent.com/nixietab/picodulce-themes/main/repo.json",
            "Locale": "en",
            "ManageJava": False,
            "MaxRAM": 2,
            "JavaPath": ""
        }

        # Step 1: Check if the file exists; if not, create it with default values
        if not os.path.exists(config_path):
            with open(config_path, "w") as config_file:
                json.dump(default_config, config_file, indent=4)
            self.config = default_config
            return

        # Step 2: Try loading the config file, handle invalid JSON
        try:
            with open(config_path, "r") as config_file:
                self.config = json.load(config_file)
        except (json.JSONDecodeError, ValueError):
            # File is corrupted, overwrite it with default configuration
            with open(config_path, "w") as config_file:
                json.dump(default_config, config_file, indent=4)
            self.config = default_config
            return

        # Step 3: Check for missing keys and add defaults if necessary
        updated = False
        for key, value in default_config.items():
            if key not in self.config:  # Field is missing
                self.config[key] = value
                updated = True

        # Step 4: Save the repaired config back to the file
        if updated:
            with open(config_path, "w") as config_file:
                json.dump(self.config, config_file, indent=4)

    def themes_integrity(self):
        # Define folder and file paths
        themes_folder = "themes"
        dark_theme_file = os.path.join(themes_folder, "Dark.json")
        native_theme_file = os.path.join(themes_folder, "Native.json")

        # Define the default content for Dark.json
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

        # Define the default content for Native.json
        native_theme_content = {
            "manifest": {
                "name": "Native",
                "description": "The native looks of your OS",
                "author": "Your Qt Style",
                "license": "Any"
            },
            "palette": {}
        }

        # Step 1: Ensure the themes folder exists
        if not os.path.exists(themes_folder):
            print(f"Creating folder: {themes_folder}")
            os.makedirs(themes_folder)

        # Step 2: Ensure Dark.json exists
        if not os.path.isfile(dark_theme_file):
            print(f"Creating file: {dark_theme_file}")
            with open(dark_theme_file, "w", encoding="utf-8") as file:
                json.dump(dark_theme_content, file, indent=2)
            print("Dark.json has been created successfully.")

        # Step 3: Ensure Native.json exists
        if not os.path.isfile(native_theme_file):
            print(f"Creating file: {native_theme_file}")
            with open(native_theme_file, "w", encoding="utf-8") as file:
                json.dump(native_theme_content, file, indent=2)
            print("Native.json has been created successfully.")

        # Check if both files exist and print OK message
        if os.path.isfile(dark_theme_file) and os.path.isfile(native_theme_file):
            print("Theme Integrity OK")
