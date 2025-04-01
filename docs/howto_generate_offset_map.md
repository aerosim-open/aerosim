# Offset Map JSON Generation Guide

## Summary

This script addresses inconsistencies in altitude data caused by mismatched datums between the EGM08 geoid model and Cesium's tiles. Cesium uses a private datum, leading to discrepancies in altitude values. The Python script:

1. Retrieves the height differences between the expected altitude (computed using standard MSL-to-HAE functions) and the Cesium-rendered ground altitude.
2. Generates an Offset Map using RBF interpolation to create a regular grid of altitude offsets.
3. Facilitates accurate conversion by introducing conversion functions that apply the offset map using bilinear interpolation.

---

## Prerequisites
Install additional required Python libraries:
    - `numpy`
    - `matplotlib`
    - `scipy`

---

## How to Use the Script

### 1. Start the UE5 Renderer and Kafka

- Ensure the UE5 renderer and Kafka server are running before starting the script.
use the following commands to start the UE5 renderer and Kafka server:
Windows:
```bash
./launch_aerosim.bat --unreal-editor
```
Linux:
```bash
./launch_aerosim.sh --unreal-editor
```

- Run the simulation using the play button in the editor

### 2. Run the Script

- Use the `generate_offset_data.py` script to collect altitude offsets and create an offset map. The script requires a JSON file with expected altitudes for known lat/lon locations in HAE.
- input file: JSON file with expected altitudes for known lat/lon locations in HAE.
- output file: JSON file with the offset map.
- grid_spacing: The spacing between grid points in lat lon degrees.
- padding: The padding around the input data in percentage distance.
- visualize: Flag to visualize the resulting offset map using matplotlib.

#### Command
```bash
python generate_offset_data.py --input <input_file> [--output <output_file>] [--grid_spacing <value>] [--padding <value>] [--visualize]
```

### 3. Apply the Offset Map

- Use the resulting offset map json file to import the data into the OffsetMap data structure using the .from_json() method.
- Use the `OffsetMap` class to apply the offset map to a given lat/lon location.

```rust
     let offset_map = OffsetMap::from_json("json_file_path");
     let result_hae = msl_to_hae_with_offset(Vector3::new(lat, lon, msl_alt), &geoid, &offset_map);
```