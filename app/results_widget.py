from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QFrame, QScrollArea, QStackedWidget,
                             QCheckBox, QPushButton, QTableWidget, QTableWidgetItem, QMessageBox, QHeaderView,
                             QTextEdit)
from PyQt5.QtCore import Qt, QEvent
from PyQt5.QtGui import QFontMetrics
import qtawesome as qta
import math

from app.ui_widget import TextEditDelegate
from assets.styles import (ADVANCED_CHECK_STYLES, SIMPLE_VIEW_STYLES, DELETE_ROW_STYLES)

class ResultsWidget(QWidget):
    def __init__(self, main_window, combine_action, find_action):
        super().__init__()
        self.main_window = main_window
        self.combine_action = combine_action
        self.find_action = find_action
        self._init_ui()
        
    def _init_ui(self):
        # Main layout for this new composite widget
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(10)

        # --- Content Stack (Simple/Advanced Views) ---
        self.right_content_stack = QStackedWidget()

        # Advanced View: Table
        self.results_table = QTableWidget()
        self.results_table.setColumnCount(6)
        self.results_table.setHorizontalHeaderLabels(["Text", "Confidence", "Coordinates", "File", "Row Number", ""])
        self.results_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.results_table.setColumnWidth(1, 50)
        self.results_table.setColumnWidth(2, 50)
        self.results_table.setColumnWidth(3, 50)
        self.results_table.setColumnWidth(4, 50)
        self.results_table.setColumnWidth(5, 50)
        self.results_table.horizontalHeader().setSectionResizeMode(5, QHeaderView.Fixed)
        self.results_table.setContextMenuPolicy(Qt.ActionsContextMenu)
        self.results_table.setWordWrap(True)
        self.results_table.setItemDelegateForColumn(0, TextEditDelegate(self))
        self.results_table.addAction(self.combine_action)
        self.results_table.addAction(self.find_action)
        self.results_table.cellChanged.connect(self.on_cell_changed)
        self.results_table.installEventFilter(self)

        # Simple View: Scrollable List
        self.simple_view_widget = QWidget()
        self.simple_layout = QVBoxLayout(self.simple_view_widget)
        self.simple_layout.setContentsMargins(5, 5, 5, 5)
        self.simple_layout.setSpacing(10)
        self.simple_scroll = QScrollArea()
        self.simple_scroll.setWidgetResizable(True)
        self.simple_scroll_content = QWidget()
        self.simple_scroll_layout = QVBoxLayout(self.simple_scroll_content)
        self.simple_scroll.setWidget(self.simple_scroll_content)
        self.simple_scroll.setStyleSheet("border: none;")

        # Add views to stack
        self.right_content_stack.addWidget(self.simple_scroll) # Index 0
        self.right_content_stack.addWidget(self.results_table) # Index 1

        main_layout.addWidget(self.right_content_stack, 1)

    def update_views(self):
        """Public method called by MainWindow to refresh the currently visible view."""
        if self.main_window.advanced_mode_check.isChecked():
            self.update_results_table()
        else:
            self.update_simple_view()

    def update_simple_view(self):
        self.main_window._clear_layout(self.simple_scroll_layout)
        visible_results = [res for res in self.main_window.ocr_results if not res.get('is_deleted', False)]

        for result in visible_results:
            original_row_number = result['row_number']
            container = QWidget()
            container.setProperty("ocr_row_number", original_row_number)
            container.setObjectName(f"SimpleViewRowContainer_{original_row_number}")
            container_layout = QHBoxLayout(container)
            container_layout.setContentsMargins(5, 5, 5, 5); container_layout.setSpacing(10)
            text_frame = QFrame(); text_frame.setStyleSheet(SIMPLE_VIEW_STYLES)
            text_layout = QVBoxLayout(text_frame); text_layout.setContentsMargins(0, 0, 0, 0)
            text_edit = QTextEdit(result['text']); text_edit.setStyleSheet(SIMPLE_VIEW_STYLES)
            text_edit.setLineWrapMode(QTextEdit.WidgetWidth)
            text_edit.textChanged.connect(lambda rn=original_row_number, te=text_edit: self.on_simple_text_changed(rn, te.toPlainText()))
            text_layout.addWidget(text_edit)
            delete_btn = QPushButton(qta.icon('fa5s.trash-alt', color='red'), "")
            delete_btn.setFixedSize(40, 40); delete_btn.setStyleSheet(DELETE_ROW_STYLES)
            delete_btn.clicked.connect(lambda _, rn=original_row_number: self.main_window.delete_row(rn))
            container_layout.addWidget(text_frame, 1); container_layout.addWidget(delete_btn)
            self.simple_scroll_layout.addWidget(container)

        self.simple_scroll_layout.addStretch()
        if self.main_window.find_replace_widget.isVisible(): self.main_window.find_replace_widget.find_text()

    def on_simple_text_changed(self, original_row_number, text):
        # This method now acts as a controller, calling MainWindow to update the data
        # and then updating sibling views if necessary.
        target_result, _ = self.main_window._find_result_by_row_number(original_row_number)
        if target_result:
            if target_result.get('is_deleted', False): return
            if target_result['text'] != text:
                 self.main_window.update_ocr_text(original_row_number, text)
                 self._update_table_cell_if_visible(original_row_number, 0, text)
                 if self.main_window.find_replace_widget.isVisible() and self.main_window.find_replace_widget.find_input.text():
                     self.main_window.find_replace_widget.find_text()

    def update_results_table(self):
        self.results_table.blockSignals(True)
        visible_results = [res for res in self.main_window.ocr_results if not res.get('is_deleted', False)]
        self.results_table.setRowCount(len(visible_results))

        for visible_row_index, result in enumerate(visible_results):
            original_row_number = result['row_number']
            try:
                 rn_float = float(original_row_number)
                 display_row_number = f"{int(rn_float)}" if rn_float.is_integer() else f"{rn_float:.1f}"
            except (ValueError, TypeError): display_row_number = str(original_row_number)

            text_item = QTableWidgetItem(result['text'])
            text_item.setTextAlignment(Qt.AlignTop | Qt.AlignLeft)
            text_item.setFlags(text_item.flags() | Qt.ItemIsEditable)
            text_item.setData(Qt.UserRole, original_row_number)
            self.results_table.setItem(visible_row_index, 0, text_item)

            conf_val = result.get('confidence', float('nan'))
            conf_str = f"{conf_val:.2f}" if not math.isnan(conf_val) else "N/A"
            confidence_item = QTableWidgetItem(conf_str)
            confidence_item.setTextAlignment(Qt.AlignCenter)
            confidence_item.setFlags(confidence_item.flags() & ~Qt.ItemIsEditable)
            confidence_item.setData(Qt.UserRole, original_row_number)
            self.results_table.setItem(visible_row_index, 1, confidence_item)

            coord_str = str(result.get('coordinates', 'N/A'))
            coord_item = QTableWidgetItem(coord_str)
            coord_item.setTextAlignment(Qt.AlignCenter)
            coord_item.setFlags(coord_item.flags() & ~Qt.ItemIsEditable)
            coord_item.setData(Qt.UserRole, original_row_number)
            self.results_table.setItem(visible_row_index, 2, coord_item)

            file_item = QTableWidgetItem(result.get('filename', 'N/A'))
            file_item.setTextAlignment(Qt.AlignCenter)
            file_item.setFlags(file_item.flags() & ~Qt.ItemIsEditable)
            file_item.setData(Qt.UserRole, original_row_number)
            self.results_table.setItem(visible_row_index, 3, file_item)

            row_num_display_item = QTableWidgetItem(display_row_number)
            row_num_display_item.setTextAlignment(Qt.AlignCenter)
            row_num_display_item.setFlags(row_num_display_item.flags() & ~Qt.ItemIsEditable)
            row_num_display_item.setData(Qt.UserRole, original_row_number)
            self.results_table.setItem(visible_row_index, 4, row_num_display_item)

            delete_btn = QPushButton(qta.icon('fa5s.trash-alt', color='red'), "")
            delete_btn.setFixedSize(30, 30)
            delete_btn.setStyleSheet(DELETE_ROW_STYLES)
            container = QWidget()
            layout = QHBoxLayout(container); layout.addStretch(); layout.addWidget(delete_btn); layout.setContentsMargins(0, 0, 5, 0)
            delete_btn.clicked.connect(lambda _, rn=original_row_number: self.main_window.delete_row(rn))
            self.results_table.setCellWidget(visible_row_index, 5, container)

        self.adjust_row_heights()
        self.results_table.blockSignals(False)

    def on_cell_changed(self, row, column):
        item = self.results_table.item(row, column)
        if not item: return
        original_row_number = item.data(Qt.UserRole)
        if original_row_number is None: return

        target_result, _ = self.main_window._find_result_by_row_number(original_row_number)
        if not target_result or target_result.get('is_deleted', False): return

        if column == 0:
             new_text = item.text()
             if target_result['text'] != new_text:
                 self.main_window.update_ocr_text(original_row_number, new_text)
                 self._update_simple_view_text_if_visible(original_row_number, new_text)
                 if self.main_window.find_replace_widget.isVisible() and self.main_window.find_replace_widget.find_input.text():
                    self.main_window.find_replace_widget.find_text()

    def _update_table_cell_if_visible(self, original_row_number, column, new_value):
        if not self.main_window.advanced_mode_check.isChecked(): return

        for row in range(self.results_table.rowCount()):
            item = self.results_table.item(row, column)
            if item and item.data(Qt.UserRole) == original_row_number:
                self.results_table.blockSignals(True)
                item.setText(str(new_value))
                self.results_table.blockSignals(False)
                if column == 0: self.adjust_row_heights()
                break

    def _update_simple_view_text_if_visible(self, original_row_number, new_text):
        if self.main_window.advanced_mode_check.isChecked(): return

        for i in range(self.simple_scroll_layout.count()):
             widget = self.simple_scroll_layout.itemAt(i).widget()
             if isinstance(widget, QWidget) and widget.property("ocr_row_number") == original_row_number:
                 text_edit = widget.findChild(QTextEdit)
                 if text_edit:
                     text_edit.blockSignals(True)
                     if text_edit.toPlainText() != new_text:
                         text_edit.setText(new_text)
                     text_edit.blockSignals(False)
                 break

    def adjust_row_heights(self):
        font_metrics = QFontMetrics(self.results_table.font())
        base_padding = 10
        for row in range(self.results_table.rowCount()):
            text_item = self.results_table.item(row, 0)
            if text_item:
                text = text_item.text()
                column_width = self.results_table.columnWidth(0) - 10
                if column_width > 0:
                    rect = font_metrics.boundingRect(0, 0, column_width, 0, Qt.TextWordWrap, text)
                    required_height = rect.height() + base_padding
                    min_height = 40
                    self.results_table.setRowHeight(row, max(required_height, min_height))
            else:
                self.results_table.setRowHeight(row, 40)

    def eventFilter(self, obj, event):
        if obj == self.results_table and event.type() == QEvent.Resize:
            self.adjust_row_heights()
        return super().eventFilter(obj, event)

    def combine_selected_rows(self):
        selected_ranges = self.results_table.selectedRanges()
        if not selected_ranges: return

        selected_original_row_numbers_raw = set()
        for r in selected_ranges:
            for row in range(r.topRow(), r.bottomRow() + 1):
                item = self.results_table.item(row, 0)
                if item:
                    rn_raw = item.data(Qt.UserRole)
                    if rn_raw is not None: selected_original_row_numbers_raw.add(rn_raw)

        if len(selected_original_row_numbers_raw) < 2: return

        selected_original_row_numbers = []
        for rn_raw in selected_original_row_numbers_raw:
            try: selected_original_row_numbers.append(float(rn_raw))
            except (ValueError, TypeError): QMessageBox.critical(self, "Error", "Invalid row number data."); return
        selected_original_row_numbers.sort()

        selected_results = []; filename_set = set(); contains_float = False
        for rn_float in selected_original_row_numbers:
            result, _ = self.main_window._find_result_by_row_number(rn_float)
            if result and not result.get('is_deleted', False):
                selected_results.append(result)
                filename_set.add(result.get('filename'))
                rn_orig = result.get('row_number')
                if isinstance(rn_orig, float) and not rn_orig.is_integer(): contains_float = True
            else: QMessageBox.critical(self, "Error", f"Result {rn_float} not found/deleted."); return

        if len(filename_set) > 1: QMessageBox.warning(self, "Warning", "Cannot combine rows from different files"); return
        if contains_float: QMessageBox.warning(self, "Combine Restriction", "Combining manually added rows (decimal numbers) is not supported yet."); return

        is_adjacent = all(math.isclose(selected_original_row_numbers[i+1] - selected_original_row_numbers[i], 1.0) for i in range(len(selected_original_row_numbers) - 1))
        if not is_adjacent: QMessageBox.warning(self, "Warning", "Selected standard rows must be a contiguous sequence."); return

        selected_results.sort(key=lambda x: float(x.get('row_number', float('inf'))))
        combined_text_list = [res['text'] for res in selected_results]
        min_confidence = min(res.get('confidence', 0.0) for res in selected_results)
        first_result = selected_results[0]
        rows_to_delete = [res['row_number'] for res in selected_results[1:]]

        self.main_window.combine_rows_in_model(
            first_result['row_number'],
            '\n'.join(combined_text_list),
            min_confidence,
            rows_to_delete
        )