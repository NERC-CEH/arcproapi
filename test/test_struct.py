"""unit tests for features"""
import unittest

from inspect import getsourcefile as _getsourcefile
import os.path as _path

import arcpy  # noqa

import funclite.iolib as iolib

import arcproapi.structure as struct


class Test(unittest.TestCase):
    """unittest for keypoints"""

    def setUp(self):
        """setup variables etc for use in test cases
        """
        self.pth = iolib.get_file_parts2(_path.abspath(_getsourcefile(lambda: 0)))[0]
        self.modpath = _path.normpath(self.pth)

        self.aprx = _path.normpath(_path.join(self.modpath, 'test_arcpro_project/test_arcpro_project.aprx'))
        # C:\development\erammp-python\arcapi\test\testing.gdb
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
    def test_schema_compare(self):
        """testfunc"""
        res = struct.fcs_schema_compare(self.illinois_gdb, self.illinois_shp, sortfield='NAME')
        print(res)

    # @unittest.skip("Temporaily disabled while debugging")
    def test_FieldsDescribe(self):
        """testfunc"""
        FD = struct.FieldsDescribe(self.illinois_gdb)
        print(FD['NAME'])

        E = FD.editable()
        Ef = FD.editable(as_fields=True)

        G = FD.Geometry()
        self.assertEqual(G.name, 'Shape')  # noqa
        # self.assertFalse(G.isnullable)  # noqa

        Gf = FD.Geometry(as_field=True)

        O = FD.OID()
        Of = FD.OID(as_field=True)

        R = FD.required()
        Rf = FD.required(as_fields=True)

        self.assertIsInstance([F for F in FD.iterfields()], list)
        self.assertIsInstance([F for F in FD], list)

        s = str(FD)
        pass

    @unittest.skip("Temporaily disabled while debugging")
    def test_AliasToFieldName(self):
        pass
        struct.fc_fields_rename_to_alias(self.illinois_gdb)
        pass

if __name__ == '__main__':
    unittest.main(verbosity=2)
