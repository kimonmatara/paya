from paya.util import short, without_duplicates
from pymel.util import expandArgs

#------------------------------------------------------------|
#------------------------------------------------------------|    ERRORS
#------------------------------------------------------------|

class CycleError(RuntimeError):
    """
    An evaluation cycle has been detected in the graph.
    """

class NoPathError(RuntimeError):
    """
    Couldn't find a path between two requested nodes.
    """

class NonexistentNodeError(RuntimeError):
    """
    A specified node doesn't exist in the graph.
    """

#------------------------------------------------------------|
#------------------------------------------------------------|    CLASS
#------------------------------------------------------------|

class EvalGraph:
    """
    Simple directed-acyclic-graph simulator. Good for rig build sequences etc.

    :Construction by Dictionary:

    :class:`EvalGraph` objects use a dictionary with the following structure:

    .. code-block:: python

        {
            <nodeName>: [inputNodeName, inputNodeName...],
            <nodeName>: [inputNodeName, inputNodeName...],
            [...]
        }

    A :class:`EvalGraph` can be instantiated directly around such a
    dictionary, or via :meth:`fromSegments`, which may be more intuitive.

    :class:`Graphs <EvalGraph>` cannot be edited after instantiation, only
    analysed and evaluated.

    To get a build sequence for the entire graph, either iterate over the
    object or call :meth:`getBuildSequence`.
    """
    #--------------------------------------------------------|    Init

    def __init__(self, dct):
        """
        :param dict dct: the content dictionary
        :raises CycleError: An evaluation cycle has been detected.
        :rtype: :class:`EvalGraph`
        """
        self._dct = dct
        self._expand()

    @classmethod
    def fromSegments(cls, segments):
        """
        :Example:

        .. code-block:: python

            items = [
                ['A', 'C', 'D', 'G'],
                ['B', 'C', 'E', 'H'],
                ['E', 'F', 'G']
            ]

            graph = EvalGraph.fromSegments(items)
            print(list(graph)) # evaluate
            ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H']

        :param list segments: a list of lists (or tuples) where each sublist
            describes left-to-right connections between two or more nodes
        :rtype: :class:`EvalGraph`
        """
        dct = {}

        for segment in segments:
            for i, item in enumerate(segment):
                pool = dct.setdefault(item, [])

                if i > 0:
                    prev = segment[i-1]

                    if prev not in pool:
                        pool.append(prev)

        return cls(dct)

    #--------------------------------------------------------|    Initial analysis

    def _calcAllNodes(self):
        out = []

        for node, inputs in self._dct.items():
            for item in inputs + [node]:
                if item not in out:
                    out.append(item)

        return out

    def _calcStartNodes(self):
        return [node for node in self._nodes if not self._dct.get(node)]

    def _calcEndNodes(self):
        allInputs = []

        for node in self._nodes:
            allInputs += self._dct.get(node, [])

        allInputs = set(allInputs)

        return [node for node in self._nodes if node not in allInputs]

    def _calcOrphanNodes(self):
        return [node for node in self._nodes \
            if node in self._startNodes and node in self._endNodes]

    def _expand(self):
        self._nodes = self._calcAllNodes()
        self._cycleCheck()
        self._endNodes = self._calcEndNodes()
        self._startNodes = self._calcStartNodes()
        self._orphanNodes = self._calcOrphanNodes()

    #--------------------------------------------------------|    Basic user inspections

    @short(startTerminals='st',
           endTerminals='et',
           orphan='o')
    def nodes(self,
              startTerminals=False,
              endTerminals=False,
              orphan=False):
        """
        If ``startTerminals``, ``endTerminals`` and ``orphan`` are
        omitted, all nodes will be returned.

        :param bool startTerminals: return only nodes with no inputs;
            defaults to ``False``
        :param bool endTerminals: return only nodes with no outputs;
            defaults to ``False``
        :param bool orphan: return only nodes with no inputs or outputs;
            defaults to ``False``
        :return: A list of node names.
        :rtype: [:class:`str`]
        """
        if any([startTerminals, endTerminals, orphan]):
            bools = [bool(x) for x in (
                startTerminals, endTerminals, orphan)]

            if bools.count(True) > 1:
                raise ValueError("Multiple flags are not supported.")

            if startTerminals:
                return self._startNodes

            if endTerminals:
                return self._endNodes

            return self._orphanNodes

        return self._nodes

    #--------------------------------------------------------|    Topo Analysis

    def getNodeInputs(self, node):
        """
        :param str node: the node whose input nodes to return
        :return: The node's inputs.
        :rtype: [:class:`str`]
        """
        self.assertNodeExists(node)
        return self._dct.get(node, [])

    def getNodeOutputs(self, node):
        """
        :param str node: the node whose output nodes to return
        :return: The node's outputs.
        :rtype: [:class:`str`]
        """
        self.assertNodeExists(node)
        
        return [_node for _node in \
            self._nodes if node in self._dct.get(_node, [])]

    def assertNodeExists(self, node):
        if node not in self._nodes:
            raise NonexistentNodeError(
                "Node does not exist: {}".format(node)
            )

    def _cycleCheck(self):
        for node in self._nodes:
            def _trace(_node, callers):
                if _node in callers:
                    raise CycleError(
                        "Node visited more than once: {}".format(_node)
                    )

                outputs = self.getNodeOutputs(_node)

                if outputs:
                    callers = callers[:]
                    callers.append(_node)

                    for output in outputs:
                        _trace(output, callers)

            _trace(node, [])

    def getNodesUpstreamOf(self, node):
        """
        :param node: the node to trace from
        :return: All nodes upstream of *node*.
        :rtype: [:class:`str`]
        """
        out = []

        def _trace(_node):
            if _node not in out:
                for input in self.getNodeInputs(_node):
                    _trace(input)

                if _node != node:
                    out.append(_node)

        _trace(node)
        return out

    def getNodesDownstreamOf(self, node):
        """
        :param node: the node to trace from
        :return: All nodes downstream of *node*.
        :rtype: [:class:`str`]
        """
        out = []

        def _trace(_node):
            if _node not in out:
                if _node != node:
                    out.append(_node)

                outputs = self.getNodeOutputs(_node)

                if outputs:
                    for output in outputs:
                        _trace(output)

        _trace(node)
        return out

    def getPath(self, start, end):
        """
        :param str start: the start node
        :param str end: the end node
        :raises NoPathError: A path could not be found.
        :return: A path from the start to the end node.
        :rtype: [:class:`str`]
        """
        buff = {}
        
        self.assertNodeExists(start)
        self.assertNodeExists(end)

        def _trace(_node, path):
            path = path[:]
            path.append(_node)

            if _node == end:
                buff['result'] = path

            else:
                for output in self.getNodeOutputs(_node):
                    _trace(output, path)

        _trace(start, [])

        try:
            return buff['result']
        except KeyError:
            raise NoPathError(
                "Couldn't find a path between '{}' and '{}'.".format(start, end))

    def reduceTargetList(self, *targets):
        """
        Given a list of target nodes, returns another list with duplicates
        and implied nodes (i.e. nodes that are already upstream of other
        nodes) removed.

        :param \*targets: the targets to process
        :type \*targets: :class:`str`, [:class:`str`]
        :return: The reduced target list.
        :rtype: :class:`list`
        """
        targets = without_duplicates(expandArgs(*targets))

        for target in targets:
            self.assertNodeExists(target)

        # Remove nodes that are upstream of other nodes in the list
        upstreamMap = {
            target: self.getNodesUpstreamOf(target) \
            for target in targets
        }

        skipNodes = []

        for nodeToPrune in targets:
            for refNode in targets:
                if nodeToPrune == refNode:
                    continue

                if nodeToPrune in upstreamMap[refNode]:
                    skipNodes.append(nodeToPrune)

        return [target for target \
            in targets if target not in skipNodes]

    def getBuildSequence(self, targets=None):
        """
        :param \*targets: optionally, a subset of target nodes to
            evaluate for; if omitted, the graph's downstream-terminating
            nodes will be used as targets
        :type \*targets: :class:`str`, [:class:`str`]
        :raises NonExistentNodeError: A specified target node does
            not exist.
        :return: The full build sequence.
        :rtype: [:class:`str`]
        """
        if targets:
            targets = self.reduceTargetList(*targets)
        else:
            targets = self._endNodes

        fullSequence = []

        for target in targets:
            thisSequence = []

            def _trace(_node):
                if _node not in fullSequence:
                    if _node not in thisSequence:
                        for input in self.getNodeInputs(_node):
                            _trace(input)

                    thisSequence.append(_node)

            _trace(target)
            fullSequence += thisSequence

        return fullSequence