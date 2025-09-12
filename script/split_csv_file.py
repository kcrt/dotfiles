#!/usr/bin/env python3
import argparse
import sys
from pathlib import Path


def split_csv(input_file, lines_per_file=None, size_per_file=None, output_pattern=None):
    if lines_per_file is None and size_per_file is None:
        raise ValueError("Either lines_per_file or size_per_file must be specified")
    
    if input_file == '-':
        input_stream = sys.stdin
        if output_pattern is None:
            output_pattern = "stdin_splitted_{:05d}.csv"
    else:
        input_stream = open(input_file, 'r')
        if output_pattern is None:
            base_name = Path(input_file).stem
            output_pattern = f"{base_name}_splitted_{{:05d}}.csv"
    
    try:
        header = input_stream.readline()
        if not header:
            raise ValueError("Input file is empty")
        
        file_count = 1
        current_lines = 0
        current_size = 0
        current_file = None
        
        for line in input_stream:
            if current_file is None or should_create_new_file(current_lines, current_size, lines_per_file, size_per_file):
                if current_file:
                    current_file.close()
                
                output_filename = output_pattern.format(file_count)
                current_file = open(output_filename, 'w')
                current_file.write(header)
                
                current_lines = 1
                current_size = len(header)
                file_count += 1
            
            current_file.write(line)
            current_lines += 1
            if size_per_file:
                current_size += len(line)
        
        if current_file:
            current_file.close()
            
    finally:
        if input_file != '-' and input_stream:
            input_stream.close()


def should_create_new_file(current_lines, current_size, lines_per_file, size_per_file):
    if lines_per_file and current_lines >= lines_per_file:
        return True
    if size_per_file and current_size >= size_per_file:
        return True
    return False


def parse_size(size_str):
    size_str = size_str.upper().strip()
    multipliers = [
        ('GB', 1024*1024*1024),
        ('MB', 1024*1024),
        ('KB', 1024),
    ]
    
    for suffix, multiplier in multipliers:
        if size_str.endswith(suffix):
            return int(float(size_str[:-len(suffix)]) * multiplier)
    
    return int(size_str)


def main():
    parser = argparse.ArgumentParser(
        description='Split CSV file into multiple files with same header',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''Examples:
  %(prog)s -l 1000 data.csv                    # Split by 1000 lines per file
  %(prog)s -s 10MB data.csv                    # Split by 10MB per file  
  %(prog)s -l 500 -p "part_{:03d}.csv" data.csv  # Custom output pattern
  cat data.csv | %(prog)s -l 1000              # Read from stdin
        '''
    )
    
    parser.add_argument('filename', nargs='?', default='-',
                       help='CSV file to split (use - or omit for stdin)')
    
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('-l', '--lines', type=int,
                      help='Number of lines per output file')
    group.add_argument('-s', '--size', type=str,
                      help='Size per output file (e.g., 10MB, 1GB, 500K)')
    
    parser.add_argument('-p', '--pattern', type=str,
                       help='Output filename pattern (use {:05d} for file number)')
    
    args = parser.parse_args()
    
    try:
        size_bytes = None
        if args.size:
            size_bytes = parse_size(args.size)
        
        split_csv(
            input_file=args.filename,
            lines_per_file=args.lines,
            size_per_file=size_bytes,
            output_pattern=args.pattern
        )
        
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        print("\nInterrupted by user", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()

