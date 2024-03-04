"""
Helper functions for working with geometries
"""
import hashlib as _hashlib
import copy as _copy

import arcpy
import arcpy as _arcpy

import arcproapi.errors as _errors  # noqa


#################
# Classes first #
#################

class Square:
    """
    Create an arcpy Polygon instance representation of a square
    with origin at origin, with sides of length side_length.

    Origin is typlically in standard cartesian convention (i.e. x1,y1)

    Args:
        origin (list, tuple, arcpy.Point): A point like object
        side_length (float, int): Side length

    Members:
        Polygon: The arcpy Polygon instance
        pt_x?y?: arcpy point objects, defining the square

    Examples:
        >>> Sq = Square([0,0], 1)
        >>> print(Sq.Polygon.centroid)
        <Point (0.50006103515625, 0.50006103515625, #, #)>
    """
    def __init__(self, origin: (list, _arcpy.Point), side_length):
        if isinstance(origin, (list, tuple)):
            self.pt_x1y1 = _arcpy.Point(*origin)
        else:
            self.pt_x1y1 = _copy.copy(origin)  # deepcopy fails (ESRI object doesnt support necessary interfaces), this just copies the pointer. We dont manipulate origin anyway

        self.pt_x1y2 = _arcpy.Point(self.pt_x1y1.X, self.pt_x1y1.Y + side_length)
        self.pt_x2y2 = _arcpy.Point(self.pt_x1y1.X + side_length, self.pt_x1y1.Y + side_length)
        self.pt_x2y1 = _arcpy.Point(self.pt_x1y1.X + side_length, self.pt_x1y1.Y)

        self.Polygon = _arcpy.Polygon(_arcpy.Array([self.pt_x1y1, self.pt_x1y2, self.pt_x2y2, self.pt_x2y1, self.pt_x1y1]))


    def as_list(self) -> list:
        """Return square polygon as list of lists

        Examples:
            >>> Sq = Square([0,0], 1)
            >>> Sq.as_list
            [[0,0], [0, 1], [1, 1], [1, 0], [0, 0]]
        """
        return list_from_polygon(self.Polygon)

    def as_geometry(self, **kwargs) -> _arcpy.Geometry:
        """
        Get instance as a Geometry instance.
        This is consumed by the InsertCursor

        Args:
            kwargs: passed to arcpy.Geometry init

        Returns:
            arcpy.Geometry: Geometry instance of square points
        """
        return _arcpy.Geometry('polygon', _arcpy.Array([self.pt_x1y1, self.pt_x1y2, self.pt_x2y2, self.pt_x2y1, self.pt_x1y1]), **kwargs)

    def as_array(self) -> _arcpy.Array:
        """get as an arcpy Array instance

        Returns:
            arcpy.Array: Array instance of square points
        """
        return _arcpy.Array([self.pt_x1y1, self.pt_x1y2, self.pt_x2y2, self.pt_x2y1, self.pt_x1y1])





###################
# General methods #
###################
def shape_hash(shape: _arcpy.Polygon) -> str:
    """
    Given a polygon instance (as read from SearchCursor 'Shape@'), get the hash value
    of the wkt representation of the shape.

    This is useful if we want to get a unique text value of the shape for aggregate
    operations, like Dissolve, which do not support Shape.

    Args:
        shape: Polygon instance

    Returns:
        The sha256 has of shape

    Examples:

        >>> row = arcpy.da.SearchCursor('C:/myshape.shp', config.GeoDatabaseLayersAndTables.ERAMMPCommon.sq, ['Shape@']).next()  # noqa
        >>> shape_hash(row[0])
        '773bd78d5d2c0bf243d0d773272be8e36c25b52fc282f79ebd96afd372e68e58'
    """
    return _hashlib.sha256(shape.WKT.encode('ASCII')).hexdigest()

def polygon_from_list(lst: (list, tuple)) -> _arcpy.Polygon:
    """
    Args:
        lst (any): A list of points, accepts tuples as well

    Returns:
         arcpy.Polygon: An instance of arcpy.Polygon

    Notes:
        Include the closing point, so a square is defined by 5 points

    Examples:
        >>> ply = polygon_from_list([(0,0), (0, 1), (1, 1), (1, 0), (0, 0)])  # noqa
        >>> ply.centroid
        <Point (0.50006103515625, 0.50006103515625, #, #)>

        With Z and M
        >>> ply = polygon_from_list([(0, 0, 2, 2), (0, 1, 2, 2), (1, 1, 2, 2), (1, 0, 2, 2), (0, 0, 2, 2)])  # noqa
        >>> ply.centroid
        <Point (0.50006103515625, 0.50006103515625, #, #)>

    """
    pts = _arcpy.Array([_arcpy.Point(*pt) for pt in lst])
    poly = _arcpy.Polygon(pts)
    return poly



def polygon_from_extent(ext: _arcpy.Extent):
    """Make an arcpy polygon object from an input extent object.

    Largely superflous because Extent instances expose the Polygon obj as a property and vica-versa

    Args:
        ext (_arcpy.Extent): Instance of arcpy.Extent

    Returns:
        _arcpy.Polygon: A Polygon instance representation of the extent

    Examples:
        Circular example for illustration
        >>> poly = polygon_from_extent(arcpy.da.SearchCursor('C:/my.gdb/countries', ['SHAPE@']).next()[0].extent)  # noqa
        >>> arcpy.CopyFeatures_management(poly, r'C:\Temp\Project_boundary.shp')  # noqa
    """
    array = _arcpy.Array()
    array.add(ext.lowerLeft)
    array.add(ext.lowerRight)
    array.add(ext.upperRight)
    array.add(ext.upperLeft)
    array.add(ext.lowerLeft)
    return _arcpy.Polygon(array, ext.spatialReference)

def polyline_from_list(lst: (list[list[(int, float)]])) -> _arcpy.Polyline:
    """
    Get instance of an arcpy.Polyline from a list/tuple of points

    Args:
        lst (any): A list of points, accepts tuples as well

    Returns:
         arcpy.Polyline: An instance of arcpy.Polyline

    Notes:
        Order matters.
        Should accept any combination of lists or tuples containing ints and/or floats

    Examples:
        >>> poly = polyline_from_list([(0,0), (0, 1), (1, 1), (1, 0)])  # noqa
        >>> poly.centroid
        <Point (0.50006103515625, 0.50006103515625, #, #)>

        With Z and M
        >>> ply = polyline_from_list([(0, 0, 1, 1), (0, 1, 1, 1), (1, 1, 1, 1), (1, 0, 1, 1)])  # noqa
        >>> ply.centroid
        <Point (0.50006103515625, 0.50006103515625, 0, 0)>
    """
    pts = _arcpy.Array([_arcpy.Point(*pt) for pt in lst])
    poly = _arcpy.Polyline(pts)
    return poly


def polyline_to_polygon(polyline: arcpy.Polyline) -> (arcpy.Polygon, None, tuple[arcpy.Polygon]):
    """
    Given a polyline, create a polygon.
    Takes the last point of polyline and adds a final point at the start point of polyline

    Supports multipart features, but returns them as a tuple of polygons

    Args:
        polyline: a polyline

    Returns:
        None: If polyline had no points or no polygon could be generated from the line(s)
        arcpy.Polygon: Polygon instance, if polyline was a single polyline feature
        tuple[arcpy.Polygon]: If the polyline was a multipart feature, i.e. breaks multipart polylines into individual polygons

    """
    line: _arcpy.Array
    out = []
    for line in polyline:
        if points_equal(line[0], line[-1]):
            out += [arcpy.Polygon(line)]
        else:
            line.add(line[0])
            out += [arcpy.Polygon(line)]

    if not out:
        return None

    if len(out) == 1:
        return out[0]
    return out


def points_equal(pt1: _arcpy.Point, pt2: _arcpy.Point) -> bool:
    """
    Are two points equal.
    pt1 == pt2 doesnt work.

    Args:
        pt1: arcpy.Point instance
        pt2: arcpy.Point instance

    Returns:
        bool
    """
    return pt1.X == pt2.X and pt1.Y == pt2.Y and pt1.Z == pt2.Z


def point_from_list(lst) -> _arcpy.Point:
    """
    Get instance of an arcpy.Point from a list/tuple of points

    Args:
        lst (tuple, list): A list of points, accepts tuples as well

    Returns:
         arcpy.Point: An instance of arcpy.Point

    Notes:
        Added for completeness - creating an arcpy point is trivial

    Examples:
        >>> pt = point_from_list((0, 0))  # noqa
        <Point (0.50006103515625, 0.50006103515625, #, #)>

        With Z and M
        >>> pt = point_from_list((0, 0, 0, 0))  # noqa
        <Point (0.50006103515625, 0.50006103515625, 0, 0)>
    """
    return _arcpy.Point(*lst)


def array_from_list(lst: (list, tuple)) -> _arcpy.Array:
    """
    Get an arcpy.Array instance from a list or tuple

    Args:
        lst (any): A list of points, accepts tuples as well

    Returns:
         arcpy.Polygon: An instance of arcpy.Polygon

    Notes:
        Include the closing point, so a square is defined by 5 points

    Examples:
        >>> array_from_list([(0,0), (0, 1), (1, 1), (1, 0), (0, 0)])
    """
    return _arcpy.Array([_arcpy.Point(x, y) for x, y in lst])

def list_from_polygon(poly: _arcpy.Polygon):
    """
    Return arcpy polygon instance as a list of points

    Args:
        poly: An arcpy polygon object

    Returns:
        list: 2d-list, e.g. [[0,0], [0, 1], [1, 1], [1, 0], [0, 0]]

    Examples:
        >>> Poly = polygon_from_list([(0,0), (0, 1), (1, 1), (1, 0), (0, 0)])
        >>> list_from_polygon(Poly)
        [[0,0], [0, 1], [1, 1], [1, 0], [0, 0]]
    """
    return [[pt.X, pt.Y] for pt in poly[0]]



def extent_zoom(extent: _arcpy.Extent, factor_perc: float = None, factor_abs: float = None) -> _arcpy.Extent:
    """
    Expand or contract an extent by a percent or absolute factor

    Args:
        extent:
        factor_perc:
        factor_abs:

    Returns:
        "arcpy.Extent": An arcpy extent object
    """
    if not (factor_abs or factor_perc):
        return extent

    if factor_abs and factor_perc:
        raise ValueError('factor_perc and factor_abs were passed. Use one or the other.')

    if factor_abs:
        buff_dist = factor_abs
    else:
        buff_dist = ((int(abs(extent.lowerLeft.X - extent.lowerRight.X))) * (factor_perc/100))

    return extent.polygon.buffer(buff_dist).extent



if __name__ == '__main__':
    # quick tests here
    ply = polygon_from_list([(0, 0), (0, 1), (1, 1), (1, 0), (0, 0)])
    extent_zoom(ply.extent, factor_abs=0.4)
