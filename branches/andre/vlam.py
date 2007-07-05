"""
perform vlam substitution

sets up the page and calls appropriate plugins
"""

from StringIO import StringIO

import security

# Third party modules - included in crunchy distribution
from element_tree import ElementTree, HTMLTreeBuilder, ElementSoup
et = ElementTree

from cometIO import register_new_page
import configuration

DTD = '<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Strict//EN" '\
'"http://www.w3.org/TR/xhtml1/DTD/strict.dtd">\n\n'
count = 0

def uidgen():
    """an suid (session unique ID) generator
    """
    global count
    count += 1
    return str(count)

class CrunchyPage(object):
    # handlers ::  string -> string -> handler function
    # pagehandlers ::
    # (sorry, a weird mix of haskell and OCaml notation in a python program :)
    handlers = {}
    pagehandlers = []
    null_handlers = {}
    def __init__(self, filehandle, url, remote=False, local=False):
        """url should be just a path if crunchy accesses the page locally, or the full URL if it is remote"""
        self.is_remote = remote # True if remote tutorial, on the web
        self.is_local = local  # True if local tutorial, not from the server root
        self.pageid = uidgen()
        self.url = url
        register_new_page(self.pageid)
        # "old" method using ElementTree directly
        #self.tree = HTMLTreeBuilder.parse(filehandle, encoding = 'utf-8')
        html = ElementSoup.parse(filehandle, encoding = 'utf-8')
        self.tree = et.ElementTree(html)
        # The security module removes all kinds of potential security holes
        # including some meta tags with an 'http-equiv' attribute.
        self.tree = security.remove_unwanted(self.tree)
        self.included = set([])
        self.head = self.tree.find("head")
        if not self.head:
            self.head = et.Element("head")
            self.head.text = " "
            html = self.tree.find("html")
            html.insert(0, self.head)
        self.body = self.tree.find("body")
        self.frameset = self.tree.find("frameset")
        self.process_tags()
        # we have to check wether there is a body element
        # because sometimes there is just a frameset elem.
        if self.body:
            self.body.attrib["onload"] = 'runOutput("%s")' % self.pageid
        else:
            print "No body, assuming frameset"
        self.add_js_code(comet_js)

    def add_include(self, include_str):
        self.included.add(include_str)

    def includes(self, include_str):
        return include_str in self.included

    def add_js_code(self, code):
        ''' includes some javascript code in the <head>.
            This is the preferred method.'''
        js = et.Element("script")
        js.set("type", "text/javascript")
        js.text = code
        self.head.append(js)

    def insert_js_file(self, filename):
        '''Inserts a javascript file link in the <head>.
           This should only be used for really big scripts
           (like editarea); the preferred method is to add the
           javascript code directly'''
        js = et.Element("script")
        js.set("src", filename)
        js.set("type", "text/javascript")
        js.text = " "  # prevents premature closing of <script> tag, misinterpreted by Firefox
        self.head.insert(0, js)
        return

    def add_css_code(self, code):
        css = et.Element("style")
        css.set("type", "text/css")
        css.text = code
        self.head.insert(0, css)

    def process_tags(self):
        """process all the customised tags in the page"""
        for tag in CrunchyPage.handlers:
            for elem in self.tree.getiterator(tag):
                if "title" in elem.attrib:
                    vlam = elem.attrib["title"].lower()
                    keyword = vlam.split(" ")[0]
                    if keyword in CrunchyPage.handlers[tag]:
                        CrunchyPage.handlers[tag][keyword](self, elem,
                                         self.pageid + ":" + uidgen(),
                                         vlam)
        for tag in CrunchyPage.null_handlers:
            for elem in self.tree.getiterator(tag):
                CrunchyPage.null_handlers[tag](self, elem, self.pageid +
                                                      ":" + uidgen(), None)
        # Crunchy can treat <pre> that have no markup as though they
        # are marked up with a default value
        # We only do this on pages that have not been prepared for Crunchy
        n_m = configuration.defaults.no_markup.lower()
        if n_m != 'none':
            vlam = n_m   # full value
            if n_m.startswith('image_file'): # image file has a filename
                n_m = 'image_file'  # extract just the type, like the others
            for elem in self.tree.getiterator("pre"):
                if "title" not in elem.attrib:
                    elem.attrib["title"] = vlam
                    CrunchyPage.handlers["pre"][n_m](self, elem,
                                                self.pageid + ":" + uidgen(),
                                                elem.attrib["title"])
        if "menu_included" not in self.included:
            CrunchyPage.handlers["no_tag"]["menu"](self)
        return

    def read(self):
        fake_file = StringIO()
        fake_file.write(DTD + '\n')
        # May want to use the "private" _write() instead of write() as the
        # latter will add a redundant <xml ...> statement unless the
        # encoding is utf-8 or ascii.
        self.tree.write(fake_file)
        return fake_file.getvalue()


comet_js = """
function runOutput(channel)
{
    var h = new XMLHttpRequest();
    h.onreadystatechange = function(){
        if (h.readyState == 4)
        {
            try
            {
                var status = h.status;
            }
            catch(e)
            {
                var status = "NO HTTP RESPONSE";
            }
            switch (status)
            {
            case 200:
                //alert(h.responseText);
                resText = h.responseText;
                if (resText.indexOf("Help on") != -1) {
                    // parse out the uid and replace with help_menu
                    start = resText.indexOf("getElementById(\\"out_") + 16;
                    end = resText.indexOf('"', start);
                    uid = resText.substring(start, end);
                    resText = resText.replace(uid, "help_menu");
                    document.getElementById("help_menu").innerHTML = "";
                    document.getElementById("help_menu").style.display = "block";
                    document.getElementById("help_menu_x").style.display = "block";
                }
                eval(resText);
                runOutput(channel);
                break;
            default:
                //alert("Output seems to have finished");
            }
        }
    };
    h.open("GET", "/comet?pageid="+channel, true);
    h.send("");
};
"""