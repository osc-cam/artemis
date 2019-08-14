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

PROOF_PATTERNS = [
    {'pattern': "UNCORRECTED PROOF", 'error ratio': 0.1},
    {'pattern': "Available online xxx", 'error ratio': 0},
]
