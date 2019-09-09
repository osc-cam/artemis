from utils.constants import SMUR, AM, P, VOR

class VersionPattern:
    """
    Regex patterns that are either indicative of or never found on a certain manuscript version
    """
    def __init__(self, pattern, indicative_of=None, not_found_on=None, error_ratio=0.1):
        """
        :param pattern: The regex pattern
        :param indicative_of: list of manuscript versions we could expect to find pattern on
        :param never_found_on: list of manuscript versions we would not normally expect to find pattern on
        :param error_ratio: the tolerance for fuzzy matching of pattern
        """
        self.pattern = pattern,
        self.indicative_of = indicative_of
        self.not_found_on = not_found_on
        self.error_ratio = error_ratio
        if self.indicative_of and not self.not_found_on:
            # https://stackoverflow.com/a/4211228/11999227
            self.not_found_on = [x for x in [SMUR, AM, P, VOR] if x not in self.indicative_of]
        elif self.not_found_on and not self.indicative_of:
            self.indicative_of = [x for x in [SMUR, AM, P, VOR] if x not in self.not_found_on]


VERSION_PATTERNS = [
    VersionPattern("bioRxiv preprint first posted online", indicative_of=[SMUR]),
    VersionPattern("The copyright holder for this preprint (which was not peer-reviewed) is the author/funder, who has "
                   "granted bioRxiv a license to display the preprint in perpetuity", indicative_of=[SMUR]),
    VersionPattern("Powered by Editorial Manager® and ProduXion Manager® from Aries Systems Corporation",
                   indicative_of=[SMUR, AM]),
    VersionPattern("This article has been accepted for publication and undergone full peer review but has not been "
                   "through the copyediting, typesetting, pagination and proofreading process, which may lead to "
                   "differences between this version and the Version of Record", indicative_of=[AM]),
    VersionPattern("UNCORRECTED PROOF", indicative_of=[P]),
    VersionPattern("Available online xxx", indicative_of=[P]),

]

# modified from: https://www.crossref.org/blog/dois-and-matching-regular-expressions/
DOI_PATTERN = '10\.\d{4,9}/[-._;()/:a-zA-Z0-9]+'

CC0 = {'short name': 'CC0',
       'long name': 'Public domain',
       'url': 'https://creativecommons.org/publicdomain/zero/1.0/'}

CC_BY = {'short name': 'CC BY',
         'long name': 'Creative Commons Attribution',
         'url': 'https://creativecommons.org/licenses/by/4.0/'}

CC_BY_NC = {'short name': 'CC BY-NC',
            'long name': 'Creative Commons Attribution-NonCommercial',
            'url': 'https://creativecommons.org/licenses/by-nc/4.0/'}

CC_BY_ND = {'short name': 'CC BY-ND',
            'long name': 'Creative Commons Attribution-NoDerivatives',
            'url': 'https://creativecommons.org/licenses/by-nd/4.0/'}

CC_BY_SA = {'short name': 'CC BY-SA',
            'long name': 'Creative Commons Attribution-ShareAlike',
            'url': 'https://creativecommons.org/licenses/by-sa/4.0/'}

CC_BY_NC_ND = {'short name': 'CC BY-NC-ND',
               'long name': 'Creative Commons Attribution-NonCommercial-NoDerivatives',
               'url': 'https://creativecommons.org/licenses/by-nc-nd/4.0/'}

CC_BY_NC_SA = {'short name': 'CC BY-NC-SA',
               'long name': 'Creative Commons Attribution-NonCommercial-ShareAlike',
               'url': 'https://creativecommons.org/licenses/by-nc-sa/4.0/'}

ALL_CC_LICENCES = [CC0, CC_BY, CC_BY_NC, CC_BY_ND, CC_BY_SA, CC_BY_NC_ND, CC_BY_NC_SA]

# not currently used anywhere:
ADDITIONAL_CC_PATTERNS = [
    {'pattern': "This is an open access article under the terms of the CC BY 4.0 license", 'error ratio': 0.1},
    {'pattern': "This is an open access article under the CC BY license", 'error ratio': 0.1},
    {'pattern': "http://creativecommons.org/licenses/by/4.0/", 'error ratio': 0.1},
    {'pattern': "This is an open access article distributed in accordance with the Creative Commons Attribution 4.0 "
                "Unported (CC BY 4.0) license, which permits others to copy, redistribute, remix, transform and build "
                "upon this work for any purpose, provided the original work is properly cited, a link to the licence "
                "is given, and indication of whether changes were made. "
                "See: https://creativecommons.org/licenses/by/4.0/"}
]

RIGHTS_RESERVED_PATTERNS = [
    {'pattern': "All rights reserved.", 'error ratio': 0.1},
]
