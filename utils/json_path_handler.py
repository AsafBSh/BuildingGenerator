import os
import json
import gzip
import logging
from pathlib import Path
from typing import Any, Dict, Optional, Union

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("json_path_handler")

# Base directory for all JSON files
DATA_COMPONENTS_DIR = "data_components"

# Constants for JSON filenames used throughout the project
class JsonFiles:
    # Template files
    OBJECTIVE_TEMPLATES = "objective_templates.json"
    CT_TEMPLATES = "ct_templates.json"
    COMPREHENSIVE_CT_TEMPLATES = "comprehensive_ct_templates.json"
    
    # Cache files
    OBJECTIVE_CACHE = "objective_cache.json"
    
    # Settings files
    SAVED_OBJECTIVE_SETTINGS = "saved_objective_settings.json"
    
    # Values dictionary
    VALUES_DICTIONARY = "ValuesDic.json"
    
    # Statistics files
    FEATURE_STATISTICS = "feature_statistics.json.gz"
    
    # Configuration files
    CONFIG_JSON = "config.json"

def ensure_data_dir() -> Path:
    """
    Ensures the data_components directory exists.
    Returns the path to the directory.
    """
    data_dir = Path(DATA_COMPONENTS_DIR)
    data_dir.mkdir(exist_ok=True)
    return data_dir

def get_json_path(filename: str) -> Path:
    """
    Returns the full path to a JSON file in the data_components directory.
    If the filename already includes a directory, it will be stripped.
    
    Args:
        filename (str): The name of the JSON file
        
    Returns:
        Path: Full path to the JSON file in the data_components directory
    """
    # Ensure data directory exists
    data_dir = ensure_data_dir()
    
    # Extract just the filename if a path is provided
    file_only = os.path.basename(filename)
    
    # Add .json extension if not already present and not a gzip file
    if not file_only.endswith(".json") and not file_only.endswith(".json.gz"):
        file_only += ".json"
    
    return data_dir / file_only

def load_json(filename: str, default: Optional[Dict] = None) -> Dict:
    """
    Load JSON data from a file in the data_components directory.
    
    Args:
        filename (str): The name of the JSON file
        default (Dict, optional): Default value to return if file not found
        
    Returns:
        Dict: The loaded JSON data or default if file not found/invalid
    """
    file_path = get_json_path(filename)
    
    try:
        if file_path.exists():
            # Handle gzipped files
            if str(file_path).endswith(".gz"):
                with gzip.open(file_path, "rt") as f:
                    data = json.load(f)
                    return data
            else:
                with open(file_path, 'r') as f:
                    data = json.load(f)
                    return data
        else:
            logger.warning(f"File not found: {file_path}, returning default value")
            return {} if default is None else default
    except Exception as e:
        logger.error(f"Error loading JSON data from {file_path}: {e}")
        return {} if default is None else default

def save_json(filename: str, data: Union[Dict, list], indent: int = 2) -> bool:
    """
    Save JSON data to a file in the data_components directory.
    
    Args:
        filename (str): The name of the JSON file
        data (Dict): The data to save
        indent (int): Indentation level for the JSON file
        
    Returns:
        bool: True if successful, False otherwise
    """
    file_path = get_json_path(filename)
    
    try:
        # Ensure parent directory exists
        file_path.parent.mkdir(exist_ok=True)
        
        # Handle gzipped files
        if str(file_path).endswith(".gz"):
            with gzip.open(file_path, "wt") as f:
                json.dump(data, f, indent=indent)
                logger.info(f"Saved gzipped JSON data to {file_path}")
        else:
            with open(file_path, 'w') as f:
                json.dump(data, f, indent=indent)
                logger.info(f"Saved JSON data to {file_path}")
        return True
    except Exception as e:
        logger.error(f"Error saving JSON data to {file_path}: {e}")
        return False