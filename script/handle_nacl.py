#!/usr/bin/env -S uv run
# /// script
# requires-python = ">=3.13"
# dependencies = [
#     "pynacl",
#     "python-dotenv",
# ]
# ///

# This script is under development!

# -*- coding: utf-8 -*-

import argparse
import os
import sys
import subprocess
import hashlib
from io import StringIO
from pathlib import Path
from typing import Tuple
from nacl.secret import SecretBox
from dotenv import dotenv_values

# Global verbose flag
VERBOSE = False

def if_verbose(message: str) -> None:
    """Print message to stderr if verbose mode is enabled"""
    if VERBOSE:
        print(message, file=sys.stderr)

def derive_key(encryption_key: str, salt: str) -> bytes:
    """Derive a 32-byte key from encryption_key and salt using BLAKE2b"""
    if_verbose("Deriving key from encryption_key and salt...")
    
    # Check key and salt lengths and warn if needed
    if len(encryption_key) < 16:
        if_verbose(f"WARNING: Encryption key is short ({len(encryption_key)} chars), consider using a longer key for better security")
    elif len(encryption_key) > 64:
        if_verbose(f"WARNING: Encryption key is long ({len(encryption_key)} chars), excess will be hashed")
    
    if len(salt) < 8:
        if_verbose(f"WARNING: Salt is short ({len(salt)} chars), consider using a longer salt for better security")
    elif len(salt) > 32:
        if_verbose(f"WARNING: Salt is long ({len(salt)} chars), excess will be hashed")
    
    # Combine key and salt
    key_material = (encryption_key + salt).encode('utf-8')
    
    # Use BLAKE2b to derive exactly 32 bytes
    derived_key = hashlib.blake2b(key_material, digest_size=32).digest()
    
    if_verbose(f"Derived key of length: {len(derived_key)} bytes")
    return derived_key

def load_keys() -> Tuple[str, str]:
    """Load ENCRYPTION_KEY and SALT from environment variables first, then from files"""
    # Check environment variables first
    env_encryption_key = os.getenv('ENCRYPTION_KEY')
    env_salt = os.getenv('SALT')
    
    if env_encryption_key and env_salt:
        if_verbose("Using ENCRYPTION_KEY and SALT from environment variables")
        if_verbose(f"ENCRYPTION_KEY: {env_encryption_key[:2]}{'*' * (len(env_encryption_key) - 2)}")
        if_verbose(f"SALT: {env_salt[:2]}{'*' * (len(env_salt) - 2)}")
        return env_encryption_key, env_salt
    
    # Fall back to file-based loading
    if_verbose("Environment variables not found, checking files...")
    keys_env_path = Path("keys.env")
    keys_gpg_path = Path("keys.env.gpg")
    
    if keys_env_path.exists():
        if_verbose(f"Found keys.env file: {keys_env_path}")
        return load_env_file(keys_env_path)
    elif keys_gpg_path.exists():
        if_verbose(f"Found encrypted keys file: {keys_gpg_path}")
        return load_gpg_file(keys_gpg_path)
    else:
        raise FileNotFoundError("ENCRYPTION_KEY and SALT not found in environment variables, keys.env, or keys.env.gpg")

def load_env_file(file_path: Path) -> Tuple[str, str]:
    """Load environment variables from a plain .env file using python-dotenv"""
    if_verbose(f"Reading environment variables from: {file_path}")
    
    env_vars = dotenv_values(file_path)
    
    for key in env_vars:
        if_verbose(f"Loaded variable: {key}")
    
    if 'ENCRYPTION_KEY' not in env_vars or 'SALT' not in env_vars:
        raise ValueError("ENCRYPTION_KEY and SALT must be present in keys.env")
    
    if_verbose("Successfully loaded ENCRYPTION_KEY and SALT")
    if_verbose(f"ENCRYPTION_KEY: {env_vars['ENCRYPTION_KEY'][:2]}{'*' * (len(env_vars['ENCRYPTION_KEY']) - 2)}")
    if_verbose(f"SALT: {env_vars['SALT'][:2]}{'*' * (len(env_vars['SALT']) - 2)}")
    
    return env_vars['ENCRYPTION_KEY'], env_vars['SALT']

def load_gpg_file(file_path: Path) -> Tuple[str, str]:
    """Load environment variables from a GPG encrypted .env file"""
    if_verbose(f"Processing encrypted file: {file_path}")
    
    try:
        # Decrypt GPG file to memory
        if_verbose("Decrypting GPG file to memory...")
        decrypt_result = subprocess.run(['gpg', '--decrypt', str(file_path)], 
                                      check=True, capture_output=True)
        env_content = decrypt_result.stdout.decode('utf-8')
        
        # Parse environment variables from memory using dotenv
        if_verbose("Parsing environment variables from memory")
        
        # Write content to a temporary string stream for dotenv_values
        env_stream = StringIO(env_content)
        env_vars = dotenv_values(stream=env_stream)
        
        for key in env_vars:
            if_verbose(f"Loaded variable: {key}")
        
        if 'ENCRYPTION_KEY' not in env_vars or 'SALT' not in env_vars:
            raise ValueError("ENCRYPTION_KEY and SALT must be present in keys.env")
        
        if_verbose("Successfully loaded ENCRYPTION_KEY and SALT from encrypted file")
        if_verbose(f"ENCRYPTION_KEY: {env_vars['ENCRYPTION_KEY'][:2]}{'*' * (len(env_vars['ENCRYPTION_KEY']) - 2)}")
        if_verbose(f"SALT: {env_vars['SALT'][:2]}{'*' * (len(env_vars['SALT']) - 2)}")
        
        return env_vars['ENCRYPTION_KEY'], env_vars['SALT']
        
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"Failed to decrypt GPG file: {e}")
    except Exception as e:
        raise RuntimeError(f"Error processing encrypted file: {e}")

def parsearg() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Encrypt or decrypt NaCl strings using keys from environment variables, keys.env or keys.env.gpg")
    parser.add_argument('--version', action='version', version='%(prog)s 0.1')
    parser.add_argument('--verbose', '-v', action='store_true', help='Enable verbose output')
    parser.add_argument('--encrypt', '-e', action='store_true', help='Encrypt mode (default is decrypt)')
    parser.add_argument('input_string', nargs='?', help='String to encrypt/decrypt (if not provided, reads from stdin)')
    return parser.parse_args()

def get_input_string(args: argparse.Namespace) -> str:
    """Get the input string from command line argument or stdin"""
    if args.input_string:
        mode = "encrypted" if not args.encrypt else "plain"
        if_verbose(f"Using {mode} string from command line argument")
        return args.input_string
    else:
        mode = "encrypted" if not args.encrypt else "plain"
        if_verbose(f"Reading {mode} string from stdin")
        if sys.stdin.isatty():
            action = "encrypt" if args.encrypt else "decrypt"
            print(f"Enter string to {action} (press Enter when done):")
        input_data = sys.stdin.read().strip()
        if_verbose(f"Read {len(input_data)} characters from stdin")
        return input_data

def decrypt_string(encrypted_string: str, encryption_key: str, salt: str) -> str:
    """Decrypt the encrypted string using NaCl with the provided key and salt"""
    try:
        if_verbose("Starting decryption process...")
        if_verbose(f"Encrypted string length: {len(encrypted_string)} characters")
        
        # Decode the hex encrypted string
        if_verbose("Decoding hex encrypted string...")
        encrypted_data = bytes.fromhex(encrypted_string)
        
        # Derive the key using salt
        key = derive_key(encryption_key, salt)
        
        # Create SecretBox with the derived key
        if_verbose("Creating NaCl SecretBox...")
        box = SecretBox(key)
        
        # Decrypt the data
        if_verbose("Decrypting data...")
        decrypted_data = box.decrypt(encrypted_data)
        
        # Return as string
        result = decrypted_data.decode('utf-8')
        if_verbose(f"Successfully decrypted {len(result)} characters")
        
        return result
        
    except Exception as e:
        raise ValueError(f"Decryption failed: {e}")

def encrypt_string(plain_string: str, encryption_key: str, salt: str) -> str:
    """Encrypt the plain string using NaCl with the provided key and salt"""
    try:
        if_verbose("Starting encryption process...")
        if_verbose(f"Plain string length: {len(plain_string)} characters")
        
        # Derive the key using salt
        key = derive_key(encryption_key, salt)
        
        # Create SecretBox with the derived key
        if_verbose("Creating NaCl SecretBox...")
        box = SecretBox(key)
        
        # Encrypt the data
        if_verbose("Encrypting data...")
        plain_data = plain_string.encode('utf-8')
        encrypted_data = box.encrypt(plain_data)
        
        # Return as hex string
        result = encrypted_data.hex()
        if_verbose(f"Successfully encrypted to {len(result)} hex characters")
        
        return result
        
    except Exception as e:
        raise ValueError(f"Encryption failed: {e}")

def main() -> None:
    global VERBOSE
    try:
        args = parsearg()
        VERBOSE = args.verbose
        
        if_verbose("Starting decrypt_nacl.py in verbose mode")
        
        # Load encryption keys
        encryption_key, salt = load_keys()
        
        # Get input string
        input_string = get_input_string(args)
        
        if not input_string:
            action = "encrypt" if args.encrypt else "decrypt"
            print(f"Error: No string provided to {action}", file=sys.stderr)
            sys.exit(1)
        
        # Process based on mode
        if args.encrypt:
            # Encrypt mode
            encrypted_text = encrypt_string(input_string, encryption_key, salt)
            if_verbose("Encryption completed successfully")
            print(encrypted_text)
        else:
            # Decrypt mode (default)
            decrypted_text = decrypt_string(input_string, encryption_key, salt)
            if_verbose("Decryption completed successfully")
            print(decrypted_text)
        
    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except RuntimeError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == '__main__':
    main()

