# 🛩️ Aerosim Utils

<div align="center">

[![Python Version](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)


A suite of tools for aircraft trajectory and scenario generation, supporting both real ADS-B data processing and artificial track generation.

[Installation](#-installation) • [Quick Start](#-quick-start)

</div>

## 🌟 Features

<div align="center">

| Category | Features |
|----------|----------|
| 📊 **OpenADSB Track Generator** | • ADS‑B JSON to CSV conversion<br>• Geographic filtering<br>• Time range filtering<br>• Relative ownship path filtering<br>• Trajectory JSON conversion<br>• Simulation scenario creation |
| 🎮 **Artificial Track Generator** | • Random track generation<br>• Circular/elliptical patterns<br>• Flyby/square/rectangle patterns<br>• Zigzag and spiral patterns<br>• Ownship-relative patterns<br>• KML data conversion |
| 🗺️ **Google Earth Integration** | • KML to CSV conversion<br>• Real-world track integration<br>• Custom track creation |
| 📈 **Visualization & Conversion** | • Interactive Folium maps<br>• Combined KML generation<br>• Real-time visualization |
| ⚙️ **Scenario Generation** | • JSON scenario creation<br>• Actor configuration<br>• Sensor setup<br>• FMU model integration |
| 📝 **Scenario Reports** | • Markdown report generation<br>• Trajectory visualization |
| 🛠️ **Utilities** | • LLA/NED coordinate conversion<br>• Distance & bearing calculations<br>• Interactive track visualization |

</div>

## 🚀 Quick Start

### Installation

```bash
# Install from PyPI (Recommended)
pip install aerosim-utils

# Or install from source
cd aerosim-utils
pip install -e .
```

### Basic Usage

<details>
<summary>Process ADS-B Data</summary>

```bash
# Convert ADS-B JSON to CSV
aerosim adsb json2csv -i inputs/ssedata.json -o outputs/output.csv

# Filter tracks around a reference point
aerosim adsb filter -i outputs/output.csv \
    --lat 34.217411 \
    --lon -118.491081 \
    --radius 50 \
    -o outputs/filtered_tracks.csv \
    --tracks-dir tracks

# Convert filtered tracks to trajectory JSON files
aerosim adsb tracks2json -i tracks -o trajectories
```
</details>

<details>
<summary>Generate Artificial Tracks</summary>

```bash
# Generate artificial tracks using a specified maneuver
aerosim artificial generate-tracks \
    --num-tracks 5 \
    --maneuver circular \
    --center-lat 34.217411 \
    --center-lon -118.491081 \
    --center-alt 1000 \
    --separation 0.005 \
    --time-delay 30 \
    --num-points 20 \
    --interval 10 \
    -o outputs/artificial_tracks.csv

# Fly-along mode using an external ownship trajectory
aerosim artificial generate-tracks \
    --num-tracks 3 \
    --maneuver zigzag \
    --center-lat 33.75 \
    --center-lon -118.25 \
    --center-alt 1000 \
    --separation 0.005 \
    --time-delay 30 \
    --num-points 20 \
    --interval 10 \
    -o outputs/artificial_tracks_flyalong.csv \
    --fly-along \
    --ownship-file inputs/ownship_trajectory.json \
    --ownship-format json
```
</details>

<details>
<summary>Convert KML from Google Earth</summary>

```bash
# Convert a KML file from Google Earth to CSV format
aerosim tracks kml2csv -i my_track.kml -o kml_output.csv --interval 10
```
</details>

<details>
<summary>Generate Scenarios</summary>

```bash
# Generate simulation scenario JSON from trajectory files
aerosim scenario generate -t trajectories -o auto_gen_scenario.json
```
</details>

<details>
<summary>Visualization</summary>

```bash
# Generate a combined interactive Folium map
aerosim vis visualize -i tracks -o visualization/folium/combined_map.html --method folium

# Generate a combined KML file
aerosim vis visualize -i trajectories -o visualization/kml/combined_map.kml --method kml
```
</details>

<details>
<summary>Scenario Reports</summary>

```bash
# Generate a markdown report from a scenario JSON file
aerosim report scenario -i scenario.json -o reports/scenario_report.md

# Generate a report with trajectory plot
aerosim report scenario -i scenario.json -o reports/scenario_report.md --plot --plot-output reports/trajectories.png

# Generate reports as part of workflow commands (enabled by default)
aerosim workflow openadsb --input-json data.json --no-report  # Disable report generation
aerosim workflow artificial --no-plot  # Disable trajectory plot
aerosim workflow kml --report-output custom_report.md  # Custom report path
```

The scenario report includes:
- Overview of the scenario
- Clock settings
- Orchestrator configuration
- World settings
- Actor details
- Sensor configurations
- Renderer information
- FMU model details
- Optional trajectory visualization
</details>

<details>
<summary>Helper Utilities</summary>

```bash
# Clamp a value between minimum and maximum
aerosim helpers clamp --value 150 --min 0 --max 100  # Returns 100

# Normalize a heading to 0-360 degrees
aerosim helpers normalize-heading --heading 370  # Returns 10

# Calculate distance and bearing between two points
aerosim helpers distance-bearing \
    --lat1 34.217411 \
    --lon1 -118.491081 \
    --lat2 34.217411 \
    --lon2 -118.491081
```
</details>

## 💻 Python API Usage

```python
from aerosim_utils import ArtificialTrackGenerator, convert_json_to_csv, visualize_folder

# Generate artificial tracks
generator = ArtificialTrackGenerator(
    num_tracks=5,
    track_generator_class='circular',
    center_lat=34.217411,
    center_lon=-118.491081,
    center_alt=1000,
    separation_distance=0.005,
    time_delay=30,
    num_points=20,
    interval_seconds=10
)
generator.generate()
generator.save_to_csv("outputs/artificial_tracks.csv")

# Convert ADS-B JSON data to CSV
convert_json_to_csv("inputs/ssedata.json", "outputs/output.csv")

# Visualize track data
visualize_folder("tracks", "visualization/folium/combined_map.html", method='folium')
```

## ⚙️ Configuration

Customize the package behavior using a configuration file:

```bash
# Show current configuration
aerosim config show

# Set a specific configuration value
aerosim config set DEFAULT_CENTER_LAT 34.217411

# Reset to defaults
aerosim config reset

# Validate configuration
aerosim config validate
```

### Available Settings
```json
{
    "DEFAULT_INPUT_DIR": "inputs",
    "DEFAULT_OUTPUT_DIR": "outputs",
    "DEFAULT_TRACKS_DIR": "tracks",
    "DEFAULT_TRAJECTORIES_DIR": "trajectories",
    "DEFAULT_CENTER_LAT": 34.217411,
    "DEFAULT_CENTER_LON": -118.491081,
    "DEFAULT_RADIUS_KM": 50.0,
    "DEFAULT_ALTITUDE": 1000.0,
    "DEFAULT_INTERVAL_SECONDS": 5.0,
    "DEFAULT_SCENARIO_NAME": "auto_gen_scenario",
    "DEFAULT_WORLD_NAME": "default_world",
    "DEFAULT_SENSOR_CONFIG": {
        "type": "camera",
        "fov": 90,
        "resolution": [1920, 1080],
        "update_rate": 30
    }
}
```


## 🔍 Data Sources

### OpenSky Network

<div align="center">

[![OpenSky Network](https://img.shields.io/badge/OpenSky_Network-0078D4?style=for-the-badge&logo=github&logoColor=white)](https://opensky-network.org/)

</div>

The OpenSky Network provides open access to real‑time and historical ADS‑B data:

- Registration: Sign up for a free account
- Data Access: Use their REST API for real‑time or historical data
- Usage: Save JSON data in the `inputs/` folder

**Resources:**
- [OpenSky Network Documentation](https://opensky-network.org/)
- [MIT LL - em-download-opensky](https://github.com/mit-ll/em-download-opensky)

### ADS-B Exchange

<div align="center">

[![ADS-B Exchange](https://img.shields.io/badge/ADS--B_Exchange-FF6B6B?style=for-the-badge&logo=github&logoColor=white)](https://www.adsbexchange.com/)

</div>

ADSBExchange offers ADS‑B data services:

- Free Feed: Available for non‑commercial projects
- API Access: Follow their documentation and guidelines
- Integration: Store data in `inputs/` directory

## 📝 Creating Tracks in Google Earth

<details>
<summary>Step-by-Step Guide</summary>

### Step 1: Install and Open Google Earth Pro
1. Download from [Google Earth website](https://earth.google.com/web/)
2. Follow installation instructions
3. Launch Google Earth Pro

### Step 2: Create a Track
1. Navigate to your area of interest
2. Click "Add Path" icon
3. Name your track (e.g., "Trajectory 10000")
4. Create track points by clicking
5. Adjust points as needed
6. Customize appearance
7. Click OK to save

### Step 3: Export as KML
1. Find path in "Places" panel
2. Right-click → "Save Place As..."
3. Choose location and filename
4. Select KML format (not KMZ)
5. Click Save

### Step 4: Process with Aerosim Utils
```bash
# Convert KML to CSV
aerosim tracks kml2csv -i my_track.kml -o kml_output.csv --interval 10

# Generate scenario
aerosim scenario generate -t trajectories -o auto_gen_scenario.json
```
</details>

## 🔄 Complete Processing Workflows

<div align="center">

| Workflow | Description | Command |
|----------|-------------|---------|
| OpenADSB | Process real ADS‑B data | `aerosim workflow openadsb` |
| Artificial | Generate artificial tracks | `aerosim workflow artificial` |
| KML | Process Google Earth tracks | `aerosim workflow kml` |

</div>

<details>
<summary>OpenADSB Workflow</summary>

```bash
aerosim workflow openadsb \
    --input-json inputs/your_adsb_data.json \
    --lat 34.217411 \
    --lon -118.491081 \
    --radius 50 \
    --interval 10
```

Steps:
1. Convert raw ADS‑B JSON to CSV
2. Filter based on geographic reference
3. Convert to trajectory JSON
4. Generate simulation scenario
5. Create interactive visualization
</details>

<details>
<summary>Artificial Track Workflow</summary>

```bash
aerosim workflow artificial \
    --num-tracks 5 \
    --maneuver elliptical \
    --center-lat 34.217411 \
    --center-lon -118.491081 \
    --center-alt 1000 \
    --separation 0.005 \
    --time-delay 30 \
    --num-points 20 \
    --interval 10
```

Steps:
1. Generate artificial tracks
2. Save to CSV
3. Convert to trajectory JSON
4. Generate scenario
5. Create visualization
</details>

<details>
<summary>KML Workflow</summary>

```bash
aerosim workflow kml \
    --input-kml inputs/my_track.kml \
    --interval 10
```

Steps:
1. Convert KML to CSV
2. Convert to trajectory JSON
3. Generate scenario
4. Create visualization
</details>

---

<div align="center">

