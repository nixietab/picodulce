import sys
import subprocess
import ctypes
import threading
import logging
from PyQt5.QtWidgets import QApplication, QComboBox, QWidget, QVBoxLayout, QPushButton, QMessageBox, QDialog, QHBoxLayout, QLabel, QLineEdit, QCheckBox
from PyQt5.QtGui import QFont, QIcon, QColor, QPalette
from PyQt5.QtCore import Qt

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class PicomcVersionSelector(QWidget):
    def __init__(self):
        super().__init__()

        self.init_ui()

    def init_ui(self):
        self.setWindowTitle('PicoDulce Launcher')  # Change window title
        self.setWindowIcon(QIcon('launcher_icon.ico'))  # Set window icon
        self.setGeometry(100, 100, 400, 250)

        # Set application style and palette
        app_style = QApplication.setStyle("Fusion")
        dark_palette = self.create_dark_palette()
        QApplication.instance().setPalette(dark_palette)

        # Set window border color to dark mode on Windows
        if sys.platform == 'win32':
            self.setStyleSheet("QMainWindow { border: 2px solid rgb(53, 53, 53); }")

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
        self.play_button.setStyleSheet("background-color: #4bb679; color: white;")
        buttons_layout.addWidget(self.play_button)

        # Create button to open version download menu
        self.version_download_button = QPushButton('Download Version')
        self.version_download_button.clicked.connect(self.open_version_menu)
        buttons_layout.addWidget(self.version_download_button)

        # Create button to manage accounts
        self.manage_accounts_button = QPushButton('Manage Accounts')
        self.manage_accounts_button.clicked.connect(self.manage_accounts)
        buttons_layout.addWidget(self.manage_accounts_button)

        # Create button to install mod loader
        self.install_mod_loader_button = QPushButton('Install Mod Loader')
        self.install_mod_loader_button.clicked.connect(self.open_mod_loader_menu)
        buttons_layout.addWidget(self.install_mod_loader_button)

        # Create About button
        self.about_button = QPushButton('About')
        self.about_button.clicked.connect(self.show_about_dialog)
        buttons_layout.addWidget(self.about_button)

        # Set buttons layout alignment and spacing
        buttons_layout.setAlignment(Qt.AlignTop)
        buttons_layout.setSpacing(10)

        # Set layout
        main_layout = QVBoxLayout()
        main_layout.addWidget(title_label, alignment=Qt.AlignCenter)
        main_layout.addWidget(installed_versions_label)
        main_layout.addWidget(self.installed_version_combo)
        main_layout.addLayout(buttons_layout)
        main_layout.setAlignment(Qt.AlignCenter)
        main_layout.setSpacing(20)

        self.setLayout(main_layout)
        
    def populate_installed_versions(self):
        # Run the command and get the output
        try:
            process = subprocess.Popen(['py', '-m','picomc', 'version', 'list'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
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

    def play_instance(self):
        if self.installed_version_combo.count() == 0:
            QMessageBox.warning(self, "No Version Available", "Please download a version first.")
            return
        
        #Checks if you have an account
        accounts = PicomcVersionSelector.get_accounts_list(self)
        if(accounts == None):
            return QMessageBox.critical(self, "No accounts created", "You need to create an account to play")
        
        selected_instance = self.installed_version_combo.currentText()

        # Create a separate thread to run the game process
        play_thread = threading.Thread(target=self.run_game, args=(selected_instance,))
        play_thread.start()

    def run_game(self, selected_instance):
        try:
            subprocess.run(['py', '-m','picomc', 'play', selected_instance], check=True)
        except subprocess.CalledProcessError as e:
            error_message = f"Error playing {selected_instance}: {e.stderr.decode()}"
            logging.error(error_message)
            QMessageBox.critical(self, "Error", error_message)

    def open_version_menu(self):
        dialog = QDialog(self)
        dialog.setWindowTitle('Download Version')
        dialog.setFixedSize(300, 250)

        # Create title label
        title_label = QLabel('Download Version')
        title_label.setFont(QFont("Arial", 14))

        # Create checkboxes for different version types
        release_checkbox = QCheckBox('Releases')
        snapshot_checkbox = QCheckBox('Snapshots')
        alpha_checkbox = QCheckBox('Alpha')
        beta_checkbox = QCheckBox('Beta')
        release_checkbox.setChecked(True)
        # Create dropdown menu for versions
        version_combo = QComboBox()

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
                    process = subprocess.Popen(['py', '-m','picomc', 'version', 'list'] + options, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
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
                
        update_versions()
        release_checkbox.clicked.connect(update_versions)
        snapshot_checkbox.clicked.connect(update_versions)
        alpha_checkbox.clicked.connect(update_versions)
        beta_checkbox.clicked.connect(update_versions)

        # Set layout
        layout = QVBoxLayout()
        layout.addWidget(title_label)
        layout.addWidget(release_checkbox)
        layout.addWidget(snapshot_checkbox)
        layout.addWidget(alpha_checkbox)
        layout.addWidget(beta_checkbox)
        layout.addWidget(version_combo)

        # Create download button
        download_button = QPushButton('Download')
        download_button.clicked.connect(lambda: self.prepare_version(dialog, version_combo.currentText()))

        layout.addWidget(download_button)

        dialog.setLayout(layout)
        dialog.exec_()

    def prepare_version(self, dialog, version):
        dialog.close()
        try:
            subprocess.run(['py', '-m','picomc', 'version', 'prepare', version], check=True)
            QMessageBox.information(self, "Success", f"Version {version} prepared successfully!")
            self.populate_installed_versions()  # Refresh the installed versions list after downloading
        except subprocess.CalledProcessError as e:
            error_message = f"Error preparing {version}: {e.stderr.decode()}"
            QMessageBox.critical(self, "Error", error_message)
            logging.error(error_message)

    def manage_accounts(self):
        dialog = QDialog(self)
        dialog.setWindowTitle('Manage Accounts')
        dialog.setFixedSize(300, 150)

        # Create title label
        title_label = QLabel('Manage Accounts')
        title_label.setFont(QFont("Arial", 14))

        # Create dropdown menu for accounts
        account_combo = QComboBox()
        self.populate_accounts(account_combo)

        # Create select button
        select_button = QPushButton('Select')
        select_button.clicked.connect(lambda: self.set_default_account(dialog, account_combo.currentText()))

        # Set layout
        layout = QVBoxLayout()
        layout.addWidget(title_label)
        layout.addWidget(account_combo)
        layout.addWidget(select_button)

        # Create a separate section for creating a new account
        create_account_layout = QHBoxLayout()
        new_account_input = QLineEdit()
        create_account_button = QPushButton('Create')
        create_account_button.clicked.connect(lambda: self.create_account(dialog, new_account_input.text()))
        create_account_layout.addWidget(new_account_input)
        create_account_layout.addWidget(create_account_button)

        layout.addLayout(create_account_layout)

        dialog.setLayout(layout)
        dialog.exec_()

    def populate_accounts(self, account_combo):
        # Run the command and get the output
        accounts = PicomcVersionSelector.get_accounts_list(self)

        # Populate accounts combo box
        account_combo.clear()
        account_combo.addItems(accounts)

    def create_account(self, dialog, username):
        if username.strip() == '':
            QMessageBox.warning(dialog, "Warning", "Username cannot be blank.")
            return
        try:
            subprocess.run(['py', '-m','picomc', 'account', 'create', username], check=True)
            QMessageBox.information(self, "Success", f"Account {username} created successfully!")
            self.populate_accounts(dialog.findChild(QComboBox))
        except subprocess.CalledProcessError as e:
            error_message = f"Error creating account: {e.stderr.decode()}"
            QMessageBox.critical(self, "Error", error_message)
            logging.error(error_message)

    def get_accounts_list(self):
        try:
            process = subprocess.Popen(['py', '-m','picomc', 'account', 'list'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
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
        return accounts
    
    
    def set_default_account(self, dialog, account):
        dialog.close()
        try:
            subprocess.run(['py', '-m','picomc', 'account', 'setdefault', account], check=True)
            QMessageBox.information(self, "Success", f"Default account set to {account}!")
        except subprocess.CalledProcessError as e:
            error_message = f"Error setting default account: {e.stderr.decode()}"
            QMessageBox.critical(self, "Error", error_message)
            logging.error(error_message)

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
                    subprocess.run(['py', '-m','picomc', 'account', 'remove', username], check=True)
                    QMessageBox.information(self, "Success", f"Account '{username}' removed successfully!")
                    self.populate_accounts(dialog.findChild(QComboBox))
                except subprocess.CalledProcessError as e:
                    error_message = f"Error removing account: {e.stderr.decode()}"
                    logging.error(error_message)
                    QMessageBox.critical(self, "Error", error_message)

    def show_about_dialog(self):
        about_message = "PicoDulce Launcher\n\nA simple gui for the picomc proyect."
        QMessageBox.about(self, "About", about_message)

    def create_dark_palette(self):
        palette = QApplication.palette()
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
        palette.setColor(QPalette.HighlightedText, Qt.white)  # Change highlighted text color to white
        return palette
    
    def open_mod_loader_menu(self):
        dialog = QDialog(self)
        dialog.setWindowTitle('Mod Loader Installer')
        dialog.setFixedSize(300, 200)

        # Create title label
        title_label = QLabel('Mod Loader Installer')
        title_label.setFont(QFont("Arial", 14))

        # Create checkboxes for mod loaders
        forge_checkbox = QCheckBox('Forge')
        fabric_checkbox = QCheckBox('Fabric')

        # Create dropdown menu for versions
        version_combo = QComboBox()

        def update_versions():
            version_combo.clear()
            if forge_checkbox.isChecked():
                self.populate_available_releases(version_combo, True, False)
            elif fabric_checkbox.isChecked():
                self.populate_available_releases(version_combo, False, True)

        forge_checkbox.clicked.connect(update_versions)
        fabric_checkbox.clicked.connect(update_versions)

        # Set layout
        layout = QVBoxLayout()
        layout.addWidget(title_label)
        layout.addWidget(forge_checkbox)
        layout.addWidget(fabric_checkbox)
        layout.addWidget(version_combo)

        # Create install button
        install_button = QPushButton('Install')
        install_button.clicked.connect(lambda: self.install_mod_loader(dialog, version_combo.currentText(), forge_checkbox.isChecked(), fabric_checkbox.isChecked()))
        layout.addWidget(install_button)

        dialog.setLayout(layout)
        dialog.exec_()
    def populate_available_releases(self, version_combo, install_forge, install_fabric):
        try:
            process = subprocess.Popen(['py', '-m','picomc', 'version', 'list', '--release'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
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

    def install_mod_loader(self, dialog, version, install_forge, install_fabric):
        if not install_forge and not install_fabric:
            QMessageBox.warning(dialog, "Select Mod Loader", "Please select at least one mod loader.")
            return

        mod_loader = None
        if install_forge:
            mod_loader = 'forge'
        elif install_fabric:
            mod_loader = 'fabric'

        if not mod_loader:
            QMessageBox.warning(dialog, "Select Mod Loader", "Please select at least one mod loader.")
            return

        try:
            if mod_loader == 'forge':
                subprocess.run(['py', '-m','picomc', 'mod', 'loader', 'forge', 'install', '--game', version], check=True)
            elif mod_loader == 'fabric':
                subprocess.run(['py', '-m','picomc', 'mod', 'loader', 'fabric', 'install', version], check=True)
            QMessageBox.information(self, "Success", f"{mod_loader.capitalize()} installed successfully for version {version}!")
            self.populate_installed_versions()  # Refresh the installed versions list after installation
        except subprocess.CalledProcessError as e:
            error_message = f"Error installing {mod_loader} for version {version}: {e.stderr.decode()}"
            QMessageBox.critical(self, "Error", error_message)
            logging.error(error_message)

def install_dependencies(pip, picomc):
    if(pip == False):
        try:
            logging.info("Installing Pip")
            process = subprocess.Popen(['py', '-m', 'ensurepip', '--upgrade'])
            output, error = process.communicate()
            process.wait()
            if process.returncode != 0:
                raise subprocess.CalledProcessError(process.returncode, process.args, error)
            logging.info("Pip installed successfully")
        except subprocess.CalledProcessError as e:
            logging.error("Error: %s", e.stderr)

    if(picomc == False):
        try:
            logging.info("Installing Picomc")
            process = subprocess.Popen(['py', '-m', 'pip', 'install', 'picomc'])
            output, error = process.communicate()
            process.wait()
            if process.returncode != 0:
                raise subprocess.CalledProcessError(process.returncode, process.args, error)
            else:
                logging.info("Picomc installed successfully")
        except subprocess.CalledProcessError as e:
            logging.error("Error: %s", e.stderr)
    
def check_dependencies():
    pip = True
    picomc = True
    
    #Check if Piython is installed
    try:
        logging.info("Searching for Python")
        process = subprocess.Popen(['py', '--version'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,)
        process.wait()
        output, error = process.communicate()
        if process.returncode != 0:
            raise subprocess.CalledProcessError(process.returncode, process.args, error)
    except FileNotFoundError:
                ctypes.windll.user32.MessageBoxW(0, 'This launcher needs Python to work \n' + "https://www.python.org/", "Python is not installed!", 0)
                input("Install Python and press any key")
                check_dependencies()
    except subprocess.CalledProcessError as e:
        ctypes.windll.user32.MessageBoxW(0, 'This launcher needs Python to work \n' + "https://www.python.org/", "Python is not installed!", 0)
        input("Install Python and press any key")
        check_dependencies()

    #Chekc if Pip is installed
    try:
        logging.info("Searching for Pip")
        process = subprocess.Popen(['py', '-m', 'pip'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,)
        output, error = process.communicate()
        process.wait()
        if process.returncode != 0:
            pip = False
            raise subprocess.CalledProcessError(process.returncode, process.args, error)
    except FileNotFoundError:
        logging.error("'Pip' command not found")
        pip = False
    if(pip):
        logging.info("Pip is installed")

    #Check if Picomc is installed
    try:
        logging.info("Searching for Picomc")
        process = subprocess.Popen(['picomc'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,)
        process.wait()
        output, error = process.communicate()
        if process.returncode != 0:
            picomc = False;
            raise subprocess.CalledProcessError(process.returncode, process.args, error)
    except FileNotFoundError:
        logging.error("'picomc' command not found")
        picomc = False
    
    if(picomc):
        logging.info("Picomc is installed")

    install_dependencies(pip, picomc)

                
if __name__ == '__main__':

    check_dependencies()

    app = QApplication(sys.argv)
    window = PicomcVersionSelector()
    ctypes.windll.user32.ShowWindow( ctypes.windll.kernel32.GetConsoleWindow(), 0 )
    window.show()

    sys.exit(app.exec_())
    
