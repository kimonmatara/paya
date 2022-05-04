"""
Node-naming utilities, usually called indirectly by custom class methods.
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

        name = re.sub(r'([^_a-zA-Z0-9\:]+)', '_', name)

    if name:
        return name

    else:
        return '_'

@short(padding='pad')
def conformElems(*elems, padding=None):
    """
    Cleans up user name elements, typically specified through ``*args``
    and / or the ``name/n`` keyword argument.

    :param elems: one or more name elements, packed or unpacked
    :type elems: int, str
    :param padding/pad: optional padding depth for any integers; defaults
        to None
    :type padding/pad: None, int
    :return: The conformed elements.
    :rtype: list
    """
    out = []

    for elem in _pu.expandArgs(*elems):
        if isinstance(elem, int):
            if padding is None:
                elem = str(elem)

            else:
                elem = pad(elem, padding)

        elif not elem:
            continue

        out.append(elem)

    return out

class Name(object):
    """
    Context manager. Accumulates name elements hierarchically.

    :param elems: one or more name elements, packed or unpacked
    :type elems: int, str
    :param padding/pad: optional padding depth for any integers; defaults
        to None
    :param bool inherit/i: inherit from containing blocks; defaults to True
    :param suffix/suf: optional override for ``config.autoSuffix``;
        defaults to None
    :type suffix/suf: None, bool
    """
    __elems__ = []
    __suffix__ = None

    @short(inherit='i', suffix='suf', padding='pad')
    def __init__(self, *elems, inherit=True, suffix=None, padding=None):
        self._elems = conformElems(*elems, padding=padding)
        self._inherit = inherit

        if suffix is None:
            suffix = Name.__suffix__

        elif isinstance(suffix, str):
            raise TypeError("'suffix' must be a boolean")

        self._suffix = suffix

    def __enter__(self):
        self._old_elems = Name.__elems__

        new_elems = self._elems

        if self._inherit:
            new_elems = self._old_elems + new_elems

        Name.__elems__ = new_elems

        self._old_suffix = Name.__suffix__
        Name.__suffix__ = self._suffix

    def __exit__(self, exc_type, exc_val, exc_tb):
        Name.__elems__ = self._old_elems
        Name.__suffix__ = self._old_suffix

        return False


@short(
    name='n',
    inherit='i',
    suffix='suf',
    nodeType='nt',
    padding='pad'
)
def make(
        *elems,
        name=None,
        inherit=True,
        suffix=None,
        node=None,
        nodeType=None,
        padding=None
):
    """
    Constructs Maya node names.

    :param elems: one or more name elements, packed or unpacked
    :type elems: int, str
    :param name/n: pass-through for any elements provided via a ``name/n``
        keyword argument; these will always be prepended; defaults to None
    :type name/n: None, str
    :param padding/pad: optional padding depth for any integers; defaults
        to None
    :type padding/pad: None, int
    :param bool inherit/i: inherit prefixes from :class:`Name` blocks;
        defaults to True
    :param suffix/suf: optional override for ``config.autoSuffix``; if
        ``True``, apply suffixes; if ``False``, omit them; if a string,
        use it; defaults to None
    :type suffix/suf: bool, str
    :param node: ignored if ``nodeType`` is provided; a node to inspect
        for an appropriate suffix lookup; defaults to None
    :type node: PyNode, str, None
    :param nodeType/nt: ignored if ``suffix`` is a string; if provided, will
        be used as the suffix lookup; defaults to None
    :type nodeType/nt: bool, None
    :return: The name.
    :rtype: str
    """
    # Resolve elements

    elems = conformElems(name, elems, padding=padding)

    if inherit:
        elems = Name.__elems__ + elems

    # Resolve suffix

    if suffix is None:
        if inherit:
            suffix = Name.__suffix__

    if suffix is None:
        suffix = config.autoSuffix

    if suffix:
        _suffix = None

        if isinstance(suffix, str):
            _suffix = suffix

        else:
            if nodeType is None:
                if node:
                    nodeType = _suf.getKeyFromNode(node)

            if nodeType is not None:
                _suffix = _suf.suffixes.get(nodeType)

        if _suffix is not None:
            elems.append(_suffix)

    name = '_'.join(elems)

    return legalise(name)