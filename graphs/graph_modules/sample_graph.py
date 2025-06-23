"""
Sample graph implementation for TGraph Bot.

This module provides a concrete example of how to extend the BaseGraph class
to create new graph types. It serves as a template and reference for developers
adding new graph implementations to the system.
"""

import logging
from collections.abc import Mapping, Sequence
from typing import TYPE_CHECKING, cast, override

import seaborn as sns

from .base_graph import BaseGraph

if TYPE_CHECKING:
    from config.schema import TGraphBotConfig

logger = logging.getLogger(__name__)


class SampleGraph(BaseGraph):
    """
    Sample concrete graph implementation demonstrating the BaseGraph pattern.

    This class shows how to:
    - Extend the BaseGraph abstract base class
    - Implement required abstract methods
    - Use utility functions from the base class
    - Follow modern Python patterns and best practices
    - Handle data processing and visualization
    """

    def __init__(
        self,
        config: "TGraphBotConfig | dict[str, object] | None" = None,
        width: int = 10,
        height: int = 6,
        dpi: int = 100,
        background_color: str | None = None,
    ) -> None:
        """
        Initialize the sample graph.

        Args:
            config: Configuration object containing graph settings
            width: Figure width in inches
            height: Figure height in inches
            dpi: Dots per inch for the figure
            background_color: Background color for the graph (overrides config if provided)
        """
        super().__init__(
            config=config,
            width=width,
            height=height,
            dpi=dpi,
            background_color=background_color,
        )

    @override
    def get_title(self) -> str:
        """
        Get the title for this graph type.

        Returns:
            The graph title
        """
        return "Sample Data Visualization"

    @override
    def generate(self, data: Mapping[str, object]) -> str:
        """
        Generate the sample graph using the provided data.

        This method demonstrates the complete workflow:
        1. Data validation and processing
        2. Figure setup using base class methods
        3. Data visualization using matplotlib/seaborn
        4. Saving the figure using utility functions

        Args:
            data: Dictionary containing the data needed for the graph.
                 Expected keys:
                 - 'x_values': List of x-axis values
                 - 'y_values': List of y-axis values
                 - 'title': Optional custom title
                 - 'user_id': Optional user ID for filename

        Returns:
            Path to the generated graph image file

        Raises:
            ValueError: If required data is missing or invalid
        """
        # Step 1: Validate and process input data
        x_values_raw = data.get("x_values")
        y_values_raw = data.get("y_values")

        if not x_values_raw or not y_values_raw:
            raise ValueError("Both 'x_values' and 'y_values' are required in data")

        # Cast to sequences for type safety
        x_values = cast(Sequence[float], x_values_raw)
        y_values = cast(Sequence[float], y_values_raw)

        if len(x_values) != len(y_values):
            raise ValueError("x_values and y_values must have the same length")

        # Extract optional parameters
        custom_title = cast(str, data.get("title")) if data.get("title") else None
        user_id = data.get("user_id")

        # Step 2: Setup figure using base class method
        figure, axes = self.setup_figure()

        # Step 3: Configure seaborn style for better aesthetics
        sns.set_style("whitegrid")
        sns.set_palette("husl")

        # Step 4: Create the visualization
        try:
            # Create a simple line plot with markers
            _ = axes.plot(x_values, y_values, marker="o", linewidth=2, markersize=6)  # pyright: ignore[reportUnknownMemberType]

            # Set title (use custom title if provided, otherwise use default)
            title = custom_title if custom_title else self.get_title()
            _ = axes.set_title(title, fontsize=16, fontweight="bold", pad=20)  # pyright: ignore[reportUnknownMemberType]

            # Set axis labels
            _ = axes.set_xlabel("X Values", fontsize=12)  # pyright: ignore[reportUnknownMemberType]
            _ = axes.set_ylabel("Y Values", fontsize=12)  # pyright: ignore[reportUnknownMemberType]

            # Add grid for better readability
            axes.grid(True, alpha=0.3)  # pyright: ignore[reportUnknownMemberType]

            # Improve layout
            figure.tight_layout()

            logger.info(f"Generated sample graph with {len(x_values)} data points")

        except Exception as e:
            logger.error(f"Error creating sample graph visualization: {e}")
            raise

        # Step 5: Save the figure using base class utility method
        try:
            # Convert user_id to string if provided
            user_id_str = str(user_id) if user_id is not None else None

            # Use base class save method with automatic filename generation
            output_path = self.save_figure(
                graph_type="sample_graph", user_id=user_id_str
            )

            logger.info(f"Sample graph saved successfully to: {output_path}")
            return output_path

        except Exception as e:
            logger.error(f"Error saving sample graph: {e}")
            raise
        finally:
            # Always cleanup matplotlib resources
            self.cleanup()

    def validate_data(self, data: Mapping[str, object]) -> bool:
        """
        Validate input data for the sample graph.

        This is an optional helper method that demonstrates how to
        implement data validation for specific graph types.

        Args:
            data: Data dictionary to validate

        Returns:
            True if data is valid, False otherwise
        """
        required_keys = ["x_values", "y_values"]

        # Check for required keys
        for key in required_keys:
            if key not in data:
                logger.warning(f"Missing required key: {key}")
                return False

        # Validate data types and content
        x_values = data.get("x_values")
        y_values = data.get("y_values")

        if not isinstance(x_values, (list, tuple)) or not isinstance(
            y_values, (list, tuple)
        ):
            logger.warning("x_values and y_values must be lists or tuples")
            return False

        if len(x_values) == 0 or len(y_values) == 0:  # pyright: ignore[reportUnknownArgumentType]
            logger.warning("x_values and y_values cannot be empty")
            return False

        if len(x_values) != len(y_values):  # pyright: ignore[reportUnknownArgumentType]
            logger.warning("x_values and y_values must have the same length")
            return False

        return True

    def get_sample_data(self) -> dict[str, object]:
        """
        Generate sample data for testing and demonstration purposes.

        Returns:
            Dictionary with sample data that can be used with this graph
        """
        import random

        # Generate sample data points
        x_values = list(range(1, 11))  # 1 to 10
        y_values = [random.randint(10, 100) for _ in x_values]

        return {
            "x_values": x_values,
            "y_values": y_values,
            "title": "Sample Data Points",
            "user_id": "demo_user",
        }
