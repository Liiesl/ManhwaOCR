from PyQt5.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QSizePolicy, QFrame, QScrollArea, QStackedWidget, 
                             QCheckBox, QPushButton, QTableWidget, QTableWidgetItem, QMessageBox, QSplitter, QHeaderView, 
                             QAction, QTextEdit, QLabel)
from PyQt5.QtCore import Qt, QSettings, QEvent, QPoint, QBuffer
from PyQt5.QtGui import QPixmap, QKeySequence, QFontMetrics, QColor
import qtawesome as qta
from core.ocr_processor import OCRProcessor
from utils.file_io import export_ocr_results, import_translation_file, export_rendered_images
from core.data_processing import group_and_merge_text, distance, merge_ocr_entries
from app.widgets import ResizableImageLabel, CustomScrollArea, TextEditDelegate
from app.widgets_2 import CustomProgressBar, MenuBar
from app.custom_bubble import TextBoxStylePanel
from utils.settings import SettingsDialog
from core.translations import TranslationThread, generate_for_translate_content, import_translation_file_content
from assets.styles import (COLORS, MAIN_STYLESHEET, IV_BUTTON_STYLES, ADVANCED_CHECK_STYLES, RIGHT_WIDGET_STYLES, SIMPLE_VIEW_STYLES, DELETE_ROW_STYLES,
                        PROGRESS_STYLES, DEFAULT_TEXT_STYLE, get_style_diff) 
import easyocr, os, gc, json, zipfile, math, PIL, io, sys, traceback
import numpy as np # Added numpy
from PIL import Image # Added PIL Image

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Manhwa OCR Tool")
        self.setGeometry(100, 100, 1200, 600)
        self.settings = QSettings("YourCompany", "MangaOCRTool")
        self.min_text_height = int(self.settings.value("min_text_height", 40))
        self.max_text_height = int(self.settings.value("max_text_height", 100))
        self.min_confidence = float(self.settings.value("min_confidence", 0.2))
        self.distance_threshold = int(self.settings.value("distance_threshold", 100))
        self.combine_action = QAction("Combine Rows", self)
        self.combine_action.triggered.connect(self.combine_selected_rows)
        self.update_shortcut()
        self.language_map = {
            "Korean": "ko",
            "Chinese": "ch_sim",
            "Japanese": "ja"
        }
        self.original_language = "Korean"
        self.manual_ocr_mode = False # Flag for manual OCR mode
        self.active_manual_ocr_label = None # Track which label is being used for manual OCR
        self.manual_selected_rect_scene = None # Store selected QRectF in scene coordinates
        self.rubber_band = None # Instance of QRubberBand for selection
        self.origin_point = None # Starting point for rubber band

        # Variables for manual OCR row numbering
        self.last_assigned_manual_sub_index = {} # Dictionary to track sub-indices per base row

        self.init_ui()
        self.current_image = None
        self.ocr_results = []
        self.results_table.cellChanged.connect(self.on_cell_changed)
        self.image_paths = []
        self.current_image_index = 0
        self.scroll_content = QWidget()
        self.reader = None
        self.ocr_processor = None
        
        # Variables for time tracking
        self.start_time = None
        self.processing_times = []
        self.current_progress = 0
        self.target_progress = 0

        self.active_image_label = None
        self.confirm_button = None
        self.current_text_items = []

        self.results_table.installEventFilter(self)

        self.mmtl_path = None  # Add this line to track current project pathl
        self.current_selected_row = None  # Track row number
        self.current_selected_image_label = None  # Track image label
        self.selected_text_box_item = None # <--- Add this to track the actual item
        self.style_panel.style_changed.connect(self.update_text_box_style)

    def init_ui(self):
        self.menuBar = MenuBar(self)  # From new file
        self.setMenuBar(self.menuBar)
        # Set the main widget and layout
        main_widget = QWidget()
        main_layout = QHBoxLayout()  # Main horizontal layou

        self.colors = COLORS

        # Apply global stylesheet for the application
        self.setStyleSheet(MAIN_STYLESHEET)

        # Left Panel
        left_panel = QVBoxLayout()  # Vertical layout for the left panel
        left_panel.setSpacing(20)

        # Open Folder Button
        settings_layout = QHBoxLayout()

        self.btn_settings = QPushButton(qta.icon('fa5s.cog', color='white'), "")
        self.btn_settings.setFixedSize(50, 50)
        self.btn_settings.clicked.connect(self.show_settings_dialog)
        settings_layout.addWidget(self.btn_settings)

        self.btn_save = QPushButton(qta.icon('fa5s.save', color='white'), "Save Project")
        self.btn_save.clicked.connect(self.save_project)
        settings_layout.addWidget(self.btn_save)
        left_panel.addLayout(settings_layout)       
        
        # Progress bars in their own row
        progress_layout = QVBoxLayout()
        self.ocr_progress = CustomProgressBar()
        self.ocr_progress.setFixedHeight(20)
        progress_layout.addWidget(self.ocr_progress)
        left_panel.addLayout(progress_layout)

        # Scroll Area
        self.scroll_area = CustomScrollArea(None)  # Initialize with None, will be set later
        self.scroll_content = QWidget()
        self.scroll_content.setStyleSheet("background-color: transparent;")  # Add this line
        self.scroll_content.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)  # Add this
        self.scroll_layout = QVBoxLayout(self.scroll_content)
        self.scroll_layout.setContentsMargins(0, 0, 0, 0)
        self.scroll_layout.setSpacing(0)
        self.scroll_area.setWidget(self.scroll_content)
        self.scroll_area.setWidgetResizable(True)
        left_panel.addWidget(self.scroll_area)

        # Add Scroll Top/Bottom Buttons as an Overlay
        scroll_button_overlay = QWidget(self.scroll_area)  # Create a widget for the overlay as a child of scroll_area
        scroll_button_overlay.setObjectName("ScrollButtonOverlay")  # Assign an object name for styling
        scroll_button_overlay.setStyleSheet("""
            #ScrollButtonOverlay {
                background-color: transparent;
            }
        """)
        scroll_button_layout = QHBoxLayout(scroll_button_overlay)  # Horizontal layout for the overlay
        scroll_button_layout.setContentsMargins(10, 10, 10, 10)  # Add some padding
        scroll_button_layout.setSpacing(1)  # Add spacing between buttons

        # Scroll Top Button
        self.btn_scroll_top = QPushButton(qta.icon('fa5s.arrow-up', color='white'), "")
        self.btn_scroll_top.setFixedSize(50, 50)  # Set fixed size for the button
        self.btn_scroll_top.clicked.connect(lambda: self.scroll_area.verticalScrollBar().setValue(0))
        self.btn_scroll_top.setStyleSheet(IV_BUTTON_STYLES)
        scroll_button_layout.addWidget(self.btn_scroll_top)

        # Export Manhwa Button
        self.btn_export_manhwa = QPushButton(qta.icon('fa5s.file-archive', color='white'), "Save")
        self.btn_export_manhwa.setFixedSize(120, 50)  # Set fixed size for the button
        self.btn_export_manhwa.clicked.connect(self.export_manhwa)
        self.btn_export_manhwa.setStyleSheet(IV_BUTTON_STYLES)
        scroll_button_layout.addWidget(self.btn_export_manhwa)  # Add the button to the layout

        # Scroll Bottom Button
        self.btn_scroll_bottom = QPushButton(qta.icon('fa5s.arrow-down', color='white'), "")
        self.btn_scroll_bottom.setFixedSize(50, 50)  # Set fixed size for the button
        self.btn_scroll_bottom.clicked.connect(lambda: self.scroll_area.verticalScrollBar().setValue(self.scroll_area.verticalScrollBar().maximum()))
        self.btn_scroll_bottom.setStyleSheet(IV_BUTTON_STYLES)
        scroll_button_layout.addWidget(self.btn_scroll_bottom)

        # Set the overlay widget to the custom scroll area
        self.scroll_area.overlay_widget = scroll_button_overlay

        # Position the overlay inside the scroll area
        self.scroll_area.update_overlay_position()
        scroll_button_overlay.raise_()  # Ensure the overlay is on top of other widgets

        # Right Panel
        right_panel = QVBoxLayout()  # Vertical layout for the right panel
        right_panel.padding = 30
        right_panel.setContentsMargins(20, 20, 20, 20)
        right_panel.setSpacing(20)

        # Top Row Buttons
        button_layout = QHBoxLayout()  # Horizontal layout for top row buttons
        self.btn_process = QPushButton(qta.icon('fa5s.magic', color='white'), "Process OCR")
        self.btn_process.setFixedWidth(160)
        self.btn_process.clicked.connect(self.start_ocr)
        self.btn_process.setEnabled(False)
        button_layout.addWidget(self.btn_process)
        self.btn_stop_ocr = QPushButton(qta.icon('fa5s.stop', color='white'), "Stop OCR")
        self.btn_stop_ocr.setFixedWidth(160)
        self.btn_stop_ocr.clicked.connect(self.stop_ocr)
        self.btn_stop_ocr.setVisible(False)  # Initially disabled
        button_layout.addWidget(self.btn_stop_ocr)
        # --- Add Manual OCR Button ---
        self.btn_manual_ocr = QPushButton(qta.icon('fa5s.crop-alt', color='white'), "Manual OCR")
        self.btn_manual_ocr.setFixedWidth(160) # Adjust width
        self.btn_manual_ocr.setCheckable(True) # Make it toggleable
        self.btn_manual_ocr.clicked.connect(self.toggle_manual_ocr_mode)
        self.btn_manual_ocr.setEnabled(False) # Disabled initially
        button_layout.addWidget(self.btn_manual_ocr)
        # --- End Add Manual OCR Button ---
        file_button_layout = QHBoxLayout()
        file_button_layout.setAlignment(Qt.AlignRight)
        file_button_layout.setSpacing(20)
        self.btn_import_translation = QPushButton(qta.icon('fa5s.file-import', color='white'), "Import Translation")
        self.btn_import_translation.setFixedWidth(250)
        self.btn_import_translation.clicked.connect(self.import_translation)
        file_button_layout.addWidget(self.btn_import_translation)
        self.btn_export_ocr = QPushButton(qta.icon('fa5s.file-export', color='white'), "Export OCR")
        self.btn_export_ocr.setFixedWidth(250)
        self.btn_export_ocr.clicked.connect(self.export_ocr)
        file_button_layout.addWidget(self.btn_export_ocr)
        button_layout.addLayout(file_button_layout)
        right_panel.addLayout(button_layout)

        # --- Add Manual OCR Overlay (initially hidden) ---
        self.manual_ocr_overlay = QWidget(self) # Parent is main window for global positioning
        self.manual_ocr_overlay.setObjectName("ManualOCROverlay")
        self.manual_ocr_overlay.setStyleSheet("""
            #ManualOCROverlay {
                background-color: rgba(0, 0, 0, 0.7); /* Semi-transparent black */
                border-radius: 5px;
            }
            QPushButton {
                background-color: #4CAF50; /* Green */
                border: none;
                color: white;
                padding: 5px 10px;
                text-align: center;
                font-size: 14px;
                margin: 2px;
                border-radius: 3px;
            }
            QPushButton:hover { background-color: #45a049; }
            QPushButton#CancelButton { background-color: #f44336; /* Red */ }
            QPushButton#CancelButton:hover { background-color: #da190b; }
            QPushButton#ResetButton { background-color: #ff9800; /* Orange */ }
            QPushButton#ResetButton:hover { background-color: #e68a00; }
            QLabel { color: white; font-size: 12px; }
        """)
        overlay_layout = QVBoxLayout(self.manual_ocr_overlay)
        overlay_layout.setContentsMargins(5, 5, 5, 5)
        overlay_layout.addWidget(QLabel("Selected Area:"))

        overlay_buttons = QHBoxLayout()
        self.btn_ocr_manual_area = QPushButton("OCR This Part")
        self.btn_ocr_manual_area.clicked.connect(self.process_manual_ocr_area)
        overlay_buttons.addWidget(self.btn_ocr_manual_area)

        self.btn_reset_manual_selection = QPushButton("Reset Selection")
        self.btn_reset_manual_selection.setObjectName("ResetButton")
        self.btn_reset_manual_selection.clicked.connect(self.reset_manual_selection)
        overlay_buttons.addWidget(self.btn_reset_manual_selection)

        self.btn_cancel_manual_ocr = QPushButton("Cancel Manual OCR")
        self.btn_cancel_manual_ocr.setObjectName("CancelButton")
        self.btn_cancel_manual_ocr.clicked.connect(self.cancel_manual_ocr_mode)
        overlay_buttons.addWidget(self.btn_cancel_manual_ocr)

        overlay_layout.addLayout(overlay_buttons)
        self.manual_ocr_overlay.setFixedSize(350, 80) # Adjust size as needed
        self.manual_ocr_overlay.hide()
        # --- End Manual OCR Overlay ---

        # Create a horizontal splitter to hold the style panel and the main content stack
        self.right_content_splitter = QSplitter(Qt.Horizontal)
        
        # Create the Text Box Style Panel
        self.style_panel = TextBoxStylePanel(default_style=DEFAULT_TEXT_STYLE) # Pass defaults
        self.style_panel.hide() # Initially hidden
        self.right_content_splitter.addWidget(self.style_panel) # Add panel to the left
        
        # OCR Results Table wrapped in a container widget
        self.right_content_stack = QStackedWidget()
        
        # OCR Results Table
        self.results_table = QTableWidget()
        self.results_table.setColumnCount(7)
        self.results_table.setHorizontalHeaderLabels(["Text", "Confidence", "Coordinates", "File", "Line Counts", "Row Number", ""])
        # Set column width after creating the table
        self.results_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.results_table.setColumnWidth(1, 50)
        self.results_table.setColumnWidth(2, 50)
        self.results_table.setColumnWidth(3, 50)
        self.results_table.setColumnWidth(5, 50)
        self.results_table.setColumnWidth(6, 50)
        self.results_table.horizontalHeader().setSectionResizeMode(6, QHeaderView.Fixed)
        self.results_table.setContextMenuPolicy(Qt.ActionsContextMenu)
        self.results_table.setWordWrap(True)
        self.results_table.setItemDelegateForColumn(0, TextEditDelegate(self))  # Add delegate for column 0
        self.results_table.addAction(self.combine_action)

        # Create container for simple view
        self.simple_view_widget = QWidget()
        self.simple_layout = QVBoxLayout(self.simple_view_widget)
        self.simple_layout.setContentsMargins(5, 5, 5, 5)
        self.simple_layout.setSpacing(10)

        self.simple_scroll = QScrollArea()
        self.simple_scroll.setWidgetResizable(True)
        self.simple_scroll_content = QWidget()
        self.simple_scroll_layout = QVBoxLayout(self.simple_scroll_content)
        self.simple_scroll.setWidget(self.simple_scroll_content)
        self.simple_scroll.setStyleSheet("border: none;")

        # Add both views to stack
        self.right_content_stack.addWidget(self.simple_scroll)
        self.right_content_stack.addWidget(self.results_table)
        
        # Create a container for the stack widget with stretch capabilities
        stack_container = QWidget()
        stack_layout = QVBoxLayout(stack_container)
        stack_layout.setContentsMargins(0, 0, 0, 0)
        stack_layout.addWidget(self.right_content_stack)
        
        # Add the stack container to the splitter
        self.right_content_splitter.addWidget(stack_container)
        
        # Set stretch factors for splitter
        self.right_content_splitter.setStretchFactor(0, 0)  # Style panel - don't stretch
        self.right_content_splitter.setStretchFactor(1, 1)  # Content - stretch to fill available space
        
        # Add the splitter to the right panel
        right_panel.addWidget(self.right_content_splitter, 1)  # Give it a stretch factor

        # Save the current splitter sizes when the style panel is shown
        self.style_panel_size = None

        # Modify translation button layout
        translation_btn_layout = QHBoxLayout()
        
        self.btn_translate = QPushButton(qta.icon('fa5s.language', color='white'), "Translate")
        self.btn_translate.clicked.connect(self.start_translation)
        translation_btn_layout.addWidget(self.btn_translate)
        
        self.btn_apply_translation = QPushButton(qta.icon('fa5s.check', color='white'), "Apply Translation")
        self.btn_apply_translation.clicked.connect(self.apply_translation)
        translation_btn_layout.addWidget(self.btn_apply_translation)

        # In the init_ui method, modify the translation_btn_layout section
        self.advanced_mode_check = QCheckBox("Advanced Mode")
        self.advanced_mode_check.setStyleSheet(ADVANCED_CHECK_STYLES)
        self.advanced_mode_check.setChecked(False)
        self.advanced_mode_check.setCursor(Qt.PointingHandCursor)  # Changes cursor to hand when hovering
        self.advanced_mode_check.stateChanged.connect(self.toggle_advanced_mode)
        translation_btn_layout.addWidget(self.advanced_mode_check)
        right_panel.addLayout(translation_btn_layout)

        # Create the right widget and apply specific styles
        right_widget = QWidget()
        right_widget.setLayout(right_panel)
        right_widget.setStyleSheet(RIGHT_WIDGET_STYLES)

        # Splitter to divide left and right panels
        splitter = QSplitter(Qt.Horizontal)
        left_widget = QWidget()
        left_widget.setLayout(left_panel)
        splitter.addWidget(left_widget)
        splitter.addWidget(right_widget)

        main_layout.addWidget(splitter)
        main_widget.setLayout(main_layout)
        self.setCentralWidget(main_widget)

    def show_settings_dialog(self):
        dialog = SettingsDialog(self)
        if dialog.exec_():
            # Update settings in main window
            self.update_shortcut()
            self.min_text_height = int(self.settings.value("min_text_height", 40))
            self.max_text_height = int(self.settings.value("max_text_height", 100))
            self.min_confidence = float(self.settings.value("min_confidence", 0.2))
            self.distance_threshold = int(self.settings.value("distance_threshold", 100))

    def process_mmtl(self, mmtl_path, temp_dir):
        self.mmtl_path = mmtl_path
        # Add project name to window title
        project_name = os.path.splitext(os.path.basename(mmtl_path))[0]
        self.setWindowTitle(f"{project_name} | ManhwaOCR")  # <-- Add this line
        self.temp_dir = temp_dir
        self.image_paths = sorted([
            os.path.join(temp_dir, 'images', f) 
            for f in os.listdir(os.path.join(temp_dir, 'images'))
            if f.lower().endswith(('png', 'jpg', 'jpeg'))
        ])
        
        # Load existing OCR results (only if master.json exists)
        master_path = os.path.join(temp_dir, 'master.json')
        if os.path.exists(master_path):
            try:
                with open(master_path, 'r') as f:
                    self.ocr_results = json.load(f)
            except json.JSONDecodeError:
                QMessageBox.critical(self, "Error", "Failed to load OCR data. Corrupted master.json?")
                self.ocr_results = []
        
        # Load meta.json to get original language
        meta_path = os.path.join(temp_dir, 'meta.json')
        with open(meta_path, 'r') as f:
            meta = json.load(f)
            self.original_language = meta.get('original_language', 'Korean')  # Default to Korean
        
        if not self.image_paths:
            QMessageBox.warning(self, "Error", "No images found in selected folder")
            return

        self.btn_process.setEnabled(True)
        self.btn_manual_ocr.setEnabled(True) # Enable manual OCR button
        self.ocr_progress.setValue(0)

        # --- Reset manual OCR state when loading new project ---
        if self.manual_ocr_mode:
             self.cancel_manual_ocr_mode() # Turn off mode if active
        # --- End Reset ---

        # Clear existing images and widgets
        while self.scroll_layout.count():
             item = self.scroll_layout.takeAt(0)
             widget = item.widget()
             if widget:
                  # Explicitly cleanup ResizableImageLabel if needed
                  if isinstance(widget, ResizableImageLabel):
                       widget.cleanup() # Call cleanup before deleting
                  widget.deleteLater()

        # Add images to single scroll area
        for image_path in self.image_paths:
            try:
                 pixmap = QPixmap(image_path)
                 if pixmap.isNull():
                      print(f"Warning: Failed to load image {image_path}")
                      continue
                 filename = os.path.basename(image_path)
                 label = ResizableImageLabel(pixmap, filename)
                 label.textBoxDeleted.connect(self.delete_row)
                 label.textBoxSelected.connect(self.handle_text_box_selected)
                 label.manual_area_selected.connect(self.handle_manual_area_selected)
                 self.scroll_layout.addWidget(label)
            except Exception as e:
                 print(f"Error creating ResizableImageLabel for {image_path}: {e}")

        # Update UI components immediately
        self.update_results_table()  # <-- Add this line
    
    def handle_text_box_selected(self, row_number, image_label, selected):
        """Handles selection changes from ANY ResizableImageLabel."""
        if selected:
            # --- Find the item and update panel ---
            self.current_selected_row = row_number
            self.current_selected_image_label = image_label
            self.selected_text_box_item = None
            for tb in image_label.get_text_boxes():
                if tb.row_number == row_number:
                    self.selected_text_box_item = tb
                    break

            if self.selected_text_box_item:
                # Fetch current style (including custom overrides) from the item or ocr_results
                current_style = self.get_style_for_row(row_number)
                print(f"Found TextBoxItem for row {row_number}. Updating style panel with: {current_style}")
                self.style_panel.update_style_panel(current_style) # Pass the full style dict
                self.style_panel.show() # Ensure panel is visible
            else:
                print(f"ERROR: Could not find TextBoxItem for row {row_number} in label {image_label.filename}")
                self.style_panel.clear_and_hide()

            # --- Deselect in other images (existing logic) ---
            for i in range(self.scroll_layout.count()):
                widget = self.scroll_layout.itemAt(i).widget()
                if isinstance(widget, ResizableImageLabel) and widget != image_label:
                    widget.deselect_all_text_boxes()

        else:
            # --- Hide panel if the deselected item was the active one ---
            if row_number == self.current_selected_row and image_label == self.current_selected_image_label:
                self.current_selected_row = None
                self.current_selected_image_label = None
                self.selected_text_box_item = None
                self.style_panel.clear_and_hide()

    def get_style_for_row(self, row_number):
        """Gets the combined style (default + custom) for a given row."""
        # Start with a copy of the default style
        # Important: Need to convert default color strings back to QColor for comparison/use
        style = {}
        for k, v in DEFAULT_TEXT_STYLE.items():
             if k in ['bg_color', 'border_color', 'text_color']:
                 style[k] = QColor(v)
             else:
                 style[k] = v

        # Find the result and apply custom overrides
        for result in self.ocr_results:
            if result.get('row_number') == row_number:
                custom_style = result.get('custom_style', {})
                for k, v in custom_style.items():
                     if k in ['bg_color', 'border_color', 'text_color']:
                         style[k] = QColor(v) # Convert stored string to QColor
                     else:
                         style[k] = v
                break # Found the result
        return style

    def update_text_box_style(self, new_style_dict):
        """Applies the style to the selected TextBoxItem and stores the diff."""
        if not self.selected_text_box_item:
            print("Style changed but no text box selected.")
            return

        row_number = self.selected_text_box_item.row_number

        # Find the corresponding result in ocr_results
        target_result = None
        for result in self.ocr_results:
            if result.get('row_number') == row_number:
                target_result = result
                break

        if not target_result:
            print(f"Error: Could not find result for row {row_number} to apply style.")
            return
            
        if target_result.get('is_deleted', False):
             print(f"Warning: Attempting to style a deleted row ({row_number}). Ignoring.")
             return

        print(f"Applying style to row {row_number}: {new_style_dict}")

        # Calculate the difference from the default style
        style_diff = get_style_diff(new_style_dict, DEFAULT_TEXT_STYLE)

        # Store the difference (or remove the key if back to default)
        if style_diff:
            target_result['custom_style'] = style_diff
            print(f"Stored custom style diff for row {row_number}: {style_diff}")
        elif 'custom_style' in target_result:
            del target_result['custom_style']
            print(f"Removed custom style for row {row_number} (back to default).")

        # --- Apply the *full* new style to the visual TextBoxItem ---
        # We need the TextBoxItem to have a method to accept a style dictionary
        self.selected_text_box_item.apply_styles(new_style_dict)

        # --- New Methods for Manual OCR ---

    def toggle_manual_ocr_mode(self, checked):
        """Activate or deactivate manual OCR selection mode."""
        if checked:
            # --- Entering Manual OCR Mode ---
            self.manual_ocr_mode = True
            self.btn_manual_ocr.setText("Cancel Manual OCR")
            self.btn_process.setEnabled(False) # Disable standard OCR

            # Initialize EasyOCR reader (only if not already initialized)
            if self.reader is None:
                try:
                    print("Initializing EasyOCR reader for manual mode...")
                    lang_code = self.language_map.get(self.original_language, 'ko')
                    use_gpu = self.settings.value("use_gpu", "true").lower() == "true"
                    # Make reader an instance variable if used elsewhere, otherwise local is fine
                    self.reader = easyocr.Reader([lang_code], gpu=use_gpu)
                    print("EasyOCR reader initialized successfully.")
                except Exception as e:
                    print(f"Failed to initialize OCR reader: {e}")
                    QMessageBox.critical(self, "Error", f"Failed to initialize OCR reader: {str(e)}")
                    self.cancel_manual_ocr_mode() # Abort entering mode
                    return

            # Stop any ongoing standard OCR
            if hasattr(self, 'ocr_processor') and self.ocr_processor and self.ocr_processor.isRunning():
                self.stop_ocr() # Ensure standard OCR process is stopped

            self.btn_stop_ocr.setVisible(False)
            self.manual_ocr_overlay.hide() # Ensure overlay is hidden initially
            self._clear_any_active_selection() # Clear selection from previous attempts if any
            self._set_manual_selection_enabled_on_all(True) # Enable selection START on all labels
            QMessageBox.information(self, "Manual OCR Mode",
                                    "Click and drag on an image to select an area for OCR.")
        else:
            # --- Exiting Manual OCR Mode ---
            self.cancel_manual_ocr_mode()

    def cancel_manual_ocr_mode(self):
        """Cleans up and exits manual OCR mode fully."""
        print("Cancelling Manual OCR mode...")
        self.manual_ocr_mode = False
        if self.btn_manual_ocr.isChecked():
            self.btn_manual_ocr.setChecked(False) # Uncheck the button programmatically
        self.btn_manual_ocr.setText("Manual OCR")
        # Re-enable process button ONLY if images are loaded
        self.btn_process.setEnabled(bool(self.image_paths))

        self.manual_ocr_overlay.hide()
        self._clear_any_active_selection() # Clear visual selection rectangle if present
        self._set_manual_selection_enabled_on_all(False) # Disable selection START on all labels

        self.active_manual_ocr_label = None
        self.manual_selected_rect_scene = None
        # self.reader = None # Optional: Release reader if memory is critical, or keep for next time
        # gc.collect()

        print("Manual OCR mode cancelled.")

    def reset_manual_selection(self):
        """Resets the current selection, allowing the user to draw again."""
        print("Resetting manual selection...")
        self.manual_ocr_overlay.hide()
        self._clear_any_active_selection() # Hide rubber band on the active label

        self.active_manual_ocr_label = None # Forget which label had the selection
        self.manual_selected_rect_scene = None

        # Re-enable selection START on all labels IF still in manual mode
        if self.manual_ocr_mode:
             self._set_manual_selection_enabled_on_all(True)
             print("Selection reset. Ready for new selection.")
        else:
             print("Selection reset (mode was also exited).")

    def _set_manual_selection_enabled_on_all(self, enabled):
        """Enable/disable the ability to START a manual selection on all image labels."""
        # print(f"Setting manual selection enabled={enabled} on ALL labels.")
        for i in range(self.scroll_layout.count()):
            widget = self.scroll_layout.itemAt(i).widget()
            if isinstance(widget, ResizableImageLabel):
                widget.set_manual_selection_enabled(enabled)

    def _clear_any_active_selection(self):
        """Finds the label with the active selection (if any) and clears it."""
        if self.active_manual_ocr_label:
             # print(f"Clearing active selection on specific label: {self.active_manual_ocr_label.filename}")
             self.active_manual_ocr_label.clear_active_selection()
        else:
            # Fallback: Iterate all just in case state is inconsistent
            # print("No specific active label known, checking all labels to clear selection.")
            for i in range(self.scroll_layout.count()):
                widget = self.scroll_layout.itemAt(i).widget()
                if isinstance(widget, ResizableImageLabel):
                    widget.clear_active_selection() # Tell each label to clear its state

    def handle_manual_area_selected(self, rect_scene, label_widget):
        """Called when ResizableImageLabel signals a valid selection is completed."""
        if not self.manual_ocr_mode:
            print("DEBUG: handle_manual_area_selected called but manual_ocr_mode is False. Ignoring.")
            # This label might need its selection cleared if state is weird
            label_widget.clear_active_selection()
            return

        print(f"Handling completed manual selection from {label_widget.filename}")
        self.manual_selected_rect_scene = rect_scene
        self.active_manual_ocr_label = label_widget # This IS the label with the active selection

        # --- IMPORTANT: Disable STARTING a new selection on ALL labels ---
        # The active label already set its internal flag (_is_selection_active)
        # and changed its cursor upon successful selection completion.
        self._set_manual_selection_enabled_on_all(False)

        # --- Position and Show Overlay ---
        try:
            # Map label's top-left corner relative to the scroll area's viewport
            label_pos_in_viewport = label_widget.mapTo(self.scroll_area.viewport(), QPoint(0, 0))
            # Map viewport position to global screen coordinates
            global_pos = self.scroll_area.viewport().mapToGlobal(label_pos_in_viewport)
            # Map global position back to the main window's coordinates
            main_window_pos = self.mapFromGlobal(global_pos)

            # Calculate overlay position relative to the label within the main window
            # Adjust based on scroll position if necessary (mapping should handle this)
            overlay_x = main_window_pos.x() + (label_widget.width() - self.manual_ocr_overlay.width()) // 2
            overlay_y = main_window_pos.y() + label_widget.height() + 5 # 5px below label

            # Clamp position to be within main window bounds
            overlay_x = max(0, min(overlay_x, self.width() - self.manual_ocr_overlay.width()))
            overlay_y = max(0, min(overlay_y, self.height() - self.manual_ocr_overlay.height()))

            self.manual_ocr_overlay.move(overlay_x, overlay_y)
            self.manual_ocr_overlay.show()
            self.manual_ocr_overlay.raise_()
            print(f"Manual OCR overlay shown for selection on {label_widget.filename}")

        except Exception as e:
            print(f"Error positioning/showing manual OCR overlay: {e}")
            traceback.print_exc(file=sys.stdout)
            self.reset_manual_selection() # Reset state if overlay fails

    def process_manual_ocr_area(self):
        """
        Crops the selected area, runs OCR, potentially merges results *within*
        that area based on proximity, assigns new row numbers, and adds them.
        Does NOT merge with existing results outside the selection.
        """
        if not self.manual_selected_rect_scene or not self.active_manual_ocr_label or not self.reader:
            QMessageBox.warning(self, "Error", "No area selected, active label lost, or OCR reader not ready.")
            self.reset_manual_selection()
            return

        print(f"Processing manual OCR for selection on {self.active_manual_ocr_label.filename}")
        self.manual_ocr_overlay.hide()

        try:
            # 1. Get the Crop
            crop_rect = self.manual_selected_rect_scene.toRect()
            if crop_rect.width() <= 0 or crop_rect.height() <= 0:
                QMessageBox.warning(self, "Error", "Invalid selection area.")
                self.reset_manual_selection()
                return

            pixmap = self.active_manual_ocr_label.original_pixmap
            pixmap_rect = pixmap.rect()
            # Ensure crop_rect is QRect, not QRectF for intersection if needed, though toRect() usually returns QRect
            bounded_crop_rect = crop_rect.intersected(pixmap_rect)

            if bounded_crop_rect.width() <= 0 or bounded_crop_rect.height() <= 0:
                 QMessageBox.warning(self, "Error", "Selection area is outside image bounds.")
                 self.reset_manual_selection()
                 return

            cropped_pixmap = pixmap.copy(bounded_crop_rect)
            buffer = QBuffer()
            buffer.open(QBuffer.ReadWrite)
            cropped_pixmap.save(buffer, "PNG")
            pil_image = Image.open(io.BytesIO(buffer.data())).convert('L')
            img_np = np.array(pil_image)

            # 2. Run OCR on the Cropped Area
            print(f"Running manual OCR on cropped area: {bounded_crop_rect}")
            # Use detail=1 to get coordinates, text, confidence
            raw_results_relative = self.reader.readtext(img_np, batch_size=1, detail=1)
            print(f"Manual OCR raw results (relative coords): {raw_results_relative}")

            if not raw_results_relative:
                 QMessageBox.information(self, "Info", "No text found in the selected area.")
                 self.reset_manual_selection()
                 return

            # 3. Prepare Raw Results for Internal Merging (using relative coords)
            temp_results_for_merge = []
            filename_placeholder = "manual_crop" # Filename doesn't matter for internal merge
            for (coord_rel, text, confidence) in raw_results_relative:
                # Keep relative coordinates for the internal merge step
                temp_results_for_merge.append({
                    'coordinates': coord_rel, # Relative coordinates
                    'text': text,
                    'confidence': confidence,
                    'filename': filename_placeholder, # Consistent placeholder
                    'line_counts': text.count('\n') + 1,
                    # 'is_manual': True # Will be added later
                })

            # 4. Merge Results *Within* the Selection Based on Proximity
            # Pass the temporary list with relative coordinates
            print(f"Attempting internal merge on {len(temp_results_for_merge)} raw detections...")
            merged_results_relative = group_and_merge_text(
                temp_results_for_merge,
                distance_threshold=self.distance_threshold
            )
            print(f"Internal merge resulted in {len(merged_results_relative)} final block(s).")

            # 5. Process Final Blocks (Filter, Offset Coords, Assign Row Num, Add)
            filename_actual = self.active_manual_ocr_label.filename
            added_rows_info = []
            any_change_made = False
            offset_x = bounded_crop_rect.left()
            offset_y = bounded_crop_rect.top()

            for merged_result in merged_results_relative:
                # Basic filtering (confidence, height) *after* internal merge
                confidence = merged_result['confidence']
                coords_relative = merged_result['coordinates'] # These are still relative
                text = merged_result['text']

                if not coords_relative: continue # Should not happen after merge, but check

                y_coords_rel = [p[1] for p in coords_relative]
                height = max(y_coords_rel) - min(y_coords_rel) if y_coords_rel else 0
                min_manual_height = 5 # Minimum height for a *final* block

                if confidence < self.min_confidence or height < min_manual_height:
                    print(f"Excluded final manual block (low conf/small): Text: '{text[:20]}...', Conf: {confidence:.2f}, Height: {height}")
                    continue

                # Convert coordinates to absolute (original image)
                coords_absolute = [[int(p[0] + offset_x), int(p[1] + offset_y)] for p in coords_relative]

                # Calculate new row number based on absolute coordinates
                try:
                    new_row_number = self._calculate_manual_row_number(coords_absolute, filename_actual)
                except Exception as e:
                     print(f"Error calculating row number for manual block '{text[:20]}...': {e}. Skipping.")
                     continue # Skip this block if row number fails

                # Create the final result dictionary to add to self.ocr_results
                final_result = {
                    'coordinates': coords_absolute,
                    'text': text,
                    'confidence': confidence,
                    'filename': filename_actual,
                    'line_counts': merged_result['line_counts'],
                    'is_manual': True, # Mark as manually added
                    'is_deleted': False,
                    'row_number': new_row_number # Assign calculated number
                    # 'custom_style': {} # Add default empty style if needed later
                }

                # Add to the main list
                self.ocr_results.append(final_result)
                any_change_made = True
                added_rows_info.append({'row': new_row_number, 'text': text})
                print(f"Added final manual block: Row {new_row_number}, Text: '{text[:20]}...'")

            # 6. Sort Results & Update UI (only if changes were made)
            if any_change_made:
                 self._sort_ocr_results() # Sort the entire list after adding new blocks
                 self.update_results_table()
                 # Refresh the specific image label where text was added
                 self.apply_translation_to_images([filename_actual]) # Update only the affected image
                 QMessageBox.information(self, "Success", f"Added {len(added_rows_info)} text block(s) from manual selection.")
            elif merged_results_relative: # Merging happened but results failed filters
                 QMessageBox.information(self, "Info", "Text detected, but final blocks did not meet criteria after internal merging.")
            # else case (no raw results) handled earlier

            # 7. Reset state to allow new selection
            self.reset_manual_selection()

        except Exception as e:
            print(f"Error during manual OCR processing: {e}")
            traceback.print_exc(file=sys.stdout)
            QMessageBox.critical(self, "Manual OCR Error", f"An unexpected error occurred: {str(e)}")
            # Attempt to reset state even on error
            self.reset_manual_selection()

    def _calculate_manual_row_number(self, coordinates, filename):
        """
        Calculates a float row number for a manually added OCR box.
        The number indicates its position relative to the *globally sorted* list.
        Format: floor(preceding_row_number).next_available_sub_index
        Considers deleted rows when determining the next sub-index to avoid reuse.
        """
        if not coordinates: return 0.0 # Safety first

        try:
            # Use the minimum y-coordinate (top edge) for sorting comparison
            y_coords = [p[1] for p in coordinates]
            sort_key_y = min(y_coords)
        except (ValueError, TypeError, IndexError) as e:
             print(f"Error calculating sort key Y for new manual box: {e}")
             return float('inf') # Assign a high number to sort last

        # --- Find the correct preceding row based on GLOBAL sort order ---
        # The global list self.ocr_results is assumed to be sorted by filename, then row_number
        preceding_result = None
        # Iterate through the sorted list to find the item that comes right before the new one
        for res in self.ocr_results:
            # *** IMPORTANT: Still skip deleted items when finding the PRECEDING VISIBLE item ***
            # We need to find the *visible* item that comes just before the new item's position.
            if res.get('is_deleted', False):
                continue

            res_filename = res.get('filename', '')
            res_coords = res.get('coordinates')
            res_row_number_raw = res.get('row_number') # Keep raw for now

            if res_row_number_raw is None or res_coords is None: continue # Skip items without row numbers or coords

            # Determine the sort key for the existing result (top y-coord)
            try:
                res_sort_key_y = min(p[1] for p in res_coords)
            except (ValueError, TypeError, IndexError):
                continue # Skip if coords invalid

            # --- Comparison Logic (based on global sort order) ---
            # 1. Compare Filenames
            if res_filename < filename:
                preceding_result = res # This result from a previous file is definitely before
                continue # Check the next one

            # 2. Compare within the Same File (based on vertical position)
            elif res_filename == filename:
                if res_sort_key_y < sort_key_y:
                    preceding_result = res # This result in the same file is vertically above
                    continue # Check the next one
                else:
                    # Found the first item in the same file at or below the new item.
                    # The 'preceding_result' stored *before* this loop is correct.
                    break # Exit the loop

            # 3. First item in a Later File
            else: # res_filename > filename
                # Found the first item belonging to a subsequent file.
                # The 'preceding_result' stored *before* this loop is correct.
                break # Exit the loop

        # --- Determine Base Row Number from the Preceding Result ---
        base_row_number = 0 # Default if it's the very first item
        if preceding_result:
            try:
                # Get the row number of the item found to be immediately preceding
                preceding_row_num_float = float(preceding_result.get('row_number', 0.0))
                base_row_number = math.floor(preceding_row_num_float)
            except (ValueError, TypeError):
                 print(f"Warning: Could not parse preceding row number '{preceding_result.get('row_number')}' for base calc.")
                 base_row_number = 0
        # else: it's the first item overall, base_row_number remains 0


        # --- Calculate Max Sub-index for this GLOBAL base_row_number ---
        # Find the highest existing sub-index associated with this base_row_number,
        # regardless of which file those sub-indexed rows belong to,
        # *** INCLUDING DELETED ROWS *** to avoid reusing their sub-indices.
        max_sub_index_for_base = 0
        for res in self.ocr_results:
             # *** MODIFICATION: REMOVED the 'is_deleted' check here ***
             # if not res.get('is_deleted', False): # <-- Removed this line

             current_row_num_raw = res.get('row_number')
             if current_row_num_raw is None: continue
             try:
                 current_row_num_float = float(current_row_num_raw)
                 # Check if this row belongs to the same integer base GLOBALLY
                 if math.floor(current_row_num_float) == base_row_number:
                      # Calculate sub-index accurately
                      # Multiply by 10, round to handle potential float inaccuracies
                      # Use a small epsilon for comparison to avoid floating point issues
                      epsilon = 1e-9
                      sub_index_float = (current_row_num_float - base_row_number) * 10
                      sub_index = int(sub_index_float + epsilon) # Round towards nearest int carefully

                      if sub_index > 0: # Only consider actual sub-indices (e.g., ignore the .0 part)
                           max_sub_index_for_base = max(max_sub_index_for_base, sub_index)
             except (ValueError, TypeError) as e:
                 # Log quietly, don't stop the whole process
                 # print(f"Debug: Could not parse row '{current_row_num_raw}' for sub-index calc: {e}")
                 pass # Continue checking other results

        new_sub_index = max_sub_index_for_base + 1
        # Construct the new float row number
        new_row_number = float(base_row_number) + (float(new_sub_index) / 10.0)

        # Debug print
        preceding_info = f"Row {preceding_result.get('row_number', 'N/A')} in {preceding_result.get('filename', 'N/A')}" if preceding_result else "None"
        print(f"Calculated manual row: {new_row_number:.1f} (Preceding Visible: [{preceding_info}], Base: {base_row_number}, Max Sub Found (incl. deleted): {max_sub_index_for_base}, New Sub: {new_sub_index})")

        return new_row_number

    def _sort_ocr_results(self):
        """Sorts OCR results primarily by filename, then by row number (float/int)."""
        try:
             # Ensure row_number is treated as float for consistent sorting
             def sort_key(item):
                 try:
                     # Use inf for None or unparseable row numbers to sort them last
                     row_num = float(item.get('row_number', float('inf')))
                 except (ValueError, TypeError):
                     row_num = float('inf')
                 return (item.get('filename', ''), row_num)

             self.ocr_results.sort(key=sort_key)
        except Exception as e: # Catch potential exceptions during sorting
             print(f"Error during sorting OCR results: {e}. Check row_number values.")
             traceback.print_exc(file=sys.stdout)
             QMessageBox.warning(self, "Sort Error", f"Could not sort OCR results: {e}\nManual row numbering might be affected.")
             # Avoid proceeding with operations that rely on sorted data if sort fails

    # --- End New Methods ---
    
    def start_ocr(self):
        if not self.image_paths:
            print("No images available for OCR.")
            return

        print("Starting OCR...")
        try:
            # Get language code from mapping
            lang_code = self.language_map.get(self.original_language, 'ko')
            self.reader = easyocr.Reader([lang_code])  # Use dynamic language
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to initialize OCR reader: {str(e)}")
            return
        self.ocr_progress.start_initial_progress()
        self.current_image_index = 0  # Start from the first image
        self.process_next_image()

    def process_next_image(self):
        if self.current_image_index >= len(self.image_paths):
            print("All images processed.")
            self.btn_stop_ocr.setVisible(False)
            self.btn_process.setVisible(True)
            self.reader = None
            self.ocr_processor = None
            gc.collect()
            
            # Stop the progress timer
            self.ocr_progress.setValue(100)
            return

        self.btn_process.setVisible(False)
        self.btn_stop_ocr.setVisible(True)

        image_path = self.image_paths[self.current_image_index]
        print(f"Processing image {self.current_image_index + 1}/{len(self.image_paths)}: {image_path}")

        # Start OCR for the current image
        self.ocr_processor = OCRProcessor(
            image_path,
            self.reader,
            min_text_height=self.min_text_height,
            max_text_height=self.max_text_height,
            min_confidence=self.min_confidence  # Add this line
        )
        self.ocr_processor.ocr_progress.connect(self.update_ocr_progress_for_image)
        self.ocr_processor.ocr_finished.connect(self.handle_ocr_results)
        self.ocr_processor.error_occurred.connect(self.handle_error)
        self.ocr_processor.start()

    def update_ocr_progress_for_image(self, progress):
        total_images = len(self.image_paths)
        if total_images == 0:
            return  # Prevent division by zero
        per_image_contribution = 80.0 / total_images # Calculate per-image contribution (80% divided by number of images)
        current_image_progress = progress / 100.0 # Calculate progress within the current image (0-100 to 0.0-1.0)
        overall_progress = 20 + (self.current_image_index * per_image_contribution) + (current_image_progress * per_image_contribution) # Total progress from completed images plus current image progress
        self.target_progress = min(int(overall_progress), 100) # Ensure progress does not exceed 100%

    def handle_ocr_results(self, results):
        if self.ocr_processor.stop_requested:
            print("Partial results discarded due to stop request")
            self.ocr_progress.reset() # Also reset progress on stop
            self.btn_stop_ocr.setVisible(False)
            self.btn_process.setVisible(True)
            return

        self.ocr_progress.record_processing_time()

        # Update progress (calculation remains the same)
        total_images = len(self.image_paths)
        if total_images > 0: # Prevent division by zero if stopped early
            per_image_contribution = 80.0 / total_images
            current_image_progress = 1.0  # Assume 100% progress for the completed image
            overall_progress = 20 + (self.current_image_index * per_image_contribution) + (current_image_progress * per_image_contribution)
            self.ocr_progress.update_target_progress(overall_progress)

        # --- Start of Row Numbering Change ---

        current_image_path = self.image_paths[self.current_image_index]
        filename = os.path.basename(current_image_path)

        # Add filename to raw results before merging
        results_with_filename = []
        for res in results:
            res['filename'] = filename
            results_with_filename.append(res)

        # Group and merge text from the same speech bubble (no row number assigned yet)
        merged_results_unassigned = group_and_merge_text(
            results_with_filename,
            distance_threshold=self.distance_threshold
        )

        # Sort the merged results for THIS FILE vertically based on top y-coordinate
        try:
            merged_results_unassigned.sort(key=lambda r: min(p[1] for p in r.get('coordinates', [[0, 0]])))
        except ValueError:
            print(f"Warning: Could not sort merged results for {filename} due to coordinate issues.")
            # Handle error - maybe skip adding results for this image or log more details

        # Assign sequential integer row numbers (0, 1, 2...) for THIS FILE
        newly_processed_results = []
        for idx, result in enumerate(merged_results_unassigned):
            result['row_number'] = idx # Assign file-specific integer row number
            newly_processed_results.append(result)

        # Extend the main results list
        self.ocr_results.extend(newly_processed_results)

        # Sort the *entire* list (important after adding new file's results and for manual OCR)
        self._sort_ocr_results()

        # --- End of Row Numbering Change ---

        # Update the table
        self.update_results_table()
        # Apply changes to the image label immediately
        self.apply_translation_to_images([filename]) # Update only the just-processed image

        # Move to the next image
        self.current_image_index += 1
        # Check stop condition *after* incrementing index
        if self.current_image_index >= len(self.image_paths):
            print("All images processed.")
            self.btn_stop_ocr.setVisible(False)
            self.btn_process.setVisible(True)
            # Final progress update
            self.ocr_progress.update_target_progress(100)
            self.reader = None # Release reader after all processing
            self.ocr_processor = None
            gc.collect()
            return # Explicitly return here

        # Continue to next image if not finished
        self.process_next_image()

    def toggle_advanced_mode(self, state):
        if state:
            self.update_simple_view()
            self.right_content_stack.setCurrentIndex(1)  # Table view
        else:
            self.right_content_stack.setCurrentIndex(0)  # Simple view

    def update_simple_view(self):
        # Clear existing widgets properly
        while self.simple_scroll_layout.count():
            child = self.simple_scroll_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        # --- Filter out deleted results ---
        visible_results = [res for res in self.ocr_results if not res.get('is_deleted', False)]

        # Create new editable text items with external delete buttons for VISIBLE results
        for result in visible_results: # Iterate over visible results
            original_row_number = result['row_number'] # Get original row number

            # Create container widget for frame + button
            container = QWidget()
            container_layout = QHBoxLayout(container)
            container_layout.setContentsMargins(5, 5, 5, 5)
            container_layout.setSpacing(10)

            # Text Frame
            text_frame = QFrame()
            text_frame.setStyleSheet(SIMPLE_VIEW_STYLES)
            text_layout = QVBoxLayout(text_frame)
            text_layout.setContentsMargins(0, 0, 0, 0)

            # Text Edit
            text_edit = QTextEdit(result['text'])
            text_edit.setStyleSheet(SIMPLE_VIEW_STYLES)
            text_edit.setLineWrapMode(QTextEdit.WidgetWidth)
            # --- Pass ORIGINAL row number to the handler ---
            text_edit.textChanged.connect(
                lambda rn=original_row_number, te=text_edit: self.on_simple_text_changed(rn, te.toPlainText())
            )
            text_layout.addWidget(text_edit)

            # Delete Button
            delete_btn = QPushButton(qta.icon('fa5s.trash-alt', color='red'), "")
            delete_btn.setFixedSize(100, 100) # Adjust size as needed
            delete_btn.setStyleSheet(SIMPLE_VIEW_STYLES)
            # --- Connect delete button using ORIGINAL row number ---
            delete_btn.clicked.connect(lambda _, rn=original_row_number: self.delete_row(rn))

            # Add widgets to container
            container_layout.addWidget(text_frame, 1)  # Allow frame to expand
            container_layout.addWidget(delete_btn)

            self.simple_scroll_layout.addWidget(container)

        self.simple_scroll_layout.addStretch()

    def on_simple_text_changed(self, original_row_number, text):
        """Update OCR results when text is edited in simple view"""
        # Find the result in the main list using the original row number
        target_result = None
        for res in self.ocr_results:
            if res.get('row_number') == original_row_number:
                target_result = res
                break

        if target_result:
            # Check if deleted (safety)
            if target_result.get('is_deleted', False):
                print(f"Warning: Attempted to edit deleted row {original_row_number} from simple view.")
                return
            target_result['text'] = text
            # If in advanced mode, refresh the table (optional, maybe not needed if table updates drive simple view)
            # if self.advanced_mode_check.isChecked():
            #    self.update_results_table() # Careful about potential loops
        else:
            print(f"Warning: Could not find result with row_number {original_row_number} in on_simple_text_changed")

    def update_results_table(self):
        self.results_table.blockSignals(True)  # Block signals during update

        # --- Filter out deleted results ---
        visible_results = [res for res in self.ocr_results if not res.get('is_deleted', False)]

        self.results_table.setRowCount(len(visible_results)) # Set row count to visible items

        # --- Iterate over VISIBLE results ---
        for visible_row_index, result in enumerate(visible_results):
            original_row_number = result['row_number'] # Get original row number

            # --- Format row number for display ---
            display_row_number = str(original_row_number)

            # Text column (editable)
            text_item = QTableWidgetItem(result['text'])
            text_item.setTextAlignment(Qt.AlignTop | Qt.AlignLeft)
            text_item.setFlags(text_item.flags() | Qt.ItemIsEditable)
            # --- Store original row number ---
            text_item.setData(Qt.UserRole, original_row_number)
            self.results_table.setItem(visible_row_index, 0, text_item)

            # Confidence (non-editable)
            confidence_item = QTableWidgetItem(f"{result['confidence']:.2f}")
            confidence_item.setTextAlignment(Qt.AlignCenter)
            confidence_item.setFlags(confidence_item.flags() & ~Qt.ItemIsEditable)
            confidence_item.setData(Qt.UserRole, original_row_number) # Also store here for consistency
            self.results_table.setItem(visible_row_index, 1, confidence_item)

            # Coordinates (non-editable)
            coord_item = QTableWidgetItem(str(result['coordinates']))
            coord_item.setTextAlignment(Qt.AlignCenter)
            coord_item.setFlags(coord_item.flags() & ~Qt.ItemIsEditable)
            coord_item.setData(Qt.UserRole, original_row_number)
            self.results_table.setItem(visible_row_index, 2, coord_item)

            # File (non-editable)
            file_item = QTableWidgetItem(result['filename'])
            file_item.setTextAlignment(Qt.AlignCenter)
            file_item.setFlags(file_item.flags() & ~Qt.ItemIsEditable)
            file_item.setData(Qt.UserRole, original_row_number)
            self.results_table.setItem(visible_row_index, 3, file_item)

            # Line Counts (editable)
            line_counts = str(result.get('line_counts', 1))
            line_item = QTableWidgetItem(line_counts)
            line_item.setTextAlignment(Qt.AlignCenter)
            line_item.setFlags(line_item.flags() | Qt.ItemIsEditable)
            line_item.setData(Qt.UserRole, original_row_number)
            self.results_table.setItem(visible_row_index, 4, line_item)

            # Row Number (non-editable) - Display the ORIGINAL row number
            row_num_display_item = QTableWidgetItem(display_row_number) # Use formatted string
            row_num_display_item.setTextAlignment(Qt.AlignCenter)
            row_num_display_item.setFlags(row_num_display_item.flags() & ~Qt.ItemIsEditable)
            row_num_display_item.setData(Qt.UserRole, original_row_number) # Store original
            self.results_table.setItem(visible_row_index, 5, row_num_display_item)

            # Add Delete Button
            delete_btn = QPushButton(qta.icon('fa5s.trash-alt', color='red'), "")
            delete_btn.setFixedSize(30, 30)

            container = QWidget()
            layout = QHBoxLayout()
            layout.addStretch()
            layout.addWidget(delete_btn)
            layout.setContentsMargins(0, 0, 0, 0)
            container.setLayout(layout)

            delete_btn.clicked.connect(lambda _, rn=original_row_number: self.delete_row(rn))
            self.results_table.setCellWidget(visible_row_index, 6, container)

        self.adjust_row_heights() # Adjust heights based on visible rows
        self.results_table.blockSignals(False)

        # Also update simple view if it's active
        if not self.advanced_mode_check.isChecked():
            self.update_simple_view()
    
    # Modify adjust_row_heights to better handle word wrap
    def adjust_row_heights(self):
        for row in range(self.results_table.rowCount()):
            text_item = self.results_table.item(row, 0)
            if text_item:
                text = text_item.text()
                font = text_item.font()
                font_metrics = QFontMetrics(font)
                column_width = self.results_table.columnWidth(0)
                
                # Calculate required height with word wrap
                rect = font_metrics.boundingRect(
                    0, 0, column_width, 0,
                    Qt.TextWordWrap,
                    text
                )
                required_height = rect.height()
                
                # Add padding for better visibility
                self.results_table.setRowHeight(row, required_height + 10)

    def eventFilter(self, obj, event):
        if obj == self.results_table and event.type() == QEvent.Resize:
            self.adjust_row_heights()
        return super().eventFilter(obj, event)

    def delete_row(self, row_number_to_delete):
        # Find the index corresponding to the row_number
        target_index = -1
        target_result = None # Store the result for filename lookup
        for idx, result in enumerate(self.ocr_results):
            if result.get('row_number') == row_number_to_delete:
                target_index = idx
                target_result = result # Keep track of the result dict
                break

        if target_index == -1 or target_result is None:
            print(f"Warning: Row number {row_number_to_delete} not found in ocr_results.")
            return # Row not found

        # --- Check if already marked as deleted ---
        if target_result.get('is_deleted', False):
            print(f"Info: Row number {row_number_to_delete} is already marked as deleted.")
            # Optionally, ensure it's visually removed if somehow still present
            # (This part handles potential inconsistencies)
            deleted_filename = target_result.get('filename')
            if deleted_filename:
                for i in range(self.scroll_layout.count()):
                    widget = self.scroll_layout.itemAt(i).widget()
                    if isinstance(widget, ResizableImageLabel) and widget.filename == deleted_filename:
                        widget.remove_text_box_by_row(row_number_to_delete) # Attempt removal again
                        break
            return # No further action needed if already marked

        # --- Confirmation Dialog Logic (remains the same) ---
        show_warning = self.settings.value("show_delete_warning", "true") == "true"
        proceed = True
        if show_warning:
            # ... (Confirmation dialog code remains unchanged) ...
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Warning)
            msg.setWindowTitle("Confirm Deletion Marking")
            msg.setText("<b>Mark for Deletion Warning</b>")
            msg.setInformativeText("This action will mark the selected text entry for deletion. It will be hidden from view and removed during translation application.\n\nDo you want to continue?")
            msg.setStyleSheet(DELETE_ROW_STYLES)
            dont_show_cb = QCheckBox("Remember my choice and do not ask again", msg)
            msg.setCheckBox(dont_show_cb)
            msg.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
            msg.setDefaultButton(QMessageBox.No)
            msg.setWindowIcon(qta.icon('fa5s.exclamation-triangle', color='orange'))
            response = msg.exec_()
            if dont_show_cb.isChecked():
                self.settings.setValue("show_delete_warning", "false")
            proceed = response == QMessageBox.Yes

        if not proceed:
            return

        # --- Core Change: Mark as deleted ---
        self.ocr_results[target_index]['is_deleted'] = True
        print(f"Marked row number {row_number_to_delete} (index {target_index}) as deleted.")
        deleted_filename = target_result.get('filename') # Get filename from the result

        # --- Check if the deleted row was the one currently selected for styling ---
        was_selected = (row_number_to_delete == self.current_selected_row)
        if was_selected:
            print(f"Deselecting deleted row {row_number_to_delete} and hiding style panel.")
            self.current_selected_row = None
            self.current_selected_image_label = None
            self.selected_text_box_item = None
            self.style_panel.clear_and_hide()

        # --- NEW: Immediately remove the visual item from the correct ResizableImageLabel ---
        if deleted_filename:
            found_label = False
            for i in range(self.scroll_layout.count()):
                widget = self.scroll_layout.itemAt(i).widget()
                if isinstance(widget, ResizableImageLabel) and widget.filename == deleted_filename:
                    print(f"Found ResizableImageLabel for {deleted_filename}. Requesting visual removal of row {row_number_to_delete}.")
                    widget.remove_text_box_by_row(row_number_to_delete)
                    found_label = True
                    break # Found the label, no need to continue loop
            if not found_label:
                    print(f"Warning: Could not find ResizableImageLabel widget for filename {deleted_filename} to perform visual removal.")
        else:
                print(f"Warning: Could not get filename for deleted row {row_number_to_delete} to perform visual removal.")

        # --- Refresh UI (table/simple view) ---
        self.update_results_table() # This will filter out the deleted item from the views


    def apply_translation_to_images(self, filenames_to_update=None):
        """Apply translations/visibility changes to images based on OCR results.
           Optionally updates only specific filenames."""
        grouped_results = {}
        for result in self.ocr_results:
             # No need to filter deleted here, ResizableImageLabel handles it
            filename = result.get('filename')
            row_number = result.get('row_number')

            # Skip if filename is None or row_number is None
            if filename is None or row_number is None:
                print(f"Warning: Skipping result with missing filename or row_number: {result}")
                continue

            # Optimization: Only process relevant files if specified
            if filenames_to_update and filename not in filenames_to_update:
                continue

            if filename not in grouped_results:
                grouped_results[filename] = {}

            # Pass the whole result dictionary, including 'custom_style'
            grouped_results[filename][row_number] = result


        # Iterate through visual labels
        for i in range(self.scroll_layout.count()):
            widget = self.scroll_layout.itemAt(i).widget()
            if isinstance(widget, ResizableImageLabel):
                image_filename = widget.filename
                # Update if it's in the target list (or if list is None/empty)
                if not filenames_to_update or image_filename in filenames_to_update:
                    # Get results for this specific image, or empty dict if none
                    results_for_this_image = grouped_results.get(image_filename, {})
                    # print(f"Applying updates to {image_filename} with {len(results_for_this_image)} entries.")
                    widget.apply_translation(results_for_this_image, DEFAULT_TEXT_STYLE)

    def on_cell_changed(self, row, column):
        # Get the original row number from the item's UserRole data
        item = self.results_table.item(row, column)
        if not item: return # Should not happen if called correctly

        original_row_number = item.data(Qt.UserRole)
        if original_row_number is None:
             print(f"Warning: Could not get original row number for visible row {row}, column {column}")
             return

        # Find the result in the main list using the original row number
        target_result = None
        for res in self.ocr_results:
            if res.get('row_number') == original_row_number:
                target_result = res
                break

        if not target_result:
            print(f"Warning: Could not find result with row_number {original_row_number} in ocr_results")
            return
        
        # Check if the result was marked deleted (shouldn't be editable, but safety check)
        if target_result.get('is_deleted', False):
             print(f"Warning: Attempted to edit a deleted row ({original_row_number}). Ignoring.")
             # Optionally revert the change in the table if it somehow happened
             # self.results_table.blockSignals(True)
             # item.setText(...) # Set back to original value if known
             # self.results_table.blockSignals(False)
             return

        # Update the target_result dictionary
        if column == 0:  # Text column
            new_text = item.text()
            target_result['text'] = new_text
            # If simple view is active, update it too
            if not self.advanced_mode_check.isChecked():
                 self.update_simple_view() # TODO: Optimize this later if needed
        elif column == 4:  # Line Counts column
            new_line_counts = item.text()
            try:
                line_counts = int(new_line_counts)
                target_result['line_counts'] = line_counts
            except ValueError:
                # Revert to previous value if invalid input
                prev_value = str(target_result.get('line_counts', 1))
                self.results_table.blockSignals(True)
                item.setText(prev_value)
                self.results_table.blockSignals(False)

    def update_shortcut(self):
        shortcut = self.settings.value("combine_shortcut", "Ctrl+G")
        self.combine_action.setShortcut(QKeySequence(shortcut))
    
    # Update combine_selected_rows to be safer with floats/ints
    def combine_selected_rows(self):
        selected_ranges = self.results_table.selectedRanges()
        if not selected_ranges:
            return

        # Get UNIQUE original row numbers from selected visible rows
        selected_original_row_numbers_raw = set()
        for r in selected_ranges:
            for row in range(r.topRow(), r.bottomRow() + 1):
                item = self.results_table.item(row, 0) # Check if item exists
                if item:
                    rn_raw = item.data(Qt.UserRole)
                    if rn_raw is not None:
                        selected_original_row_numbers_raw.add(rn_raw)

        if len(selected_original_row_numbers_raw) < 2:
            QMessageBox.warning(self, "Warning", "Select at least 2 rows to combine")
            return

        # Convert to float for reliable sorting, handle errors
        selected_original_row_numbers = []
        for rn_raw in selected_original_row_numbers_raw:
            try:
                selected_original_row_numbers.append(float(rn_raw))
            except (ValueError, TypeError):
                QMessageBox.critical(self, "Error", f"Invalid row number data found: {rn_raw}. Cannot combine.")
                return
        selected_original_row_numbers.sort() # Sort numerically

        # Fetch the actual result dictionaries using the original row numbers
        selected_results = []
        filename_set = set()
        contains_float = False
        for rn_float in selected_original_row_numbers:
            found = False
            for res in self.ocr_results:
                # Compare as floats after conversion for robustness
                try:
                    res_rn_float = float(res.get('row_number', float('inf')))
                    # Use a small tolerance for float comparison if necessary, but exact match preferred here
                    if math.isclose(res_rn_float, rn_float) and not res.get('is_deleted', False):
                        selected_results.append(res)
                        filename_set.add(res.get('filename'))
                        if isinstance(res.get('row_number'), float) and not res.get('row_number').is_integer():
                             contains_float = True
                        found = True
                        break
                except (ValueError, TypeError):
                     continue # Skip results with bad row numbers
            if not found:
                 # This should ideally not happen if UserRole data is correct
                 QMessageBox.critical(self, "Error", f"Could not find non-deleted result for row number {rn_float} during combine operation.")
                 return

        # --- Check: All from same file ---
        if len(filename_set) > 1:
            QMessageBox.warning(self, "Warning", "Cannot combine rows from different files")
            return

        # --- Check: RESTRICTION - Only allow combining if all selected rows are standard (integer) rows for now ---
        # This simplifies the adjacency check significantly.
        if contains_float:
             QMessageBox.warning(self, "Combine Restriction", "Combining rows that include manually added entries (decimal row numbers) is not supported yet. Please select only adjacent standard OCR rows.")
             return

        # --- Check: Adjacency for INTEGER rows ---
        # Since we filtered for integers and sorted numerically:
        is_adjacent = True
        for i in range(len(selected_original_row_numbers) - 1):
            # We are comparing the sorted float representations of the original integer row numbers
            if not math.isclose(selected_original_row_numbers[i+1] - selected_original_row_numbers[i], 1.0):
                is_adjacent = False
                break

        if not is_adjacent:
             QMessageBox.warning(self, "Warning", "Selected standard rows must form a contiguous sequence (e.g., 5, 6, 7) to combine.")
             return

        # --- Combine the rows (logic remains similar, but uses the fetched 'selected_results') ---
        # Sort selected_results again just to be sure order matches row numbers
        selected_results.sort(key=lambda x: float(x.get('row_number', float('inf'))))

        combined_text = []
        total_lines = 0
        coordinates = []
        min_confidence = 1.0 # Start high

        for result in selected_results:
            combined_text.append(result['text'])
            total_lines += result.get('line_counts', 1)
            coordinates.extend(result['coordinates']) # Extend might need refinement if precise bounding box needed
            min_confidence = min(min_confidence, result.get('confidence', 0.0))

        # Find the first result in the ORIGINAL list to update it
        # Use the first result from the sorted selected_results list
        first_result_to_update = selected_results[0]
        first_original_row = first_result_to_update['row_number'] # Keep original type for message

        # Update the first result *in the main ocr_results list*
        try:
             first_result_index = self.ocr_results.index(first_result_to_update)
             self.ocr_results[first_result_index]['text'] = '\n'.join(combined_text) # Join with newline? Or space? Check requirement. Let's use newline.
             self.ocr_results[first_result_index]['confidence'] = min_confidence
             # TODO: Recalculate combined coordinates properly if needed, for now just aggregate
             # self.ocr_results[first_result_index]['coordinates'] = calculate_combined_bbox(coordinates)
             self.ocr_results[first_result_index]['line_counts'] = total_lines
             self.ocr_results[first_result_index]['is_deleted'] = False # Ensure the combined one is not deleted
             # Keep the original row number of the first item
        except ValueError:
             QMessageBox.critical(self, "Error", "Could not find the first row in the main list to update during combine.")
             return


        # --- Mark the subsequent selected results as deleted ---
        for result_to_delete in selected_results[1:]: # Skip the first one
            try:
                 delete_index = self.ocr_results.index(result_to_delete)
                 self.ocr_results[delete_index]['is_deleted'] = True
            except ValueError:
                 # This might happen if the list was modified unexpectedly
                 print(f"Warning: Could not find result for row {result_to_delete.get('row_number')} to mark as deleted during combine.")


        # Update table and potentially the image label
        self.update_results_table()
        target_filename = list(filename_set)[0]
        if target_filename:
            self.apply_translation_to_images([target_filename])

        QMessageBox.information(self, "Success", f"Combined {len(selected_results)} rows into row {first_original_row}")
    
    def stop_ocr(self):
        if hasattr(self, 'ocr_processor'):
            self.ocr_processor.stop_requested = True
            self.ocr_progress.setValue(0)
            self.btn_stop_ocr.setVisible(False)
            self.btn_process.setVisible(True)
            self.reader = None
            gc.collect()
            QMessageBox.information(self, "Stopped", "OCR processing was stopped.")

        # Stop the progress timer
        self.ocr_progress.reset()

    def export_ocr(self):
        export_ocr_results(self)

    def start_translation(self):
        """Handle translation using Gemini API."""
        api_key = self.settings.value("gemini_api_key", "")
        model_name = self.settings.value("gemini_model", "gemini-2.0-flash")  # Get selected model
        if not api_key:
            QMessageBox.critical(self, "Error", "Please set Gemini API key in Settings")
            return
            
        # Generate for-translate format
        content = generate_for_translate_content(self)

        # Debug print: Show the content being sent to Gemini
        print("\n===== DEBUG: Content sent to Gemini =====\n")
        print(content)
        print("\n=======================================\n")

        target_lang = self.settings.value("target_language", "English")
        
        # Create progress dialog to show real-time translation
        self.translation_progress_dialog = QMessageBox(self)
        self.translation_progress_dialog.setWindowTitle("Translation in Progress")
        self.translation_progress_dialog.setText("Translating content using Gemini API...")
        self.translation_progress_dialog.setIcon(QMessageBox.Information)
        self.translation_progress_dialog.setStandardButtons(QMessageBox.Cancel)
        self.translation_progress_dialog.setDetailedText("")  # Will be updated with real-time content
        
        # Show the dialog non-modally
        self.translation_progress_dialog.show()
        
        # Create and start the translation thread
        self.translation_thread = TranslationThread(api_key, content, model_name=model_name, target_lang=target_lang)
        self.translation_thread.translation_finished.connect(self.on_translation_finished)
        self.translation_thread.translation_failed.connect(self.on_translation_failed)
        self.translation_thread.debug_print.connect(self.on_debug_print)
        self.translation_thread.translation_progress.connect(self.on_translation_progress)
        self.translation_thread.start()

    def on_translation_progress(self, chunk):
        """Handle real-time translation progress updates."""
        # Update the progress dialog with new chunks
        if hasattr(self, 'translation_progress_dialog') and self.translation_progress_dialog.isVisible():
            current_text = self.translation_progress_dialog.detailedText()
            self.translation_progress_dialog.setDetailedText(current_text + chunk)

    def on_translation_finished(self, translated_text):
        """Handle the successful completion of the translation."""
        try:
            # Close progress dialog if it exists
            if hasattr(self, 'translation_progress_dialog') and self.translation_progress_dialog.isVisible():
                self.translation_progress_dialog.accept()
                
            self.import_translated_content(translated_text)
            QMessageBox.information(self, "Success", "Translation completed successfully!")
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    def on_translation_failed(self, error_message):
        """Handle the failure of the translation."""
        # Close progress dialog if it exists
        if hasattr(self, 'translation_progress_dialog') and self.translation_progress_dialog.isVisible():
            self.translation_progress_dialog.accept()
            
        QMessageBox.critical(self, "Error", error_message)

    def on_debug_print(self, debug_message):
        """Handle real-time debug prints from the translation thread."""
        print("\n===== DEBUG: Real-time response from Gemini =====\n")
        print(debug_message)
        print("\n===============================================\n")

    def import_translated_content(self, content):
        """Import translated content back into OCR results."""
        try:
            # Reuse existing import logic
            import_translation_file_content(self, content)
            self.update_results_table()
        except Exception as e:
            raise Exception(f"Failed to import translation: {str(e)}")

    def apply_translation(self):
        """Apply translations/visibility changes to images based on OCR results."""
        self.apply_translation_to_images() # Call the renamed method

    def import_translation(self):
        import_translation_file(self)

    def export_manhwa(self):
        export_rendered_images(self)

    def save_project(self):
        """Saves the project, including custom styles."""
        # Ensure custom_style (with color strings) is saved
        master_path = os.path.join(self.temp_dir, 'master.json')
        try:
            self._sort_ocr_results()
            with open(master_path, 'w') as f:
                # Make sure QColor objects aren't accidentally saved
                serializable_results = []
                for res in self.ocr_results:
                    # No need to modify res directly if custom_style already has strings
                    serializable_results.append(res)
                json.dump(serializable_results, f, indent=2)

            # Repackage (existing logic)
            with zipfile.ZipFile(self.mmtl_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for root, dirs, files in os.walk(self.temp_dir):
                    for file in files:
                        full_path = os.path.join(root, file)
                        rel_path = os.path.relpath(full_path, self.temp_dir)
                        zipf.write(full_path, rel_path)

            QMessageBox.information(self, "Saved", "Project saved successfully")
        except Exception as e:
             QMessageBox.critical(self, "Save Error", f"Failed to save project: {e}")

    def closeEvent(self, event):
        # Clean up temp directory
        if os.path.exists(self.temp_dir):
            import shutil
            shutil.rmtree(self.temp_dir)
        super().closeEvent(event)

    def handle_error(self, message):
        print(f"Error occurred: {message}")
        QMessageBox.critical(self, "Error", message)
        self.progress.setValue(0)
        self.btn_process.setEnabled(False)