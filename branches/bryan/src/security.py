'''
security.py

Javascript code is normally executed in a web-browser "sandbox", preventing
access to the user's computer.  Crunchy creates a link between the browser and
a Python backend, enabling the user to execute code on his computer (with full
access to the resources), thereby bypassing the security sandbox of the browser.

This creates a potential security hole.

The purpose of this module is to prevents the automatic execution of Python code
caused by insertion of malicious javascript code within a web page.
'''

# Note: a 2nd layer of security is implemented through a random session
# id generated in CrunchyPlugin.py
import imp
import os

import urllib
import urlparse
import sys

# Third party modules - included in crunchy distribution
from element_tree import ElementTree

import configuration

DEBUG = True
DEBUG2 = False

# Better safe than sorry: we do not allow the following html tags for the
# following reasons:
# script: because we want to prevent unauthorised code execution
# button, form, input, textarea: we only want Crunchy itself to create those
# *frame*: we don't want hidden frames that could be playing tricks with the
#          user (very remote possibility, but still.)
# embed: as the name indicates, can be used to embed some unwanted objects.
#
#
#  It may be worthwhile to check http://ha.ckers.org/xss.html from time to
# time to find out about possible other security issues.
#


# The following is not used currently
#attribute_black_list = ["text/javascript"]


# Rather than trying to find which attributes might be problematic (black list),
# we create a database of allowed (safe) attributes which we know will not cause
# any trouble.  This list can always be expanded if required.
# Note that a black list would have included onblur, onload, oninit, etc.,
# with possibly some new attributes introduced by a given browser which we
# would not have foreseen.

# To save on typing, we list here the common attributes
# that almost all html tags can make use of in a sensible way:
common_allowed = ['class', 'dir', 'id', 'lang', 'title']
# note that we left out "style" which will be handled separately

# index {1} below: see also http://feedparser.org/docs/html-sanitization.html
specific_allowed = {
    'a': ['charset', 'type', 'name', 'href', 'hreflang', 'rel'],
    'abbr': [],
    'acronym': [],
    'address': [],
    # applet deprecated
    'area': ['name', 'shape', 'coords', 'href', 'alt', 'nohref'],
    'b': [],
    #'basefont': [], # not allowed in {1}
    #'base': [],  # not allowed in {1}
    'bdo': [],  # keep, even if not allowed in {1}
    'big': [],
    'blockquote': ['cite'],
    'body': ['bgcolor'],
    'br' : ['clear'],
    # button not allowed  - should be no reason
    'canvas': [],
    'caption': ['align'],
    'center': [],
    'cite': [],
    'code': [],
    'col': ['span', 'width'],
    'colgroup': ['span', 'width'],
    'dd': [],
    'del': ['cite', 'datetime'],
    'dfn': [],
    'dir': [],  #  deprecated but allowed
    'div': ['align'],
    'dl': [],
    'dt': [],
    'em': [],
    'fieldset': ['align'],
    'font': ['size', 'color', 'face'], # deprecated... but still often used!
    # form not allowed; if required, will be inserted by Crunchy itself
    # frame not allowed (don't want stuff possibly hidden)
    # frameset not allowed
    'h1': ['align'],
    'h2': ['align'],
    'h3': ['align'],
    'h4': ['align'],
    'h5': ['align'],
    'h6': ['align'],
    'head': [],
    'hr': ['align', 'noshade', 'size', 'width'], # these attributes are deprecated!
    'html': [],
    'i': [],
    # iframe not allowed
    'img': ['src', 'alt', 'longdesc', 'name', 'height', 'width',
            'usemap', 'ismap', 'border'],
    # input not allowed
    'ins': ['cite', 'datetime'],
    # isindex deprecated
    'kbd': [],
    'label': ['for'],
    'legend': ['align'],
    'li': ['value'], # value is deprecated... but replaced by what?
    'link': ['charset', 'href', 'hreflang', 'type', 'rel', 'rev', 'media'],
    'map': ['shape', 'coords', 'href', 'nohref', 'alt'],
    'menu': [], # deprecated
    'meta': ['name', 'content'], #  'http-equiv' can be a potential problem
    'noframes': [],   # should not be needed
    'noscript' : [],   # should not be needed
    # object not allowed - preventing unwanted interactions
    'ol': ['start'],  # start is deprecated ... but replaced by ??
    #'optgroup': ['name', 'size', 'multiple'],  # Keep???
    #'option': ['name', 'size', 'multiple'],    # Keep???
    'p': [],
    # param not needed: only for object
    'pre': [],
    'q': ['cite'],
    's': [],  # deprecated but harmless
    'samp': [],
    # script not allowed!
    # 'select': ['name', 'size', 'multiple'], # Keep???
    'small': [],
    'span': ['align'],
    'strike': [], # deprecated
    'strong': [],
    'style': ['type', 'media'],
    'sub': [],
    'sup': [],
    'table': ['summary', 'align', 'width', 'bgcolor', 'frame', 'rules',
                'border', 'cellspacing', 'cellpadding'],
    'tbody': ['align', 'char', 'charoff', 'valign'],
    'td': ['abbr', 'axis', 'headers', 'scope', 'rowspan', 'colspan', 'bgcolor',
            'align', 'char', 'charoff', 'valign'],
    # textarea not needed; only included by Crunchy
    'tfoot': ['align', 'char', 'charoff', 'valign'],
    'th': ['abbr', 'axis', 'headers', 'scope', 'rowspan', 'colspan', 'bgcolor',
            'align', 'char', 'charoff', 'valign'],
    'thead': ['align', 'char', 'charoff', 'valign'],
    'title': ['abbr', 'axis', 'headers', 'scope', 'rowspan', 'colspan', 'bgcolor',
            'align', 'char', 'charoff', 'valign'],
    'tr': [],
    'tt': [],
    'u': [], # deprecated ... but still used
    'ul': [],
    'var': []
    }

# We now build lists of allowed combinations tag/attributes based
# on the security level; we build separate dict since it needs
# to be done only once and is easier to modify individually while
# making sure we avoid accidental shared references.

allowed_attributes = {}

#- severe -
severe = {}
for key in specific_allowed:
    if key != 'link' and key != 'style' and key != 'meta':
        severe[key] = []
        for item in specific_allowed[key]:
            severe[key].append(item)
        for item in common_allowed:
            severe[key].append(item)

allowed_attributes['severe'] = severe
allowed_attributes['display severe'] = severe


# - normal
normal = {}
for key in specific_allowed:
    if key != 'meta':  # until we secure the menu plugin, exclude it.
        normal[key] = []
        for item in specific_allowed[key]:
            normal[key].append(item)
        for item in common_allowed:
            normal[key].append(item)
        normal[key].append('style')

allowed_attributes['normal'] = normal
allowed_attributes['display normal'] = normal


# - trusted
trusted = {}
for key in specific_allowed:
    trusted[key] = []
    for item in specific_allowed[key]:
        trusted[key].append(item)
    for item in common_allowed:
        trusted[key].append(item)
    trusted[key].append('style')

allowed_attributes['trusted'] = trusted
allowed_attributes['display trusted'] = trusted

# - paranoid -
paranoid = {}
for key in specific_allowed:
    if key != 'style' and key!= 'meta' and key != 'link':
        paranoid[key] = ['title']  # only harmless vlam-specific attribute

paranoid['a'] = ['href', 'id'] # only items required for navigation

allowed_attributes['paranoid'] = paranoid
allowed_attributes['display paranoid'] = paranoid


# Just like XSS vulnerability are possible through <style> or 'style' attrib
# -moz-binding:url(" http://ha.ckers.org/xssmoz.xml#xss")
# [see: http://ha.ckers.org/xss.html for reference], the same holes
# could be used to inject javascript code into Crunchy processed pages.
#
# In addition, one common technique is to encode character into html
# entities to bypass normal filters.  In addition to ha.ckers.org,
# see also for example http://feedparser.org/docs/html-sanitization.html
#
# As a result, we will not allowed dangerous "substring" to appear
# in style attributes or in style sheets in "normal" security level;
# styles are not permitted in "severe" or "paranoid".

dangerous_strings = ['url(', '&#']

__dangerous_text = ''

# default trusted sites are specified here
site_access = {'trusted':[],'normal':[],'severe':[],'paranoid':[]}
site_access['trusted'] = ["127.0.0.1", "docs.python.org", "python.org"]

# update security setting for a specific domain
def set_page_security(request):
    if request.data == "":
        return

    # prevent duplicates of any domain name
    for access in site_access.keys():
        while site_access[access].count(request.data) > 0:
            site_access[access].remove(request.data)

    site_access[request.args['level']].append(request.data)

    # save settings
    sites = open("sites.txt", 'w')
    sites.write(repr(site_access))
    sites.close()

def get_page_security(url):
    # local pages do not have a domain
    # setting all local pages to trusted may invalidate the security test
    #if url[0] == "/":
    #    return 'trusted'

    if not url[0:7] in ['http://','file://']:
        return configuration.defaults.security

    # parse hostname
    lastIndex = url.find("/",7)
    if lastIndex == -1:
        lastIndex = len(url)
    hostname = url[7:lastIndex].rstrip("#")

    for access in site_access.keys():
        if hostname in site_access[access]:
            return access

    return configuration.defaults.security

def remove_unwanted(tree, page):
    '''Removes unwanted tags and or attributes from a "tree" created by
    ElementTree from an html page.'''
    global __dangerous_text

    access = get_page_security(page.url)
    if DEBUG:
        print "Removing tags based on " + access + " access for " + page.url

    _allowed = allowed_attributes[access]
    #The following will be updated so as to add result from page.
    page.security_info = { 'level': access,
                          'number removed': 0,
                          'tags removed' : [],
                          'attributes removed': [],
                          'styles removed': []
                        }

# first, removing unwanted tags
    unwanted = set()
    tag_count = {}
    page.security_info['number removed'] = 0
    for element in tree.getiterator():
        if element.tag not in _allowed:
            unwanted.add(element.tag)
            if element.tag in tag_count:
                tag_count[element.tag] += 1
            else:
                tag_count[element.tag] = 1
            page.security_info['number removed'] += 1
    for tag in unwanted:
        for element in tree.getiterator(tag):
            element.clear() # removes the text
            element.tag = None  # set up so that cleanup will remove it.
        page.security_info['tags removed'].append([tag, tag_count[tag]])
    if DEBUG:
        print "These unwanted tags have been removed:"
        print unwanted


# next, removing unwanted attributes of allowed tags
    unwanted = set()
    count = 0
    for tag in _allowed:
        for element in tree.getiterator(tag):
# Filtering for possible dangerous content in "styles..."
            if tag == "link":
                if not 'trusted' in configuration.defaults.security: # default is True
                    if not is_link_safe(element, page):
                        page.security_info['styles removed'].append(
                                                [tag, '', __dangerous_text])
                        __dangerous_text = ''
                        element.clear()
                        element.tag = None
                        page.security_info['number removed'] += 1
                        continue
            for attr in element.attrib.items():
                if attr[0].lower() not in _allowed[tag]:
                    if DEBUG:
                        unwanted.add(attr[0])
                    page.security_info['attributes removed'].append(
                                                [tag, attr[0], ''])
                    del element.attrib[attr[0]]
                    page.security_info['number removed'] += 1
                elif attr[0].lower() == 'href':
                    testHREF = urllib.unquote_plus(attr[1]).replace("\r","").replace("\n","")
                    testHREF = testHREF.replace("\t","").lstrip().lower()
                    if testHREF.startswith("javascript:"):
                        if DEBUG:
                            print "removing href = ", testHREF
                        page.security_info['attributes removed'].append(
                                                [tag, attr[0], attr[1]])
                        del element.attrib[attr[0]]
                        page.security_info['number removed'] += 1
# Filtering for possible dangerous content in "styles..."
                elif attr[0].lower() == 'style':
                    if not 'trusted' in configuration.defaults.security: # default is True
                        value = attr[1].lower().replace(' ', '').replace('\t', '')
                        for x in dangerous_strings:
                            if x in value:
                                if DEBUG:
                                    unwanted.add(value)
                                page.security_info['styles removed'].append(
                                                [tag, attr[0], attr[1]])
                                del element.attrib[attr[0]]
                                page.security_info['number removed'] += 1
# Filtering for possible dangerous content in "styles..."
            if tag == 'style':
                if not 'trusted' in configuration.defaults.security: # default is True
                    text = element.text.lower().replace(' ', '').replace('\t', '')
                    for x in dangerous_strings:
                        if x in text:
                            if DEBUG:
                                unwanted.add(text)
                            page.security_info['styles removed'].append(
                                                [tag, '', element.text])
                            element.clear()
                            element.tag = None
                            page.security_info['number removed'] += 1
    __cleanup(tree.getroot(), lambda e: e.tag)
    if DEBUG:
        print "These unwanted attributes have been removed:"
        print unwanted
    return tree

def __cleanup(elem, filter):
    ''' See http://effbot.org/zone/element-bits-and-pieces.htm'''
    out = []
    for e in elem:
        __cleanup(e, filter)
        if not filter(e):
            if e.text:
                if out:
                    out[-1].tail += e.text
                else:
                    elem.text += e.text
            out.extend(e)
            if e.tail:
                if out:
                    out[-1].tail += e.tail
                else:
                    elem.text += e.tail
        else:
            out.append(e)
    elem[:] = out
    return

def is_link_safe(elem, page):
    '''only keep <link> referring to style sheets that are deemed to
       be safe'''
    global __dangerous_text
    url = page.url
    if DEBUG:
        print "found link element; page url = ", url
    #--  Only allow style files
    if "type" in elem.attrib:
        type = elem.attrib["type"]
        if DEBUG2:
            print "type = ", type
        if type.lower() != "text/css":  # not a style sheet - eliminate
            __dangerous_text = 'type != "text/css"'
            return False
    else:
        if DEBUG2:
            print "type not found."
        __dangerous_text = 'type not found'
        return False
    #--
    if "rel" in elem.attrib:
        rel = elem.attrib["rel"]
        if DEBUG2:
            print "rel = ", rel
        if rel.lower() != "stylesheet":  # not a style sheet - eliminate
            __dangerous_text = 'rel != "stylesheet"'
            return False
    else:
        if DEBUG2:
            print "rel not found."
        __dangerous_text = 'rel not found'
        return False
    #--
    if "href" in elem.attrib:
        href = elem.attrib["href"]
        if DEBUG2:
            print "href = ", href
    else:         # no link to a style sheet: not a style sheet!
        if DEBUG2:
            print "href not found."
        __dangerous_text = 'href not found'
        return False
    #--If we reach this point we have in principle a valid style sheet.
    link_url = find_url(url, href)
    if DEBUG2:
        print "link url = ", link_url
    #--Scan for suspicious content
    suspicious = False
    if page.is_local:
        css_file = open_local_file(link_url)
        if not css_file:  # could not open the file
            return False
        suspicious = scan_for_unwanted(css_file)
    elif page.is_remote:
        css_file = open_local_file(link_url)
        if not css_file:  # could not open the file
            return False
        suspicious = scan_for_unwanted(css_file)
    else:  # local page loaded via normal link.
        css_file = open_local_file(link_url)
        if not css_file:  # could not open the file
            return False
        suspicious = scan_for_unwanted(css_file)

    if not suspicious:
        if DEBUG:
            print "No suspicious content found in css file"
        return True
    elif DEBUG:
        print "suspicious content found in css file"
        return False

    if DEBUG:
        print "should not be reached"
    return False  # don't take any chances

# the root of the server is in a separate directory:
root_path = os.path.join(os.path.dirname(imp.find_module("crunchy")[1]), "server_root/")

def find_url(url, href):
    '''given the url of a "parent" html page and the href of a "child"
       (specified in a link element), returns
       the complete url of the child.'''
    if "://" in url:
        if DEBUG2:
            print ":// found in url"
        return urlparse.urljoin(url, href)
    elif "://" in href:
        if DEBUG2:
            print ":// found in href"
        return href
    elif href.startswith("/"):   # local css file from the root server
        return os.path.normpath(os.path.join(root_path, os.path.normpath(href[1:])))
    else:
        base, fname = os.path.split(url)
        if DEBUG2:
            print "base path =", base
            print "root_path =", root_path
        href = os.path.normpath(os.path.join(base, os.path.normpath(href)))
        if href.startswith(root_path):
            if DEBUG2:
                print "href starts with rootpath"
                print "href =", href
            return href
        if DEBUG2:
            print "href does not start with rootpath"
            print "href =", href
        return os.path.normpath(os.path.join(root_path, href[1:]))

def open_local_file(url):
    if DEBUG:
        print "attempting to open file: ", url
    if url.startswith("http://"):
        try:
            return urllib.urlopen(url)
        except:
            if DEBUG:
                print "Cannot open remote file with url=", url
            return False
    try:
        return open(url, mode="r")
    except IOError:
        if DEBUG2:
            print "opening the file without encoding did not work."
        try:
            return open(url.encode(sys.getfilesystemencoding()),
                        mode="r")
        except IOError:
            if DEBUG:
                print "Cannot open local file with url=", url
            return False

def scan_for_unwanted(css_file):
    '''Looks for any suspicious code in a css file

    For now, any file with "url(", "&#" and other "dangerous substrings
    in it is deemed suspicious  and will be rejected.

    returns True if suspicious code is found.'''
    global __dangerous_text

    for line in css_file.readlines():
        squished = line.replace(' ', '').replace('\t', '')
        for x in dangerous_strings:
            if x in squished:
                if DEBUG:
                    print "found suspicious content in the following line:"
                    print squished
                __dangerous_text = squished
                return True
    return False




