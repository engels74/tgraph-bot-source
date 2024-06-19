# bot/commands.py
import os
from datetime import datetime
import discord
from discord import app_commands
from discord.ext import commands
from config.config import load_config
from i18n import load_translations
from graphs.generate_graphs import update_and_post_graphs
from main import log, config

# Load configuration
config = load_config(os.path.join(os.path.dirname(__file__), '..', 'config', 'config.yml'))

# Load translations
translations = load_translations(config['LANGUAGE'])

class Commands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.start_time = datetime.now()

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

    @app_commands.command(name="set_language", description="Set the language for the bot")
    @app_commands.choices(language=[
        app_commands.Choice(name=language.split('.')[0], value=language.split('.')[0])
        for language in os.listdir(os.path.join(os.path.dirname(__file__), '..', 'i18n'))
    ])
    async def set_language(self, interaction: discord.Interaction, language: str):
        try:
            config['LANGUAGE'] = language
            global translations
            translations = load_translations(language)
            await interaction.response.send_message(f"Language set to {language}. The new language will be used for future graph updates.")
            log(f"Command /set_language executed by {interaction.user.name}#{interaction.user.discriminator}. Language set to {language}")
        except Exception as e:
            log(f"Error in /set_language command: {str(e)}")
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

async def setup(bot):
    await bot.add_cog(Commands(bot))
