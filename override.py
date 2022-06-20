import paya.config as config

class ConfigKeyNotFoundError(RuntimeError):
    """
    The specified configuration key doesn't exist.
    """


class Override(object):
    """
    Context manager. Overrides paya configuration keys for the block. The
    configuration keys must exist.

    This class can be imported from :mod:`paya.overrides` or accessed
    directly on :mod:`paya.runtime`.

    :Example:
        .. code-block:: python

            with r.Override(suffix=False):
                r.createNode('joint')

    :raises ConfigKeyNotFoundError: The configuration key doesn't exist.
    """

    def __init__(self, **overrides):
        self._overrides = overrides

    def __enter__(self):
        self._prev_states = {}

        for k, v in self._overrides.items():
            try:
                self._prev_states[k] = getattr(config, k)

            except AttributeError:
                raise ConfigKeyNotFoundError

            setattr(config, k, v)

        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        for k, v in self._prev_states.items():
            setattr(config, k, v)

        return False

def resolve(argName, userVal):
    """
    Internal use. Used for quick resolution of user arguments. If an argument
    is None, a default is sought under config and returned. Otherwise, the
    user value is returned. The argument must exist as a configuration key.

    :param argName: the argument name
    :param userVal: the user value
    :raises ConfigKeyNotFoundError: No configuration key with a matching name
        was found.
    :return: The resolved value for the argument.
    """
    if hasattr(config, argName):
        if userVal is None:
            return getattr(config, argName)

        return userVal

    raise ConfigKeyNotFoundError