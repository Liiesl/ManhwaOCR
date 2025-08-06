from assets.styles import COLORS

MENU_STYLES = f"""
            QWidget {{
                background-color: {COLORS['primary']};
                border: 1px solid {COLORS['border']};
                border-radius: 5px;
                padding: 5px;
            }}
            QPushButton {{
                background-color: {COLORS['secondary']};
                color: {COLORS['text']};
                border: 1px solid {COLORS['border']};
                padding: 10px 15px;
                font-size: 14px;
                text-align: left;
                border-radius: 4px;
                margin: 2px;
            }}
            QPushButton:hover {{
                background-color: {COLORS['button_hover_bg']};
                border: 1px solid {COLORS['border']};
            }}
            QPushButton:pressed {{
                background-color: {COLORS['button_pressed']};
            }}
        """

CHROMESTYLES = {
    # Styles for the CustomTitleBar widget
    'title_bar':{
        'title': f"""
            background-color: {COLORS['background']};
            color: {COLORS['text']};
            font-weight: bold;
            padding-left: 10px;
        """,
        'button_common': """
            QPushButton {
                background-color: transparent;
                border: none;
            }
        """,
        'button_close_hover': f"QPushButton:hover {{ background-color: {COLORS['error']}; }}",
        'button_generic_hover': f"QPushButton:hover {{ background-color: {COLORS['button_hover_bg']}; }}",
        'button_maximize_hover': f"QPushButton:hover {{ background-color: {COLORS['button_hover_bg']}; }}",
        'button_minimize_hover': f"QPushButton:hover {{ background-color: {COLORS['button_hover_bg']}; }}",
    },
}

MANUALOCR_STYLES = """
    #ManualOCROverlay { background-color: rgba(0, 0, 0, 0.7); border-radius: 5px; }
    QPushButton { background-color: #4CAF50; border: none; color: white; padding: 5px 10px; text-align: center; font-size: 14px; margin: 2px; border-radius: 3px; }
    QPushButton:hover { background-color: #45a049; }
    QPushButton#CancelButton { background-color: #f44336; }
    QPushButton#CancelButton:hover { background-color: #da190b; }
    QPushButton#ResetButton { background-color: #ff9800; }
    QPushButton#ResetButton:hover { background-color: #e68a00; }
    QLabel { color: white; font-size: 12px; }
    """