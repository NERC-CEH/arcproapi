"""Structural stuff, like deleting or renaming cols, and functions that query structure related properties"""
import os.path as _path
import fnmatch as _fnmatch

import arcpy.management
import pandas as _pd
import fuckit as _fuckit

import arcpy as _arcpy

import funclite.iolib as _iolib
import funclite.baselib as _baselib

import arcapi.common as _common
from arcapi.common import get_row_count2 as rowcnt  # noqa


import arcapi.environ as _environ
import arcapi.errors as _errors


field_add = arcpy.management.AddField  # expose here
fields_add = arcpy.management.AddFields  # expose here

def field_oid(fname):
    """Return name of the object ID field in table table"""
    return _arcpy.Describe(fname).OIDFieldName


def field_shp(fname):
    """(str)->str
    Return name of the Shape (Geometry) field in feature class fname

    Args:
        fname (str): path to feature class/table etc.

    Returns:
         str: Name of the shape/geometry field
    """
    D = _arcpy.Describe(fname).shapeFieldName
    return D


def field_delete_not_in(fname, not_in):
    """
    Delete all fields not in not_in

    Args:
        fname (str): path to feature class
        not_in (iter): iterable of field names to keep

    Examples:
        >>> field_delete_not_in('c:\lyr.shp', ('cola', 'colb'))
     """
    not_in = [s.lower() for s in not_in]
    fname = _path.normpath(fname)
    flds = [fld.name for fld in _arcpy.ListFields(fname) if fld.name.lower() not in not_in and not fld.required]
    _arcpy.DeleteField_management(fname, flds)


def fc_delete(fname: str) -> bool:
    """Deletes a table or feature class

    Returns: bool: False if x does not exist, True if x exists and was deleted.
    """
    deletted = False
    if _arcpy.Exists(fname):
        _arcpy.Delete_management(fname)
        deletted = True
    return deletted


def fc_delete2(fname: str, err_on_not_exists: bool = False, data_type: str = None) -> None:
    """Deletes a table or feature class

    Args:
        fname (str): feature class or table path
        err_on_not_exists (bool): raise an error if featureclass/table does not exist
        data_type (str): data type to delete, see https://pro.arcgis.com/en/pro-app/2.9/tool-reference/data-management/delete.htm

    Raises:
        arcpy.ExecuteError: Raised if err_on_no_field and the field does not exist
        Other exceptions should raise an error as normal (which may also be arcpy.ExecuteError

    Returns: None

    Examples:
        >>> fc_delete2('c:/my.gdb/this_does_not_exist', err_on_not_exists=False)
    """
    try:
        _arcpy.management.Delete(fname, data_type=data_type)
    except _arcpy.ExecuteError as e:
        if 'does not exist' in str(e):
            if err_on_not_exists:
                raise _arcpy.ExecuteError('%s does not exist' % fname) from e
        else:
            raise _arcpy.ExecuteError from e




def fcs_delete(fnames, err_on_not_exists=False):
    """_arcpy.Delete_management(x) if _arcpy.Exists(x).
    Args:
        fnames (list, tuple): iterable of feature class or table path names
        err_on_not_exists (bool): raise an error if field does not exist in fname

    Raises: Raises an error if err_on_not_exists and an error occurs

    Examples:
        >>> fcs_delete(['c:/my.gdb/layer1', 'c:/my.gdb/layer2'])
    """
    for fname in fnames:
        try:
            fc_delete2(fname, err_on_not_exists)
        except Exception as e:
            if err_on_not_exists:
                raise e


def cleanup(fname_list, verbose=False, **args):
    """Delete items in x and return number of items that could not be deleted.

    This function uses the dlt function, which in turn uses
    _arcpy. Exists and _arcpy.management.Delete. The deletion is wrapped in a try
    statement so failed deletions are skipped silently.

    Required:
    x -- iterable of items to delete

    Optional:
    verbose -- suppress messages if False (default), otherwise print messages
    **args -- keyword arguments 'timef' and 'log' for function 'msg'

    Example:
    >>> cleanup(['c:\\foo\\bar.shp', 'lyr', 'c:\\foo\\eggs.tif'])
    """
    cnt = 0
    for i in fname_list:
        try:
            deleted = fc_delete(i)
        except:
            deleted = False
        if deleted:
            m = "Cleanup deleted " + str(i)
        else:
            m = "Cleanup could not delete " + str(i)
        _common.msg(m, args.get('timef', '%Y-%m-%d %H:%M:%S'), verbose, args.get('log', None))
    return cnt


def fcs_list_all(gdb, wild='*', ftype='All', rel=False):
    """Return a list of all feature classes in a geodatabase.

    if rel is True, only relative paths will be returned.  If
    false, the full path to each feature classs is returned
    Relative path Example:

    Utilities\Storm_Mh
    Utilities\Storm_Cb
    Transportation\Roads


    Args:
        gdb (str): Geodatabase containing feature classes to be listed
        wild (str): wildcard for feature classes. Default is "*"
        ftype (str):  feature class type. Default is 'All'
                 Valid values:

                 Annotation - Only annotation feature classes are returned.
                 Arc - Only arc (or line) feature classes are returned.
                 Dimension - Only dimension feature classes are returned.
                 Edge - Only edge feature classes are returned.
                 Junction - Only junction feature classes are returned.
                 Label - Only label feature classes are returned.
                 Line - Only line (or arc) feature classes are returned.
                 Multipatch - Only multipatch feature classes are returned.
                 Node - Only node feature classes are returned.
                 Point - Only point feature classes are returned.
                 Polygon - Only polygon feature classes are returned.
                 Polyline - Only line (or arc) feature classes are returned.
                 Region - Only region feature classes are returned.
                 Route - Only route feature classes are returned.
                 Tic - Only tic feature classes are returned.
                 All - All datasets in the workspace. This is the default value.
                 Table - Only tables
        rel (bool): Option to have relative paths. Default is false;
               will include full paths unless rel is set to True

    Returns:
          List: List of all feature class paths

    Examples:
       >>> # Return relative paths for fc
        >>> gdb_ = r'C:\TEMP\test.gdb'
        >>> for fc in getFCPaths(gdb_, rel=True):  # noqa
        >>>     pass
    """
    # feature type (add all in case '' is returned
    # from script tool
    if not ftype:
        ftype = 'All'
    _arcpy.env.workspace = gdb

    # loop through feature classes
    feats = []

    # Add top level fc's (not in feature data sets)
    feats += _arcpy.ListFeatureClasses(wild, ftype)

    # loop through feature datasets
    for fd in _arcpy.ListDatasets('*', 'Feature'):
        _arcpy.env.workspace = _environ.workspace_set(_path.normpath(_path.join(gdb, fd)))
        feats += [_path.join(fd, fc) for fc in
                  _arcpy.ListFeatureClasses(wild, ftype)]

    # return list of features, relative pathed or full pathed
    if rel:
        return sorted(feats)
    else:
        return sorted([_path.join(gdb, ft) for ft in feats])

def field_list_compare(fname: str, col_list: list, **kwargs):
    """Compare the field list from fname with col_list
    returning the symetric difference as a dic

    Args:
        fname (str): feature class
        col_list (list): list of col names to check
        **kwargs (any): keyword args to pass to struct.fieldlist

    Returns:
        dict: {'a_notin_b':[..], 'a_and_b':[...], 'b_notin_a':[...]},
        where "a" is the feature class cols and "b" is the cols from col_list
        .. so in_feature_class, in_both, in_list

    Examples:
        >>> field_list_compare('c:/my.gdb/lyr', ['OBJECTID', 'colb', 'colc'], shape=True)
        {'a_notin_b':['fname_col1'], 'a_and_b':['OBJECTID'], 'b_notin_a':['colb','colc']}
    """
    dbcols = field_list(fname, **kwargs)
    return _baselib.list_sym_diff(dbcols, col_list)


def field_list(fname, cols_exclude=(), oid=True, shape=True, objects=False, func=lambda s: s, **kwargs) -> list:
    """Return a list of fields or a list of field objects on input feature class.

    This function will handle list comprehensions to either return field names
    or field objects. Object ID and Geometry fields are omitted by default.

    Args:
        fname (str): Feature class, feature layer,  table, or table view
        cols_exclude (str, list): column names to exclude
        oid (bool): If False, will exclude the primary key field
        shape (bool): If false, will exclude the Geometry field
        objects (bool): True, will return field objects, else
                    field names. Field objects have field properties.
                     e.g. field.name, field.type, field.length
        func (any): A function applied to returned field list, e.g. str.lower
        kwargs: keyword arguments used to filter by arcpy field properties.
                isNullable, editable, aliasName, required, type
                Fields without matching properties are all excluded.
                Operations is AND'ed, ie all conditions must be true to keep the Field
                See https://pro.arcgis.com/en/pro-app/latest/arcpy/classes/field.htm

    Returns:
        (list): An iterable of col names or fields

    Examples:
        >>> field_list(r'C:\Temp\Counties.shp', ['STATE_FIPS', 'COUNTY_CODE'], objects=True)
        [<Field1>, <Field2>, ...]

        strings not objects please
        >>> field_list(r'C:\Temp\Counties.shp', ['STATE_FIPS', 'COUNTY_CODE'], objects=False)
        ['OBJECTID', 'STATE', ....]

        Passing kwarg type='OID'
        >>> field_list(r'C:\Temp\Counties.shp', ['STATE_FIPS', 'COUNTY_CODE'], objects=False, type='OID')
        ['OBJECTID']
    """

    def _filt_fld(fld):
        """(Obj:arcpy.Field)->bool
        filter based on property and kwargs"""
        if not kwargs: return True
        keep = True
        for k, v in kwargs.items():
            if field_get_property(fld, k) != v:
                keep = False
                break
        return keep

    if isinstance(cols_exclude, str):
        cols_exclude = (cols_exclude,)

    # add exclude types and exclude fields
    if not oid:
        cols_exclude.append(_common.get_id_col(fname))  # noqa
    if not shape:
        cols_exclude.extend(['Geometry', 'Shape'])  # noqa

    exclude = map(lambda x: x.lower(), cols_exclude)

    # return either field names or field objects
    if objects:
        return [f for f in _arcpy.ListFields(fname)
                if f.name.lower() not in exclude and _filt_fld(f)]
    else:
        return [func(f.name) for f in _arcpy.ListFields(fname)
                if f.name.lower() not in exclude and _filt_fld(f)]


def field_type_get(in_field, fc=''):
    """Converts esri field type returned from list fields or describe fields
    to format for adding fields to tables.

    Required:
    in_field -- field name to find field type. If no feature class
        is specified, the in_field paramter should be a describe of
        a field.type

    Optional:
    fc -- feature class or table.  If no feature class is specified,
        the in_field paramter should be a describe of a field.type

    Example
    >>> # field type of 'String' needs to be 'TEXT' to be added to table
    >>> # This is a text type field
    >>> # now get esri field type
    >>> print getFieldType(table, 'PARCEL_ID') #esri field.type return is 'String', we want 'TEXT'  # noqa
    TEXT
    """
    if fc:
        field = [f.type for f in _arcpy.ListFields(fc) if f.name == in_field][0]
    else:
        field = in_field
    if field in _common.lut_field_types:
        return _common.lut_field_types[field]
    else:
        return None


def fields_get(table_or_list, match='*', multi: bool = True):
    """Return a list of field objects where name matches the specified pattern.

    Args:
        table_or_list: input table or feature class or list of fields
        match (str):pattern to match to field
        multi (bool): If True, will return a list of all matches, if false, will raise ValueError

    Returns:
        (list, None, arcpy.Field): Returns a list of Fields, a single Field or None.

    Raises:
        StructMultipleFieldMatches: If multi was False and more than one field matched 'match'

    Examples:
        >>> fields_get(r'C:\Temp\Counties.shp', 'county_*', multi=True)
        ['COUNTY_CODE', 'COUNTY_FIPS']

        >>> fields_get(r'C:\Temp\Counties.shp', 'county_*', multi=False)
        Traceback (most recent call last):
            File: ....
        StructMultipleFieldMatches ...
    """
    if isinstance(table_or_list, list):
        fields = table_or_list
    else:
        fields = [f.name for f in _arcpy.ListFields(table_or_list)]

    all_mats = []
    for f in fields:
        if _fnmatch.fnmatch(f, match):
            all_mats.append(f)

    if not all_mats: return None
    if multi: return all_mats

    if len(all_mats) > 1:
        raise _errors.StructMultipleFieldMatches('Multiple fields matched, expected a single field match')

    return all_mats[0]


def fields_add_from_table(target, source, add_fields):
    """Add fields (schema only) from one table to another

    Args:
        target (str): target table to which the field will be added
        source (str): source table containing fields to add to "target"
        add_fields (str, list, tuple): fields from template table to add to input table (list),
                                        also support strings delimited by ;

    Examples:
        >>> fields_add_from_table(parcels, permits, ['Permit_Num', 'Permit_Date'])  # noqa
    """

    # fix args if args from script tool
    if isinstance(add_fields, str):
        add_fields = add_fields.split(';')

    # grab field types
    f_dict = dict((f.name, [field_type_get(f.type), f.length, f.aliasName]) for f in _arcpy.ListFields(source))

    # Add fields
    for field in add_fields:
        f_ob = f_dict[field]
        _arcpy.AddField_management(target, field, f_ob[0], field_length=f_ob[1], field_alias=f_ob[2])


def field_name_create(fname: str, new_field: str) -> str:
    """Return a unique and valid field name in feature class/table fname
    derived from new_field

    Args:
        fname (str): feature class, feature layer, table, or table view
        new_field (str): new field name, will be altered if field already exists

    Returns: str: New field name

    Example:
        >>> fname = 'c:\\testing.gdb\\ne_110m_admin_0_countries'  # noqa
        >>> field_name_create(fname, 'NEWCOL')
        'NEWCOL'
        >>> field_name_create(fname, 'Shape')
        'Shape_1'
    """

    # if fc is a table view or a feature layer, some fields may be hidden;
    # grab the data source to make sure all columns are examined
    fname = _arcpy.Describe(fname).catalogPath
    new_field = _arcpy.ValidateFieldName(new_field, _path.dirname(fname))

    # maximum length of the new field name
    maxlen = 64
    dtype = _arcpy.Describe(fname).dataType
    if dtype.lower() in ('dbasetable', 'shapefile'):
        maxlen = 10

    # field list
    fields = [f.name.lower() for f in _arcpy.ListFields(fname)]

    # see if field already exists
    if new_field.lower() in fields:
        count = 1
        while new_field.lower() in fields:

            if count > 1000:
                raise _errors.ArcapiError('Maximum number of iterations reached in uniqueFieldName.')

            if len(new_field) > maxlen:
                ind = maxlen - (1 + len(str(count)))
                new_field = '{0}_{1}'.format(new_field[:ind], count)
                count += 1
            else:
                new_field = '{0}_{1}'.format(new_field, count)
                count += 1
    return new_field


def fields_concatenate(fname: str, new_field: str, length: int, fields: (tuple, list), delimiter: str = '', number_only: bool = False) -> str:
    """Create a new field in a table and concatenate user defined fields.

    This can be used in situations such as creating a Section-Township-Range
    field from 3 different fields.
    Returns the field name that was added.

    Args:
        fname (str): Input table
        new_field (str): new field name
        length (int): field length
        fields (tuple, list): list of fields to concatenate
        delimiter (str): join value for concatenated fields, eg '-' so all fields dash delimited
        number_only (bool): if True, only extract numeric values from a text field

    Returns:
        str: The name of the new field

    Examples:
        >>> fields_concatenate('my.shp', 'SEC_TWP_RNG', 15, ['SECTION', 'TOWNSHIP', 'RANGE'], '-')
        'SEC_TWP_RNG'

    TODO: Debug/test fields_concatenate
    """

    # Add field
    new_field = field_name_create(fname, new_field)
    _arcpy.AddField_management(fname, new_field, 'TEXT', field_length=length)

    # Concatenate fields
    if _arcpy.GetInstallInfo()['Version'] != '10.0':
        # da cursor
        with _arcpy.da.UpdateCursor(fname, fields + [new_field]) as rows:  # noqa
            for r in rows:
                r[-1] = _common.concatenate(r[:-1], delimiter, number_only)
                rows.updateRow(r)

    else:
        # 10.0 cursor
        rows = _arcpy.UpdateCursor(fname)
        for r in rows:
            r.setValue(new_field, _common.concatenate([r.getValue(f) for f in fields], delimiter, number_only))
            rows.updateRow(r)
        del r, rows
    return new_field


def fcs_schema_compare(fname1, fname2, sortfield, as_df=True):
    """

    Args:
        fname1: name of first feature class
        fname2: name of second feature class
        sortfield: sortfield, required, must be common to both
        as_df: return a dataframe or a printable string of the comparison results

    Returns:
        pandas.DataFrame: if as_df is true, return a pandas dataframe of the differences
        str: if as_df was false, just get a printable string of the differences

    Examples:
        >>> fcs_schema_compare('c:/my.gdb/fc1', 'c:/my.gdb/fc2', 'country', as_df=False)
        Start Time: 14 February 2022 15:02:23
        Table: Table fields do not match.
        Field: Field is Shape nullable is different ....

        >>> df = fcs_schema_compare('c:/my.gdb/fc1', 'c:/my.gdb/fc2', 'country', as_df=True)  # noqa
        >>> xlwings.view(df)  # noqa
    """
    fname1 = _path.normpath(fname1)
    fname2 = _path.normpath(fname2)
    if as_df:
        out_name = _iolib.get_temp_fname()
        out = _arcpy.management.TableCompare(fname1, fname2, sortfield, 'SCHEMA_ONLY',
                                             ignore_options=['IGNORE_EXTENSION_PROPERTIES', 'IGNORE_SUBTYPES ', 'IGNORE_RELATIONSHIPCLASSES', 'IGNORE_FIELDALIAS'],
                                             continue_compare=True, out_compare_file=out_name)
        df = _pd.read_csv(out_name)
        _iolib.file_delete(out_name)
        return df
    else:
        out = _arcpy.management.TableCompare(fname1, fname2, sortfield, 'SCHEMA_ONLY',
                                             ignore_options=['IGNORE_EXTENSION_PROPERTIES', 'IGNORE_SUBTYPES ', 'IGNORE_RELATIONSHIPCLASSES', 'IGNORE_FIELDALIAS'],
                                             continue_compare=True)
        return out.getMessages()

def fcs_field_sym_diff(fname1, fname2, ignore_case=True):
    """Show field differences

    Args:
        fname1 (str): feature class 1
        fname2 (str) feature class 2

    Returns:
        dict: Dictionary of items in 1 not in 2, items in 1 and 2, items in 2 not in 1. See example.

    Examples:
        >>> fcs_field_sym_diff('c:/my.gdb/lyr1', 'c:/my.gdb/lyr2')
        {'a_notin_b':['colA1', 'colA2'], 'a_and_b':['colAB'], 'b_notin_a':['colB1', colB2']}
    """
    fname1 = _path.normpath(fname1)
    fname2 = _path.normpath(fname2)

    if ignore_case:
        lst1 = fields_get(fname1)
        lst2 = fields_get(fname2)
    else:
        lst1 = [s.lower() for s in fields_get(fname1, match='*')]
        lst2 = [s.lower() for s in fields_get(fname2, match='*')]

    return _baselib.list_sym_diff(lst1, lst2)


def fc_schema_copy(template, new, sr=''):
    """Copy the schema (field definition) of a feature class or a table.

    Required:
    template -- template table or fc
    new -- new output fc or table

    Optional:
    sr -- spatial reference (only applies if fc) If no sr
          is defined, it will default to sr of template.

    Example:
    >>> fc_schema_copy(r'C:\Temp\soils_city.shp', r'C:\Temp\soils_county.shp')
    """
    path, name = _path.split(new)
    desc = _arcpy.Describe(template)
    ftype = desc.dataType
    if 'table' in ftype.lower():
        _arcpy.CreateTable_management(path, name, template)
    else:
        stype = desc.shapeType.upper()
        sm = 'SAME_AS_TEMPLATE'
        if not sr:
            sr = desc.spatialReference
        _arcpy.CreateFeatureclass_management(path, name, stype, template, sm, sm, sr)
    return new


def table_to_points(tbl, out_fc, xcol, ycol, sr, zcol='#', w=''):
    """Convert table to point feature class, return path to the feature class.

    Required:
    tbl -- input table or table view
    out_fc -- path to output feature class
    xcol -- name of a column in tbl that stores x coordinates
    ycol -- name of a column in tbl that stores y coordinates
    sr -- spatial reference for out_fc
        sr can be either _arcpy.SpatialReference object or a well known id as int

    Optional:
    zcol -- name of a column in tbl that stores y coordinates, default is '#'
    w -- where clause to limit the rows of tbl considered, default is ''

    Example:
    >>> t = 'c:\\foo\\bar.shp'
    >>> o = 'c:\\foo\\bar_pts.shp'
    >>> table_to_points(t, o, "XC", "YC", 4326, zcol='#', w='"FID" < 10')  # noqa
    >>> table_to_points(t, o, "XC", "YC", _arcpy.SpatialReference(27700))  # noqa
    >>> table_to_points(t, o, "XC", "YC", _arcpy.describe(tbl).spatialReference)  # noqa
    """
    lrnm = _common.tstamp('lr', '%m%d%H%M%S', '')
    if type(sr) != _arcpy.SpatialReference:
        sr = _arcpy.SpatialReference(sr)
    lr = _arcpy.MakeXYEventLayer_management(tbl, xcol, ycol, lrnm, sr, zcol).getOutput(0)
    if str(w) not in ('', '*'):
        _arcpy.SelectLayerByAttribute_management(lr, "NEW_SELECTION", w)
    out_fc = _arcpy.CopyFeatures_management(lr, out_fc).getOutput(0)
    fc_delete(lr)
    return _arcpy.Describe(out_fc).catalogPath


def field_rename(tbl, col, newcol, alias=''):
    """Rename column in table tbl and return the new name of the column.

    This function first adds column newcol, re-calculates values of col into it,
    and deletes column col.
    Uses _arcpy.ValidateFieldName to adjust newcol if not valid.
    Raises ArcapiError if col is not found or if newcol already exists.

    Required:
    :param tbl: -- table with the column to rename
    :param col: -- name of the column to rename
    :param newcol:  -- new name of the column

    Optional:
    :param alias: -- field alias for newcol, default is '' to use newcol for alias too
    :return name of new column
    :rtype: str
    :raises ArcapiError: If col does not exist or newcol already exists
    """
    if col != newcol:
        d = _arcpy.Describe(tbl)
        dcp = d.catalogPath
        flds = _arcpy.ListFields(tbl)
        fnames = [f.name.lower() for f in flds]
        newcol = _arcpy.ValidateFieldName(newcol, tbl)  # _path.dirname(dcp))
        if col.lower() not in fnames:
            raise _errors.ArcapiError("Field %s not found in %s." % (col, dcp))
        if newcol.lower() in fnames:
            raise _errors.ArcapiError("Field %s already exists in %s" % (newcol, dcp))
        oldF = [f for f in flds if f.name.lower() == col.lower()][0]
        if alias == "": alias = newcol
        _arcpy.AddField_management(tbl, newcol, oldF.type, oldF.precision, oldF.scale, oldF.length, alias, oldF.isNullable, oldF.required, oldF.domain)
        _arcpy.CalculateField_management(tbl, newcol, "!" + col + "!", "PYTHON_9.3")
        _arcpy.DeleteField_management(tbl, col)
    return newcol


def field_get_property(fld, property_):
    """(Obj, str)->any|None
    This gets a property from an arcpy field describe object from a string.
    Field describe objects are simply the objects returned from a ListFields call

    This is necessary to support other lib functions to get the property with late binding,
    because the Describe object exposes nothing! No __dict__, getattr() etc

    Args:
        param fld: The field object (ListField outputs)
        param property_: The property name, eg. 'isNullable'. See https://pro.arcgis.com/en/pro-app/latest/arcpy/classes/field.htm

    Returns: any (the value of the property), or None of property is not a member of fld

    Examples:
        >>> field_get_property(field_list('c:/my.shp', objects=True)[0], 'type')
        'OID'
    """
    p = property_.lower()
    if p == 'aliasName': return fld.aliasName
    if p == 'basename': return fld.baseName
    if p == 'defaultvalue': return fld.defaultValue
    if p == 'domain': return fld.domain
    if p == 'editable': return fld.editable
    if p == 'isnullable': return fld.isNullable
    if p == 'length': return fld.length
    if p == 'name': return fld.name
    if p == 'precision': return fld.precision
    if p == 'required': return fld.required
    if p == 'scale': return fld.scale
    if p == 'type': return fld.type
    return None


def geodb_dump_struct(gdb: str, wild_lyr: str = '*', ftype='All'):
    """dump the structure of a geodb to excel"""
    # TODO Implement geodb_dump_struct
    out = {'lyr': [], 'fld': [], 'type': []}

    def _add_fld(fc_, fld_):
        out['lyr'].append(fc_)
        out['fld'].append(fld_.name)
        out['type'].append(fld_.type)

    for fc in fcs_list_all(gdb, wild=wild_lyr, ftype=ftype, rel=False):
        for fld in field_list(fc, objects=True):
            pass


def geodb_find_cols(gdb, col_name, partial_match=False):
    """
    List cols in a geodb that match col_name, useful for "soft" relationships

    Args:
        gdb:
        col_name:
        partial_match:

    Returns: dict: Dictionary like {'lyr':[...], 'col':[...], 'type':[...]}

    Examples:
        >>> geodb_find_cols('c:/my.gdb', 'OBJECTID')
        {'lyr': ['lyr1', 'lyr2'], 'col': ['OBJECTID', 'OBJECTID'], 'type': ['integer','integer']}
    """
    out = {'lyr': [], 'fld': [], 'type': []}

    def _add_fld(fc_, fld_):
        if fld_.name.lower() in fld_.lower():
            if partial_match:
                out['lyr'].append(fc_)
                out['fld'].append(fld_.name)
                out['type'].append(fld_.type)
            elif len(col_name) == len(fld_):
                out['lyr'].append(fc_)
                out['fld'].append(fld_.name)
                out['type'].append(fld_.type)

    for fc in fcs_list_all(gdb, rel=False):
        for fld in field_list(fc, objects=True):
            _add_fld(fc, fld)

    for tbl in _arcpy.ListTables():
        for fld in field_list(tbl, objects=True):
            _add_fld(tbl, fld)

    return out


def excel_import_worksheet(xls: str, fname: str, worksheet: str, header_row=1, overwrite: bool = False, data_type: str = '', **kwargs) -> None:
    """
    Import an excel spreadsheet as a table into a gdb.

    Args:
        xls (str): path to excel
        fname (str): fully qualified path to the table to create
        worksheet (str): excel worksheet name
        header_row (int): header row
        overwrite (bool): Allow overwrite. If false and fname exists, an error will be raised
        data_type (str): Passed to arcpy.management.Delete, required if expecting more than 1 layer with the same name in the geodb.
        kwargs: keyword args passed to arcpy.conversion.ExcelToTable

    Raises:
        FileNotFoundError: If the excel file does not exist

    Returns: None

    Notes:
        See See https://pro.arcgis.com/en/pro-app/latest/tool-reference/data-management/delete.htm for data_type values.
    """
    xls = _path.normpath(xls)
    fname = _path.normpath(fname)

    if not _iolib.file_exists(xls):  # important we raise an error if file DOES NOT exists, otherwise we'd delete the table without anything the data to replace it
        raise FileNotFoundError('Excel file %s does not exist' % xls)

    if overwrite:
        with _fuckit:
            _arcpy.management.Delete(fname, data_type=data_type)

    _arcpy.conversion.ExcelToTable(xls, fname, worksheet, 1, '', **kwargs)
