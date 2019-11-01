'''
A simple and incomplete client for the DSpace 5 API
'''

import getpass
import logging
import logging.config
import json
import os
import re
import requests
import subprocess
import textract
import urllib.request
import xml.etree.ElementTree as ET
from docx import Document
from pprint import pprint
from PyPDF2 import PdfFileReader

from secrets_local import apollo_creds

# create logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
# create console handler and set level to debug
ch = logging.StreamHandler()
ch.setLevel(logging.INFO)
# create formatter
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
# add formatter to ch
ch.setFormatter(formatter)
# add ch to logger
# logger.addHandler(ch)

class ApiUser():
    def __init__(self, email=apollo_creds['email'], password=apollo_creds['password']):
        self.email = email
        # self.password = getpass.getpass()
        self.password = password

class Dspace5Client():
    '''
    A minimal Dspace5client containing only the methods we need for testing.
    '''
    endpoint = 'https://dspace-staging.lib.cam.ac.uk/rest/'
    bs_ep = endpoint + 'bitstreams/'
    items_ep = endpoint + 'items/'
    token = None
    header = None
    s = requests.Session()

    def login(self):
        epoint = self.endpoint + 'login'
        api_user = ApiUser()
        r = self.s.post(epoint, json={'email': api_user.email, 'password': api_user.password})
        self.token = r.text
        logger.debug("Status code: {}; DSpace token: {}".format(r.status_code, self.token))

    def prepare_header(self, content_type):
        """
        Modified from: https://github.com/UKUK-Repository-Dept/dsapy

        Prepares DSpace headers based on provided DSpace API token and request content-type.

        Check if DSpace API token is None and replaces in with correct 'null' value if it is
        (this should only be true when connecting to DSpace API).
        Then, headers dictionary is created.

        Without DSpace API token some requests might not work.

        :param content_type: 'json' or 'xml'
        :return:
        """
        if not self.token:
            api_token = 'null'
        else:
            api_token = self.token

        self.header = {'rest-dspace-token': str(api_token),
                   'accept': 'application/' + content_type,
                   'Accept-Charset': 'UTF-8',
                   'Content-Type': 'application/' + content_type}

    def get_items(self, offset=0):
        '''
        Use the offset parameter for paging. Each page contains 100 items by default
        :param offset: use 0 for page 1, 100 for page 2...
        :return:
        '''
        r = self.s.get(self.items_ep.rstrip('/') + '?offset=' + str(offset), headers=self.header)
        items = r.json()
        logger.debug("Status code: {}; len(items): {}; Items: {}".format(r.status_code, len(items), items))
        return items

    def get_item(self, item_id):
        if not self.header:
            self.prepare_header('json')
        r = self.s.get(self.items_ep + str(item_id), headers=self.header)
        if r.ok:
            logger.debug("item_id: {}; status code: {}; r.text: {}".format(item_id, r.status_code, r.text))
            return r.json()
        else:
            logger.error("Item_id {} could not be found; perhaps it is not available in staging yet? "
                         "(Status code: {}; r.text: {})".format(item_id, r.status_code, r.text))
            return None

    def get_item_metadata(self, item_id):
        r = self.s.get(self.items_ep + str(item_id) + '/metadata', headers=self.header)
        info = r.json()
        logger.debug("Status code: {}; len(item_bs): {}; item_bs: {}".format(r.status_code, len(info), info))
        return info

    def get_item_bitstreams(self, item_id):
        if not self.header:
            self.prepare_header('json')
        r = self.s.get(self.items_ep + str(item_id) + '/bitstreams', headers=self.header)
        if r.ok:
            logger.debug("item_id: {}; status code: {}; r.text: {}".format(item_id, r.status_code, r.text))
            return r.json()
        else:
            logger.error("Item_id {} could not be found; perhaps it is not available in staging yet? "
                         "(Status code: {}; r.text: {})".format(item_id, r.status_code, r.text))
            return None

    def find_by_metadata_field(self, offset=0, **kwargs):
        '''
        See https://wiki.duraspace.org/display/DSDOC5x/REST+API?focusedCommentId=68068154#comment-68068154 for
        example

        Problem: The DSpace5 API does not support the offset parameter for this method, so the maximum number of items
        that can be recovered using this function is 100.

        :param kwargs: Dictionary containing metadata description. Example:
            '{"key": "dc.title","value": "Test Webpage","language": "en_US"}'
        :return:
        '''
        print(kwargs)
        # r = self.s.post('https://demo.dspace.org/rest/items/find-by-metadata-field', json={"key": "dc.title","value": "Test Webpage","language": "en_US"})
        r = self.s.post(self.items_ep + '/find-by-metadata-field?offset=' + str(offset), json=kwargs)
        print(r.text)
        print(r.status_code)
        info = r.json()
        logger.info("Status code: {}; len(info): {}; info: {}".format(r.status_code, len(info), info))
        return info

    def download_bitstream(self, bs_id, dest_folder):
        logger.debug("bs_id: {}; dest_folder: {}".format(bs_id, dest_folder))
        r = self.s.get(self.bs_ep + str(bs_id), headers=self.header)
        logger.debug("Status code: {}; r.text: {}".format(r.status_code, r.text))
        path = os.path.join(dest_folder, r.json()['name'])
        r = self.s.get(self.bs_ep + str(bs_id) + '/retrieve', headers=self.header)
        with open(path, 'wb') as out:
            out.write(r.content)

    # def get_all_bitstreams(self):
    #     if not self.token:
    #         self.login()
    #     r = self.s.get(self.bs_ep, json={'rest-dspace-token': self.token})
    #     print(r.status_code)
    #     print(r.content)

class DSpace5Item():
    '''
    Class representing an Item (record) in DSpace
    '''

    client = Dspace5Client()

    def __init__(self, id, metadata=None, bitstreams=None):
        self.id = id
        self.metadata = metadata
        self.bitstreams = bitstreams

    def get_metadata(self):
        self.metadata = self.client.get_item_metadata(self.id)

    def get_bitstreams(self):
        self.bitstreams = self.client.get_item_bitstreams(self.id)

    def metadata_filter(self, accept=True, **kwargs):
        '''
        Filters items based on values of metadata fields
        :param accept: boolean; if True, items matching kwargs are retained (function returns True); if false,
            matching items are rejected (function returns False)
        :param kwargs: Dictionary of metadata field keys and list of values to accept/reject
            (e.g. {'dc.type': ['article', 'conference object', 'journal article'])
        :return: True for retain; False for reject
        '''
        if not self.metadata:
            self.get_metadata()

        if accept:
            accept_item = False # reject by default (picking mode)
        else:
            accept_item = True # accept by default (pruning mode)
        for m in self.metadata:
            if m["key"] in kwargs.keys():
                if m["value"].lower() in kwargs[m["key"]]:
                    if accept:
                        accept_item = True  # accept match (picking mode)
                    else:
                        accept_item = False  # reject match (pruning mode)
        return accept_item
