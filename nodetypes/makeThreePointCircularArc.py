import paya.runtime as r
from paya.util import short


class MakeThreePointCircularArc:

    def _isCompensated(self):
        try:
            curveOutput = self.attr('compensatedOutputCurve')

        except r.MayaAttributeError:
            return False

        if curveOutput.inputs():
            for attrName in ('point1Proxy', 'point2Proxy', 'point3Proxy'):
                try:
                    plug = self.attr(attrName)

                except r.MayaAttributeError:
                    return False

                if not plug.inputs():
                    return False

            return True

        return False

    @short(replaceOutputs='ro')
    def getCompensatedOutputCurve(self, jitterVector, replaceOutputs=False):
        """
        Returns a curve output that will work even when the tree arc points
        are collinear. The curve output will be exposed on the node itself
        as ``.compensatedOutputCurve``.

        This is implemented by swapping-in a straight NURBS curve with matched
        spans and degree where appropriate.

        .. note::

            This method will move the point inputs (point1, point2 and point3)
            of the node into 'proxy' inputs (point1Proxy, point2Proxy and
            point3Proxy). To preserve the compensation, any subsequent edits
            should be performed on those proxies instead of the main inputs.

        .. warning::

            This method can only be run once per node. An error will be raised
            if the compensation attributes are already present.

        :param jitterVector: equivalent to *directionVector* on a two-point
            circular arc; when the arc is collinear, the middle point will
            be moved along this vector to prevent Maya Script Editor errors;
            this will never be seen, since the 'line' curve will take over
            in those cases
        :type jitterVector: list, tuple, :class:`~paya.runtime.plugs.Vector`
        :param bool replaceOutputs/ro: replace any existing outgoing curve
            connections; defaults to False
        :return: The compensated curve output.
        :rtype: :class:`~paya.runtime.plugs.NurbsCurve`
        """
        if self._isCompensated():
            return self.attr('compensatedOutputCurve')

        for attrName in [
            'compensatedOutputCurve',
            'point1Proxy',
            'point2Proxy',
            'point3Proxy'
        ]:
            if self.hasAttr(attrName):
                plug = self.attr(attrName)
                plug.release(recursive=True)
                self.deleteAttr(attrName)

        # Init the output

        if self.hasAttr('compensatedOutputCurve'):
            self.deleteAttr('compensatedOutputCurve')

        output = self.addAttr('compensatedOutputCurve', dt='nurbsCurve')
        output.__class__ = r.plugs.NurbsCurve

        # Init the proxies

        proxies = []
        mainPlugs = []

        for attrName in ('point1', 'point2', 'point3'):
            main = self.attr(attrName)
            main.unlock(recursive=True)
            pxyName = attrName+'Proxy'

            if self.hasAttr(pxyName):
                existing = self.attr(pxyName)
                existing.unlock(recursive=True)
                self.deleteAttr(pxyName)

            self.addAttr(pxyName, nc=3, at='double3', k=True)

            for i, axis in enumerate('XYZ'):
                self.addAttr(
                    pxyName+axis,
                    at='double',
                    k=True,
                    parent=attrName+'Proxy'
                )

            pxy = self.attr(pxyName)
            pxy.set(main.get())

            sources = [pxy] + pxy.getChildren()
            dests = [main] + main.getChildren()

            for source, dest in zip(sources, dests):
                inputs = dest.inputs(plugs=True)

                if inputs:
                    inputs[0] >> source

                source >> dest

            proxies.append(pxy)
            mainPlugs.append(main)

        # Detect if inline

        v1 = proxies[1]-proxies[0]
        v2 = proxies[2]-proxies[1]

        inline = v1.dot(v2, nr=True).abs().ge(1.0)

        # Jitter middle point

        middlePoint = inline.ifElse(
            proxies[1]+jitterVector,
            proxies[1]
        )

        middlePoint >> self.attr('point2')

        for mainPlug in mainPlugs:
            mainPlug.lock(recursive=True)

        # Draw line output

        line = r.plugs.NurbsCurve.createLine(
            mainPlugs[0],
            mainPlugs[2],
            degree=self.attr('degree'),
            numCVs=self.attr('sections')+self.attr('degree')
        )

        existingOutputs = self.attr('outputCurve').outputs(plugs=True)
        inline.ifElse(line, self.attr('outputCurve')) >> output

        if replaceOutputs:
            for dest in existingOutputs:
                output >> dest

        return output