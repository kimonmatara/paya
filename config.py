"""
Reads ``config.json`` into a ``config`` dictionary on import.
"""

from functools import wraps
import re
import inspect
import os
import json

from paya.util.functions import undefined
import maya.cmds as m


path = os.path.join(os.path.dirname(__file__), 'config.json')

with open(path, 'r') as f:
    data = f.read()

config = json.loads(data)

# If useOffsetParentMatrix is undefined in config, set it to True only if
# Maya >= 2022, to avoid bugs with earlier implementations
mayaIntVersion = int(re.findall(r"[0-9]{4}", m.about(version=True))[0])
config.setdefault('useOffsetParentMatrix', mayaIntVersion >= 2022)


class Config:
    """
    Context manager that takes overrides to ``config`` as keyword arguments.
    """
    def __init__(self, **overrides):
        self._overrides = overrides

    def __enter__(self):
        self._prev_config = config.copy()
        config.update(self._overrides)

    def __exit__(self, exc_type, exc_val, exc_tb):
        config.clear()
        config.update(self._prev_config)


def takeUndefinedFromConfig(f):
    """
    Function decorator. Intercepts any keyword arguments that have been set
    to, or left at a default of,
    :class:`undefined <paya.util.functions.Undefined>` and swaps them out with
    values from ``config``.

    :param f: the function to wrap
    :return: The wrapped function.
    """
    params = inspect.signature(f).parameters
    kwnames = [param.name for param in params.values() \
             if param.kind == inspect.Parameter.KEYWORD_ONLY]

    @wraps(f)
    def wrapped(*args, **kwargs):
        _kwargs = {}

        for kwname in kwnames:
            val = kwargs.get(kwname, params[kwname].default)
            if val is undefined:
                val = config[kwname]
            _kwargs[kwname] = val

        return f(*args, **_kwargs)

    return wrapped