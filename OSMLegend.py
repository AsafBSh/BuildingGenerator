import tkinter as tk
from tkinter import ttk, Entry, Frame, Label, StringVar
import customtkinter as Ctk
from PIL import Image, ImageTk
import os

class OSMLegend(tk.Toplevel):
    def __init__(window):
        tk.Toplevel.__init__(window)
        window.title("OpenStreetMap Legend")
        window.geometry("700x520")
        window.resizable(True, True)
        window.configure(bg="#f0f0f0")
        
        # Define colors for different categories
        window.category_colors = {
            "aeroway": "#ADD8E6",      # Light blue
            "barrier": "#D3D3D3",      # Light gray
            "building": "#FFB6C1",     # Light pink
            "man_made": "#90EE90",     # Light green
            "leisure": "#FFFFE0",      # Light yellow
            "military": "#FFA07A",     # Light salmon
            "power": "#E6E6FA",        # Lavender
            "sport": "#98FB98",        # Pale green
            "tower": "#87CEFA",        # Light sky blue
            "religion": "#DDA0DD",     # Plum
            "bms": "#B0C4DE"           # Light steel blue
        }
        
        # Create main frame
        main_frame = Frame(window, bg="#f0f0f0")
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Create header with title and search
        header_frame = Frame(main_frame, bg="#f0f0f0")
        header_frame.pack(fill="x", pady=5)
        
        # Title
        title_label = Label(
            header_frame,
            text="OpenStreetMap Tags Legend",
            font=("Arial", 14, "bold"),
            bg="#f0f0f0"
        )
        title_label.pack(side="left", padx=5)
        
        # Search functionality
        search_frame = Frame(header_frame, bg="#f0f0f0")
        search_frame.pack(side="right", padx=5)
        
        Label(search_frame, text="Search:", bg="#f0f0f0").pack(side="left")
        search_var = StringVar()
        search_entry = Ctk.CTkEntry(search_frame, textvariable=search_var, width=140, height=15)
        search_entry.pack(side="left", padx=5)
        search_entry.bind("<KeyRelease>", lambda e: window.search_tree(search_var.get()))
        
        # Create notebook (tabbed interface)
        notebook = ttk.Notebook(main_frame)
        notebook.pack(fill="both", expand=True, pady=5)
        
        # Create All Categories tab
        all_tab = Frame(notebook, bg="#f5f5f5")
        notebook.add(all_tab, text="All Categories")
        
        # Create category tabs dictionary
        category_tabs = {}
        
        # Create a frame for the treeview with a scrollbar
        tree_frame = Frame(all_tab)
        tree_frame.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Add scrollbars
        y_scrollbar = ttk.Scrollbar(tree_frame, orient="vertical")
        y_scrollbar.pack(side="right", fill="y")
        
        x_scrollbar = ttk.Scrollbar(tree_frame, orient="horizontal")
        x_scrollbar.pack(side="bottom", fill="x")
        
        # Create and configure the Treeview widget with UNIQUE style names for OSM Legend
        style = ttk.Style()
        
        # Create custom named styles specific to OSM Legend
        style.configure("OSMLegend.Treeview", 
                         background="#f5f5f5",
                         foreground="black",
                         rowheight=25,
                         fieldbackground="#f5f5f5")
        style.map('OSMLegend.Treeview', background=[('selected', '#4a6984')])
        
        # Configure the header style
        style.configure("OSMLegend.Treeview.Heading", 
                         font=('Arial', 10, 'bold'),
                         background="#e0e0e0",
                         foreground="black")
        
        # Create the treeview with the custom style
        window.tree = ttk.Treeview(
            tree_frame, 
            columns=("OSM Keys", "Words", "Types"),
            show="headings",
            yscrollcommand=y_scrollbar.set,
            xscrollcommand=x_scrollbar.set,
            style="OSMLegend.Treeview"  # Apply our custom style
        )
        
        # Configure column headings
        window.tree.heading("OSM Keys", text="OSM Keys", anchor="w")
        window.tree.heading("Words", text="Words/Tags", anchor="w")
        window.tree.heading("Types", text="BMS Types", anchor="w")
        
        # Configure column widths
        window.tree.column("OSM Keys", width=200, minwidth=150, anchor="w")
        window.tree.column("Words", width=300, minwidth=150, anchor="w")
        window.tree.column("Types", width=300, minwidth=150, anchor="w")
        
        # Configure scrollbars
        y_scrollbar.config(command=window.tree.yview)
        x_scrollbar.config(command=window.tree.xview)
        
        # Pack the treeview
        window.tree.pack(fill="both", expand=True)
        
        # Dictionary to store categories and their items
        window.category_data = {}
        
        # Populate the tree with data
        window.populate_tree()
        
        # Create category tabs
        for category in window.category_data:
            # Create tab for category
            cat_tab = Frame(notebook, bg=window.category_colors.get(category, "#f5f5f5"))
            notebook.add(cat_tab, text=category.capitalize())
            category_tabs[category] = cat_tab
            
            # Create treeview for category tab
            cat_tree_frame = Frame(cat_tab)
            cat_tree_frame.pack(fill="both", expand=True, padx=5, pady=5)
            
            # Add scrollbars
            cat_y_scrollbar = ttk.Scrollbar(cat_tree_frame, orient="vertical")
            cat_y_scrollbar.pack(side="right", fill="y")
            
            cat_x_scrollbar = ttk.Scrollbar(cat_tree_frame, orient="horizontal")
            cat_x_scrollbar.pack(side="bottom", fill="x")
            
            # Create the treeview for category with our custom style
            cat_tree = ttk.Treeview(
                cat_tree_frame, 
                columns=("OSM Keys", "Words", "Types"),
                show="headings",
                yscrollcommand=cat_y_scrollbar.set,
                xscrollcommand=cat_x_scrollbar.set,
                style="OSMLegend.Treeview"  # Apply our custom style
            )
            
            # Configure column headings
            cat_tree.heading("OSM Keys", text="OSM Keys", anchor="w")
            cat_tree.heading("Words", text="Words/Tags", anchor="w")
            cat_tree.heading("Types", text="BMS Types", anchor="w")
            
            # Configure column widths
            cat_tree.column("OSM Keys", width=200, minwidth=150, anchor="w")
            cat_tree.column("Words", width=300, minwidth=150, anchor="w")
            cat_tree.column("Types", width=300, minwidth=150, anchor="w")
            
            # Configure scrollbars
            cat_y_scrollbar.config(command=cat_tree.yview)
            cat_x_scrollbar.config(command=cat_tree.xview)
            
            # Pack the treeview
            cat_tree.pack(fill="both", expand=True)
            
            # Populate category-specific treeview
            for item_data in window.category_data[category]:
                cat_tree.insert("", "end", values=item_data)
        
        # Create help section at the bottom
        help_frame = Frame(main_frame, bg="#e0e0e0", height=30)
        help_frame.pack(fill="x", pady=5)
        
        help_text = Label(
            help_frame,
            text="Tip: OSM tags help identify the building type for automatic model selection. Click on a category tab for detailed view.",
            font=("Arial", 9),
            bg="#e0e0e0",
            fg="#555555"
        )
        help_text.pack(pady=5)
        
        # Make the window always appear on top
        window.attributes("-topmost", 1)
        
    def populate_tree(window):
        """Populate the treeview with OSM tag data"""
        # Dictionary to organize category data
        categories = {
            "aeroway": [],
            "barrier": [],
            "building": [],
            "man_made": [],
            "leisure": [],
            "military": [],
            "power": [],
            "sport": [],
            "tower": [],
            "religion": [],
            "bms": []
        }
        
        # Add aeroway items
        categories["aeroway"].append(("arresting_gear", "", "Arrestor Cable"))
        categories["aeroway"].append(("apron", "hangar, terminal, depot, warehouse", "Air Terminal, Hangar"))
        categories["aeroway"].append(("heliport, helipad", "helipad", "Helipad"))
        categories["aeroway"].append(("navigationaid", "localizer, tacan, beacon", "Nav Beacon"))
        categories["aeroway"].append(("terminal", "terminal", ""))
        categories["aeroway"].append(("tower", "", "Control Tower"))
        categories["aeroway"].append(("windsock", "windsock", ""))
        
        # Add barrier items
        categories["barrier"].append(("border_control", "", "Guard House"))
        categories["barrier"].append(("fence", "", "Fence"))
        
        # Add building items
        categories["building"].append(("cathedral, chapel, presbytery", "church, presbytery, cathedral, chapel, monastery", ""))
        categories["building"].append(("mosque, minaret, muslim", "minaret, mosque", ""))
        categories["building"].append(("temple", "temple, monastery", ""))
        categories["building"].append(("shrine", "shrine", ""))
        categories["building"].append(("synagogue", "synagogue", ""))
        categories["building"].append(("bridge, bridges", "", "Bridges"))
        categories["building"].append(("barrack, barracks", "", "Warehouse, Barracks, Depot"))
        categories["building"].append(("bunker", "", "Bunker"))
        categories["building"].append(("fuel, gasometer, storage_tank, tank", "fuel, gas", "Storage Tank"))
        categories["building"].append(("hangar", "HAS, hangar, FT Shelter", ""))
        categories["building"].append(("hospital", "", "Hospital"))
        categories["building"].append(("industrial", "", "Refinery, Cooling Tower, Chemical Plants, Power Plant, Factories, Transformer"))
        categories["building"].append(("silo", "silo", ""))
        categories["building"].append(("warehouse", "warehouse", "Warehouse"))
        categories["building"].append(("water_tower", "", "Water Tower"))
        
        # Add man_made items
        categories["man_made"].append(("beacon", "beacon", ""))
        categories["man_made"].append(("bridge, bridges", "", "Bridges"))
        categories["man_made"].append(("antenna, satellite_dish, telescope", "antenna, satellite", "R Tower, Radars, SAM, TV Station"))
        categories["man_made"].append(("communications_tower", "Radio Tower, Telecom Tower", ""))
        categories["man_made"].append(("cooling_tower", "", "Cooling Tower"))
        categories["man_made"].append(("flare, chimney", "Release Value", "Smoke Stack, Tower"))
        categories["man_made"].append(("gasometer, storage_tank, fuel, tank", "fuel, gas", "Storage Tank"))
        categories["man_made"].append(("lighting", "lights, light", "Lights"))
        categories["man_made"].append(("pump, pumping_station, works", "", "Refinery, Cooling Tower, Chemical Plants, Power Plant, Factories, Transformer"))
        categories["man_made"].append(("pipeline", "piping", ""))
        categories["man_made"].append(("silo", "silo", ""))
        categories["man_made"].append(("tower", "", "Control Tower"))
        categories["man_made"].append(("water_tower", "", "Water Tower"))
        
        # Add leisure items
        categories["leisure"].append(("stadium, ice_rink, sports_centre, sports_hall", "sport", "Stadium"))
        
        # Add military items
        categories["military"].append(("ammo, ammunition, munition", "ammo, ammunition, munition, bunker", ""))
        categories["military"].append(("barrack, barracks", "", "Warehouse, Barracks, Depot"))
        categories["military"].append(("bunker", "bunker", "Bunker"))
        
        # Add power items
        categories["power"].append(("compensator, plant, substation", "converter, Processor, Generator, Forge", "Power Plant, Refinery"))
        categories["power"].append(("tower, terminal, connection", "", "Power Tower"))
        categories["power"].append(("converter", "converter", ""))
        categories["power"].append(("transformer", "transformer", ""))
        categories["power"].append(("heliostat", "Solar Mirrors", ""))
        
        # Add sport items
        categories["sport"].append(("stadium, ice_rink, sports_centre, sports_hall", "sport", "Stadium"))
        
        # Add tower items
        categories["tower"].append(("control, traffic", "", "Control Tower"))
        categories["tower"].append(("lighting", "lights, light", "Lights"))
        categories["tower"].append(("minaret", "minaret, mosque", ""))
        categories["tower"].append(("monitoring, na", "", "R Tower"))
        categories["tower"].append(("communication", "Radio Tower, Telecom Tower", ""))
        categories["tower"].append(("radar", "radar", ""))
        categories["tower"].append(("watchtower, observation", "Watchtower", ""))
        
        # Add religion items
        categories["religion"].append(("buddhist, shinto", "temple, shrine, monastery", ""))
        categories["religion"].append(("christian", "church, presbytery, cathedral, chapel, monastery", ""))
        categories["religion"].append(("jewish", "synagogue", ""))
        categories["religion"].append(("muslim", "minaret, mosque", ""))
        categories["religion"].append(("anything else", "", "Shrine, Church"))
        
        # Add bms items
        categories["bms"].append(("'Name of a feature'", "Will search for the features requested", ""))
        
        # Store data in class variable for use in other methods
        window.category_data = categories
        
        # First add all data to main treeview
        for category, items in categories.items():
            # Create a parent node for the category
            category_node = window.tree.insert("", "end", values=(category.upper(), "", ""), tags=(category,))
            
            # Apply category styling
            window.tree.tag_configure(category, background=window.category_colors.get(category, "#f5f5f5"))
            
            # Add each item under its category
            for item_data in items:
                window.tree.insert(category_node, "end", values=item_data)
    
    def search_tree(window, query):
        """Search the treeview for matching items"""
        if not query:
            # If search is empty, reset to show all items
            window.tree.detach(*window.tree.get_children())
            window.populate_tree()
            return
            
        # Convert query to lowercase for case-insensitive search
        query = query.lower()
        
        # Clear the current tree
        window.tree.delete(*window.tree.get_children())
        
        # Search through all categories and items
        for category, items in window.category_data.items():
            category_added = False
            category_node = None
            
            for item_data in items:
                # Check if any column contains the search query
                if (query in item_data[0].lower() or 
                    query in item_data[1].lower() or 
                    query in item_data[2].lower()):
                    
                    # If category hasn't been added yet, add it first
                    if not category_added:
                        category_node = window.tree.insert("", "end", values=(category.upper(), "", ""), tags=(category,))
                        window.tree.tag_configure(category, background=window.category_colors.get(category, "#f5f5f5"))
                        category_added = True
                    
                    # Add the matching item
                    window.tree.insert(category_node, "end", values=item_data)
