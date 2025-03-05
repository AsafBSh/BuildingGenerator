# Building Generator v1.1

## Overview

The Building Generator is a tool designed to assist theater creators in constructing custom Objectives for Falcon BMS. It facilitates the accurate placement of buildings and features from a selected database within the BMS environment.

## Key Features

- **GeoData Import:** Loads building footprints and related data from GeoJSON files.
- **Database Integration:** Connects to and utilizes a database of building models and features.
- **Random & GeoJSON-Based Placement:** Supports feature placement using either random distribution or alignment with GeoJSON data.
- **Customizable Parameters:** Allows users to adjust parameters like building height, size, rotation, and density.
- **Automated Feature Selection**: Automatically detects proper models from Database by different types of building's attributes from GeoJson data for best type fitting
- **Falcon BMS Compatibility:** Generates output files compatible with the Falcon BMS format.
- **Graphical User Interface (GUI):** Provides an intuitive interface for easy operation.
- **Statistics:** The GUI provides statistic and data about the generations and feature types used.

## Dependencies

- Python 3.6+
- Libraries
  - geopandas
  - numpy
  - pyproj
  - tkinter
  - customtkinter
  - matplotlib
  - scipy
  - pandas
  - sqlite3
  - re
  - time
  - gzip
  - json
  - math
  - pathlib
  - winreg

## Installation

1. Ensure you have Python 3.6 or higher installed.
  
2. Install the required libraries using pip:
  
  ```
  pip install geopandas numpy pyproj tkinter customtkinter matplotlib scipy pandas
  ```
  

## Usage

1. **Configure Settings:**
  - Set the paths to the Class Table XML file (CT file).
  - Specify the GeoJSON file containing building footprints.
  - Optionally, load a projection file for theater-specific coordinate transformations.
2. **Database Operations:**
  - Generate a new database from the CT file.
  - View and manage existing databases.
3. **GeoData Operations:**
  - Load GeoJSON data to populate the feature list.
  - Adjust the floor height for building height calculations.
4. **Operation Parameters:**
  - Select between random and GeoJSON-based feature placement.
  - Define restrictions to filter the buildings (by Names / Types)
  - Define a radius and amount of object for random creation
  - Set value and presence values or set them to use automatic mapping.
5. **Generate Output:**
  - Customize the output file name and save location.
  - Generate the feature list for Falcon BMS.

## File Structure

- `MainGui.py`: Main GUI application file.
- `Load_Geo_File.py`: Handles loading and processing GeoJSON files.
- `MainCode.py`: Contains the core logic for feature assignment, saving, and statistics.
- `Database.py`: Includes functions for generating the feature database.
- `OSMLegend.py`: Displays the OSM legend.
- `Restrictions.py`: Manages database restrictions
- `InternalConsole.py`: Manages console output
- `ValuesDictionary.py`: Manages values for object creation
- `Assets/`: Contains GUI assets (images, icons).

## Code Description

### Load\_Geo\_File.py

This script contains functions for loading and processing geospatial data from a GeoJSON file.

- `get_field_value(row, field_names, special=None)`: Extracts the first non-null value from a list of field names in a GeoPandas row.
- `get_height_value(value)`: Checks for valid height or height level values.
- `projection(coordinations, string)`: Applies a coordinate projection from WGS84 to a custom projection.
- `Load_Geo_File(json_path, debugger=False, projection_string=None, floor_height=2.286)`: Loads a GeoJSON file, extracts feature information, applies projection (if specified), and calculates feature attributes.

### MainCode.py

This script implements the main algorithms for feature selection, placement, and saving to a file format compatible with Falcon BMS.

- `Load_Db(path, feature_name="All")`: Loads a database from a SQLite file based on different filtering
- `Show_Selected_Features(buildings, Calc_data)`: Display the features that have been selected from Geo Data
- `Show_Selected_Features_2D(plot_option, buildings=None, Calc_data=None, feature_entries=None,models_FrameData=None)`: Display the 2D features that have been selected from Geo Data or from models
- `Show_Selected_Features_3D(plot_option,buildings=None, Calc_data=None,feature_entries=None,models_FrameData=None)`: Display the 3D features that have been selected from Geo Data or from models
- `filter_structures(Geo_Data, Raw_Geo_Data, Num_Of_Structures, selection_option="Total Size")`: Selects a subset of structures from a given dataframe based on a probabilistic algorithm.
- `Decision_Algo(GeoFeature, GeoFeatureData, Geo_Idx, selected_BMSModels, floor_height, State, num_floors=0)`: Finds the most appropriate BMS model based on given criteria.
- `Rotation_Definer(Angle, BMS_Length_idx)`: Assigns a fixed angle for rotation based on the longest side of the model.
- `Assign_features_randomly(num_features, radius, DB_path, DB_restrictions)`: Randomly selects features and generates random coordinates within a specified radius.
- `Save_random_features(...)`: Saves randomly generated features to a file in the Falcon BMS format.
- `Assign_features_accuratly(...)`: Fills features according to criterias
- `Save_accurate_features(...)`: Saves accurately generated features to a file in the Falcon BMS format.
- `get_value(Values_i, Values_f, model_type)`: Gets a value based on input parameters and values dictionary.
- `write_to_file(SavePath, BuildingGeneratorVer, AOI_center, num_features, feature_entries)`: Writes feature entries to a file.
- `format_entry(...)`: Formats a feature entry string.
- `load_values_dict()`: Loads values dictionary from a JSON file.
- `sort_feature_entries(feature_entries, sort_option)`: Sorts the feature entries based on the specified option.
- `save_statistics(stats)`: Saves statistics to a gzipped JSON file.
- `update_statistics(num_features, feature_types)`: Updates statistics.
- `load_statistics()`: Loads statistics from a gzipped JSON file.
- `Auto_Selected(Db_path, Selected_GeoFeature)`: Automatically detects possible keys in the GeoFeature and loading a proper Models from the Database for better type fitting
- `split_string(s)`: Splits a string by multiple delimiters and returns a list of lowercase terms.

### MainGui.py

This script defines the GUI using `tkinter` and `customtkinter`.

## Contributing

Contributions are welcome!

## License

[MIT License](LICENSE)
