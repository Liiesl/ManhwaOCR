from PyQt5.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QSizePolicy, QFrame, QScrollArea, QStackedWidget,
                             QCheckBox, QPushButton, QTableWidget, QTableWidgetItem, QMessageBox, QSplitter, QHeaderView,
                             QAction, QTextEdit, QLabel)
from PyQt5.QtCore import Qt, QSettings, QEvent, QPoint, QBuffer
from PyQt5.QtGui import QPixmap, QKeySequence, QFontMetrics, QColor
import qtawesome as qta
# --- Updated OCRProcessor import ---
from core.ocr_processor import OCRProcessor
from utils.file_io import export_ocr_results, import_translation_file, export_rendered_images
from core.data_processing import group_and_merge_text # Still needed for manual OCR merge
from app.image_area import ResizableImageLabel
from app.ui_widget import CustomProgressBar, MenuBar, CustomScrollArea, TextEditDelegate
from app.custom_bubble import TextBoxStylePanel
from app.find_replace import FindReplaceWidget # <--- IMPORT
from utils.settings import SettingsDialog
from core.translations import TranslationThread, generate_for_translate_content, import_translation_file_content
from assets.styles import (COLORS, MAIN_STYLESHEET, IV_BUTTON_STYLES, ADVANCED_CHECK_STYLES, RIGHT_WIDGET_STYLES, SIMPLE_VIEW_STYLES, DELETE_ROW_STYLES,
                        PROGRESS_STYLES, DEFAULT_TEXT_STYLE, get_style_diff)
import easyocr, os, gc, json, zipfile, math, PIL, io, sys, traceback
import numpy as np
from PIL import Image

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Manhwa OCR Tool")
        self.setGeometry(100, 100, 1200, 600)
        self.settings = QSettings("YourCompany", "MangaOCRTool")
        self._load_filter_settings() # Load settings initially

        self.combine_action = QAction("Combine Rows", self)
        self.combine_action.triggered.connect(self.combine_selected_rows)
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
        self.manual_ocr_mode = False
        self.active_manual_ocr_label = None
        self.manual_selected_rect_scene = None
        self.rubber_band = None
        self.origin_point = None

        self.last_assigned_manual_sub_index = {}
        self.next_global_row_number = 0

        self.init_ui()
        self.current_image = None
        self.ocr_results = []
        self.results_table.cellChanged.connect(self.on_cell_changed)
        self.image_paths = []
        self.current_image_index = 0
        self.scroll_content = QWidget()
        self.reader = None  # EasyOCR reader instance
        self.ocr_processor = None # OCR thread instance

        # Time tracking
        self.start_time = None
        self.processing_times = []
        self.current_progress = 0
        self.target_progress = 0

        self.active_image_label = None
        self.confirm_button = None
        self.current_text_items = []

        self.results_table.installEventFilter(self)

        self.mmtl_path = None
        self.temp_dir = None # Initialize temp_dir
        self.current_selected_row = None
        self.current_selected_image_label = None
        self.selected_text_box_item = None
        if hasattr(self, 'style_panel'):
             self.style_panel.style_changed.connect(self.update_text_box_style)

    def _load_filter_settings(self):
        """Loads OCR filter settings from QSettings."""
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
        self.btn_manual_ocr.clicked.connect(self.toggle_manual_ocr_mode)
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
        self.manual_ocr_overlay.setFixedSize(350, 80)
        self.manual_ocr_overlay.hide()

        self.right_content_splitter = QSplitter(Qt.Horizontal)
        self.style_panel = TextBoxStylePanel(default_style=DEFAULT_TEXT_STYLE)
        self.style_panel.hide()
        self.right_content_splitter.addWidget(self.style_panel)

        self.right_content_stack = QStackedWidget()
        self.results_table = QTableWidget()
        self.results_table.setColumnCount(6)
        self.results_table.setHorizontalHeaderLabels(["Text", "Confidence", "Coordinates", "File", "Row Number", ""])
        self.results_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.results_table.setColumnWidth(1, 50)
        self.results_table.setColumnWidth(2, 50)
        self.results_table.setColumnWidth(3, 50)
        self.results_table.setColumnWidth(4, 50)
        self.results_table.setColumnWidth(5, 50)
        self.results_table.horizontalHeader().setSectionResizeMode(5, QHeaderView.Fixed)
        self.results_table.setContextMenuPolicy(Qt.ActionsContextMenu)
        self.results_table.setWordWrap(True)
        self.results_table.setItemDelegateForColumn(0, TextEditDelegate(self))
        self.results_table.addAction(self.combine_action)
        self.results_table.addAction(self.find_action) # Add find action to table context menu


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

        self.right_content_stack.addWidget(self.simple_scroll)
        self.right_content_stack.addWidget(self.results_table)

        stack_container = QWidget()
        stack_layout = QVBoxLayout(stack_container)
        stack_layout.setContentsMargins(0, 0, 0, 0)
        stack_layout.addWidget(self.right_content_stack)

        self.right_content_splitter.addWidget(stack_container)
        self.right_content_splitter.setStretchFactor(0, 0)
        self.right_content_splitter.setStretchFactor(1, 1)
        right_panel.addWidget(self.right_content_splitter, 1)

        self.style_panel_size = None

        translation_btn_layout = QHBoxLayout()
        self.btn_translate = QPushButton(qta.icon('fa5s.language', color='white'), "Translate")
        self.btn_translate.clicked.connect(self.start_translation)
        translation_btn_layout.addWidget(self.btn_translate)
        self.btn_apply_translation = QPushButton(qta.icon('fa5s.check', color='white'), "Apply Translation")
        self.btn_apply_translation.clicked.connect(self.apply_translation_to_images)
        translation_btn_layout.addWidget(self.btn_apply_translation)
        self.advanced_mode_check = QCheckBox("Advanced Mode")
        self.advanced_mode_check.setStyleSheet(ADVANCED_CHECK_STYLES)
        self.advanced_mode_check.setChecked(False)
        self.advanced_mode_check.setCursor(Qt.PointingHandCursor)
        self.advanced_mode_check.stateChanged.connect(self.toggle_advanced_mode)
        translation_btn_layout.addWidget(self.advanced_mode_check)
        right_panel.addLayout(translation_btn_layout)

        right_widget = QWidget()
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
            self._load_filter_settings() # Reload filter settings
            self.update_shortcut() # Update shortcuts including find

    def toggle_find_widget(self):
        if self.find_replace_widget.isVisible():
            self.find_replace_widget.close_widget()
        else:
            self.find_replace_widget.raise_()
            self.find_replace_widget.show()

    def update_find_shortcut(self):
        """Updates the shortcut for the find action from settings."""
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
                with open(master_path, 'r') as f:
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
                             except (ValueError, TypeError):
                                 print(f"Warning: Skipping invalid row number '{res.get('row_number')}' in loaded data.")
                                 continue
                        else:
                             print(f"Warning: Skipping incomplete result from master.json: {res}")

                    self.ocr_results = valid_results_loaded
                    self.next_global_row_number = max_row_num + 1
                    print(f"Loaded project. Next global row number set to: {self.next_global_row_number}")
            except json.JSONDecodeError:
                QMessageBox.critical(self, "Error", "Failed to load OCR data. Corrupted master.json?")
                self.ocr_results = []
                self.next_global_row_number = 0
            except Exception as e:
                 QMessageBox.critical(self, "Error", f"An unexpected error occurred loading master.json: {e}")
                 self.ocr_results = []
                 self.next_global_row_number = 0

        meta_path = os.path.join(temp_dir, 'meta.json')
        if os.path.exists(meta_path): # Check if meta.json exists
            try:
                with open(meta_path, 'r') as f:
                    meta = json.load(f)
                    self.original_language = meta.get('original_language', 'Korean')
            except (json.JSONDecodeError, FileNotFoundError) as e:
                print(f"Warning: Could not load or parse meta.json: {e}. Using default language.")
                self.original_language = 'Korean'
        else:
             print("Warning: meta.json not found. Using default language 'Korean'.")
             self.original_language = 'Korean'


        if not self.image_paths:
            QMessageBox.warning(self, "Error", "No images found in selected folder")
            return

        self.btn_process.setEnabled(True)
        self.btn_manual_ocr.setEnabled(True)
        self.ocr_progress.setValue(0)

        if self.manual_ocr_mode:
             self.cancel_manual_ocr_mode()

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
                 label.manual_area_selected.connect(self.handle_manual_area_selected)
                 self.scroll_layout.addWidget(label)
            except Exception as e:
                 print(f"Error creating ResizableImageLabel for {image_path}: {e}")

        self._sort_ocr_results()
        self._update_all_views()

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

    # --- Manual OCR Methods ---
    def toggle_manual_ocr_mode(self, checked):
        if checked:
            self.manual_ocr_mode = True
            self.btn_manual_ocr.setText("Cancel Manual OCR")
            self.btn_process.setEnabled(False)

            # Initialize EasyOCR reader if needed (shared instance)
            if self.reader is None:
                if not self._initialize_ocr_reader("Manual OCR"):
                    self.cancel_manual_ocr_mode()
                    return

            if self.ocr_processor and self.ocr_processor.isRunning():
                print("Stopping ongoing standard OCR process to enter manual mode...")
                self.stop_ocr()

            self.btn_stop_ocr.setVisible(False)
            self.manual_ocr_overlay.hide()
            self._clear_manual_selection_state()
            self._set_manual_selection_enabled_on_all(True)
            QMessageBox.information(self, "Manual OCR Mode",
                                    "Click and drag on an image to select an area for OCR.")
        else:
            self.cancel_manual_ocr_mode()

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

    def _clear_manual_selection_state(self):
        self.manual_ocr_overlay.hide()
        self._clear_any_active_selection()
        self.active_manual_ocr_label = None
        self.manual_selected_rect_scene = None

    def cancel_manual_ocr_mode(self):
        print("Cancelling Manual OCR mode...")
        self.manual_ocr_mode = False
        if self.btn_manual_ocr.isChecked():
            self.btn_manual_ocr.setChecked(False)
        self.btn_manual_ocr.setText("Manual OCR")
        self.btn_process.setEnabled(bool(self.image_paths))
        self._clear_manual_selection_state()
        self._set_manual_selection_enabled_on_all(False)
        # Don't release the reader here, it might be needed for standard OCR
        print("Manual OCR mode cancelled.")

    def reset_manual_selection(self):
        self._clear_manual_selection_state()
        if self.manual_ocr_mode:
             self._set_manual_selection_enabled_on_all(True)
             print("Selection reset. Ready for new selection.")
        else:
             print("Selection reset (mode was also exited).")

    def _set_manual_selection_enabled_on_all(self, enabled):
        for i in range(self.scroll_layout.count()):
            widget = self.scroll_layout.itemAt(i).widget()
            if isinstance(widget, ResizableImageLabel):
                widget.set_manual_selection_enabled(enabled)

    def _clear_any_active_selection(self):
        if self.active_manual_ocr_label:
             self.active_manual_ocr_label.clear_active_selection()
        else:
            for i in range(self.scroll_layout.count()):
                widget = self.scroll_layout.itemAt(i).widget()
                if isinstance(widget, ResizableImageLabel):
                    widget.clear_active_selection()

    def handle_manual_area_selected(self, rect_scene, label_widget):
        if not self.manual_ocr_mode:
            print("DEBUG: handle_manual_area_selected called but manual_ocr_mode is False. Ignoring.")
            label_widget.clear_active_selection()
            return

        print(f"Handling completed manual selection from {label_widget.filename}")
        self.manual_selected_rect_scene = rect_scene
        self.active_manual_ocr_label = label_widget
        self._set_manual_selection_enabled_on_all(False) # Disable starting new ones

        try:
            label_pos_in_viewport = label_widget.mapTo(self.scroll_area.viewport(), QPoint(0, 0))
            global_pos = self.scroll_area.viewport().mapToGlobal(label_pos_in_viewport)
            main_window_pos = self.mapFromGlobal(global_pos)
            overlay_x = main_window_pos.x() + (label_widget.width() - self.manual_ocr_overlay.width()) // 2
            overlay_y = main_window_pos.y() + label_widget.height() + 5
            overlay_x = max(0, min(overlay_x, self.width() - self.manual_ocr_overlay.width()))
            overlay_y = max(0, min(overlay_y, self.height() - self.manual_ocr_overlay.height()))
            self.manual_ocr_overlay.move(overlay_x, overlay_y)
            self.manual_ocr_overlay.show()
            self.manual_ocr_overlay.raise_()
            print(f"Manual OCR overlay shown for selection on {label_widget.filename}")
        except Exception as e:
            print(f"Error positioning/showing manual OCR overlay: {e}")
            traceback.print_exc(file=sys.stdout)
            self.reset_manual_selection()

    def process_manual_ocr_area(self):
        """
        Crops the selected area, runs OCR, filters RAW results, merges the
        filtered results, assigns new row numbers, and adds them.
        """
        if not self.manual_selected_rect_scene or not self.active_manual_ocr_label or not self.reader:
            QMessageBox.warning(self, "Error", "No area selected, active label lost, or OCR reader not ready.")
            self.reset_manual_selection()
            return

        print(f"Processing manual OCR for selection on {self.active_manual_ocr_label.filename}")
        self.manual_ocr_overlay.hide()

        try:
            # 1. Get the Crop (same as before)
            crop_rect = self.manual_selected_rect_scene.toRect()
            if crop_rect.width() <= 0 or crop_rect.height() <= 0:
                QMessageBox.warning(self, "Error", "Invalid selection area.")
                self.reset_manual_selection(); return

            pixmap = self.active_manual_ocr_label.original_pixmap
            bounded_crop_rect = crop_rect.intersected(pixmap.rect())
            if bounded_crop_rect.width() <= 0 or bounded_crop_rect.height() <= 0:
                 QMessageBox.warning(self, "Error", "Selection area is outside image bounds.")
                 self.reset_manual_selection(); return

            cropped_pixmap = pixmap.copy(bounded_crop_rect)
            buffer = QBuffer()
            buffer.open(QBuffer.ReadWrite); cropped_pixmap.save(buffer, "PNG")
            pil_image = Image.open(io.BytesIO(buffer.data())).convert('L')
            img_np = np.array(pil_image)

            # 2. Run OCR on the Cropped Area (same as before)
            print(f"Running manual OCR on cropped area: {bounded_crop_rect}")
            batch_size = int(self.settings.value("ocr_batch_size", 1)) # Batch 1 might be fine for manual
            decoder = self.settings.value("ocr_decoder", "beamsearch")
            adjust_contrast = float(self.settings.value("ocr_adjust_contrast", 0.5))

            raw_results_relative = self.reader.readtext(
                img_np, batch_size=batch_size, adjust_contrast=adjust_contrast,
                decoder=decoder, detail=1
            )
            print(f"Manual OCR raw results (relative coords): {raw_results_relative}")

            if not raw_results_relative:
                 QMessageBox.information(self, "Info", "No text found in the selected area.")
                 self.reset_manual_selection(); return

            # --- 3. Pre-filter RAW results BEFORE Merging ---
            temp_results_for_merge = []
            self._load_filter_settings() # Ensure current filter settings are used
            print(f"Pre-filtering {len(raw_results_relative)} raw manual results (MinH={self.min_text_height}, MaxH={self.max_text_height}, MinConf={self.min_confidence})...")

            for (coord_rel, text, confidence) in raw_results_relative:
                # Calculate height of this specific raw detection
                raw_height = 0
                if coord_rel:
                     try:
                         y_coords_rel = [p[1] for p in coord_rel]
                         raw_height = max(y_coords_rel) - min(y_coords_rel) if y_coords_rel else 0
                     except (ValueError, IndexError, TypeError) as coord_err:
                          print(f"Warning: Error calculating raw height for coords {coord_rel}. Skipping filter check. Error: {coord_err}")
                          raw_height = 0 # Treat as failing height filter if calculation fails

                # Apply filtering criteria to the RAW result
                if (self.min_text_height <= raw_height <= self.max_text_height and
                    confidence >= self.min_confidence):
                    temp_results_for_merge.append({
                        'coordinates': coord_rel, # Relative coordinates
                        'text': text,
                        'confidence': confidence,
                        'filename': "manual_crop", # Placeholder needed for merge function
                    })
                else:
                    # Log which raw results are excluded
                    exclusion_reasons = []
                    if not (self.min_text_height <= raw_height <= self.max_text_height):
                         exclusion_reasons.append(f"height {raw_height:.1f}px (bounds: {self.min_text_height}-{self.max_text_height})")
                    if confidence < self.min_confidence:
                        exclusion_reasons.append(f"low confidence ({confidence:.2f} < {self.min_confidence})")
                    if exclusion_reasons:
                         print(f"Excluded RAW manual block ({', '.join(exclusion_reasons)}): '{text[:50]}...'")

            # Check if any results survived the pre-filtering
            if not temp_results_for_merge:
                QMessageBox.information(self, "Info", "No text found in the selected area passed the initial filters.")
                self.reset_manual_selection()
                return

            # --- 4. Merge the PRE-FILTERED Results ---
            # Use distance threshold from settings
            local_distance_threshold = self.distance_threshold
            merged_results_relative = group_and_merge_text(
                temp_results_for_merge, # Pass the pre-filtered list
                distance_threshold=local_distance_threshold
            )
            print(f"Internal merge of pre-filtered results produced {len(merged_results_relative)} final block(s).")

            # --- 5. Process Final MERGED Blocks (NO Filtering Here Anymore) ---
            filename_actual = self.active_manual_ocr_label.filename
            added_rows_info = []
            any_change_made = False
            offset_x = bounded_crop_rect.left()
            offset_y = bounded_crop_rect.top()

            for merged_result in merged_results_relative:
                # Get data from the merged block
                confidence = merged_result['confidence'] # Merged confidence
                coords_relative = merged_result['coordinates'] # Merged coordinates
                text = merged_result['text'] # Merged text

                if not coords_relative: continue # Safety check

                # Convert coordinates to absolute (original image)
                coords_absolute = [[int(p[0] + offset_x), int(p[1] + offset_y)] for p in coords_relative]

                # Calculate new row number based on absolute coordinates
                try:
                    new_row_number = self._calculate_manual_row_number(coords_absolute, filename_actual)
                except Exception as e:
                     print(f"Error calculating row number for manual block '{text[:20]}...': {e}. Skipping.")
                     continue # Skip this block if row number fails

                # Create the final result dictionary to add to self.ocr_results
                # *** No height/confidence filter applied here anymore ***
                final_result = {
                    'coordinates': coords_absolute,
                    'text': text,
                    'confidence': confidence, # Store the merged confidence
                    'filename': filename_actual,
                    'is_manual': True, # Mark as manually added
                    'row_number': new_row_number # Assign calculated number
                }

                # Add to the main list
                self.ocr_results.append(final_result)
                any_change_made = True
                added_rows_info.append({'row': new_row_number, 'text': text})
                print(f"Added final MERGED manual block: Row {new_row_number}, Text: '{text[:20]}...'")

            # --- 6. Sort Results & Update UI (only if changes were made) ---
            if any_change_made:
                 self._sort_ocr_results() # Sort the entire list after adding new blocks
                 self._update_all_views(affected_filenames=[filename_actual])
                 QMessageBox.information(self, "Success", f"Added {len(added_rows_info)} text block(s) from manual selection.")
            # else: # This case covered earlier if temp_results_for_merge was empty
            #      QMessageBox.information(self, "Info", "No text detected or passed filters.")

            # --- 7. Reset state to allow new selection ---
            self.reset_manual_selection()

        except Exception as e:
            print(f"Error during manual OCR processing: {e}")
            traceback.print_exc(file=sys.stdout)
            QMessageBox.critical(self, "Manual OCR Error", f"An unexpected error occurred: {str(e)}")
            # Attempt to reset state even on error
            self.reset_manual_selection()

    def _calculate_manual_row_number(self, coordinates, filename):
        # --- Logic remains the same, depends on self.ocr_results ---
        if not coordinates: return 0.0
        try:
            sort_key_y = min(p[1] for p in coordinates)
        except (ValueError, TypeError, IndexError) as e:
            print(f"Error calculating sort key Y: {e}"); return float('inf')

        preceding_result = None
        for res in self.ocr_results:
            if res.get('is_deleted', False): continue
            res_filename = res.get('filename', '')
            res_coords = res.get('coordinates')
            res_row_number_raw = res.get('row_number')
            if res_row_number_raw is None or res_coords is None: continue

            try: res_sort_key_y = min(p[1] for p in res_coords)
            except: continue

            if res_filename < filename:
                preceding_result = res; continue
            elif res_filename == filename:
                if res_sort_key_y < sort_key_y:
                    preceding_result = res; continue
                else: break
            else: break

        base_row_number = 0
        if preceding_result:
            try:
                preceding_row_num_float = float(preceding_result.get('row_number', 0.0))
                base_row_number = math.floor(preceding_row_num_float)
            except (ValueError, TypeError): base_row_number = 0

        max_sub_index_for_base = 0
        for res in self.ocr_results: # Check all, including deleted, for sub-index calc
             current_row_num_raw = res.get('row_number')
             if current_row_num_raw is None: continue
             try:
                 current_row_num_float = float(current_row_num_raw)
                 if math.floor(current_row_num_float) == base_row_number:
                      epsilon = 1e-9
                      sub_index_float = (current_row_num_float - base_row_number) * 10
                      sub_index = int(sub_index_float + epsilon)
                      if sub_index > 0:
                           max_sub_index_for_base = max(max_sub_index_for_base, sub_index)
             except (ValueError, TypeError): pass

        new_sub_index = max_sub_index_for_base + 1
        new_row_number = float(base_row_number) + (float(new_sub_index) / 10.0)
        return new_row_number

    # --- Helper: Find Result by Row Number ---
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

    # --- Helper: Clear Layout ---
    def _clear_layout(self, layout):
        if layout is not None:
            while layout.count():
                item = layout.takeAt(0)
                widget = item.widget()
                if widget is not None: widget.deleteLater()

    # --- Helper: Update All Views ---
    def _update_all_views(self, affected_filenames=None):
        self.update_results_table() # Updates table and triggers simple view update
        self.apply_translation_to_images(affected_filenames) # Updates image labels

    # --- Helper: Sort OCR Results ---
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
        if self.manual_ocr_mode:
            QMessageBox.warning(self, "Warning", "Cannot start standard OCR while in Manual OCR mode."); return

        print("Starting standard OCR process...")

        # --- Initialize Reader Here (crucial) ---
        if not self._initialize_ocr_reader("Standard OCR"):
             return # Stop if reader initialization fails

        # --- Read settings needed for the processor ---
        self._load_filter_settings() # Load filter settings
        # Merging threshold (passed to processor)
        distance_threshold = self.distance_threshold
        # EasyOCR params (passed to processor)
        batch_size = int(self.settings.value("ocr_batch_size", 8))
        decoder = self.settings.value("ocr_decoder", "beamsearch")
        adjust_contrast = float(self.settings.value("ocr_adjust_contrast", 0.5))
        resize_threshold = int(self.settings.value("ocr_resize_threshold", 1024))

        # --- Reset and Prepare ---
        self.ocr_progress.start_initial_progress()
        self.current_image_index = 0

        # Clear previous *standard* OCR results
        results_to_keep = [res for res in self.ocr_results if res.get('is_manual', False)]
        standard_ocr_results_count = len(self.ocr_results) - len(results_to_keep)
        if standard_ocr_results_count > 0:
            print(f"Clearing {standard_ocr_results_count} previous standard OCR results.")
            self.ocr_results = results_to_keep
            # Don't sort or update UI yet, wait until first results come back

        # Reset global row number based on remaining manual results
        self.next_global_row_number = 0
        if results_to_keep:
             max_existing_base = -1
             for res in results_to_keep:
                  try: max_existing_base = max(max_existing_base, math.floor(float(res.get('row_number', -1))))
                  except: pass
             self.next_global_row_number = max_existing_base + 1
        print(f"Starting standard OCR run. Next global row number set to: {self.next_global_row_number}")

        # --- Start processing ---
        self.process_next_image()

    def process_next_image(self):
        """Creates and starts the OCRProcessor for the next image."""
        if self.current_image_index >= len(self.image_paths):
            print("All images processed.")
            self.finish_ocr_run() # Call dedicated finish method
            return

        if not self.reader:
            QMessageBox.critical(self, "Error", "OCR Reader not available. Cannot process next image.")
            self.stop_ocr() # Stop the process
            return

        self.btn_process.setVisible(False)
        self.btn_stop_ocr.setVisible(True)

        image_path = self.image_paths[self.current_image_index]
        print(f"Processing image {self.current_image_index + 1}/{len(self.image_paths)}: {os.path.basename(image_path)}")

        # --- Reload ALL settings needed by the processor ---
        # It's safer to reload here in case settings changed mid-run, although maybe not ideal UX.
        # Alternatively, pass settings captured in start_ocr. Let's stick with reloading for now.
        self._load_filter_settings()
        batch_size = int(self.settings.value("ocr_batch_size", 8))
        decoder = self.settings.value("ocr_decoder", "beamsearch")
        adjust_contrast = float(self.settings.value("ocr_adjust_contrast", 0.5))
        resize_threshold = int(self.settings.value("ocr_resize_threshold", 1024))

        # --- Create and start the processor THREAD ---
        self.ocr_processor = OCRProcessor(
            image_path=image_path,
            reader=self.reader, # Pass the shared reader instance
            # Filters
            min_text_height=self.min_text_height,
            max_text_height=self.max_text_height,
            min_confidence=self.min_confidence,
            # Merging threshold
            distance_threshold=self.distance_threshold,
            # EasyOCR Params
            batch_size=batch_size,
            decoder=decoder,
            adjust_contrast=adjust_contrast,
            resize_threshold=resize_threshold
        )

        self.ocr_processor.ocr_progress.connect(self.update_ocr_progress_for_image)
        self.ocr_processor.ocr_finished.connect(self.handle_ocr_results) # Connect to the updated handler
        self.ocr_processor.error_occurred.connect(self.handle_error)
        self.ocr_processor.start()

    def update_ocr_progress_for_image(self, progress):
        # --- Logic remains the same ---
        total_images = len(self.image_paths)
        if total_images == 0: return
        per_image_contribution = 80.0 / total_images
        current_image_progress = progress / 100.0
        overall_progress = 20 + (self.current_image_index * per_image_contribution) + (current_image_progress * per_image_contribution)
        self.target_progress = min(int(overall_progress), 100)
        # Could directly call self.ocr_progress.update_target_progress(self.target_progress) here

    def handle_ocr_results(self, processed_results):
        """Receives filtered and merged results from OCRProcessor."""
        if not self.ocr_processor or self.ocr_processor.stop_requested:
            print("Partial results discarded due to stop request or processor issue")
            # Don't automatically stop here, wait for stop_ocr or completion signal
            return

        self.ocr_progress.record_processing_time()

        # Update overall progress bar
        total_images = len(self.image_paths)
        if total_images > 0:
            per_image_contribution = 80.0 / total_images
            overall_progress = 20 + ((self.current_image_index + 1) * per_image_contribution)
            self.ocr_progress.update_target_progress(overall_progress)

        current_image_path = self.image_paths[self.current_image_index]
        filename = os.path.basename(current_image_path)

        # --- Assign Filename and Global Row Numbers ---
        newly_processed_and_numbered_results = []
        if processed_results:
            # Sort vertically *within the results returned for this file* before assigning global numbers
            try:
                processed_results.sort(key=lambda r: min(p[1] for p in r.get('coordinates', [[0, float('inf')]])))
            except (ValueError, TypeError, IndexError) as e:
                print(f"Warning: Could not sort processed results for {filename}: {e}. Using processor order.")

            for result in processed_results:
                result['filename'] = filename # Add filename
                result['row_number'] = self.next_global_row_number # Assign global number
                result['is_manual'] = False # Mark as standard OCR
                newly_processed_and_numbered_results.append(result)
                self.next_global_row_number += 1 # Increment global counter

        # Extend the main results list
        self.ocr_results.extend(newly_processed_and_numbered_results)
        print(f"Processed {filename}: Integrated {len(newly_processed_and_numbered_results)} filtered/merged block(s). Next global row number is now {self.next_global_row_number}")

        # Sort the *entire* list and update views
        self._sort_ocr_results()
        self._update_all_views(affected_filenames=[filename]) # Update UI

        # --- Move to the next image or finish ---
        self.current_image_index += 1

        if self.ocr_processor.stop_requested:
             print("OCR stopped by user after processing image.")
             self.stop_ocr() # Trigger cleanup
        elif self.current_image_index >= len(self.image_paths):
            print("All images processed.")
            self.finish_ocr_run() # Call dedicated finish method
        else:
            # Continue to next image
            self.process_next_image()

    def finish_ocr_run(self):
        """Cleans up after a successful OCR run."""
        print("Finishing OCR run.")
        self.btn_stop_ocr.setVisible(False)
        self.btn_process.setVisible(True)
        self.ocr_progress.update_target_progress(100) # Ensure it hits 100
        # self.reader = None # Keep reader instance for potential manual OCR? Or release? Let's keep it for now.
        self.ocr_processor = None # Release thread instance
        gc.collect()
        QMessageBox.information(self, "Finished", "OCR processing completed for all images.")

    def stop_ocr(self):
        """Stops the currently running OCR process."""
        print("Stopping OCR...")
        if self.ocr_processor and self.ocr_processor.isRunning():
            self.ocr_processor.stop_requested = True
            # Don't wait indefinitely, signal and let handle_ocr_results or finish_ocr_run clean up
            print("Stop request sent to OCR processor.")
        else:
            print("No active OCR processor to stop.")

        # Reset UI and state immediately
        self.ocr_progress.reset()
        self.btn_stop_ocr.setVisible(False)
        self.btn_process.setVisible(True)
        self.btn_process.setEnabled(bool(self.image_paths))

        # Clean up resources potentially (Processor instance cleaned up when thread finishes/in handle_results)
        # self.reader = None # Decide if reader should be released on stop
        self.ocr_processor = None # Clear reference
        gc.collect()
        QMessageBox.information(self, "Stopped", "OCR processing was stopped.")

    def handle_error(self, message):
        """Handles errors emitted by the OCRProcessor thread."""
        print(f"Error occurred during OCR processing: {message}")
        QMessageBox.critical(self, "OCR Error", message)
        # Attempt to clean up state similar to stop_ocr
        self.ocr_progress.reset()
        self.btn_stop_ocr.setVisible(False)
        self.btn_process.setVisible(True)
        self.btn_process.setEnabled(bool(self.image_paths))
        # self.reader = None # Release reader on error? Maybe.
        self.ocr_processor = None
        gc.collect()

    # Add a helper for showing errors if needed by FindReplaceWidget
    def show_error_message(self, title, message):
        QMessageBox.critical(self, title, message)

    # --- UI Update Methods (Table, Simple View, Image Labels) ---

    def toggle_advanced_mode(self, state):
        if state:
            self.right_content_stack.setCurrentIndex(1)  # Table view
            self.update_results_table() # Ensure table is up-to-date
        else:
            self.right_content_stack.setCurrentIndex(0)  # Simple view
            self.update_simple_view() # Ensure simple view is up-to-date

    def update_simple_view(self):
        self._clear_layout(self.simple_scroll_layout)
        visible_results = [res for res in self.ocr_results if not res.get('is_deleted', False)]

        for result in visible_results:
            original_row_number = result['row_number']
            container = QWidget()
            container.setProperty("ocr_row_number", original_row_number)
            container.setObjectName(f"SimpleViewRowContainer_{original_row_number}")
            container_layout = QHBoxLayout(container)
            container_layout.setContentsMargins(5, 5, 5, 5); container_layout.setSpacing(10)
            text_frame = QFrame(); text_frame.setStyleSheet(SIMPLE_VIEW_STYLES)
            text_layout = QVBoxLayout(text_frame); text_layout.setContentsMargins(0, 0, 0, 0)
            text_edit = QTextEdit(result['text']); text_edit.setStyleSheet(SIMPLE_VIEW_STYLES)
            text_edit.setLineWrapMode(QTextEdit.WidgetWidth)
            text_edit.textChanged.connect(lambda rn=original_row_number, te=text_edit: self.on_simple_text_changed(rn, te.toPlainText()))
            text_layout.addWidget(text_edit)
            delete_btn = QPushButton(qta.icon('fa5s.trash-alt', color='red'), "")
            delete_btn.setFixedSize(40, 40); delete_btn.setStyleSheet(DELETE_ROW_STYLES) # Match table style closer
            delete_btn.clicked.connect(lambda _, rn=original_row_number: self.delete_row(rn))
            container_layout.addWidget(text_frame, 1); container_layout.addWidget(delete_btn)
            self.simple_scroll_layout.addWidget(container)

        self.simple_scroll_layout.addStretch()
        if self.find_replace_widget.isVisible(): self.find_replace_widget.find_text()

    def on_simple_text_changed(self, original_row_number, text):
        target_result, _ = self._find_result_by_row_number(original_row_number)
        if target_result:
            if target_result.get('is_deleted', False): return
            if target_result['text'] != text:
                 target_result['text'] = text
                 # Update corresponding table cell if visible
                 self._update_table_cell_if_visible(original_row_number, 0, text)
                 if self.find_replace_widget.isVisible() and self.find_replace_widget.find_input.text():
                     self.find_replace_widget.find_text()
        else:
            print(f"Warning: Could not find result {original_row_number} in on_simple_text_changed")

    def update_results_table(self):
        self.results_table.blockSignals(True)
        visible_results = [res for res in self.ocr_results if not res.get('is_deleted', False)]
        self.results_table.setRowCount(len(visible_results))

        for visible_row_index, result in enumerate(visible_results):
            original_row_number = result['row_number']
            try:
                 rn_float = float(original_row_number)
                 display_row_number = f"{int(rn_float)}" if rn_float.is_integer() else f"{rn_float:.1f}"
            except (ValueError, TypeError): display_row_number = str(original_row_number)

            # Column 0: Text
            text_item = QTableWidgetItem(result['text'])
            text_item.setTextAlignment(Qt.AlignTop | Qt.AlignLeft)
            text_item.setFlags(text_item.flags() | Qt.ItemIsEditable)
            text_item.setData(Qt.UserRole, original_row_number)
            self.results_table.setItem(visible_row_index, 0, text_item)

            # Column 1: Confidence
            conf_val = result.get('confidence', float('nan'))
            conf_str = f"{conf_val:.2f}" if not math.isnan(conf_val) else "N/A"
            confidence_item = QTableWidgetItem(conf_str)
            confidence_item.setTextAlignment(Qt.AlignCenter)
            confidence_item.setFlags(confidence_item.flags() & ~Qt.ItemIsEditable)
            confidence_item.setData(Qt.UserRole, original_row_number)
            self.results_table.setItem(visible_row_index, 1, confidence_item)

            # Column 2: Coordinates
            coord_str = str(result.get('coordinates', 'N/A'))
            coord_item = QTableWidgetItem(coord_str)
            coord_item.setTextAlignment(Qt.AlignCenter)
            coord_item.setFlags(coord_item.flags() & ~Qt.ItemIsEditable)
            coord_item.setData(Qt.UserRole, original_row_number)
            self.results_table.setItem(visible_row_index, 2, coord_item)

            # Column 3: File
            file_item = QTableWidgetItem(result.get('filename', 'N/A'))
            file_item.setTextAlignment(Qt.AlignCenter)
            file_item.setFlags(file_item.flags() & ~Qt.ItemIsEditable)
            file_item.setData(Qt.UserRole, original_row_number)
            self.results_table.setItem(visible_row_index, 3, file_item)

            # Column 4: Row Number
            row_num_display_item = QTableWidgetItem(display_row_number)
            row_num_display_item.setTextAlignment(Qt.AlignCenter)
            row_num_display_item.setFlags(row_num_display_item.flags() & ~Qt.ItemIsEditable)
            row_num_display_item.setData(Qt.UserRole, original_row_number)
            self.results_table.setItem(visible_row_index, 4, row_num_display_item)

            # Column 5: Delete Button
            delete_btn = QPushButton(qta.icon('fa5s.trash-alt', color='red'), "")
            delete_btn.setFixedSize(30, 30) # Smaller button for table
            delete_btn.setStyleSheet(DELETE_ROW_STYLES) # Use specific style if needed
            container = QWidget()
            layout = QHBoxLayout(container); layout.addStretch(); layout.addWidget(delete_btn); layout.setContentsMargins(0, 0, 5, 0) # Align right
            delete_btn.clicked.connect(lambda _, rn=original_row_number: self.delete_row(rn))
            self.results_table.setCellWidget(visible_row_index, 5, container)

        self.adjust_row_heights()
        self.results_table.blockSignals(False)

        # Update simple view ONLY if it's the active view
        if not self.advanced_mode_check.isChecked():
            self.update_simple_view()

    def on_cell_changed(self, row, column):
        item = self.results_table.item(row, column)
        if not item: return
        original_row_number = item.data(Qt.UserRole)
        if original_row_number is None: return

        target_result, _ = self._find_result_by_row_number(original_row_number)
        if not target_result or target_result.get('is_deleted', False): return

        if column == 0:  # Text column
             new_text = item.text()
             if target_result['text'] != new_text:
                 target_result['text'] = new_text
                 # Update simple view if visible
                 self._update_simple_view_text_if_visible(original_row_number, new_text)
                 if self.find_replace_widget.isVisible() and self.find_replace_widget.find_input.text():
                    self.find_replace_widget.find_text()

    def _update_table_cell_if_visible(self, original_row_number, column, new_value):
        """Updates a specific cell in the results table if it's visible."""
        if not self.advanced_mode_check.isChecked(): return # Only if table is visible

        for row in range(self.results_table.rowCount()):
            item = self.results_table.item(row, column)
            if item and item.data(Qt.UserRole) == original_row_number:
                self.results_table.blockSignals(True)
                item.setText(str(new_value))
                self.results_table.blockSignals(False)
                if column == 0: self.adjust_row_heights() # Re-adjust height if text changed
                break

    def _update_simple_view_text_if_visible(self, original_row_number, new_text):
        """Updates the QTextEdit in the simple view if it's visible."""
        if self.advanced_mode_check.isChecked(): return # Only if simple view is visible

        for i in range(self.simple_scroll_layout.count()):
             widget = self.simple_scroll_layout.itemAt(i).widget()
             # Check if it's the container widget we created
             if isinstance(widget, QWidget) and widget.property("ocr_row_number") == original_row_number:
                 # Find the QTextEdit within the container
                 text_edit = widget.findChild(QTextEdit)
                 if text_edit:
                     # Block signals to prevent recursive updates
                     text_edit.blockSignals(True)
                     if text_edit.toPlainText() != new_text: # Avoid unnecessary updates
                         text_edit.setText(new_text)
                     text_edit.blockSignals(False)
                 break # Found the widget, no need to continue loop

    def adjust_row_heights(self):
        # --- Logic remains the same ---
        font_metrics = QFontMetrics(self.results_table.font()) # Use table's default font
        base_padding = 10 # Base padding
        for row in range(self.results_table.rowCount()):
            text_item = self.results_table.item(row, 0)
            if text_item:
                text = text_item.text()
                column_width = self.results_table.columnWidth(0) - 10 # Approx padding/margin
                if column_width > 0:
                    rect = font_metrics.boundingRect(0, 0, column_width, 0, Qt.TextWordWrap, text)
                    required_height = rect.height() + base_padding
                    # Consider button height in last column? Or set a minimum?
                    min_height = 40 # Ensure space for delete button
                    self.results_table.setRowHeight(row, max(required_height, min_height))
            else:
                self.results_table.setRowHeight(row, 40) # Default height for rows without text item?

    def eventFilter(self, obj, event):
        if obj == self.results_table and event.type() == QEvent.Resize:
            self.adjust_row_heights()
        return super().eventFilter(obj, event)

    def delete_row(self, row_number_to_delete):
        target_result, target_index = self._find_result_by_row_number(row_number_to_delete)
        if target_index == -1 or target_result is None or target_result.get('is_deleted', False):
            return # Already deleted or not found

        # --- Confirmation Dialog ---
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

        # --- Mark as deleted ---
        self.ocr_results[target_index]['is_deleted'] = True
        print(f"Marked row {row_number_to_delete} as deleted.")
        deleted_filename = target_result.get('filename')

        if self.find_replace_widget.isVisible(): self.find_replace_widget.find_text() # Refresh find

        # Deselect if it was the currently selected item
        if row_number_to_delete == self.current_selected_row:
            self.current_selected_row = None
            self.current_selected_image_label = None
            self.selected_text_box_item = None
            self.style_panel.clear_and_hide()

        # Update UI (Table/Simple View and Image)
        self._update_all_views(affected_filenames=[deleted_filename] if deleted_filename else None)

    def apply_translation_to_images(self, filenames_to_update=None):
        """Applies OCR results (text, visibility, style) to ResizableImageLabels."""
        grouped_results = {}
        for result in self.ocr_results:
            filename = result.get('filename')
            row_number = result.get('row_number')
            if filename is None or row_number is None: continue
            if filenames_to_update and filename not in filenames_to_update: continue

            if filename not in grouped_results: grouped_results[filename] = {}
            # Pass the whole result dictionary
            grouped_results[filename][row_number] = result

        # Iterate through visual labels
        for i in range(self.scroll_layout.count()):
            widget = self.scroll_layout.itemAt(i).widget()
            if isinstance(widget, ResizableImageLabel):
                image_filename = widget.filename
                if not filenames_to_update or image_filename in filenames_to_update:
                    results_for_this_image = grouped_results.get(image_filename, {})
                    # Pass default style for reference
                    widget.apply_translation(results_for_this_image, DEFAULT_TEXT_STYLE)

    def update_shortcut(self):
        combine_shortcut = self.settings.value("combine_shortcut", "Ctrl+G")
        self.combine_action.setShortcut(QKeySequence(combine_shortcut))
        self.update_find_shortcut() # Update find shortcut as well

    def combine_selected_rows(self):
        selected_ranges = self.results_table.selectedRanges()
        if not selected_ranges: return

        selected_original_row_numbers_raw = set()
        for r in selected_ranges:
            for row in range(r.topRow(), r.bottomRow() + 1):
                item = self.results_table.item(row, 0)
                if item:
                    rn_raw = item.data(Qt.UserRole)
                    if rn_raw is not None: selected_original_row_numbers_raw.add(rn_raw)

        if len(selected_original_row_numbers_raw) < 2: return

        selected_original_row_numbers = []
        for rn_raw in selected_original_row_numbers_raw:
            try: selected_original_row_numbers.append(float(rn_raw))
            except (ValueError, TypeError): QMessageBox.critical(self, "Error", "Invalid row number data."); return
        selected_original_row_numbers.sort()

        selected_results = []; filename_set = set(); contains_float = False
        for rn_float in selected_original_row_numbers:
            result, _ = self._find_result_by_row_number(rn_float)
            if result and not result.get('is_deleted', False):
                selected_results.append(result)
                filename_set.add(result.get('filename'))
                rn_orig = result.get('row_number')
                if isinstance(rn_orig, float) and not rn_orig.is_integer(): contains_float = True
            else: QMessageBox.critical(self, "Error", f"Result {rn_float} not found/deleted."); return

        if len(filename_set) > 1: QMessageBox.warning(self, "Warning", "Cannot combine rows from different files"); return
        if contains_float: QMessageBox.warning(self, "Combine Restriction", "Combining manually added rows (decimal numbers) is not supported yet."); return

        is_adjacent = all(math.isclose(selected_original_row_numbers[i+1] - selected_original_row_numbers[i], 1.0) for i in range(len(selected_original_row_numbers) - 1))
        if not is_adjacent: QMessageBox.warning(self, "Warning", "Selected standard rows must be a contiguous sequence."); return

        selected_results.sort(key=lambda x: float(x.get('row_number', float('inf'))))
        combined_text = [res['text'] for res in selected_results]
        min_confidence = min(res.get('confidence', 0.0) for res in selected_results)

        first_result_to_update = selected_results[0]
        _, first_result_index = self._find_result_by_row_number(first_result_to_update['row_number'])
        if first_result_index != -1:
            self.ocr_results[first_result_index]['text'] = '\n'.join(combined_text)
            self.ocr_results[first_result_index]['confidence'] = min_confidence
            # Combine coordinates? Maybe just keep the first one's for now or calculate bounding box later if needed.
            # self.ocr_results[first_result_index]['coordinates'] = ...
        else: QMessageBox.critical(self, "Error", "Could not find first row to update."); return

        for result_to_delete in selected_results[1:]:
            _, delete_index = self._find_result_by_row_number(result_to_delete['row_number'])
            if delete_index != -1: self.ocr_results[delete_index]['is_deleted'] = True

        if self.find_replace_widget.isVisible(): self.find_replace_widget.find_text()

        target_filename = list(filename_set)[0]
        self._update_all_views(affected_filenames=[target_filename] if target_filename else None)
        QMessageBox.information(self, "Success", f"Combined {len(selected_results)} rows into row {first_result_to_update['row_number']}")


    # --- Export/Import/Save Methods ---
    def export_ocr(self):
        export_ocr_results(self) # Assumes this util function reads self.ocr_results

    def start_translation(self):
        api_key = self.settings.value("gemini_api_key", "")
        model_name = self.settings.value("gemini_model", "gemini-1.5-flash") # Default or from settings
        if not api_key:
            QMessageBox.critical(self, "Error", "Please set Gemini API key in Settings"); return

        content = generate_for_translate_content(self) # Assumes reads self.ocr_results
        if not content.strip():
             QMessageBox.warning(self, "Info", "No text found to translate (check OCR results and filters)."); return

        print("\n===== DEBUG: Content sent to Gemini =====\n")
        print(content)
        print("\n=======================================\n")

        target_lang = self.settings.value("target_language", "English")

        self.translation_progress_dialog = QMessageBox(self)
        self.translation_progress_dialog.setWindowTitle("Translation in Progress")
        self.translation_progress_dialog.setText("Translating content using Gemini API...")
        self.translation_progress_dialog.setIcon(QMessageBox.Information)
        self.translation_progress_dialog.setStandardButtons(QMessageBox.Cancel) # Allow cancellation
        self.translation_progress_dialog.setDetailedText("Waiting for translation stream...")
        self.translation_progress_dialog.show()

        self.translation_thread = TranslationThread(api_key, content, model_name=model_name, target_lang=target_lang)
        # Connect cancel button if the dialog supports it, or handle cancellation via thread stopping
        # if self.translation_progress_dialog.button(QMessageBox.Cancel):
        #      self.translation_progress_dialog.button(QMessageBox.Cancel).clicked.connect(self.cancel_translation)

        self.translation_thread.translation_finished.connect(self.on_translation_finished)
        self.translation_thread.translation_failed.connect(self.on_translation_failed)
        self.translation_thread.debug_print.connect(self.on_debug_print)
        self.translation_thread.translation_progress.connect(self.on_translation_progress)
        self.translation_thread.start()

    # def cancel_translation(self): # Example cancellation
    #     if hasattr(self, 'translation_thread') and self.translation_thread.isRunning():
    #         print("Attempting to stop translation thread...")
    #         # Add a stop mechanism to TranslationThread if possible
    #         # self.translation_thread.requestInterruption() or a custom flag
    #         self.translation_thread.terminate() # Forceful stop (use with caution)
    #         self.on_translation_failed("Translation cancelled by user.")

    def on_translation_progress(self, chunk):
        if hasattr(self, 'translation_progress_dialog') and self.translation_progress_dialog.isVisible():
            current_text = self.translation_progress_dialog.detailedText()
            if current_text == "Waiting for translation stream...": current_text = "" # Clear initial message
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
        print(f"DEBUG (Translation Thread): {debug_message}") # Simpler print

    def import_translated_content(self, content):
        try:
            import_translation_file_content(self, content) # Util updates self.ocr_results
            self._update_all_views() # Refresh UI
        except Exception as e:
            raise Exception(f"Failed to import translation content: {str(e)}")

    def import_translation(self):
        # Calls utility which modifies self.ocr_results and then we update UI
        if import_translation_file(self):
            self._update_all_views()

    def export_manhwa(self):
        export_rendered_images(self) # Assumes reads self.ocr_results and finds labels

    def save_project(self):
        """Saves the project state (master.json) and repackages MMTL."""
        if not self.mmtl_path or not self.temp_dir:
            QMessageBox.warning(self, "Warning", "No project loaded or temporary directory missing. Cannot save.")
            return

        master_path = os.path.join(self.temp_dir, 'master.json')
        try:
            self._sort_ocr_results() # Ensure consistent order before saving
            with open(master_path, 'w') as f:
                # Ensure only serializable data is saved (custom_style should already have strings)
                json.dump(self.ocr_results, f, indent=2)

            # Repackage MMTL
            with zipfile.ZipFile(self.mmtl_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for root, dirs, files in os.walk(self.temp_dir):
                    # Exclude potentially problematic temp files if any exist
                    files = [f for f in files if not f.endswith(('.tmp', '.bak'))]
                    dirs[:] = [d for d in dirs if not d.startswith('.')] # Exclude hidden dirs

                    for file in files:
                        full_path = os.path.join(root, file)
                        # Ensure arcname uses forward slashes for ZIP compatibility
                        rel_path = os.path.relpath(full_path, self.temp_dir).replace(os.sep, '/')
                        zipf.write(full_path, rel_path)

            QMessageBox.information(self, "Saved", f"Project saved successfully to\n{self.mmtl_path}")
        except Exception as e:
             print(f"Save Error: {e}")
             traceback.print_exc()
             QMessageBox.critical(self, "Save Error", f"Failed to save project: {e}")

    def closeEvent(self, event):
        # Optional: Ask to save changes if needed
        # Clean up temp directory
        if hasattr(self, 'temp_dir') and self.temp_dir and os.path.exists(self.temp_dir):
            try:
                import shutil
                print(f"Cleaning up temporary directory: {self.temp_dir}")
                shutil.rmtree(self.temp_dir)
            except Exception as e:
                print(f"Warning: Could not remove temporary directory {self.temp_dir}: {e}")
        # Ensure OCR thread is stopped if running
        if self.ocr_processor and self.ocr_processor.isRunning():
            print("Stopping OCR processor on close...")
            self.ocr_processor.stop_requested = True
            self.ocr_processor.wait(500) # Wait briefly
            if self.ocr_processor.isRunning():
                 self.ocr_processor.terminate() # Force if needed
        super().closeEvent(event)