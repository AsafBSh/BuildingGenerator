import math
import numpy as np
import matplotlib.pyplot as plt
from MinimumBoundingBox import MinimumBoundingBox


def draw_shape(points_list, shape_color="blue", marker="o", label=None):
    """
    Draws a shape based on a list of points.

    Args:
        points_list (list): List of lists, where each inner list contains (x, y) coordinates representing a point.
        shape_color (str): Color of the shape's outline.
        marker (str): Marker style for the points.
        label (str): Label for the shape in the plot legend.

    Returns:
        None
    """
    # Extract x and y coordinates from the points_list
    x_coords = [point[0] for point in points_list]
    y_coords = [point[1] for point in points_list]

    # Plot the points
    plt.plot(x_coords, y_coords, marker=marker, label=label, color=shape_color)

    # Connect the last point to the first point to close the shape
    plt.plot(
        [x_coords[-1], x_coords[0]], [y_coords[-1], y_coords[0]], color=shape_color
    )


def calc_rotation_and_side_lengths_via_slope(rectangle_points):
    """calculate distances and angle from the negative Y axis in a clockwise rotation.
    it is done by calculating the slope of the most left point (or most left upper point) as pixed point"""
    try:
        # Ensure rectangle_points are numeric values
        rectangle_points = np.array(rectangle_points, dtype=float)
        
        distances = []
        # Get distances of the rectangle
        for i in range(len(rectangle_points)):
            distances.append(
                np.linalg.norm(
                    rectangle_points[i] - rectangle_points[(i + 1) % len(rectangle_points)]
                )
            )
    except Exception as e:
        raise ValueError(f"Error calculating distances: {str(e)}")

    # Find the index of the leftmost point considering left upper point if multiple points have the same x-coordinate
    leftmost_point_indexes = np.where(
        rectangle_points[:, 0] == np.min(rectangle_points[:, 0])
    )[0]
    leftmost_point_index = leftmost_point_indexes[
        np.argmin(rectangle_points[leftmost_point_indexes, 1])
    ]
    leftmost_point = rectangle_points[leftmost_point_index]

    # Find neighboring points
    prv_point_idx = (leftmost_point_index - 1) % len(rectangle_points)
    nxt_point_idx = (leftmost_point_index + 1) % len(rectangle_points)

    # get side lengths
    length_to_previous = distances[prv_point_idx]
    length_to_next = distances[leftmost_point_index]

    # Determine the longer side
    if length_to_previous > length_to_next:
        longer_side_neighbor = rectangle_points[prv_point_idx]
    else:
        longer_side_neighbor = rectangle_points[nxt_point_idx]

    # Calculate the slope
    Slope = (longer_side_neighbor[1] - leftmost_point[1]) / (
        longer_side_neighbor[0] - leftmost_point[0]
    )
    # calculate angle in radians from -y axis then convert to degrees
    Angle_in_Deg = math.degrees((math.pi / 2 * 3) - math.atan(Slope))

    return Angle_in_Deg, distances


def check_crossing_lines(bondingBox):
    """The funtion is fixing the arrangement of the bonding box's points making it consistent with the algorithm"""
    try:
        # Ensure bondingBox contains numeric values
        bondingBox = np.array(bondingBox, dtype=float)
        
        threshold = 1e-6  # A small threshold to account for numerical imprecisions

        for i in range(len(bondingBox)):
            p1 = bondingBox[i]
            p2 = bondingBox[
                (i + 1) % len(bondingBox)
            ]  # Wrap around to the first point if needed
            p3 = bondingBox[
                (i + 2) % len(bondingBox)
            ]  # Wrap around to the second point if needed

            # Calculate the vectors of the two line segments
            vec1 = p2 - p1
            vec2 = p3 - p2

            # Calculate the dot product between the vectors
            dot_product = np.dot(vec1, vec2)
            # Check if the dot product is above the threshold
            if abs(dot_product) > threshold:
                # If the dot product is above the threshold, switch the second and third coordinates
                (
                    bondingBox[(i + 2) % len(bondingBox), :],
                    bondingBox[(i + 3) % len(bondingBox), :],
                ) = (
                    bondingBox[(i + 3) % len(bondingBox), :].copy(),
                    bondingBox[(i + 2) % len(bondingBox), :].copy(),
                )
    except Exception as e:
        raise ValueError(f"Error processing bounding box: {str(e)}")

    return bondingBox




def fitted_features(coordinates):
    """Main function:
    input: list of x and y coordinates
    output: size of bonding box and its rotation compare to the longest side
    """
    # Ensure all coordinates are float values before processing
    try:
        # Convert all coordinates to float values
        float_coordinates = []
        for point in coordinates:
            if len(point) < 2:
                continue  # Skip points with insufficient dimensions
            try:
                # Try to convert each coordinate to float
                float_point = [float(point[0]), float(point[1])]
                float_coordinates.append(float_point)
            except (ValueError, TypeError):
                # Skip points with non-numeric values
                continue
                
        if len(float_coordinates) < 3:
            # Need at least 3 points for a valid polygon
            raise ValueError("Insufficient valid points after conversion")
            
        # Convert to tuples for MinimumBoundingBox
        tuple_coordinations = [tuple(point) for point in float_coordinates]
        bounding_box = MinimumBoundingBox(tuple_coordinations)
    except Exception as e:
        # Re-raise with more context
        raise ValueError(f"Error processing coordinates: {str(e)}")

    # listing the bounding box
    try:
        bondingBox = np.array(list(bounding_box.corner_points), dtype=float)
        # Center (is list inside list for showing in graph
        center = [np.array(list(bounding_box.rectangle_center), dtype=float)]
        # Fixing arrange of points
        bondingBox = check_crossing_lines(bondingBox)
    except Exception as e:
        raise ValueError(f"Error processing bounding box data: {str(e)}")

    try:
        rotation_angle, side_lengths = calc_rotation_and_side_lengths_via_slope(bondingBox)
    except Exception as e:
        raise ValueError(f"Error calculating rotation and side lengths: {str(e)}")



    # Ensure all return values are proper numeric types
    try:
        center_float = np.array(center[0], dtype=float)
        rotation_float = float(rotation_angle)
        side_lengths_float = [float(side) for side in side_lengths]
        return center_float, rotation_float, side_lengths_float
    except Exception as e:
        raise ValueError(f"Error converting return values to numeric types: {str(e)}")

    #
