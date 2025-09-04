import re
import time
import gzip
import json
import math
import sqlite3
import traceback
import numpy as np
import pandas as pd
from tkinter import messagebox
from pathlib import Path
import matplotlib.pyplot as MatPlt
from scipy.spatial.distance import cdist
from collections import Counter
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
from utils.file_manager import FileManager
from utils.json_path_handler import load_json, save_json, JsonFiles
import os
import logging
logger = logging.getLogger(__name__)


# Load the data from the database
def Load_Db(path, feature_name="All"):
    """Loads Classified DB based on demand
    *feature_name is string, and will have all the information in numbers and strings
    --if all data need to be extracted, place "All, or empty space
    --numbers will be classified as "types" and names would be matched by the actual name
    --if "ModelNum" is present, every number would be extracted from the model number"""

    logger.debug(f"Loading database from path: {path} with feature_name: {feature_name}")
    
    try:
        conn = sqlite3.connect(path)
        logger.debug(f"Successfully connected to database: {path}")
    except Exception as e:
        logger.error(f"Failed to connect to database {path}: {str(e)}")
        raise
    
    # Get all items divided by comma
    Allitems = [item.strip() for item in feature_name.split(",")]

    # Adjust the query based on the feature type
    AllModels = {"", "\n", "All"}

    # convert to sets
    set_Allitems = set(Allitems)
    if set_Allitems.issubset(AllModels) and len(Allitems) == 1:
        query = "SELECT * FROM MyTable"
        logger.debug("Using query for all models")

    elif "ModelNum" in Allitems:
        # get only the numbers inside the
        numbers = [number.strip() for number in Allitems if number.isdigit()]
        # Construct the query to match any of the words in Allitems
        number_conditions = " OR ".join(
            [f"ModelNumber = {number}" for number in numbers]
        )
        # Combine the conditions
        query = f"SELECT * FROM MyTable WHERE {number_conditions}"
        logger.debug(f"Using ModelNum query with {len(numbers)} numbers")

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
            logger.debug(f"Using combined query with {len(words)} words and {len(numbers)} numbers")
        elif word_conditions:
            query = f"SELECT * FROM MyTable WHERE {word_conditions}"
            logger.debug(f"Using word-based query with {len(words)} words")
        elif number_conditions:
            query = f"SELECT * FROM MyTable WHERE {number_conditions}"
            logger.debug(f"Using number-based query with {len(numbers)} numbers")

    try:
        dataframe = pd.read_sql_query(query, conn)
        logger.debug(f"Query executed successfully, retrieved {len(dataframe)} rows")
    except Exception as e:
        logger.error(f"Database query failed: {str(e)}")
        logger.error(f"Query was: {query}")
        conn.close()
        raise
    finally:
        conn.close()

    # get size
    num_rows, num_cols = dataframe.shape
    # Generate random indices to ensure random load of data
    np.random.seed(num_rows)  # To ensure reproducibility
    selected_indices = np.random.choice(num_rows, size=num_rows, replace=False)

    # Get the CT numbers and feature names for the selected indices
    random_dataframe = dataframe.iloc[selected_indices]
    
    logger.info(f"Loaded {num_rows} features from database for feature_name: {feature_name}")
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
            
            # Find model data - match CTNumber exactly to avoid substring collisions (e.g., 88 matching 886)
            ct_series_2d = pd.to_numeric(models_data["CTNumber"], errors="coerce")
            model_data = models_data[ct_series_2d == ct_number]
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
            
            # Find model data - match CTNumber exactly to avoid substring collisions
            ct_series_3d = pd.to_numeric(models_FrameData["CTNumber"], errors="coerce")
            model_data = models_FrameData[ct_series_3d == ct_number]
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
    """Extracts structures from GeoJSON data based on the maximum total size of components.

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
    
    # Log function entry with key parameters
    logging.info(f"Starting structure filtering with selection option: '{selection_option}'")
    logging.info(f"Input data: {len(Geo_Data)} structures, requesting {Num_Of_Structures} structures")
    logging.debug(f"Geo_Data shape: {Geo_Data.shape}, Raw_Geo_Data shape: {Raw_Geo_Data.shape}")

    # Extract relevant columns from the dataframe
    data = Geo_Data[
        ["Surface Size (feet^2)", "Height (feet)", "XXX Cords", "YYY Cords"]
    ].values
    logging.debug(f"Extracted coordinate and size data array with shape: {data.shape}")
    
    # Calculate the selection criteria
    if selection_option == "Height":
        # Sort based on height
        logging.info("Using Height-based selection criteria")
        selection_criteria = Geo_Data["Height (feet)"]
        logging.debug(f"Height range: {selection_criteria.min():.2f} to {selection_criteria.max():.2f} feet")
        
    elif selection_option == "Area":
        # Sort based on area
        logging.info("Using Area-based selection criteria")
        selection_criteria = Geo_Data["Surface Size (feet^2)"]
        logging.debug(f"Area range: {selection_criteria.min():.2f} to {selection_criteria.max():.2f} sq ft")
        
    elif selection_option == "Total Size":
        # Sort based on height and total size
        logging.info("Using Total Size (height × area) selection criteria")
        selection_criteria = (
            Geo_Data["Height (feet)"] * Geo_Data["Surface Size (feet^2)"]
        )
        logging.debug(f"Total size range: {selection_criteria.min():.2f} to {selection_criteria.max():.2f}")

    elif selection_option == "Centerness":
        # Sort based on normal distribution probability from the center of the cluster
        logging.info("Using Normal Distribution-based Centerness selection criteria")
        mean = np.mean(data[:, 2:], axis=0)
        logging.debug(f"Cluster center coordinates: ({mean[0]:.2f}, {mean[1]:.2f})")
        distances = np.linalg.norm(data[:, 2:] - mean, axis=1)
        logging.debug(f"Distance range from center: {distances.min():.2f} to {distances.max():.2f}")
        
        # Calculate sigma as a fraction of the data spread for adaptive scaling
        # Use 75th percentile distance as sigma to capture most of the data distribution
        sigma = np.percentile(distances, 75) if len(distances) > 0 else 1.0
        if sigma == 0:  # Handle edge case where all points are at the center
            sigma = 1.0
        logging.debug(f"Normal distribution sigma (75th percentile): {sigma:.2f}")
        
        # Apply normal distribution: higher probability for closer points, but with gradual falloff
        # Use Gaussian function: exp(-(distance^2)/(2*sigma^2))
        centerness_probabilities = np.exp(-(distances**2) / (2 * sigma**2))
        logging.debug(f"Centerness probabilities range: {centerness_probabilities.min():.4f} to {centerness_probabilities.max():.4f}")
        
        # Add small random component for randomness while preserving distance-based preference
        # Scale random component to be 10% of the probability range
        prob_range = centerness_probabilities.max() - centerness_probabilities.min()
        random_component = np.random.uniform(0, prob_range * 0.1, len(centerness_probabilities))
        selection_criteria = centerness_probabilities + random_component
        logging.debug(f"Final centerness scores (with randomness): {selection_criteria.min():.4f} to {selection_criteria.max():.4f}")
        logging.info(f"Applied normal distribution with σ={sigma:.2f} and 10% randomness component")

    elif selection_option == "Mix":
        # Sort based on both size and normal distribution-based distance
        logging.info("Using Mixed (size + normal distribution centerness) selection criteria")
        mean = np.mean(data[:, 2:], axis=0)
        logging.debug(f"Cluster center coordinates: ({mean[0]:.2f}, {mean[1]:.2f})")
        distances = np.linalg.norm(data[:, 2:] - mean, axis=1)
        logging.debug(f"Distance range from center: {distances.min():.2f} to {distances.max():.2f}")
        
        # Calculate size component
        size_component = Geo_Data["Height (feet)"] * Geo_Data["Surface Size (feet^2)"]
        logging.debug(f"Size component range: {size_component.min():.2f} to {size_component.max():.2f}")
        
        # Calculate enhanced centerness component using normal distribution
        sigma = np.percentile(distances, 75) if len(distances) > 0 else 1.0
        if sigma == 0:  # Handle edge case where all points are at the center
            sigma = 1.0
        logging.debug(f"Normal distribution sigma (75th percentile): {sigma:.2f}")
        
        # Apply normal distribution for centerness
        centerness_probabilities = np.exp(-(distances**2) / (2 * sigma**2))
        logging.debug(f"Centerness probabilities range: {centerness_probabilities.min():.4f} to {centerness_probabilities.max():.4f}")
        
        # Add randomness to centerness component (5% for mix to balance with size)
        prob_range = centerness_probabilities.max() - centerness_probabilities.min()
        random_component = np.random.uniform(0, prob_range * 0.05, len(centerness_probabilities))
        centerness_component = centerness_probabilities + random_component
        
        # Combine size and enhanced centerness
        selection_criteria = centerness_component * size_component
        logging.debug(f"Mixed criteria range: {selection_criteria.min():.2f} to {selection_criteria.max():.2f}")
        logging.info(f"Applied normal distribution with σ={sigma:.2f}, 5% randomness, and size weighting")

    elif selection_option == "Random":
        # Randomly shuffle the indices
        logging.info("Using Random selection criteria")
        selection_criteria = np.random.rand(len(Geo_Data))
        logging.debug(f"Generated {len(selection_criteria)} random values for selection")

    # Sort the data based on the selection criteria
    logging.debug("Sorting structures based on selection criteria")
    sorted_indices = np.argsort(selection_criteria)

    # Select the top amount of structures with the highest selection criteria
    original_request = Num_Of_Structures
    Num_Of_Structures = min(
        Num_Of_Structures, len(Geo_Data), 256
    )  # Limit to dataframe size
    
    if Num_Of_Structures != original_request:
        logging.warning(f"Requested {original_request} structures, but limited to {Num_Of_Structures} (available: {len(Geo_Data)}, max: 256)")
    else:
        logging.info(f"Selecting top {Num_Of_Structures} structures based on criteria")
        
    selected_indices = sorted_indices[-Num_Of_Structures:]
    logging.debug(f"Selected indices range: {selected_indices.min()} to {selected_indices.max()}")

    # Log selection results
    if len(selected_indices) > 0:
        selected_criteria_values = selection_criteria.iloc[selected_indices] if hasattr(selection_criteria, 'iloc') else selection_criteria[selected_indices]
        logging.info(f"Selected {len(selected_indices)} structures with criteria values from {selected_criteria_values.min():.4f} to {selected_criteria_values.max():.4f}")
    else:
        logging.warning("No structures were selected")

    # Return a new dataframe with the selected structures
    filtered_raw = Raw_Geo_Data.iloc[selected_indices]
    filtered_geo = Geo_Data.iloc[selected_indices]
    logging.info(f"Structure filtering completed successfully - returned {len(filtered_raw)} structures")
    
    return filtered_raw, filtered_geo


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


def Assign_features_randomly(num_features, radius, DB_path, DB_restrictions, distribution_type):
    """Assign features randomly with collision detection.
    
    This function assigns features randomly within a specified radius and tries
    to avoid collisions between features by checking bounding boxes.
    
    Args:
        num_features: Number of features to place
        radius: Maximum radius from center (0,0) for placement
        DB_path: Path to the database containing feature data
        DB_restrictions: Restrictions for database query
        distribution_type: Type of distribution to use
        
    Returns:
        Tuple of (selected_data, x_coordinates, y_coordinates)
    """
    logger.info(f"Using distribution type: {distribution_type}")
    # Load the database file containing the features data (mydatabase.db)
    AllBMSModels = Load_Db(DB_path, DB_restrictions)  # Options ModelNum, Name, Type

    if len(AllBMSModels) == 0:
        return TypeError

    np.random.seed(int(time.time()))
    # Randomly select features
    selected_indices = np.random.choice(len(AllBMSModels), num_features, replace=True)
    selected_data = AllBMSModels.iloc[selected_indices]
    
    # Initialize arrays for coordinates
    x_coordinates = np.zeros(num_features)
    y_coordinates = np.zeros(num_features)
    
    # Create a list to store occupied bounding boxes
    # Each bounding box is represented as [x_min, y_min, x_max, y_max]
    occupied_bounding_boxes = []
    
    # Get feature dimensions directly from the database
    # No estimation or default values are used
    def get_feature_dimensions(feature_row):
        # Get actual Width and Length from the database
        if 'Width' not in feature_row or 'Length' not in feature_row:
            # If dimensions are missing, raise an error - no defaults
            error_msg = f"Feature dimensions missing from database for feature {feature_row['FeatureName'] if 'FeatureName' in feature_row else 'unknown'}"
            logger.error(error_msg)
            raise ValueError(error_msg)
            
        width = feature_row['Width']
        length = feature_row['Length']
        
        # Log the actual dimensions
        logger.debug(f"Actual dimensions for feature {feature_row['FeatureName'] if 'FeatureName' in feature_row else 'unknown'}: Width={width}, Length={length}")
        
        return width, length
    
    # Check for collision between a proposed bounding box and existing boxes
    # Returns both a collision boolean and an overlap score (0 = no overlap, higher = more overlap)
    def check_collision_with_score(new_box, existing_boxes):
        # If no existing boxes, no collision
        if not existing_boxes:
            return False, 0.0
        
        # Unpack the coordinates for easier reading
        new_min_x, new_min_y, new_max_x, new_max_y = new_box
        
        # Calculate area of new box
        new_width = new_max_x - new_min_x
        new_height = new_max_y - new_min_y
        new_area = new_width * new_height
        
        # Ensure the box is valid (min < max)
        if new_min_x >= new_max_x or new_min_y >= new_max_y:
            logger.warning(f"Invalid bounding box detected: {new_box}. Treating as collision.")
            return True, float('inf')  # Invalid box - treat as maximum collision
        
        # Variables to track total overlap
        total_overlap_area = 0.0
        max_overlap_ratio = 0.0  # Ratio of overlap compared to box size
        has_collision = False
        
        # Check if the new box overlaps with any existing box
        for idx, box in enumerate(existing_boxes):
            # Validate the existing box
            if len(box) != 4:
                logger.warning(f"Invalid box format at index {idx}: {box}. Skipping.")
                continue
                
            try:
                ex_min_x, ex_min_y, ex_max_x, ex_max_y = box
                
                # Check for non-overlap first (AABB test)
                if (new_min_x > ex_max_x or  # new is to the right of existing
                    new_max_x < ex_min_x or  # new is to the left of existing
                    new_min_y > ex_max_y or  # new is above existing
                    new_max_y < ex_min_y):   # new is below existing
                    # No overlap with this box
                    continue
                
                # If we get here, there's an overlap - calculate its area
                overlap_width = min(new_max_x, ex_max_x) - max(new_min_x, ex_min_x)
                overlap_height = min(new_max_y, ex_max_y) - max(new_min_y, ex_min_y)
                overlap_area = overlap_width * overlap_height
                
                # Skip if overlap is negligible (floating point error)
                if overlap_area < 0.01:
                    continue
                    
                # We have a real collision
                has_collision = True
                total_overlap_area += overlap_area
                
                # Calculate overlap ratio relative to new box area
                overlap_ratio = overlap_area / new_area
                max_overlap_ratio = max(max_overlap_ratio, overlap_ratio)
                
                # Early exit if we have a severe overlap (optimization)
                if max_overlap_ratio > 0.5:
                    return True, max_overlap_ratio
                    
            except Exception as e:
                logger.error(f"Error in collision detection with box {box}: {e}")
                # Be conservative - treat as collision if there's an error
                return True, 1.0
        
        # Additionally, check proximity to other boxes (not just overlap)
        # This helps maintain good spacing between features
        for box in existing_boxes:
            try:
                ex_min_x, ex_min_y, ex_max_x, ex_max_y = box
                
                # Calculate center points
                new_center_x = (new_min_x + new_max_x) / 2
                new_center_y = (new_min_y + new_max_y) / 2
                ex_center_x = (ex_min_x + ex_max_x) / 2
                ex_center_y = (ex_min_y + ex_max_y) / 2
                
                # Distance between centers
                center_distance = np.sqrt((new_center_x - ex_center_x)**2 + (new_center_y - ex_center_y)**2)
                
                # Minimum distance needed for no overlap
                new_radius = max(new_width, new_height) / 2
                ex_radius = max(ex_max_x - ex_min_x, ex_max_y - ex_min_y) / 2
                min_distance = new_radius + ex_radius
                
                # If centers are too close (as a ratio of min_distance)
                proximity_ratio = min_distance / max(center_distance, 0.001) - 1.0
                if proximity_ratio > 0:
                    # Add to the score based on proximity (closer = higher score)
                    max_overlap_ratio = max(max_overlap_ratio, proximity_ratio * 0.5)
                    
                    # If very close, count as collision
                    if proximity_ratio > 0.2:  # Within 20% of minimum distance
                        has_collision = True
            except Exception as e:
                logger.warning(f"Error checking proximity: {e}")
        
        # Return final collision result and score
        return has_collision, max_overlap_ratio
        
    # Legacy collision detection function for backward compatibility
    def check_collision(new_box, existing_boxes):
        collision, _ = check_collision_with_score(new_box, existing_boxes)
        return collision
    
    # Place each feature with collision detection
    for i in range(num_features):
        feature = selected_data.iloc[i]
        
        # Get actual feature dimensions from the database
        width, length = get_feature_dimensions(feature)
        
        # Calculate larger safety buffer based on feature size - larger features need more space
        # Minimum 5 meter buffer, or 25% of the feature's largest dimension, whichever is greater
        min_buffer = 5.0  # Minimum 5-meter buffer around each feature
        size_based_buffer = max(width, length) * 0.25  # 25% of largest dimension
        safety_buffer = max(min_buffer, size_based_buffer)
        
        # Apply buffer for collision detection purposes
        placement_width = width + safety_buffer
        placement_length = length + safety_buffer
        
        # Keep track of placement attempts
        placed = False
        attempts = 0
        max_attempts = 50  # Increase max attempts for better chances of finding valid placement
        
        # Advanced tracking for best fallback position if all attempts fail
        best_position = None
        best_overlap_score = float('inf')  # Lower is better (less overlap)
        
        # For visualization in case of failure
        all_attempted_positions = []
        
        # Placement strategies based on selected distribution type
        while attempts < max_attempts and not placed:
            # Generate coordinates based on distribution type
            if distribution_type == "Normal Distribution":
                # Normal Distribution - more features near the center
                if attempts < 15:
                    # Higher probability near center
                    distance = radius * np.random.normal(0, 0.3)  # Mean 0, SD 0.3 * radius
                    angle = np.random.uniform(0, 2 * np.pi)
                    x = distance * np.cos(angle)
                    y = distance * np.sin(angle)
                elif attempts < 30:
                    # Try with slightly wider distribution
                    distance = radius * np.random.normal(0, 0.5)  # Mean 0, SD 0.5 * radius
                    angle = np.random.uniform(0, 2 * np.pi)
                    x = distance * np.cos(angle)
                    y = distance * np.sin(angle)
                else:
                    # Fallback to spiral search from center
                    t = (attempts - 30) / 20.0  # Parameter for spiral equation
                    spiral_radius = t * radius * 0.9  # Gradually increases radius
                    spiral_angle = t * 10 * np.pi  # Multiple rotations
                    x = spiral_radius * np.cos(spiral_angle)
                    y = spiral_radius * np.sin(spiral_angle)
            
            elif distribution_type == "Peripheral Distribution":
                # Peripheral Distribution - more features toward the edges
                if attempts < 15:
                    # Higher probability near the edge
                    # Use beta distribution skewed towards 1.0 (edge)
                    distance_factor = np.random.beta(2, 1)  # Shape parameters favor values near 1.0
                    distance = radius * (0.4 + 0.6 * distance_factor)  # At least 40% out from center
                    angle = np.random.uniform(0, 2 * np.pi)
                    x = distance * np.cos(angle)
                    y = distance * np.sin(angle)
                elif attempts < 30:
                    # Try with ring pattern
                    angle = np.random.uniform(0, 2 * np.pi)
                    # Create a narrower ring near the edge
                    ring_factor = np.random.uniform(0.7, 0.95)  # 70-95% of radius
                    distance = radius * ring_factor
                    x = distance * np.cos(angle)
                    y = distance * np.sin(angle)
                else:
                    # Fallback to quadrant-based placement
                    quadrant = attempts % 4  # 0: NE, 1: SE, 2: SW, 3: NW
                    base_angle = (quadrant * np.pi/2) + np.random.uniform(-np.pi/4, np.pi/4)
                    distance = radius * (0.7 + 0.3 * np.random.random())  # 70-100% of radius
                    x = distance * np.cos(base_angle)
                    y = distance * np.sin(base_angle)
            
            else:  # "Uniform Distribution"
                # Uniform Distribution - equal probability across the entire area
                if attempts < 15:
                    # Pure uniform distribution
                    distance = radius * np.sqrt(np.random.random())  # Square root for uniform density
                    angle = np.random.uniform(0, 2 * np.pi)
                    x = distance * np.cos(angle)
                    y = distance * np.sin(angle)
                elif attempts < 30:
                    # Grid-based placement with jitter
                    grid_cells = 6  # 6x6 grid
                    grid_x = ((attempts - 15) % grid_cells) - (grid_cells/2 - 0.5)
                    grid_y = ((attempts - 15) // grid_cells) - (grid_cells/2 - 0.5)
                    # Normalize to radius and add jitter
                    grid_scale = radius / (grid_cells/2)
                    jitter = grid_scale * 0.3 * np.random.random()
                    jitter_angle = np.random.uniform(0, 2 * np.pi)
                    x = grid_x * grid_scale + jitter * np.cos(jitter_angle)
                    y = grid_y * grid_scale + jitter * np.sin(jitter_angle)
                else:
                    # Fallback to systematic spiral coverage
                    t = (attempts - 30) / 20.0  # Parameter for spiral equation
                    # More even spiral with consistent spacing
                    spiral_radius = radius * np.sqrt(t)  # Square root for uniform density
                    spiral_angle = t * 15 * np.pi  # More rotations for better coverage
                    x = spiral_radius * np.cos(spiral_angle)
                    y = spiral_radius * np.sin(spiral_angle)
            
            # Store attempted position for visualization
            all_attempted_positions.append((x, y))
            
            # Calculate bounding box with the feature at the center
            half_width = placement_width / 2
            half_length = placement_length / 2
            new_box = [x - half_width, y - half_length, x + half_width, y + half_length]
            
            # Check for boundary constraint - keep fully within radius if possible
            corner_distances = [
                np.sqrt((x - half_width)**2 + (y - half_length)**2),  # bottom-left
                np.sqrt((x - half_width)**2 + (y + half_length)**2),  # top-left
                np.sqrt((x + half_width)**2 + (y - half_length)**2),  # bottom-right
                np.sqrt((x + half_width)**2 + (y + half_length)**2)   # top-right
            ]
            max_corner_distance = max(corner_distances)
            
            # Only consider positions where feature is fully within radius
            # But relax this constraint in later attempts
            within_radius = max_corner_distance <= radius or attempts >= 30
            
            # Check if this position collides with existing features
            collision, overlap_score = check_collision_with_score(new_box, occupied_bounding_boxes)
            
            # Track best position even if there's collision
            # Lower overlap score is better (less overlap with existing features)
            if within_radius and (best_position is None or overlap_score < best_overlap_score):
                best_position = (x, y, new_box)
                best_overlap_score = overlap_score
            
            if not collision and within_radius:
                # Valid placement found - no collision and within radius
                placed = True
                x_coordinates[i] = x
                y_coordinates[i] = y
                
                # Use the ACTUAL dimensions for the final bounding box (no safety buffer)
                half_width = width / 2
                half_length = length / 2
                final_box = [x - half_width, y - half_length, x + half_width, y + half_length]
                occupied_bounding_boxes.append(final_box)
                
                logger.debug(f"Feature {i} ({feature['FeatureName'] if 'FeatureName' in feature else 'unknown'}) placed at ({x:.2f}, {y:.2f}) without collision (attempt {attempts+1})")
            else:
                # Log collision details for debugging
                if not within_radius:
                    logger.debug(f"Feature {i} attempt {attempts+1}: outside radius boundary at ({x:.2f}, {y:.2f})")
                if collision:
                    logger.debug(f"Feature {i} attempt {attempts+1}: collision detected at ({x:.2f}, {y:.2f}) with score {overlap_score:.2f}")
                
                # Try again
                attempts += 1
        
        # If all attempts failed, use the best position found with overlap warning
        if not placed:
            # We must have a best position by now unless something is wrong
            if best_position is None:
                # If somehow we don't have a best position, use a fallback at the origin with warning
                logger.error(f"CRITICAL: Failed to find any valid position for feature {i} - using origin")
                x, y = 0, 0
                half_width = width / 2
                half_length = length / 2
                final_box = [x - half_width, y - half_length, x + half_width, y + half_length]
            else:
                # Use the best position we found (least overlap)
                x, y, overlap_box = best_position
                x_coordinates[i] = x
                y_coordinates[i] = y
                
                # Use actual dimensions for the final bounding box (no safety buffer)
                half_width = width / 2
                half_length = length / 2
                final_box = [x - half_width, y - half_length, x + half_width, y + half_length]
            
            # Record this box
            occupied_bounding_boxes.append(final_box)
            
            # ALWAYS log warning for failed placements - this is critical!
            failure_msg = f"WARNING: Feature {i} ({feature['FeatureName'] if 'FeatureName' in feature else 'unknown'}) placed with COLLISION at ({x:.2f}, {y:.2f}) after {attempts} failed attempts - overlap score: {best_overlap_score:.2f}"
            logger.warning(failure_msg)  # Log as warning

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
    shared_data_dict,  # Added shared_data_dict parameter
    CT_Num=None,
    Obj_Num=None,
    selection_type="Random Selection"  # Added to control collision detection
):
    # Log only critical information
    logger.info(f"Save_random_features: {SaveType} mode, {num_features} features, selection_type={selection_type}")
    if CT_Num is not None and Obj_Num is not None:
        logger.info(f"BMS Injection: CT={CT_Num}, Obj={Obj_Num}")
        logger.info(f"Collision detection will be {'ENABLED' if selection_type == 'Random Selection' else 'DISABLED'} for {selection_type} mode")
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

    # Check if we're using BMS injection mode
    if SaveType == "BMS" and CT_Num is not None and Obj_Num is not None:
        logger.info("\n===== BMS INJECTION MODE DETECTED =====\n")
        try:
            logger.info("DEBUG: Importing BMS injection modules")
            from bms_injector import BmsInjector
            from pathlib import Path
            import tkinter as tk
            from tkinter import messagebox
            logger.info("DEBUG: Successfully imported BMS injection modules")
            
            # Get BMS path from shared_data_dict CTpath if available
            logger.info("DEBUG: Determining BMS path")
            if shared_data_dict and 'CTpath' in shared_data_dict and shared_data_dict["CTpath"].get():
                bms_path = os.path.dirname(shared_data_dict["CTpath"].get())
                logger.info(f"DEBUG: Using path from shared_data_dict: {bms_path}")
            else:
                # Fall back to SavePath parent directory
                bms_path = Path(output_file_path).parent
                logger.info(f"DEBUG: Using fallback path from output_file_path: {bms_path}")
            
            # Get backup setting from shared_data_dict if available
            backup_bms_files = False  # Default to True for safety
            if shared_data_dict and 'backup_bms_files' in shared_data_dict:
                # Make sure to handle if shared_data_dict['backup_bms_files'] is already a boolean
                backup_setting = shared_data_dict['backup_bms_files']
                if isinstance(backup_setting, tk.StringVar): # Check if it's a Tkinter StringVar
                    backup_value = backup_setting.get()
                    backup_bms_files = backup_value == '1'
                elif isinstance(backup_setting, str): # Check if it's a plain string '0' or '1'
                    backup_bms_files = backup_setting == '1'
                elif isinstance(backup_setting, bool): # Check if it's already a boolean
                    backup_bms_files = backup_setting
                else:
                    logger.warning(f"Unknown type for backup_bms_files in shared_data_dict (Save_accurate_features): {type(backup_setting)}. Defaulting to True.")
                    backup_bms_files = False # Default to true if type is unexpected
                logger.info(f"BMS file backup {'enabled' if backup_bms_files else 'disabled'}")
            else:
                logger.warning("shared_data_dict or 'backup_bms_files' not found in Save_accurate_features. Defaulting to backup_bms_files=False")
            
            # Create BMS injector instance with appropriate backup setting
            injector = BmsInjector(bms_path, backup=backup_bms_files)
            
            # Check if CT is an objective
            is_objective = injector.is_objective_ct(CT_Num)
            objective_exists = injector.objective_exists(Obj_Num)
            
            proceed = True
            
            # Changed warnings to ask for confirmation instead of warning about CT not being an objective
            if not is_objective and objective_exists:
                proceed = messagebox.askyesno(
                    "Confirmation",
                    f"Are you sure you wish to create Objective overlapping CT Number {CT_Num} and Objective Number {Obj_Num}?"
                )
            elif not is_objective:
                proceed = messagebox.askyesno(
                    "Confirmation",
                    f"Are you sure you wish to create Objective for CT Number {CT_Num} and Objective Number {Obj_Num}?"
                )
            elif objective_exists:
                proceed = messagebox.askyesno(
                    "Confirmation",
                    f"Objective {Obj_Num} already exists. Do you want to override it?"
                )
            
            if proceed:
                # Try to load saved settings for this CT/Obj combination
                try:
                    from utils.json_path_handler import load_json, JsonFiles
                    
                    # Create a temporary root window for message boxes
                    root = tk.Tk()
                    root.withdraw()  # Hide the root window
                    
                    # Load saved objective settings
                    saved_settings = load_json(JsonFiles.SAVED_OBJECTIVE_SETTINGS, default={})
                    
                    # Check if we have saved settings for this CT/Obj combination
                    if saved_settings and saved_settings.get("ct_num") == CT_Num and saved_settings.get("obj_num") == Obj_Num:
                        logger.info(f"Found settings for CT:{CT_Num} Obj:{Obj_Num}")
                        obj_type = saved_settings.get("type")
                        name = saved_settings.get("name")
                        reset_pd = saved_settings.get("reset_pd", True)
                        fields = saved_settings.get("fields", {})
                        
                        # Convert field values to appropriate types
                        typed_fields = {}
                        for field_name, value in fields.items():
                            try:
                                if isinstance(value, str) and "." in value:
                                    typed_fields[field_name] = float(value)
                                elif isinstance(value, str) and value.isdigit():
                                    typed_fields[field_name] = int(value)
                                else:
                                    typed_fields[field_name] = value
                            except ValueError:
                                typed_fields[field_name] = value
                                
                        fields = typed_fields
                        logger.info(f"Using saved settings: type={obj_type}, name={name}, reset_pd={reset_pd}")
                    else:
                        logger.error(f"No saved settings found for CT:{CT_Num} Obj:{Obj_Num}")
                        messagebox.showerror(
                            "Missing Configuration",
                            f"No saved settings found for CT:{CT_Num} and Objective:{Obj_Num}.\n\n"
                            f"Please configure this objective first using the BMS Injection window."
                        )
                        root.destroy()
                        return None
                except Exception as e:
                    error_msg = f"Error loading saved settings: {e}"
                    logger.error(error_msg)
                    messagebox.showerror(
                        "Error",
                        f"Failed to load objective settings: {str(e)}\n\n"
                        f"Please reconfigure this objective using the BMS Injection window."
                    )
                    root.destroy()
                    return None
                
                # Clean up the root window
                root.destroy()
                        
                # Update injector with new path if changed
                injector = BmsInjector(bms_path, backup=backup_bms_files)
                
                # Create objective and inject features in one operation
                logger.info("\n===== INJECTING FEATURES INTO BMS =====\n")
                logger.info(f"DEBUG: Calling create_and_inject_objective with {len(feature_entries)} features")
                logger.info(f"DEBUG: Obj_Num = {Obj_Num}, CT_Num = {CT_Num}, name = {name}, obj_type = {obj_type}")
                logger.info(f"DEBUG: Feature entries sample (first 3): {feature_entries[:3] if len(feature_entries) >= 3 else feature_entries}")
                
                try:
                    injection_result = injector.create_and_inject_objective(Obj_Num, CT_Num, name, obj_type, feature_entries, selected_data, fields, reset_pd, selection_type)
                    logger.info(f"DEBUG: Injection result: {injection_result}")
                    
                    # Check if injection was successful (not cancelled or error)
                    if isinstance(injection_result, dict) and injection_result.get("status") == "success":
                        # Success - just update statistics without showing a message
                        # as the calling function will display a success message
                        logger.info("DEBUG: Injection successful, updating statistics")
                        try:
                            update_statistics(num_features, feature_types)
                            logger.info("DEBUG: Statistics updated successfully")
                        except Exception as e:
                            logger.error(f"DEBUG: Error updating statistics: {e}")
                    elif isinstance(injection_result, dict) and injection_result.get("status") == "cancelled":
                        # User cancelled - log and return without doing anything
                        logger.info(f"DEBUG: Injection cancelled by user: {injection_result.get('reason', 'unknown')}")
                        return []  # Return empty list to indicate no features were processed
                    elif isinstance(injection_result, dict) and injection_result.get("status") == "error":
                        # Error occurred - log and show error message
                        error_msg = injection_result.get("message", "Unknown error occurred")
                        logger.error(f"DEBUG: Injection failed: {error_msg}")
                        messagebox.showerror("BMS Injection Error", f"Failed to inject features: {error_msg}")
                        return []  # Return empty list to indicate no features were processed
                    elif injection_result:  # Backwards compatibility for old boolean returns
                        # Success - just update statistics without showing a message
                        # as the calling function will display a success message
                        logger.info("DEBUG: Injection successful (legacy boolean), updating statistics")
                        try:
                            update_statistics(num_features, feature_types)
                            logger.info("DEBUG: Statistics updated successfully")
                        except Exception as e:
                            logger.error(f"DEBUG: Error updating statistics: {e}")
                    
                        # Clean up temporary files after successful operation
                        logger.info("DEBUG: Cleaning up temporary files")
                        try:
                            injector.cleanup_temp_files(Obj_Num)
                            logger.info("DEBUG: Temporary files cleaned up")
                        except Exception as e:
                            logger.error(f"DEBUG: Error cleaning up temporary files: {e}")
                        
                        # Don't create files in the Generated folder for successful BMS injections
                        logger.info("DEBUG: Returning feature entries, BMS injection completed successfully")
                        return feature_entries
                    else:
                        logger.info("DEBUG: Injection failed")
                except Exception as e:
                    logger.error(f"DEBUG: Error during injection: {e}")
                    import traceback
                    logger.error(f"DEBUG: Traceback: {traceback.format_exc()}")
                    raise
                else:
                    messagebox.showerror(
                        "Error",
                        f"Failed to create objective {Obj_Num} or inject features."
                    )
            else:
                # User decided not to proceed
                return None
        except Exception as e:
            messagebox.showerror(
                "Error",
                f"Failed to initialize BMS injection: {str(e)}"
            )
            return None
    else:
        # Write features to file (original behavior) - only for Editor mode
        if SaveType == "Editor":
            success, entries = write_to_file(
                output_file_path, BuildingGeneratorVer, [0, 0], num_features, feature_entries
            )

            # Update statistics only if save was successful
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
    logger.debug(f"Assign_features_accuratly: Applying filter_structures with {len(GeoFeatures)} input features, requesting {num_features}, using filter '{fillter_option}'")
    Selected_GeoFeatures, Selected_CalcData_GeoFeatures = filter_structures(
        pd.DataFrame(CalcData_GeoFeatures),
        pd.DataFrame(GeoFeatures),
        num_features,
        fillter_option,
    )
    logger.debug(f"Assign_features_accuratly: filter_structures returned {len(Selected_GeoFeatures)} features")
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
    shared_data_dict,  # Added shared_data_dict parameter
    CT_Num=None,
    Obj_Num=None,
    selection_type="GeoJson"  # Added to control collision detection
):
    # Seed the random number generator for reproducibility
    np.random.seed(int(time.time()))
    
    # DEBUG: Log all important parameters received
    logger.debug(f"Save_accurate_features called with SaveType='{SaveType}', num_features={num_features}, auto_features_detection={auto_features_detection}, selection_type={selection_type}")
    logger.debug(f"Save_accurate_features: selection_option='{selection_option}', floor_height={floor_height}, num_floors={num_floors}")
    logger.debug(f"Save_accurate_features: AllBMSModels has {len(AllBMSModels)} models, Selected_GeoFeatures has {len(Selected_GeoFeatures)} features")
    if SaveType == "BMS":
        logger.info(f"BMS Injection: Collision detection will be {'ENABLED' if selection_type == 'Random Selection' else 'DISABLED'} for {selection_type} mode")
    logger.debug(f"Save_accurate_features: Values_f={Values_f}, Values_i={Values_i}, Presence_f={Presence_f}, Presence_i={Presence_i}")

    #  initialize lists
    feature_entries = []
    feature_types = []

    # Iterate through each selected geographic feature (LIMITED BY num_features)
    features_to_process = min(num_features, len(Selected_GeoFeatures))
    logger.info(f"Processing {features_to_process} features (requested: {num_features}, available: {len(Selected_GeoFeatures)})")
    for select in range(features_to_process):
        # Auto-select BMS models if enabled
        Auto_BMSModels = (
            Auto_Selected(Db_path, Selected_GeoFeatures.iloc[select])
            if auto_features_detection
            else None
        )
        Models = Auto_BMSModels if Auto_BMSModels is not None else AllBMSModels
        
        # DEBUG: Log auto selection and model info
        if auto_features_detection:
            logger.info(f"Feature {select}: Auto_BMSModels = {Auto_BMSModels.shape if Auto_BMSModels is not None else None}")
            logger.info(f"Feature {select}: Using {'auto-selected' if Auto_BMSModels is not None else 'all'} models ({len(Models)} models)")
            if Auto_BMSModels is None:
                logger.warning(f"Feature {select}: AUTO SELECTION FAILED - falling back to ALL {len(AllBMSModels)} models")
        logger.info(f"Feature {select}: Decision_Algo parameters - selection_option='{selection_option}', floor_height={floor_height}, num_floors={num_floors}")

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
        logger.debug(f"Feature {select}: Decision_Algo selected model CT#{model['CTNumber']} '{model['FeatureName']}' (distance: {closest_distance:.2f})")
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
        
        # Debug logging to help diagnose the value issue
        if Values_f is None and Values_i is None:
            logger.info(f"Using Map value for feature type {model['Type']}: {value}")
        elif Values_i is not None:
            logger.info(f"Using Random value between {Values_i} and {Values_f}: {value}")
        else:
            logger.info(f"Using Solid value {Values_f}: {value}")
        
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

    # Log final feature count to verify the fix worked
    logger.debug(f"Generated {len(feature_entries)} feature entries (limit was {num_features})")
    
    # Sort feature entries if required
    if sort_option != "None":
        feature_entries = sort_feature_entries(feature_entries, sort_option)

    # Check if we're using BMS injection mode
    if SaveType == "BMS" and CT_Num is not None and Obj_Num is not None:
        try:
            from bms_injector import BmsInjector
            from pathlib import Path
            import tkinter as tk
            from tkinter import messagebox
            
            # Get BMS path from shared_data_dict CTpath if available
            if shared_data_dict and 'CTpath' in shared_data_dict and shared_data_dict["CTpath"].get():
                bms_path = os.path.dirname(shared_data_dict["CTpath"].get())
            else:
                # Fall back to SavePath parent directory
                bms_path = Path(SavePath).parent
            
            # Get backup setting from shared_data if available
            # Get backup setting from shared_data_dict if available
            backup_bms_files = False  # Default to True for safety
            if shared_data_dict and 'backup_bms_files' in shared_data_dict:
                # Make sure to handle if shared_data_dict['backup_bms_files'] is already a boolean
                backup_setting = shared_data_dict['backup_bms_files']
                if isinstance(backup_setting, tk.StringVar): # Check if it's a Tkinter StringVar
                    backup_value = backup_setting.get()
                    backup_bms_files = backup_value == '1'
                elif isinstance(backup_setting, str): # Check if it's a plain string '0' or '1'
                    backup_bms_files = backup_setting == '1'
                elif isinstance(backup_setting, bool): # Check if it's already a boolean
                    backup_bms_files = backup_setting
                else:
                    logger.warning(f"Unknown type for backup_bms_files in shared_data_dict (Save_accurate_features): {type(backup_setting)}. Defaulting to False.")
                    backup_bms_files = False # Default to true if type is unexpected
                logger.info(f"BMS file backup {'enabled' if backup_bms_files else 'disabled'}")
            else:
                logger.warning("shared_data_dict or 'backup_bms_files' not found in Save_accurate_features. Defaulting to backup_bms_files=False")
            
            # Create BMS injector instance with appropriate backup setting
            injector = BmsInjector(bms_path, backup=backup_bms_files)
            
            # Check if CT is an objective
            is_objective = injector.is_objective_ct(CT_Num)
            objective_exists = injector.objective_exists(Obj_Num)
            
            proceed = True
            
            # Changed warnings to ask for confirmation instead of warning about CT not being an objective
            if not is_objective and objective_exists:
                proceed = messagebox.askyesno(
                    "Confirmation",
                    f"Are you sure you wish to create Objective overlapping CT Number {CT_Num} and Objective Number {Obj_Num}?"
                )
            elif not is_objective:
                proceed = messagebox.askyesno(
                    "Confirmation",
                    f"Are you sure you wish to create Objective for CT Number {CT_Num} and Objective Number {Obj_Num}?"
                )
            elif objective_exists:
                proceed = messagebox.askyesno(
                    "Confirmation",
                    f"Objective {Obj_Num} already exists. Do you want to override it?"
                )
            
            if proceed:
                # Try to load saved settings for this CT/Obj combination
                try:
                    from utils.json_path_handler import load_json, JsonFiles
                    
                    # Create a temporary root window for message boxes
                    root = tk.Tk()
                    root.withdraw()  # Hide the root window
                    
                    # Load saved objective settings
                    saved_settings = load_json(JsonFiles.SAVED_OBJECTIVE_SETTINGS, default={})
                    
                    # Check if we have saved settings for this CT/Obj combination
                    if saved_settings and saved_settings.get("ct_num") == CT_Num and saved_settings.get("obj_num") == Obj_Num:
                        logger.info(f"Found settings for CT:{CT_Num} Obj:{Obj_Num}")
                        obj_type = saved_settings.get("type")
                        name = saved_settings.get("name")
                        reset_pd = saved_settings.get("reset_pd", True)
                        fields = saved_settings.get("fields", {})
                        
                        # Convert field values to appropriate types
                        typed_fields = {}
                        for field_name, value in fields.items():
                            try:
                                if isinstance(value, str) and "." in value:
                                    typed_fields[field_name] = float(value)
                                elif isinstance(value, str) and value.isdigit():
                                    typed_fields[field_name] = int(value)
                                else:
                                    typed_fields[field_name] = value
                            except ValueError:
                                typed_fields[field_name] = value
                                
                        fields = typed_fields
                        logger.info(f"Using saved settings: type={obj_type}, name={name}, reset_pd={reset_pd}")
                    else:
                        logger.error(f"No saved settings found for CT:{CT_Num} Obj:{Obj_Num}")
                        messagebox.showerror(
                            "Missing Configuration",
                            f"No saved settings found for CT:{CT_Num} and Objective:{Obj_Num}.\n\n"
                            f"Please configure this objective first using the BMS Injection window."
                        )
                        root.destroy()
                        return None
                except Exception as e:
                    error_msg = f"Error loading saved settings: {e}"
                    logger.error(error_msg)
                    messagebox.showerror(
                        "Error",
                        f"Failed to load objective settings: {str(e)}\n\n"
                        f"Please reconfigure this objective using the BMS Injection window."
                    )
                    root.destroy()
                    return None
                
                # Clean up the root window
                root.destroy()
                        
                # Update injector with new path if changed
                injector = BmsInjector(bms_path, backup=backup_bms_files)
                
                # Create objective and inject features in one operation
                injection_result = injector.create_and_inject_objective(Obj_Num, CT_Num, name, obj_type, feature_entries, AllBMSModels, fields, reset_pd, selection_type)
                
                # Check if injection was successful (not cancelled or error)
                if isinstance(injection_result, dict) and injection_result.get("status") == "success":
                    # Success - just update statistics without showing a message
                    # as the calling function will display a success message
                    update_statistics(num_features, feature_types)
                
                    # Clean up temporary files after successful operation
                    injector.cleanup_temp_files(Obj_Num)
                    
                    # Don't create files in the Generated folder for successful BMS injections
                    return feature_entries
                elif isinstance(injection_result, dict) and injection_result.get("status") == "cancelled":
                    # User cancelled - log and return without doing anything
                    logger.info(f"BMS injection cancelled by user: {injection_result.get('reason', 'unknown')}")
                    return []  # Return empty list to indicate no features were processed
                elif isinstance(injection_result, dict) and injection_result.get("status") == "error":
                    # Error occurred - show error message
                    error_msg = injection_result.get("message", "Unknown error occurred")
                    logger.error(f"BMS injection failed: {error_msg}")
                    messagebox.showerror("BMS Injection Error", f"Failed to inject features: {error_msg}")
                    return []  # Return empty list to indicate no features were processed
                elif injection_result:  # Backwards compatibility for old boolean returns
                    # Success - just update statistics without showing a message
                    # as the calling function will display a success message
                    update_statistics(num_features, feature_types)
                
                    # Clean up temporary files after successful operation
                    injector.cleanup_temp_files(Obj_Num)
                    
                    # Don't create files in the Generated folder for successful BMS injections
                    return feature_entries
                else:
                    messagebox.showerror(
                        "Error",
                        f"Failed to create objective {Obj_Num} or inject features."
                    )
            else:
                # User decided not to proceed
                return None
        except Exception as e:
            messagebox.showerror(
                "Error",
                f"Failed to initialize BMS injection: {str(e)}"
            )
            return None
    else:
        # Write features to file only in Editor mode
        if SaveType == "Editor":
            success, entries = write_to_file(
                SavePath, BuildingGeneratorVer, AOI_center, num_features, feature_entries
            )
            # Update statistics only if save was successful
            if success:
                update_statistics(num_features, feature_types)

    return feature_entries

# Initialize cached values dictionary
_cached_values_dict = None


# Function to load values dictionary from a JSON file
def load_values_dict():
    # No defaults - if loading fails, it should raise an error
    try:
        values_dict = load_json(JsonFiles.VALUES_DICTIONARY, default=None)
        if values_dict is None:
            error_msg = "ValuesDictionary.json file not found or empty"
            logger.error(error_msg)
            raise ValueError(error_msg)
        return values_dict
    except Exception as e:
        error_msg = f"Failed to load ValuesDictionary: {str(e)}"
        logger.error(error_msg)
        raise ValueError(error_msg)


# Function to get a value based on input parameters and values dictionary
def get_value(Values_i, Values_f, model_type):
    if Values_i is not None and Values_f is not None:
        # Random value between min and max
        try:
            value = np.random.uniform(Values_i, Values_f)
            return value
        except Exception as e:
            error_msg = f"Failed to generate random value between {Values_i} and {Values_f}: {str(e)}"
            logger.error(error_msg)
            raise ValueError(error_msg)
    elif Values_f is not None:
        return Values_f
    else:
        # Validation checks
        if model_type is None:
            error_msg = "Cannot look up value in ValuesDictionary: model_type is None"
            logger.error(error_msg)
            raise ValueError(error_msg)
        # Only load values dictionary when actually needed
        try:
            values_dict = load_values_dict()
        except Exception as e:
            error_msg = f"Failed to load ValuesDictionary: {str(e)}"
            logger.error(error_msg)
            raise ValueError(error_msg)
            
        # Make sure model_type is a string when looking up in the dictionary
        model_type_str = str(model_type)
        
        # Look up the value based on model type and return it
        type_entry = values_dict.get(model_type_str)
        
        # No defaults - if the model type isn't in the dictionary, it's an error
        if not type_entry:
            error_msg = f"No entry found in ValuesDictionary for model type {model_type}"
            logger.error(error_msg)
            raise ValueError(error_msg)
            
        # Validate the entry has a Value field
        if "Value" not in type_entry:
            error_msg = f"ValuesDictionary entry for model type {model_type} is missing the 'Value' field"
            logger.error(error_msg)
            raise ValueError(error_msg)
            
        dict_value = type_entry["Value"]
        logger.info(f"Using ValuesDictionary value {dict_value} for model type {model_type}")
        return dict_value


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
    # Validate all required inputs are provided
    if ct_number is None:
        error_msg = "CT number cannot be None"
        logger.error(error_msg)
        raise ValueError(error_msg)
        
    if value is None:
        error_msg = f"Feature value cannot be None for CT {ct_number} ({feature_name})"
        logger.error(error_msg)
        raise ValueError(error_msg)
        
    if presence is None:
        error_msg = f"Feature presence cannot be None for CT {ct_number} ({feature_name})"
        logger.error(error_msg)
        raise ValueError(error_msg)
        
    if feature_name is None:
        error_msg = f"Feature name cannot be None for CT {ct_number}"
        logger.error(error_msg)
        raise ValueError(error_msg)
    
    # Format the value as a 4-digit integer
    try:
        # Convert value to integer and format to 4 digits with leading zeros
        value_int = int(value)  # Ensure value is an integer
        formatted_value = f"{value_int:04d}"
        
        # Show the value transformation for debugging
        logger.debug(f"Feature CT {ct_number} ({feature_name}) - value {value} formatted to '{formatted_value}'")
        logger.info(f"Feature value for CT {ct_number} ({feature_name}): {value} -> {formatted_value}")
    except (ValueError, TypeError) as e:
        # No defaults - if we can't format the value, it's an error
        error_msg = f"Error formatting value '{value}' for feature {feature_name}: {e}"
        logger.error(error_msg)
        logger.error(error_msg)
        raise ValueError(error_msg)
    
    # Format presence as integer
    try:
        presence_int = int(presence)
    except (ValueError, TypeError) as e:
        error_msg = f"Error converting presence '{presence}' to integer for CT {ct_number}: {e}"
        logger.error(error_msg)
        raise ValueError(error_msg)
    
    # Format the feature entry string
    try:
        return (
            f"FeatureEntry={ct_number} {y_distance:.4f} {x_distance:.4f} 0.0000 {rotation:.4f} "
            f"{formatted_value} 0000 -1 {presence_int}# {select}) {feature_name}"
        )
    except Exception as e:
        error_msg = f"Error creating feature entry for CT {ct_number}: {e}"
        logger.error(error_msg)
        raise ValueError(error_msg)


# Function to load values dictionary from a JSON file
def load_values_dict():
    try:
        values_dict = load_json(JsonFiles.VALUES_DICTIONARY, default=None)
        if values_dict is None:
            error_msg = "ValuesDictionary.json file not found or empty"
            logger.error(error_msg)
            raise ValueError(error_msg)
        return values_dict
    except Exception as e:
        error_msg = f"Failed to load ValuesDictionary: {str(e)}"
        logger.error(error_msg)
        raise ValueError(error_msg)


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

    # Pre-convert the data to a JSON-compatible format
    try:
        # First convert using json.dumps with the custom default function
        # Then parse it back to a Python object that save_json can handle
        json_compatible_stats = json.loads(json.dumps(stats, default=default))
        # Now save using save_json without the default parameter
        save_json(JsonFiles.FEATURE_STATISTICS, json_compatible_stats)
    except Exception as e:
        logger.error(f"Error saving statistics: {e}")


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
        stats = load_json(JsonFiles.FEATURE_STATISTICS, default=None)
        
        if stats:
            logger.info(f"Loaded feature statistics from {JsonFiles.FEATURE_STATISTICS}")
            
            # Ensure all required keys exist and have the correct types
            if "total_features" not in stats:
                stats["total_features"] = 0
            if "total_usage" not in stats:
                stats["total_usage"] = 0
            if "feature_types" not in stats:
                stats["feature_types"] = Counter()
            elif not isinstance(stats["feature_types"], Counter):
                stats["feature_types"] = Counter(stats["feature_types"])
                
            return stats
        else:
            # If no stats were loaded, create a new stats dictionary
            logger.info("No feature statistics found, creating new default statistics")
            return {"total_features": 0, "total_usage": 0, "feature_types": Counter()}
    except Exception as e:
        logger.error(f"Error loading feature statistics: {e}")
        if logger.isEnabledFor(logging.DEBUG):
            import traceback
            logger.debug(traceback.format_exc())
        return {"total_features": 0, "total_usage": 0, "feature_types": Counter()}


def Auto_Selected(Db_path, Selected_GeoFeature):
    """The function detects possible keys in the GeoFeature and loading a proper Models from the Database for better type fitting"""
    logger.info(f"Auto_Selected DEBUG: Feature keys available: {list(Selected_GeoFeature.keys())}")
    logger.info(f"Auto_Selected DEBUG: building='{Selected_GeoFeature.get('building', 'NOT_FOUND')}', leisure='{Selected_GeoFeature.get('leisure', 'NOT_FOUND')}', amenity='{Selected_GeoFeature.get('amenity', 'NOT_FOUND')}'")
    logger.info(f"Auto_Selected DEBUG: man_made='{Selected_GeoFeature.get('man_made', 'NOT_FOUND')}', military='{Selected_GeoFeature.get('military', 'NOT_FOUND')}', bms='{Selected_GeoFeature.get('bms', 'NOT_FOUND')}'")
    logger.info(f"Auto_Selected DEBUG: Full feature data sample: {dict(list(Selected_GeoFeature.items())[:10])}")
    
    fillters = []

    # Check for direct BMS type specification
    if Selected_GeoFeature["bms"]:
        logger.debug(f"Direct BMS type specified: {Selected_GeoFeature['bms']}")
        Accurate_filltered_BMSmodels = Load_Db(Db_path, str(Selected_GeoFeature["bms"]))
        if not Accurate_filltered_BMSmodels.empty:
            logger.info(f"Found {len(Accurate_filltered_BMSmodels)} direct BMS models for type '{Selected_GeoFeature['bms']}'")
            return Accurate_filltered_BMSmodels
        else:
            logger.warning(f"No BMS models found for direct type '{Selected_GeoFeature['bms']}'")

    # Sports facilities
    stadium = ["stadium", "ice_rink", "sports_centre", "sports_hall"]
    if (Selected_GeoFeature["leisure"] and any(s in split_string(Selected_GeoFeature["leisure"]) for s in stadium)) or Selected_GeoFeature["sport"]:
        fillters.extend(["66", "sport"])
        logger.debug("Added sports facility filters")

    # Religious buildings
    if Selected_GeoFeature["religion"]:
        religion_terms = split_string(Selected_GeoFeature["religion"])
        logger.debug(f"Processing religion terms: {religion_terms}")
        if "muslim" in religion_terms:
            fillters.extend(["minaret", "mosque"])
            logger.debug("Added Muslim religious filters")
        elif "jewish" in religion_terms:
            fillters.extend(["synagogue"])
            logger.debug("Added Jewish religious filters")
        elif "christian" in religion_terms:
            fillters.extend(["church", "presbytery", "cathedral", "chapel"])
            logger.debug("Added Christian religious filters")
        elif "buddhist" in religion_terms or "shinto" in religion_terms:
            fillters.extend(["temple", "shrine", "monastery"])
            logger.debug("Added Buddhist/Shinto religious filters")
        else:
            fillters.extend(["7", "40"])
            logger.debug("Added generic religious filters")

    # Building types
    if Selected_GeoFeature["building"]:
        building_terms = split_string(Selected_GeoFeature["building"])
        logger.debug(f"Processing building terms: {building_terms}")
        if "hangar" in building_terms:
            fillters.extend(["has", "hangar", "ft shelter"])
            logger.debug("Added hangar filters")
        elif any(term in building_terms for term in ["mosque", "minaret", "muslim"]):
            fillters.extend(["minaret", "mosque"])
            logger.debug("Added mosque filters")
        if any(term in building_terms for term in ["cathedral", "chapel", "presbytery"]):
            fillters.extend(["church", "presbytery", "cathedral", "chapel", "monastery"])
            logger.debug("Added church filters")
        if "warehouse" in building_terms:
            fillters.extend(["12", "warehouse"])
            logger.debug("Added warehouse filters")
        if "synagogue" in building_terms:
            fillters.extend(["synagogue"])
            logger.debug("Added synagogue filters")
        if "shrine" in building_terms:
            fillters.extend(["shrine"])
            logger.debug("Added shrine filters")
        if "temple" in building_terms:
            fillters.extend(["temple", "monastery"])
            logger.debug("Added temple filters")

    # Aeroway facilities
    if Selected_GeoFeature["aeroway"]:
        aeroway_terms = split_string(Selected_GeoFeature["aeroway"])
        logger.debug(f"Processing aeroway terms: {aeroway_terms}")
        heli = ["heliport", "helipad"]
        if "terminal" in aeroway_terms:
            fillters.extend(["terminal"])
            logger.debug("Added terminal filters")
        if "apron" in aeroway_terms:
            fillters.extend(["39", "45", "hangar", "terminal", "depot", "warehouse"])
            logger.debug("Added apron filters")
        if any(term in aeroway_terms for term in heli):
            fillters.extend(["helipad", "13"])
            logger.debug("Added helipad filters")
        elif "windsock" in aeroway_terms:
            fillters.extend(["windsock"])
            logger.debug("Added windsock filters")
        elif "arresting_gear" in aeroway_terms:
            fillters.extend(["68"])
            logger.debug("Added arresting gear filters")
        elif "navigationaid" in aeroway_terms:
            fillters.extend(["25", "localizer", "tacan", "beacon"])
            logger.debug("Added navigation aid filters")
        elif "tower" in aeroway_terms:
            fillters.extend(["2"])
            logger.debug("Added control tower filters")

    # Barriers
    if Selected_GeoFeature["barrier"]:
        barrier_terms = split_string(Selected_GeoFeature["barrier"])
        logger.debug(f"Processing barrier terms: {barrier_terms}")
        if "border_control" in barrier_terms:
            fillters.extend(["55"])
            logger.debug("Added border control filters")
        if "fence" in barrier_terms:
            fillters.extend(["49"])
            logger.debug("Added fence filters")

    # Man-made structures
    if Selected_GeoFeature["man_made"]:
        man_made_terms = split_string(Selected_GeoFeature["man_made"])
        logger.debug(f"Processing man_made terms: {man_made_terms}")
        fire_poles = ["flare", "chimney"]
        if "beacon" in man_made_terms:
            fillters.extend(["beacon"])
            logger.debug("Added beacon filters")
        elif any(term in man_made_terms for term in fire_poles):
            fillters.extend(["61", "51", "release value"])
            logger.debug("Added fire/chimney filters")
        elif "lighting" in man_made_terms:
            fillters.extend(["46", "lights", "light"])
            logger.debug("Added lighting filters")

    # Towers
    if Selected_GeoFeature["tower"]:
        tower_terms = split_string(Selected_GeoFeature["tower"])
        logger.debug(f"Processing tower terms: {tower_terms}")
        watch_tower = ["watchtower", "observation"]
        antennas = ["monitoring", "communication", "na"]
        if any(term in tower_terms for term in watch_tower):
            fillters.extend(["watchtower"])
            logger.debug("Added watchtower filters")
        if any(term in tower_terms for term in antennas):
            fillters.extend(["radio tower", "telecom tower"])
            logger.debug("Added antenna tower filters")
        if "lighting" in tower_terms:
            fillters.extend(["46", "lights", "light"])
            logger.debug("Added lighting tower filters")
        if "minaret" in tower_terms:
            fillters.extend(["minaret", "mosque"])
            logger.debug("Added minaret filters")
        if "radar" in tower_terms:
            fillters.extend(["radar"])
            logger.debug("Added radar filters")
        if "control" in tower_terms or "traffic" in tower_terms:
            fillters.extend(["2"])
            logger.debug("Added control tower filters")
    elif Selected_GeoFeature["man_made"]:
        man_made_terms = split_string(Selected_GeoFeature["man_made"])
        antennas = ["communications_tower", "antenna", "satellite_dish", "telescope"]
        if "tower" in man_made_terms:
            if Selected_GeoFeature["service"] and "aircraft_control" in split_string(Selected_GeoFeature["service"]):
                fillters.extend(["2"])
                logger.debug("Added aircraft control tower filters")
            else:
                fillters.extend(["61", "tower"])
                logger.debug("Added generic tower filters")
        if "cooling_tower" in man_made_terms:
            fillters.extend(["53"])
            logger.debug("Added cooling tower filters")
        if any(term in man_made_terms for term in antennas):
            fillters.extend(["29", "43", "antenna", "33", "28", "satellite"])
            logger.debug("Added antenna/satellite filters")
        if "communications_tower" in man_made_terms:
            fillters.extend(["radio tower", "telecom tower"])
            logger.debug("Added communications tower filters")

    # Power infrastructure
    if Selected_GeoFeature["power"]:
        power_terms = split_string(Selected_GeoFeature["power"])
        logger.debug(f"Processing power terms: {power_terms}")
        power = ["compensator", "plant", "substation", "busbar"]
        electric_tower = ["tower", "terminal", "connection"]
        if any(term in power_terms for term in power):
            fillters.extend(["23", "converter", "32", "processor","Generator", "Forge"])
            logger.debug("Added power plant filters")
        if any(term in power_terms for term in electric_tower):
            fillters.extend(["20"])
            logger.debug("Added electric tower filters")
        if "converter" in power_terms:
            fillters.extend(["converter"])
            logger.debug("Added converter filters")
        if "transformer" in power_terms:
            fillters.extend(["transformer"])
            logger.debug("Added transformer filters")
        if "heliostat" in power_terms:
            fillters.extend(["Solar Mirrors"])
            logger.debug("Added solar mirror filters")

    # Industrial facilities
    if (Selected_GeoFeature["man_made"] and any(term in split_string(Selected_GeoFeature["man_made"]) for term in ["pump", "pumping_station", "works"])) or \
       (Selected_GeoFeature["building"] and "industrial" in split_string(Selected_GeoFeature["building"])):
        fillters.extend(["32", "53", "60", "56", "23", "6"])
        logger.debug("Added industrial facility filters")

    # Pipelines
    if Selected_GeoFeature["man_made"] and "pipeline" in split_string(Selected_GeoFeature["man_made"]):
        fillters.extend(["piping"])
        logger.debug("Added pipeline filters")

    # Storage tanks
    if (Selected_GeoFeature["building"] and any(term in split_string(Selected_GeoFeature["building"]) for term in ["gasometer", "storage_tank", "fuel", "tank"])) or \
       (Selected_GeoFeature["man_made"] and any(term in split_string(Selected_GeoFeature["man_made"]) for term in ["gasometer", "storage_tank", "fuel", "tank"])):
        fillters.extend(["48", "fuel", "gas"])
        logger.debug("Added storage tank filters")

    # Silos
    if (Selected_GeoFeature["building"] and "silo" in split_string(Selected_GeoFeature["building"])) or \
       (Selected_GeoFeature["man_made"] and "silo" in split_string(Selected_GeoFeature["man_made"])):
        fillters.extend(["silo"])
        logger.debug("Added silo filters")

    # Water towers
    if (Selected_GeoFeature["building"] and "water_tower" in split_string(Selected_GeoFeature["building"])) or \
       (Selected_GeoFeature["man_made"] and "water_tower" in split_string(Selected_GeoFeature["man_made"])):
        fillters.extend(["37"])
        logger.debug("Added water tower filters")

    # Bridges
    if (Selected_GeoFeature["building"] and any(term in split_string(Selected_GeoFeature["building"]) for term in ["bridge", "bridges"])) or \
       (Selected_GeoFeature["man_made"] and any(term in split_string(Selected_GeoFeature["man_made"]) for term in ["bridge", "bridges"])) or \
       Selected_GeoFeature["bridge"]:
        fillters.extend(["16"])
        logger.debug("Added bridge filters")

    # Hospitals
    if (Selected_GeoFeature["building"] and "hospital" in split_string(Selected_GeoFeature["building"])) or \
       (Selected_GeoFeature["amenity"] and "hospital" in split_string(Selected_GeoFeature["amenity"])):
        fillters.extend(["62"])
        logger.debug("Added hospital filters")

    # Military bunkers
    if (Selected_GeoFeature["military"] and "bunker" in split_string(Selected_GeoFeature["military"])) or \
       (Selected_GeoFeature["building"] and "bunker" in split_string(Selected_GeoFeature["building"])):
        fillters.extend(["4", "bunker"])
        logger.debug("Added bunker filters")

    # Military barracks
    barracks = ["barrack", "barracks"]
    if (Selected_GeoFeature["building"] and any(term in split_string(Selected_GeoFeature["building"]) for term in barracks)) or \
       (Selected_GeoFeature["military"] and any(term in split_string(Selected_GeoFeature["military"]) for term in barracks)):
        fillters.extend(["12", "35", "10"])
        logger.debug("Added barrack filters")

    # Military ammunition
    if Selected_GeoFeature["military"] and any(term in split_string(Selected_GeoFeature["military"]) for term in ["ammo", "ammunition", "munition"]):
        fillters.extend(["ammo", "ammunition", "munition", "bunker"])
        logger.debug("Added ammunition filters")

    # Execute the database query with collected filters
    filters_str = ", ".join(fillters)
    logger.debug(f"Final filter string: '{filters_str}'")
    
    if filters_str != "":
        try:
            Accurate_filltered_BMSmodels = Load_Db(Db_path, filters_str)
            if not Accurate_filltered_BMSmodels.empty:
                logger.info(f"Auto_Selected found {len(Accurate_filltered_BMSmodels)} matching BMS models using {len(fillters)} filters")
                logger.debug(f"Auto_Selected: Filtered models CT numbers: {Accurate_filltered_BMSmodels['CTNumber'].tolist()}")
                return Accurate_filltered_BMSmodels
            else:
                logger.warning(f"Auto_Selected: No BMS models found matching filters: {filters_str}")
                return None
        except Exception as e:
            logger.error(f"Auto_Selected: Error querying database with filters '{filters_str}': {str(e)}")
            return None
    else:
        logger.info("Auto_Selected: No applicable filters found for the given GeoFeature")
        logger.debug(f"Auto_Selected: Feature has no matching filters - falling back to AllBMSModels")
        return None

def split_string(s):
    """Split a string by multiple delimiters and return a list of lowercase terms"""
    return [term.strip().lower() for term in re.split(r'[,\s/\\.]', s) if term.strip()]
