import math
import numpy as np
import sqlite3
import pandas as pd
import matplotlib.pyplot as MatPlt
import re
from mpl_toolkits.mplot3d.art3d import Poly3DCollection


# Load the data from the database
def Load_Db(path, feature_name="All"):
    """Loads Classified DB based on demand
    *feature_name is string, and will have all the information in numbers and strings
    --if all data need to be extracted, place "All, or empty space
    --numbers will be classified as "types" and names would be matched by the actual name
    --if "ModelNum" is present, every number would be extracted from the model number"""

    conn = sqlite3.connect(path)
    # Get all items divided by comma
    Allitems = [item.strip() for item in feature_name.split(",")]

    # Adjust the query based on the feature type
    AllModels = {"", "\n", "All"}

    # convert to sets
    set_Allitems = set(Allitems)
    if set_Allitems.issubset(AllModels) and len(Allitems) == 1:
        query = "SELECT * FROM MyTable"

    elif "ModelNum" in Allitems:
        # get only the numbers inside the
        numbers = [number.strip() for number in Allitems if number.isdigit()]
        # Construct the query to match any of the words in Allitems
        number_conditions = " OR ".join(
            [f"ModelNumber = {number}" for number in numbers]
        )
        # Combine the conditions
        query = f"SELECT * FROM MyTable WHERE {number_conditions}"

    else:
        # Separate words and numbers
        words = [item for item in Allitems if not item.isdigit()]
        numbers = [item for item in Allitems if item.isdigit()]

        # Construct the query to match any of the words in FeatureName and any of the numbers in Type
        word_conditions = " OR ".join(
            [f"FeatureName LIKE '%{word}%'" for word in words]
        )
        number_conditions = " OR ".join([f"Type = {number}" for number in numbers])

        # Combine the conditions
        if word_conditions and number_conditions:
            query = f"SELECT * FROM MyTable WHERE ({word_conditions}) OR ({number_conditions})"
        elif word_conditions:
            query = f"SELECT * FROM MyTable WHERE {word_conditions}"
        elif number_conditions:
            query = f"SELECT * FROM MyTable WHERE {number_conditions}"

    data_array = pd.read_sql_query(query, conn)

    conn.close()

    return data_array


def Show_Selected_Features(buildings, Calc_data):
    # Create a figure and axis
    # fig, ax = plt.subplots()

    # Loop through each feature
    for i in range(len(buildings)):
        feature = buildings.iloc[i]
        length = feature["length"]
        width = feature["width"]
        rotation = feature["rotation"]

        # Extract radius and angle from calc_features
        radius = Calc_data[i, 3]
        angle = Calc_data[i, 4]

        x_distance = radius * math.cos(math.radians(angle))
        y_distance = radius * math.sin(math.radians(angle))

        # Calculate the corner points of the rectangle
        corner_points = np.array(
            [
                [-width / 2, -length / 2],
                [width / 2, -length / 2],
                [width / 2, length / 2],
                [-width / 2, length / 2],
            ]
        )

        # Apply rotation to the corner points
        rotation_matrix = np.array(
            [
                [np.cos(np.radians(rotation)), -np.sin(np.radians(rotation))],
                [np.sin(np.radians(rotation)), np.cos(np.radians(rotation))],
            ]
        )
        rotated_corner_points = np.dot(corner_points, rotation_matrix.T)

        # Translate the corner points to the center
        translated_corner_points = rotated_corner_points + [y_distance, x_distance]

        # Plot the points
        MatPlt.plot(
            translated_corner_points[:, 1], translated_corner_points[:, 0], label=None
        )

        # Connect the last point to the first point to close the shape
        MatPlt.plot(
            [translated_corner_points[-1, 1], translated_corner_points[0, 1]],
            [translated_corner_points[-1, 0], translated_corner_points[0, 0]],
        )

    # Set the title for the plot
    MatPlt.title("Shape from Points")


def Show_Selected_Features_2D(
    plot_option,
    buildings=None,
    Calc_data=None,
    feature_entries=None,
    models_FrameData=None,
):
    # Initialize an empty list to hold the axes
    axes = []

    if plot_option in ["JSON_BondingBox", "Both"]:
        # Plot the 'selected_buildings'
        fig, ax = MatPlt.subplots(figsize=(6, 6))  # Create a figure with one subplot
        axes.append(ax)
        for i in range(len(buildings)):
            feature = buildings.iloc[i]
            length = feature["length"]
            width = feature["width"]
            rotation = (feature["rotation"] + 90) % 360

            # # Extract radius and angle from calc_features
            x_distance = Calc_data[i, 5]
            y_distance = Calc_data[i, 6]

            # Calculate the corner points of the rectangle
            corner_points = np.array(
                [
                    [-width / 2, -length / 2],
                    [width / 2, -length / 2],
                    [width / 2, length / 2],
                    [-width / 2, length / 2],
                ]
            )

            # Apply rotation to the corner points
            rotation_matrix = np.array(
                [
                    [np.cos(np.radians(rotation)), -np.sin(np.radians(rotation))],
                    [np.sin(np.radians(rotation)), np.cos(np.radians(rotation))],
                ]
            )
            rotated_corner_points = np.dot(corner_points, rotation_matrix.T)

            # Translate the corner points to the center
            translated_corner_points = rotated_corner_points + [y_distance, x_distance]

            # Append the first point to the end to close the shape
            translated_corner_points = np.concatenate(
                [translated_corner_points, translated_corner_points[0:1]]
            )

            # Plot the points for the first subplot
            axes[0].plot(
                translated_corner_points[:, 1], translated_corner_points[:, 0], "b-"
            )

        axes[0].set_title("Selected Buildings from JSON")

        # Plot the 'feature_entries'
    if plot_option in ["BMS_Fitting", "Both"]:
        fig, ax = MatPlt.subplots(figsize=(6, 6))  # Create a figure with one subplot
        axes.append(ax)
        for i, entry in enumerate(feature_entries):
            entry_parts = entry.split()
            ct_number = int(
                re.search(r"\d+", entry_parts[0]).group()
            )  # Extract digits from the string and convert to integer

            # Fetch the row from GeoFeatures using CTNumber
            model_data = models_FrameData[
                models_FrameData["CTNumber"].astype(str).str.contains(str(ct_number))
            ]
            if not model_data.empty:
                model_width, model_length = (
                    model_data.iloc[0]["Width"],
                    model_data.iloc[0]["Length"],
                )

                # Extract other parameters from the entry
                y_distance, x_distance, z_height, rotation = map(
                    float, entry_parts[1:5]
                )
                # Note!! returning the Y and X coordinations to its proper place after editor switching

            # Calculate the corner points of the rectangle
            corner_points = np.array(
                [
                    [-model_width / 2, -model_length / 2],
                    [model_width / 2, -model_length / 2],
                    [model_width / 2, model_length / 2],
                    [-model_width / 2, model_length / 2],
                ]
            )

            # Apply rotation to the corner points
            rotation_matrix = np.array(
                [
                    [np.cos(np.radians(rotation)), -np.sin(np.radians(rotation))],
                    [np.sin(np.radians(rotation)), np.cos(np.radians(rotation))],
                ]
            )
            rotated_corner_points = np.dot(corner_points, rotation_matrix.T)

            # Translate the corner points to the center
            translated_corner_points = rotated_corner_points + [y_distance, x_distance]
            # Append the first point to the end to close the shape
            translated_corner_points = np.concatenate(
                [translated_corner_points, translated_corner_points[0:1]]
            )

            # Plot the points for the second subplot
            axes[-1].plot(
                translated_corner_points[:, 1], translated_corner_points[:, 0], "r-"
            )

        axes[-1].set_title("Feature Entries generated from BMS")

    for ax in axes:
        ax.set_xlabel("X [feet]")
        ax.set_ylabel("Y [feet]")
        ax.axis("equal")
        ax.grid(True)

    MatPlt.show()


def Show_Selected_Features_3D(
    plot_option,
    buildings=None,
    Calc_data=None,
    feature_entries=None,
    models_FrameData=None,
):
    # Initialize an empty list to hold the axes
    axes = []

    # Initialize variables to stor the min and max values for each axis
    x_min, x_max, y_min, y_max, z_min, z_max = (
        float("inf"),
        float("-inf"),
        float("inf"),
        float("-inf"),
        float("inf"),
        float("-inf"),
    )

    if plot_option in ["JSON_BondingBox", "Both"]:
        fig = MatPlt.figure(figsize=(6, 6))
        ax = fig.add_subplot(111, projection="3d")  # Create a 3D subplot
        axes.append(ax)

        # Plot the 'selected_buildings'
        for i in range(len(buildings)):
            feature = buildings.iloc[i]
            length = feature["length"]
            width = feature["width"]
            height = feature["height"]
            rotation = (feature["rotation"] + 90) % 360

            # Extract radius and angle from calc_features
            x_distance = Calc_data[i, 5]
            y_distance = Calc_data[i, 6]

            # Calculate the corner points of the rectangle
            corner_points = np.array(
                [
                    [-width / 2, -length / 2, 0],
                    [width / 2, -length / 2, 0],
                    [width / 2, length / 2, 0],
                    [-width / 2, length / 2, 0],
                    [-width / 2, -length / 2, height],
                    [width / 2, -length / 2, height],
                    [width / 2, length / 2, height],
                    [-width / 2, length / 2, height],
                ]
            )

            # Apply rotation to the corner points
            rotation_matrix = np.array(
                [
                    [np.cos(np.radians(rotation)), -np.sin(np.radians(rotation)), 0],
                    [np.sin(np.radians(rotation)), np.cos(np.radians(rotation)), 0],
                    [0, 0, 1],
                ]
            )
            rotated_corner_points = np.dot(corner_points, rotation_matrix.T)

            # Translate the corner points to the center
            translated_corner_points = rotated_corner_points + [
                y_distance,
                x_distance,
                0,
            ]

            # Append the first point to the end to close the shape
            translated_corner_points = np.concatenate(
                [translated_corner_points, translated_corner_points[0:1]]
            )

            # Update the min and max values for each axis
            x_min = min(x_min, np.min(translated_corner_points[:, 0]))
            x_max = max(x_max, np.max(translated_corner_points[:, 0]))
            y_min = min(y_min, np.min(translated_corner_points[:, 1]))
            y_max = max(y_max, np.max(translated_corner_points[:, 1]))
            z_min = min(z_min, np.min(translated_corner_points[:, 2]))
            z_max = max(z_max, np.max(translated_corner_points[:, 2]))

            # Create a 3D polygon and add it to the plot
            faces = np.array(
                [
                    [translated_corner_points[i] for i in [0, 1, 5, 4]],
                    [translated_corner_points[i] for i in [1, 2, 6, 5]],
                    [translated_corner_points[i] for i in [2, 3, 7, 6]],
                    [translated_corner_points[i] for i in [3, 0, 4, 7]],
                    [translated_corner_points[i] for i in [0, 1, 2, 3]],
                    [translated_corner_points[i] for i in [0, 1, 5, 4]],
                    [translated_corner_points[i] for i in [4, 5, 6, 7]],
                ]
            )

            for face in faces:
                z = np.array([face[:, 2]])
                verts = [list(zip(face[:, 0], face[:, 1], z[0]))]
            ax.add_collection3d(
                Poly3DCollection(
                    verts, facecolors="blue", linewidths=1, edgecolors="r", alpha=0.25
                )
            )

        axes[0].set_title("3D Selected Buildings from JSON")

    if plot_option in ["BMS_Fitting", "Both"]:
        fig = MatPlt.figure(figsize=(6, 6))
        ax = fig.add_subplot(111, projection="3d")  # Create a 3D subplot
        axes.append(ax)

        # Plot the 'feature_entries'
        for i, entry in enumerate(feature_entries):
            entry_parts = entry.split()
            ct_number = int(
                re.search(r"\d+", entry_parts[0]).group()
            )  # Extract digits from the string and convert to integer

            # Fetch the row from GeoFeatures using CTNumber
            model_data = models_FrameData[
                models_FrameData["CTNumber"].astype(str).str.contains(str(ct_number))
            ]
            if not model_data.empty:
                model_width, model_length, model_height = (
                    model_data.iloc[0]["Width"],
                    model_data.iloc[0]["Length"],
                    model_data.iloc[0]["Height"],
                )

                # Extract other parameters from the entry
                y_distance, x_distance, z_height, rotation = map(
                    float, entry_parts[1:5]
                )
                # Note!! returning the Y and X coordinations to its proper place after editor switching

            # Calculate the corner points of the rectangle
            corner_points = np.array(
                [
                    [-model_width / 2, -model_length / 2, 0],
                    [model_width / 2, -model_length / 2, 0],
                    [model_width / 2, model_length / 2, 0],
                    [-model_width / 2, model_length / 2, 0],
                    [-model_width / 2, -model_length / 2, model_height],
                    [model_width / 2, -model_length / 2, model_height],
                    [model_width / 2, model_length / 2, model_height],
                    [-model_width / 2, model_length / 2, model_height],
                ]
            )

            # Apply rotation to the corner points
            rotation_matrix = np.array(
                [
                    [np.cos(np.radians(rotation)), -np.sin(np.radians(rotation)), 0],
                    [np.sin(np.radians(rotation)), np.cos(np.radians(rotation)), 0],
                    [0, 0, 1],
                ]
            )
            rotated_corner_points = np.dot(corner_points, rotation_matrix.T)

            # Translate the corner points to the center
            translated_corner_points = rotated_corner_points + [
                y_distance,
                x_distance,
                0,
            ]

            # Append the first point to the end to close the shape
            translated_corner_points = np.concatenate(
                [translated_corner_points, translated_corner_points[0:1]]
            )

            # Update the min and max values for each axis
            x_min = min(x_min, np.min(translated_corner_points[:, 0]))
            x_max = max(x_max, np.max(translated_corner_points[:, 0]))
            y_min = min(y_min, np.min(translated_corner_points[:, 1]))
            y_max = max(y_max, np.max(translated_corner_points[:, 1]))
            z_max = max(z_max, np.max(translated_corner_points[:, 2]))

            # Create a 3D polygon and add it to the plot
            faces = np.array(
                [
                    [translated_corner_points[i] for i in [0, 1, 5, 4]],
                    [translated_corner_points[i] for i in [1, 2, 6, 5]],
                    [translated_corner_points[i] for i in [2, 3, 7, 6]],
                    [translated_corner_points[i] for i in [3, 0, 4, 7]],
                    [translated_corner_points[i] for i in [0, 1, 2, 3]],
                    [translated_corner_points[i] for i in [0, 1, 5, 4]],
                    [translated_corner_points[i] for i in [4, 5, 6, 7]],
                ]
            )

            for face in faces:
                z = np.array([face[:, 2]])
                verts = [list(zip(face[:, 0], face[:, 1], z[0]))]
                ax.add_collection3d(
                    Poly3DCollection(
                        verts,
                        facecolors="blue",
                        linewidths=1,
                        edgecolors="b",
                        alpha=0.25,
                    )
                )

        axes[-1].set_title("3D Feature Entries generated from BMS")

    for ax in axes:
        ax.set_xlabel("X [feet]")
        ax.set_ylabel("Y [feet]")
        ax.set_zlabel("Z [feet]")
        ax.grid(True)  # Add a grid to the plot

        # Set the limits of the axes
        ax.set_xlim([x_min * 1.1, x_max * 1.1])
        ax.set_ylim([y_min * 1.1, y_max * 1.1])
        ax.set_zlim([0, z_max * 2])

    MatPlt.show()


def filter_structures(
    Geo_Data, Raw_Geo_Data, Num_Of_Structures, selection_option="Total Size"
):
    """
    Selects a subset of structures from a given dataframe based on a probabilistic algorithm.

    Parameters:
    - Geo_Data (pandas.DataFrame): Input dataframe containing information about Geodata.
    - Raw_Geo_Data(pandas.DataFrame): Input dataframe containing information about Raw Geodata.
    - Num_Of_Structures: Amount of structures to select
    - selection_option (str): Selection criteria for the structures. Options include 'size', 'closer', 'both', 'random'.

    Selection Options:
    - 'Height': Probability is increased based on the dot's size (Only Height).
    - 'Area': Probability is increased based on the dot's size (Only Area).
    - 'Total Size': Probability is increased based on the dot's size (height and total size).
    - 'Centerness': Probability is increased for structures closer to the center of the cluster.
    - 'Mix': Probability is influenced by both size and distance.
    - 'Random': structures are randomly selected without considering probabilities
    """

    # Extract relevant columns from the dataframe
    data = Geo_Data[
        ["Surface Size (feet^2)", "Height (feet)", "XXX Cords", "YYY Cords"]
    ].values
    # Calculate the selection criteria
    if selection_option == "Height":
        # Sort based on height
        selection_criteria = Geo_Data["Height (feet)"]
    elif selection_option == "Area":
        # Sort based on area
        selection_criteria = Geo_Data["Surface Size (feet^2)"]
    elif selection_option == "Total Size":
        # Sort based on height and total size
        selection_criteria = (
            Geo_Data["Height (feet)"] * Geo_Data["Surface Size (feet^2)"]
        )

    elif selection_option == "Centerness":
        # Sort based on distance from the center of the cluster
        mean = np.mean(data[:, 2:], axis=0)
        distances = np.linalg.norm(data[:, 2:] - mean, axis=1)
        selection_criteria = 1 / (1 + distances)

    elif selection_option == "Mix":
        # Sort based on both size and distance
        mean = np.mean(data[:, 2:], axis=0)
        distances = np.linalg.norm(data[:, 2:] - mean, axis=1)
        selection_criteria = (1 / (1 + distances)) * (
            Geo_Data["Height (feet)"] * Geo_Data["Surface Size (feet^2)"]
        )

    elif selection_option == "Random":
        # Randomly shuffle the indices
        selection_criteria = np.random.rand(len(Geo_Data))

    # Sort the data based on the selection criteria
    sorted_indices = np.argsort(selection_criteria)

    # Select the top amount of structures with the highest selection criteria
    Num_Of_Structures = min(
        Num_Of_Structures, len(Geo_Data), 256
    )  # Limit to dataframe size
    selected_indices = sorted_indices[-Num_Of_Structures:]

    # Return a new dataframe with the selected structures
    return Raw_Geo_Data.iloc[selected_indices], Geo_Data.iloc[selected_indices]


def Decision_Algo(GeoFeature, GeoFeatureData, Geo_Idx, selected_BMSModels, State="3D"):
    """Iterates for every BMS model and find the must appropriate feature based on the critiria"""
    # Define starting points
    corrent_model_idx = 0
    closest_distance = 10**9

    if State == "3D":
        # Include Height in the distance calculation
        for model in range(0, len(selected_BMSModels)):
            SingleStructure_FrameData = GeoFeature.iloc[Geo_Idx]  # FrameData Type
            SingleStructure_Height = GeoFeatureData[Geo_Idx, 1]  # Numpy Array Type

            # Distance value consider abs of substraction of model and building specific sizem then adding them into solid one value
            width_dist = abs(
                SingleStructure_FrameData["width"]
                - selected_BMSModels.iloc[model]["Width"]
            )
            length_dist = abs(
                SingleStructure_FrameData["length"]
                - selected_BMSModels.iloc[model]["Length"]
            )
            height_dist = abs(
                SingleStructure_Height - selected_BMSModels.iloc[model]["Height"]
            )
            calc_dist = math.sqrt(width_dist**2 + length_dist**2 + height_dist**2)
            if calc_dist < closest_distance:
                corrent_model_idx = model
                closest_distance = calc_dist

    elif State == "2D":
        # Iterate through Models
        # Don't include Height in the distance calculation
        for model in range(0, len(selected_BMSModels)):
            SingleStructure_FrameData = GeoFeature.iloc[Geo_Idx]
            # Distance value consider abs of substraction of model and building specific sizem then adding them into solid one value
            width_dist = abs(
                SingleStructure_FrameData["width"]
                - selected_BMSModels.iloc[model]["Width"]
            )
            length_dist = abs(
                SingleStructure_FrameData["length"]
                - selected_BMSModels.iloc[model]["Length"]
            )
            calc_dist = math.sqrt(width_dist**2 + length_dist**2)
            if calc_dist < closest_distance:
                corrent_model_idx = model
                closest_distance = calc_dist

    return corrent_model_idx, closest_distance


def Rotation_Definer(Angle, BMS_Length_idx):
    """Through the knowledge of the longest side of the model, assign fixed angle for rotation
    Idx == 0 ( X is the longest)/ 1 (Y is the longest)"""
    if BMS_Length_idx == 1:
        Angle_y_algned = (Angle + 90) % 360
        return Angle_y_algned
    elif BMS_Length_idx == 0:
        return Angle


def Assign_features_randomly(num_features, radius, DB_path, DB_restrictions):
    # Load the database file containing the features data (mydatabase.db)
    AllBMSModels = Load_Db(DB_path, DB_restrictions)  # Options ModelNum, Name, Type

    if len(AllBMSModels) == 0:
        return TypeError
    # Generate random indices to select 'apartment' features
    np.random.seed(num_features)  # To ensure reproducibility
    selected_indices = np.random.choice(len(AllBMSModels), num_features, replace=True)

    # Get the CT numbers and feature names for the selected indices
    selected_data = AllBMSModels.iloc[selected_indices]

    # Generate random coordinates within the specified radius
    angles = np.random.uniform(0, 2 * np.pi, num_features)
    distances = np.random.uniform(0, radius, num_features)
    x_coordinates = distances * np.cos(angles)
    y_coordinates = distances * np.sin(angles)

    return selected_data, x_coordinates, y_coordinates


def Save_random_features(
    SaveType,
    num_features,
    selected_data,
    x_coordinates,
    y_coordinates,
    output_file_path,
    BuildingGeneratorVer,
    Presence_f,
    Values_f,
    Presence_i,
    Values_i,
    CT_Num=None,
    Obj_Num=None,
):
    if SaveType == "Editor":
        # Format the FeatureEntry data for each 'apartment' feature
        feature_entries = []
        for i, (x, y) in enumerate(zip(x_coordinates, y_coordinates)):
            ct_number = selected_data.iloc[i]["CTNumber"]
            feature_name = selected_data.iloc[i]["FeatureName"]
            x_distance = x
            y_distance = y
            z_height = (
                0  # You can set the height as needed, here we assume a height of 0 feet
            )
            rotation = np.random.uniform(0, 360)
            # Apply random value if initial value is available
            if Values_i:
                value = np.random.uniform(Values_i, Values_f)
            else:
                value = Values_f
            point_link = -1
            # Apply random presence if initial presence is available
            if Presence_i:
                presence = np.random.uniform(Presence_i, Presence_f)
            else:
                presence = Presence_f

            chance_of_presence = (
                f"{int(presence)}#"  # We keep it as a string to include the '#' character
            )
            count_of_features = f"{i})"  # 0-indexed count of features
            formatted_entry = (
                f"FeatureEntry={ct_number} {x_distance:.4f} {y_distance:.4f} {z_height:.4f} {rotation:.4f} {int(value):04d} 0000 "
                f"{point_link} {chance_of_presence} {count_of_features} {feature_name}"
            )
            feature_entries.append(formatted_entry)

        # Write the formatted data to a file in the Falcon BMS format
        with open(output_file_path, "w") as output_file:
            output_file.write(
                f"# BMS-BuildingGenerator (v{BuildingGeneratorVer} alpha) for FalconEditor - Objective Data\n\n"
            )
            output_file.write("Version=6\n\n")
            output_file.write(
                f"# FeatureEntries {num_features}\n\n"
            )  # set to amount of features
            for entry in feature_entries:
                output_file.write(entry + "\n")
            output_file.write("\n# Point Headers 0\n")

    # if SaveType == "BMS":


def Assign_features_accuratly(
    num_features,
    DB_path,
    DB_restrictions,
    fillter_option,
    GeoFeatures,
    CalcData_GeoFeatures,
):
    """the Function fillter features according to critirias :
    input::
    num_features = number of features to generate
    DB_path = the path to the DB which the software have been processed
    DB_restriction_type = 'ModelNum'\'Type'\'Name
    DB_restrictions = the restrictions in a string
    fillter_option = Will select the method of filltering the real buildings (default = based on centerness and height)
    GeoFeatures, CalcData_GeoFeatures = Geo data from Load_DB function
    output::
    AllBMSModels - filltered BMS models through the restrictions
    Selected_GeoFeatures - filltered Geo structures
    Selected_CalcData_GeoFeatures - corrolated data of Geo structures to Selected_GeoFeatures
    """

    # Load the database file containing the features data (mydatabase.db)
    AllBMSModels = Load_Db(DB_path, DB_restrictions)  # Options ModelNum, Name, Type

    if len(AllBMSModels) == 0:
        return TypeError

    # Apply Structure selection algorithm through preferences -                     "size", "closer", "both", "random"
    Selected_GeoFeatures, Selected_CalcData_GeoFeatures = filter_structures(
        pd.DataFrame(CalcData_GeoFeatures),
        pd.DataFrame(GeoFeatures),
        num_features,
        fillter_option,
    )
    Selected_CalcData_GeoFeatures = np.array(Selected_CalcData_GeoFeatures)

    return AllBMSModels, Selected_GeoFeatures, Selected_CalcData_GeoFeatures


def Save_accurate_features(
    SaveType,
    num_features,
    Selected_GeoFeatures,
    Selected_CalcData_GeoFeatures,
    Db_path,
    AllBMSModels,
    selection_option,
    SavePath,
    AOI_center,
    Presence_f,
    Values_f,
    Presence_i,
    Values_i,
    auto_features_detection,
    CT_Num=None,
    Obj_Num=None,
):
    if SaveType == "Editor":
        BMSver = 38
        BuildingGeneratorVer = "0.9b"
        feature_entries = []
        for select in range(0, len(Selected_GeoFeatures)):
            if auto_features_detection:
                Auto_BMSModels = Auto_Selected(
                    Db_path, Selected_GeoFeatures.iloc[select]
                )
                if Auto_BMSModels is not None:
                    AllBMSModels = Auto_BMSModels

            ## Get the most suited BMS model to the selected Geo Structure
            corrent_model_idx, closest_distance = Decision_Algo(
                Selected_GeoFeatures,
                Selected_CalcData_GeoFeatures,
                select,
                AllBMSModels,
                selection_option,
            )

            # Get CT and name of the selected model
            ct_number = AllBMSModels.iloc[corrent_model_idx]["CTNumber"]
            feature_name = AllBMSModels.iloc[corrent_model_idx]["FeatureName"]

            ## For Euclidian coordination
            x_distance = Selected_CalcData_GeoFeatures[select, 5]  # XXX in feet
            y_distance = Selected_CalcData_GeoFeatures[select, 6]  # YYY in feet

            z_height = (
                0  # You can set the height as needed, here we assume a height of 0 feet
            )
            rotation = Rotation_Definer(
                Selected_GeoFeatures.iloc[select]["rotation"],
                AllBMSModels.iloc[corrent_model_idx]["LengthIdx"],
            )

            if Values_i:
                value = np.random.uniform(Values_i, Values_f)
            else:
                value = Values_f
            # Apply random presence if initial presence is available
            if Presence_i:
                presence = np.random.uniform(Presence_i, Presence_f)
            else:
                presence = Presence_f
            chance_of_presence = (
                f"{int(presence)}#"  # We keep it as a string to include the '#' character
            )

            point_link = -1
            count_of_features = f"{select})"  # 0-indexed count of features
            # Note! Editor switched the x and y coordinates
            formatted_entry = (
                f"FeatureEntry={ct_number} {y_distance:.4f} {x_distance:.4f} {z_height:.4f} {rotation:.4f} {int(value):04d} 0000 "
                f"{point_link} {chance_of_presence} {count_of_features} {feature_name}"
            )
            feature_entries.append(formatted_entry)

        # Write the formatted data to a file in the Falcon BMS format
        with open(SavePath, "w") as output_file:
            output_file.write(
                f"# BMS-BuildingGenerator (v{BuildingGeneratorVer} alpha) for FalconEditor - Objective Data\n\n"
            )
            output_file.write(
                f"# Objective original location in Falcon World (Falcon BMS 4.{BMSver} with New Terrain)\n# ObjX: {AOI_center[0]} \n# ObjY: {AOI_center[1]}\n\n"
            )
            output_file.write("Version=6\n\n")
            output_file.write(f"# FeatureEntries {num_features}\n\n")

            for entry in feature_entries:
                output_file.write(entry + "\n")
            output_file.write("\n# Point Headers 0\n")

        return feature_entries


def Auto_Selected(Db_path, Selected_GeoFeature):
    """The function detects possible keys in the GeoFeature and loading a proper Models from the Database
    for better type fitting"""

    fillters = []

    stadium = ["stadium", "ice_rink", "sports_centre", "sports_hall"]
    if (
        Selected_GeoFeature["leisure"]
        and Selected_GeoFeature["leisure"].lower() in stadium
        or Selected_GeoFeature["sport"]
    ):
        fillters.extend(["66", "sport"])

    if Selected_GeoFeature["religion"]:
        fillters.extend(["7", "40"])

    if (
        Selected_GeoFeature["building"]
        and Selected_GeoFeature["building"].lower() == "hangar"
    ):
        fillters.extend(["39", "45"])

    if Selected_GeoFeature["barrier"]:
        if Selected_GeoFeature["barrier"].lower() == "border_control":
            fillters.extend(["55"])
        if Selected_GeoFeature["barrier"].lower() == "fence":
            fillters.extend(["49"])

    if Selected_GeoFeature["man_made"]:
        antennas = ["communications_tower", "antenna", "satellite_dish", "telescope"]
        fire_poles = ["flare", "chimney"]
        if Selected_GeoFeature["man_made"].lower() in antennas:
            fillters.extend(["29", "43", "antenna", "33", "28"])
        if Selected_GeoFeature["man_made"].lower() == "tower":
            fillters.extend(["61", "tower"])
        if Selected_GeoFeature["man_made"].lower() == "beacon":
            fillters.extend(["beacon"])
        if Selected_GeoFeature["man_made"].lower() == "cooling_tower":
            fillters.extend(["53"])
        if Selected_GeoFeature["man_made"].lower() in fire_poles:
            fillters.extend(["61", "51"])

    if Selected_GeoFeature["power"]:
        Power = [
            "compensator",
            "converter",
            "plant",
            "substation",
            "transformer",
            "busbar",
        ]
        electric_tower = ["tower", "terminal", "connection"]
        if Selected_GeoFeature["power"].lower() in Power:
            fillters.extend(["23", "converter", "32"])
        if Selected_GeoFeature["power"].lower() in electric_tower:
            fillters.extend(["20"])

    factory = ["pipeline", "pump", "pumping_station", "works"]
    fuel_storage = ["gasometer", "storage_tank"]
    if (
        Selected_GeoFeature["man_made"]
        and Selected_GeoFeature["man_made"].lower() in factory
        or Selected_GeoFeature["building"]
        and Selected_GeoFeature["building"].lower() == "industrial"
    ):
        fillters.extend(["32", "53", "60", "56", "23", "6"])
    if (
        Selected_GeoFeature["building"]
        and Selected_GeoFeature["building"].lower() in fuel_storage
        or Selected_GeoFeature["man_made"]
        and Selected_GeoFeature["man_made"].lower() in fuel_storage
    ):
        fillters.extend(["48", "10"])
    if (
        Selected_GeoFeature["building"]
        and Selected_GeoFeature["building"].lower() == "silo"
        or Selected_GeoFeature["man_made"]
        and Selected_GeoFeature["man_made"].lower() == "silo"
    ):
        fillters.extend(["silo"])
    if (
        Selected_GeoFeature["building"]
        and Selected_GeoFeature["building"].lower() == "water_tower"
        or Selected_GeoFeature["man_made"]
        and Selected_GeoFeature["man_made"].lower() == "water_tower"
    ):
        fillters.extend(["37"])

    bridge_cap = ["bridge", "bridges"]
    if (
        Selected_GeoFeature["building"]
        and Selected_GeoFeature["building"].lower() in bridge_cap
        or Selected_GeoFeature["man_made"]
        and Selected_GeoFeature["man_made"].lower() in bridge_cap
        or Selected_GeoFeature["bridge"]
    ):
        fillters.extend(["16"])

    if (
        Selected_GeoFeature["building"]
        and Selected_GeoFeature["building"].lower() == "hospital"
        or Selected_GeoFeature["amenity"]
        and Selected_GeoFeature["amenity"].lower() == "hospital"
    ):
        fillters.extend(["62"])

    if (
        Selected_GeoFeature["military"]
        or Selected_GeoFeature["building"]
        and Selected_GeoFeature["building"].lower() == "bunker"
    ):
        fillters.extend(["4"])

    barracks = ["barrack", "barracks"]
    if (
        Selected_GeoFeature["building"]
        and Selected_GeoFeature["building"].lower() in barracks
        or Selected_GeoFeature["military"]
    ):
        fillters.extend(["12", "35", "10"])

    # convert list into string
    filters_str = ", ".join(fillters)
    # Get database through new fillters, if fillters are not defined then
    if filters_str != "":
        Accurate_filltered_BMSmodels = Load_Db(Db_path, filters_str)
        return Accurate_filltered_BMSmodels
    else:
        return None
