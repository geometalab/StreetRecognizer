import os
import json
import subprocess

from osgeo import gdal, ogr
from imageprocessor.ImageProcessorConfig import ImageProcessorConfig
from geodataprovider.GeoDataProvider import GeoDataProvider


class ImageProcessor:
    burn_attribute = None
    def __init__(self, config: ImageProcessorConfig):
        self.config = config

    def get_raster_from_geojson(self, geojson_path:str, pixel_width: int, pixel_height: int):
        file_name = os.path.splitext(os.path.basename(geojson_path))[0] + "_raster.tif" 
        geojson = ogr.Open(geojson_path)
        jsonlayer = geojson.GetLayer()
        x_min, x_max, y_min, y_max = jsonlayer.GetExtent()

        cols = int((x_max - x_min) / pixel_width)
        rows = int((y_max - y_min) / pixel_height)      

        target_image = gdal.GetDriverByName('GTiff').Create(os.path.join(self.config.output_path, file_name), cols, rows*-1, 1, gdal.GDT_Byte) 
        target_image.SetGeoTransform((x_min, pixel_width, 0, y_max, 0, pixel_height))
        # todo set projection not as string
        target_image.SetProjection('GEOGCS["WGS 84",DATUM["WGS_1984",SPHEROID["WGS 84",6378137,298.257223563,AUTHORITY["EPSG","7030"]],AUTHORITY["EPSG","6326"]],PRIMEM["Greenwich",0],UNIT["degree",0.0174532925199433],AUTHORITY["EPSG","4326"]]')
        if self.burn_attribute:
            gdal.RasterizeLayer(target_image, [1], jsonlayer, options=["ATTRIBUTE="+self.burn_attribute])
        else:
            gdal.RasterizeLayer(target_image, [1], jsonlayer, burn_values=[255])
        target_image.FlushCache()
        target_image = None
        return os.path.join(self.config.output_path, file_name)



    def cut_geo_image(self, base_image_path: str, to_cut_image_path: str):
        file_name = os.path.splitext(os.path.basename(base_image_path))[0] + "_cut_raster.tif"
        lower_left = GeoDataProvider(base_image_path)
        upper_right = GeoDataProvider(base_image_path)
        # todo may use python wrapper and not command line interface
        bash_command = "gdalwarp -te {0} {1} {2} {3} {4} {5}".format(
                lower_left.east, 
                lower_left.north, 
                upper_right.east, 
                upper_right.north,
                to_cut_image_path,
                os.path.join(self.config.output_path, file_name))
        process = subprocess.Popen(bash_command.split(), stdout=subprocess.PIPE)
        output, error = process.communicate() 
        return os.path.join(self.config.output_path, file_name)
            
    def add_print_attribute(self, geojson_path: str):
        with open(geojson_path, "r+") as file:
            data = json.load(file)
            for feature in data["features"]:
                properties = feature["properties"]
                if properties.get(self.config.filter.field):
                    try:
                        properties[self.config.filter.name] = self.config.filter.values[properties.get(self.config.filter.field)]
                    except:
                        properties[self.config.filter.name] = self.config.filter.values["default"]
                else:
                    properties[self.config.filter.name] = self.config.filter.values["empty"]
            file.seek(0)
            json.dump(data, file, indent=4)
            file.truncate()
        return self.config.filter.name
