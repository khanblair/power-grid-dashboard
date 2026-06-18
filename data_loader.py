"""
Loads the pre-generated CSVs once at import time and exposes them as
module-level DataFrames for all Dash pages to share.
"""

from pathlib import Path
import pandas as pd

DATA_DIR = Path(__file__).parent / "data"

national_df = pd.read_csv(DATA_DIR / "national_summary.csv", parse_dates=["timestamp"])
generation_df = pd.read_csv(DATA_DIR / "generation_hourly.csv", parse_dates=["timestamp"])
regional_df = pd.read_csv(DATA_DIR / "regional_load.csv", parse_dates=["timestamp"])
outage_df = pd.read_csv(DATA_DIR / "outage_events.csv", parse_dates=["start_time", "end_time"])
water_df = pd.read_csv(DATA_DIR / "water_levels.csv", parse_dates=["date"])

PLANTS = sorted(generation_df["plant"].unique().tolist())
REGIONS = sorted(regional_df["region"].unique().tolist())
HYDRO_PLANTS = sorted(generation_df.loc[generation_df["source"] == "Hydro", "plant"].unique().tolist())

PLANT_COORDS = regional_df[["region", "lat", "lon"]].drop_duplicates().set_index("region")

DATE_MIN = national_df["timestamp"].min()
DATE_MAX = national_df["timestamp"].max()

SOURCE_COLORS = {"Hydro": "#1f9e89", "Solar": "#f4a623", "Thermal": "#c0392b"}
