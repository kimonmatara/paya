import re

from paya.lib.grouptree import GroupTree
from paya.util import int_to_letter
import maya.cmds as m
import paya.runtime as r


class CreateGuide:

    def __get__(self, inst, instype):
        return instype.getGuideClass().create


class Part(r.parts.PartBase):
    """
    Base class for rig parts.
    """

    #-----------------------------------------------------|    Guide interop

    createGuide = CreateGuide()

    @classmethod
    def getGuideClass(cls):
        return getattr(r.parts, '{}Guide'.format(cls.__name__))

    #-----------------------------------------------------|    Construction

    @classmethod
    def _getCreateNameContext(cls):
        """
        Called before a build wrapped by
        :func:`~paya.part.partcreator.partCreator` to establish the naming
        environment.

        Parts are named according to these rules:

        -   If there is no active :class:`~paya.lib.names.Name` block, the
            name element will be set to ``'unnamed'``.
        -   There must be no active namespace.

        :return: A configured context manager.
        :rtype: :class:`~paya.lib.names.Name`
        """
        # Should not be building main rig parts under a namespace
        if m.namespaceInfo(currentNamespace=True) != ':':
            raise RuntimeError("Rig parts cannot be built under a namespace.")

        # If there are no name elements, add a default name element, but
        # make sure it's not in use by any other part in the scene

        if r.Name.__elems__:
            return r.NullCtx()

        num = 0
        base = 'unnamed'

        while True:
            if num:
                name = '{}_{}'.format(base, int_to_letter(num.upper()))
            else:
                name = base

            if not m.objExists('{}_{}'.format(name, cls.__suffix__)):
                break

            num += 1

        return r.Name(name)