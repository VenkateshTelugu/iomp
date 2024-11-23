import cv2
import numpy as np

def analyze_image(image_path):
    # Load the image
    img = cv2.imread(image_path)

    # Convert to grayscale
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # Detect edges
    edges = cv2.Canny(gray, 50, 150)

    # Find contours
    contours, _ = cv2.findContours(edges, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)

    # Assume the largest contour is the roof
    roof_contour = max(contours, key=cv2.contourArea)

    # Calculate roof area (assuming each pixel = 1 sq. ft.)
    roof_area = cv2.contourArea(roof_contour)

    # Usable solar area (80% of roof area)
    solar_area = roof_area * 0.8

    # Panel calculations (Assume one panel = 18 sq. ft.)
    panels = int(solar_area / 18)

    # Dummy shading impact (for now)
    shading_impact = "Low"

    return roof_area, solar_area, panels, shading_impact
