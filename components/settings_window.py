import tkinter as tk
import customtkinter as Ctk
import logging
import os
import sys
import threading
import time
from pathlib import Path
from tkinter import ttk, messagebox
from typing import Dict, Any, Optional, List, Tuple

# Add the project root directory to the path for proper imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Now we can import the modules
from utils.json_path_handler import load_json, save_json, JsonFiles
from components import objective_cache
from components.ct_data_handler import CTDataHandler

# Version information for documentation
__version__ = '1.5.0'
__author__ = 'BMS Building Generator Team'
__doc__ = '''
Enhanced Settings Window for the Building Generator Application

This module provides a modern, user-friendly settings interface with tabbed navigation
and comprehensive configuration options for BMS object properties.

'''


# Ensure we can import from parent directory
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.json_path_handler import load_json, save_json, JsonFiles, get_json_path
from components.objective_cache import cache as objective_cache

class SettingsWindow(tk.Toplevel):
    """
    Enhanced Settings Window for the Building Generator application.
    
    Features:
    - Tabbed interface for organized settings
    - General settings with BMS and Backup KTO path configuration
    - BMS Injection settings with Objective Type configuration
    - Class Table Data settings
    """
    
    def __init__(self, parent, bms_path=None, kto_backup_path=None, database_path=None, 
                 geojson_path=None, editor_extraction_path=None):
        """Initialize the Settings Window.
        
        Args:
            parent: Parent window (MainPage)
            bms_path: Path to BMS CT file
            kto_backup_path: Path for KTO backup files
            database_path: Path to BMS database
            geojson_path: Path to GeoJSON files
            editor_extraction_path: Path for editor extraction output
        """
        super().__init__(parent)
        self._creation_time = time.perf_counter() # Record creation time
        
        # Store reference to parent
        self.parent = parent
        
        # Set window properties
        self.title("Settings")
        self.geometry("550x750")
        self.minsize(550, 750)
        self.resizable(True, True)
        self.configure(bg="#FFFFFF")
        
        # Store paths
        self.bms_path = bms_path
        self.kto_backup_path = kto_backup_path
        self.database_path = database_path
        self.geojson_path = geojson_path
        self.editor_extraction_path = editor_extraction_path
        
        # Add debugging information about the BMS path
        logging.debug(f"SettingsWindow initialized with BMS path: '{self.bms_path}'")
        logging.debug(f"BMS path type: {type(self.bms_path)}")
        if self.bms_path:
            logging.debug(f"BMS path exists: {os.path.exists(self.bms_path)}")
            logging.debug(f"BMS path is file: {os.path.isfile(self.bms_path)}")
            logging.debug(f"BMS path is dir: {os.path.isdir(self.bms_path)}")
            if os.path.isfile(self.bms_path):
                logging.debug(f"BMS path directory: '{os.path.dirname(self.bms_path)}'")
        else:
            logging.warning("BMS path is None or empty during initialization")
        
        # Initialize logger reference (use parent's logging system)
        self.logger = logging.getLogger(__name__)
        
        # Create the UI
        self._init_ui()
        
        # Center window on screen
        self.update_idletasks()
        width = self.winfo_width()
        height = self.winfo_height()
        x = (self.winfo_screenwidth() // 2) - (width // 2)
        y = (self.winfo_screenheight() // 2) - (height // 2)
        self.geometry(f"{width}x{height}+{x}+{y}")
        
        # Set up protocol handler for when the window is closed
        self.protocol("WM_DELETE_WINDOW", self._on_close)
    


    def _init_ui(self):
        """Initialize the user interface components."""
        # Configure the window background
        self.configure(bg="#F0F0F5")
        
        # Create main frame with modern styling
        self.main_frame = Ctk.CTkFrame(self, fg_color="#E7E7EF")
        self.main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Header section with title
        self.header_frame = Ctk.CTkFrame(self.main_frame, fg_color="#D5E3F0")
        self.header_frame.pack(fill=tk.X, padx=5, pady=5)
        
        Ctk.CTkLabel(
            self.header_frame,
            text="Settings",
            font=("Arial", 16, "bold"),
            text_color="#000000",
            fg_color="transparent"
        ).pack(pady=5)
        
        # Configure notebook style for a more modern look
        style = ttk.Style()
        style.configure("TNotebook", background="#E7E7EF")
        style.configure("TNotebook.Tab", background="#A1B9D0", foreground="#000000", padding=[12, 6])
        style.map("TNotebook.Tab", background=[("selected", "#7A92A9")], foreground=[("selected", "#000000")])

        # Create notebook (tabbed interface) with modern styling
        self.notebook = ttk.Notebook(self.main_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)
        
        # Create tab frames
        self.general_tab = self._create_scrollable_frame(self.notebook, tab_name="general_tab")
        self.bms_injection_tab = self._create_scrollable_frame(self.notebook, tab_name="bms_injection_tab")
        self.cache_tab = self._create_scrollable_frame(self.notebook, tab_name="cache_tab")
        
        # Add tabs to notebook
        self.notebook.add(self.general_tab, text="General")
        self.notebook.add(self.bms_injection_tab, text="BMS Injection")
        self.notebook.add(self.cache_tab, text="Cache")
        
        # Initialize content for each tab
        self._init_general_tab()
        self._init_bms_injection_tab()
        self._init_cache_tab()
        
        # Add bottom buttons frame with modern styling
        self.buttons_frame = Ctk.CTkFrame(self.main_frame, fg_color="#D5E3F0")
        self.buttons_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Add close button with modern style
        self.close_button = Ctk.CTkButton(
            self.buttons_frame,
            text="Close",
            command=self._on_close, # Changed from self.destroy
            fg_color="#A1B9D0",
            hover_color="#7A92A9",
            text_color="#000000",
            height=35,
            width=167,
            corner_radius=8,
            border_width=1,
            border_color="#8AA2BC",
            font=("Arial", 12, "bold")
        )
        self.close_button.pack(side=tk.RIGHT, padx=8, pady=8)
    
    def _create_scrollable_frame(self, parent, tab_name=None):
        """Create a frame with scrollbars."""
        # Create a canvas with scrollbar using modern colors
        frame = Ctk.CTkFrame(parent, fg_color="#E8E8F0")
        
        # Create canvas and scrollbar with modern styling
        canvas = tk.Canvas(frame, bg="#E8E8F0", highlightthickness=0)
        scrollbar = Ctk.CTkScrollbar(frame, orientation="vertical", command=canvas.yview, 
                                   button_color="#A1B9D0", button_hover_color="#7A92A9")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # Pack scrollbar and canvas
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Create inner frame for content
        inner_frame = Ctk.CTkFrame(canvas, fg_color="#E8E8F0")
        
        # Create window in canvas for the inner frame
        window_id = canvas.create_window((0, 0), window=inner_frame, anchor="nw")
        
        # Configure inner frame and canvas
        def _configure_inner_frame(event):
            canvas.configure(scrollregion=canvas.bbox("all"))
            # Make inner frame width match canvas width
            canvas.itemconfig(window_id, width=canvas.winfo_width())
        
        inner_frame.bind("<Configure>", _configure_inner_frame)
        canvas.bind("<Configure>", lambda e: canvas.itemconfig(window_id, width=e.width))
        
        # Enable mousewheel scrolling - use an instance variable to track the binding
        def _on_mousewheel(event):
            # Only scroll if the canvas exists and is visible
            if canvas.winfo_exists():
                canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
            else:
                # If canvas no longer exists, unbind the mousewheel
                self.unbind_all("<MouseWheel>")
                
        # Store a reference to the function to unbind later
        if not hasattr(self, '_mouse_bindings'):
            self._mouse_bindings = {}
        
        # Generate a unique identifier if tab_name is not provided
        if tab_name is None:
            tab_name = f"frame_{id(frame)}"
            
        # Remove any previous binding
        if tab_name in self._mouse_bindings:
            self.unbind_all("<MouseWheel>")
            
        # Add new binding and store it
        self._mouse_bindings[tab_name] = _on_mousewheel
        canvas.bind("<Enter>", lambda e: self.bind_all("<MouseWheel>", _on_mousewheel))
        canvas.bind("<Leave>", lambda e: self.unbind_all("<MouseWheel>"))
        
        return frame
    
    def _init_general_tab(self):
        """Initialize the General tab content."""
        # Get the scrollable frame content area
        content_frame = self._get_scrollable_content(self.general_tab)
        
        # Create container for configuration presets section with modern styling
        presets_frame = Ctk.CTkFrame(content_frame, fg_color="#E0E8F0", border_width=1, border_color="#B3C8DD")
        presets_frame.pack(fill=tk.X, padx=10, pady=10)
        
        # Section title with modern styling
        presets_section_label = Ctk.CTkLabel(
            presets_frame,
            text="Configuration Presets",
            font=("Arial", 16, "bold"),
            text_color="#000033",
            fg_color="transparent"
        )
        presets_section_label.pack(anchor="w", padx=12, pady=(12, 6))
        
        # Buttons frame with modern styling
        buttons_frame = Ctk.CTkFrame(presets_frame, fg_color="#E0E8F0")
        buttons_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # Save Preset Button with modern styling
        self.save_preset_button = Ctk.CTkButton(
            buttons_frame,
            text="Save Preset",
            command=self._save_preset,
            fg_color="#A1B9D0",
            hover_color="#7A92A9",
            text_color="#000000",
            height=35,
            width=167,
            corner_radius=8,
            border_width=1,
            border_color="#8AA2BC",
            font=("Arial", 12)
        )
        self.save_preset_button.pack(side=tk.LEFT, padx=6, pady=8)
        
        # Load Preset Button with modern styling
        self.load_preset_button = Ctk.CTkButton(
            buttons_frame,
            text="Load Preset",
            command=self._load_preset,
            fg_color="#A1B9D0",
            hover_color="#7A92A9",
            text_color="#000000",
            height=35,
            width=167,
            corner_radius=8,
            border_width=1,
            border_color="#8AA2BC",
            font=("Arial", 12)
        )
        self.load_preset_button.pack(side=tk.LEFT, padx=6, pady=8)
        
        # Create container for checkbox options section with modern styling
        checkbox_frame = Ctk.CTkFrame(content_frame, fg_color="#E0E8F0", border_width=1, border_color="#B3C8DD")
        checkbox_frame.pack(fill=tk.X, padx=10, pady=10)
        
        # Section title with modern styling
        checkbox_section_label = Ctk.CTkLabel(
            checkbox_frame,
            text="Options",
            font=("Arial", 16, "bold"),
            text_color="#000033",
            fg_color="transparent"
        )
        checkbox_section_label.pack(anchor="w", padx=12, pady=(12, 6))
        
        # Checkbox container for row 1 with modern styling
        checkbox_row1 = Ctk.CTkFrame(checkbox_frame, fg_color="#E0E8F0")
        checkbox_row1.pack(fill=tk.X, padx=10, pady=5)
        
        # Auto-Start Checkbox with modern styling
        self.auto_start_var = tk.BooleanVar(value=False)
        self.auto_start_checkbox = Ctk.CTkCheckBox(
            checkbox_row1,
            text="Auto-Start",
            variable=self.auto_start_var,
            onvalue=True,
            offvalue=False,
            command=self._toggle_auto_start,
            checkbox_height=20,
            checkbox_width=20,
            width=120,
            text_color="#2E2E3A",
            font=("Arial", 12),
            hover_color="#7A92A9",
            fg_color="#8DBBE7"
        )
        self.auto_start_checkbox.pack(side=tk.LEFT, padx=8, pady=8)
        
        # Spacer to balance the layout
        spacer = Ctk.CTkFrame(
            checkbox_row1,
            width=120,
            height=20,
            fg_color="transparent"
        )
        spacer.pack(side=tk.LEFT, padx=8, pady=8)
        
        # Checkbox container for row 2 with modern styling
        checkbox_row2 = Ctk.CTkFrame(checkbox_frame, fg_color="#E0E8F0")
        checkbox_row2.pack(fill=tk.X, padx=10, pady=5)
        
        # Backup BMS files checkbox
        backup_bms_default = True  # Default to True (enable backup)
        if hasattr(self.parent, 'shared_data') and 'backup_bms_files' in self.parent.shared_data:
            val = self.parent.shared_data['backup_bms_files']
            if isinstance(val, tk.StringVar):
                backup_bms_default = (val.get() == '1')
            elif isinstance(val, str):
                backup_bms_default = (val == '1')
            logging.info(f"Loaded backup BMS setting: {backup_bms_default} from shared_data type: {type(val).__name__}")
        else:
            logging.info(f"No 'backup_bms_files' in shared_data, using default: {backup_bms_default}")

        self.backup_bms_var = tk.BooleanVar(value=backup_bms_default)

        # Ensure shared_data has a tk.StringVar for 'backup_bms_files' and it's correctly set
        if hasattr(self.parent, 'shared_data'):
            current_bms_shared_value_str = "1" if self.backup_bms_var.get() else "0"
            if not isinstance(self.parent.shared_data.get('backup_bms_files'), tk.StringVar) or \
            self.parent.shared_data['backup_bms_files'].get() != current_bms_shared_value_str:
                self.parent.shared_data['backup_bms_files'] = tk.StringVar(value=current_bms_shared_value_str)
                logging.info(f"Initialized/Updated 'backup_bms_files' in shared_data as StringVar with value: {current_bms_shared_value_str}")
        
        self.backup_bms_checkbox = Ctk.CTkCheckBox(
            checkbox_row2, # This parent frame should be defined earlier in the method
            text="Backup BMS files before modification",
            variable=self.backup_bms_var,
            onvalue=True,
            offvalue=False,
            command=self._toggle_backup_bms,
            checkbox_height=20,
            checkbox_width=20,
            width=260,
            text_color="#2E2E3A",
            font=("Arial", 12),
            hover_color="#7A92A9",
            fg_color="#8DBBE7"
        )
        self.backup_bms_checkbox.pack(side=tk.LEFT, padx=8, pady=8)

        # Backup generated features checkbox
        backup_features_default = False  # Default to False (disable backup)
        if hasattr(self.parent, 'shared_data') and 'backup_features_files' in self.parent.shared_data:
            val = self.parent.shared_data['backup_features_files']
            if isinstance(val, tk.StringVar):
                backup_features_default = (val.get() == '1')
            elif isinstance(val, str):
                backup_features_default = (val == '1')
            logging.info(f"Loaded backup features setting: {backup_features_default} from shared_data type: {type(val).__name__}")
        else:
            logging.info(f"No 'backup_features_files' in shared_data, using default: {backup_features_default}")

        self.backup_features_var = tk.BooleanVar(value=backup_features_default)

        # Ensure shared_data has a tk.StringVar for 'backup_features_files' and it's correctly set
        if hasattr(self.parent, 'shared_data'):
            current_features_shared_value_str = "1" if self.backup_features_var.get() else "0"
            if not isinstance(self.parent.shared_data.get('backup_features_files'), tk.StringVar) or \
               self.parent.shared_data['backup_features_files'].get() != current_features_shared_value_str:
                self.parent.shared_data['backup_features_files'] = tk.StringVar(value=current_features_shared_value_str)
                logging.info(f"Initialized/Updated 'backup_features_files' in shared_data as StringVar with value: {current_features_shared_value_str}")
        
        self.backup_features_checkbox = Ctk.CTkCheckBox(
            checkbox_row2,
            text="Backup generated features",
            variable=self.backup_features_var,
            onvalue=True,
            offvalue=False,
            command=self._toggle_backup_features,
            checkbox_height=20,
            checkbox_width=20,
            width=280,
            text_color="#2E2E3A",
            font=("Arial", 12),
            hover_color="#7A92A9",
            fg_color="#8DBBE7"
        )
        self.backup_features_checkbox.pack(side=tk.LEFT, padx=8, pady=8)
        
        # Create container for external tools section with modern styling
        external_tools_frame = Ctk.CTkFrame(content_frame, fg_color="#E0E8F0", border_width=1, border_color="#B3C8DD")
        external_tools_frame.pack(fill=tk.X, padx=10, pady=10)
        
        # Section title with modern styling
        external_tools_label = Ctk.CTkLabel(
            external_tools_frame,
            text="External Tools",
            font=("Arial", 16, "bold"),
            text_color="#000033",
            fg_color="transparent"
        )
        external_tools_label.pack(anchor="w", padx=12, pady=(12, 6))
        
        # Open Console Window Button with modern styling
        console_button_frame = Ctk.CTkFrame(external_tools_frame, fg_color="#E0E8F0")
        console_button_frame.pack(fill=tk.X, padx=10, pady=5)
        
        self.console_window_button = Ctk.CTkButton(
            console_button_frame,
            text="Open Console Window",
            command=self._open_console_window,
            fg_color="#A1B9D0",
            hover_color="#7A92A9",
            text_color="#000000",
            height=35,
            width=354,
            corner_radius=8,
            border_width=1,
            border_color="#8AA2BC",
            font=("Arial", 12)
        )
        self.console_window_button.pack(fill=tk.X, padx=8, pady=8)
        
        # Create container for paths section with modern styling
        paths_frame = Ctk.CTkFrame(content_frame, fg_color="#E0E8F0", border_width=1, border_color="#B3C8DD")
        paths_frame.pack(fill=tk.X, padx=10, pady=10)
        
        # Section title with modern styling
        paths_section_label = Ctk.CTkLabel(
            paths_frame,
            text="Paths Configuration",
            font=("Arial", 16, "bold"),
            text_color="#000033",
            fg_color="transparent"
        )
        paths_section_label.pack(anchor="w", padx=12, pady=(12, 6))
        
        # BMS Path Configuration with modern styling
        bms_path_frame = Ctk.CTkFrame(paths_frame, fg_color="#E0E8F0")
        bms_path_frame.pack(fill=tk.X, padx=10, pady=5)
        
        bms_path_label = Ctk.CTkLabel(
            bms_path_frame,
            text="BMS Path:",
            width=120,
            anchor="w",
            text_color="#2E2E3A",
            font=("Arial", 12)
        )
        bms_path_label.pack(side=tk.LEFT, padx=(8, 0))
        
        self.bms_path_var = tk.StringVar(value=self.bms_path if self.bms_path else "No BMS path selected")
        self.bms_path_entry = Ctk.CTkEntry(
            bms_path_frame,
            textvariable=self.bms_path_var,
            state="readonly",
            width=400,
            fg_color="#FFFFFF",
            text_color="#000000",
            border_width=1,
            border_color="#B3C8DD",
            font=("Arial", 11)
        )
        self.bms_path_entry.pack(side=tk.LEFT, padx=8, pady=8, fill=tk.X, expand=True)
        
        # Backup KTO Path Configuration with modern styling
        backup_path_frame = Ctk.CTkFrame(paths_frame, fg_color="#E0E8F0")
        backup_path_frame.pack(fill=tk.X, padx=10, pady=5)
        
        backup_path_label = Ctk.CTkLabel(
            backup_path_frame,
            text="Backup KTO Path:",
            width=120,
            anchor="w",
            text_color="#2E2E3A",
            font=("Arial", 12)
        )
        backup_path_label.pack(side=tk.LEFT, padx=(8, 0))
        
        self.backup_path_var = tk.StringVar(value=self.kto_backup_path if self.kto_backup_path else "No backup path selected")
        self.backup_path_entry = Ctk.CTkEntry(
            backup_path_frame,
            textvariable=self.backup_path_var,
            state="readonly",
            width=400,
            fg_color="#FFFFFF",
            text_color="#000000",
            border_width=1,
            border_color="#B3C8DD",
            font=("Arial", 11)
        )
        self.backup_path_entry.pack(side=tk.LEFT, padx=8, pady=8, fill=tk.X, expand=True)
        
        # Database Path Configuration with modern styling
        db_path_frame = Ctk.CTkFrame(paths_frame, fg_color="#E0E8F0")
        db_path_frame.pack(fill=tk.X, padx=10, pady=5)
        
        db_path_label = Ctk.CTkLabel(
            db_path_frame,
            text="Database Path:",
            width=120,
            anchor="w",
            text_color="#2E2E3A",
            font=("Arial", 12)
        )
        db_path_label.pack(side=tk.LEFT, padx=(8, 0))
        
        self.db_path_var = tk.StringVar(value=self.database_path if self.database_path else "No database path selected")
        self.db_path_entry = Ctk.CTkEntry(
            db_path_frame,
            textvariable=self.db_path_var,
            state="readonly",
            width=400,
            fg_color="#FFFFFF",
            text_color="#000000",
            border_width=1,
            border_color="#B3C8DD",
            font=("Arial", 11)
        )
        self.db_path_entry.pack(side=tk.LEFT, padx=8, pady=8, fill=tk.X, expand=True)
        
        # GeoJSON Path Configuration with modern styling
        geojson_path_frame = Ctk.CTkFrame(paths_frame, fg_color="#E0E8F0")
        geojson_path_frame.pack(fill=tk.X, padx=10, pady=5)
        
        geojson_path_label = Ctk.CTkLabel(
            geojson_path_frame,
            text="GeoJSON Path:",
            width=120,
            anchor="w",
            text_color="#2E2E3A",
            font=("Arial", 12)
        )
        geojson_path_label.pack(side=tk.LEFT, padx=(8, 0))
        
        self.geojson_path_var = tk.StringVar(value=self.geojson_path if self.geojson_path else "No GeoJSON path selected")
        self.geojson_path_entry = Ctk.CTkEntry(
            geojson_path_frame,
            textvariable=self.geojson_path_var,
            state="readonly",
            width=400,
            fg_color="#FFFFFF",
            text_color="#000000",
            border_width=1,
            border_color="#B3C8DD",
            font=("Arial", 11)
        )
        self.geojson_path_entry.pack(side=tk.LEFT, padx=8, pady=8, fill=tk.X, expand=True)
        
        # Editor Extraction Path Configuration with modern styling
        editor_path_frame = Ctk.CTkFrame(paths_frame, fg_color="#E0E8F0")
        editor_path_frame.pack(fill=tk.X, padx=10, pady=5)
        
        editor_path_label = Ctk.CTkLabel(
            editor_path_frame,
            text="Editor Output:",
            width=120,
            anchor="w",
            text_color="#2E2E3A",
            font=("Arial", 12)
        )
        editor_path_label.pack(side=tk.LEFT, padx=(8, 0))
        
        self.editor_path_var = tk.StringVar(value=self.editor_extraction_path if self.editor_extraction_path else "No editor path selected")
        self.editor_path_entry = Ctk.CTkEntry(
            editor_path_frame,
            textvariable=self.editor_path_var,
            state="readonly",
            width=400,
            fg_color="#FFFFFF",
            text_color="#000000",
            border_width=1,
            border_color="#B3C8DD",
            font=("Arial", 11)
        )
        self.editor_path_entry.pack(side=tk.LEFT, padx=8, pady=8, fill=tk.X, expand=True)
        
        # Create container for logging section with modern styling
        logging_frame = Ctk.CTkFrame(content_frame, fg_color="#E0E8F0", border_width=1, border_color="#B3C8DD")
        logging_frame.pack(fill=tk.X, padx=10, pady=10)
        
        # Section title with modern styling
        logging_section_label = Ctk.CTkLabel(
            logging_frame,
            text="Logging Configuration",
            font=("Arial", 16, "bold"),
            text_color="#000033",
            fg_color="transparent"
        )
        logging_section_label.pack(anchor="w", padx=12, pady=(12, 6))
        
        # Logging Type with modern styling
        log_type_frame = Ctk.CTkFrame(logging_frame, fg_color="#E0E8F0")
        log_type_frame.pack(fill=tk.X, padx=10, pady=5)
        
        log_type_label = Ctk.CTkLabel(
            log_type_frame,
            text="Logging Type:",
            width=120,
            anchor="w",
            text_color="#2E2E3A",
            font=("Arial", 12)
        )
        log_type_label.pack(side=tk.LEFT, padx=(8, 0))
        
        self.log_type_var = tk.StringVar()
        # Initialize from shared_data, defaulting to "None" if not found or invalid (user specified default)
        initial_log_method = self.parent.shared_data.get("logging_method").get() if self.parent.shared_data.get("logging_method") else "None"
        # Ensure the loaded value is one of the valid options for the dropdown
        valid_log_types = ["None", "Console Only", "File Only", "Console and File"]
        if initial_log_method not in valid_log_types: # Map from simple config value if needed
            if initial_log_method == "Console": initial_log_method = "Console Only"
            elif initial_log_method == "File": initial_log_method = "File Only"
            elif initial_log_method == "Both": initial_log_method = "Console and File"
            else: initial_log_method = "None" # Fallback to disabled (user specified default)
        self.log_type_var.set(initial_log_method if initial_log_method in valid_log_types else "None")
        self.log_type_dropdown = Ctk.CTkComboBox(
            log_type_frame,
            values=["None", "Console Only", "File Only", "Console and File"],
            variable=self.log_type_var,
            state="readonly",
            width=170,
            fg_color="#FFFFFF",
            text_color="#000000",
            button_color="#A1B9D0",
            button_hover_color="#7A92A9",
            border_width=1,
            border_color="#B3C8DD",
            dropdown_fg_color="#FFFFFF",
            font=("Arial", 11)
        )
        self.log_type_dropdown.pack(side=tk.LEFT, padx=8, pady=8)
        
        # Logging Level with modern styling
        log_level_frame = Ctk.CTkFrame(logging_frame, fg_color="#E0E8F0")
        log_level_frame.pack(fill=tk.X, padx=10, pady=5)
        
        log_level_label = Ctk.CTkLabel(
            log_level_frame,
            text="Logging Level:",
            width=120,
            anchor="w",
            text_color="#2E2E3A",
            font=("Arial", 12)
        )
        log_level_label.pack(side=tk.LEFT, padx=(8, 0))
        
        self.log_level_var = tk.StringVar()
        initial_log_level = self.parent.shared_data.get("log_level").get() if self.parent.shared_data.get("log_level") else "INFO"
        valid_log_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        self.log_level_var.set(initial_log_level if initial_log_level in valid_log_levels else "INFO")
        self.log_level_dropdown = Ctk.CTkComboBox(
            log_level_frame,
            values=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
            variable=self.log_level_var,
            state="readonly",
            width=170,
            fg_color="#FFFFFF",
            text_color="#000000",
            button_color="#A1B9D0",
            button_hover_color="#7A92A9",
            border_width=1,
            border_color="#B3C8DD",
            dropdown_fg_color="#FFFFFF",
            font=("Arial", 11)
        )
        self.log_level_dropdown.pack(side=tk.LEFT, padx=8, pady=8)
        
        # Add buttons for general tab options with modern styling
        buttons_frame = Ctk.CTkFrame(content_frame, fg_color="#E0E8F0")
        buttons_frame.pack(fill=tk.X, padx=10, pady=10)
        
        self.apply_logging_settings_button = Ctk.CTkButton(
            buttons_frame,
            text="Apply Logging Settings",
            command=self._apply_logging_settings,
            fg_color="#A1B9D0",
            hover_color="#7A92A9",
            text_color="#000000",
            height=35,
            width=200,
            corner_radius=8,
            border_width=1,
            border_color="#8AA2BC",
            font=("Arial", 12)
        )
        self.apply_logging_settings_button.pack(side=tk.RIGHT, padx=8, pady=8)
    
    def _init_bms_injection_tab(self):
        """Initialize the BMS Injection tab content."""
        # Get the scrollable frame content area
        content_frame = self._get_scrollable_content(self.bms_injection_tab)
        
        # Create data type selector frame at the top with modern styling
        data_type_frame = Ctk.CTkFrame(content_frame, fg_color="#E0E8F0", border_width=1, border_color="#B3C8DD")
        data_type_frame.pack(fill=tk.X, padx=10, pady=10)
        
        # Section title with modern styling
        bms_section_label = Ctk.CTkLabel(
            data_type_frame,
            text="BMS Data Selection",
            font=("Arial", 16, "bold"),
            text_color="#000033",
            fg_color="transparent"
        )
        bms_section_label.pack(anchor="w", padx=12, pady=(12, 6))
        
        # Data type selector container
        selector_frame = Ctk.CTkFrame(data_type_frame, fg_color="#E0E8F0")
        selector_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # Add data type label with modern styling
        data_type_label = Ctk.CTkLabel(
            selector_frame,
            text="Data Type:",
            width=120,
            anchor="w",
            text_color="#2E2E3A",
            font=("Arial", 12)
        )
        data_type_label.pack(side=tk.LEFT, padx=(8, 0), pady=8)
        
        # Add data type dropdown with modern styling
        self.data_type_var = tk.StringVar(value="Objective Data")
        self.data_type_dropdown = Ctk.CTkComboBox(
            selector_frame,
            values=["Objective Data", "Class Table Data"],
            variable=self.data_type_var,
            state="readonly",
            width=170,
            fg_color="#FFFFFF",
            text_color="#000000",
            button_color="#A1B9D0",
            button_hover_color="#7A92A9",
            border_width=1,
            border_color="#B3C8DD",
            dropdown_fg_color="#FFFFFF",
            font=("Arial", 11),
            command=self._update_bms_content
        )
        self.data_type_dropdown.pack(side=tk.LEFT, padx=8, pady=8)
        
        # Add content frame that will be updated based on selection with modern styling
        self.dynamic_content_frame = Ctk.CTkFrame(content_frame, fg_color="#E0E8F0", border_width=1, border_color="#B3C8DD")
        self.dynamic_content_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Load objective types from templates and cache
        self.objective_types = self._load_objective_types()
        
        # Create sub-frames for different data types (initially hidden)
        self.objective_frame = Ctk.CTkFrame(self.dynamic_content_frame, fg_color="#E0E8F0")
        self.ct_frame = Ctk.CTkFrame(self.dynamic_content_frame, fg_color="#E0E8F0")
        
        # Initialize with default selection (Objective Data)
        self._update_bms_content("Objective Data")
    
    def _load_objective_types(self):
        """Load objective types from templates and cache.
        
        Returns a dictionary of objective types with ID as key and name as value.
        Tries to load from:  
        1. objective_templates.json
        2. Objective cache
        """
        objective_types = {}
        
        try:
            # Try to load from objective_templates.json first
            obj_templates = load_json(JsonFiles.OBJECTIVE_TEMPLATES, default={})
            if obj_templates:
                for obj_id in obj_templates.keys():
                    # Add to objective_types with the ID-Name format
                    type_name = self._get_type_name(int(obj_id))
                    objective_types[obj_id] = f"{obj_id}: {type_name}"
                logging.info(f"Loaded {len(objective_types)} objective types from templates")
            
            # If no types found in templates, try objective cache
            if not objective_types:
                cache_types = objective_cache.get_objective_types()
                if cache_types:
                    for obj_id, type_name in cache_types.items():
                        objective_types[str(obj_id)] = f"{obj_id}: {type_name}"
                    logging.info(f"Loaded {len(objective_types)} objective types from cache")
            
            # If still no types found, use default fallback list
            if not objective_types:
                # Provide basic fallback list
                fallback_types = {
                    "1": "1: Airbase",
                    "2": "2: Airstrip",
                    "3": "3: Army Base",
                    "9": "9: Command & Control",
                    "20": "20: Power Plant",
                    "31": "31: SAM Site"
                }
                objective_types = fallback_types
                logging.info("Using fallback objective types list")
        
        except Exception as e:
            logging.error(f"Error loading objective types: {str(e)}")
            # Provide minimal fallback if everything fails
            objective_types = {"1": "1: Airbase"}
        
        return objective_types
        
    def _load_objective_fields(self, selection):
        """Load the fields for the selected objective type.
        
        This method loads objective properties from objective_templates.json and creates
        consistent field entries that match the bms_injection_window.py implementation.
        
        Args:
            selection (str): The selected objective type in format 'ID: Name'
        """
        # Performance optimization - Use a loading indicator for large datasets
        loading_start_time = time.time()
        
        # Clear existing fields
        for widget in self.obj_fields_frame.winfo_children():
            widget.destroy()
            
        # Get the type ID from the selection string (format: "ID: Name")
        try:
            # Extract just the ID number from the selection string
            type_id = selection.split(":")[0].strip()
        except Exception as e:
            logging.error(f"Error parsing objective type: {selection} - {str(e)}")
            return
        
        # Load the template for this type - same approach as bms_injection_window.py
        try:
            # ONLY load directly from the JSON file - no fallback to cache or injector
            templates = load_json(JsonFiles.OBJECTIVE_TEMPLATES, default={})
            template = {}
            
            # Get template for this type from JSON file only
            if templates and str(type_id) in templates:
                template = templates[str(type_id)]
                logging.info(f"Template source: objective_templates.json file")
            else:
                # If not found in file, use empty template - validation should prevent this
                logging.info(f"Type {type_id} not found in objective_templates.json")
                template = {}
            
            # Create fields for each property - same approach as bms_injection_window.py
            self.field_vars = {}  # Store StringVars for each field
            
            # Create a container frame without scrolling (uses main window scrolling)
            fields_container = Ctk.CTkFrame(
                self.obj_fields_frame, 
                fg_color="#E0E8F0",
                border_width=1,
                border_color="#B3C8DD"
            )
            fields_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
            
            # Add a title for the properties section
            props_title = Ctk.CTkLabel(
                fields_container,
                text="Objective Properties",
                font=("Arial", 12, "bold"),
                text_color="#000033",
                fg_color="#D5E3F0",
                corner_radius=5
            )
            props_title.pack(fill=tk.X, padx=5, pady=5)
            
            # Common fields that all objectives have - same as bms_injection_window.py
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
            
            # Group detection properties
            detection_frame = Ctk.CTkFrame(fields_container, fg_color="#E0E8F0")
            detection_frame.pack(fill=tk.X, padx=5, pady=5)
            
            det_label = Ctk.CTkLabel(
                detection_frame,
                text="Detection Properties",
                font=("Arial", 12, "bold"),
                text_color="#000033",
                fg_color="#D5E3F0",
                corner_radius=5
            )
            det_label.pack(fill=tk.X, padx=5, pady=5)
            
            # Group damage properties
            damage_frame = Ctk.CTkFrame(fields_container, fg_color="#E0E8F0")
            damage_frame.pack(fill=tk.X, padx=5, pady=5)
            
            dam_label = Ctk.CTkLabel(
                damage_frame,
                text="Damage Properties",
                font=("Arial", 12, "bold"),
                text_color="#000033",
                fg_color="#D5E3F0",
                corner_radius=5
            )
            dam_label.pack(fill=tk.X, padx=5, pady=5)
            
            # Group other properties including Value field
            other_frame = Ctk.CTkFrame(fields_container, fg_color="#E0E8F0")
            other_frame.pack(fill=tk.X, padx=5, pady=5)
            
            other_label = Ctk.CTkLabel(
                other_frame,
                text="Other Properties",
                font=("Arial", 12, "bold"),
                text_color="#000033",
                fg_color="#D5E3F0",
                corner_radius=5
            )
            other_label.pack(fill=tk.X, padx=5, pady=5)
            
            # Create field entries for each field with proper grouping
            for field_name, default_value in common_fields:
                # Get value from template or use default
                field_value = template.get(field_name, default_value)
                
                # Create StringVar and store for later retrieval
                var = tk.StringVar(value=field_value)
                self.field_vars[field_name] = var
                
                # Create property row - group by field name prefix
                if field_name.startswith("Det_"):
                    target_frame = detection_frame
                elif field_name.startswith("Dam_"):
                    target_frame = damage_frame
                else:
                    target_frame = other_frame
                    
                # Create row frame
                row_frame = Ctk.CTkFrame(target_frame, fg_color="#E0E8F0")
                row_frame.pack(fill=tk.X, padx=5, pady=2)
                
                # Property label
                prop_label = Ctk.CTkLabel(
                    row_frame,
                    text=field_name + ":",
                    width=150,
                    anchor="w",
                    text_color="#2E2E3A",
                    font=("Arial", 11)
                )
                prop_label.pack(side=tk.LEFT, padx=5, pady=3)
                
                # Property entry
                prop_entry = Ctk.CTkEntry(
                    row_frame,
                    textvariable=var,
                    width=180,  # Increased width for better visibility
                    fg_color="#FFFFFF",
                    text_color="#000000",
                    border_width=1,
                    border_color="#B3C8DD",
                    font=("Arial", 11)
                )
                prop_entry.pack(side=tk.LEFT, padx=5, pady=5, fill=tk.X, expand=True)
            
            # Performance metric
            elapsed_time = time.time() - loading_start_time
            logging.info(f"Loaded {len(self.field_vars)} properties for objective type {type_id} in {elapsed_time:.2f} seconds")
            
        except Exception as e:
            logging.error(f"Error loading objective fields for type {type_id}: {str(e)}")
            # Create error message
            error_label = Ctk.CTkLabel(
                self.obj_fields_frame,
                text=f"Error loading fields: {str(e)}",
                font=("Arial", 12),
                text_color="#FF0000",
                fg_color="transparent"
            )
            error_label.pack(padx=10, pady=20)
    
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
    
    def _update_bms_content(self, selection=None):
        """Update the BMS Injection tab content based on data type selection.
        
        This method handles switching between Objective Data and Class Table Data views,
        ensuring that the appropriate data is loaded and displayed.
        """
        # Start performance tracking
        start_time = time.time()
        
        # Clear existing content in dynamic frame
        for widget in self.dynamic_content_frame.winfo_children():
            widget.pack_forget()
            
        # If no selection is provided, get from StringVar
        if not selection:
            selection = self.data_type_var.get()
        else:
            # Update StringVar to match selection
            self.data_type_var.set(selection)
            
        # Store current data type for context-aware operations
        self.current_data_type = selection
        
        if selection == "Objective Data":
            # Initialize objective data interface if not already done
            if not hasattr(self, 'objective_type_var'):
                self._init_objective_interface()
            
            # Show objective frame
            self.objective_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
            
            # Update data source indicator
            if hasattr(self, 'data_source_label'):
                self.data_source_label.configure(text="Data Source: objective_templates.json")
            
            # Load data for the currently selected objective type
            if hasattr(self, 'objective_type_var') and self.objective_type_var.get():
                self._load_objective_fields(self.objective_type_var.get())
            else:
                # Auto-select first objective type if none selected
                if hasattr(self, 'objective_types') and self.objective_types:
                    first_type = next(iter(self.objective_types.values()))
                    self.objective_type_var.set(first_type)
                    self._load_objective_fields(first_type)
        
        elif selection == "Class Table Data":
            # Initialize CT data interface if not already done
            if not hasattr(self, 'ct_type_var'):
                self._init_ct_interface()
                
            # Show CT frame
            self.ct_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
            
            # Update data source indicator
            if hasattr(self, 'data_source_label'):
                self.data_source_label.configure(text="Data Source: ct_templates.json")
            
            # Load data for the currently selected CT type
            if hasattr(self, 'ct_type_var') and self.ct_type_var.get():
                self._load_ct_fields(self.ct_type_var.get())
            else:
                # Auto-select first CT type if none selected
                if hasattr(self, 'ct_types') and self.ct_types:
                    first_type = next(iter(self.ct_types.values()))
                    self.ct_type_var.set(first_type)
                    self._load_ct_fields(first_type)
            
        # Log performance metrics
        elapsed_time = time.time() - start_time
        logging.info(f"Updated BMS content for {selection} in {elapsed_time:.4f} seconds")
            
    def _save_objective_template(self):
        """Save the current objective template configuration.
        
        This method saves field values to objective_templates.json using the same
        approach as bms_injection_window.py for consistency.
        """
        try:
            # Get the type ID from the selection string
            selection = self.objective_type_var.get()
            type_id = selection.split(":")[0].strip()
            
            # Get field values - stored as strings to make saving/loading simpler
            fields = {}
            for field_name, string_var in self.field_vars.items():
                raw_value = string_var.get().strip()
                fields[field_name] = raw_value
            
            # Show confirmation dialog before saving
            if messagebox.askyesno("Confirm Save", f"Save template for objective type {type_id}?\nThis will update the template in objective_templates.json"):
                # Load existing templates to preserve other types
                objective_templates = load_json(JsonFiles.OBJECTIVE_TEMPLATES, default={})
                
                # Create or update the template for the current type
                type_key_str = str(type_id)  # Ensure it's a string for JSON keys
                
                if type_key_str not in objective_templates:
                    objective_templates[type_key_str] = {}
                    
                # Update the fields in the template - same approach as bms_injection_window.py
                objective_templates[type_key_str].update(fields)
                
                # Save updated templates
                success = save_json(JsonFiles.OBJECTIVE_TEMPLATES, objective_templates)
                if success:
                    logging.info(f"Successfully saved field values to objective_templates.json for type {type_id}")
                    messagebox.showinfo("Template Saved", f"Template for objective type {type_id} saved successfully.")
                else:
                    logging.error(f"Failed to save field values to objective_templates.json")
                    messagebox.showerror("Error", "Failed to save template.")
            
        except Exception as e:
            logging.error(f"Error saving objective template: {str(e)}")
            messagebox.showerror("Error", f"Failed to save template: {str(e)}")
    
    def _reset_objective_fields(self):
        """
        Calculate median values for fields based on existing objectives of the same type.
        Uses the same sophisticated OCD analysis as bms_injection_window.py.
        Only updates the GUI fields, does not save data to any file.
        """
        from processing_window import ProcessType, run_template_generation
        from tkinter import messagebox
        import os
        
        # 1. Initialization - Get the selected type and validate BMS path
        selection = self.objective_type_var.get()
        if not selection or ':' not in selection:
            messagebox.showerror("Error", "Please select an objective type first")
            return False
            
        try:
            type_key = int(selection.split(':', 1)[0].strip())
        except ValueError:
            logging.error(f"Invalid type key in selection: {selection}")
            messagebox.showerror("Error", "Invalid objective type selected")
            return False
            
        type_name = self._get_type_name(type_key)
        logging.info(f"RESETTING VALUES FOR OBJECTIVE TYPE: {type_key} ({type_name})")
        
        # Validate BMS path
        if not self.bms_path:
            logging.critical("BMS path is None or empty")
            messagebox.showerror("Error", "BMS path is not set. Please check the BMS path in General tab.")
            return False
            
        # Handle case where bms_path might be a file instead of directory
        if os.path.isfile(self.bms_path):
            logging.warning(f"BMS path '{self.bms_path}' is a file, extracting directory")
            bms_path = os.path.dirname(self.bms_path)
        else:
            bms_path = self.bms_path
            
        if not os.path.isdir(bms_path):
            logging.critical(f"BMS directory does not exist: '{bms_path}'")
            messagebox.showerror("Error", f"Invalid BMS installation directory: {bms_path}\nPlease check the BMS path in General tab.")
            return False
            
        logging.info(f"Using BMS path: {bms_path}")
        
        # Define the calculation task that will run in the background
        def calculate_objective_default_values_task(processing_window=None):
            """Background task to calculate median values for the selected objective type."""
            return self._calculate_objective_median_values_for_type(type_key, type_name, bms_path)
        
        # Run the calculation with a processing window
        logging.info(f"[SETTINGS] Starting objective default value calculation with processing window for type {type_key}")
        result = run_template_generation(
            parent=self,
            task_function=calculate_objective_default_values_task,
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
            self._update_objective_gui_fields_with_values(calculated_values)
            
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
    
    def _calculate_objective_median_values_for_type(self, type_key, type_name, bms_path):
        """
        Calculate median values for objective fields based on existing objectives of the given type.
        This method contains the core processing logic separated from UI updates.
        
        Args:
            type_key: The objective type key (1-31)
            type_name: The human-readable name of the objective type
            bms_path: The BMS installation directory path
            
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
        
        # Find the CT file with case-insensitive search
        logging.debug(f"Searching for CT file in directory: '{bms_path}'")
        ct_path = None
        for ct_filename in ["Falcon4_CT.xml", "Falcon4_CT.XML"]:
            potential_path = os.path.join(bms_path, ct_filename)
            logging.debug(f"Checking for CT file: '{potential_path}'")
            if os.path.exists(potential_path):
                ct_path = potential_path
                logging.info(f"Found CT file: '{ct_path}'")
                break
            else:
                logging.debug(f"CT file not found: '{potential_path}'")
        
        if not ct_path:
            logging.error(f"CT file not found in '{bms_path}' (tried both .xml and .XML)")
            return {
                'success': False,
                'error': f"CT file not found in {bms_path}"
            }
        
        try:
            # 2. CT File Processing - Load and parse the CT file
            logging.info(f"Loading CT file: {ct_path}")
            tree = ET.parse(ct_path)
            root = tree.getroot()
            
            # Verify we have CT entries with the target type
            matching_ct_entries = []
            for ct_elem in root.findall('.//CT'):
                type_elem = ct_elem.find("Type")
                if type_elem is not None and type_elem.text and type_elem.text.strip().isdigit():
                    ct_type = int(type_elem.text.strip())
                    if ct_type == type_key:
                        ct_num = ct_elem.get("Num")
                        matching_ct_entries.append(ct_num)
            
            # 3. OCD Directory Scanning
            obj_dir = os.path.join(bms_path, "ObjectiveRelatedData")
            if not os.path.exists(obj_dir) or not os.path.isdir(obj_dir):
                logging.error(f"ObjectiveRelatedData directory not found at {obj_dir}")
                messagebox.showerror("Error", f"ObjectiveRelatedData directory not found at {obj_dir}")
                return False
                
            # Verify CT file structure
            ct_entries = root.findall('.//CT')
            if not ct_entries:
                # Try alternative format if standard format not found
                ct_entries = root.findall('./CT/Entry')
            
            # Get all OCD directories
            ocd_dirs = [d for d in os.listdir(obj_dir) if os.path.isdir(os.path.join(obj_dir, d)) and d.startswith("OCD_")]
            logging.info(f"Found {len(ocd_dirs)} OCD directories")
            
            # Counter for found OCD files of our type
            ocd_count = 0
            processed_count = 0
            
            # Process each OCD directory
            for ocd_dir_name in ocd_dirs:
                processed_count += 1
                if processed_count % 100 == 0:
                    logging.info(f"Progress: Processed {processed_count}/{len(ocd_dirs)} directories...")
                    
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
                        ct_elem = root.find(f".//CT[@Num='{ct_idx}']")
                        
                        # If not found by @Num attribute, try finding by Index element
                        if ct_elem is None:
                            # Search for CT entries with matching Index element
                            for entry in root.findall("./CT/Entry"):
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
                    logging.error(f"Error processing OCD file {ocd_file}: {str(e)}")
            
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
                            if field in self.field_vars:
                                current_value = self.field_vars[field].get()
                                calculated_values[field] = current_value
                            else:
                                calculated_values[field] = "0"
                else:
                    # No values found for this field in any OCD files
                    if field in self.field_vars:
                        current_value = self.field_vars[field].get()
                        calculated_values[field] = current_value
                    else:
                        calculated_values[field] = "0"
            
            # Count fields that would be updated
            field_count = len([field for field in calculated_values.keys() if field in self.field_vars])
            
            # Return result based on success
            if ocd_count == 0:
                # No matching OCD files found
                logging.warning(f"No objectives of type {type_key} ({type_name}) were found")
                return {
                    'success': False,
                    'ocd_count': 0,
                    'field_count': 0,
                    'calculated_values': {}
                }
            else:
                # Successfully calculated values
                logging.info(f"Successfully calculated median values from {ocd_count} existing objectives, updating {field_count} fields")
                return {
                    'success': True,
                    'ocd_count': ocd_count,
                    'field_count': field_count,
                    'calculated_values': calculated_values
                }
                
        except Exception as e:
            # Log the error
            error_msg = f"Error calculating objective median values: {e}"
            logging.error(f"ERROR: {error_msg}")
            traceback.print_exc()
            return {
                'success': False,
                'error': error_msg,
                'ocd_count': 0,
                'field_count': 0,
                'calculated_values': {}
            }
    
    def _update_objective_gui_fields_with_values(self, calculated_values):
        """
        Update the objective GUI field variables with the calculated values.
        
        Args:
            calculated_values: Dictionary of field names to calculated values
        """
        updated_fields = set()
        field_count = 0
        
        # Make sure we have the field variables before trying to update them
        if not hasattr(self, 'field_vars') or not self.field_vars:
            logging.warning("No objective field variables available to update")
            return 0
            
        for field_name, string_var in self.field_vars.items():
            if field_name in calculated_values and field_name not in updated_fields:
                value = calculated_values[field_name]
                # Update the StringVar
                string_var.set(str(value))
                
                # Count updated fields and mark as updated
                field_count += 1
                updated_fields.add(field_name)
                logging.debug(f"Updated objective field {field_name} = {value}")
        
        logging.info(f"Updated {field_count} objective GUI fields with calculated values")
        return field_count
    
    def _toggle_backup_bms(self):
        """Toggle backup BMS files setting.
        
        Controls whether BMS files are backed up before modification.
        This is a safety feature to prevent data loss.
        """
        # Update backup BMS setting with optimized performance
        try:
            # Store setting in configuration
            if hasattr(self.parent, 'shared_data'):
                # Use string value for compatibility with MainGui
                backup_value = "1" if self.backup_bms_var.get() else "0"
                # Store the value in parent's shared data
                if 'backup_bms_files' in self.parent.shared_data:
                    self.parent.shared_data['backup_bms_files'].set(backup_value)
                else:
                    # Create the variable if it doesn't exist
                    self.parent.shared_data['backup_bms_files'] = tk.StringVar(value=backup_value)
                
                # Update in a thread-safe manner and log clearly
                status = "enabled" if self.backup_bms_var.get() else "disabled"
                # Use the unified logging approach that respects user preferences
                logging.info(f"BMS file backup {status}")
                
                # Make the logging more prominent for debugging
                logging.info(f"======= BMS BACKUP SETTING CHANGED: {status} =======")
        except Exception as e:
            logging.error(f"Error toggling BMS backup setting: {str(e)}")
    
    def _toggle_backup_features(self):
        """Toggle backup generated features setting.
        
        Controls whether generated features are backed up for critical cases.
        This helps with troubleshooting and recovery if issues arise.
        """
        # Update backup features setting with optimized performance
        try:
            # Store setting in configuration
            if hasattr(self.parent, 'shared_data'):
                # Use string value for compatibility with MainGui
                backup_value = "1" if self.backup_features_var.get() else "0"
                
                # Update the shared_data variable to be used by the BmsInjector
                if 'backup_features_files' in self.parent.shared_data:
                    self.parent.shared_data['backup_features_files'].set(backup_value)
                else:
                    self.parent.shared_data['backup_features_files'] = tk.StringVar(value=backup_value)
                
                            # Update in a thread-safe manner
            status = "enabled" if self.backup_features_var.get() else "disabled"
            logging.info(f"Critical features backup {status}")
        except Exception as e:
            logging.error(f"Error toggling features backup setting: {str(e)}")
    
    def _init_objective_interface(self):
        """Initialize the interface for objective data."""
        # Create the objective type selection section
        obj_type_frame = Ctk.CTkFrame(self.objective_frame, fg_color="#E0E8F0")
        obj_type_frame.pack(fill=tk.X, padx=10, pady=10)
        
        # Title for objective type section
        obj_type_title = Ctk.CTkLabel(
            obj_type_frame,
            text="Objective Type Configuration",
            font=("Arial", 14, "bold"),
            text_color="#000033",
            fg_color="transparent"
        )
        obj_type_title.pack(anchor="w", padx=10, pady=(10, 5))
        
        # Objective type selection container
        type_select_frame = Ctk.CTkFrame(obj_type_frame, fg_color="#E0E8F0")
        type_select_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # Objective type label
        type_label = Ctk.CTkLabel(
            type_select_frame,
            text="Objective Type:",
            width=120,
            anchor="w",
            text_color="#2E2E3A",
            font=("Arial", 12)
        )
        type_label.pack(side=tk.LEFT, padx=(8, 0), pady=8)
        
        # Objective type dropdown
        self.objective_type_var = tk.StringVar(value=next(iter(self.objective_types.values()), "1: Airbase"))
        self.objective_type_dropdown = Ctk.CTkComboBox(
            type_select_frame,
            values=list(self.objective_types.values()),
            variable=self.objective_type_var,
            state="readonly",
            width=250,
            fg_color="#FFFFFF",
            text_color="#000000",
            button_color="#A1B9D0",
            button_hover_color="#7A92A9",
            border_width=1,
            border_color="#B3C8DD",
            dropdown_fg_color="#FFFFFF",
            font=("Arial", 11),
            command=self._load_objective_fields
        )
        self.objective_type_dropdown.pack(side=tk.LEFT, padx=8, pady=8)
        
        # Create fields frame for the objective properties
        self.obj_fields_frame = Ctk.CTkFrame(self.objective_frame, fg_color="#E0E8F0", border_width=1, border_color="#B3C8DD")
        self.obj_fields_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Buttons frame for save and default options
        buttons_frame = Ctk.CTkFrame(self.objective_frame, fg_color="#E0E8F0")
        buttons_frame.pack(fill=tk.X, padx=10, pady=10)
        
        # Save button for objective data
        self.save_obj_button = Ctk.CTkButton(
            buttons_frame,
            text="Save Template",
            command=self._save_objective_template,
            fg_color="#A1B9D0",
            hover_color="#7A92A9",
            text_color="#000000",
            height=35,
            width=150,
            corner_radius=8,
            border_width=1,
            border_color="#8AA2BC",
            font=("Arial", 12)
        )
        self.save_obj_button.pack(side=tk.LEFT, padx=8, pady=8)
        
        # Default button for objective data
        self.default_obj_button = Ctk.CTkButton(
            buttons_frame,
            text="Reset to Default",
            command=self._reset_objective_fields,
            fg_color="#A1B9D0",
            hover_color="#7A92A9",
            text_color="#000000",
            height=35,
            width=150,
            corner_radius=8,
            border_width=1,
            border_color="#8AA2BC",
            font=("Arial", 12)
        )
        self.default_obj_button.pack(side=tk.LEFT, padx=8, pady=8)
        
        # Load the fields for initially selected objective type
        if self.objective_type_var.get():
            self._load_objective_fields(self.objective_type_var.get())
    
    def _load_ct_fields(self, selection):
        """Load the fields for the selected Class Table type.
        
        This method loads CT field data directly from ct_templates.json using the same
        approach as the objective data fields for consistency.
        
        Args:
            selection (str): The selected class table type in format 'ID: Name'
        """
        # Start performance tracking
        loading_start_time = time.time()
        
        # Clear existing fields
        for widget in self.ct_fields_frame.winfo_children():
            widget.destroy()
            
        # Get the type ID from the selection string (format: "ID: Name")
        try:
            # Extract just the ID number from the selection string
            type_id = selection.split(":")[0].strip()
        except Exception as e:
            logging.error(f"Error parsing class table type: {selection} - {str(e)}")
            messagebox.showerror("Error", f"Failed to parse class table type: {str(e)}")
            return
        
        # Load the template for this type directly from ct_templates.json
        try:
            # Load templates using json_path_handler - same approach as objective fields
            from utils.json_path_handler import load_json, JsonFiles
            ct_templates = load_json(JsonFiles.CT_TEMPLATES, default={})
            
            # Get template for this specific type
            if type_id in ct_templates:
                template = ct_templates[type_id]
            else:
                # Create default template if not found
                template = self._create_default_ct_template(type_id)
                logging.info(f"Using default template for CT type {type_id}")
            
            # Create fields for each property
            self.ct_field_vars = {}  # Store StringVars for each field
            
            # Create a container frame without scrolling (uses main window scrolling)
            fields_container = Ctk.CTkFrame(
                self.ct_fields_frame, 
                fg_color="#E0E8F0",
                border_width=1,
                border_color="#B3C8DD"
            )
            fields_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
            
            # Add a title for the properties section
            props_title = Ctk.CTkLabel(
                fields_container,
                text="Class Table Properties",
                font=("Arial", 12, "bold"),
                text_color="#000033",
                fg_color="#D5E3F0",
                corner_radius=5
            )
            props_title.pack(fill=tk.X, padx=5, pady=5)
            
            # Create categories frame similar to objective interface
            categories_frame = Ctk.CTkFrame(fields_container, fg_color="#E0E8F0")
            categories_frame.pack(fill=tk.X, padx=5, pady=5)
            
            # Define field categories similar to objective interface
            field_categories = {
                "Core Properties": [
                    "Id", "CollisionType", "CollisionRadius", "UpdateRate", "UpdateTolerance",
                    "FineUpdateRange", "FineUpdateForceRange", "FineUpdateMultiplier"
                ],
                "Damage Properties": [
                    "DamageSeed", "HitPoints"
                ],
                "Version Properties": [
                    "MajorRev", "MinRev"
                ],
                "Management Properties": [
                    "CreatePriority", "ManagementDomain", "Transferable", "Private", 
                    "Tangible", "Collidable", "Global", "Persistent"
                ],
                "Graphics Properties": [
                    "GraphicsNormal", "GraphicsRepaired", "GraphicsDamaged", "GraphicsDestroyed",
                    "GraphicsLeftDestroyed", "GraphicsRightDestroyed", "GraphicsBothDestroyed"
                ],
                "Classification Properties": [
                    "Domain", "Class", "SubType", "Specific", "Owner", "Class_6", "Class_7",
                    "MoverDefinitionData", "EntityType"
                ]
            }
            
            # Create fields for each category
            for category, field_names in field_categories.items():
                # Create category frame
                category_frame = Ctk.CTkFrame(categories_frame, fg_color="#E8F0F7")
                category_frame.pack(fill=tk.X, padx=5, pady=5)
                
                # Category title
                category_title = Ctk.CTkLabel(
                    category_frame,
                    text=category,
                    font=("Arial", 11, "bold"),
                    text_color="#2E2E3A",
                    fg_color="transparent"
                )
                category_title.pack(anchor="w", padx=10, pady=(5, 0))
                
                # Create fields for this category
                for field_name in field_names:
                    if field_name in template:
                        # Create StringVar and store for later retrieval
                        var = tk.StringVar(value=str(template[field_name]))
                        self.ct_field_vars[field_name] = var
                        
                        # Create row frame
                        row_frame = Ctk.CTkFrame(category_frame, fg_color="#E8F0F7")
                        row_frame.pack(fill=tk.X, padx=10, pady=2)
                        
                        # Property label
                        prop_label = Ctk.CTkLabel(
                            row_frame,
                            text=field_name + ":",
                            width=150,
                            anchor="w",
                            text_color="#2E2E3A",
                            font=("Arial", 11)
                        )
                        prop_label.pack(side=tk.LEFT, padx=5, pady=3)
                        
                        # Property entry
                        prop_entry = Ctk.CTkEntry(
                            row_frame,
                            textvariable=var,
                            width=180,
                            fg_color="#FFFFFF",
                            text_color="#000000",
                            border_width=1,
                            border_color="#B3C8DD",
                            font=("Arial", 11)
                        )
                        prop_entry.pack(side=tk.LEFT, padx=5, pady=5, fill=tk.X, expand=True)
            
            # Performance metric
            elapsed_time = time.time() - loading_start_time
            logging.info(f"Loaded {len(self.ct_field_vars)} properties for class table type {type_id} in {elapsed_time:.2f} seconds")
            
        except Exception as e:
            logging.error(f"Error loading class table fields for type {type_id}: {str(e)}")
            # Create error message
            error_label = Ctk.CTkLabel(
                self.ct_fields_frame,
                text=f"Error loading fields: {str(e)}",
                font=("Arial", 12),
                text_color="#FF0000",
                fg_color="transparent"
            )
            error_label.pack(padx=10, pady=20)
    
    def _create_default_ct_template(self, type_id):
        """Create a default CT template for a given type ID.
        
        Args:
            type_id (str): The CT type ID
            
        Returns:
            dict: Default CT template
        """
        return {
            "Id": "0",
            "CollisionType": "0",
            "CollisionRadius": "0.0",
            "Domain": "0",
            "Class": "0",
            "SubType": "0",
            "Specific": "0",
            "Owner": "0",
            "Class_6": "0",
            "Class_7": "0",
            "UpdateRate": "0",
            "UpdateTolerance": "0",
            "FineUpdateRange": "0.0",
            "FineUpdateForceRange": "0.0",
            "FineUpdateMultiplier": "0.0",
            "DamageSeed": "0",
            "HitPoints": "0",
            "MajorRev": "0",
            "MinRev": "0",
            "CreatePriority": "0",
            "ManagementDomain": "0",
            "Transferable": "0",
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
            "EntityType": "0"
        }
            
    def _save_ct_template(self):
        """Save the current class table template configuration.
        
        This method saves field values to ct_templates.json using the same
        approach as the objective template save for consistency.
        """
        try:
            # Get the type ID from the selection string
            selection = self.ct_type_var.get()
            type_id = selection.split(":")[0].strip()
            
            # Get field values - stored as strings to make saving/loading simpler
            fields = {}
            for field_name, string_var in self.ct_field_vars.items():
                raw_value = string_var.get().strip()
                fields[field_name] = raw_value if raw_value else "0"
            
            # Load existing templates
            from utils.json_path_handler import load_json, save_json, JsonFiles
            templates = load_json(JsonFiles.CT_TEMPLATES, default={})
            
            # Update the template for this type
            templates[type_id] = fields
            
            # Save back to file
            success = save_json(JsonFiles.CT_TEMPLATES, templates)
            
            if success:
                messagebox.showinfo("Template Saved", f"Template for class table type {type_id} has been saved successfully.")
                logging.info(f"Saved template for class table type {type_id}")
            else:
                messagebox.showerror("Error", f"Failed to save template for class table type {type_id}.")
                
        except Exception as e:
            logging.error(f"Error saving class table template: {str(e)}")
            messagebox.showerror("Error", f"Failed to save template: {str(e)}")
    
    def _reset_ct_fields(self):
        """
        Calculate median values for CT fields based on existing CT entries of the same type.
        Uses the same sophisticated CT analysis as bms_injection_window.py.
        Only updates the GUI fields, does not save data to any file.
        """
        from processing_window import ProcessType, run_template_generation
        from tkinter import messagebox
        import os
        
        # 1. Initialization - Get the selected type and validate BMS path
        selection = self.ct_type_var.get()
        if not selection or ':' not in selection:
            messagebox.showerror("Error", "Please select a CT type first")
            return False
            
        # Extract type key from selection string
        type_key = int(selection.split(":")[0].strip())
        type_name = self._get_type_name(type_key)
        logging.info(f"RESETTING CT VALUES FOR TYPE: {type_key} ({type_name})")
        
        # Validate BMS path
        if not self.bms_path:
            logging.critical("BMS path is None or empty")
            messagebox.showerror("Error", "BMS path is not set. Please check the BMS path in General tab.")
            return False
            
        # Handle case where bms_path might be a file instead of directory
        if os.path.isfile(self.bms_path):
            logging.warning(f"BMS path '{self.bms_path}' is a file, extracting directory")
            bms_path = os.path.dirname(self.bms_path)
        else:
            bms_path = self.bms_path
            
        if not os.path.isdir(bms_path):
            logging.critical(f"BMS directory does not exist: '{bms_path}'")
            messagebox.showerror("Error", f"Invalid BMS installation directory: {bms_path}\nPlease check the BMS path in General tab.")
            return False
        
        # Define the calculation task that will run in the background
        def calculate_ct_default_values_task(processing_window=None):
            """Background task to calculate median values for the selected CT type."""
            return self._calculate_ct_median_values_for_type(type_key, type_name, bms_path)
        
        # Run the calculation with a processing window
        logging.info(f"[SETTINGS] Starting CT default value calculation with processing window for type {type_key}")
        result = run_template_generation(
            parent=self,
            task_function=calculate_ct_default_values_task,
            process_type=ProcessType.CALCULATE_DEFAULT_VALUES,
            title="Calculating Default CT Values",
            message=f"Calculating median values for {type_name} CT entries..."
        )
        
        # Handle the result
        if result and isinstance(result, dict) and result.get('success'):
            calculated_values = result.get('calculated_values', {})
            ct_count = result.get('ct_count', 0)
            field_count = result.get('field_count', 0)
            
            # Update the GUI fields with calculated values
            self._update_ct_gui_fields_with_values(calculated_values)
            
            # Show success message
            messagebox.showinfo(
                "Reset Complete",
                f"Successfully calculated median values from {ct_count} existing CT entries.\n"
                f"Updated {field_count} fields with median values."
            )
            return True
        elif result and isinstance(result, dict) and result.get('success') is False:
            # No matching CT entries found
            messagebox.showwarning(
                "No Matching CT Entries Found",
                f"No CT entries of type {type_key} ({type_name}) were found.\n"
                f"Field values have been kept as is."
            )
            return False
        else:
            # Error occurred
            messagebox.showerror(
                "Error",
                "An error occurred while calculating default CT values. Check the console for details."
            )
            return False
    
    def _calculate_ct_median_values_for_type(self, type_key, type_name, bms_path):
        """
        Calculate median values for CT fields based on existing CT entries of the given type.
        This method contains the core processing logic separated from UI updates.
        
        Args:
            type_key: The objective type key (1-31)
            type_name: The human-readable name of the objective type
            bms_path: The BMS installation directory path
            
        Returns:
            dict: Result dictionary with success status, calculated values, and counts
        """
        import xml.etree.ElementTree as ET
        from pathlib import Path
        import os
        import traceback
        
        # Find the CT file with case-insensitive search
        logging.debug(f"Searching for CT file in directory: '{bms_path}'")
        ct_path = None
        for ct_filename in ["Falcon4_CT.xml", "Falcon4_CT.XML"]:
            potential_path = os.path.join(bms_path, ct_filename)
            logging.debug(f"Checking for CT file: '{potential_path}'")
            if os.path.exists(potential_path):
                ct_path = potential_path
                logging.info(f"Found CT file: '{ct_path}'")
                break
            else:
                logging.debug(f"CT file not found: '{potential_path}'")
        
        if not ct_path:
            logging.error(f"CT file not found in '{bms_path}' (tried both .xml and .XML)")
            return {
                'success': False,
                'error': f"CT file not found in {bms_path}"
            }
            
        # Define field names to collect values for (same as bms_injection_window.py)
        median_fields = [
            "CollisionType", "CollisionRadius", "UpdateRate", "UpdateTolerance", 
            "FineUpdateRange", "FineUpdateForceRange", "FineUpdateMultiplier",
            "DamageSeed", "HitPoints", "MajorRev", "MinRev", 
            "CreatePriority", "ManagementDomain", "Transferable", "Private", 
            "Tangible", "Collidable", "Global", "Persistent", "Id"
        ]
        
        # Dictionary to store values by field
        field_values = {field: [] for field in median_fields}
        
        try:
            # 2. CT File Processing - Load and parse the CT file
            logging.info(f"Loading CT file: {ct_path}")
            tree = ET.parse(ct_path)
            root = tree.getroot()
            
            # Verify we have CT entries with the target type
            matching_ct_entries = 0
            
            # Process all CT entries
            for ct_elem in root.findall('.//CT'):
                try:
                    # Check if this is an objective CT (Domain=3, Class=4, EntityType=3)
                    domain_elem = ct_elem.find("Domain")
                    class_elem = ct_elem.find("Class")
                    entity_type_elem = ct_elem.find("EntityType")
                    type_elem = ct_elem.find("Type")
                    
                    if (domain_elem is not None and domain_elem.text == "3" and
                        class_elem is not None and class_elem.text == "4" and
                        entity_type_elem is not None and entity_type_elem.text == "3" and
                        type_elem is not None and type_elem.text):
                        
                        # Get the type number (1-31)
                        ct_type = int(type_elem.text)
                        
                        # Check if this matches our target type
                        if ct_type == type_key:
                            matching_ct_entries += 1
                            
                            # Extract values for all our fields of interest
                            for field in median_fields:
                                field_elem = ct_elem.find(field)
                                if field_elem is not None and field_elem.text:
                                    try:
                                        # Convert to the appropriate type (float or int)
                                        field_text = field_elem.text.strip()
                                        if "." in field_text:
                                            value = float(field_text)
                                        else:
                                            value = int(field_text)
                                        field_values[field].append(value)
                                    except (ValueError, TypeError):
                                        # Keep as string if conversion fails
                                        field_values[field].append(field_elem.text)
                                        
                except Exception as e:
                    # Log the error but continue processing other entries
                    logging.error(f"Error processing CT entry: {str(e)}")
            
            # 3. Field Value Calculation - Calculate median values for each field
            calculated_values = {}
            
            for field in median_fields:
                values = field_values[field]
                
                if values and len(values) > 0:
                    # We found values for this field in CT entries
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
                            # If we can't determine the most common, use default
                            calculated_values[field] = "0"
                else:
                    # No values found for this field in any CT entries
                    # Use default values based on field type
                    if field == "Id":
                        calculated_values[field] = "60395"  # Common ID value
                    elif field == "FineUpdateMultiplier":
                        calculated_values[field] = "1.0"
                    elif field in ["MajorRev", "MinRev"]:
                        calculated_values[field] = "17" if field == "MajorRev" else "26"
                    elif field in ["CreatePriority", "ManagementDomain", "Transferable"]:
                        calculated_values[field] = "1" if field == "CreatePriority" else "2" if field == "ManagementDomain" else "1"
                    else:
                        calculated_values[field] = "0"
            
            # Count fields that would be updated
            field_count = len([field for field in calculated_values.keys() if field in self.ct_field_vars])
            
            # Return result based on success
            if matching_ct_entries == 0:
                # No matching CT entries found
                logging.warning(f"No CT entries of type {type_key} ({type_name}) were found")
                return {
                    'success': False,
                    'ct_count': 0,
                    'field_count': 0,
                    'calculated_values': {}
                }
            else:
                # Successfully calculated values
                logging.info(f"Successfully calculated median values from {matching_ct_entries} existing CT entries, updating {field_count} fields")
                return {
                    'success': True,
                    'ct_count': matching_ct_entries,
                    'field_count': field_count,
                    'calculated_values': calculated_values
                }
                
        except Exception as e:
            # Log the error
            error_msg = f"Error calculating CT median values: {e}"
            logging.error(f"ERROR: {error_msg}")
            traceback.print_exc()
            return {
                'success': False,
                'error': error_msg,
                'ct_count': 0,
                'field_count': 0,
                'calculated_values': {}
            }
    
    def _update_ct_gui_fields_with_values(self, calculated_values):
        """
        Update the CT GUI field variables with the calculated values.
        
        Args:
            calculated_values: Dictionary of field names to calculated values
        """
        updated_fields = set()
        field_count = 0
        
        # Make sure we have the CT field variables before trying to update them
        if not hasattr(self, 'ct_field_vars') or not self.ct_field_vars:
            logging.warning("No CT field variables available to update")
            return 0
            
        for field_name, string_var in self.ct_field_vars.items():
            if field_name in calculated_values and field_name not in updated_fields:
                value = calculated_values[field_name]
                # Update the string variable
                string_var.set(str(value))
                
                # Count updated fields and mark as updated
                field_count += 1
                updated_fields.add(field_name)
                logging.debug(f"Updated CT field {field_name} = {value}")
        
        logging.info(f"Updated {field_count} CT GUI fields with calculated values")
        return field_count
    
    def _init_ct_interface(self):
        """Initialize the interface for class table data.
        
        Creates all necessary UI elements for selecting and editing Class Table data.
        """
        # Load Class Table types using a better naming approach
        self.ct_types = self._load_ct_types()
        
        # Create the CT type selection section
        ct_type_frame = Ctk.CTkFrame(self.ct_frame, fg_color="#E0E8F0")
        ct_type_frame.pack(fill=tk.X, padx=10, pady=10)
        
        # Title for CT type section
        ct_type_title = Ctk.CTkLabel(
            ct_type_frame,
            text="Class Table Configuration",
            font=("Arial", 14, "bold"),
            text_color="#000033",
            fg_color="transparent"
        )
        ct_type_title.pack(anchor="w", padx=10, pady=(10, 5))
        
        # CT type selection container
        type_select_frame = Ctk.CTkFrame(ct_type_frame, fg_color="#E0E8F0")
        type_select_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # CT type label
        type_label = Ctk.CTkLabel(
            type_select_frame,
            text="Class Table Type:",
            width=120,
            anchor="w",
            text_color="#2E2E3A",
            font=("Arial", 12)
        )
        type_label.pack(side=tk.LEFT, padx=(8, 0), pady=8)
        
        # CT type dropdown
        self.ct_type_var = tk.StringVar(value=next(iter(self.ct_types.values()), "1: Airbase") if self.ct_types else "1: Airbase")
        self.ct_type_dropdown = Ctk.CTkComboBox(
            type_select_frame,
            values=list(self.ct_types.values()),
            variable=self.ct_type_var,
            state="readonly",
            width=250,
            fg_color="#FFFFFF",
            text_color="#000000",
            button_color="#A1B9D0",
            button_hover_color="#7A92A9",
            border_width=1,
            border_color="#B3C8DD",
            dropdown_fg_color="#FFFFFF",
            font=("Arial", 11),
            command=self._load_ct_fields
        )
        self.ct_type_dropdown.pack(side=tk.LEFT, padx=8, pady=8)
        
        # Create fields frame for the CT properties
        self.ct_fields_frame = Ctk.CTkFrame(self.ct_frame, fg_color="#E0E8F0", border_width=1, border_color="#B3C8DD")
        self.ct_fields_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Add indicator showing data source
        self.data_source_label = Ctk.CTkLabel(
            self.ct_frame,
            text="Data Source: ct_templates.json",
            font=("Arial", 10),
            text_color="#555555",
            fg_color="transparent"
        )
        self.data_source_label.pack(anchor="se", padx=10, pady=(0, 5))
        
        # Buttons frame for save and default options
        buttons_frame = Ctk.CTkFrame(self.ct_frame, fg_color="#E0E8F0")
        buttons_frame.pack(fill=tk.X, padx=10, pady=10)
        
        # Save button for CT data
        self.save_ct_button = Ctk.CTkButton(
            buttons_frame,
            text="Save Template",
            command=self._save_ct_template,
            fg_color="#A1B9D0",
            hover_color="#7A92A9",
            text_color="#000000",
            height=35,
            width=150,
            corner_radius=8,
            border_width=1,
            border_color="#8AA2BC",
            font=("Arial", 12)
        )
        self.save_ct_button.pack(side=tk.LEFT, padx=8, pady=8)
        
        # Default button for CT data
        self.default_ct_button = Ctk.CTkButton(
            buttons_frame,
            text="Reset to Default",
            command=self._reset_ct_fields,
            fg_color="#A1B9D0",
            hover_color="#7A92A9",
            text_color="#000000",
            height=35,
            width=150,
            corner_radius=8,
            border_width=1,
            border_color="#8AA2BC",
            font=("Arial", 12)
        )
        self.default_ct_button.pack(side=tk.LEFT, padx=8, pady=8)
        
        # Load the fields for initially selected CT type (same as objective interface)
        if self.ct_type_var.get():
            self._load_ct_fields(self.ct_type_var.get())
    
    def _init_cache_tab(self):
        """Initialize the Cache tab content."""
        # Get the scrollable frame content area
        content_frame = self._get_scrollable_content(self.cache_tab)
        
        # Create header section with warning
        header_frame = Ctk.CTkFrame(content_frame, fg_color="#E0E8F0", border_width=1, border_color="#B3C8DD")
        header_frame.pack(fill=tk.X, padx=10, pady=10)
        
        # Section title
        header_label = Ctk.CTkLabel(
            header_frame,
            text="Cache Management",
            font=("Arial", 16, "bold"),
            text_color="#000033",
            fg_color="transparent"
        )
        header_label.pack(anchor="w", padx=12, pady=(12, 6))
        
        # Warning text
        warning_label = Ctk.CTkLabel(
            header_frame,
            text="⚠️ Warning: These operations will modify or delete cached data.\nMake sure to backup important configurations before proceeding.",
            font=("Arial", 11),
            text_color="#CC3300",
            fg_color="transparent",
            justify="left"
        )
        warning_label.pack(anchor="w", padx=12, pady=(0, 12))
        
        # Create data recalculation section
        data_section_frame = Ctk.CTkFrame(content_frame, fg_color="#E0E8F0", border_width=1, border_color="#B3C8DD")
        data_section_frame.pack(fill=tk.X, padx=10, pady=10)
        
        data_section_label = Ctk.CTkLabel(
            data_section_frame,
            text="Data Recalculation",
            font=("Arial", 14, "bold"),
            text_color="#000033",
            fg_color="transparent"
        )
        data_section_label.pack(anchor="w", padx=12, pady=(12, 6))
        
        # Recalculate All Data button
        recalc_all_frame = Ctk.CTkFrame(data_section_frame, fg_color="#E0E8F0")
        recalc_all_frame.pack(fill=tk.X, padx=10, pady=5)
        
        self.recalc_all_button = Ctk.CTkButton(
            recalc_all_frame,
            text="Recalculate Data",
            command=self._recalculate_all_data,
            fg_color="#A1B9D0",
            hover_color="#7A92A9",
            text_color="#000000",
            height=35,
            width=180,
            corner_radius=8,
            border_width=1,
            border_color="#8AA2BC",
            font=("Arial", 12)
        )
        self.recalc_all_button.pack(side=tk.LEFT, padx=8, pady=8)
        
        recalc_all_desc = Ctk.CTkLabel(
            recalc_all_frame,
            text="Recalculate all cache data (objectives, templates, class tables)",
            font=("Arial", 11),
            text_color="#2E2E3A",
            fg_color="transparent"
        )
        recalc_all_desc.pack(side=tk.LEFT, padx=8, pady=8)
        
        # Recalculate Objects Cache button
        recalc_obj_frame = Ctk.CTkFrame(data_section_frame, fg_color="#E0E8F0")
        recalc_obj_frame.pack(fill=tk.X, padx=10, pady=5)
        
        self.recalc_obj_button = Ctk.CTkButton(
            recalc_obj_frame,
            text="Recalculate Objects Cache",
            command=self._recalculate_objects_cache,
            fg_color="#A1B9D0",
            hover_color="#7A92A9",
            text_color="#000000",
            height=35,
            width=180,
            corner_radius=8,
            border_width=1,
            border_color="#8AA2BC",
            font=("Arial", 12)
        )
        self.recalc_obj_button.pack(side=tk.LEFT, padx=8, pady=8)
        
        recalc_obj_desc = Ctk.CTkLabel(
            recalc_obj_frame,
            text="Recalculate objective templates from BMS data",
            font=("Arial", 11),
            text_color="#2E2E3A",
            fg_color="transparent"
        )
        recalc_obj_desc.pack(side=tk.LEFT, padx=8, pady=8)
        
        # Recalculate Class Tables Cache button
        recalc_ct_frame = Ctk.CTkFrame(data_section_frame, fg_color="#E0E8F0")
        recalc_ct_frame.pack(fill=tk.X, padx=10, pady=5)
        
        self.recalc_ct_button = Ctk.CTkButton(
            recalc_ct_frame,
            text="Recalculate Class Tables Cache",
            command=self._recalculate_ct_cache,
            fg_color="#A1B9D0",
            hover_color="#7A92A9",
            text_color="#000000",
            height=35,
            width=180,
            corner_radius=8,
            border_width=1,
            border_color="#8AA2BC",
            font=("Arial", 12)
        )
        self.recalc_ct_button.pack(side=tk.LEFT, padx=8, pady=8)
        
        recalc_ct_desc = Ctk.CTkLabel(
            recalc_ct_frame,
            text="Recalculate class table templates from BMS data",
            font=("Arial", 11),
            text_color="#2E2E3A",
            fg_color="transparent"
        )
        recalc_ct_desc.pack(side=tk.LEFT, padx=8, pady=8)
        
        # Create maintenance section
        maintenance_section_frame = Ctk.CTkFrame(content_frame, fg_color="#E0E8F0", border_width=1, border_color="#B3C8DD")
        maintenance_section_frame.pack(fill=tk.X, padx=10, pady=10)
        
        maintenance_section_label = Ctk.CTkLabel(
            maintenance_section_frame,
            text="Data Maintenance",
            font=("Arial", 14, "bold"),
            text_color="#000033",
            fg_color="transparent"
        )
        maintenance_section_label.pack(anchor="w", padx=12, pady=(12, 6))
        
        # Reset Statistics button
        reset_stats_frame = Ctk.CTkFrame(maintenance_section_frame, fg_color="#E0E8F0")
        reset_stats_frame.pack(fill=tk.X, padx=10, pady=5)
        
        self.reset_stats_button = Ctk.CTkButton(
            reset_stats_frame,
            text="Reset Statistics",
            command=self._reset_statistics,
            fg_color="#A1B9D0",
            hover_color="#7A92A9",
            text_color="#000000",
            height=35,
            width=180,
            corner_radius=8,
            border_width=1,
            border_color="#8AA2BC",
            font=("Arial", 12)
        )
        self.reset_stats_button.pack(side=tk.LEFT, padx=8, pady=8)
        
        reset_stats_desc = Ctk.CTkLabel(
            reset_stats_frame,
            text="Reset feature generation statistics to defaults",
            font=("Arial", 11),
            text_color="#2E2E3A",
            fg_color="transparent"
        )
        reset_stats_desc.pack(side=tk.LEFT, padx=8, pady=8)
        
        # Delete Configuration button
        delete_config_frame = Ctk.CTkFrame(maintenance_section_frame, fg_color="#E0E8F0")
        delete_config_frame.pack(fill=tk.X, padx=10, pady=5)
        
        self.delete_config_button = Ctk.CTkButton(
            delete_config_frame,
            text="Delete Saved Configuration",
            command=self._delete_configuration,
            fg_color="#D08A8A",  # Different color for destructive action
            hover_color="#B87A7A",
            text_color="#000000",
            height=35,
            width=180,
            corner_radius=8,
            border_width=1,
            border_color="#C88888",
            font=("Arial", 12)
        )
        self.delete_config_button.pack(side=tk.LEFT, padx=8, pady=8)
        
        delete_config_desc = Ctk.CTkLabel(
            delete_config_frame,
            text="Delete saved application configuration (config.json)",
            font=("Arial", 11),
            text_color="#2E2E3A",
            fg_color="transparent"
        )
        delete_config_desc.pack(side=tk.LEFT, padx=8, pady=8)
    
    def _load_ct_types(self):
        """Load Class Table types with meaningful objective type names.
        
        Returns:
            dict: Dictionary of CT types with ID as key and "ID: Name" as value
        """
        ct_types = {}
        
        try:
            # Load from ct_templates.json using json_path_handler
            from utils.json_path_handler import load_json, JsonFiles
            ct_templates = load_json(JsonFiles.CT_TEMPLATES, default={})
            
            if ct_templates:
                for ct_id in ct_templates.keys():
                    # Use the same objective type names as used in objective interface
                    type_name = self._get_type_name(int(ct_id))
                    ct_types[ct_id] = f"{ct_id}: {type_name}"
                
                logging.info(f"Loaded {len(ct_types)} class table types from ct_templates.json")
            
            # If no types found, use default fallback matching objective types
            if not ct_types:
                fallback_types = {
                    "1": "1: Airbase",
                    "2": "2: Airstrip",
                    "3": "3: Army Base",
                    "4": "4: Beach",
                    "5": "5: Border",
                    "6": "6: Bridge",
                    "7": "7: Chemical",
                    "8": "8: City",
                    "9": "9: Command & Control",
                    "10": "10: Depot",
                    "11": "11: Factory",
                    "12": "12: Ford",
                    "13": "13: Fortification",
                    "14": "14: Scenery",
                    "15": "15: Intersect",
                    "16": "16: Nav Beacon",
                    "17": "17: Nuclear",
                    "18": "18: Pass",
                    "19": "19: Port",
                    "20": "20: Power Plant",
                    "21": "21: Radar",
                    "22": "22: Radio Tower",
                    "23": "23: Rail Terminal",
                    "24": "24: Railroad",
                    "25": "25: Refinery",
                    "26": "26: Railroad",
                    "27": "27: Seal",
                    "28": "28: Town",
                    "29": "29: Village",
                    "30": "30: HARTS",
                    "31": "31: SAM Site"
                }
                ct_types = fallback_types
                logging.info("Using fallback class table types list")
                
        except Exception as e:
            logging.error(f"Error loading class table types: {str(e)}")
            # Provide minimal fallback if everything fails
            ct_types = {"1": "1: Airbase"}
        
        return ct_types
    
# Custom logging methods removed - now using standard logging.info(), logging.error() etc. directly
    
    def _get_scrollable_content(self, scrollable_frame):
        """Get the content frame from a scrollable frame."""
        # Find the canvas within the scrollable frame
        for child in scrollable_frame.winfo_children():
            if isinstance(child, tk.Canvas):
                canvas = child
                break
        else:
            # If we didn't find a canvas, return the scrollable frame itself
            return scrollable_frame
        
        # Find the inner frame within the canvas
        for item_id in canvas.find_all():
            if canvas.type(item_id) == "window":
                # Get the window widget (which is our inner frame)
                inner_frame = canvas.itemcget(item_id, "window")
                if inner_frame:
                    return canvas.nametowidget(inner_frame)
        
        # If we didn't find an inner frame, return the canvas
        return canvas
    
    def _save_preset(self):
        """Save current configuration as a preset by calling MainGui's save_config_file method."""
        try:
            # Check if we have a parent that has the save_config_file method
            if hasattr(self.parent, 'save_config_file'):
                self.parent.save_config_file()
            else:
                logging.error("Cannot save preset: Parent window does not have save_config_file method")
                messagebox.showerror("Error", "Cannot save preset: Parent window does not have save_config_file method")
        except Exception as e:
            logging.error(f"Error saving preset: {str(e)}")
    
    def _load_preset(self):
        """Load configuration preset by calling MainGui's load_config method."""
        try:
            # Check if we have a parent that has the load_config method
            if hasattr(self.parent, 'load_config'):
                self.parent.load_config()
                
                # Update UI elements if needed
                self._update_ui_from_parent()
            else:
                logging.error("Cannot load preset: Parent window does not have load_config method")
                messagebox.showerror("Error", "Cannot load preset: Parent window does not have load_config method")
        except Exception as e:
            logging.error(f"Error loading preset: {str(e)}")
    
    def _update_ui_from_parent(self):
        """Update UI elements based on parent's shared_data."""
        try:
            # Check if parent has shared_data
            if hasattr(self.parent, 'shared_data'):
                # Update Auto-Start checkbox if parent has Startup in shared_data
                if "Startup" in self.parent.shared_data:
                    startup_value = self.parent.shared_data["Startup"].get()
                    if startup_value and startup_value.lower() == 'true':
                        self.auto_start_var.set(True)
                    else:
                        self.auto_start_var.set(False)
                
                # Update BMS path if parent has CTpath in shared_data
                if "CTpath" in self.parent.shared_data:
                    ct_path = self.parent.shared_data["CTpath"].get()
                    if ct_path:
                        self.bms_path_var.set(ct_path)
                
                # Update Backup KTO path if parent has backup_CTpath in shared_data
                if "backup_CTpath" in self.parent.shared_data:
                    backup_path = self.parent.shared_data["backup_CTpath"].get()
                    if backup_path:
                        self.backup_path_var.set(backup_path)
        except Exception as e:
            logging.error(f"Error updating UI from parent: {str(e)}")
    
    def _toggle_auto_start(self):
        """Toggle auto-start setting.
        
        Controls whether the application starts automatically when the system boots.
        Connected to shared_data["Startup"] in MainGui.
        """
        # Update auto-start setting
        try:
            # Update parent's Auto_Load variable to match our checkbox state
            if hasattr(self.parent, 'Auto_Load'):
                self.parent.Auto_Load.set(self.auto_start_var.get())
                
            # Forward to parent if it has a method for this
            if hasattr(self.parent, 'startup_selection_checkbox'):
                self.parent.startup_selection_checkbox()
            
            # Provide feedback confirmation
            status = "enabled" if self.auto_start_var.get() else "disabled"
            logging.info(f"Auto-start {status}")
            
        except Exception as e:
            logging.error(f"Error toggling auto-start: {str(e)}")
    
    def _configure_logger(self, log_level=None, log_handlers=None):
        """Configure the application logger with the specified settings.
        
        This method sets up the root logger with the specified log level and handlers.
        
        Args:
            log_level: The logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
            log_handlers: List of handlers to use ('console', 'file', or both)
        """
        try:
            # Get logging level from argument or UI selection
            level = log_level or self.log_level_var.get()
            handlers = log_handlers or []
            
            # Determine which handlers to use based on log_type_var
            if not handlers:
                log_type = self.log_type_var.get()
                if log_type == "Console Only":
                    handlers = ['console']
                elif log_type == "File Only":
                    handlers = ['file']
                elif log_type == "Console and File":
                    handlers = ['console', 'file']
            
            # Convert level string to numeric value
            numeric_level = getattr(logging, level)
            
            # Configure the root logger
            root_logger = logging.getLogger()
            root_logger.setLevel(numeric_level)
            
            # Remove all existing handlers
            for handler in root_logger.handlers[:]:
                root_logger.removeHandler(handler)
            
            # Create formatter
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            
            # Add handlers as requested
            if 'console' in handlers:
                console_handler = logging.StreamHandler()
                console_handler.setLevel(numeric_level)
                console_handler.setFormatter(formatter)
                root_logger.addHandler(console_handler)
            
            if 'file' in handlers:
                # Ensure logs directory exists
                logs_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "logs")
                os.makedirs(logs_dir, exist_ok=True)
                
                # Create file handler
                log_file = os.path.join(logs_dir, "app.log")
                file_handler = logging.FileHandler(log_file)
                file_handler.setLevel(numeric_level)
                file_handler.setFormatter(formatter)
                root_logger.addHandler(file_handler)
            
            # Log confirmation
            logging.info(f"Logger configured with level: {level}, handlers: {', '.join(handlers)}")
            
            # Update parent's logging configuration if method exists
            if hasattr(self.parent, 'update_logging_config'):
                self.parent.update_logging_config(level, handlers)
                
        except Exception as e:
            # Use print as a fallback in case logging is broken
            logging.error(f"Error configuring logger: {str(e)}")
    
    def _open_console_window(self):
        """Open console window by calling parent's open_console_window method."""
        try:
            # Check if we have a parent that has the open_console_window method
            if hasattr(self.parent, 'open_console_window'):
                self.parent.open_console_window()
            else:
                logging.error("Cannot open console window: Parent window does not have open_console_window method")
                messagebox.showerror("Error", "Cannot open console window: Parent window does not have open_console_window method")
        except Exception as e:
            logging.error(f"Error opening console window: {str(e)}")
    
    def _save_and_destroy_task(self):
        """Saves checkbox states and then destroys the window.
        
        This task is scheduled to run when the event loop is idle to improve
        perceived responsiveness of the window closing.
        """
        task_start_time = time.perf_counter()
        elapsed_task_start = task_start_time - self._creation_time
        logging.info(f"[{elapsed_task_start:.4f}s] Deferred task: _save_and_destroy_task started.")
        
        try:
            save_start_time = time.perf_counter()
            elapsed_before_save = save_start_time - self._creation_time
            logging.info(f"[{elapsed_before_save:.4f}s] Deferred task: Calling _save_checkbox_states().")
            
            self._save_checkbox_states() # Now this runs deferred
            
            save_end_time = time.perf_counter()
            elapsed_after_save = save_end_time - self._creation_time
            duration_save = save_end_time - save_start_time
            logging.info(f"[{elapsed_after_save:.4f}s] Deferred task: _save_checkbox_states() completed in {duration_save:.4f}s.")
            
        except Exception as e:
            save_error_time = time.perf_counter()
            elapsed_save_error = save_error_time - self._creation_time
            logging.error(f"[{elapsed_save_error:.4f}s] Error during deferred saving of checkbox states: {str(e)}")
        finally:
            # Ensure destroy is called even if saving fails or an error occurs during saving
            if self.winfo_exists():
                destroy_start_time = time.perf_counter()
                elapsed_before_destroy = destroy_start_time - self._creation_time
                logging.info(f"[{elapsed_before_destroy:.4f}s] Deferred task: Calling self.destroy().")
                try:
                    self.destroy()
                    destroy_end_time = time.perf_counter()
                    elapsed_after_destroy = destroy_end_time - self._creation_time
                    duration_destroy = destroy_end_time - destroy_start_time
                    logging.info(f"[{elapsed_after_destroy:.4f}s] Deferred task: Window destroyed successfully in {duration_destroy:.4f}s.")
                except Exception as e_destroy:
                    destroy_error_time = time.perf_counter()
                    elapsed_destroy_error = destroy_error_time - self._creation_time
                    logging.error(f"[{elapsed_destroy_error:.4f}s] Error during deferred window destruction: {str(e_destroy)}")
            else:
                no_destroy_time = time.perf_counter()
                elapsed_no_destroy = no_destroy_time - self._creation_time
                logging.info(f"[{elapsed_no_destroy:.4f}s] Deferred task: Window no longer exists, skipping destroy.")

    def _on_close(self):
        """Schedules the window to save settings and then close.
        
        This method is called when the user closes the window. It immediately
        schedules the saving of settings and window destruction to happen 
        when the event loop is idle, making the window appear to close instantly.
        """
        try:
            # Log the action immediately
            elapsed_on_close = time.perf_counter() - self._creation_time
            logging.info(f"[{elapsed_on_close:.4f}s] Settings window close requested. Scheduling save and destroy task.")
            
            # Schedule the save and destroy operation to run when idle
            self.after_idle(self._save_and_destroy_task)
        except Exception as e:
            logging.error(f"Error in _on_close while scheduling save/destroy task: {str(e)}")
            # Fallback: If scheduling itself fails, try to destroy immediately.
            # This might hang if the original problem was in destroy(), but it's a last resort.
            if self.winfo_exists():
                try:
                    logging.info("Fallback: Attempting immediate destroy due to error in _on_close scheduling.")
                    self.destroy()
                except Exception as e_destroy:
                    logging.error(f"Error during fallback immediate destroy: {str(e_destroy)}")
    
    def _save_checkbox_states(self):
        """Save the states of all checkboxes in the settings window.
        
        This ensures checkbox preferences are preserved between sessions.
        """
        try:
            # Make sure the parent has shared_data
            if hasattr(self.parent, 'shared_data'):
                # Save backup BMS files checkbox state
                backup_bms_value = "1" if self.backup_bms_var.get() else "0"
                if 'backup_bms_files' in self.parent.shared_data:
                    self.parent.shared_data['backup_bms_files'].set(backup_bms_value)
                else:
                    self.parent.shared_data['backup_bms_files'] = tk.StringVar(value=backup_bms_value)
                
                # Save backup features checkbox state
                backup_features_value = "1" if self.backup_features_var.get() else "0"
                if 'backup_features_files' in self.parent.shared_data:
                    self.parent.shared_data['backup_features_files'].set(backup_features_value)
                else:
                    self.parent.shared_data['backup_features_files'] = tk.StringVar(value=backup_features_value)
                
                # Save auto-start checkbox state if it exists
                if hasattr(self, 'auto_start_var'):
                    auto_start_value = "1" if self.auto_start_var.get() else "0"
                    if 'auto_start' in self.parent.shared_data:
                        self.parent.shared_data['auto_start'].set(auto_start_value)
                    else:
                        self.parent.shared_data['auto_start'] = tk.StringVar(value=auto_start_value)
                
                logging.info("Saved checkbox states to shared data")
        except Exception as e:
            logging.error(f"Error saving checkbox states: {str(e)}")
    
    def _apply_logging_settings(self):
        """Apply the logging settings from the UI controls.
        
        This method reads the current logging configuration from the UI controls
        and applies them using the _configure_logger method.
        """
        # Get logging settings from UI controls
        log_level_str = self.log_level_var.get()
        log_method_ui_str = self.log_type_var.get() # This is the string from the UI, e.g., "Console Only"

        # Translate UI string to handlers list and a storable simple string (like in config.json)
        handlers = []
        storable_log_method = "Console" # Default storable value
        if log_method_ui_str == "Console Only":
            handlers = ['console']
            storable_log_method = "Console"
        elif log_method_ui_str == "File Only":
            handlers = ['file']
            storable_log_method = "File"
        elif log_method_ui_str == "Console and File":
            handlers = ['console', 'file']
            storable_log_method = "Both"
        elif log_method_ui_str == "None":
            handlers = [] # No handlers
            storable_log_method = "None"
        
        # Apply the settings using the parent's update_logging_config method
        if hasattr(self.parent, 'update_logging_config'):
            self.parent.update_logging_config(level=log_level_str, handlers=handlers)
            logging.info(f"Applied logging settings: Level={log_level_str}, Method UI='{log_method_ui_str}' (Handlers: {handlers})")
        else:
            logging.error("Parent does not have update_logging_config method.")
            messagebox.showerror("Error", "Failed to apply logging settings: Parent context error.")
            return

        # Update shared_data in the parent (MainGui) with the storable simple string
        if hasattr(self.parent, 'shared_data'):
            if self.parent.shared_data.get("log_level"):
                self.parent.shared_data["log_level"].set(log_level_str)
            else: 
                self.parent.shared_data["log_level"] = tk.StringVar(value=log_level_str)
                
            if self.parent.shared_data.get("logging_method"):
                self.parent.shared_data["logging_method"].set(storable_log_method) # Save the simple form
            else: 
                self.parent.shared_data["logging_method"] = tk.StringVar(value=storable_log_method)
            logging.info("Updated shared_data with new logging settings.")
        else:
            logging.error("Parent does not have shared_data attribute.")

        # Create a simple message for the confirmation dialog
        message = "Logging settings have been applied.\n\n"
        message += f"Level: {log_level_str}\n"
        message += f"Output: {log_method_ui_str}\n\n"
        message += "The new settings are now active."
        
        # Show a confirmation message to the user
        messagebox.showinfo("Logging Settings Applied", message)
    
    def _recalculate_all_data(self):
        """Recalculate all cache data including objectives, templates, and class tables."""
        # Show confirmation dialog
        confirm_result = messagebox.askyesno(
            "Confirm Recalculation",
            "This will recalculate ALL major cache data:\n\n"
            "• General objectives data (objective_cache.json)\n"
            "• Objective templates (objective_templates.json)\n" 
            "• Class table templates (ct_templates.json)\n"
            "This operation may take several minutes.\n\n"
            "Are you sure you want to continue?",
            icon='warning'
        )
        
        if not confirm_result:
            return
            
        try:
            from processing_window import run_with_processing
            import os
            
            def recalculation_task(processing_window):
                """Task to recalculate all data with proper error handling."""
                try:
                    # Step 1: Remove existing files
                    from utils.json_path_handler import get_json_path, JsonFiles
                    files_to_remove = [
                        JsonFiles.OBJECTIVE_CACHE,
                        JsonFiles.OBJECTIVE_TEMPLATES,
                        JsonFiles.CT_TEMPLATES,
                        JsonFiles.SAVED_OBJECTIVE_SETTINGS
                    ]
                    
                    for file_name in files_to_remove:
                        file_path = get_json_path(file_name)
                        if os.path.exists(file_path):
                            os.remove(file_path)
                            logging.info(f"Removed {file_name}")
                    
                    # Step 2: Resolve BMS root and create injector
                    from pathlib import Path
                    from bms_injector import BmsInjector
                    from utils.json_path_handler import save_json, JsonFiles

                    def _resolve_bms_root_path_local(input_path):
                        try:
                            p = Path(input_path) if input_path else Path.cwd()
                            if p.is_file():
                                p = p.parent
                            # Try a few ancestors to locate Data/TerrData/Falcon4_CT.xml
                            candidates = [p, p.parent, p.parent.parent, p.parent.parent.parent]
                            for base in candidates:
                                ct_candidate = base / "Data" / "TerrData" / "Falcon4_CT.xml"
                                if ct_candidate.exists():
                                    return str(base)
                            return str(p)
                        except Exception:
                            return str(Path.cwd())

                    bms_root_path = _resolve_bms_root_path_local(self.bms_path)

                    injector = BmsInjector(
                        bms_path=bms_root_path,
                        auto_create_templates=False  # We'll create them manually
                    )

                    # Step 3: Generate templates directly (single authority)
                    objective_templates = injector._create_default_templates()
                    ct_templates = injector._create_default_ct_templates()

                    # Persist templates
                    save_json(JsonFiles.OBJECTIVE_TEMPLATES, objective_templates)
                    save_json(JsonFiles.CT_TEMPLATES, ct_templates)

                    # Step 4: Rebuild the objective cache synchronously
                    from components.objective_cache import cache as objective_cache

                    bms_version = injector._get_bms_version()
                    objective_cache.set_bms_version(bms_version)

                    ct_data = injector._analyze_ct_file()
                    if ct_data:
                        objective_cache.set_ct_data(ct_data)

                    obj_data = injector._analyze_objectives()
                    if obj_data:
                        objective_cache.set_objective_data(obj_data)

                    # Ensure cache uses the freshly generated templates
                    objective_cache.set_objective_templates(objective_templates)

                    # Save cache synchronously
                    objective_cache.save_cache()
                    
                    logging.info("Successfully recalculated all cache data")
                    return True
                    
                except Exception as e:
                    logging.error(f"Error during data recalculation: {str(e)}")
                    raise e
            
            # Run the task with processing window
            result = run_with_processing(
                parent=self,
                task_function=recalculation_task,
                title="Recalculating Data",
                message="Recalculating all cache data...\nThis may take several minutes.",
                width=400,
                height=150
            )
            
            if result:
                messagebox.showinfo(
                    "Recalculation Complete",
                    "All cache data has been successfully recalculated.\n\n"
                    "The following files have been regenerated:\n"
                    "• objective_cache.json\n"
                    "• objective_templates.json\n"
                    "• ct_templates.json\n"
                )
            else:
                messagebox.showerror("Error", "Failed to recalculate cache data. Check logs for details.")
                
        except Exception as e:
            logging.error(f"Error in recalculate all data: {str(e)}")
            messagebox.showerror("Error", f"Failed to recalculate data: {str(e)}")
    
    def _recalculate_objects_cache(self):
        """Recalculate objective templates from BMS data."""
        # Show confirmation dialog
        confirm_result = messagebox.askyesno(
            "Confirm Objective Templates Recalculation",
            "This will recalculate objective templates from BMS data:\n\n"
            "• objective_templates.json will be regenerated\n\n"
            "This operation may take a few minutes.\n\n"
            "Are you sure you want to continue?",
            icon='warning'
        )
        
        if not confirm_result:
            return
            
        try:
            from processing_window import run_with_processing
            import os
            
            def objectives_recalculation_task(processing_window):
                """Task to recalculate objective templates."""
                try:
                    # Remove existing objective templates file
                    from utils.json_path_handler import get_json_path, JsonFiles
                    obj_templates_path = get_json_path(JsonFiles.OBJECTIVE_TEMPLATES)
                    if os.path.exists(obj_templates_path):
                        os.remove(obj_templates_path)
                        logging.info("Removed existing objective_templates.json")
                    
                    # Create BmsInjector and generate objective templates directly
                    from bms_injector import BmsInjector
                    
                    # Create injector instance
                    injector = BmsInjector(
                        bms_path=self.bms_path,
                        auto_create_templates=False  # We'll create them manually
                    )
                    
                    # Generate objective templates directly
                    objective_templates = injector._create_default_templates()
                    
                    # Save the templates
                    from utils.json_path_handler import save_json, JsonFiles
                    save_json(JsonFiles.OBJECTIVE_TEMPLATES, objective_templates)
                    
                    logging.info("Successfully recalculated objective templates")
                    return True
                    
                except Exception as e:
                    logging.error(f"Error during objective templates recalculation: {str(e)}")
                    raise e
            
            # Run the task with processing window
            result = run_with_processing(
                parent=self,
                task_function=objectives_recalculation_task,
                title="Recalculating Objective Templates",
                message="Analyzing BMS data and generating objective templates...",
                width=400,
                height=150
            )
            
            if result:
                messagebox.showinfo(
                    "Recalculation Complete",
                    "Objective templates have been successfully recalculated from BMS data.\n\n"
                    "The objective_templates.json file has been regenerated."
                )
            else:
                messagebox.showerror("Error", "Failed to recalculate objective templates. Check logs for details.")
                
        except Exception as e:
            logging.error(f"Error in recalculate objectives cache: {str(e)}")
            messagebox.showerror("Error", f"Failed to recalculate objective templates: {str(e)}")
    
    def _recalculate_ct_cache(self):
        """Recalculate class table templates from BMS data."""
        # Show confirmation dialog
        confirm_result = messagebox.askyesno(
            "Confirm Class Table Templates Recalculation",
            "This will recalculate class table templates from BMS data:\n\n"
            "• ct_templates.json will be regenerated\n\n"
            "This operation may take a few minutes.\n\n"
            "Are you sure you want to continue?",
            icon='warning'
        )
        
        if not confirm_result:
            return
            
        try:
            from processing_window import run_with_processing
            import os
            
            def ct_recalculation_task(processing_window):
                """Task to recalculate CT templates."""
                try:
                    # Remove existing CT templates file
                    from utils.json_path_handler import get_json_path, JsonFiles
                    ct_templates_path = get_json_path(JsonFiles.CT_TEMPLATES)
                    if os.path.exists(ct_templates_path):
                        os.remove(ct_templates_path)
                        logging.info("Removed existing ct_templates.json")
                    
                    # Create BmsInjector and generate CT templates directly
                    from bms_injector import BmsInjector
                    
                    # Create injector instance
                    injector = BmsInjector(
                        bms_path=self.bms_path,
                        auto_create_templates=False  # We'll create them manually
                    )
                    
                    # Generate CT templates directly
                    ct_templates = injector._create_default_ct_templates()
                    
                    # Save the templates
                    from utils.json_path_handler import save_json, JsonFiles
                    save_json(JsonFiles.CT_TEMPLATES, ct_templates)
                    
                    logging.info("Successfully recalculated CT templates")
                    return True
                    
                except Exception as e:
                    logging.error(f"Error during CT templates recalculation: {str(e)}")
                    raise e
            
            # Run the task with processing window
            result = run_with_processing(
                parent=self,
                task_function=ct_recalculation_task,
                title="Recalculating Class Table Templates",
                message="Analyzing BMS CT file and generating templates...",
                width=400,
                height=150
            )
            
            if result:
                messagebox.showinfo(
                    "Recalculation Complete",
                    "Class table templates have been successfully recalculated from BMS data.\n\n"
                    "The ct_templates.json file has been regenerated."
                )
            else:
                messagebox.showerror("Error", "Failed to recalculate CT templates. Check logs for details.")
                
        except Exception as e:
            logging.error(f"Error in recalculate CT cache: {str(e)}")
            messagebox.showerror("Error", f"Failed to recalculate CT templates: {str(e)}")
    
    def _reset_statistics(self):
        """Reset feature generation statistics to defaults."""
        # Show confirmation dialog
        confirm_result = messagebox.askyesno(
            "Confirm Statistics Reset",
            "This will reset all feature generation statistics to defaults:\n\n"
            "• Total features count will be reset to 0\n"
            "• Total usage count will be reset to 0\n"
            "• Feature type statistics will be cleared\n\n"
            "This action cannot be undone.\n\n"
            "Are you sure you want to continue?",
            icon='warning'
        )
        
        if not confirm_result:
            return
            
        try:
            from utils.json_path_handler import save_json, JsonFiles
            from collections import Counter
            
            # Create default statistics structure
            default_stats = {
                "total_features": 0,
                "total_usage": 0,
                "feature_types": {}
            }
            
            # Save the default statistics
            success = save_json(JsonFiles.FEATURE_STATISTICS, default_stats)
            
            if success:
                logging.info("Successfully reset feature statistics to defaults")
                messagebox.showinfo(
                    "Statistics Reset Complete",
                    "Feature generation statistics have been successfully reset to defaults.\n\n"
                    "All counters have been reset to 0."
                )
            else:
                messagebox.showerror("Error", "Failed to reset statistics. Check logs for details.")
                
        except Exception as e:
            logging.error(f"Error resetting statistics: {str(e)}")
            messagebox.showerror("Error", f"Failed to reset statistics: {str(e)}")
    
    def _delete_configuration(self):
        """Delete saved application configuration (config.json)."""
        # Show strong confirmation dialog
        confirm_result = messagebox.askyesno(
            "⚠️ CONFIRM CONFIGURATION DELETION",
            "This will PERMANENTLY DELETE your saved application configuration:\n\n"
            "• All saved paths and settings will be lost\n"
            "• Application will start with default settings next time\n"
            "• You will need to reconfigure all paths and preferences\n\n"
            "THIS ACTION CANNOT BE UNDONE!\n\n"
            "Are you absolutely sure you want to delete the configuration?",
            icon='error'
        )
        
        if not confirm_result:
            return
            
        # Second confirmation for extra safety
        final_confirm = messagebox.askyesno(
            "FINAL CONFIRMATION",
            "Last chance to cancel!\n\n"
            "This will delete config.json and ALL your saved settings.\n\n"
            "Click YES to delete configuration.\n"
            "Click NO to cancel and keep your settings.",
            icon='error'
        )
        
        if not final_confirm:
            return
            
        try:
            from utils.json_path_handler import get_json_path, JsonFiles
            import os
            
            # Get path to config.json
            config_path = get_json_path(JsonFiles.CONFIG_JSON)
            
            if os.path.exists(config_path):
                os.remove(config_path)
                logging.info("Successfully deleted configuration file")
                messagebox.showinfo(
                    "Configuration Deleted",
                    "Application configuration has been successfully deleted.\n\n"
                    "The application will start with default settings next time it's launched.\n\n"
                    "You may want to restart the application now."
                )
            else:
                messagebox.showwarning(
                    "Configuration Not Found",
                    "No configuration file was found to delete.\n\n"
                    "The application may already be using default settings."
                )
                
        except Exception as e:
            logging.error(f"Error deleting configuration: {str(e)}")
            messagebox.showerror("Error", f"Failed to delete configuration: {str(e)}")


# For testing purposes only
if __name__ == '__main__':
    # Check if the SettingsWindow is a Toplevel window
    if hasattr(tk, 'Toplevel') and issubclass(SettingsWindow, tk.Toplevel):
        # Create a simple mock parent for the Toplevel window
        class MockFrame(tk.Frame):
            def __init__(self, master=None):
                super().__init__(master)
                # Create shared data for settings window
                self.shared_data = {
                    "CTpath": tk.StringVar(value="C:/BMS/User/Config"),
                    "BMS_Database_Path": tk.StringVar(value="C:/BMS/Data"),
                    "backup_CTpath": tk.StringVar(value="C:/BMS/Backup"),
                    "Startup": tk.StringVar(),
                }
            
            def console_log(self, message):
                logging.info(f"[CONSOLE] {message}")
        
        # Create root window
        root = tk.Tk()
        root.title("BMS Building Generator - Settings")
        root.geometry("800x600")
        
        # Create parent frame
        parent_frame = MockFrame(root)
        parent_frame.pack(fill=tk.BOTH, expand=True)
        
        # Create a button to open settings
        def open_settings():
            settings_dialog = SettingsWindow(parent_frame)
            root.wait_window(settings_dialog)
        
        open_button = tk.Button(parent_frame, text="Open Settings", command=open_settings)
        open_button.pack(padx=20, pady=20)
        
        # Open settings dialog automatically for testing
        root.after(100, open_settings)
        
        # Start the main loop
        root.mainloop()
    else:
        logging.error("SettingsWindow is not a Toplevel widget. Unable to run standalone.")
        sys.exit(1)