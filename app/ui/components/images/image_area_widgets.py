# --- START OF FILE image_area_widgets.py ---

from PyQt5.QtWidgets import QGraphicsTextItem, QGraphicsItem, QGraphicsRectItem
from PyQt5.QtCore import Qt, pyqtSignal, QRectF, QPointF, QObject,QLineF
from PyQt5.QtGui import QPainter, QFont, QBrush, QColor, QPen, QPainterPath, QLinearGradient, QTransform, QPolygonF

# --- NEW: Custom Item for Selection and Resize Handles ---
class SelectionFrameItem(QGraphicsItem):
    """
    A custom QGraphicsItem that provides a selection, resize, and rotation frame.
    It draws an outline, resize handles, a rotation handle, and a delete button.
    It also supports free transform (perspective distortion) when dragging handles with Ctrl key.
    This item is intended to be a child of the item it frames (e.g., TextBoxItem).
    """

    def __init__(self, parent):
        super().__init__(parent)
        self.parent_item = parent
        self.setZValue(10)  # Ensure it's drawn on top of the parent
        self.setAcceptHoverEvents(True)

        # --- Configuration ---
        self.handle_size = 10
        self.outline_color = QColor(0, 120, 215)  # Standard blue selection color
        self.handle_fill_color = QColor(255, 255, 255)
        self.delete_btn_size = 20
        self.rotate_btn_size = 20
        self.control_offset = 15  # How far above the top edge the controls are

        # --- State ---
        self.active_handle = None
        self.drag_start_pos = None
        self.drag_start_rect = None
        self.drag_start_angle = 0
        self.drag_start_center = QPointF()
        self.is_free_transform = False  # True if Ctrl is held during a resize drag
        self.initial_scene_quad = None  # Stores the item's corner positions for free transform

        # --- Caches for hit testing ---
        self._handle_rects = {}
        self._delete_btn_rect = QRectF()
        self._rotate_handle_rect = QRectF()

    def _update_geometry(self):
        """Recalculates positions of all frame elements based on parent's rect."""
        parent_rect = self.parent_item.rect()
        hs = self.handle_size
        hs_half = hs / 2.0

        self._handle_rects = {
            'tl': QRectF(parent_rect.left() - hs_half, parent_rect.top() - hs_half, hs, hs),
            'tr': QRectF(parent_rect.right() - hs_half, parent_rect.top() - hs_half, hs, hs),
            'bl': QRectF(parent_rect.left() - hs_half, parent_rect.bottom() - hs_half, hs, hs),
            'br': QRectF(parent_rect.right() - hs_half, parent_rect.bottom() - hs_half, hs, hs),
            't': QRectF(parent_rect.center().x() - hs_half, parent_rect.top() - hs_half, hs, hs),
            'b': QRectF(parent_rect.center().x() - hs_half, parent_rect.bottom() - hs_half, hs, hs),
            'l': QRectF(parent_rect.left() - hs_half, parent_rect.center().y() - hs_half, hs, hs),
            'r': QRectF(parent_rect.right() - hs_half, parent_rect.center().y() - hs_half, hs, hs),
        }

        # Calculate rotation handle position
        top_handle_center = self._handle_rects['t'].center()
        rotate_btn_center_y = top_handle_center.y() - self.control_offset - self.rotate_btn_size / 2
        rotate_btn_center = QPointF(top_handle_center.x(), rotate_btn_center_y)
        self._rotate_handle_rect = QRectF(0, 0, self.rotate_btn_size, self.rotate_btn_size)
        self._rotate_handle_rect.moveCenter(rotate_btn_center)

        # Calculate delete button position, shifted right from the rotate handle
        delete_btn_center_x = self._rotate_handle_rect.center().x() + self._rotate_handle_rect.width() / 2 + self.control_offset
        delete_btn_center = QPointF(delete_btn_center_x, rotate_btn_center.y())
        self._delete_btn_rect = QRectF(0, 0, self.delete_btn_size, self.delete_btn_size)
        self._delete_btn_rect.moveCenter(delete_btn_center)

    def boundingRect(self):
        """The bounding rect must include the parent, handles, and control buttons."""
        self._update_geometry()
        rect = self.parent_item.rect()
        for handle_rect in self._handle_rects.values():
            rect = rect.united(handle_rect)
        rect = rect.united(self._delete_btn_rect)
        rect = rect.united(self._rotate_handle_rect)
        return rect.adjusted(-2, -2, 2, 2)  # Add a small margin for pen widths

    def paint(self, painter, option, widget=None):
        self._update_geometry()  # Ensure positions are fresh for painting
        painter.setRenderHint(QPainter.Antialiasing)
        
        # 1. Draw main outline
        outline_pen = QPen(self.outline_color, 1.5, Qt.SolidLine)
        painter.setPen(outline_pen)
        painter.setBrush(Qt.NoBrush)
        painter.drawRect(self.parent_item.rect())

        # 2. Draw 8 resize handles (unfilled rectangles)
        handle_pen = QPen(self.outline_color, 1)
        painter.setPen(handle_pen)
        painter.setBrush(self.handle_fill_color)
        for handle_rect in self._handle_rects.values():
            painter.drawRect(handle_rect)

        # 3. Draw center '+' indicator
        center = self.parent_item.rect().center()
        cross_size = 5
        painter.setPen(outline_pen)
        painter.drawLine(QPointF(center.x() - cross_size, center.y()), QPointF(center.x() + cross_size, center.y()))
        painter.drawLine(QPointF(center.x(), center.y() - cross_size), QPointF(center.x(), center.y() + cross_size))

        # 4. Draw control buttons and their connecting lines
        top_handle_center = self._handle_rects['t'].center()
        painter.drawLine(top_handle_center, self._rotate_handle_rect.center())
        painter.drawLine(self._rotate_handle_rect.center(), self._delete_btn_rect.center())

        # Draw rotate handle
        painter.setPen(QPen(self.outline_color, 1)); painter.setBrush(self.handle_fill_color)
        painter.drawRect(self._rotate_handle_rect)
        # Draw rotate icon (circular arrow)
        icon_rect = self._rotate_handle_rect.adjusted(4, 4, -4, -4)
        path = QPainterPath()
        path.moveTo(icon_rect.right(), icon_rect.center().y())
        path.arcTo(icon_rect, 0, 270)
        p1 = path.currentPosition(); arrow_size = 3
        path.moveTo(p1); path.lineTo(p1.x() - arrow_size, p1.y() - arrow_size)
        path.moveTo(p1); path.lineTo(p1.x() + arrow_size, p1.y() - arrow_size)
        painter.setBrush(Qt.NoBrush); painter.setPen(QPen(self.outline_color, 1.5))
        painter.drawPath(path)

        # Draw delete button
        painter.setBrush(QBrush(Qt.red)); painter.setPen(QPen(Qt.black, 1))
        painter.drawEllipse(self._delete_btn_rect)
        painter.setPen(QPen(Qt.white, 2))
        margin = 6
        x_rect = self._delete_btn_rect.adjusted(margin, margin, -margin, -margin)
        painter.drawLine(x_rect.topLeft(), x_rect.bottomRight())
        painter.drawLine(x_rect.topRight(), x_rect.bottomLeft())

    def _get_handle_at(self, pos):
        if self._delete_btn_rect.contains(pos): return 'delete'
        if self._rotate_handle_rect.contains(pos): return 'rotate'
        for name, rect in self._handle_rects.items():
            if rect.contains(pos): return name
        return None

    def hoverMoveEvent(self, event):
        handle = self._get_handle_at(event.pos())
        cursor = self.parent_item.cursor()
        if handle:
            cursors = {'tl': Qt.SizeFDiagCursor, 'br': Qt.SizeFDiagCursor, 'tr': Qt.SizeBDiagCursor, 
                         'bl': Qt.SizeBDiagCursor, 't': Qt.SizeVerCursor, 'b': Qt.SizeVerCursor,
                         'l': Qt.SizeHorCursor, 'r': Qt.SizeHorCursor, 'delete': Qt.PointingHandCursor,
                         'rotate': Qt.CrossCursor}
            cursor = cursors.get(handle)
        self.setCursor(cursor)
        super().hoverMoveEvent(event)

    def mousePressEvent(self, event):
        self.active_handle = self._get_handle_at(event.pos())
        if not self.active_handle:
            event.ignore()
            return

        # --- FIX: Check for free transform mode (Ctrl key pressed on a CORNER resize handle) ---
        self.is_free_transform = (event.modifiers() & Qt.ControlModifier) and \
                                 self.active_handle in ['tl', 'tr', 'bl', 'br']

        if self.active_handle == 'delete':
            self.parent_item.request_delete()
        elif self.active_handle == 'rotate':
            self.drag_start_pos = event.scenePos()
            self.drag_start_angle = self.parent_item.rotation()
            self.drag_start_center = self.parent_item.mapToScene(self.parent_item.transformOriginPoint())
        elif self.is_free_transform:
            # --- FREE TRANSFORM START ---
            p_rect = self.parent_item.rect()
            # Store the current visual corners of the item in scene coordinates
            self.initial_scene_quad = q = [
                self.parent_item.mapToScene(p_rect.topLeft()),
                self.parent_item.mapToScene(p_rect.topRight()),
                self.parent_item.mapToScene(p_rect.bottomRight()),
                self.parent_item.mapToScene(p_rect.bottomLeft())
            ]
            
            # To make the handle follow the cursor, we must calculate the delta
            # relative to the handle's logical anchor point, not the arbitrary mouse click point.
            # By setting drag_start_pos to the anchor, the delta in mouseMoveEvent
            # becomes (current_mouse - anchor). When this delta is added to the initial
            # corner positions, it effectively makes the anchor point follow the cursor.
            handle = self.active_handle
            anchor_point = QPointF()
            if   handle == 'tl': anchor_point = q[0]
            elif handle == 'tr': anchor_point = q[1]
            elif handle == 'br': anchor_point = q[2]
            elif handle == 'bl': anchor_point = q[3]
            self.drag_start_pos = anchor_point

        else:  # --- REGULAR RESIZE START ---
            self.drag_start_pos = event.scenePos()
            self.drag_start_rect = self.parent_item.sceneBoundingRect()
        
        event.accept()

    def mouseMoveEvent(self, event):
        if self.is_free_transform and self.active_handle:
            # --- FREE TRANSFORM LOGIC ---
            delta = event.scenePos() - self.drag_start_pos
            new_scene_quad_pts = list(self.initial_scene_quad)
            handle = self.active_handle

            # Move the corner(s) corresponding to the dragged handle.
            # Quad points order: 0:tl, 1:tr, 2:br, 3:bl
            if handle == 'tl': new_scene_quad_pts[0] += delta
            elif handle == 'tr': new_scene_quad_pts[1] += delta
            elif handle == 'br': new_scene_quad_pts[2] += delta
            elif handle == 'bl': new_scene_quad_pts[3] += delta
            # --- The code for side handles below is now unreachable, ---
            # --- but is kept for completeness/future reference.      ---
            elif handle == 't':
                new_scene_quad_pts[0] += delta; new_scene_quad_pts[1] += delta
            elif handle == 'b':
                new_scene_quad_pts[2] += delta; new_scene_quad_pts[3] += delta
            elif handle == 'l':
                new_scene_quad_pts[0] += delta; new_scene_quad_pts[3] += delta
            elif handle == 'r':
                new_scene_quad_pts[1] += delta; new_scene_quad_pts[2] += delta
            
            # Source quad is the item's local, untransformed rectangle
            parent_rect = self.parent_item.rect()
            source_poly = QPolygonF([parent_rect.topLeft(), parent_rect.topRight(), parent_rect.bottomRight(), parent_rect.bottomLeft()])
            
            # Target quad is the new set of corners in scene coordinates
            target_poly = QPolygonF(new_scene_quad_pts)
            
            # To avoid compounding transforms, reset pos/rotation and control geometry with a single QTransform.
            self.parent_item.prepareGeometryChange()
            self.parent_item.setPos(0, 0)
            self.parent_item.setRotation(0)

            transform = QTransform()
            ok = QTransform.quadToQuad(source_poly, target_poly, transform)
            
            if ok:
                self.parent_item.setTransform(transform)
            event.accept()
        
        elif self.active_handle == 'rotate':
            start_line = QLineF(self.drag_start_center, self.drag_start_pos)
            current_line = QLineF(self.drag_start_center, event.scenePos())
            angle_delta = start_line.angleTo(current_line)
            self.parent_item.setRotation(self.drag_start_angle - angle_delta)
            event.accept()

        elif self.active_handle and self.active_handle != 'delete':
            # --- REGULAR RESIZE LOGIC ---
            # Reset any free-transform to ensure a predictable rectangular result.
            self.parent_item.setTransform(QTransform())
            
            delta = event.scenePos() - self.drag_start_pos
            new_rect = QRectF(self.drag_start_rect)

            if self.active_handle == 'tl': new_rect.setTopLeft(new_rect.topLeft() + delta)
            elif self.active_handle == 'tr': new_rect.setTopRight(new_rect.topRight() + delta)
            elif self.active_handle == 'bl': new_rect.setBottomLeft(new_rect.bottomLeft() + delta)
            elif self.active_handle == 'br': new_rect.setBottomRight(new_rect.bottomRight() + delta)
            elif self.active_handle == 't': new_rect.setTop(new_rect.top() + delta.y())
            elif self.active_handle == 'b': new_rect.setBottom(new_rect.bottom() + delta.y())
            elif self.active_handle == 'l': new_rect.setLeft(new_rect.left() + delta.x())
            elif self.active_handle == 'r': new_rect.setRight(new_rect.right() + delta.x())

            min_w, min_h = self.parent_item.min_width, self.parent_item.min_height
            if new_rect.width() < min_w:
                if self.active_handle in ['tl', 'bl', 'l']: new_rect.setLeft(new_rect.right() - min_w)
                else: new_rect.setWidth(min_w)
            if new_rect.height() < min_h:
                if self.active_handle in ['tl', 'tr', 't']: new_rect.setTop(new_rect.bottom() - min_h)
                else: new_rect.setHeight(min_h)
            
            self.parent_item.prepareGeometryChange()
            self.parent_item.setPos(new_rect.topLeft())
            self.parent_item.setRect(QRectF(0, 0, new_rect.width(), new_rect.height()))
            event.accept()
        else:
            event.ignore()

    def mouseReleaseEvent(self, event):
        self.active_handle = None
        self.drag_start_pos = None
        self.drag_start_rect = None
        self.drag_start_angle = 0
        self.drag_start_center = None
        self.is_free_transform = False
        self.initial_scene_quad = None
        self.setCursor(self.parent_item.cursor())
        event.accept()


# --- Signal class remains the same ---
class TextBoxSignals(QObject):
    rowDeleted = pyqtSignal(object)
    selectedChanged = pyqtSignal(bool, object)

# --- The Refactored TextBoxItem ---
# (No changes needed in this class)
class TextBoxItem(QGraphicsRectItem):
    def __init__(self, rect, row_number, text="", original_rect=None, initial_style=None):
        self.padding = 10
        bubble_rect = rect.adjusted(-self.padding, -self.padding, self.padding, self.padding)
        super().__init__(QRectF(0, 0, bubble_rect.width(), bubble_rect.height()))
        self.setPos(bubble_rect.x(), bubble_rect.y())
        self.setTransformOriginPoint(self.rect().center()) # For rotation

        self.signals = TextBoxSignals()
        self.setFlag(QGraphicsItem.ItemIsMovable, True)
        self.setFlag(QGraphicsItem.ItemIsSelectable, True)
        self.setFlag(QGraphicsItem.ItemSendsGeometryChanges, True)
        self.row_number = row_number
        self.original_rect = original_rect

        # --- Style and State Variables ---
        self._bubble_type, self.corner_radius, self._auto_font_size = 1, 50, True
        self._fill_type, self._bg_color, self._bg_gradient = 'solid', QColor(255, 255, 255), None
        self._border_width, self._border_color = 1, QColor(0, 0, 0)
        self._text_color_type, self._text_color, self._text_gradient = 'solid', QColor(0, 0, 0), None
        self._font, self._alignment = QFont("Arial", 12), Qt.AlignCenter
        self._original_pen = QPen(self._border_color, self._border_width)

        self.min_width, self.min_height = 50, 30
        
        # --- Create Selection Frame ---
        self.selection_frame = SelectionFrameItem(self)
        self.selection_frame.hide()

        # --- Text Item ---
        self.text_item = QGraphicsTextItem(text, self)
        
        if initial_style: self.apply_styles(initial_style)
        else: self.apply_styles({}) # Apply defaults

        self.setCursor(Qt.SizeAllCursor)

    def request_delete(self):
        """Emits the rowDeleted signal."""
        self.signals.rowDeleted.emit(self.row_number)

    def itemChange(self, change, value):
        if change == QGraphicsItem.ItemSelectedHasChanged:
            selected = bool(value)
            self.selection_frame.setVisible(selected)
            self.signals.selectedChanged.emit(selected, self.row_number)
        
        elif change == QGraphicsItem.ItemPositionChange and self.scene():
            # This logic is complex with rotation. For now, we'll keep it simple.
            # A truly robust solution would need to account for the rotated bounding box.
            scene_rect = self.scene().sceneRect()
            # Approximate the bounding rect in scene coords
            item_scene_rect = self.sceneBoundingRect()
            # Calculate future rect
            current_pos = self.pos()
            future_rect_pos = value
            future_rect = item_scene_rect.translated(future_rect_pos - current_pos)

            new_pos = QPointF(value)
            if future_rect.left() < scene_rect.left(): new_pos.setX(value.x() - (future_rect.left() - scene_rect.left()))
            elif future_rect.right() > scene_rect.right(): new_pos.setX(value.x() - (future_rect.right() - scene_rect.right()))
            if future_rect.top() < scene_rect.top(): new_pos.setY(value.y() - (future_rect.top() - scene_rect.top()))
            elif future_rect.bottom() > scene_rect.bottom(): new_pos.setY(value.y() - (future_rect.bottom() - scene_rect.bottom()))
            
            if new_pos != value and self.original_rect:
                 self.original_rect = self.rect().translated(new_pos)
            return new_pos

        elif change == QGraphicsItem.ItemScenePositionHasChanged:
            if self.original_rect is not None:
                self.original_rect = self.sceneBoundingRect()

        return super().itemChange(change, value)

    def apply_styles(self, style_dict):
        style_dict = self._ensure_style_defaults(style_dict)
        self._bubble_type = style_dict.get('bubble_type', 1)
        self.corner_radius = style_dict.get('corner_radius', 50)
        self._fill_type = style_dict.get('fill_type', 'solid')
        self._bg_color = QColor(style_dict.get('bg_color', '#ffffffff'))
        if self._fill_type == 'linear_gradient':
            gradient_data = style_dict.get('bg_gradient', {})
            self._bg_gradient = {
                'color1': QColor(gradient_data.get('color1', '#ffffffff')),
                'color2': QColor(gradient_data.get('color2', '#ffcccccc')),
                'direction': gradient_data.get('direction', 0),
                'midpoint': float(gradient_data.get('midpoint', 50))
            }
            self.setBrush(QBrush(Qt.NoBrush))
        else:
            self._bg_gradient = None
            self.setBrush(QBrush(self._bg_color))

        self._border_color = QColor(style_dict.get('border_color', '#ff000000'))
        self._border_width = style_dict.get('border_width', 1)
        new_pen = QPen(self._border_color, self._border_width)
        new_pen.setStyle(Qt.NoPen if self._border_width == 0 else Qt.SolidLine)
        self._original_pen = new_pen
        self.setPen(self._original_pen)

        self._text_color_type = style_dict.get('text_color_type', 'solid')
        self._text_color = QColor(style_dict.get('text_color', '#ff000000'))
        if self._text_color_type == 'linear_gradient':
            gradient_data = style_dict.get('text_gradient', {})
            self._text_gradient = {
                'color1': QColor(gradient_data.get('color1', '#ffffffff')),
                'color2': QColor(gradient_data.get('color2', '#ffcccccc')),
                'direction': gradient_data.get('direction', 0),
                'midpoint': float(gradient_data.get('midpoint', 50))
            }
            self.text_item.setVisible(False)
            self.text_item.setDefaultTextColor(Qt.transparent)
        else:
            self._text_gradient = None
            self.text_item.setDefaultTextColor(self._text_color)
            self.text_item.setVisible(True)

        font_family = style_dict.get('font_family', "Arial")
        font_size = style_dict.get('font_size', 12)
        font_bold = style_dict.get('font_bold', False)
        font_italic = style_dict.get('font_italic', False)
        self._auto_font_size = style_dict.get('auto_font_size', True)
        self._font = QFont()
        if font_family != "Default (System Font)": self._font.setFamily(font_family)
        self._font.setPointSize(font_size); self._font.setBold(font_bold); self._font.setItalic(font_italic)
        self.text_item.setFont(self._font)
        alignment_index = style_dict.get('text_alignment', 1)
        if alignment_index == 0: self._alignment = Qt.AlignLeft | Qt.AlignVCenter
        elif alignment_index == 1: self._alignment = Qt.AlignCenter
        elif alignment_index == 2: self._alignment = Qt.AlignRight | Qt.AlignVCenter
        else: self._alignment = Qt.AlignCenter
        doc_option = self.text_item.document().defaultTextOption()
        doc_option.setAlignment(self._alignment)
        self.text_item.document().setDefaultTextOption(doc_option)
        
        self.prepareGeometryChange()
        if self.rect().isValid(): self.setRect(self.rect())
        self.update()

    def _ensure_style_defaults(self, style_dict):
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
        super().setRect(local_rect)
        self.setTransformOriginPoint(local_rect.center()) # Update rotation origin
        padding = self.padding
        text_rect_width = max(0, new_width - 2 * padding)
        self.text_item.setTextWidth(text_rect_width)
        self.adjust_font_size()
        if hasattr(self, 'selection_frame'):
            self.selection_frame.prepareGeometryChange() # Inform frame to update

    def adjust_font_size(self):
        padding = self.padding
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
        font = self.text_item.font()
        if self._auto_font_size:
            min_font_size = 6; max_font_size = 72
            low, high = min_font_size, max_font_size
            optimal_size = low
            temp_text = QGraphicsTextItem()
            temp_text.setPlainText(text)
            temp_text.setTextWidth(available_width)
            temp_text.document().setDefaultTextOption(self.text_item.document().defaultTextOption())
            while low <= high:
                mid = (low + high) // 2
                if mid < min_font_size: break
                current_font = QFont(font); current_font.setPointSize(mid)
                temp_text.setFont(current_font)
                text_rect = temp_text.boundingRect()
                doc_height = temp_text.document().size().height()
                if doc_height <= available_height and text_rect.width() <= available_width:
                    optimal_size = mid; low = mid + 1
                else:
                    high = mid - 1
            del temp_text
            font.setPointSize(optimal_size)
            self.text_item.setFont(font)
            self._font = QFont(font)
        text_height = self.text_item.boundingRect().height()
        doc_height = self.text_item.document().size().height()
        effective_text_height = max(text_height, doc_height)
        vertical_offset = padding
        if self._alignment & Qt.AlignVCenter:
             vertical_offset = (self.rect().height() - effective_text_height) / 2
        elif self._alignment & Qt.AlignBottom:
             vertical_offset = self.rect().height() - effective_text_height - padding
        vertical_offset = max(padding, vertical_offset)
        self.text_item.setPos(padding, vertical_offset)

    def paint(self, painter, option, widget):
        painter.setRenderHint(QPainter.Antialiasing)
        rect = self.rect()
        path = QPainterPath()
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
        if self._fill_type == 'linear_gradient' and self._bg_gradient:
            gradient = QLinearGradient()
            direction = self._bg_gradient['direction']
            if direction == 0: gradient.setStart(rect.topLeft()); gradient.setFinalStop(rect.topRight())
            elif direction == 1: gradient.setStart(rect.topLeft()); gradient.setFinalStop(rect.bottomLeft())
            elif direction == 2: gradient.setStart(rect.topLeft()); gradient.setFinalStop(rect.bottomRight())
            elif direction == 3: gradient.setStart(rect.bottomLeft()); gradient.setFinalStop(rect.topRight())
            color1 = self._bg_gradient['color1']; color2 = self._bg_gradient['color2']
            midpoint_float = max(0.0, min(1.0, self._bg_gradient['midpoint'] / 100.0))
            gradient.setColorAt(0.0, color1); gradient.setColorAt(midpoint_float, color1); gradient.setColorAt(1.0, color2)
            painter.fillPath(path, gradient)
        elif self._fill_type == 'solid':
            painter.fillPath(path, self.brush())
        if self.pen().style() != Qt.NoPen:
            painter.strokePath(path, self.pen())
        if self._text_color_type == 'linear_gradient' and self._text_gradient:
            text = self.text_item.toPlainText()
            if text:
                text_pos = self.text_item.pos(); text_width = self.text_item.textWidth()
                text_height = self.text_item.document().size().height()
                text_rect = QRectF(text_pos.x(), text_pos.y(), text_width, text_height)
                if text_rect.isValid():
                    gradient = QLinearGradient()
                    direction = self._text_gradient['direction']
                    if direction == 0: gradient.setStart(text_rect.topLeft()); gradient.setFinalStop(text_rect.topRight())
                    elif direction == 1: gradient.setStart(text_rect.topLeft()); gradient.setFinalStop(text_rect.bottomLeft())
                    elif direction == 2: gradient.setStart(text_rect.topLeft()); gradient.setFinalStop(text_rect.bottomRight())
                    elif direction == 3: gradient.setStart(text_rect.bottomLeft()); gradient.setFinalStop(text_rect.topRight())
                    color1 = self._text_gradient['color1']; color2 = self._text_gradient['color2']
                    midpoint_float = max(0.0, min(1.0, self._text_gradient['midpoint'] / 100.0))
                    gradient.setColorAt(0.0, color1); gradient.setColorAt(midpoint_float, color1); gradient.setColorAt(1.0, color2)
                    painter.setFont(self._font); painter.setPen(QPen(gradient, 0))
                    draw_flags = int(self._alignment | Qt.TextWordWrap)
                    painter.drawText(text_rect, draw_flags, text)

    def cleanup(self):
        if hasattr(self, 'signals'):
            try:
                self.signals.rowDeleted.disconnect()
                self.signals.selectedChanged.disconnect()
            except (TypeError, RuntimeError): pass
        for child in reversed(self.childItems()):
            child.setParentItem(None)
            if child.scene(): child.scene().removeItem(child)
        self.text_item = None
        self.selection_frame = None
        if self.scene(): self.scene().removeItem(self)