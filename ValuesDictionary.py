import tkinter as tk
import json
import os
import customtkinter as Ctk


class ValuesDictionary(tk.Toplevel):
    def __init__(self, filepath=None, callback=None):
        tk.Toplevel.__init__(self)
        self.title("Values Window")
        self.filepath = filepath
        self.geometry("680x450")

        # Call the callback when the window is destroyed
        self.callback = callback
        self.protocol("WM_DELETE_WINDOW", self.on_close)

        # Create a scrolled frame to hold the checkboxes
        self.frame = Ctk.CTkScrollableFrame(self, height=500)
        self.frame.grid(row=0, column=0, pady=5, padx=5, sticky="nsew")

        # Configure the grid to expand and fill the window
        self.grid_rowconfigure(0, weight=4)
        self.grid_columnconfigure(0, weight=4)

        try:
            # Load the values_dict from the file
            with open(filepath, "r") as f:
                self.values_dict = json.load(f)
            # If dictionary is found but is empty, raise an error
            if len(self.values_dict) == 0:
                raise Exception("Forced Error to load default values")
        except Exception:
            # If files is not exists, use the default values and create the file
            self.default_values()
            # Get the path of the current script and save the values_dict to the file
            own_path = os.path.dirname(os.path.realpath(__file__))
            # Add your filename to the script's path
            filename = "ValuesDic.json"
            self.filepath = os.path.join(own_path, filename)
            # Save the values_dict to the file
            with open(self.filepath, "w") as f:
                json.dump(self.values_dict, f)

        self.entries = {}
        col = 0  # Column number
        row = 0  # Row number
        for i, (key, value) in enumerate(self.values_dict.items()):
            row += 1
            if i % 17 == 0:
                col += 2
                row = 0
            Ctk.CTkLabel(self.frame, text=str(i + 1) + ". " + value["Type"]).grid(
                row=row, column=col
            )
            entry = Ctk.CTkEntry(
                self.frame, width=50
            )  # Adjust the width parameter as needed
            entry.insert(0, value["Value"])
            entry.grid(row=row, column=col + 1, padx=5, pady=2)
            self.entries[key] = entry

        # Grid the buttons with columnspan=2
        Ctk.CTkButton(
            self,
            text="Save",
            command=self.save,
            fg_color="#8DBBE7",
        ).grid(row=1, column=0, sticky="ew", padx=5, pady=2)
        Ctk.CTkButton(
            self,
            text="Set Default",
            command=self.default,
            fg_color="#8DBBE7",
        ).grid(row=2, column=0, sticky="ew", padx=5, pady=2)
        self.mainloop()

    def save(self):
        """
        Save the values_dict to the Json File.
        the values will be bonded between 0 and 100.
        :return:
        """
        for i, (key, entry) in enumerate(self.entries.items()):
            value = int(entry.get())
            if value < 0:
                self.values_dict[key]["Value"] = 0
            elif value > 100:
                self.values_dict[key]["Value"] = 100
            else:
                self.values_dict[key]["Value"] = value

        # Save the values_dict to the file
        with open(self.filepath, "w") as f:
            json.dump(self.values_dict, f)

    def default(self):
        # Reload the values_dict from the file
        self.default_values()

        for key, entry in self.entries.items():
            entry.delete(0, Ctk.END)
            key_value = self.values_dict[int(key)]["Value"]
            entry.insert(0, key_value)

    def on_close(self):
        self.callback()
        self.destroy()

    def default_values(self):
        self.values_dict = {
            1: {"Type": "Carter", "Value": "0"},
            2: {"Type": "Control Tower", "Value": "60"},
            3: {"Type": "Barn", "Value": "0"},
            4: {"Type": "Bunker", "Value": "50"},
            5: {"Type": "Blush", "Value": "0"},
            6: {"Type": "Factories", "Value": "50"},
            7: {"Type": "Church", "Value": "10"},
            8: {"Type": "City Hall", "Value": "20"},
            9: {"Type": "Dock", "Value": "80"},
            10: {"Type": "Depot", "Value": "40"},
            11: {"Type": "Runway", "Value": "95"},
            12: {"Type": "Warehouse", "Value": "0"},
            13: {"Type": "Helipad", "Value": "0"},
            14: {"Type": "Fuel Tanks", "Value": "40"},
            15: {"Type": "Nuclear Plant", "Value": "90"},
            16: {"Type": "Bridges", "Value": "80"},
            17: {"Type": "Pier", "Value": "90"},
            18: {"Type": "Power Pole", "Value": "60"},
            19: {"Type": "Shops", "Value": "0"},
            20: {"Type": "Power Tower", "Value": "60"},
            21: {"Type": "Apartment", "Value": "0"},
            22: {"Type": "House", "Value": "0"},
            23: {"Type": "Power Plant", "Value": "80"},
            24: {"Type": "Taxi Signs", "Value": "0"},
            25: {"Type": "Nav Beacon", "Value": "0"},
            26: {"Type": "Radar Site", "Value": "0"},
            27: {"Type": "Craters", "Value": "0"},
            28: {"Type": "Radars", "Value": "70"},
            29: {"Type": "R Tower", "Value": "60"},
            30: {"Type": "Taxiway", "Value": "0"},
            31: {"Type": "Rail Terminal", "Value": "0"},
            32: {"Type": "Refinery", "Value": "70"},
            33: {"Type": "SAM", "Value": "0"},
            34: {"Type": "Shed", "Value": "0"},
            35: {"Type": "Barracks", "Value": "10"},
            36: {"Type": "Tree", "Value": "0"},
            37: {"Type": "Water Tower", "Value": "10"},
            38: {"Type": "Town Hall", "Value": "30"},
            39: {"Type": "Air Terminal", "Value": "20"},
            40: {"Type": "Shrine", "Value": "0"},
            41: {"Type": "Park", "Value": "0"},
            42: {"Type": "Off Block", "Value": "20"},
            43: {"Type": "TV Station", "Value": "40"},
            44: {"Type": "Hotel", "Value": "0"},
            45: {"Type": "Hangar", "Value": "10"},
            46: {"Type": "Lights", "Value": "0"},
            47: {"Type": "VASI", "Value": "0"},
            48: {"Type": "Storage Tank", "Value": "30"},
            49: {"Type": "Fence", "Value": "0"},
            50: {"Type": "Parking Lot", "Value": "0"},
            51: {"Type": "Smoke Stack", "Value": "20"},
            52: {"Type": "Building", "Value": "10"},
            53: {"Type": "Cooling Tower", "Value": "30"},
            54: {"Type": "Cont Dome", "Value": "54"},
            55: {"Type": "Guard House", "Value": "0"},
            56: {"Type": "Transformer", "Value": "70"},
            57: {"Type": "Ammo Dump", "Value": "40"},
            58: {"Type": "Art Site", "Value": "0"},
            59: {"Type": "Office", "Value": "0"},
            60: {"Type": "Chemical Plant", "Value": "80"},
            61: {"Type": "Tower", "Value": "0"},
            62: {"Type": "Hospital", "Value": "0"},
            63: {"Type": "Shops/Blocks", "Value": "20"},
            64: {"Type": "Static", "Value": "0"},
            65: {"Type": "Runway Marker", "Value": "0"},
            66: {"Type": "Stadium", "Value": "0"},
            67: {"Type": "Monument", "Value": "0"},
            68: {"Type": "Arrestor Cable", "Value": "0"},
        }
