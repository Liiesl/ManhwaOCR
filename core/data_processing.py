import numpy as np

def group_and_merge_text(results, distance_threshold):
    """
    Groups and merges text regions that are close to each other.
    :param results: List of OCR results (each containing 'coordinates' and 'text').
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
    for result in results:
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
        # Sort text regions top-to-bottom based on the y-coordinate of the bounding box
        group.sort(key=lambda y: np.mean(y['coordinates'], axis=0)[1])  # Sort by y-coordinate (top-to-bottom)
        
        # Track the number of lines for each text region
        merged_text = ""
        line_counts = 0
        for entry in group:
            lines = entry['text'].split('\n')
            merged_text += " ".join(lines) + " "  # Concatenate without newlines
            line_counts += len(lines)  # Add the number of lines to the total
        
        # Calculate new bounding box that encompasses all regions in the group
        all_coords = [coord for entry in group for coord in entry['coordinates']]
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
            'confidence': np.mean([entry['confidence'] for entry in group]),  # Average confidence
            'filename': group[0]['filename'],  # Preserve filename from the first entry in the group
            'line_counts': line_counts  # Track the number of lines for each text region
        })

    return merged_results