# pylint: disable=C0103, too-few-public-methods, locally-disabled, no-self-use, unused-argument
__doc__ = 'Define a projection on a shapefile. Annoyingly ArcPro forces the use of the DefineProjection Tool'
import arcpy
import os.path as path

LAYERS = ['C:/GIS/INSPIRE/shp/Denbighshire.shp', 'C:/GIS/INSPIRE/shp/Flintshire.shp', 'C:/GIS/INSPIRE/shp/Glamorgan.shp', 'C:/GIS/INSPIRE/shp/Gwynedd.shp', 'C:/GIS/INSPIRE/shp/Isle_of_Anglesey.shp', 'C:/GIS/INSPIRE/shp/Merthyr_Tydfil.shp', 'C:/GIS/INSPIRE/shp/Monmouthshire.shp', 'C:/GIS/INSPIRE/shp/Neath_Port_Talbot.shp', 'C:/GIS/INSPIRE/shp/Newport.shp', 'C:/GIS/INSPIRE/shp/Powys.shp', 'C:/GIS/INSPIRE/shp/Rhondda_Cynon_Taf.shp', 'C:/GIS/INSPIRE/shp/swansea.shp', 'C:/GIS/INSPIRE/shp/Torfaen.shp', 'C:/GIS/INSPIRE/shp/Wrexham.shp', 'C:/GIS/INSPIRE/shp/Benfro.shp', 'C:/GIS/INSPIRE/shp/Blaenau_Gwent.shp', 'C:/GIS/INSPIRE/shp/Bridgend.shp', 'C:/GIS/INSPIRE/shp/Caerphilly.shp', 'C:/GIS/INSPIRE/shp/Cardiff.shp', 'C:/GIS/INSPIRE/shp/carmarthen.shp', 'C:/GIS/INSPIRE/shp/Ceredigion.shp', 'C:/GIS/INSPIRE/shp/Conwy.shp']

class Projections():
    BNG = 'PROJCS["British_National_Grid",GEOGCS["GCS_OSGB_1936",DATUM["D_OSGB_1936",SPHEROID["Airy_1830",6377563.396,299.3249646]], PRIMEM["Greenwich",0.0],UNIT["Degree",0.0174532925199433]],PROJECTION["Transverse_Mercator"],PARAMETER["False_Easting",400000.0],PARAMETER["False_Northing",-100000.0],PARAMETER["Central_Meridian",-2.0],PARAMETER["Scale_Factor",0.9996012717],PARAMETER["Latitude_Of_Origin",49.0],UNIT["Meter",1.0]]'

for f in LAYERS:
    f = path.normpath(f)
    try:
        print('Converting %s ...' % f)
        arcpy.management.DefineProjection(f, Projections.BNG)
    except Exception as e:
        #exception occur if a projection exists
        print(e)

print("Finished")