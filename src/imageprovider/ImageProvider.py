
import os
import subprocess

from azure.storage.blob import BlockBlobService
from os import walk
from utils.logger import get_logger
from imageprovider.ImageProviderConfig import ImageProviderConfig


class ImageProvider:
    EPSG_LV95 = "EPSG:2056"
    EPSG_WGS84 = "EPSG:4326"
    def __init__ (self, config: ImageProviderConfig):
        self.logger = get_logger("imageprovider")
        self.config = config
        self.all_images = []
        if self.config.is_azure:
            self.block_blob_service = BlockBlobService(account_name=self.config.azure_blob_account, account_key=self.config.azure_blob_key) 
            for image in self.block_blob_service.list_blobs(self.config.azure_blob_name):
                self.all_images.append(image.name)
        else:
            files = []
            for (dirpath, dirnames, filenames) in walk(self.config.input_url):
                files.extend(filenames)
                break
            self.all_images = files

    def get_image(self, image_number: str):
        tif_image_names = []
        for image in self.all_images:
            if image.find(image_number) >= 0:
                if (os.path.exists(self.config.input_url + "/" + image)) and (self.config.is_azure):
                    print("skip download file " + image + " because file already exists")
                else:
                    self._download(image)
                if image.find("tif") >= 0:
                    tif_image_names.append(image)
        if len(tif_image_names) == 0:
            print("no images with number " + image_number + " were found")
        return tif_image_names
    
    def get_images_names(self, image_number: str):
        tif_image_names = []
        for image in self.all_images:
            if image.find("tif") >= 0 and image.find(image_number) >=0:
                tif_image_names.append(image)
        return tif_image_names
    
    def get_image_as_wgs84(self, image_number):
        image_names = self.get_image(image_number)
        downloaded_images = []
        for image_name in image_names:
            try:
                self._set_to_lv95(image_name)
                self._convert_to_wgs84(image_name)
                downloaded_images.append(image_name)
            except Exception as e:
                self.logger("failed to convert image {0} error: {1}".format(image_name, e))
                pass
        return downloaded_images
 
    def _convert_to_wgs84 (self, image_name):
        path = self.config.input_url + "/" + image_name
        path_out = self.config.output_url + "/" + image_name
        if os.path.exists(path_out):
            print("file " + path_out + " already exists, skip tranformation")
            return
        print("convertig image " + image_name + " to WGS84, that may take some time")
        bash_command = "gdalwarp " + path + " " + path_out + " -s_srs " + self.EPSG_LV95 + " -t_srs " + self.EPSG_WGS84
        if not os.path.exists(self.config.output_url):
                os.makedirs(self.config.output_url)
        process = subprocess.Popen(bash_command.split(), stdout=subprocess.PIPE)
        output, error = process.communicate() 
    
    def _set_to_lv95 (self, image_name):
        image_url = self.config.input_url + "/" + image_name
        bash_command = "python ./utils/gdal_edit.py -a_srs "+ self.EPSG_LV95 + " " + image_url
        process = subprocess.Popen(bash_command.split(), stdout=subprocess.PIPE)
        output, error = process.communicate() 

    def _download(self, image_name):
        if not self.config.is_azure:
            return
        path = self.config.input_url
        print("downloading " + image_name + " to " + path + "/" + image_name)
        if not os.path.exists(path):
                os.makedirs(path)
        self.block_blob_service.get_blob_to_path(self.config.azure_blob_name, image_name, path + "/" + image_name)
