import os
import codecs
import json 
from urllib.parse import urlparse, parse_qs
from apicall import APICall


class HarParser:

    def __init__(self, har_path, search_string=None, remove_params=False):
        self.har_path = har_path
        self.search_string = search_string
        self.content_types_recorded = ["text/html", "application/json", "application/xml"]
        self.remove_params = remove_params

    def get_all_har_files(self):
        files = os.listdir(self.har_path)
        har_files = []
        for filename in files:
            if "har" in filename:
                har_files.append(self.har_path + "/" + filename)
        return har_files

    @staticmethod
    def read_har_file(har_path):
        f = codecs.open(har_path, "rb")
        har_txt = f.read().decode("utf-8", "replace")
        har_obj = json.loads(har_txt)
        return har_obj

    def get_single_har_file(self):
        # f = open("nextexport/"+files[0], 'rb')
        har_files = self.get_all_har_files()
        if len(har_files) < 1:
            return None
        # Get last harFile in the directory
        har_file = self.get_all_har_files()[-1]
        return self.read_har_file(har_file)

    def parse_entry(self, entry):
        url = entry["request"]["url"]
        method = entry["request"]["method"]
        params = dict()
        url_obj = urlparse(url)
        base = url_obj.scheme+"://"+url_obj.netloc
        mime_type = None

        response = entry.get('response', {})
        content = response.get('content', {})

        if "mimeType" in content and "text" in content:
            text = entry["response"]["content"]["text"]
            context = None
            if self.search_string is not None:
                if self.search_string not in text:
                    return None
                # Set the search string, with some surrounding context in the apiCall
                start = entry["response"]["content"]["text"].index(self.search_string)
                end = start + len(self.search_string) + 50
                start = 0 if start < 50 else start-50
                context = text[start:end]

            content_type = entry["response"]["content"]["mimeType"]
            response_size = entry["response"]["content"]["size"]

            content = text
            if content_type is None:
                return None
            elif content_type.lower() in self.content_types_recorded:
                mime_type = content_type.lower()
            elif content_type.lower() == "application/gzip":
                print("GZIP ENTRY:\n"+entry)
            else:
                return None

            if method == "GET":
                params = parse_qs(url_obj.query, keep_blank_values=True)
            elif method == "POST":
                if "params" in entry["request"]["postData"]:
                    param_list = entry["request"]["postData"]["params"]
                    for param in param_list:
                        if param['name'] not in params:
                            params[param['name']] = []
                        params[param['name']].append(param['value'])
                elif "text" in entry["request"]["postData"]:
                    param_list = entry["request"]["postData"]["text"]
                    # The code above does not translate to Params in the APICall below, this path passes empty dict

            api_call = APICall(
                url,
                base,
                url_obj.path,
                mime_type,
                method,
                params,
                response_size,
                content,
                search_context=context
            )
            return api_call

    def scan_har_file(self, har_obj, api_calls=None):
        if api_calls is None:
            api_calls = []
        # Store the api call objects here
        entries = har_obj["log"]["entries"]
        for entry in entries:
            call = self.parse_entry(entry)
            if call is not None:
                call.add_to_list(api_calls, remove_unneeded_params=self.remove_params)
        return api_calls

    def parse_multiple_hars(self):
        api_calls = []
        har_paths = self.get_all_har_files()
        for harPath in har_paths:
            print("Parsing file: "+harPath)
            har_obj = self.read_har_file(harPath)
            api_calls = self.scan_har_file(har_obj, api_calls=api_calls)
        return api_calls
