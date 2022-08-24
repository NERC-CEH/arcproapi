"""Translations on shapes"""
import arcpy as _arcpy

import funclite.iolib as _iolib
import arcproapi.data as _data
import arcproapi.errors as _errors

_errors.DataUnexpectedRowCount

def points_translate(fname: str, where: str = '', x_offset: float = 0, y_offset: float = 0, expected_rows=0, show_progress: bool = False) -> int:
    """
    Translate a point or points (i.e. shift x or y coords) in layer fname
    where records match where

    Args:

        fname ():
        where ():
        x_offset ():
        y_offset ():
        expected_rows (int): If > 0, then first check that the where matches expected rows, e.g. expected_rows=1 if we expect only 1 match.
        show_progress (bool): show progress

    Returns:
        int: Number of points translated

    Raises:
        errors.DataUnexpectedRowCount: If expected_rows > 0, but doesnt match number of rows retrieved with the where clause. Use as a validation!

    Notes:
        Credit to https://gis.stackexchange.com/questions/65959/moving-offsetting-point-locations-using-arcpy-or-modelbuilder

    Examples:
        Translate a point 100 map units east
        >>> points_translate('C:/my.gdb/centroids', where="centroid_name='here'", x=100)
        \nUse the expected rows failsafe
        >>> points_translate('C:/my.gdb/centroids', where="centroid_name='matches_loads'", expected_rows=1, x=100)
        Traceback (most rec ...
        DataUnexpectedRowCount(...
    """
    fname = _iolib._path.normpath(fname)  # noqa
    mx = _data.get_row_count2(fname, where)
    if show_progress:
        PP = _iolib.PrintProgress(maximum=mx)

    if expected_rows and expected_rows != mx:
        raise _errors.DataUnexpectedRowCount('expected rows was %s, but got %s matching rows' % (expected_rows, mx))

    i = 0
    with _arcpy.da.UpdateCursor(fname, ["SHAPE@XY"], where=where) as cursor:
        for row in cursor:
            cursor.updateRow([[row[0][0] + x, row[0][1] + y]])
            i += 1
            if show_progress:
                PP.increment()
    return i