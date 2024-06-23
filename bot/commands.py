# bot/commands.py
import os
from datetime import datetime, timedelta
import discord
from discord import app_commands
from discord.ext import commands
from config.config import load_config, update_config, RESTART_REQUIRED_KEYS, get_configurable_options, CONFIG_PATH
from i18n import load_translations
from graphs.generate_graphs import update_and_post_graphs
from graphs.generate_graphs_user import generate_user_graphs
from main import log
import requests

# Load configuration
config = load_config(CONFIG_PATH)

# Load translations
translations = load_translations(config['LANGUAGE'])

# Get configurable options
CONFIG_OPTIONS = get_configurable_options()

class Commands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.start_time = datetime.now().astimezone()
        self.user_cooldowns = {}
        self.global_cooldown = datetime.now()

    async def cog_load(self):
        log(translations['log_commands_cog_loading'])
        for command in self.get_app_commands():
            log(translations['log_registering_command'].format(command_name=command.name))
        log(translations['log_commands_cog_loaded'])

    @app_commands.command(name="about", description=translations['about_command_description'])
    async def about(self, interaction: discord.Interaction):
        try:
            embed = discord.Embed(title="TGraph Bot", color=0x3498db)
            embed.add_field(name="Description", value=translations['about_description'], inline=False)
            embed.add_field(name=translations['about_github'], value="https://github.com/engels74/tgraph-bot-source", inline=False)
            embed.add_field(name=translations['about_license'], value="AGPLv3", inline=False)
            await interaction.response.send_message(embed=embed, ephemeral=True)
            log(translations['log_command_executed'].format(command="about", user=f"{interaction.user.name}#{interaction.user.discriminator}"))
        except Exception as e:
            log(translations['log_command_error'].format(command="about", error=str(e)))
            await interaction.response.send_message(translations['error_processing_command'], ephemeral=True)

    @app_commands.command(name="config", description=translations['config_command_description'])
    @app_commands.choices(action=[
        app_commands.Choice(name="View", value="view"),
        app_commands.Choice(name="Edit", value="edit")
    ])
    @app_commands.choices(key=[app_commands.Choice(name=option, value=option) for option in CONFIG_OPTIONS])
    async def config_command(self, interaction: discord.Interaction, action: str, key: str = None, value: str = None):
        global config, translations
        try:
            config = load_config(CONFIG_PATH, reload=True)
            
            if action == "view":
                if key:
                    if key in config and key in CONFIG_OPTIONS:
                        await interaction.response.send_message(f"{key}: {config[key]}", ephemeral=True)
                    else:
                        await interaction.response.send_message(translations['config_view_invalid_key'].format(key=key), ephemeral=True)
                else:
                    embed = discord.Embed(title="Bot Configuration", color=0x3498db)
                    for k, v in config.items():
                        if k in CONFIG_OPTIONS:
                            embed.add_field(name=k, value=str(v), inline=False)
                    await interaction.response.send_message(embed=embed, ephemeral=True)
            elif action == "edit":
                if key is None:
                    await interaction.response.send_message(translations['config_edit_specify_key'], ephemeral=True)
                    return
                if key not in CONFIG_OPTIONS:
                    await interaction.response.send_message(translations['config_view_invalid_key'].format(key=key), ephemeral=True)
                    return
                if value is None:
                    await interaction.response.send_message(translations['config_edit_specify_value'], ephemeral=True)
                    return

                # Convert value to appropriate type
                if isinstance(config[key], bool):
                    value = value.lower() == 'true'
                elif isinstance(config[key], int):
                    value = int(value)

                # Update configuration
                new_config = update_config(key, value)
                
                # Reload translations if language changed
                if key == 'LANGUAGE':
                    translations = load_translations(value)

                # Send response
                if key in RESTART_REQUIRED_KEYS:
                    await interaction.response.send_message(translations['config_updated_restart'].format(key=key), ephemeral=True)
                else:
                    await interaction.response.send_message(translations['config_updated'].format(key=key, value=value), ephemeral=True)

            log(translations['log_command_executed'].format(command="config", user=f"{interaction.user.name}#{interaction.user.discriminator}"))
        except Exception as e:
            log(translations['log_command_error'].format(command="config", error=str(e)))
            await interaction.followup.send(translations['error_processing_command'], ephemeral=True)

    @app_commands.command(name="my_stats", description=translations['my_stats_command_description'])
    async def my_stats(self, interaction: discord.Interaction, email: str):
        # Check global cooldown
        if datetime.now() < self.global_cooldown:
            remaining = int((self.global_cooldown - datetime.now()).total_seconds())
            await interaction.response.send_message(
                translations['rate_limit_global'].format(time=f"<t:{int((datetime.now() + timedelta(seconds=remaining)).timestamp())}:R>"),
                ephemeral=True
            )
            return

        # Check user cooldown
        user_id = str(interaction.user.id)
        if user_id in self.user_cooldowns and datetime.now() < self.user_cooldowns[user_id]:
            remaining = int((self.user_cooldowns[user_id] - datetime.now()).total_seconds())
            await interaction.response.send_message(
                translations['rate_limit_user'].format(time=f"<t:{int((datetime.now() + timedelta(seconds=remaining)).timestamp())}:R>"),
                ephemeral=True
            )
            return

        await interaction.response.defer(ephemeral=True)

        try:
            # Reload configuration
            global config
            config = load_config(CONFIG_PATH, reload=True)
            
            tautulli_user_id = self.get_user_id_from_email(email)

            if not tautulli_user_id:
                await interaction.followup.send(translations['my_stats_no_user_found'], ephemeral=True)
                return

            log(translations['log_generating_user_graphs'].format(user_id=tautulli_user_id))
            graph_files = generate_user_graphs(tautulli_user_id, config, translations)
            log(translations['log_generated_graph_files'].format(count=len(graph_files)))

            if not graph_files:
                log(translations['my_stats_generate_failed'])
                await interaction.followup.send(translations['my_stats_generate_failed'], ephemeral=True)
                return

            # Send graphs via PM
            log(translations['log_sending_graphs_pm'])
            dm_channel = await interaction.user.create_dm()
            for graph_file in graph_files:
                log(translations['log_sending_graph_file'].format(file=graph_file))
                await dm_channel.send(file=discord.File(graph_file))

            # Update cooldowns
            log(translations['log_updating_cooldowns'])
            self.user_cooldowns[user_id] = datetime.now() + timedelta(minutes=config['MY_STATS_COOLDOWN_MINUTES'])
            self.global_cooldown = datetime.now() + timedelta(seconds=config['MY_STATS_GLOBAL_COOLDOWN_SECONDS'])

            await interaction.followup.send(translations['my_stats_success'], ephemeral=True)
            log(translations['log_command_executed'].format(command="my_stats", user=f"{interaction.user.name}#{interaction.user.discriminator}"))

        except Exception as e:
            log(translations['log_command_error'].format(command="my_stats", error=str(e)))
            await interaction.followup.send(
                translations['my_stats_error'],
                ephemeral=True
            )

    @app_commands.command(name="update_graphs", description=translations['update_graphs_command_description'])
    async def update_graphs(self, interaction: discord.Interaction):
        try:
            await interaction.response.defer(ephemeral=True)
            await update_and_post_graphs(self.bot, translations)
            try:
                await interaction.followup.send(translations['update_graphs_success'], ephemeral=True)
                log(translations['log_command_executed'].format(command="update_graphs", user=f"{interaction.user.name}#{interaction.user.discriminator}"))
                log(translations['log_graphs_updated_posted'])
            except discord.errors.NotFound:
                log(translations['log_command_executed'].format(command="update_graphs", user=f"{interaction.user.name}#{interaction.user.discriminator}"))
                log(translations['log_graphs_updated_posted'])
        except Exception as e:
            log(translations['log_command_error'].format(command="update_graphs", error=str(e)))
            try:
                await interaction.followup.send(translations['update_graphs_error'], ephemeral=True)
            except discord.errors.NotFound:
                log(translations['log_command_error'].format(command="update_graphs", error=str(e)))

    @app_commands.command(name="uptime", description=translations['uptime_command_description'])
    async def uptime(self, interaction: discord.Interaction):
        try:
            current_time = datetime.now().astimezone()
            uptime = current_time - self.start_time
            await interaction.response.send_message(translations['uptime_response'].format(uptime=uptime), ephemeral=True)
            log(translations['log_command_executed'].format(command="uptime", user=f"{interaction.user.name}#{interaction.user.discriminator}"))
        except Exception as e:
            log(translations['log_command_error'].format(command="uptime", error=str(e)))
            await interaction.followup.send(translations['error_processing_command'], ephemeral=True)

    def get_user_id_from_email(self, email):
        if not email:
            return None

        try:
            response = requests.get(
                f"{config['TAUTULLI_URL']}/api/v2",
                params={
                    "apikey": config['TAUTULLI_API_KEY'],
                    "cmd": "get_users"
                }
            )
            response.raise_for_status()
            users = response.json()['response']['data']

            for user in users:
                if user.get('email') and user['email'].lower() == email.lower():
                    return user['user_id']

            return None
        except Exception as e:
            log(translations['error_fetching_user_id'].format(error=str(e)))
            return None

async def setup(bot):
    await bot.add_cog(Commands(bot))
    log(translations['log_commands_cog_setup'])
