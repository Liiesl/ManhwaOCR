# app/settings.py
# Centralized QSettings object for the entire application.

from PySide6.QtCore import QSettings

# This will be the single, globally accessible settings object.
# It is initialized once in main.py after the QApplication is created.
settings_instance = None

def init_settings():
    """
    Initializes the global settings object. Must be called after
    QApplication has been instantiated.
    """
    global settings_instance
    if settings_instance is None:
        # Use consistent names across the application
        settings_instance = QSettings("YourCompany", "ManhwaOCR")