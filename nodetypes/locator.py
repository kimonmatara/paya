import paya.lib.mathops as _mo
from paya.util import short
import paya.runtime as r


class Locator:

    #-----------------------------------------------------|    Macros

    @classmethod
    def createFromMacro(cls, macro, **overrides):
        """
        :param dict macro: the type of macro returned by :meth:`macro`
        :param \*\*overrides: overrides to the macro, passed in as keyword
            arguments
        :return: The reconstructed locator shape.
        :rtype: :class:`Locator`
        """
        macro = macro.copy()
        macro.update(overrides)

        shape = r.createNode('locator', n=macro['name'])
        xf = shape.getParent()

        shape.attr('localPosition').set(macro['localPosition'])
        shape.attr('localScale').set(macro['localScale'])

        return shape

    def macro(self):
        """
        :return: A simplified representation of this locator shape,
            used by :meth:`createFromMacro` to reconstruct it.
        :rtype: dict
        """
        macro = r.nodes.DependNode.macro(self)

        macro['localPosition'] = list(self.attr('localPosition').get())
        macro['localScale'] = list(self.attr('localScale').get())

        return macro

    @classmethod
    def normalizeMacro(cls, macro):
        """
        Used by the shapes library to fit control points inside a unit cube.
        This is an in-place operation; the method has no return value.

        :param dict macro: the macro to edit
        """
        point = macro['localPosition']
        point = _mo.pointsIntoUnitCube([point])[0]
        macro['localPosition'] = list(point)