# bot/commands.py
import discord
import logging
import requests
from config.config import (
    load_config,
    update_config,
    RESTART_REQUIRED_KEYS,
    get_configurable_options,
    CONFIG_PATH,
    format_color_value,
)
from datetime import datetime, timedelta
from discord import app_commands
from discord.ext import commands
from graphs.generate_graphs import update_and_post_graphs
from graphs.generate_graphs_user import generate_user_graphs
from i18n import load_translations

# Get configurable options
CONFIG_OPTIONS = get_configurable_options()


class Commands(commands.Cog):
    def __init__(self, bot, translations):
        self.bot = bot
        self.start_time = datetime.now().astimezone()
        self.user_cooldowns = {}
        self.global_cooldown = datetime.now()
        self.config = load_config(CONFIG_PATH)
        self.translations = translations
        logging.info("[DEBUG] Commands class initialized")
        logging.info(f"[DEBUG] Loaded translations: {self.translations}")

    def get_app_commands(self):
        return [
            self.about,
            self.config_command,
            self.my_stats,
            self.update_graphs,
            self.uptime
        ]

    async def cog_load(self):
        logging.info("[DEBUG] Cog load started")
        logging.info(self.translations["log_commands_cog_loading"])
        for command in self.get_app_commands():
            logging.info(
                self.translations["log_registering_command"].format(
                    command_name=command.name
                )
            )
            logging.info(f"[DEBUG] Command /{command.name} description: {command.description}")
        logging.info(self.translations["log_commands_cog_loaded"])
        logging.info("[DEBUG] Cog load completed")

    def update_command_descriptions(self):
        logging.info("[DEBUG] Updating command descriptions")
        logging.info(f"[DEBUG] Available translations keys: {self.translations.keys()}")
        for command in self.get_app_commands():
            translation_key = f"{command.name}_command_description"
            logging.info(f"[DEBUG] Looking for translation key: {translation_key}")
            if translation_key in self.translations:
                command.description = self.translations[translation_key]
                logging.info(f"[DEBUG] Updated description for /{command.name}: {command.description}")
            else:
                logging.info(f"[DEBUG] No translation found for /{command.name}")
            logging.info(f"[DEBUG] Final description for /{command.name}: {command.description}")
        logging.info(self.translations["log_command_descriptions_updated"])

    def _create_about_embed(self):
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
        return embed

    @app_commands.command(name="about")
    async def about(self, interaction: discord.Interaction):
        try:
            embed = self._create_about_embed()
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
            app_commands.Choice(name=option, value=option) for option in CONFIG_OPTIONS
        ]
    )
    async def config_command(
        self,
        interaction: discord.Interaction,
        action: str,
        key: str = None,
        value: str = None,
    ):
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

    async def _handle_view_config(self, interaction: discord.Interaction, key: str):
        if key:
            if key in self.config and key in CONFIG_OPTIONS:
                await interaction.response.send_message(
                    f"{key}: {self.config[key]}", ephemeral=True
                )
            else:
                await interaction.response.send_message(
                    self.translations["config_view_invalid_key"].format(key=key),
                    ephemeral=True,
                )
        else:
            embed = discord.Embed(title="Bot Configuration", color=0x3498DB)
            for k, v in self.config.items():
                if k in CONFIG_OPTIONS:
                    embed.add_field(name=k, value=str(v), inline=False)
            await interaction.response.send_message(embed=embed, ephemeral=True)

    async def _handle_edit_config(self, interaction: discord.Interaction, key: str, value: str):
        if key is None or value is None:
            await interaction.response.send_message(
                self.translations["config_edit_specify_key_value"], ephemeral=True
            )
            return

        if key not in CONFIG_OPTIONS:
            await interaction.response.send_message(
                self.translations["config_view_invalid_key"].format(key=key),
                ephemeral=True,
            )
            return

        old_value = self.config.get(key, "N/A")
        new_value = self._process_config_value(key, value)
        self.config = update_config(key, new_value, self.translations)

        self._sync_update_tracker(self.config)
        self._update_translations_if_needed(key, new_value)

        response_message = self._prepare_response_message(key, old_value, new_value)
        await self._send_config_update_response(interaction, key, response_message)

    def _process_config_value(self, key: str, value: str):
        if isinstance(self.config.get(key), bool):
            return value.lower() == "true"
        elif isinstance(self.config.get(key), int):
            return int(value)
        elif key in ["TV_COLOR", "MOVIE_COLOR", "ANNOTATION_COLOR"]:
            return format_color_value(value)
        elif key == "FIXED_UPDATE_TIME":
            try:
                return self._validate_fixed_update_time(value)
            except ValueError as e:
                raise ValueError(str(e))
        return value

    def _validate_fixed_update_time(self, value):
        if value.upper() == "XX:XX":
            return None
        try:
            return datetime.strptime(value, "%H:%M").time()
        except ValueError as err:
            raise ValueError(
                f"Invalid time format: {value}. Use HH:MM or XX:XX to disable."
            ) from err

    def _update_translations_if_needed(self, key: str, value: str):
        if key == "LANGUAGE":
            self.translations = load_translations(value)
            self.update_command_descriptions()

    def _prepare_response_message(self, key: str, old_value: str, new_value: str) -> str:
        if key == "FIXED_UPDATE_TIME":
            if new_value is None:
                return self.translations["config_updated_fixed_time_disabled"].format(key=key)
            return self.translations["config_updated"].format(
                key=key, old_value=old_value, new_value=new_value.strftime("%H:%M")
            )
        return self.translations["config_updated"].format(
            key=key, old_value=old_value, new_value=new_value
        )

    async def _send_config_update_response(self, interaction: discord.Interaction, key: str, message: str):
        if key in RESTART_REQUIRED_KEYS:
            await interaction.response.send_message(
                self.translations["config_updated_restart"].format(key=key),
                ephemeral=True,
            )
        else:
            await interaction.response.send_message(message, ephemeral=True)

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
        if user_id in self.user_cooldowns and datetime.now() < self.user_cooldowns[user_id]:
            remaining = int((self.user_cooldowns[user_id] - datetime.now()).total_seconds())
            await interaction.response.send_message(
                self.translations["rate_limit_user"].format(
                    time=f"<t:{int((datetime.now() + timedelta(seconds=remaining)).timestamp())}:R>"
                ),
                ephemeral=True,
            )
            return False

        return True

    @app_commands.command(name="my_stats")
    async def my_stats(self, interaction: discord.Interaction, email: str):
        if not await self._check_cooldowns(interaction):
            return

        await interaction.response.defer(ephemeral=True)

        try:
            # Reload configuration
            self.config = load_config(CONFIG_PATH, reload=True)

            tautulli_user_id = self.get_user_id_from_email(email)

            if not tautulli_user_id:
                await interaction.followup.send(
                    self.translations["my_stats_no_user_found"], ephemeral=True
                )
                return

            logging.info(
                self.translations["log_generating_user_graphs"].format(
                    user_id=tautulli_user_id
                )
            )
            graph_files = generate_user_graphs(
                tautulli_user_id, self.bot.img_folder, self.config, self.translations
            )
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

            # Reload config and update the tracker
            self.config = load_config(CONFIG_PATH, reload=True)
            self._sync_update_tracker(self.config)

            # Perform the graph update
            await update_and_post_graphs(self.bot, self.translations, self.config)

            # Update the tracker and get the next update time
            self.bot.update_tracker.update()
            try:
                next_update = self.bot.update_tracker.next_update.strftime(
                    "%Y-%m-%d %H:%M:%S"
                )
            except Exception as e:
                logging.error(f"Error getting next update timestamp: {str(e)}")
                next_update = "Unknown"

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

    def get_user_id_from_email(self, email):
        if not email:
            return None

        try:
            response = requests.get(
                f"{self.config['TAUTULLI_URL']}/api/v2",
                params={"apikey": self.config["TAUTULLI_API_KEY"], "cmd": "get_users"},
            )
            response.raise_for_status()
            users = response.json()["response"]["data"]

            for user in users:
                if user.get("email") and user["email"].lower() == email.lower():
                    return user["user_id"]

            return None
        except Exception as e:
            logging.error(
                self.translations["error_fetching_user_id"].format(error=str(e))
            )
            return None

    def _sync_update_tracker(self, new_config):
        try:
            self.bot.update_tracker.update_config(new_config)
            self.bot.update_tracker.reset()
        except Exception as e:
            logging.error(f"Error updating tracker config: {str(e)}")

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

    def update_command_descriptions(self):
        # Update translations in other modules
        from graphs import generate_graphs
        generate_graphs.translations = self.translations
        from graphs import generate_graphs_user
        generate_graphs_user.translations = self.translations


async def setup(bot):
    logging.info("[DEBUG] Setup function called")
    config = load_config(CONFIG_PATH)
    translations = load_translations(config["LANGUAGE"])
    commands_cog = Commands(bot, translations)
    await bot.add_cog(commands_cog)
    logging.info("[DEBUG] Cog added to bot")
    commands_cog.update_command_descriptions()
    logging.info("[DEBUG] Command descriptions updated")
    logging.info(translations["log_commands_cog_setup"])
    logging.info("[DEBUG] Setup function completed")
