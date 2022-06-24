import re
import maya.cmds as m
import pymel.core as p

#------------------------------------------------------------|    Reordering

def expandAttrListToParentsAndChildren(attrList, instances=True):
    """
    Given a list of attributes, expands to include compound children.
    
    :param attrList: the list of attributes to expand
    :type attrList: list of str or
        :class:`~paya.plugtypes.attribute.Attribute`
    :param bool instances: return
        :class:`~paya.plugtypes.attribute.Attribute` instances rather than
        strings; defaults to True 
    :return: The expanded attribute list.
    :rtype: list of str or :class:`~paya.plugtypes.attribute.Attribute`
    """

    out = []

    for attr in attrList:
        plug = p.Attribute(attr)

        if plug.isChild():
            out.append(plug.getParent())

        elif plug.isCompound():
            out += plug.getChildren()

        out.append(plug)

    out = list(set(out))

    if not instances:
        out = map(str, out)

    return out

def _releasePlugsAndReturnStates(node):

	#--------------------------------|    Get a list of all user-defined attrs

	userAttrs = filter(
		lambda x: x.get(k=True) or x.get(cb=True),
		node.listAttr(ud=True)
		)

	# Expand to include parents and children

	userAttrs = expandAttrListToParentsAndChildren(userAttrs,instances=True)

	#--------------------------------|    Store information on inputs and outputs

	connections = []

	for userAttr in userAttrs:
		inputs = userAttr.inputs(plugs=True)

		if inputs:
			for input in inputs:
				connections.append([str(input),str(userAttr)])

		outputs = userAttr.outputs(plugs=True)

		if outputs:
			for output in outputs:
				connections.append([str(userAttr),str(output)])

	#--------------------------------|    Aggregate all attrs, store lock info, unlock them

	allInvolvedAttrs = map(str,userAttrs)

	for pair in connections:
		allInvolvedAttrs += pair

	allInvolvedAttrs = list(set(allInvolvedAttrs))

	# Expand to children / parents

	allInvolvedAttrs = \
		expandAttrListToParentsAndChildren(allInvolvedAttrs,instances=False)

	lockStates = {}

	for attr in allInvolvedAttrs:
		lockStates[attr] = m.getAttr(attr, l=True)
		m.setAttr(attr, l=False)

	#--------------------------------|    Break all connection pairs

	for pair in connections:
		m.disconnectAttr(pair[0], pair[1])

	#--------------------------------|    Return info

	return {'lockStates':lockStates, 'connections':connections}

def _restorePlugStates(states):
	for src, dest in states['connections']:
		m.connectAttr(src, dest, f=True)

	for plug, lockState in states['lockStates'].items():
		m.setAttr(plug, l=lockState)

def reorder(node,attrNames):
	"""
	Rebuilds attributes in the specified order.

	:param node: the node that carries the specified attributes
	:type node: str, :class:`~pymel.core.general.PyNode`
	:param attrNames: attribute names, in the preferred order
	:type attrNames: list, tuple
	:return: The rebuilt and reordered attributes.
	:rtype: list of :class:`~paya.plugtypes.attribute.Attribute`
	"""
	# Make sure undo queue is on

	undoState = {}

	for queryFlag in (
		'state',
		'infinity',
		'length'
		):
		undoState[queryFlag] = m.undoInfo(q=True,**{queryFlag:True})

	m.undoInfo(
		state=True,
		infinity=True,
		stateWithoutFlush=True
		)

	try:
		node = p.PyNode(node)
		states = _releasePlugsAndReturnStates(node)
		plugs = [node.attr(x) for x in attrNames]

		out = []

		for attrName, plug in zip(attrNames, plugs):
			m.deleteAttr(str(plug))
			m.undo()

			plug = node.attr(attrName)
			out.append(plug)

		_restorePlugStates(states)

	finally:
		m.undoInfo(
			stateWithoutFlush=True,
			**undoState
			)

	return out

__section_enum__ = '       '

