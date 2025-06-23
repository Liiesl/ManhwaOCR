from PyQt5.QtWidgets import QWidget, QHBoxLayout, QLabel, QPushButton
from PyQt5.QtCore import Qt, QPoint, QObject, QEvent, QRect
from PyQt5.QtGui import QCursor # CORRECTED: Import QCursor
import qtawesome

## ADDED: A custom title bar widget ##
class CustomTitleBar(QWidget):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.layout = QHBoxLayout()
        self.layout.setContentsMargins(5, 0, 5, 0)
        self.layout.setSpacing(0)

        self.title = QLabel("ManhwaOCR")
        self.title.setFixedHeight(35)
        self.title.setAlignment(Qt.AlignCenter)
        self.title.setStyleSheet("""
            background-color: #2B2B2B;
            color: white;
            font-weight: bold;
            padding-left: 10px;
        """)

        btn_size = 35
        icon_color = "#AAAAAA"
        icon_hover_color = "white"

        # Create buttons
        self.btn_close = QPushButton()
        self.btn_maximize = QPushButton()
        self.btn_minimize = QPushButton()

        # Set icons using qtawesome
        self.icon_close = qtawesome.icon('fa.times', color=icon_color, color_active=icon_hover_color)
        self.icon_minimize = qtawesome.icon('msc.chrome-minimize', color=icon_color, color_active=icon_hover_color)
        self.icon_maximize = qtawesome.icon('msc.chrome-maximize', color=icon_color, color_active=icon_hover_color)
        self.icon_restore = qtawesome.icon('msc.chrome-restore', color=icon_color, color_active=icon_hover_color)
        
        self.btn_close.setIcon(self.icon_close)
        self.btn_minimize.setIcon(self.icon_minimize)
        self.btn_maximize.setIcon(self.icon_maximize) # Start with maximize icon

        # Connect signals
        self.btn_close.clicked.connect(self.parent.close)
        self.btn_maximize.clicked.connect(self.toggle_maximize_restore)
        self.btn_minimize.clicked.connect(self.parent.showMinimized)

        # Set size
        self.btn_close.setFixedSize(btn_size, btn_size)
        self.btn_maximize.setFixedSize(btn_size, btn_size)
        self.btn_minimize.setFixedSize(btn_size, btn_size)

        # Common style for buttons, specific hover colors for background
        # Note: Icon color is handled by qtawesome's `color_active` parameter
        button_style = """
            QPushButton {
                background-color: transparent;
                border: none;
            }
        """
        self.btn_close.setStyleSheet(button_style + "QPushButton:hover { background-color: #E81123; }")
        self.btn_maximize.setStyleSheet(button_style + "QPushButton:hover { background-color: #3E3E3E; }")
        self.btn_minimize.setStyleSheet(button_style + "QPushButton:hover { background-color: #3E3E3E; }")

        self.layout.addWidget(self.title)
        self.layout.addWidget(self.btn_minimize)
        self.layout.addWidget(self.btn_maximize)
        self.layout.addWidget(self.btn_close)

        self.setLayout(self.layout)

        self.start = QPoint(0, 0)
        self.pressing = False

    def toggle_maximize_restore(self):
        if self.parent.isMaximized():
            self.parent.showNormal()
        else:
            self.parent.showMaximized()
    
    def update_maximize_icon(self):
        """Updates the maximize/restore icon based on the window state."""
        if self.parent.isMaximized():
            self.btn_maximize.setIcon(self.icon_restore)
        else:
            self.btn_maximize.setIcon(self.icon_maximize)

    def mousePressEvent(self, event):
        # CORRECTED: Prioritize resize over move.
        # The WindowResizer uses a margin to detect resize events. We must prevent
        # the title bar from initiating a move when the cursor is in this margin.
        RESIZE_MARGIN = 5  # This value must match the `margin` in WindowResizer.
        child = self.childAt(event.pos())

        # Condition to start moving the window
        should_move = (
            event.button() == Qt.LeftButton and
            # a) Click was on the title bar background, not a button
            (not child or child is self.title) and
            # b) EITHER the window is maximized (no resize) OR the click was
            #    outside the top resize margin.
            (self.parent.isMaximized() or event.y() >= RESIZE_MARGIN)
        )

        if should_move:
            self.start = self.mapToGlobal(event.pos())
            self.pressing = True
        else:
            # If the conditions to move are not met (e.g., right-click, click on
            # a button, or click in the resize margin), pass the event to the
            # base class for default handling.
            super().mousePressEvent(event)


    def mouseMoveEvent(self, event):
        if self.pressing:
            end = self.mapToGlobal(event.pos())
            movement = end - self.start

            # CORRECTED: Handle dragging from a maximized state
            if self.parent.isMaximized():
                # When dragging from maximized, restore the window and position it correctly
                norm_geom = self.parent.normalGeometry()
                rel_pos_on_title = event.pos().x() / self.width()
                
                self.parent.showNormal()
                
                new_x = end.x() - norm_geom.width() * rel_pos_on_title
                new_y = end.y() - event.pos().y()
                self.parent.move(int(new_x), int(new_y))
                
                self.start = self.mapToGlobal(event.pos())
                return

            # CORRECTED: Use parent.move() for correct drag behavior
            self.parent.move(self.parent.pos() + movement)
            self.start = end
        else:
            # CORRECTED: Pass event to parent to handle resizing cursors
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        self.pressing = False
        super().mouseReleaseEvent(event)

## ADDED: A class to handle window resizing for a frameless window ##
class WindowResizer(QObject):
    def __init__(self, window):
        super().__init__(window)
        self.window = window
        self.margin = 5  # The size of the resize handles in pixels
        self.resizing = False
        self.resize_edges = {}
        self.start_pos = None
        self.start_geo = None

        # Install the event filter on the window
        self.window.setMouseTracking(True)
        self.window.installEventFilter(self)

    def eventFilter(self, obj, event):
        # We only care about mouse events for the main window object.
        if obj is not self.window or event.type() not in [QEvent.MouseMove, QEvent.MouseButtonPress, QEvent.MouseButtonRelease, QEvent.HoverMove]:
            return super().eventFilter(obj, event)

        # CORRECTED: Use QCursor.pos() which works for all mouse-related events,
        # including QHoverEvent which does not have a .globalPos() method.
        global_pos = QCursor.pos()
        pos_in_window = self.window.mapFromGlobal(global_pos)

        if event.type() == QEvent.MouseButtonPress and event.button() == Qt.LeftButton:
            # Don't start resize if window is maximized
            if not self.window.isMaximized() and self._check_edges(pos_in_window):
                self.resizing = True
                self.start_pos = global_pos
                self.start_geo = self.window.geometry()
                return True

        elif event.type() == QEvent.MouseButtonRelease and event.button() == Qt.LeftButton:
            if self.resizing:
                self.resizing = False
                self.resize_edges = {}
                return True

        elif event.type() == QEvent.MouseMove or event.type() == QEvent.HoverMove:
            if self.resizing:
                self._resize_window(global_pos)
                return True
            else:
                self._update_cursor(pos_in_window)
        
        return super().eventFilter(obj, event)

    def _check_edges(self, pos):
        """Check which edge(s) the mouse is on and store them."""
        rect = self.window.rect()
        self.resize_edges['top'] = pos.y() < self.margin
        self.resize_edges['bottom'] = pos.y() > rect.bottom() - self.margin
        self.resize_edges['left'] = pos.x() < self.margin
        self.resize_edges['right'] = pos.x() > rect.right() - self.margin
        return any(self.resize_edges.values())

    def _update_cursor(self, pos):
        """Update the cursor icon based on the mouse position over the edges."""
        # Do not show resize cursor when maximized or during a resize
        if self.window.isMaximized() or self.resizing:
            self.window.unsetCursor()
            return
            
        rect = self.window.rect()
        on_top = pos.y() < self.margin
        on_bottom = pos.y() > rect.bottom() - self.margin
        on_left = pos.x() < self.margin
        on_right = pos.x() > rect.right() - self.margin

        # Set cursor for corners and edges
        if (on_top and on_left) or (on_bottom and on_right):
            self.window.setCursor(Qt.SizeFDiagCursor)
        elif (on_top and on_right) or (on_bottom and on_left):
            self.window.setCursor(Qt.SizeBDiagCursor)
        elif on_top or on_bottom:
            self.window.setCursor(Qt.SizeVerCursor)
        elif on_left or on_right:
            self.window.setCursor(Qt.SizeHorCursor)
        else:
            self.window.unsetCursor()

    def _resize_window(self, global_pos):
        """Calculate the new window geometry and apply it, respecting minimum size."""
        delta = global_pos - self.start_pos
        start_rect = self.start_geo
        min_size = self.window.minimumSize()
        
        new_rect = QRect(start_rect)

        if self.resize_edges.get('left'):
            new_left = start_rect.left() + delta.x()
            # Clamp to the right edge if width is less than minimum
            if start_rect.width() - delta.x() < min_size.width():
                new_left = start_rect.right() - min_size.width()
            new_rect.setLeft(new_left)

        if self.resize_edges.get('right'):
            new_right = start_rect.right() + delta.x()
            # Clamp to the left edge if width is less than minimum
            if start_rect.width() + delta.x() < min_size.width():
                new_right = start_rect.left() + min_size.width()
            new_rect.setRight(new_right)

        if self.resize_edges.get('top'):
            new_top = start_rect.top() + delta.y()
            # Clamp to the bottom edge if height is less than minimum
            if start_rect.height() - delta.y() < min_size.height():
                new_top = start_rect.bottom() - min_size.height()
            new_rect.setTop(new_top)

        if self.resize_edges.get('bottom'):
            new_bottom = start_rect.bottom() + delta.y()
            # Clamp to the top edge if height is less than minimum
            if start_rect.height() + delta.y() < min_size.height():
                new_bottom = start_rect.top() + min_size.height()
            new_rect.setBottom(new_bottom)
            
        self.window.setGeometry(new_rect)