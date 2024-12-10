import sys
import subprocess
import threading
from threading import Thread
import logging
import shutil
import platform
import requests
import json
import os
import time
from PyQt5.QtWidgets import QApplication, QComboBox, QWidget, QVBoxLayout, QListWidget, QPushButton, QMessageBox, QDialog, QHBoxLayout, QLabel, QLineEdit, QCheckBox, QTabWidget, QFrame, QSpacerItem, QSizePolicy, QMainWindow, QGridLayout, QTextEdit
from PyQt5.QtGui import QFont, QIcon, QColor, QPalette, QMovie, QPixmap, QDesktopServices
from PyQt5.QtCore import Qt, QObject, pyqtSignal, QThread, QUrl, QMetaObject, Q_ARG
from datetime import datetime

logging.basicConfig(level=logging.ERROR, format='%(asctime)s - %(levelname)s - %(message)s')

class PicomcVersionSelector(QWidget):
    def __init__(self):
        self.open_dialogs = []
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
        current_date = datetime.now()
        if (current_date.month == 12 and current_date.day >= 8) or (current_date.month == 1 and current_date.day <= 1):
            self.setWindowIcon(QIcon('holiday.ico'))  # Set holiday icon
        else:
            self.setWindowIcon(QIcon('launcher_icon.ico'))  # Set regular icon


        self.setGeometry(100, 100, 400, 250)

        # Set application style and palette
        QApplication.setStyle("Fusion")
        self.check_config_file()
        palette_type = self.config.get("Palette", "Dark")
        palette = self.get_palette(palette_type)
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

    def keyPressEvent(self, event):
        focus_widget = self.focusWidget()
        if event.key() == Qt.Key_Down:
            self.focusNextChild()  # Move focus to the next widget
        elif event.key() == Qt.Key_Up:
            self.focusPreviousChild()  # Move focus to the previous widget
        elif event.key() in [Qt.Key_Return, Qt.Key_Enter]:
            if isinstance(focus_widget, QPushButton):
                focus_widget.click()  # Trigger the button click
            elif isinstance(focus_widget, QComboBox):
                focus_widget.showPopup()  # Show dropdown for combo box
        else:
            super().keyPressEvent(event)

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
        dialog.setFixedSize(300, 250)

        # Create title label
        title_label = QLabel('Settings')
        title_label.setFont(QFont("Arial", 14))

        # Add settings components here...
        layout = QVBoxLayout()
        layout.addWidget(title_label)

        # Create checkboxes
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
        themes = ['Dark', 'Obsidian', 'Redstone', 'Alpha', 'Strawberry', "Native", "Christmas"]  # Replace with your actual themes
        theme_combobox.addItems(themes)
        current_theme_index = themes.index(self.config.get("Palette", "Default Theme"))
        theme_combobox.setCurrentIndex(current_theme_index)
        layout.addWidget(theme_combobox)

        # Create Save button
        save_button = QPushButton('Save')
        save_button.clicked.connect(lambda: self.save_settings(discord_rcp_checkbox.isChecked(), check_updates_checkbox.isChecked(), theme_combobox.currentText()))
        layout.addWidget(save_button)

        # Create Check for updates button
        update_button = QPushButton('Check for updates')
        update_button.clicked.connect(self.check_for_update)
        layout.addWidget(update_button)

        # Create Open game directory button
        open_game_directory_button = QPushButton('Open game directory')
        open_game_directory_button.clicked.connect(self.open_game_directory)
        layout.addWidget(open_game_directory_button)

        # Create "Stats for Nerds" button
        stats_button = QPushButton('Stats for Nerds')
        stats_button.clicked.connect(self.show_system_info)
        layout.addWidget(stats_button)

        dialog.setLayout(layout)
        dialog.exec_()

    def get_palette(self, palette_type):
        """Retrieve the corresponding palette based on the palette type."""
        palettes = {
            "Dark": self.create_dark_palette,
            "Obsidian": self.create_obsidian_palette,
            "Redstone": self.create_redstone_palette,
            "Alpha": self.create_alpha_palette,
            "Strawberry": self.create_strawberry_palette,
            "Native": self.create_native_palette,
            "Christmas": self.create_christmas_palette,
        }
        # Default to dark palette if the type is not specified or invalid
        return palettes.get(palette_type, self.create_dark_palette)()

    def get_system_info(self):
        # Get system information
        java_version = subprocess.getoutput("java -version 2>&1 | head -n 1")
        python_version = sys.version
        pip_version = subprocess.getoutput("pip --version")
        architecture = platform.architecture()[0]
        operating_system = platform.system() + " " + platform.release()

        # Get versions of installed pip packages
        installed_packages = subprocess.getoutput("pip list")

        return f"Java Version: {java_version}\nPython Version: {python_version}\nPip Version: {pip_version}\n" \
               f"Architecture: {architecture}\nOperating System: {operating_system}\n\nPip Installed Packages:\n{installed_packages}"

    def show_system_info(self):
        system_info = self.get_system_info()

        # Create a dialog to show the system info in a text box
        info_dialog = QDialog(self)
        info_dialog.setWindowTitle('Stats for Nerds')

        layout = QVBoxLayout()

        # Create a text box to display the system info
        text_box = QTextEdit()
        text_box.setText(system_info)
        text_box.setReadOnly(True)  # Make the text box read-only
        layout.addWidget(text_box)

        # Create a close button
        close_button = QPushButton('Close')
        close_button.clicked.connect(info_dialog.close)
        layout.addWidget(close_button)

        info_dialog.setLayout(layout)
        info_dialog.exec_()

    def open_game_directory(self):
        try:
            # Run the command and capture the output
            result = subprocess.run(['picomc', 'instance', 'dir'], capture_output=True, text=True, check=True)
            game_directory = result.stdout.strip()

            # Open the directory in the system's file explorer
            QDesktopServices.openUrl(QUrl.fromLocalFile(game_directory))
        except subprocess.CalledProcessError as e:
            print(f"Error running picomc command: {e}")

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
        
        # Check if the config file exists
        if not os.path.exists(config_path):
            logging.error("Config file not found.")
            self.populate_installed_versions_normal_order()
            return

        # Load config from the file
        try:
            with open(config_path, "r") as config_file:
                self.config = json.load(config_file)
        except json.JSONDecodeError as e:
            logging.error("Failed to load config: %s", e)
            self.populate_installed_versions_normal_order()
            return

        # Run the command and capture the output
        try:
            process = subprocess.Popen(['picomc', 'version', 'list'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            output, error = process.communicate()
            
            if process.returncode != 0:
                raise subprocess.CalledProcessError(process.returncode, process.args, output=output, stderr=error)
        except FileNotFoundError:
            logging.error("'picomc' command not found. Please ensure it's installed and in your PATH.")
            return
        except subprocess.CalledProcessError as e:
            logging.error("Error running 'picomc': %s", e.stderr)
            return

        # Parse the output and replace '[local]' with a space
        versions = [version.replace('[local]', ' ').strip() for version in output.splitlines()]

        # Get the last played version from the config
        last_played = self.config.get("LastPlayed", "")

        # If last played is not empty and is in the versions list, move it to the top
        if last_played and last_played in versions:
            versions.remove(last_played)
            versions.insert(0, last_played)

        # Populate the installed versions combo box
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
            # Use the interpreter from the current environment
            interpreter = sys.executable
            subprocess.Popen([interpreter, './marroc.py'])
        except FileNotFoundError:
            logging.error("'marroc.py' not found.")
            QMessageBox.critical(self, "Error", "'marroc.py' not found.")

    def play_instance(self):
        if self.installed_version_combo.count() == 0:
            QMessageBox.warning(self, "No Version Available", "Please download a version first.")
            return

        # Check if there are any accounts
        try:
            account_list_output = subprocess.check_output(["picomc", "account", "list"]).decode("utf-8").strip()
            if not account_list_output:
                QMessageBox.warning(self, "No Account Available", "Please create an account first.")
                return

            # Check if the selected account has a '*' (indicating it's the selected one)
            if '*' not in account_list_output:
                QMessageBox.warning(self, "No Account Selected", "Please select an account.")
                return
        except subprocess.CalledProcessError as e:
            error_message = f"Error fetching accounts: {str(e)}"
            logging.error(error_message)
            QMessageBox.critical(self, "Error", error_message)
            return

        selected_instance = self.installed_version_combo.currentText()
        logging.info(f"Selected instance: {selected_instance}")

        play_thread = threading.Thread(target=self.run_game, args=(selected_instance,))
        play_thread.start()

    def run_game(self, selected_instance):
        try:
            # Update lastplayed field in config.json on a separate thread
            update_thread = threading.Thread(target=self.update_last_played, args=(selected_instance,))
            update_thread.start()
            subprocess.run(['picomc', 'play', selected_instance], check=True)
        except subprocess.CalledProcessError as e:
            error_message = f"Error playing {selected_instance}: {e}"
            logging.error(error_message)
            # Use QMetaObject.invokeMethod to call showError safely
            QMetaObject.invokeMethod(self, "showError", Qt.QueuedConnection, 
                                     Q_ARG(str, "Error"), Q_ARG(str, error_message))

    def update_last_played(self, selected_instance):
        config_path = "config.json"
        self.config["LastPlayed"] = selected_instance
        with open(config_path, "w") as config_file:
            json.dump(self.config, config_file, indent=4)


    def showError(self, title, message):
        QMessageBox.critical(self, title, message)

    def manage_accounts(self):
        # Main account management dialog
        dialog = QDialog(self)
        self.open_dialogs.append(dialog)
        dialog.setWindowTitle('Manage Accounts')
        dialog.setFixedSize(400, 250)

        # Title
        title_label = QLabel('Manage Accounts')
        title_label.setFont(QFont("Arial", 14))
        title_label.setAlignment(Qt.AlignCenter)  # Center the text
        # Dropdown for selecting accounts
        account_combo = QComboBox()
        self.populate_accounts(account_combo)

        # Buttons
        create_account_button = QPushButton('Create Account')
        create_account_button.clicked.connect(self.open_create_account_dialog)

        authenticate_button = QPushButton('Authenticate Account')
        authenticate_button.clicked.connect(lambda: self.authenticate_account(dialog, account_combo.currentText()))

        remove_account_button = QPushButton('Remove Account')
        remove_account_button.clicked.connect(lambda: self.remove_account(dialog, account_combo.currentText()))

        # New button to set the account idk
        set_default_button = QPushButton('Select')
        set_default_button.setFixedWidth(100)  # Set button width to a quarter
        set_default_button.clicked.connect(lambda: self.set_default_account(account_combo.currentText(), dialog))

        # Layout for account selection (dropdown and set default button)
        account_layout = QHBoxLayout()
        account_layout.addWidget(account_combo)
        account_layout.addWidget(set_default_button)

        button_layout = QHBoxLayout()
        button_layout.addWidget(create_account_button)
        button_layout.addWidget(authenticate_button)
        button_layout.addWidget(remove_account_button)

        # Main layout
        layout = QVBoxLayout()
        layout.addWidget(title_label)
        layout.addLayout(account_layout)
        layout.addLayout(button_layout)

        dialog.setLayout(layout)
        dialog.exec_()
        self.open_dialogs.remove(dialog)

    def open_create_account_dialog(self):
        # Dialog for creating a new account
        dialog = QDialog(self)
        self.open_dialogs.append(dialog)
        dialog.setWindowTitle('Create Account')
        dialog.setFixedSize(300, 150)

        username_input = QLineEdit()
        username_input.setPlaceholderText('Enter Username')

        microsoft_checkbox = QCheckBox('Microsoft Account')

        create_button = QPushButton('Create')
        create_button.clicked.connect(lambda: self.create_account(dialog, username_input.text(), microsoft_checkbox.isChecked()))

        layout = QVBoxLayout()
        layout.addWidget(username_input)
        layout.addWidget(microsoft_checkbox)
        layout.addWidget(create_button)

        dialog.setLayout(layout)
        dialog.exec_()
        self.open_dialogs.remove(dialog)

    def authenticate_account(self, dialog, account_name):
        # Authenticate a selected account
        account_name = account_name.strip().lstrip(" * ")
        if not account_name:
            QMessageBox.warning(dialog, "Warning", "Please select an account to authenticate.")
            return

        try:
            subprocess.run(['picomc', 'account', 'authenticate', account_name], check=True)
            QMessageBox.information(self, "Success", f"Account '{account_name}' authenticated successfully!")
        except subprocess.CalledProcessError as e:
            error_message = f"Error authenticating account '{account_name}': {e.stderr.decode()}"
            logging.error(error_message)
            QMessageBox.critical(self, "Error", error_message)

    def remove_account(self, dialog, username):
        # Remove a selected account
        username = username.strip().lstrip(" * ")
        if not username:
            QMessageBox.warning(dialog, "Warning", "Please select an account to remove.")
            return

        confirm_message = f"Are you sure you want to remove the account '{username}'?\nThis action cannot be undone."
        confirm_dialog = QMessageBox.question(dialog, "Confirm Removal", confirm_message, QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if confirm_dialog == QMessageBox.Yes:
            try:
                subprocess.run(['picomc', 'account', 'remove', username], check=True)
                QMessageBox.information(dialog, "Success", f"Account '{username}' removed successfully!")
                self.populate_accounts_for_all_dialogs()
            except subprocess.CalledProcessError as e:
                error_message = f"Error removing account: {e.stderr.decode()}"
                logging.error(error_message)
                QMessageBox.critical(dialog, "Error", error_message)

    def create_account(self, dialog, username, is_microsoft):
        # Create a new account
        if not username.strip():
            QMessageBox.warning(dialog, "Warning", "Username cannot be blank.")
            return

        try:
            command = ['picomc', 'account', 'create', username]
            if is_microsoft:
                command.append('--ms')

            subprocess.run(command, check=True)
            QMessageBox.information(dialog, "Success", f"Account '{username}' created successfully!")
            self.populate_accounts_for_all_dialogs()
        except subprocess.CalledProcessError as e:
            error_message = f"Error creating account: {e.stderr.decode()}"
            logging.error(error_message)
            QMessageBox.critical(dialog, "Error", error_message)

    def populate_accounts(self, account_combo):
        # Populate the account dropdown
        try:
            process = subprocess.Popen(['picomc', 'account', 'list'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            output, error = process.communicate()
            if process.returncode != 0:
                raise subprocess.CalledProcessError(process.returncode, process.args, error)

            # Process accounts, keeping the one with "*" at the top
            accounts = output.splitlines()
            starred_account = None
            normal_accounts = []

            for account in accounts:
                account = account.strip()
                if account.startswith('*'):
                    starred_account = account.lstrip(' *').strip()
                else:
                    normal_accounts.append(account)

            # Clear the combo box and add accounts
            account_combo.clear()

            # Add the starred account first, if exists
            if starred_account:
                account_combo.addItem(f"* {starred_account}")

            # Add the normal accounts
            for account in normal_accounts:
                account_combo.addItem(account)

        except FileNotFoundError:
            logging.error("'picomc' command not found. Please make sure it's installed and in your PATH.")
        except subprocess.CalledProcessError as e:
            logging.error(f"Error: {e.stderr}")

    def populate_accounts_for_all_dialogs(self):
        # Update account dropdowns in all open dialogs
        for dialog in self.open_dialogs:
            combo_box = dialog.findChild(QComboBox)
            if combo_box:
                self.populate_accounts(combo_box)

    def set_default_account(self, account_name, dialog):
        # Set the selected account as the default
        account_name = account_name.strip().lstrip(" * ")
        if not account_name:
            QMessageBox.warning(dialog, "Warning", "Please select an account to set as default.")
            return

        try:
            subprocess.run(['picomc', 'account', 'setdefault', account_name], check=True)
            QMessageBox.information(self, "Success", f"Account '{account_name}' set as default!")
            self.populate_accounts_for_all_dialogs()
        except subprocess.CalledProcessError as e:
            error_message = f"Error setting default account '{account_name}': {e.stderr.decode()}"
            logging.error(error_message)
            QMessageBox.critical(self, "Error", error_message)

    def show_about_dialog(self):
        # Load the version number from version.json
        try:
            with open('version.json', 'r') as version_file:
                version_data = json.load(version_file)
                version_number = version_data.get('version', 'unknown version')
        except (FileNotFoundError, json.JSONDecodeError):
            version_number = 'unknown version'

        about_message = (
            f"PicoDulce Launcher (v{version_number})\n\n"
            "A simple Minecraft launcher built using Qt, based on the picomc project.\n\n"
            "Credits:\n"
            "Nixietab: Code and UI design\n"
            "Wabaano: Graphic design\n"
            "Olinad: Christmas!!!!"
        )
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

    def create_christmas_palette(self):
        palette = QPalette()
        # I know is shitty ok
        # Background colors
        palette.setColor(QPalette.Window, QColor(34, 49, 34))  # Deep evergreen
        palette.setColor(QPalette.WindowText, QColor(210, 255, 210))  # Soft, frosty green text
        palette.setColor(QPalette.Base, QColor(17, 34, 17))  # Dark forest green
        palette.setColor(QPalette.AlternateBase, QColor(25, 51, 25))  # Slightly lighter green for contrast
        palette.setColor(QPalette.ToolTipBase, QColor(245, 255, 245))  # Light green for tooltips
        palette.setColor(QPalette.ToolTipText, QColor(34, 139, 34))  # Vibrant green for tooltip text
        
        # Text colors
        palette.setColor(QPalette.Text, QColor(245, 255, 245))  # Light green for standard text
        palette.setColor(QPalette.Button, QColor(0, 100, 0))  # Dark green for buttons
        palette.setColor(QPalette.ButtonText, QColor(245, 255, 245))  # Light green button text
        palette.setColor(QPalette.BrightText, QColor(60, 179, 113))  # Bright mint green for emphasis
        palette.setColor(QPalette.Link, QColor(42, 130, 218))  # Blue links for contrast
        
        # Highlight colors
        palette.setColor(QPalette.Highlight, QColor(0, 128, 0))  # Rich pine green highlight
        palette.setColor(QPalette.HighlightedText, QColor(245, 255, 245))  # Light green text on highlights

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
        from pypresence import Presence
        client_id = '1236906342086606848'
        presence = Presence(client_id)
        
        try:
            presence.connect()

            presence.update(
                state="In the menu",
                details="best launcher to exist",
                large_image="launcher_icon",  
                large_text="PicoDulce Launcher",
                start=time.time(),
                buttons=[{"label": "Download", "url": "https://github.com/nixietab/picodulce"}] 
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

class DownloadThread(QThread):
    completed = pyqtSignal(bool, str)

    def __init__(self, version):
        super().__init__()
        self.version = version

    def run(self):
        try:
            subprocess.run(['picomc', 'version', 'prepare', self.version], check=True)
            self.completed.emit(True, f"Version {self.version} prepared successfully!")
        except subprocess.CalledProcessError as e:
            error_message = f"Error preparing {self.version}: {e.stderr.decode()}"
            self.completed.emit(False, error_message)

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
        self.forge_checkbox = QCheckBox('Forge')
        self.fabric_checkbox = QCheckBox('Fabric')
        layout.addWidget(self.forge_checkbox)
        layout.addWidget(self.fabric_checkbox)

        # Create dropdown menu for versions
        self.version_combo_mod = QComboBox()
        layout.addWidget(self.version_combo_mod)

        def update_versions():
            self.version_combo_mod.clear()
            if self.forge_checkbox.isChecked():
                self.populate_available_releases(self.version_combo_mod, True, False)
            elif self.fabric_checkbox.isChecked():
                self.populate_available_releases(self.version_combo_mod, False, True)

        self.forge_checkbox.clicked.connect(update_versions)
        self.fabric_checkbox.clicked.connect(update_versions)

        # Create install button
        install_button = QPushButton('Install')
        install_button.clicked.connect(lambda: self.install_mod_loader(
            self.version_combo_mod.currentText(), 
            self.forge_checkbox.isChecked(), 
            self.fabric_checkbox.isChecked()
        ))
        layout.addWidget(install_button)

    def setup_download_version_tab(self, download_version_tab):
        layout = QVBoxLayout(download_version_tab)

        # Create title label
        title_label = QLabel('Download Version')
        title_label.setFont(QFont("Arial", 14))
        layout.addWidget(title_label)

        # Create checkboxes for different version types
        self.release_checkbox = QCheckBox('Releases')
        self.snapshot_checkbox = QCheckBox('Snapshots')
        self.alpha_checkbox = QCheckBox('Alpha')
        self.beta_checkbox = QCheckBox('Beta')
        layout.addWidget(self.release_checkbox)
        layout.addWidget(self.snapshot_checkbox)
        layout.addWidget(self.alpha_checkbox)
        layout.addWidget(self.beta_checkbox)

        # Create dropdown menu for versions
        self.version_combo = QComboBox()
        layout.addWidget(self.version_combo)

        def update_versions():
            self.version_combo.clear()
            options = []
            if self.release_checkbox.isChecked():
                options.append('--release')
            if self.snapshot_checkbox.isChecked():
                options.append('--snapshot')
            if self.alpha_checkbox.isChecked():
                options.append('--alpha')
            if self.beta_checkbox.isChecked():
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
                self.version_combo.addItems(versions)
            # Update the download button state whenever versions are updated
            self.update_download_button_state()

        self.release_checkbox.clicked.connect(update_versions)
        self.snapshot_checkbox.clicked.connect(update_versions)
        self.alpha_checkbox.clicked.connect(update_versions)
        self.beta_checkbox.clicked.connect(update_versions)

        # Create download button
        self.download_button = QPushButton('Download')
        self.download_button.setEnabled(False)  # Initially disabled
        self.download_button.clicked.connect(lambda: self.download_version(self.version_combo.currentText()))
        layout.addWidget(self.download_button)

        # Connect the combo box signal to the update function
        self.version_combo.currentIndexChanged.connect(self.update_download_button_state)

    def update_download_button_state(self):
        self.download_button.setEnabled(self.version_combo.currentIndex() != -1)

    def show_popup(self):
        self.popup = QDialog(self)
        self.popup.setWindowTitle("Installing Version")
        layout = QVBoxLayout(self.popup)

        label = QLabel("The version is being installed...")
        layout.addWidget(label)

        movie = QMovie("drums.gif")
        gif_label = QLabel()
        gif_label.setMovie(movie)
        layout.addWidget(gif_label)

        movie.start()
        self.popup.setGeometry(200, 200, 300, 200)
        self.popup.setWindowModality(Qt.ApplicationModal)
        self.popup.show()

    def download_version(self, version):
        # Show the popup in the main thread
        self.show_popup()

        self.download_thread = DownloadThread(version)
        self.download_thread.completed.connect(self.on_download_completed)
        self.download_thread.start()

    def on_download_completed(self, success, message):
        self.popup.close()
        if success:
            QMessageBox.information(self, "Success", message)
        else:
            QMessageBox.critical(self, "Error", message)
        logging.error(message)

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
    current_date = datetime.now()

    # Set the application icon based on the date
    if (current_date.month == 12 and current_date.day >= 8) or (current_date.month == 1 and current_date.day <= 1):
        app.setWindowIcon(QIcon('holiday.ico'))  # Set holiday icon
    else:
        app.setWindowIcon(QIcon('launcher_icon.ico'))  # Set regular icon
    window = PicomcVersionSelector()
    window.show()
    sys.exit(app.exec_())
