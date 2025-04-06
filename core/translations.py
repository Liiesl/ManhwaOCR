# translations.py
import google.generativeai as genai
from PyQt5.QtWidgets import QMessageBox
from PyQt5.QtCore import QThread, pyqtSignal
import os, math # Added math

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
                    # Emit debug print less frequently or remove if too noisy
                    self.debug_print.emit(response_text)
                    self.translation_progress.emit(chunk)  # Emit just the new chunk

            # When stream is complete, emit the final full response
            self.translation_finished.emit(response_text)
        except Exception as e:
            self.translation_failed.emit(f"Gemini API Error: {str(e)}")


def generate_for_translate_content(self):
    """Generate Markdown content in for-translate format, EXCLUDING deleted results."""
    content = "<!-- type: for-translate -->\n\n"
    grouped_results = {}
    extensions = set()

    # --- Filter out deleted results BEFORE grouping ---
    visible_results = [res for res in self.ocr_results if not res.get('is_deleted', False)]

    # Process only visible results
    for result in visible_results:
        filename = result['filename']
        ext = os.path.splitext(filename)[1].lstrip('.').lower()
        extensions.add(ext)
        text = result['text']
        row_number = result['row_number'] # Keep the original row number

        # Skip if text is empty or whitespace only
        if not text or text.isspace():
             continue

        if filename not in grouped_results:
            grouped_results[filename] = []
        # Store tuple (text, original_row_number)
        grouped_results[filename].append((text, row_number))

    if len(extensions) == 1:
        content += f"<!-- ext: {list(extensions)[0]} -->\n\n"

    # Generate content using the filtered and grouped results
    for idx, (filename, texts_with_rows) in enumerate(grouped_results.items()):
        if idx > 0:
            content += "\n\n" # Separator between files
        content += f"<!-- file: {filename} -->\n\n"

        # Sort by the original row number (float/int aware)
        sorted_texts_with_rows = sorted(texts_with_rows, key=lambda x: float(x[1])) # Ensure float conversion for sorting

        for text, row_number in sorted_texts_with_rows:
            # Format the row number as string (e.g., "10" or "10.1")
            row_number_str = str(row_number)
            # Write the text, potentially multi-line
            content += f"{text}\n"
            # Add the row number marker AFTER the text
            content += f"-/{row_number_str}\\-\n\n" # Add extra newline for spacing

    # Remove trailing newline if exists
    content = content.rstrip() + "\n"

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

        translations = {} # Dictionary to store parsed translations: {filename: {row_number_str: translated_text}}
        current_file = None
        buffer_text = ""
        buffer_row_number_str = None

        lines = content.split('\n')
        i = 0
        while i < len(lines):
            line = lines[i].strip()

            if line.startswith('<!-- file:') and line.endswith('-->'):
                # Process previous entry before starting new file
                if current_file and buffer_row_number_str and buffer_text:
                    if current_file not in translations:
                        translations[current_file] = {}
                    translations[current_file][buffer_row_number_str] = buffer_text.strip()
                    print(f"DEBUG (End of File): Parsed {current_file} row {buffer_row_number_str}")

                # Reset for new file
                current_file = line[10:-3].strip()
                buffer_text = ""
                buffer_row_number_str = None
                i += 1
                # Skip potential blank lines after file comment
                while i < len(lines) and not lines[i].strip():
                    i += 1
                continue # Move to the next line after file comment

            elif line.startswith('-/') and line.endswith('\\-') and current_file:
                # This is a row number marker, it signifies the end of the preceding text block
                row_number_str = line[2:-2].strip()
                if buffer_text: # Only save if there was text before the marker
                    if current_file not in translations:
                        translations[current_file] = {}
                    translations[current_file][row_number_str] = buffer_text.strip()
                    print(f"DEBUG: Parsed {current_file} row {row_number_str}")
                else:
                    print(f"DEBUG: Found row marker {row_number_str} but no preceding text buffered.")

                # Reset buffer for the *next* potential text block
                buffer_text = ""
                buffer_row_number_str = None # Marker consumed
                i += 1
                 # Skip potential blank lines after marker
                while i < len(lines) and not lines[i].strip():
                    i += 1
                continue # Move to the next line

            elif current_file:
                # This is part of a text block
                if buffer_text: # Append with newline if not the first line
                    buffer_text += "\n" + lines[i] # Preserve original line breaks
                else:
                    buffer_text = lines[i] # Start the buffer
                # Keep track of the row number this text *will* belong to (found later)
                # We don't know the row number *until* we hit the marker line.
                i += 1
                continue

            # If none of the above, just move to the next line
            i += 1

        # Process the very last entry if the file ended with text before a marker
        # (This case shouldn't happen with the corrected generate function format)
        # if current_file and buffer_row_number_str and buffer_text:
        #     if current_file not in translations:
        #         translations[current_file] = {}
        #     translations[current_file][buffer_row_number_str] = buffer_text.strip()
        #     print(f"DEBUG (End of Content): Parsed {current_file} row {buffer_row_number_str}")


        # Debug print: Show parsed structure
        print("\n===== DEBUG: Parsed translations structure =====\n")
        print(translations)
        print("\n==============================================\n")

        # Apply translations back to ocr_results (only update non-deleted entries)
        updated_count = 0
        missed_count = 0
        for result in self.ocr_results:
            # --- IMPORTANT: Only update results that were NOT deleted ---
            if result.get('is_deleted', False):
                continue

            filename = result.get('filename')
            original_row_number = result.get('row_number')
            original_row_number_str = str(original_row_number) # Convert to string for dict lookup

            if filename and original_row_number is not None:
                if filename in translations and original_row_number_str in translations[filename]:
                    translated_text = translations[filename][original_row_number_str]
                    result['text'] = translated_text
                    # DO NOT update row_number here, keep the original float/int value
                    # result['row_number'] = original_row_number
                    print(f"Applied translation to {filename} row {original_row_number_str}")
                    updated_count += 1
                    # Optional: Remove the entry from translations dict to track unmatched ones
                    # del translations[filename][original_row_number_str]
                    # if not translations[filename]: del translations[filename]
                else:
                    print(f"Warning: No translation found in parsed content for {filename} row {original_row_number_str}")
                    missed_count += 1
            else:
                print(f"Warning: Skipping OCR result with missing filename or row_number: {result}")

        print(f"\nTranslation import summary:")
        print(f" - Applied updates: {updated_count}")
        print(f" - Missing translations (expected if text was only markers/comments): {missed_count}")
        # print(f" - Unmatched translations left in parsed data: {translations}") # See if anything wasn't used

        # Check if any translations were parsed but not applied (could indicate mismatch issues)
        if translations:
             unapplied_count = sum(len(rows) for rows in translations.values())
             if unapplied_count > 0:
                  print(f"Warning: {unapplied_count} parsed translations were not applied to any existing OCR results.")
                  print("Unapplied:", translations)


    except Exception as e:
        import traceback
        print(traceback.format_exc())
        raise Exception(f"Failed to parse translated content: {str(e)}")