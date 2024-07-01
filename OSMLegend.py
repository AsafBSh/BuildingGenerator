import tkinter as tk
from tkinter import ttk


class OSMLegend(tk.Toplevel):
    def __init__(window):
        tk.Toplevel.__init__(window)
        window.title("Open Street map Legend")
        window.geometry("800x400")
        window.resizable(True, True)

        # Create a Treeview widget
        window.tree = ttk.Treeview(window, columns=("OSM Keys", "Words", "Types"))
        window.tree.heading("#0", text="Item")
        window.tree.heading("OSM Keys", text="OSM Keys")
        window.tree.heading("Words", text="Words")
        window.tree.heading("Types", text="Types")
        window.tree.pack(fill="both", expand=True)

        # Add aeroway items
        aeroway = window.tree.insert("", "end", text="aeroway")
        # Children for aeroway
        window.tree.insert(
            aeroway, "end", values=("arresting_gear", "", "Arrestor Cable")
        )
        window.tree.insert(
            aeroway,
            "end",
            values=(
                "apron",
                "hangar, terminal, depot, warehouse",
                "Air Terminal, Hangar",
            ),
        )
        window.tree.insert(
            aeroway, "end", values=("heliport, helipad", "helipad", "Helipad")
        )
        window.tree.insert(
            aeroway,
            "end",
            values=("navigationaid", "localizer, tacan, beacon", "Nav Beacon"),
        )
        window.tree.insert(aeroway, "end", values=("terminal", "terminal"))
        window.tree.insert(aeroway, "end", values=("tower", "", "Control Tower"))
        window.tree.insert(aeroway, "end", values=("windsock", "windsock"))

        # Add barrier items
        barrier = window.tree.insert("", "end", text="barrier")
        # Children for barrier
        window.tree.insert(barrier, "end", values=("border_control", "", "Guard House"))
        window.tree.insert(barrier, "end", values=("fence", "", "Fence"))

        # Add building items
        building = window.tree.insert("", "end", text="building")
        # Children for buildings
        window.tree.insert(
            building,
            "end",
            values=(
                "cathedral, chapel, presbytery",
                "church,presbytery, cathedral, chapel, monastery",
            ),
        )
        window.tree.insert(
            building, "end", values=("mosque, minaret, muslim", "minaret, mosque")
        )
        window.tree.insert(building, "end", values=("temple", "temple, monastery"))
        window.tree.insert(building, "end", values=("shrine", "shrine"))
        window.tree.insert(building, "end", values=("synagogue", "synagogue"))
        window.tree.insert(building, "end", values=("bridge, bridges", "", "Bridges"))
        window.tree.insert(
            building,
            "end",
            values=("barrack, barracks", "", "Warehouse, Barracks, Depot"),
        )
        window.tree.insert(building, "end", values=("bunker", "", "Bunker"))
        window.tree.insert(
            building,
            "end",
            values=("fuel, gasometer, storage_tank", "fuel", "Depot,Storage Tank"),
        )
        window.tree.insert(
            building, "end", values=("hangar", "HAS, hangar, FT Shelter")
        )
        window.tree.insert(building, "end", values=("hospital", "", "Hospital"))
        window.tree.insert(
            building,
            "end",
            values=(
                "industrial",
                "",
                "Refinery, Cooling Tower, Chemical Plants, Power Plant, Factories, Transformer",
            ),
        )

        window.tree.insert(building, "end", values=("silo", "silo"))
        window.tree.insert(building, "end", values=("water_tower", "", "Water Tower"))

        # Add man_made items
        man_made = window.tree.insert("", "end", text="man_made")
        # Children for man_made
        window.tree.insert(man_made, "end", values=("beacon", "beacon"))
        window.tree.insert(man_made, "end", values=("bridge, bridges", "", "Bridges"))
        window.tree.insert(
            man_made,
            "end",
            values=(
                "communications_tower, antenna, satellite_dish, telescope",
                "antenna, satellite",
                "R Tower, Radars, SAM, TV Station",
            ),
        )
        window.tree.insert(
            man_made, "end", values=("cooling_tower", "", "Cooling Tower")
        )
        window.tree.insert(
            man_made, "end", values=("flare, chimney", "", "Smoke Stack, Tower")
        )
        window.tree.insert(
            man_made,
            "end",
            values=("gasometer, storage_tank,fuel", "fuel", "Depot,Storage Tank"),
        )
        window.tree.insert(
            man_made, "end", values=("lighting", "lights,light", "Lights")
        )

        window.tree.insert(
            man_made,
            "end",
            values=(
                "pipeline, pump, pumping_station, works",
                "",
                "Refinery, Cooling Tower, Chemical Plants, Power Plant, Factories, Transformer",
            ),
        )
        window.tree.insert(man_made, "end", values=("silo", "silo"))
        window.tree.insert(man_made, "end", values=("tower", "", "Control Tower"))
        window.tree.insert(man_made, "end", values=("water_tower", "", "Water Tower"))

        # Add leisure items
        leisure = window.tree.insert("", "end", text="leisure")
        # Children for leisure
        window.tree.insert(
            leisure,
            "end",
            values=(
                "stadium, ice_rink, sports_centre, sports_hall",
                "sport",
                "Stadium",
            ),
        )

        # Add military items
        military = window.tree.insert("", "end", text="military")
        # Children for military
        window.tree.insert(
            military,
            "end",
            values=("ammo, ammunition, munition", "ammo, ammunition, munition, bunker"),
        )
        window.tree.insert(
            military,
            "end",
            values=("barrack, barracks", "", "Warehouse, Barracks, Depot"),
        )
        window.tree.insert(military, "end", values=("bunker", "", "Bunker"))

        # Add power items
        power = window.tree.insert("", "end", text="power")
        # Children for power
        window.tree.insert(
            power,
            "end",
            values=(
                "compensator, converter, plant, substation, transformer",
                "converter",
                "Power Plant, Refinery",
            ),
        )
        window.tree.insert(
            power, "end", values=("tower, terminal, connection", "", "Power Tower")
        )

        # Add sport items
        sport = window.tree.insert("", "end", text="sport")
        # Children for sport
        window.tree.insert(
            sport,
            "end",
            values=(
                "stadium, ice_rink, sports_centre, sports_hall",
                "sport",
                "Stadium",
            ),
        )

        # Add tower items
        tower = window.tree.insert("", "end", text="tower")
        # Children for tower
        window.tree.insert(
            tower, "end", values=("control, traffic", "", "Control Tower")
        )
        window.tree.insert(tower, "end", values=("lighting", "lights,light", "Lights"))
        window.tree.insert(tower, "end", values=("minaret", "minaret, mosque"))
        window.tree.insert(
            tower, "end", values=("monitoring, communication, na", "", "R Tower")
        )
        window.tree.insert(tower, "end", values=("radar", "radar"))
        window.tree.insert(
            tower, "end", values=("watchtower, observation", "Watchtower")
        )

        # Add religion items
        religion = window.tree.insert("", "end", text="religion")
        # Children for buildings
        window.tree.insert(
            religion, "end", values=("buddhist, shinto", "temple, shrine, monastery")
        )
        window.tree.insert(
            religion,
            "end",
            values=("christian", "church,presbytery, cathedral, chapel, monastery"),
        )
        window.tree.insert(religion, "end", values=("jewish", "synagogue"))
        window.tree.insert(religion, "end", values=("muslim", "minaret, mosque"))
        window.tree.insert(
            religion, "end", values=("anything else", "", "Shrine, Church")
        )

        # Make the window always appear on top
        window.attributes("-topmost", 1)

        window.mainloop()
