import re
from paya.util import short
import pymel.util as _pu
import paya.runtime as r


class NurbsCurveParameter:

    #-----------------------------------------------------|    Component management

    def isRange(self):
        """
        :return: True if this component represents a range.
        :rtype: bool
        """
        return len(self.indices()) > 1

    def indices(self):
        """
        :return: A tuple of either one or two indices
            (representing a U range).
        :rtype: (float), (float, float)
        """
        pat = r"^.*?\.u\[(.*?)\]$"
        st = str(self)

        content = re.match(pat, st).groups()[0]
        elems = content.split(':')
        return tuple([float(elem) for elem in elems])

    def __float__(self):
        """
        :return: This parameter as a float.
        :raises ValueError: Can't return a float because this parameter
            instance represents a range.
        :rtype: :class:`float`
        """
        if self.isRange():
            raise ValueError("Parameter is a range.")

        return self.indices()[0]

    #-----------------------------------------------------|    Sampling

    @short(plug='p')
    def point(self, plug=False):
        """
        :alias: ``getWorldPosition`` / ``gwp``
        :param bool plug/p: return a plug, not value; defaults to False
        :return: A world position at this parameter.
        """
        return self.node().pointAtParam(float(self), p=plug)

    gwp = getWorldPosition = point

    @short(
        squashStretch='ss',
        upVector='upv',
        upObject='upo',
        aimCurve='aic',
        globalScale='gs',
        matchedCurve='mc',
        plug='p'
    )
    def matrix(
            self,
            tangentAxis,
            upAxis,
            squashStretch=False,
            upVector=None,
            upObject=None,
            aimCurve=None,
            globalScale=None,
            matchedCurve=False,
            plug=False
    ):
        """
        :param str tangentAxis: the axis to align to the curve tangent
        :param str upAxis: the axis to align to the resolved up vector
        :param bool squashStretch/ss: incorporate tangent stretching
            (dynamic only); defaults to False
        :param upVector/upv: used as an up vector on its own, or extracted from
            *upObject*; defaults to None
        :type upVector/upv: None, list, tuple, str,
            :class:`~paya.runtime.data.Vector`,
            :class:`~paya.runtime.plugs.Vector`
        :param aimCurve/aic: an up curve; defaults to None
        :type aimCurve/aic: str, :class:`~paya.runtime.nodes.Transform`,
            :class:`~paya.runtime.nodes.NurbsCurve`,
            :class:`~paya.runtime.plugs.NurbsCurve`
        :param upObject/upo: used as an aiming interest on its own, or as a source
            for *upVector*; defaults to None
        :type upObject/upo: None, str, :class:`~paya.runtime.nodes.Transform`
        :param globalScale/gs: used to drive scaling on dynamic matrices only;
            the scale will be normalised; defaults to None
        :type globalScale/gs: None, float, :class:`~paya.runtime.plugs.Math1D`
        :param bool matchedCurve/mc: set this to True when *aimCurve* has the
            same U domain as this curve, to avoid unnecessary closest-point
            calculations; defaults to False
        :param bool plug/p: force a dynamic output; defaults to False
        :return: A matrix at the specified parameter, constructed using the
            most efficient DG configuration for the given options.
        :rtype: :class:`~paya.runtime.plugs.Matrix`,
            :class:`~paya.runtime.data.Matrix`
        """
        return self.node().matrixAtParam(
            float(self),
            tangentAxis,
            upAxis,
            ss=squashStretch,
            upv=upVector,
            upo=upObject,
            aic=aimCurve,
            gs=globalScale,
            mc=matchedCurve,
            p=plug
        )

    gwm = getWorldMatrix = matrix

    @short(plug='p')
    def fraction(self, plug=False):
        """
        :param bool plug/p: force a dynamic output; defaults to False
        :return: The length fraction at the given parameter
        :rtype: float, :class:`~paya.runtime.plugs.Math1D`
        """
        return self.node().fractionAtParam(float(self), p=plug)

    @short(plug='p')
    def length(self, param, plug=False):
        """
        :param bool plug/p: force a dynamic output; defaults to False
        :return: The curve length at the given parameter.
        :rtype: float, :class:`~paya.runtime.plugs.Math1D`
        """
        return self.node().lengthAtParam(float(self), p=plug)

    #-----------------------------------------------------|    Edits

    def detach(self):
        """
        :return: The resulting shape segments.
        :rtype: [:class:`~paya.runtime.nodes.NurbsCurve`]
        """
        return self.node().detach(self)

    def subCurve(self, *toParameter):
        """
        Returns a sub-curve (via a ``subCurve`` node). If this is a ranged
        parameter, its range is used. Otherwise, *toParameter* is used for
        the end.

        :param \*toParameter: the end parameter for the segment if this
            parameter is not ranged.
        :type \*toParameter: float, string,
            :class:`~paya.runtime.comps.NurbsCurveParameter`
            :class:`~paya.runtime.plugs.Math1D`
        :return: The resulting shape.
        """
        indices = list(self.indices())

        if len(indices) < 2:
            if toParameter:
                indices.append(toParameter[0])

            else:
                raise RuntimeError("Need an end parameter.")

        return self.node().subCurve(*indices)