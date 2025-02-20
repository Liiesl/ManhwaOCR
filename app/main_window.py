from PyQt5.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QFileDialog, QLabel, QProgressBar, QTableWidget, QTableWidgetItem, QScrollArea, QMessageBox, QSplitter
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QPixmap
import qtawesome as qta
from core.ocr_processor import OCRProcessor
from utils.file_io import export_ocr_results, import_translation_file
from core.data_processing import group_and_merge_text
from app.widgets import ResizableImageLabel
import easyocr
import os
import gc

class CustomScrollArea(QScrollArea):
    def __init__(self, overlay_widget, parent=None):
        super().__init__(parent)
        self.overlay_widget = overlay_widget

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.update_overlay_position()

    def update_overlay_position(self):
        if self.overlay_widget:
            overlay_width = 300
            overlay_height = 60
            scroll_width = self.width()
            scroll_height = self.height()

            # Calculate the new position for the overlay
            x = (scroll_width - overlay_width) // 2
            y = scroll_height - overlay_height - 20  # 10 pixels from the bottom

            self.overlay_widget.setGeometry(x, y, overlay_width, overlay_height)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Manga OCR Tool")
        self.setGeometry(100, 100, 1200, 600)
        
        self.init_ui()
        self.current_image = None
        self.ocr_results = []
        self.results_table.cellChanged.connect(self.on_cell_changed)
        self.image_paths = []
        self.current_image_index = 0
        self.scroll_content = QWidget()
        self.reader = None
        self.ocr_processor = None

    def init_ui(self):
        # Set the main widget and layout
        main_widget = QWidget()
        main_layout = QHBoxLayout()  # Main horizontal layout

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
            /* Table header style */
            QHeaderView::section {
                background-color: #3A3A3A;
                color: #FFFFFF;
                padding: 4px;
                border: 1px solid #2A2A2A;
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
        self.btn_open = QPushButton(qta.icon('fa5s.folder-open', color='white'), "Open Folder")
        self.btn_open.clicked.connect(self.open_folder)
        left_panel.addWidget(self.btn_open)

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
        self.results_table.setColumnCount(6)   # Add one more column
        self.results_table.setHorizontalHeaderLabels(["Text", "Confidence", "Coordinates", "File", "Line Counts", "Row Number"])
        right_panel.addWidget(self.results_table)

        # Apply Translation Button
        self.btn_apply_translation = QPushButton(qta.icon('fa5s.check', color='white'), "Apply Translation")
        self.btn_apply_translation.clicked.connect(self.apply_translation)
        right_panel.addWidget(self.btn_apply_translation)

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
        self.process_next_image()

    def process_next_image(self):
        if self.current_image_index >= len(self.image_paths):
            print("All images processed.")
            self.btn_stop_ocr.setVisible(False)
            self.btn_process.setVisible(True)
            self.reader = None
            self.ocr_processor = None
            gc.collect()
            return

        self.btn_process.setVisible(False)
        self.btn_stop_ocr.setVisible(True)

        image_path = self.image_paths[self.current_image_index]
        print(f"Processing image {self.current_image_index + 1}/{len(self.image_paths)}: {image_path}")

        # Start OCR for the current image
        self.ocr_processor = OCRProcessor(image_path, self.reader)
        self.ocr_processor.ocr_progress.connect(self.update_ocr_progress_for_image)
        self.ocr_processor.ocr_finished.connect(self.handle_ocr_results)
        self.ocr_processor.error_occurred.connect(self.handle_error)
        self.ocr_processor.start()

    def update_ocr_progress_for_image(self, progress):
        overall_progress = int((self.current_image_index / len(self.image_paths)) * 100 + progress / len(self.image_paths))
        self.ocr_progress.setValue(overall_progress)

    def handle_ocr_results(self, results):
        if self.ocr_processor.stop_requested:
            print("Partial results discarded due to stop request")
            return

        # Calculate the starting row number for this batch
        start_row = len(self.ocr_results)
        
        # Add filename and row number to each result
        current_image_path = self.image_paths[self.current_image_index]
        filename = os.path.basename(current_image_path)
        for idx, result in enumerate(results):
            result['filename'] = filename
            result['row_number'] = start_row + idx  # Use continuous row numbering across all images
            
        # Group and merge text from the same speech bubble
        merged_results = group_and_merge_text(results)
        
        # Make sure the merged results maintain proper row numbers
        for idx, result in enumerate(merged_results):
            result['row_number'] = start_row + idx
            
        # Add merged results to the global list
        self.ocr_results.extend(merged_results)

        # Update the table
        self.update_results_table()

        # Move to the next image
        self.current_image_index += 1
        if self.current_image_index >= len(self.image_paths):
            self.btn_stop_ocr.setVisible(False)
            self.btn_process.setVisible(True)
        self.process_next_image()

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
            confidence_item.setFlags(confidence_item.flags() & ~Qt.ItemIsEditable)
            self.results_table.setItem(row, 1, confidence_item)

            # Coordinates (non-editable)
            coord_item = QTableWidgetItem(str(result['coordinates']))
            coord_item.setFlags(coord_item.flags() & ~Qt.ItemIsEditable)
            self.results_table.setItem(row, 2, coord_item)

            # File (non-editable)
            file_item = QTableWidgetItem(result['filename'])
            file_item.setFlags(file_item.flags() & ~Qt.ItemIsEditable)
            self.results_table.setItem(row, 3, file_item)

            # Line Counts (editable)
            line_counts = str(result.get('line_counts', 1))
            line_item = QTableWidgetItem(line_counts)
            line_item.setFlags(line_item.flags() | Qt.ItemIsEditable)
            self.results_table.setItem(row, 4, line_item)

            # Row Number (non-editable)
            row_item = QTableWidgetItem(str(result['row_number']))
            row_item.setFlags(row_item.flags() & ~Qt.ItemIsEditable)
            self.results_table.setItem(row, 5, row_item)
        self.results_table.blockSignals(False)  # Unblock signals

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
    
    def stop_ocr(self):
        if hasattr(self, 'ocr_processor'):
            self.ocr_processor.stop_requested = True
            self.ocr_progress.setValue(0)
            self.btn_stop_ocr.setVisible(False)
            self.btn_process.setVisible(True)
            self.reader = None
            gc.collect()
            QMessageBox.information(self, "Stopped", "OCR processing was stopped.")

    def export_ocr(self):
        export_ocr_results(self)

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