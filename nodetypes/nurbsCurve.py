import paya.lib.mathops as _mo
import pymel.core.nodetypes as _nt
from paya.util import short
import paya.runtime as r


class NurbsCurve:

    @classmethod
    def createFromMacro(cls, macro, **overrides):
        """
        :param dict macro: the type of macro returned by :meth:`macro`
        :param \*\*overrides: overrides passed-in as keyword arguments
        :return: A curve constructed using the macro.
        :rtype: :class:`NurbsCurve`.
        """
        macro = macro.copy()
        macro.update(overrides)

        kwargs = {
            'point': macro['point'],
            'knot': macro['knot'],
            'periodic': macro['form'] is 2,
            'degree': macro['degree']
        }

        xf = r.curve(**kwargs)

        if macro['knotDomain'][1] == 1.0 and curve.getKnotDomain()[1] != 1.0:
            xf = r.rebuildCurve(
                xf,
                ch=False,
                d=macro['degree'],
                kcp=True,
                kep=True,
                kt=True,
                rt=0,
                rpo=True,
                kr=0
            )[0]

        shape = xf.getShape()
        shape.rename(macro['name'])

        if macro['form'] is 1:
            shape.attr('f').set(1)

        return shape

    #-----------------------------------------------------|    Macro

    # @short(normalize='nr')
    # def macro(self, normalize=False):
    #     """
    #     :param bool normalize/nr: normalize curve points (used by the shapes
    #         library); defaults to False
    #     :return: A simplified dictionary representation of this curve shape
    #         that can be used to reconstruct it. Point information will be in
    #         local (object) space. Name is ignored.
    #     :rtype: dict
    #     """
    #     macro = r.nodes.DependNode.macro(self)
    #
    #     macro['knot'] = self.getKnots()
    #     macro['degree'] = self.degree()
    #     macro['form'] = self.attr('f').get()
    #     macro['point'] = list(map(list, self.getCVs()))
    #     macro['knotDomain'] = self.getKnotDomain()
    #
    #     if normalize:
    #         macro['point'] = [list(p) for p in \
    #             _mo.pointsIntoUnitCube(macro['point'])]
    #
    #     return macro

    def macro(self):
        """
        :return: A simplified representation of this curve that can be used
            by :meth:`createFromMacro` to reconstruct it.
        :rtype: dict
        """
        macro = r.nodes.DependNode.macro(self)

        macro['knot'] = self.getKnots()
        macro['degree'] = self.degree()
        macro['form'] = self.attr('f').get()
        macro['point'] = list(map(list, self.getCVs()))
        macro['knotDomain'] = self.getKnotDomain()

        return macro

    @classmethod
    def normalizeMacro(cls, macro):
        """
        Used by the shapes library to fit control points inside a unit cube.
        This is an in-place operation; the method has no return value.

        :param dict macro: the macro to edit
        """
        points = macro['point']
        points = _mo.pointsIntoUnitCube(points)
        macro['point'] = [list(point) for point in points]

    #-----------------------------------------------------|    Sampling

    def takeClosestPoint(self, refPoint):
        """
        :param refPoint: the reference point
        :return: The closest point along the curve to 'refPoint`.
        :rtype: :class:`~paya.runtime.data.Point`
        """
        return self.closestPoint(refPoint, space='world')

    def takePointAtParam(self, param):
        """
        :param param: the parameter to sample
        :type param: float, int,
            :class:`~paya.runtime.comps.NurbsCurveParameter`
        :return: A world-space point at the specified parameter.
        :rtype: :class:`~paya.runtime.data.Point`
        """
        param = float(param)
        point = self.getPointAtParam(param, space='world')
        return point

    def takeParamAtFraction(self, fraction):
        """
        :param float fraction: the length fraction to sample
        :return: A parameter at the given length fraction.
        :rtype:
            :class:`~paya.runtime.comps.NurbsCurveParameter`
        """
        length = self.length() * float(fraction)
        param = self.findParamFromLength(length)
        return self.comp('u')[param]

    def takePointAtFraction(self, fraction):
        """
        :param fraction: the length fraction to sample
        :return: A world-space point at the given length fraction.
        :rtype: :class:`~paya.runtime.data.Point`
        """
        param = self.takeParamAtFraction(fraction)
        return self.takePointAtParam(param)

    def distributePoints(self, numberOrFractions):
        """
        Return world-space points distributed along the length of the curve.

        :param numberOrFractions: this can either be a list of length
            fractions, or a number
        :type numberOrFractions: tuple, list or int
        :return: The distributed points.
        :rtype: :class:`list` of :class:`~paya.runtime.data.Point`
        """
        if isinstance(numberOrFractions, int):
            fractions = _mo.floatRange(0, 1, numberOrFractions)

        else:
            fractions = numberOrFractions

        return [self.takePointAtFraction(
            fraction) for fraction in fractions]