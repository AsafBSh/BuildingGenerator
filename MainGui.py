from tkinter import ttk, Canvas, Button, PhotoImage, messagebox
import tkinter.filedialog
import tkinter as tk
import customtkinter as Ctk
from PIL import Image

# General libraries
import os
import sys
import json
import gzip
import winreg
import numpy as np
import pandas as pd
from pathlib import Path
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import traceback
import math
import logging
from utils.json_path_handler import load_json, save_json, JsonFiles, get_json_path

# For GlobalAtlas WFS error handling
try:
    import requests
except ImportError:
    requests = None
# Import enhanced settings window
from components.settings_window import SettingsWindow

# functions from Code
import OSMLegend
import Restrictions
from components.internal_console import show_console
import ValuesDictionary
import Load_Geo_File as geo
from MainCode import Load_Db
from Database import GenerateDB
from MainCode import (
    Assign_features_accuratly,
    Save_accurate_features,
    Save_random_features,
    Assign_features_randomly,
)
from MainCode import Show_Selected_Features_2D, Show_Selected_Features_3D


class MainPage(tk.Tk):
    def __init__(self, *args, **kwargs):
        # Initiate variables
        self.ASSETS_PATH = Path(r"Assets")

        tk.Tk.__init__(self, *args, **kwargs)
        # Set Geometry of the page
        self.geometry("1152x720")
        self.configure(bg="#FFFFFF")
        self.resizable(False, False)
        
        # Configure global ttk styles
        style = ttk.Style()
        style.configure("Treeview.Heading", font=('Arial', 10, 'bold'))
        
        # Set up application logging
        self._configure_application_logging()

        # Set Shared data variables
        self.shared_data = {
            "CTpath": tk.StringVar(),
            "BMS_Database_Path": tk.StringVar(),
            "BMS_Databse": np.array([]),
            "Theater": tk.StringVar(),
            "BMS_version": tk.StringVar(),
            "Geopath": tk.StringVar(),
            "GeoData": np.array([]),
            "Calc_GeoData": np.array([]),
            "Geo_AOI_Center": np.array([]),
            "backup_CTpath": tk.StringVar(),
            "EditorSavingPath": tk.StringVar(),
            "Database_Availability": tk.StringVar(),
            "projection_path": tk.StringVar(),
            "projection_string": tk.StringVar(),
            "Startup": tk.StringVar(),
            "log_level": tk.StringVar(),  # Replaces debugger with log level
            "logging_method": tk.StringVar(), # For logging handler (Console, File, Both)
            "BuildingGeneratorVer": tk.StringVar(),
             "MaxGeojsonDraw": tk.IntVar(),# Visualization limits
        }
        self.shared_data["BMS_version"].set("-")
        self.shared_data["Theater"].set("-")
        self.shared_data["CTpath"].set("No CT file selected")
        self.shared_data["projection_path"].set("No Projection file selected")
        self.shared_data["backup_CTpath"].set("No CT file selected")
        self.shared_data["Geopath"].set("No GeoJson file selected")
        self.shared_data["log_level"].set("INFO")  # Default log level
        self.shared_data["logging_method"].set("None") # Default logging_method (disabled as per user specification)
        self.shared_data["MaxGeojsonDraw"].set(256)# Default maximum GeoJSON buildings to render
        
        # Initialize Auto_Load attribute for settings window integration
        self.Auto_Load = tk.BooleanVar(value=False)
        
        # Initialize destruction state tracking
        self._destroying = False
        self._child_windows = set()  # Track child windows

        self.frames = {}
        for F in (DashboardPage, DatabasePage, GeoDataPage, OperationPage, FootPrintsPage):
            page_name = F.__name__
            frame = F(parent=self, controller=self)
            self.frames[page_name] = frame
            # Configure the grid to expand and fill the window
            self.grid_rowconfigure(0, weight=1)
            self.grid_columnconfigure(0, weight=1)
            frame.grid(row=0, column=0, sticky="nsew")

        # Set Name and Icon and version
        self.shared_data["BuildingGeneratorVer"].set("Building Generator v2.2")
        self.title(self.shared_data["BuildingGeneratorVer"].get())
        self.iconbitmap("Assets/icon_128.ico")

        # Select Dash as main front page
        self.show_frame("DashboardPage")
        # Startup check loading
        self.startup_definition()
        
        # Set up window close protocol
        self.protocol("WM_DELETE_WINDOW", self.on_closing)

        # Ensure footprints directory structure exists
        try:
            self._ensure_footprints_dirs()
        except Exception as _e:
            logging.warning(f"Could not ensure footprints directories: {_e}")

    def show_frame(self, page_name):
        # Hide all frames
        for frame in self.frames.values():
            frame.grid_remove()
        # Show the selected frame
        frame = self.frames[page_name]
        frame.grid()
        
    def _configure_application_logging(self):
        """Configure the application-wide logging system with PyInstaller compatibility.
        
        This method sets up proper logging for the entire application with special
        handling for compiled executables to ensure logs are always accessible.
        """
        try:
            # Detect if running as compiled executable
            is_compiled = getattr(sys, 'frozen', False)
            
            # Determine the base directory for the application
            if is_compiled:
                # For compiled executables, use the directory containing the executable
                if hasattr(sys, '_MEIPASS'):
                    # PyInstaller temp directory
                    base_dir = os.path.dirname(sys.executable)
                else:
                    base_dir = os.path.dirname(sys.executable)
            else:
                # For normal Python scripts
                base_dir = os.path.dirname(os.path.abspath(__file__))
            
            # Create logs directory - try multiple locations for compiled executables
            logs_dir = None
            possible_log_dirs = [
                os.path.join(base_dir, "logs"),
                os.path.join(os.getcwd(), "logs"),
                os.path.join(os.path.expanduser("~"), "Building_Generator_Logs"),
            ]
            
            for log_dir in possible_log_dirs:
                try:
                    os.makedirs(log_dir, exist_ok=True)
                    # Test write permissions
                    test_file = os.path.join(log_dir, "test_write.tmp")
                    with open(test_file, 'w') as f:
                        f.write("test")
                    os.remove(test_file)
                    logs_dir = log_dir
                    break
                except (OSError, PermissionError):
                    continue
            
            # If no writable directory found, use temp directory as last resort
            if logs_dir is None:
                import tempfile
                logs_dir = tempfile.gettempdir()
            
            # Configure the root logger
            root_logger = logging.getLogger()
            root_logger.setLevel(logging.INFO)
            
            # Remove any existing handlers to avoid duplicates
            for handler in root_logger.handlers[:]:
                root_logger.removeHandler(handler)
            
            # Create formatter for consistent log messages
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            
            # For compiled executables, always create an emergency log file
            if is_compiled:
                try:
                    emergency_log = os.path.join(logs_dir, "building_generator_emergency.log")
                    emergency_handler = logging.FileHandler(emergency_log, mode='w')
                    emergency_handler.setLevel(logging.DEBUG)
                    emergency_handler.setFormatter(formatter)
                    root_logger.addHandler(emergency_handler)
                    
                    # Log startup information immediately
                    root_logger.critical(f"=== COMPILED EXECUTABLE STARTUP ===")
                    root_logger.critical(f"Executable path: {sys.executable}")
                    root_logger.critical(f"Working directory: {os.getcwd()}")
                    root_logger.critical(f"Base directory: {base_dir}")
                    root_logger.critical(f"Logs directory: {logs_dir}")
                    root_logger.critical(f"Emergency log: {emergency_log}")
                    root_logger.critical("=== END STARTUP INFO ===")
                except Exception as e:
                    # If even emergency logging fails, create a fallback file
                    try:
                        fallback_log = os.path.join(os.path.expanduser("~"), "building_generator_fallback.log")
                        with open(fallback_log, 'w') as f:
                            f.write(f"CRITICAL ERROR: Cannot set up logging system\n")
                            f.write(f"Error: {str(e)}\n")
                            f.write(f"Executable: {sys.executable}\n")
                            f.write(f"Working dir: {os.getcwd()}\n")
                    except:
                        pass  # If all else fails, continue without logging
            else:
                # For normal execution, add a NullHandler by default
                null_handler = logging.NullHandler()
                root_logger.addHandler(null_handler)
            
            # Store the logs directory for later use
            self.logs_dir = logs_dir
            
            # Configure all imported modules to use this logger configuration
            for name in ['Load_Geo_File', 'objective_cache', 'Database', 'MainCode', 'OSMLegend', 'ValuesDictionary']:
                module_logger = logging.getLogger(name)
                module_logger.setLevel(logging.INFO)
            
            # Log successful initialization
            if is_compiled:
                root_logger.info("Logging system initialized for compiled executable")
            else:
                root_logger.debug("Logging system initialized for Python script")
                
        except Exception as e:
            # Emergency fallback - write to a file in user's home directory
            try:
                emergency_file = os.path.join(os.path.expanduser("~"), "building_generator_critical_error.log")
                with open(emergency_file, 'w') as f:
                    f.write(f"CRITICAL: Failed to initialize logging system\n")
                    f.write(f"Error: {str(e)}\n")
                    f.write(f"Python path: {sys.executable}\n")
                    f.write(f"Working directory: {os.getcwd()}\n")
                    f.write(f"Frozen: {getattr(sys, 'frozen', False)}\n")
                    import traceback
                    f.write(f"Traceback:\n{traceback.format_exc()}\n")
            except:
                pass  # If even this fails, continue without logging

    def _get_root_dir(self):
        """Return the application root directory for storing footprints."""
        try:
            is_compiled = getattr(sys, 'frozen', False)
            if is_compiled:
                return os.path.dirname(sys.executable)
            return os.path.dirname(os.path.abspath(__file__))
        except Exception:
            return os.getcwd()

    def _get_footprints_root(self):
        """Return the root/footprints directory path."""
        return os.path.join(self._get_root_dir(), "footprints")

    def _ensure_footprints_dirs(self):
        """Create the footprints directory structure if missing."""
        fp_root = self._get_footprints_root()
        subdirs = [
            fp_root,
            os.path.join(fp_root, "microsoft"),
            os.path.join(fp_root, "google"),
            os.path.join(fp_root, "tmp"),
        ]
        for d in subdirs:
            try:
                os.makedirs(d, exist_ok=True)
            except Exception as e:
                logging.debug(f"Could not create directory {d}: {e}")

    def SelectCTfile(self, event):
        """Open a file dialog to select a CT XML file and update the application state.
        
        This method handles CT file selection, updates the database path, and refreshes
        the database display based on the selected CT file.
        """
        logging.debug("CT file selection dialog opened")
        
        # open a file dialog and update the label text with the selected file path
        file_path = tkinter.filedialog.askopenfilename(
            filetypes=[("Class-Table files", "*.xml")]
        )
        
        if file_path:
            logging.info(f"CT file selected: {file_path}")
            # Will place in CTfile the right path
            if file_path == "":
                self.shared_data["CTpath"].set("No CT file selected")
                logging.warning("Empty CT file path selected")
            else:
                self.shared_data["CTpath"].set(file_path)
                logging.debug(f"CT path updated in shared_data: {file_path}")

            self.Get_Version_Theater_From_path(file_path)
            ImagePath = self.frames["DatabasePage"].Check_Availability_Database()

            # Update Un/Availability picture of Database which loaded through CT XML file
            self.frames["DatabasePage"].image_available = PhotoImage(file=ImagePath)
            self.frames["DatabasePage"].image_11 = self.frames[
                "DatabasePage"
            ].canvas.create_image(
                989.0, 412.0, image=self.frames["DatabasePage"].image_available
            )
            
            # Get Database and present it in table
            DB_path = self.shared_data["BMS_Database_Path"].get()
            if DB_path and self.shared_data["Database_Availability"].get() == "1":
                logging.info(f"Loading database from: {DB_path}")
                array = Load_Db(DB_path, "All")
                self.shared_data["BMS_Databse"] = array
                self.frames["DatabasePage"].UdpateDB_Tables()
                logging.debug("Database loaded and tables updated successfully")

            # If Database is not present, erase last data related to the old DB
            else:
                logging.warning("Database not available, clearing existing data")
                self.shared_data["BMS_Databse"] = np.array([])

                for row in self.frames["DatabasePage"].ModelsTable.get_children():
                    self.frames["DatabasePage"].ModelsTable.delete(row)
        else:
            logging.debug("CT file selection cancelled by user")

    def SettingWindow(self):
        """Open the enhanced settings window with tabbed interface.
        
        This method creates an instance of the enhanced SettingsWindow class from
        components/settings_window.py, which provides a modern tabbed interface
        with comprehensive configuration options including full support for the
        Value field in FED XML entries.
        """
        # Disable settings buttons while window is open
        self.disable_Settings_buttons()
        
        # Create the enhanced settings window
        # Pass self (MainPage) as parent to provide access to shared_data and methods
        # Pass all relevant paths to the settings window
        ct_path = self.shared_data["CTpath"].get()
        backup_kto_path = self.shared_data["backup_CTpath"].get()
        database_path = self.shared_data["BMS_Database_Path"].get()
        geojson_path = self.shared_data["Geopath"].get()
        editor_path = self.shared_data["EditorSavingPath"].get() if "EditorSavingPath" in self.shared_data else ""
        
        # Create settings window with all paths
        settings_window = SettingsWindow(
            self, 
            bms_path=ct_path, 
            kto_backup_path=backup_kto_path,
            database_path=database_path,
            geojson_path=geojson_path,
            editor_extraction_path=editor_path
        )
        
        # Register the child window for proper cleanup
        self.register_child_window(settings_window)
        
        # Ensure Auto-Start checkbox state matches shared data
        startup_value = self.shared_data["Startup"].get()
        # Set our own Auto_Load value based on the Startup shared data
        self.Auto_Load.set(startup_value == "1")
        
        # Update the auto_start_var in settings window to match
        if hasattr(settings_window, 'auto_start_var'):
            settings_window.auto_start_var.set(startup_value == "1")
        
        # Bind the window's "destroy" event to re-enable settings button and unregister
        def on_settings_destroy(event):
            self.unregister_child_window(settings_window)
            self.enable_Settings_button(event)
        
        settings_window.bind("<Destroy>", on_settings_destroy)
        
        return settings_window

    def update_logging_config(self, level='INFO', handlers=None):
        """Update the application logging configuration.
        
        This method configures the logging system with specified level and handlers.
        
        Args:
            level (str): The logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
            handlers (list): List of handler types to use ('console', 'file')
        """
        if handlers is None:
            handlers = ['console']
            
        # Validate and normalize the log level
        valid_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        if level not in valid_levels:
            level = 'INFO'  # Default to INFO if invalid level provided
            
        # Update the log level in shared data for other components to access
        self.shared_data["log_level"].set(level)
        
        # Configure the root logger
        root_logger = logging.getLogger()
        numeric_level = getattr(logging, level)
        root_logger.setLevel(numeric_level)
        
        # Remove existing handlers
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)
            
        # Create formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        # Add requested handlers or NullHandler if none requested
        if 'console' in handlers:
            console_handler = logging.StreamHandler()
            console_handler.setLevel(numeric_level)
            console_handler.setFormatter(formatter)
            root_logger.addHandler(console_handler)
            
        if 'file' in handlers:
            # Use the logs directory determined during initialization
            logs_dir = getattr(self, 'logs_dir', None)
            if logs_dir is None:
                # Fallback if logs_dir wasn't set during initialization
                is_compiled = getattr(sys, 'frozen', False)
                if is_compiled:
                    logs_dir = os.path.dirname(sys.executable)
                else:
                    logs_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")
                os.makedirs(logs_dir, exist_ok=True)
            
            # Create file handler with error handling
            try:
                log_file = os.path.join(logs_dir, "building_generator.log")
                file_handler = logging.FileHandler(log_file)
                file_handler.setLevel(numeric_level)
                file_handler.setFormatter(formatter)
                root_logger.addHandler(file_handler)
            except (OSError, PermissionError) as e:
                # If main log file fails, try alternative locations
                fallback_locations = [
                    os.path.join(os.getcwd(), "building_generator.log"),
                    os.path.join(os.path.expanduser("~"), "building_generator.log"),
                ]
                for fallback_log in fallback_locations:
                    try:
                        file_handler = logging.FileHandler(fallback_log)
                        file_handler.setLevel(numeric_level)
                        file_handler.setFormatter(formatter)
                        root_logger.addHandler(file_handler)
                        logging.warning(f"Using fallback log location: {fallback_log}")
                        break
                    except (OSError, PermissionError):
                        continue
            
        # If no real handlers were added, add NullHandler to prevent automatic StreamHandler creation
        if not handlers or len(handlers) == 0:
            null_handler = logging.NullHandler()
            root_logger.addHandler(null_handler)
        
        # Update levels for known module loggers as well
        for name in ['Load_Geo_File', 'objective_cache', 'Database', 'MainCode', 'OSMLegend', 'ValuesDictionary']:
            module_logger = logging.getLogger(name)
            module_logger.setLevel(numeric_level)
            
        # Log the configuration change
        logger = logging.getLogger(__name__)
        logger.info(f"Logging configuration updated: level={level}, handlers={handlers}")
        
        # Test message to verify logging is working (only when handlers are configured)
        if handlers:
            logger.debug("Debug logging test - settings applied successfully")
            logger.info("Info logging test - configuration active")
            logger.warning("Warning logging test - all levels functional")

    def open_console_window(self):
        """Opens a new console window or brings existing one to front"""
        show_console(self)

    def startup_selection_checkbox(self):
        """Update the Auto-Start setting when the checkbox is toggled in the settings window.
        
        This method only updates the config file if it exists, and uses json_path_handler.
        It doesn't create a new config file if one doesn't exist.
        """
        try:
            # Log the current state for debugging
            logging.info(f"Auto-Start checkbox toggled. New state: {self.Auto_Load.get()}")
            
            # Load the existing config file using json_path_handler
            config_data = load_json(JsonFiles.CONFIG_JSON, default=None)
            
            # Only proceed if we have a valid config file - don't create one if it doesn't exist
            if config_data:
                # Set Startup value based on the Auto_Load checkbox state
                startup_value = "1" if self.Auto_Load.get() else "0"
                
                # Update both the shared_data and config_data
                self.shared_data["Startup"].set(startup_value)
                config_data["Startup"] = startup_value
                
                # Save the updated config file using json_path_handler
                if save_json(JsonFiles.CONFIG_JSON, config_data):
                    logging.info(f"Successfully saved config.json with Startup={startup_value}")
                else:
                    logging.error("Failed to save config.json")
            else:
                # Config file doesn't exist, just update the shared_data
                startup_value = "1" if self.Auto_Load.get() else "0"
                self.shared_data["Startup"].set(startup_value)
                logging.info("No config file found, only updated shared_data")
            
        except Exception as e:
            logging.error(f"Error in startup_selection_checkbox: {str(e)}")
            logging.error(traceback.format_exc())

    def enable_Settings_button(self, event):
        """Enable the settings button in all pages, with safe destruction handling."""
        try:
            # Skip if window is being destroyed
            if hasattr(self, '_destroying') and self._destroying:
                return
                
            # Enable the settings button in all pages
            for Page in ("DashboardPage", "DatabasePage", "GeoDataPage", "OperationPage", "FootPrintsPage"):
                try:
                    # Check if frame exists and widget is still valid
                    if (Page in self.frames and 
                        hasattr(self.frames[Page], 'button_settings') and
                        self.frames[Page].button_settings.winfo_exists()):
                        self.frames[Page].button_settings.configure(state="normal")
                except tk.TclError as e:
                    # Widget has been destroyed, skip it
                    logging.debug(f"Widget {Page}.button_settings destroyed during enable: {e}")
                    continue
                except Exception as e:
                    logging.warning(f"Error enabling settings button for {Page}: {e}")
                    continue
        except Exception as e:
            logging.error(f"Error in enable_Settings_button: {e}")

    def disable_Settings_buttons(self):
        """Disable the settings button in all pages, with safe destruction handling."""
        try:
            # Skip if window is being destroyed
            if hasattr(self, '_destroying') and self._destroying:
                return
                
            # Disable the settings button in all pages
            for Page in ("DashboardPage", "DatabasePage", "GeoDataPage", "OperationPage", "FootPrintsPage"):
                try:
                    # Check if frame exists and widget is still valid
                    if (Page in self.frames and 
                        hasattr(self.frames[Page], 'button_settings') and
                        self.frames[Page].button_settings.winfo_exists()):
                        self.frames[Page].button_settings.configure(state="disabled")
                except tk.TclError as e:
                    # Widget has been destroyed, skip it
                    logging.debug(f"Widget {Page}.button_settings destroyed during disable: {e}")
                    continue
                except Exception as e:
                    logging.warning(f"Error disabling settings button for {Page}: {e}")
                    continue
        except Exception as e:
            logging.error(f"Error in disable_Settings_buttons: {e}")

    def save_config_file(self):
        """Check if Configuration file exists, and Save it when "save" button is clicked"""
        try:
            # Prepare settings dictionary with all current values
            settings = {
                "Startup": self.shared_data["Startup"].get(),
                "CT_path": self.shared_data["CTpath"].get(),
                "BMS_Database_Path": self.shared_data["BMS_Database_Path"].get(),
                "Theater": self.shared_data["Theater"].get(),
                "BMS_version": self.shared_data["BMS_version"].get(),
                "Geopath": self.shared_data["Geopath"].get(),
                "backup_CTpath": self.shared_data["backup_CTpath"].get(),
                "EditorSavingPath": self.shared_data["EditorSavingPath"].get(),
                "Database_Availability": self.shared_data["Database_Availability"].get(),
                "projection_path": self.shared_data["projection_path"].get(),
                "projection_string": self.shared_data["projection_string"].get(),
                "backup_bms_files": self.shared_data['backup_bms_files'].get() if isinstance(self.shared_data.get('backup_bms_files'), tk.StringVar) else '1',
                "backup_features_files": self.shared_data['backup_features_files'].get() if isinstance(self.shared_data.get('backup_features_files'), tk.StringVar) else '1',
                "log_level": self.shared_data["log_level"].get(),
                "logging_method": self.shared_data["logging_method"].get(),
                "restriction_box": self.frames["OperationPage"].restriction_box.get("0.0", "end"),
                "textbox_Radius_random": self.frames["OperationPage"].textbox_Radius_random.get(),
                "textbox_Amount_random": self.frames["OperationPage"].textbox_Amount_random.get(),
                "textbox_Values_random1": self.frames["OperationPage"].textbox_Values_random1.get(),
                "textbox_Values_random2": self.frames["OperationPage"].textbox_Values_random2.get(),
                "switch_Presence_random": self.frames["OperationPage"].switch_Presence_random.get(),
                "textbox_Presence_random1": self.frames["OperationPage"].textbox_Presence_random1.get(),
                "textbox_Presence_random2": self.frames["OperationPage"].textbox_Presence_random2.get(),
                "Fillter_optionmenu": self.frames["OperationPage"].Fillter_optionmenu.get(),
                "values_geo_optionmenu": self.frames["OperationPage"].values_geo_optionmenu.get(),
                "values_rand_optionmenu": self.frames["OperationPage"].values_rand_optionmenu.get(),
                "Selection_optionmenu": self.frames["OperationPage"].Selection_optionmenu.get(),
                "Auto_features_detector": self.frames["OperationPage"].Auto_features_detector.get(),
                "textbox_Amount_geo": self.frames["OperationPage"].textbox_Amount_geo.get(),
                "textbox_Values_geo1": self.frames["OperationPage"].textbox_Values_geo1.get(),
                "textbox_Values_geo2": self.frames["OperationPage"].textbox_Values_geo2.get(),
                "switch_Presence_geo": self.frames["OperationPage"].switch_Presence_geo.get(),
                "textbox_Presence_geo1": self.frames["OperationPage"].textbox_Presence_geo1.get(),
                "textbox_Presence_geo2": self.frames["OperationPage"].textbox_Presence_geo2.get(),
                "segemented_button": self.frames["OperationPage"].segemented_button.get(),
                "segemented_button_Saving": self.frames["OperationPage"].segemented_button_Saving.get(),
                "segemented_button_graphing1": self.frames["OperationPage"].segemented_button_graphing1.get(),
                "segemented_button_graphing2": self.frames["OperationPage"].segemented_button_graphing2.get(),
                "Editor_Extraction_name": self.frames["OperationPage"].Editor_Extraction_name.get(),
                "floor_deviation_entry": self.frames["OperationPage"].floor_deviation_entry.get(),
                "textbox_floor_height": self.frames["GeoDataPage"].textbox_floor_height.get(),
                "sorting_saving": self.frames["OperationPage"].sorting_saving.get(),
                "distribution_selection": self.frames["OperationPage"].distribution_selection.get(),
                "MaxGeojsonDraw": str(self.shared_data["MaxGeojsonDraw"].get()),# Visualization config
            }
            
            # Check if configuration file already exists in data_components folder
            try:
                existing_config = load_json(JsonFiles.CONFIG_JSON, default=None)
                if existing_config:
                    result = messagebox.askyesno(
                        "Override",
                        "Configuration file already exists in \nDo you want to override it?",
                    )
                    if not result:
                        return messagebox.showinfo("Saving Aborted", "The saving process has been cancelled by user")
            except Exception:
                # If there's an error checking for the file, assume it doesn't exist
                pass
                
            # Save the configuration to data_components folder
            save_json(JsonFiles.CONFIG_JSON, settings)
            
            # Show success message
            return messagebox.showinfo(
                "Saving succeeded",
                "The configuration has been saved to data_components folder successfully"
            )
            
        except Exception as e:
            # Show error message if any exception occurs during saving
            logging.error(f"Error saving configuration: {str(e)}")
            return messagebox.showerror(
                    "Saving Aborted", "The Saving process has been aborted"
                )

    def load_config(self, show_message=True):
        """Check if Configuration file exists, and load it when "load" button is clicked
        
        Args:
            show_message: Whether to show success/error messages. Set to False for silent loading during startup.
        """
        try:
            # Use json_path_handler to read from data_components folder
            loaded_data = load_json(JsonFiles.CONFIG_JSON, default=None)
            
            if not loaded_data:
                if show_message:
                    messagebox.showwarning("Loading Failed", "Configuration file doesn't exist or is empty in data_components folder")
                return

            # Set shared data values - using get() with default values for safety
            self.shared_data["Startup"].set(loaded_data.get("Startup", ""))
            self.shared_data["CTpath"].set(loaded_data.get("CT_path", ""))
            self.shared_data["BMS_Database_Path"].set(loaded_data.get("BMS_Database_Path", ""))
            self.shared_data["Theater"].set(loaded_data.get("Theater", ""))
            self.shared_data["BMS_version"].set(loaded_data.get("BMS_version", ""))
            self.shared_data["Geopath"].set(loaded_data.get("Geopath", ""))
            self.shared_data["backup_CTpath"].set(loaded_data.get("backup_CTpath", ""))
            self.shared_data["EditorSavingPath"].set(loaded_data.get("EditorSavingPath", ""))
            self.shared_data["Database_Availability"].set(loaded_data.get("Database_Availability", ""))
            self.shared_data["projection_path"].set(loaded_data.get("projection_path", ""))
            self.shared_data["projection_string"].set(loaded_data.get("projection_string", ""))
            self.shared_data['backup_bms_files'] = loaded_data.get('backup_bms_files', '0') # Default to '0' (False)
            self.shared_data['backup_features_files'] = loaded_data.get('backup_features_files', '0') # Default to '0' (False)
            try:
                max_geo = int(loaded_data.get("MaxGeojsonDraw", 256)) # Visualization config (default 256)
            except Exception:
                max_geo = 256
            self.shared_data["MaxGeojsonDraw"].set(max(10, min(1000, max_geo)))
            
            # Load and apply logging configuration using settings_window.py mapping approach
            log_level = loaded_data.get("log_level", "INFO")
            logging_method = loaded_data.get("logging_method", "None")  # Default to None (disabled)
            
            # Validate log level
            valid_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
            if log_level not in valid_levels:
                log_level = 'INFO'  # Default to INFO if invalid level
            
            self.shared_data["log_level"].set(log_level)
            self.shared_data["logging_method"].set(logging_method)
            
            # Convert logging_method to handlers list using the same mapping as settings_window.py
            handlers = []
            if logging_method == "Console":
                handlers = ['console']
            elif logging_method == "File":
                handlers = ['file']
            elif logging_method == "Both":
                handlers = ['console', 'file']
            elif logging_method == "None":
                handlers = []  # No logging
            else:
                # Invalid value, default to None (disabled) as per user specification
                handlers = []
                logging_method = "None"
                self.shared_data["logging_method"].set("None")
            
            # Apply the logging configuration - only if handlers are specified
            if handlers:
                self.update_logging_config(level=log_level, handlers=handlers)
                logging.info(f"Applied loaded logging configuration: level={log_level}, method={logging_method}")
            else:
                # Disable logging by removing all handlers and adding NullHandler
                root_logger = logging.getLogger()
                for handler in root_logger.handlers[:]:
                    root_logger.removeHandler(handler)
                # Add NullHandler to prevent automatic StreamHandler creation
                null_handler = logging.NullHandler()
                root_logger.addHandler(null_handler)
                logging.info("Logging disabled by loaded configuration")
            
            # Set dropdown and segmented button values
            self.frames["OperationPage"].Fillter_optionmenu.set(loaded_data.get("Fillter_optionmenu", ""))
            self.frames["OperationPage"].values_geo_optionmenu.set(loaded_data.get("values_geo_optionmenu", ""))
            self.frames["OperationPage"].values_rand_optionmenu.set(loaded_data.get("values_rand_optionmenu", ""))
            self.frames["OperationPage"].Selection_optionmenu.set(loaded_data.get("Selection_optionmenu", ""))
            self.frames["OperationPage"].segemented_button.set(loaded_data.get("segemented_button", ""))
            self.frames["OperationPage"].segemented_button_Saving.set(loaded_data.get("segemented_button_Saving", ""))
            self.frames["OperationPage"].segemented_button_graphing1.set(loaded_data.get("segemented_button_graphing1", ""))
            self.frames["OperationPage"].segemented_button_graphing2.set(loaded_data.get("segemented_button_graphing2", ""))
            
            # Set distribution selection if present (new feature)
            if hasattr(self.frames["OperationPage"], "distribution_selection") and "distribution_selection" in loaded_data:
                self.frames["OperationPage"].distribution_selection.set(loaded_data["distribution_selection"])
            
            # Set sorting saving option if present
            if hasattr(self.frames["OperationPage"], "sorting_saving") and "sorting_saving" in loaded_data:
                self.frames["OperationPage"].sorting_saving.set(loaded_data["sorting_saving"])

            # Force entries to disable or enable
            self.frames["OperationPage"].value_State(
                self.frames["OperationPage"].values_rand_optionmenu.get(), "rand"
            )
            self.frames["OperationPage"].value_State(
                self.frames["OperationPage"].values_rand_optionmenu.get(), "geo"
            )

            # setting Switches
            states = [
                "switch_Presence_random",
                "Auto_features_detector",
                "switch_Presence_geo",
            ]

            for state in states:
                if loaded_data[state]:
                    self.frames["OperationPage"].__dict__[state].select()
                else:
                    self.frames["OperationPage"].__dict__[state].deselect()

            # Force switches functions
            self.frames["OperationPage"].switch_presence_State_random()
            self.frames["OperationPage"].switch_presence_State_geo()

            # clear and Set Text Boxes
            text_boxes = [
                "textbox_Amount_geo",
                "textbox_Values_geo1",
                "textbox_Values_geo2",
                "textbox_Presence_geo1",
                "textbox_Presence_geo2",
                "textbox_Radius_random",
                "textbox_Amount_random",
                "textbox_Values_random1",
                "textbox_Values_random2",
                "textbox_Presence_random1",
                "textbox_Presence_random2",
                "Editor_Extraction_name",
            ]
            
            # Add new text boxes
            if "floor_deviation_entry" in loaded_data:
                text_boxes.append("floor_deviation_entry")
                
            for box in text_boxes:
                if loaded_data and loaded_data[box] is not None:
                    self.frames["OperationPage"].__dict__[box].delete(0, tk.END)
                    self.frames["OperationPage"].__dict__[box].insert(
                        0, loaded_data[box]
                    )
                    
            # Handle floor height separately since it's in a different frame
            if "textbox_floor_height" in loaded_data:
                self.frames["GeoDataPage"].textbox_floor_height.delete(0, tk.END)
                self.frames["GeoDataPage"].textbox_floor_height.insert(
                    0, loaded_data["textbox_floor_height"]
                )
                
            self.frames["OperationPage"].restriction_box.delete("0.0", tk.END)
            self.frames["OperationPage"].restriction_box.insert(
                tk.END, loaded_data["restriction_box"]
            )
            
            # Will try to load Database through CT path that been inserted through the config file
            if loaded_data["CT_path"]:
                logging.debug("Loading database from config CT path")
                ImagePath = self.frames["DatabasePage"].Check_Availability_Database()

                # Update Un/Availability picture of Database which loaded through CT XML file
                self.frames["DatabasePage"].image_available = PhotoImage(file=ImagePath)
                self.frames["DatabasePage"].image_11 = self.frames[
                    "DatabasePage"
                ].canvas.create_image(
                    989.0, 412.0, image=self.frames["DatabasePage"].image_available
                )
                # Get Database and present it in table
                DB_path = self.shared_data["BMS_Database_Path"].get()

                if DB_path and self.shared_data["Database_Availability"].get() == "1":
                    logging.info(f"Loading database from: {DB_path}")
                    array = Load_Db(DB_path, "All")
                    self.shared_data["BMS_Databse"] = array
                    self.frames["DatabasePage"].UdpateDB_Tables()
                    logging.debug("Database loaded and tables updated successfully")

                # If Database is not present, erase last data related to the old DB
                else:
                    logging.warning("Database not available, clearing data")
                    self.shared_data["BMS_Databse"] = np.array([])
                    self.shared_data["CTpath"].set("No CT file selected")
                    for row in self.frames["DatabasePage"].ModelsTable.get_children():
                        self.frames["DatabasePage"].ModelsTable.delete(row)
                        
            # Show success message only if show_message is True
            if show_message:
                messagebox.showinfo("Loading Succeeded", "Configuration has been loaded successfully from data_components folder")
            
        except Exception as e:
            # Log the error regardless of show_message setting
            logging.error(f"Error loading configuration: {str(e)}")
            
            # Show error message only if show_message is True
            if show_message:
                messagebox.showerror("Loading Error", f"An error occurred while loading configuration: {str(e)}")

    def startup_definition(self):
        """Check if startup configuration exists in the config file, and apply it if it does
        
        This method loads logging configuration from config file and applies it,
        then loads full config if auto-start is enabled.
        """
        try:
            # Use json_path_handler to read from data_components folder
            config_data = load_json(JsonFiles.CONFIG_JSON, default=None)
            
            # Skip if no config data found
            if not config_data:
                logging.info("No config data found. Skipping startup configuration.")
                return
                
            # Get the Startup value from config
            startup_value = config_data.get("Startup", "0")  # Default to '0' if not found
            
            # Update shared data with the startup value
            self.shared_data["Startup"].set(startup_value)
            
            # Update Auto_Load to match the Startup value from config
            self.Auto_Load.set(startup_value == "1")
            
            # Apply logging configuration from config file using settings_window.py mapping approach
            log_level = config_data.get("log_level", "INFO")
            logging_method = config_data.get("logging_method", "None")  # Default to None (disabled)
            
            # Validate log level
            valid_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
            if log_level not in valid_levels:
                log_level = 'INFO'  # Default to INFO if invalid level
            
            # Update shared data with logging settings
            self.shared_data["log_level"].set(log_level)
            self.shared_data["logging_method"].set(logging_method)
            
            # Convert logging_method to handlers list using the same mapping as settings_window.py
            handlers = []
            if logging_method == "Console":
                handlers = ['console']
            elif logging_method == "File":
                handlers = ['file']
            elif logging_method == "Both":
                handlers = ['console', 'file']
            elif logging_method == "None":
                handlers = []  # No logging
            else:
                # Invalid value, default to None (disabled) as per user specification
                handlers = []
                logging_method = "None"
                self.shared_data["logging_method"].set("None")
            
            # Apply the logging configuration - only if handlers are specified
            if handlers:
                self.update_logging_config(level=log_level, handlers=handlers)
                logging.info(f"Applied logging configuration from config: level={log_level}, method={logging_method}")
            else:
                # Disable logging by removing all handlers and adding NullHandler
                root_logger = logging.getLogger()
                for handler in root_logger.handlers[:]:
                    root_logger.removeHandler(handler)
                # Add NullHandler to prevent automatic StreamHandler creation
                null_handler = logging.NullHandler()
                root_logger.addHandler(null_handler)
                logging.info("Logging disabled by configuration")
            
            # Only load full config if Startup is '1'
            if startup_value == "1":
                logging.info("Auto-start is enabled. Loading full configuration...")
                self.load_config(show_message=False)
            else:
                logging.info("Auto-start is disabled. Applied logging settings only.")
                
        except Exception as e:
            # Log the error but don't show a message box as this happens at startup
            logging.error(f"Error loading startup configuration: {str(e)}")

    def on_closing(self):
        """Handle application closing with proper cleanup."""
        try:
            # Set destruction flag to prevent further operations
            self._destroying = True
            
            # Close all child windows first
            self._close_all_child_windows()
            
            # Perform any other cleanup if needed
            logging.info("Application closing...")
            
            # Finally destroy the main window
            self.destroy()
        except Exception as e:
            logging.error(f"Error during application closing: {e}")
            # Force destroy in case of error
            try:
                self.destroy()
            except:
                pass

    def _close_all_child_windows(self):
        """Safely close all tracked child windows."""
        try:
            # Make a copy of the set to avoid modification during iteration
            child_windows_copy = self._child_windows.copy()
            
            for window in child_windows_copy:
                try:
                    if window.winfo_exists():
                        window.destroy()
                except Exception as e:
                    logging.debug(f"Error closing child window: {e}")
            
            # Clear the set
            self._child_windows.clear()
        except Exception as e:
            logging.error(f"Error closing child windows: {e}")

    def register_child_window(self, window):
        """Register a child window for proper cleanup."""
        if not self._destroying:
            self._child_windows.add(window)

    def unregister_child_window(self, window):
        """Unregister a child window when it's closed normally."""
        self._child_windows.discard(window)

    def Get_Version_Theater_From_path(self, file_path):
        """Parse the CT XML file path to extract BMS version and theater information.
        
        The function analyzes the path structure to determine the BMS version and theater.
        If not found, "N/A" is set for the respective values.
        
        Args:
            file_path (str): Path to the CT XML file
        """
        logging.debug(f"Parsing version and theater from path: {file_path}")
        
        # Split path into components
        components = file_path.split("/")
        try:
            # find index of rightmost string of "Data"
            idx = components.index("Data")
            # Get the BMS version string before "Data"
            bms_version = components[idx - 1]
            self.shared_data["BMS_version"].set(bms_version)
            logging.info(f"BMS version detected: {bms_version}")
            
            # if component before "Data" starts with "Add-on" or "Add-On" its theater
            if components[idx + 1].lower().startswith("add-on"):
                temp = components[idx + 1].lower().replace("add-on ", "")
                theater = (
                    temp[0].upper() + temp[1 : len(temp)]
                )  # Assign upper later to the first letter
                self.shared_data["Theater"].set(theater)
                logging.info(f"Theater detected from add-on: {theater}")
            else:
                # if version is not detected, place Korea as the default theater
                self.shared_data["Theater"].set("korea")
                logging.info("Theater set to default: korea")

        except Exception as e:
            logging.warning(f"Error parsing version/theater from path: {str(e)}")
            # if version is not detected, find a theater with "add-on" (korea cannot be located)
            theater = "N/A"
            self.shared_data["BMS_version"].set("N/A")
            logging.debug("BMS version set to N/A due to parsing error")
            
            # Iterate over the components from right to left
            for i in range(len(components) - 1, -1, -1):
                # If the component starts with "Add-On", update the Theater string and break the loop
                if components[i].lower().startswith("add-on"):
                    temp = components[i].lower().replace("add-on ", "")
                    # first letter should be upper
                    theater = (
                        temp[0].upper() + temp[1 : len(temp)]
                    )  # Assign upper later to the first letter
                    self.shared_data["Theater"].set(theater)
                    logging.info(f"Theater detected from fallback search: {theater}")
                    break
            # if theater is not detected then N/A
            self.shared_data["Theater"].set(theater)

class DashboardPage(tk.Frame):
    def __init__(self, parent, controller):
        tk.Frame.__init__(self, parent)
        self.controller = controller

        self.Body_font = Ctk.CTkFont(family="Inter", size=15)
        self.Body_font_Bold = Ctk.CTkFont(family="Inter", size=15, weight="bold")
        self.button_font = Ctk.CTkFont(family="Inter", size=12)
        self.dash_font = Ctk.CTkFont(family="Inter", size=10)

        self.canvas = Canvas(
            self,
            bg="#FFFFFF",
            height=720,
            width=1152,
            bd=0,
            highlightthickness=0,
            relief="ridge",
        )

        self.canvas.place(x=0, y=0)
        self.canvas.create_rectangle(0.0, 0.0, 204.0, 720.0, fill="#A0B9D0", outline="")

        # Load button images using CTkImage
        self.button_operations_img = Ctk.CTkImage(
            light_image=Image.open(str(self.controller.ASSETS_PATH / "button_operations.png")),size=(21, 17)
        )
        self.button_geo_img = Ctk.CTkImage(
            light_image=Image.open(str(self.controller.ASSETS_PATH / "button_geo.png")),size=(21, 17)
        )
        self.button_data_img = Ctk.CTkImage(
            light_image=Image.open(str(self.controller.ASSETS_PATH / "button_data.png")),size=(21, 17)
        )
        self.button_dash_img = Ctk.CTkImage(
            light_image=Image.open(str(self.controller.ASSETS_PATH / "button_dash.png")),size=(21, 17)
        )
        self.button_settings_img = Ctk.CTkImage(
            light_image=Image.open(str(self.controller.ASSETS_PATH / "button_options.png")),size=(21, 17)
        )
        self.button_footprints_img = Ctk.CTkImage(
            light_image=Image.open(str(self.controller.ASSETS_PATH / "button_footprint.png")),
            size=(21, 17)
        )

        self.button_operations = Ctk.CTkButton(
            self,
            text="Operations",
            fg_color="#A1B9D0",
            bg_color="#A1B9D0",
            image=self.button_operations_img,
            height=33,
            width=167,
            command=lambda: controller.show_frame("OperationPage"),
            corner_radius=0,
            hover_color="#7A92A9",
            font=("arial", 15),
            text_color="#000000",
        )
        self.button_operations.place(x=0, y=397)

        # New FootPrints navigation button
        self.button_footprints = Ctk.CTkButton(
            self,
            text="FootPrints",
            fg_color="#A1B9D0",
            bg_color="#A1B9D0",
            image=self.button_footprints_img,
            height=33,
            width=167,
            command=lambda: controller.show_frame("FootPrintsPage"),
            corner_radius=0,
            hover_color="#7A92A9",
            font=("Sans Font", 15),
            text_color="#000000",
        )
        self.button_footprints.place(x=0, y=445)

        self.button_geo = Ctk.CTkButton(
            self,
            text="GeoData",
            fg_color="#A1B9D0",
            bg_color="#A1B9D0",
            image=self.button_geo_img,
            height=33,
            width=167,
            command=lambda: controller.show_frame("GeoDataPage"),
            corner_radius=0,
            hover_color="#7A92A9",
            font=("Sans Font", 15),
            text_color="#000000",
        )
        self.button_geo.place(x=0, y=349)

        self.button_data = Ctk.CTkButton(
            self,
            text="Database",
            fg_color="#A1B9D0",
            bg_color="#A1B9D0",
            image=self.button_data_img,
            height=33,
            width=167,
            command=lambda: controller.show_frame("DatabasePage"),
            corner_radius=0,
            hover_color="#7A92A9",
            font=("Sans Font", 15),
            text_color="#000000",
        )
        self.button_data.place(x=0, y=297)

        self.button_dash = Ctk.CTkButton(
            self,
            text="DashBoard",
            fg_color="#7A92A9",
            bg_color="#7A92A9",
            image=self.button_dash_img,
            height=33,
            width=167,
            hover=False,
            corner_radius=0,
            font=("Sans Font", 15),
            text_color="#000000",
        )
        self.button_dash.place(x=0, y=248)

        self.button_settings = Ctk.CTkButton(
            self,
            text="More\nSettings",
            fg_color="#778593",
            bg_color="#A1B9D0",
            image=self.button_settings_img,
            height=97,
            width=125,
            corner_radius=20,
            hover=False,
            font=("Sans Font", 16),
            text_color="#000000",
            command=self.controller.SettingWindow,
        )
        self.button_settings.place(x=14, y=581)
        
        self.canvas.create_rectangle(
            172.0, 0.0, 1152.0, 720.0, fill="#A1B9D0", outline=""
        )

        self.image_image_1 = PhotoImage(
            file=str(self.controller.ASSETS_PATH / "image_BG.png")
        )
        self.canvas.create_image(659.0, 360.0, image=self.image_image_1)

        self.image_image_2 = PhotoImage(
            file=str(self.controller.ASSETS_PATH / "image_BG_mask.png")
        )
        self.canvas.create_image(659.0, 360.0, image=self.image_image_2)

        self.image_image_3 = PhotoImage(
            file=str(self.controller.ASSETS_PATH / "image_Name.png")
        )
        self.canvas.create_image(84.0, 116.0, image=self.image_image_3)

        self.image_image_4 = PhotoImage(
            file=str(self.controller.ASSETS_PATH / "image_Welcome.png")
        )
        self.canvas.create_image(84.0, 82.0, image=self.image_image_4)

        self.image_image_5 = PhotoImage(
            file=str(self.controller.ASSETS_PATH / "image_Logo.png")
        )
        self.canvas.create_image(89.0, 39.0, image=self.image_image_5)

        self.canvas.create_text(
            206.0,
            56.0,
            anchor="nw",
            text="Welcome to Building Generator\nfor Falcon BMS ",
            fill="#000000",
            font=("Inter Bold", 17 * -1, "bold"),
        )

        self.canvas.create_text(
            221.0,
            127.0,
            anchor="nw",
            text="The following software designed to help theater \ncreators to construct custom Objectives, with \naccurate"
            " placement of buildings and features, from \na selected Database within BMS arsenal.\n\nTo be able"
            " to provide valid data please download \nQGIS and QuickOSM and other Buildings footprint \nextractors. \n\nTheater projection can be done through "
            "the software\nitself. Explanations will be offered in the ReadMe.pdf \nfile.\n",
            fill="#000000",
            font=("Inter Medium", 14 * -1),
        )

        self.image_image_6 = PhotoImage(
            file=str(self.controller.ASSETS_PATH / "image_6_dash.png")
        )
        self.canvas.create_image(837.0, 193.0, image=self.image_image_6)

        self.canvas.create_rectangle(
            584.4705810546875,
            107.22308349609375,
            1097,
            108.22308349609375,
            fill="#000000",
            outline="",
        )

        self.canvas.create_text(
            586.0,
            81.0,
            anchor="nw",
            text="Overview",
            fill="#000000",
            font=("Inter", 15 * -1),
        )

        # Add counters for generations and features
        self.generations_counter = tk.StringVar()
        self.features_counter = tk.StringVar()

        # Load statistics for the pie chart
        labels, sizes, features_counter, generations_counter = (
            self.load_statistics_for_chart()
        )
        # Set values for Counters
        self.generations_counter.set(generations_counter)
        self.features_counter.set(features_counter)

        pie_figure = Figure(figsize=(5, 5), dpi=40)
        chart = pie_figure.add_subplot(111)

        colors = [
            "#ff9999",
            "#66b3ff",
            "#99ff99",
            "#ffcc99",
            "#c2c2f0",
        ]  # Added a color for "Other"
        explode = (0.1, 0, 0, 0, 0)  # Added an explode value for "Other"

        # draw circle
        chart.pie(
            sizes,
            explode=explode,
            labels=labels,
            colors=colors,
            autopct="%1.1f%%",
            shadow=True,
            startangle=140,
            textprops={"fontsize": 16},
        )
        chart.axis("equal")

        # Create a canvas and add it to the frame
        self.pie_canvas = FigureCanvasTkAgg(pie_figure, self)
        self.pie_canvas.draw()
        self.pie_canvas.get_tk_widget().place(x=587, y=115)

        self.canvas.create_text(
            856.0,
            134,
            anchor="nw",
            text="Amount of \nGenerations \nprocessed: ",
            fill="#000000",
            font=("Inter", 14 * -1),
        )
        self.generations_label = tk.Label(
            self,
            textvariable=self.generations_counter,
            bg="#FFFFFF",
            font=("Inter", 30 * -1),
        )
        self.generations_label.place(x=950, y=134)

        self.canvas.create_text(
            856.0,
            224,
            anchor="nw",
            text="Amount of \nFeatures \nprocessed: ",
            fill="#000000",
            font=("Inter", 14 * -1),
        )
        self.features_label = tk.Label(
            self,
            textvariable=self.features_counter,
            bg="#FFFFFF",
            font=("Inter", 30 * -1),
        )
        self.features_label.place(x=950, y=224)

        self.image_image_7 = PhotoImage(
            file=str(self.controller.ASSETS_PATH / "image_7_dash.png")
        )
        self.canvas.create_image(838.0, 473.0, image=self.image_image_7)

        self.canvas.create_rectangle(
            581.0, 406.0, 1097, 407.0, fill="#000000", outline=""
        )

        self.canvas.create_text(
            586.0,
            381.0,
            anchor="nw",
            text="Database Detected",
            fill="#000000",
            font=("Inter", 15 * -1),
        )

        # Create table of available Databases in DatabasePage
        # Set Frame to the Table
        Dash_DBtable_frame = tk.Frame(self, bd=0, relief="flat", width=515, height=146)
        Dash_DBtable_frame.place(x=582, y=421)
        Dash_DBtable_frame.grid_propagate(0)
        # Add a Scrollbar to the Canvas
        vScrollDBTable = tk.Scrollbar(Dash_DBtable_frame, orient="vertical")
        vScrollDBTable.grid(row=0, column=1, sticky="ns")

        # Create the table
        self.Dash_DB_Table = ttk.Treeview(
            Dash_DBtable_frame,
            columns=("Idx", "BMS", "Theater"),
            show="headings",
            yscrollcommand=vScrollDBTable.set,
            height=5,
        )
        Col_Size = [25, 300, 185]
        for i, col in enumerate(("Idx", "BMS", "Theater")):
            self.Dash_DB_Table.column(col, width=Col_Size[i])
            self.Dash_DB_Table.heading(col, text=col)
        # Update Database table with the current state

        # Configure the scroll bar
        vScrollDBTable.config(command=self.Dash_DB_Table.yview)
        self.Dash_DB_Table.grid(row=0, column=0, sticky="nsew")

        self.image_image_8 = PhotoImage(
            file=str(self.controller.ASSETS_PATH / "image_8_dash.png")
        )
        self.canvas.create_image(370.0, 473.0, image=self.image_image_8)

        self.canvas.create_rectangle(
            235.0, 408.0, 506.7910461425781, 409.0, fill="#000000", outline=""
        )

        self.image_image_9 = PhotoImage(
            file=str(self.controller.ASSETS_PATH / "image_CT.png")
        )
        self.canvas.create_image(667.0, 631.0, image=self.image_image_9)

        # Label/Button Widget for transparent  box
        self.CTpath_box = tk.Label(
            self, textvariable=self.controller.shared_data["CTpath"]
        )
        self.CTpath_box.place(x=375.0, y=612.0, width=730.0, height=30.0)
        self.CTpath_box.bind(("<Button-1>"), self.controller.SelectCTfile)

        self.canvas.create_text(
            239.0,
            383.0,
            anchor="nw",
            text="BMS versions Detected",
            fill="#000000",
            font=("Inter", 15 * -1),
        )

        BMS_detection_frame = Ctk.CTkFrame(
            self, width=271, height=146, fg_color="#fcfcfd"
        )

        BMS_detection_frame.place(x=236, y=421)
        BMS_detection_frame.grid_propagate(0)

        # Will search for directories in the registry to show in the Dash
        BMS_directories = self.Get_Installed_BMS_versions()
        if len(BMS_directories) != 0:
            for labels in range(len(BMS_directories)):
                Ctk.CTkButton(
                    BMS_detection_frame,
                    text=BMS_directories[labels],
                    font=self.button_font,
                    fg_color="transparent",
                    text_color="#000000",
                    corner_radius=0,
                    hover_color="#A0B9D0",
                ).grid(row=labels, column=0, sticky="nsew")
        # If paths hasnt been found, present fail message
        else:
            Ctk.CTkButton(
                BMS_detection_frame,
                text="No Falcon BMS installations detected",
                font=self.button_font,
                fg_color="#A1B9D0",
                corner_radius=0,
                hover_color="#A0B9D0",
            ).grid(row=0, column=0, sticky="we")
        self.image_image_11 = PhotoImage(
            file=str(self.controller.ASSETS_PATH / "image_BMSver.png")
        )
        self.canvas.create_image(566.0, 681.0, image=self.image_image_11)

        self.image_image_12 = PhotoImage(
            file=str(self.controller.ASSETS_PATH / "image_theater.png")
        )
        self.canvas.create_image(329.0, 682.0, image=self.image_image_12)

        self.theater_box = tk.Label(
            self,
            textvariable=self.controller.shared_data["Theater"],
            wraplength=100,
        )
        self.theater_box.place(x=310.0, y=663.0, width=112.0, height=28.0)
        self.theater_box.lift()

        self.BMSver_box = tk.Label(
            self,
            textvariable=self.controller.shared_data["BMS_version"],
            wraplength=100,
        )
        self.BMSver_box.place(x=555.0, y=663.0, width=112.0, height=28.0)
        self.BMSver_box.lift()

    def Get_Installed_BMS_versions(self):
        """The function looks at the registry path of BMS and extracting the baseDir file in every detected folder"""
        BMS_paths = []
        key = winreg.OpenKey(
            winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Benchmark Sims"
        )
        target_file = "baseDir"

        # Enumerate over installs folders
        i = 0
        while True:
            try:
                sub_folder_name = winreg.EnumKey(key, i)
                sub_folder_path = (
                    r"SOFTWARE\WOW6432Node\Benchmark Sims" + "\\" + sub_folder_name
                )
                sub_folder_key = winreg.OpenKey(
                    winreg.HKEY_LOCAL_MACHINE, sub_folder_path
                )

                # Enumerate over Files inside the sub folder
                j = 0
                while True:
                    try:
                        value_name, value_data, regtype = winreg.EnumValue(
                            sub_folder_key, j
                        )
                        if target_file == value_name:
                            BMS_paths.append(os.path.basename(value_data))
                        j += 1
                    except OSError:
                        break
                i += 1
            except OSError:
                break
        return BMS_paths

    def load_statistics_for_chart(self):
        logger = logging.getLogger(__name__)
        try:
            # Get the path to feature_statistics.json.gz in the data_components folder
            stats_path = get_json_path(JsonFiles.FEATURE_STATISTICS)
            
            # Open the file from the data_components folder
            with gzip.open(stats_path, "rt") as f:
                stats = json.load(f)
                
            feature_types = stats["feature_types"]
            total_features = stats["total_features"]
            total_usage = stats["total_usage"]

            # Convert keys to integers and values to integers
            feature_types = {int(k): int(v) for k, v in feature_types.items()}

            # Map type numbers to their names
            type_names = {
                1: "Carter",
                2: "Control Tower",
                3: "Barn",
                4: "Bunker",
                5: "Blush",
                6: "Factories",
                7: "Church",
                8: "City Hall",
                9: "Dock",
                10: "Depot",
                11: "Runway",
                12: "Warehouse",
                13: "Helipad",
                14: "Fuel Tanks",
                15: "Nuclear Plant",
                16: "Bridges",
                17: "Pier",
                18: "Power Pole",
                19: "Shops",
                20: "Power Tower",
                21: "Apartment",
                22: "House",
                23: "Power Plant",
                24: "Taxi Signs",
                25: "Nav Beacon",
                26: "Radar Site",
                27: "Craters",
                28: "Radars",
                29: "R Tower",
                30: "Taxiway",
                31: "Rail Terminal",
                32: "Refinery",
                33: "SAM",
                34: "Shed",
                35: "Barracks",
                36: "Tree",
                37: "Water Tower",
                38: "Town Hall",
                39: "Air Terminal",
                40: "Shrine",
                41: "Park",
                42: "Off Block",
                43: "TV Station",
                44: "Hotel",
                45: "Hangar",
                46: "Lights",
                47: "VASI",
                48: "Storage Tank",
                49: "Fence",
                50: "Parking Lot",
                51: "Smoke Stack",
                52: "Building",
                53: "Cooling Tower",
                54: "Cont Dome",
                55: "Guard House",
                56: "Transformer",
                57: "Ammo Dump",
                58: "Art Site",
                59: "Office",
                60: "Chemical Plant",
                61: "Tower",
                62: "Hospital",
                63: "Shops/Blocks",
                64: "Static",
                65: "Runway Marker",
                66: "Stadium",
                67: "Monument",
                68: "Arrestor Cable",
            }

            # Replace type numbers with type names
            named_feature_types = {
                type_names.get(k, f"Type {k}"): v for k, v in feature_types.items()
            }

            # Sort types by value (count) in descending order
            sorted_types = sorted(
                named_feature_types.items(), key=lambda x: x[1], reverse=True
            )

            # Get the top 4 feature types
            top_4_types = dict(sorted_types[:4])

            # Calculate the sum of the remaining types
            other_sum = sum(dict(sorted_types[4:]).values())

            # Add "Other" to the dictionary if there are more than 4 types
            if other_sum > 0:
                top_4_types["Other"] = other_sum

            labels = list(top_4_types.keys())
            sizes = list(top_4_types.values())

            return labels, sizes, total_features, total_usage
        except (FileNotFoundError, json.JSONDecodeError, ValueError) as e:
            logger.error(f"Error loading statistics: {e}")
            # Return default data if file not found, invalid, or conversion fails
            return (
                ["No Data", "No Data", "No Data", "No Data", "Other"],
                [1, 1, 1, 1, 1],
                0,
                0,
            )

    def update_pie_chart(self):
        labels, sizes, total_features, total_usage = self.load_statistics_for_chart()

        # Update counters
        self.controller.frames["DashboardPage"].generations_counter.set(
            str(total_usage)
        )
        self.controller.frames["DashboardPage"].features_counter.set(
            str(total_features)
        )

        pie_figure = Figure(figsize=(5, 5), dpi=40)
        chart = pie_figure.add_subplot(111)

        colors = [
            "#ff9999",
            "#66b3ff",
            "#99ff99",
            "#ffcc99",
            "#c2c2f0",
        ]  # Added a color for "Other"
        explode = (0.1, 0, 0, 0, 0)  # Added an explode value for "Other"

        chart.clear()
        chart.pie(
            sizes,
            explode=explode,
            labels=labels,
            colors=colors,
            autopct="%1.1f%%",
            shadow=True,
            startangle=140,
            textprops={"fontsize": 16},
        )
        chart.axis("equal")

        self.controller.frames["DashboardPage"].pie_canvas.figure = pie_figure
        self.controller.frames["DashboardPage"].pie_canvas.draw()


class DatabasePage(tk.Frame):
    def __init__(self, parent, controller):
        tk.Frame.__init__(self, parent)
        self.controller = controller

        self.Body_font = Ctk.CTkFont(family="Inter", size=15)
        self.Body_font_Bold = Ctk.CTkFont(family="Inter", size=15, weight="bold")
        self.button_font = Ctk.CTkFont(family="Inter", size=12)
        self.dash_font = Ctk.CTkFont(family="Inter", size=10)
        
        # Features dictionary mapping numeric type to descriptive names
        self.FEATURES = {
            "1": "Carter",
            "2": "Control Tower",
            "3": "Barn",
            "4": "Bunker",
            "5": "Blush",
            "6": "Factories",
            "7": "Church",
            "8": "City Hall",
            "9": "Dock",
            "10": "Depot",
            "11": "Runway",
            "12": "Warehouse",
            "13": "Helipad",
            "14": "Fuel Tanks",
            "15": "Nuclear Plant",
            "16": "Bridges",
            "17": "Pier",
            "18": "Power Pole",
            "19": "Shops",
            "20": "Power Tower",
            "21": "Apartment",
            "22": "House",
            "23": "Power Plant",
            "24": "Taxi Signs",
            "25": "Nav Beacon",
            "26": "Radar Site",
            "27": "Craters",
            "28": "Radars",
            "29": "R Tower",
            "30": "Taxiway",
            "31": "Rail Terminal",
            "32": "Refinery",
            "33": "SAM",
            "34": "Shed",
            "35": "Barracks",
            "36": "Tree",
            "37": "Water Tower",
            "38": "Town Hall",
            "39": "Air Terminal",
            "40": "Shrine",
            "41": "Park",
            "42": "Off Block",
            "43": "TV Station",
            "44": "Hotel",
            "45": "Hangar",
            "46": "Lights",
            "47": "VASI",
            "48": "Storage Tank",
            "49": "Fence",
            "50": "Parking Lot",
            "51": "Smoke Stack",
            "52": "Building",
            "53": "Cooling Tower",
            "54": "Cont Dome",
            "55": "Guard House",
            "56": "Transformer",
            "57": "Ammo Dump",
            "58": "Art Site",
            "59": "Office",
            "60": "Chemical Plant",
            "61": "Tower",
            "62": "Hospital",
            "63": "Shops/Blocks",
            "64": "Static",
            "65": "Runway Marker",
            "66": "Stadium",
            "67": "Monument",
            "68": "Arrestor Cable",
        }

        self.canvas = Canvas(
            self,
            bg="#FFFFFF",
            height=720,
            width=1152,
            bd=0,
            highlightthickness=0,
            relief="ridge",
        )

        self.canvas.place(x=0, y=0)
        self.canvas.create_rectangle(0.0, 0.0, 204.0, 720.0, fill="#A0B9D0", outline="")

        # Load button images using CTkImage
        self.button_operations_img = Ctk.CTkImage(
            light_image=Image.open(str(self.controller.ASSETS_PATH / "button_operations.png")),size=(21, 17)
        )
        self.button_geo_img = Ctk.CTkImage(
            light_image=Image.open(str(self.controller.ASSETS_PATH / "button_geo.png")),size=(21, 17)
        )
        self.button_data_img = Ctk.CTkImage(
            light_image=Image.open(str(self.controller.ASSETS_PATH / "button_data.png")),size=(21, 17)
        )
        self.button_dash_img = Ctk.CTkImage(
            light_image=Image.open(str(self.controller.ASSETS_PATH / "button_dash.png")),size=(21, 17)
        )
        self.button_settings_img = Ctk.CTkImage(
            light_image=Image.open(str(self.controller.ASSETS_PATH / "button_options.png")),size=(21, 17)
        )
        self.button_footprints_img = Ctk.CTkImage(
            light_image=Image.open(str(self.controller.ASSETS_PATH / "button_footprint.png")),
            size=(21, 17)
        ) 

        self.button_operations = Ctk.CTkButton(
            self,
            text="Operations",
            fg_color="#A1B9D0",
            bg_color="#A1B9D0",
            image=self.button_operations_img,
            height=33,
            width=167,
            command=lambda: controller.show_frame("OperationPage"),
            corner_radius=0,
            hover_color="#7A92A9",
            font=("arial", 15),
            text_color="#000000",
        )
        self.button_operations.place(x=0, y=397)

        # New FootPrints navigation button
        self.button_footprints = Ctk.CTkButton(
            self,
            text="FootPrints",
            fg_color="#A1B9D0",
            bg_color="#A1B9D0",
            image=self.button_footprints_img,
            height=33,
            width=167,
            command=lambda: controller.show_frame("FootPrintsPage"),
            corner_radius=0,
            hover_color="#7A92A9",
            font=("Sans Font", 15),
            text_color="#000000",
        )
        self.button_footprints.place(x=0, y=445)

        self.button_geo = Ctk.CTkButton(
            self,
            text="GeoData",
            fg_color="#A1B9D0",
            bg_color="#A1B9D0",
            image=self.button_geo_img,
            height=33,
            width=167,
            command=lambda: controller.show_frame("GeoDataPage"),
            corner_radius=0,
            hover_color="#7A92A9",
            font=("Sans Font", 15),
            text_color="#000000",
        )
        self.button_geo.place(x=0, y=349)

        self.button_data = Ctk.CTkButton(
            self,
            text="Database",
            fg_color="#7A92A9",
            bg_color="#7A92A9",
            image=self.button_data_img,
            height=33,
            width=167,
            corner_radius=0,
            hover=False,
            font=("Sans Font", 15),
            text_color="#000000",
        )
        self.button_data.place(x=0, y=297)

        self.button_dash = Ctk.CTkButton(
            self,
            text="DashBoard",
            fg_color="#A1B9D0",
            bg_color="#A1B9D0",
            image=self.button_dash_img,
            height=33,
            width=167,
            hover_color="#7A92A9",
            corner_radius=0,
            font=("Sans Font", 15),
            text_color="#000000",
            command=lambda: controller.show_frame("DashboardPage"),
        )

        self.button_dash.place(x=0, y=248)

        self.button_settings = Ctk.CTkButton(
            self,
            text="More\nSettings",
            fg_color="#778593",
            bg_color="#A1B9D0",
            image=self.button_settings_img,
            height=97,
            width=125,
            corner_radius=20,
            hover=False,
            font=("Sans Font", 16),
            text_color="#000000",
            command=self.controller.SettingWindow,
        )
        self.button_settings.place(x=14, y=581)

        self.button_GenerateDatabase = PhotoImage(
            file=str(self.controller.ASSETS_PATH / "Image_GenerateDatabase.png")
        )
        button_6 = Button(
            self,
            image=self.button_GenerateDatabase,
            borderwidth=0,
            highlightthickness=0,
            command=self.GenerateDatabase,
            relief="flat",
        )
        button_6.place(x=868.0, y=445.0)

        self.canvas.create_rectangle(
            172.0, 0.0, 1152.0, 720.0, fill="#A1B9D0", outline=""
        )

        self.image_image_1 = PhotoImage(
            file=str(self.controller.ASSETS_PATH / "image_BG.png")
        )
        self.canvas.create_image(659.0, 360.0, image=self.image_image_1)

        self.image_image_2 = PhotoImage(
            file=str(self.controller.ASSETS_PATH / "image_BG_mask.png")
        )
        self.canvas.create_image(659.0, 360.0, image=self.image_image_2)

        self.image_image_3 = PhotoImage(
            file=str(self.controller.ASSETS_PATH / "image_Name.png")
        )
        self.canvas.create_image(84.0, 116.0, image=self.image_image_3)

        self.image_image_4 = PhotoImage(
            file=str(self.controller.ASSETS_PATH / "image_Welcome.png")
        )
        self.canvas.create_image(84.0, 82.0, image=self.image_image_4)

        self.image_image_5 = PhotoImage(
            file=str(self.controller.ASSETS_PATH / "image_Logo.png")
        )
        self.canvas.create_image(89.0, 39.0, image=self.image_image_5)

        self.image_image_6 = PhotoImage(
            file=str(self.controller.ASSETS_PATH / "image_CT.png")
        )
        self.canvas.create_image(667.0, 631.0, image=self.image_image_6)

        # Label/Button Widget for transparent  box
        self.CTpath_box = tk.Label(
            self, textvariable=self.controller.shared_data["CTpath"]
        )
        self.CTpath_box.place(x=375.0, y=612.0, width=730.0, height=30.0)
        self.CTpath_box.bind(("<Button-1>"), self.controller.SelectCTfile)

        # Create table of opened features inside a database in DatabasePage
        # Set Frame to the Table
        ModelsTable_frame = tk.Frame(self, bd=0, relief="solid", width=558, height=410)
        ModelsTable_frame.place(x=247, y=110)
        ModelsTable_frame.grid_propagate(0)

        # Add a Scrollbar to the Canvas
        vScrollModelsTable = tk.Scrollbar(ModelsTable_frame, orient="vertical")
        vScrollModelsTable.grid(row=0, column=1, sticky="ns")

        # canvas_table.configure(yscrollcommand=vScrollModelsTable.set, xscrollcommand=hScrollModelsTable.set)
        # Create the table
        columns = [
            "ModelNumber",
            "Name",
            "Type",
            "CTNumber",
            "EntityIdx",
            "Height",
            "Width",
            "WidthOff",
            "Length",
            "LengthOff",
        ]
        self.ModelsTable = ttk.Treeview(
            ModelsTable_frame,
            columns=columns,
            show="headings",
            height=19,
            yscrollcommand=vScrollModelsTable.set,
        )
        self.ModelsTable.grid(row=0, column=0, sticky="nsew")

        # Configure the scroll bar
        vScrollModelsTable.config(command=self.ModelsTable.yview)

        # Set up sorting callback for columns
        for col in columns:
            self.ModelsTable.heading(
                col,
                text=col,
                command=lambda c=col: self.sort_column_models(self.ModelsTable, c),
            )

        for col in columns:
            self.ModelsTable.heading(col, text=col)
            if col == "Type":
                self.ModelsTable.column(col, width=85)
            elif col == "Name":
                self.ModelsTable.column(col, width=90)
            elif col == "ModelNumber":
                self.ModelsTable.column(col, width=45)
            elif col == "CTNumber" or col == "EntityIdx":
                self.ModelsTable.column(col, width=45)
            elif col in ["Width", "Length", "Height"]:
                self.ModelsTable.column(col, width=47)
            elif col in ["WidthOff", "LengthOff"]:
                self.ModelsTable.column(col, width=45)
            else:
                self.ModelsTable.column(col, width=45)

            # Insert basic data
            self.ModelsTable.insert(
                "",
                "end",
                values=["-", "-", "-", "-", "-", "-", "-", "-", "-", "-"],
            )

        self.image_image_7 = PhotoImage(
            file=str(self.controller.ASSETS_PATH / "Rectangle_DB_ListOfFeatures.png")
        )
        self.canvas.create_image(989.0, 208.0, image=self.image_image_7)

        self.canvas.create_rectangle(
            883.0,
            90.0,
            1096,
            91.0,
            fill="#000000",
            outline="",
        )

        self.canvas.create_text(
            912.0,
            68.0,
            anchor="nw",
            text="Available Databases",
            fill="#000000",
            font=("Inter", 15 * -1),
        )

        # label and Entry for amount of features
        self.label_features_amount = Ctk.CTkLabel(
            self, text="Amount of Features:", font=self.button_font, bg_color="#F8F9FB"
        )
        self.label_features_amount.place(x=247, y=523)
        self.textbox_features_amount = Ctk.CTkEntry(
            self,
            width=50,
            height=18,
            border_color="#D5E3F0",
            fg_color="#E7E7E7",
            placeholder_text="0",
            state="disabled",
        )
        self.textbox_features_amount.place(x=368, y=526)

        # label and Entry for average size of the features
        self.label_features_avg_size = Ctk.CTkLabel(
            self, text="Average Size:", font=self.button_font, bg_color="#F8F9FB"
        )
        self.label_features_avg_size.place(x=446, y=523)
        self.textbox_features_avg_size = Ctk.CTkEntry(
            self,
            width=90,
            height=18,
            border_color="#D5E3F0",
            fg_color="#E7E7E7",
            placeholder_text="0",
            state="disabled",
        )
        self.textbox_features_avg_size.place(x=531, y=526)

        # label and Entry for average height of the features
        self.label_features_max_height = Ctk.CTkLabel(
            self, text="Maximum Height:", font=self.button_font, bg_color="#F8F9FB"
        )
        self.label_features_max_height.place(x=649, y=523)
        self.textbox_features_max_height = Ctk.CTkEntry(
            self,
            width=49,
            height=18,
            border_color="#D5E3F0",
            fg_color="#E7E7E7",
            placeholder_text="0",
            state="disabled",
        )
        self.textbox_features_max_height.place(x=756, y=526)

        # Create table of available Databases in DatabasePage
        # Set Frame to the Table
        DBtable_frame = tk.Frame(self, bd=0, relief="solid", width=215, height=230)
        DBtable_frame.place(x=883, y=110)
        DBtable_frame.grid_propagate(0)
        # Add a Scrollbar to the Canvas
        vScrollDBTable = tk.Scrollbar(DBtable_frame, orient="vertical")
        vScrollDBTable.grid(row=0, column=1, sticky="ns")

        # Create the table
        self.DB_Table = ttk.Treeview(
            DBtable_frame,
            columns=("Idx", "BMS", "Theater"),
            show="headings",
            yscrollcommand=vScrollDBTable.set,
            height=10,
        )
        Col_Size = [24, 120, 65]
        for i, col in enumerate(("Idx", "BMS", "Theater")):
            self.DB_Table.column(col, width=Col_Size[i])
            self.DB_Table.heading(col, text=col)
        # Update Database table with the current state
        self.Udpate_existedDB_Tables()

        # Configure the scroll bar
        vScrollDBTable.config(command=self.DB_Table.yview)
        self.DB_Table.grid(row=0, column=0, sticky="nsew")

        self.image_image_8 = PhotoImage(
            file=str(self.controller.ASSETS_PATH / "Rectangle_DB.png")
        )
        self.canvas.create_image(528.0, 305.0, image=self.image_image_8)

        self.Rectangle_DB_1 = PhotoImage(
            file=str(self.controller.ASSETS_PATH / "Rectangle_DB_1.png")
        )
        self.canvas.create_image(989.0, 471.0, image=self.Rectangle_DB_1)

        self.canvas.create_rectangle(
            247.0, 90.0, 805.0, 91.0, fill="#000000", outline=""
        )

        self.canvas.create_text(
            280.0,
            68.0,
            anchor="nw",
            text="Databse Features List",
            fill="#000000",
            font=("Inter", 15 * -1),
        )
        
        # Search functionality
        search_frame = tk.Frame(self, bg="#FFFFFF")
        search_frame.place(x=650, y=65)
        
        tk.Label(search_frame, text="Search:", bg="#FFFFFF").pack(side="left")
        self.search_var = tk.StringVar()
        search_entry = Ctk.CTkEntry(search_frame, textvariable=self.search_var, width=106, height=15)
        search_entry.pack(side="left", padx=5)
        search_entry.bind("<KeyRelease>", lambda e: self.search_models_table())

        self.image_image_9 = PhotoImage(
            file=str(self.controller.ASSETS_PATH / "image_Geo_data.png")
        )
        self.canvas.create_image(895.0, 76.0, image=self.image_image_9)

        self.image_image_10 = PhotoImage(
            file=str(self.controller.ASSETS_PATH / "image_Data.png")
        )
        self.canvas.create_image(259.0, 75.0, image=self.image_image_10)

        self.image_available = PhotoImage(file=self.Check_Availability_Database())
        self.image_11 = self.canvas.create_image(
            989.0, 412.0, image=self.image_available
        )

        self.image_image_12 = PhotoImage(
            file=str(self.controller.ASSETS_PATH / "image_backupCT.png")
        )
        self.canvas.create_image(902.0, 682.0, image=self.image_image_12)

        # Label/Button Widget for transparent  box
        self.backupCTpath_box = tk.Label(
            self,
            textvariable=self.controller.shared_data["backup_CTpath"],
            wraplength=200,
        )
        self.backupCTpath_box.place(x=824.0, y=663.0, width=280.0, height=28.0)
        self.backupCTpath_box.bind(("<Button-1>"), self.SelectBackupCTfile)

        self.image_image_13 = PhotoImage(
            file=str(self.controller.ASSETS_PATH / "image_BMSver.png")
        )
        self.canvas.create_image(566.0, 681.0, image=self.image_image_13)

        self.image_image_14 = PhotoImage(
            file=str(self.controller.ASSETS_PATH / "image_theater.png")
        )
        self.canvas.create_image(329.0, 682.0, image=self.image_image_14)
        self.theater_box = tk.Label(
            self,
            textvariable=self.controller.shared_data["Theater"],
            wraplength=100,
        )
        self.theater_box.place(x=310.0, y=663.0, width=112.0, height=28.0)
        self.theater_box.lift()

        self.BMSver_box = tk.Label(
            self,
            textvariable=self.controller.shared_data["BMS_version"],
            wraplength=100,
        )
        self.BMSver_box.place(x=555.0, y=663.0, width=112.0, height=28.0)
        self.BMSver_box.lift()

    def sort_column_models(self, tree, col, reverse=False):
        """Sort the data in the given column based on appropriate data type.
        
        Args:
            tree: The treeview widget
            col: The column to sort
            reverse: Whether to reverse the sort order
        """
        # Integer columns
        if col in ["ModelNumber", "CTNumber", "EntityIdx"]:
            data = []
            for item in tree.get_children(""):
                # Handle empty or invalid values
                try:
                    value = int(tree.set(item, col))
                except ValueError:
                    value = -1  # Default value for invalid entries
                data.append((value, item))
                
        # Float columns (measurements)
        elif col in ["Width", "WidthOff", "Length", "LengthOff", "Height"]:
            data = []
            for item in tree.get_children(""):
                try:
                    value = float(tree.set(item, col))
                except ValueError:
                    value = -1.0  # Default value for invalid entries
                data.append((value, item))
                
        # String columns (Name, Type)
        else:
            data = [(tree.set(item, col).lower(), item) for item in tree.get_children("")]

        # Sort the data
        data.sort(reverse=reverse)
        
        # Rearrange items in sorted positions
        for idx, (_, item) in enumerate(data):
            tree.move(item, "", idx)

        # Reverse sort next time
        tree.heading(col, command=lambda c=col: self.sort_column_models(tree, c, not reverse))

    def Check_Availability_Database(self):
        """the function will check if BMS_DB with correlated names (to the main CT path) is available,
        "Database_Availability" variable will be changed to 0/1 according to the availability
        if available: will send back a path of the picture that need to be loaded in the page"""
        # Get names of the installation and theater
        Installation = self.controller.shared_data["BMS_version"].get()
        theater = self.controller.shared_data["Theater"].get()

        # If both names are unknown then there is no db
        if theater == "N/A" and Installation == "N/A":
            self.controller.shared_data["Database_Availability"].set("0")
            return str(self.controller.ASSETS_PATH / "Image_not_Available.png")

        if Installation == "N/A":
            Installation = "Unknown"  # Set installation status for the function

        try:
            file_path = str(
                # Path(__file__).parent
                Path(r"Database") / Installation / theater / "Database.db"
            )
            if os.path.isfile(file_path):
                self.controller.shared_data["BMS_Database_Path"].set(file_path)
                self.controller.shared_data["Database_Availability"].set("1")
                return str(self.controller.ASSETS_PATH / "Image_Available.png")
            else:
                self.controller.shared_data["Database_Availability"].set("0")
                self.controller.shared_data["BMS_Database_Path"].set("")
                return str(self.controller.ASSETS_PATH / "Image_not_Available.png")
        except ValueError:
            self.controller.shared_data["Database_Availability"].set("0")
            self.controller.shared_data["BMS_Database_Path"].set("")
            return str(self.controller.ASSETS_PATH / "Image_not_Available.png")

    def UdpateDB_Tables(self):
        """the function will update tables if database is found"""
        # Erase all data
        for row in self.ModelsTable.get_children():
            self.ModelsTable.delete(row)

        data = self.controller.shared_data["BMS_Databse"]
        # Amount and information variables
        features_amount = len(data)
        avg_size = (data["Width"] * data["Length"]).mean()
        max_height = (data["Height"]).max()

        # Update the Table with the features information
        for i in range(features_amount):
            list_data = list(data.iloc[i])
            # round the decimal numbers to 3, for better veiwing the data on the dable
            for col in range(7, 12):
                list_data[col] = round(list_data[col], 3)
                
            # Convert numeric Type to descriptive name
            type_num = str(list_data[4])
            type_name = self.FEATURES.get(type_num, f"Type {type_num}")
            list_data[4] = type_name
            
            # Exclude "Class" and "Domain" columns and "LengthIdx"
            list_data = [
                list_data[0],  # ModelNumber
                list_data[1],  # Name
                list_data[4],  # Type (now descriptive)
                list_data[5],  # CTNumber
                list_data[6],  # EntityIdx
                list_data[11],  # Height
                list_data[7],  # Width
                list_data[8],  # WidthOff
                list_data[9], # Length
                list_data[10], # LengthOff
            ]
            self.ModelsTable.insert("", "end", values=list_data)

        # make entries open
        self.textbox_features_amount.configure(state="normal")
        self.textbox_features_max_height.configure(state="normal")
        self.textbox_features_avg_size.configure(state="normal")

        # Update Enteties to the GUI
        if len(self.textbox_features_amount.get()) > 0:
            self.textbox_features_amount.delete(0, "end")
        self.textbox_features_amount.insert(0, str(features_amount))

        if len(self.textbox_features_avg_size.get()) > 0:
            self.textbox_features_avg_size.delete(0, "end")
        self.textbox_features_avg_size.insert(0, str(round(avg_size, 2)))

        if len(self.textbox_features_max_height.get()) > 0:
            self.textbox_features_max_height.delete(0, "end")
        self.textbox_features_max_height.insert(0, str(round(max_height, 2)))

        # make entries disable
        self.textbox_features_amount.configure(state="disabled")
        self.textbox_features_max_height.configure(state="disabled")
        self.textbox_features_avg_size.configure(state="disabled")

    def Udpate_existedDB_Tables(self):
        """the function will update table of existing databases in the "Database" folder"""
        # Erase all data in the exsisting database lists
        for row in self.DB_Table.get_children():
            self.DB_Table.delete(row)
            self.controller.frames["DashboardPage"].Dash_DB_Table.delete(row)

        main_path = Path(r"Database")
        # main_path = str(Path(__file__).parent / "Database")
        data = []
        idx = 1
        # go over all the folders in "Database" folder, and if "db" ending is found, the 2 folders
        # would be noted in list, and then will be inserted to data variable (list of lists)
        for root, dirs, files in os.walk(main_path):
            for file in files:
                if file.lower().endswith(".db"):
                    # Normalize the path to remove trailing slashes
                    normalized_path = os.path.normpath(root)
                    # split the path into components
                    components = normalized_path.split(os.path.sep)
                    data.append([idx, components[-2], components[-1]])
                    idx += 1

        # insert data list into the table
        for i in range(len(data)):
            self.DB_Table.insert("", "end", values=data[i])
            self.controller.frames["DashboardPage"].Dash_DB_Table.insert(
                "", "end", values=data[i]
            )

    def GenerateDatabase(self):
        """Function takes the chosen theater and BMS version and check if database is already existing
        if not, it will create folders with the relevant path and place the new database there"""
        # Create a logger for this function
        logger = logging.getLogger(__name__)
        
        if self.controller.shared_data["CTpath"].get() == "No CT file selected":
            logger.warning("Database generation aborted: No CT file selected")
            return messagebox.showwarning(
                "Procedure Aborted", "Class Table XML has not been selected."
            )

        # Check version and theater of XML base folder
        ownPath = Path(r"")
        # ownPath = str(Path(__file__).parent)
        if self.controller.shared_data["Theater"].get() == "N/A":
            Theater = "N_A"
        else:
            Theater = self.controller.shared_data["Theater"].get()

        if self.controller.shared_data["BMS_version"].get() == "N/A":
            BMSVer = "N_A"
        else:
            BMSVer = self.controller.shared_data["BMS_version"].get()

        # Set folders and generate data
        backup_CT_path = self.controller.shared_data["backup_CTpath"].get()
        db_path = os.path.join(ownPath, "Database", BMSVer, Theater, "database.db")
        db_save_path = os.path.join(ownPath, "Database", BMSVer, Theater)
        
        # Import the processing window functionality
        from processing_window import run_with_processing
        
        # Gather all needed parameters
        CT_path = self.controller.shared_data["CTpath"].get()
        
        # If db is detected in the detected folder, ask if you want to rewrite BEFORE starting the processing window
        if os.path.isfile(db_path):
            logger.info(f"Existing database found at {db_path}")
            result = messagebox.askyesno(
                "Warning", "Suited Database has been found. Do you want to override it?"
            )
            if not result:
                logger.info("User chose not to override existing database")
                messagebox.showwarning(
                    "Procedure Aborted", "The Database generating has been aborted."
                )
                return
            logger.info("User chose to override existing database")
                
        try:
            # Define the database generation task that will run in the background thread
            def database_task(processing_window):
                try:
                    # Log action with appropriate logger
                    logger.info("Starting database generation process")
                    logger.info(f"Using CT path: {CT_path}")
                    logger.info(f"Using backup CT path: {backup_CT_path}")
                    logger.info(f"Saving to: {db_save_path}")
                    
                    # Call the GenerateDB function - logging is configured at application level
                    GenerateDB(CT_path, db_save_path, backup_CT_path)
                    
                    # Return success
                    logger.info("Database generation completed successfully")
                    return True
                except Exception as e:
                    import traceback
                    error_details = traceback.format_exc()
                    logger.error(f"Database generation error: {str(e)}")
                    logger.debug(f"Error details: {error_details}")
                    raise
            
            # Run the database task with a processing window
            logger.info("Launching database generation with processing window")
            result = run_with_processing(
                parent=self.controller,
                task_function=database_task,
                title="Generating Database",
                message="Initializing database generation..."
            )
            
            # Check if the result is valid
            if result is None or result is False:
                logger.error(f"Invalid result from database generation: {result}")
                return messagebox.showerror("Error", "Failed to generate database. Check the logs for details.")
            
            # Update the UI after successful completion
            logger.info("Updating UI with new database information")
            self.NewDBupdate()
            self.Udpate_existedDB_Tables()
            
            messagebox.showinfo(
                "Success", "Database has been generated successfully"
            )
            
        except Exception as e:
            logger.error(f"Database generation failed with error: {str(e)}")
            messagebox.showwarning("Procedure Aborted", f"Error has occurred: {str(e)}")


    def NewDBupdate(self):
        """The function should be called after successful run of generating DB
        ** Tables will get update by the new data
        ** Image change to "available"
        ** DB path shared
        ** Array of the DB shared"""
        ImagePath = self.Check_Availability_Database()

        # Update Un/Availability picture of Database which loaded through CT XML file
        self.image_available = PhotoImage(file=ImagePath)
        self.image_11 = self.controller.frames["DatabasePage"].canvas.create_image(
            989.0, 412.0, image=self.image_available
        )
        # Get Database and present it in table
        DB_path = self.controller.shared_data["BMS_Database_Path"].get()
        if DB_path:
            array = Load_Db(DB_path, "All")
            self.controller.shared_data["BMS_Databse"] = array
            self.controller.frames["DatabasePage"].UdpateDB_Tables()

    def SelectBackupCTfile(self, event):
        # open a file dialog and update the label text with the selected file path
        file_path = tkinter.filedialog.askopenfilename(
            filetypes=[("Class-Table files", "*.xml")]
        )
        if file_path:
            self.controller.shared_data["backup_CTpath"].set(file_path)

        # if path is not selected
        else:
            self.controller.shared_data["backup_CTpath"].set("No CT file selected")

    def search_models_table(self):
        """Search the database table for matching items"""
        query = self.search_var.get()
        
        if not query:
            # If search is empty, restore the original data
            self.UdpateDB_Tables()
            return
            
        # Convert query to lowercase for case-insensitive search
        query = query.lower()
        
        # Get all items from the original data
        original_data = self.controller.shared_data["BMS_Databse"]
        
        # Clear the current tree
        for row in self.ModelsTable.get_children():
            self.ModelsTable.delete(row)
            
        # Search through all items for matches in any column
        for i in range(len(original_data)):
            row_data = original_data.iloc[i]
            # Convert all values to strings for searching
            row_values = [str(val).lower() for val in row_data.values]
            
            # Check if the query is in any of the columns
            if any(query in val for val in row_values):
                # Format the data for display
                list_data = list(row_data)
                
                # Round decimal values for better viewing
                for col in range(7, 12):
                    list_data[col] = round(list_data[col], 3)
                    
                # Format Type column
                type_num = str(list_data[4])
                type_name = self.FEATURES.get(type_num, f"Type {type_num}")
                list_data[4] = type_name
                
                # Prepare the values to display (same order as in UdpateDB_Tables method)
                display_values = [
                    list_data[0],  # ModelNumber
                    list_data[1],  # Name
                    list_data[4],  # Type (now descriptive)
                    list_data[5],  # CTNumber
                    list_data[6],  # EntityIdx
                    list_data[11], # Height
                    list_data[7],  # Width
                    list_data[8],  # WidthOff
                    list_data[9],  # Length
                    list_data[10], # LengthOff
                ]
                
                # Insert the matching item
                self.ModelsTable.insert("", "end", values=display_values)


class GeoDataPage(tk.Frame):
    def __init__(self, parent, controller):
        tk.Frame.__init__(self, parent)
        self.controller = controller

        self.Body_font = Ctk.CTkFont(family="Inter", size=15)
        self.Body_font_Bold = Ctk.CTkFont(family="Inter", size=15, weight="bold")
        self.button_font = Ctk.CTkFont(family="Inter", size=12)
        self.dash_font = Ctk.CTkFont(family="Inter", size=10)

        self.canvas = Canvas(
            self,
            bg="#FFFFFF",
            height=720,
            width=1152,
            bd=0,
            highlightthickness=0,
            relief="ridge",
        )

        self.canvas.place(x=0, y=0)
        self.canvas.create_rectangle(0.0, 0.0, 204.0, 720.0, fill="#A0B9D0", outline="")

        # Load button images using CTkImage
        self.button_operations_img = Ctk.CTkImage(
            light_image=Image.open(str(self.controller.ASSETS_PATH / "button_operations.png")),size=(21, 17)
        )
        self.button_geo_img = Ctk.CTkImage(
            light_image=Image.open(str(self.controller.ASSETS_PATH / "button_geo.png")),size=(21, 17)
        )
        self.button_data_img = Ctk.CTkImage(
            light_image=Image.open(str(self.controller.ASSETS_PATH / "button_data.png")),size=(21, 17)
        )
        self.button_dash_img = Ctk.CTkImage(
            light_image=Image.open(str(self.controller.ASSETS_PATH / "button_dash.png")),size=(21, 17)
        )
        self.button_settings_img = Ctk.CTkImage(
            light_image=Image.open(str(self.controller.ASSETS_PATH / "button_options.png")),size=(21, 17)
        )
        self.button_footprints_img = Ctk.CTkImage(
            light_image=Image.open(str(self.controller.ASSETS_PATH / "button_footprint.png")),
            size=(21, 17)
        )

        self.button_operations = Ctk.CTkButton(
            self,
            text="Operations",
            fg_color="#A1B9D0",
            bg_color="#A1B9D0",
            image=self.button_operations_img,
            height=33,
            width=167,
            command=lambda: controller.show_frame("OperationPage"),
            corner_radius=0,
            hover_color="#7A92A9",
            font=("arial", 15),
            text_color="#000000",
        )
        self.button_operations.place(x=0, y=397)

        # New FootPrints navigation button
        self.button_footprints = Ctk.CTkButton(
            self,
            text="FootPrints",
            fg_color="#A1B9D0",
            bg_color="#A1B9D0",
            image=self.button_footprints_img,
            height=33,
            width=167,
            command=lambda: controller.show_frame("FootPrintsPage"),
            corner_radius=0,
            hover_color="#7A92A9",
            font=("Sans Font", 15),
            text_color="#000000",
        )
        self.button_footprints.place(x=0, y=445)

        self.button_geo = Ctk.CTkButton(
            self,
            text="GeoData",
            fg_color="#7A92A9",
            bg_color="#7A92A9",
            image=self.button_geo_img,
            height=33,
            width=167,
            corner_radius=0,
            hover=False,
            font=("Sans Font", 15),
            text_color="#000000",
        )
        self.button_geo.place(x=0, y=349)

        self.button_data = Ctk.CTkButton(
            self,
            text="Database",
            fg_color="#A1B9D0",
            bg_color="#A1B9D0",
            image=self.button_data_img,
            height=33,
            width=167,
            command=lambda: controller.show_frame("DatabasePage"),
            corner_radius=0,
            hover_color="#7A92A9",
            font=("arial", 15),
            text_color="#000000",
        )
        self.button_data.place(x=0, y=297)

        self.button_dash = Ctk.CTkButton(
            self,
            text="DashBoard",
            fg_color="#A1B9D0",
            bg_color="#A1B9D0",
            image=self.button_dash_img,
            height=33,
            width=167,
            hover_color="#7A92A9",
            corner_radius=0,
            font=("Sans Font", 15),
            text_color="#000000",
            command=lambda: controller.show_frame("DashboardPage"),
        )
        self.button_dash.place(x=0, y=248)

        self.button_settings = Ctk.CTkButton(
            self,
            text="More\nSettings",
            fg_color="#778593",
            bg_color="#A1B9D0",
            image=self.button_settings_img,
            height=97,
            width=125,
            corner_radius=20,
            hover=False,
            font=("Sans Font", 16),
            text_color="#000000",
            command=self.controller.SettingWindow,
        )
        self.button_settings.place(x=14, y=581)

        self.canvas.create_rectangle(
            172.0, 0.0, 1152.0, 720.0, fill="#A1B9D0", outline=""
        )

        self.image_image_1 = PhotoImage(
            file=str(self.controller.ASSETS_PATH / "image_BG.png")
        )
        self.canvas.create_image(659.0, 360.0, image=self.image_image_1)

        self.image_image_2 = PhotoImage(
            file=str(self.controller.ASSETS_PATH / "image_BG_mask.png")
        )
        self.canvas.create_image(659.0, 360.0, image=self.image_image_2)

        self.image_image_3 = PhotoImage(
            file=str(self.controller.ASSETS_PATH / "image_Name.png")
        )
        self.canvas.create_image(84.0, 116.0, image=self.image_image_3)

        self.image_image_4 = PhotoImage(
            file=str(self.controller.ASSETS_PATH / "image_Welcome.png")
        )
        self.canvas.create_image(84.0, 82.0, image=self.image_image_4)

        self.image_image_5 = PhotoImage(
            file=str(self.controller.ASSETS_PATH / "image_Logo.png")
        )
        self.canvas.create_image(89.0, 39.0, image=self.image_image_5)

        self.image_image_6 = PhotoImage(
            file=str(self.controller.ASSETS_PATH / "image_CT.png")
        )
        self.canvas.create_image(667.0, 631.0, image=self.image_image_6)

        # Label/Button Widget for transparent  box
        self.CTpath_box = tk.Label(
            self, textvariable=self.controller.shared_data["CTpath"]
        )
        self.CTpath_box.place(x=375.0, y=612.0, width=730.0, height=30.0)
        self.CTpath_box.bind(("<Button-1>"), self.controller.SelectCTfile)

        # Load button images using CTkImage
        self.button_operations_img = Ctk.CTkImage(
            light_image=Image.open(str(self.controller.ASSETS_PATH / "button_operations.png")),size=(21, 17)
        )
        self.button_geo_img = Ctk.CTkImage(
            light_image=Image.open(str(self.controller.ASSETS_PATH / "button_geo.png")),size=(21, 17)
        )
        self.button_data_img = Ctk.CTkImage(
            light_image=Image.open(str(self.controller.ASSETS_PATH / "button_data.png")),size=(21, 17)
        )
        self.button_dash_img = Ctk.CTkImage(
            light_image=Image.open(str(self.controller.ASSETS_PATH / "button_dash.png")),size=(21, 17)
        )
        self.button_settings_img = Ctk.CTkImage(
            light_image=Image.open(str(self.controller.ASSETS_PATH / "button_options.png")),size=(21, 17)
        )
        self.button_footprints_img = Ctk.CTkImage(
            light_image=Image.open(str(self.controller.ASSETS_PATH / "button_footprint.png")),
            size=(21, 17)
        )

        self.button_operations = Ctk.CTkButton(
            self,
            text="Operations",
            fg_color="#A1B9D0",
            bg_color="#A1B9D0",
            image=self.button_operations_img,
            height=33,
            width=167,
            command=lambda: controller.show_frame("OperationPage"),
            corner_radius=0,
            hover_color="#7A92A9",
            font=("arial", 15),
            text_color="#000000",
        )
        self.button_operations.place(x=0, y=397)

        self.button_geo = Ctk.CTkButton(
            self,
            text="GeoData",
            fg_color="#7A92A9",
            bg_color="#7A92A9",
            image=self.button_geo_img,
            height=33,
            width=167,
            corner_radius=0,
            hover=False,
            font=("Sans Font", 15),
            text_color="#000000",
        )
        self.button_geo.place(x=0, y=349)

        self.button_data = Ctk.CTkButton(
            self,
            text="Database",
            fg_color="#A1B9D0",
            bg_color="#A1B9D0",
            image=self.button_data_img,
            height=33,
            width=167,
            command=lambda: controller.show_frame("DatabasePage"),
            corner_radius=0,
            hover_color="#7A92A9",
            font=("arial", 15),
            text_color="#000000",
        )
        self.button_data.place(x=0, y=297)

        self.button_dash = Ctk.CTkButton(
            self,
            text="DashBoard",
            fg_color="#A1B9D0",
            bg_color="#A1B9D0",
            image=self.button_dash_img,
            height=33,
            width=167,
            hover_color="#7A92A9",
            corner_radius=0,
            font=("Sans Font", 15),
            text_color="#000000",
            command=lambda: controller.show_frame("DashboardPage"),
        )
        self.button_dash.place(x=0, y=248)

        self.button_settings = Ctk.CTkButton(
            self,
            text="More\nSettings",
            fg_color="#778593",
            bg_color="#A1B9D0",
            image=self.button_settings_img,
            height=97,
            width=125,
            corner_radius=20,
            hover=False,
            font=("Sans Font", 16),
            text_color="#000000",
            command=self.controller.SettingWindow,
        )
        self.button_settings.place(x=14, y=581)

        self.canvas.create_rectangle(
            172.0, 0.0, 1152.0, 720.0, fill="#A1B9D0", outline=""
        )

        self.image_image_1 = PhotoImage(
            file=str(self.controller.ASSETS_PATH / "image_BG.png")
        )
        self.canvas.create_image(659.0, 360.0, image=self.image_image_1)

        self.image_image_2 = PhotoImage(
            file=str(self.controller.ASSETS_PATH / "image_BG_mask.png")
        )
        self.canvas.create_image(659.0, 360.0, image=self.image_image_2)

        self.image_image_3 = PhotoImage(
            file=str(self.controller.ASSETS_PATH / "image_Name.png")
        )
        self.canvas.create_image(84.0, 116.0, image=self.image_image_3)

        self.image_image_4 = PhotoImage(
            file=str(self.controller.ASSETS_PATH / "image_Welcome.png")
        )
        self.canvas.create_image(84.0, 82.0, image=self.image_image_4)

        self.image_image_5 = PhotoImage(
            file=str(self.controller.ASSETS_PATH / "image_Logo.png")
        )
        self.canvas.create_image(89.0, 39.0, image=self.image_image_5)

        self.image_image_6 = PhotoImage(
            file=str(self.controller.ASSETS_PATH / "image_CT.png")
        )
        self.canvas.create_image(667.0, 631.0, image=self.image_image_6)

        # Label/Button Widget for transparent  box
        self.CTpath_box = tk.Label(
            self, textvariable=self.controller.shared_data["CTpath"]
        )
        self.CTpath_box.place(x=375.0, y=612.0, width=730.0, height=30.0)
        self.CTpath_box.bind(("<Button-1>"), self.controller.SelectCTfile)

        self.image_image_7 = PhotoImage(
            file=str(self.controller.ASSETS_PATH / "image_GeoJson.png")
        )
        self.canvas.create_image(667.0, 581.0, image=self.image_image_7)

        # Label/Button Widget for transparent  box
        # self.GeoJson_path = "No GeoJson file selected"
        self.GeoJsonPath_box = tk.Label(
            self, textvariable=self.controller.shared_data["Geopath"]
        )
        self.GeoJsonPath_box.place(x=375.0, y=562.0, width=730.0, height=30.0)
        self.GeoJsonPath_box.bind(("<Button-1>"), self.SelectGeoJsonFile)

        # Load button to apply the main function of loading Geo data
        self.GeoJsonPath_loadButton = Ctk.CTkButton(
            self,
            text="Load",
            fg_color="#D5E3F0",
            bg_color="#f0f0f0",
            command=self.CalculateGeo,
            height=29,
            width=113,
            corner_radius=20,
            font=("Sans Font", 15),
            text_color="#000000",
        )
        self.GeoJsonPath_loadButton.place(x=993, y=563)

        # label and Entry for amount of structures
        self.label_structures_amount = Ctk.CTkLabel(
            self,
            text="Structures:",
            font=self.button_font,
            bg_color="#F8F9FB",
        )
        self.label_structures_amount.place(x=247, y=486)

        self.textbox_structures_amount = Ctk.CTkEntry(
            self,
            width=50,
            height=18,
            border_color="#D5E3F0",
            fg_color="#E7E7E7",
            placeholder_text="0",
            state="disabled",
        )
        self.textbox_structures_amount.place(x=321, y=489)

        # label and Entry for detailed structures
        self.label_structures_detailed = Ctk.CTkLabel(
            self, text="Detailed:", font=self.button_font, bg_color="#F8F9FB"
        )
        self.label_structures_detailed.place(x=400, y=486)
        self.textbox_structures_detailed = Ctk.CTkEntry(
            self,
            width=50,
            height=18,
            border_color="#D5E3F0",
            fg_color="#E7E7E7",
            placeholder_text="0",
            state="disabled",
        )
        self.textbox_structures_detailed.place(x=464, y=489)

        # label and Entry for structures_center
        self.label_structures_center = Ctk.CTkLabel(
            self, text="Center:", font=self.button_font, bg_color="#EEEEEE"
        )
        self.label_structures_center.place(x=544, y=486)
        self.textbox_structures_center = Ctk.CTkEntry(
            self,
            width=180,
            height=18,
            border_color="#D5E3F0",
            fg_color="#E7E7E7",
            placeholder_text="XXXX/YYYY",
        )
        self.textbox_structures_center.place(x=599, y=489)
        self.textbox_structures_center.configure(state="disabled")

        # label and Entry for structures_center
        self.label_floor_height = Ctk.CTkLabel(
            self, text="Floor Height[m]:", font=self.button_font, bg_color="#F8F6F9"
        )
        self.label_floor_height.place(x=809, y=486)
        self.textbox_floor_height = Ctk.CTkEntry(
            self,
            width=60,
            height=18,
            border_color="#D5E3F0",
            fg_color="#E7E7E7",
            placeholder_text="2.286",
        )
        self.textbox_floor_height.place(x=905, y=489)

        # Load button to apply the main function of loading Geo data
        self.osm_legend_window = Ctk.CTkButton(
            self,
            text="OSM Legend",
            fg_color="#D5E3F0",
            bg_color="#f0f0f0",
            command=self.osm_legend_class,
            height=25,
            width=100,
            corner_radius=15,
            font=("Sans Font", 15),
            text_color="#000000",
        )
        self.osm_legend_window.place(x=973, y=488)

        self.image_image_8 = PhotoImage(
            file=str(self.controller.ASSETS_PATH / "Rectrangle_Geo.png")
        )
        self.canvas.create_image(667.0, 286.0, image=self.image_image_8)

        self.canvas.create_rectangle(
            247.0, 90.0, 1094.0, 91.0, fill="#000000", outline=""
        )

        self.canvas.create_text(
            280.0,
            68.0,
            anchor="nw",
            text="GeographicalData Buildings list",
            fill="#000000",
            font=("Sans Font", 15 * -1),
        )

        # Create table of opened features inside a database in DatabasePage
        # Set Frame to the Table
        GeoTable_frame = tk.Frame(self, bd=0, relief="solid", width=847, height=367)
        GeoTable_frame.place(x=247.0, y=110)
        GeoTable_frame.grid_propagate(0)

        # Add a Scrollbar to the Canvas
        vScrollGeoTable = tk.Scrollbar(GeoTable_frame, orient="vertical")
        vScrollGeoTable.grid(row=0, column=1, sticky="ns")

        # Create the table
        columns = [
            "Index",
            "Name",
            "Length",
            "Width",
            "Rotation",
            "Center",
            "Type",
            "Levels",
            "Height",
            "Aeroway",
            "Amenity",
            "Barrier",
            "BMS",
            "Bridge",
            "Building",
            "Diplomatic",
            "Leisure",
            "Man Made",
            "Military",
            "Office",
            "Power",
            "Religion",
            "Service",
            "Sport",
        ]
        self.GeoTable = ttk.Treeview(
            GeoTable_frame,
            columns=columns,
            show="headings",
            height=17,
            yscrollcommand=vScrollGeoTable.set,
        )
        self.GeoTable.grid(row=0, column=0, sticky="nsew")

        # Configure the scroll bar
        vScrollGeoTable.config(command=self.GeoTable.yview)

        # Set up sorting callback for columns
        for col in columns:
            self.GeoTable.heading(
                col,
                text=col,
                command=lambda c=col: self.sort_column_geo(self.GeoTable, c),
            )

        for col in columns:
            self.GeoTable.heading(col, text=col)
            # Place Sizes of columns better
            if col == "Index":
                self.GeoTable.column(col, width=28)
            elif col == "Levels":
                self.GeoTable.column(col, width=10)
            else:
                self.GeoTable.column(col, width=36)
            self.GeoTable.insert(
                "",
                "end",
                values=[
                    "-",
                    "-",
                    "-",
                    "-",
                    "-",
                    "-",
                    "-",
                    "-",
                    "-",
                    "-",
                    "-",
                    "-",
                    "-",
                    "-",
                    "-",
                    "-",
                    "-",
                    "-",
                    "-",
                    "-",
                    "-",
                    "-",
                    "-",
                ],
            )

        self.image_image_9 = PhotoImage(
            file=str(self.controller.ASSETS_PATH / "image_Features.png")
        )
        self.canvas.create_image(259.0, 74.0, image=self.image_image_9)

        self.image_image_10 = PhotoImage(
            file=str(self.controller.ASSETS_PATH / "image_Projection.png")
        )
        self.projection_field = self.canvas.create_image(
            902.0, 682.0, image=self.image_image_10
        )
        # Label/Button Widget for transparent  box
        self.projection_field_label = tk.Label(
            self,
            textvariable=self.controller.shared_data["projection_path"],
            wraplength=200,
        )
        self.projection_field_label.place(x=824.0, y=663.0, width=280.0, height=28.0)
        self.projection_field_label.bind(("<Button-1>"), self.SelectProjectionfile)

        self.image_image_11 = PhotoImage(
            file=str(self.controller.ASSETS_PATH / "image_BMSver.png")
        )
        self.canvas.create_image(566.0, 681.0, image=self.image_image_11)

        self.image_image_12 = PhotoImage(
            file=str(self.controller.ASSETS_PATH / "image_theater.png")
        )
        self.canvas.create_image(329.0, 682.0, image=self.image_image_12)

        self.theater_box = tk.Label(
            self,
            textvariable=self.controller.shared_data["Theater"],
            wraplength=100,
        )
        self.theater_box.place(x=310.0, y=663.0, width=112.0, height=28.0)
        self.theater_box.lift()

        self.BMSver_box = tk.Label(
            self,
            textvariable=self.controller.shared_data["BMS_version"],
            wraplength=100,
        )
        self.BMSver_box.place(x=555.0, y=663.0, width=112.0, height=28.0)
        self.BMSver_box.lift()

    def osm_legend_class(self):
        OSMLegend.OSMLegend()

    def sort_column_geo(self, tree, col, reverse=False):
        """Sort the data in the given column based on appropriate data type.
        
        Args:
            tree: The treeview widget
            col: The column to sort
            reverse: Whether to reverse the sort order
        """
        # Integer columns
        if col in ["Index", "Levels", "Height"] or col in ["Length", "Width", "Rotation"]:
            data = []
            for item in tree.get_children(""):
                try:
                    value = float(tree.set(item, col))  # Using float to handle decimals
                except ValueError:
                    value = -1  # Default value for invalid entries
                data.append((value, item))
                
        # String columns
        elif col in ["Name", "Type", "Aeroway", "Amenity", "Barrier", "BMS", 
                    "Bridge", "Building", "Diplomatic", "Leisure", "Man Made",
                    "Military", "Office", "Power", "Religion", "Service", "Sport"]:
            data = [(tree.set(item, col).lower(), item) for item in tree.get_children("")]
            
        # Special case for Center column which might have complex format
        elif col == "Center":
            data = [(tree.set(item, col), item) for item in tree.get_children("")]
        else:
            data = [(tree.set(item, col), item) for item in tree.get_children("")]

        # Sort the data
        data.sort(reverse=reverse)
        
        # Rearrange items in sorted positions
        for idx, (_, item) in enumerate(data):
            tree.move(item, "", idx)

        # Reverse sort next time
        tree.heading(col, command=lambda c=col: self.sort_column_geo(tree, c, not reverse))

    def is_floor_height_not_valid(self, textbox):
        content = textbox.get()
        if not content:
            return True  # Textbox is empty
        try:
            value = float(content)
            if value == 0.0:
                return True
            return False  # Content is a valid float
        except ValueError:
            return True  # Content is not a valid float
            
    def CalculateGeo(self):
        """Will get Geo-Json file and if the file is valid, the box will be updated with the path string, and the structures list
        will be updated into the table in the page"""
        # Create a logger for this function
        logger = logging.getLogger(__name__)
        logger.info("Starting GeoJSON calculation process")
        
        try:
            file_path = self.controller.shared_data["Geopath"].get()
            logger.info(f"Using GeoJSON file: {file_path}")
            
            # Validate file path is not empty or default text
            if not file_path or file_path in ["No GeoJSON file selected", ""]:
                logger.error("No GeoJSON file selected")
                return messagebox.showerror("Error", "Please select a GeoJSON file first")
            
            # Check if file actually exists
            import os
            if not os.path.exists(file_path):
                logger.error(f"GeoJSON file not found: {file_path}")
                return messagebox.showerror("Error", f"GeoJSON file not found:\n{file_path}\n\nPlease select a valid file.")
            
            # Check if file has correct extension
            if not file_path.lower().endswith(('.geojson', '.json')):
                logger.warning(f"File does not have .geojson extension: {file_path}")
                
        except Exception as e:
            logger.error(f"Error getting GeoJSON path: {str(e)}")
            return messagebox.showerror("Error", f"Error accessing GeoJSON path: {str(e)}")

        # Import the processing window functionality
        from processing_window import run_with_processing
        
        # Check if projection string is available
        has_projection = (
            self.controller.shared_data["projection_string"].get()
            and self.controller.shared_data["projection_string"].get() != ""
        )
        projection_string = self.controller.shared_data["projection_string"].get() if has_projection else None
        
        # Application logging is already configured globally, no need to pass log level to functions
        
        # Check if floor height is available
        has_floor_height = not self.is_floor_height_not_valid(self.textbox_floor_height) if hasattr(self, 'textbox_floor_height') else False
        floor_height = float(self.textbox_floor_height.get()) if has_floor_height else None
        
        # Log configuration settings
        logger.info(f"Projection available: {has_projection}")
        if has_projection:
            logger.info(f"Using projection string: {projection_string}")
        logger.info(f"Floor height available: {has_floor_height}")
        if has_floor_height:
            logger.info(f"Using floor height: {floor_height} feet")
        
        # Define the GeoJSON loading task that will run in the background thread
        def load_geojson_task(processing_window):
            try:
                # Log action to application logs instead of print statements
                logger.info("Loading GeoJSON file...")
                
                # Prepare arguments for geo.Load_Geo_File with signature (json_path, projection_string, floor_height)
                args_for_load_geo = [file_path] # file_path

                # Add projection_string (it's None if not available, which matches the default in Load_Geo_File)
                args_for_load_geo.append(projection_string)

                # Add floor_height if available, otherwise Load_Geo_File will use its default
                if has_floor_height:
                    args_for_load_geo.append(floor_height)
                # If not has_floor_height, we don't append, relying on default in Load_Geo_File

                logger.info(f"Calling geo.Load_Geo_File with args: {args_for_load_geo}")
                result = geo.Load_Geo_File(*args_for_load_geo)
                    
                # Log processing features message
                logger.info("Processing GeoJSON features...")
                
                # Return the results
                return result
                
            except Exception as e:
                import traceback
                error_details = traceback.format_exc()
                logger.error(f"GeoJSON loading error: {str(e)}")
                logger.debug(f"Error details: {error_details}")
                raise ValueError("Projection string or GeoJson path are not valid")
        
        try:
            # Run the GeoJSON loading task with a processing window
            logger.info("Launching GeoJSON loading with processing window")
            result = run_with_processing(
                parent=self.controller,
                task_function=load_geojson_task,
                title="Loading GeoJSON Data",
                message="Initializing GeoJSON loading..."
            )
            
            # Check if result is valid (not None or False)
            if not result or not isinstance(result, tuple) or len(result) != 3:
                logger.error(f"Invalid result from GeoJSON loading: {result}")
                return messagebox.showerror("Error", "Failed to load GeoJSON data. Check the logs for details.")            
            # Unpack the results
            GeoFeatures, CalcData_GeoFeatures, AOI_center = result
            
            # Update the UI with the loaded data
            self.update_geo_data_GUI_fields(
                GeoFeatures, CalcData_GeoFeatures, AOI_center
            )
            
            # Convert data to dataframe and get the relevant data from it
            GeoFeatures = pd.DataFrame(GeoFeatures)
            CalcData_GeoFeatures = pd.DataFrame(CalcData_GeoFeatures)
            heights = np.transpose(CalcData_GeoFeatures[["Height (feet)"]].values)
            
            # Save all geo elements in global variables
            self.controller.shared_data["Geodata"] = GeoFeatures
            self.controller.shared_data["Calc_Geodata"] = CalcData_GeoFeatures
            self.controller.shared_data["Geo_AOI_center"] = AOI_center

            # Erase all data in the table
            for row in self.GeoTable.get_children():
                self.GeoTable.delete(row)
                
            # Update Geo data table with collected data
            for i in range(len(GeoFeatures)):
                # round the decimal numbers to 3, for better veiwing the data on the dable
                data_list = list(GeoFeatures.iloc[i])
                
                # Clean the data list values - replace empty/false values with empty strings
                data_list = self.clean_data_for_display(data_list)
                
                # Round numeric values for display
                data_list[2:5] = [
                    round(val, 3) if isinstance(val, (int, float)) else val for val in data_list[2:5]
                ]  # Round length, width, rotation
                
                try:
                    data_list[8] = round(
                        float(heights[0, i]), 3
                    )  # Replace initial height from the raw Geofile to the calculated height
                except (ValueError, TypeError, IndexError) as e:
                    logging.debug(f"Could not convert height data for row {i}: {str(e)}")
                    data_list[9] = ""  # Use empty string instead of 0
                    
                self.GeoTable.insert("", "end", values=data_list)

            # Show message if succeeded
            return messagebox.showinfo(
                "Success", "The load of GeoData from GeoJson file has been succeeded"
            )
            
        except ValueError as e:
            return messagebox.showerror("Error", str(e) or "Projection string or GeoJson path are not valid")
        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            logger.error(f"Unexpected error during GeoJSON loading: {str(e)}")
            logger.debug(f"Full error traceback: {error_details}")
            
            # Provide a more user-friendly error message
            error_msg = "Failed to load GeoJSON data"
            
            # Check specific error types to give more helpful messages
            if "TypeError: cannot unpack" in str(e):
                error_msg = "Processing error: Could not parse GeoJSON data structure. Check the file format."
                logger.error("GeoJSON data structure parsing failed - invalid return format")
            elif "ValueError: Projection string" in str(e):
                error_msg = "Invalid projection string or GeoJSON path."
                logger.error("Invalid projection string or GeoJSON path provided")
            elif "FileNotFoundError" in error_details:
                error_msg = "GeoJSON file not found. Check the file path."
                logger.error("GeoJSON file not found at specified path")
            elif "PermissionError" in error_details:
                error_msg = "Cannot read GeoJSON file. Check file permissions."
                logger.error("Permission denied when trying to read GeoJSON file")
            elif "geopandas" in str(e).lower():
                error_msg = "GeoJSON file format error. The file may be corrupted or not a valid GeoJSON."
                logger.error("Geopandas failed to read the file - likely format issue")
            else:
                error_msg = f"{error_msg}: {str(e)}"
                logger.error(f"Unhandled error type: {type(e).__name__}")
                
            # Log the error for debugging
            logger.critical(f"GeoJSON loading failed completely. Error: {error_msg}")
                
            # Show error message to user
            messagebox.showerror("Error", error_msg)

    def clean_data_for_display(self, data_list):
        """Cleans data values for display in the GeoTable
        Replaces empty/false/none values with empty strings"""
        non_display_values = [
            False, "False", None, "None", "none", "nan", "NaN", "false", "0", 
            "no", "building", "yes", "True", "true", "", " ", "roof"
        ]
        
        for i, val in enumerate(data_list):
            # Handle NaN values
            if isinstance(val, float) and math.isnan(val):
                data_list[i] = ""
            # Handle NumPy arrays
            elif isinstance(val, np.ndarray):
                # Convert NumPy array to string for display
                data_list[i] = str(val) if val.size > 0 else ""
            # Handle other types that could be in non_display_values
            elif not isinstance(val, (list, dict, np.ndarray)) and (
                val in non_display_values or 
                (isinstance(val, str) and val.lower() in non_display_values)
            ):
                data_list[i] = ""
                
        return data_list

    def update_geo_data_GUI_fields(self, GeoFeatures, CalcData_GeoFeatures, AOI_center):
        """

        :param self:
        :param GeoFeatures:
        :param CalcData_GeoFeatures:
        :param AOI_center:

        called from the function CalculateGeo for updating the GUI page with the new data
        """

        # update the status of structures amount to the GUI
        self.textbox_structures_amount.configure(state="normal")
        self.textbox_structures_amount.delete(0, tk.END)
        self.textbox_structures_amount.insert(0, str(len(GeoFeatures)))
        self.textbox_structures_amount.configure(state="disabled")

        # update the status of detailed structures to the GUI
        self.textbox_structures_detailed.configure(state="normal")
        self.textbox_structures_detailed.delete(0, tk.END)
        CalcData_GeoFeatures = pd.DataFrame(CalcData_GeoFeatures)
        self.textbox_structures_detailed.insert(
            0,
            str(CalcData_GeoFeatures["Detailed Structure"].value_counts().get(1.0, 0)),
        )
        self.textbox_structures_detailed.configure(state="disabled")

        # Convert the numbers to strings and Join the numbers with a '/'
        str_AOI_center = " / ".join([str(np.round(num, 6)) for num in AOI_center])
        initial_value = self.textbox_structures_center.get()
        len_initial_value = len(initial_value)
        # update the status on the GUI, Entry need to be enabled before updating it's value
        self.textbox_structures_center.configure(state="normal")
        if len_initial_value > 0:
            self.textbox_structures_center.delete(0, tk.END)
        self.textbox_structures_center.insert(0, str_AOI_center)
        self.textbox_structures_center.configure(state="disabled")

    def SelectGeoJsonFile(self, event):
        """Clicking on Geo box will open dialog which will allow to select"""
        logger = logging.getLogger(__name__)

        try:
            # open a file dialog and update the label text with the selected file path
            file_path = tkinter.filedialog.askopenfilename(
                filetypes=[("Geo-Json files", "*.GeoJson")]
            )
            if file_path:
                # Show File at the text place on the GUI
                self.controller.shared_data["Geopath"].set(file_path)
            else:
                # User canceled the dialog, just set the Geopath to default text
                self.controller.shared_data["Geopath"].set("No GeoJSON file selected")
        except Exception as e:
            # Handle any potential errors during file selection
            self.controller.shared_data["Geopath"].set("No GeoJSON file selected")
            logger.error(f"Error during file selection: {e}")
            if hasattr(self.controller, "debugger") and self.controller.debugger:
                traceback.print_exc()

    def SelectProjectionfile(self, event):
        """The function called by the projection TXT button, and looking for txt file which contain a string of projection
        self.controller.shared_data["projection_path"] = will have the path if file is selected
        self.controller.shared_data["projection_string"] = will have the string itself for projection"""
        logger = logging.getLogger(__name__)
        try:
            file_path = tkinter.filedialog.askopenfilename(
                filetypes=[("Projection file", "*.txt")]
            )

            # if path is valid
            if file_path:
                # Open the file in read mode
                with open(file_path, "r") as file:
                    # Read all lines in the file
                    lines = file.readlines()

                # Initialize an empty dictionary to store the data
                string = {}

                # Loop through each line in the file
                for line in lines:
                    # Split the line into key and value
                    try:
                        key, value = line.strip().split("=", 1)
                    except ValueError:
                        try:
                            key, value = line.strip().split("=")
                        except ValueError as e:
                            logging.error(f"Unable to parse line '{line.strip()}' in projection file: {str(e)}")
                            return messagebox.showerror("Error", "File cannot be read - invalid format")

                    # Add the key-value pair to the dictionary
                    string[key] = value

                # Check if 'Projection string' is in the dictionary
                if "Projection string" in string:
                    # Print the projection string
                    self.controller.shared_data["projection_string"].set(
                        string["Projection string"]
                    )
                    self.controller.shared_data["projection_path"].set(file_path)
                else:
                    # Show an error message
                    self.controller.shared_data["projection_path"].set(
                        "No Projection file selected"
                    )
                    self.controller.shared_data["projection_string"].set("")
                    return messagebox.showerror(
                        "Error", "Projection string not found in the file"
                    )
            # Erase old values if dialog was canceled
            else:
                self.controller.shared_data["projection_path"].set(
                    "No Projection file selected"
                )
                self.controller.shared_data["projection_string"].set("")
        except Exception as e:
            # Handle any potential errors during file selection
            self.controller.shared_data["projection_path"].set("No Projection file selected")
            self.controller.shared_data["projection_string"].set("")
            logger.error(f"Error during projection file selection: {e}")
            if hasattr(self.controller, "debugger") and self.controller.debugger:
                traceback.print_exc()
            return messagebox.showerror("Error", f"Error selecting projection file: {str(e)}")


class OperationPage(tk.Frame):
    def __init__(self, parent, controller):
        tk.Frame.__init__(self, parent)
        self.controller = controller
        self.configure(bg="#ffffff")

        self.Body_font = Ctk.CTkFont(family="Inter", size=15)
        self.Body_font_Bold = Ctk.CTkFont(family="Inter", size=15, weight="bold")
        self.button_font = Ctk.CTkFont(family="Inter", size=12)
        self.dash_font = Ctk.CTkFont(family="Inter", size=10)

        self.canvas = Canvas(
            self,
            bg="#FFFFFF",
            height=720,
            width=1152,
            bd=0,
            highlightthickness=0,
            relief="ridge",
        )

        self.canvas.place(x=0, y=0)
        self.canvas.create_rectangle(0.0, 0.0, 204.0, 720.0, fill="#A0B9D0", outline="")

        # Load button images using CTkImage
        self.button_operations_img = Ctk.CTkImage(
            light_image=Image.open(str(self.controller.ASSETS_PATH / "button_operations.png")),size=(21, 17)
        )
        self.button_geo_img = Ctk.CTkImage(
            light_image=Image.open(str(self.controller.ASSETS_PATH / "button_geo.png")),size=(21, 17)
        )
        self.button_data_img = Ctk.CTkImage(
            light_image=Image.open(str(self.controller.ASSETS_PATH / "button_data.png")),size=(21, 17)
        )
        self.button_dash_img = Ctk.CTkImage(
            light_image=Image.open(str(self.controller.ASSETS_PATH / "button_dash.png")),size=(21, 17)
        )
        self.button_settings_img = Ctk.CTkImage(
            light_image=Image.open(str(self.controller.ASSETS_PATH / "button_options.png")),size=(21, 17)
        )
        self.button_footprints_img = Ctk.CTkImage(
            light_image=Image.open(str(self.controller.ASSETS_PATH / "button_footprint.png")),
            size=(21, 17)
        )

        self.button_operations = Ctk.CTkButton(
            self,
            text="Operations",
            fg_color="#7A92A9",
            bg_color="#7A92A9",
            image=self.button_operations_img,
            height=33,
            width=167,
            corner_radius=0,
            hover=False,
            font=("Sans Font", 15),
            text_color="#000000",
        )
        self.button_operations.place(x=0, y=397)

        # New FootPrints navigation button
        self.button_footprints = Ctk.CTkButton(
            self,
            text="FootPrints",
            fg_color="#A1B9D0",
            bg_color="#A1B9D0",
            image=self.button_footprints_img,
            height=33,
            width=167,
            command=lambda: controller.show_frame("FootPrintsPage"),
            corner_radius=0,
            hover_color="#7A92A9",
            font=("Sans Font", 15),
            text_color="#000000",
        )
        self.button_footprints.place(x=0, y=445)

        self.button_geo = Ctk.CTkButton(
            self,
            text="GeoData",
            fg_color="#A1B9D0",
            bg_color="#A1B9D0",
            image=self.button_geo_img,
            height=33,
            width=167,
            command=lambda: controller.show_frame("GeoDataPage"),
            corner_radius=0,
            hover_color="#7A92A9",
            font=("arial", 15),
            text_color="#000000",
        )
        self.button_geo.place(x=0, y=349)

        self.button_data = Ctk.CTkButton(
            self,
            text="Database",
            fg_color="#A1B9D0",
            bg_color="#A1B9D0",
            image=self.button_data_img,
            height=33,
            width=167,
            command=lambda: controller.show_frame("DatabasePage"),
            corner_radius=0,
            hover_color="#7A92A9",
            font=("arial", 15),
            text_color="#000000",
        )
        self.button_data.place(x=0, y=297)

        self.button_dash = Ctk.CTkButton(
            self,
            text="DashBoard",
            fg_color="#A1B9D0",
            bg_color="#A1B9D0",
            image=self.button_dash_img,
            height=33,
            width=167,
            hover_color="#7A92A9",
            corner_radius=0,
            font=("Sans Font", 15),
            text_color="#000000",
            command=lambda: controller.show_frame("DashboardPage"),
        )
        self.button_dash.place(x=0, y=248)

        self.button_settings = Ctk.CTkButton(
            self,
            text="More\nSettings",
            fg_color="#778593",
            bg_color="#A1B9D0",
            image=self.button_settings_img,
            height=97,
            width=125,
            corner_radius=20,
            hover=False,
            font=("Sans Font", 16),
            text_color="#000000",
            command=self.controller.SettingWindow,
        )
        self.button_settings.place(x=14, y=581)

        self.canvas.create_rectangle(
            172.0, 0.0, 1152.0, 720.0, fill="#A1B9D0", outline=""
        )

        self.image_image_1 = PhotoImage(
            file=str(self.controller.ASSETS_PATH / "image_BG.png")
        )
        self.canvas.create_image(659.0, 360.0, image=self.image_image_1)

        self.image_image_2 = PhotoImage(
            file=str(self.controller.ASSETS_PATH / "image_BG_mask.png")
        )
        self.canvas.create_image(659.0, 360.0, image=self.image_image_2)

        self.image_image_3 = PhotoImage(
            file=str(self.controller.ASSETS_PATH / "image_Name.png")
        )
        self.canvas.create_image(84.0, 116.0, image=self.image_image_3)

        self.image_image_4 = PhotoImage(
            file=str(self.controller.ASSETS_PATH / "image_Welcome.png")
        )
        self.canvas.create_image(84.0, 82.0, image=self.image_image_4)

        self.image_image_5 = PhotoImage(
            file=str(self.controller.ASSETS_PATH / "image_Logo.png")
        )
        self.canvas.create_image(89.0, 39.0, image=self.image_image_5)

        self.image_image_6 = PhotoImage(
            file=str(self.controller.ASSETS_PATH / "image_CT.png")
        )
        self.canvas.create_image(667.0, 631.0, image=self.image_image_6)

        # Label/Button Widget for transparent  box
        self.CTpath_box = tk.Label(
            self, textvariable=self.controller.shared_data["CTpath"]
        )
        self.CTpath_box.place(x=375.0, y=612.0, width=730.0, height=30.0)
        self.CTpath_box.bind(("<Button-1>"), self.controller.SelectCTfile)

        self.image_image_7 = PhotoImage(
            file=str(self.controller.ASSETS_PATH / "Rectangle_Op_1.png")
        )
        self.canvas.create_image(989.0, 191.0, image=self.image_image_7)

        self.canvas.create_rectangle(
            883.0,
            90.0,
            1096.9998931884766,
            91.02392291863521,
            fill="#000000",
            outline="",
        )

        self.canvas.create_text(
            910.0,
            70.0,
            anchor="nw",
            text="Results",
            fill="#000000",
            font=("Inter", 15 * -1),
        )

        self.image_image_8 = PhotoImage(
            file=str(self.controller.ASSETS_PATH / "Rectangle_Op_2.png")
        )
        self.canvas.create_image(989.0, 429.0, image=self.image_image_8)

        self.canvas.create_rectangle(
            882.0,
            376.0,
            1095.9998931884766,
            377.0239229186352,
            fill="#000000",
            outline="",
        )

        self.canvas.create_text(
            909.0,
            356.0,
            anchor="nw",
            text="Restrictions",
            fill="#000000",
            font=("Inter", 15 * -1),
        )

        self.button_image_6 = PhotoImage(
            file=str(self.controller.ASSETS_PATH / "button_Generate.png")
        )
        button_6 = Button(
            self,
            image=self.button_image_6,
            borderwidth=0,
            highlightthickness=0,
            command=self.Create_Feature_List_For_BMS,
            relief="flat",
        )
        button_6.place(x=870.0, y=528.0)

        self.Rectangle_Op_4 = PhotoImage(
            file=str(self.controller.ASSETS_PATH / "Rectangle_Op_4.png")
        )
        self.canvas.create_image(989.0, 553.0, image=self.Rectangle_Op_4)

        self.image_image_9 = PhotoImage(
            file=str(self.controller.ASSETS_PATH / "Rectangle_Op_3.png")
        )
        self.canvas.create_image(528.0, 316.0, image=self.image_image_9)

        self.canvas.create_rectangle(
            247.0, 90.0, 805.0, 91.0, fill="#000000", outline=""
        )

        self.canvas.create_text(
            273.0,
            67.0,
            anchor="nw",
            text="Preferences\n",
            fill="#000000",
            font=("Inter", 15 * -1),
        )

        self.image_image_10 = PhotoImage(
            file=str(self.controller.ASSETS_PATH / "image_configuration.png")
        )
        self.canvas.create_image(256.0, 76.0, image=self.image_image_10)

        self.image_image_11 = PhotoImage(
            file=str(self.controller.ASSETS_PATH / "image_restrictions.png")
        )
        self.canvas.create_image(893.0, 364.0, image=self.image_image_11)

        self.image_image_12 = PhotoImage(
            file=str(self.controller.ASSETS_PATH / "image_results.png")
        )
        self.canvas.create_image(894.0, 77.0, image=self.image_image_12)

        self.image_image_14 = PhotoImage(
            file=str(self.controller.ASSETS_PATH / "image_BMSver.png")
        )
        self.canvas.create_image(566.0, 681.0, image=self.image_image_14)

        self.image_image_15 = PhotoImage(
            file=str(self.controller.ASSETS_PATH / "image_theater.png")
        )
        self.canvas.create_image(329.0, 682.0, image=self.image_image_15)

        self.theater_box = tk.Label(
            self,
            textvariable=self.controller.shared_data["Theater"],
            wraplength=100,
        )
        self.theater_box.place(x=310.0, y=663.0, width=112.0, height=28.0)
        self.theater_box.lift()

        self.BMSver_box = tk.Label(
            self,
            textvariable=self.controller.shared_data["BMS_version"],
            wraplength=100,
        )
        self.BMSver_box.place(x=555.0, y=663.0, width=112.0, height=28.0)
        self.BMSver_box.lift()

        self.canvas.create_rectangle(
            256.5,
            129.50000173039734,
            790.999076962471,
            130.5,
            fill="#B3C8DD",
            outline="",
        )

        self.canvas.create_text(
            257.0,
            106.0,
            anchor="nw",
            text="Method Selection",
            fill="#000000",
            font=("Inter Bold", 15 * -1),
        )

        # Create the segemented_button widget for Method Selection
        self.segemented_button = Ctk.CTkSegmentedButton(
            self,
            values=["Random Selection", "GeoJson"],
            fg_color="#D5E3F0",
            unselected_color="#D5E3F0",
            selected_color="#8DBBE7",
            font=self.button_font,
            height=20,
            width=267,
            text_color="#565454",
            dynamic_resizing=False,
        )
        self.segemented_button.place(x=524, y=105)
        self.segemented_button.set("GeoJson")

        self.canvas.create_rectangle(
            266.5, 159.5, 778.0, 160.0, fill="#B3C8DD", outline=""
        )

        self.canvas.create_text(
            267.0,
            142.0,
            anchor="nw",
            text="Random Selection",
            fill="#000000",
            font=("Inter", 14 * -1),
        )

        # Add distribution type selection
        # Create the distribution_selection segmented button widget
        self.distribution_selection = Ctk.CTkSegmentedButton(
            self,
            values=["Normal Distribution", "Peripheral Distribution", "Uniform Distribution"],
            fg_color="#D5E3F0",
            unselected_color="#D5E3F0",
            selected_color="#8DBBE7",
            font=Ctk.CTkFont(family="Inter", size=9),  # Smaller font to fit the button
            height=20,
            width=290,
            text_color="#565454",
            dynamic_resizing=False,
        )
        self.distribution_selection.place(x=487, y=135)
        self.distribution_selection.set("Normal Distribution")  # Default selection

        self.canvas.create_text(
            287.0,
            175.0,
            anchor="nw",
            text="Radius",
            fill="#000000",
            font=("Inter", 12 * -1),
        )

        # Create the CTkTextbox widget for radius
        self.textbox_Radius_random = Ctk.CTkEntry(
            self, width=95, height=18, border_color="#D5E3F0", text_color="#565454"
        )
        self.textbox_Radius_random.place(x=684, y=172)
        self.textbox_Radius_random.insert(0, 3600)

        self.canvas.create_text(
            287.0,
            201.0,
            anchor="nw",
            text="Amount",
            fill="#000000",
            font=("Inter", 12 * -1),
        )

        # Create the CTkTextbox widget for amount
        self.textbox_Amount_random = Ctk.CTkEntry(
            self, width=95, height=18, border_color="#D5E3F0", text_color="#565454"
        )
        self.textbox_Amount_random.place(x=684, y=200)
        self.textbox_Amount_random.insert(0, 256)

        # Set CTkTextbox widget and option selection menu for value mapping for geo data
        self.values_rand_optionmenu = Ctk.CTkOptionMenu(
            self,
            width=80,
            height=18,
            fg_color="#D5E3F0",
            text_color="#565454",
            values=["Solid", "Random", "Map"],
            command=lambda current_option: self.value_State(current_option, "rand"),
        )
        self.values_rand_optionmenu.place(x=580, y=227)
        self.values_rand_optionmenu.set("Solid")

        self.values_rand_mapping = Ctk.CTkButton(
            self,
            text="#",
            fg_color="#8DBBE7",
            width=20,
            height=18,
            corner_radius=20,
            command=self.value_mapping,
        )
        self.values_rand_mapping.place(x=545, y=227)

        self.canvas.create_text(
            287.0,
            227.0,
            anchor="nw",
            text="Values",
            fill="#000000",
            font=("Inter", 12 * -1),
        )

        self.textbox_Values_random2 = Ctk.CTkEntry(
            self, width=45, height=18, border_color="#D5E3F0", text_color="#565454"
        )
        self.textbox_Values_random2.place(x=734, y=226)
        self.textbox_Values_random2.insert(0, 100)
        self.textbox_Values_random1 = Ctk.CTkEntry(
            self,
            width=45,
            height=18,
            border_color="#D5E3F0",
            fg_color="#E7E7E7",
            state="disabled",
            text_color="#565454",
        )
        self.textbox_Values_random1.place(x=684, y=226)

        self.canvas.create_text(
            287.0,
            253.0,
            anchor="nw",
            text="Presence",
            fill="#000000",
            font=("Inter", 12 * -1),
        )
        # Create the CTkTextbox/box widget for Presence on random
        self.switch_Presence_random_ver = Ctk.StringVar(value="on")
        self.switch_Presence_random = Ctk.CTkSwitch(
            self,
            text="",
            bg_color="#FDFBFC",
            command=self.switch_presence_State_random,
            variable=self.switch_Presence_random_ver,
            onvalue=1,
            offvalue=0,
        )
        self.switch_Presence_random.place(x=597, y=252)

        # min and maximum values (2 - max, 1- min)
        self.textbox_Presence_random2 = Ctk.CTkEntry(
            self, width=45, height=18, border_color="#D5E3F0", text_color="#565454"
        )
        self.textbox_Presence_random2.place(x=734, y=252)
        self.textbox_Presence_random2.insert(0, 100)
        self.textbox_Presence_random1 = Ctk.CTkEntry(
            self,
            width=45,
            height=18,
            border_color="#D5E3F0",
            fg_color="#E7E7E7",
            state="disabled",
            text_color="#565454",
        )
        self.textbox_Presence_random1.place(x=684, y=252)

        self.canvas.create_rectangle(
            266.5, 298.5, 778.0, 299.0, fill="#B3C8DD", outline=""
        )

        self.canvas.create_text(
            267.0,
            281.0,
            anchor="nw",
            text="GeoJson Importation",
            fill="#000000",
            font=("Inter", 14 * -1),
        )

        self.canvas.create_rectangle(
            266.5, 509.5, 534.0, 510.0, fill="#B3C8DD", outline=""
        )

        self.canvas.create_text(
            274.0,
            492.0,
            anchor="nw",
            text="BMS Injection",
            fill="#000000",
            font=("Inter", 14 * -1),
        )

        self.canvas.create_rectangle(
            545.5, 509.5, 791.0, 510.0, fill="#B3C8DD", outline=""
        )

        self.canvas.create_text(
            544.0,
            492.0,
            anchor="nw",
            text="Editor Extraction",
            fill="#000000",
            font=("Inter", 14 * -1),
        )

        self.canvas.create_text(
            287.0,
            366.0,
            anchor="nw",
            text="Fillter",
            fill="#000000",
            font=("Inter", 12 * -1),
        )

        # Set Fillter option selection menu
        self.Fillter_optionmenu = Ctk.CTkOptionMenu(
            self,
            width=94,
            height=18,
            fg_color="#D5E3F0",
            text_color="#565454",
            values=["Height", "Area", "Total Size", "Centerness", "Mix", "Random"],
        )
        self.Fillter_optionmenu.place(x=684, y=365)
        self.Fillter_optionmenu.set("Total Size")

        self.canvas.create_text(
            884.0,
            381.0,
            anchor="nw",
            text="Please state the values of the feature's restriction \nyou are willing to integrate",
            fill="#565454",
            font=("Inter", 9 * -1),
        )

        self.canvas.create_text(
            287.0,
            314.0,
            anchor="nw",
            text="Amount",
            fill="#000000",
            font=("Inter", 12 * -1),
        )
        # Create the CTkTextbox widget for Amount
        self.textbox_Amount_geo = Ctk.CTkEntry(
            self, width=95, height=18, border_color="#D5E3F0", text_color="#565454"
        )
        self.textbox_Amount_geo.place(x=684, y=313)
        self.textbox_Amount_geo.insert(0, 100)

        # Create the max button widget for max Amount
        self.button_Amount_geo = Ctk.CTkButton(
            self,
            text="Maximum",
            fg_color="#8DBBE7",
            width=116,
            height=18,
            command=self.get_maximum_amount_geo,
        )
        self.button_Amount_geo.place(x=545, y=314)

        self.canvas.create_text(
            286.0,
            392.0,
            anchor="nw",
            text="Selection ",
            fill="#000000",
            font=("Inter", 12 * -1),
        )

        # Set Fitting options selection menu and AutoDetect mechanism checkbox
        self.Selection_optionmenu = Ctk.CTkOptionMenu(
            self,
            width=94,
            height=18,
            fg_color="#D5E3F0",
            text_color="#565454",
            values=["3D", "2D"],
        )
        self.Selection_optionmenu.place(x=684, y=391)

        # label and Entry for Floor deviation Settings
        self.floor_deviation_label = Ctk.CTkLabel(
            self, text="Floor Deviation:", font=self.button_font, bg_color="#FDFDFD"
        )
        self.floor_deviation_label.place(x=450, y=386)

        self.floor_deviation_entry = Ctk.CTkEntry(
            self,
            width=36,
            height=18,
            border_color="#D5E3F0",
            fg_color="#FDFDFD",
            placeholder_text="0",
        )
        self.floor_deviation_entry.place(x=542, y=390)

        self.Auto_features_detector = Ctk.CTkCheckBox(
            self,
            checkbox_height=18,
            checkbox_width=18,
            text="Auto Sel",
            onvalue=True,
            offvalue=False,
            font=self.button_font,
            text_color="#565454",
            width=30,
            bg_color="#FDFBFC",
        )
        self.Auto_features_detector.place(x=589, y=388)

        self.canvas.create_text(
            286.0,
            340.0,
            anchor="nw",
            text="Values ",
            fill="#000000",
            font=("Inter", 12 * -1),
        )

        # Create the CTkTextbox widget for Values
        # Set  option selection menu for value mapping for geo data
        self.values_geo_optionmenu = Ctk.CTkOptionMenu(
            self,
            width=80,
            height=18,
            fg_color="#D5E3F0",
            text_color="#565454",
            values=["Solid", "Random", "Map"],
            command=lambda current_option: self.value_State(current_option, "geo"),
        )
        self.values_geo_optionmenu.place(x=580, y=341)
        self.values_geo_optionmenu.set("Solid")

        self.values_geo_mapping = Ctk.CTkButton(
            self,
            text="#",
            fg_color="#8DBBE7",
            width=20,
            height=18,
            corner_radius=20,
            command=self.value_mapping,
        )
        self.values_geo_mapping.place(x=545, y=341)

        # min and maximum values (2 - max, 1- min)
        self.textbox_Values_geo2 = Ctk.CTkEntry(
            self, width=45, height=18, border_color="#D5E3F0", text_color="#565454"
        )
        self.textbox_Values_geo2.place(x=734, y=339)
        self.textbox_Values_geo2.insert(0, 100)

        self.textbox_Values_geo1 = Ctk.CTkEntry(
            self,
            width=45,
            height=18,
            border_color="#D5E3F0",
            fg_color="#E7E7E7",
            state="disabled",
            text_color="#565454",
        )
        self.textbox_Values_geo1.place(x=684, y=339)

        self.canvas.create_text(
            287.0,
            418.0,
            anchor="nw",
            text="Presence",
            fill="#000000",
            font=("Inter", 12 * -1),
        )
        # Create the CTkTextbox/switch widget for Presence
        self.switch_Presence_geo_ver = Ctk.StringVar(value="on")
        self.switch_Presence_geo = Ctk.CTkSwitch(
            self,
            text="",
            bg_color="#FDFBFC",
            command=self.switch_presence_State_geo,
            variable=self.switch_Presence_geo_ver,
            onvalue=1,
            offvalue=0,
        )
        self.switch_Presence_geo.place(x=597, y=417)

        # min and maximum Presence (2 - max, 1- min)
        self.textbox_Presence_geo2 = Ctk.CTkEntry(
            self, width=35, height=18, border_color="#D5E3F0", text_color="#565454"
        )
        self.textbox_Presence_geo2.place(x=745, y=417)
        self.textbox_Presence_geo2.insert(0, 100)
        self.textbox_Presence_geo1 = Ctk.CTkEntry(
            self,
            width=35,
            height=18,
            border_color="#D5E3F0",
            fg_color="#E7E7E7",
            state="disabled",
            text_color="#565454",
        )
        self.textbox_Presence_geo1.place(x=705, y=417)

        self.canvas.create_text(
            286.0,
            521.0,
            anchor="nw",
            text="CT number",
            fill="#000000",
            font=("Inter", 12 * -1),
        )

        # Create the CTkTextbox widget for Objective number
        self.textbox_Obj = Ctk.CTkEntry(
            self,
            width=74,
            height=18,
            fg_color="#FDFDFD",
            border_color="#D5E3F0",
            text_color="#565454",
            state="disable",
        )
        self.textbox_Obj.place(x=415, y=544)

        self.canvas.create_text(
            286.0,
            547.0,
            anchor="nw",
            text="Objective Number",
            fill="#000000",
            font=("Inter", 12 * -1),
        )

        # Create the CTkTextbox widget for CT number
        self.textbox_CT = Ctk.CTkEntry(
            self,
            width=74,
            height=18,
            fg_color="#FDFDFD",
            border_color="#D5E3F0",
            text_color="#565454",
            state="disable",
        )
        self.textbox_CT.place(x=415, y=518)

        self.canvas.create_rectangle(
            256.5,
            475.50000173039734,
            790.999076962471,
            477.0,
            fill="#B3C8DD",
            outline="",
        )

        self.canvas.create_text(
            257.0,
            454.0,
            anchor="nw",
            text="Saving Method",
            fill="#000000",
            font=("Inter Bold", 15 * -1),
        )

        # Create the segemented_button widget for Method Selection
        self.saving_method_var = tk.StringVar(value="Editor")
        self.segemented_button_Saving = Ctk.CTkSegmentedButton(
            self,
            values=["BMS", "Editor"],
            fg_color="#D5E3F0",
            unselected_color="#D5E3F0",
            selected_color="#8DBBE7",
            font=self.button_font,
            height=20,
            width=267,
            text_color="#565454",
            dynamic_resizing=False,
            variable=self.saving_method_var,
            command=self.switch_save_method
        )
        self.segemented_button_Saving.place(x=524, y=451)
        self.segemented_button_Saving.set("Editor")

        self.canvas.create_rectangle(
            247.0, 90.0, 805.0, 91.0, fill="#000000", outline=""
        )

        self.restriction_box = Ctk.CTkTextbox(
            self,
            height=60,
            width=213,
            text_color="#565454",
            corner_radius=0,
            fg_color="#E7E7E7",
        )
        self.restriction_box.place(x=883, y=406)

        self.restriction_button = Ctk.CTkButton(
            self,
            text="List of restrictions",
            fg_color="#A7A7A7",
            height=21,
            width=213,
            command=self.restriction_window,
        )
        self.restriction_button.place(x=884, y=476)

        self.canvas.create_rectangle(
            961.0, 476.0, 1023.0, 497.0, fill="#D9D9D9", outline=""
        )

        self.canvas.create_rectangle(
            1033.0, 476.0, 1095.0, 497.0, fill="#D9D9D9", outline=""
        )

        # Create the segemented_button widget for Method Selection
        self.sorting_saving = Ctk.CTkSegmentedButton(
            self,
            values=["None", "Alphabet", "Value"],
            font=("Arial", 10),
            fg_color="#D5E3F0",
            unselected_color="#D5E3F0",
            selected_color="#8DBBE7",
            height=18,
            width=135,
            text_color="#565454",
            dynamic_resizing=False,
        )
        self.sorting_saving.place(x=656, y=490)
        self.sorting_saving.set("None")

        self.canvas.create_text(
            557.0,
            521.0,
            anchor="nw",
            text="Saving Path",
            fill="#000000",
            font=("Inter", 12 * -1),
        )

        self.canvas.create_text(
            557.0,
            547.0,
            anchor="nw",
            text="File Name",
            fill="#000000",
            font=("Inter", 12 * -1),
        )

        # Create the CTkTextbox widget for getting numbers for CT and Objectives
        self.Get_More_button = Ctk.CTkButton(
            self,
            width=30,
            height=10,
            text="Preferences",
            font=("Arial", 10),
            text_color="#565454",
            command=self.open_bms_injection_window,  # Add command to open BMS injection window
            fg_color="#D5E3F0"
        )
        self.Get_More_button.place(x=467, y=490)

        # Update CT and Objective entries to be wider since we're removing the Browse buttons
        self.textbox_CT.configure(width=120)
        self.textbox_Obj.configure(width=120)

        # Create the CTkTextbox widget for path for Editor Extraction
        self.Editor_Extraction_browse = Ctk.CTkButton(
            self,
            width=124,
            height=18,
            text="Browse",
            command=self.Browse_saving_path,
            fg_color="#8DBBE7",
        )
        self.Editor_Extraction_browse.place(x=667, y=520)

        # Create the CTkTextbox widget for File name for Editor Extraction
        self.Editor_Extraction_name = Ctk.CTkEntry(
            self, width=124, height=18, border_color="#D5E3F0", text_color="#565454"
        )
        self.Editor_Extraction_name.place(x=667, y=546)
        self.Editor_Extraction_name.insert(0, "FeaturesFile")

        # Set Results panel #
        # Labels
        self.results_label_0 = Ctk.CTkLabel(
            self, text="2D Feature map", font=self.Body_font, bg_color="#F8F9FB"
        )
        self.results_label_0.place(x=884, y=102)
        self.results_label_1 = Ctk.CTkLabel(
            self, text="3D Feature map", font=self.Body_font, bg_color="#F8F9FB"
        )
        self.results_label_1.place(x=884, y=128)
        self.results_label_2 = Ctk.CTkLabel(
            self, text="2D Geodata map", font=self.Body_font, bg_color="#F8F9FB"
        )
        self.results_label_2.place(x=884, y=152)
        self.results_label_3 = Ctk.CTkLabel(
            self, text="3D Geodata map", font=self.Body_font, bg_color="#F8F9FB"
        )
        self.results_label_3.place(x=884, y=176)
        self.results_label_4 = Ctk.CTkLabel(
            self,
            text="Show After Generating the",
            font=self.Body_font,
            bg_color="#F8F9FB",
        )
        self.results_label_4.place(x=884, y=215)
        self.results_label_5 = Ctk.CTkLabel(
            self, text="following map:", font=self.Body_font, bg_color="#F8F9FB"
        )
        self.results_label_5.place(x=884, y=235)

        # Line
        # self.canvas.create_rectangle(882.0,251.0,1096.0,268.0,fill="#D9D9D9",outline="")
        self.canvas.create_rectangle(
            880.5,
            209.5,
            1093.9998931884766,
            210.0239229186352,
            fill="#B3C8DD",
            outline="",
        )

        # Buttons
        self.results_button_0 = Ctk.CTkButton(
            self,
            width=86,
            height=15,
            text="Show",
            font=self.button_font,
            command=self.Two_D_Feature_map,
            fg_color="#8DBAE6",
        )
        self.results_button_0.place(x=1011, y=108)
        self.results_button_1 = Ctk.CTkButton(
            self,
            width=86,
            height=15,
            text="Show",
            font=self.button_font,
            command=self.Three_D_Feature_map,
            fg_color="#8DBAE6",
        )
        self.results_button_1.place(x=1011, y=133)
        self.results_button_2 = Ctk.CTkButton(
            self,
            width=86,
            height=15,
            text="Show",
            font=self.button_font,
            command=self.Two_D_Geo_maps,
            fg_color="#8DBAE6",
        )
        self.results_button_2.place(x=1011, y=157)
        self.results_button_3 = Ctk.CTkButton(
            self,
            width=86,
            height=15,
            text="Show",
            command=self.Three_D_Geo_maps,
            fg_color="#8DBAE6",
        )
        self.results_button_3.place(x=1011, y=181)

        # Create the first row of segemented_button widget
        self.segemented_button_graphing1 = Ctk.CTkSegmentedButton(
            self,
            values=["2D Fit", "3D Fit", "2D Geo", "3D Geo"],
            fg_color="#D5E3F0",
            unselected_color="#D5E3F0",
            selected_color="#8DBBE7",
            height=20,
            width=214,
            text_color="#565454",
            font=self.button_font,
            dynamic_resizing=False,
            corner_radius=0,
            command=self.segemented_button_1_selection,
        )
        self.segemented_button_graphing1.place(x=882, y=265)

        # Create the second row of segemented_button widget
        self.segemented_button_graphing2 = Ctk.CTkSegmentedButton(
            self,
            values=["2D Both", "3D Both", "None"],
            fg_color="#D5E3F0",
            unselected_color="#D5E3F0",
            selected_color="#8DBBE7",
            height=20,
            width=214,
            text_color="#565454",
            font=self.button_font,
            dynamic_resizing=False,
            corner_radius=0,
            command=self.segemented_button_2_selection,
        )
        self.segemented_button_graphing2.place(
            x=882, y=285
        )  # Adjust the y-coordinate for the second row
        self.segemented_button_graphing2.set("None")

    def value_mapping(self):
        """
        Will launch the window to get the custom values for the value_mapping in the random  and GeoData sections.
        the window will take the values from the ValuesDic.json file.
        while window is opened, any buttons related are disabled.
        """
        self.values_rand_mapping.configure(state="disabled")
        self.values_geo_mapping.configure(state="disabled")
        ValuesDictionary.ValuesDictionary(
            filepath="ValuesDic.json", callback=self.value_mapping_close
        )

    def value_mapping_close(self):
        self.values_geo_mapping.configure(state="normal")
        self.values_rand_mapping.configure(state="normal")

    def get_maximum_amount_geo(self):
        try:
            count = self.controller.frames[
                "GeoDataPage"
            ].textbox_structures_amount.get()
            if len(count) > 0:
                self.textbox_Amount_geo.delete(0, "end")
                if 0 < int(count) <= 255:
                    self.textbox_Amount_geo.insert(0, count)
                elif int(count) > 255:
                    self.textbox_Amount_geo.insert(0, "255")
            else:
                return messagebox.showerror(
                    "Error",
                    "Geo-Data is not loaded correctly\n"
                    "Please load the data and try again.",
                )
        except:
            return messagebox.showerror(
                "Error",
                "Geo-Data is not loaded correctly\n"
                "Please load the data and try again.",
            )

    def auto_graph_generating(self):
        '''The function will decide which map to generate based on the Segmented button in the GUI
        Available states of graph generating is: "2D Both", "3D Both", "None","2D Fit", "3D Fit", "2D Geo", "3D Geo"'''
        state1 = self.segemented_button_graphing1.get()
        state2 = self.segemented_button_graphing2.get()

        if state2 == "":
            if state1 == "2D Fit":
                self.ShowMap("2D", "BMS_Fitting")

            elif state1 == "3D Fit":
                self.ShowMap("3D", "BMS_Fitting")

            elif state1 == "2D Geo":
                self.ShowMap("2D", "JSON_BondingBox")

            elif state1 == "3D Geo":
                self.ShowMap("3D", "JSON_BondingBox")

        else:
            if state2 == "2D Both":
                self.ShowMap("2D", "Both")

            elif state2 == "3D Both":
                self.ShowMap("3D", "Both")

            elif state2 == "None":
                return None

    def Two_D_Feature_map(self):
        """:Trigger: 2D BMS features button
        :return: Graph of 2D features from BMS"""
        try:
            if (
                self.BMS_features_map
                and self.controller.shared_data["BMS_Databse"].size != 0
            ):
                self.ShowMap("2D", "BMS_Fitting")
            else:
                return messagebox.showerror(
                    "Process Aborted",
                    "Features Map or Database were'nt found,"
                    "\nPlease verify your data state.",
                )
        except:
            return messagebox.showerror(
                "Process Aborted",
                "Features Map or Database were'nt found,"
                "\nPlease verify your data state.",
            )

    def Two_D_both_maps(self):
        """:Trigger: 2D Geo map and BMS features button
        :return: Graph of 2D features from Geomap and BMS side by side"""
        try:
            if (
                self.BMS_features_map
                and self.controller.shared_data["BMS_Databse"].size != 0
                and not self.Filltered_GeoFeatures.empty
                and not self.Filltered_Calc_GeoFeatures.empty
            ):
                self.ShowMap("2D", "Both")
            else:
                return messagebox.showerror(
                    "Process Aborted",
                    "Some data is missing," "\nPlease verify your state.",
                )
        except:
            return messagebox.showerror(
                "Process Aborted", "Some data is missing," "\nPlease verify your state."
            )

    def Two_D_Geo_maps(self):
        """:Trigger: 2D Geo map button
        :return: Graph of 2D features from Geomap"""

        try:
            if (
                not self.Filltered_GeoFeatures.empty
                and self.Filltered_Calc_GeoFeatures.size != 0
            ):
                self.ShowMap("2D", "JSON_BondingBox")
            else:
                return messagebox.showerror(
                    "Process Aborted",
                    "Fitted GeoMaps are missing,"
                    "\nPlease generate it before attempting again.",
                )
        except:
            return messagebox.showerror(
                "Process Aborted",
                "Fitted GeoMaps are missing,"
                "\nPlease generate it before attempting again.",
            )

    def Three_D_Feature_map(self):
        """:Trigger: 3D Feature map button
        :return: Graph of 3D features from BMS"""
        try:
            if (
                self.BMS_features_map
                and self.controller.shared_data["BMS_Databse"].size != 0
            ):
                self.ShowMap("3D", "BMS_Fitting")
            else:
                return messagebox.showerror(
                    "Process Aborted",
                    "Features Map or Database were'nt found,"
                    "\nPlease verify your data state.",
                )
        except:
            return messagebox.showerror(
                "Process Aborted",
                "Features Map or Database were'nt found,"
                "\nPlease verify your data state.",
            )

    def Three_D_both_maps(self):
        """:Trigger: 3D Geo map and BMS features button
        :return: Graph of 3D features from Geomap and BMS side by side"""
        try:
            if (
                self.BMS_features_map
                and self.controller.shared_data["BMS_Databse"].size != 0
                and not self.Filltered_GeoFeatures.empty
                and not self.Filltered_Calc_GeoFeatures.empty
            ):
                self.ShowMap("3D", "Both")
            else:
                return messagebox.showerror(
                    "Process Aborted",
                    "Some data is missing," "\nPlease verify your state.",
                )
        except:
            return messagebox.showerror(
                "Process Aborted", "Some data is missing," "\nPlease verify your state."
            )

    def Three_D_Geo_maps(self):
        """:Trigger: 3D Geo map button
        :return: Graph of 3D features from Geomap"""
        try:
            if (
                not self.Filltered_GeoFeatures.empty
                and self.Filltered_Calc_GeoFeatures.size != 0
            ):
                self.ShowMap("3D", "JSON_BondingBox")
            else:
                return messagebox.showerror(
                    "Process Aborted",
                    "Fitted GeoMaps are missing,"
                    "\nPlease generate it before attempting again.",
                )
        except:
            return messagebox.showerror(
                "Process Aborted",
                "Fitted GeoMaps are missing,"
                "\nPlease generate it before attempting again.",
            )

    def ShowMap(self, Dimension, plot_option):
        '''Will check the map that needed to be shown, and then call function: Show_Selected_Features_2D from MainCode
        input: plot_option == "Both", "BMS_Fitting", "JSON_BondingBox"'''

        # Will show 2D or 3D graphs of both BMS features and Geo Bondingbox
        if plot_option == "Both":
            LoadedBMSModels = self.controller.shared_data["BMS_Databse"]
            # Build display set: include all fitted Geo features plus extra from full set up to 256
            try:
                all_geo = self.controller.shared_data.get("Geodata")
                all_calc = self.controller.shared_data.get("Calc_Geodata")
                fitted_geo = self.Filltered_GeoFeatures if hasattr(self, 'Filltered_GeoFeatures') else None
                # Use user-configured limit (10-1000), default 256
                cfg_limit = 256
                try:
                    cfg_limit = int(self.controller.shared_data["MaxGeojsonDraw"].get())
                except Exception:
                    cfg_limit = 256
                cfg_limit = max(10, min(1000, cfg_limit))
                allowed = min(cfg_limit, len(all_geo)) if all_geo is not None else 0
                fitted_idx = list(fitted_geo.index) if fitted_geo is not None and not fitted_geo.empty else []
                extra_needed = max(0, allowed - len(fitted_idx))
                extra_idx = [i for i in all_geo.index if i not in fitted_idx][:extra_needed]
                display_idx = fitted_idx + extra_idx
                geo_display = all_geo.loc[display_idx] if allowed > 0 else fitted_geo
                calc_display = all_calc.loc[display_idx].values if allowed > 0 and hasattr(self, 'Filltered_Calc_GeoFeatures') else (self.Filltered_Calc_GeoFeatures if hasattr(self, 'Filltered_Calc_GeoFeatures') else None)
            except Exception as e:
                # Fallback to previous filtered data on any issue
                # Check if filtered data exists before using it
                if not hasattr(self, 'Filltered_GeoFeatures') or not hasattr(self, 'Filltered_Calc_GeoFeatures'):
                    # No data available at all, show warning and return
                    import logging
                    logging.warning(f"Cannot show map: No geodata available (error: {e})")
                    messagebox.showwarning(
                        "No Data Available",
                        "Cannot display map because no geodata has been loaded or generated yet.\n\n"
                        "Please load geodata from the GeoData page first."
                    )
                    return
                geo_display = self.Filltered_GeoFeatures
                calc_display = self.Filltered_Calc_GeoFeatures
            if Dimension == "2D":
                Show_Selected_Features_2D(
                    plot_option,
                    geo_display,
                    calc_display,
                    self.BMS_features_map,
                    LoadedBMSModels,
                )
            elif Dimension == "3D":
                Show_Selected_Features_3D(
                    plot_option,
                    geo_display,
                    calc_display,
                    self.BMS_features_map,
                    LoadedBMSModels,
                )

        # Will show 2D or 3D graph BMS features
        elif plot_option == "BMS_Fitting":
            Selected_GeoFeatures = None
            Selected_CalcData_GeoFeatures = None
            LoadedBMSModels = self.controller.shared_data["BMS_Databse"]
            if Dimension == "2D":
                Show_Selected_Features_2D(
                    plot_option,
                    Selected_GeoFeatures,
                    Selected_CalcData_GeoFeatures,
                    self.BMS_features_map,
                    LoadedBMSModels,
                )
            elif Dimension == "3D":
                Show_Selected_Features_3D(
                    plot_option,
                    Selected_GeoFeatures,
                    Selected_CalcData_GeoFeatures,
                    self.BMS_features_map,
                    LoadedBMSModels,
                )

        # Will show 2D or 3D graph of Geo Bondingbox
        elif plot_option == "JSON_BondingBox":
            if Dimension == "2D":
                # Build display set: include all fitted Geo features plus extra from full set up to 256
                try:
                    all_geo = self.controller.shared_data["Geodata"]
                    all_calc = self.controller.shared_data["Calc_Geodata"]
                    fitted_geo = self.Filltered_GeoFeatures if hasattr(self, 'Filltered_GeoFeatures') else None
                    cfg_limit = 256
                    try:
                        cfg_limit = int(self.controller.shared_data["MaxGeojsonDraw"].get())
                    except Exception:
                        cfg_limit = 256
                    cfg_limit = max(10, min(1000, cfg_limit))
                    allowed = min(cfg_limit, len(all_geo)) if all_geo is not None else 0
                    fitted_idx = list(fitted_geo.index) if fitted_geo is not None and not fitted_geo.empty else []
                    extra_needed = max(0, allowed - len(fitted_idx))
                    extra_idx = [i for i in all_geo.index if i not in fitted_idx][:extra_needed]
                    display_idx = fitted_idx + extra_idx
                    geo_display = all_geo.loc[display_idx] if allowed > 0 else fitted_geo
                    calc_display = all_calc.loc[display_idx].values if allowed > 0 else self.Filltered_Calc_GeoFeatures
                except Exception:
                    geo_display = self.Filltered_GeoFeatures
                    calc_display = self.Filltered_Calc_GeoFeatures
                Show_Selected_Features_2D(
                    plot_option,
                    geo_display,
                    calc_display,
                )
            elif Dimension == "3D":
                try:
                    all_geo = self.controller.shared_data["Geodata"]
                    all_calc = self.controller.shared_data["Calc_Geodata"]
                    fitted_geo = self.Filltered_GeoFeatures if hasattr(self, 'Filltered_GeoFeatures') else None
                    cfg_limit = 256
                    try:
                        cfg_limit = int(self.controller.shared_data["MaxGeojsonDraw"].get())
                    except Exception:
                        cfg_limit = 256
                    cfg_limit = max(10, min(1000, cfg_limit))
                    allowed = min(cfg_limit, len(all_geo)) if all_geo is not None else 0
                    fitted_idx = list(fitted_geo.index) if fitted_geo is not None and not fitted_geo.empty else []
                    extra_needed = max(0, allowed - len(fitted_idx))
                    extra_idx = [i for i in all_geo.index if i not in fitted_idx][:extra_needed]
                    display_idx = fitted_idx + extra_idx
                    geo_display = all_geo.loc[display_idx] if allowed > 0 else fitted_geo
                    calc_display = all_calc.loc[display_idx].values if allowed > 0 else self.Filltered_Calc_GeoFeatures
                except Exception:
                    geo_display = self.Filltered_GeoFeatures
                    calc_display = self.Filltered_Calc_GeoFeatures
                Show_Selected_Features_3D(
                    plot_option,
                    geo_display,
                    calc_display,
                )

    def segemented_button_1_selection(self, value):
        """The fuction will diselect button segemented_button_graphing2"""
        self.segemented_button_graphing2.set("")

    def segemented_button_2_selection(self, value):
        """The fuction will diselect button segemented_button_graphing1"""
        self.segemented_button_graphing1.set("")

    def switch_presence_State_random(self):
        """The function decides the ability to write values in the first entry box"""
        current_state = self.switch_Presence_random.get()

        if current_state == 0:
            self.textbox_Presence_random1.configure(state="disabled")
            self.textbox_Presence_random1.configure(fg_color="#E7E7E7")
        else:
            self.textbox_Presence_random1.configure(state="normal")
            self.textbox_Presence_random1.configure(fg_color="white")

    def value_State(self, current_option, value):
        """The function decides the ability to write values in the first or second entry box in random or geoData section"""

        if current_option == "Solid":
            # Disable first textbox and enable second textbox on Geo section or Random Section
            if value == "geo":
                self.textbox_Values_geo1.configure(state="disabled")
                self.textbox_Values_geo1.configure(fg_color="#E7E7E7")
                self.textbox_Values_geo2.configure(state="normal")
                self.textbox_Values_geo2.configure(fg_color="white")
            elif value == "rand":
                self.textbox_Values_random1.configure(state="disabled")
                self.textbox_Values_random1.configure(fg_color="#E7E7E7")
                self.textbox_Values_random2.configure(state="normal")
                self.textbox_Values_random2.configure(fg_color="white")

        elif current_option == "Random":
            # Enable first and second textboxs on Geo section or Random Section
            if value == "geo":
                self.textbox_Values_geo1.configure(state="normal")
                self.textbox_Values_geo1.configure(fg_color="white")
                self.textbox_Values_geo2.configure(state="normal")
                self.textbox_Values_geo2.configure(fg_color="white")
            elif value == "rand":
                self.textbox_Values_random1.configure(state="normal")
                self.textbox_Values_random1.configure(fg_color="white")
                self.textbox_Values_random2.configure(state="normal")
                self.textbox_Values_random2.configure(fg_color="white")

        elif current_option == "Map":
            if value == "geo":
                # disable first and second textboxs on Geo section or Random Section
                self.textbox_Values_geo1.configure(state="disabled")
                self.textbox_Values_geo1.configure(fg_color="#E7E7E7")
                self.textbox_Values_geo2.configure(state="disabled")
                self.textbox_Values_geo2.configure(fg_color="#E7E7E7")
            elif value == "rand":
                self.textbox_Values_random1.configure(state="disabled")
                self.textbox_Values_random1.configure(fg_color="#E7E7E7")
                self.textbox_Values_random2.configure(state="disabled")
                self.textbox_Values_random2.configure(fg_color="#E7E7E7")

    def switch_presence_State_geo(self):
        """The function decides the ability to write values in the first entry box"""
        current_state = self.switch_Presence_geo.get()

        if current_state == 0:
            self.textbox_Presence_geo1.configure(state="disabled")
            self.textbox_Presence_geo1.configure(state="disabled")
            self.textbox_Presence_geo1.configure(fg_color="#E7E7E7")
        else:
            self.textbox_Presence_geo1.configure(state="normal")
            self.textbox_Presence_geo1.configure(fg_color="white")

    def restriction_window(self):
        """Will Create a new window Class of the restrictions functionalities outside of the main GUI"""
        Restrictions.RestrictionsWindow(self.restriction_box, self.restriction_button)

    def Browse_saving_path(self):
        """The function opens UI window for finding a saving path for Editor new generated files
        the variable: self.controller.shared_data["EditorSavingPath"], the path assigned to it"""
        folder_path = tkinter.filedialog.askdirectory()
        if folder_path:
            self.controller.shared_data["EditorSavingPath"].set(folder_path)

    def Create_Feature_List_For_BMS(self):
        # Check all requests before continue to the algorithm
        ## Set Version of Software:
        # Initialize logger for this function
        import logging
        logger = logging.getLogger(__name__)
        
        BuildingGeneratorVer = self.controller.shared_data["BuildingGeneratorVer"].get()

        generating_method = self.segemented_button.get()
        saving_method = self.saving_method_var.get()
        
        # Validate incompatible combinations of generation method and graph display options
        # Get selected graph options from both segmented buttons
        graph_option_1 = self.segemented_button_graphing1.get()
        graph_option_2 = self.segemented_button_graphing2.get()
        
        # Check if Random Selection is combined with Geo-based graph options
        if generating_method == "Random Selection":
            # List of graph options that require GeoData
            geo_graph_options = ["2D Geo", "3D Geo", "2D Both", "3D Both"]
            
            # Check if any geo-based graph option is selected
            selected_geo_graph = (graph_option_1 in geo_graph_options) or (graph_option_2 in geo_graph_options)
            
            if selected_geo_graph:
                logger.warning(f"Invalid combination detected: Random Selection with {graph_option_1 or graph_option_2}")
                messagebox.showerror(
                    "Invalid Configuration",
                    "Random Selection cannot be used with geodata-based graph options.\n\n"
                    f"Current selection:\n"
                    f"• Generation Method: {generating_method}\n"
                    f"• Graph Display: {graph_option_1 or graph_option_2}\n\n"
                    "Please either:\n"
                    "1. Switch to 'GeoJson' method\n"
                    "2. Select '2D Fit', '3D Fit' for graph display\n"
                    "3. Remove Graph display options"
                )
                return  # Abort generation
        
        # Make CT path from shared_data available to MainCode
        import MainCode
        if not hasattr(MainCode, "shared_data"):
            MainCode.shared_data = self.controller.shared_data

        # ##########  GeoJson Generating method part ##########
        if generating_method == "GeoJson":
            # Check if geo-data calculated already
            if "Calc_Geodata" in self.controller.shared_data:
                GeoFeatures = self.controller.shared_data["Geodata"]
                CalcData_GeoFeatures = self.controller.shared_data["Calc_Geodata"]
                AOI_center = self.controller.shared_data["Geo_AOI_center"]

                # Check if database is available
                if self.controller.shared_data["Database_Availability"].get() == "1":
                    DB_path = self.controller.shared_data["BMS_Database_Path"].get()
                    num_features = max(min(int(self.textbox_Amount_geo.get()), 256), 1)

                    # Prepere values of features through the option menu selection
                    if self.values_geo_optionmenu.get() == "Solid":
                        Values = max(min(int(self.textbox_Values_geo2.get()), 100), 0)
                        Values_i = None
                        logger.debug(f"Set Solid value: Values={Values}, Values_i=None")

                    elif self.values_geo_optionmenu.get() == "Random":
                        Values = max(min(int(self.textbox_Values_geo2.get()), 100), 0)
                        Values_i = max(
                            min(int(self.textbox_Values_geo1.get()), Values), 0
                        )
                        logger.debug(f"Set Random value range: Values_i={Values_i}, Values={Values}")
                    else:  # Map mode
                        Values = None
                        Values_i = None
                        logger.debug(f"Set Map mode: Values=None, Values_i=None")
                    
                    # Prepere Presence of features through the Switch selection
                    Presence = max(min(int(self.textbox_Presence_geo2.get()), 100), 0)
                    # If range of presence is found set it in variable
                    if self.switch_Presence_geo.get() == 1:
                        Presence_i = max(
                            min(int(self.textbox_Presence_geo1.get()), Presence), 0
                        )
                    else:
                        Presence_i = None

                    # Get Floor height and floor deviation from Geodata page for height deviation functionality
                    if self.controller.frames["GeoDataPage"].is_floor_height_not_valid(
                        self.floor_deviation_entry
                    ):
                        floor_deviation = 0
                    else:
                        floor_deviation = float(self.floor_deviation_entry.get())

                    if self.controller.frames["GeoDataPage"].is_floor_height_not_valid(
                        self.controller.frames["GeoDataPage"].textbox_floor_height
                    ):
                        floor_height = 2.286
                    else:
                        floor_height = float(
                            self.controller.frames[
                                "GeoDataPage"
                            ].textbox_floor_height.get()
                        )

                    fillter = self.Fillter_optionmenu.get()
                    selection = self.Selection_optionmenu.get()

                    restriction_text = self.restriction_box.get("0.0", "end")

                    # Import the processing window functionality
                    from processing_window import run_with_processing
                    
                    # Capture current values of all variables needed in the task
                    _num_features = num_features
                    _db_path = DB_path
                    _restriction_text = restriction_text
                    _fillter = fillter
                    _geo_features = GeoFeatures
                    _calc_data_geo_features = CalcData_GeoFeatures
                    
                    # Define the feature generation task that will run in the background thread
                    def generate_features_task(processing_window):
                        try:
                            # Update the message to show feature generation is in progress if possible
                            try:
                                # Try to update the message if it's a ProcessingWindow instance
                                if hasattr(processing_window, 'update_message'):
                                    processing_window.update_message(f"Generating {_num_features} features using {_fillter} filter...")
                                # If it's a Toplevel, try to update a label if it exists
                                elif hasattr(processing_window, 'children'):
                                    # Look for labels in the window's children
                                    for widget in processing_window.children.values():
                                        if isinstance(widget, tk.Label) or \
                                           (hasattr(widget, 'winfo_class') and widget.winfo_class() == 'Label'):
                                            widget.config(text=f"Generating {_num_features} features using {_fillter} filter...")
                                            break
                            except Exception as update_error:
                                # If updating the UI fails, just log it and continue
                                # Use the logger from outer scope
                                logger.warning(f"Could not update processing window: {update_error}")
                            
                            # Call the feature generation function
                            result = Assign_features_accuratly(
                                _num_features,
                                _db_path,
                                _restriction_text,
                                _fillter,
                                _geo_features,
                                _calc_data_geo_features,
                            )
                            
                            # Return the result
                            return result
                        except Exception as e:
                            import traceback
                            error_details = traceback.format_exc()
                            # Use the logger from outer scope
                            logger.error(f"Feature generation error: {error_details}")
                            raise
                    
                    # Run the feature generation task with a processing window
                    result = run_with_processing(
                        parent=self.controller,
                        task_function=generate_features_task,
                        title="Generating Features",
                        message="Initializing feature generation..."
                    )
                    
                    # Unpack the results
                    (
                        Filltered_models,
                        self.Filltered_GeoFeatures,
                        self.Filltered_Calc_GeoFeatures,
                    ) = result

                    if saving_method == "Editor":
                        # initiate variables
                        file_save_path = os.path.join(
                            self.controller.shared_data["EditorSavingPath"].get(),
                            self.Editor_Extraction_name.get() + ".txt",
                        )
                        # Capture current values of all variables needed in the task
                        _saving_method = saving_method
                        _num_features = num_features
                        _filltered_geo_features = self.Filltered_GeoFeatures
                        _filltered_calc_geo_features = self.Filltered_Calc_GeoFeatures
                        _db_path = DB_path
                        _filltered_models = Filltered_models
                        _selection = selection
                        _file_save_path = file_save_path
                        _aoi_center = AOI_center
                        _presence = Presence
                        _values = Values
                        _presence_i = Presence_i
                        _values_i = Values_i
                        _auto_features = self.Auto_features_detector.get()
                        _building_generator_ver = BuildingGeneratorVer
                        _sorting_saving = self.sorting_saving.get()
                        _floor_height = floor_height
                        _floor_deviation = floor_deviation
                        _ct_num = int(self.textbox_CT.get()) if self.textbox_CT.get() and self.saving_method_var.get() == "BMS" else None
                        _obj_num = int(self.textbox_Obj.get()) if self.textbox_Obj.get() and self.saving_method_var.get() == "BMS" else None
                        
                        # Define the feature saving task that will run in the background thread
                        def save_features_task(processing_window):
                            nonlocal logger
                            # Import tkinter and customtkinter to ensure they're accessible in this scope
                            import tkinter as tk
                            import customtkinter as Ctk
                            
                            try:
                                # Update the message to show feature saving is in progress safely
                                # Check if the window has the update_message method (ProcessingWindow instance)
                                if hasattr(processing_window, 'update_message'):
                                    processing_window.update_message(f"Saving {_num_features} features in {_saving_method} format...")
                                # If it's a Toplevel window, try to update a label if present
                                elif hasattr(processing_window, 'children'):
                                    # Try to find labels in the window
                                    for child in processing_window.children.values():
                                        if isinstance(child, (tk.Label, Ctk.CTkLabel)) and hasattr(child, 'configure'):
                                            child.configure(text=f"Saving {_num_features} features in {_saving_method} format...")
                                            break
                                    # If no label found, add a new one
                                    else:
                                        try:
                                            new_label = tk.Label(processing_window, 
                                                                text=f"Saving {_num_features} features in {_saving_method} format...")
                                            new_label.pack(padx=20, pady=20)
                                        except Exception as label_ex:
                                            # Silent fail for UI updates
                                            pass
                                
                                # Call the feature saving function
                                result = Save_accurate_features(
                                    _saving_method,
                                    _num_features,
                                    _filltered_geo_features,
                                    _filltered_calc_geo_features,
                                    _db_path,
                                    _filltered_models,
                                    _selection,
                                    _file_save_path,
                                    _aoi_center,
                                    _presence,
                                    _values,
                                    _presence_i,
                                    _values_i,
                                    _auto_features,
                                    _building_generator_ver,
                                    _sorting_saving,
                                    _floor_height,
                                    _floor_deviation,
                                    self.controller.shared_data, # Pass shared_data
                                    _ct_num,
                                    _obj_num,
                                    "GeoJson"  # selection_type parameter
                                )
                                
                                # Return the result
                                return result
                            except Exception as e:
                                import traceback
                                error_details = traceback.format_exc()
                                logger.error(f"Feature saving error: {error_details}")
                                raise
                        
                        # Run the feature saving task with a processing window
                        self.BMS_features_map = run_with_processing(
                            parent=self.controller,
                            task_function=save_features_task,
                            title=f"Saving {saving_method} Features",
                            message="Initializing feature saving..."
                        )

                        # Update other dashboard elements as needed
                        self.controller.frames["DashboardPage"].update_pie_chart()

                        # Only show success message if save was successful
                        if self.BMS_features_map:
                            messagebox.showinfo(
                                "Operation succeeded",
                                f"Editor file with {num_features} Accurate feautures has been successfully "
                                f"generated",
                            )
                            # Will generate graph of the BMSfeatures/GeoFeatures based on the segmented button in the GUI
                            self.auto_graph_generating()

                    elif saving_method == "BMS":
                        # Debug print at start of BMS processing
                        logger.info("\n===== STARTING BMS INJECTION PROCESS =====\n")
                        
                        # Get CT and Obj numbers
                        try:
                            ct_num = int(self.textbox_CT.get())
                            obj_num = int(self.textbox_Obj.get())
                            logger.debug(f"CT number = {ct_num}, Objective number = {obj_num}")
                        except (ValueError, TypeError) as e:
                            logger.debug(f"Error parsing CT or objective numbers: {e}")
                            return messagebox.showwarning(
                                "Procedure Aborted",
                                "CT Number and Objective Number must be valid integers."
                            )
                        
                        # Import the processing window functionality if not already imported
                        from processing_window import run_with_processing
                        logger.debug("Successfully imported run_with_processing")
                        
                        # Check which method is selected: Random or GeoJSON
                        logger.debug(f"Selected method = {selection}")
                        
                        # Store common variables used by both methods
                        logger.debug("Setting up common variables")
                        _num_features = num_features
                        _db_path = DB_path
                        _file_save_path = os.path.join(
                            self.controller.shared_data["EditorSavingPath"].get(),
                            self.Editor_Extraction_name.get() + ".txt"
                        )
                        _filltered_models = Filltered_models
                        _auto_features = self.Auto_features_detector.get()
                        _building_generator_ver = BuildingGeneratorVer
                        _sorting_saving = self.sorting_saving.get()
                        _ct_num = ct_num
                        _obj_num = obj_num
                        
                        # Define the feature saving task based on the selection method
                        if selection == "Random Selection":
                            logger.debug("\n=== USING RANDOM SELECTION FOR BMS INJECTION ===\n")
                            
                            # Get the radius for random placement
                            try:
                                _radius = float(self.textbox_Radius_random.get())
                            except (ValueError, TypeError) as e:
                                logging.getLogger(__name__).error(f"Error parsing radius: {e}")
                                return messagebox.showwarning(
                                    "Procedure Aborted",
                                    "Radius must be a valid number for Random Selection."
                                )
                                
                            # Get values and presence parameters for random selection
                            try:
                                _values_random = Values
                                _values_i_random = Values_i
                                _presence_random = Presence
                                _presence_i_random = Presence_i
                            except Exception as e:
                                logging.getLogger(__name__).error(f"Error setting random parameters: {e}")
                                import traceback
                                logging.getLogger(__name__).error(f"Traceback: {traceback.format_exc()}")
                            
                            def save_features_task_bms(processing_window):
                                try:
                                    # Get the selected distribution type
                                    distribution_type = self.distribution_selection.get()
                                    
                                    # Update the message to show random feature generation is in progress for BMS
                                    processing_window.update_message(f"Generating {_num_features} random features for BMS objective {_obj_num} using {distribution_type}...")
                                    
                                    # Log minimal but useful information
                                    logging.info(f"Using {distribution_type} for {_num_features} features with radius {_radius}")
                                    
                                    # First, generate the random features using the distribution type
                                    random_features = Assign_features_randomly(
                                        _num_features, 
                                        _radius, 
                                        _db_path, 
                                        _restriction_text, 
                                        distribution_type
                                    )
                                    
                                    if random_features is None or isinstance(random_features, TypeError):
                                        raise ValueError("Failed to generate random features")
                                        
                                    # Unpack the returned features
                                    selected_data, x_coordinates, y_coordinates = random_features
                                    
                                    # Now call Save_random_features with the generated features
                                    result = Save_random_features(
                                        "BMS",  # saving_method
                                        _num_features,
                                        selected_data,  # Use the randomly generated features
                                        x_coordinates,
                                        y_coordinates,
                                        _file_save_path,
                                        _building_generator_ver,
                                        _presence_random,
                                        _values_random,
                                        _presence_i_random,
                                        _values_i_random,
                                        _sorting_saving,
                                        self.controller.shared_data, # Pass shared_data
                                        _ct_num,
                                        _obj_num,
                                        "Random Selection"  # selection_type parameter
                                    )
                                    return result
                                except Exception as e:
                                    import traceback
                                    error_details = traceback.format_exc()
                                    logging.getLogger(__name__).error(f"Random BMS feature generation error: {error_details}")
                                    raise
                        else:  # GeoJSON selection
                            # These variables are only needed for accurate placement
                            _filltered_geo_features = self.Filltered_GeoFeatures
                            _filltered_calc_geo_features = self.Filltered_Calc_GeoFeatures
                            _selection = selection
                            _aoi_center = AOI_center
                            _presence = Presence
                            _values = Values
                            _presence_i = Presence_i
                            _values_i = Values_i
                            _auto_features = self.Auto_features_detector.get()  # FIX: Added missing auto features detection
                            _floor_height = floor_height
                            _floor_deviation = floor_deviation
                            
                            def save_features_task_bms(processing_window):
                                try:
                                    # Update the message to show feature saving is in progress for BMS if possible
                                    try:
                                        # Try to update the message if it's a ProcessingWindow instance
                                        if hasattr(processing_window, 'update_message'):
                                            processing_window.update_message(f"Injecting {_num_features} features into BMS objective {_obj_num}...")
                                        # If it's a Toplevel, try to update a label if it exists
                                        elif hasattr(processing_window, 'children'):
                                            # Look for labels in the window's children
                                            for widget in processing_window.children.values():
                                                if isinstance(widget, tk.Label) or \
                                                   (hasattr(widget, 'winfo_class') and widget.winfo_class() == 'Label'):
                                                    widget.config(text=f"Injecting {_num_features} features into BMS objective {_obj_num}...")
                                                    break
                                    except Exception as update_error:
                                        # If updating the UI fails, just log it and continue
                                        logging.getLogger(__name__).warning(f"Could not update processing window: {update_error}")
                                    
                                    # Call the feature saving function with BMS parameters
                                    return Save_accurate_features(
                                        "BMS",  # saving_method
                                        _num_features,
                                        _filltered_geo_features,
                                        _filltered_calc_geo_features,
                                        _db_path,
                                        _filltered_models,
                                        _selection,
                                        _file_save_path,
                                        _aoi_center,
                                        _presence,
                                        _values,
                                        _presence_i,
                                        _values_i,
                                        _auto_features,
                                        _building_generator_ver,
                                        _sorting_saving,
                                        _floor_height,
                                        _floor_deviation,
                                        self.controller.shared_data, # Pass shared_data
                                        _ct_num,
                                                                                _obj_num,
                                        "GeoJson"  # selection_type parameter
                                    )
                                except Exception as e:
                                    import traceback
                                    error_details = traceback.format_exc()
                                    logging.getLogger(__name__).error(f"GeoJSON BMS feature generation error: {error_details}")
                                    raise
                        
                        try:
                            self.BMS_features_map = run_with_processing(
                                parent=self.controller,
                                task_function=save_features_task_bms,
                                title="Injecting Features into BMS",
                                message="Initializing BMS feature injection..."
                            )
                        except Exception as e:
                            logging.getLogger(__name__).error(f"Error in BMS injection: {str(e)}")
                            import traceback
                            logging.getLogger(__name__).error(f"Traceback: {traceback.format_exc()}")
                            raise
                        
                        # Update other dashboard elements as needed
                        try:
                            self.controller.frames["DashboardPage"].update_pie_chart()
                        except Exception as e:
                            logging.getLogger(__name__).warning(f"Error updating dashboard: {str(e)}")
                        
                        # Only show success message if BMS injection was successful
                        if self.BMS_features_map:
                            messagebox.showinfo(
                                "Operation succeeded",
                                f"Successfully injected {num_features} accurate features into BMS objective {obj_num}."
                            )
                            # Will generate graph of the BMSfeatures/GeoFeatures based on the segmented button in the GUI
                            self.auto_graph_generating()

                else:
                    # if Database_Availability is 0, place error (no valid db)
                    return messagebox.showwarning(
                        "Procedure Aborted",
                        "Error: Database is unavailable\n"
                        "Make sure it selected properly",
                    )
            else:
                # if Geodata is empty, place error (no valid geodata)
                return messagebox.showwarning(
                    "Procedure Aborted",
                    "Error: Geodata is unavailable\n" "Make sure it selected properly",
                )
        ########## for Random Selection algorithm part ##########
        elif generating_method == "Random Selection":
            # Check if database is available, block radius, num of features, values and presences between (0-100) or (1-256)
            if self.controller.shared_data["Database_Availability"].get() == "1":
                DB_path = self.controller.shared_data["BMS_Database_Path"].get()
                try:
                    Radius = max(int(self.textbox_Radius_random.get()), 1)
                    num_features = max(
                        min(int(self.textbox_Amount_random.get()), 256), 1
                    )

                    # Prepere values of features through the option menu selection
                    if self.values_rand_optionmenu.get() == "Solid":
                        Values = max(
                            min(int(self.textbox_Values_random2.get()), 100), 0
                        )
                        Values_i = None

                    elif self.values_rand_optionmenu.get() == "Random":
                        Values = max(
                            min(int(self.textbox_Values_random2.get()), 100), 0
                        )
                        Values_i = max(
                            min(int(self.textbox_Values_random1.get()), Values), 0
                        )
                    else:
                        Values = None
                        Values_i = None

                    # Prepere presence of features through the switch selection
                    Presence = max(
                        min(int(self.textbox_Presence_random2.get()), 100), 0
                    )
                    if self.switch_Presence_geo.get() == 1:
                        # If range of presence is found set it in variable
                        Presence_i = max(
                            min(int(self.textbox_Presence_random1.get()), Presence), 0
                        )
                    else:
                        Presence_i = None

                    restriction_text = self.restriction_box.get("0.0", "end")

                # missing critical values will cause error
                except:
                    return messagebox.showwarning(
                        "Procedure Aborted",
                        "Some Values are missing\n" "Make sure it selected properly",
                    )

                if saving_method == "Editor":
                    # Import the processing window functionality if not already imported
                    from processing_window import run_with_processing
                    
                    # Get the file save path - file override will be handled by FileManager later
                    file_save_path = os.path.join(
                        self.controller.shared_data["EditorSavingPath"].get(),
                        self.Editor_Extraction_name.get() + ".txt",
                    )
                    
                    # Now capture all variables needed in the task
                    _num_features = num_features
                    _radius = Radius
                    _db_path = DB_path
                    _restriction_text = restriction_text
                    _file_save_path = file_save_path
                    
                    # Define the random feature generation task that will run in the background thread
                    def random_features_task(processing_window):
                        # Ensure logger is visible in this scope
                        nonlocal logger
                        
                        try:
                            # Update the message to show feature generation is in progress if possible
                            try:
                                # Try to update the message if it's a ProcessingWindow instance
                                if hasattr(processing_window, 'update_message'):
                                    processing_window.update_message("Preparing random feature generation...")
                                # If it's a Toplevel, try to update a label if it exists
                                elif hasattr(processing_window, 'children'):
                                    # Look for labels in the window's children
                                    for widget in processing_window.children.values():
                                        if isinstance(widget, tk.Label) or \
                                           (hasattr(widget, 'winfo_class') and widget.winfo_class() == 'Label'):
                                            widget.config(text="Preparing random feature generation...")
                                            break
                            except Exception as update_error:
                                # If updating the UI fails, just log it and continue
                                logger.warning(f"Could not update processing window: {update_error}")
                            
                            # Get the selected distribution type
                            distribution_type = self.distribution_selection.get()
                            
                            # Log message instead of updating processing window
                            logger.debug(f"[PROCESSING WINDOW] Generating {_num_features} random features with {_radius} radius using {distribution_type}...")
                            
                            # Call the random feature generation function with distribution type
                            return Assign_features_randomly(
                                _num_features, _radius, _db_path, _restriction_text, distribution_type
                            )
                        except Exception as e:
                            import traceback
                            error_details = traceback.format_exc()
                            logging.getLogger(__name__).error(f"Random feature generation error: {error_details}")
                            raise
                    
                    # Run the random feature generation task with a processing window
                    result = run_with_processing(
                        parent=self.controller,
                        task_function=random_features_task,
                        title="Generating Random Features",
                        message="Initializing random feature generation..."
                    )
                    
                    # Check if result is valid (not None or False) and has the expected format
                    if not result or not isinstance(result, tuple) or len(result) != 3:
                        logging.getLogger(__name__).error(f"Invalid result from random feature generation: {result}")
                        return messagebox.showerror("Error", "Failed to generate random features. Check the console for details.")
                    
                    # Get the generated features
                    selected_data, x_coordinates, y_coordinates = result

                    # Capture current values of all variables needed in the task
                    _saving_method = saving_method
                    _num_features = num_features
                    _selected_data = selected_data
                    _x_coordinates = x_coordinates
                    _y_coordinates = y_coordinates
                    _file_save_path = file_save_path
                    _building_generator_ver = BuildingGeneratorVer
                    _presence = Presence
                    _values = Values
                    _presence_i = Presence_i
                    _values_i = Values_i
                    _sorting_saving = self.sorting_saving.get()
                    
                    # Define the random feature saving task that will run in the background thread
                    def save_random_features_task(processing_window):
                        # Ensure logger is visible in this scope
                        nonlocal logger
                        
                        try:
                            # Update the message to show feature saving is in progress if possible
                            try:
                                # Try to update the message if it's a ProcessingWindow instance
                                if hasattr(processing_window, 'update_message'):
                                    processing_window.update_message(f"Saving {_num_features} random features...")
                                # If it's a Toplevel, try to update a label if it exists
                                elif hasattr(processing_window, 'children'):
                                    # Look for labels in the window's children
                                    for widget in processing_window.children.values():
                                        if isinstance(widget, tk.Label) or \
                                           (hasattr(widget, 'winfo_class') and widget.winfo_class() == 'Label'):
                                            widget.config(text=f"Saving {_num_features} random features...")
                                            break
                            except Exception as update_error:
                                # If updating the UI fails, just log it and continue
                                logger.warning(f"Could not update processing window: {update_error}")
                            
                            # Proceed with saving the features
                            
                            # Call the random feature saving function
                            return Save_random_features(
                                _saving_method,
                                _num_features,
                                _selected_data,
                                _x_coordinates,
                                _y_coordinates,
                                _file_save_path,
                                _building_generator_ver,
                                _presence,
                                _values,
                                _presence_i,
                                _values_i,
                                _sorting_saving,
                                self.controller.shared_data, # Pass shared_data
                                None,  # CT_Num
                                None,  # Obj_Num
                                "Random Selection"  # selection_type parameter
                            )
                        except Exception as e:
                            import traceback
                            error_details = traceback.format_exc()
                            logging.getLogger(__name__).error(f"Random feature saving error: {error_details}")
                            raise
                    
                    # Run the random feature saving task with a processing window
                    result = run_with_processing(
                        parent=self.controller,
                        task_function=save_random_features_task,
                        title=f"Saving Random Features",
                        message="Initializing random feature saving..."
                    )
                    
                    # Check if the result is valid
                    if result is None or result is False:
                        logging.getLogger(__name__).error(f"Invalid result from random feature saving: {result}")
                        return messagebox.showerror("Error", "Failed to save random features. Check the console for details.")
                    
                    # Set the result to BMS_features_map
                    self.BMS_features_map = result

                    # Update other dashboard elements as needed
                    self.controller.frames["DashboardPage"].update_pie_chart()

                    # Only show success message if save was successful
                    if self.BMS_features_map:
                        messagebox.showinfo(
                            "Operation succeeded",
                            f"Editor file with {num_features} Random feautures has been successfully "
                            f"generated",
                        )

                        # Will generate graph of the BMSfeatures/GeoFeatures based on the segmented button in the GUI
                        self.auto_graph_generating()

                elif saving_method == "BMS":
                    try:
                        # Get CT and Obj numbers
                        ct_num = int(self.textbox_CT.get())
                        obj_num = int(self.textbox_Obj.get())
                        
                        # Check if CT and Obj numbers are valid (must be greater than 0)
                        if ct_num <= 0 or obj_num <= 0:
                            return messagebox.showwarning(
                                "Procedure Aborted",
                                "CT Number and Objective Number must be greater than 0."
                            )
                    except (ValueError, TypeError):
                        return messagebox.showwarning(
                            "Procedure Aborted",
                            "CT Number and Objective Number must be valid integers."
                        )
                    
                    # Import the processing window functionality if not already imported
                    from processing_window import run_with_processing
                    
                    # Get the file save path - file override will be handled later
                    file_save_path = os.path.join(
                        self.controller.shared_data["EditorSavingPath"].get(),
                        self.Editor_Extraction_name.get() + ".txt",
                    )
                    
                    # Capture all variables needed for the background task
                    _num_features = num_features
                    _radius = Radius
                    _db_path = DB_path
                    _restriction_text = restriction_text
                    _file_save_path = file_save_path
                    _building_generator_ver = BuildingGeneratorVer 
                    _presence = Presence
                    _values = Values
                    _presence_i = Presence_i 
                    _values_i = Values_i
                    _sorting_option = self.sorting_saving.get()
                    _ct_num = ct_num
                    _obj_num = obj_num
                    
                    # Define the task function that will run in the background thread
                    def random_bms_task(processing_window):
                        # Ensure logger is visible in this scope
                        nonlocal logger
                        
                        try:
                            # Update the message to show feature generation is in progress if possible
                            try:
                                # Try to update the message if it's a ProcessingWindow instance
                                if hasattr(processing_window, 'update_message'):
                                    processing_window.update_message("Preparing random feature generation...")
                                # If it's a Toplevel, try to update a label if it exists
                                elif hasattr(processing_window, 'children'):
                                    # Look for labels in the window's children
                                    for widget in processing_window.children.values():
                                        if isinstance(widget, tk.Label) or \
                                           (hasattr(widget, 'winfo_class') and widget.winfo_class() == 'Label'):
                                            widget.config(text="Preparing random feature generation...")
                                            break
                            except Exception as update_error:
                                # If updating the UI fails, just log it and continue
                                logger.warning(f"Could not update processing window: {update_error}")
                            
                            # Get the selected distribution type
                            distribution_type = self.distribution_selection.get()
                            
                            # Update processing window with current task
                            try:
                                if hasattr(processing_window, 'update_message'):
                                    processing_window.update_message(f"Generating {_num_features} random features...")
                            except Exception:
                                pass
                                
                            # Step 1: Generate random features
                            random_result = Assign_features_randomly(
                                _num_features, _radius, _db_path, _restriction_text, distribution_type
                            )
                            
                            if isinstance(random_result, Exception):
                                raise ValueError("No features found matching the restrictions.")
                                
                            selected_data, x_coordinates, y_coordinates = random_result
                            
                            # Step 2: Save features to BMS
                            # Note: can't update processing window message since we don't have the parameter
                            
                            return Save_random_features(
                                "BMS",  # saving_method
                                _num_features,
                                selected_data,
                                x_coordinates,
                                y_coordinates,
                                _file_save_path,
                                _building_generator_ver,
                                _presence,
                                _values,
                                _presence_i,
                                _values_i,
                                _sorting_option,
                                self.controller.shared_data, # Pass shared_data
                                _ct_num,
                                _obj_num,
                                "Random Selection"  # selection_type parameter
                            )
                        except Exception as e:
                            import traceback
                            error_details = traceback.format_exc()
                            logging.getLogger(__name__).error(f"Random BMS feature generation error: {error_details}")
                            raise
                    
                    # Run the task with a processing window
                    self.BMS_features_map = run_with_processing(
                        parent=self.controller,
                        task_function=random_bms_task,
                        title="BMS Random Feature Injection",
                        message="Initializing random feature generation for BMS..."
                    )

                    # Update other dashboard elements as needed
                    self.controller.frames["DashboardPage"].update_pie_chart()

                    # Only show success message if save was successful
                    if self.BMS_features_map:
                        messagebox.showinfo(
                            "Operation succeeded",
                            f"Successfully injected {num_features} features into BMS objective {obj_num}."
                        )

                        # Will generate graph of the BMSfeatures/GeoFeatures based on the segmented button in the GUI
                        self.auto_graph_generating()

    # Add a new method for handling save method switching
    def switch_save_method(self, value):
        """Handle switching between Editor and BMS save methods"""
        if value == "BMS":
            # Enable CT and Objective number fields for initial entry
            self.textbox_CT.configure(state="normal")
            self.textbox_Obj.configure(state="normal")
            
            # Make them required by changing background color
            self.textbox_CT.configure(fg_color="#F0F8FF")
            self.textbox_Obj.configure(fg_color="#F0F8FF")
            
            # Enable the More button for BMS injection
            self.Get_More_button.configure(state="normal")
            
            # If values are already entered, disable editing
            if self.textbox_CT.get() and self.textbox_Obj.get():
                self.textbox_CT.configure(state="disable")
                self.textbox_Obj.configure(state="disable")
        else:
            # Reset to disabled state
            self.textbox_CT.configure(state="disable")
            self.textbox_Obj.configure(state="disable")
            
            # Reset background color
            self.textbox_CT.configure(fg_color="#F9F9FA")
            self.textbox_Obj.configure(fg_color="#F9F9FA")
            
            # Disable the More button for BMS injection
            self.Get_More_button.configure(state="disabled")

    # Add new methods for BMS injection functionality
    def open_bms_injection_window(self):
        """
        Open the BMS Injection Configuration window from the Preferences button.
        
        This method opens the BMS Injection Configuration window allowing users to
        configure objective properties for injection. It passes the current CT and
        objective numbers to the window if they are available, and updates these
        values in the main UI when the user saves their settings.
        """
        # Initialize logger for this function
        import logging
        logger = logging.getLogger(__name__)
        
        try:
            from components.bms_injection_window import BmsInjectionWindow
            
            # Get CT and Obj numbers if available
            try:
                ct_num = int(self.textbox_CT.get()) if self.textbox_CT.get() else None
                obj_num = int(self.textbox_Obj.get()) if self.textbox_Obj.get() else None
            except ValueError:
                ct_num = None
                obj_num = None
            
            # Get BMS path from the CT file path
            bms_path = os.path.dirname(self.controller.shared_data["CTpath"].get())
            
            # Create and show the window
            window = BmsInjectionWindow(
                self,
                ct_num=ct_num,
                obj_num=obj_num,
                bms_path=bms_path
            )
            
            # Register the child window for proper cleanup
            self.controller.register_child_window(window)
            
            # Set up cleanup when window is destroyed
            def on_bms_window_destroy():
                self.controller.unregister_child_window(window)
            
            # Bind cleanup to window destruction
            window.bind("<Destroy>", lambda e: on_bms_window_destroy())
            
            # When window closes, update CT and Obj numbers if available
            self.wait_window(window)
            
            # Debug: Print if window has result attribute
            logger.debug(f"Window has result attribute: {hasattr(window, 'result')}")
            
            if hasattr(window, 'result') and window.result.get("status") == "success":
                # Only update if the user successfully saved settings
                if "ct_num" in window.result and "obj_num" in window.result:
                    # Enable the entries in case they're disabled
                    if self.textbox_CT.cget("state") == "disable":
                        self.textbox_CT.configure(state="normal")
                    if self.textbox_Obj.cget("state") == "disable":
                        self.textbox_Obj.configure(state="normal")
                    
                    # Update the entries with the new values
                    self.textbox_CT.delete(0, "end")
                    self.textbox_CT.insert(0, str(window.result["ct_num"]))
                    
                    self.textbox_Obj.delete(0, "end")
                    self.textbox_Obj.insert(0, str(window.result["obj_num"]))
                    
                    # If BMS mode is not active, switch to it
                    if self.saving_method_var.get() != "BMS":
                        self.segemented_button_Saving.set("BMS")
                        self.switch_save_method("BMS")
                    else:
                        # Make sure entries are disabled if BMS mode is already active
                        self.textbox_CT.configure(state="disable")
                        self.textbox_Obj.configure(state="disable")
                    
                    # Debug: Print updated values
                    logger.debug(f"Updated CT: {self.textbox_CT.get()}, Obj: {self.textbox_Obj.get()}")
                else:
                    logger.debug("BMS window result missing ct_num or obj_num")
            elif hasattr(window, 'result'):
                # Window was cancelled or had an error
                logger.debug(f"BMS window closed with status: {window.result.get('status', 'unknown')}")
            else:
                logger.debug("BMS window closed without result")
                
        except Exception as e:
            messagebox.showerror(
                "Error",
                f"Could not open BMS Injection window: {str(e)}"
            )
    
    def browse_objective_numbers(self):
        """Open a window to browse and select available objective numbers"""
        try:
            # Get BMS path
            bms_path = os.path.dirname(self.controller.shared_data["CTpath"].get())
            obj_dir = os.path.join(bms_path, "ObjectiveRelatedData")
            
            if not os.path.exists(obj_dir):
                messagebox.showwarning(
                    "Warning",
                    f"ObjectiveRelatedData directory not found at {obj_dir}"
                )
                return
            
            # Get list of existing objectives
            obj_numbers = []
            for entry in os.listdir(obj_dir):
                if entry.startswith("OCD_") and os.path.isdir(os.path.join(obj_dir, entry)):
                    try:
                        obj_num = int(entry.split("_")[1])
                        obj_numbers.append(obj_num)
                    except (ValueError, IndexError):
                        pass
            
            if not obj_numbers:
                messagebox.showinfo(
                    "Information",
                    "No existing objectives found. You can create a new one by entering a number."
                )
                return
            
            # Create a simple selection dialog
            selection_dialog = tk.Toplevel(self)
            selection_dialog.title("Select Objective Number")
            selection_dialog.geometry("300x400")
            selection_dialog.transient(self)
            selection_dialog.grab_set()
            
            # Register the child window for proper cleanup
            self.controller.register_child_window(selection_dialog)
            
            # Set up cleanup when window is destroyed
            def on_obj_dialog_destroy():
                self.controller.unregister_child_window(selection_dialog)
            
            selection_dialog.bind("<Destroy>", lambda e: on_obj_dialog_destroy())
            
            # Create listbox with objectives
            listbox = tk.Listbox(selection_dialog)
            listbox.pack(fill="both", expand=True, padx=10, pady=10)
            
            # Sort objective numbers
            obj_numbers.sort()
            
            # Add objectives to listbox
            for obj_num in obj_numbers:
                listbox.insert("end", f"Objective {obj_num}")
            
            # Add a selection button
            def on_select():
                selection = listbox.curselection()
                if selection:
                    obj_num = obj_numbers[selection[0]]
                    self.textbox_Obj.delete(0, "end")
                    self.textbox_Obj.insert(0, str(obj_num))
                selection_dialog.destroy()
            
            button = tk.Button(selection_dialog, text="Select", command=on_select)
            button.pack(pady=10)
            
        except Exception as e:
            messagebox.showerror(
                "Error",
                f"Error browsing objectives: {str(e)}"
            )
    
    def browse_ct_numbers(self):
        """Open a window to browse and select available CT numbers"""
        try:
            # Get BMS path and CT file
            ct_file_path = self.controller.shared_data["CTpath"].get()
            
            if not os.path.exists(ct_file_path):
                messagebox.showwarning(
                    "Warning",
                    f"CT file not found at {ct_file_path}"
                )
                return
            
            # Parse CT file to find objectives
            import xml.etree.ElementTree as ET
            tree = ET.parse(ct_file_path)
            root = tree.getroot()
            
            # Find objectives (EntityType=3)
            objective_cts = []
            for ct in root.findall("CT"):
                try:
                    ct_num = int(ct.get("Num"))
                    entity_type = int(ct.find("EntityType").text)
                    
                    if entity_type == 3:
                        # It's an objective
                        objective_type = int(ct.find("Type").text)
                        objective_cts.append((ct_num, objective_type))
                except (ValueError, AttributeError, TypeError):
                    pass
            
            if not objective_cts:
                messagebox.showinfo(
                    "Information",
                    "No objective CTs found in the CT file."
                )
                return
            
            # Create a simple selection dialog
            selection_dialog = tk.Toplevel(self)
            selection_dialog.title("Select CT Number")
            selection_dialog.geometry("300x400")
            selection_dialog.transient(self)
            selection_dialog.grab_set()
            
            # Register the child window for proper cleanup
            self.controller.register_child_window(selection_dialog)
            
            # Set up cleanup when window is destroyed
            def on_ct_dialog_destroy():
                self.controller.unregister_child_window(selection_dialog)
            
            selection_dialog.bind("<Destroy>", lambda e: on_ct_dialog_destroy())
            
            # Create listbox with CT numbers
            listbox = tk.Listbox(selection_dialog, width=40)
            listbox.pack(fill="both", expand=True, padx=10, pady=10)
            
            # Sort CT numbers
            objective_cts.sort()
            
            # Add CT numbers to listbox
            for ct_num, obj_type in objective_cts:
                listbox.insert("end", f"CT {ct_num} (Objective Type {obj_type})")
            
            # Add a selection button
            def on_select():
                selection = listbox.curselection()
                if selection:
                    ct_num = objective_cts[selection[0]][0]
                    self.textbox_CT.delete(0, "end")
                    self.textbox_CT.insert(0, str(ct_num))
                selection_dialog.destroy()
            
            button = tk.Button(selection_dialog, text="Select", command=on_select)
            button.pack(pady=10)
            
        except Exception as e:
            messagebox.showerror(
                "Error",
                f"Error browsing CT numbers: {str(e)}"
                )
    

class FootPrintsPage(tk.Frame):
    def __init__(self, parent, controller):
        tk.Frame.__init__(self, parent)
        self.controller = controller
        self.configure(bg="#ffffff")

        self.Body_font = Ctk.CTkFont(family="Inter", size=15)
        self.Body_font_Bold = Ctk.CTkFont(family="Inter", size=15, weight="bold")
        self.button_font = Ctk.CTkFont(family="Inter", size=12)

        self.canvas = Canvas(
            self,
            bg="#FFFFFF",
            height=720,
            width=1152,
            bd=0,
            highlightthickness=0,
            relief="ridge",
        )
        self.canvas.place(x=0, y=0)
        self.canvas.create_rectangle(0.0, 0.0, 204.0, 720.0, fill="#A0B9D0", outline="")

        # Left navigation buttons (match style)
        self.button_operations_img = Ctk.CTkImage(
            light_image=Image.open(str(self.controller.ASSETS_PATH / "button_operations.png"))
        )
        self.button_geo_img = Ctk.CTkImage(
            light_image=Image.open(str(self.controller.ASSETS_PATH / "button_geo.png"))
        )
        self.button_data_img = Ctk.CTkImage(
            light_image=Image.open(str(self.controller.ASSETS_PATH / "button_data.png"))
        )
        self.button_dash_img = Ctk.CTkImage(
            light_image=Image.open(str(self.controller.ASSETS_PATH / "button_dash.png"))
        )
        self.button_settings_img = Ctk.CTkImage(
            light_image=Image.open(str(self.controller.ASSETS_PATH / "button_options.png"))
        )
        self.button_footprints_img = Ctk.CTkImage(
            light_image=Image.open(str(self.controller.ASSETS_PATH / "button_footprint.png")),
            size=(21, 17)
        )

        self.button_operations = Ctk.CTkButton(
            self,
            text="Operations",
            fg_color="#A1B9D0",
            bg_color="#A1B9D0",
            image=self.button_operations_img,
            height=33,
            width=167,
            command=lambda: controller.show_frame("OperationPage"),
            corner_radius=0,
            hover_color="#7A92A9",
            font=("arial", 15),
            text_color="#000000",
        )
        self.button_operations.place(x=0, y=397)

        self.button_geo = Ctk.CTkButton(
            self,
            text="GeoData",
            fg_color="#A1B9D0",
            bg_color="#A1B9D0",
            image=self.button_geo_img,
            height=33,
            width=167,
            command=lambda: controller.show_frame("GeoDataPage"),
            corner_radius=0,
            hover_color="#7A92A9",
            font=("Sans Font", 15),
            text_color="#000000",
        )
        self.button_geo.place(x=0, y=349)

        self.button_data = Ctk.CTkButton(
            self,
            text="Database",
            fg_color="#A1B9D0",
            bg_color="#A1B9D0",
            image=self.button_data_img,
            height=33,
            width=167,
            command=lambda: controller.show_frame("DatabasePage"),
            corner_radius=0,
            hover_color="#7A92A9",
            font=("Sans Font", 15),
            text_color="#000000",
        )
        self.button_data.place(x=0, y=297)

        self.button_dash = Ctk.CTkButton(
            self,
            text="DashBoard",
            fg_color="#A1B9D0",
            bg_color="#A1B9D0",
            image=self.button_dash_img,
            height=33,
            width=167,
            corner_radius=0,
            hover_color="#7A92A9",
            font=("Sans Font", 15),
            text_color="#000000",
            command=lambda: controller.show_frame("DashboardPage"),
        )
        self.button_dash.place(x=0, y=248)

        # Active page
        self.button_footprints = Ctk.CTkButton(
            self,
            text="FootPrints",
            fg_color="#7A92A9",
            bg_color="#7A92A9",
            image=self.button_footprints_img,
            height=33,
            width=167,
            hover=False,
            corner_radius=0,
            font=("Sans Font", 15),
            text_color="#000000",
        )
        self.button_footprints.place(x=0, y=445)

        self.button_settings = Ctk.CTkButton(
            self,
            text="More\nSettings",
            fg_color="#778593",
            bg_color="#A1B9D0",
            image=self.button_settings_img,
            height=97,
            width=125,
            corner_radius=20,
            hover=False,
            font=("Sans Font", 16),
            text_color="#000000",
            command=self.controller.SettingWindow,
        )
        self.button_settings.place(x=14, y=581)

        # Main area styling

        # Background images (match other pages)
        try:
            self.fp_bg_img = PhotoImage(file=str(self.controller.ASSETS_PATH / "image_BG.png"))
            self.canvas.create_image(659.0, 360.0, image=self.fp_bg_img)
            self.fp_bg_mask = PhotoImage(file=str(self.controller.ASSETS_PATH / "image_BG_mask.png"))
            self.canvas.create_image(659.0, 360.0, image=self.fp_bg_mask)
            # Draw footprints container on top of background
            self.rectangle_footprint = PhotoImage(file=str(self.controller.ASSETS_PATH / "Rectrangle_Footprint.png"))
            self.rectangle_footprint_item = self.canvas.create_image(667.0, 286.0, image=self.rectangle_footprint)
            # Ensure Benchmark Sims visuals are present (logo + titles)
            self.fp_logo = PhotoImage(file=str(self.controller.ASSETS_PATH / "image_Logo.png"))
            self.fp_logo_item = self.canvas.create_image(89.0, 39.0, image=self.fp_logo)
            try:
                self.fp_welcome = PhotoImage(file=str(self.controller.ASSETS_PATH / "image_Welcome.png"))
                self.fp_welcome_item = self.canvas.create_image(84.0, 82.0, image=self.fp_welcome)
            except Exception:
                self.fp_welcome_item = None
            try:
                self.fp_name = PhotoImage(file=str(self.controller.ASSETS_PATH / "image_Name.png"))
                self.fp_name_item = self.canvas.create_image(84.0, 116.0, image=self.fp_name)
            except Exception:
                self.fp_name_item = None
        except Exception:
            pass

        # Title
        self.canvas.create_rectangle(247.0, 90.0, 1094.0, 91.0, fill="#000000", outline="")
        try:
            self.image_image_footprints = PhotoImage(file=str(self.controller.ASSETS_PATH / "image_Features.png"))
            self.canvas.create_image(259.0, 74.0, image=self.image_image_footprints)
        except Exception:
            pass
        self.canvas.create_text(280.0, 68.0, anchor="nw", text="FootPrints", fill="#000000", font=("Inter", 15 * -1))

        # Section header for AOI / Map (moved down to avoid overlap with title)
        self.canvas.create_rectangle(247.0, 126.0, 1094.0, 127.0, fill="#000000", outline="")
        self.canvas.create_text(250.0, 104.0, anchor="nw", text="Area of Interest", fill="#000000", font=("Inter", 15 * -1))

        # Coordinate inputs
        self.canvas.create_text(247.0, 142.0, anchor="nw", text="Top-left (lat,lon)", fill="#000000", font=("Inter", 12 * -1))
        self.fp_top_left_entry = Ctk.CTkEntry(self, width=210, height=18, border_color="#D5E3F0", text_color="#565454")
        self.fp_top_left_entry.place(x=350, y=140)

        self.canvas.create_text(580.0, 142.0, anchor="nw", text="Bottom-right (lat,lon)", fill="#000000", font=("Inter", 12 * -1))
        self.fp_bottom_right_entry = Ctk.CTkEntry(self, width=210, height=18, border_color="#D5E3F0", text_color="#565454")
        self.fp_bottom_right_entry.place(x=710, y=140)

        # State and status
        self.fp_top_left = None
        self.fp_bottom_right = None
        self.fp_status_label = Ctk.CTkLabel(self, text="", bg_color="#F8F9FB")
        self.fp_status_label.place(x=250, y=155)

        # Actions for coords
        self.fp_update_btn = Ctk.CTkButton(self, text="Update BBox", fg_color="#8DBBE7", width=80, height=20, command=self._on_update_bbox)
        self.fp_update_btn.place(x=930, y=140)
        self.fp_fit_btn = Ctk.CTkButton(self, text="Fit BBox", fg_color="#A7A7A7", width=70, height=20, state="disabled")
        self.fp_fit_btn.place(x=1022, y=140)

        # Bind entry events
        self.fp_top_left_entry.bind("<FocusOut>", lambda e: self._on_update_bbox())
        self.fp_top_left_entry.bind("<Return>", lambda e: self._on_update_bbox())
        self.fp_bottom_right_entry.bind("<FocusOut>", lambda e: self._on_update_bbox())
        self.fp_bottom_right_entry.bind("<Return>", lambda e: self._on_update_bbox())

        # Map region: initialize tkintermapview (show specific errors if it fails)
        self.canvas.create_text(250.0, 180.0, anchor="nw", text="Area of Interest Map", fill="#000000", font=("Inter", 14 * -1))
        self._map_mode = None
        self._bbox_polygon = None
        try:
            from tkintermapview import TkinterMapView  # type: ignore
        except Exception as e:
            # tkintermapview not importable → show install hint
            self._map_mode = "missing"
            try:
                import logging as _logging
                _logging.getLogger(__name__).error(f"tkintermapview import failed: {e}")
                self.map_hint = Ctk.CTkLabel(self, text="Interactive map unavailable. Install: pip install tkintermapview", bg_color="#F8F9FB", text_color="#565454")
                self.map_hint.place(x=250, y=470)
                self.map_install_btn = Ctk.CTkButton(self, text="Install Map Support", fg_color="#8DBBE7", width=150, height=20, command=self._install_map_support)
                self.map_install_btn.place(x=720, y=468)
                self.fp_fit_btn.configure(state="disabled")
            except Exception:
                pass
        else:
            try:
                self.map_widget = TkinterMapView(self, corner_radius=0)
                self.map_widget.place(x=247.0, y=200.0, width=847.0, height=290.0)
                self.map_widget.set_zoom(5)
                self.map_widget.set_position(31.0, 34.8)  # default center
                self._map_mode = "tkmap"

                # Tile source selector (OSM/Google)
                try:
                    self.tile_source_var = tk.StringVar(value="Google Road")
                    self.tile_source_menu = Ctk.CTkOptionMenu(self, width=130, height=18, fg_color="#D5E3F0", text_color="#565454", variable=self.tile_source_var, values=["Google Road", "Google Satellite", "Google Hybrid", "Google Terrain", "OSM"], command=lambda s: self._set_map_tile_source(s))
                    self.tile_source_menu.place(x=963, y=180)
                except Exception:
                    pass
                # Default to Google Road tiles if allowed
                self._set_map_tile_source("Google Road")
                # Enable fit button for tkmap once bbox valid
                self.fp_fit_btn.configure(state="disabled")
                self.fp_fit_btn.configure(command=self._fit_map_to_bbox)
            except Exception as e:
                # Map failed to initialize for another reason; surface error in UI
                self._map_mode = "missing"
                try:
                    import logging as _logging
                    _logging.getLogger(__name__).error(f"Failed to initialize map widget: {e}")
                    self.map_hint = Ctk.CTkLabel(self, text=f"Map error: {e}", bg_color="#F8F9FB", text_color="#565454")
                    self.map_hint.place(x=250, y=470)
                    self.fp_fit_btn.configure(state="disabled")
                except Exception:
                    pass

        # Microsoft panel (left) with image banner
        try:
            self.image_ms = PhotoImage(file=str(self.controller.ASSETS_PATH / "image_Microsoft_Footprint.png"))
            self.canvas.create_image(667.0, 631.0, image=self.image_ms)

        except Exception:
            pass
        # Microsoft controls aligned horizontally under map (left side)
        self.ms_location_entry = Ctk.CTkEntry(self, width=200, height=18, border_color="#D5E3F0", placeholder_text="Country/Location")
        self.ms_location_entry.place(x=380, y=617)
        self.ms_divide_switch = Ctk.CTkSwitch(self, text="Divide after download", onvalue=1, offvalue=0, text_color="#565454", bg_color="#FDFBFC")
        self.ms_divide_switch.place(x=605, y=616)
        self.ms_download_btn = Ctk.CTkButton(self, text="Download", fg_color="#8DBBE7", width=90, height=20, command=self._ms_download)
        self.ms_download_btn.place(x=790, y=617)

        # Google panel with image banner
        try:
            self.image_geo = PhotoImage(file=str(self.controller.ASSETS_PATH / "image_Google_Footprint.png"))
            self.canvas.create_image(667.0, 581.0, image=self.image_geo)
        except Exception:
            pass
        # Google controls aligned horizontally under map (right side)
        self.gg_select_btn = Ctk.CTkButton(self, text="Browse...", fg_color="#8DBBE7", width=80, height=20, command=self._gg_browse)
        self.gg_select_btn.place(x=465, y=568)
        self.gg_source_label = Ctk.CTkLabel(self, text="No source selected", text_color="#565454", bg_color="#FDFBFC")
        self.gg_source_label.place(x=555, y=565)
        self.gg_tile_entry = Ctk.CTkEntry(self, width=130, height=19, border_color="#D5E3F0", placeholder_text="Tile ID")
        self.gg_tile_entry.place(x=970, y=567)
        self.gg_divide_btn = Ctk.CTkButton(self, text="Divide", fg_color="#8DBBE7", width=70, height=20, command=self._gg_divide)
        self.gg_divide_btn.place(x=390, y=568)

        # Save options
        try:
            self.image_save = PhotoImage(file=str(self.controller.ASSETS_PATH / "image_Saving_Footprint.png"))
            self.canvas.create_image(667.0, 682.0, image=self.image_save)
        except Exception:
            pass
        # self.canvas.create_text(250.0, 525.0, anchor="nw", text="Saving", fill="#000000", font=("Inter", 14 * -1))
        # Save folder (Google row) aligned horizontally
        self.fp_save_browse = Ctk.CTkButton(self, text="Saving Path", fg_color="#8DBBE7", width=100, height=20, command=self._fp_browse_save)
        self.fp_save_browse.place(x=705, y=667)
        # Internal holder for selected saving path (no visible label to save space)
        self.fp_save_path = ""

        # Saving row aligned
        self.canvas.create_text(375.0, 670.0, anchor="nw", text="File Name", fill="#000000", font=("Inter", 12 * -1))
        self.fp_filename_entry = Ctk.CTkEntry(self, width=150, height=18, border_color="#D5E3F0", placeholder_text="buildings.geojson")
        self.fp_filename_entry.place(x=445, y=667.0)
        self.fp_extrafields = Ctk.CTkCheckBox(self, text="extra fields", text_color="#565454", bg_color="#FDFBFC")
        self.fp_extrafields.place(x=605, y=667.0)

        # Extraction source selector and action button
        try:
            self.extract_source = Ctk.CTkSegmentedButton(
                self,
                values=["Microsoft", "Google", "Atlas"],
                fg_color="#D5E3F0",
                unselected_color="#D5E3F0",
                selected_color="#8DBBE7",
                height=20,
                width=170,
                text_color="#565454",
                dynamic_resizing=False,
            )
            self.extract_source.place(x=821, y=667)
            self.extract_source.set("Google")
        except Exception:
            self.extract_source = None

        self.extract_run_btn = Ctk.CTkButton(self, text="Extraction", fg_color="#D5E3F0",bg_color="#f0f0f0",text_color="#000000",
                                              width=100, height=29, corner_radius=20, command=self._run_extraction)
        self.extract_run_btn.place(x=1000, y=664)

        # Placeholders for later wiring of events and algorithms
        self.gg_selected_source = None
        self.gg_use_chunks = False
        self.ms_last_output_dir = None
        self.gg_last_output_dir = None

        # Finally ensure Benchmark Sims logo is on top
        try:
            # Lift in correct z-order: logo above name above welcome
            if hasattr(self, 'fp_welcome_item') and self.fp_welcome_item:
                self.canvas.lift(self.fp_welcome_item)
            if hasattr(self, 'fp_name_item') and self.fp_name_item:
                self.canvas.lift(self.fp_name_item)
            if hasattr(self, 'fp_logo_item') and self.fp_logo_item:
                self.canvas.lift(self.fp_logo_item)
        except Exception:
            pass

    # ===== Save helpers =====
    def _default_save_dir(self, provider):
        root = self.controller._get_footprints_root()
        if provider == "microsoft":
            loc = (self.ms_location_entry.get() or "").strip()
            if not loc:
                loc = "default"
            out = os.path.join(root, "microsoft", loc)
        elif provider == "globalatlas":
            out = os.path.join(root, "globalatlas")
        else:
            out = os.path.join(root, "google")
        try:
            os.makedirs(out, exist_ok=True)
        except Exception:
            pass
        return out

    def _ensure_output_path(self, provider):
        path = (getattr(self, 'fp_save_path', '') or "").strip()
        if not path:
            path = self._default_save_dir(provider)
            try:
                self.fp_save_path = path
            except Exception:
                pass
        try:
            os.makedirs(path, exist_ok=True)
        except Exception:
            pass
        return path

    def _compose_output_file(self, provider):
        folder = self._ensure_output_path(provider)
        name = (self.fp_filename_entry.get() or "buildings.geojson").strip()
        if not name.lower().endswith(".geojson"):
            name += ".geojson"
        return os.path.join(folder, name)

    def _confirm_file_overwrite(self, output_file):
        """
        Check if output file already exists and prompt user to confirm overwrite.
        
        Returns:
            True if file doesn't exist OR user confirms overwrite
            False if user cancels the operation
        """
        if os.path.exists(output_file):
            return messagebox.askyesno(
                "File Already Exists",
                f"The file already exists:\n{output_file}\n\nDo you want to overwrite it?"
            )
        return True

    def _fp_browse_save(self):
        try:
            folder = tkinter.filedialog.askdirectory()
            if folder:
                self.fp_save_path = folder
        except Exception as e:
            logging.getLogger(__name__).warning(f"Browse save failed: {e}")

    # ===== Microsoft actions =====
    def _ms_download(self):
        try:
            from processing_window import run_with_processing
        except Exception as e:
            return messagebox.showerror("Error", f"Processing window not available: {e}")
        location = (self.ms_location_entry.get() or "").strip()
        if not location:
            return messagebox.showwarning("Missing Input", "Please enter a Microsoft location (country)")
        divide_flag = bool(self.ms_divide_switch.get())
        if not divide_flag:
            if not messagebox.askyesno("Not Dividing?", "You chose not to divide the dataset. Extraction may be significantly slower. Continue?"):
                return
        output_dir = os.path.join(self.controller._get_footprints_root(), "microsoft", location)
        try:
            os.makedirs(output_dir, exist_ok=True)
        except Exception:
            pass

        err_holder = {"msg": None}

        def task(win):
            try:
                import threading
                cancel_event = threading.Event()
                # stash on self to allow external cancel (ProcessingWindow should wire a cancel button)
                self._ms_cancel_event = cancel_event
                import building_extractor as be
                outdir = be.download_ms_dataset(self.controller._get_root_dir(), location, divide_flag, cancel_event=cancel_event)
                return True
            except Exception as e:
                err_text = str(e)
                err_holder["msg"] = err_text
                logging.getLogger(__name__).error(f"MS download error: {err_text}")
                # Re-raise to allow processing window to stop immediately
                raise

        try:
            res = run_with_processing(parent=self.controller, task_function=task, title="Microsoft Download", message=f"Downloading {location}...")
        except Exception as e:
            # Surface common public access error or detailed message
            msg = str(e)
            if "Public access is not permitted" in msg or "HTTP Error 409" in msg:
                messagebox.showerror("Download Error", "Microsoft dataset links are not accessible (HTTP 409). Please try again later or check network/policy.")
            else:
                messagebox.showerror("Download Error", msg)
            return

        # If operation did not succeed and no exception was propagated, still inform the user
        if not res:
            msg = err_holder.get("msg") or "Download was cancelled or failed. Please check the location spelling or logs for details."
            if "Public access is not permitted" in msg or "HTTP Error 409" in msg:
                messagebox.showerror("Download Error", "Microsoft dataset links are not accessible (HTTP 409). Please try again later or check network/policy.")
            else:
                messagebox.showerror("Download Error", msg)
            return
        if res:
            self.ms_last_output_dir = output_dir
            messagebox.showinfo("Success", f"Downloaded data for {location} into:\n{output_dir}")

    def _ms_extract(self):
        if not (self.fp_top_left and self.fp_bottom_right):
            return messagebox.showwarning("Invalid BBox", "Please enter valid coordinates and update BBox.")
        location = (self.ms_location_entry.get() or "").strip()
        if not location:
            return messagebox.showwarning("Missing Input", "Please enter a Microsoft location (country)")
        # Resolve best source under footprints/microsoft/<location>
        kind, path = self._resolve_ms_input(location)
        if not kind:
            logging.getLogger(__name__).error(f"Microsoft dataset not found: {location}")
            return messagebox.showerror("Not Found", f"No dataset found for '{location}' under footprints/microsoft.")
        output_file = self._compose_output_file("microsoft")
        
        # Check if file exists and confirm overwrite
        if not self._confirm_file_overwrite(output_file):
            return
        
        extrafields = bool(self.fp_extrafields.get())
        tl = [float(self.fp_top_left[0]), float(self.fp_top_left[1])]
        br = [float(self.fp_bottom_right[0]), float(self.fp_bottom_right[1])]
        try:
            from processing_window import run_with_processing
        except Exception as e:
            return messagebox.showerror("Error", f"Processing window not available: {e}")

        def task(win):
            try:
                from building_extractor import extract_ms_divided, extract_ms_combined
                if kind == "divided":
                    return extract_ms_divided(path, output_file, tl, br, extrafields)
                else:
                    return extract_ms_combined(path, output_file, tl, br, extrafields)
            except Exception as e:
                logging.getLogger(__name__).error(f"MS extract error: {e}")
                raise

        res = run_with_processing(parent=self.controller, task_function=task, title="Microsoft Extract", message="Extracting AOI from dataset...")
        if res:
            count = res.get("count") if isinstance(res, dict) else None
            logging.getLogger(__name__).info(f"Microsoft extraction completed. Output: {output_file}, Buildings: {count}")
            if count is not None:
                messagebox.showinfo("Extraction Completed", f"Saved AOI to:\n{output_file}\nBuildings extracted: {count}")
            else:
                messagebox.showinfo("Extraction Completed", f"Saved AOI to:\n{output_file}")

    # ===== Google actions =====
    def _gg_browse(self):
        try:
            # Single dialog: pick a CSV file; cancel means do nothing
            path = tkinter.filedialog.askopenfilename(filetypes=[("CSV files", "*.csv")])
            if not path:
                # Cancelled
                return
            self._set_google_source(path)
        except Exception as e:
            logging.getLogger(__name__).warning(f"Browse error: {e}")

    def _set_google_source(self, path):
        self.gg_selected_source = path
        self.gg_use_chunks = os.path.isdir(path)
        try:
            self.gg_source_label.configure(text=path)
        except Exception:
            pass
        # Try to infer tile id into field if CSV
        if not self.gg_use_chunks and path:
            base = os.path.basename(path)
            # Expect format like TILEID_buildings.csv
            if "_buildings" in base:
                tid = base.split("_buildings")[0]
                self.gg_tile_entry.delete(0, tk.END)
                self.gg_tile_entry.insert(0, tid)

    def _gg_divide(self):
        tile_id = (self.gg_tile_entry.get() or "").strip()
        if not tile_id:
            return messagebox.showwarning("Missing Input", "Please select or enter a tile ID to divide")
        # Determine destination directory under root/footprints/google/<tile_id>
        fp_google_root = os.path.join(self.controller._get_footprints_root(), "google")
        dest_dir = os.path.join(fp_google_root, tile_id)
        try:
            os.makedirs(dest_dir, exist_ok=True)
        except Exception:
            pass
        # If a CSV was browsed, copy it into destination as <tile_id>_buildings.csv
        if getattr(self, 'gg_selected_source', None) and os.path.isfile(self.gg_selected_source):
            try:
                import shutil
                src_csv = self.gg_selected_source
                dst_csv = os.path.join(dest_dir, f"{tile_id}_buildings.csv")
                shutil.copy2(src_csv, dst_csv)
                # Ensure tiles.geojson is available at root/footprints/google/tiles.geojson
                src_tiles = os.path.join(os.path.dirname(src_csv), "tiles.geojson")
                root_tiles = os.path.join(fp_google_root, "tiles.geojson")
                if os.path.isfile(src_tiles) and not os.path.isfile(root_tiles):
                    try:
                        shutil.copy2(src_tiles, root_tiles)
                    except Exception as e:
                        logging.getLogger(__name__).warning(f"Failed to copy tiles.geojson to google root: {e}")
            except Exception as e:
                logging.getLogger(__name__).warning(f"Failed to stage CSV/tiles for divide: {e}")
        # Use destination directory for division
        csv_dir = dest_dir

        try:
            from processing_window import run_with_processing
        except Exception as e:
            return messagebox.showerror("Error", f"Processing window not available: {e}")

        def task(win):
            try:
                import threading
                self._gg_cancel_event = threading.Event()
                from building_extractor import divide_google_tile
                # Verify tiles.geojson is present either at root/footprints/google or next to CSV
                google_root = fp_google_root
                root_tiles = os.path.join(google_root, "tiles.geojson")
                local_tiles = os.path.join(csv_dir, "tiles.geojson")
                if not (os.path.isfile(root_tiles) or os.path.isfile(local_tiles)):
                    logging.getLogger(__name__).error("tiles.geojson not found in expected locations")
                    messagebox.showerror("Missing tiles.geojson", "tiles.geojson was not found in root/footprints/google/ or next to the CSV. Operation cancelled.")
                    return False
                divide_google_tile(csv_dir, tile_id, google_root=google_root)
                return True
            except Exception:
                raise

        res = run_with_processing(parent=self.controller, task_function=task, title="Google Divide", message=f"Dividing tile {tile_id} into chunks...")
        if res:
            outdir = os.path.join(csv_dir, f"{tile_id}_chunks")
            self.gg_last_output_dir = outdir
            messagebox.showinfo("Success", f"Chunks written to:\n{outdir}")

    def _gg_extract(self):
        if not (self.fp_top_left and self.fp_bottom_right):
            return messagebox.showwarning("Invalid BBox", "Please enter valid coordinates and update BBox.")
        # Determine source: prefer user-browsed CSV; else dataset name entry under footprints/google/<name>
        use_chunks, input_path = self._resolve_google_source()
        if not input_path:
            logging.getLogger(__name__).error("Google dataset not found")
            return messagebox.showerror("Not Found", "No Google dataset found. Browse a CSV or enter a dataset/tile name present in footprints/google.")
        output_file = self._compose_output_file("google")
        
        # Check if file exists and confirm overwrite
        if not self._confirm_file_overwrite(output_file):
            return
        
        extrafields = bool(self.fp_extrafields.get())
        tl = (float(self.fp_top_left[0]), float(self.fp_top_left[1]))
        br = (float(self.fp_bottom_right[0]), float(self.fp_bottom_right[1]))
        try:
            from processing_window import run_with_processing
        except Exception as e:
            return messagebox.showerror("Error", f"Processing window not available: {e}")

        def task(win):
            try:
                from building_extractor import extract_google
                return extract_google(use_chunks, input_path, output_file, tl, br, extrafields)
            except Exception as e:
                logging.getLogger(__name__).error(f"Google extract error: {e}")
                raise

        res = run_with_processing(parent=self.controller, task_function=task, title="Google Extract", message="Filtering polygons in AOI...")
        if res:
            count = res.get("count") if isinstance(res, dict) else None
            logging.getLogger(__name__).info(f"Google extraction completed. Output: {output_file}, Buildings: {count}")
            if count is not None:
                messagebox.showinfo("Extraction Completed", f"Saved AOI to:\n{output_file}\nBuildings extracted: {count}")
            else:
                messagebox.showinfo("Extraction Completed", f"Saved AOI to:\n{output_file}")

    def _ga_extract(self):
        """Extract buildings from GlobalBuildingAtlas WFS service."""
        logger = logging.getLogger(__name__)
        
        # Validate coordinates
        if not (self.fp_top_left and self.fp_bottom_right):
            logger.warning("GlobalAtlas extraction attempted without valid BBox")
            return messagebox.showwarning("Invalid BBox", "Please enter valid coordinates and update BBox.")
        
        # Prepare extraction parameters
        output_file = self._compose_output_file("globalatlas")
        
        # Check if file exists and confirm overwrite
        if not self._confirm_file_overwrite(output_file):
            return
        
        extrafields = bool(self.fp_extrafields.get())
        tl = (float(self.fp_top_left[0]), float(self.fp_top_left[1]))
        br = (float(self.fp_bottom_right[0]), float(self.fp_bottom_right[1]))
        
        logger.info(f"Starting GlobalAtlas extraction:")
        logger.info(f"  Top-left: {tl}")
        logger.info(f"  Bottom-right: {br}")
        logger.info(f"  Output file: {output_file}")
        logger.info(f"  Extra OSM fields: {extrafields}")
        logger.debug(f"  WFS Service: https://tubvsig-so2sat-vm1.srv.mwn.de/geoserver/ows?")
        logger.debug(f"  Layer: global3D:lod1_global")
        
        # Import processing window
        try:
            from processing_window import run_with_processing
        except Exception as e:
            logger.error(f"Processing window not available: {e}")
            return messagebox.showerror("Error", f"Processing window not available: {e}")
        
        # Define extraction task
        def task(win):
            try:
                logger.debug("Importing global_atlas_extractor module from components")
                from components.global_atlas_extractor import extract_globalatlas_buildings
                
                logger.info("Calling extract_globalatlas_buildings...")
                result = extract_globalatlas_buildings(tl, br, output_file, extrafields)
                
                logger.debug(f"Extraction result: {result}")
                return result
                
            except ImportError as e:
                logger.error(f"Failed to import global_atlas_extractor: {e}", exc_info=True)
                raise Exception(f"GlobalAtlas integration module not found: {e}")
            except Exception as e:
                logger.error(f"GlobalAtlas extract error: {e}", exc_info=True)
                raise
        
        # Run extraction with progress window
        try:
            logger.info("Launching processing window...")
            res = run_with_processing(
                parent=self.controller, 
                task_function=task, 
                title="GlobalAtlas Extract", 
                message="Fetching buildings from GlobalAtlas...\n\nPlease wait (30-120 seconds)"
            )
            
            logger.debug(f"Processing window returned: {res}")
            
            # Handle results - check if res is a valid dict
            if res is None or res is False:
                logger.warning(f"Extraction failed or returned invalid result: {res}")
                messagebox.showwarning(
                    "Extraction Failed", 
                    "Extraction failed to complete.\n\n"
                    "The GlobalBuildingAtlas service may be experiencing\n"
                    "high traffic or connection issues.\n\n"
                    "Please try:\n"
                    "  • Smaller bounding box\n"
                    "  • Retry in a few minutes\n"
                    "  • Use Microsoft/Google sources"
                )
                return
            
            # Ensure res is a dictionary before calling .get()
            if not isinstance(res, dict):
                logger.error(f"Unexpected result type: {type(res)} - expected dict")
                messagebox.showerror(
                    "Extraction Error",
                    "Extraction returned unexpected result format.\n"
                    "Check logs for details."
                )
                return
            
            if res.get('cancelled', False):
                logger.info("Extraction was cancelled by user")
                messagebox.showinfo("Cancelled", "Extraction was cancelled.")
                return
            
            # Success case
            count = res.get("count", 0)
            total_available = res.get("total_available")
            
            logger.info(f"GlobalAtlas extraction completed successfully:")
            logger.info(f"  Output file: {output_file}")
            logger.info(f"  Buildings extracted: {count}")
            if total_available:
                logger.info(f"  Total available in area: {total_available}")
            
            # Build success message
            msg = f"Saved AOI to:\n{output_file}\n\nBuildings extracted: {count}"
            
            if count == 0:
                msg += "\n\n⚠️ No buildings found in the specified area."
                msg += "\nTry expanding your bounding box or checking coordinates."
                messagebox.showwarning("No Buildings Found", msg)
            else:
                if total_available and total_available > count:
                    msg += f"\nTotal available in area: {total_available}"
                    if total_available > count:
                        msg += f"\n\n(Showing {count} of {total_available} buildings)"

                messagebox.showinfo("Extraction Completed", msg)
                
        except Exception as e:
            # Handle requests-specific exceptions if requests is available
            if requests and isinstance(e, requests.exceptions.Timeout):
                logger.error(f"WFS request timed out: {e}")
                messagebox.showerror(
                    "Service Timeout", 
                    "GlobalBuildingAtlas WFS service request timed out.\n\n"
                    "The service may be experiencing high traffic.\n"
                    "Please try:\n"
                    "  • Smaller bounding box\n"
                    "  • Retry in a few minutes\n"
                    "  • Use Microsoft/Google sources instead"
                )
            elif requests and isinstance(e, requests.exceptions.RequestException):
                logger.error(f"WFS request failed: {e}", exc_info=True)
                error_msg = str(e)
                if "high traffic" in error_msg.lower() or "incompleteread" in error_msg.lower():
                    messagebox.showerror(
                        "Service Unavailable", 
                        "GlobalBuildingAtlas WFS service connection was interrupted.\n\n"
                        "The service may be experiencing high traffic or instability.\n\n"
                        "Please try:\n"
                        "  • Retry in a few minutes\n"
                        "  • Smaller bounding box\n"
                        "  • Use Microsoft/Google sources instead"
                    )
                else:
                    messagebox.showerror(
                        "Connection Error", 
                        f"Failed to connect to GlobalBuildingAtlas WFS:\n\n{error_msg}\n\n"
                        "Check your internet connection and try again."
                    )
            else:
                # Generic error handling for non-requests exceptions
                logger.error(f"Unexpected error during GlobalAtlas extraction: {e}", exc_info=True)
                error_msg = str(e)
                messagebox.showerror(
                    "Extraction Error", 
                    f"Failed to extract from GlobalAtlas:\n\n{error_msg}\n\n"
                    "Check logs for more details."
                )

    def _resolve_ms_input(self, location):
        from building_extractor import resolve_ms_input
        return resolve_ms_input(self.controller._get_root_dir(), location)

    def _resolve_google_source(self):
        from building_extractor import resolve_google_source
        # Priority: entry tile ID under root/footprints/google/<id> → browsed file
        tile_id = (self.gg_tile_entry.get() if hasattr(self, 'gg_tile_entry') else None)
        # If tile_id present, attempt to resolve under roots first
        use_chunks, input_path = resolve_google_source(self.controller._get_root_dir(), None, tile_id)
        if use_chunks is not None and input_path:
            return use_chunks, input_path
        # Fallback to browsed source
        return resolve_google_source(self.controller._get_root_dir(), self.gg_selected_source, None)
    
    def _fit_map_to_bbox(self):
        if not (self.fp_top_left and self.fp_bottom_right):
            return
        top_lat, left_lon = self.fp_top_left
        bottom_lat, right_lon = self.fp_bottom_right
        # Normalize order
        min_lon = min(left_lon, right_lon)
        max_lon = max(left_lon, right_lon)
        min_lat = min(bottom_lat, top_lat)
        max_lat = max(bottom_lat, top_lat)
        center_lat = (min_lat + max_lat) / 2.0
        center_lon = (min_lon + max_lon) / 2.0
        if self._map_mode == "tkmap":
            try:
                self.map_widget.set_position(center_lat, center_lon)
                zoom = self._estimate_zoom(max_lat - min_lat, max_lon - min_lon)
                self.map_widget.set_zoom(zoom)
            except Exception:
                pass
        else:
            return

    def _estimate_zoom(self, dlat, dlon):
        try:
            span = max(abs(dlat), abs(dlon))
            if span <= 0.05:
                return 15
            if span <= 0.1:
                return 14
            if span <= 0.25:
                return 13
            if span <= 0.5:
                return 12
            if span <= 1.0:
                return 11
            if span <= 2.0:
                return 10
            if span <= 4.0:
                return 9
            if span <= 8.0:
                return 8
            if span <= 16.0:
                return 7
            if span <= 32.0:
                return 6
            if span <= 64.0:
                return 5
            return 4
        except Exception:
            return 8

    def _set_map_tile_source(self, selection):
        """Set tile server for tkintermapview to Google or OSM."""
        if self._map_mode != "tkmap":
            return
        try:
            # Google tile variants
            if selection == "Google Road":
                url = "https://mt1.google.com/vt/lyrs=r&x={x}&y={y}&z={z}"
            elif selection == "Google Satellite":
                url = "https://mt1.google.com/vt/lyrs=s&x={x}&y={y}&z={z}"
            elif selection == "Google Hybrid":
                url = "https://mt1.google.com/vt/lyrs=y&x={x}&y={y}&z={z}"
            elif selection == "Google Terrain":
                url = "https://mt1.google.com/vt/lyrs=p&x={x}&y={y}&z={z}"
            else:
                url = None

            if url:
                # Use Google tile server (subject to provider terms)
                self.map_widget.set_tile_server(url, tile_size=256, max_zoom=22)
            else:
                # Default OSM
                self.map_widget.set_tile_server("https://a.tile.openstreetmap.org/{z}/{x}/{y}.png", tile_size=256, max_zoom=19)
        except Exception as _e:
            logging.getLogger(__name__).warning(f"Tile server set failed: {_e}")

    def _install_map_support(self):
        """Attempt to install tkintermapview at runtime (Windows) and prompt restart."""
        try:
            import subprocess, sys
            cmd = [sys.executable, "-m", "pip", "install", "--upgrade", "tkintermapview"]
            subprocess.check_call(cmd)
            messagebox.showinfo("Installation", "tkintermapview installed. Please restart the application to enable the interactive map.")
        except Exception as e:
            messagebox.showerror("Installation Error", f"Failed to install tkintermapview.\nYou can install manually:\npython -m pip install tkintermapview\nError: {e}")

    def _run_extraction(self):
        """Run extraction based on selector (Microsoft/Google/GlobalAtlas) using saving options."""
        try:
            source = self.extract_source.get() if self.extract_source else "Google"
        except Exception:
            source = "Google"
        if source == "Microsoft":
            return self._ms_extract()
        elif source == "Atlas":
            return self._ga_extract()
        else:
            return self._gg_extract()

    
    def _on_update_bbox(self):
        """Parse coordinate fields, validate, and update status. Map overlay added later."""
        try:
            top_left_text = self.fp_top_left_entry.get().strip()
            bottom_right_text = self.fp_bottom_right_entry.get().strip()

            # If a WKT polygon is pasted in either field, parse bounds and populate both
            if self._looks_like_wkt_polygon(top_left_text) or self._looks_like_wkt_polygon(bottom_right_text):
                bbox = self._parse_wkt_bounds(top_left_text if self._looks_like_wkt_polygon(top_left_text) else bottom_right_text)
                if bbox:
                    minx, miny, maxx, maxy = bbox
                    # Top-left (lat,lon) => (maxy, minx); Bottom-right (lat,lon) => (miny, maxx)
                    self.fp_top_left_entry.delete(0, tk.END)
                    self.fp_top_left_entry.insert(0, f"{maxy:.6f},{minx:.6f}")
                    self.fp_bottom_right_entry.delete(0, tk.END)
                    self.fp_bottom_right_entry.insert(0, f"{miny:.6f},{maxx:.6f}")
                    top_left_text = self.fp_top_left_entry.get().strip()
                    bottom_right_text = self.fp_bottom_right_entry.get().strip()

            top_left = self._parse_coord_string(top_left_text)
            bottom_right = self._parse_coord_string(bottom_right_text)

            if top_left is None or bottom_right is None:
                self._set_status("Invalid coordinates", ok=False)
                self.fp_top_left = None
                self.fp_bottom_right = None
                return

            if not self._valid_latlon(*top_left) or not self._valid_latlon(*bottom_right):
                self._set_status("Coordinates out of range", ok=False)
                self.fp_top_left = None
                self.fp_bottom_right = None
                return

            self.fp_top_left = top_left
            self.fp_bottom_right = bottom_right
            self._set_status("BBox valid", ok=True)
            # Draw/refresh bbox overlay
            self._draw_bbox_overlay()
            # Enable fit button
            try:
                self.fp_fit_btn.configure(state="normal")
            except Exception:
                pass
            logging.getLogger(__name__).info(f"Updated AOI bbox: TL={self.fp_top_left}, BR={self.fp_bottom_right}")
            # Auto-fit to bbox for immediate feedback
            self._fit_map_to_bbox()
        except Exception as e:
            logging.getLogger(__name__).warning(f"BBox update failed: {e}")
            self._set_status("Error parsing coords", ok=False)

    def _set_status(self, text, ok=True):
        try:
            self.fp_status_label.configure(text=text)
            self.fp_status_label.configure(text_color="#0a7f00" if ok else "#a40000")
        except Exception:
            pass

    def _parse_coord_string(self, value):
        """Return (lat, lon) or None. Supports 'lat,lon', 'lat lon', and 'Point(lon lat)'."""
        if not value:
            return None
        s = value.strip()
        # Try comma-separated
        for sep in [",", " "]:
            try:
                if sep in s:
                    parts = [p.strip().strip("()") for p in s.split(sep) if p.strip()]
                    if len(parts) == 2:
                        lat = float(parts[0])
                        lon = float(parts[1])
                        # If looks like lon,lat (first outside lat range and second valid lat), swap
                        if (abs(lat) > 90 and abs(lon) <= 90) or (abs(lat) <= 90 and abs(lon) > 180):
                            lon, lat = lat, lon
                        return (lat, lon)
            except Exception:
                pass
        # Try POINT WKT like 'Point (lon lat)'
        try:
            import re
            m = re.search(r"point\s*\(\s*([-+]?\d*\.?\d+)\s+([-+]?\d*\.?\d+)\s*\)", s, re.IGNORECASE)
            if m:
                lon = float(m.group(1))
                lat = float(m.group(2))
                return (lat, lon)
        except Exception:
            pass
        return None

    def _looks_like_wkt_polygon(self, value):
        if not value:
            return False
        v = value.strip().upper()
        return v.startswith("POLYGON(") or v.startswith("MULTIPOLYGON(")

    def _parse_wkt_bounds(self, wkt_text):
        """Return (minx, miny, maxx, maxy) from WKT polygon if shapely is available."""
        try:
            from shapely import wkt as _wkt
            geom = _wkt.loads(wkt_text)
            return geom.bounds
        except Exception:
            return None

    def _valid_latlon(self, lat, lon):
        try:
            return -90.0 <= float(lat) <= 90.0 and -180.0 <= float(lon) <= 180.0
        except Exception:
            return False

    def _draw_bbox_overlay(self):
        if not (self.fp_top_left and self.fp_bottom_right):
            return
        top_lat, left_lon = self.fp_top_left
        bottom_lat, right_lon = self.fp_bottom_right
        min_lon = min(left_lon, right_lon)
        max_lon = max(left_lon, right_lon)
        min_lat = min(bottom_lat, top_lat)
        max_lat = max(bottom_lat, top_lat)

        if self._map_mode == "tkmap":
            try:
                # Remove previous polygon if exists
                if self._bbox_polygon is not None:
                    try:
                        self._bbox_polygon.delete()
                    except Exception:
                        pass
                    self._bbox_polygon = None
                # TkinterMapView expects list of (lat, lon)
                coords = [
                    (max_lat, min_lon),
                    (max_lat, max_lon),
                    (min_lat, max_lon),
                    (min_lat, min_lon),
                ]
                self._bbox_polygon = self.map_widget.set_polygon(coords, outline_color="#C40000", fill_color="#C40000", border_width=2, name="AOI")
            except Exception:
                pass

if __name__ == "__main__":
    app = MainPage()
    app.mainloop()
