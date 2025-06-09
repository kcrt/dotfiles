#!/bin/bash

# Find all PDF files in the current directory
pdf_files=(*.pdf)

# Array to store encrypted PDF files
encrypted_pdfs=()

echo "Checking PDF files for encryption..."

# Check if qpdf, pdfinfo is available
if ! command -v pdfinfo &> /dev/null; then
    echo "Error: pdfinfo command not found. Please install it (e.g., sudo apt-get install poppler-utils or brew install poppler)."
    exit 1
fi
if ! command -v qpdf &> /dev/null; then
  echo "Error: qpdf command not found. Please install it (e.g., sudo apt-get install qpdf or brew install qpdf)."
  exit 1
fi

# Loop through each PDF file
for pdf_file in "${pdf_files[@]}"; do
  if [ -f "$pdf_file" ]; then
    # Check encryption status
    encryption_status=$(pdfinfo "$pdf_file" 2>/dev/null | grep "Encrypted:" | awk '{print $2}')
    if [ "$encryption_status" == "yes" ]; then
      encrypted_pdfs+=("$pdf_file")
    fi
  fi
done

# Check if any encrypted PDFs were found
if [ ${#encrypted_pdfs[@]} -eq 0 ]; then
  echo "No encrypted PDF files found in the current directory."
  exit 0
fi

echo ""
echo "The following PDF files are encrypted:"
for encrypted_pdf in "${encrypted_pdfs[@]}"; do
  echo "  - $encrypted_pdf"
done
echo ""

# Ask user for confirmation
read -p "Do you want to unprotect these files? (yes/no): " user_confirmation

if [[ "$user_confirmation" != "yes" && "$user_confirmation" != "y" ]]; then
  echo "Operation cancelled by the user."
  exit 0
fi

echo ""
echo "Proceeding with unprotection..."


for pdf_to_unprotect in "${encrypted_pdfs[@]}"; do
  backup_file="${pdf_to_unprotect}.org"
  echo "Backing up '$pdf_to_unprotect' to '$backup_file'..."
  cp "$pdf_to_unprotect" "$backup_file"
  if [ $? -ne 0 ]; then
    echo "Error: Failed to backup '$pdf_to_unprotect'. Skipping."
    continue
  fi

  echo "Decrypting '$pdf_to_unprotect'..."
  qpdf --decrypt --replace-input "$pdf_to_unprotect"
  if [ $? -eq 0 ]; then
    echo "'$pdf_to_unprotect' decrypted successfully."
  else
    echo "Error: Failed to decrypt '$pdf_to_unprotect'. Original file might be corrupted or password protected."
    echo "Restoring from backup..."
    mv "$backup_file" "$pdf_to_unprotect"
  fi
  echo ""
done

echo "Unprotection process completed."
