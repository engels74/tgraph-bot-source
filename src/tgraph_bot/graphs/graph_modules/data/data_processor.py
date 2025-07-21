"""
Data processor for TGraph Bot graph generation.

This module provides centralized data extraction and validation patterns
used across multiple graph classes.
"""

from __future__ import annotations

import logging
from typing import Callable, TypeVar, TYPE_CHECKING, cast
from collections.abc import Mapping, Sequence

if TYPE_CHECKING:
    from .data_fetcher import PlayHistoryData
    from ..utils.utils import ProcessedRecords

T = TypeVar('T')

logger = logging.getLogger(__name__)


class DataProcessor:
    """Centralized data processing utilities for graph generation."""

    def extract_and_validate_data(
        self,
        data: Mapping[str, object],
        data_key: str,
        required_keys: list[str] | None = None,
        context: str = "data processing",
    ) -> Mapping[str, object]:
        """
        Extract and validate data from a nested dictionary.
        
        Args:
            data: The data dictionary to extract from
            data_key: The key to extract data from
            required_keys: List of required keys in the extracted data
            context: Context string for error messages
            
        Returns:
            The extracted and validated data
            
        Raises:
            ValueError: If data validation fails
        """
        if data_key not in data:
            raise ValueError(f"Missing '{data_key}' in {context}")
            
        extracted_data = data[data_key]
        if not isinstance(extracted_data, dict):
            raise ValueError(f"Invalid format for '{data_key}' in {context}: expected dict")
            
        if required_keys:
            for key in required_keys:
                if key not in extracted_data:
                    raise ValueError(f"Missing required key '{key}' in {data_key} for {context}")
                    
        return cast(Mapping[str, object], extracted_data)

    def validate_list_data(
        self,
        data: object,
        context: str = "list validation",
        min_length: int = 0,
    ) -> Sequence[Mapping[str, object]]:
        """
        Validate that data is a list and meets minimum length requirements.
        
        Args:
            data: The data to validate
            context: Context string for error messages
            min_length: Minimum required length
            
        Returns:
            The validated list
            
        Raises:
            ValueError: If validation fails
        """
        if not isinstance(data, list):
            raise ValueError(f"Invalid data format for {context}: expected list")
            
        # Type-safe operations after validation
        data_list = cast(list[object], data)
        if len(data_list) < min_length:
            raise ValueError(f"Insufficient data for {context}: got {len(data_list)}, expected at least {min_length}")

        # Validate that all items are dictionaries
        validated_items: list[Mapping[str, object]] = []
        for item in data_list:
            if isinstance(item, dict):
                validated_items.append(cast(Mapping[str, object], item))
        
        return validated_items

    def validate_dict_data(
        self,
        data: object,
        required_keys: list[str] | None = None,
        context: str = "dict validation",
    ) -> Mapping[str, object]:
        """
        Validate that data is a dictionary and has required keys.
        
        Args:
            data: The data to validate
            required_keys: List of required keys
            context: Context string for error messages
            
        Returns:
            The validated dictionary
            
        Raises:
            ValueError: If validation fails
        """
        if not isinstance(data, dict):
            raise ValueError(f"Invalid data format for {context}: expected dict")
            
        if required_keys:
            for key in required_keys:
                if key not in data:
                    raise ValueError(f"Missing required key '{key}' in {context}")
                    
        return cast(Mapping[str, object], data)

    def safe_get_nested(
        self,
        data: Mapping[str, object],
        keys: list[str],
        default: object = None,
    ) -> object:
        """
        Safely extract nested data using a list of keys.
        
        Args:
            data: The data dictionary
            keys: List of keys to traverse
            default: Default value if any key is missing
            
        Returns:
            The extracted value or default
        """
        current: object = data
        for key in keys:
            if not isinstance(current, dict) or key not in current:
                return default
            # We've already checked that current is a dict
            # This is a safe operation since we've validated current is a dict
            current_dict = current  # pyright: ignore[reportUnknownVariableType] # validated as dict above
            current = current_dict[key]  # pyright: ignore[reportUnknownVariableType] # nested dict access
        return current  # pyright: ignore[reportUnknownVariableType] # nested object extraction

    def extract_monthly_plays_data(
        self, data: Mapping[str, object]
    ) -> Mapping[str, object]:
        """
        Extract monthly plays data from API response.
        
        Args:
            data: API response data
            
        Returns:
            Extracted monthly plays data
        """
        return self.extract_and_validate_data(
            data, 
            "monthly_plays", 
            context="monthly plays data extraction"
        )

    def extract_and_process_play_history(
        self, data: Mapping[str, object] | PlayHistoryData
    ) -> tuple[Sequence[Mapping[str, object]], ProcessedRecords]:
        """
        Extract and process play history data from API response.
        
        Args:
            data: API response data or PlayHistoryData
            
        Returns:
            Tuple of (raw_records, processed_records)
        """
        if hasattr(data, 'data'):  # PlayHistoryData type
            data_dict = cast(dict[str, object], data)
            if 'data' in data_dict:
                raw_data = data_dict['data']
                if isinstance(raw_data, list):
                    # Cast to list[object] after validation
                    list_data = cast(list[object], raw_data)
                    records = self.validate_list_data(
                        list_data,
                        context="play history records",
                        min_length=0
                    )
                else:
                    records = []
            else:
                records = []
        else:  # Regular dict
            data_mapping = cast(Mapping[str, object], data)
            if "data" not in data_mapping:
                raise ValueError("Missing 'data' in play history extraction")
            raw_data = data_mapping["data"]
            if isinstance(raw_data, list):
                # Cast to list[object] after validation
                list_data = cast(list[object], raw_data)
                records = self.validate_list_data(
                    list_data,
                    context="play history records",
                    min_length=0
                )
            else:
                raise ValueError("Invalid format for 'data' in play history extraction: expected list")
        
        # Process raw records into properly typed ProcessedPlayRecord objects
        from ..utils.utils import process_play_history_data
        
        # Convert records back to dict format for the utility function
        record_dicts: list[dict[str, object]] = []
        for record in records:  # pyright: ignore[reportUnknownVariableType] # validated sequence
            if isinstance(record, Mapping):
                # Cast to proper type after validation
                record_mapping = cast(Mapping[str, object], record)
                record_dicts.append(dict(record_mapping))

        raw_data_dict: dict[str, list[dict[str, object]]] = {"data": record_dicts}
        processed_records = process_play_history_data(raw_data_dict)

        return records, processed_records  # pyright: ignore[reportUnknownVariableType] # validated sequence return

    def validate_extracted_data(
        self,
        data: Mapping[str, object],
        required_keys: list[str] | None = None,
        context: str = "data validation",
    ) -> tuple[bool, str]:
        """
        Validate extracted data and return validation status.
        
        Args:
            data: The data to validate
            required_keys: List of required keys
            context: Context string for error messages
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            _ = self.validate_dict_data(data, required_keys, context)
            return True, ""
        except ValueError as e:
            return False, f"Invalid {context} data: {str(e).replace(f'Invalid data format for {context}: expected dict', 'Missing required key').replace(f'Missing required key ', 'Missing required key: ')}"

    def extract_and_process_monthly_plays(
        self, data: Mapping[str, object]
    ) -> tuple[Mapping[str, object], Mapping[str, object]]:
        """
        Extract and process monthly plays data from API response.
        
        Args:
            data: API response data
            
        Returns:
            Tuple of (validated_data, processed_data)
        """
        try:
            validated_data = self.extract_and_validate_data(
                data,
                "monthly_plays",
                required_keys=["categories", "series"],
                context="monthly plays extraction"
            )
            # For now, processed data is the same as validated data
            return validated_data, validated_data
        except ValueError as e:
            raise ValueError(f"Invalid monthly plays data: {str(e).replace('Missing required key ', 'Missing required key: ')}")

    def safe_extract_with_fallback(
        self,
        data: Mapping[str, object],
        data_key: str,
        required_keys: list[str] | None = None,
        fallback_data: Mapping[str, object] | None = None,
        context: str = "data extraction with fallback",
    ) -> Mapping[str, object]:
        """
        Extract data with fallback support if extraction fails.
        
        Args:
            data: The data dictionary to extract from
            data_key: The key to extract data from
            required_keys: List of required keys in the extracted data
            fallback_data: Fallback data to use if extraction fails
            context: Context string for error messages
            
        Returns:
            The extracted data or fallback data
        """
        try:
            return self.extract_and_validate_data(data, data_key, required_keys, context)
        except ValueError:
            if fallback_data is not None:
                return fallback_data
            raise

    def extract_play_history_data(
        self, data: Mapping[str, object]
    ) -> Mapping[str, object]:
        """
        Extract play history data from API response.
        
        Args:
            data: API response data
            
        Returns:
            Extracted play history data
        """
        return self.extract_and_validate_data(
            data,
            "play_history",
            context="play history data extraction"
        )

    def process_data_safely(
        self,
        data: Mapping[str, object],
        processing_function: Callable[..., object],
        context: str = "data processing",
        **kwargs: object,
    ) -> object:
        """
        Process data safely with error handling.
        
        Args:
            data: Data to process
            processing_function: Function to use for processing
            context: Context string for error messages
            **kwargs: Additional arguments for processing function
            
        Returns:
            Processed data
        """
        try:
            return processing_function(data, **kwargs)
        except Exception as e:
            raise ValueError(f"Error in {context}: {str(e)}")

    def process_play_history_safely(
        self, data: Mapping[str, object]
    ) -> tuple[Sequence[Mapping[str, object]], ProcessedRecords]:
        """
        Process play history data safely with error handling.
        
        Args:
            data: Play history data to process
            
        Returns:
            Tuple of (raw_records, processed_records)
        """
        try:
            return self.extract_and_process_play_history(data)
        except Exception as e:
            raise ValueError(f"Error processing play history: {str(e)}")


# Singleton instance for convenience
data_processor = DataProcessor()