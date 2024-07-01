from tkinter import ttk, Canvas, Button, PhotoImage, messagebox
import tkinter.filedialog
import tkinter as tk
import customtkinter as Ctk

# General libraries
import numpy as np
from pathlib import Path
import pandas as pd
import os
import json
import winreg
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import random as rand

# functions from Code
from MainCode import Load_Db
import Load_Geo_File as geo
import ValuesDictionary
import Restrictions
import OSMLegend
import InternalConsole
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
        # Initiate veriables
        # self.ASSETS_PATH = Path(__file__).parent / Path(r"Assets")
        self.ASSETS_PATH = Path(r"Assets")

        tk.Tk.__init__(self, *args, **kwargs)
        # Set Geometry of the page
        self.geometry("1152x720")
        self.configure(bg="#FFFFFF")
        self.resizable(False, False)
        # Set Shared data vatiables
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
            "debugger": tk.BooleanVar(),
        }
        self.shared_data["BMS_version"].set("-")
        self.shared_data["Theater"].set("-")
        self.shared_data["CTpath"].set("No CT file selected")
        self.shared_data["projection_path"].set("No Projection file selected")
        self.shared_data["backup_CTpath"].set("No CT file selected")
        self.shared_data["Geopath"].set("No GeoJson file selected")
        self.shared_data["debugger"] = False

        self.frames = {}
        for F in (DashboardPage, DatabasePage, GeoDataPage, OperationPage):
            page_name = F.__name__
            frame = F(parent=self, controller=self)
            self.frames[page_name] = frame
            # Configure the grid to expand and fill the window
            self.grid_rowconfigure(0, weight=1)
            self.grid_columnconfigure(0, weight=1)
            frame.grid(row=0, column=0, sticky="nsew")

        # Set Name and Icon
        self.title("Building Generator v0.95b")
        # icon_path = os.path.abspath("icon_128.ico")
        self.iconbitmap("icon_128.ico")

        # Select Dash as main front page
        self.show_frame("DashboardPage")
        # Startup check loading
        self.startup_definition()

    def show_frame(self, page_name):
        # Hide all frames
        for frame in self.frames.values():
            frame.grid_remove()
        # Show the selected frame
        frame = self.frames[page_name]
        frame.grid()

    def SelectCTfile(self, event):
        # open a file dialog and update the label text with the selected file path
        file_path = tkinter.filedialog.askopenfilename(
            filetypes=[("Class-Table files", "*.xml")]
        )
        if file_path:
            # Will place in CTfile the right path
            if file_path == "":
                self.shared_data["CTpath"].set("No CT file selected")
            else:
                self.shared_data["CTpath"].set(file_path)

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
                array = Load_Db(DB_path, "All")
                self.shared_data["BMS_Databse"] = array
                self.frames["DatabasePage"].UdpateDB_Tables()

            # If Database is not present, erase last data related to the old DB
            else:
                self.shared_data["BMS_Databse"] = np.array([])

                for row in self.frames["DatabasePage"].ModelsTable.get_children():
                    self.frames["DatabasePage"].ModelsTable.delete(row)

    def SettingWindow(self):
        Settings = Ctk.CTkToplevel(self)
        Settings.resizable(False, False)
        Settings.title("Settings")
        self.disable_Settings_buttons()

        self.SaveSettings = Ctk.CTkButton(
            Settings,
            text="Save Preset",
            fg_color="#A1B9D0",
            bg_color="#A1B9D0",
            height=33,
            width=167,
            corner_radius=5,
            hover_color="#7A92A9",
            command=self.save_config_file,
            text_color="#000000",
        )
        self.SaveSettings.grid(row=0, column=1, padx=10, pady=10)

        self.LoadSettings = Ctk.CTkButton(
            Settings,
            text="Load Preset",
            fg_color="#A1B9D0",
            bg_color="#A1B9D0",
            height=33,
            width=167,
            corner_radius=5,
            hover_color="#7A92A9",
            text_color="#000000",
            command=self.load_config,
        )
        self.LoadSettings.grid(row=0, column=2, padx=10, pady=10)

        self.Auto_Load = Ctk.CTkCheckBox(
            Settings,
            checkbox_height=18,
            checkbox_width=18,
            text="Startup",
            onvalue=True,
            offvalue=False,
            text_color="#565454",
            width=30,
            command=self.startup_selection_checkbox,
            fg_color="#8DBBE7",
        )
        self.Auto_Load.grid(row=0, column=0, padx=10, pady=10)

        self.debbuger = Ctk.CTkCheckBox(
            Settings,
            checkbox_height=18,
            checkbox_width=18,
            text="Debbuger",
            onvalue=True,
            offvalue=False,
            text_color="#565454",
            width=30,
            command=self.change_debugger_state,
            fg_color="#8DBBE7",
        )
        self.debbuger.grid(row=1, column=0, padx=10, pady=10)

        self.console_window = Ctk.CTkButton(
            Settings,
            text="Open Console Window",
            fg_color="#A1B9D0",
            bg_color="#A1B9D0",
            height=33,
            width=354,
            corner_radius=5,
            hover_color="#7A92A9",
            text_color="#000000",
            command=self.open_console_window,
        )
        self.console_window.grid(row=1, column=1, columnspan=2, padx=10, pady=10)

        # Set Startup state based on the shared data value
        if self.shared_data["Startup"].get():
            self.Auto_Load.select()
        else:
            self.Auto_Load.deselect()

        # Bind the window's "destroy" event to a function that enables the button
        Settings.bind("<Destroy>", self.enable_Settings_button)

    def change_debugger_state(self):
        debugger_value = self.debbuger.get()
        if debugger_value:
            print("Debugger Activated")
            self.shared_data["debugger"] = True
        elif not debugger_value:
            print("Debugger Deactivated")
            self.shared_data["debugger"] = False

    def open_console_window(self):
        """Opens a new console window"""
        InternalConsole.InternalConsole()

    def startup_selection_checkbox(self):
        """Change of checkbox in the settings window will set values to the shared value of startup
        It will load the config file, and change the value on the fly"""

        # Load Config file
        filename, filepath = "config.json", Path(r"config.json")
        # filepath = Path(__file__).parent / Path(filename)
        if os.path.isfile(filepath):
            with open(filename, "r") as f:
                loaded_data = json.load(f)

        # Set Startup state based on the shared data value
        if self.Auto_Load.get():
            self.shared_data["Startup"].set(True)
            loaded_data["Startup"] = self.shared_data["Startup"].get()
            with open(filename, "w") as f:
                json.dump(loaded_data, f)
        else:
            self.shared_data["Startup"].set(False)
            loaded_data["Startup"] = self.shared_data["Startup"].get()
            with open(filename, "w") as f:
                json.dump(loaded_data, f)

    def enable_Settings_button(self, event):
        # Enable the settings button in all pages
        for Page in ("DashboardPage", "DatabasePage", "GeoDataPage", "OperationPage"):
            self.frames[Page].button_settings.configure(state="normal")

    def disable_Settings_buttons(self):
        # Disable the settings button in all pages
        for Page in ("DashboardPage", "DatabasePage", "GeoDataPage", "OperationPage"):
            self.frames[Page].button_settings.configure(state="disabled")

    def save_config_file(self):
        """Check if Configuration file is exists, and Save it when "save" button is clicked"""
        filepath = Path(r"config.json")
        # filepath = Path(__file__).parent / Path(filename)
        if os.path.isfile(filepath):
            result = messagebox.askyesno(
                "Override",
                "Configuration file is already existing\nDo you want to override it?",
            )

            if result:
                settings = {
                    "Startup": self.shared_data["Startup"].get(),
                    "CT_path": self.shared_data["CTpath"].get(),
                    "BMS_Database_Path": self.shared_data["BMS_Database_Path"].get(),
                    "Theater": self.shared_data["Theater"].get(),
                    "BMS_version": self.shared_data["BMS_version"].get(),
                    "Geopath": self.shared_data["Geopath"].get(),
                    "backup_CTpath": self.shared_data["backup_CTpath"].get(),
                    "EditorSavingPath": self.shared_data["EditorSavingPath"].get(),
                    "Database_Availability": self.shared_data[
                        "Database_Availability"
                    ].get(),
                    "projection_path": self.shared_data["projection_path"].get(),
                    "projection_string": self.shared_data["projection_string"].get(),
                    "restriction_box": self.frames["OperationPage"].restriction_box.get(
                        "0.0", "end"
                    ),
                    "textbox_Radius_random": self.frames[
                        "OperationPage"
                    ].textbox_Radius_random.get(),
                    "textbox_Amount_random": self.frames[
                        "OperationPage"
                    ].textbox_Amount_random.get(),
                    "textbox_Values_random1": self.frames[
                        "OperationPage"
                    ].textbox_Values_random1.get(),
                    "textbox_Values_random2": self.frames[
                        "OperationPage"
                    ].textbox_Values_random2.get(),
                    "switch_Presence_random": self.frames[
                        "OperationPage"
                    ].switch_Presence_random.get(),
                    "textbox_Presence_random1": self.frames[
                        "OperationPage"
                    ].textbox_Presence_random1.get(),
                    "textbox_Presence_random2": self.frames[
                        "OperationPage"
                    ].textbox_Presence_random2.get(),
                    "Fillter_optionmenu": self.frames[
                        "OperationPage"
                    ].Fillter_optionmenu.get(),
                    "values_geo_optionmenu": self.frames[
                        "OperationPage"
                    ].values_geo_optionmenu.get(),
                    "values_rand_optionmenu": self.frames[
                        "OperationPage"
                    ].values_rand_optionmenu.get(),
                    "Selection_optionmenu": self.frames[
                        "OperationPage"
                    ].Selection_optionmenu.get(),
                    "Auto_features_detector": self.frames[
                        "OperationPage"
                    ].Auto_features_detector.get(),
                    "textbox_Amount_geo": self.frames[
                        "OperationPage"
                    ].textbox_Amount_geo.get(),
                    "textbox_Values_geo1": self.frames[
                        "OperationPage"
                    ].textbox_Values_geo1.get(),
                    "textbox_Values_geo2": self.frames[
                        "OperationPage"
                    ].textbox_Values_geo2.get(),
                    "switch_Presence_geo": self.frames[
                        "OperationPage"
                    ].switch_Presence_geo.get(),
                    "textbox_Presence_geo1": self.frames[
                        "OperationPage"
                    ].textbox_Presence_geo1.get(),
                    "textbox_Presence_geo2": self.frames[
                        "OperationPage"
                    ].textbox_Presence_geo2.get(),
                    "segemented_button": self.frames[
                        "OperationPage"
                    ].segemented_button.get(),
                    "segemented_button_Saving": self.frames[
                        "OperationPage"
                    ].segemented_button_Saving.get(),
                    "segemented_button_graphing1": self.frames[
                        "OperationPage"
                    ].segemented_button_graphing1.get(),
                    "segemented_button_graphing2": self.frames[
                        "OperationPage"
                    ].segemented_button_graphing2.get(),
                    "Editor_Extraction_name": self.frames[
                        "OperationPage"
                    ].Editor_Extraction_name.get(),
                }

                with open(filepath, "w") as f:
                    json.dump(settings, f)

                return messagebox.showinfo(
                    "Saving succeeded",
                    "The Saving process has been finished successfully",
                )

            else:
                return messagebox.showwarning(
                    "Saving Aborted", "The Saving process has been aborted"
                )

    def load_config(self):
        """Check if Configuration file is exists, and load it when "load" button is clicked"""
        filepath = Path(r"config.json")
        # filepath = Path(__file__).parent / Path(filename)
        if os.path.isfile(filepath):
            with open(filepath, "r") as f:
                loaded_data = json.load(f)

            self.shared_data["Startup"].set(loaded_data["Startup"])
            self.shared_data["CTpath"].set(loaded_data["CT_path"])
            self.shared_data["BMS_Database_Path"].set(loaded_data["BMS_Database_Path"])
            self.shared_data["Theater"].set(loaded_data["Theater"])
            self.shared_data["BMS_version"].set(loaded_data["BMS_version"])
            self.shared_data["Geopath"].set(loaded_data["Geopath"])
            self.shared_data["backup_CTpath"].set(loaded_data["backup_CTpath"])
            self.shared_data["EditorSavingPath"].set(loaded_data["EditorSavingPath"])
            self.shared_data["Database_Availability"].set(
                loaded_data["Database_Availability"]
            )
            self.shared_data["projection_path"].set(loaded_data["projection_path"])
            self.shared_data["projection_string"].set(loaded_data["projection_string"])
            self.frames["OperationPage"].Fillter_optionmenu.set(
                loaded_data["Fillter_optionmenu"]
            )
            self.frames["OperationPage"].values_geo_optionmenu.set(
                loaded_data["values_geo_optionmenu"]
            )
            self.frames["OperationPage"].values_rand_optionmenu.set(
                loaded_data["values_rand_optionmenu"]
            )
            self.frames["OperationPage"].Selection_optionmenu.set(
                loaded_data["Selection_optionmenu"]
            )
            self.frames["OperationPage"].segemented_button.set(
                loaded_data["segemented_button"]
            )
            self.frames["OperationPage"].segemented_button_Saving.set(
                loaded_data["segemented_button_Saving"]
            )
            self.frames["OperationPage"].segemented_button_graphing1.set(
                loaded_data["segemented_button_graphing1"]
            )
            self.frames["OperationPage"].segemented_button_graphing2.set(
                loaded_data["segemented_button_graphing2"]
            )

            # Force entries to diasable or enable
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
            for box in text_boxes:
                if loaded_data and loaded_data[box] is not None:
                    self.frames["OperationPage"].__dict__[box].delete(0, tk.END)
                    self.frames["OperationPage"].__dict__[box].insert(
                        0, loaded_data[box]
                    )
            self.frames["OperationPage"].restriction_box.delete("0.0", tk.END)
            self.frames["OperationPage"].restriction_box.insert(
                tk.END, loaded_data["restriction_box"]
            )

            # Will try to load Database through CT path that been inserted through the config file
            if loaded_data["CT_path"]:
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
                    array = Load_Db(DB_path, "All")
                    self.shared_data["BMS_Databse"] = array
                    self.frames["DatabasePage"].UdpateDB_Tables()

                # If Database is not present, erase last data related to the old DB
                else:
                    self.shared_data["BMS_Databse"] = np.array([])
                    self.shared_data["CTpath"].set("No CT file selected")
                    for row in self.frames["DatabasePage"].ModelsTable.get_children():
                        self.frames["DatabasePage"].ModelsTable.delete(row)

        else:
            return messagebox.showwarning(
                "Loading Aborted", "Configuration file couldn't be found."
            )

    def startup_definition(self):
        """Check if startup is exist in the configuration file, it its exists"""
        filename, filepath = "config.json", Path(r"config.json")
        # filepath = Path(__file__).parent / Path(filename)
        if os.path.isfile(filepath):
            with open(filename, "r") as f:
                loaded_data = json.load(f)
            if loaded_data["Startup"] == "1":
                self.load_config()

    def Get_Version_Theater_From_path(self, file_path):
        """The Fucntion gets a path of CT XML file and analyze the version
        BMS version and Theater are found and sent to the shared data variable.
        if not found "N/A" is mentioned
        file_path:   CT XML
        output:      none"""
        # Split path into components
        components = file_path.split("/")
        try:
            # find index of rightmost string of "Data"
            idx = components.index("Data")
            # Get the BMS version string before "Data"
            self.shared_data["BMS_version"].set(components[idx - 1])
            # if component before "Data" starts with "Add-on" or "Add-On" its theater
            if components[idx + 1].lower().startswith("add-on"):
                temp = components[idx + 1].lower().replace("add-on ", "")
                theater = (
                    temp[0].upper() + temp[1 : len(temp)]
                )  # Assign upper later to the first letter
                self.shared_data["Theater"].set(theater)
            else:
                # if version is not detected, place Korea as the default theater
                self.shared_data["Theater"].set("korea")

        except:
            # if version is not detected, find a theater with "add-on" (korea cannot be located)
            theater = "N/A"
            self.shared_data["BMS_version"].set("N/A")
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

        self.button_operations_img = PhotoImage(
            file=str(self.controller.ASSETS_PATH / "button_operations.png")
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

        self.button_geo_img = PhotoImage(
            file=str(self.controller.ASSETS_PATH / "button_geo.png")
        )

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

        self.button_data_img = PhotoImage(
            file=str(self.controller.ASSETS_PATH / "button_data.png")
        )

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

        self.button_dash_img = PhotoImage(
            file=str(self.controller.ASSETS_PATH / "button_dash.png")
        )
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

        self.button_settings_img = PhotoImage(
            file=str(self.controller.ASSETS_PATH / "button_options.png")
        )
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
            text="Welcome to the Building Generator \nfor Falcon BMS 4.38+",
            fill="#000000",
            font=("Inter Bold", 17 * -1, "bold"),
        )

        self.canvas.create_text(
            221.0,
            127.0,
            anchor="nw",
            text="the following software designed to help theater \ncreators to create custom Objectives with accurate"
            " \nplacement of buildings and features from a selected \nDatabase within BMS arsenal.\n\nTo be able"
            " to provide valid data please download \nQGIS and QuickOSM. \n\nTheater projection can be done through "
            "the software\nitself. Explanations will be offered in different section.\n",
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

        pie_figure = Figure(figsize=(5, 5), dpi=40)
        chart = pie_figure.add_subplot(111)

        # Pie chart
        labels = ["Apartment", "Power Plant", "Chemical Plant", "Army Bases"]
        sizes = [
            rand.randint(10, 400),
            rand.randint(10, 400),
            rand.randint(10, 400),
            rand.randint(10, 400),
        ]
        colors = ["#ff9999", "#66b3ff", "#99ff99", "#ffcc99"]
        explode = (0.1, 0, 0, 0)

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
        pie_canvas = FigureCanvasTkAgg(pie_figure, self)
        pie_canvas.draw()
        pie_canvas.get_tk_widget().place(x=587, y=115)

        self.canvas.create_text(
            856.0,
            134,
            anchor="nw",
            text="Amount of Generations processed: ",
            fill="#000000",
            font=("Inter", 12 * -1),
        )

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


class DatabasePage(tk.Frame):
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

        self.button_operations_img = PhotoImage(
            file=str(self.controller.ASSETS_PATH / "button_operations.png")
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

        self.button_geo_img = PhotoImage(
            file=str(self.controller.ASSETS_PATH / "button_geo.png")
        )

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

        self.button_data_img = PhotoImage(
            file=str(self.controller.ASSETS_PATH / "button_data.png")
        )

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

        self.button_dash_img = PhotoImage(
            file=str(self.controller.ASSETS_PATH / "button_dash.png")
        )
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

        self.button_settings_img = PhotoImage(
            file=str(self.controller.ASSETS_PATH / "button_options.png")
        )
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
            "Width",
            "WidthOff",
            "Length",
            "LengthOff",
            "Height",
            "LengthIdx",
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
            if col == "LengthIdx":
                self.ModelsTable.column(col, width=30)
            else:
                self.ModelsTable.column(col, width=52)

            # Insert basic data
            self.ModelsTable.insert(
                "",
                "end",
                values=["-", "-", "-", "-", "-", "-", "-", "-", "-", "-", "-"],
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
            text="List of buildings and features in the selected Database",
            fill="#000000",
            font=("Inter", 15 * -1),
        )

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
        """Sort the data in the given column."""
        if col in ["ModelNumber", "Type", "CTNumber", "EntityIdx"]:
            data = [(int(tree.set(item, col)), item) for item in tree.get_children("")]
        elif col in ["Width", "WidthOff", "Length", "LengthOff", "Height", "LengthIdx"]:
            data = [
                (float(tree.set(item, col)), item) for item in tree.get_children("")
            ]
        else:
            data = [(tree.set(item, col), item) for item in tree.get_children("")]

        data.sort(reverse=reverse)
        for index, (value, item) in enumerate(data):
            tree.move(item, "", index)

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
            # Exclude "Class" and "Domain" columns
            list_data = [
                list_data[0],
                list_data[1],
                list_data[4],
                list_data[5],
                list_data[6],
                list_data[7],
                list_data[8],
                list_data[9],
                list_data[10],
                list_data[11],
                list_data[12],
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
        """Function takes the chosen theater and BMS version and check if database is already exising
        if not, it will create folders with the relevant path and place the new database there"""
        if self.controller.shared_data["CTpath"].get() == "No CT file selected":
            return messagebox.showwarning(
                "Procedure Aborted", "Class Table XML has'nt been selected."
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
        # If db is detected in the detected folder, ask if you want to rewrite, else just create the db.
        if os.path.isfile(db_path):
            result = messagebox.askyesno(
                "Warning", "Suited Database has been found. Do you want to override it?"
            )
            if result:
                try:
                    CT_path = self.controller.shared_data["CTpath"].get()
                    debugger_state = self.controller.shared_data["debugger"]
                    GenerateDB(
                        CT_path, db_save_path, debugger_state, backup_CT_path
                    )  # Get Db saved
                    self.NewDBupdate()
                except ValueError:
                    messagebox.showwarning("Procedure Aborted", "Error has occurred")
            else:
                messagebox.showwarning(
                    "Procedure Aborted", "The Database generating has been aborted."
                )
        else:
            try:
                CT_path = self.controller.shared_data["CTpath"].get()
                debugger_state = self.controller.shared_data["debugger"]
                GenerateDB(CT_path, db_save_path, debugger_state, backup_CT_path)
                self.NewDBupdate()
            except ValueError:
                messagebox.showwarning("Procedure Aborted", "Error has occurred")

        # Update existing database table
        self.Udpate_existedDB_Tables()

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

        self.button_operations_img = PhotoImage(
            file=str(self.controller.ASSETS_PATH / "button_operations.png")
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

        self.button_geo_img = PhotoImage(
            file=str(self.controller.ASSETS_PATH / "button_geo.png")
        )

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

        self.button_data_img = PhotoImage(
            file=str(self.controller.ASSETS_PATH / "button_data.png")
        )

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

        self.button_dash_img = PhotoImage(
            file=str(self.controller.ASSETS_PATH / "button_dash.png")
        )
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

        self.button_settings_img = PhotoImage(
            file=str(self.controller.ASSETS_PATH / "button_options.png")
        )
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
            text="Amount of Structures:",
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
        self.textbox_structures_amount.place(x=375, y=489)

        # label and Entry for detailed structures
        self.label_structures_detailed = Ctk.CTkLabel(
            self, text="Detailed:", font=self.button_font, bg_color="#F8F9FB"
        )
        self.label_structures_detailed.place(x=454, y=486)
        self.textbox_structures_detailed = Ctk.CTkEntry(
            self,
            width=50,
            height=18,
            border_color="#D5E3F0",
            fg_color="#E7E7E7",
            placeholder_text="0",
            state="disabled",
        )
        self.textbox_structures_detailed.place(x=518, y=489)

        # label and Entry for structures_center
        self.label_structures_center = Ctk.CTkLabel(
            self, text="Center:", font=self.button_font, bg_color="#F8F9FB"
        )
        self.label_structures_center.place(x=598, y=486)
        self.textbox_structures_center = Ctk.CTkEntry(
            self,
            width=300,
            height=18,
            border_color="#D5E3F0",
            fg_color="#E7E7E7",
            placeholder_text="XXXX/YYYY",
            state="disabled",
        )
        self.textbox_structures_center.place(x=649, y=489)

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
            text="List of features in the selected region",
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
                self.GeoTable.column(col, width=38)
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
        """Sort the data in the given column."""
        if col == "Index":
            data = [(int(tree.set(item, col)), item) for item in tree.get_children("")]
        elif col in ["Length", "Width", "Rotation", "Height"]:
            data = [
                (float(tree.set(item, col)), item) for item in tree.get_children("")
            ]
        else:
            data = [(tree.set(item, col), item) for item in tree.get_children("")]

        data.sort(reverse=reverse)
        for index, (value, item) in enumerate(data):
            tree.move(item, "", index)

    def CalculateGeo(self):
        """will get Geo-Json file and If the file is valid, The box will be updated with the path string, and the structures list
        will be updated into the table in the page"""
        try:
            file_path = self.controller.shared_data["Geopath"].get()
        except ValueError:
            return messagebox.showerror("Error", "GeoJson path is invalid")

        if (
            self.controller.shared_data["projection_string"].get()
            or self.controller.shared_data["projection_string"].get() != ""
        ):
            string = self.controller.shared_data["projection_string"].get()
            try:
                debugger_state = self.controller.shared_data["debugger"]
                GeoFeatures, CalcData_GeoFeatures, AOI_center = geo.Load_Geo_File(
                    file_path, debugger_state, string
                )
                self.update_geo_data_GUI_fields(
                    GeoFeatures, CalcData_GeoFeatures, AOI_center
                )

            except ValueError:
                # Show message if string is not valid
                messagebox.showerror(
                    "Error", "Projection string or GeoJson path are not valid"
                )
                return
        else:
            try:
                debugger_state = self.controller.shared_data["debugger"]
                GeoFeatures, CalcData_GeoFeatures, AOI_center = geo.Load_Geo_File(
                    file_path, debugger_state
                )

                self.update_geo_data_GUI_fields(
                    GeoFeatures, CalcData_GeoFeatures, AOI_center
                )

            except ValueError:
                return messagebox.showerror(
                    "Error", "Projection string or GeoJson path are not valid"
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
            data_list[2:5] = [
                round(val, 3) for val in data_list[2:5]
            ]  # Round length, width, rotation
            try:
                data_list[8] = round(
                    float(heights[0, i]), 3
                )  # Replace initial height from the raw Geofile to the calculated height
            except:
                data_list[9] = 0
            self.GeoTable.insert("", "end", values=data_list)

        # Show message if succeeded
        return messagebox.showinfo(
            "Success", "The load of GeoData from GeoJson file has been succeeded"
        )

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
            0, str(CalcData_GeoFeatures["Detailed Structure"].value_counts()[1.0])
        )
        self.textbox_structures_detailed.configure(state="disabled")

        # Convert the numbers to strings and Join the numbers with a '/'
        str_AOI_center = " / ".join([str(num) for num in AOI_center])
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

        # open a file dialog and update the label text with the selected file path
        file_path = tkinter.filedialog.askopenfilename(
            filetypes=[("Geo-Json files", "*.GeoJson")]
        )
        if file_path:
            # Show File at the text place on the GUI
            self.controller.shared_data["Geopath"].set(file_path)

        else:
            self.controller.shared_data["Geopath"].set("No Projection file selected")
            self.controller.shared_data["Geodata"].set(np.array([]))

    def SelectProjectionfile(self, event):
        """The function called by the projection TXT button, and looking for txt file which contain a string of projection
        self.controller.shared_data["projection_path"] = will have the path if file is selected
        self.controller.shared_data["projection_string"] = will have the string itself for projection"""

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
                except:
                    try:
                        key, value = line.strip().split("=")
                    except:
                        return messagebox.showerror("Error", "File cannot be read")

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
        # Erase old values
        else:
            self.controller.shared_data["projection_path"].set(
                "No Projection file selected"
            )
            self.controller.shared_data["projection_string"].set("")


class OperationPage(tk.Frame):
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

        self.button_operations_img = PhotoImage(
            file=str(self.controller.ASSETS_PATH / "button_operations.png")
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

        self.button_geo_img = PhotoImage(
            file=str(self.controller.ASSETS_PATH / "button_geo.png")
        )

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

        self.button_data_img = PhotoImage(
            file=str(self.controller.ASSETS_PATH / "button_data.png")
        )

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

        self.button_dash_img = PhotoImage(
            file=str(self.controller.ASSETS_PATH / "button_dash.png")
        )
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

        self.button_settings_img = PhotoImage(
            file=str(self.controller.ASSETS_PATH / "button_options.png")
        )
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
            text="Please state the values of the feature’s restriction \nyou are willing to integrate",
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
        self.Auto_features_detector = Ctk.CTkCheckBox(
            self,
            checkbox_height=18,
            checkbox_width=18,
            text="Auto",
            onvalue=True,
            offvalue=False,
            font=self.button_font,
            text_color="#565454",
            width=30,
            bg_color="#FDFBFC",
        )
        self.Auto_features_detector.place(x=589, y=388)

        self.canvas.create_text(
            287.0,
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
            text="Objective number",
            fill="#000000",
            font=("Inter", 12 * -1),
        )

        # Create the CTkTextbox widget for Objective number
        self.textbox_Obj = Ctk.CTkEntry(
            self, width=74, height=18, border_color="#D5E3F0", text_color="#565454"
        )
        self.textbox_Obj.place(x=460, y=544)

        self.canvas.create_text(
            286.0,
            547.0,
            anchor="nw",
            text="CT number",
            fill="#000000",
            font=("Inter", 12 * -1),
        )

        # Create the CTkTextbox widget for CT number
        self.textbox_CT = Ctk.CTkEntry(
            self, width=74, height=18, border_color="#D5E3F0", text_color="#565454"
        )
        self.textbox_CT.place(x=460, y=518)

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
            text="More",
            font=("Arial", 10),
            text_color="#565454",
            # command=self.Browse_saving_path,
            fg_color="#D5E3F0",
        )
        self.Get_More_button.place(x=499, y=490)

        self.Get_Objective_button = Ctk.CTkButton(
            self,
            width=46,
            height=18,
            text="Browse",
            # command=self.Browse_saving_path,
            fg_color="#8DBBE7",
        )
        self.Get_Objective_button.place(x=400, y=518)
        self.Get_CT_button = Ctk.CTkButton(
            self,
            width=46,
            height=18,
            text="Browse",
            # command=self.Browse_saving_path,
            fg_color="#8DBBE7",
        )
        self.Get_CT_button.place(x=400, y=544)

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
            if Dimension == "2D":
                Show_Selected_Features_2D(
                    plot_option,
                    self.Filltered_GeoFeatures,
                    self.Filltered_Calc_GeoFeatures,
                    self.BMS_features_map,
                    LoadedBMSModels,
                )
            elif Dimension == "3D":
                Show_Selected_Features_3D(
                    plot_option,
                    self.Filltered_GeoFeatures,
                    self.Filltered_Calc_GeoFeatures,
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
                Show_Selected_Features_2D(
                    plot_option,
                    self.Filltered_GeoFeatures,
                    self.Filltered_Calc_GeoFeatures,
                )
            elif Dimension == "3D":
                Show_Selected_Features_3D(
                    plot_option,
                    self.Filltered_GeoFeatures,
                    self.Filltered_Calc_GeoFeatures,
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
        BuildingGeneratorVer = "0.91b"

        generating_method = self.segemented_button.get()
        saving_method = self.segemented_button_Saving.get()
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

                    elif self.values_geo_optionmenu.get() == "Random":
                        Values = max(min(int(self.textbox_Values_geo2.get()), 100), 0)
                        Values_i = max(
                            min(int(self.textbox_Values_geo1.get()), Values), 0
                        )
                    else:
                        Values = None
                        Values_i = None

                    # Prepere Presence of features through the Switch selection
                    Presence = max(min(int(self.textbox_Presence_geo2.get()), 100), 0)
                    # If range of presence is found set it in variable
                    if self.switch_Presence_geo.get() == 1:
                        Presence_i = max(
                            min(int(self.textbox_Presence_geo1.get()), Presence), 0
                        )
                    else:
                        Presence_i = None

                    fillter = self.Fillter_optionmenu.get()
                    selection = self.Selection_optionmenu.get()

                    restriction_text = self.restriction_box.get("0.0", "end")

                    (
                        Filltered_models,
                        self.Filltered_GeoFeatures,
                        self.Filltered_Calc_GeoFeatures,
                    ) = Assign_features_accuratly(
                        num_features,
                        DB_path,
                        restriction_text,
                        fillter,
                        GeoFeatures,
                        CalcData_GeoFeatures,
                    )

                    if saving_method == "Editor":
                        # initiate variables
                        file_save_path = os.path.join(
                            self.controller.shared_data["EditorSavingPath"].get(),
                            self.Editor_Extraction_name.get() + ".txt",
                        )
                        self.BMS_features_map = Save_accurate_features(
                            saving_method,
                            num_features,
                            self.Filltered_GeoFeatures,
                            self.Filltered_Calc_GeoFeatures,
                            DB_path,
                            Filltered_models,
                            selection,
                            file_save_path,
                            AOI_center,
                            Presence,
                            Values,
                            Presence_i,
                            Values_i,
                            self.Auto_features_detector.get(),
                            BuildingGeneratorVer,
                        )

                        # Without issues, success message will apear
                        messagebox.showinfo(
                            "Operation succeeded",
                            f"Editor file with {num_features} Accurate feautures has been successfully "
                            f"generated",
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
                    selected_data, x_coordinates, y_coordinates = (
                        Assign_features_randomly(
                            num_features, Radius, DB_path, restriction_text
                        )
                    )

                    # initiate save path
                    file_save_path = os.path.join(
                        self.controller.shared_data["EditorSavingPath"].get(),
                        self.Editor_Extraction_name.get() + ".txt",
                    )

                    Save_random_features(
                        saving_method,
                        num_features,
                        selected_data,
                        x_coordinates,
                        y_coordinates,
                        file_save_path,
                        BuildingGeneratorVer,
                        Presence,
                        Values,
                        Presence_i,
                        Values_i,
                        CT_Num=None,
                        Obj_Num=None,
                    )

                    messagebox.showinfo(
                        "Operation succeeded",
                        f"Editor file with {num_features} Random feautures has been successfully "
                        f"generated",
                    )

            # elif saving_method == "BMS":
            #     k = 1


if __name__ == "__main__":
    app = MainPage()
    app.mainloop()
