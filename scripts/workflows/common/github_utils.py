"""
GitHub utilities for workflow scripts.

This module provides common GitHub Actions operations and utilities.
"""

import os
import re


def set_github_output(key: str, value: str) -> None:
    """
    Set GitHub Actions output.
    
    Args:
        key: The output key name
        value: The output value
    """
    github_output = os.environ.get('GITHUB_OUTPUT')
    if github_output:
        with open(github_output, 'a') as f:
            _ = f.write(f"{key}={value}\n")
    else:
        # Fallback for older GitHub Actions syntax
        print(f"::set-output name={key}::{value}")


def get_github_env(key: str, default: str = '') -> str:
    """
    Get GitHub Actions environment variable.
    
    Args:
        key: The environment variable key
        default: Default value if not found
        
    Returns:
        The environment variable value or default
    """
    return os.environ.get(key, default).strip()


def extract_pr_numbers_from_commits(commit_messages: list[str]) -> list[str]:
    """
    Extract PR numbers from commit messages.
    
    Args:
        commit_messages: List of commit messages
        
    Returns:
        List of unique PR numbers
    """
    pr_numbers: list[str] = []
    for msg in commit_messages:
        # Match patterns like (#123), #123, PR #123
        matches = re.findall(r'(?:#|PR\s*#)(\d+)', msg)
        pr_numbers.extend(matches)

    return list(set(pr_numbers))  # Remove duplicates


def is_github_actions() -> bool:
    """
    Check if running in GitHub Actions environment.
    
    Returns:
        True if running in GitHub Actions, False otherwise
    """
    return os.environ.get('GITHUB_ACTIONS') == 'true'


def get_repository_info() -> tuple[str | None, str | None]:
    """
    Get repository owner and name from GitHub environment.
    
    Returns:
        Tuple of (owner, repo_name) or (None, None) if not available
    """
    repo_full_name = os.environ.get('GITHUB_REPOSITORY')
    if repo_full_name and '/' in repo_full_name:
        owner, repo = repo_full_name.split('/', 1)
        return owner, repo
    return None, None


def get_workflow_run_info() -> dict[str, str | None]:
    """
    Get information about the current workflow run.
    
    Returns:
        Dictionary with workflow run information
    """
    return {
        'run_id': os.environ.get('GITHUB_RUN_ID'),
        'run_number': os.environ.get('GITHUB_RUN_NUMBER'),
        'workflow': os.environ.get('GITHUB_WORKFLOW'),
        'event_name': os.environ.get('GITHUB_EVENT_NAME'),
        'ref': os.environ.get('GITHUB_REF'),
        'sha': os.environ.get('GITHUB_SHA'),
        'actor': os.environ.get('GITHUB_ACTOR')
    }


def format_github_summary(title: str, content: str) -> str:
    """
    Format content for GitHub Actions job summary.
    
    Args:
        title: Summary title
        content: Summary content
        
    Returns:
        Formatted summary string
    """
    return f"# {title}\n\n{content}"


def write_github_summary(content: str) -> None:
    """
    Write content to GitHub Actions job summary.
    
    Args:
        content: Content to write to summary
    """
    github_step_summary = os.environ.get('GITHUB_STEP_SUMMARY')
    if github_step_summary:
        with open(github_step_summary, 'a') as f:
            _ = f.write(content + '\n')
    else:
        print("GitHub Step Summary not available")


def create_github_notice(message: str, title: str | None = None, file: str | None = None,
                        line: int | None = None) -> None:
    """
    Create a GitHub Actions notice.
    
    Args:
        message: Notice message
        title: Optional notice title
        file: Optional file path
        line: Optional line number
    """
    notice_parts: list[str] = ['::notice']

    params: list[str] = []
    if title:
        params.append(f"title={title}")
    if file:
        params.append(f"file={file}")
    if line:
        params.append(f"line={line}")

    if params:
        notice_parts.append(' '.join(params))
    
    notice_parts.append(f"::{message}")
    print(''.join(notice_parts))


def create_github_warning(message: str, title: str | None = None, file: str | None = None,
                         line: int | None = None) -> None:
    """
    Create a GitHub Actions warning.
    
    Args:
        message: Warning message
        title: Optional warning title
        file: Optional file path
        line: Optional line number
    """
    warning_parts: list[str] = ['::warning']

    params: list[str] = []
    if title:
        params.append(f"title={title}")
    if file:
        params.append(f"file={file}")
    if line:
        params.append(f"line={line}")

    if params:
        warning_parts.append(' '.join(params))
    
    warning_parts.append(f"::{message}")
    print(''.join(warning_parts))


def create_github_error(message: str, title: str | None = None, file: str | None = None,
                       line: int | None = None) -> None:
    """
    Create a GitHub Actions error.
    
    Args:
        message: Error message
        title: Optional error title
        file: Optional file path
        line: Optional line number
    """
    error_parts: list[str] = ['::error']

    params: list[str] = []
    if title:
        params.append(f"title={title}")
    if file:
        params.append(f"file={file}")
    if line:
        params.append(f"line={line}")

    if params:
        error_parts.append(' '.join(params))
    
    error_parts.append(f"::{message}")
    print(''.join(error_parts))
