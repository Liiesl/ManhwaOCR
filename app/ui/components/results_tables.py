# --- START OF FILE results_widget.py ---

from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QFrame, QScrollArea, QStackedWidget,
                             QPushButton, QTableWidget, QTableWidgetItem, QMessageBox, QHeaderView,
                             QTextEdit, QAbstractItemView, QStyledItemDelegate)
from PySide6.QtCore import Qt, Signal, QEvent
import qtawesome as qta
import math
from assets import SIMPLE_VIEW_STYLES, DELETE_ROW_STYLES

class ResultsWidget(QWidget):
    rowSelected = Signal(object)  # Signal to emit the row_number when selected
    def __init__(self, main_window, combine_action, find_action):
        super().__init__()
        self.main_window = main_window
        self.combine_action = combine_action
        self.find_action = find_action
        self.focused_column = 0  # Default to text column being stretched
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
        self.results_table.currentCellChanged.connect(self.on_table_item_selected)

        # --- Column resizing and word wrap changes ---
        # Disable word wrap to allow the focused column to expand on a single line.
        self.results_table.setWordWrap(False)
        # Set a fixed row height as dynamic height adjustment is no longer needed.
        self.results_table.verticalHeader().setDefaultSectionSize(40)
        
        # The delete button column (5) should always have a fixed size.
        self.results_table.setColumnWidth(5, 50)
        self.results_table.horizontalHeader().setSectionResizeMode(5, QHeaderView.Fixed)

        self.results_table.setContextMenuPolicy(Qt.ActionsContextMenu)
        self.results_table.setItemDelegateForColumn(0, TextEditDelegate(self))
        self.results_table.addAction(self.combine_action)
        self.results_table.addAction(self.find_action)
        self.results_table.cellChanged.connect(self.on_cell_changed)
        
        # Connect signal to handle dynamic column resizing on focus change.
        self.results_table.currentCellChanged.connect(self.on_table_focus_changed)
        # Set the initial column sizes.
        self.update_column_resize_modes()
        # --- End of changes ---

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

    def eventFilter(self, source, event):
        # --- MODIFICATION: Filter for FocusIn on a QTextEdit ---
        if event.type() == QEvent.FocusIn and isinstance(source, QTextEdit):
            row_number = source.property("ocr_row_number")
            if row_number is not None:
                self.rowSelected.emit(row_number)
            # We don't consume the event, just react to it
            return False
        return super().eventFilter(source, event)

    def on_table_item_selected(self, currentRow, currentColumn, previousRow, previousColumn):
        # Slot for the advanced view (table) selection
        item = self.results_table.item(currentRow, 0) # Always get data from first column
        if item:
            row_number = item.data(Qt.UserRole)
            if row_number is not None:
                self.rowSelected.emit(row_number)

    def update_views(self):
        """Public method called by MainWindow to refresh the currently visible view."""
        if self.main_window.advanced_mode_check.isChecked():
            self.update_results_table()
        else:
            self.update_simple_view()

    def update_simple_view(self):
        self.main_window._clear_layout(self.simple_scroll_layout)
        # --- FIX: Access ocr_results from the model ---
        visible_results = [res for res in self.main_window.model.ocr_results if not res.get('is_deleted', False)]

        for result in visible_results:
            original_row_number = result['row_number']
            container = QWidget()
            container.setProperty("ocr_row_number", original_row_number)
            container.setObjectName(f"SimpleViewRowContainer_{original_row_number}")

            container_layout = QHBoxLayout(container)
            container_layout.setContentsMargins(5, 5, 5, 5); container_layout.setSpacing(10)
            text_frame = QFrame(); text_frame.setStyleSheet(SIMPLE_VIEW_STYLES)

            text_layout = QVBoxLayout(text_frame); text_layout.setContentsMargins(0, 0, 0, 0)
            # --- MODIFIED: Use get_display_text to fetch text from the active profile ---
            display_text = self.main_window.get_display_text(result)
            text_edit = QTextEdit(display_text)
            text_edit.setStyleSheet(SIMPLE_VIEW_STYLES)
            text_edit.setProperty("ocr_row_number", original_row_number)
            text_edit.installEventFilter(self)
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
        self.main_window.update_ocr_text(original_row_number, text)
        self._update_table_cell_if_visible(original_row_number, 0, text)

    def update_results_table(self):
        self.results_table.blockSignals(True)
        # --- FIX: Access ocr_results from the model ---
        visible_results = [res for res in self.main_window.model.ocr_results if not res.get('is_deleted', False)]
        self.results_table.setRowCount(len(visible_results))

        # --- NEW: Update header to show active profile ---
        active_profile = self.main_window.model.active_profile_name
        header_text = f"Text ({active_profile})" if active_profile != "Original" else "Text (Original OCR)"
        self.results_table.setHorizontalHeaderLabels([header_text, "Confidence", "Coordinates", "File", "Row Number", ""])

        for visible_row_index, result in enumerate(visible_results):
            original_row_number = result['row_number']
            try:
                 rn_float = float(original_row_number)
                 display_row_number = f"{int(rn_float)}" if rn_float.is_integer() else f"{rn_float:.1f}"
            except (ValueError, TypeError): display_row_number = str(original_row_number)

            # --- MODIFIED: Use get_display_text to fetch text from the active profile ---
            display_text = self.main_window.get_display_text(result)
            text_item = QTableWidgetItem(display_text)
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

        self.results_table.blockSignals(False)
        self.update_column_resize_modes() # Re-apply column sizing after header change

    def on_table_focus_changed(self, currentRow, currentColumn, previousRow, previousColumn):
        """
        Handles dynamic column resizing when the user changes the focused cell.
        The focused column is expanded, and others are shrunk.
        """
        # Ignore focus changes on the last column (delete button)
        if currentColumn == self.results_table.columnCount() - 1:
            return

        if currentColumn >= 0 and currentColumn != self.focused_column:
            self.focused_column = currentColumn
            self.update_column_resize_modes()

    def update_column_resize_modes(self):
        """
        Sets column resize modes based on self.focused_column. The focused column
        stretches, while others become fixed-width.
        """
        header = self.results_table.horizontalHeader()

        # Iterate over all data columns (0 to 4)
        for col_index in range(self.results_table.columnCount() - 1):
            if col_index == self.focused_column:
                header.setSectionResizeMode(col_index, QHeaderView.Stretch)
            else:
                header.setSectionResizeMode(col_index, QHeaderView.Fixed)
                # Assign reasonable shrunken widths for non-focused columns
                if col_index == 0:    # Text
                    self.results_table.setColumnWidth(col_index, 200)
                elif col_index == 1:  # Confidence
                    self.results_table.setColumnWidth(col_index, 80)
                elif col_index == 2:  # Coordinates
                    self.results_table.setColumnWidth(col_index, 150)
                elif col_index == 3:  # File
                    self.results_table.setColumnWidth(col_index, 150)
                elif col_index == 4:  # Row Number
                    self.results_table.setColumnWidth(col_index, 80)

    def on_cell_changed(self, row, column):
        item = self.results_table.item(row, column)
        if not item: return
        original_row_number = item.data(Qt.UserRole)
        if original_row_number is None: return

        if column == 0:
             new_text = item.text()
             self.main_window.update_ocr_text(original_row_number, new_text)
             self._update_simple_view_text_if_visible(original_row_number, new_text)

    def scroll_to_row(self, row_number):
        """Scrolls the active view to make the specified row_number visible, preferably centered."""
        found = False
        try:
            target_rn_float = float(row_number)
        except (ValueError, TypeError):
            print(f"Warning: Could not convert row_number '{row_number}' to float for scrolling.")
            return False

        if self.main_window.advanced_mode_check.isChecked():
            # Scroll the table view
            for row in range(self.results_table.rowCount()):
                item = self.results_table.item(row, 0)
                if item and item.data(Qt.UserRole) is not None:
                    try:
                        if math.isclose(float(item.data(Qt.UserRole)), target_rn_float):
                            # Check if the item is already visible before scrolling
                            item_rect = self.results_table.visualRect(self.results_table.indexFromItem(item))
                            viewport_rect = self.results_table.viewport().rect()
                            
                            if not viewport_rect.contains(item_rect):
                                self.results_table.scrollToItem(item, QAbstractItemView.PositionAtCenter)

                            found = True
                            break
                    except (ValueError, TypeError):
                        continue
        else:
            # Scroll the simple view
            for i in range(self.simple_scroll_layout.count()):
                widget = self.simple_scroll_layout.itemAt(i).widget()
                if widget and widget.property("ocr_row_number") is not None:
                    try:
                        if math.isclose(float(widget.property("ocr_row_number")), target_rn_float):
                            # Check if the widget is visible, then scroll to center if it's not
                            scrollbar = self.simple_scroll.verticalScrollBar()
                            viewport_height = self.simple_scroll.viewport().height()
                            current_scroll_y = scrollbar.value()

                            widget_y = widget.y()
                            widget_height = widget.height()

                            # Check if the widget is fully visible
                            is_visible = (widget_y >= current_scroll_y) and \
                                         (widget_y + widget_height <= current_scroll_y + viewport_height)
                            
                            if not is_visible:
                                # Calculate position to center the widget in the viewport
                                target_scroll_y = widget_y + (widget_height / 2) - (viewport_height / 2)
                                clamped_scroll_y = max(scrollbar.minimum(), min(int(target_scroll_y), scrollbar.maximum()))
                                scrollbar.setValue(clamped_scroll_y)
                            
                            found = True
                            break
                    except (ValueError, TypeError):
                        continue
        
        if not found:
            print(f"Info: Could not find row {row_number} in the current results view to scroll to.")
        
        return found

    def _update_table_cell_if_visible(self, original_row_number, column, new_value):
        # The `if...return` guard was incorrect and prevented syncing, so it has been removed.
        # This function is now responsible for updating the table's data representation.
        for row in range(self.results_table.rowCount()):
            item = self.results_table.item(row, column)
            if item and item.data(Qt.UserRole) == original_row_number:
                # Add a check to prevent setting the same text. This is the key fix to
                # break the infinite signal loop.
                if item.text() == str(new_value):
                    break

                self.results_table.blockSignals(True)
                item.setText(str(new_value))
                self.results_table.blockSignals(False)
                break

    def _update_simple_view_text_if_visible(self, original_row_number, new_text):
        # The `if...return` guard was incorrect and prevented syncing, so it has been removed.
        # This function is now responsible for updating the simple view's data representation.
        for i in range(self.simple_scroll_layout.count()):
             widget = self.simple_scroll_layout.itemAt(i).widget()
             if isinstance(widget, QWidget) and widget.property("ocr_row_number") == original_row_number:
                 text_edit = widget.findChild(QTextEdit)
                 if text_edit:
                     # This function already had the crucial check to see if the text was different
                     # before setting it, which correctly prevents signal loops. No changes needed here.
                     if text_edit.toPlainText() != new_text:
                         text_edit.blockSignals(True)
                         text_edit.setText(new_text)
                         text_edit.blockSignals(False)
                 break

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
        # --- MODIFIED: Combine the currently displayed text, not the original OCR text ---
        combined_text_list = [self.main_window.get_display_text(res) for res in selected_results]
        min_confidence = min(res.get('confidence', 0.0) for res in selected_results)
        first_result = selected_results[0]
        rows_to_delete = [res['row_number'] for res in selected_results[1:]]

        self.main_window.combine_rows_in_model(
            first_result['row_number'],
            '\n'.join(combined_text_list),
            min_confidence,
            rows_to_delete
        )

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