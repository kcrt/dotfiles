#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Get abstract from PubMed using PMID or DOI
# Usage: python pubmed_get_abstract.py <PMID_or_DOI>

import sys
import time
import requests
import xml.etree.ElementTree as ET
import argparse
from typing import Optional

PUBMED_EFETCH_API = 'https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi'     # EFetch

def print_error(message: str):
    """ Print error message to stderr in red color """
    print(f'\033[91mERROR: {message}\033[0m', file=sys.stderr)

def get_abstract(identifier: str) -> Optional[str]:
    """
    Fetches the abstract for a given PMID or DOI from PubMed.

    Args:
        identifier: The PMID or DOI of the article.

    Returns:
        The abstract text as a single string, or None if not found or an error occurs.
    """
    params = {
        'db': 'pubmed',
        'id': identifier,
        'retmode': 'xml',
        'rettype': 'abstract' # Request abstract type specifically
    }

    try:
        response = requests.get(PUBMED_EFETCH_API, params=params)
        response.raise_for_status()  # Raise an exception for bad status codes
        xml_content = response.text
        root = ET.fromstring(xml_content)
        article = root.find('.//PubmedArticle')

        if article is None:
            # Sometimes the structure might be different, try finding AbstractText directly
            abstract_elements = root.findall('.//AbstractText')
            if not abstract_elements:
                 # Check if it's an error response from NCBI
                error_msg = root.find('.//ERROR')
                if error_msg is not None:
                    print_error(f"PubMed API returned an error for identifier '{identifier}': {error_msg.text}")
                    return None
                else:
                    print_error(f"Could not find article or abstract structure for identifier '{identifier}'.")
                    return None
        else:
            abstract_elements = article.findall('.//Abstract/AbstractText')

        if not abstract_elements:
            # Check for BookDocument structure as well
            abstract_elements = root.findall('.//BookDocument/Abstract/AbstractText')

        if not abstract_elements:
            print_error(f"No abstract found for identifier '{identifier}'.")
            return None

        # Combine abstract parts if necessary
        abstract_parts = []
        for elem in abstract_elements:
            # Use itertext() to get all text content, including child elements like <i> or <sub>
            text = "".join(elem.itertext()).strip()
            if text:
                label = elem.attrib.get('Label')
                if label:
                    # Ensure label is only added once per AbstractText element
                    abstract_parts.append(f"{label}: {text}")
                else:
                    abstract_parts.append(text)

        return "\n".join(abstract_parts)

    except requests.exceptions.RequestException as e:
        print_error(f"Network or HTTP error occurred: {e}")
        return None
    except ET.ParseError as e:
        print_error(f"Error parsing XML response: {e}")
        # Optionally print the problematic XML for debugging
        # print_error(f"XML Content:\n{xml_content}")
        return None
    except Exception as e:
        print_error(f"An unexpected error occurred: {e}")
        return None


def main():
    parser = argparse.ArgumentParser(description='Get abstract from PubMed using PMID or DOI.')
    parser.add_argument('identifier', type=str, help='PMID or DOI of the article')
    args = parser.parse_args()

    abstract = get_abstract(args.identifier)

    if abstract:
        print(abstract)
    else:
        # Error messages are printed within get_abstract
        sys.exit(1) # Exit with error code if abstract retrieval failed
    
    # Sleep
    time.sleep(3)

if __name__ == '__main__':
    main()
