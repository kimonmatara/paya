"""Routes custom Maya plug classes based on an abstract tree defined in ``./plugtree.json``.
"""

import os
import json

import maya.OpenMaya as om
import maya.cmds as m

#-----------------------------------------------------|
#-----------------------------------------------------|    UTILS
#-----------------------------------------------------|

cap = lambda x: x[0].upper()+x[1:]

#-----------------------------------------------------|
#-----------------------------------------------------|    TREE MANAGEMENT
#-----------------------------------------------------|

jsonpath = os.path.join(
    os.path.dirname(__file__),
    'plugtree.json'
)

with open(jsonpath,'r') as f:
    data = f.read()

dct = json.loads(data)

def getPath(typeName):
    """
    Returns hierarchical type information.

    :param str typeName: The plug type to query
    :return: A list of abstract type names, ordered
        similarly to ``nodeType(inherited=True)``.
    :rtype: :class:`list`
    """
    foundPath = []

    def parseDict(dct,result,pathToHere=[]):

        for k, v in dct.items():
            thisPath = pathToHere + [k]

            if k == typeName:
                result[:] = thisPath[:]
                break

            else:
                parseDict(v,result,pathToHere=thisPath)

    result = []
    parseDict(dct,result,[])

    if result:
        out = result

    else:
        # Invent a path

        out = ['Attribute',typeName]

    out = map(str,out)
    return list(out)

#-----------------------------------------------------|
#-----------------------------------------------------|    PLUG INSPECTION
#-----------------------------------------------------|

def enumerator(enum):
    """
    Helper for reverse lookups on enumerators such as `MFn.type`.
    """
    out = dict()

    for key,value in enum.__dict__.items():
        if not key.startswith('k'):
            continue

        if isinstance(value,int):
            out[value] = key

    return out

def getMPlugPathString(mplug):
	"""
	Returns the full DAG path to a given mplug.

	:param `OpenMaya.MPlug` mplug: the MPlug instance to query
	:return: The DAG path to the MPlug.
	:rtype: :class:`str`
	"""
	name = '.'.join(mplug.name().split('.')[1:])
	node = mplug.node()

	if node.hasFn(om.MFn.kDagNode):
		# Need to get resolved path
		dp = om.MDagPath()
		om.MFnDagNode(node).getPath(dp)
		name = dp.partialPathName()+'.'+name

	else:
		name = om.MFnDependencyNode(node).name()+'.'+name

	return name


def getMPlugTypeInfo(mplug):
    """
    Returns plug type information on the given MPlug in a
    dict comprising the following keys:

    - plugType
        The basic MObject type, e.g. ``kNumericAttribute``

    - dataType
        If available, the type of data served

    - numericType
        The numeric subtype (e.g. ``kFloat``) if the plugType was ``kNumericAttribute``
    """
    out = {}

    # Plug type
    plugType = out['plugType'] = mplug.attribute().apiTypeStr()

    # Data type
    if plugType in ('kGenericAttribute','kTypedAttribute'):

        # Evaluate if dirty, as data type might change
        fullpath = getMPlugPathString(mplug)

        try:
            if m.isDirty(fullpath):
                m.dgeval(fullpath)

        except RuntimeError as exc:
            m.warning(__name__+'.getMPlugTypeInfo(): '+
                      'Could not evaluate plug '+fullpath+
                      '. The error was: '+str(exc.message))

        # Try and extract a data type by getting the data
        # packet using asMObject()... especially relevant
        # for nodes that spit out different types of geometry
        # depending on their inputs

        try:
            _dtp = mplug.asMObject().apiTypeStr()

        except:
            _dtp = None

        if not _dtp:
            # Fall back to non-API methods, as PyMEL does in
            # pymel.core.general.Attribute.type()

            _dtp = m.getAttr(fullpath,type=1)

            if not _dtp:
                # From PyMEL: Sometimes getAttr fails with
                # dynamic attributes...

                if om.MFnAttribute(mplug.attribute()).isDynamic():
                    try:
                        _dtp = m.addAttr(fullpath,q=1,dt=1)

                    except:
                        pass
        if _dtp:

            if isinstance(_dtp,(tuple,list)):
                _dtp = _dtp[0]

            if not _dtp.startswith('k'):
                _dtp = 'k'+cap(_dtp)+'Data'

            out['dataType'] = str(_dtp)

    # Numeric subtype
    if plugType == 'kNumericAttribute':

        # Get numeric subtype
        fn = om.MFnNumericAttribute(mplug.attribute())

        out['numericType'] = enumerator(
            om.MFnNumericData)[fn.unitType()]

    return out


def getTypeFromMPlug(mplug,inherited=False):
    """Given an MPlug, returns a best-fit name from the abstract class tree.

    :param OpenMaya.MPlug mplug: the MPlug to query
    :param bool inherited: return a hierarchy path, defaults to ``False``
    :return: A full inheritance stack if ``inherited=True``, otherwise a single string.
    :rtype: ``str`` or ``[str]``
    """
    info = getMPlugTypeInfo(mplug)

    plugType = info['plugType']
    dataType = info.get('dataType')

    if dataType:
        if dataType.endswith('Data'):
            _dataType = dataType[1:-4]

        else:
            _dataType = dataType[1:]

        out = 'AttributeData'+_dataType

    elif plugType == 'kNumericAttribute':
        numericType = info.get('numericType')

        if numericType:
            return 'AttributeNumeric'+(numericType[1:])

        out = 'AttributeNumeric'

    else:
        # In all other cases, construct a full fallback name
        basename = plugType[1:]

        if basename.endswith('Attribute'):
            basename = basename[:-9]

        if not basename.startswith('Attribute'):
            basename = 'Attribute'+basename

        out = basename

    # Deal with some odd situations caused by occasional
    # wonky API names like kDataBezierCurveData

    out = out.replace('DataData','Data')

    if inherited:
        out = getPath(out)

    return out