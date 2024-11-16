# bot/permission_checker.py

"""
Enhanced permission checker for TGraph Bot.
Handles Discord permission management with robust error handling and validation.
"""

from discord.errors import NotFound, Forbidden, HTTPException
from typing import Dict, List, Set, Any
import asyncio
import discord
import logging
import textwrap

class PermissionError(Exception):
    """Base exception for permission-related errors."""
    pass

class CommandError(PermissionError):
    """Raised when there are command-related errors."""
    pass

class ValidationError(PermissionError):
    """Raised when permission validation fails."""
    pass

class DiscordAPIError(PermissionError):
    """Raised when Discord API operations fail."""
    pass

class EntityResolutionError(PermissionError):
    """Raised when entity resolution fails."""
    pass

class TableFormattingError(PermissionError):
    """Raised when table formatting fails."""
    pass

def create_table(
    headers: List[str],
    rows: List[List[str]],
    column_widths: List[int]
) -> str:
    """
    Create a formatted table string with error handling.
    
    Args:
        headers: Table header strings
        rows: Table row data
        column_widths: Width for each column
        
    Returns:
        str: Formatted table string
        
    Raises:
        TableFormattingError: If table creation fails
    """
    try:
        if not headers or not column_widths or len(headers) != len(column_widths):
            raise ValueError("Invalid headers or column widths")

        def format_cell(content: str, width: int) -> str:
            return " " + content.ljust(width - 2) + " "

        def create_separator(widths: List[int], corner: str = "+", line: str = "-") -> str:
            return corner + corner.join(line * w for w in widths) + corner

        table = [create_separator(column_widths)]
        table.append(
            "|" + "|".join(
                format_cell(header, width) 
                for header, width in zip(headers, column_widths)
            ) + "|"
        )
        table.append(create_separator(column_widths, "+", "="))

        for row in rows:
            if len(row) != len(column_widths):
                raise ValueError(f"Row has incorrect number of columns: {row}")
                
            wrapped_row = [
                textwrap.wrap(cell, width - 2)
                for cell, width in zip(row, column_widths)
            ]
            max_lines = max(len(cell) for cell in wrapped_row)
            
            for i in range(max_lines):
                line = []
                for j, cell in enumerate(wrapped_row):
                    if i < len(cell):
                        line.append(format_cell(cell[i], column_widths[j]))
                    else:
                        line.append(format_cell("", column_widths[j]))
                table.append("|" + "|".join(line) + "|")
            table.append(create_separator(column_widths))

        return "\n".join(table)

    except Exception as e:
        error_msg = f"Failed to create formatted table: {str(e)}"
        logging.error(error_msg)
        raise TableFormattingError(error_msg) from e

async def fetch_with_retry(fetch_func, max_retries=3):
    """
    Execute a fetch function with retry logic for rate limits.
    
    Args:
        fetch_func: Async function to execute
        max_retries: Maximum number of retry attempts
        
    Returns:
        Result from the fetch function
        
    Raises:
        CommandError: If max retries exceeded
    """
    for attempt in range(max_retries):
        try:
            return await fetch_func()
        except HTTPException as e:
            if e.status == 429:  # Rate limited
                retry_after = e.response.headers.get('Retry-After', 1)
                await asyncio.sleep(float(retry_after))
                continue
            raise
    raise CommandError("Max retries exceeded")

async def get_registered_commands(
    bot: discord.Client,
    guild: discord.Guild,
    translations: Dict[str, str]
) -> Dict[str, discord.app_commands.Command]:
    """
    Get all registered commands for a guild with error handling.
    
    Args:
        bot: Bot instance
        guild: Guild to fetch commands for
        translations: Translation dictionary
        
    Returns:
        Dictionary mapping command IDs to command objects
        
    Raises:
        CommandError: If command fetching fails
    """
    try:
        command_map = {}
        
        try:
            global_commands = await fetch_with_retry(lambda: bot.tree.fetch_commands())
            for cmd in global_commands:
                command_map[str(cmd.id)] = cmd
        except HTTPException as e:
            error_msg = translations.get(
                'error_fetch_global_commands',
                'Failed to fetch global commands: {error}'
            ).format(error=str(e))
            raise CommandError(error_msg) from e

        try:
            guild_commands = await fetch_with_retry(lambda: bot.tree.fetch_commands(guild=guild))
            for cmd in guild_commands:
                cmd_id = str(cmd.id)
                if cmd_id in command_map:
                    logging.info(
                        translations.get(
                            'log_command_override',
                            'Guild command /{cmd_name} (ID: {cmd_id}) overrides global command '
                            '/{global_name} in guild {guild_name}'
                        ).format(
                            cmd_name=cmd.name,
                            cmd_id=cmd_id,
                            global_name=command_map[cmd_id].name,
                            guild_name=guild.name
                        )
                    )
                command_map[cmd_id] = cmd
        except HTTPException as e:
            error_msg = translations.get(
                'error_fetch_guild_commands',
                'Failed to fetch guild commands: {error}'
            ).format(error=str(e))
            raise CommandError(error_msg) from e

        return command_map

    except Exception as e:
        if isinstance(e, CommandError):
            raise
        error_msg = translations.get(
            'error_fetch_commands',
            'Failed to fetch commands: {error}'
        ).format(error=str(e))
        logging.error(error_msg)
        raise CommandError(error_msg) from e

async def resolve_permission_entities(
    bot: discord.Client,
    guild: discord.Guild,
    permissions: List[Dict[str, Any]],
    translations: Dict[str, str],
    show_unknown: bool = False
) -> List[str]:
    """
    Resolve permission entities to their names with enhanced error handling.
    
    Args:
        bot: Bot instance
        guild: Guild to resolve entities for
        permissions: List of permission dictionaries
        translations: Translation dictionary
        show_unknown: Whether to show unknown entities
        
    Returns:
        List of resolved entity strings
        
    Raises:
        EntityResolutionError: If entity resolution fails
    """
    try:
        entities = []
        
        for perm in permissions:
            try:
                if not isinstance(perm, dict) or 'id' not in perm or 'type' not in perm:
                    raise ValidationError(f"Invalid permission format: {perm}")
                    
                entity_id = int(perm["id"])
                permission_allowed = translations.get(
                    'permission_allowed' if perm["permission"] else 'permission_denied',
                    "Allowed" if perm["permission"] else "Denied"
                )

                try:
                    if perm["type"] == 1:  # Role
                        role = guild.get_role(entity_id)
                        if role:
                            entities.append(f"{role.name} ({permission_allowed})")
                        elif show_unknown:
                            logging.debug(f"Role {entity_id} not found in guild {guild.name}")
                            entities.append(
                                translations.get(
                                    'unknown_role',
                                    'Unknown Role {id} ({permission})'
                                ).format(id=entity_id, permission=permission_allowed)
                            )

                    elif perm["type"] == 2:  # User
                        member = guild.get_member(entity_id)
                        if member:
                            entities.append(f"{member.name} ({permission_allowed})")
                        elif show_unknown:
                            logging.debug(f"Member {entity_id} not found in guild {guild.name}")
                            entities.append(
                                translations.get(
                                    'unknown_member',
                                    'Unknown Member {id} ({permission})'
                                ).format(id=entity_id, permission=permission_allowed)
                            )

                    elif perm["type"] == 3:  # Channel
                        channel = guild.get_channel(entity_id)
                        if channel:
                            entities.append(f"#{channel.name} ({permission_allowed})")
                        elif show_unknown:
                            logging.debug(f"Channel {entity_id} not found in guild {guild.name}")
                            entities.append(
                                translations.get(
                                    'unknown_channel',
                                    'Unknown Channel {id} ({permission})'
                                ).format(id=entity_id, permission=permission_allowed)
                            )

                except NotFound as e:
                    if show_unknown:
                        error_msg = translations.get(
                            'error_entity_not_found',
                            'Entity {id} not found: {error}'
                        ).format(id=entity_id, error=str(e))
                        logging.warning(error_msg)
                        entities.append(f"Not Found: {entity_id}")
                except Forbidden as e:
                    error_msg = translations.get(
                        'error_entity_forbidden',
                        'Access forbidden to entity {id}: {error}'
                    ).format(id=entity_id, error=str(e))
                    logging.warning(error_msg)
                    if show_unknown:
                        entities.append(f"Access Denied: {entity_id}")

            except ValueError as e:
                if show_unknown:
                    entities.append(
                        translations.get(
                            'invalid_entity_id',
                            'Invalid ID format: {id}'
                        ).format(id=perm.get('id', 'unknown'))
                    )
                logging.warning(f"Invalid entity ID format: {e}")
            except KeyError as e:
                logging.warning(f"Missing required permission attributes: {e}")
                if show_unknown:
                    entities.append("Invalid Permission Entry")

        return entities

    except Exception as e:
        if isinstance(e, (EntityResolutionError, ValidationError)):
            raise
        error_msg = translations.get(
            'error_resolve_entities',
            'Failed to resolve permission entities: {error}'
        ).format(error=str(e))
        logging.error(error_msg)
        raise EntityResolutionError(error_msg) from e

async def check_command_permissions(
    bot: discord.Client,
    guild: discord.Guild,
    translations: Dict[str, str],
    show_unknown: bool = False
) -> None:
    """
    Check and log command permissions for a guild.
    
    Args:
        bot: Bot instance
        guild: Guild to check permissions for
        translations: Translation dictionary
        show_unknown: Whether to show unknown command entries
        
    Raises:
        PermissionError: If permission check fails
    """
    try:
        command_map = await get_registered_commands(bot, guild, translations)
        
        try:
            guild_permissions = await bot.http.get_guild_application_command_permissions(
                bot.application_id,
                guild.id
            )
        except HTTPException as e:
            error_msg = translations.get(
                'error_fetch_guild_permissions',
                'Failed to fetch guild permissions: {error}'
            ).format(error=str(e))
            raise PermissionError(error_msg) from e

        headers = [
            translations.get('permission_entity', 'Permission Entity'),
            translations.get('accessible_by', 'Accessible By')
        ]
        all_rows = []
        bot_permissions_row = None
        no_permissions_set = True
        commands_with_permissions: Set[str] = set()

        # Process permissions
        for command_permissions in guild_permissions:
            command_id = str(command_permissions["id"])
            permissions = command_permissions.get("permissions", [])

            # Handle bot overall permissions
            if command_id == str(bot.application_id):
                if permissions:
                    entities = await resolve_permission_entities(
                        bot, guild, permissions, translations, show_unknown
                    )
                    if entities:
                        bot_permissions_row = [
                            translations.get('bot_overall_permissions', 'Bot Overall Permissions'),
                            ", ".join(entities)
                        ]
                continue

            # Skip unknown commands unless show_unknown is True
            if command_id not in command_map:
                if show_unknown:
                    logging.debug(f"Found legacy permission entry for command ID: {command_id}")
                    permission_name = translations.get(
                        'unknown_command',
                        'Unknown Command'
                    ) + f" (ID: {command_id})"
                else:
                    continue
            else:
                command = command_map[command_id]
                permission_name = f"/{command.name}"
                commands_with_permissions.add(command.name)

            if permissions:
                no_permissions_set = False
                entities = await resolve_permission_entities(
                    bot, guild, permissions, translations, show_unknown
                )
                if entities:
                    all_rows.append([permission_name, ", ".join(entities)])
                else:
                    all_rows.append([
                        permission_name,
                        translations.get(
                            'no_specific_permissions_assigned',
                            'No specific permissions assigned'
                        )
                    ])
            else:
                all_rows.append([
                    permission_name,
                    translations.get(
                        'accessible_to_all_members',
                        'Accessible to all members'
                    )
                ])

        # Add commands without explicit permissions
        for cmd in command_map.values():
            if cmd.name not in commands_with_permissions:
                all_rows.append([
                    f"/{cmd.name}",
                    translations.get(
                        'accessible_to_all_members',
                        'Accessible to all members'
                    )
                ])

        # Sort rows alphabetically by command name
        all_rows.sort(key=lambda x: x[0].lower())

        # Combine rows with bot permissions at top
        final_rows = []
        if bot_permissions_row:
            final_rows.append(bot_permissions_row)
        final_rows.extend(all_rows)

        # Handle case where no permissions are set
        if no_permissions_set:
            warning_msg = translations.get(
                'no_permissions_set_warning',
                'WARNING: No permissions are set for any commands in the guild \'{guild_name}\'. '
                'This may pose a security risk.'
            ).format(guild_name=guild.name)
            logging.warning(warning_msg)
            final_rows.append([
                translations.get('warning_message', 'WARNING'),
                translations.get(
                    'no_permissions_set_message',
                    'No permissions are set for any commands. All commands are accessible to everyone.'
                )
            ])

        # Check critical commands
        critical_commands = {"config", "update_graphs"}
        for command in critical_commands:
            command_pattern = f"/{command}"
            if command not in commands_with_permissions:
                logging.warning(
                    translations.get(
                        'critical_command_no_permissions',
                        'WARNING: The /{command} command has no specific permissions set in the '
                        'guild \'{guild}\'. This may pose a security risk.'
                    ).format(command=command, guild=guild.name)
                )
            elif any(
                row[0] == command_pattern and row[1] == translations.get(
                    'accessible_to_all_members',
                    'Accessible to all members'
                )
                for row in final_rows
            ):
                logging.warning(
                    translations.get(
                        'critical_command_all_access',
                        'WARNING: The /{command} command is accessible to all members in the '
                        'guild \'{guild}\'. This may pose a security risk.'
                    ).format(command=command, guild=guild.name)
                )

        # Create and log the formatted table
        try:
            column_widths = [30, 50]
            table = create_table(headers, final_rows, column_widths)
            logging.info(
                translations.get(
                    'permissions_for_guild',
                    'Permissions for guild \'{guild_name}\':\n{table}'
                ).format(
                    guild_name=guild.name,
                    table="\n" + table
                )
            )
        except TableFormattingError as e:
            error_msg = translations.get(
                'error_format_permissions_table',
                'Failed to format permissions table: {error}'
            ).format(error=str(e))
            logging.error(error_msg)
            raise PermissionError(error_msg) from e

    except Exception as e:
        if isinstance(e, (CommandError, EntityResolutionError, PermissionError)):
            raise
        error_msg = translations.get(
            'error_check_permissions',
            'Error checking permissions for guild {guild_name}: {error}'
        ).format(guild_name=guild.name, error=str(e))
        logging.error(error_msg)
        raise PermissionError(error_msg) from e

async def check_permissions_all_guilds(
    bot: discord.Client,
    translations: Dict[str, str],
    show_unknown: bool = False
) -> None:
    """
    Check permissions for all guilds the bot is in.
    
    Args:
        bot: Bot instance
        translations: Translation dictionary
        show_unknown: Whether to show unknown command entries
        
    Raises:
        PermissionError: If permission checks fail critically
    """
    success_count = 0
    failure_count = 0
    failed_guilds = []
    
    for guild in bot.guilds:
        try:
            await check_command_permissions(bot, guild, translations, show_unknown)
            success_count += 1
        except PermissionError as e:
            failure_count += 1
            failed_guilds.append((guild.name, str(e)))
            logging.error(
                translations.get(
                    'error_guild_permission_check',
                    'Failed to check permissions for guild {guild_name} (ID: {guild_id}): {error}'
                ).format(
                    guild_name=guild.name,
                    guild_id=guild.id,
                    error=str(e)
                )
            )
        except Exception as e:
            failure_count += 1
            failed_guilds.append((guild.name, str(e)))
            logging.error(
                translations.get(
                    'error_unexpected_guild_check',
                    'Unexpected error checking permissions for guild {guild_name} '
                    '(ID: {guild_id}): {error}'
                ).format(
                    guild_name=guild.name,
                    guild_id=guild.id,
                    error=str(e)
                )
            )

    # Log summary with appropriate level based on results
    total_guilds = len(bot.guilds)
    if failure_count > 0:
        log_level = logging.ERROR if failure_count == total_guilds else logging.WARNING
        logging.log(
            log_level,
            translations.get(
                'permissions_check_summary',
                'Completed permissions check with {failure_count} failures. '
                'Successfully checked {success_count}/{total_count} guilds'
            ).format(
                failure_count=failure_count,
                success_count=success_count,
                total_count=total_guilds
            )
        )
        
        # Log details of failed guilds
        for guild_name, error in failed_guilds:
            logging.error(
                translations.get(
                    'guild_check_failure_detail',
                    'Permission check failed for {guild_name}: {error}'
                ).format(guild_name=guild_name, error=error)
            )
            
        # If all guilds failed, raise error
        if failure_count == total_guilds:
            raise PermissionError(
                translations.get(
                    'error_all_guilds_failed',
                    'Permission checks failed for all guilds'
                )
            )
    else:
        logging.info(
            translations.get(
                'permissions_check_complete',
                'Successfully checked permissions for all {count} guilds'
            ).format(count=success_count)
        )

def validate_permission_entry(
    entry: Dict[str, Any],
    translations: Dict[str, str]
) -> None:
    """
    Validate a permission entry's structure.
    
    Args:
        entry: Permission entry to validate
        translations: Translation dictionary
        
    Raises:
        ValidationError: If entry is invalid
    """
    required_keys = {'id', 'type', 'permission'}
    try:
        if not isinstance(entry, dict):
            raise ValidationError(
                translations.get(
                    'error_invalid_permission_type',
                    'Permission entry must be a dictionary'
                )
            )
            
        missing_keys = required_keys - set(entry.keys())
        if missing_keys:
            raise ValidationError(
                translations.get(
                    'error_missing_permission_keys',
                    'Missing required keys in permission entry: {keys}'
                ).format(keys=', '.join(missing_keys))
            )
            
        if not isinstance(entry['id'], (int, str)):
            raise ValidationError(
                translations.get(
                    'error_invalid_id_type',
                    'Permission ID must be an integer or string'
                )
            )
            
        if not isinstance(entry['type'], int):
            raise ValidationError(
                translations.get(
                    'error_invalid_type_value',
                    'Permission type must be an integer'
                )
            )
            
        if not isinstance(entry['permission'], bool):
            raise ValidationError(
                translations.get(
                    'error_invalid_permission_value',
                    'Permission value must be a boolean'
                )
            )
            
    except Exception as e:
        if isinstance(e, ValidationError):
            raise
        error_msg = translations.get(
            'error_permission_validation',
            'Error validating permission entry: {error}'
        ).format(error=str(e))
        raise ValidationError(error_msg) from e
