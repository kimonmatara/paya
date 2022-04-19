"""
This module imports the entire :py:mod:`pymel.core` namespace. It is in turn
served by the :py:mod:`paya.runtime` interface. Any module-level variables or
functions added here will therefore also become available via that interface.

.. warning::

    When customising this module, take care not to **shadow** factory commands from
    :py:mod:`pymel.core`. Doing so may break code that accesses such commands via
    :py:mod:`paya.runtime`.
"""

from pymel.core import *