"""
The contents of this module can be directly accessed via the
:py:mod:`paya.runtime` interface. This includes:

    * The entire :py:mod:`pymel.core` namespace
    * :class:`~paya.names.Name`
    * :func:`~paya.lib.mathops.makeMatrix` / ``mm``

Any module-level variables or functions added here will also become available
via :py:mod:`paya.runtime`.

.. warning::

    When customising this module, take care not to **shadow** factory commands from
    :py:mod:`pymel.core`. Doing so may break code that accesses such commands via
    :py:mod:`paya.runtime`.
"""

from pymel.core import *
from paya.lib.names import Name