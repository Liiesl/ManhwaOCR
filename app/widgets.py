from PyQt5.QtWidgets import (QLabel, QGraphicsScene, QSizePolicy, QGraphicsPixmapItem, QGraphicsBlurEffect, QGraphicsEllipseItem, 
                             QGraphicsTextItem, QScrollArea, QGraphicsItem, QGraphicsRectItem, QGraphicsView, QGraphicsDropShadowEffect, 
                             QStyledItemDelegate, QTextEdit, QMenuBar, QAction, QDialog, QMessageBox, QFileDialog)
from PyQt5.QtCore import Qt, QRect, QThread, pyqtSignal, QRectF, QPointF, QObject, QDateTime, Qt, QDir
from PyQt5.QtGui import QPixmap, QPainter, QFont, QResizeEvent, QBrush, QColor, QPen, QTextOption, QFontDatabase
import qtawesome as qta
import os, zipfile, json, tempfile, re, shutil
from shutil import copyfile

class TextBoxSignals(QObject):
    rowDeleted = pyqtSignal(int)

class TextBoxItem(QGraphicsRectItem):
    def __init__(self, rect, row_number, text="", original_rect=None):
        super().__init__(QRectF(0, 0, rect.width(), rect.height()))  # Local rect starts at (0,0)
        # Set the item's position in the scene (this is where the rect will be drawn)
        self.setPos(rect.x(), rect.y())  # Position in the scene
        self.signals = TextBoxSignals()  # Signal holder
        self.setFlag(QGraphicsItem.ItemIsMovable, True)
        self.setFlag(QGraphicsItem.ItemIsSelectable, True)
        self.setFlag(QGraphicsItem.ItemSendsGeometryChanges, True)
        self.row_number = row_number
        self.original_rect = original_rect  # Store original image coordinates
        self.setBrush(QBrush(QColor(255, 255, 255)))
        self.setPen(QPen(QColor(0, 0, 0, 0), 1))
        self.corner_radius = 50
        self.min_width = 50  # Minimum width
        self.min_height = 30  # Minimum height
        self.resize_mode = False
        self.active_handle = None

        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(20)
        shadow.setColor(QColor(255, 255, 255, 150))
        shadow.setOffset(0, 0)
        self.setGraphicsEffect(shadow)

        self.handles = []
        self.handle_size = 10
        # Add more handles for better resizing control
        self.handle_positions = [
            Qt.TopLeftCorner, Qt.TopRightCorner, 
            Qt.BottomLeftCorner, Qt.BottomRightCorner,
            Qt.TopEdge, Qt.BottomEdge, Qt.LeftEdge, Qt.RightEdge
        ]
        
        for position in self.handle_positions:
            handle = QGraphicsRectItem(0, 0, self.handle_size, self.handle_size, self)
            handle.setFlag(QGraphicsItem.ItemIsMovable, False)  # Don't move independently
            handle.setFlag(QGraphicsItem.ItemSendsGeometryChanges, True)
            
            # Set different colors for corner and edge handles
            if position in [Qt.TopLeftCorner, Qt.TopRightCorner, Qt.BottomLeftCorner, Qt.BottomRightCorner]:
                handle.setBrush(QBrush(Qt.red))
            else:
                handle.setBrush(QBrush(Qt.blue))
                
            handle.setPen(QPen(Qt.black))
            handle.position = position
            handle.hide()
            self.handles.append(handle)
            
        self.update_handles_positions()

        # Create a circular remove button with an icon
        self.remove_button = QGraphicsEllipseItem(0, 0, 20, 20, self)  # Use ellipse for a circle
        self.remove_button.setBrush(QBrush(Qt.red))
        self.remove_button.setPen(QPen(Qt.black))
        self.remove_button.setPos(rect.width() - 30, -20)  # Adjust position (top-right corner)
        self.remove_button.hide()

        # Add icon using QtAwesome
        remove_icon = qta.icon('fa.times', color='white')  # Use FontAwesome 'times' icon
        pixmap = remove_icon.pixmap(16, 16)  # Generate a 16x16 pixmap
        self.remove_icon_item = QGraphicsPixmapItem(pixmap, self.remove_button)
        self.remove_icon_item.setOffset(1, 1)  # Center the icon within the button
        # Handle click
        self.remove_button.setFlag(QGraphicsItem.ItemIsSelectable, True)
        def on_remove_clicked(event):
            self.signals.rowDeleted.emit(self.row_number)
            event.accept()
        self.remove_button.mousePressEvent = on_remove_clicked

        self.text_item = QGraphicsTextItem(text, self)
        self.text_item.setDefaultTextColor(Qt.black)
        # Load custom font
        font_id = QFontDatabase.addApplicationFont("assets/fonts/animeace.ttf")
        font_family = QFontDatabase.applicationFontFamilies(font_id)[0] if font_id != -1 else "Arial"
        font = QFont(font_family)
        font.setPointSize(12)
        self.text_item.setFont(font)
        self.setRect(rect)
        
        # Set cursor shapes based on position
        self.setCursor(Qt.SizeAllCursor)

    def setRect(self, rect):
        # Enforce minimum size
        if rect.width() < self.min_width:
            rect.setWidth(self.min_width)
        if rect.height() < self.min_height:
            rect.setHeight(self.min_height)
            
        # Ensure the local rect starts at (0,0) and has the new size
        new_rect = QRectF(0, 0, rect.width(), rect.height())
        super().setRect(new_rect)
        
        # Center the text item within the rectangle
        self.text_item.setPos(rect.x() + 10, rect.y() + 10)
        self.text_item.setTextWidth(rect.width() - 20)
        
        # Center align the text
        document = self.text_item.document()
        document.setDefaultTextOption(QTextOption(Qt.AlignCenter))
        
        self.adjust_font_size()
        # Update remove button position
        self.remove_button.setPos(rect.width() - 20, -20)
        self.update_handles_positions()

    def adjust_font_size(self):
        """Adjust font size to ensure text fills the rectangle while remaining readable."""
        available_width = self.rect().width() - 20  # Account for padding
        available_height = self.rect().height() - 20
        
        text = self.text_item.toPlainText()
        if not text:
            return
        
        font = self.text_item.font()
        
        # Start with a larger font size and decrease until it fits
        # or increase from current size if there's room to grow
        min_font_size = 6  # Minimum readable size
        max_font_size = 72  # Maximum font size to try
        
        # Binary search to find optimal font size
        low = min_font_size
        high = max_font_size
        optimal_size = low
        
        while low <= high:
            mid = (low + high) // 2
            font.setPointSize(mid)
            self.text_item.setFont(font)
            
            text_rect = self.text_item.boundingRect()
            
            if text_rect.height() <= available_height and text_rect.width() <= available_width:
                optimal_size = mid  # This size fits, try larger
                low = mid + 1
            else:
                high = mid - 1  # Too large, try smaller
        
        # Set the optimal font size
        font.setPointSize(optimal_size)
        self.text_item.setFont(font)
        
        # Center the text within the box
        document = self.text_item.document()
        document.setDefaultTextOption(QTextOption(Qt.AlignCenter))
        
        # Adjust vertical position for center alignment
        text_height = self.text_item.boundingRect().height()
        vertical_padding = (self.rect().height() - text_height) / 2
        if vertical_padding > 0:
            self.text_item.setPos(self.rect().x() + 10, self.rect().y() + vertical_padding)

    def update_handles_positions(self):
        """Position handles at the corners and edges of the rectangle."""
        rect = self.rect()
        for handle in self.handles:
            # Corner positions
            if handle.position == Qt.TopLeftCorner:
                handle.setPos(rect.topLeft())
            elif handle.position == Qt.TopRightCorner:
                handle.setPos(rect.topRight() - QPointF(self.handle_size, 0))
            elif handle.position == Qt.BottomLeftCorner:
                handle.setPos(rect.bottomLeft() - QPointF(0, self.handle_size))
            elif handle.position == Qt.BottomRightCorner:
                handle.setPos(rect.bottomRight() - QPointF(self.handle_size, self.handle_size))
            # Edge positions
            elif handle.position == Qt.TopEdge:
                handle.setPos(rect.left() + rect.width()/2 - self.handle_size/2, rect.top())
            elif handle.position == Qt.BottomEdge:
                handle.setPos(rect.left() + rect.width()/2 - self.handle_size/2, rect.bottom() - self.handle_size)
            elif handle.position == Qt.LeftEdge:
                handle.setPos(rect.left(), rect.top() + rect.height()/2 - self.handle_size/2)
            elif handle.position == Qt.RightEdge:
                handle.setPos(rect.right() - self.handle_size, rect.top() + rect.height()/2 - self.handle_size/2)

    def get_cursor_for_handle(self, handle):
        """Return appropriate cursor based on handle position."""
        if handle.position in [Qt.TopLeftCorner, Qt.BottomRightCorner]:
            return Qt.SizeFDiagCursor
        elif handle.position in [Qt.TopRightCorner, Qt.BottomLeftCorner]:
            return Qt.SizeBDiagCursor
        elif handle.position in [Qt.TopEdge, Qt.BottomEdge]:
            return Qt.SizeVerCursor
        elif handle.position in [Qt.LeftEdge, Qt.RightEdge]:
            return Qt.SizeHorCursor
        return Qt.ArrowCursor

    def mousePressEvent(self, event):
        """Handle mouse press events for both moving and resizing."""
        # Check if we clicked on a handle
        for handle in self.handles:
            if handle.isVisible() and handle.contains(handle.mapFromScene(event.scenePos())):
                self.resize_mode = True
                self.active_handle = handle
                self.drag_start_pos = event.pos()
                self.drag_start_rect = self.rect()
                self.setCursor(self.get_cursor_for_handle(handle))
                event.accept()
                return
                
        # If not clicking on a handle, proceed with normal move
        self.resize_mode = False
        self.active_handle = None
        self.setCursor(Qt.SizeAllCursor)
        super().mousePressEvent(event)
        
    def mouseMoveEvent(self, event):
        """Handle mouse move events for both moving and resizing."""
        if self.resize_mode and self.active_handle:
            delta = event.pos() - self.drag_start_pos
            new_rect = QRectF(self.drag_start_rect)
            
            # Handle resizing logic based on which handle is active
            if self.active_handle.position == Qt.TopLeftCorner:
                new_rect.setTopLeft(new_rect.topLeft() + delta)
            elif self.active_handle.position == Qt.TopRightCorner:
                new_rect.setTopRight(new_rect.topRight() + delta)
            elif self.active_handle.position == Qt.BottomLeftCorner:
                new_rect.setBottomLeft(new_rect.bottomLeft() + delta)
            elif self.active_handle.position == Qt.BottomRightCorner:
                new_rect.setBottomRight(new_rect.bottomRight() + delta)
            elif self.active_handle.position == Qt.TopEdge:
                new_rect.setTop(new_rect.top() + delta.y())
            elif self.active_handle.position == Qt.BottomEdge:
                new_rect.setBottom(new_rect.bottom() + delta.y())
            elif self.active_handle.position == Qt.LeftEdge:
                new_rect.setLeft(new_rect.left() + delta.x())
            elif self.active_handle.position == Qt.RightEdge:
                new_rect.setRight(new_rect.right() + delta.x())
                
            if new_rect.width() >= self.min_width and new_rect.height() >= self.min_height:
                self.setRect(new_rect)
                # Update original_rect to current scene bounding rect
                if self.original_rect:
                    self.original_rect = self.sceneBoundingRect()
            
            event.accept()
        else:
            super().mouseMoveEvent(event)
            
        self.update_handles_positions()
    
    def mouseReleaseEvent(self, event):
        """Handle mouse release events."""
        self.resize_mode = False
        self.active_handle = None
        self.setCursor(Qt.SizeAllCursor)
        super().mouseReleaseEvent(event)
        self.update_handles_positions()
    
    def itemChange(self, change, value):
        if change == QGraphicsItem.ItemPositionChange:
            # Keep within scene bounds
            if self.scene():
                scene_rect = self.scene().sceneRect()
                item_rect = self.rect().translated(value)
                
                # Check if the item would move outside the scene boundaries
                if not scene_rect.contains(item_rect):
                    # Adjust the position to keep it inside
                    new_pos = value
                    
                    # Adjust horizontally
                    if item_rect.left() < scene_rect.left():
                        new_pos.setX(scene_rect.left())
                    elif item_rect.right() > scene_rect.right():
                        new_pos.setX(scene_rect.right() - self.rect().width())
                    
                    # Adjust vertically
                    if item_rect.top() < scene_rect.top():
                        new_pos.setY(scene_rect.top())
                    elif item_rect.bottom() > scene_rect.bottom():
                        new_pos.setY(scene_rect.bottom() - self.rect().height())
                    
                    return new_pos
                    
        elif change == QGraphicsItem.ItemSelectedHasChanged:
            # Show/hide handles and remove button when selected
            selected = bool(value)
            for handle in self.handles:
                handle.setVisible(selected)
            self.remove_button.setVisible(selected)
                
        elif change == QGraphicsItem.ItemSceneHasChanged:
            if value is not None:
                self.update_handles_positions()
                
        return super().itemChange(change, value)

    def paint(self, painter, option, widget):
        """Draw rounded rectangle with padding and shadow."""
        painter.setBrush(self.brush())
        painter.setPen(self.pen())
        painter.drawRoundedRect(self.rect(), self.corner_radius, self.corner_radius)
        
    def cleanup(self):
        """Properly clean up all child items and disconnect signals"""
        # Safely disconnect signals if they exist
        if hasattr(self, 'signals'):
            try:
                self.signals.rowDeleted.disconnect()
            except (TypeError, RuntimeError):
                pass  # Already disconnected or C++ object deleted
        
        # Remove child items
        for handle in self.handles[:]:
            if handle.scene():
                handle.scene().removeItem(handle)
            handle.setParentItem(None)
        self.handles = []

        if self.text_item and self.text_item.scene():
            self.text_item.scene().removeItem(self.text_item)
            self.text_item = None

        if self.remove_button and self.remove_button.scene():
            self.remove_button.scene().removeItem(self.remove_button)
            self.remove_button = None

        if self.scene():
            self.scene().removeItem(self)
            
class ResizableImageLabel(QGraphicsView):
    textBoxDeleted = pyqtSignal(int)  # Signal to forward deletion

    def __init__(self, pixmap, filename):
        super().__init__()
        self.setScene(QGraphicsScene())
        self.setRenderHints(QPainter.Antialiasing | QPainter.SmoothPixmapTransform)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        self.original_pixmap = pixmap
        self.current_pixmap = pixmap
        self.filename = filename
        self.pixmap_item = self.scene().addPixmap(self.current_pixmap)
        self.scene().setSceneRect(0, 0, self.original_pixmap.width(), self.original_pixmap.height())  # Set scene to original size
        self.setInteractive(True)
        self.text_boxes = []
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)  # Adjusted size policy
        self.original_text_entries = {}  # Store original text entries
        
    def hasHeightForWidth(self):
        return True  # Enable height-for-width

    def heightForWidth(self, width):
        if self.original_pixmap.isNull():
            return 0
        return int((self.original_pixmap.height() / self.original_pixmap.width()) * width)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        
        # Use Qt's single shot timer to defer the fitInView call 
        from PyQt5.QtCore import QTimer
        QTimer.singleShot(0, self.adjustView)
        
    def adjustView(self):
        if self.pixmap_item and not self.original_pixmap.isNull():
            self.fitInView(self.scene().sceneRect(), Qt.KeepAspectRatio)
            self.viewport().update()
        
    def apply_translation(self, text_entries):
        # Clear existing text boxes safely
        for text_box in self.text_boxes[:]:  # Iterate over a copy
            try:
                text_box.signals.rowDeleted.disconnect()  # Disconnect signals
            except (TypeError, RuntimeError):
                pass  # Already disconnected or object deleted
            text_box.cleanup()  # Call cleanup to remove child items
            self.scene().removeItem(text_box)  # Remove from the scene
            self.text_boxes.remove(text_box)  # Remove from the list

        self.text_boxes.clear()  # Ensure the list is emptied

        # Force garbage collection to clean up deleted objects
        import gc
        gc.collect()

        # Add new text boxes
        self.original_text_entries = text_entries.copy()
        for row, entry in text_entries.items():
            coords = entry['coordinates']
            x = min(p[0] for p in coords)
            y = min(p[1] for p in coords)
            width = max(p[0] for p in coords) - x
            height = max(p[1] for p in coords) - y
            
            text_box = TextBoxItem(QRectF(0, 0, width, height), row, entry['text'])
            text_box.setPos(x, y)
            self.scene().addItem(text_box)
            text_box.signals.rowDeleted.connect(self.handle_text_box_deleted)
            self.text_boxes.append(text_box)

    def handle_text_box_deleted(self, row_number):
        for text_box in self.text_boxes:
            if text_box.row_number == row_number:
                # Disconnect signals before removal
                try:
                    text_box.signals.rowDeleted.disconnect()
                except TypeError:
                    pass  # Already disconnected
                text_box.cleanup()
                self.scene().removeItem(text_box)
                self.text_boxes.remove(text_box)
                break
        self.textBoxDeleted.emit(row_number)

    def cleanup(self):
        """Clean up resources before removal."""
        # Remove handles
        for handle in self.handles:
            handle.setParentItem(None)
        # Remove text item
        if self.text_item:
            self.text_item.setParentItem(None)
        # Remove any effects
        self.setGraphicsEffect(None)
            
    def get_text_boxes(self):
        return self.text_boxes
    
    def __del__(self):
        print(f"DEBUG: TextBoxItem destructor called for row {self.row_number}")
        self.cleanup()

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
            y = scroll_height - overlay_height - 30  # 10 pixels from the bottom

            self.overlay_widget.setGeometry(x, y, overlay_width, overlay_height)

class TextEditDelegate(QStyledItemDelegate):
    def createEditor(self, parent, option, index):
        editor = QTextEdit(parent)
        editor.setAcceptRichText(False)
        editor.setLineWrapMode(QTextEdit.WidgetWidth)
        return editor

    def setEditorData(self, editor, index):
        text = index.model().data(index, Qt.DisplayRole)
        editor.setPlainText(text)

    def setModelData(self, editor, model, index):
        model.setData(index, editor.toPlainText(), Qt.EditRole)

    def updateEditorGeometry(self, editor, option, index):
        editor.setGeometry(option.rect)

class TextEditDelegate(QStyledItemDelegate):
    def createEditor(self, parent, option, index):
        editor = QTextEdit(parent)
        editor.setAcceptRichText(False)
        editor.setLineWrapMode(QTextEdit.WidgetWidth)
        return editor

    def setEditorData(self, editor, index):
        text = index.model().data(index, Qt.DisplayRole)
        editor.setPlainText(text)

    def setModelData(self, editor, model, index):
        model.setData(index, editor.toPlainText(), Qt.EditRole)

    def updateEditorGeometry(self, editor, option, index):
        editor.setGeometry(option.rect)

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
        from main import NewProjectDialog  # Import needed dialog
        dialog = NewProjectDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            source_path, project_path = dialog.get_paths()
            if not source_path or not project_path:
                QMessageBox.warning(self, "Error", "Please select both source and project location")
                return
            
            try:
                with zipfile.ZipFile(project_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                    meta = {
                        'created': QDateTime.currentDateTime().toString(Qt.ISODate),
                        'source': source_path,
                        'version': '1.0'
                    }
                    zipf.writestr('meta.json', json.dumps(meta, indent=2))
                    images_dir = 'images/'
                    if os.path.isfile(source_path):
                        zipf.write(source_path, images_dir + os.path.basename(source_path))
                    elif os.path.isdir(source_path):
                        for file in os.listdir(source_path):
                            if file.lower().endswith(('png', 'jpg', 'jpeg')):
                                zipf.write(os.path.join(source_path, file), images_dir + file)
                    zipf.writestr('master.json', json.dumps([]))
                self.load_project(project_path)
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to create project: {str(e)}")

    def open_project(self):
        file, _ = QFileDialog.getOpenFileName(self, "Open Project", "", "Manga Translation Files (*.mmtl)")
        if file:
            self.load_project(file)

    def load_project(self, mmtl_path):
        temp_dir = tempfile.mkdtemp()
        with zipfile.ZipFile(mmtl_path, 'r') as zipf:
            zipf.extractall(temp_dir)
        
        if not all(os.path.exists(os.path.join(temp_dir, p)) for p in ['meta.json', 'master.json', 'images/']):
            QMessageBox.critical(self, "Error", "Invalid .mmtl file")
            return
        
        # Clean previous project
        if hasattr(self, 'temp_dir'):
            import shutil
            shutil.rmtree(self.temp_dir, ignore_errors=True)
        
        self.mmtl_path = mmtl_path
        self.temp_dir = temp_dir
        self.main_window.process_mmtl(mmtl_path, temp_dir)

    def import_from_wfwf(self):
        from main import ImportWFWFDialog  # Import needed dialog
        dialog = ImportWFWFDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            temp_dir = dialog.get_temp_dir()
            if temp_dir and os.path.exists(temp_dir):
                self.create_project_from_wfwf(temp_dir, dialog.get_url())

    def create_project_from_wfwf(self, temp_dir, url):
        project_path, _ = QFileDialog.getSaveFileName(
            self, "Save Project", QDir.homePath(), "Manga Translation Files (*.mmtl)"
        )
        if project_path:
            try:
                filename_map = self.correct_filenames(temp_dir)
                corrected_dir = tempfile.mkdtemp()
                for old_name, new_name in filename_map.items():
                    src = os.path.join(temp_dir, old_name)
                    dst = os.path.join(corrected_dir, new_name)
                    copyfile(src, dst)
                with zipfile.ZipFile(project_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                    meta = {
                        'created': QDateTime.currentDateTime().toString(Qt.ISODate),
                        'source': url,
                        'version': '1.0'
                    }
                    zipf.writestr('meta.json', json.dumps(meta, indent=2))
                    images_dir = 'images/'
                    for img in os.listdir(corrected_dir):
                        if img.lower().endswith(('png', 'jpg', 'jpeg')):
                            zipf.write(os.path.join(corrected_dir, img), os.path.join(images_dir, img))
                    zipf.writestr('master.json', json.dumps([]))
                self.load_project(project_path)
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to create project: {str(e)}")
            finally:
                shutil.rmtree(temp_dir)
                shutil.rmtree(corrected_dir)

    def go_to_home(self):
        from main import Home
        self.home = Home()
        self.home.show()
        self.close()

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
            self.mmtl_path = file_path
            self.main_window.save_project()  # Reuse existing save logic with new path