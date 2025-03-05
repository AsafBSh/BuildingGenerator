import geopandas as gpd
import numpy as np
from Find_features import fitted_features
from pyproj import Transformer
import math as m


def get_field_value(row, field_names, special=None):
    """
    Try to get the value of the first non-null field from the list.
    if the field is not found, return False.
    find if the structure is detailed by checking the field value
    """
    for field in field_names:
        try:
            value = row[field]
            # If the value is a string, return it
            if isinstance(value, str):
                value = value.lower()
                # Check if special is a None, if not, check if the value is not in the list to determine if it is special
                if special is not None:
                    if special or value not in [
                        " ",
                        "roof",
                        "no",
                        "building",
                        "yes",
                        "0",
                    ]:
                        return value, True
                    else:
                        return value, False
                return value
            elif value is not None and not m.isnan(value):
                # Same check for non-string values (no lowercase conversion)
                if special is not None:
                    if special or str(value).lower() not in [
                        " ",
                        "roof",
                        "no",
                        "building",
                        "yes",
                        "0",
                    ]:
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
        x_bms, y_bms = transformer.transform(coord[0], coord[1])
        projected_coordinations.append([x_bms, y_bms])
    return projected_coordinations


def Load_Geo_File(
    json_path, debugger=False, projection_string=None, floor_height=2.286
):
    # meter2feet_google = 3.2808399
    meter2feet_BMS = 3.27998

    # Load the GeoJSON file
    geojson_file = json_path
    gdf = gpd.read_file(geojson_file)
    if debugger:
        print("********* Fetching GeoData *********")

    # Create a list to store the extracted information for each feature and center list of each feature
    feature_list = []
    center_list = []

    # count detailed features
    detailed_features = []
    special = False

    # Extract the important values along with all coordinates
    for index, row in gdf.iterrows():
        name = get_field_value(row, ["name:en", "name:int", "name"])
        if row["geometry"] is None:  # Handle error by data
            print(f"Null geometry in row {index}")
            continue
        try:  # Handle error by data
            geom_type = row["geometry"].geom_type
        except Exception as e:
            print(f"Error processing row {index}: {e}")
            continue
        building, special = get_field_value(row, ["building"], special)
        building_levels, special = get_field_value(row, ["building:levels"], special)
        height, special = get_field_value(row, ["height"], special)
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

        if special:
            detailed_features.append(1)
        else:
            detailed_features.append(0)
        special = False

        # Handle both "Polygon" and "MultiPolygon" geometries
        if geom_type in ["Polygon", "MultiPolygon"]:
            polygons = (
                [row["geometry"]] if geom_type == "Polygon" else row["geometry"].geoms
            )
            coordinates = []
            for polygon in polygons:
                exterior_coords = np.array(polygon.exterior.coords)
                # Check if projection_string is available if so, apply projection and continue as planned
                if projection_string and projection_string != "":
                    exterior_coords = projection(exterior_coords, projection_string)
                coordinates.append(exterior_coords)
            Real_center, rotation_angle, side_lengths = fitted_features(coordinates[0])
            # add to center list for later average center calculation
            center_list.append(Real_center)
        else:
            # Handle other geometry types as needed
            coordinates = None

        if coordinates is not None:
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
            if debugger:
                print(
                    f"Structure number #{index},sized {round(side_bigger * meter2feet_BMS,3)} x {round(side_smaller * meter2feet_BMS,3)} x {round(height,3)} fetched "
                )

    ### Old Way
    # # convert into falcon coordination = coor/1000, x,y = [0,1] -> xxx,yyy = [-1640,+1640]
    # center_list = np.round(np.array(center_list), decimals=10)*1640/(1000)    # Format, first column == real X, second column == real Y
    #
    # # Calc avarage center of the system
    # main_center = np.round(np.mean(center_list, axis=0), decimals=10)
    #
    # # Calculate the differences between points and center
    # center_related = center_list - main_center

    # Calc center of all features
    center_list = np.round(np.array(center_list), decimals=10) * meter2feet_BMS
    main_center = np.round(np.mean(center_list, axis=0), decimals=10)
    center_related = center_list - main_center

    # Set Center from feet to Km(1000m)
    main_center = main_center / (meter2feet_BMS)
    if projection_string and projection_string != "":
        main_center = main_center / 1000

    # Calculate radius and angle (polar space) for each point with falcon coordination
    Radius = np.sqrt(center_related[:, 0] ** 2 + center_related[:, 1] ** 2)
    angles = np.arctan2(center_related[:, 1], center_related[:, 0])

    # Convert angles of polar space to degrees
    angles_deg = np.degrees(angles)
    angles_deg = (angles_deg + 360) % 360

    sizes_list = []
    heights = []
    Floor_height_feet = floor_height * meter2feet_BMS  # default 7.5 feet == 2.286 meter

    # Iterate through the list to calculate center of features
    for feature in feature_list:
        # Fix Senerio when building_levels and height not defined therefore presented as None or nan
        none_height = get_height_value(feature["height"])
        none_level = get_height_value(feature["building_levels"])

        # assign heights appropriately
        if none_height and none_level:
            heights.append(Floor_height_feet)
        elif not none_height:
            heights.append(float(feature["height"]) * meter2feet_BMS)
        elif not none_level:
            heights.append(float(feature["building_levels"]) * Floor_height_feet)
        # Sizes
        sizes_list.append(feature["length"] * feature["width"])

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

    calculated_data = np.zeros((len(feature_list), 8))
    calculated_data[:, 0] = np.arange(len(feature_list)).reshape(
        -1
    )  # all Geo data arrange in dictionary
    calculated_data[:, 1] = np.array(heights).reshape(
        -1
    )  # Heights of all the buildings
    calculated_data[:, 2] = np.array(sizes_list).reshape(
        -1
    )  # Sizes of all the buildings

    calculated_data[:, 3] = Radius  # Radius compare to the avg center of each building
    calculated_data[:, 4] = angles_deg  # Angle to the avg center of each building
    calculated_data[:, 5:7] = center_related  # Location in 2 columns, (XXX,YYY)
    calculated_data[:, 7] = np.array(detailed_features).reshape(
        -1
    )  # Detailed structures

    calculated_data_with_Names = np.core.records.fromarrays(
        calculated_data.transpose(), names=column_names
    )
    if debugger:
        print("********* GeoData has been fetched successfully *********")
    return feature_list, calculated_data_with_Names, main_center
