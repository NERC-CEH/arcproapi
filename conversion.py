""" convert area units, also has error trapping

See https://digimap.edina.ac.uk/help/our-maps-and-data/bng/ got a great explanation of OS grids
"""
from enum import Enum as _Enum

import math as _math
import arcpy as _arcpy  # noqa
from arcpy.management import ConvertCoordinateNotation  # noqa - helper func, see https://desktop.arcgis.com/en/arcmap/latest/tools/data-management-toolbox/convert-coordinate-notation.htm

# Subject to errors to the order of meters
from OSGridConverter import latlong2grid, grid2latlong  # noqa

import funclite.numericslib as _numerics
from funclite.baselib import classproperty as _classproperty

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
    """ Working with British National Grid conversions.

    Also exposes British National Grid codes as class field lists for convieniance.
    """
    TILES_100km = ['HP', 'HT', 'HU', 'HW', 'HX', 'HY', 'HZ', 'NA', 'NB', 'NC', 'ND', 'NF', 'NG', 'NH', 'NJ', 'NK', 'NL', 'NM', 'NN', 'NO', 'NR', 'NS', 'NT', 'NU', 'NW', 'NX', 'NY', 'NZ', 'OV', 'SC',
                   'SD', 'SE', 'SH', 'SJ', 'SK', 'SM', 'SN', 'SO', 'SP', 'SR', 'SS', 'ST', 'SU', 'SV', 'SW', 'SX', 'SY', 'SZ', 'TA', 'TF', 'TG', 'TL', 'TM', 'TQ', 'TR', 'TV']

    TILES_10KM_ALL = ['HP40', 'HP50', 'HP51', 'HP60', 'HP61', 'HP62', 'HT93', 'HT94', 'HU06', 'HU14', 'HU15', 'HU16', 'HU24', 'HU25', 'HU26', 'HU27', 'HU28', 'HU30', 'HU31', 'HU32', 'HU33', 'HU34',
                      'HU35', 'HU36', 'HU37', 'HU38', 'HU39', 'HU40', 'HU41', 'HU42', 'HU43', 'HU44', 'HU45', 'HU46', 'HU47', 'HU48', 'HU49', 'HU53', 'HU54', 'HU55', 'HU56', 'HU57', 'HU58', 'HU59',
                      'HU66', 'HU67', 'HU68', 'HU69', 'HU77', 'HW62', 'HW63', 'HW73', 'HW83', 'HX62', 'HY10', 'HY20', 'HY21', 'HY22', 'HY23', 'HY30', 'HY31', 'HY32', 'HY33', 'HY34', 'HY35', 'HY40',
                      'HY41', 'HY42', 'HY43', 'HY44', 'HY45', 'HY50', 'HY51', 'HY52', 'HY53', 'HY54', 'HY55', 'HY60', 'HY61', 'HY62', 'HY63', 'HY64', 'HY73', 'HY74', 'HY75', 'HZ16', 'HZ17', 'HZ26',
                      'HZ27', 'NA00', 'NA10', 'NA64', 'NA74', 'NA81', 'NA90', 'NA91', 'NA92', 'NA93', 'NB00', 'NB01', 'NB02', 'NB03', 'NB10', 'NB11', 'NB12', 'NB13', 'NB14', 'NB20', 'NB21', 'NB22',
                      'NB23', 'NB24', 'NB25', 'NB30', 'NB31', 'NB32', 'NB33', 'NB34', 'NB35', 'NB36', 'NB40', 'NB41', 'NB42', 'NB43', 'NB44', 'NB45', 'NB46', 'NB52', 'NB53', 'NB54', 'NB55', 'NB56',
                      'NB90', 'NB91', 'NC00', 'NC01', 'NC02', 'NC03', 'NC10', 'NC11', 'NC12', 'NC13', 'NC14', 'NC15', 'NC16', 'NC20', 'NC21', 'NC22', 'NC23', 'NC24', 'NC25', 'NC26', 'NC27', 'NC30',
                      'NC31', 'NC32', 'NC33', 'NC34', 'NC35', 'NC36', 'NC37', 'NC38', 'NC40', 'NC41', 'NC42', 'NC43', 'NC44', 'NC45', 'NC46', 'NC47', 'NC50', 'NC51', 'NC52', 'NC53', 'NC54', 'NC55',
                      'NC56', 'NC60', 'NC61', 'NC62', 'NC63', 'NC64', 'NC65', 'NC66', 'NC70', 'NC71', 'NC72', 'NC73', 'NC74', 'NC75', 'NC76', 'NC80', 'NC81', 'NC82', 'NC83', 'NC84', 'NC85', 'NC86',
                      'NC87', 'NC90', 'NC91', 'NC92', 'NC93', 'NC94', 'NC95', 'NC96', 'ND01', 'ND02', 'ND03', 'ND04', 'ND05', 'ND06', 'ND07', 'ND10', 'ND12', 'ND13', 'ND14', 'ND15', 'ND16', 'ND17',
                      'ND19', 'ND23', 'ND24', 'ND25', 'ND26', 'ND27', 'ND28', 'ND29', 'ND33', 'ND34', 'ND35', 'ND36', 'ND37', 'ND38', 'ND39', 'ND47', 'ND48', 'ND49', 'ND59', 'NF09', 'NF19', 'NF56',
                      'NF58', 'NF60', 'NF61', 'NF66', 'NF67', 'NF68', 'NF70', 'NF71', 'NF72', 'NF73', 'NF74', 'NF75', 'NF76', 'NF77', 'NF80', 'NF81', 'NF82', 'NF83', 'NF84', 'NF85', 'NF86', 'NF87',
                      'NF88', 'NF89', 'NF95', 'NF96', 'NF97', 'NF98', 'NF99', 'NG07', 'NG08', 'NG09', 'NG10', 'NG13', 'NG14', 'NG15', 'NG18', 'NG19', 'NG20', 'NG23', 'NG24', 'NG25', 'NG26', 'NG29',
                      'NG30', 'NG31', 'NG32', 'NG33', 'NG34', 'NG35', 'NG36', 'NG37', 'NG39', 'NG38', 'NG40', 'NG41', 'NG42', 'NG43', 'NG44', 'NG45', 'NG46', 'NG47', 'NG49', 'NG50', 'NG51', 'NG52',
                      'NG53', 'NG54', 'NG55', 'NG56', 'NG60', 'NG61', 'NG62', 'NG63', 'NG64', 'NG65', 'NG66', 'NG70', 'NG71', 'NG72', 'NG73', 'NG74', 'NG75', 'NG76', 'NG77', 'NG78', 'NG79', 'NG80',
                      'NG81', 'NG82', 'NG83', 'NG84', 'NG85', 'NG86', 'NG87', 'NG88', 'NG89', 'NG90', 'NG91', 'NG92', 'NG93', 'NG94', 'NG95', 'NG96', 'NG97', 'NG98', 'NG99', 'NH00', 'NH01', 'NH02',
                      'NH03', 'NH04', 'NH05', 'NH06', 'NH07', 'NH08', 'NH09', 'NH10', 'NH11', 'NH12', 'NH13', 'NH14', 'NH15', 'NH16', 'NH17', 'NH18', 'NH19', 'NH20', 'NH21', 'NH22', 'NH23', 'NH24',
                      'NH25', 'NH26', 'NH27', 'NH28', 'NH29', 'NH30', 'NH31', 'NH32', 'NH33', 'NH34', 'NH35', 'NH36', 'NH37', 'NH38', 'NH39', 'NH40', 'NH41', 'NH42', 'NH43', 'NH44', 'NH45', 'NH46',
                      'NH47', 'NH48', 'NH49', 'NH50', 'NH51', 'NH52', 'NH53', 'NH54', 'NH55', 'NH56', 'NH57', 'NH58', 'NH59', 'NH60', 'NH61', 'NH62', 'NH63', 'NH64', 'NH65', 'NH66', 'NH67', 'NH68',
                      'NH69', 'NH70', 'NH71', 'NH72', 'NH73', 'NH74', 'NH75', 'NH76', 'NH77', 'NH78', 'NH79', 'NH80', 'NH81', 'NH82', 'NH83', 'NH84', 'NH85', 'NH86', 'NH87', 'NH88', 'NH89', 'NH90',
                      'NH91', 'NH92', 'NH93', 'NH94', 'NH95', 'NH96', 'NH97', 'NH98', 'NJ00', 'NJ01', 'NJ02', 'NJ03', 'NJ04', 'NJ05', 'NJ06', 'NJ10', 'NJ11', 'NJ12', 'NJ13', 'NJ14', 'NJ15', 'NJ16',
                      'NJ17', 'NJ20', 'NJ21', 'NJ22', 'NJ23', 'NJ24', 'NJ25', 'NJ26', 'NJ27', 'NJ30', 'NJ31', 'NJ32', 'NJ33', 'NJ34', 'NJ35', 'NJ36', 'NJ40', 'NJ41', 'NJ42', 'NJ43', 'NJ44', 'NJ45',
                      'NJ46', 'NJ50', 'NJ51', 'NJ52', 'NJ53', 'NJ54', 'NJ55', 'NJ56', 'NJ60', 'NJ61', 'NJ62', 'NJ63', 'NJ64', 'NJ65', 'NJ66', 'NJ70', 'NJ71', 'NJ72', 'NJ73', 'NJ74', 'NJ75', 'NJ76',
                      'NJ80', 'NJ81', 'NJ82', 'NJ83', 'NJ84', 'NJ85', 'NJ86', 'NJ90', 'NJ91', 'NJ92', 'NJ93', 'NJ94', 'NJ95', 'NJ96', 'NK02', 'NK03', 'NK04', 'NK05', 'NK06', 'NK13', 'NK14', 'NK15',
                      'NL57', 'NL58', 'NL68', 'NL69', 'NL79', 'NL84', 'NL93', 'NL94', 'NM04', 'NM05', 'NM14', 'NM15', 'NM16', 'NM19', 'NM21', 'NM22', 'NM23', 'NM24', 'NM25', 'NM26', 'NM29', 'NM31',
                      'NM32', 'NM33', 'NM34', 'NM35', 'NM37', 'NM38', 'NM39', 'NM40', 'NM41', 'NM42', 'NM43', 'NM44', 'NM45', 'NM46', 'NM47', 'NM48', 'NM49', 'NM51', 'NM52', 'NM53', 'NM54', 'NM55',
                      'NM56', 'NM57', 'NM59', 'NM60', 'NM61', 'NM62', 'NM63', 'NM64', 'NM65', 'NM66', 'NM67', 'NM68', 'NM69', 'NM70', 'NM71', 'NM72', 'NM73', 'NM74', 'NM75', 'NM76', 'NM77', 'NM78',
                      'NM79', 'NM80', 'NM81', 'NM82', 'NM83', 'NM84', 'NM85', 'NM86', 'NM87', 'NM88', 'NM89', 'NM90', 'NM91', 'NM92', 'NM93', 'NM94', 'NM95', 'NM96', 'NM97', 'NM98', 'NM99', 'NN00',
                      'NN01', 'NN02', 'NN03', 'NN04', 'NN05', 'NN06', 'NN07', 'NN08', 'NN09', 'NN10', 'NN11', 'NN12', 'NN13', 'NN14', 'NN15', 'NN16', 'NN17', 'NN18', 'NN19', 'NN20', 'NN21', 'NN22',
                      'NN23', 'NN24', 'NN25', 'NN26', 'NN27', 'NN28', 'NN29', 'NN30', 'NN31', 'NN32', 'NN33', 'NN34', 'NN35', 'NN36', 'NN37', 'NN38', 'NN39', 'NN40', 'NN41', 'NN42', 'NN43', 'NN44',
                      'NN45', 'NN46', 'NN47', 'NN48', 'NN49', 'NN50', 'NN51', 'NN52', 'NN53', 'NN54', 'NN55', 'NN56', 'NN57', 'NN58', 'NN59', 'NN60', 'NN61', 'NN62', 'NN63', 'NN64', 'NN65', 'NN66',
                      'NN67', 'NN68', 'NN69', 'NN70', 'NN71', 'NN72', 'NN73', 'NN74', 'NN75', 'NN76', 'NN77', 'NN78', 'NN79', 'NN80', 'NN81', 'NN82', 'NN83', 'NN84', 'NN85', 'NN86', 'NN87', 'NN88',
                      'NN89', 'NN90', 'NN91', 'NN92', 'NN93', 'NN94', 'NN95', 'NN96', 'NN97', 'NN98', 'NN99', 'NO00', 'NO01', 'NO02', 'NO03', 'NO04', 'NO05', 'NO06', 'NO07', 'NO08', 'NO09', 'NO10',
                      'NO11', 'NO12', 'NO13', 'NO14', 'NO15', 'NO16', 'NO17', 'NO18', 'NO19', 'NO20', 'NO21', 'NO22', 'NO23', 'NO24', 'NO25', 'NO26', 'NO27', 'NO28', 'NO29', 'NO30', 'NO31', 'NO32',
                      'NO33', 'NO34', 'NO35', 'NO36', 'NO37', 'NO38', 'NO39', 'NO40', 'NO41', 'NO42', 'NO43', 'NO44', 'NO45', 'NO46', 'NO47', 'NO48', 'NO49', 'NO50', 'NO51', 'NO52', 'NO53', 'NO54',
                      'NO55', 'NO56', 'NO57', 'NO58', 'NO59', 'NO60', 'NO61', 'NO63', 'NO64', 'NO65', 'NO66', 'NO67', 'NO68', 'NO69', 'NO74', 'NO75', 'NO76', 'NO77', 'NO78', 'NO79', 'NO86', 'NO87',
                      'NO88', 'NO89', 'NO99', 'NR15', 'NR16', 'NR24', 'NR25', 'NR26', 'NR27', 'NR33', 'NR34', 'NR35', 'NR36', 'NR37', 'NR38', 'NR39', 'NR44', 'NR45', 'NR46', 'NR47', 'NR48', 'NR49',
                      'NR50', 'NR51', 'NR56', 'NR57', 'NR58', 'NR59', 'NR60', 'NR61', 'NR62', 'NR63', 'NR64', 'NR65', 'NR67', 'NR68', 'NR69', 'NR70', 'NR71', 'NR72', 'NR73', 'NR74', 'NR75', 'NR76',
                      'NR77', 'NR78', 'NR79', 'NR82', 'NR83', 'NR84', 'NR85', 'NR86', 'NR87', 'NR88', 'NR89', 'NR91', 'NR92', 'NR93', 'NR94', 'NR95', 'NR96', 'NR97', 'NR98', 'NR99', 'NS00', 'NS01',
                      'NS02', 'NS03', 'NS04', 'NS05', 'NS06', 'NS07', 'NS08', 'NS09', 'NS10', 'NS14', 'NS15', 'NS16', 'NS17', 'NS18', 'NS19', 'NS20', 'NS21', 'NS22', 'NS23', 'NS24', 'NS25', 'NS26',
                      'NS27', 'NS28', 'NS29', 'NS30', 'NS31', 'NS32', 'NS33', 'NS34', 'NS35', 'NS36', 'NS37', 'NS38', 'NS39', 'NS40', 'NS41', 'NS42', 'NS43', 'NS44', 'NS45', 'NS46', 'NS47', 'NS48',
                      'NS49', 'NS50', 'NS51', 'NS52', 'NS53', 'NS54', 'NS55', 'NS56', 'NS57', 'NS58', 'NS59', 'NS60', 'NS61', 'NS62', 'NS63', 'NS64', 'NS65', 'NS66', 'NS67', 'NS68', 'NS69', 'NS70',
                      'NS71', 'NS72', 'NS73', 'NS74', 'NS75', 'NS76', 'NS77', 'NS78', 'NS79', 'NS80', 'NS81', 'NS82', 'NS83', 'NS84', 'NS85', 'NS86', 'NS87', 'NS88', 'NS89', 'NS90', 'NS91', 'NS92',
                      'NS93', 'NS94', 'NS95', 'NS96', 'NS97', 'NS98', 'NS99', 'NT00', 'NT01', 'NT02', 'NT03', 'NT04', 'NT05', 'NT06', 'NT07', 'NT08', 'NT09', 'NT10', 'NT11', 'NT12', 'NT13', 'NT14',
                      'NT15', 'NT16', 'NT17', 'NT18', 'NT19', 'NT20', 'NT21', 'NT22', 'NT23', 'NT24', 'NT25', 'NT26', 'NT27', 'NT28', 'NT29', 'NT30', 'NT31', 'NT32', 'NT33', 'NT34', 'NT35', 'NT36',
                      'NT37', 'NT38', 'NT39', 'NT40', 'NT41', 'NT42', 'NT43', 'NT44', 'NT45', 'NT46', 'NT47', 'NT48', 'NT49', 'NT50', 'NT51', 'NT52', 'NT53', 'NT54', 'NT55', 'NT56', 'NT57', 'NT58',
                      'NT59', 'NT60', 'NT61', 'NT62', 'NT63', 'NT64', 'NT65', 'NT66', 'NT67', 'NT68', 'NT69', 'NT70', 'NT71', 'NT72', 'NT73', 'NT74', 'NT75', 'NT76', 'NT77', 'NT80', 'NT81', 'NT82',
                      'NT83', 'NT84', 'NT85', 'NT86', 'NT87', 'NT90', 'NT91', 'NT92', 'NT93', 'NT94', 'NT95', 'NT96', 'NU00', 'NU01', 'NU02', 'NU03', 'NU04', 'NU05', 'NU10', 'NU11', 'NU12', 'NU13',
                      'NU14', 'NU20', 'NU21', 'NU22', 'NU23', 'NW95', 'NW96', 'NW97', 'NX03', 'NX04', 'NX05', 'NX06', 'NX07', 'NX08', 'NX09', 'NX12', 'NX13', 'NX14', 'NX15', 'NX16', 'NX17', 'NX18',
                      'NX19', 'NX23', 'NX24', 'NX25', 'NX26', 'NX27', 'NX28', 'NX29', 'NX30', 'NX33', 'NX34', 'NX35', 'NX36', 'NX37', 'NX38', 'NX39', 'NX40', 'NX43', 'NX44', 'NX45', 'NX46', 'NX47',
                      'NX48', 'NX49', 'NX54', 'NX55', 'NX56', 'NX57', 'NX58', 'NX59', 'NX64', 'NX65', 'NX66', 'NX67', 'NX68', 'NX69', 'NX74', 'NX75', 'NX76', 'NX77', 'NX78', 'NX79', 'NX84', 'NX85',
                      'NX86', 'NX87', 'NX88', 'NX89', 'NX90', 'NX91', 'NX92', 'NX93', 'NX94', 'NX95', 'NX96', 'NX97', 'NX98', 'NX99', 'NY00', 'NY01', 'NY02', 'NY03', 'NY04', 'NY05', 'NY06', 'NY07',
                      'NY08', 'NY09', 'NY10', 'NY11', 'NY12', 'NY13', 'NY14', 'NY15', 'NY16', 'NY17', 'NY18', 'NY19', 'NY20', 'NY21', 'NY22', 'NY23', 'NY24', 'NY25', 'NY26', 'NY27', 'NY28', 'NY29',
                      'NY30', 'NY31', 'NY32', 'NY33', 'NY34', 'NY35', 'NY36', 'NY37', 'NY38', 'NY39', 'NY40', 'NY41', 'NY42', 'NY43', 'NY44', 'NY45', 'NY46', 'NY47', 'NY48', 'NY49', 'NY50', 'NY51',
                      'NY52', 'NY53', 'NY54', 'NY55', 'NY56', 'NY57', 'NY58', 'NY59', 'NY60', 'NY61', 'NY62', 'NY63', 'NY64', 'NY65', 'NY66', 'NY67', 'NY68', 'NY69', 'NY70', 'NY71', 'NY72', 'NY73',
                      'NY74', 'NY75', 'NY76', 'NY77', 'NY78', 'NY79', 'NY80', 'NY81', 'NY82', 'NY83', 'NY84', 'NY85', 'NY86', 'NY87', 'NY88', 'NY89', 'NY90', 'NY91', 'NY92', 'NY93', 'NY94', 'NY95',
                      'NY96', 'NY97', 'NY98', 'NY99', 'NZ00', 'NZ01', 'NZ02', 'NZ03', 'NZ04', 'NZ05', 'NZ06', 'NZ07', 'NZ08', 'NZ09', 'NZ10', 'NZ11', 'NZ12', 'NZ13', 'NZ14', 'NZ15', 'NZ16', 'NZ17',
                      'NZ18', 'NZ19', 'NZ20', 'NZ21', 'NZ22', 'NZ23', 'NZ24', 'NZ25', 'NZ26', 'NZ27', 'NZ28', 'NZ29', 'NZ30', 'NZ31', 'NZ32', 'NZ33', 'NZ34', 'NZ35', 'NZ36', 'NZ37', 'NZ38', 'NZ39',
                      'NZ40', 'NZ41', 'NZ42', 'NZ43', 'NZ44', 'NZ45', 'NZ46', 'NZ50', 'NZ51', 'NZ52', 'NZ53', 'NZ60', 'NZ61', 'NZ62', 'NZ70', 'NZ71', 'NZ72', 'NZ80', 'NZ81', 'NZ90', 'NZ91', 'OV00',
                      'SC16', 'SC17', 'SC26', 'SC27', 'SC28', 'SC36', 'SC37', 'SC38', 'SC39', 'SC47', 'SC48', 'SC49', 'SD08', 'SD09', 'SD16', 'SD17', 'SD18', 'SD19', 'SD20', 'SD21', 'SD22', 'SD23',
                      'SD24', 'SD25', 'SD26', 'SD27', 'SD28', 'SD29', 'SD30', 'SD31', 'SD32', 'SD33', 'SD34', 'SD35', 'SD36', 'SD37', 'SD38', 'SD39', 'SD40', 'SD41', 'SD42', 'SD43', 'SD44', 'SD45',
                      'SD46', 'SD47', 'SD48', 'SD49', 'SD50', 'SD51', 'SD52', 'SD53', 'SD54', 'SD55', 'SD56', 'SD57', 'SD58', 'SD59', 'SD60', 'SD61', 'SD62', 'SD63', 'SD64', 'SD65', 'SD66', 'SD67',
                      'SD68', 'SD69', 'SD70', 'SD71', 'SD72', 'SD73', 'SD74', 'SD75', 'SD76', 'SD77', 'SD78', 'SD79', 'SD80', 'SD81', 'SD82', 'SD83', 'SD84', 'SD85', 'SD86', 'SD87', 'SD88', 'SD89',
                      'SD90', 'SD91', 'SD92', 'SD93', 'SD94', 'SD95', 'SD96', 'SD97', 'SD98', 'SD99', 'SE00', 'SE01', 'SE02', 'SE03', 'SE04', 'SE05', 'SE06', 'SE07', 'SE08', 'SE09', 'SE10', 'SE11',
                      'SE12', 'SE13', 'SE14', 'SE15', 'SE16', 'SE17', 'SE18', 'SE19', 'SE20', 'SE21', 'SE22', 'SE23', 'SE24', 'SE25', 'SE26', 'SE27', 'SE28', 'SE29', 'SE30', 'SE31', 'SE32', 'SE33',
                      'SE34', 'SE35', 'SE36', 'SE37', 'SE38', 'SE39', 'SE40', 'SE41', 'SE42', 'SE43', 'SE44', 'SE45', 'SE46', 'SE47', 'SE48', 'SE49', 'SE50', 'SE51', 'SE52', 'SE53', 'SE54', 'SE55',
                      'SE56', 'SE57', 'SE58', 'SE59', 'SE60', 'SE61', 'SE62', 'SE63', 'SE64', 'SE65', 'SE66', 'SE67', 'SE68', 'SE69', 'SE70', 'SE71', 'SE72', 'SE73', 'SE74', 'SE75', 'SE76', 'SE77',
                      'SE78', 'SE79', 'SE80', 'SE81', 'SE82', 'SE83', 'SE84', 'SE85', 'SE86', 'SE87', 'SE88', 'SE89', 'SE90', 'SE91', 'SE92', 'SE93', 'SE94', 'SE95', 'SE96', 'SE97', 'SE98', 'SE99',
                      'SH12', 'SH13', 'SH22', 'SH23', 'SH24', 'SH27', 'SH28', 'SH29', 'SH32', 'SH33', 'SH34', 'SH36', 'SH37', 'SH38', 'SH39', 'SH43', 'SH44', 'SH45', 'SH46', 'SH47', 'SH48', 'SH49',
                      'SH50', 'SH51', 'SH52', 'SH53', 'SH54', 'SH55', 'SH56', 'SH57', 'SH58', 'SH59', 'SH60', 'SH61', 'SH62', 'SH63', 'SH64', 'SH65', 'SH66', 'SH67', 'SH68', 'SH70', 'SH71', 'SH72',
                      'SH73', 'SH74', 'SH75', 'SH76', 'SH77', 'SH78', 'SH80', 'SH81', 'SH82', 'SH83', 'SH84', 'SH85', 'SH86', 'SH87', 'SH88', 'SH90', 'SH91', 'SH92', 'SH93', 'SH94', 'SH95', 'SH96',
                      'SH97', 'SH98', 'SJ00', 'SJ01', 'SJ02', 'SJ03', 'SJ04', 'SJ05', 'SJ06', 'SJ07', 'SJ08', 'SJ10', 'SJ11', 'SJ12', 'SJ13', 'SJ14', 'SJ15', 'SJ16', 'SJ17', 'SJ18', 'SJ19', 'SJ20',
                      'SJ21', 'SJ22', 'SJ23', 'SJ24', 'SJ25', 'SJ26', 'SJ27', 'SJ28', 'SJ29', 'SJ30', 'SJ31', 'SJ32', 'SJ33', 'SJ34', 'SJ35', 'SJ36', 'SJ37', 'SJ38', 'SJ39', 'SJ40', 'SJ41', 'SJ42',
                      'SJ43', 'SJ44', 'SJ45', 'SJ46', 'SJ47', 'SJ48', 'SJ49', 'SJ50', 'SJ51', 'SJ52', 'SJ53', 'SJ54', 'SJ55', 'SJ56', 'SJ57', 'SJ58', 'SJ59', 'SJ60', 'SJ61', 'SJ62', 'SJ63', 'SJ64',
                      'SJ65', 'SJ66', 'SJ67', 'SJ68', 'SJ69', 'SJ70', 'SJ71', 'SJ72', 'SJ73', 'SJ74', 'SJ75', 'SJ76', 'SJ77', 'SJ78', 'SJ79', 'SJ80', 'SJ81', 'SJ82', 'SJ83', 'SJ84', 'SJ85', 'SJ86',
                      'SJ87', 'SJ88', 'SJ89', 'SJ90', 'SJ91', 'SJ92', 'SJ93', 'SJ94', 'SJ95', 'SJ96', 'SJ97', 'SJ98', 'SJ99', 'SK00', 'SK01', 'SK02', 'SK03', 'SK04', 'SK05', 'SK06', 'SK07', 'SK08',
                      'SK09', 'SK10', 'SK11', 'SK12', 'SK13', 'SK14', 'SK15', 'SK16', 'SK17', 'SK18', 'SK19', 'SK20', 'SK21', 'SK22', 'SK23', 'SK24', 'SK25', 'SK26', 'SK27', 'SK28', 'SK29', 'SK30',
                      'SK31', 'SK32', 'SK33', 'SK34', 'SK35', 'SK36', 'SK37', 'SK38', 'SK39', 'SK40', 'SK41', 'SK42', 'SK43', 'SK44', 'SK45', 'SK46', 'SK47', 'SK48', 'SK49', 'SK50', 'SK51', 'SK52',
                      'SK53', 'SK54', 'SK55', 'SK56', 'SK57', 'SK58', 'SK59', 'SK60', 'SK61', 'SK62', 'SK63', 'SK64', 'SK65', 'SK66', 'SK67', 'SK68', 'SK69', 'SK70', 'SK71', 'SK72', 'SK73', 'SK74',
                      'SK75', 'SK76', 'SK77', 'SK78', 'SK79', 'SK80', 'SK81', 'SK82', 'SK83', 'SK84', 'SK85', 'SK86', 'SK87', 'SK88', 'SK89', 'SK90', 'SK91', 'SK92', 'SK93', 'SK94', 'SK95', 'SK96',
                      'SK97', 'SK98', 'SK99', 'SM40', 'SM50', 'SM60', 'SM62', 'SM70', 'SM71', 'SM72', 'SM73', 'SM80', 'SM81', 'SM82', 'SM83', 'SM84', 'SM90', 'SM91', 'SM92', 'SM93', 'SM94', 'SN00',
                      'SN01', 'SN02', 'SN03', 'SN04', 'SN10', 'SN11', 'SN12', 'SN13', 'SN14', 'SN15', 'SN20', 'SN21', 'SN22', 'SN23', 'SN24', 'SN25', 'SN30', 'SN31', 'SN32', 'SN33', 'SN34', 'SN35',
                      'SN36', 'SN40', 'SN41', 'SN42', 'SN43', 'SN44', 'SN45', 'SN46', 'SN50', 'SN51', 'SN52', 'SN53', 'SN54', 'SN55', 'SN56', 'SN57', 'SN58', 'SN59', 'SN60', 'SN61', 'SN62', 'SN63',
                      'SN64', 'SN65', 'SN66', 'SN67', 'SN68', 'SN69', 'SN70', 'SN71', 'SN72', 'SN73', 'SN74', 'SN75', 'SN76', 'SN77', 'SN78', 'SN79', 'SN80', 'SN81', 'SN82', 'SN83', 'SN84', 'SN85',
                      'SN86', 'SN87', 'SN88', 'SN89', 'SN90', 'SN91', 'SN92', 'SN93', 'SN94', 'SN95', 'SN96', 'SN97', 'SN98', 'SN99', 'SO00', 'SO01', 'SO02', 'SO03', 'SO04', 'SO05', 'SO06', 'SO07',
                      'SO08', 'SO09', 'SO10', 'SO11', 'SO12', 'SO13', 'SO14', 'SO15', 'SO16', 'SO17', 'SO18', 'SO19', 'SO20', 'SO21', 'SO22', 'SO23', 'SO24', 'SO25', 'SO26', 'SO27', 'SO28', 'SO29',
                      'SO30', 'SO31', 'SO32', 'SO33', 'SO34', 'SO35', 'SO36', 'SO37', 'SO38', 'SO39', 'SO40', 'SO41', 'SO42', 'SO43', 'SO44', 'SO45', 'SO46', 'SO47', 'SO48', 'SO49', 'SO50', 'SO51',
                      'SO52', 'SO53', 'SO54', 'SO55', 'SO56', 'SO57', 'SO58', 'SO59', 'SO60', 'SO61', 'SO62', 'SO63', 'SO64', 'SO65', 'SO66', 'SO67', 'SO68', 'SO69', 'SO70', 'SO71', 'SO72', 'SO73',
                      'SO74', 'SO75', 'SO76', 'SO77', 'SO78', 'SO79', 'SO80', 'SO81', 'SO82', 'SO83', 'SO84', 'SO85', 'SO86', 'SO87', 'SO88', 'SO89', 'SO90', 'SO91', 'SO92', 'SO93', 'SO94', 'SO95',
                      'SO96', 'SO97', 'SO98', 'SO99', 'SP00', 'SP01', 'SP02', 'SP03', 'SP04', 'SP05', 'SP06', 'SP07', 'SP08', 'SP09', 'SP10', 'SP11', 'SP12', 'SP13', 'SP14', 'SP15', 'SP16', 'SP17',
                      'SP18', 'SP19', 'SP20', 'SP21', 'SP22', 'SP23', 'SP24', 'SP25', 'SP26', 'SP27', 'SP28', 'SP29', 'SP30', 'SP31', 'SP32', 'SP33', 'SP34', 'SP35', 'SP36', 'SP37', 'SP38', 'SP39',
                      'SP40', 'SP41', 'SP42', 'SP43', 'SP44', 'SP45', 'SP46', 'SP47', 'SP48', 'SP49', 'SP50', 'SP51', 'SP52', 'SP53', 'SP54', 'SP55', 'SP56', 'SP57', 'SP58', 'SP59', 'SP60', 'SP61',
                      'SP62', 'SP63', 'SP64', 'SP65', 'SP66', 'SP67', 'SP68', 'SP69', 'SP70', 'SP71', 'SP72', 'SP73', 'SP74', 'SP75', 'SP76', 'SP77', 'SP78', 'SP79', 'SP80', 'SP81', 'SP82', 'SP83',
                      'SP84', 'SP85', 'SP86', 'SP87', 'SP88', 'SP89', 'SP90', 'SP91', 'SP92', 'SP93', 'SP94', 'SP95', 'SP96', 'SP97', 'SP98', 'SP99', 'SR89', 'SR99', 'SS09', 'SS10', 'SS11', 'SS14',
                      'SS19', 'SS20', 'SS21', 'SS22', 'SS30', 'SS31', 'SS32', 'SS38', 'SS39', 'SS40', 'SS41', 'SS42', 'SS43', 'SS44', 'SS48', 'SS49', 'SS50', 'SS51', 'SS52', 'SS53', 'SS54', 'SS58',
                      'SS59', 'SS60', 'SS61', 'SS62', 'SS63', 'SS64', 'SS68', 'SS69', 'SS70', 'SS71', 'SS72', 'SS73', 'SS74', 'SS75', 'SS77', 'SS78', 'SS79', 'SS80', 'SS81', 'SS82', 'SS83', 'SS84',
                      'SS87', 'SS88', 'SS89', 'SS90', 'SS91', 'SS92', 'SS93', 'SS94', 'SS96', 'SS97', 'SS98', 'SS99', 'ST00', 'ST01', 'ST02', 'ST03', 'ST04', 'ST06', 'ST07', 'ST08', 'ST09', 'ST10',
                      'ST11', 'ST12', 'ST13', 'ST14', 'ST16', 'ST17', 'ST18', 'ST19', 'ST20', 'ST21', 'ST22', 'ST23', 'ST24', 'ST25', 'ST26', 'ST27', 'ST28', 'ST29', 'ST30', 'ST31', 'ST32', 'ST33',
                      'ST34', 'ST35', 'ST36', 'ST37', 'ST38', 'ST39', 'ST40', 'ST41', 'ST42', 'ST43', 'ST44', 'ST45', 'ST46', 'ST47', 'ST48', 'ST49', 'ST50', 'ST51', 'ST52', 'ST53', 'ST54', 'ST55',
                      'ST56', 'ST57', 'ST58', 'ST59', 'ST60', 'ST61', 'ST62', 'ST63', 'ST64', 'ST65', 'ST66', 'ST67', 'ST68', 'ST69', 'ST70', 'ST71', 'ST72', 'ST73', 'ST74', 'ST75', 'ST76', 'ST77',
                      'ST78', 'ST79', 'ST80', 'ST81', 'ST82', 'ST83', 'ST84', 'ST85', 'ST86', 'ST87', 'ST88', 'ST89', 'ST90', 'ST91', 'ST92', 'ST93', 'ST94', 'ST95', 'ST96', 'ST97', 'ST98', 'ST99',
                      'SU00', 'SU01', 'SU02', 'SU03', 'SU04', 'SU05', 'SU06', 'SU07', 'SU08', 'SU09', 'SU10', 'SU11', 'SU12', 'SU13', 'SU14', 'SU15', 'SU16', 'SU17', 'SU18', 'SU19', 'SU20', 'SU21',
                      'SU22', 'SU23', 'SU24', 'SU25', 'SU26', 'SU27', 'SU28', 'SU29', 'SU30', 'SU31', 'SU32', 'SU33', 'SU34', 'SU35', 'SU36', 'SU37', 'SU38', 'SU39', 'SU40', 'SU41', 'SU42', 'SU43',
                      'SU44', 'SU45', 'SU46', 'SU47', 'SU48', 'SU49', 'SU50', 'SU51', 'SU52', 'SU53', 'SU54', 'SU55', 'SU56', 'SU57', 'SU58', 'SU59', 'SU60', 'SU61', 'SU62', 'SU63', 'SU64', 'SU65',
                      'SU66', 'SU67', 'SU68', 'SU69', 'SU70', 'SU71', 'SU72', 'SU73', 'SU74', 'SU75', 'SU76', 'SU77', 'SU78', 'SU79', 'SU80', 'SU81', 'SU82', 'SU83', 'SU84', 'SU85', 'SU86', 'SU87',
                      'SU88', 'SU89', 'SU90', 'SU91', 'SU92', 'SU93', 'SU94', 'SU95', 'SU96', 'SU97', 'SU98', 'SU99', 'SV80', 'SV81', 'SV90', 'SV91', 'SW21', 'SW32', 'SW33', 'SW42', 'SW43', 'SW44',
                      'SW52', 'SW53', 'SW54', 'SW61', 'SW62', 'SW63', 'SW64', 'SW65', 'SW71', 'SW72', 'SW73', 'SW74', 'SW75', 'SW76', 'SW81', 'SW82', 'SW83', 'SW84', 'SW85', 'SW86', 'SW87', 'SW93',
                      'SW94', 'SW95', 'SW96', 'SW97', 'SW98', 'SX03', 'SX04', 'SX05', 'SX06', 'SX07', 'SX08', 'SX09', 'SX14', 'SX15', 'SX16', 'SX17', 'SX18', 'SX19', 'SX25', 'SX26', 'SX27', 'SX28',
                      'SX29', 'SX33', 'SX35', 'SX36', 'SX37', 'SX38', 'SX39', 'SX44', 'SX45', 'SX46', 'SX47', 'SX48', 'SX49', 'SX54', 'SX55', 'SX56', 'SX57', 'SX58', 'SX59', 'SX63', 'SX64', 'SX65',
                      'SX66', 'SX67', 'SX68', 'SX69', 'SX73', 'SX74', 'SX75', 'SX76', 'SX77', 'SX78', 'SX79', 'SX83', 'SX84', 'SX85', 'SX86', 'SX87', 'SX88', 'SX89', 'SX94', 'SX95', 'SX96', 'SX97',
                      'SX98', 'SX99', 'SY07', 'SY08', 'SY09', 'SY18', 'SY19', 'SY28', 'SY29', 'SY38', 'SY39', 'SY48', 'SY49', 'SY58', 'SY59', 'SY66', 'SY67', 'SY68', 'SY69', 'SY77', 'SY78', 'SY79',
                      'SY87', 'SY88', 'SY89', 'SY97', 'SY98', 'SY99', 'SZ07', 'SZ08', 'SZ09', 'SZ19', 'SZ28', 'SZ29', 'SZ38', 'SZ39', 'SZ47', 'SZ48', 'SZ49', 'SZ57', 'SZ58', 'SZ59', 'SZ68', 'SZ69',
                      'SZ79', 'SZ89', 'SZ99', 'TA00', 'TA01', 'TA02', 'TA03', 'TA04', 'TA05', 'TA06', 'TA07', 'TA08', 'TA09', 'TA10', 'TA11', 'TA12', 'TA13', 'TA14', 'TA15', 'TA16', 'TA17', 'TA18',
                      'TA20', 'TA21', 'TA22', 'TA23', 'TA24', 'TA25', 'TA26', 'TA27', 'TA30', 'TA31', 'TA32', 'TA33', 'TA40', 'TA41', 'TA42', 'TF00', 'TF01', 'TF02', 'TF03', 'TF04', 'TF05', 'TF06',
                      'TF07', 'TF08', 'TF09', 'TF10', 'TF11', 'TF12', 'TF13', 'TF14', 'TF15', 'TF16', 'TF17', 'TF18', 'TF19', 'TF20', 'TF21', 'TF22', 'TF23', 'TF24', 'TF25', 'TF26', 'TF27', 'TF28',
                      'TF29', 'TF30', 'TF31', 'TF32', 'TF33', 'TF34', 'TF35', 'TF36', 'TF37', 'TF38', 'TF39', 'TF40', 'TF41', 'TF42', 'TF43', 'TF44', 'TF45', 'TF46', 'TF47', 'TF48', 'TF49', 'TF50',
                      'TF51', 'TF52', 'TF53', 'TF54', 'TF55', 'TF56', 'TF57', 'TF58', 'TF60', 'TF61', 'TF62', 'TF63', 'TF64', 'TF65', 'TF70', 'TF71', 'TF72', 'TF73', 'TF74', 'TF80', 'TF81', 'TF82',
                      'TF83', 'TF84', 'TF90', 'TF91', 'TF92', 'TF93', 'TF94', 'TG00', 'TG01', 'TG02', 'TG03', 'TG04', 'TG10', 'TG11', 'TG12', 'TG13', 'TG14', 'TG20', 'TG21', 'TG22', 'TG23', 'TG24',
                      'TG30', 'TG31', 'TG32', 'TG33', 'TG40', 'TG41', 'TG42', 'TG50', 'TG51', 'TL00', 'TL01', 'TL02', 'TL03', 'TL04', 'TL05', 'TL06', 'TL07', 'TL08', 'TL09', 'TL10', 'TL11', 'TL12',
                      'TL13', 'TL14', 'TL15', 'TL16', 'TL17', 'TL18', 'TL19', 'TL20', 'TL21', 'TL22', 'TL23', 'TL24', 'TL25', 'TL26', 'TL27', 'TL28', 'TL29', 'TL30', 'TL31', 'TL32', 'TL33', 'TL34',
                      'TL35', 'TL36', 'TL37', 'TL38', 'TL39', 'TL40', 'TL41', 'TL42', 'TL43', 'TL44', 'TL45', 'TL46', 'TL47', 'TL48', 'TL49', 'TL50', 'TL51', 'TL52', 'TL53', 'TL54', 'TL55', 'TL56',
                      'TL57', 'TL58', 'TL59', 'TL60', 'TL61', 'TL62', 'TL63', 'TL64', 'TL65', 'TL66', 'TL67', 'TL68', 'TL69', 'TL70', 'TL71', 'TL72', 'TL73', 'TL74', 'TL75', 'TL76', 'TL77', 'TL78',
                      'TL79', 'TL80', 'TL81', 'TL82', 'TL83', 'TL84', 'TL85', 'TL86', 'TL87', 'TL88', 'TL89', 'TL90', 'TL91', 'TL92', 'TL93', 'TL94', 'TL95', 'TL96', 'TL97', 'TL98', 'TL99', 'TM00',
                      'TM01', 'TM02', 'TM03', 'TM04', 'TM05', 'TM06', 'TM07', 'TM08', 'TM09', 'TM10', 'TM11', 'TM12', 'TM13', 'TM14', 'TM15', 'TM16', 'TM17', 'TM18', 'TM19', 'TM21', 'TM22', 'TM23',
                      'TM24', 'TM25', 'TM26', 'TM27', 'TM28', 'TM29', 'TM31', 'TM32', 'TM33', 'TM34', 'TM35', 'TM36', 'TM37', 'TM38', 'TM39', 'TM44', 'TM45', 'TM46', 'TM47', 'TM48', 'TM49', 'TM57',
                      'TM58', 'TM59', 'TQ00', 'TQ01', 'TQ02', 'TQ03', 'TQ04', 'TQ05', 'TQ06', 'TQ07', 'TQ08', 'TQ09', 'TQ10', 'TQ11', 'TQ12', 'TQ13', 'TQ14', 'TQ15', 'TQ16', 'TQ17', 'TQ18', 'TQ19',
                      'TQ20', 'TQ21', 'TQ22', 'TQ23', 'TQ24', 'TQ25', 'TQ26', 'TQ27', 'TQ28', 'TQ29', 'TQ30', 'TQ31', 'TQ32', 'TQ33', 'TQ34', 'TQ35', 'TQ36', 'TQ37', 'TQ38', 'TQ39', 'TQ40', 'TQ41',
                      'TQ42', 'TQ43', 'TQ44', 'TQ45', 'TQ46', 'TQ47', 'TQ48', 'TQ49', 'TQ50', 'TQ51', 'TQ52', 'TQ53', 'TQ54', 'TQ55', 'TQ56', 'TQ57', 'TQ58', 'TQ59', 'TQ60', 'TQ61', 'TQ62', 'TQ63',
                      'TQ64', 'TQ65', 'TQ66', 'TQ67', 'TQ68', 'TQ69', 'TQ70', 'TQ71', 'TQ72', 'TQ73', 'TQ74', 'TQ75', 'TQ76', 'TQ77', 'TQ78', 'TQ79', 'TQ80', 'TQ81', 'TQ82', 'TQ83', 'TQ84', 'TQ85',
                      'TQ86', 'TQ87', 'TQ88', 'TQ89', 'TQ91', 'TQ92', 'TQ93', 'TQ94', 'TQ95', 'TQ96', 'TQ97', 'TQ98', 'TQ99', 'TR01', 'TR02', 'TR03', 'TR04', 'TR05', 'TR06', 'TR07', 'TR08', 'TR09',
                      'TR12', 'TR13', 'TR14', 'TR15', 'TR16', 'TR17', 'TR19', 'TR23', 'TR24', 'TR25', 'TR26', 'TR27', 'TR33', 'TR34', 'TR35', 'TR36', 'TR37', 'TR46', 'TR47', 'TV49', 'TV59', 'TV69',
                      'HX51']

    TILES_10KM_WALES = ['SH12', 'SH13', 'SH22', 'SH23', 'SH24', 'SH27', 'SH28', 'SH29', 'SH32', 'SH33', 'SH34', 'SH36', 'SH37', 'SH38', 'SH39', 'SH43', 'SH44', 'SH45', 'SH46', 'SH47', 'SH48', 'SH49',
                        'SH50', 'SH51', 'SH52', 'SH53', 'SH54', 'SH55', 'SH56', 'SH57', 'SH58', 'SH59', 'SH60', 'SH61', 'SH62', 'SH63', 'SH64', 'SH65', 'SH66', 'SH67', 'SH68', 'SH70', 'SH71', 'SH72',
                        'SH73', 'SH74', 'SH75', 'SH76', 'SH77', 'SH78', 'SH80', 'SH81', 'SH82', 'SH83', 'SH84', 'SH85', 'SH86', 'SH87', 'SH88', 'SH90', 'SH91', 'SH92', 'SH93', 'SH94', 'SH95', 'SH96',
                        'SH97', 'SH98', 'SJ00', 'SJ01', 'SJ02', 'SJ03', 'SJ04', 'SJ05', 'SJ06', 'SJ07', 'SJ08', 'SJ10', 'SJ11', 'SJ12', 'SJ13', 'SJ14', 'SJ15', 'SJ16', 'SJ17', 'SJ18', 'SJ20', 'SJ21',
                        'SJ22', 'SJ23', 'SJ24', 'SJ25', 'SJ26', 'SJ27', 'SJ28', 'SJ31', 'SJ33', 'SJ34', 'SJ35', 'SJ36', 'SJ37', 'SJ43', 'SJ44', 'SJ45', 'SJ53', 'SJ54', 'SM40', 'SM50', 'SM60', 'SM62',
                        'SM70', 'SM71', 'SM72', 'SM73', 'SM80', 'SM81', 'SM82', 'SM83', 'SM84', 'SM90', 'SM91', 'SM92', 'SM93', 'SM94', 'SN00', 'SN01', 'SN02', 'SN03', 'SN04', 'SN10', 'SN11', 'SN12',
                        'SN13', 'SN14', 'SN15', 'SN20', 'SN21', 'SN22', 'SN23', 'SN24', 'SN25', 'SN30', 'SN31', 'SN32', 'SN33', 'SN34', 'SN35', 'SN36', 'SN40', 'SN41', 'SN42', 'SN43', 'SN44', 'SN45',
                        'SN46', 'SN50', 'SN51', 'SN52', 'SN53', 'SN54', 'SN55', 'SN56', 'SN57', 'SN58', 'SN59', 'SN60', 'SN61', 'SN62', 'SN63', 'SN64', 'SN65', 'SN66', 'SN67', 'SN68', 'SN69', 'SN70',
                        'SN71', 'SN72', 'SN73', 'SN74', 'SN75', 'SN76', 'SN77', 'SN78', 'SN79', 'SN80', 'SN81', 'SN82', 'SN83', 'SN84', 'SN85', 'SN86', 'SN87', 'SN88', 'SN89', 'SN90', 'SN91', 'SN92',
                        'SN93', 'SN94', 'SN95', 'SN96', 'SN97', 'SN98', 'SN99', 'SO00', 'SO01', 'SO02', 'SO03', 'SO04', 'SO05', 'SO06', 'SO07', 'SO08', 'SO09', 'SO10', 'SO11', 'SO12', 'SO13', 'SO14',
                        'SO15', 'SO16', 'SO17', 'SO18', 'SO19', 'SO20', 'SO21', 'SO22', 'SO23', 'SO24', 'SO25', 'SO26', 'SO27', 'SO28', 'SO29', 'SO30', 'SO31', 'SO32', 'SO36', 'SO37', 'SO38', 'SO39',
                        'SO40', 'SO41', 'SO42', 'SO50', 'SO51', 'SR89', 'SR99', 'SS09', 'SS19', 'SS38', 'SS39', 'SS48', 'SS49', 'SS58', 'SS59', 'SS68', 'SS69', 'SS77', 'SS78', 'SS79', 'SS87', 'SS88',
                        'SS89', 'SS96', 'SS97', 'SS98', 'SS99', 'ST06', 'ST07', 'ST08', 'ST09', 'ST16', 'ST17', 'ST18', 'ST19', 'ST26', 'ST27', 'ST28', 'ST29', 'ST36', 'ST37', 'ST38', 'ST39', 'ST47',
                        'ST48', 'ST49', 'ST58', 'ST59']

    TILES_10KM_ENGLAND = ['NT60', 'NT70', 'NT71', 'NT73', 'NT80', 'NT81', 'NT82', 'NT83', 'NT84', 'NT90', 'NT91', 'NT92', 'NT93', 'NT94', 'NT95', 'NU00', 'NU01', 'NU02', 'NU03', 'NU04', 'NU05',
                          'NU10', 'NU11', 'NU12', 'NU13', 'NU14', 'NU20', 'NU21', 'NU22', 'NU23', 'NX90', 'NX91', 'NX92', 'NX93', 'NY00', 'NY01', 'NY02', 'NY03', 'NY04', 'NY05', 'NY10', 'NY11',
                          'NY12', 'NY13', 'NY14', 'NY15', 'NY16', 'NY20', 'NY21', 'NY22', 'NY23', 'NY24', 'NY25', 'NY26', 'NY30', 'NY31', 'NY32', 'NY33', 'NY34', 'NY35', 'NY36', 'NY37', 'NY40',
                          'NY41', 'NY42', 'NY43', 'NY44', 'NY45', 'NY46', 'NY47', 'NY48', 'NY50', 'NY51', 'NY52', 'NY53', 'NY54', 'NY55', 'NY56', 'NY57', 'NY58', 'NY59', 'NY60', 'NY61', 'NY62',
                          'NY63', 'NY64', 'NY65', 'NY66', 'NY67', 'NY68', 'NY69', 'NY70', 'NY71', 'NY72', 'NY73', 'NY74', 'NY75', 'NY76', 'NY77', 'NY78', 'NY79', 'NY80', 'NY81', 'NY82', 'NY83',
                          'NY84', 'NY85', 'NY86', 'NY87', 'NY88', 'NY89', 'NY90', 'NY91', 'NY92', 'NY93', 'NY94', 'NY95', 'NY96', 'NY97', 'NY98', 'NY99', 'NZ00', 'NZ01', 'NZ02', 'NZ03', 'NZ04',
                          'NZ05', 'NZ06', 'NZ07', 'NZ08', 'NZ09', 'NZ10', 'NZ11', 'NZ12', 'NZ13', 'NZ14', 'NZ15', 'NZ16', 'NZ17', 'NZ18', 'NZ19', 'NZ20', 'NZ21', 'NZ22', 'NZ23', 'NZ24', 'NZ25',
                          'NZ26', 'NZ27', 'NZ28', 'NZ29', 'NZ30', 'NZ31', 'NZ32', 'NZ33', 'NZ34', 'NZ35', 'NZ36', 'NZ37', 'NZ38', 'NZ39', 'NZ40', 'NZ41', 'NZ42', 'NZ43', 'NZ44', 'NZ45', 'NZ46',
                          'NZ50', 'NZ51', 'NZ52', 'NZ53', 'NZ60', 'NZ61', 'NZ62', 'NZ70', 'NZ71', 'NZ72', 'NZ80', 'NZ81', 'NZ90', 'NZ91', 'OV00', 'SD08', 'SD09', 'SD16', 'SD17', 'SD18', 'SD19',
                          'SD20', 'SD21', 'SD22', 'SD23', 'SD24', 'SD25', 'SD26', 'SD27', 'SD28', 'SD29', 'SD30', 'SD31', 'SD32', 'SD33', 'SD34', 'SD35', 'SD36', 'SD37', 'SD38', 'SD39', 'SD40',
                          'SD41', 'SD42', 'SD43', 'SD44', 'SD45', 'SD46', 'SD47', 'SD48', 'SD49', 'SD50', 'SD51', 'SD52', 'SD53', 'SD54', 'SD55', 'SD56', 'SD57', 'SD58', 'SD59', 'SD60', 'SD61',
                          'SD62', 'SD63', 'SD64', 'SD65', 'SD66', 'SD67', 'SD68', 'SD69', 'SD70', 'SD71', 'SD72', 'SD73', 'SD74', 'SD75', 'SD76', 'SD77', 'SD78', 'SD79', 'SD80', 'SD81', 'SD82',
                          'SD83', 'SD84', 'SD85', 'SD86', 'SD87', 'SD88', 'SD89', 'SD90', 'SD91', 'SD92', 'SD93', 'SD94', 'SD95', 'SD96', 'SD97', 'SD98', 'SD99', 'SE00', 'SE01', 'SE02', 'SE03',
                          'SE04', 'SE05', 'SE06', 'SE07', 'SE08', 'SE09', 'SE10', 'SE11', 'SE12', 'SE13', 'SE14', 'SE15', 'SE16', 'SE17', 'SE18', 'SE19', 'SE20', 'SE21', 'SE22', 'SE23', 'SE24',
                          'SE25', 'SE26', 'SE27', 'SE28', 'SE29', 'SE30', 'SE31', 'SE32', 'SE33', 'SE34', 'SE35', 'SE36', 'SE37', 'SE38', 'SE39', 'SE40', 'SE41', 'SE42', 'SE43', 'SE44', 'SE45',
                          'SE46', 'SE47', 'SE48', 'SE49', 'SE50', 'SE51', 'SE52', 'SE53', 'SE54', 'SE55', 'SE56', 'SE57', 'SE58', 'SE59', 'SE60', 'SE61', 'SE62', 'SE63', 'SE64', 'SE65', 'SE66',
                          'SE67', 'SE68', 'SE69', 'SE70', 'SE71', 'SE72', 'SE73', 'SE74', 'SE75', 'SE76', 'SE77', 'SE78', 'SE79', 'SE80', 'SE81', 'SE82', 'SE83', 'SE84', 'SE85', 'SE86', 'SE87',
                          'SE88', 'SE89', 'SE90', 'SE91', 'SE92', 'SE93', 'SE94', 'SE95', 'SE96', 'SE97', 'SE98', 'SE99', 'SJ18', 'SJ19', 'SJ20', 'SJ21', 'SJ22', 'SJ23', 'SJ27', 'SJ28', 'SJ29',
                          'SJ30', 'SJ31', 'SJ32', 'SJ33', 'SJ34', 'SJ35', 'SJ36', 'SJ37', 'SJ38', 'SJ39', 'SJ40', 'SJ41', 'SJ42', 'SJ43', 'SJ44', 'SJ45', 'SJ46', 'SJ47', 'SJ48', 'SJ49', 'SJ50',
                          'SJ51', 'SJ52', 'SJ53', 'SJ54', 'SJ55', 'SJ56', 'SJ57', 'SJ58', 'SJ59', 'SJ60', 'SJ61', 'SJ62', 'SJ63', 'SJ64', 'SJ65', 'SJ66', 'SJ67', 'SJ68', 'SJ69', 'SJ70', 'SJ71',
                          'SJ72', 'SJ73', 'SJ74', 'SJ75', 'SJ76', 'SJ77', 'SJ78', 'SJ79', 'SJ80', 'SJ81', 'SJ82', 'SJ83', 'SJ84', 'SJ85', 'SJ86', 'SJ87', 'SJ88', 'SJ89', 'SJ90', 'SJ91', 'SJ92',
                          'SJ93', 'SJ94', 'SJ95', 'SJ96', 'SJ97', 'SJ98', 'SJ99', 'SK00', 'SK01', 'SK02', 'SK03', 'SK04', 'SK05', 'SK06', 'SK07', 'SK08', 'SK09', 'SK10', 'SK11', 'SK12', 'SK13',
                          'SK14', 'SK15', 'SK16', 'SK17', 'SK18', 'SK19', 'SK20', 'SK21', 'SK22', 'SK23', 'SK24', 'SK25', 'SK26', 'SK27', 'SK28', 'SK29', 'SK30', 'SK31', 'SK32', 'SK33', 'SK34',
                          'SK35', 'SK36', 'SK37', 'SK38', 'SK39', 'SK40', 'SK41', 'SK42', 'SK43', 'SK44', 'SK45', 'SK46', 'SK47', 'SK48', 'SK49', 'SK50', 'SK51', 'SK52', 'SK53', 'SK54', 'SK55',
                          'SK56', 'SK57', 'SK58', 'SK59', 'SK60', 'SK61', 'SK62', 'SK63', 'SK64', 'SK65', 'SK66', 'SK67', 'SK68', 'SK69', 'SK70', 'SK71', 'SK72', 'SK73', 'SK74', 'SK75', 'SK76',
                          'SK77', 'SK78', 'SK79', 'SK80', 'SK81', 'SK82', 'SK83', 'SK84', 'SK85', 'SK86', 'SK87', 'SK88', 'SK89', 'SK90', 'SK91', 'SK92', 'SK93', 'SK94', 'SK95', 'SK96', 'SK97',
                          'SK98', 'SK99', 'SO17', 'SO18', 'SO22', 'SO23', 'SO24', 'SO25', 'SO26', 'SO27', 'SO28', 'SO29', 'SO32', 'SO33', 'SO34', 'SO35', 'SO36', 'SO37', 'SO38', 'SO39', 'SO41',
                          'SO42', 'SO43', 'SO44', 'SO45', 'SO46', 'SO47', 'SO48', 'SO49', 'SO50', 'SO51', 'SO52', 'SO53', 'SO54', 'SO55', 'SO56', 'SO57', 'SO58', 'SO59', 'SO60', 'SO61', 'SO62',
                          'SO63', 'SO64', 'SO65', 'SO66', 'SO67', 'SO68', 'SO69', 'SO70', 'SO71', 'SO72', 'SO73', 'SO74', 'SO75', 'SO76', 'SO77', 'SO78', 'SO79', 'SO80', 'SO81', 'SO82', 'SO83',
                          'SO84', 'SO85', 'SO86', 'SO87', 'SO88', 'SO89', 'SO90', 'SO91', 'SO92', 'SO93', 'SO94', 'SO95', 'SO96', 'SO97', 'SO98', 'SO99', 'SP00', 'SP01', 'SP02', 'SP03', 'SP04',
                          'SP05', 'SP06', 'SP07', 'SP08', 'SP09', 'SP10', 'SP11', 'SP12', 'SP13', 'SP14', 'SP15', 'SP16', 'SP17', 'SP18', 'SP19', 'SP20', 'SP21', 'SP22', 'SP23', 'SP24', 'SP25',
                          'SP26', 'SP27', 'SP28', 'SP29', 'SP30', 'SP31', 'SP32', 'SP33', 'SP34', 'SP35', 'SP36', 'SP37', 'SP38', 'SP39', 'SP40', 'SP41', 'SP42', 'SP43', 'SP44', 'SP45', 'SP46',
                          'SP47', 'SP48', 'SP49', 'SP50', 'SP51', 'SP52', 'SP53', 'SP54', 'SP55', 'SP56', 'SP57', 'SP58', 'SP59', 'SP60', 'SP61', 'SP62', 'SP63', 'SP64', 'SP65', 'SP66', 'SP67',
                          'SP68', 'SP69', 'SP70', 'SP71', 'SP72', 'SP73', 'SP74', 'SP75', 'SP76', 'SP77', 'SP78', 'SP79', 'SP80', 'SP81', 'SP82', 'SP83', 'SP84', 'SP85', 'SP86', 'SP87', 'SP88',
                          'SP89', 'SP90', 'SP91', 'SP92', 'SP93', 'SP94', 'SP95', 'SP96', 'SP97', 'SP98', 'SP99', 'SS10', 'SS11', 'SS14', 'SS20', 'SS21', 'SS22', 'SS30', 'SS31', 'SS32', 'SS40',
                          'SS41', 'SS42', 'SS43', 'SS44', 'SS50', 'SS51', 'SS52', 'SS53', 'SS54', 'SS60', 'SS61', 'SS62', 'SS63', 'SS64', 'SS70', 'SS71', 'SS72', 'SS73', 'SS74', 'SS75', 'SS80',
                          'SS81', 'SS82', 'SS83', 'SS84', 'SS90', 'SS91', 'SS92', 'SS93', 'SS94', 'ST00', 'ST01', 'ST02', 'ST03', 'ST04', 'ST10', 'ST11', 'ST12', 'ST13', 'ST14', 'ST20', 'ST21',
                          'ST22', 'ST23', 'ST24', 'ST25', 'ST26', 'ST30', 'ST31', 'ST32', 'ST33', 'ST34', 'ST35', 'ST36', 'ST37', 'ST40', 'ST41', 'ST42', 'ST43', 'ST44', 'ST45', 'ST46', 'ST47',
                          'ST48', 'ST50', 'ST51', 'ST52', 'ST53', 'ST54', 'ST55', 'ST56', 'ST57', 'ST58', 'ST59', 'ST60', 'ST61', 'ST62', 'ST63', 'ST64', 'ST65', 'ST66', 'ST67', 'ST68', 'ST69',
                          'ST70', 'ST71', 'ST72', 'ST73', 'ST74', 'ST75', 'ST76', 'ST77', 'ST78', 'ST79', 'ST80', 'ST81', 'ST82', 'ST83', 'ST84', 'ST85', 'ST86', 'ST87', 'ST88', 'ST89', 'ST90',
                          'ST91', 'ST92', 'ST93', 'ST94', 'ST95', 'ST96', 'ST97', 'ST98', 'ST99', 'SU00', 'SU01', 'SU02', 'SU03', 'SU04', 'SU05', 'SU06', 'SU07', 'SU08', 'SU09', 'SU10', 'SU11',
                          'SU12', 'SU13', 'SU14', 'SU15', 'SU16', 'SU17', 'SU18', 'SU19', 'SU20', 'SU21', 'SU22', 'SU23', 'SU24', 'SU25', 'SU26', 'SU27', 'SU28', 'SU29', 'SU30', 'SU31', 'SU32',
                          'SU33', 'SU34', 'SU35', 'SU36', 'SU37', 'SU38', 'SU39', 'SU40', 'SU41', 'SU42', 'SU43', 'SU44', 'SU45', 'SU46', 'SU47', 'SU48', 'SU49', 'SU50', 'SU51', 'SU52', 'SU53',
                          'SU54', 'SU55', 'SU56', 'SU57', 'SU58', 'SU59', 'SU60', 'SU61', 'SU62', 'SU63', 'SU64', 'SU65', 'SU66', 'SU67', 'SU68', 'SU69', 'SU70', 'SU71', 'SU72', 'SU73', 'SU74',
                          'SU75', 'SU76', 'SU77', 'SU78', 'SU79', 'SU80', 'SU81', 'SU82', 'SU83', 'SU84', 'SU85', 'SU86', 'SU87', 'SU88', 'SU89', 'SU90', 'SU91', 'SU92', 'SU93', 'SU94', 'SU95',
                          'SU96', 'SU97', 'SU98', 'SU99', 'SV80', 'SV81', 'SV90', 'SV91', 'SW21', 'SW32', 'SW33', 'SW42', 'SW43', 'SW44', 'SW52', 'SW53', 'SW54', 'SW61', 'SW62', 'SW63', 'SW64',
                          'SW65', 'SW71', 'SW72', 'SW73', 'SW74', 'SW75', 'SW76', 'SW81', 'SW82', 'SW83', 'SW84', 'SW85', 'SW86', 'SW87', 'SW93', 'SW94', 'SW95', 'SW96', 'SW97', 'SW98', 'SX03',
                          'SX04', 'SX05', 'SX06', 'SX07', 'SX08', 'SX09', 'SX14', 'SX15', 'SX16', 'SX17', 'SX18', 'SX19', 'SX25', 'SX26', 'SX27', 'SX28', 'SX29', 'SX33', 'SX35', 'SX36', 'SX37',
                          'SX38', 'SX39', 'SX44', 'SX45', 'SX46', 'SX47', 'SX48', 'SX49', 'SX54', 'SX55', 'SX56', 'SX57', 'SX58', 'SX59', 'SX63', 'SX64', 'SX65', 'SX66', 'SX67', 'SX68', 'SX69',
                          'SX73', 'SX74', 'SX75', 'SX76', 'SX77', 'SX78', 'SX79', 'SX83', 'SX84', 'SX85', 'SX86', 'SX87', 'SX88', 'SX89', 'SX94', 'SX95', 'SX96', 'SX97', 'SX98', 'SX99', 'SY07',
                          'SY08', 'SY09', 'SY18', 'SY19', 'SY28', 'SY29', 'SY38', 'SY39', 'SY48', 'SY49', 'SY58', 'SY59', 'SY66', 'SY67', 'SY68', 'SY69', 'SY77', 'SY78', 'SY79', 'SY87', 'SY88',
                          'SY89', 'SY97', 'SY98', 'SY99', 'SZ07', 'SZ08', 'SZ09', 'SZ19', 'SZ28', 'SZ29', 'SZ38', 'SZ39', 'SZ47', 'SZ48', 'SZ49', 'SZ57', 'SZ58', 'SZ59', 'SZ68', 'SZ69', 'SZ79',
                          'SZ89', 'SZ99', 'TA00', 'TA01', 'TA02', 'TA03', 'TA04', 'TA05', 'TA06', 'TA07', 'TA08', 'TA09', 'TA10', 'TA11', 'TA12', 'TA13', 'TA14', 'TA15', 'TA16', 'TA17', 'TA18',
                          'TA20', 'TA21', 'TA22', 'TA23', 'TA24', 'TA25', 'TA26', 'TA27', 'TA30', 'TA31', 'TA32', 'TA33', 'TA40', 'TA41', 'TA42', 'TF00', 'TF01', 'TF02', 'TF03', 'TF04', 'TF05',
                          'TF06', 'TF07', 'TF08', 'TF09', 'TF10', 'TF11', 'TF12', 'TF13', 'TF14', 'TF15', 'TF16', 'TF17', 'TF18', 'TF19', 'TF20', 'TF21', 'TF22', 'TF23', 'TF24', 'TF25', 'TF26',
                          'TF27', 'TF28', 'TF29', 'TF30', 'TF31', 'TF32', 'TF33', 'TF34', 'TF35', 'TF36', 'TF37', 'TF38', 'TF39', 'TF40', 'TF41', 'TF42', 'TF43', 'TF44', 'TF45', 'TF46', 'TF47',
                          'TF48', 'TF49', 'TF50', 'TF51', 'TF52', 'TF53', 'TF54', 'TF55', 'TF56', 'TF57', 'TF58', 'TF60', 'TF61', 'TF62', 'TF63', 'TF64', 'TF65', 'TF70', 'TF71', 'TF72', 'TF73',
                          'TF74', 'TF80', 'TF81', 'TF82', 'TF83', 'TF84', 'TF90', 'TF91', 'TF92', 'TF93', 'TF94', 'TG00', 'TG01', 'TG02', 'TG03', 'TG04', 'TG10', 'TG11', 'TG12', 'TG13', 'TG14',
                          'TG20', 'TG21', 'TG22', 'TG23', 'TG24', 'TG30', 'TG31', 'TG32', 'TG33', 'TG40', 'TG41', 'TG42', 'TG50', 'TG51', 'TL00', 'TL01', 'TL02', 'TL03', 'TL04', 'TL05', 'TL06',
                          'TL07', 'TL08', 'TL09', 'TL10', 'TL11', 'TL12', 'TL13', 'TL14', 'TL15', 'TL16', 'TL17', 'TL18', 'TL19', 'TL20', 'TL21', 'TL22', 'TL23', 'TL24', 'TL25', 'TL26', 'TL27',
                          'TL28', 'TL29', 'TL30', 'TL31', 'TL32', 'TL33', 'TL34', 'TL35', 'TL36', 'TL37', 'TL38', 'TL39', 'TL40', 'TL41', 'TL42', 'TL43', 'TL44', 'TL45', 'TL46', 'TL47', 'TL48',
                          'TL49', 'TL50', 'TL51', 'TL52', 'TL53', 'TL54', 'TL55', 'TL56', 'TL57', 'TL58', 'TL59', 'TL60', 'TL61', 'TL62', 'TL63', 'TL64', 'TL65', 'TL66', 'TL67', 'TL68', 'TL69',
                          'TL70', 'TL71', 'TL72', 'TL73', 'TL74', 'TL75', 'TL76', 'TL77', 'TL78', 'TL79', 'TL80', 'TL81', 'TL82', 'TL83', 'TL84', 'TL85', 'TL86', 'TL87', 'TL88', 'TL89', 'TL90',
                          'TL91', 'TL92', 'TL93', 'TL94', 'TL95', 'TL96', 'TL97', 'TL98', 'TL99', 'TM00', 'TM01', 'TM02', 'TM03', 'TM04', 'TM05', 'TM06', 'TM07', 'TM08', 'TM09', 'TM10', 'TM11',
                          'TM12', 'TM13', 'TM14', 'TM15', 'TM16', 'TM17', 'TM18', 'TM19', 'TM21', 'TM22', 'TM23', 'TM24', 'TM25', 'TM26', 'TM27', 'TM28', 'TM29', 'TM31', 'TM32', 'TM33', 'TM34',
                          'TM35', 'TM36', 'TM37', 'TM38', 'TM39', 'TM44', 'TM45', 'TM46', 'TM47', 'TM48', 'TM49', 'TM57', 'TM58', 'TM59', 'TQ00', 'TQ01', 'TQ02', 'TQ03', 'TQ04', 'TQ05', 'TQ06',
                          'TQ07', 'TQ08', 'TQ09', 'TQ10', 'TQ11', 'TQ12', 'TQ13', 'TQ14', 'TQ15', 'TQ16', 'TQ17', 'TQ18', 'TQ19', 'TQ20', 'TQ21', 'TQ22', 'TQ23', 'TQ24', 'TQ25', 'TQ26', 'TQ27',
                          'TQ28', 'TQ29', 'TQ30', 'TQ31', 'TQ32', 'TQ33', 'TQ34', 'TQ35', 'TQ36', 'TQ37', 'TQ38', 'TQ39', 'TQ40', 'TQ41', 'TQ42', 'TQ43', 'TQ44', 'TQ45', 'TQ46', 'TQ47', 'TQ48',
                          'TQ49', 'TQ50', 'TQ51', 'TQ52', 'TQ53', 'TQ54', 'TQ55', 'TQ56', 'TQ57', 'TQ58', 'TQ59', 'TQ60', 'TQ61', 'TQ62', 'TQ63', 'TQ64', 'TQ65', 'TQ66', 'TQ67', 'TQ68', 'TQ69',
                          'TQ70', 'TQ71', 'TQ72', 'TQ73', 'TQ74', 'TQ75', 'TQ76', 'TQ77', 'TQ78', 'TQ79', 'TQ80', 'TQ81', 'TQ82', 'TQ83', 'TQ84', 'TQ85', 'TQ86', 'TQ87', 'TQ88', 'TQ89', 'TQ91',
                          'TQ92', 'TQ93', 'TQ94', 'TQ95', 'TQ96', 'TQ97', 'TQ98', 'TQ99', 'TR01', 'TR02', 'TR03', 'TR04', 'TR05', 'TR06', 'TR07', 'TR08', 'TR09', 'TR12', 'TR13', 'TR14', 'TR15',
                          'TR16', 'TR17', 'TR19', 'TR23', 'TR24', 'TR25', 'TR26', 'TR27', 'TR33', 'TR34', 'TR35', 'TR36', 'TR37', 'TR46', 'TR47', 'TV49', 'TV59', 'TV69']

    TILES_10KM_SCOTLAND = ['HP40', 'HP50', 'HP51', 'HP60', 'HP61', 'HP62', 'HT93', 'HT94', 'HU06', 'HU14', 'HU15', 'HU16', 'HU24', 'HU25', 'HU26', 'HU27', 'HU28', 'HU30', 'HU31', 'HU32', 'HU33',
                           'HU34', 'HU35', 'HU36', 'HU37', 'HU38', 'HU39', 'HU40', 'HU41', 'HU42', 'HU43', 'HU44', 'HU45', 'HU46', 'HU47', 'HU48', 'HU49', 'HU53', 'HU54', 'HU55', 'HU56', 'HU57',
                           'HU58', 'HU59', 'HU66', 'HU67', 'HU68', 'HU69', 'HU77', 'HW62', 'HW63', 'HW73', 'HW83', 'HX62', 'HY10', 'HY20', 'HY21', 'HY22', 'HY23', 'HY30', 'HY31', 'HY32', 'HY33',
                           'HY34', 'HY35', 'HY40', 'HY41', 'HY42', 'HY43', 'HY44', 'HY45', 'HY50', 'HY51', 'HY52', 'HY53', 'HY54', 'HY55', 'HY60', 'HY61', 'HY62', 'HY63', 'HY64', 'HY73', 'HY74',
                           'HY75', 'HZ16', 'HZ17', 'HZ26', 'HZ27', 'NA00', 'NA10', 'NA64', 'NA74', 'NA81', 'NA90', 'NA91', 'NA92', 'NA93', 'NB00', 'NB01', 'NB02', 'NB03', 'NB10', 'NB11', 'NB12',
                           'NB13', 'NB14', 'NB20', 'NB21', 'NB22', 'NB23', 'NB24', 'NB25', 'NB30', 'NB31', 'NB32', 'NB33', 'NB34', 'NB35', 'NB36', 'NB40', 'NB41', 'NB42', 'NB43', 'NB44', 'NB45',
                           'NB46', 'NB52', 'NB53', 'NB54', 'NB55', 'NB56', 'NB90', 'NB91', 'NC00', 'NC01', 'NC02', 'NC03', 'NC10', 'NC11', 'NC12', 'NC13', 'NC14', 'NC15', 'NC16', 'NC20', 'NC21',
                           'NC22', 'NC23', 'NC24', 'NC25', 'NC26', 'NC27', 'NC30', 'NC31', 'NC32', 'NC33', 'NC34', 'NC35', 'NC36', 'NC37', 'NC38', 'NC40', 'NC41', 'NC42', 'NC43', 'NC44', 'NC45',
                           'NC46', 'NC47', 'NC50', 'NC51', 'NC52', 'NC53', 'NC54', 'NC55', 'NC56', 'NC60', 'NC61', 'NC62', 'NC63', 'NC64', 'NC65', 'NC66', 'NC70', 'NC71', 'NC72', 'NC73', 'NC74',
                           'NC75', 'NC76', 'NC80', 'NC81', 'NC82', 'NC83', 'NC84', 'NC85', 'NC86', 'NC87', 'NC90', 'NC91', 'NC92', 'NC93', 'NC94', 'NC95', 'NC96', 'ND01', 'ND02', 'ND03', 'ND04',
                           'ND05', 'ND06', 'ND07', 'ND10', 'ND12', 'ND13', 'ND14', 'ND15', 'ND16', 'ND17', 'ND19', 'ND23', 'ND24', 'ND25', 'ND26', 'ND27', 'ND28', 'ND29', 'ND33', 'ND34', 'ND35',
                           'ND36', 'ND37', 'ND38', 'ND39', 'ND47', 'ND48', 'ND49', 'ND59', 'NF09', 'NF19', 'NF56', 'NF58', 'NF60', 'NF61', 'NF66', 'NF67', 'NF68', 'NF70', 'NF71', 'NF72', 'NF73',
                           'NF74', 'NF75', 'NF76', 'NF77', 'NF80', 'NF81', 'NF82', 'NF83', 'NF84', 'NF85', 'NF86', 'NF87', 'NF88', 'NF89', 'NF95', 'NF96', 'NF97', 'NF98', 'NF99', 'NG07', 'NG08',
                           'NG09', 'NG10', 'NG13', 'NG14', 'NG15', 'NG18', 'NG19', 'NG20', 'NG23', 'NG24', 'NG25', 'NG26', 'NG29', 'NG30', 'NG31', 'NG32', 'NG33', 'NG34', 'NG35', 'NG36', 'NG37',
                           'NG39', 'NG38', 'NG40', 'NG41', 'NG42', 'NG43', 'NG44', 'NG45', 'NG46', 'NG47', 'NG49', 'NG50', 'NG51', 'NG52', 'NG53', 'NG54', 'NG55', 'NG56', 'NG60', 'NG61', 'NG62',
                           'NG63', 'NG64', 'NG65', 'NG66', 'NG70', 'NG71', 'NG72', 'NG73', 'NG74', 'NG75', 'NG76', 'NG77', 'NG78', 'NG79', 'NG80', 'NG81', 'NG82', 'NG83', 'NG84', 'NG85', 'NG86',
                           'NG87', 'NG88', 'NG89', 'NG90', 'NG91', 'NG92', 'NG93', 'NG94', 'NG95', 'NG96', 'NG97', 'NG98', 'NG99', 'NH00', 'NH01', 'NH02', 'NH03', 'NH04', 'NH05', 'NH06', 'NH07',
                           'NH08', 'NH09', 'NH10', 'NH11', 'NH12', 'NH13', 'NH14', 'NH15', 'NH16', 'NH17', 'NH18', 'NH19', 'NH20', 'NH21', 'NH22', 'NH23', 'NH24', 'NH25', 'NH26', 'NH27', 'NH28',
                           'NH29', 'NH30', 'NH31', 'NH32', 'NH33', 'NH34', 'NH35', 'NH36', 'NH37', 'NH38', 'NH39', 'NH40', 'NH41', 'NH42', 'NH43', 'NH44', 'NH45', 'NH46', 'NH47', 'NH48', 'NH49',
                           'NH50', 'NH51', 'NH52', 'NH53', 'NH54', 'NH55', 'NH56', 'NH57', 'NH58', 'NH59', 'NH60', 'NH61', 'NH62', 'NH63', 'NH64', 'NH65', 'NH66', 'NH67', 'NH68', 'NH69', 'NH70',
                           'NH71', 'NH72', 'NH73', 'NH74', 'NH75', 'NH76', 'NH77', 'NH78', 'NH79', 'NH80', 'NH81', 'NH82', 'NH83', 'NH84', 'NH85', 'NH86', 'NH87', 'NH88', 'NH89', 'NH90', 'NH91',
                           'NH92', 'NH93', 'NH94', 'NH95', 'NH96', 'NH97', 'NH98', 'NJ00', 'NJ01', 'NJ02', 'NJ03', 'NJ04', 'NJ05', 'NJ06', 'NJ10', 'NJ11', 'NJ12', 'NJ13', 'NJ14', 'NJ15', 'NJ16',
                           'NJ17', 'NJ20', 'NJ21', 'NJ22', 'NJ23', 'NJ24', 'NJ25', 'NJ26', 'NJ27', 'NJ30', 'NJ31', 'NJ32', 'NJ33', 'NJ34', 'NJ35', 'NJ36', 'NJ40', 'NJ41', 'NJ42', 'NJ43', 'NJ44',
                           'NJ45', 'NJ46', 'NJ50', 'NJ51', 'NJ52', 'NJ53', 'NJ54', 'NJ55', 'NJ56', 'NJ60', 'NJ61', 'NJ62', 'NJ63', 'NJ64', 'NJ65', 'NJ66', 'NJ70', 'NJ71', 'NJ72', 'NJ73', 'NJ74',
                           'NJ75', 'NJ76', 'NJ80', 'NJ81', 'NJ82', 'NJ83', 'NJ84', 'NJ85', 'NJ86', 'NJ90', 'NJ91', 'NJ92', 'NJ93', 'NJ94', 'NJ95', 'NJ96', 'NK02', 'NK03', 'NK04', 'NK05', 'NK06',
                           'NK13', 'NK14', 'NK15', 'NL57', 'NL58', 'NL68', 'NL69', 'NL79', 'NL84', 'NL93', 'NL94', 'NM04', 'NM05', 'NM14', 'NM15', 'NM16', 'NM19', 'NM21', 'NM22', 'NM23', 'NM24',
                           'NM25', 'NM26', 'NM29', 'NM31', 'NM32', 'NM33', 'NM34', 'NM35', 'NM37', 'NM38', 'NM39', 'NM40', 'NM41', 'NM42', 'NM43', 'NM44', 'NM45', 'NM46', 'NM47', 'NM48', 'NM49',
                           'NM51', 'NM52', 'NM53', 'NM54', 'NM55', 'NM56', 'NM57', 'NM59', 'NM60', 'NM61', 'NM62', 'NM63', 'NM64', 'NM65', 'NM66', 'NM67', 'NM68', 'NM69', 'NM70', 'NM71', 'NM72',
                           'NM73', 'NM74', 'NM75', 'NM76', 'NM77', 'NM78', 'NM79', 'NM80', 'NM81', 'NM82', 'NM83', 'NM84', 'NM85', 'NM86', 'NM87', 'NM88', 'NM89', 'NM90', 'NM91', 'NM92', 'NM93',
                           'NM94', 'NM95', 'NM96', 'NM97', 'NM98', 'NM99', 'NN00', 'NN01', 'NN02', 'NN03', 'NN04', 'NN05', 'NN06', 'NN07', 'NN08', 'NN09', 'NN10', 'NN11', 'NN12', 'NN13', 'NN14',
                           'NN15', 'NN16', 'NN17', 'NN18', 'NN19', 'NN20', 'NN21', 'NN22', 'NN23', 'NN24', 'NN25', 'NN26', 'NN27', 'NN28', 'NN29', 'NN30', 'NN31', 'NN32', 'NN33', 'NN34', 'NN35',
                           'NN36', 'NN37', 'NN38', 'NN39', 'NN40', 'NN41', 'NN42', 'NN43', 'NN44', 'NN45', 'NN46', 'NN47', 'NN48', 'NN49', 'NN50', 'NN51', 'NN52', 'NN53', 'NN54', 'NN55', 'NN56',
                           'NN57', 'NN58', 'NN59', 'NN60', 'NN61', 'NN62', 'NN63', 'NN64', 'NN65', 'NN66', 'NN67', 'NN68', 'NN69', 'NN70', 'NN71', 'NN72', 'NN73', 'NN74', 'NN75', 'NN76', 'NN77',
                           'NN78', 'NN79', 'NN80', 'NN81', 'NN82', 'NN83', 'NN84', 'NN85', 'NN86', 'NN87', 'NN88', 'NN89', 'NN90', 'NN91', 'NN92', 'NN93', 'NN94', 'NN95', 'NN96', 'NN97', 'NN98',
                           'NN99', 'NO00', 'NO01', 'NO02', 'NO03', 'NO04', 'NO05', 'NO06', 'NO07', 'NO08', 'NO09', 'NO10', 'NO11', 'NO12', 'NO13', 'NO14', 'NO15', 'NO16', 'NO17', 'NO18', 'NO19',
                           'NO20', 'NO21', 'NO22', 'NO23', 'NO24', 'NO25', 'NO26', 'NO27', 'NO28', 'NO29', 'NO30', 'NO31', 'NO32', 'NO33', 'NO34', 'NO35', 'NO36', 'NO37', 'NO38', 'NO39', 'NO40',
                           'NO41', 'NO42', 'NO43', 'NO44', 'NO45', 'NO46', 'NO47', 'NO48', 'NO49', 'NO50', 'NO51', 'NO52', 'NO53', 'NO54', 'NO55', 'NO56', 'NO57', 'NO58', 'NO59', 'NO60', 'NO61',
                           'NO63', 'NO64', 'NO65', 'NO66', 'NO67', 'NO68', 'NO69', 'NO74', 'NO75', 'NO76', 'NO77', 'NO78', 'NO79', 'NO86', 'NO87', 'NO88', 'NO89', 'NO99', 'NR15', 'NR16', 'NR24',
                           'NR25', 'NR26', 'NR27', 'NR33', 'NR34', 'NR35', 'NR36', 'NR37', 'NR38', 'NR39', 'NR44', 'NR45', 'NR46', 'NR47', 'NR48', 'NR49', 'NR50', 'NR51', 'NR56', 'NR57', 'NR58',
                           'NR59', 'NR60', 'NR61', 'NR62', 'NR63', 'NR64', 'NR65', 'NR67', 'NR68', 'NR69', 'NR70', 'NR71', 'NR72', 'NR73', 'NR74', 'NR75', 'NR76', 'NR77', 'NR78', 'NR79', 'NR82',
                           'NR83', 'NR84', 'NR85', 'NR86', 'NR87', 'NR88', 'NR89', 'NR91', 'NR92', 'NR93', 'NR94', 'NR95', 'NR96', 'NR97', 'NR98', 'NR99', 'NS00', 'NS01', 'NS02', 'NS03', 'NS04',
                           'NS05', 'NS06', 'NS07', 'NS08', 'NS09', 'NS10', 'NS14', 'NS15', 'NS16', 'NS17', 'NS18', 'NS19', 'NS20', 'NS21', 'NS22', 'NS23', 'NS24', 'NS25', 'NS26', 'NS27', 'NS28',
                           'NS29', 'NS30', 'NS31', 'NS32', 'NS33', 'NS34', 'NS35', 'NS36', 'NS37', 'NS38', 'NS39', 'NS40', 'NS41', 'NS42', 'NS43', 'NS44', 'NS45', 'NS46', 'NS47', 'NS48', 'NS49',
                           'NS50', 'NS51', 'NS52', 'NS53', 'NS54', 'NS55', 'NS56', 'NS57', 'NS58', 'NS59', 'NS60', 'NS61', 'NS62', 'NS63', 'NS64', 'NS65', 'NS66', 'NS67', 'NS68', 'NS69', 'NS70',
                           'NS71', 'NS72', 'NS73', 'NS74', 'NS75', 'NS76', 'NS77', 'NS78', 'NS79', 'NS80', 'NS81', 'NS82', 'NS83', 'NS84', 'NS85', 'NS86', 'NS87', 'NS88', 'NS89', 'NS90', 'NS91',
                           'NS92', 'NS93', 'NS94', 'NS95', 'NS96', 'NS97', 'NS98', 'NS99', 'NT00', 'NT01', 'NT02', 'NT03', 'NT04', 'NT05', 'NT06', 'NT07', 'NT08', 'NT09', 'NT10', 'NT11', 'NT12',
                           'NT13', 'NT14', 'NT15', 'NT16', 'NT17', 'NT18', 'NT19', 'NT20', 'NT21', 'NT22', 'NT23', 'NT24', 'NT25', 'NT26', 'NT27', 'NT28', 'NT29', 'NT30', 'NT31', 'NT32', 'NT33',
                           'NT34', 'NT35', 'NT36', 'NT37', 'NT38', 'NT39', 'NT40', 'NT41', 'NT42', 'NT43', 'NT44', 'NT45', 'NT46', 'NT47', 'NT48', 'NT49', 'NT50', 'NT51', 'NT52', 'NT53', 'NT54',
                           'NT55', 'NT56', 'NT57', 'NT58', 'NT59', 'NT60', 'NT61', 'NT62', 'NT63', 'NT64', 'NT65', 'NT66', 'NT67', 'NT68', 'NT69', 'NT70', 'NT71', 'NT72', 'NT73', 'NT74', 'NT75',
                           'NT76', 'NT77', 'NT80', 'NT81', 'NT82', 'NT83', 'NT84', 'NT85', 'NT86', 'NT87', 'NT90', 'NT91', 'NT92', 'NT93', 'NT94', 'NT95', 'NT96', 'NU00', 'NU01', 'NU02', 'NU03',
                           'NU04', 'NU05', 'NU10', 'NU11', 'NU12', 'NU13', 'NU14', 'NU20', 'NU21', 'NU22', 'NU23', 'NW95', 'NW96', 'NW97', 'NX03', 'NX04', 'NX05', 'NX06', 'NX07', 'NX08', 'NX09',
                           'NX12', 'NX13', 'NX14', 'NX15', 'NX16', 'NX17', 'NX18', 'NX19', 'NX23', 'NX24', 'NX25', 'NX26', 'NX27', 'NX28', 'NX29', 'NX30', 'NX33', 'NX34', 'NX35', 'NX36', 'NX37',
                           'NX38', 'NX39', 'NX40', 'NX43', 'NX44', 'NX45', 'NX46', 'NX47', 'NX48', 'NX49', 'NX54', 'NX55', 'NX56', 'NX57', 'NX58', 'NX59', 'NX64', 'NX65', 'NX66', 'NX67', 'NX68',
                           'NX69', 'NX74', 'NX75', 'NX76', 'NX77', 'NX78', 'NX79', 'NX84', 'NX85', 'NX86', 'NX87', 'NX88', 'NX89', 'NX90', 'NX91', 'NX92', 'NX93', 'NX94', 'NX95', 'NX96', 'NX97',
                           'NX98', 'NX99', 'NY00', 'NY01', 'NY02', 'NY03', 'NY04', 'NY05', 'NY06', 'NY07', 'NY08', 'NY09', 'NY10', 'NY11', 'NY12', 'NY13', 'NY14', 'NY15', 'NY16', 'NY17', 'NY18',
                           'NY19', 'NY20', 'NY21', 'NY22', 'NY23', 'NY24', 'NY25', 'NY26', 'NY27', 'NY28', 'NY29', 'NY30', 'NY31', 'NY32', 'NY33', 'NY34', 'NY35', 'NY36', 'NY37', 'NY38', 'NY39',
                           'NY40', 'NY41', 'NY42', 'NY43', 'NY44', 'NY45', 'NY46', 'NY47', 'NY48', 'NY49', 'NY50', 'NY51', 'NY52', 'NY53', 'NY54', 'NY55', 'NY56', 'NY57', 'NY58', 'NY59', 'NY60',
                           'NY61', 'NY62', 'NY63', 'NY64', 'NY65', 'NY66', 'NY67', 'NY68', 'NY69', 'NY70', 'NY71', 'NY72', 'NY73', 'NY74', 'NY75', 'NY76', 'NY77', 'NY78', 'NY79', 'NY80', 'NY81',
                           'NY82', 'NY83', 'NY84', 'NY85', 'NY86', 'NY87', 'NY88', 'NY89', 'NY90', 'NY91', 'NY92', 'NY93', 'NY94', 'NY95', 'NY96', 'NY97', 'NY98', 'NY99', 'NZ00', 'NZ01', 'NZ02',
                           'NZ03', 'NZ04', 'NZ05', 'NZ06', 'NZ07', 'NZ08', 'NZ09', 'NZ10', 'NZ11', 'NZ12', 'NZ13', 'NZ14', 'NZ15', 'NZ16', 'NZ17', 'NZ18', 'NZ19', 'NZ20', 'NZ21', 'NZ22', 'NZ23',
                           'NZ24', 'NZ25', 'NZ26', 'NZ27', 'NZ28', 'NZ29', 'NZ30', 'NZ31', 'NZ32', 'NZ33', 'NZ34', 'NZ35', 'NZ36', 'NZ37', 'NZ38', 'NZ39', 'NZ40', 'NZ41', 'NZ42', 'NZ43', 'NZ44',
                           'NZ45', 'NZ46', 'NZ50', 'NZ51', 'NZ52', 'NZ53', 'NZ60', 'NZ61', 'NZ62', 'NZ70', 'NZ71', 'NZ72', 'NZ80', 'NZ81', 'NZ90', 'NZ91', 'OV00', 'SC16', 'SC17', 'SC26', 'SC27',
                           'SC28', 'SC36', 'SC37', 'SC38', 'SC39', 'SC47', 'SC48', 'SC49', 'SD08', 'SD09', 'SD16', 'SD17', 'SD18', 'SD19', 'SD20', 'SD21', 'SD22', 'SD23', 'SD24', 'SD25', 'SD26',
                           'SD27', 'SD28', 'SD29', 'SD30', 'SD31', 'SD32', 'SD33', 'SD34', 'SD35', 'SD36', 'SD37', 'SD38', 'SD39', 'SD40', 'SD41', 'SD42', 'SD43', 'SD44', 'SD45', 'SD46', 'SD47',
                           'SD48', 'SD49', 'SD50', 'SD51', 'SD52', 'SD53', 'SD54', 'SD55', 'SD56', 'SD57', 'SD58', 'SD59', 'SD60', 'SD61', 'SD62', 'SD63', 'SD64', 'SD65', 'SD66', 'SD67', 'SD68',
                           'SD69', 'SD70', 'SD71', 'SD72', 'SD73', 'SD74', 'SD75', 'SD76', 'SD77', 'SD78', 'SD79', 'SD80', 'SD81', 'SD82', 'SD83', 'SD84', 'SD85', 'SD86', 'SD87', 'SD88', 'SD89',
                           'SD90', 'SD91', 'SD92', 'SD93', 'SD94', 'SD95', 'SD96', 'SD97', 'SD98', 'SD99', 'SE00', 'SE01', 'SE02', 'SE03', 'SE04', 'SE05', 'SE06', 'SE07', 'SE08', 'SE09', 'SE10',
                           'SE11', 'SE12', 'SE13', 'SE14', 'SE15', 'SE16', 'SE17', 'SE18', 'SE19', 'SE20', 'SE21', 'SE22', 'SE23', 'SE24', 'SE25', 'SE26', 'SE27', 'SE28', 'SE29', 'SE30', 'SE31',
                           'SE32', 'SE33', 'SE34', 'SE35', 'SE36', 'SE37', 'SE38', 'SE39', 'SE40', 'SE41', 'SE42', 'SE43', 'SE44', 'SE45', 'SE46', 'SE47', 'SE48', 'SE49', 'SE50', 'SE51', 'SE52',
                           'SE53', 'SE54', 'SE55', 'SE56', 'SE57', 'SE58', 'SE59', 'SE60', 'SE61', 'SE62', 'SE63', 'SE64', 'SE65', 'SE66', 'SE67', 'SE68', 'SE69', 'SE70', 'SE71', 'SE72', 'SE73',
                           'SE74', 'SE75', 'SE76', 'SE77', 'SE78', 'SE79', 'SE80', 'SE81', 'SE82', 'SE83', 'SE84', 'SE85', 'SE86', 'SE87', 'SE88', 'SE89', 'SE90', 'SE91', 'SE92', 'SE93', 'SE94',
                           'SE95', 'SE96', 'SE97', 'SE98', 'SE99', 'SH12', 'SH13', 'SH22', 'SH23', 'SH24', 'SH27', 'SH28', 'SH29', 'SH32', 'SH33', 'SH34', 'SH36', 'SH37', 'SH38', 'SH39', 'SH43',
                           'SH44', 'SH45', 'SH46', 'SH47', 'SH48', 'SH49', 'SH50', 'SH51', 'SH52', 'SH53', 'SH54', 'SH55', 'SH56', 'SH57', 'SH58', 'SH59', 'SH60', 'SH61', 'SH62', 'SH63', 'SH64',
                           'SH65', 'SH66', 'SH67', 'SH68', 'SH70', 'SH71', 'SH72', 'SH73', 'SH74', 'SH75', 'SH76', 'SH77', 'SH78', 'SH80', 'SH81', 'SH82', 'SH83', 'SH84', 'SH85', 'SH86', 'SH87',
                           'SH88', 'SH90', 'SH91', 'SH92', 'SH93', 'SH94', 'SH95', 'SH96', 'SH97', 'SH98', 'SJ00', 'SJ01', 'SJ02', 'SJ03', 'SJ04', 'SJ05', 'SJ06', 'SJ07', 'SJ08', 'SJ10', 'SJ11',
                           'SJ12', 'SJ13', 'SJ14', 'SJ15', 'SJ16', 'SJ17', 'SJ18', 'SJ19', 'SJ20', 'SJ21', 'SJ22', 'SJ23', 'SJ24', 'SJ25', 'SJ26', 'SJ27', 'SJ28', 'SJ29', 'SJ30', 'SJ31', 'SJ32',
                           'SJ33', 'SJ34', 'SJ35', 'SJ36', 'SJ37', 'SJ38', 'SJ39', 'SJ40', 'SJ41', 'SJ42', 'SJ43', 'SJ44', 'SJ45', 'SJ46', 'SJ47', 'SJ48', 'SJ49', 'SJ50', 'SJ51', 'SJ52', 'SJ53',
                           'SJ54', 'SJ55', 'SJ56', 'SJ57', 'SJ58', 'SJ59', 'SJ60', 'SJ61', 'SJ62', 'SJ63', 'SJ64', 'SJ65', 'SJ66', 'SJ67', 'SJ68', 'SJ69', 'SJ70', 'SJ71', 'SJ72', 'SJ73', 'SJ74',
                           'SJ75', 'SJ76', 'SJ77', 'SJ78', 'SJ79', 'SJ80', 'SJ81', 'SJ82', 'SJ83', 'SJ84', 'SJ85', 'SJ86', 'SJ87', 'SJ88', 'SJ89', 'SJ90', 'SJ91', 'SJ92', 'SJ93', 'SJ94', 'SJ95',
                           'SJ96', 'SJ97', 'SJ98', 'SJ99', 'SK00', 'SK01', 'SK02', 'SK03', 'SK04', 'SK05', 'SK06', 'SK07', 'SK08', 'SK09', 'SK10', 'SK11', 'SK12', 'SK13', 'SK14', 'SK15', 'SK16',
                           'SK17', 'SK18', 'SK19', 'SK20', 'SK21', 'SK22', 'SK23', 'SK24', 'SK25', 'SK26', 'SK27', 'SK28', 'SK29', 'SK30', 'SK31', 'SK32', 'SK33', 'SK34', 'SK35', 'SK36', 'SK37',
                           'SK38', 'SK39', 'SK40', 'SK41', 'SK42', 'SK43', 'SK44', 'SK45', 'SK46', 'SK47', 'SK48', 'SK49', 'SK50', 'SK51', 'SK52', 'SK53', 'SK54', 'SK55', 'SK56', 'SK57', 'SK58',
                           'SK59', 'SK60', 'SK61', 'SK62', 'SK63', 'SK64', 'SK65', 'SK66', 'SK67', 'SK68', 'SK69', 'SK70', 'SK71', 'SK72', 'SK73', 'SK74', 'SK75', 'SK76', 'SK77', 'SK78', 'SK79',
                           'SK80', 'SK81', 'SK82', 'SK83', 'SK84', 'SK85', 'SK86', 'SK87', 'SK88', 'SK89', 'SK90', 'SK91', 'SK92', 'SK93', 'SK94', 'SK95', 'SK96', 'SK97', 'SK98', 'SK99', 'SM40',
                           'SM50', 'SM60', 'SM62', 'SM70', 'SM71', 'SM72', 'SM73', 'SM80', 'SM81', 'SM82', 'SM83', 'SM84', 'SM90', 'SM91', 'SM92', 'SM93', 'SM94', 'SN00', 'SN01', 'SN02', 'SN03',
                           'SN04', 'SN10', 'SN11', 'SN12', 'SN13', 'SN14', 'SN15', 'SN20', 'SN21', 'SN22', 'SN23', 'SN24', 'SN25', 'SN30', 'SN31', 'SN32', 'SN33', 'SN34', 'SN35', 'SN36', 'SN40',
                           'SN41', 'SN42', 'SN43', 'SN44', 'SN45', 'SN46', 'SN50', 'SN51', 'SN52', 'SN53', 'SN54', 'SN55', 'SN56', 'SN57', 'SN58', 'SN59', 'SN60', 'SN61', 'SN62', 'SN63', 'SN64',
                           'SN65', 'SN66', 'SN67', 'SN68', 'SN69', 'SN70', 'SN71', 'SN72', 'SN73', 'SN74', 'SN75', 'SN76', 'SN77', 'SN78', 'SN79', 'SN80', 'SN81', 'SN82', 'SN83', 'SN84', 'SN85',
                           'SN86', 'SN87', 'SN88', 'SN89', 'SN90', 'SN91', 'SN92', 'SN93', 'SN94', 'SN95', 'SN96', 'SN97', 'SN98', 'SN99', 'SO00', 'SO01', 'SO02', 'SO03', 'SO04', 'SO05', 'SO06',
                           'SO07', 'SO08', 'SO09', 'SO10', 'SO11', 'SO12', 'SO13', 'SO14', 'SO15', 'SO16', 'SO17', 'SO18', 'SO19', 'SO20', 'SO21', 'SO22', 'SO23', 'SO24', 'SO25', 'SO26', 'SO27',
                           'SO28', 'SO29', 'SO30', 'SO31', 'SO32', 'SO33', 'SO34', 'SO35', 'SO36', 'SO37', 'SO38', 'SO39', 'SO40', 'SO41', 'SO42', 'SO43', 'SO44', 'SO45', 'SO46', 'SO47', 'SO48',
                           'SO49', 'SO50', 'SO51', 'SO52', 'SO53', 'SO54', 'SO55', 'SO56', 'SO57', 'SO58', 'SO59', 'SO60', 'SO61', 'SO62', 'SO63', 'SO64', 'SO65', 'SO66', 'SO67', 'SO68', 'SO69',
                           'SO70', 'SO71', 'SO72', 'SO73', 'SO74', 'SO75', 'SO76', 'SO77', 'SO78', 'SO79', 'SO80', 'SO81', 'SO82', 'SO83', 'SO84', 'SO85', 'SO86', 'SO87', 'SO88', 'SO89', 'SO90',
                           'SO91', 'SO92', 'SO93', 'SO94', 'SO95', 'SO96', 'SO97', 'SO98', 'SO99', 'SP00', 'SP01', 'SP02', 'SP03', 'SP04', 'SP05', 'SP06', 'SP07', 'SP08', 'SP09', 'SP10', 'SP11',
                           'SP12', 'SP13', 'SP14', 'SP15', 'SP16', 'SP17', 'SP18', 'SP19', 'SP20', 'SP21', 'SP22', 'SP23', 'SP24', 'SP25', 'SP26', 'SP27', 'SP28', 'SP29', 'SP30', 'SP31', 'SP32',
                           'SP33', 'SP34', 'SP35', 'SP36', 'SP37', 'SP38', 'SP39', 'SP40', 'SP41', 'SP42', 'SP43', 'SP44', 'SP45', 'SP46', 'SP47', 'SP48', 'SP49', 'SP50', 'SP51', 'SP52', 'SP53',
                           'SP54', 'SP55', 'SP56', 'SP57', 'SP58', 'SP59', 'SP60', 'SP61', 'SP62', 'SP63', 'SP64', 'SP65', 'SP66', 'SP67', 'SP68', 'SP69', 'SP70', 'SP71', 'SP72', 'SP73', 'SP74',
                           'SP75', 'SP76', 'SP77', 'SP78', 'SP79', 'SP80', 'SP81', 'SP82', 'SP83', 'SP84', 'SP85', 'SP86', 'SP87', 'SP88', 'SP89', 'SP90', 'SP91', 'SP92', 'SP93', 'SP94', 'SP95',
                           'SP96', 'SP97', 'SP98', 'SP99', 'SR89', 'SR99', 'SS09', 'SS10', 'SS11', 'SS14', 'SS19', 'SS20', 'SS21', 'SS22', 'SS30', 'SS31', 'SS32', 'SS38', 'SS39', 'SS40', 'SS41',
                           'SS42', 'SS43', 'SS44', 'SS48', 'SS49', 'SS50', 'SS51', 'SS52', 'SS53', 'SS54', 'SS58', 'SS59', 'SS60', 'SS61', 'SS62', 'SS63', 'SS64', 'SS68', 'SS69', 'SS70', 'SS71',
                           'SS72', 'SS73', 'SS74', 'SS75', 'SS77', 'SS78', 'SS79', 'SS80', 'SS81', 'SS82', 'SS83', 'SS84', 'SS87', 'SS88', 'SS89', 'SS90', 'SS91', 'SS92', 'SS93', 'SS94', 'SS96',
                           'SS97', 'SS98', 'SS99', 'ST00', 'ST01', 'ST02', 'ST03', 'ST04', 'ST06', 'ST07', 'ST08', 'ST09', 'ST10', 'ST11', 'ST12', 'ST13', 'ST14', 'ST16', 'ST17', 'ST18', 'ST19',
                           'ST20', 'ST21', 'ST22', 'ST23', 'ST24', 'ST25', 'ST26', 'ST27', 'ST28', 'ST29', 'ST30', 'ST31', 'ST32', 'ST33', 'ST34', 'ST35', 'ST36', 'ST37', 'ST38', 'ST39', 'ST40',
                           'ST41', 'ST42', 'ST43', 'ST44', 'ST45', 'ST46', 'ST47', 'ST48', 'ST49', 'ST50', 'ST51', 'ST52', 'ST53', 'ST54', 'ST55', 'ST56', 'ST57', 'ST58', 'ST59', 'ST60', 'ST61',
                           'ST62', 'ST63', 'ST64', 'ST65', 'ST66', 'ST67', 'ST68', 'ST69', 'ST70', 'ST71', 'ST72', 'ST73', 'ST74', 'ST75', 'ST76', 'ST77', 'ST78', 'ST79', 'ST80', 'ST81', 'ST82',
                           'ST83', 'ST84', 'ST85', 'ST86', 'ST87', 'ST88', 'ST89', 'ST90', 'ST91', 'ST92', 'ST93', 'ST94', 'ST95', 'ST96', 'ST97', 'ST98', 'ST99', 'SU00', 'SU01', 'SU02', 'SU03',
                           'SU04', 'SU05', 'SU06', 'SU07', 'SU08', 'SU09', 'SU10', 'SU11', 'SU12', 'SU13', 'SU14', 'SU15', 'SU16', 'SU17', 'SU18', 'SU19', 'SU20', 'SU21', 'SU22', 'SU23', 'SU24',
                           'SU25', 'SU26', 'SU27', 'SU28', 'SU29', 'SU30', 'SU31', 'SU32', 'SU33', 'SU34', 'SU35', 'SU36', 'SU37', 'SU38', 'SU39', 'SU40', 'SU41', 'SU42', 'SU43', 'SU44', 'SU45',
                           'SU46', 'SU47', 'SU48', 'SU49', 'SU50', 'SU51', 'SU52', 'SU53', 'SU54', 'SU55', 'SU56', 'SU57', 'SU58', 'SU59', 'SU60', 'SU61', 'SU62', 'SU63', 'SU64', 'SU65', 'SU66',
                           'SU67', 'SU68', 'SU69', 'SU70', 'SU71', 'SU72', 'SU73', 'SU74', 'SU75', 'SU76', 'SU77', 'SU78', 'SU79', 'SU80', 'SU81', 'SU82', 'SU83', 'SU84', 'SU85', 'SU86', 'SU87',
                           'SU88', 'SU89', 'SU90', 'SU91', 'SU92', 'SU93', 'SU94', 'SU95', 'SU96', 'SU97', 'SU98', 'SU99', 'SV80', 'SV81', 'SV90', 'SV91', 'SW21', 'SW32', 'SW33', 'SW42', 'SW43',
                           'SW44', 'SW52', 'SW53', 'SW54', 'SW61', 'SW62', 'SW63', 'SW64', 'SW65', 'SW71', 'SW72', 'SW73', 'SW74', 'SW75', 'SW76', 'SW81', 'SW82', 'SW83', 'SW84', 'SW85', 'SW86',
                           'SW87', 'SW93', 'SW94', 'SW95', 'SW96', 'SW97', 'SW98', 'SX03', 'SX04', 'SX05', 'SX06', 'SX07', 'SX08', 'SX09', 'SX14', 'SX15', 'SX16', 'SX17', 'SX18', 'SX19', 'SX25',
                           'SX26', 'SX27', 'SX28', 'SX29', 'SX33', 'SX35', 'SX36', 'SX37', 'SX38', 'SX39', 'SX44', 'SX45', 'SX46', 'SX47', 'SX48', 'SX49', 'SX54', 'SX55', 'SX56', 'SX57', 'SX58',
                           'SX59', 'SX63', 'SX64', 'SX65', 'SX66', 'SX67', 'SX68', 'SX69', 'SX73', 'SX74', 'SX75', 'SX76', 'SX77', 'SX78', 'SX79', 'SX83', 'SX84', 'SX85', 'SX86', 'SX87', 'SX88',
                           'SX89', 'SX94', 'SX95', 'SX96', 'SX97', 'SX98', 'SX99', 'SY07', 'SY08', 'SY09', 'SY18', 'SY19', 'SY28', 'SY29', 'SY38', 'SY39', 'SY48', 'SY49', 'SY58', 'SY59', 'SY66',
                           'SY67', 'SY68', 'SY69', 'SY77', 'SY78', 'SY79', 'SY87', 'SY88', 'SY89', 'SY97', 'SY98', 'SY99', 'SZ07', 'SZ08', 'SZ09', 'SZ19', 'SZ28', 'SZ29', 'SZ38', 'SZ39', 'SZ47',
                           'SZ48', 'SZ49', 'SZ57', 'SZ58', 'SZ59', 'SZ68', 'SZ69', 'SZ79', 'SZ89', 'SZ99', 'TA00', 'TA01', 'TA02', 'TA03', 'TA04', 'TA05', 'TA06', 'TA07', 'TA08', 'TA09', 'TA10',
                           'TA11', 'TA12', 'TA13', 'TA14', 'TA15', 'TA16', 'TA17', 'TA18', 'TA20', 'TA21', 'TA22', 'TA23', 'TA24', 'TA25', 'TA26', 'TA27', 'TA30', 'TA31', 'TA32', 'TA33', 'TA40',
                           'TA41', 'TA42', 'TF00', 'TF01', 'TF02', 'TF03', 'TF04', 'TF05', 'TF06', 'TF07', 'TF08', 'TF09', 'TF10', 'TF11', 'TF12', 'TF13', 'TF14', 'TF15', 'TF16', 'TF17', 'TF18',
                           'TF19', 'TF20', 'TF21', 'TF22', 'TF23', 'TF24', 'TF25', 'TF26', 'TF27', 'TF28', 'TF29', 'TF30', 'TF31', 'TF32', 'TF33', 'TF34', 'TF35', 'TF36', 'TF37', 'TF38', 'TF39',
                           'TF40', 'TF41', 'TF42', 'TF43', 'TF44', 'TF45', 'TF46', 'TF47', 'TF48', 'TF49', 'TF50', 'TF51', 'TF52', 'TF53', 'TF54', 'TF55', 'TF56', 'TF57', 'TF58', 'TF60', 'TF61',
                           'TF62', 'TF63', 'TF64', 'TF65', 'TF70', 'TF71', 'TF72', 'TF73', 'TF74', 'TF80', 'TF81', 'TF82', 'TF83', 'TF84', 'TF90', 'TF91', 'TF92', 'TF93', 'TF94', 'TG00', 'TG01',
                           'TG02', 'TG03', 'TG04', 'TG10', 'TG11', 'TG12', 'TG13', 'TG14', 'TG20', 'TG21', 'TG22', 'TG23', 'TG24', 'TG30', 'TG31', 'TG32', 'TG33', 'TG40', 'TG41', 'TG42', 'TG50',
                           'TG51', 'TL00', 'TL01', 'TL02', 'TL03', 'TL04', 'TL05', 'TL06', 'TL07', 'TL08', 'TL09', 'TL10', 'TL11', 'TL12', 'TL13', 'TL14', 'TL15', 'TL16', 'TL17', 'TL18', 'TL19',
                           'TL20', 'TL21', 'TL22', 'TL23', 'TL24', 'TL25', 'TL26', 'TL27', 'TL28', 'TL29', 'TL30', 'TL31', 'TL32', 'TL33', 'TL34', 'TL35', 'TL36', 'TL37', 'TL38', 'TL39', 'TL40',
                           'TL41', 'TL42', 'TL43', 'TL44', 'TL45', 'TL46', 'TL47', 'TL48', 'TL49', 'TL50', 'TL51', 'TL52', 'TL53', 'TL54', 'TL55', 'TL56', 'TL57', 'TL58', 'TL59', 'TL60', 'TL61',
                           'TL62', 'TL63', 'TL64', 'TL65', 'TL66', 'TL67', 'TL68', 'TL69', 'TL70', 'TL71', 'TL72', 'TL73', 'TL74', 'TL75', 'TL76', 'TL77', 'TL78', 'TL79', 'TL80', 'TL81', 'TL82',
                           'TL83', 'TL84', 'TL85', 'TL86', 'TL87', 'TL88', 'TL89', 'TL90', 'TL91', 'TL92', 'TL93', 'TL94', 'TL95', 'TL96', 'TL97', 'TL98', 'TL99', 'TM00', 'TM01', 'TM02', 'TM03',
                           'TM04', 'TM05', 'TM06', 'TM07', 'TM08', 'TM09', 'TM10', 'TM11', 'TM12', 'TM13', 'TM14', 'TM15', 'TM16', 'TM17', 'TM18', 'TM19', 'TM21', 'TM22', 'TM23', 'TM24', 'TM25',
                           'TM26', 'TM27', 'TM28', 'TM29', 'TM31', 'TM32', 'TM33', 'TM34', 'TM35', 'TM36', 'TM37', 'TM38', 'TM39', 'TM44', 'TM45', 'TM46', 'TM47', 'TM48', 'TM49', 'TM57', 'TM58',
                           'TM59', 'TQ00', 'TQ01', 'TQ02', 'TQ03', 'TQ04', 'TQ05', 'TQ06', 'TQ07', 'TQ08', 'TQ09', 'TQ10', 'TQ11', 'TQ12', 'TQ13', 'TQ14', 'TQ15', 'TQ16', 'TQ17', 'TQ18', 'TQ19',
                           'TQ20', 'TQ21', 'TQ22', 'TQ23', 'TQ24', 'TQ25', 'TQ26', 'TQ27', 'TQ28', 'TQ29', 'TQ30', 'TQ31', 'TQ32', 'TQ33', 'TQ34', 'TQ35', 'TQ36', 'TQ37', 'TQ38', 'TQ39', 'TQ40',
                           'TQ41', 'TQ42', 'TQ43', 'TQ44', 'TQ45', 'TQ46', 'TQ47', 'TQ48', 'TQ49', 'TQ50', 'TQ51', 'TQ52', 'TQ53', 'TQ54', 'TQ55', 'TQ56', 'TQ57', 'TQ58', 'TQ59', 'TQ60', 'TQ61',
                           'TQ62', 'TQ63', 'TQ64', 'TQ65', 'TQ66', 'TQ67', 'TQ68', 'TQ69', 'TQ70', 'TQ71', 'TQ72', 'TQ73', 'TQ74', 'TQ75', 'TQ76', 'TQ77', 'TQ78', 'TQ79', 'TQ80', 'TQ81', 'TQ82',
                           'TQ83', 'TQ84', 'TQ85', 'TQ86', 'TQ87', 'TQ88', 'TQ89', 'TQ91', 'TQ92', 'TQ93', 'TQ94', 'TQ95', 'TQ96', 'TQ97', 'TQ98', 'TQ99', 'TR01', 'TR02', 'TR03', 'TR04', 'TR05',
                           'TR06', 'TR07', 'TR08', 'TR09', 'TR12', 'TR13', 'TR14', 'TR15', 'TR16', 'TR17', 'TR19', 'TR23', 'TR24', 'TR25', 'TR26', 'TR27', 'TR33', 'TR34', 'TR35', 'TR36', 'TR37',
                           'TR46', 'TR47', 'TV49', 'TV59', 'TV69', 'HX51']

    TILES_100KM_WALES = [s[0:2] for s in TILES_10KM_WALES]
    TILES_100KM_ENGLAND = [s[0:2] for s in TILES_10KM_ENGLAND]
    TILES_100KM_SCOTLAND = [s[0:2] for s in TILES_10KM_SCOTLAND]

    _BNG_100KM_GRID_DICT = {
        'tile': TILES_100km,
        'origin_easting': [400000, 300000, 400000, 100000, 200000, 300000, 400000, 0, 100000, 200000, 300000, 0, 100000, 200000, 300000, 400000, 0, 100000, 200000, 300000, 100000, 200000, 300000,
                           400000, 100000, 200000, 300000, 400000, 500000, 200000, 300000, 400000, 200000, 300000, 400000, 100000, 200000, 300000, 400000, 100000, 200000, 300000, 400000, 0, 100000,
                           200000, 300000, 400000, 500000, 500000, 600000, 500000, 600000, 500000, 600000, 500000],
        'origin_northing': [1200000, 1100000, 1100000, 1000000, 1000000, 1000000, 1000000, 900000, 900000, 900000, 900000, 800000, 800000, 800000, 800000, 800000, 700000, 700000, 700000, 700000,
                            600000, 600000, 600000, 600000, 500000, 500000, 500000, 500000, 500000, 400000, 400000, 400000, 300000, 300000, 300000, 200000, 200000, 200000, 200000, 100000, 100000,
                            100000, 100000, 0, 0, 0, 0, 0, 400000, 300000, 300000, 200000, 200000, 100000, 100000, 0]}

    @_classproperty  # noqa
    def tiles_wales_land(cls) -> list[str]:  # noqa
        """
        Get tiles intersecting wales land (excludes all sea intersecting Welsh waters.

        Returns:
            list[str]: a list of the two letter tiles that intersect wales
        """
        return ['SH', 'SJ', 'SM', 'SN', 'SO', 'SR', 'SS', 'ST']

    @staticmethod
    def tile_get(e: (int, float), n: (int, float)) -> str:
        #  See https://oobrien.com/2010/02/en-to-gridref-in-python/
        """
        Get 100km OS grid tile from easting and northing

        Args:
            e (int, float): Easting
            n (int, float): Northing

        Returns:
            str: The tile in which the point defined by e,n lies.

        Examples:
            >>> BNG100kmGrid.tile_get(204459, 204863)
            'SJ'
        """

        # Correct that there is no I
        gridChars = "ABCDEFGHJKLMNOPQRSTUVWXYZ"

        # get the 100km-grid indices
        e100k = _math.floor(e / 100000)
        n100k = _math.floor(n / 100000)

        # translate those into numeric equivalents of the grid letters
        l1 = (19 - n100k) - (19 - n100k) % 5 + _math.floor((e100k + 10) / 5)
        l2 = (19 - n100k) * 5 % 25 + e100k % 5

        # tile will look like 'SN'
        tile = gridChars[int(l1)] + gridChars[int(l2)]
        return tile

    @staticmethod
    def cell_part_get(v: (int, float), astype_: any = str) -> str:
        """
        Get the coordinate in the context of a 100km cell, where
        coordinate is an easting or northing.

        Args:
            v (int, float): An easting or a northing
            astype_ (object): A conversion function, eg str, float etc.

        Returns:
            (str): The coordinate as a string, in the context of the cell

        Examples:
            >>> BNG100kmGrid.cell_part_get(204459)
            '04459'
        """
        out = str(v).rjust(6, "0")[1:]
        return astype_(out)  # noqa

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

    class eBNGGrid(_Enum):
        KM_100by100 = 99
        KM_10by10 = 2
        KM_1by1 = 4
        M_100by100 = 6
        M_10by10 = 8
        M_1by1 = 10
        NoTruncation = 0

    @staticmethod
    def grid_to_bng(grid_ref: str, centroid: bool = False) -> tuple[(int, float)]:
        """
        Convert OS Grids to British National Grid eastings and northings (tuple returns values in that order).

        This gets the grid origin by default

        Args:
            grid_ref (str): The grid ref, spaces allowed. e.g. SN123456, SN 123 456, SN1234567890 are all valid.
            centroid (bool): Get the grid centroid, rather than the origin

        Returns:
            tuple[int]: Point as easting, northing if grid size >= 1m by 1m (i.e. len(grid_ref) <= 12) and we dont want the centroid
            tuple[float]: Point as easting, northing if grid size < 1m by 1m (i.e. len(grid_ref) > 12) or if we are asking for centroid of a 1m box

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
            # ALthough 10 digits is a square of 1m by 1m, the centroid will ofcourse be 0.5 meters from the origin
            return int(xx) if len(grid_ref) <= 10 else float(xx), int(yy) if len(grid_ref) <= 10 else float(yy)  # noqa

        # Dont want the centroid, a 1m by 1m origin is an integer
        return int(xx) if len(grid_ref) <= 12 else float(xx), int(yy) if len(grid_ref) <= 12 else float(yy)  # noqa

    @staticmethod
    def bng_to_grid(e: (int, float), n: (int, float)) -> str:
        """
        Return an OS grid reference from an easting and northing (OSGB36 projection).

        If the e and n in are fractional, then the out format is fractional friendly.

        Args:
            e (int, float): The easting
            n (int, float): The northing

        Returns:
            str: the grid reference

        Examples:
            >>> OSBNG.bng_to_grid(204459, 204863)
            'SN0445904863'

            With frational coords
            >>> OSBNG.bng_to_grid(204459.123, 204863.456)
            'SN 04459.123 04863.456'

        """
        tile = BNG100kmGrid.tile_get(e, n)

        easting = BNG100kmGrid.cell_part_get(e)

        # Fix Shetland northings
        if n >= 1000000:
            n = n - 1000000
        northing = BNG100kmGrid.cell_part_get(n)

        if _numerics.is_float(e, int_is_float=False) or _numerics.is_float(n, int_is_float=False):
            return '%s %s %s' % (tile, easting, northing)
        else:
            return '%s%s%s' % (tile, easting, northing)


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
    s_m = OSBNG.bng_to_grid(204459, 204863)
    # s_m = OSBNG.bng_to_grid(204459.123, 204863.456)
    print(s_m)
    pass
