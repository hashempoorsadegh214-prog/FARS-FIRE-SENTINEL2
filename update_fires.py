import os
import re
from io import StringIO
from datetime import datetime, timedelta

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

DAYS_TO_KEEP = 5


def get_headers():
    if not TOKEN:
        raise RuntimeError(
            "EARTHDATA_TOKEN در GitHub Secrets پیدا نشد."
        )

    return {
        "Authorization": f"Bearer {TOKEN}",
        "User-Agent": "FARS-FIRE-SENTINEL2"
    }


def get_recent_dates():
    today = datetime.utcnow().date()

    return {
        (today - timedelta(days=i)).strftime("%Y%j")
        for i in range(DAYS_TO_KEEP)
    }


def get_files(folder_url, recent_dates):
    response = requests.get(
        folder_url,
        headers=get_headers(),
        timeout=60
    )

    print(
        f"Directory status: {response.status_code} | "
        f"{folder_url}"
    )

    response.raise_for_status()

    links = re.findall(
        r'href=["\']([^"\']+\.txt)["\']',
        response.text,
        flags=re.IGNORECASE
    )

    filenames = []

    for link in links:

        filename = link.split("/")[-1]

        if not filename.lower().endswith(".txt"):
            continue

        match = re.search(
            r'_(\d{7})\.txt$',
            filename
        )

        if not match:
            continue

        file_date = match.group(1)

        if file_date in recent_dates:
            filenames.append(filename)

    filenames = sorted(
        set(filenames)
    )

    if not filenames:
        raise RuntimeError(
            "هیچ فایل مربوط به ۵ روز اخیر پیدا نشد."
        )

    print(
        f"Recent files found: {len(filenames)}"
    )

    for filename in filenames:
        print(
            f"  {filename}"
        )

    return filenames


def download_file(folder_url, filename):
    file_url = f"{folder_url}{filename}"

    response = requests.get(
        file_url,
        headers=get_headers(),
        timeout=120
    )

    print(
        f"File status: {response.status_code} | "
        f"{filename}"
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
            f"فایل {BOUNDARY_FILE} پیدا نشد."
        )

    fars = gpd.read_file(
        BOUNDARY_FILE
    )

    if fars.empty:
        raise RuntimeError(
            "فایل fars.geojson خالی است."
        )

    return fars.to_crs(
        "EPSG:4326"
    )


def filter_fars(df, fars):
    if df.empty:
        return df

    required = {
        "latitude",
        "longitude"
    }

    missing = required - set(df.columns)

    if missing:
        raise RuntimeError(
            f"ستون‌های لازم FIRMS وجود ندارند: {missing}"
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

    df = df.dropna(
        subset=[
            "latitude",
            "longitude"
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
    print("========================================")
    print("FARS FIRE DATA UPDATE")
    print("========================================")

    fars = load_fars()
    recent_dates = get_recent_dates()

    print(
        "Dates included:"
    )

    for date_value in sorted(recent_dates):
        print(
            f"  {date_value}"
        )

    all_fires = []

    for sensor, folder in SOURCES.items():

        print()
        print("========================================")
        print(
            f"SOURCE: {sensor}"
        )
        print("========================================")

        folder_url = (
            f"{BASE_URL}/{folder}/"
        )

        try:

            filenames = get_files(
                folder_url,
                recent_dates
            )

            for filename in filenames:

                print()
                print(
                    f"Downloading: {filename}"
                )

                df = download_file(
                    folder_url,
                    filename
                )

                if df.empty:
                    print(
                        "File is empty."
                    )
                    continue

                print(
                    f"Records in file: {len(df)}"
                )

                df = filter_fars(
                    df,
                    fars
                )

                print(
                    f"Records inside Fars: {len(df)}"
                )

                if df.empty:
                    continue

                df["sensor"] = sensor

                all_fires.append(
                    df
                )

        except Exception as error:

            print()
            print(
                f"ERROR in {sensor}:"
            )
            print(
                str(error)
            )

    if not all_fires:
        raise RuntimeError(
            "هیچ داده حریقی برای فارس در ۵ روز اخیر پیدا نشد."
        )

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

    result["acq_date"] = pd.to_datetime(
        result["acq_date"],
        errors="coerce"
    )

    minimum_date = (
        datetime.utcnow().date()
        - timedelta(days=DAYS_TO_KEEP - 1)
    )

    result = result[
        result["acq_date"].dt.date >= minimum_date
    ].copy()

    result["acq_date"] = result[
        "acq_date"
    ].dt.strftime("%Y-%m-%d")

    os.makedirs(
        "data",
        exist_ok=True
    )

    result.to_csv(
        OUTPUT_FILE,
        index=False
    )

    print()
    print("========================================")
    print(
        f"FINAL FARS FIRE RECORDS: {len(result)}"
    )
    print(
        f"OUTPUT: {OUTPUT_FILE}"
    )
    print("========================================")


if __name__ == "__main__":
    main()
