from paya.util import short
import paya.runtime as r

class ObjectSet:

    def subsets(self):
        """
        :return: Any object sets nested under this one.
        :rtype: :class:`list`
        """
        return [member for member in self.members() \
            if isinstance(member, r.nodetypes.ObjectSet)]

    @short(recursive='r')
    def remove(self, recursive=False):
        """
        Removes this object set.

        :param bool recursive/r: remove nested object sets recursively;
            defaults to ``False``
        """
        if recursive:
            subsets = self.subsets()

        r.delete(self)

        if recursive:
            for subset in subsets:
                subset.remove(r=True)