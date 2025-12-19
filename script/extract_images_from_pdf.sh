#!/bin/bash

# Show help message
show_help() {
    cat << EOF
Usage: $(basename "$0") [OPTIONS] <pdf_file>

Extract all images from a PDF file using pdfimages command.

This script:
1. Takes a PDF file as input
2. Determines output prefix based on the PDF filename (without extension)
3. Uses pdfimages to extract all images with -all and --print-filenames options
4. Saves extracted images in the current directory

OPTIONS:
    -h, --help    Show this help message and exit

ARGUMENTS:
    pdf_file      Path to the PDF file to extract images from

REQUIREMENTS:
    - pdfimages: Install with 'brew install poppler' (macOS) or 'sudo apt-get install poppler-utils' (Ubuntu)

EXAMPLES:
    $(basename "$0") document.pdf           # Extract images from document.pdf with prefix "document"
    $(basename "$0") /path/to/file.pdf      # Extract images from file.pdf with prefix "file"
    $(basename "$0") --help                 # Show this help message

NOTE: Images are extracted to the current working directory.
EOF
}

# Function to extract all images from a PDF file
extract_images_from_pdf() {
    local pdf_file="$1"
    
    if [ -z "$pdf_file" ]; then
        echo "Error: No PDF file provided"
        echo "Usage: extract_images_from_pdf <pdf_file>"
        return 1
    fi
    
    if [ ! -f "$pdf_file" ]; then
        echo "Error: PDF file not found - $pdf_file"
        return 1
    fi
    
    # Check if pdfimages command is available
    if ! command -v pdfimages &> /dev/null; then
        echo "Error: pdfimages command not found. Please install it (e.g., sudo apt-get install poppler-utils or brew install poppler)."
        return 1
    fi
    
    # Get the stem of the PDF file (filename without extension)
    local output_prefix
    output_prefix=$(basename "$pdf_file" .pdf)
    
    # Extract images using pdfimages
    echo "Extracting images from $pdf_file..."
    if pdfimages -all -print-filenames "$pdf_file" "$output_prefix"; then
        echo "Image extraction completed successfully."
        return 0
    else
        echo "Error: Failed to extract images from $pdf_file"
        return 1
    fi
}

# Parse command line arguments
case "${1:-}" in
    -h|--help)
        show_help
        exit 0
        ;;
    "")
        echo "Error: No PDF file provided"
        echo "Use --help for usage information."
        exit 1
        ;;
    *)
        # Main execution when script is run directly
        if [ "${BASH_SOURCE[0]}" == "${0}" ]; then
            extract_images_from_pdf "$1"
        fi
        ;;
esac