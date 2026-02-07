import sys
import os
import shutil
import json
import threading
import requests
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QListWidget, QListWidgetItem, QMessageBox, QComboBox, QDialog, QTabWidget, QMainWindow, QSpacerItem, QSizePolicy
from PyQt5.QtCore import Qt, QSize, QObject, pyqtSignal
from PyQt5.QtGui import QIcon, QPixmap

CONFIG_FILE = "config.json"








class IconLoader(QObject, threading.Thread):
    icon_loaded = pyqtSignal(QPixmap)

    def __init__(self, icon_url):
        super().__init__()
        threading.Thread.__init__(self)
        self.icon_url = icon_url

    def run(self):
        try:
            response = requests.get(self.icon_url)
            if response.status_code == 200:
                pixmap = QPixmap()
                pixmap.loadFromData(response.content)
                self.icon_loaded.emit(pixmap.scaled(QSize(42, 42), Qt.KeepAspectRatio, Qt.SmoothTransformation))
            else:
                self.icon_loaded.emit(QPixmap("missing.png"))
        except Exception as e:
            print("Error loading icon:", e)
            self.icon_loaded.emit(QPixmap("missing.png"))

class ModrinthSearchApp(QWidget):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Marroc Mod Manager")
        self.setGeometry(100, 100, 500, 400)
        self.ensure_directories_exist()

        layout = QVBoxLayout()

        tab_widget = QTabWidget()
        self.search_tab = QWidget()
        self.mods_tab = QWidget()

        tab_widget.addTab(self.search_tab, "Search")
        tab_widget.addTab(self.mods_tab, "Manager")

        self.init_search_tab()
        self.init_mods_tab()

        layout.addWidget(tab_widget)

        self.setLayout(layout)

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

    def ensure_directories_exist(self):
        directories = ["marroc/mods", "marroc/resourcepacks"]
        for directory in directories:
            if not os.path.exists(directory):
                os.makedirs(directory)

    def init_search_tab(self):
        layout = QVBoxLayout()

        search_layout = QHBoxLayout()  
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Enter a search term...")
        search_layout.addWidget(self.search_input)

        self.search_button = QPushButton("Search")
        self.search_button.clicked.connect(self.search_mods)
        search_layout.addWidget(self.search_button)

        self.search_type_dropdown = QComboBox()  
        self.search_type_dropdown.addItems(["Mod", "Texture Pack"])
        search_layout.addWidget(self.search_type_dropdown)

        layout.addLayout(search_layout)

        self.mods_list = QListWidget()
        layout.addWidget(self.mods_list)

        self.select_button = QPushButton("Select")
        self.select_button.clicked.connect(self.show_mod_details_window)
        layout.addWidget(self.select_button)

        self.selected_mod = None

        self.search_tab.setLayout(layout)

    def init_mods_tab(self):
        layout = QVBoxLayout()
        self.mod_manager_window = ModManagerWindow()  
        layout.addWidget(self.mod_manager_window)
        self.mods_tab.setLayout(layout)

    def search_mods(self):
        self.mods_list.clear()
        mod_name = self.search_input.text()
        search_type = self.search_type_dropdown.currentText().lower()  
        if search_type == "texture pack":
            api_url = f"https://api.modrinth.com/v2/search?query={mod_name}&limit=20&facets=%5B%5B%22project_type%3Aresourcepack%22%5D%5D"
        else:
            api_url = f"https://api.modrinth.com/v2/search?query={mod_name}&limit=20&facets=%5B%5B%22project_type%3A{search_type}%22%5D%5D"
        response = requests.get(api_url)
        if response.status_code == 200:
            mods_data = json.loads(response.text)
            for mod in mods_data['hits']:
                mod_name = mod['title']
                mod_description = mod['description']
                icon_url = mod['icon_url']
                item = QListWidgetItem(f"Title: {mod_name}\nDescription: {mod_description}")
                item.setSizeHint(QSize(200, 50))  
                icon_loader = IconLoader(icon_url)
                icon_loader.icon_loaded.connect(lambda pixmap, item=item: self.set_item_icon(item, pixmap))
                icon_loader.start()
                item.mod_data = mod
                self.mods_list.addItem(item)
        else:
            self.mods_list.addItem("Failed to fetch mods. Please try again later.")

    def set_item_icon(self, item, pixmap):
        if pixmap:
            item.setData(Qt.DecorationRole, pixmap)
        else:
            # Set a default icon if loading failed
            item.setIcon(QIcon("missing.png"))

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

class ModManagerWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Mod Manager")
        self.setGeometry(100, 100, 600, 400)

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)

        self.layout = QHBoxLayout(self.central_widget)

        self.file_type_combo_box = QComboBox()
        self.file_type_combo_box.addItems(["Mods", "Resource Packs"])
        self.file_type_combo_box.currentIndexChanged.connect(self.load_files)

        self.available_files_widget = QListWidget()

        self.installed_files_widget = QListWidget()

        self.button_dropdown_layout = QVBoxLayout()
        self.button_dropdown_layout.addWidget(self.file_type_combo_box)
        self.button_dropdown_layout.addSpacerItem(QSpacerItem(20, 40, QSizePolicy.Minimum, QSizePolicy.Expanding))
        self.move_right_button = QPushButton(">")
        self.move_right_button.clicked.connect(self.move_right)
        self.button_dropdown_layout.addWidget(self.move_right_button)
        self.move_left_button = QPushButton("<")
        self.move_left_button.clicked.connect(self.move_left)
        self.button_dropdown_layout.addWidget(self.move_left_button)
        self.delete_button = QPushButton("Delete")
        self.delete_button.clicked.connect(self.delete_selected_item)
        self.button_dropdown_layout.addWidget(self.delete_button)
        self.button_dropdown_layout.addSpacerItem(QSpacerItem(20, 40, QSizePolicy.Minimum, QSizePolicy.Expanding))

        self.layout.addWidget(self.available_files_widget)
        self.layout.addLayout(self.button_dropdown_layout)
        self.layout.addWidget(self.installed_files_widget)

        self.load_files()

    def load_files(self):
        file_type = self.file_type_combo_box.currentText()
        if file_type == "Mods":
            self.load_mods()
        elif file_type == "Resource Packs":
            self.load_resource_packs()

    def load_mods(self):
        mods_directory = "marroc/mods"
        if os.path.exists(mods_directory) and os.path.isdir(mods_directory):
            mods = os.listdir(mods_directory)
            self.available_files_widget.clear()
            self.available_files_widget.addItems(mods)
        self.load_installed_mods("mods")

    def load_resource_packs(self):
        resource_packs_directory = "marroc/resourcepacks"
        if os.path.exists(resource_packs_directory) and os.path.isdir(resource_packs_directory):
            resource_packs = os.listdir(resource_packs_directory)
            self.available_files_widget.clear()
            self.available_files_widget.addItems(resource_packs)
        self.load_installed_mods("resourcepacks")

    def load_installed_mods(self, file_type):
        if sys.platform.startswith('linux'):
            minecraft_directory = os.path.expanduser("~/.local/share/zucaro/instances/default/minecraft")
        elif sys.platform.startswith('win'):
            minecraft_directory = os.path.join(os.getenv('APPDATA'), '.zucaro/instances/default/minecraft')
        else:
            minecraft_directory = ""
        if minecraft_directory:
            installed_files_directory = os.path.join(minecraft_directory, file_type)
            if os.path.exists(installed_files_directory) and os.path.isdir(installed_files_directory):
                installed_files = os.listdir(installed_files_directory)
                self.installed_files_widget.clear()
                self.installed_files_widget.addItems(installed_files)

    def move_right(self):
        selected_item = self.available_files_widget.currentItem()
        if selected_item:
            source_directory = self.get_source_directory()
            destination_directory = self.get_destination_directory()
            file_name = selected_item.text()
            source_path = os.path.join(source_directory, file_name)
            destination_path = os.path.join(destination_directory, file_name)
            shutil.move(source_path, destination_path)
            self.load_files()

    def move_left(self):
        selected_item = self.installed_files_widget.currentItem()
        if selected_item:
            source_directory = self.get_destination_directory()
            destination_directory = self.get_source_directory()
            file_name = selected_item.text()
            source_path = os.path.join(source_directory, file_name)
            destination_path = os.path.join(destination_directory, file_name)
            shutil.move(source_path, destination_path)
            self.load_files()

    def delete_selected_item(self):
        selected_item = self.available_files_widget.currentItem() or self.installed_files_widget.currentItem()
        if selected_item:
            file_name = selected_item.text()
            reply = QMessageBox.question(self, 'Delete Item', f'Are you sure you want to delete "{file_name}"?',
                                         QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            if reply == QMessageBox.Yes:
                file_type = self.file_type_combo_box.currentText()
                if file_type == "Mods":
                    directory = "marroc/mods"
                elif file_type == "Resource Packs":
                    directory = "marroc/resourcepacks"
                else:
                    return
                file_path = os.path.join(directory, file_name)
                if os.path.exists(file_path):
                    os.remove(file_path)
                    self.load_files()
                else:
                    QMessageBox.warning(self, 'File Not Found', 'The selected file does not exist.')

    def get_source_directory(self):
        file_type = self.file_type_combo_box.currentText()
        if file_type == "Mods":
            return "marroc/mods"
        elif file_type == "Resource Packs":
            return "marroc/resourcepacks"
        else:
            return ""

    def get_destination_directory(self):
        file_type = self.file_type_combo_box.currentText()
        if file_type == "Mods":
            if sys.platform.startswith('linux'):
                return os.path.expanduser("~/.local/share/zucaro/instances/default/minecraft/mods")
            elif sys.platform.startswith('win'):
                return os.path.join(os.getenv('APPDATA'), '.zucaro/instances/default/minecraft/mods')
        elif file_type == "Resource Packs":
            if sys.platform.startswith('linux'):
                return os.path.expanduser("~/.local/share/zucaro/instances/default/minecraft/resourcepacks")
            elif sys.platform.startswith('win'):
                return os.path.join(os.getenv('APPDATA'), '.zucaro/instances/default/minecraft/resourcepacks')
        else:
            return ""

class ModDetailsWindow(QDialog):
    def __init__(self, mod_data, icon_url, mod_versions):
        super().__init__()

        self.setWindowTitle("Mod Details")
        self.setGeometry(100, 100, 400, 300)

        self.mod_data = mod_data  

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
            icon_label.setPixmap(icon_pixmap)
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
                return pixmap.scaled(QSize(128, 128), Qt.KeepAspectRatio, Qt.SmoothTransformation)
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
                    save_dir = "marroc/mods" if filename.endswith('.jar') else "marroc/resourcepacks"
                    with open(os.path.join(save_dir, filename), 'wb') as f:
                        f.write(response.content)
                    QMessageBox.information(self, "Download Mod", f"Downloaded {filename} successfully.")
                    return
                except requests.exceptions.RequestException as e:
                    QMessageBox.warning(self, "Download Error", f"Error downloading mod: {e}")
                    return
        QMessageBox.warning(self, "Download Mod", "Failed to download the mod.")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app_icon = QIcon('marroc.ico')  
    app.setWindowIcon(app_icon)  
    window = ModrinthSearchApp()
    window.show()
    sys.exit(app.exec_())
