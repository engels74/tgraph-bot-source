# bot/commands.py
import os
from datetime import datetime
import discord
from discord import app_commands
from discord.ext import commands
from config.config import load_config
from i18n import load_translations
from graphs.generate_graphs import update_and_post_graphs

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
        embed = discord.Embed(title="TGraph Bot", color=0x3498db)
        embed.add_field(name="GitHub", value="https://github.com/engels74/tgraph-bot-source", inline=False)
        embed.add_field(name="License", value="AGPLv3", inline=False)
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="set_language", description="Set the language for the bot")
    @app_commands.choices(language=[
        app_commands.Choice(name=language.split('.')[0], value=language.split('.')[0])
        for language in os.listdir(os.path.join(os.path.dirname(__file__), '..', 'i18n'))
    ])
    async def set_language(self, interaction: discord.Interaction, language: str):
        config['LANGUAGE'] = language
        translations = load_translations(language)
        await interaction.response.send_message(f"Language set to {language}")

    @app_commands.command(name="update_graphs", description="Update and post the graphs")
    async def update_graphs(self, interaction: discord.Interaction):
        await interaction.response.defer()
        await update_and_post_graphs(self.bot)
        await interaction.followup.send("Graphs updated and posted.")

    @app_commands.command(name="uptime", description="Show the bot's uptime")
    async def uptime(self, interaction: discord.Interaction):
        current_time = datetime.now()
        uptime = current_time - self.start_time
        await interaction.response.send_message(f"Bot has been running for {uptime}")

async def setup(bot):
    await bot.add_cog(Commands(bot))
