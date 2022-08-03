from paya.util import short
import paya.runtime as r


class MotionPath:

    #------------------------------------------------------|    Config helpers

    @short(
        worldUpVector='wu',
        worldUpObject='wuo'
    )
    def configFollow(
            self,
            frontAxis,
            upAxis,
            worldUpVector=None,
            worldUpObject=None
    ):
        """
        Performs quick configuration of follow options. If no 'up' hints are
        provided, the curve normal is used. All previous configuration is
        discarded.

        :param str frontAxis: the axis aligned to the curve tangent, e.g. '-y'
        :param str upAxis: the axis aligned to the resolved up vector, e.g.
            'x'
        :param worldUpVector/wu: if provided on its own, used for ``Vector``
            mode; if combined with *worldUpObject*, used for
            ``Object Rotation`` mode; defaults to None
        :type worldUpVector/wu: None, list, tuple, str,
            :class:`~paya.runtime.plugs.Vector`
        :param worldUpObject/wuo: if provided on its own, used for ``Object Up``
            mode; if combined with **worldUpVector**, used for
            ``Object Rotation`` mode; defaults to None
        :type worldUpObject/wuo: None, str,
            :class:`~paya.runtime.nodes.Transform`
        :return: ``self``
        :rtype: :class:`~paya.runtime.nodes.MotionPath`
        """
        for attrName, default in zip(
                ['worldUpVector', 'worldUpMatrix', 'worldUpType'],
                [[0, 1, 0], r.data.Matrix(), 'Normal']
        ):
            plug = self.attr(attrName)
            plug.release(recursive=True)
            plug.set(default)

        self.attr('follow').set(True)
        self.setFrontAxis(frontAxis)
        self.setUpAxis(upAxis)

        if worldUpVector:
            worldUpVector >> self.attr('worldUpVector')

        if worldUpObject:
            worldUpObject = r.PyNode(worldUpObject)
            worldUpObject.attr('wm') >> self.attr('worldUpMatrix')

        if worldUpVector and worldUpObject:
            self.attr('worldUpType').set('Object Rotation Up')

        elif worldUpVector:
            self.attr('worldUpType').set('Vector')

        elif worldUpObject:
            self.attr('worldUpType').set('Object Up')

        return self

    def setFrontAxis(self, axis):
        """
        Convenience method. Sets *frontAxis* and *inverseFront*
        on the motionPath using a single argument.

        :param str axis: the axis to set, for example '-y'
        :return: ``self``
        :rtype: :class:`~paya.runtime.nodes.MotionPath`
        """
        axis = axis.upper()
        self.attr('frontAxis').set(axis.strip('-'))
        self.attr('inverseFront').set('-' in axis)
        return self

    def setUpAxis(self, axis):
        """
        Convenience method. Sets *upAxis* and *inverseUp*
        on the motionPath using a single argument.

        :param str axis: the axis to set, for example 'x'
        :return: ``self``
        :rtype: :class:`~paya.runtime.nodes.MotionPath`
        """
        axis = axis.upper()
        self.attr('upAxis').set(axis.strip('-'))
        self.attr('inverseUp').set('-' in axis)
        return self

    def getFrontAxis(self):
        """
        Note that this doesn't check whether 'follow' is actually active
        on the node.

        :return: The signed front axis, for example '-x'.
        :rtype: str
        """
        ax = self.attr('frontAxis').get(asString=True).lower()
        if self.attr('inverseFront').get():
            ax = '-' + ax

        return ax

    def getUpAxis(self):
        """
        Note that this doesn't check whether 'follow' is actually active
        on the node.

        :return: The signed up axis, for example '-z'.
        :rtype: str
        """
        ax = self.attr('upAxis').get(asString=True).lower()
        if self.attr('inverseUp').get():
            ax = '-' + ax

        return ax

    #--------------------------------------------|    Sampling routines

    # Properties to mimic a pointOnCurveInfo node

    @property
    def normal(self):
        return self.attr('orientMatrix').getAxis(self.getUpAxis())

    @property
    def normalizedNormal(self):
        return self.normal.normal()

    @property
    def tangent(self):
        return self.attr('orientMatirx').getAxis(self.getFrontAxis())

    @property
    def normalizedTangent(self):
        return self.tangent.normal()

    @property
    def position(self):
        return self.attr('allCoordinates')