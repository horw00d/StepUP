# StepUP Gait Analysis Platform

An interactive data visualization and analysis platform built to streamline the exploration of the UNB StepUP-P150 dataset. 

## Background
Gait analysis is the process of characterizing how a person walks based on their biomechanics and movement habits. The [UNB StepUP-P150 dataset](https://www.frdr-dfdr.ca/repo/dataset/5aebad39-7977-475d-8f1b-41f22599b5a4) is the largest high-resolution plantar pressure dataset to date, containing over 200,000 footsteps from 150 diverse participants. 

The high dimensionality and volume of the raw 3D pressure tensors presented an opportunity to create a platform that increases accessibility to the StepUP-P150 dataset and offers high reproducibility to researchers performing gait analysis. This platform provides researchers with a centralized, real-time dashboard to filter, visualize, and extract statistical insights from the data without needing to write custom processing scripts.

## Key Features
The dashboard utilizes Plotly Dash, SQLAlchemy, Pandas, and NumPy, offering two primary scopes of analysis:

* **Trial-Level Analysis:** Optimized for within-subject exploration. Visualizes individual footsteps using a 2D Spatial Walkway, a peak-pressure Footstep Library, and time-series kinematics (Ground Reaction Force and Center of Pressure) to establish normative baselines.
* **Dataset-Level Analysis:** Optimized for cross-subject, macroscopic comparisons. Supports hierarchical aggregation, statistical distribution plots (Box/Violin), bivariate scatter plots with OLS regression, and aggregate kinematic waveforms to compare demographics, footwear types, and walking speeds.

---

## Getting Started

### 1. Sourcing the Data
The raw StepUP-P150 dataset must be downloaded independently before initializing the platform.
1. Download the complete dataset from the [Federated Research Data Repository (FRDR)](https://www.frdr-dfdr.ca/repo/dataset/5aebad39-7977-475d-8f1b-41f22599b5a4).
2. Extract the contents and ensure the parent folder is named exactly `StepUP-P150`.
3. Place the `StepUP-P150` folder directly into the root directory of this project.

### 2. Environment Setup
To ensure environment consistency and prevent dependency conflicts, it is highly recommended to run this application within an isolated Python virtual environment.

```bash
# Clone the repository
git clone [https://github.com/](https://github.com/)[Organization]/StepUP.git
cd StepUP

# Create a virtual environment
python -m venv venv

# Activate the virtual environment
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate

# Install required dependencies
pip install -r requirements.txt
```

### 3. Platform Initialization
Before launching the dashboard, the raw data must be parsed and optimized. The initialization script will automatically ingest the participant metadata into a normalized SQLite database (stepup.db) and pre-compute the 2D peak-pressure static assets required by the frontend.

```bash
python initialize.py
```

### 4. Running the Application
Once the initialization script completes successfully, you can start the local web server:

```bash
python app.py
```

Open a web browser and navigate to the localhost URL provided in your terminal (typically http://127.0.0.1:8050/) to begin exploring the data.

## Repository Structure

* **app.py** The main entry point that initializes the Dash server.
* **initialize.py** Driver script for database ingestion and asset generation.
* **initialization/** Contains the data ingestion and asset generation pipeline scripts.
* **layout/** UI components, static styling, and view routing.
* **callbacks/** Interaction logic bridging the UI and the underlying data model.
* **models.py & database.py** SQLAlchemy ORM definitions and database connection management.
* **data.py & physics.py** Centralized Pandas DataFrame operations and NumPy tensor math.
* **tests/** A pytest suite for validating queries, layout integrity, and processing functions.

## Acknowledgements
This platform was developed in association with the Mobility Intelligence Lab (MOBIL) at the University of New Brunswick.

For inquiries regarding the underlying dataset, please refer to the associated
[Nature Scientific Data publication](https://www.nature.com/articles/s41597-025-05792-1)