from PyQt5.QtWidgets import QDialog, QVBoxLayout, QFormLayout, QComboBox, QSpinBox, QDialogButtonBox, QTabWidget, QWidget, QLineEdit, QKeySequenceEdit, QCheckBox
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

        general_tab = QWidget()
        general_layout = QFormLayout()

        self.show_delete_warning_check = QCheckBox()
        self.show_delete_warning_check.setChecked(
            self.settings.value("show_delete_warning", "true") == "true"
        )
        general_layout.addRow("Show delete confirmation dialog:", self.show_delete_warning_check)

        general_tab.setLayout(general_layout)
        self.tab_widget.addTab(general_tab, "General")
        
        # OCR Processing Settings Tab
        processing_tab = QWidget()
        form_layout = QFormLayout()
        
        # Min Text Area Setting
        self.min_text_spin = QSpinBox()
        self.min_text_spin.setRange(0, 1000000)
        self.min_text_spin.setValue(int(self.settings.value("min_text_height", 40)))  # Default 40px
        form_layout.addRow("Minimum Text Height:", self.min_text_spin)
        
        #Max Text Area Setting
        self.max_text_spin = QSpinBox()
        self.max_text_spin.setRange(0, 10000000)
        self.max_text_spin.setValue(int(self.settings.value("max_text_height", 100)))  # Default 200px
        form_layout.addRow("Maximum Text Height:", self.max_text_spin)
        
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

        self.lang_combo = QComboBox()
        self.lang_combo.addItems([
            "English",
            "Japanese",
            "Chinese (Simplified)",
            "Spanish",
            "French",
            "German",
            "Bahasa Indonesia"
        ])
        current_lang = self.settings.value("target_language", "English")
        self.lang_combo.setCurrentText(current_lang)
        api_layout.addRow("Target Language:", self.lang_combo)
        
        api_tab.setLayout(api_layout)
        self.tab_widget.addTab(api_tab, "Translations")
        
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
        self.settings.setValue("show_delete_warning", 
            "true" if self.show_delete_warning_check.isChecked() else "false"
        )
        self.settings.setValue("min_text_height", self.min_text_spin.value())
        self.settings.setValue("max_text_height", self.max_text_spin.value())
        self.settings.setValue("distance_threshold", self.distance_spin.value())
        self.settings.setValue("gemini_api_key", self.api_key_edit.text())
        self.settings.setValue("gemini_model", self.model_combo.currentText())
        self.settings.setValue("combine_shortcut", self.combine_shortcut_edit.keySequence().toString())
        self.settings.setValue("target_language", self.lang_combo.currentText())
        super().accept()