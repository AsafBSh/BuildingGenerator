import os
import json
import time
import logging
import random
import shutil
import threading
import math  # Added for collision detection calculations
from pathlib import Path
from typing import Dict, List, Any, Tuple, Optional
from xml.dom import minidom
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict

# Import the cache instance directly
from components.objective_cache import cache as objective_cache
from utils.json_path_handler import load_json, save_json, get_json_path, JsonFiles
from tkinter import messagebox

# Set up logging - use standard pattern to inherit from main application
logger = logging.getLogger(__name__)

class BmsInjector:
    """
    Handles injection of building data directly into Falcon BMS data files.
    
    This class provides methods for creating and updating BMS objective data
    by modifying XML files in the BMS directory structure.
    """
    
    def __init__(self, bms_path, backup=True, backup_features=True, auto_create_templates=True):
        """
        Initialize the BMS injector.
        
        Args:
            bms_path (str): Path to the BMS installation directory
            backup (bool): Whether to create backups before modifying files
            backup_features (bool): Whether to backup generated features in the Generated folder
            auto_create_templates (bool): Whether to automatically create templates during initialization
        """
        # Convert to Path object and normalize
        if bms_path:
            self.bms_path = Path(bms_path).resolve()
        else:
            self.bms_path = Path()
            logger.warning("No BMS path provided, using defaults")
        
        self.backup = backup
        self.backup_features = backup_features
        self.auto_create_templates = auto_create_templates
        self.templates_need_creation = False
        
        # Log backup settings to aid debugging
        logger.info(f"BMS Injector initialized with backup={self.backup}, backup_features={self.backup_features}")
        
        # Create Generated folder for temporary files
        self.generated_dir = Path("Generated")
        os.makedirs(self.generated_dir, exist_ok=True)
        
        # Create Backupfiles folder for backups
        self.backup_dir = Path("Backupfiles")
        os.makedirs(self.backup_dir, exist_ok=True)
        
        # Look for CT file in common locations
        self.ct_file = self._find_ct_file()
        
        # Try to find the objective directory
        self.objective_dir = self._find_objective_dir()
        
        # Validate BMS installation
        self.is_valid_installation = self._validate_installation()
        
        # Store templates for different objective types
        self.objective_templates = {}
        self.ct_templates = {}
        
        # Load templates if available
        self._load_templates()
        
        # Check if the cache is valid for this BMS installation
        bms_version = self._get_bms_version()
        if self.is_valid_installation:
            try:
                # Try to check if cache is valid
                if not objective_cache.is_cache_valid(bms_version=bms_version):
                    # Start a background thread to analyze objectives and build cache
                    logger.info("Cache is not valid, building in background thread")
                    threading.Thread(target=self._build_cache_async, daemon=True).start()
                else:
                    logger.info("Cache is valid, using cached data")
            except (AttributeError, Exception) as e:
                logger.warning(f"Error checking cache validity: {e}, proceeding without cache")
                # Start a background thread to analyze objectives and build cache anyway
                threading.Thread(target=self._build_cache_async, daemon=True).start()
        elif not self.is_valid_installation:
            # If invalid installation, use default templates only
            logger.warning("Invalid BMS installation, using default templates")
            if self.auto_create_templates:
                self.objective_templates = self._create_default_templates()
                self.ct_templates = self._create_default_ct_templates()
            else:
                self.templates_need_creation = True
    
    def _find_ct_file(self) -> Path:
        """Find the CT file in common locations."""
        # Common locations for Falcon4_CT.xml
        common_locations = [
            self.bms_path / "Data" / "TerrData" / "Falcon4_CT.xml",  # Standard path
            self.bms_path / "Falcon4_CT.xml",                        # Root directory
            self.bms_path / "TerrData" / "Falcon4_CT.xml",          # Alternative path
            Path(self.bms_path).parent / "Data" / "TerrData" / "Falcon4_CT.xml" # One level up
        ]
        
        # Try each location
        for location in common_locations:
            if location.exists() and location.is_file():
                logger.info(f"Found CT file at: {location}")
                return location
        
        # If not found, return the standard path (will be handled later)
        logger.warning(f"CT file not found in common locations, using default path")
        return self.bms_path / "Data" / "TerrData" / "Falcon4_CT.xml"
        
    def _find_objective_dir(self) -> Path:
        """Find the objective directory in common locations."""
        # Common locations for ObjectiveRelatedData - start with CT file path
        ct_path = self.ct_file.parent
        
        common_locations = [
            ct_path / "ObjectiveRelatedData",                   # Next to CT file (most accurate)
            self.bms_path / "Data" / "TerrData" / "ObjectiveRelatedData",  # Standard path
            self.bms_path / "ObjectiveRelatedData",                        # Root directory
            self.bms_path / "TerrData" / "ObjectiveRelatedData",          # Alternative path
            Path(self.bms_path).parent / "Data" / "TerrData" / "ObjectiveRelatedData" # One level up
        ]
        
        # Try each location
        for location in common_locations:
            if location.exists() and location.is_dir():
                logger.info(f"Found objective directory at: {location}")
                return location
        
        # If not found, use the path next to CT file (will create if needed)
        obj_dir = ct_path / "ObjectiveRelatedData"
        logger.warning(f"Objective directory not found in common locations, using path next to CT file: {obj_dir}")
        return obj_dir
        
    def _validate_installation(self) -> bool:
        """Validate that the BMS installation is usable."""
        # Check if the path exists
        if not self.bms_path.exists():
            logger.warning(f"BMS path does not exist: {self.bms_path}")
            return False
            
        # Check if CT file exists and is readable
        if not self.ct_file.exists():
            logger.warning(f"CT file does not exist: {self.ct_file}")
            return False
            
        try:
            # Try to open the CT file to check read permissions
            with open(self.ct_file, 'rb') as f:
                # Read a small chunk to verify it's readable
                f.read(100)
        except Exception as e:
            logger.warning(f"Cannot read CT file: {e}")
            return False
            
        # If we got here, basic validation passed
        return True
    
    def _load_templates(self):
        """Load objective and CT templates from JSON files or cache if available."""
        # Load templates using json_path_handler
        self.objective_templates = load_json(JsonFiles.OBJECTIVE_TEMPLATES, default={})
        if self.objective_templates:
            logger.info("Loaded objective templates from data_components directory")
        
        self.ct_templates = load_json(JsonFiles.CT_TEMPLATES, default={})
        if self.ct_templates:
            logger.info("Loaded CT templates from data_components directory")
        
        # If templates are still empty, flag the need to create them or create them immediately
        if not self.objective_templates:
            logger.info("No objective templates found")
            if self.auto_create_templates:
                logger.info("Auto-creating objective templates")
                self.objective_templates = self._create_default_templates()
                # Save the defaults for future use
                save_json(JsonFiles.OBJECTIVE_TEMPLATES, self.objective_templates)
            else:
                logger.info("Template creation deferred, will need to create objective templates later")
                self.templates_need_creation = True
        
        if not self.ct_templates:
            logger.info("No CT templates found")
            if self.auto_create_templates:
                logger.info("Auto-creating CT templates")
                self.ct_templates = self._create_default_ct_templates()
                # Save the defaults for future use
                save_json(JsonFiles.CT_TEMPLATES, self.ct_templates)
            else:
                logger.info("Template creation deferred, will need to create CT templates later")
                self.templates_need_creation = True
    
    def save_templates(self):
        """Save current templates to JSON files."""
        # Save templates using json_path_handler
        save_result_obj = save_json(JsonFiles.OBJECTIVE_TEMPLATES, self.objective_templates)
        save_result_ct = save_json(JsonFiles.CT_TEMPLATES, self.ct_templates)
        
        if save_result_obj and save_result_ct:
            logger.info("Successfully saved templates to data_components directory")
        else:
            logger.warning("Error saving one or more templates to data_components directory")
    
    def analyze_objectives(self):
        """
        Analyze existing objectives to create templates.
        
        Returns:
            dict: Mapping of objective types to template data
        """
        if not self.objective_dir.exists():
            return {}
        
        # Dictionary to store aggregated values by objective type
        type_data = {}
        
        # Process all OCD directories
        for ocd_dir in self.objective_dir.glob("OCD_*"):
            if not ocd_dir.is_dir():
                continue
                
            obj_index = ocd_dir.name.split("_")[1]
            ocd_file = ocd_dir / f"OCD_{obj_index}.XML"
            
            if not ocd_file.exists():
                continue
                
            try:
                # Parse OCD file
                tree = ET.parse(ocd_file)
                root = tree.getroot()
                ocd = root.find("OCD")
                
                if ocd is None:
                    continue
                    
                # Get CT index to find type
                ct_idx = int(ocd.find("CtIdx").text)
                obj_type = self._get_objective_type(ct_idx)
                
                if obj_type is None:
                    continue
                
                # Create template entry for this type if it doesn't exist
                if str(obj_type) not in type_data:
                    type_data[str(obj_type)] = {
                        "count": 0,
                        "fields": {}
                    }
                
                # Update data for this type
                template = type_data[str(obj_type)]
                template["count"] += 1
                
                # Process all fields in the OCD
                for elem in ocd:
                    if elem.tag == "Name" or elem.tag == "CtIdx" or elem.tag == "Num":
                        continue  # Skip unique fields
                        
                    value = elem.text
                    
                    # Try to convert numeric values
                    try:
                        if "." in value:
                            value = float(value)
                        else:
                            value = int(value)
                    except (ValueError, TypeError):
                        pass
                        
                    # Add/update field in template
                    if elem.tag not in template["fields"]:
                        template["fields"][elem.tag] = {
                            "values": [value],
                            "total": value if isinstance(value, (int, float)) else 0
                        }
                    else:
                        field_data = template["fields"][elem.tag]
                        field_data["values"].append(value)
                        if isinstance(value, (int, float)):
                            field_data["total"] += value
            
            except Exception as e:
                logger.error(f"Error processing {ocd_file}: {e}")
        
        # Calculate median/most common values
        for obj_type, template in type_data.items():
            for field_name, field_data in template["fields"].items():
                values = field_data["values"]
                
                if all(isinstance(v, (int, float)) for v in values):
                    # For numeric values, use the median
                    median = field_data["total"] / len(values)
                    if all(isinstance(v, int) for v in values):
                        median = int(median)
                    template["fields"][field_name] = median
                else:
                    # For non-numeric, use most common
                    value_counts = {}
                    for v in values:
                        value_counts[v] = value_counts.get(v, 0) + 1
                    
                    most_common = max(value_counts.items(), key=lambda x: x[1])[0]
                    template["fields"][field_name] = most_common
        
        # Update object templates
        self.objective_templates = {k: v["fields"] for k, v in type_data.items()}
        return self.objective_templates
    
    def _get_objective_type(self, ct_idx):
        """
        Get objective type from CT index.
        
        Args:
            ct_idx (int): CT index to lookup
            
        Returns:
            int: Objective type or None if not found or not an objective
        """
        if not self.ct_file.exists():
            return None
            
        try:
            tree = ET.parse(str(self.ct_file))
            root = tree.getroot()
            
            for ct in root.findall("CT"):
                if int(ct.get("Num")) == ct_idx:
                    entity_type = int(ct.find("EntityType").text)
                    
                    # Check if it's an objective (EntityType == 3)
                    if entity_type == 3:
                        return int(ct.find("Type").text)
                    return None
            
            return None
        except Exception as e:
            logger.error(f"Error getting objective type: {e}")
            return None
    
    def is_objective_ct(self, ct_num):
        """
        Check if a CT number is an objective.
        
        Args:
            ct_num (int): CT number to check
            
        Returns:
            bool: True if the CT is an objective, False otherwise
        """
        if not self.ct_file.exists():
            return False
            
        try:
            tree = ET.parse(str(self.ct_file))
            root = tree.getroot()
            
            for ct in root.findall("CT"):
                if int(ct.get("Num")) == ct_num:
                    entity_type = int(ct.find("EntityType").text)
                    return entity_type == 3
            
            return False
        except Exception as e:
            logger.error(f"Error checking if CT is objective: {e}")
            return False
    
    def objective_exists(self, obj_num):
        """
        Check if an objective exists.
        
        Args:
            obj_num (int): Objective number to check
            
        Returns:
            bool: True if the objective exists, False otherwise
        """
        obj_dir = self.objective_dir / f"OCD_{obj_num:05d}"
        return obj_dir.exists()
    
    def _write_xml(self, tree, filepath):
        """
        Write an XML tree to file with proper formatting.
        
        Args:
            tree (ElementTree): XML element tree
            filepath (Path): Path to save the file
        """
        # Create directory if it doesn't exist
        os.makedirs(filepath.parent, exist_ok=True)
        
        # Write with XML declaration and proper indentation
        xmlstr = '<?xml version="1.0" encoding="utf-8"?>\n'
        xmlstr += self._pretty_print(tree.getroot())
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(xmlstr)
    
    def _pretty_print(self, elem, level=0):
        """
        Format an XML element with proper indentation.
        
        Args:
            elem (Element): XML element
            level (int): Indentation level
            
        Returns:
            str: Formatted XML string
        """
        indent = '    ' * level
        result = indent + '<' + elem.tag
        
        # Add attributes
        for name, value in elem.attrib.items():
            result += f' {name}="{value}"'
        
        # Process children
        children = list(elem)
        if not children and (elem.text is None or elem.text.strip() == ''):
            result += '/>\n'
        else:
            result += '>'
            
            # Add text content if present
            if elem.text and elem.text.strip():
                result += elem.text
                
            result += '\n' if children else ''
            
            # Add children
            for child in children:
                result += self._pretty_print(child, level + 1)
                
            if children:
                result += indent
                
            result += f'</{elem.tag}>\n'
            
        return result 

    def _build_cache_async(self):
        """Build the cache in a background thread to avoid UI blocking."""
        start_time = time.time()
        logger.info("Building objective cache in background...")
        
        # Get BMS version
        bms_version = self._get_bms_version()
        objective_cache.set_bms_version(bms_version)
        
        # Analyze CT file and objectives
        ct_data = self._analyze_ct_file()
        objective_cache.set_ct_data(ct_data)
        
        obj_data = self._analyze_objectives()
        objective_cache.set_objective_data(obj_data)
        
        # Create default templates if needed
        if not objective_cache.get_objective_templates():
            templates = self._create_default_templates()
            objective_cache.set_objective_templates(templates)
        
        # CT templates are now only created in the BMS injection window
        # This improves performance for users who don't need BMS injection
        self.ct_templates = {}
        
        # Save the cache
        objective_cache.save_cache()
        
        elapsed = time.time() - start_time
        logger.info(f"Cache built in {elapsed:.2f} seconds")
    
    def _get_bms_version(self) -> str:
        """
        Get the BMS version from installation.
        
        Returns:
            BMS version string or empty string if not found
        """
        try:
            # Try to read BMS version from falcon_bms.cfg or another reliable source
            falcon_cfg = self.bms_path / "User" / "Config" / "falcon_bms.cfg"
            if falcon_cfg.exists():
                with open(falcon_cfg, 'r') as f:
                    for line in f:
                        if "set g_nVersion" in line:
                            parts = line.split('"')
                            if len(parts) >= 3:
                                return parts[1]
            return ""
        except Exception as e:
            logger.error(f"Error getting BMS version: {e}")
            return ""
    
    def _analyze_ct_file(self) -> Dict[str, Any]:
        """
        Analyze the CT file to extract objective-related data.
        
        Returns:
            Dictionary of CT data indexed by CT number
        """
        ct_data = {}
        error_count = 0
        
        try:
            # Check if CT file exists and is accessible
            if not self.ct_file.exists():
                logger.warning(f"CT file not found at path: {self.ct_file}")
                return ct_data
                
            # Check file size - if it's too small, it's probably not a valid XML file
            if self.ct_file.stat().st_size < 100:  # Arbitrary small size
                logger.warning(f"CT file appears to be empty or too small: {self.ct_file}")
                return ct_data
            
            # Parse the CT file
            try:
                tree = ET.parse(self.ct_file)
                root = tree.getroot()
            except ET.ParseError as e:
                logger.error(f"Failed to parse CT file {self.ct_file}: {e}")
                return ct_data
                
            # Count total CTs to track progress
            all_cts = root.findall(".//CT")
            total_cts = len(all_cts)
            logger.info(f"Found {total_cts} CT elements to analyze")
            
            # Extract data for each CT
            for i, ct in enumerate(all_cts):
                try:
                    # Get CT number from attribute
                    ct_num_attr = ct.get("Num")
                    if ct_num_attr is None:
                        continue
                        
                    ct_num = int(ct_num_attr)
                    
                    # Find the EntityType element
                    entity_type_elem = ct.find("EntityType")
                    if entity_type_elem is None or entity_type_elem.text is None:
                        continue
                    
                    entity_type = int(entity_type_elem.text)
                    
                    # Only include objectives (EntityType=3)
                    if entity_type == 3:
                        # Find Type element
                        type_elem = ct.find("Type")
                        if type_elem is None or type_elem.text is None:
                            continue
                            
                        ct_type = int(type_elem.text)
                        
                        # Find Name element
                        name_elem = ct.find("Name")
                        name = name_elem.text if name_elem is not None and name_elem.text is not None else ""
                        
                        ct_data[str(ct_num)] = {
                            "num": ct_num,
                            "type": ct_type,
                            "name": name,
                            "is_objective": True
                        }
                except (ValueError, AttributeError, TypeError) as e:
                    error_count += 1
                    # Only log every 100th error to avoid console spam
                    if error_count <= 3 or error_count % 100 == 0:
                        logger.warning(f"Error parsing CT element {i+1}/{total_cts}: {e}")
            
            if error_count > 0:
                logger.warning(f"Encountered {error_count} errors while parsing CT file")
                
            logger.info(f"Successfully analyzed {len(ct_data)} objective CTs")
            return ct_data
        
        except Exception as e:
            logger.error(f"Error analyzing CT file: {e}")
            return ct_data
    
    def _analyze_objectives(self) -> Dict[str, Any]:
        """
        Analyze existing objectives to extract data and templates.
        
        Returns:
            Dictionary of objective data indexed by objective number
        """
        obj_data = {}
        
        try:
            if not self.objective_dir.exists():
                logger.warning(f"Objective path not found: {self.objective_dir}")
                return obj_data
            
            # Collect templates by objective type
            templates_by_type = {}
            
            # Loop through all objective directories
            for obj_dir in self.objective_dir.glob("OCD_*"):
                try:
                    # Extract objective number from directory name
                    obj_num = int(obj_dir.name.split("_")[1])
                    
                    # Read the OCD file
                    ocd_file = obj_dir / f"{obj_dir.name}.XML"
                    if not ocd_file.exists():
                        continue
                    
                    # Parse the OCD file
                    tree = ET.parse(ocd_file)
                    root = tree.getroot()
                    
                    for ocd in root.findall(".//OCD"):
                        try:
                            ct_idx = int(ocd.find("CtIdx").text)
                            name = ocd.find("Name").text
                            
                            # Get CT type from cached CT data or direct lookup
                            ct_data = objective_cache.get_ct_data(ct_idx)
                            if ct_data:
                                obj_type = ct_data.get("type", 0)
                            else:
                                obj_type = self._get_ct_type(ct_idx)
                            
                            # Create objective data entry
                            obj_entry = {
                                "num": obj_num,
                                "ct_idx": ct_idx,
                                "name": name,
                                "type": obj_type
                            }
                            
                            # Extract all field values for template
                            field_dict = {}
                            for child in ocd:
                                tag = child.tag
                                if tag != "Name" and tag != "CtIdx" and tag != "Num":
                                    field_dict[tag] = child.text
                            
                            # Add to templates by type
                            if obj_type not in templates_by_type:
                                templates_by_type[obj_type] = []
                            templates_by_type[obj_type].append(field_dict)
                            
                            # Add to objective data
                            obj_data[str(obj_num)] = obj_entry
                        
                        except (ValueError, AttributeError, TypeError) as e:
                            logger.warning(f"Error parsing OCD element: {e}")
                
                except (ValueError, Exception) as e:
                    logger.warning(f"Error processing objective directory {obj_dir}: {e}")
            
            # Process templates by type to create median values
            template_medians = {}
            for obj_type, templates in templates_by_type.items():
                if not templates:
                    continue
                
                # Create a median template for this type
                median_template = {}
                
                # Get all field names
                all_fields = set()
                for template in templates:
                    all_fields.update(template.keys())
                
                # For each field, find the median or most common value
                for field in all_fields:
                    values = [t.get(field) for t in templates if field in t]
                    if not values:
                        continue
                    
                    # Try to convert to numeric
                    try:
                        # Check if all values are numeric
                        numeric_values = []
                        for v in values:
                            if "." in v:
                                numeric_values.append(float(v))
                            else:
                                numeric_values.append(int(v))
                        
                        # Find median
                        numeric_values.sort()
                        if len(numeric_values) % 2 == 0:
                            median = (numeric_values[len(numeric_values)//2 - 1] + 
                                      numeric_values[len(numeric_values)//2]) / 2
                        else:
                            median = numeric_values[len(numeric_values)//2]
                        
                        # Always store as string to ensure consistency
                        median_template[field] = str(median)
                    
                    except (ValueError, TypeError):
                        # For non-numeric values, use most common
                        value_counts = {}
                        for v in values:
                            value_counts[v] = value_counts.get(v, 0) + 1
                        
                        most_common = max(value_counts.items(), key=lambda x: x[1])[0]
                        median_template[field] = str(most_common)
                
                # Store the median template
                template_medians[str(obj_type)] = median_template
            
            # Update in-memory templates only; do not modify cache here
            self.objective_templates = template_medians
            
            logger.info(f"Analyzed {len(obj_data)} objectives and created {len(template_medians)} templates")
            return obj_data
        
        except Exception as e:
            logger.error(f"Error analyzing objectives: {e}")
            return obj_data
    
    def _create_default_templates(self) -> Dict[str, Dict[str, str]]:
        """
        Create templates for each objective type based on OCD files.
        If OCD files are not available, creates templates with default values.
        
        Returns:
            Dictionary of templates indexed by type number
        """
        logger.info("Creating objective templates from OCD files")
        
        # Find ObjectiveRelatedData directory
        obj_related_data_dir = self._find_objective_dir()
        if not obj_related_data_dir or not obj_related_data_dir.exists() or not obj_related_data_dir.is_dir():
            logger.warning(f"ObjectiveRelatedData directory not found. Using default templates.")
            return self._create_empty_templates()
            
        # Dictionary to map CT indexes to their types
        ct_idx_to_type = {}
        
        # First pass: build a mapping of CT indexes to their types from CT file
        try:
            ct_tree = ET.parse(self.ct_file)
            ct_root = ct_tree.getroot()
            
            for ct in ct_root.findall("CT"):
                try:
                    # Check if this is an objective (Domain=3, Class=4, EntityType=3)
                    domain_elem = ct.find("Domain")
                    class_elem = ct.find("Class")
                    entity_type_elem = ct.find("EntityType")
                    type_elem = ct.find("Type")
                    num_attr = ct.get("Num")
                    
                    if (domain_elem is not None and domain_elem.text == "3" and
                        class_elem is not None and class_elem.text == "4" and
                        entity_type_elem is not None and entity_type_elem.text == "3" and
                        type_elem is not None and type_elem.text and
                        num_attr is not None):
                        
                        # Store the mapping: CT index -> objective type
                        ct_idx = num_attr
                        obj_type = int(type_elem.text)
                        
                        if obj_type >= 1 and obj_type <= 31:
                            ct_idx_to_type[ct_idx] = obj_type
                except Exception as e:
                    logger.warning(f"Error processing CT entry: {e}")
            
            logger.info(f"Found {len(ct_idx_to_type)} objective types in CT file")
        except Exception as e:
            logger.error(f"Error parsing CT file: {e}")
            return self._create_empty_templates()
            
        # Fields to calculate median for
        median_fields = [
            "DataRate", "DeaggDistance", "Det_NoMove", "Det_Foot", "Det_Wheeled",
            "Det_Tracked", "Det_LowAir", "Det_Air", "Det_Naval", "Det_Rail",
            "Dam_None", "Dam_Penetration", "Dam_HighExplosive", "Dam_Heave", "Dam_Incendairy",
            "Dam_Proximity", "Dam_Kinetic", "Dam_Hydrostatic", "Dam_Chemical", "Dam_Nuclear",
            "Dam_Other", "ObjectiveIcon"
        ]
        
        # Dictionary to store values by objective type
        type_values = {}
        
        # Initialize all types with empty field lists
        for obj_type in range(1, 32):
            type_values[obj_type] = {field: [] for field in median_fields}
            
        # Scan all OCD directories and files
        ocd_count = 0
        logger.info(f"Scanning OCD files in: {obj_related_data_dir}")
        
        # Loop through all subdirectories in ObjectiveRelatedData
        for ocd_dir in obj_related_data_dir.iterdir():
            if not ocd_dir.is_dir() or not ocd_dir.name.startswith("OCD_"):
                continue
                
            # Look for the OCD XML file in this directory
            ocd_file = None
            for file in ocd_dir.iterdir():
                if file.is_file() and file.name.startswith("OCD_") and file.suffix.upper() == ".XML":
                    ocd_file = file
                    break
            
            if ocd_file is None:
                continue
                
            logger.debug(f"Processing OCD file: {ocd_file}")
            
            try:
                # Parse the OCD file
                ocd_tree = ET.parse(ocd_file)
                ocd_root = ocd_tree.getroot()
                ocd_elem = ocd_root.find("OCD")
                
                if ocd_elem is None:
                    continue
                
                # Get the CT index to find the objective type
                ct_idx_elem = ocd_elem.find("CtIdx")
                if ct_idx_elem is None or not ct_idx_elem.text:
                    continue
                
                ct_idx = ct_idx_elem.text
                if ct_idx not in ct_idx_to_type:
                    continue
                
                # Get the objective type for this OCD
                obj_type = ct_idx_to_type[ct_idx]
                
                # Collect values for each field
                for field in median_fields:
                    field_elem = ocd_elem.find(field)
                    if field_elem is not None and field_elem.text:
                        try:
                            # Try to convert to appropriate numeric type
                            if "." in field_elem.text:
                                value = float(field_elem.text)
                            else:
                                value = int(field_elem.text)
                            type_values[obj_type][field].append(value)
                        except (ValueError, TypeError):
                            # For non-numeric values, keep as string
                            type_values[obj_type][field].append(field_elem.text)
                
                ocd_count += 1
            except Exception as e:
                logger.warning(f"Error processing OCD file {ocd_file}: {e}")
                
        logger.info(f"Processed {ocd_count} OCD files.")
        
        # Calculate median values and create the templates
        templates = {}
        
        # Create a default template for any missing types
        basic_template = {field: "0" for field in median_fields}
        basic_template["RadarFeature"] = "0"  # Add constant field
        
        # Generate templates for all 31 objective types
        for obj_type in range(1, 32):
            template = {}
            
            # Calculate median values for all fields
            for field in median_fields:
                values = type_values[obj_type][field]
                
                if values and len(values) > 0:
                    # We have some values from OCD files
                    if all(isinstance(v, (int, float)) for v in values):
                        # Calculate median for numeric values
                        sorted_values = sorted(values)
                        n = len(sorted_values)
                        
                        if n % 2 == 0:
                            # Even number of values, average the middle two
                            mid_right = n // 2
                            mid_left = mid_right - 1
                            median = (sorted_values[mid_left] + sorted_values[mid_right]) / 2
                        else:
                            # Odd number of values, take the middle one
                            median = sorted_values[n // 2]
                            
                        # Keep integers as integers if all values were integers
                        if all(isinstance(v, int) for v in values):
                            median = int(median)
                            
                        template[field] = str(median)
                        logger.debug(f"Type {obj_type} {field}: Using median {median} from {len(values)} values")
                    else:
                        # For non-numeric values, use the most common value
                        value_counts = {}
                        for v in values:
                            if v is not None:
                                value_counts[v] = value_counts.get(v, 0) + 1
                                
                        if value_counts:
                            most_common = max(value_counts.items(), key=lambda x: x[1])[0]
                            template[field] = str(most_common)
                            logger.debug(f"Type {obj_type} {field}: Using most common value {most_common}")
                        else:
                            # Fallback to default - use 0
                            template[field] = "0"
                            logger.debug(f"Type {obj_type} {field}: No valid values, using 0")
                else:
                    # No values found for this field, use 0
                    template[field] = "0"
                    logger.debug(f"Type {obj_type} {field}: No OCD values found, using 0")
            
            # Add constant values
            template["RadarFeature"] = "0"  # Constant value per requirements
            
            # Add the template to the dictionary
            if template:
                templates[str(obj_type)] = template
            else:
                # If no template was created for this type, use the basic template
                templates[str(obj_type)] = basic_template.copy()
                logger.debug(f"Using empty template for objective type {obj_type} (no OCD data found)")
        
        # Save the templates to JSON file
        from utils.json_path_handler import save_json, JsonFiles
        save_json(JsonFiles.OBJECTIVE_TEMPLATES, templates)
        logger.info(f"Saved objective templates with real values from OCD files")
            
        return templates
        
    def _create_empty_templates(self) -> Dict[str, Dict[str, str]]:
        """
        Create empty templates with all zeros when no OCD data is available.
        
        Returns:
            Dictionary of default templates indexed by type number
        """
        logger.warning("Creating empty objective templates with default values")
        
        # Basic template with common fields
        basic_template = {
            "DataRate": "0",
            "DeaggDistance": "0",
            "Det_NoMove": "0.0",
            "Det_Foot": "0.0",
            "Det_Wheeled": "0.0",
            "Det_Tracked": "0.0",
            "Det_LowAir": "0.0",
            "Det_Air": "0.0",
            "Det_Naval": "0.0",
            "Det_Rail": "0.0",
            "Dam_None": "0",
            "Dam_Penetration": "0",
            "Dam_HighExplosive": "0",
            "Dam_Heave": "0",
            "Dam_Incendairy": "0",
            "Dam_Proximity": "0",
            "Dam_Kinetic": "0",
            "Dam_Hydrostatic": "0",
            "Dam_Chemical": "0",
            "Dam_Nuclear": "0",
            "Dam_Other": "0",
            "ObjectiveIcon": "0",
            "RadarFeature": "0"
        }
        
        # Create templates for each type (1-31)
        templates = {}
        for i in range(1, 32):
            templates[str(i)] = basic_template.copy()
        
        return templates
    
    def _create_default_ct_templates(self) -> Dict[str, Dict[str, str]]:
        """
        Create default CT templates for all objective types.
        
        Returns:
            Dictionary of CT templates indexed by type number
        """
        # Create a minimal template for each objective type (1-31)
        templates = {}
        logger.info("Creating default CT templates")
        
        # Fields that need default values
        median_fields = [
            "CollisionType", "CollisionRadius", "UpdateRate", "UpdateTolerance", 
            "FineUpdateRange", "FineUpdateForceRange", "FineUpdateMultiplier",
            "DamageSeed", "HitPoints", "MajorRev", "MinRev", 
            "CreatePriority", "ManagementDomain", "Transferable", "Private", 
            "Tangible", "Collidable", "Global", "Persistent", "Id"
        ]
        
        # Create template for each objective type
        for obj_type in range(1, 32):
            # Create template with default values
            template = {}
            
            # Set default value for all fields
            for field in median_fields:
                template[field] = "0"
                
            # Add constant values
            constant_values = {
                "Domain": "3",
                "Class": "4",
                "SubType": "255",
                "Specific": "255",
                "Owner": "0",
                "Class_6": "255",
                "Class_7": "255",
                "GraphicsNormal": "0",
                "GraphicsRepaired": "0",
                "GraphicsDamaged": "0",
                "GraphicsDestroyed": "0",
                "GraphicsLeftDestroyed": "0",
                "GraphicsRightDestroyed": "0",
                "GraphicsBothDestroyed": "0",
                "MoverDefinitionData": "0",
                "EntityType": "3"
            }
            
            # Create a new template with fields in the exact requested order
            ordered_template = {}
            
            # Add Id field first
            ordered_template["Id"] = template.get("Id", "60395")
            
            # First the median fields
            ordered_template["CollisionType"] = template.get("CollisionType", "0")
            ordered_template["CollisionRadius"] = template.get("CollisionRadius", "0")
            
            # Then add constant values in the specified order
            for field in ["Domain", "Class", "SubType", "Specific", "Owner", "Class_6", "Class_7"]:
                ordered_template[field] = constant_values[field]
            
            # Add remaining median fields in the specified order
            for field in ["UpdateRate", "UpdateTolerance", "FineUpdateRange", "FineUpdateForceRange", 
                          "FineUpdateMultiplier", "DamageSeed", "HitPoints", "MajorRev", "MinRev",
                          "CreatePriority", "ManagementDomain", "Transferable", "Private", 
                          "Tangible", "Collidable", "Global", "Persistent"]:
                ordered_template[field] = template.get(field, "0")
            
            # Add remaining constant fields in the specified order
            for field in ["GraphicsNormal", "GraphicsRepaired", "GraphicsDamaged", "GraphicsDestroyed",
                          "GraphicsLeftDestroyed", "GraphicsRightDestroyed", "GraphicsBothDestroyed",
                          "MoverDefinitionData", "EntityType"]:
                ordered_template[field] = constant_values[field]
            
            # Add to templates
            templates[str(obj_type)] = ordered_template
        
        return templates
    
    def _get_ct_type(self, ct_num: int) -> int:
        """
        Get the type of a CT number.
        
        Args:
            ct_num: CT number to look up
        
        Returns:
            CT type or 0 if not found
        """
        try:
            # Check cache first
            ct_data = objective_cache.get_ct_data(ct_num)
            if ct_data:
                return ct_data.get("type", 0)
            
            # Parse the CT file directly
            if not self.ct_file.exists():
                return 0
            
            tree = ET.parse(self.ct_file)
            root = tree.getroot()
            
            # Find the CT with the given number
            ct_elem = root.find(f".//CT[@Num='{ct_num}']")
            if ct_elem is not None:
                type_elem = ct_elem.find("Type")
                if type_elem is not None:
                    return int(type_elem.text)
            
            return 0
        
        except Exception as e:
            logger.warning(f"Error getting CT type: {e}")
            return 0

    def _backup_ct_file(self):
        """Create a backup of the CT file in the Backupfiles folder."""
        # Skip backup if backup setting is disabled
        if not self.backup:
            logger.debug(f"Skipping CT file backup due to disabled backup setting")
            return None
            
        if not self.ct_file.exists():
            logger.warning(f"CT file not found, cannot backup: {self.ct_file}")
            return None
            
        # Format timestamp for filename
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        
        # Create backup filename with timestamp
        backup_filename = f"Falcon4_CT-{timestamp}.xml"
        
        # If file already exists, add a counter
        counter = 1
        while (self.backup_dir / backup_filename).exists():
            backup_filename = f"Falcon4_CT-{timestamp}_{counter}.xml"
            counter += 1
            
        # Copy file to backup directory
        backup_path = self.backup_dir / backup_filename
        try:
            shutil.copy2(self.ct_file, backup_path)
            logger.info(f"Created backup of CT file: {backup_path}")
            return backup_path
        except Exception as e:
            logger.error(f"Failed to backup CT file: {e}")
            return None
            
    def _backup_objective_files(self, obj_num):
        """
        Create a backup of objective files in the Backupfiles folder.
        
        Args:
            obj_num (int): Objective number to backup
            
        Returns:
            Path: Path to the backup directory or None if backup failed
        """
        # Skip backup if backup setting is disabled
        if not self.backup:
            logger.info(f"Skipping objective {obj_num} backup due to disabled backup setting (self.backup={self.backup})")
            return None
            
        obj_num_str = f"{obj_num:05d}"
        obj_dir = self.objective_dir / f"OCD_{obj_num_str}"
        
        if not obj_dir.exists():
            logger.warning(f"Objective directory not found, cannot backup: {obj_dir}")
            return None
        
        # Format timestamp for folder name
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        
        # Create backup folder name with timestamp
        backup_dirname = f"OCD_{obj_num_str}-{timestamp}"
        
        # If folder already exists, add a counter
        counter = 1
        while (self.backup_dir / backup_dirname).exists():
            backup_dirname = f"OCD_{obj_num_str}-{timestamp}_{counter}"
            counter += 1
            
        # Create backup directory path
        backup_dir = self.backup_dir / backup_dirname
        
        try:
            # Copy the entire directory structure to ensure a complete backup
            shutil.copytree(obj_dir, backup_dir)
            
            logger.info(f"Created backup of objective {obj_num}: {backup_dir}")
            return backup_dir
        except Exception as e:
            logger.error(f"Failed to backup objective {obj_num}: {e}")
            return None
        
    def _create_ct_templates(self) -> Dict[str, Dict[str, str]]:
        """
        Create templates for CT elements based on objective type.
        
        This extracts typical values from existing CTs by type and creates template
        dictionaries that can be used when creating new CT elements.
        This function should only be called from the BMS injection window.
        
        Returns:
            Dictionary of CT templates indexed by type number
        """
        if not self.ct_file.exists():
            logger.warning(f"CT file not found, cannot create CT templates: {self.ct_file}")
            return self._create_default_ct_templates()
            
        try:
            # Dictionary to store aggregated values by objective type
            type_data = {}
            
            # Parse the CT file
            tree = ET.parse(self.ct_file)
            root = tree.getroot()
            
            # Process all CT elements
            for ct in root.findall("CT"):
                try:
                    # Check if it's an objective
                    entity_type_elem = ct.find("EntityType")
                    if entity_type_elem is None or entity_type_elem.text != "3":
                        continue
                        
                    # Get the objective type
                    type_elem = ct.find("Type")
                    if type_elem is None or not type_elem.text:
                        continue
                        
                    obj_type = type_elem.text
                    
                    # Create template entry for this type if it doesn't exist
                    if obj_type not in type_data:
                        type_data[obj_type] = {
                            "count": 0,
                            "fields": {}
                        }
                    
                    # Update data for this type
                    template = type_data[obj_type]
                    template["count"] += 1
                    
                    # Process all fields in the CT
                    for elem in ct:
                        if elem.tag == "Type" or elem.tag == "Name" or elem.tag == "EntityType":
                            continue  # Skip key fields that are set specifically
                            
                        if elem.text is not None:
                            value = elem.text
                            
                            # Try to convert numeric values
                            try:
                                if "." in value:
                                    value = float(value)
                                else:
                                    value = int(value)
                            except (ValueError, TypeError):
                                pass
                                
                            # Add/update field in template
                            if elem.tag not in template["fields"]:
                                template["fields"][elem.tag] = {
                                    "values": [value],
                                    "total": value if isinstance(value, (int, float)) else 0
                                }
                            else:
                                field_data = template["fields"][elem.tag]
                                field_data["values"].append(value)
                                if isinstance(value, (int, float)):
                                    field_data["total"] += value
                except Exception as e:
                    logger.warning(f"Error processing CT element: {e}")
                    continue
            
            # Calculate median/most common values for each type
            templates = {}
            for obj_type, template in type_data.items():
                type_template = {}
                for field_name, field_data in template["fields"].items():
                    values = field_data["values"]
                    
                    if all(isinstance(v, (int, float)) for v in values):
                        # For numeric values, use the median
                        median = field_data["total"] / len(values)
                        if all(isinstance(v, int) for v in values):
                            median = int(median)
                        type_template[field_name] = str(median)
                    else:
                        # For non-numeric, use most common
                        value_counts = {}
                        for v in values:
                            value_counts[v] = value_counts.get(v, 0) + 1
                        
                        most_common = max(value_counts.items(), key=lambda x: x[1])[0]
                        type_template[field_name] = str(most_common)
                
                templates[obj_type] = type_template
            
            # Cache the templates
            self.ct_templates = templates
            
            # Save to ct_templates.json in cache directory
            cache_dir = Path("data_components")
            cache_dir.mkdir(exist_ok=True)
            
            with open(cache_dir / "ct_templates.json", "w") as f:
                json.dump(templates, f, indent=2)
                
            logger.info(f"Created CT templates for {len(templates)} objective types")
            return templates
            
        except Exception as e:
            logger.error(f"Error creating CT templates: {e}")
            return self._create_default_ct_templates()

    def _create_default_ct_templates(self) -> Dict[str, Dict[str, str]]:
        """
        Create default templates for CT elements.
        
        Returns:
            Dictionary of default CT templates
        """
        # Define the EXACT field order based on the example - NO ADDITIONAL FIELDS
        field_order = [
            "Id", "CollisionType", "CollisionRadius", "Domain", "Class", "Type",
            "SubType", "Specific", "Owner", "Class_6", "Class_7", "UpdateRate",
            "UpdateTolerance", "FineUpdateRange", "FineUpdateForceRange", 
            "FineUpdateMultiplier", "DamageSeed", "HitPoints", "MajorRev", "MinRev",
            "CreatePriority", "ManagementDomain", "Transferable", "Private", "Tangible",
            "Collidable", "Global", "Persistent", "GraphicsNormal", "GraphicsRepaired",
            "GraphicsDamaged", "GraphicsDestroyed", "GraphicsLeftDestroyed", 
            "GraphicsRightDestroyed", "GraphicsBothDestroyed", "MoverDefinitionData",
            "EntityType", "EntityIdx"
        ]
        
        # Basic template with common fields for all objective types - ONLY fields in the original example
        default_template = {
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
            "GraphicsRepaired": "0",
            "GraphicsDamaged": "0",
            "GraphicsDestroyed": "0",
            "GraphicsLeftDestroyed": "0",
            "GraphicsRightDestroyed": "0",
            "GraphicsBothDestroyed": "0",
            "MoverDefinitionData": "0",
            "EntityType": "3"
        }
        
        # Create templates for each objective type (1-31)
        templates = {}
        for i in range(1, 32):
            # Create a copy of the default template
            template = default_template.copy()
            # Set the type value
            template["Type"] = str(i)
            templates[str(i)] = template
        
        # Save templates to cache for future use (functionality moved from _create_comprehensive_ct_templates)
        try:
            cache_dir = Path("data_components")
            cache_dir.mkdir(exist_ok=True)
            
            with open(cache_dir / "ct_templates.json", "w") as f:
                json.dump(templates, f, indent=2)
            
            logger.info(f"Saved CT templates for {len(templates)} objective types")
        except Exception as e:
            logger.error(f"Error saving CT templates: {e}")
        
        return templates
    
    def _update_ct_file(self, ct_num, obj_type, name, backup=True, obj_num=None):
        """
        Update the CT file with objective data.
        
        Args:
            ct_num (int): CT number
            obj_type (int): Objective type
            name (str): Objective name
            backup (bool): Whether to create a backup of the CT file
            obj_num (int, optional): Objective number, used to set EntityIdx
            
        Returns:
            bool: True if successful, False otherwise
        """
        if not self.ct_file.exists():
            logger.warning(f"CT file not found, cannot update: {self.ct_file}")
            return False
            
        # Create a backup of the CT file before modifying only if backups are enabled and requested
        if self.backup and backup:
            self._backup_ct_file()
        
        # Convert obj_type to string and ensure it's valid
        try:
            # Explicitly convert to int first to validate it's a number
            obj_type_int = int(obj_type)
            obj_type_str = str(obj_type_int)
            logger.debug(f"Converting type from {obj_type} to int {obj_type_int} to str {obj_type_str}")
            logger.info(f"Setting objective type {obj_type_str} for CT {ct_num}")
        except (ValueError, TypeError):
            logger.error(f"Invalid objective type: {obj_type}, must be a number")
            return False
            
        try:
            # Parse the CT file
            tree = ET.parse(self.ct_file)
            root = tree.getroot()
            
            # Load templates from ct_templates.json file
            cache_file = Path("data_components") / "ct_templates.json"
            if cache_file.exists():
                try:
                    with open(cache_file, "r") as f:
                        ct_templates = json.load(f)
                        logger.info(f"Loaded CT templates from {cache_file}")
                except Exception as e:
                    logger.warning(f"Error loading CT templates: {e}, calculating templates")
                    ct_templates = self._create_default_ct_templates()
            else:
                logger.warning(f"CT templates file not found at {cache_file}, calculating templates")
                ct_templates = self._create_default_ct_templates()
            
            # Get template for this objective type
            ct_template = ct_templates.get(obj_type_str, {})
            
            # If template not found, get default template
            if not ct_template:
                logger.warning(f"No template found for objective type {obj_type_str}, creating default")
                default_templates = self._create_default_ct_templates()
                ct_template = default_templates.get(obj_type_str, {})
                
                # Add minimum required fields if not present
                if "EntityType" not in ct_template:
                    ct_template["EntityType"] = "3"  # Objective
                if "Domain" not in ct_template:
                    ct_template["Domain"] = "3"
                if "Class" not in ct_template:
                    ct_template["Class"] = "4"
            
            # Define the EXACT field order based on the example - NO ADDITIONAL FIELDS
            field_order = [
                "Id", "CollisionType", "CollisionRadius", "Domain", "Class", "Type",
                "SubType", "Specific", "Owner", "Class_6", "Class_7", "UpdateRate",
                "UpdateTolerance", "FineUpdateRange", "FineUpdateForceRange", 
                "FineUpdateMultiplier", "DamageSeed", "HitPoints", "MajorRev", "MinRev",
                "CreatePriority", "ManagementDomain", "Transferable", "Private", "Tangible",
                "Collidable", "Global", "Persistent", "GraphicsNormal", "GraphicsRepaired",
                "GraphicsDamaged", "GraphicsDestroyed", "GraphicsLeftDestroyed", 
                "GraphicsRightDestroyed", "GraphicsBothDestroyed", "MoverDefinitionData",
                "EntityType", "EntityIdx"
            ]
            
            # Check if CT already exists
            ct_exists = False
            for ct in root.findall("CT"):
                try:
                    if int(ct.get("Num")) == ct_num:
                        ct_exists = True
                        logger.info(f"Found existing CT entry #{ct_num}, updating it")
                        
                        # Remove all existing children to ensure proper order
                        for child in list(ct):
                            ct.remove(child)
                        
                        # Update basic field values in correct order
                        field_values = {}
                        # Start with template values
                        for field_name, field_value in ct_template.items():
                            field_values[field_name] = field_value
                        
                        # CRITICAL: Force set the Type field to objective type
                        field_values["Type"] = obj_type_str
                        logger.info(f"Setting Type field to: {obj_type_str}")
                            
                        # EntityType must be 3 for objectives
                        field_values["EntityType"] = "3"  # 3 = Objective
                        
                        # Set EntityIdx (objective number)
                        if obj_num is not None:
                            field_values["EntityIdx"] = str(obj_num)
                        else:
                            # Find highest existing Entity Index
                            highest_entity_idx = 0
                            for other_ct in root.findall("CT"):
                                other_idx_elem = other_ct.find("EntityIdx")
                                if other_idx_elem is not None and other_idx_elem.text:
                                    try:
                                        entity_idx = int(other_idx_elem.text)
                                        highest_entity_idx = max(highest_entity_idx, entity_idx)
                                    except (ValueError, TypeError):
                                        pass
                            
                            field_values["EntityIdx"] = str(highest_entity_idx + 1)
                        
                        # Create elements in the correct order
                        for field in field_order:
                            if field in field_values:
                                elem = ET.SubElement(ct, field)
                                elem.text = field_values[field]
                                
                                # Additional logging for Type field to ensure it's being set
                                if field == "Type":
                                    logger.info(f"Created Type field with value: {field_values[field]}")
                        
                        break
                except (ValueError, TypeError, AttributeError) as e:
                    # Skip invalid CT entries
                    logger.warning(f"Skipping invalid CT entry: {e}")
                    continue
            
            # If CT doesn't exist, create a new one
            if not ct_exists:
                logger.info(f"CT #{ct_num} not found, creating new one")
                # Create new CT element
                new_ct = ET.SubElement(root, "CT", Num=str(ct_num))
                
                # Prepare field values
                field_values = {}
                
                # Start with template values
                for field_name, field_value in ct_template.items():
                    field_values[field_name] = field_value
                
                # CRITICAL: Force set the Type field to objective type
                field_values["Type"] = obj_type_str
                logger.info(f"Setting Type field to: {obj_type_str}")
                    
                # EntityType must be 3 for objectives
                field_values["EntityType"] = "3"  # 3 = Objective
                
                # Set EntityIdx
                if obj_num is not None:
                    field_values["EntityIdx"] = str(obj_num)
                else:
                    # Find highest existing Entity Index
                    highest_entity_idx = 0
                    for other_ct in root.findall("CT"):
                        entity_idx_elem = other_ct.find("EntityIdx")
                        if entity_idx_elem is not None and entity_idx_elem.text:
                            try:
                                entity_idx = int(entity_idx_elem.text)
                                highest_entity_idx = max(highest_entity_idx, entity_idx)
                            except (ValueError, TypeError):
                                pass
                    
                    field_values["EntityIdx"] = str(highest_entity_idx + 1)
                
                # Create elements in the correct order - ONLY those in field_order
                for field in field_order:
                    if field in field_values:
                        elem = ET.SubElement(new_ct, field)
                        elem.text = field_values[field]
                        
                        # Additional logging for Type field to ensure it's being set
                        if field == "Type":
                            logger.info(f"Created Type field with value: {field_values[field]}")
            
            # Verify the Type field was correctly set before writing
            type_correct = False
            for ct in root.findall("CT"):
                if int(ct.get("Num")) == ct_num:
                    type_elem = ct.find("Type")
                    if type_elem is not None:
                        if type_elem.text != str(obj_type):
                            logger.warning(f"CT file verification failed: Type={type_elem.text}, expected {obj_type}")
                            # Try to fix it
                            type_elem.text = str(obj_type)
                            self._write_xml(tree, self.ct_file)
                            logger.info(f"Fixed Type field to: {obj_type}")
                        else:
                            logger.info(f"CT file verification passed: Type={type_elem.text}")
                    else:
                        # Type element is missing, add it
                        logger.warning("Type element is missing, adding it")
                        type_elem = ET.SubElement(ct, "Type")
                        type_elem.text = str(obj_type)
                        self._write_xml(tree, self.ct_file)
                        logger.info(f"Added Type field with value: {obj_type}")
            if not type_correct:
                logger.warning("Could not verify Type field was set correctly, proceeding anyway")
            
            # Write the updated CT file
            self._write_xml(tree, self.ct_file)
            logger.info(f"Updated CT file with objective {ct_num}, type {obj_type_str}")
            
            # Update the cache
            if hasattr(objective_cache, 'set_ct_data'):
                objective_cache.set_ct_data({
                    "num": ct_num,
                    "type": obj_type_int,  # Use the integer value for cache
                    "name": name,
                    "is_objective": True
                }, ct_num)
                objective_cache.save_cache()
            
            return True
        except Exception as e:
            logger.error(f"Error updating CT file: {e}")
            return False
    
    def create_objective(self, obj_num, ct_num, name, obj_type, fields=None, reset_pd=True):
        """
        Create a new objective or update an existing one.
        
        Args:
            obj_num (int): Objective number
            ct_num (int): CT number
            name (str): Objective name
            obj_type (int): Objective type
            fields (dict): Field values for the objective
            reset_pd (bool): Whether to reset PHD and PDX files
            
        Returns:
            dict: Result dictionary with status and details
        """
        # Validate and convert objective type
        try:
            obj_type = int(obj_type)  # Convert to int to ensure it's a valid number
            logger.info(f"Creating objective {obj_num} with type {obj_type}")
        except (ValueError, TypeError):
            error_msg = f"Invalid objective type: {obj_type}, must be a number"
            logger.error(error_msg)
            return {"status": "error", "message": error_msg}
        
        # Note: Overwrite confirmation is handled in MainCode.py before this method is called
            
        # Format objective number with leading zeros
        obj_num_str = f"{obj_num:05d}"
        
        # Create a backup of the CT file (only once - we'll pass backup=False to _update_ct_file)
        # We need to reimplement the core functionality without calling create_objective
        # to avoid the duplicate backup of the CT file
        
        # Define timestamp and temporary directory variables
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        tmp_dir = None

        # Only set up backup directory if backup_features is enabled
        if self.backup_features:
            tmp_dir = self.generated_dir / f"OCD_{obj_num_str}-{timestamp}"
            os.makedirs(tmp_dir, exist_ok=True)
            logger.debug(f"Created backup directory for generated features: {tmp_dir}")
        else:
            logger.debug("Skipping backup directory creation - backup_features disabled")
        
        # Create objective directory if needed
        os.makedirs(self.objective_dir / f"OCD_{obj_num_str}", exist_ok=True)
        
        # Initialize combined fields dictionary
        combined_fields = {}

        # First, add template values for this specific objective type (base template)
        template_fields = self.objective_templates.get(str(obj_type), {})
        for key, value in template_fields.items():
            combined_fields[key] = str(value)  # Ensure template values are strings
        
        # Then override with provided fields if any
        if fields:
            for key, value in fields.items():
                combined_fields[key] = str(value)  # Ensure all values are strings
        
        # Log for debugging
        logger.debug(f"Creating objective type {obj_type} with template fields: {template_fields}")
        logger.debug(f"Final combined fields: {combined_fields}")
        
        # Create OCD file and its temp copy
        ocd_file = self.objective_dir / f"OCD_{obj_num_str}.XML"
        success = self._create_ocd_file(ocd_file, obj_num, ct_num, name, combined_fields)
        # Create a copy in the Generated folder if backup_features is enabled
        if self.backup_features and tmp_dir is not None:
            tmp_ocd_file = tmp_dir / f"OCD_{obj_num_str}.XML"
            self._create_ocd_file(tmp_ocd_file, obj_num, ct_num, name, combined_fields)
        
        if not success:
            error_msg = f"Failed to create OCD file for objective {obj_num}"
            logger.error(error_msg)
            return {"status": "error", "message": error_msg, "obj_num": obj_num}
        
        # Create/reset PHD and PDX files if requested
        if reset_pd:
            pdx_file = self.objective_dir / f"PDX_{obj_num_str}.XML"
            phd_file = self.objective_dir / f"PHD_{obj_num_str}.XML"

            
            self._create_pd_file(pdx_file, "PDRecords", "PD")
            self._create_pd_file(phd_file, "PHDRecords", "PHD")
            # Create copies in the Generated folder if backup_features is enabled
            if self.backup_features and tmp_dir is not None:
                tmp_pdx_file = tmp_dir / f"PDX_{obj_num_str}.XML"
                tmp_phd_file = tmp_dir / f"PHD_{obj_num_str}.XML"
                self._create_pd_file(tmp_pdx_file, "PDRecords", "PD")
                self._create_pd_file(tmp_phd_file, "PHDRecords", "PHD")
        
        # Create empty FED file ready for injection
        fed_file = self.objective_dir / f"FED_{obj_num_str}.XML"
        self._create_fed_file(fed_file)
        # Create a copy in the Generated folder if backup_features is enabled
        if self.backup_features and tmp_dir is not None:
            tmp_fed_file = tmp_dir / f"FED_{obj_num_str}.XML"
            self._create_fed_file(tmp_fed_file)
        
        # Update CT file with objective data, but don't create another backup
        # Pass obj_num to properly set the EntityIdx in the CT file
        ct_success = self._update_ct_file(ct_num, obj_type, name, backup=False, obj_num=obj_num)
        if not ct_success:
            error_msg = f"Failed to update CT file for objective {obj_num}"
            logger.warning(error_msg)
            return {"status": "error", "message": error_msg, "obj_num": obj_num}
            
        # Verify the CT file was updated with the correct type
        try:
            tree = ET.parse(self.ct_file)
            root = tree.getroot()
            for ct in root.findall("CT"):
                if int(ct.get("Num")) == ct_num:
                    type_elem = ct.find("Type")
                    if type_elem is not None:
                        if type_elem.text != str(obj_type):
                            logger.warning(f"CT file verification failed: Type={type_elem.text}, expected {obj_type}")
                            # Try to fix it
                            type_elem.text = str(obj_type)
                            self._write_xml(tree, self.ct_file)
                            logger.info(f"Fixed Type field to: {obj_type}")
                        else:
                            logger.info(f"CT file verification passed: Type={type_elem.text}")
                    else:
                        # Type element is missing, add it
                        logger.warning("Type element is missing, adding it")
                        type_elem = ET.SubElement(ct, "Type")
                        type_elem.text = str(obj_type)
                        self._write_xml(tree, self.ct_file)
                        logger.info(f"Added Type field with value: {obj_type}")
        except Exception as e:
            logger.error(f"Error verifying CT file update: {e}")
        
        # Operation completed successfully
        return {
            "status": "success", 
            "message": f"Successfully created objective {obj_num}",
            "obj_num": obj_num,
            "ct_num": ct_num
        }

    def _create_ocd_file(self, filepath, obj_num, ct_num, name, fields):
        """
        Create an OCD file with specified fields.
        
        Args:
            filepath (Path): Path to the OCD file
            obj_num (int): Objective number
            ct_num (int): CT number
            name (str): Objective name
            fields (dict): Field values for the objective
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            root = ET.Element("OCDRecords")
            ocd = ET.SubElement(root, "OCD", Num=str(obj_num))
            
            # Define the exact field order to match BMS requirements
            field_order = [
                "CtIdx",
                "Name",
                "DataRate",
                "DeaggDistance",
                "Det_NoMove",
                "Det_Foot",
                "Det_Wheeled",
                "Det_Tracked",
                "Det_LowAir",
                "Det_Air",
                "Det_Naval",
                "Det_Rail",
                "Dam_None",
                "Dam_Penetration",
                "Dam_HighExplosive",
                "Dam_Heave",
                "Dam_Incendairy",
                "Dam_Proximity",
                "Dam_Kinetic",
                "Dam_Hydrostatic",
                "Dam_Chemical",
                "Dam_Nuclear",
                "Dam_Other",
                "ObjectiveIcon",
                "RadarFeature"
            ]
            
            # Add required fields in the specified order
            for field_name in field_order:
                if field_name == "CtIdx":
                    # Add CT index
                    ct_idx = ET.SubElement(ocd, "CtIdx")
                    ct_idx.text = str(ct_num)
                elif field_name == "Name":
                    # Add name
                    name_elem = ET.SubElement(ocd, "Name")
                    name_elem.text = name
                else:
                    # Add other fields with values from the input or defaults
                    field_elem = ET.SubElement(ocd, field_name)
                    field_elem.text = str(fields.get(field_name, ""))
            
            # Write to file with proper formatting
            tree = ET.ElementTree(root)
            self._write_xml(tree, filepath)
            return True
            
        except Exception as e:
            logger.error(f"Error creating OCD file: {e}")
            return False

    def _create_pd_file(self, filepath, root_tag, elem_tag):
        """
        Create a generic PD file (PDX or PHD).
        
        Args:
            filepath (Path): Path to the PD file
            root_tag (str): Root element tag
            elem_tag (str): Child element tag
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            root = ET.Element(root_tag)
            pd = ET.SubElement(root, elem_tag, Num="0")
            
            if elem_tag == "PD":
                # PDX format
                fields = ["OffsetX", "OffsetY", "OffsetZ", "MaxHeight", "MaxWidth", "MaxLength"]
                for field in fields:
                    elem = ET.SubElement(pd, field)
                    elem.text = "0.000"
            else:
                # PHD format
                fields = [
                    ("ObjIdx", "0"), ("Type", "0"), ("PointCount", "0"), 
                    ("Data", "0.000"), ("FirstPtIdx", "0"), 
                    ("RunwayTexture", "0"), ("RunwayNumber", "0"), ("LandingPattern", "0")
                ]
                for field_name, default_value in fields:
                    elem = ET.SubElement(pd, field_name)
                    elem.text = default_value
            
            # Write to file with proper formatting
            tree = ET.ElementTree(root)
            self._write_xml(tree, filepath)
            return True
            
        except Exception as e:
            logger.error(f"Error creating PD file: {e}")
            return False

    def _create_fed_file(self, filepath):
        """
        Create an empty FED file.
        
        Args:
            filepath (Path): Path to the FED file
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            root = ET.Element("FEDRecords")
            # Empty FED file just has the root element initially
            
            # Write to file with proper formatting
            tree = ET.ElementTree(root)
            self._write_xml(tree, filepath)
            return True
            
        except Exception as e:
            logger.error(f"Error creating FED file: {e}")
            return False

    def inject_features(self, obj_num, features, models_data, skip_backup=False):
        """
        Inject feature data into an objective's FED file.
        
        Args:
            obj_num (int): Objective number
            features (list): List of feature entry strings
            models_data (DataFrame): DataFrame with model information
            skip_backup (bool): Whether to skip backing up objective files (default: False)
            
        Returns:
            dict: Result dictionary with status and details
        """
        obj_num_str = f"{obj_num:05d}"
        obj_dir = self.objective_dir / f"OCD_{obj_num_str}"
        fed_file = obj_dir / f"FED_{obj_num_str}.XML"
        
        # Check if objective exists
        if not obj_dir.exists() or not fed_file.exists():
            error_msg = f"Objective directory or FED file does not exist: {obj_dir}"
            logger.error(error_msg)
            return {"status": "error", "message": error_msg, "obj_num": obj_num}
        
        # Backup objective files before modifying only if backups are enabled and not skipped
        if self.backup and not skip_backup:
            self._backup_objective_files(obj_num)
            
        # Initialize tmp_dir and tmp_fed_file as None
        tmp_dir = None
        tmp_fed_file = None
        
        # Only set up backup paths if backup_features is enabled
        if self.backup_features:
            # Define timestamp for backup paths
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            tmp_dir = self.generated_dir / f"OCD_{obj_num_str}-{timestamp}"
            os.makedirs(tmp_dir, exist_ok=True)
            tmp_fed_file = tmp_dir / f"FED_{obj_num_str}.XML"
            logger.debug(f"Created backup directory for generated features: {tmp_dir}")
        else:
            # Skip all backup operations
            logger.debug("Skipping all backup operations - backup_features disabled")
        
        try:
            # Parse existing FED file
            tree = ET.parse(str(fed_file))
            root = tree.getroot()
            
            # Clear existing entries
            for child in list(root):
                root.remove(child)
            
            # Process each feature entry and add to FED file
            for i, feature in enumerate(features):
                self._add_fed_entry(root, i, feature, models_data)
            
            # Write updated XML to the main FED file
            self._write_xml(tree, fed_file)
            
            # Only write to backup files if backup_features is enabled
            if self.backup_features and tmp_dir is not None and tmp_fed_file is not None:
                # Write to the backup FED file
                self._write_xml(tree, tmp_fed_file)
                
                # Also save features to a text file for debugging
                with open(tmp_dir / f"Features_{obj_num_str}.txt", "w") as f:
                    f.write(f"# Features for Objective {obj_num}\n\n")
                    for feature in features:
                        f.write(f"{feature}\n")
                logger.info(f"Created feature backups in {tmp_dir}")
                    
            # Operation completed successfully
            return {
                "status": "success", 
                "message": f"Successfully injected {len(features)} features into objective {obj_num}",
                "obj_num": obj_num,
                "feature_count": len(features)
            }
            
        except Exception as e:
            error_msg = f"Error injecting features: {e}"
            logger.error(error_msg)
            # Try to save features to tmp file even if injection failed, but only if backup_features is enabled
            if self.backup_features and tmp_dir is not None:
                try:
                    with open(tmp_dir / f"Features_{obj_num_str}_failed.txt", "w") as f:
                        f.write(f"# Features that failed to inject for Objective {obj_num}\n\n")
                        f.write(f"# Error: {str(e)}\n\n")
                        for feature in features:
                            f.write(f"{feature}\n")
                except Exception:
                    pass
            return {"status": "error", "message": error_msg, "obj_num": obj_num}
    
    def process_features_with_collision_detection(self, features, models_data):
        """
        Process feature entries with collision detection.
        
        This function processes the feature entries to avoid collisions between features
        by checking bounding boxes. If collisions are detected, it will retry placement
        up to 5 times before placing the feature anyway.
        
        Args:
            features (list): List of feature entry strings
            models_data (DataFrame): DataFrame with model information
            
        Returns:
            list: Processed feature entries with adjusted coordinates to minimize collisions
        """
        # If no features, return empty list
        if not features:
            return []
            
        # List to store processed features
        processed_features = []
        
        # Create a list to store occupied bounding boxes
        # Each bounding box is represented as [x_min, y_min, x_max, y_max]
        occupied_bounding_boxes = []
        
        # Get feature dimensions directly from the database
        def get_feature_dimensions(ct_number):
            # Find the model data for this CT number
            model_rows = models_data[models_data["CTNumber"] == ct_number] if models_data is not None else None
            
            # If no model data found, raise an error - no defaults
            if model_rows is None or model_rows.empty:
                error_msg = f"No model data found for CT {ct_number}"
                logger.error(error_msg)
                raise ValueError(error_msg)
            
            # Get actual Width and Length from the database
            if 'Width' not in model_rows.columns or 'Length' not in model_rows.columns:
                error_msg = f"Feature dimensions (Width/Length) missing from database for CT {ct_number}"
                logger.error(error_msg)
                raise ValueError(error_msg)
                
            width = model_rows.iloc[0]['Width']
            length = model_rows.iloc[0]['Length']
            feature_name = model_rows.iloc[0]['FeatureName'] if 'FeatureName' in model_rows.columns else 'unknown'
            
            # Log the actual dimensions
            logger.debug(f"Actual dimensions for CT {ct_number} ({feature_name}): Width={width}, Length={length}")
            
            return width, length
        
        # Check for collision between a proposed bounding box and existing boxes
        def check_collision(new_box, existing_boxes):
            # If no existing boxes, no collision
            if not existing_boxes:
                return False
                
            # Check if the new box overlaps with any existing box
            for box in existing_boxes:
                # Check for non-overlap conditions
                if (new_box[0] > box[2] or  # new_min_x > existing_max_x
                    new_box[2] < box[0] or  # new_max_x < existing_min_x
                    new_box[1] > box[3] or  # new_min_y > existing_max_y
                    new_box[3] < box[1]):   # new_max_y < existing_min_y
                    # No overlap with this box
                    continue
                # If we get here, there's an overlap
                return True
            
            # No overlap with any box
            return False
        
        # Process each feature with collision detection
        for feature in features:
            # Parse the feature entry
            parts = feature.split()
            ct_number = int(parts[0].split('=')[1])
            y_dist, x_dist, z_dist, rotation = map(float, parts[1:5])
            
            # Get the actual feature dimensions from the database
            try:
                width, length = get_feature_dimensions(ct_number)
                
                # Try to place the feature up to 5 times to avoid collisions
                placed = False
                attempts = 0
                original_x, original_y = x_dist, y_dist
                best_x, best_y = x_dist, y_dist  # Store best position (for fallback)
                
                while attempts < 5 and not placed:
                    # Calculate bounding box with the feature at this position
                    # Use actual width and length for more accurate collision detection
                    half_width = width / 2
                    half_length = length / 2
                    new_box = [x_dist - half_width, y_dist - half_length, x_dist + half_width, y_dist + half_length]
                    
                    # Check if this position collides with existing features
                    if not check_collision(new_box, occupied_bounding_boxes):
                        # No collision, accept this position
                        placed = True
                        occupied_bounding_boxes.append(new_box)
                        logger.debug(f"Feature CT {ct_number} placed at ({x_dist:.2f}, {y_dist:.2f}) without collision")
                    else:
                        # Collision detected, try a slightly different position
                        attempts += 1
                        
                        # Save current position as best candidate if it's the first attempt
                        if attempts == 1:
                            best_x, best_y = x_dist, y_dist
                            
                        # Calculate a new position nearby (slightly randomized)
                        angle = random.uniform(0, 2 * math.pi)
                        # Use max of width/length for offset calculation
                        feature_size = max(width, length)
                        offset = random.uniform(feature_size * 0.5, feature_size * 1.5)  # Offset by 0.5-1.5x feature size
                        x_dist = original_x + offset * math.cos(angle)
                        y_dist = original_y + offset * math.sin(angle)
                        
                        logger.debug(f"Feature CT {ct_number} attempt {attempts}: collision detected, trying ({x_dist:.2f}, {y_dist:.2f})")
                
                # If all attempts failed, use the best position anyway
                if not placed:
                    x_dist, y_dist = best_x, best_y
                    half_width = width / 2
                    half_length = length / 2
                    new_box = [x_dist - half_width, y_dist - half_length, x_dist + half_width, y_dist + half_length]
                    occupied_bounding_boxes.append(new_box)
                    logger.debug(f"Feature CT {ct_number} placed at ({x_dist:.2f}, {y_dist:.2f}) after {attempts} failed attempts")
            except ValueError as e:
                # If dimensions can't be retrieved, log the error but don't modify the position
                # This ensures no default sizes are used
                logger.error(f"Error getting dimensions for CT {ct_number}: {str(e)}. Using original position without collision detection.")
                # We don't add this feature to the occupied_bounding_boxes since we don't know its dimensions
            
            # Create modified feature entry with updated coordinates
            modified_feature = f"FeatureEntry={ct_number} {y_dist:.4f} {x_dist:.4f} {z_dist:.4f} {rotation:.4f} {parts[5]} {' '.join(parts[6:])}"
            processed_features.append(modified_feature)
        
        return processed_features
        
    def _add_fed_entry(self, root, index, feature_entry, models_data):
        """
        Add a FED entry from a feature entry without re-validating against the database.
        It trusts that the feature_entry string is already correct.
        """
        try:
            # Parse feature entry - format is like:
            # FeatureEntry=CT_NUM Y_DIST X_DIST Z_DIST ROTATION VALUE FLAGS CAMPAIGN PRESENCE# INDEX) NAME
            parts = feature_entry.split()
            ct_number = int(parts[0].split('=')[1])
            y_dist, x_dist, z_dist, rotation = map(float, parts[1:5])
            
            # Create the FED element
            fed = ET.SubElement(root, "FED", Num=str(index))
            
            # Add required fields
            ET.SubElement(fed, "FeatureCtIdx").text = str(ct_number)
            
            # Add the Value field
            value_elem = ET.SubElement(fed, "Value")
            if len(parts) > 5:
                value_elem.text = str(int(parts[5]))
            else:
                value_elem.text = "0"
            
            ET.SubElement(fed, "OffsetX").text = f"{x_dist:.3f}"
            ET.SubElement(fed, "OffsetY").text = f"{y_dist:.3f}"
            ET.SubElement(fed, "OffsetZ").text = f"{z_dist:.3f}"
            ET.SubElement(fed, "Heading").text = f"{rotation:.1f}"
            
            return True  # Return True when entry is successfully added

        except (ValueError, IndexError) as e:
            logger.error(f"Failed to parse feature entry: '{feature_entry}'. Error: {e}")
            return False
    
    def cleanup_temp_files(self, obj_num):
        """
        Remove temporary files for a specific objective after successful operation.
        
        Args:
            obj_num (int): Objective number to clean up
        
        Returns:
            bool: True if successful, False otherwise
        """
        obj_num_str = f"{obj_num:05d}"
        
        try:
            # Find all temporary directories for this objective
            temp_dirs = list(self.generated_dir.glob(f"OCD_{obj_num_str}-*"))
            
            if not temp_dirs:
                return True
                
            # Delete all temp directories for this objective
            for tmp_dir in temp_dirs:
                try:
                    shutil.rmtree(tmp_dir)
                    logger.info(f"Removed temporary directory: {tmp_dir}")
                except Exception as e:
                    logger.error(f"Failed to remove {tmp_dir}: {e}")
                    return False
            
            return True
        except Exception as e:
            logger.error(f"Error cleaning up temporary files for objective {obj_num}: {e}")
            return False

    def process_features_with_collision_detection(self, features, models_data, placement_radius=500.0):
        """
        Process features with collision detection to avoid overlapping placements.
        
        Args:
            features (list): List of feature entry strings in BMS format
            models_data (DataFrame): DataFrame with model information including dimensions
            placement_radius (float): Maximum radius for feature placement (default: 500.0 feet)
            
        Returns:
            list: Processed feature entries with non-overlapping coordinates
        """
        # The features list contains strings in the following format:
        # FeatureEntry=CT_NUM Y_DIST X_DIST Z_DIST ROTATION VALUE FLAGS CAMPAIGN PRESENCE# INDEX) NAME
        
        logger.info(f"Starting collision detection processing for {len(features)} features")
        
        # Extract coordinates from original features for initial layout
        original_feature_data = []
        for feature_str in features:
            try:
                parts = feature_str.split()
                # Extract the relevant data
                ct_num = int(parts[0].split('=')[1])
                y_dist = float(parts[1])  # North/South coordinate
                x_dist = float(parts[2])  # East/West coordinate
                z_dist = float(parts[3])  # Altitude
                rotation = float(parts[4])  # Heading
                value = parts[5] if len(parts) > 5 else "0000"  # Feature value
                
                # Get remaining parts (everything after the 6th item) for reconstruction
                remaining = ' '.join(parts[6:]) if len(parts) > 6 else ""
                
                # Store original feature data
                original_feature_data.append({
                    'ct_num': ct_num,
                    'y_dist': y_dist,
                    'x_dist': x_dist,
                    'z_dist': z_dist,
                    'rotation': rotation,
                    'value': value,
                    'remaining': remaining
                })
            except Exception as e:
                logger.error(f"Error parsing feature data: {e}, feature: {feature_str}")
                # Add the original feature without modification
                original_feature_data.append({
                    'ct_num': 0,  # Default CT number as fallback
                    'y_dist': 0.0,
                    'x_dist': 0.0,
                    'z_dist': 0.0,
                    'rotation': 0.0,
                    'value': "0000",
                    'remaining': "",
                    'original': feature_str  # Keep the original string for later restoration
                })
        
        # Track occupied spaces with bounding boxes, format: [min_x, min_y, max_x, max_y]
        occupied_bounding_boxes = []
        processed_features = []
        
        # Sort features by size (process larger features first)
        # Estimate size from the models_data if available
        for feature in original_feature_data:
            feature['size_estimate'] = self._get_feature_dimensions(feature['ct_num'], models_data)
        
        # Sort features by size (largest first)
        sorted_features = sorted(
            original_feature_data,
            key=lambda x: x['size_estimate'][0] * x['size_estimate'][1],
            reverse=True
        )
        
        # Process each feature with collision detection
        for feature_idx, feature in enumerate(sorted_features):
            # Skip features with the 'original' key (these had parsing errors)
            if 'original' in feature:
                logger.warning(f"Using original feature data for feature {feature_idx} due to parsing error")
                processed_features.append(feature['original'])
                continue
                
            # Get feature dimensions
            width, length = feature['size_estimate']
            
            # Calculate larger safety buffer based on feature size
            min_buffer = 5.0  # Minimum 5-meter buffer around each feature
            size_based_buffer = max(width, length) * 0.25  # 25% of largest dimension
            safety_buffer = max(min_buffer, size_based_buffer)
            
            # Apply buffer for collision detection purposes
            placement_width = width + safety_buffer
            placement_length = length + safety_buffer
            
            # Keep track of placement attempts
            placed = False
            attempts = 0
            max_attempts = 50  # Maximum attempts before giving up
            
            # Advanced tracking for best fallback position
            best_position = None
            best_overlap_score = float('inf')  # Lower is better (less overlap)
            
            # Get original coordinates as starting point
            original_x = feature['x_dist']
            original_y = feature['y_dist']
            original_z = feature['z_dist']
            original_rotation = feature['rotation']
            
            # Try to use original position first
            half_width = placement_width / 2
            half_length = placement_length / 2
            original_box = [
                original_x - half_width, original_y - half_length, 
                original_x + half_width, original_y + half_length
            ]
            
            # Check if original position is valid (no collision)
            collision, overlap_score = self._check_collision_with_score(original_box, occupied_bounding_boxes)
            if not collision:
                # Original position is fine, keep it
                placed = True
                x, y = original_x, original_y
                
                # Log that we're keeping the original position
                logger.debug(f"Feature {feature_idx} (CT {feature['ct_num']}) - keeping original position: ({x:.2f}, {y:.2f})")
                
                # Use actual dimensions for the final bounding box
                half_width = width / 2
                half_length = length / 2
                final_box = [x - half_width, y - half_length, x + half_width, y + half_length]
                occupied_bounding_boxes.append(final_box)
            else:
                # Original position has collision, try new positions
                # For BMS injection, we'll use the progressive placement strategies
                logger.info(f"Feature {feature_idx} (CT {feature['ct_num']}) - original position has collision, trying new positions")
                
                # Try placement with progressive strategies
                while attempts < max_attempts and not placed:
                    # Placement strategies - similar to MainCode.py but modified for BMS
                    if attempts < 15:
                        # Strategy 1: Quadrant-based placement with randomized distance
                        quadrant = attempts % 4  # 0: NE, 1: SE, 2: SW, 3: NW
                        base_angle = (quadrant * math.pi/2) + random.uniform(-math.pi/4, math.pi/4)
                        # Use distance based on attempt number - start from edge and move inward
                        distance_factor = 0.4 + (0.5 * random.random())  # 40-90% of radius
                        distance = placement_radius * distance_factor
                        x = distance * math.cos(base_angle)
                        y = distance * math.sin(base_angle)
                    elif attempts < 30:
                        # Strategy 2: Grid-based placement with jitter
                        grid_cells = 6  # 6x6 grid
                        grid_x = ((attempts - 15) % grid_cells) - (grid_cells/2 - 0.5)
                        grid_y = ((attempts - 15) // grid_cells) - (grid_cells/2 - 0.5)
                        # Normalize to radius and add jitter
                        grid_scale = placement_radius / (grid_cells/2)
                        jitter = grid_scale * 0.3 * random.random()
                        jitter_angle = random.uniform(0, 2 * math.pi)
                        x = grid_x * grid_scale + jitter * math.cos(jitter_angle)
                        y = grid_y * grid_scale + jitter * math.sin(jitter_angle)
                    else:
                        # Strategy 3: Spiral outward from center
                        t = (attempts - 30) / 20.0  # Parameter for spiral equation
                        spiral_radius = t * placement_radius * 0.9  # Gradually increases radius
                        spiral_angle = t * 10 * math.pi  # Multiple rotations
                        x = spiral_radius * math.cos(spiral_angle)
                        y = spiral_radius * math.sin(spiral_angle)
                    
                    # Calculate bounding box with the feature at the center
                    half_width = placement_width / 2
                    half_length = placement_length / 2
                    new_box = [x - half_width, y - half_length, x + half_width, y + half_length]
                    
                    # Check for boundary constraint - keep fully within radius if possible
                    corner_distances = [
                        math.sqrt((x - half_width)**2 + (y - half_length)**2),  # bottom-left
                        math.sqrt((x - half_width)**2 + (y + half_length)**2),  # top-left
                        math.sqrt((x + half_width)**2 + (y - half_length)**2),  # bottom-right
                        math.sqrt((x + half_width)**2 + (y + half_length)**2)   # top-right
                    ]
                    max_corner_distance = max(corner_distances)
                    
                    # Only consider positions where feature is fully within radius
                    # But relax this constraint in later attempts
                    within_radius = max_corner_distance <= placement_radius or attempts >= 30
                    
                    # Check if this position collides with existing features
                    collision, overlap_score = self._check_collision_with_score(new_box, occupied_bounding_boxes)
                    
                    # Track best position even if there's collision
                    if within_radius and (best_position is None or overlap_score < best_overlap_score):
                        best_position = (x, y, new_box)
                        best_overlap_score = overlap_score
                    
                    if not collision and within_radius:
                        # Valid placement found - no collision and within radius
                        placed = True
                        
                        # Use the ACTUAL dimensions for the final bounding box (no safety buffer)
                        half_width = width / 2
                        half_length = length / 2
                        final_box = [x - half_width, y - half_length, x + half_width, y + half_length]
                        occupied_bounding_boxes.append(final_box)
                        
                        logger.debug(f"Feature {feature_idx} (CT {feature['ct_num']}) placed at ({x:.2f}, {y:.2f}) without collision (attempt {attempts+1})")
                    else:
                        # Try again
                        attempts += 1
                
                # If all attempts failed, use the best position found with overlap warning
                if not placed:
                    # Use the best position we found (least overlap)
                    if best_position is None:
                        # Fallback to original position if we couldn't find a better one
                        logger.warning(f"Failed to find any valid position for feature {feature_idx} (CT {feature['ct_num']}) - using original position")
                        x, y = original_x, original_y
                    else:
                        x, y, overlap_box = best_position
                    
                    # Use actual dimensions for the final bounding box (no safety buffer)
                    half_width = width / 2
                    half_length = length / 2
                    final_box = [x - half_width, y - half_length, x + half_width, y + half_length]
                    occupied_bounding_boxes.append(final_box)
                    
                    # Log warning for failed placements
                    failure_msg = f"WARNING: Feature {feature_idx} (CT {feature['ct_num']}) placed with COLLISION at ({x:.2f}, {y:.2f}) after {attempts} failed attempts - overlap score: {best_overlap_score:.2f}"
                    logger.warning(failure_msg)  # Log as warning
            
            # Construct the updated feature string with new coordinates
            # Keep the original Z and rotation values
            feature_string = f"FeatureEntry={feature['ct_num']} {y:.3f} {x:.3f} {original_z:.3f} {original_rotation:.3f} {feature['value']}"
            
            # Add remaining parts if available
            if feature['remaining']:
                feature_string += " " + feature['remaining']
                
            processed_features.append(feature_string)
            
        logger.info(f"Completed collision detection processing: {len(processed_features)} features processed")
        return processed_features
    
    def _get_feature_dimensions(self, ct_num, models_data, default_size=(10.0, 10.0)):
        """
        Get the dimensions of a feature based on its CT number from models_data.
        
        Args:
            ct_num (int): CT number of the feature
            models_data (DataFrame): DataFrame with model information
            default_size (tuple): Default dimensions (width, length) if not found
            
        Returns:
            tuple: (width, length) dimensions of the feature
        """
        try:
            # Find the model data for this CT number
            model_rows = models_data[models_data["CTNumber"] == ct_num]
            
            # If we have data and the required columns exist, use actual dimensions
            if not model_rows.empty and "Width" in model_rows.columns and "Length" in model_rows.columns:
                width = float(model_rows.iloc[0]["Width"])
                length = float(model_rows.iloc[0]["Length"])
                
                # Apply some validation to prevent zero or negative dimensions
                width = max(width, 5.0)  # Minimum width of 5 meters
                length = max(length, 5.0)  # Minimum length of 5 meters
                
                logger.debug(f"Found dimensions for CT {ct_num}: Width={width:.2f}, Length={length:.2f}")
                return width, length
            else:
                # Use default dimensions if not found
                logger.debug(f"No dimensions found for CT {ct_num}, using defaults: {default_size}")
                return default_size
        except Exception as e:
            logger.error(f"Error getting feature dimensions for CT {ct_num}: {e}")
            return default_size
    
    def _check_collision_with_score(self, new_box, existing_boxes):
        """
        Check for collision between a proposed bounding box and existing boxes.
        Returns both a collision boolean and an overlap score (0 = no overlap, higher = more overlap).
        
        Args:
            new_box (list): The new bounding box [min_x, min_y, max_x, max_y]
            existing_boxes (list): List of existing bounding boxes
            
        Returns:
            tuple: (collision_detected, overlap_score)
        """
        # If no existing boxes, no collision
        if not existing_boxes:
            return False, 0.0
        
        # Unpack the coordinates for easier reading
        new_min_x, new_min_y, new_max_x, new_max_y = new_box
        
        # Calculate area of new box
        new_width = new_max_x - new_min_x
        new_height = new_max_y - new_min_y
        new_area = new_width * new_height
        
        # Ensure the box is valid (min < max)
        if new_min_x >= new_max_x or new_min_y >= new_max_y:
            logger.warning(f"Invalid bounding box detected: {new_box}. Treating as collision.")
            return True, float('inf')  # Invalid box - treat as maximum collision
        
        # Variables to track total overlap
        total_overlap_area = 0.0
        max_overlap_ratio = 0.0  # Ratio of overlap compared to box size
        has_collision = False
        
        # Check if the new box overlaps with any existing box
        for idx, box in enumerate(existing_boxes):
            # Validate the existing box
            if len(box) != 4:
                logger.warning(f"Invalid box format at index {idx}: {box}. Skipping.")
                continue
                
            try:
                ex_min_x, ex_min_y, ex_max_x, ex_max_y = box
                
                # Check for non-overlap first (AABB test)
                if (new_min_x > ex_max_x or  # new is to the right of existing
                    new_max_x < ex_min_x or  # new is to the left of existing
                    new_min_y > ex_max_y or  # new is above existing
                    new_max_y < ex_min_y):   # new is below existing
                    # No overlap with this box
                    continue
                
                # If we get here, there's an overlap - calculate its area
                overlap_width = min(new_max_x, ex_max_x) - max(new_min_x, ex_min_x)
                overlap_height = min(new_max_y, ex_max_y) - max(new_min_y, ex_min_y)
                overlap_area = overlap_width * overlap_height
                
                # Skip if overlap is negligible (floating point error)
                if overlap_area < 0.01:
                    continue
                    
                # We have a real collision
                has_collision = True
                total_overlap_area += overlap_area
                
                # Calculate overlap ratio relative to new box area
                overlap_ratio = overlap_area / new_area
                max_overlap_ratio = max(max_overlap_ratio, overlap_ratio)
                
                # Early exit if we have a severe overlap (optimization)
                if max_overlap_ratio > 0.5:
                    return True, max_overlap_ratio
                    
            except Exception as e:
                logger.error(f"Error in collision detection with box {box}: {e}")
                # Be conservative - treat as collision if there's an error
                return True, 1.0
        
        # Additionally, check proximity to other boxes (not just overlap)
        for box in existing_boxes:
            try:
                ex_min_x, ex_min_y, ex_max_x, ex_max_y = box
                
                # Calculate center points
                new_center_x = (new_min_x + new_max_x) / 2
                new_center_y = (new_min_y + new_max_y) / 2
                ex_center_x = (ex_min_x + ex_max_x) / 2
                ex_center_y = (ex_min_y + ex_max_y) / 2
                
                # Distance between centers
                center_distance = math.sqrt((new_center_x - ex_center_x)**2 + (new_center_y - ex_center_y)**2)
                
                # Minimum distance needed for no overlap
                new_radius = max(new_width, new_height) / 2
                ex_radius = max(ex_max_x - ex_min_x, ex_max_y - ex_min_y) / 2
                min_distance = new_radius + ex_radius
                
                # If centers are too close (as a ratio of min_distance)
                proximity_ratio = min_distance / max(center_distance, 0.001) - 1.0
                if proximity_ratio > 0:
                    # Add to the score based on proximity (closer = higher score)
                    max_overlap_ratio = max(max_overlap_ratio, proximity_ratio * 0.5)
                    
                    # If very close, count as collision
                    if proximity_ratio > 0.2:  # Within 20% of minimum distance
                        has_collision = True
            except Exception as e:
                logger.warning(f"Error checking proximity: {e}")
        
        # Return final collision result and score
        return has_collision, max_overlap_ratio
    
    def create_and_inject_objective(self, obj_num, ct_num, name, obj_type, features, models_data, fields=None, reset_pd=True, selection_type="GeoJson"):
        """
        Create or update an objective and inject features in a single operation with one backup.
        
        Args:
            obj_num (int): Objective number
            ct_num (int): CT number
            name (str): Objective name
            obj_type (int): Objective type
            features (list): List of feature entry strings
            models_data (DataFrame): DataFrame with model information
            fields (dict): Field values for the objective
            reset_pd (bool): Whether to reset PHD and PDX files
            selection_type (str): Type of selection ("GeoJson" or "Random Selection")
            
        Returns:
            dict: Result dictionary with status and details
        """
        # Validate and convert objective type
        try:
            obj_type = int(obj_type)  # Ensure obj_type is always an integer
            logger.info(f"Creating objective {obj_num} with type {obj_type}")
            logger.debug(f"BmsInjector creating objective {obj_num} with type {obj_type}")
        except (ValueError, TypeError):
            error_msg = f"Invalid objective type: {obj_type}, must be a number"
            logger.error(error_msg)
            return {"status": "error", "message": error_msg}
        
        # Note: Overwrite confirmation is handled in MainCode.py before this method is called
            
        # Format objective number with leading zeros
        obj_num_str = f"{obj_num:05d}"
        
        # Determine if we're creating or updating
        obj_dir = self.objective_dir / f"OCD_{obj_num_str}"
        creating = not obj_dir.exists()
        
        # At this point, all confirmations are complete - proceed with operation
        # Only create backups if the backup setting is enabled
        if self.backup:
            # Create a backup of the CT file (only once)
            backup_result = self._backup_ct_file()
            if backup_result is None and self.backup:
                logger.warning("Failed to create CT file backup but proceeding with operation")
            
            # If updating an existing objective, backup its files first (only once)
            if not creating:
                backup_result = self._backup_objective_files(obj_num)
                if backup_result is None and self.backup:
                    logger.warning(f"Failed to create objective {obj_num} backup but proceeding with operation")
        else:
            logger.debug(f"Skipping backups due to disabled backup setting")

        
        # First create the objective without backing up again (passing backup=False)
        # We need to reimplement the core functionality without calling create_objective
        # to avoid the duplicate backup of the CT file
        # Only set up backup paths if backup_features is enabled
        if self.backup_features:
            # Define timestamp for backup paths
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            tmp_dir = self.generated_dir / f"OCD_{obj_num_str}-{timestamp}"
            os.makedirs(tmp_dir, exist_ok=True)
            logger.debug(f"Created backup directory for generated features: {tmp_dir}")
        else:
            # Skip all backup operations
            tmp_dir = None
            logger.debug("Skipping all backup operations - backup_features disabled")
        
        # Create objective directory if needed
        os.makedirs(obj_dir, exist_ok=True)
        
        # Initialize combined fields dictionary
        combined_fields = {}

        # First, add template values for this specific objective type (base template)
        template_fields = self.objective_templates.get(str(obj_type), {})
        for key, value in template_fields.items():
            combined_fields[key] = str(value)  # Ensure template values are strings
        
        # Then override with provided fields if any
        if fields:
            for key, value in fields.items():
                combined_fields[key] = str(value)  # Ensure all values are strings
        
        # Log for debugging
        logger.debug(f"Creating objective type {obj_type} with template fields: {template_fields}")
        logger.debug(f"Final combined fields: {combined_fields}")
        
        # Create OCD file and its temp copy
        ocd_file = obj_dir / f"OCD_{obj_num_str}.XML"
        success = self._create_ocd_file(ocd_file, obj_num, ct_num, name, combined_fields)
        # Create a copy in the Generated folder if backup_features is enabled
        if self.backup_features and tmp_dir is not None:
            tmp_ocd_file = tmp_dir / f"OCD_{obj_num_str}.XML"
            self._create_ocd_file(tmp_ocd_file, obj_num, ct_num, name, combined_fields)
        
        if not success:
            error_msg = f"Failed to create OCD file for objective {obj_num}"
            logger.error(error_msg)
            return {"status": "error", "message": error_msg, "obj_num": obj_num}
        
        # Create/reset PHD and PDX files if requested
        if creating or reset_pd:
            pdx_file = obj_dir / f"PDX_{obj_num_str}.XML"
            phd_file = obj_dir / f"PHD_{obj_num_str}.XML"
            
            self._create_pd_file(pdx_file, "PDRecords", "PD")
            self._create_pd_file(phd_file, "PHDRecords", "PHD")
            # Create copies in the Generated folder if backup_features is enabled
            if self.backup_features and tmp_dir is not None:
                tmp_pdx_file = tmp_dir / f"PDX_{obj_num_str}.XML"
                tmp_phd_file = tmp_dir / f"PHD_{obj_num_str}.XML"
                self._create_pd_file(tmp_pdx_file, "PDRecords", "PD")
                self._create_pd_file(tmp_phd_file, "PHDRecords", "PHD")
        
        # Create empty FED file ready for injection
        fed_file = obj_dir / f"FED_{obj_num_str}.XML"
        self._create_fed_file(fed_file)
        # Create a copy in the Generated folder if backup_features is enabled
        if self.backup_features and tmp_dir is not None:
            tmp_fed_file = tmp_dir / f"FED_{obj_num_str}.XML"
            self._create_fed_file(tmp_fed_file)
        
        # Update CT file with objective data, but don't create another backup
        # Pass obj_num to properly set the EntityIdx in the CT file
        if not self._update_ct_file(ct_num, obj_type, name, backup=False, obj_num=obj_num):
            error_msg = f"Failed to update CT file for objective {obj_num}"
            logger.warning(error_msg)
            return {"status": "error", "message": error_msg, "obj_num": obj_num}
        
        # Verify the CT file was updated with the correct type
        try:
            tree = ET.parse(self.ct_file)
            root = tree.getroot()
            for ct in root.findall("CT"):
                if int(ct.get("Num")) == ct_num:
                    type_elem = ct.find("Type")
                    if type_elem is not None:
                        if type_elem.text != str(obj_type):
                            logger.warning(f"CT file verification failed: Type={type_elem.text}, expected {obj_type}")
                            # Try to fix it
                            type_elem.text = str(obj_type)
                            self._write_xml(tree, self.ct_file)
                            logger.info(f"Fixed Type field to: {obj_type}")
                        else:
                            logger.info(f"CT file verification passed: Type={type_elem.text}")
                    else:
                        # Type element is missing, add it
                        logger.warning("Type element is missing, adding it")
                        type_elem = ET.SubElement(ct, "Type")
                        type_elem.text = str(obj_type)
                        self._write_xml(tree, self.ct_file)
                        logger.info(f"Added Type field with value: {obj_type}")
        except Exception as e:
            logger.error(f"Error verifying CT file update: {e}")
        
        # Then inject features without creating another backup
        try:
            # Conditional collision detection based on selection type
            if selection_type == "Random Selection":
                # Apply collision detection for random placement
                logger.info(f"Processing {len(features)} features with collision detection (Random Selection mode)")
                processed_features = self.process_features_with_collision_detection(features, models_data)
                logger.info(f"Processed {len(processed_features)} features with collision detection")
            else:
                # Preserve original coordinates for GeoJson placement
                logger.info(f"Processing {len(features)} features while preserving original coordinates (GeoJson mode)")
                processed_features = features  # Use features as-is without coordinate modification
                logger.info(f"Processed {len(processed_features)} features while preserving original coordinates")
            
            # Parse existing FED file
            tree = ET.parse(str(fed_file))
            root = tree.getroot()
            
            # Clear existing entries
            for child in list(root):
                root.remove(child)
            
            # Process each feature entry and add to FED file
            for i, feature in enumerate(processed_features):
                self._add_fed_entry(root, i, feature, models_data)
            
            # Write updated XML to both locations
            # Write updated XML to the main FED file
            self._write_xml(tree, fed_file)
            # Also write to the Generated folder and save debug info if backup_features is enabled
            if self.backup_features and tmp_dir is not None:
                self._write_xml(tree, tmp_fed_file)
                
                # Also save features to a text file for debugging
                with open(tmp_dir / f"Features_{obj_num_str}.txt", "w") as f:
                    f.write(f"# Features for Objective {obj_num}\n\n")
                    for feature in processed_features:
                        f.write(f"{feature}\n")
                logger.info(f"Backed up features to {tmp_dir}")
            else:
                logger.debug("Skipping feature backup due to disabled backup_features setting")
                    
            # Operation completed successfully
            return {
                "status": "success", 
                "message": f"Successfully created and injected objective {obj_num}",
                "obj_num": obj_num,
                "ct_num": ct_num,
                "feature_count": len(processed_features)
            }
        except Exception as e:
            error_msg = f"Error injecting features: {e}"
            logger.error(error_msg)
            return {"status": "error", "message": error_msg, "obj_num": obj_num}

if __name__ == "__main__":
    # Test code
    bms_path = r"C:\Falcon BMS 4.35"
    injector = BmsInjector(bms_path)
    
    # Test if CT is objective
    logger.info(f"Is CT 9 an objective: {injector.is_objective_ct(9)}")
    
    # Test if objective exists
    logger.info(f"Does objective 1 exist: {injector.objective_exists(1)}")
    
    # Print templates
    logger.info(f"Objective templates: {len(injector.objective_templates)}")