from PyQt5.QtWidgets import ( QGraphicsScene, QSizePolicy, QGraphicsPixmapItem, QGraphicsEllipseItem, 
                             QGraphicsTextItem, QScrollArea, QGraphicsItem, QGraphicsRectItem, QGraphicsView, QGraphicsDropShadowEffect, 
                             QStyledItemDelegate, QTextEdit, )
from PyQt5.QtCore import Qt, pyqtSignal, QRectF, QPointF, QObject
from PyQt5.QtGui import QPainter, QFont, QBrush, QColor, QPen, QTextOption, QFontDatabase, QPainterPath
import qtawesome as qta

class TextBoxSignals(QObject):
    rowDeleted = pyqtSignal(int)
    selectedChanged = pyqtSignal(bool, int)  # Add this line

class TextBoxItem(QGraphicsRectItem):
    def __init__(self, rect, row_number, text="", original_rect=None, initial_style=None):
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
        self._bubble_type = 1 # Default: Rounded Rectangle, overridden by style
        self._auto_font_size = True # Default, overridden by style

        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(20)
        shadow.setColor(QColor(255, 255, 255, 150))
        shadow.setOffset(0, 0)
        self.setGraphicsEffect(shadow)

        self.handles = []
        self.handle_size = 20
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
        self.remove_button = QGraphicsEllipseItem(0, 0, 40, 40, self)  # Use ellipse for a circle
        self.remove_button.setBrush(QBrush(Qt.red))
        self.remove_button.setPen(QPen(Qt.black))
        self.remove_button.setPos(rect.width() -100, -100)  # Adjust position (top-right corner)
        self.remove_button.hide()

        # Add icon using QtAwesome
        remove_icon = qta.icon('fa.times', color='white')  # Use FontAwesome 'times' icon
        pixmap = remove_icon.pixmap(30, 30)  # Generate a 16x16 pixmap
        self.remove_icon_item = QGraphicsPixmapItem(pixmap, self.remove_button)
        self.remove_icon_item.setOffset(1, 1)  # Center the icon within the button
        # Handle click
        self.remove_button.setFlag(QGraphicsItem.ItemIsSelectable, True)
        def on_remove_clicked(event):
            self.signals.rowDeleted.emit(self.row_number)
            event.accept()
        self.remove_button.mousePressEvent = on_remove_clicked

        self.text_item = QGraphicsTextItem(text, self)
        # Apply the initial style passed during creation
        if initial_style:
             self.apply_styles(initial_style)
        else:
             # Apply some basic defaults if no style provided (shouldn't happen ideally)
             self.setBrush(QBrush(QColor(255, 255, 255)))
             self.setPen(QPen(QColor(0, 0, 0), 1))
             self.text_item.setDefaultTextColor(Qt.black)
             font = QFont("Arial", 12) # Basic fallback font
             self.text_item.setFont(font)
             # Default alignment
             doc_option = self.text_item.document().defaultTextOption()
             doc_option.setAlignment(Qt.AlignCenter)
             self.text_item.document().setDefaultTextOption(doc_option)

        # Final setup after styling
        self.setRect(QRectF(0, 0, rect.width(), rect.height())) # Call setRect AFTER potential styling
        self.setCursor(Qt.SizeAllCursor)

    def apply_styles(self, style_dict):
        """Applies the given style dictionary to the item."""
        # --- Shape & Appearance ---
        self._bubble_type = style_dict.get('bubble_type', 1) # Store type for paint()
        self.corner_radius = style_dict.get('corner_radius', 50)

        # --- Colors ---
        bg_color = QColor(style_dict.get('bg_color', '#ffffffff'))
        border_color = QColor(style_dict.get('border_color', '#ff000000'))
        text_color = QColor(style_dict.get('text_color', '#ff000000'))
        border_width = style_dict.get('border_width', 1)

        self.setBrush(QBrush(bg_color))
        pen = QPen(border_color, border_width)
        # Make border transparent if width is 0
        if border_width == 0:
             pen.setStyle(Qt.NoPen)
        else:
            pen.setStyle(Qt.SolidLine) # Ensure it's solid otherwise
        self.setPen(pen)
        self.text_item.setDefaultTextColor(text_color)

        # --- Font ---
        font_family = style_dict.get('font_family', "Arial")
        font_size = style_dict.get('font_size', 12)
        font_bold = style_dict.get('font_bold', False)
        font_italic = style_dict.get('font_italic', False)
        alignment_index = style_dict.get('text_alignment', 1) # 0:Left, 1:Center, 2:Right
        self._auto_font_size = style_dict.get('auto_font_size', True)

        # Try loading the font family
        font = QFont()
        font.setFamily(font_family) # Set family first
        # Check if the family was successfully set (or resolved to a fallback)
        # QFontInfo might be needed for robust check, but setFamily is usually enough
        font.setPointSize(font_size)
        font.setBold(font_bold)
        font.setItalic(font_italic)
        self.text_item.setFont(font)

        # --- Text Alignment ---
        alignment = Qt.AlignCenter # Default
        if alignment_index == 0:
            alignment = Qt.AlignLeft
        elif alignment_index == 2:
            alignment = Qt.AlignRight
        # Apply alignment to the text document option
        doc_option = self.text_item.document().defaultTextOption()
        doc_option.setAlignment(alignment | Qt.AlignVCenter) # Add vertical centering
        self.text_item.document().setDefaultTextOption(doc_option)

        # --- Final Adjustments ---
        # Call adjust_font_size if auto-sizing is enabled
        self.setRect(self.rect()) # Recalculate text position/width based on new style

        self.update() # Redraw the item

    def setRect(self, rect):
        # Enforce minimum size (logic moved from original __init__)
        new_width = max(rect.width(), self.min_width)
        new_height = max(rect.height(), self.min_height)
        
        # The item's own rect is always at (0,0)
        local_rect = QRectF(0, 0, new_width, new_height)
        
        # Only call super().setRect if the rect actually changes
        if local_rect != self.rect():
             super().setRect(local_rect)

        # Adjust text item position and width within the bounds
        padding = 10 # Padding around text
        self.text_item.setTextWidth(max(0, new_width - 2 * padding))

        # Recalculate font size and position
        self.adjust_font_size() # This now handles alignment and positioning

        # Update handle and button positions relative to the new rect
        self.remove_button.setPos(new_width - 20, -20) # Relative to top-right of the item's rect
        self.update_handles_positions()

    def adjust_font_size(self):
        """Adjust font size and position based on current settings."""
        padding = 10
        available_width = self.rect().width() - 2 * padding
        available_height = self.rect().height() - 2 * padding

        if available_width <= 0 or available_height <= 0:
            # Ensure text item exists before clearing
            if self.text_item:
                self.text_item.setPlainText("") # Hide text if no space
            return

        # Ensure text_item exists
        if not self.text_item:
            return

        text = self.text_item.toPlainText()
        if not text:
            self.text_item.setPos(padding, padding) # Reset position even if empty
            return

        font = self.text_item.font()
        
        if self._auto_font_size:
            min_font_size = 6
            max_font_size = 72
            
            # Binary search to find optimal font size
            low = min_font_size
            high = max_font_size
            optimal_size = low
            
            while low <= high:
                mid = (low + high) // 2
                font.setPointSize(mid)
                self.text_item.setFont(font)
                
                # Use boundingRect for actual rendered width/height
                text_rect = self.text_item.boundingRect()
                
                if text_rect.height() <= available_height and text_rect.width() <= available_width:
                    optimal_size = mid  # This size fits, try larger
                    low = mid + 1
                else:
                    high = mid - 1  # Too large, try smaller
            
            # Set the optimal font size
            font.setPointSize(optimal_size)
            self.text_item.setFont(font)
        
        # --- Calculate vertical position for VCenter ---
        text_height = self.text_item.boundingRect().height()
        vertical_offset = (self.rect().height() - text_height) / 2
        vertical_offset = max(padding, vertical_offset) # Ensure it respects top padding
        
        # Horizontal alignment is handled by the document's default text option
        # which should already be set in apply_styles()
        
        # Set the top-left position of the QGraphicsTextItem
        self.text_item.setPos(padding, vertical_offset)

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
            self.signals.selectedChanged.emit(selected, self.row_number)
                
        elif change == QGraphicsItem.ItemSceneHasChanged:
            if value is not None:
                self.update_handles_positions()
                
        return super().itemChange(change, value)

    def paint(self, painter, option, widget):
        """Draw the shape based on bubble_type."""
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setBrush(self.brush())
        painter.setPen(self.pen())

        rect = self.rect()

        if self._bubble_type == 0: # Rectangle
            painter.drawRect(rect)
        elif self._bubble_type == 1: # Rounded Rectangle
            radius = min(rect.width() / 2, rect.height() / 2, self.corner_radius) # Clamp radius
            painter.drawRoundedRect(rect, radius, radius)
        elif self._bubble_type == 2: # Ellipse
            painter.drawEllipse(rect)
        elif self._bubble_type == 3: # Speech Bubble (Simple Example)
            radius = min(rect.width() / 2, rect.height() / 2, self.corner_radius)
            path = QPainterPath()
            path.addRoundedRect(rect, radius, radius)
            # Add a simple triangular tail at the bottom center
            tail_width = 20
            tail_height = 15
            path.moveTo(rect.center().x() - tail_width / 2, rect.bottom())
            path.lineTo(rect.center().x(), rect.bottom() + tail_height)
            path.lineTo(rect.center().x() + tail_width / 2, rect.bottom())
            path.closeSubpath()
            painter.drawPath(path)
        else: # Default to rounded rectangle
             radius = min(rect.width() / 2, rect.height() / 2, self.corner_radius) # Clamp radius
             painter.drawRoundedRect(rect, radius, radius)
        
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
    textBoxSelected = pyqtSignal(int, object, bool)  # Add this line (row_number, image_label)

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
        
    def apply_translation(self, text_entries_by_row, default_style): # Accept default style
        current_entries = {rn: entry for rn, entry in text_entries_by_row.items()
                           if not entry.get('is_deleted', False)}
        existing_boxes = {tb.row_number: tb for tb in self.text_boxes}

        # Update/Remove
        for row_number, text_box in list(existing_boxes.items()):
            if row_number not in current_entries:
                text_box.cleanup()
                if text_box in self.text_boxes:
                    self.text_boxes.remove(text_box)
            else:
                entry = current_entries[row_number]
                # --- Get the combined style ---
                style = {}
                # Start with defaults (convert colors)
                for k, v in default_style.items():
                     if k in ['bg_color', 'border_color', 'text_color']:
                         style[k] = QColor(v)
                     else:
                         style[k] = v
                 # Apply custom overrides (convert colors)
                custom_style = entry.get('custom_style', {})
                for k, v in custom_style.items():
                     if k in ['bg_color', 'border_color', 'text_color']:
                         style[k] = QColor(v)
                     else:
                         style[k] = v

                # Apply text first
                text_box.text_item.setPlainText(entry.get('text', ''))
                # Then apply the full style dictionary
                text_box.apply_styles(style) # apply_styles handles font adjustment

        # Add New
        for row_number, entry in current_entries.items():
            if row_number not in existing_boxes:
                coords = entry.get('coordinates')
                if not coords: continue # Skip if no coordinates

                try:
                    x = min(p[0] for p in coords)
                    y = min(p[1] for p in coords)
                    width = max(p[0] for p in coords) - x
                    height = max(p[1] for p in coords) - y
                    # Basic size validation
                    if width <=0 or height <=0: continue

                except (TypeError, IndexError, ValueError) as e:
                    print(f"Error processing coordinates for row {row_number}: {e}")
                    continue

                # --- Get combined style for new box ---
                style = {}
                # Start with defaults (convert colors)
                for k, v in default_style.items():
                     if k in ['bg_color', 'border_color', 'text_color']:
                         style[k] = QColor(v)
                     else:
                         style[k] = v
                # Apply custom overrides (convert colors)
                custom_style = entry.get('custom_style', {})
                for k, v in custom_style.items():
                     if k in ['bg_color', 'border_color', 'text_color']:
                         style[k] = QColor(v)
                     else:
                         style[k] = v

                # Create TextBoxItem, passing the combined style
                text_box = TextBoxItem(QRectF(x, y, width, height), # Use coords directly for initial rect
                                       row_number,
                                       entry.get('text', ''),
                                       initial_style=style) # Pass the full style
                # text_box.setPos(x, y) # Position is set in __init__ now

                text_box.signals.rowDeleted.connect(self.handle_text_box_deleted)
                text_box.signals.selectedChanged.connect(self.on_text_box_selected)
                self.scene().addItem(text_box)
                self.text_boxes.append(text_box)

        self.adjustView() # Fit view after updates

    def on_text_box_selected(self, selected, row_number):
        if selected:
            # Only deselect other text boxes WITHIN THIS SAME SCENE
            for tb in self.text_boxes:
                if tb.row_number != row_number:
                    tb.setSelected(False)
            # Notify MainWindow to deselect in other scenes
            self.textBoxSelected.emit(row_number, self, selected)

    def deselect_all_text_boxes(self):
        for text_box in self.text_boxes:
            text_box.setSelected(False)

    def handle_text_box_deleted(self, row_number):
        # This is triggered by the RED X button ON the TextBoxItem itself.
        # We forward this signal to the MainWindow, which will then call its
        # own delete_row method to MARK the item as deleted in the main data source.
        print(f"TextBoxItem requested deletion for row: {row_number}")
        self.textBoxDeleted.emit(row_number)
        # Note: We don't directly remove the TextBoxItem here anymore.
        # The removal/hiding will happen when MainWindow calls
        # apply_translation_to_images again after marking the item.

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