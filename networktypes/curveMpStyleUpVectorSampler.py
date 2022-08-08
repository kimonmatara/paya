import paya.lib.mathops as _mo
from paya.util import short
import paya.runtime as r


class CurveMpStyleUpVectorSampler(r.networks.CurveUpVectorSampler):

    """
    Curve up vector generator. Mimics 'follow' options on
    :class:`motionPath <paya.runtime.nodes.MotionPath>` nodes.
    """

    #----------------------------------------------------------|
    #----------------------------------------------------------|    CONSTRUCTOR
    #----------------------------------------------------------|

    @classmethod
    @short(upObject='uo',
           upVector='upv',
           perpendicularize='per')
    def create(cls,
               curve,
               upObject=None,
               upVector=None,
               perpendicularize=False):
        """
        If neither *upObject* nor *upVector* as specified, curve normals will
        be used instead.

        :param curve: the associated curve
        :type curve: str, :class:`~paya.runtime.plugs.NurbsCurve`,
            :class:`~paya.runtime.nodes.NurbsCurve`
        :param upObject/uo: if provided on its own, becomes an 'aim'
            target ('Object Up' mode); if combined with *upVector*,
            multiplies *upVector* ('Object Rotation Up' mode); defaults to
            None
        :type upObject/uo: None, str, :class:`~paya.runtime.nodes.Transform`
        :param upVector/upv: if provided on its own, it's used directly;
            if combined with *upObject*, it's multiplied with the world matrix
            of *upObject*; defaults to None
        :param bool perpendicularize/per: when this is ``False``, vectors
            won't be perpendicular to the curve (unless defaulting to curve
            normals), but this won't matter for dynamic matrix construction;
            set to ``True`` to force perpendicularity; defaults to False
        :return: The up vector sampler.
        :rtype: :class:`CurveMpStyleUpVectorSampler`
        """
        node = r.networks.CurveUpVectorSampler.create(curve)
        node.attr('payaSubtype').set(cls.__name__)
        node.__class__ = cls
        node.addAttr('perpendicularize', at='bool', dv=perpendicularize)
        node.doPerpendicularize = perpendicularize

        if upObject:
            upObject = r.PyNode(upObject)

        if upVector:
            upVector = _mo.conformVectorArg(upVector)

            if upObject:
                upVector *= upObject.attr('wm')

            node.addAttr('upVector', nc=3, at='double3')

            for ax in 'XYZ':
                node.addAttr('upVector'+ax, parent='upVector')

            upVector >> node.attr('upVector')
            node.hasUpVector = True
            node.hasInterest = False

        elif upObject:
            node.addAttr('interest', nc=3, at='double3')

            for ax in 'XYZ':
                node.addAttr('interest'+ax, parent='interest')
            
            upObject.getWorldPosition(p=True) >> node.attr('interest')

            node.hasUpVector = False
            node.hasInterest = True

        else:
            node.hasUpVector = False
            node.hasInterest = False

        return node

    def __paya_subtype_init__(self):
        super().__paya_subtype_init__()
        self.hasInterest = self.hasAttr('interest')
        self.hasUpVector = self.hasAttr('upVector')
        self.doPerpendicularize = self.attr('perpendicularize').get()

    #----------------------------------------------------------|
    #----------------------------------------------------------|    SAMPLES
    #----------------------------------------------------------|

    @short(plug='p')
    def sampleAtParam(self, parameter, plug=True):
        """
        :param parameter: the parameter at which to sample the up vector
        :type parameter: float, str, :class:`~paya.runtime.plugs.Math1D`
        :param bool plug/p: return an attribute output, not just a value;
            if ``False``, *parameter* must also be a value; defaults to True
        :return: A vector value or plug at the specified parameter.
        :rtype: :class:`paya.runtime.data.Vector`,
            :class:`paya.runtime.plugs.Vector`
        """
        if self.hasUpVector and not self.doPerpendicularize:
            # Quickest return
            return self.attr('upVector').get(plug=plug)

        return r.networks.CurveUpVectorSampler.sampleAtParam(
            self, parameter, p=plug)

    def _sampleAtParam(self, parameter, plug=True):
        hasUpVector = self.hasUpVector
        doPerpendicularize = self.doPerpendicularize
        hasInterest = self.hasInterest
        curve = self.curve()

        if hasUpVector:
            upVector = self.attr('upVector').get(p=plug)

        elif hasInterest:
            interest = self.attr('interest').get(p=plug)
            refPoint = curve.pointAtParam(parameter, plug=plug)
            upVector = interest-refPoint

        else:
            doPerpendicularize = False
            upVector = curve.normalAtParam(parameter, plug=plug)

        if doPerpendicularize:
            tangent = curve.tangentAtParam(parameter, plug=plug)
            upVector = upVector.rejectFrom(tangent)

        return upVector