import re
import time
import os
import shutil
from pathlib import Path

import maya.cmds as m
import pymel.core as p
from pymel.util import expandArgs
from paya.util import short, without_duplicates
from paya.trunk import Trunk
from paya.lib.evalgraph import EvalGraph


class Rig(Trunk):

    #-------------------------------------------------------------|
    #-------------------------------------------------------------|    CONFIGURATION
    #-------------------------------------------------------------|

    __graph__ = []  # List of lists; each list should describe
                    # directioned connections between two or more
                    # nodes

    @classmethod
    def getAssetName(cls):
        """
        :return: A basename for the asset associated with this rig class.
            In this implementation, this is merely the non-capitalized name
            of this class, but can be overriden freely.
        :rtype: :class:`str`
        """
        out = cls.__name__
        return out[0].lower()+out[1:]

    #-------------------------------------------------------------|
    #-------------------------------------------------------------|    TRUNK
    #-------------------------------------------------------------|

    @classmethod
    def findTrunkScene(cls, name):
        """
        Convenience method. Looks for a Maya scene dependency across this
        rig's :class:`trunk <paya.trunk.Trunk>` directories.

        :param str name: the name of the scene (e.g. ``'layout.ma'``); if
            the extension is omitted, both Maya extensions (``'.ma'`` and
            ``'.mb'``) will be considered
        :return: The path to a matching scene, if one is found.
        :rtype: :class:`~pathlib.Path`, ``None``
        """
        head, tail = os.path.splitext(name)

        if tail in ['.ma', 'mb']:
            exts = [tail]
        else:
            exts = ['.ma', '.mb']

        for ext in exts:
            name = head+ext
            found = cls.findFile(name)

            if found is not None:
                return found

    @classmethod
    def exportAllToTrunkScene(cls, name):
        """
        Exports the full contents of the currently-open scene to the
        :class:`trunk <paya.trunk.Trunk>` directory for this rig class.

        :Example:

        .. code-block:: python

            cls.exportAllToTrunkScene('layout.ma')

        :param str name: the name of the scene to save into; if the extension
            is omitted, it will be set to ``'.ma'`` (``mayaAscii``)
        :return: The full export path.
        :rtype: :class:`~pathlib.Path`
        """
        head, tail = os.path.splitext(name)

        if not tail:
            tail = '.ma'

        filename = head+tail
        fullPath = cls.getDir().joinpath(filename)

        m.file(fullPath.as_posix(),
               exportAll=True,
               options='v=0;',
               type='mayaAscii',
               force=True)

        print("Exported scene contents to: {}".format(fullPath))
        return fullPath

    @classmethod
    @short(namespace='ns')
    def referenceTrunkScene(cls, name, namespace=None):
        """
        Locates and references the specified trunk scene.

        :param str name: the name of the scene to retrieve; if the extension
            is omitted, both ASCII and binary scene files will be considered
        :param str namespace/ns: a namespace for the reference; if omitted,
            it will be set to the file basename; defaults to ``None``
        :return: The retrieved file path.
        :rtype: :class:`~pathlib.Path`
        """
        path = cls.findTrunkScene(name)

        if path is None:
            raise RuntimeError(
                "No Maya scene matches found for "+
                "'{}' in the trunks.".format(name))

        if namespace is None:
            namespace = os.path.splitext(name)[0]

        m.file(
            path.as_posix(),
            reference=True,
            namespace=namespace
        )

        return path

    @classmethod
    def unreferenceTrunkScene(cls, name):
        """
        Looks for any matches for the specified trunk scene amongst current
        references and removes them.

        :param str name: the name of the trunk scene; if the extension is
            omitted, both ASCII and binary scene files will be considered
        :return: A list of matching reference paths that were removed
            (without copy numbers).
        :rtype: [:class:`~pathlib.Path`]
        """
        head, tail = os.path.splitext(name)

        if tail in ['.ma', '.mb']:
            exts = [tail]
        else:
            exts = ['.ma', '.mb']

        matches = []

        for ext in exts:
            matches += cls.findFiles('{}{}'.format(head, ext))

        matches = [match.as_posix() for match in matches]

        refs = m.file(q=True, reference=True)

        out = []

        for ref in refs:
            basepath = re.match(
                r"^(.*?)(?:{.*})?$",
                ref
            ).groups()[0]

            if basepath in matches:
                m.file(ref, rr=True)
                out.append(basepath)

        return without_duplicates(basepath)

    #-------------------------------------------------------------|
    #-------------------------------------------------------------|    BUILD MANAGEMENT
    #-------------------------------------------------------------|

    #---------------------------------------------------------|    Snapshots

    @classmethod
    def getSnapshotsDir(cls, create=False):
        """
        :return: The directory for rig build snapshots. In this
            implementation, it's ``'<maya project>/rig_build_snapshots'``,
            but can be overriden freely.
        :rtype: :class:`~pathlib.Path`
        """
        workdir = Path(m.workspace(q=True, rd=True))
        out = workdir.joinpath('rig_build_snapshots')

        if create:
            if not out.exists():
                os.makedirs(out)

        return out

    @classmethod
    def snapshotExists(cls, stageName):
        """
        :param str stageName: the name of the stage for which to source a
            snapshot
        :return: ``True`` if there's a snapshot for the specified build
            stage, otherwise ``False``.
        :rtype: :class:`bool`
        """
        return cls.getSnapshotScene(stageName).is_file()

    @classmethod
    def removeSnapshot(cls, stageName):
        """
        Removes the snapshot for the specified stage name, if it exists.

        :param str stageName: the build stage for the snapshot
        """
        path = cls.getSnapshotScene(stageName)
        
        try:
            os.remove(path)
            print("Removed snapshot: {}".format(path))
        except IOError:
            pass

    @classmethod
    def clearSnapshots(cls):
        """
        Deletes the snapshots directory along with its contents.
        """
        dr = cls.getSnapshotsDir()

        if dr.is_dir():
            pdir = dr.parent
            shutil.rmtree(dr)

    @classmethod
    def getSnapshotScene(cls, stageName):
        """
        :param str stageName: the name of the build stage for which to source
            a snapshot scene.
        :return: The path to a Maya scene snapshot for the specified stage.
            Note that this does not check whether the file actually exists.
        :rtype: :class:`~pathlib.Path`
        """
        return cls.getSnapshotsDir().joinpath('{}.ma'.format(stageName))

    @classmethod
    def pruneSnapshots(cls, dirtyStages=None):
        """
        Performs housekeeping on build-stage snapshots. For every stage, if
        there isn't a snapshot, snapshots for all downstream stages are also
        deleted.

        :param dirtyStages: one or more stages for which snapshots should
            be explicitly deleted, along with those of all their descendants;
            defaults to ``None``
        :type dirtyStages: :class:`str`, [:class:`str`]
        """
        graph = cls.getBuildGraph()
        cleared = set()

        # Remove any snapshots for 'dirty' stages
        if dirtyStages:
            dirtyStages = without_duplicates(expandArgs(dirtyStages))

            for dirtyStage in dirtyStages:
                if cls.snapshotExists(dirtyStage):
                    cls.removeSnapshot(dirtyStage)
                    cleared.add(dirtyStage)

        # Evaluate from start terminals; propagate any gaps in snapshots
        # downstream
        startTerminals = graph.nodes(startTerminals=True)

        for startTerminal in startTerminals:
            sequence = [startTerminal] \
                       + graph.getNodesDownstreamOf(startTerminal)

            for node in sequence:
                if not cls.snapshotExists(node):
                    for desc in graph.getNodesDownstreamOf(node):
                        if desc not in cleared:
                            cls.removeSnapshot(desc)
                            cleared.add(desc)
                    
                    break

                cleared.add(node)

    #---------------------------------------------------------|    Graph evaluation

    @classmethod
    def getBuildGraph(cls):
        """
        :return: An evaluation graph built off the connection segments
            in the ``__graph__`` attribute on this class.
        :rtype: :class:`~paya.lib.evalgraph.EvalGraph`
        """
        return EvalGraph.fromSegments(cls.__graph__)

    @classmethod
    def build(cls,
              targetStages=None,
              rebuildDependencies=True,
              clearSnapshots=False,
              dirtyStages=None):
        """
        Runs a rig-building sequence.

        :param targetStages: one or more build stages to evaluate for; if this
            is omitted, the entire build graph will be evaluated; defaults to
            ``None``
        :type targetStages: :class:`str`, [:class:`str`]
        :param bool rebuildDependencies: rebuild stage dependencies instead of
            relying on snapshots; defaults to ``True``
        :param bool clearSnapshots: clear all snapshots before building;
            defaults to ``False``
        :param dirtyStages: one or more stages which should be considered
            'dirty', meaning their snapshots, and those of their descendants,
            should be cleared before building; defaults to ``None``
        :type dirtyStages: :class:`str`, [:class:`str`]
        """
        print("\n#----------|    Start of '{}' Build    |----------#".format(cls.__name__))

        startTime = time.time()
        graph = cls.getBuildGraph()

        #------------------------|    Determine target stages

        if targetStages:
            targetStages = graph.reduceTargetList(targetStages)
        else:
            targetStages = graph.nodes(endTerminals=True)

        print("Resolved target stages: {}".format(", ".join(targetStages)))

        #------------------------|    Pre-evaluate dependency trees for
        #------------------------|    all the stages, pre-source the
        #------------------------|    methods for early erroring

        targetStageSequences = [
            graph.getNodesUpstreamOf(targetStage) + [targetStage]
            for targetStage in targetStages
        ]

        methodsMap = {}

        for targetStageSequence in targetStageSequences:
            for stageToBuild in targetStageSequence:
                try:
                    methodsMap.setdefault(stageToBuild,
                                          getattr(cls, stageToBuild))
                except AttributeError:
                    raise RuntimeError(
                        "Missing build method for stage"+
                         " '{}'.".format(stageToBuild)
                    )

        #------------------------|    Housekeep snapshots

        if clearSnapshots:
            cls.clearSnapshots()
        else:
            cls.pruneSnapshots(dirtyStages=dirtyStages)

        #------------------------|    Iterate

        resolvedStages = []
        previousStage = ''

        for targetStage in targetStages:
            buildSequence = \
                graph.getNodesUpstreamOf(targetStage) + [targetStage]

            for stageToBuild in buildSequence:
                snapshot = cls.getSnapshotScene(stageToBuild)

                if snapshot.exists():
                    # Just open the scene, so that the next stage in line
                    # can build into it
                    m.file(snapshot.as_posix(), open=True, force=True)
                else:
                    dependencies = graph.getNodeInputs(stageToBuild)

                    # If this stage has one input, and that's previousStage,
                    # just build into the currently-open scene; otherwise,
                    # create a new scene and import all dependencies
                    # before running the build

                    if not (
                        len(dependencies) is 1
                        and dependencies[0] == previousStage
                    ):
                        m.file(newFile=True, force=True)

                        for dependency in dependencies:
                            p.importFile(
                                cls.getSnapshotScene(dependency).as_posix()
                            )

                    # Source the namesake method, run it
                    getattr(cls, stageToBuild)()

                    p.renameFile(snapshot)
                    p.saveFile()

                resolvedStages.append(stageToBuild)
                previousStage = stageToBuild

        endTime = time.time()

        #------------------------|    Print summary

        print("#----------|    End of '{}' Build    |----------#".format(cls.__name__))
        print("Resolved nodes: {}".format(", ".join(resolvedStages)))
        print("Elapsed time: {} seconds".format(endTime-startTime))