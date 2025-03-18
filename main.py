import sys
from PyQt5.QtWidgets import (QApplication, QWidget, QVBoxLayout, QPushButton, QProgressBar,
                            QLabel, QListWidget, QMessageBox, QLineEdit, QFileDialog, QStatusBar,
                            QListWidgetItem, QHBoxLayout, QGridLayout, QDialog, QDialogButtonBox, QComboBox)
from PyQt5.QtCore import Qt, QSettings, QDateTime, QDir, QThread, pyqtSignal
from PyQt5.QtGui import QFont
import os
import zipfile
import json
import tempfile
import re
from shutil import copyfile, rmtree
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin

class ImportWFWFDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Import from WFWF")
        self.setMinimumSize(500, 300)
        
        layout = QVBoxLayout()
        self.setLayout(layout)
        
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("Enter WFWF URL...")
        layout.addWidget(QLabel("WFWF URL:"))
        layout.addWidget(self.url_input)
        
        # Add status display area
        self.status_text = QListWidget()
        layout.addWidget(QLabel("Download Progress:"))
        layout.addWidget(self.status_text)
        
        # Add progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        layout.addWidget(self.progress_bar)
        
        # Status bar
        self.status_bar = QStatusBar()
        layout.addWidget(self.status_bar)
        
        # Button layout
        button_layout = QHBoxLayout()
        self.download_btn = QPushButton("Download")
        self.download_btn.clicked.connect(self.start_download)
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self.reject)
        self.save_btn = QPushButton("Save Project")
        self.save_btn.setEnabled(False)
        self.save_btn.clicked.connect(self.accept)
        
        button_layout.addWidget(self.download_btn)
        button_layout.addWidget(self.cancel_btn)
        button_layout.addWidget(self.save_btn)
        layout.addLayout(button_layout)
        
        self.temp_dir = None
        self.download_worker = None
        
        self.setStyleSheet("""
            QDialog {
                background-color: #2D2D2D;
                color: #FFFFFF;
                font-size: 14px;
            }
            QLineEdit {
                background-color: #3A3A3A;
                padding: 8px;
                border: 1px solid #4A4A4A;
                border-radius: 4px;
                margin: 5px 0;
            }
            QLabel {
                color: #CCCCCC;
            }
            QListWidget {
                background-color: #3A3A3A;
                color: #FFFFFF;
                border-radius: 4px;
                padding: 5px;
            }
            QPushButton {
                background-color: #4A4A4A;
                color: #FFFFFF;
                padding: 8px 16px;
                border: none;
                border-radius: 4px;
                min-width: 80px;
            }
            QPushButton:hover {
                background-color: #5A5A5A;
            }
            QPushButton:disabled {
                background-color: #3A3A3A;
                color: #999999;
            }
            QProgressBar {
                border: 1px solid #4A4A4A;
                border-radius: 4px;
                text-align: center;
                height: 20px;
            }
            QProgressBar::chunk {
                background-color: #5294e2;
                width: 1px;
            }
            QStatusBar {
                color: #CCCCCC;
            }
        """)
    
    def get_url(self):
        return self.url_input.text().strip()
    
    def get_temp_dir(self):
        return self.temp_dir
    
    def start_download(self):
        url = self.get_url()
        if not url:
            self.status_bar.showMessage("Please enter a valid URL", 3000)
            return
        
        self.temp_dir = tempfile.mkdtemp()
        self.download_worker = ImportDownloadWorker(url, self.temp_dir)
        self.download_worker.progress.connect(self.update_progress)
        self.download_worker.status.connect(self.update_status)
        self.download_worker.finished.connect(self.download_finished)
        
        # Disable buttons during download
        self.download_btn.setEnabled(False)
        self.url_input.setEnabled(False)
        
        # Clear previous status
        self.status_text.clear()
        self.progress_bar.setValue(0)
        
        # Start download
        self.download_worker.start()
    
    def update_progress(self, value):
        self.progress_bar.setValue(value)
    
    def update_status(self, message):
        self.status_text.addItem(message)
        self.status_text.scrollToBottom()
        self.status_bar.showMessage(message, 3000)
    
    def download_finished(self, success):
        if success:
            self.status_bar.showMessage("Download completed successfully!", 5000)
            self.save_btn.setEnabled(True)
        else:
            self.status_bar.showMessage("Download failed!", 5000)
            if self.temp_dir and os.path.exists(self.temp_dir):
                rmtree(self.temp_dir)
                self.temp_dir = None
        
        # Re-enable buttons
        self.download_btn.setEnabled(True)
        self.url_input.setEnabled(True)

class ImportDownloadWorker(QThread):
    progress = pyqtSignal(int)
    status = pyqtSignal(str)
    finished = pyqtSignal(bool)

    def __init__(self, url, output_dir):
        super().__init__()
        self.url = url
        self.output_dir = output_dir

    def run(self):
        try:
            self.status.emit(f"Fetching URL: {self.url}")
            response = requests.get(self.url)
            if response.status_code != 200:
                self.status.emit(f"Failed to fetch URL (HTTP {response.status_code})")
                self.finished.emit(False)
                return

            self.status.emit("Parsing page content...")
            soup = BeautifulSoup(response.text, 'html.parser')
            images = soup.find_all('img', class_='v-img lazyload')
            if not images:
                self.status.emit("No images found on the page!")
                self.finished.emit(False)
                return

            self.status.emit(f"Found {len(images)} images")
            os.makedirs(self.output_dir, exist_ok=True)

            valid_images = [img for img in images if 'data-original' in img.attrs]
            total_images = len(valid_images)
            
            if total_images == 0:
                self.status.emit("No valid images found with data-original attribute")
                self.finished.emit(False)
                return
                
            self.status.emit(f"Starting download of {total_images} images...")
            
            for i, img in enumerate(valid_images):
                img_url = urljoin(self.url, img['data-original'])
                img_name = os.path.basename(img_url) or f'image_{i}.jpg'
                img_path = os.path.join(self.output_dir, img_name)
                
                self.status.emit(f"Downloading {img_name}...")
                img_response = requests.get(img_url)
                if img_response.status_code == 200:
                    with open(img_path, 'wb') as f:
                        f.write(img_response.content)
                    self.status.emit(f"Downloaded {img_name}")
                else:
                    self.status.emit(f"Failed to download {img_url}")
                
                # Update progress bar
                progress_value = int((i + 1) / total_images * 100)
                self.progress.emit(progress_value)

            self.status.emit(f"Download complete! All {total_images} images saved.")
            self.finished.emit(True)
        except Exception as e:
            self.status.emit(f"Error: {str(e)}")
            self.finished.emit(False)


class NewProjectDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("New Project")
        self.setMinimumSize(600, 250)  # Increased height
        
        layout = QVBoxLayout()
        self.setLayout(layout)
        
        # Source selection
        source_layout = QHBoxLayout()
        self.edit_source = QLineEdit()
        self.edit_source.setPlaceholderText("Select an image or folder...")
        self.edit_source.setReadOnly(True)
        self.btn_choose_image = QPushButton("Image")
        self.btn_choose_image.clicked.connect(self.choose_image)
        self.btn_choose_folder = QPushButton("Folder")
        self.btn_choose_folder.clicked.connect(self.choose_folder)
        
        source_layout.addWidget(self.edit_source)
        source_layout.addWidget(self.btn_choose_image)
        source_layout.addWidget(self.btn_choose_folder)
        
        # Language selection
        language_layout = QHBoxLayout()
        self.language_combo = QComboBox()
        self.language_combo.addItems(["Korean", "Chinese", "Japanese"])
        language_layout.addWidget(QLabel("Original Language:"))
        language_layout.addWidget(self.language_combo)
        
        # Project location
        project_layout = QHBoxLayout()
        self.edit_project = QLineEdit()
        self.edit_project.setPlaceholderText("Choose project save location...")
        self.edit_project.setReadOnly(True)
        self.btn_choose_project = QPushButton("Browse")
        self.btn_choose_project.clicked.connect(self.choose_project_location)
        
        project_layout.addWidget(self.edit_project)
        project_layout.addWidget(self.btn_choose_project)
        
        # Button box
        self.button_box = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel,
            Qt.Horizontal, self
        )
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        self.button_box.button(QDialogButtonBox.Ok).setText("Create")
        
        # Add to main layout
        layout.addWidget(QLabel("Source:"))
        layout.addLayout(source_layout)
        layout.addLayout(language_layout)  # Add language selection
        layout.addWidget(QLabel("Project Location:"))
        layout.addLayout(project_layout)
        layout.addWidget(self.button_box)
        
        # Styling
        self.setStyleSheet("""
            QDialog {
                background-color: #2D2D2D;
                color: #FFFFFF;
                font-size: 14px;
            }
            QLineEdit {
                background-color: #3A3A3A;
                padding: 8px;
                border: 1px solid #4A4A4A;
                border-radius: 4px;
                margin: 5px 0;
            }
            QPushButton {
                background-color: #4A4A4A;
                color: #FFFFFF;
                padding: 8px 16px;
                border: none;
                border-radius: 4px;
                min-width: 80px;
            }
            QPushButton:hover {
                background-color: #5A5A5A;
            }
            QLabel {
                margin-top: 10px;
                color: #CCCCCC;
            }
            QComboBox {
                background-color: #3A3A3A;
                color: #FFFFFF;
                padding: 5px;
                border: 1px solid #4A4A4A;
                border-radius: 4px;
            }
            QComboBox::drop-down {
                border: none;
            }
            QComboBox QAbstractItemView {
                background-color: #3A3A3A;
                color: #FFFFFF;
                selection-background-color: #5A5A5A;
            }
        """)
    
    def choose_image(self):
        file, _ = QFileDialog.getOpenFileName(self, "Select Image", QDir.homePath(), "Images (*.png *.jpg *.jpeg)")
        if file:
            self.edit_source.setText(file)
    
    def choose_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Image Folder", QDir.homePath())
        if folder:
            self.edit_source.setText(folder)
    
    def choose_project_location(self):
        file, _ = QFileDialog.getSaveFileName(self, "Create Project", QDir.homePath(), "Manga Translation Files (*.mmtl)")
        if file:
            self.edit_project.setText(file)
    
    def get_paths(self):
        return self.edit_source.text(), self.edit_project.text(), self.language_combo.currentText()
    
class Home(QWidget):
    def __init__(self):
        super().__init__()
        self.settings = QSettings("YourCompany", "MangaOCRTool")
        self.init_ui()
        
    def init_ui(self):
        self.setWindowTitle("Manga OCR Tool")
        self.setGeometry(100, 100, 800, 600)
        
        main_layout = QHBoxLayout()
        self.setLayout(main_layout)

        left_layout = QVBoxLayout()

        self.btn_new = QPushButton("New Project")
        self.btn_open = QPushButton("Open Project")
        self.btn_import = QPushButton("Import from WFWF")
        
        for btn in [self.btn_new, self.btn_open, self.btn_import]:
            btn.setFixedHeight(50)
            left_layout.addWidget(btn)
        
        self.btn_new.clicked.connect(self.new_project)
        self.btn_open.clicked.connect(self.open_project)
        self.btn_import.clicked.connect(self.import_from_wfwf)

        right_layout = QVBoxLayout()
        
        recent_label = QLabel("Recent Projects:")
        recent_label.setFont(QFont("Arial", 12, QFont.Bold))
        right_layout.addWidget(recent_label)
        
        self.recent_list = QListWidget()
        self.recent_list.itemDoubleClicked.connect(self.open_recent_project)
        right_layout.addWidget(self.recent_list)
        
        main_layout.addLayout(left_layout, 1)
        main_layout.addLayout(right_layout, 3)
        
        self.load_recent_projects()
        
        # Styling
        self.setStyleSheet("""
            QWidget {
                background-color: #2D2D2D;
                color: #FFFFFF;
            }
            QPushButton {
                background-color: #3A3A3A;
                border-radius: 5px;
                padding: 10px;
                font-size: 16px;
                margin: 5px;
            }
            QPushButton:hover {
                background-color: #4A4A4A;
            }
            QListWidget {
                background-color: #3A3A3A;
                border-radius: 5px;
                padding: 5px;
                font-size: 14px;
            }
            QLabel {
                padding: 5px;
                color: #CCCCCC;
            }
        """)

    def load_recent_projects(self):
        recent = self.settings.value("recent_projects", [])
        self.recent_list.clear()
        for path in recent:
            if os.path.exists(path):
                item = QListWidgetItem(os.path.basename(path))
                item.setData(Qt.UserRole, path)
                self.recent_list.addItem(item)

    def open_recent_project(self, item):
        path = item.data(Qt.UserRole)
        if os.path.exists(path):
            self.launch_main_app(path)
        else:
            QMessageBox.warning(self, "Error", "Project file no longer exists")

    def new_project(self):
        dialog = NewProjectDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            source_path, project_path, language = dialog.get_paths()  # Get language
            
            if not source_path or not project_path:
                QMessageBox.warning(self, "Error", "Please select both source and project location")
                return
                
            try:
                # Create new .mmtl file
                with zipfile.ZipFile(project_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                    # Create meta.json
                    meta = {
                        'created': QDateTime.currentDateTime().toString(Qt.ISODate),
                        'source': source_path,
                        'original_language': language,  # Added field
                        'version': '1.0'
                    }
                    zipf.writestr('meta.json', json.dumps(meta, indent=2))
                    
                    # Add images
                    images_dir = 'images/'
                    if os.path.isfile(source_path):
                        zipf.write(source_path, images_dir + os.path.basename(source_path))
                    elif os.path.isdir(source_path):
                        for file in os.listdir(source_path):
                            if file.lower().endswith(('png', 'jpg', 'jpeg')):
                                zipf.write(os.path.join(source_path, file), 
                                         images_dir + file)
                    
                    # Create empty OCR results
                    zipf.writestr('master.json', json.dumps([]))  # Empty list
                
                self.launch_main_app(project_path)
                
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to create project: {str(e)}")

    def open_project(self):
        file, _ = QFileDialog.getOpenFileName(self, "Open Project", "", "Manga Translation Files (*.mmtl)")
        if file:
            self.launch_main_app(file)

    def correct_filenames(self, directory):
        """
        Apply number correction to filenames in the directory.
        Returns a dict mapping original filenames to corrected ones.
        """
        # Get all files in the directory
        files = os.listdir(directory)
        filename_map = {}
        
        # Dictionaries to track maximum suffix lengths for both formats
        parentheses_lengths = []
        direct_suffix_lengths = []
        
        # First pass: determine maximum numeric suffix lengths for both formats
        for filename in files:
            base, ext = os.path.splitext(filename)
            
            # Check for numbers in parentheses: "filename (123).ext"
            parentheses_match = re.match(r'^(.*?)\s*\((\d+)\)$', base)
            if parentheses_match:
                num_str = parentheses_match.group(2)
                parentheses_lengths.append(len(num_str))
                continue
            
            # Check for direct numeric suffixes: "filename123.ext"
            direct_match = re.match(r'^(.*?)(\d+)$', base)
            if direct_match:
                num_str = direct_match.group(2)
                direct_suffix_lengths.append(len(num_str))
        
        # Determine maximum lengths (if any files were found)
        max_parentheses_length = max(parentheses_lengths) if parentheses_lengths else 0
        max_direct_length = max(direct_suffix_lengths) if direct_suffix_lengths else 0
        
        # No files with numeric suffixes found
        if max_parentheses_length == 0 and max_direct_length == 0:
            return {filename: filename for filename in files}
        
        # Second pass: rename files with padded numbers
        for filename in files:
            base, ext = os.path.splitext(filename)
            new_filename = filename  # Default to no change
            
            # Handle numbers in parentheses: "filename (123).ext"
            parentheses_match = re.match(r'^(.*?)\s*\((\d+)\)$', base)
            if parentheses_match and max_parentheses_length > 0:
                base_part = parentheses_match.group(1).rstrip()  # Remove trailing space
                num_str = parentheses_match.group(2)
                padded_num = num_str.zfill(max_parentheses_length)
                new_base = f"{base_part} ({padded_num})"
                new_filename = f"{new_base}{ext}"
            
            # Handle direct numeric suffixes: "filename123.ext"
            direct_match = re.match(r'^(.*?)(\d+)$', base)
            if direct_match and max_direct_length > 0:
                base_part = direct_match.group(1)
                num_str = direct_match.group(2)
                padded_num = num_str.zfill(max_direct_length)
                new_base = f"{base_part}{padded_num}"
                new_filename = f"{new_base}{ext}"
            
            if new_filename != filename:
                # Record the mapping but don't rename yet to avoid conflicts
                filename_map[filename] = new_filename
            else:
                filename_map[filename] = filename
                
        return filename_map

    def import_from_wfwf(self):
        dialog = ImportWFWFDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            temp_dir = dialog.get_temp_dir()
            if not temp_dir or not os.path.exists(temp_dir):
                QMessageBox.warning(self, "Error", "No downloaded images found.")
                return
            
            project_path, _ = QFileDialog.getSaveFileName(
                self, "Save Project", QDir.homePath(), "Manga Translation Files (*.mmtl)"
            )
            
            if not project_path:
                rmtree(temp_dir)
                return
            
            try:
                # Run number correction on downloaded files
                filename_map = self.correct_filenames(temp_dir)
                
                # Create a temporary directory for corrected filenames
                corrected_dir = tempfile.mkdtemp()
                
                # Copy files with corrected names
                for old_name, new_name in filename_map.items():
                    if old_name.lower().endswith(('png', 'jpg', 'jpeg')):
                        src = os.path.join(temp_dir, old_name)
                        dst = os.path.join(corrected_dir, new_name)
                        copyfile(src, dst)
                
                with zipfile.ZipFile(project_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                    meta = {
                        'created': QDateTime.currentDateTime().toString(Qt.ISODate),
                        'source': dialog.get_url(),
                        'version': '1.0'
                    }
                    zipf.writestr('meta.json', json.dumps(meta, indent=2))
                    
                    images_dir = 'images/'
                    for img in os.listdir(corrected_dir):
                        if img.lower().endswith(('png', 'jpg', 'jpeg')):
                            zipf.write(os.path.join(corrected_dir, img), os.path.join(images_dir, img))
                    
                    zipf.writestr('master.json', json.dumps([]))
                
                self.launch_main_app(project_path)
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to create project: {str(e)}")
            finally:
                rmtree(temp_dir)
                if 'corrected_dir' in locals() and os.path.exists(corrected_dir):
                    rmtree(corrected_dir)

    def create_mmtl(self, folder, target_path):
        # Create ZIP structure
        with zipfile.ZipFile(target_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            # Create meta.json
            meta = {
                'created': QDateTime.currentDateTime().toString(Qt.ISODate),
                'version': '1.0',
                'settings': dict(self.settings.allKeys())
            }
            zipf.writestr('meta.json', json.dumps(meta, indent=2))
            
            # Copy images
            image_files = [f for f in os.listdir(folder) if f.lower().endswith(('png', 'jpg', 'jpeg'))]
            for img in image_files:
                src = os.path.join(folder, img)
                zipf.write(src, os.path.join('images', img))
                
            # Create empty master.json
            zipf.writestr('master.json', json.dumps([]))  # Directly write an empty list
            
    def open_mmtl(self, file_path):
        # Extract to temp directory
        temp_dir = tempfile.mkdtemp()
        with zipfile.ZipFile(file_path, 'r') as zipf:
            zipf.extractall(temp_dir)
            
        # Verify structure
        required = ['meta.json', 'master.json', 'images/']
        if not all(os.path.exists(os.path.join(temp_dir, p)) for p in required):
            QMessageBox.critical(self, "Error", "Invalid .mmtl file")
            return None
            
        return temp_dir
    
    def update_recent_projects(self, folder):
        recent = self.settings.value("recent_projects", [])
        if folder in recent:
            recent.remove(folder)
        recent.insert(0, folder)
        recent = list(dict.fromkeys(recent))[:5]  # Keep unique, last 5
        self.settings.setValue("recent_projects", recent)

    def launch_main_app(self, mmtl_path):
        from app.main_window import MainWindow
        self.update_recent_projects(mmtl_path)
        
        # Create temp directory
        temp_dir = tempfile.mkdtemp()
        with zipfile.ZipFile(mmtl_path, 'r') as zipf:
            zipf.extractall(temp_dir)
            
        # Verify structure
        required = ['meta.json', 'master.json', 'images/']
        if not all(os.path.exists(os.path.join(temp_dir, p)) for p in required):
            QMessageBox.critical(self, "Error", "Invalid .mmtl file")
            return
            
        # Create and show main window
        self.main_window = MainWindow()
        self.main_window.process_mmtl(mmtl_path, temp_dir)
        self.main_window.show()
        
        self.close()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = Home()
    window.show()
    sys.exit(app.exec_())