# bot/commands.py
import discord
import logging
from datetime import datetime, timedelta
from discord import app_commands
from discord.ext import commands
from typing import Optional

# Config imports - clean interface through config.config
from config.config import (
    load_config,
    CONFIGURABLE_OPTIONS,
    RESTART_REQUIRED_KEYS,
    CONFIG_PATH,
    validate_config_value,
    sanitize_config_value
)

# Translation imports
from i18n import load_translations

# Time utilities
from graphs.graph_modules.utils import parse_time, format_time_value

class Commands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.start_time = datetime.now().astimezone()
        self.user_cooldowns = {}
        self.global_cooldown = datetime.now()
        self.config = load_config(CONFIG_PATH)
        self.translations = load_translations(self.config["LANGUAGE"])

    def get_app_commands(self):
        return [
            self.about,
            self.config_command,
            self.my_stats,
            self.update_graphs,
            self.uptime,
        ]

    async def cog_load(self):
        logging.info(self.translations["log_commands_cog_loading"])
        for command in self.get_app_commands():
            logging.info(
                self.translations["log_registering_command"].format(
                    command_name=command.name
                )
            )
        logging.info(self.translations["log_commands_cog_loaded"])

    def update_command_descriptions(self):
        for command in self.get_app_commands():
            translation_key = f"{command.name}_command_description"
            if translation_key in self.translations:
                command.description = self.translations[translation_key]
        logging.info(self.translations["log_command_descriptions_updated"])

    @app_commands.command(name="about")
    async def about(self, interaction: discord.Interaction):
        try:
            embed = discord.Embed(title="TGraph Bot", color=0x3498DB)
            embed.add_field(
                name="Description",
                value=self.translations["about_description"],
                inline=False,
            )
            embed.add_field(
                name=self.translations["about_github"],
                value="https://github.com/engels74/tgraph-bot-source",
                inline=False,
            )
            embed.add_field(
                name=self.translations["about_license"], value="AGPLv3", inline=False
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            logging.info(
                self.translations["log_command_executed"].format(
                    command="about",
                    user=f"{interaction.user.name}#{interaction.user.discriminator}",
                )
            )
        except Exception as e:
            logging.error(
                self.translations["log_command_error"].format(
                    command="about", error=str(e)
                )
            )
            await self._send_error_message(
                interaction, self.translations["error_processing_command"]
            )

    @app_commands.command(name="config")
    @app_commands.choices(
        action=[
            app_commands.Choice(name="View", value="view"),
            app_commands.Choice(name="Edit", value="edit"),
        ]
    )
    @app_commands.choices(
        key=[
            app_commands.Choice(name=option, value=option) for option in CONFIGURABLE_OPTIONS
        ]
    )
    async def config_command(
        self,
        interaction: discord.Interaction,
        action: str,
        key: Optional[str] = None,
        value: Optional[str] = None,
    ):
        """Handle the /config command."""
        try:
            self.config = load_config(CONFIG_PATH, reload=True)

            if action == "view":
                await self._handle_view_config(interaction, key)
            elif action == "edit":
                await self._handle_edit_config(interaction, key, value)

            logging.info(
                self.translations["log_command_executed"].format(
                    command="config",
                    user=f"{interaction.user.name}#{interaction.user.discriminator}",
                )
            )
        except Exception as e:
            logging.error(
                self.translations["log_command_error"].format(
                    command="config", error=str(e)
                )
            )
            await self._send_error_message(
                interaction, self.translations["error_processing_command"]
            )

    async def _handle_view_config(self, interaction: discord.Interaction, key: Optional[str]):
        """Handle viewing configuration values."""
        if key:
            if key in self.config and key in CONFIGURABLE_OPTIONS:
                # Format the value for display
                value = self.config[key]
                if isinstance(value, (str, int, float, bool)):
                    display_value = str(value).strip('"\'')  # Remove quotes for display
                else:
                    display_value = str(value)
                
                await interaction.response.send_message(
                    f"{key}: {display_value}", ephemeral=True
                )
            else:
                await interaction.response.send_message(
                    self.translations["config_view_invalid_key"].format(key=key),
                    ephemeral=True,
                )
        else:
            embed = discord.Embed(title="Bot Configuration", color=0x3498DB)
            for k, v in self.config.items():
                if k in CONFIGURABLE_OPTIONS:
                    # Format the value for display
                    if isinstance(v, (str, int, float, bool)):
                        display_value = str(v).strip('"\'')  # Remove quotes for display
                    else:
                        display_value = str(v)
                    embed.add_field(name=k, value=display_value, inline=False)
            await interaction.response.send_message(embed=embed, ephemeral=True)

    async def _handle_edit_config(
        self, interaction: discord.Interaction, key: Optional[str], value: Optional[str]
    ):
        """Handle editing configuration values."""
        if key is None:
            await interaction.response.send_message(
                self.translations["config_edit_specify_key"], ephemeral=True
            )
            return

        if value is None:
            await interaction.response.send_message(
                self.translations["config_edit_specify_value"], ephemeral=True
            )
            return

        if key not in CONFIGURABLE_OPTIONS:
            await interaction.response.send_message(
                self.translations["config_view_invalid_key"].format(key=key),
                ephemeral=True,
            )
            return

        try:
            # Pre-process and validate value
            if not validate_config_value(key, value):
                raise ValueError(f"Invalid value for {key}: {value}")
                
            # Load current config
            config = load_config(CONFIG_PATH, reload=True)
            
            # Process the value based on the key type
            if key in ["TV_COLOR", "MOVIE_COLOR", "ANNOTATION_COLOR"]:
                if not value.startswith("#"):
                    await interaction.response.send_message(
                        "Color value must start with '#'. Example: #ff0000", 
                        ephemeral=True
                    )
                    return
            elif key == "FIXED_UPDATE_TIME":
                if value.upper() != "XX:XX":
                    if not parse_time(value):
                        await interaction.response.send_message(
                            "Invalid time format. Please use HH:MM format (e.g., 14:30) or XX:XX to disable.", 
                            ephemeral=True
                        )
                        return
                    value = format_time_value(value)
            elif key in ["UPDATE_DAYS", "KEEP_DAYS", "TIME_RANGE_DAYS", 
                        "MY_STATS_COOLDOWN_MINUTES", "MY_STATS_GLOBAL_COOLDOWN_SECONDS"]:
                try:
                    value = int(value)
                    if value <= 0:
                        await interaction.response.send_message(
                            f"{key} must be a positive number.", 
                            ephemeral=True
                        )
                        return
                except ValueError:
                    await interaction.response.send_message(
                        f"{key} must be a number.", 
                        ephemeral=True
                    )
                    return
            elif key.startswith(("ENABLE_", "ANNOTATE_", "CENSOR_")):
                value = value.lower() in ['true', '1', 'yes', 'on']

            # Sanitize the value
            sanitized_value = sanitize_config_value(key, value)
            old_value = config.get(key)
            
            # Update and save config
            config[key] = sanitized_value
            config = load_config(CONFIG_PATH, reload=True)  # Reload to ensure consistency
            
            # Return appropriate message
            if key == "FIXED_UPDATE_TIME" and str(sanitized_value).upper() == "XX:XX":
                response_message = self.translations["config_updated_fixed_time_disabled"].format(key=key)
            elif key in RESTART_REQUIRED_KEYS:
                response_message = self.translations["config_updated_restart"].format(key=key)
            else:
                response_message = self.translations["config_updated"].format(
                    key=key,
                    old_value=old_value,
                    new_value=sanitized_value
                )
            
            await interaction.response.send_message(response_message, ephemeral=True)

            if key == "LANGUAGE":
                self.translations = load_translations(value)
                self.update_command_descriptions()

        except Exception as e:
            logging.error(f"Error updating config value: {str(e)}")
            await interaction.response.send_message(
                f"Error updating configuration: {str(e)}", 
                ephemeral=True
            )

    @app_commands.command(name="my_stats")
    async def my_stats(self, interaction: discord.Interaction, email: str):
        if not await self._check_cooldowns(interaction):
            return

        await interaction.response.defer(ephemeral=True)

        try:
            self.config = load_config(CONFIG_PATH, reload=True)

            user_id = self.bot.data_fetcher.get_user_id_from_email(email)

            if not user_id:
                await interaction.followup.send(
                    self.translations["my_stats_no_user_found"], ephemeral=True
                )
                return

            logging.info(
                self.translations["log_generating_user_graphs"].format(
                    user_id=user_id
                )
            )
            graph_files = await self.bot.user_graph_manager.generate_user_graphs(user_id)
            logging.info(
                self.translations["log_generated_graph_files"].format(
                    count=len(graph_files)
                )
            )

            if not graph_files:
                logging.warning(self.translations["my_stats_generate_failed"])
                await interaction.followup.send(
                    self.translations["my_stats_generate_failed"], ephemeral=True
                )
                return

            # Send graphs via PM
            logging.info(self.translations["log_sending_graphs_pm"])
            dm_channel = await interaction.user.create_dm()
            for graph_file in graph_files:
                logging.info(
                    self.translations["log_sending_graph_file"].format(file=graph_file)
                )
                await dm_channel.send(file=discord.File(graph_file))

            # Update cooldowns
            logging.info(self.translations["log_updating_cooldowns"])
            self.user_cooldowns[str(interaction.user.id)] = datetime.now() + timedelta(
                minutes=self.config["MY_STATS_COOLDOWN_MINUTES"]
            )
            self.global_cooldown = datetime.now() + timedelta(
                seconds=self.config["MY_STATS_GLOBAL_COOLDOWN_SECONDS"]
            )

            await interaction.followup.send(
                self.translations["my_stats_success"], ephemeral=True
            )
            logging.info(
                self.translations["log_command_executed"].format(
                    command="my_stats",
                    user=f"{interaction.user.name}#{interaction.user.discriminator}",
                )
            )

        except Exception as e:
            logging.error(
                self.translations["log_command_error"].format(
                    command="my_stats", error=str(e)
                )
            )
            await self._send_error_message(
                interaction, self.translations["my_stats_error"]
            )

    @app_commands.command(name="update_graphs")
    async def update_graphs(self, interaction: discord.Interaction):
        try:
            await interaction.response.defer(ephemeral=True)
            logging.info(self.translations["log_manual_update_started"])

            self.config = load_config(CONFIG_PATH, reload=True)
            self.bot.update_tracker.update_config(self.config)

            channel = self.bot.get_channel(self.config["CHANNEL_ID"])
            await self.bot.graph_manager.delete_old_messages(channel)
            
            graph_files = await self.bot.graph_manager.generate_and_save_graphs()
            
            if graph_files:
                await self.bot.graph_manager.post_graphs(channel, graph_files)

            self.bot.update_tracker.update()
            next_update = self.bot.update_tracker.get_next_update_readable()

            logging.info(self.translations["log_manual_update_completed"])
            await interaction.followup.send(
                self.translations["update_graphs_success"].format(
                    next_update=next_update
                ),
                ephemeral=True,
            )
            logging.info(
                self.translations["log_command_executed"].format(
                    command="update_graphs",
                    user=f"{interaction.user.name}#{interaction.user.discriminator}",
                )
            )
            logging.info(
                self.translations["log_graphs_updated_posted"].format(
                    next_update=next_update
                )
            )
        except Exception as e:
            logging.error(
                self.translations["log_command_error"].format(
                    command="update_graphs", error=str(e)
                )
            )
            await self._send_error_message(
                interaction, self.translations["update_graphs_error"]
            )

    @app_commands.command(name="uptime")
    async def uptime(self, interaction: discord.Interaction):
        try:
            current_time = datetime.now().astimezone()
            uptime = current_time - self.start_time
            await interaction.response.send_message(
                self.translations["uptime_response"].format(uptime=uptime),
                ephemeral=True,
            )
            logging.info(
                self.translations["log_command_executed"].format(
                    command="uptime",
                    user=f"{interaction.user.name}#{interaction.user.discriminator}",
                )
            )
        except Exception as e:
            logging.error(
                self.translations["log_command_error"].format(
                    command="uptime", error=str(e)
                )
            )
            await self._send_error_message(
                interaction, self.translations["error_processing_command"]
            )

    async def _check_cooldowns(self, interaction: discord.Interaction):
        # Check global cooldown
        if datetime.now() < self.global_cooldown:
            remaining = int((self.global_cooldown - datetime.now()).total_seconds())
            await interaction.response.send_message(
                self.translations["rate_limit_global"].format(
                    time=f"<t:{int((datetime.now() + timedelta(seconds=remaining)).timestamp())}:R>"
                ),
                ephemeral=True,
            )
            return False

        # Check user cooldown
        user_id = str(interaction.user.id)
        if (
            user_id in self.user_cooldowns
            and datetime.now() < self.user_cooldowns[user_id]
        ):
            remaining = int(
                (self.user_cooldowns[user_id] - datetime.now()).total_seconds()
            )
            await interaction.response.send_message(
                self.translations["rate_limit_user"].format(
                    time=f"<t:{int((datetime.now() + timedelta(seconds=remaining)).timestamp())}:R>"
                ),
                ephemeral=True,
            )
            return False

        return True

    async def _send_error_message(self, interaction, error_message):
        try:
            if interaction.response.is_done():
                await interaction.followup.send(error_message, ephemeral=True)
            else:
                await interaction.response.send_message(error_message, ephemeral=True)
        except discord.errors.HTTPException as http_err:
            logging.error(f"Failed to send error message: {str(http_err)}")
        except Exception as inner_e:
            logging.error(
                f"Unexpected error when sending error message: {str(inner_e)}"
            )

async def setup(bot):
    await bot.add_cog(Commands(bot))
    logging.info(bot.translations["log_commands_cog_setup"])
