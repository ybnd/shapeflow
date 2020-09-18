# Check whether this url exists:
url = "$url/releases/download/$version/dist-$version.tar.gz"

from urllib.request import HTTPErrorProcessor, Request, build_opener


class FirstResponse(HTTPErrorProcessor):
    """Don't redirect, since that transforms HEAD into GET,
    which we don't need yet.

    This would be nicer with https://requests.readthedocs.io/en/master/
    but we don't want to introduce dependencies.
    """

    def http_response(self, request, response):
        return response

    def https_response(self, request, response):
        return response


request = Request(url, method='HEAD')
response = build_opener(FirstResponse).open(request)

# Resource should exist
if response.status != 302:
    raise ValueError(f"Resource {url} does not exist!")
