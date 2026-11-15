# NISAR Wildfire Explorer
### Exploring wildfire-related surface changes using NASA–ISRO NISAR L-band SAR data

An interactive geospatial application for exploring radar-observed surface changes associated with the September 2026 wildfire near Aksu, Antalya, Türkiye.

**Built for NASA Space Apps Challenge 2026**

[![NASA Space Apps Challenge](https://img.shields.io/badge/NASA%20Space%20Apps-2026-blue)](https://www.spaceappschallenge.org/)

**Live application:** (https://nisar-aksuwildfire-inspector-explorer.streamlit.app/) 
**Dataset:** [NISAR Aksu Wildfire Dataset](https://huggingface.co/datasets/FyS457/nisar-aksu-wildfire-data)

---

## Overview

Wildfires can rapidly transform vegetation and land surfaces. Understanding these changes is important for environmental monitoring, disaster assessment and recovery planning.

The **NISAR Wildfire Explorer** uses L-band Synthetic Aperture Radar (SAR) observations from NASA–ISRO's NISAR mission to explore surface changes around the September 2026 Aksu wildfire in Antalya, Türkiye.

The application provides an interactive environment for comparing radar backscatter observations across three acquisition dates:

- August 27, 2026 — pre-fire reference
- September 8, 2026 — during or shortly after the fire event
- September 20, 2026 — post-event observation

Users can explore HH and HV polarization, compare acquisition dates, inspect spatial patterns of backscatter change, and examine an external fire-perimeter dataset.

**Important:** The application identifies unusual radar-observed surface changes. It does not independently confirm burned areas or distinguish wildfire effects from every other possible environmental cause.

## Key Features

- **Interactive radar visualization:** Explore NISAR HH and HV backscatter.
- **Temporal comparison:** Compare observations from different acquisition dates.
- **Change maps:** Visualize differences in backscatter expressed in decibels (dB).
- **Candidate change areas:** Highlight spatial regions with unusually large changes using a robust statistical threshold.
- **Fire perimeter overlay:** Compare radar observations with an external wildfire perimeter.
- **Inside/outside statistics:** Explore differences between areas inside and outside the supplied perimeter.
- **Display filtering:** Apply a median filter to change maps to make spatial patterns easier to inspect.
- **Interactive exploration:** Navigate the study area using Plotly visualizations.

## Data Sources

### NISAR

The primary data source is the NISAR Level-2 Geocoded Polarimetric (GCOV) product.

NISAR is a joint mission between NASA and the Indian Space Research Organisation (ISRO). Its L-band radar observations allow Earth surface monitoring during both day and night and through many cloud conditions.

The project uses:

- L-band radar observations
- HH polarization
- HV polarization
- Geocoded radar backscatter data

Dataset repository: [Hugging Face — NISAR Aksu Wildfire Dataset](https://huggingface.co/datasets/FyS457/nisar-aksu-wildfire-data)

### Wildfire perimeter

An external fire-perimeter dataset is used as a spatial reference for comparison.

Source: [WorldFires — Aksu, Antalya, September 2026](https://worldfires.org/en/fire/aksu-antalya-2026-09)

The perimeter is not derived from the NISAR change maps.

## Methodology

The application follows a multi-temporal radar comparison workflow.

1. Load the NISAR GCOV acquisitions.
2. Select the study area and relevant radar observations.
3. Extract HH and HV backscatter measurements.
4. Convert linear radar power into decibels:

   `dB = 10 × log10(power)`

5. Compare observations acquired on different dates.
6. Calculate pixel-wise backscatter differences.
7. Identify unusually large changes using a robust statistical threshold based on the median absolute deviation (MAD).
8. Compare the resulting spatial patterns with the external fire perimeter.

The change calculation is:

`Change (dB) = Backscatter_after (dB) − Backscatter_before (dB)`

A positive value indicates increased backscatter; a negative value indicates decreased backscatter.

Candidate change areas are exploratory indicators, not confirmed burned pixels.

## Technology Stack

- **Python** — primary programming language
- **Streamlit** — interactive web application
- **NumPy** — numerical processing
- **h5py** — reading NISAR HDF5 products
- **SciPy** — spatial filtering and statistical processing
- **Plotly** — interactive geospatial visualizations
- **PyProj** — coordinate transformations
- **Shapely** — geometric operations
- **Hugging Face Hub** — hosting and downloading the datasets

## Running Locally

### 1. Clone the repository

```bash
git clone YOUR_GITHUB_REPOSITORY_URL
cd nisar-wildfire-explorer
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Run the application

```bash
streamlit run app.py
```

The application downloads the required data files from the Hugging Face dataset repository.

## Limitations

Radar backscatter is influenced by several environmental factors, including:

- Vegetation structure
- Soil moisture
- Surface roughness
- Incidence and observation geometry
- Seasonal and environmental changes

Consequently, a difference between two radar acquisitions cannot automatically be attributed to wildfire damage.

Other important limitations:

- The analysis uses a limited number of acquisition dates.
- Candidate change regions are not independently validated burned-area classifications.
- The external fire perimeter has its own mapping uncertainty.
- Spatial and temporal differences between datasets can affect comparisons.
- The results should be interpreted as exploratory observations rather than definitive damage assessments.

## Future Work

Potential improvements include:

- Integrating additional NISAR acquisitions.
- Comparing radar observations with optical satellite imagery.
- Validating candidate changes against independently mapped burned areas.
- Investigating soil moisture and vegetation-related effects.
- Developing more robust change-detection methods.
- Extending the workflow to other wildfire events and regions.

## Acknowledgements

This project was developed as part of the **NASA Space Apps Challenge 2026**.

I acknowledge NASA and ISRO for the NISAR mission and the providers of the external wildfire reference data.

---

**Project:** NISAR Wildfire Explorer  
**Study area:** Aksu, Antalya, Türkiye  
**Observation period:** August–September 2026  
**Purpose:** Exploratory analysis of wildfire-related surface changes using satellite radar observations.
