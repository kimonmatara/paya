import maya.cmds as m
from paya.util import short
import paya.runtime as r


class Transform:

    #--------------------------------------------------------|    Sampling

    @short(plug='p', useLocatorShape='uls')
    def getWorldPosition(self, plug=False, useLocatorShape=True):
        """
        Returns the world translation of this transform. Pivots are ignored.

        :shorthand: ``gwp``
        :param bool plug/p: return an attribute instead of a value; if
            'useLocatorShape' is True then, where available, the locator
            shape's 'worldPosition' attribute will be returned; otherwise,
            a 'worldPosition' attribute will be retrieved, or initialised,
            on the transform itself, with its input configured as self.t ^
            self.pm[0]; defaults to False
        :param bool useLocatorShape/uls: True
        :return: The position attribute or value.
        :rtype: :class:`~paya.datatypes.point.Point` or
            :class:`~paya.plugtypes.vector.Vector`
        """
        if plug:
            if useLocatorShape:
                locatorShapes = self.getChildren(type='locator')

                if locatorShapes:
                    return locatorShapes[0].attr('worldPosition')

            if not self.hasAttr('worldPosition', checkShape=False):
                self.addAttr('worldPosition', at='double3', nc=3)

                for axis in 'XYZ':
                    self.addAttr('worldPosition'+axis,
                        at='doubleLinear', parent='worldPosition')

            attr = self.attr('worldPosition')

            if not attr.inputs():
                input = self.attr('t') ^ self.attr('pm')[0]
                input >> attr

            return attr

        return r.data.Point(r.xform(self, q=True, t=True, a=True, ws=True))

    gwp = getWorldPosition

    @short(plug='p')
    def getWorldMatrix(self, plug=False):
        """:param bool plug/p: return a plug instead of a value; defaults to
            False
        :return: The world matrix of this transform, as a value or plug.
        :rtype: :class:`paya.datatypes.matrix.Matrix` or
            :class:`paya.plugtypes.matrix.Matrix`
        """
        if plug:
            return self.attr('wm')

        return self.getMatrix(worldSpace=True)

    gwm = getWorldMatrix