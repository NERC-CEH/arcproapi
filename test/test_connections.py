"""unit tests for features"""
import unittest

from inspect import getsourcefile as _getsourcefile
import os.path as _path

import pandas

import funclite.iolib as iolib


# import funclite.stringslib as stringslib
import arcproapi.connections as conn
import arcproapi.sql as sql
from arcproapi.connections import ESRICursorType

class Test(unittest.TestCase):
    """unittest for keypoints"""

    def setUp(self):
        """setup variables etc for use in test cases
        """
        self.pth = iolib.get_file_parts2(_path.abspath(_getsourcefile(lambda: 0)))[0]
        self.modpath = _path.normpath(self.pth)

        self.aprx = _path.normpath(_path.join(self.modpath, 'test_arcpro_project/test_arcpro_project.aprx'))
        self.gdb = _path.normpath(_path.join(self.modpath, 'testing.gdb'))

        self.illinois = 'Illinois'
        self.countries = 'ne_110m_admin_0_countries'
        self.illinois_table = 'Illinois_county_info'

        self.illinois_shp = _path.normpath(_path.join(self.modpath, 'testing_files/illinois.shp'))

        self.excel = _path.normpath(_path.join(self.modpath, 'testing_files/workbook.xlsx'))
        self.txt = _path.normpath(_path.join(self.modpath, 'testing_files/txt.csv'))

        self.topo = 'base_group_layer/Topographic'

    @unittest.skip("Temporaily disabled while debugging")
    def test_esri_feature_class(self):
        """testfunc"""
        cols = ('STATE_NAME', 'STATE_FIPS')
        f = sql.columns_delim(cols, self.gdb)  # just to test this
        w = sql.query_where_in('STATE_NAME', values=('Illinois','Texas'), datasource=self.gdb)

        Config = conn.ConfigESRIGeoDBTableOrFeatureClass(fname=self.gdb, lyr_or_tbl_name=self.illinois)
        with conn.ESRIGeoDBFeatureClassOrTable(Config, cursor_type=ESRICursorType.PandasDataframe, cols=cols, where_clause=w) as C:
            self.assertIsInstance(C.df, pandas.DataFrame)

        Config = conn.ConfigESRIGeoDBTableOrFeatureClass(fname=self.gdb, lyr_or_tbl_name=self.illinois_table)
        with conn.ESRIGeoDBFeatureClassOrTable(Config, cursor_type=ESRICursorType.PandasDataframe) as C:
            self.assertIsInstance(C.df, pandas.DataFrame)
        pass

    @unittest.skip("Temporaily disabled while debugging")
    def test_esri_shp(self):
        """testfunc"""
        cols = ('STATE_NAME', 'STATE_FIPS')

        w = sql.query_where_in('STATE_NAME', values=('Illinois','Texas'), datasource=self.gdb)
        Config = conn.ConfigESRIShp(self.illinois_shp)
        with conn.ESRIShp(Config, cursor_type=ESRICursorType.PandasDataframe, cols=cols, where_clause=w) as C:
            self.assertIsInstance(C.df, pandas.DataFrame)
        pass

    @unittest.skip("Temporaily disabled while debugging")
    def test_excel(self):
        """testfunc"""
        Config = conn.ConfigExcel(self.excel, 'table_worksheet_one')
        with conn.Excel(Config, visible=True) as C:
            self.assertIsInstance(C.df, pandas.DataFrame)
            self.assertEquals(C.Table.range.rows.count, 6)
            self.assertEquals(C.Table.range.columns.count, 5)

        Config = conn.ConfigExcel(self.excel, worksheet='worksheet_no_table', range_='A1', expand_cell_range='table')
        with conn.Excel(Config, visible=True) as C:
            self.assertIsInstance(C.df, pandas.DataFrame)
            self.assertEquals(C.Range.rows.count, 6)
            self.assertEquals(C.Range.columns.count, 5)


    def test_text(self):
        """testfunc"""
        Config = conn.ConfigTextFile(self.txt)
        with conn.TextFile(Config) as C:
            self.assertIsInstance(C.df, pandas.DataFrame)



if __name__ == '__main__':
    unittest.main(verbosity=2)
