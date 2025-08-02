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

T = TypeVar("T")

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
            raise ValueError(
                f"Invalid format for '{data_key}' in {context}: expected dict"
            )

        if required_keys:
            for key in required_keys:
                if key not in extracted_data:
                    raise ValueError(
                        f"Missing required key '{key}' in {data_key} for {context}"
                    )

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
            raise ValueError(
                f"Insufficient data for {context}: got {len(data_list)}, expected at least {min_length}"
            )

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
            data, "monthly_plays", context="monthly plays data extraction"
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
        if hasattr(data, "data"):  # PlayHistoryData type
            data_dict = cast(dict[str, object], data)
            if "data" in data_dict:
                raw_data = data_dict["data"]
                if isinstance(raw_data, list):
                    # Cast to list[object] after validation
                    list_data = cast(list[object], raw_data)
                    records = self.validate_list_data(
                        list_data, context="play history records", min_length=0
                    )
                else:
                    records = []
            else:
                records = []
        else:  # Regular dict
            data_mapping = cast(Mapping[str, object], data)
            if "data" not in data_mapping:
                # Check for alternative data structures that Tautulli API might return
                possible_keys = [
                    "response",
                    "result",
                    "play_history",
                    "history",
                    "records",
                ]
                found_key = None
                for key in possible_keys:
                    if key in data_mapping:
                        found_key = key
                        break

                if found_key:
                    logger.warning(f"'data' key not found, using '{found_key}' instead")
                    raw_data = data_mapping[found_key]
                else:
                    # If no data is found, return empty records instead of raising an error
                    logger.warning(
                        "No data found in API response, returning empty records"
                    )
                    records = []
                    raw_data = []
            else:
                raw_data = data_mapping["data"]

            if raw_data and isinstance(raw_data, list):
                # Cast to list[object] after validation
                list_data = cast(list[object], raw_data)
                records = self.validate_list_data(
                    list_data, context="play history records", min_length=0
                )
            elif raw_data and not isinstance(raw_data, list):
                # If raw_data is a dict, try to extract a list from it
                if isinstance(raw_data, dict):
                    # Try common keys that might contain the actual list data
                    for list_key in ["data", "records", "history", "play_history"]:
                        if list_key in raw_data:
                            nested_data: object = raw_data[list_key]  # pyright: ignore[reportUnknownVariableType]
                            if isinstance(nested_data, list):
                                logger.info(
                                    f"Found list data nested under '{list_key}' key"
                                )
                                list_data = cast(list[object], nested_data)
                                records = self.validate_list_data(
                                    list_data,
                                    context="play history records",
                                    min_length=0,
                                )
                                break
                    else:
                        # No valid list found in nested structure
                        logger.warning(
                            "No list data found in nested structure, returning empty records"
                        )
                        records = []
                else:
                    # raw_data is neither list nor dict
                    raise ValueError(
                        "Invalid format for data in play history extraction: expected list or dict containing list"
                    )
            else:
                # Empty or None data
                records = []

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

    def extract_and_process_play_history_enhanced(
        self, data: Mapping[str, object] | PlayHistoryData
    ) -> tuple[Sequence[Mapping[str, object]], ProcessedRecords]:
        """
        Enhanced version of extract_and_process_play_history with resolution field fallback logic.
        
        This method provides fallback support for resolution fields by attempting to
        combine width/height fields when the primary resolution fields are not available.
        
        Args:
            data: API response data or PlayHistoryData
            
        Returns:
            Tuple of (raw_records, processed_records) with enhanced resolution handling
        """
        if hasattr(data, "data"):  # PlayHistoryData type
            data_dict = cast(dict[str, object], data)
            if "data" in data_dict:
                raw_data = data_dict["data"]
                if isinstance(raw_data, list):
                    # Cast to list[object] after validation
                    list_data = cast(list[object], raw_data)
                    records = self.validate_list_data(
                        list_data, context="play history records", min_length=0
                    )
                else:
                    records = []
            else:
                records = []
        else:  # Regular dict
            data_mapping = cast(Mapping[str, object], data)
            if "data" not in data_mapping:
                # Check for alternative data structures that Tautulli API might return
                possible_keys = [
                    "response",
                    "result",
                    "play_history",
                    "history",
                    "records",
                ]
                found_key = None
                for key in possible_keys:
                    if key in data_mapping:
                        found_key = key
                        break

                if found_key:
                    logger.warning(f"'data' key not found, using '{found_key}' instead")
                    raw_data = data_mapping[found_key]
                else:
                    # If no data is found, return empty records instead of raising an error
                    logger.warning(
                        "No data found in API response, returning empty records"
                    )
                    records = []
                    raw_data = []
            else:
                raw_data = data_mapping["data"]

            if raw_data and isinstance(raw_data, list):
                # Cast to list[object] after validation
                list_data = cast(list[object], raw_data)
                records = self.validate_list_data(
                    list_data, context="play history records", min_length=0
                )
            elif raw_data and not isinstance(raw_data, list):
                # If raw_data is a dict, try to extract a list from it
                if isinstance(raw_data, dict):
                    # Try common keys that might contain the actual list data
                    for list_key in ["data", "records", "history", "play_history"]:
                        if list_key in raw_data:
                            nested_data: object = raw_data[list_key]  # pyright: ignore[reportUnknownVariableType]
                            if isinstance(nested_data, list):
                                logger.info(
                                    f"Found list data nested under '{list_key}' key"
                                )
                                list_data = cast(list[object], nested_data)
                                records = self.validate_list_data(
                                    list_data,
                                    context="play history records",
                                    min_length=0,
                                )
                                break
                    else:
                        # No valid list found in nested structure
                        logger.warning(
                            "No list data found in nested structure, returning empty records"
                        )
                        records = []
                else:
                    # raw_data is neither list nor dict
                    raise ValueError(
                        "Invalid format for data in play history extraction: expected list or dict containing list"
                    )
            else:
                # Empty or None data
                records = []

        # Process raw records into properly typed ProcessedPlayRecord objects using enhanced function
        from ..utils.utils import process_play_history_data_enhanced

        # Convert records back to dict format for the utility function
        record_dicts: list[dict[str, object]] = []
        for record in records:  # pyright: ignore[reportUnknownVariableType] # validated sequence
            if isinstance(record, Mapping):
                # Cast to proper type after validation
                record_mapping = cast(Mapping[str, object], record)
                record_dicts.append(dict(record_mapping))

        raw_data_dict: dict[str, list[dict[str, object]]] = {"data": record_dicts}
        processed_records = process_play_history_data_enhanced(raw_data_dict)

        return records, processed_records  # pyright: ignore[reportUnknownVariableType] # validated sequence return

    async def extract_and_process_play_history_with_resolution(
        self, data: Mapping[str, object] | PlayHistoryData
    ) -> tuple[Sequence[Mapping[str, object]], ProcessedRecords]:
        """
        Enhanced version that fetches resolution data from media metadata and joins with play history.
        
        This method:
        1. Extracts play history (same as standard method)
        2. Identifies unique rating_keys from the play data
        3. Fetches media metadata for those items to get resolution info
        4. Joins resolution data with play records
        
        Args:
            data: API response data or PlayHistoryData
            
        Returns:
            Tuple of (raw_records, processed_records) with resolution data from metadata
        """
        # Step 1: Get the basic play history data (without resolution)
        records, _ = self.extract_and_process_play_history(data)
        
        # Step 2: Extract unique rating_keys from play records
        rating_keys: set[str] = set()
        for record in records:
            if isinstance(record, dict) and "rating_key" in record:
                rating_key = record["rating_key"]
                if rating_key:
                    rating_keys.add(str(rating_key))
        
        logger.info(f"Found {len(rating_keys)} unique media items in play history")
        
        # Step 3: Fetch media metadata for resolution information
        from .data_fetcher import DataFetcher
        from tgraph_bot.config.manager import ConfigManager
        from tgraph_bot.utils.cli.paths import PathConfig
        
        resolution_cache: dict[str, dict[str, str]] = {}
        
        try:
            # Load config to get Tautulli connection details
            path_config = PathConfig()
            config_path = path_config.config_file
            config_manager = ConfigManager()
            config = config_manager.load_config(config_path)
            
            # Fetch resolution data for each unique rating_key
            async with DataFetcher(
                base_url=config.services.tautulli.url,
                api_key=config.services.tautulli.api_key
            ) as fetcher:
                
                # Batch process rating keys (limit API calls)
                for rating_key in list(rating_keys)[:100]:  # Limit to avoid too many API calls
                    try:
                        metadata = await fetcher.get_media_metadata(int(rating_key))
                        
                        # Extract resolution info from metadata
                        video_resolution = "unknown"
                        stream_video_resolution = "unknown"
                        
                        if isinstance(metadata, dict):
                            # Check media_info field which contains the actual resolution data
                            media_info = metadata.get("media_info")
                            if media_info and isinstance(media_info, list) and media_info:
                                # Get the first media info item (there may be multiple parts)
                                media_data = media_info[0]
                                if isinstance(media_data, dict):
                                    # Extract source resolution from media_info
                                    for field_name in ["video_resolution", "video_full_resolution"]:
                                        if field_name in media_data:
                                            resolution_value = media_data[field_name]
                                            if resolution_value and str(resolution_value) != "unknown":
                                                # Convert to standard format (e.g., "1080" -> "1920x1080")
                                                if str(resolution_value) == "1080":
                                                    width = media_data.get("width", 1920)
                                                    height = media_data.get("height", 1080)
                                                    video_resolution = f"{width}x{height}"
                                                elif str(resolution_value) == "720":
                                                    width = media_data.get("width", 1280)
                                                    height = media_data.get("height", 720)
                                                    video_resolution = f"{width}x{height}"
                                                elif str(resolution_value) == "480":
                                                    width = media_data.get("width", 720)
                                                    height = media_data.get("height", 480)
                                                    video_resolution = f"{width}x{height}"
                                                elif str(resolution_value) == "2160":
                                                    width = media_data.get("width", 3840)
                                                    height = media_data.get("height", 2160)
                                                    video_resolution = f"{width}x{height}"
                                                else:
                                                    # Use width x height directly
                                                    width = media_data.get("width")
                                                    height = media_data.get("height")
                                                    if width and height:
                                                        video_resolution = f"{width}x{height}"
                                                    else:
                                                        video_resolution = str(resolution_value)
                                                break
                                    
                                    # For stream resolution, use the same as source resolution for now
                                    # (stream resolution would come from active session data, not historical metadata)
                                    stream_video_resolution = video_resolution
                            
                            # Fallback: try direct fields in metadata (unlikely to have data based on our testing)
                            if video_resolution == "unknown":
                                for field_name in ["video_resolution", "resolution", "video_full_resolution"]:
                                    if field_name in metadata:
                                        resolution_value = metadata[field_name]
                                        if resolution_value and str(resolution_value) != "unknown":
                                            video_resolution = str(resolution_value)
                                            break
                                
                                # Try to construct from width/height in main metadata
                                if video_resolution == "unknown":
                                    width = metadata.get("width")
                                    height = metadata.get("height")
                                    if width and height:
                                        try:
                                            w = int(width)
                                            h = int(height)
                                            if w > 0 and h > 0:
                                                video_resolution = f"{w}x{h}"
                                        except (ValueError, TypeError):
                                            pass
                        
                        resolution_cache[rating_key] = {
                            "video_resolution": video_resolution,
                            "stream_video_resolution": stream_video_resolution
                        }
                        
                    except Exception as e:
                        logger.warning(f"Failed to fetch metadata for rating_key {rating_key}: {e}")
                        resolution_cache[rating_key] = {
                            "video_resolution": "unknown",
                            "stream_video_resolution": "unknown"
                        }
                        
        except Exception as e:
            logger.error(f"Failed to fetch resolution metadata: {e}")
            # Fall back to using unknown values
            for rating_key in rating_keys:
                resolution_cache[rating_key] = {
                    "video_resolution": "unknown", 
                    "stream_video_resolution": "unknown"
                }
        
        logger.info(f"Fetched resolution data for {len(resolution_cache)} media items")
        
        # Step 4: Process records with enhanced resolution data
        from ..utils.utils import process_play_history_data_enhanced
        
        # Convert records to dict format and add resolution data
        enriched_record_dicts: list[dict[str, object]] = []
        for record in records:
            if isinstance(record, dict):
                # Copy the original record
                enriched_record = dict(record)
                
                # Add resolution data from metadata cache
                rating_key = str(record.get("rating_key", ""))
                if rating_key in resolution_cache:
                    enriched_record.update(resolution_cache[rating_key])
                else:
                    enriched_record.update({
                        "video_resolution": "unknown",
                        "stream_video_resolution": "unknown"
                    })
                
                enriched_record_dicts.append(enriched_record)
        
        # Process the enriched data
        enriched_raw_data = {"data": enriched_record_dicts}
        processed_records = process_play_history_data_enhanced(enriched_raw_data)
        
        logger.info(f"Enhanced processing with resolution data completed: {len(processed_records)} records")
        
        return records, processed_records

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
            return (
                False,
                f"Invalid {context} data: {str(e).replace(f'Invalid data format for {context}: expected dict', 'Missing required key').replace('Missing required key ', 'Missing required key: ')}",
            )

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
                context="monthly plays extraction",
            )
            # For now, processed data is the same as validated data
            return validated_data, validated_data
        except ValueError as e:
            raise ValueError(
                f"Invalid monthly plays data: {str(e).replace('Missing required key ', 'Missing required key: ')}"
            )

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
            return self.extract_and_validate_data(
                data, data_key, required_keys, context
            )
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
            data, "play_history", context="play history data extraction"
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
