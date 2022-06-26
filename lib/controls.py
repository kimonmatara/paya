from collections import UserList, UserDict
import os
import json

import pymel.util as _pu
import pymel.core as p
from paya.util import short, LazyModule, AccessorOnNode, resolveFlags


r = LazyModule('paya.runtime')

#------------------------------------------------------------|    Constants

libpath = os.path.join(
    os.path.dirname(__file__),
    'ctrlshapes.json'
)

#------------------------------------------|    Shapes bundle for a single control

def _getShapesConfig(shapes, tmplock=False):
    out = {}

    for shape in shapes:
        if shape.attr('overrideEnabled').get():
            out['color'] = shape.attr('overrideColor').get()
            break

    for shape in shapes:
        inputs = shape.attr('v').inputs(plugs=True)

        if inputs:
            out['vis'] = inputs[0]

            if tmplock:
                inputs[0].node().lock()

            break

    return out

def _applyShapesConfig(config, shapes):
    if 'vis' in config:
        for shape in shapes:
            try: config['vis'] >> shape.attr('v')
            except: pass

        config['vis'].node().unlock()

    if 'color' in config:
        for shape in shapes:
            try: shape.attr('overrideEnabled').set(True)
            except: pass

            try: shape.attr('overrideColor').set(config['color'])
            except: pass

def getControlShapes(control):
    """
    :param control: the control to inspect
    :type control: str or :class:`~paya.nodetypes.transform.Transform`
    :return: Non-intermediate curve and locator shapes under the control.
    :rtype: [:class:`~paya.nodetypes.nurbsCurve.NurbsCurve` or
        :class:`~paya.nodetypes.locator.Locator`]
    """
    control = p.PyNode(control)

    shapes = control.getShapes(type='nurbsCurve', noIntermediate=True)
    shapes += control.getShapes(type='locator', noIntermediate=True)

    return shapes

def getShapeMacroBundleFromControl(control):
    """
    :param control: The control to inspect.
    :type control: str, :class:`~paya.nodetypes.transform.Transform`
    :return: A list of macros for the non-intermediate curve and locator
        shapes under the specified control.
    :rtype: list of dict
    """
    control = p.PyNode(control)
    shapes = getControlShapes(control)

    return [shape.macro() for shape in shapes]

def normalizePoints(points):
    """
    Normalizes shape points so that they fit inside a unit cube.

    :param points: the points to normalize
    :type points: list
    :return: The normalized points.
    :rtype: list of :class:`~paya.datatypes.point.Point`
    """
    xVals = list(map(abs,[point[0] for point in points]))
    yVals = list(map(abs, [point[1] for point in points]))
    zVals = list(map(abs, [point[2] for point in points]))

    maxX = max(xVals)
    maxY = max(yVals)
    maxZ = max(zVals)

    maxFactor = max(maxX, maxY, maxZ)

    try:
        scaleFactor = 0.5 / maxFactor

    except ZeroDivisionError:
        scaleFactor = 1.0

    scaleMatrix = r.createMatrix()
    scaleMatrix.x *= scaleFactor
    scaleMatrix.y *= scaleFactor
    scaleMatrix.z *= scaleFactor

    return [r.data.Point(point) ^ scaleMatrix for point in points]

def normalizeMacro(macro):
    """
    In-place operation. Normalizes any point information inside *macro*.
    See :func:`normalizePoints`.

    :param dict macro: the macro to edit
    """
    nt = macro['nodeType']

    if nt == 'nurbsCurve':
        points = normalizePoints(macro['point'])
        points = list(map(list, points))
        macro['point'] = points

    else:
        point = macro['localPosition']
        point = normalizePoints([point])[0]
        macro['localPosition'] = list(point)

@short(replace='rep')
def applyShapeMacroBundleToControls(bundle, controls, replace=False):
    """
    Uses a list of macros to create shapes under a control. Existing
    colors and visibility inputs will be replicated.

    :param bundle: a list of control shape macros
    :type bundle: list of dict
    :param list controls: the controls to add shapes to
    :param bool replace/rep: delete existing shapes on the destination
        controls
    :return: list of :class:`~paya.nodetypes.shape.Shape`
    """
    # Create the source curves and locators

    sources = [
        r.nodes.DependNode.createFromMacro(macro
        ).getParent() for macro in bundle
    ]

    newShapes = []

    for control in controls:
        existing = getControlShapes(control)
        config = _getShapesConfig(existing, tmplock=True)

        if replace:
            r.delete(existing)

        _sources = r.duplicate(sources)

        theseNewShapes = []

        for _source in _sources:
            newShape = _source.getShape()
            r.parent(newShape, control, r=True, shape=True)
            theseNewShapes.append(newShape)

        r.delete(_sources)

        _applyShapesConfig(config, theseNewShapes)
        newShapes += theseNewShapes

        control.conformShapeNames()

    r.delete(sources)
    return newShapes


class NoControlShapesError(RuntimeError):
    """
    No shapes were found under the specified control(s).
    """

class ControlShapesLibrary(UserDict):

    #------------------------------------------------------|    Init

    __instance__ = None

    def __new__(cls, *args, **kwargs):
        if cls.__instance__ is None:
            cls.__instance__ = object.__new__(cls)

        return cls.__instance__

    def __init__(self):
        self.load()

    #------------------------------------------------------|    I/O

    def load(self):
        """
        Loads the library content fromn ``paya/lib/ctrlshapes.json``.

        :return: ``self``
        """
        try:
            with open(libpath, 'r') as f:
                data = f.read()

            data = json.loads(data)
            print("Control shapes read from: "+libpath)

        except IOError:
            r.warning("Missing control shapes library: "+libpath)
            data = {}

        self.data = data

        return self

    def dump(self):
        """
        Dumps the library content into ``paya/lib/ctrlshapes.json``.

        :return: ``self``
        """
        data = json.dumps(self.data)
        with open(libpath, 'w') as f:
            f.write(data)

        print("Control shapes saved into: "+libpath)

        return self

    #------------------------------------------------------|    Appying

    @short(replace='rep')
    def applyToControls(self, name, controls, replace=True):
        """
        Adds shapes to the specified controls from the named library entry.

        :param name: the name of the library entry to retrieve
        :param list controls: the controls to add shapes to
        :param bool replace/rep: replace existing shapes on the controls;
            defaults to True
        :return: The newly-generated control shape nodes.
        :rtype: list of :class:`~paya.nodetypes.shape.Shape`
        """
        macros = self[name]
        srcShapes = [
            r.nodes.DependNode.createFromMacro(macro) for macro in macros]

        for srcShape in srcShapes:
            srcShape.addAttr('libCtrlShape', dt='string').set(name)

        srcGp = r.group(empty=True)

        for srcShape in srcShapes:
            parent = srcShape.getParent()
            r.parent(srcShape, srcGp, r=True, shape=True)
            r.delete(parent)

        newShapes = srcGp.cs.copyTo(controls, color=False, rep=replace)
        r.delete(srcGp)

        return newShapes

    def addFromControl(self, control, name):
        """
        Captures shape macros from the specified control and adds them under
        a new entry in the library.

        .. warning::

            If the name already exists in the library, it will be overwritten.

        .. note::

            Changes are not saved into ``paya/lib/ctrlshapes.json`` until
            :meth:`~paya.lib.controls.ControlShapesLibrary.dump` is called.

        :param control: the control to inspect
        :type control: str, :class:`~paya.nodetypes.transform.Transform`
        :param str name: the name for the new entry
        :raises NoControlShapesError: no control shapes were found under the
            control
        :return: ``self``
        """
        control = r.PyNode(control)
        shapes = list(control.cs)

        if shapes:
            macros = [shape.macro() for shape in shapes]

            for macro in macros:
                normalizeMacro(macro)

            self[name] = macros

        else:
            raise NoControlShapesError

        return self

controlShapesLibrary = ControlShapesLibrary()


class ControlShapesManager(AccessorOnNode):
    """
    Implements the ``controlShapes`` / ``cs`` interface attribute on
    :class:`~paya.nodetypes.transform.Transform`.

    'Control shapes' comprise any non-intermediate curve or locator shape
    under a transform.

    -   To copy shapes and / or color, use :meth:`copyTo`.
    -   To transform shapes, use :meth:`rotate` and :meth:`scale`.
    -   To assign shapes from the library, use :meth:`setFromLib`.
    -   To save shapes *into* the library, use :meth:`addToLib`.
    -   To interactively cycle through shapes, call :meth:`cycle` repeatedly.
    """

    #--------------------------------------------------|    Member access

    def _getCurveComponents(self):
        out = []

        for shape in list(self):
            if shape.nodeType() == 'nurbsCurve':
                out += list(shape.comp('cv'))

        return out

    def __iter__(self):
        """
        :return: an iterator of non-intermediate curve and locator shapes
        :rtype: iterator of :class:`~paya.nodetypes.shape.Shape`
        """
        return iter(getControlShapes(self.node()))

    def __len__(self):
        """
        :return: the number of non-intermediate curve and locator shapes under
            this control
        :rtype: int
        """
        return len(getControlShapes(self.node()))

    def __getitem__(self, index):
        """
        :param index: the index of the non-intermediate curve or locator shape
            to retrieve
        :return: A non-intermediate curve or locator shape.
        :rtype: :class:`~paya.nodetypes.shape.Shape`
        """
        return list(self)[index]

    #--------------------------------------------------|    Copying

    @short(
        replace='rep',
        worldSpace='ws',
        mirrorAxis='ma',
        color='col',
        shape='sh'
    )
    def copyTo(
            self,
            *destControls,
            replace=True,
            worldSpace=False,
            mirrorAxis=None,
            color=None,
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
        :param \*destControls: one or more controls to copy shapes to
        :type \*destControls: list, str,
            :class:`~paya.nodetypes.transform.Transform`
        :param bool replace/rep: remove existing shapes on the destination
            controls; defaults to True
        :param bool worldSpace/ws: copy shapes in world space; defaults to
            False
        :param mirrorAxis/ma: a positive axis to flip when copying in local
            space, or along which to mirror when copying in world space, for
            example 'x';  defaults to ``None``
        :type mirrorAxis/ma: ``None``, str
        :return: The new control shapes.
        :rtype: list of :class:`~paya.nodetypes.shape.Shape`
        """
        color, shape = resolveFlags(color, shape)
        destControls = list(map(p.PyNode, _pu.expandArgs(*destControls)))

        if not destControls:
            raise RuntimeError("No destination controls specified.")

        if color and not shape: # Quick bail
            col = self.getColor()

            if col is not None:
                for destControl in destControls:
                    destControl.cs.setColor(col)

        if not shape:
            return self

        srcControl = self.node()

        # Prep main source

        _srcGp = p.group(empty=True)
        srcShapes = getControlShapes(srcControl)

        r.parent(srcShapes, _srcGp, r=True, shape=True, add=True)
        srcGp = _srcGp.duplicate()[0]
        r.delete(_srcGp)

        if mirrorAxis:
            mirrorMtx = r.createMatrix()

            setattr(mirrorMtx, mirrorAxis,
                    getattr(mirrorMtx, mirrorAxis)*-1.0)

        if worldSpace:
            matrix = srcControl.getMatrix(worldSpace=True)

            if mirrorAxis:
                matrix *= mirrorMtx

            srcGp.setMatrix(matrix)

        elif mirrorAxis:
            srcGp.setMatrix(mirrorMtx)
            r.makeIdentity(srcGp, apply=True, t=True, r=True, s=True)

        # Iterate

        newShapes = []

        for destControl in destControls:
            oldShapes = getControlShapes(destControl)
            config = _getShapesConfig(oldShapes, tmplock=True)

            if color:
                try:
                    del(config['color'])

                except KeyError:
                    pass

            if replace:
                r.delete(oldShapes)

            thisSrcGp = srcGp.duplicate()[0]

            if worldSpace:
                thisSrcGp.setParent(destControl)
                r.makeIdentity(thisSrcGp, apply=True, t=True, r=True, s=True)
                thisSrcGp.setParent(None)
                
            theseNewShapes = thisSrcGp.getShapes()
            r.parent(theseNewShapes, destControl, r=True, shape=True)

            r.delete(thisSrcGp)

            _applyShapesConfig(config, theseNewShapes)
            newShapes += theseNewShapes

            destControl.conformShapeNames()

        r.delete(srcGp)
        return newShapes

    #--------------------------------------------------|    Colour management

    def getColor(self):
        """
        :return: The ``overrideColor`` value of the first encountered shape
            with overrides enabled, or ``None`` if no shapes had overrides
            enabled.
        :rtype: NoneType or int
        """
        for shape in self:
            if shape.attr('overrideEnabled').get():
                return shape.attr('overrideColor').get()

    def setColor(self, index):
        """
        Sets ``overrideColor`` (by index) on all non-intermediate curve and
        locator shapes under this control.

        :param int index: the color index to apply
        :return: ``self``
        """
        for shape in self:
            shape.attr('overrideEnabled').set(True)
            shape.attr('overrideColor').set(index)

        return self

    def clearColor(self, disableOverrides=True):
        """
        Resets the override color on all control shapes.

        :param bool disableOverrides/dis: set ``overrideEnabled`` to False
            too; defaults to True
        :return: ``self``
        """
        for shape in self:
            shape.attr('overrideColor').set(0)

            if disableOverrides:
                shape.attr('overrideEnabled').set(False)

        return self

    #--------------------------------------------------|    Removals

    def clear(self):
        """
        Removes all control shapes.
        :return: ``self``
        """
        r.delete(list(self))
        return self

    def __delitem__(self, index):
        """
        :param int index: the index of the control shape to delete
        """
        items = self[index]
        r.delete(items)

    #--------------------------------------------------|    Transformations

    def scale(self, scale):
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

    def rotate(self, rotation):
        """
        Rotates control shapes in local space. Locator shapes won't be rotated,
        but their ``localPosition`` will. Note that rotation is expected in
        degrees.

        :param rotation: an iterable of three rotation values, in degrees
        :type rotation: list, tuple, :class:`~pymel.core.datatypes.Array`
        :return: ``self``
        """
        curveComponents = self._getCurveComponents()
        locators = self.node().getShapes(noIntermediate=True, type='locator')

        if curveComponents or locators:
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

    #--------------------------------------------------|    Library interfacing

    def setFromLib(self, name):
        """
        Sets control shapes to the named library entry.

        :param str name: the name of the library entry, e.g. 'cube'
        :return: The newly-generated control shapes.
        :rtype: list of :class:`~paya.nodetypes.shape.Shape`
        """
        return controlShapesLibrary.applyToControls(name, self.node())

    def addToLib(self, name, dump=True):
        """
        Captures control shapes into a library entry. If the library entry
        already exists it will be overwritten.

        :param str name: the name of the new library entry
        :param bool dump: write the shapes library to disk immediately;
            defaults to True
        :return: ``self``
        """
        controlShapesLibrary.addFromControl(self.node(), name)

        if dump:
            controlShapesLibrary.dump()

        return self

    @short(backward='back')
    def cycle(self, backward=False):
        """
        Steps through the library alphabetically and applies a different shape
        on each invocation. Useful for trying out different shapes quickly.

        :param bool backward/back: cycle backwards instead of forwards;
            defaults to False
        :return: The newly-generated control shapes.
        :rtype: list of :class:`~paya.nodetypes.shape.Shape`
        """
        libKeys = list(sorted(controlShapesLibrary.keys()))
        maxIndex = len(libKeys) - 1
        currentKey = None

        for shape in list(self):
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
        return self.setFromLib(newKey)

@short(
    name='n',
    under='u',
    shape='sh',
    size='sz',
    color='col',
    worldMatrix='wm',
    keyable='k',
    channelBox='cb',
    rotateOrder='ro',
    asControl='ac',
    offsetGroups='og',
    pickWalkParent='pwp'
)
def createControl(
        name=None,
        under=None,
        shape='cube',
        size=1.0,
        color=None,
        worldMatrix=None,
        keyable=None,
        channelBox=None,
        rotateOrder='xyz',
        asControl=True,
        offsetGroups='offset',
        pickWalkParent=None
):
    """
    Creates rig controls. Available on :mod:`paya.runtime`.

    :param name/n: one or more name elements
    :type name/n: None, str, int, list
    :param under/u: an optional parent for the control; defaults to None
    :type under/u: None, str, :class:`~paya.nodetypes.transform.Transform`
    :param str shape/sh: the name of a library shape to apply to the control;
        defaults to 'cube'
    :param color/col: an optional override color index for the control;
        defaults to None
    :type color/col: int, None
    :param float size/sz: a uniform scaling factor for the control shape;
        defaults to 1.0
    :param worldMatrix/wm: the world matrix for the control; if this is
        omitted then, if ``under`` is provided, the matrix is copied from the
        destination parent; otherwise, it defaults to the identity matrix
    :type worldMatrix/wm: list, :class:`~paya.datatypes.matrix.Matrix`, None
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
        :class:`~paya.nodetypes.dependNode.DependNode`
    :return: The generated control.
    :rtype: :class:`~paya.nodetypes.transform.Transform`
    """
    #--------------------------------------------------------|    Prep

    if under:
        under = r.PyNode(under)

    if worldMatrix:
        worldMatrix = r.data.Matrix(worldMatrix)

    else:
        if under:
            worldMatrix = under.getMatrix(worldSpace=True)

        else:
            worldMatrix = r.data.Matrix()

    #--------------------------------------------------------|    Build

    kwargs = {}

    if under is not None:
        kwargs['parent'] = under

    name = r.nodes.Transform.makeName(name, control=asControl)
    ct = r.group(empty=True, n=name, **kwargs)

    ct.setMatrix(worldMatrix, worldSpace=True)
    ct.attr('rotateOrder').set(rotateOrder)

    ct.createOffsetGroups(offsetGroups)
    ct.maskAnimAttrs(k=keyable, cb=channelBox)

    if asControl:
        ct.isControl(True)

        if shape:
            ct.controlShapes.setFromLib(shape)

        if size != 1.0:
            ct.controlShapes.scale([size] * 3)

        if color is not None:
            ct.controlShapes.setColor(color)

        if pickWalkParent:
            ct.setPickWalkParent(pickWalkParent)

    return ct