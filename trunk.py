from fnmatch import fnmatch
import os
import inspect
from pathlib import Path

from paya.util import short


class Trunk:
    """
    A subclass of :class:`Trunk` is aware of the directory it was defined in.
    This is useful for sourcing inherited dependencies (e.g. control shape
    templates, weight files etc.) in rig or rig part construction.
    """

    #--------------------------------------------|    Home directory detection

    def __init_subclass__(cls, **kwargs):
        cls.__home__ = Path(os.path.dirname(inspect.getfile(cls)))

    #--------------------------------------------|    Retrievals

    @classmethod
    def getDir(cls):
        """
        :return: The directory this class was defined in.
        :rtype: :class:`~pathlib.Path`
        """
        return cls.__home__

    @classmethod
    def getDirs(cls):
        """
        :return: The home directory of every :class:`Trunk` subclass in the
            MRO.
        :rtype: [:class:`~pathlib.Path`]
        """
        out = []

        for c in cls.__mro__:
            try:
                out.append(c.__home__)
            except AttributeError:
                break

            if not issubclass(c, Trunk):
                break

        return out

    @classmethod
    @short(inherited='i')
    def findFiles(cls, pattern, first=False, inherited=True):
        """
        :param str pattern: a glob-style matching pattern, e.g. ``'*.json'``
        :param bool first: return the first matching file; defaults to
            ``False``
        :param bool inherited/i: look inside the home directory of every
            :class:`Trunk` subclass in the MRO; defaults to ``True``
        :return: Either a single file path, or a list of file paths.
        :rtype: :class:`~pathlib.Path`, [:class:`~pathlib.Path`]
        """
        searchDirs = [cls.getDir()] if first else cls.getDirs()
        matches = []

        for searchDir in searchDirs:
            for root, dirs, files in os.walk(searchDir):
                for fil in files:
                    if fnmatch(fil, pattern):
                        fullPath = Path(os.path.join(root, fil))

                        if first:
                            return fullPath

                        matches.append(fullPath)

        if not first:
            return matches

    @classmethod
    @short(inherited='i')
    def findFile(cls, pattern, inherited=True):
        """
        Equivalent to :meth:`findFiles(pattern, first=True [...])
        <findFiles>`.
        """
        return cls.findFiles(pattern, inherited=inherited, first=True)