# artemis

Artemis (Automatic Recognition of manuscripT vErsions and suppleMentary functIonS) is a command line application intended to facilitate and expedite self-archiving of academic journal articles, by automating the process of recognising and vetting the manuscript version of a file received by an Open Access repository (see, for example, [this blog post](https://unlockingresearch-blog.lib.cam.ac.uk/?p=1872) for more details of this process).

## Installation

On UNIX machines, clone or download this repository and then install the required Python packages by opening a terminal, navigating to the "artemis" folder you just cloned or extracted, and issuing the command:

```
$ pip3 install -r requirements.txt
``` 

Download [CERMINE](https://github.com/CeON/CERMINE) version 1.13 standalone JAR file from [here](https://maven.ceon.pl/artifactory/kdd-releases/pl/edu/icm/cermine/cermine-impl/1.13/cermine-impl-1.13-jar-with-dependencies.jar) and place it in the root of the "artemis" folder (i.e. the folder containing the artemis.py file).

## Usage

For a description of usage and arguments, issue the command:

```
$ ./artemis.py --help
```

This will produce the following output:

```
usage: Artemis [-h] [-k] [-t "Expected title of journal article"]
               [-v "submitted manuscript under review", "accepted manuscript", "proof" or "version of record"]
               <path>

Detects the manuscript version of an academic journal article

positional arguments:
  <path>                Path to input file (journal article file to be
                        analysed)

optional arguments:
  -h, --help            show this help message and exit
  -k, --keep            Keep temporary files
  -t "Expected title of journal article", --title "Expected title of journal article"
                        Expected/declared title of journal article
  -v "submitted manuscript under review", "accepted manuscript", "proof" or "version of record", --version "submitted manuscript under review", "accepted manuscript", "proof" or "version of record"
                        Expected/declared version of journal article
```

Unless you issue the optional argument -k (--keep), Artemis will automatically delete temporary files created during processing, such as text and images extracted from the input file. Temporary files are created in a folder beginning with the string "artemis-" in your system's default location for temporary directories. In UNIX machines, this is usually "/tmp".

Example usage:

```
$ ./artemis.py -t "Radiation and decline of endodontid land snails in Makatea, French \
Polynesia" -v "accepted manuscript" ~/Downloads/endodontidaeMakatea.pdf
```

Example of output from Artemis:

```
{'input file': 'endodontidaeMakatea.pdf', 'approved': True, 
'reason': 'Could not find any evidence that this PDF is publisher-generated', 
'title_match_file_metadata': False, 'number_of_publisher_tags_in_file_metadata': 0, 
'more_than_three_pages': True, 'title_match_extracted_text': False, 
'doi_match_extracted_text': False, 'cc_match_extracted_text': None, 
'title_match_cermxml': True, 'image_on_first_page': False, 'detected_logos': []}
```
