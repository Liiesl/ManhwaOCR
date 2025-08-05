# app/project_model.py

import os
import json
import traceback
from dataclasses import dataclass, field
from PyQt5.QtWidgets import QMessageBox

@dataclass
class ProjectData:
    """A simple container for all loaded project data."""
    mmtl_path: str = ""
    temp_dir: str = ""
    project_name: str = ""
    image_paths: list[str] = field(default_factory=list)
    ocr_results: list[dict] = field(default_factory=list)
    profiles: set[str] = field(default_factory=set)
    original_language: str = "Korean"
    active_profile_name: str = "Original"
    next_global_row_number: int = 0

class ProjectLoader:
    """Handles loading a project from a temporary directory into a ProjectData object."""

    def load_from_directory(self, mmtl_path: str, temp_dir: str) -> ProjectData | None:
        """
        Parses project files from a directory and returns a ProjectData object.
        Returns None on critical failure.
        """
        try:
            data = ProjectData(mmtl_path=mmtl_path, temp_dir=temp_dir)
            
            data.project_name = os.path.splitext(os.path.basename(mmtl_path))[0]

            # 1. Load image paths
            image_dir = os.path.join(temp_dir, 'images')
            if not os.path.exists(image_dir):
                raise FileNotFoundError("The 'images' directory is missing in the project file.")
                
            data.image_paths = sorted([
                os.path.join(image_dir, f)
                for f in os.listdir(image_dir)
                if f.lower().endswith(('png', 'jpg', 'jpeg'))
            ])
            
            if not data.image_paths:
                 # This can be a warning, not necessarily a fatal error yet
                 print("Warning: No images found in the project's images directory.")

            # 2. Load master.json (OCR results)
            master_path = os.path.join(temp_dir, 'master.json')
            if os.path.exists(master_path):
                data.ocr_results, data.next_global_row_number, data.profiles = self._load_master_json(master_path)
            
            # 3. Load meta.json (project metadata)
            meta_path = os.path.join(temp_dir, 'meta.json')
            if os.path.exists(meta_path):
                meta_data = self._load_meta_json(meta_path)
                data.original_language = meta_data.get('original_language', 'Korean')
                
                # If the saved active profile exists in the list of loaded profiles, use it.
                # Otherwise, default to "Original" to prevent errors.
                saved_profile = meta_data.get('active_profile_name', 'Original')
                if saved_profile in data.profiles:
                    data.active_profile_name = saved_profile
                else:
                    data.active_profile_name = "Original"
                    print(f"Warning: Saved active profile '{saved_profile}' not found in project. Defaulting to 'Original'.")


            return data

        except Exception as e:
            # Handle exceptions gracefully
            error_msg = f"Failed to load project: {e}"
            print(error_msg)
            traceback.print_exc()
            QMessageBox.critical(None, "Project Load Error", error_msg)
            return None

    def _load_master_json(self, path: str):
        """Loads and processes the master.json file."""
        ocr_results = []
        profiles = {"Original"} # "Original" always exists
        max_row_num = -1
        
        with open(path, 'r', encoding='utf-8') as f:
            loaded_data = json.load(f)

        for res in loaded_data:
            if all(k in res for k in ['row_number', 'filename', 'coordinates', 'text']):
                 if 'row_number' in res:
                     max_row_num = max(max_row_num, int(float(res['row_number'])))
                 if 'translations' in res and isinstance(res['translations'], dict):
                     for profile_name in res['translations']:
                         profiles.add(profile_name)
                 ocr_results.append(res)
        
        next_global_row_number = max_row_num + 1
        return ocr_results, next_global_row_number, profiles

    def _load_meta_json(self, path: str) -> dict:
        """Loads and processes the meta.json file, returning its contents as a dictionary."""
        with open(path, 'r', encoding='utf-8') as f:
            meta = json.load(f)
        return meta