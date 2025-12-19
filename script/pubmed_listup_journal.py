#!/usr/bin/env -S uv run
# /// script
# requires-python = ">=3.13"
# dependencies = [
#     "requests",
# ]
# ///

"""
PubMed Journal Article Lister

Fetches article metadata from PubMed API for a specific journal/date range and outputs as TSV.
Implements NCBI's E-Utilities API with error handling and batch processing.

Usage:
  # Journal-based search with date range:
  python listup_journal.py "Journal Name" YYYY-MM-DD YYYY-MM-DD [--keyword "search term"]

  # Custom PubMed query (without date filtering):
  python listup_journal.py --query "asthma[MeSH] AND 2024[PDAT]"

  # Custom PubMed query with date filtering:
  python listup_journal.py --query "asthma[MeSH]" --mindate 2024-01-01 --maxdate 2024-12-31

Options:
  --query         Custom PubMed query (overrides journal_name and keyword)
  --keyword       Keyword to search for in articles (only with journal mode)
  --mindate       Minimum date for filtering (use with --query)
  --maxdate       Maximum date for filtering (use with --query)
  --dump-xml      Save XML responses for debugging
  --allow-many    Skip confirmation for large result sets
  --debug         Enable debug output

Output Format:
  pmid | doi | title | journal | pub_type | keywords | pub_date | authors | abstract
  (TSV format with abstract newlines converted to <CR>)
"""
# Usage: python listup_journal.py "Pediatric Allergy and Immunology" 2024-01-01 2024-12-31 --keyword "allergy"
# Usage: python listup_journal.py --query "asthma[MeSH]" --mindate 2024-01-01 --maxdate 2024-12-31

import os
import sys
from typing import List
import requests
import xml.etree.ElementTree as ET
from datetime import datetime
import time
from pathlib import Path
import argparse

PUBMED_ESEARCH_API = 'https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi'   # ESearch
PUBMED_ESUMMARY_API = 'https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi'  # ESummary
PUBMED_EFETCH_API = 'https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi'     # EFetch

CurrentProcedure = None
CurrentProcedureStart = None


def print_info(message: str, no_cr: bool = False):
    """ Print information to stderr in aqua color """
    print(f'\033[96m{message}\033[0m',
          file=sys.stderr, end="" if no_cr else "\n")


def start_procedure(procedure_name: str):
    """ Start procedure """
    global CurrentProcedure, CurrentProcedureStart
    CurrentProcedure = procedure_name
    CurrentProcedureStart = datetime.now()
    print_info(f"[START] {procedure_name}" + ("-" * 20))


def end_procedure():
    global CurrentProcedure, CurrentProcedureStart
    if CurrentProcedureStart is not None:
        elapsed_time = datetime.now() - CurrentProcedureStart
        # Show in 0.000 sec
        print_info(f"[END] {CurrentProcedure} ({
                elapsed_time.total_seconds():.3f} sec)")
    else:
        print_info(f"[END] {CurrentProcedure}")


def parse_args():
    parser = argparse.ArgumentParser(description='List up journal files')
    parser.add_argument('journal_name', type=str, nargs='?',
                        help='Journal name (e.g. Pediatric Allergy and Immunology)')
    parser.add_argument('start_date', type=str, nargs='?',
                        help='Start date (e.g. 2024/01/01)')
    parser.add_argument('end_date', type=str, nargs='?',
                        help='End date (e.g. 2024/12/31)',
                        default=None)
    parser.add_argument('--query', type=str,
                        help='Custom PubMed query (overrides journal_name and keyword)')
    parser.add_argument('--keyword', type=str,
                        help='Keyword to search for in articles')
    parser.add_argument('--mindate', type=str,
                        help='Minimum date for filtering (e.g. 2024/01/01) - use with --query')
    parser.add_argument('--maxdate', type=str,
                        help='Maximum date for filtering (e.g. 2024/12/31) - use with --query')
    parser.add_argument('--dump-xml', action='store_true',
                        help='Dump XML for debug')
    parser.add_argument('--allow-many', action='store_true',
                        help='Allow to list up many articles')
    parser.add_argument('--debug', action='store_true',
                        help='Enable debug output')
    args = parser.parse_args()

    # Validation: either --query or journal_name must be provided
    if not args.query and not args.journal_name:
        parser.error('Either --query or journal_name must be provided')

    # If using journal_name mode, require start_date
    if args.journal_name and not args.start_date:
        parser.error('start_date is required when using journal_name')

    # Set default end_date if not provided (for journal_name mode)
    if args.end_date is None and args.start_date and args.journal_name:
        args.end_date = datetime.today().strftime('%Y/%m/%d')

    # For --query mode with --maxdate, set default if not provided
    if args.query and args.mindate and not args.maxdate:
        args.maxdate = datetime.today().strftime('%Y/%m/%d')

    return args


def get_article_details(article_ids: List[str], dump_xml: bool = False):
    """Fetch and parse detailed article metadata from PubMed EFetch API
    
    Args:
        article_ids: List of PubMed article IDs to fetch
        dump_xml: Save raw XML response for debugging
    
    Process:
        1. Calls EFetch API with comma-separated article IDs
        2. Parses XML response using ElementTree
        3. Extracts key metadata fields including:
           - Basic identifiers (PMID, DOI)
           - Title and publication info
           - Authors list (last names only)
           - Abstract text (concatenated if multiple sections)
           - Keywords and publication type
        4. Outputs TSV-formatted results to stdout
    """
    params = {
        'db': 'pubmed',
        'id': ','.join(article_ids),
        'retmode': 'xml'
    }
    response = requests.get(PUBMED_EFETCH_API, params=params)
    response.raise_for_status()
    xml = response.text

    if dump_xml:
        currenttime = datetime.now().strftime('%Y%m%d%H%M%S')
        xmlfilename = f"dump_{currenttime}.xml"
        with open(xmlfilename, 'w') as f:
            f.write(xml)

    root = ET.fromstring(xml)
    for article in root.findall('.//PubmedArticle'):
        print_info(".", no_cr=True)

        def find_and_get(key: str):
            element = article.find(f'.//{key}')
            if element is None:
                return ""
            return element.text

        pmid = find_and_get('PMID')
        doi = find_and_get('ArticleId[@IdType="doi"]')
        title = find_and_get('ArticleTitle')
        journal = find_and_get('Title')
        year = find_and_get('PubDate/Year') or ""
        month = find_and_get('PubDate/Month') or ""
        pub_date = f"{year} {month}".strip()
        pub_type = find_and_get('PublicationTypeList/PublicationType')
        abstracts = article.findall('.//Abstract/AbstractText')
        # if abstracts is list, connect all
        abstract_all = ""
        if type(abstracts) == list:
            for abstract in abstracts:
                label = abstract.attrib.get('Label', '')
                text = abstract.text
                abstract_all = abstract_all + f"{label}: {text}\n"
        else:
            abstract_all = ""
        abstract_all = abstract_all.replace('\n', '<CR>')

        keywords = article.findall(".//KeywordList/Keyword")
        keywords = ', '.join([keyword.text for keyword in keywords if keyword.text is not None])

        authors = [author.text for author in article.findall(
            './/Author/LastName') if author.text is not None]
        authors = ', '.join(authors)
        print(f"{pmid}\t{doi}\t{title}\t{journal}\t{
              pub_type}\t{keywords}\t{pub_date}\t{authors}\t{abstract_all}")


def main():
    """Main execution flow:
    1. Parse command line arguments
    2. Query ESearch API for article IDs matching criteria
    3. Handle large result sets with user confirmation
    4. Batch process results using EFetch API
    5. Implement rate limiting (5s between batches)
    6. Output final TSV results
    """
    args = parse_args()

    start_procedure("Search articles")

    # Build query based on mode
    if args.query:
        # Use custom query directly
        query = args.query
        print_info(f"Using custom query: {query}")
    else:
        # Build query from journal name and optional keyword
        query = f"\"{args.journal_name}\"[Journal]"

        # Add keyword search if provided
        if args.keyword:
            query += f" AND {args.keyword}[All Fields]"
            print_info(f"Keyword search with: {args.keyword}")

    # Build params based on whether dates are provided
    params = {
        'db': 'pubmed',
        'term': query,
        'retmode': 'json',
        'retmax': 1000,  # Maximum allowed by PubMed API
    }

    # Add date filters
    # For --query mode, use --mindate/--maxdate
    # For journal_name mode, use start_date/end_date
    mindate = args.mindate if args.query else args.start_date
    maxdate = args.maxdate if args.query else args.end_date

    if mindate and maxdate:
        params['datetype'] = 'pdat'
        params['mindate'] = mindate
        params['maxdate'] = maxdate
        print_info(f"Date range: {mindate} to {maxdate}")

    print_info(f"Searching articles from PubMed: Query = {query}")
    response = requests.get(PUBMED_ESEARCH_API, params=params)
    response.raise_for_status()
    result = response.json()
    end_procedure()

    if args.debug:
        print("DEBUG:", result)

    print_info(f"Translated query: {
               result['esearchresult']['querytranslation']}")
    count = int(result['esearchresult']['count'])
    if count == 0:
        print_info("No articles.")
        return
    else:
        print_info(f"Found {count} articles")
    article_ids = result['esearchresult']['idlist']

    # Ask if there are too many articles
    if not args.allow_many and count > 500:
        print_info(
            "Too many articles found. Would you like to continue? (y/n)")
        answer = input()
        if answer.lower() != 'y':
            print_info("Cancelled.")
            return

    start_procedure("Get article details")
    print("pmid\tdoi\ttitle\tjournal\tpub_type\tkeywords\tpub_date\tauthors\tabstract")

    GET_EVERY = 50  # Process in batches to avoid API limits
    for i in range(0, count, GET_EVERY):
        # show progress in format of "  51 -  100 / 1234"
        progress_str = f"{i+1:4}-{min(i+GET_EVERY, count):4} / {count:4}"
        print_info(f"Getting articles {progress_str}", no_cr=True)
        get_article_details(article_ids[i:i+GET_EVERY], args.dump_xml)
        time.sleep(5)
        print_info("")

    end_procedure()

    print_info("*** Done. ***")


if __name__ == '__main__':
    main()
