import tkinter as tk
import customtkinter as Ctk
from tkinter import ttk, messagebox, filedialog
from bms_injector import BmsInjector
import os
import sys
import math
import json
import time
import traceback
import xml.etree.ElementTree as ET

# Import the objective cache
from components.objective_cache import cache as objective_cache

# Import JSON path handler
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.json_path_handler import load_json, save_json, JsonFiles, get_json_path

class BmsInjectionWindow(tk.Toplevel):
    """
    Window for configuring BMS objective properties for injection.
    
    This component provides the UI for setting objective type, name,
    CT number, objective number, and other objective-specific properties
    when using the BMS injection capability.
    """
    
    def __init__(self, parent, bms_path="", ct_num=None, obj_num=None, obj_template=None, ct_file_path=None):
        """Initialize the BMS feature injection window."""
        super().__init__(parent)
        
        # If ct_file_path is provided, use its parent directory as bms_path
        if ct_file_path:
            from pathlib import Path
            
            # Use the parent directory of the Falcon4_CT.xml file as BMS path
            ct_file = Path(ct_file_path)
            if ct_file.exists():
                # Navigate up to find the base BMS directory
                # Typically it's 2 or 3 levels up from the CT file
                parent_dir = ct_file.parent
                if "TerrData" in str(parent_dir):
                    bms_path = parent_dir.parent  # TerrData/.. -> Data
                    if "Data" in str(bms_path):
                        bms_path = bms_path.parent  # Data/.. -> BMS root
        
        # Store bms_path and create injector
        self.bms_path = bms_path
        self.ct_num = ct_num
        self.obj_num = obj_num
        self.injector = BmsInjector(bms_path)
        self.installation_valid = self.injector.is_valid_installation
        
        # Store obj_template for saving
        self.obj_template = obj_template
        
        # Check if there's a saved configuration from previous session
        self.load_previous_settings()
        
        # Feature dictionary
        self.features = {}
        
        # Set up the window
        self.title("BMS Objective Configuration")
        self.geometry("630x750")
        self.resizable(True, True)
        self.configure(bg="#F0F0F5")
        
        # Load objective types
        self.objective_types = self._load_objective_types()
        
        # Flag to prevent validation during initial loading
        self.loading = True
        
        # Initialize UI
        self._init_ui()
        
        # Center the window on screen
        self.update_idletasks()
        width = self.winfo_width()
        height = self.winfo_height()
        x = (self.winfo_screenwidth() // 2) - (width // 2)
        y = (self.winfo_screenheight() // 2) - (height // 2)
        self.geometry(f"{width}x{height}+{x}+{y}")
        
        # Loading complete
        self.loading = False
        
    def _get_settings_path(self):
        """Get the path to the saved settings file in the data_components directory"""
        return get_json_path(JsonFiles.SAVED_OBJECTIVE_SETTINGS)
    
    def load_previous_settings(self):
        """Load previous saved settings if they exist."""
        try:
            # Log the settings path for debugging
            settings_path = self._get_settings_path()
            print(f"Loading settings from: {settings_path}")
            
            # Load settings using json_path_handler
            saved_settings = load_json(JsonFiles.SAVED_OBJECTIVE_SETTINGS, default={})
            
            # Only load previous settings if CT and obj numbers match
            if saved_settings and (saved_settings.get("ct_num") == self.ct_num and 
                saved_settings.get("obj_num") == self.obj_num):
                
                # Store field values to apply to templates
                self.obj_template = saved_settings.get("fields", {})
                
                # Store name for later application
                self.saved_name = saved_settings.get("name", "")
                
                # Store type for later selection and field loading
                self.saved_type = saved_settings.get("type")
                
                print("LOADING PREVIOUS SETTINGS")
                print(f"  Loaded settings for CT:{self.ct_num} Obj:{self.obj_num}")
                print(f"  Saved Type: {self.saved_type}")
                print(f"  Saved Name: {self.saved_name}")
                print(f"  Field Values: {len(self.obj_template)}")
            else:
                print("No matching previous settings found")
                if saved_settings:
                    print(f"  Found settings for CT:{saved_settings.get('ct_num')} Obj:{saved_settings.get('obj_num')}")
                else:
                    print("  No saved settings file found")
                
        except Exception as e:
            print(f"ERROR loading previous settings: {e}")
            traceback.print_exc()
        
    def _load_objective_types(self):
        """Load objective types from cache or from a default list."""
        # Try to get from cache first
        cached_templates = objective_cache.get_objective_templates()
        if cached_templates:
            return {int(k): f"{self._get_type_name(int(k))} - {k}" for k in cached_templates.keys()}
        
        # If not in cache, use the injector's templates
        if self.injector.objective_templates:
            return {int(k): f"{self._get_type_name(int(k))} - {k}" for k in self.injector.objective_templates.keys()}
        
        # Complete list of objective types
        return {
            1: "Airbase - 1",
            2: "Airstrip - 2",
            3: "Army Base - 3",
            4: "Beach - 4",
            5: "Border - 5",
            6: "Bridge - 6",
            7: "Chemical - 7",
            8: "City - 8",
            9: "Command & Control - 9",
            10: "Depot - 10",
            11: "Factory - 11",
            12: "Ford - 12",
            13: "Fortification - 13",
            14: "Scenery - 14",
            15: "Intersect - 15",
            16: "Nav Beacon - 16",
            17: "Nuclear - 17",
            18: "Pass - 18",
            19: "Port - 19",
            20: "Power Plant - 20",
            21: "Radar - 21",
            22: "Radio Tower - 22",
            23: "Rail Terminal - 23",
            24: "Railroad - 24",
            25: "Refinery - 25",
            26: "Railroad - 26",
            27: "Seal - 27",
            28: "Town - 28",
            29: "Village - 29",
            30: "HARTS - 30",
            31: "SAM Site - 31"
        }
    
    def _get_type_name(self, type_id):
        """Get the name for an objective type ID."""
        type_names = {
            1: "Airbase",
            2: "Airstrip",
            3: "Army Base",
            4: "Beach",
            5: "Border",
            6: "Bridge",
            7: "Chemical",
            8: "City",
            9: "Command & Control",
            10: "Depot",
            11: "Factory",
            12: "Ford",
            13: "Fortification",
            14: "Scenery",
            15: "Intersect",
            16: "Nav Beacon",
            17: "Nuclear",
            18: "Pass",
            19: "Port",
            20: "Power Plant",
            21: "Radar",
            22: "Radio Tower",
            23: "Rail Terminal",
            24: "Railroad",
            25: "Refinery",
            26: "Railroad",
            27: "Seal",
            28: "Town",
            29: "Village",
            30: "HARTS",
            31: "SAM Site"
        }
        return type_names.get(type_id, f"Type {type_id}")
    
    def _init_ui(self):
        """Initialize the user interface components."""
        # Store parent reference
        self.parent = self.master
        
        # Main frame
        main_frame = Ctk.CTkFrame(self, fg_color="#E7E7EF")
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Header section
        header_frame = Ctk.CTkFrame(main_frame, fg_color="#D5E3F0")
        header_frame.pack(fill="x", padx=5, pady=5)
        
        Ctk.CTkLabel(
            header_frame,
            text="BMS Objective Configuration",
            font=("Arial", 16, "bold"),
            text_color="#000000",
            fg_color="transparent"  # Use "transparent" instead of None
        ).pack(pady=5)
        
        # BMS Path section with validation indicator
        bms_path_frame = Ctk.CTkFrame(main_frame, fg_color="#E0E8F0", border_width=1, border_color="#B3C8DD")
        bms_path_frame.pack(fill="x", padx=5, pady=5)
        
        # Status indicator for BMS path
        self.bms_status_indicator = Ctk.CTkLabel(
            bms_path_frame,
            text="✗" if not self.installation_valid else "✓",
            width=18,
            text_color="red" if not self.installation_valid else "green",
            font=("Arial", 12, "bold"),
            fg_color="transparent"  # Use "transparent" instead of None
        )
        self.bms_status_indicator.pack(side="left", padx=3, pady=(4, 4))  # Add vertical padding
        
        Ctk.CTkLabel(
            bms_path_frame,
            text="BMS Path:",
            width=95,
            anchor="w",
            text_color="#000000",
            fg_color="transparent"  # Use "transparent" instead of None
        ).pack(side="left", padx=2, pady=(4, 4))  # Add vertical padding
        
        self.bms_path_entry = Ctk.CTkEntry(
            bms_path_frame,
            width=400,
            fg_color="#FDFDFD",
            border_color="#B3C8DD",
            text_color="#000000",
            state="readonly"  # Use readonly instead of disabled to keep text visible
        )
        self.bms_path_entry.pack(side="left", fill="x", expand=True, padx=5, pady=(4, 4))  # Add vertical padding
        
        # Clear existing text and insert updated path
        self.bms_path_entry.configure(state="normal")
        self.bms_path_entry.delete(0, tk.END)
        self.bms_path_entry.insert(0, str(self.bms_path))
        self.bms_path_entry.configure(state="readonly")
        
        # Basic settings section
        settings_frame = Ctk.CTkFrame(main_frame, fg_color="#E0E8F0", border_width=1, border_color="#B3C8DD")
        settings_frame.pack(fill="x", padx=5, pady=5)
        
        # CT Number section
        ct_frame = Ctk.CTkFrame(settings_frame, fg_color="#E0E8F0", border_width=1, border_color="#B3C8DD")
        ct_frame.pack(fill="x", padx=5, pady=5)
        
        Ctk.CTkLabel(
            ct_frame,
            text="CT Number:",
            width=115,
            anchor="w",
            text_color="#000000",
            fg_color="transparent"  # Use "transparent" instead of None
        ).pack(side="left", padx=5, pady=(4, 4))  # Add vertical padding
        
        self.ct_entry = Ctk.CTkEntry(
            ct_frame,
            width=100,
            fg_color="#FDFDFD",
            border_color="#B3C8DD",
            text_color="#000000"
        )
        self.ct_entry.pack(side="left", padx=5, pady=(4, 4))  # Add vertical padding
        if self.ct_num:
            self.ct_entry.insert(0, str(self.ct_num))
        
        # Add "Get Last" button for CT Number
        Ctk.CTkButton(
            ct_frame,
            text="Get Last",
            width=80,
            command=self._get_last_ct,
            fg_color="#8DBBE7",
            hover_color="#6A9AC9",
            text_color="#000000"
        ).pack(side="left", padx=5, pady=(4, 4))  # Add vertical padding
        
        # Add "Get Obj Num" button for CT Number
        Ctk.CTkButton(
            ct_frame,
            text="Get Obj Num",
            width=80,
            command=self._get_obj_from_ct,
            fg_color="#8DBBE7",
            hover_color="#6A9AC9",
            text_color="#000000"
        ).pack(side="left", padx=5, pady=(4, 4))  # Add vertical padding
        
        self.ct_info_label = Ctk.CTkLabel(
            ct_frame,
            text="",
            width=250,
            anchor="w",
            fg_color="transparent"  # Use "transparent" instead of None
        )
        self.ct_info_label.pack(side="left", padx=5, fill="x", expand=True, pady=(4, 4))  # Add vertical padding
        
        # Objective Number section
        obj_frame = Ctk.CTkFrame(settings_frame, fg_color="#E0E8F0", border_width=1, border_color="#B3C8DD")
        obj_frame.pack(fill="x", padx=5, pady=5)
        
        Ctk.CTkLabel(
            obj_frame,
            text="Objective Number:",
            width=115,
            anchor="w",
            text_color="#000000",
            fg_color="transparent"  # Use "transparent" instead of None
        ).pack(side="left", padx=5, pady=(4, 4))  # Add vertical padding
        
        self.obj_entry = Ctk.CTkEntry(
            obj_frame,
            width=100,
            fg_color="#FDFDFD",
            border_color="#B3C8DD",
            text_color="#000000"
        )
        self.obj_entry.pack(side="left", padx=5, pady=(4, 4))  # Add vertical padding
        if self.obj_num:
            self.obj_entry.insert(0, str(self.obj_num))
        
        # Add "Get Last" button for Obj Number
        Ctk.CTkButton(
            obj_frame,
            text="Get Last",
            width=80,
            command=self._get_last_obj,
            fg_color="#8DBBE7",
            hover_color="#6A9AC9",
            text_color="#000000"
        ).pack(side="left", padx=5, pady=(4, 4))  # Add vertical padding
        
        # Add "Get Data" button for Obj Number
        Ctk.CTkButton(
            obj_frame,
            text="Get Data",
            width=80,
            command=self._get_ct_from_obj,
            fg_color="#8DBBE7",
            hover_color="#6A9AC9",
            text_color="#000000"
        ).pack(side="left", padx=5, pady=(4, 4))  # Add vertical padding
        
        self.obj_info_label = Ctk.CTkLabel(
            obj_frame,
            text="",
            width=250,
            anchor="w",
            fg_color="transparent"  # Use "transparent" instead of None
        )
        self.obj_info_label.pack(side="left", padx=5, fill="x", expand=True, pady=(4, 4))  # Add vertical padding
        
        # Type dropdown section
        type_frame = Ctk.CTkFrame(settings_frame, fg_color="#E0E8F0", border_width=1, border_color="#B3C8DD")
        type_frame.pack(fill="x", padx=5, pady=5)
        
        Ctk.CTkLabel(
            type_frame,
            text="Objective Type:",
            width=115,
            anchor="w",
            text_color="#000000",
            fg_color="transparent"  # Use "transparent" instead of None
        ).pack(side="left", padx=5, pady=(4, 4))  # Add vertical padding
        
        # Convert objective types to list of strings for dropdown and sort alphabetically
        self.objective_types_sorted = {k: v for k, v in sorted(self.objective_types.items(), key=lambda item: item[1])}
        self.type_values = list(self.objective_types_sorted.values())
        self.type_keys = list(self.objective_types_sorted.keys())
        
        self.type_var = tk.StringVar(value=self.type_values[0] if self.type_values else "")
        self.type_dropdown = Ctk.CTkOptionMenu(
            type_frame,
            values=self.type_values,
            variable=self.type_var,
            width=350,
            command=self._on_type_selected,
            fg_color="#FDFDFD",
            button_color="#8DBBE7",
            button_hover_color="#6A9AC9",
            dropdown_fg_color="#FDFDFD",
            text_color="#000000"
        )
        self.type_dropdown.pack(side="left", padx=5, fill="x", expand=True, pady=(4, 4))  # Add vertical padding
        
        # Name section
        name_frame = Ctk.CTkFrame(settings_frame, fg_color="#E0E8F0", border_width=1, border_color="#B3C8DD")
        name_frame.pack(fill="x", padx=5, pady=5)
        
        Ctk.CTkLabel(
            name_frame,
            text="Objective Name:",
            width=115,
            anchor="w",
            text_color="#000000",
            fg_color="transparent"  # Use "transparent" instead of None
        ).pack(side="left", padx=5, pady=(4, 4))  # Add vertical padding
        
        self.name_entry = Ctk.CTkEntry(
            name_frame,
            width=350,
            fg_color="#FDFDFD",
            border_color="#B3C8DD",
            text_color="#000000"
        )
        self.name_entry.pack(side="left", padx=5, fill="x", expand=True, pady=(4, 4))  # Add vertical padding
        
        # Apply saved name if available
        if hasattr(self, 'saved_name') and self.saved_name:
            self.name_entry.delete(0, tk.END)
            self.name_entry.insert(0, self.saved_name)
        
        # Reset PHD/PDX checkbox section
        reset_frame = Ctk.CTkFrame(settings_frame, fg_color="#E0E8F0", border_width=1, border_color="#B3C8DD")
        reset_frame.pack(fill="x", padx=5, pady=5)
        
        self.reset_var = tk.BooleanVar(value=True)
        self.reset_checkbox = Ctk.CTkCheckBox(
            reset_frame,
            text="Reset PHD and PDX files when updating existing objective",
            variable=self.reset_var,
            fg_color="#8DBBE7",
            hover_color="#6A9AC9",
            text_color="#000000",
            checkbox_height=20,
            checkbox_width=20
        )
        self.reset_checkbox.pack(padx=5, pady=(8, 8))  # Add increased vertical padding
        
        # Separator
        separator = ttk.Separator(main_frame, orient="horizontal")
        separator.pack(fill="x", padx=5, pady=10)
        
        # Dynamic fields section
        Ctk.CTkLabel(
            main_frame,
            text="Objective Properties",
            font=("Arial", 12, "bold"),
            text_color="#000000",
            fg_color="transparent"  # Use "transparent" instead of None
        ).pack(anchor="w", padx=10, pady=5)
        
        self.fields_frame = Ctk.CTkScrollableFrame(
            main_frame,
            height=250,
            fg_color="#E0E8F0",
            border_color="#B3C8DD",
            border_width=1
        )
        self.fields_frame.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Initialize field entries dict
        self.field_entries = {}
        
        # Create all common fields upfront regardless of type
        self._create_all_fields()
        
        # Button section
        button_frame = Ctk.CTkFrame(main_frame, fg_color="#E0E8F0", border_width=1, border_color="#B3C8DD")
        button_frame.pack(fill="x", padx=5, pady=10)
        
        # Reset to Defaults button (stays on the left)
        Ctk.CTkButton(
            button_frame,
            text="Reset to Defaults",
            command=self._reset_fields,
            fg_color="#8DBBE7",
            hover_color="#6A9AC9",
            text_color="#000000"
        ).pack(side="left", padx=5, pady=(6, 6))  # Add vertical padding
        
        # Save Settings button (moved to the right)
        Ctk.CTkButton(
            button_frame,
            text="Save Settings",
            command=self._save_settings,
            fg_color="#8DBBE7",
            hover_color="#6A9AC9",
            text_color="#000000"
        ).pack(side="right", padx=5, pady=(6, 6))  # Add vertical padding
        
        # Cancel button (left of Save Settings button)
        Ctk.CTkButton(
            button_frame,
            text="Cancel",
            command=self.destroy,
            fg_color="#8DBBE7",
            hover_color="#6A9AC9",
            text_color="#000000"
        ).pack(side="right", padx=5, pady=(6, 6))  # Add vertical padding
        
        # Bind validation and update events
        self.ct_entry.bind("<FocusOut>", self._validate_ct)
        self.obj_entry.bind("<FocusOut>", self._validate_obj)
        
        # Add Enter key bindings for validation
        self.ct_entry.bind("<Return>", self._validate_ct)
        self.ct_entry.bind("<KP_Enter>", self._validate_ct)  # Numpad Enter
        self.obj_entry.bind("<Return>", self._validate_obj)
        self.obj_entry.bind("<KP_Enter>", self._validate_obj)  # Numpad Enter
        
        # Apply saved type if available
        if hasattr(self, 'saved_type') and self.saved_type and self.saved_type in self.type_keys:
            type_index = self.type_keys.index(self.saved_type)
            if type_index >= 0 and type_index < len(self.type_values):
                self.type_var.set(self.type_values[type_index])
                # Make sure to load the field data when setting type
                self._on_type_selected(self.type_values[type_index])
                
        # Now load field data based on type selection
        self._load_type_data()
        
        # Validate CT and objective numbers
        if not self.loading:
            self._validate_ct(None)
            self._validate_obj(None)
        
    def _create_all_fields(self):
        """Create all common field entries that all objectives have."""
        # Clear any existing fields
        for widget in self.fields_frame.winfo_children():
            widget.destroy()
        
        self.field_entries.clear()
        
        # Common fields that all objectives have
        common_fields = [
            ("DataRate", "0"),
            ("DeaggDistance", "0"),
            ("Det_NoMove", "0.0"),
            ("Det_Foot", "0.0"),
            ("Det_Wheeled", "0.0"),
            ("Det_Tracked", "0.0"),
            ("Det_LowAir", "0.0"),
            ("Det_Air", "0.0"),
            ("Det_Naval", "0.0"),
            ("Det_Rail", "0.0"),
            ("Dam_None", "0"),
            ("Dam_Penetration", "0"),
            ("Dam_HighExplosive", "0"),
            ("Dam_Heave", "0"),
            ("Dam_Incendairy", "0"),
            ("Dam_Proximity", "0"),
            ("Dam_Kinetic", "0"),
            ("Dam_Hydrostatic", "0"),
            ("Dam_Chemical", "0"),
            ("Dam_Nuclear", "0"),
            ("Dam_Other", "0"),
            ("ObjectiveIcon", "0"),
            ("RadarFeature", "0")
        ]
        
        # Add field entries for each field
        for row, (field_name, default_value) in enumerate(common_fields):
            field_frame = Ctk.CTkFrame(self.fields_frame, fg_color="#E0E8F0")
            field_frame.grid(row=row, column=0, sticky="ew", padx=5, pady=3)  # Increased vertical spacing
            
            Ctk.CTkLabel(
                field_frame,
                text=field_name + ":",
                width=145,
                anchor="w",
                text_color="#000000",
                fg_color="transparent"  # Use "transparent" instead of None
            ).pack(side="left", padx=5, pady=(3, 3))  # Add vertical padding
            
            entry = Ctk.CTkEntry(
                field_frame, 
                width=120, 
                fg_color="#FDFDFD",
                border_color="#B3C8DD",
                text_color="#000000"
            )
            entry.pack(side="left", padx=5, fill="x", expand=True, pady=(3, 3))  # Add vertical padding
            entry.insert(0, str(default_value))  # Insert the default value into the entry
            
            self.field_entries[field_name] = entry
        
        # Configure grid to expand properly
        self.fields_frame.columnconfigure(0, weight=1)
    
    def _load_type_data(self):
        """Load field data for the selected objective type."""
        # Get the selected type
        type_key = self._get_selected_type_key()
        if not type_key:
            return
        
        # Enhanced logging with prefix for easier tracking
        print(f"LOADING TYPE DATA: Type {type_key}")
        
        # Get template for this type from cache
        template = objective_cache.get_objective_templates(int(type_key))
        if not template:
            # If not in cache, try from injector
            template = self.injector.objective_templates.get(str(type_key), {})
            print(f"  Template source: injector (not found in cache)")
        else:
            print(f"  Template source: cache")
        
        # Debug print template
        print(f"  Base template fields: {len(template)}")
        
        # Override with user-saved template if available
        user_template = objective_cache.get_user_templates(int(type_key))
        if user_template:
            print(f"  Applying user template with {len(user_template)} fields")
            template.update(user_template)
        else:
            print(f"  No user template found for type {type_key}")
        
        # Override with saved values if available
        if self.obj_template and isinstance(self.obj_template, dict):
            print(f"  Applying saved object template with {len(self.obj_template)} fields")
            template.update(self.obj_template)
        
        # Store the current template for later use
        self.current_template = template
        
        # Debug print the final template being applied
        print(f"  Final template has {len(template)} fields")
        
        # Update existing fields with template values
        for field_name, entry in self.field_entries.items():
            # Always update all fields when changing types
            value = template.get(field_name, "0")  # Default to "0" if not in template
            
            # Debug print each field update
            print(f"    Setting field {field_name} = {value}")
            
            # Update the entry
            entry.delete(0, tk.END)
            entry.insert(0, str(value))
    
    def _on_type_selected(self, selection):
        """Handle type selection and update fields."""
        # Prevent unnecessary field loading during initialization
        if self.loading:
            print("Still loading, not updating fields yet")
            return
        
        # Get the type key for this selection
        selected_index = self.type_values.index(selection)
        selected_type_key = self.type_keys[selected_index]
        
        # Enhanced logging with more detail
        print(f"OBJECTIVE TYPE SELECTED: {selection}")
        print(f"  Type Key: {selected_type_key}")
        print(f"  Type Index: {selected_index}")
        
        # Load the template data for the selected type
        self._load_type_data()
    
    def _reset_fields(self):
        """Reset fields to default values based on selected type."""
        # Get the selected type
        type_key = self._get_selected_type_key()
        
        print(f"RESETTING FIELDS to defaults for type {type_key}")
        
        # Get default template for this type
        template = objective_cache.get_objective_templates(type_key)
        
        # If not in cache, use injector's templates or default values
        if not template:
            template = self.injector.objective_templates.get(str(type_key), {})
            print(f"  Using template from injector with {len(template)} fields")
        else:
            print(f"  Using template from cache with {len(template)} fields")
        
        # Update fields with template values
        field_count = 0
        for field_name, entry in self.field_entries.items():
            value = template.get(field_name, "0")
            entry.delete(0, tk.END)
            entry.insert(0, str(value))
            field_count += 1
            print(f"    Reset field {field_name} = {value}")
        
        print(f"  Reset {field_count} fields completed")
    
    def _save_settings(self):
        """Save settings and close the window."""
        print("SAVING OBJECTIVE SETTINGS")
        
        # Validate inputs
        try:
            ct_num = int(self.ct_entry.get())
            obj_num = int(self.obj_entry.get())
            print(f"  CT Number: {ct_num}")
            print(f"  Objective Number: {obj_num}")
        except ValueError:
            print("  ERROR: Invalid CT or Objective Number")
            messagebox.showerror(
                "Invalid Input",
                "CT Number and Objective Number must be integers."
            )
            return
        
        # Check for missing name
        name = self.name_entry.get().strip()
        if not name:
            print("  ERROR: Missing objective name")
            messagebox.showerror(
                "Missing Name",
                "Objective Name is required."
            )
            return
        
        print(f"  Objective Name: {name}")
        
        # Get selected type
        type_key = self._get_selected_type_key()
        selected_type = self.type_var.get()
        print(f"  Selected Type: {selected_type}")
        print(f"  Type Key: {type_key}")
        
        # Get field values - stored as strings to make saving/loading simpler
        fields = {}
        for field_name, entry in self.field_entries.items():
            raw_value = entry.get().strip()
            fields[field_name] = raw_value
        
        # Debug print the field values
        print(f"  Collected {len(fields)} field values")
        
        # Create a version with converted types for internal use
        typed_fields = {}
        for field_name, value in fields.items():
            try:
                # Try to convert to appropriate type
                if "." in value:
                    typed_fields[field_name] = float(value)
                else:
                    typed_fields[field_name] = int(value)
            except ValueError:
                typed_fields[field_name] = value
        
        # Create the result dict
        result_data = {
            "ct_num": ct_num,
            "obj_num": obj_num,
            "name": name,
            "type": type_key,
            "fields": fields,  # Store raw string values for easier loading
            "reset_pd": self.reset_var.get(),
            "bms_path": self.bms_path_entry.get()
        }
        
        # Store in instance variable - use typed fields for actual operation
        self.result = {
            "ct_num": ct_num,
            "obj_num": obj_num,
            "name": name,
            "type": type_key,
            "fields": typed_fields,  # Use converted values for operation
            "reset_pd": self.reset_var.get(),
            "bms_path": self.bms_path_entry.get()
        }
        
        print(f"  Reset PHD/PDX: {self.reset_var.get()}")
        print(f"  BMS Path: {self.bms_path_entry.get()}")
        
        # Save settings for next time using json_path_handler
        try:
            # Log the settings path for debugging
            settings_path = self._get_settings_path()
            print(f"  Saving settings to: {settings_path}")
            
            success = save_json(JsonFiles.SAVED_OBJECTIVE_SETTINGS, result_data)
            if success:
                print(f"  Successfully saved settings to {JsonFiles.SAVED_OBJECTIVE_SETTINGS}")
            else:
                print(f"  Failed to save settings to {JsonFiles.SAVED_OBJECTIVE_SETTINGS}")
        except Exception as e:
            print(f"  Error saving settings: {e}")
            traceback.print_exc()
        
        # Also store in parent window if it's the OperationPage
        if hasattr(self.parent, 'textbox_CT') and hasattr(self.parent, 'textbox_Obj'):
            print(f"  Updating parent window entries")
            # Directly update parent window entries
            if hasattr(self.parent.textbox_CT, 'cget') and self.parent.textbox_CT.cget('state') == 'disable':
                self.parent.textbox_CT.configure(state='normal')
            self.parent.textbox_CT.delete(0, tk.END)
            self.parent.textbox_CT.insert(0, str(ct_num))
            if hasattr(self.parent.textbox_CT, 'cget') and self.parent.textbox_CT.cget('state') == 'normal':
                self.parent.textbox_CT.configure(state='disable')
            
            if hasattr(self.parent.textbox_Obj, 'cget') and self.parent.textbox_Obj.cget('state') == 'disable':
                self.parent.textbox_Obj.configure(state='normal')
            self.parent.textbox_Obj.delete(0, tk.END)
            self.parent.textbox_Obj.insert(0, str(obj_num))
            if hasattr(self.parent.textbox_Obj, 'cget') and self.parent.textbox_Obj.cget('state') == 'normal':
                self.parent.textbox_Obj.configure(state='disable')
            
            # Ensure BMS mode is active if the parent has this functionality
            if hasattr(self.parent, 'saving_method_var') and hasattr(self.parent, 'segemented_button_Saving'):
                if self.parent.saving_method_var.get() != "BMS":
                    print(f"  Setting parent to BMS mode")
                    self.parent.segemented_button_Saving.set("BMS")
                    if hasattr(self.parent, 'switch_save_method'):
                        self.parent.switch_save_method("BMS")
                else:
                    # Ensure entries are disabled even if BMS mode is already active
                    print(f"  BMS mode already active")
                    if hasattr(self.parent.textbox_CT, 'configure'):
                        self.parent.textbox_CT.configure(state='disable')
                    if hasattr(self.parent.textbox_Obj, 'configure'):
                        self.parent.textbox_Obj.configure(state='disable')
        
        # Debug print
        print(f"  BMS Injection Window saving result: {self.result}")
        
        # Save user template in cache - use typed fields
        print(f"  Saving user template for type {type_key}")
        objective_cache.set_user_templates(typed_fields, type_key)
        objective_cache.save_cache()
        
        # Also update templates in injector - use typed fields
        print(f"  Updating injector templates for type {type_key}")
        self.injector.objective_templates[str(type_key)] = typed_fields
        self.injector.save_templates()
        
        print("OBJECTIVE SETTINGS SAVE COMPLETED")
        
        # Close window
        self.destroy()
    
    def _get_selected_type_key(self):
        """Get the key (numeric type) for the selected type."""
        selected = self.type_var.get()
        try:
            index = self.type_values.index(selected)
            key = self.type_keys[index]
            print(f"Getting selected type key: {selected} -> {key}")
            return key
        except (ValueError, IndexError):
            default = self.type_keys[0] if self.type_keys else 1
            print(f"Error getting type key, using default: {default}")
            return default
    
    def _validate_bms_path(self, event=None):
        """Validate the BMS path and update the UI accordingly."""
        # Get path from entry
        new_path = self.bms_path_entry.get()
        
        # Check if path has changed
        if new_path == self.bms_path:
            return
            
        # Update path and recreate injector
        self.bms_path = new_path
        self.injector = BmsInjector(self.bms_path)
        
        # Update installation validity
        self.installation_valid = self.injector.is_valid_installation
        
        # Update status indicator
        self.bms_status_indicator.configure(
            text="✓" if self.installation_valid else "✗",
            text_color="green" if self.installation_valid else "red"
        )
        
        # Reload objective types if installation is valid
        if self.installation_valid:
            self.objective_types = self._load_objective_types()
            self._load_type_data()
        else:
            # Show warning about invalid installation
            messagebox.showwarning(
                "Invalid BMS Path",
                f"Could not find a valid BMS installation at:\n{self.bms_path}\n\n"
                "Please select a valid BMS installation directory."
            )
    
    def _browse_bms_path(self):
        """Open a file dialog to choose the BMS installation directory."""
        # Get directory from user
        path = filedialog.askdirectory(
            title="Select BMS Installation Directory",
            initialdir=self.bms_path if os.path.exists(self.bms_path) else os.path.expanduser("~")
        )
        
        # Update if user selected a path
        if path:
            self.bms_path_entry.delete(0, "end")
            self.bms_path_entry.insert(0, path)
            
            # Validate the new path
            self._validate_bms_path()
    
    def _validate_ct(self, event):
        """Validate CT number and update info label."""
        try:
            ct_num = int(self.ct_entry.get())
            
            # Check if CT number exists
            ct_exists = False
            is_objective = False
            
            # Check cache first
            ct_data = objective_cache.get_ct_data(ct_num)
            if ct_data:
                ct_exists = True
                is_objective = ct_data.get("is_objective", False)
            else:
                # If not in cache, check if CT exists in CT file
                if self.injector.is_valid_installation:
                    try:
                        tree = ET.parse(self.injector.ct_file)
                        root = tree.getroot()
                        
                        for ct in root.findall("CT"):
                            try:
                                if int(ct.get("Num")) == ct_num:
                                    ct_exists = True
                                    # Check if it's an objective (EntityType = 3)
                                    entity_type = ct.find("EntityType")
                                    if entity_type is not None and entity_type.text == "3":
                                        is_objective = True
                                    break
                            except (ValueError, TypeError):
                                continue
                    except Exception:
                        pass
            
            # Get highest CT number
            highest_ct = 0
            try:
                tree = ET.parse(self.injector.ct_file)
                root = tree.getroot()
                
                for ct in root.findall("CT"):
                    try:
                        ct_val = int(ct.get("Num"))
                        highest_ct = max(highest_ct, ct_val)
                    except (ValueError, TypeError):
                        pass
            except Exception:
                pass
                
            # Update status based on validation rules
            if ct_exists and is_objective:
                self.ct_info_label.configure(
                    text="⚠ CT is an Objective",
                    text_color="orange",
                    fg_color="transparent"
                )
            elif ct_exists and not is_objective:
                self.ct_info_label.configure(
                    text="⚠ CT is not an Objective",
                    text_color="brown",
                    fg_color="transparent"
                )
            elif ct_num == highest_ct + 1:
                self.ct_info_label.configure(
                    text="✓ Valid CT Number",
                    text_color="green",
                    fg_color="transparent"
                )
            else:
                self.ct_info_label.configure(
                    text="❌ Invalid CT Number",
                    text_color="red",
                    fg_color="transparent"
                )
                
        except ValueError:
            self.ct_info_label.configure(
                text="❌ Invalid CT number",
                text_color="red",
                fg_color="transparent"
            )
    
    def _validate_obj(self, event):
        """Validate objective number and update info label."""
        try:
            obj_num = int(self.obj_entry.get())
            
            # Check if objective exists
            obj_exists = False
            
            # Check cache first
            obj_data = objective_cache.get_objective_data(obj_num)
            if obj_data is not None:
                obj_exists = True
            else:
                # If not in cache, check if objective exists in file system
                if self.injector.objective_exists(obj_num):
                    obj_exists = True
            
            # Get highest objective number
            highest_obj = 0
            try:
                if hasattr(objective_cache, 'get_all_objectives'):
                    cached_obj_nums = [int(key) for key in objective_cache.get_all_objectives().keys()]
                    if cached_obj_nums:
                        highest_obj = max(cached_obj_nums)
                
                if highest_obj == 0 and self.injector.is_valid_installation:
                    for obj_dir in self.injector.objective_dir.glob("OCD_*"):
                        if not obj_dir.is_dir():
                            continue
                        
                        obj_idx = obj_dir.name.split("_")[1]
                        try:
                            obj_val = int(obj_idx)
                            highest_obj = max(highest_obj, obj_val)
                        except ValueError:
                            pass
            except Exception:
                pass
                
            # Update status based on validation rules
            if obj_exists:
                self.obj_info_label.configure(
                    text="⚠ Existing Objective will be updated",
                    text_color="orange",
                    fg_color="transparent"
                )
            elif obj_num == highest_obj + 1:
                self.obj_info_label.configure(
                    text="✓ Valid Objective number",
                    text_color="green",
                    fg_color="transparent"
                )
            else:
                self.obj_info_label.configure(
                    text="❌ Invalid Objective Number",
                    text_color="red",
                    fg_color="transparent"
                )
                
        except ValueError:
            self.obj_info_label.configure(
                text="❌ Invalid objective number",
                text_color="red",
                fg_color="transparent"
            )
    
    def _get_last_ct(self):
        """Find the highest CT number and set the CT entry to last+1."""
        try:
            # Check if the CT file exists and is valid
            if not self.injector.is_valid_installation:
                messagebox.showwarning(
                    "Invalid Installation",
                    "Cannot find highest CT number without a valid BMS installation."
                )
                self.ct_info_label.configure(
                    text="Invalid BMS installation",
                    text_color="red",
                    fg_color="transparent"
                )
                return
                
            # Parse the CT file to find the highest CT number
            highest_ct = 0
            try:
                tree = ET.parse(self.injector.ct_file)
                root = tree.getroot()
                
                for ct in root.findall("CT"):
                    try:
                        ct_num = int(ct.get("Num"))
                        highest_ct = max(highest_ct, ct_num)
                    except (ValueError, TypeError, AttributeError):
                        pass
                        
                # Set the entry to highest + 1
                self.ct_entry.delete(0, tk.END)
                self.ct_entry.insert(0, str(highest_ct + 1))
                
                # Validate the new CT number
                self._validate_ct(None)
                
                # Update the status message
                self.ct_info_label.configure(
                    text=f"Found highest CT: {highest_ct}",
                    text_color="green",
                    fg_color="transparent"
                )
                
            except Exception as e:
                self.ct_info_label.configure(
                    text=f"Error: {str(e)}",
                    text_color="red",
                    fg_color="transparent"
                )
                messagebox.showerror(
                    "Error",
                    f"Failed to find highest CT number: {str(e)}"
                )
                
        except Exception as e:
            self.ct_info_label.configure(
                text=f"Error: {str(e)}",
                text_color="red",
                fg_color="transparent"
            )
            messagebox.showerror(
                "Error",
                f"An unexpected error occurred: {str(e)}"
            )
    
    def _get_obj_from_ct(self):
        """Get the objective number for the CT in the CT entry field and load all data."""
        try:
            # Get the CT number from the entry
            ct_entry_text = self.ct_entry.get().strip()
            
            # Check if entry is empty
            if not ct_entry_text:
                self.ct_info_label.configure(
                    text="CT Number is empty",
                    text_color="red",
                    fg_color="transparent"
                )
                return
                
            try:
                ct_num = int(ct_entry_text)
            except ValueError:
                self.ct_info_label.configure(
                    text="Invalid CT Number",
                    text_color="red",
                    fg_color="transparent"
                )
                return
            
            # Check if installation is valid
            if not self.injector.is_valid_installation:
                self.ct_info_label.configure(
                    text="Invalid BMS installation",
                    text_color="red",
                    fg_color="transparent"
                )
                return
                
            # Check if the CT is an objective
            if not self.injector.is_objective_ct(ct_num):
                self.ct_info_label.configure(
                    text="CT is not an Objective",
                    text_color="orange",
                    fg_color="transparent"
                )
                return
                
            # Try to find the objective that uses this CT
            found = False
            obj_num = None
            
            # First check in cache if the method exists
            try:
                obj_data_dict = objective_cache.get_all_objectives() if hasattr(objective_cache, 'get_all_objectives') else {}
                for obj_key, obj_data in obj_data_dict.items():
                    if obj_data.get("ct_idx") == ct_num:
                        obj_num = int(obj_key)
                        found = True
                        break
            except Exception as cache_err:
                # Just continue to file search if cache lookup fails
                print(f"Cache lookup failed: {cache_err}")
            
            # If not found in cache, search through objective files
            if not found and self.injector.is_valid_installation:
                try:
                    for obj_dir in self.injector.objective_dir.glob("OCD_*"):
                        if not obj_dir.is_dir():
                            continue
                        
                        obj_idx = obj_dir.name.split("_")[1]
                        ocd_file = obj_dir / f"OCD_{obj_idx}.XML"
                        
                        if not ocd_file.exists():
                            continue
                        
                        try:
                            tree = ET.parse(ocd_file)
                            root = tree.getroot()
                            ocd = root.find("OCD")
                            
                            if ocd is None:
                                continue
                            
                            ct_idx_elem = ocd.find("CtIdx")
                            if ct_idx_elem is not None and ct_idx_elem.text is not None:
                                if int(ct_idx_elem.text) == ct_num:
                                    # Found the objective that uses this CT
                                    obj_num = int(obj_idx)
                                    found = True
                                    break
                        except Exception as file_err:
                            print(f"Error processing file {ocd_file}: {file_err}")
                            continue
                except Exception as search_err:
                    self.ct_info_label.configure(
                        text=f"Error searching objectives: {search_err}",
                        text_color="red",
                        fg_color="transparent"
                    )
            
            if found and obj_num is not None:
                # Set the objective number
                self.obj_entry.delete(0, tk.END)
                self.obj_entry.insert(0, str(obj_num))
                self._validate_obj(None)
                
                # Now load all data from this objective
                self._get_ct_from_obj()
                
                self.ct_info_label.configure(
                    text="Found Objective",
                    text_color="green",
                    fg_color="transparent"
                )
            else:
                self.ct_info_label.configure(
                    text="No Objective Found for this CT",
                    text_color="orange",
                    fg_color="transparent"
                )
                
        except Exception as e:
            self.ct_info_label.configure(
                text=f"Error: {str(e)}",
                text_color="red",
                fg_color="transparent"
            )
    
    def _get_last_obj(self):
        """Find the highest objective number and set the objective entry to last+1."""
        try:
            # Check if the installation is valid
            if not self.injector.is_valid_installation:
                self.obj_info_label.configure(
                    text="Invalid BMS installation",
                    text_color="red",
                    fg_color="transparent"
                )
                messagebox.showwarning(
                    "Invalid Installation",
                    "Cannot find highest objective number without a valid BMS installation."
                )
                return
                
            # Find all objective directories and get the highest number
            highest_obj = 0
            
            try:
                # Check cache first for faster lookup if the method exists
                try:
                    if hasattr(objective_cache, 'get_all_objectives'):
                        cached_obj_nums = [int(key) for key in objective_cache.get_all_objectives().keys()]
                        if cached_obj_nums:
                            highest_obj = max(cached_obj_nums)
                except Exception as cache_err:
                    # Continue to file search if cache lookup fails
                    print(f"Cache lookup failed: {cache_err}")
                
                # If not found in cache, search through directory
                if highest_obj == 0:
                    for obj_dir in self.injector.objective_dir.glob("OCD_*"):
                        if not obj_dir.is_dir():
                            continue
                        
                        obj_idx = obj_dir.name.split("_")[1]
                        try:
                            obj_num = int(obj_idx)
                            highest_obj = max(highest_obj, obj_num)
                        except ValueError:
                            pass
                
                # Set the entry to highest + 1
                self.obj_entry.delete(0, tk.END)
                self.obj_entry.insert(0, str(highest_obj + 1))
                
                # Validate the new objective number
                self._validate_obj(None)
                
                # Update status
                self.obj_info_label.configure(
                    text=f"Found highest Obj: {highest_obj}",
                    text_color="green",
                    fg_color="transparent"
                )
                
            except Exception as e:
                self.obj_info_label.configure(
                    text=f"Error: {str(e)}",
                    text_color="red",
                    fg_color="transparent"
                )
                messagebox.showerror(
                    "Error",
                    f"Failed to find highest objective number: {str(e)}"
                )
                
        except Exception as e:
            self.obj_info_label.configure(
                text=f"Error: {str(e)}",
                text_color="red",
                fg_color="transparent"
            )
            messagebox.showerror(
                "Error",
                f"An unexpected error occurred: {str(e)}"
            )
    
    def _get_ct_from_obj(self):
        """Get the CT number and all data from the objective in the objective entry field."""
        try:
            # Get the objective number from the entry
            obj_entry_text = self.obj_entry.get().strip()
            
            # Check if entry is empty
            if not obj_entry_text:
                self.obj_info_label.configure(
                    text="Objective Number is empty",
                    text_color="red",
                    fg_color="transparent"
                )
                return
                
            try:
                obj_num = int(obj_entry_text)
            except ValueError:
                self.obj_info_label.configure(
                    text="Invalid Objective Number",
                    text_color="red",
                    fg_color="transparent"
                )
                return
            
            # Check if installation is valid
            if not self.injector.is_valid_installation:
                self.obj_info_label.configure(
                    text="Invalid BMS installation",
                    text_color="red",
                    fg_color="transparent"
                )
                return
                
            # Check if the objective exists
            if not self.injector.objective_exists(obj_num):
                self.obj_info_label.configure(
                    text="No Data to show",
                    text_color="red",
                    fg_color="transparent"
                )
                return
                
            # Try to find the CT number and other data for this objective
            obj_num_str = f"{obj_num:05d}"
            ocd_file = self.injector.objective_dir / f"OCD_{obj_num_str}" / f"OCD_{obj_num_str}.XML"
            
            if not ocd_file.exists():
                self.obj_info_label.configure(
                    text="No Data to show",
                    text_color="red",
                    fg_color="transparent"
                )
                return
                
            try:
                tree = ET.parse(ocd_file)
                root = tree.getroot()
                ocd = root.find("OCD")
                
                if ocd is None:
                    self.obj_info_label.configure(
                        text="No Data to show",
                        text_color="red",
                        fg_color="transparent"
                    )
                    return
                    
                # Get the CT index (required)
                ct_idx_elem = ocd.find("CtIdx")
                if ct_idx_elem is None or ct_idx_elem.text is None:
                    self.obj_info_label.configure(
                        text="No Data to show",
                        text_color="red",
                        fg_color="transparent"
                    )
                    return
                    
                ct_num = int(ct_idx_elem.text)
                
                # Set the CT entry
                self.ct_entry.delete(0, tk.END)
                self.ct_entry.insert(0, str(ct_num))
                
                # Get the name if available
                name_elem = ocd.find("Name")
                if name_elem is not None and name_elem.text:
                    self.name_entry.delete(0, tk.END)
                    self.name_entry.insert(0, name_elem.text)
                
                # Determine the objective type from CT data
                type_found = False
                if self.injector.is_valid_installation:
                    try:
                        ct_tree = ET.parse(self.injector.ct_file)
                        ct_root = ct_tree.getroot()
                        
                        for ct in ct_root.findall("CT"):
                            if ct.get("Num") == str(ct_num):
                                # Found the matching CT
                                type_elem = ct.find("Type")
                                if type_elem is not None and type_elem.text:
                                    try:
                                        # Try to find this type in our dropdown
                                        type_value = int(type_elem.text)
                                        
                                        # Find this type in the dropdown values
                                        if type_value in self.type_keys:
                                            # Set the type dropdown
                                            type_index = self.type_keys.index(type_value)
                                            self.type_var.set(self.type_values[type_index])
                                            # Load fields for this type
                                            self._on_type_selected(self.type_values[type_index])
                                            type_found = True
                                    except (ValueError, IndexError) as type_err:
                                        print(f"Error setting type: {type_err}")
                                break
                    except Exception as ct_err:
                        print(f"Error finding CT type: {ct_err}")
                
                if not type_found:
                    print("Type not found in dropdown, using default fields")
                
                # Load all fields from OCD
                for field_name, entry in self.field_entries.items():
                    # Find corresponding element in OCD
                    field_elem = ocd.find(field_name)
                    if field_elem is not None and field_elem.text is not None:
                        # Update field with value from OCD
                        entry.delete(0, tk.END)
                        entry.insert(0, field_elem.text)
                
                # Validate the CT number
                self._validate_ct(None)
                
                self.obj_info_label.configure(
                    text="Data has been Collected",
                    text_color="green",
                    fg_color="transparent"
                )
                
            except ET.ParseError as parse_err:
                self.obj_info_label.configure(
                    text=f"XML Parse Error: {str(parse_err)}",
                    text_color="red",
                    fg_color="transparent"
                )
            except Exception as e:
                self.obj_info_label.configure(
                    text="Error processing objective data",
                    text_color="red",
                    fg_color="transparent"
                )
                print(f"Error processing objective data: {e}")
                
        except Exception as e:
            self.obj_info_label.configure(
                text=f"Error: {str(e)}",
                text_color="red",
                fg_color="transparent"
            )

    def update_bms_path(self, new_path):
        """Update the BMS path display with a new path."""
        if new_path and new_path != self.bms_path:
            self.bms_path = new_path
            
            # Update the display
            self.bms_path_entry.configure(state="normal")
            self.bms_path_entry.delete(0, tk.END)
            self.bms_path_entry.insert(0, str(self.bms_path))
            self.bms_path_entry.configure(state="readonly")
            
            # Update the injector
            self.injector = BmsInjector(self.bms_path)
            self.installation_valid = self.injector.is_valid_installation
            
            # Update status indicator
            self.bms_status_indicator.configure(
                text="✓" if self.installation_valid else "✗",
                text_color="green" if self.installation_valid else "red"
            )
            
            # Reload objective types if installation is valid
            if self.installation_valid:
                self.objective_types = self._load_objective_types()
                self._load_type_data()

if __name__ == "__main__":
    # Test code
    root = tk.Tk()
    root.withdraw()
    
    app = BmsInjectionWindow(root, ct_num=123, obj_num=456)
    root.wait_window(app)
    
    if hasattr(app, 'result'):
        print("Result:", app.result)
    else:
        print("Cancelled")
    
    root.destroy() 
