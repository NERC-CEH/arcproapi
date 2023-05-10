"""Projection related stuff"""
import os.path as _path

import arcpy as _arcpy

import arcproapi.httplib as _http



def epsg(epsgcode, form='esriwkt'):
    """Get spatial reference system by EPSG code as string.
    Queries the http://epsg.io website.
    epsgcode -- European Petrol Survey Group code (http://www.epsg.org/)
    form -- Format to return:
        html : HTML
        wkt : Well Known Text
        esriwkt : Esri Well Known Text
        gml : GML
        xml : XML
        proj4 : Proj4
        js : proj4js
        geoserver : GeoServer
        map : MAPfile
        mapserverpython : MapServer - Python
        mapnik : Mapnik
        sql : PostGIS
    Example:
    >>> srs_str_by_epsg(27700, 'esriwkt')
    """
    srsstr = _http.request('http://epsg.io/%s.%s' % (epsgcode, str(form).lower()))
    return srsstr


def project_coordinates(xys, in_sr, out_sr, datum_transformation=None):
    """Project list of coordinate pairs (or triplets).
        xys -- list of coordinate pairs or triplets to project one by one
        in_sr -- input spatial reference, wkid, prj file, etc.
        out_sr -- output spatial reference, wkid, prj file, etc.
        datum_transformation=None -- datum transformation to use
            if in_sr and out_sr are defined on different datums,
            defining appropriate datum_transformation is necessary
            in order to obtain correct results!
            (hint: use _arcpy.ListTransformations to list valid transformations)

    Example:
    >>> dtt = 'TM65_To_WGS_1984_2 + OSGB_1936_To_WGS_1984_NGA_7PAR'
    >>> coordinates = [(240600.0, 375800.0), (245900.0, 372200.0)]
    >>> project_coordinates(coordinates, 29902, 27700, dtt)
    """

    if not type(in_sr) is _arcpy.SpatialReference:
        in_sr = _arcpy.SpatialReference(in_sr)
    if not type(out_sr) is _arcpy.SpatialReference:
        out_sr = _arcpy.SpatialReference(out_sr)

    xyspr = []
    for xy in xys:
        pt = _arcpy.Point(*xy)
        hasz = True if pt.Z is not None else False
        ptgeo = _arcpy.PointGeometry(pt, in_sr)
        ptgeopr = ptgeo.projectAs(out_sr, datum_transformation)
        ptpr = ptgeopr.firstPoint
        if hasz:
            xypr = (ptpr.X, ptpr.Y, ptpr.Z)
        else:
            xypr = (ptpr.X, ptpr.Y)
        xyspr.append(xypr)

    return xyspr



def spatial_ref_get(wkid: int = 27700):
    """
    Returns an arcpy SpatialReference object from the input WKID (set to
    British National Grid by default). Use to set environments, or as an input
    to certain arcpy tools.

    Args:
        wkid (int):  An ESRI Well Known ID (WKID) code for the required projection


    Return
        obj: An arcpy spatial reference object for the WKID.

    """
    sr = _arcpy.SpatialReference()
    sr.factoryCode = wkid
    sr.create()
    return sr


def spatial_ref_is_bng(fname:str) -> bool:
    """
    Is the projection of layer <fname> BNG.

    Args:
        fname (str): layer

    Returns:
        bool: True if is BNG else False
    """
    return _arcpy.da.Describe(_path.normpath(fname))['spatialReference'].name == 'British_National_Grid'
