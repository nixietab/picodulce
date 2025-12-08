import sys
import threading
import time
import shlex
import gc
import re
from io import StringIO
from PyQt5.QtWidgets import QDialog, QVBoxLayout, QLabel, QProgressBar, QPushButton, QHBoxLayout
from PyQt5.QtCore import Qt, pyqtSignal, QObject, QTimer, QEvent
from PyQt5.QtGui import QFont


class LaunchSignals(QObject):
    log_update = pyqtSignal(str)
    launch_complete = pyqtSignal()
    launch_aborted = pyqtSignal()
    cleanup_done = pyqtSignal()


class AbortException(Exception):
    pass


class StreamingCapture(StringIO):
    def __init__(self, log_signal, launch_signal):
        super().__init__()
        self.log_signal = log_signal
        self.launch_signal = launch_signal
        self.launch_detected = False
        self.abort_requested = False
    
    def write(self, text):
        if self.abort_requested:
            raise AbortException("Launch aborted by user")

        if text and text.strip():
            # Check if signal is still valid before emitting
            try:
                self.log_signal.emit(text.strip())
            except RuntimeError:
                # Signal/Object might be deleted
                pass
            
            if not self.launch_detected and self.launch_signal:
                lower_text = text.lower()
                if "launching" in lower_text and ("game" in lower_text or "version" in lower_text or "minecraft" in lower_text):
                    self.launch_detected = True
                    try:
                        self.launch_signal.emit()
                    except RuntimeError:
                        pass
        
        return super().write(text)


class LaunchWindow(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Launching Minecraft")
        self.setModal(True)
        self.resize(400, 150)
        
        layout = QVBoxLayout()
        
        self.status_label = QLabel("Initializing...")
        self.status_label.setWordWrap(True)
        self.status_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.status_label)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)  # Indeterminate progress
        self.progress_bar.setTextVisible(False)
        layout.addWidget(self.progress_bar)
        
        # Add a manual close/cancel button
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.request_abort)
        button_layout.addWidget(self.cancel_button)
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
        
        self.signals = LaunchSignals()
        self.signals.log_update.connect(self.update_status)
        self.signals.launch_complete.connect(self.on_launch_complete)
        self.signals.launch_aborted.connect(self.on_launch_aborted)
        self.signals.cleanup_done.connect(self.on_cleanup_done)
        
        self.launch_detected = False
        self.closing_scheduled = False
        self.aborting = False
        self.capture_streams = []
        self.thread_running = False
    
    def update_status(self, text):
        if len(text) > 100:
            text = text[:97] + "..."
        self.status_label.setText(text)
    
    def on_launch_complete(self):
        if not self.closing_scheduled and not self.aborting:
            self.closing_scheduled = True
            self.status_label.setText("Game Launched! Closing window...")
            self.progress_bar.setRange(0, 100)
            self.progress_bar.setValue(100)
            self.cancel_button.setEnabled(False)
            QTimer.singleShot(3000, self.accept)
    
    def on_launch_aborted(self):
        self.status_label.setText("Launch Aborted.")
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
    
    def on_cleanup_done(self):
        self.thread_running = False
        # Now it is safe to close the window
        super().reject()

    def request_abort(self):
        if self.thread_running and not self.aborting:
            self.aborting = True
            self.status_label.setText("Aborting...")
            self.cancel_button.setEnabled(False)
            # Signal streams to stop
            for stream in self.capture_streams:
                stream.abort_requested = True
        elif not self.thread_running:
            super().reject()

    def reject(self):
        # Handle Esc key or X button
        self.request_abort()
    
    def closeEvent(self, event):
        if self.thread_running:
            event.ignore()
            self.request_abort()
        else:
            event.accept()

    def launch_game(self, command):
        self.thread_running = True
        thread = threading.Thread(target=self._run_launch, args=(command,), daemon=True)
        thread.start()
    
    def _run_launch(self, command):
        try:
            modules_to_remove = [mod for mod in sys.modules if mod.startswith('zucaro')]
            for mod in modules_to_remove:
                del sys.modules[mod]
            gc.collect()

            from zucaro.cli.main import zucaro_cli
            
            old_stdout, old_stderr = sys.stdout, sys.stderr
            
            stdout_capture = StreamingCapture(self.signals.log_update, self.signals.launch_complete)
            stderr_capture = StreamingCapture(self.signals.log_update, self.signals.launch_complete)
            
            self.capture_streams = [stdout_capture, stderr_capture]
            
            sys.stdout = stdout_capture
            sys.stderr = stderr_capture
            
            try:
                zucaro_cli.main(args=shlex.split(command), standalone_mode=False)
            except AbortException:
                self.signals.launch_aborted.emit()
            except SystemExit:
                pass
            except Exception as e:
                self.signals.log_update.emit(f"Error: {str(e)}")
            finally:
                sys.stdout = old_stdout
                sys.stderr = old_stderr
                
                if not stdout_capture.launch_detected and not stderr_capture.launch_detected and not stdout_capture.abort_requested:
                     self.signals.launch_complete.emit()

                modules_to_remove = [mod for mod in sys.modules if mod.startswith('zucaro')]
                for mod in modules_to_remove:
                    del sys.modules[mod]
                gc.collect()
                
                self.signals.cleanup_done.emit()
        
        except Exception as e:
            try:
                self.signals.log_update.emit(f"Error launching game: {str(e)}")
                self.signals.cleanup_done.emit()
            except:
                pass


class PrepareWindow(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Preparing Version")
        self.setModal(True)
        self.resize(400, 150)
        
        layout = QVBoxLayout()
        
        self.status_label = QLabel("Initializing...")
        self.status_label.setWordWrap(True)
        self.status_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.status_label)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)  # Indeterminate progress
        self.progress_bar.setTextVisible(False)
        layout.addWidget(self.progress_bar)
        
        # Add a manual close/cancel button
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.request_abort)
        button_layout.addWidget(self.cancel_button)
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
        
        self.signals = LaunchSignals()
        self.signals.log_update.connect(self.update_status)
        self.signals.launch_complete.connect(self.on_prepare_complete)
        self.signals.launch_aborted.connect(self.on_prepare_aborted)
        self.signals.cleanup_done.connect(self.on_cleanup_done)
        
        self.aborting = False
        self.capture_streams = []
        self.thread_running = False
        self.success = False

    def update_status(self, text):
        # Parse output for progress updates
        
        if "Downloading" in text and "libraries" in text:
             try:
                 count = int(re.search(r'\d+', text).group())
                 self.status_label.setText(f"Downloading {count} libraries...")
             except:
                 self.status_label.setText(text)
        elif "Checking" in text and "assets" in text:
             try:
                 count = int(re.search(r'\d+', text).group())
                 self.status_label.setText(f"Checking {count} assets...")
             except:
                 self.status_label.setText(text)
        elif "Jar file" in text and "downloaded" in text:
            self.status_label.setText("Downloading game jar...")
        elif "Checking libraries" in text:
            self.status_label.setText("Checking libraries...")
        else:
            if len(text) > 100:
                text = text[:97] + "..."
            self.status_label.setText(text)

    def on_prepare_complete(self):
        if not self.aborting:
            self.success = True
            self.status_label.setText("Version prepared successfully!")
            self.progress_bar.setRange(0, 100)
            self.progress_bar.setValue(100)
            self.cancel_button.setEnabled(False)
            QTimer.singleShot(1500, self.accept)

    def on_prepare_aborted(self):
        self.status_label.setText("Preparation Aborted.")
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.success = False

    def on_cleanup_done(self):
        self.thread_running = False
        if not self.success:
             super().reject()

    def request_abort(self):
        if self.thread_running and not self.aborting:
            self.aborting = True
            self.status_label.setText("Aborting...")
            self.cancel_button.setEnabled(False)
            # Signal streams to stop
            for stream in self.capture_streams:
                stream.abort_requested = True
        elif not self.thread_running:
            super().reject()

    def reject(self):
        self.request_abort()
    
    def closeEvent(self, event):
        if self.thread_running:
            event.ignore()
            self.request_abort()
        else:
            event.accept()

    def prepare_version(self, version):
        command = f"version prepare {version}"
        self.thread_running = True
        thread = threading.Thread(target=self._run_prepare, args=(command,), daemon=True)
        thread.start()

    def _run_prepare(self, command):
        try:
            modules_to_remove = [mod for mod in sys.modules if mod.startswith('zucaro')]
            for mod in modules_to_remove:
                del sys.modules[mod]
            gc.collect()

            from zucaro.cli.main import zucaro_cli
            
            old_stdout, old_stderr = sys.stdout, sys.stderr
            
            stdout_capture = StreamingCapture(self.signals.log_update, None)
            stderr_capture = StreamingCapture(self.signals.log_update, None)
            
            self.capture_streams = [stdout_capture, stderr_capture]
            
            sys.stdout = stdout_capture
            sys.stderr = stderr_capture
            
            try:
                zucaro_cli.main(args=shlex.split(command), standalone_mode=False)
            except AbortException:
                self.signals.launch_aborted.emit()
            except SystemExit:
                pass
            except Exception as e:
                self.signals.log_update.emit(f"Error: {str(e)}")
            finally:
                sys.stdout = old_stdout
                sys.stderr = old_stderr
                
                if not stdout_capture.abort_requested:
                     self.signals.launch_complete.emit()

                modules_to_remove = [mod for mod in sys.modules if mod.startswith('zucaro')]
                for mod in modules_to_remove:
                    del sys.modules[mod]
                gc.collect()
                
                self.signals.cleanup_done.emit()
        
        except Exception as e:
            try:
                self.signals.log_update.emit(f"Error preparing version: {str(e)}")
                self.signals.cleanup_done.emit()
            except:
                pass


def launch_instance_with_window(command, parent=None):
    window = LaunchWindow(parent)
    window.launch_game(command)
    window.exec_()
    return window

def prepare_version_with_window(version, parent=None):
    window = PrepareWindow(parent)
    window.prepare_version(version)
    result = window.exec_()
    return window.success
