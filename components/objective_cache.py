"""
Objective Cache Module for BMS Building Generator

This module handles caching of BMS objective data to improve performance of the
BMS injection window. It stores parsed CT and objective data in JSON format and
provides methods to access and update this data.
"""

import os
import json
import time
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple

# Import the json path handler
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.json_path_handler import load_json, save_json, JsonFiles, get_json_path
    
# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("objective_cache")

class ObjectiveCache:
    """Class for handling cached BMS objective data."""
    
    def __init__(self):
        # Initialize cache data structure
        self.cache_data = {
            "timestamp": 0,
            "bms_version": "",
            "ct_data": {},
            "objective_data": {},
            "objective_templates": {},
            "user_templates": {}
        }
        
        # Load cache if available
        self._load_cache()
        
    def _load_cache(self) -> bool:
        """Load cache from file."""
        try:
            # Load cache from file using json_path_handler
            loaded_data = load_json(JsonFiles.OBJECTIVE_CACHE)
            
            if loaded_data:
                self.cache_data = loaded_data
                logger.info("Loaded objective cache successfully")
                return True
            else:
                logger.warning("No cache file found or empty cache")
                return False
        except Exception as e:
            logger.error(f"Error loading cache: {e}")
            return False
            
    def save_cache(self) -> bool:
        """Save cache to file."""
        try:
            # Update timestamp
            self.cache_data["timestamp"] = int(time.time())
            
            # Save cache to file using json_path_handler
            success = save_json(JsonFiles.OBJECTIVE_CACHE, self.cache_data, indent=2)
            
            if success:
                logger.info("Saved objective cache successfully")
                return True
            else:
                logger.error("Failed to save objective cache")
                return False
        except Exception as e:
            logger.error(f"Error saving cache: {e}")
            return False
    
    def clear_cache(self) -> bool:
        """Clear the cache data and remove the cache file."""
        try:
            self.cache_data = {
                "timestamp": 0,
                "bms_version": "",
                "ct_data": {},
                "objective_data": {},
                "objective_templates": {},
                "user_templates": {}
            }
            
            # Remove cache file using json_path_handler
            cache_file_path = get_json_path(JsonFiles.OBJECTIVE_CACHE)
            if cache_file_path.exists():
                cache_file_path.unlink()
                logger.info(f"Removed cache file: {cache_file_path}")
            
            return True
        except Exception as e:
            logger.error(f"Error clearing cache: {e}")
            return False
    
    def is_cache_valid(self, max_age: int = 86400, bms_version: str = None) -> bool:
        """
        Check if the cache is valid based on age and BMS version.
        
        Args:
            max_age: Maximum age of cache in seconds (default: 24 hours)
            bms_version: BMS version to compare with cached version
        
        Returns:
            True if cache is valid, False otherwise
        """
        # Check if cache exists
        if not self.cache_data:
            return False
        
        # Check cache age
        current_time = int(time.time())
        cache_age = current_time - self.cache_data.get("timestamp", 0)
        if cache_age > max_age:
            logger.info(f"Cache is too old ({cache_age} seconds)")
            return False
        
        # Check BMS version if provided
        if bms_version and bms_version != self.cache_data.get("bms_version", ""):
            logger.info(f"BMS version changed: {self.cache_data.get('bms_version', '')} -> {bms_version}")
            return False
        
        return True
    
    def get_ct_data(self, ct_num: int = None) -> Any:
        """
        Get cached CT data.
        
        Args:
            ct_num: Optional specific CT number to retrieve
        
        Returns:
            Dictionary of all CT data or specific CT data
        """
        ct_data = self.cache_data.get("ct_data", {})
        
        if ct_num is not None:
            return ct_data.get(str(ct_num))
        
        return ct_data
    
    def set_ct_data(self, ct_data: Dict, ct_num: int = None) -> None:
        """
        Set CT data in the cache.
        
        Args:
            ct_data: CT data to store
            ct_num: Optional specific CT number
        """
        if ct_num is not None:
            self.cache_data.setdefault("ct_data", {})[str(ct_num)] = ct_data
        else:
            self.cache_data["ct_data"] = ct_data
    
    def get_objective_data(self, obj_num: int = None) -> Any:
        """
        Get cached objective data.
        
        Args:
            obj_num: Optional specific objective number to retrieve
        
        Returns:
            Dictionary of all objective data or specific objective data
        """
        obj_data = self.cache_data.get("objective_data", {})
        
        if obj_num is not None:
            return obj_data.get(str(obj_num))
        
        return obj_data
    
    def set_objective_data(self, obj_data: Dict, obj_num: int = None) -> None:
        """
        Set objective data in the cache.
        
        Args:
            obj_data: Objective data to store
            obj_num: Optional specific objective number
        """
        if obj_num is not None:
            self.cache_data.setdefault("objective_data", {})[str(obj_num)] = obj_data
        else:
            self.cache_data["objective_data"] = obj_data
    
    def get_objective_templates(self, obj_type: int = None) -> Any:
        """
        Get cached objective templates.
        
        Args:
            obj_type: Optional specific objective type
        
        Returns:
            Dictionary of all templates or specific template
        """
        templates = self.cache_data.get("objective_templates", {})
        
        if obj_type is not None:
            return templates.get(str(obj_type))
        
        return templates
    
    def set_objective_templates(self, templates: Dict, obj_type: int = None) -> None:
        """
        Set objective templates in the cache. Ensures all values are stored as strings.
        
        Args:
            templates: Templates to store
            obj_type: Optional specific objective type
        """
        # Convert all template values to strings
        def convert_to_strings(template_dict):
            return {k: str(v) for k, v in template_dict.items()}
            
        if obj_type is not None:
            # Set a specific template with string values
            self.cache_data.setdefault("objective_templates", {})[str(obj_type)] = convert_to_strings(templates)
        else:
            # Set all templates with string values
            string_templates = {}
            for t_type, t_values in templates.items():
                string_templates[str(t_type)] = convert_to_strings(t_values)
            self.cache_data["objective_templates"] = string_templates
    
    def get_user_templates(self, obj_type: int = None) -> Any:
        """
        Get user-defined templates.
        
        Args:
            obj_type: Optional specific objective type
        
        Returns:
            Dictionary of all user templates or specific user template
        """
        templates = self.cache_data.get("user_templates", {})
        
        if obj_type is not None:
            return templates.get(str(obj_type))
        
        return templates
    
    def set_user_templates(self, templates: Dict, obj_type: int = None) -> None:
        """
        Set user-defined templates in the cache. Ensures all values are stored as strings.
        
        Args:
            templates: Templates to store
            obj_type: Optional specific objective type
        """
        # Convert all template values to strings
        def convert_to_strings(template_dict):
            return {k: str(v) for k, v in template_dict.items()}
            
        if obj_type is not None:
            # Set a specific template with string values
            self.cache_data.setdefault("user_templates", {})[str(obj_type)] = convert_to_strings(templates)
        else:
            # Set all templates with string values
            string_templates = {}
            for t_type, t_values in templates.items():
                string_templates[str(t_type)] = convert_to_strings(t_values)
            self.cache_data["user_templates"] = string_templates
    
    def set_bms_version(self, version: str) -> None:
        """
        Set BMS version in the cache.
        
        Args:
            version: BMS version string
        """
        self.cache_data["bms_version"] = version
    
    def get_bms_version(self) -> str:
        """
        Get BMS version from the cache.
        
        Returns:
            BMS version string
        """
        return self.cache_data.get("bms_version", "")

# Global cache instance
cache = ObjectiveCache() 