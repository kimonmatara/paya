"""
Node-naming utilities, usually called indirectly.
"""

import re

import pymel.util as _pu

import maya.cmds as m
from paya.util import short, pad, undefined
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

@short(padding='pad')
def conformElems(*elems, padding=undefined):
    """
    Cleans up user name elements wrangled by :class:`Name`.

    :param \*elems: one or more name elements, packed or unpacked
    :type \*elems: int, str
    :param padding/pad: padding for any integer elements; defaults
        to ``config['padding']``
    :return: The conformed elements.
    :rtype: list
    """
    out = []

    if padding is undefined:
        padding = config['padding']

    for elem in _pu.expandArgs(*elems):
        if isinstance(elem, int):
            elem = pad(elem, padding)

        elif not elem:
            continue

        out.append(elem)

    return out


@short(
    stripNamespace='sns',
    stripDagPath='sdp',
    stripTypeSuffix='sts'
)
def shorten(
        name,
        stripNamespace=False,
        stripDagPath=False,
        stripTypeSuffix=False
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

            if _suf.isTypeSuffix(lastElem):
                del(underElems[-1])
                shortName = '_'.join(underElems)

            dagElems[-1] = shortName
            name = ''.join(dagElems)

    return name


class Name:
    __elems__ = []
    __suffix__ = config['suffixNodes']
    __padding__ = undefined
    __inherit__ = True

    @short(suffix='suf',
           padding='pad',
           inherit='i')
    def __init__(self,
                 *elems,
                 suffix=undefined,
                 padding=undefined,
                 inherit=undefined):
        self.elems = list(_pu.expandArgs(*elems))
        self.suffix = suffix
        self.padding = padding
        self.inherit = inherit

    def __enter__(self):
        self._prev_elems = Name.__elems__
        self._prev_suffix = Name.__suffix__
        self._prev_padding = Name.__padding__
        self._prev_inherit = Name.__inherit__

        Name.__elems__ = Name.__elems__ + self.elems

        if self.suffix is not undefined:
            Name.__suffix__ = self.suffix

        if self.padding is not undefined:
            Name.__padding__ = self.padding

        if self.inherit is not undefined:
            Name.__inherit__ = self.inherit

        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        Name.__elems__ = self._prev_elems
        Name.__suffix__ = self._prev_suffix
        Name.__padding__ = self._prev_padding
        Name.__inherit__ = self._prev_inherit

        return False

    @classmethod
    @short(nodeType='nt',
           transform='xf',
           suffix='suf',
           padding='pad',
           inherit='i',
           control='ct')
    def make(cls,
             *elems,
             nodeType=None,
             transform=None,
             suffix=undefined,
             padding=undefined,
             inherit=undefined,
             control=False):

        if suffix is undefined:
            suffix = Name.__suffix__

        if padding is undefined:
            padding = Name.__padding__

        if inherit is undefined:
            inherit = Name.__inherit__

        elems = list(_pu.expandArgs(*elems))

        if inherit:
            elems = Name.__elems__ + elems

        elems = conformElems(*elems, padding=padding)

        isShape = False

        if isinstance(suffix, str):
            elems.append(suffix)

        elif suffix:
            if control:
                suffix = _suf.suffixes['payaControl']

            else:
                if nodeType:
                    elems.append(_suf.suffixes.get(nodeType, nodeType))

                    isShape = (not transform) and ('shape' \
                        in m.nodeType(nodeType, i=True, itn=True))

        if elems:
            name = '_'.join(elems)

            if isShape:
                name += 'Shape'

            return legalise(name)

        # No elements; if we have a node type, use it to improvise a name

        if nodeType:
            out = nodeType+'1'

            if isShape:
                out += 'Shape'

            return out

        return legalise('')