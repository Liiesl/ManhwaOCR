from PyQt5.QtWidgets import QDialog, QVBoxLayout, QFormLayout, QComboBox, QSpinBox, QDialogButtonBox, QTabWidget, QWidget, QLineEdit, QKeySequenceEdit
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QKeySequence

class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.settings = parent.settings  # Access main window's QSettings
        
        # Main layout for the dialog
        main_layout = QVBoxLayout()
        
        # Create tab widget
        self.tab_widget = QTabWidget()
        
        # OCR Processing Settings Tab
        processing_tab = QWidget()
        form_layout = QFormLayout()
        
        # Min Text Area Setting
        self.min_text_spin = QSpinBox()
        self.min_text_spin.setRange(0, 1000000)
        self.min_text_spin.setValue(int(self.settings.value("min_text_area", 4000)))  # Default value: 4000
        form_layout.addRow("Minimum Text Area:", self.min_text_spin)
        
        # Distance Threshold Setting
        self.distance_spin = QSpinBox()
        self.distance_spin.setRange(0, 500)
        self.distance_spin.setValue(int(self.settings.value("distance_threshold", 100)))  # Default value: 100
        form_layout.addRow("Distance Threshold:", self.distance_spin)
        
        processing_tab.setLayout(form_layout)
        self.tab_widget.addTab(processing_tab, "OCR Processing")

        # API Settings Tab
        api_tab = QWidget()
        api_layout = QFormLayout()
        
        # Gemini API Key
        self.api_key_edit = QLineEdit()
        self.api_key_edit.setEchoMode(QLineEdit.Password)
        self.api_key_edit.setText(self.settings.value("gemini_api_key", ""))
        api_layout.addRow("Gemini API Key:", self.api_key_edit)
        
        # Gemini Model Selection
        self.model_combo = QComboBox()
        self.model_combo.addItems([
            "gemini-2.0-flash",
            "gemini-2.0-flash-lite",
            "gemini-2.0-pro-exp-02-05",
            "gemini-2.0-flash-thinking-exp-01-21",
            "gemini-1.5-pro",
            "gemini-1.5-flash",
        ])
        current_model = self.settings.value("gemini_model", "gemini-2.0-flash")
        self.model_combo.setCurrentText(current_model)
        api_layout.addRow("Gemini Model:", self.model_combo)
        
        api_tab.setLayout(api_layout)
        self.tab_widget.addTab(api_tab, "Translation APIs")
        
        # Add the tab widget to the main layout
        main_layout.addWidget(self.tab_widget)
        
        # Buttons
        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        main_layout.addWidget(buttons)  # Add buttons after the tab widget

        # Add Keyboard Shortcuts Tab
        shortcuts_tab = QWidget()
        shortcuts_layout = QFormLayout()
        
        # Combine Rows Shortcut
        self.combine_shortcut_edit = QKeySequenceEdit(
            QKeySequence(self.settings.value("combine_shortcut", "Ctrl+G"))
        )
        shortcuts_layout.addRow("Combine Rows Shortcut:", self.combine_shortcut_edit)
        
        shortcuts_tab.setLayout(shortcuts_layout)
        self.tab_widget.addTab(shortcuts_tab, "Keyboard Shortcuts")
        
        # Set the main layout for the dialog
        self.setLayout(main_layout)

    def accept(self):
        # Save new settings
        self.settings.setValue("min_text_area", self.min_text_spin.value())
        self.settings.setValue("distance_threshold", self.distance_spin.value())
        self.settings.setValue("gemini_api_key", self.api_key_edit.text())
        self.settings.setValue("gemini_model", self.model_combo.currentText())
        self.settings.setValue("combine_shortcut", self.combine_shortcut_edit.keySequence().toString())
        super().accept()