# bot/permission_checker.py

from typing import Dict, List, Set
import discord
import logging
import textwrap

def create_table(
    headers: List[str], rows: List[List[str]], column_widths: List[int]
) -> str:
    """Create a formatted table string."""
    def format_cell(content: str, width: int) -> str:
        return " " + content.ljust(width - 2) + " "

    def create_separator(widths: List[int], corner: str = "+", line: str = "-") -> str:
        return corner + corner.join(line * w for w in widths) + corner

    table = [create_separator(column_widths)]
    table.append(
        "|"
        + "|".join(
            format_cell(header, width) for header, width in zip(headers, column_widths)
        )
        + "|"
    )
    table.append(create_separator(column_widths, "+", "="))

    for row in rows:
        wrapped_row = [
            textwrap.wrap(cell, width - 2) for cell, width in zip(row, column_widths)
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

async def get_registered_commands(
    bot: discord.Client, 
    guild: discord.Guild
) -> Dict[str, discord.app_commands.Command]:
    """Get all registered commands for a guild."""
    try:
        global_commands = await bot.tree.fetch_commands()
        guild_commands = await bot.tree.fetch_commands(guild=guild)
        
        command_map = {}
        for cmd in global_commands:
            command_map[str(cmd.id)] = cmd
            
        for cmd in guild_commands:
            cmd_id = str(cmd.id)
            if cmd_id in command_map:
                logging.info(
                    f"Guild command /{cmd.name} (ID: {cmd_id}) overrides global command "
                    f"/{command_map[cmd_id].name} in guild {guild.name}"
                )
            command_map[cmd_id] = cmd
            
        return command_map
    except discord.HTTPException as e:
        logging.error(f"Failed to fetch commands: {e}")
        return {}

async def resolve_permission_entities(
    bot: discord.Client,
    guild: discord.Guild,
    permissions: List[Dict],
    show_unknown: bool = False
) -> List[str]:
    """
    Resolve permission entities to their names.
    
    Parameters
    ----------
    bot : discord.Client
        The bot instance
    guild : discord.Guild
        The guild to resolve entities for
    permissions : List[Dict]
        List of permission dictionaries
    show_unknown : bool
        Whether to show unknown entities in the output
    """
    entities = []
    for perm in permissions:
        try:
            entity_id = int(perm["id"])
            permission_allowed = "Allowed" if perm["permission"] else "Denied"

            if perm["type"] == 1:  # Role
                if role := guild.get_role(entity_id):
                    entities.append(f"{role.name} ({permission_allowed})")
                elif show_unknown:
                    logging.debug(f"Role {entity_id} not found in guild {guild.name}")
                    entities.append(f"Unknown Role {entity_id} ({permission_allowed})")

            elif perm["type"] == 2:  # User
                if member := guild.get_member(entity_id):
                    entities.append(f"{member.name} ({permission_allowed})")
                elif show_unknown:
                    logging.debug(f"Member {entity_id} not found in guild {guild.name}")
                    entities.append(f"Unknown Member {entity_id} ({permission_allowed})")

            elif perm["type"] == 3:  # Channel
                if channel := guild.get_channel(entity_id):
                    entities.append(f"#{channel.name} ({permission_allowed})")
                elif show_unknown:
                    logging.debug(f"Channel {entity_id} not found in guild {guild.name}")
                    entities.append(f"Unknown Channel {entity_id} ({permission_allowed})")

        except ValueError as e:
            logging.error(f"Invalid entity ID format {perm['id']}: {e}")
            if show_unknown:
                entities.append(f"Invalid entity ID {perm['id']}")
        except AttributeError as e:
            logging.error(f"Missing required permission attributes: {e}")
            if show_unknown:
                entities.append(f"Invalid permission entry for {perm.get('id', 'unknown')}")
        except discord.HTTPException as e:
            logging.error(f"Discord API error while resolving entity {perm['id']}: {e}")
            if show_unknown:
                entities.append(f"API Error resolving {perm['id']}")

    return entities

async def check_command_permissions(
    bot: discord.Client,
    guild: discord.Guild,
    translations: Dict[str, str],
    show_unknown: bool = False
) -> None:
    """
    Check and log command permissions for a guild.
    
    Parameters
    ----------
    bot : discord.Client
        The bot instance
    guild : discord.Guild
        The guild to check permissions for
    translations : Dict[str, str]
        Translation strings
    show_unknown : bool
        Whether to show unknown command entries in the output
    """
    try:
        command_map = await get_registered_commands(bot, guild)
        guild_permissions = await bot.http.get_guild_application_command_permissions(
            bot.application_id, guild.id
        )

        headers = [translations["permission_entity"], translations["accessible_by"]]
        all_rows = []
        bot_permissions_row = None
        no_permissions_set = True
        commands_with_permissions: Set[str] = set()

        # Process permissions
        for command_permissions in guild_permissions:
            command_id = str(command_permissions["id"])
            permissions = command_permissions.get("permissions", [])

            # Handle bot overall permissions separately
            if command_id == str(bot.application_id):
                if permissions:
                    # Pass show_unknown to resolve_permission_entities
                    entities = await resolve_permission_entities(bot, guild, permissions, show_unknown)
                    if entities:  # Only add if there are resolved entities
                        bot_permissions_row = [
                            translations["bot_overall_permissions"],
                            ", ".join(entities)
                        ]
                continue

            # Skip unknown commands unless show_unknown is True
            if command_id not in command_map:
                if show_unknown:
                    logging.debug(f"Found legacy permission entry for command ID: {command_id}")
                    permission_name = f"{translations['unknown_command']} (ID: {command_id})"
                else:
                    continue
            else:
                command = command_map[command_id]
                permission_name = f"/{command.name}"
                commands_with_permissions.add(command.name)

            if permissions:
                no_permissions_set = False
                entities = await resolve_permission_entities(bot, guild, permissions)
                if entities:
                    all_rows.append([permission_name, ", ".join(entities)])
                else:
                    all_rows.append([
                        permission_name,
                        translations["no_specific_permissions_assigned"],
                    ])
            else:
                all_rows.append([
                    permission_name,
                    translations["accessible_to_all_members"]
                ])

        # Add commands without explicit permissions
        for cmd in command_map.values():
            if cmd.name not in commands_with_permissions:
                all_rows.append([
                    f"/{cmd.name}",
                    translations["accessible_to_all_members"]
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
            logging.warning(
                translations["no_permissions_set_warning"].format(guild_name=guild.name)
            )
            final_rows.append([
                translations["warning_message"],
                translations["no_permissions_set_message"],
            ])

        # Check critical commands
        critical_commands = {"config", "update_graphs"}
        for command in critical_commands:
            command_pattern = f"/{command}"
            if command not in commands_with_permissions:
                logging.warning(
                    translations["critical_command_no_permissions"].format(
                        command=command, guild=guild.name
                    )
                )
            elif any(
                row[0] == command_pattern and row[1] == translations["accessible_to_all_members"]
                for row in final_rows
            ):
                logging.warning(
                    translations["critical_command_all_access"].format(
                        command=command, guild=guild.name
                    )
                )

        # Create and log the table
        column_widths = [30, 50]
        table = create_table(headers, final_rows, column_widths)
        logging.info(
            translations["permissions_for_guild"].format(
                guild_name=guild.name, table="\n" + table
            )
        )

    except discord.HTTPException as e:
        logging.error(
            translations["error_fetching_permissions"].format(
                guild_name=guild.name, error=str(e)
            )
        )
    except Exception as e:
        logging.error(f"Unexpected error in check_command_permissions: {str(e)}")

async def check_permissions_all_guilds(
    bot: discord.Client,
    translations: Dict[str, str],
    show_unknown: bool = False
) -> None:
    """
    Check permissions for all guilds the bot is in.
    
    Parameters
    ----------
    bot : discord.Client
        The bot instance
    translations : Dict[str, str]
        Translation strings
    show_unknown : bool
        Whether to show unknown command entries in the output
    """
    success_count = 0
    failure_count = 0
    
    for guild in bot.guilds:
        try:
            await check_command_permissions(bot, guild, translations, show_unknown)
            success_count += 1
        except discord.HTTPException as e:
            failure_count += 1
            logging.error(
                translations.get("error_checking_guild_permissions",
                    "Failed to check permissions for guild {guild_name} (ID: {guild_id}): {error}"
                ).format(
                    guild_name=guild.name,
                    guild_id=guild.id,
                    error=str(e)
                )
            )
        except Exception as e:
            failure_count += 1
            logging.error(
                f"Unexpected error checking permissions for guild {guild.name} (ID: {guild.id}): {e}"
            )
            continue

    # Log summary
    if failure_count > 0:
        logging.warning(
            translations.get("permissions_check_summary",
                "Completed permissions check with {failure_count} failures. "
                "Successfully checked {success_count}/{total_count} guilds"
            ).format(
                failure_count=failure_count,
                success_count=success_count,
                total_count=len(bot.guilds)
            )
        )
    else:
        logging.info(
            translations.get("permissions_check_complete",
                "Successfully checked permissions for all {count} guilds"
            ).format(count=success_count)
        )
