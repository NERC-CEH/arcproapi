"""Projection related stuff"""
import os.path as _path

import fuckit as _fuckit

import arcpy as _arcpy

import arcproapi.httplib as _http



class SpatialRef:
    """ Helper class wrapper around arcpy.SpatialReference

    Mainly to make reporting and viewing spatial ref info easier for reporting purposes.

    Fields:
        _GCS: Exposes the arcpy.SpatialReference object of the Geographic cordinate system where the parent Coord system is projected
        _SpatialReference: Exposes the arcpy.SpatialReference object for the spatial reference passed to initiate the object

    Methods:
        as_dict: Return the spatial reference as a dictionary
    """
    # TODO: Do this, but its a bit more complicated with the GCS property for projected coordinate systems
    # https://pro.arcgis.com/en/pro-app/latest/arcpy/classes/spatialreference.htm

    def __init__(self, SpatialReference: _arcpy.SpatialReference):
        self._SpatialReference: _arcpy.SpatialReference = SpatialReference
        S = SpatialReference

        # Assuming that some of these will be invalid depending on spatial reference - too many cases to check
        # So blast through with fuckit
        with _fuckit:
            self.abbreviation = S.abbreviation
            self.alias = S.alias
            self.angularUnitCode = S.angularUnitCode
            self.angularUnitName = S.angularUnitName
            self.as_string = S.exportToString()
            self.azimuth = S.azimuth
            self.centralMeridian = S.centralMeridian
            self.centralMeridianInDegrees = S.centralMeridianInDegrees
            self.centralParallel = S.centralParallel
            self.classification = S.classification
            self.datumCode = S.datumCode
            self.datumName = S.datumName
            self.domain = S.domain
            self.factoryCode = S.factoryCode
            self.falseEasting = S.falseEasting
            self.falseNorthing = S.falseNorthing
            self.falseOriginAndUnits = S.falseOriginAndUnits
            self.flattening = S.flattening
            self.GCSCode = S.GCSCode
            self.GCSName = S.GCSName
            self.hasMPrecision = S.hasMPrecision
            self.hasXYPrecision = S.hasXYPrecision
            self.hasZPrecision = S.hasZPrecision
            self.isHighPrecision = S.isHighPrecision
            self.latitudeOf1st = S.latitudeOf1st
            self.latitudeOf2nd = S.latitudeOf2nd
            self.latitudeOfOrigin = S.latitudeOfOrigin
            self.linearUnitCode = S.linearUnitCode
            self.linearUnitName = S.linearUnitName
            self.longitude = S.longitude
            self.longitudeOf1st = S.longitudeOf1st
            self.longitudeOf2nd = S.longitudeOf2nd
            self.longitudeOfOrigin = S.longitudeOfOrigin
            self.metersPerUnit = S.metersPerUnit
            self.MDomain = S.MDomain
            self.MFalseOriginAndUnits = S.MFalseOriginAndUnits
            self.MResolution = S.MResolution
            self.MTolerance = S.MTolerance
            self.name = S.name
            self.PCSCode = S.PCSCode
            self.PCSName = S.PCSName
            self.primeMeridianCode = S.primeMeridianCode
            self.primeMeridianName = S.primeMeridianName
            self.projectionCode = S.projectionCode
            self.projectionName = S.projectionName
            self.radiansPerUnit = S.radiansPerUnit
            self.remarks = S.remarks
            self.scaleFactor = S.scaleFactor
            self.semiMajorAxis = S.semiMajorAxis
            self.semiMinorAxis = S.semiMinorAxis
            self.spheroidCode = S.spheroidCode
            self.spheroidName = S.spheroidName
            self.standardParallel1 = S.standardParallel1
            self.standardParallel2 = S.standardParallel2
            self.type = S.type
            self.usage = S.usage
            self.VCS = S.VCS
            self.XYResolution = S.XYResolution
            self.XYTolerance = S.XYTolerance
            self.ZDomain = S.ZDomain
            self.ZFalseOriginAndUnits = S.ZFalseOriginAndUnits
            self.ZResolution = S.ZResolution
            self.ZTolerance = S.ZTolerance

            self._GCS = S.GCS if self.type == 'Projected' else None
            if self._GCS:
                self.GCS = SpatialRef(self._GCS).as_dict


    def __repr__(self):
        return '\n'.join(['%s: %s' % (k, v) for k, v in self.as_dict.items()])

    @property
    def as_dict(self) -> dict:
        """
        Get spatialref as a dict of attrs

        Returns:
            dict: the dictionary representation
        """
        return {k: v for k, v in self.__dict__.items() if k[0] != '_' and k != 'GCS'}



def epsg(epsgcode, format_: str = 'esriwkt'):
    """
    Get spatial reference system by EPSG code as string.
    Queries the http://epsg.io website.
    epsgcode -- European Petrol Survey Group code (http://www.epsg.org/)

    Args:

        format_:
            Format to return, valid values are:
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


    Examples:

        >>> epsg(27700, 'esriwkt')
    """
    srsstr = _http.request('http://epsg.io/%s.%s' % (epsgcode, str(format_).lower()))
    return srsstr


def project_coordinates(xys: list[tuple[float, float]], in_sr: int, out_sr: int, datum_transformation: str = None):
    """
    Project list of coordinate pairs (or triplets).

    Args:
        xys: list of coordinate pairs or triplets to project one by one
        in_sr: input spatial reference, wkid, prj file, etc.
        out_sr: output spatial reference, wkid, prj file, etc.

        datum_transformation: datum transformation to use
            if in_sr and out_sr are defined on different datums,
            defining appropriate datum_transformation is necessary
            in order to obtain correct results!
            (hint: use _arcpy.ListTransformations to list valid transformations)

    Examples:

        >>> dtt = 'TM65_To_WGS_1984_2 + OSGB_1936_To_WGS_1984_NGA_7PAR'  # noqa
        >>> coordinates = [(240600.0, 375800.0), (245900.0, 372200.0)]  # noqa
        >>> project_coordinates(coordinates, 29902, 27700, dtt)   # noqa
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

    Notes:
        See https://developers.arcgis.com/rest/services-reference/enterprise/pdf/pcs_pdf_11.1.pdf for WKIDs under ESRI
    """
    sr = _arcpy.SpatialReference()
    sr.factoryCode = wkid
    sr.create()
    return sr


def spatial_ref_is_bng(fname: str) -> bool:
    """
    Is the projection of layer <fname> BNG.

    Args:
        fname (str): layer

    Returns:
        bool: True if is BNG else False
    """
    return _arcpy.da.Describe(_path.normpath(fname))['spatialReference'].name == 'British_National_Grid'





if __name__ == '__main__':
    pass

