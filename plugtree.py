"""
Manages the inheritance tree used to construct the abstract **paya**
attribute subtypes. The tree is defined inside ``paya/plugtree.json``.

This module is not intended for direct use.
"""

import re
import json
from pprint import pprint

import maya.OpenMaya as om

#------------------------------------------------------|    Tree construction

def printTree():
    pprint(tree)

global tree
tree = {}

def insert(typeName, parent=None):
    if parent:
        path = getPath(parent)

    else:
        path = ['Attribute']

    container = tree[path[0]]

    for key in path[1:]:
        container = container[key]

    container[typeName] = {}

class NoPathError(RuntimeError):
    pass

def getPath(typeName):
    """
    Returns hierarchical type information.

    :param str typeName: The plug type to query
    :return: A list of abstract type names, ordered
        similarly to ``nodeType(inherited=True)``.
    :rtype: :class:`list`
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

    raise NoPathError(
        "Couldn't find class '{}' in the abstract plug tree".format(typeName)
    )


def initTree():
    global tree

    tree = {
        'Attribute':{
            'Compound': {
                'Math2D': {},
                'Math3D':{
                    'EulerRotation': {},
                    'Vector': {}
                },
                'Quaternion': {}
            },
            'Math1D':{
                'Unit':{
                    'Distance': {},
                    'Time': {},
                    'Angle': {}
                },
                'Boolean': {},
                'Enum': {}
            },
            'Matrix': {},
            'Data':{
                'Geometry':{
                    'PluginGeometry': {},
                    'Mesh': {},
                    'Lattice': {},
                    'NurbsCurve': {
                        'BezierCurve': {}
                    },
                    'NurbsSurface': {},
                    'Sphere': {},
                    'SubdSurface': {},
                    'DynSweptGeometry': {}
                },
                'DynArrayAttrs': {},
                'ComponentList': {},
                'DataNumeric': {}, # Dump non-DG-manipulatable plugs here
                'DataArray': {}, # Expand dynamically via MFnData
                # Include all the rest here, except for Matrix data, which should be piped to Matrix
            },
        }
    }

    # Expand data types

    ignore = ('kMatrix', 'kInvalid', 'kLast', 'kNumeric')

    dataTypes = filter(
        lambda x: re.match(r"^k[A-Z].*$", x) and x not in ignore,
        om.MFnData.__dict__.keys()
    )

    for dataType in dataTypes:

        mt = re.match(r"^k(.*?)(Array)?$", dataType)

        basename, array = mt.groups()

        if array:
            clsname = '{}Array'.format(basename)
            insert(clsname, parent='DataArray')

        else:
            clsname = '{}'.format(basename)

            try:
                getPath(clsname)

            except NoPathError: # not already added manually
                insert(clsname, parent='Data')

    ignore = ('kInvalid', 'kLast')

    numericDataTypes = filter(
        lambda x: re.match(r"^k.*$", x) and x not in ignore,
        om.MFnNumericData.__dict__.keys()
    )

    for numericDataType in numericDataTypes:
        mt = re.match("^k([2-4].*)$", numericDataType)

        if mt:
            clsname = "Data{}".format(mt.groups()[0])
            insert(clsname, parent='DataNumeric')

initTree()

#------------------------------------------------------|    Type analysis

def numericUnitTypeIs1D(unitType):
    for item in [
        om.MFnNumericData.k2Short,
        om.MFnNumericData.k3Short,

        om.MFnNumericData.k2Long,
        om.MFnNumericData.k2Int,
        om.MFnNumericData.k3Long,
        om.MFnNumericData.k3Int,

        om.MFnNumericData.k2Float,
        om.MFnNumericData.k3Float,

        om.MFnNumericData.k2Double,
        om.MFnNumericData.k3Double,
        om.MFnNumericData.k4Double
    ]:
        if unitType == item:
            return False

    return True

def getTypeFromDataBlock(mplug, asString=False):
    if mplug.isArray():
        _mplug = mplug.elementByLogicalIndex(0)

    else:
        _mplug = mplug

    hnd = _mplug.asMDataHandle()
    data = hnd.data()

    return data.apiTypeStr() if asString else data.apiType()

def _getTypeFromMPlug(mplug):
    """
    Pseudo
        If compound:
            If num children in (2, 3, 4):
                If number is 3:
                    For each child:
                        If it's a numeric attribute:
                            If it's a 1D type, record a type of '1D'
                            Otherwise: return general compound key

                        elif it's a unit attribute:
                            If it's an angle, record a type of 'angle'
                            Otherwise, record a type of '1D'

                        else:
                            return general compound type

                If number is 4:
                    If all children are numbers (regardless), return as Quaternion
                    Otherwise, return compound

                if number is 2:
                    if all children are numbers, return Math2D

            else:
                return compound

        else:
            if numeric:
                we know it's not a compound type.
                return an appropriate key

            elif it's unit:
                if it's angle, return angle
                otherwise return a subclass of Math1D, i.e. distance or time

            elif it's matrix: return matrix

            elif is typed or generic:
                get the type from the data block

            else:
                return attribute
    """
    if mplug.isCompound():
        compoundMfn = om.MFnCompoundAttribute(mplug.attribute())
        numChildren = compoundMfn.numChildren()

        if numChildren in (2, 3, 4):
            childMObjects = [compoundMfn.child(x) for x in range(numChildren)]

            if numChildren is 3:
                types = []

                for childMObject in childMObjects:
                    if childMObject.hasFn(om.MFn.kNumericAttribute):
                        mfn = om.MFnNumericAttribute(childMObject)

                        if numericUnitTypeIs1D(mfn.unitType()):
                            types.append('1D')

                        else:
                            return 'Compound'

                    elif childMObject.hasFn(om.MFn.kUnitAttribute):
                        mfn = om.MFnUnitAttribute(childMObject)
                        ut = mfn.unitType()

                        if ut == om.MFnUnitAttribute.kAngle:
                            types.append('angle')

                        else:
                            types.append('1D')

                    else:
                        return 'Compound'

                if len(set(types)) is 1:
                    type = types[0]

                    if type == 'angle':
                        return 'EulerRotation'

                    return 'Vector'

                return 'Compound'

            else:
                for childMObject in childMObjects:
                    if childMObject.hasFn(om.MFn.kNumericAttribute):
                        mfn = om.MFnNumericAttribute(childMObject)

                        if numericUnitTypeIs1D(mfn.unitType()):
                            continue

                        else:
                            return 'Compound'

                    elif childMObject.hasFn(om.MFn.kUnitAttribute):
                        continue

                    return 'Compound'

                return 'Quaternion' if numChildren is 4 else 'Math2D'

        else:
            return 'Compound'

    mobj = mplug.attribute()

    if mobj.hasFn(om.MFn.kNumericAttribute):
        # We already know it's not a numeric compound or a data type,
        # so can only be a boolean or other 1D type

        mfn = om.MFnNumericAttribute(mobj)
        unitType = mfn.unitType()

        if unitType == om.MFnNumericData.kBoolean:
            return 'Boolean'

        return 'Math1D'

    if mobj.hasFn(om.MFn.kUnitAttribute):
        mfn = om.MFnUnitAttribute(mobj)
        unitType = mfn.unitType()

        if unitType == om.MFnUnitAttribute.kDistance:
            return 'Distance'

        elif unitType == om.MFnUnitAttribute.kAngle:
            return 'Angle'

        else:
            return 'Time'

    if mobj.hasFn(om.MFn.kEnumAttribute):
        return 'Enum'

    if mobj.hasFn(om.MFn.kMatrixAttribute):
        return 'Matrix'

    dataType = None

    isTyped = mobj.hasFn(om.MFn.kTypedAttribute)

    if isTyped:
        isGeneric = False

    else:
        isGeneric = mobj.hasFn(om.MFn.kGenericAttribute)

    if isTyped or isGeneric:
        dataType = getTypeFromDataBlock(mplug, asString=True)

        if dataType == 'kInvalid':
            return 'Data'

        if dataType == 'kNumericData':
            return 'DataNumeric'

        if dataType == 'kMatrixData':
            return 'Matrix'

        mt = re.match(r"^k(.*?)(Array)?Data$", dataType)

        basename, array = mt.groups()

        if array:
            return '{}Array'.format(basename)
            insert(clsname, parent='DataArray')

        else:
            return '{}'.format(basename)

    return 'Attribute'

def getTypeFromMPlug(mplug, inherited=False):
    typ = _getTypeFromMPlug(mplug)

    if inherited:
        return getPath(typ)

    return typ