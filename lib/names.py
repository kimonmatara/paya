"""
Node-naming utilities, usually called indirectly.
"""

import re

import pymel.util as _pu

from paya.util import short, pad
import paya.config as config
import paya.lib.suffixes as _suf

def legalise(name):
    """
    Modifies a string so that Maya will accept it as a node name.

    :param str name: the string to conform
    :return: The Maya name.
    """
    if name:
        name = name.strip()

    if name:
        # If there are numbers at the start, insert an underscore

        if name[0].isdigit():
            name = '_'+name

        # Fuse all internal illegal characters into single underscores
        name = re.sub(r'([^_a-zA-Z0-9:]+)', '_', name)

    if name:
        return name

    else:
        return '_'

def conformElems(*elems):
    """
    Cleans up user name elements, typically specified through ``*args``
    and / or the ``name/n`` keyword argument.

    :param \*elems: one or more name elements, packed or unpacked
    :type \*elems: int, str
    :return: The conformed elements.
    :rtype: list
    """
    out = []
    padding = config['padding']

    for elem in _pu.expandArgs(*elems):
        if isinstance(elem, int):
            elem = pad(elem, padding)

        elif not elem:
            continue

        out.append(elem)

    return out

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

    return string in _suf.suffixes.values()

@short(
    stripNamespace='sns',
    stripDagPath='sdp',
    stripTypeSuffix='sts'
)
def shorten(
        name,
        stripNamespace=None,
        stripDagPath=None,
        stripTypeSuffix=None
):
    """
    Shortens a Maya name to various degrees. The name will be returned as-is
    unless one or more flags are set to ``True``.

    :param str name: the name to process
    :param bool stripNamespace/sns: remove namespace information; defaults to
        False
    :param bool stripDagPath/sdp: remove DAG path information; defaults to
        False
    :param bool stripTypeSuffix/sts: removes anything that looks like a type
        suffix; defaults to False
    :return: the modified name
    :rtype: str
    """
    if stripNamespace:
        name = re.sub(r'[a-zA-Z_0-9]*:', '', name)

    if stripDagPath:
        name = re.split(r'\-\>|\|', name)[-1]

    if stripTypeSuffix:
        dagElems = re.split(r'(\-\>|\|)', name)
        shortName = dagElems[-1]
        underElems = shortName.split('_')

        if len(underElems) > 1:
            lastElem = underElems[-1]

            if isTypeSuffix(lastElem):
                del(underElems[-1])
                shortName = '_'.join(underElems)

            dagElems[-1] = shortName
            name = ''.join(dagElems)

    return name

class Name:
    """
    Context manager. Accumulates name elements hierarchically, and can also
    be used to override config['padding'].

    :param elems: one or more name elements, packed or unpacked
    :type elems: int, str
    :param padding/pad: if provided, will be used to set padding defaults for
        the block
    :type padding/pad: None, int
    """
    __elems__ = []

    @short(padding='pad')
    def __init__(self, *elems, padding=None):
        self._elems = _pu.expandArgs(*elems)
        self._padding = padding

    def __enter__(self):
        if self._padding:
            self._prev_padding = config['padding']
            config['padding'] = self._padding

        self._prev_elems = Name.__elems__[:]
        Name.__elems__ += conformElems(self._elems)

        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._padding:
            config['padding'] = self._prev_padding

        Name.__elems__ = self._prev_elems

        return False

@short(name='n', nodeType='nt', control='ct')
def make(*elems, name=None, node=None, nodeType=None, control=False):
    """
    Constructs Maya node names.

    :config keys: ``suffixNodes``, ``padding``, ``inheritNames``
    :param \*elems: one or more name elements
    :type \*elems: int, str, list
    :param name/n: elements passed-through via a ``name`` argument;
        these will always be prepended to \*elems; defaults to None
    :type name/n: int, str, list, None
    :param bool control/ct: ignore the *node* and *nodeType* arguments
        and apply the Paya suffix for controls; defaults to False
    :param node: ignored if ``nodeType`` has been provided; a node to inspect
        to determine the node type suffix; defaults to None
    :type node: None, str, :class:`~pymel.core.general.PyNode`
    :param nodeType/nt: a reference node type for the suffix lookups, or
        'payaControl' for controls; defaults to None
    :type nodeType/nt: None, str
    :return: A Maya node name.
    :rtype: str
    """
    elems = list(_pu.expandArgs(*elems))

    if name:
        elems = list(_pu.expandArgs(name)) + elems

    elems = conformElems(elems)

    if config['inheritNames']:
        if Name.__elems__:
            elems = Name.__elems__ + elems

    if config['suffixNodes']:
        if control:
            nodeType = 'payaControl'

        else:
            if nodeType is None:
                if node:
                    nodeType = _suf.getKeyFromNode(node)

        if nodeType:
            suffix = _suf.suffixes.get(nodeType)

            if suffix:
                elems.append(suffix)

    name = '_'.join(elems)
    name = legalise(name)

    return name