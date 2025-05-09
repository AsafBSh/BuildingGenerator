import json
import os
import customtkinter as Ctk
import tkinter as tk
import sys
import shutil
from pathlib import Path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from utils.json_path_handler import load_json, save_json, get_json_path, JsonFiles
import logging

logger = logging.getLogger(__name__)

# Define the standard location for ValuesDic.json
VALUES_DICTIONARY_FILE = JsonFiles.VALUES_DICTIONARY


class ValuesDictionary(tk.Toplevel):
    """
    Values Dictionary window for managing feature type values.
    
    This class provides a UI for viewing and editing the values assigned to different
    feature types in the BMS Building Generator. Values are stored in the ValuesDic.json
    file located in the data_components directory.
    """
    
    def __init__(self, filepath=None, callback=None):
        """
        Initialize the Values Dictionary window.
        
        Args:
            filepath (str, optional): Path to the JSON file. Defaults to None.
            callback (function, optional): Function to call on close. Defaults to None.
        """
        super().__init__()
        self.filepath = filepath or self._get_default_filepath()
        self.callback = callback
        
        # Configure window appearance
        self.title("Values Dictionary")
        self.geometry("1000x600")
        self.configure(bg="#E9EFF2")  # Light blue-gray background
        self.iconbitmap("Assets/icon_128.ico")
        self.resizable(True, True)
        self.minsize(850, 600)
        
        # Define fonts and colors - using the BMS app blue theme
        self.title_font = Ctk.CTkFont(family="Inter", size=16, weight="bold")
        self.label_font = Ctk.CTkFont(family="Inter", size=13)
        self.entry_font = Ctk.CTkFont(family="Inter", size=12)
        self.button_font = Ctk.CTkFont(family="Inter", size=14, weight="bold")
        self.primary_color = "#2D7FB8"       # BMS blue
        self.secondary_color = "#A1B9D0"     # Light BMS blue
        self.accent_color = "#8DBBE7"        # BMS accent blue
        self.text_color = "#000000"          # Black text
        self.hover_color = "#7A92A9"         # Darker blue for hover
        self.header_color = "#A1B9D0"        # BMS lighter blue
        self.bg_color = "#E7F3F7"            # Very light blue background
        self.row_alt_color = "#F3F8FB"       # Subtle row alternating color
        
        # Create a protocol for window close
        self.protocol("WM_DELETE_WINDOW", self.on_close)
        
        # Create main frames
        self.create_layout()
        
        # Initialize values dictionary
        self.initialize_values_dict()
        
        # Create UI elements
        self.create_ui_elements()
        
    def create_layout(self):
        """Create the main layout frames"""
        # Create a header frame
        self.header_frame = Ctk.CTkFrame(self, fg_color=self.header_color, corner_radius=0, height=60)
        self.header_frame.pack(side="top", fill="x")
        self.header_frame.pack_propagate(False)
        
        # Add title to header
        Ctk.CTkLabel(
            self.header_frame, 
            text="Building Features Value Configuration", 
            font=Ctk.CTkFont(family="Inter", size=18, weight="bold"),
            text_color=self.text_color
        ).pack(side="left", padx=20, pady=15)
        
        # Create a content frame with scrollable area
        self.content_frame = Ctk.CTkFrame(self, fg_color=self.bg_color, corner_radius=0)
        self.content_frame.pack(side="top", fill="both", expand=True, padx=10, pady=10)
        
        # Create scrollable frame for the entries
        self.scrollable_frame = Ctk.CTkScrollableFrame(
            self.content_frame,
            fg_color=self.bg_color,
            corner_radius=10,
            label_text="Feature Values (0-100)",
            label_font=self.title_font,
            label_fg_color=self.secondary_color
        )
        self.scrollable_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Create frame for grid layout inside scrollable frame
        self.grid_frame = Ctk.CTkFrame(self.scrollable_frame, fg_color="transparent")
        self.grid_frame.pack(fill="both", expand=True)
        
        # Create footer with buttons
        self.footer_frame = Ctk.CTkFrame(self, fg_color=self.bg_color, corner_radius=0, height=70)
        self.footer_frame.pack(side="bottom", fill="x", padx=10, pady=10)
        
        # Add save button
        self.save_button = Ctk.CTkButton(
            self.footer_frame,
            text="Save Values",
            command=self.save,
            font=self.button_font,
            fg_color=self.accent_color,
            hover_color=self.hover_color,
            corner_radius=8,
            height=40,
            width=180,
            border_width=0,
            text_color=self.text_color
        )
        self.save_button.pack(side="left", padx=20, pady=10)
        
        # Add reset to default button
        self.default_button = Ctk.CTkButton(
            self.footer_frame,
            text="Reset to Default",
            command=self.default,
            font=self.button_font,
            fg_color=self.accent_color,
            hover_color=self.hover_color,
            corner_radius=8,
            height=40,
            width=180,
            border_width=0,
            text_color=self.text_color
        )
        self.default_button.pack(side="right", padx=20, pady=10)
    
    def migrate_legacy_files(self):
        """
        Check for and migrate any legacy ValuesDic.json files to the standard location.
        
        This ensures backward compatibility with older installations that might have
        the file in the root directory rather than data_components.
        """
        try:
            # Check for ValuesDic.json in the root directory
            root_file = Path(__file__).parent / "ValuesDic.json"
            if root_file.exists():
                logger.info(f"Found legacy ValuesDic.json in root directory: {root_file}")
                
                # Ensure data_components directory exists
                target_path = get_json_path(VALUES_DICTIONARY_FILE)
                target_path.parent.mkdir(exist_ok=True)
                
                # Only migrate if the target file doesn't exist already
                if not target_path.exists():
                    logger.info(f"Migrating legacy ValuesDic.json to: {target_path}")
                    shutil.copy2(root_file, target_path)
                    logger.info("Migration successful")
                else:
                    logger.info(f"Target file already exists: {target_path}, skipping migration")
        except Exception as e:
            logger.warning(f"Error during legacy file migration: {e}")

    def initialize_values_dict(self):
        """Load existing values or create default values"""
        try:
            # Try to load the values dictionary from file
            self.values_dict = load_json(VALUES_DICTIONARY_FILE, default=None)
            
            # If dictionary is not found or empty, use defaults
            if not self.values_dict:
                logger.info("No values dictionary found, creating defaults")
                self.default_values()
                # Save the new dictionary
                self.save_values_to_file()
            else:
                # Ensure all values are stored as integers for consistency
                self.validate_values_types()
            
        except Exception as e:
            logger.warning(f"Error loading ValuesDic.json: {e}")
            # Create default values and save them
            self.default_values()
            self.save_values_to_file()
    
    def validate_values_types(self):
        """Ensure all values in the dictionary are integers"""
        try:
            # First, convert string keys to integers if needed
            updated_dict = {}
            for key, value_data in list(self.values_dict.items()):
                # Always convert string keys to integers
                if isinstance(key, str):
                    try:
                        numeric_key = int(key)
                        updated_dict[numeric_key] = value_data
                    except ValueError:
                        # If key can't be converted to int, skip it
                        logger.warning(f"Skipping non-numeric key: {key}")
                        continue
                else:
                    updated_dict[key] = value_data
            
            # Replace the dictionary with the updated one
            self.values_dict = updated_dict
            
            # Now validate that all values are integers
            for key, value_data in list(self.values_dict.items()):
                if "Value" in value_data and not isinstance(value_data["Value"], int):
                    try:
                        self.values_dict[key]["Value"] = int(value_data["Value"])
                    except (ValueError, TypeError):
                        logger.warning(f"Invalid value for key {key}, resetting to 0")
                        self.values_dict[key]["Value"] = 0
        except Exception as e:
            logger.warning(f"Error validating value types: {e}")
    
    def save_values_to_file(self):
        """Save values dictionary to file"""
        success = save_json(VALUES_DICTIONARY_FILE, self.values_dict)
        if success:
            logger.info(f"Successfully saved values to {VALUES_DICTIONARY_FILE}")
        else:
            logger.error(f"Failed to save values to {VALUES_DICTIONARY_FILE}")
            
    def create_ui_elements(self):
        """Create all the UI elements for the ValuesDictionary window"""
        self.entries = {}
        self.type_labels = {}  # Store the actual type names for each key
        
        # Clear any existing widgets in the grid frame
        for widget in self.grid_frame.winfo_children():
            widget.destroy()
        
        # Ensure we're iterating through integer keys
        sorted_items = sorted(self.values_dict.items(), key=lambda x: x[0] if isinstance(x[0], int) else int(x[0]))
        
        # Create column headers
        col_span = 4  # Number of entry columns
        headers = ["Military", "Infrastructure", "Buildings", "Markers"]
        
        for i, header in enumerate(headers):
            header_frame = Ctk.CTkFrame(self.grid_frame, fg_color=self.primary_color, corner_radius=6, height=30)
            header_frame.grid(row=0, column=i*2, columnspan=2, padx=5, pady=(0, 10), sticky="ew")
            header_frame.grid_propagate(False)
            
            Ctk.CTkLabel(
                header_frame,
                text=header,
                font=Ctk.CTkFont(family="Inter", size=14, weight="bold"),
                text_color="#FFFFFF"
            ).pack(padx=5, pady=3)
        
        # Calculate items per column for balanced layout
        items_per_col = max(5, (len(sorted_items) + col_span - 1) // col_span)
        
        # Set up columns configuration based on feature categories
        categories = {
            "Military": [4, 9, 10, 14, 15, 26, 28, 29, 32, 33, 35, 57, 58],  # Military related
            "Infrastructure": [2, 6, 11, 13, 16, 17, 18, 20, 23, 30, 31, 43, 48, 51, 53, 54, 56, 60],  # Infrastructure
            "Buildings": [1, 3, 5, 7, 8, 12, 19, 21, 22, 34, 38, 39, 40, 42, 44, 45, 52, 59, 62, 63, 66],  # Buildings
            "Markers": [24, 25, 27, 36, 37, 41, 46, 47, 49, 50, 55, 61, 64, 65, 67, 68]  # Markers/Misc
        }
        
        # Create a lookup for category column placement
        category_cols = {}
        for col_idx, (category, type_ids) in enumerate(categories.items()):
            for type_id in type_ids:
                category_cols[type_id] = col_idx
        
        # Track rows per column to maintain balanced layout
        col_rows = [1, 1, 1, 1]  # Start at 1 because row 0 has headers
        
        # Place items in appropriate columns
        for i, (key, value) in enumerate(sorted_items):
            # Use the integer representation of the key for display
            display_key = key if isinstance(key, int) else int(key)
            type_name = value["Type"]
            
            # Store the type name for this key
            self.type_labels[display_key] = type_name
            
            # Determine which column to place this item in
            col_idx = category_cols.get(display_key, display_key % col_span)
            row_idx = col_rows[col_idx]
            col_rows[col_idx] += 1
            
            # Calculate grid position
            grid_col = col_idx * 2
            grid_row = row_idx
            
            # Create container frame for each entry
            entry_frame = Ctk.CTkFrame(self.grid_frame, fg_color="transparent")
            entry_frame.grid(row=grid_row, column=grid_col, columnspan=2, padx=5, pady=2, sticky="ew")
            
            # Create label with type name
            label = Ctk.CTkLabel(
                entry_frame,
                text=f"{display_key}. {type_name}",
                font=self.label_font,
                anchor="w",
                width=150,
                text_color=self.text_color
            )
            label.grid(row=0, column=0, sticky="w", padx=(5, 10))
            
            # Create value entry
            entry = Ctk.CTkEntry(
                entry_frame,
                width=50,
                font=self.entry_font,
                border_width=1,
                border_color=self.secondary_color,
                fg_color="white",
                corner_radius=5,
                text_color=self.text_color
            )
            entry.insert(0, value["Value"])
            entry.grid(row=0, column=1, padx=(0, 5), pady=5, sticky="e")
            
            # Store the entry with the integer key to ensure consistency
            self.entries[display_key] = entry
            
            # Alternate row backgrounds for better readability
            if grid_row % 2 == 0:
                entry_frame.configure(fg_color=self.row_alt_color)

    def save(self):
        """
        Save the values_dict to the Json File.
        The values will be bounded between 0 and 100.
        """
        for i, (key, entry) in enumerate(self.entries.items()):
            try:
                value = int(entry.get())
                # Make sure we're using integer keys to match the dictionary structure
                dict_key = int(key) if isinstance(key, str) else key
                
                # Preserve the Type name if we have it stored
                if dict_key in self.values_dict:
                    type_name = self.values_dict[dict_key]["Type"]
                elif hasattr(self, 'type_labels') and dict_key in self.type_labels:
                    type_name = self.type_labels[dict_key]
                else:
                    # Fallback to a generic name only if we can't find the original
                    type_name = f"Type_{dict_key}"
                
                if value < 0:
                    self.values_dict[dict_key] = {"Type": type_name, "Value": 0}
                elif value > 100:
                    self.values_dict[dict_key] = {"Type": type_name, "Value": 100}
                else:
                    self.values_dict[dict_key] = {"Type": type_name, "Value": value}
            except ValueError:
                logger.warning(f"Invalid value for key {key}, using default")
                dict_key = int(key) if isinstance(key, str) else key
                
                # Preserve the Type name
                if dict_key in self.values_dict:
                    type_name = self.values_dict[dict_key]["Type"]
                elif hasattr(self, 'type_labels') and dict_key in self.type_labels:
                    type_name = self.type_labels[dict_key]
                else:
                    type_name = f"Type_{dict_key}"
                    
                self.values_dict[dict_key] = {"Type": type_name, "Value": 0}
            except KeyError:
                # Handle case where key doesn't exist in dictionary
                logger.error(f"Key {key} not found in values dictionary")
                dict_key = int(key) if isinstance(key, str) else key
                
                # Try to get the type name from our stored labels
                if hasattr(self, 'type_labels') and dict_key in self.type_labels:
                    type_name = self.type_labels[dict_key]
                else:
                    type_name = f"Type_{dict_key}"
                    
                if dict_key not in self.values_dict:
                    self.values_dict[dict_key] = {"Type": type_name, "Value": 0}
                    logger.info(f"Added missing key {dict_key} to values dictionary")

        # Save to file
        self.save_values_to_file()
        
        # Close the window after saving
        self.on_close()

    def default(self):
        """
        Reset all values to defaults and update the UI.
        """
        # Store the current type names before reloading defaults
        original_type_names = {}
        if hasattr(self, 'type_labels'):
            original_type_names = self.type_labels.copy()
        else:
            # If type_labels doesn't exist, try to extract from values_dict
            for key, value in self.values_dict.items():
                if "Type" in value:
                    original_type_names[key] = value["Type"]
        
        # Reload the values_dict from the file - this sets default values
        self.default_values()
        
        # Restore the original type names where possible
        for key, type_name in original_type_names.items():
            if key in self.values_dict:
                self.values_dict[key]["Type"] = type_name
                
        # Now update the entries with the new values
        for key, entry in self.entries.items():
            entry.delete(0, Ctk.END)
            key_int = int(key) if isinstance(key, str) else key
            key_value = self.values_dict[key_int]["Value"]
            entry.insert(0, key_value)
        
        # Save to file to ensure the type names are preserved
        self.save_values_to_file()

    def on_close(self):
        """
        Handle window close event and call any callback function.
        """
        if self.callback:
            self.callback()
        self.destroy()

    def default_values(self):
        """Initialize with default values"""
        self.values_dict = {
            1: {"Type": "Carter", "Value": 0},
            2: {"Type": "Control Tower", "Value": 60},
            3: {"Type": "Barn", "Value": 0},
            4: {"Type": "Bunker", "Value": 50},
            5: {"Type": "Blush", "Value": 0},
            6: {"Type": "Factories", "Value": 50},
            7: {"Type": "Church", "Value": 10},
            8: {"Type": "City Hall", "Value": 20},
            9: {"Type": "Dock", "Value": 80},
            10: {"Type": "Depot", "Value": 40},
            11: {"Type": "Runway", "Value": 95},
            12: {"Type": "Warehouse", "Value": 0},
            13: {"Type": "Helipad", "Value": 0},
            14: {"Type": "Fuel Tanks", "Value": 40},
            15: {"Type": "Nuclear Plant", "Value": 90},
            16: {"Type": "Bridges", "Value": 80},
            17: {"Type": "Pier", "Value": 90},
            18: {"Type": "Power Pole", "Value": 60},
            19: {"Type": "Shops", "Value": 0},
            20: {"Type": "Power Tower", "Value": 60},
            21: {"Type": "Apartment", "Value": 0},
            22: {"Type": "House", "Value": 0},
            23: {"Type": "Power Plant", "Value": 80},
            24: {"Type": "Taxi Signs", "Value": 0},
            25: {"Type": "Nav Beacon", "Value": 0},
            26: {"Type": "Radar Site", "Value": 0},
            27: {"Type": "Craters", "Value": 0},
            28: {"Type": "Radars", "Value": 70},
            29: {"Type": "R Tower", "Value": 60},
            30: {"Type": "Taxiway", "Value": 0},
            31: {"Type": "Rail Terminal", "Value": 0},
            32: {"Type": "Refinery", "Value": 70},
            33: {"Type": "SAM", "Value": 0},
            34: {"Type": "Shed", "Value": 0},
            35: {"Type": "Barracks", "Value": 10},
            36: {"Type": "Tree", "Value": 0},
            37: {"Type": "Water Tower", "Value": 10},
            38: {"Type": "Town Hall", "Value": 30},
            39: {"Type": "Air Terminal", "Value": 20},
            40: {"Type": "Shrine", "Value": 0},
            41: {"Type": "Park", "Value": 0},
            42: {"Type": "Off Block", "Value": 20},
            43: {"Type": "TV Station", "Value": 40},
            44: {"Type": "Hotel", "Value": 0},
            45: {"Type": "Hangar", "Value": 10},
            46: {"Type": "Lights", "Value": 0},
            47: {"Type": "VASI", "Value": 0},
            48: {"Type": "Storage Tank", "Value": 30},
            49: {"Type": "Fence", "Value": 0},
            50: {"Type": "Parking Lot", "Value": 0},
            51: {"Type": "Smoke Stack", "Value": 20},
            52: {"Type": "Building", "Value": 10},
            53: {"Type": "Cooling Tower", "Value": 30},
            54: {"Type": "Cont Dome", "Value": 54},
            55: {"Type": "Guard House", "Value": 0},
            56: {"Type": "Transformer", "Value": 70},
            57: {"Type": "Ammo Dump", "Value": 40},
            58: {"Type": "Hart Site", "Value": 0},
            59: {"Type": "Office", "Value": 0},
            60: {"Type": "Chemical Plant", "Value": 80},
            61: {"Type": "Tower", "Value": 0},
            62: {"Type": "Hospital", "Value": 0},
            63: {"Type": "Shops/Blocks", "Value": 20},
            64: {"Type": "Static", "Value": 0},
            65: {"Type": "Runway Marker", "Value": 0},
            66: {"Type": "Stadium", "Value": 0},
            67: {"Type": "Monument", "Value": 0},
            68: {"Type": "Arrestor Cable", "Value": 0},
        }

    def _get_default_filepath(self):
        return get_json_path(VALUES_DICTIONARY_FILE)
