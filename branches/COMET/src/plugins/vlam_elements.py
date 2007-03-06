"""A plugin that handles all the VLAM elements"""

from CrunchyPlugin import *

# Third party modules - included in crunchy distribution
from element_tree import ElementTree, HTMLTreeBuilder
et = ElementTree


def register():
    register_vlam_handler("pre", "editor", insert_editor)
    register_vlam_handler("pre", "interpreter", insert_interpreter)
    register_service(insert_editor_subwidget, "insert_editor_subwidget")
        
def insert_editor_subwidget(elem, uid, code="\n"):
    """inserts an Elementtree that is an editor,
    used to provide a basic insert_editor_subwidget service
    """
    inp = et.SubElement(elem, "textarea")
    inp.attrib["rows"] = "10"
    inp.attrib["cols"] = "80"
    inp.attrib["id"] = "code_" + uid
    inp.text = code
    
def insert_editor(page, elem, uid):
    """handles the editor widget"""
    services.insert_editor_subwidget(elem, uid)
    et.SubElement(elem, "br")
    btn = et.SubElement(elem, "button")
    btn.attrib["onclick"] = "exec_code('%s')" % uid
    btn.text = "Execute"
    et.SubElement(elem, "br")
    page.insert_output(elem, uid)
        
def insert_interpreter(page, elem, uid):
    """inserts an interpreter (actually the js code to initialise an interpreter)"""
    page.add_js_code('init_interp("%s");' % uid)
    page.insert_output(elem, uid)
    