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
from healtcheck import HealthCheck

from PyQt5.QtWidgets import QApplication, QComboBox, QWidget, QInputDialog, QVBoxLayout, QListWidget, QPushButton, QMessageBox, QDialog, QHBoxLayout, QLabel, QLineEdit, QCheckBox, QTabWidget, QFrame, QSpacerItem, QSizePolicy, QMainWindow, QGridLayout, QTextEdit, QListWidget, QListWidgetItem, QMenu
from PyQt5.QtGui import QFont, QIcon, QColor, QPalette, QMovie, QPixmap, QDesktopServices, QBrush
from PyQt5.QtCore import Qt, QObject, pyqtSignal, QThread, QUrl, QMetaObject, Q_ARG, QByteArray, QSize, QTranslator, QLocale
from datetime import datetime

logging.basicConfig(level=logging.ERROR, format='%(asctime)s - %(levelname)s - %(message)s')

class PicomcVersionSelector(QWidget):

    def __init__(self):
        super().__init__()  # Initialize the parent class properly
        self.current_state = "menu"
        self.open_dialogs = []
        
        
        # Set up and use the health_check module
        health_checker = HealthCheck()
        health_checker.themes_integrity()
        health_checker.check_config_file()
        self.config = health_checker.config
        health_checker.locales_integrity()

        # Load translations before initializing UI
        self.translators = []
        self.load_locale("./locales")

        themes_folder = "themes"
        theme_file = self.config.get("Theme", "Dark.json")

        theme_file_path = os.path.join(themes_folder, theme_file)

        try:
            self.load_theme_from_file(theme_file_path, app)
            print(f"Theme '{theme_file}' loaded successfully.")
        except Exception as e:
            print(f"Error: Could not load theme '{theme_file}'. Falling back to default theme. {e}")

        self.init_ui()

        if self.config.get("CheckUpdate", False):
            self.check_for_update_start()

        if self.config.get("IsRCPenabled", False):
            discord_rcp_thread = Thread(target=self.start_discord_rcp)
            discord_rcp_thread.daemon = True
            discord_rcp_thread.start()

        if self.config.get("IsFirstLaunch", False):
            self.FirstLaunch()

        self.authenticator = MinecraftAuthenticator(self)
        self.authenticator.auth_finished.connect(self._on_auth_finished)

    def load_locale(self, locale_dir_path):
        self.config_path = "config.json"
        if not os.path.exists(locale_dir_path):
            print(f"Warning: Locale directory {locale_dir_path} does not exist")
            return

        # Try to load and read config.json
        try:
            with open(self.config_path, 'r', encoding='utf-8') as config_file:
                config = json.load(config_file)
                locale_code = config.get("Locale", "")
        except FileNotFoundError:
            print(f"Warning: Config file {self.config_path} not found")
            return
        except json.JSONDecodeError:
            print(f"Error: Invalid JSON in {self.config_path}")
            return
        
        if not locale_code:
            print("Warning: No locale specified in config.json")
            return

        # Look for matching locale file
        locale_pattern = f"*_{locale_code}.qm"  # Pattern like stuff
        found_matching_locale = False

        for filename in os.listdir(locale_dir_path):
            if filename.endswith(".qm") and f"_{locale_code}" in filename:
                locale_file_path = os.path.join(locale_dir_path, filename)
                translator = QTranslator()
                if translator.load(locale_file_path):
                    QApplication.instance().installTranslator(translator)
                    self.translators.append(translator)
                    print(f"Loaded locale: {locale_file_path}")
                    found_matching_locale = True
                else:
                    print(f"Failed to load locale: {locale_file_path}")

        if not found_matching_locale:
            print(f"Warning: No matching locale file found for language code: {locale_code}")

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
            print("Running picomc instance create default command...")
            # Run the command using subprocess
            result = subprocess.run(["picomc", "instance", "create", "default"], check=True, capture_output=True, text=True)
            
            # Print the output of the command
            print("Command output:", result.stdout)
            
            # Change the value of IsFirstLaunch to False
            self.config["IsFirstLaunch"] = False
            print("IsFirstLaunch set to False")

            # Save the updated config to the config.json file
            with open(self.config_path, 'w') as f:
                json.dump(self.config, f, indent=4)
            print("Configuration saved to", self.config_path)

        except subprocess.CalledProcessError as e:
            print("An error occurred while creating the instance.")
            print("Error output:", e.stderr)

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
        installed_versions_label = QLabel(self.tr('Installed Versions:'))
        installed_versions_label.setFont(QFont("Arial", 14))
        self.installed_version_combo = QComboBox()
        self.installed_version_combo.setMinimumWidth(200)
        self.populate_installed_versions()

        # Create buttons layout
        buttons_layout = QVBoxLayout()

        # Create play button for installed versions
        self.play_button = QPushButton(self.tr('Play'))
        self.play_button.clicked.connect(self.play_instance)
        highlight_color = self.palette().color(QPalette.Highlight)
        self.play_button.setStyleSheet(f"background-color: {highlight_color.name()}; color: white;")
        buttons_layout.addWidget(self.play_button)

        # Version Manager Button
        self.open_menu_button = QPushButton(self.tr('Version Manager'))
        self.open_menu_button.clicked.connect(self.open_mod_loader_and_version_menu)
        buttons_layout.addWidget(self.open_menu_button)

        # Create button to manage accounts
        self.manage_accounts_button = QPushButton(self.tr('Manage Accounts'))
        self.manage_accounts_button.clicked.connect(self.manage_accounts)
        buttons_layout.addWidget(self.manage_accounts_button)

        # Create a button for the marroc mod loader
        self.open_marroc_button = QPushButton(self.tr('Marroc Mod Manager'))
        self.open_marroc_button.clicked.connect(self.open_marroc_script)
        buttons_layout.addWidget(self.open_marroc_button)

        # Create grid layout for Settings and About buttons
        grid_layout = QGridLayout()
        self.settings_button = QPushButton(self.tr('Settings'))
        self.settings_button.clicked.connect(self.open_settings_dialog)
        self.about_button = QPushButton(self.tr('About'))
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
        dialog.setWindowTitle(self.tr('Settings'))

        # Make the window resizable
        dialog.setMinimumSize(400, 300)

        # Create a Tab Widget
        tab_widget = QTabWidget()

        # Create the Settings Tab
        settings_tab = QWidget()
        settings_layout = QVBoxLayout()

        title_label = QLabel(self.tr('Settings'))
        title_label.setFont(QFont("Arial", 14))

        # Create checkboxes for settings tab
        discord_rcp_checkbox = QCheckBox(self.tr('Discord Rich Presence'))
        discord_rcp_checkbox.setChecked(self.config.get("IsRCPenabled", False))

        check_updates_checkbox = QCheckBox(self.tr('Check Updates on Start'))
        check_updates_checkbox.setChecked(self.config.get("CheckUpdate", False))

        bleeding_edge_checkbox = QCheckBox(self.tr('Bleeding Edge'))
        bleeding_edge_checkbox.setChecked(self.config.get("IsBleeding", False))
        bleeding_edge_checkbox.stateChanged.connect(lambda: self.show_bleeding_edge_popup(bleeding_edge_checkbox))

        settings_layout.addWidget(title_label)
        settings_layout.addWidget(discord_rcp_checkbox)
        settings_layout.addWidget(check_updates_checkbox)
        settings_layout.addWidget(bleeding_edge_checkbox)

        # Add language dropdown
        language_label = QLabel(self.tr('Language'))
        language_dropdown = QComboBox()
        languages = {
            "English": "en",
            "Español": "es",
            "Italiano": "it"
            # Here will be more
        }
        
        # Populate dropdown with language options
        for lang_name, lang_code in languages.items():
            language_dropdown.addItem(lang_name, lang_code)
        
        # Set the current language in the dropdown
        current_language_code = self.config.get('Locale', 'en')
        current_language_index = language_dropdown.findData(current_language_code)
        if current_language_index != -1:
            language_dropdown.setCurrentIndex(current_language_index)

        settings_layout.addWidget(language_label)
        settings_layout.addWidget(language_dropdown)

        # Add buttons in the settings tab
        update_button = QPushButton(self.tr('Check for updates'))
        update_button.clicked.connect(self.check_for_update)

        open_game_directory_button = QPushButton(self.tr('Open game directory'))
        open_game_directory_button.clicked.connect(self.open_game_directory)

        stats_button = QPushButton(self.tr('Stats for Nerds'))
        stats_button.clicked.connect(self.show_system_info)

        settings_layout.addWidget(update_button)
        settings_layout.addWidget(open_game_directory_button)
        settings_layout.addWidget(stats_button)

        settings_tab.setLayout(settings_layout)

        # Create the Customization Tab
        customization_tab = QWidget()
        customization_layout = QVBoxLayout()

        # Create theme background checkbox for customization tab
        theme_background_checkbox = QCheckBox(self.tr('Theme Background'))
        theme_background_checkbox.setChecked(self.config.get("ThemeBackground", False))

        # Label to show currently selected theme
        theme_filename = self.config.get('Theme', 'Dark.json')
        current_theme_label = QLabel(self.tr(f"Current Theme: {theme_filename}"))

        # QListWidget to display available themes
        json_files_label = QLabel(self.tr('Installed Themes:'))
        self.json_files_list_widget = QListWidget()

        # Track selected theme
        self.selected_theme = theme_filename  # Default to current theme

        # Build the list of themes
        themes_list = self.build_themes_list()
        
        # Populate themes initially
        self.populate_themes(self.json_files_list_widget, themes_list)

        # Update current theme label when a theme is selected
        self.json_files_list_widget.itemClicked.connect(
            lambda: self.on_theme_selected(self.json_files_list_widget, current_theme_label)
        )

        # Add widgets to the layout
        customization_layout.addWidget(theme_background_checkbox)
        customization_layout.addWidget(current_theme_label)
        customization_layout.addWidget(json_files_label)
        customization_layout.addWidget(self.json_files_list_widget)

        # Button to download themes
        download_themes_button = QPushButton(self.tr("Download More Themes"))
        download_themes_button.clicked.connect(self.download_themes_window)

        customization_layout.addWidget(download_themes_button)

        customization_tab.setLayout(customization_layout)

        # Add the tabs to the TabWidget
        tab_widget.addTab(settings_tab, self.tr("Settings"))
        tab_widget.addTab(customization_tab, self.tr("Customization"))

        # Save button
        save_button = QPushButton(self.tr('Save'))
        save_button.clicked.connect(
            lambda: self.save_settings(
                discord_rcp_checkbox.isChecked(),
                check_updates_checkbox.isChecked(),
                theme_background_checkbox.isChecked(),
                self.selected_theme,  # Pass the selected theme here
                bleeding_edge_checkbox.isChecked(),  # Pass the bleeding edge setting here
                language_dropdown.currentData()  # Pass the selected language code here
            )
        )

        # Main layout
        main_layout = QVBoxLayout()
        main_layout.addWidget(tab_widget)
        main_layout.addWidget(save_button)

        dialog.setLayout(main_layout)
        dialog.exec_()

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
            current_theme_label.setText(self.tr(f"Current Theme: {self.selected_theme}"))
            
     ## REPOSITORY BLOCK BEGGINS

    def download_themes_window(self):
        dialog = QDialog(self)
        dialog.setWindowTitle(self.tr("Themes Repository"))
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

        download_button = QPushButton(self.tr("Download Theme"), dialog)
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
                raise ValueError(self.tr("ThemeRepository is not defined in config.json"))
            response = requests.get(url)
            response.raise_for_status()
            return response.json()
        except (FileNotFoundError, json.JSONDecodeError) as config_error:
            self.show_error_popup(self.tr("Error reading configuration"), self.tr(f"An error occurred while reading config.json: {config_error}"))
            return {}
        except requests.exceptions.RequestException as fetch_error:
            self.show_error_popup(self.tr("Error fetching themes"), self.tr(f"An error occurred while fetching themes: {fetch_error}"))
            return {}
        except ValueError as value_error:
            self.show_error_popup(self.tr("Configuration Error"), self.tr(str(value_error)))
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
            print(self.tr(f"Downloaded {theme_name} theme to {theme_filename}"))
        except requests.exceptions.RequestException as e:
            self.show_error_popup(self.tr("Error downloading theme"), self.tr(f"An error occurred while downloading {theme_name}: {e}"))

    def show_error_popup(self, title, message):
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Critical)
        msg.setWindowTitle(self.tr(title))
        msg.setText(self.tr(message))
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
                theme_display_name += self.tr(" [I]")
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
                    self.tr(f"<b>Name:</b> {theme['name']}<br>"
                            f"<b>Description:</b> {theme['description']}<br>"
                            f"<b>Author:</b> {theme['author']}<br>"
                            f"<b>License:</b> {theme['license']}<br>"
                            f"<b>Link:</b> <a href='{theme['link']}'>{theme['link']}</a><br>")
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
            self.show_error_popup(self.tr("Error fetching image"), self.tr(f"An error occurred while fetching the image: {e}"))
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


    def save_settings(self, is_rcp_enabled, check_updates_on_start, theme_background, selected_theme, is_bleeding, selected_language):
        config_path = "config.json"
        updated_config = {
            "IsRCPenabled": is_rcp_enabled,
            "CheckUpdate": check_updates_on_start,
            "ThemeBackground": theme_background,
            "Theme": selected_theme,
            "IsBleeding": is_bleeding,
            "Locale": selected_language
        }

        # Update config values
        self.config.update(updated_config)

        # Save updated config to file
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
            # Run the command and capture the output
            result = subprocess.run(['picomc', 'instance', 'dir'], capture_output=True, text=True, check=True)
            game_directory = result.stdout.strip()

            # Open the directory in the system's file explorer
            QDesktopServices.openUrl(QUrl.fromLocalFile(game_directory))
        except subprocess.CalledProcessError as e:
            print(f"Error running picomc command: {e}")


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
        # Run the 'picomc instance create default' command at the start
        try:
            process = subprocess.Popen(['picomc', 'instance', 'create', 'default'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            output, error = process.communicate()
            if process.returncode != 0:
                raise subprocess.CalledProcessError(process.returncode, process.args, error)
        except FileNotFoundError:
            logging.error("'picomc' command not found. Please make sure it's installed and in your PATH.")
            return
        except subprocess.CalledProcessError as e:
            logging.error("Error creating default instance: %s", e.stderr)
            return

        # Run the 'picomc version list' command and get the output
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
            # Set current_state to the selected instance
            self.current_state = selected_instance

            # Read the config.json to get the "Instance" value
            with open('config.json', 'r') as config_file:
                config = json.load(config_file)
                instance_value = config.get("Instance", "default")  # Default to "default" if not found

            # Update lastplayed field in config.json on a separate thread
            update_thread = threading.Thread(target=self.update_last_played, args=(selected_instance,))
            update_thread.start()

            # Run the game subprocess with the instance_value from config.json
            subprocess.run(['picomc', 'instance', 'launch', '--version-override', selected_instance, instance_value], check=True)

        except subprocess.CalledProcessError as e:
            error_message = f"Error playing {selected_instance}: {e}"
            logging.error(error_message)
            # Use QMetaObject.invokeMethod to call showError safely
            QMetaObject.invokeMethod(
                self, "showError", Qt.QueuedConnection,
                Q_ARG(str, "Error"), Q_ARG(str, error_message)
            )
        finally:
            # Reset current_state to "menu" after the game closes
            self.current_state = "menu"
            
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
        dialog.setWindowTitle(self.tr('Manage Accounts'))
        dialog.setFixedSize(400, 250)

        # Title
        title_label = QLabel(self.tr('Manage Accounts'))
        title_label.setFont(QFont("Arial", 14))
        title_label.setAlignment(Qt.AlignCenter)  # Center the text
        # Dropdown for selecting accounts
        account_combo = QComboBox()
        self.populate_accounts(account_combo)

        # Buttons
        create_account_button = QPushButton(self.tr('Create Account'))
        create_account_button.clicked.connect(self.open_create_account_dialog)

        authenticate_button = QPushButton(self.tr('Authenticate Account'))
        authenticate_button.clicked.connect(lambda: self.authenticate_account(dialog, account_combo.currentText()))

        remove_account_button = QPushButton(self.tr('Remove Account'))
        remove_account_button.clicked.connect(lambda: self.remove_account(dialog, account_combo.currentText()))

        # New button to set the account idk
        set_default_button = QPushButton(self.tr('Select'))
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
        dialog.setWindowTitle(self.tr('Create Account'))
        dialog.setFixedSize(300, 150)

        username_input = QLineEdit()
        username_input.setPlaceholderText(self.tr('Enter Username'))

        microsoft_checkbox = QCheckBox(self.tr('Microsoft Account'))

        create_button = QPushButton(self.tr('Create'))
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
            QMessageBox.warning(dialog, self.tr("Warning"), self.tr("Username cannot be blank."))
            return

        if not self.is_valid_username(username):
            QMessageBox.warning(dialog, self.tr("Warning"), 
                self.tr("Invalid username. Usernames must be 3-16 characters long and can only contain letters, numbers, and underscores."))
            return

        try:
            command = ['picomc', 'account', 'create', username]
            if is_microsoft:
                command.append('--ms')

            subprocess.run(command, check=True)
            QMessageBox.information(dialog, self.tr("Success"), 
                self.tr("Account '{username}' created successfully!").format(username=username))
            self.populate_accounts_for_all_dialogs()
            dialog.accept()
        except subprocess.CalledProcessError as e:
            error_message = self.tr("Error creating account: {error}").format(error=e.stderr.decode())
            logging.error(error_message)
            QMessageBox.critical(dialog, self.tr("Error"), error_message)

    def is_valid_username(self, username):
        # Validate the username according to Minecraft's rules
        if 3 <= len(username) <= 16 and re.match(r'^[a-zA-Z0-9_]+$', username):
            return True
        return False

    def authenticate_account(self, dialog, account_name):
        # Clean up the account name
        account_name = account_name.strip().lstrip(" * ")
        if not account_name:
            QMessageBox.warning(dialog, self.tr("Warning"), 
                self.tr("Please select an account to authenticate."))
            return

        try:
            # Create authenticator instance if it doesn't exist
            if self.authenticator is None:
                self.authenticator = MinecraftAuthenticator(self)
                self.authenticator.auth_finished.connect(self._on_auth_finished)

            # Start authentication process
            self.authenticator.authenticate(account_name)
            
        except Exception as e:
            error_message = self.tr("Error authenticating account '{account}': {error}").format(
                account=account_name, error=str(e))
            logging.error(error_message)
            QMessageBox.critical(dialog, self.tr("Error"), error_message)

    def _on_auth_finished(self, success):
        if success:
            QMessageBox.information(self, self.tr("Success"), 
                self.tr("Account authenticated successfully!"))
        else:
            QMessageBox.critical(self, self.tr("Error"), 
                self.tr("Failed to authenticate account"))

        # Cleanup
        if self.authenticator:
            self.authenticator.cleanup()
            self.authenticator = None

    def remove_account(self, dialog, username):
        # Remove a selected account
        username = username.strip().lstrip(" * ")
        if not username:
            QMessageBox.warning(dialog, self.tr("Warning"), 
                self.tr("Please select an account to remove."))
            return

        confirm_message = self.tr("Are you sure you want to remove the account '{username}'?\nThis action cannot be undone.").format(username=username)
        confirm_dialog = QMessageBox.question(dialog, self.tr("Confirm Removal"), 
            confirm_message, QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if confirm_dialog == QMessageBox.Yes:
            try:
                subprocess.run(['picomc', 'account', 'remove', username], check=True)
                QMessageBox.information(dialog, self.tr("Success"), 
                    self.tr("Account '{username}' removed successfully!").format(username=username))
                self.populate_accounts_for_all_dialogs()
            except subprocess.CalledProcessError as e:
                error_message = self.tr("Error removing account: {error}").format(error=e.stderr.decode())
                logging.error(error_message)
                QMessageBox.critical(dialog, self.tr("Error"), error_message)


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

        about_message = self.tr(
            "PicoDulce Launcher (v{0})\n\n"
            "A simple Minecraft launcher built using Qt, based on the picomc project.\n\n"
            "Credits:\n"
            "Nixietab: Code and UI design\n"
            "Wabaano: Graphic design\n"
            "Olinad: Christmas!!!!"
        ).format(version_number)

        QMessageBox.about(self, self.tr("About"), about_message)

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
            locales_folder = "locales"

            if not os.path.exists(update_folder):
                os.makedirs(update_folder)

            # Download regular update files
            for link in version_info.get("links", []):
                self.download_file(link, update_folder)

            # Download locale files
            for link in version_info.get("locales", []):
                self.download_file(link, locales_folder)

            # Move downloaded files while preserving directory structure
            def copy_tree_up(src, dst_parent):
                for item in os.listdir(src):
                    s = os.path.join(src, item)
                    d = os.path.join(dst_parent, item)
                    if os.path.isdir(s):
                        if not os.path.exists(d):
                            os.makedirs(d)
                        copy_tree_up(s, dst_parent)
                    else:
                        if os.path.exists(d):
                            os.remove(d)  # Remove existing file if it exists
                        shutil.move(s, d)

            # Move files one directory up while preserving structure
            copy_tree_up(update_folder, os.path.dirname(update_folder))
            copy_tree_up(locales_folder, os.path.dirname(locales_folder))

            # Remove the update folders
            shutil.rmtree(update_folder)
            shutil.rmtree(locales_folder)

            QMessageBox.information(self, "Update", "Updates downloaded successfully.")
        except Exception as e:
            logging.error("Error downloading updates: %s", str(e))
            QMessageBox.critical(self, "Error", "Failed to download updates.")

    def download_file(self, link, folder):
        try:
            # Get the relative path from the URL
            parsed_url = urllib.parse.urlparse(link)
            relative_path = parsed_url.path.lstrip('/')
            # Remove any repository-specific parts if present
            parts = relative_path.split('/', 3)
            if len(parts) > 3:  # If URL contains owner/repo/branch/path format
                relative_path = parts[3]
            
            # Create the full path in the specified folder
            full_path = os.path.join(folder, relative_path)
            # Create the directory structure
            os.makedirs(os.path.dirname(full_path), exist_ok=True)

            # Download the file
            response = requests.get(link, stream=True)
            if response.status_code == 200:
                with open(full_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=1024):
                        f.write(chunk)
                logging.info(f"Successfully downloaded: {relative_path}")
            else:
                QMessageBox.critical(self, "Error", f"Failed to download update file: {relative_path}")
                raise Exception(f"Failed to download {relative_path}")
        except Exception as e:
            logging.error("Error downloading file: %s", str(e))
            QMessageBox.critical(self, "Error", f"Failed to download file: {link}")
            
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
            self.completed.emit(True, self.tr(f"Version {self.version} prepared successfully!"))
        except subprocess.CalledProcessError as e:
            error_message = self.tr(f"Error preparing {self.version}: {e.stderr.decode()}")
            self.completed.emit(False, error_message)

class ModLoaderAndVersionMenu(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(self.tr("Mod Loader and Version Menu"))
        self.setGeometry(100, 100, 400, 300)

        main_layout = QVBoxLayout(self)

        tab_widget = QTabWidget()
        main_layout.addWidget(tab_widget)

        # Create tabs
        install_mod_tab = QWidget()
        download_version_tab = QWidget()
        instances_tab = QWidget()  # New tab for instances

        tab_widget.addTab(download_version_tab, self.tr("Download Version"))
        tab_widget.addTab(install_mod_tab, self.tr("Install Mod Loader"))
        tab_widget.addTab(instances_tab, self.tr("Instances"))  # Add the new tab

        # Add content to "Install Mod Loader" tab
        self.setup_install_mod_loader_tab(install_mod_tab)

        # Add content to "Download Version" tab
        self.setup_download_version_tab(download_version_tab)

        # Add content to "Instances" tab
        self.setup_instances_tab(instances_tab)


    def setup_instances_tab(self, instances_tab):
        layout = QVBoxLayout(instances_tab)

        # Create title label
        title_label = QLabel(self.tr('Manage Minecraft Instances'))
        title_label.setFont(QFont("Arial", 14))
        layout.addWidget(title_label)

        # Create a label to display the current instance
        self.current_instance_label = QLabel(self.tr('Loading...'))  # Placeholder text
        layout.addWidget(self.current_instance_label)

        # Create a QListWidget to display the instances
        self.instances_list_widget = QListWidget()
        layout.addWidget(self.instances_list_widget)

        # Create input field and button to create a new instance
        self.create_instance_input = QLineEdit()
        self.create_instance_input.setPlaceholderText(self.tr("Enter instance name"))
        layout.addWidget(self.create_instance_input)

        create_instance_button = QPushButton(self.tr("Create Instance"))
        create_instance_button.clicked.connect(self.create_instance)
        layout.addWidget(create_instance_button)

        # Fetch and display the current instances
        self.load_instances()

        # Connect the item selection to the instance selection method
        self.instances_list_widget.itemClicked.connect(self.on_instance_selected)

        # Update the label with the current instance from the config
        self.update_instance_label()

    def create_instance(self):
        instance_name = self.create_instance_input.text().strip()

        if instance_name:
            try:
                # Run the "picomc instance create" command
                process = subprocess.Popen(['picomc', 'instance', 'create', instance_name], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                output, error = process.communicate()

                if process.returncode != 0:
                    raise subprocess.CalledProcessError(process.returncode, process.args, error)

                # Notify the user that the instance was created
                QMessageBox.information(self, self.tr("Instance Created"), self.tr(f"Instance '{instance_name}' has been created successfully."))

                # Reload the instances list
                self.load_instances()

                # Optionally select the newly created instance
                self.on_instance_selected(self.instances_list_widget.item(self.instances_list_widget.count() - 1))

            except FileNotFoundError:
                logging.error(self.tr("'picomc' command not found. Please make sure it's installed and in your PATH."))
            except subprocess.CalledProcessError as e:
                logging.error(self.tr("Error creating instance: %s"), e.stderr)
                QMessageBox.critical(self, self.tr("Error"), self.tr(f"Failed to create instance: {e.stderr}"))
        else:
            QMessageBox.warning(self, self.tr("Invalid Input"), self.tr("Please enter a valid instance name."))

    def rename_instance(self, old_instance_name, new_instance_name):
        if old_instance_name == "default":
            QMessageBox.warning(self, self.tr("Cannot Rename Instance"), self.tr("You cannot rename the 'default' instance."))
            return

        try:
            # Run the "picomc instance rename" command
            process = subprocess.Popen(
                ['picomc', 'instance', 'rename', old_instance_name, new_instance_name],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
            )
            output, error = process.communicate()

            if process.returncode != 0:
                raise subprocess.CalledProcessError(process.returncode, process.args, error)

            QMessageBox.information(self, self.tr("Instance Renamed"), self.tr(f"Instance '{old_instance_name}' has been renamed to '{new_instance_name}' successfully."))

            # Reload the instances list
            self.load_instances()

            # Optionally select the newly renamed instance
            matching_items = self.instances_list_widget.findItems(new_instance_name, Qt.MatchExactly)
            if matching_items:
                self.instances_list_widget.setCurrentItem(matching_items[0])

        except FileNotFoundError:
            logging.error(self.tr("'picomc' command not found. Please make sure it's installed and in your PATH."))
        except subprocess.CalledProcessError as e:
            logging.error(self.tr("Error renaming instance: %s"), e.stderr)
            QMessageBox.critical(self, self.tr("Error"), self.tr(f"Failed to rename instance: {e.stderr}"))

    def delete_instance(self, instance_name):
        if instance_name == "default":
            QMessageBox.warning(self, self.tr("Cannot Delete Instance"), self.tr("You cannot delete the 'default' instance."))
            return

        confirm_delete = QMessageBox.question(
            self, self.tr("Confirm Deletion"), self.tr(f"Are you sure you want to delete the instance '{instance_name}'?"),
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )

        if confirm_delete == QMessageBox.Yes:
            try:
                # Run the "picomc instance delete" command
                process = subprocess.Popen(['picomc', 'instance', 'delete', instance_name], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                output, error = process.communicate()

                if process.returncode != 0:
                    raise subprocess.CalledProcessError(process.returncode, process.args, error)

                # Notify the user that the instance was deleted
                QMessageBox.information(self, self.tr("Instance Deleted"), self.tr(f"Instance '{instance_name}' has been deleted successfully."))

                # Reload the instances list
                self.load_instances()

            except FileNotFoundError:
                logging.error(self.tr("'picomc' command not found. Please make sure it's installed and in your PATH."))
            except subprocess.CalledProcessError as e:
                logging.error(self.tr("Error deleting instance: %s"), e.stderr)
                QMessageBox.critical(self, self.tr("Error"), self.tr(f"Failed to delete instance: {e.stderr}"))

    def load_instances(self):
        try:
            process = subprocess.Popen(['picomc', 'instance', 'list'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            output, error = process.communicate()
            if process.returncode != 0:
                raise subprocess.CalledProcessError(process.returncode, process.args, error)

            # Parse the output and add each instance to the list widget
            instances = output.splitlines()
            self.instances_list_widget.clear()  # Clear the previous list
            for instance in instances:
                item = QListWidgetItem()
                self.instances_list_widget.addItem(item)
                self.add_instance_buttons(item, instance)

        except FileNotFoundError:
            logging.error(self.tr("'picomc' command not found. Please make sure it's installed and in your PATH."))
        except subprocess.CalledProcessError as e:
            logging.error(self.tr("Error fetching instances: %s"), e.stderr)

    def add_instance_buttons(self, list_item, instance_name):
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)

        label = QLabel(instance_name)
        rename_button = QPushButton(self.tr("Rename"))
        delete_button = QPushButton(self.tr("Delete"))

        # Stylize the buttons
        button_style = """
        QPushButton {
            padding: 2px 5px;
        }
        """
        rename_button.setStyleSheet(button_style)
        delete_button.setStyleSheet(button_style)

        layout.addWidget(label)
        layout.addStretch()
        layout.addWidget(rename_button)
        layout.addWidget(delete_button)

        widget.setLayout(layout)
        list_item.setSizeHint(widget.sizeHint())
        self.instances_list_widget.setItemWidget(list_item, widget)

        # Connect button signals
        rename_button.clicked.connect(lambda: self.prompt_rename_instance(instance_name))
        delete_button.clicked.connect(lambda: self.delete_instance(instance_name))

    def prompt_rename_instance(self, old_instance_name):
        new_instance_name, ok = QInputDialog.getText(
            self, self.tr("Rename Instance"),
            self.tr(f"Enter new name for instance '{old_instance_name}':")
        )

        if ok and new_instance_name:
            self.rename_instance(old_instance_name, new_instance_name)

    def on_instance_selected(self, item):
        widget = self.instances_list_widget.itemWidget(item)
        instance_name = widget.findChild(QLabel).text()

        config_file = 'config.json'

        if os.path.exists(config_file):
            try:
                with open(config_file, 'r') as file:
                    config_data = json.load(file)

                config_data['Instance'] = instance_name

                with open(config_file, 'w') as file:
                    json.dump(config_data, file, indent=4)

                logging.info(self.tr(f"Config updated: Instance set to {instance_name}"))

                self.update_instance_label()

            except (json.JSONDecodeError, FileNotFoundError) as e:
                logging.error(self.tr(f"Error reading config.json: {e}"))
        else:
            logging.warning(self.tr(f"{config_file} not found. Unable to update instance."))

    def update_instance_label(self):
        config_file = 'config.json'

        if os.path.exists(config_file):
            try:
                with open(config_file, 'r') as file:
                    config_data = json.load(file)

                current_instance = config_data.get('Instance', self.tr('Not set'))
                self.current_instance_label.setText(self.tr(f'Current instance: {current_instance}'))

            except (json.JSONDecodeError, FileNotFoundError) as e:
                logging.error(self.tr(f"Error reading config.json: {e}"))
        else:
            self.current_instance_label.setText(self.tr('Current instance: Not set'))


    def setup_install_mod_loader_tab(self, install_mod_tab):
        layout = QVBoxLayout(install_mod_tab)

        # Create title label
        title_label = QLabel(self.tr('Mod Loader Installer'))
        title_label.setFont(QFont("Arial", 14))
        layout.addWidget(title_label)

        # Create checkboxes for mod loaders
        self.forge_checkbox = QCheckBox(self.tr('Forge'))
        self.fabric_checkbox = QCheckBox(self.tr('Fabric'))
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
        install_button = QPushButton(self.tr('Install'))
        install_button.clicked.connect(lambda: self.install_mod_loader(
            self.version_combo_mod.currentText(), 
            self.forge_checkbox.isChecked(), 
            self.fabric_checkbox.isChecked()
        ))
        layout.addWidget(install_button)

    def setup_download_version_tab(self, download_version_tab):
        layout = QVBoxLayout(download_version_tab)

        # Create title label
        title_label = QLabel(self.tr('Download Version'))
        title_label.setFont(QFont("Arial", 14))
        layout.addWidget(title_label)

        # Create checkboxes for different version types
        self.release_checkbox = QCheckBox(self.tr('Releases'))
        self.snapshot_checkbox = QCheckBox(self.tr('Snapshots'))
        self.alpha_checkbox = QCheckBox(self.tr('Alpha'))
        self.beta_checkbox = QCheckBox(self.tr('Beta'))
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
                    logging.error(self.tr("'picomc' command not found. Please make sure it's installed and in your PATH."))
                    return
                except subprocess.CalledProcessError as e:
                    logging.error(self.tr("Error: %s"), e.stderr)
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
        self.download_button = QPushButton(self.tr('Download'))
        self.download_button.setEnabled(False)  # Initially disabled
        self.download_button.clicked.connect(lambda: self.download_version(self.version_combo.currentText()))
        layout.addWidget(self.download_button)

        # Connect the combo box signal to the update function
        self.version_combo.currentIndexChanged.connect(self.update_download_button_state)

    def update_download_button_state(self):
        self.download_button.setEnabled(self.version_combo.currentIndex() != -1)

    def show_popup(self):
        self.popup = QDialog(self)
        self.popup.setWindowTitle(self.tr("Installing Version"))
        layout = QVBoxLayout(self.popup)

        label = QLabel(self.tr("The version is being installed..."))
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
            QMessageBox.information(self, self.tr("Success"), message)
        else:
            QMessageBox.critical(self, self.tr("Error"), message)
        logging.error(message)

    def populate_available_releases(self, version_combo, install_forge, install_fabric):
        try:
            process = subprocess.Popen(['picomc', 'version', 'list', '--release'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            output, error = process.communicate()
            if process.returncode != 0:
                raise subprocess.CalledProcessError(process.returncode, process.args, error)
        except FileNotFoundError:
            logging.error(self.tr("'picomc' command not found. Please make sure it's installed and in your PATH."))
            return
        except subprocess.CalledProcessError as e:
            logging.error(self.tr("Error: %s"), e.stderr)
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
            QMessageBox.warning(self, self.tr("Select Mod Loader"), self.tr("Please select at least one mod loader."))
            return

        mod_loader = None
        if install_forge:
            mod_loader = 'forge'
        elif install_fabric:
            mod_loader = 'fabric'

        if not mod_loader:
            QMessageBox.warning(self, self.tr("Select Mod Loader"), self.tr("Please select at least one mod loader."))
            return

        try:
            if mod_loader == 'forge':
                subprocess.run(['picomc', 'mod', 'loader', 'forge', 'install', '--game', version], check=True)
            elif mod_loader == 'fabric':
                subprocess.run(['picomc', 'mod', 'loader', 'fabric', 'install', version], check=True)
            QMessageBox.information(self, self.tr("Success"), self.tr(f"{mod_loader.capitalize()} installed successfully for version {version}!"))
        except subprocess.CalledProcessError as e:
            error_message = self.tr(f"Error installing {mod_loader} for version {version}: {e.stderr.decode()}")
            QMessageBox.critical(self, self.tr("Error"), error_message)
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
    window = PicomcVersionSelector()
    window.show()
    sys.exit(app.exec_())
