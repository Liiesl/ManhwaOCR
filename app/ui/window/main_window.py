from PyQt5.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QSizePolicy,
                             QCheckBox, QPushButton,  QMessageBox, QSplitter, QAction, 
                             QLabel, QComboBox)
from PyQt5.QtCore import Qt, QSettings, QPoint
from PyQt5.QtGui import QPixmap, QKeySequence, QColor
import qtawesome as qta
from app.utils.file_io import export_ocr_results, import_translation_file, export_rendered_images
from app.ui.components import ResizableImageLabel, CustomScrollArea, ResultsWidget, TextBoxStylePanel, FindReplaceWidget, ImportExportMenu, SaveMenu, ActionMenu
from app.ui.widgets import CustomProgressBar, MenuBar 
from app.ui.handlers import BatchOCRHandler, ManualOCRHandler, StitchHandler 
# --- MODIFIED IMPORT ---
from app.ui import ProjectModel
from app.ui.dialogs import SettingsDialog
from app.core.translations import import_translation_file_content
from app.ui.window.translation_window import TranslationWindow
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
        
        # --- NEW: Project Model ---
        # The model is the single source of truth for project data.
        self.model = ProjectModel()
        self.model.project_loaded.connect(self.on_project_loaded)
        self.model.project_load_failed.connect(self.on_project_load_failed)
        self.model.model_updated.connect(self.on_model_updated)
        self.model.profiles_updated.connect(self.update_profile_selector)


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
        # --- REMOVED state variables now in the model ---
        # self.active_profile_name, self.profiles, self.ocr_results, self.image_paths, etc.

        self._is_handling_selection = False # Flag to prevent signal loops

        self.init_ui()
        # Connect actions that depend on widgets created in init_ui
        self.combine_action.triggered.connect(self.results_widget.combine_selected_rows)

        self.manual_ocr_handler = ManualOCRHandler(self)
        self.stitch_handler = StitchHandler(self) # --- NEW: Instantiate StitchHandler ---

        self.current_image = None
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
        # ... (UI initialization is mostly unchanged) ...
        # NOTE: self.update_profile_selector() is called here, but the model is empty,
        # so it will correctly show just "Original" initially.
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
        self.scroll_area.action_menu_requested.connect(self.show_action_menu)
        # --- NEW: Connection for stitch handler UI positioning ---
        self.scroll_area.resized.connect(lambda: self.stitch_handler._update_widget_position() if self.stitch_handler.is_active else None)

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


    # ... (show_*_menu methods are unchanged) ...
    def show_import_export_menu(self):
        """Creates and shows the ImportExportMenu popup."""
        menu = ImportExportMenu(self)
        menu.import_requested.connect(self.import_translation)
        menu.export_requested.connect(export_ocr_results)

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

        # Get the global position of the button's top-right corner.
        button_pos = button.mapToGlobal(button.rect().topRight())
        
        # Calculate the menu's top-left position so its bottom-right corner
        # aligns with the button's top-right corner.
        menu_pos = QPoint(button_pos.x() - menu.width(), button_pos.y() - menu.height())
        menu.move(menu_pos)
        
        menu.show()

    def show_action_menu(self, button):
        """Creates and shows the ActionMenu popup, positioned relative to the provided button."""
        menu = ActionMenu(self)
        menu.hide_text_requested.connect(self.hide_text)
        menu.split_images_requested.connect(self.split_images)
        menu.stitch_images_requested.connect(self.stitch_images)

        # Get the global position of the button's top-left corner.
        button_pos = button.mapToGlobal(button.rect().topLeft())
        
        # Calculate the menu's top-left position.
        # X: Align the menu's left edge with the button's left edge.
        # Y: Position the menu's bottom edge at the button's top edge (button_y - menu_height).
        menu_pos = QPoint(button_pos.x(), button_pos.y() - menu.height())
        menu.move(menu_pos)
        
        menu.show()
    
    def hide_text(self):
        return
    def split_images(self):
        return
    def stitch_images(self):
        self.stitch_handler.start_stitching_mode()

    def update_profile_selector(self):
        """Syncs the profile dropdown with the profiles from the model."""
        if not hasattr(self, 'profile_selector'): return
        self.profile_selector.blockSignals(True)
        self.profile_selector.clear()

        profiles_list = sorted([p for p in self.model.profiles.keys() if p != "Original"])
        profiles_list.insert(0, "Original")
        self.profile_selector.addItems(profiles_list)

        if self.model.active_profile_name in self.model.profiles:
            index = self.profile_selector.findText(self.model.active_profile_name)
            if index != -1: self.profile_selector.setCurrentIndex(index)

        self.profile_selector.blockSignals(False)

    def switch_active_profile(self, profile_name):
        """Tells the model to switch the active profile."""
        if profile_name and profile_name in self.model.profiles and profile_name != self.model.active_profile_name:
            print(f"Switching to active profile: {profile_name}")
            self.model.active_profile_name = profile_name
            # An update is needed to show the text from the new profile
            self.on_model_updated(None) # None = full refresh

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
        """ DELEGATED: Asks the model to load the project. """
        self.model.load_project(mmtl_path, temp_dir)

    def on_project_load_failed(self, error_msg):
        """ SLOT: Handles the project_load_failed signal from the model. """
        QMessageBox.critical(self, "Project Load Error", error_msg)
        self.close()

    def on_project_loaded(self):
        """
        SLOT: Handles the project_loaded signal from the model.
        Populates the UI with the newly loaded data.
        """
        self._clear_layout(self.scroll_layout)
        if self.manual_ocr_handler.is_active:
            self.manual_ocr_handler.cancel_mode()

        image_paths = self.model.image_paths
        
        self.setWindowTitle(f"{self.model.project_name} | ManhwaOCR")
        self.btn_process.setEnabled(bool(image_paths))
        self.btn_manual_ocr.setEnabled(bool(image_paths))
        self.ocr_progress.setValue(0)
        
        if not image_paths:
            QMessageBox.warning(self, "No Images", "The project was loaded, but no images were found inside.")

        for image_path in image_paths:
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

        # Trigger final UI updates
        self.update_profile_selector()
        self.on_model_updated(None) # None signifies a full refresh
        print(f"Project '{self.model.project_name}' loaded and UI populated.")
    
    def on_model_updated(self, affected_filenames):
        """ SLOT: Handles the model_updated signal. Refreshes all relevant views. """
        self.update_all_views(affected_filenames)

    def get_display_text(self, result):
        """ DELEGATED: Asks the model for the correct text to display. """
        return self.model.get_display_text(result)

    def on_result_row_selected(self, row_number):
        # ... (This method's logic is largely unchanged, but it now gets data from self.model) ...
        if self._is_handling_selection:
            return

        self._is_handling_selection = True
        try:
            target_result, _ = self.model._find_result_by_row_number(row_number)
            if not target_result:
                return

            filename = target_result.get('filename')
            # ... (the rest of the scrolling and selection logic remains the same) ...
            if not filename:
                return
            
            target_image_label = None
            # Find the image widget corresponding to the result's filename
            for i in range(self.scroll_layout.count()):
                widget = self.scroll_layout.itemAt(i).widget()
                if isinstance(widget, ResizableImageLabel):
                    if widget.filename == filename:
                        target_image_label = widget
                        # SCROLLING LOGIC IS MOVED to after the text box is selected.
                    else:
                        # Deselect boxes on all other images
                        widget.deselect_all_text_boxes()

            if target_image_label:
                # Tell the found image widget to select the correct text box.
                # This now returns the QGraphicsItem for the text box.
                selected_box_item = target_image_label.select_text_box(row_number)

                # --- NEW SCROLL LOGIC to center the selected box if not visible ---
                if selected_box_item:
                    # 1. Get coordinates and dimensions
                    scroll_viewport = self.scroll_area.viewport()
                    viewport_height = scroll_viewport.height()
                    current_scroll_y = self.scroll_area.verticalScrollBar().value()
                    
                    image_label_y_in_scroll = target_image_label.y()
                    
                    # Scene coordinates of the text box
                    box_rect_scene = selected_box_item.sceneBoundingRect()
                    
                    # Scale factor from the QGraphicsView transform
                    scale = target_image_label.transform().m11()
                    
                    # Box position relative to the top of the image label, scaled
                    box_top_in_image = box_rect_scene.top() * scale
                    box_bottom_in_image = box_rect_scene.bottom() * scale
                    box_center_y_in_image = box_rect_scene.center().y() * scale

                    # Box absolute position in the entire scrollable area content
                    box_global_top = image_label_y_in_scroll + box_top_in_image
                    box_global_bottom = image_label_y_in_scroll + box_bottom_in_image

                    # 2. Check if the text box is fully visible in the viewport
                    is_visible = (box_global_top >= current_scroll_y) and \
                                 (box_global_bottom <= current_scroll_y + viewport_height)
                    
                    if not is_visible:
                        # 3. Calculate new scroll position to center the box
                        target_scroll_y = image_label_y_in_scroll + box_center_y_in_image - (viewport_height / 2)
                        
                        # 4. Clamp the value to be within scrollbar's valid range and scroll
                        scrollbar = self.scroll_area.verticalScrollBar()
                        clamped_scroll_y = max(scrollbar.minimum(), min(int(target_scroll_y), scrollbar.maximum()))
                        scrollbar.setValue(clamped_scroll_y)

        finally:
            self._is_handling_selection = False


    # ... (handle_text_box_selected is unchanged) ...
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
        # ... (This method now gets its data from self.model)
        style = {}
        for k, v in DEFAULT_TEXT_STYLE.items():
             if k in ['bg_color', 'border_color', 'text_color']:
                 style[k] = QColor(v)
             else:
                 style[k] = v

        target_result, _ = self.model._find_result_by_row_number(row_number)
        if target_result:
            custom_style = target_result.get('custom_style', {})
            for k, v in custom_style.items():
                 if k in ['bg_color', 'border_color', 'text_color']:
                     style[k] = QColor(v)
                 else:
                     style[k] = v
        return style

    def update_text_box_style(self, new_style_dict):
        # ... (This method now gets its data from self.model)
        if not self.selected_text_box_item:
            print("Style changed but no text box selected.")
            return

        row_number = self.selected_text_box_item.row_number
        target_result, _ = self.model._find_result_by_row_number(row_number)

        if not target_result:
            print(f"Error: Could not find result for row {row_number} to apply style.")
            return

        if target_result.get('is_deleted', False):
             print(f"Warning: Attempting to style a deleted row ({row_number}). Ignoring.")
             return
        
        style_diff = get_style_diff(new_style_dict, DEFAULT_TEXT_STYLE)

        # The model doesn't need to be updated here unless styling is part of the save data
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
            # Get language from the model
            lang_code = self.language_map.get(self.model.original_language, 'ko')
            use_gpu = self.settings.value("use_gpu", "true").lower() == "true"
            print(f"Initializing EasyOCR reader for {context}: Lang='{lang_code}', GPU={use_gpu}")
            self.reader = easyocr.Reader([lang_code], gpu=use_gpu)
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
            self.reader = None
            return False

    def _find_result_by_row_number(self, row_number_to_find):
        """ DELEGATED: Asks the model to find the result. """
        return self.model._find_result_by_row_number(row_number_to_find)

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

    # --- REMOVED _sort_ocr_results, now handled by model ---

    def start_ocr(self):
        if not self.model.image_paths:
            QMessageBox.warning(self, "Warning", "No images loaded to process.")
            return
        # ... (rest of the checks are the same)
        if self.batch_handler:
            QMessageBox.warning(self, "Warning", "OCR is already running.")
            return
        if self.manual_ocr_handler.is_active:
            QMessageBox.warning(self, "Warning", "Cannot start standard OCR while in Manual OCR mode.")
            return

        print("Starting standard OCR process...")
        if not self._initialize_ocr_reader("Standard OCR"):
            return

        self.btn_process.setVisible(False)
        self.btn_stop_ocr.setVisible(True)
        self.ocr_progress.start_initial_progress()

        # DELEGATED: Tell the model to prepare for a new OCR run
        self.model.clear_standard_results()
        self.on_model_updated(None) # Clear visuals of old results
        
        self._load_filter_settings()
        ocr_settings = {
            "min_text_height": self.min_text_height, "max_text_height": self.max_text_height,
            "min_confidence": self.min_confidence, "distance_threshold": self.distance_threshold,
            # ... (other settings are the same)
            "batch_size": int(self.settings.value("ocr_batch_size", 8)), "decoder": self.settings.value("ocr_decoder", "beamsearch"),
            "adjust_contrast": float(self.settings.value("ocr_adjust_contrast", 0.5)), "resize_threshold": int(self.settings.value("ocr_resize_threshold", 1024)),
        }

        self.batch_handler = BatchOCRHandler(
            self.model.image_paths, self.reader, ocr_settings, self.model.next_global_row_number
        )
        self.batch_handler.batch_progress.connect(self.on_batch_progress_updated)
        self.batch_handler.image_processed.connect(self.on_image_processed)
        self.batch_handler.batch_finished.connect(self.on_batch_finished)
        self.batch_handler.error_occurred.connect(self.on_batch_error)
        self.batch_handler.processing_stopped.connect(self.on_batch_stopped)
        self.batch_handler.start_processing()

    def on_image_processed(self, new_results):
        """ DELEGATED: Adds new OCR results to the model. """
        # The model will emit a signal, and on_model_updated will handle the UI refresh.
        self.model.add_new_ocr_results(new_results)

    def on_batch_finished(self, next_row_number):
        """Handles the successful completion of the entire batch."""
        print("MainWindow: Batch finished.")
        self.model.next_global_row_number = next_row_number
        self.cleanup_ocr_session()
        QMessageBox.information(self, "Finished", "OCR processing completed for all images.")

    # ... (Other batch handler slots and cleanup logic are mostly unchanged) ...
    def on_batch_progress_updated(self, progress):
        """Updates the progress bar based on the handler's overall progress."""
        self.ocr_progress.update_target_progress(progress)
    
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
        self.btn_process.setEnabled(bool(self.model.image_paths))
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

    def update_ocr_text(self, row_number, new_text):
        """ DELEGATED: Asks the model to update the text. """
        # The model handles the creation of the "User Edit 1" profile
        if self.model.active_profile_name == "Original":
             QMessageBox.information(self, "Edit Profile Created",
                                     f"First edit detected. A new profile 'User Edit 1' has been created and set as active. "
                                     "Your original OCR text is preserved.")
        self.model.update_text(row_number, new_text)

    def combine_rows_in_model(self, first_row_number, combined_text, min_confidence, rows_to_delete):
        """ DELEGATED: Asks the model to combine rows. """
        if self.model.active_profile_name == "Original":
             QMessageBox.information(self, "Edit Profile Created",
                                     f"First combination edit detected. A new profile 'User Edit 1' has been created and set as active.")
        
        message, success = self.model.combine_rows(first_row_number, combined_text, min_confidence, rows_to_delete)

        if success:
            if self.find_replace_widget.isVisible():
                self.find_replace_widget.find_text()
            QMessageBox.information(self, "Success", message)
        else:
            QMessageBox.critical(self, "Error", message)
    
    def toggle_advanced_mode(self, state):
        if state:
            self.results_widget.right_content_stack.setCurrentIndex(1)
        else:
            self.results_widget.right_content_stack.setCurrentIndex(0)
        self.results_widget.update_views()

    def delete_row(self, row_number_to_delete):
        """ DELEGATED: Asks the model to delete a row after confirming with the user. """
        # Confirmation logic stays in the UI layer
        show_warning = self.settings.value("show_delete_warning", "true") == "true"
        proceed = True
        if show_warning:
            # ... (QMessageBox logic is unchanged)
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

        # Delegate to model
        self.model.delete_row(row_number_to_delete)
        
        # UI-specific cleanup
        if self.find_replace_widget.isVisible(): self.find_replace_widget.find_text()
        if row_number_to_delete == self.current_selected_row:
            self.current_selected_row = None
            self.current_selected_image_label = None
            self.selected_text_box_item = None
            self.style_panel.clear_and_hide()

    def apply_translation_to_images(self, filenames_to_update=None):
        # This method reads from the model but directly manipulates UI widgets, which is correct.
        grouped_results = {}
        for result in self.model.ocr_results: # Read from model
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
                    widget.apply_translation(self, results_for_this_image, DEFAULT_TEXT_STYLE)

    def start_translation(self):
        # ... (unchanged, but reads from self.model.ocr_results) ...
        api_key = self.settings.value("gemini_api_key", "")
        if not api_key:
            QMessageBox.critical(self, "API Key Missing", "Please set your Gemini API key in Settings.")
            return

        if not self.model.ocr_results:
            QMessageBox.warning(self, "No Data", "There are no OCR results to translate.")
            return
            
        model_name = self.settings.value("gemini_model", "gemini-1.5-flash-latest")

        dialog = TranslationWindow(
            api_key, model_name, self.model.ocr_results, list(self.model.profiles.keys()), self
        )
        dialog.translation_complete.connect(self.handle_translation_completed)
        dialog.exec_()

    def handle_translation_completed(self, profile_name, translated_data):
        """ DELEGATED: Asks the model to add the new profile and data. """
        try:
            self.model.add_profile(profile_name, translated_data)
            QMessageBox.information(self, "Success", 
                f"Translation successfully applied to profile:\n'{profile_name}'")
        except Exception as e:
            QMessageBox.critical(self, "Import Error", f"Failed to apply translation: {str(e)}")
            traceback.print_exc()

    def import_translation(self):
        """ DELEGATED: Uses a helper to get content, then asks the model to add it. """
        profile_name = "Imported Translation"
        try:
            # import_translation_file now needs to return content instead of directly acting on the window
            content = import_translation_file(self) # Assuming this is modified to return content
            if content:
                 # We can use the same import logic as the AI translation
                 translation_data = json.loads(content)
                 self.model.add_profile(profile_name, translation_data)
                 # The model signals will trigger the necessary UI updates
        except Exception as e:
            QMessageBox.critical(self, "Import Error", f"Failed to import and apply translation file: {str(e)}")

    def update_shortcut(self):
        combine_shortcut = self.settings.value("combine_shortcut", "Ctrl+G")
        self.combine_action.setShortcut(QKeySequence(combine_shortcut))
        self.update_find_shortcut()

    def export_manhwa(self):
        export_rendered_images(self)

    def save_project(self):
        """ DELEGATED: Asks the model to save the project. """
        result_message = self.model.save_project()
        if "successfully" in result_message:
            QMessageBox.information(self, "Saved", result_message)
        else:
            QMessageBox.critical(self, "Save Error", result_message)

    def closeEvent(self, event):
        # This now reads from self.model
        if hasattr(self.model, 'temp_dir') and self.model.temp_dir and os.path.exists(self.model.temp_dir):
            try:
                import shutil
                print(f"Cleaning up temporary directory: {self.model.temp_dir}")
                shutil.rmtree(self.model.temp_dir)
            except Exception as e:
                print(f"Warning: Could not remove temporary directory {self.model.temp_dir}: {e}")
        # ... (rest of closeEvent is unchanged) ...
        if self.ocr_processor and self.ocr_processor.isRunning():
            print("Stopping OCR processor on close...")
            self.ocr_processor.stop_requested = True
            self.ocr_processor.wait(500)
            if self.ocr_processor.isRunning():
                 self.ocr_processor.terminate()
        super().closeEvent(event)