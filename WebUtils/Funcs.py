"""WebUtils.Funcs

This module provides some basic functions that are useful
in HTML and web development.

You can safely import * from WebUtils.Funcs if you like.

TO DO

* Document the 'codes' arg of htmlEncode/Decode.

"""


htmlForNone = '-' # used by htmlEncode

htmlCodes = (
    ('&', '&amp;'),
    ('<', '&lt;'),
    ('>', '&gt;'),
    ('"', '&quot;'),
    # ['\n', '<br>'],
)

htmlCodesReversed = tuple(reversed(htmlCodes))


def htmlEncode(what, codes=htmlCodes):
    if what is None:
        return htmlForNone
    if hasattr(what, 'html'):
        # allow objects to specify their own translation to html
        # via a method, property or attribute
        ht = what.html
        if callable(ht):
            ht = ht()
        return ht
    what = str(what)
    return htmlEncodeStr(what, codes)


def htmlEncodeStr(s, codes=htmlCodes):
    """Return the HTML encoded version of the given string.

    This is useful to display a plain ASCII text string on a web page.

    """
    for code in codes:
        s = s.replace(code[0], code[1])
    return s


def htmlDecode(s, codes=htmlCodesReversed):
    """Return the ASCII decoded version of the given HTML string.

    This does NOT remove normal HTML tags like <p>.
    It is the inverse of htmlEncode().

    """
    for code in codes:
        s = s.replace(code[1], code[0])
    return s


# Aliases for URL encoding and decoding functions:
from urllib import quote_plus as urlEncode, unquote_plus as urlDecode


def htmlForDict(d, addSpace=None, filterValueCallBack=None,
        maxValueLength=None, topHeading=None, isEncoded=None):
    """Return an HTML string with a table where each row is a key-value pair."""
    if not d:
        return ''
    keys = d.keys()
    keys.sort()
    # A really great (er, bad) example of hardcoding.  :-)
    html = ['<table class="NiceTable">\n']
    if topHeading:
        html.append('<tr class="TopHeading"><th')
        html.append((type(topHeading) is type(())
            and '>%s</th><th>%s' or ' colspan="2">%s') % topHeading)
        html.append('</th></tr>\n')
    for key in keys:
        value = d[key]
        if addSpace and addSpace.has_key(key):
            target = addSpace[key]
            value = (target + ' ').join(value.split(target))
        if filterValueCallBack:
            value = filterValueCallBack(value, key, d)
        if maxValueLength and not isEncoded:
            value = str(value)
            if len(value) > maxValueLength:
                value = value[:maxValueLength] + '...'
        key = htmlEncode(key)
        if not isEncoded:
            value = htmlEncode(value)
        html.append('<tr><th align="left">%s</th><td>%s</td></tr>\n'
            % (key, value))
    html.append('</table>')
    return ''.join(html)


def requestURI(env):
    """Return the request URI for a given CGI-style dictionary.

    Uses REQUEST_URI if available, otherwise constructs and returns it
    from SCRIPT_URL, SCRIPT_NAME, PATH_INFO and QUERY_STRING.

    """
    uri = env.get('REQUEST_URI', None)
    if uri is None:
        uri = env.get('SCRIPT_URL', None)
        if uri is None:
            uri = env.get('SCRIPT_NAME', '') + env.get('PATH_INFO', '')
        query = env.get('QUERY_STRING', '')
        if query != '':
            uri += '?' + query
    return uri


def normURL(path):
    """Normalizes a URL path, like os.path.normpath.

    Acts on a URL independant of operating system environment.

    """
    if not path:
        return
    initialslash = path[0] == '/'
    lastslash = path[-1] == '/'
    comps = path.split('/')
    newcomps = []
    for comp in comps:
        if comp in ('', '.'):
            continue
        if comp != '..':
            newcomps.append(comp)
        elif newcomps:
            newcomps.pop()
    path = '/'.join(newcomps)
    if path and lastslash:
        path += '/'
    if initialslash:
        path = '/' + path
    return path
