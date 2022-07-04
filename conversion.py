""" convert area units, also has error trapping
"""
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


def convertArea(x, from_unit, to_unit):
    """area conversion with error trapping
    Example:
        >>> import arcapi.conversion as conversion
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
