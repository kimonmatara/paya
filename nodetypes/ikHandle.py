import paya.lib.mathops as _mo
import pymel.core.nodetypes as _nt
from paya.util import short
import paya.runtime as r


class IkHandle:

    @classmethod
    @short(name='n', solver='sol')
    def create(cls, name=None, **mayaOptions):
        """
        :param name/n: one or more name elements; defaults to None
        :type name/n: None, str, int, or list
        :param \*\*mayaOptions: all overflow keyword arguments are forwarded
            to :func:`~pymel.core.animation.ikHandle`
        :return: The constructed node.
        :rtype: :class:`~pymel.core.general.PyNode`
        """
        buildKwargs = {
            'name': cls.makeName(name),
            'solver': 'ikRPsolver'
        }

        buildKwargs.update(mayaOptions)

        return r.ikHandle(**buildKwargs)[0]

    #------------------------------------------------------------|    Inspections

    def getEndJoint(self):
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
            out.append(self.getEndJoint())

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

    #------------------------------------------------------------|    Pole vector

    @short(maintainOffset='mo')
    def setPolePoint(self, point, maintainOffset=False):
        """
        Configures the pole vector by aiming towards ``point`` in world-space.

        :param point: the point to aim towards
        :type point: list, tuple, :class:`~paya.datatypes.point.Point`
            or :class:`~paya.plugtypes.math3D.Math3D`
        :param bool maintainOffset/mo: preserve chain state; defaults to False
        :return: ``self``
        """
        point, dim, isplug = _mo.info(point)
        chordStart = self.getStartJoint().getWorldPosition(p=True)
        poleVec = point-chordStart

        if maintainOffset:
            # Gather info
            chordEnd = self.getWorldPosition(p=True)
            chordVec = chordEnd-chordStart

            _point = point.get()
            _initPoleVec = self.attr('poleVector'
                ).get() * self.attr('pm')[0].get()

            _chordStart = chordStart.get()
            _chordEnd = chordEnd.get()
            _chordVec = chordVec.get()
            _poleVec = poleVec.get()

            # 'Spin' the user point into an inert position
            # that wouldn't move the chain
            _defaultSpinMtx = r.createMatrix(
                'y', _chordVec,
                'x', _initPoleVec,
                t=_chordStart
            ).pk(t=True, r=True)

            _solvedSpinMtx = r.createMatrix(
                'y', _chordVec,
                'x', _poleVec,
                t=_chordStart
            ).pk(t=True, r=True)

            compensation = _solvedSpinMtx.inverse() * _defaultSpinMtx
            _defaultPoint = _point ^ compensation

            # Create the 'real' pole vector spin matrix, transform the inert
            # point with an offset
            solveMtx = r.createMatrix(
                'y', chordVec,
                'x', poleVec,
                t=chordStart
            ).pk(t=1, r=1)

            point = _defaultPoint ^ solveMtx.asOffset()

            # Rederive pole vector in world space
            poleVec = point-chordStart

        # Localise and connect
        poleVec *= self.attr('pim')[0]
        poleVec >> self.attr('poleVector')
        self.attr('poleVector').splitInputs()

        return self