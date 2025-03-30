#! /usr/bin/env python3 
# -*- coding: utf-8 -*-

"""
This code
1. list up files from /Users/kcrt/prog/M5Paper_myroom/data/signs
2. Show the list of files and user can select one of them
3. Construct string "/signs/<selected_file_name>|<current_time_epoch>"
4. Save this to /var/www/files/m5paper.txt on kcrt.net via scp
5. Implement error handling for file transfer
6. Optionally, user can select file via command line argument
"""

import os
import sys
import time
import subprocess
import argparse
from pathlib import Path

def list_sign_files():
    """List PNG files in the signs directory."""
    signs_dir = Path("/Users/kcrt/prog/M5Paper_myroom/data/signs")
    
    if not signs_dir.exists():
        print(f"Error: Directory {signs_dir} does not exist.")
        sys.exit(1)
    
    files = [f.name for f in signs_dir.iterdir() if f.is_file() and f.name.lower().endswith('.png')]
    files.sort()
    
    return files

def select_file(files, selected_file=None):
    """Let user select a file or use the provided file name."""
    if selected_file:
        if selected_file in files:
            return selected_file
        else:
            print(f"Error: File '{selected_file}' not found in signs directory.")
            print("Available files:")
            for i, file in enumerate(files, 1):
                print(f"{i}. {file}")
            sys.exit(1)
    
    if not files:
        print("No files found in the signs directory.")
        sys.exit(1)
    
    print("Available sign files:")
    for i, file in enumerate(files, 1):
        print(f"{i}. {file}")
    print("99. Input custom text")
    
    while True:
        try:
            choice = input("\nSelect a file or option (enter number): ")
            if choice == "99":
                text_message = input("Enter your text message: ")
                if len(text_message) > 40:
                    print("Text message too long. Please keep it under 40 characters.")
                    continue
                return f"text:{text_message}"
            
            index = int(choice) - 1
            if 0 <= index < len(files):
                return files[index]
            else:
                print(f"Please enter a number between 1 and {len(files)}, or 99 for text input.")
        except ValueError:
            print("Please enter a valid number.")

def construct_message(filename_or_text):
    """Construct the message string with filename and current epoch time (UTC+0)."""
    # Explicitly use UTC+0 for epoch time
    current_epoch = int(time.time())
    print(f"Current UTC epoch time: {current_epoch}")
    print(f"Human readable UTC time: {time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime(current_epoch))}")
    
    # Check if this is a text message
    if filename_or_text.startswith("text:"):
        return f"{filename_or_text}|{current_epoch}"
    else:
        return f"/signs/{filename_or_text}|{current_epoch}"

def save_to_remote(message):
    """Save the message to the remote server using scp."""
    # Create a temporary file
    temp_file = Path("/tmp/m5paper_temp.txt")
    try:
        with open(temp_file, "w") as f:
            f.write(message)
        
        # Use scp to transfer the file
        result = subprocess.run(
            ["scp", str(temp_file), "kcrt.net:/var/www/files/m5paper.txt"],
            capture_output=True,
            text=True
        )
        # print(f"Result: {result}")
        
        if result.returncode != 0:
            print(f"Error transferring file to server: {result.stderr}")
            return False
        
        print("File successfully transferred to server.")
        return True
    
    except Exception as e:
        print(f"Error: {e}")
        return False
    finally:
        # Clean up temporary file
        if temp_file.exists():
            temp_file.unlink()

def main():
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="M5Paper sign selector")
    parser.add_argument("file", nargs="?", help="Specific sign file to use")
    args = parser.parse_args()
    
    # List available files
    files = list_sign_files()
    
    # Select a file
    selected_file = select_file(files, args.file)
    print(f"Selected: {selected_file}")
    
    # Construct the message
    message = construct_message(selected_file)
    print(f"Message: {message}")
    
    # Save to remote server
    success = save_to_remote(message)
    
    if success:
        print("Sign updated successfully!")
    else:
        print("Failed to update sign. Please try again.")
        sys.exit(1)

if __name__ == "__main__":
    main()
