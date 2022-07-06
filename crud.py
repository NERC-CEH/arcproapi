"""CRUD with feature classes and tables

Notes:
    Shapefiles do not support transactions. Changes occur immediately and trans_rollback has no effect.

Examples:
    See test/test_crud.py

TODO:
    Consider converting the upsert to seperate add and insert to reduce complexity.
"""

import os.path as _path
from warnings import warn as _warn
import fuckit as _fuckit

import arcpy as _arcpy
import arcpy.da as _da

import arcproapi.environ as _environ
import arcproapi.sql as _sql
import arcproapi.errors as _errors


from arcproapi.common import FieldNamesSpecial, get_row_count2 as get_row_cnt, get_id_col  # noqa


class SearchCursor(_da.SearchCursor):
    """
    Wrapper around arcpy.da.SearchCursor. The rows yielded are of class crud.Row,
    which supports accessing values as a property of the Row instance or using indexing
    on column name.

    Args:
        fname (str): Name of feature class or table
        field_names (str, list, tuple): String or iterable of field names to retreive
        load_shape (bool): load the geometry, note that the name is mangled in the underlying Row, as the @ symbol is invalid
        **kwargs: Keyword arguments, passed to the arcpy SearchCursor call. See https://pro.arcgis.com/en/pro-app/latest/arcpy/data-access/searchcursor-class.htm

    Notes:
        Unexpected 'A column was specified which does not exist' may be solved by using 'FID' instead of 'ObjectID'. Sometimes using OID@ doesnt even work.

    Examples:
        >>> with SearchCursor('c:/my.gdb/mytable', ['OBJECTID'], where_clause='OBJECTID=10', load_shape=True) as Cur:
        >>>     for R in Cur:
        >>>         R.OBJECTID, R['OBJECTID']  # noqa
        >>>         R.SHAPEat.area, R['SHAPE@'].area # noqa
        10,10
        23.223, 23.223
        """

    def __init__(self, fname, field_names, load_shape=False, **kwargs):
        # no comments here, otherwise it breaks pycharms ctrl-Q documentation
        if fname[-4:] == '.shp' and 'objectid' in [s.lower() for s in field_names]:
            _warn('This may error with an unexpected "A column was specified which does not exist."'
                  'Shapefiles have their primary key named "FID", not "ObjectID". ObjectID is used in geodatabases.'
                  )

        fname = _path.normpath(fname)
        self._load_shape = load_shape
        self._rowcount = None
        if isinstance(field_names, str):
            field_names = [field_names]
        if load_shape and 'SHAPE@' not in field_names:
            field_names.append('SHAPE@')
        super().__init__(fname, field_names, **kwargs)

    def __enter__(self):
        """enter"""
        super().__enter__()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        super().__exit__()

    def __str__(self):
        """object instance description"""
        sb = []
        for key in self.__dict__:  # noqa
            sb.append("{key}='{value}'".format(key=key, value=self.__dict__[key]))
        return ', '.join(sb)

    def __iter__(self):
        """iter"""
        return self

    def __next__(self):
        """iter next"""
        try:
            r = _Row(super().__next__(), self.fields)
        except RuntimeError as e:
            if 'invalid SQL' in str(e):
                raise RuntimeError('Invalid SQL statement. Check that the feature class isnt using a text type to store numerics and/or adjust your kwargs')
            else:
                raise e
        return r

    def __delitem__(self, key):
        raise _errors.ReadOnlyError('SearchCursor items are read only')

    @property
    def rowcount(self):
        """Get row count. This can be called first, then the cursor can still be reused"""
        if self._rowcount:
            return self._rowcount
        i = 0
        try:
            while self.__next__():
                i += 1
        except StopIteration:
            pass
        self._rowcount = i
        self.reset()
        return i


class UpdateCursor(_da.UpdateCursor):
    """Wrapper around arcpy.da.SearchCursor. The rows yielded are of class crud.Row,
    which supports accessing values as a property of the Row instance or using indexing
    on column name.

    Args:
        fname (str): name of feature class or table
        field_names (list, str): string or iterable of field names to retreive
        load_shape (bool): load the shape, note that the name is mangled in the underlying Row, as the @ symbol is invalid
                    hence, the
        kwargs: keyword value pairs, passed to the arcpy SearchCursor call. See https://pro.arcgis.com/en/pro-app/latest/arcpy/data-access/searchcursor-class.htm

    Notes:
        Unexpected 'A column was specified which does not exist' may be solved by using 'FID' instead of 'ObjectID'. Sometimes using OID@ doesnt work.

    Examples:
        >>> with UpdateCursor('c:/my.gdb/mytable', ['OBJECTID', 'CITY'], where_clause='OBJECTID = 10', load_shape=True) as Cur:
        >>>     for R in Cur:
        >>>         R['CITY'] = 'London'  # noqa
        >>>         Cur.update(R)  # noqa
        10,10
        23.223, 23.223
    """

    def __init__(self, fname, field_names, load_shape=False, **kwargs):
        fname = _path.normpath(fname)
        self._load_shape = load_shape
        self._rowcount = None
        if isinstance(field_names, str):
            field_names = [field_names]
        if load_shape and 'SHAPE@' not in field_names:
            field_names.append('SHAPE@')
        super().__init__(fname, field_names, **kwargs)

    def __enter__(self):
        super().__enter__()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        super().__exit__(exc_type, exc_val, exc_tb)

    def __str__(self):
        sb = []
        for key in self.__dict__:  # noqa
            sb.append("{key}='{value}'".format(key=key, value=self.__dict__[key]))
        return ', '.join(sb)

    def __iter__(self):
        """iter"""
        return self

    def __next__(self):
        return _Row(super().__next__(), self.fields)

    def __delitem__(self, key):
        raise _errors.ReadOnlyError('UpdateCursor items are read only')

    def updateRow(self, Row):
        Row._write_row()  # noqa
        super().updateRow(Row._row)  # noqa

    @property
    def rowcount(self):
        if self._rowcount:
            return self._rowcount
        i = 0
        while self.__next__():
            i += 1
        self.reset()
        self._rowcount = i
        return i


class _Row:
    """
    Wrapper for the row list, enabling accessing row vals by col name"""
    class Field:
        """
        Args:
            name (str): name of column
            value (any): The value of the field
            index (int): Index within the row
        """

        def __init__(self, name: str, value: any, index: int):
            self.name = name
            self.value = value
            self.index = index

        def __str__(self):
            """friendly print instance members"""
            return '[%s] %s: %s' % (self.index, self.name, self.value)


    def __init__(self, row, flds):
        """init"""
        self._row = row
        self._flds = flds

        for v in zip(row, flds):
            v = list(v)
            if '@' in v[1]:
                v[1] = v[1].replace('@', 'at')  # noqa
            self.__dict__[v[1]] = v[0]

    def __getitem__(self, item):
        """iterator"""
        if isinstance(item, int):
            return self._row[item]
        return self._row[self._flds.index(item)]

    def __setitem__(self, item, value):
        """setitem"""
        if isinstance(item, int):
            self._row[item] = value
        else:
            self._row[self._flds.index(item)] = value
            self.__dict__[item] = value

    def __str__(self):
        """friendly print"""
        sb = []
        for key, v in self.__dict__.items():  # noqa
            sb.append("{key}='{value}'".format(key=key, value=v))
        return ', '.join(sb)

    def _write_row(self):
        """write things back to row, so we can use it for the update"""
        for k, v in self.__dict__.items():
            if k == '_row' or k == '_flds': continue
            self._row[self._flds.index(k)] = v

    def fields(self):
        """Generator which yields crud._Row fields

        Yields:
            _Row.Field:

        Examples:
            >>> with SearchCursor('c:/my.gdb/mytable', ['OBJECTID'], where_clause='OBJECTID=10', load_shape=True) as Cur:
            >>>     for R in Cur:
            >>>         for F in R.fields():
            >>>             print(F)

        """
        ff = zip(self._flds, self._row)
        for i, f, v in enumerate(ff):
            F = _Row.Field(f, v, i)
            yield F


    @property
    def Shape(self):
        """Return shape as an arcpy.Geometry instance
        https://pro.arcgis.com/en/pro-app/latest/arcpy/classes/geometry.htm
        """
        if 'SHAPE@' not in self._flds:
            return None
        shp = self._row[self._flds.index('SHAPE@')]
        assert isinstance(shp, _arcpy.Geometry)  # just for intellisense
        return shp


class CRUD:
    """Create/Read/Update/Delete wrapper for file geodatabases and shapefiles

    Supports context creation. If we ask for an edit session, then the context manager automatically
    deals with opening and commiting edits.

    To roll back edits call tran_rollback.

    Parameters:
        fname: path to shape file or file geodatabase layer
        workspace: A file geodatabase workspace, used to support transactions. Will use scratch space if workspace==None
        enable_transactions: Set to true if doing any edit work, Automatically starts an edit session.


    Example 1 Working in an edit session:
    >>> with CRUD('c:/my.gdb/mylyr', 'c:/my.gdb', True) as Crud:
    >>>     Crud.upsert()
    """

    def __init__(self, fname, workspace=None, enable_transactions=True):
        """(str,str|None)->None
        Open our feature class or table in workspace

        Workspace allows us to transactionalise operations

        Parameters:
            workspace: Open the workspace, workspace is created if workspace doesnt exist, if workspace is None, uses a default temporary scratch workspace
        """
        fname = _path.normpath(fname)
        self._workspace_txt = workspace
        self._fname = fname
        self._enable_transactions = enable_transactions
        self._transaction = None
        self._workspace = _environ.workspace_set(workspace)

        self._editor = None
        if self._enable_transactions:
            self._editor = _da.Editor(self._workspace)


    def __enter__(self):
        """enter"""
        if self._enable_transactions:
            self.tran_begin()
        return self

    def __exit__(self, t, v, tb):
        """exit"""
        self.close()

    def close(self, commit=True):
        """Closes the active workspace

        Args:
            commit: commit any edits, else rollsback any edits

        Notes:
            This should be called with no using a context handler, so that the inheriting ORM classes
            members can still be accessed without potentially holding a lock on the work
            """
        if self._editor:
            with _fuckit:
                if commit:
                    self.tran_commit()
                else:
                    self.tran_rollback()
                del self._editor
                del self._workspace

    def exists_by_key(self, fld, v):
        """(str, float|int|str)->bool
        return bool indicating if  v exists in the field fld
        """
        # TODO check it works with dates
        where = _sql.query_where_in(fld, v)
        with SearchCursor(self._fname, fld, where_clause=where) as Cur:
            return isinstance(Cur.rowcount, int)

    def exists_by_compositekey(self, **kwargs):
        """(str, dic)->bool
        Return true or false if a record exists in table based on multiple values
        so dic would be for e.g.
        foreignkey1.id=1, foreignkey2.id=3, id=5
        """
        if not kwargs:
            return False

        where = CRUD._kwargs_where(kwargs)
        with SearchCursor(self._fname, 'OID@', where_clause=where) as Cur:
            v = Cur.rowcount
            return True if v else False


    def lookup(self, cols_to_read, key_val_dict, allow_multi=False):
        """(str, str|iter, dic:str) -> any-iter
        Read the values in cols_to_read which matches
        the values assigned to the col-value pairs in key_cols.

        By default, expects to match a single row, but if
        allow_multi is true, then can return multiple rows
        in a 2d list.

        Args:
        table:
            the name of the table
        cols_to_read:
            column name or iterable for multiple columns, Use '*' to retreive all columns, except BLOBS
        key_val_dict:
            a dictionary of key value pairs, e.g. {'id':1, 'country':'UK'}

        returns:
            If allow_multi is false, returns a 1d-list of the column values of cols_to_read.
            Uf allow_muliti is true, returns a 2d-list of crud.Row types,

            If no matches (or errored), then returns list of [None] * len(cols_to_read), or [[None] * len(cols_to_read)]

        Raises:
            errors.LookUpGotMoreThanOneRow: If allow_multi is false and we get more than 1 row

        Notes:
            1) crud.FieldNamesSpecial is a aide-memoir to ESRI's special field names
            2) If you are getting an unexpected error 'An invalid sql statement....', check that the featureclass is not storing integers as text
            3) Raises an error if more than 1 record matches

        Exmaple - Found Record:
        >>> with CRUD('c:/my.gdb', enable_transactions=True) as C:
        >>>     ord_nr, ord_total = C.lookup(['onumber', 'total'], {'company':'Amazon', 'region':'UK'})
        >>> 'ON1235', 24000.123

        Example - no record
        >>> with CRUD('c:/my.gdb', enable_transactions=True) as C:
        >>>     C.lookup(['onumber', 'total'], {'company':'NoCompany', 'region':'Lala Land'})
        >>> [None, None]

        Example - allow_multi=True
        >>> with CRUD('c:/my.gdb', enable_transactions=False) as C:
        >>>     rows = C.lookup(['orders', 'total'], {'company':'Amazon', 'region':'UK'})
        >>>     print(rows[0])
        'ON1235', 24000.123

        """
        if isinstance(cols_to_read, str):
            if not cols_to_read == '*':
                cols_to_read = [cols_to_read]

        where = CRUD._kwargs_where(key_val_dict)
        rows_out = []
        with SearchCursor(self._fname, cols_to_read, where_clause=where) as Cur:
            v = [None] * len(cols_to_read)
            for i, R in enumerate(Cur):
                if i == 1 and not allow_multi:
                    raise _errors.LookUpGotMoreThanOneRow('Lookup %s matched more than a single record in %s' % (key_val_dict, self._fname))
                v = [R[col] for col in cols_to_read]
                if allow_multi:
                    rows_out.append(v)

            if allow_multi:
                return rows_out

            return v



    def upsert(self, search_dict, force_add: bool = False, fail_on_multi: bool = False, fail_on_exists: bool = False, fail_on_not_exists: bool = False, **kwargs):
        """(str, dict, bool, **kwargs)->None|int
        Upsert or insert a record.

        If the record exists, as determined by the key-val records in col_val_dict, then an update is
        generated, otherwise an insert

        col_val_dict is dictionary of key fields and their values used to build the where.

        Args:
            search_dict:
                Builds the where e.g. {'orderid':1, 'supplier':'Widget Company'}
            force_add:
                Force an add, this is necessary when doing an upsert based of non-composite key fields (i.e. members)
            fail_on_multi:
                Raise an error if get more than one row for the update cursor
            fail_on_exists:
                Raise an error the row exists by search_dict
            fail_on_not_exists:
                Raise an error if this should be an update
            kwargs:
                Field/value pairs to insert/update

        Returns:
            (int, None): None if update, returns new OID if a record was inserted.

        Notes:
            For INSERTS, keylist alone can just be populated as a shortcut.
            Also see crud.fieldNamesSpecial which has ESRI's special field names

        Example:
        >>> with CRUD('c:/my.gdb', enable_transactions=True) as C:
        >>>     C.upsert({'orderid':1, 'supplier':'Widget Company'}, orderid=1, supplier='Foo Company')
        >>>     C.upsert({'ordernr':'A1234', 'value':12.35, 'n':5})  # simplified insert

        # Force as update, error if record {'orderid':1, 'supplier':'Widget Company'} does not exist
        >>>     C.upsert({'orderid':1, 'supplier':'Widget Company'}, fail_on_nor_exists=True, orderid=1, supplier='Foo Foo Company')
        """
        i = None
        cols = list(kwargs.keys())
        values = list(kwargs.values())
        where = CRUD._kwargs_where(search_dict)

        # writing back, you have to use Shape@, otherwise you get a null feature
        for i, v in enumerate(cols):
            if v.lower() == 'shape':
                cols[cols.index(v)] = 'Shape@'

        exists = self.exists_by_compositekey(**search_dict)
        if not exists and fail_on_not_exists:
            raise _errors.UpsertExpectedUpdateButMatchedRow('Upsert expected an update but no records matched %s in %s' % (str(search_dict), self._fname))

        if exists and not force_add:
            if not kwargs or fail_on_exists:
                raise _errors.UpsertExpectedInsertButHadMatchedRow(_errors.UpsertExpectedInsertButHadMatchedRow.__doc__)

            if get_row_cnt(self._fname, where) > 1 and fail_on_multi:
                raise _errors.UpdateCursorGotMultipleRecords(_errors.UpdateCursorGotMultipleRecords.__doc__)

            with _da.UpdateCursor(self._fname, cols, where_clause=where) as Cur:
                for row in Cur:
                    for j in range(len(cols)):
                        row[j] = values[j]
                    try:
                        Cur.updateRow(row)
                    except RuntimeError as r:
                        raise RuntimeError('Runtime errors in arcpy cursor operations are usually the result of incorrect column names, mismatched data types, '
                                           'string truncation or locking issues.') from r
        else:
            try:
                if not kwargs:
                    # caller was lazy and wanted a quick insert using search_dict only,
                    # so  use the search cols/vals to add a new row
                    Cur = _da.InsertCursor(self._fname, list(search_dict.keys()))
                    i = Cur.insertRow(list(search_dict.values()))
                else:
                    Cur = _da.InsertCursor(self._fname, cols)
                    i = Cur.insertRow(values)
            except RuntimeError as r:
                raise RuntimeError('Runtime errors in arcpy cursor operations are usually the result of incorrect column names, mismatched data types, '
                                   'string truncation or locking issues.') from r
            finally:
                with _fuckit:
                    del Cur

        return i


    def updatew(self, where: str, **kwargs) -> int:
        """(str, str, **kwargs)->None
        Update 1 or more records matching the SQL where. This is NOT transactionalised.

        Args:
            where (str): SQL where, e.g. "orderid>1 AND supplier='Widget Company'"
            kwargs (any): Field/value pairs to insert/update

        Returns:
            int: Number of rows updated

        Notes:
             CRUD.FieldNamesSpecial is a aide-memoir to ESRI's special field names.

        Examples:
            >>> with CRUD('c:/my.gdb', enable_transactions=True) as C:
            >>>     C.updatew("supplier='Old Widgets' AND address='Old Address'", supplier='New Widgets', Address='New Address')
        """
        cols = list(kwargs.keys())
        values = list(kwargs.values())
        i = 0

        with _da.UpdateCursor(self._fname, cols, where_clause=where) as Cur:
            for row in Cur:
                for j in range(len(cols)):
                    row[j] = values[j]

                try:
                    Cur.updateRow(row)
                    i += 1
                except RuntimeError as r:
                    raise RuntimeError('Runtime errors in arcpy cursor operations are usually the result of mismatched data types,'
                                       ' string truncation or locking issues.') from r
        return i



    def delete(self, fail_on_multi=False, error_on_no_rows=True, **kwargs):
        """(kwargs)->None
        Delete a row or rows.

        fail_on_multi:
            Raise an error if get more than one row for the update cursor
        kwargs:
            Field/value pairs to insert/update

        Example
        >>> with CRUD('c:/my.gdb', enable_transactions=True) as C:
        >>>     C.delete(orderid=1, supplier='Foo Company')
        """
        where = CRUD._kwargs_where(kwargs)
        n = get_row_cnt(self._fname, where)
        if n > 1 and fail_on_multi:
            raise _errors.DeleteMatchedMutlipleRecords(
                'Delete key-value pairs %s matched more than 1 record in feature class %s' % (str(kwargs),
                self._fname)
            )

        if n == 0 and error_on_no_rows:
            raise _errors.DeleteHadNoMatchingRecords(_errors.DeleteHadNoMatchingRecords.__doc__)

        with _da.UpdateCursor(self._fname, ['OID@'], where_clause=where) as Cur:
            for _ in Cur:
                Cur.deleteRow()


    def deletew(self, where: str) -> int:
        """
        Simple delete with custom where

        Args:
            where (str): Record filter. Pass '*' to delete all records.

        Returns:
            int: number of rows deleted

        Examples:
            >>> with CRUD('c:/my.gdb', enable_transactions=True) as C:
            >>>     C.deletew("orderid>100 AND supplier='Foo Company'")
            12
        """
        i = 0
        if where == '*':
            where = None

        with _da.UpdateCursor(self._fname, ['OID@'], where_clause=where) as Cur:
            for row in Cur:
                Cur.deleteRow()
                i += 1
        return i



    def tran_begin(self):
        """begin trans
        does a commit if in an existing transaction
        """
        if not self._editor:
            _warn('tran_begin was called, but there was no editor object (self._editor is None)')
            return

        if self._fname[-4:] == '.shp':
            _warn('Shapefiles do not support editing operations. Changes occur immediately. CRUD cannot be rolled back')

        if self._editor.isEditing:
            self.tran_commit()

        self._editor.startEditing(False, False)
        self._editor.startOperation()


    def tran_rollback(self):
        """rollback"""
        if not self._editor:
            _warn('tran_rollback was called, but there was no editor object (self._editor is None)')
            return

        with _fuckit:
            self._editor.abortOperation()
            self._editor.stopEditing(False)


    def tran_commit(self):
        """committrans"""
        if not self._editor:
            _warn('tran_rollback was called, but there was no editor object (self._editor is None)')
            return

        with _fuckit:
            if self._editor.isEditing:
                self._editor.stopOperation()
                self._editor.stopEditing(True)


    @staticmethod
    def _read_col(row, colname):
        """(class:Row, str)->any
        reads a cursor row column value
        returns None if there is no row
        First row only
        """
        if not row:
            return None
        return row[colname]

    @staticmethod
    def _kwargs_where(kwargs_dict):
        """(dict)->str
        Return where generated from keyword arguments

        Example:
        >>> CRUD._kwargs_where({'county':'Anglesey', 'population':10000})
        county='Anglesey' AND population=10000
        """
        where = ["%s=%s AND " % (j, CRUD._f(k)) for j, k in kwargs_dict.items() if j.lower() != 'shape@']
        where[-1] = where[-1].replace('AND', '')
        where = "".join(where)
        return where

    @staticmethod
    def _f(v):
        """fix vals"""
        if isinstance(v, str):
            return "'%s'" % v
        return str(v)
