"""
Node-naming utilities, usually called indirectly.
"""

import re
from functools import wraps
from contextlib import ContextDecorator

import pymel.util as _pu
import maya.cmds as m

from paya.util import short, pad, undefined
from paya.config import config, takeUndefinedFromConfig
import paya.lib.suffixes as _suf

#----------------------------------------------------------|
#----------------------------------------------------------|    FUNCTIONAL
#----------------------------------------------------------|

def legalise(name):
    """
    Modifies a string so that Maya will accept it as a node name.

    :param str name: the string to conform
    :return: The Maya name.
    :rtype: :class:`str`
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
@takeUndefinedFromConfig
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

        lastElem = underElems[-1]

        if _suf.isTypeSuffix(lastElem):
            del(underElems[-1])
            shortName = '_'.join(underElems)

        dagElems[-1] = shortName
        name = ''.join(dagElems)

    return name

#----------------------------------------------------------|
#----------------------------------------------------------|    CONTEXTUAL
#----------------------------------------------------------|

class Name(ContextDecorator):
    """
    Context manager. Accumulates prefixes for default node names, and
    provides other useful overrides.

    This context manager can also be used as a decorator:

    .. code-block:: python

        @Name('build')
        def build(*args, **kwargs):
            pass

    Inside list comprehensions, it would take this form:

    .. code-block:: python

        locs = [Name('point', x+1, padding=3)(r.nodes.Locator.createNode)() for x in range(20)]
        # Produces point_001_LOCT, point_002_LOCT etc.

    :param \*elems: one or more name elements to combine into a prefix
    :type \*elems: :class:`str`, :class:`int`
    :param suffix/suf: if this is a string, it will be used a suffix for all
        nodes; if it's ``True``, appropriate suffixes will be looked up;
        if it's ``False``, no suffixes will be applied; defaults to
        enclosing overrides, or the namesake configuration flag
    :type suffix/suf: :class:`str`, :class:`bool`
    :param padding/pad: the padding depth for any integer elements;
        defaults to enclosing overrides, or the namesake configuration
        flag
    :type padding/pad: :class:`int`
    :param bool inherit/i: inherit elements from enclosing :class:`Name`
        blocks; defaults to ``True``
    :param namespace/ns: set the namespace for the block; if omitted,
        no namespace will be set
    :type namespace/ns: :class:`str`
    :param bool relativeNames/rel: switches to relative name lookups for
        the block; defaults to enclosing overrides
    :param bool allowUnprefixedSuffixes/aus: where no name elements have
        been accumulated, allows, for example, a transform to be named
        ``XFRM`` rather than ``transform1``; defaults to enclosing
        overrides or the namesake configuration flag
    """
    __elems__ = []

    @short(suffix='suf',
           padding='pad',
           inherit='i',
           namespace='ns',
           relativeNames='rel',
           allowUnprefixedSuffixes='aus')
    def __init__(self,
                 *elems,
                 suffix=undefined,
                 padding=undefined,
                 inherit=True,
                 namespace=undefined,
                 relativeNames=undefined,
                 allowUnprefixedSuffixes=undefined):

        self.elems = list(_pu.expandArgs(*elems))
        self.suffix = suffix
        self.padding = padding
        self.inherit = inherit
        self.namespace = namespace
        self.relativeNames = relativeNames
        self.allowUnprefixedSuffixes = allowUnprefixedSuffixes

    def __enter__(self):
        # Elements
        self._prev_elems = Name.__elems__[:]

        if self.inherit:
            Name.__elems__ = self._prev_elems + self.elems
        else:
            Name.__elems__ = self.elems

        # Config overrides
        overrides = {k:v for k, v in zip(
            ['suffix', 'padding', 'allowUnprefixedSuffixes'],
            [self.suffix, self.padding, self.allowUnprefixedSuffixes],
            ) if v is not undefined}

        self._prev_config = config.copy()
        config.update(overrides)

        # Namespace
        if self.namespace is not undefined:
            self._prevNamespace = m.namespaceInfo(currentNamespace=True)

            if not m.namespace(exists=self.namespace):
                m.namespace(addNamespace=self.namespace)

            m.namespace(setNamespace=self.namespace)

        if self.relativeNames is not undefined:
            self._prevRelativeNames = m.namespace(q=True, rel=True)
            m.namespace(relativeNames=self.relativeNames)

        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        # Elements
        Name.__elems__ = self._prev_elems

        # Config overrides
        config.clear()
        config.update(self._prev_config)

        if self.namespace is not undefined:
            m.namespace(setNamespace=self._prevNamespace)

        if self.relativeNames is not undefined:
            m.namespace(relativeNames=self._prevRelativeNames)

        return False

    @classmethod
    @short(nodeType='nt',
           transform='xf',
           suffix='suf',
           allowUnprefixedSuffixes='aus',
           padding='pad',
           inherit='i',
           control='ct')
    @takeUndefinedFromConfig
    def make(cls,
             *elems,
             nodeType=None,
             transform=None,
             suffix=undefined,
             allowUnprefixedSuffixes=undefined,
             padding=undefined,
             inherit=True,
             control=False):
        """
        Constructs Maya node names.

        :param \*elems: one or more name elements to combine into a prefix
        :type \*elems: :class:`str`, :class:`int`
        :param nodeType/nt: a hint for the node type suffix; defaults to
            ``None``
        :type nodeType/nt: :class:`str`, ``None``
        :param bool transform/xf: indicate that the name is intended for a
            transform; defaults to ``None``
        :param suffix/suf: if this is a string, it will be used a suffix for all
            nodes; if it's ``True``, appropriate suffixes will be looked up;
            if it's ``False``, no suffixes will be applied; defaults to
            enclosing overrides, or the namesake configuration flag
        :type suffix/suf: :class:`str`, :class:`bool`
        :param bool allowUnprefixedSuffixes/aus: where no name elements have
            been accumulated, allows, for example, a transform to be named
            ``XFRM`` rather than ``transform1``; defaults to enclosing
            overrides or the namesake configuration flag
        :param padding/pad: the padding depth for any integer elements;
            defaults to enclosing overrides, or the namesake configuration
            flag
        :type padding/pad: :class:`int`
        :param bool inherit/i: inherit name elements from :class:`Name`
            blocks; defaults to ``True``
        :param bool control/ct: indicate that the name is for a control;
            defaults to ``False``
        :return: The constructed node name.
        :rtype: :class:`str`
        """
        if control:
            suffix = _suf.suffixes['payaControl']

        elems = list(_pu.expandArgs(*elems))

        if inherit:
            elems = Name.__elems__ + elems

        elems = conformElems(*elems, padding=padding)

        if transform:
            isShape = False

        else:
            if nodeType:
                isShape = 'shape' in m.nodeType(nodeType, i=True, itn=True)

            else:
                isShape = False

        if suffix and not isinstance(suffix, str):
            if nodeType:
                suffix = _suf.suffixes.get(nodeType)
            else:
                suffix = None

        if elems:
            if suffix:
                elems.append(suffix)

            name = '_'.join(elems)

        else:
            if suffix and allowUnprefixedSuffixes:
                name = suffix
            elif nodeType:
                name = nodeType+'1'
            else:
                name = ''

        if isShape:
            name += 'Shape'

        name = legalise(name)
        return name