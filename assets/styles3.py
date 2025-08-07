TEXT_BOX_STYLE_PANEL_STYLE = """
            #TextBoxStylePanel {
                background-color: #2A2A2A; 
                border-left: 1px solid #3A3A3A;
                border-right: 1px solid #1A1A1A;
            }
            #panelTitle {
                color: #FFFFFF;
                font-size: 20px;
                font-weight: bold;
            }
            #headerDivider {
                border-color: #3A3A3A;
            }
            #styleScrollArea {
                 background-color: transparent;
            }
            #styleGroup {
                color: #FFFFFF;
                font-weight: bold;
                border: 1px solid #3A3A3A;
                border-radius: 10px;
                margin-top: 15px;
                padding-top: 15px;
                font-size: 20px;
            }
            #styleGroup::title {
                subcontrol-origin: margin;
                subcontrol-position: top center;
                padding: 0 8px;
                background-color: #2A2A2A;
            }
            #buttonContainer {
                background-color: #2A2A2A;
            }
            #resetButton, #applyButton {
                 background-color: #3A3A3A;
                 color: #FFFFFF;
                 border: none;
                 padding: 10px;
                 border-radius: 20px;
                 font-size: 20px;
            }
            #addPresetButton { 
                background-color: #333; 
                border: 1px solid #555; 
                border-radius: 3px; 
            }
            #addPresetButton:hover { 
                background-color: #444; 
                border-color: #666; 
            }
        """

SHAPE_PANEL_STYLE = """
            #ShapeStylePanel { background-color: transparent; }
            QLabel { color: #EAEAEA; font-size: 13px; font-family: "Segoe UI"; }
            QLabel#mainLabel {
                color: #EAEAEA; font-weight: 600; font-size: 13px;
                margin-top: 5px; margin-bottom: 4px; padding-left: 2px;
            }
            QLabel#tinyLabel {
                color: #B0B1B2; font-size: 11px; font-weight: 500; margin-bottom: 3px;
            }
            QPushButton#colorButton {
                border: 1px solid #60666E; border-radius: 3px;
            }
            QPushButton#colorButton:hover { border: 1px solid #70777F; }
            QComboBox, QSpinBox {
                background-color: #3A3A3A; color: #FFFFFF; border: 1px solid #4A4A4A;
                padding: 4px; border-radius: 4px; font-size: 13px; font-family: "Segoe UI";
            }
            QSpinBox { padding-right: 0px; }
            QComboBox::drop-down { border: none; width: 20px; }
            QComboBox QAbstractItemView {
                background-color: #3A3A3A; color: #FFFFFF;
                selection-background-color: #0078D7; font-size: 13px; outline: 0px;
            }
            QSpinBox::up-button, QSpinBox::down-button {
                subcontrol-origin: border; width: 16px; border-left: 1px solid #4A4A4A;
            }
            QSpinBox::up-arrow, QSpinBox::down-arrow { width: 10px; height: 10px; }
        """
TYPOGRAPHY_PANEL_STYLE = """
            #TypographyStylePanel { background-color: transparent; }
            QLabel { color: #EAEAEA; font-size: 13px; font-family: "Segoe UI"; }
            QLabel#mainLabel {
                color: #EAEAEA; font-weight: 600; font-size: 13px;
                margin-top: 5px; margin-bottom: 4px; padding-left: 2px;
            }
            QLabel#tinyLabel {
                color: #B0B1B2; font-size: 11px; font-weight: 500; margin-bottom: 3px;
            }
            QPushButton#colorButton {
                border: 1px solid #60666E; border-radius: 3px;
            }
            QPushButton#colorButton:hover { border: 1px solid #70777F; }
            QComboBox, QSpinBox {
                background-color: #3A3A3A; color: #FFFFFF; border: 1px solid #4A4A4A;
                padding: 4px; border-radius: 4px; font-size: 13px; font-family: "Segoe UI";
            }
            QSpinBox { padding-right: 0px; }
            QComboBox::drop-down { border: none; width: 20px; }
            QComboBox QAbstractItemView {
                background-color: #3A3A3A; color: #FFFFFF;
                selection-background-color: #0078D7; font-size: 13px; outline: 0px;
            }
            QSpinBox::up-button, QSpinBox::down-button {
                subcontrol-origin: border; width: 16px; border-left: 1px solid #4A4A4A;
            }
            QSpinBox::up-arrow, QSpinBox::down-arrow { width: 10px; height: 10px; }
            QCheckBox { spacing: 5px; color: #B0B1B2; font-size: 11px; }
            QCheckBox::indicator { width: 18px; height: 18px; }
            
            QPushButton#alignButton, QPushButton#styleToggleButton {
                border: 1px solid #555; background-color: transparent;
                padding: 5px; margin: 0px; border-radius: 4px;
            }
            QPushButton#alignButton:checked, QPushButton#styleToggleButton:checked {
                background-color: #0078D7; border-color: #005A9E;
            }
            QPushButton#alignButton:hover, QPushButton#styleToggleButton:hover {
                border-color: #777;
            }
            QFrame#gradientGroup {
                background-color: #2F2F2F; border-radius: 4px; padding: 0 8px 8px 8px;
            }
            """