"""
Some of these methods were originally taken from the
arcapi project by Filip Kral, Caleb Mackey (01/02/2014)
Their original repository can be found on CEH's github site.
https://github.com/NERC-CEH/arcapi

The intention is to make this library seamlessly compatible with
ArcMap arcpy and ArcGISPro arcpy. However due to daily requirements
 this has slipped by the wayside and is currently only compatible
 with ArcGISPro.

 Compatibility with ArcMap will be a PITA because of Python differences
 between 2 and 3.

Much work is still required to make this package compatible with
both. (Graham Monkman 9/3/2022)
"""
import arcpy as _arcpy


__all__ = ['charts_stats', 'common', 'data', 'display', 'environ',
           'errors', 'http', 'meta', 'projections', 'raster', 'sql',
           'struct']

from enum import Enum as _Enum

from arcproapi.errors import *


class Version(_Enum):
    """Version enumeration"""
    ArcPro = 1
    ArcMap = 2


def version():
    """() -> Enum:Version
    Get version"""
    d = _arcpy.GetInstallInfo()
    return Version.ArcPro if d['ProductName'] == 'ArcGISPro' else Version.ArcMap

def current_project():
    """Return handle to the CURRENT map document.
    ***Can be used only in an ArcMap session***
    """
    if version() == Version.ArcPro:
        return mp.ArcGISProject("CURRENT")
    return mp.MapDocument("CURRENT")  # noqa



if version() == Version.ArcPro:
    import arcpy.mp as mp  # noqa
    #import arcpy.MetadataImporter_conversion # noqa
else:
    import arcpy.mapping as mp  # noqa
