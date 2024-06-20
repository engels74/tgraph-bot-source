# bot/commands.py
import os
from datetime import datetime
import discord
from discord import app_commands
from discord.ext import commands
from config.config import load_config, update_config, RESTART_REQUIRED_KEYS
from i18n import load_translations
from graphs.generate_graphs import update_and_post_graphs
from main import log

# Load configuration
config = load_config()

# Load translations
translations = load_translations(config['LANGUAGE'])

class Commands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.start_time = datetime.now()

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
            await interaction.response.send_message(embed=embed)
            log(f"Command /about executed by {interaction.user.name}#{interaction.user.discriminator}")
        except Exception as e:
            log(f"Error in /about command: {str(e)}")
            await interaction.response.send_message("An error occurred while processing the command.")

    @app_commands.command(name="update_graphs", description="Update and post the graphs")
    async def update_graphs(self, interaction: discord.Interaction):
        try:
            await interaction.response.defer()
            await update_and_post_graphs(self.bot, translations)
            try:
                await interaction.followup.send("Graphs updated and posted.")
                log(f"Command /update_graphs executed by {interaction.user.name}#{interaction.user.discriminator}. Graphs updated and posted.")
            except discord.errors.NotFound:
                log(f"Command /update_graphs executed by {interaction.user.name}#{interaction.user.discriminator}. Interaction message deleted. Graphs updated and posted.")
        except Exception as e:
            log(f"Error in /update_graphs command: {str(e)}")
            try:
                await interaction.followup.send("An error occurred while processing the command.")
            except discord.errors.NotFound:
                log(f"Error in /update_graphs command: {str(e)}. Interaction message not found.")

    @app_commands.command(name="uptime", description="Show the bot's uptime")
    async def uptime(self, interaction: discord.Interaction):
        try:
            current_time = datetime.now()
            uptime = current_time - self.start_time
            await interaction.response.send_message(f"Bot has been running for {uptime}")
            log(f"Command /uptime executed by {interaction.user.name}#{interaction.user.discriminator}")
        except Exception as e:
            log(f"Error in /uptime command: {str(e)}")
            await interaction.response.send_message("An error occurred while processing the command.")

    @app_commands.command(name="bot_config", description="View or edit bot configuration")
    @app_commands.choices(action=[
        app_commands.Choice(name="View", value="view"),
        app_commands.Choice(name="Edit", value="edit")
    ])
    async def bot_config(self, interaction: discord.Interaction, action: str, key: str = None, value: str = None):
        try:
            if action == "view":
                embed = discord.Embed(title="Bot Configuration", color=0x3498db)
                for k, v in config.items():
                    if k != 'timezone':
                        embed.add_field(name=k, value=str(v), inline=False)
                await interaction.response.send_message(embed=embed)
            elif action == "edit":
                if key is None or value is None:
                    await interaction.response.send_message("Both key and value must be provided for editing.")
                    return
                
                if key not in config:
                    await interaction.response.send_message(f"Invalid configuration key: {key}")
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
                    global translations
                    translations = load_translations(value)

                # Send response
                if key in RESTART_REQUIRED_KEYS:
                    await interaction.response.send_message(f"Configuration updated. Note: Changes to {key} require a bot restart to take effect.")
                else:
                    await interaction.response.send_message(f"Configuration updated. {key} set to {value}")

            log(f"Command /bot_config executed by {interaction.user.name}#{interaction.user.discriminator}")
        except Exception as e:
            log(f"Error in /bot_config command: {str(e)}")
            await interaction.response.send_message("An error occurred while processing the command.")

async def setup(bot):
    await bot.add_cog(Commands(bot))
    log("Commands cog has been set up.")
