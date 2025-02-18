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

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Manga OCR Tool")
        self.setGeometry(100, 100, 1200, 600)
        
        self.init_ui()
        self.current_image = None
        self.ocr_results = []
        self.image_paths = []
        self.current_image_index = 0
        self.scroll_content = QWidget()
        self.reader = None
        self.ocr_processor = None

    def init_ui(self):
        main_widget = QWidget()
        main_layout = QVBoxLayout()  # Changed to vertical layout

        # Controls layout for buttons and progress bars
        controls_layout = QVBoxLayout()

        # Top row for buttons
        button_layout = QHBoxLayout()
        self.btn_open = QPushButton(qta.icon('fa5s.folder-open'), " Open Folder")
        self.btn_open.clicked.connect(self.open_folder)
        button_layout.addWidget(self.btn_open)

        self.btn_process = QPushButton(qta.icon('fa5s.magic'), " Process OCR")
        self.btn_process.clicked.connect(self.start_ocr)
        self.btn_process.setEnabled(False)
        button_layout.addWidget(self.btn_process)

        # In MainWindow's init_ui method, within button_layout setup:
        self.btn_stop_ocr = QPushButton(qta.icon('fa5s.stop'), " Stop OCR")
        self.btn_stop_ocr.clicked.connect(self.stop_ocr)
        self.btn_stop_ocr.setEnabled(False)  # Initially disabled
        button_layout.addWidget(self.btn_stop_ocr)

        self.btn_export_ocr = QPushButton(qta.icon('fa5s.file-export'), " Export OCR")
        self.btn_export_ocr.clicked.connect(self.export_ocr)
        button_layout.addWidget(self.btn_export_ocr)

        self.btn_import_translation = QPushButton(qta.icon('fa5s.file-import'), " Import Translation")
        self.btn_import_translation.clicked.connect(self.import_translation)
        button_layout.addWidget(self.btn_import_translation)

        controls_layout.addLayout(button_layout)

        # Progress bars in their own row
        progress_layout = QHBoxLayout()
        self.image_progress_label = QLabel("Image Processing Progress:")
        progress_layout.addWidget(self.image_progress_label)
        self.image_progress = QProgressBar()
        progress_layout.addWidget(self.image_progress)

        self.ocr_progress_label = QLabel("OCR Processing Progress:")
        progress_layout.addWidget(self.ocr_progress_label)
        self.ocr_progress = QProgressBar()
        progress_layout.addWidget(self.ocr_progress)

        controls_layout.addLayout(progress_layout)

        # Add controls layout to the main layout
        main_layout.addLayout(controls_layout)

        # Splitter to divide image and table
        splitter = QSplitter(Qt.Horizontal)

        # Image display area with scroll
        self.scroll_area = QScrollArea()
        self.scroll_content = QWidget()
        self.scroll_layout = QVBoxLayout(self.scroll_content)
        self.scroll_layout.setContentsMargins(0, 0, 0, 0)
        self.scroll_layout.setSpacing(0)
        self.scroll_area.setWidget(self.scroll_content)
        self.scroll_area.setWidgetResizable(True)
        splitter.addWidget(self.scroll_area)

        # OCR results table and apply button
        table_widget = QWidget()
        table_layout = QVBoxLayout(table_widget)
        self.results_table = QTableWidget()
        self.results_table.setColumnCount(6)  # Add one more column
        self.results_table.setHorizontalHeaderLabels(["Text", "Confidence", "Coordinates", "File", "Line Counts", "Row Number"])
        table_layout.addWidget(self.results_table)

        self.btn_apply_translation = QPushButton(qta.icon('fa5s.check'), " Apply Translation")
        self.btn_apply_translation.clicked.connect(self.apply_translation)
        table_layout.addWidget(self.btn_apply_translation)

        self.btn_export_manhwa = QPushButton(qta.icon('fa5s.file-archive'), " Export Manhwa")
        self.btn_export_manhwa.clicked.connect(self.export_manhwa)
        table_layout.addWidget(self.btn_export_manhwa)

        splitter.addWidget(table_widget)
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
        self.image_progress.setValue(0)
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
            self.btn_stop_ocr.setEnabled(False)
            self.btn_process.setEnabled(True)
            self.reader = None
            self.ocr_processor = None
            gc.collect()
            return

        self.btn_process.setEnabled(False)
        self.btn_stop_ocr.setEnabled(True)

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
            self.btn_stop_ocr.setEnabled(False)
            self.btn_process.setEnabled(True)
        self.process_next_image()

    def update_results_table(self):
        self.results_table.setRowCount(len(self.ocr_results))
        for row, result in enumerate(self.ocr_results):
            self.results_table.setItem(row, 0, QTableWidgetItem(result['text']))
            self.results_table.setItem(row, 1, QTableWidgetItem(f"{result['confidence']:.2f}"))
            self.results_table.setItem(row, 2, QTableWidgetItem(str(result['coordinates'])))
            self.results_table.setItem(row, 3, QTableWidgetItem(result['filename']))
            self.results_table.setItem(row, 4, QTableWidgetItem(str(result.get('line_counts', 1))))
            self.results_table.setItem(row, 5, QTableWidgetItem(str(result['row_number'])))  # Use the stored row number
    
    def stop_ocr(self):
        if hasattr(self, 'ocr_processor'):
            self.ocr_processor.stop_requested = True
            self.ocr_progress.setValue(0)
            self.btn_stop_ocr.setEnabled(False)
            self.btn_process.setEnabled(True)
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