from PyQt5.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QSizePolicy,
                             QCheckBox, QPushButton,  QMessageBox, QSplitter, QAction, QLabel)
from PyQt5.QtCore import Qt, QSettings
from PyQt5.QtGui import QPixmap, QKeySequence, QColor
import qtawesome as qta
from core.ocr_processor import OCRProcessor
from utils.file_io import export_ocr_results, import_translation_file, export_rendered_images
from app.images.image_area import ResizableImageLabel
from app.ui_widget import CustomProgressBar, MenuBar, CustomScrollArea
from app.results_widget import ResultsWidget
from app.images.custom_bubble import TextBoxStylePanel
from app.find_replace import FindReplaceWidget
from utils.settings import SettingsDialog
from core.translations import TranslationThread, generate_for_translate_content, import_translation_file_content
from assets.styles import (COLORS, MAIN_STYLESHEET, IV_BUTTON_STYLES, ADVANCED_CHECK_STYLES, RIGHT_WIDGET_STYLES,
                            DEFAULT_TEXT_STYLE, DELETE_ROW_STYLES, get_style_diff)
import easyocr, os, gc, json, zipfile, math, sys, traceback
from app.manual_ocr_handler import ManualOCRHandler

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Manhwa OCR Tool")
        self.setGeometry(100, 100, 1200, 600)
        self.settings = QSettings("YourCompany", "MangaOCRTool")
        self._load_filter_settings()

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

        self.init_ui()
        # Connect actions that depend on widgets created in init_ui
        self.combine_action.triggered.connect(self.results_widget.combine_selected_rows)

        # --- NEW: Instantiate Manual OCR Handler ---
        # Done after init_ui so all UI elements exist
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

        # Left Panel
        left_panel = QVBoxLayout()
        left_panel.setSpacing(20)

        settings_layout = QHBoxLayout()
        self.btn_settings = QPushButton(qta.icon('fa5s.cog', color='white'), "")
        self.btn_settings.setFixedSize(50, 50)
        self.btn_settings.clicked.connect(self.show_settings_dialog)
        settings_layout.addWidget(self.btn_settings)

        self.btn_save = QPushButton(qta.icon('fa5s.save', color='white'), "Save Project")
        self.btn_save.clicked.connect(self.save_project)
        settings_layout.addWidget(self.btn_save)
        left_panel.addLayout(settings_layout)

        progress_layout = QVBoxLayout()
        self.ocr_progress = CustomProgressBar()
        self.ocr_progress.setFixedHeight(20)
        progress_layout.addWidget(self.ocr_progress)
        left_panel.addLayout(progress_layout)

        self.scroll_area = CustomScrollArea(None)
        self.scroll_content = QWidget()
        self.scroll_content.setStyleSheet("background-color: transparent;")
        self.scroll_content.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.scroll_layout = QVBoxLayout(self.scroll_content)
        self.scroll_layout.setContentsMargins(0, 0, 0, 0)
        self.scroll_layout.setSpacing(0)
        self.scroll_area.setWidget(self.scroll_content)
        self.scroll_area.setWidgetResizable(True)
        left_panel.addWidget(self.scroll_area)

        scroll_button_overlay = QWidget(self.scroll_area)
        scroll_button_overlay.setObjectName("ScrollButtonOverlay")
        scroll_button_overlay.setStyleSheet("#ScrollButtonOverlay { background-color: transparent; }")
        scroll_button_layout = QHBoxLayout(scroll_button_overlay)
        scroll_button_layout.setContentsMargins(10, 10, 10, 10)
        scroll_button_layout.setSpacing(1)

        self.btn_scroll_top = QPushButton(qta.icon('fa5s.arrow-up', color='white'), "")
        self.btn_scroll_top.setFixedSize(50, 50)
        self.btn_scroll_top.clicked.connect(lambda: self.scroll_area.verticalScrollBar().setValue(0))
        self.btn_scroll_top.setStyleSheet(IV_BUTTON_STYLES)
        scroll_button_layout.addWidget(self.btn_scroll_top)

        self.btn_export_manhwa = QPushButton(qta.icon('fa5s.file-archive', color='white'), "Save")
        self.btn_export_manhwa.setFixedSize(120, 50)
        self.btn_export_manhwa.clicked.connect(self.export_manhwa)
        self.btn_export_manhwa.setStyleSheet(IV_BUTTON_STYLES)
        scroll_button_layout.addWidget(self.btn_export_manhwa)

        self.btn_scroll_bottom = QPushButton(qta.icon('fa5s.arrow-down', color='white'), "")
        self.btn_scroll_bottom.setFixedSize(50, 50)
        self.btn_scroll_bottom.clicked.connect(lambda: self.scroll_area.verticalScrollBar().setValue(self.scroll_area.verticalScrollBar().maximum()))
        self.btn_scroll_bottom.setStyleSheet(IV_BUTTON_STYLES)
        scroll_button_layout.addWidget(self.btn_scroll_bottom)

        self.scroll_area.overlay_widget = scroll_button_overlay
        self.scroll_area.update_overlay_position()
        scroll_button_overlay.raise_()

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

        self.find_replace_widget = FindReplaceWidget(self)
        right_panel.addWidget(self.find_replace_widget)
        self.find_replace_widget.hide()

        # --- Manual OCR Overlay (UI Definition remains here, logic is in handler) ---
        self.manual_ocr_overlay = QWidget(self)
        self.manual_ocr_overlay.setObjectName("ManualOCROverlay")
        self.manual_ocr_overlay.setStyleSheet("""
            #ManualOCROverlay { background-color: rgba(0, 0, 0, 0.7); border-radius: 5px; }
            QPushButton { background-color: #4CAF50; border: none; color: white; padding: 5px 10px; text-align: center; font-size: 14px; margin: 2px; border-radius: 3px; }
            QPushButton:hover { background-color: #45a049; }
            QPushButton#CancelButton { background-color: #f44336; }
            QPushButton#CancelButton:hover { background-color: #da190b; }
            QPushButton#ResetButton { background-color: #ff9800; }
            QPushButton#ResetButton:hover { background-color: #e68a00; }
            QLabel { color: white; font-size: 12px; }
        """)
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
        self.right_content_splitter.addWidget(self.results_widget)
        self.right_content_splitter.setStretchFactor(0, 0)
        self.right_content_splitter.setStretchFactor(1, 1)
        right_panel.addWidget(self.right_content_splitter, 1)
        self.style_panel_size = None

        bottom_controls_layout = QHBoxLayout()
        self.btn_translate = QPushButton(qta.icon('fa5s.language', color='white'), "Translate")
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
        self.mmtl_path = mmtl_path
        project_name = os.path.splitext(os.path.basename(mmtl_path))[0]
        self.setWindowTitle(f"{project_name} | ManhwaOCR")
        self.temp_dir = temp_dir
        self.image_paths = sorted([
            os.path.join(temp_dir, 'images', f)
            for f in os.listdir(os.path.join(temp_dir, 'images'))
            if f.lower().endswith(('png', 'jpg', 'jpeg'))
        ])
        self.ocr_results = []
        self.next_global_row_number = 0
        master_path = os.path.join(temp_dir, 'master.json')
        if os.path.exists(master_path):
            try:
                # --- FIX: Added encoding='utf-8' to handle non-ASCII characters ---
                with open(master_path, 'r', encoding='utf-8') as f:
                    loaded_results = json.load(f)
                    max_row_num = -1
                    valid_results_loaded = []
                    for res in loaded_results:
                        if 'row_number' in res and 'filename' in res and 'coordinates' in res and 'text' in res:
                             try:
                                 row_num_float = float(res['row_number'])
                                 if row_num_float.is_integer() and not res.get('is_deleted', False):
                                     max_row_num = max(max_row_num, int(row_num_float))
                                 valid_results_loaded.append(res)
                             except (ValueError, TypeError): continue
                        else: print(f"Warning: Skipping incomplete result from master.json: {res}")
                    self.ocr_results = valid_results_loaded
                    self.next_global_row_number = max_row_num + 1
                    print(f"Loaded project. Next global row number set to: {self.next_global_row_number}")
            except json.JSONDecodeError: QMessageBox.critical(self, "Error", "Failed to load OCR data. Corrupted master.json?")
            except Exception as e: QMessageBox.critical(self, "Error", f"An unexpected error occurred loading master.json: {e}")
        meta_path = os.path.join(temp_dir, 'meta.json')
        if os.path.exists(meta_path):
            try:
                # --- FIX: Added encoding='utf-8' to handle non-ASCII characters ---
                with open(meta_path, 'r', encoding='utf-8') as f: 
                    meta = json.load(f)
                    self.original_language = meta.get('original_language', 'Korean')
            except (json.JSONDecodeError, FileNotFoundError) as e:
                print(f"Warning: Could not load or parse meta.json: {e}. Using default language.")
        else:
            self.original_language = 'Korean'
        if not self.image_paths: QMessageBox.warning(self, "Error", "No images found in selected folder"); return
        self.btn_process.setEnabled(True)
        self.btn_manual_ocr.setEnabled(True)
        self.ocr_progress.setValue(0)
        # --- MODIFIED: Call manual handler to cancel if active ---
        if self.manual_ocr_handler.is_active:
            self.manual_ocr_handler.cancel_mode()
        self._clear_layout(self.scroll_layout)
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
                 # --- NEW: Connect label signal to the handler ---
                 label.manual_area_selected.connect(self.manual_ocr_handler.handle_area_selected)
                 self.scroll_layout.addWidget(label)
            except Exception as e:
                 print(f"Error creating ResizableImageLabel for {image_path}: {e}")

        self._sort_ocr_results()
        self.update_all_views()

    def handle_text_box_selected(self, row_number, image_label, selected):
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

        else:
            if row_number == self.current_selected_row and image_label == self.current_selected_image_label:
                self.current_selected_row = None
                self.current_selected_image_label = None
                self.selected_text_box_item = None
                self.style_panel.clear_and_hide()

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

        print(f"Applying style to row {row_number}: {new_style_dict}")
        style_diff = get_style_diff(new_style_dict, DEFAULT_TEXT_STYLE)

        if style_diff:
            target_result['custom_style'] = style_diff
            print(f"Stored custom style diff for row {row_number}: {style_diff}")
        elif 'custom_style' in target_result:
            del target_result['custom_style']
            print(f"Removed custom style for row {row_number} (back to default).")

        self.selected_text_box_item.apply_styles(new_style_dict)

    # --- Manual OCR Methods REMOVED (now in ManualOCRHandler) ---

    # --- This method is KEPT as it's shared by standard and manual OCR ---
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

    # --- Renamed from _update_all_views to make its public role clearer ---
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

    # --- Standard OCR Processing ---
    def start_ocr(self):
        if not self.image_paths:
            QMessageBox.warning(self, "Warning", "No images loaded to process."); return
        if self.ocr_processor and self.ocr_processor.isRunning():
            QMessageBox.warning(self, "Warning", "OCR is already running."); return
        # --- MODIFIED: Check manual handler's state ---
        if self.manual_ocr_handler.is_active:
            QMessageBox.warning(self, "Warning", "Cannot start standard OCR while in Manual OCR mode."); return

        print("Starting standard OCR process...")

        if not self._initialize_ocr_reader("Standard OCR"):
             return

        self.ocr_progress.start_initial_progress()
        self.current_image_index = 0

        results_to_keep = [res for res in self.ocr_results if res.get('is_manual', False)]
        standard_ocr_results_count = len(self.ocr_results) - len(results_to_keep)
        if standard_ocr_results_count > 0:
            print(f"Clearing {standard_ocr_results_count} previous standard OCR results.")
            self.ocr_results = results_to_keep

        self.next_global_row_number = 0
        if results_to_keep:
             max_existing_base = -1
             for res in results_to_keep:
                  try: max_existing_base = max(max_existing_base, math.floor(float(res.get('row_number', -1))))
                  except: pass
             self.next_global_row_number = max_existing_base + 1
        print(f"Starting standard OCR run. Next global row number set to: {self.next_global_row_number}")

        self.process_next_image()

    def process_next_image(self):
        """Creates and starts the OCRProcessor for the next image."""
        if self.current_image_index >= len(self.image_paths):
            self.finish_ocr_run()
            return

        if not self.reader:
            QMessageBox.critical(self, "Error", "OCR Reader not available. Cannot process next image.")
            self.stop_ocr()
            return

        self.btn_process.setVisible(False)
        self.btn_stop_ocr.setVisible(True)

        image_path = self.image_paths[self.current_image_index]
        print(f"Processing image {self.current_image_index + 1}/{len(self.image_paths)}: {os.path.basename(image_path)}")

        self._load_filter_settings()
        batch_size = int(self.settings.value("ocr_batch_size", 8))
        decoder = self.settings.value("ocr_decoder", "beamsearch")
        adjust_contrast = float(self.settings.value("ocr_adjust_contrast", 0.5))
        resize_threshold = int(self.settings.value("ocr_resize_threshold", 1024))

        self.ocr_processor = OCRProcessor(
            image_path=image_path, reader=self.reader,
            min_text_height=self.min_text_height, max_text_height=self.max_text_height,
            min_confidence=self.min_confidence, distance_threshold=self.distance_threshold,
            batch_size=batch_size, decoder=decoder,
            adjust_contrast=adjust_contrast, resize_threshold=resize_threshold
        )

        self.ocr_processor.ocr_progress.connect(self.update_ocr_progress_for_image)
        self.ocr_processor.ocr_finished.connect(self.handle_ocr_results)
        self.ocr_processor.error_occurred.connect(self.handle_error)
        self.ocr_processor.start()

    def update_ocr_progress_for_image(self, progress):
        total_images = len(self.image_paths)
        if total_images == 0: return
        per_image_contribution = 80.0 / total_images
        current_image_progress = progress / 100.0
        overall_progress = 20 + (self.current_image_index * per_image_contribution) + (current_image_progress * per_image_contribution)
        self.target_progress = min(int(overall_progress), 100)
        self.ocr_progress.update_target_progress(self.target_progress)

    def handle_ocr_results(self, processed_results):
        """Receives filtered and merged results from OCRProcessor."""
        if not self.ocr_processor or self.ocr_processor.stop_requested:
            print("Partial results discarded due to stop request or processor issue")
            return

        self.ocr_progress.record_processing_time()

        total_images = len(self.image_paths)
        if total_images > 0:
            per_image_contribution = 80.0 / total_images
            overall_progress = 20 + ((self.current_image_index + 1) * per_image_contribution)
            self.ocr_progress.update_target_progress(overall_progress)

        current_image_path = self.image_paths[self.current_image_index]
        filename = os.path.basename(current_image_path)

        newly_processed_and_numbered_results = []
        if processed_results:
            try:
                processed_results.sort(key=lambda r: min(p[1] for p in r.get('coordinates', [[0, float('inf')]])))
            except (ValueError, TypeError, IndexError) as e:
                print(f"Warning: Could not sort processed results for {filename}: {e}. Using processor order.")

            for result in processed_results:
                result['filename'] = filename
                result['row_number'] = self.next_global_row_number
                result['is_manual'] = False
                newly_processed_and_numbered_results.append(result)
                self.next_global_row_number += 1

        self.ocr_results.extend(newly_processed_and_numbered_results)
        print(f"Processed {filename}: Integrated {len(newly_processed_and_numbered_results)} block(s). Next global row is {self.next_global_row_number}")

        self._sort_ocr_results()
        self.update_all_views(affected_filenames=[filename])

        self.current_image_index += 1

        if self.ocr_processor.stop_requested:
             print("OCR stopped by user after processing image.")
             self.stop_ocr()
        elif self.current_image_index >= len(self.image_paths):
            self.finish_ocr_run()
        else:
            self.process_next_image()

    def finish_ocr_run(self):
        """Cleans up after a successful OCR run."""
        print("Finishing OCR run.")
        self.btn_stop_ocr.setVisible(False)
        self.btn_process.setVisible(True)
        self.ocr_progress.update_target_progress(100)
        self.ocr_processor = None
        gc.collect()
        QMessageBox.information(self, "Finished", "OCR processing completed for all images.")

    def stop_ocr(self):
        """Stops the currently running OCR process."""
        print("Stopping OCR...")
        if self.ocr_processor and self.ocr_processor.isRunning():
            self.ocr_processor.stop_requested = True
            print("Stop request sent to OCR processor.")
        else:
            print("No active OCR processor to stop.")

        self.ocr_progress.reset()
        self.btn_stop_ocr.setVisible(False)
        self.btn_process.setVisible(True)
        self.btn_process.setEnabled(bool(self.image_paths))
        self.ocr_processor = None
        gc.collect()
        QMessageBox.information(self, "Stopped", "OCR processing was stopped.")

    def handle_error(self, message):
        """Handles errors emitted by the OCRProcessor thread."""
        print(f"Error occurred during OCR processing: {message}")
        QMessageBox.critical(self, "OCR Error", message)
        self.ocr_progress.reset()
        self.btn_stop_ocr.setVisible(False)
        self.btn_process.setVisible(True)
        self.btn_process.setEnabled(bool(self.image_paths))
        self.ocr_processor = None
        gc.collect()

    def show_error_message(self, title, message):
        QMessageBox.critical(self, title, message)

    def update_ocr_text(self, row_number, new_text):
        """Updates the text for a given row number in the main data model."""
        target_result, _ = self._find_result_by_row_number(row_number)
        if target_result and target_result.get('text') != new_text:
            if not target_result.get('is_deleted', False):
                target_result['text'] = new_text

    def combine_rows_in_model(self, first_row_number, combined_text, min_confidence, rows_to_delete):
        """Updates the data model by combining OCR result rows."""
        _, first_result_index = self._find_result_by_row_number(first_row_number)
        if first_result_index == -1:
            QMessageBox.critical(self, "Error", "Could not find first row to update in data model.")
            return

        self.ocr_results[first_result_index]['text'] = combined_text
        self.ocr_results[first_result_index]['confidence'] = min_confidence
        affected_filenames = {self.ocr_results[first_result_index].get('filename')}

        for rn_to_delete in rows_to_delete:
            result_to_delete, delete_index = self._find_result_by_row_number(rn_to_delete)
            if delete_index != -1:
                self.ocr_results[delete_index]['is_deleted'] = True
                affected_filenames.add(result_to_delete.get('filename'))

        if self.find_replace_widget.isVisible():
            self.find_replace_widget.find_text()

        self.update_all_views(affected_filenames=list(filter(None, affected_filenames)))
        QMessageBox.information(self, "Success", f"Combined rows into row {first_row_number}")

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
            grouped_results[filename][row_number] = result
        for i in range(self.scroll_layout.count()):
            widget = self.scroll_layout.itemAt(i).widget()
            if isinstance(widget, ResizableImageLabel):
                image_filename = widget.filename
                if not filenames_to_update or image_filename in filenames_to_update:
                    results_for_this_image = grouped_results.get(image_filename, {})
                    widget.apply_translation(results_for_this_image, DEFAULT_TEXT_STYLE)

    def update_shortcut(self):
        combine_shortcut = self.settings.value("combine_shortcut", "Ctrl+G")
        self.combine_action.setShortcut(QKeySequence(combine_shortcut))
        self.update_find_shortcut()

    def export_ocr(self):
        export_ocr_results(self)

    def start_translation(self):
        api_key = self.settings.value("gemini_api_key", "")
        model_name = self.settings.value("gemini_model", "gemini-2.5-flash-preview-04-17")
        if not api_key:
            QMessageBox.critical(self, "Error", "Please set Gemini API key in Settings"); return
        content = generate_for_translate_content(self)
        if not content.strip():
             QMessageBox.warning(self, "Info", "No text found to translate (check OCR results and filters)."); return
        print("\n===== DEBUG: Content sent to Gemini =====\n"); print(content); print("\n=======================================\n")
        target_lang = self.settings.value("target_language", "English")
        self.translation_progress_dialog = QMessageBox(self)
        self.translation_progress_dialog.setWindowTitle("Translation in Progress")
        self.translation_progress_dialog.setText("Translating content using Gemini API...")
        self.translation_progress_dialog.setIcon(QMessageBox.Information)
        self.translation_progress_dialog.setStandardButtons(QMessageBox.Cancel)
        self.translation_progress_dialog.setDetailedText("Waiting for translation stream...")
        self.translation_progress_dialog.show()
        self.translation_thread = TranslationThread(api_key, content, model_name=model_name, target_lang=target_lang)
        self.translation_thread.translation_finished.connect(self.on_translation_finished)
        self.translation_thread.translation_failed.connect(self.on_translation_failed)
        self.translation_thread.debug_print.connect(self.on_debug_print)
        self.translation_thread.translation_progress.connect(self.on_translation_progress)
        self.translation_thread.start()

    def on_translation_progress(self, chunk):
        if hasattr(self, 'translation_progress_dialog') and self.translation_progress_dialog.isVisible():
            current_text = self.translation_progress_dialog.detailedText()
            if current_text == "Waiting for translation stream...": current_text = ""
            self.translation_progress_dialog.setDetailedText(current_text + chunk)

    def on_translation_finished(self, translated_text):
        if hasattr(self, 'translation_progress_dialog') and self.translation_progress_dialog.isVisible():
            self.translation_progress_dialog.accept()
        try:
            self.import_translated_content(translated_text)
            QMessageBox.information(self, "Success", "Translation completed successfully!")
        except Exception as e:
            QMessageBox.critical(self, "Import Error", f"Failed to apply translation: {str(e)}")

    def on_translation_failed(self, error_message):
        if hasattr(self, 'translation_progress_dialog') and self.translation_progress_dialog.isVisible():
            self.translation_progress_dialog.accept()
        QMessageBox.critical(self, "Translation Error", error_message)

    def on_debug_print(self, debug_message):
        print(f"DEBUG (Translation Thread): {debug_message}")

    def import_translated_content(self, content):
        try:
            import_translation_file_content(self, content)
            self.update_all_views()
        except Exception as e:
            raise Exception(f"Failed to import translation content: {str(e)}")

    def import_translation(self):
        if import_translation_file(self):
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