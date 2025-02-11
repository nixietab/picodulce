import sys
import subprocess
import re
from PyQt5.QtWidgets import (QApplication, QDialog, QLabel, QVBoxLayout, 
                          QPushButton, QLineEdit, QMessageBox)
from PyQt5.QtCore import QThread, pyqtSignal, Qt, QUrl, QObject
from PyQt5.QtGui import QDesktopServices

class AuthenticationParser:
    @staticmethod
    def clean_ansi(text):
        ansi_clean = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
        printable_clean = re.compile(r'[^\x20-\x7E\n]')
        text = ansi_clean.sub('', text)
        text = printable_clean.sub('', text)
        return text.strip()

    @staticmethod
    def is_auth_error(output):
        cleaned_output = AuthenticationParser.clean_ansi(output)
        return "AADSTS70016" in cleaned_output and "not yet been authorized" in cleaned_output

    @staticmethod
    def parse_auth_output(output):
        cleaned_output = AuthenticationParser.clean_ansi(output)
        if AuthenticationParser.is_auth_error(cleaned_output):
            return None

        pattern = r"https://[^\s]+"
        code_pattern = r"code\s+([A-Z0-9]+)"
        
        url_match = re.search(pattern, cleaned_output)
        code_match = re.search(code_pattern, cleaned_output, re.IGNORECASE)
        
        if url_match and code_match:
            return {
                'url': url_match.group(0),
                'code': code_match.group(1)
            }
        return None

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
    
    def __init__(self, account):
        super().__init__()
        self.account = account
        self.process = None
        self.is_running = True
        self.current_output = ""
        self.waiting_for_auth = False

    def run(self):
        try:
            command = f'picomc account authenticate {self.account}'
            
            self.process = subprocess.Popen(
                command,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                stdin=subprocess.PIPE,
                text=True,
                bufsize=1,
                universal_newlines=True
            )
            
            self.current_output = ""
            while self.is_running and self.process.poll() is None:
                line = self.process.stdout.readline()
                if line:
                    self.current_output += line
                    
                    if not self.waiting_for_auth:
                        parsed_data = AuthenticationParser.parse_auth_output(self.current_output)
                        if parsed_data:
                            self.auth_data_received.emit(parsed_data)
                            self.waiting_for_auth = True
                            self.current_output = ""
                    elif AuthenticationParser.is_auth_error(self.current_output):
                        self.auth_error_detected.emit(self.current_output)
                        self.waiting_for_auth = False
                        self.current_output = ""
            
            self.process.wait()
            self.finished.emit()
            
        except Exception as e:
            self.error_occurred.emit(str(e))
            self.finished.emit()

    def send_enter(self):
        if self.process and self.process.poll() is None:
            self.process.stdin.write("\n")
            self.process.stdin.flush()

    def stop(self):
        self.is_running = False
        if self.process:
            self.process.terminate()

class MinecraftAuthenticator(QObject):  # Changed to inherit from QObject
    auth_finished = pyqtSignal(bool)  # Add signal for completion

    def __init__(self, parent=None):
        super().__init__(parent)
        self.auth_thread = None
        self.current_auth_data = None
        self.auth_dialog = None
        self.success = False
        
    def authenticate(self, username):
        """
        Start the authentication process for the given username
        Returns immediately, authentication result will be emitted via auth_finished signal
        """
        self.success = False
        self.auth_thread = AuthenticationThread(username)
        self.auth_thread.auth_data_received.connect(self.show_auth_dialog)
        self.auth_thread.auth_error_detected.connect(self.handle_auth_error)
        self.auth_thread.error_occurred.connect(self.show_error)
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

    def on_authentication_finished(self):
        if self.auth_dialog is not None:
            self.auth_dialog.close()
            self.auth_dialog = None
            
        if self.auth_thread:
            self.auth_thread.stop()
            self.auth_thread = None
            
        self.success = True
        self.auth_finished.emit(True)

    def cleanup(self):
        if self.auth_dialog is not None:
            self.auth_dialog.close()
            self.auth_dialog = None
            
        if self.auth_thread and self.auth_thread.isRunning():
            self.auth_thread.stop()
            self.auth_thread.wait()

# Example usage
if __name__ == '__main__':
    authenticator = MinecraftAuthenticator()
    authenticator.authenticate("TestUser")
