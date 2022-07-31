from paya.util import short
import paya.lib.plugops as _po
import paya.runtime as r


class CurveAimUpGenerator(r.networks.CurveUpGenerator):
    """
    Derives curve up vector plugs based on interest points sampled from an
    'aim' curve, similar to how the ``curveWarp`` deformer does it.
    """

    #----------------------------------------------------|    Constructor

    @classmethod
    @short(closestPoint='cp')
    def create(cls, mainCurve, aimCurve, closestPoint=True):
        """
        :param aimCurve: the aim curve
        :type aimCurve: str, :class:`~paya.runtime.nodes.Transform`,
            :class:`~paya.runtime.nodes.NurbsCurve`,
            :class:`~paya.runtime.plugs.NurbsCurves`
        :param bool closestPoint/cp: pull points from the aim curve
            by proximity rather than matched parameter; defaults to
            True
        :return: An up-vector sampler system based on an aim curve.
        :rtype: :class:`CurveAimUpGenerator`.
        """
        curvePlug = _po.asGeoPlug(mainCurve, worldSpace=True)
        nameElems = (curvePlug.node().basename(), 'aim_curve_up')

        with r.Name(nameElems):
            node = cls._create(curvePlug, aimCurve, closestPoint=closestPoint)

        return node

    @classmethod
    def _create(cls, curvePlug, aimCurve, closestPoint=True):
        node = super(cls, cls)._create(curvePlug)
        aimCurve = _po.asGeoPlug(aimCurve, worldSpace=True)
        aimCurve >> node.addAttr('aimCurve', at='message')
        node.addAttr('closestPoint',
                at='bool', k=True, dv=closestPoint).lock()

        return node

    #----------------------------------------------------|    Sampling

    def aimCurvePlug(self):
        """
        :return: The output of the aim curve associated with this system.
        :rtype: :class:`~paya.runtime.plugs.NurbsCurve`
        """
        return self.attr('aimCurve').inputs(plugs=True)[0]

    def _sampleAt(self, parameter):
        mainCurve = self.curvePlug()
        aimCurve = self.aimCurvePlug()
        cp = self.attr('closestPoint').get()

        refPoint = mainCurve.pointAtParam(parameter)

        if cp:
            interest = aimCurve.closestPoint(refPoint)

        else:
            interest = aimCurve.pointAtParam(parameter)

        return interest-refPoint