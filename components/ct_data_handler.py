"""
Class Table Data Handler for BMS Building Generator

This module handles loading and saving of Class Table data templates.
It provides functions to interact with ct_templates.json and create
appropriate interfaces for the settings window.

Version: 1.0.0
"""

import json
import logging
import os
import sys
import time
from pathlib import Path
from typing import Dict, Any, Optional

# Add the project root directory to the path for proper imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Now we can import the modules
from utils.json_path_handler import load_json, save_json, JsonFiles


class CTDataHandler:
    """Class Table Data Handler for BMS Building Generator.
    
    This class provides methods to load and save Class Table data,
    as well as utilities for handling the data format.
    """
    
    @staticmethod
    def load_ct_types() -> Dict[str, str]:
        """Load Class Table types from ct_templates.json.
        
        Returns:
            Dict[str, str]: A dictionary of CT types with ID as key and display name as value.
        """
        ct_types = {}
        
        try:
            # Load from ct_templates.json
            ct_templates = load_json(JsonFiles.CT_TEMPLATES, default={})
            if ct_templates:
                for ct_id in ct_templates.keys():
                    # Get name from template if available, otherwise use a generic name
                    if "Class" in ct_templates[ct_id]:
                        class_type = ct_templates[ct_id]["Class"]
                        ct_types[ct_id] = f"{ct_id}: Class {class_type}"
                    else:
                        ct_types[ct_id] = f"{ct_id}: CT Entry"
                
                logging.info(f"Loaded {len(ct_types)} class table types from templates")
            
            # If no types found, use default fallback
            if not ct_types:
                fallback_types = {
                    "1": "1: Default CT"
                }
                ct_types = fallback_types
                logging.info("Using fallback class table types list")
                
        except Exception as e:
            logging.error(f"Error loading class table types: {str(e)}")
            # Provide minimal fallback if everything fails
            ct_types = {"1": "1: Default CT"}
        
        return ct_types
    
    @staticmethod
    def get_ct_template(type_id: str) -> Dict[str, str]:
        """Get the template for a specific Class Table type.
        
        Args:
            type_id (str): The type ID of the Class Table.
            
        Returns:
            Dict[str, str]: The template for the Class Table type, or a default template if not found.
        """
        try:
            # Load templates
            templates = load_json(JsonFiles.CT_TEMPLATES, default={})
            
            # If type_id exists, return the template
            if type_id in templates:
                return templates[type_id]
            
            # Otherwise create and save a default template
            default_template = CTDataHandler.create_default_ct_template()
            templates[type_id] = default_template
            save_json(JsonFiles.CT_TEMPLATES, templates)
            logging.info(f"Created default template for class table type {type_id}")
            
            return default_template
        
        except Exception as e:
            logging.error(f"Error getting CT template: {str(e)}")
            return CTDataHandler.create_default_ct_template()
    
    @staticmethod
    def save_ct_template(type_id: str, template_data: Dict[str, str]) -> bool:
        """Save a Class Table template to the ct_templates.json file.
        
        Args:
            type_id (str): The type ID of the Class Table.
            template_data (Dict[str, str]): The template data to save.
            
        Returns:
            bool: True if successful, False otherwise.
        """
        try:
            # Start performance tracking
            start_time = time.time()
            
            # Load existing templates
            templates = load_json(JsonFiles.CT_TEMPLATES, default={})
            
            # If original template had a Type field, preserve it
            if type_id in templates and "Type" in templates[type_id]:
                template_data["Type"] = templates[type_id]["Type"]
            
            # Update templates
            templates[type_id] = template_data
            
            # Save templates to file
            save_json(JsonFiles.CT_TEMPLATES, templates)
            
            # Log performance metrics
            elapsed_time = time.time() - start_time
            logging.info(f"Saved template for class table type {type_id} in {elapsed_time:.2f} seconds")
            
            return True
            
        except Exception as e:
            logging.error(f"Error saving class table template: {str(e)}")
            return False
    
    @staticmethod
    def create_default_ct_template() -> Dict[str, str]:
        """Create a default template for Class Table with standard fields.
        
        Returns:
            Dict[str, str]: A dictionary of field names and their default values
        """
        return {
            "Id": "60395",
            "CollisionType": "0",
            "CollisionRadius": "0.000",
            "Domain": "3",
            "Class": "4",
            "SubType": "255",
            "Specific": "255",
            "Owner": "0",
            "Class_6": "255",
            "Class_7": "255",
            "UpdateRate": "0",
            "UpdateTolerance": "0",
            "FineUpdateRange": "150000.000",
            "FineUpdateForceRange": "0.000",
            "FineUpdateMultiplier": "1.000",
            "DamageSeed": "0",
            "HitPoints": "0",
            "MajorRev": "17",
            "MinRev": "26",
            "CreatePriority": "1",
            "ManagementDomain": "2",
            "Transferable": "1",
            "Private": "0",
            "Tangible": "0",
            "Collidable": "0",
            "Global": "0",
            "Persistent": "0",
            "GraphicsNormal": "0",
            "GraphicsRepaired": "0"
        }
