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

        self.attr('frontAxis').set(frontAxis.upper().strip('-'))
        self.attr('upAxis').set(upAxis.upper().strip('-'))

        self.attr('inverseFront').set('-' in frontAxis)
        self.attr('inverseUp').set('-' in upAxis)

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