"""
#-------------------------------------------------------------------------------
# Name:        arcapi_test
# Purpose:     Tests for arcapi module.
#
# Author:      Filip Kral, Caleb Mackay
#
# Created:     01/02/2014
# Updated:     05/15/2014
# Licence:     LGPL v3
#-------------------------------------------------------------------------------
# Most of the functions operate on potentially complex data, or require manual
# checking of results, and therefore testing is rather difficult.
#
# Everybody is encouraged to contribute to tests.
#-------------------------------------------------------------------------------
"""


import datetime as _datetime
import os
import os.path as _path
import sys
import unittest

import arcpy

import arcproapi.charts_stats as _charts_stats
import arcproapi.common as _common
import arcproapi.data as _data
import arcproapi.http as http
import arcproapi.meta as meta
from arcproapi.errors import ArcapiError, MapNotFound, MapFrameNotFound, LayoutNotFound # noqa


class TestGlobalFunctions(unittest.TestCase):

    def setUp(self):
        # access testing data
        try:
            self.testingfolder = _path.join(_path.dirname(_path.realpath(__file__)), 'testing')
        except:
            self.testingfolder = _path.join(_path.dirname(_path.realpath(sys.argv[0])), 'testing')
        self.testing_gdb = _path.join(self.testingfolder, 'testing.gdb')
        #self.t_table = _path.join(self.testing_gdb, '\left_i_right')
        #self.t_fc =  _path.join(self.testing_gdb, 'left_i_right')
        #self.t_cols = ('OBJECTID', 'Shape', 'CCARM2', 'POINT_X', u'POINT_Y', u'ROUND_X', 'ROUND_Y', 'name', 'propagatedName', 'fullName', 'GID', 'DOWNGID', 'HA_NUM','STRAHLER', 'SHREVE', 'OS_NAME', 'FNODE_FULL', 'TNODE_FULL', 'NAMENOXML', 'Shape_Length')
        self.t_fc =  _path.join(self.testing_gdb, 'ne_110m_admin_0_countries')
        self.t_fc2 = _path.join(self.testing_gdb, 'Illinois')
        self.t_tab = _path.join(self.testing_gdb, 'Illinois_county_info')
        self.t_cols =  ('OBJECTID','Shape','ScaleRank','LabelRank','FeatureCla',
                      'SOVEREIGNT','SOV_A3','ADM0_DIF','LEVEL','TYPE','ADMIN',
                      'ADM0_A3','GEOU_DIF','GEOUNIT','GU_A3','SU_DIF','SUBUNIT',
                      'SU_A3','NAME','ABBREV','POSTAL','NAME_FORMA','TERR_',
                      'NAME_SORT','MAP_COLOR','POP_EST','GDP_MD_EST','FIPS_10_',
                      'ISO_A2','ISO_A3','ISO_N3','Shape_Length','Shape_Area')
        pass

    def tearDown(self):
        pass

    def testnames(self):
        est = map(str, tuple(_common.names(self.t_fc)))
        obs = ('OBJECTID','Shape','ScaleRank','LabelRank','FeatureCla',
                'SOVEREIGNT','SOV_A3','ADM0_DIF','LEVEL','TYPE','ADMIN',
                'ADM0_A3','GEOU_DIF','GEOUNIT','GU_A3','SU_DIF','SUBUNIT',
                'SU_A3','NAME','ABBREV','POSTAL','NAME_FORMA','TERR_',
                'NAME_SORT','MAP_COLOR','POP_EST','GDP_MD_EST','FIPS_10_',
                'ISO_A2','ISO_A3','ISO_N3','Shape_Length','Shape_Area')
        self.assertEqual(tuple(est), obs)
        pass

    def testtypes(self):
        est = map(str, tuple(_common.types(self.t_fc)))
        obs = ('OID','Geometry','SmallInteger','SmallInteger','String','String',
                'String','Single','Single','String','String','String','Single',
                'String', 'String','Single','String','String','String','String',
                'String','String', 'String','String','Single','Double','Double',
                'Single','String','String', 'Single','Double','Double')
        pass

    def testnrow(self):
        est = _common.nrow(self.t_fc)
        obs = 177
        self.assertEqual(est, obs)
        pass

    def testvalues(self):

        fc = self.t_fc
        w = '"OBJECTID" < 11'

        vals1 = _data.field_values(fc, 'Shape_Length', w)
        vals2 = _data.field_values(fc, 'Shape_Length', w, 'Shape_Length ASC')
        vals3 = _data.field_values(fc, 'SHAPE@XY', w)
        vals4 = _data.field_values(fc, 'SHAPE@XY;Shape_Length', w, 'Shape_Length DESC')
        vals5 = _data.field_values(fc, 'OBJECTID')[0:10]
        est = all([len(vi) == 10 for vi in [vals1, vals2, vals3, vals4, vals5]])
        self.assertTrue(est)

    def testvalues_crosscolumns(self):
        # the values function requires columns included in the o parameter
        # to be included in the col parameter too, otherwise an invalid
        # sql statement is generated.
        fc = self.t_fc
        w = '"OBJECTID" < 11'
        with self.assertRaises(RuntimeError):
            vals = _data.field_values(fc, 'SHAPE@XY', w, 'Shape_Length ASC')
        pass


##    def testdistinct(self):
##        pass

    def testhead(self):
        est = 5
        hd = _common.head(self.t_fc, est, geoms = " ", verbose=False)
        obs = len(hd[0])
        self.assertEqual(est, obs)
        pass

    def testchart(self):
        obs = r'c:\temp\chart.jpg'
        t_fc = self.t_fc
        est = _charts_stats.chart(t_fc, obs, texts = {'txt': 'Element txt'}, openit=False)
        self.assertEqual(str(est).lower(), str(obs).lower())
        pass

    def testplot(self):
        pic = r'c:\temp\plot.png'
        x = range(20)
        _charts_stats.plot(x, out_file=pic, openit=False)
        y = range(50,70)
        _charts_stats.plot(x, y, pic, 'Main', 'X [m]', 'Y [m]', 'o', 'k', openit=False)
        os.remove(pic)
        with self.assertRaises(_common.ArcapiError):
            _charts_stats.plot(x, [1,2,3], pic, 'Main', 'X [m]', 'Y [m]', 'o', 'k', openit=False)
        pass

    def testhist(self):
        pic = r'c:\temp\plot.png'
        x = range(20)
        h = _charts_stats.hist(x, out_file=pic, openit=False)
        h = _charts_stats.hist(x, pic, main='Main', xlab='Xlbl', log=True, openit=False)
        os.remove(pic)
        self.assertFalse(_path.exists(pic))

    def testbars(self):
        pic = r'c:\temp\plot.png'
        x = range(20)
        _charts_stats.bars(x, out_file=pic, openit=False)
        y = range(50,70)
        _charts_stats.bars(x, out_file=pic, labels=y, main='Main', xlab='X', ylab='Y', openit=False)
        _charts_stats.bars([], openit=False)
        os.remove(pic)
        self.assertFalse(_path.exists(pic))

    def testpie(self):
        pic = r'c:\temp\plot.png'
        x = [1,2,3,4,5,6,7]
        y = [1,1,2,2,3,3,3]
        _charts_stats.pie(x, openit=False)
        _charts_stats.pie(x, y, main="A chart", out_file=pic, autopct='%1.1f%%', openit=False)
        _charts_stats.pie(x=[], y=[], openit=False)
        os.remove(pic)
        self.assertFalse(_path.exists(pic))

    def testrename_col(self):
        import arcpy
        import tempfile
        owo = arcpy.env.overwriteOutput
        arcpy.env.overwriteOutput = True
        tmpfc = _path.join(tempfile.gettempdir(), "tmp")
        tmpfc = arcpy.CopyFeatures_management(self.t_fc, tmpfc).getOutput(0)
        est = _common.rename_col(tmpfc, "ABBREV", "ABBREVIATION")
        obs = "ABBREVIATI"
        arcpy.Delete_management(tmpfc)
        arcpy.env.overwriteOutput = owo
        self.assertEqual(est, obs)
        pass

    def testtlist_to_table(self):
        colnames = ['NAME', 'POP_EST']
        coltypes = ['TEXT', 'DOUBLE']
        collengths = [250, '#']
        coldefs = zip(colnames, coltypes, collengths)
        coldefs2 = ['NAME:TEXT', 'POP_EST:DOUBLE']

        # read data
        tl = []
        with arcpy.da.SearchCursor(self.t_fc, colnames) as sc:
            for row in sc:
                tl.append(tuple(row))

        # write as table using log column definition
        ot = arcpy.CreateScratchName('tmp.dbf', workspace='c:\\temp')
        ot = _common.tlist_to_table(tl, ot, coldefs, -9, 'nullText')
        est1 = int(arcpy.GetCount_management(ot).getOutput(0))

        # write as table using short column definition
        ot = arcpy.CreateScratchName('tmp.dbf', workspace='c:\\temp')
        ot = _common.tlist_to_table(tl, ot, coldefs2, -9, 'nullText')
        est2 = int(arcpy.GetCount_management(ot).getOutput(0))
        obs = int(arcpy.GetCount_management(self.t_fc).getOutput(0))

        arcpy.Delete_management(ot)
        self.assertTrue(all((est1 == obs, est2 == obs)))
        pass

##    def testdocu(self):
##        pass

    def testmeta(self):
        fcws = 'c:\\temp'
        tempshp = arcpy.CreateScratchName('tmp.dbf', workspace=fcws).replace('.dbf', '.shp')
        fcnm = _path.basename(tempshp)

        # testing entries
        ttl,pps,abt = "Bar","example", "Column Spam means eggs"

        fc = arcpy.FeatureClassToFeatureClass_conversion(
            self.t_fc,
            fcws,
            fcnm
        ).getOutput(0)
        meta.meta(fc, 'OVERWRITE', title=ttl)
        editted = meta.meta(fc, 'append', purpose=pps, abstract=abt)
        editted = meta.meta(fc, 'overwrite', title=ttl, purpose=pps, abstract=abt)
        retrieved = meta.meta(fc)
        _common.dlt(fc)
        self.assertEqual(set(editted.values()), set(retrieved.values()))

##    def testmsg(self):
##        pass

    def testfrequency(self):
        est = _common.frequency([1,1,2,3,4,4,4])
        obs = {1: 2, 2: 1, 3: 1, 4: 3}
        samekeys = set(est.keys()) == set(obs.keys())
        good = all([samekeys] + [est[i] == obs[i] for i in est])
        self.assertTrue(good)
        pass

    def testlist_environments(self):
        envs = _common.list_environments([])
        self.assertEqual(len(envs), 50)
        pass

    def testoidF(self):
        est = _common.oidF(self.t_fc)
        obs = "OBJECTID"
        self.assertEqual(str(est), obs)
        pass

    def testshpF(self):
        est = _common.shpF(self.t_fc)
        obs = "Shape"
        self.assertEqual(str(est), obs)
        pass

    def testtstamp(self):
        est = []
        est.append(len(_common.tstamp()) == len('20140216184029'))
        est.append(len(_common.tstamp("lr")) == len('lr20140216184045'))
        est.append(len(_common.tstamp("lr", "%H%M%S")) == len('lr184045'))
        est.append(len(_common.tstamp("lr", "%H%M%S")) == len('lr184045'))
        est.append(len(_common.tstamp("lr", "%H%M%S", s=('run',1))) == len('lr184527_run_1'))
        obs = [True, True, True, True, True]
        self.assertEqual(est, obs)
        pass

    def testdlt(self):
        est = []
        wc = '"OBJECTID" < 11'
        lr = arcpy.management.MakeFeatureLayer(self.t_fc, "lr", wc).getOutput(0)
        # TODO: test for deleting layers won't pass even though _common.dlt works
        #print lr
        #print arcpy.Exists(lr)
        tempfc = 'in_memory\\tmp'
        if arcpy.Exists(tempfc):
            arcpy.Delete_management(tempfc)
        tmpfc = arcpy.CopyFeatures_management(lr, tempfc).getOutput(0)
        tempshp = arcpy.CreateScratchName('tmp.dbf', workspace='c:\\temp').replace('.dbf', '.shp')
        fc = arcpy.CopyFeatures_management(tmpfc, tempshp).getOutput(0)
        _common.dlt(lr)
        est.append(_common.dlt(tmpfc))
        est.append(_common.dlt(fc))
        est.append(_common.dlt('this does not exist'))
        self.assertEquals(est, [True, True, False])
        pass

    def testcleanup(self):
        x = []
        out = arcpy.CreateScratchName("tmp", workspace=arcpy.env.scratchGDB)
        x.append(arcpy.management.Copy(self.t_fc, out).getOutput(0))
        est = _common.cleanup(x)
        obs = 0
        self.assertEqual(est, obs)

    def testto_points(self):
        obs = 10
        wc = '"OBJECTID" < ' + str(obs + 1)
        ofc = arcpy.CreateScratchName("tmp_out.dbf", workspace="c:\\temp").replace('.dbf', '.shp')
        cs = 27700
        ptfc = _common.to_points(self.t_fc, ofc, "POP_EST", "GDP_MD_EST", cs, w = wc)
        est = int(arcpy.GetCount_management(ptfc).getOutput(0))
        arcpy.Delete_management(ptfc)
        self.assertEqual(est, obs)
        pass


##    def testwsp(self):
##        pass
##
##    def testswsp(self):
##        pass

    def testto_scratch(self):
        est = []
        obs = []
        arcpy.env.scratchWorkspace = arcpy.env.scratchGDB
        s = arcpy.env.scratchWorkspace

        est.append(_common.to_scratch('foo', 0))
        obs.append(_common._path.join(s, 'foo'))
        est.append(_common.to_scratch('foo', 1))
        obs.append(_path.join(s, 'foo0'))
        est.append(_common.to_scratch('foo.shp', 0))
        obs.append(_path.join(s, 'foo_shp'))
        est.append(_common.to_scratch('foo.shp', 1))
        obs.append(_path.join(s, 'foo_shp0'))

        # not tested for file based workspaces
        arcpy.env.scratchWorkspace = arcpy.env.scratchFolder
        a = arcpy.env.scratchWorkspace
        _common.to_scratch('foo', 0) == _path.join(s, 'foo')
        _common.to_scratch('foo', 1) == _path.join(s, 'foo0')
        _common.to_scratch('foo.shp', 0) == _path.join(s, 'foo_shp')
        _common.to_scratch('foo.shp', 1) == _path.join(s, 'foo_shp0')

        eq = all([ei == oi for ei,oi in zip(est, obs)])
        self.assertTrue(eq)

    def testremap_sa(self):
        est = []

        remapped = _common.remap_3d(10,50,10)
        est.append(remapped == '10 20 1;20 30 2;30 40 3;40 50 4')

        remapped = _common.remap_3d(0,5,1)
        est.append(remapped == '0 1 1;1 2 2;2 3 3;3 4 4;4 5 5')

        remapped = _common.remap_3d(-10,10,5)
        est.append(remapped == '-10 -5 1;-5 0 2;0 5 3;5 10 4')

        remapped = _common.remap_3d(-10,10,-5)
        est.append(remapped == '')

        remapped = _common.remap_3d(10,-20,-7)
        est.append(remapped == '10 3 1;3 -4 2;-4 -11 3;-11 -18 4;-18 -25 5')

        self.assertTrue(all(est))

    def testremap_3d(self):
        est = []

        remapped = _common.remap_sa(10,50,10)
        ob = [[[10, 20], 1], [[20, 30], 2], [[30, 40], 3], [[40, 50], 4]]
        est.append(remapped == ob)

        remapped = _common.remap_sa(0,5,1)
        ob = [[[0, 1], 1], [[1, 2], 2], [[2, 3], 3], [[3, 4], 4], [[4, 5], 5]]
        est.append(remapped == ob)

        remapped = _common.remap_sa(-10,10,5)
        ob = [[[-10, -5], 1], [[-5, 0], 2], [[0, 5], 3], [[5, 10], 4]]
        est.append(remapped == ob)

        remapped = _common.remap_sa(-10,10,-5)
        ob = []
        est.append(remapped == ob)

        remapped = _common.remap_sa(10,-20,-7)
        ob = [
            [[10, 3], 1], [[3, -4], 2], [[-4, -11], 3], [[-11, -18], 4],
            [[-18, -25], 5]
        ]
        est.append(remapped == ob)

        self.assertTrue(all(est))

    def testfind(self):
        self.testingfolder = _path.join(_path.dirname(sys.argv[0]), 'testing')
        obs = [1, 5]
        est = []
        findings = _common.find('*.shp', self.testingfolder)
        est.append(len(findings))
        findings = _common.find('*110m*', self.testingfolder)
        est.append(len(findings))
        self.assertEqual(est, obs)

    def testfixArgs(self):
        list_args = 'C:\Temp\Shapefiles\Contours.shp;C:\Temp\Shapefiles\Contours.shp'
        est = _common.fix_args(list_args, list)
        obs = ['C:\\Temp\\Shapefiles\\Contours.shp', 'C:\\Temp\\Shapefiles\\Contours.shp']
        self.assertEqual(est, obs)
        est = _common.fix_args('false', bool)
        self.assertEqual(est, False)
        pass

    def testint_to_float(self):
        _dir = _path.join(self.testingfolder, r'testing_files\rasters')
        ndvi = _path.join(_dir, 'dh_july_ndvi')
        ob = round(arcpy.Raster(ndvi).maximum, 5)
        int_rst = _path.join(_dir, 'ndvi_int')
        est = _path.join(_dir, 'ndvi_tst')
        if arcpy.CheckExtension('Spatial') == 'Available':
            arcpy.CheckOutExtension('Spatial')
            arcpy.sa.Int(arcpy.sa.Times(ndvi, 1000000)).save(int_rst)
            arcpy.CheckInExtension('Spatial')
            _common.int_to_float(int_rst, est, 6)
            self.assertEqual(ob, round(arcpy.Raster(est).maximum, 5))
            for rast in [int_rst, est]:
                try:
                    arcpy.Delete_management(rast)
                except:pass
        pass

    def testfill_no_data(self):
        _dir = _path.join(self.testingfolder, r'testing_files\rasters')
        ndvi = _path.join(_dir, 'dh_july_ndvi')
        est = _path.join(_dir, 'ndvi_fill')
        null = _path.join(_dir, 'null_rst')
        if arcpy.CheckExtension('Spatial') == 'Available':
            _common.fill_no_data(ndvi, est, 10, 10)
            arcpy.CheckOutExtension('Spatial')
            arcpy.sa.IsNull(est).save(null)
            self.assertEqual(arcpy.Raster(null).maximum, 0)
            arcpy.CheckInExtension('Spatial')
            for rast in [est, null]:
                try:
                    arcpy.Delete_management(rast)
                except:pass
        pass

    def testmeters_to_feet(self):
        _dir = _path.join(self.testingfolder, r'testing_files\rasters')
        dem = _path.join(_dir, 'dh30m_dem')
        est = _path.join(_dir, 'dem_ft')
        _common.meters_to_feet(dem, est)
        self.assertEqual(int(arcpy.Raster(est).maximum), 6244)
        try:
            arcpy.Delete_management(est)
        except:
            pass
        pass

    def testcopy_schema(self):
        tmp = r'in_memory\schema_test'
        _common.copy_schema(self.t_fc, tmp)
        self.assertTrue(arcpy.Exists(tmp))
        arcpy.Delete_management(tmp)
        pass

    def testmake_poly_from_extent(self):
        desc = arcpy.Describe(self.t_fc2)
        ext = desc.extent
        sr = desc.spatialReference
        est = _common.make_poly_from_extent(ext, sr)
        self.assertEqual(str(ext), str(est.extent))
        pass

    def testlist_all_fcs(self):
        est = _common.list_all_fcs(self.testing_gdb, '*', 'All', True)
        obs = ['Illinois', 'ne_110m_admin_0_countries']
        self.assertEqual(est, obs)
        pass

    def testfield_list(self):
        il = _path.join(self.testing_gdb, 'Illinois')
        est = _common.field_list(il, ['state_fips', 'cnty_fips'])
        obs = ['OBJECTID', 'Shape', 'NAME', 'STATE_NAME',
               'FIPS', 'Shape_Length', 'Shape_Area']
        self.assertEqual(est, obs)
        pass

    def testget_field_type(self):
        il = _path.join(self.testing_gdb, 'Illinois')
        est = _common.get_field_type('NAME', il)
        self.assertEqual(est, 'TEXT')
        pass

    def testmatch_field(self):
        fc = _path.join(self.testing_gdb, 'Illinois')
        est = _common.match_field(fc, '*fips', True)
        obs = ['STATE_FIPS', 'CNTY_FIPS', 'FIPS']
        self.assertEqual(est, obs)
        pass

    def testadd_fields_from_table(self):
        fc = _path.join(self.testing_gdb, 'Illinois')
        copy = fc + '_copy'
        if arcpy.Exists(copy):
            arcpy.Delete_management(copy)
        arcpy.CopyFeatures_management(fc, copy)
        flds = ['POP1990', 'POP2000']
        tab = fc = _path.join(self.testing_gdb, 'Illinois_county_info')
        _common.add_fields_from_table(copy, tab, flds)
        est = [f.name for f in arcpy.ListFields(copy)]
        try:
            arcpy.Delete_management(copy)
        except: pass
        for f in flds:
            self.assertTrue(f in est)
        pass

    def testcreate_field_name(self):
        fc = _path.join(self.testing_gdb, 'Illinois')
        est = _common.create_field_name(fc, 'NAME')
        self.assertEqual(est, 'NAME_1')
        pass

    def testjoin_using_dict(self):
        if arcpy.Exists(r'in_memory\copy'):
            arcpy.Delete_management(r'in_memory\copy')
        fc = _path.join(self.testing_gdb, 'Illinois')
        copy = fc + '_copy'
        if arcpy.Exists(copy):
            arcpy.Delete_management(copy)
        arcpy.CopyFeatures_management(fc, copy)
        flds = ['POP1990', 'POP2000']
        tab = fc = _path.join(self.testing_gdb, 'Illinois_county_info')
        _common.join_using_dict(copy, 'CNTY_FIPS', tab, 'CNTY_FIPS', flds)
        est = [f.name for f in arcpy.ListFields(copy)]
        try:
            arcpy.Delete_management(copy)
        except: pass
        for f in flds:
            self.assertTrue(f in est)
        pass

    def testconcatenate(self):
        est = _common.concatenate(['A','B','C'], '-')
        self.assertEqual(est, 'A-B-C')
        pass

    def testconcatenate_fields(self):
        if arcpy.Exists(r'in_memory\copy'):
            arcpy.Delete_management(r'in_memory\copy')
        fc = _path.join(self.testing_gdb, 'Illinois')
        copy = fc + '_copy'
        if arcpy.Exists(copy):
            arcpy.Delete_management(copy)
        arcpy.CopyFeatures_management(fc, copy)
        _common.concatenate_fields(copy, 'FULL', 75, ['NAME', 'STATE_NAME'], ' County, ')
        obs = 'Jo Daviess County, Illinois'
        with arcpy.da.SearchCursor(copy, 'FULL') as rows:
            est = rows.next()[0]
        del rows
        try:
            arcpy.Delete_management(copy)
        except: pass
        self.assertEqual(est, obs)
        pass

    def testcreate_pie_chart(self):
        tab = fc = _path.join(self.testing_gdb, 'Illinois_county_info')
        oid = arcpy.AddFieldDelimiters(tab, arcpy.Describe(tab).OIDFieldName)
        where = '{0} < 11'.format(oid)
        tv = arcpy.MakeTableView_management(tab, 'IL_table', where)
        fig = _path.join(self.testingfolder, 'IL_county_pop.png')
        # will use 'CNTY_FIPS' as case field since our pop field is
        # already populated for each county
        _common.create_pie_chart(fig, tv, 'NAME','POP2000', 'IL Counties')
        self.assertTrue(_path.exists(fig))
####        try:
####            arcpy.Delete_management(fig) # may want to look at the figure, pretty cool!
####        except:
####            pass
        pass

    def testcombine_pdfs(self):
        _dir = _path.dirname(self.testingfolder)
        mapDoc = _path.join(_dir, 'chart.mxd')
        mxd = arcpy.mapping.MapDocument(mapDoc)
        txt_elm = [elm for elm in arcpy.mapping.ListLayoutElements(mxd, 'TEXT_ELEMENT')
                   if elm.text == 'SomeText'][0]
        del_list = []
        for i in range(3):
            txt_elm.text = "Hi, I'm page {0}".format(i)
            pdf = _path.join(_dir, 'test_{0}.pdf'.format(i))
            arcpy.mapping.ExportToPDF(mxd, pdf, resolution=100)
            del_list.append(pdf)
        combined = _path.join(_dir, 'combined.pdf')
        del mxd
        _common.combine_pdfs(combined, del_list)
        self.assertTrue(_path.exists(combined))
        del_list.append(combined)
        try:
            for p in del_list:
                arcpy.Delete_management(p)
        except:
            pass
        pass

    def testlist_data(self):
        """TODO: Write more tests for listing data"""
        expected = ['testing.gdb','testing_files']
        data = _common.list_data(self.testingfolder)
        datas = str("".join(data))
        all_in = all([(ei in datas) for ei in expected])
        self.assertTrue(all_in)

    def testrequest_text(self):
        """Basic test to get a page as text"""
        d = _common.request('http://google.com')
        self.assertNotEqual(d, '')

    def testrequest_json(self):
        """Get json from arcgis sampleserver"""
        u = 'http://sampleserver3.arcgisonline.com/ArcGIS/rest/services'
        d = _common.request(u, {'f':'json'}, 'json')
        items = [
            isinstance(d, dict),
            isinstance(d.get('services'), list),
            isinstance(d.get('folders'), list),
            isinstance(d.get('currentVersion'), int)
        ]
        self.assertTrue(all(items))

    def testrequest_xml(self):
        """Get XML from epsg.io"""
        u = 'http://epsg.io/4326.xml'
        d = _common.request(u, None, 'xml')

        tg = str(d.tag)
        tp = '{http://www.opengis.net/gml/3.2}GeographicCRS'

        self.assertEqual(tg, tp)

    def testarctype_to_ptype(self):
        """Converting from ArcGIS type strings to python types"""
        self.assertTrue(_common.arctype_to_ptype("SHORT") is int)
        self.assertTrue(_common.arctype_to_ptype("Short") is int)
        self.assertTrue(_common.arctype_to_ptype("SHORT ") is int)
        self.assertTrue(_common.arctype_to_ptype("TEXT") is str)
        self.assertTrue(_common.arctype_to_ptype("STRING") is str)

        self.assertTrue(_common.arctype_to_ptype("SMALLINTEGER") is int)
        self.assertTrue(_common.arctype_to_ptype("LONG") is int)
        self.assertTrue(_common.arctype_to_ptype("INTEGER") is int)
        self.assertTrue(_common.arctype_to_ptype("DATE") is _datetime.datetime)
        self.assertTrue(_common.arctype_to_ptype("DATETIME") is _datetime.datetime)
        self.assertTrue(_common.arctype_to_ptype("FLOAT") is float)
        self.assertTrue(_common.arctype_to_ptype("SINGLE") is float)
        self.assertTrue(_common.arctype_to_ptype("DOUBLE") is float)

        self.assertTrue(_common.arctype_to_ptype("") is str)
        self.assertTrue(_common.arctype_to_ptype(None) is str)

        with self.assertRaises(Exception):
            _common.arctype_to_ptype()
        pass

    def testproject_coordinates(self):
        """Projecting list of coordinate pairs"""
        dtt = 'TM65_To_WGS_1984_2 + OSGB_1936_To_WGS_1984_NGA_7PAR'
        coordinates = [(240600.0, 375800.0), (245900.0, 372200.0)]
        observed = _common.project_coordinates(coordinates, 29902, 27700, dtt)
        expected = [
            (53444.10991363949, 539226.5651404626),
            (58422.59724314464, 535183.1931399861)
        ]
        self.assertEqual(observed, expected)
        pass


if __name__ == '__main__':
    unittest.main(verbosity = 2)
