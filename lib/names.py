"""
Node-naming utilities, usually called indirectly.
"""

import re

import pymel.util as _pu

from paya.util import short, pad
import paya.config as config
import paya.override as override
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

@short(padding='pad')
def conformElems(*elems):
    """
    Cleans up user name elements, typically specified through ``*args``
    and / or the ``name/n`` keyword argument.

    :config keys: ``padding``
    :param \*elems: one or more name elements, packed or unpacked
    :type \*elems: int, str
    :return: The conformed elements.
    :rtype: list
    """
    out = []
    padding = config.padding

    for elem in _pu.expandArgs(*elems):
        if isinstance(elem, int):
            elem = pad(elem, padding)

        elif not elem:
            continue

        out.append(elem)

    return out


class Name:
    """
    Context manager. Accumulates name elements hierarchically.

    :param elems: one or more name elements, packed or unpacked
    :type elems: int, str
    """
    __elems__ = []

    def __init__(self, *elems):
        self._elems = _pu.expandArgs(*elems)

    def __enter__(self):
        self._prev_elems = Name.__elems__[:]
        Name.__elems__ += conformElems(self._elems)

        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        Name.__elems__ = self._prev_elems

        return False

@short(name='n', nodeType='nt')
def make(*elems, name=None, node=None, nodeType=None):
    """
    Constructs Maya node names.

    :config keys: ``suffixNodes``, ``padding``, ``inheritNames``
    :param \*elems: one or more name elements
    :type \*elems: int, str, list
    :param name/n: elements passed-through via a ``name`` argument;
        these will always be prepended to \*elems; defaults to None
    :type name/n: int, str, list, None
    :param node: ignored if ``nodeType`` has been provided; a node to inspect
        to determine the node type suffix; defaults to None
    :type node: None, str, :class:`~pymel.core.general.PyNode`
    :param nodeType/nt: a reference node type for the suffix lookups; defaults
        to None
    :type nodeType/nt: None, str
    :return: A Maya node name.
    :rtype: str
    """
    elems = list(_pu.expandArgs(*elems))

    if name:
        elems = list(_pu.expandArgs(name)) + elems

    elems = conformElems(elems)

    if config.inheritNames:
        if Name.__elems__:
            elems = Name.__elems__ + elems

    if config.suffixNodes:
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