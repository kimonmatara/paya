import pymel.core.nodetypes as _nt
from paya.util import short
import paya.runtime as r


class IkHandle:

    @classmethod
    @short(
        name='n',
        suffix='suf',
        inheritName='inn',
        solver='sol'
    )
    def create(
            cls,
            name=None,
            suffix=None,
            inheritName=True,
            **mayaOptions):
        """
        :param name/n: one or more name elements; defaults to None
        :type name/n: None, str, int, or list
        :param suffix/suf: if string, append; if ``True``, look up a type
            suffix and apply it; if ``False``, omit; defaults to
            :attr:`~paya.config.autoSuffix`
        :type suffix/suf: None, bool, str
        :param bool inheritName/inn: inherit names from
            :class:`~paya.lib.names.Name` blocks; defaults to True
        :param \*\*mayaOptions: all overflow keyword arguments are forwarded
            to :func:`~pymel.core.animation.ikHandle`
        :return: The constructed node.
        :rtype: :class:`~pymel.core.general.PyNode`
        """
        buildKwargs = {
            'name': cls.makeName(n=name, inn=inheritName, suf=suffix),
            'solver': 'ikRPsolver'
        }

        buildKwargs.update(mayaOptions)

        return r.ikHandle(**buildKwargs)[0]

    #------------------------------------------------------------|    Inspections

    def getTipJoint(self):
        """
        :return: The tip joint for the chain driven by this IK handle.
        :rtype: :class:`~paya.nodetypes.joint.Joint`
        """
        eff = self.getEffector()
        joint = None

        for attr in [eff.attr('t')] + eff.attr('t').getChildren():
            joint = attr.inputs(type='joint')

            if joint:
                joint = joint[0]
                break

        return joint

    @short(includeTip='it')
    def getJointList(self, includeTip=False):
        """
        Overloads :meth:`~paya.core.nodetypes.Joint.getJointList` to add the
        ``includeTip/it`` option. Note that, for parity with PyMEL, this is
        set to False by default.

        :param bool includeTip/it: include the tip joint; defaults to False
        :return: Joints driven by this IK handle.
        :rtype: list
        """
        out = _nt.IkHandle.getJointList(self)

        if includeTip:
            out.append(self.getTipJoint())

        return out

    def chain(self):
        """
        :return: The driven chain, including tip.
        :rtype: :class:`~paya.lib.skel.Chain`
        """
        return r.Chain(self.getJointList(it=True))

    #------------------------------------------------------------|    Twist

    @short(downAxis='da')
    def setTwistVectors(self, startVector, endVector, upAxis, downAxis=None):
        """
        For spline handles only. Activates advanced twist options and
        configures the start / end vectors.

        :param startVector: the start 'up' vector
        :type startVector: list, :class:`~paya.datatypes.vector.Vector`,
            :class:`~paya.plugtypes.math3D.Math3D`
        :param endVector: the end 'up' vector
        :type endVector: list, :class:`~paya.datatypes.vector.Vector`,
            :class:`~paya.plugtypes.math3D.Math3D`
        :param str upAxis: the chain axis to map to the 'up' vectors, for
            example 'z'
        :param str downAxis/da: if you know the 'bone' axis of the chain,
            provide it here to avoid extraneous calculations; defaults to None
        :return: ``self``
        """
        self.attr('dTwistControlEnable').set(True)
        self.attr('dWorldUpType').set(6) # Vector Start / End

        if downAxis is None:
            downAxis = self.chain().downAxis()

        for axisValue, attrName in zip(
                (downAxis, upAxis),
                ('dForwardAxis', 'dWorldUpAxis')
        ):
            if isinstance(axisValue, str):
                axisValue = {
                    'x': 'Positive X',
                    'y': 'Positive Y',
                    'z': 'Positive Z',
                    '-x': 'Negative X',
                    '-y': 'Negative Y',
                    '-z': 'Negative Z'
                }.get(axisValue, axisValue)

            self.attr(attrName).set(axisValue)

        startVector >> self.attr('dWorldUpVector')
        endVector >> self.attr('dWorldUpVectorEnd')

        return self