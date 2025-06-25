"""
Git utilities for workflow scripts.

This module provides common Git operations used across workflow scripts.
"""

import subprocess


def get_last_tag() -> str | None:
    """Get the last release tag."""
    try:
        result = subprocess.run(
            ['git', 'describe', '--tags', '--abbrev=0'],
            capture_output=True, text=True, check=True
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError:
        return None


def get_commits_since_tag(tag: str | None, format_str: str = '%H|%s|%an') -> list[str]:
    """
    Get commits since the specified tag.
    
    Args:
        tag: The tag to compare against, or None for all commits
        format_str: Git log format string
        
    Returns:
        List of commit strings in the specified format
    """
    if tag:
        cmd = ['git', 'log', f'{tag}..HEAD', f'--pretty=format:{format_str}']
    else:
        cmd = ['git', 'log', f'--pretty=format:{format_str}']

    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.stdout.strip().split('\n') if result.stdout.strip() else []


def get_changed_files_since_tag(tag: str | None, path_filter: str = '') -> list[str]:
    """
    Get files changed since the specified tag.
    
    Args:
        tag: The tag to compare against, or None for all changes
        path_filter: Optional path filter (e.g., 'locale/')
        
    Returns:
        List of changed file paths
    """
    if not tag:
        return []
        
    cmd = ['git', 'diff', '--name-only', f'{tag}..HEAD']
    if path_filter:
        cmd.append(path_filter)

    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.stdout.strip().split('\n') if result.stdout.strip() else []


def get_contributors_since_tag(tag: str | None) -> list[str]:
    """
    Get unique contributors since the specified tag.
    
    Args:
        tag: The tag to compare against, or None for all contributors
        
    Returns:
        Sorted list of contributor names and emails
    """
    if tag:
        cmd = ['git', 'log', f'{tag}..HEAD', '--pretty=format:%an <%ae>']
    else:
        cmd = ['git', 'log', '--pretty=format:%an <%ae>']

    result = subprocess.run(cmd, capture_output=True, text=True)
    contributors: set[str] = set(result.stdout.strip().split('\n')) if result.stdout else set()

    # Remove bot accounts and empty entries
    contributors = {c for c in contributors if 'bot' not in c.lower() and c.strip()}

    return sorted(contributors)


def check_git_repository() -> bool:
    """
    Check if the current directory is a Git repository.
    
    Returns:
        True if in a Git repository, False otherwise
    """
    try:
        _ = subprocess.run(
            ['git', 'rev-parse', '--git-dir'],
            capture_output=True, check=True
        )
        return True
    except subprocess.CalledProcessError:
        return False
