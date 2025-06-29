from app.images.image_area import ResizableImageLabel
from app.ui_widget import CustomProgressBar, MenuBar, CustomScrollArea
from app.results_widget import ResultsWidget
from app.images.custom_bubble import TextBoxStylePanel
from app.find_replace import FindReplaceWidget
from app.combined_button import ImportExportMenu, SaveMenu
from app.ocr_batch_handler import BatchOCRHandler # <-- ADD THIS IMPORT
from app.project_model import ProjectLoader
from app.manual_ocr_handler import ManualOCRHandler