#!/usr/bin/env -S uv run
# -*- coding: utf-8 -*-
# /// script
# requires-python = ">=3.14"
# dependencies = [
#     "pillow",
# ]
# ///

from PIL import Image, ImageDraw

ICON_SIZE = 16

def create_error_icon() -> Image.Image:
    """Create a red X icon for errors."""
    img = Image.new('RGBA', (ICON_SIZE, ICON_SIZE), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Draw red X
    padding = 3
    draw.line([(padding, padding), (ICON_SIZE - padding, ICON_SIZE - padding)],
              fill=(220, 50, 50, 255), width=2)
    draw.line([(ICON_SIZE - padding, padding), (padding, ICON_SIZE - padding)],
              fill=(220, 50, 50, 255), width=2)

    return img


def create_warning_icon() -> Image.Image:
    """Create a yellow/orange warning icon with exclamation."""
    img = Image.new('RGBA', (ICON_SIZE, ICON_SIZE), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Draw triangle
    padding = 2
    points = [
        (ICON_SIZE // 2, padding),
        (ICON_SIZE - padding, ICON_SIZE - padding),
        (padding, ICON_SIZE - padding),
    ]
    draw.polygon(points, fill=(255, 180, 0, 230), outline=(200, 140, 0, 255))

    # Draw exclamation mark
    center_x = ICON_SIZE // 2
    draw.rectangle((center_x - 1, 5, center_x + 1, 9), fill=(0, 0, 0, 255))
    draw.rectangle((center_x - 1, 11, center_x + 1, 11), fill=(0, 0, 0, 255))

    return img


def create_info_icon() -> Image.Image:
    """Create a blue information icon with 'i'."""
    img = Image.new('RGBA', (ICON_SIZE, ICON_SIZE), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Draw circle
    padding = 2
    bbox = (padding, padding, ICON_SIZE - padding, ICON_SIZE - padding)
    draw.ellipse(bbox, fill=(60, 140, 220, 230), outline=(40, 100, 180, 255))

    # Draw 'i' dot
    center_x = ICON_SIZE // 2
    draw.ellipse((center_x - 1, 4, center_x + 1, 6), fill=(255, 255, 255, 255))

    # Draw 'i' body
    draw.rectangle((center_x - 1, 7, center_x + 1, 13), fill=(255, 255, 255, 255))

    return img


def main():
    base_dir = '/Users/kcrt/dotfiles/materials/image'

    create_error_icon().save(f'{base_dir}/lsp_error.png')
    print(f'Created: {base_dir}/lsp_error.png')

    create_warning_icon().save(f'{base_dir}/lsp_warning.png')
    print(f'Created: {base_dir}/lsp_warning.png')

    create_info_icon().save(f'{base_dir}/lsp_information.png')
    print(f'Created: {base_dir}/lsp_information.png')


if __name__ == '__main__':
    main()
