import tkinter as tk
from pathlib import Path

class SharedData:
    """Centralized storage for shared application data."""
    
    def __init__(self):
        # File paths and locations
        self.CTpath = tk.StringVar()
        self.BMS_Database_Path = tk.StringVar()
        self.Geopath = tk.StringVar()
        self.backup_CTpath = tk.StringVar()
        self.EditorSavingPath = tk.StringVar()
        self.projection_path = tk.StringVar()
        
        # Application state
        self.BMS_version = tk.StringVar()
        self.Theater = tk.StringVar()
        self.Database_Availability = tk.StringVar()
        self.projection_string = tk.StringVar()
        self.Startup = tk.StringVar()
        self.debugger = tk.BooleanVar()
        # Future: configurable visualization limits
        self.max_geojson_draw = tk.IntVar(value=256)
        
        # Data storage
        self.BMS_Databse = None
        self.Geodata = None
        self.Calc_Geodata = None
        self.Geo_AOI_Center = None
        
        # Initialize default values
        self.set_defaults()
    
    def set_defaults(self):
        """Set default values for shared data."""
        self.BMS_version.set("-")
        self.Theater.set("-")
        self.CTpath.set("No CT file selected")
        self.projection_path.set("No Projection file selected")
        self.backup_CTpath.set("No CT file selected")
        self.Geopath.set("No GeoJson file selected")
        self.debugger.set(False)

"""Configuration settings for the Building Generator application."""

# Color scheme
COLORS = {
    "MAIN_BG": "#E7F3F7",
    "CANVAS_BG": "#FFFFFF",
    "SIDEBAR_BG": "#8DBBE7",
    "BUTTON_BG": "#8DBBE7",
    "BUTTON_HOVER": "#6B9FD3",
    "SETTINGS_BG": "#FF6B6B",
    "FRAME_BG": "#FFFFFF",
    "PANEL_BG": "#F5F5F5",
    "PLOT_BG": "#FFFFFF",
    "TEXT_COLOR": "#000000"
}

# Font configurations
FONTS = {
    "DASH": ("Arial", 14),
    "BUTTON": ("Arial", 10),
    "BODY": ("Arial", 12),
    "BODY_BOLD": ("Arial", 12, "bold")
}

# Window dimensions
WINDOW_SIZE = {
    "WIDTH": 1200,
    "HEIGHT": 800,
    "SIDEBAR_WIDTH": 200,
    "MAIN_FRAME_WIDTH": 980,
    "MAIN_FRAME_HEIGHT": 760,
    "NAV_WIDTH": 180
}

# Button dimensions
BUTTON_SIZES = {
    "NAV_HEIGHT": 40,
    "NAV_WIDTH": 180,
    "SETTINGS_HEIGHT": 60,
    "SETTINGS_WIDTH": 180
}

# Navigation button positions
NAV_POSITIONS = {
    "OPERATIONS": (10, 100),
    "DATABASE": (10, 160),
    "DASHBOARD": (10, 220),
    "SETTINGS": (10, 700),
    "GEO": (10, 280)
} 