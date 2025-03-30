#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from mistralai import Mistral, DocumentURLChunk, OCRResponse
from pathlib import Path
import json
import os
import argparse
from typing import Optional, Union, Dict, Any


# MistralAI team code ---
def replace_images_in_markdown(markdown_str: str, images_dict: dict) -> str:
    for img_name, base64_str in images_dict.items():
        markdown_str = markdown_str.replace(f"![{img_name}]({img_name})", f"![{img_name}]({base64_str})")
    return markdown_str

def get_combined_markdown(ocr_response: OCRResponse) -> str:
  markdowns: list[str] = []
  for page in ocr_response.pages:
    image_data = {}
    for img in page.images:
      image_data[img.id] = img.image_base64
    markdowns.append(replace_images_in_markdown(page.markdown, image_data))

  return "\n\n".join(markdowns)
# ---

def parse_args():
    parser = argparse.ArgumentParser(description='Mistral OCR')
    parser.add_argument("input", type=str, help='Input file path (pdf)')
    parser.add_argument("output", type=str, help='Output file path (Markdown)')
    parser.add_argument('--debug', action='store_true', help='Debug mode')
    parser.add_argument('--no-image', action='store_true', help='Do not include images in output')
    return parser.parse_args()


def process_ocr(
    input_file: Union[str, Path], 
    output_file: Union[str, Path], 
    include_images: bool = True, 
    debug: bool = False, 
    api_key: Optional[str] = None,
    verbose: bool = True
) -> Dict[str, Any]:
    """
    Process a PDF file with Mistral OCR and save the result as Markdown.
    
    Args:
        input_file: Path to the input PDF file
        output_file: Path where the output Markdown file will be saved
        include_images: Whether to include images in the output
        debug: Whether to save debug information
        api_key: Mistral API key (if None, will use MISTRALAI_API_KEY environment variable)
        verbose: Whether to print progress messages
        
    Returns:
        Dictionary containing the OCR response data
    """
    if verbose:
        print(f"Input file: {input_file}")
        print(f"Output file: {output_file}")
        print(f"Image included: {include_images}")

    # Get API key from parameter or environment variable
    if api_key is None:
        api_key = os.getenv('MISTRALAI_API_KEY')
        if api_key is None:
            raise ValueError("API key not provided and MISTRALAI_API_KEY environment variable not set")
    
    client = Mistral(api_key=api_key)

    # Ensure input file is a Path object and exists
    in_file = Path(input_file)
    if not in_file.is_file():
        raise FileNotFoundError(f"Input file not found: {in_file}")

    if verbose:
        print(f"Uploading file...")
    uploaded_file = client.files.upload(
        file={
            "file_name": in_file.stem,
            "content": in_file.read_bytes()
        },
        purpose="ocr"  # type: ignore
    )
    signed_url = client.files.get_signed_url(file_id=uploaded_file.id, expiry=1)

    if verbose:
        print(f"Signed URL: {signed_url}")
        print(f"Processing OCR...")
    
    pdf_response = client.ocr.process(
        document=DocumentURLChunk(document_url=signed_url.url),
        model="mistral-ocr-latest",
        include_image_base64=include_images)
    
    if verbose:
        print("Done.")

    # Convert response to dictionary
    response_dict = json.loads(pdf_response.model_dump_json())
    json_string = json.dumps(response_dict, indent=4, ensure_ascii=False)

    if debug:
        result_file = Path("./debug.json")
        result_file.write_text(json_string, encoding="utf-8")
        if verbose:
            print(f"Debug info saved to {result_file}")

    # Save as Markdown format
    if not include_images:
        # When no images are included, just use the markdown directly
        markdown_string = "\n\n".join([page.markdown for page in pdf_response.pages])
    else:
        markdown_string = get_combined_markdown(pdf_response)
    
    markdown_file = Path(output_file)
    markdown_file.write_text(markdown_string, encoding="utf-8")
    
    if verbose:
        print(f"Markdown file saved to {markdown_file}")
    
    return response_dict


def main():
    args = parse_args()
    
    try:
        process_ocr(
            input_file=args.input,
            output_file=args.output,
            include_images=not args.no_image,
            debug=args.debug
        )
    except Exception as e:
        print(f"Error: {e}")
        return 1
    
    return 0

if __name__ == '__main__':
    exit_code = main()
    exit(exit_code)
