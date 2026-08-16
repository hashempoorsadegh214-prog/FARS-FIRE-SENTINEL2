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

FILES_PER_SOURCE = 5


def get_headers():
    if not TOKEN:
        raise RuntimeError(
            "EARTHDATA_TOKEN در GitHub Secrets پیدا نشد."
        )

    return {
        "Authorization": f"Bearer {TOKEN}",
        "User-Agent": "FARS-FIRE-SENTINEL2"
    }


def get_files(folder_url):
    response = requests.get(
        folder_url,
        headers=get_headers(),
        timeout=60,
        allow_redirects=True
    )

    print(
        f"Directory status: {response.status_code} | "
        f"URL: {folder_url}"
    )

    if response.status_code != 200:
        raise RuntimeError(
            f"خطا در دسترسی به پوشه FIRMS: "
            f"{response.status_code}"
        )

    files = re.findall(
        r'href=["\']([^"\']+\.txt)["\']',
        response.text,
        flags=re.IGNORECASE
    )

    files = sorted(set(files))

    if not files:
        raise RuntimeError(
            f"هیچ فایل TXT در این مسیر پیدا نشد:\n{folder_url}"
        )

    selected = files[-FILES_PER_SOURCE:]

    print(
        f"Found {len(files)} files. "
        f"Using last {len(selected)} files."
    )

    for filename in selected:
        print(f"  {filename}")

    return selected


def download_file(file_url):
    response = requests.get(
        file_url,
        headers=get_headers(),
        timeout=120,
        allow_redirects=True
    )

    print(
        f"File status: {response.status_code} | "
        f"{file_url}"
    )

    if response.status_code != 200:
        raise RuntimeError(
            f"دانلود فایل موفق نبود: "
            f"{response.status_code}"
        )

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
            f"ستون‌های لازم در داده FIRMS وجود ندارند: {missing}"
        )

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
    print("========================================")
    print("FARS FIRE DATA UPDATE")
    print("========================================")

    fars = load_fars()

    all_fires = []
    successful_sources = 0

    for sensor, folder in SOURCES.items():

        print()
        print("========================================")
        print(f"SOURCE: {sensor}")
        print("========================================")

        folder_url = (
            f"{BASE_URL}/{folder}/"
        )

        try:

            files = get_files(
                folder_url
            )

            source_has_data = False

            for filename in files:

                file_url = (
                    f"{folder_url}{filename}"
                )

                print()
                print(
                    f"Downloading {filename}"
                )

                df = download_file(
                    file_url
                )

                if df.empty:
                    print(
                        "File contains no records."
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

                source_has_data = True

            if source_has_data:
                successful_sources += 1

        except Exception as error:

            print()
            print(
                f"ERROR in {sensor}:"
            )
            print(
                str(error)
            )

    print()
    print("========================================")
    print(
        f"Successful sources: "
        f"{successful_sources} / {len(SOURCES)}"
    )
    print("========================================")

    if successful_sources == 0:
        raise RuntimeError(
            "هیچ منبع FIRMS با موفقیت پردازش نشد."
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
    print("========================================")
    print(
        f"FINAL FARS FIRE RECORDS: "
        f"{len(result)}"
    )
    print(
        f"OUTPUT: {OUTPUT_FILE}"
    )
    print("========================================")


if __name__ == "__main__":
    main()
