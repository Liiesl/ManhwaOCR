import os, gc, time, math, traceback
from PyQt5.QtCore import QObject, pyqtSignal
from app.core.ocr_processor import OCRProcessor

class BatchOCRHandler(QObject):
    """
    Manages the entire batch OCR process for multiple images.
    This object lives in the main thread but orchestrates worker QThreads.
    """
    batch_progress = pyqtSignal(int)      # Overall progress (0-100)
    # --- NEW: Signal for incremental updates ---
    image_processed = pyqtSignal(list)    # Emits results for a single completed image
    # --- MODIFIED: batch_finished no longer needs to carry all results ---
    batch_finished = pyqtSignal(int)      # Emits final next row number when all images are done
    error_occurred = pyqtSignal(str)      # Emits any critical error message
    processing_stopped = pyqtSignal()     # Emits when the process is stopped by the user

    def __init__(self, image_paths, reader, settings, starting_row_number):
        super().__init__()
        self.image_paths = image_paths
        self.reader = reader
        self.settings = settings
        self.starting_row_number = starting_row_number
        
        self.current_image_index = 0
        self.next_global_row_number = self.starting_row_number
        # --- REMOVED: No need to accumulate results here anymore ---
        # self.accumulated_results = [] 
        self._is_stopped = False
        self.ocr_thread = None

    def start_processing(self):
        """Starts the batch process."""
        print("Batch Handler: Starting processing...")
        self._is_stopped = False
        self._process_next_image()

    # ... stop() and _process_next_image() remain the same ...
    def stop(self):
        """Requests the batch process to stop."""
        print("Batch Handler: Stop requested by user.")
        self._is_stopped = True
        if self.ocr_thread and self.ocr_thread.isRunning():
            self.ocr_thread.stop_requested = True
            
    def _process_next_image(self):
        """Processes a single image or finishes the batch if all are done."""
        if self._is_stopped:
            print("Batch Handler: Process was stopped, not starting next image.")
            self.processing_stopped.emit()
            return
            
        if self.current_image_index >= len(self.image_paths):
            print("Batch Handler: All images processed.")
            self._finish_batch()
            return

        if not self.reader:
            self.error_occurred.emit("OCR Reader not available. Cannot process next image.")
            return

        image_path = self.image_paths[self.current_image_index]
        print(f"Batch Handler: Creating thread for image {self.current_image_index + 1}/{len(self.image_paths)}: {os.path.basename(image_path)}")

        self.ocr_thread = OCRProcessor(
            image_path=image_path,
            reader=self.reader,
            **self.settings # Unpack the settings dictionary
        )

        self.ocr_thread.ocr_progress.connect(self._handle_image_progress)
        self.ocr_thread.ocr_finished.connect(self._handle_image_results)
        self.ocr_thread.error_occurred.connect(self._handle_image_error)
        self.ocr_thread.start()
        
    # ... _handle_image_progress() remains the same ...
    def _handle_image_progress(self, progress):
        """Calculates and emits the overall batch progress."""
        total_images = len(self.image_paths)
        if total_images == 0: return
        per_image_contribution = 80.0 / total_images
        current_image_progress = progress / 100.0
        overall_progress = 20 + (self.current_image_index * per_image_contribution) + (current_image_progress * per_image_contribution)
        self.batch_progress.emit(int(overall_progress))

    # --- MODIFIED: This is the key change ---
    def _handle_image_results(self, processed_results):
        """Receives results from a single image, emits them for UI update, and starts the next."""
        if self._is_stopped:
            print("Batch Handler: Ignoring results from finished image due to stop request.")
            return

        current_image_path = self.image_paths[self.current_image_index]
        filename = os.path.basename(current_image_path)
        
        newly_numbered_results = []
        if processed_results:
            try:
                processed_results.sort(key=lambda r: min(p[1] for p in r.get('coordinates', [[0, float('inf')]])))
            except (ValueError, TypeError, IndexError) as e:
                print(f"Warning: Could not sort processed results for {filename}: {e}. Using processor order.")
            
            for result in processed_results:
                result['filename'] = filename
                result['row_number'] = self.next_global_row_number
                result['is_manual'] = False
                result['translations'] = {}
                newly_numbered_results.append(result)
                self.next_global_row_number += 1
        
        # --- EMIT the results for this one image immediately ---
        if newly_numbered_results:
            self.image_processed.emit(newly_numbered_results)
            print(f"Batch Handler: Emitted {len(newly_numbered_results)} blocks from {filename}.")
        
        # Move to the next image
        self.current_image_index += 1
        self.ocr_thread = None
        gc.collect()

        self._process_next_image()

    # ... _handle_image_error() remains the same ...
    def _handle_image_error(self, message):
        """Handles an error from a worker thread."""
        print(f"Batch Handler: An error occurred: {message}")
        self._is_stopped = True
        self.error_occurred.emit(message)

    # --- MODIFIED: _finish_batch is now simpler ---
    def _finish_batch(self):
        """Cleans up and signals that the entire batch is complete."""
        print("Batch Handler: Finishing run.")
        self.batch_progress.emit(100)
        # Emit the final row number, no need to send the giant list of results.
        self.batch_finished.emit(self.next_global_row_number)
        self.ocr_thread = None
        gc.collect()