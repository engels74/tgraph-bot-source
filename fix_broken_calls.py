#!/usr/bin/env python3
"""
Script to fix broken function calls caused by the migration script.
"""

import re
from pathlib import Path


def fix_broken_function_calls(content: str) -> str:
    """Fix broken function calls where parameters got split incorrectly."""
    
    # Pattern to find broken function calls where closing parenthesis is followed by parameters
    pattern = r'(\w+\([^)]*\))\s*\n\s*([A-Z_]+=.*?)\s*\n\s*\)'
    
    def fix_call(match):
        func_call = match.group(1)
        extra_params = match.group(2)
        
        # Remove the closing parenthesis from func_call and add the extra params
        if func_call.endswith(')'):
            func_call = func_call[:-1]  # Remove closing paren
            if not func_call.endswith(','):
                func_call += ','
            return f"{func_call}\n                {extra_params},\n            )"
        
        return match.group(0)  # Return original if pattern doesn't match expected format
    
    # Apply the fix multiple times to handle nested cases
    for _ in range(5):  # Max 5 iterations to avoid infinite loops
        new_content = re.sub(pattern, fix_call, content, flags=re.MULTILINE | re.DOTALL)
        if new_content == content:
            break
        content = new_content
    
    return content


def process_file(file_path: Path) -> bool:
    """Process a single file to fix broken function calls."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            original_content = f.read()
        
        content = fix_broken_function_calls(original_content)
        
        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"Fixed: {file_path}")
            return True
        
        return False
        
    except Exception as e:
        print(f"Error processing {file_path}: {e}")
        return False


def main():
    """Main function."""
    # Focus on the files we know have issues
    problem_files = [
        "tests/integration/test_palette_priority_integration.py",
        "tests/integration/test_graph_manager_architecture.py",
    ]
    
    fixed_count = 0
    for file_path_str in problem_files:
        file_path = Path(file_path_str)
        if file_path.exists():
            if process_file(file_path):
                fixed_count += 1
    
    print(f"Fixed {fixed_count} files")


if __name__ == "__main__":
    main()
