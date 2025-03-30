#!/usr/bin/env bash

#===============================================================================
#
#          FILE:  add_to_memory_bank.sh
#
#         USAGE:  ./add_to_memory_bank.sh <INPUT_FILE>
#
#   DESCRIPTION:  This script adds data to the memory bank. (~/Documents/memorybank)
#
#       OPTIONS:  INPUT_FILE - The pdf file to add to the memory bank.
#        AUTHOR:  kcrt <kcrt@kcrt.net>
#       COMPANY:  Nanoseconds Hunter "http://www.kcrt.net"
#
#===============================================================================

if [ "$VIRTUAL_ENV" != "/Users/kcrt/venv" ]; then
    echo "Error: Please run this script under the correct virtual environment: /Users/kcrt/venv."
    exit 1
fi

if [ $# -ne 1 ]; then
    echo "Usage: $0 <INPUT_FILE>"
    exit 1
fi

INPUT_FILE=$1
MEMORY_BANK_DIR=~/Documents/memorybank

# Choose the target directory in $MEMORY_BANK_DIR
# First get the list and show it to the user
# Then ask the user to choose the target directory
# + memorybank
#  + md
#    + <category 1>
#      + <sub-category 1> (save target)
#      + <sub-category 2>
#    + <category 2>
#      ...
#  + pdf
#    + <category 1>
#      + <sub-category 1> (save target)
#      + <sub-category 2>
#    + <category 2>
#      ...


if [ ! -d "$MEMORY_BANK_DIR" ]; then
    echo "Error: Memory bank directory '$MEMORY_BANK_DIR' does not exist!"
    exit 1
fi

readarray -t categories_path < <(find "$MEMORY_BANK_DIR/md" -mindepth 1 -maxdepth 1 -type d | sort)
for i in "${!categories_path[@]}"; do
    echo "$i: $(basename "${categories_path[$i]}")"
done
echo "99: Create a new category"
read -rp "Enter the number of your choice: " choice
if [ "$choice" -eq 99 ]; then
    read -rp "Enter the name of the new category: " category_name
    mkdir "$MEMORY_BANK_DIR/md/$category_name"
    mkdir "$MEMORY_BANK_DIR/pdf/$category_name"
else
    category_path="${categories_path[$choice]}"
    category_name="$(basename "$category_path")"
fi

readarray -t sub_categories_path < <(find "$MEMORY_BANK_DIR/md/$category_name" -mindepth 1 -maxdepth 1 -type d | sort)
for i in "${!sub_categories_path[@]}"; do
    echo "$i: $(basename "${sub_categories_path[$i]}")"
done
echo "99: Create a new sub-category"
read -rp "Enter the number of your choice: " choice
if [ "$choice" -eq 99 ]; then
    read -rp "Enter the name of the new sub-category: " subcategory_name
    mkdir "$MEMORY_BANK_DIR/md/$category_name/$subcategory_name"
    mkdir "$MEMORY_BANK_DIR/pdf/$category_name/$subcategory_name"
else
    subcategory_path="${sub_categories_path[$choice]}"
    subcategory_name="$(basename "$subcategory_path")"
fi

TARGET_MD_DIR="$MEMORY_BANK_DIR/md/$category_name/$subcategory_name"
TARGET_PDF_DIR="$MEMORY_BANK_DIR/pdf/$category_name/$subcategory_name"

TEMP_MD_FILE=$(mktemp)

# Convert pdf into md with mistral OCR
~/dotfiles/script/mistral_ocr.py --no-image "$INPUT_FILE" "$TEMP_MD_FILE"

# Check if $TEMP_MD_FILE is not empty
if [ ! -s "$TEMP_MD_FILE" ]; then
    echo "Error: Failed to convert the pdf file into md file."
    exit 1
fi

# From md file, extract the title and the abstract content using LLM
echo "Extracting title and summary using LLM..."
cp "$TEMP_MD_FILE" "$MEMORY_BANK_DIR/processing.md" # backup the md file for api failure
TITLE_AND_SUMMARY=$(python3 "$HOME/dotfiles/script/summarize_md_ollama.py" "$TEMP_MD_FILE")

echo "LLM output:"
echo "$TITLE_AND_SUMMARY"

# Extract title and summary
TITLE=$(echo "$TITLE_AND_SUMMARY" | grep "^Title:" | sed 's/^Title: //')
# Extract summary - this handles multi-line summaries
SUMMARY=$(echo "$TITLE_AND_SUMMARY" | sed -n '/^Summary: /,$p' | sed 's/^Summary: //')

# Create sanitized filename from title (replace spaces with underscores, remove special characters)
SANITIZED_TITLE=$(echo "$TITLE" | tr ' ' '_' | tr -cd 'a-zA-Z0-9_-')

# Get current date in YYYYMMDD format
CURRENT_DATE=$(date +"%Y%m%d")

# Create filenames with date prefix
MD_FILENAME="${CURRENT_DATE}_${SANITIZED_TITLE}.md"
PDF_FILENAME="${CURRENT_DATE}_${SANITIZED_TITLE}.pdf"

# Add title and summary to the beginning of the markdown file
FINAL_MD_FILE=$(mktemp)
{
    echo "# $TITLE"
    echo ""
    echo "## Summary"
    echo "$SUMMARY"
    echo ""
    cat "$TEMP_MD_FILE"
} > "$FINAL_MD_FILE"

# Copy the files to the target directories
cp "$INPUT_FILE" "$TARGET_PDF_DIR/$PDF_FILENAME"
cp "$FINAL_MD_FILE" "$TARGET_MD_DIR/$MD_FILENAME"

# Update or create the index.md file
INDEX_FILE="$MEMORY_BANK_DIR/index.md"

# Create index file if it doesn't exist
if [ ! -f "$INDEX_FILE" ]; then
    echo "# Memory Bank Index" > "$INDEX_FILE"
    echo "" >> "$INDEX_FILE"
    echo "This file contains an index of all documents in the memory bank." >> "$INDEX_FILE"
    echo "" >> "$INDEX_FILE"
fi

# Add entry to index.md
{
    echo "## $TITLE"
    echo ""
    echo "**Category:** $category_name/$subcategory_name"
    echo ""
    echo "**Files:**"
    echo "- Markdown: [${MD_FILENAME}](md/$category_name/$subcategory_name/${MD_FILENAME})"
    echo "- PDF: [${PDF_FILENAME}](pdf/$category_name/$subcategory_name/${PDF_FILENAME})"
    echo ""
    echo "**Summary:**"
    echo "$SUMMARY"
    echo ""
    echo "---"
    echo ""
} >> "$INDEX_FILE"

# Clean up temporary files
rm "$TEMP_MD_FILE"
rm "$FINAL_MD_FILE"

echo "Successfully added to memory bank:"
echo "Title: $TITLE"
echo "PDF saved to: $TARGET_PDF_DIR/$PDF_FILENAME"
echo "Markdown saved to: $TARGET_MD_DIR/$MD_FILENAME"

rm "$MEMORY_BANK_DIR/processing.md"