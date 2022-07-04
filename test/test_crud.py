"""unit tests for features"""
import unittest

from inspect import getsourcefile as _getsourcefile
import os.path as _path

import arcpy

import funclite.iolib as iolib

import arcapi.crud as crud


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
    def test_crud_cursors(self):
        """testfunc"""
        cols = ['NAME', 'CNTY_FIPS', 'OID@']
        with crud.SearchCursor(self.illinois_shp, cols, load_shape=True) as Cur:
            for R in Cur:
                print(R['NAME'])
                print(R.Shape.centroid)
            pass

    #  @unittest.skip("Temporaily disabled while debugging")
    def test_crud(self):
        """test_crud"""
        if False:
            with crud.CRUD(self.illinois_shp, self.gdb, enable_transactions=False) as Crud:
                # lookup
                filt = {'NAME': 'INVALID_NAME', 'FIPS': '17085', 'FID': -99999}
                geom, wkt = Crud.lookup([crud.FieldNamesSpecial.shape, crud.FieldNamesSpecial.wkt], filt)
                self.assertIsNone(geom)
                self.assertIsNone(wkt)

                filt = {'NAME': 'Jo Daviess', 'FIPS': '17085', 'FID': 0}  # dont forget this is the shape file and not the geodatabase
                geom, wkt = Crud.lookup([crud.FieldNamesSpecial.shape, crud.FieldNamesSpecial.wkt], filt)
                v = Crud.exists_by_compositekey(**filt)
                self.assertTrue(v)


            with crud.CRUD(self.illinois_shp, self.gdb, enable_transactions=True) as Crud:
                filt = {'NAME': 'Jo Daviess', 'FIPS': '17085', 'FID': 0}
                Crud.upsert(filt, True, STATE_NAME='TEST')  # This is an edit

                vals = {crud.FieldNamesSpecial.shape: geom, 'NAME': 'TEST_NAME',
                        'STATE_NAME': 'TEST_STATE', 'STATE_FIPS': '17',
                        'CNTY_FIPS': '999', 'FIPS': '99', }
                Crud.upsert(vals)

            with crud.CRUD(self.illinois_shp, self.gdb, enable_transactions=True) as Crud:
                vals = {'NAME': 'TEST_NAME',
                        'STATE_NAME': 'TEST_STATE', 'STATE_FIPS': '17',
                        'CNTY_FIPS': '999', 'FIPS': '99', }
                Crud.delete(**vals)

        with crud.CRUD(self.illinois_gdb, self.gdb, enable_transactions=True) as Crud:
            filt = {'OBJECTID': 1}
            Crud.upsert(filt, NAME='YYYYY')
            # Crud.tran_rollback()
            Crud.tran_commit()
        return

        with crud.CRUD(self.illinois_shp, self.gdb, enable_transactions=True) as Crud:
            filt = {'FID': 0}
            Crud.upsert(filt, NAME='TRAN_COMMIT')
            Crud.tran_commit()



        print('That should be done')


if __name__ == '__main__':
    unittest.main(verbosity=2)
