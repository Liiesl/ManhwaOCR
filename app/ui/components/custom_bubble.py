import os
import json
import functools
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QLabel, QComboBox, QPushButton, QColorDialog, QFrame,
                             QCheckBox, QSpinBox, QGroupBox, QHBoxLayout, QScrollArea)
from PyQt5.QtCore import Qt, pyqtSignal, QSettings
from PyQt5.QtGui import (QColor, QFontDatabase)
import qtawesome as qta
from app.ui.components import PresetButton
from assets.styles import TEXT_BOX_STYLE_PANEL_STYLESHEET, DEFAULT_GRADIENT
from app.ui.dialogs import CustomColorDialog

def get_style_diff(style_dict, base_style_dict):
    """Compares a style dict to a base and returns only the changed values."""
    diff = {}
    for key, value in style_dict.items():
        if key not in base_style_dict or base_style_dict[key] != value:
            # For nested dictionaries (like gradients), compare them deeply
            if isinstance(value, dict) and key in base_style_dict and isinstance(base_style_dict[key], dict):
                nested_diff = get_style_diff(value, base_style_dict[key])
                if nested_diff:
                    diff[key] = nested_diff
            else:
                diff[key] = value
    return diff

class TextBoxStylePanel(QWidget):
    """
    A panel for customizing the appearance of a selected TextBoxItem, including gradients with midpoints.
    """
    style_changed = pyqtSignal(dict)

    def __init__(self, parent=None, default_style=None):
        super().__init__(parent)
        self.setObjectName("TextBoxStylePanel")
        self.setMinimumWidth(400)
        self.settings = QSettings("YourCompany", "MangaOCRTool")
        self.presets = []
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
        self._load_presets()

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

        bg_grad_dir_layout = QHBoxLayout()
        bg_grad_dir_label = QLabel("  Direction:")
        bg_grad_dir_layout.addWidget(bg_grad_dir_label, 1)
        self.combo_bg_gradient_direction = QComboBox()
        self.combo_bg_gradient_direction.setObjectName("styleCombo")
        self.combo_bg_gradient_direction.addItems([
            "Horizontal (L>R)",
            "Vertical (T>B)",
            "Diagonal (TL>BR)", # TopLeft to BottomRight
            "Diagonal (BL>TR)"  # BottomLeft to TopRight
        ])
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
        self.combo_text_gradient_direction.addItems([
            "Horizontal (L>R)",
            "Vertical (T>B)",
            "Diagonal (TL>BR)",
            "Diagonal (BL>TR)"
        ])
        self.combo_text_gradient_direction.currentIndexChanged.connect(self.style_changed_handler)
        text_grad_dir_layout.addWidget(self.combo_text_gradient_direction, 2)
        gradient_text_layout.addLayout(text_grad_dir_layout)
        font_layout.addWidget(self.gradient_text_group)

        # --- Font Properties ---
        font_family_layout = QHBoxLayout()
        font_family_label = QLabel("Font:")
        font_family_layout.addWidget(font_family_label, 1)
        self.combo_font_family = QComboBox()
        self.combo_font_family.setObjectName("styleCombo")
        self.load_custom_fonts()
        font_family_layout.addWidget(self.combo_font_family, 2)
        font_layout.addLayout(font_family_layout)

        self.font_style_widget = QWidget()
        self.font_style_layout = QHBoxLayout(self.font_style_widget)
        self.font_style_layout.setContentsMargins(0, 0, 0, 0)
        self.font_style_layout.setSpacing(8)
        font_style_label = QLabel("Style:")
        self.font_style_layout.addWidget(font_style_label, 1)
        self.combo_font_style = QComboBox()
        self.combo_font_style.setObjectName("styleCombo")
        self.combo_font_style.currentIndexChanged.connect(self.style_changed_handler)
        self.font_style_layout.addWidget(self.combo_font_style, 2)
        font_layout.addWidget(self.font_style_widget)
        self.font_style_widget.setVisible(False)

        self.combo_font_family.currentIndexChanged.connect(self._update_font_style_combo)
        self.combo_font_family.currentIndexChanged.connect(self.style_changed_handler)
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
        self.btn_font_bold.setIcon(qta.icon('fa5s.bold', color='white'))
        font_props_layout.addWidget(self.btn_font_bold)
        self.btn_font_italic = QCheckBox("")
        self.btn_font_italic.setObjectName("italicButton")
        self.btn_font_italic.setToolTip("Italic")
        self.btn_font_italic.stateChanged.connect(self.style_changed_handler)
        self.btn_font_italic.setIcon(qta.icon('fa5s.italic', color='white'))
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
        self.radio_align_left.setIcon(qta.icon('fa5s.align-left', color='white'))
        self.radio_align_left.setToolTip("Align Left")
        self.radio_align_left.clicked.connect(lambda: self.set_alignment(0))
        alignment_buttons_layout.addWidget(self.radio_align_left)
        self.radio_align_center = QCheckBox("")
        self.radio_align_center.setObjectName("alignButton")
        self.radio_align_center.setIcon(qta.icon('fa5s.align-center', color='white'))
        self.radio_align_center.setToolTip("Align Center")
        self.radio_align_center.setChecked(True)
        self.radio_align_center.clicked.connect(lambda: self.set_alignment(1))
        alignment_buttons_layout.addWidget(self.radio_align_center)
        self.radio_align_right = QCheckBox("")
        self.radio_align_right.setObjectName("alignButton")
        self.radio_align_right.setIcon(qta.icon('fa5s.align-right', color='white'))
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

        # --- Presets Group (Scrollable & Dynamic) ---
        presets_group = QGroupBox("Presets")
        presets_group.setObjectName("styleGroup")
        presets_main_layout = QHBoxLayout(presets_group)
        presets_main_layout.setContentsMargins(10, 15, 10, 10)
        presets_main_layout.setSpacing(6)

        # Scroll Area for preset buttons
        preset_scroll_area = QScrollArea()
        preset_scroll_area.setWidgetResizable(True)
        preset_scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        preset_scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        preset_scroll_area.setFrameShape(QFrame.NoFrame)
        preset_scroll_area.setStyleSheet("background-color: transparent;")

        # Container widget and layout for the buttons
        self.preset_buttons_container = QWidget()
        self.presets_buttons_layout = QHBoxLayout(self.preset_buttons_container)
        self.presets_buttons_layout.setContentsMargins(0, 0, 0, 0)
        self.presets_buttons_layout.setSpacing(6)
        
        preset_scroll_area.setWidget(self.preset_buttons_container)
        presets_main_layout.addWidget(preset_scroll_area)

        self.preset_buttons = [] # This list will be populated by _rebuild_preset_ui

        # The Add button is now outside the scroll area for permanent visibility
        self.btn_add_preset = QPushButton(qta.icon('fa5s.plus'), "")
        self.btn_add_preset.setToolTip("Save current style as a new preset")
        self.btn_add_preset.setFixedSize(48, 48)
        self.btn_add_preset.setObjectName("addPresetButton")
        self.btn_add_preset.clicked.connect(self._add_preset)
        presets_main_layout.addWidget(self.btn_add_preset)

        main_layout.addWidget(presets_group)

        # --- Button Bar ---
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
                background-color: #3A3A3A; color: #FFFFFF; border: 1px solid #4A4A4A;
                padding: 5px; border-radius: 3px; min-height: 24px; font-size: 18px; max-width: 70px;
            }
            #styleCombo { min-height: 28px; padding-left: 8px; }
            #addPresetButton { background-color: #333; border: 1px solid #555; border-radius: 3px; }
            #addPresetButton:hover { background-color: #444; border-color: #666; }
        """)

        # --- Initial Control State ---
        self._toggle_fill_gradient_controls()
        self._toggle_text_gradient_controls()
        self._update_font_style_combo()

    # --- Preset Management ---
    def _rebuild_preset_ui(self):
        """Clears and rebuilds the preset button UI from the self.presets list."""
        # Clear the layout first
        while self.presets_buttons_layout.count():
            child = self.presets_buttons_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
        
        self.preset_buttons.clear()

        # Re-populate from the self.presets list
        for i, style in enumerate(self.presets):
            preset_button = PresetButton(i, self)
            preset_button.set_style(style)
            preset_button.clicked.connect(functools.partial(self._on_preset_clicked, i))
            preset_button.overwrite_requested.connect(self._overwrite_preset)
            preset_button.delete_requested.connect(self._delete_preset)
            self.preset_buttons.append(preset_button)
            self.presets_buttons_layout.addWidget(preset_button)
        
        # Add a stretch at the end to keep buttons aligned to the left
        self.presets_buttons_layout.addStretch()
        
        # The add button is always enabled for creating new presets
        self.btn_add_preset.setEnabled(True)

# In custom_bubble.py, inside the TextBoxStylePanel class:

    def _load_presets(self):
        """Loads presets from QSettings by reading sequential keys."""
        self.presets = []
        
        # --- FIX: Use beginGroup/endGroup for reading to mirror the saving logic ---
        # This makes the code more robust and symmetrical.
        self.settings.beginGroup("style_presets")
        i = 0
        while True:
            # Now we use the relative key "preset_i", as QSettings knows the group context.
            key = f"preset_{i}"
            preset_str = self.settings.value(key, None)
            
            if preset_str is None:
                # No more presets found in the group.
                break
            
            try:
                self.presets.append(json.loads(preset_str))
            except (json.JSONDecodeError, TypeError):
                print(f"Warning: Could not load preset at index {i}. It will be removed on next save.")
            i += 1
            
        self.settings.endGroup()
        
        self._rebuild_preset_ui()

    def _save_presets(self):
        """Saves the current presets to QSettings, overwriting old ones."""
        self.settings.beginGroup("style_presets")
        self.settings.remove("") # Clear all keys in this group first
        for i, preset in enumerate(self.presets):
            if preset: # Don't save None placeholders
                self.settings.setValue(f"preset_{i}", json.dumps(preset))
        self.settings.endGroup()
        
        # --- FIX: Explicitly write changes to persistent storage ---
        # This ensures that settings are saved immediately and not just on app exit.
        self.settings.sync()

    def _on_preset_clicked(self, index):
        """Applies a preset style to the panel when a preset button is clicked."""
        if not (0 <= index < len(self.presets)):
            return
            
        style_diff = self.presets[index]
        if style_diff is None:
            return

        # Deep merge the diff with the panel's own default style
        full_style = json.loads(json.dumps(self._default_style))  # Deep copy
        for key, value in style_diff.items():
            if isinstance(value, dict) and key in full_style:
                full_style[key].update(value)
            else:
                full_style[key] = value

        self.update_style_panel(full_style)
        self.style_changed_handler()

    def _add_preset(self):
        """Saves the current style as a new preset."""
        current_style = self.get_current_style()
        style_diff = get_style_diff(current_style, self._default_style)
        self.presets.append(style_diff)
        self._save_presets()
        self._rebuild_preset_ui()
        print(f"New preset saved. Total presets: {len(self.presets)}.")

    def _overwrite_preset(self, index):
        """Saves the current style over a specific preset slot."""
        if not (0 <= index < len(self.presets)):
            return
        current_style = self.get_current_style()
        style_diff = get_style_diff(current_style, self._default_style)
        self.presets[index] = style_diff
        self._save_presets()
        self._rebuild_preset_ui() # Rebuild to update the visual
        print(f"Preset at slot {index + 1} overwritten.")

    def _delete_preset(self, index):
        """Deletes a preset from a specific slot."""
        if not (0 <= index < len(self.presets)):
            return
        self.presets.pop(index)
        self._save_presets()
        self._rebuild_preset_ui()
        print(f"Preset at slot {index + 1} deleted.")

    # --- Methods for toggling gradient controls ---
    def _toggle_fill_gradient_controls(self):
        is_gradient = self.combo_fill_type.currentIndex() == 1
        self.gradient_fill_group.setVisible(is_gradient)

    def _toggle_text_gradient_controls(self):
        is_gradient = self.combo_text_color_type.currentIndex() == 1
        self.gradient_text_group.setVisible(is_gradient)

    # --- Alignment Helper ---
    def set_alignment(self, index):
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
        added_families = set()
        self.combo_font_family.clear()
        self.combo_font_family.addItem("Default (System Font)")
        added_families.add("Default (System Font)")

        fonts_dir = "assets/fonts"
        if not os.path.exists(fonts_dir):
            print("Font directory not found:", fonts_dir)
            return

        db = QFontDatabase()
        loaded_families = set()

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

        for family in sorted(list(loaded_families)):
            styles = db.styles(family)
            filtered_styles = []
            has_regular = False
            for style in styles:
                style_lower = style.lower()
                if "bold" not in style_lower and "italic" not in style_lower and "oblique" not in style_lower:
                     filtered_styles.append(style)
                     if style_lower == "regular" or style_lower == "normal" or style_lower == "book":
                         has_regular = True

            if not filtered_styles and "Regular" in styles:
                 filtered_styles.append("Regular")
            elif not filtered_styles and styles: # If only bold/italic, maybe add the first non-filtered one? Risky.
                pass # Keep filtered_styles empty if only bold/italic variants exist

            if filtered_styles:
                self.font_styles[family] = sorted(filtered_styles)

            if family not in added_families:
                self.combo_font_family.addItem(family)
                added_families.add(family)

    def _update_font_style_combo(self):
        """Populates the font style combo based on the selected family."""
        if self._updating_controls: return

        self._updating_controls = True

        current_family = self.combo_font_family.currentText()
        self.combo_font_style.clear()

        if current_family in self.font_styles and self.font_styles[current_family]:
            styles = self.font_styles[current_family]
            self.combo_font_style.addItems(styles)

            default_style = "Regular"
            if default_style in styles:
                self.combo_font_style.setCurrentText(default_style)
            elif styles:
                self.combo_font_style.setCurrentIndex(0)

            self.font_style_widget.setVisible(True)
        else:
            self.font_style_widget.setVisible(False)

        self._updating_controls = False

    # --- Color Helpers ---
    def set_button_color(self, button, color):
        if not isinstance(color, QColor): color = QColor(color)
        if not color.isValid(): color = QColor(255, 255, 255)
        button.setStyleSheet(f"background-color: {color.name(QColor.HexArgb)}; border: 1px solid #60666E; border-radius: 3px;")

    def choose_color(self, button):
        """Opens the custom color dialog to choose a color for the button."""
        current_color = self._get_color_from_button(button)
        # Use the custom color dialog instead of QColorDialog
        # Pass the current button color as initial_color and self as parent
        color = CustomColorDialog.getColor(initial_color=current_color, parent=self)

        # The rest of the logic remains the same:
        # Check if a valid color was returned (CustomColorDialog.getColor returns the selected color on accept)
        if color is not None and color.isValid():
            self.set_button_color(button, color)
            self.style_changed_handler() # Emit signal that style might have changed

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
        font_family = "Arial"
        selected_family_text = self.combo_font_family.currentText()
        font_style = "Regular"

        if selected_family_text == "Default (System Font)":
            font_family = self._default_style.get('font_family', "Arial")
            font_style = self._default_style.get('font_style', "Regular")
        elif selected_family_text in self.font_styles:
            font_family = selected_family_text
            if self.font_style_widget.isVisible() and self.combo_font_style.count() > 0:
                font_style = self.combo_font_style.currentText()
            else:
                font_style = self.font_styles[font_family][0] if self.font_styles[font_family] else "Regular"
        else:
            font_family = selected_family_text

        style = {
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
                'midpoint': self.spin_bg_gradient_midpoint.value(),
            },
            'text_color_type': 'solid' if self.combo_text_color_type.currentIndex() == 0 else 'linear_gradient',
            'text_color': self._get_color_from_button(self.btn_text_color).name(QColor.HexArgb),
            'text_gradient': {
                'color1': self._get_color_from_button(self.btn_text_gradient_color1).name(QColor.HexArgb),
                'color2': self._get_color_from_button(self.btn_text_gradient_color2).name(QColor.HexArgb),
                'direction': self.combo_text_gradient_direction.currentIndex(),
                'midpoint': self.spin_text_gradient_midpoint.value(),
            },
            'font_family': font_family,
            'font_style': font_style,
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
        self.update_style_panel(self._default_style)
        self.style_changed_handler()

    def update_style_panel(self, style_dict_in):
        if not style_dict_in:
            style_dict = self._default_style
        else:
            style_dict = self._ensure_gradient_defaults(style_dict_in)

        self._updating_controls = True
        self.selected_style_info = style_dict

        self.combo_bubble_type.setCurrentIndex(style_dict.get('bubble_type', 1))
        self.spin_corner_radius.setValue(style_dict.get('corner_radius', 50))
        self.spin_border_width.setValue(style_dict.get('border_width', 1))
        self.set_button_color(self.btn_border_color, style_dict.get('border_color', '#ff000000'))

        fill_type = style_dict.get('fill_type', 'solid')
        self.combo_fill_type.setCurrentIndex(1 if fill_type == 'linear_gradient' else 0)
        self.set_button_color(self.btn_bg_color, style_dict.get('bg_color', '#ffffffff'))
        bg_gradient = style_dict.get('bg_gradient', DEFAULT_GRADIENT)
        self.set_button_color(self.btn_bg_gradient_color1, bg_gradient.get('color1'))
        self.set_button_color(self.btn_bg_gradient_color2, bg_gradient.get('color2'))
        self.combo_bg_gradient_direction.setCurrentIndex(bg_gradient.get('direction'))
        self.spin_bg_gradient_midpoint.setValue(int(bg_gradient.get('midpoint', 50)))

        text_color_type = style_dict.get('text_color_type', 'solid')
        self.combo_text_color_type.setCurrentIndex(1 if text_color_type == 'linear_gradient' else 0)
        self.set_button_color(self.btn_text_color, style_dict.get('text_color', '#ff000000'))
        text_gradient = style_dict.get('text_gradient', DEFAULT_GRADIENT)
        self.set_button_color(self.btn_text_gradient_color1, text_gradient.get('color1'))
        self.set_button_color(self.btn_text_gradient_color2, text_gradient.get('color2'))
        self.combo_text_gradient_direction.setCurrentIndex(text_gradient.get('direction'))
        self.spin_text_gradient_midpoint.setValue(int(text_gradient.get('midpoint', 50)))

        font_family = style_dict.get('font_family', "Arial")
        font_style = style_dict.get('font_style', 'Regular')

        index = self.combo_font_family.findText(font_family)
        if index != -1:
            self.combo_font_family.setCurrentIndex(index)
        else:
            default_index = self.combo_font_family.findText("Default (System Font)")
            self.combo_font_family.setCurrentIndex(default_index if default_index != -1 else 0)
            print(f"Warning: Font family '{font_family}' not found, using default.")
            font_family = self.combo_font_family.currentText()

        if self.font_style_widget.isVisible():
            style_index = self.combo_font_style.findText(font_style)
            if style_index != -1:
                self.combo_font_style.setCurrentIndex(style_index)
            elif self.combo_font_style.count() > 0:
                self.combo_font_style.setCurrentIndex(0)
                print(f"Warning: Font style '{font_style}' not found for family '{font_family}', using first available.")

        self.spin_font_size.setValue(style_dict.get('font_size', 12))
        self.btn_font_bold.setChecked(style_dict.get('font_bold', False))
        self.btn_font_italic.setChecked(style_dict.get('font_italic', False))
        alignment_index = style_dict.get('text_alignment', 1)
        self.combo_text_alignment.setCurrentIndex(alignment_index)
        self.radio_align_left.setChecked(alignment_index == 0)
        self.radio_align_center.setChecked(alignment_index == 1)
        self.radio_align_right.setChecked(alignment_index == 2)
        self.chk_auto_font_size.setChecked(style_dict.get('auto_font_size', True))

        self._toggle_fill_gradient_controls()
        self._toggle_text_gradient_controls()

        self._updating_controls = False
        if style_dict_in: self.show()

    def clear_and_hide(self):
        self.selected_style_info = None
        self.hide()