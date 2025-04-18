# --- START OF FILE custom_bubble.py ---

import os
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QLabel, QComboBox, QPushButton, QSlider, QColorDialog, QFrame,
                             QGridLayout, QCheckBox, QSpinBox, QGroupBox, QFontComboBox, QHBoxLayout, QScrollArea,
                             QSpacerItem, QSizePolicy)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QColor, QFont, QFontDatabase, QLinearGradient
import qtawesome as qta
# Assuming this exists and contains the base CSS
from assets.styles import TEXT_BOX_STYLE_PANEL_STYLESHEET, DEFAULT_GRADIENT

class TextBoxStylePanel(QWidget):
    """
    A panel for customizing the appearance of a selected TextBoxItem, including gradients with midpoints.
    """
    style_changed = pyqtSignal(dict)

    def __init__(self, parent=None, default_style=None):
        super().__init__(parent)
        self.setObjectName("TextBoxStylePanel")
        self.setMinimumWidth(300)
        self._original_default_style = default_style if default_style else {}
        self._default_style = self._ensure_gradient_defaults(self._original_default_style)

        self.init_ui()
        self.selected_text_box_info = None
        self._updating_controls = False
        self.selected_style_info = None
        self.update_style_panel(self._default_style) # Apply defaults initially
        # self.hide() # Hide until needed

    def _ensure_gradient_defaults(self, style_dict):
        """Ensures a style dictionary has default gradient fields including integer midpoint."""
        style = style_dict.copy() if style_dict else {}
        # Fill defaults
        if 'fill_type' not in style: style['fill_type'] = 'solid'
        if 'bg_color' not in style: style['bg_color'] = '#ffffffff'
        if 'bg_gradient' not in style: style['bg_gradient'] = {}
        # Ensure all keys exist in bg_gradient, using integer midpoint
        style['bg_gradient'] = {**DEFAULT_GRADIENT, **style['bg_gradient']}

        # Text defaults
        if 'text_color_type' not in style: style['text_color_type'] = 'solid'
        if 'text_color' not in style: style['text_color'] = '#ff000000'
        if 'text_gradient' not in style: style['text_gradient'] = {}
        # Ensure all keys exist in text_gradient, using integer midpoint
        style['text_gradient'] = {**DEFAULT_GRADIENT, **style['text_gradient']}

        # --- Ensure colors are strings ---
        if isinstance(style.get('bg_color'), QColor): style['bg_color'] = style['bg_color'].name(QColor.HexArgb)
        if isinstance(style.get('text_color'), QColor): style['text_color'] = style['text_color'].name(QColor.HexArgb)
        if isinstance(style['bg_gradient'].get('color1'), QColor): style['bg_gradient']['color1'] = style['bg_gradient']['color1'].name(QColor.HexArgb)
        if isinstance(style['bg_gradient'].get('color2'), QColor): style['bg_gradient']['color2'] = style['bg_gradient']['color2'].name(QColor.HexArgb)
        if isinstance(style['text_gradient'].get('color1'), QColor): style['text_gradient']['color1'] = style['text_gradient']['color1'].name(QColor.HexArgb)
        if isinstance(style['text_gradient'].get('color2'), QColor): style['text_gradient']['color2'] = style['text_gradient']['color2'].name(QColor.HexArgb)

        # Ensure midpoint is int
        if 'midpoint' in style['bg_gradient']: style['bg_gradient']['midpoint'] = int(style['bg_gradient']['midpoint'])
        if 'midpoint' in style['text_gradient']: style['text_gradient']['midpoint'] = int(style['text_gradient']['midpoint'])

        return style

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(10)
        main_layout.setAlignment(Qt.AlignTop)

        # --- Header ---
        header_layout = QHBoxLayout()
        title_label = QLabel("Text Box Styles")
        title_label.setObjectName("panelTitle")
        header_layout.addWidget(title_label)
        main_layout.addLayout(header_layout)
        header_divider = QFrame()
        header_divider.setObjectName("headerDivider")
        header_divider.setFrameShape(QFrame.HLine)
        header_divider.setFrameShadow(QFrame.Plain)
        main_layout.addWidget(header_divider)

        # --- Scroll Area Setup ---
        scroll_area = QScrollArea()
        scroll_area.setObjectName("styleScrollArea")
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.NoFrame)
        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)
        scroll_layout.setContentsMargins(0, 5, 5, 5)
        scroll_layout.setSpacing(12)

        # --- Shape Group ---
        # ... (Shape group remains the same) ...
        shape_group = QGroupBox("Shape")
        shape_group.setObjectName("styleGroup")
        shape_layout = QVBoxLayout(shape_group)
        shape_layout.setContentsMargins(10, 15, 10, 10)
        shape_layout.setSpacing(8)
        type_layout = QHBoxLayout()
        bubble_type_label = QLabel("Type:")
        type_layout.addWidget(bubble_type_label, 1)
        self.combo_bubble_type = QComboBox()
        self.combo_bubble_type.setObjectName("styleCombo")
        self.combo_bubble_type.addItems(["Rectangle", "Rounded Rectangle", "Ellipse", "Speech Bubble"])
        self.combo_bubble_type.currentIndexChanged.connect(self.style_changed_handler)
        type_layout.addWidget(self.combo_bubble_type, 2)
        shape_layout.addLayout(type_layout)
        radius_layout = QHBoxLayout()
        corner_radius_label = QLabel("Corner Radius:")
        radius_layout.addWidget(corner_radius_label, 1)
        self.spin_corner_radius = QSpinBox()
        self.spin_corner_radius.setObjectName("styleSpinBox")
        self.spin_corner_radius.setRange(0, 100)
        self.spin_corner_radius.setValue(50)
        self.spin_corner_radius.valueChanged.connect(self.style_changed_handler)
        radius_layout.addWidget(self.spin_corner_radius, 2)
        shape_layout.addLayout(radius_layout)
        scroll_layout.addWidget(shape_group)


        # --- Fill & Stroke Group ---
        color_group = QGroupBox("Fill & Stroke")
        color_group.setObjectName("styleGroup")
        color_layout = QVBoxLayout(color_group)
        color_layout.setContentsMargins(10, 15, 10, 10)
        color_layout.setSpacing(8)

        # Fill Type
        fill_type_layout = QHBoxLayout()
        fill_type_label = QLabel("Fill Type:")
        fill_type_layout.addWidget(fill_type_label, 1)
        self.combo_fill_type = QComboBox()
        self.combo_fill_type.setObjectName("styleCombo")
        self.combo_fill_type.addItems(["Solid", "Linear Gradient"])
        self.combo_fill_type.currentIndexChanged.connect(self._toggle_fill_gradient_controls)
        self.combo_fill_type.currentIndexChanged.connect(self.style_changed_handler)
        fill_type_layout.addWidget(self.combo_fill_type, 2)
        color_layout.addLayout(fill_type_layout)

        # Solid Fill Color
        self.solid_fill_layout = QHBoxLayout()
        bg_color_label = QLabel("Fill Color:")
        self.solid_fill_layout.addWidget(bg_color_label, 1)
        self.btn_bg_color = QPushButton("")
        self.btn_bg_color.setObjectName("colorButton")
        self.btn_bg_color.setFixedSize(32, 24)
        self.btn_bg_color.clicked.connect(lambda: self.choose_color(self.btn_bg_color))
        self.solid_fill_layout.addWidget(self.btn_bg_color, 2)
        color_layout.addLayout(self.solid_fill_layout)

        # Gradient Fill Controls
        self.gradient_fill_group = QWidget()
        gradient_fill_layout = QVBoxLayout(self.gradient_fill_group)
        gradient_fill_layout.setContentsMargins(0, 5, 0, 0)
        gradient_fill_layout.setSpacing(5)

        bg_grad_col1_layout = QHBoxLayout()
        bg_grad_col1_label = QLabel("  Start:")
        bg_grad_col1_layout.addWidget(bg_grad_col1_label, 1)
        self.btn_bg_gradient_color1 = QPushButton("")
        self.btn_bg_gradient_color1.setObjectName("colorButton")
        self.btn_bg_gradient_color1.setFixedSize(32, 24)
        self.btn_bg_gradient_color1.clicked.connect(lambda: self.choose_color(self.btn_bg_gradient_color1))
        bg_grad_col1_layout.addWidget(self.btn_bg_gradient_color1, 2)
        gradient_fill_layout.addLayout(bg_grad_col1_layout)

        bg_grad_col2_layout = QHBoxLayout()
        bg_grad_col2_label = QLabel("  End:")
        bg_grad_col2_layout.addWidget(bg_grad_col2_label, 1)
        self.btn_bg_gradient_color2 = QPushButton("")
        self.btn_bg_gradient_color2.setObjectName("colorButton")
        self.btn_bg_gradient_color2.setFixedSize(32, 24)
        self.btn_bg_gradient_color2.clicked.connect(lambda: self.choose_color(self.btn_bg_gradient_color2))
        bg_grad_col2_layout.addWidget(self.btn_bg_gradient_color2, 2)
        gradient_fill_layout.addLayout(bg_grad_col2_layout)

        # --- Midpoint Control for Fill ---
        bg_grad_mid_layout = QHBoxLayout()
        bg_grad_mid_label = QLabel("  Midpoint (%):")
        bg_grad_mid_layout.addWidget(bg_grad_mid_label, 1)
        self.spin_bg_gradient_midpoint = QSpinBox()
        self.spin_bg_gradient_midpoint.setObjectName("gradientMidpointSpinBox") # Style separately if needed
        self.spin_bg_gradient_midpoint.setRange(0, 100)
        self.spin_bg_gradient_midpoint.setValue(50) # Default midpoint
        self.spin_bg_gradient_midpoint.setSuffix("%")
        self.spin_bg_gradient_midpoint.valueChanged.connect(self.style_changed_handler)
        bg_grad_mid_layout.addWidget(self.spin_bg_gradient_midpoint, 2)
        gradient_fill_layout.addLayout(bg_grad_mid_layout)
        # --- End Midpoint Control ---

        bg_grad_dir_layout = QHBoxLayout()
        bg_grad_dir_label = QLabel("  Direction:")
        bg_grad_dir_layout.addWidget(bg_grad_dir_label, 1)
        self.combo_bg_gradient_direction = QComboBox()
        self.combo_bg_gradient_direction.setObjectName("styleCombo")
        # --- Updated Direction Names ---
        self.combo_bg_gradient_direction.addItems([
            "Horizontal (L>R)",
            "Vertical (T>B)",
            "Diagonal (TL>BR)", # TopLeft to BottomRight
            "Diagonal (BL>TR)"  # BottomLeft to TopRight
        ])
        # --- End Updated Names ---
        self.combo_bg_gradient_direction.currentIndexChanged.connect(self.style_changed_handler)
        bg_grad_dir_layout.addWidget(self.combo_bg_gradient_direction, 2)
        gradient_fill_layout.addLayout(bg_grad_dir_layout)

        color_layout.addWidget(self.gradient_fill_group)

        # Border Width & Color
        # ... (Border controls remain the same) ...
        border_layout = QHBoxLayout()
        border_color_label = QLabel("Stroke:")
        border_layout.addWidget(border_color_label, 1)
        self.spin_border_width = QSpinBox()
        self.spin_border_width.setObjectName("borderWidthSpinner")
        self.spin_border_width.setRange(0, 10)
        self.spin_border_width.setValue(1)
        self.spin_border_width.valueChanged.connect(self.style_changed_handler)
        border_layout.addWidget(self.spin_border_width)
        self.btn_border_color = QPushButton("")
        self.btn_border_color.setObjectName("colorButton")
        self.btn_border_color.setFixedSize(32, 24)
        self.btn_border_color.clicked.connect(lambda: self.choose_color(self.btn_border_color))
        border_layout.addWidget(self.btn_border_color)
        color_layout.addLayout(border_layout)

        scroll_layout.addWidget(color_group)

        # --- Typography Group ---
        font_group = QGroupBox("Typography")
        font_group.setObjectName("styleGroup")
        font_layout = QVBoxLayout(font_group)
        font_layout.setContentsMargins(10, 15, 10, 10)
        font_layout.setSpacing(8)

        # Text Color Type
        text_color_type_layout = QHBoxLayout()
        text_color_type_label = QLabel("Text Color Type:")
        text_color_type_layout.addWidget(text_color_type_label, 1)
        self.combo_text_color_type = QComboBox()
        self.combo_text_color_type.setObjectName("styleCombo")
        self.combo_text_color_type.addItems(["Solid", "Linear Gradient"])
        self.combo_text_color_type.currentIndexChanged.connect(self._toggle_text_gradient_controls)
        self.combo_text_color_type.currentIndexChanged.connect(self.style_changed_handler)
        text_color_type_layout.addWidget(self.combo_text_color_type, 2)
        font_layout.addLayout(text_color_type_layout)

        # Solid Text Color
        self.solid_text_color_layout = QHBoxLayout()
        text_color_label = QLabel("Text Color:")
        self.solid_text_color_layout.addWidget(text_color_label, 1)
        self.btn_text_color = QPushButton("")
        self.btn_text_color.setObjectName("colorButton")
        self.btn_text_color.setFixedSize(32, 24)
        self.btn_text_color.clicked.connect(lambda: self.choose_color(self.btn_text_color))
        self.solid_text_color_layout.addWidget(self.btn_text_color, 2)
        font_layout.addLayout(self.solid_text_color_layout)

        # Gradient Text Controls
        self.gradient_text_group = QWidget()
        gradient_text_layout = QVBoxLayout(self.gradient_text_group)
        gradient_text_layout.setContentsMargins(0, 5, 0, 0)
        gradient_text_layout.setSpacing(5)

        text_grad_col1_layout = QHBoxLayout()
        text_grad_col1_label = QLabel("  Start:")
        text_grad_col1_layout.addWidget(text_grad_col1_label, 1)
        self.btn_text_gradient_color1 = QPushButton("")
        self.btn_text_gradient_color1.setObjectName("colorButton")
        self.btn_text_gradient_color1.setFixedSize(32, 24)
        self.btn_text_gradient_color1.clicked.connect(lambda: self.choose_color(self.btn_text_gradient_color1))
        text_grad_col1_layout.addWidget(self.btn_text_gradient_color1, 2)
        gradient_text_layout.addLayout(text_grad_col1_layout)

        text_grad_col2_layout = QHBoxLayout()
        text_grad_col2_label = QLabel("  End:")
        text_grad_col2_layout.addWidget(text_grad_col2_label, 1)
        self.btn_text_gradient_color2 = QPushButton("")
        self.btn_text_gradient_color2.setObjectName("colorButton")
        self.btn_text_gradient_color2.setFixedSize(32, 24)
        self.btn_text_gradient_color2.clicked.connect(lambda: self.choose_color(self.btn_text_gradient_color2))
        text_grad_col2_layout.addWidget(self.btn_text_gradient_color2, 2)
        gradient_text_layout.addLayout(text_grad_col2_layout)

        # --- Midpoint Control for Text ---
        text_grad_mid_layout = QHBoxLayout()
        text_grad_mid_label = QLabel("  Midpoint (%):")
        text_grad_mid_layout.addWidget(text_grad_mid_label, 1)
        self.spin_text_gradient_midpoint = QSpinBox()
        self.spin_text_gradient_midpoint.setObjectName("gradientMidpointSpinBox")
        self.spin_text_gradient_midpoint.setRange(0, 100)
        self.spin_text_gradient_midpoint.setValue(50)
        self.spin_text_gradient_midpoint.setSuffix("%")
        self.spin_text_gradient_midpoint.valueChanged.connect(self.style_changed_handler)
        text_grad_mid_layout.addWidget(self.spin_text_gradient_midpoint, 2)
        gradient_text_layout.addLayout(text_grad_mid_layout)
        # --- End Midpoint Control ---

        text_grad_dir_layout = QHBoxLayout()
        text_grad_dir_label = QLabel("  Direction:")
        text_grad_dir_layout.addWidget(text_grad_dir_label, 1)
        self.combo_text_gradient_direction = QComboBox()
        self.combo_text_gradient_direction.setObjectName("styleCombo")
        # --- Updated Direction Names ---
        self.combo_text_gradient_direction.addItems([
            "Horizontal (L>R)",
            "Vertical (T>B)",
            "Diagonal (TL>BR)",
            "Diagonal (BL>TR)"
        ])
        # --- End Updated Names ---
        self.combo_text_gradient_direction.currentIndexChanged.connect(self.style_changed_handler)
        text_grad_dir_layout.addWidget(self.combo_text_gradient_direction, 2)
        gradient_text_layout.addLayout(text_grad_dir_layout)

        font_layout.addWidget(self.gradient_text_group)

        # Font Family, Size, Style, Alignment, Auto-Size
        # ... (These controls remain the same) ...
        font_family_layout = QHBoxLayout()
        font_family_label = QLabel("Font:")
        font_family_layout.addWidget(font_family_label, 1)
        self.combo_font_family = QComboBox()
        self.combo_font_family.setObjectName("styleCombo")
        self.load_custom_fonts()
        self.combo_font_family.currentIndexChanged.connect(self.style_changed_handler)
        font_family_layout.addWidget(self.combo_font_family, 2)
        font_layout.addLayout(font_family_layout)
        font_props_layout = QHBoxLayout()
        font_size_label = QLabel("Size:")
        font_props_layout.addWidget(font_size_label)
        self.spin_font_size = QSpinBox()
        self.spin_font_size.setObjectName("styleSpinBox")
        self.spin_font_size.setRange(6, 72)
        self.spin_font_size.setValue(12)
        self.spin_font_size.valueChanged.connect(self.style_changed_handler)
        font_props_layout.addWidget(self.spin_font_size)
        font_props_layout.addSpacing(10)
        self.btn_font_bold = QCheckBox("")
        self.btn_font_bold.setObjectName("boldButton")
        self.btn_font_bold.setToolTip("Bold")
        self.btn_font_bold.stateChanged.connect(self.style_changed_handler)
        bold_icon = qta.icon('fa5s.bold', color='white')
        self.btn_font_bold.setIcon(bold_icon)
        font_props_layout.addWidget(self.btn_font_bold)
        self.btn_font_italic = QCheckBox("")
        self.btn_font_italic.setObjectName("italicButton")
        self.btn_font_italic.setToolTip("Italic")
        self.btn_font_italic.stateChanged.connect(self.style_changed_handler)
        italic_icon = qta.icon('fa5s.italic', color='white')
        self.btn_font_italic.setIcon(italic_icon)
        font_props_layout.addWidget(self.btn_font_italic)
        font_props_layout.addStretch()
        font_layout.addLayout(font_props_layout)
        alignment_layout = QHBoxLayout()
        alignment_label = QLabel("Alignment:")
        alignment_layout.addWidget(alignment_label, 1)
        alignment_buttons_layout = QHBoxLayout()
        alignment_buttons_layout.setSpacing(0)
        self.radio_align_left = QCheckBox("")
        self.radio_align_left.setObjectName("alignButton")
        left_icon = qta.icon('fa5s.align-left', color='white')
        self.radio_align_left.setIcon(left_icon)
        self.radio_align_left.setToolTip("Align Left")
        self.radio_align_left.clicked.connect(lambda: self.set_alignment(0))
        alignment_buttons_layout.addWidget(self.radio_align_left)
        self.radio_align_center = QCheckBox("")
        self.radio_align_center.setObjectName("alignButton")
        center_icon = qta.icon('fa5s.align-center', color='white')
        self.radio_align_center.setIcon(center_icon)
        self.radio_align_center.setToolTip("Align Center")
        self.radio_align_center.setChecked(True)
        self.radio_align_center.clicked.connect(lambda: self.set_alignment(1))
        alignment_buttons_layout.addWidget(self.radio_align_center)
        self.radio_align_right = QCheckBox("")
        self.radio_align_right.setObjectName("alignButton")
        right_icon = qta.icon('fa5s.align-right', color='white')
        self.radio_align_right.setIcon(right_icon)
        self.radio_align_right.setToolTip("Align Right")
        self.radio_align_right.clicked.connect(lambda: self.set_alignment(2))
        alignment_buttons_layout.addWidget(self.radio_align_right)
        alignment_layout.addLayout(alignment_buttons_layout, 2)
        font_layout.addLayout(alignment_layout)
        self.combo_text_alignment = QComboBox() # Hidden storage
        self.combo_text_alignment.addItems(["Left", "Center", "Right"])
        self.combo_text_alignment.setCurrentIndex(1)
        self.combo_text_alignment.setVisible(False)
        font_layout.addWidget(self.combo_text_alignment)
        auto_size_layout = QHBoxLayout()
        auto_size_label = QLabel("Auto-adjust font size:")
        auto_size_layout.addWidget(auto_size_label, 1)
        self.chk_auto_font_size = QCheckBox("")
        self.chk_auto_font_size.setObjectName("toggleSwitch")
        self.chk_auto_font_size.setChecked(True)
        self.chk_auto_font_size.stateChanged.connect(self.style_changed_handler)
        auto_size_layout.addWidget(self.chk_auto_font_size, 2)
        font_layout.addLayout(auto_size_layout)


        scroll_layout.addWidget(font_group)

        # --- Finish Scroll Area ---
        scroll_layout.addStretch()
        scroll_area.setWidget(scroll_content)
        main_layout.addWidget(scroll_area)

        # --- Button Bar ---
        # ... (Button bar remains the same) ...
        button_container = QWidget()
        button_container.setObjectName("buttonContainer")
        button_layout = QHBoxLayout(button_container)
        button_layout.setContentsMargins(0, 10, 0, 0)
        self.btn_reset = QPushButton("Reset")
        self.btn_reset.setObjectName("resetButton")
        self.btn_reset.clicked.connect(self.reset_style)
        button_layout.addWidget(self.btn_reset)
        button_layout.addSpacing(10)
        self.btn_apply = QPushButton("Apply")
        self.btn_apply.setObjectName("applyButton")
        self.btn_apply.clicked.connect(self.apply_style)
        button_layout.addWidget(self.btn_apply)
        main_layout.addWidget(button_container)


        # --- Apply Stylesheet ---
        # Ensure style IDs match controls, add styling for gradientMidpointSpinBox if desired
        self.setStyleSheet(TEXT_BOX_STYLE_PANEL_STYLESHEET + """
            #gradientMidpointSpinBox { /* Example additional style */
                background-color: #3A3A3A;
                color: #FFFFFF;
                border: 1px solid #4A4A4A;
                padding: 5px;
                border-radius: 3px;
                min-height: 24px;
                font-size: 18px; /* Smaller font maybe */
                max-width: 70px; /* Adjust width */
            }
        """)

        # --- Initial Control State ---
        self._toggle_fill_gradient_controls()
        self._toggle_text_gradient_controls()

    # --- Methods for toggling gradient controls ---
    def _toggle_fill_gradient_controls(self):
        is_gradient = self.combo_fill_type.currentIndex() == 1
        self.gradient_fill_group.setVisible(is_gradient)
        # self.solid_fill_layout.setVisible(not is_gradient) # Optional

    def _toggle_text_gradient_controls(self):
        is_gradient = self.combo_text_color_type.currentIndex() == 1
        self.gradient_text_group.setVisible(is_gradient)
        # self.solid_text_color_layout.setVisible(not is_gradient) # Optional

    # --- Alignment Helper ---
    def set_alignment(self, index):
        # ... (remains the same) ...
        self._updating_controls = True
        self.combo_text_alignment.setCurrentIndex(index)
        self.radio_align_left.setChecked(index == 0)
        self.radio_align_center.setChecked(index == 1)
        self.radio_align_right.setChecked(index == 2)
        self._updating_controls = False
        self.style_changed_handler()

    # --- Font Loading ---
    def load_custom_fonts(self):
        # ... (remains the same) ...
        self.custom_fonts = {}
        self.combo_font_family.clear()
        self.combo_font_family.addItem("Default (System Font)")
        fonts_dir = "assets/fonts"
        if not os.path.exists(fonts_dir): return
        for file in os.listdir(fonts_dir):
            if file.lower().endswith(('.ttf', '.otf')):
                font_path = os.path.join(fonts_dir, file)
                font_id = QFontDatabase.addApplicationFont(font_path)
                if font_id != -1:
                    families = QFontDatabase.applicationFontFamilies(font_id)
                    for family in families:
                        self.custom_fonts[family] = font_id
                        self.combo_font_family.addItem(family)


    # --- Color Helpers ---
    def set_button_color(self, button, color):
        # ... (remains the same) ...
        if not isinstance(color, QColor): color = QColor(color)
        if not color.isValid(): color = QColor(255, 255, 255)
        button.setStyleSheet(f"background-color: {color.name(QColor.HexArgb)}; border: 1px solid #60666E; border-radius: 3px;")


    def choose_color(self, button):
        # ... (remains the same) ...
        current_color = self._get_color_from_button(button)
        color = QColorDialog.getColor(initial=current_color)
        if color.isValid():
            self.set_button_color(button, color)
            self.style_changed_handler()

    def _get_color_from_button(self, button):
        # ... (remains the same) ...
        style = button.styleSheet()
        try:
            start = style.find("background-color:") + len("background-color:")
            end = style.find(";", start)
            return QColor(style[start:end].strip())
        except:
            return QColor(0, 0, 0)


    # --- Style Get/Set/Reset ---
    def get_current_style(self):
        """Get the current style settings including integer gradient midpoint."""
        # ... (font family logic remains the same) ...
        font_family = "Arial"
        selected_text = self.combo_font_family.currentText()
        if selected_text != "Default (System Font)": font_family = selected_text
        elif self._default_style: font_family = self._default_style.get('font_family', "Arial")

        style = {
            # ... (other style keys: bubble_type, corner_radius, border_width, border_color) ...
            'bubble_type': self.combo_bubble_type.currentIndex(),
            'corner_radius': self.spin_corner_radius.value(),
            'border_width': self.spin_border_width.value(),
            'border_color': self._get_color_from_button(self.btn_border_color).name(QColor.HexArgb),

            'fill_type': 'solid' if self.combo_fill_type.currentIndex() == 0 else 'linear_gradient',
            'bg_color': self._get_color_from_button(self.btn_bg_color).name(QColor.HexArgb),
            'bg_gradient': {
                'color1': self._get_color_from_button(self.btn_bg_gradient_color1).name(QColor.HexArgb),
                'color2': self._get_color_from_button(self.btn_bg_gradient_color2).name(QColor.HexArgb),
                'direction': self.combo_bg_gradient_direction.currentIndex(),
                # --- Get midpoint value directly as int ---
                'midpoint': self.spin_bg_gradient_midpoint.value(), # Store as 0-100
            },

            'text_color_type': 'solid' if self.combo_text_color_type.currentIndex() == 0 else 'linear_gradient',
            'text_color': self._get_color_from_button(self.btn_text_color).name(QColor.HexArgb),
            'text_gradient': {
                'color1': self._get_color_from_button(self.btn_text_gradient_color1).name(QColor.HexArgb),
                'color2': self._get_color_from_button(self.btn_text_gradient_color2).name(QColor.HexArgb),
                'direction': self.combo_text_gradient_direction.currentIndex(),
                # --- Get midpoint value directly as int ---
                'midpoint': self.spin_text_gradient_midpoint.value(), # Store as 0-100
            },

            # ... (other style keys: font_family, font_size, font_bold, etc.) ...
            'font_family': font_family,
            'font_size': self.spin_font_size.value(),
            'font_bold': self.btn_font_bold.isChecked(),
            'font_italic': self.btn_font_italic.isChecked(),
            'text_alignment': self.combo_text_alignment.currentIndex(),
            'auto_font_size': self.chk_auto_font_size.isChecked(),
        }
        return style
    
    def style_changed_handler(self):
        if not self._updating_controls:
            current_style = self.get_current_style()
            self.style_changed.emit(current_style)

    def apply_style(self):
        self.style_changed.emit(self.get_current_style())

    def reset_style(self):
        # Reset to the augmented default style (which includes midpoint: 0.5)
        self.update_style_panel(self._default_style)
        self.style_changed_handler() # Emit the reset style

    def update_style_panel(self, style_dict_in):
        if not style_dict_in:
            style_dict = self._default_style # Use augmented default with int midpoint
        else:
            style_dict = self._ensure_gradient_defaults(style_dict_in) # Ensure incoming has int midpoint

        self._updating_controls = True
        self.selected_style_info = style_dict

        # ... (Shape, Border setup remains the same) ...
        self.combo_bubble_type.setCurrentIndex(style_dict.get('bubble_type', 1))
        self.spin_corner_radius.setValue(style_dict.get('corner_radius', 50))
        self.spin_border_width.setValue(style_dict.get('border_width', 1))
        self.set_button_color(self.btn_border_color, style_dict.get('border_color', '#ff000000'))


        # Fill
        fill_type = style_dict.get('fill_type', 'solid')
        self.combo_fill_type.setCurrentIndex(1 if fill_type == 'linear_gradient' else 0)
        self.set_button_color(self.btn_bg_color, style_dict.get('bg_color', '#ffffffff'))
        bg_gradient = style_dict.get('bg_gradient', DEFAULT_GRADIENT) # Use default as fallback
        self.set_button_color(self.btn_bg_gradient_color1, bg_gradient.get('color1'))
        self.set_button_color(self.btn_bg_gradient_color2, bg_gradient.get('color2'))
        self.combo_bg_gradient_direction.setCurrentIndex(bg_gradient.get('direction'))
        # --- Set midpoint control directly as int ---
        self.spin_bg_gradient_midpoint.setValue(int(bg_gradient.get('midpoint', 50)))

        # Text Color
        text_color_type = style_dict.get('text_color_type', 'solid')
        self.combo_text_color_type.setCurrentIndex(1 if text_color_type == 'linear_gradient' else 0)
        self.set_button_color(self.btn_text_color, style_dict.get('text_color', '#ff000000'))
        text_gradient = style_dict.get('text_gradient', DEFAULT_GRADIENT)
        self.set_button_color(self.btn_text_gradient_color1, text_gradient.get('color1'))
        self.set_button_color(self.btn_text_gradient_color2, text_gradient.get('color2'))
        self.combo_text_gradient_direction.setCurrentIndex(text_gradient.get('direction'))
        # --- Set midpoint control directly as int ---
        self.spin_text_gradient_midpoint.setValue(int(text_gradient.get('midpoint', 50)))

        # ... (Font, Alignment, Auto-size setup remains the same) ...
        font_family = style_dict.get('font_family', "Arial")
        index = self.combo_font_family.findText(font_family)
        self.combo_font_family.setCurrentIndex(index if index != -1 else 0)
        self.spin_font_size.setValue(style_dict.get('font_size', 12))
        self.btn_font_bold.setChecked(style_dict.get('font_bold', False))
        self.btn_font_italic.setChecked(style_dict.get('font_italic', False))
        alignment_index = style_dict.get('text_alignment', 1)
        self.combo_text_alignment.setCurrentIndex(alignment_index)
        self.radio_align_left.setChecked(alignment_index == 0)
        self.radio_align_center.setChecked(alignment_index == 1)
        self.radio_align_right.setChecked(alignment_index == 2)
        self.chk_auto_font_size.setChecked(style_dict.get('auto_font_size', True))

        # Toggle visibility AFTER setting values
        self._toggle_fill_gradient_controls()
        self._toggle_text_gradient_controls()

        self._updating_controls = False
        if style_dict_in: self.show()

    def clear_and_hide(self):
        self.selected_style_info = None
        self.hide()

# --- END OF FILE custom_bubble.py ---