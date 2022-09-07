import maya.cmds as m
import paya.config as config
import pymel.util as _pu

from paya.util import short, resolveFlags
from paya.lib.controlshapes import controlShapes
import paya.runtime as r


class Transform:

    #--------------------------------------------------------|    Constructor

    @classmethod
    @short(
        dagPath='dp',
        name='n',
        rotateOrder='ro',
        worldMatrix='wm',
        parent='p',
        displayLocalAxis='dla'
    )
    def create(
            cls,
            dagPath=None,
            name=None,
            parent=None,
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
        :param str name/n: the node name; defaults to ``None``
        :param parent/p: an optional parent for the transform; if this is
            combined with ``dagPath``, then this node's DAG path will be
            prepended; defaults to None
        :type parent/p: None, str, :class:`~paya.runtime.nodes.Transform`
        :param bool displayLocalAxis/dla: display the transform's local axes;
            defaults to False
        :param rotateOrder/ro: the transform's rotate order; defaults to 'xyz'
        :type rotateOrder/ro: int, str or None
        :param worldMatrix/wm: an optional world matrix for the transform,
            applied to the SRT channels; defaults to None
        :type worldMatrix/wm: None, list, tuple or
            :class:`~paya.runtime.data.Matrix`
        :return: The transform.
        :rtype: :class:`~paya.runtime.nodes.Transform`
        """
        if dagPath:
            fromRoot = dagPath.startswith('|')
            dagPath = dagPath.strip('|')

            if parent:
                parent = r.PyNode(parent)
                head = parent.name(long=True)

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
            kwargs = {}

            if parent:
                kwargs['parent'] = parent

            group = r.group(empty=True, n=name if name else cls.makeName(), **kwargs)

        if worldMatrix:
            group.setMatrix(worldMatrix, worldSpace=True)

        if displayLocalAxis:
            group.attr('displayLocalAxis').set(True)

        group.attr('ro').set(rotateOrder)

        return group

    @classmethod
    @short(name='n',
           parent='p',
           shape='sh',
           size='siz',
           color='col',
           worldMatrix='wm',
           keyable='k',
           channelBox='cb',
           rotateOrder='ro',
           asControl='ac',
           offsetGroups='og',
           pickWalkParent='pwp',
           lineWidth='lw')
    def createControl(cls,
                      name=None,
                      parent=None,
                      shape='cube',
                      size=1.0,
                      color=None,
                      worldMatrix=None,
                      keyable=None,
                      channelBox=None,
                      rotateOrder='xyz',
                      asControl=True,
                      offsetGroups='offset',
                      pickWalkParent=None,
                      lineWidth=None):

        """
        Creates rig controls. Also available directly on :mod:`paya.runtime`.

        :param str name/n: an optional explicit name for the control; defaults
            to a contextual name
        :param parent/p: an optional parent for the control; defaults to None
        :type parent/p: None, str, :class:`~paya.runtime.nodes.Transform`
        :param str shape/sh: the name of a library shape to apply to the control;
            defaults to 'cube'
        :param color/col: an optional override color index for the control;
            defaults to None
        :type color/col: int, None
        :param float size: a uniform scaling factor for the control shape;
            defaults to 1.0
        :param worldMatrix/wm: the world matrix for the control; if this is
            omitted then, if *parent* is provided, the matrix is copied from the
            destination parent; otherwise, it defaults to the identity matrix
        :type worldMatrix/wm: list, :class:`~paya.runtime.data.Matrix`, None
        :param list keyable/k: a list of channels to set to keyable on the
            control
        :param list channelBox/cb: a list of channels to set to settable on the
            control
        :param rotateOrder/ro: the control's rotate order; defaults to 'xyz'
        :type rotateOrder/ro: str, int
        :param bool asControl/ac: if this is ``False``, create the control as a
            group with no shapes and omit the controller tag; defaults to True
        :param offsetGroups: the suffixes of one or more offset groups to create;
            defaults to 'offset'
        :type offsetGroups: list, str
        :param pickWalkParent/pwp: an optional pick-walk parent for this control;
            ignored if *asControl* is False; defaults to None
        :type pickWalkParent/pwp: str,
            :class:`~paya.runtime.nodes.DependNode`
        :param float lineWidth/lw: an override for the control shapes' line
            width; defaults to None
        :return: The generated control.
        :rtype: :class:`~paya.runtime.nodes.Transform`
        """

        kwargs = {}

        kwargs['name'] = name if name else r.Name.make(
            control=asControl,
            nodeType=None if asControl else 'transform'
        )

        if parent is not None:
            kwargs['parent'] = parent

        ct = r.group(empty=True, **kwargs)

        ct.setMatrix(worldMatrix, worldSpace=True)
        ct.attr('rotateOrder').set(rotateOrder)

        ct.createOffsetGroups(offsetGroups)
        ct.maskAnimAttrs(k=keyable, cb=channelBox)

        if asControl:
            ct.isControl(True)

            if shape:
                ct.setCtShapesFromLib(shape, lw=lineWidth)

            if size != 1.0:
                ct.scaleCtShapes([size]*3)

            if color is not None:
                ct.colorCtShapes(color)

            if pickWalkParent:
                ct.setPickWalkParent(pickWalkParent)

        return ct

    #--------------------------------------------------------|    Shape / transform management

    def toShape(self):
        """
        :return: If this node is a transform, its first shape child;
            otherwise, the node itself.
        :rtype: :class:`~paya.runtime.nodes.Shape` or
            :class:`~paya.runtime.nodes.Transform`
        """
        return self.getShape()

    def toTransform(self):
        """
        :return: If this node is a shape, its parent; otherwise, the node
            itself.
        :rtype: :class:`~paya.runtime.nodes.Shape` or
            :class:`~paya.runtime.nodes.Transform`
        """
        return self

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

    def closestOf(self, elems):
        """
        Returns the closest amongst 'elems' to this transform.

        :param elems: a list of Python objects that, when instantiated into
            PyNodes, implement ``getWorldPosition()``
        :return: The closest amongst 'elems'.
        """
        thisPosition = self.getWorldPosition()

        bestDistance = None
        bestIndex = None

        for i, elem in enumerate(elems):
            if not isinstance(elem, r.PyNode):
                elem = r.PyNode(elem)

            targetPosition = elem.getWorldPosition()
            vec = targetPosition - thisPosition
            distance = vec.length()

            if bestDistance is None or distance < bestDistance:
                bestDistance = distance
                bestIndex = i

        return list(elems)[bestIndex]

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
        :rtype: :class:`~paya.runtime.data.Point` or
            :class:`~paya.runtime.plugs.Vector`
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
        :rtype: :class:`paya.runtime.data.Matrix` or
            :class:`paya.runtime.plugs.Matrix`
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
        :rtype: :class:`paya.runtime.data.Matrix` or
            :class:`paya.runtime.plugs.Matrix`
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

    def makeIdentity(self, **kwargs):
        """
        Convenience wrapper for :func:`pymel.internal.pmcmds.makeIdentity`.

        :param \*\*kwargs: passed along to
            :func:`pymel.internal.pmcmds.makeIdentity`.
        :return: ``self``
        :rtype: :class:`~paya.runtime.nodes.Transform`
        """
        r.makeIdentity(self, **kwargs)
        return self

    #--------------------------------------------------------|    Offset groups

    def createOffsetGroups(self, *descriptors):
        """
        Creates transformationally-matched offset ('zero') groups.

        :param \*descriptors: base names for the offset groups, from
            innermost to outermost; if omitted, defaults to ``'offset'``
        :type \*descriptors: :class:`str`, [:class:`str`]
        :return: The offset groups, from innermost to outermost.
        :rtype: [:class:`Transform`]
        """
        # Wrangle names
        descriptors = _pu.expandArgs(*descriptors)

        if (len(descriptors) is 1 \
            and descriptors[0] is None) or not descriptors:
            descriptors = ['offset']

        bn = self.basename(sns=True, sts=True, sdp=True)

        # Prep details
        mtx = self.getMatrix(worldSpace=True)
        ro = self.attr('rotateOrder').get()

        # Iterate
        lastChild = self
        out = []

        for descriptor in descriptors[::-1]:
            with r.Name(bn, descriptor, inherit=False):
                parent = lastChild.getParent()
                kwargs = {}

                if parent is not None:
                    kwargs['parent'] = parent

                group = r.group(empty=True,
                                name=r.nodes.Transform.makeName(),
                                **kwargs)

                group.setMatrix(mtx, worldSpace=True)
                lastChild.setParent(group)
                out.append(group)

        return out[::-1]

    #--------------------------------------------------------|    Shapes

    @short(
        includeIntermediateShapes='iis',
        shapeList='shl'
    )
    def conformShapeNames(self,
                          includeIntermediateShapes=False,
                          shapeList=None):
        """
        Conforms the names of this transform's shape children to the Maya
        convention.

        :param bool includeIntermediateShapes/iis: process intermediate shapes
            as well
        :param shapeList/shl: if this is provided, it will be used instead of
            scanning for the transform's children; defaults to None
        :type shapeList/shl: None, [str, :class:`~paya.runtime.nodes.Shape`]
        :return: ``self``
        :rtype: :class:`Transform`
        """
        bn = self.basename()
        ourShapes = self.getShapes(noIntermediate=False)

        # Determine worklist
        if shapeList:
            worklist = []
            shapeList = _pu.expandArgs(shapeList)

            for member in shapeList:
                member = r.PyNode(member)

                if isinstance(member, r.nodetypes.Shape):
                    if member.hasParent(self):
                        if not(
                                (not includeIntermediateShapes) \
                                and member.isIntermediate):
                            worklist.append(member)
                    else:
                        raise RuntimeError(
                            "Not a child of {}: {}".format(self, member)
                        )

                else:
                    raise TypeError(
                        "Not a shape: {}".format(member)
                    )

        else:
            if includeIntermediateShapes:
                mainShapes = []
                intermShapes = []

                for shape in ourShapes:
                    if shape.isIntermediate():
                        intermShapes.append(shape)

                    else:
                        mainShapes.append(shape)

                worklist = mainShapes + intermShapes

            else:
                worklist = [shape for shape in \
                    ourShapes if not shape.isIntermediate()]

        # Rename all nodes in worklist to gibberish temporarily
        for node in worklist:
            node.rename('gibberish')

        unprocessedNodes = set(ourShapes)-set(worklist)
        reservedNames = [unprocessedNode.basename(
            ) for unprocessedNode in unprocessedNodes]

        # Iterate
        for node in worklist:
            count = 0

            while True:
                name = '{}Shape'.format(bn)

                if count:
                    name += str(count)

                if name in reservedNames:
                    count += 1
                    continue

                reservedNames.append(name)
                break

            node.rename(name)

        return self

    #--------------------------------------------------------|    General shape utils

    def getHeroShapes(self):
        """
        :return: All non-intermediate shapes under this transform.
        :rtype: [:class:`~paya.runtime.nodes.Shape`]
        """
        return self.getShapes(noIntermediate=True)

    def getIntermediateShapes(self):
        """
        :return: All intermediate shapes under this transform.
        :rtype: [:class:`~paya.runtime.nodes.Shape`]
        """
        return [shape for shape in self.getShapes(
            noIntermediate=False) if shape.isIntermediate()]

    #--------------------------------------------------------|    Control Shapes

    def _getCurveComponents(self):
        curves = self.getShapes(type='nurbsCurve', noIntermediate=True)

        out = []

        for curve in curves:
            out += list(curve.comp('cv'))

        return out

    def getCtShapes(self):
        """
        :return: Non-intermediate curve and locator shapes under this transform.
        :rtype: [:class:`~paya.runtime.nodes.NurbsCurve` or
            :class:`~paya.runtime.nodes.Locator`]
        """
        shapes = self.getShapes(type='nurbsCurve', noIntermediate=True)
        shapes += self.getShapes(type='locator', noIntermediate=True)

        return shapes

    def rotateCtShapes(self, rotation):
        """
        Rotates control shapes in local space. Locator shapes won't be rotated,
        but their ``localPosition`` will. Note that rotation is expected in
        degrees.

        :param rotation: an iterable of three rotation values, in degrees
        :type rotation: list, tuple, :class:`~pymel.core.datatypes.Array`
        :return: ``self``
        """
        curveComponents = self._getCurveComponents()
        locators = self.getShapes(noIntermediate=True, type='locator')

        if curveComponents or locators:
            if isinstance(rotation, r.data.EulerRotation):
                unit = rotation.unit

            else:
                unit = 'degrees'

            rotation = list(rotation)

            if unit == 'radians':
                rotation = list(map(_pu.degrees, rotation))

            rotationMtx = r.data.EulerRotation(
                rotation, unit='degrees').asMatrix()

            for curveComponent in curveComponents:
                point = r.pointPosition(curveComponent, local=True)
                point ^= rotationMtx

                r.move(curveComponent, point, ls=True, a=True)

            for locator in locators:
                localPosition = r.data.Point(
                    locator.attr('localPosition').get())

                localPosition ^= rotationMtx
                locator.attr('localPosition').set(localPosition)

        return self

    def scaleCtShapes(self, scale):
        """
        Scales control shapes in local space.

        :param scale: an iterable of three scale values
        :type scale: list, tuple, :class:`~pymel.core.datatypes.Array`
        :return: ``self``
        """
        curveComponents = self._getCurveComponents()
        locators = self.node().getShapes(noIntermediate=True, type='locator')

        if curveComponents:
            scaleMtx = r.data.Vector(scale).asScaleMatrix()

            for curveComponent in curveComponents:
                point = r.pointPosition(curveComponent, local=True)
                point ^= scaleMtx

                r.move(curveComponent, point, ls=True, a=True)

        for locator in locators:
            scale = p.datatypes.Array(scale)
            localScale = p.datatypes.Array(locator.attr('localScale').get())
            newScale = localScale * scale
            locator.attr('localScale').set(newScale)
        curveComponents = self._getCurveComponents()
        locators = self.getShapes(noIntermediate=True, type='locator')

        if curveComponents:
            scaleMtx = r.data.Vector(scale).asScaleMatrix()

            for curveComponent in curveComponents:
                point = r.pointPosition(curveComponent, local=True)
                point ^= scaleMtx

                r.move(curveComponent, point, ls=True, a=True)

        for locator in locators:
            scale = p.datatypes.Array(scale)
            localScale = p.datatypes.Array(locator.attr('localScale').get())
            newScale = localScale * scale
            locator.attr('localScale').set(newScale)

        return self

    @short(lineWidth='lw')
    def setCtShapesFromLib(self, libKey, lineWidth=None):
        """
        Sets control shapes to the named library entry.

        :param str name: the name of the library entry, e.g. 'cube'
        :param float lineWidth/lw: an override for the line width;
            defaults to None
        :return: The newly-generated control shapes.
        :rtype: list of :class:`~paya.runtime.nodes.Shape`
        """
        controlShapes.applyToControls(libKey, [self], lw=lineWidth)

    @short(backward='back')
    def cycleCtShapes(self, backward=False):
        """
        Steps through the library alphabetically and applies a different shape
        on each invocation. Useful for trying out different shapes quickly.

        :param bool backward/back: cycle backwards instead of forwards;
            defaults to False
        :return: The newly-generated control shapes.
        :rtype: list of :class:`~paya.runtime.nodes.Shape`
        """
        libKeys = list(sorted(controlShapes.keys()))
        maxIndex = len(libKeys) - 1
        currentKey = None

        for shape in self.getCtShapes():
            try:
                currentKey = shape.attr('libCtrlShape').get()

            except r.MayaAttributeError:
                continue

        if currentKey:
            try:
                currentKeyIndex = libKeys.index(currentKey)

                if backward:
                    newKeyIndex = currentKeyIndex - 1

                    if newKeyIndex < 0:
                        newKeyIndex = maxIndex

                else:
                    newKeyIndex = currentKeyIndex + 1

                    if newKeyIndex > maxIndex:
                        newKeyIndex = 0

            except:
                newKeyIndex = 0

        else:
            newKeyIndex = 0

        newKey = libKeys[newKeyIndex]
        print(newKey)
        return self.setCtShapesFromLib(newKey)

    def clearCtShapes(self):
        """
        Removes all non-intermediate curve or locator shapes under this
        transform.

        :return: ``self``
        :rtype: :class:`~paya.runtime.nodes.Transform`
        """
        for shape in self.getCtShapes():
            try:
                r.delete(shape)

            except:
                pass

        return self

    @short(clearOverrides='co')
    def colorCtShapes(self, *colorIndex, clearOverrides=True):
        """
        :param \*colorIndex: if a color index is provided, it is used to set
            the override color on all control shapes; if ``None`` is passed,
            override colors are reset; if the argument is omitted, the first-
            encountered override color index is returned
        :type \*colorIndex: int or None
        :param bool clearOverrides/co: used only if *colorIndex* was set to
            ``None``; set ``overrideEnabled`` to False as well; defaults to
            True
        :return: If *colorIndex* was provided, ``self`` is returned;
            otherwise, a color index.
        :rtype: :class:`~paya.runtime.nodes.Transform` or int
        """
        shapes = self.getCtShapes()

        if len(colorIndex):
            colorIndex = colorIndex[0]

            if colorIndex is None:
                shape.attr('overrideColor').set(0)

                if clearOverrides:
                    shape.attr('overrideEnabled').set(False)

            for shape in shapes:
                shape.attr('overrideEnabled').set(True)
                shape.attr('overrideColor').set(colorIndex)

            return self

        else:
            for shape in shapes:
                if shape.attr('overrideEnabled').get():
                    return shape.attr('overrideColor').get()

    @staticmethod
    def _getCtShapesConfig(shapes, tmplock=False):
        out = {}

        for shape in shapes:
            if shape.attr('overrideEnabled').get():
                out['color'] = shape.attr('overrideColor').get()
                break

            if isinstance(shape, r.nodetypes.NurbsCurve):
                lw = shape.attr('lineWidth').get()

                if lw > 0.0:
                    out['lineWidth'] = lw
                    break

        if 'color' not in out:
            out['color'] = None

        for shape in shapes:
            inputs = shape.attr('v').inputs(plugs=True)

            if inputs:
                out['vis'] = inputs[0]

                if tmplock:
                    inputs[0].node().lock()

                break

        return out

    @staticmethod
    def _applyCtShapesConfig(config, shapes):
        if 'vis' in config:
            for shape in shapes:
                try: config['vis'] >> shape.attr('v')
                except: pass

            config['vis'].node().unlock()

        if 'lineWidth' in config:
            for shape in shapes:
                if isinstance(shape, r.nodetypes.NurbsCurve):
                    shape.attr('lineWidth').set(config['lineWidth'])

        color = config['color']

        if color is None:
            for shape in shapes:
                try: shape.attr('overrideEnabled').set(False)
                except: pass

                try: shape.attr('overrideColor').set(0)
                except: pass

        else:
            for shape in shapes:
                try: shape.attr('overrideEnabled').set(True)
                except: pass

                try: shape.attr('overrideColor').set(config['color'])
                except: pass

    @short(
        replace='rep',
        worldSpace='ws',
        mirrorAxis='ma',
        color='col',
        shape='sh',
        lineWidth='lw'
    )
    def copyCtShapesTo(
            self,
            *destControls,
            replace=True,
            worldSpace=False,
            mirrorAxis=None,
            color=None,
            lineWidth=None,
            shape=None
    ):
        """
        Copies control shapes and / or color from this control to one or more
        destination controls. The 'shape' and 'color' flags can be defined by
        omission, Maya-style; for example, to copy only color, just pass
        ``col=True``, and 'shape' will be set to ``False`` automatically
        unless explicitly set.

        :param bool shape/sh: copy shapes; if this is ``False``, all other
            arguments except ``color`` are ignored
        :param bool color/col: copy color
        :param bool lineWidth/lw: copy line width
        :param \*destControls: one or more controls to copy shapes to
        :type \*destControls: list, str,
            :class:`~paya.runtime.nodes.Transform`
        :param bool replace/rep: remove existing shapes on the destination
            controls; defaults to True
        :param bool worldSpace/ws: copy shapes in world space; defaults to
            False
        :param mirrorAxis/ma: a positive axis to flip when copying in local
            space, or along which to mirror when copying in world space, for
            example 'x';  defaults to ``None``
        :type mirrorAxis/ma: ``None``, str
        :return: The new control shapes.
        :rtype: list of :class:`~paya.runtime.nodes.Shape`
        """
        destControls = list(map(r.PyNode, _pu.expandArgs(*destControls)))

        if destControls:
            shape, color, lineWidth = resolveFlags(shape, color, lineWidth)

            if not shape:
                if color:
                    col = self.colorCtShapes()

                    if col is not None:
                        for destControl in destControls:
                            destControl.colorCtShapes(col)

                if lineWidth:
                    srcLineWidth = self.getCtShapesLineWidth()

                    if srcLineWidth is not None:
                        for destControl in destControls:
                            destControl.setCtShapesLineWidth(srcLineWidth)

                return self

            # Prep main source

            _srcGp = r.group(empty=True)
            srcShapes = self.getCtShapes()

            if lineWidth:
                srcLineWidth = self.getCtShapesLineWidth()

            r.parent(srcShapes, _srcGp, r=True, shape=True, add=True)
            srcGp = _srcGp.duplicate()[0]
            r.delete(_srcGp)

            if mirrorAxis:
                mirrorMtx = r.createMatrix()

                setattr(mirrorMtx, mirrorAxis,
                    getattr(mirrorMtx, mirrorAxis)*-1.0)

            if worldSpace:
                matrix = self.getMatrix(worldSpace=True)

                if mirrorAxis:
                    matrix *= mirrorMtx

                srcGp.setMatrix(matrix)

            elif mirrorAxis:
                srcGp.setMatrix(mirrorMtx)
                r.makeIdentity(srcGp, apply=True, t=True, r=True, s=True)

            # Iterate

            newShapes = []

            for destControl in destControls:
                oldShapes = destControl.getCtShapes()
                config = self._getCtShapesConfig(oldShapes, tmplock=True)

                if color:
                    del(config['color'])

                if lineWidth:
                    try:
                        del(config['lineWidth'])

                    except KeyError:
                        pass

                if replace:
                    r.delete(oldShapes)

                thisSrcGp = srcGp.duplicate()[0]

                if worldSpace:
                    thisSrcGp.setParent(destControl)
                    r.makeIdentity(thisSrcGp,
                        apply=True, t=True, r=True, s=True)

                    thisSrcGp.setParent(None)

                theseNewShapes = thisSrcGp.getShapes()
                r.parent(theseNewShapes, destControl, r=True, shape=True)
                r.delete(thisSrcGp)

                self._applyCtShapesConfig(config, theseNewShapes)
                newShapes += theseNewShapes

                destControl.conformShapeNames()

            r.delete(srcGp)

            if lineWidth:
                if srcLineWidth is not None:
                    for shape in newShapes:
                        if isinstance(shape, r.nodetypes.NurbsCurve):
                            shape.attr('lineWidth').set(srcLineWidth)

            return newShapes

        else:
            return []

    def addCtShapesToLib(self, entryName):
        """
        Captures this control's shapes into a new library entry for reuse via
        :meth:`setCtShapes`.

        :param str entryName: the name of the new library entry
        :return: ``self``
        :rtype: :class:`~paya.runtime.nodes.Transform`
        """
        controlShapes.addFromControl(self, entryName)
        return self

    def getCtShapesLineWidth(self):
        """
        :return: The first encountered line width which is above 0.0
            (i.e. not the Maya default of -1.0), or None
        :rtype: float, None
        """
        for shape in self.getCtShapes():
            if isinstance(shape, r.nodetypes.NurbsCurve):
                lw = shape.attr('lineWidth').get()

                if lw > 0.0:
                    return lw

    def setCtShapesLineWidth(self, lineWidth):
        """
        Sets the line width on NURBS control shapes.

        :param lineWidth: the line width to set; if None is passed,
            the line width will be set to -1.0
        :type lineWidth: float, None
        :return: ``self``
        :rtype: :class:`Transform`
        """
        if lineWidth is None:
            lineWidth = -1.0

        for shape in self.getCtShapes():
            if isinstance(shape, r.nodetypes.NurbsCurve):
                shape.attr('lineWidth').set(lineWidth)

        return self