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
        log("Commands cog is being loaded...")
        for command in self.get_app_commands():
            log(f"Registering command: {command.name}")
        log("Commands cog loaded successfully.")

    @app_commands.command(name="about", description="Information about the bot")
    async def about(self, interaction: discord.Interaction):
        try:
            embed = discord.Embed(title="TGraph Bot", color=0x3498db)
            embed.add_field(name="Description", value="TGraph Bot is a Discord bot that generates and posts graphs based on Tautulli data. It provides insights into your media server usage, including daily play counts, play counts by day of the week, play counts by hour of the day, top 10 platforms, top 10 users, and play counts by month.", inline=False)
            embed.add_field(name="GitHub", value="https://github.com/engels74/tgraph-bot-source", inline=False)
            embed.add_field(name="License", value="AGPLv3", inline=False)
            await interaction.response.send_message(embed=embed, ephemeral=True)
            log(f"Command /about executed by {interaction.user.name}#{interaction.user.discriminator}")
        except Exception as e:
            log(f"Error in /about command: {str(e)}")
            await interaction.response.send_message(translations['error_processing_command'], ephemeral=True)

    @app_commands.command(name="config", description="View or edit bot configuration")
    @app_commands.choices(action=[
        app_commands.Choice(name="View", value="view"),
        app_commands.Choice(name="Edit", value="edit")
    ])
    @app_commands.choices(key=[app_commands.Choice(name=option, value=option) for option in CONFIG_OPTIONS])
    async def config_command(self, interaction: discord.Interaction, action: str, key: str = None, value: str = None):
        try:
            global config, translations
            config = load_config(CONFIG_PATH, reload=True)
            
            if action == "view":
                if key:
                    if key in config and key in CONFIG_OPTIONS:
                        await interaction.response.send_message(f"{key}: {config[key]}", ephemeral=True)
                    else:
                        await interaction.response.send_message(f"Invalid or non-configurable key: {key}", ephemeral=True)
                else:
                    embed = discord.Embed(title="Bot Configuration", color=0x3498db)
                    for k, v in config.items():
                        if k in CONFIG_OPTIONS:
                            embed.add_field(name=k, value=str(v), inline=False)
                    await interaction.response.send_message(embed=embed, ephemeral=True)
            elif action == "edit":
                if key is None:
                    await interaction.response.send_message("Please specify a key to edit.", ephemeral=True)
                    return
                if key not in CONFIG_OPTIONS:
                    await interaction.response.send_message(f"Invalid or non-configurable key: {key}", ephemeral=True)
                    return
                if value is None:
                    await interaction.response.send_message("Please specify a value to set.", ephemeral=True)
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
                    await interaction.response.send_message(f"Configuration updated. Note: Changes to {key} require a bot restart to take effect.", ephemeral=True)
                else:
                    await interaction.response.send_message(f"Configuration updated. {key} set to {value}", ephemeral=True)

            log(f"Command /config executed by {interaction.user.name}#{interaction.user.discriminator}")
        except Exception as e:
            log(f"Error in /config command: {str(e)}")
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
            log(f"Retrieving user ID for email: {email}")
            tautulli_user_id = self.get_user_id_from_email(email)
            log(f"User ID retrieved: {tautulli_user_id}")

            if not tautulli_user_id:
                log(f"No user found for email: {email}")
                await interaction.followup.send(translations['my_stats_no_user_found'], ephemeral=True)
                return

            log(f"Generating user graphs for user ID: {tautulli_user_id}")
            graph_files = generate_user_graphs(tautulli_user_id, config, translations)
            log(f"Generated {len(graph_files)} graph files")

            if not graph_files:
                log("Failed to generate user graphs")
                await interaction.followup.send(translations['my_stats_generate_failed'], ephemeral=True)
                return

            # Send graphs via PM
            log("Sending graphs via PM")
            dm_channel = await interaction.user.create_dm()
            for graph_file in graph_files:
                log(f"Sending graph file: {graph_file}")
                await dm_channel.send(file=discord.File(graph_file))

            # Update cooldowns
            log("Updating cooldowns")
            self.user_cooldowns[user_id] = datetime.now() + timedelta(minutes=config['MY_STATS_COOLDOWN_MINUTES'])
            self.global_cooldown = datetime.now() + timedelta(seconds=config['MY_STATS_GLOBAL_COOLDOWN_SECONDS'])

            await interaction.followup.send(translations['my_stats_success'], ephemeral=True)
            log(f"Command /my_stats executed successfully by {interaction.user.name}#{interaction.user.discriminator}")

        except Exception as e:
            log(f"Error in /my_stats command: {str(e)}")
            await interaction.followup.send(
                translations['my_stats_error'],
                ephemeral=True
            )

    @app_commands.command(name="update_graphs", description="Update and post the graphs")
    async def update_graphs(self, interaction: discord.Interaction):
        try:
            await interaction.response.defer(ephemeral=True)
            await update_and_post_graphs(self.bot, translations)
            try:
                await interaction.followup.send("Graphs updated and posted.", ephemeral=True)
                log(f"Command /update_graphs executed by {interaction.user.name}#{interaction.user.discriminator}. Graphs updated and posted.")
            except discord.errors.NotFound:
                log(f"Command /update_graphs executed by {interaction.user.name}#{interaction.user.discriminator}. Interaction message deleted. Graphs updated and posted.")
        except Exception as e:
            log(f"Error in /update_graphs command: {str(e)}")
            try:
                await interaction.followup.send("An error occurred while processing the command.", ephemeral=True)
            except discord.errors.NotFound:
                log(f"Error in /update_graphs command: {str(e)}. Interaction message not found.")

    @app_commands.command(name="uptime", description="Show the bot's uptime")
    async def uptime(self, interaction: discord.Interaction):
        try:
            current_time = datetime.now().astimezone()
            uptime = current_time - self.start_time
            await interaction.response.send_message(f"Bot has been running for {uptime}", ephemeral=True)
            log(f"Command /uptime executed by {interaction.user.name}#{interaction.user.discriminator}")
        except Exception as e:
            log(f"Error in /uptime command: {str(e)}")
            await interaction.followup.send(translations['error_processing_command'], ephemeral=True)

    def get_user_id_from_email(self, email):
        if not email:
            log(f"Error: Email is empty or None")
            return None

        try:
            log(f"Sending API request to retrieve users")
            response = requests.get(
                f"{config['TAUTULLI_URL']}/api/v2",
                params={
                    "apikey": config['TAUTULLI_API_KEY'],
                    "cmd": "get_users"
                }
            )
            response.raise_for_status()
            log(f"API response status code: {response.status_code}")
            log(f"API response content: {response.text}")

            users = response.json()['response']['data']
            log(f"Retrieved {len(users)} users from API")

            for user in users:
                log(f"Checking user: {user}")
                if user.get('email') and user['email'].lower() == email.lower():
                    log(f"Found matching user ID: {user['user_id']}")
                    return user['user_id']

            log(f"No user found with email: {email}")
            return None
        except Exception as e:
            log(f"Error fetching user ID from email: {str(e)}")
            return None

async def setup(bot):
    await bot.add_cog(Commands(bot))
    log("Commands cog has been set up.")
