import sys
import re
import colorama
import requests
from PyQt5.QtWidgets import (QApplication, QDialog, QLabel, QVBoxLayout, 
                          QPushButton, QLineEdit, QMessageBox)
from PyQt5.QtCore import QThread, pyqtSignal, Qt, QUrl, QObject, QTimer
from PyQt5.QtGui import QDesktopServices
from picomc.logging import logger

# Constants
URL_DEVICE_AUTH = "https://login.microsoftonline.com/consumers/oauth2/v2.0/devicecode"
URL_TOKEN = "https://login.microsoftonline.com/consumers/oauth2/v2.0/token"
CLIENT_ID = "c52aed44-3b4d-4215-99c5-824033d2bc0f"
SCOPE = "XboxLive.signin offline_access"
GRANT_TYPE = "urn:ietf:params:oauth:grant-type:device_code"

class AuthDialog(QDialog):
    def __init__(self, url, code, parent=None, error_mode=False):
        super().__init__(parent)
        self.setWindowTitle("Microsoft Authentication")
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        self.setModal(True)
        self.setup_ui(url, code, error_mode)

    def setup_ui(self, url, code, error_mode):
        layout = QVBoxLayout(self)
        
        if error_mode:
            error_label = QLabel("Error in Login - Please try again")
            error_label.setStyleSheet("QLabel { color: red; font-weight: bold; }")
            layout.addWidget(error_label)

        instructions = QLabel(
            "To authenticate your Microsoft Account:\n\n"
            "1. Click 'Open Authentication Page' or visit:\n"
            "2. Copy the code below\n"
            "3. Paste the code on the Microsoft website\n"
            "4. After completing authentication, click 'I've Completed Authentication'"
        )
        instructions.setWordWrap(True)
        layout.addWidget(instructions)

        url_label = QLabel(url)
        url_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        url_label.setWordWrap(True)
        layout.addWidget(url_label)
        
        self.code_input = QLineEdit(code)
        self.code_input.setReadOnly(True)
        self.code_input.setAlignment(Qt.AlignCenter)
        self.code_input.setStyleSheet("""
            QLineEdit {
                font-size: 16pt;
                font-weight: bold;
                padding: 5px;
            }
        """)
        layout.addWidget(self.code_input)
        
        copy_button = QPushButton("Copy Code")
        copy_button.clicked.connect(self.copy_code)
        layout.addWidget(copy_button)
        
        open_url_button = QPushButton("Open Authentication Page")
        open_url_button.clicked.connect(lambda: self.open_url(url))
        layout.addWidget(open_url_button)
        
        continue_button = QPushButton("I've Completed Authentication")
        continue_button.clicked.connect(self.accept)
        layout.addWidget(continue_button)

    def copy_code(self):
        clipboard = QApplication.clipboard()
        clipboard.setText(self.code_input.text())

    def open_url(self, url):
        QDesktopServices.openUrl(QUrl(url))

class AuthenticationThread(QThread):
    auth_data_received = pyqtSignal(dict)
    error_occurred = pyqtSignal(str)
    auth_error_detected = pyqtSignal(str)
    finished = pyqtSignal()
    access_token_received = pyqtSignal(str, str)
    
    def __init__(self, account):
        super().__init__()
        self.account = account
        self.device_code = None
        self.is_running = True

    def run(self):
        try:
            self.authenticate(self.account)
        except Exception as e:
            self.error_occurred.emit(str(e))
            self.finished.emit()

    def authenticate(self, account):
        try:
            data = {"client_id": CLIENT_ID, "scope": SCOPE}

            # Request device code
            resp = requests.post(URL_DEVICE_AUTH, data)
            resp.raise_for_status()

            j = resp.json()
            self.device_code = j["device_code"]
            user_code = j["user_code"]
            link = j["verification_uri"]

            # Format message with colorama
            msg = j["message"]
            msg = msg.replace(
                user_code, colorama.Fore.RED + user_code + colorama.Fore.RESET
            ).replace(link, colorama.Style.BRIGHT + link + colorama.Style.NORMAL)

            # Emit auth data received signal
            self.auth_data_received.emit({'url': link, 'code': user_code})

        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed: {e}")
            self.error_occurred.emit(str(e))
            self.finished.emit()
    
    def poll_for_token(self):
        try:
            data = {"code": self.device_code, "grant_type": GRANT_TYPE, "client_id": CLIENT_ID}
            resp = requests.post(URL_TOKEN, data)
            if resp.status_code == 400:
                j = resp.json()
                logger.debug(j)
                if j["error"] == "authorization_pending":
                    logger.warning(j["error_description"])
                    self.auth_error_detected.emit(j["error_description"])
                    return
                else:
                    raise Exception(j["error_description"])
            resp.raise_for_status()
            j = resp.json()
            access_token = j["access_token"]
            refresh_token = j["refresh_token"]
            logger.debug("OAuth device code flow successful")
            self.access_token_received.emit(access_token, refresh_token)
            self.finished.emit()
        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed: {e}")
            self.error_occurred.emit(str(e))
            self.finished.emit()
    
    def send_enter(self):
        self.poll_for_token()

    def stop(self):
        self.is_running = False

class MinecraftAuthenticator(QObject):
    auth_finished = pyqtSignal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.auth_thread = None
        self.current_auth_data = None
        self.auth_dialog = None
        self.success = False
        
    def authenticate(self, username):
        self.success = False
        self.auth_thread = AuthenticationThread(username)
        self.auth_thread.auth_data_received.connect(self.show_auth_dialog)
        self.auth_thread.auth_error_detected.connect(self.handle_auth_error)
        self.auth_thread.error_occurred.connect(self.show_error)
        self.auth_thread.access_token_received.connect(self.on_access_token_received)
        self.auth_thread.finished.connect(self.on_authentication_finished)
        self.auth_thread.start()

    def show_auth_dialog(self, auth_data):
        self.current_auth_data = auth_data
        
        if self.auth_dialog is not None:
            self.auth_dialog.close()
            self.auth_dialog = None
        
        self.auth_dialog = AuthDialog(auth_data['url'], auth_data['code'])
        if self.auth_dialog.exec_() == QDialog.Accepted:
            self.auth_thread.send_enter()

    def handle_auth_error(self, output):
        if self.current_auth_data:
            if self.auth_dialog is not None:
                self.auth_dialog.close()
                self.auth_dialog = None
            
            self.auth_dialog = AuthDialog(
                self.current_auth_data['url'],
                self.current_auth_data['code'],
                error_mode=True
            )
            if self.auth_dialog.exec_() == QDialog.Accepted:
                self.auth_thread.send_enter()

    def show_error(self, error_message):
        QMessageBox.critical(None, "Error", f"Authentication error: {error_message}")
        self.success = False
        self.auth_finished.emit(False)

    def on_access_token_received(self, access_token, refresh_token):
        QMessageBox.information(None, "Success", "Authentication successful!")
        self.success = True
        self.auth_finished.emit(True)

    def on_authentication_finished(self):
        if self.auth_dialog is not None:
            self.auth_dialog.close()
            self.auth_dialog = None
            
        if self.auth_thread:
            self.auth_thread.stop()
            self.auth_thread = None
            
        if not self.success:
            self.auth_finished.emit(False)

    def cleanup(self):
        if self.auth_dialog is not None:
            self.auth_dialog.close()
            self.auth_dialog = None
            
        if self.auth_thread and self.auth_thread.isRunning():
            self.auth_thread.stop()
            self.auth_thread.wait()

# Example usage
if __name__ == '__main__':
    app = QApplication(sys.argv)
    authenticator = MinecraftAuthenticator()
    authenticator.authenticate("TestUser")
    sys.exit(app.exec_())
