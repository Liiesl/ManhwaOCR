# gemini_handler.py
import google.generativeai as genai
from PyQt5.QtWidgets import QMessageBox
from PyQt5.QtCore import QThread, pyqtSignal
import os

class TranslationThread(QThread):
    translation_finished = pyqtSignal(str)
    translation_failed = pyqtSignal(str)
    debug_print = pyqtSignal(str)
    translation_progress = pyqtSignal(str)  # New signal for real-time updates

    def __init__(self, api_key, text, model_name="gemini-2.0-flash", target_lang="English", parent=None):
        super().__init__(parent)
        self.api_key = api_key
        self.text = text
        self.model_name = model_name
        self.target_lang = target_lang

    def run(self):
        try:
            genai.configure(api_key=self.api_key)
            model = genai.GenerativeModel(self.model_name)
            
            prompt = f"""translate and change only the korean text to {self.target_lang}, keep everything else.

            {self.text}"""
            
            # Use streaming generation instead of single response
            response_text = ""
            
            # Use streaming generation for real-time updates
            for response in model.generate_content(prompt, stream=True):
                if response.text:
                    chunk = response.text
                    response_text += chunk
                    self.debug_print.emit(response_text)  # Emit current accumulated response
                    self.translation_progress.emit(chunk)  # Emit just the new chunk
            
            # When stream is complete, emit the final full response
            self.translation_finished.emit(response_text)
        except Exception as e:
            self.translation_failed.emit(str(e))
    
def generate_for_translate_content(self):
    """Generate Markdown content in for-translate format."""
    content = "<!-- type: for-translate -->\n\n"
    grouped_results = {}
    extensions = set()

    for result in self.ocr_results:
        filename = result['filename']
        ext = os.path.splitext(filename)[1].lstrip('.').lower()
        extensions.add(ext)
        text = result['text']
        row_number = result['row_number']
        
        if filename not in grouped_results:
            grouped_results[filename] = []
        grouped_results[filename].append((text, row_number))

    if len(extensions) == 1:
        content += f"<!-- ext: {list(extensions)[0]} -->\n\n"

    for idx, (filename, texts) in enumerate(grouped_results.items()):
        if idx > 0:
            content += "\n\n"
        content += f"<!-- file: {filename} -->\n\n"
        sorted_texts = sorted(texts, key=lambda x: x[1])
        for text, row_number in sorted_texts:
            lines = text.split('\n')
            for line in lines:
                content += f"{line.strip()}\n"
                content += f"-/{row_number}\\-\n"

    return content

def import_translation_file_content(self, content):
    """Modified version of import_translation that works with direct content instead of file path."""
    try:
        # Debug print: Show the content being parsed
        print("\n===== DEBUG: Content being parsed =====\n")
        print(content)
        print("\n======================================\n")
        if '<!-- type: for-translate -->' not in content:
            raise ValueError("Unsupported MD format - missing type comment.")

        translations = {}
        current_file = None
        file_texts = {}
        current_entry = []  # Buffer for current text entry
        row_numbers = []

        # Parse filename groups and entries
        for line in content.split('\n'):
            line = line.strip()
            if line.startswith('<!-- file:') and line.endswith('-->'):
                # Save previous file's entries
                if current_file is not None and current_entry:
                    file_texts[current_file].append(('\n'.join(current_entry), row_numbers))
                    current_entry = []
                    row_numbers = []
                # Extract filename
                current_file = line[10:-3].strip()
                file_texts[current_file] = []
            elif line.startswith('-/') and line.endswith('\\-'):
                # Extract row number from marker (e.g., "-/3\\-")
                if current_entry:
                    row_number_str = line[2:-2].strip()
                    try:
                        row_number = int(row_number_str)
                    except ValueError:
                        row_number = 0  # Default to 0 if parsing fails
                    row_numbers.append(row_number)
                    # Save current entry
                    file_texts[current_file].append(('\n'.join(current_entry), row_numbers))
                    current_entry = []
                    row_numbers = []
            elif current_file is not None:
                # Skip empty lines between entries
                if line or current_entry:
                    current_entry.append(line)

        # Add the last entry if buffer isn't empty
        if current_file is not None and current_entry:
            file_texts[current_file].append(('\n'.join(current_entry), row_numbers))

        # Debug print: Show parsed structure
        print("\n===== DEBUG: Parsed structure =====\n")
        for filename, entries in file_texts.items():
            print(f"File: {filename}")
            for entry in entries:
                print(f"  - Text: {entry[0]}")
                print(f"    Row numbers: {entry[1]}")
        print("\n==================================\n")

        # Rebuild translations in original OCR order
        translation_index = {k: 0 for k in file_texts.keys()}
        for result in self.ocr_results:
            filename = result['filename']
            if filename in file_texts and translation_index[filename] < len(file_texts[filename]):
                translated_text, row_numbers = file_texts[filename][translation_index[filename]]
                result['text'] = translated_text
                result['row_number'] = row_numbers[0]  # Update row number
                translation_index[filename] += 1
                print(f"DEBUG: Updated {filename} row {row_numbers[0]} with translation")

            else:
                print(f"Warning: No translation found for entry in '{filename}'")

    except Exception as e:
        raise Exception(f"Failed to parse translated content: {str(e)}")