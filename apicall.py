from statistics import mean
import requests
import json
import html
import codecs


class APICall:

    def __init__(self, original_url, base, path, encoding_type, method, params, size, content, search_context=None):
        self.original_url = original_url
        self.base = base.rstrip("/")
        self.path = path.rstrip("/")
        self.encoding_type = encoding_type
        self.method = method
        # Dictionary of key, [list of values] pairs
        self.params = params
        self.path_params = set()
        size = int(size)
        if size is not None and size > 0:
            self.return_sizes = [size]
        else:
            self.return_sizes = []
        self.unneeded_keys = []
        self.content = content
        self.search_context = search_context

    def __json__(self):
        json_dict = {
            "original": self.original_url,
            "base": self.base,
            "path": self.path,
            "encodingType": self.encoding_type,
            "method": self.method,
            "params": self.params,
            "pathParams": list(self.path_params),
            "responseSizes": 0 if len(self.return_sizes) == 0 else int(mean(self.return_sizes)),
            "content": self.content
        }
        return json_dict

    def to_html(self):
        html_val = "<div class=\"apicall " + self.encoding_type.split("/")[1] + "\">"
        html_val += "<b>URL:</b>"+self.base+self.path
        html_val += "<br><b>METHOD:</b> "+self.method
        if len(self.params) > 0:
            html_val += "<table><tr><td><b>Key</b></td><td><b>Value(s)</b></td></tr>"
            for key, vals in self.params.items():
                html_val += "<tr><td>"+key+"</td>"
                html_val += "<td>"+str(vals)+"</td></tr>"
            html_val += "</table><p>"
        html_val += "<br><b>Example:</b> <a href=\"" + self.original_url + "\ target=\"_blank\">"
        html_val += self.original_url + "</a></br>"
        html_val += "<textarea class=\"content\">"
        html_val += html.escape(self.content, quote=True)
        html_val += "</textarea></div>"
        return html_val

    def remove_unneeded_parameters(self):
        # params is a dict of [string:string], not [string:list<string>]
        # need to convert
        params = dict()
        for key, value in self.params.items():
            params[key] = value[0]
        str(self.base)+str(self.path)
        # get baseline
        baseline = requests.get(str(self.base)+str(self.path), params=params).text
        for key in params.keys():
            new_params = dict(params)
            del new_params[key]
            test_text = requests.get(str(self.base)+str(self.path), params=new_params).text
            if test_text == baseline:
                self.unneeded_keys.append(key)
                del self.params[key]

    # Adds the API call to the list if it does not exist yet. If the call does
    # exist in the list, integrates any new parameters found
    def add_to_list(self, api_calls, remove_unneeded_params=False):
        for call in api_calls:
            if self.path == call.path and self.base == call.base:
                call.return_sizes = call.return_sizes + self.return_sizes
                for unneeded_key in call.unneeded_keys:
                    # Remove all the unneeded keys we've found in the parent already
                    if unneeded_key in self.params:
                        del self.params[unneeded_key]

                if remove_unneeded_params:
                    self.remove_unneeded_parameters()

                # The calls are the same, make sure to add all the params together
                for key, vals in self.params.items():
                    if key not in call.params:
                        call.params[key] = vals
                    else:
                        # Add all the values together
                        call.params[key] = list(set(call.params[key] + self.params[key]))
                return api_calls
        # Has not been found in the current list, simply append it
        if remove_unneeded_params:
            self.remove_unneeded_parameters()
        api_calls.append(self)
        return api_calls

    def to_string(self):
        cell_size = 40
        print("\n" + cell_size * "-")
        if self.path_params:
            print("URL: " + str(self.base) + str(self.path) + "/\nPATH PARAMS: " + ",".join(self.path_params))
        else:
            print("URL: "+str(self.base)+str(self.path))
        print("METHOD: "+self.method)
        if len(self.return_sizes) > 0:
            print("AVG RESPONSE SIZE: " + str(int(mean(self.return_sizes))))
        if self.search_context:
            print("SEARCH TERM CONTEXT: " + self.search_context + "\n")
        if self.params:
            print("|  KEY" + " " * (cell_size - 5) + "|  VALUE(S)" + " " * (cell_size - 10) + "|")
            for key, vals in self.params.items():
                key_space = cell_size - len(key)
                if vals[0] == "":
                    print("|" + key + " " * key_space + "|(blank)        |")
                else:
                    val_str = ""
                    for value in vals:
                        val_str = value + ","
                    # Remove final comma
                    val_str = val_str[:-1]
                    val_length = len(val_str)
                    while val_length > cell_size:
                        print("|" + " " * cell_size + "|" + val_str[:cell_size] + "|")
                        val_str = val_str[cell_size:]
                        val_length = len(val_str)
                    val_space = cell_size - val_length
                    print("|" + key + " " * key_space + "|" + val_str + " " * val_space + "|")
                print("--" + "--" * cell_size + "-")


class APICallEncoder(json.JSONEncoder):
    def default(self, obj):
        if hasattr(obj, '__json__'):
            return obj.__json__()
        return json.JSONEncoder.default(self, obj)


class APIWriter:
    def __init__(self, api_calls):
        self.api_calls = api_calls
        self.api_calls = self.find_path_variables()

    def output_apis(self):
        print("API RESULTS ARE")
        json_file = open("output.json", "w")
        for apiResult in self.api_calls:
            print(apiResult.to_string())
        self.output_html()
        json_file.write(self.output_json())
        return

    def output_json(self):
        return json.dumps(self.api_calls, cls=APICallEncoder)

    def output_html(self):
        f = codecs.open("html_template.html", "r")
        template = f.read()
        template_parts = template.split("CALLSGOHERE")
        open('output.html', 'w').close()
        html_file = open('output.html', 'a')
        html_file.write(template_parts[0])
        for api_call in self.api_calls:
            html_file.write(api_call.to_html())
        html_file.write(template_parts[1])
        html_file.close()

    @staticmethod
    def is_path_var(var):
        if '.' in var:
            return False
        num_digs = sum(c.isdigit() for c in var)
        if float(num_digs) / float(len(var)) > .5:
            return True
        return False

    def find_path_variables(self):
        """
        Experimental feature to identify variables in paths and group similar API calls
        """
        # digits = re.compile('\d')
        for i in range(0, len(self.api_calls)):
            for j in range(i+1, len(self.api_calls)):
                paths1 = self.api_calls[i].path.split('/')
                paths2 = self.api_calls[j].path.split('/')
                if len(paths1) == len(paths2) and len(paths1) > 3:
                    if paths1[:-1] == paths2[:-1]:
                        print("Paths match to the last item:")
                        paths_1_end = paths1[len(paths1) - 1]
                        paths_2_end = paths2[len(paths2) - 1]
                        if self.is_path_var(paths_1_end) and self.is_path_var(paths_2_end):
                            # We can assume that they're the same API
                            print("APIs are the same")
                            self.api_calls[i].pathParams.add(paths_1_end)
                            self.api_calls[i].pathParams.add(paths_2_end)
                            self.api_calls[j].path = ''

        return [api for api in self.api_calls if api.path != '']
