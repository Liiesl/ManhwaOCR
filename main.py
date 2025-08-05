import sys
from PyQt5.QtWidgets import (QApplication, QWidget, QVBoxLayout, QPushButton,  QFrame, QMainWindow, QLabel, QMessageBox,
                             QScrollArea, QHBoxLayout, QDialog)
# MODIFIED: Added QEvent for the changeEvent handler
from PyQt5.QtCore import Qt, QSettings, QDateTime, QThread, pyqtSignal, QEvent
from app.utils import new_project, open_project, import_from_wfwf, correct_filenames
from assets.styles import (HOME_STYLES, HOME_LEFT_LAYOUT_STYLES)
# MODIFIED: Import CustomTitleBar and WindowResizer from the new chrome.py file
from app.ui import CustomTitleBar, WindowResizer
import os, zipfile, tempfile
from shutil import rmtree
from app.ui.widgets import TitleBarState

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
        ## MODIFIED: Go frameless
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
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
                border: 1px solid #3E3E3E; /* Add a border for definition */
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
        
        ## MODIFIED: Go frameless ##
        self.setWindowFlags(Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground) # Makes rounded corners possible if desired
        
        self.init_ui()
        # MODIFIED: Instantiate the resizer class to make the window resizable
        self.resizer = WindowResizer(self)
        
    def init_ui(self):
        # self.setWindowTitle("ManhwaOCR") # No longer needed, title is in custom bar
        self.setMinimumSize(800, 600)
        
        # ## MODIFIED: Layout structure for frameless window ##
        # Main container widget
        self.container = QFrame()

        # Main vertical layout
        self.main_layout = QVBoxLayout(self.container)
        self.main_layout.setContentsMargins(1, 1, 1, 1) # Small margin for the border
        self.main_layout.setSpacing(0)
        
        # Add custom title bar
        self.title_bar = CustomTitleBar(self)
        self.main_layout.addWidget(self.title_bar)
        self.title_bar.setState(TitleBarState.HOME)

        # Set the dark theme
        self.setStyleSheet(HOME_STYLES)
        
        # Create central widget
        self.content_widget = QWidget() # This will hold the original layout
        self.main_layout.addWidget(self.content_widget)

        self.setCentralWidget(self.container)
        
        # Original main layout (now for content)
        self.content_layout_hbox = QHBoxLayout(self.content_widget)
        self.content_layout_hbox.setContentsMargins(10, 10, 10, 10)
    
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
        
        # Add widgets to content layout
        self.content_layout_hbox.addWidget(self.left_layout)
        self.content_layout_hbox.addWidget(self.content, 1)
        
        # Load recent projects
        self.load_recent_projects()

    # MODIFIED: Add changeEvent to update maximize icon when window state changes
    def changeEvent(self, event):
        """Override changeEvent to detect window state changes (e.g., maximize)."""
        if event.type() == QEvent.WindowStateChange:
            self.title_bar.update_maximize_icon()
        super().changeEvent(event)

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
        new_project(self)

    def open_project(self):
        open_project(self)

    def import_from_wfwf(self):
        import_from_wfwf(self)

    def correct_filenames(self, directory):
        return correct_filenames(directory)

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
            from app.ui.window import MainWindow
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

    # Always create the Home window instance. It will act as our controller.
    window = Home()

    project_to_open = None
    # Check if a .mmtl file path was passed as a command-line argument
    if len(sys.argv) > 1 and sys.argv[1].lower().endswith('.mmtl'):
        path = sys.argv[1]
        if os.path.exists(path):
            # The path is valid, store it for launching.
            project_to_open = path
        else:
            # The path was provided but is invalid. Show an error, and then
            # we will fall back to showing the normal Home window.
            QMessageBox.critical(window, "Error", f"The project file could not be found:\n{path}")

    # Now, decide what to do based on whether we have a project to open.
    if project_to_open:
        # A valid project path was provided.
        # Call the launch function, which will show the loading dialog.
        window.launch_main_app(project_to_open)
    else:
        # No valid project was provided via command line.
        # Show the normal 'Home' window with the recent projects list.
        window.show()

    sys.exit(app.exec_())