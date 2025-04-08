# --- START OF FILE data_processing.py ---

import numpy as np
import math # Added for distance calculation

def distance(coord1, coord2):
    """
    Calculate the Euclidean distance between the centers of two bounding boxes.
    Handles potential None or empty coordinates.

    :param coord1: List of [x, y] coordinates for the first box.
    :param coord2: List of [x, y] coordinates for the second box.
    :return: Euclidean distance, or float('inf') if coordinates are invalid.
    """
    try:
        if not coord1 or not coord2 or len(coord1) < 1 or len(coord2) < 1:
            return float('inf') # Cannot calculate distance without valid coordinates
        center1 = np.mean(np.array(coord1), axis=0)
        center2 = np.mean(np.array(coord2), axis=0)
        dist = np.linalg.norm(center1 - center2)
        # Handle potential NaN if input arrays were weird, though mean should handle empty lists okay
        return dist if not math.isnan(dist) else float('inf')
    except (ValueError, TypeError, IndexError) as e:
        print(f"Warning: Could not calculate distance between {coord1} and {coord2}. Error: {e}")
        return float('inf') # Return infinity on error to prevent accidental merging

def merge_ocr_entries(entries_to_merge):
    """
    Merges a list of OCR result dictionaries into a single dictionary.
    Sorts internally by vertical position before merging text.
    Calculates combined bounding box, averages confidence, sums line counts.
    Does NOT assign row number. Preserves filename from the first entry.

    :param entries_to_merge: A list of OCR result dictionaries to merge.
    :return: A single merged OCR result dictionary, or None if input is empty/invalid.
    """
    if not entries_to_merge:
        return None

    # Sort text regions top-to-bottom based on the y-coordinate of the top edge
    try:
        # Sort by the minimum y-coordinate (top edge)
        entries_to_merge.sort(key=lambda entry: min((p[1] for p in entry.get('coordinates', [[0, float('inf')]])), default=float('inf')))
    except (IndexError, TypeError, KeyError, ValueError) as e:
        print(f"Warning: Could not sort entries for merging due to coordinate issue: {e}. Group: {entries_to_merge}")
        # Use the first entry as a fallback if sorting fails? Or return None? Let's try returning None.
        return None

    merged_text_parts = []
    line_counts = 0
    all_coords = []
    confidences = []
    filenames = set() # Track filenames to ensure consistency (should ideally be the same)
    is_manual_flags = []

    for entry in entries_to_merge:
        text = entry.get('text', '').strip()
        if text: # Only add non-empty text parts
            merged_text_parts.append(text)
        lines = text.split('\n')
        line_counts += len(lines) if text else 0 # Count lines only if text exists
        all_coords.extend(entry.get('coordinates', []))
        confidences.append(entry.get('confidence', 0.0))
        filenames.add(entry.get('filename', 'unknown'))
        is_manual_flags.append(entry.get('is_manual', False)) # Track if any merged part was manual

    if len(filenames) > 1:
        print(f"Warning: Merging entries from different filenames: {filenames}. Using filename from first entry.")

    merged_text = " ".join(merged_text_parts).strip() # Join with space, remove leading/trailing space

    if not all_coords: # Skip if no coordinates found in the group
        print(f"Warning: Skipping merge group with no coordinates: {entries_to_merge}")
        return None

    # Calculate the bounding box covering all coordinates
    try:
        x_coords = [p[0] for p in all_coords]
        y_coords = [p[1] for p in all_coords]
        new_coords = [
            [min(x_coords), min(y_coords)],  # Top-left
            [max(x_coords), min(y_coords)],  # Top-right
            [max(x_coords), max(y_coords)],  # Bottom-right
            [min(x_coords), max(y_coords)]   # Bottom-left
        ]
    except ValueError: # Handle cases where min/max fail (e.g., empty coords list)
         print(f"Warning: Skipping merge group due to empty coordinates after processing: {entries_to_merge}")
         return None

    # Determine filename (use the first entry's filename)
    merged_filename = entries_to_merge[0].get('filename', 'unknown')
    # If any part was manually added, mark the merged result as manual
    merged_is_manual = any(is_manual_flags)

    merged_entry = {
        'coordinates': new_coords,
        'text': merged_text,
        'confidence': np.mean(confidences) if confidences else 0.0,
        'filename': merged_filename,
        'line_counts': line_counts,
        'is_manual': merged_is_manual
        # 'row_number': IS ASSIGNED EXTERNALLY
    }
    return merged_entry


def group_and_merge_text(results, distance_threshold):
    """
    Groups and merges text regions that are close to each other using spatial proximity.
    Focuses on merging geometry, text, confidence, and tracking lines.
    Row number assignment is handled externally after sorting.

    :param results: List of OCR results (each containing 'coordinates', 'text', 'confidence', 'filename').
    :param distance_threshold: Maximum distance between bounding box centers to consider them part of the same group.
    :return: List of merged OCR results without final 'row_number'.
    """
    # Filter out results without coordinates before grouping
    valid_results = [r for r in results if 'coordinates' in r and r['coordinates'] and r.get('filename') is not None]
    if not valid_results:
        return []

    grouped_results_by_file = {} # Group by filename first

    for result in valid_results:
        filename = result['filename']
        if filename not in grouped_results_by_file:
             grouped_results_by_file[filename] = []

        added_to_group = False
        # Check groups ONLY within the same file
        for group in grouped_results_by_file[filename]:
            # Check if this result is close to any result ALREADY in the group
            if any(distance(result['coordinates'], existing['coordinates']) < distance_threshold for existing in group):
                group.append(result)
                added_to_group = True
                break # Added to a group, move to next result

        if not added_to_group:
             # Start a new group for this file
             grouped_results_by_file[filename].append([result])

    # Merge text within each group for each file
    merged_results_final = []
    for filename, groups in grouped_results_by_file.items():
        for group in groups:
            merged_entry = merge_ocr_entries(group) # Use the new helper
            if merged_entry:
                 merged_results_final.append(merged_entry)

    # Note: The final list is NOT sorted globally here. Sorting happens later.
    return merged_results_final

# --- END OF FILE data_processing.py ---