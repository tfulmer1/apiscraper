from flask import Flask
from flask import request
from apiFinder import APIFinder
from apicall import APIWriter
app = Flask(__name__)


@app.route("/search")
def search():
    # (self, url=None, harDirectory=None, search_string=None, remove_params=False, count=1)
    search_str = request.args.get('search')
    url_str = request.args.get('url')
    finder = APIFinder(url=url_str, search_string=search_str)
    api_calls = finder.start()
    writer = APIWriter(api_calls)
    return writer.output_json()


@app.route("/crawl")
def crawl():
    return "Hello World!"


if __name__ == "__main__":
    app.run()
