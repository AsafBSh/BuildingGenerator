import xml.etree.ElementTree as ET
import os
import sqlite3
import numpy as np
import pandas as pd


def parse_dat_file(Path, arr, debugger=False, backup_path=None):
    Model_count = np.size(arr, 0)
    All_dimensions = np.zeros((Model_count, 6))

    for model_num in range(0, Model_count):
        try:
            model_path = os.path.join(
                Path, "Models", str(int(arr[model_num])), "Parent.dat"
            )
            file = open(model_path, "r")
            if debugger:
                print(f"model number {model_num} has been fetched")
        except FileNotFoundError:
            # if Folder of the model is missing in "Models" folder, take from Backup path the needed models
            if backup_path is not None:
                model_path = os.path.join(
                    backup_path, "Models", str(int(arr[model_num])), "Parent.dat"
                )
                file = open(model_path, "r")
                if debugger:
                    print(f"model number {model_num} from Backup CT has been fetched")
        # Get dimensions of each model number through  hit box parameters
        with file:
            for line in file:
                if line.startswith("Dimensions"):
                    dimensions = line.strip().split("=")[1].strip().split()
                    dimensions = [float(dimension) for dimension in dimensions]

        # Calculate the actual dimensions for wdth, len, hgt for feet units
        side_1 = dimensions[4] - dimensions[3]  # Y - (-Y)
        side_1_Offset = (dimensions[4] + dimensions[3]) / 2  # Find offset of Y axis
        side_2 = dimensions[2] - dimensions[1]  # X - (-X)
        side_2_Offset = (dimensions[2] + dimensions[1]) / 2  # Find offset of X axis
        height = abs(
            (0 - dimensions[5])
        )  # (Z - (-Z) note that some features might be inverted
        # * 0.3048 for feet

        # Assign Sizes to all dimensions array
        if side_1 >= side_2:
            All_dimensions[model_num, 0] = abs(
                side_2
            )  # width == X, abs is for fixing X if inverted
            All_dimensions[model_num, 1] = side_2_Offset  # width offset from center (X)
            All_dimensions[model_num, 2] = abs(
                side_1
            )  # length == Y , abs is for fixing Y if inverted
            All_dimensions[model_num, 3] = (
                side_1_Offset  # length offset from center (Y)
            )
            All_dimensions[model_num, 4] = height
            All_dimensions[model_num, 5] = 1  # length index position

        elif side_1 < side_2:
            All_dimensions[model_num, 0] = abs(
                side_1
            )  # width == Y,  abs is for fixing Y if inverted
            All_dimensions[model_num, 1] = side_1_Offset  # width offset from center (Y)
            All_dimensions[model_num, 2] = abs(
                side_2
            )  # length == X,  abs is for fixing X if inverted
            All_dimensions[model_num, 3] = (
                side_2_Offset  # length offset from center (X)
            )
            All_dimensions[model_num, 4] = height
            All_dimensions[model_num, 5] = 0  # length index position
        # Note, X and Y defined through the Editor Bonding Box window, its suppose to be switched
    return All_dimensions


def extract_name_of_feature(Path, EntityIdxData):
    # Load the Feature Data XML
    feature_data_xml_path = os.path.join(Path, "Falcon4_FCD.xml")
    feature_tree = ET.parse(feature_data_xml_path)
    root = feature_tree.getroot()

    # Find the FCD elements
    fcd_elements = root.findall("FCD")
    num_elements = len(fcd_elements)

    # Amount of Features to find
    FCD_Amount = np.size(EntityIdxData, 0)
    # list of features name definition
    features_names = []
    for index in range(0, FCD_Amount):
        # Check if the index is valid
        if num_elements >= EntityIdxData[index]:
            element = fcd_elements[EntityIdxData[index]]  # Adjust index to 0-based
            # Extract and append the name of the element
            features_names.append(element.find("Name").text)

    return features_names


# Helper function to extract class data from the Class Table XML (similar to the previous code snippet)
def extract_class_data(xml_file_path):
    """
    Extracts class data from the Class Table XML.

    Args:
        xml_file_path (str): Path to the Class Table XML file.

    Returns:
        tuple: Tuple containing the extracted domain, class value, and graphics normal number.
               Returns None if the data is not found or there is an XML parsing error.
    """
    class_value_to_keep = 2

    tree = ET.parse(xml_file_path)
    root = tree.getroot()

    # Find all CT elements in the XML
    ct_elements = root.findall("./CT")

    # Iterate through the CT elements and remove those that don't have the specified class_value
    for ct_element in ct_elements:
        class_value = int(ct_element.find("Class").text)
        if class_value != class_value_to_keep:
            # Remove the element from the XML tree
            root.remove(ct_element)

    # Find all CT elements from filtered Root
    ct_elements = root.findall("./CT")
    ct_length = len(ct_elements)
    Data_Array = np.zeros((ct_length, 6), dtype=int)
    for index, ct_element in enumerate(ct_elements):
        # Extract the desired data from the CT element
        Data_Array[index, 0] = int(ct_element.find("GraphicsNormal").text)
        Data_Array[index, 1] = int(ct_element.find("Domain").text)
        Data_Array[index, 2] = int(ct_element.find("Class").text)
        Data_Array[index, 3] = int(ct_element.find("Type").text)
        Data_Array[index, 4] = int(ct_element.get("Num"))
        Data_Array[index, 5] = int(ct_element.find("EntityIdx").text)
    return Data_Array


def GenerateDB(class_table_xml_path, save_path, debugger=False, Korea_CT_XML_path=None):
    # Set Paths
    # Remove the file name from the directory path
    Base_Path = os.path.dirname(class_table_xml_path)
    if Korea_CT_XML_path:
        backup_Path = os.path.dirname(Korea_CT_XML_path)

    # Extract data from CT XML file
    data = extract_class_data(class_table_xml_path)
    # Extract Dimensions from parents files
    if Korea_CT_XML_path:
        if debugger:
            print("********* Fetch data with Backup CT *********")
        model_dimensions = parse_dat_file(Base_Path, data[:, 0], debugger, backup_Path)
    else:
        if debugger:
            print("********* Fetch data *********")
        model_dimensions = parse_dat_file(Base_Path, data[:, 0], debugger)

    # Extract features names
    features_names = extract_name_of_feature(Base_Path, data[:, 5])

    # Find indices of empty feature names (" " and "_Empty FTR Position")
    empty_feature_indices = [
        i
        for i, name in enumerate(features_names)
        if name.strip() == "" or name.strip() == "_Empty FTR Position"
    ]

    # Remove the empty feature names
    features_names = [
        name for i, name in enumerate(features_names) if i not in empty_feature_indices
    ]

    # Remove corresponding rows from the data array
    data = np.delete(data, empty_feature_indices, axis=0)
    # do the same sane for models dimenstions
    model_dimensions = np.delete(model_dimensions, empty_feature_indices, axis=0)

    # Combine data and model_dimensions into a single array
    combined_data = np.hstack((data, model_dimensions))

    # Update the columns list to include the 'FeatureName' column
    columns = [
        "ModelNumber",
        "Domain",
        "Class",
        "Type",
        "CTNumber",
        "EntityIdx",
        "Width",
        "WidthOff",
        "Length",
        "LengthOff",
        "Height",
        "LengthIdx",
    ]

    # Create a Pandas DataFrame from the combined_data array
    df = pd.DataFrame(combined_data, columns=columns)

    # Insert the 'FeatureName' column at the appropriate position in the DataFrame
    df.insert(1, "FeatureName", features_names)

    # Convert columns to appropriate data types
    df["ModelNumber"] = df["ModelNumber"].astype(int)
    df["Domain"] = df["Domain"].astype(int)
    df["Class"] = df["Class"].astype(int)
    df["Type"] = df["Type"].astype(int)
    df["CTNumber"] = df["CTNumber"].astype(int)
    df["EntityIdx"] = df["EntityIdx"].astype(int)
    df["Width"] = df["Width"].astype(float)
    df["WidthOff"] = df["WidthOff"].astype(float)
    df["Length"] = df["Length"].astype(float)
    df["LengthOff"] = df["LengthOff"].astype(float)
    df["Height"] = df["Height"].astype(float)
    df["LengthIdx"] = df["LengthIdx"].astype(float)

    # Save the DataFrame to a SQLite database
    saveTo = os.path.join(save_path, "database.db")
    # Check if the directory exists
    dir_name = os.path.dirname(saveTo)
    if not os.path.exists(dir_name):
        # If the directory doesn't exist, create it
        os.makedirs(dir_name)
    # Save data with SQL method
    conn = sqlite3.connect(saveTo)
    df.to_sql("MyTable", conn, if_exists="replace", index=False)
    if debugger:
        print("********* database.db saved successfully *********")
    conn.close()
