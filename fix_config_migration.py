#!/usr/bin/env python3
"""
Script to fix configuration migration issues in test files.

This script systematically replaces old flat configuration constructors
and attribute access patterns with the new nested structure.
"""

import re
import os
from pathlib import Path
from typing import List, Tuple


def find_test_files() -> List[Path]:
    """Find all test files that need to be updated."""
    test_dirs = ["tests/integration", "tests/unit", "tests/utils"]
    test_files = []
    
    for test_dir in test_dirs:
        if os.path.exists(test_dir):
            for root, dirs, files in os.walk(test_dir):
                for file in files:
                    if file.endswith(".py") and file.startswith("test_"):
                        test_files.append(Path(root) / file)
    
    return test_files


def fix_constructor_calls(content: str) -> str:
    """Fix TGraphBotConfig constructor calls to use helper function."""
    
    # Pattern to match TGraphBotConfig constructor with old flat parameters
    pattern = r'TGraphBotConfig\(\s*\n?(\s*(?:TAUTULLI_API_KEY|TAUTULLI_URL|DISCORD_TOKEN|CHANNEL_ID|ENABLE_|ANNOTATE_|TV_COLOR|MOVIE_COLOR|GRAPH_|UPDATE_DAYS|KEEP_DAYS|TIME_RANGE_|CENSOR_|LANGUAGE)[^)]*)\)'
    
    def replace_constructor(match):
        params_text = match.group(1)
        
        # Extract parameter assignments
        param_lines = []
        for line in params_text.split('\n'):
            line = line.strip()
            if line and '=' in line and not line.startswith('#'):
                param_lines.append(line.rstrip(','))
        
        if not param_lines:
            return match.group(0)  # Return original if no params found
        
        # Build replacement using helper function
        replacement = "create_test_config_with_overrides(\n"
        for param_line in param_lines:
            replacement += f"                {param_line},\n"
        replacement += "            )"
        
        return replacement
    
    return re.sub(pattern, replace_constructor, content, flags=re.MULTILINE | re.DOTALL)


def fix_attribute_access(content: str) -> str:
    """Fix attribute access to use nested structure."""
    
    # Mapping of old flat attributes to new nested paths
    attribute_mapping = {
        'TAUTULLI_API_KEY': 'services.tautulli.api_key',
        'TAUTULLI_URL': 'services.tautulli.url',
        'DISCORD_TOKEN': 'services.discord.token',
        'CHANNEL_ID': 'services.discord.channel_id',
        'DISCORD_TIMESTAMP_FORMAT': 'services.discord.timestamp_format',
        'UPDATE_DAYS': 'automation.scheduling.update_days',
        'FIXED_UPDATE_TIME': 'automation.scheduling.fixed_update_time',
        'KEEP_DAYS': 'automation.data_retention.keep_days',
        'TIME_RANGE_DAYS': 'data_collection.time_ranges.days',
        'TIME_RANGE_MONTHS': 'data_collection.time_ranges.months',
        'CENSOR_USERNAMES': 'data_collection.privacy.censor_usernames',
        'LANGUAGE': 'system.localization.language',
        'ENABLE_DAILY_PLAY_COUNT': 'graphs.features.enabled_types.daily_play_count',
        'ENABLE_PLAY_COUNT_BY_DAYOFWEEK': 'graphs.features.enabled_types.play_count_by_dayofweek',
        'ENABLE_PLAY_COUNT_BY_HOUROFDAY': 'graphs.features.enabled_types.play_count_by_hourofday',
        'ENABLE_TOP_10_PLATFORMS': 'graphs.features.enabled_types.top_10_platforms',
        'ENABLE_TOP_10_USERS': 'graphs.features.enabled_types.top_10_users',
        'ENABLE_PLAY_COUNT_BY_MONTH': 'graphs.features.enabled_types.play_count_by_month',
        'ENABLE_MEDIA_TYPE_SEPARATION': 'graphs.features.media_type_separation',
        'ENABLE_STACKED_BAR_CHARTS': 'graphs.features.stacked_bar_charts',
        'GRAPH_WIDTH': 'graphs.appearance.dimensions.width',
        'GRAPH_HEIGHT': 'graphs.appearance.dimensions.height',
        'GRAPH_DPI': 'graphs.appearance.dimensions.dpi',
        'TV_COLOR': 'graphs.appearance.colors.tv',
        'MOVIE_COLOR': 'graphs.appearance.colors.movie',
        'GRAPH_BACKGROUND_COLOR': 'graphs.appearance.colors.background',
        'ENABLE_GRAPH_GRID': 'graphs.appearance.grid.enabled',
        'ANNOTATION_COLOR': 'graphs.appearance.annotations.basic.color',
        'ANNOTATION_OUTLINE_COLOR': 'graphs.appearance.annotations.basic.outline_color',
        'ENABLE_ANNOTATION_OUTLINE': 'graphs.appearance.annotations.basic.enable_outline',
        'ANNOTATE_DAILY_PLAY_COUNT': 'graphs.appearance.annotations.enabled_on.daily_play_count',
        'ANNOTATE_PLAY_COUNT_BY_DAYOFWEEK': 'graphs.appearance.annotations.enabled_on.play_count_by_dayofweek',
        'ANNOTATE_PLAY_COUNT_BY_HOUROFDAY': 'graphs.appearance.annotations.enabled_on.play_count_by_hourofday',
        'ANNOTATE_TOP_10_PLATFORMS': 'graphs.appearance.annotations.enabled_on.top_10_platforms',
        'ANNOTATE_TOP_10_USERS': 'graphs.appearance.annotations.enabled_on.top_10_users',
        'ANNOTATE_PLAY_COUNT_BY_MONTH': 'graphs.appearance.annotations.enabled_on.play_count_by_month',
    }
    
    # Replace attribute access patterns
    for old_attr, new_path in attribute_mapping.items():
        # Pattern for config.OLD_ATTR or config_var.OLD_ATTR
        pattern = r'(\w+\.)' + re.escape(old_attr) + r'\b'
        replacement = r'\1' + new_path
        content = re.sub(pattern, replacement, content)
        
        # Pattern for assignment to attributes
        pattern = r'(\w+\.)' + re.escape(old_attr) + r'\s*='
        replacement = r'\1' + new_path + ' ='
        content = re.sub(pattern, replacement, content)
    
    return content


def add_import_if_needed(content: str) -> str:
    """Add import for create_test_config_with_overrides if needed."""
    
    if 'create_test_config_with_overrides' in content:
        # Check if import already exists
        if 'from tests.utils.test_helpers import' in content:
            # Add to existing import
            pattern = r'(from tests\.utils\.test_helpers import[^)]*)'
            if 'create_test_config_with_overrides' not in content:
                replacement = r'\1, create_test_config_with_overrides'
                content = re.sub(pattern, replacement, content)
        else:
            # Add new import after other test_helpers imports
            import_line = "from tests.utils.test_helpers import create_test_config_with_overrides\n"
            
            # Find a good place to insert the import
            lines = content.split('\n')
            insert_index = 0
            
            for i, line in enumerate(lines):
                if line.startswith('from tests.utils') or line.startswith('from src.tgraph_bot'):
                    insert_index = i + 1
                elif line.startswith('if TYPE_CHECKING:'):
                    break
            
            lines.insert(insert_index, import_line)
            content = '\n'.join(lines)
    
    return content


def process_file(file_path: Path) -> bool:
    """Process a single test file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            original_content = f.read()
        
        content = original_content
        
        # Apply fixes
        content = fix_constructor_calls(content)
        content = fix_attribute_access(content)
        content = add_import_if_needed(content)
        
        # Only write if content changed
        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"Updated: {file_path}")
            return True
        
        return False
        
    except Exception as e:
        print(f"Error processing {file_path}: {e}")
        return False


def main():
    """Main function to process all test files."""
    test_files = find_test_files()
    
    print(f"Found {len(test_files)} test files to process")
    
    updated_count = 0
    for file_path in test_files:
        if process_file(file_path):
            updated_count += 1
    
    print(f"Updated {updated_count} files")


if __name__ == "__main__":
    main()
