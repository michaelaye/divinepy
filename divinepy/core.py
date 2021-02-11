# AUTOGENERATED! DO NOT EDIT! File to edit: 00_core.ipynb (unless otherwise specified).

__all__ = ['raster_to_xarray', 'mapcycle_to_xarray', 'read_images_into_stacked_array',
           'read_mapcycles_into_stacked_array', 'get_data_for_pixel']

# Internal Cell
from pathlib import Path

import xarray as xr

# Cell
def raster_to_xarray(fpath, chunk_scale=2):
    """Read raster image into an xarray.DataArray.

    Using the `chunks` keyword in the open_rasterio method
    activates the return of an out-of-memory virtual array instead
    of the in-memory xarray.DataArray

    fpath: pathlib.Path, str
    chunk_scale: int
        Multiplier for the hardcoded 2048/1024 chunk-sizes for
        x/y axes.
    """
    fpath = Path(fpath)
    da = xr.open_rasterio(
        fpath, chunks={"x": chunk_scale * 2048, "y": chunk_scale * 1024}
    )
    return da

# Cell
def mapcycle_to_xarray(fpath, chunk_scale=2):
    """Read an Diviner map cycle rasterio image into a dask.array.

    The cycle identifier will be read from the filename and added
    to the xarray as a coordinate value.

    fpath: str, pathlib.Path
    chunk_scale: int
        Scaling the chunk
    """
    fpath = Path(fpath)
    da = raster_to_xarray(fpath)
    cycle = int(fpath.name.split("_")[4][:-1])
    da = da.assign_coords(band=[cycle])
    return da.rename({"band": "time"})

# Cell
def read_images_into_stacked_array(image_paths, name, chunk_scale=2):
    arrays = [raster_to_xarray(p, chunk_scale) for p in image_paths]
    stack = xr.concat(arrays, "time")
    stack.name = name
    return stack


def read_mapcycles_into_stacked_array(image_paths, name, chunk_scale=2):
    arrays = [mapcycle_to_xarray(p, chunk_scale) for p in image_paths]
    stack = xr.concat(arrays, "time")
    stack.name = name
    return stack


def get_data_for_pixel(xoff, yoff, ReaderClass, image_paths, name, chunk_scale=1):
    stack = read_images_into_stacked_array(image_paths, name, chunk_scale)
    pix = stack.isel(x=xoff, y=yoff)
    pix = pix.where(pix != -32768)
    img = ReaderClass.from_fpath(image_paths[0])
    pix = pix * img.SCALING_FACTOR + img.OFFSET
    return pix.compute()