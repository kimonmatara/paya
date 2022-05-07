"""
Administers type suffixes of the kind typically found in Maya pipelines. These
are defined inside ``paya/lib/suffixes.json``, and are derived from the 'tags'
in the `Maya Module Index <https://help.autodesk.com/view/MAYAUL/2023/ENU/?guid=__Nodes_index_html>`_.

Suffixes are applied according to this rule:

-   If the node is a transform, then:

    -   If the node has a shape, the lookup is the shape's node type
    -   Otherwise, the lookup is the transform's node type

-   Otherwise:

    -   If the node is a shape, no suffix is applied
    -   Otherwise, the lookup is the shape's node type

Once read, suffixes are held in the ``suffixes`` global variable of this
module.
"""

import os
import re
import json

import maya.cmds as m

#-------------------------------------------------------------------|    Constants

filepath = os.path.join(
    os.path.dirname(__file__),
    'suffixes.json'
)

global suffixes
suffixes = {}

#-------------------------------------------------------------------|    Node inspection

def getKeyFromNode(node):
    """
    Given a Maya node, returns the appropriate key to use for suffix lookups.

    If the node is a (strict) transform then, if it has a shape, the shape's
    node type will be returned. If it doesn't have a shape, 'transform' will
    be returned.

    If the node is not a transform then, if it's a shape, None will be
    returned. If it's not a shape, the node's type will be returned.

    :param node: the node to inspect
    :type node: PyNode or str
    :return: The suffix lookup.
    :rtype: str
    """
    node = str(node)

    nts = m.nodeType(node, i=True)
    nt = nts[-1]

    if nt == 'transform':
        shapes = m.listRelatives(node, shapes=True)

        if shapes:
            return m.nodeType(shapes[0])

        return nt

    elif 'shape' in nts:
        return

    else:
        return nt

#-------------------------------------------------------------------|    I/O

def load():
    """
    Loads suffixes from ``suffixes.json``.
    """
    try:
        with open(filepath, 'r') as f:
            data = f.read()

    except IOError:
        m.warning(
            "Could not read file: {}".format(filepath)
        )

        return

    global suffixes
    suffixes = json.loads(data)

    print("Suffixes successfully read from : {}".format(filepath))

def dump():
    """
    Dumps suffixes into ``suffixes.json``.
    """
    global suffixes

    data = json.dumps(suffixes)

    with open(filepath, 'w') as f:
        f.write(data)

    print("Suffixes successfully dumped to: {}".format(filepath))

load()

#-------------------------------------------------------------------|    Population helpers

def learnFromHelp(htmlpath):
    """
    Populates the suffixes dict from a dumped Maya help file.

    To use this:

        -   Navigate to the Maya 'nodes index' page
        -   Turn on 'tags'
        -   Dump the main frame source code into an html file
        -   Pass the file path to this method

    To make changes permanent, call :func:`dump` afterwards.

    :param str htmlpath: the path to the saved html file
    """
    with open(htmlpath, 'r') as f:
        lines = f.readlines()

    global suffixes
    out = {}

    pat = r'\<tt\>([A-Za-z_0-9]{4}).*target\=\"contentFrame"\>(.*)\<\/a\>\<br \/>'

    count = 0

    for line in lines:
        mt = re.match(pat, line)

        if mt:
            suf, nodeType = mt.groups()
            out[nodeType] = suf
            count += 1

    suffixes.update(out)

    print("Learned {} suffix(es).".format(count))

def getFromName(name):
    """
    Extracts a type suffix from a node name.

    :param str name: the name to inspect
    :return: The extracted suffix, if any.
    """
    pat = r"^(.*?_)?([A-Z]+)$"

    name = name.split('|')[-1].split(':')[-1]
    mt = re.match(pat, name)

    if mt:
        return mt.groups()[-1]

def learnFromScene():
    """
    Learns suffixes from node names in the current scene. To make changes
    permanent, call :func:`dump` afterwards.
    """
    nodes = m.ls()
    shapes = m.ls(type='shape')

    nodes = set(nodes)-set(shapes)

    count = 0
    visited = []

    for node in nodes:
        suffix = getFromName(node)

        if suffix and suffix not in visited:
            key = getKeyFromNode(node)

            suffixes[key] = suffix
            count += 1
            visited.append(suffix)

    print("Learned {} suffix(es).".format(count))