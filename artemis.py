import chardet
from difflib import SequenceMatcher
import logging
import logging.config
import os
import regex
import shelve
import subprocess
import textract
import xml.etree.ElementTree as ET
from docx import Document
from pprint import pprint
from PyPDF2 import PdfFileReader
from PIL import Image
import imagehash

from utils.patterns import DOI_PATTERN, ALL_CC_LICENCES, RIGHTS_RESERVED_PATTERNS, PROOF_PATTERNS
from utils.logos import PublisherLogo

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

# LOGOS_DB_PATH = os.path.join(os.path.realpath(__file__), "utils", "logos_db.shelve") # for some reason, this doesn't
# work with line: with shelve.open("utils/logos_db.shelve") as db:
LOGOS_DB_PATH = "utils/logos_db.shelve"

NUMBER_OF_CHARACTERS_IN_ONE_PAGE = 2600

PUBLISHER_PDF_METADATA_TAGS = [
    '/CrossMarkDomains#5B1#5D',
    '/CrossMarkDomains#5B2#5D',
    '/CrossmarkDomainExclusive',
    '/CrossmarkMajorVersionDate',
    '/doi',
    '/ElsevierWebPDFSpecifications',
    '/Keywords',
]
# NISO versions (source: https://groups.niso.org/publications/rp/RP-8-2008.pdf)
SMUR = 'submitted manuscript under review'
AM = 'accepted manuscript'
P = 'proof'
VOR = 'version of record'

class BaseParser:
    """
    Parser with common methods shared by all inheriting classes
    """
    def __init__(self, file_path, dec_ms_title=None, dec_version=None, dec_authors=None, **kwargs):
        '''

        :param file_path: Path to file this class will evaluate
        :param dec_ms_title: Declared title of manuscript
        :param dec_version: Declared manuscript version of file
        :param dec_authors: Declared authors of manuscript (list)
        :param kwargs: Dictionary of citation details and any other known metadata fields; values may include:
            acceptance_date=None, doi=None, publication_date=None, title=None
        '''
        self.file_path = file_path
        self.file_name = os.path.basename(self.file_path)
        self.file_dirname = os.path.dirname(self.file_path)
        self.file_ext = os.path.splitext(self.file_path)[-1].lower()
        self.file = open(self.file_path)
        self.dec_ms_title = dec_ms_title
        self.dec_version = dec_version
        self.dec_authors = dec_authors
        self.metadata = kwargs

        self.extracted_text = None
        self.number_of_pages = None
        self.file_metadata = None
        self.possible_versions = [SMUR, AM, P, VOR]
        self.test_results = {} # dictionary to log the results of individual tests

    def extract_text(self, method=None):
        '''
        Extracts text from file using textract (https://textract.readthedocs.io/en/stable/python_package.html)
        :return:
        '''
        try:
            if method:
                self.extracted_text = textract.process(self.file_path, method=method)
            else:
                self.extracted_text = textract.process(self.file_path)
        except UnicodeDecodeError:
            logger.error("Textract failed with UnicodeDecodeError")
            return None

        if isinstance(self.extracted_text, str):
            result = chardet.detect(self.extracted_text)
            self.extracted_text = self.extracted_text.decode(result['encoding'])
        else:
            logger.error("extracted_text is a {} instance; only strings are currently "
                         "supported".format(type(self.extracted_text)))
        return self.extracted_text

    def find_match_in_extracted_text(self, query=None, escape_char=True, expected_span=(0, 2600),
                                     allowed_error_ratio=.1):
        """
        Fuzzy search extracted text.
        :param query: Search string; manuscript title by default
        :param escape_char: Escape query characters that have a special regex meaning
        :param expected_span: Tuple indicating start and end characters of sector we expect to find string. For example,
            if we are searching for an article title, we would expect it to appear in the first page of the document.
            An uninterrupted page of text contains about 1300 words, so the first page should span less than
            2600 characters. This is the arbitrarily set default, but we could obtain a median empirically
        :param allowed_error_ratio: By default, a number of errors equal to 20% the length of the search string is
            allowed
        :return:
        """
        if not query:
            query = self.dec_ms_title
        if escape_char:
            query = regex.escape(query)
        if not allowed_error_ratio:
            pattern = query
        else:
            pattern = "{}{{e<{}}}".format(query, int(allowed_error_ratio*len(query)))
        if not self.extracted_text:
            self.extract_text()
        # remove all line breaks from extracted text; otherwise match will often fail
        continuous_text = self.extracted_text.replace('\n', ' ').replace('  ', ' ')
        try:
            logger.debug("pattern: {}".format(pattern))
            m = regex.search(pattern, continuous_text, flags=regex.IGNORECASE)
            if m:
                logger.debug("Match object: {}".format(m))
                match_in_expected_position = False
                if (m.start() >= expected_span[0]) and (m.end() <= expected_span[1]):
                    match_in_expected_position = True
                return {'match': m.group(), 'match in expected position': match_in_expected_position}
        except TypeError:
            logger.error("Attempt to find match in extracted_text failed because it is not a string.")
        return None

    def find_doi_in_extracted_text(self):
        return self.find_match_in_extracted_text(query=DOI_PATTERN, escape_char=False, allowed_error_ratio=0)

    def find_cc_statement_in_extracted_text(self):
        for l in ALL_CC_LICENCES:
            for key, error_ratio in [('url', 0), ('long name', 0.1), ('short name', 0)]:
                m = self.find_match_in_extracted_text(query=l[key], escape_char=False,
                                                      allowed_error_ratio=error_ratio)
                if m:
                    logger.debug("Found Creative Commons statement in extracted text: {}".format(m.group()))
                    return m
        logger.debug("Could not find a Creative Commons statement in extracted text")
        return None

    def convert_to_pdf(self):
        '''
        Converts file to PDF using pandoc (https://pandoc.org/)
        :return:
        '''
        subprocess.run(['pandoc', self.file_path, '--latex-engine=xelatex', '-o',
                        self.file_path.replace(self.file_ext, '.pdf')], check=True)

    def detect_funding(self):
        pass

    def exclude_versions(self, e_list):
        """
        Excludes versions in e_list from self.possible_versions
        :param e_list: List of versions to exclude
        :return: filtered self.possible_versions
        """
        for v in e_list:
            if v in self.possible_versions:
                self.possible_versions.remove(v)
        return self.possible_versions

    def test_title_match_in_file_metadata(self, title_key, min_similarity=0.9):
        """
        Test if there is a match for declared title in file's metadata
        :param title_key: value of key for title field in self.metadata
        :param min_similarity: Minimum similarity for which a match will be accepted
        :return: True for match found; False for no match; None if test could not be performed
        """
        if self.dec_ms_title:
            if title_key in self.file_metadata.keys():
                if SequenceMatcher(None, self.file_metadata[title_key], self.dec_ms_title).ratio() >= min_similarity:
                    logger.debug("Found declared title in file metadata with a similarity of {}".format(min_similarity))
                    return True
                else:
                    logger.debug("Declared title could not be found in file metadata with a"
                                 " similarity of {}".format(min_similarity))
                    return False
            else:
                logger.error("File metadata does not contain title field, so cannot test match")
        else:
            logger.error("No declared title (self.dec_ms_title), so cannot test match")
        return None

    def test_title_match_in_extracted_text(self):
        """
        Test if there is a match for declared title in extracted text
        :return: True for match found; False for no match; None if test could not be performed
        """
        if self.dec_ms_title:
            if self.find_match_in_extracted_text():
                logger.debug("Found declared title (or similar) in extracted text")
                return True
            else:
                logger.debug("Could not find declared title (or similar) in extracted text")
                return False
        else:
            logger.error("No declared title (self.dec_ms_title), so cannot test match")
        return None

    def test_length_of_extracted_text(self, min_length=3*NUMBER_OF_CHARACTERS_IN_ONE_PAGE):
        """
        Test if extracted plain text has at list min_length characters
        :param min_length: minimum number of characters for test to succeed
        :return:
        """
        if self.extracted_text:
            if len(self.extracted_text) >= min_length:
                logger.debug("Extracted text is longer than {} characters".format(min_length))
                return True
            else:
                logger.debug("Extracted text is shorter than {} characters".format(min_length))
                return False
        logger.error("Extracted text unavailable (self.extracted_text), so could not perform test")
        return None


class DocxParser(BaseParser):
    """
    Parser for .docx files
    """
    def extract_file_metadata(self):
        '''
        Extracts the metadata of a .docx file
        :return:
        '''
        docx = Document(docx=self.file_path)
        self.file_metadata = {
            'author': docx.core_properties.author,
            'created': docx.core_properties.created,
            'last_modified_by': docx.core_properties.last_modified_by,
            'last_printed': docx.core_properties.last_printed,
            'modified': docx.core_properties.modified,
            'revision': docx.core_properties.revision,
            'title': docx.core_properties.title,
            'category': docx.core_properties.category,
            'comments': docx.core_properties.comments,
            'identifier': docx.core_properties.identifier,
            'keywords': docx.core_properties.keywords,
            'language': docx.core_properties.language,
            'subject': docx.core_properties.subject,
            'version': docx.core_properties.version,
            'keywords': docx.core_properties.keywords,
            'content_status': docx.core_properties.content_status,
        }

    def parse(self):
        '''
        Workflow for DOCX files
        :return: Tuple where: first element is string "success" or "fail" to indicate outcome; second element is
            string containing details
        '''

        self.extract_file_metadata()
        title_match_file_metadata = self.test_title_match_in_file_metadata('title')
        self.extract_text()
        more_than_three_pages = self.test_length_of_extracted_text()
        title_match_extracted_text = self.test_title_match_in_extracted_text()

        if more_than_three_pages and (title_match_file_metadata or title_match_extracted_text):
            if self.dec_version.lower() in ['submitted version', 'accepted version']:
                return "success", self.dec_version
            else:
                return "fail", "This is either a submitted or accepted version, " \
                       "but declared version is {}".format(self.dec_version)
        else:
            return "fail", "File {} failed automated checks. more_than_three_pages: {}, title_match_file_metadata:" \
                           " {}, title_match_extracted_text: {}".format(self.file_name, more_than_three_pages,
                                                           title_match_file_metadata, title_match_extracted_text)


class PdfParser(BaseParser):
    #TODO: If pdf metadata field '/Creator' == publisher name, PDF is proof/published version
    #TODO: Compare cermine extracted images to library of publisher logos:
    # http://www.imagemagick.org/Usage/compare/
    # https://pysource.com/2018/07/19/check-if-two-images-are-equal-with-opencv-and-python/
    # https://datascience.stackexchange.com/questions/28840/compare-image-similarity-in-python
    #TODO: Investigate identifying watermark http://blog.uorz.me/2018/06/19/removeing-watermark-with-PyPDF2.html
    """
    Parser for .pdf files
    """
    def __init__(self, file_path, dec_ms_title=None, dec_version=None, dec_authors=None, **kwargs):
        self.cerm_ran_and_parsed = False
        self.cerm_doi = None
        self.cerm_title = None
        self.cerm_journal_title = None
        super(PdfParser, self).__init__(file_path, dec_ms_title=dec_ms_title,
                                        dec_version=dec_version, dec_authors=dec_authors, **kwargs)

    def extract_file_metadata(self):
        '''
        Extracts the metadata of a PDF file. For more information on PDF metadata tags, see
        https://www.sno.phy.queensu.ca/~phil/exiftool/TagNames/PDF.html
        :return:
        '''
        with open(self.file_path, 'rb') as f:
            pdf = PdfFileReader(f, strict=False)
            info = pdf.getDocumentInfo()
            # pprint(pdf.getPage(0).extractText())
            logger.debug("output of pdf.getDocumentInfo(): {}".format(info))
            self.number_of_pages = pdf.getNumPages()
            self.file_metadata = info

    def extract_text(self):
        try:
            super(PdfParser, self).extract_text()
        except TypeError:
            logger.warning("Text extraction of PDF using textract default method failed; "
                           "trying again with pdfminer method")
            super(PdfParser, self).extract_text(method='pdfminer')
        if not isinstance(self.extracted_text, str):
            logger.warning("Text extraction of PDF using textract failed; "
                           "using cermine instead")
            self.cermine_file()
            cermtxt_path = self.file_path.replace(self.file_ext, ".cermtxt")
            with open(cermtxt_path) as f:
                self.extracted_text = f.read()

    def cermine_file(self):
        '''
        Runs CERMINE (https://github.com/CeON/CERMINE) on pdf file
        :return:
        '''
        try:
            subprocess.run(["java", "-cp", "cermine-impl-1.13-jar-with-dependencies.jar",
                        "pl.edu.icm.cermine.ContentExtractor", "-path", self.file_dirname, "-outputs",
                        # '"jats,text"'
                        '"jats,text,zones,trueviz,images"'
                        ],
                       check=True)
        except subprocess.CalledProcessError as e:
            logger.error("return code: {}; output: {}".format(e.returncode, e.output))

    def parse_cermxml(self):
        cermxml_path = self.file_path.replace(self.file_ext, ".cermxml")
        with open(cermxml_path) as f:
            tree = ET.parse(f)
        root = tree.getroot()
        # extract DOI
        for c_id in root.iter('article-id'):
            if c_id.get('pub-id-type') == 'doi':
                if self.cerm_doi is not None:
                    logger.warning("Previously detected DOI {} will be overwritten by value {}".format(self.cerm_doi,
                                                                                                c_id.text))
                self.cerm_doi = c_id.text

        # extract title
        for c_title in root.find('front').iter('article-title'):
            if self.cerm_title is not None:
                logger.warning("Previously detected title '{}' will be overwritten by value '{}'".format(self.cerm_title,
                                                                                                   c_title.text))
            self.cerm_title = c_title.text

        # extract journal title
        for c_journal in root.iter('journal-title'):
            if self.cerm_journal_title is not None:
                logger.warning("Previously detected journal title '{}' will be overwritten by"
                               " value '{}'".format(self.cerm_journal_title, c_journal.text))
            self.cerm_journal_title = c_journal.text

        self.cerm_ran_and_parsed = True
        return self.cerm_doi, self.cerm_title, self.cerm_journal_title

    def detect_publisher_logos(self, max_hash_difference=5, stop_at_first_match=False):
        """
        Detects publisher logos in file
        :param max_hash_difference: max_hash_difference to be passed to PublisherLogo.test_hash_match
        :param stop_at_first_match: if True, stop trying additional matches if one is found
        :return: list of detected logos (as PublisherLogo instances)
        """
        detected_logos = []
        images_folder = self.file_path.replace(self.file_ext, ".images")
        if not os.path.exists(images_folder):
            self.cermine_file()
        for i in os.listdir(images_folder):
            i_path = os.path.join(images_folder, i)
            pl = PublisherLogo(i, path=i_path)
            with shelve.open(LOGOS_DB_PATH) as db:
                for key in db:
                    logo = db[key]
                    logo.test_hash_match(pl, max_hash_difference=max_hash_difference, method="perception")
                    if logo.test_hash_match(pl, max_hash_difference=max_hash_difference):
                        logger.debug("Extracted image {} matched logo {}".format(i_path, logo.name))
                        detected_logos.append(logo)
                        if stop_at_first_match:
                            break
            if detected_logos and stop_at_first_match:
                break
        return detected_logos

    def test_file_has_image_on_first_page(self):
        images_folder = self.file_path.replace(self.file_ext, ".images")
        if not os.path.exists(images_folder):
            self.cermine_file()
        for i in os.listdir(images_folder):
            if "img_1_" in i:
                return True
        return False

    def test_file_metadata_contains_publisher_tags(self):
        for tag in PUBLISHER_PDF_METADATA_TAGS:
            if tag in self.file_metadata.keys():
                logger.debug("Found publisher tag {} in file metadata".format(tag))
                return True
        logger.debug("Could not find any publisher tags in file metadata")
        return False

    def test_title_match_cermxml(self, min_similarity=0.9):
        """
        Test if there is a match for declared title in title element of xml file produced by cermine
        :return: True, False or None
        """
        if not self.cerm_ran_and_parsed:
            self.parse_cermxml()
        if self.dec_ms_title and self.cerm_title:
            if SequenceMatcher(None, self.cerm_title, self.dec_ms_title).ratio() >= min_similarity:
                logger.debug("Declared title matches title identified by CERMINE")
                return True
            else:
                logger.debug("Declared title does not match title identified by CERMINE")
                return False
        logger.debug("Could not test title match with cermxml; "
                     "self.dec_ms_title: {}; self.cerm_title: {}".format(self.dec_ms_title, self.cerm_title))
        return None

    def test_doi_match(self):
        result = self.find_doi_in_extracted_text()
        if result:
            logger.debug("Found DOI in extracted text")
            return True
        logger.debug("Could not find DOI in extracted text")
        return False

    def parse(self):
        '''
        Workflow for PDF files
        :return: Tuple where: first element is string "success" or "fail" to indicate outcome; second element is
            string containing details
        '''

        approve_deposit = False

        # region file metadata tests
        self.extract_file_metadata()
        title_match_file_metadata = self.test_title_match_in_file_metadata('/Title')
        self.test_results['title_match_file_metadata'] = title_match_file_metadata
        file_metadata_contains_publisher_tags = self.test_file_metadata_contains_publisher_tags()
        self.test_results['file_metadata_contains_publisher_tags'] = file_metadata_contains_publisher_tags
        # endregion

        # region extracted text tests
        self.extract_text()
        more_than_three_pages = self.test_length_of_extracted_text()
        self.test_results['more_than_three_pages'] = more_than_three_pages
        title_match_extracted_text = self.test_title_match_in_extracted_text()
        self.test_results['title_match_extracted_text'] = title_match_extracted_text
        doi_match_extracted_text = self.test_doi_match()
        self.test_results['doi_match_extracted_text'] = doi_match_extracted_text
        cc_match_extracted_text = self.find_cc_statement_in_extracted_text()
        self.test_results['cc_match_extracted_text'] = cc_match_extracted_text
        # endregion

        # region cermine tests
        self.cermine_file()
        self.parse_cermxml()
        if self.cerm_doi:
            logger.debug("Cermine identified DOI {} in this file".format(self.cerm_doi))
            doi_found_in_cermxml = True
            self.test_results['doi_found_in_cermxml'] = doi_found_in_cermxml
        title_match_cermxml = self.test_title_match_cermxml()
        self.test_results['title_match_cermxml'] = title_match_cermxml
        # endregion

        # region logo tests
        image_on_first_page = self.test_file_has_image_on_first_page()
        self.test_results['image_on_first_page'] = image_on_first_page
        detected_logos = self.detect_publisher_logos()
        self.test_results['detected_logos'] = detected_logos
        # endregion

        if more_than_three_pages and (title_match_file_metadata or title_match_extracted_text or title_match_cermxml):
            # sanity check (this is the correct file; no mistake on upload)
            if file_metadata_contains_publisher_tags or cc_match_extracted_text:
                # file is publisher-generated
                # TODO: Add more tests here
                self.exclude_versions([SMUR, AM])
                if self.dec_version.lower() in ['submitted version', 'accepted version', SMUR, AM]:
                    reason = 'PDF metadata contains publisher tags, but declared version is author-generated'
                if cc_match_extracted_text:
                    reason = 'Create Commons licence detected in extracted text'
                    approve_deposit = True # could be proof, so additional checking is desirable
                else:
                    reason = 'Publisher-generated version; no evidence of CC licence'
            else:
                if self.dec_version.lower() in ['submitted version', 'accepted version']:
                    approve_deposit = True
                    reason = 'Could not find any evidence that this PDF is publisher-generated'
                else:
                    reason = "This is either a submitted or accepted version, " \
                                   "but declared version is {}".format(self.dec_version)
        else:
            reason = "File {} failed automated checks. more_than_three_pages: {}, title_match_file_metadata:" \
                           " {}, title_match_extracted_text: {}".format(self.file_name,
                                                                        more_than_three_pages,
                                                                        title_match_file_metadata,
                                                                        title_match_extracted_text)
        return {'approved': approve_deposit, 'reason': reason, **self.test_results}


class VersionDetector:
    def __init__(self, file_path, dec_ms_title=None, dec_version=None, dec_authors=None, **kwargs):
        '''

        :param file_path: Path to file this class will evaluate
        :param dec_ms_title: Declared title of manuscript
        :param dec_version: Declared manuscript version of file
        :param dec_authors: Declared authors of manuscript (list)
        :param **kwargs: Dictionary of citation details and any other known metadata fields; values may include:
            acceptance_date=None, doi=None, publication_date=None, title=None
        '''
        self.file_path = file_path
        self.file_ext = os.path.splitext(self.file_path)[-1].lower()
        self.dec_ms_title = dec_ms_title
        self.dec_version = dec_version
        self.dec_authors = dec_authors
        self.metadata = kwargs
        logger.info("----- Working on file {}".format(file_path))

    def check_extension(self):
        logger.debug("file_ext: {}; file_path: {}".format(self.file_ext, self.file_path))
        if self.file_ext == ".pdf":
            return "pdf"
        elif self.file_ext == ".docx":
            return "docx"
        elif self.file_ext in [".doc", ".html", ".htm", ".odt", ".ppt", ".pptx", ".rtf", ".tex", ".txt"]:
            return "editable_document"
        else:
            logger.error("Unrecognised file extension {} detected for {}".format(self.file_ext, self.file_path))
            return self.file_ext

    def detect(self):
        """
        Detect version of file using appropriate parser
        :return:
        """
        ext = self.check_extension()
        if ext == "docx":
            parser = DocxParser(self.file_path, self.dec_ms_title, self.dec_version, self.dec_authors, **self.metadata)
        elif ext == "pdf":
            parser = PdfParser(self.file_path, self.dec_ms_title, self.dec_version, self.dec_authors, **self.metadata)
        else:
            error_msg = "{} is not a supported file extension".format(ext)
            logger.error(error_msg)
            return "fail", error_msg
            # sys.exit(error_msg)

        result = parser.parse()
        return result




if __name__ == "__main__":
    logfilename = 'artemis.log'
    logging.config.fileConfig('logging.conf', defaults={'logfilename': logfilename})
    logger = logging.getLogger('artemis')

    # TODO: This project has some useful functions: https://github.com/Phyks/libbmc/blob/master/libbmc/doi.py

