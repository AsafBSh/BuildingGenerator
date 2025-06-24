import geopandas as gpd
import numpy as np
from Find_features import fitted_features
from pyproj import Transformer
import math as m
import logging
import traceback


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
            elif value is not None and not m.isnan(value):
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
        except:
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
        else:
            # Try to convert feature["height"] to a float
            try:
                float(value)
                if value < 0:  # If value is negative, ignore
                    none_height = True
                else:
                    none_height = False
            except:
                none_height = True
    except:
        none_height = True
    return none_height


def projection(coordinations, string):
    """The fucntion apply projection from WGS84 to any custom projection of theater
    input:  coordinations: list of lists, first argument must be lan(x) and long(y)
            string: string of the projection
    oputput: list of list of the projected to BMS x,y"""

    # Define the source and target projections
    transformer = Transformer.from_crs("4326", string, always_xy=True)

    # Transform the point from WGS84 to the target projection
    projected_coordinations = []
    for coord in coordinations:
        try:
            # Ensure coordinates are float values
            x, y = float(coord[0]), float(coord[1])
            x_bms, y_bms = transformer.transform(x, y)
            projected_coordinations.append([x_bms, y_bms])
        except (ValueError, TypeError) as e:
            # Skip invalid coordinates and log them
            logging.warning(f"Skipping invalid coordinate {coord}: {str(e)}")
            continue
    return projected_coordinations


def Load_Geo_File(
    json_path, projection_string=None, floor_height=2.286
):
    # Create a logger for this function
    logger = logging.getLogger(__name__)

    # Create formatter for consistent log messages
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # meter2feet_google = 3.2808399
    meter2feet_BMS = 3.27998

    # Load the GeoJSON file
    geojson_file = json_path
    logger.info(f"Loading GeoJSON from: {json_path}")
    gdf = gpd.read_file(geojson_file)
    logger.info(f"GeoJSON loaded with {len(gdf)} features")
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
                
            building, special = get_field_value(row, ["building"], special)
            # Get building_levels and height without affecting the special flag
            building_levels = get_field_value(row, ["building:levels"])
            height = get_field_value(row, ["height"])
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
                    "building_levels": building_levels,
                    "height": height,
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
                    f"Structure #{index}, size: {round(side_bigger * meter2feet_BMS,3)} x {round(side_smaller * meter2feet_BMS,3)} x {round(height,3) if height else 'N/A'} fetched"
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

    # Iterate through the list to calculate center of features
    for feature in feature_list:
        try:
            # Fix Senerio when building_levels and height not defined therefore presented as None or nan
            none_height = get_height_value(feature["height"])
            none_level = get_height_value(feature["building_levels"])

            # assign heights appropriately
            if none_height and none_level:
                heights.append(Floor_height_feet)
            elif not none_height:
                # Convert to float to ensure numeric type
                height_value = float(feature["height"]) if isinstance(feature["height"], (str, int, float)) else 0
                heights.append(height_value * meter2feet_BMS)
            elif not none_level:
                # Convert to float to ensure numeric type
                level_value = float(feature["building_levels"]) if isinstance(feature["building_levels"], (str, int, float)) else 0
                heights.append(level_value * Floor_height_feet)
            else:
                # Fallback case to avoid data inconsistency
                heights.append(Floor_height_feet)
                
            # Sizes - ensure values are numeric
            sizes_list.append(float(feature["length"]) * float(feature["width"]))
        except Exception as e:
            logger.warning(f"Error processing feature heights or sizes for index {feature.get('index', 'unknown')}: {str(e)}")
            heights.append(Floor_height_feet)  # Use default height
            sizes_list.append(100.0)  # Use default size

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
