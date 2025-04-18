from PyQt5.QtWidgets import ( QGraphicsScene, QSizePolicy, QGraphicsPixmapItem, QGraphicsEllipseItem,
                             QGraphicsTextItem, QScrollArea, QGraphicsItem, QGraphicsRectItem, QGraphicsView, QGraphicsDropShadowEffect,
                             QStyledItemDelegate, QTextEdit, QRubberBand)
# Use object for signals to handle both int and float row numbers robustly
from PyQt5.QtCore import Qt, pyqtSignal, QRectF, QPointF, QObject, QPoint, QRect, QSize, QTimer
from PyQt5.QtGui import QPainter, QFont, QBrush, QColor, QPen, QTextOption, QFontDatabase, QPainterPath, QLinearGradient
import qtawesome as qta
from assets.styles import DEFAULT_GRADIENT

class TextBoxSignals(QObject):
    rowDeleted = pyqtSignal(object)
    selectedChanged = pyqtSignal(bool, object)

class TextBoxItem(QGraphicsRectItem):
    def __init__(self, rect, row_number, text="", original_rect=None, initial_style=None):
        super().__init__(QRectF(0, 0, rect.width(), rect.height()))
        self.setPos(rect.x(), rect.y())
        self.signals = TextBoxSignals()
        self.setFlag(QGraphicsItem.ItemIsMovable, True)
        self.setFlag(QGraphicsItem.ItemIsSelectable, True)
        self.setFlag(QGraphicsItem.ItemSendsGeometryChanges, True)
        self.row_number = row_number
        self.original_rect = original_rect

        # --- Style related instance variables ---
        self._bubble_type = 1
        self.corner_radius = 50
        self._auto_font_size = True
        self._fill_type = 'solid'
        self._bg_color = QColor(255, 255, 255)
        self._bg_gradient = None # Will store dict: {'color1': QColor, 'color2': QColor, 'direction': int}
        self._border_width = 1
        self._border_color = QColor(0, 0, 0)
        self._text_color_type = 'solid'
        self._text_color = QColor(0, 0, 0)
        self._text_gradient = None # Will store dict like _bg_gradient
        self._font = QFont("Arial", 12)
        self._alignment = Qt.AlignCenter
        # --- End Style Variables ---

        # Set initial brush/pen based on defaults (will be overridden by apply_styles)
        self.setBrush(QBrush(self._bg_color))
        self.setPen(QPen(self._border_color, self._border_width))

        self.min_width = 50
        self.min_height = 30
        self.resize_mode = False
        self.active_handle = None

        # shadow = QGraphicsDropShadowEffect()
        # shadow.setBlurRadius(20)
        # shadow.setColor(QColor(255, 255, 255, 150))
        # shadow.setOffset(0, 0)
        # self.setGraphicsEffect(shadow)

        self.handles = []
        self.handle_size = 20
        self.handle_positions = [
            Qt.TopLeftCorner, Qt.TopRightCorner, Qt.BottomLeftCorner, Qt.BottomRightCorner,
            Qt.TopEdge, Qt.BottomEdge, Qt.LeftEdge, Qt.RightEdge
        ]
        for position in self.handle_positions:
            handle = QGraphicsRectItem(0, 0, self.handle_size, self.handle_size, self)
            handle.setFlag(QGraphicsItem.ItemIsMovable, False)
            handle.setFlag(QGraphicsItem.ItemSendsGeometryChanges, True)
            if position in [Qt.TopLeftCorner, Qt.TopRightCorner, Qt.BottomLeftCorner, Qt.BottomRightCorner]: handle.setBrush(QBrush(Qt.red))
            else: handle.setBrush(QBrush(Qt.blue))
            handle.setPen(QPen(Qt.black))
            handle.position = position
            handle.hide()
            self.handles.append(handle)
        # self.update_handles_positions()

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
        self.remove_icon_item.setOffset(5, 5) # Center adjust based on 40x40 button, 30x30 icon
        def on_remove_clicked(event): self.signals.rowDeleted.emit(self.row_number); event.accept()
        self.remove_button.mousePressEvent = on_remove_clicked

        # Text Item - will be hidden if text gradient is used
        self.text_item = QGraphicsTextItem(text, self)
        # Apply initial/default styles
        if initial_style:
            self.apply_styles(initial_style)
        else:
            # Apply minimal defaults if no style provided
            self.apply_styles({
                'bg_color': '#ffffffff', 'border_color': '#ff000000', 'text_color': '#ff000000',
                'border_width': 1, 'font_family': 'Arial', 'font_size': 12, 'text_alignment': 1,
                'bubble_type': 1, 'corner_radius': 50, 'auto_font_size': True,
                'fill_type': 'solid', 'text_color_type': 'solid', # Add gradient defaults
                'bg_gradient': {'midpoint': 50}, 'text_gradient': {'midpoint': 50}
            })

        self.setRect(QRectF(0, 0, rect.width(), rect.height())) # Trigger text width/pos calc
        self.setCursor(Qt.SizeAllCursor)

    def apply_styles(self, style_dict):
        """Applies the given style dictionary, including gradients."""
        style_dict = self._ensure_style_defaults(style_dict)

        self._bubble_type = style_dict.get('bubble_type', 1)
        self.corner_radius = style_dict.get('corner_radius', 50)

        # --- Fill Handling ---
        self._fill_type = style_dict.get('fill_type', 'solid')
        self._bg_color = QColor(style_dict.get('bg_color', '#ffffffff'))
        if self._fill_type == 'linear_gradient':
            gradient_data = style_dict.get('bg_gradient', {})
            self._bg_gradient = {
                'color1': QColor(gradient_data.get('color1', '#ffffffff')),
                'color2': QColor(gradient_data.get('color2', '#ffcccccc')),
                'direction': gradient_data.get('direction', 0),
                'midpoint': float(gradient_data.get('midpoint', 50)) # Ensure float
            }
            self.setBrush(QBrush(Qt.NoBrush)) # Gradient applied in paint()
        else:
            self._bg_gradient = None
            self.setBrush(QBrush(self._bg_color)) # Solid color brush

        # --- Border Handling ---
        self._border_color = QColor(style_dict.get('border_color', '#ff000000'))
        self._border_width = style_dict.get('border_width', 1)
        pen = QPen(self._border_color, self._border_width)
        pen.setStyle(Qt.NoPen if self._border_width == 0 else Qt.SolidLine)
        self.setPen(pen)

        # --- Text Color Handling ---
        self._text_color_type = style_dict.get('text_color_type', 'solid')
        self._text_color = QColor(style_dict.get('text_color', '#ff000000'))
        if self._text_color_type == 'linear_gradient':
            gradient_data = style_dict.get('text_gradient', {})
            self._text_gradient = {
                'color1': QColor(gradient_data.get('color1', '#ffffffff')),
                'color2': QColor(gradient_data.get('color2', '#ffcccccc')),
                'direction': gradient_data.get('direction', 0),
                'midpoint': float(gradient_data.get('midpoint', 50)) # Ensure float
            }
            self.text_item.setVisible(False)
            self.text_item.setDefaultTextColor(Qt.transparent)
        else:
            self._text_gradient = None
            self.text_item.setDefaultTextColor(self._text_color)
            self.text_item.setVisible(True)

        # --- Font and Alignment ---
        font_family = style_dict.get('font_family', "Arial")
        font_size = style_dict.get('font_size', 12)
        font_bold = style_dict.get('font_bold', False)
        font_italic = style_dict.get('font_italic', False)
        self._auto_font_size = style_dict.get('auto_font_size', True)

        self._font = QFont()
        # Handle "Default (System Font)" case
        if font_family != "Default (System Font)":
             self._font.setFamily(font_family)
        # Set size (will be adjusted by auto-size if enabled)
        self._font.setPointSize(font_size)
        self._font.setBold(font_bold)
        self._font.setItalic(font_italic)
        self.text_item.setFont(self._font) # Also set on text_item for size calcs

        alignment_index = style_dict.get('text_alignment', 1)
        if alignment_index == 0: self._alignment = Qt.AlignLeft | Qt.AlignVCenter
        elif alignment_index == 1: self._alignment = Qt.AlignCenter
        elif alignment_index == 2: self._alignment = Qt.AlignRight | Qt.AlignVCenter
        else: self._alignment = Qt.AlignCenter # Default

        doc_option = self.text_item.document().defaultTextOption()
        doc_option.setAlignment(self._alignment)
        self.text_item.document().setDefaultTextOption(doc_option)

        # Re-calculate layout based on new styles BEFORE repaint
        self.prepareGeometryChange() # Important if style affects geometry/layout
        if self.rect().isValid(): # Only call setRect if we have a valid rect already
             self.setRect(self.rect())
        self.update()

    def _ensure_style_defaults(self, style_dict):
        """Internal helper to add missing defaults, especially for gradients."""
        # Similar to panel's helper, but simpler, focused on reading
        style = style_dict.copy() if style_dict else {}
        if 'bg_gradient' not in style: style['bg_gradient'] = {}
        if 'midpoint' not in style['bg_gradient']: style['bg_gradient']['midpoint'] = 50
        if 'text_gradient' not in style: style['text_gradient'] = {}
        if 'midpoint' not in style['text_gradient']: style['text_gradient']['midpoint'] = 50
        return style

    def setRect(self, rect):
        new_width = max(rect.width(), self.min_width)
        new_height = max(rect.height(), self.min_height)
        local_rect = QRectF(0, 0, new_width, new_height)

        super().setRect(local_rect) # Call super class's setRect

        padding = 10 # Padding inside the bubble
        text_rect_width = max(0, new_width - 2 * padding)
        self.text_item.setTextWidth(text_rect_width) # Set width constraint for QGraphicsTextItem

        self.adjust_font_size() # Adjust font size and position (also handles text_item pos)

        # Update remove button position (relative to top-right of the rect)
        self.remove_button.setPos(new_width - self.remove_button.boundingRect().width() / 2 - 5, -self.remove_button.boundingRect().height() / 2 + 5) # Slightly offset

        self.update_handles_positions()

    def adjust_font_size(self):
        """Adjust font size (if auto) and position text item (if visible)."""
        padding = 10
        available_width = self.rect().width() - 2 * padding
        available_height = self.rect().height() - 2 * padding

        if available_width <= 0 or available_height <= 0:
            if self.text_item: self.text_item.setPlainText("")
            return

        if not self.text_item: return
        text = self.text_item.toPlainText()
        if not text:
            self.text_item.setPos(padding, padding)
            return

        font = self.text_item.font() # Use the current font from text_item

        if self._auto_font_size:
            min_font_size = 6; max_font_size = 72
            low, high = min_font_size, max_font_size
            optimal_size = low

            # Create temporary text item for measurement to avoid visual flicker
            temp_text = QGraphicsTextItem()
            temp_text.setPlainText(text)
            temp_text.setTextWidth(available_width)
            temp_text.document().setDefaultTextOption(self.text_item.document().defaultTextOption())

            while low <= high:
                mid = (low + high) // 2
                if mid < min_font_size: break # Ensure size doesn't go below min
                current_font = QFont(font)
                current_font.setPointSize(mid)
                temp_text.setFont(current_font)
                text_rect = temp_text.boundingRect()

                # Use document height for better multi-line fit check
                doc_height = temp_text.document().size().height()

                if doc_height <= available_height and text_rect.width() <= available_width:
                    optimal_size = mid
                    low = mid + 1
                else:
                    high = mid - 1

            # Clean up temporary item
            del temp_text

            # Apply the optimal font size to the real text item and internal font storage
            font.setPointSize(optimal_size)
            self.text_item.setFont(font)
            self._font = QFont(font) # Update internal font storage


        # --- Position the QGraphicsTextItem (even if hidden, needed for manual drawing reference) ---
        # Use bounding rect height after font size is set
        text_height = self.text_item.boundingRect().height()
        # Use document height if available and larger (better for multi-line VCenter)
        doc_height = self.text_item.document().size().height()
        effective_text_height = max(text_height, doc_height)

        # Calculate vertical position based on alignment VCenter component
        vertical_offset = padding # Default top padding
        if self._alignment & Qt.AlignVCenter:
             vertical_offset = (self.rect().height() - effective_text_height) / 2
        elif self._alignment & Qt.AlignBottom:
             vertical_offset = self.rect().height() - effective_text_height - padding

        # Ensure vertical offset is at least the padding
        vertical_offset = max(padding, vertical_offset)

        self.text_item.setPos(padding, vertical_offset)


    def update_handles_positions(self):
        rect = self.rect()
        hs = self.handle_size
        for handle in self.handles:
            pos = handle.position
            if pos == Qt.TopLeftCorner: handle.setPos(rect.topLeft() - QPointF(hs/2, hs/2)) # Center handle on corner
            elif pos == Qt.TopRightCorner: handle.setPos(rect.topRight() - QPointF(hs/2, -hs/2))
            elif pos == Qt.BottomLeftCorner: handle.setPos(rect.bottomLeft() - QPointF(-hs/2, hs/2))
            elif pos == Qt.BottomRightCorner: handle.setPos(rect.bottomRight() - QPointF(hs/2, hs/2))
            elif pos == Qt.TopEdge: handle.setPos(rect.center().x() - hs/2, rect.top() - hs/2)
            elif pos == Qt.BottomEdge: handle.setPos(rect.center().x() - hs/2, rect.bottom() - hs/2)
            elif pos == Qt.LeftEdge: handle.setPos(rect.left() - hs/2, rect.center().y() - hs/2)
            elif pos == Qt.RightEdge: handle.setPos(rect.right() - hs/2, rect.center().y() - hs/2)

    # --- Mouse Events (Largely Unchanged, Ensure setRect is Called) ---
    def get_cursor_for_handle(self, handle):
        # ... (keep existing implementation)
        if handle.position in [Qt.TopLeftCorner, Qt.BottomRightCorner]: return Qt.SizeFDiagCursor
        elif handle.position in [Qt.TopRightCorner, Qt.BottomLeftCorner]: return Qt.SizeBDiagCursor
        elif handle.position in [Qt.TopEdge, Qt.BottomEdge]: return Qt.SizeVerCursor
        elif handle.position in [Qt.LeftEdge, Qt.RightEdge]: return Qt.SizeHorCursor
        return Qt.ArrowCursor

    def mousePressEvent(self, event):
        # ... (keep existing implementation)
        for handle in self.handles:
            # Check bounding rect contains scene pos mapped to item coords
            handle_rect_in_item = handle.mapRectToParent(handle.boundingRect())
            if handle.isVisible() and handle_rect_in_item.contains(event.pos()):
                self.resize_mode = True
                self.active_handle = handle
                self.drag_start_pos_item = event.pos() # Position within item's coordinate system
                self.drag_start_rect_item = self.rect() # Item's local rectangle
                self.setCursor(self.get_cursor_for_handle(handle))
                event.accept()
                return

        self.resize_mode = False
        self.active_handle = None
        self.setCursor(Qt.SizeAllCursor)
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        # ... (keep existing implementation, use drag_start_pos_item, drag_start_rect_item)
        if self.resize_mode and self.active_handle:
            # Calculate delta in item's coordinates
            delta = event.pos() - self.drag_start_pos_item
            new_rect = QRectF(self.drag_start_rect_item)
            pos = self.active_handle.position

            # Adjust the local rectangle based on the handle being dragged
            if pos == Qt.TopLeftCorner: new_rect.setTopLeft(new_rect.topLeft() + delta)
            elif pos == Qt.TopRightCorner: new_rect.setTopRight(new_rect.topRight() + QPointF(delta.x(), 0)) ; new_rect.setTop(new_rect.top() + delta.y()) # Split adjustments
            elif pos == Qt.BottomLeftCorner: new_rect.setBottomLeft(new_rect.bottomLeft() + QPointF(0, delta.y())) ; new_rect.setLeft(new_rect.left() + delta.x())
            elif pos == Qt.BottomRightCorner: new_rect.setBottomRight(new_rect.bottomRight() + delta)
            elif pos == Qt.TopEdge: new_rect.setTop(new_rect.top() + delta.y())
            elif pos == Qt.BottomEdge: new_rect.setBottom(new_rect.bottom() + delta.y())
            elif pos == Qt.LeftEdge: new_rect.setLeft(new_rect.left() + delta.x())
            elif pos == Qt.RightEdge: new_rect.setRight(new_rect.right() + delta.x())

             # --- Enforce Minimum Size ---
            final_new_rect = QRectF(new_rect) # Work with a copy for min size check
            if final_new_rect.width() < self.min_width:
                if pos in [Qt.TopLeftCorner, Qt.BottomLeftCorner, Qt.LeftEdge]:
                    final_new_rect.setLeft(final_new_rect.right() - self.min_width)
                else: # Right handles
                    final_new_rect.setWidth(self.min_width)
            if final_new_rect.height() < self.min_height:
                if pos in [Qt.TopLeftCorner, Qt.TopRightCorner, Qt.TopEdge]:
                     final_new_rect.setTop(final_new_rect.bottom() - self.min_height)
                else: # Bottom handles
                     final_new_rect.setHeight(self.min_height)

            # --- Update Position and Local Rect ---
            # Calculate the change in top-left corner due to resizing
            pos_change = final_new_rect.topLeft() - self.drag_start_rect_item.topLeft()
            # Move the item's position in the scene
            new_scene_pos = self.pos() + pos_change
            self.setPos(new_scene_pos)

            # Set the local rectangle (size only changes)
            local_rect = QRectF(0, 0, final_new_rect.width(), final_new_rect.height())
            self.setRect(local_rect) # This calls our overridden setRect

            # Reset drag start references for continuous dragging feel
            self.drag_start_pos_item = event.pos() - pos_change # Adjust start pos relative to new item pos
            self.drag_start_rect_item = local_rect

            event.accept()
            self.update() # Ensure repaint during drag
            # No need to call update_handles_positions here, setRect does it

        else: # Moving the whole item
            super().mouseMoveEvent(event)
            # No need for update_handles_positions on move, itemChange handles scene pos

    def mouseReleaseEvent(self, event):
        # ... (keep existing implementation)
        self.resize_mode = False
        self.active_handle = None
        self.setCursor(Qt.SizeAllCursor)
        super().mouseReleaseEvent(event)
        # self.update_handles_positions() # setRect should handle final update

    # --- itemChange (Handle Selection and Boundary Checks) ---
    def itemChange(self, change, value):
        if change == QGraphicsItem.ItemPositionChange and self.scene():
            # Boundary check (keep item within scene)
            scene_rect = self.scene().sceneRect()
            item_rect = self.rect().translated(value) # Predicted rect in scene coords
            new_pos = QPointF(value) # Start with proposed new position

            if item_rect.left() < scene_rect.left(): new_pos.setX(scene_rect.left())
            elif item_rect.right() > scene_rect.right(): new_pos.setX(scene_rect.right() - self.rect().width())
            if item_rect.top() < scene_rect.top(): new_pos.setY(scene_rect.top())
            elif item_rect.bottom() > scene_rect.bottom(): new_pos.setY(scene_rect.bottom() - self.rect().height())

            # If position changed due to boundary, update original_rect if needed
            if new_pos != value and self.original_rect:
                 self.original_rect = self.rect().translated(new_pos)

            return new_pos # Return adjusted or original position

        elif change == QGraphicsItem.ItemSelectedHasChanged:
            selected = bool(value)
            for handle in self.handles: handle.setVisible(selected)
            self.remove_button.setVisible(selected)
            self.signals.selectedChanged.emit(selected, self.row_number)

        elif change == QGraphicsItem.ItemScenePositionHasChanged:
            # Update original_rect when position actually changes
            if self.original_rect is not None:
                self.original_rect = self.sceneBoundingRect()
            # No need to update handles here usually, setPos triggers necessary updates

        return super().itemChange(change, value)


    # --- PAINT METHOD with Gradient Support ---
    def paint(self, painter, option, widget):
        painter.setRenderHint(QPainter.Antialiasing)
        rect = self.rect()
        path = QPainterPath()

        # ... (Shape definition code remains the same) ...
        if self._bubble_type == 0: path.addRect(rect)
        elif self._bubble_type == 1: radius = min(rect.width()/2, rect.height()/2, self.corner_radius); path.addRoundedRect(rect, radius, radius)
        elif self._bubble_type == 2: path.addEllipse(rect)
        elif self._bubble_type == 3:
            radius = min(rect.width()/2, rect.height()/2, self.corner_radius); path.addRoundedRect(rect, radius, radius)
            tail_width = max(10, min(30, rect.width()*0.2)); tail_height = max(10, min(25, rect.height()*0.15))
            path.moveTo(rect.center().x() - tail_width/2, rect.bottom())
            control_y = rect.bottom() + tail_height*0.6
            path.cubicTo(rect.center().x() - tail_width*0.3, control_y, rect.center().x() + tail_width*0.3, control_y, rect.center().x() + tail_width/2, rect.bottom())
            path.closeSubpath()
        else: radius = min(rect.width()/2, rect.height()/2, self.corner_radius); path.addRoundedRect(rect, radius, radius)

        # --- Fill the Shape ---
        if self._fill_type == 'linear_gradient' and self._bg_gradient:
            gradient = QLinearGradient()
            direction = self._bg_gradient['direction']
            # ... (Set Start/Stop based on direction index - same as before) ...
            if direction == 0: gradient.setStart(rect.topLeft()); gradient.setFinalStop(rect.topRight())
            elif direction == 1: gradient.setStart(rect.topLeft()); gradient.setFinalStop(rect.bottomLeft())
            elif direction == 2: gradient.setStart(rect.topLeft()); gradient.setFinalStop(rect.bottomRight())
            elif direction == 3: gradient.setStart(rect.bottomLeft()); gradient.setFinalStop(rect.topRight())


            # --- Set Colors using integer midpoint ---
            color1 = self._bg_gradient['color1']
            color2 = self._bg_gradient['color2']
            # Convert stored int midpoint (0-100) to float (0.0-1.0) for setColorAt
            midpoint_float = max(0.0, min(1.0, self._bg_gradient['midpoint'] / 100.0))

            gradient.setColorAt(0.0, color1)
            gradient.setColorAt(midpoint_float, color1) # Start transition at calculated float midpoint
            gradient.setColorAt(1.0, color2)
            # --- End Color Setting ---

            painter.fillPath(path, gradient)
        elif self._fill_type == 'solid':
            painter.fillPath(path, self.brush())

        # --- Stroke the Shape ---
        if self.pen().style() != Qt.NoPen:
            painter.strokePath(path, self.pen())

        # --- Draw Text (if gradient) ---
        if self._text_color_type == 'linear_gradient' and self._text_gradient:
            text = self.text_item.toPlainText()
            if text:
                # ... (text_rect calculation remains the same) ...
                text_pos = self.text_item.pos()
                text_width = self.text_item.textWidth()
                text_height = self.text_item.document().size().height()
                text_rect = QRectF(text_pos.x(), text_pos.y(), text_width, text_height)


                if text_rect.isValid():
                    gradient = QLinearGradient()
                    direction = self._text_gradient['direction']
                    # ... (Set Start/Stop based on direction index - same as before) ...
                    if direction == 0: gradient.setStart(text_rect.topLeft()); gradient.setFinalStop(text_rect.topRight())
                    elif direction == 1: gradient.setStart(text_rect.topLeft()); gradient.setFinalStop(text_rect.bottomLeft())
                    elif direction == 2: gradient.setStart(text_rect.topLeft()); gradient.setFinalStop(text_rect.bottomRight())
                    elif direction == 3: gradient.setStart(text_rect.bottomLeft()); gradient.setFinalStop(text_rect.topRight())

                    # --- Set Colors using integer midpoint ---
                    color1 = self._text_gradient['color1']
                    color2 = self._text_gradient['color2']
                    # Convert stored int midpoint (0-100) to float (0.0-1.0) for setColorAt
                    midpoint_float = max(0.0, min(1.0, self._text_gradient['midpoint'] / 100.0))

                    gradient.setColorAt(0.0, color1)
                    gradient.setColorAt(midpoint_float, color1) # Start transition at calculated float midpoint
                    gradient.setColorAt(1.0, color2)
                    # --- End Color Setting ---

                    painter.setFont(self._font)
                    painter.setPen(QPen(gradient, 0))
                    draw_flags = int(self._alignment | Qt.TextWordWrap)
                    painter.drawText(text_rect, draw_flags, text)
                    
    # --- Cleanup ---
    def cleanup(self):
        """Properly clean up all child items and disconnect signals"""
        if hasattr(self, 'signals'):
            try:
                # Use disconnect() without arguments to disconnect all slots
                self.signals.rowDeleted.disconnect()
                self.signals.selectedChanged.disconnect()
            except (TypeError, RuntimeError): pass

        # Remove child items safely
        # Use reversed list to avoid index issues if removal modifies list
        for child in reversed(self.childItems()):
            child.setParentItem(None)
            if child.scene():
                child.scene().removeItem(child)
        self.handles = []
        self.text_item = None # Break reference
        self.remove_button = None # Break reference

        if self.scene():
            self.scene().removeItem(self)

    def __del__(self):
        # print(f"DEBUG: TextBoxItem destructor called for row {self.row_number}")
        # Avoid calling cleanup here unless absolutely necessary and safe
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
        """Applies text entries, creating/updating/removing TextBoxItems."""
        # Ensure default style includes gradient defaults
        processed_default_style = self._ensure_gradient_defaults_for_ril(default_style)

        current_entries = {rn: entry for rn, entry in text_entries_by_row.items()
                           if not entry.get('is_deleted', False)}
        existing_boxes = {tb.row_number: tb for tb in self.text_boxes}

        rows_to_remove_from_list = []
        # Update/Remove existing boxes
        for row_number, text_box in list(existing_boxes.items()):
            if row_number not in current_entries:
                text_box.cleanup()
                rows_to_remove_from_list.append(row_number)
            else:
                entry = current_entries[row_number]
                # Combine default and custom styles
                combined_style = self._combine_styles(processed_default_style, entry.get('custom_style', {}))

                # Update text and apply combined style
                text_box.text_item.setPlainText(entry.get('text', ''))
                text_box.apply_styles(combined_style) # Apply the full style dict

        # Remove cleaned-up boxes from the internal list
        self.text_boxes = [tb for tb in self.text_boxes if tb.row_number not in rows_to_remove_from_list]

        # Add New boxes
        existing_rows_after_removal = {tb.row_number for tb in self.text_boxes}
        for row_number, entry in current_entries.items():
            if row_number not in existing_rows_after_removal:
                coords = entry.get('coordinates')
                if not coords: continue
                try:
                    x = min(p[0] for p in coords); y = min(p[1] for p in coords)
                    width = max(p[0] for p in coords) - x; height = max(p[1] for p in coords) - y
                    if width <= 0 or height <= 0: continue
                except Exception as e:
                    print(f"Error processing coords for new row {row_number}: {coords} -> {e}")
                    continue

                # Combine default and custom styles for the new box
                combined_style = self._combine_styles(processed_default_style, entry.get('custom_style', {}))

                text_box = TextBoxItem(QRectF(x, y, width, height),
                                       row_number,
                                       entry.get('text', ''),
                                       initial_style=combined_style) # Pass combined style

                text_box.signals.rowDeleted.connect(self.handle_text_box_deleted)
                text_box.signals.selectedChanged.connect(self.on_text_box_selected)
                self.scene().addItem(text_box)
                self.text_boxes.append(text_box)

        # Defer view update slightly
        QTimer.singleShot(0, self.update_view_transform)

        # --- Helper to ensure style dict has gradient defaults ---
    def _ensure_gradient_defaults_for_ril(self, style_dict):
        style = style_dict.copy() if style_dict else {}
        # Fill
        if 'fill_type' not in style: style['fill_type'] = 'solid'
        if 'bg_color' not in style: style['bg_color'] = '#ffffffff'
        if 'bg_gradient' not in style: style['bg_gradient'] = {}
        style['bg_gradient'] = {'midpoint': 50, **style['bg_gradient']} # Add default midpoint if missing

        # Text
        if 'text_color_type' not in style: style['text_color_type'] = 'solid'
        if 'text_color' not in style: style['text_color'] = '#ff000000'
        if 'text_gradient' not in style: style['text_gradient'] = {}
        style['text_gradient'] = {'midpoint': 50, **style['text_gradient']} # Add default midpoint if missing

                # Ensure midpoint is int after merge
        if 'midpoint' in style['bg_gradient']: style['bg_gradient']['midpoint'] = int(style['bg_gradient']['midpoint'])
        if 'midpoint' in style['text_gradient']: style['text_gradient']['midpoint'] = int(style['text_gradient']['midpoint'])

        return style

    # --- Helper to combine default and custom styles ---
    def _combine_styles(self, default_style, custom_style):
        # Ensure default has the base structure first (with int midpoint)
        combined = self._ensure_gradient_defaults_for_ril(default_style)

        if custom_style:
            # Make sure custom style also has base structure if needed before merging
            processed_custom = self._ensure_gradient_defaults_for_ril(custom_style)

            for key, value in processed_custom.items():
                 if key in ['bg_gradient', 'text_gradient'] and isinstance(value, dict):
                     # Merge the gradient sub-dictionary (will overwrite midpoint if present in custom)
                     combined[key].update(value)
                     # Ensure midpoint remains integer after potential merge
                     if 'midpoint' in combined[key]: combined[key]['midpoint'] = int(combined[key]['midpoint'])
                 else:
                     combined[key] = value # Overwrite other keys
        return combined

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