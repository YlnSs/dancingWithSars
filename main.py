import h5py
import numpy as np


during_path = "./datasets/NISAR_L2_PR_GCOV_030_028_A_020_2005_DHDH_A_20260908T030947_20260908T031013_P05023_N_F_J_001.h5"
after_path = "./datasets/NISAR_L2_PR_GCOV_031_028_A_020_2005_DHDH_A_20260920T030947_20260920T031013_P05023_F_F_J_001.h5"
grid_path = "science/LSAR/GCOV/grids/frequencyA"
with h5py.File(during_path, "r") as before, h5py.File(after_path, "r") as after:
    grid_before = before[grid_path]
    grid_after = after[grid_path]

    x_before = grid_before["xCoordinates"][:]
    x_after = grid_after["xCoordinates"][:]

    y_before = grid_before["yCoordinates"][:]
    y_after = grid_after["yCoordinates"][:]

    print("HHHH shapes:")
    print(grid_before["HHHH"].shape)
    print(grid_after["HHHH"].shape)

    print("\nX coordinates identical:",
          np.array_equal(x_before, x_after))

    print("Y coordinates identical:",
          np.array_equal(y_before, y_after))
