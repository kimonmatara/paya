import paya.lib.mathops as _mo
from paya.util import short
import paya.runtime as r


class Locator:

    #-----------------------------------------------------|    Constructors

    @classmethod
    @short(name='n', under='u', conformShapeNames='csn')
    def createFromMacro(cls, macro, name=None,
            under=None, conformShapeNames=True):
        """
        Recreates a locator from the type of dictionary returned by
        :meth:`~paya.nodetypes.locator.Locator.macro`.

        :param macro: the macro dictionary to use
        :param under/u: an optional parent for the locator; defaults to None
        :type under/u: None, str, :class:`~paya.nodetypes.transform.Transform`
        :param bool conformShapeNames/csn: ignored if *under* is None; clean
           up destination shape names after reparenting to the specified
           transform; defaults to True
        :param name/n: one or more name elements; defaults to None
        :type name/n: list, tuple, str
        :return: The locator.
        :rtype: :class:`~paya.nodetypes.locator.Locator`
        """
        shape = cls.createNode(n=name)
        xf = shape.getParent()

        shape.attr('localPosition').set(macro['localPosition'])
        shape.attr('localScale').set(macro['localScale'])

        if under:
            r.parent(shape, under, r=True, shape=True)
            r.delete(xf)

            if conformShapeNames:
                r.PyNode(under).conformShapeNames()

        return shape

    #-----------------------------------------------------|    Macro

    @short(normalize='nr')
    def macro(self, normalize=False):
        """
        :param bool normalize/nr: normalize any scale or position information
            (used by the shapes library); defaults to False
        :return: A simplified dictionary representation of this locator shape
            that can be used to reconstruct it. All information will be in
            local (object) space.
        :rtype: dict
        """
        out = {
            'nodeType': 'locator',
            'localPosition': list(self.attr('localPosition').get()),
            'localScale': list(self.attr('localScale').get())
        }

        if normalize:
            point = out['localPosition']
            point = _mo.pointsIntoUnitCube([point])[0]
            out['localPosition'] = list(point)

        return out