#!/usr/bin/env python3

# Draw a barcode

import argparse
import barcode
from barcode.writer import ImageWriter


def generate_barcode(barcode_type, text, output_file):
    try:
        # 指定されたバーコードの種類を取得
        barcode_class = barcode.get_barcode_class(barcode_type)

        # バーコードオブジェクトを作成し、画像として保存
        barcode_obj = barcode_class(text, writer=ImageWriter())
        barcode_obj.save(output_file)

        print(f"Barcode saved as {output_file}.png")
    except Exception as e:
        print(f"Error generating barcode: {e}")


def main():
    parser = argparse.ArgumentParser(description="Generate barcode images.")
    parser.add_argument("barcode_type", type=str,
                        help="Type of the barcode (e.g., code39, ean13)")
    parser.add_argument("text", type=str, help="Text to encode in the barcode")
    parser.add_argument("output_file", type=str,
                        help="Name of the output file (without extension)")

    args = parser.parse_args()

    generate_barcode(args.barcode_type, args.text, args.output_file)


if __name__ == "__main__":
    main()
