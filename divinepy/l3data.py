# AUTOGENERATED! DO NOT EDIT! File to edit: 04_l3data.ipynb (unless otherwise specified).

__all__ = ['DIVINER_URL', 'root', 'L3DataManager', 'get_l3_image_paths', 'L3Data', 'STData']

# Cell
import warnings
from pathlib import Path

import numpy as np
import pvl
from planetarypy import geotools as gt
import matplotlib.pyplot as plt
from planetarypy.utils import url_retrieve
from yarl import URL

DIVINER_URL = URL(
    "https://pds-geosciences.wustl.edu/lro/lro-l-dlre-4-rdr-v1/lrodlr_1001/data"
)

root = Path("/luna4/maye/l3_data")

# Cell
class L3DataManager:
    @property
    def labels(self):
        return sorted(list(root.glob("dgdr_*.lbl")))

    @property
    def images(self):
        return sorted(list(root.glob("dgdr_*.tif")))


def get_l3_image_paths():
    return L3DataManager().images


class L3Data:
    GDR_L3_URL = DIVINER_URL / "gdr_l3"

    def __init__(
        self,
        cycle=None,
        datatype="ST",
        map_res=1,
        projection="cylindrical",
        format="jp2",
        year=None,
    ):
        self.cycle = cycle
        self.datatype = datatype
        self.map_res = map_res
        self.projection = projection
        self.format = format
        self.year = year

        if cycle is None and year is None:
            warnings.warn("Set `year` for getting a correct folder URL.")

    @property
    def cycle(self):
        return self._cycle

    @cycle.setter
    def cycle(self, value):
        self._cycle = value

    @property
    def year(self):
        if self.cycle is not None:
            return str(self.cycle)[:4]
        else:
            return self._year

    @year.setter
    def year(self, value):
        self._year = str(value)

    @property
    def map_res(self):
        return self._map_res

    @map_res.setter
    def map_res(self, value):
        self._map_res = str(value).zfill(3)

    @property
    def datatype(self):
        return self._datatype

    @datatype.setter
    def datatype(self, value):
        """Set datatype string.

        This is for a Diviner GDR L3 datatype.

        Parameters
        ----------
        value : {"ra", "rms", "st", "tbol"}
            RA = Rock abundance
            RMS = RMS error for RA
            ST = Regolith temperature
            TBOL = Average Bolometric Temperature
        """
        allowed = "ra rms st tbol".split()
        if not value.lower() in allowed:
            raise ValueError(f"Only {allowed} allowed.")
        else:
            self._datatype = value.lower()

    @property
    def second_token(self):
        return "avg" if self.datatype == "tbol" else "clc"

    @property
    def fname(self):
        "Construct L3 GDR data filename."

        res = 128
        if self.datatype == "tbol":
            res = self.map_res
        return f"dgdr_{self.datatype}_{self.second_token}_cyl_{self.cycle}n_{res}_{self.format}.{self.format}"

    @property
    def label(self):
        return str(Path(self.fname).with_suffix(".lbl"))

    @property
    def folder_url(self):
        return self.GDR_L3_URL / self.year / self.projection / self.format

    @property
    def data_url(self):
        return self.folder_url / self.fname

    @property
    def label_url(self):
        return self.folder_url / self.label

    def download_label(self, subfolder="/luna4/maye/l3_data"):
        p = Path(subfolder)
        p.mkdir(exist_ok=True)
        url_retrieve(self.label_url, Path(subfolder) / self.label)

    def download_data(self, subfolder="/luna4/maye/l3_data", overwrite=False):
        p = Path(subfolder)
        p.mkdir(exist_ok=True)
        savepath = p / self.fname
        if savepath.exists() and not overwrite:
            print("File exists, use `overwrite=True` to force download.")
            return
        else:
            url_retrieve(self.data_url, Path(subfolder) / self.fname)

# Cell
class STData:
    root = Path("/luna4/maye/l3_data")
    name = "st"

    @classmethod
    def from_fpath(cls, fpath):
        cycle = int(fpath.name.split("_")[4][:-1])
        return cls(cycle)

    def __init__(self, cycle):
        self.cycle = cycle
        self.l3divdata = L3Data(cycle=cycle)
        self.img = gt.ImgData(str(root / self.l3divdata.fname))

    def read_window(self, ul_lon=0, ul_lat=1, width_degrees=1):
        ul = gt.Point.copy_geodata(self.img.center, lon=ul_lon, lat=ul_lat)
        ul.lonlat_to_pixel()
        lr = gt.Point.copy_geodata(
            ul, lon=ul_lon + width_degrees, lat=ul_lat - width_degrees
        )
        lr.lonlat_to_pixel()
        win = gt.Window(ulPoint=ul, lrPoint=lr)
        self.img.read_window(win)

    @property
    def label(self):
        return pvl.load(root / self.l3divdata.label)

    @property
    def fname(self):
        return root / self.l3divdata.fname

    @property
    def SCALING_FACTOR(self):
        return self.label["UNCOMPRESSED_FILE"]["IMAGE"]["SCALING_FACTOR"]

    @property
    def OFFSET(self):
        return self.label["UNCOMPRESSED_FILE"]["IMAGE"]["OFFSET"]

    @property
    def NODATA(self):
        return self.label["UNCOMPRESSED_FILE"]["IMAGE"]["MISSING_CONSTANT"]

    @property
    def data(self):
        data = self.img.data.astype("float")
        data[data == self.NODATA] = np.nan
        return data

    @property
    def scaled_data(self):
        return self.data * self.SCALING_FACTOR + self.OFFSET

    def get_pixel(self, xoff, yoff):
        value = np.squeeze(self.img.ds.ReadAsArray(xoff, yoff, 1, 1))
        if value == self.NODATA:
            return np.nan
        else:
            return value * self.SCALING_FACTOR + self.OFFSET

    def plot_window(self):
        plt.figure()
        plt.imshow(self.scaled_data, cmap="plasma")
        plt.colorbar()

    @property
    def window_mean(self):
        return np.nanmean(self.scaled_data)

    @property
    def window_std(self):
        return np.nanstd(self.scaled_data)

    @property
    def n_valid(self):
        return np.count_nonzero(~np.isnan(self.data))