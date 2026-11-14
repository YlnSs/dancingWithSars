import h5py
import numpy as np


files = {
    "August 27": "./datasets/NISAR_L2_PR_GCOV_029_028_A_020_2005_DHDH_A_20260827T030948_20260827T031013_P05023_N_P_J_001.h5",
    "September 8": "./datasets/NISAR_L2_PR_GCOV_030_028_A_020_2005_DHDH_A_20260908T030947_20260908T031013_P05023_N_F_J_001.h5",
    "September 20": "./datasets/NISAR_L2_PR_GCOV_031_028_A_020_2005_DHDH_A_20260920T030947_20260920T031013_P05023_F_F_J_001.h5"
}

dataset_path = "science/LSAR/GCOV/grids/frequencyA/HHHH"

attributes_to_check = [
    "description",
    "units",
    "min_value",
    "max_value",
    "mean_value",
    "sample_stddev"
]

for date, file_path in files.items():

    print(f"\n {date}")

    with h5py.File(file_path, "r") as f:

        hhh = f[dataset_path]

        print("Shape:", hhh.shape)
        print("Data type:", hhh.dtype)

        for attribute in attributes_to_check:
            value = hhh.attrs.get(attribute, "Not available")
            print(f"{attribute}: {value}")