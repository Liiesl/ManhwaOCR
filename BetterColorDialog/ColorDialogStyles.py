# --- Main Dialog Stylesheet (Updated) ---
# Style adjustments for new layout might be needed, especially for Hex/Eyedropper container
CUSTOM_COLOR_DIALOG_V2_STYLESHEET = """
QDialog {
    background-color: #2D2D2D;
    color: #FFFFFF;
    border: 1px solid #3A3A3A;
    border-radius: 10px;
    min-width: 550px; /* May need adjustment */
}
QLabel {
    color: #FFFFFF;
    font-size: 13px;
    background: transparent;
    padding-top: 3px; /* Align labels better with controls */
    padding-bottom: 3px;
}
QLineEdit {
    background-color: #3A3A3A;
    color: #FFFFFF;
    border: 1px solid #4A4A4A;
    border-radius: 4px;
    padding: 5px;
    font-size: 13px;
}
QLineEdit:read-only { background-color: #333333; }

/* Horizontal Sliders (RGB/HSV tabs) */
QSlider::groove:horizontal {
    border: 1px solid #3A3A3A;
    height: 8px; /* Reduced height */
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #3A3A3A, stop:1 #444444);
    margin: 2px 0;
    border-radius: 4px;
}
QSlider::handle:horizontal {
    background: #DDDDDD; /* Lighter handle */
    border: 1px solid #555555;
    width: 16px;
    margin: -4px 0; /* Adjust margin for new groove height */
    border-radius: 8px;
}
QSlider::handle:horizontal:hover { background: #EEEEEE; }

QPushButton {
    background-color: #3A3A3A;
    color: #FFFFFF;
    border: none;
    padding: 6px 12px;
    border-radius: 12px;
    font-size: 13px;
    min-width: 60px;
}
QPushButton:hover { background-color: #4A4A4A; }
QPushButton:pressed { background-color: #2A2A2A; }
QPushButton#EyedropperButton { /* Keep specific style */
    min-width: 30px; padding: 5px; border-radius: 5px;
    background-color: #444444; /* Slightly different BG */
}
QPushButton#EyedropperButton:hover { background-color: #555555; }
QPushButton#AddSwatchButton {
    min-width: 30px; padding: 5px; border-radius: 5px; /* Smaller radius */
}
QPushButton#ResetButton { background-color: #553333; }
QPushButton#ResetButton:hover { background-color: #6F4040; }

/* Color Previews */
#ColorPreviewCurrent, #ColorPreviewNew {
    border: 1px solid #555555;
    border-radius: 4px;
    min-height: 40px;
    min-width: 80px;
}

/* Generic Tab Widget Styling */
QTabWidget::pane {
    border: 1px solid #3A3A3A; border-top: none;
    background-color: #333333;
    border-bottom-left-radius: 5px; border-bottom-right-radius: 5px;
    padding: 10px;
}
QTabBar::tab {
    background: #3A3A3A; color: #BBBBBB;
    border: 1px solid #3A3A3A; border-bottom: none;
    padding: 8px 15px; margin-right: 2px;
    border-top-left-radius: 5px; border-top-right-radius: 5px;
}
QTabBar::tab:selected { background: #333333; color: #FFFFFF; border-bottom: 1px solid #333333; }
QTabBar::tab:hover { background: #4A4A4A; }

/* Specific Styling for Input Tabs */
#InputTabWidget::pane {
     padding: 10px 10px 5px 10px;
}
/* Specific Styling for Swatch Tabs */
#SwatchTabWidget::pane {
     padding: 10px 10px 10px 10px;
     min-height: 100px; /* Ensure it has some minimum height */
}
#SwatchTabWidget {
    margin-top: 10px; /* Space above swatch tabs */
}


/* Swatch Button */
QPushButton.SwatchButton { /* Use class selector */
    min-width: 30px; max-width: 30px;
    min-height: 30px; max-height: 30px;
    border: 1px solid #555555;
    border-radius: 4px;
    padding: 1px;
    /* Base gradient for checkerboard effect if color has alpha */
    background-color: qlineargradient(spread:pad, x1:0, y1:0, x2:1, y2:1, stop:0 rgba(255, 255, 255, 50), stop:1 rgba(0, 0, 0, 50));
}
QPushButton.SwatchButton:hover { border: 1px solid #FFFFFF; }

/* SpinBoxes */
QSpinBox {
    background-color: #3A3A3A; color: #FFFFFF;
    border: 1px solid #4A4A4A; border-radius: 4px;
    padding: 3px 5px; min-width: 45px;
}
QSpinBox::up-button, QSpinBox::down-button {
    subcontrol-origin: border; background-color: #4A4A4A; border-radius: 2px;
}
QSpinBox::up-button { subcontrol-position: top right; width: 15px; }
QSpinBox::down-button { subcontrol-position: bottom right; width: 15px; }
QSpinBox::up-button:hover, QSpinBox::down-button:hover { background-color: #5A5A5A; }
QSpinBox::up-arrow, QSpinBox::down-arrow { width: 7px; height: 7px; }

/* Picker Widgets Styling */
ColorSquare {
    border: 1px solid #4A4A4A;
}
HueRing {
    /* No specific border needed */
}
#PickerContainer { /* Style the container if needed */
    background: transparent;
}

/* Hex Input Area Container */
#HexEyedropperContainer {
    background-color: #333333; /* Match tab pane background */
    border: 1px solid #3A3A3A;
    border-radius: 5px;
    padding: 5px 10px; /* Adjusted padding */
    margin-top: 8px; /* Space between input tabs and this area */
}
/* Adjust label padding inside the hex container if needed */
#HexEyedropperContainer QLabel {
    padding-top: 0px;
    padding-bottom: 0px;
    color: #BBBBBB; /* Slightly dimmer label */
}
/* Ensure LineEdit background matches container */
#HexEyedropperContainer QLineEdit {
     background-color: #3A3A3A; /* Match other inputs */
}

"""