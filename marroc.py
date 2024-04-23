import sys
import os
import shutil
import json
import requests
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QListWidget, QListWidgetItem, QMessageBox, QComboBox, QDialog, QTabWidget, QFileDialog, QListView
from PyQt5.QtCore import Qt, QSize, QDir, QStringListModel
from PyQt5.QtGui import QPixmap, QIcon, QPalette, QColor



CONFIG_FILE = "config.json"

class ModrinthSearchApp(QWidget):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Marroc Mod Manager")
        self.setGeometry(100, 100, 500, 400)

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
        palette.setColor(QPalette.Highlight, QColor(42, 130, 218))
        palette.setColor(QPalette.HighlightedText, Qt.white)
        self.setPalette(palette)


        layout = QVBoxLayout()

        tab_widget = QTabWidget()
        self.search_tab = QWidget()
        self.mods_tab = QWidget()

        tab_widget.addTab(self.search_tab, "Search")
        tab_widget.addTab(self.mods_tab, "Mods")

        self.init_search_tab()
        self.init_mods_tab()

        layout.addWidget(tab_widget)

        self.setLayout(layout)

    def init_search_tab(self):
        layout = QVBoxLayout()

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Enter mod name...")
        layout.addWidget(self.search_input)

        self.search_button = QPushButton("Search")
        self.search_button.clicked.connect(self.search_mods)
        layout.addWidget(self.search_button)

        self.mods_list = QListWidget()
        layout.addWidget(self.mods_list)

        self.select_button = QPushButton("Select Mod")
        self.select_button.clicked.connect(self.show_mod_details_window)
        layout.addWidget(self.select_button)

        self.selected_mod = None

        self.search_tab.setLayout(layout)

    def init_mods_tab(self):
        layout = QVBoxLayout()
        self.mod_manager = ModManager()  # Integrate ModManager into Mods Tab
        layout.addWidget(self.mod_manager)
        self.mods_tab.setLayout(layout)

    def search_mods(self):
        self.mods_list.clear()
        mod_name = self.search_input.text()
        api_url = f"https://api.modrinth.com/v2/search?query={mod_name}&limit=20&facets=%5B%5B%22project_type%3Amod%22%5D%5D"
        response = requests.get(api_url)
        if response.status_code == 200:
            mods_data = json.loads(response.text)
            for mod in mods_data['hits']:
                mod_name = mod['title']
                mod_description = mod['description']
                item = QListWidgetItem(f"Title: {mod_name}\nDescription: {mod_description}")
                item.setSizeHint(QSize(100, 50))  # Set size hint to increase height
                item.mod_data = mod
                self.mods_list.addItem(item)
        else:
            self.mods_list.addItem("Failed to fetch mods. Please try again later.")

    def show_mod_details_window(self):
        selected_item = self.mods_list.currentItem()
        if selected_item is not None:
            mod_data = selected_item.mod_data
            mod_slug = mod_data.get('slug')
            if mod_slug:
                api_url = f"https://api.modrinth.com/v2/project/{mod_slug}"
                response = requests.get(api_url)
                if response.status_code == 200:
                    mod_info = json.loads(response.text)
                    icon_url = mod_info.get('icon_url')
                    mod_versions = self.get_mod_versions(mod_slug)
                    mod_details_window = ModDetailsWindow(mod_data, icon_url, mod_versions)
                    mod_details_window.exec_()
                else:
                    QMessageBox.warning(self, "Failed to Fetch Mod Details", "Failed to fetch mod details. Please try again later.")
            else:
                QMessageBox.warning(self, "No Mod Slug", "Selected mod has no slug.")
        else:
            QMessageBox.warning(self, "No Mod Selected", "Please select a mod first.")

    def get_mod_versions(self, mod_slug):
        api_url = f"https://api.modrinth.com/v2/project/{mod_slug}/version"
        response = requests.get(api_url)
        if response.status_code == 200:
            versions = json.loads(response.text)
            mod_versions = []
            for version in versions:
                version_name = version['name']
                version_files = version.get('files', [])
                if version_files:
                    file_urls = [file['url'] for file in version_files]
                    mod_versions.append({'version': version_name, 'files': file_urls})
                else:
                    mod_versions.append({'version': version_name, 'files': []})
            return mod_versions
        else:
            return []

class ModManager(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Mod Manager")
        self.setGeometry(100, 100, 600, 400)

        self.load_config()
        self.mods = []
        self.available_mods = []

        layout = QHBoxLayout()

        layout_mods = QVBoxLayout()
        layout_buttons = QVBoxLayout()
        layout_arrow = QVBoxLayout()
        layout_available_mods = QVBoxLayout()

        self.list_view_mods = QListView()
        self.list_view_mods.doubleClicked.connect(self.move_mod_to_local)
        self.list_view_available_mods = QListView()
        self.list_view_available_mods.doubleClicked.connect(self.move_mod_to_minecraft)
        self.populate_mod_list()

        self.arrow_right_button = QPushButton(">")
        self.arrow_right_button.setIcon(QIcon('arrow_right.png'))
        self.arrow_right_button.setIconSize(QSize(32, 32))
        self.arrow_right_button.clicked.connect(self.move_mod_to_minecraft)

        self.arrow_left_button = QPushButton("<")
        self.arrow_left_button.setIcon(QIcon('arrow_left.png'))
        self.arrow_left_button.setIconSize(QSize(32, 32))
        self.arrow_left_button.clicked.connect(self.move_mod_to_local)

        self.delete_button = QPushButton("Delete")
        self.delete_button.clicked.connect(self.delete_mod)

        self.config_button = QPushButton("Config")
        self.config_button.clicked.connect(self.select_mods_directory)

        self.refresh_button = QPushButton("Refresh")
        self.refresh_button.clicked.connect(self.refresh_mod_list)

        layout_mods.addWidget(self.list_view_mods)
        layout_buttons.addWidget(self.arrow_right_button)
        layout_buttons.addWidget(self.arrow_left_button)
        layout_buttons.addWidget(self.delete_button)
        layout_buttons.addWidget(self.config_button)
        layout_buttons.addWidget(self.refresh_button)  # Add refresh button
        layout_arrow.addLayout(layout_buttons)
        layout_available_mods.addWidget(self.list_view_available_mods)

        layout.addLayout(layout_mods)
        layout.addLayout(layout_arrow)
        layout.addLayout(layout_available_mods)

        self.setLayout(layout)

    # Other methods remain unchanged

    def refresh_mod_list(self):
        self.populate_mod_list()

    def load_config(self):
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, 'r') as f:
                config = json.load(f)
                self.mod_folder = config.get('mod_folder')
                if not self.mod_folder:
                    self.set_default_mod_folder()
        else:
            self.set_default_mod_folder()

    def set_default_mod_folder(self):
        if sys.platform == 'win32':
            self.mod_folder = os.path.expandvars('%APPDATA%\\.picomc\\instances\\default\\mods')
        elif sys.platform == 'linux':
            self.mod_folder = os.path.expanduser('~/.local/share/picomc/instances/default/minecraft/mods')
        else:
            self.mod_folder = QDir.homePath()

    def save_config(self):
        config = {'mod_folder': self.mod_folder}
        with open(CONFIG_FILE, 'w') as f:
            json.dump(config, f)

    def populate_mod_list(self):
        self.available_mods = os.listdir(self.mod_folder)
        self.mods = [f for f in os.listdir('.') if os.path.isfile(f) and f.endswith('.jar')]
        
        self.model_mods = QStringListModel(self.mods)
        self.model_available_mods = QStringListModel(self.available_mods)
        
        self.list_view_mods.setModel(self.model_mods)
        self.list_view_available_mods.setModel(self.model_available_mods)

    def move_mod_to_minecraft(self):
        selected_mod_index = self.list_view_mods.currentIndex()
        selected_mod = self.mods[selected_mod_index.row()]
        destination_path = os.path.join(self.mod_folder, os.path.basename(selected_mod))
        
        if os.path.exists(destination_path):
            QMessageBox.warning(self, "Error", "A mod with the same name already exists in the mods folder.")
        else:
            shutil.move(selected_mod, self.mod_folder)
            self.available_mods.append(selected_mod)
            self.model_available_mods.setStringList(self.available_mods)

            # Update the lists
            self.populate_mod_list()
            self.save_config()

    def move_mod_to_local(self):
        selected_mod_index = self.list_view_available_mods.currentIndex()
        selected_mod = self.available_mods[selected_mod_index.row()]
        destination_path = os.path.join(os.getcwd(), os.path.basename(selected_mod))
        
        if os.path.exists(destination_path):
            QMessageBox.warning(self, "Error", "A mod with the same name already exists in the current directory.")
        else:
            shutil.move(os.path.join(self.mod_folder, selected_mod), os.getcwd())
            self.mods.append(selected_mod)
            self.model_mods.setStringList(self.mods)

            # Update the lists
            self.populate_mod_list()
            self.save_config()

    def delete_mod(self):
        selected_mod_index = self.list_view_available_mods.currentIndex()
        selected_mod = self.available_mods[selected_mod_index.row()]

        reply = QMessageBox.question(self, 'Confirmation', f"Are you sure you want to delete '{selected_mod}'?",
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            os.remove(os.path.join(self.mod_folder, selected_mod))
            self.available_mods.remove(selected_mod)
            self.model_available_mods.setStringList(self.available_mods)
            self.save_config()

    def select_mods_directory(self):
        directory = QFileDialog.getExistingDirectory(self, "Select Minecraft Mods Directory", self.mod_folder)
        if directory:
            self.mod_folder = directory
            self.populate_mod_list()
            self.save_config()


class ModDetailsWindow(QDialog):
    def __init__(self, mod_data, icon_url, mod_versions):
        super().__init__()

        self.setWindowTitle("Mod Details")
        self.setGeometry(100, 100, 400, 300)

        self.mod_data = mod_data  # Store mod data

        layout = QVBoxLayout()

        mod_name_label = QLabel(f"<h2>{mod_data['title']}</h2>")
        mod_name_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(mod_name_label)

        mod_description_label = QLabel(mod_data['description'])
        mod_description_label.setWordWrap(True)
        layout.addWidget(mod_description_label)

        icon_pixmap = self.load_icon(icon_url)
        icon_label = QLabel()
        if icon_pixmap:
            icon_label.setPixmap(icon_pixmap.scaledToWidth(200))
            icon_label.setAlignment(Qt.AlignCenter)
            layout.addWidget(icon_label)

        self.version_dropdown = QComboBox()
        for version in mod_versions:
            self.version_dropdown.addItem(version['version'])
            self.version_dropdown.setItemData(self.version_dropdown.count() - 1, version['files'], Qt.UserRole)
        layout.addWidget(self.version_dropdown)

        self.download_button = QPushButton("Download")
        self.download_button.clicked.connect(self.download_mod)
        layout.addWidget(self.download_button)

        self.download_url_label = QLabel()
        self.download_url_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.download_url_label)

        layout.addStretch(1)

        self.setLayout(layout)

    def load_icon(self, icon_url):
        try:
            response = requests.get(icon_url)
            if response.status_code == 200:
                pixmap = QPixmap()
                pixmap.loadFromData(response.content)
                return pixmap
            else:
                return None
        except Exception as e:
            print("Error loading icon:", e)
            return None

    def download_mod(self):
        selected_version_index = self.version_dropdown.currentIndex()
        selected_version_files = self.version_dropdown.itemData(selected_version_index, Qt.UserRole)
        if selected_version_files:
            for file_url in selected_version_files:
                filename = os.path.basename(file_url)
                try:
                    response = requests.get(file_url)
                    response.raise_for_status()
                    with open(filename, 'wb') as f:
                        f.write(response.content)
                    QMessageBox.information(self, "Download Mod", f"Downloaded {filename} successfully.")
                    return
                except requests.exceptions.RequestException as e:
                    QMessageBox.warning(self, "Download Error", f"Error downloading mod: {e}")
                    return
        QMessageBox.warning(self, "Download Mod", "Failed to download the mod.")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app_icon = QIcon('marroc.ico')  # Provide the path to your icon file
    app.setWindowIcon(app_icon)  # Set the application icon
    window = ModrinthSearchApp()
    window.show()
    sys.exit(app.exec_())