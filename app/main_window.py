from PyQt5.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QSizePolicy,
                             QCheckBox, QPushButton,  QMessageBox, QSplitter, QAction, 
                             QLabel, QComboBox)
from PyQt5.QtCore import Qt, QSettings, QPoint
from PyQt5.QtGui import QPixmap, QKeySequence, QColor
import qtawesome as qta
from utils.file_io import export_ocr_results, import_translation_file, export_rendered_images
from app import (ResizableImageLabel, CustomProgressBar, MenuBar, CustomScrollArea, ResultsWidget, TextBoxStylePanel, 
                 FindReplaceWidget, ImportExportMenu, SaveMenu, BatchOCRHandler, ProjectLoader, ManualOCRHandler )
from utils.settings import SettingsDialog
from core.translations import TranslationWindow, import_translation_file_content
from assets.styles import (COLORS, MAIN_STYLESHEET, IV_BUTTON_STYLES, ADVANCED_CHECK_STYLES, RIGHT_WIDGET_STYLES,
                            DEFAULT_TEXT_STYLE, DELETE_ROW_STYLES, get_style_diff)
from assets.styles2 import MANUALOCR_STYLES
import easyocr, os, gc, json, zipfile, math, sys, traceback

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Manhwa OCR Tool")
        self.setGeometry(100, 100, 1200, 600)
        self.settings = QSettings("YourCompany", "MangaOCRTool")
        self._load_filter_settings()
        
        # --- NEW: Profile Management ---
        self.active_profile_name = "Original"
        self.profiles = {"Original": {}} # This will store available profiles

        # Actions are created here
        self.combine_action = QAction("Combine Rows", self)
        # Connection is deferred until after results_widget is created
        self.find_action = QAction("Find/Replace", self)
        self.find_action.triggered.connect(self.toggle_find_widget)
        self.addAction(self.find_action)
        self.update_shortcut()

        self.language_map = {
            "Korean": "ko",
            "Chinese": "ch_sim",
            "Japanese": "ja",
            "Englidh": "en",
            "Indonesian": "id",
        }
        self.original_language = "Korean"
        
        # --- REMOVED Manual OCR state variables ---
        self.next_global_row_number = 0

        self._is_handling_selection = False # Flag to prevent signal loops

        self.init_ui()
        # Connect actions that depend on widgets created in init_ui
        self.combine_action.triggered.connect(self.results_widget.combine_selected_rows)

        self.manual_ocr_handler = ManualOCRHandler(self)

        self.current_image = None
        self.ocr_results = []
        self.image_paths = []
        self.current_image_index = 0
        self.scroll_content = QWidget()
        self.reader = None
        self.ocr_processor = None

        self.start_time = None
        self.processing_times = []
        self.current_progress = 0
        self.target_progress = 0

        self.active_image_label = None
        self.confirm_button = None
        self.current_text_items = []

        self.mmtl_path = None
        self.temp_dir = None
        self.current_selected_row = None
        self.current_selected_image_label = None
        self.selected_text_box_item = None
        if hasattr(self, 'style_panel'):
             self.style_panel.style_changed.connect(self.update_text_box_style)
        self.batch_handler = None # Initialize batch handler to None

    def _load_filter_settings(self):
        self.min_text_height = int(self.settings.value("min_text_height", 40))
        self.max_text_height = int(self.settings.value("max_text_height", 100))
        self.min_confidence = float(self.settings.value("min_confidence", 0.2))
        self.distance_threshold = int(self.settings.value("distance_threshold", 100))
        print(f"Loaded settings: MinH={self.min_text_height}, MaxH={self.max_text_height}, MinConf={self.min_confidence}, DistThr={self.distance_threshold}")

    def init_ui(self):
        self.menuBar = MenuBar(self)
        self.setMenuBar(self.menuBar)
        main_widget = QWidget()
        main_layout = QHBoxLayout()
        self.colors = COLORS
        self.setStyleSheet(MAIN_STYLESHEET)
        # --- NEW: Call to initialize profile selector UI ---
        self.update_profile_selector()

        # Left Panel
        left_panel = QVBoxLayout()
        left_panel.setSpacing(20)

        # --- MODIFIED: Settings and Progress Bar Layout ---
        settings_layout = QHBoxLayout()
        self.btn_settings = QPushButton(qta.icon('fa5s.cog', color='white'), "")
        self.btn_settings.setFixedSize(50, 50)
        self.btn_settings.clicked.connect(self.show_settings_dialog)
        settings_layout.addWidget(self.btn_settings)

        # MOVED: Progress bar is now here, replacing the old save button
        self.ocr_progress = CustomProgressBar()
        self.ocr_progress.setFixedHeight(20)
        settings_layout.addWidget(self.ocr_progress, 1) # Add stretch factor to fill space

        left_panel.addLayout(settings_layout)

        # REMOVED: Old progress layout and save button

        # --- MODIFIED: CustomScrollArea is now self-contained ---
        self.scroll_area = CustomScrollArea(self)
        self.scroll_area.save_requested.connect(self.show_save_menu)

        self.scroll_content = QWidget()
        self.scroll_content.setStyleSheet("background-color: transparent;")
        self.scroll_content.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.scroll_layout = QVBoxLayout(self.scroll_content)
        self.scroll_layout.setContentsMargins(0, 0, 0, 0)
        self.scroll_layout.setSpacing(0)
        self.scroll_area.setWidget(self.scroll_content)
        self.scroll_area.setWidgetResizable(True)
        left_panel.addWidget(self.scroll_area)

        # --- REMOVED: All logic for creating the scroll area overlay and buttons ---
        # This is now handled inside the CustomScrollArea class.

        # Right Panel
        right_panel = QVBoxLayout()
        right_panel.padding = 30
        right_panel.setContentsMargins(20, 20, 20, 20)
        right_panel.setSpacing(20)

        button_layout = QHBoxLayout()
        self.btn_process = QPushButton(qta.icon('fa5s.magic', color='white'), "Process OCR")
        self.btn_process.setFixedWidth(160)
        self.btn_process.clicked.connect(self.start_ocr)
        self.btn_process.setEnabled(False)
        button_layout.addWidget(self.btn_process)
        self.btn_stop_ocr = QPushButton(qta.icon('fa5s.stop', color='white'), "Stop OCR")
        self.btn_stop_ocr.setFixedWidth(160)
        self.btn_stop_ocr.clicked.connect(self.stop_ocr)
        self.btn_stop_ocr.setVisible(False)
        button_layout.addWidget(self.btn_stop_ocr)
        self.btn_manual_ocr = QPushButton(qta.icon('fa5s.crop-alt', color='white'), "Manual OCR")
        self.btn_manual_ocr.setFixedWidth(160)
        self.btn_manual_ocr.setCheckable(True)
        # --- REMOVED CONNECTION (Handled by ManualOCRHandler) ---
        self.btn_manual_ocr.setEnabled(False)
        button_layout.addWidget(self.btn_manual_ocr)
        file_button_layout = QHBoxLayout()
        file_button_layout.setAlignment(Qt.AlignRight)
        file_button_layout.setSpacing(20)
        # --- NEW: Profile Selector Dropdown ---
        self.profile_selector = QComboBox(self)
        self.profile_selector.setFixedWidth(220)
        self.profile_selector.setToolTip("Switch between different text profiles (e.g., Original, User Edits, Translations).")
        self.profile_selector.activated[str].connect(self.switch_active_profile)
        file_button_layout.addWidget(self.profile_selector)
        # --- NEW: Import/Export Menu Button ---
        self.btn_import_export_menu = QPushButton(qta.icon('fa5s.bars', color='white'), "")
        self.btn_import_export_menu.setFixedWidth(60)
        self.btn_import_export_menu.setToolTip("Open Import/Export Menu")
        self.btn_import_export_menu.clicked.connect(self.show_import_export_menu)
        file_button_layout.addWidget(self.btn_import_export_menu)
        button_layout.addLayout(file_button_layout)
        right_panel.addLayout(button_layout)

        self.find_replace_widget = FindReplaceWidget(self)
        right_panel.addWidget(self.find_replace_widget)
        self.find_replace_widget.hide()

        # --- Manual OCR Overlay (UI Definition remains here, logic is in handler) ---
        self.manual_ocr_overlay = QWidget(self)
        self.manual_ocr_overlay.setObjectName("ManualOCROverlay")
        self.manual_ocr_overlay.setStyleSheet(MANUALOCR_STYLES)
        overlay_layout = QVBoxLayout(self.manual_ocr_overlay)
        overlay_layout.setContentsMargins(5, 5, 5, 5)
        overlay_layout.addWidget(QLabel("Selected Area:"))
        overlay_buttons = QHBoxLayout()
        self.btn_ocr_manual_area = QPushButton("OCR This Part")
        overlay_buttons.addWidget(self.btn_ocr_manual_area)
        self.btn_reset_manual_selection = QPushButton("Reset Selection")
        self.btn_reset_manual_selection.setObjectName("ResetButton")
        overlay_buttons.addWidget(self.btn_reset_manual_selection)
        self.btn_cancel_manual_ocr = QPushButton("Cancel Manual OCR")
        self.btn_cancel_manual_ocr.setObjectName("CancelButton")
        overlay_buttons.addWidget(self.btn_cancel_manual_ocr)
        overlay_layout.addLayout(overlay_buttons)
        self.manual_ocr_overlay.setFixedSize(350, 80)
        self.manual_ocr_overlay.hide()

        self.right_content_splitter = QSplitter(Qt.Horizontal)
        self.style_panel = TextBoxStylePanel(default_style=DEFAULT_TEXT_STYLE)
        self.style_panel.hide()
        self.right_content_splitter.addWidget(self.style_panel)

        self.results_widget = ResultsWidget(self, self.combine_action, self.find_action)
        self.results_widget.rowSelected.connect(self.on_result_row_selected)
        self.right_content_splitter.addWidget(self.results_widget)
        self.right_content_splitter.setStretchFactor(0, 0)
        self.right_content_splitter.setStretchFactor(1, 1)
        right_panel.addWidget(self.right_content_splitter, 1)
        self.style_panel_size = None

        bottom_controls_layout = QHBoxLayout()
        self.btn_translate = QPushButton(qta.icon('fa5s.language', color='white'), "AI Translation")
        self.btn_translate.clicked.connect(self.start_translation)
        bottom_controls_layout.addWidget(self.btn_translate)

        self.btn_apply_translation = QPushButton(qta.icon('fa5s.check', color='white'), "Apply Translation")
        self.btn_apply_translation.clicked.connect(self.apply_translation_to_images)
        bottom_controls_layout.addWidget(self.btn_apply_translation)

        self.advanced_mode_check = QCheckBox("Advanced Mode")
        self.advanced_mode_check.setStyleSheet(ADVANCED_CHECK_STYLES)
        self.advanced_mode_check.setChecked(False)
        self.advanced_mode_check.setCursor(Qt.PointingHandCursor)
        self.advanced_mode_check.stateChanged.connect(self.toggle_advanced_mode)
        bottom_controls_layout.addWidget(self.advanced_mode_check)
        right_panel.addLayout(bottom_controls_layout)

        right_widget = QWidget()
        right_widget.setObjectName("RightWidget")
        right_widget.setLayout(right_panel)
        right_widget.setStyleSheet(RIGHT_WIDGET_STYLES)

        splitter = QSplitter(Qt.Horizontal)
        left_widget = QWidget()
        left_widget.setLayout(left_panel)
        splitter.addWidget(left_widget)
        splitter.addWidget(right_widget)

        main_layout.addWidget(splitter)
        main_widget.setLayout(main_layout)
        self.setCentralWidget(main_widget)

    def show_import_export_menu(self):
        """Creates and shows the ImportExportMenu popup."""
        menu = ImportExportMenu(self)
        menu.import_requested.connect(self.import_translation)
        menu.export_requested.connect(self.export_ocr)

        # Position the menu. We want to align its top-right corner
        # with the bottom-right corner of the button that triggered it.
        button = self.sender()
        button_pos = button.mapToGlobal(button.rect().bottomRight())
        
        # Move the menu's top-left corner to (button_x - menu_width, button_y)
        menu_pos = QPoint(button_pos.x() - menu.width(), button_pos.y())
        menu.move(menu_pos)
        
        menu.show()

    def show_save_menu(self, button):
        """Creates and shows the SaveMenu popup, positioned relative to the provided button."""
        menu = SaveMenu(self)
        menu.save_project_requested.connect(self.save_project)
        menu.save_images_requested.connect(self.export_manhwa)

        # Position the menu. We want to align its top-right corner
        # with the bottom-right corner of the button that triggered it.
        button_pos = button.mapToGlobal(button.rect().bottomRight())
        
        # Move the menu's top-left corner to (button_x - menu_width, button_y)
        menu_pos = QPoint(button_pos.x() - menu.width(), button_pos.y())
        menu.move(menu_pos)
        
        menu.show()

    def update_profile_selector(self):
        """Syncs the profile dropdown with the self.profiles dictionary."""
        if not hasattr(self, 'profile_selector'): return # Return if UI not yet initialized
        self.profile_selector.blockSignals(True)
        self.profile_selector.clear()

        # Ensure "Original" is always present and first.
        profiles_list = sorted([p for p in self.profiles.keys() if p != "Original"])
        profiles_list.insert(0, "Original")

        self.profile_selector.addItems(profiles_list)

        if self.active_profile_name in self.profiles:
            index = self.profile_selector.findText(self.active_profile_name)
            if index != -1: self.profile_selector.setCurrentIndex(index)

        self.profile_selector.blockSignals(False)

    def switch_active_profile(self, profile_name):
        """Handles the user selecting a new profile from the dropdown."""
        if profile_name and profile_name in self.profiles and profile_name != self.active_profile_name:
            print(f"Switching to active profile: {profile_name}")
            self.active_profile_name = profile_name
            self.update_all_views()

    def show_settings_dialog(self):
        dialog = SettingsDialog(self)
        if dialog.exec_():
            self._load_filter_settings()
            self.update_shortcut()

    def toggle_find_widget(self):
        if self.find_replace_widget.isVisible():
            self.find_replace_widget.close_widget()
        else:
            self.find_replace_widget.raise_()
            self.find_replace_widget.show()

    def update_find_shortcut(self):
        shortcut = self.settings.value("find_shortcut", "Ctrl+F")
        self.find_action.setShortcut(QKeySequence(shortcut))
        print(f"Find shortcut set to: {shortcut}")

    def process_mmtl(self, mmtl_path, temp_dir):
        """ Processes a .mmtl project by using ProjectLoader and then applying the loaded data to the UI. """
        # --- 1. Load data using the new loader class ---
        loader = ProjectLoader()
        project_data = loader.load_from_directory(mmtl_path, temp_dir)

        # If loading failed, project_data will be None. The loader shows the error.
        if not project_data:
            self.close() # Or handle the empty state appropriately
            return

        # --- 2. Apply the loaded data to the MainWindow's state and UI ---
        # Reset internal state
        self._clear_layout(self.scroll_layout)
        if self.manual_ocr_handler.is_active:
            self.manual_ocr_handler.cancel_mode()

        # Apply data from the data container object
        self.mmtl_path = project_data.mmtl_path
        self.temp_dir = project_data.temp_dir
        self.image_paths = project_data.image_paths
        self.ocr_results = project_data.ocr_results
        self.profiles = {name: {} for name in project_data.profiles} # Convert set to dict format
        self.original_language = project_data.original_language
        self.next_global_row_number = project_data.next_global_row_number
        self.active_profile_name = "Original"

        # Update UI elements
        self.setWindowTitle(f"{project_data.project_name} | ManhwaOCR")
        self.btn_process.setEnabled(bool(self.image_paths))
        self.btn_manual_ocr.setEnabled(bool(self.image_paths))
        self.ocr_progress.setValue(0)
        
        # Populate the image scroll area
        if not self.image_paths:
            QMessageBox.warning(self, "No Images", "The project was loaded, but no images were found inside.")

        for image_path in self.image_paths:
            try:
                 pixmap = QPixmap(image_path)
                 if pixmap.isNull(): continue
                 filename = os.path.basename(image_path)
                 label = ResizableImageLabel(pixmap, filename)
                 label.textBoxDeleted.connect(self.delete_row)
                 label.textBoxSelected.connect(self.handle_text_box_selected)
                 label.manual_area_selected.connect(self.manual_ocr_handler.handle_area_selected)
                 self.scroll_layout.addWidget(label)
            except Exception as e:
                 print(f"Error creating ResizableImageLabel for {image_path}: {e}")

        # --- 3. Trigger final UI updates ---
        self._sort_ocr_results()
        self.update_profile_selector()
        self.update_all_views()
        print(f"Project '{project_data.project_name}' loaded successfully.")
    
    # --- NEW HELPER FUNCTION ---
    def get_display_text(self, result):
        """Gets the text to display based on the active profile."""
        if self.active_profile_name != "Original":
            # Check if the result has a translation for the active profile
            edited_text = result.get('translations', {}).get(self.active_profile_name)
            if edited_text is not None:
                return edited_text
        # Fallback to the original OCR text
        return result.get('text', '')

    def on_result_row_selected(self, row_number):
        """Handles selection from the ResultsWidget."""
        if self._is_handling_selection:
            return  # Prevent recursive loop

        self._is_handling_selection = True
        try:
            target_result, _ = self._find_result_by_row_number(row_number)
            if not target_result:
                return

            filename = target_result.get('filename')
            if not filename:
                return
            
            target_image_label = None
            # Find the image widget corresponding to the result's filename
            for i in range(self.scroll_layout.count()):
                widget = self.scroll_layout.itemAt(i).widget()
                if isinstance(widget, ResizableImageLabel):
                    if widget.filename == filename:
                        target_image_label = widget
                        # Scroll the image into view, positioning it at the top
                        self.scroll_area.verticalScrollBar().setValue(widget.y())
                    else:
                        # Deselect boxes on all other images
                        widget.deselect_all_text_boxes()

            if target_image_label:
                # Tell the found image widget to select the correct text box
                target_image_label.select_text_box(row_number)

        finally:
            self._is_handling_selection = False

    def handle_text_box_selected(self, row_number, image_label, selected):
        if self._is_handling_selection:
            return
        
        self._is_handling_selection = True
        try:
            if selected:
                self.current_selected_row = row_number
                self.current_selected_image_label = image_label
                self.selected_text_box_item = None
                for tb in image_label.get_text_boxes():
                    if tb.row_number == row_number:
                        self.selected_text_box_item = tb
                        break

                if self.selected_text_box_item:
                    current_style = self.get_style_for_row(row_number)
                    self.style_panel.update_style_panel(current_style)
                    self.style_panel.show()
                else:
                    print(f"ERROR: Could not find TextBoxItem for row {row_number} in label {image_label.filename}")
                    self.style_panel.clear_and_hide()

                for i in range(self.scroll_layout.count()):
                    widget = self.scroll_layout.itemAt(i).widget()
                    if isinstance(widget, ResizableImageLabel) and widget != image_label:
                        widget.deselect_all_text_boxes()
                self.results_widget.scroll_to_row(row_number)

            else:
                if row_number == self.current_selected_row and image_label == self.current_selected_image_label:
                    self.current_selected_row = None
                    self.current_selected_image_label = None
                    self.selected_text_box_item = None
                    self.style_panel.clear_and_hide()
        finally:
            self._is_handling_selection = False

    def get_style_for_row(self, row_number):
        style = {}
        for k, v in DEFAULT_TEXT_STYLE.items():
             if k in ['bg_color', 'border_color', 'text_color']:
                 style[k] = QColor(v)
             else:
                 style[k] = v

        target_result, _ = self._find_result_by_row_number(row_number)
        if target_result:
            custom_style = target_result.get('custom_style', {})
            for k, v in custom_style.items():
                 if k in ['bg_color', 'border_color', 'text_color']:
                     style[k] = QColor(v)
                 else:
                     style[k] = v
        return style

    def update_text_box_style(self, new_style_dict):
        if not self.selected_text_box_item:
            print("Style changed but no text box selected.")
            return

        row_number = self.selected_text_box_item.row_number
        target_result, _ = self._find_result_by_row_number(row_number)

        if not target_result:
            print(f"Error: Could not find result for row {row_number} to apply style.")
            return

        if target_result.get('is_deleted', False):
             print(f"Warning: Attempting to style a deleted row ({row_number}). Ignoring.")
             return
        
        style_diff = get_style_diff(new_style_dict, DEFAULT_TEXT_STYLE)

        if style_diff:
            target_result['custom_style'] = style_diff
            print(f"Stored custom style diff for row {row_number}: {style_diff}")
        elif 'custom_style' in target_result:
            del target_result['custom_style']
            print(f"Removed custom style for row {row_number} (back to default).")

        self.selected_text_box_item.apply_styles(new_style_dict)

    def _initialize_ocr_reader(self, context="OCR"):
        """Initializes the EasyOCR reader if it doesn't exist."""
        if self.reader:
            print("EasyOCR reader already initialized.")
            return True
        try:
            lang_code = self.language_map.get(self.original_language, 'ko')
            use_gpu = self.settings.value("use_gpu", "true").lower() == "true"
            print(f"Initializing EasyOCR reader for {context}: Lang='{lang_code}', GPU={use_gpu}")
            self.reader = easyocr.Reader([lang_code], gpu=use_gpu) # Assign to self.reader
            print("EasyOCR reader initialized successfully.")
            return True
        except Exception as e:
            error_msg = f"Failed to initialize OCR reader for {context}: {str(e)}\n\n" \
                        f"Common causes:\n" \
                        f"- Incorrect language code.\n" \
                        f"- Missing EasyOCR models (try running OCR once).\n" \
                        f"- If using GPU: CUDA/driver issues or insufficient VRAM."
            print(f"Error: {error_msg}")
            traceback.print_exc()
            QMessageBox.critical(self, "OCR Initialization Error", error_msg)
            self.reader = None # Ensure reader is None on failure
            return False

    def _find_result_by_row_number(self, row_number_to_find):
        try: target_rn_float = float(row_number_to_find)
        except (ValueError, TypeError): return None, -1
        for index, result in enumerate(self.ocr_results):
            try:
                current_rn_float = float(result.get('row_number', float('nan')))
                if not math.isnan(current_rn_float) and math.isclose(current_rn_float, target_rn_float):
                    return result, index
            except (ValueError, TypeError): continue
        return None, -1

    def _clear_layout(self, layout):
        if layout is not None:
            while layout.count():
                item = layout.takeAt(0)
                widget = item.widget()
                if widget is not None: widget.deleteLater()


    def update_all_views(self, affected_filenames=None):
        """Refreshes all views that depend on the ocr_results data."""
        self.results_widget.update_views()
        self.apply_translation_to_images(affected_filenames)

    def _sort_ocr_results(self):
        try:
             def sort_key(item):
                 try: row_num = float(item.get('row_number', float('inf')))
                 except (ValueError, TypeError): row_num = float('inf')
                 return (item.get('filename', ''), row_num)
             self.ocr_results.sort(key=sort_key)
        except Exception as e:
             print(f"Error during sorting OCR results: {e}. Check row_number values.")
             traceback.print_exc(file=sys.stdout)
             QMessageBox.warning(self, "Sort Error", f"Could not sort OCR results: {e}")

    # --- REWRITTEN: Standard OCR Processing ---
    def start_ocr(self):
        if not self.image_paths:
            QMessageBox.warning(self, "Warning", "No images loaded to process.")
            return
        if self.batch_handler:
            QMessageBox.warning(self, "Warning", "OCR is already running.")
            return
        if self.manual_ocr_handler.is_active:
            QMessageBox.warning(self, "Warning", "Cannot start standard OCR while in Manual OCR mode.")
            return

        print("Starting standard OCR process...")
        if not self._initialize_ocr_reader("Standard OCR"):
            return

        # --- 1. Prepare for the run ---
        self.btn_process.setVisible(False)
        self.btn_stop_ocr.setVisible(True)
        self.ocr_progress.start_initial_progress() # This handles the initial 20% jump

        # Clear previous standard results and determine starting row number
        results_to_keep = [res for res in self.ocr_results if res.get('is_manual', False)]
        self.ocr_results = results_to_keep # Immediately clear old results
        
        starting_row_number = 0
        if results_to_keep:
            max_existing_base = -1
            for res in results_to_keep:
                try: max_existing_base = max(max_existing_base, math.floor(float(res.get('row_number', -1))))
                except: pass
            starting_row_number = max_existing_base + 1
        print(f"Starting standard OCR run. Next global row number will start from: {starting_row_number}")
        
        # --- 2. Gather settings for the handler ---
        self._load_filter_settings()
        ocr_settings = {
            "min_text_height": self.min_text_height, "max_text_height": self.max_text_height,
            "min_confidence": self.min_confidence, "distance_threshold": self.distance_threshold,
            "batch_size": int(self.settings.value("ocr_batch_size", 8)), "decoder": self.settings.value("ocr_decoder", "beamsearch"),
            "adjust_contrast": float(self.settings.value("ocr_adjust_contrast", 0.5)), "resize_threshold": int(self.settings.value("ocr_resize_threshold", 1024)),
        }

        # --- 3. Create, connect, and start the handler ---
        self.batch_handler = BatchOCRHandler(
            self.image_paths, self.reader, ocr_settings, starting_row_number
        )
        self.batch_handler.batch_progress.connect(self.on_batch_progress_updated)
        # --- NEW CONNECTION ---
        self.batch_handler.image_processed.connect(self.on_image_processed)
        self.batch_handler.batch_finished.connect(self.on_batch_finished)
        self.batch_handler.error_occurred.connect(self.on_batch_error)
        self.batch_handler.processing_stopped.connect(self.on_batch_stopped)
        self.batch_handler.start_processing()

    # --- NEW SLOT for incremental updates ---
    def on_image_processed(self, new_results):
        """ Slot to receive results from a single processed image. Updates the model and views incrementally. """
        if not new_results:
            return

        # Append new data to the main list
        self.ocr_results.extend(new_results)
        self._sort_ocr_results()

        # Update the UI. We can optimize by only updating the specific image.
        affected_filename = new_results[0].get('filename')
        self.update_all_views(affected_filenames=[affected_filename] if affected_filename else None)
        print(f"MainWindow: Updated views with results from {affected_filename}")

    # --- NEW: Slots to handle signals from BatchOCRHandler ---
    def on_batch_progress_updated(self, progress):
        """Updates the progress bar based on the handler's overall progress."""
        self.ocr_progress.update_target_progress(progress)
    
    # --- MODIFIED SLOT for the final signal ---
    def on_batch_finished(self, next_row_number):
        """Handles the successful completion of the entire batch."""
        print("MainWindow: Batch finished.")
        self.next_global_row_number = next_row_number # Sync the final count
        # UI views are already up-to-date from the incremental signals.
        self.cleanup_ocr_session()
        QMessageBox.information(self, "Finished", "OCR processing completed for all images.")

    def on_batch_error(self, message):
        """Handles a critical error during the batch process."""
        print(f"MainWindow: Batch error received: {message}")
        self.cleanup_ocr_session()
        QMessageBox.critical(self, "OCR Error", message)

    def on_batch_stopped(self):
        """Handles the UI cleanup after the user manually stops the process."""
        print("MainWindow: Batch processing was stopped by user.")
        self.cleanup_ocr_session()
        QMessageBox.information(self, "Stopped", "OCR processing was stopped.")

    def cleanup_ocr_session(self):
        """Resets UI and state after an OCR run (success, error, or stop)."""
        self.btn_stop_ocr.setVisible(False)
        self.btn_process.setVisible(True)
        self.btn_process.setEnabled(bool(self.image_paths))
        self.ocr_progress.reset()
        if self.batch_handler:
            self.batch_handler.deleteLater() # Ensure proper cleanup of the QObject
            self.batch_handler = None
        gc.collect()
        
    def stop_ocr(self):
        """Stops the currently running OCR process by signaling the handler."""
        print("MainWindow: Sending stop request to batch handler...")
        if self.batch_handler:
            self.batch_handler.stop()
        else:
            print("No active batch handler to stop.")
            # If no handler, but UI is stuck, reset it
            self.cleanup_ocr_session()

    # --- REWRITTEN: handle_error to be a generic error display ---
    def handle_error(self, message):
        """Generic error display. The batch error is handled by on_batch_error."""
        print(f"Error occurred: {message}")
        QMessageBox.critical(self, "Error", message)

    def show_error_message(self, title, message):
        QMessageBox.critical(self, title, message)

    # --- REWRITTEN: update_ocr_text now manages profiles ---
    def update_ocr_text(self, row_number, new_text):
        """Updates the text for a given row number in the active profile."""
        target_result, _ = self._find_result_by_row_number(row_number)
        if not target_result or target_result.get('is_deleted', False):
            return

        # If user is editing while in the "Original" profile, create a new one.
        if self.active_profile_name == "Original":
            new_profile_name = "User Edit 1"
            self.active_profile_name = new_profile_name
            if new_profile_name not in self.profiles:
                self.profiles[new_profile_name] = {}
                self.update_profile_selector()
                QMessageBox.information(self, "Edit Profile Created",
                                        f"First edit detected. A new profile '{new_profile_name}' has been created and set as active. "
                                        "Your original OCR text is preserved.")
                # Future enhancement: Update a profile selector dropdown here.

        # Ensure the 'translations' dictionary exists
        if 'translations' not in target_result:
            target_result['translations'] = {}

        # If the new text is the same as the original, remove it from the profile
        # to keep the data clean.
        original_text = target_result.get('text', '')
        if new_text == original_text:
            if self.active_profile_name in target_result['translations']:
                del target_result['translations'][self.active_profile_name]
                print(f"Row {row_number}: Edit reverted to original. Removed from '{self.active_profile_name}' profile.")
        else:
            # Store the edit in the active profile
            target_result['translations'][self.active_profile_name] = new_text
            print(f"Row {row_number}: Text updated in '{self.active_profile_name}' profile.")


    # --- REWRITTEN: combine_rows_in_model now uses profiles ---
    def combine_rows_in_model(self, first_row_number, combined_text, min_confidence, rows_to_delete):
        """Updates the data model by combining OCR result rows into the active profile."""
        first_result, first_result_index = self._find_result_by_row_number(first_row_number)
        if first_result_index == -1:
            QMessageBox.critical(self, "Error", "Could not find first row to update in data model.")
            return

        # Logic to create a new profile on first edit, same as update_ocr_text
        if self.active_profile_name == "Original":
            new_profile_name = "User Edit 1"
            self.active_profile_name = new_profile_name
            if new_profile_name not in self.profiles:
                self.profiles[new_profile_name] = {}
                self.update_profile_selector()
                QMessageBox.information(self, "Edit Profile Created",
                                        f"First combination edit detected. A new profile '{new_profile_name}' has been created and set as active.")

        # Update confidence on the original record, but store combined text in the profile
        self.ocr_results[first_result_index]['confidence'] = min_confidence
        if 'translations' not in self.ocr_results[first_result_index]:
            self.ocr_results[first_result_index]['translations'] = {}
        self.ocr_results[first_result_index]['translations'][self.active_profile_name] = combined_text

        affected_filenames = {self.ocr_results[first_result_index].get('filename')}
        
        for rn_to_delete in rows_to_delete:
            result_to_delete, delete_index = self._find_result_by_row_number(rn_to_delete)
            if delete_index != -1:
                self.ocr_results[delete_index]['is_deleted'] = True
                affected_filenames.add(result_to_delete.get('filename'))

        if self.find_replace_widget.isVisible():
            self.find_replace_widget.find_text()

        self.update_all_views(affected_filenames=list(filter(None, affected_filenames)))
        QMessageBox.information(self, "Success", f"Combined rows into row {first_row_number} in profile '{self.active_profile_name}'")

    def toggle_advanced_mode(self, state):
        if state:
            self.results_widget.right_content_stack.setCurrentIndex(1)
        else:
            self.results_widget.right_content_stack.setCurrentIndex(0)
        self.results_widget.update_views()

    def delete_row(self, row_number_to_delete):
        target_result, target_index = self._find_result_by_row_number(row_number_to_delete)
        if target_index == -1 or target_result is None or target_result.get('is_deleted', False): return
        show_warning = self.settings.value("show_delete_warning", "true") == "true"
        proceed = True
        if show_warning:
            msg = QMessageBox(self); msg.setIcon(QMessageBox.Warning)
            msg.setWindowTitle("Confirm Deletion Marking"); msg.setText("<b>Mark for Deletion Warning</b>")
            msg.setInformativeText("Mark this entry for deletion? It will be hidden and excluded from exports.")
            msg.setStyleSheet(DELETE_ROW_STYLES)
            dont_show_cb = QCheckBox("Remember choice", msg); msg.setCheckBox(dont_show_cb)
            msg.setStandardButtons(QMessageBox.Yes | QMessageBox.No); msg.setDefaultButton(QMessageBox.No)
            response = msg.exec_()
            if dont_show_cb.isChecked(): self.settings.setValue("show_delete_warning", "false")
            proceed = response == QMessageBox.Yes
        if not proceed: return
        self.ocr_results[target_index]['is_deleted'] = True
        print(f"Marked row {row_number_to_delete} as deleted.")
        deleted_filename = target_result.get('filename')
        if self.find_replace_widget.isVisible(): self.find_replace_widget.find_text()
        if row_number_to_delete == self.current_selected_row:
            self.current_selected_row = None; self.current_selected_image_label = None; self.selected_text_box_item = None
            self.style_panel.clear_and_hide()
        self.update_all_views(affected_filenames=[deleted_filename] if deleted_filename else None)

    def apply_translation_to_images(self, filenames_to_update=None):
        grouped_results = {}
        for result in self.ocr_results:
            filename = result.get('filename')
            row_number = result.get('row_number')
            if filename is None or row_number is None: continue
            if filenames_to_update and filename not in filenames_to_update: continue
            if filename not in grouped_results: grouped_results[filename] = {}
            # --- MODIFIED: Pass the whole result object ---
            grouped_results[filename][row_number] = result
        for i in range(self.scroll_layout.count()):
            widget = self.scroll_layout.itemAt(i).widget()
            if isinstance(widget, ResizableImageLabel):
                image_filename = widget.filename
                if not filenames_to_update or image_filename in filenames_to_update:
                    results_for_this_image = grouped_results.get(image_filename, {})
                    # --- MODIFIED: Pass self to access get_display_text ---
                    widget.apply_translation(self, results_for_this_image, DEFAULT_TEXT_STYLE)

    def update_shortcut(self):
        combine_shortcut = self.settings.value("combine_shortcut", "Ctrl+G")
        self.combine_action.setShortcut(QKeySequence(combine_shortcut))
        self.update_find_shortcut()

    def export_ocr(self):
        export_ocr_results(self)

    def start_translation(self):
        """ Opens the TranslationWindow to handle the online translation process. """
        api_key = self.settings.value("gemini_api_key", "")
        if not api_key:
            QMessageBox.critical(self, "API Key Missing", "Please set your Gemini API key in Settings.")
            return

        if not self.ocr_results:
            QMessageBox.warning(self, "No Data", "There are no OCR results to translate.")
            return
            
        model_name = self.settings.value("gemini_model", "gemini-1.5-flash-latest")

        # Create and execute the modal translation dialog
        dialog = TranslationWindow(
            api_key, model_name, self.ocr_results, list(self.profiles.keys()), self
        )
        dialog.translation_complete.connect(self.handle_translation_completed)
        dialog.exec_() # Blocks until the dialog is closed

    def handle_translation_completed(self, profile_name, translated_data):
        """  Slot to receive the completed translation from TranslationWindow. Applies the new data as a new profile. """
        try:
            unique_profile_name = self._get_unique_profile_name(profile_name)
            self._apply_translation_profile(unique_profile_name, translated_data)
            
            QMessageBox.information(self, "Success", 
                f"Translation successfully applied to new profile:\n'{unique_profile_name}'")

        except Exception as e:
            QMessageBox.critical(self, "Import Error", f"Failed to apply translation: {str(e)}")
            traceback.print_exc()

    def _apply_translation_profile(self, profile_name, translation_data):
        """ Merges a dictionary of translated data into the main ocr_results under a specific profile name. """
        if profile_name in self.profiles:
            print(f"Warning: Overwriting existing profile '{profile_name}'.")
        
        applied_count = 0
        for result in self.ocr_results:
            # Skip deleted results
            if result.get('is_deleted', False):
                continue

            filename = result.get('filename')
            row_number_str = str(result.get('row_number'))

            # Check if a translation exists for this specific result
            if filename in translation_data and row_number_str in translation_data[filename]:
                translated_text = translation_data[filename][row_number_str]
                
                # Ensure the translations dictionary exists
                if 'translations' not in result:
                    result['translations'] = {}
                
                # Store the new text in the specified profile
                result['translations'][profile_name] = translated_text
                applied_count += 1

        print(f"Applied {applied_count} translations to profile '{profile_name}'.")
        
        # Update the main window's state
        self.profiles[profile_name] = {}
        self.active_profile_name = profile_name
        self.update_profile_selector()
        self.update_all_views()

    def _get_unique_profile_name(self, base_name):
        """Ensures the profile name is unique to avoid accidental overwrites."""
        if base_name not in self.profiles:
            return base_name
        
        i = 1
        while True:
            new_name = f"{base_name} ({i})"
            if new_name not in self.profiles:
                return new_name
            i += 1
        
    # --- REWRITTEN to support profiles ---
    def import_translated_content(self, content, profile_name):
        try:
            import_translation_file_content(self, content, profile_name)
            self.active_profile_name = profile_name
            if profile_name not in self.profiles:
                self.profiles[profile_name] = {}
            print(f"Switched to active profile: {profile_name}")
            self.update_all_views()
        except Exception as e:
            raise Exception(f"Failed to import translation content into profile '{profile_name}': {str(e)}")

    def import_translation(self):
        # --- MODIFIED: Use a distinct profile name ---
        profile_name = "Imported Translation"
        if import_translation_file(self, profile_name):
            self.active_profile_name = profile_name
            if profile_name not in self.profiles:
                self.profiles[profile_name] = {}
            print(f"Switched to active profile: {profile_name}")
            self.update_all_views()

    def export_manhwa(self):
        export_rendered_images(self)

    def save_project(self):
        if not self.mmtl_path or not self.temp_dir:
            QMessageBox.warning(self, "Warning", "No project loaded or temporary directory missing. Cannot save.")
            return
        master_path = os.path.join(self.temp_dir, 'master.json')
        try:
            self._sort_ocr_results()
            with open(master_path, 'w', encoding='utf-8') as f:
                # The 'translations' dict is now part of ocr_results, so it's saved automatically
                json.dump(self.ocr_results, f, indent=2, ensure_ascii=False)
            with zipfile.ZipFile(self.mmtl_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for root, dirs, files in os.walk(self.temp_dir):
                    files = [f for f in files if not f.endswith(('.tmp', '.bak'))]
                    dirs[:] = [d for d in dirs if not d.startswith('.')]
                    for file in files:
                        full_path = os.path.join(root, file)
                        rel_path = os.path.relpath(full_path, self.temp_dir).replace(os.sep, '/')
                        zipf.write(full_path, rel_path)
            QMessageBox.information(self, "Saved", f"Project saved successfully to\n{self.mmtl_path}")
        except Exception as e:
             print(f"Save Error: {e}")
             traceback.print_exc()
             QMessageBox.critical(self, "Save Error", f"Failed to save project: {e}")

    def closeEvent(self, event):
        if hasattr(self, 'temp_dir') and self.temp_dir and os.path.exists(self.temp_dir):
            try:
                import shutil
                print(f"Cleaning up temporary directory: {self.temp_dir}")
                shutil.rmtree(self.temp_dir)
            except Exception as e:
                print(f"Warning: Could not remove temporary directory {self.temp_dir}: {e}")
        if self.ocr_processor and self.ocr_processor.isRunning():
            print("Stopping OCR processor on close...")
            self.ocr_processor.stop_requested = True
            self.ocr_processor.wait(500)
            if self.ocr_processor.isRunning():
                 self.ocr_processor.terminate()
        super().closeEvent(event)