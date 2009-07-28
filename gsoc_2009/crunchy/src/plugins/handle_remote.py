"""Handle remote loading of tutorials.

Defines the /remote http request path.
Creates a form allowing to specify the URL of a tutorial to be loaded
by Crunchy.
"""

import sys
from StringIO import StringIO

# urllib reshuffled in Python 3 and 2to3 seems to skip this.
if sys.version_info[0] < 3:
    from urllib import unquote_plus
else:
    from urllib.parse import unquote_plus

# All plugins should import the crunchy plugin API via interface.py
from src.interface import plugin, preprocessor, config, SubElement
from src.utilities import unicode_urlopen

provides = set(["/remote"])

def register():  # tested
    '''registers http handler for dealing with remote files as well as
    handler for inserting widget for loading remote tutorials.'''
    plugin['register_http_handler']("/remote", remote_loader)
    # 'load_remote' only appears inside <span> elements, using the notation
    # <span title='load_remote'>
    plugin['register_tag_handler']("span", "title", "load_remote",
                                                    insert_load_remote)
    plugin['add_vlam_option']('power_browser', 'remote_html')
    plugin['register_service']("remote_html", insert_load_remote)

def remote_loader(request):  # tested
    '''
    create a vlam page from a request to get a remote file
    '''
    url = unquote_plus(request.args["url"])
    extension = url.split('.')[-1]
    username = request.crunchy_username
    if extension in preprocessor:
        # TODO: preprocessor don't forward Accept-Language HTTP headers
        page = plugin['create_vlam_page'](
                    preprocessor[extension](url, local=False), url,
                                                username=username, remote=True)
    else:
        accept_lang = None
        if config[username]["forward_accept_language"]:
            accept_lang = request.headers.get("Accept-Language")
        page = unicode_urlopen(url, accept_lang)
        page = plugin['create_vlam_page'](page, url,
                                          username=username,
                                          remote=True)
    request.send_response(200)
    request.send_header(u'Cache-Control',
                        u'no-cache, must-revalidate, no-store')
    request.end_headers()
    # write() in python 3.0 returns an int instead of None;
    # this interferes with unit tests
    dummy = request.wfile.write(page.read().encode('utf-8'))

def insert_load_remote(dummy_page, parent, dummy_uid): # tested
    '''inserts a form to load a remote page'''
    # in general, page and uid are used by similar plugins, but they are
    # redundant here.
    form = SubElement(parent, 'form',
                      name=u'url',
                      size=u'80',
                      method=u'get',
                      action=u'/remote')
    SubElement(form, 'input',
               name=u'url',
               size=u'80',
               value=parent.text)
    input2 = SubElement(form, 'input',
                        type=u'submit',
                        value=u'Load remote tutorial')
    input2.attrib['class'] = u'crunchy'
    parent.text = u' '
