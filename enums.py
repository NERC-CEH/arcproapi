from enum import Enum as _Enum

import arcproapi.mixins as _mixins


class EnumSpatialReference(_Enum, _mixins.MixinEnumHelper):
    """ Enums representing spatial references, to expand as required.

    These enums represent the strings returned by arcpy.da.Describe(<layer>)['spatialReference'].name
    """
    GCS_WGS_1984 = 1
    British_National_Grid = 2