import re
import time
import gzip
import json
import math
import sqlite3
import numpy as np
import pandas as pd
from tkinter import messagebox
from pathlib import Path
import matplotlib.pyplot as MatPlt
from scipy.spatial.distance import cdist
from collections import Counter
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
from utils.file_manager import FileManager


# Load the data from the database
def Load_Db(path, feature_name="All"):
    """Loads Classified DB based on demand
    *feature_name is string, and will have all the information in numbers and strings
    --if all data need to be extracted, place "All, or empty space
    --numbers will be classified as "types" and names would be matched by the actual name
    --if "ModelNum" is present, every number would be extracted from the model number"""

    conn = sqlite3.connect(path)
    # Get all items divided by comma
    Allitems = [item.strip() for item in feature_name.split(",")]

    # Adjust the query based on the feature type
    AllModels = {"", "\n", "All"}

    # convert to sets
    set_Allitems = set(Allitems)
    if set_Allitems.issubset(AllModels) and len(Allitems) == 1:
        query = "SELECT * FROM MyTable"

    elif "ModelNum" in Allitems:
        # get only the numbers inside the
        numbers = [number.strip() for number in Allitems if number.isdigit()]
        # Construct the query to match any of the words in Allitems
        number_conditions = " OR ".join(
            [f"ModelNumber = {number}" for number in numbers]
        )
        # Combine the conditions
        query = f"SELECT * FROM MyTable WHERE {number_conditions}"

    else:
        # Separate words and numbers
        words = [item for item in Allitems if not item.isdigit()]
        numbers = [item for item in Allitems if item.isdigit()]

        # Construct the query to match any of the words in FeatureName and any of the numbers in Type
        word_conditions = " OR ".join(
            [f"FeatureName LIKE '%{word}%'" for word in words]
        )
        number_conditions = " OR ".join([f"Type = {number}" for number in numbers])

        # Combine the conditions
        if word_conditions and number_conditions:
            query = f"SELECT * FROM MyTable WHERE ({word_conditions}) OR ({number_conditions})"
        elif word_conditions:
            query = f"SELECT * FROM MyTable WHERE {word_conditions}"
        elif number_conditions:
            query = f"SELECT * FROM MyTable WHERE {number_conditions}"

    dataframe = pd.read_sql_query(query, conn)

    conn.close()

    # get size
    num_rows, num_cols = dataframe.shape
    # Generate random indices to ensure random load of data
    np.random.seed(num_rows)  # To ensure reproducibility
    selected_indices = np.random.choice(num_rows, size=num_rows, replace=False)

    # Get the CT numbers and feature names for the selected indices
    random_dataframe = dataframe.iloc[selected_indices]

    return random_dataframe


def Show_Selected_Features(buildings, Calc_data):
    # Create a figure and axis
    # fig, ax = plt.subplots()

    # Loop through each feature
    for i in range(len(buildings)):
        feature = buildings.iloc[i]
        length = feature["length"]
        width = feature["width"]
        rotation = feature["rotation"]

        # Extract radius and angle from calc_features
        radius = Calc_data[i, 3]
        angle = Calc_data[i, 4]

        x_distance = radius * math.cos(math.radians(angle))
        y_distance = radius * math.sin(math.radians(angle))

        # Calculate the corner points of the rectangle
        corner_points = np.array(
            [
                [-width / 2, -length / 2],
                [width / 2, -length / 2],
                [width / 2, length / 2],
                [-width / 2, length / 2],
            ]
        )

        # Apply rotation to the corner points
        rotation_matrix = np.array(
            [
                [np.cos(np.radians(rotation)), -np.sin(np.radians(rotation))],
                [np.sin(np.radians(rotation)), np.cos(np.radians(rotation))],
            ]
        )
        rotated_corner_points = np.dot(corner_points, rotation_matrix.T)

        # Translate the corner points to the center
        translated_corner_points = rotated_corner_points + [y_distance, x_distance]

        # Plot the points
        MatPlt.plot(
            translated_corner_points[:, 1], translated_corner_points[:, 0], label=None
        )

        # Connect the last point to the first point to close the shape
        MatPlt.plot(
            [translated_corner_points[-1, 1], translated_corner_points[0, 1]],
            [translated_corner_points[-1, 0], translated_corner_points[0, 0]],
        )

    # Set the title for the plot
    MatPlt.title("Shape from Points")


def Show_Selected_Features_2D(
    plot_option,
    buildings=None,
    Calc_data=None,
    feature_entries=None,
    models_FrameData=None,
):
    # Create a single figure for all visualizations
    fig = MatPlt.figure(figsize=(10, 8))
    
    # Create coordinate limits based on all data for consistent scaling
    x_coords = []
    y_coords = []
    
    # Collect all coordinates for proper scaling
    if buildings is not None:
        for i in range(len(buildings)):
            x_coords.append(Calc_data[i, 5])
            y_coords.append(Calc_data[i, 6])
    
    if feature_entries is not None:
        for entry in feature_entries:
            entry_parts = entry.split()
            x_coords.append(float(entry_parts[2]))
            y_coords.append(float(entry_parts[1]))
    
    # Calculate padding for axes limits
    if x_coords and y_coords:
        x_min, x_max = min(x_coords), max(x_coords)
        y_min, y_max = min(y_coords), max(y_coords)
        x_padding = (x_max - x_min) * 0.15
        y_padding = (y_max - y_min) * 0.15
        x_limits = [x_min - x_padding, x_max + x_padding]
        y_limits = [y_min - y_padding, y_max + y_padding]
    else:
        x_limits = [-2000, 2000]
        y_limits = [-2000, 2000]

    # Create the appropriate number of subplots based on plot_option
    if plot_option == "Both":
        # Both side-by-side and combined view
        gs = MatPlt.GridSpec(2, 2, height_ratios=[1, 1])
        ax1 = fig.add_subplot(gs[0, 0])  # GeoJSON only
        ax2 = fig.add_subplot(gs[0, 1])  # BMS only
        ax3 = fig.add_subplot(gs[1, :])  # Combined view
        axes = [ax1, ax2, ax3]
        titles = ["Selected Buildings from JSON", "Feature Entries from BMS", "Combined View"]
    else:
        # Single view
        ax = fig.add_subplot(111)
        axes = [ax]
        titles = ["Selected Buildings from JSON" if plot_option == "JSON_BondingBox" else "Feature Entries from BMS"]

    # Create a function to draw buildings with better styling
    def draw_buildings(ax, buildings_data, calc_data, color, alpha, is_geo=True):
        for i in range(len(buildings_data)):
            feature = buildings_data.iloc[i]
            length = feature["length"]
            width = feature["width"]
            
            # Use consistent rotation based on the current solution
            rotation = (feature["rotation"] + 90) % 360
            
            # Extract coordinates
            x_distance = calc_data[i, 5]
            y_distance = calc_data[i, 6]
            
            # Calculate corner points
            corner_points = np.array([
                [-width / 2, -length / 2],
                [width / 2, -length / 2],
                [width / 2, length / 2],
                [-width / 2, length / 2],
            ])
            
            # Apply rotation
            rotation_matrix = np.array([
                [np.cos(np.radians(rotation)), -np.sin(np.radians(rotation))],
                [np.sin(np.radians(rotation)), np.cos(np.radians(rotation))],
            ])
            rotated_points = np.dot(corner_points, rotation_matrix.T)
            
            # Translate points
            translated_points = rotated_points + [y_distance, x_distance]
            
            # Close the shape
            translated_points = np.concatenate([translated_points, translated_points[0:1]])
            
            # Plot building outline
            ax.plot(translated_points[:, 1], translated_points[:, 0], color=color, linewidth=1.5, alpha=alpha)
            
            # Fill building with color
            ax.fill(translated_points[:, 1], translated_points[:, 0], color=color, alpha=alpha*0.3)
            
            # Add label at center
            if is_geo:
                label = f"B{i}"
                tooltip = f"Building {i}: {length:.1f}×{width:.1f}ft"
            else:
                label = f"{i}"
                name = feature.get("name", "")
                tooltip = f"{name}: {length:.1f}×{width:.1f}ft"
            
            ax.text(x_distance, y_distance, label, ha='center', va='center', 
                   fontsize=8, color='black', weight='bold', alpha=0.7)
    
    # Function to draw BMS features
    def draw_features(ax, entries, models_data, color, alpha):
        for i, entry in enumerate(entries):
            entry_parts = entry.split()
            ct_number = int(re.search(r"\d+", entry_parts[0]).group())
            
            # Find model data
            model_data = models_data[models_data["CTNumber"].astype(str).str.contains(str(ct_number))]
            if model_data.empty:
                continue
                
            model_width = model_data.iloc[0]["Width"]
            model_length = model_data.iloc[0]["Length"]
            
            # Get coordinates and rotation
            y_distance, x_distance = map(float, entry_parts[1:3])
            rotation = float(entry_parts[4])
            
            # Adjust rotation based on LengthIdx
            if model_data.iloc[0]["LengthIdx"] == 0:
                rotation = (rotation + 90) % 360
            
            # Calculate corner points
            corner_points = np.array([
                [-model_width / 2, -model_length / 2],
                [model_width / 2, -model_length / 2],
                [model_width / 2, model_length / 2],
                [-model_width / 2, model_length / 2],
            ])
            
            # Apply rotation
            rotation_matrix = np.array([
                [np.cos(np.radians(rotation)), -np.sin(np.radians(rotation))],
                [np.sin(np.radians(rotation)), np.cos(np.radians(rotation))],
            ])
            rotated_points = np.dot(corner_points, rotation_matrix.T)
            
            # Translate points
            translated_points = rotated_points + [y_distance, x_distance]
            
            # Close the shape
            translated_points = np.concatenate([translated_points, translated_points[0:1]])
            
            # Plot building outline
            ax.plot(translated_points[:, 1], translated_points[:, 0], color=color, linewidth=1.5, alpha=alpha)
            
            # Fill building with color
            ax.fill(translated_points[:, 1], translated_points[:, 0], color=color, alpha=alpha*0.3)
            
            # Add label
            feature_name = model_data.iloc[0]["FeatureName"]
            short_name = f"F{i}"
            ax.text(x_distance, y_distance, short_name, ha='center', va='center', 
                   fontsize=8, color='black', weight='bold', alpha=0.7)
    
    # Draw the appropriate content on each axis
    for idx, ax in enumerate(axes):
        # Configure common axis properties
        ax.set_xlabel("X [feet]")
        ax.set_ylabel("Y [feet]")
        ax.grid(True, linestyle='--', alpha=0.6)
        ax.set_title(titles[idx])
        
        # Set consistent axis limits
        ax.set_xlim(x_limits)
        ax.set_ylim(y_limits)
        
        # Draw content based on plot option and current axis
        if plot_option == "Both":
            if idx == 0 and buildings is not None:
                # GeoJSON buildings only
                draw_buildings(ax, buildings, Calc_data, 'blue', 0.8, True)
                ax.set_aspect('equal')
            
            elif idx == 1 and feature_entries is not None:
                # BMS features only
                draw_features(ax, feature_entries, models_FrameData, 'red', 0.8)
                ax.set_aspect('equal')
            
            elif idx == 2:
                # Combined view
                if buildings is not None:
                    draw_buildings(ax, buildings, Calc_data, 'blue', 0.7, True)
                if feature_entries is not None:
                    draw_features(ax, feature_entries, models_FrameData, 'red', 0.7)
                ax.set_aspect('equal')
                
                # Add legend for combined view
                from matplotlib.patches import Patch
                geo_patch = Patch(color='blue', alpha=0.3, label='GeoJSON Buildings')
                bms_patch = Patch(color='red', alpha=0.3, label='BMS Features')
                ax.legend(handles=[geo_patch, bms_patch], loc='upper right')
        
        else:
            # Single view
            if plot_option == "JSON_BondingBox" and buildings is not None:
                draw_buildings(ax, buildings, Calc_data, 'blue', 0.8, True)
            elif plot_option == "BMS_Fitting" and feature_entries is not None:
                draw_features(ax, feature_entries, models_FrameData, 'red', 0.8)
            ax.set_aspect('equal')
    
    # Add a scale bar on the combined view or single view
    scale_bar_ax = axes[-1]
    scale_length = 100  # 100 feet scale bar
    x_pos = x_limits[0] + (x_limits[1] - x_limits[0]) * 0.05
    y_pos = y_limits[0] + (y_limits[1] - y_limits[0]) * 0.05
    scale_bar_ax.plot([x_pos, x_pos + scale_length], [y_pos, y_pos], 'k-', linewidth=2)
    scale_bar_ax.text(x_pos + scale_length/2, y_pos - (y_limits[1] - y_limits[0]) * 0.02, 
                     f"{scale_length} feet", ha='center', va='top')
    
    # Add a compass indicator in the corner
    compass_ax = axes[-1]
    compass_size = min(x_limits[1] - x_limits[0], y_limits[1] - y_limits[0]) * 0.05
    compass_x = x_limits[1] - (x_limits[1] - x_limits[0]) * 0.1
    compass_y = y_limits[1] - (y_limits[1] - y_limits[0]) * 0.1
    
    # Draw compass
    compass_ax.arrow(compass_x, compass_y, 0, compass_size, head_width=compass_size*0.3, 
                    head_length=compass_size*0.3, fc='k', ec='k')
    compass_ax.text(compass_x, compass_y + compass_size*1.2, 'N', ha='center', va='center', fontweight='bold')
    
    # Adjust layout and show
    fig.tight_layout()
    MatPlt.show()
    
    return axes


def Show_Selected_Features_3D(
    plot_option,
    buildings=None,
    Calc_data=None,
    feature_entries=None,
    models_FrameData=None,
):
    # Create a figure
    fig = MatPlt.figure(figsize=(10, 8))
    
    # Initialize variables to store the min and max values for each axis
    x_min, x_max, y_min, y_max, z_max = (
        float("inf"),
        float("-inf"),
        float("inf"),
        float("-inf"),
        float("-inf"),
    )
    
    # Collect data from both sources to determine proper axis limits
    building_data = []
    feature_data = []
    
    # Process building data if available
    if buildings is not None and len(buildings) > 0:
        for i in range(len(buildings)):
            feature = buildings.iloc[i]
            length = feature["length"]
            width = feature["width"]
            height = Calc_data[i, 1]
            rotation = (feature["rotation"] + 90) % 360
            x_distance = Calc_data[i, 5]
            y_distance = Calc_data[i, 6]
            
            building_data.append({
                "length": length,
                "width": width,
                "height": height,
                "rotation": rotation,
                "x": x_distance,
                "y": y_distance,
                "idx": i,
                "name": f"B{i}",
                "type": "geo"
            })
            
            # Update bounds
            x_min = min(x_min, x_distance - width/2, x_distance + width/2)
            x_max = max(x_max, x_distance - width/2, x_distance + width/2)
            y_min = min(y_min, y_distance - length/2, y_distance + length/2)
            y_max = max(y_max, y_distance - length/2, y_distance + length/2)
            z_max = max(z_max, height)
    
    # Process feature data if available
    if feature_entries is not None and len(feature_entries) > 0:
        for i, entry in enumerate(feature_entries):
            entry_parts = entry.split()
            ct_number = int(re.search(r"\d+", entry_parts[0]).group())
            
            # Find model data
            model_data = models_FrameData[
                models_FrameData["CTNumber"].astype(str).str.contains(str(ct_number))
            ]
            if model_data.empty:
                continue
                
            model_width = model_data.iloc[0]["Width"]
            model_length = model_data.iloc[0]["Length"]
            model_height = model_data.iloc[0]["Height"]
            
            # Get coordinates and rotation
            y_distance, x_distance = map(float, entry_parts[1:3])
            if len(entry_parts) >= 4:
                z_height = float(entry_parts[3])
            else:
                z_height = 0.0
                
            rotation = float(entry_parts[4]) if len(entry_parts) >= 5 else 0.0
            
            # Adjust rotation based on LengthIdx
            if model_data.iloc[0]["LengthIdx"] == 0:
                rotation = (rotation + 90) % 360
            
            feature_data.append({
                "length": model_length,
                "width": model_width,
                "height": model_height,
                "rotation": rotation,
                "x": x_distance,
                "y": y_distance,
                "z": z_height,
                "idx": i,
                "name": model_data.iloc[0]["FeatureName"],
                "type": "bms"
            })
            
            # Update bounds
            x_min = min(x_min, x_distance - model_width/2, x_distance + model_width/2)
            x_max = max(x_max, x_distance - model_width/2, x_distance + model_width/2)
            y_min = min(y_min, y_distance - model_length/2, y_distance + model_length/2)
            y_max = max(y_max, y_distance - model_length/2, y_distance + model_length/2)
            z_max = max(z_max, model_height)
    
    # Apply padding to bounds
    x_range = x_max - x_min
    y_range = y_max - y_min
    padding = max(x_range, y_range) * 0.15
    
    x_min -= padding
    x_max += padding
    y_min -= padding
    y_max += padding
    z_max *= 1.1  # Add 10% to height
    
    # Create subplots based on plot_option
    if plot_option == "Both":
        # Create side-by-side view only (no combined view)
        gs = MatPlt.GridSpec(1, 2)
        ax1 = fig.add_subplot(gs[0, 0], projection='3d')  # GeoJSON only
        ax2 = fig.add_subplot(gs[0, 1], projection='3d')  # BMS only
        axes = [ax1, ax2]
        titles = ["3D Selected Buildings from JSON", "3D Feature Entries from BMS"]
    else:
        # Create a single subplot
        ax = fig.add_subplot(111, projection='3d')
        axes = [ax]
        titles = ["3D Selected Buildings from JSON" if plot_option == "JSON_BondingBox" else "3D Feature Entries from BMS"]
    
    # Function to create a building with proper color and style
    def create_building_3d(ax, building, alpha=0.6, color='blue', wireframe=False):
        length = building["length"]
        width = building["width"]
        height = building["height"]
        rotation = building["rotation"]
        x_distance = building["x"]
        y_distance = building["y"]
        z_distance = building.get("z", 0)
        
        # Create corner points for the building (bottom and top)
        corner_points = np.array([
            [-width / 2, -length / 2, 0],
            [width / 2, -length / 2, 0],
            [width / 2, length / 2, 0],
            [-width / 2, length / 2, 0],
            [-width / 2, -length / 2, height],
            [width / 2, -length / 2, height],
            [width / 2, length / 2, height],
            [-width / 2, length / 2, height],
        ])
        
        # Apply rotation
        rotation_matrix = np.array([
            [np.cos(np.radians(rotation)), -np.sin(np.radians(rotation)), 0],
            [np.sin(np.radians(rotation)), np.cos(np.radians(rotation)), 0],
            [0, 0, 1],
        ])
        rotated_points = np.dot(corner_points, rotation_matrix.T)
        
        # Translate the points
        translated_points = rotated_points + [y_distance, x_distance, z_distance]
        
        # Define the faces of the building
        faces = [
            [translated_points[i] for i in [0, 1, 5, 4]],  # Front face
            [translated_points[i] for i in [1, 2, 6, 5]],  # Right face
            [translated_points[i] for i in [2, 3, 7, 6]],  # Back face
            [translated_points[i] for i in [3, 0, 4, 7]],  # Left face
            [translated_points[i] for i in [0, 1, 2, 3]],  # Bottom face
            [translated_points[i] for i in [4, 5, 6, 7]],  # Top face
        ]
        
        # Determine color based on height if not specified
        if color == 'auto':
            import matplotlib.cm as cm
            norm_height = building["height"] / z_max if z_max > 0 else 0.5
            color = cm.viridis(norm_height)
        
        # Draw each face with proper coloring
        for face in faces:
            face_array = np.array(face)
            z_values = np.array([face_array[:, 2]])
            verts = [list(zip(face_array[:, 0], face_array[:, 1], z_values[0]))]
            
            # Add the polygon to the plot
            poly = Poly3DCollection(
                verts,
                facecolors=color,
                linewidths=1.5 if wireframe else 0.5,
                edgecolors='k',
                alpha=alpha
            )
            ax.add_collection3d(poly)
        
        # Draw building shadow on the ground
        if not wireframe:
            ground_shadow = np.array([
                [translated_points[i][0], translated_points[i][1], 0] for i in range(4)
            ])
            shadow_verts = [list(zip(ground_shadow[:, 0], ground_shadow[:, 1], ground_shadow[:, 2]))]
            shadow = Poly3DCollection(
                shadow_verts,
                facecolors='gray',
                linewidths=0,
                alpha=0.15
            )
            ax.add_collection3d(shadow)
        
        return translated_points
    
    # Create ground plane function
    def create_ground_plane(ax, x_min, x_max, y_min, y_max):
        # Create a grid for the ground plane
        x_grid, y_grid = np.meshgrid(
            np.linspace(x_min, x_max, 20),
            np.linspace(y_min, y_max, 20)
        )
        z_grid = np.zeros_like(x_grid)
        
        # Plot the ground plane
        ax.plot_surface(
            y_grid, x_grid, z_grid,
            color='lightgray',
            alpha=0.2,
            antialiased=True,
            shade=False
        )
        
        # Add grid lines
        grid_alpha = 0.1
        grid_spacing = min(x_max - x_min, y_max - y_min) / 10
        
        for x in np.arange(x_min, x_max, grid_spacing):
            ax.plot([y_min, y_max], [x, x], [0, 0], 'k-', alpha=grid_alpha)
            
        for y in np.arange(y_min, y_max, grid_spacing):
            ax.plot([y, y], [x_min, x_max], [0, 0], 'k-', alpha=grid_alpha)
    
    # Setup and draw each axis
    for idx, ax in enumerate(axes):
        # Common axis settings
        ax.set_xlabel('X [feet]')
        ax.set_ylabel('Y [feet]')
        ax.set_zlabel('Z [feet]')
        ax.set_title(titles[idx])
        
        # Set consistent axis limits
        ax.set_xlim([y_min, y_max])  # X and Y are flipped in the 3D view
        ax.set_ylim([x_min, x_max])
        ax.set_zlim([0, z_max * 1.2])
        
        # Set optimal viewing angle
        ax.view_init(elev=30, azim=225)
        
        # Add ground plane
        create_ground_plane(ax, x_min, x_max, y_min, y_max)
        
        # Draw the appropriate content based on plot_option and current axis
        if plot_option == "Both":
            if idx == 0 and building_data:
                # Draw GeoJSON buildings only
                for building in building_data:
                    create_building_3d(ax, building, alpha=0.8, color='blue')
                    
            elif idx == 1 and feature_data:
                # Draw BMS features only
                for feature in feature_data:
                    create_building_3d(ax, feature, alpha=0.8, color='red')
        else:
            # Single view
            if plot_option == "JSON_BondingBox" and building_data:
                for building in building_data:
                    create_building_3d(ax, building, alpha=0.8, color='blue')
                    
            elif plot_option == "BMS_Fitting" and feature_data:
                for feature in feature_data:
                    create_building_3d(ax, feature, alpha=0.8, color='red')
        
        # Add a scale indicator on the main axis
        if idx == len(axes) - 1:  # Last axis
            # Horizontal scale indicator
            scale_length = 100  # 100 feet scale
            scale_x = x_min + (x_max - x_min) * 0.1
            scale_y = y_min + (y_max - y_min) * 0.1
            
            # Draw the scale bar
            ax.plot([scale_y, scale_y], [scale_x, scale_x + scale_length], [0, 0], 'k-', linewidth=2)
            
            # Add text label
            ax.text(scale_y, scale_x + scale_length/2, 5, f"{scale_length} feet", 
                   ha='center', va='bottom', size=8, zdir=None,
                   bbox=dict(facecolor='white', alpha=0.7, boxstyle='round,pad=0.2'))
            
            # Add a height indicator
            height_x = x_min + (x_max - x_min) * 0.1
            height_y = y_min + (y_max - y_min) * 0.9
            height_z = 100  # 100 feet height indicator
            
            # Draw the height indicator
            ax.plot([height_y, height_y], [height_x, height_x], [0, height_z], 'k-', linewidth=2)
            
            # Add text label
            ax.text(height_y, height_x, height_z/2, f"{height_z} feet", 
                   ha='left', va='center', size=8, zdir=None,
                   bbox=dict(facecolor='white', alpha=0.7, boxstyle='round,pad=0.2'))
    
    # Adjust layout
    fig.tight_layout()
    MatPlt.show()
    
    return axes


def filter_structures(
    Geo_Data, Raw_Geo_Data, Num_Of_Structures, selection_option="Total Size"
):
    """
    Selects a subset of structures from a given dataframe based on a probabilistic algorithm.

    Parameters:
    - Geo_Data (pandas.DataFrame): Input dataframe containing information about Geodata.
    - Raw_Geo_Data(pandas.DataFrame): Input dataframe containing information about Raw Geodata.
    - Num_Of_Structures: Amount of structures to select
    - selection_option (str): Selection criteria for the structures. Options include 'size', 'closer', 'both', 'random'.

    Selection Options:
    - 'Height': Probability is increased based on the dot's size (Only Height).
    - 'Area': Probability is increased based on the dot's size (Only Area).
    - 'Total Size': Probability is increased based on the dot's size (height and total size).
    - 'Centerness': Probability is increased for structures closer to the center of the cluster.
    - 'Mix': Probability is influenced by both size and distance.
    - 'Random': structures are randomly selected without considering probabilities
    """

    # Extract relevant columns from the dataframe
    data = Geo_Data[
        ["Surface Size (feet^2)", "Height (feet)", "XXX Cords", "YYY Cords"]
    ].values
    # Calculate the selection criteria
    if selection_option == "Height":
        # Sort based on height
        selection_criteria = Geo_Data["Height (feet)"]
    elif selection_option == "Area":
        # Sort based on area
        selection_criteria = Geo_Data["Surface Size (feet^2)"]
    elif selection_option == "Total Size":
        # Sort based on height and total size
        selection_criteria = (
            Geo_Data["Height (feet)"] * Geo_Data["Surface Size (feet^2)"]
        )

    elif selection_option == "Centerness":
        # Sort based on distance from the center of the cluster
        mean = np.mean(data[:, 2:], axis=0)
        distances = np.linalg.norm(data[:, 2:] - mean, axis=1)
        selection_criteria = 1 / (1 + distances)

    elif selection_option == "Mix":
        # Sort based on both size and distance
        mean = np.mean(data[:, 2:], axis=0)
        distances = np.linalg.norm(data[:, 2:] - mean, axis=1)
        selection_criteria = (1 / (1 + distances)) * (
            Geo_Data["Height (feet)"] * Geo_Data["Surface Size (feet^2)"]
        )

    elif selection_option == "Random":
        # Randomly shuffle the indices
        selection_criteria = np.random.rand(len(Geo_Data))

    # Sort the data based on the selection criteria
    sorted_indices = np.argsort(selection_criteria)

    # Select the top amount of structures with the highest selection criteria
    Num_Of_Structures = min(
        Num_Of_Structures, len(Geo_Data), 256
    )  # Limit to dataframe size
    selected_indices = sorted_indices[-Num_Of_Structures:]

    # Return a new dataframe with the selected structures
    return Raw_Geo_Data.iloc[selected_indices], Geo_Data.iloc[selected_indices]


def Decision_Algo(
    GeoFeature,
    GeoFeatureData,
    Geo_Idx,
    selected_BMSModels,
    floor_height,
    State,
    num_floors=0,
):
    """
    Find the most appropriate BMS model based on the given criteria.

    Args:
        GeoFeature (pd.DataFrame): Geographic features of structures.
        GeoFeatureData (np.array): Additional data for geographic features.
        Geo_Idx (int): Index of the current geographic feature.
        selected_BMSModels (pd.DataFrame): Available BMS models.
        floor_height (float): Height of each floor.
        State (str): Dimension state, either "3D" or "2D".
        num_floors (float): Average number of floors to add. Default is 0.

    Returns:
        tuple: Index of the most appropriate model and its distance.
    """
    SingleStructure = GeoFeature.iloc[Geo_Idx]

    # Prepare structure dimensions
    structure_dims = [SingleStructure["width"], SingleStructure["length"]]

    if State == "3D":
        # Include Height in the distance calculation
        SingleStructure_Height = GeoFeatureData[Geo_Idx, 1]

        if num_floors > 0:
            # Generate a random number of floors from a Gaussian distribution
            additional_floors = max(0, np.random.normal(num_floors, num_floors / 2))
            # Calculate additional height and add it to the original height
            SingleStructure_Height += np.abs(additional_floors * floor_height)
        structure_dims.append(SingleStructure_Height)

    # Prepare model dimensions
    model_dims = selected_BMSModels[["Width", "Length"]]
    if State == "3D":
        model_dims = model_dims.join(selected_BMSModels["Height"])

    # Calculate distances
    distances = cdist([structure_dims], model_dims.values, metric="euclidean")

    # Find the index of the minimum distance
    corrent_model_idx = np.argmin(distances)
    closest_distance = np.min(distances)

    return corrent_model_idx, closest_distance


def Rotation_Definer(Angle, BMS_Length_idx):
    """Through the knowledge of the longest side of the model, assign fixed angle for rotation
    Idx == 0 (X is the longest)/ 1 (Y is the longest)
    
    For consistent rotation:
    - GeoData buildings are rotated (rotation + 90) % 360 in visualization
    - If LengthIdx is 1 (Y-aligned), add 90 degrees to align with X-axis
    - If LengthIdx is 0 (X-aligned), keep the original angle
    """
    if BMS_Length_idx == 1:
        # Feature is Y-aligned (longer in Y-axis), add 90 degrees
        Angle_y_algned = (Angle + 90) % 360
        return Angle_y_algned
    elif BMS_Length_idx == 0:
        # Feature is X-aligned (longer in X-axis), use original angle
        return Angle


def Assign_features_randomly(num_features, radius, DB_path, DB_restrictions):
    # Load the database file containing the features data (mydatabase.db)
    AllBMSModels = Load_Db(DB_path, DB_restrictions)  # Options ModelNum, Name, Type

    if len(AllBMSModels) == 0:
        return TypeError

    np.random.seed(int(time.time()))
    # Randomly select features
    selected_indices = np.random.choice(len(AllBMSModels), num_features, replace=True)
    selected_data = AllBMSModels.iloc[selected_indices]

    # Generate random coordinates within the specified radius
    angles = np.random.uniform(0, 2 * np.pi, num_features)
    distances = np.random.uniform(0, radius, num_features)
    x_coordinates = distances * np.cos(angles)
    y_coordinates = distances * np.sin(angles)

    return selected_data, x_coordinates, y_coordinates


def Save_random_features(
    SaveType,
    num_features,
    selected_data,
    x_coordinates,
    y_coordinates,
    output_file_path,
    BuildingGeneratorVer,
    Presence_f,
    Values_f,
    Presence_i,
    Values_i,
    sort_option,
    CT_Num=None,
    Obj_Num=None,
):
    feature_entries = []
    feature_types = []

    # Iterate through each feature to be generated
    for i, (x, y) in enumerate(zip(x_coordinates, y_coordinates)):
        # Extract data for the current feature
        ct_number = selected_data.iloc[i]["CTNumber"]
        feature_name = selected_data.iloc[i]["FeatureName"]
        feature_type = selected_data.iloc[i]["Type"]

        # Set coordinates and height
        x_distance = x
        y_distance = y
        z_height = 0

        # Generate random rotation
        rotation = np.random.uniform(0, 360)

        # Generate random value and presence based on input parameters
        value = get_value(Values_i, Values_f, feature_type)
        presence = (
            np.random.uniform(Presence_i, Presence_f)
            if Presence_i is not None
            else Presence_f
        )

        formatted_entry = format_entry(
            ct_number,
            y_distance,
            x_distance,
            rotation,
            value,
            presence,
            i,
            feature_name,
        )
        feature_entries.append(formatted_entry)
        feature_types.append(feature_type)

        # After creating all feature_entries, sort them if needed
        if sort_option != "None":
            feature_entries = sort_feature_entries(feature_entries, sort_option)

    # Write the formatted data to a file in the Falcon BMS format
    success, entries = write_to_file(
        output_file_path, BuildingGeneratorVer, [0, 0], num_features, feature_entries
    )

    # Update statistics with the new features
    if success:
        update_statistics(num_features, feature_types)

    return feature_entries


def Assign_features_accuratly(
    num_features,
    DB_path,
    DB_restrictions,
    fillter_option,
    GeoFeatures,
    CalcData_GeoFeatures,
):
    """the Function fillter features according to critirias :
    input::
    num_features = number of features to generate
    DB_path = the path to the DB which the software have been processed
    DB_restriction_type = 'ModelNum'\'Type'\'Name
    DB_restrictions = the restrictions in a string
    fillter_option = Will select the method of filltering the real buildings (default = based on centerness and height)
    GeoFeatures, CalcData_GeoFeatures = Geo data from Load_DB function
    output::
    AllBMSModels - filltered BMS models through the restrictions
    Selected_GeoFeatures - filltered Geo structures
    Selected_CalcData_GeoFeatures - corrolated data of Geo structures to Selected_GeoFeatures
    """

    # Load the database file containing the features data (mydatabase.db)
    AllBMSModels = Load_Db(DB_path, DB_restrictions)  # Options ModelNum, Name, Type

    if len(AllBMSModels) == 0:
        return TypeError

    # Apply Structure selection algorithm through preferences -                     "size", "closer", "both", "random"
    Selected_GeoFeatures, Selected_CalcData_GeoFeatures = filter_structures(
        pd.DataFrame(CalcData_GeoFeatures),
        pd.DataFrame(GeoFeatures),
        num_features,
        fillter_option,
    )
    Selected_CalcData_GeoFeatures = np.array(Selected_CalcData_GeoFeatures)

    return AllBMSModels, Selected_GeoFeatures, Selected_CalcData_GeoFeatures


def Save_accurate_features(
    SaveType,
    num_features,
    Selected_GeoFeatures,
    Selected_CalcData_GeoFeatures,
    Db_path,
    AllBMSModels,
    selection_option,
    SavePath,
    AOI_center,
    Presence_f,
    Values_f,
    Presence_i,
    Values_i,
    auto_features_detection,
    BuildingGeneratorVer,
    sort_option,
    floor_height,
    num_floors,
    CT_Num=None,
    Obj_Num=None,
):
    # Seed the random number generator for reproducibility
    np.random.seed(int(time.time()))

    #  initialize lists
    feature_entries = []
    feature_types = []

    # Iterate through each selected geographic feature
    for select in range(len(Selected_GeoFeatures)):
        # Auto-select BMS models if enabled
        Auto_BMSModels = (
            Auto_Selected(Db_path, Selected_GeoFeatures.iloc[select])
            if auto_features_detection
            else None
        )
        Models = Auto_BMSModels if Auto_BMSModels is not None else AllBMSModels

        # Use Decision_Algo to find the best model
        corrent_model_idx, closest_distance = Decision_Algo(
            Selected_GeoFeatures,
            Selected_CalcData_GeoFeatures,
            select,
            Models,
            floor_height,
            selection_option,
            num_floors,
        )

        # Extract model information
        model = Models.iloc[corrent_model_idx]
        ct_number, feature_name = model["CTNumber"], model["FeatureName"]
        
        # Apply Rotation_Definer to handle rotation based on LengthIdx
        # - If LengthIdx=1 (Y-aligned), adds 90 degrees to align with X-axis
        # - If LengthIdx=0 (X-aligned), keeps original angle
        # This ensures consistent rotation between feature generation and visualization
        rotation = Rotation_Definer(
            Selected_GeoFeatures.iloc[select]["rotation"], model["LengthIdx"]
        )

        # Calculate offset and distances
        r_offset = np.sqrt(model["LengthOff"] ** 2 + model["WidthOff"] ** 2)
        x_distance = Selected_CalcData_GeoFeatures[select, 5] - r_offset * np.sin(
            np.radians(rotation)
        )
        y_distance = Selected_CalcData_GeoFeatures[select, 6] - r_offset * np.cos(
            np.radians(rotation)
        )

        # Get value and presence
        value = get_value(Values_i, Values_f, model["Type"])
        presence = (
            np.random.uniform(Presence_i, Presence_f)
            if Presence_i is not None
            else Presence_f
        )

        # Format and append the entry
        formatted_entry = format_entry(
            ct_number,
            y_distance,
            x_distance,
            rotation,
            value,
            presence,
            select,
            feature_name,
        )
        feature_entries.append(formatted_entry)
        feature_types.append(model["Type"])

    # Sort feature entries if required
    if sort_option != "None":
        feature_entries = sort_feature_entries(feature_entries, sort_option)

    # Write features to file
    success, entries = write_to_file(
        SavePath, BuildingGeneratorVer, AOI_center, num_features, feature_entries
    )

    # Update statistics only if save was successful
    if success:
        update_statistics(num_features, feature_types)

    return feature_entries


# Function to get a value based on input parameters and values dictionary
def get_value(Values_i, Values_f, model_type):
    if Values_i is not None and Values_f is not None:
        return np.random.uniform(Values_i, Values_f)
    elif Values_f is not None:
        return Values_f
    else:
        values_dict = load_values_dict()
        return values_dict.get(str(model_type), {"Value": 10})["Value"]


# Function to write feature entries to a file
def write_to_file(SavePath, BuildingGeneratorVer, AOI_center, num_features, feature_entries):
    """Write feature entries to a file with overwrite protection."""
    def do_save(filepath):
        with open(filepath, "w") as output_file:
            output_file.write(
                f"# BMS-BuildingGenerator v{BuildingGeneratorVer} for FalconEditor - Objective Data\n\n"
            )
            output_file.write(
                "# Objective original location in Falcon World (Falcon BMS 4.38 with New Terrain)\n"
            )
            output_file.write(f"# ObjX: {AOI_center[0]} \n# ObjY: {AOI_center[1]}\n\n")
            output_file.write("Version=6\n\n")
            output_file.write(f"# FeatureEntries {num_features}\n\n")
            output_file.write("\n".join(feature_entries))
            output_file.write("\n\n# Point Headers 0\n")
    
    # Use FileManager to handle the save operation
    success, final_path = FileManager.save_with_confirmation(None, SavePath, do_save)
    if not success and final_path is None:
        messagebox.showinfo(
            "Operation Cancelled",
            "The save operation was cancelled by the user. A temporary file has been saved in the generated_tmp folder."
        )
    return success, feature_entries


# Function to format a feature entry string
def format_entry(
    ct_number, y_distance, x_distance, rotation, value, presence, select, feature_name
):
    return (
        f"FeatureEntry={ct_number} {y_distance:.4f} {x_distance:.4f} 0.0000 {rotation:.4f} "
        f"{int(value):04d} 0000 -1 {int(presence)}# {select}) {feature_name}"
    )


# Function to load values dictionary from a JSON file
def load_values_dict():
    filepath = Path(r"ValuesDic.json")
    try:
        with open(filepath, "r") as f:
            values_dict = json.load(f)
        if not values_dict:
            messagebox.showerror(
                "Error",
                "The values dictionary is empty. The procedure will continue with Value == 10.",
            )
            return {"default": {"Value": 10}}
    except Exception:
        messagebox.showerror(
            "Error",
            "The values dictionary is not found. The procedure will continue with Value == 10.",
        )
        return {"default": {"Value": 10}}
    return values_dict


def sort_feature_entries(feature_entries, sort_option):
    """
    Sort the feature entries based on the specified option.

    :param feature_entries: List of feature entry strings
    :param sort_option: String, either "Alphabet" or "Value"
    :return: Sorted list of feature entry strings
    """

    def extract_info(entry):
        parts = entry.split()
        ct_number = int(
            parts[0].split("=")[1]
        )  # Extract the number after 'FeatureEntry='
        value = int(parts[5])
        name_part = " ".join(parts[8:])  # Join all parts after the 8th element
        _, name = name_part.split(")", 1)
        name = name.strip()
        return ct_number, value, name

    if sort_option == "Alphabet":
        sorted_entries = sorted(
            feature_entries, key=lambda x: extract_info(x)[2].lower()
        )
    elif sort_option == "Value":
        sorted_entries = sorted(
            feature_entries,
            key=lambda x: (-extract_info(x)[1], extract_info(x)[2].lower()),
        )
    else:
        return feature_entries  # No sorting if option is invalid

    # Renumber the sorted entries
    for i, entry in enumerate(sorted_entries):
        parts = entry.split()
        name_part = " ".join(parts[8:])
        presence_idx, name = name_part.split(")", 1)
        presence, idx = name_part.split(" ", 1)
        new_name = f"{i}) {name.strip()}"
        parts[8:] = [presence, new_name]
        sorted_entries[i] = " ".join(parts)

    return sorted_entries


def save_statistics(stats):
    # Function to save statistics to a gzipped JSON file
    def default(obj):
        if isinstance(obj, Counter):
            return dict(obj)
        elif isinstance(obj, (np.integer, np.int64)):
            return int(obj)
        elif isinstance(obj, (np.floating, float)):
            return float(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        else:
            return obj

    # Convert all keys to strings and ensure all values in feature_types are integers
    stats = {
        str(k): (
            v if k != "feature_types" else {str(fk): int(fv) for fk, fv in v.items()}
        )
        for k, v in stats.items()
    }

    with gzip.open("feature_statistics.json.gz", "wt") as f:
        json.dump(stats, f, default=default)


def update_statistics(num_features, feature_types):
    stats = load_statistics()
    stats["total_features"] += int(num_features)
    stats["total_usage"] += 1

    # Ensure feature_types is a Counter with integer values
    if not isinstance(stats["feature_types"], Counter):
        stats["feature_types"] = Counter(
            {str(k): int(v) for k, v in stats["feature_types"].items()}
        )

    # Update feature types, converting all keys to strings and values to integers
    feature_type_counts = Counter({str(ft): 1 for ft in feature_types})
    stats["feature_types"].update(feature_type_counts)

    # Ensure all values in feature_types are integers
    stats["feature_types"] = Counter(
        {k: int(v) for k, v in stats["feature_types"].items()}
    )

    save_statistics(stats)


def load_statistics():
    # Function to load statistics from a gzipped JSON file
    try:
        with gzip.open("feature_statistics.json.gz", "rt") as f:
            stats = json.load(f)

        # Ensure feature_types is a Counter with integer values
        stats["feature_types"] = Counter(
            {str(k): int(v) for k, v in stats["feature_types"].items()}
        )

        return stats
    except (FileNotFoundError, json.JSONDecodeError):
        return {"total_features": 0, "total_usage": 0, "feature_types": Counter()}


def Auto_Selected(Db_path, Selected_GeoFeature):
    """The function detects possible keys in the GeoFeature and loading a proper Models from the Database for better type fitting"""
    fillters = []

    if Selected_GeoFeature["bms"]:
        Accurate_filltered_BMSmodels = Load_Db(Db_path, str(Selected_GeoFeature["bms"]))
        if not Accurate_filltered_BMSmodels.empty:
            return Accurate_filltered_BMSmodels

    stadium = ["stadium", "ice_rink", "sports_centre", "sports_hall"]
    if (Selected_GeoFeature["leisure"] and any(s in split_string(Selected_GeoFeature["leisure"]) for s in stadium)) or Selected_GeoFeature["sport"]:
        fillters.extend(["66", "sport"])

    if Selected_GeoFeature["religion"]:
        religion_terms = split_string(Selected_GeoFeature["religion"])
        if "muslim" in religion_terms:
            fillters.extend(["minaret", "mosque"])
        elif "jewish" in religion_terms:
            fillters.extend(["synagogue"])
        elif "christian" in religion_terms:
            fillters.extend(["church", "presbytery", "cathedral", "chapel"])
        elif "buddhist" in religion_terms or "shinto" in religion_terms:
            fillters.extend(["temple", "shrine", "monastery"])
        else:
            fillters.extend(["7", "40"])

    if Selected_GeoFeature["building"]:
        building_terms = split_string(Selected_GeoFeature["building"])
        if "hangar" in building_terms:
            fillters.extend(["has", "hangar", "ft shelter"])
        elif any(term in building_terms for term in ["mosque", "minaret", "muslim"]):
            fillters.extend(["minaret", "mosque"])
        if any(term in building_terms for term in ["cathedral", "chapel", "presbytery"]):
            fillters.extend(["church", "presbytery", "cathedral", "chapel", "monastery"])
        if "warehouse" in building_terms:
            fillters.extend(["12", "warehouse"])
        if "synagogue" in building_terms:
            fillters.extend(["synagogue"])
        if "shrine" in building_terms:
            fillters.extend(["shrine"])
        if "temple" in building_terms:
            fillters.extend(["temple", "monastery"])

    if Selected_GeoFeature["aeroway"]:
        aeroway_terms = split_string(Selected_GeoFeature["aeroway"])
        heli = ["heliport", "helipad"]
        if "terminal" in aeroway_terms:
            fillters.extend(["terminal"])
        if "apron" in aeroway_terms:
            fillters.extend(["39", "45", "hangar", "terminal", "depot", "warehouse"])
        if any(term in aeroway_terms for term in heli):
            fillters.extend(["helipad", "13"])
        elif "windsock" in aeroway_terms:
            fillters.extend(["windsock"])
        elif "arresting_gear" in aeroway_terms:
            fillters.extend(["68"])
        elif "navigationaid" in aeroway_terms:
            fillters.extend(["25", "localizer", "tacan", "beacon"])
        elif "tower" in aeroway_terms:
            fillters.extend(["2"])

    if Selected_GeoFeature["barrier"]:
        barrier_terms = split_string(Selected_GeoFeature["barrier"])
        if "border_control" in barrier_terms:
            fillters.extend(["55"])
        if "fence" in barrier_terms:
            fillters.extend(["49"])

    if Selected_GeoFeature["man_made"]:
        man_made_terms = split_string(Selected_GeoFeature["man_made"])
        fire_poles = ["flare", "chimney"]
        if "beacon" in man_made_terms:
            fillters.extend(["beacon"])
        elif any(term in man_made_terms for term in fire_poles):
            fillters.extend(["61", "51", "release value"])
        elif "lighting" in man_made_terms:
            fillters.extend(["46", "lights", "light"])

    if Selected_GeoFeature["tower"]:
        tower_terms = split_string(Selected_GeoFeature["tower"])
        watch_tower = ["watchtower", "observation"]
        antennas = ["monitoring", "communication", "na"]
        if any(term in tower_terms for term in watch_tower):
            fillters.extend(["watchtower"])
        if any(term in tower_terms for term in antennas):
            fillters.extend(["radio tower", "telecom tower"])
        if "lighting" in tower_terms:
            fillters.extend(["46", "lights", "light"])
        if "minaret" in tower_terms:
            fillters.extend(["minaret", "mosque"])
        if "radar" in tower_terms:
            fillters.extend(["radar"])
        if "control" in tower_terms or "traffic" in tower_terms:
            fillters.extend(["2"])
    elif Selected_GeoFeature["man_made"]:
        man_made_terms = split_string(Selected_GeoFeature["man_made"])
        antennas = ["communications_tower", "antenna", "satellite_dish", "telescope"]
        if "tower" in man_made_terms:
            if Selected_GeoFeature["service"] and "aircraft_control" in split_string(Selected_GeoFeature["service"]):
                fillters.extend(["2"])
            else:
                fillters.extend(["61", "tower"])
        if "cooling_tower" in man_made_terms:
            fillters.extend(["53"])
        if any(term in man_made_terms for term in antennas):
            fillters.extend(["29", "43", "antenna", "33", "28", "satellite"])
        if "communications_tower" in man_made_terms:
            fillters.extend(["radio tower", "telecom tower"])

    if Selected_GeoFeature["power"]:
        power_terms = split_string(Selected_GeoFeature["power"])
        power = ["compensator", "plant", "substation", "busbar"]
        electric_tower = ["tower", "terminal", "connection"]
        if any(term in power_terms for term in power):
            fillters.extend(["23", "converter", "32", "processor","Generator", "Forge"])
        if any(term in power_terms for term in electric_tower):
            fillters.extend(["20"])
        if "converter" in power_terms:
            fillters.extend(["converter"])
        if "transformer" in power_terms:
            fillters.extend(["transformer"])
        if "heliostat" in power_terms:
            fillters.extend(["Solar Mirrors"])

    if (Selected_GeoFeature["man_made"] and any(term in split_string(Selected_GeoFeature["man_made"]) for term in ["pump", "pumping_station", "works"])) or \
       (Selected_GeoFeature["building"] and "industrial" in split_string(Selected_GeoFeature["building"])):
        fillters.extend(["32", "53", "60", "56", "23", "6"])

    if Selected_GeoFeature["man_made"] and "pipeline" in split_string(Selected_GeoFeature["man_made"]):
        fillters.extend(["piping"])

    if (Selected_GeoFeature["building"] and any(term in split_string(Selected_GeoFeature["building"]) for term in ["gasometer", "storage_tank", "fuel", "tank"])) or \
       (Selected_GeoFeature["man_made"] and any(term in split_string(Selected_GeoFeature["man_made"]) for term in ["gasometer", "storage_tank", "fuel", "tank"])):
        fillters.extend(["48", "fuel", "gas"])

    if (Selected_GeoFeature["building"] and "silo" in split_string(Selected_GeoFeature["building"])) or \
       (Selected_GeoFeature["man_made"] and "silo" in split_string(Selected_GeoFeature["man_made"])):
        fillters.extend(["silo"])

    if (Selected_GeoFeature["building"] and "water_tower" in split_string(Selected_GeoFeature["building"])) or \
       (Selected_GeoFeature["man_made"] and "water_tower" in split_string(Selected_GeoFeature["man_made"])):
        fillters.extend(["37"])

    if (Selected_GeoFeature["building"] and any(term in split_string(Selected_GeoFeature["building"]) for term in ["bridge", "bridges"])) or \
       (Selected_GeoFeature["man_made"] and any(term in split_string(Selected_GeoFeature["man_made"]) for term in ["bridge", "bridges"])) or \
       Selected_GeoFeature["bridge"]:
        fillters.extend(["16"])

    if (Selected_GeoFeature["building"] and "hospital" in split_string(Selected_GeoFeature["building"])) or \
       (Selected_GeoFeature["amenity"] and "hospital" in split_string(Selected_GeoFeature["amenity"])):
        fillters.extend(["62"])

    if (Selected_GeoFeature["military"] and "bunker" in split_string(Selected_GeoFeature["military"])) or \
       (Selected_GeoFeature["building"] and "bunker" in split_string(Selected_GeoFeature["building"])):
        fillters.extend(["4", "bunker"])

    barracks = ["barrack", "barracks"]
    if (Selected_GeoFeature["building"] and any(term in split_string(Selected_GeoFeature["building"]) for term in barracks)) or \
       (Selected_GeoFeature["military"] and any(term in split_string(Selected_GeoFeature["military"]) for term in barracks)):
        fillters.extend(["12", "35", "10"])

    if Selected_GeoFeature["military"] and any(term in split_string(Selected_GeoFeature["military"]) for term in ["ammo", "ammunition", "munition"]):
        fillters.extend(["ammo", "ammunition", "munition", "bunker"])

    filters_str = ", ".join(fillters)
    if filters_str != "":
        Accurate_filltered_BMSmodels = Load_Db(Db_path, filters_str)
        return Accurate_filltered_BMSmodels
    else:
        return None

def split_string(s):
    """Split a string by multiple delimiters and return a list of lowercase terms"""
    return [term.strip().lower() for term in re.split(r'[,\s/\\.]', s) if term.strip()]
