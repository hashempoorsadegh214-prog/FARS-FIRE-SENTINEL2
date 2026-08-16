import os
from io import BytesIO

import pandas as pd
import requests
import geopandas as gpd


# --------------------------------------------------
# تنظیمات
# --------------------------------------------------

TOKEN = os.getenv("EARTHDATA_TOKEN")

BOUNDARY_FILE = "fars.geojson"
OUTPUT_FILE = "data/fires.csv"

BASE_URL = "https://nrt3.modaps.eosdis.nasa.gov/archive/FIRMS"


# --------------------------------------------------
# بررسی Token
# --------------------------------------------------

if not TOKEN:
    raise RuntimeError("EARTHDATA_TOKEN تنظیم نشده است.")


# --------------------------------------------------
# منابع FIRMS
# --------------------------------------------------

SOURCES = {
    "MODIS": "modis-c6.1",
    "VIIRS_SNPP": "viirs-snpp",
    "VIIRS_NOAA20": "viirs-noaa20",
    "VIIRS_NOAA21": "viirs-noaa21",
}


# --------------------------------------------------
# دریافت فهرست فایل‌های یک منبع
# --------------------------------------------------

def get_directory(url):
    response = requests.get(
        url,
        headers={
            "Authorization": f"Bearer {TOKEN}"
        },
        timeout=60
    )

    response.raise_for_status()

    return response.text


# --------------------------------------------------
# دریافت داده
# --------------------------------------------------

def download_file(url):

    response = requests.get(
        url,
        headers={
            "Authorization": f"Bearer {TOKEN}"
        },
        timeout=120
    )

    response.raise_for_status()

    return pd.read_csv(
        BytesIO(response.content)
    )


# --------------------------------------------------
# فیلتر فارس با GeoJSON
# --------------------------------------------------

def filter_fars(df):

    gdf = gpd.GeoDataFrame(
        df,
        geometry=gpd.points_from_xy(
            df.longitude,
            df.latitude
        ),
        crs="EPSG:4326"
    )

    fars = gpd.read_file(
        BOUNDARY_FILE
    )

    fars = fars.to_crs(
        "EPSG:4326"
    )

    result = gpd.sjoin(
        gdf,
        fars,
        predicate="within",
        how="inner"
    )

    return result.drop(
        columns=["geometry", "index_right"],
        errors="ignore"
    )


# --------------------------------------------------
# دریافت داده‌ها
# --------------------------------------------------

all_data = []


for sensor, folder in SOURCES.items():

    print(f"Checking {sensor}...")

    url = f"{BASE_URL}/{folder}/"

    try:

        html = get_directory(url)

        print(
            f"{sensor}: directory accessible"
        )

        # این بخش بعد از تست مسیر واقعی فایل‌ها تکمیل می‌شود.

    except Exception as error:

        print(
            f"{sensor}: {error}"
        )


# --------------------------------------------------
# ایجاد خروجی اولیه
# --------------------------------------------------

os.makedirs(
    "data",
    exist_ok=True
)

if all_data:

    result = pd.concat(
        all_data,
        ignore_index=True
    )

else:

    result = pd.DataFrame(
        columns=[
            "latitude",
            "longitude",
            "acq_date",
            "acq_time",
            "satellite",
            "instrument",
            "confidence",
            "frp"
        ]
    )


result.to_csv(
    OUTPUT_FILE,
    index=False
)

print(
    f"Saved {len(result)} records to {OUTPUT_FILE}"
)
