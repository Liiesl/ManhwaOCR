import sys
import math
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
                             QPushButton, QSlider, QWidget, QSpacerItem, QSizePolicy,
                             QDialogButtonBox, QGridLayout, QColorDialog, QFrame,
                             QApplication, QStyle, QTabWidget, QAbstractSpinBox, QSpinBox)
from PyQt5.QtCore import Qt, pyqtSignal, pyqtSlot, QSize, QPoint, QRegularExpression, QRect, QPointF, QSettings
from PyQt5.QtGui import (QColor, QPalette, QIntValidator, QPixmap, QPainter,
                         QConicalGradient, QRadialGradient, QCursor, QScreen,
                         QRegularExpressionValidator, QIcon, QImage, QBrush, QPen)

# --- Helper Functions/Classes ---

class CheckerboardWidget(QWidget):
    """A widget that draws a checkerboard pattern as its background."""
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, False) # Sharp squares

        tileSize = 10 # Size of each checkerboard square
        bgColor1 = QColor(200, 200, 200) # Light gray
        bgColor2 = QColor(230, 230, 230) # Lighter gray

        for y in range(0, self.height(), tileSize):
            for x in range(0, self.width(), tileSize):
                if ((x // tileSize) % 2 == 0 and (y // tileSize) % 2 == 0) or \
                   ((x // tileSize) % 2 != 0 and (y // tileSize) % 2 != 0):
                    painter.fillRect(x, y, tileSize, tileSize, bgColor1)
                else:
                    painter.fillRect(x, y, tileSize, tileSize, bgColor2)

        # Let the base class paint (if needed, though not typical here)
        # super().paintEvent(event)

class ColorWheel(QWidget):
    """ A widget displaying a Hue/Saturation color wheel with a Value slider. """
    colorChanged = pyqtSignal(QColor)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._hue = 0
        self._saturation = 0
        self._value = 255 # Start with full brightness
        self._wheel_pixmap = None
        self._wheel_size = 200 # Diameter of the wheel
        self._indicator_pos = QPoint(0, 0)
        self.setMinimumSize(self._wheel_size, self._wheel_size)
        self.setCursor(Qt.CrossCursor)
        self._generate_wheel_pixmap()
        self._update_indicator_pos()

    def sizeHint(self):
        return QSize(self._wheel_size, self._wheel_size)

    def _generate_wheel_pixmap(self):
        """ Generates the H/S wheel pixmap based on current Value """
        size = self._wheel_size
        radius = size / 2.0
        image = QImage(size, size, QImage.Format_ARGB32_Premultiplied)
        image.fill(Qt.transparent) # Start transparent

        painter = QPainter(image)
        painter.setRenderHint(QPainter.Antialiasing)

        # --- Draw the Hue Wheel ---
        hue_gradient = QConicalGradient(radius, radius, 0)
        for angle in range(0, 360, 10): # Sample hues around the circle
             hue_gradient.setColorAt(angle / 360.0, QColor.fromHsvF(angle / 360.0, 1.0, self._value / 255.0))
        # Ensure the start/end point matches
        hue_gradient.setColorAt(1.0, QColor.fromHsvF(0.0, 1.0, self._value / 255.0))
        painter.setBrush(QBrush(hue_gradient))
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(0, 0, size, size)

        # --- Overlay Saturation Gradient (White center -> transparent edge) ---
        # This simulates decreasing saturation towards the center
        saturation_gradient = QRadialGradient(radius, radius, radius)
        # Center color: fully saturated (will be covered by white) -> actually needs to be transparent-ish white
        # We want white in the center (S=0) fading to transparent at the edge (S=1)
        center_color = QColor(255, 255, 255, 255) # White at center (S=0)
        center_color.setHsv(0, 0, self._value) # Adjust white brightness by V
        edge_color = QColor(255, 255, 255, 0)   # Transparent white at edge (S=1)

        saturation_gradient.setColorAt(0, center_color) # White center (S=0)
        saturation_gradient.setColorAt(1, edge_color) # Transparent edge (S=1)
        painter.setBrush(QBrush(saturation_gradient))
        painter.drawEllipse(0, 0, size, size)

        painter.end()
        self._wheel_pixmap = QPixmap.fromImage(image)
        self.update() # Request repaint

    def paintEvent(self, event):
        painter = QPainter(self)
        if self._wheel_pixmap:
            # Center the pixmap if widget is larger
            x_offset = (self.width() - self._wheel_size) / 2
            y_offset = (self.height() - self._wheel_size) / 2
            painter.drawPixmap(int(x_offset), int(y_offset), self._wheel_pixmap)

            # Draw indicator (small circle)
            indicator_size = 10
            # Ensure indicator position calculation uses integer offsets
            indicator_x = self._indicator_pos.x() + int(x_offset) - indicator_size / 2
            indicator_y = self._indicator_pos.y() + int(y_offset) - indicator_size / 2

            # Choose contrasting color for indicator
            indicator_color = QColor(0,0,0) if self._value > 128 else QColor(255,255,255)

            painter.setPen(QPen(indicator_color, 2))
            painter.setBrush(Qt.NoBrush)
            painter.drawEllipse(QPointF(indicator_x + indicator_size/2, indicator_y + indicator_size/2),
                                indicator_size/2, indicator_size/2)


    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._update_color_from_pos(event.pos())

    def mouseMoveEvent(self, event):
        if event.buttons() & Qt.LeftButton:
            self._update_color_from_pos(event.pos())

    def _update_color_from_pos(self, pos):
        """ Calculate H/S from mouse position """
        radius = self._wheel_size / 2.0
        # Calculate offsets (can be float)
        x_offset = (self.width() - self._wheel_size) / 2
        y_offset = (self.height() - self._wheel_size) / 2

        # Adjust pos relative to the wheel's center
        center_x = radius + x_offset
        center_y = radius + y_offset
        dx = pos.x() - center_x
        dy = pos.y() - center_y
        distance = math.sqrt(dx**2 + dy**2)

        # Clamp position to within the wheel radius
        if distance > radius:
            angle_rad = math.atan2(dy, dx)
            dx = radius * math.cos(angle_rad)
            dy = radius * math.sin(angle_rad)
            distance = radius
            # Update pos to the clamped position for indicator drawing
            # Calculate indicator position relative to the wheel's top-left (0,0)
            clamped_indicator_x = int(radius + dx)
            clamped_indicator_y = int(radius + dy)
            # *** FIX: Cast arguments to int for QPoint ***
            self._indicator_pos = QPoint(clamped_indicator_x, clamped_indicator_y)

        else:
             # Calculate indicator position relative to the wheel's top-left (0,0)
             indicator_relative_x = pos.x() - x_offset
             indicator_relative_y = pos.y() - y_offset
             # *** FIX: Cast arguments to int for QPoint ***
             self._indicator_pos = QPoint(int(indicator_relative_x), int(indicator_relative_y))


        # Calculate Hue (angle)
        hue_angle = math.degrees(math.atan2(-dy, dx)) # Negate dy because y increases downwards
        if hue_angle < 0:
            hue_angle += 360
        self._hue = int(hue_angle)

        # Calculate Saturation (distance from center)
        self._saturation = int(min(1.0, distance / radius) * 255)

        self._emit_color()
        self.update() # Repaint to show indicator move


    def set_color(self, color):
        """ Set the wheel's state based on an external QColor """
        if not isinstance(color, QColor) or not color.isValid(): return

        new_hue = color.hue()
        new_sat = color.saturation()
        new_val = color.value()

        # QColor uses -1 for hue of grayscale colors, handle this
        if new_hue == -1: new_hue = 0 # Default to red for grayscale on wheel? or keep old hue? let's default.

        needs_wheel_update = (new_val != self._value)

        self._hue = new_hue
        self._saturation = new_sat
        self._value = new_val

        if needs_wheel_update:
            self._generate_wheel_pixmap() # Regenerate wheel if Value changed

        self._update_indicator_pos()
        self.update() # Repaint

    def set_value(self, value):
        """ Update the Value component (0-255) and regenerate wheel """
        if self._value != value:
            self._value = value
            self._generate_wheel_pixmap()
            self._emit_color() # Emit updated color with new value

    def _update_indicator_pos(self):
        """ Calculate indicator position based on H/S """
        radius = self._wheel_size / 2.0
        angle_rad = math.radians(self._hue)
        distance = (self._saturation / 255.0) * radius

        # Calculate position relative to top-left (0,0) of the wheel itself
        indicator_x = radius + distance * math.cos(angle_rad)
        indicator_y = radius - distance * math.sin(angle_rad) # Negate sin because y increases downwards

        # *** FIX: Cast arguments to int for QPoint ***
        self._indicator_pos = QPoint(int(indicator_x), int(indicator_y))


    def _emit_color(self):
        """ Emits the current H, S, V as a QColor """
        # Use fromHsv to handle potential precision issues
        color = QColor.fromHsv(self._hue, self._saturation, self._value, self._current_color.alpha() if hasattr(self, '_current_color') else 255)
        self.colorChanged.emit(color)

class EyedropperOverlay(QWidget):
    colorSelected = pyqtSignal(QColor)

    def __init__(self, parent=None):
        # print("[Eyedropper] DEBUG: Initializing...") # Less critical setup detail
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setCursor(Qt.CrossCursor)
        self.setGeometry(self.screen_geometry())
        self.setStyleSheet("background: transparent;")

    def screen_geometry(self):
        rect = QRect()
        for screen in QApplication.screens():
            rect = rect.united(screen.geometry())
        return rect

    def mouseMoveEvent(self, event):
        # No debug print here - too frequent
        self.update()

    def paintEvent(self, event):
        # No debug print here - too frequent, primarily visual feedback
        painter = QPainter(self)
        painter.setPen(QPen(Qt.white, 2))
        pos = QCursor.pos()
        local_pos = self.mapFromGlobal(pos)
        painter.drawLine(local_pos.x() - 15, local_pos.y(), local_pos.x() + 15, local_pos.y())
        painter.drawLine(local_pos.x(), local_pos.y() - 15, local_pos.x(), local_pos.y() + 15)

    def mousePressEvent(self, event):
        # CRITICAL: Click event start
        print(f"[Eyedropper] DEBUG: Mouse Press detected. Button: {event.button()}")
        if event.button() == Qt.LeftButton:
            pos = event.globalPos()
            screen = QApplication.screenAt(pos)
            if screen:
                screen_geom = screen.geometry()
                # CRITICAL: Coordinates being used for grab
                screen_x = pos.x() - screen_geom.x()
                screen_y = pos.y() - screen_geom.y()
                print(f"[Eyedropper] DEBUG: Grabbing at screen '{screen.name()}' coords: ({screen_x}, {screen_y}) from global: {pos}")

                # CRITICAL: The screen grab itself
                pixmap = screen.grabWindow(0, screen_x, screen_y, 1, 1)

                if pixmap.isNull():
                     # CRITICAL: Grab failure
                     print("[Eyedropper] DEBUG: ERROR - Grabbed pixmap is null!")
                     color = QColor() # Invalid color
                else:
                     image = pixmap.toImage()
                     if image.isNull():
                          # CRITICAL: Image conversion failure
                          print("[Eyedropper] DEBUG: ERROR - Converted image is null!")
                          color = QColor() # Invalid color
                     else:
                        color_val = image.pixel(0, 0)
                        color = QColor(color_val)
                        # CRITICAL: Successful color extraction
                        print(f"[Eyedropper] DEBUG: Grab SUCCESS - Color: {color.name(QColor.HexRgb)}")

                # CRITICAL: Signal emission
                print(f"[Eyedropper] DEBUG: Emitting color: {color.name(QColor.HexRgb)}")
                self.colorSelected.emit(color)
            else:
                # CRITICAL: Screen detection failure
                print(f"[Eyedropper] DEBUG: ERROR - No screen found at global position: {pos}")
                self.colorSelected.emit(QColor()) # Emit invalid color

            # CRITICAL: Closing action
            print("[Eyedropper] DEBUG: Closing overlay (Left Click).")
            self.close()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            # CRITICAL: Closing action
            print("[Eyedropper] DEBUG: Escape pressed. Closing overlay.")
            self.colorSelected.emit(QColor()) # Emit invalid color on escape
            self.close()

    def closeEvent(self, event):
        # CRITICAL: Ensure cursor is always restored on close
        print("[Eyedropper] DEBUG: Close event. Restoring cursor.")
        QApplication.restoreOverrideCursor()
        super().closeEvent(event)

# --- Main Dialog ---

# Enhanced Stylesheet (add styles for new widgets)
CUSTOM_COLOR_DIALOG_V2_STYLESHEET = """
QDialog {
    background-color: #2D2D2D; /* Surface color */
    color: #FFFFFF;
    border: 1px solid #3A3A3A;
    border-radius: 10px;
    min-width: 550px; /* Wider dialog */
}
QLabel {
    color: #FFFFFF;
    font-size: 13px; /* Slightly smaller */
    background: transparent;
}
QLineEdit {
    background-color: #3A3A3A;
    color: #FFFFFF;
    border: 1px solid #4A4A4A;
    border-radius: 4px;
    padding: 5px;
    font-size: 13px;
}
QLineEdit:read-only {
    background-color: #333333;
}
QSlider::groove:horizontal {
    border: 1px solid #3A3A3A;
    height: 8px;
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #3A3A3A, stop:1 #444444); /* Subtle gradient */
    margin: 2px 0;
    border-radius: 4px;
}
QSlider::handle:horizontal {
    background: #007ACC; /* Accent */
    border: 1px solid #007ACC;
    width: 16px;
    margin: -4px 0;
    border-radius: 8px;
}
QSlider::handle:horizontal:hover {
    background: #0099EE;
}
/* Vertical slider for Value */
QSlider::groove:vertical {
    border: 1px solid #3A3A3A;
    width: 8px;
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #444444, stop:1 #3A3A3A);
    margin: 0 2px;
    border-radius: 4px;
}
QSlider::handle:vertical {
    background: #007ACC;
    border: 1px solid #007ACC;
    height: 16px;
    margin: 0 -4px;
    border-radius: 8px;
}
QSlider::handle:vertical:hover {
    background: #0099EE;
}

QPushButton {
    background-color: #3A3A3A;
    color: #FFFFFF;
    border: none;
    padding: 6px 12px; /* Smaller padding */
    border-radius: 12px; /* Consistent rounding */
    font-size: 13px;
    min-width: 60px;
}
QPushButton:hover {
    background-color: #4A4A4A;
}
QPushButton:pressed {
    background-color: #2A2A2A;
}
QPushButton#EyedropperButton, QPushButton#AddSwatchButton {
    min-width: 30px; /* Make icon buttons smaller */
    padding: 5px;
}
QPushButton#ResetButton {
    background-color: #553333; /* Different color for reset */
}
QPushButton#ResetButton:hover {
    background-color: #6F4040;
}
/* Color Previews */
#ColorPreviewCurrent, #ColorPreviewNew {
    border: 1px solid #555555;
    border-radius: 4px;
    min-height: 40px;
    min-width: 80px;
}
#ColorPreviewNew {
    /* Maybe add a subtle inner glow? */
}
/* Tab Widget */
QTabWidget::pane {
    border: 1px solid #3A3A3A;
    border-top: none; /* Pane border overlaps with tab bar */
    background-color: #333333; /* Slightly different bg for tab content */
    border-bottom-left-radius: 5px;
    border-bottom-right-radius: 5px;
     padding: 10px;
}
QTabBar::tab {
    background: #3A3A3A;
    color: #BBBBBB;
    border: 1px solid #3A3A3A;
    border-bottom: none; /* Merge with pane */
    padding: 8px 15px;
    margin-right: 2px; /* Spacing between tabs */
    border-top-left-radius: 5px;
    border-top-right-radius: 5px;
}
QTabBar::tab:selected {
    background: #333333; /* Match pane background */
    color: #FFFFFF;
    border-bottom: 1px solid #333333; /* Hide bottom border */
}
QTabBar::tab:hover {
    background: #4A4A4A;
}

/* Swatch Button */
QPushButton.SwatchButton {
    min-width: 30px;
    max-width: 30px;
    min-height: 30px;
    max-height: 30px;
    border: 1px solid #555555;
    border-radius: 4px;
    padding: 1px; /* Minimal padding */
    background-color: qlineargradient(spread:pad, x1:0, y1:0, x2:1, y2:1, stop:0 rgba(255, 255, 255, 50), stop:1 rgba(0, 0, 0, 50)); /* Default indication */
}
QPushButton.SwatchButton:hover {
     border: 1px solid #FFFFFF;
}

/* SpinBoxes for direct number input */
QSpinBox {
    background-color: #3A3A3A;
    color: #FFFFFF;
    border: 1px solid #4A4A4A;
    border-radius: 4px;
    padding: 3px 5px; /* Adjust padding */
    min-width: 45px; /* Ensure enough space for 3 digits */
}
QSpinBox::up-button, QSpinBox::down-button {
    subcontrol-origin: border;
    background-color: #4A4A4A;
    border-radius: 2px;
     /* width: 16px; Less wide */
}
QSpinBox::up-button { subcontrol-position: top right; }
QSpinBox::down-button { subcontrol-position: bottom right; }
QSpinBox::up-button:hover, QSpinBox::down-button:hover {
    background-color: #5A5A5A;
}
QSpinBox::up-arrow, QSpinBox::down-arrow {
     /* Center the arrow */
     width: 7px; height: 7px;
}
"""

class CustomColorDialog(QDialog):
    """
    An enhanced, stylable color picker dialog with multiple input methods.
    """
    colorSelected = pyqtSignal(QColor)

    # Constants for settings
    SETTINGS_GROUP = "CustomColorDialog"
    SETTINGS_RECENT_COLORS = "RecentColors"
    SETTINGS_SWATCHES = "Swatches"
    MAX_RECENT_COLORS = 12
    MAX_SWATCHES = 24 # 4 rows of 6

    def __init__(self, initial_color=QColor(255, 255, 255), parent=None):
        super().__init__(parent)
        self._initial_color = QColor(initial_color) # Store original color
        self._current_color = QColor(initial_color) # Working copy
        self._updating_controls = False # Prevent signal loops
        self._settings = QSettings() # For recent/swatches

        self.setWindowTitle("Select Color")
        self.setModal(True)
        self.setStyleSheet(CUSTOM_COLOR_DIALOG_V2_STYLESHEET)

        # Load persistent data
        self._recent_colors = self._load_colors(self.SETTINGS_RECENT_COLORS, self.MAX_RECENT_COLORS)
        self._swatches = self._load_colors(self.SETTINGS_SWATCHES, self.MAX_SWATCHES)

        # Pass initial color to ColorWheel's _emit_color
        self.color_wheel = ColorWheel()
        self.color_wheel._current_color = self._current_color # Hacky, better way?

        self.init_ui()
        self.update_controls(self._current_color, initial_update=True) # Set initial values

    def init_ui(self):
        main_layout = QHBoxLayout(self) # Main layout: Left (wheel/sliders) | Right (preview/tabs)
        main_layout.setSpacing(15)
        main_layout.setContentsMargins(15, 15, 15, 15)

        # --- Left Pane: Color Wheel and Value Slider ---
        left_pane_layout = QVBoxLayout()
        left_pane_layout.setSpacing(10)

        # Color Wheel (already created in __init__)
        # self.color_wheel = ColorWheel() # Removed from here
        self.color_wheel.colorChanged.connect(self._wheel_color_changed)
        # left_pane_layout.addWidget(self.color_wheel, alignment=Qt.AlignCenter) # Added below

        # Value Slider (Vertical)
        self.value_slider = QSlider(Qt.Vertical)
        self.value_slider.setRange(0, 255)
        self.value_slider.setToolTip("Value / Brightness")
        self.value_slider.valueChanged.connect(self._value_slider_changed)

        # Place wheel and slider side-by-side
        wheel_slider_layout = QHBoxLayout()
        wheel_slider_layout.addWidget(self.color_wheel)
        wheel_slider_layout.addWidget(self.value_slider)
        left_pane_layout.addLayout(wheel_slider_layout)

        # Eyedropper Button
        self.eyedropper_button = QPushButton()
        self.eyedropper_button.setObjectName("EyedropperButton")
        try:
             # Try a more specific icon name if available
             icon = QIcon.fromTheme("color-picker", QIcon.fromTheme("applications-graphics"))
             if icon.isNull():
                 icon = self.style().standardIcon(QStyle.SP_ArrowRight) # Fallback
        except:
             icon = self.style().standardIcon(QStyle.SP_ArrowRight) # Fallback
        self.eyedropper_button.setIcon(icon)
        self.eyedropper_button.setToolTip("Pick color from screen")
        self.eyedropper_button.setFixedSize(32, 32)
        self.eyedropper_button.clicked.connect(self._activate_eyedropper)
        left_pane_layout.addWidget(self.eyedropper_button, alignment=Qt.AlignCenter)


        main_layout.addLayout(left_pane_layout, 1) # Give left pane some stretch factor

        # --- Right Pane: Previews, Tabs (Inputs/Swatches), Buttons ---
        right_pane_layout = QVBoxLayout()
        right_pane_layout.setSpacing(10)

        # Preview Area (Comparison)
        preview_layout = QHBoxLayout()
        preview_layout.setSpacing(5)

        # Checkerboard background for previews
        self.preview_current_bg = CheckerboardWidget()
        self.preview_new_bg = CheckerboardWidget()

        preview_current_layout = QVBoxLayout(self.preview_current_bg)
        preview_current_layout.setContentsMargins(0,0,0,0)
        self.preview_current_widget = QWidget()
        self.preview_current_widget.setObjectName("ColorPreviewCurrent")
        self.preview_current_widget.setAutoFillBackground(True)
        preview_current_layout.addWidget(self.preview_current_widget)

        preview_new_layout = QVBoxLayout(self.preview_new_bg)
        preview_new_layout.setContentsMargins(0,0,0,0)
        self.preview_new_widget = QWidget()
        self.preview_new_widget.setObjectName("ColorPreviewNew")
        self.preview_new_widget.setAutoFillBackground(True)
        preview_new_layout.addWidget(self.preview_new_widget)

        preview_layout.addWidget(self.preview_current_bg, 1) # Give stretch factor
        preview_layout.addWidget(self.preview_new_bg, 1)

        # Add labels
        preview_area = QWidget()
        preview_area_layout = QVBoxLayout(preview_area)
        preview_area_layout.setContentsMargins(0,0,0,0)
        preview_area_layout.setSpacing(2)
        preview_area_layout.addLayout(preview_layout)
        label_layout = QHBoxLayout()
        label_layout.addWidget(QLabel("Original"), 1, Qt.AlignCenter)
        label_layout.addWidget(QLabel("New"), 1, Qt.AlignCenter)
        preview_area_layout.addLayout(label_layout)

        right_pane_layout.addWidget(preview_area)

        # Tab Widget for Inputs and Swatches
        self.tab_widget = QTabWidget()
        self._create_input_tabs() # Create RGB, HSV, Hex tabs
        self._create_swatch_tabs() # Create Swatches, Recent tabs
        right_pane_layout.addWidget(self.tab_widget)

        # Buttons (OK/Cancel/Reset)
        button_layout = QHBoxLayout()
        self.reset_button = QPushButton("Reset")
        self.reset_button.setObjectName("ResetButton")
        self.reset_button.clicked.connect(self._reset_color)
        button_layout.addWidget(self.reset_button)
        button_layout.addStretch(1) # Push OK/Cancel right

        self.button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.button_box.accepted.connect(self.accept_color)
        self.button_box.rejected.connect(self.reject)
        button_layout.addWidget(self.button_box)

        right_pane_layout.addLayout(button_layout)

        main_layout.addLayout(right_pane_layout, 1) # Give right pane equal stretch


    def _create_input_tabs(self):
        """ Creates the RGB, HSV, and Hex input tabs. """
        # --- RGB Tab ---
        rgb_widget = QWidget()
        rgb_layout = QGridLayout(rgb_widget)
        rgb_layout.setSpacing(8)
        self.rgb_sliders = {}
        self.rgb_spinboxes = {}
        for i, comp in enumerate(["Red", "Green", "Blue", "Alpha"]):
            label = QLabel(f"{comp}:")
            slider = QSlider(Qt.Horizontal)
            slider.setRange(0, 255)
            spinbox = QSpinBox()
            spinbox.setRange(0, 255)
            spinbox.setButtonSymbols(QAbstractSpinBox.NoButtons) # Cleaner look

            rgb_layout.addWidget(label, i, 0)
            rgb_layout.addWidget(slider, i, 1)
            rgb_layout.addWidget(spinbox, i, 2)

            slider.valueChanged.connect(lambda val, s=comp.lower(): self._slider_changed("rgb", s, val))
            spinbox.valueChanged.connect(lambda val, s=comp.lower(): self._spinbox_changed("rgb", s, val))

            self.rgb_sliders[comp.lower()] = slider
            self.rgb_spinboxes[comp.lower()] = spinbox

        self.tab_widget.addTab(rgb_widget, "RGB(A)")

        # --- HSV Tab ---
        hsv_widget = QWidget()
        hsv_layout = QGridLayout(hsv_widget)
        hsv_layout.setSpacing(8)
        self.hsv_sliders = {}
        self.hsv_spinboxes = {}
        # Note: QColor uses H(0-359 or -1), S(0-255), V(0-255)
        ranges = {"hue": 359, "saturation": 255, "value": 255}
        for i, comp in enumerate(["Hue", "Saturation", "Value"]):
            label = QLabel(f"{comp[0]}:") # H, S, V
            slider = QSlider(Qt.Horizontal)
            slider.setRange(0, ranges[comp.lower()])
            spinbox = QSpinBox()
            spinbox.setRange(0, ranges[comp.lower()])
            spinbox.setButtonSymbols(QAbstractSpinBox.NoButtons)

            hsv_layout.addWidget(label, i, 0)
            hsv_layout.addWidget(slider, i, 1)
            hsv_layout.addWidget(spinbox, i, 2)

            slider.valueChanged.connect(lambda val, s=comp.lower(): self._slider_changed("hsv", s, val))
            spinbox.valueChanged.connect(lambda val, s=comp.lower(): self._spinbox_changed("hsv", s, val))

            self.hsv_sliders[comp.lower()] = slider
            self.hsv_spinboxes[comp.lower()] = spinbox

        self.tab_widget.addTab(hsv_widget, "HSV")

        # --- Hex Tab ---
        hex_widget = QWidget()
        hex_layout = QVBoxLayout(hex_widget)
        hex_input_layout = QHBoxLayout()
        hex_label = QLabel("Hex (#RRGGBBAA):")
        self.hex_edit = QLineEdit()
        # Validator allows #, 0-9, A-F, a-f, up to 9 chars long (# + 8 hex)
        regex = QRegularExpression(r"^#[0-9A-Fa-f]{0,8}$")
        validator = QRegularExpressionValidator(regex)
        self.hex_edit.setValidator(validator)
        self.hex_edit.setMaxLength(9)
        self.hex_edit.setPlaceholderText("#RRGGBBAA")
        self.hex_edit.textEdited.connect(self.hex_changed) # Use textEdited for live feedback

        hex_input_layout.addWidget(hex_label)
        hex_input_layout.addWidget(self.hex_edit)
        hex_layout.addLayout(hex_input_layout)
        hex_layout.addStretch(1) # Push input to top
        self.tab_widget.addTab(hex_widget, "Hex")


    def _create_swatch_tabs(self):
        """ Creates the Swatches and Recent Colors tabs. """
         # --- Swatches Tab ---
        swatches_widget = QWidget()
        swatches_layout = QVBoxLayout(swatches_widget)

        self.swatch_grid_layout = QGridLayout()
        self.swatch_grid_layout.setSpacing(5)
        swatches_layout.addLayout(self.swatch_grid_layout)

        # Add button to add current color to swatches
        add_swatch_layout = QHBoxLayout()
        self.add_swatch_button = QPushButton()
        self.add_swatch_button.setObjectName("AddSwatchButton")
        try:
            icon = QIcon.fromTheme("add", QIcon.fromTheme("list-add")) # Try theme icons
            if icon.isNull():
                icon = self.style().standardIcon(QStyle.SP_DialogSaveButton) # Fallback
        except:
             icon = self.style().standardIcon(QStyle.SP_DialogSaveButton) # Fallback
        self.add_swatch_button.setIcon(icon)
        self.add_swatch_button.setToolTip("Add current color to swatches")
        self.add_swatch_button.setFixedSize(28, 28)
        self.add_swatch_button.clicked.connect(self._add_current_color_to_swatches)
        add_swatch_layout.addStretch(1)
        add_swatch_layout.addWidget(self.add_swatch_button)
        add_swatch_layout.addStretch(1)
        swatches_layout.addLayout(add_swatch_layout)

        swatches_layout.addStretch(1) # Push grid and button up
        self._populate_swatch_grid() # Fill grid with loaded swatches
        self.tab_widget.addTab(swatches_widget, "Swatches")

        # --- Recent Colors Tab ---
        recent_widget = QWidget()
        recent_layout = QVBoxLayout(recent_widget)
        self.recent_grid_layout = QGridLayout()
        self.recent_grid_layout.setSpacing(5)
        recent_layout.addLayout(self.recent_grid_layout)
        recent_layout.addStretch(1) # Push grid up
        self._populate_recent_grid() # Fill grid with loaded recent colors
        self.tab_widget.addTab(recent_widget, "Recent")

    # --- Swatch/Recent Helper Methods ---

    def _create_swatch_button(self, color):
        """ Creates a clickable button representing a color swatch. """
        button = QPushButton()
        button.setFlat(True) # Looks better as a swatch
        button.setAutoFillBackground(True)
        button.setObjectName("SwatchButton")
        # button.setProperty("cssClass", "SwatchButton") # Might not be needed if using objectName

        # Set background color using stylesheet for better alpha handling
        button.setStyleSheet(f"""
            QPushButton.SwatchButton {{
                background-color: {color.name(QColor.HexArgb)};
                min-width: 30px;
                max-width: 30px;
                min-height: 30px;
                max-height: 30px;
                border: 1px solid #555555;
                border-radius: 4px;
                padding: 1px;
            }}
            QPushButton.SwatchButton:hover {{
                 border: 1px solid #FFFFFF;
            }}
        """)

        # Set tooltip to hex value
        button.setToolTip(color.name(QColor.HexArgb).upper())

        # Connect click to update the main color
        button.clicked.connect(lambda: self.update_controls(color))
        return button

    def _populate_grid(self, grid_layout, colors, max_items, cols=6):
        """ Populates a QGridLayout with color swatch buttons. """
        # Clear existing items in grid
        while grid_layout.count():
            item = grid_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

        row, col = 0, 0
        for i, color_hex in enumerate(colors):
            if i >= max_items: break
            color = QColor(color_hex)
            if color.isValid():
                swatch_button = self._create_swatch_button(color)
                grid_layout.addWidget(swatch_button, row, col)
                col += 1
                if col >= cols:
                    col = 0
                    row += 1

    def _populate_swatch_grid(self):
        self._populate_grid(self.swatch_grid_layout, self._swatches, self.MAX_SWATCHES)

    def _populate_recent_grid(self):
        self._populate_grid(self.recent_grid_layout, self._recent_colors, self.MAX_RECENT_COLORS)

    def _load_colors(self, key, max_items):
        """ Loads color list (hex strings) from QSettings. """
        self._settings.beginGroup(self.SETTINGS_GROUP)
        colors = self._settings.value(key, [], type=list)
        self._settings.endGroup()
        # Ensure items are strings, filter invalid entries if any accidental bad data
        colors = [c for c in colors if isinstance(c, str) and QColor.isValidColor(c)][:max_items]
        return colors

    def _save_colors(self, key, colors):
        """ Saves color list (hex strings) to QSettings. """
        self._settings.beginGroup(self.SETTINGS_GROUP)
        self._settings.setValue(key, colors)
        self._settings.endGroup()

    @pyqtSlot()
    def _add_current_color_to_swatches(self):
        """ Adds the current color to the swatches list and saves. """
        if not self._current_color.isValid(): return

        hex_color = self._current_color.name(QColor.HexArgb).upper()

        # Avoid duplicates
        if hex_color in self._swatches:
            self._swatches.remove(hex_color) # Move to front if exists

        self._swatches.insert(0, hex_color) # Add to beginning

        # Limit size
        self._swatches = self._swatches[:self.MAX_SWATCHES]

        self._save_colors(self.SETTINGS_SWATCHES, self._swatches)
        self._populate_swatch_grid() # Refresh UI

    def _add_color_to_recent(self, color):
        """ Adds a color to the recent list and saves. """
        if not color.isValid(): return

        hex_color = color.name(QColor.HexArgb).upper()

        # Avoid duplicates, move to front if exists
        if hex_color in self._recent_colors:
            self._recent_colors.remove(hex_color)

        self._recent_colors.insert(0, hex_color)

        # Limit size
        self._recent_colors = self._recent_colors[:self.MAX_RECENT_COLORS]

        self._save_colors(self.SETTINGS_RECENT_COLORS, self._recent_colors)
        self._populate_recent_grid() # Refresh UI (might not be visible unless tab is open)


    # --- Control Update Logic ---

    def update_controls(self, color, source=None, initial_update=False):
        """Updates all controls based on the given color. Source indicates caller if needed."""
        if self._updating_controls or not isinstance(color, QColor) or not color.isValid():
            return

        self._updating_controls = True
        self._current_color = QColor(color) # Store the valid color
        self.color_wheel._current_color = self._current_color # Update wheel's knowledge of alpha


        # --- Update Previews ---
        self.update_preview(self._current_color, self._initial_color if initial_update else None)

        # --- Update Color Wheel & Value Slider ---
        if source != "wheel":
            self.color_wheel.set_color(self._current_color)
        if source != "value_slider":
            # Ensure slider updates wheel visuals correctly
            self.value_slider.setValue(self._current_color.value())
            if source != "wheel": # Avoid redundant wheel update if value change came from wheel itself
                 self.color_wheel.set_value(self._current_color.value())


        # --- Update RGB(A) Tab ---
        if source not in ["rgb_slider", "rgb_spinbox"]:
            self.rgb_sliders['red'].setValue(color.red())
            self.rgb_sliders['green'].setValue(color.green())
            self.rgb_sliders['blue'].setValue(color.blue())
            self.rgb_sliders['alpha'].setValue(color.alpha())
            self.rgb_spinboxes['red'].setValue(color.red())
            self.rgb_spinboxes['green'].setValue(color.green())
            self.rgb_spinboxes['blue'].setValue(color.blue())
            self.rgb_spinboxes['alpha'].setValue(color.alpha())

        # --- Update HSV Tab ---
        if source not in ["hsv_slider", "hsv_spinbox"]:
            # Handle hue = -1 for grayscale colors
            hue = color.hue()
            sat = color.saturation()
            val = color.value()

            if hue == -1: hue = self.hsv_sliders['hue'].value() # Keep existing hue if gray

            self.hsv_sliders['hue'].setValue(hue)
            self.hsv_sliders['saturation'].setValue(sat)
            self.hsv_sliders['value'].setValue(val) # This slider is linked to the main Value slider
            self.hsv_spinboxes['hue'].setValue(hue)
            self.hsv_spinboxes['saturation'].setValue(sat)
            self.hsv_spinboxes['value'].setValue(val)


        # --- Update Hex Tab ---
        if source != "hex":
            # Format consistently with alpha
            self.hex_edit.setText(color.name(QColor.HexArgb).upper())

        self._updating_controls = False

    def update_preview(self, new_color, initial_color=None):
        """ Updates the color preview widgets using stylesheets for alpha. """
        if initial_color and initial_color.isValid():
            # Use stylesheet for background to correctly show transparency over checkerboard
            self.preview_current_widget.setStyleSheet(f"#ColorPreviewCurrent {{ background-color: {initial_color.name(QColor.HexArgb)}; }}")

        if new_color and new_color.isValid():
            self.preview_new_widget.setStyleSheet(f"#ColorPreviewNew {{ background-color: {new_color.name(QColor.HexArgb)}; }}")


    # --- Signal Handlers ---

    @pyqtSlot(QColor)
    def _wheel_color_changed(self, color):
        """ Handles color change from the ColorWheel """
        # Wheel only gives H/S/V, keep current Alpha
        alpha = self._current_color.alpha()
        new_color_with_alpha = QColor(color.red(), color.green(), color.blue(), alpha)
        self.update_controls(new_color_with_alpha, source="wheel")

    @pyqtSlot(int)
    def _value_slider_changed(self, value):
        """ Handles change from the Value slider """
        if self._updating_controls: return
        # Update the color wheel's value, which causes it to redraw and emit its color
        self.color_wheel.set_value(value)
        # Also update the HSV tab's value slider/spinbox
        self.hsv_sliders['value'].setValue(value)
        self.hsv_spinboxes['value'].setValue(value)
        # The wheel's colorChanged signal will trigger update_controls


    @pyqtSlot(str, str, int) # model, component, value
    def _slider_changed(self, model, component, value):
        """ Handles value changes from RGB or HSV sliders. """
        if self._updating_controls: return

        # Update corresponding spinbox first to avoid potential signal loop
        spinbox = getattr(self, f"{model}_spinboxes")[component]
        spinbox.blockSignals(True)
        spinbox.setValue(value)
        spinbox.blockSignals(False)

        # Construct new color based on the changed model
        new_color = self._construct_color_from_inputs(model)
        if new_color:
             self.update_controls(new_color, source=f"{model}_slider")


    @pyqtSlot(str, str, int) # model, component, value
    def _spinbox_changed(self, model, component, value):
        """ Handles value changes from RGB or HSV spinboxes. """
        if self._updating_controls: return

        # Update corresponding slider first
        slider = getattr(self, f"{model}_sliders")[component]
        slider.blockSignals(True)
        slider.setValue(value)
        slider.blockSignals(False)

        # Construct new color (same logic as _slider_changed)
        new_color = self._construct_color_from_inputs(model)
        if new_color:
            self.update_controls(new_color, source=f"{model}_spinbox")

    def _construct_color_from_inputs(self, model):
        """ Helper to construct QColor from current RGB or HSV inputs. """
        try:
            if model == "rgb":
                return QColor(
                    self.rgb_spinboxes['red'].value(),
                    self.rgb_spinboxes['green'].value(),
                    self.rgb_spinboxes['blue'].value(),
                    self.rgb_spinboxes['alpha'].value()
                )
            elif model == "hsv":
                 return QColor.fromHsv(
                    self.hsv_spinboxes['hue'].value(),
                    self.hsv_spinboxes['saturation'].value(),
                    self.hsv_spinboxes['value'].value(),
                    self.rgb_spinboxes['alpha'].value() # Get alpha from RGB tab
                )
        except Exception as e:
            print(f"Error constructing color: {e}")
            return None
        return None


    @pyqtSlot(str)
    def hex_changed(self, text):
        """ Handles changes in the Hex input field. """
        if self._updating_controls:
            return

        # Add '#' if missing and potentially valid
        if not text.startswith('#') and len(text) in [3, 4, 6, 8] and all(c in '0123456789ABCDEFabcdef' for c in text):
             text = '#' + text
             # Update the line edit text visually, but block signals briefly
             self.hex_edit.blockSignals(True)
             self.hex_edit.setText(text)
             self.hex_edit.blockSignals(False)


        # Validate and parse
        temp_color = QColor(text)

        if temp_color.isValid():
             # If hex is short (#RGB or #RRGGBB), preserve current alpha
             current_alpha = self._current_color.alpha()
             if len(text) in [4, 7]: # #RGB or #RRGGBB format
                 temp_color.setAlpha(current_alpha)

             self.update_controls(temp_color, source="hex")
        else:
            # Maybe provide visual feedback for invalid hex (e.g., red border on line edit)
            # self.hex_edit.setStyleSheet("border: 1px solid red;") # Example
             pass # Or just ignore invalid input for now

    @pyqtSlot()
    def _reset_color(self):
        """ Resets the color to the initial color. """
        self.update_controls(self._initial_color, source="reset")

    @pyqtSlot()
    def _activate_eyedropper(self):
        """Grabs the color under the mouse cursor anywhere on screen."""
        # CRITICAL: Eyedropper activation start
        print("[Main Window] DEBUG: Activating eyedropper...")
        self.overlay = EyedropperOverlay(self)
        self.overlay.colorSelected.connect(self._handle_eyedropper_color)
        self.overlay.showFullScreen()
        QApplication.setOverrideCursor(Qt.CrossCursor)
        self.hide()

    def _handle_eyedropper_color(self, color):
        """Handle color selection from overlay"""
        # CRITICAL: Signal reception in main window
        print(f"[Main Window] DEBUG: Received color signal: {color.name(QColor.HexRgb)}")
        # CRITICAL: Cursor restoration after overlay closes (should also happen in overlay's closeEvent)
        QApplication.restoreOverrideCursor()
        print("[Main Window] DEBUG: Override cursor restored.")
        self.show()
        if color.isValid():
            # CRITICAL: Handling a valid color
            print("[Main Window] DEBUG: Received color is valid. Updating controls.")
            color.setAlpha(self._current_color.alpha()) # Preserve alpha
            self.update_controls(color, source="eyedropper")
        else:
            # CRITICAL: Handling an invalid color (e.g., from Esc key)
            print("[Main Window] DEBUG: Received invalid color. No update.")

    def _grab_pixel(self, screen):
        """ Helper function to perform the screen grab after a potential delay. """
        try:
            # Grab a tiny pixmap at the cursor position
            pos = QCursor.pos()
            # Ensure coordinates are valid
            screen_geom = screen.geometry()
            grab_x = max(screen_geom.x(), min(pos.x(), screen_geom.right()))
            grab_y = max(screen_geom.y(), min(pos.y(), screen_geom.bottom()))

            pixmap = screen.grabWindow(0, grab_x, grab_y, 1, 1) # Grab 1x1 pixel at cursor

        except Exception as e:
             print(f"Eyedropper screen grab Error: {e}")
             pixmap = QPixmap() # Create null pixmap on error

        # Show the dialog again regardless of grab success
        self.show()
        QApplication.processEvents() # Ensure it's visible

        if not pixmap.isNull():
            image = pixmap.toImage()
            if not image.isNull():
                color = QColor(image.pixel(0, 0))
                if color.isValid():
                    # Keep current alpha setting when using eyedropper
                    current_alpha = self._current_color.alpha()
                    color.setAlpha(current_alpha)
                    self.update_controls(color, source="eyedropper")
                else:
                    print("Eyedropper Error: Invalid color grabbed.")
            else:
                print("Eyedropper Error: Failed to convert pixmap to image.")
        else:
             print("Eyedropper Error: Failed to grab screen pixel (Pixmap is Null).")


    def accept_color(self):
        """ Emits the selected color signal and closes the dialog. """
        self._add_color_to_recent(self._current_color) # Add accepted color to recent list
        self.colorSelected.emit(self._current_color)
        self.accept()

    def selected_color(self):
        """ Returns the finally selected color. """
        return self._current_color

    @staticmethod
    def getColor(initial_color=QColor(255, 255, 255), parent=None):
        """ Static method to show the dialog and get a color. """
        dialog = CustomColorDialog(initial_color, parent)
        result = dialog.exec_()
        if result == QDialog.Accepted:
            return dialog.selected_color()
        else:
            # Return invalid color on cancel, consistent with QColorDialog
            return QColor() # Returns invalid QColor
