import geopandas as gpd
import numpy as np
from Find_features import fitted_features
from pyproj import Transformer
import math as m
import logging
import traceback
import sys
import os

# Set up logging - use standard pattern to inherit from main application
logger = logging.getLogger(__name__)

# Ensure logger inherits configuration from root logger
logger.propagate = True


def get_field_value(row, field_names, special=None):
    """
    Try to get the value of the first non-null field from the list.
    if the field is not found, return False.
    find if the structure is detailed by checking the field value
    """
    # List of values that are not considered special/detailed
    non_special_values = [
        " ", "", "roof", "no", "building", "yes", "0", "false", "true", 
        "False", "True", "none", "None", 0, False, True, None
    ]
    
    for field in field_names:
        try:
            value = row[field]
            # If the value is a string, return it
            if isinstance(value, str):
                value = value.lower()
                # Check if special is a None, if not, check if the value is not in the list to determine if it is special
                if special is not None:
                    if special or value not in non_special_values:
                        return value, True
                    else:
                        return value, False
                return value
            elif value is not None:
                # Check if value is numeric to avoid m.isnan() on strings
                try:
                    if isinstance(value, (int, float)) and not m.isnan(value):
                        # Same check for non-string values (no lowercase conversion)
                        if special is not None:
                            # Convert to string and check against non_special_values
                            str_value = str(value).lower()
                            if special or (str_value not in non_special_values and value not in non_special_values):
                                return value, True
                            else:
                                return value, False
                        # If the value is not None and not nan, return it
                        return value
                    else:
                        # Non-numeric value (including strings already handled above)
                        if special is not None:
                            # Convert to string and check against non_special_values
                            str_value = str(value).lower()
                            if special or (str_value not in non_special_values and value not in non_special_values):
                                return value, True
                            else:
                                return value, False
                        return value
                except (TypeError, ValueError):
                    # Fallback for any unexpected value types
                    if special is not None:
                        str_value = str(value).lower()
                        if special or (str_value not in non_special_values and value not in non_special_values):
                            return value, True
                        else:
                            return value, False
                    return value
        except Exception as e:
            logger.debug(f"Error accessing field '{field}': {str(e)}")
            pass

    if special is not None:
        return False, special
    else:
        return False


def get_height_value(value):
    """The function will try to refine the understanding if there is a valid value for height or height level"""
    try:
        # Check if feature["height"] is a number
        if isinstance(value, bool):
            none_height = True
        elif isinstance(value, (int, float)) and value > 0:
            none_height = False
        elif isinstance(value, str):
            # Handle string values that might contain valid numbers
            try:
                value_str = value.strip()
                if value_str and value_str.lower() not in ["none", "null", "n/a", "", "false", "true"]:
                    float_value = float(value_str)
                    none_height = float_value <= 0  # If value is negative or zero, consider it invalid
                else:
                    none_height = True
            except (ValueError, TypeError):
                none_height = True
        else:
            # Try to convert feature["height"] to a float
            try:
                float_value = float(value)
                if float_value <= 0:  # If value is negative or zero, ignore
                    none_height = True
                else:
                    none_height = False
            except Exception as e:
                logger.debug(f"Error converting height value to float: {str(e)}")
                none_height = True
    except Exception as e:
        logger.debug(f"Error processing height value: {str(e)}")
        none_height = True
    return none_height


def parse_height_value(value):
    """Parse and convert height value to float, handling various formats and units"""
    if value is None or value is False:
        return None, None
    
    try:
        if isinstance(value, (int, float)):
            if value > 0:
                return float(value), "meters"
            return None, None
        
        if isinstance(value, str):
            value_str = value.strip().lower()
            if not value_str or value_str in ["none", "null", "n/a", "", "false", "true", "unknown"]:
                return None, None
            
            # Handle common height formats with units
            # Remove quotes and clean up
            value_str = value_str.replace('"', '').replace("'", "'")
            
            # Handle feet and inches (e.g., "12'6\"", "12'", "12 ft", "12 feet")
            if "'" in value_str or 'ft' in value_str or 'feet' in value_str:
                try:
                    # Handle formats like "12'6\"" or "12'6"
                    if "'" in value_str:
                        parts = value_str.split("'")
                        feet = float(parts[0])
                        inches = 0
                        if len(parts) > 1 and parts[1]:
                            inch_part = parts[1].replace('"', '').replace('\\', '').strip()
                            if inch_part:
                                inches = float(inch_part)
                        total_feet = feet + inches / 12.0
                        return total_feet * 0.3048, "meters"  # Convert feet to meters
                    
                    # Handle "12 ft" or "12 feet"
                    value_str = value_str.replace('ft', '').replace('feet', '').strip()
                    return float(value_str) * 0.3048, "meters"
                except (ValueError, IndexError):
                    pass
            
            # Handle meters (e.g., "12m", "12 m", "12 meters")
            if 'm' in value_str and 'ft' not in value_str:
                try:
                    # Remove unit indicators
                    clean_str = value_str.replace('m', '').replace('meters', '').replace('metre', '').strip()
                    return float(clean_str), "meters"
                except ValueError:
                    pass
            
            # Handle simple numeric values (assume meters)
            try:
                numeric_value = float(value_str)
                if numeric_value > 0:
                    return numeric_value, "meters"
            except ValueError:
                pass
                
        return None, None
        
    except Exception as e:
        logger.debug(f"Error parsing height value '{value}': {str(e)}")
        return None, None


def calculate_comprehensive_height(feature, floor_height_meters=2.286):
    """
    Calculate building height using comprehensive OSM height data with intelligent fallbacks
    
    Returns: (height_in_meters, source_description)
    """
    feature_idx = feature.get('index', 'unknown')
    
    # Building type-specific floor heights (in meters)
    building_type_heights = {
        'office': 3.5,
        'commercial': 4.0, 
        'retail': 4.0,
        'warehouse': 6.0,
        'industrial': 5.0,
        'hospital': 3.8,
        'school': 3.2,
        'church': 6.0,
        'cathedral': 8.0,
        'temple': 5.0,
        'mosque': 5.0,
        'synagogue': 5.0,
        'hotel': 3.0,
        'residential': 2.7,
        'apartments': 2.7,
        'house': 2.5,
        'detached': 2.5,
        'terraced': 2.5,
        'semi-detached': 2.5,
        'bungalow': 2.3,
        'garage': 2.5,
        'shed': 2.2,
        'barn': 4.0,
        'greenhouse': 3.0,
        'hangar': 8.0,
        'stadium': 10.0,
        'sports_hall': 8.0,
        'train_station': 6.0,
        'tower': 3.0,  # Per level
        'yes': floor_height_meters,  # Generic building
    }
    
    # Get building-specific floor height
    building_type = feature.get('building_type', 'yes')
    if isinstance(building_type, str):
        type_floor_height = building_type_heights.get(building_type.lower(), floor_height_meters)
    else:
        type_floor_height = floor_height_meters
    
    # 1. Try direct height measurements (highest priority)
    height_value, height_unit = parse_height_value(feature.get('height'))
    if height_value is not None:
        logger.debug(f"Feature {feature_idx}: Using direct height {height_value:.2f}m from 'height' tag")
        return height_value, f"height={height_value:.2f}m"
    
    # 2. Try estimated height
    est_height_value, est_height_unit = parse_height_value(feature.get('est_height'))
    if est_height_value is not None:
        logger.debug(f"Feature {feature_idx}: Using estimated height {est_height_value:.2f}m from 'est_height' tag")
        return est_height_value, f"est_height={est_height_value:.2f}m"
    
    # 3. Calculate from building levels
    building_levels_value, _ = parse_height_value(feature.get('building_levels'))
    roof_levels_value, _ = parse_height_value(feature.get('roof_levels'))
    min_level_value, _ = parse_height_value(feature.get('min_level'))
    
    if building_levels_value is not None and building_levels_value > 0:
        # Calculate total levels
        total_levels = building_levels_value
        
        # Add roof levels if available
        if roof_levels_value is not None and roof_levels_value > 0:
            total_levels += roof_levels_value
            
        # Calculate height from levels
        calculated_height = total_levels * type_floor_height
        
        # Add minimum height offset if building is elevated
        min_height_value, _ = parse_height_value(feature.get('min_height'))
        if min_height_value is not None and min_height_value > 0:
            calculated_height += min_height_value
        elif min_level_value is not None and min_level_value > 0:
            calculated_height += min_level_value * type_floor_height
        
        roof_str = f"+{roof_levels_value}roof" if roof_levels_value else ""
        min_str = f"+{min_height_value:.1f}m_min" if min_height_value else (f"+{min_level_value}lvl_min" if min_level_value else "")
        
        logger.debug(f"Feature {feature_idx}: Calculated height {calculated_height:.2f}m from {building_levels_value} levels (floor_height={type_floor_height}m{roof_str}{min_str})")
        return calculated_height, f"levels={building_levels_value}{roof_str}, floor_height={type_floor_height:.1f}m{min_str}"
    
    # 4. Try roof height only (unusual case)
    roof_height_value, _ = parse_height_value(feature.get('roof_height'))
    if roof_height_value is not None and roof_height_value > 0:
        # Estimate total height as roof height + 1 level
        estimated_height = roof_height_value + type_floor_height
        logger.debug(f"Feature {feature_idx}: Estimated height {estimated_height:.2f}m from roof_height {roof_height_value:.2f}m + 1 level")
        return estimated_height, f"roof_height={roof_height_value:.2f}m + 1_level({type_floor_height:.1f}m)"
    
    # 5. Use building-type-specific default
    default_height = type_floor_height  # Single-story default
    logger.debug(f"Feature {feature_idx}: Using default height {default_height:.2f}m for building type '{building_type}'")
    return default_height, f"default_for_{building_type}={default_height:.1f}m"


def projection(coordinations, string):
    """The fucntion apply projection from WGS84 to any custom projection of theater
    input:  coordinations: list of lists, first argument must be lan(x) and long(y)
            string: string of the projection
    oputput: list of list of the projected to BMS x,y"""

    logger.debug(f"Starting coordinate projection with {len(coordinations)} coordinates using projection: {string}")
    
    try:
        # Define the source and target projections
        transformer = Transformer.from_crs("4326", string, always_xy=True)
        logger.debug("Coordinate transformer created successfully")
    except Exception as e:
        error_msg = f"Failed to create coordinate transformer: {str(e)}"
        logger.error(error_msg)
        
        # Enhanced error logging for compiled executables
        if getattr(sys, 'frozen', False):
            logger.critical("PROJECTION ERROR IN COMPILED EXECUTABLE")
            logger.critical(f"PROJ_LIB: {os.environ.get('PROJ_LIB', 'NOT SET')}")
            logger.critical("Ensure PROJ library and data files are bundled with executable")
        
        raise ValueError(f"Coordinate projection setup failed: {error_msg}")

    # Transform the point from WGS84 to the target projection
    projected_coordinations = []
    skipped_count = 0
    
    for coord in coordinations:
        try:
            # Ensure coordinates are float values
            x, y = float(coord[0]), float(coord[1])
            x_bms, y_bms = transformer.transform(x, y)
            projected_coordinations.append([x_bms, y_bms])
        except (ValueError, TypeError) as e:
            # Skip invalid coordinates and log them
            logger.warning(f"Skipping invalid coordinate {coord}: {str(e)}")
            skipped_count += 1
            continue
    
    # Log projection results summary
    if skipped_count > 0:
        logger.warning(f"Projection completed: {len(projected_coordinations)} successful, {skipped_count} skipped")
    else:
        logger.debug(f"Projection completed successfully for all {len(projected_coordinations)} coordinates")
        
    return projected_coordinations


def Load_Geo_File(
    json_path, projection_string=None, floor_height=2.286
):
    # Enhanced logging for compiled executable debugging
    is_compiled = getattr(sys, 'frozen', False)
    logger.info(f"Starting GeoJSON processing with parameters:")
    logger.info(f"  - GeoJSON path: {json_path}")
    logger.info(f"  - Projection string: {'Provided' if projection_string else 'None'}")
    logger.info(f"  - Floor height: {floor_height} meters")
    logger.info(f"  - Running environment: {'Compiled executable' if is_compiled else 'Python script'}")
    
    # Log environment info for compiled executable debugging
    if is_compiled:
        logger.info(f"  - Executable directory: {os.path.dirname(sys.executable) if hasattr(sys, 'executable') else 'Unknown'}")
        logger.info(f"  - GDAL_DATA: {os.environ.get('GDAL_DATA', 'Not set')}")
        logger.info(f"  - PROJ_LIB: {os.environ.get('PROJ_LIB', 'Not set')}")
        logger.info("  - If geospatial loading fails, ensure GDAL, GEOS, PROJ libraries are bundled with executable")
    
    # meter2feet_google = 3.2808399
    meter2feet_BMS = 3.27998

    # Validate input parameters
    if not json_path:
        raise ValueError("GeoJSON file path cannot be empty")
    
    # Check if file exists
    if not os.path.exists(json_path):
        raise FileNotFoundError(f"GeoJSON file not found: {json_path}")
    
    # Check if file is readable
    if not os.access(json_path, os.R_OK):
        error_msg = f"Cannot read GeoJSON file: {json_path}"
        logger.critical(error_msg)
        raise PermissionError(error_msg)
    
    # Load the GeoJSON file
    geojson_file = json_path
    logger.info(f"Loading GeoJSON from: {json_path}")
    
    try:
        gdf = gpd.read_file(geojson_file)
        logger.info(f"GeoJSON loaded successfully with {len(gdf)} features")
        
        if len(gdf) == 0:
            error_msg = f"GeoJSON file is empty: {json_path}"
            logger.error(error_msg)
            raise ValueError(error_msg)
            
    except Exception as e:
        error_details = traceback.format_exc()
        error_msg = f"Failed to read GeoJSON file '{json_path}': {str(e)}"
        logger.error(error_msg)
        logger.debug(f"Detailed error: {error_details}")
        
        # Enhanced error diagnostics for compiled executables
        if is_compiled:
            logger.critical("=" * 50)
            logger.critical("COMPILED EXECUTABLE GEOSPATIAL ERROR DETECTED")
            logger.critical("=" * 50)
            logger.critical(f"Error type: {type(e).__name__}")
            logger.critical(f"Error message: {str(e)}")
            logger.critical(f"File being loaded: {json_path}")
            logger.critical(f"Current working directory: {os.getcwd()}")
            logger.critical(f"Python executable: {sys.executable}")
            logger.critical(f"GDAL_DATA environment: {os.environ.get('GDAL_DATA', 'NOT SET')}")
            logger.critical(f"PROJ_LIB environment: {os.environ.get('PROJ_LIB', 'NOT SET')}")
            logger.critical("TROUBLESHOOTING STEPS:")
            logger.critical("1. Ensure GDAL, GEOS, PROJ libraries are included in compilation")
            logger.critical("2. Include GDAL and PROJ data files in executable bundle")
            logger.critical("3. Verify Fiona and GeoPandas are properly bundled")
            logger.critical("4. Check if all required DLL files are in executable directory")
            logger.critical("5. Try setting GDAL_DATA and PROJ_LIB environment variables manually")
            logger.critical("=" * 50)
        
        raise ValueError(error_msg)
    logger.debug("Fetching GeoData details for each feature")

    # Create a list to store the extracted information for each feature and center list of each feature
    feature_list = []
    center_list = []
    
    # Track skipped features for final reporting
    skipped_features = []
    skipped_count = 0

    # count detailed features
    detailed_features = []
    special = False
    
    # Keep track of valid feature indices for proper array alignment
    valid_feature_indices = []
    
    # Track height sources for summary logging
    height_sources = {}

    # Extract the important values along with all coordinates
    for index, row in gdf.iterrows():
        try:
            name = get_field_value(row, ["name:en", "name:int", "name"])
            if row["geometry"] is None:  # Handle error by data
                logger.warning(f"Null geometry in row {index}")
                skipped_features.append({'index': index, 'error': 'Null geometry', 'details': 'Feature has no geometry data'})
                skipped_count += 1
                continue
                
            try:  # Handle error by data
                geom_type = row["geometry"].geom_type
            except Exception as e:
                logger.error(f"Error processing row {index}: {e}")
                skipped_features.append({'index': index, 'error': 'Invalid geometry', 'details': str(e)})
                skipped_count += 1
                continue
                
            # Building characteristics (for height estimation and feature classification)
            building, special = get_field_value(row, ["building"], special)
            
            # Extract comprehensive height and level data from all OSM variations for calculation
            osm_height_data = {
                'height': get_field_value(row, ["height", "building:height"]),
                'building_levels': get_field_value(row, ["building:levels", "levels"]),
                'min_height': get_field_value(row, ["min_height", "building:min_height"]),
                'min_level': get_field_value(row, ["building:min_level", "min_level"]),
                'roof_height': get_field_value(row, ["roof:height", "building:roof:height"]),
                'roof_levels': get_field_value(row, ["roof:levels"]),
                'underground_levels': get_field_value(row, ["building:levels:underground"]),
                'est_height': get_field_value(row, ["est_height"]),
                'building_type': building,
                'index': index
            }
            
            # Calculate final height immediately using comprehensive OSM data
            calculated_height_meters, height_source = calculate_comprehensive_height(osm_height_data, floor_height)
            calculated_height_feet = calculated_height_meters * meter2feet_BMS  # Convert to feet for BMS
            
            # Track height sources for summary logging
            source_key = height_source.split('=')[0]  # Get main source type
            height_sources[source_key] = height_sources.get(source_key, 0) + 1
            
            aeroway, special = get_field_value(row, ["aeroway"], special)
            amenity, special = get_field_value(row, ["amenity"], special)
            barrier, special = get_field_value(row, ["barrier"], special)
            bms, special = get_field_value(row, ["bms"], special)
            bridge, special = get_field_value(row, ["bridge"], special)
            diplomatic, special = get_field_value(row, ["diplomatic"], special)
            leisure, special = get_field_value(row, ["leisure"], special)
            man_made, special = get_field_value(row, ["man_made"], special)
            military, special = get_field_value(row, ["military"], special)
            office, special = get_field_value(row, ["office"], special)
            power, special = get_field_value(row, ["power"], special)
            religion, special = get_field_value(row, ["religion"], special)
            service, special = get_field_value(row, ["service"], special)
            sport, special = get_field_value(row, ["sport"], special)
            tower, special = get_field_value(row, ["tower"], special)

            # We'll add to detailed_features only for features we successfully process fully
            # This keeps the arrays aligned later
            special_value = 1 if special else 0
            special = False

            # Handle both "Polygon" and "MultiPolygon" geometries
            if geom_type in ["Polygon", "MultiPolygon"]:
                try:
                    polygons = (
                        [row["geometry"]] if geom_type == "Polygon" else row["geometry"].geoms
                    )
                    coordinates = []
                    for polygon in polygons:
                        try:
                            # Convert polygon exterior to numpy array ensuring all values are float type
                            exterior_coords = np.array(polygon.exterior.coords, dtype=float)
                            
                            # Check if projection_string is available if so, apply projection and continue as planned
                            if projection_string and projection_string != "":
                                exterior_coords = projection(exterior_coords, projection_string)
                            coordinates.append(exterior_coords)
                        except Exception as e:
                            logger.warning(f"Error processing polygon in feature {index}: {e}")
                            continue
                            
                    if not coordinates:
                        logger.warning(f"No valid coordinates found in feature {index}")
                        skipped_features.append({'index': index, 'error': 'Empty coordinates', 'details': 'No valid coordinates found after processing polygons'})
                        skipped_count += 1
                        continue
                        
                    # Ensure we have valid coordinates before proceeding
                    if len(coordinates) == 0 or len(coordinates[0]) < 3:  # Need at least 3 points to form a polygon
                        logger.warning(f"Insufficient points in feature {index}: {len(coordinates[0]) if coordinates else 0} points")
                        skipped_features.append({'index': index, 'error': 'Insufficient points', 'details': f'Need at least 3 points to form a polygon, got {len(coordinates[0]) if coordinates else 0}'})
                        skipped_count += 1
                        continue
                        
                    Real_center, rotation_angle, side_lengths = fitted_features(coordinates[0])
                    # add to center list for later average center calculation
                    center_list.append(Real_center)
                except Exception as e:
                    error_details = traceback.format_exc()
                    logger.error(f"Error calculating feature {index} bounds: {str(e)}")
                    logger.debug(f"Detailed error for feature {index}: {error_details}")
                    skipped_features.append({'index': index, 'error': 'Calculation error', 'details': str(e)})
                    skipped_count += 1
                    continue
            else:
                # Handle other geometry types as needed
                logger.warning(f"Unsupported geometry type for feature {index}: {geom_type}")
                skipped_features.append({'index': index, 'error': 'Unsupported geometry', 'details': f'Geometry type {geom_type} is not supported'})
                skipped_count += 1
                continue

            # Ensure we have valid coordinates before proceeding with measurements
            if coordinates is not None and len(coordinates) > 0:
                # Check if side_lengths[0] is greater than side_lengths[1]
                if side_lengths[0] > side_lengths[1]:
                    side_bigger = side_lengths[0]
                    side_smaller = side_lengths[1]
                else:
                    side_bigger = side_lengths[1]
                    side_smaller = side_lengths[0]

                # Raw data from telemetry
                feature_data = {
                    "index": index,
                    "name": name,
                    "length": side_bigger * meter2feet_BMS,  # Convert length to feet
                    "width": side_smaller * meter2feet_BMS,  # Convert weidth to feet
                    "rotation": rotation_angle,  # calculated rotation of fitted square
                    "Real_World_center": Real_center,  # Coordination through fitted square
                    "type": geom_type,
                    "building_levels": osm_height_data['building_levels'],
                    "height": calculated_height_feet,  # Final calculated height in feet for BMS from comprehensive OSM data
                    "aeroway": aeroway,
                    "amenity": amenity,
                    "barrier": barrier,
                    "bms": bms,
                    "bridge": bridge,
                    "building": building,
                    "diplomatic": diplomatic,
                    "leisure": leisure,
                    "man_made": man_made,
                    "military": military,
                    "office": office,
                    "power": power,
                    "religion": religion,
                    "service": service,
                    "sport": sport,
                    "tower": tower,
                }
                feature_list.append(feature_data)
                # Only now, since we have a complete and valid feature, add to the detailed_features list
                detailed_features.append(special_value)
                valid_feature_indices.append(index)
                
                # Log detailed structure information at debug level
                logger.debug(
                    f"Structure #{index}, size: {round(side_bigger * meter2feet_BMS,3)} x {round(side_smaller * meter2feet_BMS,3)} x {round(calculated_height_feet,1)}ft ({round(calculated_height_meters,2)}m) fetched ({height_source})"
                )
        except Exception as e:
            error_details = traceback.format_exc()
            logger.error(f"Unexpected error processing feature {index}: {str(e)}")
            logger.debug(f"Detailed error for feature {index}: {error_details}")
            skipped_features.append({'index': index, 'error': 'Unexpected error', 'details': str(e)})
            skipped_count += 1

    ### Old Way
    # # convert into falcon coordination = coor/1000, x,y = [0,1] -> xxx,yyy = [-1640,+1640]
    # center_list = np.round(np.array(center_list), decimals=10)*1640/(1000)    # Format, first column == real X, second column == real Y
    #
    # # Calc avarage center of the system
    # main_center = np.round(np.mean(center_list, axis=0), decimals=10)
    #
    # # Calculate the differences between points and center
    # center_related = center_list - main_center

    # Check if we have any valid features to process
    if len(center_list) == 0:
        logger.error("No valid features could be processed from the GeoJSON file")
        raise ValueError("Could not extract any valid features from the GeoJSON file")
    
    # Log summary of skipped features
    if skipped_count > 0:
        logger.warning(f"Skipped {skipped_count} features due to errors ({skipped_count/len(gdf)*100:.1f}% of total)")
        for i, skipped in enumerate(skipped_features[:5]):  # Log first 5 skipped features
            logger.warning(f"Skipped feature {skipped['index']}: {skipped['error']} - {skipped['details']}")
        if len(skipped_features) > 5:
            logger.warning(f"... and {len(skipped_features) - 5} more skipped features")
    
    # Calc center of all features
    try:
        # Ensure all values in center_list are numeric before conversion
        center_list = np.array(center_list, dtype=float)
        center_list = np.round(center_list, decimals=10) * meter2feet_BMS
        main_center = np.round(np.mean(center_list, axis=0), decimals=10)
        center_related = center_list - main_center
    except Exception as e:
        logger.error(f"Error calculating center: {str(e)}")
        # If there's an error in the center calculation, raise a more specific exception
        if len(feature_list) == 0:
            raise ValueError("No features could be successfully processed")
        raise ValueError(f"Error in center calculation: {str(e)}")

    # Set Center from feet to Km(1000m)
    main_center = main_center / (meter2feet_BMS)
    if projection_string and projection_string != "":
        main_center = main_center / 1000

    # Calculate radius and angle (polar space) for each point with falcon coordination
    try:
        # Ensure the arrays are properly shaped for operations
        if center_related.shape[0] == 0:
            logger.error("No valid centers were found for features")
            raise ValueError("No valid centers were found for features")
            
        Radius = np.sqrt(center_related[:, 0] ** 2 + center_related[:, 1] ** 2)
        angles = np.arctan2(center_related[:, 1], center_related[:, 0])

        # Convert angles of polar space to degrees
        angles_deg = np.degrees(angles)
        angles_deg = (angles_deg + 360) % 360
    except Exception as e:
        logger.error(f"Error calculating radius and angles: {str(e)}")
        raise ValueError(f"Error in calculating spatial relationships: {str(e)}")

    sizes_list = []
    heights = []
    Floor_height_feet = floor_height * meter2feet_BMS  # default 7.5 feet == 2.286 meter

    # Iterate through the list to extract heights (already in feet) and calculate sizes
    for feature in feature_list:
        try:
            # Height is already calculated in feet for BMS
            height_feet = feature["height"]
            heights.append(height_feet)
            
            # Sizes - ensure values are numeric
            sizes_list.append(float(feature["length"]) * float(feature["width"]))
            
        except Exception as e:
            logger.warning(f"Error processing feature heights or sizes for index {feature.get('index', 'unknown')}: {str(e)}")
            heights.append(Floor_height_feet)  # Use default height
            sizes_list.append(100.0)  # Use default size
            height_sources['error_fallback'] = height_sources.get('error_fallback', 0) + 1
    
    # Log summary of height sources used
    if height_sources:
        logger.info(f"Height calculation summary:")
        for source, count in sorted(height_sources.items(), key=lambda x: x[1], reverse=True):
            percentage = (count / len(feature_list)) * 100
            logger.info(f"  - {source}: {count} features ({percentage:.1f}%)")
    
    # Log height statistics
    if heights:
        avg_height_ft = sum(heights) / len(heights)
        min_height_ft = min(heights)
        max_height_ft = max(heights)
        # Convert to meters for reference
        avg_height_m = avg_height_ft / meter2feet_BMS
        min_height_m = min_height_ft / meter2feet_BMS
        max_height_m = max_height_ft / meter2feet_BMS
        logger.info(f"Height statistics: avg={avg_height_ft:.1f}ft ({avg_height_m:.1f}m), min={min_height_ft:.1f}ft ({min_height_m:.1f}m), max={max_height_ft:.1f}ft ({max_height_m:.1f}m)")

    # unite into array of data
    column_names = [
        "Geo Data Index",
        "Height (feet)",
        "Surface Size (feet^2)",
        "Location Radius (feet)",
        "Location Angle (Deg)",
        "XXX Cords",
        "YYY Cords",
        "Detailed Structure",
    ]

    # Verify all array lengths match for consistent data structure
    logger.debug(f"Feature list length: {len(feature_list)}")
    logger.debug(f"Heights length: {len(heights)}")
    logger.debug(f"Sizes length: {len(sizes_list)}")
    logger.debug(f"Radius length: {len(Radius)}")
    logger.debug(f"Angles length: {len(angles_deg)}")
    logger.debug(f"Center related length: {len(center_related)}")
    logger.debug(f"Detailed features length: {len(detailed_features)}")
    
    # Ensure all arrays have the same length before creating the data array
    n_features = len(feature_list)
    
    # If needed, pad or truncate arrays to match
    if len(heights) != n_features:
        logger.warning(f"Heights array length mismatch. Adjusting from {len(heights)} to {n_features}")
        heights = heights[:n_features] if len(heights) > n_features else heights + [Floor_height_feet] * (n_features - len(heights))
    
    if len(sizes_list) != n_features:
        logger.warning(f"Sizes array length mismatch. Adjusting from {len(sizes_list)} to {n_features}")
        sizes_list = sizes_list[:n_features] if len(sizes_list) > n_features else sizes_list + [100.0] * (n_features - len(sizes_list))
    
    if len(detailed_features) != n_features:
        logger.warning(f"Detailed features array length mismatch. Adjusting from {len(detailed_features)} to {n_features}")
        detailed_features = detailed_features[:n_features] if len(detailed_features) > n_features else detailed_features + [0] * (n_features - len(detailed_features))

    # Create data array with consistent shapes
    calculated_data = np.zeros((n_features, 8))
    calculated_data[:, 0] = np.arange(n_features).reshape(-1)  # all Geo data arrange in dictionary
    calculated_data[:, 1] = np.array(heights, dtype=float).reshape(-1)  # Heights of all the buildings
    calculated_data[:, 2] = np.array(sizes_list, dtype=float).reshape(-1)  # Sizes of all the buildings

    # Only use as many radius/angle values as we have features
    radius_to_use = Radius[:n_features] if len(Radius) > n_features else np.pad(Radius, (0, n_features - len(Radius)), 'constant', constant_values=0)
    angles_to_use = angles_deg[:n_features] if len(angles_deg) > n_features else np.pad(angles_deg, (0, n_features - len(angles_deg)), 'constant', constant_values=0)
    
    calculated_data[:, 3] = radius_to_use  # Radius compare to the avg center of each building
    calculated_data[:, 4] = angles_to_use  # Angle to the avg center of each building
    
    # Handle center_related which is 2D
    if len(center_related) >= n_features:
        calculated_data[:, 5:7] = center_related[:n_features]  # Location in 2 columns, (XXX,YYY)
    else:
        # Pad center_related if needed
        padding_needed = n_features - len(center_related)
        padded_center = np.pad(center_related, ((0, padding_needed), (0, 0)), 'constant', constant_values=0)
        calculated_data[:, 5:7] = padded_center  # Location in 2 columns, (XXX,YYY)
    
    calculated_data[:, 7] = np.array(detailed_features, dtype=float).reshape(-1)  # Detailed structures

    calculated_data_with_Names = np.core.records.fromarrays(
        calculated_data.transpose(), names=column_names
    )
    # Log successful completion of GeoData processing
    logger.info(f"GeoData has been fetched and processed successfully: {len(feature_list)} valid features out of {len(gdf)} total")
    if skipped_count > 0:
        logger.info(f"Skipped {skipped_count} features due to various errors")
    return feature_list, calculated_data_with_Names, main_center
