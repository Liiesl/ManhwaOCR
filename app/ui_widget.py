from PyQt5.QtWidgets import QProgressBar, QMenuBar, QAction, QDialog, QMessageBox, QFileDialog, QTextEdit, QStyledItemDelegate, QScrollArea
from PyQt5.QtCore import QTimer, QDateTime, Qt
import qtawesome as qta

class MenuBar(QMenuBar):
    def __init__(self, parent):
        super().__init__(parent)
        self.main_window = parent  # Reference to main window
        self.setStyleSheet("""
         
            QMenuBar {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #2D2D2D, stop:1 #1E1E1E);
                padding: 5px;
            }
            QMenuBar::item {
                background-color: transparent;
                padding: 8px 16px;
                margin: 0px 2px;
                border-radius: 4px;
            }
            QMenuBar::item:selected {
                background-color: #4A4A4A;
                color: #FFFFFF;
            }
        """)                   
        self.create_menu_bar()
        # Add other menus here
        
    def create_menu_bar(self):
        # File menu
        file_menu = self.addMenu("File")
        file_menu.setStyleSheet("""
            QMenu {
                background-color: #3A3A3A;
                color: #FFFFFF;
                border: none;
                border-radius: 4px;
            }
            QMenu::item {
                padding: 8px 16px;
                border-radius: 4px;
            }
            QMenu::item:selected {
                background-color: #4A4A4A;
            }
        """)
        
        # File menu actions with icons and shortcuts
        file_menu_action = file_menu.menuAction()
        file_menu_action.setIcon(qta.icon('fa5s.file', color="white"))

        new_project_action = QAction(qta.icon('fa5s.file-alt', color="white"), "New Project", self)
        new_project_action.setShortcut("Ctrl+N")
        new_project_action.triggered.connect(self.new_project)
        file_menu.addAction(new_project_action)
        
        open_project_action = QAction(qta.icon('fa5s.folder-open', color="white"), "Open Project", self)
        open_project_action.setShortcut("Ctrl+O")
        open_project_action.triggered.connect(self.open_project)
        file_menu.addAction(open_project_action)

        import_wfwf_action = QAction(qta.icon('fa5s.file-import', color="white"), "Import from WFWF", self)
        import_wfwf_action.triggered.connect(self.import_from_wfwf)
        file_menu.addAction(import_wfwf_action)

        file_menu.addSeparator()
        
        save_action = QAction(qta.icon('fa5s.save', color="white"), "Save Project", self)
        save_action.setShortcut("Ctrl+S")
        save_action.triggered.connect(self.main_window.save_project)
        file_menu.addAction(save_action)
        
        save_as_action = QAction(qta.icon('fa5s.download', color="white"), "Save Project As...", self)
        save_as_action.setShortcut("Ctrl+Shift+S")
        save_as_action.triggered.connect(self.save_project_as)
        file_menu.addAction(save_as_action)
        
        file_menu.addSeparator()
        
        home_action = QAction(qta.icon('fa5s.home', color="white"), "Go to Home", self)
        home_action.triggered.connect(self.go_to_home)
        file_menu.addAction(home_action)

    def new_project(self):
        from utils.project_processing import new_project
        new_project(self)

    def open_project(self):
        from utils.project_processing import open_project
        open_project(self)

    def import_from_wfwf(self):
        from utils.project_processing import import_from_wfwf
        import_from_wfwf(self)

    def correct_filenames(self, directory):
        from utils.project_processing import correct_filenames
        return correct_filenames(directory)

    def go_to_home(self):
        from main import Home
        self.home = Home()
        self.home.show()
        self.main_window.close()
    
    def save_project_as(self):
        """Handle Save As functionality"""
        options = QFileDialog.Options()
        file_path, _ = QFileDialog.getSaveFileName(
            self, 
            "Save Project As", 
            "", 
            "Manga Translation Project (*.mmtl)", 
            options=options
        )
        
        if file_path:
            if not file_path.endswith('.mmtl'):
                file_path += '.mmtl'
            self.main_window.mmtl_path = file_path
            self.main_window.save_project()  # Reuse existing save logic with new path

class CustomProgressBar(QProgressBar):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(20)
        
        # Progress animation variables
        self.current_progress = 0
        self.target_progress = 0
        self.processing_times = []
        self.start_time = None
        
        # Timers
        self.flat_progress_timer = QTimer(self)
        self.progress_timer = QTimer(self)
        self.flat_progress_timer.timeout.connect(self.update_flat_progress)
        self.progress_timer.timeout.connect(self.update_progress_smoothly)

    def start_initial_progress(self):
        """Start the initial flat progress phase"""
        self.current_progress = 0
        self.target_progress = 0
        self.processing_times.clear()
        self.start_time = QDateTime.currentDateTime()
        
        # Flat progress timer setup
        self.flat_progress_timer_duration = 5000  # 5 seconds
        self.flat_progress_timer_interval = 70
        self.flat_progress_steps = self.flat_progress_timer_duration // self.flat_progress_timer_interval
        self.flat_progress_increment = 20 / self.flat_progress_steps
        self.flat_progress_timer.start(self.flat_progress_timer_interval)

    def update_flat_progress(self):
        if self.current_progress < 20:
            self.current_progress += self.flat_progress_increment
            self.setValue(int(self.current_progress))
        else:
            self.flat_progress_timer.stop()
            self.progress_timer.start(self.calculate_dynamic_interval())

    def update_target_progress(self, progress):
        """Update target progress from external source"""
        self.target_progress = min(int(progress), 100)
        self.progress_timer.setInterval(self.calculate_dynamic_interval())

    def calculate_dynamic_interval(self):
        """Calculate interval based on remaining progress"""
        remaining = 100 - self.current_progress
        if remaining <= 0:
            return 100
        
        # Calculate based on average processing time if available
        if self.processing_times:
            avg_time = sum(self.processing_times) / len(self.processing_times)
            remaining_time = avg_time * (100 - self.current_progress)
            interval = int((remaining_time / remaining) * 1000)
            return max(50, min(interval, 500))
        
        return 100  # Default interval

    def update_progress_smoothly(self):
        remaining = self.target_progress - self.current_progress
        if remaining <= 0:
            return

        increment = max(1, min(remaining, 3))
        self.current_progress += increment
        self.setValue(int(self.current_progress))

        # Update interval dynamically
        self.progress_timer.setInterval(self.calculate_dynamic_interval())

    def record_processing_time(self):
        """Record time for one processing unit"""
        if self.start_time:
            end_time = QDateTime.currentDateTime()
            processing_time = self.start_time.msecsTo(end_time) / 1000
            self.processing_times.append(processing_time)
            self.start_time = QDateTime.currentDateTime()

    def reset(self):
        """Reset progress to zero"""
        self.current_progress = 0
        self.target_progress = 0
        self.setValue(0)
        self.processing_times.clear()
        self.flat_progress_timer.stop()
        self.progress_timer.stop()

class TextEditDelegate(QStyledItemDelegate):
    def createEditor(self, parent, option, index):
        editor = QTextEdit(parent)
        editor.setAcceptRichText(False)
        editor.setLineWrapMode(QTextEdit.WidgetWidth) # Use WidgetWidth for auto-wrap
        # editor.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff) # Optional: hide scrollbar in editor
        return editor

    def setEditorData(self, editor, index):
        text = index.model().data(index, Qt.DisplayRole)
        editor.setPlainText(text)

    def setModelData(self, editor, model, index):
        model.setData(index, editor.toPlainText(), Qt.EditRole)

    def updateEditorGeometry(self, editor, option, index):
        # Provide sufficient height based on content or use table row height
        editor.setGeometry(option.rect)

    # Optional: Adjust size hint for better row height calculation
    def sizeHint(self, option, index):
        size = super().sizeHint(option, index)
        # Consider calculating height based on text content if needed
        # For simplicity, rely on adjust_row_heights in MainWindow for now
        return size
    
class CustomScrollArea(QScrollArea):
    def __init__(self, overlay_widget, parent=None):
        super().__init__(parent)
        self.overlay_widget = overlay_widget

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.update_overlay_position()

    def update_overlay_position(self):
        if self.overlay_widget:
            overlay_width = 300 # Consider making these dynamic or constants
            overlay_height = 60
            # Use viewport size for positioning relative to visible area
            viewport_width = self.viewport().width()
            viewport_height = self.viewport().height()

            # Position relative to viewport, adjust for scrollbar width if necessary
            scrollbar_width = self.verticalScrollBar().width() if self.verticalScrollBar().isVisible() else 0
            x = (viewport_width - overlay_width) // 2
            y = viewport_height - overlay_height - 10 # 10 pixels from bottom of viewport

            # Map viewport coordinates to widget coordinates if overlay is child of self
            # If overlay is child of viewport(), positioning is simpler
            # Assuming overlay_widget is child of self (the QScrollArea)
            self.overlay_widget.setGeometry(x, y, overlay_width, overlay_height)
            self.overlay_widget.raise_() # Ensure it stays on top