from urllib.parse import urlparse
import sys
import os
from random import shuffle
from bs4 import BeautifulSoup

from apicall import APIWriter
from harParser import HarParser
from browser import Browser


class APIFinder:

    def __init__(self, url=None, har_directory=None, search_string=None, remove_params=False, count=1, cookies=None):
        self.url = url
        self.har_directory = har_directory
        self.search_string = search_string
        self.remove_params = remove_params
        self.count = count
        self.browser = None
        self.cookies = cookies

    def start(self):
        if self.count > 1 and self.url is None:
            print("Cannot provide page count with no URL given")
            exit(1)
        if self.remove_params and self.url is None:
            print("WARNING: Must have Internet connection to remove unneeded parameters")

        # Scan for all APIs
        if self.url:
            os.makedirs(self.har_directory, exist_ok=True)
            self.delete_existing_hars()
            self.browser = Browser("chromedriver/chromedriver",
                                   "browsermob-proxy-2.1.4/bin/browsermob-proxy",
                                   self.har_directory,
                                   cookies=self.cookies
                                   )
            if self.search_string is not None:
                print("Searching URL " + self.url + " for string " + self.search_string)
            # Move recursively through the site
            api_calls = self.crawling_scan(self.url)

        # Scan directory of har files
        else:
            print("Parsing existing directory of har files")
            har_parser = HarParser(self.har_directory, self.search_string, self.remove_params)
            api_calls = har_parser.parse_multiple_hars()

        if self.browser is not None:
            self.browser.close()

        return api_calls

    def open_url(self, url):
        return self.browser.get(url)  # load the url in Chrome

    @staticmethod
    def get_domain(url):
        return urlparse(url).netloc.lstrip('www.')

    def is_internal(self, url, base_url):
        if url.startswith("/"):
            return base_url + url
        if self.get_domain(base_url) == self.get_domain(url):
            return url
        return None

    '''
    @staticmethod
    def find_internal_urls_in_text(text, current_url, all_found_urls):
        regex = re.compile(
            r'(https?://[\w]+\.)(com|org|biz|net)((/[\w]+)+)(\.[a-z]{2,4})?(\?[\w]+=[\w]+)?((&[\w]+=[\w]+)+)?',
            re.ASCII
        )

        matches = re.finditer(regex, text)

        for match in matches:
            print(str(match.group()))
    '''

    # Returns a list of all internal URLs on a page as long
    # as they are either relative URLs or contain the current domain name
    def find_internal_urls(self, soup, current_url, all_found_urls):
        new_urls = []
        base_url = urlparse(current_url).scheme + "://" + urlparse(current_url).netloc
        # Finds all links that begin with a "/"
        for link in soup.findAll("a"):
            if 'href' in link.attrs:
                # baseUrl, urlInPage = parseUrl(link.attrs)
                url = link.attrs['href']
                # It's an internal URL and we haven't found it already
                url = self.is_internal(url, base_url)
                if url is not None and url not in new_urls and url not in all_found_urls:
                    new_urls.append(url)
                    all_found_urls.append(url)
        return all_found_urls, new_urls

    @staticmethod
    def get_content_type(headers):
        for header in headers:
            if header["name"] == "Content-Type":
                return header["value"]

    # Get rid of all the current har files
    def delete_existing_hars(self):
        files = os.listdir(self.har_directory)
        for singleFile in files:
            if "har" in singleFile:
                os.remove(self.har_directory + "/" + singleFile)

    # Performs a recursive crawl of a site, searching for APIs
    def crawling_scan(self, url, api_calls=None, all_found_urls=None):
        if api_calls is None:
            api_calls = []
        if all_found_urls is None:
            all_found_urls = []
        self.count = self.count - 1
        if self.count < 0:
            return

        har_parser = HarParser(self.har_directory, search_string=self.search_string, remove_params=self.remove_params)

        # If uncommented, will return as soon as a matching call is found
        # if self.search_string is not None and len(apiCalls) > 0:
        # 	return apiCalls
        try:
            print("Scanning URL: "+url)
            html = self.open_url(url)
            if html is not None:
                soup = BeautifulSoup(html, "lxml")

                har_obj = har_parser.get_single_har_file()
                api_calls = har_parser.scan_har_file(har_obj, api_calls=api_calls)

                all_found_urls, new_urls = self.find_internal_urls(soup, url, all_found_urls)
                shuffle(new_urls)

                for newUrl in new_urls:
                    self.crawling_scan(newUrl, api_calls, all_found_urls)

        except (KeyboardInterrupt, SystemExit):
            print("Stopping crawl")
            self.browser.close()
            api_writer = APIWriter(api_calls)
            api_writer.output_apis()
            sys.exit(1)
        return api_calls
