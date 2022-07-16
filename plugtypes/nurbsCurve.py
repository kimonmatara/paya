import paya.lib.mathops as _mo
import pymel.util as _pu
from paya.util import short
import paya.runtime as r


class NurbsCurve:

    #---------------------------------------------------|    Curve-level info

    @short(reuse='re')
    def info(self, reuse=True):
        """
        :param bool reuse/re: Reuse any previously-connected ``curveInfo``
            node; defaults to True
        :return: A ``curveInfo`` node connected to this curve output.
        :rtype: :class:`~paya.runtime.nodes.CurveInfo`
        """
        if reuse:
            existing = self.outputs(type='curveInfo')

            if existing:
                return existing[0]

        node = r.nodes.CurveInfo.createNode()
        self >> node.attr('inputCurve')
        return node

    def length(self):
        """
        :return: The arc length of this curve output.
        :rtype: :class:`~paya.runtime.plugs.Math1D`
        """
        return self.info().attr('arcLength')

    def controlPoints(self):
        """
        :return: The ``.controlPoints`` multi-attribute of a connected
            ``curveInfo`` node.
        :rtype: :class:`~paya.runtime.plugs.Vector`
        """
        return self.info().attr('controlPoints')

    #---------------------------------------------------|    Granular sampling

    @short(uValue='u')
    def initMotionPath(self, *uValue, **attrConfig):
        """
        Connects and configures a ``motionPath`` node.

        :param uValue: an optional value or input for the ``uValue`` attribute
        :type uValue: float, :class:`~paya.runtime.plugs.Math1D`
        :param \*\*attrConfig: if provided, these should be an unpacked
            mapping of *attrName: attrSource* to configure the node's
            attributes; sources can be values or plugs
        :return: The ``motionPath`` node.
        :rtype: :class:`~paya.runtime.nodes.MotionPath`
        """
        if uValue:
            if 'uValue' in attrConfig:
                raise RuntimeError(
                    "'uValue' must either be passed as a "+
                    "positional or keyword argument, not both."
                )

            uValue = uValue[0]

        elif 'uValue' in attrConfig:
            uValue = attrConfig.pop('uValue')

        else:
            uValue = 0.0

        mp = r.nodes.MotionPath.createNode()
        self >> mp.attr('geometryPath')
        uValue >> mp.attr('uValue')

        for attrName, attrSource in attrConfig.items():
            attrSource >> mp.attr(attrName)

        return mp

    @short(turnOnPercentage='top')
    def infoAtParam(self, param, turnOnPercentage=False):
        """
        :param param: the parameter input for a ``pointOnCurveInfo`` node
        :type param: float, :class:`~paya.runtime.plugs.Math1D`
        :param bool turnOnPercentage/top: sets the ``turnOnPercentage`` flag
            of the ``pointOnCurveInfo`` node (note that this is just a
            normalization of parametric space; it is not equivalent to
            ``fractionMode`` on a ``motionPath``; defaults to False
        :return: A ``pointOnCurveInfo`` node configured for the specified
            parameter.
        :rtype: :class:`~paya.runtime.nodes.PointOnCurveInfo`
        """
        node = r.nodes.PointOnCurveInfo.createNode()
        node.attr('turnOnPercentage').set(turnOnPercentage)
        self >> node.attr('inputCurve')
        param >> node.attr('parameter')

        return node

    def pointAtParam(self, param):
        """
        :param param: the parameter to sample
        :type param: float, :class:`~paya.runtime.plugs.Math1D`
        :return: A point at the given parameter.
        """
        return self.infoAtParam(param).attr('position')

    def initNearestPointOnCurve(self, point):
        """
        Connects and configures a ``nearestPointOnCurve`` node.

        :param point: the reference point
        :return: The ``nearestPointOnCurve`` node.
        :rtype: :class:`~paya.runtime.nodes.NearestPointOnCurve`
        """
        node = r.nodes.NearestPointOnCurve.createNode()
        self >> node.attr('inputCurve')
        point >> node.attr('inPosition')
        return node

    def closestParam(self, point):
        """
        Returns the closest parameter to the given point.

        :param point: the reference point
        :type point: list, tuple, :class:`~paya.runtime.data.Vector`,
            :class:`~paya.runtime.data.Point`,
            :class:`~paya.runtime.plugs.Vector`
        :return: The sampled parameter.
        :rtype: :class:`~paya.runtime.plugs.Math1D`
        """
        return self.initNearestPointOnCurve().attr('parameter')

    paramAtPoint = closestParam

    def closestPoint(self, point):
        """
        Returns the closest point to the given point.

        :param point: the reference point
        :type point: list, tuple, :class:`~paya.runtime.data.Vector`,
            :class:`~paya.runtime.data.Point`,
            :class:`~paya.runtime.plugs.Vector`
        :return: The sampled point.
        :rtype: :class:`~paya.runtime.plugs.Vector`
        """
        return self.initNearestPointOnCurve().attr('position')

    def pointAtFraction(self, fraction):
        """
        :param fraction: the length fraction at which to sample a point
        :type fraction: float, :class:`~paya.runtime.plugs.Math1D`
        :return: A point at the specified length fraction.
        :rtype: :class:`~paya.runtime.plugs.Vector`
        """
        mp = self.initMotionPath(fraction, fractionMode=True)
        return mp.attr('allCoordinates')

    #---------------------------------------------------|    Edits

    @short(select='sel')
    def detach(self, *parameters, select=None):
        """
        Detaches this curve at the specified parameter(s).

        :param \*parameters: the parameter(s) at which to 'cut' the curve
        :type \*parameters: float, :class:`~paya.runtime.plugs.Math1D`
        :param select/sel: a subset of output indices to include in the
            return; ``keep`` attributes will configured accordingly
        :return: [:class:`~paya.runtime.plugs.NurbsCurve`]
        """
        parameters = _pu.expandArgs(*parameters)

        if not parameters:
            raise RuntimeError("No parameter(s) specified.")

        node = r.nodes.DetachCurve.createNode()

        self >> node.attr('inputCurve')

        for i, parameter in enumerate(parameters):
            parameter >> node.attr('parameter')[i]

        node.attr('outputCurve').evaluate()
        outputIndices = range(len(parameters)-1)

        if select is None:
            selectedIndices = outputIndices

        else:
            selectedIndices = _pu.expandArgs(select)

            for outputIndex in outputIndices:
                node.attr('keep')[
                    outputIndex].set(outputIndex in selectedIndices)

        return [node.attr('outputCurve'
            )[selectedIndex] for selectedIndex in selectedIndices]

    @short(relative='r')
    def subCurve(self, minValue, maxValue, relative=False):
        """
        Connects and configures a ``subCurve`` node and returns its output.

        :param minValue: a source for the ``minValue`` attribute
        :type minValue: float, :class:`~paya.runtime.plugs.Math1D`
        :param maxValue: a source for the ``maxValue`` attribute
        :type maxValue: float, :class:`~paya.runtime.plugs.Math1D`
        :param bool relative/r: set the node to 'relative'; defaults to False
        :return: The sub-curve.
        :rtype: :class:`~paya.runtime.plugs.NurbsCurve`
        """
        node = r.nodes.SubCurve.createNode()
        self >> node.attr('inputCurve')
        minValue >> node.attr('minValue')
        maxValue >> node.attr('maxValue')
        node.attr('relative').set(relative)

        return node.attr('outputCurve').setClass(type(self))

    def initExtendCurve(self, **config):
        """
        Connects and configures an ``extendCurve`` node.

        :param \*\*config: if provided, this should be an unpacked mapping
            of *attrName: attrSource* to configure the node attributes.
            Attribute sources can be values or plugs.
        :return: The ``extendCurve`` node.
        :rtype: :class:`~paya.runtime.nodes.ExtendCurve`
        """
        node = r.nodes.ExtendCurve.createNode()
        self >> node.attr('inputCurve1')

        for attrName, attrSource in config.items():
            attrSource >> node.attr(attrName)

        return node

    @short(
        removeMultipleKnots='rmk',
        atStart='ats'
    )
    def extendToPoint(
            self,
            point,
            atStart=False,
            removeMultipleKnots=False
    ):
        """
        Extends this curve to the specified point.

        :param point: the vector along which to extend
        :type point: list, tuple, str,
            :class:`paya.runtime.data.Point`,
            :class:`paya.runtime.plugs.Vector`
        :param bool atStart/ats: extend from the start of the curve instead
            of the end; defaults to False
        :param bool removeMultipleKnots/rmk: remove multiple knots; defaults
            to False
        :return: The modified curve output.
        :rtype: :class:`~paya.runtime.plugs.NurbsCurve`
        """
        return self.initExtendCurve(
            extendMethod='Point',
            inputPoint=point,
            start=1 if atStart else 0,
            removeMultipleKnots=removeMultipleKnots
        ).attr('outputCurve').setClass(type(self))

    @short(
        removeMultipleKnots='rmk',
        atStart='ats'
    )
    def extendByVector(
            self,
            vector,
            atStart=False,
            removeMultipleKnots=False
    ):
        """
        Extends this curve along the specified vector.

        :param vector: the vector along which to extend
        :type vector: list, tuple, str,
            :class:`paya.runtime.data.Vector`,
            :class:`paya.runtime.plugs.Vector`
        :param bool atStart/ats: extend from the start of the curve instead
            of the end; defaults to False
        :param bool removeMultipleKnots/rmk: remove multiple knots; defaults
            to False
        :return: The modified curve output.
        :rtype: :class:`~paya.runtime.plugs.NurbsCurve`
        """
        controlPoints = list(self.controlPoints())
        startPoint = controlPoints[0 if atStart else -1]
        endPoint = startPoint + vector

        return self.extendToPoint(
            endPoint,
            ats=atStart,
            rmk=removeMultipleKnots
        )

    @short(
        linear='lin',
        circular='cir',
        extrapolate='ext',
        atStart='ats',
        atBothEnds='abe',
        removeMultipleKnots='rmk'
    )
    def extendByDistance(
            self,
            distance,
            linear=False,
            circular=False,
            extrapolate=False,
            atStart=None,
            atBothEnds=None,
            removeMultipleKnots=False
    ):
        """
        Extends this curve by distance.

        :param distance: the distance (length) to extend by
        :type distance: float, :class:`~paya.runtime.plugs.Math1D`
        :param bool linear/lin: use the 'Linear' mode of the
            ``extendCurve`` node; defaults to True
        :param bool circular/cir: use the 'Linear' mode of the
            ``extendCurve`` node; defaults to False
        :param bool extrapolate/ext: use the 'extrpolate' mode of the
            ``extendCurve`` node; defaults to False
        :param bool atStart/ats: extend from the start of the curve instead
            of the end; defaults to False
        :param bool atBothEnds/abe: extend from both ends of the curve;
            defauls to False
        :param bool removeMultipleKnots: remove multiple knots; defaults to
            False
        :return: The modified curve.
        :rtype: :class:`~paya.runtime.plugs.NurbsCurve`
        """
        if circular:
            extensionType = 'Circular'

        elif extrapolate:
            extensionType = 'Extrapolate'

        else:
            extensionType = 'Linear'

        if atStart:
            start = 'Start'

        elif atBothEnds:
            start = 'Both'

        else:
            start = 'End'

        return self.initExtendCurve(
            extendMethod='Distance',
            extensionType=extensionType,
            distance=distance,
            removeMultipleKnots=removeMultipleKnots,
            start=start
        ).attr('outputCurve').setClass(type(self))