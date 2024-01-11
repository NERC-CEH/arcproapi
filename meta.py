"""work with metadata"""
import os as _os
import os.path as _path

import arcpy as _arcpy

from funclite.stringslib import pretty_date_time_now

import arcproapi as _arcapi
import arcproapi.common as _common


class LicenseText:
    # NB: As arcproapi is a general package, don't put localised non-standard licenses here (e.g. the one your small company made up)
    OGL_v3 = 'Open Government License v3. See https://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/ for conditions'



class MetaBuilderBasic:
    """
    Build summary and description for the write_basic metadata method.
    Adds a standard structure/formatting and as an aide-memoir in what to include.

    The "what" and "purpose" builds the summary.

    Everything except "title" builds the description.

    Methods:
        summary (str): Text for summary, constructed from "when" and "purpose2
        title (str): Passed and written as provided at class instantiation
        description (str): Built from all attributes, except title
        write_basic: Convieniance function to write out the metadata to the specified fname

    Notes:
        creation_date is set to the current date by default

    Examples:

        >>> Build = MetaBuilderBasic(title='title', purpose='purpose', ...)  # noqa
        >>> Build.caveats_and_limitations = 'caveats'
        >>> Build.write_basic('C:/my.gdb/fc')
    """
    # No license as this is exposed through arcpy metadata class
    def __init__(self, title: str, what: str = '', purpose: str = '', where: str = '', when: str = '', how: str = '', lineage: str = '', missing_data: str = '', caveats_and_limitations: str = '',
                 quality_control: str = '', credit: str = '', license: str = '', creation_date: str = pretty_date_time_now(), inputs: (tuple[str], list[str]) = (), scripts: (tuple[str], list[str]) = ()):  # noqa
        self.title = title
        self.purpose = purpose
        self.what = what
        self.where = where
        self.when = when
        self.how = how
        self.missing_data = missing_data
        self.caveats_and_limitations = caveats_and_limitations
        self.quality_control = quality_control
        self.inputs = inputs
        self.scripts = scripts
        self.credit = credit
        self.license = license
        self.lineage = lineage
        self.creation_date = creation_date

    def summary(self) -> str:
        return self.description(filt=('what', 'purpose', 'creation_date'))

    def description(self, filt=()) -> str:
        jn = []
        for k, v in self.__dict__.items():
            if k[0:2] == '__': continue
            if filt and k not in filt: continue
            if not v: continue
            if isinstance(v, (str, int, float)):
                jn += [MetaBuilderBasic.addhdr(k)]
                jn += [v]
            elif isinstance(v, (list, tuple)):
                jn += [MetaBuilderBasic.addhdr(k)]
                jn += ['\n'.join(v)]
        return '\n\n'.join(jn)


    def write_basic(self, fname):
        write_basic(fname, self.summary(), self.description(), self.title)

    @staticmethod
    def addhdr(s):
        return '%s\n%s' % (s.upper(), '=' * len(s))


def meta(datasource, mode="PREPEND", **args):  # noqa
    """
    Read-write metadata of ArcGIS Feature Class, Raster Dataset, Table, etc.

    Returns a dictionary of all accessible (if readonly) or all editted entries.

    *** This function may irreversibly alter metadata, see details below! ***

    The following entries (XML elements) can be read or updated:
    Title ("dataIdInfo/idCitation/resTitle")
    Purpose ("dataIdInfo/idPurp")
    Abstract ("dataIdInfo/idAbs")

    This function exports metadata of the datasource to XML file using template
    'Metadata\Stylesheets\gpTools\exact copy of.xslt' from ArcGIS installation
    directory. Then it loads the exported XML file into memory using Pythons
    xml.etree.ElementTree, modifies supported elements, writes a new XML file,
    and imports this new XML file as metadata to the datasource.
    If the content of exported metada does not contain element dataInfo,
    it is assumend the metadata is not up to date with current ArcGIS version
    and UpgradeMetadata_conversion(datasource, 'ESRIISO_TO_ARCGIS') is applied!
    Try whether this function is appropriate for your work flows on dummy data.

    Required:
    datasource -- path to the data source to update metadata for
    mode -- {PREPEND|APPEND|OVERWRITE}, indicates whether new entries will be
        prepended or appended to existing entries, or whether new entries will
        overwrite existing entries. Case insensitive.
    **args, keyword arguments of type string indicating what entries to update:
        title, string to use in Title
        purpose, string to use in Purpose
        abstract, string to use in Abstract
        If no keyword argument is specifed, metadata are read only, not edited.

    Examples:

        >>> fc = r'c:\\foo\\bar.shp'
        >>> meta(fc) # reads existing entries
        >>> meta(fc, 'OVERWRITE', title="Bar") # updates title
        >>> meta(fc, 'append', purpose='example', abstract='Column Spam means eggs')
    """
    raise NotImplementedError
    # https://github.com/Esri/arcgis-pro-metadata-toolkit
    # Need to convert so compatible with arcpro

    import xml.etree.ElementTree as ET
    xslt = None  # metadata template, could be exposed as a parameter
    sf = _arcpy.env.scratchFolder
    tmpmetadatafile = _arcpy.CreateScratchName('tmpmetadatafile', workspace=sf)

    # checks
    if xslt is None:
        template = 'Metadata/Stylesheets/gpTools/exact copy of.xslt'
        arcdir = _arcpy.GetInstallInfo()['InstallDir']
        xslt = _path.join(arcdir, template)
    if not _path.isfile(xslt):
        raise ArcapiError("Cannot find xslt file " + str(xslt))
    mode = mode.upper()

    lut_name_by_node = {
        'dataIdInfo/idCitation/resTitle': 'title',
        'dataIdInfo/idPurp': 'purpose',
        'dataIdInfo/idAbs': 'abstract'
    }

    # work
    r = _arcpy.XSLTransform_conversion(datasource, xslt, tmpmetadatafile)  # noqa
    tmpmetadatafile = r.getOutput(0)
    with open(tmpmetadatafile, "r") as f:
        mf = f.read()
    tree = ET.fromstring(mf)

    # check if read-only access requested (no entries supplied)
    readonly = True if len(args) == 0 else False
    reader = {}
    if readonly:
        args = {'title': '', 'purpose': '', 'abstract': ''}
    else:
        # Update the metadata version if it is not up to date
        if tree.find('dataIdInfo') is None:
            _arcpy.conversion.UpgradeMetadata(datasource, 'ESRIISO_TO_ARCGIS')
            _os.remove(tmpmetadatafile)
            r = _arcpy.XSLTransform_conversion(datasource, xslt, tmpmetadatafile)  # noqa
            tmpmetadatafile = r.getOutput(0)
            with open(tmpmetadatafile, "r") as f:
                mf = f.read()
            tree = ET.fromstring(mf)

    # get what user wants to update
    entries = {}
    if args.get('title', None) is not None:
        entries.update({'dataIdInfo/idCitation/resTitle': args.get('title')})
    if args.get('purpose', None) is not None:
        entries.update({'dataIdInfo/idPurp': args.get('purpose')})
    if args.get('abstract', None) is not None:
        entries.update({'dataIdInfo/idAbs': args.get('abstract')})

    # update entries
    for p, t in entries.iteritems():  # noqa
        el = tree.find(p)
        if el is None:
            if not readonly:
                wm = "Element %s not found, creating it from scratch." % str(p)
                _arcpy.AddWarning(wm)
                pparent = "/".join(p.split("/")[:-1])
                parent = tree.find(pparent)
                if parent is None:
                    em = "Could not find parent %s as parent of %s in %s " % \
                         (pparent, p, str(datasource))
                    raise ArcapiError(em)
                subel = ET.SubElement(parent, p.split("/")[-1])
                subel.text = str(t)
                el = subel
                del subel
        else:
            if not readonly:
                pre, mid, post = ('', '', '')
                if mode != "OVERWRITE":
                    # remember existing content if not overwrite
                    mid = '' if el.text is None else el.text
                    joiner = '&lt;br/&gt;'
                else:
                    mid = str('' if t is None else t)
                    joiner = ''
                if mode == 'APPEND': post = str('' if t is None else t)
                if mode == 'PREPEND': pre = str('' if t is None else t)
                el.text = joiner.join((pre, mid, post))
        reader.update({lut_name_by_node[p]: getattr(el, 'text', None)})

    # write a new xml file to be imported
    mf = ET.tostring(tree, encoding='utf-8')
    with open(tmpmetadatafile, "w", encoding='utf-8') as f:
        f.write(mf)

    # import new xml file as metadata
    _arcapi.ImportMetadata_conversion(tmpmetadatafile, datasource)  # noqa

    _common.msg("Updated metadata for " + str(datasource))

    # try to clean up
    try:
        _os.remove(tmpmetadatafile)
    except:
        pass

    return reader


def write_basic(fname: str, summary: str = '', description: str = '', title: str = '') -> bool:
    """
    Write out summary and description metadata to table/fc fname.
    All errors are suppressed.


    Args:
        fname (str): the layer
        summary (str): the summary
        description (str): the description
        title (str): the title

    Returns:
        bool: True if write worked, false if error

    Notes:
        *** Recommend use MetaBuilderBasic to construct and write basic metadata to title, summary and description ***
        Title: The title should describe the data, not the project. It should describe what the data is. Good practive is to answer What, Where and When
        Summary: Extend on title, but keep it succint. Think - What, Where, When, How, Who
        Description: Recovering the summary is not required. But extent to include:
            (i) Input datasets and processing
            (ii) Quality Control
            (iii) Missing and extra data
            (iv) Caveats and limitations

        See https://eidc.ac.uk/deposit/metadata/guidance


    Examples:
        >>> write_basic('C:/my.gdb', 'my summary', 'my description', 'my title')
        True
    """
    out = False
    fname = _path.normpath(fname)
    try:
        M = _arcpy.metadata.Metadata(fname)
        M.summary = summary
        M.description = description
        M.title = title

        if False:
            # Exposed, but can't write it, even though it is not set to the layer extent, well done ESRI. Leaving code here incase it is ever fixed
            if write_extent:
                d = _arcpy.Describe(fname).extent
                M.xMin, M.xMax, M.yMin, M.yMax = d.XMin, d.XMax, d.YMin, d.YMax
        M.save()  # noqa
        out = True
    finally:
        try:  # paranoid about ESRI not clearing up properly
            del M
        except:
            pass
    return out
