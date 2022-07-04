"""unit tests for features"""
import unittest

from inspect import getsourcefile as _getsourcefile
import os.path as _path

import xlwings
import arcpy

import funclite.iolib as iolib

import arcapi.data as data


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
        self.illinois_gdb = _path.normpath(_path.join(self.gdb, self.illinois))
        self.excel = _path.normpath(_path.join(self.modpath, 'testing_files/workbook.xlsx'))
        self.txt = _path.normpath(_path.join(self.modpath, 'testing_files/txt.csv'))

        self.topo = 'base_group_layer/Topographic'

    @unittest.skip("Temporaily disabled while debugging")
    def test_table_to_pandas(self):
        """testfunc"""
        df = data.table_as_pandas2(self.illinois_gdb)
        print('done')

    # @unittest.skip("Temporaily disabled while debugging")
    def test_misc(self):
        """misc stuff"""
        data.field_get_dup_values(r'S:\SPECIAL-ACL\ERAMMP2 Survey Restricted\Handover space\2 PERSONAL Permissions for ERAMMP 2021\Local geodatabase\permissionsERAMMP.gdb\AllSurveyedSquares', 'SQ_ID')



if __name__ == '__main__':
    unittest.main(verbosity=2)
