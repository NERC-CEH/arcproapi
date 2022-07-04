"""http stuff"""
from contextlib import closing as _closing
import urllib as _urllib
import urllib.request as _urllib2
import json as _json
import http.client as _client

def request_http(url, data=None, data_type='text', headers=None):
    """Return result of an HTTP Request.

    Only GET and POST methods are supported. To issue a GET request, parameters
    must be encoded as part of the url and data must be None. To issue a POST
    request, parameters must be supplied as a dictionary for parameter data and
    the url must not include parameters.

    Parameters:
        url -- URL to issue the request to
    Optional:
        data -- dictionary of data to send
        data_type -- text(default)|xml|json|jsonp|pjson
            data is always obtained as text, but the this function
            can convert the text depending on the data_type parameter:
                text -- return the raw text as it is
                xml -- parse the text with xml.etree.ElementTree and return
                json -- parse the text with json.loads(text) and return
                jsonp,pjson -- parse the text with json.loads(text) and return
                    also, add parameter callback to the request
        header -- dictionary of headers to include in the request
    Example:
    >>> request('http://google.com')
    >>> u = 'http://sampleserver3.arcgisonline.com/ArcGIS/rest/services'
    >>> request(u,{'f':'json'}, 'json')
    >>> request('http://epsg.io/4326.xml', None, 'xml')
    """

    result = '' # noqa
    callback = 'callmeback'  # may not be used

    # prepare data
    data_type = str(data_type).lower()
    if data_type in ('jsonp', 'pjson'):
        if data is None:
            data = {}
        data['callback'] = callback

    if data is not None:
        data = _urllib.parse.urlparse(data) # noqa

    # make the request
    rq = _urllib2.Request(url, data, headers)
    re = _urllib2.urlopen(rq)
    rs = re.read()

    # handle result
    if data_type in ('json', 'jsonp', 'pjson'):
        rs = rs.strip()

        # strip callback function if present
        if rs.startswith(callback + '('):
            rs = rs.lstrip(callback + '(')
            rs = rs[:rs.rfind(')')]

        result = _json.loads(rs)
    elif data_type == 'xml':
        from xml.etree import ElementTree as ET # noqa
        rs = rs.strip()
        result = ET.fromstring(rs) # noqa
    elif data_type == 'text':
        result = rs
    else:
        raise Exception('Unsupported data_type %s ' % data_type)

    return result


def request_https(url, data=None, data_type="text", headers=None):
    """Return result of an HTTPS Request.
    Uses urllib.HTTPSConnection to issue the request.

    Only GET and POST methods are supported. To issue a GET request, parameters
    must be encoded as part of the url and data must be None. To issue a POST
    request, parameters must be supplied as a dictionary for parameter data and
    the url must not include parameters.

    Parameters:
        url -- URL to issue the request to
    Optional:
        data -- dictionary of data to send
        data_type -- text(default)|xml|json|jsonp|pjson
            data is always obtained as text, but the this function
            can convert the text depending on the data_type parameter:
                text -- return the raw text as it is
                xml -- parse the text with xml.etree.ElementTree and return
                json -- parse the text with json.loads(text) and return
                jsonp,pjson -- parse the text with json.loads(text) and return
                    also, add parameter callback to the request
        header -- dictionary of headers to include in the request
    Example:
    >>> request_https('https://gitgub.com')
    >>> u = 'https://sampleserver3.arcgisonline.com/ArcGIS/rest/services'
    >>> request_https(u,{'f':'json'}, 'json')
    """
    url = str(url)
    callback = ''  # may not be used

    # add the https protocol if not already specified
    if not url.lower().startswith("https://"):
        url = "https://" + url

    urlparsed = _urllib.parse.urlparse(url) # noqa
    hostname = urlparsed.hostname
    path = url[8 + len(hostname):]  # get path as url without https and host name

    # connect to the host and issue the request
    with _closing(_client.HTTPSConnection(hostname)) as cns:

        if data is None:

            if data_type == 'jsonp' or data_type == 'pjson':
                # TODO: Make sure callback parameter is included
                pass

            # use GET request, all parameters must be encoded as part of the url
            cns.request("GET", path, None, headers)

        else:

            if data_type == 'jsonp' or data_type == 'pjson':
                raise Exception("data_type 'jsonp' not allowed for POST method!")

            # use POST request, data must be a dictionary and not part of the url
            d = _urllib.parse.quote(data)  # noqa
            cns.request("POST", path, d, headers)

        r = cns.getresponse()
        s = r.read()
        cns.close()

    # convert to required format
    result = None
    if data_type is None or data_type == 'text':
        result = s
    elif data_type == 'json':
        result = _json.loads(s)
    elif data_type == 'jsonp' or data_type == 'pjson':
        result = _json.loads(s.lstrip(callback + "(").rstrip(")"))
    elif data_type == 'xml':
        from xml.etree import ElementTree as ET  # noqa
        rs = s.strip()
        result = ET.fromstring(rs)

    return result


def request(url, data=None, data_type='text', headers=None):
    """Return result of an HTTP or HTTPS Request.

    Uses urllib2.Request to issue HTTP request and the urllib.HTTPSConnection
    to issue https requests.
    Only GET and POST methods are supported. To issue a GET request, parameters
    must be encoded as part of the url and data must be None. To issue a POST
    request, parameters must be supplied as a dictionary for parameter data and
    the url must not include parameters.

    ***Security warning***
    If url does not contain the protocol (http:// or https://) but just //,
    this function will first try https request, but if that fails, http request
    will be issued. For security reasons, protocol should be always specified,
    otherwise sensitive data inteded for encrypted connection (https) may be
    send to an unencripted connection. For example, consider you use the // to
    request a https url and you need to include secret token in the header.
    If the request fails, this function will attept to issue another request
    over http and will include the secret token with the http request, which can
    then be intercepted by malicious Internet users!

    Parameters:
        url -- URL to issue the request to
    Optional:
        data -- dictionary of data to send
        data_type -- text(default)|xml|json|jsonp|pjson
            data is always obtained as text, but the this function
            can convert the text depending on the data_type parameter:
                text -- return the raw text as it is
                xml -- parse the text with xml.etree.ElementTree and return
                json -- parse the text with json.loads(text) and return
                jsonp,pjson -- parse the text with json.loads(text) and return
                    also, add parameter callback to the request
        headers -- dictionary of headers to include in the request
    Example:
    >>> request('http://google.com')
    >>> u = 'http://sampleserver3.arcgisonline.com/ArcGIS/rest/services'
    >>> request(u,{'f':'json'}, 'json')
    >>> request('http://epsg.io/4326.xml', None, 'xml')
    >>> request('https://gitgub.com')
    """
    url = str(url)
    urll = url.lower()
    if urll.startswith("http://"):
        result = request_http(url, data, data_type, headers)
    elif urll.startswith("https://"):
        result = request_https(url, data, data_type, headers)
    elif url.startswith("//"):
        # try https first, then http
        try:
            result = request_https("https://" + url, data, data_type, headers)
        except:
            result = request_http("http://" + url, data, data_type, headers)
    else:
        raise Exception("Protocol can only be http or https!")

    return result
