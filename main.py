import h5py
import numpy as np
from pyproj import Transformer



files = {
    "August 27": "./datasets/NISAR_L2_PR_GCOV_029_028_A_020_2005_DHDH_A_20260827T030948_20260827T031013_P05023_N_P_J_001.h5",
    "September 8": "./datasets/NISAR_L2_PR_GCOV_030_028_A_020_2005_DHDH_A_20260908T030947_20260908T031013_P05023_N_F_J_001.h5",
    "September 20": "./datasets/NISAR_L2_PR_GCOV_031_028_A_020_2005_DHDH_A_20260920T030947_20260920T031013_P05023_F_F_J_001.h5"
}


# AOI in geographic coordinates (longitude, latitude)
west, east = 30.785, 30.835
south, north = 37.044, 37.152

# Convert WGS84 coordinates into the NISAR raster CRS
transformer = Transformer.from_crs(
    "EPSG:4326",
    "EPSG:32636",
    always_xy=True
)

# Transform the four corners
corners = [
    (west, south),
    (west, north),
    (east, south),
    (east, north)
]

projected = [
    transformer.transform(lon, lat)
    for lon, lat in corners
]

min_x = min(point[0] for point in projected)
max_x = max(point[0] for point in projected)
min_y = min(point[1] for point in projected)
max_y = max(point[1] for point in projected)

with h5py.File(files["August 27"], "r") as f:
    grid = f["science/LSAR/GCOV/grids/frequencyA"]

    x = grid["xCoordinates"][:]
    y = grid["yCoordinates"][:]

    cols = np.flatnonzero((x >= min_x) & (x <= max_x))
    rows = np.flatnonzero((y >= min_y) & (y <= max_y))

    col_start, col_stop = cols[0], cols[-1] + 1
    row_start, row_stop = rows.min(), rows.max() + 1

    print("Columns:", col_start, "to", col_stop)
    print("Rows:", row_start, "to", row_stop)
    print("ROI shape:", row_stop - row_start, "x", col_stop - col_start)

base_path = "science/LSAR/GCOV/grids/frequencyA"

roi_data = {}
valid_masks = {}

# Extract the same pixel window from every acquisition
for date, file_path in files.items():

    with h5py.File(file_path, "r") as f:

        hh = f[f"{base_path}/HHHH"][
            row_start:row_stop,
            col_start:col_stop
        ]

        hv = f[f"{base_path}/HVHV"][
            row_start:row_stop,
            col_start:col_stop
        ]

        mask = f[f"{base_path}/mask"][
            row_start:row_stop,
            col_start:col_stop
        ]

        # A pixel is usable if the mask marks it as valid
        # and both polarization values are finite and positive.
        valid = (
            (mask == 1)
            & np.isfinite(hh)
            & np.isfinite(hv)
            & (hh > 0)
            & (hv > 0)
        )

        roi_data[date] = {
            "HH": hh,
            "HV": hv
        }

        valid_masks[date] = valid

        print(f"\n{date}")
        print("HH shape:", hh.shape)
        print("HV shape:", hv.shape)
        print("Valid pixels:", np.count_nonzero(valid))
        print("Valid percentage:", round(valid.mean() * 100, 2), "%")


# Find pixels valid on all three dates
common_valid = np.logical_and.reduce(
    list(valid_masks.values())
)

print("\nCommon valid pixels across all dates:")
print(np.count_nonzero(common_valid))

print(
    "Common valid percentage:",
    round(common_valid.mean() * 100, 2),
    "%"
)

# Convert HH backscatter from linear power to dB
hh_db = {}

for date in files:
    hh_db[date] = 10 * np.log10(roi_data[date]["HH"])


# Define which dates we want to compare
comparisons = [
    ("August 27", "September 8"),
    ("September 8", "September 20"),
    ("August 27", "September 20")
]


# Store the resulting change maps
change_maps = {}

for before, after in comparisons:

    # Calculate the pixel-by-pixel difference
    change = hh_db[after] - hh_db[before]

    # Keep only pixels valid in all three acquisitions
    valid_changes = change[common_valid]

    # Save the change array
    change_maps[f"{before} -> {after}"] = change

    # Calculate summary statistics
    print(f"\n{before} -> {after}")

    print("Mean change (dB):", np.mean(valid_changes))
    print("Median change (dB):", np.median(valid_changes))
    print("Minimum change (dB):", np.min(valid_changes))
    print("Maximum change (dB):", np.max(valid_changes))

    print(
        "Pixels with decreased backscatter:",
        np.mean(valid_changes < 0) * 100,
        "%"
    )

    print(
        "Pixels with increased backscatter:",
        np.mean(valid_changes > 0) * 100,
        "%"
    )