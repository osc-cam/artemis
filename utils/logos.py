import os
import subprocess
import sys
from PIL import Image
import imagehash

class PublisherLogo:
    def __init__(self, width=None, height=None, text=None, publisher=None,
                 average_hash=None, perception_hash=None, path=None):
        self.width = width
        self.height = height
        self.text = text
        self.publisher = publisher
        self.average_hash = average_hash
        self.perception_hash = perception_hash
        self.path = path

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

    def test_hash_match(self, pl_instance, method="average", max_hash_difference=50):
        """
        Tests if the hash of another image (suspected logo) matches this one.
        :param pl_instance: another instance of PublisherLogo class, representing the image we want to compare to
        :return: True if match detected; False if not
        """
        if method == "average":
            if not self.average_hash:
                self.calculate_average_hash()
            if not pl_instance.average_hash:
                pl_instance.calculate_average_hash()
            if (self.average_hash - pl_instance.average_hash) < max_hash_difference:
                return True
        elif method == "perception":
            if not self.perception_hash:
                self.calculate_perception_hash()
            if not pl_instance.perception_hash:
                pl_instance.calculate_perception_hash()
            if (self.perception_hash - pl_instance.perception_hash) < max_hash_difference:
                return True
        else:
            logger.critical("{} is not a supported method".format(method))
        return False


SCHOLAR_ONE = PublisherLogo(width=1051, height=340, text="SCHOLARONE™\nManuscripts",
                            average_hash="ffd8c0c0ffe0e0ff",
                            perception_hash="ea1c85a3946a7a9d")

ALL_LOGOS = [SCHOLAR_ONE]
