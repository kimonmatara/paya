import paya.lib.mathops as _mo
import pymel.core.nodetypes as _nt
from paya.util import short
import paya.runtime as r


class NurbsCurve:

    @classmethod
    @short(
        name='n',
        under='u',
        conformShapeNames='csn',
        dispCV='dcv'
    )
    def createFromMacro(
            cls,
            macro,
            under=None,
            conformShapeNames=True,
            name=None,
            dispCV=False
    ):
        """
        Recreates a curve from the type of dictionary returned by
        :meth:`~paya.nodetypes.nurbsCurve.NurbsCurve.macro`.

        :param macro: the macro dictionary to use
        :param under/u: an optional parent for the curve; defaults to None
        :type under/u: None, str, :class:`~paya.nodetypes.transform.Transform`
        :param bool conformShapeNames/csn: ignored if *under* is None; clean
            up destination shape names after reparenting to the specified
            transform; defaults to True
        :param name/n: one or more name elements; defaults to None
        :type name/n: list, tuple, str
        :param bool dispCV/dcv: display curve CVs; defaults to False
        :return: The curve.
        :rtype: :class:`~paya.nodetypes.nurbsCurve.NurbsCurve`
        """
        kwargs = {
            'point': macro['point'],
            'knot': macro['knot'],
            'periodic': macro['form'] is 2,
            'degree': macro['degree'],
            'name': cls.makeName(n=name)
        }

        curve = r.curve(**kwargs)

        if macro['knotDomain'][1] == 1.0 and curve.getKnotDomain()[1] != 1.0:
            curve = r.rebuildCurve(curve, ch=False, d=macro['degree'],
                kcp=True, kep=True, kt=True, rt=0, rpo=True, kr=0)[0]

        if macro['form'] is 1:
            curve.attr('f').set(1)

        shape = curve.getShape()

        if under:
            r.parent(shape, under, r=True, shape=True)
            r.delete(curve)

            if conformShapeNames:
                r.PyNode(under).conformShapeNames()

        if dispCV:
            shape.attr('dcv').set(True)

        return shape

    #-----------------------------------------------------|    Macro

    def macro(self):
        """
        :return: A simplified dictionary representation of this curve shape
            that can be used to reconstruct it. Point information will be in
            local (object) space. Name is ignored.

        :rtype: dict
        """
        return {
            'nodeType': 'nurbsCurve',
            'knot': self.getKnots(),
            'degree': self.degree(),
            'form': self.attr('f').get(),
            'point': list(map(list, self.getCVs())),
            'knotDomain': self.getKnotDomain()
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