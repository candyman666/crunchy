links.py tests
=================

Tested successfully with Python 2.4, 2.5

links.py is a plugin whose main purpose is to rewrite urls in a form that
can be used by Crunchy.  
It has the following functions that require testing:

1. register(): registers some tag handlers.
2. external_link(): deal with links that point to external file meant to be 
unprocessed by Crunchy.
3. a_tag_handler(): 
4. link_tag_handler():
5. src_handler():
6. style_handler()
7. secure_url():

0. Setting things up
--------------------

See how_to.rst_ for details.

.. _how_to.rst: how_to.rst

    >>> from src.interface import plugin, Element, SubElement
    >>> plugin.clear()
    >>> import src.plugins.links as links
    >>> import src.tests.mocks as mocks
    >>> mocks.init()
    >>> page_default = mocks.Page()
    >>> page_default.is_from_root = True
    >>> page_remote = mocks.Page()
    >>> page_remote.is_remote = True
    >>> page_local = mocks.Page()
    >>> page_local.is_local = True


1. Testing register()
----------------------

    >>> links.register()
    >>> 
    >>> mocks.registered_tag_handler['a'][None][None] == links.a_tag_handler
    True
    >>> mocks.registered_tag_handler['a']['title']['external_link'] == links.external_link
    True
    >>> mocks.registered_tag_handler['img'][None][None] == links.src_handler
    True
    >>> mocks.registered_tag_handler['link'][None][None] == links.link_tag_handler
    True
    >>> mocks.registered_tag_handler['style'][None][None] == links.style_handler
    True


2. Testing external_link()
--------------------------

This function leaves an external link, of the form http://... unchanged,
except that it adds an image to help the user identify it.

    >>> fake_url_1 = "http://www.python.org"
    >>> a_link = Element('a', href=fake_url_1)
    >>> a_link.text = "Python"

We will first do a test with each page type, with a different number of
arguments for each.

    >>> links.external_link(page_default, a_link)
    >>> print a_link[0].tag, a_link[0].attrib['src']
    img /external_link.png
    >>> links.external_link(page_local, a_link, 'dummy1')
    >>> print a_link[0].tag, a_link[0].attrib['src']
    img /external_link.png
    >>> links.external_link(page_remote, a_link, 'dummy1', 'dummy2')
    >>> print a_link[0].tag, a_link[0].attrib['src']
    img /external_link.png

Next, we do an example with a more complicated link object, one that
has a subelement.

    >>> a_link = Element('a', href=fake_url_1)
    >>> a_link.text = " "
    >>> an_image = SubElement(a_link, 'img', src="logo.png", alt="Python")
    >>> a_link.tail = "official website"
    >>> links.external_link(page_default, a_link)
    >>> print a_link[0].tag, a_link[0].attrib['src']
    img logo.png
    >>> print a_link[1].tag, a_link[1].attrib['src']
    img /external_link.png

3. Testing a_tag_handler()
--------------------------

    >>> fake_url_2 = "http://docs.python.org/tut/tut.html#hash"

leave link start with / untouch 

    >>> a_link = Element('a', href="/path/to/")
    >>> links.a_tag_handler(page_default, a_link) 
    >>> a_link.attrib['href']
    '/path/to/'
    >>> links.a_tag_handler(page_local, a_link) 
    >>> a_link.attrib['href']
    '/path/to/'
    >>> links.a_tag_handler(page_remote, a_link) 
    >>> a_link.attrib['href']
    '/path/to/'

3a. Testing a_tag_handler for default page 
--------------------------
External link  

    >>> a_link = Element('a', href=fake_url_1)
    >>> links.a_tag_handler(page_default, a_link) 
    >>> a_link.attrib['href']
    '/remote?url=http%3A%2F%2Fwww.python.org'

Relative link , leave untouch (?)

    >>> a_link = Element('a', href="crunchy_tutor/welcome_en.html")
    >>> links.a_tag_handler(page_default, a_link) 
    >>> a_link.attrib['href']
    'crunchy_tutor/welcome_en.html'

3a. Testing a_tag_handler for local page
--------------------------
External link (with ://)

    >>> a_link = Element('a', href=fake_url_1)
    >>> links.a_tag_handler(page_local, a_link) 
    >>> a_link.attrib['href']
    '/remote?url=http%3A%2F%2Fwww.python.org'


Relative link 

    >>> a_link = Element('a', href="path/to/some_file.htm#hash")
    >>> links.a_tag_handler(page_local, a_link) 
    >>> a_link.attrib['href']
    '/local?url=path%2Fto%2Fsome_file.htm'
    >>> page_local.url = a_link.attrib['href']
    >>> a_link = Element('a', href="some_file.htm#hash")
    >>> links.a_tag_handler(page_local, a_link) 
    >>> a_link.attrib['href']
    '#hash'

Files with extesnion 'rst' and 'txt'

    >>> a_link = Element('a', href="path/to/some_rst.rst")
    >>> links.a_tag_handler(page_local, a_link) 
    >>> a_link.attrib['href']
    '/rst?url=//path%2Fto%2Fsome_rst.rst'
    >>> a_link = Element('a', href="path/to/some_txt.txt")
    >>> links.a_tag_handler(page_local, a_link) 
    >>> a_link.attrib['href']
    '/rst?url=//path%2Fto%2Fsome_txt.txt'

3c. Testing a_tag_handler for remote page
--------------------------

External link (with ://)

    >>> a_link = Element('a', href=fake_url_1)
    >>> links.a_tag_handler(page_remote, a_link) 
    >>> a_link.attrib['href']
    'http://www.python.org'

External link with hash 

    >>> a_link = Element('a', href=fake_url_2)
    >>> links.a_tag_handler(page_remote, a_link) 
    >>> a_link.attrib['href']
    'http://docs.python.org/tut/tut.html'

Relative link 

    >>> page_remote.url = ""
    >>> a_link = Element('a', href="path/to/some_file.htm")
    >>> links.a_tag_handler(page_remote, a_link) 
    >>> a_link.attrib['href']
    '/remote?url=path%2Fto%2Fsome_file.htm'
    >>> a_link = Element('a', href="path/to/some_file.htm#hash")
    >>> links.a_tag_handler(page_remote, a_link) 
    >>> a_link.attrib['href']
    '/remote?url=path%2Fto%2Fsome_file.htm'
    >>> page_remote.url = a_link.attrib['href']
    >>> a_link = Element('a', href="some_file.htm#hash")
    >>> links.a_tag_handler(page_remote, a_link) 
    >>> a_link.attrib['href']
    '#hash'

4. Testing link_tag_handler()
-----------------------------

For remote page , only relative path will be converted . 

    >>> link_ele = Element('link', href='http://python.org/path/to/some_file.css')
    >>> links.link_tag_handler(page_remote, link_ele) 
    >>> link_ele.attrib['href']
    'http://python.org/path/to/some_file.css'
    >>> page_remote.url = "http://python.org/"
    >>> link_ele = Element('link', href="path/to/some_file.css")
    >>> links.link_tag_handler(page_remote, link_ele) 
    >>> link_ele.attrib['href']
    'http://python.org/path/to/some_file.css'

For locale page, relative path will be coverted absoulte local path.
Note: link_tag_handler() may act differently among different OSs , as it use os.path.join. 
TODO:write this test.

5. Testing src_handler()
------------------------

It will work just the same as link element.

    >>> src_ele = Element('script', src='http://python.org/path/to/some_js.js')
    >>> links.src_handler(page_remote, src_ele) 
    >>> src_ele.attrib['src']
    'http://python.org/path/to/some_js.js'
    >>> page_remote.url = "http://python.org/"
    >>> src_ele = Element('script', src="path/to/some_js.js")
    >>> links.src_handler(page_remote, src_ele) 
    >>> src_ele.attrib['src']
    'http://python.org/path/to/some_js.js'

TODO: test local page

6. Testing style_handler()
------------------------

    >>> page_default.url = "/crunchy/"
    >>> css_import = Element('style')
    >>> css_import.text = '@import "some_file.css"'
    >>> links.style_handler(page_default, css_import)
    >>> css_import.text
    '@import "/crunchy/some_file.css"'

7. Testing secure_url()

    >>> safe_url = 'http://python.org/some/path/some_file.html'
    >>> links.secure_url(safe_url)
    'http://python.org/some/path/some_file.html'
    >>> un_safe_url = 'http://python.org/some/path/some_file.html?act=xxx'
    >>> links.secure_url(un_safe_url)
    'http://python.org/some/path/some_file.html'