# pylint: disable=C0103, too-few-public-methods, locally-disabled, no-self-use, unused-argument
"""Wrapper for interacting with arcpro projects"""
import os.path as _path
import glob as _glob
from warnings import warn as _warn

import arcpy as _arcpy
import fuckit as _fuckit

import funclite.log as _log

import arcproapi.errors as _errors
import arcproapi.common as _common

from arcproapi import mp as _mp  # arcpy.mapping/arcpy.mp


class Project:
    """Class to work with projects

    Args:
        aprx (str): fully qualified path to the arpx project file

    Methods:
        Project: The arcgispro Project object, exposed for convieniance
    """

    def __init__(self, aprx: str):
        self._arpx_path = _path.normpath(aprx)
        self.Project = _arcpy.mp.ArcGISProject(self._arpx_path)

    def __enter__(self):
        """support context manager"""
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        """clean up to stop locks persisting"""
        try:
            self.Project.save()
        except Exception as e:
            _warn('An exception occured when saving the project on exit:\n\n' % e)
        finally:
            del self.Project

    def __str__(self):
        """friendly print instance members"""
        return self._arpx_path




    def paths_update(self, find, replace, **kwargs) -> list[str]:
        """
        Change paths for layers. Calls updateConnectionProperties on
        each layer which matches ..

        Args:
            find (str): find in source path
            replace (str): replace "find" in source path

            **kwargs (any): Keyword arguments to pass to updateConnectionProperties. Currently supportes validate, auto_update_joins_and_relates, ignore_case
            See https://pro.arcgis.com/en/pro-app/latest/arcpy/mapping/layer-class.htm

        Returns:
            list[str]: list of layers/table which were updated

        Notes:
            Needed because updateConnectionsProperties called against the project
            does not currently function correctly.

        Examples:
            >>> with Project('C:/my.arpx') as Prj:  # noqa
            >>>     Prj.paths_update('bad/layer/path', 'good/layer/path')
            ['layer1', 'layer2', 'table2']
        """
        good = []
        for M in self.Project.listMaps():
            for lyr in M.listLayers():
                if lyr.supports("CONNECTIONPROPERTIES"):
                    try:
                        lyr.updateConnectionProperties(find, replace, **kwargs)
                        good += lyr.name
                    except Exception as e:
                        _warn('Failed to change source for layer %s. The error was:\n%s' % (lyr.name, e))

        self.Project.save()
        return good


class Map:
    """Class to work with maps in an arcgispro project.
    Supports a context manager, i.e. instantiate using with.

    Args:
        aprx (str): fully qualified path to the arpx project file
        map_name (str): name of a map in the project file
        logto (str): open a logfile to record errors etc (need to call save to persist to file system)
        overwrite_log (bool): Overwrite the existing log file.
        layout (str): optionally set a layout object in the class

    Notes:
        The object Map, Layout, Mapframe and Project are the native arcpy objects.

        The collection Layers is a dictionary of all layers in the map, hence
        layers can be accessed with Map.Layers['layer_name'].

    Examples:
        >>> with arcpro.Map('c:/proj.arpx', 'mymap', 'c:/log.log', 'Layout1') as MyMap:  # noqa
        >>> MyMap.<do stuff>  # noqa
    """

    def __init__(self, aprx: str, map_name: str, logto: str, overwrite_log: bool = False, layout: str = '', map_frame: str = ''):
        self._arpx_path = _path.normpath(aprx)
        self._logto = _path.normpath(logto)
        self._map_name = map_name
        self._layout_name = layout
        self._map_frame_name = map_frame
        self._overwrite_log = overwrite_log
        self.Logger = _log.Log(self._logto, self._overwrite_log)

        self.Layers = {}
        self.Map = None
        self.Layout = None
        self.MapFrame = None

        self.Project = _arcpy.mp.ArcGISProject(self._arpx_path)

        if self._map_name:
            self.map_open(self._map_name)

        if self._layout_name:
            self.layout_open(self._layout_name)

        if self._map_frame_name:
            self.map_frame_open(self._map_frame_name)

    def __enter__(self):
        """support context manager"""
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        """clean up to stop locks persisting"""
        with _fuckit:
            del self.Layout
            del self.Map
            del self.Project
            self.Logger.write()

    # MAP OBJECT STUFF--------------------------------
    def map_open(self, map_name):
        """(str) -> Obj:ArcPy.Map
        open a map, close the current one
        Sets self.Map, and returns an ArcPy map object
        """
        self._map_close()
        self._map_name = ''
        self.Map = self.Project.listMaps(map_name)[0]
        self._map_name = map_name
        self.layers_refresh()
        return self.Map

    def layers_refresh(self):
        """Refresh layers dict so that
        the self.Layers matches removal and additions
        to the Map object

        Returns: None
        """
        self.Layers = {listLayer.name: listLayer for listLayer in self.Map.listLayers() if not listLayer.isGroupLayer and listLayer.supports("NAME")}

    def _map_close(self):
        with _fuckit:
            del self.Layers
            del self.Map

    # LAYOUT OBJECT STUFF--------------------------------
    def layout_open(self, layout_name):
        """(str) -> Obj:ArcPy.Map
        open a map, close the current one
        Sets self.Layout, and returns an ArcPy Layout object
        """
        self._layout_close()
        self._layout_name = ''
        self.Layout = self.Project.listLayouts(layout_name)[0]
        self._layout_name = layout_name
        return self.Layout

    def _layout_close(self):
        with _fuckit:
            del self.Layout

    def layout_to_pdf(self, fname: str, dpi: int = 300, image_quality: str = 'BEST', **args):
        """(str) -> str
        Export current layout to pdf

        Args:
            fname (str): The feature class/table
            dpi (int): Resolution of the pdf
            image_quality(str): See  the arcpy Layout.exportToPDF documentation
            **args: Keyword arguments passed to the arcpy Layout.exportToPDF method

        Examples:
            >>> Map.layout_open('mylayout')
            >>> Map.layout_to_pdf('C:/temp.mylayout.pdf')

        See https://pro.arcgis.com/en/pro-app/latest/arcpy/mapping/layout-class.htm for args
        """
        fname = _path.normpath(fname)
        self.Layout.exportToPDF(fname, dpi, image_quality, **args)

    def mapframe_zoom_to_feature(self, lyr_name: str, feat_col: str, fid: int, scale_factor: float = 1, abs_scale: float = None) -> None:
        """
        Pan and zoom to feature with OID=fid.

        Args:
            lyr_name: Name of layer in the Map object
            feat_col: Name of column to look up the feature on
            fid: Row data to find in the column
            scale_factor: after zooming, either grow or shrink the extent by this factor
            abs_scale: zoom to this absolute scale

        Returns:
            None


        TODO:
            This is a hacky and relies on clearing filters. Redesign so find a feature then zoom to that features extent
        """
        if scale_factor != 1 and abs_scale:
            _warn('scale_factor and abs_scale arguments both set. Using scale_factor, ignoring abs_scale')
            abs_scale = None

        self.layers_clear_filters()
        lyrs = self.Map.listLayers(lyr_name)
        if len(lyrs) > 1:
            _warn('Map "%s" had %s layers named "%s". Picked the first one.' % (self._map_name, len(lyrs), lyr_name))
        lyr = lyrs[0]

        q = '%s = %s' % (feat_col, fid)
        _arcpy.management.SelectLayerByAttribute(lyr, "NEW_SELECTION", q,
                                                 None)  # If this is failing unexpectedly, check that data types are as expected, e.g. if doing sqid=1, make sure the underlying table data type is int/long
        self.MapFrame.zoomToAllLayers()  # zooms to currently selected feature, honest

        factor = scale_factor * self.MapFrame.camera.scale if scale_factor != 1 else abs_scale  # zoom in/out by scale factor
        self.MapFrame.camera.scale = factor

    def map_frame_open(self, map_frame_name: str):
        """(str) -> Obj:ArcPy.Map
        open a map, close the current one
        Sets self.Layout, and returns an ArcPy Layout object

        Returns
        """
        if not self.Layout:
            raise _errors.LayoutNotFound('Could not open MapFrame "%s" because no Layout was set' % map_frame_name)

        self._map_frame_close()
        self._map_frame_name = ''
        self.MapFrame = self.Layout.listElements('mapframe_element', map_frame_name)[0]
        self._map_frame_name = map_frame_name
        return self.MapFrame

    def _map_frame_close(self):
        with _fuckit:
            del self.MapFrame

    def layers_hide(self, layers, show_rest=False):
        """(str|iter) -> None
        Hide layers by name in the iterable layers

        Args:
            layers:
                Iterable or string of layer names
            show_rest:
                Boolean, if true will force all layers not in layers to be hidden

        Examples:
            >>> Map.layers_hide(['square','my_polys'], show_rest=True)  # noqa
        """
        if isinstance(layers, str):
            lyrs = (layers,)
        else:
            lyrs = tuple(layers)
        lyrs = (s.lower() for s in lyrs)
        for lname in self.Map.listLayers():
            lname = lname.lower()
            if show_rest:
                lname.visible = lname not in lyrs
            else:
                lname.visible = lname not in lyrs if lname in lyrs else lname.visible  # i.e. leave it unchanged if not in layers

    def layers_show(self, layers: (str, list[str]), hide_rest: bool = False, force_show_group_layers: bool = True):
        """
        Show layers by name in the iterable layers

        Args:
            layers: Iterable or string of layer names
            hide_rest: Boolean, if true will force all layers not in layers to be hidden, ignores group layers
            force_show_group_layers: will turn all group layers to visible

        Examples:
            >>> Map.layers_show(['square','my_polys'], show_rest=True)
        """
        if isinstance(layers, str):
            lyrs = (layers,)
        else:
            lyrs = tuple(layers)
        lyrs = tuple((s.lower() for s in lyrs))
        for map_lyr in self.Map.listLayers():
            if not map_lyr.supports('NAME'):
                continue

            s = map_lyr.name.lower()

            if force_show_group_layers and map_lyr.isGroupLayer:
                map_lyr.visible = True
                continue

            if hide_rest:
                if map_lyr.isGroupLayer: continue
                map_lyr.visible = s in lyrs
            else:
                map_lyr.visible = s in lyrs if s in lyrs else map_lyr.visible  # i.e. leave it unchanged if not in layers

    def layer_clear_filters(self, lyr_name_or_lyr, clear_definition_query=True, clear_selection=True):
        """(str|Object:Layer, bool, bool) -> None
        Clear definition queries and selections on a layer.

        Args:
            lyr_name_or_lyr: text name of layer or a Layer object, case insensitive
            clear_definition_query (bool): clear the definition query from the layer
            clear_selection (bool): deselect selected features

        Returns: None

        Notes:
            Uses listLayers, so use layer name as displayed in map and NOT the feature class name in the db
        """
        # noinspection PyBroadException
        try:
            lyr = self.Map.listLayers(lyr_name_or_lyr)[0] if isinstance(lyr_name_or_lyr, str) else lyr_name_or_lyr
            if clear_definition_query:
                lyr.definitionQuery = ''
            if clear_selection:
                lyr.setSelectionSet([], 'NEW')
        except:
            self.Logger.log('clear_layer_filters failed for layer %s' % lyr_name_or_lyr)

    def layer_set_transparency(self, lyr_name_or_lyr: str, v: int):
        """
        Set layer transparency

        Args:
            lyr_name_or_lyr: An arcpy layer object or the layer name as a string
            v: transparency vale (0-100)
        """
        try:
            lyr = self.Map.listLayers(lyr_name_or_lyr)[0] if isinstance(lyr_name_or_lyr, str) else lyr_name_or_lyr
            lyr.transparency = v
        except:
            self.Logger.log('layer_set_transparency failed for layer %s' % lyr_name_or_lyr)

    def layers_clear_filters(self, wildcard_or_list: str = '', clear_definition_query: bool = True, clear_selection: bool = True):
        """
        Clear filters or definition queries from all layers

        Args:
            wildcard_or_list: string to match to layer names, * is wildcarded, or pass a list
            clear_definition_query: clear the definition query from the layer
            clear_selection: deselect selected features

        Returns: None

        Examples:
            with wildcard, clear all filters
            >>> layers_clear_filters('*')  # noqa

            passing a list, clearing only the selection
            >>> layers_clear_filters(['mylayer', 'mynextlayer'], clear_definition_query=False)  # noqa
        """
        if isinstance(wildcard_or_list, str):
            _ = (self.layer_clear_filters(lyr, clear_definition_query, clear_selection) for lyr in
                 self.Map.listLayers(wildcard_or_list))
        else:
            for name in wildcard_or_list:
                self.layer_clear_filters(name, clear_definition_query=clear_definition_query, clear_selection=clear_selection)

    def features_show(self, lyrname: str, feat_col: str = '', fid: str = '', override_where: str = ''):
        """
        Show features in layer lyrname.
        Clears any selected features and removes the definition
        query for the layer

        Args:
            lyrname (str): Name of layer
            feat_col (str): Name of column in the layer
            fid: A value or iterable to search for in field feat_col
            override_where (str): provide a custom where statement to pass to the definition query, overriding feat_col and fid.

        Returns: None
        """

        def _f(v):
            if isinstance(v, str):
                return "'%s'" % v
            return str(v)

        if override_where:
            sql = override_where
        else:
            if isinstance(fid, (int, float, str)):
                fid = (fid,)

            lst = [_f(s) for s in fid]

            sql = '%s IN (%s)' % (feat_col, ','.join(lst))

        self.layer_clear_filters(lyrname)
        self.layer_definition_query_set(lyrname, sql)

    def layer_definition_query_clear(self, lyrname: str) -> None:
        """
        Clear layer definition using ArcGISPro CIM calls.

        Args:
            lyrname (str): The layer name

        Returns: None

        Notes:
            See https://community.esri.com/t5/python-questions/arcgis-pro-modifying-layer-definition-query-via/td-p/258922

        Examples:
            >>> layer_definition_query_clear('mylyr')  # noqa

        TODO: Debug/test me
        """
        lyr = self.Map.listLayers(lyrname)[0]
        cim_layer = lyr.getDefinition('V2')
        if cim_layer.featureTable.definitionFilterChoices:
            cim_layer.featureTable.definitionFilterChoices[0].definitionExpression = None
            cim_layer.featureTable.definitionExpression = None
        else:
            cim_layer.featureTable.definitionExpression = None
        lyr.setDefinition(cim_layer)

    def layer_definition_query_set(self, lyrname: str, query: str) -> None:
        """
        Set a definition query for a layer.

        Args:
            lyrname (str): Name of the layer.
            query (str): An SQL query, compatible with ArcPro query definition language

        Raises:
            errors.DisplayFeatureClassNotFound: If no feature matched lyrname
            errors.DisplayFeatureClassNameMatchedMultipleLayers: If multiple layers matched lyrname

        Examples:
            >>> Map.layer_definition_query_set('mylayer', 'SQ_ID IN (123,1234)')
        """
        lyrs = self.Map.listLayers(lyrname)
        if not lyrs:
            raise _errors.DisplayFeatureClassNotFound('Failed to set the layer definition query. No feature class matched the layer name %s.' % lyrname)

        if len(lyrs) > 1:
            raise _errors.DisplayFeatureClassNameMatchedMultipleLayers('Failed to set the layer definition query. Multiple feature classes matched layer name %s.' % lyrname)

        lyr = self.Map.listLayers(lyrname)[0]
        lyr.definitionQuery = query

    def element_set_text(self, element_name: str, txt: str) -> None:
        """
        Set text for text element with name element_name

        Args:
            element_name (str): the name of the text element
            txt (str): txt to set the text element to

        Returns: None

        Examples:
            >>> Map.element_set_text('txt_box_name', 'This is the text')
        """
        e = self.Layout.listElements('TEXT_ELEMENT', element_name)[0]
        e.text = txt

    def field_get_values(self, lyr_or_table_name: str, col: (str, list[str]), w: (str, None) = None, o: (str, None) = None, search_layers_first: bool = True, unique: bool = False):
        """Return a list of all values in column col in table tbl.

        If col is a single column, returns a list of values, otherwise returns
        a list of tuples of values where each tuple is one row.

        Columns included in the o parameter must be included in the col parameter!

        Args:
            lyr_or_table_name (str): input table or table view
            col (str, list[str]): input column name(s) as string or a list; valid options are:
                col='colA'
                col=['colA']
                col=['colA', 'colB', 'colC']
                col='colA,colB,colC'
                col='colA;colB;colC'
            w (str): where clause
            o (str, None): order by clause like 'ELEVATION DESC',
                default is None, which means order by object id if exists
            search_layers_first (bool): Tables and feature classes can have the same name. Search for layer lyr_or_table_name first, else looks at tables first
            unique (bool): Return unique items only

        Examples:
            >>> with Map('C:/my.arpx', 'mymap', 'C:/temp/my.log') as M:
            >>>     M.field_get_values('c:/foo/bar.shp', 'Shape_Length')
            >>>     M.field_get_values('c:/fo/bar.shp', 'SHAPE@XY')
            >>>     M.field_get_values('c:/foo/bar.shp', 'SHAPE@XY;Shape_Length', 'Shape_Length ASC')

            Columns in 'o' must be in 'col', otherwise RuntimeError is raised:
            >>>     M.field_get_values('c:/foo/bar.shp', 'SHAPE@XY', 'Shape_Length DESC')
            Traceback (most recent call last): ....
        """
        if search_layers_first:
            obj = get_item(self.Map.listLayers(lyr_or_table_name))
            if not obj:
                obj = get_item(self.Map.listTables(lyr_or_table_name))
        else:
            obj = get_item(self.Map.listTables(lyr_or_table_name))
            if not obj:
                obj = get_item(self.Map.listLayers(lyr_or_table_name))

        # unpack column names
        if isinstance(col, (list, tuple)):
            cols = col
        else:
            col = str(col)
            separ = ';' if ';' in col else ','
            cols = [c.strip() for c in col.split(separ)]

        # indicate whether one or more than one columns were specified
        multicols = False
        if len(cols) > 1:
            multicols = True

        # construct order by clause
        if o is not None:
            o = 'ORDER BY ' + str(o)
        else:
            pass

        # retrieve values with search cursor
        ret = []
        with _arcpy.da.SearchCursor(obj, cols, where_clause=w, sql_clause=(None, o)) as sc:
            for row in sc:
                if multicols:
                    ret.append(row)
                else:
                    ret.append(row[0])

        if unique:
            ret = list(set(ret))

        return ret


def get_item(objs: (list, tuple, None)) -> any:
    """
    Return first item in iter, else none.
    Used for this listXXXX functions in arcpy
    
    Args:
        objs: An iterable
        
    Returns:
        First item in the iterable objs
    """
    if isinstance(objs, (list, tuple)):
        if objs:
            return objs[0]
        return None
    return None


def combine_pdfs(out_pdf: str, pdf_path_or_list: (str, list[str]), wildcard: str = '') -> str:
    """Combine PDF documents using arcpy mapping module
    
    Args:
        out_pdf (str): output pdf document (.pdf)
        pdf_path_or_list (str, list[str]): list of pdf documents or folder path containing pdf documents.
        wildcard (str): Optional wildcard search (only applies when searching through paths)

    Returns:
        str: The output pdf name, this is just a normpathed out_pdf

    Examples:
        With a path
        >>> out_pdf = r'C:/Users/calebma/Desktop/test.pdf'  # noqa
        >>> path = r'C:/Users/calebma/Desktop/pdfTest'
        >>> combine_pdfs(out_pdf, path)
    
        With a list
        >>> out = r'C:/Users/calebma/Desktop/test2.pdf'
        >>> pdfs = [r'C:/Users/calebma/Desktop/pdfTest/Mailing_Labels5160.pdf',
                    r'C:/Users/calebma/Desktop/pdfTest/Mailing_Taxpayer.pdf',
                    r'C:/Users/calebma/Desktop/pdfTest/stfr.pdf']
        >>> combine_pdfs(out, pdfs)
    """

    # Create new PDF document
    pdfDoc = _mp.PDFDocumentCreate(out_pdf)

    # if list, use that to combine pdfs
    if isinstance(pdf_path_or_list, list):
        for pdf in pdf_path_or_list:
            pdfDoc.appendPages(pdf)
            _common.msg('Added "%s" to "%s"' % (pdf, _path.basename(out_pdf)))

    # search path to find pdfs
    elif isinstance(pdf_path_or_list, str):
        if _path.exists(pdf_path_or_list):
            search = _path.join(pdf_path_or_list, '{0}*.pdf'.format(wildcard))
            for pdf in sorted(_glob.glob(search)):
                pdfDoc.appendPages(_path.join(pdf_path_or_list, pdf))
                _common.msg('Added "%s" to "%s"' % (pdf, _path.basename(out_pdf)))

    # Save and close pdf document
    pdfDoc.saveAndClose()
    del pdfDoc
    _common.msg('Created: %s' % out_pdf)
    return out_pdf


if __name__ == '__main__':
    """simple debugging"""
    Prj = Project('S:/SPECIAL-ACL/ERAMMP2 Survey Restricted/current/data/GIS/_arcpro_projects/_templates/xsg_letters_per_crn/xsg_letters_per_crn.aprx')
