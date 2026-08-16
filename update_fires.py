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

DAYS_TO_DOWNLOAD = 3


def get_headers():
    if not TOKEN:
        raise RuntimeError("EARTHDATA_TOKEN تنظیم نشده است.")

    return {
        "Authorization": f"Bearer {TOKEN}",
        "User-Agent": "FARS-FIRE-SENTINEL2/1.0"
    }


def get_files(folder_url):
    response = requests.get(
        folder_url,
        headers=get_headers(),
        timeout=60
    )

    response.raise_for_status()

    files = re.findall(
        r'href=["\']([^"\']+\.(?:txt|csv))["\']',
        response.text,
        flags=re.IGNORECASE
    )

    if not files:
        raise RuntimeError(
            f"هیچ فایل داده‌ای پیدا نشد: {folder_url}"
        )

    files = sorted(
        set(files)
    )

    return files[-DAYS_TO_DOWNLOAD:]


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

    required_columns = {
        "latitude",
        "longitude"
    }

    missing = required_columns - set(df.columns)

    if missing:
        raise RuntimeError(
            f"ستون‌های لازم موجود نیستند: {missing}"
        )

    fars = gpd.read_file(
        BOUNDARY_FILE
    ).to_crs("EPSG:4326")

    points = gpd.GeoDataFrame(
        df.copy(),
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
        columns=[
            "geometry",
            "index_right"
        ],
        errors="ignore"
    )


def main():
    all_fires = []

    for sensor, folder in SOURCES.items():

        print(f"\n===== {sensor} =====")

        folder_url = f"{BASE_URL}/{folder}/"

        try:
            files = get_files(folder_url)

            print(
                f"Files found: {len(files)}"
            )

            for filename in files:

                file_url = f"{folder_url}{filename}"

                print(
                    f"Downloading: {filename}"
                )

                try:
                    df = download_file(
                        file_url
                    )

                    if df.empty:
                        print(
                            "File is empty."
                        )
                        continue

                    print(
                        f"Total records: {len(df)}"
                    )

                    df = filter_fars(df)

                    if df.empty:
                        print(
                            "No fire detected inside Fars."
                        )
                        continue

                    df["sensor"] = sensor

                    all_fires.append(df)

                    print(
                        f"Fars records: {len(df)}"
                    )

                except Exception as error:

                    print(
                        f"File error: {error}"
                    )

        except Exception as error:

            print(
                f"Source error: {error}"
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
            ],
            keep="first"
        )

    else:

        result = pd.DataFrame(
            columns=[
                "latitude",
                "longitude",
                "acq_date",
                "acq_time",
                "sensor"
            ]
        )

    result.to_csv(
        OUTPUT_FILE,
        index=False
    )

    print()
    print(
        "================================"
    )
    print(
        f"Total Fars fires: {len(result)}"
    )
    print(
        f"Output: {OUTPUT_FILE}"
    )
    print(
        "================================"
    )


if __name__ == "__main__":
    main()
