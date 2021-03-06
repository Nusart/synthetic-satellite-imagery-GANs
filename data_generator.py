# module to preprocess data
# Sarthak Mishra 18388

from enum import Enum
from typing import Tuple, Optional, List

import numpy as np
import pandas as pd
import rasterio
from rasterio.enums import Resampling
from rasterio.plot import reshape_as_image
from sklearn.preprocessing import MinMaxScaler
from pathlib import Path
from keras.preprocessing.image import load_img, img_to_array


class Purpose(Enum):
    TRAIN = 'train'
    TEST = 'test'
    VAL = 'plot'
    PLOT = 'plot'


class DataGenerator:
    dataset: str = 'sample'

    def images_df(self, purpose: Purpose = Purpose.TRAIN) -> pd.DataFrame:
        pass

    def load(self, batch: int = 1, purpose: Purpose = Purpose.TRAIN,
             random_state=None) -> Tuple[List[np.ndarray], List[np.ndarray]]:
        pass


class SentinelDataGenerator(DataGenerator):

    def __init__(self,
                 dataset: str,
                 descriptor: str = 'data_descriptor.csv',
                 landcover_mask_shape=(1, 128, 128),
                 satellite_image_shape=(4, 128, 128),
                 feature_range: Tuple[int, int] = (-1, 1),
                 landcover_mask_resampling: Optional[Resampling] = None,
                 satellite_image_resampling: Optional[Resampling] = None,
                 clip: Optional[int] = None
                 ):
        self.dataset = dataset
        self.descriptor = descriptor
        self.landcover_mask_shape = landcover_mask_shape
        self.satellite_image_shape = satellite_image_shape
        self.feature_range = feature_range
        self.landcover_mask_resampling = landcover_mask_resampling
        self.satellite_image_resampling = satellite_image_resampling
        self.clip = clip

    def images_df(self, purpose: Purpose = Purpose.TRAIN):
        path = Path('../data/%s/%s/%s' % (self.dataset, purpose.value, self.descriptor)).resolve()
        return pd.read_csv(path)

    def load(self, batch: int = 1, purpose: Purpose = Purpose.TRAIN,
             random_state=None) -> Tuple[List[np.ndarray], List[np.ndarray]]:

        images_df = self.images_df(purpose)
        images_df = images_df.sample(frac=1, random_state=random_state)

        for batch_df in [images_df[i:i + batch] for i in range(0, images_df.shape[0], batch)]:

            satellite_images = []
            landcover_masks = []

            for _, row in batch_df.iterrows():
                row_id = row['id']
                satellite_image_path = Path(
                    'data/%s/%s/S/S_%s.tif' % (self.dataset, purpose.value, row_id)
                ).resolve()

                landcover_mask_path = Path(
                    'data/%s/%s/LC/LC_%s.tif' % (self.dataset, purpose.value, row_id)
                ).resolve()

                satellite_image = self.read_raster(satellite_image_path, self.satellite_image_shape, self.feature_range,
                                                   self.satellite_image_resampling)
                landcover_mask = self.read_raster(landcover_mask_path, self.landcover_mask_shape, self.feature_range,
                                                  self.landcover_mask_resampling)

                satellite_images.append(satellite_image)
                landcover_masks.append(landcover_mask)

            yield np.array(satellite_images), np.array(landcover_masks)

    @staticmethod
    def read_raster(path: str, out_shape: Tuple[int, int], feature_range: Tuple[int, int],
                    resampling: Optional[Resampling] = None,
                    clip: Optional[int] = None) -> np.ndarray:

        if resampling:
            raster = rasterio.open(path, dtype='int16').read(out_shape=out_shape, resampling=resampling)
        else:
            raster = rasterio.open(path, dtype='int16').read(out_shape=out_shape)

        scaler = MinMaxScaler(feature_range=feature_range)
        raster = np.nan_to_num(raster, posinf=0, neginf=0)
        raster = np.clip(raster, 0, clip) if clip else raster
        raster = [scaler.fit_transform(channel) for channel in raster]
        return reshape_as_image(raster)


class RGBDataGenerator(DataGenerator):

    def __init__(self, dataset: str, descriptor: str = 'data_descriptor.csv'):
        self.dataset = dataset
        self.descriptor = descriptor

    def images_df(self, purpose: Purpose = Purpose.TRAIN) -> pd.DataFrame:
        path = Path('data/%s/%s/%s' % (self.dataset, purpose.value, self.descriptor)).resolve()
        return pd.read_csv(path)

    def load(self, batch: int = 1, purpose: Purpose = Purpose.TRAIN,
             random_state=None) -> Tuple[List[np.ndarray], List[np.ndarray]]:

        images_df = self.images_df(purpose)
        images_df = images_df.sample(frac=1, random_state=random_state)

        for batch_df in [images_df[i:i + batch] for i in range(0, images_df.shape[0], batch)]:

            target_images = []
            condition_images = []

            for _, row in batch_df.iterrows():
                row_id = row['id']
                target_image_path = Path(
                    'data/%s/%s/target/%s.png' % (self.dataset, purpose.value, '{:04d}'.format(row_id))
                ).resolve()

                condition_image_path = Path(
                    'data/%s/%s/condition/%s.png' % (self.dataset, purpose.value, '{:04d}'.format(row_id))
                ).resolve()

                target_image = self.read_raster(target_image_path)
                condition_image = self.read_raster(condition_image_path)

                target_images.append(target_image)
                condition_images.append(condition_image)

            yield np.array(target_images) / 127.5 - 1.0, np.array(condition_images) / 127.5 - 1.0

    @staticmethod
    def read_raster(path):
        return img_to_array(load_img(path))
