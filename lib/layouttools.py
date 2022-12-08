"""
Interactive layout helpers.
"""

import paya.runtime as r
import maya.cmds as m
from paya.lib.mathops import floatRange

@r
def locatorAtComponentCentre():
    """
    Creates a locator at the center of selected mesh components.

    :Instructions:

    #. Select some components.
    #. Run.

    :return: The generated locator transform.
    :rtype: :class:`~paya.runtime.nodes.Transform`
    """
    sel = m.ls(sl=True)
    verts = m.polyListComponentConversion(sel, toVertex=True)
    verts = m.ls(verts, flatten=True)
    points = [m.pointPosition(vert, world=True) for vert in verts]
    points = [r.data.Point(point) for point in points]

    centroid = points[0].center(*points[1:])
    return centroid.createLocator()

@r
def locatorBetweenTwoObjects():
    """
    Creates a locator at the midpoint between two other objects.

    :Instructions:

    #.  Select two objects. These can be transforms, or any Paya type that
        implements ``getWorldPosition()``.
    #.  Run.

    :return: The generated locator transform.
    :rtype: :class:`~paya.runtime.nodes.Transform`
    """
    a, b = r.ls(sl=1, flatten=True)
    pointA, pointB = [a.gwp(), b.gwp()]
    point = pointA.blend(pointB, weight=0.5)
    return point.createLocator()

@r
def distributePositions():
    """
    Distributes transform positions. The start and end transform positions
    won't be edited at all.

    :Instructions:

    #.  Select three or more transforms, in the order you want them
        distributed.
    #.  Run.
    """
    sel = r.ls(sl=True, type='transform')
    positions = [node.getWorldPosition() for node in sel]
    ratios = floatRange(0, 1, len(positions))[1:-1]

    for node, ratio in zip(sel[1:-1], ratios):
        point = r.util.blend(positions[0], positions[-1], weight=ratio)
        r.move(node, point, a=True, ws=True)

@r
def aimObject():
    """
    Orients a transform using an 'aim' and 'up' interest. Aim and up axes are
    derived from initial orientation.

    :Instructions:

    #.  Roughly orient the 'slave' transform.
    #.  Select the 'aim' interest. This can be a transform, or any Paya type
        that implements ``getWorldPosition()``.
    #.  Add-select the 'up' interest. This can be a transform, or any Paya
        type that implements that implements ``getWorldPosition()``.
    #.  Add-select the 'slave' transform.
    #.  Run.
    """
    aimInterest, upInterest, xform = r.ls(sl=True)
    aimPoint, upPoint, xformPoint = \
        [item.getWorldPosition() for item in (aimInterest, upInterest, xform)]

    aimVec = aimPoint - xformPoint
    upVec = upPoint - xformPoint

    aimAxis = xform.closestAxisToVector(aimVec)
    upAxis = xform.closestAxisToVector(upVec)

    matrix = r.createMatrix(aimAxis, aimVec, upAxis, upVec)
    matrix = matrix.pick(r=True, default=xform.getMatrix(worldSpace=True))
    xform.setMatrix(matrix, worldSpace=True)