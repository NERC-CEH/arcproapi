"""Create the 100m OS grid with 8 figure grid references for Wales.

An 8 figure OS grid reference looks like SJ632532

Requires the official OS 1km squared layer here https://github.com/OrdnanceSurvey/OS-British-National-Grids,
which should be downloaded locally and passed as an argument ot the script.

For a clear explanation of grid refs see https://getoutside.ordnancesurvey.co.uk/guides/beginners-guide-to-grid-references/

Notes:
    Trivial to change the where clause to filter for different 100km grid refs.
"""
import argparse
import os.path as path
import itertools

import arcpy

import funclite.iolib as iolib
import arcproapi.crud as crud
import arcproapi.struct as struct
import arcproapi.data as data
import arcproapi.geom as geom

# OS1KM = r'S:\SPECIAL-ACL\ERAMMP2 Survey Restricted\2022\data\1 third_party\OS\grids\OSGB_Grid_1km.shp'
# OUT = r'S:\SPECIAL-ACL\ERAMMP2 Survey Restricted\2022\data\1 third_party\OS\grids\OSGB_Grid_1km.shp'

def main():
    """do the work"""
    cmdline = argparse.ArgumentParser(description=__doc__)  # use the module __doc__
    cmdline.add_argument('os_1km_shp', type=path.normpath, help='Official OS shape file of 1km grids')
    cmdline.add_argument('file_out', type=path.normpath, help='Shapefile to create. Must not exist')
    cmdline.add_argument('-o', '--overwrite', help='Allow overwriting existing file_out', action='store_true')
    args = cmdline.parse_args()
    arcpy.env.overwriteOutput = args.overwrite

    if not args.overwrite and iolib.file_exists(args.file_out):
        raise FileExistsError('File %s exist and overwrite was disabled' % args.file_out)

    # iolib.file_delete(args.file_out)
    d, f, e = iolib.get_file_parts2(args.file_out)
    if e != '.shp':
        raise ValueError('Out file name does not end in .shp')

    struct.CreateFeatureclass(d, f, 'POLYGON', spatial_reference=args.os_1km_shp)
    struct.AddField(args.file_out, 'grid_ref', field_type='TEXT', field_length=8)
    struct.AddField(args.file_out, 'tile_name', field_type='TEXT', field_length=2)
    struct.DeleteField(args.file_out, 'Id')  # Don't ask to create an Id, but there it is, and doesnt accept null. So kill the fucker

    where_wales = "tile_name in ('SH', 'SJ', 'SM', 'SN', 'SO', 'SR', 'SS', 'ST')"
    PP = iolib.PrintProgress(maximum=data.get_row_count2(args.os_1km_shp, where=where_wales))

    try:
        insCur = arcpy.da.InsertCursor(args.file_out, ['grid_ref', 'SHAPE@', 'tile_name'])

        with crud.SearchCursor(args.os_1km_shp, field_names=['PLAN_NO', 'tile_name'], load_shape=True, where_clause=where_wales) as Cur:
            for R in Cur:
                root_ref = R.PLAN_NO
                if len(root_ref) != 6:
                    raise ValueError('Unexpected PLAN_NO (OS reference) value %s' % root_ref)
                grid_letters = root_ref[0:2]
                east_2digit = root_ref[2:4]
                north_2digit = root_ref[4:]

                origins = list(itertools.product(range(0, 1000, 100), repeat=2))

                for x, y in origins:
                    gridref = '%s%s%s%s%s' % (grid_letters, east_2digit, int(x/100), north_2digit, int(y/100))
                    sq = geom.Square(arcpy.Point(R.Shape.firstPoint.X + x, R.Shape.firstPoint.Y + y),  100)
                    g = sq.as_geometry()
                    insCur.insertRow([gridref, g, R.tile_name])
                PP.increment()
            print('Done. Exported to layer %s' % args.file_out)
    finally:
        del insCur



if __name__ == "__main__":
    main()
