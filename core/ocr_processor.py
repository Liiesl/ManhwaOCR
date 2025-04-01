from PyQt5.QtCore import QThread, pyqtSignal
import easyocr
import numpy as np
from PIL import Image
from core.data_processing import group_and_merge_text

class OCRProcessor(QThread):
    ocr_progress = pyqtSignal(int)  # Progress for the current image
    ocr_finished = pyqtSignal(list)  # Results for the current image
    error_occurred = pyqtSignal(str)

    def __init__(self, image_path, reader, min_text_height, max_text_height, min_confidence):
        super().__init__()
        self.image_path = image_path
        self.reader = reader  # Reuse the existing reader
        self.stop_requested = False  # Add stop flag
        self.min_text_height = min_text_height  # Changed from area to height
        self.max_text_height = max_text_height  # Changed from area to height
        self.min_confidence = min_confidence

    def run(self):
        try:
            # Preprocess the image
            print("preprocessing the image...")
            img = Image.open(self.image_path)
            # Convert to grayscale
            img = img.convert('L')
            # Resize to max width 1024 while maintaining aspect ratio
            max_width = 1024
            w, h = img.size
            if w > max_width:
                ratio = max_width / w
                new_h = int(h * ratio)
                img = img.resize((max_width, new_h), Image.Resampling.LANCZOS)
            # Convert to numpy array for EasyOCR
            img_np = np.array(img)
            # Process the preprocessed image
            print("Starting OCR processing...")
            results = self.reader.readtext(
                img_np,
                batch_size=3,        # Process multiple text regions in parallel
                adjust_contrast=0.5, # Improve contrast for low-quality images
                decoder='beamsearch',    # Faster decoding (trade accuracy for speed)
                detail=1
            )
            # Scale coordinates back to original size
            if w != img.width:  # Only if resized
                scale_x = w / img.width
                scale_y = h / img.height
                for result in results:
                    result[0] = [[x * scale_x, y * scale_y] for (x, y) in result[0]]
            # Format results with coordinates and text
            formatted = []
            for i, (coord, text, confidence) in enumerate(results):
                if self.stop_requested:  # Check stop flag
                    print("OCR stopped by user")
                    break

                # Calculate the area of the bounding box
                x_coords = [p[0] for p in coord]
                y_coords = [p[1] for p in coord]

                # Exclude small text regions (e.g., watermarks)
                height = max(y_coords) - min(y_coords)
                if (self.min_text_height <= height <= self.max_text_height and 
                    confidence >= self.min_confidence):
                    formatted.append({
                        'coordinates': [[int(x), int(y)] for x, y in coord],
                        'text': text,
                        'confidence': confidence
                    })
                else:
                    # Update exclusion message
                    exclusion_reasons = []
                    if height < self.min_text_height:
                        exclusion_reasons.append("short")
                    if height > self.max_text_height:
                        exclusion_reasons.append("tall")
                    if confidence < self.min_confidence:
                        exclusion_reasons.append(f"low confidence ({confidence:.2f})")
                    
                    if exclusion_reasons:
                        print(f"Excluded {'/'.join(exclusion_reasons)} text region: {text}")

                self.ocr_progress.emit(int((i + 1) / len(results) * 100))  # 0-100% for current image
                print(f"Processed OCR result {i + 1}/{len(results)}")

            print("OCR processing completed.")
            self.ocr_finished.emit(formatted)
        except Exception as e:
            print(f"OCR error: {str(e)}")
            self.error_occurred.emit(f"OCR error: {str(e)}")
