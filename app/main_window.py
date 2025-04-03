from PyQt5.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QSizePolicy, QFrame, QScrollArea, QStackedWidget, 
                             QCheckBox, QPushButton, QTableWidget, QTableWidgetItem, QMessageBox, QSplitter, QHeaderView, 
                             QAction, QTextEdit)
from PyQt5.QtCore import Qt, QSettings, QEvent
from PyQt5.QtGui import QPixmap, QKeySequence, QFontMetrics, QColor
import qtawesome as qta
from core.ocr_processor import OCRProcessor
from utils.file_io import export_ocr_results, import_translation_file, export_rendered_images
from core.data_processing import group_and_merge_text
from app.widgets import ResizableImageLabel, CustomScrollArea, TextEditDelegate
from app.widgets_2 import CustomProgressBar, MenuBar
from app.custom_bubble import TextBoxStylePanel
from utils.settings import SettingsDialog
from core.translations import TranslationThread, generate_for_translate_content, import_translation_file_content
from assets.styles import (COLORS, MAIN_STYLESHEET, IV_BUTTON_STYLES, ADVANCED_CHECK_STYLES, RIGHT_WIDGET_STYLES, SIMPLE_VIEW_STYLES, DELETE_ROW_STYLES,
                        PROGRESS_STYLES, DEFAULT_TEXT_STYLE, get_style_diff) 
import easyocr, os, gc, json, zipfile

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
        self.scroll_content.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)  # Add this
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
        self.btn_process.setFixedWidth(250)
        self.btn_process.clicked.connect(self.start_ocr)
        self.btn_process.setEnabled(False)
        button_layout.addWidget(self.btn_process)
        self.btn_stop_ocr = QPushButton(qta.icon('fa5s.stop', color='white'), "Stop OCR")
        self.btn_stop_ocr.setFixedWidth(250)
        self.btn_stop_ocr.clicked.connect(self.stop_ocr)
        self.btn_stop_ocr.setVisible(False)  # Initially disabled
        button_layout.addWidget(self.btn_stop_ocr)
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
        self.ocr_progress.setValue(0)

        # Clear existing images
        for i in reversed(range(self.scroll_layout.count())): 
            widget = self.scroll_layout.itemAt(i).widget()
            if widget:
                widget.deleteLater()

        # Add images to single scroll area
        for image_path in self.image_paths:
            pixmap = QPixmap(image_path)
            filename = os.path.basename(image_path)
            label = ResizableImageLabel(pixmap, filename)
            label.textBoxDeleted.connect(self.delete_row)
            label.textBoxSelected.connect(self.handle_text_box_selected)  # Connect signal
            self.scroll_layout.addWidget(label)

        # Update UI components immediately
        self.update_results_table()  # <-- Add this line
    
    def handle_text_box_selected(self, row_number, image_label, selected):
        """Handles selection changes from ANY ResizableImageLabel."""
        print(f"handle_text_box_selected called: row={row_number}, selected={selected}, label={image_label.filename}")

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
                print(f"Deselecting the active item (row {row_number}). Hiding style panel.")
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
            return
        
        self.ocr_progress.record_processing_time()
        
        # Update progress
        total_images = len(self.image_paths)
        per_image_contribution = 80.0 / total_images
        current_image_progress = 100 / 100.0  # 100% per image
        overall_progress = 20 + (self.current_image_index * per_image_contribution) + (current_image_progress * per_image_contribution)
        self.ocr_progress.update_target_progress(overall_progress)

        # Add results to the global list
        start_row = len(self.ocr_results)
        current_image_path = self.image_paths[self.current_image_index]
        filename = os.path.basename(current_image_path)
        for idx, result in enumerate(results):
            result['filename'] = filename
            result['row_number'] = start_row + idx  # Use continuous row numbering across all images

        # Group and merge text from the same speech bubble
        merged_results = group_and_merge_text(
            results, 
            distance_threshold=self.distance_threshold  # Pass new setting
        )
        for idx, result in enumerate(merged_results):
            result['row_number'] = start_row + idx
        self.ocr_results.extend(merged_results)

        # Update the table
        self.update_results_table()

        # Move to the next image
        self.current_image_index += 1
        if self.current_image_index >= len(self.image_paths):
            self.btn_stop_ocr.setVisible(False)
            self.btn_process.setVisible(True)
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
            row_num_display_item = QTableWidgetItem(str(original_row_number))
            row_num_display_item.setTextAlignment(Qt.AlignCenter)
            row_num_display_item.setFlags(row_num_display_item.flags() & ~Qt.ItemIsEditable)
            row_num_display_item.setData(Qt.UserRole, original_row_number)
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

            self.results_table.setCellWidget(visible_row_index, 6, container)
            # --- Connect delete button using the ORIGINAL row number ---
            delete_btn.clicked.connect(lambda _, rn=original_row_number: self.delete_row(rn))

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
        for idx, result in enumerate(self.ocr_results):
            if result.get('row_number') == row_number_to_delete:
                target_index = idx
                break
        
        if target_index == -1:
            print(f"Warning: Row number {row_number_to_delete} not found in ocr_results.")
            return # Row not found

        # Confirmation dialog logic (remains the same)
        show_warning = self.settings.value("show_delete_warning", "true") == "true"
        proceed = True

        if show_warning:
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Warning)
            msg.setWindowTitle("Confirm Deletion Marking")
            # Modify text slightly to reflect marking instead of deletion
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

        # --- Core Change: Mark as deleted instead of removing ---
        if 0 <= target_index < len(self.ocr_results):
            self.ocr_results[target_index]['is_deleted'] = True
            print(f"Marked row number {row_number_to_delete} (index {target_index}) as deleted.")
            # --- Check if the deleted row was the selected one ---
            was_selected = (row_number_to_delete == self.current_selected_row)
            # Refresh UI (which will now filter out deleted items)
            self.update_results_table()
            # Also update the image view if text boxes are currently shown
            self.apply_translation_to_images() # Renamed for clarity

        else:
            print(f"Error: Could not mark row number {row_number_to_delete}. Index {target_index} out of bounds.")

    def apply_translation_to_images(self):
        """Apply translations/visibility changes to images based on OCR results."""
        grouped_results = {}
        active_rows_by_file = {}
        for result in self.ocr_results:
            filename = result['filename']
            row_number = result.get('row_number', None)
            is_deleted = result.get('is_deleted', False)

            if filename not in grouped_results:
                grouped_results[filename] = {}
                active_rows_by_file[filename] = set()
            if row_number is not None:
                # Include the 'custom_style' if it exists
                grouped_results[filename][row_number] = result # Pass the whole dict
                if not is_deleted:
                    active_rows_by_file[filename].add(row_number)

        something_was_selected = self.selected_text_box_item is not None
        panel_needs_hide = False

        for i in range(self.scroll_layout.count()):
            widget = self.scroll_layout.itemAt(i).widget()
            if isinstance(widget, ResizableImageLabel):
                image_filename = widget.filename
                if image_filename in grouped_results:
                    # Pass the default style dictionary along with the results
                    widget.apply_translation(grouped_results[image_filename], DEFAULT_TEXT_STYLE)

                if something_was_selected and widget == self.current_selected_image_label:
                    current_file_active_rows = active_rows_by_file.get(image_filename, set())
                    if self.current_selected_row not in current_file_active_rows:
                        panel_needs_hide = True

        if panel_needs_hide:
            self.current_selected_row = None
            self.current_selected_image_label = None
            self.selected_text_box_item = None
            self.style_panel.clear_and_hide()

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
    
    def combine_selected_rows(self):
        selected_ranges = self.results_table.selectedRanges()
        if not selected_ranges:
            return

        # Get UNIQUE original row numbers from selected visible rows
        selected_original_row_numbers = sorted(list(set(
            self.results_table.item(row, 0).data(Qt.UserRole)
            for r in selected_ranges
            for row in range(r.topRow(), r.bottomRow() + 1)
            if self.results_table.item(row, 0) # Check if item exists
        )))

        if len(selected_original_row_numbers) < 2:
            QMessageBox.warning(self, "Warning", "Select at least 2 rows to combine")
            return

        # Fetch the actual result dictionaries using the original row numbers
        selected_results = []
        for rn in selected_original_row_numbers:
            found = False
            for res in self.ocr_results:
                # Make sure we only consider non-deleted items for combining
                if res.get('row_number') == rn and not res.get('is_deleted', False):
                    selected_results.append(res)
                    found = True
                    break
            if not found:
                 QMessageBox.critical(self, "Error", f"Could not find result for row number {rn} during combine operation.")
                 return

        # Sort selected_results by original row number to check adjacency correctly
        selected_results.sort(key=lambda x: x['row_number'])

        # Check adjacency based on original row numbers
        first_original_row = selected_results[0]['row_number']
        last_original_row = selected_results[-1]['row_number']
        
        # We need to ensure the original row numbers form a contiguous block
        # among the *non-deleted* items. This is complex.
        # Let's simplify: Check if the *visible* selection was contiguous.
        visible_rows = sorted(list(set(
            row for r in selected_ranges for row in range(r.topRow(), r.bottomRow() + 1)
        )))
        if any(visible_rows[i+1] - visible_rows[i] != 1 for i in range(len(visible_rows)-1)):
             QMessageBox.warning(self, "Warning", "Selected rows in the table must be adjacent to combine.")
             return

        # Check if all rows are from same file (using the fetched results)
        filenames = {res['filename'] for res in selected_results}
        if len(filenames) > 1:
            QMessageBox.warning(self, "Warning", "Cannot combine rows from different files")
            return

        # Combine the rows
        combined_text = []
        total_lines = 0
        coordinates = []
        min_confidence = 1.0 # Start high

        for result in selected_results:
            combined_text.append(result['text'])
            total_lines += result.get('line_counts', 1)
            coordinates.extend(result['coordinates'])
            min_confidence = min(min_confidence, result['confidence'])

        # Find the first result in the ORIGINAL list to update it
        first_result_to_update = None
        for res in self.ocr_results:
            if res['row_number'] == first_original_row:
                 first_result_to_update = res
                 break
        
        if not first_result_to_update:
            QMessageBox.critical(self, "Error", "Could not find the first row to update during combine.")
            return

        # Update the first result
        first_result_to_update['text'] = '\n'.join(combined_text)
        first_result_to_update['confidence'] = min_confidence
        first_result_to_update['coordinates'] = coordinates
        first_result_to_update['line_counts'] = total_lines
        first_result_to_update['is_deleted'] = False # Ensure the combined one is not deleted

        # --- Mark the subsequent selected results as deleted ---
        for result_to_delete in selected_results[1:]: # Skip the first one
            original_rn_to_delete = result_to_delete['row_number']
            for res in self.ocr_results: # Find in original list
                 if res['row_number'] == original_rn_to_delete:
                     res['is_deleted'] = True
                     break

        # Update table
        self.update_results_table()
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