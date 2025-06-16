# --- START OF FILE app/results_view.py ---

from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QStackedWidget, QTableWidget, QHeaderView,
                             QTextEdit, QFrame, QScrollArea, QPushButton, QTableWidgetItem, QSizePolicy,
                             QCheckBox, QAbstractItemView)
from PyQt5.QtCore import Qt, pyqtSignal, QEvent, QSize, QTimer
from PyQt5.QtGui import QFontMetrics, QColor
import qtawesome as qta
import math

# Assuming TextEditDelegate is defined elsewhere (e.g., app.ui_widget)
from .ui_widget import TextEditDelegate
from assets.styles import SIMPLE_VIEW_STYLES, DELETE_ROW_STYLES

class ResultsViewWidget(QWidget):
    """
    Manages the display of OCR results in either a Simple or Advanced (Table) view.
    Handles user interactions within these views and signals changes/requests
    back to the main window.
    """
    # Signals to communicate with MainWindow
    request_delete_row = pyqtSignal(object) # Sends the original row_number
    text_changed = pyqtSignal(object, str) # Sends original row_number, new_text
    request_combine_rows = pyqtSignal(list) # Sends list of original row_numbers
    find_replace_triggered = pyqtSignal() # Signal when find/replace context action is triggered
    selection_changed = pyqtSignal(list) # Sends list of selected original row_numbers

    def __init__(self, parent=None):
        super().__init__(parent)
        self.main_window = parent # Reference to MainWindow if needed for context/settings
        self._ocr_results_cache = [] # Local cache of results to display
        self._is_advanced_mode = False # Default view state
        self._current_highlights = {} # {row_number: [(start, end), ...]}

        self._setup_ui()
        self._connect_signals()

        # Initialize view state
        self.results_table.hide()
        self.simple_view_widget.show()

    def _setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0) # Reduce spacing if needed

        self.right_content_stack = QStackedWidget()

        # --- Simple View ---
        self.simple_view_widget = QWidget()
        self.simple_layout = QVBoxLayout(self.simple_view_widget)
        self.simple_layout.setContentsMargins(5, 5, 5, 5)
        self.simple_layout.setSpacing(10)
        self.simple_scroll = QScrollArea()
        self.simple_scroll.setWidgetResizable(True)
        self.simple_scroll_content = QWidget()
        self.simple_scroll_layout = QVBoxLayout(self.simple_scroll_content)
        self.simple_scroll_layout.addStretch() # Add stretch at the end initially
        self.simple_scroll.setWidget(self.simple_scroll_content)
        self.simple_scroll.setStyleSheet("border: none;")
        self.simple_layout.addWidget(self.simple_scroll)

        # --- Advanced (Table) View ---
        self.results_table = QTableWidget()
        self.results_table.setColumnCount(6)
        self.results_table.setHorizontalHeaderLabels(["Text", "Confidence", "Coordinates", "File", "Row Number", ""])
        self.results_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.results_table.setColumnWidth(1, 80)  # Adjusted width
        self.results_table.setColumnWidth(2, 100) # Adjusted width
        self.results_table.setColumnWidth(3, 100) # Adjusted width
        self.results_table.setColumnWidth(4, 80) # Adjusted width
        self.results_table.setColumnWidth(5, 40) # Fixed width for button
        self.results_table.horizontalHeader().setSectionResizeMode(5, QHeaderView.Fixed)
        self.results_table.setContextMenuPolicy(Qt.ActionsContextMenu)
        self.results_table.setWordWrap(True)
        self.results_table.setItemDelegateForColumn(0, TextEditDelegate(self))
        self.results_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.results_table.setSelectionMode(QAbstractItemView.ExtendedSelection) # Allow multi-select
        self.results_table.installEventFilter(self) # For resize adjustments

        # Add table and simple view to stack
        self.right_content_stack.addWidget(self.simple_view_widget) # Index 0
        self.right_content_stack.addWidget(self.results_table)      # Index 1

        main_layout.addWidget(self.right_content_stack)

    def _connect_signals(self):
        self.results_table.cellChanged.connect(self._handle_cell_changed)
        self.results_table.itemSelectionChanged.connect(self._handle_table_selection_change)
        # Simple view text changes are connected dynamically when items are created

    def set_context_actions(self, combine_action, find_action):
        """Adds context menu actions provided by the main window."""
        self.results_table.addAction(combine_action)
        self.results_table.addAction(find_action)
        # Connect the triggers here to emit signals
        combine_action.triggered.connect(self._handle_combine_request)
        find_action.triggered.connect(self.find_replace_triggered.emit) # Directly emit signal

    def update_results(self, ocr_results_full):
        """
        Receives the complete list of OCR results and updates the
        internal cache and the currently visible view.
        """
        self._ocr_results_cache = [res for res in ocr_results_full if not res.get('is_deleted', False)]
        self.clear_highlights() # Clear old highlights
        # Update the currently visible view
        if self._is_advanced_mode:
            self._update_table_view()
        else:
            self._update_simple_view()

    def toggle_view(self, is_advanced):
        """Switches between Simple and Advanced view."""
        self._is_advanced_mode = is_advanced
        self.clear_highlights() # Clear highlights on view switch
        if is_advanced:
            self.right_content_stack.setCurrentIndex(1)
            self._update_table_view() # Update table content when switching to it
            self.results_table.show()
            self.simple_view_widget.hide()
        else:
            self.right_content_stack.setCurrentIndex(0)
            self._update_simple_view() # Update simple view content when switching to it
            self.simple_view_widget.show()
            self.results_table.hide()

    def _clear_layout(self, layout):
        if layout is not None:
            # Clear existing widgets except the stretch item
            while layout.count() > 1: # Keep the stretch item at the end
                item = layout.takeAt(0)
                widget = item.widget()
                if widget is not None:
                    widget.deleteLater()

    # --- Simple View Methods ---

    def _update_simple_view(self):
        self._clear_layout(self.simple_scroll_layout) # Clear previous items

        for result in self._ocr_results_cache: # Iterate through filtered cache
            original_row_number = result['row_number']
            text = result['text']

            container = QWidget()
            container.setProperty("ocr_row_number", original_row_number) # Store for reference
            container.setObjectName(f"SimpleViewRowContainer_{original_row_number}")
            container_layout = QHBoxLayout(container)
            container_layout.setContentsMargins(5, 5, 5, 5)
            container_layout.setSpacing(10)

            text_frame = QFrame()
            text_frame.setStyleSheet(SIMPLE_VIEW_STYLES) # Apply styles if needed
            text_layout = QVBoxLayout(text_frame)
            text_layout.setContentsMargins(2, 2, 2, 2) # Minimal margins for text edit

            text_edit = QTextEdit(text)
            text_edit.setStyleSheet(SIMPLE_VIEW_STYLES) # Apply styles if needed
            text_edit.setLineWrapMode(QTextEdit.WidgetWidth)
            text_edit.setObjectName(f"SimpleViewTextEdit_{original_row_number}") # For highlighting

            # Connect text changed signal, passing row number and the text edit instance
            text_edit.textChanged.connect(
                lambda rn=original_row_number, te=text_edit: self._handle_simple_text_changed(rn, te.toPlainText())
            )
            text_layout.addWidget(text_edit)

            delete_btn = QPushButton(qta.icon('fa5s.trash-alt', color='red'), "")
            delete_btn.setFixedSize(40, 40)
            delete_btn.setStyleSheet(DELETE_ROW_STYLES)
            delete_btn.setToolTip(f"Mark row {original_row_number} for deletion")
            # Connect delete button click, passing the row number
            delete_btn.clicked.connect(
                lambda _, rn=original_row_number: self.request_delete_row.emit(rn)
            )

            container_layout.addWidget(text_frame, 1) # Text takes available space
            container_layout.addWidget(delete_btn)

            # Insert new widget before the stretch item
            self.simple_scroll_layout.insertWidget(self.simple_scroll_layout.count() - 1, container)

    def _handle_simple_text_changed(self, original_row_number, text):
        # Find the corresponding result in the *main* list via signal
        self.text_changed.emit(original_row_number, text)
        # Optionally update local cache if immediate feedback is needed,
        # but primary update comes from MainWindow calling update_results

    # --- Table View Methods ---

    def _update_table_view(self):
        self.results_table.blockSignals(True)
        self.results_table.setRowCount(len(self._ocr_results_cache))

        for visible_row_index, result in enumerate(self._ocr_results_cache):
            original_row_number = result['row_number']
            try:
                 # Format row number nicely (int if whole, else float)
                 rn_float = float(original_row_number)
                 display_row_number = f"{int(rn_float)}" if rn_float.is_integer() else f"{rn_float:.1f}"
            except (ValueError, TypeError):
                 display_row_number = str(original_row_number) # Fallback

            # Column 0: Text
            text_item = QTableWidgetItem(result['text'])
            text_item.setTextAlignment(Qt.AlignTop | Qt.AlignLeft)
            text_item.setFlags(text_item.flags() | Qt.ItemIsEditable)
            text_item.setData(Qt.UserRole, original_row_number) # Store original row num
            self.results_table.setItem(visible_row_index, 0, text_item)

            # Column 1: Confidence
            conf_val = result.get('confidence', float('nan'))
            conf_str = f"{conf_val:.2f}" if not math.isnan(conf_val) else "N/A"
            confidence_item = QTableWidgetItem(conf_str)
            confidence_item.setTextAlignment(Qt.AlignCenter)
            confidence_item.setFlags(confidence_item.flags() & ~Qt.ItemIsEditable)
            confidence_item.setData(Qt.UserRole, original_row_number)
            self.results_table.setItem(visible_row_index, 1, confidence_item)

            # Column 2: Coordinates (Consider showing only bounding box?)
            coord_str = str(result.get('coordinates', 'N/A'))[:50] + "..." # Keep it short
            coord_item = QTableWidgetItem(coord_str)
            coord_item.setTextAlignment(Qt.AlignCenter)
            coord_item.setToolTip(str(result.get('coordinates', 'N/A'))) # Full coords in tooltip
            coord_item.setFlags(coord_item.flags() & ~Qt.ItemIsEditable)
            coord_item.setData(Qt.UserRole, original_row_number)
            self.results_table.setItem(visible_row_index, 2, coord_item)

            # Column 3: File
            file_item = QTableWidgetItem(result.get('filename', 'N/A'))
            file_item.setTextAlignment(Qt.AlignCenter)
            file_item.setFlags(file_item.flags() & ~Qt.ItemIsEditable)
            file_item.setData(Qt.UserRole, original_row_number)
            self.results_table.setItem(visible_row_index, 3, file_item)

            # Column 4: Row Number
            row_num_display_item = QTableWidgetItem(display_row_number)
            row_num_display_item.setTextAlignment(Qt.AlignCenter)
            row_num_display_item.setFlags(row_num_display_item.flags() & ~Qt.ItemIsEditable)
            row_num_display_item.setData(Qt.UserRole, original_row_number)
            self.results_table.setItem(visible_row_index, 4, row_num_display_item)

            # Column 5: Delete Button
            delete_btn_widget = self._create_delete_button_widget(original_row_number)
            self.results_table.setCellWidget(visible_row_index, 5, delete_btn_widget)

        self._adjust_table_row_heights()
        self.results_table.blockSignals(False)

    def _create_delete_button_widget(self, original_row_number):
        """Helper to create the delete button centered in a widget."""
        delete_btn = QPushButton(qta.icon('fa5s.trash-alt', color='red'), "")
        delete_btn.setFixedSize(30, 30)
        delete_btn.setStyleSheet(DELETE_ROW_STYLES)
        delete_btn.setToolTip(f"Mark row {original_row_number} for deletion")
        # Connect the specific button's click to the signal emit
        delete_btn.clicked.connect(lambda: self.request_delete_row.emit(original_row_number))

        # Use a container widget to center the button
        container = QWidget()
        layout = QHBoxLayout(container)
        layout.addWidget(delete_btn)
        layout.setAlignment(Qt.AlignCenter)
        layout.setContentsMargins(0, 0, 0, 0)
        return container

    def _handle_cell_changed(self, row, column):
        if column == 0: # Only care about text column changes
            item = self.results_table.item(row, column)
            if item:
                original_row_number = item.data(Qt.UserRole)
                if original_row_number is not None:
                    self.text_changed.emit(original_row_number, item.text())
                    self._adjust_table_row_heights() # Adjust height after text change

    def _handle_table_selection_change(self):
        """Emits a signal with the original row numbers of selected rows."""
        selected_rows = self.results_table.selectionModel().selectedRows()
        selected_original_row_numbers = []
        for index in selected_rows:
            item = self.results_table.item(index.row(), 0) # Get item from first column
            if item:
                rn = item.data(Qt.UserRole)
                if rn is not None:
                    selected_original_row_numbers.append(rn)
        self.selection_changed.emit(selected_original_row_numbers)

    def _handle_combine_request(self):
        """Gets selected rows and emits the request to combine."""
        selected_rows = self.results_table.selectionModel().selectedRows()
        selected_original_row_numbers = []
        for index in selected_rows:
            item = self.results_table.item(index.row(), 0) # Get item from first column
            if item:
                rn = item.data(Qt.UserRole)
                if rn is not None:
                    selected_original_row_numbers.append(rn)

        if len(selected_original_row_numbers) >= 2:
            self.request_combine_rows.emit(selected_original_row_numbers)
        else:
            # Optional: Show a small message if needed
            print("Select 2 or more rows to combine.")


    def _adjust_table_row_heights(self):
        """Adjusts row heights in the table based on text content."""
        if not self.results_table.isVisible(): # Optimization: Don't adjust if hidden
             return

        font_metrics = QFontMetrics(self.results_table.font())
        base_padding = 15 # Increased padding slightly
        min_height = 40   # Minimum height for button visibility

        for row in range(self.results_table.rowCount()):
            text_item = self.results_table.item(row, 0)
            if text_item:
                text = text_item.text()
                # Use column 0 width for calculation
                column_width = self.results_table.columnWidth(0) - 10 # Approx padding
                if column_width > 0:
                    # Calculate bounding rect for wrapped text
                    rect = font_metrics.boundingRect(0, 0, column_width, 0, Qt.TextWordWrap, text)
                    required_height = rect.height() + base_padding
                    self.results_table.setRowHeight(row, max(required_height, min_height))
                else:
                    # Fallback if column width is not yet determined
                    self.results_table.setRowHeight(row, min_height)
            else:
                self.results_table.setRowHeight(row, min_height) # Default height

    # --- Find/Replace Highlighting ---

    def clear_highlights(self):
        """Removes all current highlights from the active view."""
        self._current_highlights = {}
        if self._is_advanced_mode:
            # Clear table highlights (e.g., by resetting item backgrounds/fonts)
             for row in range(self.results_table.rowCount()):
                 item = self.results_table.item(row, 0)
                 if item:
                     item.setBackground(QColor(Qt.transparent)) # Reset background
        else:
            # Clear simple view highlights
            for i in range(self.simple_scroll_layout.count() -1): # Exclude stretch
                 container = self.simple_scroll_layout.itemAt(i).widget()
                 if container:
                     text_edit = container.findChild(QTextEdit)
                     if text_edit:
                         cursor = text_edit.textCursor()
                         cursor.select(cursor.Document)
                         fmt = cursor.charFormat()
                         fmt.setBackground(QColor(Qt.transparent)) # Reset background
                         cursor.setCharFormat(fmt)
                         cursor.clearSelection()


    def highlight_search_results(self, matches):
        """
        Applies highlights to the found matches in the currently active view.
        `matches` is a dictionary: {original_row_number: [(start_index, end_index), ...]}
        """
        self.clear_highlights() # Clear previous before applying new ones
        self._current_highlights = matches
        highlight_color = QColor("yellow") # Or get from settings/styles

        if self._is_advanced_mode:
            # Highlight table rows (simpler: just background of the text cell)
            for row in range(self.results_table.rowCount()):
                item = self.results_table.item(row, 0)
                if item:
                    original_row_number = item.data(Qt.UserRole)
                    if original_row_number in matches and matches[original_row_number]:
                        item.setBackground(highlight_color)
                    else:
                        item.setBackground(QColor(Qt.transparent)) # Ensure non-matches are clear
        else:
            # Highlight specific text ranges in simple view QTextEdits
            for i in range(self.simple_scroll_layout.count() - 1): # Exclude stretch
                container = self.simple_scroll_layout.itemAt(i).widget()
                if not container: continue

                original_row_number = container.property("ocr_row_number")
                if original_row_number in matches and matches[original_row_number]:
                    text_edit = container.findChild(QTextEdit)
                    if text_edit:
                        cursor = text_edit.textCursor()
                        fmt = cursor.charFormat()
                        fmt.setBackground(highlight_color)

                        for start, end in matches[original_row_number]:
                            cursor.setPosition(start)
                            cursor.movePosition(cursor.Right, cursor.KeepAnchor, end - start)
                            cursor.mergeCharFormat(fmt)
                        cursor.clearSelection() # Remove the final selection highlight

    # --- Event Filter ---

    def eventFilter(self, obj, event):
        """Handle table resize events to adjust row heights."""
        if obj == self.results_table and event.type() == QEvent.Resize:
            # Schedule height adjustment after the resize event is processed
            self.results_table.blockSignals(True) # Avoid triggering cellChanged during resize
            QTimer.singleShot(0, self._adjust_table_row_heights)
            self.results_table.blockSignals(False)
        return super().eventFilter(obj, event)

# --- END OF FILE app/results_view.py ---