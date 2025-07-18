"""
Tests for DataProcessor utility class in TGraph Bot.

This module tests the DataProcessor class that centralizes data extraction
and validation patterns found across multiple graph classes.
"""

import pytest
from collections.abc import Mapping
from unittest.mock import Mock, patch

from src.tgraph_bot.graphs.graph_modules.data_processor import DataProcessor, data_processor


class TestDataProcessor:
    """Test cases for the DataProcessor class."""
    
    def test_init(self) -> None:
        """Test DataProcessor initialization."""
        processor = DataProcessor()
        assert processor is not None
    
    def test_singleton_instance(self) -> None:
        """Test that data_processor singleton is available."""
        assert data_processor is not None
        assert isinstance(data_processor, DataProcessor)


class TestExtractAndValidateData:
    """Test cases for extract_and_validate_data method."""
    
    def test_valid_data_extraction(self) -> None:
        """Test successful data extraction and validation."""
        processor = DataProcessor()
        
        # Mock data structure
        data = {
            "play_history": {
                "data": [{"user": "test_user", "date": "2023-01-01"}],
                "result": "success"
            },
            "other_data": "ignored"
        }
        
        result = processor.extract_and_validate_data(
            data=data,
            data_key="play_history",
            required_keys=["data"],
            context="test"
        )
        
        assert result == data["play_history"]
        assert "data" in result
        assert "result" in result
    
    def test_missing_data_key(self) -> None:
        """Test extraction fails when data key is missing."""
        processor = DataProcessor()
        
        data = {"other_data": "present"}
        
        with pytest.raises(ValueError, match="Invalid test data: Missing required key: data"):
            _ = processor.extract_and_validate_data(
                data=data,
                data_key="play_history",
                required_keys=["data"],
                context="test"
            )
    
    def test_invalid_data_type(self) -> None:
        """Test extraction fails when data is not a dictionary."""
        processor = DataProcessor()
        
        data = {"play_history": "not_a_dict"}
        
        with pytest.raises(ValueError, match="Missing or invalid 'play_history' data in input"):
            _ = processor.extract_and_validate_data(
                data=data,
                data_key="play_history",
                required_keys=["data"],
                context="test"
            )
    
    def test_missing_required_keys(self) -> None:
        """Test extraction fails when required keys are missing."""
        processor = DataProcessor()
        
        data = {
            "play_history": {
                "result": "success"
                # Missing "data" key
            }
        }
        
        with pytest.raises(ValueError, match="Invalid test data: Missing required key: data"):
            _ = processor.extract_and_validate_data(
                data=data,
                data_key="play_history",
                required_keys=["data"],
                context="test"
            )
    
    def test_multiple_required_keys(self) -> None:
        """Test extraction with multiple required keys."""
        processor = DataProcessor()
        
        data = {
            "monthly_plays": {
                "categories": ["Jan", "Feb", "Mar"],
                "series": [10, 20, 30]
            }
        }
        
        result = processor.extract_and_validate_data(
            data=data,
            data_key="monthly_plays",
            required_keys=["categories", "series"],
            context="monthly"
        )
        
        assert result == data["monthly_plays"]
        assert "categories" in result
        assert "series" in result


class TestExtractPlayHistoryData:
    """Test cases for extract_play_history_data method."""
    
    def test_valid_play_history_extraction(self) -> None:
        """Test successful play history data extraction."""
        processor = DataProcessor()
        
        data = {
            "play_history": {
                "data": [{"user": "test", "date": "2023-01-01"}]
            }
        }
        
        result = processor.extract_play_history_data(data)
        
        assert result == data["play_history"]
        assert "data" in result
    
    def test_missing_play_history(self) -> None:
        """Test extraction fails when play_history is missing."""
        processor = DataProcessor()
        
        data = {"other_data": "present"}
        
        with pytest.raises(ValueError, match="Invalid play history data: Missing required key: data"):
            processor.extract_play_history_data(data)
    
    def test_invalid_play_history_data(self) -> None:
        """Test extraction fails when play_history data is invalid."""
        processor = DataProcessor()
        
        data = {
            "play_history": {
                # Missing "data" key
                "result": "success"
            }
        }
        
        with pytest.raises(ValueError, match="Invalid play history data: Missing required key: data"):
            processor.extract_play_history_data(data)


class TestExtractMonthlyPlaysData:
    """Test cases for extract_monthly_plays_data method."""
    
    def test_valid_monthly_plays_extraction(self) -> None:
        """Test successful monthly plays data extraction."""
        processor = DataProcessor()
        
        data = {
            "monthly_plays": {
                "categories": ["Jan", "Feb"],
                "series": [10, 20]
            }
        }
        
        result = processor.extract_monthly_plays_data(data)
        
        assert result == data["monthly_plays"]
        assert "categories" in result
        assert "series" in result
    
    def test_missing_monthly_plays(self) -> None:
        """Test extraction fails when monthly_plays is missing."""
        processor = DataProcessor()
        
        data = {"other_data": "present"}
        
        with pytest.raises(ValueError, match="Invalid monthly plays data: Missing required key: categories"):
            processor.extract_monthly_plays_data(data)
    
    def test_invalid_monthly_plays_data(self) -> None:
        """Test extraction fails when monthly_plays data is invalid."""
        processor = DataProcessor()
        
        data = {
            "monthly_plays": {
                "categories": ["Jan", "Feb"]
                # Missing "series" key
            }
        }
        
        with pytest.raises(ValueError, match="Invalid monthly plays data: Missing required key: series"):
            processor.extract_monthly_plays_data(data)


class TestProcessDataSafely:
    """Test cases for process_data_safely method."""
    
    def test_successful_processing(self) -> None:
        """Test successful data processing."""
        processor = DataProcessor()
        
        # Mock processor function
        def mock_processor(_: Mapping[str, object]) -> list[str]:
            return ["processed_item"]
        
        data = {"test": "data"}
        
        result = processor.process_data_safely(
            data=data,
            processor_func=mock_processor,
            context="test"
        )
        
        assert result == ["processed_item"]
    
    def test_processing_failure_with_fallback(self) -> None:
        """Test processing failure with fallback value."""
        processor = DataProcessor()
        
        # Mock processor function that raises an exception
        def mock_processor(_: Mapping[str, object]) -> list[str]:
            raise ValueError("Processing failed")
        
        data = {"test": "data"}
        fallback = ["fallback_item"]
        
        result = processor.process_data_safely(
            data=data,
            processor_func=mock_processor,
            fallback_value=fallback,
            context="test"
        )
        
        assert result == fallback
    
    def test_processing_failure_without_fallback(self) -> None:
        """Test processing failure without fallback value raises exception."""
        processor = DataProcessor()
        
        # Mock processor function that raises an exception
        def mock_processor(_: Mapping[str, object]) -> list[str]:
            raise ValueError("Processing failed")
        
        data = {"test": "data"}
        
        with pytest.raises(ValueError, match="Failed to process test: Processing failed"):
            processor.process_data_safely(
                data=data,
                processor_func=mock_processor,
                context="test"
            )


class TestProcessPlayHistorySafely:
    """Test cases for process_play_history_safely method."""
    
    @patch('src.tgraph_bot.graphs.graph_modules.data_processor.process_play_history_data')
    def test_successful_play_history_processing(self, mock_process: Mock) -> None:
        """Test successful play history data processing."""
        processor = DataProcessor()
        
        # Mock the process_play_history_data function
        mock_records = [{"user": "test", "date": "2023-01-01"}]
        mock_process.return_value = mock_records
        
        data = {"data": [{"user": "test", "date": "2023-01-01"}]}
        
        result = processor.process_play_history_safely(data)
        
        assert result == mock_records
        mock_process.assert_called_once_with(data)
    
    @patch('src.tgraph_bot.graphs.graph_modules.data_processor.process_play_history_data')
    def test_play_history_processing_failure(self, mock_process: Mock) -> None:
        """Test play history processing failure returns empty list."""
        processor = DataProcessor()
        
        # Mock the process_play_history_data function to raise an exception
        mock_process.side_effect = ValueError("Processing failed")
        
        data = {"data": [{"user": "test", "date": "2023-01-01"}]}
        
        result = processor.process_play_history_safely(data)
        
        assert result == []
        mock_process.assert_called_once_with(data)


class TestExtractAndProcessPlayHistory:
    """Test cases for extract_and_process_play_history method."""
    
    @patch('src.tgraph_bot.graphs.graph_modules.data_processor.process_play_history_data')
    def test_successful_extract_and_process(self, mock_process: Mock) -> None:
        """Test successful extraction and processing of play history data."""
        processor = DataProcessor()
        
        # Mock the process_play_history_data function
        mock_records = [{"user": "test", "date": "2023-01-01"}]
        mock_process.return_value = mock_records
        
        data = {
            "play_history": {
                "data": [{"user": "test", "date": "2023-01-01"}]
            }
        }
        
        validated_data, processed_records = processor.extract_and_process_play_history(data)
        
        assert validated_data == data["play_history"]
        assert processed_records == mock_records
        mock_process.assert_called_once_with(data["play_history"])
    
    def test_extract_and_process_extraction_failure(self) -> None:
        """Test extract and process fails when extraction fails."""
        processor = DataProcessor()
        
        data = {"other_data": "present"}  # Missing play_history
        
        with pytest.raises(ValueError, match="Invalid play history data: Missing required key: data"):
            processor.extract_and_process_play_history(data)
    
    @patch('src.tgraph_bot.graphs.graph_modules.data_processor.process_play_history_data')
    def test_extract_and_process_processing_failure(self, mock_process: Mock) -> None:
        """Test extract and process with processing failure."""
        processor = DataProcessor()
        
        # Mock the process_play_history_data function to raise an exception
        mock_process.side_effect = ValueError("Processing failed")
        
        data = {
            "play_history": {
                "data": [{"user": "test", "date": "2023-01-01"}]
            }
        }
        
        validated_data, processed_records = processor.extract_and_process_play_history(data)
        
        assert validated_data == data["play_history"]
        assert processed_records == []  # Should return empty list on processing failure
        mock_process.assert_called_once_with(data["play_history"])


class TestExtractAndProcessMonthlyPlays:
    """Test cases for extract_and_process_monthly_plays method."""
    
    def test_successful_extract_and_process_monthly(self) -> None:
        """Test successful extraction and processing of monthly plays data."""
        processor = DataProcessor()
        
        data = {
            "monthly_plays": {
                "categories": ["Jan", "Feb"],
                "series": [10, 20]
            }
        }
        
        validated_data, processed_data = processor.extract_and_process_monthly_plays(data)
        
        assert validated_data == data["monthly_plays"]
        assert processed_data == data["monthly_plays"]  # Should be the same for monthly plays
    
    def test_extract_and_process_monthly_extraction_failure(self) -> None:
        """Test extract and process monthly fails when extraction fails."""
        processor = DataProcessor()
        
        data = {"other_data": "present"}  # Missing monthly_plays
        
        with pytest.raises(ValueError, match="Invalid monthly plays data: Missing required key: categories"):
            processor.extract_and_process_monthly_plays(data)


class TestSafeExtractWithFallback:
    """Test cases for safe_extract_with_fallback method."""
    
    def test_successful_extraction_with_fallback(self) -> None:
        """Test successful extraction when fallback is provided."""
        processor = DataProcessor()
        
        data = {
            "play_history": {
                "data": [{"user": "test", "date": "2023-01-01"}]
            }
        }
        
        result = processor.safe_extract_with_fallback(
            data=data,
            data_key="play_history",
            required_keys=["data"],
            fallback_data={"fallback": "data"},
            context="test"
        )
        
        assert result == data["play_history"]
    
    def test_extraction_failure_with_fallback(self) -> None:
        """Test extraction failure returns fallback data."""
        processor = DataProcessor()
        
        data = {"other_data": "present"}  # Missing play_history
        fallback = {"fallback": "data"}
        
        result = processor.safe_extract_with_fallback(
            data=data,
            data_key="play_history",
            required_keys=["data"],
            fallback_data=fallback,
            context="test"
        )
        
        assert result == fallback
    
    def test_extraction_failure_without_fallback(self) -> None:
        """Test extraction failure without fallback raises exception."""
        processor = DataProcessor()
        
        data = {"other_data": "present"}  # Missing play_history
        
        with pytest.raises(ValueError, match="Invalid test data: Missing required key: data"):
            processor.safe_extract_with_fallback(
                data=data,
                data_key="play_history",
                required_keys=["data"],
                context="test"
            )


class TestValidateExtractedData:
    """Test cases for validate_extracted_data method."""
    
    def test_valid_data_validation(self) -> None:
        """Test validation of valid data."""
        processor = DataProcessor()
        
        data = {
            "data": [{"user": "test", "date": "2023-01-01"}],
            "result": "success"
        }
        
        is_valid, error_msg = processor.validate_extracted_data(
            data=data,
            required_keys=["data"],
            context="test"
        )
        
        assert is_valid is True
        assert error_msg == ""
    
    def test_invalid_data_validation(self) -> None:
        """Test validation of invalid data."""
        processor = DataProcessor()
        
        data = {
            "result": "success"
            # Missing "data" key
        }
        
        is_valid, error_msg = processor.validate_extracted_data(
            data=data,
            required_keys=["data"],
            context="test"
        )
        
        assert is_valid is False
        assert "Invalid test data: Missing required key: data" in error_msg
    
    def test_validation_with_multiple_keys(self) -> None:
        """Test validation with multiple required keys."""
        processor = DataProcessor()
        
        data = {
            "categories": ["Jan", "Feb"],
            "series": [10, 20]
        }
        
        is_valid, error_msg = processor.validate_extracted_data(
            data=data,
            required_keys=["categories", "series"],
            context="monthly"
        )
        
        assert is_valid is True
        assert error_msg == ""


class TestIntegrationScenarios:
    """Integration test scenarios for DataProcessor."""
    
    @patch('src.tgraph_bot.graphs.graph_modules.data_processor.process_play_history_data')
    def test_complete_workflow_play_history(self, mock_process: Mock) -> None:
        """Test complete workflow for play history data processing."""
        processor = DataProcessor()
        
        # Mock the process_play_history_data function
        mock_records = [{"user": "test", "date": "2023-01-01"}]
        mock_process.return_value = mock_records
        
        # Complete API response structure
        api_response = {
            "response": {
                "result": "success",
                "data": {
                    "play_history": {
                        "data": [
                            {"user": "test", "date": "2023-01-01"},
                            {"user": "test2", "date": "2023-01-02"}
                        ],
                        "recordsFiltered": 2,
                        "recordsTotal": 2
                    }
                }
            }
        }
        
        # Extract data from nested structure
        data = api_response["response"]["data"]
        assert isinstance(data, dict)
        
        # Process using DataProcessor
        validated_data, processed_records = processor.extract_and_process_play_history(data)
        
        assert "data" in validated_data
        assert processed_records == mock_records
        mock_process.assert_called_once_with(validated_data)
    
    def test_complete_workflow_monthly_plays(self) -> None:
        """Test complete workflow for monthly plays data processing."""
        processor = DataProcessor()
        
        # Complete API response structure
        api_response = {
            "response": {
                "result": "success",
                "data": {
                    "monthly_plays": {
                        "categories": ["Jan", "Feb", "Mar"],
                        "series": [10, 20, 30]
                    }
                }
            }
        }
        
        # Extract data from nested structure
        data = api_response["response"]["data"]
        assert isinstance(data, dict)
        
        # Process using DataProcessor
        validated_data, processed_data = processor.extract_and_process_monthly_plays(data)
        
        assert "categories" in validated_data
        assert "series" in validated_data
        assert processed_data == validated_data
    
    def test_error_handling_chain(self) -> None:
        """Test error handling through the entire processing chain."""
        processor = DataProcessor()
        
        # Invalid API response structure
        api_response = {
            "response": {
                "result": "error",
                "data": {
                    "play_history": {
                        # Missing "data" key
                        "result": "success"
                    }
                }
            }
        }
        
        # Extract data from nested structure
        data = api_response["response"]["data"]
        assert isinstance(data, dict)
        
        # Should raise ValueError for missing required key
        with pytest.raises(ValueError, match="Invalid play history data: Missing required key: data"):
            processor.extract_and_process_play_history(data)