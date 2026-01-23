import numpy as np
import pandas as pd
from dataclasses import dataclass, field
from typing import List, Protocol, Tuple, Optional, Any
import os

@dataclass
class FrameData:
    """
    Data structure representing the extraction result from a single frame.
    """
    frame_index: int
    timestamp: float
    # List of (x, y) points found on the neutral line
    # Using float because sub-pixel detection might return non-integers
    neutral_points: List[Tuple[float, float]] = field(default_factory=list)

class EdgeDetector(Protocol):
    """
    Protocol (Interface) for edge detection algorithms.
    This allows us to swap Canny for Sub-pixel methods later without changing the main loop.
    """
    def detect(self, image_roi: np.ndarray) -> Any:
        # Returns an edge map or similar structure suitable for line extraction
        ...

class VibrationTimeSeries:
    """
    Core class to accumulate vibration data and handle physical conversions.
    """
    def __init__(self, fps: float = 30.0, scale_factor: float = 1.0):
        """
        :param fps: Frames per second of the video.
        :param scale_factor: Conversion factor (e.g., mm per pixel). 1.0 means data is in pixels.
        """
        self.fps = fps
        self.scale_factor = scale_factor
        self.data_store: List[FrameData] = []

    def add_frame(self, frame_idx: int, points: List[Tuple[float, float]]):
        """
        Registers data for a specific frame.
        """
        timestamp = frame_idx / self.fps
        # Apply scaling if needed immediately, or store raw and scale on export.
        # Storing raw is usually safer.
        frame_data = FrameData(
            frame_index=frame_idx,
            timestamp=timestamp,
            neutral_points=points
        )
        self.data_store.append(frame_data)

    def to_dataframe(self) -> pd.DataFrame:
        """
        Exports the accumulated data to a pandas DataFrame.
        Format:
        Index: Timestamp
        Columns: x_coord_1, x_coord_2, ... (Displacements at specific X)
        
        *Note*: Since the neutral line moves, we might need to interpolate to fixed X positions
        if we want a clean matrix. For now, we export a "melted" or raw structure.
        """
        # Flattens the data: Frame | Time | X_px | Y_px | Y_mm
        records = []
        for fd in self.data_store:
            for (x, y) in fd.neutral_points:
                records.append({
                    "frame": fd.frame_index,
                    "time_sec": fd.timestamp,
                    "x_px": x,
                    "y_px": y,
                    "displacement_mm": y * self.scale_factor # Assuming Y is displacement
                })
        
        return pd.DataFrame(records)

    def save_csv(self, filepath: str):
        """
        Persists data to CSV.
        """
        df = self.to_dataframe()
        if not df.empty:
            df.to_csv(filepath, index=False)
            print(f"Data successfully saved to {filepath}")
        else:
            print("No data to save.")
