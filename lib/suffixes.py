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

#-------------------------------------------------------------------|    Analysis / extractions

def isTypeSuffix(string):
    """
    Checks if 'string' looks like a type suffix, i.e. it's a group of
    uppercase letters starting with a non-number, or is a value inside
    :attr:`paya.lib.suffixes.suffixes`.

    :param string: The string to inspect
    :return: ``True`` if 'string' looks like a type suffix, otherwise
        ``False``.
    :rtype: bool
    """
    if re.match(r"^[A-Z][A-Z0-9]*$", string):
        return True

    global suffixes
    return string in suffixes.values()

def getFromName(name):
    """
    Extracts a type suffix from a node name.

    :param str name: the name to inspect
    :return: The extracted suffix, if any.
    :rtype: :class:`str`, ``None``
    """
    name = str(name).split('|')[-1].split(':')[-1]
    last = name.split('_')[-1]

    if isTypeSuffix(last):
        return last

#-------------------------------------------------------------------|    Node inspection

def getKeyFromNode(node):
    node = str(node)

    nts = m.nodeType(node, i=True)
    nt = nts[-1]

    if nt == 'transform':
        if m.controller(node, q=True):
            return 'payaControl'

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

    print("Suffixes read from: {}".format(filepath))

def dump():
    """
    Dumps suffixes into ``suffixes.json``.
    """
    global suffixes

    data = json.dumps(suffixes)

    with open(filepath, 'w') as f:
        f.write(data)

    print("Suffixes saved into: {}".format(filepath))

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