#!/usr/bin/env -S uv run
# -*- coding: utf-8 -*-
# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "requests",
# ]
# ///

import argparse
import base64
import os
import sys
from pathlib import Path
from typing import Optional
import requests


def get_next_filename(base_name: str = "ai", extension: str = "png") -> str:
    """Generate next available filename with incrementing number."""
    filename = f"{base_name}.{extension}"
    if not Path(filename).exists():
        return filename

    counter = 0
    while True:
        filename = f"{base_name}{counter:03d}.{extension}"
        if not Path(filename).exists():
            return filename
        counter += 1


def validate_model_size(model: str, size: str, mode: str = "draw") -> bool:
    """Validate size is compatible with the model."""
    valid_sizes = {
        "gpt-image-1.5": ["1024x1024", "1536x1024", "1024x1536"],
        "gpt-image-1": ["1024x1024", "1536x1024", "1024x1536"],
        "gpt-image-1-mini": ["1024x1024", "1536x1024", "1024x1536"],
        "dall-e-2": ["256x256", "512x512", "1024x1024"],
        "dall-e-3": ["1024x1024", "1792x1024", "1024x1792"],
    }

    return size in valid_sizes.get(model, [])


def determine_auto_size(model: str) -> str:
    """Determine default size for auto mode based on model."""
    if model.startswith("gpt-image") or model == "dall-e-3":
        return "1024x1024"
    elif model == "dall-e-2":
        return "1024x1024"
    return "1024x1024"


def generate_image(
    prompt: str,
    model: str = "gpt-image-1.5",
    size: str = "1024x1024",
    n: int = 1,
    background: Optional[str] = None,
    timeout: int = 300
) -> list[bytes]:
    """
    Generate image using OpenAI API.

    Args:
        prompt: The text prompt for image generation
        model: Model to use for generation
        size: Image size (must be compatible with model)
        n: Number of images to generate
        background: Background setting (auto/transparent/opaque) for gpt-image models
        timeout: Request timeout in seconds (default 300 for heavy operations)

    Returns:
        List of image data as bytes

    Raises:
        ValueError: If API key is not set or parameters are invalid
        requests.RequestException: If API request fails
    """
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY environment variable is not set")

    org_id = os.environ.get("OPENAI_ORG_ID")

    # Validate model and size combination
    if not validate_model_size(model, size):
        raise ValueError(f"Size {size} is not valid for model {model}")

    # Build request payload
    payload = {
        "model": model,
        "prompt": prompt,
        "n": n,
        "size": size
    }

    # Add model-specific parameters
    if model.startswith("gpt-image"):
        payload["moderation"] = "low"
        if background:
            payload["background"] = background
    else:
        # DALL-E models need response_format specified
        payload["response_format"] = "b64_json"

    # Build headers
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }

    if org_id:
        headers["OpenAI-Organization"] = org_id

    # Make API request with timeout
    print(f"Generating image with {model}...", file=sys.stderr)
    print(f"Timeout set to {timeout} seconds", file=sys.stderr)

    try:
        response = requests.post(
            "https://api.openai.com/v1/images/generations",
            headers=headers,
            json=payload,
            timeout=timeout
        )
        response.raise_for_status()
    except requests.Timeout:
        raise TimeoutError(
            f"Request timed out after {timeout} seconds. "
            "Try increasing timeout with --timeout option."
        )
    except requests.RequestException as e:
        if hasattr(e, 'response') and e.response is not None and hasattr(e.response, 'text'):
            error_msg = f"API request failed: {e.response.text}"
        else:
            error_msg = f"API request failed: {str(e)}"
        raise requests.RequestException(error_msg)

    # Parse response and decode images
    data = response.json()

    if "data" not in data:
        raise ValueError(f"Unexpected API response: {data}")

    images = []
    for item in data["data"]:
        if "b64_json" not in item:
            raise ValueError(f"No b64_json in response item: {item}")

        image_data = base64.b64decode(item["b64_json"])
        images.append(image_data)

    return images


def edit_image(
    prompt: str,
    image_paths: list[str],
    model: str = "dall-e-2",
    size: str = "1024x1024",
    n: int = 1,
    background: Optional[str] = None,
    mask_path: Optional[str] = None,
    timeout: int = 300
) -> list[bytes]:
    """
    Edit image using OpenAI API.

    Args:
        prompt: The text prompt describing the desired edit
        image_paths: List of image file paths to edit (up to 16 for gpt-image models, 1 for dall-e-2)
        model: Model to use for editing
        size: Image size (must be compatible with model)
        n: Number of images to generate
        background: Background setting (auto/transparent/opaque) for gpt-image models
        mask_path: Path to mask image (PNG with transparent areas indicating edit regions)
        timeout: Request timeout in seconds (default 300 for heavy operations)

    Returns:
        List of image data as bytes

    Raises:
        ValueError: If API key is not set or parameters are invalid
        requests.RequestException: If API request fails
    """
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY environment variable is not set")

    org_id = os.environ.get("OPENAI_ORG_ID")

    # Validate model
    if model not in ["dall-e-2", "gpt-image-1", "gpt-image-1.5", "gpt-image-1-mini"]:
        raise ValueError(f"Model {model} is not supported for edit mode. Only dall-e-2 and gpt-image models are supported.")

    # Validate image count
    if model == "dall-e-2" and len(image_paths) > 1:
        raise ValueError("dall-e-2 only supports editing one image at a time")
    if model.startswith("gpt-image") and len(image_paths) > 16:
        raise ValueError("gpt-image models support up to 16 images")

    # Validate model and size combination
    if not validate_model_size(model, size, mode="edit"):
        raise ValueError(f"Size {size} is not valid for model {model}")

    # Validate image files
    for img_path in image_paths:
        if not Path(img_path).exists():
            raise ValueError(f"Image file not found: {img_path}")

        # Check file size and format
        file_size = Path(img_path).stat().st_size
        if model == "dall-e-2":
            if file_size > 4 * 1024 * 1024:  # 4MB
                raise ValueError(f"Image file {img_path} must be less than 4MB for dall-e-2")
        elif model.startswith("gpt-image"):
            if file_size > 50 * 1024 * 1024:  # 50MB
                raise ValueError(f"Image file {img_path} must be less than 50MB for gpt-image models")

    # Validate mask file if provided
    if mask_path:
        if not Path(mask_path).exists():
            raise ValueError(f"Mask file not found: {mask_path}")
        if Path(mask_path).stat().st_size > 4 * 1024 * 1024:
            raise ValueError("Mask file must be less than 4MB")

    # Build multipart form data
    files = []
    for img_path in image_paths:
        files.append(('image[]' if model.startswith("gpt-image") else 'image',
                     (Path(img_path).name, open(img_path, 'rb'), 'image/png')))

    # Add mask if provided
    if mask_path:
        files.append(('mask', (Path(mask_path).name, open(mask_path, 'rb'), 'image/png')))

    # Build form data
    data = {
        'prompt': prompt,
        'model': model,
        'n': str(n),
        'size': size
    }

    # Add model-specific parameters
    if model.startswith("gpt-image"):
        if background:
            data['background'] = background
    else:
        # DALL-E models need response_format specified
        data['response_format'] = 'b64_json'

    # Build headers
    headers = {
        "Authorization": f"Bearer {api_key}"
    }

    if org_id:
        headers["OpenAI-Organization"] = org_id

    # Make API request with timeout
    print(f"Editing image with {model}...", file=sys.stderr)
    print(f"Timeout set to {timeout} seconds for heavy operation", file=sys.stderr)

    try:
        response = requests.post(
            "https://api.openai.com/v1/images/edits",
            headers=headers,
            data=data,
            files=files,
            timeout=timeout
        )
        response.raise_for_status()
    except requests.Timeout:
        raise TimeoutError(
            f"Request timed out after {timeout} seconds. "
            "Try increasing timeout with --timeout option."
        )
    except requests.RequestException as e:
        if hasattr(e, 'response') and e.response is not None and hasattr(e.response, 'text'):
            error_msg = f"API request failed: {e.response.text}"
        else:
            error_msg = f"API request failed: {str(e)}"
        raise requests.RequestException(error_msg)
    finally:
        # Close file handles
        for _, file_tuple in files:
            if hasattr(file_tuple[1], 'close'):
                file_tuple[1].close()

    # Parse response and decode images
    result_data = response.json()

    if "data" not in result_data:
        raise ValueError(f"Unexpected API response: {result_data}")

    images = []
    for item in result_data["data"]:
        if "b64_json" not in item:
            raise ValueError(f"No b64_json in response item: {item}")

        image_data = base64.b64decode(item["b64_json"])
        images.append(image_data)

    return images


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Generate or edit images using OpenAI's image API.",
        epilog="Examples:\n"
               "  Draw: %(prog)s 'A beautiful sunset' --save-to=sunset.png\n"
               "  Edit: %(prog)s 'Add a hat to the cat' --mode=edit --image=cat.png --save-to=cat_with_hat.png",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument(
        'prompt',
        type=str,
        help='Text prompt for image generation or editing'
    )

    parser.add_argument(
        '--mode',
        type=str,
        choices=['draw', 'edit'],
        default='draw',
        help='Operation mode: draw (generate new image) or edit (modify existing image). Default: draw'
    )

    parser.add_argument(
        '--image',
        type=str,
        action='append',
        help='Image file path(s) to edit (required for edit mode). Can be specified multiple times for gpt-image models (up to 16). Example: --image=img1.png --image=img2.png'
    )

    parser.add_argument(
        '--mask',
        type=str,
        default=None,
        help='Mask image path (PNG with transparent areas indicating where to edit). Optional for edit mode.'
    )

    parser.add_argument(
        '--save-to',
        type=str,
        default=None,
        help='Output filename (default: ai.png or ai000.png if exists)'
    )

    parser.add_argument(
        '--model',
        type=str,
        choices=['gpt-image-1.5', 'gpt-image-1', 'gpt-image-1-mini', 'dall-e-2', 'dall-e-3'],
        default='gpt-image-1.5',
        help='Model to use. For draw mode: any model (default: gpt-image-1.5). For edit mode: only dall-e-2 or gpt-image models (default: dall-e-2 if not specified)'
    )

    parser.add_argument(
        '--size',
        type=str,
        default='auto',
        help='Image size (default: auto). GPT models: 1024x1024, 1536x1024, 1024x1536. '
             'DALL-E 2: 256x256, 512x512, 1024x1024. DALL-E 3: 1024x1024, 1792x1024, 1024x1792'
    )

    parser.add_argument(
        '--background',
        type=str,
        choices=['auto', 'transparent', 'opaque'],
        default=None,
        help='Background setting (only for gpt-image models)'
    )

    parser.add_argument(
        '--n',
        type=int,
        default=1,
        help='Number of images to generate (default: 1)'
    )

    parser.add_argument(
        '--timeout',
        type=int,
        default=300,
        help='Request timeout in seconds (default: 300). Increase for heavy operations'
    )

    parser.add_argument(
        '--version',
        action='version',
        version='%(prog)s 1.0'
    )

    return parser.parse_args()


def main() -> None:
    """Main entry point."""
    args = parse_args()

    # Validate mode-specific requirements
    if args.mode == "edit":
        if not args.image:
            print("Error: --image is required for edit mode", file=sys.stderr)
            sys.exit(1)
        # Default to dall-e-2 for edit mode if user specified dall-e-3
        if args.model == "dall-e-3":
            print("Warning: dall-e-3 does not support edit mode. Switching to dall-e-2", file=sys.stderr)
            args.model = "dall-e-2"
    else:  # draw mode
        if args.image:
            print("Warning: --image is only used in edit mode, ignoring", file=sys.stderr)
        if args.mask:
            print("Warning: --mask is only used in edit mode, ignoring", file=sys.stderr)

    # Determine size
    size = args.size
    if size == 'auto':
        size = determine_auto_size(args.model)
        print(f"Auto-selected size: {size}", file=sys.stderr)

    # Validate background option
    if args.background and not args.model.startswith("gpt-image"):
        print(
            "Warning: --background is only supported for gpt-image models, ignoring",
            file=sys.stderr
        )
        background = None
    else:
        background = args.background

    try:
        # Generate or edit images based on mode
        if args.mode == "draw":
            images = generate_image(
                prompt=args.prompt,
                model=args.model,
                size=size,
                n=args.n,
                background=background,
                timeout=args.timeout
            )
        else:  # edit mode
            images = edit_image(
                prompt=args.prompt,
                image_paths=args.image,
                model=args.model,
                size=size,
                n=args.n,
                background=background,
                mask_path=args.mask,
                timeout=args.timeout
            )

        # Save images
        if args.n == 1:
            # Single image
            filename = args.save_to if args.save_to else get_next_filename()
            with open(filename, 'wb') as f:
                f.write(images[0])
            print(f"Image saved to: {filename}")
        else:
            # Multiple images
            base_name = args.save_to.rsplit('.', 1)[0] if args.save_to else "ai"
            extension = args.save_to.rsplit('.', 1)[1] if args.save_to and '.' in args.save_to else "png"

            for i, image_data in enumerate(images):
                filename = f"{base_name}_{i+1}.{extension}"
                with open(filename, 'wb') as f:
                    f.write(image_data)
                print(f"Image {i+1} saved to: {filename}")

    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except TimeoutError as e:
        print(f"Timeout Error: {e}", file=sys.stderr)
        sys.exit(2)
    except requests.RequestException as e:
        print(f"API Error: {e}", file=sys.stderr)
        sys.exit(3)
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        sys.exit(4)


if __name__ == '__main__':
    main()
