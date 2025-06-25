import xml.etree.ElementTree as ET
import os
import sqlite3
import numpy as np
import pandas as pd
import logging

# Set up logging - use standard pattern to inherit from main application
logger = logging.getLogger(__name__)


def parse_dat_file(Path, arr, backup_path=None):
    logger.info(f"Starting parse_dat_file with path: {Path}")
    logger.info(f"Backup path provided: {'Yes' if backup_path else 'No'}")
    
    Model_count = np.size(arr, 0)
    All_dimensions = np.zeros((Model_count, 6))
    
    logger.info(f"Parsing {Model_count} model dimension files")

    for model_num in range(0, Model_count):
        try:
            model_path = os.path.join(
                Path, "Models", str(int(arr[model_num])), "Parent.dat"
            )
            file = open(model_path, "r")
            logger.debug(f"Model number {model_num} has been fetched from path: {model_path}")
        except FileNotFoundError:
            # if Folder of the model is missing in "Models" folder, take from Backup path the needed models
            if backup_path is not None:
                model_path = os.path.join(
                    backup_path, "Models", str(int(arr[model_num])), "Parent.dat"
                )
                file = open(model_path, "r")
                logger.debug(f"Model number {model_num} from Backup CT has been fetched: {model_path}")
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
    logger.info(f"Starting extract_name_of_feature with path: {Path}")
    logger.info(f"Processing {np.size(EntityIdxData, 0)} entity indices")
    
    try:
        # Load the Feature Data XML
        feature_data_xml_path = os.path.join(Path, "Falcon4_FCD.xml")
        logger.debug(f"Loading Feature Data XML from: {feature_data_xml_path}")
        feature_tree = ET.parse(feature_data_xml_path)
        root = feature_tree.getroot()

        # Find the FCD elements
        fcd_elements = root.findall("FCD")
        num_elements = len(fcd_elements)
        logger.info(f"Found {num_elements} FCD elements in XML")

        # Amount of Features to find
        FCD_Amount = np.size(EntityIdxData, 0)
        # list of features name definition
        features_names = []
        
        for index in range(0, FCD_Amount):
            # Check if the index is valid
            if num_elements >= EntityIdxData[index]:
                element = fcd_elements[EntityIdxData[index]]  # Adjust index to 0-based
                # Extract and append the name of the element
                feature_name = element.find("Name").text
                features_names.append(feature_name)
                logger.debug(f"Extracted feature name: {feature_name} for index {EntityIdxData[index]}")
            else:
                logger.warning(f"Invalid EntityIdx {EntityIdxData[index]} - exceeds available FCD elements ({num_elements})")

        logger.info(f"Successfully extracted {len(features_names)} feature names")
        return features_names
        
    except ET.ParseError as e:
        logger.error(f"XML parsing error in extract_name_of_feature: {e}")
        raise
    except Exception as e:
        logger.error(f"Error in extract_name_of_feature: {e}")
        raise


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
    logger.info(f"Starting extract_class_data from XML: {xml_file_path}")
    
    try:
        class_value_to_keep = 2
        logger.debug(f"Filtering CT elements with class value: {class_value_to_keep}")

        tree = ET.parse(xml_file_path)
        root = tree.getroot()

        # Find all CT elements in the XML
        ct_elements = root.findall("./CT")
        initial_ct_count = len(ct_elements)
        logger.info(f"Found {initial_ct_count} CT elements in XML")

        # Iterate through the CT elements and remove those that don't have the specified class_value
        removed_count = 0
        for ct_element in ct_elements[:]:  # Use slice to avoid modification during iteration
            class_value = int(ct_element.find("Class").text)
            if class_value != class_value_to_keep:
                # Remove the element from the XML tree
                root.remove(ct_element)
                removed_count += 1

        logger.info(f"Removed {removed_count} CT elements with class value != {class_value_to_keep}")

        # Find all CT elements from filtered Root
        ct_elements = root.findall("./CT")
        ct_length = len(ct_elements)
        logger.info(f"Processing {ct_length} filtered CT elements")
        
        Data_Array = np.zeros((ct_length, 6), dtype=int)
        
        for index, ct_element in enumerate(ct_elements):
            try:
                # Extract the desired data from the CT element
                Data_Array[index, 0] = int(ct_element.find("GraphicsNormal").text)
                Data_Array[index, 1] = int(ct_element.find("Domain").text)
                Data_Array[index, 2] = int(ct_element.find("Class").text)
                Data_Array[index, 3] = int(ct_element.find("Type").text)
                Data_Array[index, 4] = int(ct_element.get("Num"))
                Data_Array[index, 5] = int(ct_element.find("EntityIdx").text)
                
                logger.debug(f"Processed CT element {index}: GraphicsNormal={Data_Array[index, 0]}, Domain={Data_Array[index, 1]}")
                
            except (ValueError, AttributeError) as e:
                logger.error(f"Error processing CT element at index {index}: {e}")
                raise

        logger.info(f"Successfully extracted data for {ct_length} CT elements")
        return Data_Array
        
    except ET.ParseError as e:
        logger.error(f"XML parsing error in extract_class_data: {e}")
        raise
    except Exception as e:
        logger.error(f"Error in extract_class_data: {e}")
        raise


def GenerateDB(class_table_xml_path, save_path, Korea_CT_XML_path=None):
    logger.info("=== Starting Database Generation ===")
    logger.info(f"Class table XML path: {class_table_xml_path}")
    logger.info(f"Save path: {save_path}")
    logger.info(f"Backup CT XML path: {Korea_CT_XML_path if Korea_CT_XML_path else 'None'}")
    
    try:
        # Set Paths
        # Remove the file name from the directory path
        Base_Path = os.path.dirname(class_table_xml_path)
        logger.debug(f"Base path determined: {Base_Path}")
        
        if Korea_CT_XML_path:
            backup_Path = os.path.dirname(Korea_CT_XML_path)
            logger.debug(f"Backup path determined: {backup_Path}")
            logger.info(f"Using backup CT path: {Korea_CT_XML_path}")

        # Extract data from CT XML file
        logger.info("Extracting data from CT XML file")
        data = extract_class_data(class_table_xml_path)
        logger.info(f"Extracted {len(data)} class data records")
        
        # Extract Dimensions from parents files
        if Korea_CT_XML_path:
            logger.info("Fetching model dimensions with backup CT")
            model_dimensions = parse_dat_file(Base_Path, data[:, 0], backup_Path)
        else:
            logger.info("Fetching model dimensions")
            model_dimensions = parse_dat_file(Base_Path, data[:, 0])

        # Extract features names
        logger.info("Extracting feature names")
        features_names = extract_name_of_feature(Base_Path, data[:, 5])

        # Find indices of empty feature names (" " and "_Empty FTR Position")
        empty_feature_indices = [
            i
            for i, name in enumerate(features_names)
            if name.strip() == "" or name.strip() == "_Empty FTR Position"
        ]
        logger.info(f"Found {len(empty_feature_indices)} empty feature names to remove")

        # Remove the empty feature names
        features_names = [
            name for i, name in enumerate(features_names) if i not in empty_feature_indices
        ]

        # Remove corresponding rows from the data array
        data = np.delete(data, empty_feature_indices, axis=0)
        # do the same sane for models dimenstions
        model_dimensions = np.delete(model_dimensions, empty_feature_indices, axis=0)
        logger.info(f"Cleaned data arrays - remaining records: {len(data)}")

        # Combine data and model_dimensions into a single array
        logger.debug("Combining class data and model dimensions")
        combined_data = np.hstack((data, model_dimensions))
        logger.info(f"Combined data shape: {combined_data.shape}")

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
        logger.debug("Creating Pandas DataFrame")
        df = pd.DataFrame(combined_data, columns=columns)

        # Insert the 'FeatureName' column at the appropriate position in the DataFrame
        df.insert(1, "FeatureName", features_names)
        logger.info(f"DataFrame created with {len(df)} rows and {len(df.columns)} columns")

        # Convert columns to appropriate data types
        logger.debug("Converting DataFrame columns to appropriate data types")
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
        logger.info(f"Preparing to save database to: {saveTo}")
        
        # Check if the directory exists
        dir_name = os.path.dirname(saveTo)
        if not os.path.exists(dir_name):
            # If the directory doesn't exist, create it
            logger.debug(f"Creating directory: {dir_name}")
            os.makedirs(dir_name)
        
        # Save data with SQL method
        logger.debug("Connecting to SQLite database")
        conn = sqlite3.connect(saveTo)
        try:
            df.to_sql("MyTable", conn, if_exists="replace", index=False)
            logger.info(f"Database saved successfully to {saveTo}")
        finally:
            conn.close()
            logger.debug("Database connection closed")
        
        logger.info("=== Database Generation Completed Successfully ===")
        return True
        
    except Exception as e:
        logger.error(f"Error in GenerateDB: {e}")
        import traceback
        logger.debug(f"Full traceback: {traceback.format_exc()}")
        return False
