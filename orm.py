# pylint: disable=import-error,useless-super-delegation
"""Various functions to help create ORM/CRUD classes to work
with feature classes and tables

See test/test_orm for examples of use"""
from warnings import warn as _warn
from collections import defaultdict as _ddict
from enum import Enum as _Enum

import fuckit as _fuckit
import arcpy as _arcpy
import pyperclip as _clip
import pandas as _pd

import arcapi.struct as _struct
import arcapi.errors as _errors
import arcapi.crud as _crud
import arcapi.common as _common

import funclite.iolib as _iolib
import funclite.baselib as _baselib
import funclite.stringslib as _stringslib


class EnumLogAction(_Enum):
    add = 1
    update = 2
    delete = 3


class EnumMembers(_Enum):
    """enum"""
    oid = 1
    composite_key = 2
    members = 4
    in_db_not_members = 8
    all_members = 4 + 2 + 1


def class_def_to_clip(fname, workspace='None', composite_key_cols='()', short_super=True):
    """(str, str, list|str)->s

    Get columns from feature class/table fname and create
     a class definition based on _BaseORM

     Args:
        fname: path to feature class/table etc
        workspace: path to workspace, e.g. geodatabase
        composite_key_cols: either a list:str definining a composite key or a string representing that list
        .
        short_super:
            set the members up in the created class,
            rather than passing to super() to set in the parent class

     Returns:
        str: the class definition as a string


     Examples:
        >>> import arcapi.orm as orm
        >>> import erammp.config as config
        >>> orm.class_def_to_clip(config.GeoDatabaseLayersAndTables.address_crn_lpis_sq, ('crn', 'plotid'), config.GeoDatabasePaths.erampp)  # noqa
    """
    if short_super:
        s = class_def2(fname, composite_key_cols, workspace)
    else:
        s = class_def(fname, composite_key_cols, workspace)
    _clip.copy(s)
    print('Copied to clipboard')
    return s



def class_def(fname: str, composite_key_cols: (str, list), workspace: str,
              exclude: tuple = ('Shape_Length', 'Shape_Area', 'created_date', 'last_edited_date')
              ) -> str:
    """
    Create a static class definition from a feature class.
    Used to quickly make class definitions to include in code

    Args:
        fname (str): feature class/table name
        composite_key_cols (str, list): key column(s)
        workspace: path to gdb to use as workspace
        exclude (tuple): tuple of cols to exclude form the orm statement - this would be cols that are automatically managed by arcgis

    Returns:
        str: the class definition as a string

    Notes:
        Use class_def_to_clip to copy the definition to the clipboard, ready to be pasted.

    Examples:
        >>> import arcapi.orm as orm
        >>> s = orm.class_def('c:/my.gdb/mytable', workspace='c:/my.gdb', composite_key_cols='myID')
        >>> print(s)
        'class AddressXlsxAddressJoinConsentForm(_orm.ORM): .....'
    """
    fname = fname

    if workspace: workspace = workspace
    if isinstance(composite_key_cols, list):
        composite_key_cols = str(composite_key_cols)
    elif isinstance(composite_key_cols, str) and '(' not in composite_key_cols and ')' not in composite_key_cols and \
            '[' not in composite_key_cols and ']' not in composite_key_cols:
        composite_key_cols = "['%s']" % composite_key_cols

    class_dec = 'class %s(_orm.ORM):\n\t"""class %s"""' % (_make_class_name(fname), _make_class_name(fname))
    class_dec = class_dec + '\n\tfname = %s' % fname   # ("'%s'" % fname)
    class_dec = class_dec + '\n\tcomposite_key_cols = %s' % composite_key_cols
    class_dec = class_dec + '\n\tworkspace = %s' % ("'%s'" % workspace)
    class_dec = class_dec + '\n\n'

    init_str = '\tdef __init__(self, is_edit_session=False, enable_log=True, #):\n'

    init_args = []
    members = []
    for fld in _struct.field_list(fname, objects=True):  # type:_arcpy.Field
        if fld.baseName.lower() not in map(str.lower, exclude):
            init_args.append('%s=None' % fld.baseName)

            members.append('%s=%s' % (fld.baseName, fld.baseName))

    super_ = '\t\tsuper().__init__(%s, %s, %s, %s' % ('%s.fname' % _make_class_name(fname),
                                                      '%s.composite_key_cols' % _make_class_name(fname),
                                                      '%s.workspace' % _make_class_name(fname),
                                                      'is_edit_session=is_edit_session, enable_log=enable_log,\n\t'
                                                      )
    super_ = super_ + _stringslib.join_newline(members, ', ')
    super_ = super_ + ')'

    #  loop init line over multiple rows...
    for v in [init_args[x] for x in range(3, len(init_args), 3)]:
        with _fuckit:
            init_args[init_args.index(v)] = '\n%s' % init_args[init_args.index(v)]

    init_str = init_str.replace('#', ', '.join(init_args))
    # memb_str = '\n\t\t'.join(members)
    hdr = class_dec + init_str + super_

    return hdr


def class_def2(fname, composite_key_cols, workspace,
               exclude=('Shape_Length', 'Shape_Area', 'created_date', 'last_edited_date')
               ):
    """(str)->str
    Create a static class definition from a feature class.

    Used to quickly make class definitions to include in code
    """

    fname = fname
    if workspace: workspace = workspace
    if isinstance(composite_key_cols, list):
        composite_key_cols = str(composite_key_cols)
    elif isinstance(composite_key_cols, str) and '(' not in composite_key_cols and ')' not in composite_key_cols and \
            '[' not in composite_key_cols and ']' not in composite_key_cols:
        composite_key_cols = "['%s']" % composite_key_cols

    class_dec = 'class %s(_orm.ORM):\n\t"""class %s"""' % (_make_class_name(fname), _make_class_name(fname))
    class_dec = class_dec + '\n\tfname = %s' % ("'%s'" % fname)
    class_dec = class_dec + '\n\tcomposite_key_cols = %s' % composite_key_cols
    class_dec = class_dec + '\n\tworkspace = %s' % ("'%s'" % workspace)
    class_dec = class_dec + '\n\n'

    init_str = '\tdef __init__(self, is_edit_session=False, #):\n'

    init_args = []
    members = []
    for fld in _struct.field_list(fname, objects=True):  # type:_arcpy.Field
        if fld.baseName.lower() not in map(str.lower, exclude):
            init_args.append('%s=None' % fld.baseName)
            members.append('\t\tself.%s = %s' % (fld.baseName, fld.baseName))

    super_ = ('\t\tsuper().__init__(%s, %s, %s, %s, %s)' %
              ('%s.fname' % _make_class_name(fname),
               '%s.composite_key_cols' % _make_class_name(fname),
               '%s.workspace' % _make_class_name(fname),
               'is_edit_session=is_edit_session',
               'enable_log=False'
               )
              )

    members.append(super_)

    #  loop init line over multiple rows...
    for v in [init_args[x] for x in range(3, len(init_args), 3)]:
        with _fuckit:
            init_args[init_args.index(v)] = '\n%s' % init_args[init_args.index(v)]

    init_str = init_str.replace('#', ', '.join(init_args))
    memb_str = '\n\t\t'.join(members)
    hdr = class_dec + init_str + memb_str

    return hdr


def _is_key(fld):
    """is_key_field"""
    return fld.name.lower() in ('oid', 'objectid,', 'fid')


def _make_class_name(fname, split_='_'):
    """get class name"""
    if '/' in fname or '\\' in fname:
        _, fname, _ = _iolib.get_file_parts(fname)
    fname = ''.join(map(str.capitalize, fname.split(split_)))
    return fname


class ORM(_crud.CRUD):
    """
    Reload class after changing member values, can optionally provide keyword arguments to set those values.
    Values can also be changed by using members or treating the class as an indexed iterable.

    *** Before a call to update, ENSURE you first read in values UNLESS you know what you are doing ***

    Parameters:
        composite_key_cols (list): iterable of composite_key_cols
        workspace (str): A workspace (e.g. geodb path) in which edit sessions (transactions) are managed
        enable_transactions (bool): Create with an edit session (required to work with transactions)
        update_read_check: Performing an update without a prior read risks overwriting values with None. If true, an update can only occur if you have called .read.
        enable_log (bool): If false then there will be no attempt to write to the corresponding log featureclass/table
        kwargs (kwargs): keword arguments to set member values prior to refresh

    Notes:
        Shapefiles an autoincremental primary key named OID, GDBs use OBJECTID.

    Examples:
        >>> B = ORM('c:/my.gdb/mylayer', ['userid', 'username'], userid='mhunt', username='mike hunt')
        >>> # B.dowork....

        #Update a record using a composite key
        >>> with ORM('c:/my.gdb/mylayer', ['userid', 'username'], workspace='c:/my.gdb', userid='mhunt', username='mike hunt', tel=None) as B:
        >>>     B.tel = '01234 5678'
        >>>     B.update()

        >>> with ORM('c:/my.gdb/mylayer', userid='mhunt', username='mike hunt') as B:
        >>>     B.delete()

        See ./tests/test_orm.py for more examples
    """

    def __init__(self, fname, composite_key_cols=(), workspace=None, enable_transactions=True, enable_log=True, update_read_check=True, **kwargs):
        #  always add composite key placeholders
        # it is critical that underscores are used for any non kwarg args
        self._XX_id_col_from_db = None  # mangled deliberately
        self._XX_db_cols_as_list = None  # mangled deliberately
        self._XX_db_cols_as_list_read_only = None

        self._XX_composite_key_cols = composite_key_cols  # mangled deliberately
        self._XX_enable_log = enable_log
        self._XX_was_read = False
        self._XX_update_read_check = update_read_check
        self._XX_fname = fname
        self._XX_enable_transaction = enable_transactions
        super().__init__(fname, workspace, enable_transactions)
        if self._has_col_name_clash():
            raise _errors.FeatureClassMemberNamingClash('The feature class or table %s has a column '
                                                        'name which clashes with the ORM member naming convention.\n"'
                                                        '"Look for cols starting with "_" and rename them.')
        self._load(**kwargs)

    def __enter__(self):
        """enter"""
        super().__enter__()
        return self

    def __exit__(self, t, v, tb):
        """exit"""
        super().__exit__(t, v, tb)

    def __getitem__(self, key):
        """iterator"""
        return self.__dict__[key]

    def __setitem__(self, key, value):
        """set item"""
        if key:
            self.__dict__[key] = value

    def __str__(self):
        """friendly print"""
        sb = []
        for key, v in self.__dict__.items():  # noqa
            if key[0] != '__':
                sb.append("{key}='{value}'".format(key=key, value=v))
        return ', '.join(sb)

    def pretty_print_members(self, include=(), include_empty=True, to_console=True, to_clip=True, do_read=True, exclude=()):
        """(bool, bool, bool, bool)->str
        Pretty print class members, i.e. the underlying table field values

        Args:
            include (list, tule): Include these members only
            include_empty (bool): Include members with None values
            to_console (bool): Print member string to the console
            to_clip (bool): Copy the member string to the clipboard
            do_read (bool): Read members from the underlying feature class, pass False if you know the instance has already called read()
            exclude (iter): Iterable of keys to exclude

        Returns:
            str: A pretty formatted string of the member values

        Notes:
            do_read will reload any current values set for the members,
            overwriting any value you may have set as a precursor to an update or delete.
            Read will use the composite key or OID to identify the feature class record.

        Examples:
            >>> pretty_print_members(include_empty=True, exclude=('dull', 'pointless'))  # noqa
            interesting: flower
            fascinating: bee
        """
        if do_read:
            try:
                self.read()
            except IndexError:
                raise IndexError('IndexError raised. This is likely caused by not instantiating your object correctly.\n'
                                 'For example: Sq=erammp.ORM.VSqSurvey(1234)  *WRONG*\n'
                                 'Use: Sq=erammp.ORM.VSqSurvey(sq_id=1234)  *CORRECT*')

        members = self.members_as_dict(EnumMembers.all_members)
        if include:
            include = [s.lower for s in include]
            members = [s for s in members if s.lower() in include]

        # include empty and is the member None, or '' or 0 etc
        d = {k.lower(): v for k, v in members.items() if include_empty or v}
        if exclude:
            d = {k: v for k, v in d.items() if k.lower() not in map(str.lower, exclude)}

        s = '\n'.join(['%s: %s' % (k, v) for k, v in d.items()])

        if to_console: print(s)
        try:
            if to_clip: _clip.copy(s)
        except Exception as e:
            _warn('Failed to copy members to the clipboard. The error was:\n\n%s' % str(e))
        return s

    def update(self, tran_commit=True):
        """
        Update records based on the configured oid, or the composite key

        Args:
            tran_commit (bool): commit any existing transaction, recommended.

        Returns: None

        Raises:
            UpdateCursorGotMultipleRecords: If the update would affect more than a single row. This can occur unexpectedly if there are now row matches on the composite key or primary key (OID@)

        Notes:
            tran_commit does nothing if the use_transaction is not True for the instance
        """
        if not self._XX_was_read and self._XX_update_read_check:
            raise _errors.ORMUpdateBeforeRead('An update was called before a read and read_check was true.'
                                              'This could overwrite row values with None.')

        if tran_commit and self._XX_enable_transaction:
            self.tran_begin()

        if not (self._has_oid or self._has_composite_key):
            raise _errors.UpdateMissingOIDOrCompositeKeyValues(_errors.UpdateMissingOIDOrCompositeKeyValues.__doc__)

        if self._OID:
            search_dict = self._members_as_dict(self._cols_as_list(EnumMembers.oid))
        else:
            search_dict = self._members_as_dict(self._cols_as_list(EnumMembers.composite_key))

        kwargs = self.members_as_dict(EnumMembers.members.value + EnumMembers.composite_key.value, editable_only=True)

        try:
            if self._XX_enable_log:
                self._log(EnumLogAction.update)

            self.upsert(search_dict, fail_on_multi=True, fail_on_exists=False, **kwargs)

            if tran_commit and self._XX_enable_transaction:
                self.tran_commit()
        except Exception as e:
            if self._XX_enable_transaction:
                self.tran_rollback()
            raise e

    def add(self, tran_commit=True, force_add=False, fail_on_exists=True):
        """(bool)->int
        Add a record

        Args: tran_commit (bool): Commit the transaction fail_on_exists (bool): Raise an error if the record already exists by the composite key. This is a useful override, for example when we are
        adding log records where the composite key can be duplicated

        Returns:
            None if add failed, otherwise int of the OID

        Raises:
            ORMNoColumnsWereIdentifiedForReadOperation: Raised if the ORM instance had no members (i.e. no fields had been set)

        Notes:
            tran_commit is defaulted to True to match other calls,
            but when adding multiple records suggest doing multiple edits then committing.
            Add's should generally not cause any unforseen issues.
            tran_commit does nothing if the use_transaction is not True for the instance
        """
        search_dict = self._members_as_dict(self._cols_as_list(EnumMembers.composite_key))
        if not search_dict:
            search_dict = self.members_as_dict(EnumMembers.members)
            with _fuckit:
                del search_dict['SHAPE@']  # don't include shape in the search

        if not search_dict:
            raise _errors.ORMNoColumnsWereIdentifiedForReadOperation('No values were set for the ORM instance.'
                                                                     )
        # cp = self.__dict__.copy()
        # self.__dict__ = {**cp, **search_dict}
        # kwargs = self._members_as_dict(self._cols_as_list(EnumMembers.members, EnumMembers.composite_key), editable_only=True)

        kwargs = self.members_as_dict(EnumMembers.members.value + EnumMembers.composite_key.value)

        if tran_commit and self._XX_enable_transaction:
            self.tran_begin()  # tran_begin first commits if in a tran

        try:
            i = self.upsert(search_dict, force_add=force_add, fail_on_multi=False, fail_on_exists=fail_on_exists, **kwargs)
            self._OID = i
            if tran_commit and self._XX_enable_transaction:
                self.tran_commit()
            return i
        except Exception as e:
            if self._XX_enable_transaction:
                self.tran_rollback()
            raise e

    def read(self, use_keys_only=False):
        """(dict, args...)->None|int
        Clear old members and read in new members

        Args:
            use_keys_only (bool):   Do not fall back to using general members. Useful if we just want to loop through a composite key list and some of the composite keys (rows) do not exist in the data source

        Raises:
            arcapi.errors.LookUpGotMoreThanOneRow: If read matches multiple rows. This can happen unexpectedly if there was no match on the primary key or composite key which causes read to fall back on a member lookup

        Returns: (int, None): primary key int or None

        Example:
            >>> C.read({'OBJECTID':121}, 'town', 'street', 'postcode')  # noqa
            121
        C.town;C.city;C.postcode  # noqa
        'Bangor', 'Main Street', 'CH4 4FF'  # noqa
        """
        # Have we created an instance with composite keys set ... then load it...
        key_cols = self._cols_as_list(EnumMembers.composite_key)

        # now try and get our record, first using the oid
        vals = [None]
        cols_to_get = None
        if self._has_oid:
            cols_to_get = self._cols_as_list(EnumMembers.composite_key, EnumMembers.members)
            cols_to_get_fix = list(map(self._remap_cols_in, cols_to_get))
            vals = self.lookup(cols_to_get_fix, {self.oid_col: self[self.oid_col]})

        # did oid fail, then try the composite key
        if all([v is None for v in vals]):
            d = self._members_as_dict(key_cols)
            if any(d.values()):  # do we have a composite key (allowing None for some values)
                if self.exists_by_compositekey(**self._members_as_dict(key_cols)):
                    cols_to_get = self._cols_as_list(EnumMembers.members)  # the oid is used to flag loaded
                    cols_to_get.append(self.oid_col_from_db)
                    cols_to_get_fix = list(map(self._remap_cols_in, cols_to_get))
                    # TODO Here we could capture an error with  "column was specified that does not exist" in str(e)
                    # TODO Then check for bad cols, as errors are most commonly due to orm class differences with the feature class
                    vals = self.lookup(cols_to_get_fix, self._members_as_dict(key_cols))
                else:
                    _warn('Composite key defined with value, but no records matched.\nTrying to use members instead (which will fail if no member lookup values were provided.\n\nYour expected '
                          'record may not exist.')

        if (not vals or vals == [None]) and use_keys_only: return  # we don't want to fall back on using general members
        # this may be expected, for example if we are just looping through a list of ids and we dont care if the ids exists or not

        # finaly try using any other members
        if all([v is None for v in vals]):
            cols_to_get = self._cols_as_list(EnumMembers.all_members)
            cols_to_get.append(self.db_cols_as_list[0])
            cols_to_get = list(set(cols_to_get))
            cols_to_get_fix = list(map(self._remap_cols_in, cols_to_get))
            try:
                vals = self.lookup(cols_to_get_fix, self._members_as_dict(self._cols_as_list(EnumMembers.members), include_none=False))
            except _errors.LookUpGotMoreThanOneRow as e:
                _warn('Record not found by key %s.\nFell back to using non-key members. You should check that the expected composite key or primary key (OID@) is valid.' % str(
                    self._members_as_dict(key_cols)))
                raise e

        if not cols_to_get:
            raise _errors.ORMNoColumnsWereIdentifiedForReadOperation('No columns were identified for the read operation.')

        for k, v in zip(cols_to_get, vals):
            self[k] = v
        self._XX_was_read = True
        return self._OID

    def validate_cols(self):
        """
        Check columns in the table definition against
        class members.

        Returns:
            dict: {'in_db':[...], 'both': [...], 'in_members': [...]}
        """
        dbcols = _struct.field_list(self._XX_fname)
        dcols: dict = self.members_as_dict(EnumMembers.all_members, include_none=True)
        cols = list(dcols.keys())

        d = _baselib.list_sym_diff(dbcols, cols)
        return {'in_db': d['a_notin_b'], 'both': d['a_and_b'], 'in_members': d['b_notin_a']}

    def delete(self, tran_commit=True, err_on_no_key=True):  # noqa
        """()->bool
        Delete a row.

        Args:
            tran_commit (bool): commits any open edits, starts a transaction, commits it.
            err_on_no_key (bool): Check if there is a composite key set for the delete operation

        Returns:
            True if deletes a row, False if no records matched OID or composite key

        Raises:
            DeleteHadNoOIDOrCompositeKey: Raise an error if err_on_no_key is True and if no composite key was set.

        Notes:
            Errors if more than a single row matches the specified OID or the composite key values
            as set in refresh or during initialisation
            Errors if no composite key or oid set
            tran_commit does nothing if the use_transaction is not True for the instance

        Example:
        >>> with ORM('c:/my.gdb/mylayer', userid='mhunt', username='mike hunt') as B:
        >>>     B.delete()

        """
        if tran_commit and self._XX_enable_transaction:
            self.tran_begin()

        try:
            if self._has_oid:
                if self._XX_enable_log:
                    self._log(EnumLogAction.delete)  # Debug - fields werent being copied to the log entry
                super().delete(fail_on_multi=True, **self._members_as_dict(self._cols_as_list(EnumMembers.oid)))
            elif self._has_composite_key:
                if self._XX_enable_log:
                    self._log(EnumLogAction.delete)  # Debug - fields werent being copied to the log entry
                super().delete(fail_on_multi=True, **self._members_as_dict(self._cols_as_list(EnumMembers.composite_key)))
            else:
                if err_on_no_key:
                    raise _errors.DeleteHadNoOIDOrCompositeKey('Delete had no primary key or composite key configured and err_on_no_key was True')
                if self._XX_enable_log:
                    self._log(EnumLogAction.delete)  # Debug - fields werent being copied to the log entry
                super().delete(fail_on_multi=True, **self._members_as_dict(self._cols_as_list(EnumMembers.all_members)))

            if tran_commit and self._XX_enable_transaction:
                self.tran_commit()

            return True
        except _errors.DeleteHadNoMatchingRecords:
            if self._XX_enable_transaction:
                self.tran_rollback()
            return False
        except Exception as e:
            if self._XX_enable_transaction:
                self.tran_rollback()
            raise e
        finally:
            self._clear_members()

    def _load(self, **kwargs):
        """try and load data

        Called on init and refersh
        """

        def _fix_oid(k_):
            """fix"""
            if k_.lower() == 'oid':
                return 'OID'
            if k_.lower() == 'oid@':
                return 'OID@'
            if k_.lower() == 'objectid':
                return 'OBJECTID'
            return k_

        # _BaseORM used as inherited class which preset the members, this will allow intellisense/autocomplete when using the inheriting class
        # See erammp-python/objs.py as an example
        if not kwargs:
            kwargs = dict(filter(self._is_member, self.__dict__.items()))  # noqa
            for k, v in kwargs.items():
                if _fix_oid(k) in ['OID', 'OID@', 'OBJECTID']:
                    del self.__dict__[k]
                    self.__dict__[_fix_oid(k)] = v

            for key in self._XX_composite_key_cols:
                if key not in kwargs:
                    self.__dict__[key] = None
        else:
            # add key to kwargs for composites, setting value to None
            for key in self._XX_composite_key_cols:
                if key not in kwargs:
                    kwargs[key] = None

            for k, v in kwargs.items():
                k = _fix_oid(k)
                self.__dict__[k] = v

        if _baselib.list_not(self._cols_as_list(EnumMembers.composite_key), self.db_cols_as_list):
            raise _errors.CompositeKeyColumnsInvalid('One or more Composite cols %s not found in feature class %s.\nNote field names ARE CASE SENSITIVE.' %
                                                     (str(self._XX_composite_key_cols), self._fname))

    def _cols_as_list(self, *args):
        """(args:orm.EnumColsAsList, ...)->List

        Lst of cols as requested by args, where args is a bitwise list
        on orm.EnumColsAsList

        Parameters
            args ... multiple args, which are summed to determine which set of cols were return,

        Example:
        >>> cols_as_list(EnumMembers.composite_key, EnumMembers.oid, EnumMembers.members)  # noqa
        ['compkeyA', 'compkeyB', 'ObjectID', '...']  # noqa
        """
        if isinstance(args[0], int):
            n = args[0]
        else:
            n = sum(i.value for i in args)
        out = []

        if n & EnumMembers.composite_key.value:  # noqa
            out.extend(self._XX_composite_key_cols)
        if n & EnumMembers.oid.value:  # noqa
            if self._fname[-4:] == '.shp':
                if 'OID' in self.__dict__:
                    out.append('OID')
            else:
                if 'OBJECTID' in self.__dict__:
                    out.append('OBJECTID')
            # out.extend([k for k in self.__dict__ if k.lower() in ['oid', 'objectid', 'oid@']])
        if n & EnumMembers.members.value:  # noqa
            exclude = ['oid', 'objectid', 'oid@']
            exclude.extend([s.lower() for s in self._XX_composite_key_cols])
            out.extend([k for k in self.__dict__ if k.lower() not in exclude and k[0] != '_'])
        return out

    def _members_as_dict(self, members, include_none=False, editable_only=False):
        """(list)->dict
        get members as a dictionary

        Example
        >>> self._members_as_dict(['county', 'identifier'])
        {'county':'Anglesey', 'identifier':12345'}
        """
        if include_none:
            out = {k: self[k] for k in members}
        else:
            out = {k: self[k] for k in members if self[k] is not None}

        if not editable_only:
            d = {k: v for k, v in out.items()}
        else:
            ed = list(map(str.lower, list(self.db_cols_as_list_editable)))
            d = {k: v for k, v in out.items() if k.lower() in ed}
        return d

    def members_as_dict(self, enum_=EnumMembers.all_members, include_none=False, editable_only=False) -> dict:
        """
        Get members as a dictionary, using the enum

        Just a wrapper around _members_as_dict which requires the col names
        to be passed in.

        Args:
            enum_: An enumeration from EnumMembers, or pass an int of summed EnumMembers for bitwise retreival
            include_none (bool): include members which have None values
            editable_only (bool): Editable members only, eg exclude OBJECTID

        Returns:
            dict: members keyword/values as a dict, {'OBJECTID':1, 'Country':'Wales', ...}

        Examples:
            >>> self.members_as_dict(EnumMembers.oid.value + EnumMembers.composite_key.value)  # noqa
            {'a':2, ....}

            >>> self.members_as_dict(EnumMembers.oid.value)  # noqa
            {'OBJECTID':2}
        """
        cols = self._cols_as_list(enum_)
        return self._members_as_dict(cols, include_none=include_none, editable_only=editable_only)

    def dict_as_members(self, dict_: dict, member_exists_check: bool = True) -> None:
        """set members from kwargs

        Args:
            dict_ (dict): keyword arguments as dictionary.
            member_exists_check (bool): Check if the member already exist in the object instance

        Raises:
            ORMMemberDoesNotExist: If the member does not preexist in the class instance and member_exists_check is True

        Examples:
             >>> dict_as_members({'town':'manchester', 'locale':'stockport'})  # noqa
        """
        if member_exists_check:
            for k, v in dict_.items():
                if k not in self.__dict__.keys():
                    raise _errors.ORMMemberDoesNotExist('The member %s does not exist' % k)

        for k, v in dict_.items():
            self.__dict__[k] = v  # noqa

    def _log(self, action: EnumLogAction):
        """(EnumAction)->None
        Automate logging/archiving actions

        log will look for a feature class with name <fname>_log and
        if it exists will copy the exiting record and append action
        to the 'action' field.

        Args:
            action (EnumLogAction): The action enumeration. Only deletes and updates persist data to a log backup table

        Returns:
            type: None

        Examples:
            >>> _log(EnumLogAction.add)  # noqa

        Notes:
            This call commites the current transaction, this should be revisited
        """

        if self._fname[-4:].lower() == '_log': return  # ignore if we are already a log file
        fname = '%s_%s' % (self._fname, 'log')

        if not _arcpy.Exists('%s_%s' % (self._fname, 'log')):
            return

        if action not in EnumLogAction:
            raise _errors.ORMLogActionWasInvalid('EnumLogAction %s was invalid.' % str(action))

        if action == EnumLogAction.add: return

        if 'action' in map(str.lower, self.db_cols_as_list):
            raise _errors.ORMLogActionTableHasActionCol("Cannot support ORM per-record logs. "
                                                        "The feature class %s has an 'action' column. "
                                                        " Rename the existing action column and add another one." % self._fname)
        # TODO: This still isnt working right, might be an error in table structure
        with ORM(self._fname, self._XX_composite_key_cols, self._workspace, enable_transactions=True) as CurRow:
            # load primary key and/or composite key to get the current record
            CurRow._OID = self._OID
            for k, v in self.members_as_dict(EnumMembers.composite_key).items():
                CurRow.__dict__[k] = v

            for k in self.members_as_dict(EnumMembers.composite_key.value + EnumMembers.members.value):
                CurRow.__dict__[k] = None  # we want to load these existing values in

            CurRow.read()
            CurRow.__dict__['action'] = action.name
            CurRow._fname = fname  # important line, switch to the log feature class and try add
            try:
                CurRow.add(tran_commit=True, fail_on_exists=False)
            except Exception as e:
                with _fuckit:
                    d = _struct.fcs_field_sym_diff(self._fname, fname)
                    if d['a_notin_b']:
                        raise _errors.ORMLogTableColumnMismatch('Columns %s in %s but not in %s. Add them.' % (str(d['a_notin_b']), self._fname, fname)) from e
                raise e

    def _clear_members(self):
        """set all members to None after a delete"""
        for k in filter(self._is_member, self.__dict__.keys()):
            self.__dict__[k] = None

    def _has_col_name_clash(self):
        b = any(filter(self._is_not_member, self.db_cols_as_list))
        return b

    @property
    def oid_col_from_db(self):
        """this returns the id column from the db
        the id column is always listed first"""
        if self._XX_id_col_from_db:
            return self._XX_id_col_from_db
        self._XX_id_col_from_db = _common.get_id_col(self._fname)
        return self._XX_id_col_from_db

    @property
    def _has_oid(self):
        return self._OID is not None

    @property
    def _has_composite_key(self):
        """does it look like the composite is set"""
        return not all(v is None for v in self._members_as_dict(self._XX_composite_key_cols).values())

    @property
    def db_cols_as_list_editable(self):
        """list of editable cols"""
        lst = _baselib.list_not(self.db_cols_as_list, self.db_cols_as_list_read_only)
        if self.__dict__.get('action'):
            lst.append('action')  # cludge for when we are writing logs
        return lst

    @property
    def db_cols_as_list_read_only(self):
        """list of readonly cols"""
        if self._XX_db_cols_as_list_read_only:
            return self._XX_db_cols_as_list_read_only
        lst = _struct.field_list(self._fname, editable=False)
        self._XX_db_cols_as_list_read_only = lst

    @property
    def db_cols_as_list(self):
        """List of all field headings in the feature class"""
        if self._XX_db_cols_as_list:
            return self._XX_db_cols_as_list
        self._XX_db_cols_as_list = _struct.field_list(self._fname)
        return self._XX_db_cols_as_list

    @property
    # leave as is despite having oid_col_from_db property
    # should refactor at some point
    def oid_col(self):
        """name of the oid col"""
        return self._cols_as_list(EnumMembers.oid)[0] if self._cols_as_list(EnumMembers.oid) else None

    @property
    def shape_col(self):
        """
        Get name of the Shape (Geometry) field in feature class fname

        Returns:
             str: Name of the shape/geometry field
        """
        return _struct.field_shp(self._fname)

    # The following OID trickery is necessary to consistently reference
    # the OID field when using it in this class. Refector at some point
    @property
    def _OID(self):
        """get the OID"""
        return self.__dict__.get(self.oid_col, None)

    @_OID.setter
    def _OID(self, value):
        """utility func to overwrite the OID"""
        if self._fname[-4:] == '.shp':
            s = 'OID'
        else:
            s = 'OBJECTID'
        self[s] = value

    @property
    def loaded(self):
        """did we load ok from the db?

        A load will be attempted if a class instance is created with a value for the
        autoincremental primary key (i.e. OID or ObjectID). Or where composite key
        values are provided.
        """
        return self.__dict__[self.oid_col] is not None

    @staticmethod
    def _remap_cols_in(s):
        """we cant use members with @ in a variable name, and
        Shape doesn't return the actual shape poly
        So we have to cludge stuff for the _load func"""
        if s == 'Shape': return 'Shape@'
        return s

    @staticmethod
    def _is_member(item):
        """(tuple|str)-> bool
        is it member

        Intended to work with dict.keys() or dict.items()"""
        assert isinstance(item, (str, tuple))
        if isinstance(item, str):
            return item[0] != '_'
        if isinstance(item, tuple):
            return item[0][0] != '_'

    @staticmethod
    def _is_not_member(item):
        """(tuple|str)-> bool
        is it member

        Intended to work with dict.keys() or dict.items()"""
        assert isinstance(item, (str, tuple))
        if isinstance(item, str):
            return item[0] == '_'
        if isinstance(item, tuple):
            return item[0][0] == '_'

    @staticmethod
    def to_pandas(Objs: list, skip='Shape', **kwargs) -> _pd.DataFrame:
        """
        Return a pandas dataframe from all objs in list.
        The pandas columns are the attributes and each row
        represents an object in the list

        Args:
            Objs: List of ORM objects
            skip (str,iter): Skip cols in skip. May want this as Arc geoms fail with xlwings.view
            kwargs: keyword arguments passed to pandas.DataFrame.from_dict
                    See https://pandas.pydata.org/docs/reference/api/pandas.DataFrame.from_dict.html

        Returns:
            pandas.DataFrame

        Notes:
            Objects should all be the same

        Examples:
            >>> Obj1 = ORM(fname='C:/shp.shp', ObjectID=13, a=None, b=None)
            >>> Obj1.read()
            >>> Obj2 = ORM(fname='C:/shp.shp', ObjectID=22, a=None, b=None)
            >>> Obj2.read()
            >>> Os = [Obj1, Obj2]
            >>> df = ORM.to_pandas(Os); df  # noqa
                objectid    'a'     'b'
            1   13          1       2
            2   22          3       4
        """
        # Obj = Objs[0]
        # assert isinstance(Obj, ORM)
        if isinstance(skip, str): skip = [skip]

        dd = _ddict(list)
        for Obj in Objs:
            assert isinstance(Obj, ORM)
            d = Obj.members_as_dict()
            for k, v in d.items():
                if k.lower() in map(str.lower, skip):
                    continue
                dd[k].append(v)
        df = _pd.DataFrame.from_dict(dd, **kwargs)
        return df

    def read_multi(self, **kwargs):
        # TODO Implement read_multi
        pass
