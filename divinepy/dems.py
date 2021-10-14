# AUTOGENERATED! DO NOT EDIT! File to edit: 01_dems.ipynb (unless otherwise specified).

__all__ = ['root', 'datasets', 'LOLA_TOPO']

# Cell
import math
from pathlib import Path

import dask
import hvplot.pandas  # noqa
import hvplot.xarray  # noqa
import numpy as np
import xarray as xr
import holoviews as hv
from divinepy import core

hv.extension('bokeh')
root = Path("/luna4/maye/dems")

datasets = {
    "divgdr": {
        "dem": ("divgdr/ldem_128_topo_img.tif", "Elevation", "m"),
        "slope": ("divgdr/ldem_128_slope_img.tif", "Slope", "deg"),
        "aspect": ("divgdr/ldem_128_az_img.tif", "Aspect", "deg(north)"),
    }
}

# Cell
class LOLA_TOPO:
    """Data reader class for LOLA Topography data.

    It accesses preproduced data for 128 ppd for DEM, slope, and aspect,
    located on the luna4 disk.

    It uses virtual dask.Arrays so that virtually no memory is consumed until you
    resolve a chain of operations with the `.compute()` call.

    Attributes
    ----------
    dem: xarray.DataArray
        LOLA DEM 128 ppd
    slope: xarray.DataArray
        Slope in percent, derived from `dem` using `gdaldem` command line tool.
    aspect: xarray.DataArray
        Aspect in degrees, derived from `dem` using `gdaldem` command line tool.
    """

    def __init__(self, dataset="divgdr", lat_limit=None):
        self.dataset_name = dataset
        self.lat_limit = lat_limit

        self.fnames = datasets[dataset]

        # assign name attributes data/slope/aspect:
        for key, (fname, long_name, unit) in self.fnames.items():
            setattr(self, f"{key}_fpath", root / fname)
            setattr(self, key, core.raster_to_xarray(root / fname).squeeze(drop=True))

        lats = np.linspace(90, -90, len(self.dem.y), endpoint=True)
        # Note that the PDS files originally are in lon180 but Pierre's files
        # for divdata are in lon360, hence the comment out.
        # TODO: Provide different sets of DEMs to user.
        #         lons = np.linspace(-180, 180, len(self.dem.x))
        lons = np.linspace(0, 360, len(self.dem.x), endpoint=False)

        for key, (_, long_name, unit) in self.fnames.items():
            o = getattr(self, key)
            o = o.assign_coords(lat=("y", lats))
            o = o.assign_coords(lon=("x", lons))
            o = o.swap_dims({"y": "lat", "x": "lon"})
            with xr.set_options(keep_attrs=True):
                scale = o.attrs["scales"][0]
                o = o * scale
            if self.lat_limit is not None:
                s = slice(self.lat_limit, -self.lat_limit)
                o = o.sel(lat=s, drop=True)
            if self.dataset_name == "divgdr" and key == "aspect":
                # change angles to surface normal angles
                o = np.mod(o + 180, 360)
            o.attrs["long_name"] = long_name
            o.attrs["units"] = unit
            o.name = key
            setattr(self, key, o)

    def slice_lat(self, data, lat):
        """Return the map `data` constrained to lat <= `lat`.

        Parameters
        ----------
        data: {'dem', 'slope','aspect'}
            String that choses which data product should be constrained.
        lat: int, float
            Limiting latitude value.
        """
        s = slice(lat, -lat)
        return getattr(self, data).sel(lat=s, drop=True)

    def convert_to_lon180(self):
        "Switch all three maps to -180/180 longitude system."
        for data in ["dem", "slope", "aspect"]:
            p = getattr(self, data)
            p.coords["lon"] = ((p.lon + 180) % 360) - 180
            with dask.config.set(**{"array.slicing.split_large_chunks": False}):
                setattr(self, data, p.sortby(p.lon))

        # da.assign_coords(lon=(((da.lon + 180) % 360) - 180))

    def convert_to_lon360(self):
        "Switch all three maps to 360 longitude system."
        for data in ["dem", "slope", "aspect"]:
            p = getattr(self, data)
            p.coords["lon"] = p.coords["lon"] % 360
            with dask.config.set(**{"array.slicing.split_large_chunks": False}):
                setattr(self, data, p.sortby(p.lon))

    def assign_new_latlon(self, lat, lon):
        "make sure longitude layout matches!"
        for data in ["dem", "slope", "aspect"]:
            p = getattr(self, data)
            p.coords["lon"] = lon
            p.coords["lat"] = lat
            setattr(self, data, p.sortby(p.lon))

    def get_elev_by_pixel(self, ilat, ilon):
        "Note: Decided to not apply offset!"
        val = self.dem.isel(lat=ilat, lon=ilon)
        return float(val * self.dem_scale)

    def get_elev_by_coord(self, lat, lon):
        "Note: Decided to not apply offset!"
        val = self.dem.sel(lat=lat, lon=lon, method="nearest")
        return float(val * self.dem_scale)

    def get_slope_by_pixel(self, ilat, ilon):
        """Convert stored degrees into dimensionless rise/run slope."""
        val = self.slope.isel(lat=ilat, lon=ilon)
        return math.tan(math.radians(val))

    def get_slope_by_coord(self, lat, lon):
        """Apply scale and return dimensonless rise/run slope."""
        val = self.slope.sel(lat=lat, lon=lon, method="nearest")
        return math.tan(math.radians(val))

    def get_az_by_pixel(self, ilat, ilon):
        return float(self.aspect.isel(lat=ilat, lon=ilon))

    def get_az_by_coord(self, lat, lon):
        return float(self.aspect.sel(lat=lat, lon=lon, method="nearest", drop=True))

    def get_scale(self, obj):
        return getattr(self, obj).attrs["scales"][0]

    @property
    def dem_scale(self):
        return self.get_scale("dem")

    @property
    def slope_scale(self):
        return self.get_scale("slope")

    @property
    def aspect_scale(self):
        return self.get_scale("aspect")

    def plot_dem(self, lat_min, lon_min, dlat=1, dlon=1, lat_max=None, lon_max=None):
        sliced = self.get_slice("dem", lat_min, lon_min, dlat, dlon, lat_max, lon_max)
        return sliced.hvplot(cmap="viridis", aspect="equal", title="DEM")

    def plot_slope(self, lat_min, lon_min, dlat=1, dlon=1, lat_max=None, lon_max=None):
        sliced = self.get_slice("slope", lat_min, lon_min, dlat, dlon, lat_max, lon_max)
        return sliced.hvplot(cmap="inferno", aspect="equal", title="Slope [degrees]")

    def plot_aspect(self, lat_min, lon_min, dlat=1, dlon=1, lat_max=None, lon_max=None):
        sliced = self.get_slice(
            "aspect", lat_min, lon_min, dlat, dlon, lat_max, lon_max
        )
        return sliced.hvplot(cmap="twilight", aspect="equal", title="Azimuth [degrees]")

    def get_slice(
        self, obj, lat_min, lon_min, dlat=None, dlon=None, lat_max=None, lon_max=None
    ):
        """Slice a rectangular data tile out of the map.

        Parameters
        ----------
        obj: {'dem','slope','aspect'}
            Determines the object that will be sliced
        lat_min: float
            Lower left corner latitude of slice.
        lon_min: float
            Lower left corner longitude of slice.
        dlat: float
            Delta to be added to `lat_min`
        dlon: float
            Delta lon to be added to `lon_min`
        lat_max: float
            Alternative for dlat, to set upper end of latitude interval.
        lon_max: float
            Alternative for dlon, to set right end of longitude interval.

        Returns
        -------
        xarray.DataArray
            Sliced for the provided coordinate values.
        """
        data = getattr(self, obj)
        if lon_max is None:
            lon_max = lon_min + dlon
        if lat_max is None:
            lat_max = lat_min + dlat
        return data.sel(lat=slice(lat_max, lat_min), lon=slice(lon_min, lon_max))