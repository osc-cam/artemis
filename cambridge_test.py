import csv
import datetime
import json
import logging
import logging.config
import os
import re
from pprint import pprint
from urllib.parse import unquote
from zenpy import Zenpy

from dspace_client import Dspace5Client
from artemis import VersionDetector
from secrets_local import zd_creds, downloads_folder, working_folder
from zd_fields import ZdFields

from utils.logos import PublisherLogo

logging.config.fileConfig('logging.conf', defaults={'logfilename':'cambridge_test.log'})
logger = logging.getLogger(__name__)


class TestCase():
    """
    Test object fulfilling all the right criteria for testing and storing all the required data
    """
    zd_ticket = None
    dspace_id = None
    dspace_item = None
    dspace_bitstreams = None


def parse_zd_ticket_description(description):
    """
    Extracts file versions and names from ticket original comment
    :param description: String containing the initial description of a ZD ticket
    :return:
    """

    def parse_filename(st):
        """
        Converts the filename extracted from the link in ZD to the value stored in DSpace
        :param st: filename extracted from the link in ZD
        :return:
        """
        return st.replace('+', ' ')

    orig_files = []
    t = re.compile(
        '^(?P<version>Accepted|Published|Submitted) version: (?P<link>.+)$',
        re.MULTILINE)
    matches = t.findall(description)
    m_counter = 0
    for m in matches:
        version = m[0]
        link = m[1]
        filename = parse_filename(unquote(link.split('%2F')[-1]))
        orig_files.append({
            "version": version,
            "link": link,
            "filename": filename,
        })
    return orig_files


def extract_list_of_authors_from_ds_metadata(metadata_list):
    """
    :param metadata_list: List of metadata fields returned by DSpace
    :return: list of authors extracted from metadata. Each author is represented by a tuple (name, orcid)
    """
    authors = []
    orcid = None
    orcid_pattern = re.compile('\d{4}-\d{4}-\d{4}-\d{4}')
    for meta in metadata_list:
        if meta['key'] == 'dc.contributor.author':
            name_orcid = meta['value']
            m = orcid_pattern.search(name_orcid)
            if m:
                orcid = m.group()
                author = name_orcid.replace('; orcid: {}'.format(orcid), '')
            else:
                author = name_orcid
            authors.append((author, orcid))
    return authors


OUTPUT_CSV = os.path.join(working_folder, "apollo_analysis.csv")

DSPACE_ID_TAG = "DSpace ID"

FIELDS_OF_INTEREST = {
    ZdFields.manuscript_title: "manuscript title",
    ZdFields.acceptance_date: "acceptance date",
    ZdFields.journal_title: "journal title",
    ZdFields.doi_like_10_123_abc456: "doi",
    ZdFields.publisher: "publisher",
    ZdFields.apollo_file_versions: "apollo file versions",
    ZdFields.fast_track_deposit_type: "ft deposit type",
}

today = datetime.datetime.now()
thirty_days_ago = today - datetime.timedelta(days=30)
yesterday = datetime.datetime.now() - datetime.timedelta(days=1)

def main():
    # Fetch tickets from ZD (as a list of dictionaries)
    # load from disk if possible; if not call Zendesk API and save to disk
    logger.info("Fetching ZD tickets")
    zd_tickets = []
    zenpy_client = Zenpy(**zd_creds)
    begin_datetime = datetime.datetime(2019,1,1,0,0,0,0)
    end_datetime = datetime.datetime(2019,1,31,0,0,0,0)
    zd_tickets_filepath = "zd_tickets.json"
    if os.path.exists(zd_tickets_filepath):
        with open(zd_tickets_filepath) as f:
            zd_tickets = json.load(f)
    else:
        for ticket in zenpy_client.search("Open Access enquiry has been received",
                                              created_between=[begin_datetime, end_datetime],
                                              type='ticket'):
            zd_tickets.append(ticket.to_dict())
        with open(zd_tickets_filepath, "w") as f:
            json.dump(zd_tickets, f)

    # Keep only tickets with zd_field_DspaceID not null
    # extract useful info from those tickets
    logger.info("Keeping only tickets with zd_field_DspaceID not null")
    _ = []
    for t in zd_tickets:
        include_ticket = False
        for c in t['custom_fields']:
            if (c['id'] == ZdFields.internal_item_id_apollo) and c['value']:
                t[DSPACE_ID_TAG] = c['value']
                include_ticket = True
                for k, v in FIELDS_OF_INTEREST.items():
                    if c['id'] == k:
                        t[v] = c['value']
        if include_ticket:
            t['original_files'] = parse_zd_ticket_description(t['description'])
            _.append(t)
    zd_tickets = _

    # Obtain the data and files we need from Apollo
    # Load from disk if possible; otherwise use API
    test_cases_filepath = "test_cases.json"
    if os.path.exists(test_cases_filepath):
        logger.info("Loading test cases from disk (delete {} "
                    "to collect from server instead)".format(test_cases_filepath))
        with open(test_cases_filepath) as f:
            test_cases = json.load(f)
    else:
        # Create a DSpace API client instance and login
        logger.info("Logging in to DSpace API")
        client = Dspace5Client()
        client.login()

        # Keep only tickets that:
        # 1-) have been archived in DSpace staging;
        # (i.e. we know what file version was made available/approved)
        logger.info("Collecting test cases")
        test_cases = []
        for t in zd_tickets:
            item = client.get_item(t[DSPACE_ID_TAG])
            if item['archived'] == 'true':
                bitstreams = client.get_item_bitstreams(t[DSPACE_ID_TAG])
                tc = TestCase()
                tc.zd_ticket = t
                tc.dspace_id = t[DSPACE_ID_TAG]
                tc.dspace_item = item
                tc.dspace_bitstreams = bitstreams
                test_cases.append(tc)
                # TODO: ged rid of this break when ready to test many cases
                if len(test_cases) > 10:
                    break
        with open(test_cases_filepath, "w") as f:
            json.dump(test_cases, f)

    # Changing wd to download folder
    os.chdir(downloads_folder)

    logger.info("Working on test cases")
    with open(OUTPUT_CSV, "w") as f:
        header = ["bitstream", "Apollo version", "outcome", "version/details"]
        csv_writer = csv.DictWriter(f, fieldnames=header, extrasaction='ignore')
        csv_writer.writeheader()
        for tc in test_cases[:19]:
            for bs in tc.dspace_bitstreams:
                if (bs['bundleName'] == 'ORIGINAL') and (bs['description'].lower() not in ['supporting information']):
                    if bs['name'] not in os.listdir(downloads_folder):
                        client.download_bitstream(bs['id'], downloads_folder)
                    vd = VersionDetector(os.path.join(downloads_folder, bs['name']),
                                         dec_ms_title=tc.dspace_item['name'],
                                         dec_version=bs['description'],
                                         dec_authors=extract_list_of_authors_from_ds_metadata(client.get_item_metadata(
                                             tc.dspace_id)),
                                         # **{'doi': 'foo'}
                                         )

                    # if vd.check_extension() == 'docx':  # restrict tests to docx for now
                    result = vd.detect()
                    logger.info(result)
                    row = {"bitstream": bs['name'],
                           "Apollo version": bs['description'],
                           "outcome": result[0],
                           "version/details": result[1]
                           }
                    csv_writer.writerow(row)

if __name__ == '__main__':
    logging.getLogger('chardet').setLevel(logging.WARNING) # disables debug messages from imported chardet module
    logging.getLogger('PIL').setLevel(logging.WARNING)  # disables debug messages from imported chardet module
    main()




