# main.py
# Application entry point with a splash screen for a smooth startup.
# FIXED to prevent multiple Home windows and handle app termination properly.

import sys
import os
import time

# --- Dependency Checking ---
try:
    from PySide6.QtWidgets import QApplication, QSplashScreen, QMessageBox
    from PySide6.QtCore import Qt, QThread, Signal, QSettings, QDateTime
    from PySide6.QtGui import QPixmap, QPainter, QFont, QColor
except ImportError:
    # PySide6 is not installed. Let's check for PyQt5.
    try:
        import PyQt5 #type: ignore
        # If this import succeeds, it means the user has PyQt5.
        # We need to inform them to install PySide6.
        # We can't use QApplication from PySide6, so we'll use it from PyQt5
        # to show an error message.
        from PyQt5.QtWidgets import QApplication, QMessageBox #type: ignore
        app = QApplication(sys.argv)
        msg_box = QMessageBox()
        msg_box.setIcon(QMessageBox.Critical)
        msg_box.setText("Incorrect Library Detected")
        msg_box.setInformativeText(
            "This application requires PySide6, but it appears you have PyQt5 "
            "installed.\nPlease uninstall PyQt5 and install PySide6.\n\n"
            "You can do this by running:\n"
            "pip uninstall PyQt5\n"
            "pip install pyside6"
        )
        msg_box.setWindowTitle("Dependency Error")
        msg_box.exec_()
    except ImportError:
        # Neither PySide6 nor PyQt5 are installed.
        # We can't show a GUI message, so we'll print to the console.
        print("CRITICAL ERROR: PySide6 is not installed. Please install it by running: pip install pyside6")
    sys.exit(1)  # Exit the application


class CustomSplashScreen(QSplashScreen):
    """A custom splash screen to show loading messages."""
    def __init__(self, pixmap):
        super().__init__(pixmap)
        self.message = "Initializing..."
        self.setStyleSheet("QSplashScreen { border: 1px solid #555; }")

    def drawContents(self, painter):
        """Draw the pixmap and the custom message."""
        super().drawContents(painter)
        text_rect = self.rect().adjusted(10, 0, -10, -10)
        painter.setPen(QColor(220, 220, 220)) # Light gray text
        painter.drawText(text_rect, Qt.AlignBottom | Qt.AlignLeft, self.message)

    def showMessage(self, message, alignment=Qt.AlignLeft, color=Qt.white):
        """Override to repaint the splash screen with the new message."""
        self.message = message
        super().showMessage(message, alignment, color)
        self.repaint()
        QApplication.processEvents()


def get_relative_time(timestamp_str):
    """Calculates a human-readable relative time string from an ISO date string."""
    if not timestamp_str: return "Never opened"
    timestamp = QDateTime.fromString(timestamp_str, Qt.ISODate)
    seconds = timestamp.secsTo(QDateTime.currentDateTime())
    if seconds < 0: return timestamp.toString("MMM d, yyyy h:mm AP")
    if seconds < 60: return "Just now"
    minutes = seconds // 60
    if minutes < 60: return f"{minutes} minute{'s' if minutes > 1 else ''} ago"
    hours = seconds // 3600
    if hours < 24: return f"{hours} hour{'s' if hours > 1 else ''} ago"
    days = seconds // 86400
    if days < 7: return f"{days} day{'s' if days > 1 else ''} ago"
    weeks = seconds // 604800
    if weeks < 4: return f"{weeks} week{'s' if weeks > 1 else ''} ago"
    months = seconds // 2592000
    if months < 12: return f"{months} month{'s' if months > 1 else ''} ago"
    years = seconds // 31536000
    return f"{years} year{'s' if years > 1 else ''} ago"

class Preloader(QThread):
    """
    Performs initial, non-GUI tasks in a separate thread.
    This now includes loading the recent projects list.
    """
    finished = Signal(list)  # Signal will emit the list of loaded project data
    progress_update = Signal(str)

    def run(self):
        """The entry point for the thread."""
        self.progress_update.emit("Loading application settings...")
        time.sleep(0.3)
        
        # --- Actually preload the recent projects data ---
        self.progress_update.emit("Finding recent projects...")
        projects_data = []
        try:
            settings = QSettings("YourCompany", "MangaOCRTool")
            recent_projects = settings.value("recent_projects", [])
            recent_timestamps = settings.value("recent_timestamps", {})
            
            for path in recent_projects:
                if os.path.exists(path):
                    filename = os.path.basename(path)
                    timestamp = recent_timestamps.get(path, "")
                    last_opened = get_relative_time(timestamp)
                    projects_data.append({
                        "name": filename,
                        "path": path,
                        "last_opened": last_opened
                    })
            time.sleep(0.5) # Simulate work
        except Exception as e:
            print(f"Could not preload recent projects: {e}")
            # Continue with an empty list on error

        self.progress_update.emit("Preparing main interface...")
        time.sleep(0.4)

        self.progress_update.emit("Finalizing...")
        time.sleep(0.2)

        self.finished.emit(projects_data)


# --- Global variables to hold instances ---
splash = None
home_window = None

def on_preload_finished(projects_data):
    """
    This slot runs on the main thread. It creates the Home window instance,
    populates it with the preloaded data, and then decides whether to show
    it or immediately launch a project.
    """
    global home_window, splash
    print("[ENTRY] Preloading finished. Handling window creation.")

    # --- Import Home from the correct module ---
    from app.ui.window.home_window import Home
    
    # Only create Home window instance if it doesn't exist
    if home_window is None:
        home_window = Home()
        # --- Populate the home window with the preloaded data ---
        home_window.populate_recent_projects(projects_data)
        print("[ENTRY] Home window instance created and populated.")

    # Check for a project file in command-line arguments.
    project_to_open = None
    if len(sys.argv) > 1 and sys.argv[1].lower().endswith('.mmtl'):
        path = sys.argv[1]
        if os.path.exists(path):
            project_to_open = path
        else:
            # We need a parent for the message box. The invisible home_window is perfect.
            QMessageBox.critical(home_window, "Error", f"The project file could not be found:\n{path}")

    # --- THIS IS THE IMPROVED LOGIC ---
    if project_to_open:
        print("[ENTRY] Project file provided. Skipping Home window.")
        # Immediately close the splash screen. We use .close() instead of .finish()
        # because we are not transferring control to a visible main window yet.
        splash.close()

        # Now, call the method that creates and shows the LoadingDialog.
        # Because the dialog is modal (exec_()), this call will block until
        # the project is loaded or fails, preventing the script from exiting early.
        home_window.launch_main_app(project_to_open)
    else:
        print("[ENTRY] No project file. Showing Home window.")
        # Show the fully prepared Home window.
        home_window.show()

        # Gracefully close the splash screen, transferring focus to the Home window.
        splash.finish(home_window)

    print("[ENTRY] Initial launch sequence complete.")


if __name__ == '__main__':
    # The dependency check is now at the top of the file, so if we get here,
    # we can assume PySide6 is installed.
    app = QApplication(sys.argv)
    
    # Check if application is already running (optional)
    app.setApplicationName("ManhwaOCR")
    app.setApplicationVersion("1.0")

    # --- Create and configure the splash screen pixmap ---
    pixmap = QPixmap(500, 250)
    pixmap.fill(QColor(45, 45, 45))
    painter = QPainter(pixmap)
    painter.setPen(QColor(220, 220, 220))
    font = QFont("Segoe UI", 24, QFont.Bold)
    painter.setFont(font)
    painter.drawText(pixmap.rect().adjusted(0, -20, 0, -20), Qt.AlignCenter, "ManhwaOCR")
    painter.end()

    # --- Show splash and start preloader ---
    splash = CustomSplashScreen(pixmap)
    splash.show()

    preloader = Preloader()
    preloader.progress_update.connect(splash.showMessage)
    preloader.finished.connect(on_preload_finished)
    preloader.start()

    sys.exit(app.exec())