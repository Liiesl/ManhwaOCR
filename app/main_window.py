from PyQt5.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QFileDialog, QLabel, QProgressBar, QTableWidget, QTableWidgetItem, QMessageBox, QSplitter, QHeaderView, QAction
from PyQt5.QtCore import Qt, pyqtSignal, QDateTime, QTimer, QSettings
from PyQt5.QtGui import QPixmap, QKeySequence
import qtawesome as qta
from core.ocr_processor import OCRProcessor
from utils.file_io import export_ocr_results, import_translation_file
from core.data_processing import group_and_merge_text
from app.widgets import ResizableImageLabel, CustomScrollArea
from utils.settings import SettingsDialog
from core.translations import translate_with_gemini
import easyocr
import os
import gc

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Manga OCR Tool")
        self.setGeometry(100, 100, 1200, 600)
        self.settings = QSettings("YourCompany", "MangaOCRTool")
        self.min_text_area = int(self.settings.value("min_text_area", 4000))
        self.distance_threshold = int(self.settings.value("distance_threshold", 100))
        self.combine_action = QAction("Combine Rows", self)
        self.combine_action.triggered.connect(self.combine_selected_rows)
        self.update_shortcut()
        
        self.init_ui()
        self.current_image = None
        self.ocr_results = []
        self.results_table.cellChanged.connect(self.on_cell_changed)
        self.image_paths = []
        self.current_image_index = 0
        self.scroll_content = QWidget()
        self.reader = None
        self.ocr_processor = None

        # Add a timer for smooth progress updates
        self.progress_timer = QTimer(self)
        self.progress_timer.timeout.connect(self.update_progress_smoothly)
        
        # Variables for time tracking
        self.start_time = None
        self.processing_times = []
        self.current_progress = 0
        self.target_progress = 0

    def init_ui(self):
        # Set the main widget and layout
        main_widget = QWidget()
        main_layout = QHBoxLayout()  # Main horizontal layout

        self.colors = {
        "background": "#1E1E1E",
        "surface": "#2D2D2D",
        "primary": "#3A3A3A",
        "secondary": "#4A4A4A",
        "accent": "#007ACC",
        "text": "#FFFFFF"
        }

        # Apply global stylesheet for the application
        self.setStyleSheet("""
            /* General background color */
            QMainWindow, QWidget {
                background-color: #1A1A1A;
                color: #FFFFFF;
                font-size: 20px;
            }
            /* Buttons style */
            QPushButton {
                background-color: #3A3A3A;
                color: #FFFFFF;
                border: none;
                padding: 10px;
                border-radius: 20px; 
            }
            QPushButton:hover {
                background-color: #4A4A4A;
            }
            QPushButton:pressed {
                background-color: #2A2A2A;
            }
                           
            /* Table styling */
            QTableWidget {
                background-color: #2D2D2D;
                gridline-color: "#3A3A3A";
                border-radius: 50px;
            }
            QHeaderView::section {
                background-color: "#3A3A3A";
                padding: 12px;
                border: none;
            }
            QTableWidget::item {
                padding: 2px;
            }
            QTableWidget::item.column-6 {  /* Target the 7th column (index 6) */
                background-color: transparent;
                border: none;
            }
            
            /* Ensure table buttons use the same style */
            QTableWidget QPushButton {
                background-color: #3A3A3A;
                color: #FFFFFF;
                border: none;
                padding: 10px;
                border-radius: 20px;
            }
            QTableWidget QPushButton:hover {
                background-color: #4A4A4A;
            }
            QTableWidget QPushButton:pressed {
                background-color: #2A2A2A;
            }
                           
            /* Scroll area style */
            QScrollArea {
                border: 20px solid #2A2A2A; /* Solid color border */
                border-top-right-radius: 50px; /* Rounded top-right corner */
                background-color: #2A2A2A; /* Background color */
            }
                           
            QScrollArea > QWidget > QWidget {  /* Target the viewport */
                background: transparent;
            }
                           
            /* Progress bar style */
            QProgressBar {
                background-color: #2A2A2A;
                color: #FFFFFF;
                border: 1px solid #3A3A3A;
                border-radius: 5px;
                text-align: center;
            }
            QProgressBar::chunk {
                background-color: #4A4A4A;
                width: 10px;
            }
            
            /* Tab Widget style */
            QTabWidget {
                background-color: #1A1A1A;
                border: none;
            }
            QTabWidget::pane {
                border: 1px solid #3A3A3A;
                border-radius: 10px;
                background-color: #2D2D2D;
            }
            QTabBar::tab {
                background-color: #3A3A3A;
                color: #FFFFFF;
                padding: 10px;
                border: none;
                border-radius: 5px;
            }
            QTabBar::tab:selected {
                background-color: #4A4A4A;
                margin-bottom: -1px; /* Ensure selected tab appears above the pane border */
            }
            QTabBar::tab:!selected {
                margin-top: 2px; /* Add some spacing between unselected tabs and the pane */
            }

            QSplitter {
                width: 30px;
            }
            
            QTableWidget {
                background-color: #1A1A1A;
            }
        """)

        # Left Panel
        left_panel = QVBoxLayout()  # Vertical layout for the left panel
        left_panel.setSpacing(20)

        # Open Folder Button
        settings_layout = QHBoxLayout()

        self.btn_settings = QPushButton(qta.icon('fa5s.cog', color='white'), "")
        self.btn_settings.setFixedSize(50, 50)
        self.btn_settings.clicked.connect(self.show_settings_dialog)
        settings_layout.addWidget(self.btn_settings)

        self.btn_open = QPushButton(qta.icon('fa5s.folder-open', color='white'), "Open Folder")
        self.btn_open.clicked.connect(self.open_folder)
        settings_layout.addWidget(self.btn_open)

        left_panel.addLayout(settings_layout)

        # Progress bars in their own row
        progress_layout = QVBoxLayout()
        self.ocr_progress = QProgressBar()
        self.ocr_progress.setFixedHeight(20)
        progress_layout.addWidget(self.ocr_progress)
        left_panel.addLayout(progress_layout)

        # Scroll Area
        self.scroll_area = CustomScrollArea(None)  # Initialize with None, will be set later
        self.scroll_content = QWidget()
        self.scroll_content.setStyleSheet("background-color: transparent;")  # Add this line
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
        self.btn_scroll_top.setStyleSheet("""
            QPushButton {
                background-color: #3A3A3A;
                border: none;
                border-radius: 25px; 
            }
            QPushButton:hover {
                background-color: #4A4A4A;
            }
            QPushButton:pressed {
                background-color: #2A2A2A;
            }
        """)
        scroll_button_layout.addWidget(self.btn_scroll_top)

        # Export Manhwa Button
        self.btn_export_manhwa = QPushButton(qta.icon('fa5s.file-archive', color='white'), "Save")
        self.btn_export_manhwa.setFixedSize(120, 50)  # Set fixed size for the button
        self.btn_export_manhwa.clicked.connect(self.export_manhwa)
        self.btn_export_manhwa.setStyleSheet("""
            QPushButton {
                background-color: #3A3A3A;
                color: #FFFFFF;
                border: none;
                border-radius: 25px; 
                padding: 10px;
            }
            QPushButton:hover {
                background-color: #4A4A4A;
            }
            QPushButton:pressed {
                background-color: #2A2A2A;
            }
        """)
        scroll_button_layout.addWidget(self.btn_export_manhwa)  # Add the button to the layout

        # Scroll Bottom Button
        self.btn_scroll_bottom = QPushButton(qta.icon('fa5s.arrow-down', color='white'), "")
        self.btn_scroll_bottom.setFixedSize(50, 50)  # Set fixed size for the button
        self.btn_scroll_bottom.clicked.connect(lambda: self.scroll_area.verticalScrollBar().setValue(self.scroll_area.verticalScrollBar().maximum()))
        self.btn_scroll_bottom.setStyleSheet("""
            QPushButton {
                background-color: #3A3A3A;
                border: none;
                border-radius: 25px; 
            }
            QPushButton:hover {
                background-color: #4A4A4A;
            }
            QPushButton:pressed {
                background-color: #2A2A2A;
            }
        """)
        scroll_button_layout.addWidget(self.btn_scroll_bottom)

        # Set the overlay widget to the custom scroll area
        self.scroll_area.overlay_widget = scroll_button_overlay

        # Position the overlay inside the scroll area
        self.scroll_area.update_overlay_position()
        scroll_button_overlay.raise_()  # Ensure the overlay is on top of other widgets

        # Right Panel
        right_panel = QVBoxLayout()  # Vertical layout for the right panel
        right_panel.setContentsMargins(20, 20, 20, 20)
        right_panel.setSpacing(20)

        # Top Row Buttons
        button_layout = QHBoxLayout()  # Horizontal layout for top row buttons
        button_layout.setSpacing(10)
        self.btn_process = QPushButton(qta.icon('fa5s.magic', color='white'), "Process OCR")
        self.btn_process.clicked.connect(self.start_ocr)
        self.btn_process.setEnabled(False)
        button_layout.addWidget(self.btn_process)
        self.btn_stop_ocr = QPushButton(qta.icon('fa5s.stop', color='white'), "Stop OCR")
        self.btn_stop_ocr.clicked.connect(self.stop_ocr)
        self.btn_stop_ocr.setVisible(False)  # Initially disabled
        button_layout.addWidget(self.btn_stop_ocr)
        self.btn_import_translation = QPushButton(qta.icon('fa5s.file-import', color='white'), "Import Translation")
        self.btn_import_translation.clicked.connect(self.import_translation)
        button_layout.addWidget(self.btn_import_translation)
        self.btn_export_ocr = QPushButton(qta.icon('fa5s.file-export', color='white'), "Export OCR")
        self.btn_export_ocr.clicked.connect(self.export_ocr)
        button_layout.addWidget(self.btn_export_ocr)
        right_panel.addLayout(button_layout)

        # OCR Results Table
        self.results_table = QTableWidget()
        self.results_table.setColumnCount(7)
        self.results_table.setHorizontalHeaderLabels(["Text", "Confidence", "Coordinates", "File", "Line Counts", "Row Number", ""])
        # Set column width after creating the table
        self.results_table.setColumnWidth(1, 50)
        self.results_table.setColumnWidth(2, 50)
        self.results_table.setColumnWidth(3, 50)
        self.results_table.setColumnWidth(5, 50)
        self.results_table.setColumnWidth(6, 50)
        self.results_table.horizontalHeader().setSectionResizeMode(6, QHeaderView.Fixed)
        self.results_table.setContextMenuPolicy(Qt.ActionsContextMenu)
        self.results_table.addAction(self.combine_action)
        right_panel.addWidget(self.results_table)

        # Modify translation button layout
        translation_btn_layout = QHBoxLayout()
        
        self.btn_translate = QPushButton(qta.icon('fa5s.language', color='white'), "Translate")
        self.btn_translate.clicked.connect(self.start_translation)
        translation_btn_layout.addWidget(self.btn_translate)
        
        self.btn_apply_translation = QPushButton(qta.icon('fa5s.check', color='white'), "Apply Translation")
        self.btn_apply_translation.clicked.connect(self.apply_translation)
        translation_btn_layout.addWidget(self.btn_apply_translation)
        
        right_panel.addLayout(translation_btn_layout)

        # Create the right widget and apply specific styles
        right_widget = QWidget()
        right_widget.setLayout(right_panel)
        right_widget.setStyleSheet("""
            QWidget {
                background-color: #2A2A2A;
                border: none;
                border-top-left-radius: 50px; /* Rounded top-left corner */
            }
            /* Buttons style */
            QPushButton {
                background-color: #3A3A3A;
                color: #FFFFFF;
                border: none;
                padding: 10px;
                border-radius: 20px; 
            }
            QPushButton:hover {
                background-color: #4A4A4A;
            }
            QPushButton:pressed {
                background-color: #2A2A2A;
            }
        """)

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
            self.min_text_area = int(self.settings.value("min_text_area", 4000))
            self.distance_threshold = int(self.settings.value("distance_threshold", 100))

    def open_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Image Folder")
        if folder:
            self.process_folder(folder)

    def process_folder(self, folder):
        self.image_paths = sorted([os.path.join(folder, f) for f in os.listdir(folder) 
                        if f.lower().endswith(('png', 'jpg', 'jpeg'))])
        
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

        # Add images to scroll area
        for image_path in self.image_paths:
            pixmap = QPixmap(image_path)
            filename = os.path.basename(image_path)
            label = ResizableImageLabel(pixmap, filename)
            self.scroll_layout.addWidget(label)

    def start_ocr(self):
        if not self.image_paths:
            print("No images available for OCR.")
            return

        print("Starting OCR...")
        self.reader = easyocr.Reader(['ko'])  # Initialize once here
        self.current_image_index = 0  # Start from the first image
        
        # Reset time tracking variables
        self.start_time = QDateTime.currentDateTime()
        self.processing_times.clear()
        self.current_progress = 0
        self.target_progress = 0
        
        # Set the first 20% of the progress bar to 10 seconds
        self.flat_progress_timer = QTimer(self)
        self.flat_progress_timer.timeout.connect(self.update_flat_progress)
        self.flat_progress_timer_duration = 5000  # 10 seconds
        self.flat_progress_timer_interval = 70  # Update every 100ms
        self.flat_progress_steps = self.flat_progress_timer_duration // self.flat_progress_timer_interval
        self.flat_progress_increment = 20 / self.flat_progress_steps  # 20% over 10 seconds
        self.flat_progress_timer.start(self.flat_progress_timer_interval)

        # Start the progress timer for smooth updates
        self.progress_timer = QTimer(self)
        self.progress_timer.timeout.connect(self.update_progress_smoothly)
        self.update_dynamic_timer_interval()  # Initialize the timer interval
        self.process_next_image()

    def update_dynamic_timer_interval(self):
        """Update the interval of the progress timer based on ETA."""
        if self.current_image_index > 0 and self.processing_times:
            avg_processing_time = sum(self.processing_times) / len(self.processing_times)
            remaining_images = len(self.image_paths) - self.current_image_index
            estimated_remaining_time = avg_processing_time * remaining_images
            
            # Adjust the timer interval dynamically
            # Ensure the interval is at least 50ms and at most 500ms
            new_interval = max(50, min(int(estimated_remaining_time / 10), 500))
            self.progress_timer.setInterval(new_interval)

    def update_flat_progress(self):
        if self.current_progress < 20:
            self.current_progress += self.flat_progress_increment
            self.ocr_progress.setValue(int(self.current_progress))
        else:
            self.flat_progress_timer.stop()
            self.progress_timer.start()  # Start the main progress timer after flat progress


    def process_next_image(self):
        if self.current_image_index >= len(self.image_paths):
            print("All images processed.")
            self.btn_stop_ocr.setVisible(False)
            self.btn_process.setVisible(True)
            self.reader = None
            self.ocr_processor = None
            gc.collect()
            
            # Stop the progress timer
            self.progress_timer.stop()
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
            min_text_area=self.min_text_area  # Pass new setting
        )
        self.ocr_processor.ocr_progress.connect(self.update_ocr_progress_for_image)
        self.ocr_processor.ocr_finished.connect(self.handle_ocr_results)
        self.ocr_processor.error_occurred.connect(self.handle_error)
        self.ocr_processor.start()

    def update_ocr_progress_for_image(self, progress):
        if self.current_image_index == 0:
            # Ignore the first image's processing time for estimation
            overall_progress = 20 + int((self.current_image_index / len(self.image_paths)) * 80 + progress / len(self.image_paths) * 80)
        else:
            overall_progress = 20 + int((self.current_image_index / len(self.image_paths)) * 80 + progress / len(self.image_paths) * 80)
        self.target_progress = overall_progress

    def update_progress_smoothly(self):
        # Gradually increase the progress bar towards the target
        if self.current_progress < self.target_progress:
            self.current_progress += 1
            self.ocr_progress.setValue(int(self.current_progress))

        # Recalculate estimated time dynamically after the first image
        if self.current_image_index > 0:
            # Use the average processing time of all processed images
            avg_processing_time = sum(self.processing_times) / len(self.processing_times)
            remaining_images = len(self.image_paths) - self.current_image_index
            estimated_remaining_time = avg_processing_time * remaining_images

            # Display estimated time in the progress bar tooltip
            self.ocr_progress.setToolTip(f"Estimated time remaining: {estimated_remaining_time:.1f} seconds")

            # Update the dynamic timer interval
            self.update_dynamic_timer_interval()

    def handle_ocr_results(self, results):
        if self.ocr_processor.stop_requested:
            print("Partial results discarded due to stop request")
            return
        
        # Record the processing time for the current image
        end_time = QDateTime.currentDateTime()
        processing_time = self.start_time.msecsTo(end_time) / 1000  # in seconds
        self.processing_times.append(processing_time)

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
        else:
            # Recalculate estimated time after processing each image
            self.recalculate_estimated_time()
        self.process_next_image()
    
    def recalculate_estimated_time(self):
        if self.current_image_index > 0:
            # Use the processing time of the most recent image
            most_recent_processing_time = self.processing_times[-1]
            remaining_images = len(self.image_paths) - self.current_image_index
            estimated_remaining_time = most_recent_processing_time * remaining_images

            # Display estimated time in the progress bar tooltip
            self.ocr_progress.setToolTip(f"Estimated time remaining: {estimated_remaining_time:.1f} seconds")

    def update_results_table(self):
        self.results_table.blockSignals(True)  # Block signals during update
        self.results_table.setRowCount(len(self.ocr_results))
        for row, result in enumerate(self.ocr_results):
            # Text column (editable)
            text_item = QTableWidgetItem(result['text'])
            text_item.setFlags(text_item.flags() | Qt.ItemIsEditable)
            self.results_table.setItem(row, 0, text_item)

            # Confidence (non-editable)
            confidence_item = QTableWidgetItem(f"{result['confidence']:.2f}")
            confidence_item.setTextAlignment(Qt.AlignCenter)
            confidence_item.setFlags(confidence_item.flags() & ~Qt.ItemIsEditable)
            self.results_table.setItem(row, 1, confidence_item)

            # Coordinates (non-editable)
            coord_item = QTableWidgetItem(str(result['coordinates']))
            coord_item.setTextAlignment(Qt.AlignCenter)
            coord_item.setFlags(coord_item.flags() & ~Qt.ItemIsEditable)
            self.results_table.setItem(row, 2, coord_item)

            # File (non-editable)
            file_item = QTableWidgetItem(result['filename'])
            file_item.setTextAlignment(Qt.AlignCenter)
            file_item.setFlags(file_item.flags() & ~Qt.ItemIsEditable)
            self.results_table.setItem(row, 3, file_item)

            # Line Counts (editable)
            line_counts = str(result.get('line_counts', 1))
            line_item = QTableWidgetItem(line_counts)
            line_item.setTextAlignment(Qt.AlignCenter)
            line_item.setFlags(line_item.flags() | Qt.ItemIsEditable)
            self.results_table.setItem(row, 4, line_item)

            # Row Number (non-editable)
            row_item = QTableWidgetItem(str(result['row_number']))
            row_item.setTextAlignment(Qt.AlignCenter)
            row_item.setFlags(row_item.flags() & ~Qt.ItemIsEditable)
            self.results_table.setItem(row, 5, row_item)

            # Add Delete Button
            delete_btn = QPushButton(qta.icon('fa5s.trash-alt', color='red'), "")
            delete_btn.setFixedSize(30, 30)
            
            # Create a container widget with right-aligned button
            container = QWidget()
            layout = QHBoxLayout()
            layout.addStretch()  # Pushes the button to the right
            layout.addWidget(delete_btn)
            layout.setContentsMargins(0, 0, 0, 0)
            container.setLayout(layout)
            
            self.results_table.setCellWidget(row, 6, container)
            delete_btn.clicked.connect(lambda _, r=row: self.delete_row(r))
        self.results_table.blockSignals(False)
    
    def delete_row(self, row):
        if 0 <= row < len(self.ocr_results):
            del self.ocr_results[row]
            self.update_results_table()  # Rebuild the table to reflect changes

    def on_cell_changed(self, row, column):
        if row < 0 or row >= len(self.ocr_results):
            return

        if column == 0:  # Text column
            new_text = self.results_table.item(row, column).text()
            self.ocr_results[row]['text'] = new_text
        elif column == 4:  # Line Counts column
            new_line_counts = self.results_table.item(row, column).text()
            try:
                line_counts = int(new_line_counts)
                self.ocr_results[row]['line_counts'] = line_counts
            except ValueError:
                # Revert to previous value if invalid input
                prev_value = str(self.ocr_results[row].get('line_counts', 1))
                self.results_table.blockSignals(True)
                self.results_table.item(row, column).setText(prev_value)
                self.results_table.blockSignals(False)

    def update_shortcut(self):
        shortcut = self.settings.value("combine_shortcut", "Ctrl+G")
        self.combine_action.setShortcut(QKeySequence(shortcut))
        
    def show_settings_dialog(self):
        dialog = SettingsDialog(self)
        if dialog.exec_():
            self.update_shortcut()
            # ... existing settings update code ...
    
    def combine_selected_rows(self):
        selected_ranges = self.results_table.selectedRanges()
        if not selected_ranges:
            return
            
        selected_rows = sorted(set(
            row for r in selected_ranges 
            for row in range(r.topRow(), r.bottomRow()+1)
        ))
        
        # Check if valid selection
        if len(selected_rows) < 2:
            QMessageBox.warning(self, "Warning", "Select at least 2 adjacent rows to combine")
            return
            
        # Check adjacency and same file
        if any(selected_rows[i+1] - selected_rows[i] != 1 for i in range(len(selected_rows)-1)):
            QMessageBox.warning(self, "Warning", "Selected rows must be adjacent")
            return
            
        first_row = selected_rows[0]
        last_row = selected_rows[-1]
        
        # Check if all rows are from same file
        filenames = {self.ocr_results[row]['filename'] for row in selected_rows}
        if len(filenames) > 1:
            QMessageBox.warning(self, "Warning", "Cannot combine rows from different files")
            return
            
        # Combine the rows
        combined_text = []
        total_lines = 0
        coordinates = []
        
        for row in selected_rows:
            result = self.ocr_results[row]
            combined_text.append(result['text'])
            total_lines += result.get('line_counts', 1)
            coordinates.extend(result['coordinates'])
            
        # Create merged result
        merged_result = {
            'text': '\n'.join(combined_text),
            'confidence': min(r['confidence'] for r in self.ocr_results[first_row:last_row+1]),
            'coordinates': coordinates,
            'filename': self.ocr_results[first_row]['filename'],
            'line_counts': total_lines,
            'row_number': self.ocr_results[first_row]['row_number']
        }
        
        # Update OCR results
        del self.ocr_results[first_row+1:last_row+1]
        self.ocr_results[first_row] = merged_result
        
        # Update table
        self.update_results_table()
        QMessageBox.information(self, "Success", f"Combined {len(selected_rows)} rows")
    
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
        self.progress_timer.stop()

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
        content = self.generate_for_translate_content()

        # Debug print: Show the content being sent to Gemini
        print("\n===== DEBUG: Content sent to Gemini =====\n")
        print(content)
        print("\n=======================================\n")
        
        try:
            translated_text = translate_with_gemini(api_key, content, model_name=model_name,)  # Pass selected model

            # Debug print: Show the raw response from Gemini
            print("\n===== DEBUG: Raw response from Gemini =====\n")
            print(translated_text)
            print("\n==========================================\n")

            self.import_translated_content(translated_text)
            QMessageBox.information(self, "Success", "Translation completed successfully!")
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    def generate_for_translate_content(self):
        """Generate Markdown content in for-translate format."""
        content = "<!-- type: for-translate -->\n\n"
        grouped_results = {}
        extensions = set()

        for result in self.ocr_results:
            filename = result['filename']
            ext = os.path.splitext(filename)[1].lstrip('.').lower()
            extensions.add(ext)
            text = result['text']
            row_number = result['row_number']
            
            if filename not in grouped_results:
                grouped_results[filename] = []
            grouped_results[filename].append((text, row_number))

        if len(extensions) == 1:
            content += f"<!-- ext: {list(extensions)[0]} -->\n\n"

        for idx, (filename, texts) in enumerate(grouped_results.items()):
            if idx > 0:
                content += "\n\n"
            content += f"<!-- file: {filename} -->\n\n"
            sorted_texts = sorted(texts, key=lambda x: x[1])
            for text, row_number in sorted_texts:
                lines = text.split('\n')
                for line in lines:
                    content += f"{line.strip()}\n"
                    content += f"-/{row_number}\\-\n"

        return content

    def import_translated_content(self, content):
        """Import translated content back into OCR results."""
        try:
            # Reuse existing import logic
            self.import_translation_file_content(content)
            self.update_results_table()
        except Exception as e:
            raise Exception(f"Failed to import translation: {str(e)}")
        
    def import_translation_file_content(self, content):
        """Modified version of import_translation that works with direct content instead of file path."""
        try:
            # Debug print: Show the content being parsed
            print("\n===== DEBUG: Content being parsed =====\n")
            print(content)
            print("\n======================================\n")
            if '<!-- type: for-translate -->' not in content:
                raise ValueError("Unsupported MD format - missing type comment.")

            translations = {}
            current_file = None
            file_texts = {}
            current_entry = []  # Buffer for current text entry
            row_numbers = []

            # Parse filename groups and entries
            for line in content.split('\n'):
                line = line.strip()
                if line.startswith('<!-- file:') and line.endswith('-->'):
                    # Save previous file's entries
                    if current_file is not None and current_entry:
                        file_texts[current_file].append(('\n'.join(current_entry), row_numbers))
                        current_entry = []
                        row_numbers = []
                    # Extract filename
                    current_file = line[10:-3].strip()
                    file_texts[current_file] = []
                elif line.startswith('-/') and line.endswith('\\-'):
                    # Extract row number from marker (e.g., "-/3\\-")
                    if current_entry:
                        row_number_str = line[2:-2].strip()
                        try:
                            row_number = int(row_number_str)
                        except ValueError:
                            row_number = 0  # Default to 0 if parsing fails
                        row_numbers.append(row_number)
                        # Save current entry
                        file_texts[current_file].append(('\n'.join(current_entry), row_numbers))
                        current_entry = []
                        row_numbers = []
                elif current_file is not None:
                    # Skip empty lines between entries
                    if line or current_entry:
                        current_entry.append(line)

            # Add the last entry if buffer isn't empty
            if current_file is not None and current_entry:
                file_texts[current_file].append(('\n'.join(current_entry), row_numbers))

            # Debug print: Show parsed structure
            print("\n===== DEBUG: Parsed structure =====\n")
            for filename, entries in file_texts.items():
                print(f"File: {filename}")
                for entry in entries:
                    print(f"  - Text: {entry[0]}")
                    print(f"    Row numbers: {entry[1]}")
            print("\n==================================\n")

            # Rebuild translations in original OCR order
            translation_index = {k: 0 for k in file_texts.keys()}
            for result in self.ocr_results:
                filename = result['filename']
                if filename in file_texts and translation_index[filename] < len(file_texts[filename]):
                    translated_text, row_numbers = file_texts[filename][translation_index[filename]]
                    result['text'] = translated_text
                    result['row_number'] = row_numbers[0]  # Update row number
                    translation_index[filename] += 1
                    print(f"DEBUG: Updated {filename} row {row_numbers[0]} with translation")

                else:
                    print(f"Warning: No translation found for entry in '{filename}'")

        except Exception as e:
            raise Exception(f"Failed to parse translated content: {str(e)}")

    def apply_translation(self):
        """Apply translations to images based on OCR results."""
        # Group OCR results by filename and row number
        grouped_results = {}
        for result in self.ocr_results:
            filename = result['filename']
            row_number = result.get('row_number', None)
            if filename not in grouped_results:
                grouped_results[filename] = {}
            if row_number is not None:
                grouped_results[filename][row_number] = {
                    'coordinates': result['coordinates'],
                    'text': result['text'],
                    'line_counts': result.get('line_counts', 1)  # Default to 1 line if not available
                }

        # Apply translations to each image
        for i in range(self.scroll_layout.count()):
            widget = self.scroll_layout.itemAt(i).widget()
            if isinstance(widget, ResizableImageLabel) and widget.filename in grouped_results:
                widget.apply_translation(grouped_results[widget.filename])

    def import_translation(self):
        import_translation_file(self)

    def export_manhwa(self):
        """Export images with applied translations into a ZIP file."""
        # Ensure there are processed images before proceeding
        if not self.image_paths:
            QMessageBox.warning(self, "Warning", "No images available for export.")
            return

        # Collect all translated images
        translated_images = []
        for i in range(self.scroll_layout.count()):
            widget = self.scroll_layout.itemAt(i).widget()
            if isinstance(widget, ResizableImageLabel):
                # Get the updated image with applied translation
                translated_image_path = widget.get_updated_image_path()
                if translated_image_path:
                    translated_images.append((translated_image_path, os.path.basename(translated_image_path)))

        if not translated_images:
            QMessageBox.warning(self, "Warning", "No translated images found.")
            return

        # Call the export function from file_io
        from utils.file_io import export_translated_images_to_zip
        export_path, success = export_translated_images_to_zip(translated_images)

        if success:
            QMessageBox.information(self, "Success", f"Images successfully exported to:\n{export_path}")
        else:
            QMessageBox.critical(self, "Error", "Failed to export images.")

    def handle_error(self, message):
        print(f"Error occurred: {message}")
        QMessageBox.critical(self, "Error", message)
        self.progress.setValue(0)
        self.btn_process.setEnabled(False)