# main.py
# Application entry point with a splash screen for a smooth startup.
# CORRECTED to handle command-line arguments more gracefully.

import sys
import os
import time

# --- 1. Bare minimum imports for initial launch ---
from PySide6.QtWidgets import QApplication, QSplashScreen, QMessageBox
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QPixmap, QPainter, QFont, QColor


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


class Preloader(QThread):
    """
    Performs initial, non-GUI tasks in a separate thread.
    """
    finished = Signal()
    progress_update = Signal(str)

    def run(self):
        """The entry point for the thread."""
        self.progress_update.emit("Loading application assets...")
        time.sleep(0.5)

        self.progress_update.emit("Preparing main interface...")
        time.sleep(0.8)

        self.progress_update.emit("Finalizing...")
        time.sleep(0.1)

        self.finished.emit()


# --- Global variables to hold instances ---
splash = None
home_window = None

def on_preload_finished():
    """
    This slot runs on the main thread. It creates the Home window instance
    and then decides whether to show it or immediately launch a project.
    """
    global home_window, splash
    print("[ENTRY] Preloading finished. Handling window creation.")

    # --- Defer import and creation to this point ---
    from app.ui.window import Home
    # Always create the Home window instance in the background.
    # It acts as our application controller, even if it's never shown.
    home_window = Home()

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
    app = QApplication(sys.argv)

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

    sys.exit(app.exec_())