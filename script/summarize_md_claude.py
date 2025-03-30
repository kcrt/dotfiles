#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Summarize the markdown file with Claude API
# Usage: ./summarize_md_claude.py <MARKDOWN_FILE>
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
    return parser.parse_args()

def call_claude_api(api_key, markdown_content):
    headers = {
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01",
        "Content-Type": "application/json"
    }
    
    prompt = f"""
Please analyze the following markdown document and provide:
1. A concise title that captures the main topic
2. A comprehensive summary of the key points and content in three to ten sentences

Format your response exactly like this:
Title: [The title you've determined]
Summary: [Your summary of the content]

Here is the markdown document:

{markdown_content}
"""
    
    data = {
        "model": "claude-3-7-sonnet-20250219",
        "max_tokens": 2000,
        "temperature": 0.0,
        "messages": [
            {"role": "user", "content": prompt}
        ]
    }
    
    response = requests.post(
        "https://api.anthropic.com/v1/messages",
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
    api_key = os.environ.get("CLAUDE_API_KEY")
    if not api_key:
        print("Please set the CLAUDE_API_KEY environment variable")
        sys.exit(1)
    
    with open(args.markdown_file, "r") as f:
        markdown = f.read()
    
    # Call Claude API
    response = call_claude_api(api_key, markdown)
    
    # Extract and print the response
    if "content" in response and len(response["content"]) > 0:
        content = response["content"][0]["text"]
    else:
        print("Error: Unexpected API response format")
        print(response)
        sys.exit(1)
    
    title = content.split("Title: ")[1].split("\n")[0]
    # Extract summary - handle both cases where summary is the last part or has content after it
    summary_part = content.split("Summary: ")[1]
    # If there are additional sections after Summary, only take the summary part
    if "\n\n" in summary_part:
        summary = summary_part.split("\n\n")[0]
    else:
        summary = summary_part

    print(f"Title: {title}")
    print(f"Summary: {summary}")

if __name__ == '__main__':
    main()
