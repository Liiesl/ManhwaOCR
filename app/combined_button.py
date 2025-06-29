from PyQt5.QtWidgets import QWidget, QVBoxLayout, QPushButton
from PyQt5.QtCore import Qt, pyqtSignal, QPoint
import qtawesome as qta

class ImportExportMenu(QWidget):
    """
    A custom popup menu widget for import and export actions.
    It's a frameless widget that behaves like a modal menu.
    """
    # Define signals that the main window can connect to
    import_requested = pyqtSignal()
    export_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Make it a frameless popup that closes when you click outside of it
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Popup)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_DeleteOnClose) # Clean up memory

        # --- Styling ---
        self.setStyleSheet("""
            QWidget {
                background-color: #3E4B5B;
                border: 1px solid #566573;
                border-radius: 5px;
                padding: 5px;
            }
            QPushButton {
                background-color: #4A5A6A;
                color: white;
                border: 1px solid #566573;
                padding: 10px 15px;
                font-size: 14px;
                text-align: left;
                border-radius: 4px;
                margin: 2px;
            }
            QPushButton:hover {
                background-color: #5D6D7E;
                border: 1px solid #7D8A96;
            }
            QPushButton:pressed {
                background-color: #41505F;
            }
        """)

        # --- Layout and Widgets ---
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(1)

        # Import Button
        btn_import = QPushButton(qta.icon('fa5s.file-import', color='white'), " Import Translation")
        btn_import.clicked.connect(self.on_import_click)
        layout.addWidget(btn_import)

        # Export Button
        btn_export = QPushButton(qta.icon('fa5s.file-export', color='white'), " Export OCR Results")
        btn_export.clicked.connect(self.on_export_click)
        layout.addWidget(btn_export)

        # Adjust size to fit contents
        self.setFixedSize(self.sizeHint())

    def on_import_click(self):
        """Emits the import signal and closes the menu."""
        self.import_requested.emit()
        self.close()

    def on_export_click(self):
        """Emits the export signal and closes the menu."""
        self.export_requested.emit()
        self.close()

class SaveMenu(QWidget):
    """
    A custom popup menu widget for save actions.
    """
    # Define signals that the main window can connect to
    save_project_requested = pyqtSignal()
    save_images_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Make it a frameless popup that closes when you click outside of it
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Popup)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_DeleteOnClose)

        # --- Styling ---
        self.setStyleSheet("""
            QWidget {
                background-color: #3E4B5B;
                border: 1px solid #566573;
                border-radius: 5px;
                padding: 5px;
            }
            QPushButton {
                background-color: #4A5A6A;
                color: white;
                border: 1px solid #566573;
                padding: 10px 15px;
                font-size: 14px;
                text-align: left;
                border-radius: 4px;
                margin: 2px;
            }
            QPushButton:hover {
                background-color: #5D6D7E;
                border: 1px solid #7D8A96;
            }
            QPushButton:pressed {
                background-color: #41505F;
            }
        """)

        # --- Layout and Widgets ---
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(1)

        # Save Project Button
        btn_save_project = QPushButton(qta.icon('fa5s.save', color='white'), " Save Project (.mmtl)")
        btn_save_project.clicked.connect(self.on_save_project_click)
        layout.addWidget(btn_save_project)

        # Save Rendered Images Button
        btn_save_images = QPushButton(qta.icon('fa5s.images', color='white'), " Save Rendered Images")
        btn_save_images.clicked.connect(self.on_save_images_click)
        layout.addWidget(btn_save_images)

        # Adjust size to fit contents
        self.setFixedSize(self.sizeHint())

    def on_save_project_click(self):
        """Emits the save project signal and closes the menu."""
        self.save_project_requested.emit()
        self.close()

    def on_save_images_click(self):
        """Emits the save images signal and closes the menu."""
        self.save_images_requested.emit()
        self.close()