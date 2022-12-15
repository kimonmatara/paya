import paya.lib.typeman as _tm
import paya.lib.mathops as _mo
from paya.util import short
import maya.cmds as m
import paya.runtime as r


class NoMatchingSampleError(RuntimeError):
    """
    A matching sample wasn't found for the requested parameter.
    """


class CurveUpVectorSampler(r.networks.System):
    """
    Abstract base class for curve up vector samplers.
    """
    #-------------------------------------------------------|    Constructor

    @classmethod
    def create(cls, curve):
        """
        Not for direct use; called by the subclasses.

        :param curve: the curve on which to create the sampler
        :type curve: str, :class:`paya.runtime.nodes.NurbsCurve`,
            :class:`paya.runtime.nodes.Transform`,
            :class:`paya.runtime.plugs.NurbsCurve`
        :return: The network system.
        :rtype: :class:`CurveUpVectorSampler`
        """
        with r.NodeTracker() as track:
            node = cls._create(curve)

        node._tagDependencies(track.getNodes())

        return node

    @classmethod
    def _create(cls, curve):
        node = cls.createNode()
        node._tagCurve(curve)
        node._initSamplesAttr()
        return node

    #-------------------------------------------------------|    Partial construction

    def _tagDependencies(self, nodes):
        if not self.hasAttr('dependencies'):
            self.addAttr('dependencies', multi=True, at='message')

        arr = self.attr('dependencies')
        index = arr.getNextArrayIndex()

        for node in nodes:
            if node == self:
                continue

            node.attr('message') >> arr[index]
            index += 1

    def _tagCurve(self, curve):
        curve = _tm.asGeoPlug(curve, worldSpace=True)
        curve >> self.addAttr('curve', at='message')

    def _initSamplesAttr(self):
        self.addAttr('samples', multi=True, at='compound', nc=2)
        self.addAttr('parameter', parent='samples')
        self.addAttr('vector', at='double3', nc=3, parent='samples')

        for ax in 'XYZ':
            self.addAttr('vector'+ax, parent='vector')

        return self.attr('samples')

    #-------------------------------------------------------|    Basic inspections

    def remove(self):
        """
        Deletes this sampler system.
        """
        thisNode = str(self)
        nodes = [str(x) for x in self.getDependencies()]

        for node in nodes:
            try:
                m.delete(node)

            except:
                continue

        m.evalDeferred(
            "import maya.cmds as m\nif m.objExists('{}'):\n\tm.delete('{}')".format(
                thisNode, thisNode)
        )

    def getDependencies(self):
        """
        :return: All nodes, except this one, that were generated when this
            system was first created.
        :rtype: [:class:`~paya.runtime.nodes.DependNode``]
        """
        arr = self.attr('dependencies')
        indices = arr.getArrayIndices()
        out = []

        for index in indices:
            slot = arr[index]
            inputs = slot.inputs(plugs=True)

            if inputs:
                out.append(inputs[0].node())

        return out

    def curve(self):
        """
        :return: The curve output associated with this sampler system.
        :rtype: :class:`~paya.runtime.plugs.NurbsCurve`
        """
        out = self.attr('curve').inputs(plugs=True)

        if out:
            return out[0]

    def setAsDefault(self):
        """
        Makes this the default up vector source for the associated
        :meth:`curve output <curve>`.

        :return: ``self``
        :rtype: `CurveUpVectorSampler`
        """
        curve = self.curve()

        outputs = [output for output in curve.outputs(
            type='network', plugs=True) if output.attrName(
            ) == 'defaultFor' and output.node() != self]

        for output in outputs:
            output.disconnect(inputs=True)
            output.node().deleteAttr('defaultFor')

        if not self.hasAttr('defaultFor'):
            self.addAttr('defaultFor', at='message')

        curve >> self.attr('defaultFor')

        return self

    #-------------------------------------------------------|    Sampling

    def _findSample(self, param):
        arr = self.attr('samples')
        param, pdim, put, pisplug = _mo.info(param).values()
        indices = arr.getArrayIndices()

        for index in indices:
            compound = arr[index]
            thisParam = compound.attr('parameter')
            theseInputs = thisParam.inputs(plugs=True)

            if (theseInputs and pisplug):
                if theseInputs[0] == param:
                    return compound.attr('vector')

            elif ((not theseInputs) and (not pisplug)):
                if thisParam.get() == param:
                    return compound.attr('vector')

        raise NoMatchingSampleError(
            "No matching sample found for parameter {}.".format(param))

    @short(plug='p')
    @_tm.plugCheck('param')
    def sampleAtParam(self, param, plug=None):
        """
        :param param: the parameter to sample; if *plug* is ``False``, this
            must be a value
        :type param: float, str, :class:`~paya.runtime.plugs.Math1D`
        :param bool plug/p: force a dynamic output, or indicate that one or
            more of the arguments are plugs to skip checks; defaults to
            ``None``
        :return: A vector output or value for the specified parameter.
        :rtype: :class:`paya.runtime.data.Vector`,
            :class:`paya.runtime.plugs.Vector`
        """
        if plug:
            try:
                existing = self._findSample(param)
                return existing

            except NoMatchingSampleError:
                with r.NodeTracker() as tracker:
                    out = self._createLiveSample(param)

                self._tagDependencies(tracker.getNodes())
                return out

        return self._sampleAtParam(param, plug=False)

    def _createLiveSample(self, parameter):
        arr = self.attr('samples')
        index = arr.getNextArrayIndex()
        compound = arr[index]
        parameter >> compound.attr('parameter')

        with r.Name('sample', index+1, padding=3):
            self._sampleAtParam(compound.attr('parameter')
                                ) >> compound.attr('vector')

        return compound.attr('vector')

    def _sampleAtParam(self, param, plug=True):
        raise NotImplementedError("Not implemented on the base class.")
        # Example:
        # if plug:
        #     nw = r.nodes.Network.createNode()
        #     nw.addAttr('test', nc=3, at='double3')
        #
        #     for x in 'XYZ':
        #         nw.addAttr('test'+x, parent='test')
        #
        #     out = nw.attr('test')
        #     out.set([3, 4, 5])
        #
        #     return out
        #
        # return [3, 4, 5]