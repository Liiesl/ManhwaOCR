import os
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QLabel, QComboBox, QPushButton, QSlider, QColorDialog, QFrame, 
                             QGridLayout, QCheckBox, QSpinBox, QGroupBox, QFontComboBox, QHBoxLayout)
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
        self.setMinimumWidth(250)
        self._default_style = default_style if default_style else {} # Store defaults
        self.init_ui()
        self.selected_text_box_info = None # To store info about the selected box
        self._updating_controls = False # Flag to prevent recursive updates
        self.selected_style_info = None # Store the style dict when populated

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(15)
        main_layout.setAlignment(Qt.AlignTop) # Align controls to the top

        # Title Label
        title_label = QLabel("Text Box Style")
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        main_layout.addWidget(title_label)

        # Separator
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setFrameShadow(QFrame.Sunken)
        main_layout.addWidget(separator)

        # Create scrollable area for many controls
        from PyQt5.QtWidgets import QScrollArea
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)
        scroll_layout.setContentsMargins(5, 5, 5, 5)
        scroll_layout.setSpacing(10)
        
        # --- Shape and Appearance ---
        appearance_group = QGroupBox("Shape & Appearance")
        appearance_layout = QVBoxLayout()
        appearance_group.setLayout(appearance_layout)
        
        # Bubble Type
        bubble_type_label = QLabel("Bubble Type:")
        appearance_layout.addWidget(bubble_type_label)
        self.combo_bubble_type = QComboBox()
        self.combo_bubble_type.addItems(["Rectangle", "Rounded Rectangle", "Ellipse", "Speech Bubble"])
        self.combo_bubble_type.currentIndexChanged.connect(self.style_changed_handler)
        appearance_layout.addWidget(self.combo_bubble_type)
        
        # Corner Radius (for rounded rectangles)
        corner_radius_layout = QHBoxLayout()
        corner_radius_label = QLabel("Corner Radius:")
        corner_radius_layout.addWidget(corner_radius_label)
        self.spin_corner_radius = QSpinBox()
        self.spin_corner_radius.setRange(0, 100)
        self.spin_corner_radius.setValue(50)  # Default from widgets.py
        self.spin_corner_radius.valueChanged.connect(self.style_changed_handler)
        corner_radius_layout.addWidget(self.spin_corner_radius)
        appearance_layout.addLayout(corner_radius_layout)
        
        scroll_layout.addWidget(appearance_group)
        
        # --- Color Settings ---
        color_group = QGroupBox("Colors")
        color_layout = QVBoxLayout()
        color_group.setLayout(color_layout)
        
        # Background Color
        bg_color_layout = QHBoxLayout()
        bg_color_label = QLabel("Background:")
        bg_color_layout.addWidget(bg_color_label)
        self.btn_bg_color = QPushButton("")
        self.btn_bg_color.setFixedSize(24, 24)
        self.btn_bg_color.clicked.connect(self.choose_bg_color)
        self.set_button_color(self.btn_bg_color, QColor(255, 255, 255))  # Default white
        bg_color_layout.addWidget(self.btn_bg_color)
        color_layout.addLayout(bg_color_layout)

        # Border Color
        border_color_layout = QHBoxLayout()
        border_color_label = QLabel("Border:")
        border_color_layout.addWidget(border_color_label)
        self.btn_border_color = QPushButton("")
        self.btn_border_color.setFixedSize(24, 24)
        self.btn_border_color.clicked.connect(self.choose_border_color)
        self.set_button_color(self.btn_border_color, QColor(0, 0, 0))  # Default black
        border_color_layout.addWidget(self.btn_border_color)
        color_layout.addLayout(border_color_layout)
        
        # Text Color
        text_color_layout = QHBoxLayout()
        text_color_label = QLabel("Text:")
        text_color_layout.addWidget(text_color_label)
        self.btn_text_color = QPushButton("")
        self.btn_text_color.setFixedSize(24, 24)
        self.btn_text_color.clicked.connect(self.choose_text_color)
        self.set_button_color(self.btn_text_color, QColor(0, 0, 0))  # Default black
        text_color_layout.addWidget(self.btn_text_color)
        color_layout.addLayout(text_color_layout)
        
        # Border Thickness
        border_thick_layout = QHBoxLayout()
        border_thick_label = QLabel("Border Width:")
        border_thick_layout.addWidget(border_thick_label)
        self.spin_border_width = QSpinBox()
        self.spin_border_width.setRange(0, 10)
        self.spin_border_width.setValue(1)  # Default from widgets.py
        self.spin_border_width.valueChanged.connect(self.style_changed_handler)
        border_thick_layout.addWidget(self.spin_border_width)
        color_layout.addLayout(border_thick_layout)
        
        scroll_layout.addWidget(color_group)
        
        # --- Font Settings ---
        font_group = QGroupBox("Font")
        font_layout = QVBoxLayout()
        font_group.setLayout(font_layout)
        
        # Font Family - Using custom combo box instead of QFontComboBox
        font_family_label = QLabel("Font Family:")
        font_layout.addWidget(font_family_label)
        self.combo_font_family = QComboBox()
        
        # Load custom fonts from assets/fonts directory
        self.load_custom_fonts()
        
        self.combo_font_family.currentIndexChanged.connect(self.style_changed_handler)
        font_layout.addWidget(self.combo_font_family)
        
        # Font Size
        font_size_layout = QHBoxLayout()
        font_size_label = QLabel("Size:")
        font_size_layout.addWidget(font_size_label)
        self.spin_font_size = QSpinBox()
        self.spin_font_size.setRange(6, 72)
        self.spin_font_size.setValue(12)  # Default from widgets.py
        self.spin_font_size.valueChanged.connect(self.style_changed_handler)
        font_size_layout.addWidget(self.spin_font_size)
        font_layout.addLayout(font_size_layout)
        
        # Font Style Options
        style_options_layout = QHBoxLayout()
        
        self.chk_font_bold = QCheckBox("Bold")
        self.chk_font_bold.stateChanged.connect(self.style_changed_handler)
        style_options_layout.addWidget(self.chk_font_bold)
        
        self.chk_font_italic = QCheckBox("Italic")
        self.chk_font_italic.stateChanged.connect(self.style_changed_handler)
        style_options_layout.addWidget(self.chk_font_italic)
        
        font_layout.addLayout(style_options_layout)
        
        # Text Alignment
        alignment_label = QLabel("Text Alignment:")
        font_layout.addWidget(alignment_label)
        self.combo_text_alignment = QComboBox()
        self.combo_text_alignment.addItems(["Left", "Center", "Right"])
        self.combo_text_alignment.setCurrentIndex(1)  # Center is default in widgets.py
        self.combo_text_alignment.currentIndexChanged.connect(self.style_changed_handler)
        font_layout.addWidget(self.combo_text_alignment)
        
        # Auto-size Text to Fit
        self.chk_auto_font_size = QCheckBox("Auto-adjust font size")
        self.chk_auto_font_size.setChecked(True)  # Default from widgets.py
        self.chk_auto_font_size.stateChanged.connect(self.style_changed_handler)
        font_layout.addWidget(self.chk_auto_font_size)
        
        scroll_layout.addWidget(font_group)
        
        # Add stretch to push content to top
        scroll_layout.addStretch()
        
        # Finish setting up the scroll area
        scroll_area.setWidget(scroll_content)
        main_layout.addWidget(scroll_area)
        
        # Apply/Reset buttons
        button_layout = QHBoxLayout()
        self.btn_reset = QPushButton("Reset")
        self.btn_reset.clicked.connect(self.reset_style)
        button_layout.addWidget(self.btn_reset)
        
        self.btn_apply = QPushButton("Apply")
        self.btn_apply.clicked.connect(self.apply_style)
        button_layout.addWidget(self.btn_apply)
        main_layout.addLayout(button_layout)

        # Apply some basic styling
        self.setStyleSheet(TEXT_BOX_STYLE_PANEL_STYLESHEET)

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
            'font_bold': self.chk_font_bold.isChecked(),
            'font_italic': self.chk_font_italic.isChecked(),
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
        self.chk_font_bold.setChecked(self._default_style.get('font_bold', False))
        self.chk_font_italic.setChecked(self._default_style.get('font_italic', False))
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
        self.chk_font_bold.setChecked(style_dict.get('font_bold', False))
        self.chk_font_italic.setChecked(style_dict.get('font_italic', False))
        self.combo_text_alignment.setCurrentIndex(style_dict.get('text_alignment', 1))
        self.chk_auto_font_size.setChecked(style_dict.get('auto_font_size', True))

        self._updating_controls = False
        self.show() # Ensure panel is visible

    def clear_and_hide(self):
        """Clears selection info and hides the panel."""
        self.selected_text_box_info = None
        self.hide()