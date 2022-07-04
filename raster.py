"""raster work"""
import os.path as _path

import arcpy as _arcpy

import arcapi.common as _common

# noinspection PyBroadException
def int_to_float(raster, out_raster, decimals):
    """Convert an Integer Raster to a Float Raster
    *** Requires spatial analyst extension ***

    E.g., for a cell with a value of 45750, using this tool with 3
    decimal places will give this cell a value of 45.750

    Required:
    raster -- input integer raster
    out_raster -- new float raster
    decimals -- number of places to to move decimal for each cell

    Example:
    >>> int_to_float('C:/Temp/ndvi_int', r'C:/Temp/ndvi_float', 4)
    """
    try:
        import _arcpy.sa as sa

        # check out license
        _arcpy.CheckOutExtension('Spatial')
        fl_rast = sa.Float(_arcpy.Raster(raster) / float(10 ** int(decimals)))
        try:
            fl_rast.save(out_raster)
        except:
            # having random issues with Esri GRID format, change to tiff
            #   if grid file is create/
            if not _arcpy.Exists(out_raster):
                out_raster = out_raster.split('.')[0] + '.tif'
                fl_rast.save(out_raster)
        try:
            _arcpy.CalculateStatistics_management(out_raster)
            _arcpy.BuildPyramids_management(out_raster)
        except:
            pass

        _common.msg('Created: %s' % out_raster)
        _arcpy.CheckInExtension('Spatial')
        return out_raster
    except ImportError:
        return 'Module _arcpy.sa not found.'


def fill_no_data(in_raster, out_raster, w=5, h=5):
    """Fill "NoData" cells with mean values from focal statistics.

    Use a larger neighborhood for raster with large areas of no data cells.

    *** Requires spatial analyst extension ***

    Required:
    in_raster -- input raster
    out_raster -- output raster

    Optional:
    w -- search radius width for focal stats (rectangle)
    h -- search radius height for focal stats (rectangle)

    Example:
    >>> fill_no_data('C:/Temp/ndvi', 'C:/Temp/ndvi_filled', 10, 10)
    """
    try:
        import _arcpy.sa as sa
        # Make Copy of Raster
        _dir, name = _path.split(_arcpy.Describe(in_raster).catalogPath)
        temp = _path.join(_dir, 'rast_copyxxx')
        if _arcpy.Exists(temp):
            _arcpy.Delete_management(temp)
        _arcpy.CopyRaster_management(in_raster, temp)

        # Fill NoData
        _arcpy.CheckOutExtension('Spatial')
        filled = sa.Con(sa.IsNull(temp), sa.FocalStatistics(temp, sa.NbrRectangle(w, h), 'MEAN'), temp)
        filled.save(out_raster)
        _arcpy.BuildPyramids_management(out_raster)
        _arcpy.CheckInExtension('Spatial')

        # Delete original and replace
        if _arcpy.Exists(temp):
            _arcpy.Delete_management(temp)
        _common.msg('Filled NoData Cells in: %s' % out_raster)
        return out_raster
    except ImportError:
        return 'Module _arcpy.sa not found.'


# noinspection PyBroadException
def meters_to_feet(in_dem, out_raster, factor=3.28084):
    """Convert DEM Z units by a factor, default factor converts m -> ft.
    *** Requires spatial analyst extension ***

    Required:
    in_dem -- input dem
    out_raster -- new raster with z values as feet
    factor -- number by which the input DEM is multiplied,
        default is 3.28084 to convert metres to feet.

    Example:
    >>> meters_to_feet(r'C:\Temp\dem_m', r'C:\Temp\dem_ft')
    """
    try:
        import _arcpy.sa as sa
        _arcpy.CheckOutExtension('Spatial')
        out = sa.Float(sa.Times(_arcpy.Raster(in_dem), factor))
        # noinspection PyBroadException
        try:
            out.save(out_raster)
        except:
            # having random issues with esri GRID format
            #  will try to create as tiff if it fails
            if not _arcpy.Exists(out_raster):
                out_raster = out_raster.split('.')[0] + '.tif'
                out.save(out_raster)
        try:
            _arcpy.CalculateStatistics_management(out_raster)
            _arcpy.BuildPyramids_management(out_raster)
        except:
            pass
        _arcpy.AddMessage('Created: %s' % out_raster)
        _arcpy.CheckInExtension('Spatial')
        return out_raster
    except ImportError:
        return 'Module _arcpy.sa not found'


def remap_sa(st, stop, step, n=1):
    """Create a spatial analyst format reclassify remap range (list)
    [[start value, end value, new value]...]


    st   -- start value (int)
    stop -- stop value (int)
    step -- step value for range (int)

    Optional:
    n -- new value interval, default is 1 (int)

    >>> # ex: make range groups from 50 - 80
    >>> remap_sa(50, 80, 10)
    [[50, 60, 1], [60, 70, 2], [70, 80, 3]]
    """

    tups = [[i, i + step] for i in range(st, stop, step)]
    return [[t] + [(tups.index(t) + 1) * n] for t in tups]  # noqa


def remap_3d(st, stop, step, n=1):
    """Create a 3D analyst format reclassify remap range (str)
    "start end new;..."

    Required:
    st --   start value (int)
    stop -- stop value (int)
    step -- step value for range (int)

    Optional:
    n -- new value interval, default is 1 (int)

    Example:
    >>> # make range groups from 50 - 80
    >>> remap_3d(50, 80, 10)
    '50 60 1;60 70 2;70 80 3'
    """

    tups = [[i, i + step] for i in range(st, stop, step)]
    return ';'.join(' '.join([str(i) for i in t] + [str((tups.index(t) + 1) * n)]) for t in tups)
