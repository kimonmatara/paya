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
        conformShapeName='csn',
        size='siz',
        parent='p'
    )
    def create(
            cls,
            worldMatrix=None,
            displayLocalAxis=False,
            conformShapeName=None,
            name=None,
            parent=None,
            size=1.0
    ):
        """
        Locator constructor. Note that the return is the locator *shape*, not
        its transform.

        :param worldMatrix/wm: a world-matrix for the locator transform;
            ignored if a custom parent is specified via *parent*/*p*; defaults
            to None
        :param bool displayLocalAxis/dla: display local rotation axes; defaults to
            None
        :param bool conformShapeName/csn: ignored if *parent* was omitted;
            rename the shape after it is reparented; defaults to True if
            *parent* was provided, otherwise False
        :param float size/siz: a convenience scalar for the locator
            ``localScale`` attribute; defaults to 1.0
        :param parent/p: a custom parent for the locator *shape*; defaults to None
        :type parent/p: None, str, :class:`~paya.runtime.nodes.Transform`
        :param str name/n: a name for the locator *shape*; defaults to
            ``None``
        :return: The locator shape.
        :rtype: :class:`Locator`
        """
        shape = cls.createShape(p=parent, n=name, csn=conformShapeName)

        if worldMatrix and parent is None:
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

        for key in ('overrideEnabled', 'overrideColor'):
            try:
                shape.attr(key).set(macro[key])
            except:
                pass

    def macro(self, includeShapeDetails=False):
        """
        :param bool includeShapeDetails: include information on overrides;
            defaults to ``False``
        :return: A simplified representation of this locator shape,
            used by :meth:`createFromMacro` to reconstruct it.
        :rtype: dict
        """
        macro = r.nodes.DependNode.macro(self)

        macro['localPosition'] = list(self.attr('localPosition').get())
        macro['localScale'] = list(self.attr('localScale').get())

        if includeShapeDetails:
            macro['overrideEnabled'] = self.attr('overrideEnabled').get()
            macro['overrideColor'] = self.attr('overrideColor').get()

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