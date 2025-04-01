import sys
from PyQt5.QtWidgets import (QApplication, QWidget, QVBoxLayout, QPushButton, QProgressBar, QFrame, QMainWindow, QLabel, QListWidget, QMessageBox, QLineEdit, 
                            QFileDialog, QStatusBar, QScrollArea, QHBoxLayout, QDialog, QDialogButtonBox, QComboBox)
from PyQt5.QtCore import Qt, QSettings, QDateTime, QDir, QThread, pyqtSignal
from PyQt5.QtGui import QFont
from assets.styles import (HOME_STYLES, HOME_LEFT_LAYOUT_STYLES, NEW_PROJECT_STYLES, WFWF_STYLES)
import os, zipfile, json, tempfile, re, requests
from shutil import copyfile, rmtree
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
        
        self.setStyleSheet(WFWF_STYLES)
    
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
        self.setStyleSheet(NEW_PROJECT_STYLES)
    
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

# Keep your existing ImportWFWFDialog and NewProjectDialog classes as they are
class ProjectItemWidget(QFrame):
    """Custom widget for displaying a single project item"""
    def __init__(self, name, path, last_opened="", main_window=None):
        super().__init__()
        self.path = path
        self.main_window = main_window  # Store reference to the main window
        self.setObjectName("projectItem")
        self.setStyleSheet("""
            #projectItem {
                background-color: none;
                border-radius: 0px;
                padding: 10px;
            }
            #projectItem:hover {
                background-color: #3a3a3a;
            }
        """)
        
        # Layout
        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(10, 8, 10, 8)
        
        # Project name
        self.name_label = QLabel(name)
        self.name_label.setStyleSheet("font-size: 14px;")
        
        # Last opened (display formatted date instead of path)
        self.last_opened_label = QLabel(last_opened if last_opened else "Never opened")
        self.last_opened_label.setStyleSheet("font-size: 14px; color: #aaaaaa;")
        
        # Add widgets to layout
        self.layout.addWidget(self.name_label)
        self.layout.addStretch()
        self.layout.addWidget(self.last_opened_label)
        
        # Make the widget clickable
        self.setCursor(Qt.PointingHandCursor)
        
    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.LeftButton:
            window = self.window()
            if isinstance(window, Home):
                window.open_project_from_path(self.path)
        super().mouseDoubleClickEvent(event)  # Call superclass implementation

class ProjectsListWidget(QWidget):
    """Custom widget for displaying a list of projects"""
    def __init__(self):
        super().__init__()
        
        # Main layout
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)  # Reduced spacing
        
        # Header
        self.header = QWidget()
        self.header.setStyleSheet("padding: 10px; background-color: #3E3E3E; border-top-right-radius: 15px; border-top-left-radius: 15px;")  # Darker header
        self.header_layout = QHBoxLayout(self.header)
        self.header_layout.setContentsMargins(10, 10, 10, 10)
        
        self.name_header = QLabel("Name")
        self.name_header.setStyleSheet("font-weight: bold; color: #cccccc;")
        
        self.last_opened_header = QLabel("Last Opened")
        self.last_opened_header.setStyleSheet("font-weight: bold; color: #cccccc;")
        
        self.header_layout.addWidget(self.name_header)
        self.header_layout.addStretch()
        self.header_layout.addWidget(self.last_opened_header)
        
        # Add header to main layout
        self.layout.addWidget(self.header)
        
        # Create scroll area for projects
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QFrame.NoFrame)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        
        # Container for project items
        self.projects_container = QWidget()
        self.projects_container.setStyleSheet("background-color: #2B2B2B;")  # Add background color to container
        self.projects_layout = QVBoxLayout(self.projects_container)
        self.projects_layout.setContentsMargins(0, 0, 0, 0)
        self.projects_layout.setSpacing(1)  # Minimal spacing between projects
        
        # Add projects at the top, with stretch at the bottom
        self.projects_layout.addStretch()
        
        # Set container as scroll area widget
        self.scroll_area.setWidget(self.projects_container)
        
        # Add scroll area to main layout and make it take up all available space
        self.layout.addWidget(self.scroll_area, 1)  # Add stretch factor of 1
        
    def add_project(self, name, path, last_opened=""):
        """Add a project to the list"""
        project_item = ProjectItemWidget(name, path, last_opened)
        # Insert before the stretch
        self.projects_layout.insertWidget(self.projects_layout.count() - 1, project_item)
        return project_item
    
    def clear(self):
        """Clear all projects from the list"""
        # Remove all widgets except the stretch at the end
        while self.projects_layout.count() > 1:
            item = self.projects_layout.itemAt(0)
            if item.widget():
                item.widget().deleteLater()
            self.projects_layout.removeItem(item)

# Add after ImportDownloadWorker class
class LoadingDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Opening Project...")
        self.setWindowFlag(Qt.FramelessWindowHint)
        self.setWindowModality(Qt.ApplicationModal)
        self.setFixedSize(200, 100)
        layout = QVBoxLayout()
        self.label = QLabel("Opening project,\n please wait...")
        self.label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.label)
        self.setLayout(layout)
        self.setStyleSheet("""
            QDialog {
                background-color: #1D1D1D;
                color: #FFFFFF;
            }
            QLabel {
                background-color: none;
                color: #CCCCCC;
            }
        """)

class ProjectLoaderThread(QThread):
    finished = pyqtSignal(str, str)  # (mmtl_path, temp_dir)
    error = pyqtSignal(str)

    def __init__(self, mmtl_path):
        super().__init__()
        self.mmtl_path = mmtl_path

    def run(self):
        temp_dir = tempfile.mkdtemp()
        try:
            # Extract project
            with zipfile.ZipFile(self.mmtl_path, 'r') as zipf:
                zipf.extractall(temp_dir)

            # Verify structure
            required = ['meta.json', 'master.json', 'images/']
            if not all(os.path.exists(os.path.join(temp_dir, p)) for p in required):
                raise Exception("Invalid .mmtl file structure")

            self.finished.emit(self.mmtl_path, temp_dir)
        except Exception as e:
            self.error.emit(str(e))
            rmtree(temp_dir, ignore_errors=True)

class Home(QMainWindow):
    def __init__(self):
        super().__init__()
        self.settings = QSettings("YourCompany", "MangaOCRTool")
        self.init_ui()
        
    def init_ui(self):
        self.setWindowTitle("ManhwaOCR")
        self.setMinimumSize(800, 600)
        
        # Set the dark theme
        self.setStyleSheet(HOME_STYLES)
        
        # Create central widget
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        
        # Main layout
        self.main_layout = QHBoxLayout(self.central_widget)
        self.main_layout.setContentsMargins(10, 10, 10, 10)
    
        self.left_layout_layout = QVBoxLayout()
        self.left_layout_layout.setContentsMargins(10, 10, 10, 10)
        self.left_layout_layout.setSpacing(15)  # More spacing between buttons
        
        # Left layout buttons
        self.btn_new = QPushButton("New Project")
        self.btn_import = QPushButton("Import from WFWF")
        self.btn_open = QPushButton("Open Project")
        
        self.left_layout_layout.addWidget(self.btn_new)
        self.left_layout_layout.addWidget(self.btn_import)
        self.left_layout_layout.addWidget(self.btn_open)
        self.left_layout_layout.addStretch()

        # Connect button signals
        self.btn_new.clicked.connect(self.new_project)
        self.btn_open.clicked.connect(self.open_project)
        self.btn_import.clicked.connect(self.import_from_wfwf)

        # Left sidebar
        self.left_layout = QWidget()
        self.left_layout.setLayout(self.left_layout_layout)
        self.left_layout.setMaximumWidth(200)
        self.left_layout.setStyleSheet(HOME_LEFT_LAYOUT_STYLES)
        
        # Right content area
        self.content = QWidget()
        self.content_layout = QVBoxLayout(self.content)
        
        # Recent Projects header
        self.recent_label = QLabel("Recent Projects")
        self.recent_label.setStyleSheet("font-size: 24px; margin-bottom: 20px;")
        self.content_layout.addWidget(self.recent_label)
        
        # Projects list custom widget
        self.projects_list = ProjectsListWidget()
        self.content_layout.addWidget(self.projects_list)
        
        # Add widgets to main layout
        self.main_layout.addWidget(self.left_layout)
        self.main_layout.addWidget(self.content, 1)
        
        # Load recent projects
        self.load_recent_projects()

    # Add this function to calculate relative time
    def get_relative_time(self, timestamp_str):
        """Convert timestamp to relative time (e.g., '3 days ago')"""
        if not timestamp_str:
            return "Never opened"
            
        # Convert string timestamp to QDateTime
        timestamp = QDateTime.fromString(timestamp_str, Qt.ISODate)
        current_time = QDateTime.currentDateTime()
        
        # Calculate the time difference in seconds
        seconds = timestamp.secsTo(current_time)
        
        if seconds < 0:  # Future date (shouldn't happen, but just in case)
            return timestamp.toString("MMM d, yyyy h:mm AP")
            
        # Convert to appropriate units
        if seconds < 60:
            return "Just now"
        elif seconds < 3600:
            minutes = seconds // 60
            return f"{minutes} minute{'s' if minutes > 1 else ''} ago"
        elif seconds < 86400:
            hours = seconds // 3600
            return f"{hours} hour{'s' if hours > 1 else ''} ago"
        elif seconds < 604800:  # 7 days
            days = seconds // 86400
            return f"{days} day{'s' if days > 1 else ''} ago"
        elif seconds < 2592000:  # 30 days
            weeks = seconds // 604800
            return f"{weeks} week{'s' if weeks > 1 else ''} ago"
        elif seconds < 31536000:  # 365 days
            months = seconds // 2592000
            return f"{months} month{'s' if months > 1 else ''} ago"
        else:
            years = seconds // 31536000
            return f"{years} year{'s' if years > 1 else ''} ago"

    # Modify the load_recent_projects method to use relative time
    def load_recent_projects(self):
        recent_projects = self.settings.value("recent_projects", [])
        recent_timestamps = self.settings.value("recent_timestamps", {})
        
        self.projects_list.clear()
        for path in recent_projects:
            if os.path.exists(path):
                filename = os.path.basename(path)
                # Get relative time string
                timestamp = recent_timestamps.get(path, "")
                last_opened = self.get_relative_time(timestamp)
                self.projects_list.add_project(filename, path, last_opened)

    def open_project_from_path(self, path):
        if os.path.exists(path):
            self.launch_main_app(path)
        else:
            QMessageBox.warning(self, "Error", "Project file no longer exists")

    def new_project(self):
        dialog = NewProjectDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            source_path, project_path, language = dialog.get_paths()
            
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
                        'original_language': language,
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

    def update_recent_projects(self, project_path):
        # Update list of recent projects
        recent = self.settings.value("recent_projects", [])
        if project_path in recent:
            recent.remove(project_path)
        recent.insert(0, project_path)
        recent = recent[:5]  # Keep only last 5
        self.settings.setValue("recent_projects", recent)
        
        # Update timestamps dictionary
        timestamps = self.settings.value("recent_timestamps", {})
        # Add current timestamp for the opened project
        current_time = QDateTime.currentDateTime().toString(Qt.ISODate)
        timestamps[project_path] = current_time
        self.settings.setValue("recent_timestamps", timestamps)

    def launch_main_app(self, mmtl_path):
        # Show loading dialog
        self.loading_dialog = LoadingDialog(self)
        self.loading_dialog.show()

        # Create and start loader thread
        self.loader_thread = ProjectLoaderThread(mmtl_path)
        self.loader_thread.finished.connect(self.handle_project_loaded)
        self.loader_thread.error.connect(self.handle_project_error)
        self.loader_thread.start()

    def handle_project_loaded(self, mmtl_path, temp_dir):
        try:
            from app.main_window import MainWindow
            self.update_recent_projects(mmtl_path)
            
            # Create main window
            self.main_window = MainWindow()
            self.main_window.process_mmtl(mmtl_path, temp_dir)
            self.main_window.show()

            self.loading_dialog.close()
            
            self.close()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to launch project: {str(e)}")
            rmtree(temp_dir, ignore_errors=True)

    def handle_project_error(self, error_msg):
        self.loading_dialog.close()
        QMessageBox.critical(self, "Error", f"Failed to open project:\n{error_msg}")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = Home()
    window.show()
    sys.exit(app.exec_())