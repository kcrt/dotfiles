#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Summarize the markdown file with local Ollama model using gemma3:27b
# Usage: ./summarize_md_ollama.py <MARKDOWN_FILE>
# Output Format is like this:
# Title: <TITLE_OF_THIS_MARKDOWN_FILE> 
# Summary: <SUMMARY_OF_THIS_MARKDOWN_FILE>

import argparse
import os
import sys
import requests
import json

def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("markdown_file", help="The markdown file to summarize")
    parser.add_argument("--debug", action="store_true", help="Enable debug mode")
    return parser.parse_args()

def call_ollama_api(markdown_content):
    headers = {
        "Content-Type": "application/json"
    }
    
    prompt = f"""
Please analyze the following markdown document and provide a comprehensive summary of the key points and content in three to ten sentences

Here is the markdown document:
{markdown_content}
"""
    
    data = {
        "model": "gemma3:27b-it-qat",
        "prompt": prompt,
        "stream": False
    }
    
    response = requests.post(
        "http://localhost:11434/api/generate",
        headers=headers,
        json=data
    )
    
    if response.status_code != 200:
        print(f"Error: API request failed with status code {response.status_code}")
        print(response.text)
        sys.exit(1)
        
    return response.json()

def main():
    args = parse_args()
    
    with open(args.markdown_file, "r") as f:
        markdown = f.read()
    
    # Call Ollama API
    response = call_ollama_api(markdown)
    
    # Extract and print the response
    if "response" in response:
        content = response["response"]
    else:
        print("Error: Unexpected API response format")
        print(response)
        sys.exit(1)

    print(content)

if __name__ == '__main__':
    main()
