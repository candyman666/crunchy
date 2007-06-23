"""  Crunchy image file plugin.

plugin used to display an image generated by some Python code.
"""

import os

# All plugins should import the crunchy plugin API
import CrunchyPlugin
from configuration import defaults

# Third party modules - included in crunchy distribution
from element_tree import ElementTree, HTMLTreeBuilder
et = ElementTree

# The set of other "widgets/services" provided by this plugin
provides = set(["image_file_widget"])
# The set of other "widgets/services" required from other plugins
requires = set(["io_widget", "/exec", "style_pycode",
               "editor_widget"])

def register():
    """The register() function is required for all plugins.
       In this case, we need to register two types of 'actions':
       1. a custom 'vlam handler' designed to tell Crunchy how to
          interpret the special Crunchy markup.
       2. a custom service to insert an editor when requested by this or
          another plugin.
       """
    # 'editor' only appears inside <pre> elements, using the notation
    # <pre title='editor ...'>
    CrunchyPlugin.register_vlam_handler("pre", "image_file",
                                            insert_image_file)

def insert_image_file(page, elem, uid, vlam):
    """handles the editor widget"""
    # We add html markup, extracting the Python
    # code to be executed in the process
    code, markup = CrunchyPlugin.services.style_pycode(page, elem)

    # reset the original element to use it as a container.  For those
    # familiar with dealing with ElementTree Elements, in other context,
    # note that the style_doctest() method extracted all of the existing
    # text, removing any original markup (and other elements), so that we
    # do not need to save either the "text" attribute or the "tail" one
    # before resetting the element.
    elem.clear()
    elem.tag = "div"
    # determine where the code should appear; we can't have both
    # no-pre and no-copy at the same time
    if not "no-pre" in vlam:
        elem.insert(0, markup)
    elif "no-copy" in vlam:
        code = "\n"
    CrunchyPlugin.services.insert_editor_subwidget(page, elem, uid, code)
    # some spacing:
    et.SubElement(elem, "br")
    # the actual button used for code execution:
    btn = et.SubElement(elem, "button")
    btn.attrib["onclick"] = "image_exec_code('%s')" % uid
    btn.text = "Generate image"
    et.SubElement(elem, "br")
    # an output subwidget:
    CrunchyPlugin.services.insert_io_subwidget(page, elem, uid)
    # Inserting the widget
    try:
        img_fname = vlam.split()[1]
    except IndexError:
        # The user hasn't supplied the filename in the VLAM.
        # I don't know how to respond back to the user.
        raise
    # Extension of the file; used for determining the filetype
    ext = img_fname.rsplit('.',1)[1]

    et.SubElement(elem, "br")
    if ext in ['svg', 'svgz']:
        img = et.SubElement(elem, "iframe")
    else:
        img = et.SubElement(elem, "img")
    img.attrib['id'] = 'img_' + uid
    img.attrib['src'] = ''
    img.attrib['alt'] = 'The code above should create a file named ' +\
                        img_fname + '.'
    et.SubElement(elem, "br")
    # we need some unique javascript in the page; note how the
    # "/exec" are referred to above as required
    # services appear here
    # with a random session id appended for security reasons.

    image_jscode = """
function image_exec_code(uid){
    // execute the code
    code=editAreaLoader.getValue("code_"+uid);
    var j = new XMLHttpRequest();
    j.open("POST", "/exec%(session_id)s?uid="+uid, false);
    code = '%(pre_code)s' + code + '%(post_code)s';
    j.send(code);
    // now load newly created image.
    var now = new Date();
    img_path = "%(img_fname)s?" + now.getTime();
    img = document.getElementById("img_"+uid);
    img.src = img_path;
    img.alt = "Image file saved as %(img_fname)s";
    img.alt = img.alt + "%(error_message)s";
    // This is needed to reload the new image
     j.open("GET", img_path, false);
     j.send(null);
};
"""

    pre_code = """
import os
__current = os.getcwdu()
os.chdir("%s")
"""%(defaults.temp_dir)

    #print "pre_code = ", pre_code

    image_fname =  "/CrunchyTempDir" +os.path.join(defaults.temp_dir, img_fname) #"file://" +
    #print "image_fname=", image_fname

    image_jscode = image_jscode%{
    "session_id": CrunchyPlugin.session_random_id,

    "pre_code": pre_code.replace('\n', '\\n'),

    "post_code":\
"""
os.chdir(__current)
""".replace('\n', '\\n'),
    "img_fname": image_fname,
    "error_message": """
    If you see this message, then the image was
    not created or loaded properly. This sometimes happens when creating
    a figure for the first time with matplotlib. Try running it again.
    """.replace('\n', '\\n')
}

    # At the end we need to make sure that the required javacript code is
    # in the page.
    if not page.includes("image_included"):
        page.add_include("image_included")
        page.add_js_code(image_jscode)
