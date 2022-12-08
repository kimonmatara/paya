import re
import maya.cmds as m
import pymel.util as _pu
import pymel.core as p
from paya.util import AccessorOnNode

#------------------------------------------------------------|    Reordering

def expandAttrListToParentsAndChildren(attrList, instances=True):
    """
    Given a list of attributes, expands to include compound children.
    
    :param attrList: the list of attributes to expand
    :type attrList: list of str or
        :class:`~paya.runtime.plugs.Attribute`
    :param bool instances: return
        :class:`~paya.runtime.plugs.Attribute` instances rather than
        strings; defaults to True 
    :return: The expanded attribute list.
    :rtype: list of str or :class:`~paya.runtime.plugs.Attribute`
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

	userAttrs = list(filter(
		lambda x: x.get(k=True) or x.get(cb=True),
		node.listAttr(ud=True)
		))

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

	allInvolvedAttrs = [str(userAttr) for userAttr in userAttrs]

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

def reorder(node, *attrNames):
    """
    Rebuilds attributes in the specified order. The attributes must be
    dynamic, animatable and not compounds or multis. Lock states are dodged
    and connections are preserved:

    :param node: the node that carries the attributes
    :type node: str, :class:`~paya.runtime.nodes.DependNode`
    :param attrNames: the names of the attributes to reorder, in the preferred
        order
    :type attrNames: list of str, str
    :return: The rebuilt attributes.
    :rtype: list of :class:`~paya.runtime.plugs.Attribute`
    """
    attrNames = list(_pu.expandArgs(*attrNames))

    # Make sure undo queue is on
    undoState = {}

    for queryFlag in (
            'state',
            'infinity',
            'length'
    ):
        undoState[queryFlag] = m.undoInfo(q=True,**{queryFlag:True})

    m.undoInfo(state=True, infinity=True, stateWithoutFlush=True)

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

#------------------------------------------------------------|    Sections

__section_enum__ = '       '


class Section:

    def __init__(self, sectionAttr, owner):
        self._attr = sectionAttr
        self.owner = owner

    #----------------------------------------|    Basic inspections

    def node(self):
        """
        :return: The owner node.
        :rtype: :class:`~paya.runtime.nodes.DependNode`
        """
        return self.owner.owner

    def attr(self):
        """
        :return: The section attribute.
        :rtype: :class:`~paya.runtime.plugs.Enum`
        """
        return self._attr

    def _getName(self):
        return self._attr.attrName()

    name = property(fget=_getName)

    #----------------------------------------|    Reordering

    def _sendAboveOrBelow(self, attrName, below=True):
        allPlugs = [self.attr()] + self.members()
        allNames = [plug.attrName() for plug in allPlugs]

        node = self.node()
        kwargs = {'below' if below else 'above': attrName}
        node.reorderAttrs(allNames, **kwargs)

        return self

    def sendAbove(self, attrName):
        """
        Send this section and its members above the specified attribute in
        the channel box.

        :param str attrName: the reference attribute name
        :return: ``self``
        :rtype: :class:`Section`
        """
        return self._sendAboveOrBelow(attrName, below=False)

    def sendBelow(self, attrName):
        """
        Send this section and its members below the specified attribute in
        the channel box.

        :param str attrName: the reference attribute name
        :return: ``self``
        :rtype: :class:`Section`
        """
        return self._sendAboveOrBelow(attrName, below=True)

    #----------------------------------------|    Member access

    def members(self):
        return list(dict(self.node().getAttrSectionMembership())[self.name])

    def __iter__(self):
        return iter(self.members())

    def __getitem__(self, item):
        return self.members()[item]

    def __len__(self):
        return len(self.members())

    def __contains__(self, attr):
        return attr in self.members()

    #----------------------------------------|    Member editing

    def collect(self, *attrNames, top=False):
        """
        :param attrNames: the names of the attributes to move into this
            section
        :type attrNames: list of str
        :param bool top: insert the attributes before existing members rather
            than after; defaults to False
        :return: ``self``
        :rtype: :class:`Section`
        """
        namesToAdd = list(_pu.expandArgs(*attrNames))
        members = self.members()

        memberNames = [member.attrName() for member in members]
        memberNames = list(filter(lambda x: x not in namesToAdd, memberNames))

        if top:
            newList = namesToAdd + memberNames

        else:
            newList = memberNames + namesToAdd

        self.node().reorderAttrs(attrNames, below=self.attr().attrName())

        return self

    #----------------------------------------|    Repr

    def __str__(self):
        """
        :return: The section name.
        :rtype: str
        """
        return self.attr().attrName()

    def __repr__(self):
        return "{}.{}['{}']".format(
            repr(self.node()),
            self.owner.name,
            str(self)
        )


class Sections(AccessorOnNode):

    #----------------------------------------|    Member access

    def __getitem__(self, indexOrKey):
        """
        :param indexOrKey: the section index or name
        :type indexOrKey: int or str
        :return: A manager object for the section.
        :rtype: :class:`Section`
        """
        node = self.node()
        membership = node.getAttrSectionMembership()

        if isinstance(indexOrKey, str):
            attr = node.attr(indexOrKey)

            if attr.isSectionAttr():
                return Section(attr, self)

            raise RuntimeError("Not a section attribute: {}".format(attr))

        entry = membership[indexOrKey]
        sectionAttr = node.attr(entry[0])

        return Section(sectionAttr, self)

    def names(self):
        """
        :return: The names of all available sections.
        :rtype: list of str
        """
        return [entry[0] for entry in self.node().getAttrSectionMembership()]

    def _members(self):
        sectionAttrs = self.node().getSectionAttrs()
        return [Section(attr, self) for attr in sectionAttrs]

    def __iter__(self):
        """
        :return: an iterator of :class:`Section` objects
        """
        sections = self._members()
        return iter(sections)

    def __len__(self):
        """
        :return: the number of section attributes on the node
        :rtype: int
        """
        return len(self.node().getSectionAttrs())

    def __contains__(self, sectionName):
        """
        :param sectionName: the section name
        :return: True if the section name exists, otherwise False
        """
        return sectionName in self.names()

    #----------------------------------------|    Additions

    def add(self, sectionName):
        """
        Creates a new attribute section.

        :param sectionName: the name of the section
        :return: A manager object for the new section.
        :rtype: :class:`Section`
        """
        attr = self.node().addSectionAttr(sectionName)
        return Section(attr, self)

    #----------------------------------------|    Removals

    def __delitem__(self, indexOrKey):
        """
        :param indexOrKey: can be a list index or a section name
        :type indexOrKey: str or int
        """
        node = self.node()

        if isinstance(indexOrKey, str):
            attr = node.attr(indexOrKey)

            if attr.isSectionAttr():
                attrName = attr.attrName()

            else:
                raise RuntimeError("Not a section attribute: {}".format(attr))

        else:
            attrName = node.getAttrSectionMembership()
            attr = node.attr(attrName)

        attr.unlock()
        node.deleteAttr(attrName)

    def clear(self):
        """
        Removes all section attributes from the node. Member attributes are
        not removed.
        """
        node = self.node()

        for name in self.names():
            attr = node.attr(name)
            attr.unlock()
            node.deleteAttr(name)