"""The IO widget, handles text and graphical IO
This is just the UI part, the communication code is defined in the core
- maybe this should me moved to core?
"""

provides = set(["io_widget"])

from CrunchyPlugin import *
import CrunchyPlugin

from element_tree import ElementTree, HTMLTreeBuilder
et = ElementTree

def register():
    register_service(insert_io_subwidget, "insert_io_subwidget")

def insert_io_subwidget(page, elem, uid):
    """insert an output widget into elem, usable for editors and interpreters,
    includes a canvas :-)
    """
    if not page.includes("io_included"):
        page.add_include("io_included")
        page.add_js_code(io_js)
        page.add_css_code(io_css)
    output = et.SubElement(elem, "span")
    output.attrib["class"] = "output"
    output.attrib["id"] = "out_" + uid
    output.text = "\n"
    inp = et.SubElement(elem, "input")
    inp.attrib["id"] = "in_" + uid
    inp.attrib["onkeydown"] = 'push_keys(event, "%s")' % uid
    inp.attrib["onkeypress"] = 'tooltip_display(event, "%s")' % uid
    inp.attrib["type"] = "text"
    inp.attrib["class"] = "input"

io_js = r"""
function push_keys(event, uid){
    if(event.keyCode != 13) return;
    data = document.getElementById("in_"+uid).value;
    document.getElementById("in_"+uid).value = "";
    if (data.substring(0,5) == "help(") {
        display_help(uid, data);
        return;
    }
    var i = new XMLHttpRequest()
    i.open("POST", "/input?uid="+uid, true);
    i.send(data + "\n");
};
"""

io_css = r"""

.stdout {
    color: blue;
}

.stderr {
    color: red;
}

.input {
    display: none;
    width: 90%;
    font: 10pt monospace;
    border-width: 1px;
}

.output{
    font: 10pt monospace;
    color:darkgreen;
    white-space: -moz-pre-wrap; /* Mozilla, supported since 1999 */
    white-space: pre-wrap; /* CSS3 - Text module (Candidate Recommendation)
                            http://www.w3.org/TR/css3-text/#white-space */
}

.crunchy_canvas{
    display: none;
}
"""