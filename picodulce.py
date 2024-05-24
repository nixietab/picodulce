import sys
import subprocess
import threading
from threading import Thread
import logging
import shutil
import requests
import json
import os
from pypresence import Presence
import time
from PyQt5.QtWidgets import QApplication, QComboBox, QWidget, QVBoxLayout, QPushButton, QMessageBox, QDialog, QHBoxLayout, QLabel, QLineEdit, QCheckBox, QTabWidget, QFrame, QSpacerItem, QSizePolicy, QMainWindow, QGridLayout
from PyQt5.QtGui import QFont, QIcon, QColor, QPalette
from PyQt5.QtCore import Qt

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class PicomcVersionSelector(QWidget):
    def __init__(self):
        super().__init__()

        self.init_ui()
        self.check_config_file()
        if self.config.get("CheckUpdate", False):
            self.check_for_update_start()

        if self.config.get("IsRCPenabled", False):
            discord_rcp_thread = Thread(target=self.start_discord_rcp)
            discord_rcp_thread.daemon = True  # Make the thread a daemon so it terminates when the main program exits
            discord_rcp_thread.start()

    def init_ui(self):
        self.setWindowTitle('PicoDulce Launcher')  # Change window title
        self.setWindowIcon(QIcon('launcher_icon.ico'))  # Set window icon
        self.setGeometry(100, 100, 400, 250)

        # Set application style and palette
        app_style = QApplication.setStyle("Fusion")
        self.check_config_file()
        palette_type = self.config.get("Palette", "Dark")
        if palette_type == "Dark":
            palette = self.create_dark_palette()
        elif palette_type == "Obsidian":
            palette = self.create_obsidian_palette()
        elif palette_type == "Redstone":
            palette = self.create_redstone_palette()
        elif palette_type == "Alpha":
            palette = self.create_alpha_palette()
        elif palette_type == "Strawberry":
            palette = self.create_strawberry_palette()
        elif palette_type == "Native":
            palette = self.create_native_palette()
        else:
            # Default to dark palette if the type is not specified or invalid
            palette = self.create_dark_palette()
        QApplication.instance().setPalette(palette)
        
        # Create title label
        title_label = QLabel('PicoDulce Launcher')  # Change label text
        title_label.setFont(QFont("Arial", 24, QFont.Bold))

        # Create installed versions section
        installed_versions_label = QLabel('Installed Versions:')
        installed_versions_label.setFont(QFont("Arial", 14))
        self.installed_version_combo = QComboBox()
        self.installed_version_combo.setMinimumWidth(200)
        self.populate_installed_versions()

        # Create buttons layout
        buttons_layout = QVBoxLayout()

        # Create play button for installed versions
        self.play_button = QPushButton('Play')
        self.play_button.setFocusPolicy(Qt.NoFocus)  # Set focus policy to prevent highlighting
        self.play_button.clicked.connect(self.play_instance)
        highlight_color = self.palette().color(QPalette.Highlight)
        self.play_button.setStyleSheet(f"background-color: {highlight_color.name()}; color: white;")
        buttons_layout.addWidget(self.play_button)

        # Version Manager Button
        self.open_menu_button = QPushButton('Version Manager')
        self.open_menu_button.clicked.connect(self.open_mod_loader_and_version_menu)
        buttons_layout.addWidget(self.open_menu_button)

        # Create button to manage accounts
        self.manage_accounts_button = QPushButton('Manage Accounts')
        self.manage_accounts_button.clicked.connect(self.manage_accounts)
        buttons_layout.addWidget(self.manage_accounts_button)

        # Create a button for the marroc mod loader
        self.open_marroc_button = QPushButton('Marroc Mod Manager')
        self.open_marroc_button.clicked.connect(self.open_marroc_script)
        buttons_layout.addWidget(self.open_marroc_button)

        # Create grid layout for Settings and About buttons
        grid_layout = QGridLayout()
        self.settings_button = QPushButton('Settings')
        self.settings_button.clicked.connect(self.open_settings_dialog)
        self.about_button = QPushButton('About')
        self.about_button.clicked.connect(self.show_about_dialog)
        
        grid_layout.addWidget(self.settings_button, 0, 0)
        grid_layout.addWidget(self.about_button, 0, 1)

        # Add the grid layout to buttons layout
        buttons_layout.addLayout(grid_layout)

        # Set buttons layout alignment and spacing
        buttons_layout.setAlignment(Qt.AlignTop)
        buttons_layout.setSpacing(10)

        # Set main layout
        main_layout = QVBoxLayout()
        main_layout.addWidget(title_label, alignment=Qt.AlignCenter)
        main_layout.addWidget(installed_versions_label)
        main_layout.addWidget(self.installed_version_combo)
        main_layout.addLayout(buttons_layout)
        main_layout.setAlignment(Qt.AlignCenter)
        main_layout.setSpacing(20)

        self.setLayout(main_layout)

    def check_config_file(self):
        config_path = "config.json"
        default_config = {
            "IsRCPenabled": False,
            "CheckUpdate": False,
            "LastPlayed": "",
            "Palette": "Dark"
        }

        # Check if config file exists
        if not os.path.exists(config_path):
            # Create config file with default values
            with open(config_path, "w") as config_file:
                json.dump(default_config, config_file, indent=4)
            self.check_config_file()


        # Load config from file
        with open(config_path, "r") as config_file:
            self.config = json.load(config_file)


    def open_settings_dialog(self):
        dialog = QDialog(self)
        dialog.setWindowTitle('Settings')
        dialog.setFixedSize(300, 200)

        # Create title label
        title_label = QLabel('Settings')
        title_label.setFont(QFont("Arial", 14))

        # Add settings components here...
        layout = QVBoxLayout()
        layout.addWidget(title_label)

        # Create Update button
        discord_rcp_checkbox = QCheckBox('Discord RCP')
        discord_rcp_checkbox.setChecked(self.config.get("IsRCPenabled", False))
        check_updates_checkbox = QCheckBox('Check Updates on Start')
        check_updates_checkbox.setChecked(self.config.get("CheckUpdate", False))

        # Add checkboxes to layout
        layout.addWidget(discord_rcp_checkbox)
        layout.addWidget(check_updates_checkbox)

        # Create theme dropdown
        theme_label = QLabel('Theme:')
        layout.addWidget(theme_label)

        theme_combobox = QComboBox()
        themes = ['Dark', 'Obsidian', 'Redstone', 'Alpha', 'Strawberry', "Native"]  # Replace with your actual themes
        theme_combobox.addItems(themes)
        current_theme_index = themes.index(self.config.get("Palette", "Default Theme"))
        theme_combobox.setCurrentIndex(current_theme_index)
        layout.addWidget(theme_combobox)

        # Create Save button
        save_button = QPushButton('Save')
        save_button.clicked.connect(lambda: self.save_settings(discord_rcp_checkbox.isChecked(), check_updates_checkbox.isChecked(), theme_combobox.currentText()))
        layout.addWidget(save_button)

        update_button = QPushButton('Check for updates')
        update_button.clicked.connect(self.check_for_update)
        layout.addWidget(update_button)

        dialog.setLayout(layout)
        dialog.exec_()

    def save_settings(self, is_rcp_enabled, check_updates_on_start, selected_theme):
        config_path = "config.json"
        updated_config = {
            "IsRCPenabled": is_rcp_enabled,
            "CheckUpdate": check_updates_on_start,
            "Palette": selected_theme
        }

        # Update config values
        self.config.update(updated_config)

        # Save updated config to file
        with open(config_path, "w") as config_file:
            json.dump(self.config, config_file, indent=4)

        QMessageBox.information(self, "Settings Saved", "Settings saved successfully!\n\n to them to be applyed you need to restart the launcher")
        self.__init__()


    def populate_installed_versions(self):
        config_path = "config.json"
        # Check if config file exists
        if not os.path.exists(config_path):
            logging.error("Config file not found.")
            self.populate_installed_versions_normal_order()
            return

        # Load config from file
        with open(config_path, "r") as config_file:
            self.config = json.load(config_file)

        # Run the command and get the output
        try:
            process = subprocess.Popen(['picomc', 'version', 'list'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            output, error = process.communicate()
            if process.returncode != 0:
                raise subprocess.CalledProcessError(process.returncode, process.args, error)
        except FileNotFoundError:
            logging.error("'picomc' command not found. Please make sure it's installed and in your PATH.")
            return
        except subprocess.CalledProcessError as e:
            logging.error("Error: %s", e.stderr)
            return

        # Parse the output and replace '[local]' with a space
        versions = output.splitlines()
        versions = [version.replace('[local]', ' ').strip() for version in versions]

        # Get last played version from config
        last_played = self.config.get("LastPlayed", "")

        # If lastplayed is not empty and is in the versions list, move it to the top
        if last_played and last_played in versions:
            versions.remove(last_played)
            versions.insert(0, last_played)

        # Populate installed versions combo box
        self.installed_version_combo.clear()
        self.installed_version_combo.addItems(versions)

    def populate_installed_versions_normal_order(self):
        # Run the command and get the output
        try:
            process = subprocess.Popen(['picomc', 'version', 'list'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            output, error = process.communicate()
            if process.returncode != 0:
                raise subprocess.CalledProcessError(process.returncode, process.args, error)
        except FileNotFoundError:
            logging.error("'picomc' command not found. Please make sure it's installed and in your PATH.")
            return
        except subprocess.CalledProcessError as e:
            logging.error("Error: %s", e.stderr)
            return

        # Parse the output and replace '[local]' with a space
        versions = output.splitlines()
        versions = [version.replace('[local]', ' ').strip() for version in versions]

        # Populate installed versions combo box
        self.installed_version_combo.clear()
        self.installed_version_combo.addItems(versions)

    def open_marroc_script(self):
        try:
            # Replace 'path_to_marroc.py' with the actual path to marroc.py
            subprocess.Popen(['python', 'marroc.py'])
        except FileNotFoundError:
            logging.error("'marroc.py' not found.")
            QMessageBox.critical(self, "Error", "'marroc.py' not found.")

    def play_instance(self):
        if self.installed_version_combo.count() == 0:
            QMessageBox.warning(self, "No Version Available", "Please download a version first.")
            return

        # Check if there are any accounts
        account_list_output = subprocess.check_output(["picomc", "account", "list"]).decode("utf-8").strip()
        if not account_list_output:
            QMessageBox.warning(self, "No Account Available", "Please create an account first.")
            return

        # Check if the selected account has a '*' (indicating it's the selected one)
        if '*' not in account_list_output:
            QMessageBox.warning(self, "No Account Selected", "Please select an account.")
            return

        selected_instance = self.installed_version_combo.currentText()

        # Create a separate thread to run the game process
        play_thread = threading.Thread(target=self.run_game, args=(selected_instance,))
        play_thread.start()

    def run_game(self, selected_instance):
        try:
            subprocess.run(['picomc', 'play', selected_instance], check=True)
            # Update lastplayed field in config.json
            self.update_last_played(selected_instance)
        except subprocess.CalledProcessError as e:
            error_message = f"Error playing {selected_instance}: {e.stderr.decode()}"
            logging.error(error_message)
            QMessageBox.critical(self, "Error", error_message)

    def update_last_played(self, selected_instance):
        config_path = "config.json"
        self.config["LastPlayed"] = selected_instance
        with open(config_path, "w") as config_file:
            json.dump(self.config, config_file, indent=4)


    def manage_accounts(self):
        dialog = QDialog(self)
        dialog.setWindowTitle('Manage Accounts')
        dialog.setFixedSize(400, 250)

        # Create title label
        title_label = QLabel('Manage Accounts')
        title_label.setFont(QFont("Arial", 14))

        # Create dropdown menu for accounts
        account_combo = QComboBox()
        self.populate_accounts(account_combo)

        # Create select button
        select_button = QPushButton('Select')
        select_button.clicked.connect(lambda: self.set_default_account(dialog, account_combo.currentText()))

        # Create input field for account name
        account_input = QLineEdit()
        account_input.setPlaceholderText('Xx_PussySlayer_xX')

        # Create button to create new account
        create_account_button = QPushButton('Create')
        create_account_button.clicked.connect(lambda: self.create_account(dialog, account_input.text(), microsoft_checkbox.isChecked()))

        # Create checkbox for Microsoft account
        microsoft_checkbox = QCheckBox('Microsoft Account')

        # Create button to authenticate
        authenticate_button = QPushButton('Authenticate')
        authenticate_button.clicked.connect(lambda: self.authenticate_account(dialog, account_combo.currentText()))

        # Create button to remove account
        remove_account_button = QPushButton('Remove Account')
        remove_account_button.clicked.connect(lambda: self.remove_account(dialog, account_combo.currentText()))

        # Create layout for account selection
        account_selection_layout = QVBoxLayout()
        account_selection_layout.addWidget(title_label)
        account_selection_layout.addWidget(account_combo)
        account_selection_layout.addWidget(select_button)

        # Create layout for account creation
        create_account_layout = QHBoxLayout()
        create_account_layout.addWidget(account_input)
        create_account_layout.addWidget(create_account_button)

        # Create layout for Microsoft account checkbox and authenticate button
        microsoft_layout = QVBoxLayout()
        microsoft_layout.addWidget(microsoft_checkbox)
        microsoft_layout.addWidget(authenticate_button)

        # Create layout for remove account button
        remove_account_layout = QVBoxLayout()
        remove_account_layout.addWidget(remove_account_button)

        # Create main layout
        main_layout = QVBoxLayout()
        main_layout.addLayout(account_selection_layout)
        main_layout.addLayout(create_account_layout)
        main_layout.addLayout(microsoft_layout)
  #      main_layout.addStretch(1)
        main_layout.addLayout(remove_account_layout)

        dialog.setLayout(main_layout)
        dialog.exec_()

    def authenticate_account(self, dialog, account_name):
        # Remove leading " * " from the account name
        account_name = account_name.strip().lstrip(" * ")
        try:
            subprocess.run(['picomc', 'account', 'authenticate', account_name], check=True)
            QMessageBox.information(self, "Success", f"Account '{account_name}' authenticated successfully!")
        except subprocess.CalledProcessError as e:
            error_message = f"Error authenticating account '{account_name}': {e.stderr.decode()}"
            logging.error(error_message)
            QMessageBox.critical(self, "Error", error_message)


    def populate_accounts(self, account_combo):
        # Run the command and get the output
        try:
            process = subprocess.Popen(['picomc', 'account', 'list'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            output, error = process.communicate()
            if process.returncode != 0:
                raise subprocess.CalledProcessError(process.returncode, process.args, error)
        except FileNotFoundError:
            logging.error("'picomc' command not found. Please make sure it's installed and in your PATH.")
            return
        except subprocess.CalledProcessError as e:
            logging.error("Error: %s", e.stderr)
            return

        # Parse the output and remove ' *' from account names
        accounts = output.splitlines()
        accounts = [account.replace(' *', '').strip() for account in accounts]

        # Populate accounts combo box
        account_combo.clear()
        account_combo.addItems(accounts)

    def create_account(self, dialog, username, is_microsoft):
        if username.strip() == '':
            QMessageBox.warning(dialog, "Warning", "Username cannot be blank.")
            return
        try:
            if is_microsoft:
                subprocess.run(['picomc', 'account', 'create', username, '--ms'], check=True)
            else:
                subprocess.run(['picomc', 'account', 'create', username], check=True)
            QMessageBox.information(self, "Success", f"Account {username} created successfully!")
            self.populate_accounts(dialog.findChild(QComboBox))
        except subprocess.CalledProcessError as e:
            error_message = f"Error creating account: {e.stderr.decode()}"
            logging.error(error_message)
            QMessageBox.critical(self, "Error", error_message)

    def set_default_account(self, dialog, account):
        dialog.close()
        try:
            subprocess.run(['picomc', 'account', 'setdefault', account], check=True)
            QMessageBox.information(self, "Success", f"Default account set to {account}!")
        except subprocess.CalledProcessError as e:
            error_message = f"Error setting default account: {e.stderr.decode()}"
            logging.error(error_message)
            QMessageBox.critical(self, "Error", error_message)

    def remove_account(self, dialog, username):
        if username.strip() == '':
            QMessageBox.warning(dialog, "Warning", "Please select an account to remove.")
            return

        # Remove any leading " * " from the username
        username = username.strip().lstrip(" * ")

        # Ask for confirmation twice before removing the account
        confirm_message = f"Are you sure you want to remove the account '{username}'?\nThis action cannot be undone."
        confirm_dialog = QMessageBox.question(self, "Confirm Removal", confirm_message, QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if confirm_dialog == QMessageBox.Yes:
            confirm_message_again = "This action is irreversible. Are you absolutely sure?"
            confirm_dialog_again = QMessageBox.question(self, "Confirm Removal", confirm_message_again, QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            if confirm_dialog_again == QMessageBox.Yes:
                try:
                    subprocess.run(['picomc', 'account', 'remove', username], check=True)
                    QMessageBox.information(self, "Success", f"Account '{username}' removed successfully!")
                    self.populate_accounts(dialog.findChild(QComboBox))
                except subprocess.CalledProcessError as e:
                    error_message = f"Error removing account: {e.stderr.decode()}"
                    logging.error(error_message)
                    QMessageBox.critical(self, "Error", error_message)

    def show_about_dialog(self):
        about_message = "PicoDulce Launcher\n\nA simple Minecraft launcher built using Qt, based on the picomc project.\n\nCredits:\nNixietab: Code and UI design\nWabaano: Graphic design"
        QMessageBox.about(self, "About", about_message)



    def create_dark_palette(self):
        palette = QPalette()
        palette.setColor(QPalette.Window, QColor(53, 53, 53))
        palette.setColor(QPalette.WindowText, Qt.white)
        palette.setColor(QPalette.Base, QColor(25, 25, 25))
        palette.setColor(QPalette.AlternateBase, QColor(53, 53, 53))
        palette.setColor(QPalette.ToolTipBase, Qt.white)
        palette.setColor(QPalette.ToolTipText, Qt.white)
        palette.setColor(QPalette.Text, Qt.white)
        palette.setColor(QPalette.Button, QColor(53, 53, 53))
        palette.setColor(QPalette.ButtonText, Qt.white)
        palette.setColor(QPalette.BrightText, Qt.red)
        palette.setColor(QPalette.Link, QColor(42, 130, 218))
        palette.setColor(QPalette.Highlight, QColor(75 , 182, 121))
        palette.setColor(QPalette.HighlightedText, Qt.white)
        return palette

    def create_obsidian_palette(self):
        palette = QPalette()
        palette.setColor(QPalette.Window, QColor("#1c1c1c"))
        palette.setColor(QPalette.WindowText, Qt.white)
        palette.setColor(QPalette.Base, QColor("#1c1c1c"))
        palette.setColor(QPalette.AlternateBase, QColor("#1c1c1c"))
        palette.setColor(QPalette.ToolTipBase, QColor("#1c1c1c"))
        palette.setColor(QPalette.ToolTipText, Qt.white)
        palette.setColor(QPalette.Text, Qt.white)
        palette.setColor(QPalette.Button, QColor("#1c1c1c"))
        palette.setColor(QPalette.ButtonText, Qt.white)
        palette.setColor(QPalette.BrightText, Qt.red)
        palette.setColor(QPalette.Link, QColor("#6a0dad"))
        palette.setColor(QPalette.Highlight, QColor("#6200EE"))
        palette.setColor(QPalette.HighlightedText, Qt.white)
        return palette

    def create_redstone_palette(self):
        palette = QPalette()
        palette.setColor(QPalette.Window, QColor(53, 53, 53))
        palette.setColor(QPalette.WindowText, Qt.white)
        palette.setColor(QPalette.Base, QColor(25, 25, 25))
        palette.setColor(QPalette.AlternateBase, QColor(53, 53, 53))
        palette.setColor(QPalette.ToolTipBase, Qt.white)
        palette.setColor(QPalette.ToolTipText, Qt.white)
        palette.setColor(QPalette.Text, Qt.white)
        palette.setColor(QPalette.Button, QColor(53, 53, 53))
        palette.setColor(QPalette.ButtonText, Qt.white)
        palette.setColor(QPalette.BrightText, Qt.red)
        palette.setColor(QPalette.Link, QColor(42, 130, 218))
        palette.setColor(QPalette.Highlight, QColor(255 , 0, 0))
        palette.setColor(QPalette.HighlightedText, Qt.white)
        return palette


    def create_alpha_palette(self):
        palette = QPalette()
        palette.setColor(QPalette.Window, QColor("#31363b"))
        palette.setColor(QPalette.WindowText, Qt.white)
        palette.setColor(QPalette.Base, QColor(25, 25, 25))
        palette.setColor(QPalette.AlternateBase, QColor("#31363b"))
        palette.setColor(QPalette.ToolTipBase, Qt.white)
        palette.setColor(QPalette.ToolTipText, Qt.white)
        palette.setColor(QPalette.Text, Qt.white)
        palette.setColor(QPalette.Button, QColor("#31363b"))
        palette.setColor(QPalette.ButtonText, Qt.white)
        palette.setColor(QPalette.BrightText, Qt.red)
        palette.setColor(QPalette.Link, QColor(42, 130, 218))
        palette.setColor(QPalette.Highlight, QColor(42, 130, 218))
        palette.setColor(QPalette.HighlightedText, Qt.white)
        return palette

    def create_strawberry_palette(self):
        palette = QPalette()
        palette.setColor(QPalette.Window, QColor("#fce8e6"))
        palette.setColor(QPalette.WindowText, Qt.black)
        palette.setColor(QPalette.Base, QColor("#f8d7d5"))
        palette.setColor(QPalette.AlternateBase, QColor("#fce8e6"))
        palette.setColor(QPalette.ToolTipBase, QColor("#f8d7d5"))
        palette.setColor(QPalette.ToolTipText, Qt.black)
        palette.setColor(QPalette.Text, Qt.black)
        palette.setColor(QPalette.Button, QColor("#fce8e6"))
        palette.setColor(QPalette.ButtonText, Qt.black)
        palette.setColor(QPalette.BrightText, Qt.red)
        palette.setColor(QPalette.Link, QColor("#ff4d4d"))
        palette.setColor(QPalette.Highlight, QColor("#ff8080"))
        palette.setColor(QPalette.HighlightedText, Qt.black)
        return palette

    def create_native_palette(self):
        palette = QPalette()
        return palette



    def check_for_update_start(self):
        try:
            with open("version.json") as f:
                local_version_info = json.load(f)
                local_version = local_version_info.get("version")
                logging.info(f"Local version: {local_version}")
                if local_version:
                    remote_version_info = self.fetch_remote_version()
                    remote_version = remote_version_info.get("version")
                    logging.info(f"Remote version: {remote_version}")
                    if remote_version and remote_version != local_version:
                        update_message = f"A new version ({remote_version}) is available!\nDo you want to download it now?"
                        update_dialog = QMessageBox.question(self, "Update Available", update_message, QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
                        if update_dialog == QMessageBox.Yes:
                            # Download and apply the update
                            self.download_update(remote_version_info)
                    else:
                        print("Up to Date", "You already have the latest version!")
                else:
                    logging.error("Failed to read local version information.")
                    QMessageBox.critical(self, "Error", "Failed to check for updates.")
        except Exception as e:
            logging.error("Error checking for updates: %s", str(e))
            QMessageBox.critical(self, "Error", "Failed to check for updates.")

    def check_for_update(self):
        try:
            with open("version.json") as f:
                local_version_info = json.load(f)
                local_version = local_version_info.get("version")
                logging.info(f"Local version: {local_version}")
                if local_version:
                    remote_version_info = self.fetch_remote_version()
                    remote_version = remote_version_info.get("version")
                    logging.info(f"Remote version: {remote_version}")
                    if remote_version and remote_version != local_version:
                        update_message = f"A new version ({remote_version}) is available!\nDo you want to download it now?"
                        update_dialog = QMessageBox.question(self, "Update Available", update_message, QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
                        if update_dialog == QMessageBox.Yes:
                            # Download and apply the update
                            self.download_update(remote_version_info)
                    else:
                        QMessageBox.information(self, "Up to Date", "You already have the latest version!")
                else:
                    logging.error("Failed to read local version information.")
                    QMessageBox.critical(self, "Error", "Failed to check for updates.")
        except Exception as e:
            logging.error("Error checking for updates: %s", str(e))
            QMessageBox.critical(self, "Error", "Failed to check for updates.")

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
                    QMessageBox.critical(self, "Error", f"Failed to download update file: {filename}")
            
            # Move downloaded files one directory up
            for file in os.listdir(update_folder):
                src = os.path.join(update_folder, file)
                dst = os.path.join(os.path.dirname(update_folder), file)
                shutil.move(src, dst)
            
            # Remove the update folder
            shutil.rmtree(update_folder)
            
            QMessageBox.information(self, "Update", "Updates downloaded successfully.")
        except Exception as e:
            logging.error("Error downloading updates: %s", str(e))
            QMessageBox.critical(self, "Error", "Failed to download updates.")

    def start_discord_rcp(self):
        client_id = '1236906342086606848'  # Replace with your Discord application client ID
        presence = Presence(client_id)
        
        try:
            presence.connect()

            presence.update(
                state="In the menu",
                details="best launcher to exist",
                large_image="launcher_icon",  # Replace with your image key for the launcher image
                large_text="PicoDulce Launcher",  # Replace with the text for the launcher image
                start=time.time(),
                buttons=[{"label": "Download", "url": "https://github.com/nixietab/picodulce"}]  # Add your button here
            )
            # Keep the script running to maintain the presence
            while True:
                time.sleep(15)  # Update presence every 15 seconds
        except Exception as e:
            logging.error("Failed to start Discord RCP: %s", str(e))

    def open_mod_loader_and_version_menu(self):
        dialog = ModLoaderAndVersionMenu()
        dialog.finished.connect(self.populate_installed_versions)
        dialog.exec_()

class ModLoaderAndVersionMenu(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Mod Loader and Version Menu")
        self.setGeometry(100, 100, 400, 300)

        main_layout = QVBoxLayout(self)

        tab_widget = QTabWidget()
        main_layout.addWidget(tab_widget)

        # Create tabs
        install_mod_tab = QWidget()
        download_version_tab = QWidget()

        tab_widget.addTab(download_version_tab, "Download Version")
        tab_widget.addTab(install_mod_tab, "Install Mod Loader")

        # Add content to "Install Mod Loader" tab
        self.setup_install_mod_loader_tab(install_mod_tab)

        # Add content to "Download Version" tab
        self.setup_download_version_tab(download_version_tab)

    def setup_install_mod_loader_tab(self, install_mod_tab):
        layout = QVBoxLayout(install_mod_tab)

        # Create title label
        title_label = QLabel('Mod Loader Installer')
        title_label.setFont(QFont("Arial", 14))
        layout.addWidget(title_label)

        # Create checkboxes for mod loaders
        forge_checkbox = QCheckBox('Forge')
        fabric_checkbox = QCheckBox('Fabric')
        layout.addWidget(forge_checkbox)
        layout.addWidget(fabric_checkbox)

        # Create dropdown menu for versions
        version_combo = QComboBox()
        layout.addWidget(version_combo)

        def update_versions():
            version_combo.clear()
            if forge_checkbox.isChecked():
                self.populate_available_releases(version_combo, True, False)
            elif fabric_checkbox.isChecked():
                self.populate_available_releases(version_combo, False, True)

        forge_checkbox.clicked.connect(update_versions)
        fabric_checkbox.clicked.connect(update_versions)

        # Create install button
        install_button = QPushButton('Install')
        install_button.clicked.connect(lambda: self.install_mod_loader(version_combo.currentText(), forge_checkbox.isChecked(), fabric_checkbox.isChecked()))
        layout.addWidget(install_button)

    def setup_download_version_tab(self, download_version_tab):
        layout = QVBoxLayout(download_version_tab)
        
        # Create title label
        title_label = QLabel('Download Version')
        title_label.setFont(QFont("Arial", 14))
        layout.addWidget(title_label)

        # Create checkboxes for different version types
        release_checkbox = QCheckBox('Releases')
        snapshot_checkbox = QCheckBox('Snapshots')
        alpha_checkbox = QCheckBox('Alpha')
        beta_checkbox = QCheckBox('Beta')
        layout.addWidget(release_checkbox)
        layout.addWidget(snapshot_checkbox)
        layout.addWidget(alpha_checkbox)
        layout.addWidget(beta_checkbox)

        # Create dropdown menu for versions
        version_combo = QComboBox()
        layout.addWidget(version_combo)

        def update_versions():
            version_combo.clear()
            options = []
            if release_checkbox.isChecked():
                options.append('--release')
            if snapshot_checkbox.isChecked():
                options.append('--snapshot')
            if alpha_checkbox.isChecked():
                options.append('--alpha')
            if beta_checkbox.isChecked():
                options.append('--beta')
            if options:
                try:
                    process = subprocess.Popen(['picomc', 'version', 'list'] + options, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                    output, error = process.communicate()
                    if process.returncode != 0:
                        raise subprocess.CalledProcessError(process.returncode, process.args, error)
                except FileNotFoundError:
                    logging.error("'picomc' command not found. Please make sure it's installed and in your PATH.")
                    return
                except subprocess.CalledProcessError as e:
                    logging.error("Error: %s", e.stderr)
                    return

                # Parse the output and replace '[local]' with a space
                versions = output.splitlines()
                versions = [version.replace('[local]', ' ').strip() for version in versions]
                version_combo.addItems(versions)

        release_checkbox.clicked.connect(update_versions)
        snapshot_checkbox.clicked.connect(update_versions)
        alpha_checkbox.clicked.connect(update_versions)
        beta_checkbox.clicked.connect(update_versions)

        # Create download button
        download_button = QPushButton('Download')
        download_button.clicked.connect(lambda: self.download_version(version_combo.currentText()))
        layout.addWidget(download_button)

    def download_version(self, version):  # <- Define download_version function
        try:
            subprocess.run(['picomc', 'version', 'prepare', version], check=True)
            QMessageBox.information(self, "Success", f"Version {version} prepared successfully!")
        except subprocess.CalledProcessError as e:
            error_message = f"Error preparing {version}: {e.stderr.decode()}"
            QMessageBox.critical(self, "Error", error_message)
            logging.error(error_message)

    def populate_available_releases(self, version_combo, install_forge, install_fabric):
        try:
            process = subprocess.Popen(['picomc', 'version', 'list', '--release'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            output, error = process.communicate()
            if process.returncode != 0:
                raise subprocess.CalledProcessError(process.returncode, process.args, error)
        except FileNotFoundError:
            logging.error("'picomc' command not found. Please make sure it's installed and in your PATH.")
            return
        except subprocess.CalledProcessError as e:
            logging.error("Error: %s", e.stderr)
            return

        if install_fabric:
            releases = [version for version in output.splitlines() if version.startswith("1.") and int(version.split('.')[1]) >= 14]
        elif install_forge:
            releases = [version for version in output.splitlines() if version.startswith("1.") and float(version.split('.')[1]) >= 5]
        else:
            releases = output.splitlines()

        version_combo.clear()
        version_combo.addItems(releases)

    def install_mod_loader(self, version, install_forge, install_fabric):
        if not install_forge and not install_fabric:
            QMessageBox.warning(self, "Select Mod Loader", "Please select at least one mod loader.")
            return

        mod_loader = None
        if install_forge:
            mod_loader = 'forge'
        elif install_fabric:
            mod_loader = 'fabric'

        if not mod_loader:
            QMessageBox.warning(self, "Select Mod Loader", "Please select at least one mod loader.")
            return

        try:
            if mod_loader == 'forge':
                subprocess.run(['picomc', 'mod', 'loader', 'forge', 'install', '--game', version], check=True)
            elif mod_loader == 'fabric':
                subprocess.run(['picomc', 'mod', 'loader', 'fabric', 'install', version], check=True)
            QMessageBox.information(self, "Success", f"{mod_loader.capitalize()} installed successfully for version {version}!")
        except subprocess.CalledProcessError as e:
            error_message = f"Error installing {mod_loader} for version {version}: {e.stderr.decode()}"
            QMessageBox.critical(self, "Error", error_message)
            logging.error(error_message)


if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = PicomcVersionSelector()
    window.show()
    sys.exit(app.exec_())
