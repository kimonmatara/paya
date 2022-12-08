"""
Internal. Contains routines to get information on
:class:`~maya.OpenMaya.MPlug` instances and administer abstract Paya plug
classes.
"""

import os
import re
import json
from pprint import pprint

import maya.OpenMaya as om
import maya.cmds as m

from paya.apiutil import *

#----------------------------------------------------------------|
#----------------------------------------------------------------|    PLUG TREE
#----------------------------------------------------------------|

# The tree doesn't define all available override types; it's used
# by the info functions to define inheritance.

tree = {
    'Attribute': {
        'Math': {
            'Math1D': {
                'Unit': {
                    'Angle': {},
                    'Time': {},
                    'Distance': {}
                },
                'Enum': {}
            },
            'Math2D': {},
            'Math3D': {
                'EulerRotation': {},
                'Vector': {}
            },
            'Quaternion': {},
            'Matrix': {}
        },
        'Geometry': {
            'NurbsCurve': {'BezierCurve': {}},
            'NurbsSurface': {},
            'DynSweptGeometry': {},
            'Lattice': {},
            'Mesh': {},
            'PluginGeometry': {},
            'Sphere': {},
            'Box': {},
            'Subdiv': {}
        }
    }
}

def expandTree():
    global tree

    # Insert 1D and 2D numeric types, in case we want to override them;
    # 4D is ignored as it's always mapped directly to Quaternion
    pat = r"^k([2-4]?)(.*)$"
    keys = [key for key in om.MFnNumericData.__dict__ if key.startswith('k')]

    for key in keys:
        if key in ('kInvalid', 'kLast'):
            continue

        mt = re.match(pat, key)

        dim, typ = re.match(pat, key).groups()

        if dim:
            if dim == '4':
                # Ignore; always mapped directly to Quaternion
                continue

            niceName = '{}{}'.format(typ, dim)
            tree['Attribute']['Math']['Math{}D'.format(dim)][niceName] = {}

        else:
            tree['Attribute']['Math']['Math1D'][typ] = {}

expandTree()

def printTree():
    global tree
    pprint(tree)

def getPath(typeName):
    """
    Rejigged in Paya 1.0: If *typeName* is not in the plug tree, a simple path
    from 'Attribute' will be invented.
    """
    global tree

    foundPath = []

    def parseDict(dct, result, pathToHere=[]):
        for k, v in dct.items():
            thisPath = pathToHere + [k]

            if k == typeName:
                result[:] = thisPath[:]
                break

            else:
                parseDict(v, result, pathToHere=thisPath)

    result = []
    parseDict(tree, result, [])

    if result:
        return list(map(str, result))

    return ['Attribute', typeName]

#----------------------------------------------------------------|
#----------------------------------------------------------------|    ANALYSE MPLUG
#----------------------------------------------------------------|

"""
key (for tree)
isCompound
isData
mathDimension (only for non-data types)
mathUnitType ('distance', 'angle', 'time') (only for non-data types; omitted if no unit)
"""

def _getInfoFromDataBlock(nodeMObj,
                          attrMObj,
                          logicalIndex):
    info = {}

    mplug = om.MPlug(nodeMObj, attrMObj)

    if logicalIndex is not None:
        mplug = mplug.elementByLogicalIndex(logicalIndex)

    dataHandle = mplug.asMDataHandle()

    try:
        dataHandleType = dataHandle.type()
        data = dataHandle.data()
        dataType = data.apiType()
        dataTypeStr = data.apiTypeStr()

        if dataType == 0:
            if dataHandleType == 0:
                info['key'] = 'Invalid'
            else:
                # Parse from data handle type, i.e. MFnData enumerator
                dataHandleTypeStr = enumIndexToKey(dataHandleType, om.MFnData)

                if dataHandleTypeStr == 'kNumeric':
                    info['mathDimension'] = 1
                    info['key'] = 'Math1D'

                else:
                    info['key'] = dataHandleTypeStr[1:]

        elif data.hasFn(om.MFn.kMatrixData):
            info['key'] = 'Matrix'
            info['mathDimension'] = 16

        elif data.hasFn(om.MFn.kGeometryData):
            mt = re.match(r"^k(.*)Data$", dataTypeStr)
            info['key'] = mt.groups()[0]

        elif data.hasFn(om.MFn.kNumericData):
            dim, typ = re.match(r"^kData([2-4])(.*)$", dataTypeStr).groups()
            info['mathDimension'] = int(dim)

            if dim != 4:
                info['key'] = '{}{}'.format(typ, dim)

            else:
                info['key'] = 'Quaternion'

        elif dataTypeStr in ('kMatrixData', 'kMatrixFloatData'):
            info['key'] = 'Matrix'

        else:
            mt = re.match(r"^k(.+?)Data$", dataTypeStr)
            info['key'] = mt.groups()[0]

    finally:
        mplug.destructHandle(dataHandle)

    return info

def getInfoFromMPlug(mplug):
    if mplug.isArray():
        logicalIndex = 0
        mplug = mplug.elementByLogicalIndex(0)

    elif mplug.isElement():
        logicalIndex = mplug.logicalIndex()

    else:
        logicalIndex = None

    return getInfoFromMObjects(mplug.node(),
                               mplug.attribute(),
                               logicalIndex)

def getInfoFromMObjects(nodeMObj, attrMObj, logicalIndex):
    info = {'key': 'Attribute'} # will likely be overriden

    if attrMObj.hasFn(om.MFn.kCompoundAttribute):
        mfn = om.MFnCompoundAttribute(attrMObj)
        info['isCompound'] = True
        numChildren = mfn.numChildren()

        # Decide whether to treat as a math compound
        if numChildren in (2, 3, 4):
            childMObjs = [mfn.child(x) for x in range(numChildren)]
            childInfos = [getInfoFromMObjects(
                nodeMObj, c, None) for c in childMObjs]

            if all([info.get('mathDimension') is 1 for info in childInfos]):
                units = [info.get('mathUnitType') for info in childInfos]

                if len(set(units)) is 1:
                    unit = units[0]
                    hasUnit = unit is not None

                    if numChildren is 3:
                        info['mathDimension'] = 3

                        if hasUnit:
                            info['mathUnitType'] = unit

                            if unit == 'angle':
                                info['key'] = 'EulerRotation'
                            else:
                                info['key'] = 'Vector'
                        else:
                            info['key'] = 'Vector'

                    elif numChildren is 4 and not hasUnit:
                        info['mathDimension'] = 4
                        info['key'] = 'Quaternion'

                    elif numChildren is 2:
                        info['mathDimension'] = 2
                        info['key'] = 'Math2D'

    elif attrMObj.hasFn(om.MFn.kNumericAttribute):
        # We already know it's not a compound, therefore will be
        # a 1D type
        info['mathDimension'] = 1
        mfn = om.MFnNumericAttribute(attrMObj)
        subtype = mfn.unitType()
        subtypeStr = enumIndexToKey(subtype, om.MFnNumericData)

        pat = r"^k(.*)$"
        info['key'] = re.match(r"^k(.*)$", subtypeStr).groups()[0]

    elif attrMObj.hasFn(om.MFn.kMatrixAttribute) \
            or attrMObj.hasFn(om.MFn.kFloatMatrixAttribute):
        info['mathDimension'] = 16
        info['key'] = 'Matrix'

    elif attrMObj.hasFn(om.MFn.kUnitAttribute):
        info['mathDimension'] = 1
        mfn = om.MFnUnitAttribute(attrMObj)
        subtype = mfn.unitType()

        if subtype == om.MFnUnitAttribute.kAngle:
            info['mathUnitType'] = 'angle'
            info['key'] = 'Angle'

        elif subtype == om.MFnUnitAttribute.kDistance:
            info['mathUnitType'] = 'distance'
            info['key'] = 'Distance'

        elif subtype == om.MFnUnitAttribute.kTime:
            info['mathUnitType'] = 'time'
            info['key'] = 'Time'

        else:
            raise RuntimeError("Invalid unit type.")

    elif attrMObj.hasFn(om.MFn.kEnumAttribute):
        info['mathDimension'] = 1
        info['key'] = 'Enum'

    elif attrMObj.hasFn(om.MFn.kMessageAttribute):
        info['key'] = 'Message'

    elif attrMObj.hasFn(om.MFn.kGenericAttribute) \
            or attrMObj.hasFn(om.MFn.kTypedAttribute):
        info['isData'] = True
        info.update(_getInfoFromDataBlock(nodeMObj,
                                          attrMObj,
                                          logicalIndex))
    else:
        apiTypeStr = attrMObj.apiTypeStr()
        mt = re.match(r"^(.*)Attribute$")

        if mt:
            info['key'] = mt.groups()[0]

        else:
            raise RuntimeError(
                "Can't parse attribute type: {}".format(apiTypeStr))

    return info

def getInfoFromAttr(pmAttr):
    return getInfoFromMPlug(pmAttr.__apimplug__())