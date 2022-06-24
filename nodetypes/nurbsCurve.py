import paya.lib.mathops as _mo
import pymel.core.nodetypes as _nt
from paya.util import short
import paya.runtime as r


class NurbsCurve:

    #-----------------------------------------------------|    Macro

    def macro(self):
        """
        :return: A simplified dictionary representation of this object that
            can be used to reconstruct it.
        :rtype: dict
        """
        return {
            'knots': self.getKnots(),
            'degree': self.degree(),
            'form': self.form(),
            'points': map(list, self.getCVs())
        }

    #-----------------------------------------------------|    Sampling

    def takeClosestPoint(self, refPoint):
        """
        :param refPoint: the reference point
        :return: The closest point along the curve to 'refPoint`.
        :rtype: :class:`~paya.datatypes.point.Point`
        """
        return self.closestPoint(refPoint, space='world')

    def takePointAtParam(self, param):
        """
        :param param: the parameter to sample
        :type param: float, int,
            :class:`~paya.comptypes.nurbsCurveParameter.NurbsCurveParameter`
        :return: A world-space point at the specified parameter.
        :rtype: :class:`~paya.datatypes.point.Point`
        """
        param = float(param)
        point = self.getPointAtParam(param, space='world')
        return point

    def takeParamAtFraction(self, fraction):
        """
        :param float fraction: the length fraction to sample
        :return: A parameter at the given length fraction.
        :rtype:
            :class:`~paya.comptypes.nurbsCurveParameter.NurbsCurveParameter`
        """
        length = self.length() * float(fraction)
        param = self.findParamFromLength(length)
        return self.comp('u')[param]

    def takePointAtFraction(self, fraction):
        """
        :param fraction: the length fraction to sample
        :return: A world-space point at the given length fraction.
        :rtype: :class:`~paya.datatypes.point.Point`
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
        :rtype: :class:`list` of :class:`~paya.datatypes.point.Point`
        """
        if isinstance(numberOrFractions, int):
            fractions = _mo.floatRange(0, 1, numberOrFractions)

        else:
            fractions = numberOrFractions

        return [self.takePointAtFraction(
            fraction) for fraction in fractions]