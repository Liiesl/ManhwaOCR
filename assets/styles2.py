
from assets.styles import COLORS

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
    # You can add more style groups here later, e.g., 'main_window', 'dialogs'
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
