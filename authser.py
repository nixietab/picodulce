import sys
import json
import os
import uuid
import asyncio
import aiohttp
from datetime import datetime, timezone
from pathlib import Path
from PyQt5.QtWidgets import (QApplication, QDialog, QLabel, QVBoxLayout, 
                           QPushButton, QLineEdit, QMessageBox)
from PyQt5.QtCore import QThread, pyqtSignal, Qt, QUrl, QObject
from PyQt5.QtGui import QDesktopServices
from zucaro.logging import logger
from zucaro.launcher import get_default_root, Launcher

# Constants for Microsoft Authentication
URL_DEVICE_AUTH = "https://login.microsoftonline.com/consumers/oauth2/v2.0/devicecode"
URL_TOKEN = "https://login.microsoftonline.com/consumers/oauth2/v2.0/token"
URL_XBL = "https://user.auth.xboxlive.com/user/authenticate"
URL_XSTS = "https://xsts.auth.xboxlive.com/xsts/authorize"
URL_MC = "https://api.minecraftservices.com/authentication/login_with_xbox"
URL_PROFILE = "https://api.minecraftservices.com/minecraft/profile"

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
    access_token_received = pyqtSignal(dict)
    
    def __init__(self, username):
        super().__init__()
        self.username = username
        self.device_code = None
        self.is_running = True

    async def _ms_oauth(self):
        data = {"client_id": CLIENT_ID, "scope": SCOPE}
        
        async with aiohttp.ClientSession() as session:
            async with session.post(URL_DEVICE_AUTH, data=data) as resp:
                if resp.status != 200:
                    raise Exception(f"Failed to get device code: {await resp.text()}")
                j = await resp.json()
                self.device_code = j["device_code"]
                self.auth_data_received.emit({
                    'url': j["verification_uri"],
                    'code': j["user_code"]
                })

            while self.is_running:
                data = {
                    "grant_type": GRANT_TYPE,
                    "client_id": CLIENT_ID,
                    "device_code": self.device_code
                }
                
                async with session.post(URL_TOKEN, data=data) as resp:
                    j = await resp.json()
                    if resp.status == 400:
                        if j["error"] == "authorization_pending":
                            await asyncio.sleep(2)
                            continue
                        else:
                            raise Exception(j["error_description"])
                    elif resp.status != 200:
                        raise Exception(f"Token request failed: {j}")

                    return j["access_token"], j["refresh_token"]

    async def _xbl_auth(self, access_token):
        data = {
            "Properties": {
                "AuthMethod": "RPS",
                "SiteName": "user.auth.xboxlive.com",
                "RpsTicket": f"d={access_token}"
            },
            "RelyingParty": "http://auth.xboxlive.com",
            "TokenType": "JWT"
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(URL_XBL, json=data) as resp:
                if resp.status != 200:
                    raise Exception(f"XBL auth failed: {await resp.text()}")
                j = await resp.json()
                return j["Token"], j["DisplayClaims"]["xui"][0]["uhs"]

    async def _xsts_auth(self, xbl_token):
        data = {
            "Properties": {
                "SandboxId": "RETAIL",
                "UserTokens": [xbl_token]
            },
            "RelyingParty": "rp://api.minecraftservices.com/",
            "TokenType": "JWT"
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(URL_XSTS, json=data) as resp:
                if resp.status != 200:
                    raise Exception(f"XSTS auth failed: {await resp.text()}")
                j = await resp.json()
                return j["Token"]

    async def _mc_auth(self, uhs, xsts_token):
        data = {
            "identityToken": f"XBL3.0 x={uhs};{xsts_token}"
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(URL_MC, json=data) as resp:
                if resp.status != 200:
                    raise Exception(f"MC auth failed: {await resp.text()}")
                j = await resp.json()
                return j["access_token"]

    async def _get_profile(self, mc_token):
        headers = {
            "Authorization": f"Bearer {mc_token}"
        }

        async with aiohttp.ClientSession() as session:
            async with session.get(URL_PROFILE, headers=headers) as resp:
                if resp.status != 200:
                    raise Exception(f"Profile request failed: {await resp.text()}")
                return await resp.json()

    async def _auth_flow(self):
        try:
            ms_access_token, refresh_token = await self._ms_oauth()
            xbl_token, uhs = await self._xbl_auth(ms_access_token)
            xsts_token = await self._xsts_auth(xbl_token)
            mc_token = await self._mc_auth(uhs, xsts_token)
            profile = await self._get_profile(mc_token)

            self.access_token_received.emit({
                'access_token': mc_token,
                'refresh_token': refresh_token,
                'profile': profile
            })

        except Exception as e:
            self.error_occurred.emit(str(e))

    def run(self):
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(self._auth_flow())
        except Exception as e:
            self.error_occurred.emit(str(e))
        finally:
            self.finished.emit()

    def stop(self):
        self.is_running = False

class MinecraftAuthenticator(QObject):
    auth_finished = pyqtSignal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.auth_thread = None
        self.auth_dialog = None
        self.success = False
        self.username = None
        
        # Initialize the launcher to get the correct config path
        with Launcher.new() as launcher:
            self.config_path = launcher.root

    def authenticate(self, username):
        self.username = username
        self.success = False

        # Create accounts.json if it doesn't exist
        if not self.save_to_accounts_json():
            return

        self.auth_thread = AuthenticationThread(username)
        self.auth_thread.auth_data_received.connect(self.show_auth_dialog)
        self.auth_thread.error_occurred.connect(self.show_error)
        self.auth_thread.access_token_received.connect(self.on_access_token_received)
        self.auth_thread.finished.connect(self.on_authentication_finished)
        self.auth_thread.start()

    def show_auth_dialog(self, auth_data):
        if self.auth_dialog is not None:
            self.auth_dialog.close()
            
        self.auth_dialog = AuthDialog(auth_data['url'], auth_data['code'])
        
        result = self.auth_dialog.exec_()
        
        if result != QDialog.Accepted:
            self.auth_thread.stop()

    def show_error(self, error_msg):
        QMessageBox.critical(None, "Error", error_msg)
        self.success = False
        self.auth_finished.emit(False)

    def save_to_accounts_json(self):
        try:
            accounts_file = Path(self.config_path) / "accounts.json"
            
            if accounts_file.exists():
                with open(accounts_file) as f:
                    config = json.load(f)
            else:
                config = {
                    "default": None,
                    "accounts": {},
                    "client_token": str(uuid.uuid4())
                }
                accounts_file.parent.mkdir(parents=True, exist_ok=True)
            
            # Only create/update if account doesn't exist
            if self.username not in config["accounts"]:
                config["accounts"][self.username] = {
                    "uuid": "-",
                    "online": True,
                    "microsoft": True,
                    "gname": "-",
                    "access_token": "-",
                    "refresh_token": "-",
                    "is_authenticated": False
                }
                
                # Set as default if no default exists
                if config["default"] is None:
                    config["default"] = self.username
                
                with open(accounts_file, 'w') as f:
                    json.dump(config, f, indent=4)
                    
            return True

        except Exception as e:
            logger.error(f"Failed to initialize account data: {str(e)}")
            QMessageBox.critical(None, "Error", f"Failed to initialize account data: {str(e)}")
            return False

    def on_access_token_received(self, data):
        try:
            accounts_file = Path(self.config_path) / "accounts.json"
            
            with open(accounts_file) as f:
                config = json.load(f)
            
            if self.username in config["accounts"]:
                config["accounts"][self.username].update({
                    "access_token": data['access_token'],
                    "refresh_token": data['refresh_token'],
                    "uuid": data['profile']['id'],
                    "gname": data['profile']['name'],
                    "is_authenticated": True
                })
                
                with open(accounts_file, 'w') as f:
                    json.dump(config, f, indent=4)
                
                self.success = True
                QMessageBox.information(None, "Success", 
                                      f"Successfully authenticated account: {self.username}")
            else:
                raise Exception("Account not found in configuration")
                
        except Exception as e:
            logger.error(f"Failed to update account data: {str(e)}")
            QMessageBox.critical(None, "Error", f"Failed to update account data: {str(e)}")
            self.success = False
            
        self.auth_finished.emit(self.success)

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

def create_authenticator():
    """Factory function to create a new MinecraftAuthenticator instance"""
    return MinecraftAuthenticator()
