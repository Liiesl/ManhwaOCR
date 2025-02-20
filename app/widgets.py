from PyQt5.QtWidgets import QLabel, QGraphicsScene, QGraphicsPixmapItem, QGraphicsBlurEffect
from PyQt5.QtCore import Qt, QRect, QThread, pyqtSignal
from PyQt5.QtGui import QPixmap, QPainter, QFont, QResizeEvent

class TranslationWorker(QThread):
    """
    A worker thread to handle the translation task.
    """
    finished = pyqtSignal(QPixmap)

    def __init__(self, original_pixmap, text_entries):
        super().__init__()
        self.original_pixmap = original_pixmap
        self.text_entries = text_entries

    def run(self):
        try:
            # Create a copy of the original pixmap
            current_pixmap = QPixmap(self.original_pixmap)
            
            # Create the main painter
            painter = QPainter()
            painter.begin(current_pixmap)
            
            # Background and blur parameters
            padding = 20
            blur_radius = 20

            for entry in self.text_entries.values():  # Iterate through the dictionary values
                coords = entry['coordinates']
                text = entry['text']
                line_counts = entry.get('line_counts', 1)

                # Extract bounding box coordinates
                x_coords = [p[0] for p in coords]
                y_coords = [p[1] for p in coords]
                x_min = min(x_coords)
                y_min = min(y_coords)
                x_max = max(x_coords)
                y_max = max(y_coords)

                # Calculate bounding box dimensions
                bbox_width = x_max - x_min
                bbox_height = y_max - y_min

                # Split text into lines
                words = text.split()
                total_words = len(words)
                lines = []
                words_per_line = max(1, total_words // line_counts)
                remainder = total_words % line_counts
                word_index = 0
                
                for i in range(line_counts):
                    line = ""
                    words_in_this_line = words_per_line + (1 if i < remainder else 0)
                    for _ in range(words_in_this_line):
                        if word_index < len(words):
                            line += words[word_index] + " "
                            word_index += 1
                    lines.append(line.strip())

                # Find optimal font size
                def find_optimal_font_size(lines, max_width, max_height):
                    font_size = 1
                    while True:
                        font = QFont("Arial", font_size)
                        painter.setFont(font)
                        font_metrics = painter.fontMetrics()
                        total_height = len(lines) * font_metrics.height()
                        max_line_width = max(font_metrics.horizontalAdvance(line) for line in lines)
                        if max_line_width > max_width or total_height > max_height:
                            break
                        font_size += 1
                    return max(1, font_size - 1)

                optimal_font_size = find_optimal_font_size(
                    lines,
                    bbox_width - 2 * padding,
                    bbox_height - 2 * padding
                )
                
                font = QFont("Arial", optimal_font_size)
                painter.setFont(font)
                font_metrics = painter.fontMetrics()

                # Calculate text dimensions
                line_height = font_metrics.height()
                total_text_height = len(lines) * line_height

                # Calculate background dimensions
                bg_width = max(font_metrics.horizontalAdvance(line) for line in lines) + 2 * padding
                bg_height = total_text_height + 2 * padding

                # Center the text box
                bg_x = max(0, x_min + (bbox_width - bg_width) // 2)
                bg_y = max(0, y_min + (bbox_height - bg_height) // 2)

                # Create and setup temporary pixmap for blur
                temp_pixmap = QPixmap(bg_width + 2 * blur_radius, bg_height + 2 * blur_radius)
                temp_pixmap.fill(Qt.transparent)

                # Draw background on temp pixmap
                temp_painter = QPainter()
                temp_painter.begin(temp_pixmap)
                temp_painter.setRenderHint(QPainter.Antialiasing)
                temp_painter.setBrush(Qt.white)
                temp_painter.setPen(Qt.NoPen)
                temp_painter.drawRoundedRect(
                    blur_radius, blur_radius,
                    bg_width, bg_height,
                    padding, padding
                )
                temp_painter.end()

                # Apply blur effect
                blurred_pixmap = QPixmap(temp_pixmap.size())
                blurred_pixmap.fill(Qt.transparent)
                
                blur_painter = QPainter()
                blur_painter.begin(blurred_pixmap)
                
                scene = QGraphicsScene()
                item = QGraphicsPixmapItem(temp_pixmap)
                blur_effect = QGraphicsBlurEffect()
                blur_effect.setBlurRadius(blur_radius)
                item.setGraphicsEffect(blur_effect)
                scene.addItem(item)
                
                scene.render(blur_painter)
                blur_painter.end()

                # Draw blurred background
                painter.drawPixmap(
                    bg_x - blur_radius,
                    bg_y - blur_radius,
                    blurred_pixmap
                )

                # Draw text
                for i, line in enumerate(lines):
                    text_rect = QRect(bg_x, bg_y + i * line_height, bg_width, line_height)
                    painter.setPen(Qt.black)
                    painter.drawText(text_rect, Qt.AlignCenter | Qt.TextWordWrap, line)

            # Ensure the main painter is properly ended
            painter.end()
            
            # Emit the result
            self.finished.emit(current_pixmap)
            
        except Exception as e:
            print(f"Error in translation worker: {str(e)}")
            # Emit the original pixmap in case of error
            self.finished.emit(self.original_pixmap)

class ResizableImageLabel(QLabel):
    def __init__(self, pixmap, filename):
        super().__init__()
        self.setStyleSheet("background-color: transparent;")  # Add this line
        self.original_pixmap = pixmap
        self.current_pixmap = self.original_pixmap.copy()
        self.filename = filename
        self.setAlignment(Qt.AlignTop)
        self.setPixmap(self.current_pixmap)
        self.worker_thread = None
        

    def apply_translation(self, text_entries):
        # Clean up any existing worker thread
        if self.worker_thread is not None:
            if self.worker_thread.isRunning():
                self.worker_thread.quit()
                self.worker_thread.wait()
            self.worker_thread.deleteLater()
            self.worker_thread = None

        # Create and start new worker thread
        self.worker_thread = TranslationWorker(self.original_pixmap, text_entries)
        self.worker_thread.finished.connect(self.update_display)
        self.worker_thread.start()
    
    def resizeEvent(self, event: QResizeEvent):
        scaled_pixmap = self.current_pixmap.scaledToWidth(self.width(), Qt.SmoothTransformation)
        self.setPixmap(scaled_pixmap)

    def update_display(self, pixmap):
        self.current_pixmap = pixmap
        scaled_pixmap = self.current_pixmap.scaledToWidth(self.width(), Qt.SmoothTransformation)
        self.setPixmap(scaled_pixmap)

    def get_updated_image_path(self):
        """Save the current pixmap to a temporary file and return its path."""
        temp_path = f"translated_{self.filename}"
        self.current_pixmap.save(temp_path)
        return temp_path

    def cleanup(self):
        if self.worker_thread is not None:
            self.worker_thread.quit()
            self.worker_thread.wait()
            self.worker_thread.deleteLater()
            self.worker_thread = None

    def __del__(self):
        self.cleanup()