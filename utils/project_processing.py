import os
import zipfile
import json
import tempfile
import re
from shutil import copyfile, rmtree
from app.widgets_3 import NewProjectDialog, ImportWFWFDialog
from PyQt5.QtWidgets import QMessageBox, QFileDialog, QDialog, QApplication
from PyQt5.QtCore import QDateTime, QDir, Qt

def new_project(self):
    dialog = NewProjectDialog(self)
    if dialog.exec_() == QDialog.Accepted:
        source_path, project_path, language = dialog.get_paths()
        
        if not source_path or not project_path:
            QMessageBox.warning(self, "Error", "Please select both source and project location")
            return
            
        try:
            # Create new .mmtl file
            with zipfile.ZipFile(project_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                # Create meta.json
                meta = {
                    'created': QDateTime.currentDateTime().toString(Qt.ISODate),
                    'source': source_path,
                    'original_language': language,
                    'version': '1.0'
                }
                zipf.writestr('meta.json', json.dumps(meta, indent=2))
                
                # Add images
                images_dir = 'images/'
                if os.path.isfile(source_path):
                    zipf.write(source_path, images_dir + os.path.basename(source_path))
                elif os.path.isdir(source_path):
                    for file in os.listdir(source_path):
                        if file.lower().endswith(('png', 'jpg', 'jpeg')):
                            zipf.write(os.path.join(source_path, file), 
                                     images_dir + file)
                
                # Create empty OCR results
                zipf.writestr('master.json', json.dumps([]))  # Empty list
            
            launch_project(self, project_path)
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to create project: {str(e)}")

def open_project(self):
    file, _ = QFileDialog.getOpenFileName(self, "Open Project", "", "Manga Translation Files (*.mmtl)")
    if file:
        launch_project(self, file)  # Use the universal launch_project function

def import_from_wfwf(self):
    dialog = ImportWFWFDialog(self)
    if dialog.exec_() == QDialog.Accepted:
        temp_dir = dialog.get_temp_dir()
        if not temp_dir or not os.path.exists(temp_dir):
            QMessageBox.warning(self, "Error", "No downloaded images found.")
            return
        
        project_path, _ = QFileDialog.getSaveFileName(
            self, "Save Project", QDir.homePath(), "Manga Translation Files (*.mmtl)"
        )
        
        if not project_path:
            rmtree(temp_dir)
            return
        
        try:
            # Run number correction on downloaded files
            filename_map = correct_filenames(temp_dir)
            
            # Create a temporary directory for corrected filenames
            corrected_dir = tempfile.mkdtemp()
            
            # Copy files with corrected names
            for old_name, new_name in filename_map.items():
                if old_name.lower().endswith(('png', 'jpg', 'jpeg')):
                    src = os.path.join(temp_dir, old_name)
                    dst = os.path.join(corrected_dir, new_name)
                    copyfile(src, dst)
            
            with zipfile.ZipFile(project_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                meta = {
                    'created': QDateTime.currentDateTime().toString(Qt.ISODate),
                    'source': dialog.get_url(),
                    'version': '1.0'
                }
                zipf.writestr('meta.json', json.dumps(meta, indent=2))
                
                images_dir = 'images/'
                for img in os.listdir(corrected_dir):
                    if img.lower().endswith(('png', 'jpg', 'jpeg')):
                        zipf.write(os.path.join(corrected_dir, img), os.path.join(images_dir, img))
                
                zipf.writestr('master.json', json.dumps([]))
            
            launch_project(self, project_path)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to create project: {str(e)}")
        finally:
            rmtree(temp_dir)
            if 'corrected_dir' in locals() and os.path.exists(corrected_dir):
                rmtree(corrected_dir)

def launch_project(self, mmtl_path):
    """
    Universal function to launch a project from an mmtl file.
    Works for both Home and MenuBar classes.
    """
    # Check which class is calling this function
    if hasattr(self, 'launch_main_app'):
        # Called from Home class
        self.launch_main_app(mmtl_path)
    elif hasattr(self, 'main_window'):
        # Called from MenuBar class
        from main import LoadingDialog, ProjectLoaderThread
        
        # Show loading dialog
        loading_dialog = LoadingDialog(self)
        loading_dialog.show()
        
        # Create and start loader thread - store as instance variable
        self.loader_thread = ProjectLoaderThread(mmtl_path)
        
        def handle_project_loaded(mmtl_path, temp_dir):
            try:
                from app.main_window import MainWindow
                
                # Update recent projects if we're in the MenuBar class
                if hasattr(self, 'main_window'):
                    # Close current window and open new one
                    main_app = QApplication.instance()
                    old_window = self.main_window
                    
                    # Create main window
                    new_window = MainWindow()
                    new_window.process_mmtl(mmtl_path, temp_dir)
                    new_window.show()
                    
                    # Close the old window
                    old_window.close()
                
                loading_dialog.close()
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to launch project: {str(e)}")
                rmtree(temp_dir, ignore_errors=True)
            
            # Clean up the thread
            self.loader_thread.deleteLater()
        
        def handle_project_error(error_msg):
            loading_dialog.close()
            QMessageBox.critical(self, "Error", f"Failed to open project:\n{error_msg}")
            
            # Clean up the thread
            self.loader_thread.deleteLater()
        
        self.loader_thread.finished.connect(handle_project_loaded)
        self.loader_thread.error.connect(handle_project_error)
        self.loader_thread.start()
    else:
        QMessageBox.critical(self, "Error", "Cannot launch project: Unknown context")

def correct_filenames(directory):
    """
    Apply number correction to filenames in the directory.
    Returns a dict mapping original filenames to corrected ones.
    """
    # Get all files in the directory
    files = os.listdir(directory)
    filename_map = {}
    
    # Dictionaries to track maximum suffix lengths for both formats
    parentheses_lengths = []
    direct_suffix_lengths = []
    
    # First pass: determine maximum numeric suffix lengths for both formats
    for filename in files:
        base, ext = os.path.splitext(filename)
        
        # Check for numbers in parentheses: "filename (123).ext"
        parentheses_match = re.match(r'^(.*?)\s*\((\d+)\)$', base)
        if parentheses_match:
            num_str = parentheses_match.group(2)
            parentheses_lengths.append(len(num_str))
            continue
        
        # Check for direct numeric suffixes: "filename123.ext"
        direct_match = re.match(r'^(.*?)(\d+)$', base)
        if direct_match:
            num_str = direct_match.group(2)
            direct_suffix_lengths.append(len(num_str))
    
    # Determine maximum lengths (if any files were found)
    max_parentheses_length = max(parentheses_lengths) if parentheses_lengths else 0
    max_direct_length = max(direct_suffix_lengths) if direct_suffix_lengths else 0
    
    # No files with numeric suffixes found
    if max_parentheses_length == 0 and max_direct_length == 0:
        return {filename: filename for filename in files}
    
    # Second pass: rename files with padded numbers
    for filename in files:
        base, ext = os.path.splitext(filename)
        new_filename = filename  # Default to no change
        
        # Handle numbers in parentheses: "filename (123).ext"
        parentheses_match = re.match(r'^(.*?)\s*\((\d+)\)$', base)
        if parentheses_match and max_parentheses_length > 0:
            base_part = parentheses_match.group(1).rstrip()  # Remove trailing space
            num_str = parentheses_match.group(2)
            padded_num = num_str.zfill(max_parentheses_length)
            new_base = f"{base_part} ({padded_num})"
            new_filename = f"{new_base}{ext}"
        
        # Handle direct numeric suffixes: "filename123.ext"
        direct_match = re.match(r'^(.*?)(\d+)$', base)
        if direct_match and max_direct_length > 0:
            base_part = direct_match.group(1)
            num_str = direct_match.group(2)
            padded_num = num_str.zfill(max_direct_length)
            new_base = f"{base_part}{padded_num}"
            new_filename = f"{new_base}{ext}"
        
        if new_filename != filename:
            # Record the mapping but don't rename yet to avoid conflicts
            filename_map[filename] = new_filename
        else:
            filename_map[filename] = filename
            
    return filename_map