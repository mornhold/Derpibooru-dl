#-------------------------------------------------------------------------------
# Name:        Derpibooru-dl
# Purpose:
#
# Author:      woodenphone
#
# Created:     2014-02-88
# Copyright:   (c) new 2014
# Licence:     <your licence>
#-------------------------------------------------------------------------------
#!/usr/bin/env python

import time
import os
import sys
import re
import mechanize
import cookielib
import logging
import urllib2
import httplib
import random
import glob
import ConfigParser
import HTMLParser
import json
import shutil
import pickle
import socket
import hashlib
import string
import argparse
import derpibooru


# getwithinfo()
GET_REQUEST_DELAY = 0
GET_RETRY_DELAY = 30# [19:50] <@CloverTheClever> Ctrl-S: if your downloader gets a connection error, sleep 10 and increase delay between attempts by a second
GET_MAX_ATTEMPTS = 10




def setup_logging(log_file_path):
    # Setup logging (Before running any other code)
    # http://inventwithpython.com/blog/2012/04/06/stop-using-print-for-debugging-a-5-minute-quickstart-guide-to-pythons-logging-module/
    assert( len(log_file_path) > 1 )
    assert( type(log_file_path) == type("") )
    global logger
    # Make sure output dir exists
    log_file_folder =  os.path.dirname(log_file_path)
    if log_file_folder is not None:
        if not os.path.exists(log_file_folder):
            os.makedirs(log_file_folder)
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)
    formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
    fh = logging.FileHandler(log_file_path)
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(formatter)
    logger.addHandler(fh)
    ch = logging.StreamHandler()
    ch.setLevel(logging.DEBUG)
    ch.setFormatter(formatter)
    logger.addHandler(ch)
    logging.debug("Logging started.")
    return


def add_http(url):
    """Ensure a url starts with http://..."""
    if "http://" in url:
        return url
    elif "https://" in url:
        return url
    else:
        #case //derpicdn.net/img/view/...
        first_two_chars = url[0:2]
        if first_two_chars == "//":
            output_url = "https:"+url
            return output_url
        else:
            logging.error(repr(locals()))
            raise ValueError


def deescape(html):
    # de-escape html
    # http://stackoverflow.com/questions/2360598/how-do-i-unescape-html-entities-in-a-string-in-python-3-1
    deescaped_string = HTMLParser.HTMLParser().unescape(html)
    return deescaped_string


def get(url):
    #try to retreive a url. If unable to return None object
    #Example useage:
    #html = get("")
    #if html:
    assert_is_string(url)
    deescaped_url = deescape(url)
    url_with_protocol = add_http(deescaped_url)
    #logging.debug( "getting url ", locals())
    gettuple = getwithinfo(url_with_protocol)
    if gettuple:
        reply, info = gettuple
        return reply
    else:
        return


def getwithinfo(url):
    """Try to retreive a url. If unable to return None objects
    Example useage:
    html = get("")
        if html:
    """
    attemptcount = 0
    while attemptcount < GET_MAX_ATTEMPTS:
        attemptcount = attemptcount + 1
        if attemptcount > 1:
            delay(GET_RETRY_DELAY)
            logging.debug( "Attempt "+repr(attemptcount)+" for URL: "+repr(url) )
        try:
            save_file(os.path.join("debug","get_last_url.txt"), url, True)
            r = br.open(url, timeout=100)
            info = r.info()
            reply = r.read()
            delay(GET_REQUEST_DELAY)
            # Save html responses for debugging
            #print info
            #print info["content-type"]
            if "html" in info["content-type"]:
                #print "saving debug html"
                save_file(os.path.join("debug","get_last_html.htm"), reply, True)
            else:
                save_file(os.path.join("debug","get_last_not_html.txt"), reply, True)
            # Retry if empty response and not last attempt
            if (len(reply) < 1) and (attemptcount < GET_MAX_ATTEMPTS):
                logging.error("Reply too short :"+repr(reply))
                continue
            return reply,info
        except urllib2.HTTPError, err:
            logging.debug(repr(err))
            if err.code == 404:
                logging.debug("404 error! "+repr(url))
                return
            elif err.code == 403:
                logging.debug("403 error, ACCESS DENIED! url: "+repr(url))
                return
            elif err.code == 410:
                logging.debug("410 error, GONE")
                return
            else:
                save_file(os.path.join("debug","HTTPError.htm"), err.fp.read(), True)
                continue
        except urllib2.URLError, err:
            logging.debug(repr(err))
            if "unknown url type:" in err.reason:
                return
            else:
                continue
        except httplib.BadStatusLine, err:
            logging.debug(repr(err))
            continue
        except httplib.IncompleteRead, err:
            logging.debug(repr(err))
            continue
        except mechanize.BrowserStateError, err:
            logging.debug(repr(err))
            continue
        except socket.timeout, err:
            logging.debug(repr( type(err) ) )
            logging.debug(repr(err))
            continue
    logging.critical("Too many repeated fails, exiting.")
    sys.exit()# [19:51] <@CloverTheClever> if it does it more than 10 times, quit/throw an exception upstream



def save_file(filenamein,data,force_save=False):
    if not force_save:
        if os.path.exists(filenamein):
            logging.debug("file already exists! "+repr(filenamein))
            return
    sanitizedpath = filenamein# sanitizepath(filenamein)
    foldername = os.path.dirname(sanitizedpath)
    if len(foldername) >= 1:
        if not os.path.isdir(foldername):
            os.makedirs(foldername)
    file = open(sanitizedpath, "wb")
    file.write(data)
    file.close()
    return


def delay(basetime,upperrandom=0):
    #replacement for using time.sleep, this adds a random delay to be sneaky
    sleeptime = basetime + random.randint(0,upperrandom)
    #logging.debug("pausing for "+repr(sleeptime)+" ...")
    time.sleep(sleeptime)


def crossplatform_path_sanitize(path_to_sanitize,remove_repeats=False):
    """Take a desired file path and chop away at it until it fits all platforms path requirements"""
    # Remove disallowed characters
    # http://msdn.microsoft.com/en-us/library/windows/desktop/aa365247%28v=vs.85%29.aspx
    windows_bad_chars = """/\\"""
    nix_bad_carhs = """/"""
    all_bad_chars = set(windows_bad_chars)+set(nix_bad_carhs)
    if remove_repeats:
        # Remove repeated characters, such as hyphens or spaces
        pass
    # Shorten if above filepath length limits
    windows_max_filepath_length = 255
    nix_max_filepath_length = None
    # Ensure first and last characters of path segments are not whitespace
    path_segments = []




def import_list(listfilename="ERROR.txt"):
    """Read in a text file, return each line as a string in a list"""
    if os.path.exists(listfilename):# Check if there is a list
        query_list = []# Make an empty list
        list_file = open(listfilename, "rU")
        for line in list_file:
            if line[0] != "#" and line[0] != "\n":# Skip likes starting with '#' and the newline character
                if line[-1] == "\n":# Remove trailing newline if it exists
                    stripped_line = line[:-1]
                else:
                    stripped_line = line# If no trailing newline exists, we dont need to strip it
                query_list.append(stripped_line)# Add the username to the list
        list_file.close()
        return query_list
    else: # If there is no list, make one
        new_file_text = ("# Add one query per line, Full derpibooru search syntax MAY be available. Enter queries exactly as you would on the site.\n"
        + "# Any line that starts with a hash symbol (#) will be ignored.\n"
        + "# Search syntax help is available at https://derpibooru.org/search/syntax \n"
        + "# Example 1: -(pinkamena, +grimdark)\n"
        + "# Example 2: reversalis")
        list_file = open(listfilename, "w")
        list_file.write(new_file_text)
        list_file.close()
        return []


def append_list(lines,list_file_path="done_list.txt",initial_text="# List of completed items.\n",overwrite=False):
    # Append a string or list of strings to a file; If no file exists, create it and append to the new file.
    # Strings will be seperated by newlines.
    # Make sure we're saving a list of strings.
    if ((type(lines) is type(""))or (type(lines) is type(u""))):
        lines = [lines]
    # Ensure file exists and erase if needed
    if (not os.path.exists(list_file_path)) or (overwrite is True):
        list_file_segments = os.path.split(list_file_path)
        list_dir = list_file_segments[0]
        if list_dir:
            if not os.path.exists(list_dir):
                os.makedirs(list_dir)
        nf = open(list_file_path, "w")
        nf.write(initial_text)
        nf.close()
    # Write data to file.
    f = open(list_file_path, "a")
    for line in lines:
        outputline = line+"\n"
        f.write(outputline)
    f.close()
    return


class config_handler():
    def __init__(self,settings_path):
        self.settings_path = settings_path
        # Make sure settings folder exists
        settings_folder = os.path.dirname(self.settings_path)
        if settings_folder is not None:
            if not os.path.exists(settings_folder):
                os.makedirs(settings_folder)
        # Setup settings, these are static
        self.set_defaults()
        self.load_file(self.settings_path)
        self.save_settings(self.settings_path)
        self.handle_command_line_arguments()
        # Setup things that can change during program use
        self.load_deleted_submission_list()# list of submissions that are known to have been deleted
        return

    def set_defaults(self):
        """Set the defaults for settings, these will be overridden by settings from a file"""
        # derpibooru_dl.py
        # Login
        self.api_key = "Replace_this_with_your_API_key"

        # Download Settings
        self.reverse = False
        self.output_folder = "download"# Root path to download to
        self.download_submission_ids_list = True
        self.download_query_list = True
        self.output_long_filenames = False # Should we use the derpibooru supplied filename with the tags? !UNSUPPORTED!
        self.input_list_path = os.path.join("config","derpibooru_dl_tag_list.txt")
        self.done_list_path = os.path.join("config","derpibooru_done_list.txt")
        self.failed_list_path = os.path.join("config","derpibooru_failed_list.txt")
        self.save_to_query_folder = True # Should we save to multiple folders?
        self.skip_downloads = False # Don't retrieve remote submission files after searching
        self.sequentially_download_everything = False # download submission 1,2,3...
        self.go_backwards_when_using_sequentially_download_everything = False # when downloading everything in range mode should we go 10,9,8,7...?
        self.download_last_week = False # Download (approximately) the last weeks submissions
        self.skip_glob_duplicate_check = False # Skip glob.glob based duplicate check (only check if output file exists instead of scanning all output paths)
        self.skip_known_deleted = True # Skip submissions of the list of known deleted IDs
        self.deleted_submissions_list_path = os.path.join("config","deleted_submissions.txt")
        self.move_on_fail_verification = False # Should files be moved if verification of a submission fails?
        self.save_comments = False # Should comments be saved, uses more resources.

        # General settings
        self.show_menu = True # Should the text based menu system be used?
        self.hold_window_open = True # Should the window be kept open after all tasks are done?

        # Internal variables, these are set through this code only
        self.resume_file_path = os.path.join("config","resume.pkl")
        self.pointer_file_path = os.path.join("config","dl_everything_pointer.pkl")
        self.filename_prefix = "derpi_"
        self.sft_max_attempts = 10 # Maximum retries in search_for_tag()
        self.max_search_page_retries = 10 # maximum retries for a search page
        self.combined_download_folder_name = "combined_downloads"# Name of subfolder to use when saving to only one folder
        self.max_download_attempts = 10 # Number of times to retry a download before skipping
        self.verification_fail_output_path = "failed_verification"
        return

    def load_file(self,settings_path):
        """Load settings from a file"""
        config = ConfigParser.RawConfigParser()
        if not os.path.exists(settings_path):
            return
        config.read(settings_path)
        # derpibooru_dl.py
        # Login
        try:
            self.api_key = config.get("Login", "api_key")
        except ConfigParser.NoOptionError:
            pass
        # Download Settings
        try:
            self.reverse = config.getboolean("Download", "reverse")
        except ConfigParser.NoOptionError:
            pass
        try:
            self.output_folder = config.get("Download", "output_folder")
        except ConfigParser.NoOptionError:
            pass
        try:
            self.download_submission_ids_list = config.getboolean("Download", "download_submission_ids_list")
        except ConfigParser.NoOptionError:
            pass
        try:
            self.download_query_list = config.getboolean("Download", "download_query_list")
        except ConfigParser.NoOptionError:
            pass
        try:
            self.output_long_filenames = config.getboolean("Download", "output_long_filenames")
        except ConfigParser.NoOptionError:
            pass
        try:
            self.input_list_path = config.get("Download", "input_list_path")
        except ConfigParser.NoOptionError:
            pass
        try:
            self.done_list_path = config.get("Download", "done_list_path")
        except ConfigParser.NoOptionError:
            pass
        try:
            self.failed_list_path = config.get("Download", "failed_list_path")
        except ConfigParser.NoOptionError:
            pass
        try:
            self.save_to_query_folder = config.getboolean("Download", "save_to_query_folder")
        except ConfigParser.NoOptionError:
            pass
        try:
            self.skip_downloads = config.getboolean("Download", "skip_downloads")
        except ConfigParser.NoOptionError:
            pass
        try:
            self.sequentially_download_everything = config.getboolean("Download", "sequentially_download_everything")
        except ConfigParser.NoOptionError:
            pass
        try:
            self.go_backwards_when_using_sequentially_download_everything = config.getboolean("Download", "go_backwards_when_using_sequentially_download_everything")
        except ConfigParser.NoOptionError:
            pass
        try:
            self.download_last_week = config.getboolean("Download", "download_last_week")
        except ConfigParser.NoOptionError:
            pass
        try:
            self.skip_glob_duplicate_check = config.getboolean("Download", "skip_glob_duplicate_check")
        except ConfigParser.NoOptionError:
            pass
        try:
            self.skip_known_deleted = config.getboolean("Download", "skip_known_deleted")
        except ConfigParser.NoOptionError:
            pass
        try:
            self.deleted_submissions_list_path = config.get("Download", "deleted_submissions_list_path")
        except ConfigParser.NoOptionError:
            pass
        try:
            self.move_on_fail_verification = config.getboolean("Download", "move_on_fail_verification")
        except ConfigParser.NoOptionError:
            pass
        try:
            self.save_comments = config.getboolean("Download", "save_comments")
        except ConfigParser.NoOptionError:
            pass
        # General settings
        try:
            self.show_menu = config.getboolean("General", "show_menu")
        except ConfigParser.NoOptionError:
            pass
        try:
            self.hold_window_open = config.getboolean("General", "hold_window_open")
        except ConfigParser.NoOptionError:
            pass
        return

    def save_settings(self,settings_path):
        """Save settings to a file"""
        config = ConfigParser.RawConfigParser()
        config.add_section("Login")
        config.set("Login", "api_key", self.api_key )
        config.add_section("Download")
        config.set("Download", "reverse", str(self.reverse) )
        config.set("Download", "output_folder", self.output_folder )
        config.set("Download", "download_submission_ids_list", str(self.download_submission_ids_list) )
        config.set("Download", "download_query_list", str(self.download_query_list) )
        config.set("Download", "output_long_filenames", str(self.output_long_filenames) )
        config.set("Download", "input_list_path", self.input_list_path )
        config.set("Download", "done_list_path", self.done_list_path )
        config.set("Download", "failed_list_path", self.failed_list_path )
        config.set("Download", "save_to_query_folder", str(self.save_to_query_folder) )
        config.set("Download", "skip_downloads", str(self.skip_downloads) )
        config.set("Download", "sequentially_download_everything", str(self.sequentially_download_everything) )
        config.set("Download", "go_backwards_when_using_sequentially_download_everything", str(self.go_backwards_when_using_sequentially_download_everything) )
        config.set("Download", "download_last_week", str(self.download_last_week) )
        config.set("Download", "skip_glob_duplicate_check", str(self.skip_glob_duplicate_check) )
        config.set("Download", "skip_known_deleted", str(self.skip_known_deleted) )
        config.set("Download", "deleted_submissions_list_path", str(self.deleted_submissions_list_path) )
        config.set("Download", "move_on_fail_verification", str(self.move_on_fail_verification) )
        config.set("Download", "save_comments", str(self.save_comments) )
        config.add_section("General")
        config.set("General", "show_menu", str(self.show_menu) )
        config.set("General", "hold_window_open", str(self.hold_window_open) )
        with open(settings_path, "wb") as configfile:
            config.write(configfile)
        return

    def handle_command_line_arguments(self):
        """Handle any command line arguments"""
        parser = argparse.ArgumentParser(description="DESCRIPTION FIELD DOES WHAT?")
        # Define what arguments are allowed
        menu_group = parser.add_mutually_exclusive_group()
        menu_group.add_argument("-m", "--menu", action="store_true",help="Show text based menu.")# Show text based menu
        menu_group.add_argument("-b", "--batch", action="store_true",help="Run in batch mode.")# Use batch mode
        parser.add_argument("-k", "--api_key",help="API Key.")
        parser.add_argument("-ids", "--download_submission_ids_list",help="download_submission_ids_list")
        parser.add_argument("-queries", "--download_query_list",help="download_query_list")
        parser.add_argument("-longfn", "--output_long_filenames",help="output_long_filenames")
        parser.add_argument("-qf", "--save_to_query_folder",help="save_to_query_folder")
        parser.add_argument("-skip", "--skip_downloads",help="skip_downloads")
        parser.add_argument("--sequentially_download_everything",help="sequentially_download_everything")
        parser.add_argument("--go_backwards_when_using_sequentially_download_everything",help="go_backwards_when_using_sequentially_download_everything")
        parser.add_argument("-ilp", "--input_list_path",help="input_list_path")
        parser.add_argument("--save_args_to_settings", action="store_true")# Write new settings to file
        # Store arguments to settings
        args = parser.parse_args()
        if args.menu:
            self.show_menu = True
        elif args.batch:
            self.show_menu = False
        if args.api_key:
            self.api_key = args.api_key
        if args.download_submission_ids_list:
            self.download_submission_ids_list = args.download_submission_ids_list
        if args.download_query_list:
            self.download_query_list = args.download_query_list
        if args.output_long_filenames:
            self.output_long_filenames = args.output_long_filenames
        if args.save_to_query_folder:
            self.save_to_query_folder = args.save_to_query_folder
        if args.skip_downloads:
            self.skip_downloads = args.skip_downloads
        if args.sequentially_download_everything:
            self.sequentially_download_everything = args.sequentially_download_everything
        if args.go_backwards_when_using_sequentially_download_everything:
            self.go_backwards_when_using_sequentially_download_everything = args.go_backwards_when_using_sequentially_download_everything
        if args.input_list_path:
            self.input_list_path = args.input_list_path
        # Write to settings file if needed. Must be done last
        if args.save_args_to_settings:
            self.save_settings()
        return

    def load_deleted_submission_list(self):
        """Load a list of known bad IDs from a file"""
        self.deleted_submissions_list = import_list(listfilename=self.deleted_submissions_list_path)
        return self.deleted_submissions_list

    def update_deleted_submission_list(self,submission_id):
        """Add a bad ID to the list in both ram and disk"""
        self.deleted_submissions_list.append(submission_id)
        append_list(submission_id, list_file_path=self.deleted_submissions_list_path, initial_text="# List of deleted IDs.\n", overwrite=False)
        return



def assert_is_string(object_to_test):
    """Make sure input is either a string or a unicode string"""
    if( (type(object_to_test) == type("")) or (type(object_to_test) == type(u"")) ):
        return
    logging.critical(repr(locals()))
    raise(ValueError)


def decode_json(json_string):
    """Wrapper for JSON decoding
    Return None object if known problem case occurs
    Return decoded data if successful
    Reraise unknown cases for caught exceptions"""
    assert_is_string(json_string)
    try:
        save_file(os.path.join("debug","last_json.json"), json_string, True)
        json_data = json.loads(json_string)
        return json_data
    except ValueError, err:
        # Retry if bad json recieved
        if "Unterminated string starting at:" in repr(err):
            logging.debug("JSON data invalid, failed to decode.")
            logging.debug(repr(json_string))
            return
        elif "No JSON object could be decoded" in repr(err):
            if len(json_string) < 20:
                logging.debug("JSON string was too short!")
                logging.debug(repr(json_string))
                return
            else:
                logging.critical(repr(locals()))
                raise(err)
        # Log locals and crash if unknown issue
        else:
            logging.critical(repr(locals()))
            raise(err)


def read_file(path):
    """grab the contents of a file"""
    f = open(path, "r")
    data = f.read()
    f.close()
    return data


def setup_browser():
    #Initialize browser object to global variable "br" using cokie jar "cj"
    # Browser
    global br
    br = mechanize.Browser()
    br.set_cookiejar(cj)
    # Browser options
    br.set_handle_equiv(True)
    br.set_handle_gzip(True)
    br.set_handle_redirect(True)
    br.set_handle_referer(True)
    br.set_handle_robots(False)
    # Follows refresh 0 but not hangs on refresh > 0
    br.set_handle_refresh(mechanize._http.HTTPRefreshProcessor(), max_time=1)
    # User-Agent (this is cheating, ok?)
    #br.addheaders = [("User-agent", "Mozilla/5.0 (X11; U; Linux i686; en-US; rv:1.9.0.1) Gecko/2008071615 Fedora/3.0.1-1.fc9 Firefox/3.0.1")]
    #br.addheaders = [("User-agent", "Trixie is worst pony")]#[13:57] <%barbeque> as long as it's not something like "trixie is worst pony"
    #print "trixie is worst pony"
    br.addheaders = [("User-agent", "derpibooru_dl.py - https://github.com/woodenphone/Derpibooru-dl")] # Let's make it easy for the admins to see us so if something goes wrong we'll find out about it.
    return


def search_for_query(settings,search_query):
    """Perform search for a query on derpibooru.
    Return a lost of found submission IDs"""
    assert_is_string(search_query)
    logging.debug("Starting search for query: "+repr(search_query))
    found_submissions = []
    for image in derpibooru.Search().key(settings.api_key).limit(None).query(search_query):
        found_submissions.append(image.id)
    return found_submissions


def check_if_deleted_submission(json_dict):
    """Check whether the JSON Dict for a submission shows it as being deleted"""
    keys = json_dict.keys()
    if "deletion_reason" in keys:
        logging.error("Deleted submission! Reason: "+repr(json_dict["deletion_reason"]))
        return True
    elif "duplicate_of" in keys:
        logging.error("Deleted duplicate submission! Reason: "+repr(json_dict["duplicate_of"]))
        return True
    else:
        return False


def copy_over_if_duplicate(settings,submission_id,output_folder):
    """Check if there is already a copy of the submission downloaded in the download path.
    If there is, copy the existing version to the suppplied output location then return True
    If no copy can be found, return False"""
    assert_is_string(submission_id)
    # Setting to override this function for speed optimisation on single folder output
    if settings.skip_glob_duplicate_check:
        return False
    # Generate expected filename pattern
    submission_filename_pattern = "*"+submission_id+".*"
    # Generate search pattern
    glob_string = os.path.join(settings.output_folder, "*", submission_filename_pattern)
    # Use glob to check for existing files matching the expected pattern
    #logging.debug("CALLING glob.glob, local vars: "+ repr(locals()))
    glob_matches = glob.glob(glob_string)
    #logging.debug("CALLED glob.glob, locals: "+repr(locals()))
    # Check if any matches, if no matches then return False
    if len(glob_matches) == 0:
        return False
    else:
        # If there is an existing version:
        for glob_match in glob_matches:
            # Skip any submission with the wrong ID
            match_submission_id = find_id_from_filename(settings, glob_match)
            if match_submission_id != submission_id:
                continue
            # If there is an existing version in the output path, nothing needs to be copied
            if output_folder in glob_match:
                return False
            else:
                # Copy over submission file and metadata JSON
                logging.info("Trying to copy from previous download: "+repr(glob_match))
                # Check output folders exist
                # Build expected paths
                match_dir, match_filename = os.path.split(glob_match)
                expected_json_input_filename = submission_id+".json"
                expected_json_input_folder = os.path.join(match_dir, "json")
                expected_json_input_location = os.path.join(expected_json_input_folder, expected_json_input_filename)
                json_output_folder = os.path.join(output_folder, "json")
                json_output_filename = submission_id+".json"
                json_output_path = os.path.join(json_output_folder, json_output_filename)
                submission_output_path = os.path.join(output_folder,match_filename)
                # Redownload if a file is missing
                if not os.path.exists(glob_match):
                    logging.debug("Submission file to copy is missing.")
                    return False
                if not os.path.exists(expected_json_input_location):
                    logging.debug("JSON file to copy is missing.")
                    return False
                # Ensure output path exists
                if not os.path.exists(json_output_folder):
                    os.makedirs(json_output_folder)
                if not os.path.exists(output_folder):
                    os.makedirs(output_folder)
                logging.info("Copying files for submission: "+repr(submission_id)+" from "+repr(match_dir)+" to "+repr(output_folder))
                # Copy over files
                try:
                    # Copy submission file
                    shutil.copy2(glob_match, submission_output_path)
                    # Copy JSON
                    shutil.copy2(expected_json_input_location, json_output_path)
                    return True
                except IOError, err:
                    logging.error("Error copying files!")
                    logging.exception(err)
                    return False


def download_submission(settings,search_query,submission_id):
    """Download a submission from Derpibooru"""
    assert_is_string(search_query)
    submission_id = str(submission_id)
    setup_browser()
    query_for_filename = convert_query_for_path(settings,search_query)
    #logging.debug("Downloading submission:"+submission_id)
    # Build JSON paths
    json_output_filename = submission_id+".json"
    if settings.save_to_query_folder is True:
        json_output_path = os.path.join(settings.output_folder,query_for_filename,"json",json_output_filename)
    else:
        # Option to save to a single combined folder
        json_output_path = os.path.join(settings.output_folder,settings.combined_download_folder_name,"json",json_output_filename)
    # Check if download can be skipped
    # Check if JSON exists
    if os.path.exists(json_output_path):
        logging.debug("JSON for this submission already exists, skipping.")
        return
    # Build output folder path
    if settings.save_to_query_folder is True:
        output_folder = os.path.join(settings.output_folder,query_for_filename)
    else:
        # Option to save to a single combined folder
        output_folder = os.path.join(settings.output_folder,settings.combined_download_folder_name)
    # Check for dupliactes in download folder
    if copy_over_if_duplicate(settings, submission_id, output_folder):
        return
    # Option to skip loading remote submission files
    if settings.skip_downloads is True:
        return
    # Option to skip previously encountered deleted submissions
    if settings.skip_known_deleted:
        if submission_id in settings.deleted_submissions_list:
            return
    # Build JSON URL
    # Option to save comments, uses more resources.
    if settings.save_comments:
        json_url = "https://derpibooru.org/"+submission_id+".json?comments=true&key="+settings.api_key
    else:
        json_url = "https://derpibooru.org/"+submission_id+".json?key="+settings.api_key
    # Retry if needed
    download_attempt_counter = 0
    while download_attempt_counter <= settings.max_download_attempts:
        download_attempt_counter += 1
        if download_attempt_counter > 1:
            logging.debug("Attempt "+repr(download_attempt_counter))
        # Load JSON URL
        json_page = get(json_url)
        if not json_page:
            continue
        # Convert JSON to dict
        json_dict = decode_json(json_page)
        if json_dict is None:
            continue
        # Check if submission is deleted
        if check_if_deleted_submission(json_dict):
            logging.debug("Submission was deleted.")
            logging.debug(repr(json_page))
            settings.update_deleted_submission_list(submission_id)
            return
        # Extract needed info from JSON
        image_url = json_dict["image"]
        image_file_ext = json_dict["original_format"]
        image_height = json_dict["height"]
        image_width = json_dict["width"]
        # Build image output filenames
        if settings.output_long_filenames:
            # Grab the filename from the url by throwing away everything before the last forwardslash
            image_filename_crop_regex = """.+\/(.+)"""
            image_filename_search = re.search(image_filename_crop_regex, image_url, re.IGNORECASE|re.DOTALL)
            image_filename = image_filename_search.group(1)
            image_output_filename = settings.filename_prefix+image_filename+"."+image_file_ext
        else:
            image_output_filename = settings.filename_prefix+submission_id+"."+image_file_ext
        image_output_path = os.path.join(output_folder,image_output_filename)
        # Load image data
        authenticated_image_url = image_url+"?key="+settings.api_key
        logging.debug("Loading submission image. Height:"+repr(image_height)+", Width:"+repr(image_width)+", URL: "+repr(authenticated_image_url))
        image_data = get(authenticated_image_url)
        if not image_data:
            return
        # Image should always be bigger than this, if it isn't we got a bad file
        if len(image_data) < 100:
            logging.error("Image data was too small! "+repr(image_data))
            continue
        # Save image
        save_file(image_output_path, image_data, True)
        # Save JSON
        save_file(json_output_path, json_page, True)
        logging.debug("Download successful")
        return
    logging.error("Too many retries, skipping this submission.")
    logging.debug(repr(locals()))
    return


def read_pickle(file_path):
    file_data = read_file(file_path)
    pickle_data = pickle.loads(file_data)
    return pickle_data


def save_pickle(path,data):
    # Save data to pickle file
    # Ensure folder exists.
    if not os.path.exists(path):
        pickle_path_segments = os.path.split(path)
        pickle_dir = pickle_path_segments[0]
        if pickle_dir:# Make sure we aren't at the script root
            if not os.path.exists(pickle_dir):
                os.makedirs(pickle_dir)
    pf = open(path, "wb")
    pickle.dump(data, pf)
    pf.close()
    return


def save_resume_file(settings,search_tag,submission_ids):
    # Save submissionIDs and search_tag to pickle
    logging.debug("Saving resume data pickle")
    # {"search_tag":"FOO", "submission_ids":["1","2"]}
    # Build dict
    resume_dict = {
    "search_tag":search_tag,
    "submission_ids":submission_ids
    }
    save_pickle(settings.resume_file_path, resume_dict)
    return


def clear_resume_file(settings):
    # Erase pickle
    logging.debug("Erasing resume data pickle")
    if os.path.exists(settings.resume_file_path):
        os.remove(settings.resume_file_path)
    return


def resume_downloads(settings):
    # Look for pickle of submissions to iterate over
    if os.path.exists(settings.resume_file_path):
        logging.debug("Resuming from pickle")
        # Read pickle:
        resume_dict = read_pickle(settings.resume_file_path)
        search_tag = resume_dict["search_tag"]
        submission_ids = resume_dict["submission_ids"]
        # Iterate over submissions
        download_submission_id_list(settings,submission_ids,search_tag)
        # Clear temp file
        clear_resume_file(settings)
        append_list(search_tag, settings.done_list_path)
        return search_tag
    else:
        return False


def download_submission_id_list(settings,submission_ids,query):
    # Iterate over submissions
    submission_counter = 0
    # If no submissions to save record failure
    if len(submission_ids) == 0:
        logging.warning("No submissions to save! Query:"+repr(query))
        append_list(query, settings.failed_list_path, initial_text="# List of failed items.\n")
    if settings.reverse:
        logging.info("Reverse mode is active, reversing download order.")
        submission_ids.reverse()
    for submission_id in submission_ids:
        submission_counter += 1
        # Only save pickle every 1000 items to help avoid pickle corruption
        if (submission_counter % 1000) == 0:
            cropped_submission_ids = submission_ids[( submission_counter -1 ):]
            save_resume_file(settings,query,cropped_submission_ids)
        logging.info("Now working on submission "+repr(submission_counter)+" of "+repr(len(submission_ids) )+" : "+repr(submission_id)+" for: "+repr(query) )
        # Try downloading each submission
        download_submission(settings, query, submission_id)
        print "\n\n"
    return


def save_pointer_file(settings,start_number,finish_number):
    """Save start and finish numbers to pickle"""
    logging.debug("Saving resume data pickle")
    # {"start_number":0, "finish_number":100}
    # Build dict
    resume_dict = {
    "start_number":start_number,
    "finish_number":finish_number
    }
    save_pickle(settings.pointer_file_path, resume_dict)
    return


def clear_pointer_file(settings):
    """Erase range download pickle"""
    logging.debug("Erasing resume data pickle")
    if os.path.exists(settings.pointer_file_path):
        os.remove(settings.pointer_file_path)
    return


def get_latest_submission_id(settings):
    """Find the most recent submissions ID"""
    logging.debug("Getting ID of most recent submission...")
    latest_submissions = []
    for image in derpibooru.Search().key(settings.api_key):
        submission_id = image.id
        latest_submissions.append(submission_id)
    ordered_latest_submissions = sorted(latest_submissions)
    latest_submission_id = int(ordered_latest_submissions[0])
    logging.debug("Most recent submission ID:"+repr(latest_submission_id))
    return latest_submission_id


def download_this_weeks_submissions(settings):
    """Download (about) one weeks worth of the most recent submissions"""
    logging.info("Now downloading the last week's submissions.")
    # Get starting number
    latest_submission_id = get_latest_submission_id(settings)
    # Calculate ending number
    one_weeks_submissions_number = 1000 * 7 # less than 1000 per day
    finish_number = latest_submission_id - one_weeks_submissions_number  # Add a thousand to account for new submissions added during run
    logging.info("Downloading the last "+repr(one_weeks_submissions_number)+" submissions. Starting at "+repr(latest_submission_id)+" and stopping at "+repr(finish_number))
    download_range(settings,latest_submission_id,finish_number)
    return


def download_everything(settings):
    """Start downloading everything or resume downloading everything"""
    logging.info("Now downloading all submissions on the site")
    # Start downloading everything
    latest_submission_id = get_latest_submission_id(settings)
    start_number = 0
    finish_number = latest_submission_id + 50000 # Add 50,000 to account for new submissions added during run
    if settings.go_backwards_when_using_sequentially_download_everything:
        # Swap start and finish numbers for backwards mode
        start_number, finish_number =  latest_submission_id, start_number
    download_range(settings,start_number,finish_number)
    return


def resume_range_download(settings):
    # Look for pickle of range to iterate over
    if os.path.exists(settings.pointer_file_path):
        logging.info("Resuming range from pickle")
        # Read pickle:
        resume_dict = read_pickle(settings.pointer_file_path)
        start_number = resume_dict["start_number"]
        finish_number = resume_dict["finish_number"]
        # Iterate over range
        download_range(settings,start_number,finish_number)
    return


def download_range(settings,start_number,finish_number):
    """Try to download every submission within a given range
    If finish number is less than start number, run over the range backwards"""
    # If starting point is after end point, we're going backwards
    if(start_number > finish_number):
        backwards = True
    else:
        backwards = False
    assert(finish_number <= 2000000)# less than 2 million, 1,252,291 submissions as of 2016-09-18
    assert(start_number >= 0)# First submission is ID 0
    assert(type(finish_number) is type(1))# Must be integer
    assert(type(start_number) is type(1))# Must be integer
    total_submissions_to_attempt = abs(finish_number - start_number)
    logging.info("Downloading range: "+repr(start_number)+" to "+repr(finish_number))
    # Iterate over range of id numbers
    submission_pointer = start_number
    loop_counter = 0
    while (loop_counter <= total_submissions_to_attempt ):
        loop_counter += 1
        assert(submission_pointer >= 0)# First submission is ID 0
        assert(submission_pointer <= 2000000)# less than 2 million, 1,252,291 submissions as of 2016-09-18
        assert(type(submission_pointer) is type(1))# Must be integer
        # Only save pickle every 1000 items to help avoid pickle corruption
        if (submission_pointer % 1000) == 0:
            save_pointer_file(settings, submission_pointer, finish_number)
        logging.info("Now working on submission "+repr(loop_counter)+" of "+repr(total_submissions_to_attempt)+", ID: "+repr(submission_pointer)+" for range download mode" )
        # Try downloading each submission
        download_submission(settings, "RANGE_MODE", submission_pointer)
        print "\n\n"
        # Add/subtract from counter depending on mode
        if backwards:
            submission_pointer -= 1
        else:
            submission_pointer += 1
    # Clean up once everything is done
    clear_pointer_file(settings)
    return


def download_ids(settings,query_list,folder):
    logging.info("Now downloading user set IDs.")
    submission_ids = []
    for query in query_list:
        # remove invalid items
        if re.search("[^\d]",query):
            logging.debug("Not a submissionID! skipping.")
            continue
        else:
            submission_ids.append(query)
    download_submission_id_list(settings,submission_ids,folder)
    return


def process_query(settings,search_query):
    """Download submissions for a tag on derpibooru"""
    assert_is_string(search_query)
    #logging.info("Processing tag: "+search_query)
    # Run search for query
    submission_ids = search_for_query(settings, search_query)
    # Save data for resuming
    if len(submission_ids) > 0:
        save_resume_file(settings,search_query,submission_ids)
    # Download all found items
    download_submission_id_list(settings,submission_ids,search_query)
    # Clear temp data
    clear_resume_file(settings)
    return


def download_query_list(settings,query_list):
    logging.info("Now downloading user set tags/queries")
    counter = 0
    for search_query in query_list:
        counter += 1
        logging.info("Now proccessing query "+repr(counter)+" of "+repr(len(query_list))+": "+repr(search_query))
        process_query(settings,search_query)
        append_list(search_query, settings.done_list_path)
    return


def convert_tag_string_to_search_string(settings,query):
    """Fix a tag string for use as a search query string"""
    colons_fixed = query.replace("-colon-",":")
    dashes_fixed = colons_fixed.replace("-dash-","-")
    dots_fixed = dashes_fixed.replace("-dot-",".")
    return dots_fixed

def convert_tag_list_to_search_string_list(settings,query_list):
    """Convert a whole list of queries to the new search format"""
    processed_queries = []
    for raw_query in query_list:
        processed_query = convert_tag_string_to_search_string(settings,raw_query)
        processed_queries.append(processed_query)
    return processed_queries


def convert_query_for_path(settings,query):
    """Convert a query to the old style -colon- format for filenames"""
    colons_fixed = query.replace(":", "-colon-")
    dashes_fixed = colons_fixed.replace("-", "-dash-")
    dots_fixed = dashes_fixed.replace(".", "-dot-")
    return dots_fixed


def verify_folder(settings,target_folder):
    """Compare ID number and SHA512 hashes from submission JSON against their submission files,
     moving those that don't match to another folder"""
    logging.info("Verifying "+repr(target_folder))
    files_list = walk_for_file_paths(target_folder)
    if len(files_list) < 1:
        logging.error("No files to verify!")
        return
    counter = 0
    pass_count = 0
    fail_count = 0
    for file_path in files_list:
        counter += 1
        logging.info("Verifying submission "+repr(counter)+" of "+repr(len(files_list))+" "+repr(file_path))
        last_status = verify_saved_submission(settings,file_path)
        if last_status is True:
            pass_count += 1
        elif last_status is False:
            fail_count += 1
    logging.info("Finished verification with "+repr(pass_count)+" PASSED and "+repr(fail_count)+" FAILED for "+repr(target_folder))
    return


def walk_for_file_paths(start_path):
    """Use os.walk to collect a list of paths to files mathcing input parameters.
    Takes in a starting path and a list of patterns to check against filenames
    Patterns follow fnmatch conventions."""
    logging.debug("Starting walk. start_path:"+repr(start_path))
    assert(type(start_path) == type(""))
    matches = []
    for root, dirs, files in os.walk(start_path):
        dirs[:] = [d for d in dirs if d not in ["json"]]# Scanning /json/ is far too slow for large folders, skip it.
        c = 1
        logging.debug("root: "+root)
        for filename in files:
            c += 1
            if (c % 1000) == 0:
                logging.debug("File # "+repr(c)+": "+repr(filename))
            match = os.path.join(root,filename)
            matches.append(match)
        logging.debug("End folder")
    logging.debug("Finished walk.")
    return matches


def verify_saved_submission(settings,target_file_path):
    """Compare ID number SHA512 hash from a submissions JSON with the submission file and move if not matching
    return True if pass, False if fail"""
    # http://www.pythoncentral.io/hashing-strings-with-python/
    failed_test = False
    # Generate filenames and paths
    # Find out if we were given a JSON file
    if target_file_path[-5:].lower() == ".json".lower():
        # We were given a JSON file, so convert the folder to the submission one
        json_folder = os.path.dirname(target_file_path)
        target_folder = os.path.dirname(json_folder)
    else:
        # Not a JSON file, use the folder we are in
        target_folder = os.path.dirname(target_file_path)
    submission_id = find_id_from_filename(settings, target_file_path)
    glob_submission_filename = settings.filename_prefix+submission_id+".*"
    glob_submission_path = os.path.join(target_folder, glob_submission_filename)
    # Use glob to find submission filename
    glob_matches = glob.glob(glob_submission_path)
    if len(glob_matches) != 1:
        failed_test = True
        if len(glob_matches) == 0:
            # No matches, this means fthe file is missing.
            logging.error("No submissions matched glob string!")
            logging.debug(repr(locals()))
            return False
        else:
            # More than one match, this should never happen.
            logging.error("More than one submission matched glob string!")
            logging.debug(repr(locals()))
            raise(ValueError)
    else:
        # If there is a single glob match, get the filename.
        assert(len(glob_matches) is 1)
        submission_path = glob_matches[0]
        submission_filename = os.path.basename(submission_path)
    submission_fail_folder = settings.verification_fail_output_path
    submission_fail_path = os.path.join(submission_fail_folder, submission_filename)
    json_filename = submission_id+".json"
    json_path = os.path.join(target_folder, "json", json_filename)
    json_fail_folder = os.path.join(settings.verification_fail_output_path, "json")
    json_fail_path = os.path.join(json_fail_folder, json_filename)
    json_string = read_file(json_path)
    decoded_json = decode_json(json_string)
    # Test the data
    # If ID < 6000 or type is .svg, skip tests.
    id_from_json = str(decoded_json["id"])
    if int(id_from_json) < 6000:
        logging.info("ID below 6000, skipping tests due to unreliable hash.")
        return None
    if submission_path[-4:].lower() == ".svg".lower():
        logging.info("Extention is .svg, skipping tests due to unreliable hash.")
        return None
    # Does the JSON provided hash match the image?
    json_hash = decoded_json["sha512_hash"]
    # http://www.pythoncentral.io/hashing-files-with-python/
    BLOCKSIZE = 65536
    hasher = hashlib.sha512()
    with open(submission_path, "rb") as afile:
        buf = afile.read(BLOCKSIZE)
        while len(buf) > 0:
            hasher.update(buf)
            buf = afile.read(BLOCKSIZE)
    file_hash = u"" + hasher.hexdigest()# convert to unicode
    if json_hash != file_hash:
        logging.error("Image hash did not match JSON "+repr(submission_path))
        logging.debug(repr(file_hash))
        logging.debug(repr(json_hash))
        failed_test = True
    # Does the ID from the JSON match the image and JSON filenames?
    # Image filename
    id_from_image_filename = find_id_from_filename(settings, submission_path)
    if id_from_json != id_from_image_filename:
        logging.error("Image filename did not match JSON ID for "+repr(submission_path))
        logging.debug(repr(id_from_json)+" vs "+repr(id_from_image_filename))
        failed_test = True
    # JSON filename
    id_from_json_filename = find_id_from_filename(settings, json_path)
    if id_from_json != id_from_json_filename:
        logging.error("JSON filename did not match JSON ID "+repr(json_path))
        failed_test = True
    # End of tests
    if failed_test is True:
        # Move if any test was failed
        logging.error("Verification FAIL: "+repr(target_file_path))
        logging.debug(repr(locals()))
        if settings.move_on_fail_verification:
            logging.info("Moving sumbission and metadata to "+repr(settings.verification_fail_output_path))
            try:
                # Move submission file
                if os.path.exists(submission_path):
                    if not os.path.exists(submission_fail_folder):
                        os.makedirs(submission_fail_folder)
                    shutil.move(submission_path, submission_fail_path)
                # Move JSON file
                if os.path.exists(json_path):
                    if not os.path.exists(json_fail_folder):
                        os.makedirs(json_fail_folder)
                    shutil.move(json_path, json_fail_path)
                return False
            except IOError, err:
                logging.error("Error copying files!")
                logging.exception(err)
                return False
    else:
        logging.info("Verification PASS: "+repr(target_file_path))
        return True


def find_id_from_filename(settings, file_path):
    """Extract submission ID from a file path or filename"""
    filename = os.path.basename(file_path)
    if filename[-5:].lower() == ".json".lower():# If the path ends in .json
        # JSON files always use the ID as the filename
        # 751715.json
        submission_id = filename[:-5]
        return submission_id
    else: # Not JSON
        # Expected filename types
        # Long derpibooru:
        # "image":"//derpicdn.net/img/view/2014/10/27/751715__safe_twilight+sparkle_rainbow+dash_pinkie+pie_fluttershy_rarity_applejack_comic_crossover_mane+six.jpeg",
        # Long derpibooru_dl:
        # derpi_751715__safe_twilight+sparkle_rainbow+dash_pinkie+pie_fluttershy_rarity_applejack_comic_crossover_mane+six.jpeg
        # Short derpibooru_dl:
        # derpi_751715.jpeg
        id_regex = """(\d+)(?:[_\.])"""
        id_search = re.search(id_regex, filename, re.IGNORECASE|re.DOTALL)
        submission_id = id_search.group(1)
        return submission_id


def verify_api_key(api_key):
    """Test to see if a given API key looks real.
    Return True if it looks okay, False if it looks bad"""
    assert(type(api_key) is type(""))# If this is not a string bad things will probably happen, and something has most likely gone wrong in the import code
    key_is_valid = True
    # Test for the default string
    if api_key == "Replace_this_with_your_API_key":
        logging.error("API key was default (No key was set).")
        key_is_valid = False
    # Test length of key
    # [21:07] <@CloverTheClever> Ctrl-S: it'll be alphanumeric and fixed size iirc
    # Known valid lengths: 20
    if (len(api_key) != 20):
        logging.error("API key length invalid. Should be 20 chars. Length: "+repr(len(api_key)))
        key_is_valid = False
    # Test if any characters outside those allowed are in the string
    # "<%byte[]> it's generated with SecureRandom.urlsafe_base64(rlength).tr('lIO0', 'sxyz')
    # rlength is 15"
    # http://apidock.com/ruby/SecureRandom/urlsafe_base64/class
    # http://stackoverflow.com/questions/89909/how-do-i-verify-that-a-string-only-contains-letters-numbers-underscores-and-da
    # Remove any characters that are allowed, if any characters remain we have invalid characters in the string.
    allowed_characters = string.ascii_letters + string.digits + "-_"# http://apidock.com/ruby/SecureRandom/urlsafe_base64/class
    invalid_characters_in_key = set(api_key) - set(allowed_characters)
    if invalid_characters_in_key:
        logging.error("API key contains invalid characters.")
        logging.debug("Invalid characters found: "+repr(invalid_characters_in_key))
        key_is_valid = False
        # Check ig it's the first or last bit that's wrong.
        if set(api_key[:5]) - set(allowed_characters):
            logging.error("Problem in first 5 characters")
        if set(api_key[-5:]) - set(allowed_characters):
            logging.error("Problem in last 5 characters")
    # Try actually loading something with the key. A search for "explicit" will fail if key is invalid.
    key_test_url = "https://derpibooru.org/search.json?q=explicit&key="+api_key
    test_response = get(key_test_url)
    if len(test_response) <= len("""{"search":[]}"""):
        logging.error("Search for 'explicit' failed using this key! Check key and account display settings!")
        key_is_valid = False
    test_response_dict = decode_json(test_response)
    # If no test has failed, we have a valid key.
    if key_is_valid:
        logging.debug("API Key looks fine.")
    else:
        logging.warning("API key looks invalid!")
        logging.debug("First 5 chars of key:"+repr(api_key[:5]))
        logging.debug("First 5 chars of key:"+repr(api_key[-5:]))
        print("The API key you entered is: "+api_key+" This message is not recorded to the log file.")
    return key_is_valid # Boolean can be passed out as-is


def print_menu_options():
    """Main info text for menu"""
    print "1. Download the last week or so's submissions."
    print "2. Enter and download a range of submission IDs."
    print "3. Enter and download the results of a search query"
    print "4. Download the results of each query and submission ID in the download list"
    print "5. Run downloads automatically based on settings file."
    print "X. Exit."
    return


def menu_range_prompt(settings,input_file_list):
    """Download user specified range"""
    print "Enter ID to start from then press enter. Leave blank to cancel."
    start_id_input = raw_input()
    try:
        start_id = int(start_id_input)
    except ValueError, err:
        logging.info("Canceled.")
        return
    print "Enter ID to stop at then press enter. Leave blank to cancel."
    stop_id_input = raw_input()
    try:
        stop_id = int(stop_id_input)
    except ValueError, err:
        logging.info("Canceled.")
        return
    download_range(settings,start_id,stop_id)
    return


def console_menu(settings,input_file_list):
    """Simple text based menu"""
    menu_open = True
    while menu_open:
        print_menu_options()
        print "Enter an option then press return"
        menu_data = raw_input()
        logging.debug("Menu user input:"+repr(menu_data))
        if menu_data == "1":
            # Download the last week's submissions
            download_this_weeks_submissions(settings)
            continue
        elif menu_data == "2":
            # Download user specified range
            menu_range_prompt(settings,input_file_list)
            continue
        elif menu_data == "3":
            # Download a user specified query.
            print "Enter your search query then press enter. Leave empty to cancel."
            search_query = raw_input()
            logging.debug("Query: "+repr(search_query))
            if len(search_query) > 0:
                process_query(settings,search_query)
                append_list(search_query, settings.done_list_path)
            continue
        elif menu_data == "4":
            # Run over download list
            download_query_list(settings,input_file_list)
            continue
        elif menu_data == "5":
            # Run automatic batch mode
            run_batch_mode(settings,input_file_list)
            continue
        elif (menu_data == "x") or (menu_data == "X"):
            logging.info("Exiting menu.")
            return
        else:
            print "Invalid selection, try again."
            continue
    return


def run_batch_mode(settings,input_file_list):
    """Run downloads based on settings without the need for user interaction"""
    # Begin new download operations
    # Ordered based on expected time to complete operations.
    # Download individual submissions
    if settings.download_submission_ids_list:
        download_ids(settings,input_file_list,"from_list")
    # Download last week mode (~7,000 items)
    if settings.download_last_week:
        download_this_weeks_submissions(settings)
    # Process each search query
    if settings.download_query_list:
        download_query_list(settings,input_file_list)
    # Download evrything mode
    if settings.sequentially_download_everything:
        download_everything(settings)
    return


def remove_before_last_query(resumed_query,input_file_list):
    """Crop list of queries to exclude everything upto and including the one that was resumed"""
    if resumed_query is not False:
        if resumed_query in input_file_list:
            # Skip everything before and including resumed tag
            logging.info("Skipping all items before the resumed tag: "+repr(resumed_query))
            #logging.debug(repr(tag_list))
            position_of_resumed_query = input_file_list.index(resumed_query)
            position_to_keep_after = position_of_resumed_query + 1
            input_file_list = input_file_list[position_to_keep_after:]
    return input_file_list


def main():
    # Load settings
    settings = config_handler(os.path.join("config","derpibooru_dl_config.cfg"))
    valid_api_key = verify_api_key(settings.api_key)
    if not valid_api_key:
        logging.warning("Using API key that looks bad, some images may not be available!")
        logging.warning("Check that you entered your API key correctly.")
    if settings.api_key == "Replace_this_with_your_API_key": # Remove unset key
        logging.warning("No API key set, weird things may happen.")
        settings.api_key = ""
    # Load tag list
    raw_input_file_list = import_list(settings.input_list_path)
    # Fix input list
    input_file_list = convert_tag_list_to_search_string_list(settings, raw_input_file_list)
    #submission_list = import_list("config\\derpibooru_dl_submission_id_list.txt")
    # DEBUG
    #download_submission(settings,"DEBUG","263139")
    #print search_for_tag(settings,"test")
    #process_tag(settings,"test")
    #copy_over_if_duplicate(settings,"134533","download\\flitterpony")
    #a = read_pickle("debug\\locals.pickle")
    #print ""
    #return
    # /DEBUG
    # Handle resuming query download operations
    logging.info("Attempting to resume any failed downloads.")
    resumed_query = resume_downloads(settings)
    input_file_list = remove_before_last_query(resumed_query,input_file_list)
    # Resume range operations
    resume_range_download(settings)
    # Show menu if option set
    if settings.show_menu:
        # Interactive mode.
        console_menu(settings,input_file_list)
    else:
        # Automatic batch mode.
        run_batch_mode(settings,input_file_list)
    logging.info("All tasks done, exiting.")
    if settings.hold_window_open:
        logging.info("Press enter to close window.")
        raw_input()
    return


if __name__ == "__main__":
    # Setup logging
    setup_logging(os.path.join("debug","derpibooru_dl_log.txt"))
    try:
        cj = cookielib.LWPCookieJar()
        setup_browser()
        main()
    except Exception, err:
        # Log exceptions
        logger.critical("Unhandled exception!")
        logger.critical(repr( type(err) ) )
        logging.exception(err)
    logging.info( "Program finished.")
