"""Create the 100m OS grid with 8 figure grid references for Wales.

An 8 figure OS grid reference looks like SJ632532

Requires the official OS 1km squared layer here https://github.com/OrdnanceSurvey/OS-British-National-Grids,
which should be downloaded locally and passed as an argument ot the script. This layer should have
a field called tile_name, which is the 2 letter 100km tile, e.g. 'HP', 'SV' etc.

For a clear explanation of grid refs see https://getoutside.ordnancesurvey.co.uk/guides/beginners-guide-to-grid-references/

Notes:
    An export failure during the process may be caused by hitting the shapefile size limit of 2Gb.
    Check you export options and test with a reduced tile set to verify.

Examples:
    Wales only tiles (for efficiency), with additional filter to check that all 100m grids intersect Wales. Very Slow!\n
    > python.exe os_100m_grid.py "S:\SPECIAL-ACL\ERAMMP2 Survey Restricted\2022\data\1 third_party\OS\grids\OSGB_Grid_1km.shp" "S:\SPECIAL-ACL\ERAMMP2 Survey Restricted\2022\data\1 third_party\OS\grids\OSGB_Grid_Wales_100m.shp" -c "S:\SPECIAL-ACL\ERAMMP2 Survey Restricted\2022\data\1 third_party\OS\countries\Countries_(December_2019)_Boundaries_UK_BFC.shp" -o --tiles wales --country_filter wales

    \nAll 100km tiles that are in a 1km tile that intersect Wales
    > python.exe os_100m_grid.py "S:\SPECIAL-ACL\ERAMMP2 Survey Restricted\2022\data\1 third_party\OS\grids\OSGB_Grid_1km.shp" "S:\SPECIAL-ACL\ERAMMP2 Survey Restricted\2022\data\1 third_party\OS\grids\OSGB_Grid_Wales_100m.shp" -c "S:\SPECIAL-ACL\ERAMMP2 Survey Restricted\2022\data\1 third_party\OS\countries\Countries_(December_2019)_Boundaries_UK_BFC.shp" -o --tiles wales --country_filter_quick wales

    \nAll 100km tiles that intersect Wales
    > python.exe os_100m_grid.py "S:\SPECIAL-ACL\ERAMMP2 Survey Restricted\2022\data\1 third_party\OS\grids\OSGB_Grid_1km.shp" "S:\SPECIAL-ACL\ERAMMP2 Survey Restricted\2022\data\1 third_party\OS\grids\OSGB_Grid_Wales_100m.shp" -o --tiles wales
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
import arcproapi.environ as environ

# OS1KM = r'S:\SPECIAL-ACL\ERAMMP2 Survey Restricted\2022\data\1 third_party\OS\grids\OSGB_Grid_1km.shp'
# OUT = r'S:\SPECIAL-ACL\ERAMMP2 Survey Restricted\2022\data\1 third_party\OS\grids\OSGB_Grid_100m.shp'
# S:\SPECIAL-ACL\ERAMMP2 Survey Restricted\2022\data\1 third_party\OS\countries\Countries_(December_2019)_Boundaries_UK_BFC.shp

WALES = ('SH', 'SJ', 'SM', 'SN', 'SO', 'SR', 'SS', 'ST')
ENGLAND = ('NT', 'NU', 'NX', 'NY', 'NZ', 'OV', 'SD', 'SE', 'SJ', 'SK', 'SO', 'SP', 'SS', 'ST', 'SU', 'SV', 'SW', 'SX', 'SY', 'SZ', 'TA', 'TF', 'TG', 'TL', 'TM', 'TQ', 'TR', 'TV')
SCOTLAND = ('NW', 'NX', 'NY', 'NR', 'NS', 'NT', 'NL', 'NM', 'NN', 'NO', 'NF', 'NG', 'NH', 'NJ', 'NK', 'NA', 'NB', 'NC', 'ND', 'HW', 'HX', 'HY', 'HZ', 'HT', 'HU', 'HP')


arcpy.env.workspace = environ.workspace_in_memory_str()

def main():
    """do the work"""
    cmdline = argparse.ArgumentParser(description=__doc__)  # use the module __doc__
    cmdline.add_argument('os_1km_shp', type=path.normpath, help='Official OS shape file of 1km grids')
    cmdline.add_argument('file_out', type=path.normpath, help='Shapefile to create. Must not exist')
    cmdline.add_argument('-o', '--overwrite', help='Allow overwriting existing file_out', action='store_true')

    f = lambda s: [str(item).upper() for item in s.split(',')]
    cmdline.add_argument('-t', '--tiles', type=f, help='Export these tiles, or accepts "wales", "england" or "scotland" eg -l SJ,SM   -l wales', required=True)

    cmdline.add_argument('-f', '--country_filter', type=str.capitalize, help='SLOW, SLOW, SLOW!! Prefilter each 100m tile for intersect with country (layer countries). Accepts "wales", "england" or "scotland" eg -f wales.', required=False)
    cmdline.add_argument('-q', '--country_filter_quick', type=str.capitalize, help='Prefilter at the 1km grid level for intersect with country (layer countries). Accepts "wales", "england" or "scotland" eg -q wales. This will contain some 100m grids outside of the country boundary.', required=False)

    cmdline.add_argument('-c', '--countries_shp', type=path.normpath, help='OS Country Boundaries polygon layer. The official layer embeds the country name in field ctry19nm. ctry19nm IN ["England", "Scotland", "Wales"]', required=False)

    args = cmdline.parse_args()


    args.tiles = list(set(args.tiles))
    if len(args.tiles) > 1 and ('WALES' in args.tiles or 'ENGLAND' in args.tiles or 'SCOTLAND' in args.tiles):
        raise ValueError('Tiles includes a country directive with other tile or country directives. Just pass a single country, otherwise the exported shapefile could exceed 2Gb.')

    if len(args.tiles) > len(ENGLAND):
        raise ValueError('Tiles are limited to %s distinct values (nr. of tiles intersecting England). Otherwise the exported shapefile could exceed 2Gb.' % len(ENGLAND))

    if args.country_filter or args.country_filter_quick:
        if not args.countries_shp:
            raise ValueError('A country filter was given, but no positional argument for the countries shapefile was provided.')
        elif not iolib.file_exists(args.countries_shp):
            raise ValueError('A country filter was given, but the countries shapefile %s does not exist.' % args.countries_shp)

    if not args.overwrite and iolib.file_exists(args.file_out):
        raise FileExistsError('File %s exist and overwrite was disabled' % args.file_out)

    d, f, e = iolib.get_file_parts2(args.file_out)
    if e != '.shp':
        raise ValueError('Out file name does not end in .shp')

    # This doesn't fix if have the layer open in seperate arcpy instance (e.g. in ArcPro client)
    arcpy.env.overwriteOutput = args.overwrite

    # shapefile, field_length limit == 10 :(
    struct.CreateFeatureclass(d, f, 'POLYGON', spatial_reference=args.os_1km_shp)
    struct.AddField(args.file_out, 'tile_name', field_type='TEXT', field_length=2)
    struct.AddField(args.file_out, 'grid_1km', field_type='TEXT', field_length=6)
    struct.AddField(args.file_out, 'grid_100m', field_type='TEXT', field_length=8)
    struct.DeleteField(args.file_out, 'Id')  # Don't ask to create an Id, but there it is, and doesnt accept null. So kill the fucker

    if args.tiles[0] == 'WALES':
        args.tiles = WALES
    elif args.tiles[0] == 'ENGLAND':
        args.tiles = ENGLAND
    elif args.tiles[0] == 'SCOTLAND':
        args.tiles = SCOTLAND

    where = "tile_name in %s" % str(tuple(args.tiles))

    country_geom = None  # noqa
    if args.country_filter:
        with crud.CRUD(args.countries_shp, enable_transactions=False) as Country:
            country_geom: arcpy.Polygon = Country.lookup(['SHAPE@'], {'ctry19nm': args.country_filter})[0]

    # TODO Debug the quick filter
    country_geom_quick = None  # noqa
    if args.country_filter_quick:
        with crud.CRUD(args.countries_shp, enable_transactions=False) as Country:
            country_geom_quick: arcpy.Polygon = Country.lookup(['SHAPE@'], {'ctry19nm': args.country_filter_quick})[0]

    PP = iolib.PrintProgress(maximum=data.get_row_count2(args.os_1km_shp, where=where))

    try:
        insCur = arcpy.da.InsertCursor(args.file_out, ['grid_100m', 'SHAPE@', 'tile_name', 'grid_1km'])

        with crud.SearchCursor(args.os_1km_shp, field_names=['PLAN_NO', 'tile_name'], load_shape=True, where_clause=where) as Cur:

            for R in Cur:
                # This is a less intensive filter at the 1km square level, so will contains some 100m grids outside of the requested country boundary
                if args.country_filter_quick:
                    if country_geom_quick and R['SHAPE@'].disjoint(country_geom_quick):
                        PP.increment()
                        continue

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

                    # FYI, disjoint is the fastest way of determining an if intersection. timeit.timeit(lambda: h.disjoint(g), number=5)
                    if country_geom and sq.as_geometry().disjoint(country_geom):
                        continue

                    g = sq.as_geometry()
                    insCur.insertRow([gridref, g, R.tile_name, root_ref])
                PP.increment()
            print('Done. Exported to layer %s' % args.file_out)
    finally:
        del insCur







if __name__ == "__main__":
    main()
