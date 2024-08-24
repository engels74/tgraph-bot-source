# bot/permission_checker.py
import discord
from typing import Dict, List
import logging
import textwrap

def create_table(headers: List[str], rows: List[List[str]], column_widths: List[int]) -> str:
    def format_cell(content, width):
        return ' ' + content.ljust(width - 2) + ' '

    def create_separator(widths, corner='+', line='-'):
        return corner + corner.join(line * (w) for w in widths) + corner

    table = [create_separator(column_widths)]
    table.append('|' + '|'.join(format_cell(header, width) for header, width in zip(headers, column_widths)) + '|')
    table.append(create_separator(column_widths, '+', '='))

    for row in rows:
        wrapped_row = [textwrap.wrap(cell, width - 2) for cell, width in zip(row, column_widths)]
        max_lines = max(len(cell) for cell in wrapped_row)
        for i in range(max_lines):
            line = []
            for j, cell in enumerate(wrapped_row):
                if i < len(cell):
                    line.append(format_cell(cell[i], column_widths[j]))
                else:
                    line.append(format_cell('', column_widths[j]))
            table.append('|' + '|'.join(line) + '|')
        table.append(create_separator(column_widths))

    return '\n'.join(table)

async def check_command_permissions(bot: discord.Client, guild: discord.Guild, translations: Dict[str, str]) -> None:
    try:
        global_commands = await bot.tree.fetch_commands()
        guild_commands = await bot.tree.fetch_commands(guild=guild)
        all_commands = global_commands + guild_commands
        command_id_map = {str(cmd.id): cmd.name for cmd in all_commands}

        guild_permissions = await bot.http.get_guild_application_command_permissions(bot.application_id, guild.id)

        headers = [translations['permission_entity'], translations['accessible_by']]
        rows = []
        no_permissions_set = True

        for command_permissions in guild_permissions:
            command_id = command_permissions['id']
            
            if command_id == str(bot.application_id):
                permission_name = translations['bot_overall_permissions']
            else:
                command_name = command_id_map.get(command_id, translations['unknown_command'])
                permission_name = f"/{command_name}"
            
            permissions = command_permissions.get('permissions', [])
            if permissions:
                no_permissions_set = False
                roles_and_users = []
                for perm in permissions:
                    try:
                        if perm['type'] == 1:  # 1 is for roles
                            role = guild.get_role(int(perm['id']))
                            if role:
                                roles_and_users.append(f"{role.name} ({'Allowed' if perm['permission'] else 'Denied'})")
                            else:
                                logging.warning(f"Role with ID {perm['id']} not found in guild {guild.name}")
                        elif perm['type'] == 2:  # 2 is for users
                            user = await bot.fetch_user(int(perm['id']))
                            if user:
                                roles_and_users.append(f"{user.name} ({'Allowed' if perm['permission'] else 'Denied'})")
                            else:
                                logging.warning(f"User with ID {perm['id']} not found")
                        elif perm['type'] == 3:  # 3 is for channels
                            channel = guild.get_channel(int(perm['id']))
                            if channel:
                                roles_and_users.append(f"#{channel.name} ({'Allowed' if perm['permission'] else 'Denied'})")
                            else:
                                logging.warning(f"Channel with ID {perm['id']} not found in guild {guild.name}")
                    except discord.errors.HTTPException as e:
                        logging.error(f"HTTP error when fetching entity with ID {perm['id']}: {str(e)}")
                    except discord.errors.NotFound:
                        logging.warning(f"Entity with ID {perm['id']} not found")
                    except Exception as e:
                        logging.error(f"Unexpected error when processing permission for ID {perm['id']}: {str(e)}")
                
                if roles_and_users:
                    rows.append([permission_name, ', '.join(roles_and_users)])
                else:
                    rows.append([permission_name, translations['no_specific_permissions_assigned']])
            else:
                rows.append([permission_name, translations['accessible_to_all_members']])

        if no_permissions_set:
            logging.warning(translations['no_permissions_set_warning'].format(guild_name=guild.name))
            rows.append([translations['warning_message'], translations['no_permissions_set_message']])

        column_widths = [30, 50]  # Adjust these values as needed
        table = create_table(headers, rows, column_widths)
        logging.info(translations['permissions_for_guild'].format(guild_name=guild.name, table='\n' + table))

        # Check for critical commands with no specific permissions
        critical_commands = ['config', 'update_graphs']
        for command in critical_commands:
            if not any(command in row[0] for row in rows if row[1] != translations['accessible_to_all_members']):
                logging.warning(translations['critical_command_no_permissions'].format(command=command, guild=guild.name))

    except discord.HTTPException as e:
        logging.error(translations['error_fetching_permissions'].format(guild_name=guild.name, error=str(e)))
    except Exception as e:
        logging.error(f"Unexpected error in check_command_permissions: {str(e)}")

async def check_permissions_all_guilds(bot: discord.Client, translations: Dict[str, str]) -> None:
    for guild in bot.guilds:
        await check_command_permissions(bot, guild, translations)
