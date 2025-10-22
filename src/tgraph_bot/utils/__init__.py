"""Utility modules for TGraph Bot."""

from tgraph_bot.utils.errors import (
    ConfigurationError,
    GraphGenerationError,
    RateLimitError,
    TautulliAPIError,
    TGraphBotError,
)
from tgraph_bot.utils.logging import (
    command_name,
    get_logger,
    is_sensitive_field,
    log_api_request,
    log_operation_complete,
    log_operation_start,
    mask_sensitive_dict,
    mask_sensitive_value,
    operation_id,
    setup_logging,
    user_id,
)

__all__ = [
    # Exceptions
    "TGraphBotError",
    "ConfigurationError",
    "TautulliAPIError",
    "GraphGenerationError",
    "RateLimitError",
    # Logging
    "setup_logging",
    "get_logger",
    "mask_sensitive_value",
    "mask_sensitive_dict",
    "is_sensitive_field",
    "log_api_request",
    "log_operation_start",
    "log_operation_complete",
    # Context variables
    "operation_id",
    "user_id",
    "command_name",
]
