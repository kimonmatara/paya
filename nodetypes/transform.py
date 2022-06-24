import maya.cmds as m
import paya.config as config
import pymel.util as _pu
from paya.util import short
import paya.runtime as r


class Transform:

    #--------------------------------------------------------|    Constructor

    @classmethod
    @short(
        dagPath='dp',
        name='n',
        rotateOrder='ro',
        worldMatrix='wm'
    )
    def create(
            cls,
            dagPath=None,
            name=None,
            under=None,
            displayLocalAxis=False,
            rotateOrder='xyz',
            worldMatrix=None
    ):
        """
        Creates transform nodes.

        :param dagPath/dp: an explicit DAG path; if provided, the minimum
            number of nodes required to match this DAG path will be
            generated; ``displayLocalAxis``, ``rotateOrder`` and
            ``worldMatrix`` will only be applied to the last (innermost)
            group; defaults to None
        :type dagPath/dp: None, str
        :param name/n: one or more name elements; ignored if ``dagPath`` is
            provided; defaults to None
        :type name/n: int, str, list, tuple or None
        :param under/u: an optional parent for the transform; if this is
            combined with ``dagPath``, then this node's DAG path will be
            prepended; defaults to None
        :type under/u: None, str, :class:`~paya.nodetypes.transform.Transform`
        :param bool displayLocalAxis/dla: display the transform's local axes;
            defaults to False
        :param rotateOrder/ro: the transform's rotate order; defaults to 'xyz'
        :type rotateOrder/ro: int, str or None
        :param worldMatrix/wm: an optional world matrix for the transform,
            applied to the SRT channels; defaults to None
        :type worldMatrix/wm: None, list, tuple or
            :class:`~paya.datatypes.matrix.Matrix`
        :return: The transform.
        :rtype: :class:`~paya.nodetypes.transform.Transform`
        """
        if dagPath:
            fromRoot = dagPath.startswith('|')
            dagPath = dagPath.strip('|')

            if under:
                under = r.PyNode(under)
                head = under.name(long=True)

                if dagPath.startswith('|'):
                    dagPath = dagPath[1:]

                dagPath = head + dagPath

            elems = dagPath.split('|')
            num = len(elems)

            group = None
            coveredDepth = 0

            for i in reversed(range(num)):
                theseElems = elems[:i+1]
                thisDagPath = '|'.join(theseElems)

                if fromRoot:
                    thisDagPath = '|' + thisDagPath

                matches = r.ls(thisDagPath)

                if matches:
                    group = matches[0]
                    coveredDepth = i+1
                    break

            for i in range(coveredDepth, num):
                requiredElem = elems[i]

                kwargs = {}

                if group:
                    kwargs['parent'] = group

                group = r.group(empty=True, name=requiredElem, **kwargs)

        else:
            name = cls.makeName(n=name)
            group = r.group(empty=True, n=name)

        if worldMatrix:
            group.setMatrix(worldMatrix)

        if under:
            group.setParent(under)

        if displayLocalAxis:
            group.attr('displayLocalAxis').set(True)

        group.attr('ro').set(rotateOrder)

        return group

    #--------------------------------------------------------|    Attr management

    def releaseSRT(self):
        """
        Unlocks and disconnects every SRT channel, recursively.

        :return: ``self``
        """
        for channel in ['translate', 'rotate', 'scale', 'shear']:
            self.attr(channel).release(recursive=True)

        return self

    #--------------------------------------------------------|    Sampling

    @short(plug='p', useLocatorShape='uls')
    def getWorldPosition(self, plug=False, useLocatorShape=True):
        """
        Returns the world translation of this transform. Pivots are ignored.

        :shorthand: ``gwp``
        :param bool plug/p: return an attribute instead of a value; if
            'useLocatorShape' is True then, where available, the locator
            shape's 'worldPosition' attribute will be returned; otherwise,
            a 'worldPosition' attribute will be retrieved, or initialised,
            on the transform itself, with its input configured as self.t ^
            self.pm[0]; defaults to False
        :param bool useLocatorShape/uls: True
        :return: The position attribute or value.
        :rtype: :class:`~paya.datatypes.point.Point` or
            :class:`~paya.plugtypes.vector.Vector`
        """
        if plug:
            if useLocatorShape:
                locatorShapes = self.getChildren(type='locator')

                if locatorShapes:
                    return locatorShapes[0].attr('worldPosition')

            if not self.hasAttr('worldPosition', checkShape=False):
                self.addAttr('worldPosition', at='double3', nc=3)

                for axis in 'XYZ':
                    self.addAttr('worldPosition'+axis,
                        at='doubleLinear', parent='worldPosition')

            attr = self.attr('worldPosition')

            if not attr.inputs():
                input = self.attr('t') ^ self.attr('pm')[0]
                input >> attr

            return attr

        return r.data.Point(r.xform(self, q=True, t=True, a=True, ws=True))

    gwp = getWorldPosition

    @short(plug='p')
    def getWorldMatrix(self, plug=False):
        """:param bool plug/p: return a plug instead of a value; defaults to
            False
        :return: The world matrix of this transform, as a value or plug.
        :rtype: :class:`paya.datatypes.matrix.Matrix` or
            :class:`paya.plugtypes.matrix.Matrix`
        """
        if plug:
            return self.attr('wm')

        return self.getMatrix(worldSpace=True)

    gwm = getWorldMatrix

    @short(plug='p')
    def getRotateAxisMatrix(self, plug=False):
        """
        Returns the rotate axis as a rotation matrix.

        :param bool plug/p: return an attribute instead of a value; this will
            be cooked only once, and afterwards retrieved via a
            'rotateAxisMatrix' attribute on the node; defaults to False
        :return: The rotate axis matrix.
        :rtype: :class:`paya.datatypes.matrix.Matrix` or
            :class:`paya.plugtypes.matrix.Matrix`
        """
        if plug:
            attrName = 'rotateAxisMatrix'

            if not self.hasAttr(attrName):
                self.addAttr(attrName, at='matrix')

            attr = self.attr(attrName)

            if not attr.inputs():
                self.attr('rotateAxis').asRotateMatrix() >> attr

            return attr

        return self.attr('rotateAxis').get().asRotateMatrix()

    #--------------------------------------------------------|    Offset groups

    def createOffsetGroups(self, *suffixes):
        """
        :param \*suffixes: one or more offset group suffixes; defaults to
            'offset'
        :type \*suffixes: list, tuple, str
        :return: One or more transformationally-matched offset groups for this
            transform, in order of innermost to outermost.
        :type: list of :class:`~paya.nodetypes.transform.Transform`
        """
        suffixes = _pu.expandArgs(*suffixes)

        if not suffixes:
            suffixes = ['offset']

        bn = self.basename(sts=True, sns=True)

        mtx = self.getMatrix(worldSpace=True)
        ro = self.attr('rotateOrder').get()

        lastChild = self

        out = []

        with config(inheritNames=False):
            for suffix in suffixes:
                name = r.nodes.Transform.makeName(bn, suffix)
                parent = lastChild.getParent()
                kwargs = {}

                if parent is not None:
                    kwargs['parent'] = parent

                group = r.group(empty=True, n=name, **kwargs)
                group.setMatrix(mtx, worldSpace=True)
                lastChild.setParent(group)
                out.append(group)

        return out

    #--------------------------------------------------------|    Shapes

    def conformShapeNames(self):
        """
        Conforms the names of this transform's shape children to the Maya
        convention. Intermediate shapes are ignored, except where renaming
        them is needed to enforce logical numbering amongst the non-
        intermediate ones.

        :return: ``self``
        :rtype: :class:`~paya.nodetypes.transform.Transform`
        """
        visibleShapes = []
        intermShapes = []

        for shape in self.getShapes():
            if shape.isIntermediate():
                intermShapes.append(shape)
            else:
                visibleShapes.append(shape)

        origIntermShapeNames = [
            intermShape.basename() for intermShape in intermShapes]

        for shape in visibleShapes + intermShapes:
            shape.rename('tempName')

        bn = self.basename()

        for i, shape in enumerate(visibleShapes):
            name = bn + 'Shape'

            if i > 0:
                name += str(i)

            shape.rename(name)

        for shape, origName in zip(intermShapes, origIntermShapeNames):
            shape.rename(origName)

        return self