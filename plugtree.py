"""
For internal use. Manages the inheritance tree used to construct abstract
Paya attribute subtypes.
"""

import re
import json
from pprint import pprint

import maya.OpenMaya as om

#------------------------------------------------------|    Tree init and editing

class NoPathError(RuntimeError):
    """
    The requested class name could not be found in the tree.
    """

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
            'DataNumeric': {},  # Expanded by expandTree()
            'DataArray': {},    # Expanded by expandTree()
            # Include all the rest here, except for Matrix data, which
            # should be piped to Matrix
        },
    }
}

def printTree():
    """
    Pretty-prints the Paya attribute inheritance tree.
    """
    global tree
    pprint(tree)

def getPath(typeName):
    """
    Returns hierarchical type information. Used to implement
    :meth:`Attribute.plugType() <paya.runtime.plugs.Attribute.plugType>`

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

def getTerminatingKeys():
    """
    :return: All class names in the tree that have no descendants.
    :rtype: [str]
    """
    global tree

    terminatingKeys = []

    def _getTerminatingKeys(dct):
        for k, v in dct.items():
            if v:
                _getTerminatingKeys(v)

            else:
                terminatingKeys.append(k)

    _getTerminatingKeys(tree)

    return terminatingKeys

def insert(typeName, parent=None):
    """
    Inserts an abstract type into the tree.

    :param str typeName: the name of the type to insert
    :param parent: an optional (existing) parent for the new type
    :type parent: None, str
    """
    global tree

    if parent:
        path = getPath(parent)

    else:
        path = ['Attribute']

    container = tree[path[0]]

    for key in path[1:]:
        container = container[key]

    container[typeName] = {}

def createPath(path):
    """
    Ensures that the specified path exists in the tree.

    :param path: the path to enforce
    :type path: [str]
    """
    global tree

    current = tree

    for key in path:
        current = current.setdefault(key, {})

def expandTree():
    """
    Call on import to expand the explicit ``tree`` dictionary procedurally.
    """
    global tree

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

    # Consider restoring the below once we have a solution for
    # dunder method fallbacks (e.g. using * on a non-indexed
    # .worldMatrix)

    # # Add array subtypes
    #
    # endKeys = getTerminatingKeys()
    #
    # for endKey in endKeys:
    #     fullPath = getPath(endKey)[1:]
    #     fullPath = ['ArrayOf{}'.format(elem) for elem in fullPath]
    #     fullPath = ['Attribute', 'Array'] + fullPath
    #     createPath(fullPath)

expandTree()

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
    out = _getTypeFromMPlug(mplug)

    # Consider restoring the below once we have a solution for
    # dunder method fallbacks (e.g. using * on a non-indexed
    # .worldMatrix):

    # if mplug.isArray():
    #     out = 'ArrayOf{}'.format(out)

    if inherited:
        out = getPath(out)

    return out