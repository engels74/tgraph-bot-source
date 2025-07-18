"""
Data processing utility for TGraph Bot graph modules.

This module provides a centralized DataProcessor class that extracts and validates
data from Tautulli API responses, eliminating duplicate data extraction patterns
found across multiple graph classes.
"""

import logging
from collections.abc import Mapping
from typing import TYPE_CHECKING, cast, TypeVar, Callable

from .utils import (
    validate_graph_data,
    process_play_history_data,
    ProcessedRecords,
)

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)

T = TypeVar("T")


class DataProcessor:
    """
    Centralized data processing utility for graph modules.
    
    This class provides standardized methods for extracting and validating
    data from Tautulli API responses, eliminating code duplication across
    multiple graph classes.
    """
    
    def __init__(self) -> None:
        """Initialize the DataProcessor."""
        pass
    
    def extract_and_validate_data(
        self,
        data: Mapping[str, object],
        data_key: str,
        required_keys: list[str],
        context: str = "graph"
    ) -> Mapping[str, object]:
        """
        Extract and validate data from a Tautulli API response.
        
        This method implements the common pattern found across all graph classes
        for extracting data from API responses and validating required fields.
        
        Args:
            data: Dictionary containing the full data structure from Tautulli API
            data_key: Key to extract from the data structure (e.g., "play_history", "monthly_plays")
            required_keys: List of keys that must be present in the extracted data
            context: Context string for error messages (e.g., "play history", "monthly graph")
            
        Returns:
            Validated data mapping
            
        Raises:
            ValueError: If data is invalid or missing required fields
        """
        # Step 1: Extract the requested data from the full data structure
        extracted_data_raw = data.get(data_key, {})
        if not isinstance(extracted_data_raw, dict):
            raise ValueError(f"Missing or invalid '{data_key}' data in input")
        
        # Step 2: Cast to the proper type for type checker
        extracted_data = cast(Mapping[str, object], extracted_data_raw)
        
        # Step 3: Validate the extracted data structure
        is_valid, error_msg = validate_graph_data(extracted_data, required_keys)
        if not is_valid:
            raise ValueError(f"Invalid {context} data: {error_msg}")
        
        return extracted_data
    
    def extract_play_history_data(self, data: Mapping[str, object]) -> Mapping[str, object]:
        """
        Extract and validate play history data from Tautulli API response.
        
        This method implements the most common data extraction pattern found
        across Tautulli graph classes.
        
        Args:
            data: Dictionary containing the full data structure from Tautulli API
            
        Returns:
            Validated play history data mapping
            
        Raises:
            ValueError: If data is invalid or missing required fields
        """
        return self.extract_and_validate_data(
            data=data,
            data_key="play_history",
            required_keys=["data"],
            context="play history"
        )
    
    def extract_monthly_plays_data(self, data: Mapping[str, object]) -> Mapping[str, object]:
        """
        Extract and validate monthly plays data from Tautulli API response.
        
        This method implements the data extraction pattern used by the
        monthly play count graph.
        
        Args:
            data: Dictionary containing the full data structure from Tautulli API
            
        Returns:
            Validated monthly plays data mapping
            
        Raises:
            ValueError: If data is invalid or missing required fields
        """
        return self.extract_and_validate_data(
            data=data,
            data_key="monthly_plays",
            required_keys=["categories", "series"],
            context="monthly plays"
        )
    
    def process_data_safely(
        self,
        data: Mapping[str, object],
        processor_func: Callable[[Mapping[str, object]], T],
        fallback_value: T | None = None,
        context: str = "data"
    ) -> T:
        """
        Process data using a processor function with error handling.
        
        This method implements the common pattern found across graph classes
        for processing data with graceful error handling.
        
        Args:
            data: Data to process
            processor_func: Function to process the data
            fallback_value: Value to return if processing fails
            context: Context string for error messages
            
        Returns:
            Processed data or fallback value if processing fails
            
        Raises:
            ValueError: If processing fails and no fallback value is provided
        """
        try:
            result = processor_func(data)
            logger.info(f"Successfully processed {context}")
            return result
        except Exception as e:
            logger.error(f"Error processing {context}: {e}")
            if fallback_value is not None:
                return fallback_value
            raise ValueError(f"Failed to process {context}: {e}") from e
    
    def process_play_history_safely(
        self, play_history_data: Mapping[str, object]
    ) -> ProcessedRecords:
        """
        Process play history data with error handling.
        
        This method implements the common pattern found across all Tautulli graph classes
        for processing play history data with graceful error handling.
        
        Args:
            play_history_data: Validated play history data mapping
            
        Returns:
            List of processed play history records, empty list if processing fails
        """
        return self.process_data_safely(
            data=play_history_data,
            processor_func=process_play_history_data,
            fallback_value=[],
            context="play history data"
        )
    
    def extract_and_process_play_history(
        self, data: Mapping[str, object]
    ) -> tuple[Mapping[str, object], ProcessedRecords]:
        """
        Extract and process play history data in a single operation.
        
        This method combines the common sequence of extract_play_history_data()
        and process_play_history_safely() calls found across all graph classes.
        
        Args:
            data: Dictionary containing the full data structure from Tautulli API
            
        Returns:
            Tuple of (validated_data, processed_records)
            
        Raises:
            ValueError: If data extraction fails
        """
        # Step 1: Extract and validate play history data
        play_history_data = self.extract_play_history_data(data)
        
        # Step 2: Process the play history data safely
        processed_records = self.process_play_history_safely(play_history_data)
        
        return play_history_data, processed_records
    
    def extract_and_process_monthly_plays(
        self, data: Mapping[str, object]
    ) -> tuple[Mapping[str, object], Mapping[str, object]]:
        """
        Extract and process monthly plays data in a single operation.
        
        This method provides a standardized interface for monthly play data
        extraction and processing.
        
        Args:
            data: Dictionary containing the full data structure from Tautulli API
            
        Returns:
            Tuple of (validated_data, validated_data) - returns same data twice
            for consistency with other methods
            
        Raises:
            ValueError: If data extraction fails
        """
        # Step 1: Extract and validate monthly plays data
        monthly_plays_data = self.extract_monthly_plays_data(data)
        
        # Monthly plays data doesn't require additional processing like play history
        # so we return the same data twice for consistent interface
        return monthly_plays_data, monthly_plays_data
    
    def safe_extract_with_fallback(
        self,
        data: Mapping[str, object],
        data_key: str,
        required_keys: list[str],
        fallback_data: Mapping[str, object] | None = None,
        context: str = "graph"
    ) -> Mapping[str, object]:
        """
        Extract and validate data with fallback support.
        
        This method provides a safe extraction interface that can return
        fallback data if the primary extraction fails.
        
        Args:
            data: Dictionary containing the full data structure from Tautulli API
            data_key: Key to extract from the data structure
            required_keys: List of keys that must be present in the extracted data
            fallback_data: Data to return if extraction fails
            context: Context string for error messages
            
        Returns:
            Validated data mapping or fallback data
            
        Raises:
            ValueError: If extraction fails and no fallback data is provided
        """
        try:
            return self.extract_and_validate_data(
                data=data,
                data_key=data_key,
                required_keys=required_keys,
                context=context
            )
        except ValueError as e:
            logger.warning(f"Failed to extract {context} data: {e}")
            if fallback_data is not None:
                logger.info(f"Using fallback data for {context}")
                return fallback_data
            raise
    
    def validate_extracted_data(
        self,
        data: Mapping[str, object],
        required_keys: list[str],
        context: str = "data"
    ) -> tuple[bool, str]:
        """
        Validate extracted data has required keys.
        
        This method provides a simple interface to the validate_graph_data utility
        with enhanced error context.
        
        Args:
            data: Data to validate
            required_keys: List of keys that must be present
            context: Context string for error messages
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        is_valid, error_msg = validate_graph_data(data, required_keys)
        if not is_valid:
            return False, f"Invalid {context} data: {error_msg}"
        return True, ""


# Create a singleton instance for convenient access
data_processor = DataProcessor()