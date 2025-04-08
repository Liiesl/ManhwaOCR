import os
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QLabel, QComboBox, QPushButton, QSlider, QColorDialog, QFrame, 
                             QGridLayout, QCheckBox, QSpinBox, QGroupBox, QFontComboBox, QHBoxLayout, QScrollArea)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QColor, QFont, QFontDatabase
import qtawesome as qta
from assets.styles import TEXT_BOX_STYLE_PANEL_STYLESHEET

class TextBoxStylePanel(QWidget):
    """
    A panel for customizing the appearance of a selected TextBoxItem.
    """
    # Add signals to communicate style changes
    style_changed = pyqtSignal(dict)
    
    def __init__(self, parent=None, default_style=None):
        super().__init__(parent)
        self.setObjectName("TextBoxStylePanel") # For styling
        self.setMinimumWidth(300)
        self._default_style = default_style if default_style else {} # Store defaults
        self.init_ui()
        self.selected_text_box_info = None # To store info about the selected box
        self._updating_controls = False # Flag to prevent recursive updates
        self.selected_style_info = None # Store the style dict when populated
            
    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(10)
        main_layout.setAlignment(Qt.AlignTop)

        # Header section with title
        header_layout = QHBoxLayout()
        title_label = QLabel("Text Box Styles")
        title_label.setObjectName("panelTitle")
        header_layout.addWidget(title_label)
        main_layout.addLayout(header_layout)
        
        # Divider after header
        header_divider = QFrame()
        header_divider.setObjectName("headerDivider")
        header_divider.setFrameShape(QFrame.HLine)
        header_divider.setFrameShadow(QFrame.Plain)
        main_layout.addWidget(header_divider)
        
        # Create scrollable area
        scroll_area = QScrollArea()
        scroll_area.setObjectName("styleScrollArea")
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.NoFrame)
        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)
        scroll_layout.setContentsMargins(0, 5, 5, 5)
        scroll_layout.setSpacing(12)
        
        # --- SHAPE & APPEARANCE SECTION ---
        shape_group = QGroupBox("Shape")
        shape_group.setObjectName("styleGroup")
        shape_layout = QVBoxLayout(shape_group)
        shape_layout.setContentsMargins(10, 15, 10, 10)
        shape_layout.setSpacing(8)
        
        # Bubble Type with icon
        type_layout = QHBoxLayout()
        bubble_type_label = QLabel("Type:")
        type_layout.addWidget(bubble_type_label, 1)
        self.combo_bubble_type = QComboBox()
        self.combo_bubble_type.setObjectName("styleCombo")
        self.combo_bubble_type.addItems(["Rectangle", "Rounded Rectangle", "Ellipse", "Speech Bubble"])
        self.combo_bubble_type.currentIndexChanged.connect(self.style_changed_handler)
        type_layout.addWidget(self.combo_bubble_type, 2)
        shape_layout.addLayout(type_layout)
        
        # Corner Radius with slider
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
        
        # --- FILL & STROKE SECTION ---
        color_group = QGroupBox("Fill & Stroke")
        color_group.setObjectName("styleGroup")
        color_layout = QVBoxLayout(color_group)
        color_layout.setContentsMargins(10, 15, 10, 10)
        color_layout.setSpacing(8)
        
        # Background Color
        bg_color_layout = QHBoxLayout()
        bg_color_label = QLabel("Fill:")
        bg_color_layout.addWidget(bg_color_label, 1)
        self.btn_bg_color = QPushButton("")
        self.btn_bg_color.setObjectName("colorButton")
        self.btn_bg_color.setFixedSize(32, 24)
        self.btn_bg_color.clicked.connect(self.choose_bg_color)
        self.set_button_color(self.btn_bg_color, QColor(255, 255, 255))
        bg_color_layout.addWidget(self.btn_bg_color, 2)
        color_layout.addLayout(bg_color_layout)

        # Border Width & Color combined row
        border_layout = QHBoxLayout()
        border_color_label = QLabel("Stroke:")
        border_layout.addWidget(border_color_label, 1)
        
        # Border width spinner
        self.spin_border_width = QSpinBox()
        self.spin_border_width.setObjectName("borderWidthSpinner")
        self.spin_border_width.setRange(0, 10)
        self.spin_border_width.setValue(1)
        self.spin_border_width.valueChanged.connect(self.style_changed_handler)
        border_layout.addWidget(self.spin_border_width)
        
        # Border color button
        self.btn_border_color = QPushButton("")
        self.btn_border_color.setObjectName("colorButton")
        self.btn_border_color.setFixedSize(32, 24)
        self.btn_border_color.clicked.connect(self.choose_border_color)
        self.set_button_color(self.btn_border_color, QColor(0, 0, 0))
        border_layout.addWidget(self.btn_border_color)
        
        color_layout.addLayout(border_layout)
        
        # Text Color
        text_color_layout = QHBoxLayout()
        text_color_label = QLabel("Text Color:")
        text_color_layout.addWidget(text_color_label, 1)
        self.btn_text_color = QPushButton("")
        self.btn_text_color.setObjectName("colorButton")
        self.btn_text_color.setFixedSize(32, 24)
        self.btn_text_color.clicked.connect(self.choose_text_color)
        self.set_button_color(self.btn_text_color, QColor(0, 0, 0))
        text_color_layout.addWidget(self.btn_text_color, 2)
        color_layout.addLayout(text_color_layout)
        
        scroll_layout.addWidget(color_group)
        
        # --- TYPOGRAPHY SECTION ---
        font_group = QGroupBox("Typography")
        font_group.setObjectName("styleGroup")
        font_layout = QVBoxLayout(font_group)
        font_layout.setContentsMargins(10, 15, 10, 10)
        font_layout.setSpacing(8)
        
        # Font Family
        font_family_layout = QHBoxLayout()
        font_family_label = QLabel("Font:")
        font_family_layout.addWidget(font_family_label, 1)
        self.combo_font_family = QComboBox()
        self.combo_font_family.setObjectName("styleCombo")
        self.load_custom_fonts()
        self.combo_font_family.currentIndexChanged.connect(self.style_changed_handler)
        font_family_layout.addWidget(self.combo_font_family, 2)
        font_layout.addLayout(font_family_layout)
        
        # Font Size and Style in one row
        font_props_layout = QHBoxLayout()
        
        # Font Size
        font_size_label = QLabel("Size:")
        font_props_layout.addWidget(font_size_label)
        self.spin_font_size = QSpinBox()
        self.spin_font_size.setObjectName("styleSpinBox")
        self.spin_font_size.setRange(6, 72)
        self.spin_font_size.setValue(12)
        self.spin_font_size.valueChanged.connect(self.style_changed_handler)
        font_props_layout.addWidget(self.spin_font_size)
        
        # Spacer between size and style buttons
        font_props_layout.addSpacing(10)
        
        # Bold button
        self.btn_font_bold = QCheckBox("")
        self.btn_font_bold.setObjectName("boldButton")
        self.btn_font_bold.setToolTip("Bold")
        self.btn_font_bold.stateChanged.connect(self.style_changed_handler)
        # Use Font Awesome for the icon
        bold_icon = qta.icon('fa5s.bold', color='white')
        self.btn_font_bold.setIcon(bold_icon)
        font_props_layout.addWidget(self.btn_font_bold)
        
        # Italic button
        self.btn_font_italic = QCheckBox("")
        self.btn_font_italic.setObjectName("italicButton")
        self.btn_font_italic.setToolTip("Italic")
        self.btn_font_italic.stateChanged.connect(self.style_changed_handler)
        # Use Font Awesome for the icon
        italic_icon = qta.icon('fa5s.italic', color='white')
        self.btn_font_italic.setIcon(italic_icon)
        font_props_layout.addWidget(self.btn_font_italic)
        
        font_props_layout.addStretch()
        font_layout.addLayout(font_props_layout)
        
        # Text Alignment
        alignment_layout = QHBoxLayout()
        alignment_label = QLabel("Alignment:")
        alignment_layout.addWidget(alignment_label, 1)
        
        # Use buttons with icons for alignment
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
        
        # Hidden combo box to store actual alignment value
        self.combo_text_alignment = QComboBox()
        self.combo_text_alignment.addItems(["Left", "Center", "Right"])
        self.combo_text_alignment.setCurrentIndex(1)  # Center is default
        self.combo_text_alignment.setVisible(False)
        font_layout.addWidget(self.combo_text_alignment)
        
        # Auto-size Text with switch-like checkbox
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
        
        # Add stretch to push content to top
        scroll_layout.addStretch()
        
        # Finish setting up the scroll area
        scroll_area.setWidget(scroll_content)
        main_layout.addWidget(scroll_area)
        
        # Button bar at bottom
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

        # Define centralized stylesheet
        self.setStyleSheet("""
            #TextBoxStylePanel {
                background-color: #2A2A2A; 
                border-left: 1px solid #3A3A3A;
            }
            
            #panelTitle {
                color: #FFFFFF;
                font-size: 24px;
                font-weight: bold;
                padding-bottom: 8px;
            }
            
            #headerDivider {
                background-color: #3A3A3A;
                max-height: 1px;
                margin-bottom: 8px;
            }
            
            #styleScrollArea {
                background-color: transparent;
                border: none;
            }
            
            #styleGroup {
                color: #FFFFFF;
                font-size: 20px;
                font-weight: bold;
                border: 1px solid #3A3A3A;
                border-radius: 4px;
                margin-top: 12px;
                background-color: #2D2D2D;
            }
            
            #styleGroup::title {
                subcontrol-origin: margin;
                subcontrol-position: top left;
                padding: 0 8px;
                left: 12px;
            }
            
            QLabel {
                color: #CCCCCC;
                font-size: 20px;
            }
            
            #styleCombo, #styleSpinBox {
                background-color: #3A3A3A;
                color: #FFFFFF;
                border: 1px solid #4A4A4A;
                padding: 5px;
                border-radius: 3px;
                min-height: 24px;
                font-size: 20px;
            }
            
            #styleCombo:hover, #styleSpinBox:hover {
                border: 1px solid #5A5A5A;
            }
            
            #styleCombo::drop-down {
                border: none;
                width: 20px;
            }
            
            #styleCombo QAbstractItemView {
                background-color: #3A3A3A;
                color: #FFFFFF;
                selection-background-color: #4A4A4A;
            }
            
            #colorButton {
                border: 1px solid #4A4A4A;
                border-radius: 3px;
            }
            
            #colorButton:hover {
                border: 1px solid #6A6A6A;
            }
            
            #boldButton, #italicButton, #alignButton {
                background-color: #3A3A3A;
                border: 1px solid #4A4A4A;
                border-radius: 3px;
                padding: 3px;
                width: 28px;
                height: 24px;
            }
            
            #boldButton:checked, #italicButton:checked, #alignButton:checked {
                background-color: #505050;
                border: 1px solid #6A6A6A;
            }
            
            #toggleSwitch {
                width: 44px;
                height: 22px;
            }
            
            #toggleSwitch::indicator {
                width: 44px;
                height: 22px;
                border-radius: 11px;
            }
            
            #toggleSwitch::indicator:unchecked {
                background-color: #3A3A3A;
                border: 1px solid #4A4A4A;
            }
            
            #toggleSwitch::indicator:unchecked:hover {
                background-color: #404040;
                border: 1px solid #5A5A5A;
            }
            
            #toggleSwitch::indicator:checked {
                background-color: #007ACC;
                border: 1px solid #0088EE;
            }
            
            #buttonContainer {
                border-top: 1px solid #3A3A3A;
                padding-top: 10px;
            }
            
            #resetButton, #applyButton {
                background-color: #3A3A3A;
                color: #FFFFFF;
                border: none;
                padding: 8px 15px;
                border-radius: 3px;
                font-size: 20px;
                min-width: 80px;
            }
            
            #resetButton:hover {
                background-color: #4A4A4A;
            }
            
            #applyButton {
                background-color: #007ACC;
            }
            
            #applyButton:hover {
                background-color: #0088EE;
            }
            
            #borderWidthSpinner {
                background-color: #3A3A3A;
                color: #FFFFFF;
                border: 1px solid #4A4A4A;
                border-radius: 3px;
                padding: 5px;
                max-width: 45px;
            }
        """)
        
    # We'll need to add this helper method for the alignment radio buttons
    def set_alignment(self, index):
        # Update the hidden combo box and deselect other radio buttons
        self.combo_text_alignment.setCurrentIndex(index)
        self.radio_align_left.setChecked(index == 0)
        self.radio_align_center.setChecked(index == 1)
        self.radio_align_right.setChecked(index == 2)
        self.style_changed_handler()

    def load_custom_fonts(self):
        """Load all .ttf and .otf fonts from the assets/fonts directory"""
        # Clear existing fonts dictionary
        self.custom_fonts = {}
        self.combo_font_family.clear()
        
        # Default font
        self.combo_font_family.addItem("Default (System Font)")
        
        # Check if the fonts directory exists
        fonts_dir = "assets/fonts"
        if not os.path.exists(fonts_dir):
            print(f"Warning: Font directory {fonts_dir} not found.")
            return
            
        # Find all font files
        font_files = []
        for file in os.listdir(fonts_dir):
            if file.lower().endswith(('.ttf', '.otf')):
                font_files.append(os.path.join(fonts_dir, file))
                
        # Load each font
        for font_path in font_files:
            font_id = QFontDatabase.addApplicationFont(font_path)
            if font_id != -1:
                font_families = QFontDatabase.applicationFontFamilies(font_id)
                for family in font_families:
                    self.custom_fonts[family] = font_id
                    self.combo_font_family.addItem(family)
                    print(f"Loaded font: {family} from {font_path}")
            else:
                filename = os.path.basename(font_path)
                print(f"Failed to load font: {filename}")
                
        # Set the default selection to the first custom font if available
        if self.combo_font_family.count() > 1:
            self.combo_font_family.setCurrentIndex(1)  # Select first custom font

    def set_button_color(self, button, color):
        """Set the background color of a button to visualize the selected color."""
        # Ensure color is a valid QColor object
        if not isinstance(color, QColor):
            try:
                color = QColor(color) # Try converting from string
            except:
                print(f"Warning: Invalid color value for button: {color}")
                color = QColor(255, 255, 255) # Default to white on error

        button.setStyleSheet(f"""
            QPushButton {{
                background-color: {color.name(QColor.HexArgb)};
                border: 1px solid #60666E;
                border-radius: 3px;
            }}
        """)

    def choose_bg_color(self):
        current_color = self._get_color_from_button(self.btn_bg_color)
        color = QColorDialog.getColor(initial=current_color)
        if color.isValid():
            self.set_button_color(self.btn_bg_color, color)
            self.style_changed_handler()

    def choose_border_color(self):
        current_color = self._get_color_from_button(self.btn_border_color)
        color = QColorDialog.getColor(initial=current_color)
        if color.isValid():
            self.set_button_color(self.btn_border_color, color)
            self.style_changed_handler()

    def choose_text_color(self):
        current_color = self._get_color_from_button(self.btn_text_color)
        color = QColorDialog.getColor(initial=current_color)
        if color.isValid():
            self.set_button_color(self.btn_text_color, color)
            self.style_changed_handler()

        # Helper to get QColor from button's style
    def _get_color_from_button(self, button):
        style = button.styleSheet()
        try:
            bg_color_start = style.find("background-color:") + len("background-color:")
            bg_color_end = style.find(";", bg_color_start)
            color_str = style[bg_color_start:bg_color_end].strip()
            return QColor(color_str)
        except:
            return QColor(0,0,0) # Default black on error

    def get_current_style(self):
        """Get the current style settings as a dictionary with color strings."""
        # Get font family
        font_family = "Default (System Font)" # Default placeholder
        selected_text = self.combo_font_family.currentText()
        if selected_text != "Default (System Font)":
            font_family = selected_text
            # Use a known default if "Default" is selected but not meant literally
        elif self.combo_font_family.currentIndex() == 0 and self._default_style:
            font_family = self._default_style.get('font_family', "Arial") # Get default font


        style_dict = {
            'bubble_type': self.combo_bubble_type.currentIndex(),
            'corner_radius': self.spin_corner_radius.value(),
            # Store colors as HexArgb strings
            'bg_color': self._get_color_from_button(self.btn_bg_color).name(QColor.HexArgb),
            'border_color': self._get_color_from_button(self.btn_border_color).name(QColor.HexArgb),
            'text_color': self._get_color_from_button(self.btn_text_color).name(QColor.HexArgb),
            'border_width': self.spin_border_width.value(),
            'font_family': font_family,
            'font_size': self.spin_font_size.value(),
            'font_bold': self.btn_font_bold.isChecked(),
            'font_italic': self.btn_font_italic.isChecked(),
            'text_alignment': self.combo_text_alignment.currentIndex(),
            'auto_font_size': self.chk_auto_font_size.isChecked(),
        }
        return style_dict
        
    def style_changed_handler(self):
        """Handle any style control change."""
        if not self._updating_controls and self.selected_style_info is not None: # Check if populated
            current_style = self.get_current_style()
            # Only emit if the style actually changed from what was loaded
            # This prevents loops on initial population
            # Note: Direct dict comparison might be tricky with QColor vs string.
            # A simpler check might be needed, or rely on _updating_controls flag mostly.
            self.style_changed.emit(current_style)
    
    def apply_style(self):
        """Apply current style settings to the selected text box."""
        if self.selected_style_info is not None:
            self.style_changed.emit(self.get_current_style())
    
    def reset_style(self):
        """Reset controls to default."""
        if not self._default_style:
            print("Warning: Cannot reset style, default style not provided.")
            return

        self._updating_controls = True

        # Use the stored _default_style dictionary
        self.combo_bubble_type.setCurrentIndex(self._default_style.get('bubble_type', 1))
        self.spin_corner_radius.setValue(self._default_style.get('corner_radius', 50))

        self.set_button_color(self.btn_bg_color, QColor(self._default_style.get('bg_color', '#ffffffff')))
        self.set_button_color(self.btn_border_color, QColor(self._default_style.get('border_color', '#ff000000')))
        self.set_button_color(self.btn_text_color, QColor(self._default_style.get('text_color', '#ff000000')))
        self.spin_border_width.setValue(self._default_style.get('border_width', 1))

        default_font_family = self._default_style.get('font_family', "Arial")
        index = self.combo_font_family.findText(default_font_family)
        if index != -1:
            self.combo_font_family.setCurrentIndex(index)
        else:
             # Try adding default font if missing and path known (e.g., Anime Ace)
            font_path = "assets/fonts/animeace.ttf" # Example path
            if os.path.exists(font_path) and default_font_family == "Anime Ace 2.0 BB":
                 font_id = QFontDatabase.addApplicationFont(font_path)
                 if font_id != -1:
                     families = QFontDatabase.applicationFontFamilies(font_id)
                     if families:
                         self.custom_fonts[families[0]] = font_id
                         self.combo_font_family.addItem(families[0])
                         self.combo_font_family.setCurrentText(families[0])
                     else:
                          self.combo_font_family.setCurrentIndex(0) # Fallback to system default
                 else:
                     self.combo_font_family.setCurrentIndex(0) # Fallback
            else:
                 self.combo_font_family.setCurrentIndex(0) # Fallback

        self.spin_font_size.setValue(self._default_style.get('font_size', 12))
        self.btn_font_bold.setChecked(self._default_style.get('font_bold', False))
        self.btn_font_italic.setChecked(self._default_style.get('font_italic', False))
        self.combo_text_alignment.setCurrentIndex(self._default_style.get('text_alignment', 1))
        self.chk_auto_font_size.setChecked(self._default_style.get('auto_font_size', True))

        self._updating_controls = False

        # Emit the reset style
        self.style_changed_handler()

    # Modify update_style_panel to accept a style dictionary
    def update_style_panel(self, style_dict):
        """
        Populates the panel controls with the given style properties.
        """
        if not style_dict:
            self.clear_and_hide()
            return

        self._updating_controls = True
        self.selected_style_info = style_dict # Store the passed style

        # Populate controls from the style_dict
        self.combo_bubble_type.setCurrentIndex(style_dict.get('bubble_type', 1))
        self.spin_corner_radius.setValue(style_dict.get('corner_radius', 50))

        # Handle colors (convert QColor/string to QColor for button)
        self.set_button_color(self.btn_bg_color, style_dict.get('bg_color', QColor(255, 255, 255)))
        self.set_button_color(self.btn_border_color, style_dict.get('border_color', QColor(0, 0, 0)))
        self.set_button_color(self.btn_text_color, style_dict.get('text_color', QColor(0, 0, 0)))

        self.spin_border_width.setValue(style_dict.get('border_width', 1))

        # Font family
        font_family = style_dict.get('font_family', "Arial")
        index = self.combo_font_family.findText(font_family)
        if index != -1:
            self.combo_font_family.setCurrentIndex(index)
        else:
            print(f"Warning: Font '{font_family}' not found in dropdown, using default.")
            self.combo_font_family.setCurrentIndex(0) # Fallback to "Default (System Font)"

        self.spin_font_size.setValue(style_dict.get('font_size', 12))
        self.btn_font_bold.setChecked(style_dict.get('font_bold', False))
        self.btn_font_italic.setChecked(style_dict.get('font_italic', False))
        self.combo_text_alignment.setCurrentIndex(style_dict.get('text_alignment', 1))
        self.chk_auto_font_size.setChecked(style_dict.get('auto_font_size', True))

        self._updating_controls = False
        self.show() # Ensure panel is visible

    def clear_and_hide(self):
        """Clears selection info and hides the panel."""
        self.selected_text_box_info = None
        self.hide()