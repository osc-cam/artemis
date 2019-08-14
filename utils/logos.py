import logging
import logging.config
import os
import subprocess
import sys
from PIL import Image
import imagehash
import pytesseract
import shelve

from difflib import SequenceMatcher

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

PARENT_FOLDER = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
SHELVE_DB_PATH = os.path.join(os.path.dirname(os.path.realpath(__file__)), "logos_db.shelve")
LOGOS_LIBRARY = os.path.join(PARENT_FOLDER, "publisher_logos")

class PublisherLogo:
    def __init__(self, name, width=None, height=None, text=None, publisher=None,
                 average_hash=None, perception_hash=None, path=None):
        self.name = name
        self.width = width
        self.height = height
        self.text = text
        self.publisher = publisher
        self.average_hash = average_hash
        self.perception_hash = perception_hash
        self.path = path

    def store_in_db(self):
        if not self.width:
            self.calculate_image_size()
        if not self.text:
            self.extract_text()
        if not self.average_hash:
            self.calculate_average_hash()
        if not self.perception_hash:
            self.calculate_perception_hash()
        with shelve.open(SHELVE_DB_PATH) as db:
            db[self.name] = self

    def calculate_image_size(self):
        with Image.open(self.path) as im:
            self.width, self.height = im.size

    def extract_text(self):
        self.text = pytesseract.image_to_string(self.path)

    def calculate_average_hash(self):
        if not self.path:
            sys.exit("ERROR: {} does not contain the path to an example of this logo.".format(self.path))
        self.average_hash = imagehash.average_hash(Image.open(self.path))
        return self.average_hash

    def calculate_perception_hash(self):
        if not self.path:
            sys.exit("ERROR: {} does not contain the path to an example of this logo.".format(self.path))
        self.perception_hash = imagehash.phash(Image.open(self.path))
        return self.perception_hash

    def test_hash_match(self, pl_instance, method="average", max_hash_difference=5):
        """
        Tests if the hash of another image (suspected logo) matches this one.
        :param pl_instance: another instance of PublisherLogo class, representing the image we want to compare to
        :param method: the hashing method we want to use; support values: average, perception
        :param max_hash_difference: the maximum difference in hash values we are prepared to consider as a match;
            no idea what a reasonable value should be, so trying an arbitrary value for now.
        :return: True if match detected; False if not
        """
        if method == "average":
            if not self.average_hash:
                self.calculate_average_hash()
            if not pl_instance.average_hash:
                pl_instance.calculate_average_hash()
            hash_difference = self.average_hash - pl_instance.average_hash
            print(
                "Average hash difference between {} and {} is {}".format(pl_instance.path, self.name, hash_difference))
            if hash_difference <= max_hash_difference:
                return True
        elif method == "perception":
            if not self.perception_hash:
                self.calculate_perception_hash()
            if not pl_instance.perception_hash:
                pl_instance.calculate_perception_hash()
            hash_difference = self.perception_hash - pl_instance.perception_hash
            print("Perception hash difference between {} and {} "
                         "is {}".format(pl_instance.path, self.name, hash_difference))
            if hash_difference <= max_hash_difference:
                return True
        else:
            logger.critical("{} is not a supported method".format(method))
        return False

    def test_text_match(self, pl_instance, min_similarity=0.9):
        """
        Tests if text extracted from another image (suspected logo) matches this one
        :param pl_instance: another instance of PublisherLogo class, representing the image we want to compare to
        :param min_similarity: the minimum similarity between extract text strings we are prepared to consider as a
            match
        :return:
        """
        if not self.text:
            self.extract_text()
        if not pl_instance.text:
            pl_instance.extract_text()
        if SequenceMatcher(None, self.text, pl_instance.text).ratio() >= min_similarity:
            return True
        return False


def update_logos_db():
    for logo_name in os.listdir(LOGOS_LIBRARY):
        logo_path = os.path.join(LOGOS_LIBRARY, logo_name)
        pl = PublisherLogo(logo_name, path=logo_path)
        logger.info("Updating logo database")
        pl.store_in_db()

if __name__ == "__main__":
    logfilename = 'logos.log'
    logging.config.fileConfig(os.path.join(PARENT_FOLDER, 'logging.conf'), defaults={'logfilename': logfilename})
    logger = logging.getLogger('logos')
    update_logos_db()
