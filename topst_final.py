# -*- coding: utf-8 -*-
"""TOPST_FINAL

Automatically generated by Colab.

Original file is located at
    https://colab.research.google.com/drive/1JKqL4e1enqrS31UHJoKQ3Godj5q_aWJk

CLIMATE SMART AGRICULTURE IN MARYLAND
A regional view of the past with applications to the present. Python spatial and tabular analysis using multiple variables to look at a single time slice. This code can be a combination of cloud and local based analysis. A purpose for this exercise is to use use public research data for derived conclusions view the impacts climate change has on agriculture a look at what farmers can do and why we need to support them.

NASA Acres has defined the Essential Agricultural Variables or EAVs. These were designed by NASA Acres to define the capabilities of the top satellite data scientists and practitioners who make up NASA Acres Research, Development, and Extension partners, and the needs of decision-making-collaborators already in our network, to identify an initial set of focus.
1. Cropland and Crop Type Mapping
2. Crop and Crop Type Area Estimation


Derived results will be the county level statistics of impacts of harvestable acreage. To achieve this, a basic workflow we can
1. Use api to call in the CDL dataset to map crop types.

Then
1. Access the Sea level rise (elevation dataset) to identify new areas of potential areas that are at risk of future flooding. Clip to county of interest
2. Compare the CDL with the SLR mask and with out to identify the NOAA estimated loss of land.

Then using MODIS create a time series for NDVI of the masked crop land, derive insights about trends in NDVI
1. Use NDVI to create a time series looking backwards in time at areas that have experienced flooding to visualize the moving from productive farms to moderate quality.




---


This all together would allow us to make a predictive analysis for Maryland in the future under the projections of sea level rise. 
Given the current conditions, subtracting the sea level rise inundated areas. 
Then given the remaining areas, making predictions about the trends of NDVI given the trends in historical areas that are near impacted areas. We cannot say that 
sea level rise is driving the decrease because there are many other factor and decisions that farmers make around how much to plant, how much to harvest, chemicals applied,
 growing degree days, soil and soil moisture conditions. But this module should provide the ability to make insights about potential causes and impacts.



The data story that we have derived is about sea level rise in Maryland and the impact that it has on the production levels with in the state. From this module,
 we can provide students with the ability to draw from multiple data sources, as well as derive insights using historical and future viewing data sets.



The U.S. Mid-Atlantic has seen higher rates of sea level rise, marshes may be especially vulnerable. In the Chesapeake Bay, sea level rise has already
 contributed to the degradation of over 80,000 ha (70%) of tidal marsh (Taylor, Curson, Verutes, et al). This view can help us to understand the impacts 
 that small levels of sea level rise have on land.




We can prompt the user to think about future impacts outside the direct sea level rise projections, allowing them to include a more full picture, 
and finally using that picture to identify economic impacts that action or inaction causes. This begs the question, what can the public do to enact 
changes, rather than putting the pressure on farmers to change?

---


SOURCES

Taylor, L., Curson, D., Verutes, G.M. et al. Mapping sea level rise impacts to identify climate change adaptation opportunities in the Chesapeake and Delaware Bays,
 USA. Wetlands Ecol Manage 28, 527541 (2020). https://doi.org/10.1007/s11273-020-09729-w

Mondal, P., Walter, M., Miller, J. et al. The spread and cost of saltwater intrusion in the US Mid-Atlantic. Nat Sustain 6, 13521362 (2023).
 https://doi.org/10.1038/s41893-023-01186-6

UMD + NOAA short web course
https://www.mdsg.umd.edu/coastal-climate-resilience/farming-flooding-salt-land-loss#:~:text=Farmers%20and%20woodlot%20owners%20in%20Maryland%20and%20Virginia%20are%20facing,under%20saltier%20or%20wetter%20conditions.
"""

USERNAME = 'NASA USERNAME'
PASSWORD = 'NASA PASSWORD'

# !pip install rasterio

import geopandas as gpd
import rasterio
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from shapely.geometry import box
import numpy as np
import requests
import xml.etree.ElementTree as ET
import matplotlib.pyplot as plt
from io import BytesIO
import os
from rasterio.warp import calculate_default_transform, reproject, Resampling
from datetime import datetime, timedelta

def reproject_raster(src_dataset, src_crs, src_transform, dst_crs='EPSG:4326'):
    dst_crs = rasterio.crs.CRS.from_string(dst_crs)
    dst_transform, dst_width, dst_height = calculate_default_transform(
        src_crs, dst_crs,
        src_dataset.width, src_dataset.height,
        *src_dataset.bounds)
    dst_kwargs = src_dataset.meta.copy()
    dst_kwargs.update({
        'crs': dst_crs,
        'transform': dst_transform,
        'width': dst_width,
        'height': dst_height})
    dst_data = np.zeros((src_dataset.count, dst_height, dst_width), dtype=src_dataset.dtypes[0])
    for i in range(1, src_dataset.count + 1):
        reproject(
            source=rasterio.band(src_dataset, i),
            destination=dst_data[i-1],
            src_transform=src_transform,
            src_crs=src_crs,
            dst_transform=dst_transform,
            dst_crs=dst_crs,
            resampling=Resampling.nearest)
    return dst_data, dst_kwargs

def format_cdl_url(fips,year):
    base_url = "https://nassgeodata.gmu.edu/axis2/services/CDLService/GetCDLFile"
    url = f"{base_url}?year={year}&fips={fips}"
    return url

def get_srl_raster():
    slr_path = '/content/MD_East_slr_depth_3_5ft.tif'
    with rasterio.open(slr_path) as slr_raster:
            slr_meta = slr_raster.meta
            slr_meta['nodata'] = 0
            slr_reprojected, slr_meta_reprojected = reproject_raster(src_dataset=slr_raster, src_crs=slr_meta['crs'], src_transform=slr_meta['transform'])
    return slr_reprojected, slr_meta_reprojected

"""

# Gather sea level rise (SLR) raster, crop land database (CDL) raster, and County geodatabase

To understand the nature of Maryland agriculture we can begin by using the CDL. This raster dataset comes at a 30 meter spatial resolution. We can access this data through their api. The current configuration allows data to be pulled at the county level.

COUNTY LEVEL CDL FOR FIPS
https://nassgeodata.gmu.edu/axis2/services/CDLService/GetCDLFile

This view provides insight into the common commodities that are grown in Maryland in the desired year.
"""

crop_mapping = {0: "Background", 1: "Corn", 2: "Cotton", 3: "Rice", 4: "Sorghum", 5: "Soybeans", 6: "Sunflower", 10: "Peanuts",
11: "Tobacco", 12: "Sweet Corn", 13: "Pop or Orn Corn", 14: "Mint", 21: "Barley", 22: "Durum Wheat",23: "Spring Wheat", 24: "Winter Wheat", 25: "Other Small Grains", 26: "Dbl Crop WinWht/Soybeans", 27: "Rye",
28: "Oats", 29: "Millet", 30: "Speltz", 31: "Canola", 32: "Flaxseed", 33: "Safflower", 34: "Rape Seed",35: "Mustard", 36: "Alfalfa", 37: "Other Hay/Non Alfalfa", 38: "Camelina", 39: "Buckwheat", 41: "Sugarbeets",
42: "Dry Beans", 43: "Potatoes", 44: "Other Crops", 45: "Sugarcane", 46: "Sweet Potatoes", 47: "Misc Vegs & Fruits",48: "Watermelons", 49: "Onions", 50: "Cucumbers", 51: "Chick Peas", 52: "Lentils", 53: "Peas", 54: "Tomatoes",
55: "Caneberries", 56: "Hops", 57: "Herbs", 58: "Clover/Wildflowers", 59: "Sod/Grass Seed", 60: "Switchgrass",61: "Fallow/Idle Cropland", 63: "Forest", 64: "Shrubland", 65: "Barren", 66: "Cherries", 67: "Peaches",
68: "Apples", 69: "Grapes", 70: "Christmas Trees", 71: "Other Tree Crops", 72: "Citrus", 74: "Pecans",75: "Almonds", 76: "Walnuts", 77: "Pears", 81: "Clouds/No Data", 82: "Developed", 83: "Water", 87: "Wetlands",
88: "Nonag/Undefined", 92: "Aquaculture", 111: "Open Water", 112: "Perennial Ice/Snow", 121: "Developed/Open Space",122: "Developed/Low Intensity", 123: "Developed/Med Intensity", 124: "Developed/High Intensity", 131: "Barren",
141: "Deciduous Forest", 142: "Evergreen Forest", 143: "Mixed Forest", 152: "Shrubland", 176: "Grass/Pasture",190: "Woody Wetlands", 195: "Herbaceous Wetlands", 204: "Pistachios", 205: "Triticale", 206: "Carrots",
207: "Asparagus", 208: "Garlic", 209: "Cantaloupes", 210: "Prunes", 211: "Olives", 212: "Oranges",213: "Honeydew Melons", 214: "Broccoli", 215: "Avocados", 216: "Peppers", 217: "Pomegranates", 218: "Nectarines",
219: "Greens", 220: "Plums", 221: "Strawberries", 222: "Squash", 223: "Apricots", 224: "Vetch",225: "Dbl Crop WinWht/Corn", 226: "Dbl Crop Oats/Corn", 227: "Lettuce", 228: "Dbl Crop Triticale/Corn",
229: "Pumpkins", 230: "Dbl Crop Lettuce/Durum Wht", 231: "Dbl Crop Lettuce/Cantaloupe", 232: "Dbl Crop Lettuce/Cotton",233: "Dbl Crop Lettuce/Barley", 234: "Dbl Crop Durum Wht/Sorghum", 235: "Dbl Crop Barley/Sorghum",
236: "Dbl Crop WinWht/Sorghum", 237: "Dbl Crop Barley/Corn", 238: "Dbl Crop WinWht/Cotton",239: "Dbl Crop Soybeans/Cotton", 240: "Dbl Crop Soybeans/Oats", 241: "Dbl Crop Corn/Soybeans", 242: "Blueberries",
243: "Cabbage", 244: "Cauliflower", 245: "Celery", 246: "Radishes", 247: "Turnips", 248: "Eggplants",249: "Gourds", 250: "Cranberries", 254: "Dbl Crop Barley/Soybeans", 255: ""}

county = 'Talbot'
code = "24041"
year = 2018


service_url = format_cdl_url(code, year)
response = requests.get(service_url)
root = ET.fromstring(response.content)
tif_url = root.find('.//returnURL').text
cdl_data = rasterio.open(tif_url)
cdl_meta = cdl_data.meta
cdl_reprojected, cdl_meta_reprojected = reproject_raster(src_dataset=cdl_data, src_crs=cdl_meta['crs'], src_transform=cdl_meta['transform'])

"""The eastern seaboard has seen changes in the sea level along with increase flooding and the decrease in predictability of water flow from rivers. This daa comes from NOAA (learn more here https://coast.noaa.gov/data/digitalcoast/pdf/slr-inundation-methods.pdf)

This raster is the projection of inudated areas by the year of 2050. Data access can be found here https://coast.noaa.gov/slrdata/Depth_Rasters/MD/index.html
"""

slr_reprojected, slr_meta_reprojected = get_srl_raster()

"""# Gather NDVI values"""

def get_appeears_token(username, password):
    response = requests.post('https://appeears.earthdatacloud.nasa.gov/api/login',auth=(username, password))
    return response.json()['token']

def submit_appeears_task(token, task):
    response = requests.post('https://appeears.earthdatacloud.nasa.gov/api/task',json=task,headers={'Authorization': f'Bearer {token}'})
    return response.json()

def get_appeears_bundle(token, task_id):
    response = requests.get(f'https://appeears.earthdatacloud.nasa.gov/api/bundle/{task_id}',headers={'Authorization': f'Bearer {token}'})
    return response.json()

def load_county_data():
    sea_level_path = '/content/Talbot_County.geojson'
    sea_level_gdf = gpd.read_file(sea_level_path)
    return sea_level_gdf

def day_of_year_to_date2(day_of_year_str):
    year = int(day_of_year_str[:4])
    day_of_year = int(day_of_year_str[4:])
    start_date = datetime(year, 1, 1)
    target_date = start_date + timedelta(days=day_of_year - 1)
    return target_date.strftime('%m-%d-%Y')

def resample_using_cdl(data, data_meta, cdl_meta_reprojected):
    resampled_data = np.zeros(
        (data.shape[0], cdl_meta_reprojected['height'], cdl_meta_reprojected['width']),
        dtype=data.dtype
    )

    for i in range(data.shape[0]):
        reproject(
            source=data[i],
            destination=resampled_data[i],
            src_transform=data_meta['transform'],
            src_crs=data_meta['crs'],
            dst_transform=cdl_meta_reprojected['transform'],
            dst_crs=cdl_meta_reprojected['crs'],
            resampling=Resampling.bilinear
        )
    updated_meta = data_meta.copy()
    updated_meta.update({
        'transform': cdl_meta_reprojected['transform'],
        'width': cdl_meta_reprojected['width'],
        'height': cdl_meta_reprojected['height'],
        'crs': cdl_meta_reprojected['crs']
    })

    return resampled_data, updated_meta

county_data = load_county_data()
county_reprojected = county_data.to_crs('EPSG:4326')
us = county_reprojected.geometry.iloc[0]
minx, miny, maxx, maxy = us.bounds


bbox = [[maxx, miny],
        [maxx, maxy],
        [minx, maxy],
        [minx, maxy],
        [minx, miny]]


start = f'06-01-{year}'
end = f'09-30-{year}'


products = [{'layer': '_250m_16_days_NDVI', 'product':'MOD13Q1.061'}]

token = get_appeears_token(f'{USERNAME}', f'{PASSWORD}')

task = {'task_type': 'area',
          'task_name': 'MODIS',
          'params': {"geo": {"type": "FeatureCollection",
                            "features": [{"type": "Feature",
                                          "geometry": {"type": "MultiPolygon",
                                                      "coordinates": [[bbox]]},
                                          "properties": {}}],
                            "fileName": "Polygon"},
                    'dates': [{'startDate': start, 'endDate': end}],
                    'layers': products,
                    'coordinates': bbox,
                    "output": {"format": {"type": "geotiff"},
                              "projection": "native"}}}
task_id = submit_appeears_task(token, task)

bundle = get_appeears_bundle(token, task_id['task_id'])

data = {}

for file in bundle['files']:
    file_id = file['file_id']
    if 'NDVI' in file['file_name']:
      if '_doy' in file['file_name']:
          datesy = file['file_name'].split('_doy')[1][:7]
          doy = day_of_year_to_date2(datesy)

          print(file['file_name'])
      else:
          continue
      file_download = requests.get(
          'https://appeears.earthdatacloud.nasa.gov/api/bundle/{0}/{1}'.format(task_id['task_id'], file_id),
          headers={'Authorization': 'Bearer {0}'.format(token)},
          allow_redirects=True,
          stream=True)
      file_download.raise_for_status()
      if not file_download.content:
          print(f"Warning: Empty file downloaded for {file['file_name']}")
          continue
      file_content = BytesIO(file_download.content)
      with rasterio.open(file_content) as src_initial:
          src = src_initial.read(1, masked=True)
          src_meta = src_initial.meta
          dst_crs = cdl_data.crs
          transform, width, height = calculate_default_transform(
              src_meta['crs'], dst_crs, src.shape[1], src.shape[0], *src_initial.bounds)
          kwargs = src_meta.copy()
          kwargs.update({
              'crs': dst_crs,
              'transform': transform,
              'width': width,
              'height': height
          })

          dst = np.zeros((height, width), dtype=src_meta['dtype'])
          reproject(
              source=src,
              destination=dst,
              src_transform=src_meta['transform'],
              src_crs=src_meta['crs'],
              dst_transform=transform,
              dst_crs=dst_crs,
              resampling=Resampling.nearest)


          kwargs.update({'nodata': 0})
          key = 'MODIS_NDVI'
          if key not in data:
              data[key] = {'data': [], 'meta': kwargs, 'doy': []}
          data[key]['data'].append(dst)
          data[key]['doy'].append(doy)
    else:
      continue

ndvi = np.stack(data['MODIS_NDVI']['data']) / 100
day = np.stack(data['MODIS_NDVI']['doy'])
meta = data['MODIS_NDVI']['meta']

"""# Combine and compare the results

"""

ndvi_resampled, ndvi_resampled_meta = resample_using_cdl(ndvi, meta, cdl_meta_reprojected)
slr_resampled, slr_resampled_meta = resample_using_cdl(slr_reprojected, slr_meta_reprojected, cdl_meta_reprojected)


print("CDL shape:", cdl_reprojected.shape)

print("Original NDVI shape:", ndvi.shape)
print("Resampled NDVI shape:", ndvi_resampled.shape)

print("Original SLR shape:", slr_reprojected.shape)
print("Resampled SLR shape:", slr_resampled.shape)

def mask_rasters(cdl_raster, slr_raster, ndvi_rasters):
    corn_mask = cdl_raster == 1
    ABOVE_water_mask = slr_raster <= 1
    corn_above_water_mask = corn_mask & ~ABOVE_water_mask
    corn_below_water_mask = corn_mask & ABOVE_water_mask

    corn_above_water_mask = corn_above_water_mask[0,:,:]
    corn_below_water_mask = corn_below_water_mask[0,:,:]
    masked_ndvi_below_water = ndvi_rasters[:, corn_below_water_mask]
    masked_ndvi_above_water = ndvi_rasters[:, corn_above_water_mask]


    return {
        'corn_below_water': {
            'mask': corn_below_water_mask,
            'ndvi': masked_ndvi_below_water,
            'mean': np.mean(masked_ndvi_below_water, axis=1) if masked_ndvi_below_water.size > 0 else None,
            'min': np.min(masked_ndvi_below_water, axis=1) if masked_ndvi_below_water.size > 0 else None,
            'max': np.max(masked_ndvi_below_water, axis=1) if masked_ndvi_below_water.size > 0 else None
        },
        'corn_above_water': {
            'mask': corn_above_water_mask,
            'ndvi': masked_ndvi_above_water,
            'mean': np.mean(masked_ndvi_above_water, axis=1) if masked_ndvi_above_water.size > 0 else None,
            'min': np.min(masked_ndvi_above_water, axis=1) if masked_ndvi_above_water.size > 0 else None,
            'max': np.max(masked_ndvi_above_water, axis=1) if masked_ndvi_above_water.size > 0 else None
        }
    }

def visualize_ndvi_analysis(ndvi_analysis, days):
    plt.figure(figsize=(12, 6))

    plt.subplot(1, 2, 1)
    plt.plot(days, ndvi_analysis['corn_above_water']['mean'], label='Corn Above Water', color='green')
    plt.plot(days, ndvi_analysis['corn_below_water']['mean'], label='Corn Below Water', color='blue')
    plt.title('Mean NDVI')
    plt.xlabel('Days')
    plt.xticks(rotation=90)
    plt.ylabel('NDVI')
    plt.legend()


    plt.subplot(1, 2, 2)
    plt.plot(days, ndvi_analysis['corn_above_water']['max'], label='Corn Above Water', color='green')
    plt.plot(days, ndvi_analysis['corn_below_water']['max'], label='Corn Below Water', color='blue')
    plt.title('Maximum NDVI')
    plt.xlabel('Days')
    plt.xticks(rotation=90)
    plt.ylabel('NDVI')
    plt.legend()

    plt.tight_layout()
    plt.show()

ndvi_analysis = mask_rasters(cdl_reprojected, slr_resampled, ndvi_resampled)

visualize_ndvi_analysis(ndvi_analysis, day)

for condition in ['corn_below_water', 'corn_above_water']:
    print(f"\n{condition.replace('_', ' ').title()} Corn Analysis per MODIS:")
    for stat in ['mean', 'max']:
        print(f"{stat.capitalize()} NDVI: {ndvi_analysis[condition][stat]}")

def visualize_ndvi_histogram(ndvi_analysis):
    plt.figure(figsize=(12, 6))

    plt.hist(ndvi_analysis['corn_below_water']['ndvi'].flatten(), bins=30, alpha=0.5, label='Corn Below Water', color='blue')
    plt.hist(ndvi_analysis['corn_above_water']['ndvi'].flatten(), bins=30, alpha=0.5, label='Corn Above Water', color='green')
    plt.xlabel("NDVI values")
    plt.ylabel("Frequency")
    plt.title("Histogram of NDVI values for corn")
    plt.legend(loc='upper right')


visualize_ndvi_histogram(ndvi_analysis)

"""What are the insights that we can derive from this module?

What are the impacts of land being close to the water currently?

What is the potential loss of productive land?

Where could there be errors given the sampling methods?

"""
