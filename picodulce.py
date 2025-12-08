import sys
import subprocess
import threading
from threading import Thread
import logging
import re
import shutil
import platform
import requests
import json
import os
import time

from authser import MinecraftAuthenticator
from healthcheck import HealthCheck
import modulecli
import loaddaemon

from PyQt5.QtWidgets import QApplication, QComboBox, QWidget, QInputDialog, QVBoxLayout, QListWidget, QSpinBox, QFileDialog, QPushButton, QMessageBox, QDialog, QHBoxLayout, QLabel, QLineEdit, QCheckBox, QTabWidget, QFrame, QSpacerItem, QSizePolicy, QMainWindow, QGridLayout, QTextEdit, QListWidget, QListWidgetItem, QMenu, QRadioButton
from PyQt5.QtGui import QFont, QIcon, QColor, QPalette, QMovie, QPixmap, QDesktopServices, QBrush
from PyQt5.QtCore import Qt, QObject, pyqtSignal, QThread, QUrl, QMetaObject, Q_ARG, QByteArray, QSize
from datetime import datetime

logging.basicConfig(level=logging.ERROR, format='%(levelname)s - %(message)s')

class zucaroVersionSelector(QWidget):
    def __init__(self):
        self.current_state = "menu"
        self.open_dialogs = []

        # Set up and use the health_check module
        health_checker = HealthCheck()
        health_checker.themes_integrity()
        health_checker.check_config_file()
        health_checker.zucaro_health_check()
        self.config = health_checker.config

        themes_folder = "themes"
        theme_file = self.config.get("Theme", "Dark.json")

        # Ensure the theme file exists in the themes directory
        theme_file_path = os.path.join(themes_folder, theme_file)

        try:
            # Load and apply the theme from the file
            self.load_theme_from_file(theme_file_path, app)
            print(f"Theme '{theme_file}' loaded successfully.")
        except Exception as e:
            print(f"Error: Could not load theme '{theme_file}'. Falling back to default theme. {e}")

        super().__init__()
        self.init_ui()

        if self.config.get("CheckUpdate", False):
            self.check_for_update_start()

        if self.config.get("IsRCPenabled", False):
            discord_rcp_thread = Thread(target=self.start_discord_rcp)
            discord_rcp_thread.daemon = True  # Make the thread a daemon so it terminates when the main program exits
            discord_rcp_thread.start()

        if self.config.get("IsFirstLaunch", False):
            self.FirstLaunch()

        self.authenticator = MinecraftAuthenticator(self)
        self.authenticator.auth_finished.connect(self._on_auth_finished)


    def load_theme_from_file(self, file_path, app):
        self.theme = {}
        # Check if the file exists, else load 'Dark.json'
        if not os.path.exists(file_path):
            print(f"Theme file '{file_path}' not found. Loading default 'Dark.json' instead.")
            file_path = "themes/Dark.json"

            # Ensure the fallback file exists
            if not os.path.exists(file_path):
                raise FileNotFoundError(f"Default theme file '{file_path}' not found.")

        # Open and parse the JSON file
        with open(file_path, "r") as file:
            self.theme = json.load(file)  # Store theme as a class attribute

        # Ensure the required keys exist
        if "palette" not in self.theme:
            raise ValueError("JSON theme must contain a 'palette' section.")

        # Extract the palette
        palette_config = self.theme["palette"]

        # Create a new QPalette
        palette = QPalette()

        # Map palette roles to PyQt5 palette roles
        role_map = {
            "Window": QPalette.Window,
            "WindowText": QPalette.WindowText,
            "Base": QPalette.Base,
            "AlternateBase": QPalette.AlternateBase,
            "ToolTipBase": QPalette.ToolTipBase,
            "ToolTipText": QPalette.ToolTipText,
            "Text": QPalette.Text,
            "Button": QPalette.Button,
            "ButtonText": QPalette.ButtonText,
            "BrightText": QPalette.BrightText,
            "Link": QPalette.Link,
            "Highlight": QPalette.Highlight,
            "HighlightedText": QPalette.HighlightedText,
        }

        # Apply colors from the palette config
        for role_name, color_code in palette_config.items():
            if role_name in role_map:
                palette.setColor(role_map[role_name], QColor(color_code))
            else:
                print(f"Warning: '{role_name}' is not a recognized palette role.")
        
        # Apply the palette to the application
        app.setPalette(palette)

        # Apply style sheet if present
        if "stylesheet" in self.theme:
            stylesheet = self.theme["stylesheet"]
            app.setStyleSheet(stylesheet)
        else:
            print("Theme dosn't seem to have a stylesheet")

    def FirstLaunch(self):
        try:
            self.config_path = "config.json"
            print("Running zucaro instance create default command...")
            
            # Run the command using modulecli
            command = "instance create default"
            result = modulecli.run_command(command)
            if not result:
                print("Warning: modulecli returned empty response")
                result = ""
            print("Command output:", result)
            
            # Change the value of IsFirstLaunch to False
            self.config["IsFirstLaunch"] = False
            print("IsFirstLaunch set to False")

            # Save the updated config to the config.json file
            with open(self.config_path, 'w') as f:
                json.dump(self.config, f, indent=4)
            print("Configuration saved to", self.config_path)

        except Exception as e:
            print("An error occurred while creating the instance.")
            print("Error output:", str(e))

    def resize_event(self, event):
        if hasattr(self, 'movie_label'):
            self.movie_label.setGeometry(0, 0, 400, 320)
        event.accept()  # Accept the resize event

    def load_theme_background(self):
        """Load and set the theme background image from base64 data in the theme configuration."""
        if not self.config.get("ThemeBackground", False):  # Default to False if ThemeBackground is missing
            return

        # Get the base64 string for the background image from the theme file
        theme_background_base64 = self.theme.get("background_image_base64", "")
        if not theme_background_base64:
            print("No background GIF base64 string found in the theme file.")
            return

        try:
            # Decode the base64 string to get the binary data
            background_image_data = QByteArray.fromBase64(theme_background_base64.encode())
            temp_gif_path = "temp.gif"  # Write the gif into a temp file because Qt stuff
            with open(temp_gif_path, 'wb') as temp_gif_file:
                temp_gif_file.write(background_image_data)

            # Create a QMovie object from the temporary file
            movie = QMovie(temp_gif_path)
            if movie.isValid():
                self.setAutoFillBackground(True)
                palette = self.palette()

                # Set the QMovie to a QLabel
                self.movie_label = QLabel(self)
                self.movie_label.setMovie(movie)
                self.movie_label.setGeometry(0, 0, movie.frameRect().width(), movie.frameRect().height())
                self.movie_label.setScaledContents(True)  # Ensure the QLabel scales its contents
                movie.start()

                # Use the QLabel pixmap as the brush texture
                brush = QBrush(QPixmap(movie.currentPixmap()))
                brush.setStyle(Qt.TexturePattern)
                palette.setBrush(QPalette.Window, brush)
                self.setPalette(palette)

                # Adjust the QLabel size when the window is resized
                self.movie_label.resizeEvent = self.resize_event
            else:
                print("Error: Failed to load background GIF from base64 string.")
        except Exception as e:
            print(f"Error: Failed to decode and set background GIF. {e}")

    def init_ui(self):
        self.setWindowTitle('PicoDulce Launcher')  # Change window title
        current_date = datetime.now()
        if (current_date.month == 12 and current_date.day >= 8) or (current_date.month == 1 and current_date.day <= 1):
            self.setWindowIcon(QIcon('holiday.ico'))  # Set holiday icon
        else:
            self.setWindowIcon(QIcon('launcher_icon.ico'))  # Set regular icon

        self.setGeometry(100, 100, 400, 250)

        # Set application style and theme
        QApplication.setStyle("Fusion")
        with open("config.json", "r") as config_file:
            config = json.load(config_file)

        # Load theme background
        self.load_theme_background()

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

    def open_settings_dialog(self):
        dialog = QDialog(self)
        dialog.setWindowTitle('Settings')
        dialog.setMinimumSize(400, 300)

        tab_widget = QTabWidget()

        # --- Settings Tab ---
        settings_tab = QWidget()
        settings_layout = QVBoxLayout()

        title_label = QLabel('Settings')
        title_label.setFont(QFont("Arial", 14))

        discord_rcp_checkbox = QCheckBox('Discord Rich Presence')
        discord_rcp_checkbox.setChecked(self.config.get("IsRCPenabled", False))

        check_updates_checkbox = QCheckBox('Check Updates on Start')
        check_updates_checkbox.setChecked(self.config.get("CheckUpdate", False))

        bleeding_edge_checkbox = QCheckBox('Bleeding Edge')
        bleeding_edge_checkbox.setChecked(self.config.get("IsBleeding", False))
        bleeding_edge_checkbox.stateChanged.connect(lambda: self.show_bleeding_edge_popup(bleeding_edge_checkbox))

        settings_layout.addWidget(title_label)
        settings_layout.addWidget(discord_rcp_checkbox)
        settings_layout.addWidget(check_updates_checkbox)
        settings_layout.addWidget(bleeding_edge_checkbox)

        update_button = QPushButton('Check for updates')
        update_button.clicked.connect(self.check_for_update)

        open_game_directory_button = QPushButton('Open game directory')
        open_game_directory_button.clicked.connect(self.open_game_directory)

        stats_button = QPushButton('Stats for Nerds')
        stats_button.clicked.connect(self.show_system_info)

        settings_layout.addWidget(update_button)
        settings_layout.addWidget(open_game_directory_button)
        settings_layout.addWidget(stats_button)

        settings_tab.setLayout(settings_layout)

        # --- Customization Tab ---
        customization_tab = QWidget()
        customization_layout = QVBoxLayout()

        theme_background_checkbox = QCheckBox('Theme Background')
        theme_background_checkbox.setChecked(self.config.get("ThemeBackground", False))

        theme_filename = self.config.get('Theme', 'Dark.json')
        current_theme_label = QLabel(f"Current Theme: {theme_filename}")

        json_files_label = QLabel('Installed Themes:')
        self.json_files_list_widget = QListWidget()
        self.selected_theme = theme_filename
        themes_list = self.build_themes_list()
        self.populate_themes(self.json_files_list_widget, themes_list)
        self.json_files_list_widget.itemClicked.connect(
            lambda: self.on_theme_selected(self.json_files_list_widget, current_theme_label)
        )

        customization_layout.addWidget(theme_background_checkbox)
        customization_layout.addWidget(current_theme_label)
        customization_layout.addWidget(json_files_label)
        customization_layout.addWidget(self.json_files_list_widget)

        download_themes_button = QPushButton("Download More Themes")
        download_themes_button.clicked.connect(self.download_themes_window)
        customization_layout.addWidget(download_themes_button)

        customization_tab.setLayout(customization_layout)

        # --- Java Tab ---
        java_tab = QWidget()
        java_layout = QVBoxLayout()

        # Java path input with browse button
        java_path_layout = QHBoxLayout()
        java_path_input = QLineEdit()
        java_path_input.setPlaceholderText("Custom Java Installation Path")
        java_path_input.setText(self.config.get("JavaPath", ""))
        browse_button = QPushButton("Examine")
        browse_button.clicked.connect(lambda: self.browse_java_path(java_path_input))
        java_path_layout.addWidget(java_path_input)
        java_path_layout.addWidget(browse_button)

        ram_layout = QHBoxLayout()
        ram_label = QLabel("Assigned RAM:")
        ram_selector = QLineEdit()
        ram_selector.setPlaceholderText("2G")  # Show default placeholder
        
        # RAM selector
        ram_layout = QHBoxLayout()
        ram_label = QLabel("Assigned RAM:")
        ram_selector = QLineEdit()
        ram_selector.setPlaceholderText("2G")  # Show default placeholder
        
        # Set initial value from config, ensuring it ends with 'G'
        initial_ram = self.config.get("MaxRAM", "2G")
        if not initial_ram.endswith('G'):
            initial_ram += 'G'
        ram_selector.setText(initial_ram)
        
        # Ensure 'G' is always present when focus is lost
        def ensure_g_suffix():
            current_text = ram_selector.text()
            if not current_text.endswith('G'):
                ram_selector.setText(current_text + 'G')
        
        ram_selector.editingFinished.connect(ensure_g_suffix)
        
        ram_layout.addWidget(ram_label)
        ram_layout.addWidget(ram_selector)

        # Manage Java checkbox
        manage_java_checkbox = QCheckBox("Manage Java")
        manage_java_checkbox.setChecked(self.config.get("ManageJava", False))
        manage_java_info = QLabel(
                "<b>Disclaimer:</b> Experimental feature. Do not change these settings "
                "unless you are sure of what you are doing. "
                " If Manage Java is enabledthe launcher will download Java binaries for your OS only for Minecraft compatibility purposes.")
        manage_java_info.setWordWrap(True)

        # Add to layout
        java_layout.addLayout(java_path_layout)
        java_layout.addLayout(ram_layout)
        java_layout.addWidget(manage_java_checkbox)
        java_layout.addWidget(manage_java_info)

        java_tab.setLayout(java_layout)

        # Add all tabs
        tab_widget.addTab(settings_tab, "Settings")
        tab_widget.addTab(customization_tab, "Customization")
        tab_widget.addTab(java_tab, "Java")

        # Save button
        save_button = QPushButton('Save')
        save_button.clicked.connect(
            lambda: self.save_settings(
                discord_rcp_checkbox.isChecked(),
                check_updates_checkbox.isChecked(),
                theme_background_checkbox.isChecked(),
                self.selected_theme,
                bleeding_edge_checkbox.isChecked(),
                java_path_input.text(),
                ram_selector.text(),
                manage_java_checkbox.isChecked()
            )
        )

        main_layout = QVBoxLayout()
        main_layout.addWidget(tab_widget)
        main_layout.addWidget(save_button)

        dialog.setLayout(main_layout)
        dialog.exec_()

    def browse_java_path(self, java_path_input):
        path, _ = QFileDialog.getOpenFileName(self, "Select Java Executable")
        if path:
            java_path_input.setText(path)



    def show_bleeding_edge_popup(self, checkbox):
        if checkbox.isChecked():
            response = QMessageBox.question(
                self,
                "Bleeding Edge Feature",
                "Enabling 'Bleeding Edge' mode may expose you to unstable and experimental features. Do you want to enable it anyway? In normal mode, updates are only downloaded when a stable release is made.",
                QMessageBox.Yes | QMessageBox.No
            )
            if response == QMessageBox.No:
                checkbox.setChecked(False)

    def build_themes_list(self):
        themes_folder = os.path.join(os.getcwd(), "themes")
        themes_list = []
        if os.path.exists(themes_folder):
            json_files = [f for f in os.listdir(themes_folder) if f.endswith('.json')]
            for json_file in json_files:
                json_path = os.path.join(themes_folder, json_file)
                with open(json_path, 'r') as file:
                    theme_data = json.load(file)

                    # Get manifest details
                    manifest = theme_data.get("manifest", {})
                    name = manifest.get("name", "Unnamed")
                    description = manifest.get("description", "No description available")
                    author = manifest.get("author", "Unknown")

                    # Create display text and list item
                    display_text = f"{name}\n{description}\nBy: {author}"
                    themes_list.append((display_text, json_file))
        return themes_list

    def populate_themes(self, json_files_list_widget, themes_list):
        json_files_list_widget.clear()
        for display_text, json_file in themes_list:
            list_item = QListWidgetItem(display_text)
            list_item.setData(Qt.UserRole, json_file)  # Store the JSON filename as metadata

            # Style the name in bold
            font = QFont()
            font.setBold(False)
            list_item.setFont(font)

            json_files_list_widget.addItem(list_item)

        # Apply spacing and styling to the list
        json_files_list_widget.setStyleSheet("""
            QListWidget {
                padding: 1px;
            }
            QListWidget::item {
                margin: 3px 0;
                padding: 3px;
            }
        """)

    def on_theme_selected(self, json_files_list_widget, current_theme_label):
        selected_item = json_files_list_widget.currentItem()
        if selected_item:
            self.selected_theme = selected_item.data(Qt.UserRole)
            current_theme_label.setText(f"Current Theme: {self.selected_theme}")
            
     ## REPOSITORY BLOCK BEGGINS

    def download_themes_window(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("Themes Repository")
        dialog.setGeometry(100, 100, 800, 600)

        main_layout = QHBoxLayout(dialog)

        self.theme_list = QListWidget(dialog)
        self.theme_list.setSelectionMode(QListWidget.SingleSelection)
        self.theme_list.clicked.connect(self.on_theme_click)
        main_layout.addWidget(self.theme_list)

        right_layout = QVBoxLayout()

        self.details_label = QLabel(dialog)
        self.details_label.setWordWrap(True)
        self.details_label.setStyleSheet("padding: 10px;")
        right_layout.addWidget(self.details_label)

        self.image_label = QLabel(dialog)
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setStyleSheet("padding: 10px;")
        right_layout.addWidget(self.image_label)

        download_button = QPushButton("Download Theme", dialog)
        download_button.clicked.connect(self.theme_download)
        right_layout.addWidget(download_button)

        # Add a spacer to push the button to the bottom
        spacer = QSpacerItem(20, 40, QSizePolicy.Minimum, QSizePolicy.Expanding)
        right_layout.addItem(spacer)

        main_layout.addLayout(right_layout)
        dialog.setLayout(main_layout)

        dialog.finished.connect(lambda: self.update_themes_list())


        self.load_themes()
        dialog.exec_()

    def update_themes_list(self):
        themes_list = self.build_themes_list()
        self.populate_themes(self.json_files_list_widget, themes_list)

    def fetch_themes(self):
        try:
            with open("config.json", "r") as config_file:
                config = json.load(config_file)
            url = config.get("ThemeRepository")
            if not url:
                raise ValueError("ThemeRepository is not defined in config.json")
            response = requests.get(url)
            response.raise_for_status()
            return response.json()
        except (FileNotFoundError, json.JSONDecodeError) as config_error:
            self.show_error_popup("Error reading configuration", f"An error occurred while reading config.json: {config_error}")
            return {}
        except requests.exceptions.RequestException as fetch_error:
            self.show_error_popup("Error fetching themes", f"An error occurred while fetching themes: {fetch_error}")
            return {}
        except ValueError as value_error:
            self.show_error_popup("Configuration Error", str(value_error))
            return {}

    def download_theme_json(self, theme_url, theme_name):
        try:
            response = requests.get(theme_url)
            response.raise_for_status()
            if not os.path.exists('themes'):
                os.makedirs('themes')
            theme_filename = os.path.join('themes', f'{theme_name}.json')
            with open(theme_filename, 'wb') as f:
                f.write(response.content)
            print(f"Downloaded {theme_name} theme to {theme_filename}")
        except requests.exceptions.RequestException as e:
            self.show_error_popup("Error downloading theme", f"An error occurred while downloading {theme_name}: {e}")

    def show_error_popup(self, title, message):
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Critical)
        msg.setWindowTitle(title)
        msg.setText(message)
        msg.exec_()

    def is_theme_installed(self, theme_name):
        return os.path.exists(os.path.join('themes', f'{theme_name}.json'))

    def load_themes(self):
        themes_data = self.fetch_themes()
        themes = themes_data.get("themes", [])
        installed_themes = []
        uninstalled_themes = []
        for theme in themes:
            theme_display_name = f"{theme['name']} by {theme['author']}"
            if self.is_theme_installed(theme['name']):
                theme_display_name += " [I]"
                installed_themes.append(theme_display_name)
            else:
                uninstalled_themes.append(theme_display_name)
        self.theme_list.clear()
        self.theme_list.addItems(uninstalled_themes)
        self.theme_list.addItems(installed_themes)

        # Autoselect the first item in the list if it exists
        if self.theme_list.count() > 0:
            self.theme_list.setCurrentRow(0)
            self.on_theme_click()

    def on_theme_click(self):
        selected_item = self.theme_list.currentItem()
        if selected_item:
            theme_name = selected_item.text().split(" by ")[0]
            theme = self.find_theme_by_name(theme_name)
            if theme:
                self.details_label.setText(
                    f"<b>Name:</b> {theme['name']}<br>"
                    f"<b>Description:</b> {theme['description']}<br>"
                    f"<b>Author:</b> {theme['author']}<br>"
                    f"<b>License:</b> {theme['license']}<br>"
                    f"<b>Link:</b> <a href='{theme['link']}'>{theme['link']}</a><br>"
                )
                self.details_label.setTextFormat(Qt.RichText)
                self.details_label.setOpenExternalLinks(True)
                preview = theme.get('preview')
                if preview:
                    image_data = self.fetch_image(preview)
                    if image_data:
                        pixmap = QPixmap()
                        pixmap.loadFromData(image_data)
                        self.image_label.setPixmap(pixmap)
                    else:
                        self.image_label.clear()

    def fetch_image(self, url):
        try:
            response = requests.get(url)
            response.raise_for_status()
            return response.content
        except requests.exceptions.RequestException as e:
            self.show_error_popup("Error fetching image", f"An error occurred while fetching the image: {e}")
            return None

    def find_theme_by_name(self, theme_name):
        themes_data = self.fetch_themes()
        themes = themes_data.get("themes", [])
        for theme in themes:
            if theme["name"] == theme_name:
                return theme
        return None

    def theme_download(self):
        selected_item = self.theme_list.currentItem()
        if selected_item:
            theme_name = selected_item.text().split(" by ")[0]
            theme = self.find_theme_by_name(theme_name)
            if theme:
                theme_url = theme["link"]
                self.download_theme_json(theme_url, theme_name)
                self.load_themes()

        ## REPOSITORY BLOCK ENDS


    def save_settings(
        self,
        is_rcp_enabled,
        check_updates_on_start,
        theme_background,
        selected_theme,
        is_bleeding,
        java_path,
        ram_allocation,
        manage_java_enabled
    ):
        config_path = "config.json"
        updated_config = {
            "IsRCPenabled": is_rcp_enabled,
            "CheckUpdate": check_updates_on_start,
            "ThemeBackground": theme_background,
            "Theme": selected_theme,
            "IsBleeding": is_bleeding,
            "ManageJava": manage_java_enabled,
            "MaxRAM": ram_allocation,
            "JavaPath": java_path,
        }

        self.config.update(updated_config)

        with open(config_path, "w") as config_file:
            json.dump(self.config, config_file, indent=4)

        QMessageBox.information(
            self, 
            "Settings Saved", 
            "Settings saved successfully!\n\nTo apply the changes, please restart the launcher."
        )
        self.__init__()

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
            # Run the command using modulecli
            command = "instance dir"
            result = modulecli.run_command(command)
            if not result:
                print("Error: Could not retrieve game directory")
                return
            game_directory = result.strip()

            # Open the directory in the system's file explorer
            QDesktopServices.openUrl(QUrl.fromLocalFile(game_directory))
        except Exception as e:
            print(f"Error running zucaro command: {e}")

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
            command = "version list"
            output = modulecli.run_command(command)
            
            if not output:
                self.installed_version_combo.clear()
                return
        except Exception as e:
            self.installed_version_combo.clear()
            return

        versions = [version.replace('[local]', ' ').strip() for version in output.splitlines() if version.strip()]

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
        # Run the 'zucaro instance create default' command at the start
        try:
            command = "instance create default"
            output = modulecli.run_command(command)
            if not output:
                self.installed_version_combo.clear()
                return
        except Exception as e:
            self.installed_version_combo.clear()
            return

        # Run the 'zucaro version list' command and get the output
        try:
            command = "version list"
            output = modulecli.run_command(command)
            if not output:
                self.installed_version_combo.clear()
                return
        except Exception as e:
            self.installed_version_combo.clear()
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
            account_list_output = modulecli.run_command("account list")
            if not account_list_output:
                QMessageBox.warning(self, "No Account Available", "Please create an account first.")
                return
            account_list_output = account_list_output.strip()

            # Check if the selected account has a '*' (indicating it's the selected one)
            if '*' not in account_list_output:
                QMessageBox.warning(self, "No Account Selected", "Please select an account.")
                return
        except Exception as e:
            error_message = f"Error fetching accounts: {str(e)}"
            logging.error(error_message)
            QMessageBox.critical(self, "Error", error_message)
            return

        selected_instance = self.installed_version_combo.currentText()
        logging.info(f"Selected instance from dropdown: {selected_instance}")

        # Verify the selected instance value before starting the game
        if not selected_instance:
            logging.error("No instance selected.")
            QMessageBox.warning(self, "No Instance Selected", "Please select an instance.")
            return

        self.launch_game_with_window(selected_instance)


    def launch_game_with_window(self, selected_instance):
        try:
            self.current_state = selected_instance
            self.start_time = time.time()

            with open('config.json', 'r') as config_file:
                config = json.load(config_file)
                instance_value = config.get("Instance", "default")
                max_ram = config.get("MaxRAM", 2)
                manage_java = config.get("ManageJava", False)
                java_path = config.get("JavaPath", "")

            update_thread = threading.Thread(target=self.update_last_played, args=(selected_instance,), daemon=True)
            update_thread.start()

            command = f"instance launch {instance_value} --version-override {selected_instance} --assigned-ram {max_ram}"
            if manage_java:
                command += " --manage-java"
            if java_path:
                command += f" --java {java_path}"

            print(f"Launching command: {command}")
            
            loaddaemon.launch_instance_with_window(command, self)

        except Exception as e:
            error_message = f"Error playing {selected_instance}: {e}"
            print(error_message)
            logging.error(error_message)
            QMessageBox.critical(self, "Error", error_message)
        finally:
            self.current_state = "menu"
            self.update_total_playtime(self.start_time)

    def update_last_played(self, selected_instance):
        config_path = "config.json"
        self.config["LastPlayed"] = selected_instance
        with open(config_path, "w") as config_file:
            json.dump(self.config, config_file, indent=4)

    def update_total_playtime(self, start_time):
        config_path = "config.json"
        self.config["TotalPlaytime"] += time.time() - self.start_time
        print("TOTAL PLAYTIME:" + str(self.config["TotalPlaytime"]))
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

    def create_account(self, dialog, username, is_microsoft):
        # Remove leading and trailing spaces from the username
        username = username.strip()

        if not username:
            QMessageBox.warning(dialog, "Warning", "Username cannot be blank.")
            return

        if not self.is_valid_username(username):
            QMessageBox.warning(dialog, "Warning", "Invalid username. Usernames must be 3-16 characters long and can only contain letters, numbers, and underscores.")
            return

        try:
            command = f"account create {username}"
            if is_microsoft:
                command += " --ms"

            modulecli.run_command(command)
            QMessageBox.information(dialog, "Success", f"Account '{username}' created successfully!")
            self.populate_accounts_for_all_dialogs()
            dialog.accept()
        except Exception as e:
            error_message = f"Error creating account: {str(e)}"
            logging.error(error_message)
            QMessageBox.critical(dialog, "Error", error_message)

    def is_valid_username(self, username):
        # Validate the username according to Minecraft's rules
        if 3 <= len(username) <= 16 and re.match(r'^[a-zA-Z0-9_]+$', username):
            return True
        return False

    def authenticate_account(self, dialog, account_name):
        # Clean up the account name
        account_name = account_name.strip().lstrip(" * ")
        if not account_name:
            QMessageBox.warning(dialog, "Warning", "Please select an account to authenticate.")
            return

        try:
            # Create authenticator instance if it doesn't exist
            if self.authenticator is None:
                self.authenticator = MinecraftAuthenticator(self)
                self.authenticator.auth_finished.connect(self._on_auth_finished)

            # Start authentication process
            self.authenticator.authenticate(account_name)
            
        except Exception as e:
            error_message = f"Error authenticating account '{account_name}': {str(e)}"
            logging.error(error_message)
            QMessageBox.critical(dialog, "Error", error_message)

    def _on_auth_finished(self, success):
        if success:
            QMessageBox.information(self, "Success", "Account authenticated successfully!")
        else:
            QMessageBox.critical(self, "Error", "Failed to authenticate account")

        # Cleanup
        if self.authenticator:
            self.authenticator.cleanup()
            self.authenticator = None

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
                command = f"account remove {username}"
                modulecli.run_command(command)
                QMessageBox.information(dialog, "Success", f"Account '{username}' removed successfully!")
                self.populate_accounts_for_all_dialogs()
            except Exception as e:
                error_message = f"Error removing account: {str(e)}"
                logging.error(error_message)
                QMessageBox.critical(dialog, "Error", error_message)

    def populate_accounts(self, account_combo):
        # Populate the account dropdown
        try:
            command = "account list"
            output = modulecli.run_command(command)
            if not output:
                account_combo.clear()
                return
            
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

        except Exception as e:
            logging.error(f"Error: {str(e)}")

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
            command = f"account setdefault {account_name}"
            modulecli.run_command(command)
            QMessageBox.information(self, "Success", f"Account '{account_name}' set as default!")
            self.populate_accounts_for_all_dialogs()
        except Exception as e:
            error_message = f"Error setting default account '{account_name}': {str(e)}"
            logging.error(error_message)
            QMessageBox.critical(self, "Error", error_message)


    def get_playtime(self, config_data):

        #Gets the playtime from the json and
        total_playtime = config_data.get("TotalPlaytime")/60
        
        #if total playtime is over 60 minutes, uses hours instead
        if(total_playtime > 60):
            total_playtime = total_playtime / 60
            playtime_unit = "hours"
        else:
            playtime_unit = "minutes"
        total_playtime = round(total_playtime)
        #returs the playtime and the unit used to measure in a string
        return(f"{total_playtime} {playtime_unit}")

    def show_about_dialog(self):
        # Load the version number from version.json
        try:
            with open('version.json', 'r') as version_file:
                version_data = json.load(version_file)
                version_number = version_data.get('version', 'unknown version')
                version_bleeding = version_data.get('versionBleeding', None)
        except (FileNotFoundError, json.JSONDecodeError):
            version_number = 'unknown version'
            version_bleeding = None

        # Check the configuration for IsBleeding
        try:
            with open('config.json', 'r') as config_file:
                config_data = json.load(config_file)
                is_bleeding = config_data.get('IsBleeding', False)
        except (FileNotFoundError, json.JSONDecodeError):
            is_bleeding = False

        # Use versionBleeding if IsBleeding is true
        if is_bleeding and version_bleeding:
            version_number = version_bleeding



        about_message = (
            f"PicoDulce Launcher (v{version_number})\n\n"
            "A simple Minecraft launcher built using Qt, based on the zucaro backend.\n\n"
            "Credits:\n"
            "Nixietab: Code and UI design\n"
            "Wabaano: Graphic design\n"
            "Olinad: Christmas!!!!\n\n"
            f"Playtime:  {self.get_playtime(config_data)}"
        )
        QMessageBox.about(self, "About", about_message)

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
                        update_dialog = QMessageBox.question(self, "Update Available", update_message, QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
                        if update_dialog == QMessageBox.Yes:
                            # Download and apply the update
                            self.download_update(remote_version_info)
                    else:
                        print(f"You already have the latest version!")
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
        import time
        import logging

        client_id = '1236906342086606848'
        presence = Presence(client_id)

        try:
            presence.connect()

            # Initialize start time for the session
            start_time = time.time()

            while True:
                # Determine the state and details based on the current_state
                if self.current_state == "menu":
                    state = "In the menu"
                    details = "Picodulce FOSS Launcher"
                    large_image = "launcher_icon"
                else:
                    state = f"Playing {self.current_state}"

                    # Determine the appropriate large image based on the current_state
                    if "forge" in self.current_state.lower():
                        large_image = "forge"
                    elif "fabric" in self.current_state.lower():
                        large_image = "fabric"
                    elif "optifine" in self.current_state.lower():  # Check for OptiFine
                        large_image = "optifine"
                    else:
                        large_image = "vanilla"  # Default to vanilla if no specific patterns match

                # Update presence
                presence.update(
                    state=state,
                    details=details,
                    large_image=large_image,
                    large_text="PicoDulce Launcher",
                    start=start_time,
                    buttons=[{"label": "Download", "url": "https://github.com/nixietab/picodulce"}]
                )
                
                # Wait for 15 seconds before checking again
                time.sleep(15)
        except Exception as e:
            logging.error("Failed to start Discord RPC: %s", str(e))


    def open_mod_loader_and_version_menu(self):
        dialog = ModLoaderAndVersionMenu(parent=self)
        dialog.finished.connect(self.populate_installed_versions)
        dialog.exec_()



class ModLoaderAndVersionMenu(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Mod Loader and Version Menu")
        # Set window position relative to parent
        if parent:
            parent_pos = parent.pos()
            x = parent_pos.x() + (parent.width() - 400) // 2
            y = parent_pos.y() + (parent.height() - 300) // 2
            self.setGeometry(x, y, 400, 300)
        else:
            self.setGeometry(100, 100, 400, 300)

        main_layout = QVBoxLayout(self)

        tab_widget = QTabWidget()
        main_layout.addWidget(tab_widget)

        # Create tabs
        install_mod_tab = QWidget()
        download_version_tab = QWidget()
        instances_tab = QWidget()

        tab_widget.addTab(download_version_tab, "Download Version")
        tab_widget.addTab(install_mod_tab, "Install Mod Loader")
        tab_widget.addTab(instances_tab, "Instances")

        # Add content to "Install Mod Loader" tab
        self.setup_install_mod_loader_tab(install_mod_tab)

        # Add content to "Download Version" tab
        self.setup_download_version_tab(download_version_tab)

        # Add content to "Instances" tab
        self.setup_instances_tab(instances_tab)


    def setup_instances_tab(self, instances_tab):
        layout = QVBoxLayout(instances_tab)

        title_label = QLabel('Manage Minecraft Instances')
        title_label.setFont(QFont("Arial", 14, QFont.Bold))
        layout.addWidget(title_label)

        info_label = QLabel('Click an instance to select it. Right-click for more options.')
        palette = info_label.palette()
        info_label.setStyleSheet(f"color: {palette.color(QPalette.PlaceholderText).name()}; font-size: 10pt;")
        layout.addWidget(info_label)

        self.current_instance_label = QLabel('Current Instance: Loading...')
        self.current_instance_label.setFont(QFont("Arial", 11, QFont.Bold))
        layout.addWidget(self.current_instance_label)

        layout.addSpacing(10)

        instances_label = QLabel('Available Instances:')
        instances_label.setFont(QFont("Arial", 10))
        layout.addWidget(instances_label)

        self.instances_list_widget = QListWidget()
        self.instances_list_widget.setContextMenuPolicy(Qt.CustomContextMenu)
        self.instances_list_widget.customContextMenuRequested.connect(self.show_instance_context_menu)
        self.instances_list_widget.setAlternatingRowColors(True)
        layout.addWidget(self.instances_list_widget)

        layout.addSpacing(10)

        create_label = QLabel('Create New Instance:')
        create_label.setFont(QFont("Arial", 10))
        layout.addWidget(create_label)

        create_layout = QHBoxLayout()
        self.create_instance_input = QLineEdit()
        self.create_instance_input.setPlaceholderText("Enter instance name")
        create_layout.addWidget(self.create_instance_input)

        create_instance_button = QPushButton("Create")
        create_instance_button.clicked.connect(self.create_instance)
        create_layout.addWidget(create_instance_button)
        
        layout.addLayout(create_layout)

        self.load_instances()
        self.instances_list_widget.itemClicked.connect(self.on_instance_selected)
        self.update_instance_label()

    def create_instance(self):
        instance_name = self.create_instance_input.text().strip()

        if instance_name:
            try:
                # Run the "zucaro instance create" command
                command = f"instance create {instance_name}"
                modulecli.run_command(command)

                # Notify the user that the instance was created
                QMessageBox.information(self, "Instance Created", f"Instance '{instance_name}' has been created successfully.")

                # Reload the instances list
                self.load_instances()

                # Optionally select the newly created instance
                self.on_instance_selected(self.instances_list_widget.item(self.instances_list_widget.count() - 1))

            except Exception as e:
                logging.error("Error creating instance: %s", str(e))
                QMessageBox.critical(self, "Error", f"Failed to create instance: {str(e)}")
        else:
            QMessageBox.warning(self, "Invalid Input", "Please enter a valid instance name.")

    def rename_instance(self, old_instance_name, new_instance_name):
        if old_instance_name == "default":
            QMessageBox.warning(self, "Cannot Rename Instance", "You cannot rename the 'default' instance.")
            return

        try:
            # Run the "zucaro instance rename" command
            command = f"instance rename {old_instance_name} {new_instance_name}"
            modulecli.run_command(command)

            QMessageBox.information(self, "Instance Renamed", f"Instance '{old_instance_name}' has been renamed to '{new_instance_name}' successfully.")

            # Reload the instances list
            self.load_instances()

            # Optionally select the newly renamed instance
            matching_items = self.instances_list_widget.findItems(new_instance_name, Qt.MatchExactly)
            if matching_items:
                self.instances_list_widget.setCurrentItem(matching_items[0])

        except Exception as e:
            logging.error("Error renaming instance: %s", str(e))
            QMessageBox.critical(self, "Error", f"Failed to rename instance: {str(e)}")

    def delete_instance(self, instance_name):
        if instance_name == "default":
            QMessageBox.warning(self, "Cannot Delete Instance", "You cannot delete the 'default' instance.")
            return

        confirm_delete = QMessageBox.question(
            self, "Confirm Deletion", f"Are you sure you want to delete the instance '{instance_name}'?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )

        if confirm_delete == QMessageBox.Yes:
            try:
                # Run the "zucaro instance delete" command
                command = f"instance delete {instance_name}"
                modulecli.run_command(command)

                # Notify the user that the instance was deleted
                QMessageBox.information(self, "Instance Deleted", f"Instance '{instance_name}' has been deleted successfully.")

                # Reload the instances list
                self.load_instances()

            except Exception as e:
                logging.error("Error deleting instance: %s", str(e))
                QMessageBox.critical(self, "Error", f"Failed to delete instance: {str(e)}")

    def load_instances(self):
        try:
            command = "instance list"
            output = modulecli.run_command(command)
            if not output:
                self.instances_list_widget.clear()
                return
            
            instances = output.splitlines()
            self.instances_list_widget.clear()
            
            with open('config.json', 'r') as config_file:
                config_data = json.load(config_file)
                current_instance = config_data.get('Instance', 'default')
            
            for instance in instances:
                instance_name = instance.strip()
                item = QListWidgetItem()
                font = QFont()
                font.setPointSize(11)
                
                if instance_name == current_instance:
                    item.setText(f"★ {instance_name}")
                else:
                    item.setText(instance_name)
                
                item.setFont(font)
                self.instances_list_widget.addItem(item)

        except Exception as e:
            logging.error("Error fetching instances: %s", str(e))

    def show_instance_context_menu(self, position):
        item = self.instances_list_widget.itemAt(position)
        if not item:
            return
        
        instance_name = item.text().replace("★ ", "").strip()
        
        menu = QMenu()
        
        select_action = menu.addAction("Select Instance")
        menu.addSeparator()
        rename_action = menu.addAction("Rename")
        delete_action = menu.addAction("Delete")
        
        if instance_name == "default":
            rename_action.setEnabled(False)
            delete_action.setEnabled(False)
        
        action = menu.exec_(self.instances_list_widget.mapToGlobal(position))
        
        if action == select_action:
            self.on_instance_selected(item)
        elif action == rename_action:
            self.prompt_rename_instance(instance_name)
        elif action == delete_action:
            self.delete_instance(instance_name)

    def prompt_rename_instance(self, old_instance_name):
        new_instance_name, ok = QInputDialog.getText(
            self, "Rename Instance",
            f"Enter new name for instance '{old_instance_name}':"
        )

        if ok and new_instance_name:
            self.rename_instance(old_instance_name, new_instance_name)

    def on_instance_selected(self, item):
        instance_name = item.text().replace("★ ", "").strip()

        config_file = 'config.json'

        if os.path.exists(config_file):
            try:
                with open(config_file, 'r') as file:
                    config_data = json.load(file)

                config_data['Instance'] = instance_name

                with open(config_file, 'w') as file:
                    json.dump(config_data, file, indent=4)

                logging.info(f"Config updated: Instance set to {instance_name}")

                self.update_instance_label()
                self.load_instances()

            except (json.JSONDecodeError, FileNotFoundError) as e:
                logging.error(f"Error reading config.json: {e}")
        else:
            logging.warning(f"{config_file} not found. Unable to update instance.")

    def update_instance_label(self):
        config_file = 'config.json'

        if os.path.exists(config_file):
            try:
                with open(config_file, 'r') as file:
                    config_data = json.load(file)

                current_instance = config_data.get('Instance', 'Not set')
                self.current_instance_label.setText(f'Current Instance: {current_instance}')

            except (json.JSONDecodeError, FileNotFoundError) as e:
                logging.error(f"Error reading config.json: {e}")
        else:
            self.current_instance_label.setText('Current Instance: Not set')


    def setup_install_mod_loader_tab(self, install_mod_tab):
        layout = QVBoxLayout(install_mod_tab)

        # Create title label
        title_label = QLabel('Mod Loader Installer')
        title_label.setFont(QFont("Arial", 14))
        layout.addWidget(title_label)

        # Create radio buttons for mod loaders
        self.forge_checkbox = QRadioButton('Forge')
        self.fabric_checkbox = QRadioButton('Fabric')
        self.quilt_checkbox = QRadioButton('Quilt')
        layout.addWidget(self.forge_checkbox)
        layout.addWidget(self.fabric_checkbox)
        layout.addWidget(self.quilt_checkbox)

        # Create dropdown menu for versions
        self.version_combo_mod = QComboBox()
        layout.addWidget(self.version_combo_mod)

        def update_versions():
            self.version_combo_mod.clear()
            if self.forge_checkbox.isChecked():
                self.populate_available_releases(self.version_combo_mod, True, False, False)
            elif self.fabric_checkbox.isChecked():
                self.populate_available_releases(self.version_combo_mod, False, True, False)
            elif self.quilt_checkbox.isChecked():
                self.populate_available_releases(self.version_combo_mod, False, False, True)

        self.forge_checkbox.clicked.connect(update_versions)
        self.fabric_checkbox.clicked.connect(update_versions)
        self.quilt_checkbox.clicked.connect(update_versions)

        # Create install button
        install_button = QPushButton('Install')
        install_button.clicked.connect(lambda: self.install_mod_loader(
            self.version_combo_mod.currentText(), 
            self.forge_checkbox.isChecked(), 
            self.fabric_checkbox.isChecked(),
            self.quilt_checkbox.isChecked()
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
        self.release_checkbox.setChecked(True)
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
                    command = 'version list ' + ' '.join(options)
                    output = modulecli.run_command(command)
                    if not output or "Error" in output:
                        if not output:
                            logging.error("Empty response from modulecli")
                        else:
                            logging.error(output)
                        return

                    versions = output.splitlines()
                    versions = [version.replace('[local]', ' ').strip() for version in versions]
                    self.version_combo.addItems(versions)
                except Exception as e:
                    logging.error("Unexpected error: %s", e)
                    return
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
        
        # Initial update
        update_versions()
        
    def update_download_button_state(self):
        self.download_button.setEnabled(self.version_combo.currentIndex() != -1)

    def download_version(self, version):
        success = loaddaemon.prepare_version_with_window(version, self)
        if success:
            QMessageBox.information(self, "Success", f"Version {version} prepared successfully!")
        else:
            QMessageBox.critical(self, "Error", f"Failed to prepare version {version}.")

    def populate_available_releases(self, version_combo, install_forge, install_fabric, install_quilt):
        try:
            command = "version list --release"
            output = modulecli.run_command(command)
            if not output:
                logging.error("Empty response from modulecli")
                return
        except Exception as e:
            logging.error("Error: %s", str(e))
            return

        if install_fabric or install_quilt:
            releases = [version for version in output.splitlines() if version.startswith("1.") and int(version.split('.')[1]) >= 14]
        elif install_forge:
            releases = [version for version in output.splitlines() if version.startswith("1.") and float(version.split('.')[1]) >= 5]
        else:
            releases = output.splitlines()

        version_combo.clear()
        version_combo.addItems(releases)

    def install_mod_loader(self, version, install_forge, install_fabric, install_quilt):
        if not install_forge and not install_fabric and not install_quilt:
            QMessageBox.warning(self, "Select Mod Loader", "Please select at least one mod loader.")
            return

        mod_loader = None
        if install_forge:
            mod_loader = 'forge'
        elif install_fabric:
            mod_loader = 'fabric'
        elif install_quilt:
            mod_loader = 'quilt'

        if not mod_loader:
            QMessageBox.warning(self, "Select Mod Loader", "Please select at least one mod loader.")
            return

        try:
            if mod_loader == 'forge':
                command = f"mod loader forge install --game {version}"
            elif mod_loader == 'fabric':
                command = f"mod loader fabric install {version}"
            elif mod_loader == 'quilt':
                command = f"mod loader quilt install {version}"
            modulecli.run_command(command)
            QMessageBox.information(self, "Success", f"{mod_loader.capitalize()} installed successfully for version {version}!")
        except Exception as e:
            error_message = f"Error installing {mod_loader} for version {version}: {str(e)}"
            QMessageBox.critical(self, "Error", error_message)
            logging.error(error_message)


if __name__ == '__main__':
    app = QApplication(sys.argv)
    current_date = datetime.now()
    # ---------------------------------------------------------------------
    # I wish for everyone that plays this to enjoy the game as much as I,
    # may joy give a little more peace in this troubled world
    # ---------------------------------------------------------------------

    # Set the application icon based on the date
    if (current_date.month == 12 and current_date.day >= 8) or (current_date.month == 1 and current_date.day <= 1):
        app.setWindowIcon(QIcon('holiday.ico'))  # Set holiday icon
    else:
        app.setWindowIcon(QIcon('launcher_icon.ico'))  # Set regular icon
    window = zucaroVersionSelector()
    window.show()
    sys.exit(app.exec_())
