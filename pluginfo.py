"""
Internal. Contains routines to get information on
:class:`~maya.OpenMaya.MPlug` instances and administer abstract Paya plug
classes.
"""

import re
import maya.OpenMaya as om
import maya.cmds as m
import pymel.core as p

from paya.util import uncap
from paya.apiutil import enumIndexToKey

#------------------------------------------------------------|
#------------------------------------------------------------|    Constants
#------------------------------------------------------------|

geoTypes = [
    'NurbsCurve',
    'BezierCurve',
    'NurbsSurface',
    'Mesh',
    'Subdiv',
    'Lattice',
    'PluginGeometry',
    'SubdSurface',
    'DynSweptGeometry'
]

#------------------------------------------------------------|
#------------------------------------------------------------|    Parse MFn enums
#------------------------------------------------------------|

def parseMFnEnums():
    """
    Runs on startup.

    :return: A mapping of ``{enum name: paya class name}`` for every enum on
        :class:`maya.OpenMaya.MFn`
    :rtype: :class:`dict`
    """
    # Include all enums which may be accessed as modified keys
    # from the tree, even if they have no meaningful classification
    # (i.e. they'll be put directly under Attribute)

    out = {} # MFn enum key: tree key
    enums = filter(lambda x: x.startswith('k'), om.MFn.__dict__)

    for enum in enums:
        #---------------|    kAttribute3Float, kData3Float...
        mt = re.match(
            r"^k(?:Attribute|Data)([2-4])(.*)$",
            enum
        )

        if mt:
            dim, key = mt.groups()
            key += dim
            out[enum] = key
            continue

        #---------------|    kNurbsCurveData, kMessageAttribute...

        if 'Array' not in enum:
            mt = re.match(
                r"k(.+)(Attribute|Data)$",
                enum
            )

            if mt:
                key = mt.groups()[0]
                out[enum] = key

    return out

def parseMFnDataEnums():
    """
    Runs on startup.

    :return: A mapping of ``{enum name: paya class name}`` for every enum on
        :class:`maya.OpenMaya.MFnData`
    :rtype: :class:`dict`
    """
    enums = filter(lambda x: x.startswith('k'), om.MFnData.__dict__)
    enums = list(filter(lambda x: x != 'kLast' and 'Array' not in x, enums))

    keys = list(map(lambda x: x[1:], enums))

    return dict(zip(enums, keys))

def parseMFnNumericDataEnums():
    """
    Runs on startup.

    :return: A mapping of ``{enum name: paya class name}`` for every enum on
        :class:`maya.OpenMaya.MFnNumericData`
    :rtype: :class:`dict`
    """
    out = {}
    enums = filter(lambda x: x.startswith('k'), om.MFnNumericData.__dict__)

    for enum in enums:
        mt = re.match(
            r"k([2-4])(.*)$",
            enum
        )

        if mt:
            dim, key = mt.groups()
            key += dim
            out[enum] = key
            continue

        key = enum[1:]

        if key != 'Last':
            out[enum] = enum[1:]

    return out

def parseMFnUnitAttributeEnums():
    """
    Runs on startup.

    :return: A mapping of ``{enum name: paya class name}`` for every enum on
        :class:`maya.OpenMaya.MFnUnitAttribute`
    :rtype: :class:`dict`
    """
    out = {}
    enums = filter(lambda x: x.startswith('k'), om.MFnUnitAttribute.__dict__)

    for enum in enums:
        if enum != 'kLast':
            out[enum] = enum[1:]

    return out

mFnEnumsToTreeKeys = parseMFnEnums()
mFnDataEnumsToTreeKeys = parseMFnDataEnums()
mFnNumericDataEnumsToTreeKeys = parseMFnNumericDataEnums()
mFnUnitAttributeEnumsToTreeKeys = parseMFnUnitAttributeEnums()

tree = {
    'Attribute': {
        'Math': {
            'Math1D': {
                'Unit': {
                    'Angle': {},
                    'Time': {},
                    'Distance': {}
                },
            },
            'Math2D': {},
            'Vector': {
                'EulerRotation': {}, # if 3 compound children are all angles
                'Point': {} # if 3 compound children are all linear
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
        },
    'Array': {}
    }
}

def _getPath(key, invent=True):
    global tree
    buffer = {'result': None}

    def parse(history):
        dct = tree

        for _key in history:
            dct = dct[_key]

        for _key in dct:
            possiblePath = history + [_key]

            if _key == key:
                buffer['result'] = possiblePath
            else:
                parse(possiblePath)

    parse([])
    result = buffer['result']

    if result:
        return result

    if invent:
        return ['Attribute', key]

    raise KeyError(
        "Key '{}' is not in the plug tree.".format(key)
    )

def parsePerKeyInfo():
    """
    Runs on startup.

    :return: A ``{paya class name: info dict}`` mapping, where ``info``
        comprises:

        ::

            {
                'mathDimension': int, # e.g. 3; may be omitted
                'type': list, # the class path,
                'mathUnitType': str # one of 'angle', 'distance', 'time'; may be omitted
            }
    :rtype: :class:`dict`
    """
    global mFnEnumsToTreeKeys
    global mFnDataEnumsToTreeKeys
    global mFnNumericDataEnumsToTreeKeys
    global mFnUnitAttributeEnumsToTreeKeys

    keys = list(mFnEnumsToTreeKeys.values())
    keys += list(mFnDataEnumsToTreeKeys.values())
    keys += list(mFnNumericDataEnumsToTreeKeys.values())
    keys += list(mFnUnitAttributeEnumsToTreeKeys.values())
    keys = list(set(keys))

    out = {}

    for key in keys:
        parent = mathDimension = mathUnitType = None

        # DoubleAngle, FloatLinear
        mt = re.match(
            r"^.+(Linear|Angle)$",
            key
        )

        if mt:
            typ = mt.groups()[0]
            parent = {'Linear':'Distance'}.get(typ, typ)
            mathUnitType = uncap(parent)
            mathDimension = 1
        else:
            # Double3...
            mt = re.match(r"^[^0-9]+([0-9])$", key)

            if mt:
                mathDimension = int(mt.groups()[0])

                parent = {
                    2: 'Math2D',
                    3: 'Vector',
                    4: 'Quaternion'
                }[mathDimension]

            else:
                if key in ['Addr', 'Boolean', 'Byte', 'Char',
                           'Double', 'Enum', 'Float', 'Int',
                           'Int64', 'Long', 'Numeric', 'Short']:
                    mathDimension = 1
                    parent = 'Math1D'

                elif key == 'Matrix':
                    parent = 'Math'
                    mathDimension = 16
                elif key in ['Matrix', 'FloatMatrix', 'MatrixFloat']:
                    parent = 'Matrix'
                    mathDimension = 16
                else:
                    if key in geoTypes:
                        parent = 'Geometry'

                        if key == 'BezierCurve':
                            parent = 'NurbsCurve'

                    else:
                        if re.match(r"^.+Array$", key):
                            parent = 'Array'
                        else:
                            if key in ['Time', 'Distance', 'Angle']:
                                mathDimension = 1
                                mathUnitType = uncap(key)
                                parent = 'Unit'

        # Construct path
        if parent is None:
            path = _getPath(key, invent=True)

        else:
            path = _getPath(parent, invent=False) + [key]

        # path = []

        # if parent is None:
        #     path.append('Attribute')
        # else:
        #     path += _getPath(parent, invent=False)
        #
        # path.append(key)

        inf = {'type': path}

        if mathDimension is not None:
            inf['mathDimension'] = mathDimension

        if mathUnitType is not None:
            inf['mathUnitType'] = mathUnitType

        out[key] = inf

    return out

perKeyInfo = parsePerKeyInfo()

def getPath(key, invent=True):
    """
    :param str key: the name of a Paya class for which to retrieve
        an inheritance path
    :param bool invent: if the class is not classified, invent a basic
        classification; defaults to ``True``
    :return: The inheritance path.
    :rtype: :class:`list` [:class:`str`]
    """
    global perKeyInfo

    try:
        return perKeyInfo[key]['type']
    except KeyError as exc:
        return _getPath(key, invent=invent)

#------------------------------------------------------------|
#------------------------------------------------------------|    Instance analysis
#------------------------------------------------------------|

def getInfoFromMPlug(mplug):
    if mplug.isArray():
        mplug = mplug.elementByLogicalIndex(0)

    if mplug.isCompound():
        numChildren = mplug.numChildren()

        if numChildren in (2, 3, 4):
            children = [mplug.child(x) for x in range(mplug.numChildren())]
            childInfos = [getInfoFromMPlug(child) for child in children]

            mathDimensions = [childInfo.get(
                'mathDimension') for childInfo in childInfos]

            if all([mathDimension is 1 for mathDimension in mathDimensions]):
                if numChildren is 4:
                    return {
                        'type':getPath('Quaternion', invent=False),
                        'mathDimension': 4
                    }

                if numChildren is 3:
                    mathUnitTypes = [childInfo.get(
                        'mathUnitType', '') for childInfo in childInfos]

                    if all([mathUnitType == 'distance' for mathUnitType in mathUnitTypes]):
                        return {
                            'type':getPath('Point', invent=False),
                            'mathDimension': 3
                        }

                    elif all([mathUnitType == 'angle' for mathUnitType in mathUnitTypes]):
                        return {
                            'type':getPath('EulerRotation', invent=False),
                            'mathDimension': 3
                        }

                    else:
                        return {
                            'type':getPath('Vector', invent=False),
                            'mathDimension': 3
                        }

                return {
                    'type':getPath('Math{}D'.format(numChildren), invent=False),
                    'mathDimension': numChildren
                }

        return {'type':getPath('Compound')}

    mobj = mplug.attribute()

    if mobj.hasFn(om.MFn.kNumericAttribute):
        mfn = om.MFnNumericAttribute(mobj)
        subtype = mfn.unitType()
        subtypeStr = enumIndexToKey(subtype, om.MFnNumericData)
        key = mFnNumericDataEnumsToTreeKeys[subtypeStr]
        return perKeyInfo[key]

    if mobj.hasFn(om.MFn.kUnitAttribute):
        mfn = om.MFnUnitAttribute(mobj)
        subtypeStr = enumIndexToKey(mfn.unitType(), om.MFnUnitAttribute)
        key = mFnUnitAttributeEnumsToTreeKeys[subtypeStr]
        return perKeyInfo[key]

    if mobj.hasFn(om.MFn.kTypedAttribute):
        try:
            dataObj = mplug.asMObject()
            dataTypeStr = dataObj.apiTypeStr()
            key = mFnEnumsToTreeKeys[dataTypeStr]
            return perKeyInfo[key]
        except RuntimeError:
            mfn = om.MFnTypedAttribute(mobj)
            attrType = mfn.attrType()
            key = mFnDataEnumsToTreeKeys[enumIndexToKey(attrType, om.MFnData)]
            return perKeyInfo[key]

    if mobj.hasFn(om.MFn.kGenericAttribute):
        try:
            dataObj = mplug.asMObject()
            dataTypeStr = dataObj.apiTypeStr()
            key = mFnEnumsToTreeKeys[dataTypeStr]
            return perKeyInfo[key]
        except RuntimeError:
            mhandle = mplug.asMDataHandle()
            typ = mhandle.type()
            typeStr = enumIndexToKey(typ, om.MFnData)
            key = mFnDataEnumsToTreeKeys[typeStr]
            return perKeyInfo[key]

    if mobj.hasFn(om.MFn.kMatrixAttribute):
        return perKeyInfo['Matrix']

    elif mobj.hasFn(om.MFn.kEnumAttribute):
        return {'type':getPath('Enum'), 'mathDimension': 1}

    elif mobj.hasFn(om.MFn.kMessageAttribute):
        return {'type':getPath('Message')}

    raise RuntimeError(
        "Could not parse plug: {}".format(mplug.name())
    )

def getInfoFromAttr(pmattr):
    return getInfoFromMPlug(pmattr.__apimplug__())

#------------------------------------------------------------|
#------------------------------------------------------------|    Unit testing
#------------------------------------------------------------|

def unitTest(goto=True):
    if goto:
        path = 'C:/Users/user/Desktop/unittest.ma'
        p.openFile(path, f=1)

    plugs = [
        # 'persp.t',
        # 'persp.r',
        # 'persp.s',
        # 'persp.tx',
        # 'persp.rx',
        # 'persp.sx',
        # 'polyCube1.output',
        # 'pCubeShape1.worldMesh',
        # 'pCubeShape1.worldMesh[0]',
        # 'curve1.local',
        # 'unitConversion1.input',
        # 'unitConversion1.output',
        # 'locator1.notes',
        # 'choice1.selector',
        # 'choice1.input[0]',
        # 'choice1.output',
        # 'persp.matrix',
        # 'quatAdd1.outputQuat',
        # 'locator1.customMatrix',
        # 'bezier1.local',
        'persp.worldMatrix',
        'persp.worldMatrix[0]',
        'persp.rotateOrder'
    ]

    for plug in plugs:
        node, plug = plug.split('.')
        node = p.PyNode(node)
        plug = node.attr(plug)
        print('\nPlug is ', plug)
        print('Result is: {}'.format(getInfoFromAttr(plug)))