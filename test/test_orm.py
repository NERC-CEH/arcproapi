"""unit tests for features"""
import unittest

from inspect import getsourcefile as _getsourcefile
import os.path as _path

# import arcpy

import funclite.iolib as iolib

import arcproapi.crud as crud
import arcproapi.orm as orm


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

    #  @unittest.skip("Temporaily disabled while debugging")
    def test_class_def(self):
        """testfunc"""
        s = orm.class_def_to_clip(self.illinois_gdb, self.gdb, ['NAME', 'STATE_NAME', 'CNTY_FIPS'])
        print(s)

    @unittest.skip("Temporaily disabled while debugging")
    def test_add_update_delete(self):
        """test_crud"""
        with orm.ORM(self.illinois_gdb, workspace=self.gdb, enable_transactions=False, OBJECTID=88, Shape=None) as Shp:
            Shp.read()
            shp = Shp.Shape

        with orm.ORM(self.illinois_gdb, ['NAME', 'STATE_NAME', 'CNTY_FIPS'],
                     workspace=self.gdb,
                     NAME='NAME'
                , STATE_NAME='STATE_NAME'
                , CNTY_FIPS='A'
                , STATE_FIPS='B'
                , FIPS='C'
                , Shape=shp
                     ) as B:
            B.add(tran_commit=False, fail_on_exists=False)

            # After the add, change values, refresh and add with a commit
            B.NAME = 'NAME1'
            B.STATE_NAME = 'STATE_NAME1'
            B.CNTY_FIPS = 'AA'
            B.STATE_FIPS = 'BB'
            B.FIPS = 'CC'
            B.Shape = shp
            i = B.add(tran_commit=True)

            # change one value and recall update - this edit will use the OID, allowing update of STATE_NAME (part of commposite key)
            B.STATE_NAME = 'UPDATE'
            B.update(tran_commit=True)

        with orm.ORM(self.illinois_gdb, workspace=self.gdb, enable_transactions=True) as B:
            B.STATE_NAME = 'STATE_NAME'
            B.delete(err_on_no_key=False)

        with orm.ORM(self.illinois_gdb, workspace=self.gdb, enable_transactions=True, OBJECTID=i, STATE_NAME=None) as B:
            B.read()  # read in STATE_NAME from the objectid
            self.assertEquals(B['STATE_NAME'], 'UPDATE')
            ok = B.delete(tran_commit=True)
            assert self.assertTrue(ok)

    # @unittest.skip("Temporaily disabled while debugging")
    def test_add(self):
        from arcproapi import geom
        shp = geom.Square([0.0], 10)
        with orm.ORM(self.illinois_gdb, ['NAME', 'STATE_NAME', 'CNTY_FIPS'],
                     workspace=self.gdb,
                     NAME='NAME'
                , STATE_NAME='STATE_NAME'
                , CNTY_FIPS='A'
                , STATE_FIPS='B'
                , FIPS='C'
                , Shape=shp
                     ) as B:
            B.add(tran_commit=False, fail_on_exists=False)

            # After the add, change values, refresh and add with a commit
            B.NAME = 'NAME1'
            B.STATE_NAME = 'STATE_NAME1'
            B.CNTY_FIPS = 'AA'
            B.STATE_FIPS = 'BB'
            B.FIPS = 'CC'
            B.Shape = shp
            i = B.add(tran_commit=True)

            # change one value and recall update - this edit will use the OID, allowing update of STATE_NAME (part of commposite key)
            B.STATE_NAME = 'UPDATE'
            B.update(tran_commit=True)

        with orm.ORM(self.illinois_gdb, workspace=self.gdb, enable_transactions=True) as B:
            B.STATE_NAME = 'STATE_NAME'
            B.delete(err_on_no_key=False)

        with orm.ORM(self.illinois_gdb, workspace=self.gdb, enable_transactions=True, OBJECTID=i, STATE_NAME=None) as B:
            B.read()  # read in STATE_NAME from the objectid
            self.assertEquals(B['STATE_NAME'], 'UPDATE')
            ok = B.delete(tran_commit=True)
            assert self.assertTrue(ok)


if __name__ == '__main__':
    unittest.main(verbosity=2)
