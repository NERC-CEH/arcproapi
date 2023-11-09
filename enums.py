from enum import Enum as _Enum

import arcproapi.mixins as _mixins


class EnumSpatialReference(_mixins.MixinEnumHelper, _Enum):
    """ Enums representing spatial references, to expand as required.

    These enums represent the strings returned by arcpy.da.Describe(<layer>)['spatialReference'].name
    """
    GCS_WGS_1984 = 1
    British_National_Grid = 2
    
    
    
class EnumFieldProperties(_mixins.MixinEnumHelper, _Enum):
    """
    Enumeration for properties of field object.

    Can be used as an aide-memoir when interacting with Field objects,
    or more usefully in structure.FieldsDescribe instances.

    Notes:
        field is a custom property that is NOT a member of arcpy.Field. It is used in structure.FieldsDescribe
    """
    aliasName = 1
    baseName = 2
    defaultValue = 3
    domain = 4
    editable = 5
    isNullable = 6
    length = 7
    name = 8
    precision = 9
    required = 10
    scale = 11
    type = 12
    field = 13  # This is a custom one used by structure
