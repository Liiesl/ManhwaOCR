import numpy as np

def group_and_merge_text(results, distance_threshold):
    """
    Groups and merges text regions that are close to each other.
    :param results: List of OCR results (each containing 'coordinates', 'text', 'filename', 'row_number'). # Added row_number here for clarity
    :param distance_threshold: Maximum distance between text regions to consider them part of the same group.
    :return: List of merged OCR results.
    """
    def distance(coord1, coord2):
        """Calculate the Euclidean distance between two bounding box centers."""
        center1 = np.mean(coord1, axis=0)
        center2 = np.mean(coord2, axis=0)
        return np.linalg.norm(center1 - center2)

    # Group text regions based on proximity
    grouped_results = []
    # Filter out results without coordinates before grouping
    valid_results = [r for r in results if 'coordinates' in r and r['coordinates']]
    for result in valid_results:
        added_to_group = False
        for group in grouped_results:
            # Check if this result is close to any result in the group
            if any(distance(result['coordinates'], existing['coordinates']) < distance_threshold for existing in group):
                group.append(result)
                added_to_group = True
                break
        if not added_to_group:
            grouped_results.append([result])

    # Merge text within each group
    merged_results = []
    for group in grouped_results:
        if not group: # Skip empty groups if any occur
             continue

        # Sort text regions top-to-bottom based on the y-coordinate of the bounding box center
        try:
            group.sort(key=lambda y: np.mean(y['coordinates'], axis=0)[1])  # Sort by y-coordinate (top-to-bottom)
        except (IndexError, TypeError, KeyError) as e:
            print(f"Warning: Could not sort group due to coordinate issue: {e}. Group: {group}")
            # Decide how to handle: skip group, use first element, etc. Let's skip for now.
            continue

        # Track the number of lines for each text region
        merged_text = ""
        line_counts = 0
        for entry in group:
            lines = entry.get('text', '').split('\n') # Use .get for safety
            merged_text += " ".join(lines) + " "  # Concatenate without newlines
            line_counts += len(lines)  # Add the number of lines to the total

        # Calculate new bounding box that encompasses all regions in the group
        all_coords = [coord for entry in group for coord in entry.get('coordinates', [])] # Use .get for safety
        if not all_coords: # Skip if no coordinates found in the group
            print(f"Warning: Skipping group with no coordinates: {group}")
            continue

        x_coords = [p[0] for p in all_coords]
        y_coords = [p[1] for p in all_coords]

        # Ensure the bounding box is calculated correctly
        new_coords = [
            [min(x_coords), min(y_coords)],  # Top-left
            [max(x_coords), min(y_coords)],  # Top-right
            [max(x_coords), max(y_coords)],  # Bottom-right
            [min(x_coords), max(y_coords)]   # Bottom-left
        ]

        # Add merged result
        merged_results.append({
            'coordinates': new_coords,
            'text': merged_text.strip(),  # Remove trailing space
            'confidence': np.mean([entry.get('confidence', 0.0) for entry in group]),  # Average confidence, handle missing
            'filename': group[0].get('filename', 'unknown'),  # Preserve filename from the first entry, handle missing
            'line_counts': line_counts,  # Track the number of lines for each text region
            'row_number': group[0].get('row_number', -1) # <<< --- FIX: Preserve row_number from the first entry, handle missing
        })

    return merged_results