import os
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QLabel, QComboBox, QPushButton, QSlider, QColorDialog, QFrame,
                             QGridLayout, QCheckBox, QSpinBox, QGroupBox, QFontComboBox, QHBoxLayout, QScrollArea,
                             QSpacerItem, QSizePolicy)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QColor, QFont, QFontDatabase
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
        # Store font style info separate from the main style dict initially
        self.font_styles = {} # { "Family Name": ["Style1", "Style2", ...] }
        self._original_default_style = default_style if default_style else {}
        # Ensure defaults *before* init_ui uses them for initial population if needed
        self._default_style = self._ensure_gradient_defaults(self._original_default_style)
        self.selected_text_box_info = None
        self._updating_controls = False
        self.selected_style_info = None
        self.init_ui() # Loads fonts, populates family combo
        # Apply defaults after UI is fully initialized
        self.update_style_panel(self._default_style)
        # self.hide() # Hide until needed

    def _ensure_gradient_defaults(self, style_dict):
        """Ensures a style dictionary has default gradient fields including integer midpoint."""
        style = style_dict.copy() if style_dict else {}
        # Fill defaults
        if 'fill_type' not in style: style['fill_type'] = 'solid'
        if 'bg_color' not in style: style['bg_color'] = '#ffffffff'
        if 'bg_gradient' not in style: style['bg_gradient'] = {}
        style['bg_gradient'] = {**DEFAULT_GRADIENT, **style['bg_gradient']}

        # Text defaults
        if 'text_color_type' not in style: style['text_color_type'] = 'solid'
        if 'text_color' not in style: style['text_color'] = '#ff000000'
        if 'text_gradient' not in style: style['text_gradient'] = {}
        style['text_gradient'] = {**DEFAULT_GRADIENT, **style['text_gradient']}

        # --- Ensure colors are strings ---
        # ... (color string conversion remains the same) ...
        if isinstance(style.get('bg_color'), QColor): style['bg_color'] = style['bg_color'].name(QColor.HexArgb)
        if isinstance(style.get('text_color'), QColor): style['text_color'] = style['text_color'].name(QColor.HexArgb)
        if isinstance(style['bg_gradient'].get('color1'), QColor): style['bg_gradient']['color1'] = style['bg_gradient']['color1'].name(QColor.HexArgb)
        if isinstance(style['bg_gradient'].get('color2'), QColor): style['bg_gradient']['color2'] = style['bg_gradient']['color2'].name(QColor.HexArgb)
        if isinstance(style['text_gradient'].get('color1'), QColor): style['text_gradient']['color1'] = style['text_gradient']['color1'].name(QColor.HexArgb)
        if isinstance(style['text_gradient'].get('color2'), QColor): style['text_gradient']['color2'] = style['text_gradient']['color2'].name(QColor.HexArgb)


        # Ensure midpoint is int
        if 'midpoint' in style['bg_gradient']: style['bg_gradient']['midpoint'] = int(style['bg_gradient'].get('midpoint', 50))
        if 'midpoint' in style['text_gradient']: style['text_gradient']['midpoint'] = int(style['text_gradient'].get('midpoint', 50))

        # Font style default
        if 'font_style' not in style: style['font_style'] = 'Regular' # Add default font style

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



        # --- Text Color ---
        # ... (Text Color/Gradient controls remain the same, midpoint already added) ...
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

        # --- Font Properties (Size, Bold, Italic) ---
        # --- Font Selection ---
        font_family_layout = QHBoxLayout()
        font_family_label = QLabel("Font:")
        font_family_layout.addWidget(font_family_label, 1)
        self.combo_font_family = QComboBox()
        self.combo_font_family.setObjectName("styleCombo")
        # Load fonts *before* connecting signals that depend on font_styles
        self.load_custom_fonts() # Populates self.combo_font_family and self.font_styles
        font_family_layout.addWidget(self.combo_font_family, 2)
        font_layout.addLayout(font_family_layout)

        # --- Font Style Selection (NEW) ---
        self.font_style_widget = QWidget() # Container for visibility toggle
        self.font_style_layout = QHBoxLayout(self.font_style_widget)
        self.font_style_layout.setContentsMargins(0, 0, 0, 0)
        self.font_style_layout.setSpacing(8) # Match other layouts
        font_style_label = QLabel("Style:")
        self.font_style_layout.addWidget(font_style_label, 1)
        self.combo_font_style = QComboBox()
        self.combo_font_style.setObjectName("styleCombo")
        self.combo_font_style.currentIndexChanged.connect(self.style_changed_handler)
        self.font_style_layout.addWidget(self.combo_font_style, 2)
        font_layout.addWidget(self.font_style_widget)
        self.font_style_widget.setVisible(False) # Initially hidden

        # Connect family change to style update *after* both combos exist
        self.combo_font_family.currentIndexChanged.connect(self._update_font_style_combo)
        self.combo_font_family.currentIndexChanged.connect(self.style_changed_handler) # Keep this too
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

        # --- Alignment & Auto-Size ---
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
        self.setStyleSheet(TEXT_BOX_STYLE_PANEL_STYLESHEET + """
            #gradientMidpointSpinBox {
                background-color: #3A3A3A;
                color: #FFFFFF;
                border: 1px solid #4A4A4A;
                padding: 5px;
                border-radius: 3px;
                min-height: 24px;
                font-size: 18px; /* Smaller font maybe */
                max-width: 70px; /* Adjust width */
            }
            #styleCombo { /* Ensure style combo has consistent look */
                min-height: 28px; /* Match font family combo */
                padding-left: 8px;
            }
        """)

        # --- Initial Control State ---
        self._toggle_fill_gradient_controls()
        self._toggle_text_gradient_controls()
        self._update_font_style_combo() # Update based on initial font


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

    # --- Font Loading & Style Handling ---
    def load_custom_fonts(self):
        """Loads custom fonts, groups them by family, and populates the family combo."""
        self.font_styles.clear()
        # Keep track of families already added to the combo box
        added_families = set()
        self.combo_font_family.clear()
        self.combo_font_family.addItem("Default (System Font)")
        added_families.add("Default (System Font)")

        fonts_dir = "assets/fonts"
        if not os.path.exists(fonts_dir):
            print("Font directory not found:", fonts_dir)
            return

        db = QFontDatabase()
        loaded_families = set() # Track families loaded in this session

        for file in os.listdir(fonts_dir):
            if file.lower().endswith(('.ttf', '.otf')):
                font_path = os.path.join(fonts_dir, file)
                font_id = db.addApplicationFont(font_path)
                if font_id != -1:
                    families = db.applicationFontFamilies(font_id)
                    for family in families:
                        loaded_families.add(family)
                else:
                     print(f"Warning: Could not load font: {font_path}")

        # Now iterate through loaded families to get styles
        for family in sorted(list(loaded_families)): # Sort for consistency
            styles = db.styles(family)
            filtered_styles = []
            # Filter out styles containing 'Bold' or 'Italic' (case-insensitive)
            # Keep 'Regular' or equivalent common names explicitly if needed.
            has_regular = False
            for style in styles:
                style_lower = style.lower()
                if "bold" not in style_lower and "italic" not in style_lower and "oblique" not in style_lower:
                     filtered_styles.append(style)
                     if style_lower == "regular" or style_lower == "normal" or style_lower == "book":
                         has_regular = True

            # If only Bold/Italic styles existed, add 'Regular' if QFontDatabase lists it,
            # otherwise maybe add the first original style back? Or leave empty.
            # Let's keep it simple: only add non-bold/italic styles.
            # If after filtering, the list is empty, maybe add "Regular" if it exists in the original list?
            if not filtered_styles and "Regular" in styles:
                 filtered_styles.append("Regular")
            elif not filtered_styles and styles: # If only bold/italic, maybe add the first non-filtered one? Risky.
                pass # Keep filtered_styles empty if only bold/italic variants exist

            if filtered_styles: # Only store families that have non-bold/italic styles
                self.font_styles[family] = sorted(filtered_styles) # Store sorted styles

            # Add family to combo box only once
            if family not in added_families:
                self.combo_font_family.addItem(family)
                added_families.add(family)

    def _update_font_style_combo(self):
        """Populates the font style combo based on the selected family."""
        if self._updating_controls: return # Prevent recursion

        self._updating_controls = True # Set flag

        current_family = self.combo_font_family.currentText()
        self.combo_font_style.clear()

        if current_family in self.font_styles and self.font_styles[current_family]:
            styles = self.font_styles[current_family]
            self.combo_font_style.addItems(styles)

            # Try to select "Regular" or the first available style
            default_style = "Regular"
            if default_style in styles:
                self.combo_font_style.setCurrentText(default_style)
            elif styles:
                self.combo_font_style.setCurrentIndex(0)

            self.font_style_widget.setVisible(True)
        else:
            # Hide style combo for default font or fonts with no selectable styles
            self.font_style_widget.setVisible(False)

        self._updating_controls = False # Clear flag

        # No need to call style_changed_handler here, it's called by the family combo change signal

    # --- Color Helpers ---
    def set_button_color(self, button, color):
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

#    def choose_color(self, button):
#        """Opens the custom color dialog to choose a color for the button."""
#        current_color = self._get_color_from_button(button)
#        # Use the custom color dialog instead of QColorDialog
#        # Pass the current button color as initial_color and self as parent
#        color = CustomColorDialog.getColor(initial_color=current_color, parent=self)
#
#        # The rest of the logic remains the same:
#        # Check if a valid color was returned (CustomColorDialog.getColor returns the selected color on accept)
#        if color is not None and color.isValid():
#            self.set_button_color(button, color)
#            self.style_changed_handler() # Emit signal that style might have changed

    def _get_color_from_button(self, button):
        style = button.styleSheet()
        try:
            start = style.find("background-color:") + len("background-color:")
            end = style.find(";", start)
            return QColor(style[start:end].strip())
        except:
            return QColor(0, 0, 0)


    # --- Style Get/Set/Reset ---
    def get_current_style(self):
        """Get the current style settings including font family and style."""
        # Font Family and Style
        font_family = "Arial" # Default fallback
        selected_family_text = self.combo_font_family.currentText()
        font_style = "Regular" # Default fallback

        if selected_family_text == "Default (System Font)":
            # Use the actual default style's font if available, else Arial
            font_family = self._default_style.get('font_family', "Arial")
            font_style = self._default_style.get('font_style', "Regular")
        elif selected_family_text in self.font_styles:
            font_family = selected_family_text
            if self.font_style_widget.isVisible() and self.combo_font_style.count() > 0:
                font_style = self.combo_font_style.currentText()
            else:
                # If style combo is hidden but family is custom, use its default style if known, else Regular
                font_style = self.font_styles[font_family][0] if self.font_styles[font_family] else "Regular"
        else:
            # Should not happen if combo is populated correctly, but fallback
            font_family = selected_family_text # Use the text directly if not in font_styles? Risky.

        style = {
            # Shape
            'bubble_type': self.combo_bubble_type.currentIndex(),
            'corner_radius': self.spin_corner_radius.value(),

            # Fill & Stroke
            'border_width': self.spin_border_width.value(),
            'border_color': self._get_color_from_button(self.btn_border_color).name(QColor.HexArgb),
            'fill_type': 'solid' if self.combo_fill_type.currentIndex() == 0 else 'linear_gradient',
            'bg_color': self._get_color_from_button(self.btn_bg_color).name(QColor.HexArgb),
            'bg_gradient': {
                'color1': self._get_color_from_button(self.btn_bg_gradient_color1).name(QColor.HexArgb),
                'color2': self._get_color_from_button(self.btn_bg_gradient_color2).name(QColor.HexArgb),
                'direction': self.combo_bg_gradient_direction.currentIndex(),
                'midpoint': self.spin_bg_gradient_midpoint.value(),
            },

            # Text Color
            'text_color_type': 'solid' if self.combo_text_color_type.currentIndex() == 0 else 'linear_gradient',
            'text_color': self._get_color_from_button(self.btn_text_color).name(QColor.HexArgb),
            'text_gradient': {
                'color1': self._get_color_from_button(self.btn_text_gradient_color1).name(QColor.HexArgb),
                'color2': self._get_color_from_button(self.btn_text_gradient_color2).name(QColor.HexArgb),
                'direction': self.combo_text_gradient_direction.currentIndex(),
                'midpoint': self.spin_text_gradient_midpoint.value(),
            },

            # Typography
            'font_family': font_family,
            'font_style': font_style, # Added font style
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

        self._updating_controls = True # Prevent signals during update
        self.selected_style_info = style_dict

        # --- Update Shape, Fill, Stroke, Text Color (same as before) ---
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
        self.spin_bg_gradient_midpoint.setValue(int(bg_gradient.get('midpoint', 50)))

        # Text Color
        text_color_type = style_dict.get('text_color_type', 'solid')
        self.combo_text_color_type.setCurrentIndex(1 if text_color_type == 'linear_gradient' else 0)
        self.set_button_color(self.btn_text_color, style_dict.get('text_color', '#ff000000'))
        text_gradient = style_dict.get('text_gradient', DEFAULT_GRADIENT)
        self.set_button_color(self.btn_text_gradient_color1, text_gradient.get('color1'))
        self.set_button_color(self.btn_text_gradient_color2, text_gradient.get('color2'))
        self.combo_text_gradient_direction.setCurrentIndex(text_gradient.get('direction'))
        self.spin_text_gradient_midpoint.setValue(int(text_gradient.get('midpoint', 50)))

        # --- Update Typography ---
        font_family = style_dict.get('font_family', "Arial")
        font_style = style_dict.get('font_style', 'Regular')

        # Set Font Family
        index = self.combo_font_family.findText(font_family)
        if index != -1:
            self.combo_font_family.setCurrentIndex(index)
        else:
            # Fallback if family not found (e.g., font removed)
            default_index = self.combo_font_family.findText("Default (System Font)")
            self.combo_font_family.setCurrentIndex(default_index if default_index != -1 else 0)
            print(f"Warning: Font family '{font_family}' not found, using default.")
            # Update font_family to the one actually selected for style lookup
            font_family = self.combo_font_family.currentText()

        # Set Font Style *after* family selection might have populated the style combo
        if self.font_style_widget.isVisible():
            style_index = self.combo_font_style.findText(font_style)
            if style_index != -1:
                self.combo_font_style.setCurrentIndex(style_index)
            elif self.combo_font_style.count() > 0:
                # Fallback to first available style if specified one not found
                self.combo_font_style.setCurrentIndex(0)
                print(f"Warning: Font style '{font_style}' not found for family '{font_family}', using first available.")

        # Set other font properties
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