from collections import UserList, UserDict
import os
import json

import pymel.util as _pu
import pymel.core as p
from paya.util import short, LazyModule, AccessorOnNode


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


class ControlShapesManager(AccessorOnNode):

    #--------------------------------------------------|    Member access

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
        mirror='mir',
        mirrorAxis='ma',
        includeColor='ic',
        relativeWorldPosition='rwp'
    )
    def copyTo(
            self,
            *destControls,
            replace=False,
            worldSpace=False,
            relativeWorldPosition=False,
            mirror=False,
            mirrorAxis='x', # positive only
            includeColor=True
    ):
        """
        Copies control shapes from this control to one or more destination
        controls.

        :param \*destControls: one or more controls to copy shapes to
        :type \*destControls: list, str,
            :class:`~paya.nodetypes.transform.Transform`
        :param bool replace/rep: remove existing shapes on the destination
            controls; defaults to False
        :param bool worldSpace/ws: copy shapes in world space; defaults to
            False
        :param bool mirror/mir: flip shapes; defaults to False
        :param str mirrorAxis/ma: a positive axis along which to mirror;
            defaults to 'x'
        :param bool includeColor/ic: copy colours too; defaults to True
        :param bool relativeWorldPosition/rwp: ignored if ``worldSpace`` is
            False; preserve relative opposite-side shape positions; defaults
            to False
        :return: The new control shapes.
        :rtype: list of :class:`~paya.nodetypes.shape.Shape`
        """
        destControls = list(map(p.PyNode, _pu.expandArgs(*destControls)))

        if not destControls:
            raise RuntimeError("No destination controls specified.")

        srcControl = self.node()

        # Prep main source

        _srcGp = p.group(empty=True)
        srcShapes = getControlShapes(srcControl)

        r.parent(srcShapes, _srcGp, r=True, shape=True, add=True)
        srcGp = _srcGp.duplicate()[0]
        r.delete(_srcGp)

        if mirror:
            mirrorMtx = r.createMatrix()
            setattr(mirrorMtx, mirrorAxis,
                    getattr(mirrorMtx, mirrorAxis)*-1.0)

        if worldSpace:
            matrix = srcControl.getMatrix(worldSpace=True)

            if mirror:
                matrix *= mirrorMtx

            srcGp.setMatrix(matrix)

        elif mirror:
            srcGp.setMatrix(mirrorMtx)
            r.makeIdentity(srcGp, apply=True, t=True, r=True, s=True)

        # Iterate

        newShapes = []

        for destControl in destControls:

            oldShapes = getControlShapes(destControl)
            config = _getShapesConfig(oldShapes, tmplock=True)

            if includeColor:
                try:
                    del(config['color'])

                except KeyError:
                    pass

            if replace:
                r.delete(oldShapes)

            thisSrcGp = srcGp.duplicate()[0]

            if worldSpace:
                thisSrcGp.setParent(destControl)
                r.makeIdentity(thisSrcGp, apply=True, t=False, r=True, s=True)
                thisSrcGp.setParent(None)
                
            theseNewShapes = thisSrcGp.getShapes()
            r.parent(theseNewShapes, destControl, r=True, shape=True)

            r.delete(thisSrcGp)

            _applyShapesConfig(config, theseNewShapes)
            newShapes += theseNewShapes

            destControl.conformShapeNames()

        r.delete(srcGp)
        return newShapes

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