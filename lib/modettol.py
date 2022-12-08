"""
Utilities for model cleanup.
"""
from tempfile import gettempdir

import maya.cmds as m
import paya.runtime as r
from pymel.util import expandArgs
from paya.util import without_duplicates
from paya.lib.suffixes import suffixes

def getAllGeoShapes(noIntermediate=False):
    """
    :param bool noIntermediate: skip intermediate nodes; defaults to ``False``
    :return: ``mesh``, ``nurbsCurve`` and ``nurbsSurface`` nodes in the scene.
    :rtype: [:class:`str`]
    """
    out = []

    for typ in ('nurbsCurve', 'nurbsSurface', 'mesh'):
        matches = m.ls(type=typ)

        if matches:
            if noIntermediate:
                matches = [match for match in matches \
                    if not m.getAttr('{}.intermediateObject'.format(match))]

            out += matches

    return out

def getAllGeoXforms():
    """
    :return: Transforms for all ``mesh``, ``nurbsCurve`` and
        ``nurbsSurface`` nodes in the scene.
    :rtype: [:class:`str`]
    """
    xforms = []

    for shape in getAllGeoShapes(noIntermediate=True):
        xforms += m.listRelatives(shape, parent=True)

    return xforms

def conformShapeNames():
    """
    Repairs wonky geometry shape names.
    """
    count = 0

    for xform in getAllGeoXforms():
        shapes = m.listRelatives(xform, shapes=True, noIntermediate=False)
        origShapeNames = [shape.split('|')[-1] for shape in shapes]

        r.PyNode(xform).conformShapeNames()

        shapes = m.listRelatives(xform, shapes=True, noIntermediate=False)
        newShapeNames = [shape.split('|')[-1] for shape in shapes]

        inters = set(origShapeNames).intersection(set(newShapeNames))
        numNewNames = len(origShapeNames) - len(inters)

        count += numNewNames

    if count:
        m.confirmDialog(
            title="Conform Geometry Shape Names",
            message="Conformed shape names under"+
            " {} geometry transforms.".format(count),
            button='OK'
        )
    else:
        m.confirmDialog(
            title="Conform Geometry Shape Names",
            message="No shape names had to be conformed.",
            button='OK'
        )

def checkDuplicateNames():
    """
    Checks for duplicate geometry shape and transform names. If any are found,
    the instances are organised into a ``duplicate_names`` object set for
    further inspection.
    """
    # Clear up existing object sets
    matches = m.ls('*duplicate_names*', type='objectSet')

    if matches:
        for match in matches:
            try:
                m.delete(match)
            except:
                pass

    # Determine what to check
    allGeoShapes = getAllGeoShapes()
    allGeoXforms = []

    for geoShape in allGeoShapes:
        allGeoXforms += m.listRelatives(geoShape, parent=True)

    namesToCheck = [item.split('|')[-1] \
                    for item in allGeoShapes + allGeoXforms]

    _namesToCheck = []

    for nameToCheck in namesToCheck:
        if nameToCheck not in _namesToCheck:
            _namesToCheck.append(nameToCheck)

    namesToCheck = _namesToCheck

    # Iterate
    hasDuplicates = False
    rootSet = None

    for nameToCheck in namesToCheck:
        matches = m.ls(nameToCheck)

        if len(matches) > 1:
            hasDuplicates = True

            if rootSet is None:
                rootSet = r.sets(n='duplicate_names', empty=True)

            thisSet = r.sets(
                n='{}_duplicate_names'.format(nameToCheck),
                empty=True
            )

            rootSet.add(thisSet)

            for match in matches:
                thisSet.add(match)

    if hasDuplicates:
        m.confirmDialog(
            title='Duplicate Geometry Names',
            message="Duplicate geometry names were "+
                    "found. See the 'duplicate_names' set.",
            button='OK'
        )

    else:
        m.confirmDialog(
            title='Duplicate Geometry Names',
            message="No duplicate geometry names were found.",
            button='OK'
        )

def removeUnknownNodes():
    """
    Removes all unknown nodes from the scene.
    :return: The names of nodes which were removed.
    :rtype: [:class:`str`]
    """
    unknown = m.ls(type='unknown')
    removed = []

    if unknown:
        for node in unknown:
            if m.objExists(node):
                if m.referenceQuery(node, isNodeReferenced=True):
                    m.warning(
                        "Node '{}' is referenced and cannot be removed.".format(node)
                    )
                    continue

                m.lockNode(node, lock=False)
                m.delete(node)
                removed.append(node)
            print("Deleted unknown node: {}".format(node))
    else:
        print("No unknown nodes were found.")

    return removed

def removeUnknownPlugins():
    """
    Removes all requirements for unknown plugins from the scene.
    :return: The names of plugins which were removed.
    :rtype: [:class:`str`]
    """
    plugins = m.unknownPlugin(q=True, list=True)
    removed = []

    if plugins:
        for plugin in plugins:
            m.unknownPlugin(plugin, remove=True)
            removed.append(plugin)
            print("Removed unknown plugin requirement: {}".format(plugin))

    else:
        print("No unknown plugins were found.")

    return removed

def removeUnknown():
    """
    Convenience function. Calls :func:`removeUnknownNodes` and
    :func:`removeUnknownPlugins`.
    """
    removeUnknownNodes()
    removeUnknownPlugins()

#  STUB
# def stripdown(*nodes):
#     """
#     Exports the specified nodes to a temporary scene, starts a new scene
#     pointed to the original path (if any), and re-imports the exported nodes.
#
#     :param \*nodes: the nodes to strip the scene down to
#     :type \*nodes: :class:`str`, :class:`~paya.runtime.nodes.DependNode`,
#         [:class:`str`, :class:`~paya.runtime.nodes.DependNode`]
#     :return: The isolated nodes.
#     :rtype: [:class:`~paya.runtime.nodes.DependNode`]
#     """
#     nodes = without_duplicates([str(x) for x in expandArgs(*nodes)])