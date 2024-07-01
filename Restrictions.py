import tkinter as tk
import customtkinter as Ctk
from functools import partial


class RestrictionsWindow(tk.Toplevel):
    def __init__(self, restriction_box=None, restriction_button=None):
        tk.Toplevel.__init__(self)
        self.restriction_box = restriction_box
        self.restriction_button = restriction_button

        self.geometry("600x400")
        self.resizable(True, True)
        self.title("Restriction Window")
        """Will show all the restrictions that are available in BMS"""
        # disable button
        self.restriction_button.configure(state="disabled")

        # Create a dictionary to map checkbox names to numbers
        self.checkbox_dict = {
            "Carter": "1",
            "Control Tower": "2",
            "Barn": "3",
            "Bunker": "4",
            "Blush": "5",
            "Factories": "6",
            "Church": "7",
            "City Hall": "8",
            "Dock": "9",
            "Depot": "10",
            "Runway": "11",
            "Warehouse": "12",
            "Helipad": "13",
            "Fuel Tanks": "14",
            "Nuclear Plant": "15",
            "Bridges": "16",
            "Pier": "17",
            "Power Pole": "18",
            "Shops": "19",
            "Power Tower": "20",
            "Apartment": "21",
            "House": "22",
            "Power Plant": "23",
            "Taxi Signs": "24",
            "Nav Beacon": "25",
            "Radart Site": "26",
            "Craters": "27",
            "Radars": "28",
            "R Tower": "29",
            "Taxiway": "30",
            "Rail Terminal": "31",
            "Refinery": "32",
            "SAM": "33",
            "Shed": "34",
            "Barracks": "35",
            "Tree": "36",
            "Water Tower": "37",
            "Town Hall": "38",
            "Air Terminal": "39",
            "Shrine": "40",
            "Park": "41",
            "Off Block": "42",
            "TV Station": "43",
            "Hotel": "44",
            "Hangar": "45",
            "Lights": "46",
            "VASI": "47",
            "Storage Tank": "48",
            "Fence": "49",
            "Parking Lot": "50",
            "Smoke Stack": "51",
            "Building": "52",
            "Cooling Tower": "53",
            "Cont Dome": "54",
            "Guard House": "55",
            "Transformer": "56",
            "Ammo Dump": "57",
            "Art Site": "58",
            "Office": "59",
            "Chemical Plant": "60",
            "Tower": "61",
            "Hospital": "62",
            "Shops/Blocks": "63",
            "Static": "64",
            "Runway Marker": "65",
            "Stadium": "66",
            "Monument": "67",
            "Arrestor Cable": "68",
        }

        # Create a dictionary to store the checkboxes
        checkboxes = {}

        # Create a scrolled frame to hold the checkboxes
        scrolled_frame = Ctk.CTkScrollableFrame(self)
        scrolled_frame.pack(fill="both", expand=True, pady=5, padx=5)

        # Check the checkboxes based on the numbers in the restriction box
        # Split the Fillter string into individual items
        restriction_list = [
            item.strip() for item in self.restriction_box.get("0.0", "end").split(",")
        ]

        # Create a list to stor the numbers of the checked checkboxes
        checked_checkboxes = [item for item in restriction_list if item.isdigit()]

        for i, checkbox_name in enumerate(self.checkbox_dict.keys()):
            var = tk.IntVar()
            if self.checkbox_dict[checkbox_name] in checked_checkboxes:
                var.set(1)
            checkbox = Ctk.CTkCheckBox(
                scrolled_frame,
                text=str(i + 1) + ". " + checkbox_name,
                variable=var,
                onvalue=1,
                offvalue=0,
            )
            checkbox.configure(
                command=partial(
                    self.update_checked_checkboxes,
                    self.checkbox_dict,
                    checked_checkboxes,
                    var,
                    checkbox_name,
                )
            )
            checkbox.grid(row=i % 17, column=i // 17, sticky="w", pady=2, padx=5)
            # Store the checkbox and the associated variable in the dictionary
            checkboxes[checkbox_name] = (checkbox, var)

        # Create two buttons at the bottom of the page
        button_Import = Ctk.CTkButton(
            self,
            text="Import",
            command=partial(
                self.import_restriction_text,
                checked_checkboxes,
                self.checkbox_dict,
                checkboxes,
            ),
            fg_color="#8DBBE7",
        )
        button_Import.pack(side="bottom", fill="x", pady=5, padx=5)
        button_Export = Ctk.CTkButton(
            self,
            text="Export",
            command=partial(self.export_restriction_text, checked_checkboxes),
            fg_color="#8DBBE7",
        )
        button_Export.pack(side="bottom", fill="x", pady=5, padx=5)

        # Make the window always appear on top
        self.attributes("-topmost", 1)

        # Bind the window's "destroy" event to a function that enables the button
        self.bind("<Destroy>", self.enable_restriction_button)

        self.mainloop()

    def import_restriction_text(self, checked_checkboxes, checkbox_dict, checkboxes):
        """The function ill load the restriction text box into the restriction window"""
        restriction_list = [
            item.strip() for item in self.restriction_box.get("0.0", "end").split(",")
        ]

        # Create a list to stor the numbers of the checked checkboxes
        checked_checkboxes = [item for item in restriction_list if item.isdigit()]

        # Check the checkboxes if their numbers are in the list
        for checkbox_name, checkbox_var in checkboxes.items():
            checkbox, var = checkbox_var
            if checkbox_dict[checkbox_name] in checked_checkboxes:
                var.set(1)
            else:
                var.set(0)

    def export_restriction_text(self, checked_checkboxes):
        """The function ill save the checkboxes selected in the restriction window to the restriction text box"""
        text_box = self.restriction_box.get("0.0", "end")

        all_features = [item.strip() for item in text_box.split(",")]
        words = [word.strip() for word in all_features if not word.isdigit()]
        if "" in words:
            words.remove("")
        if "\n" in words:
            words.remove("\n")

        # Create string of all new features (words and numbers)
        new_features = words
        new_features.extend(checked_checkboxes)
        new_features = ", ".join(new_features)

        # Insert into the Gui box
        self.restriction_box.delete("0.0", tk.END)
        self.restriction_box.insert(tk.END, new_features)

    def update_checked_checkboxes(self, checkbox_dict, checked_checkboxes, var, name):
        if var.get() == 1:
            # If the checkbox is checked, add its number to the list
            checked_checkboxes.append(checkbox_dict[name])
        else:
            # If the checkbox is unchecked, remove its number from the list if it exists
            if checkbox_dict[name] in checked_checkboxes:
                checked_checkboxes.remove(checkbox_dict[name])

    def enable_restriction_button(self, event):
        # Enable the button
        self.restriction_button.configure(state="normal")
