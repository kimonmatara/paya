import os
from pathlib import Path
import maya.cmds as m
import paya.runtime as r


class ReferenceBiped(r.rigs.Rig):
    """
    ..warning::

        This is a stub / beta class, and should not be relied on for
        production purposes.
    """

    __graph__ = [
        ['init', 'buildParts', 'attachParts', 'bind', 'config']
    ]

    #-------------------------------------------------------------|
    #-------------------------------------------------------------|    MODEL MANAGEMENT
    #-------------------------------------------------------------|

    @classmethod
    def getAssetDir(cls):
        """
        :return: The path to an ``assets`` subdirectory under the Maya project.
        :rtype: :class:`~pathlib.Path`
        """
        ws = Path(m.workspace(q=True, rd=True))
        return ws.joinpath('assets', cls.getAssetName())

    @classmethod
    def getModelScene(cls):
        """
        :return: The path to a model scene which, in this base class, is
            ``model.ma`` under the path returned by :meth:`getAssetDir`.
        :rtype: :class:`~pathlib.Path`
        """
        return cls.getAssetDir().joinpath('model.ma')

    @classmethod
    def importModelScene(cls):
        path = cls.getModelScene().as_posix()
        r.importFile(path)

    @classmethod
    def exportAllToModelScene(cls):
        path = cls.getModelScene()

        if not path.parent.is_dir():
            os.makedirs(path.parent)

        m.file(path.as_posix(),
               exportAll=True,
               options='v=0;',
               type='mayaAscii',
               force=True)

        print("Exported model to: {}".format(path))

    #-------------------------------------------------------------|
    #-------------------------------------------------------------|    INIT STAGE
    #-------------------------------------------------------------|

    @classmethod
    def init(cls):
        cls.referenceTrunkScene('layout.ma')
        cls.importModelScene()

    @classmethod
    def buildParts(cls):
        cls.buildGlobalStack()
        cls.buildOffsetControl()

    @classmethod
    def attachParts(cls):
        raise NotImplementedError

    @classmethod
    def bind(cls):
        raise NotImplementedError

    @classmethod
    def config(cls):
        raise NotImplementedError