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

    def index(self):
        """
        :return: The U value at this parameter. If this is a range, only
            the start of the range will be returned.
        :rtype: :class:`float`
        """
        pat = r"^.*?\.u\[(.*?)\]$"
        st = str(self)

        content = re.match(pat, st).groups()[0]
        elems = content.split(':')

        return float(elems)[0]

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

    @short(worldSpace='ws', plug='p')
    def point(self, worldSpace=False, plug=False):
        """
        :param bool worldSpace/ws: return a world-space position;
            defaults to ``False``
        :param bool plug/p: return a plug rather than a value; defaults to
            ``False``
        :return: A point position at this parameter.
        :rtype: :class:`~paya.runtime.data.Point` |
            :class:`~paya.runtime.plugs.Vector`
        """
        return self.node().pointAtParam(
            float(self), p=plug, ws=worldSpace)

    @short(plug='p')
    def getWorldPosition(self, plug=False):
        """
        :param bool plug/p: return a plug rather than a value; defaults to
            ``False``
        :return: A world-space position at this parameter.
        :rtype: :class:`~paya.runtime.data.Point` |
            :class:`~paya.runtime.plugs.Vector`
        """
        return self.point(ws=True, p=plug)

    @short(plug='p')
    def fraction(self, plug=False):
        """
        :param bool plug/p: return a plug rather than a value; defaults to
            ``False``
        :return: The curve length fraction at this parameter.
        :rtype: :class:`float` | :class:`~paya.runtime.plugs.Math1D`
        """
        return self.node().fractionAtParam(float(self), p=plug)

    @short(plug='p')
    def length(self, plug=False):
        """
        :param bool plug/p: return a plug rather than a value; defaults to
            ``False``
        :return: The curve length at this parameter.
        :rtype: :class:`float` | :class:`~paya.runtime.plugs.Math1D`
        """
        return self.node().lengthAtParam(float(self), p=plug)

    @short(plug='p', normalize='nr')
    def tangent(self, plug=False, normalize=False):
        """
        :param bool plug/p: return a plug rather than a value; defaults to
            ``False``
        :param bool normalize/nr: return the normalized tangent;
            defaults to ``False``
        :return: The curve tangent at this parameter.
        :rtype: :class:`float` | :class:`~paya.runtime.plugs.Math1D`
        """
        return self.node().tangentAtParam(float(self), nr=normalize, p=plug)

    @short(plug='p', normalize='nr')
    def normal(self, plug=False, normalize=False):
        """
        :param bool plug/p: return a plug rather than a value; defaults to
            ``False``
        :param bool normalize/nr: return the normalized normal;
            defaults to ``False``
        :return: The curve normal at this parameter.
        :rtype: :class:`float` | :class:`~paya.runtime.plugs.Math1D`
        """
        return self.node().normalAtParam(float(self), nr=normalize, p=plug)

    #-----------------------------------------------------|    Edits

    @short(plug='p')
    def detach(self):
        """
        :return: The resulting shape segments.
        :rtype: [:class:`~paya.runtime.nodes.NurbsCurve`]
        """
        return self.node().detach(float(self))

    @short(toParameter='tp')
    def subCurve(self, toParameter=None):
        """
        :param toParameter:
        :return:
        """
        if toParameter is None:
            params = self.indices()

            if len(params) is not 2:
                raise ValueError(
                    "Please specify 'toParameter', or "+
                    "call subCurve() on a ranged component."
                )

        else:
            if isinstance(toParameter, str):
                try:
                    toParameter = r.Attribute(toParameter)

                except:
                    try:
                        toParameter = float(r.Component(toParameter))
                    except:
                        raise TypeError("Can't parse {}".format(toParameter))

            params = [float(self), toParameter]

        return self.node().subCurve(*params)