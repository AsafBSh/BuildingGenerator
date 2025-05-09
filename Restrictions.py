import tkinter as tk
import customtkinter as Ctk
from functools import partial


class RestrictionsWindow(tk.Toplevel):
    def __init__(self, restriction_box=None, restriction_button=None):
        tk.Toplevel.__init__(self)
        self.restriction_box = restriction_box
        self.restriction_button = restriction_button

        # Configure the window
        self.geometry("1000x590")
        self.minsize(750, 550)  # Set minimum window size
        self.resizable(True, True)
        self.title("Feature Restriction Window")
        self.configure(bg="#E7F3F7")  # Light blue background to match main GUI
        
        # Set the window position to center of screen
        self.update_idletasks()
        width = self.winfo_width()
        height = self.winfo_height()
        x = (self.winfo_screenwidth() // 2) - (width // 2)
        y = (self.winfo_screenheight() // 2) - (height // 2)
        self.geometry(f"+{x}+{y}")
        
        # Disable restriction button while window is open
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

        # Create main frame with padding
        main_frame = Ctk.CTkFrame(self, fg_color="#E7F3F7", corner_radius=10)
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)

        # Create a title label
        title_label = Ctk.CTkLabel(
            main_frame,
            text="Feature Restriction Configuration",
            font=("Helvetica", 16, "bold"),
            text_color="#1A1A1A"
        )
        title_label.pack(pady=(5, 5))

        # Create a frame for the panels with a specific weight distribution
        panels_frame = Ctk.CTkFrame(main_frame, fg_color="#E7F3F7")
        panels_frame.pack(fill="both", expand=True, padx=5, pady=5)
        panels_frame.grid_columnconfigure(0, weight=7)  # Left column gets 70% of width
        panels_frame.grid_columnconfigure(1, weight=3)  # Right column gets 30% of width

        # Left panel - Checkboxes section
        left_panel = Ctk.CTkFrame(panels_frame, fg_color="#D0E8F2", corner_radius=8)
        left_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 5), pady=5)

        # Add a label with explanation for the checkboxes
        checkbox_explanation = Ctk.CTkLabel(
            left_panel,
            text="Select feature types to include in the generator",
            font=("Helvetica", 12),
            text_color="#1A1A1A",
            wraplength=400
        )
        checkbox_explanation.pack(pady=(10, 2), padx=10)
        
        checkbox_info = Ctk.CTkLabel(
            left_panel,
            text="Checking a feature type will add it to the restriction list,\nallowing the Building Generator to create features of these types.",
            font=("Helvetica", 10),
            text_color="#555555",
            wraplength=400
        )
        checkbox_info.pack(pady=(0, 5), padx=10)

        # Create a scrollable frame for checkboxes
        checkbox_frame = Ctk.CTkScrollableFrame(left_panel, fg_color="#E7F3F7")
        checkbox_frame.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        # Right panel - Textbox section
        right_panel = Ctk.CTkFrame(panels_frame, fg_color="#D0E8F2", corner_radius=8)
        right_panel.grid(row=0, column=1, sticky="nsew", padx=(5, 0), pady=5)

        # Add a label with explanation for the textbox
        textbox_explanation = Ctk.CTkLabel(
            right_panel,
            text="Specify features by name",
            font=("Helvetica", 12),
            text_color="#1A1A1A",
            wraplength=200
        )
        textbox_explanation.pack(pady=(10, 2), padx=10)
        
        textbox_info = Ctk.CTkLabel(
            right_panel,
            text="Enter full or partial names of features to be generated.\nSeparate multiple feature names with commas.",
            font=("Helvetica", 10),
            text_color="#555555",
            wraplength=200
        )
        textbox_info.pack(pady=(0, 5), padx=10)

        # Create the textbox in the right panel
        self.feature_textbox = Ctk.CTkTextbox(
            right_panel, 
            fg_color="#FFFFFF",
            text_color="#1A1A1A",
            border_color="#8DBBE7",
            border_width=1,
            height=350
        )
        self.feature_textbox.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        # Get existing text from restriction_box
        restriction_text = self.restriction_box.get("0.0", "end")
        
        # Filter out numbers to display only named features
        words = [word.strip() for word in restriction_text.split(",") if not word.strip().isdigit()]
        words = [word for word in words if word and word != "\n"]
        
        # Insert filtered text into the feature_textbox
        if words:
            self.feature_textbox.insert("0.0", ", ".join(words))

        # Check the checkboxes based on the numbers in the restriction box
        # Split the restriction string into individual items
        restriction_list = [item.strip() for item in restriction_text.split(",")]

        # Create a list to store the numbers of the checked checkboxes
        checked_checkboxes = [item for item in restriction_list if item.isdigit()]

        # Create checkboxes with a cleaner layout
        for i, checkbox_name in enumerate(self.checkbox_dict.keys()):
            var = tk.IntVar()
            if self.checkbox_dict[checkbox_name] in checked_checkboxes:
                var.set(1)
            checkbox = Ctk.CTkCheckBox(
                checkbox_frame,
                text=f"{checkbox_name} ({self.checkbox_dict[checkbox_name]})",
                variable=var,
                onvalue=1,
                offvalue=0,
                fg_color="#8DBBE7",  # Blue accent color to match main GUI
                hover_color="#8DBBE7",
                text_color="#1A1A1A",
                checkmark_color="#FFFFFF",
                width=20,
                height=20
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

        # Button frame for footer buttons
        button_frame = Ctk.CTkFrame(main_frame, fg_color="#E7F3F7")
        button_frame.pack(fill="x", pady=(5, 0))

        # Create buttons with styling to match main GUI
        button_Import = Ctk.CTkButton(
            button_frame,
            text="Refresh",
            command=partial(
                self.import_restriction_text,
                checked_checkboxes,
                self.checkbox_dict,
                checkboxes,
            ),
            fg_color="#8DBBE7",
            hover_color="#7BAAD6",
            corner_radius=6,
            height=28
        )
        button_Import.pack(side="left", padx=(10, 5), pady=5, fill="x", expand=True)
        
        button_Export = Ctk.CTkButton(
            button_frame,
            text="Save & Close",
            command=lambda: self.save_and_close(checked_checkboxes),
            fg_color="#8DBBE7",
            hover_color="#7BAAD6",
            corner_radius=6,
            height=28
        )
        button_Export.pack(side="left", padx=(5, 10), pady=5, fill="x", expand=True)

        # Make the window always appear on top
        self.attributes("-topmost", 1)

        # Bind the window's "destroy" event to a function that enables the button
        self.bind("<Destroy>", self.enable_restriction_button)

        self.mainloop()

    def import_restriction_text(self, checked_checkboxes, checkbox_dict, checkboxes):
        """Refresh the UI based on the current restriction box content"""
        # Get current restriction text
        restriction_text = self.restriction_box.get("0.0", "end")
        
        # Split and process restriction items
        restriction_list = [item.strip() for item in restriction_text.split(",")]
        
        # Update checked_checkboxes list with numbers from restriction text
        checked_checkboxes.clear()
        for item in restriction_list:
            if item.isdigit():
                checked_checkboxes.append(item)
        
        # Filter words for the feature textbox
        words = [word.strip() for word in restriction_list if not word.strip().isdigit()]
        words = [word for word in words if word and word != "\n"]
        
        # Update feature textbox with words
        self.feature_textbox.delete("0.0", tk.END)
        if words:
            self.feature_textbox.insert("0.0", ", ".join(words))

        # Update checkboxes states based on checked_checkboxes list
        for checkbox_name, checkbox_var in checkboxes.items():
            checkbox, var = checkbox_var
            if checkbox_dict[checkbox_name] in checked_checkboxes:
                var.set(1)
            else:
                var.set(0)

    def export_restriction_text(self, checked_checkboxes):
        """Save the selections to the restriction box in MainGui"""
        # Get text from feature textbox
        feature_text = self.feature_textbox.get("0.0", "end").strip()
        
        # Process feature names
        words = []
        if feature_text:
            words = [word.strip() for word in feature_text.split(",")]
            words = [word for word in words if word]  # Remove empty entries
        
        # Combine feature names and checked feature numbers
        combined_features = words.copy()
        combined_features.extend(checked_checkboxes)
        new_features = ", ".join(combined_features)
        
        # Update the restriction box in the main GUI
        self.restriction_box.delete("0.0", tk.END)
        self.restriction_box.insert(tk.END, new_features)

    def save_and_close(self, checked_checkboxes):
        """Save the selections to the restriction box and close the window"""
        # Export the selections to the main restriction box
        self.export_restriction_text(checked_checkboxes)
        
        # Enable the restriction button
        self.restriction_button.configure(state="normal")
        
        # Close the window
        self.destroy()

    def update_checked_checkboxes(self, checkbox_dict, checked_checkboxes, var, name):
        """Update the checked_checkboxes list when a checkbox state changes"""
        if var.get() == 1:
            # If the checkbox is checked, add its number to the list
            if checkbox_dict[name] not in checked_checkboxes:
                checked_checkboxes.append(checkbox_dict[name])
        else:
            # If the checkbox is unchecked, remove its number from the list if it exists
            if checkbox_dict[name] in checked_checkboxes:
                checked_checkboxes.remove(checkbox_dict[name])

    def enable_restriction_button(self, event):
        """Re-enable the restriction button when window is closed"""
        # Only enable if this is actually being destroyed, not just a random event
        if event.widget == self:
            # Enable the button
            self.restriction_button.configure(state="normal")
