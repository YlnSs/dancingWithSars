import h5py
import numpy as np
from pyproj import Transformer
import matplotlib.pyplot as plt



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

base_path = "science/LSAR/GCOV/grids/frequencyA"

roi_data = {}
valid_masks = {}
looks_data = {}

# Extract the same pixel window from every acquisition
for date, file_path in files.items():

    with h5py.File(file_path, "r") as f:

        grid = f[f"{base_path}"]

        x_current = grid["xCoordinates"][:]
        y_current = grid["yCoordinates"][:]

        if date == "August 27":
            x = x_current
            y = y_current
        else:
            print(
                "X coordinates match:",
                np.array_equal(x, x_current)
            )
            print(
                "Y coordinates match:",
                np.array_equal(y, y_current)
            )

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

        number_of_looks = f[f"{base_path}/numberOfLooks"][
            row_start:row_stop,
            col_start:col_stop
        ]

        looks_data[date] = number_of_looks

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


for date, looks in looks_data.items():
    print(f"\n{date}")
    print("Mean number of looks:", np.mean(looks))
    print("Minimum number of looks:", np.min(looks))
    print("Maximum number of looks:", np.max(looks))


common_valid = np.logical_and.reduce(
    list(valid_masks.values())
)


hh_db = {}

for date in files:
    hh_db[date] = 10 * np.log10(roi_data[date]["HH"])


comparisons = [
    ("August 27", "September 8"),
    ("September 8", "September 20"),
    ("August 27", "September 20")
]



change_maps = {}

for before, after in comparisons:

    change = hh_db[after] - hh_db[before]

    valid_changes = change[common_valid]

    change_maps[f"{before} -> {after}"] = change

    print(f"\n{before} -> {after}")
    print("Mean change (dB):", np.mean(valid_changes))

x_roi = x[col_start:col_stop]
y_roi = y[row_start:row_stop]


fire_locations = {
    "Karaöz": (30.825, 37.054),
    "Yeşilkaraman": (30.812, 37.098),
    "Kızıllı": (30.795, 37.135),
    "Çamlıca": (30.822, 37.142)
}

fire_projected = {}

for name, (lon, lat) in fire_locations.items():

    fire_x, fire_y = transformer.transform(lon, lat)

    fire_projected[name] = (fire_x, fire_y)



all_changes = np.concatenate([
    np.abs(change[common_valid])
    for change in change_maps.values()
])

limit = np.percentile(all_changes, 98)


fig, axes = plt.subplots(
    1, 3,
    figsize=(18, 6),
    constrained_layout=True
)


for ax, (comparison, change) in zip(
    axes,
    change_maps.items()
):

    # Hide invalid pixels
    displayed_change = np.ma.masked_where(
        ~common_valid,
        change
    )

    # Draw the raster
    image = ax.imshow(
        displayed_change,
        cmap="RdBu_r",
        vmin=-limit,
        vmax=limit,
        extent=[
            x_roi[0] - 10,
            x_roi[-1] + 10,
            y_roi[-1] - 10,
            y_roi[0] + 10
        ],
        origin="upper"
    )

    for name, (fire_x, fire_y) in fire_projected.items():
        ax.scatter(
            fire_x,
            fire_y,
            color="yellow",
            edgecolors="black",
            marker="o",
            s=65,
            zorder=5
        )

        ax.annotate(
            name,
            (fire_x, fire_y),
            xytext=(5, 5),
            textcoords="offset points",
            fontsize=8,
            color="black"
        )

    ax.set_title(comparison)
    ax.set_xlabel("Easting (m)")
    ax.set_ylabel("Northing (m)")


fig.colorbar(
    image,
    ax=axes,
    label="HH backscatter change (dB)",
    shrink=0.8
)

fig.suptitle("NISAR HH Backscatter Change — Aksu, Antalya")

plt.show()
