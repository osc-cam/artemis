import logging
import logging.config
import math
import os
import regex
import requests
import statistics
import xml.etree.ElementTree as ET
from collections import Counter

logging.config.fileConfig('logging.conf', defaults={'logfilename':'TrueViz.log'})
logger = logging.getLogger(__name__)

# https://www.slideshare.net/dtkaczyk/tkaczyk-grotoap2slides


class Document:
    def __init__(self, cermstr_path):
        self.path = cermstr_path
        with open(cermstr_path) as f:
            tree = ET.parse(f)
        self.root = tree.getroot()
        self.pages = {}
        children = self.root.findall("Page")
        for c in children:
            page = Page(self, c)
            self.pages[page.id] = page
        self.number_of_pages = len(self.pages)
        self.middle_page = math.floor(self.number_of_pages / 2)
        self.line_spacing = None

    def detect_line_spacing(self, sample_size=5):
        """
        Detect line spacing by calculating the median of spaces between lines in sample_size pages.
        :param sample_size: Number of pages to sample. Pages are sampled from the middle of the document
        :return:
        """
        spacing_of_body_content_zones = []
        for k, page in self.pages.items():
            if (int(k) >= (self.middle_page - 2)) and (int(k) <= (self.middle_page + 2)):
                logger.debug("Working on page {}".format(int(k) + 1))
                page.get_children()
                if page.children:
                    for zone in page.children:
                        if zone.category == "BODY_CONTENT":
                            if zone.detect_line_spacing():
                                spacing_of_body_content_zones.append(zone.line_spacing)
        if spacing_of_body_content_zones:
            self.line_spacing = statistics.median(spacing_of_body_content_zones)
        else:
            logger.warning("Could not detect spacing of body content zones")
        return self.line_spacing

    def page_tikz_picture(self, output_filename=None, page_number=None):
        """
        Outputs a drawing of page page_number in tikz format
        :param page_number:
        :return:
        """
        if not output_filename:
            output_filename = self.path.replace(".cermstr", "_tikz.tex")
        if not page_number:
            page_number = self.middle_page
        with open(output_filename, "w") as f:
            s = "\\documentclass[a4paper,8pt]{extarticle}\n\\usepackage{geometry, tikz}\n\\geometry{margin=0pt}\n" \
                "\\renewcommand{\\familydefault}{\\ttdefault}\n\\begin{document}\n\\pagestyle{empty}\n"
            s += self.pages[str(page_number)].tikz_picture()
            s += "\\end{document}"
            f.write(s)


class TrueVizElement:
    def __init__(self, name, parent, xml_element, child_class=None):
        self.name = name
        self.parent = parent
        self.id_string = "{}ID".format(name)
        self.element = xml_element
        self.id = self.element.find(self.id_string).get('Value')
        self.child_class = child_class
        self.children = []

    def get_children(self):
        children = self.element.findall(self.child_class.name())
        for c in children:
            child = self.child_class(self, c)
            self.children.append(child)
        return self.children


class Page(TrueVizElement):
    def __init__(self, parent, xml_element):
        super(Page, self).__init__("Page", parent, xml_element, Zone)

    def tikz_picture(self):
        def children_check(element):
            if not element.children:
                element.get_children()
        s = "\\begin{tikzpicture}[x=1pt,y=1pt]\n"
        children_check(self)
        for zone in self.children:
            children_check(zone)
            for line in zone.children:
                children_check(line)
                for word in line.children:
                    children_check(word)
                    for character in word.children:
                        s += character.tikz_node()
                    s += word.tikz_rectangle(colour="green")
                s += line.tikz_rectangle(colour="blue")
            s += zone.tikz_rectangle(colour="red")
        s += r"\end{tikzpicture}"
        return s


class GeometricElement(TrueVizElement):
    def __init__(self, name, parent, xml_element, child_class=None):
        super(GeometricElement, self).__init__(name, parent, xml_element, child_class=child_class)
        self.corners = self.element.find("{}Corners".format(name))

    def tikz_rectangle(self, colour="black"):
        return "\\draw[draw={}] ({},{}) rectangle ({},{});\n".format(colour,
                                                                    self.corners[0].get('x'),
                                                                    self.corners[0].get('y'),
                                                                    self.corners[2].get('x'),
                                                                    self.corners[2].get('y')
                                                                    )


class Zone(GeometricElement):
    def __init__(self, parent, xml_element):
        super(Zone, self).__init__("Zone", parent, xml_element, Line)
        self.category = self.element.find('Classification').find('Category').attrib['Value']
        self.line_spacing = None

    @staticmethod
    def name():
        return "Zone"

    def detect_line_spacing(self):
        self.get_children()
        baseline_of_previous_line = None
        for line in self.children:
            top_of_line = float(line.corners[0].get('y'))
            baseline = float(line.corners[2].get('y'))
            line_height = baseline - top_of_line
            logger.debug('Line height: {}'.format(line_height))
            if not baseline_of_previous_line:
                baseline_of_previous_line = baseline
                continue  # this is the first line in this body content zone
            line_spacing = baseline - baseline_of_previous_line
            if line_height:  # avoid division by zero
                line_spacing_ratio = line_spacing / line_height
                logger.debug("Line spacing: {}; Line spacing ratio: {}".format(line_spacing, line_spacing_ratio))
                self.line_spacing = line_spacing_ratio
            baseline_of_previous_line = baseline
        return self.line_spacing


class Line(GeometricElement):
    def __init__(self, parent, xml_element):
        super(Line, self).__init__("Line", parent, xml_element, Word)

    @staticmethod
    def name():
        return "Line"


class Word(GeometricElement):
    def __init__(self, parent, xml_element):
        super(Word, self).__init__("Word", parent, xml_element, Character)

    @staticmethod
    def name():
        return "Word"


class Character(GeometricElement):
    def __init__(self, parent, xml_element):
        super(Character, self).__init__("Character", parent, xml_element)
        self.value = self.element.find('GT_Text').attrib['Value']

    @staticmethod
    def name():
        return "Character"

    def tikz_node(self):
        def tex_escape(text):
            """
                Adapted from https://stackoverflow.com/a/25875504
                :param text: a plain text message
                :return: the message escaped to appear correctly in LaTeX
            """
            conv = {
                '&': r'\&',
                '%': r'\%',
                '$': r'\$',
                '#': r'\#',
                '_': r'\_',
                '{': r'\{',
                '}': r'\}',
                '~': r'\textasciitilde{}',
                '^': r'\^{}',
                '\\': r'\textbackslash{}',
                '<': r'\textless{}',
                '>': r'\textgreater{}',
            }
            t = regex.compile(
                '|'.join(regex.escape(key) for key in sorted(conv.keys(), key=lambda item: - len(item))))
            return t.sub(lambda match: conv[match.group()], text)

        s = super(Character, self).tikz_rectangle(colour="yellow")
        x_center = (float(self.corners[0].get('x')) + float(self.corners[2].get('x'))) / 2
        y_center = (float(self.corners[0].get('y')) + float(self.corners[2].get('y'))) / 2
        s += "\\draw ({},{}) node {{{}}};\n".format(x_center, y_center, tex_escape(self.value))
        return s
#
#     left_limit_of_body_content_zones = []
#     first_words_that_are_integers = []
#     wide_body_content_zone_counter = 0
#     narrow_body_content_zone_counter = 0
#     min_words_per_zone = 50
#     for page in root.iter('Page'):
#         page_id = page.find('PageID').get('Value')
#         if int(page_id) in [(middle_page - 1), middle_page, (middle_page + 1)]:
#             logger.debug("Working on page {}".format(int(page_id) + 1))
#             zones = page.findall('Zone')
#             if zones:
#                 for zone in page.findall('Zone'):
#                     zone_id = zone.find('ZoneID').get('Value')
#                     category = zone.find('Classification').find('Category').attrib['Value']
#                     logger.debug("Zone {} is of category {}".format(zone_id, category))
#                     if category == "BODY_CONTENT":
#                         words = zone.findall('Word')
#
#                         if len(words) < min_words_per_zone:
#                             logger.debug(
#                                 "Skipped zone {}; it has less than {} words".format(zone_id, min_words_per_zone))
#                             continue
#
#                         # logger.debug("Analysing body_content zone on page {}".format(page_id))
#                         # region columns
#                         corners = zone.find('ZoneCorners').findall('Vertex')
#                         left_limit = float(corners[0].get('x'))
#                         right_limit = float(corners[1].get('x'))
#                         zone_width = right_limit - left_limit
#                         if zone_width > 312:  # c. 110 mm in pt
#                             wide_body_content_zone_counter += 1
#                         else:
#                             narrow_body_content_zone_counter += 1
#                         left_limit_of_body_content_zones.append(left_limit)
#                         # endregion
#
#                         # region line spacing and line numbering
#                         baseline_of_previous_line = None
#                         for line in zone.findall('Line'):
#                             line_id = line.find('LineID').attrib['Value']
#                             # logger.debug("LineID: {}".format(line_id))
#                             # region line numbering
#                             first_word = line.find('Word')
#                             first_word_value = ""
#                             first_word_characters = first_word.findall('Character')
#                             for c in first_word_characters:
#                                 first_word_value += c.find('GT_Text').attrib['Value']
#                             # logger.debug("First word: {}".format(first_word_value))
#                             m = NUMBER_PATTERN.match(first_word_value)
#                             if m:
#                                 w_corners = first_word.find('WordCorners').findall('Vertex')
#                                 w_left_margin = float(w_corners[3].get('x'))
#                                 w_right_margin = float(w_corners[2].get('x'))
#                                 first_words_that_are_integers.append({
#                                     "number": m.group(),
#                                     "line_id": line_id,
#                                     "page_id": page_id,
#                                     "left_margin": w_left_margin,
#                                     "right_margin": w_right_margin
#                                 }
#                                 )
#                             # endregion
#
#                             l_corners = line.find('LineCorners').findall('Vertex')
#                             top_of_line = float(l_corners[0].get('y'))
#                             baseline = float(l_corners[2].get('y'))
#                             line_height = baseline - top_of_line
#                             # logger.debug('Line height: {}'.format(line_height))
#                             if not baseline_of_previous_line:
#                                 baseline_of_previous_line = baseline
#                                 continue  # this is the first line in this body content zone
#                             line_spacing = baseline - baseline_of_previous_line
#                             if line_height:  # avoid division by zero
#                                 line_spacing_ratio = line_spacing / line_height
#                                 # logger.debug("Line spacing: {}; Line spacing ratio: {}".format(line_spacing, line_spacing_ratio))
#                                 spacing_of_body_content_zones.append(line_spacing_ratio)
#                             baseline_of_previous_line = baseline
#                             # for l_corner in l_corners:
#                             #     if l_corners.index(l_corner) in [0, 2]:
#                             #         logger.debug("LineCorner:", l_corner.get('x'), l_corner.get('y'))
#                         # endregion
#             else:
#                 logger.warning("Page {} does not have any zones".format(page_id))
#
#     logger.debug("lenght of first_words_that_are_integers: {}; first_words_that_are_integers: {}".format(
#         len(first_words_that_are_integers), first_words_that_are_integers))
#     if not first_words_that_are_integers:
#         numbered_lines = False
#     elif len(first_words_that_are_integers) < 5:
#         # we would have to be very unlucky to fail to find 5 numbered lines in 3 pages in a PDF where lines
#         # are truly numbered (though pages with large images or numbered only every 5 lines can truly have
#         # only few numbered lines
#         numbered_lines = False
#     else:
#         previous_number = None
#         exceptions_count = 0
#         for n in first_words_that_are_integers:
#             if not previous_number:
#                 previous_number = n
#                 continue
#             else:
#                 if n['page_id'] == previous_number['page_id']:
#                     if not int(n['number']) > int(previous_number['number']):  # line numbers on the same
#                         # page should be incremental
#                         exceptions_count += 1
#
#                 left_margin_offset = abs(n['left_margin'] - previous_number['left_margin'])
#                 right_margin_offset = abs(n['right_margin'] - previous_number['right_margin'])
#                 logger.debug("left_margin_offset: {}; right_margin_offset: {}".format(left_margin_offset,
#                                                                                       right_margin_offset))
#                 max_offset = 10
#                 if (left_margin_offset > max_offset) or (right_margin_offset > max_offset):
#                     # line numbers should be aligned
#                     exceptions_count += 1
#                 previous_number = n
#         logger.debug("exception_count: {}".format(exceptions_count))
#         if exceptions_count > 3:
#             numbered_lines = False
#         else:
#             numbered_lines = True
#
#     logger.debug("left_limit_of_body_content_zones: {}".format(left_limit_of_body_content_zones))
#     if left_limit_of_body_content_zones:
#         putative_columns = Counter(left_limit_of_body_content_zones).most_common(2)
#         # logger.debug("putative_columns: {}".format(putative_columns))
#         # if (abs(putative_columns[1][0] - putative_columns[0][0]) > 100  # putative columns separated by at least 100pt
#         #     ) and (
#         #         (putative_columns[1][1] / putative_columns[0][1]) > 0.5):  # number of columns on one side matched by at least 50% of columns on the opposite side
#         #     two_columns = True
#         # else:
#         #     two_columns = False
#     else:
#         logger.warning("Could not detect left limit of body content zones")
#
#     logger.debug("wide_body_content_zone_counter: {}; narrow_body_content_zone_counter: {}".format(
#         wide_body_content_zone_counter, narrow_body_content_zone_counter))
#     if wide_body_content_zone_counter > narrow_body_content_zone_counter:
#         two_columns = False
#     else:
#         two_columns = True
#
#     if spacing_of_body_content_zones:
#         spacing_median = statistics.median(spacing_of_body_content_zones)
#     else:
#         logger.warning("Could not detect spacing of body content zones")
#
#     return spacing_median, two_columns, numbered_lines
#
#
# def parse_cerm_trueviz(self):
#     """
#     Parses Trueviz (.cermstr) file generated by CERMINE to detect line spacing, column layout and numbers along
#     the left margin
#     :return:
#     """
#     two_columns = None
#     spacing_median = None
#     numbered_lines = None
#     cermstr_path = self.file_path.replace(self.file_ext, ".cermstr")
#     if not self.number_of_pages:
#         self.extract_file_metadata()
#     middle_page = int(math.floor((int(self.number_of_pages) / 2)))
#     with open(cermstr_path) as f:
#         tree = ET.parse(f)
#     root = tree.getroot()
#     spacing_of_body_content_zones = []
#     left_limit_of_body_content_zones = []
#     first_words_that_are_integers = []
#     wide_body_content_zone_counter = 0
#     narrow_body_content_zone_counter = 0
#     min_words_per_zone = 50
#     for page in root.iter('Page'):
#         page_id = page.find('PageID').get('Value')
#         if int(page_id) in [(middle_page - 1), middle_page, (middle_page + 1)]:
#             logger.debug("Working on page {}".format(int(page_id) + 1))
#             zones = page.findall('Zone')
#             if zones:
#                 for zone in page.findall('Zone'):
#                     zone_id = zone.find('ZoneID').get('Value')
#                     category = zone.find('Classification').find('Category').attrib['Value']
#                     logger.debug("Zone {} is of category {}".format(zone_id, category))
#                     if category == "BODY_CONTENT":
#                         words = zone.findall('Word')
#
#                         if len(words) < min_words_per_zone:
#                             logger.debug(
#                                 "Skipped zone {}; it has less than {} words".format(zone_id, min_words_per_zone))
#                             continue
#
#                         # logger.debug("Analysing body_content zone on page {}".format(page_id))
#                         # region columns
#                         corners = zone.find('ZoneCorners').findall('Vertex')
#                         left_limit = float(corners[0].get('x'))
#                         right_limit = float(corners[1].get('x'))
#                         zone_width = right_limit - left_limit
#                         if zone_width > 312:  # c. 110 mm in pt
#                             wide_body_content_zone_counter += 1
#                         else:
#                             narrow_body_content_zone_counter += 1
#                         left_limit_of_body_content_zones.append(left_limit)
#                         # endregion
#
#                         # region line spacing and line numbering
#                         baseline_of_previous_line = None
#                         for line in zone.findall('Line'):
#                             line_id = line.find('LineID').attrib['Value']
#                             # logger.debug("LineID: {}".format(line_id))
#                             # region line numbering
#                             first_word = line.find('Word')
#                             first_word_value = ""
#                             first_word_characters = first_word.findall('Character')
#                             for c in first_word_characters:
#                                 first_word_value += c.find('GT_Text').attrib['Value']
#                             # logger.debug("First word: {}".format(first_word_value))
#                             m = NUMBER_PATTERN.match(first_word_value)
#                             if m:
#                                 w_corners = first_word.find('WordCorners').findall('Vertex')
#                                 w_left_margin = float(w_corners[3].get('x'))
#                                 w_right_margin = float(w_corners[2].get('x'))
#                                 first_words_that_are_integers.append({
#                                     "number": m.group(),
#                                     "line_id": line_id,
#                                     "page_id": page_id,
#                                     "left_margin": w_left_margin,
#                                     "right_margin": w_right_margin
#                                 }
#                                 )
#                             # endregion
#
#                             l_corners = line.find('LineCorners').findall('Vertex')
#                             top_of_line = float(l_corners[0].get('y'))
#                             baseline = float(l_corners[2].get('y'))
#                             line_height = baseline - top_of_line
#                             # logger.debug('Line height: {}'.format(line_height))
#                             if not baseline_of_previous_line:
#                                 baseline_of_previous_line = baseline
#                                 continue  # this is the first line in this body content zone
#                             line_spacing = baseline - baseline_of_previous_line
#                             if line_height:  # avoid division by zero
#                                 line_spacing_ratio = line_spacing / line_height
#                                 # logger.debug("Line spacing: {}; Line spacing ratio: {}".format(line_spacing, line_spacing_ratio))
#                                 spacing_of_body_content_zones.append(line_spacing_ratio)
#                             baseline_of_previous_line = baseline
#                             # for l_corner in l_corners:
#                             #     if l_corners.index(l_corner) in [0, 2]:
#                             #         logger.debug("LineCorner:", l_corner.get('x'), l_corner.get('y'))
#                         # endregion
#             else:
#                 logger.warning("Page {} does not have any zones".format(page_id))
#
#     logger.debug("lenght of first_words_that_are_integers: {}; first_words_that_are_integers: {}".format(
#         len(first_words_that_are_integers), first_words_that_are_integers))
#     if not first_words_that_are_integers:
#         numbered_lines = False
#     elif len(first_words_that_are_integers) < 5:
#         # we would have to be very unlucky to fail to find 5 numbered lines in 3 pages in a PDF where lines
#         # are truly numbered (though pages with large images or numbered only every 5 lines can truly have
#         # only few numbered lines
#         numbered_lines = False
#     else:
#         previous_number = None
#         exceptions_count = 0
#         for n in first_words_that_are_integers:
#             if not previous_number:
#                 previous_number = n
#                 continue
#             else:
#                 if n['page_id'] == previous_number['page_id']:
#                     if not int(n['number']) > int(previous_number['number']):  # line numbers on the same
#                         # page should be incremental
#                         exceptions_count += 1
#
#                 left_margin_offset = abs(n['left_margin'] - previous_number['left_margin'])
#                 right_margin_offset = abs(n['right_margin'] - previous_number['right_margin'])
#                 logger.debug("left_margin_offset: {}; right_margin_offset: {}".format(left_margin_offset,
#                                                                                       right_margin_offset))
#                 max_offset = 10
#                 if (left_margin_offset > max_offset) or (right_margin_offset > max_offset):
#                     # line numbers should be aligned
#                     exceptions_count += 1
#                 previous_number = n
#         logger.debug("exception_count: {}".format(exceptions_count))
#         if exceptions_count > 3:
#             numbered_lines = False
#         else:
#             numbered_lines = True
#
#     logger.debug("left_limit_of_body_content_zones: {}".format(left_limit_of_body_content_zones))
#     if left_limit_of_body_content_zones:
#         putative_columns = Counter(left_limit_of_body_content_zones).most_common(2)
#         # logger.debug("putative_columns: {}".format(putative_columns))
#         # if (abs(putative_columns[1][0] - putative_columns[0][0]) > 100  # putative columns separated by at least 100pt
#         #     ) and (
#         #         (putative_columns[1][1] / putative_columns[0][1]) > 0.5):  # number of columns on one side matched by at least 50% of columns on the opposite side
#         #     two_columns = True
#         # else:
#         #     two_columns = False
#     else:
#         logger.warning("Could not detect left limit of body content zones")
#
#     logger.debug("wide_body_content_zone_counter: {}; narrow_body_content_zone_counter: {}".format(
#         wide_body_content_zone_counter, narrow_body_content_zone_counter))
#     if wide_body_content_zone_counter > narrow_body_content_zone_counter:
#         two_columns = False
#     else:
#         two_columns = True
#
#     if spacing_of_body_content_zones:
#         spacing_median = statistics.median(spacing_of_body_content_zones)
#     else:
#         logger.warning("Could not detect spacing of body content zones")
#
#     return spacing_median, two_columns, numbered_lines
