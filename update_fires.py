import os
import re
from io import StringIO

import geopandas as gpd
import pandas as pd
import requests


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
        raise RuntimeError(
            "EARTHDATA_TOKEN در GitHub Secrets پیدا نشد."
        )

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

    links = re.findall(
        r'href=["\']([^"\']+\.txt)["\']',
        response.text,
        flags=re.IGNORECASE
    )

    files = []

    for link in links:
        filename = link.split("/")[-1]

        if filename.lower().endswith(".txt"):
            files.append(filename)

    files = sorted(set(files))

    if not files:
        raise RuntimeError(
            f"هیچ فایل FIRMS در مسیر پیدا نشد:\n{folder_url}"
        )

    return files


def download_file(folder_url, filename):
    url = f"{folder_url}{filename}"

    response = requests.get(
        url,
        headers=get_headers(),
        timeout=120
    )

    response.raise_for_status()

    text = response.text.strip()

    if not text:
        return pd.DataFrame()

    return pd.read_csv(
        StringIO(text)
    )


def load_fars():
    if not os.path.exists(BOUNDARY_FILE):
        raise RuntimeError(
            f"{BOUNDARY_FILE} پیدا نشد."
        )

    fars = gpd.read_file(
        BOUNDARY_FILE
    )

    if fars.empty:
        raise RuntimeError(
            "fars.geojson خالی است."
        )

    return fars.to_crs("EPSG:4326")


def filter_fars(df, fars):
    if df.empty:
        return df

    if not {
        "latitude",
        "longitude",
        "acq_date",
        "acq_time"
    }.issubset(df.columns):
        raise RuntimeError(
            "ستون‌های لازم FIRMS در فایل وجود ندارند."
        )

    df = df.copy()

    df["latitude"] = pd.to_numeric(
        df["latitude"],
        errors="coerce"
    )

    df["longitude"] = pd.to_numeric(
        df["longitude"],
        errors="coerce"
    )

    df["acq_datetime"] = pd.to_datetime(
        df["acq_date"].astype(str)
        + " "
        + df["acq_time"].astype(str).str.zfill(4),
        format="%Y-%m-%d %H%M",
        errors="coerce",
        utc=True
    )

    df = df.dropna(
        subset=[
            "latitude",
            "longitude",
            "acq_datetime"
        ]
    )

    if df.empty:
        return df

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
        columns=[
            "geometry",
            "index_right"
        ],
        errors="ignore"
    )


def main():
    print("================================")
    print("FARS FIRE DATA UPDATE")
    print("================================")

    fars = load_fars()

    all_fires = []

    for sensor, folder in SOURCES.items():

        print()
        print(f"===== {sensor} =====")

        folder_url = f"{BASE_URL}/{folder}/"

        files = get_files(
            folder_url
        )

        for filename in files:

            print(
                f"Downloading {filename}"
            )

            try:

                df = download_file(
                    folder_url,
                    filename
                )

                if df.empty:
                    continue

                df = filter_fars(
                    df,
                    fars
                )

                if df.empty:
                    continue

                df["sensor"] = sensor

                all_fires.append(
                    df
                )

            except Exception as error:

                print(
                    f"ERROR: {error}"
                )

    if not all_fires:
        raise RuntimeError(
            "هیچ داده حریقی برای فارس پیدا نشد."
        )

    result = pd.concat(
        all_fires,
        ignore_index=True
    )

    # آخرین 7 روز بر اساس زمان واقعی رخداد
    now = pd.Timestamp.now(
        tz="UTC"
    )

    seven_days_ago = (
        now - pd.Timedelta(days=7)
    )

    result = result[
        result["acq_datetime"] >= seven_days_ago
    ].copy()

    # حذف تکراری‌ها
    result = result.drop_duplicates(
        subset=[
            "latitude",
            "longitude",
            "acq_date",
            "acq_time",
            "sensor"
        ]
    )

    # حذف ستون کمکی
    result = result.drop(
        columns=["acq_datetime"],
        errors="ignore"
    )

    # مرتب‌سازی
    result = result.sort_values(
        by=[
            "acq_date",
            "acq_time"
        ],
        ascending=False
    )

    os.makedirs(
        "data",
        exist_ok=True
    )

    result.to_csv(
        OUTPUT_FILE,
        index=False
    )

    print()
    print("================================")
    print(
        f"FARS FIRE RECORDS: {len(result)}"
    )
    print(
        f"OUTPUT: {OUTPUT_FILE}"
    )
    print("================================")


if __name__ == "__main__":
    main()
