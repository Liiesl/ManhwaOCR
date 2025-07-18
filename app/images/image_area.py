from PyQt5.QtWidgets import ( QGraphicsScene, QSizePolicy, QGraphicsPixmapItem, QGraphicsEllipseItem,
                             QGraphicsTextItem, QScrollArea, QGraphicsItem, QGraphicsRectItem, QGraphicsView, QGraphicsDropShadowEffect, QTextEdit, QRubberBand)
from PyQt5.QtCore import Qt, pyqtSignal, QRectF, QPointF, QObject, QPoint, QRect, QSize, QTimer
from PyQt5.QtGui import QPainter, QFont, QBrush, QColor, QPen, QTextOption, QFontDatabase, QPainterPath, QLinearGradient
from app.images.image_area_widgets import TextBoxItem

class ResizableImageLabel(QGraphicsView):
    # Signals remain the same
    textBoxDeleted = pyqtSignal(object)
    textBoxSelected = pyqtSignal(object, object, bool)
    manual_area_selected = pyqtSignal(QRectF, object)

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
        self.original_text_entries = {}

        self._is_manual_select_active = False
        self._is_selection_active = False
        self._rubber_band = None
        self._rubber_band_origin = QPoint()

        self.setCursor(Qt.ArrowCursor)

    # --- *** MODIFIED: Method signature now accepts main_window *** ---
    def apply_translation(self, main_window, text_entries_by_row, default_style):
        """
        Applies text and styles to the image.
        It is now profile-aware by using main_window.get_display_text().
        """
        processed_default_style = self._ensure_gradient_defaults_for_ril(default_style)
        current_entries = {rn: entry for rn, entry in text_entries_by_row.items()
                           if not entry.get('is_deleted', False)}
        existing_boxes = {tb.row_number: tb for tb in self.text_boxes}
        rows_to_remove_from_list = []

        # Update or remove existing text boxes
        for row_number, text_box in list(existing_boxes.items()):
            if row_number not in current_entries:
                text_box.cleanup()
                rows_to_remove_from_list.append(row_number)
            else:
                entry = current_entries[row_number]
                # --- *** MODIFIED: Get text from the active profile via main_window *** ---
                display_text = main_window.get_display_text(entry)
                combined_style = self._combine_styles(processed_default_style, entry.get('custom_style', {}))
                
                text_box.text_item.setPlainText(display_text)
                text_box.apply_styles(combined_style)

        self.text_boxes = [tb for tb in self.text_boxes if tb.row_number not in rows_to_remove_from_list]

        # Add new text boxes
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
                
                # --- *** MODIFIED: Get text from the active profile via main_window *** ---
                display_text = main_window.get_display_text(entry)
                combined_style = self._combine_styles(processed_default_style, entry.get('custom_style', {}))
                
                text_box = TextBoxItem (QRectF(x, y, width, height),
                                         row_number,
                                         display_text,
                                         initial_style=combined_style)

                text_box.signals.rowDeleted.connect(self.handle_text_box_deleted)
                text_box.signals.selectedChanged.connect(self.on_text_box_selected)
                self.scene().addItem(text_box)
                self.text_boxes.append(text_box)

        QTimer.singleShot(0, self.update_view_transform)

    def set_manual_selection_enabled(self, enabled):
        self._is_manual_select_active = enabled
        if enabled:
            if not self._is_selection_active: self.setCursor(Qt.CrossCursor)
        else:
            if not self._is_selection_active: self.setCursor(Qt.ArrowCursor)

    def mousePressEvent(self, event):
        if not self._is_manual_select_active or self._is_selection_active:
            super().mousePressEvent(event)
            return
        if event.button() == Qt.LeftButton:
            self._rubber_band_origin = event.pos()
            if not self._rubber_band:
                self._rubber_band = QRubberBand(QRubberBand.Rectangle, self)
            self._rubber_band.setGeometry(QRect(self._rubber_band_origin, QSize()))
            self._rubber_band.show()
            event.accept()
        else:
            super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        if self._is_manual_select_active and self._rubber_band and event.button() == Qt.LeftButton and not self._rubber_band_origin.isNull():
            final_rect_viewport = self._rubber_band.geometry()
            self._rubber_band_origin = QPoint()
            if final_rect_viewport.width() > 4 and final_rect_viewport.height() > 4:
                rect_scene = self.mapToScene(final_rect_viewport).boundingRect()
                self._is_selection_active = True
                self.setCursor(Qt.ArrowCursor)
                self.manual_area_selected.emit(rect_scene, self)
            else:
                 self._rubber_band.hide()
                 self._is_selection_active = False
            event.accept()
        else:
            super().mouseReleaseEvent(event)

    def mouseMoveEvent(self, event):
        if self._is_manual_select_active and self._rubber_band and not self._rubber_band_origin.isNull() and (event.buttons() & Qt.LeftButton):
            self._rubber_band.setGeometry(QRect(self._rubber_band_origin, event.pos()).normalized())
            event.accept()
        else:
            super().mouseMoveEvent(event)

    def clear_active_selection(self):
        if self._rubber_band: self._rubber_band.hide()
        self._is_selection_active = False
        self.set_manual_selection_enabled(self._is_manual_select_active)

    def hasHeightForWidth(self):
        return True

    def heightForWidth(self, width):
        if self.original_pixmap.isNull() or self.original_pixmap.width() == 0:
            return self.minimumHeight() if self.minimumHeight() > 0 else 50
        aspect_ratio = self.original_pixmap.height() / self.original_pixmap.width()
        return int(aspect_ratio * width)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        QTimer.singleShot(0, self.update_view_transform)

    def update_view_transform(self):
        if not self.scene() or self.original_pixmap.isNull() or not self.pixmap_item: return
        scene_rect = self.scene().sceneRect()
        if scene_rect.width() == 0 or scene_rect.height() == 0: return
        viewport_width = self.viewport().width()
        scale_factor = viewport_width / scene_rect.width()
        self.resetTransform()
        self.scale(scale_factor, scale_factor)
        self.viewport().update()

    def _ensure_gradient_defaults_for_ril(self, style_dict):
        style = style_dict.copy() if style_dict else {}
        if 'fill_type' not in style: style['fill_type'] = 'solid'
        if 'bg_color' not in style: style['bg_color'] = '#ffffffff'
        if 'bg_gradient' not in style: style['bg_gradient'] = {}
        style['bg_gradient'] = {'midpoint': 50, **style['bg_gradient']}
        if 'text_color_type' not in style: style['text_color_type'] = 'solid'
        if 'text_color' not in style: style['text_color'] = '#ff000000'
        if 'text_gradient' not in style: style['text_gradient'] = {}
        style['text_gradient'] = {'midpoint': 50, **style['text_gradient']}
        if 'midpoint' in style['bg_gradient']: style['bg_gradient']['midpoint'] = int(style['bg_gradient']['midpoint'])
        if 'midpoint' in style['text_gradient']: style['text_gradient']['midpoint'] = int(style['text_gradient']['midpoint'])
        return style

    def _combine_styles(self, default_style, custom_style):
        combined = self._ensure_gradient_defaults_for_ril(default_style)
        if custom_style:
            processed_custom = self._ensure_gradient_defaults_for_ril(custom_style)
            for key, value in processed_custom.items():
                 if key in ['bg_gradient', 'text_gradient'] and isinstance(value, dict):
                     combined[key].update(value)
                     if 'midpoint' in combined[key]: combined[key]['midpoint'] = int(combined[key]['midpoint'])
                 else:
                     combined[key] = value
        return combined

    def on_text_box_selected(self, selected, row_number):
        if selected:
            for tb in self.text_boxes:
                 if tb.row_number != row_number:
                     if tb.isSelected(): tb.setSelected(False)
            self.textBoxSelected.emit(row_number, self, selected)
        else:
            self.textBoxSelected.emit(row_number, self, selected)

    def deselect_all_text_boxes(self):
        for text_box in self.text_boxes:
            if text_box.isSelected(): text_box.setSelected(False)
    
    def select_text_box(self, row_number_to_select):
        """Finds and selects a specific text box, deselecting others."""
        box_to_select = None
        for tb in self.text_boxes:
            if tb.row_number == row_number_to_select:
                box_to_select = tb
                break
        
        if box_to_select:
            # First deselect all others to ensure signals are clean
            for tb in self.text_boxes:
                if tb is not box_to_select and tb.isSelected():
                    tb.setSelected(False)
            
            # Now select the target one
            if not box_to_select.isSelected():
                box_to_select.setSelected(True)
            
            return box_to_select
        return None

    def handle_text_box_deleted(self, row_number):
        self.textBoxDeleted.emit(row_number)

    def remove_text_box_by_row(self, row_number):
        item_to_remove = None
        for tb in self.text_boxes:
            try:
                if tb.row_number == row_number or float(tb.row_number) == float(row_number):
                     item_to_remove = tb
                     break
            except (TypeError, ValueError):
                 if str(tb.row_number) == str(row_number):
                      item_to_remove = tb
                      break
        if item_to_remove:
            item_to_remove.cleanup()
            try:
                index_to_remove = -1
                for i, current_tb in enumerate(self.text_boxes):
                    if current_tb is item_to_remove:
                        index_to_remove = i
                        break
                if index_to_remove != -1:
                    del self.text_boxes[index_to_remove]
            except ValueError: pass
        else: pass

    def cleanup(self):
        try:
            self.textBoxDeleted.disconnect()
            self.textBoxSelected.disconnect()
            self.manual_area_selected.disconnect()
        except TypeError: pass
        except RuntimeError: pass
        if self.scene():
            for tb in self.text_boxes[:]: tb.cleanup()
            self.text_boxes = []
            self.scene().clear()
        self.setScene(None)

    def get_text_boxes(self):
        return self.text_boxes