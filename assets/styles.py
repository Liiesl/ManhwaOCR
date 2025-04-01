# Move these to app/styles.py
COLORS = {
    "background": "#1E1E1E",
    "surface": "#2D2D2D",
    "primary": "#3A3A3A",
    "secondary": "#4A4A4A",
    "accent": "#007ACC",
    "text": "#FFFFFF"
}

MAIN_STYLESHEET = """
            /* General background color */
            QMainWindow, QWidget {
                background-color: #1A1A1A;
                color: #FFFFFF;
                font-size: 20px;
            }
            /* Buttons style */
            QPushButton {
                background-color: #3A3A3A;
                color: #FFFFFF;
                border: none;
                padding: 10px;
                border-radius: 20px; 
            }
            QPushButton:hover {
                background-color: #4A4A4A;
            }
            QPushButton:pressed {
                background-color: #2A2A2A;
            }
                           
            /* Table styling */
            QTableWidget {
                background-color: #2D2D2D;
                gridline-color: "#3A3A3A";
                border-radius: 50px;
            }
            QHeaderView::section {
                background-color: "#3A3A3A";
                padding: 12px;
                border: none;
            }
            QTableWidget::item {
                padding: 2px;
            }
            QTableWidget::item.column-6 {  /* Target the 7th column (index 6) */
                background-color: transparent;
                border: none;
            }
            
            /* Ensure table buttons use the same style */
            QTableWidget QPushButton {
                background-color: #3A3A3A;
                color: #FFFFFF;
                border: none;
                padding: 10px;
                border-radius: 20px;
            }
            QTableWidget QPushButton:hover {
                background-color: #4A4A4A;
            }
            QTableWidget QPushButton:pressed {
                background-color: #2A2A2A;
            }
                           
            /* Scroll area style */
            QScrollArea {
                border: 20px solid #2A2A2A; /* Solid color border */
                border-top-right-radius: 50px; /* Rounded top-right corner */
                background-color: #2A2A2A; /* Background color */
            }
                           
            QScrollArea > QWidget > QWidget {  /* Target the viewport */
                background: transparent;
            }
                           
            /* Progress bar style */
            QProgressBar {
                background-color: #2A2A2A;
                color: #FFFFFF;
                border: 1px solid #3A3A3A;
                border-radius: 5px;
                text-align: center;
            }
            QProgressBar::chunk {
                background-color: #4A4A4A;
                width: 10px;
            }
            
            /* Tab Widget style */
            QTabWidget {
                background-color: #1A1A1A;
                border: none;
            }
            QTabWidget::pane {
                border: 1px solid #3A3A3A;
                border-radius: 10px;
                background-color: #2D2D2D;
            }
            QTabBar::tab {
                background-color: #3A3A3A;
                color: #FFFFFF;
                padding: 10px;
                border: none;
                border-radius: 5px;
            }
            QTabBar::tab:selected {
                background-color: #4A4A4A;
                margin-bottom: -1px; /* Ensure selected tab appears above the pane border */
            }
            QTabBar::tab:!selected {
                margin-top: 2px; /* Add some spacing between unselected tabs and the pane */
            }

            QSplitter {
                width: 30px;
            }
            
            QTableWidget {
                background-color: #1A1A1A;
            }
            /* Scroll Bar Styling */
            QScrollBar:vertical {
                background-color: #1A1A1A;
                width: 15px;
                margin: 0px;
                border-radius: 7px;
            }

            QScrollBar::handle:vertical {
                background-color: #4A4A4A;
                min-height: 30px;
                border-radius: 7px;
            }

            QScrollBar::handle:vertical:hover {
                background-color: #5A5A5A;
            }

            QScrollBar::handle:vertical:pressed {
                background-color: #007ACC;
            }

            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }

            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
                background: none;
            }

            /* Horizontal Scroll Bar */
            QScrollBar:horizontal {
                background-color: #1A1A1A;
                height: 15px;
                margin: 0px;
                border-radius: 7px;
            }

            QScrollBar::handle:horizontal {
                background-color: #4A4A4A;
                min-width: 30px;
                border-radius: 7px;
            }

            QScrollBar::handle:horizontal:hover {
                background-color: #5A5A5A;
            }

            QScrollBar::handle:horizontal:pressed {
                background-color: #007ACC;
            }

            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
                width: 0px;
            }

            QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {
                background: none;
            }
        """

IV_BUTTON_STYLES = """
            QPushButton {
                background-color: #3A3A3A;
                border: none;
                border-radius: 25px; 
            }
            QPushButton:hover {
                background-color: #4A4A4A;
            }
            QPushButton:pressed {
                background-color: #2A2A2A;
            }
        """

ADVANCED_CHECK_STYLES = """
            QCheckBox {
                color: #FFFFFF;
                font-size: 16px;
                spacing: 12px;
                padding: 4px;
            }
            QCheckBox::indicator {
                width: 22px;
                height: 22px;
                border-radius: 4px;
            }
            QCheckBox::indicator:unchecked {
                border: 2px solid #3A3A3A;
                background-color: #2A2A2A;
            }
            QCheckBox::indicator:unchecked:hover {
                border: 2px solid #4A4A4A;
                background-color: #333333;
            }
            QCheckBox::indicator:checked {
                border: 2px solid #007ACC;
                background-color: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #0088EE, stop:1 #007ACC);
                image: url(data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSIxNCIgaGVpZ2h0PSIxNCIgdmlld0JveD0iMCAwIDI0IDI0IiBmaWxsPSJub25lIiBzdHJva2U9IiNGRkZGRkYiIHN0cm9rZS13aWR0aD0iMyIgc3Ryb2tlLWxpbmVjYXA9InJvdW5kIiBzdHJva2UtbGluZWpvaW49InJvdW5kIj48cG9seWxpbmUgcG9pbnRzPSIyMCA2IDkgMTcgNCAxMiI+PC9wb2x5bGluZT48L3N2Zz4=);
            }
            QCheckBox::indicator:checked:hover {
                border: 2px solid #0088EE;
                background-color: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #0099FF, stop:1 #0088EE);
            }
            QCheckBox:disabled {
                color: #666666;
            }
            QCheckBox::indicator:disabled {
                border: 2px solid #444444;
                background-color: #333333;
            }
        """

RIGHT_WIDGET_STYLES = """
            QWidget {
                background-color: #2A2A2A;
                border: none;
                border-top-left-radius: 50px; /* Rounded top-left corner */
            }
            /* Buttons style */
            QPushButton {
                background-color: #3A3A3A;
                color: #FFFFFF;
                border: none;
                padding: 10px;
                border-radius: 20px; 
            }
            QPushButton:hover {
                background-color: #4A4A4A;
            }
            QPushButton:pressed {
                background-color: #2A2A2A;
            }
        """

SIMPLE_VIEW_STYLES = """
                QFrame {
                    background-color: #3A3A3A;
                    border-radius: 35px;
                    padding: 10px;
                    margin: 0;
                }
                QTextEdit {
                    color: white;
                    font-size: 20px;
                    background-color: transparent;
                    border: 1px solid #4A4A4A;
                    border-radius: 25px;
                    padding: 5px;
                }
                QTextEdit:hover {
                    border: 1px solid #007ACC;
                }
                QTextEdit:focus {
                    border: 2px solid #007ACC;
                }
                QPushButton {
                    background-color: #3A3A3A;
                    border: none;
                    border-radius: 34px;
                }
                QPushButton:hover {
                    background-color: #4A4A4A;
                }
                QPushButton:pressed {
                    background-color: #2A2A2A;
                }
            """

DELETE_ROW_STYLES = f"""
                QMessageBox {{
                    background-color: {COLORS['background']};
                    color: {COLORS['text']};
                    font-size: 16px;
                }}
                QLabel {{
                    color: {COLORS['text']};
                }}
                QCheckBox {{
                    color: {COLORS['text']};
                    spacing: 8px;
                }}
                QCheckBox::indicator {{
                    width: 18px;
                    height: 18px;
                }}
                QPushButton {{
                    background-color: {COLORS['primary']};
                    color: {COLORS['text']};
                    min-width: 80px;
                    padding: 8px;
                    border-radius: 4px;
                }}
                QPushButton:hover {{
                    background-color: {COLORS['secondary']};
                }}
            """

HOME_STYLES = """
            QMainWindow, QWidget {
                background-color: #1a1a1a;
                color: white;
            }
            QPushButton {
                background-color: #3E3E3E;
                color: white;
                border-radius: 15px;
                padding: 10px 15px;
                border: none;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #4f4f4f;
            }
            QScrollArea {
                background-color: transparent;
                border: none;
            }
            QScrollBar:vertical {
                background: #1a1a1a;
                width: 10px;
                margin: 0px;
            }
            QScrollBar::handle:vertical {
                background: #444444;
                min-height: 20px;
                border-radius: 5px;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
        """

HOME_LEFT_LAYOUT_STYLES = """
                            QWidget {
                                background-color: #2B2B2B;
                                padding: 20px;
                                border: none;
                                border-top-right-radius: 20px;
                            }
                            QPushButton {
                                background-color: #3E3E3E;
                                color: white;
                                border-radius: 15px;
                                padding: 10px 15px;
                                border: none;
                                font-size: 14px;
                                min-height: 40px;
                            }
                            QPushButton:hover {
                                background-color: #4f4f4f;
                            }
                        """

NEW_PROJECT_STYLES = """
            QDialog {
                background-color: #2D2D2D;
                color: #FFFFFF;
                font-size: 14px;
            }
            QLineEdit {
                background-color: #3A3A3A;
                padding: 8px;
                border: 1px solid #4A4A4A;
                border-radius: 4px;
                margin: 5px 0;
            }
            QPushButton {
                background-color: #4A4A4A;
                color: #FFFFFF;
                padding: 8px 16px;
                border: none;
                border-radius: 4px;
                min-width: 80px;
            }
            QPushButton:hover {
                background-color: #5A5A5A;
            }
            QLabel {
                margin-top: 10px;
                color: #CCCCCC;
                background-color: none;
            }
            QComboBox {
                background-color: #3A3A3A;
                color: #FFFFFF;
                padding: 5px;
                border: 1px solid #4A4A4A;
                border-radius: 4px;
            }
            QComboBox::drop-down {
                border: none;
            }
            QComboBox QAbstractItemView {
                background-color: #3A3A3A;
                color: #FFFFFF;
                selection-background-color: #5A5A5A;
            }
        """

WFWF_STYLES = """
            QDialog {
                background-color: #2D2D2D;
                color: #FFFFFF;
                font-size: 14px;
            }
            QLineEdit {
                background-color: #3A3A3A;
                padding: 8px;
                border: 1px solid #4A4A4A;
                border-radius: 4px;
                margin: 5px 0;
            }
            QLabel {
                color: #CCCCCC;
            }
            QListWidget {
                background-color: #3A3A3A;
                color: #FFFFFF;
                border-radius: 4px;
                padding: 5px;
            }
            QPushButton {
                background-color: #4A4A4A;
                color: #FFFFFF;
                padding: 8px 16px;
                border: none;
                border-radius: 4px;
                min-width: 80px;
            }
            QPushButton:hover {
                background-color: #5A5A5A;
            }
            QPushButton:disabled {
                background-color: #3A3A3A;
                color: #999999;
            }
            QProgressBar {
                border: 1px solid #4A4A4A;
                border-radius: 4px;
                text-align: center;
                height: 20px;
            }
            QProgressBar::chunk {
                background-color: #5294e2;
                width: 1px;
            }
            QStatusBar {
                color: #CCCCCC;
            }
        """

PROGRESS_STYLES = """QProgressBar {...}"""