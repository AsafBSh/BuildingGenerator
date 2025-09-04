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
import logging

# Set up logging
logger = logging.getLogger(__name__)

# Import processing window for long-running tasks
from processing_window import ProcessType, run_template_generation

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
        
        # Store initial parameters
        self.parent = parent
        self.initial_bms_path = bms_path
        self.initial_ct_file_path = ct_file_path
        self.ct_num = ct_num
        self.obj_num = obj_num
        self.obj_template = obj_template
        
        # Initialize placeholders
        self.bms_path = self.initial_bms_path
        self.installation_valid = False
        self.injector = None
        self.features = {}
        self.objective_types = {}
        self.current_template = {}
        self.field_entries = {}
        self.type_keys = []
        self.type_values = []
        self.loading = True
        self._destroying = False  # Flag to prevent multiple destroy calls
        self._scheduled_destroy = None  # Track scheduled destroy operations
        
        # Store all initialization functions here for deferred execution
        self.init_functions = [
            self._initialize_bms_path,           # Process BMS path
            self._initialize_injector,           # Create injector and validate installation
            self.load_previous_settings,         # Load saved settings
            self._initialize_objective_types,     # Load objective types
            self._validate_templates,             # Validate templates
        ]
        
        # Set up the window
        self.title("BMS Objective Configuration")
        self.geometry("630x750")
        self.minsize(630, 750)
        self.resizable(True, True)
        self.configure(bg="#F0F0F5")
        
        # Initialize UI with empty values
        self._init_ui_empty()
        
        # Center the window on screen
        # self.update_idletasks()
        # width = self.winfo_width()
        # height = self.winfo_height()
        # x = (self.winfo_screenwidth() // 2) - (width // 2)
        # y = (self.winfo_screenheight() // 2) - (height // 2)
        # self.geometry(f"{width}x{height}+{x}+{y}")
        
        # Schedule initialization after UI is shown
        # This executes all initialization functions one by one
        self.after(100, self._run_deferred_initialization)
        
    def _get_settings_path(self):
        """Get the path to the saved settings file in the data_components directory"""
        return get_json_path(JsonFiles.SAVED_OBJECTIVE_SETTINGS)
    
    def _run_deferred_initialization(self):
        """Run all initialization functions in sequence after UI is loaded."""
        logger.info("Running deferred initialization...")
        
        # Execute each initialization function in sequence
        for func in self.init_functions:
            func_name = func.__name__
            logger.debug(f"Running {func_name}...")
            func()
        
        # Finally populate the UI with loaded data
        self._populate_ui()
        
        # Loading complete
        self.loading = False
        logger.info("Initialization and UI population complete")
    
    def _create_templates_with_processing_window(self):
        """Create objective and CT templates using the processing window."""
        logger.info("[BMS WINDOW] Creating templates with processing window during initialization")
        success = True
        
        # First create objective templates if needed
        if not self.injector.objective_templates or getattr(self.injector, 'templates_need_creation', False):
            logger.info("[BMS WINDOW] Creating objective templates with processing window")
            success_obj = self.analyze_ocd_files_and_create_objective_template()
            success = success and success_obj
            if success_obj:
                logger.info("[BMS WINDOW] Successfully created objective templates")
            else:
                logger.warning("[BMS WINDOW] Failed to create objective templates")
                success = False
        
        # Then create CT templates if needed
        if not self.injector.ct_templates or getattr(self.injector, 'templates_need_creation', False):
            logger.info("[BMS WINDOW] Creating CT templates with processing window")
            success_ct = self.analyze_ct_file_and_create_template()
            success = success and success_ct
            if success_ct:
                logger.info("[BMS WINDOW] Successfully created CT templates")
            else:
                logger.warning("[BMS WINDOW] Failed to create CT templates")
                success = False
                
        # Clear the templates_need_creation flag if set
        if hasattr(self.injector, 'templates_need_creation') and self.injector.templates_need_creation:
            self.injector.templates_need_creation = False
            
        return success
    
    def _initialize_bms_path(self):
        """Process and initialize the BMS path."""
        # If ct_file_path is provided, use its parent directory as bms_path
        if self.initial_ct_file_path:
            from pathlib import Path
            
            # Use the parent directory of the Falcon4_CT.xml file as BMS path
            ct_file = Path(self.initial_ct_file_path)
            if ct_file.exists():
                # Navigate up to find the base BMS directory
                # Typically it's 2 or 3 levels up from the CT file
                parent_dir = ct_file.parent
                if "TerrData" in str(parent_dir):
                    self.bms_path = parent_dir.parent  # TerrData/.. -> Data
                    if "Data" in str(self.bms_path):
                        self.bms_path = self.bms_path.parent  # Data/.. -> BMS root
        
        logger.info(f"BMS path set to: {self.bms_path}")
    
    def _initialize_injector(self):
        """Create the BMS injector and validate the installation."""
        logger.info(f"Creating BMS injector with path: {self.bms_path}")
        
        # Check if backup_bms_files setting is available in parent's shared_data
        backup = True  # Default to True for safety
        if hasattr(self.parent, 'shared_data') and 'backup_bms_files' in self.parent.shared_data:
            backup_value = self.parent.shared_data['backup_bms_files']
            backup = backup_value == '1'
            logger.debug(f"Using backup setting from configuration: {backup}")
        
        # Check if backup_features_files setting is available in parent's shared_data
        backup_features = True  # Default to True for safety
        if hasattr(self.parent, 'shared_data') and 'backup_features_files' in self.parent.shared_data:
            backup_features_value = self.parent.shared_data['backup_features_files']
            backup_features = backup_features_value == '1'
            logger.debug(f"Using backup features setting from configuration: {backup_features}")
        
        # Log the settings to ensure they're being applied correctly
        logger.info(f"Creating BMS injector with backup={backup}, backup_features={backup_features}")
        logger.info(f"BMS file backup {'enabled' if backup else 'disabled'}")
        logger.info(f"BMS features backup {'enabled' if backup_features else 'disabled'}")
        
        # Create the injector with auto-create templates set to false and appropriate backup settings
        # Templates will be created in a separate step with a progress window
        self.injector = BmsInjector(self.bms_path, backup=backup, backup_features=backup_features, auto_create_templates=False)
        logger.info(f"Created BmsInjector with backup={backup}, backup_features={backup_features}")
        
        # Check if installation is valid
        self.installation_valid = self.injector.is_valid_installation
        logger.info(f"BMS installation valid: {self.installation_valid}")
        
        # Update status indicator in UI
        self.bms_status_indicator.configure(
            text="✓" if self.installation_valid else "✗",
            text_color="green" if self.installation_valid else "red"
        )
    
    def _initialize_objective_types(self):
        """Load objective types."""
        self.objective_types = self._load_objective_types()
        logger.info(f"Loaded {len(self.objective_types)} objective types")
    
    def _validate_templates(self):
        """Validate that objective and CT templates exist and pass basic validation."""
        # Check if templates need to be created first
        if hasattr(self.injector, 'templates_need_creation') and self.injector.templates_need_creation:
            logger.info("Templates need to be created before validation, using processing window...")
            self._create_templates_with_processing_window()
        
        # Validate objective templates
        logger.info("Validating objective templates...")
        if not self.validate_objective_templates():
            return False
        
        # Validate CT templates
        logger.info("Validating CT templates...")
        if not self.validate_ct_templates():
            return False
        
        return True
    
    def _populate_ui(self):
        """Populate the UI with the loaded data."""
        # Update BMS path entry
        self.bms_path_entry.configure(state="normal")
        self.bms_path_entry.delete(0, tk.END)
        self.bms_path_entry.insert(0, str(self.bms_path))
        self.bms_path_entry.configure(state="readonly")
        
        # Update BMS status indicator
        self.bms_status_indicator.configure(
            text="✓" if self.installation_valid else "✗",
            text_color="green" if self.installation_valid else "red"
        )
        
        # Set CT and objective numbers if provided
        if self.ct_num is not None:
            self.ct_entry.delete(0, tk.END)
            self.ct_entry.insert(0, str(self.ct_num))
            self._validate_ct(None)
        
        if self.obj_num is not None:
            self.obj_entry.delete(0, tk.END)
            self.obj_entry.insert(0, str(self.obj_num))
            self._validate_obj(None)
        
        # Update objective types dropdown
        if self.objective_types:
            # Convert objective types to list of strings for dropdown and sort alphabetically
            self.objective_types_sorted = {k: v for k, v in sorted(self.objective_types.items(), key=lambda item: item[1])}
            self.type_values = list(self.objective_types_sorted.values())
            self.type_keys = list(self.objective_types_sorted.keys())
            
            # Configure dropdown with loaded values
            self.type_dropdown.configure(values=self.type_values)
            
            # Select first value by default
            if self.type_values:
                self.type_var.set(self.type_values[0])
        
        # Apply saved name if available
        if hasattr(self, 'saved_name') and self.saved_name:
            self.name_entry.delete(0, tk.END)
            self.name_entry.insert(0, self.saved_name)
        
        # Apply saved type if available
        if hasattr(self, 'saved_type') and self.saved_type and self.saved_type in self.type_keys:
            type_index = self.type_keys.index(self.saved_type)
            if type_index >= 0 and type_index < len(self.type_values):
                self.type_var.set(self.type_values[type_index])
        
        # Load field data based on type selection
        self._load_type_data()
        
    def _init_ui_empty(self):
        """Initialize the user interface components with empty values."""
        # Configure the grid
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=0)  # Header
        self.grid_rowconfigure(1, weight=1)  # Main content
        self.grid_rowconfigure(2, weight=0)  # Footer
        
        # Main frame
        main_frame = Ctk.CTkFrame(self, fg_color="#E7E7EF")
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)
        self.main_frame = main_frame  # Store reference for later use
        
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
        
        # Status indicator for BMS path - initial state as not validated
        self.bms_status_indicator = Ctk.CTkLabel(
            bms_path_frame,
            text="✗",
            width=18,
            text_color="red",
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
        
        # Set empty path initially
        self.bms_path_entry.configure(state="normal")
        self.bms_path_entry.delete(0, tk.END)
        self.bms_path_entry.insert(0, "")
        self.bms_path_entry.configure(state="readonly")
        
        # Basic settings section
        settings_frame = Ctk.CTkFrame(main_frame, fg_color="#E0E8F0", border_width=1, border_color="#B3C8DD")
        settings_frame.pack(fill="x", padx=5, pady=5)
        self.settings_frame = settings_frame  # Store reference for later use
        
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
        
        # Create empty dropdown initially
        self.type_values = [""]  # Empty placeholder
        self.type_keys = [0]  # Default key
        
        self.type_var = tk.StringVar(value="")
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
        self.type_dropdown.pack(side="left", padx=5, fill="x", expand=True, pady=(4, 4))
        
        
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
        
        # Create all common fields with empty values
        self._create_all_fields()
        
        # Button section
        button_frame = Ctk.CTkFrame(main_frame, fg_color="#E0E8F0", border_width=1, border_color="#B3C8DD")
        button_frame.pack(fill="x", padx=5, pady=10)
        
        # Reset Type to Default button (stays on the left)
        Ctk.CTkButton(
            button_frame,
            text="Reset Type to Default",
            command=self._reset_type_to_default,
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
            command=self._cancel_operation,
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

    
    def regenerate_templates(self):
        """Regenerate objective and CT templates using the processing window."""
        # Ask for confirmation
        response = messagebox.askyesno(
            "Regenerate Templates", 
            "This will regenerate all objective and CT templates using the processing window. This may take a few minutes. Continue?"
        )
        if not response:
            return
            
        # Force regeneration of templates using the processing window
        logger.info("[PROCESSING WINDOW] Regenerating templates with processing window")
        
        # First regenerate the objective templates
        success_objective = self.analyze_ocd_files_and_create_objective_template()
        
        # Then regenerate the CT templates
        success_ct = self.analyze_ct_file_and_create_template()
        
        # Show success or failure message
        if success_objective and success_ct:
            messagebox.showinfo(
                "Templates Regenerated", 
                "All templates have been successfully regenerated."
            )
        else:
            messagebox.showwarning(
                "Template Regeneration Incomplete", 
                "Some templates could not be regenerated. Check the console for details."
            )
            
    def analyze_ocd_files_and_create_objective_template(self):
        """
        Analyze OCD files and create objective templates using the processing window.
        
        Returns:
            bool: True if templates were created successfully, False otherwise
        """
        from processing_window import ProcessType, run_template_generation
        
        logger.info("[BMS WINDOW] Starting objective template generation with processing window")
        
        # Define the template generation task - NOTE: this task does NOT take any parameters
        def generate_objective_templates_task():
            logger.info("[BMS WINDOW] Creating objective templates...")
            try:
                # First remove existing templates if any
                if self.injector.objective_templates:
                    self.injector.objective_templates = {}
                
                # Create new templates
                self.injector.objective_templates = self.injector._create_default_templates()
                if not self.injector.objective_templates:
                    logger.error("[BMS WINDOW] Error: No objective templates were created")
                    return False
                
                # Save the templates for future use
                self.injector.save_templates()
                logger.info("[BMS WINDOW] Objective templates created and saved successfully")
                return True
            except Exception as e:
                logger.error(f"[BMS WINDOW] Error creating objective templates: {e}")
                import traceback
                traceback.print_exc()
                return False
        
        # Run the task with a processing window
        return run_template_generation(
            parent=self,
            task_function=generate_objective_templates_task,
            process_type=ProcessType.OBJECTIVE_TEMPLATE_GENERATION,
            title="Generating Objective Templates",
            message="Analyzing objective files and creating templates..."
        )
        
    def analyze_ct_file_and_create_template(self):
        """
        Analyze CT file and create CT templates using the processing window.
        
        Returns:
            bool: True if templates were created successfully, False otherwise
        """
        from processing_window import ProcessType, run_template_generation
        
        logger.info("[BMS WINDOW] Starting CT template generation with processing window")
        
        # Define the template generation task - NOTE: this task does NOT take any parameters
        def generate_ct_templates_task():
            logger.info("[BMS WINDOW] Creating CT templates...")
            try:
                # First remove existing templates if any
                if self.injector.ct_templates:
                    self.injector.ct_templates = {}
                
                # Create new templates
                self.injector.ct_templates = self.injector._create_default_ct_templates()
                if not self.injector.ct_templates:
                    logger.error("[BMS WINDOW] Error: No CT templates were created")
                    return False
                
                # Save the templates for future use
                self.injector.save_templates()
                logger.info("[BMS WINDOW] CT templates created and saved successfully")
                return True
            except Exception as e:
                logger.error(f"[BMS WINDOW] Error creating CT templates: {e}")
                import traceback
                traceback.print_exc()
                return False
        
        # Run the task with a processing window
        return run_template_generation(
            parent=self,
            task_function=generate_ct_templates_task,
            process_type=ProcessType.CT_TEMPLATE_GENERATION,
            title="Generating CT Templates",
            message="Analyzing CT file and creating templates..."
        )
    
    def _validate_inputs(self):
        """Validate all user inputs before saving or adding an objective."""
        # Check CT number
        try:
            ct_num = int(self.ct_entry.get())
            # Accept if CT exists and is an objective, OR if it's the next available number (highest + 1)
            is_existing_objective_ct = self.injector.is_objective_ct(ct_num)
            is_next_new_ct = False
            highest_ct = 0
            try:
                if self.injector.is_valid_installation:
                    logger.debug(f"[_validate_inputs] Parsing CT file to compute highest CT (path={self.injector.ct_file})")
                    tree = ET.parse(self.injector.ct_file)
                    root = tree.getroot()
                    for ct in root.findall("CT"):
                        try:
                            ct_val = int(ct.get("Num"))
                            highest_ct = max(highest_ct, ct_val)
                        except (ValueError, TypeError):
                            logger.debug("[_validate_inputs] Skipping CT with non-integer Num")
                            pass
                is_next_new_ct = (ct_num == highest_ct + 1)
            except Exception as compute_err:
                logger.warning(f"[_validate_inputs] Failed to compute highest CT: {compute_err}")
                # If we cannot determine highest_ct, fall back to existing-objective check only
                is_next_new_ct = False
            logger.info(f"[_validate_inputs] CT check: ct_num={ct_num}, is_existing_objective_ct={is_existing_objective_ct}, highest_ct={highest_ct}, is_next_new_ct={is_next_new_ct}")
            if not is_existing_objective_ct and not is_next_new_ct:
                logger.warning(f"[_validate_inputs] CT invalid: ct_num={ct_num}, next_available={highest_ct + 1}")
                messagebox.showerror(
                    "Invalid CT",
                    f"CT {ct_num} is not a valid objective CT number. Next available is {highest_ct + 1}."
                )
                return False
        except ValueError:
            logger.warning("[_validate_inputs] CT number is not an integer")
            messagebox.showerror("Invalid CT", "CT number must be an integer.")
            return False
            
        # Check objective number
        try:
            obj_num = int(self.obj_entry.get())
            if obj_num <= 0:
                messagebox.showerror(
                    "Invalid Objective", 
                    "Objective number must be greater than zero."
                )
                return False
                
            # Note: Overwrite confirmation will happen later in MainCode.py when features are generated
            # This allows users to configure settings without being prompted about overwriting
        except ValueError:
            messagebox.showerror("Invalid Objective", "Objective number must be an integer.")
            return False
            
        # Check objective name
        name = self.name_entry.get()
        if not name:
            messagebox.showerror("Invalid Name", "Objective name cannot be empty.")
            return False
            
        # Check objective type
        if not self.type_dropdown.get():
            messagebox.showerror("Invalid Type", "Please select an objective type.")
            return False
            
        return True
        
    def _get_form_values(self):
        """Get all form values as a simplified dictionary with only core data."""
        try:
            # Check if window is being destroyed
            if hasattr(self, '_destroying') and self._destroying:
                return {}
                
            # Only get core values without fields as per requirements
            settings = {
                "reset_pd": self.reset_var.get(),
                "bms_path": str(self.bms_path),
                "ct_num": int(self.ct_entry.get()),
                "obj_num": int(self.obj_entry.get()),
                "name": self.name_entry.get(),
                "type": self._get_selected_type_key()
                # Fields are no longer saved here, they are now saved to objectives_template.json
            }
            
            return settings
        except (tk.TclError, AttributeError) as e:
            logger.warning(f"Error getting form values (window may be destroying): {e}")
            return {}

    def load_previous_settings(self):
        """Load previous saved settings if they exist."""
        try:
            # Log the settings path for debugging
            settings_path = get_json_path(JsonFiles.SAVED_OBJECTIVE_SETTINGS)
            logger.info(f"Loading settings from: {settings_path}")
            
            # Load settings using json_path_handler
            saved_settings = load_json(JsonFiles.SAVED_OBJECTIVE_SETTINGS, default={})
            
            # Only load previous settings if CT and obj numbers match
            if saved_settings and (saved_settings.get("ct_num") == self.ct_num and 
                saved_settings.get("obj_num") == self.obj_num):
                
                # Store name for later application
                self.saved_name = saved_settings.get("name", "")
                
                # Store type for later selection and field loading
                self.saved_type = saved_settings.get("type")
                
                # Store BMS path and reset_pd values
                saved_bms_path = saved_settings.get("bms_path", "")
                if saved_bms_path and not self.bms_path:
                    self.bms_path = saved_bms_path
                    
                self.reset_var.set(saved_settings.get("reset_pd", True))
                
                # Load field values from objective_templates.json based on the saved type
                if self.saved_type is not None:
                    # Get template for this type
                    objective_templates = load_json(JsonFiles.OBJECTIVE_TEMPLATES, default={})
                    template_type = str(self.saved_type)
                    
                    if template_type in objective_templates:
                        self.obj_template = objective_templates[template_type]
                        logger.info(f"Loaded field values from objective_templates.json for type {template_type}")
                    else:
                        self.obj_template = {}
                        logger.warning(f"Type {template_type} not found in objective_templates.json")
                else:
                    self.obj_template = {}
                    
                logger.debug(f"  Saved Type: {self.saved_type}")
                logger.debug(f"  Saved Name: {self.saved_name}")
                logger.debug(f"  Saved BMS Path: {saved_bms_path}")
                logger.debug(f"  Reset PD: {saved_settings.get('reset_pd', True)}")
                logger.debug(f"  Field Values: {len(self.obj_template)}")
            else:
                logger.info("No matching previous settings found")
                if saved_settings:
                    logger.debug(f"  Found settings for CT:{saved_settings.get('ct_num')} Obj:{saved_settings.get('obj_num')}")
                else:
                    logger.debug("  No saved settings file found")
                
        except Exception as e:
            logger.error(f"ERROR loading previous settings: {e}")
            traceback.print_exc()
            
    def _load_objective_types(self):
        """Load objective types from cache or from a default list."""
        # Try to get from cache first
        cached_templates = objective_cache.get_objective_templates()
        if cached_templates:
            # Filter out any invalid types (only use 1-31) and sort by type number
            valid_types = {int(k): f"{self._get_type_name(int(k))} - {k}" 
                         for k in cached_templates.keys() 
                         if k.isdigit() and 1 <= int(k) <= 31}
            return valid_types
        
        # If not in cache, use the injector's templates
        if self.injector.objective_templates:
            # Filter out any invalid types (only use 1-31) and sort by type number
            valid_types = {int(k): f"{self._get_type_name(int(k))} - {k}" 
                         for k in self.injector.objective_templates.keys() 
                         if k.isdigit() and 1 <= int(k) <= 31}
            return valid_types
        
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
        """Legacy method for initializing the user interface components.
        This method is kept for compatibility with existing code.
        In the new two-phase initialization, _init_ui_empty() and _populate_ui() are used instead."""
        logger.warning("Using legacy _init_ui method instead of two-phase initialization")
        
        # Just call the empty UI initialization and populate it immediately
        self._init_ui_empty()
        self._populate_ui()
        
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
        logger.info(f"LOADING TYPE DATA: Type {type_key}")
        
        # ONLY load directly from the JSON file - no fallback to cache or injector
        from utils.json_path_handler import load_json, JsonFiles
        objective_templates_file = load_json(JsonFiles.OBJECTIVE_TEMPLATES, default={})
        template = {}
        
        # Get template for this type from JSON file only
        if objective_templates_file and str(type_key) in objective_templates_file:
            template = objective_templates_file[str(type_key)]
            logger.debug(f"  Template source: objective_templates.json file")
        else:
            # If not found in file, use empty template - validation should prevent this
            logger.warning(f"  Type {type_key} not found in objective_templates.json")
            template = {}
        
        # Debug print template
        logger.debug(f"  Base template fields: {len(template)}")
        
        # Override with user-saved template if available
        user_template = objective_cache.get_user_templates(int(type_key))
        if user_template:
            logger.debug(f"  Applying user template with {len(user_template)} fields")
            template.update(user_template)
        else:
            logger.debug(f"  No user template found for type {type_key}")
        
        # Override with saved values if available
        if self.obj_template and isinstance(self.obj_template, dict):
            logger.debug(f"  Applying saved object template with {len(self.obj_template)} fields")
            template.update(self.obj_template)
        
        # Store the current template for later use
        self.current_template = template
        
        # Debug print the final template being applied
        logger.debug(f"  Final template has {len(template)} fields")
        
        # Update existing fields with template values
        for field_name, entry in self.field_entries.items():
            # Always update all fields when changing types
            value = template.get(field_name, "0")  # Default to "0" if not in template
            
            # Debug print each field update
            logger.debug(f"    Setting field {field_name} = {value}")
            
            # Update the entry
            entry.delete(0, tk.END)
            entry.insert(0, str(value))
    
    def _on_type_selected(self, selection):
        """Handle type selection and update fields."""
        # Prevent unnecessary field loading during initialization
        if self.loading:
            logger.debug("Still loading, not updating fields yet")
            return
        
        # Get the type key for this selection
        selected_index = self.type_values.index(selection)
        selected_type_key = self.type_keys[selected_index]
        
        # Enhanced logging with more detail
        logger.info(f"OBJECTIVE TYPE SELECTED: {selection}")
        logger.debug(f"  Type Key: {selected_type_key}")
        logger.debug(f"  Type Index: {selected_index}")
        
        # Load the template data for the selected type
        self._load_type_data()
    
    def _reset_fields(self):
        """Reset all fields to default values."""
        # ONLY load directly from the JSON file - consistent with _load_type_data
        from utils.json_path_handler import load_json, JsonFiles
        objective_templates_file = load_json(JsonFiles.OBJECTIVE_TEMPLATES, default={})
        template = {}
        
        # Get template for this type from JSON file only
        type_key = self._get_selected_type_key()
        if objective_templates_file and str(type_key) in objective_templates_file:
            template = objective_templates_file[str(type_key)]
            logger.debug(f"Using template from objective_templates.json file with {len(template)} fields")
        else:
            logger.warning(f"Type {type_key} not found in objective_templates.json")
            template = {}
        
        # Update fields with template values
        field_count = 0
        for field_name, entry in self.field_entries.items():
            value = template.get(field_name, "0")
            entry.delete(0, tk.END)
            entry.insert(0, str(value))
            field_count += 1
            logger.debug(f"Reset field {field_name} = {value}")
        
        logger.info(f"Reset {field_count} fields completed")
            
    def _reset_type_to_default(self):
        """
        Calculate median values for fields based on existing objectives of the same type.
        Only updates the GUI fields, does not save data to any file.
        """
        from processing_window import ProcessType, run_template_generation
        from tkinter import messagebox
        import os
        
        # 1. Initialization - Get the selected type and validate BMS path
        type_key = self._get_selected_type_key()
        if not type_key:
            logger.warning("No objective type selected")
            messagebox.showwarning("No Type Selected", "Please select an objective type first.")
            return False
            
        type_name = self._get_type_name(type_key)
        logger.info(f"RESETTING VALUES FOR OBJECTIVE TYPE: {type_key} ({type_name})")
        
        # Ensure BMS path is valid
        if not self.installation_valid or not self.bms_path or not os.path.isdir(self.bms_path):
            logger.error("Invalid BMS installation path")
            messagebox.showerror("Error", "Invalid BMS installation path")
            return False
            
        # Define the calculation task that will run in the background
        def calculate_default_values_task(processing_window=None):
            """Background task to calculate median values for the selected objective type."""
            return self._calculate_median_values_for_type(type_key, type_name)
        
        # Run the calculation with a processing window
        logger.info(f"[CALCULATE DEFAULT] Starting default value calculation with processing window for type {type_key}")
        result = run_template_generation(
            parent=self,
            task_function=calculate_default_values_task,
            process_type=ProcessType.CALCULATE_DEFAULT_VALUES,
            title="Calculating Default Values",
            message=f"Calculating median values for {type_name} objectives..."
        )
        
        # Handle the result
        if result and isinstance(result, dict) and result.get('success'):
            calculated_values = result.get('calculated_values', {})
            ocd_count = result.get('ocd_count', 0)
            field_count = result.get('field_count', 0)
            
            # Update the GUI fields with calculated values
            self._update_gui_fields_with_values(calculated_values)
            
            # Show success message
            messagebox.showinfo(
                "Reset Complete",
                f"Successfully calculated median values from {ocd_count} existing objectives.\n"
                f"Updated {field_count} fields with median values."
            )
            return True
        elif result and isinstance(result, dict) and result.get('success') is False:
            # No matching objectives found
            messagebox.showwarning(
                "No Matching Objectives Found",
                f"No objectives of type {type_key} ({type_name}) were found.\n"
                f"Field values have been kept as is."
            )
            return False
        else:
            # Error occurred
            messagebox.showerror(
                "Error",
                "An error occurred while calculating default values. Check the console for details."
            )
            return False
    
    def _calculate_median_values_for_type(self, type_key, type_name):
        """
        Calculate median values for fields based on existing objectives of the given type.
        This method contains the core processing logic separated from UI updates.
        
        Args:
            type_key: The objective type key (1-31)
            type_name: The human-readable name of the objective type
            
        Returns:
            dict: Result dictionary with success status, calculated values, and counts
        """
        import xml.etree.ElementTree as ET
        from pathlib import Path
        import os
        import traceback
        
        # Define field names to collect values for
        median_fields = [
            "DataRate", "DeaggDistance", "Det_NoMove", "Det_Foot", "Det_Wheeled",
            "Det_Tracked", "Det_LowAir", "Det_Air", "Det_Naval", "Det_Rail",
            "Dam_None", "Dam_Penetration", "Dam_HighExplosive", "Dam_Heave", "Dam_Incendairy",
            "Dam_Proximity", "Dam_Kinetic", "Dam_Hydrostatic", "Dam_Chemical", "Dam_Nuclear",
            "Dam_Other", "ObjectiveIcon"
        ]
        
        # Dictionary to store values by field
        field_values = {field: [] for field in median_fields}
        
        try:
            # 2. CT File Processing - Load the CT file
            ct_file_path = os.path.join(self.bms_path, "Falcon4_CT.xml")
            if not os.path.exists(ct_file_path):
                logger.error(f"CT file not found at {ct_file_path}")
                return {
                    'success': False,
                    'error': f"CT file not found at {ct_file_path}"
                }
                
            logger.info(f"Loading CT file: {ct_file_path}")
            ct_tree = ET.parse(ct_file_path)
            ct_root = ct_tree.getroot()
            
            # Verify we have CT entries with the target type
            matching_ct_entries = []
            for ct_elem in ct_root.findall('.//CT'):
                type_elem = ct_elem.find("Type")
                if type_elem is not None and type_elem.text and type_elem.text.strip().isdigit():
                    ct_type = int(type_elem.text.strip())
                    if ct_type == type_key:
                        ct_num = ct_elem.get("Num")
                        matching_ct_entries.append(ct_num)
            
            # 3. OCD Directory Scanning
            obj_dir = os.path.join(self.bms_path, "ObjectiveRelatedData")
            if not os.path.exists(obj_dir) or not os.path.isdir(obj_dir):
                logger.error(f"ObjectiveRelatedData directory not found at {obj_dir}")
                return {
                    'success': False,
                    'error': f"ObjectiveRelatedData directory not found at {obj_dir}"
                }
                
            # Verify CT file structure
            ct_entries = ct_root.findall('.//CT')
            if not ct_entries:
                # Try alternative format if standard format not found
                ct_entries = ct_root.findall('./CT/Entry')
            
            # Get all OCD directories
            ocd_dirs = [d for d in os.listdir(obj_dir) if os.path.isdir(os.path.join(obj_dir, d)) and d.startswith("OCD_")]
            logger.info(f"Found {len(ocd_dirs)} OCD directories")
            
            # Counter for found OCD files of our type
            ocd_count = 0
            processed_count = 0
            
            # Process each OCD directory
            for ocd_dir_name in ocd_dirs:
                processed_count += 1
                if processed_count % 100 == 0:
                    logger.debug(f"Progress: Processed {processed_count}/{len(ocd_dirs)} directories...")
                    
                # Find the OCD XML file in this directory
                ocd_dir_path = os.path.join(obj_dir, ocd_dir_name)
                ocd_file = None
                
                for filename in os.listdir(ocd_dir_path):
                    if filename.startswith("OCD_") and filename.upper().endswith(".XML"):
                        ocd_file = os.path.join(ocd_dir_path, filename)
                        break
                
                if not ocd_file:
                    continue  # No OCD XML file found in this directory
                
                try:
                    # Parse the OCD file
                    ocd_tree = ET.parse(ocd_file)
                    ocd_root = ocd_tree.getroot()
                    ocd_element = ocd_root.find("OCD")
                    
                    if ocd_element is None:
                        continue  # No OCD element in this file
                        
                    # Get the CT Index from this OCD file
                    ct_idx_elem = ocd_element.find("CtIdx")
                    if ct_idx_elem is None or not ct_idx_elem.text:
                        continue  # No CT Index in this file
                        
                    # Try different formats of CT index to handle potential mismatches
                    ct_idx_raw = ct_idx_elem.text.strip()
                    
                    # Create a list of possible CT index formats to try
                    ct_idx_variants = [
                        ct_idx_raw,                  # Original format
                        ct_idx_raw.lstrip('0'),      # Remove leading zeros
                        f"{int(ct_idx_raw)}" if ct_idx_raw.isdigit() else ct_idx_raw  # Convert to int and back to string
                    ]
                    
                    # Check if any of the CT index variants has the matching type
                    matching_type = False
                    
                    for ct_idx in ct_idx_variants:
                        # Try to find the CT entry with this index variant
                        ct_elem = ct_root.find(f".//CT[@Num='{ct_idx}']")
                        
                        # If not found by @Num attribute, try finding by Index element
                        if ct_elem is None:
                            # Search for CT entries with matching Index element
                            for entry in ct_root.findall("./CT/Entry"):
                                idx_elem = entry.find("Index")
                                if idx_elem is not None and idx_elem.text and idx_elem.text.strip() == ct_idx:
                                    # Found by Index element, now check the parent CT element
                                    ct_elem = entry.getparent() if hasattr(entry, 'getparent') else None
                                    break
                        
                        if ct_elem is not None:
                            # Found the CT, check its type
                            type_elem = ct_elem.find("Type")
                            if type_elem is not None and type_elem.text:
                                try:
                                    entry_type = int(type_elem.text.strip())
                                    # Compare with our target type
                                    if entry_type == type_key:
                                        matching_type = True
                                        break
                                except ValueError:
                                    pass  # Skip if type can't be converted to int
                    
                    # Skip if this objective doesn't have the type we're looking for
                    if not matching_type:
                        continue
                        
                    # Found an OCD file with matching type - collect field values
                    ocd_count += 1
                    
                    # Extract values for all our fields of interest
                    for field in median_fields:
                        field_elem = ocd_element.find(field)
                        if field_elem is not None and field_elem.text:
                            try:
                                # Convert to the appropriate type (float or int)
                                field_text = field_elem.text.strip()
                                if "." in field_elem.text:
                                    value = float(field_text)
                                else:
                                    value = int(field_text)
                                field_values[field].append(value)
                            except (ValueError, TypeError) as e:
                                # Keep as string if conversion fails
                                field_values[field].append(field_elem.text)
                
                except Exception as e:
                    # Log the error but continue processing other files
                    logger.error(f"Error processing OCD file {ocd_file}: {e}")
            
            # Process complete
            
            # 4. Field Value Calculation - Calculate median values for each field
            calculated_values = {}
            
            for field in median_fields:
                values = field_values[field]
                
                if values and len(values) > 0:
                    # We found values for this field in OCD files
                    if all(isinstance(v, (int, float)) for v in values):
                        # For numeric values, calculate the median
                        sorted_values = sorted(values)
                        n = len(sorted_values)
                        
                        if n % 2 == 0:
                            # Even number of values - average the middle two
                            mid_right = n // 2
                            mid_left = mid_right - 1
                            median = (sorted_values[mid_left] + sorted_values[mid_right]) / 2
                        else:
                            # Odd number of values - take the middle one
                            median = sorted_values[n // 2]
                        
                        # Keep integers as integers
                        if all(isinstance(v, int) for v in values):
                            median = int(median)
                        
                        calculated_values[field] = str(median)
                    else:
                        # For non-numeric values, use the most common value
                        value_counts = {}
                        for v in values:
                            if v is not None:
                                value_counts[v] = value_counts.get(v, 0) + 1
                        
                        if value_counts:
                            most_common = max(value_counts.items(), key=lambda x: x[1])[0]
                            calculated_values[field] = str(most_common)
                        else:
                            # If we can't determine the most common, keep current value
                            if field in self.field_entries:
                                current_value = self.field_entries[field].get()
                                calculated_values[field] = current_value
                            else:
                                calculated_values[field] = "0"
                else:
                    # No values found for this field in any OCD files
                    if field in self.field_entries:
                        current_value = self.field_entries[field].get()
                        calculated_values[field] = current_value
                    else:
                        calculated_values[field] = "0"
            
            # Count fields that would be updated
            field_count = len([field for field in calculated_values.keys() if field in self.field_entries])
            
            # Return result based on success
            if ocd_count == 0:
                # No matching OCD files found
                logger.warning(f"No objectives of type {type_key} ({type_name}) were found")
                return {
                    'success': False,
                    'ocd_count': 0,
                    'field_count': 0,
                    'calculated_values': {}
                }
            else:
                # Successfully calculated values
                logger.info(f"Successfully calculated median values from {ocd_count} existing objectives, updating {field_count} fields")
                return {
                    'success': True,
                    'ocd_count': ocd_count,
                    'field_count': field_count,
                    'calculated_values': calculated_values
                }
                
        except Exception as e:
            # Log the error
            error_msg = f"Error calculating median values: {e}"
            logger.error(f"ERROR: {error_msg}")
            traceback.print_exc()
            return {
                'success': False,
                'error': error_msg,
                'ocd_count': 0,
                'field_count': 0,
                'calculated_values': {}
            }
    
    def _update_gui_fields_with_values(self, calculated_values):
        """
        Update the GUI field entries with the calculated values.
        
        Args:
            calculated_values: Dictionary of field names to calculated values
        """
        updated_fields = set()
        field_count = 0
        
        # Make sure we have the field entries before trying to update them
        if not hasattr(self, 'field_entries') or not self.field_entries:
            logger.warning("No field entries available to update")
            return 0
            
        for field_name, entry in self.field_entries.items():
            if field_name in calculated_values and field_name not in updated_fields:
                value = calculated_values[field_name]
                # Clear and update the entry
                entry.delete(0, tk.END)
                entry.insert(0, str(value))
                
                # Count updated fields and mark as updated
                field_count += 1
                updated_fields.add(field_name)
                logger.debug(f"Updated field {field_name} = {value}")
        
        logger.info(f"Updated {field_count} GUI fields with calculated values")
        return field_count

    
    def _save_settings(self):
        """Save settings and close the window."""
        logger.info("SAVING OBJECTIVE SETTINGS")
        
        # First validate all inputs including overwrite confirmation
        if not self._validate_inputs():
            logger.info("Settings save cancelled due to validation failure")
            return
        
        # If we get here, validation passed - extract the validated values
        try:
            ct_num = int(self.ct_entry.get())
            obj_num = int(self.obj_entry.get())
            logger.debug(f"CT Number: {ct_num}")
            logger.debug(f"Objective Number: {obj_num}")
        except ValueError:
            logger.error("Invalid CT or Objective Number")
            messagebox.showerror(
                "Invalid Input",
                "CT Number and Objective Number must be integers."
            )
            return
        
        # Check for missing name
        name = self.name_entry.get().strip()
        if not name:
            logger.error("Missing objective name")
            messagebox.showerror(
                "Missing Name",
                "Objective Name is required."
            )
            return
        
        logger.debug(f"Objective Name: {name}")
        
        # Get selected type
        type_key = self._get_selected_type_key()
        selected_type = self.type_var.get()
        logger.debug(f"Selected Type: {selected_type}")
        logger.debug(f"Type Key: {type_key}")
        
        # Get field values - stored as strings to make saving/loading simpler
        fields = {}
        for field_name, entry in self.field_entries.items():
            raw_value = entry.get().strip()
            fields[field_name] = raw_value
        
        # Debug print the field values
        logger.debug(f"Collected {len(fields)} field values")
        
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
        
        # Create the result dict for saved_objective_settings.json - WITHOUT fields
        settings_data = {
            "ct_num": ct_num,
            "obj_num": obj_num,
            "name": name,
            "type": type_key,
            "reset_pd": self.reset_var.get(),
            "bms_path": self.bms_path_entry.get()
        }
        
        # Store in instance variable - use typed fields for actual operation
        # Still include fields in self.result for internal use
        self.result = {
            "status": "success",  # Indicate successful validation and user confirmation
            "ct_num": ct_num,
            "obj_num": obj_num,
            "name": name,
            "type": type_key,
            "fields": typed_fields,  # Use converted values for operation
            "reset_pd": self.reset_var.get(),
            "bms_path": self.bms_path_entry.get()
        }
        
        logger.debug(f"Reset PHD/PDX: {self.reset_var.get()}")
        logger.debug(f"BMS Path: {self.bms_path_entry.get()}")
        
        # 1. Save settings to saved_objectives_settings.json
        try:
            # Log the settings path for debugging
            settings_path = self._get_settings_path()
            logger.debug(f"Saving settings to: {settings_path}")
            
            success = save_json(JsonFiles.SAVED_OBJECTIVE_SETTINGS, settings_data)
            if success:
                logger.info(f"Successfully saved settings to {JsonFiles.SAVED_OBJECTIVE_SETTINGS}")
            else:
                logger.error(f"Failed to save settings to {JsonFiles.SAVED_OBJECTIVE_SETTINGS}")
        except Exception as e:
            logger.error(f"Error saving settings: {e}")
            traceback.print_exc()
        
        # 2. Save field values to objective_templates.json for the selected type
        try:
            # First load existing templates
            objective_templates = load_json(JsonFiles.OBJECTIVE_TEMPLATES, default={})
            
            # Create or update the template for the current type
            type_key_str = str(type_key)  # Ensure it's a string for JSON keys
            
            if type_key_str not in objective_templates:
                objective_templates[type_key_str] = {}
                
            # Update only the fields in the template (keep other metadata if any)
            # Use the string fields, not typed_fields to ensure values are saved as strings
            objective_templates[type_key_str].update(fields)
            
            # Save updated templates
            success = save_json(JsonFiles.OBJECTIVE_TEMPLATES, objective_templates)
            if success:
                logger.info(f"Successfully saved field values to {JsonFiles.OBJECTIVE_TEMPLATES}")
            else:
                logger.error(f"Failed to save field values to {JsonFiles.OBJECTIVE_TEMPLATES}")
        except Exception as e:
            logger.error(f"Error saving field values: {e}")
            traceback.print_exc()
        
        # Also store in parent window if it's the OperationPage
        if hasattr(self.parent, 'textbox_CT') and hasattr(self.parent, 'textbox_Obj'):
            logger.debug(f"Updating parent window entries")
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
                    logger.debug(f"Setting parent to BMS mode")
                    self.parent.segemented_button_Saving.set("BMS")
                    if hasattr(self.parent, 'switch_save_method'):
                        self.parent.switch_save_method("BMS")
                else:
                    # Ensure entries are disabled even if BMS mode is already active
                    logger.debug(f"BMS mode already active")
        # Do not update objective_cache.json or ct_templates.json when Save Settings is pressed
        # The following lines have been commented out to fix the bugs
        # print(f"  Saving user template for type {type_key}")
        # objective_cache.set_user_templates(typed_fields, type_key)
        # objective_cache.save_cache()
        # 
        # print(f"  Updating injector templates for type {type_key}")
        # self.injector.objective_templates[str(type_key)] = typed_fields
        # self.injector.save_templates()
        
        logger.info("OBJECTIVE SETTINGS SAVE COMPLETED")
        
        # Close window
        self.destroy()
    
    def _cancel_operation(self):
        """Cancel the operation and close the window without setting any result."""
        logger.info("BMS injection operation cancelled by user")
        # Explicitly set cancellation result
        self.result = {
            "status": "cancelled",
            "reason": "user_cancelled"
        }
        self.destroy()
    
    def destroy(self):
        """Override destroy to ensure proper cancellation handling."""
        # Prevent multiple destroy calls
        if hasattr(self, '_destroying') and self._destroying:
            return
        self._destroying = True
        
        try:
            # If no result was set (e.g., window closed via X button), treat as cancellation
            if not hasattr(self, 'result') or self.result is None:
                logger.info("BMS injection window closed without result - treating as cancellation")
                self.result = {
                    "status": "cancelled", 
                    "reason": "window_closed"
                }
        except Exception as e:
            logger.error(f"Error setting result during destroy: {e}")
        
        try:
            # Cancel any scheduled destroy operations
            if self._scheduled_destroy:
                self.after_cancel(self._scheduled_destroy)
                self._scheduled_destroy = None
            super().destroy()
        except Exception as e:
            logger.error(f"Error during window destruction: {e}")
    
    def _safe_destroy(self):
        """Safely schedule window destruction, avoiding multiple scheduled calls."""
        if hasattr(self, '_destroying') and self._destroying:
            return
            
        if self._scheduled_destroy:
            # Already scheduled, don't schedule again
            return
            
        self._scheduled_destroy = self.after(100, self.destroy)
    
    def _get_selected_type_key(self):
        """Get the key (numeric type) for the selected type."""
        try:
            # Check if window is being destroyed
            if hasattr(self, '_destroying') and self._destroying:
                return 1  # Return default
                
            selected = self.type_var.get()
            index = self.type_values.index(selected)
            key = self.type_keys[index]
            logger.debug(f"Getting selected type key: {selected} -> {key}")
            return key
        except (ValueError, IndexError, tk.TclError):
            default = self.type_keys[0] if hasattr(self, 'type_keys') and self.type_keys else 1
            logger.warning(f"Error getting type key, using default: {default}")
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
        # Check if backup_features_files setting is available in parent's shared_data
        backup_features = True  # Default to True for safety
        if hasattr(self.parent, 'shared_data') and 'backup_features_files' in self.parent.shared_data:
            backup_features_value = self.parent.shared_data['backup_features_files']
            backup_features = backup_features_value == '1'
            
        self.injector = BmsInjector(self.bms_path, backup_features=backup_features)
        
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
                
            logger.info(f"[_validate_ct] Evaluated CT {ct_num}: ct_exists={ct_exists}, is_objective={is_objective}, highest_ct={highest_ct}")
            # Update status based on validation rules
            if ct_exists and is_objective:
                self.ct_info_label.configure(
                    text="⚠ CT is an Objective",
                    text_color="orange",
                    fg_color="transparent"
                )
                logger.debug(f"[_validate_ct] CT {ct_num} exists and is an objective")
            elif ct_exists and not is_objective:
                self.ct_info_label.configure(
                    text="⚠ CT is not an Objective",
                    text_color="brown",
                    fg_color="transparent"
                )
                logger.debug(f"[_validate_ct] CT {ct_num} exists but is not an objective")
            elif ct_num == highest_ct + 1:
                self.ct_info_label.configure(
                    text="✓ Valid CT Number",
                    text_color="green",
                    fg_color="transparent"
                )
                logger.debug(f"[_validate_ct] CT {ct_num} accepted as next available (highest {highest_ct})")
            else:
                self.ct_info_label.configure(
                    text="❌ Invalid CT Number",
                    text_color="red",
                    fg_color="transparent"
                )
                logger.debug(f"[_validate_ct] CT {ct_num} rejected; highest_ct={highest_ct}")
                
        except ValueError:
            logger.warning("[_validate_ct] Non-integer CT entry")
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
                logger.warning("[_get_last_ct] Invalid installation; cannot compute highest CT")
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
                logger.info(f"[_get_last_ct] Highest CT found: {highest_ct}; suggesting {highest_ct + 1}")
                
                # Validate the new CT number
                self._validate_ct(None)
                
                # Update the status message
                self.ct_info_label.configure(
                    text=f"Found highest CT: {highest_ct}",
                    text_color="green",
                    fg_color="transparent"
                )
                
            except Exception as e:
                logger.error(f"[_get_last_ct] Error while finding highest CT: {e}")
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
                logger.warning(f"Cache lookup failed: {cache_err}")
            
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
                            logger.error(f"Error processing file {ocd_file}: {file_err}")
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
                logger.warning("[_get_last_obj] Invalid installation; cannot compute highest objective")
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
                    logger.warning(f"[_get_last_obj] Cache lookup failed: {cache_err}")
                
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
                logger.info(f"[_get_last_obj] Highest OBJ found: {highest_obj}; suggesting {highest_obj + 1}")
                
                # Validate the new objective number
                self._validate_obj(None)
                
                # Update status
                self.obj_info_label.configure(
                    text=f"Found highest Obj: {highest_obj}",
                    text_color="green",
                    fg_color="transparent"
                )
                
            except Exception as e:
                logger.error(f"[_get_last_obj] Error while finding highest objective: {e}")
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
                                        logger.error(f"Error setting type: {type_err}")
                                break
                    except Exception as ct_err:
                        logger.error(f"Error finding CT type: {ct_err}")
                
                if not type_found:
                    logger.warning("Type not found in dropdown, using default fields")
                
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
                logger.error(f"Error processing objective data: {e}")
                
        except Exception as e:
            self.obj_info_label.configure(
                text=f"Error: {str(e)}",
                text_color="red",
                fg_color="transparent"
            )
        
        # Check if entry is empty
        if not obj_entry_text:
            self.obj_info_label.configure(
                text="Objective Number is empty",
                text_color="red",
                fg_color="transparent"
            )
            response = messagebox.askyesno(
                "Objective Template Missing",
                "The objective template file is missing. Would you like to generate it?",
                icon=messagebox.WARNING
            )
            if response:
                self.analyze_ocd_files_and_create_objective_template()
            return
        
        # Load the template file
        templates = load_json(JsonFiles.OBJECTIVE_TEMPLATES, default={})
        if not templates:
            response = messagebox.askyesno(
                "Empty Objective Template",
                "The objective template file is empty. Would you like to regenerate it?",
                icon=messagebox.WARNING
            )
            if response:
                # Actually call the method to regenerate templates
                logger.info("Regenerating objective templates due to empty file")
                self.analyze_ocd_files_and_create_objective_template()
            return
        
        # Required fields to check
        required_fields = [
            "DataRate", "DeaggDistance", "Det_NoMove", "Det_Foot", "Det_Wheeled",
            "Det_Tracked", "Det_LowAir", "Det_Air", "Det_Naval", "Det_Rail",
            "Dam_None", "Dam_Penetration", "Dam_HighExplosive", "Dam_Heave", "Dam_Incendairy",
            "Dam_Proximity", "Dam_Kinetic", "Dam_Hydrostatic", "Dam_Chemical", "Dam_Nuclear",
            "Dam_Other", "ObjectiveIcon", "RadarFeature"
        ]
        
        validation_errors = []
        
        # Check that all required types 1-31 are present
        for type_idx in range(1, 32):
            type_key = str(type_idx)
            if type_key not in templates:
                validation_errors.append(f"Missing template for type {type_key}")
                continue
                
            # Check each field in this type's template
            for field in required_fields:
                # Check field exists
                if field not in templates[type_key]:
                    validation_errors.append(f"Type {type_key}: Missing field '{field}'")
                    continue
                    
        # If there are validation errors, prompt the user
        if validation_errors:
            error_count = min(5, len(validation_errors))  # Show only first 5 errors
            error_msg = "The objective template file has validation errors:\n\n"
            error_msg += "\n".join(validation_errors[:error_count])
            
            if len(validation_errors) > error_count:
                error_msg += f"\n\n...and {len(validation_errors) - error_count} more errors."
                
            error_msg += "\n\nWould you like to recalculate the template?"
            
            response = messagebox.askyesno(
                "Objective Template Validation Failed",
                error_msg,
                icon=messagebox.WARNING
            )
            
            if response:
                # Actually call the method to regenerate templates
                logger.info("Regenerating objective templates due to validation errors")
                self.analyze_ocd_files_and_create_objective_template()
    
    def validate_ct_templates(self):
        """
        Validate that the CT_template.json file exists and contains all required fields with valid values.
        If validation fails, prompt the user to recalculate or terminate.
        """
        from utils.json_path_handler import load_json, get_json_path, JsonFiles
        
        # Check if CT_template.json file exists
        ct_template_path = get_json_path(JsonFiles.CT_TEMPLATES)
        if not ct_template_path.exists():
            response = messagebox.askyesno(
                "CT Template Missing",
                "The CT template file is missing. Would you like to generate it?",
                icon=messagebox.WARNING
            )
            if response:
                result = self.analyze_ct_file_and_create_template()
                if result is None:
                    logger.error("Failed to create CT templates")
                    messagebox.showerror(
                        "Template Creation Failed",
                        "Failed to create CT templates. The BMS Injection window will be closed."
                    )
                    self.result = {"status": "cancelled", "reason": "ct_template_creation_failed"}
                    self._safe_destroy()
                    return False
                else:
                    logger.info("CT templates created successfully")
            else:
                self.destroy()
            return
        
        # Load the template file
        templates = load_json(JsonFiles.CT_TEMPLATES, default={})
        if not templates:
            response = messagebox.askyesno(
                "Empty CT Template",
                "The CT template file is empty. Would you like to regenerate it?",
                icon=messagebox.WARNING
            )
            if response:
                result = self.analyze_ct_file_and_create_template()
                if result is None:
                    logger.error("Failed to regenerate CT templates")
                    messagebox.showerror(
                        "Template Regeneration Failed",
                        "Failed to regenerate CT templates. The BMS Injection window will be closed."
                    )
                    self.result = {"status": "cancelled", "reason": "ct_template_regeneration_failed"}
                    self._safe_destroy()
                    return False
                else:
                    logger.info("CT templates regenerated successfully")
            else:
                # Show an info message before closing
                messagebox.showinfo(
                    "BMS Injection Terminated",
                    "CT template file is missing. BMS Injection window will be closed."
                )
                logger.warning("User chose not to create missing templates. Terminating BMS Injection Window.")
                
                # Create a result attribute to indicate intentional closure
                self.result = {"status": "cancelled", "reason": "missing_template"}
                
                # Execute this after all pending events to ensure proper closure
                self._safe_destroy()
            return
        
        # Required fields and their expected constant values if applicable
        required_fields = {
            "Id": None,
            "CollisionType": None,
            "CollisionRadius": None,
            "Domain": "3",  # Constant
            "Class": "4",   # Constant
            "SubType": None, 
            "Specific": None,
            "Owner": None,
            "Class_6": None,
            "Class_7": None,
            "UpdateRate": None,
            "UpdateTolerance": None,
            "FineUpdateRange": None,
            "FineUpdateForceRange": None,
            "FineUpdateMultiplier": None,
            "DamageSeed": None,
            "HitPoints": None,
            "MajorRev": None,
            "MinRev": None,
            "CreatePriority": None,
            "ManagementDomain": None,
            "Transferable": None,
            "Private": None,
            "Tangible": None,
            "Collidable": None,
            "Global": None,
            "Persistent": None,
            "GraphicsNormal": "0",  # Constant
            "GraphicsRepaired": "0",  # Constant
            "GraphicsDamaged": "0",  # Constant
            "GraphicsDestroyed": "0",  # Constant
            "GraphicsLeftDestroyed": "0",  # Constant
            "GraphicsRightDestroyed": "0",  # Constant
            "GraphicsBothDestroyed": "0",  # Constant
            "MoverDefinitionData": "0",  # Constant
            "EntityType": "3"  # Constant
        }
        
        validation_errors = []
        
        # Check that all required types 1-31 are present
        for type_idx in range(1, 32):
            type_key = str(type_idx)
            if type_key not in templates:
                validation_errors.append(f"Missing template for type {type_key}")
                continue
                
            # Check each field in this type's template
            for field, expected_val in required_fields.items():
                # Check field exists
                if field not in templates[type_key]:
                    validation_errors.append(f"Type {type_key}: Missing field '{field}'")
                    continue
                    
                # Get actual value
                actual_val = templates[type_key][field]
                
                # Check constant values match expected values
                if expected_val is not None and actual_val != expected_val:
                    validation_errors.append(
                        f"Type {type_key}: Field '{field}' has invalid value '{actual_val}', expected '{expected_val}'"
                    )
                    continue
                    
                # For non-constant fields, ensure they are numeric
                if expected_val is None:
                    try:
                        # Try to convert to float to check if numeric
                        float(actual_val)  # Just a validation test, don't need to store
                    except (ValueError, TypeError):
                        validation_errors.append(
                            f"Type {type_key}: Field '{field}' has non-numeric value '{actual_val}'"
                        )
        
        # If there are validation errors, prompt the user
        if validation_errors:
            error_count = min(5, len(validation_errors))  # Show only first 5 errors
            error_msg = "The CT template file has validation errors:\n\n"
            error_msg += "\n".join(validation_errors[:error_count])
            
            if len(validation_errors) > error_count:
                error_msg += f"\n\n...and {len(validation_errors) - error_count} more errors."
                
            error_msg += "\n\nWould you like to recalculate the template?"
            
            response = messagebox.askyesno(
                "CT Template Validation Failed",
                error_msg,
                icon=messagebox.WARNING
            )
            
            if response:
                self.analyze_ct_file_and_create_template()
            else:
                # Show an info message before closing
                messagebox.showinfo(
                    "BMS Injection Terminated",
                    "CT template file is missing. BMS Injection window will be closed."
                )
                logger.warning("User chose not to create missing templates. Terminating BMS Injection Window.")
                
                # Create a result attribute to indicate intentional closure
                self.result = {"status": "cancelled", "reason": "missing_template"}
                
                # Execute this after all pending events to ensure proper closure
                self._safe_destroy()
                
    def validate_objective_templates(self):
        """
        Validate that the objective_templates.json file exists and contains all required fields with valid values.
        If validation fails, prompt the user to recalculate or terminate.
        
        Returns:
            True if validation passed, False otherwise
        """
        from utils.json_path_handler import load_json, get_json_path, JsonFiles
        from tkinter import messagebox
        import os
        
        # Required fields for all objective templates
        required_fields = [
            "DataRate", "DeaggDistance", "Det_NoMove", "Det_Foot", "Det_Wheeled",
            "Det_Tracked", "Det_LowAir", "Det_Air", "Det_Naval", "Det_Rail",
            "Dam_None", "Dam_Penetration", "Dam_HighExplosive", "Dam_Heave", "Dam_Incendairy",
            "Dam_Proximity", "Dam_Kinetic", "Dam_Hydrostatic", "Dam_Chemical", "Dam_Nuclear",
            "Dam_Other", "ObjectiveIcon", "RadarFeature"
        ]

        # Check if objective_templates.json file exists
        obj_template_path = get_json_path(JsonFiles.OBJECTIVE_TEMPLATES)
        if not os.path.exists(obj_template_path):
            response = messagebox.askyesno(
                "Objective Template Missing",
                "The objective template file is missing. Would you like to regenerate it?",
                icon=messagebox.WARNING
            )
            
            if response:
                result = self.analyze_ocd_files_and_create_objective_template()
                if result is None:
                    logger.error("Failed to create objective templates")
                    messagebox.showerror(
                        "Template Creation Failed",
                        "Failed to create objective templates. The BMS Injection window will be closed."
                    )
                    # Create a result attribute to indicate failure
                    self.result = {"status": "cancelled", "reason": "template_creation_failed"}
                    self._safe_destroy()
                    return False
                else:
                    logger.info("Objective templates created successfully")
            else:
                # Show an info message before closing
                messagebox.showinfo(
                    "BMS Injection Terminated",
                    "Objective template file is missing. BMS Injection window will be closed."
                )
                logger.warning("User chose not to create missing templates. Terminating BMS Injection Window.")
                
                # Create a result attribute to indicate intentional closure
                self.result = {"status": "cancelled", "reason": "missing_template"}
                
                # Execute this after all pending events to ensure proper closure
                self._safe_destroy()
            return False
                
        # Load the template file
        templates = load_json(JsonFiles.OBJECTIVE_TEMPLATES, default={})
        if not templates:
            response = messagebox.askyesno(
                "Empty Objective Template",
                "The objective template file is empty or corrupt. Would you like to regenerate it?",
                icon=messagebox.WARNING
            )
            
            if response:
                logger.info("Regenerating objective templates due to empty file")
                result = self.analyze_ocd_files_and_create_objective_template()
                if result is None:
                    logger.error("Failed to regenerate objective templates")
                    messagebox.showerror(
                        "Template Regeneration Failed",
                        "Failed to regenerate objective templates. The BMS Injection window will be closed."
                    )
                    self.result = {"status": "cancelled", "reason": "template_regeneration_failed"}
                    self._safe_destroy()
                    return False
                else:
                    logger.info("Objective templates regenerated successfully")
            else:
                # Show an info message before closing
                messagebox.showinfo(
                    "BMS Injection Terminated",
                    "Objective template file is empty or corrupt. BMS Injection window will be closed."
                )
                logger.warning("User chose not to regenerate empty templates. Terminating BMS Injection Window.")
                
                # Create a result attribute to indicate intentional closure
                self.result = {"status": "cancelled", "reason": "empty_template"}
                
                # Execute this after all pending events to ensure proper closure
                self._safe_destroy()
            return False
                
        # Validate all objective types and fields
        validation_errors = []
        
        # Check each objective type (1-31)
        for obj_type in range(1, 32):
            type_key = str(obj_type)
            
            # Check if this type exists in the templates
            if type_key not in templates:
                validation_errors.append(f"Objective type {type_key} is missing")
                continue
            
            # Check each required field for this type
            template = templates[type_key]
            for field in required_fields:
                # Check if field exists
                if field not in template:
                    validation_errors.append(f"Field '{field}' is missing for objective type {type_key}")
                    continue
                
                # Check if field has a numeric value
                value = template[field]
                try:
                    # Try to convert to float to check if it's numeric
                    float(value)
                except (ValueError, TypeError):
                    validation_errors.append(f"Field '{field}' has non-numeric value '{value}' for objective type {type_key}")
        
        # If validation errors were found, show dialog
        if validation_errors:
            # Prepare error message - limit to first 10 errors to avoid message box overflow
            error_msg = "The objective templates have validation errors:\n"
            error_count = min(10, len(validation_errors))
            
            for i in range(error_count):
                error_msg += f"\n- {validation_errors[i]}"
                
            if len(validation_errors) > error_count:
                error_msg += f"\n\n...and {len(validation_errors) - error_count} more errors."
                
            error_msg += "\n\nWould you like to regenerate the objective templates?"
            
            response = messagebox.askyesno(
                "Objective Template Validation Failed",
                error_msg,
                icon=messagebox.WARNING
            )
            
            if response:
                logger.info("Regenerating objective templates due to validation errors")
                self.analyze_ocd_files_and_create_objective_template()
            else:
                # Show an info message before closing
                messagebox.showinfo(
                    "BMS Injection Terminated",
                    "Objective template validation failed. BMS Injection window will be closed."
                )
                logger.warning("User chose not to regenerate templates. Terminating BMS Injection Window.")
                
                # Create a result attribute to indicate intentional closure
                self.result = {"status": "cancelled", "reason": "template_validation_failed"}
                
                # Execute this after all pending events to ensure proper closure
                self._safe_destroy()
            return False
        
        return True  # Validation passed
                
    def analyze_ct_file_and_create_template(self):
        """
        Analyze the Falcon4_CT.xml file to find objectives and create templates with median values.
        This function will:
        1. Look for CT entries with Domain=3, Class=4, EntityType=3
        2. Group them by Type (1-31)
        3. Calculate median values for specified fields
        4. Add constant values for other fields
        5. Save the resulting dictionary to CT_template.json
        """
        if not self.installation_valid or not self.injector.ct_file.exists():
            logger.error(f"Cannot analyze CT file: Invalid installation or CT file not found")
            messagebox.showerror("File Not Found", "BMS installation is invalid or CT file not found")
            return
            
        # Define the task that will run in the background with processing window
        def ct_template_generation_task(processing_window):
            # Parse the CT file
            tree = ET.parse(self.injector.ct_file)
            root = tree.getroot()
            
            # Dictionary to store values by type
            type_values = {}
            
            # Fields that need median calculation
            median_fields = [
                "CollisionType", "CollisionRadius", "UpdateRate", "UpdateTolerance", 
                "FineUpdateRange", "FineUpdateForceRange", "FineUpdateMultiplier",
                "DamageSeed", "HitPoints", "MajorRev", "MinRev", 
                "CreatePriority", "ManagementDomain", "Transferable", "Private", 
                "Tangible", "Collidable", "Global", "Persistent", "Id"
            ]
            
            # Find all CT entries that are objectives
            logger.info(f"Analyzing CT file: {self.injector.ct_file}")
            for ct in root.findall("CT"):
                try:
                    # Check if this is an objective (Domain=3, Class=4, EntityType=3)
                    domain_elem = ct.find("Domain")
                    class_elem = ct.find("Class")
                    entity_type_elem = ct.find("EntityType")
                    type_elem = ct.find("Type")
                    
                    if (domain_elem is not None and domain_elem.text == "3" and
                        class_elem is not None and class_elem.text == "4" and
                        entity_type_elem is not None and entity_type_elem.text == "3" and
                        type_elem is not None and type_elem.text):
                        
                        # Get the type number (1-31)
                        obj_type = int(type_elem.text)
                        
                        if obj_type < 1 or obj_type > 31:
                            continue
                        
                        # Initialize type entry if not exists
                        if obj_type not in type_values:
                            type_values[obj_type] = {field: [] for field in median_fields}
                        
                        # Collect values for each field
                        for field in median_fields:
                            field_elem = ct.find(field)
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
                
                except Exception as e:
                    logger.error(f"Error processing CT entry: {e}")
            
            # Calculate median values and create the template
            ct_templates = {}
            
            # Process each objective type
            for obj_type in range(1, 32):
                # Create template with the exact field order requested
                template = {}
                
                # Calculate median values if we have data for this type
                if obj_type in type_values:
                    for field in median_fields:
                        values = type_values[obj_type][field]
                        if values:
                            # Check if all values are numeric
                            if all(isinstance(v, (int, float)) for v in values):
                                # Calculate median
                                sorted_values = sorted(values)
                                if len(sorted_values) % 2 == 0:
                                    # Even number of values, average middle two
                                    median = (sorted_values[len(sorted_values)//2 - 1] + sorted_values[len(sorted_values)//2]) / 2
                                else:
                                    # Odd number of values, take middle one
                                    median = sorted_values[len(sorted_values)//2]
                                
                                # Keep integers as integers
                                if all(isinstance(v, int) for v in values):
                                    median = int(median)
                                
                                template[field] = str(median)
                            else:
                                # For non-numeric values, use most common
                                value_counts = {}
                                for v in values:
                                    value_counts[v] = value_counts.get(v, 0) + 1
                                
                                most_common = max(value_counts.items(), key=lambda x: x[1])[0]
                                template[field] = str(most_common)
                        else:
                            # No values found, use 0
                            template[field] = "0"
                else:
                    # No data for this type, use 0 for all fields
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
                ct_templates[str(obj_type)] = ordered_template
            
            # Save templates to JSON file
            from utils.json_path_handler import save_json, JsonFiles
            save_json(JsonFiles.CT_TEMPLATES, ct_templates)
            logger.info(f"CT templates generated and saved for {len(ct_templates)} objective types")
            
            # Update the injector's templates
            self.injector.ct_templates = ct_templates

            # Note: CT templates don't need to be cached in objective_cache as they're not used by the GUI
            
            return ct_templates
            
        # Run the task with a processing window
        try:
            logger.info("[BMS WINDOW] Starting CT template generation with processing window")
            result = run_template_generation(
                self,
                ct_template_generation_task,
                ProcessType.CT_TEMPLATE_GENERATION
            )
            logger.info("[BMS WINDOW] CT template generation completed")
            
            # Show success message
            if result:
                logger.info(f"CT templates generated and saved for {len(result)} objective types")
            return result
        except Exception as e:
            logger.error(f"Error analyzing CT file: {e}")
            traceback.print_exc()
            messagebox.showerror("Analysis Error", f"An error occurred while analyzing CT file: {str(e)}")
            return None
            
    def analyze_ocd_files_and_create_objective_template(self):
        """
        Analyze OCD files in ObjectiveRelatedData folder to create objective templates with median values.
        This function will:
        1. Scan ObjectiveRelatedData folders for OCD files
        2. For each OCD file, find the CT type through the CtIdx
        3. Calculate median values for specified fields grouped by type (1-31)
        4. Add constant values for other fields
        5. Save the resulting dictionary to objective_templates.json
        """
        if not self.installation_valid:
            logger.error("Cannot analyze OCD files: Invalid BMS installation")
            messagebox.showerror("Invalid Installation", "Cannot analyze OCD files: BMS installation is invalid")
            return
            
        if not self.injector.ct_file.exists():
            logger.error(f"Cannot analyze OCD files: CT file not found at {self.injector.ct_file}")
            messagebox.showerror("File Not Found", f"Cannot find CT file at: {self.injector.ct_file}")
            return
            
        # Find the ObjectiveRelatedData directory - this is the standard location
        # Path is always: <Falcon4_CT.xml path>/ObjectiveRelatedData/
        obj_related_data_dir = self.injector.ct_file.parent / "ObjectiveRelatedData"
        
        if not obj_related_data_dir.exists() or not obj_related_data_dir.is_dir():
            logger.error(f"Cannot find ObjectiveRelatedData directory at: {obj_related_data_dir}")
            messagebox.showerror("Directory Not Found", f"Cannot find ObjectiveRelatedData directory at: {obj_related_data_dir}")
            return
        
        logger.info(f"Found ObjectiveRelatedData directory at: {obj_related_data_dir}")
        
        # Define the task that will run in the background with processing window
        def objective_template_generation_task(processing_window):
            # Parse the CT file with error handling
            try:
                ct_tree = ET.parse(self.injector.ct_file)
                ct_root = ct_tree.getroot()
            except ET.ParseError as xml_error:
                error_msg = f"XML parse error in CT file: {xml_error}"
                logger.error(error_msg)
                raise Exception(f"Could not parse the CT file: {error_msg}")
                
            # Dictionary to map CT indexes to their types
            ct_idx_to_type = {}
            
            # First pass: build a mapping of CT indexes to their types
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
                    logger.error(f"Error processing CT entry: {e}")
            
            # Dictionary to store values by objective type
            type_values = {}
            
            # Fields to calculate median for
            median_fields = [
                "DataRate", "DeaggDistance", "Det_NoMove", "Det_Foot", "Det_Wheeled",
                "Det_Tracked", "Det_LowAir", "Det_Air", "Det_Naval", "Det_Rail",
                "Dam_None", "Dam_Penetration", "Dam_HighExplosive", "Dam_Heave", "Dam_Incendairy",
                "Dam_Proximity", "Dam_Kinetic", "Dam_Hydrostatic", "Dam_Chemical", "Dam_Nuclear",
                "Dam_Other", "ObjectiveIcon"
            ]
            
            # Initialize all types with empty field lists
            for obj_type in range(1, 32):
                type_values[obj_type] = {field: [] for field in median_fields}
            
            # Now scan all OCD directories and files
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
                    logger.error(f"Error processing OCD file {ocd_file}: {e}")
            
            if ocd_count == 0:
                logger.warning("No OCD files found to analyze")
                messagebox.showwarning("No Data", "No OCD files found to analyze. Cannot create objective templates.")
                return
            
            # Calculate median values and create the templates
            objective_templates = {}
            
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
                            logger.info(f"  Type {obj_type} {field}: calculated median value {median} from {len(values)} values")
                        else:
                            # For non-numeric values, use the most common value
                            value_counts = {}
                            for v in values:
                                if v is not None:
                                    value_counts[v] = value_counts.get(v, 0) + 1
                                    
                            if value_counts:
                                most_common = max(value_counts.items(), key=lambda x: x[1])[0]
                                template[field] = str(most_common)
                                logger.info(f"  Type {obj_type} {field}: using most common value {most_common}")
                            else:
                                # Fallback to default - use 0
                                template[field] = "0"
                                logger.info(f"  Type {obj_type} {field}: no valid values, using 0")
                    else:
                        # No values found for this field, use 0
                        template[field] = "0"
                        logger.info(f"  Type {obj_type} {field}: no OCD values found, using 0")
                
                # Add constant values
                template["RadarFeature"] = "0"  # Constant value per requirements
                
                # Add to templates dictionary
                objective_templates[str(obj_type)] = template
            
            # Save templates to JSON file
            try:
                from utils.json_path_handler import save_json, JsonFiles
                save_json(JsonFiles.OBJECTIVE_TEMPLATES, objective_templates)
                logger.info(f"Objective templates generated and saved for {len(objective_templates)} objective types")
                
                # Update the injector's templates if available
                if hasattr(self.injector, 'objective_templates'):
                    self.injector.objective_templates = objective_templates

                # Update the objective cache with the new templates
                from components.objective_cache import cache as objective_cache
                objective_cache.set_objective_templates(objective_templates)
                objective_cache.save_cache()
            except Exception as save_error:
                error_msg = f"Error saving objective templates: {save_error}"
                logger.error(error_msg)
                raise Exception(f"Could not save objective templates: {error_msg}")
                
            # Return the generated templates for further processing
            return objective_templates
        
        # Run the task with a processing window
        try:
            logger.info("[BMS WINDOW] Starting OBJECTIVE template generation with processing window")
            result = run_template_generation(
                self,
                objective_template_generation_task,
                ProcessType.OBJECTIVE_TEMPLATE_GENERATION
            )
            logger.info("[BMS WINDOW] OBJECTIVE template generation completed")
            
            # Show success message
            if result:
                logger.info(f"Objective templates generated and saved for {len(result)} objective types")
                
            return result
            
        except Exception as e:
            error_msg = f"Error analyzing OCD files: {e}"
            logger.error(error_msg)
            traceback.print_exc()
            messagebox.showerror("Analysis Error", "An error occurred while analyzing OCD files. Check the console for more details.")
            return None
    
    def update_bms_path(self, new_path):
        """Update the BMS path display with a new path."""
        if new_path and new_path != self.bms_path:
            self.bms_path = new_path
            
            # Update the display
            self.bms_path_entry.configure(state="normal")
            self.bms_path_entry.delete(0, tk.END)
            self.bms_path_entry.insert(0, str(self.bms_path))
            self.bms_path_entry.configure(state="readonly")
            
            # Check if backup_bms_files setting is available in parent's shared_data
            backup = True  # Default to True for safety
            if hasattr(self.parent, 'shared_data') and 'backup_bms_files' in self.parent.shared_data:
                backup_value = self.parent.shared_data['backup_bms_files']  # Read string value directly
                backup = backup_value == '1'
                logger.info(f"Using backup setting from configuration: {backup}")
                
            # Check if backup_features_files setting is available in parent's shared_data
            backup_features = True  # Default to True for safety
            if hasattr(self.parent, 'shared_data') and 'backup_features_files' in self.parent.shared_data:
                backup_features_value = self.parent.shared_data['backup_features_files']
                backup_features = backup_features_value == '1'
                
            # Update the injector with appropriate backup setting
            self.injector = BmsInjector(self.bms_path, backup_features=backup_features, backup=backup)
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
    
    root.destroy()
