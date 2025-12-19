#!/usr/bin/env -S uv run
# /// script
# requires-python = ">=3.13"
# dependencies = [
#     "requests",
# ]
# ///

# List up journal article using PubMed API and output as tsv
# Usage: ./pubmed_listup_journal.py "Pediatric Allergy and Immunology" 2024-01-01 2024-12-31

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
    elapsed_time = datetime.now() - CurrentProcedureStart
    # Show in 0.000 sec
    print_info(f"[END] {CurrentProcedure} ({
               elapsed_time.total_seconds():.3f} sec)")


def parse_args():
    parser = argparse.ArgumentParser(description='List up journal files')
    parser.add_argument('journal_name', type=str,
                        help='Journal name (e.g. Pediatric Allergy and Immunology)')
    parser.add_argument('start_date', type=str,
                        help='Start date (e.g. 2024-01-01)')
    parser.add_argument('end_date', type=str, help='End date (e.g. 2024-12-31)',
                        default=datetime.today().strftime('%Y-%m-%d'))
    parser.add_argument('--dump-xml', action='store_true',
                        help='Dump XML for debug')
    parser.add_argument('--allow-many', action='store_true',
                        help='Allow to list up many articles')
    return parser.parse_args()


def get_article_details(article_ids: List[str], dump_xml: bool = False):
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
        pub_date = find_and_get('PubDate/Year') + ' ' + find_and_get('PubDate/Month')
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
        keywords = ', '.join([keyword.text for keyword in keywords])

        authors = [author.text for author in article.findall(
            './/Author/LastName')]
        authors = ', '.join(authors)
        print(f"{pmid}\t{doi}\t{title}\t{journal}\t{
              pub_type}\t{keywords}\t{pub_date}\t{authors}\t{abstract_all}")


def main():
    args = parse_args()

    start_procedure("Search articles")
    query = f"{args.journal_name}[Journal] AND ({args.start_date}:{
        args.end_date}[Date - Publication])"

    params = {
        'db': 'pubmed',
        'term': query,
        'retmode': 'json',
        'retmax': 1000
    }
    print_info(f"Searching articles from PubMed: Query = {query}")
    response = requests.get(PUBMED_ESEARCH_API, params=params)
    response.raise_for_status()
    result = response.json()
    end_procedure()

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

    GET_EVERY = 50
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
