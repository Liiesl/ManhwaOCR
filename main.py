import sys
from PyQt5.QtWidgets import QApplication, QSplashScreen
from PyQt5.QtGui import QColor, QFont
from PyQt5.QtCore import Qt, QTimer
from app.main_window import MainWindow

if __name__ == "__main__":
    app = QApplication(sys.argv)

    # Create and display the splash screen with text
    splash = QSplashScreen()
    splash.setFont(QFont("Arial", 10))  # Set font for the text
    splash.showMessage("Loading... Please wait", Qt.AlignCenter, QColor("Black"))  # Display text
    splash.show()

    # Process events to ensure the splash screen is shown immediately
    app.processEvents()

    # Simulate a delay for loading (e.g., 2 seconds)
    QTimer.singleShot(2000, splash.close)  # Close the splash screen after 2 seconds

    # Create the main window
    window = MainWindow()

    # Use a timer to delay the showing of the main window until the splash screen is closed
    QTimer.singleShot(2000, window.show)  # Show the main window after 2 seconds

    # Start the main application loop
    sys.exit(app.exec_())