import json
import h5py
import numpy as np
from pathlib import Path
from pyproj import Transformer
from shapely.geometry import shape
from shapely.ops import transform as transform_geometry, unary_union
from shapely import contains_xy


# ==================================================
# CONFIGURATION
# ==================================================

BASE_DIR = Path(__file__).resolve().parent

FILES = {
    "August 27": BASE_DIR / "datasets" / "NISAR_L2_PR_GCOV_029_028_A_020_2005_DHDH_A_20260827T030948_20260827T031013_P05023_N_P_J_001.h5",
    "September 8": BASE_DIR / "datasets" / "NISAR_L2_PR_GCOV_030_028_A_020_2005_DHDH_A_20260908T030947_20260908T031013_P05023_N_F_J_001.h5",
    "September 20": BASE_DIR / "datasets" / "NISAR_L2_PR_GCOV_031_028_A_020_2005_DHDH_A_20260920T030947_20260920T031013_P05023_F_F_J_001.h5",
}

# Optional external EFFIS/Copernicus perimeter.
# Put a WGS84 (longitude/latitude) GeoJSON here.
PERIMETER_FILE = BASE_DIR / "datasets" / "aksu_fire_perimeter.geojson"

# Study area in longitude/latitude (EPSG:4326).
WEST, EAST = 30.680, 30.840
SOUTH, NORTH = 37.020, 37.220

BASE_PATH = "science/LSAR/GCOV/grids/frequencyA"

COMPARISONS = [
    ("August 27", "September 8"),
    ("September 8", "September 20"),
    ("August 27", "September 20"),
]

# Approximate neighbourhood centres; these are not ignition points.
FIRE_LOCATIONS = {
    "Karaöz": (30.7838768, 37.190248),
    "Yeşilkaraman": (30.802944, 37.115043),
    "Kızıllı": (30.7131593, 37.1110489),
    "Çamlıca": (30.7403824, 37.0470378),
}

THRESHOLD_MULTIPLIER = 3.0


# ==================================================
# HELPER FUNCTIONS
# ==================================================

def convert_to_db(data, valid_mask):
    """Convert linear radar power to decibels: 10 * log10(power)."""
    db_array = np.full(data.shape, np.nan, dtype=np.float32)
    np.log10(data, out=db_array, where=valid_mask)
    db_array[valid_mask] *= 10
    return db_array


def detect_candidate_changes(change, common_mask):
    """Flag statistically unusual changes, not confirmed burned pixels."""
    valid_changes = change[common_mask]
    if valid_changes.size == 0:
        raise ValueError("No valid pixels available for change detection.")

    median_change = float(np.median(valid_changes))
    mad = float(np.median(np.abs(valid_changes - median_change)))
    robust_std = 1.4826 * mad

    lower = median_change - THRESHOLD_MULTIPLIER * robust_std
    upper = median_change + THRESHOLD_MULTIPLIER * robust_std
    candidate_mask = common_mask & ((change < lower) | (change > upper))
    percentage = float(np.sum(candidate_mask) / np.sum(common_mask) * 100)

    return {
        "mask": candidate_mask,
        "median": median_change,
        "mad": mad,
        "robust_std": robust_std,
        "lower_threshold": lower,
        "upper_threshold": upper,
        "percentage": percentage,
    }


def load_fire_perimeter(transformer):
    """Load a WGS84 GeoJSON perimeter and project it to the NISAR CRS."""
    if not PERIMETER_FILE.exists():
        return None, None

    with PERIMETER_FILE.open("r", encoding="utf-8") as file:
        document = json.load(file)

    if document.get("type") == "FeatureCollection":
        geometries = [
            shape(feature["geometry"])
            for feature in document.get("features", [])
            if feature.get("geometry")
        ]
        if not geometries:
            raise ValueError("The perimeter GeoJSON contains no geometries.")
        perimeter_wgs84 = unary_union(geometries)
    elif document.get("type") == "Feature":
        perimeter_wgs84 = shape(document["geometry"])
    else:
        perimeter_wgs84 = shape(document)

    if perimeter_wgs84.is_empty or not perimeter_wgs84.is_valid:
        raise ValueError("The fire-perimeter geometry is empty or invalid.")

    # GeoJSON coordinates are expected to be longitude/latitude (WGS84).
    perimeter_utm = transform_geometry(transformer.transform, perimeter_wgs84)
    return perimeter_wgs84, perimeter_utm


def polygon_boundary_coordinates(geometry):
    """Return Plotly line coordinates for Polygon or MultiPolygon outlines."""
    xs, ys = [], []
    if geometry is None:
        return xs, ys

    polygons = list(geometry.geoms) if geometry.geom_type == "MultiPolygon" else [geometry]
    for polygon in polygons:
        rings = [polygon.exterior, *polygon.interiors]
        for ring in rings:
            coords = list(ring.coords)
            xs.extend([point[0] for point in coords] + [None])
            ys.extend([point[1] for point in coords] + [None])
    return xs, ys


def calculate_region_statistics(change, common_mask, region_mask):
    """Compare a region with its complement using the same valid pixels."""
    inside = common_mask & region_mask
    outside = common_mask & ~region_mask

    def summarize(mask):
        values = change[mask]
        if values.size == 0:
            return {
                "pixels": 0,
                "median": None,
                "mean": None,
                "p25": None,
                "p75": None
            }
        return {
            "pixels": int(values.size),
            "median": float(np.median(values)),
            "mean": float(np.mean(values)),
            "p25": float(np.percentile(values, 25)),
            "p75": float(np.percentile(values, 75)),
        }

    return {
        "inside": summarize(inside),
        "outside": summarize(outside)
    }


# ==================================================
# MAIN ANALYSIS
# ==================================================

def load_analysis():
    transformer = Transformer.from_crs(
        "EPSG:4326",
        "EPSG:32636",
        always_xy=True
    )

    corners = [
        transformer.transform(WEST, SOUTH),
        transformer.transform(WEST, NORTH),
        transformer.transform(EAST, SOUTH),
        transformer.transform(EAST, NORTH),
    ]

    min_x = min(point[0] for point in corners)
    max_x = max(point[0] for point in corners)
    min_y = min(point[1] for point in corners)
    max_y = max(point[1] for point in corners)

    for date, file_path in FILES.items():
        if not file_path.exists():
            raise FileNotFoundError(
                f"Missing NISAR file for {date}: {file_path}"
            )

    with h5py.File(FILES["August 27"], "r") as file:
        grid = file[BASE_PATH]
        x = grid["xCoordinates"][:]
        y = grid["yCoordinates"][:]

        if not np.all(np.diff(x) > 0):
            raise ValueError("NISAR X coordinates are not increasing.")

        if not np.all(np.diff(y) < 0):
            raise ValueError("NISAR Y coordinates are not decreasing.")

        if (
            min_x < x.min()
            or max_x > x.max()
            or min_y < y.min()
            or max_y > y.max()
        ):
            raise ValueError(
                "The NISAR raster does not cover the complete requested AOI. "
                f"Requested E {min_x:.0f}–{max_x:.0f} m, "
                f"N {min_y:.0f}–{max_y:.0f} m; "
                f"raster E {x.min():.0f}–{x.max():.0f} m, "
                f"N {y.min():.0f}–{y.max():.0f} m. "
                "Reduce the AOI or use another acquisition; do not silently clip it."
            )

        cols = np.flatnonzero((x >= min_x) & (x <= max_x))
        rows = np.flatnonzero((y >= min_y) & (y <= max_y))

        if len(cols) == 0 or len(rows) == 0:
            raise ValueError(
                "The selected AOI does not intersect the NISAR raster."
            )

        col_start, col_stop = cols[0], cols[-1] + 1
        row_start, row_stop = rows.min(), rows.max() + 1

    roi_data = {}
    valid_masks = {}

    for date, file_path in FILES.items():
        with h5py.File(file_path, "r") as file:
            grid = file[BASE_PATH]

            if not np.array_equal(x, grid["xCoordinates"][:]):
                raise ValueError(f"X coordinates do not match for {date}.")

            if not np.array_equal(y, grid["yCoordinates"][:]):
                raise ValueError(f"Y coordinates do not match for {date}.")

            hh = grid["HHHH"][
                row_start:row_stop,
                col_start:col_stop
            ]

            hv = grid["HVHV"][
                row_start:row_stop,
                col_start:col_stop
            ]

            mask = grid["mask"][
                row_start:row_stop,
                col_start:col_stop
            ]

            roi_data[date] = {
                "HH": hh,
                "HV": hv
            }

            valid_masks[date] = {
                "HH": (mask == 1) & np.isfinite(hh) & (hh > 0),
                "HV": (mask == 1) & np.isfinite(hv) & (hv > 0),
            }

    common_valid_hh = np.logical_and.reduce([
        valid_masks[date]["HH"] for date in FILES
    ])

    common_valid_hv = np.logical_and.reduce([
        valid_masks[date]["HV"] for date in FILES
    ])

    if not np.any(common_valid_hh):
        raise ValueError("No HH pixels are valid across all three dates.")

    if not np.any(common_valid_hv):
        raise ValueError("No HV pixels are valid across all three dates.")

    hh_db = {}
    hv_db = {}

    for date in FILES:
        hh_db[date] = convert_to_db(
            roi_data[date]["HH"],
            valid_masks[date]["HH"]
        )

        hv_db[date] = convert_to_db(
            roi_data[date]["HV"],
            valid_masks[date]["HV"]
        )

    x_roi = x[col_start:col_stop]
    y_roi = y[row_start:row_stop]

    if len(x_roi) < 2 or len(y_roi) < 2:
        raise ValueError("The selected NISAR region is too small.")

    dx = float(np.median(np.diff(x_roi)))
    dy = float(np.median(np.diff(y_roi)))

    extent = [
        float(x_roi[0] - dx / 2),
        float(x_roi[-1] + dx / 2),
        float(y_roi[-1] + dy / 2),
        float(y_roi[0] - dy / 2),
    ]

    # Raster-cell centre coordinates, used for point-in-polygon testing.
    grid_x, grid_y = np.meshgrid(x_roi, y_roi)

    perimeter_wgs84, perimeter_utm = load_fire_perimeter(transformer)

    if perimeter_utm is not None:
        perimeter_mask = contains_xy(perimeter_utm, grid_x, grid_y)
        perimeter_status = "loaded"
    else:
        perimeter_mask = None
        perimeter_status = "missing"

    fire_projected = {}

    for name, (lon, lat) in FIRE_LOCATIONS.items():
        point_x, point_y = transformer.transform(lon, lat)

        fire_projected[name] = {
            "x": float(point_x),
            "y": float(point_y),
            "inside": bool(
                extent[0] <= point_x <= extent[1]
                and extent[2] <= point_y <= extent[3]
            ),
            "longitude": lon,
            "latitude": lat,
        }

    change_maps = {}
    candidate_results = {}
    statistics = {}
    perimeter_statistics = {}

    for polarization, db_data, common_mask in [
        ("HH", hh_db, common_valid_hh),
        ("HV", hv_db, common_valid_hv),
    ]:

        change_maps[polarization] = {}
        candidate_results[polarization] = {}
        statistics[polarization] = {}
        perimeter_statistics[polarization] = {}

        for before, after in COMPARISONS:
            comparison = f"{before} -> {after}"

            change = db_data[after] - db_data[before]
            values = change[common_mask]

            change_maps[polarization][comparison] = change

            statistics[polarization][comparison] = {
                "mean": float(np.mean(values)),
                "median": float(np.median(values)),
                "std": float(np.std(values)),
                "increased": float(np.mean(values > 0) * 100),
                "decreased": float(np.mean(values < 0) * 100),
            }

            candidate_results[polarization][comparison] = (
                detect_candidate_changes(change, common_mask)
            )

            if perimeter_mask is not None:
                perimeter_statistics[polarization][comparison] = (
                    calculate_region_statistics(
                        change,
                        common_mask,
                        perimeter_mask
                    )
                )

    return {
        "dates": list(FILES.keys()),
        "comparisons": [
            f"{before} -> {after}"
            for before, after in COMPARISONS
        ],
        "hh_db": hh_db,
        "hv_db": hv_db,
        "common_valid_hh": common_valid_hh,
        "common_valid_hv": common_valid_hv,
        "change_maps": change_maps,
        "candidate_results": candidate_results,
        "statistics": statistics,
        "perimeter_statistics": perimeter_statistics,
        "perimeter_mask": perimeter_mask,
        "perimeter_geometry_utm": perimeter_utm,
        "perimeter_status": perimeter_status,
        "extent": extent,
        "fire_projected": fire_projected,
        "roi_shape": common_valid_hh.shape,
        "pixel_spacing": (abs(dx), abs(dy)),
        "threshold_multiplier": THRESHOLD_MULTIPLIER,
    }