"""
The contents of this module can be directly accessed via the
:py:mod:`paya.runtime` interface. This includes:

    * The entire :mod:`pymel.core` namespace
    * :class:`~paya.lib.names.Name`
    * :func:`~paya.lib.mathops.createMatrix` / ``cm``

Any module-level variables or functions added here will also become available
via :py:mod:`paya.runtime`.

.. warning::

    When customising this module, take care not to **shadow** factory commands from
    :mod:`pymel.core`. Doing so may break code that accesses such commands via
    :mod:`paya.runtime`.
"""

from pymel.core import *
from paya.lib.names import Name
from paya.lib.mathops import createMatrix, cm