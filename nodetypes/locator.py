import paya.lib.mathops as _mo
from paya.util import short
import paya.runtime as r


class Locator:

    #-----------------------------------------------------|    Constructor

    @classmethod
    @short(
        worldMatrix='wm',
        displayLocalAxis='dla',
        name='n',
        size='siz'
    )
    def create(
            cls,
            worldMatrix=None,
            displayLocalAxis=False,
            name=None,
            under=None,
            size=1.0
    ):
        """
        Locator constructor. Note that the return is the locator *shape*, not
        its transform.

        :param worldMatrix/wm: a world-matrix for the locator transform;
            ignored if a custom parent is specified via *under*/*u*; defaults
            to None
        :param bool displayLocalAxis/dla: display local rotation axes; defaults to
            None
        :param float size/siz: a convenience scalar for the locator
            ``localScale`` attribute; defaults to 1.0
        :param under/u: a custom parent for the locator *shape*; defaults to None
        :type under/u: None, str, :class:`~paya.runtime.nodes.Transform`
        :param name/n: one or more name elements; defaults to None
        :type name/n: None, str, int, tuple, list
        :return: The locator shape.
        :rtype: :class:`Locator`
        """
        shape = cls.createShape(u=under, n=name)

        if worldMatrix and under is None:
            shape.getParent().setMatrix(worldMatrix)

        shape.attr('localScale').set([size] * 3)

        if displayLocalAxis:
            shape.attr('displayLocalAxis').set(True)

        return shape

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