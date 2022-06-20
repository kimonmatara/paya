"""
Defines package-level configuration flags. Currently, these are:

.. list-table::
   :widths: 25 25 50
   :header-rows: 1

   * - Flag
     - Default Value
     - Description
   * - ``patchOnLoad``
     - ``True``
     - Call :py:meth:`~paya.runtime.Runtime.start` the first time :mod:`paya.runtime` is imported.
   * - ``autoSuffix``
     - ``True``
     - Apply :ref:`node suffixes <Automatic Suffixes>` automatically.

More options may be added in future Paya releases.
"""
import maya.mel as mel

# Importing behaviour

patchOnLoad = True # runs PyMEL patching as soon as paya.runtime is loaded

# Name management

suffixNodes = True
padding = 0
inheritNames = True

# Default skeleton building

downAxis = 'y'
upAxis = 'x'