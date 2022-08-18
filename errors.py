# pylint: disable=C0103, too-few-public-methods, locally-disabled, no-self-use, unused-argument
"""Custom errors for this package"""

class LayoutNotFound(ValueError):
    """Layout was not found"""

class MapNotFound(ValueError):
    """map not found"""

class MapFrameNotFound(ValueError):
    """mapframe not found"""

class ArcapiError(Exception):
    """A type of exception raised from arcapi module"""

class ReadOnlyError(Exception):
    """item is read only"""

class FieldExists(Exception):
    """The field already exists"""

# ORM Errors BEGIN
# ----------------
class ORMLogActionWasInvalid(Exception):
    """The ORM log action should be Delete, Add or Update"""
    
class ORMLogActionTableHasActionCol(Exception):
    """Cannot support ORM per-record logs The feature class has an 'action' column"""

class ORMLogTableColumnMismatch(Exception):
    """Columns exist in the feature class which are not in the log feature class"""

class ORMNoColumnsWereIdentifiedForReadOperation(Exception):
    """No columns for read"""

class ORMUpdateBeforeRead(Exception):
    """An update was called before a read and read_check was true. This could overwrite row values with None."""

class ORMMemberDoesNotExist(Exception):
    """ORM member does not exists"""

class DeleteHadNoMatchingRecords(Exception):
    """Delete had no records matching the specified key values"""

class DeleteHadNoOIDOrCompositeKey(Exception):
    """Delete could not execute as had no OID or composite key set"""

class DeleteMatchedMutlipleRecords(Exception):
    """Delete matched more than one record"""

class LookUpGotMoreThanOneRow(Exception):
    """A value lookup matched more than one row"""

class UpdateCursorGotMultipleRecords(Exception):
    """UpdateCursor had more than 1 record, and we told it this was bad"""

class UpdateMissingOIDOrCompositeKeyValues(Exception):
    """ORM Update operation was called, but the OID or Composite Key member(s) were invalid"""

class UpsertExpectedInsertButHadMatchedRow(Exception):
    """CRUD had no keyword arguments passed, but keylist found a matched row in the table or feature class"""

class UpsertExpectedUpdateButMatchedRow(Exception):
    """Upsert expected to update a record, but no record matched the key-value dict passed to the call"""

class FeatureClassMemberNamingClash(Exception):
    """The feature class or table has a column name which clashes with the ORM member naming convention"""

class EditOperationRolledBack(Exception):
    """An edit operation was rolled back"""

class CompositeKeyColumnsInvalid(Exception):
    """The definied composite key column names could not be found in the feature class/table"""
# END OF ORM ERRORS


# struct.py errors
class StructMultipleFieldMatches(Exception):
    """Multiple fields matched, expected a single field match"""

class StructFieldExists(Exception):
    """Field already exists in table or featureclass"""
# end struct.py


# data.py errors
class DataNoRowsMatched(Exception):
    """No rows matched the query"""

class DataFieldValuesNotUnique(Exception):
    """Field values were not unique"""

class DataUnexpectedRowCount(Exception):
    """Expected a fixed rowcount, got different rowcount"""

class DataDeleteAllRowsWithNoWhere(Exception):
    """Delete all rows with now where clause"""
# end data.py


# display errors
class DisplayFeatureClassNotFound(Exception):
    """No feature class matched the feature class name"""

class DisplayFeatureClassNameMatchedMultipleLayers(Exception):
    """The feature class name matched more than one feature layer"""
# end display errors


########
# geom #
########
class GeomInvalidTypeString(Exception):
    """Geometry type string invalid. Geometry strings are IN [point, polygon, polyline, or multipoint."""
