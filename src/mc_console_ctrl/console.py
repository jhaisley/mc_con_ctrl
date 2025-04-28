"""Interactive console implementation for Minecraft Command & Control."""

from prompt_toolkit import PromptSession
from prompt_toolkit.completion import Completer, Completion
from rich.console import Console
from rich.panel import Panel
from typing import Iterable
from .minecraft import MinecraftServer


class MinecraftCommandCompleter(Completer):
    def __init__(self, minecraft_server: MinecraftServer):
        self.minecraft_server = minecraft_server

    def _get_player_suggestions(self, word_before_cursor: str) -> Iterable[Completion]:
        """Get player name suggestions from settings or defaults."""
        settings_df = self.minecraft_server.settings_df
        if settings_df is not None and not settings_df.empty:
            # First try to get the default player
            default_player = settings_df[settings_df["setting"] == "default_player"]
            if not default_player.empty:
                player = str(default_player.iloc[0]["value"])
                if player.lower().startswith(word_before_cursor.lower()):
                    yield Completion(
                        player,
                        start_position=-len(word_before_cursor),
                        display_meta="Default player",
                    )

            # Then get all players from the players list
            players_setting = settings_df[settings_df["setting"] == "players"]
            if not players_setting.empty:
                players = players_setting.iloc[0]["value"].split(",")
                for player in players:
                    if player and player.lower().startswith(word_before_cursor.lower()):
                        yield Completion(
                            player,
                            start_position=-len(word_before_cursor),
                            display_meta="Saved player",
                        )

    def get_completions(self, document, complete_event) -> Iterable[Completion]:
        text = document.text
        words = text.split()

        if not words:
            return

        word_before_cursor = document.get_word_before_cursor()
        current_pos = len(words) if document.text.endswith(" ") else len(words) - 1

        # For base commands
        if len(words) == 1:
            commands = {
                "help": "Display help information",
                "exit": "Exit the application",
                "sc": "Send command to Minecraft server",
                "give": "Give items to a player",
                "raw": "Send raw input directly to the server",
                "enchant": "Enchant a player's held item",
                "effect": "Apply effect to a player",
                "effectclear": "Clear all effects from a player",
                "maxenchant": "Apply all possible max level enchantments",
                "namedpos": "Manage named positions",
                "tp": "Teleport player to coordinates or named position",
            }
            for cmd, desc in commands.items():
                if cmd.startswith(word_before_cursor):
                    yield Completion(
                        cmd, start_position=-len(word_before_cursor), display_meta=desc
                    )

        # For player name parameter in any command that needs it
        elif words[0] in [
            "give",
            "enchant",
            "effect",
            "effectclear",
            "maxenchant",
            "tp",
        ]:
            if current_pos == 1:  # First parameter is player name
                yield from self._get_player_suggestions(word_before_cursor)

            # Handle second parameters for specific commands
            elif current_pos == 2:
                if (
                    words[0] == "give"
                    and self.minecraft_server.resources_df is not None
                ):
                    # Get both blocks and items from resources
                    items_df = self.minecraft_server.resources_df[
                        (
                            self.minecraft_server.resources_df["resource_type"].isin(
                                ["block", "item"]
                            )
                        )
                        & (
                            self.minecraft_server.resources_df[
                                "Resource location"
                            ].notna()
                        )
                        & (self.minecraft_server.resources_df["Name"].notna())
                    ][["Resource location", "Name", "resource_type"]]

                    for _, row in items_df.iterrows():
                        item_id = row["Resource location"]
                        item_name = row["Name"]
                        resource_type = row["resource_type"].capitalize()
                        if item_id.lower().startswith(word_before_cursor.lower()):
                            yield Completion(
                                item_id,
                                start_position=-len(word_before_cursor),
                                display_meta=f"{resource_type}: {item_name}",
                            )
                elif words[0] == "tp":
                    # Suggest named positions if available
                    if self.minecraft_server.named_pos_df is not None:
                        for _, row in self.minecraft_server.named_pos_df.iterrows():
                            pos_name = row["pos_name"]
                            pos_value = row["pos_value"]
                            if pos_name.startswith(word_before_cursor):
                                yield Completion(
                                    pos_name,
                                    start_position=-len(word_before_cursor),
                                    display_meta=f"Position: {pos_value}",
                                )

                    # Suggest players with @ prefix
                    settings_df = self.minecraft_server.settings_df
                    if settings_df is not None and not settings_df.empty:
                        players_setting = settings_df[
                            settings_df["setting"] == "players"
                        ]
                        if not players_setting.empty:
                            players = players_setting.iloc[0]["value"].split(",")
                            for player in players:
                                if player:
                                    suggestion = f"@{player}"
                                    # Check if word starts with @ and compare rest with player name
                                    if word_before_cursor.startswith("@"):
                                        if player.lower().startswith(
                                            word_before_cursor[1:].lower()
                                        ):
                                            yield Completion(
                                                suggestion,
                                                start_position=-len(word_before_cursor),
                                                display_meta=f"Teleport to {player}",
                                            )
                                    # If no @ prefix yet, suggest if they start typing the name
                                    elif player.lower().startswith(
                                        word_before_cursor.lower()
                                    ):
                                        yield Completion(
                                            suggestion,
                                            start_position=-len(word_before_cursor),
                                            display_meta=f"Teleport to {player}",
                                        )

                    # Also suggest some common coordinates
                    common_coords = [
                        ("0 0 0", "World origin"),
                        ("0 64 0", "Sea level"),
                        ("~ ~ ~", "Current position"),
                        ("~ ~+10 ~", "10 block above current"),
                        ("~ ~-10 ~", "10 block below current"),
                        ("~-10 ~ ~", "10 blocks behind"),
                        ("~+10 ~ ~", "10 blocks ahead"),
                    ]
                    for coords, desc in common_coords:
                        if coords.startswith(word_before_cursor):
                            yield Completion(
                                coords,
                                start_position=-len(word_before_cursor),
                                display_meta=desc,
                            )

                elif (
                    words[0] == "enchant"
                    and self.minecraft_server.resources_df is not None
                ):
                    enchants_df = self.minecraft_server.resources_df[
                        (
                            self.minecraft_server.resources_df["resource_type"]
                            == "enchantment"
                        )
                        & (
                            self.minecraft_server.resources_df[
                                "Resource location"
                            ].notna()
                        )
                        & (self.minecraft_server.resources_df["Name"].notna())
                    ][["Resource location", "Name", "enchantment_max_level"]]

                    for _, row in enchants_df.iterrows():
                        enchant_id = row["Resource location"]
                        enchant_name = row["Name"]
                        max_level = int(float(row["enchantment_max_level"] or 1))
                        if enchant_id.lower().startswith(word_before_cursor.lower()):
                            yield Completion(
                                enchant_id,
                                start_position=-len(word_before_cursor),
                                display_meta=f"Enchantment: {enchant_name} (Max: {max_level})",
                            )
                elif (
                    words[0] == "effect"
                    and self.minecraft_server.resources_df is not None
                ):
                    effects_df = self.minecraft_server.resources_df[
                        (
                            self.minecraft_server.resources_df["resource_type"]
                            == "effect"
                        )
                        & (
                            self.minecraft_server.resources_df[
                                "Resource location"
                            ].notna()
                        )
                        & (self.minecraft_server.resources_df["Name"].notna())
                    ][["Resource location", "Name"]]

                    for _, row in effects_df.iterrows():
                        effect_id = row["Resource location"]
                        effect_name = row["Name"]
                        if effect_id.lower().startswith(word_before_cursor.lower()):
                            yield Completion(
                                effect_id,
                                start_position=-len(word_before_cursor),
                                display_meta=f"Effect: {effect_name}",
                            )

            # Handle third parameters for specific commands
            elif current_pos == 3:
                if words[0] == "effect":
                    durations = [
                        ("30", "Default duration"),
                        ("60", "1 minute"),
                        ("300", "5 minutes"),
                        ("600", "10 minutes"),
                        ("1200", "20 minutes"),
                        ("3600", "1 hour"),
                    ]
                    for duration, desc in durations:
                        if duration.startswith(word_before_cursor):
                            yield Completion(
                                duration,
                                start_position=-len(word_before_cursor),
                                display_meta=desc,
                            )
                elif words[0] == "enchant" and len(words) > 2:
                    enchantment = words[2]
                    if self.minecraft_server.resources_df is not None:
                        enchant_data = self.minecraft_server.resources_df[
                            (
                                self.minecraft_server.resources_df["resource_type"]
                                == "enchantment"
                            )
                            & (
                                self.minecraft_server.resources_df[
                                    "Resource location"
                                ].str.lower()
                                == enchantment.lower()
                            )
                        ]
                        if not enchant_data.empty:
                            max_level = int(
                                float(
                                    enchant_data.iloc[0]["enchantment_max_level"] or 1
                                )
                            )
                            for level in range(1, max_level + 1):
                                if str(level).startswith(word_before_cursor):
                                    yield Completion(
                                        str(level),
                                        start_position=-len(word_before_cursor),
                                        display_meta=f"Level {level}/{max_level}",
                                    )

            # Handle fourth parameter (amplifier) for effect command
            elif current_pos == 4 and words[0] == "effect":
                amplifiers = [
                    ("0", "Level 1 (Normal)"),
                    ("1", "Level 2"),
                    ("2", "Level 3"),
                    ("4", "Level 5"),
                    ("9", "Level 10"),
                ]
                for amp, desc in amplifiers:
                    if amp.startswith(word_before_cursor):
                        yield Completion(
                            amp,
                            start_position=-len(word_before_cursor),
                            display_meta=desc,
                        )

        # For sc command completions
        elif words[0] == "sc":
            if self.minecraft_server.commands_df is not None:
                commands_data = self.minecraft_server.commands_df[
                    ["command", "description"]
                ].values
                for cmd, desc in commands_data:
                    if cmd and cmd.startswith(word_before_cursor):
                        yield Completion(
                            cmd,
                            start_position=-len(word_before_cursor),
                            display_meta=desc if desc else "Minecraft command",
                        )

        # Handle namedpos command completions
        elif words[0] == "namedpos":
            if current_pos == 1:
                actions = {
                    "list": "List all named positions",
                    "add": "Add a new named position",
                    "del": "Delete a named position",
                }
                for action, desc in actions.items():
                    if action.startswith(word_before_cursor):
                        yield Completion(
                            action,
                            start_position=-len(word_before_cursor),
                            display_meta=desc,
                        )
            elif current_pos == 2 and words[1] == "del":
                # Suggest existing position names for deletion
                if self.minecraft_server.named_pos_df is not None:
                    for _, row in self.minecraft_server.named_pos_df.iterrows():
                        pos_name = row["pos_name"]
                        pos_value = row["pos_value"]
                        if pos_name.startswith(word_before_cursor):
                            yield Completion(
                                pos_name,
                                start_position=-len(word_before_cursor),
                                display_meta=f"Position: {pos_value}",
                            )
        elif words[0] == "player":
            if current_pos == 1:
                # Complete add, del, or list
                actions = {
                    "list": "List all players",
                    "add": "Add a new player",
                    "del": "Remove a player",
                }
                for action, desc in actions.items():
                    if action.startswith(word_before_cursor.lower()):
                        yield Completion(
                            action,
                            start_position=-len(word_before_cursor),
                            display_meta=desc,
                        )
            elif current_pos == 2 and words[1] == "del":
                # When deleting, suggest existing players from the settings
                if self.minecraft_server.settings_df is not None:
                    players_setting = self.minecraft_server.settings_df[
                        self.minecraft_server.settings_df["setting"] == "players"
                    ]
                    if not players_setting.empty:
                        players = players_setting.iloc[0]["value"].split(",")
                        for player in players:
                            if player and player.startswith(word_before_cursor):
                                yield Completion(
                                    player,
                                    start_position=-len(word_before_cursor),
                                    display_meta="Existing player",
                                )
        elif (
            words[0] == "qg"
            and current_pos == 1
            and self.minecraft_server.resources_df is not None
        ):
            # Get both blocks and items from resources
            items_df = self.minecraft_server.resources_df[
                (
                    self.minecraft_server.resources_df["resource_type"].isin(
                        ["block", "item"]
                    )
                )
                & (self.minecraft_server.resources_df["Resource location"].notna())
                & (self.minecraft_server.resources_df["Name"].notna())
            ][["Resource location", "Name", "resource_type"]]

            for _, row in items_df.iterrows():
                item_id = row["Resource location"]
                item_name = row["Name"]
                resource_type = row["resource_type"].capitalize()
                if item_id.lower().startswith(word_before_cursor.lower()):
                    yield Completion(
                        item_id,
                        start_position=-len(word_before_cursor),
                        display_meta=f"{resource_type}: {item_name}",
                    )


class MinecraftConsole:
    def __init__(self, minecraft_server: MinecraftServer):
        self.console = Console()
        self.minecraft_server = minecraft_server
        self.session = PromptSession()
        self.commands = {}

    def register_command(self, name: str, func, help_text: str):
        """Register a new command."""
        self.commands[name] = {"func": func, "help": help_text}

    def get_completer(self):
        """Create command completer for both built-in and Minecraft commands."""
        return MinecraftCommandCompleter(self.minecraft_server)

    async def start(self):
        """Start the interactive console."""
        self.console.print(Panel("Minecraft Console Control", style="bold green"))

        while True:
            try:
                command = await self.session.prompt_async(
                    "mc> ", completer=self.get_completer()
                )

                if not command:
                    continue

                cmd_name = command.split()[0]
                if cmd_name in self.commands:
                    await self.commands[cmd_name]["func"](command)
                else:
                    self.console.print(f"Unknown command: {cmd_name}", style="red")
            except (EOFError, KeyboardInterrupt):
                self.console.print("\nExiting console.", style="yellow")
                break
            except Exception as e:
                self.console.print(f"An error occurred: {e}", style="bold red")
