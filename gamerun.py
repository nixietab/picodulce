import sys
import subprocess
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QVBoxLayout, 
    QWidget, QPushButton, QDialog, QLabel,
    QProgressBar
)
from PyQt5.QtCore import QThread, pyqtSignal, Qt, QObject


class LaunchDialog(QDialog):
    """Dialog displayed during the game launch process."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Launching Game")
        self.setFixedSize(400, 100)
        
        # Remove context help button
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        
        # Layout and widgets for status and progress
        layout = QVBoxLayout()
        self.status_label = QLabel("Starting game launcher...")
        self.status_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.status_label)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)  # Indeterminate progress bar, going to change this latter
        layout.addWidget(self.progress_bar)
        
        self.setLayout(layout)


class PicomcThread(QThread):
    """Thread that handles launching the game and reading output."""
    
    # Signals to notify parent on various events
    output_received = pyqtSignal(str)
    game_launched = pyqtSignal()
    error_occurred = pyqtSignal(str, str)

    def __init__(self, cmd):
        super().__init__()
        self.cmd = cmd  # Command to run
        self.process = None  # Process reference
        self.stop_parsing = False  # Flag to stop output parsing

    def run(self):
        """Executes the game launch command and processes its output."""
        try:
            # Start the process with subprocess
            cmd_str = ' '.join(self.cmd)
            self.process = subprocess.Popen(
                cmd_str,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                bufsize=1,
                universal_newlines=True
            )

            # Parse the output until the game is launched
            while True:
                output = self.process.stdout.readline()
                if not output and self.process.poll() is not None:
                    break  # Process finished

                if output:
                    line = output.strip()
                    if line:
                        self.output_received.emit(line)

                        if line == "INFO Launching the game":
                            self.game_launched.emit()  # Notify that the game is launching
                            break  # Stop parsing

            # Print all remaining logs after the game has started
            print("\n[INFO] Game has launched! Showing live logs...\n")
            while True:
                output = self.process.stdout.readline()
                if not output and self.process.poll() is not None:
                    break  # Process finished

                if output:
                    print(output.strip())  # Display logs in the terminal

        except Exception as e:
            self.error_occurred.emit("Error", f"Error launching game: {str(e)}")


class MinecraftLauncher(QObject):
    """Handles the Minecraft game launcher, dialog creation, and error handling."""
    
    # Signals for dialog and status updates
    create_dialog_signal = pyqtSignal()
    close_dialog_signal = pyqtSignal()
    update_status_signal = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.parent_widget = None  # Parent widget reference
        self.launch_dialog = None  # Launch dialog instance
        self.picomc_thread = None  # Thread instance for game launch

        # Connect signals to internal methods
        self.create_dialog_signal.connect(self._create_dialog)
        self.close_dialog_signal.connect(self._close_dialog)
        self.update_status_signal.connect(self._update_status)

    def set_parent_widget(self, parent):
        """Set the parent widget for the launcher."""
        self.parent_widget = parent

    def launch_game(self, cmd):
        """Launches the game by running the picomc command."""
        try:
            print("[INFO] Creating popup...")
            self.create_dialog_signal.emit()  # Show the launch dialog

            print("[INFO] Starting picomc thread...")
            self.picomc_thread = PicomcThread(cmd)
            self.picomc_thread.output_received.connect(self._handle_output)
            self.picomc_thread.game_launched.connect(self._stop_parsing_and_close_popup)
            self.picomc_thread.error_occurred.connect(self.handle_error)
            self.picomc_thread.start()  # Start the thread

        except Exception as e:
            error_message = f"Error initializing launcher: {str(e)}"
            print(f"[ERROR] {error_message}")
            if self.parent_widget and hasattr(self.parent_widget, "showError"):
                self.parent_widget.showError("Error", error_message)

    def _handle_output(self, text):
        """Handles output from the picomc thread and updates the UI."""
        if self.picomc_thread and self.picomc_thread.stop_parsing:
            return  # Stop if parsing is stopped

        print(f"[PICOMC] {text}")
        self.update_status_signal.emit(text)  # Update status label

    def _stop_parsing_and_close_popup(self):
        """Stops parsing and closes the popup dialog."""
        print("[INFO] Stopping parsing, closing popup.")
        if self.picomc_thread:
            self.picomc_thread.stop_parsing = True
        self.close_dialog_signal.emit()  # Close the dialog

    def _create_dialog(self):
        """Creates and shows the launch dialog."""
        if self.launch_dialog is None:
            print("[INFO] Creating launch dialog...")
            self.launch_dialog = LaunchDialog(self.parent_widget)
            self.launch_dialog.show()

    def _close_dialog(self):
        """Closes the launch dialog."""
        if self.launch_dialog:
            print("[INFO] Closing dialog...")
            self.launch_dialog.close()
            self.launch_dialog = None
            print("[INFO] Dialog closed.")

    def _update_status(self, text):
        """Updates the status label in the launch dialog."""
        if self.launch_dialog and self.launch_dialog.isVisible():
            print(f"[INFO] Updating status: {text}")
            self.launch_dialog.status_label.setText(text)

    def handle_error(self, title, message):
        """Handles any error that occurs during the game launch."""
        print(f"[ERROR] {title} - {message}")
        if self.parent_widget and hasattr(self.parent_widget, "showError"):
            self.parent_widget.showError(title, message)
        self.close_dialog_signal.emit()  # Close the dialog on error