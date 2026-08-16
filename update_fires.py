import os
import re
from io import StringIO

import pandas as pd
import requests
import geopandas as gpd


TOKEN = os.getenv("EARTHDATA_TOKEN")

BOUNDARY_FILE = "fars.geojson"
OUTPUT_FILE = "data/fires.csv"

BASE_URL = "https://nrt3.modaps.eosdis.nasa.gov/archive/FIRMS"


SOURCES = {
    "MODIS": "modis-c6.1/South_Asia",
    "VIIRS_SNPP": "suomi-npp-viirs-c2/South_Asia",
    "VIIRS_NOAA20": "noaa-20-viirs-c2/South_Asia",
    "VIIRS_NOAA21": "noaa-21-viirs-c2/South_Asia",
}


def get_headers():
    if not TOKEN:
        raise RuntimeError("EARTHDATA_TOKEN تنظیم نشده است.")

    return {
        "Authorization": f"Bearer {TOKEN}"
    }


def get_latest_file(folder_url):
    response = requests.get(
        folder_url,
        headers=get_headers(),
        timeout=60
    )

    response.raise_for_status()

    files = re.findall(
        r'href="([^"]+\.txt)"',
        response.text
    )

    if not files:
        raise RuntimeError(
            f"هیچ فایل داده‌ای پیدا نشد: {folder_url}"
        )

    return files[-1]


def download_file(url):
    response = requests.get(
        url,
        headers=get_headers(),
        timeout=120
    )

    response.raise_for_status()

    text = response.text

    if not text.strip():
        return pd.DataFrame()

    return pd.read_csv(
        StringIO(text)
    )


def filter_fars(df):
    if df.empty:
        return df

    fars = gpd.read_file(
        BOUNDARY_FILE
    ).to_crs("EPSG:4326")

    points = gpd.GeoDataFrame(
        df,
        geometry=gpd.points_from_xy(
            df["longitude"],
            df["latitude"]
        ),
        crs="EPSG:4326"
    )

    result = gpd.sjoin(
        points,
        fars[["geometry"]],
        how="inner",
        predicate="within"
    )

    return result.drop(
        columns=["geometry", "index_right"],
        errors="ignore"
    )


def main():
    all_fires = []

    for sensor, folder in SOURCES.items():

        folder_url = f"{BASE_URL}/{folder}/"

        print(f"Checking {sensor}...")

        try:
            filename = get_latest_file(folder_url)

            file_url = f"{folder_url}{filename}"

            print(f"Downloading: {filename}")

            df = download_file(file_url)

            if df.empty:
                print(f"{sensor}: no data")
                continue

            df = filter_fars(df)

            if df.empty:
                print(f"{sensor}: no fires in Fars")
                continue

            df["sensor"] = sensor

            all_fires.append(df)

            print(
                f"{sensor}: {len(df)} fires in Fars"
            )

        except Exception as error:
            print(
                f"{sensor}: ERROR - {error}"
            )

    os.makedirs(
        "data",
        exist_ok=True
    )

    if all_fires:

        result = pd.concat(
            all_fires,
            ignore_index=True
        )

        result = result.drop_duplicates(
            subset=[
                "latitude",
                "longitude",
                "acq_date",
                "acq_time",
                "sensor"
            ]
        )

    else:

        result = pd.DataFrame()

    result.to_csv(
        OUTPUT_FILE,
        index=False
    )

    print()
    print(
        f"Saved {len(result)} records to {OUTPUT_FILE}"
    )


if __name__ == "__main__":
    main()
