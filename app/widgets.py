from PyQt5.QtWidgets import ( QGraphicsScene, QSizePolicy, QGraphicsPixmapItem, QGraphicsEllipseItem,
                             QGraphicsTextItem, QScrollArea, QGraphicsItem, QGraphicsRectItem, QGraphicsView, QGraphicsDropShadowEffect,
                             QStyledItemDelegate, QTextEdit, QRubberBand)
# Use object for signals to handle both int and float row numbers robustly
from PyQt5.QtCore import Qt, pyqtSignal, QRectF, QPointF, QObject, QPoint, QRect, QSize
from PyQt5.QtGui import QPainter, QFont, QBrush, QColor, QPen, QTextOption, QFontDatabase, QPainterPath
import qtawesome as qta

class TextBoxSignals(QObject):
    rowDeleted = pyqtSignal(object)
    selectedChanged = pyqtSignal(bool, object)

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
            self.signals.rowDeleted.emit(self.row_number) # Emit the row number (int or float)
            event.accept()
        self.remove_button.mousePressEvent = on_remove_clicked

        self.text_item = QGraphicsTextItem(text, self)
        if initial_style:
             self.apply_styles(initial_style)
        else:
             # Apply some basic defaults
             self.setBrush(QBrush(QColor(255, 255, 255)))
             self.setPen(QPen(QColor(0, 0, 0), 1))
             self.text_item.setDefaultTextColor(Qt.black)
             font = QFont("Arial", 12)
             self.text_item.setFont(font)
             doc_option = self.text_item.document().defaultTextOption()
             doc_option.setAlignment(Qt.AlignCenter)
             self.text_item.document().setDefaultTextOption(doc_option)

        self.setRect(QRectF(0, 0, rect.width(), rect.height()))
        self.setCursor(Qt.SizeAllCursor)

    def apply_styles(self, style_dict):
        """Applies the given style dictionary to the item."""
        self._bubble_type = style_dict.get('bubble_type', 1)
        self.corner_radius = style_dict.get('corner_radius', 50)

        bg_color = QColor(style_dict.get('bg_color', '#ffffffff'))
        border_color = QColor(style_dict.get('border_color', '#ff000000'))
        text_color = QColor(style_dict.get('text_color', '#ff000000'))
        border_width = style_dict.get('border_width', 1)

        self.setBrush(QBrush(bg_color))
        pen = QPen(border_color, border_width)
        if border_width == 0:
             pen.setStyle(Qt.NoPen)
        else:
            pen.setStyle(Qt.SolidLine)
        self.setPen(pen)
        self.text_item.setDefaultTextColor(text_color)

        font_family = style_dict.get('font_family', "Arial")
        font_size = style_dict.get('font_size', 12)
        font_bold = style_dict.get('font_bold', False)
        font_italic = style_dict.get('font_italic', False)
        alignment_index = style_dict.get('text_alignment', 1)
        self._auto_font_size = style_dict.get('auto_font_size', True)

        font = QFont()
        font.setFamily(font_family)
        font.setPointSize(font_size)
        font.setBold(font_bold)
        font.setItalic(font_italic)
        self.text_item.setFont(font)

        alignment = Qt.AlignCenter
        if alignment_index == 0:
            alignment = Qt.AlignLeft
        elif alignment_index == 2:
            alignment = Qt.AlignRight
        doc_option = self.text_item.document().defaultTextOption()
        doc_option.setAlignment(alignment | Qt.AlignVCenter)
        self.text_item.document().setDefaultTextOption(doc_option)

        self.setRect(self.rect()) # Recalculate text position/width based on new style
        self.update()

    def setRect(self, rect):
        new_width = max(rect.width(), self.min_width)
        new_height = max(rect.height(), self.min_height)
        local_rect = QRectF(0, 0, new_width, new_height)

        if local_rect != self.rect():
             super().setRect(local_rect)

        padding = 10
        self.text_item.setTextWidth(max(0, new_width - 2 * padding))
        self.adjust_font_size()

        self.remove_button.setPos(new_width - 20, -20)
        self.update_handles_positions()

    def adjust_font_size(self):
        """Adjust font size and position based on current settings."""
        padding = 10
        available_width = self.rect().width() - 2 * padding
        available_height = self.rect().height() - 2 * padding

        if available_width <= 0 or available_height <= 0:
            if self.text_item:
                self.text_item.setPlainText("")
            return

        if not self.text_item:
            return

        text = self.text_item.toPlainText()
        if not text:
            self.text_item.setPos(padding, padding)
            return

        font = self.text_item.font()

        if self._auto_font_size:
            min_font_size = 6
            max_font_size = 72
            low = min_font_size
            high = max_font_size
            optimal_size = low

            while low <= high:
                mid = (low + high) // 2
                font.setPointSize(mid)
                self.text_item.setFont(font)
                text_rect = self.text_item.boundingRect()

                if text_rect.height() <= available_height and text_rect.width() <= available_width:
                    optimal_size = mid
                    low = mid + 1
                else:
                    high = mid - 1

            font.setPointSize(optimal_size)
            self.text_item.setFont(font)

        text_height = self.text_item.boundingRect().height()
        vertical_offset = (self.rect().height() - text_height) / 2
        vertical_offset = max(padding, vertical_offset)
        self.text_item.setPos(padding, vertical_offset)

    def update_handles_positions(self):
        """Position handles at the corners and edges of the rectangle."""
        rect = self.rect()
        for handle in self.handles:
            if handle.position == Qt.TopLeftCorner:
                handle.setPos(rect.topLeft())
            elif handle.position == Qt.TopRightCorner:
                handle.setPos(rect.topRight() - QPointF(self.handle_size, 0))
            elif handle.position == Qt.BottomLeftCorner:
                handle.setPos(rect.bottomLeft() - QPointF(0, self.handle_size))
            elif handle.position == Qt.BottomRightCorner:
                handle.setPos(rect.bottomRight() - QPointF(self.handle_size, self.handle_size))
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
        for handle in self.handles:
            if handle.isVisible() and handle.contains(handle.mapFromScene(event.scenePos())):
                self.resize_mode = True
                self.active_handle = handle
                self.drag_start_pos = event.pos()
                self.drag_start_rect = self.rect()
                self.setCursor(self.get_cursor_for_handle(handle))
                event.accept()
                return

        self.resize_mode = False
        self.active_handle = None
        self.setCursor(Qt.SizeAllCursor)
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        """Handle mouse move events for both moving and resizing."""
        if self.resize_mode and self.active_handle:
            delta = event.pos() - self.drag_start_pos
            new_rect = QRectF(self.drag_start_rect)

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
        # --- DEBUG PRINT ADDED PREVIOUSLY ---
        if change == QGraphicsItem.ItemSelectedHasChanged:
            try:
                is_selected_now = bool(value)
            except Exception as e:
                print(f"Error in TextBoxItem.itemChange print: {e}") # Safety catch
        # --- END DEBUG PRINT ---

        if change == QGraphicsItem.ItemPositionChange:
            if self.scene():
                scene_rect = self.scene().sceneRect()
                item_rect = self.rect().translated(value)
                if not scene_rect.contains(item_rect):
                    new_pos = value
                    if item_rect.left() < scene_rect.left():
                        new_pos.setX(scene_rect.left())
                    elif item_rect.right() > scene_rect.right():
                        new_pos.setX(scene_rect.right() - self.rect().width())
                    if item_rect.top() < scene_rect.top():
                        new_pos.setY(scene_rect.top())
                    elif item_rect.bottom() > scene_rect.bottom():
                        new_pos.setY(scene_rect.bottom() - self.rect().height())
                    return new_pos

        elif change == QGraphicsItem.ItemSelectedHasChanged:
            selected = bool(value)
            for handle in self.handles:
                handle.setVisible(selected)
            self.remove_button.setVisible(selected)
            self.signals.selectedChanged.emit(selected, self.row_number) # Emit row_number (int or float)

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
            radius = min(rect.width() / 2, rect.height() / 2, self.corner_radius)
            painter.drawRoundedRect(rect, radius, radius)
        elif self._bubble_type == 2: # Ellipse
            painter.drawEllipse(rect)
        elif self._bubble_type == 3: # Speech Bubble
            radius = min(rect.width() / 2, rect.height() / 2, self.corner_radius)
            path = QPainterPath()
            path.addRoundedRect(rect, radius, radius)
            tail_width = 20
            tail_height = 15
            path.moveTo(rect.center().x() - tail_width / 2, rect.bottom())
            path.lineTo(rect.center().x(), rect.bottom() + tail_height)
            path.lineTo(rect.center().x() + tail_width / 2, rect.bottom())
            path.closeSubpath()
            painter.drawPath(path)
        else: # Default
             radius = min(rect.width() / 2, rect.height() / 2, self.corner_radius)
             painter.drawRoundedRect(rect, radius, radius)

    def cleanup(self):
        """Properly clean up all child items and disconnect signals"""
        if hasattr(self, 'signals'):
            try:
                # Use disconnect() without arguments to disconnect all slots
                self.signals.rowDeleted.disconnect()
                self.signals.selectedChanged.disconnect()
            except TypeError: # Raised if no slots connected
                 pass
            except RuntimeError: # Raised if C++ object deleted
                 pass


        # Remove child items safely
        for child in self.childItems():
            child.setParentItem(None) # Break parent-child link first
            if child.scene():
                child.scene().removeItem(child)
        self.handles = [] # Clear list after removal

        # No need to explicitly remove text_item and remove_button if handled by childItems() loop

        # Finally remove self from scene
        if self.scene():
            self.scene().removeItem(self)

    def __del__(self):
        # print(f"DEBUG: TextBoxItem destructor called for row {self.row_number}")
        # Cleanup might be called automatically, but being explicit can help
        # self.cleanup() # Be careful with calling cleanup in __del__
        pass

class ResizableImageLabel(QGraphicsView):
    # --- CHANGE SIGNAL DEFINITION ---
    # Use 'object' for row numbers to handle int and float robustly
    textBoxDeleted = pyqtSignal(object)
    textBoxSelected = pyqtSignal(object, object, bool) # (row_number, image_label, selected)
    # --- END CHANGE ---
    manual_area_selected = pyqtSignal(QRectF, object) # (Scene Coords, Self)

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
        self.scene().setSceneRect(0, 0, self.original_pixmap.width(), self.original_pixmap.height())
        self.setInteractive(True)
        self.text_boxes = []
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.original_text_entries = {} # Store original text entries

        self._is_manual_select_active = False
        self._is_selection_active = False # Is there a *completed* selection visible on this label?
        self._rubber_band = None
        self._rubber_band_origin = QPoint()

        self.setCursor(Qt.ArrowCursor)

    def set_manual_selection_enabled(self, enabled):
        """Controls if this label can *start* a manual selection."""
        self._is_manual_select_active = enabled
        if enabled:
            # Only set cross cursor if no selection is currently active *on this label*
            if not self._is_selection_active:
                 self.setCursor(Qt.CrossCursor)
        else:
            # Revert cursor unless a selection is active (which maintains Arrow implicitly)
            if not self._is_selection_active:
                 self.setCursor(Qt.ArrowCursor)
        # print(f"Manual selection ENABLED: {enabled} for {self.filename}, Active selection: {self._is_selection_active}, Cursor: {self.cursor().shape()}")

    def mousePressEvent(self, event):
        """Handle mouse press for starting rubber band selection or item interaction."""
        # --- Prevent starting new selection if mode is off OR if a selection is already active on THIS label ---
        if not self._is_manual_select_active or self._is_selection_active:
            super().mousePressEvent(event) # Allow normal item interaction/panning
            return

        # --- Start rubber band ---
        if event.button() == Qt.LeftButton:
            self._rubber_band_origin = event.pos()
            if not self._rubber_band:
                self._rubber_band = QRubberBand(QRubberBand.Rectangle, self)
            # Ensure it's visible and reset geometry
            self._rubber_band.setGeometry(QRect(self._rubber_band_origin, QSize()))
            self._rubber_band.show()
            event.accept()
        else:
            super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        """Finalize selection, emit signal, or handle panning release."""
        # --- Finalize rubber band selection ---
        if self._is_manual_select_active and self._rubber_band and event.button() == Qt.LeftButton and not self._rubber_band_origin.isNull():
            final_rect_viewport = self._rubber_band.geometry()
            self._rubber_band_origin = QPoint() # Reset origin

            # Check if selection is validly sized
            if final_rect_viewport.width() > 4 and final_rect_viewport.height() > 4:
                rect_scene = self.mapToScene(final_rect_viewport).boundingRect()
                print(f"Manual selection finished on {self.filename}. Viewport Rect: {final_rect_viewport}, Scene Rect: {rect_scene}")

                # --- Keep rubber band visible and set active flag ---
                self._is_selection_active = True
                self.setCursor(Qt.ArrowCursor) # Change cursor to arrow as selection is done
                # print(f"Selection active on {self.filename}. Cursor: {self.cursor().shape()}")
                self.manual_area_selected.emit(rect_scene, self) # Signal MainWindow
            else:
                 # Selection too small, hide rubber band and allow new selection
                 print("Selection too small, ignored.")
                 self._rubber_band.hide()
                 self._is_selection_active = False
                 # Cursor remains Cross if _is_manual_select_active is still true

            event.accept()
        else:
            # If not ending a rubber band, pass to base class
            super().mouseReleaseEvent(event)

    def mouseMoveEvent(self, event):
        """Update rubber band or handle panning."""
        # --- Update rubber band only if manual selection is enabled AND we started one ---
        if self._is_manual_select_active and self._rubber_band and not self._rubber_band_origin.isNull() and (event.buttons() & Qt.LeftButton):
            self._rubber_band.setGeometry(QRect(self._rubber_band_origin, event.pos()).normalized())
            event.accept()
        else:
            # Pass event to base class for item movement and panning
            super().mouseMoveEvent(event)

    def clear_active_selection(self):
        """Hides the rubber band and resets the active selection state."""
        # print(f"Clearing active selection on {self.filename}")
        if self._rubber_band:
             self._rubber_band.hide()
        self._is_selection_active = False
        # Re-evaluate cursor based on whether manual selection is globally enabled
        self.set_manual_selection_enabled(self._is_manual_select_active)

    def hasHeightForWidth(self):
        return True

    def heightForWidth(self, width):
        if self.original_pixmap.isNull() or self.original_pixmap.width() == 0:
            # Provide a sensible minimum height if pixmap is invalid or has zero width
            return self.minimumHeight() if self.minimumHeight() > 0 else 50
        # Calculate aspect ratio, ensure width isn't zero
        aspect_ratio = self.original_pixmap.height() / self.original_pixmap.width()
        calculated_height = int(aspect_ratio * width)
        # print(f"[{self.filename}] heightForWidth({width}) -> {calculated_height}") # Debug print
        return calculated_height

    def resizeEvent(self, event):
        # Instead of calling adjustView directly, let the layout settle first.
        # The layout uses heightForWidth to determine the correct height.
        # We just need to ensure the view transform is correct after resize.
        super().resizeEvent(event)
        # Use a timer to ensure the viewport dimensions are finalized after resize
        from PyQt5.QtCore import QTimer
        QTimer.singleShot(0, self.update_view_transform) # Renamed method

    def update_view_transform(self):
        """
        Updates the view's transformation matrix to scale the scene content
        to fit the current viewport width while maintaining aspect ratio.
        Relies on the layout having set the correct widget height via heightForWidth.
        """
        if not self.scene() or self.original_pixmap.isNull() or not self.pixmap_item:
            return

        scene_rect = self.scene().sceneRect()
        if scene_rect.width() == 0 or scene_rect.height() == 0:
            # print(f"[{self.filename}] update_view_transform: Invalid scene rect {scene_rect}") # Debug print
            return # Avoid division by zero or invalid scaling

        viewport_width = self.viewport().width()
        viewport_height = self.viewport().height() # We don't strictly use this for scaling, but good to know

        # Calculate the scale factor needed to make the scene width match the viewport width
        scale_factor = viewport_width / scene_rect.width()

        # Reset any previous transformations (like zoom or pan)
        self.resetTransform()
        # Apply the calculated scale uniformly to maintain aspect ratio
        self.scale(scale_factor, scale_factor)

        # After scaling, the scene origin (0,0) is at the viewport's top-left.
        # No need to center or fit further, as heightForWidth should ensure
        # the widget's height matches the scaled pixmap's height.

        # print(f"[{self.filename}] update_view_transform: VP=({viewport_width},{viewport_height}), SceneW={scene_rect.width()}, Scale={scale_factor}") # Debug print
        self.viewport().update() # Ensure redra

    # def adjustView(self):
    #    if self.pixmap_item and self.scene() and not self.original_pixmap.isNull():
    #        # Fit the entire scene content within the view
    #        self.fitInView(self.scene().sceneRect(), Qt.KeepAspectRatio)
    #        self.viewport().update() # Ensure viewport redraws


    def apply_translation(self, text_entries_by_row, default_style):
        current_entries = {rn: entry for rn, entry in text_entries_by_row.items()
                           if not entry.get('is_deleted', False)}
        existing_boxes = {tb.row_number: tb for tb in self.text_boxes}

        # Update/Remove
        rows_to_remove_from_list = []
        for row_number, text_box in list(existing_boxes.items()):
            if row_number not in current_entries:
                # print(f"  apply_translation: Cleaning up box for deleted/missing row {row_number}")
                text_box.cleanup() # Ensure proper scene removal
                rows_to_remove_from_list.append(row_number)
            else:
                # Update existing box
                entry = current_entries[row_number]
                style = {}
                # --- Load default style ---
                for k, v in default_style.items():
                    if k in ['bg_color', 'border_color', 'text_color']:
                        # Ensure QColor for apply_styles
                        style[k] = QColor(v) if isinstance(v, str) else v
                    else:
                        style[k] = v
                # --- Apply custom overrides ---
                custom_style = entry.get('custom_style', {})
                for k, v in custom_style.items():
                    if k in ['bg_color', 'border_color', 'text_color']:
                        # Ensure QColor when applying custom style from saved data
                        style[k] = QColor(v) if isinstance(v, str) else v
                    else:
                        style[k] = v

                text_box.text_item.setPlainText(entry.get('text', ''))
                text_box.apply_styles(style) # Apply the combined style

        # Remove cleaned-up boxes from the internal list
        self.text_boxes = [tb for tb in self.text_boxes if tb.row_number not in rows_to_remove_from_list]


        # Add New
        for row_number, entry in current_entries.items():
            if row_number not in existing_boxes: # Check again after removals
                coords = entry.get('coordinates')
                if not coords: continue

                try:
                    x = min(p[0] for p in coords)
                    y = min(p[1] for p in coords)
                    width = max(p[0] for p in coords) - x
                    height = max(p[1] for p in coords) - y
                    if width <=0 or height <=0: continue
                except (TypeError, IndexError, ValueError, Exception) as e: # Catch more general exceptions
                    print(f"Error processing coordinates for new row {row_number}: {coords} -> {e}")
                    continue

                style = {}
                # --- Load default style ---
                for k, v in default_style.items():
                    if k in ['bg_color', 'border_color', 'text_color']:
                        style[k] = QColor(v) if isinstance(v, str) else v
                    else:
                        style[k] = v
                # --- Apply custom overrides ---
                custom_style = entry.get('custom_style', {})
                for k, v in custom_style.items():
                     if k in ['bg_color', 'border_color', 'text_color']:
                         style[k] = QColor(v) if isinstance(v, str) else v
                     else:
                         style[k] = v

                text_box = TextBoxItem(QRectF(x, y, width, height),
                                       row_number, # Pass the int or float row number
                                       entry.get('text', ''),
                                       initial_style=style) # Pass combined style

                selectable_flag = bool(text_box.flags() & QGraphicsItem.ItemIsSelectable)

                text_box.signals.rowDeleted.connect(self.handle_text_box_deleted)
                text_box.signals.selectedChanged.connect(self.on_text_box_selected)
                self.scene().addItem(text_box)
                self.text_boxes.append(text_box)

        # Defer adjustView slightly to ensure layout is stable
        from PyQt5.QtCore import QTimer
        QTimer.singleShot(0, self.update_view_transform)

    def on_text_box_selected(self, selected, row_number):
        """Slot to handle selection changes *from* TextBoxItem signals."""
        if selected:
            # Deselect other items in *this* scene
            for tb in self.text_boxes:
                 # Use the received row_number for comparison
                 if tb.row_number != row_number:
                     # Check if the item is actually selected before deselecting
                     if tb.isSelected():
                         tb.setSelected(False)

            self.textBoxSelected.emit(row_number, self, selected) # Emits the object row_number
        else:
            self.textBoxSelected.emit(row_number, self, selected)


    def deselect_all_text_boxes(self):
        for text_box in self.text_boxes:
            if text_box.isSelected(): # Only deselect if actually selected
                text_box.setSelected(False)


    def handle_text_box_deleted(self, row_number):
        # Forward the row_number (int or float) to MainWindow
        print(f"ResizableImageLabel forwarding delete request for row: {row_number}")
        self.textBoxDeleted.emit(row_number)


    def remove_text_box_by_row(self, row_number):
        """Finds and removes a specific TextBoxItem from the scene and internal list."""
        item_to_remove = None
        for tb in self.text_boxes:
             # Use type-flexible comparison
            try:
                if tb.row_number == row_number or float(tb.row_number) == float(row_number):
                     item_to_remove = tb
                     break
            except (TypeError, ValueError): # Handle cases where conversion might fail
                 if str(tb.row_number) == str(row_number): # Fallback to string comparison
                      item_to_remove = tb
                      break

        if item_to_remove:
            # print(f"Attempting immediate removal of TextBoxItem (row {row_number}) from scene in {self.filename}")
            item_to_remove.cleanup()
            try:
                # Find item by identity before removing
                index_to_remove = -1
                for i, current_tb in enumerate(self.text_boxes):
                    if current_tb is item_to_remove:
                        index_to_remove = i
                        break
                if index_to_remove != -1:
                    del self.text_boxes[index_to_remove]
                    # print(f"Successfully removed TextBoxItem (row {row_number}) from internal list.")
                else:
                    print(f"Warning: TextBoxItem (row {row_number}) found but couldn't remove from list by identity.")
            except ValueError:
                 # This should ideally not happen if item_to_remove is from the list
                 print(f"Warning: TextBoxItem (row {row_number}) not found in list during remove_text_box_by_row?")
        else:
            # print(f"Warning: Tried to remove TextBoxItem visually (row {row_number}) but it was not found in {self.filename}'s list.")
            pass

    def cleanup(self):
        """Clean up resources before removal."""
        # Disconnect signals connected TO this object (if any) - less common here
        # Disconnect signals FROM this object
        try:
            self.textBoxDeleted.disconnect()
            self.textBoxSelected.disconnect()
            self.manual_area_selected.disconnect()
        except TypeError: pass # No slots connected
        except RuntimeError: pass # C++ object deleted

        # Clear scene properly
        if self.scene():
            # Explicitly call cleanup on all TextBoxItems before clearing scene
            for tb in self.text_boxes[:]: # Iterate copy
                tb.cleanup()
            self.text_boxes = [] # Clear internal list
            self.scene().clear() # Removes all items including pixmap_item

        self.setScene(None) # Release the scene object


    def get_text_boxes(self):
        return self.text_boxes

    def __del__(self):
        # print(f"DEBUG: ResizableImageLabel destructor called for {self.filename}")
        # self.cleanup() # Avoid explicit cleanup in __del__ if possible
        pass


# --- Other classes (CustomScrollArea, TextEditDelegate) remain unchanged ---

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