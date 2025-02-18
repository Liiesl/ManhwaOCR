import argparse
import os

def split_markdown_file(input_file, output_dir='.', chunk_size=100):
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)

    # Get base filename and extension
    base_name = os.path.basename(input_file)
    name_part, ext = os.path.splitext(base_name)

    # Read the input file
    with open(input_file, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    # Split into chunks
    chunks = [lines[i:i+chunk_size] for i in range(0, len(lines), chunk_size)]

    # Write each chunk to a file
    for i, chunk in enumerate(chunks, start=1):
        output_filename = os.path.join(output_dir, f"{name_part}_{i}{ext}")
        with open(output_filename, 'w', encoding='utf-8') as f:
            f.writelines(chunk)
        print(f"Created: {output_filename} (lines: {len(chunk)})")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Split markdown files into chunks. Automatically detects .md files in the current directory if no input is provided.')
    parser.add_argument('input_file', nargs='?', default=None,
                      help='Path to the input markdown file (optional if .md files exist in current directory)')
    parser.add_argument('--output-dir', default='.', 
                      help='Output directory for split files (default: current directory)')
    parser.add_argument('--chunk-size', type=int, default=100,
                      help='Number of lines per chunk (default: 100)')
    
    args = parser.parse_args()
    
    if args.input_file:
        # Process the specified file
        split_markdown_file(
            input_file=args.input_file,
            output_dir=args.output_dir,
            chunk_size=args.chunk_size
        )
    else:
        # Auto-detect .md files in current directory
        current_dir = os.getcwd()
        md_files = []
        for f in os.listdir(current_dir):
            file_path = os.path.join(current_dir, f)
            if os.path.isfile(file_path) and f.lower().endswith('.md'):
                md_files.append(file_path)
        
        if not md_files:
            parser.error("No input file provided and no .md files found in current directory.")
        
        # Process all detected .md files
        for md_file in md_files:
            split_markdown_file(
                input_file=md_file,
                output_dir=args.output_dir,
                chunk_size=args.chunk_size
            )