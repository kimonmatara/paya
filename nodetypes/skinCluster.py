from paya.util import short
import pymel.util as _pu
import paya.runtime as r


class SkinCluster:

    #------------------------------------------------------------|    Constructor

    @classmethod
    @short(
        bindMethod='bm',
        dropoffRate='dr',
        maximumInfluences='mi',
        name='n',
        normalizeWeights='nw',
        obeyMaximumInfluences='omi',
        skinMethod='sm',
        toSelectedBones='tsb',
        weightDistribution='wd',
        nameAfterGeo='nag',
        geometry='g',
        influence='inf',
        force='f'
    )
    def create(
            cls,
            *args,
            bindMethod=0, # closest
            dropoffRate=4.5,
            maximumInfluences=None,
            name=None,
            normalizeWeights=1, # interactive
            obeyMaximumInfluences=False,
            skinMethod=0, # linear
            toSelectedBones=True,
            weightDistribution=0, # distance
            nameAfterGeo=False,
            geometry=None,
            influence=None,
            multi=False,
            force=False,
            **kwargs
    ):
        """
        Lightweight convenience wrapper / constructor for skinClusters, with the
        following differences from the standard
        :func:`~pymel.core.animation.skinCluster` command:

        -   Positional arguments can be omitted, and the 'geometry' and
            'influence' keyword arguments used instead on creation
        -   A select subset of flags are pre-loaded with common defaults (see
            below)
        -   Added 'nameAfterGeo / nag' option
        -   Added 'multi' option
        -   Added 'force' option

        :param \*args: forwarded to :func:`~pymel.core.animation.skinCluster`
        :param int bindMethod/bm: see Maya help; defaults to 0 (closest)
        :param float dropoffRate/dr: see Maya help; defaults to 4.5
        :param maximumInfluences/mi: see Maya help; defaults to None
        :type maximumInfluences/mi: None, int
        :param name/n: one or more name elements for the deformer; ignored if
            'nameAfterGeo' is True; defaults to None
        :type name/n: list, tuple, None, str, int
        :param int normalizeWeights/nw: see Maya help; defaults to 1
            (interactive)
        :param bool obeyMaximumInfluences/omi: see Maya help; defaults to
            False
        :param int skinMethod/sm: see Maya help; defaults to 0 (linear)
        :param bool toSelectedBones/tsb: see Maya help; defaults to True
        :param int weightDistribution/wd: see Maya help; defaults to 0
            (distance)
        :param bool nameAfterGeo/nag: derive deformer names from geometry
            names; defaults to False
        :param geometry/g: the geometry to bind to; defaults to None
        :type geometry/g: list, tuple,
            :class:`~paya.runtime.nodes.DeformableShape`,
            :class:`~paya.runtime.nodes.Transform`
        :param influence/inf: one or more influences; defaults to None
        :type influence/inf: list, tuple,
            :class:`~paya.runtime.nodes.Transform`
        :param bool multi: set this to True to create multiple skinClusters
            across all passed geometries; defaults to False
        :param bool force/f: remove any existing skinClusters from the passed
            geometries; defaults to False
        :param \*\*kwargs: forwarded to
            :func:`~pymel.core.animation.skinCluster`
        :return: :class:`SkinCluster` or [:class:`SkinCluster`]
        """
        #-------------------------------------------|    Prep

        # Sift geos / infls

        infls, geos = cls._splitArgsIntoInflsGeos(
            *args, influence=influence, geometry=geometry)

        numGeos = len(geos)
        numInfls = len(infls)

        if not numGeos:
            raise RuntimeError("No geometries specified.")

        if not numInfls:
            raise RuntimeError("No influences specified.")

        buildKwargs = {
            'bm': bindMethod,
            'dr': dropoffRate,
            'nw': normalizeWeights,
            'sm': skinMethod,
            'tsb': toSelectedBones,
            'wd': weightDistribution
        }

        if maximumInfluences is not None:
            buildKwargs['mi'] = maximumInfluences
            buildKwargs['omi'] = obeyMaximumInfluences

        buildKwargs.update(kwargs)

        if numGeos > 1:
            if multi:
                out = []

                for geo in geos:
                    result = cls.create(
                        inf=infls,
                        g=geo,
                        nag=nameAfterGeo,
                        n=name, f=force,
                        **buildKwargs
                    )

                    out.append(result)

            else:
                raise RuntimeError(
                    "Set 'multi' to True to bind more than one geometry."
                )

        if force:
            existing = []

            for geo in geometry:
                existing += cls.getFromGeo(geo)

            if existing:
                r.delete(existing)

        # Resolve name

        if nameAfterGeo:
            geoBasename = geos[0
                ].toTransform().basename(sts=True, sns=True)

            name = cls.makeName(geoBasename)

        else:
            name = cls.makeName(name)

        buildKwargs['n'] = name

        # Exec

        buildArgs = infls + geos

        return r.skinCluster(*buildArgs, **buildKwargs)

    @staticmethod
    def _splitArgsIntoInflsGeos(*args, geometry=None, influence=None):
        geos = []
        infls = []

        items = list(map(r.PyNode, _pu.expandArgs(*args)))

        for item in items:
            if isinstance(item, r.nodetypes.DeformableShape):
                geos.append(item)

            elif isinstance(item, r.nodetypes.Transform):
                shapes = item.getShapes(noIntermediate=True)

                states = [isinstance(shape,
                    r.nodetypes.DeformableShape) for shape in shapes]

                if all(states):
                    geos.append(item)

                elif not any(states):
                    infls.append(item)

                else:
                    raise RuntimeError(
                        "Can't determine whether {} is a geometry or "+
                        "influence. Pass through 'influence' or 'geometry'"+
                        " to disambiguate.".format(item)
                    )

            else:
                raise RuntimeError(
                        "Can't determine whether {} is a geometry or "+
                        "influence. Pass through 'influence' or 'geometry'"+
                        " to disambiguate.".format(item)
                    )

        if geometry:
            geos += list(map(r.PyNode, _pu.expandArgs(geometry)))

        if influence:
            infls += list(map(r.PyNode, _pu.expandArgs(influence)))

        return infls, geos