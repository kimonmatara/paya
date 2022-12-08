from collections import UserDict
import os
import json

import maya.cmds as m
import pymel.core as p
from paya.util import short, LazyModule, undefined, int_to_letter, pad
import pymel.util as _pu
from paya.config import config
import paya.lib.suffixes as _suf

r = LazyModule('paya.runtime')

#----------------------------------------------------------------|
#----------------------------------------------------------------|    CONTROL SHAPES
#----------------------------------------------------------------|

#------------------------------------------------------------|    Constants

libpath = os.path.join(
    os.path.dirname(__file__),
    'controlshapes.json'
)

class NoControlShapesError(RuntimeError):
    """
    No shapes were found under the specified control(s).
    """

class ControlShapesLibrary(UserDict):
    """
    Administers Paya control shapes. An instance of this class is available
    on :mod:`paya.runtime` as ``.controlShapes``.
    """

    #------------------------------------------------------|    Init

    def __init__(self, filepath):
        self.filepath = filepath
        self.data = {}

    #------------------------------------------------------|    I/O

    def load(self):
        """
        Loads the library content fromn ``paya/lib/controlshapes.json``.

        :return: ``self``
        """
        try:
            with open(self.filepath, 'r') as f:
                data = f.read()

            data = json.loads(data)
            print("Control shapes read from: "+self.filepath)

        except IOError:
            r.warning("Missing control shapes library: "+self.filepath)
            data = {}

        self.data = data

        return self

    def dump(self):
        """
        Dumps the library content into ``paya/lib/controlshapes.json``.

        :return: ``self``
        """
        data = json.dumps(self.data)
        with open(self.filepath, 'w') as f:
            f.write(data)

        print("Control shapes saved into: "+self.filepath)

        return self

    #------------------------------------------------------|    Appying

    @short(replace='rep',
           lineWidth='lw')
    def applyToControls(self,
                        name,
                        controls,
                        replace=True,
                        lineWidth=None):
        """
        Adds shapes to the specified controls from the named library entry.

        :param name: the name of the library entry to retrieve
        :param list controls: the controls to add shapes to
        :param bool replace/rep: replace existing shapes on the controls;
            defaults to True
        :param float lineWidth/lw: an override for the line width; defaults
            to None
        :return: The newly-generated control shape nodes.
        :rtype: list of :class:`~paya.runtime.nodes.Shape`
        """
        macros = self[name]
        hasColor = any(['overrideColor' in macro for macro in macros])

        srcShapes = [
            r.nodes.DependNode.createFromMacro(macro) for macro in macros]

        if lineWidth is not None:
            for srcShape in srcShapes:
                if isinstance(srcShape, p.nodetypes.NurbsCurve):
                    srcShape.attr('lineWidth').set(lineWidth)

        for srcShape in srcShapes:
            srcShape.addAttr('libCtrlShape', dt='string').set(name)

        srcGp = r.group(empty=True)

        for srcShape in srcShapes:
            parent = srcShape.getParent()
            r.parent(srcShape, srcGp, r=True, shape=True)
            r.delete(parent)

        newShapes = srcGp.copyCtShapesTo(
            controls,
            color=hasColor,
            lineWidth=lineWidth is not None,
            shape=True,
            rep=replace
        )

        r.delete(srcGp)

        return newShapes

    @short(normalize='nr')
    def addFromControl(self, control, name,
                       normalize=True, includeShapeDetails=False):
        """
        Captures shape macros from the specified control and adds them under
        a new entry in the library.

        .. warning::

            If the name already exists in the library, it will be overwritten.

        .. note::

            Changes are not saved into ``paya/lib/controlshapes.json`` until
            :meth:`~paya.lib.controls.ControlShapesLibrary.dump` is called.

        :param control: the control to inspect
        :type control: str, :class:`~paya.runtime.nodes.Transform`
        :param str name: the name for the new entry
        :param bool normalize/nr: normalize points into a unit; defaults
            to ``True``
        :param bool includeShapeDetails: include information on override color
            and visibility inputs; defaults to ``False``
        :raises NoControlShapesError: no control shapes were found under the
            control
        :return: ``self``
        """
        control = r.PyNode(control)
        shapes = control.getCtShapes()

        if shapes:
            macros = []

            for shape in shapes:
                macro = shape.macro(includeShapeDetails=includeShapeDetails)
                if normalize:
                    shape.normalizeMacro(macro)
                macros.append(macro)

            self[name] = macros

        else:
            raise NoControlShapesError

        return self

    #------------------------------------------------------|    Repr

    def __repr__(self):
        return "{}('{}')".format(type(self).__name__, self.filepath)

controlShapes = ControlShapesLibrary(libpath)
controlShapes.load()

def dumpControlShapes(filePath, controls=None):
    """
    Dumps an archive of control shapes to the specified JSON file path.

    :param controls: a list of scene controls to work from; if omitted,
        :func:`getControls` is used
    :type controls: [:class:`~paya.runtime.nodes.Transform`, :class:`str`]
    :param str filePath: The path to a JSON file.
    """
    lib = ControlShapesLibrary(filePath)

    if not controls:
        controls = getControls()

    for control in controls:
        lib.addFromControl(control,
                           control.basename(),
                           normalize=False,
                           includeShapeDetails=True)

    lib.dump()

def loadControlShapes(filePath, controls=None):
    """
    Loads an archive of control shapes from the specified JSON file path and
    applies them to controls in the scene.

    :param str filePath: The path to the JSON file.
    :param controls: a list of scene controls to work from; if omitted,
        information in the template itself is used
    """
    lib = ControlShapesLibrary(filePath)
    lib.load()

    if controls:
        namesToKeep = [str(control).split('|')[-1] for control in controls]
        namesToDelete = [key for key in lib if key not in namesToKeep]

        for name in namesToDelete:
            del(lib[name])

    for controlName in lib:
        targets = r.ls(controlName)

        if targets:
            print("ABout to apply from loadControlShapes().")
            lib.applyToControls(controlName, targets)
        else:
            print("No matches found for '{}', skipping.".format(controlName))


    print("Applied control shapes from: "+filePath)

#----------------------------------------------------------------|
#----------------------------------------------------------------|    CONTROL CONSTRUCTION
#----------------------------------------------------------------|

@short(
    worldMatrix='wm',
    keyable='k',
    channelBox='cb',
    rotateOrder='ro',
    offsetGroups='og',
    parent='p',
    pickWalkParent='pwp',
    shape='sh',
    shapeScale='ssc',
    color='col',
    asControl='ac'
)
def createControl(
        worldMatrix=None,

        keyable=None,
        channelBox=None,
        rotateOrder='xyz',

        offsetGroups='offset',
        parent=None,
        pickWalkParent=None,

        shape='cube',
        lineWidth=None,
        shapeScale=1.0,
        color=None,

        asControl=True
):
    """
    Creates an animation control.

    :param worldMatrix/wm: the initial pose matrix; if omitted, defaults to
        the identity matrix
    :type worldMatrix/wm: :class:`list`, :class:`tuple`,
        :class:`~paya.runtime.data.Matrix`
    :param keyable/k: a list of channel names to make keyable on the
        control; defaults to ``None``
    :type keyable/b: [:class:`str`]
    :param channelBox/cb: a list of channel names to make settable on the
        control; defaults to ``None``
    :type channelBox/cb: [:class:`str`]
    :param rotateOrder/ro: the rotate order for the controls; defaults to
        ``'xyz'``
    :type rotateOrder/ro: :class:`int`, :class:`str`
    :param offsetGroups/og: one or more basenames for offset groups;
        defaults to ``'offset'``
    :type offsetGroups/og: :class:`str`, [:class:`str`]
    :param parent/p: a destination parent for the topmost offset group
        (or the control itself, if no offset groups are requested);
        defaults to ``None``
    :type parent/p: :class:`~paya.runtime.nodes.Transform`, :class:`str`
    :param pickWalkParent/pwp: if omitted, defaults to ``parent``, but only if
        ``parent`` is itself a control, otherwise ``None``
    :type pickWalkParent/pwp: :class:`~paya.runtime.nodes.DependNode`,
        :class:`str`
    :param str shape/sh: the name of a library shape to apply to the control;
        defaults to ``'cube'``
    :param lineWidth/lw: an optonal override for the display curve thickness;
        defaults to ``None``
    :param float shapeScale/ssc: scaling factor for the control shape(s);
        defaults to ``1.0``
    :param color/col: a color for the control; this can be an index value,
        or one of the shorthands supported by
        :meth:`~paya.runtime.nodes.Transform.colorCtShapes`; defaults to
        ``None``
    :param bool asControl/ac: if this is ``False``, a simple group will be
        created instead of a visible control; defaults to ``True``
    :return: The animation control.
    :rtype: :class:`~paya.runtime.nodes.Transform`
    """
    kwargs = {'empty': True}

    if parent is not None:
        kwargs['parent'] = parent

        if pickWalkParent is None:
            if r.controller(parent, q=True):
                pickWalkParent = parent

    kwargs['name'] = r.Name.make(
        control=asControl,
        nodeType=None if asControl else 'transform'
    )

    ct = r.group(**kwargs)
    ct.attr('rotateOrder').set(rotateOrder)

    if worldMatrix is not None:
        ct.setMatrix(worldMatrix, worldSpace=True)

    if offsetGroups:
        ct.createOffsetGroups(offsetGroups)

    ct.maskAnimAttrs(k=keyable, cb=channelBox)

    if asControl:
        ct.isControl(True)

        if shape:
            ct.setCtShapesFromLib(shape, lw=lineWidth)

        if shapeScale != 1.0:
            ct.scaleCtShapes(shapeScale)

        if color is not None:
            ct.colorCtShapes(color)

    if pickWalkParent is not None:
        ct.setPickWalkParent(pickWalkParent)

    return ct

@short(
    numControls='nc',
    useLetters='let',
    numberFromFirstInset='nfi',
    addVisibilitySwitches='adv',
    insetScale='iss',

    worldMatrix='wm',
    keyable='k',
    channelBox='cb',
    rotateOrder='ro',
    offsetGroups='og',
    parent='p',
    pickWalkParent='pwp',
    shape='sh',
    shapeScale='ssc',
    color='col',
    asControl='ac'
)
def createControls(
        numControls=2,
        useLetters=True,
        insetScale=0.8,
        numberFromFirstInset=False,
        addVisibilitySwitches=True,

        worldMatrix=None,

        keyable=None,
        channelBox=None,
        rotateOrder='xyz',

        offsetGroups='offset',
        parent=None,
        pickWalkParent=None,

        shape='cube',
        shapeScale=1.0,
        lineWidth=None,
        color=None,

        asControl=True
):
    """
    Creates one or more (stacked) animation controls.

    :param int numControls/nc: the number of controls to generate; defaults to
        ``2``
    :param bool useLetters/let: number controls with letters, not numbers;
        if this is set to ``False``, padding can be controlled via the
        ``padding`` keyword argument on :class:`~paya.lib.names.Name`;
        defaults to ``True``
    :param float insetScale/iss: scale shapes by this amount for every inset
        layer; defaults to ``0.8``
    :param bool numberFromFirstInset/nfs: don't apply a number to the
        topmost control; defaults to ``False``
    :param bool addVisibilitySwitches/avs: for each inset control, add a
        visibility option on the control above it; defaults to ``True``
    :param worldMatrix/wm: the initial pose matrix; if omitted, defaults to
        the identity matrix
    :type worldMatrix/wm: :class:`list`, :class:`tuple`,
        :class:`~paya.runtime.data.Matrix`
    :param keyable/k: a list of channel names to make keyable on the
        controls; defaults to ``None``
    :type keyable/b: [:class:`str`]
    :param channelBox/cb: a list of channel names to make settable on the
        controls; defaults to ``None``
    :type channelBox/cb: [:class:`str`]
    :param rotateOrder/ro: the rotate order for the controls; defaults to
        ``'xyz'``
    :type rotateOrder/ro: :class:`int`, :class:`str`
    :param offsetGroups/og: one or more basenames for offset groups to
        add to the topmost control; defaults to ``'offset'``
    :type offsetGroups/og: :class:`str`, [:class:`str`]
    :param parent/p: a destination parent for the topmost offset group;
        defaults to ``None``
    :type parent/p: :class:`~paya.runtime.nodes.Transform`, :class:`str`
    :param pickWalkParent/pwp: a pick-walk parent for the topmost control;
        if omitted, defaults to ``parent``, but only if ``parent`` is itself
        a control, otherwise ``None``
    :type pickWalkParent/pwp: :class:`~paya.runtime.nodes.DependNode`,
        :class:`str`
    :param str shape/sh: the name of a library shape to apply to the controls;
        defaults to ``'cube'``
    :param lineWidth/lw: an optonal override for the display curve thickness;
        defaults to ``None``
    :param float shapeScale/ssc: overall shape scaling factor for the control
        system; defaults to ``1.0``
    :param color/col: a color for the controls; this can be an index value,
        or one of the shorthands supported by
        :meth:`~paya.runtime.nodes.Transform.colorCtShapes`; defaults to
        ``None``
    :param bool asControl/ac: if this is ``False``, simple groups will be
        created instead of controls with shapes; defaults to ``True``
    :return: All the generated controls in a list, outermost to innermost.
    :rtype: [:class:`~paya.runtime.nodes.Transform`]
    """
    out = []

    multi = numControls > 1
    baseElems = []

    for i in range(numControls):
        theseElems = baseElems[:]

        addNumber = multi and not (i is 0 and numberFromFirstInset)

        if addNumber:
            userNumber = i

            if not numberFromFirstInset:
                userNumber = i+1

            if useLetters:
                userNumber = int_to_letter(userNumber).upper()

            else:
                userNumber = pad(userNumber, config['padding'])

            theseElems.append(userNumber)

        kwargs = {
            'worldMatrix': worldMatrix,
            'parent': out[-1] if i > 0 else parent,
            'keyable': keyable,
            'channelBox': channelBox,
            'rotateOrder': rotateOrder,
            'offsetGroups': None if i > 0 else offsetGroups,
            'shape': shape,
            'lineWidth': lineWidth,
            'shapeScale': shapeScale * (insetScale ** i),
            'color': color,
            'asControl': asControl
        }

        with r.Name(theseElems):
            ct = createControl(**kwargs)

        if asControl and addVisibilitySwitches and i > 0:
            prev = out[-1]
            prev.attrSections.add('EXTRA_CONTROLS')
            sw = prev.addAttr('insetControl', k=0, cb=1, dv=False, at='bool')

            for s in ct.getShapes():
                sw >> s.attr('v')

        out.append(ct)

    return out

#----------------------------------------------------------------|
#----------------------------------------------------------------|    MISC
#----------------------------------------------------------------|

def getControls():
    """
    :return: All controls in the scene.
    :rtype: [:class:`~paya.runtime.nodes.Transform`]
    """
    xfs = m.ls(type='transform')
    out = []

    for xf in xfs:
        if m.controller(xf, q=True):
            name = xf.split('|')[-1]
            elems = name.split('_')
            if elems[-1] == _suf.suffixes['payaControl']:
                out.append(r.pn(xf))

    return out