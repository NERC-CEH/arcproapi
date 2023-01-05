""" convert area units, also has error trapping

See https://digimap.edina.ac.uk/help/our-maps-and-data/bng/ got a great explanation of OS grids
"""
import arcpy as _arcpy  # noqa
from arcpy.management import ConvertCoordinateNotation  # noqa - helper func, see https://desktop.arcgis.com/en/arcmap/latest/tools/data-management-toolbox/convert-coordinate-notation.htm

# Subject to errors to the order of meters
from OSGridConverter import latlong2grid, grid2latlong  # noqa

SquareMetersInSquareKM = 1000000


class AreaUnits:
    """area unit factors"""
    sqmeter = 1.0
    sqmillimeter = 1000000.0
    sqcentimeter = 10000.0
    sqkilometer = 0.000001
    hectare = 0.0001
    sqinch = 1550.003
    sqfoot = 10.76391
    sqyard = 1.19599
    acre = 0.0002471054
    sqmile = 0.0000003861022


class BNG100kmGrid:
    # keys 'tile', origin_easting, origin_northing
    _BNG_100KM_GRID_DICT = {
        'tile': ['HP', 'HT', 'HU', 'HW', 'HX', 'HY', 'HZ', 'NA', 'NB', 'NC', 'ND', 'NF', 'NG', 'NH', 'NJ', 'NK', 'NL', 'NM', 'NN', 'NO', 'NR', 'NS', 'NT', 'NU', 'NW', 'NX', 'NY', 'NZ', 'OV', 'SC',
                 'SD', 'SE', 'SH', 'SJ', 'SK', 'SM', 'SN', 'SO', 'SP', 'SR', 'SS', 'ST', 'SU', 'SV', 'SW', 'SX', 'SY', 'SZ', 'TA', 'TF', 'TG', 'TL', 'TM', 'TQ', 'TR', 'TV'],
        'origin_easting': [400000, 300000, 400000, 100000, 200000, 300000, 400000, 0, 100000, 200000, 300000, 0, 100000, 200000, 300000, 400000, 0, 100000, 200000, 300000, 100000, 200000, 300000,
                           400000, 100000, 200000, 300000, 400000, 500000, 200000, 300000, 400000, 200000, 300000, 400000, 100000, 200000, 300000, 400000, 100000, 200000, 300000, 400000, 0, 100000,
                           200000, 300000, 400000, 500000, 500000, 600000, 500000, 600000, 500000, 600000, 500000],
        'origin_northing': [1200000, 1100000, 1100000, 1000000, 1000000, 1000000, 1000000, 900000, 900000, 900000, 900000, 800000, 800000, 800000, 800000, 800000, 700000, 700000, 700000, 700000,
                            600000, 600000, 600000, 600000, 500000, 500000, 500000, 500000, 500000, 400000, 400000, 400000, 300000, 300000, 300000, 200000, 200000, 200000, 200000, 100000, 100000,
                            100000, 100000, 0, 0, 0, 0, 0, 400000, 300000, 300000, 200000, 200000, 100000, 100000, 0]}

    @staticmethod
    def origin_get(tile: str) -> tuple:
        """
        Get 100km tile origin as point tuple (easting, northing)
        Args:
            tile (str): The tile, e.g. 'HP'

        Returns:
            tuple: Point (easting, northing)

        Raises:
            ValueErr: If the tile is invalid or doesnt exist.

        Notes:
            Valid tiles are in Tiles are in BNG100kmGrid.__BNG_100KM_GRID_DICT['tile']

        Examples:
            >>> BNG100kmGrid.origin_get('HP')
            (400000, 1200000)
        """
        if tile.upper() not in BNG100kmGrid._BNG_100KM_GRID_DICT['tile']:
            raise ValueError("The tile %s is invalid or doesn't exist.\nValid tiles are in Tiles are in BNG100kmGrid.__BNG_100KM_GRID_DICT['tile']" % tile.upper())

        ind = BNG100kmGrid._BNG_100KM_GRID_DICT['tile'].index(tile.upper())
        return BNG100kmGrid._BNG_100KM_GRID_DICT['origin_easting'][ind], BNG100kmGrid._BNG_100KM_GRID_DICT['origin_northing'][ind]


class OSBNG:
    """ Function for converting between Ordnance survey grids and other coordinate systems

    Currently all static methods
    """

    @staticmethod
    def grid_to_bng(grid_ref: str, centroid: bool = False) -> tuple[(int, float)]:
        """
        Convert OS Grids to British National Grid eastings and northings (tuple returns values in that order).

        This gets the grid origin by default

        Args:
            grid_ref (str): The grid ref, spaces allowed. e.g. SN123456, SN 123 456, SN1234567890 are all valid.
            centroid (bool): Get the grid centroid, rather than the origin

        Returns:
            tuple[int]: Point as easting, northing if grid size >= 1m by 1m (i.e. len(grid_ref) <= 12)
            tuple[float]: Point as easting, northing if grid size < 1m by 1m (i.e. len(grid_ref) > 12)

        Raises:
            ValueError: If the gridref numbers are of different accuracy


        Examples:
            SV is grid at the BNG origin ...
            >>> OSBNG.grid_to_bng('SV 123 456')
            (123, 456)
        """

        grid_ref = grid_ref.replace(' ', '')
        if len(grid_ref) % 2 != 0:
            raise ValueError('Grid ref %s is invalid. Are you mixing accuracies? e.g. SV 12 345 is invalid, but SV 123 345 is valid.' % grid_ref.upper())

        if len(grid_ref) == 2:
            return BNG100kmGrid.origin_get(grid_ref)

        tile = grid_ref[0:2]

        # looks complicated but just parsing out the x and y coords and casting to ints
        # the /2 is why we dont support stuff like SN 12 456
        x = int(grid_ref[2:int((len(grid_ref) - 2) / 2) + 2])
        y = int(grid_ref[int(-1 * ((len(grid_ref) - 2) / 2)):])

        x1, y1 = BNG100kmGrid.origin_get(tile)
        xx = x + x1
        yy = y + y1

        # TL63 is a 10km by 10km grid in the 100km by 100km TL grid tile
        # see https://digimap.edina.ac.uk/help/our-maps-and-data/bng/
        if centroid:
            # length of a side
            j = 10000 / pow(10, int(((len(grid_ref) - 2) / 2) - 1))
            j *= 0.5
            xx += j
            yy += j

        return int(xx) if len(grid_ref) <= 12 else float(xx), int(yy) if len(grid_ref) <= 12 else float(yy)  # noqa


def convertArea(x, from_unit, to_unit):
    """area conversion with error trapping
    Example:
        >>> import arcproapi.conversion as conversion
        >>> conversion.convertArea(12.3, conversion.AreaUnits.acre, conversion.AreaUnits.hectare)
        21.13 # figure just made up!
    """
    return to_unit * x / from_unit


def m2_to_km2(x):
    """
    Convieniance function
    m2_to_km2"""
    return convertArea(x, AreaUnits.sqmeter, AreaUnits.sqkilometer)


def m2_percent_km2(x):
    """Convieniance function"""
    return 100 * x / SquareMetersInSquareKM


if __name__ == '__main__':
    """Quick debugging"""
    #  OSBNG.grid_to_bng('SV123456')
    pass
