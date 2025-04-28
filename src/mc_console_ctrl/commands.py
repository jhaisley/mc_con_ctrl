"""Command system implementation for Minecraft Command & Control."""

from typing import Dict, Any, Callable, Awaitable
from rich.console import Console
import pandas as pd
import sqlite3
from .minecraft import MinecraftServer


class CommandRegistry:
    def __init__(self, minecraft_server: MinecraftServer):
        self.console = Console()
        self.commands: Dict[str, dict[str, Any]] = {}
        self.minecraft_server = minecraft_server
        self._register_builtin_commands()

    def _register_builtin_commands(self):
        """Register built-in commands."""
        self.register_command(
            "help",
            self.help_command,
            "Display help information about available commands",
        )
        self.register_command("exit", self.exit_command, "Exit the application")
        self.register_command(
            "sc", self.send_command, "Send a command to the Minecraft server"
        )
        self.register_command(
            "raw", self.raw_command, "Send raw input directly to the server"
        )
        self.register_command(
            "give",
            self.give_command,
            "Give items to a player (give playername block qty)",
        )
        self.register_command(
            "enchant",
            self.enchant_command,
            "Enchant a player's held item (enchant playername enchantment level)",
        )
        self.register_command(
            "effect",
            self.effect_command,
            "Apply effect to a player (effect player effect [seconds] [amplifier] [hideParticles])",
        )
        self.register_command(
            "effectclear",
            self.effectclear_command,
            "Clear all effects from a player (effectclear playername)",
        )
        self.register_command(
            "maxenchant",
            self.maxenchant_command,
            "Apply all possible max level enchantments for an item type (maxenchant itemtype playername)",
        )
        self.register_command(
            "namedpos",
            self.namedpos_command,
            "Manage named positions (namedpos list | namedpos add|del <pos_name> <x y z>)",
        )
        self.register_command(
            "player",
            self.player_command,
            "Manage players list (player list | player add|del <playername>)",
        )
        self.register_command(
            "qg",
            self.quickgive_command,
            "Quickly give items to default player (qg <item> [quantity])",
        )
        self.register_command(
            "tp",
            self.tp_command,
            "Teleport a player to coordinates, named position, or another player.",
        )

    def register_command(
        self, name: str, handler: Callable[[str], Awaitable[None]], help_text: str
    ):
        """Register a new command."""
        self.commands[name] = {"handler": handler, "help": help_text}

    async def help_command(self, _: str) -> None:
        """Display help information."""
        self.console.print("\nAvailable Commands:", style="bold green")
        for cmd_name, cmd_info in sorted(self.commands.items()):
            self.console.print(f"  {cmd_name}: {cmd_info['help']}")
        self.console.print()

    async def exit_command(self, _: str) -> None:
        """Exit the application."""
        self.console.print("\nGoodbye!", style="bold blue")
        raise SystemExit(0)

    async def send_command(self, cmd_line: str) -> None:
        """Send a command to the Minecraft server."""
        # Remove 'sc' from the beginning of the command
        _, *args = cmd_line.split()
        if not args:
            self.console.print("[yellow]Usage: sc <command>")
            return

        mc_command = " ".join(args)
        try:
            result = await self.minecraft_server.send_command(mc_command)
            self.console.print(f"[green]{result}")
        except Exception as e:
            self.console.print(f"[red]Error sending command: {e}")

    async def raw_command(self, cmd_line: str) -> None:
        """Send raw input directly to the server."""
        # Remove 'raw' from the beginning of the command
        _, *args = cmd_line.split(maxsplit=1)
        if not args:
            self.console.print("[yellow]Usage: raw <text>")
            return

        raw_input = args[0]  # Take the rest of the line as is
        try:
            result = await self.minecraft_server.send_command(raw_input)
            self.console.print(f"[green]{result}")
        except Exception as e:
            self.console.print(f"[red]Error sending command: {e}")

    async def give_command(self, cmd_line: str) -> None:
        """Give items to a player."""
        parts = cmd_line.split()
        if len(parts) < 3:
            self.console.print("[yellow]Usage: give <playername> <item> [quantity]")
            return

        _, player, item, *rest = parts
        quantity = rest[0] if rest else "1"

        try:
            # Verify item exists in resources
            if self.minecraft_server.resources_df is not None:
                # Case-insensitive resource location matching for both blocks and items
                item_data = self.minecraft_server.resources_df[
                    (
                        self.minecraft_server.resources_df["resource_type"].isin(
                            ["block", "item"]
                        )
                    )
                    & (
                        self.minecraft_server.resources_df[
                            "Resource location"
                        ].str.lower()
                        == item.lower()
                    )
                ]

                if item_data.empty:
                    self.console.print(f"[red]Invalid item: {item}")
                    # Show similar item suggestions with resource locations
                    items_df = self.minecraft_server.resources_df[
                        self.minecraft_server.resources_df["resource_type"].isin(
                            ["block", "item"]
                        )
                    ][["Resource location", "Name", "resource_type"]]

                    suggestions = []
                    for _, row in items_df.iterrows():
                        if item.lower() in row["Resource location"].lower():
                            resource_type = row["resource_type"].capitalize()
                            suggestions.append(
                                (row["Resource location"], row["Name"], resource_type)
                            )
                            if len(suggestions) >= 5:
                                break

                    if suggestions:
                        self.console.print("[yellow]Did you mean one of these?")
                        for resource_loc, name, resource_type in suggestions:
                            self.console.print(
                                f"  - {resource_loc} ({resource_type}: {name})"
                            )
                    return

                # Use the correct case from the database
                item = item_data.iloc[0]["Resource location"]

            # Construct and send the give command
            mc_command = f"give {player} {item} {quantity}"
            result = await self.minecraft_server.send_command(mc_command)
            self.console.print(f"[green]{result}")

        except Exception as e:
            self.console.print(f"[red]Error giving items: {e}")

    async def enchant_command(self, cmd_line: str) -> None:
        """Enchant a player's held item."""
        parts = cmd_line.split()
        if len(parts) < 3:
            self.console.print(
                "[yellow]Usage: enchant <playername> <enchantment> [level]"
            )
            return

        _, player, enchantment, *rest = parts
        level = rest[0] if rest else "1"

        try:
            # Verify enchantment exists in resources
            if self.minecraft_server.resources_df is not None:
                # Case-insensitive resource location matching
                enchant_data = self.minecraft_server.resources_df[
                    (
                        self.minecraft_server.resources_df["resource_type"].str.lower()
                        == "enchantment"
                    )
                    & (
                        self.minecraft_server.resources_df[
                            "Resource location"
                        ].str.lower()
                        == enchantment.lower()
                    )
                ]

                if enchant_data.empty:
                    self.console.print(f"[red]Invalid enchantment: {enchantment}")
                    # Show similar enchantment suggestions with resource locations
                    enchants_df = self.minecraft_server.resources_df[
                        self.minecraft_server.resources_df["resource_type"].str.lower()
                        == "enchantment"
                    ][["Resource location", "Name", "enchantment_max_level"]]

                    suggestions = []
                    for _, row in enchants_df.iterrows():
                        if enchantment.lower() in row["Resource location"].lower():
                            max_level = row["enchantment_max_level"] or 1
                            suggestions.append(
                                (row["Resource location"], row["Name"], max_level)
                            )
                            if len(suggestions) >= 5:
                                break

                    if suggestions:
                        self.console.print("[yellow]Did you mean one of these?")
                        for resource_loc, name, max_level in suggestions:
                            self.console.print(
                                f"  - {resource_loc} ({name}, Max Level: {max_level})"
                            )
                    return

                # Use the correct case from the database
                enchantment = enchant_data.iloc[0]["Resource location"]
                max_level = enchant_data.iloc[0]["enchantment_max_level"] or 1

                # Validate level
                try:
                    level_num = int(level)
                    if level_num < 1 or level_num > max_level:
                        self.console.print(
                            f"[yellow]Warning: Level should be between 1 and {max_level}"
                        )
                        level = str(min(max(1, level_num), max_level))
                except ValueError:
                    self.console.print("[yellow]Invalid level, using 1")
                    level = "1"

            # Construct and send the enchant command
            mc_command = f"enchant {player} {enchantment} {level}"
            result = await self.minecraft_server.send_command(mc_command)
            self.console.print(f"[green]{result}")

        except Exception as e:
            self.console.print(f"[red]Error applying enchantment: {e}")

    async def effect_command(self, cmd_line: str) -> None:
        """Apply an effect to a player."""
        parts = cmd_line.split()
        if len(parts) < 3:
            self.console.print(
                "[yellow]Usage: effect <player> <effect> [seconds] [amplifier] [hideParticles]"
            )
            return

        _, player, effect, *rest = parts
        seconds = rest[0] if len(rest) > 0 else "30"  # Default 30 seconds
        amplifier = rest[1] if len(rest) > 1 else "0"  # Default level 1 (amplifier 0)
        hide_particles = rest[2] if len(rest) > 2 else "true"  # Default hide particles

        try:
            # Verify effect exists in resources
            if self.minecraft_server.resources_df is not None:
                # Case-insensitive resource location matching
                effect_data = self.minecraft_server.resources_df[
                    (
                        self.minecraft_server.resources_df["resource_type"].str.lower()
                        == "effect"
                    )
                    & (
                        self.minecraft_server.resources_df[
                            "Resource location"
                        ].str.lower()
                        == effect.lower()
                    )
                ]

                if effect_data.empty:
                    self.console.print(f"[red]Invalid effect: {effect}")
                    # Show similar effect suggestions with resource locations
                    effects_df = self.minecraft_server.resources_df[
                        self.minecraft_server.resources_df["resource_type"].str.lower()
                        == "effect"
                    ][["Resource location", "Name"]]

                    suggestions = []
                    for _, row in effects_df.iterrows():
                        if effect.lower() in row["Resource location"].lower():
                            suggestions.append((row["Resource location"], row["Name"]))
                            if len(suggestions) >= 5:
                                break

                    if suggestions:
                        self.console.print("[yellow]Did you mean one of these?")
                        for resource_loc, name in suggestions:
                            self.console.print(f"  - {resource_loc} ({name})")
                    return

                # Use the correct case from the database
                effect = effect_data.iloc[0]["Resource location"]

                # Validate seconds
                try:
                    seconds_num = int(seconds)
                    if seconds_num < 1:
                        self.console.print(
                            "[yellow]Warning: Duration must be at least 1 second"
                        )
                        seconds = "1"
                except ValueError:
                    self.console.print("[yellow]Invalid duration, using 30 seconds")
                    seconds = "30"

                # Validate amplifier
                try:
                    amp_num = int(amplifier)
                    if amp_num < 0 or amp_num > 255:
                        self.console.print(
                            "[yellow]Warning: Amplifier must be between 0 and 255"
                        )
                        amplifier = str(min(max(0, amp_num), 255))
                except ValueError:
                    self.console.print("[yellow]Invalid amplifier, using 0")
                    amplifier = "0"

            # Construct and send the effect command
            mc_command = (
                f"effect {player} {effect} {seconds} {amplifier} {hide_particles}"
            )
            result = await self.minecraft_server.send_command(mc_command)
            self.console.print(f"[green]{result}")

        except Exception as e:
            self.console.print(f"[red]Error applying effect: {e}")

    async def effectclear_command(self, cmd_line: str) -> None:
        """Clear all effects from a player."""
        parts = cmd_line.split()
        if len(parts) < 2:
            self.console.print("[yellow]Usage: effectclear <playername>")
            return

        _, player = parts

        try:
            # Construct and send the effect clear command
            mc_command = f"effect clear {player}"
            result = await self.minecraft_server.send_command(mc_command)
            self.console.print(f"[green]{result}")

        except Exception as e:
            self.console.print(f"[red]Error clearing effects: {e}")

    async def maxenchant_command(self, cmd_line: str) -> None:
        """Apply all possible max level enchantments for an item type."""
        parts = cmd_line.split()
        if len(parts) < 3:
            self.console.print("[yellow]Usage: maxenchant <itemtype> <playername>")
            return

        # Handle multi-word item types by assuming the last word is the player name
        _, *itemtype_parts, player = parts
        itemtype = " ".join(itemtype_parts)

        try:
            if self.minecraft_server.resources_df is not None:
                # Get all enchantments that can be applied to this item type
                enchantments_df = self.minecraft_server.resources_df[
                    (
                        self.minecraft_server.resources_df["resource_type"]
                        == "enchantment"
                    )
                    & (self.minecraft_server.resources_df["Resource location"].notna())
                    & (
                        self.minecraft_server.resources_df[
                            "enchantment_applies_to"
                        ].notna()
                    )
                ]

                matching_enchants = []
                itemtype_lower = itemtype.lower()

                for _, row in enchantments_df.iterrows():
                    applies_to = str(row["enchantment_applies_to"]).lower()
                    if "any" in applies_to or itemtype_lower in applies_to:
                        matching_enchants.append(
                            {
                                "id": row["Resource location"],
                                "name": row["Name"],
                                "max_level": int(
                                    float(row["enchantment_max_level"] or 1)
                                ),
                            }
                        )

                if not matching_enchants:
                    self.console.print(
                        f"[yellow]No enchantments found for item type: {itemtype}"
                    )
                    # Show valid item types from the database
                    item_types = set()
                    for _, row in enchantments_df.iterrows():
                        if row["enchantment_applies_to"]:
                            types = [
                                t.strip()
                                for t in str(row["enchantment_applies_to"]).split(",")
                            ]
                            item_types.update(types)

                    self.console.print("[yellow]Valid item types:")
                    for item_type in sorted(item_types):
                        self.console.print(f"  - {item_type}")
                    return

                # Apply each enchantment at its maximum level
                self.console.print(
                    f"[green]Applying {len(matching_enchants)} enchantments to {player}'s {itemtype}..."
                )

                for enchant in matching_enchants:
                    mc_command = (
                        f"enchant {player} {enchant['id']} {enchant['max_level']}"
                    )
                    try:
                        result = await self.minecraft_server.send_command(mc_command)
                        self.console.print(
                            f"[green]{enchant['name']} (Level {enchant['max_level']}): {result}"
                        )
                    except Exception as e:
                        self.console.print(
                            f"[red]Failed to apply {enchant['name']}: {e}"
                        )

                self.console.print("[green]Finished applying enchantments!")

        except Exception as e:
            self.console.print(f"[red]Error applying enchantments: {e}")

    async def namedpos_command(self, cmd_line: str) -> None:
        """Manage named positions."""
        parts = cmd_line.split()
        if len(parts) < 2:
            self.console.print(
                "[yellow]Usage: namedpos list | namedpos add|del <pos_name> <x y z>"
            )
            return

        action = parts[1].lower()

        if action not in ["add", "del", "list"]:
            self.console.print("[yellow]Action must be either 'add', 'del', or 'list'")
            return

        try:
            named_pos_df = self.minecraft_server.named_pos_df
            if named_pos_df is None:
                named_pos_df = pd.DataFrame(columns=["pos_name", "pos_value"])
                self.minecraft_server.named_pos_df = named_pos_df

            if action == "list":
                if len(named_pos_df) == 0:
                    self.console.print("[yellow]No named positions defined")
                else:
                    self.console.print("\n[green]Named Positions:")
                    for _, row in named_pos_df.iterrows():
                        self.console.print(f"  {row['pos_name']}: {row['pos_value']}")
                    self.console.print()
                return

            if len(parts) < 4:
                self.console.print("[yellow]Usage: namedpos add|del <pos_name> <x y z>")
                return

            pos_name = parts[2]

            if action == "add":
                # Join all remaining parts and clean up the position value
                pos_value = " ".join(parts[3:]).replace(",", " ")
                # Split by whitespace and filter out empty strings
                coords = [x for x in pos_value.split() if x]

                if len(coords) != 3:
                    self.console.print("[yellow]Position must be three numbers (x y z)")
                    return

                try:
                    # Verify all coordinates are valid numbers
                    [float(x) for x in coords]
                except ValueError:
                    self.console.print("[yellow]Position coordinates must be numbers")
                    return

                # Format position value consistently
                pos_value = " ".join(coords)

                # Check if position name already exists
                existing = named_pos_df[named_pos_df["pos_name"] == pos_name]
                if not existing.empty:
                    self.console.print(
                        f"[yellow]Position '{pos_name}' already exists with value {existing.iloc[0]['pos_value']}"
                    )
                    return

                # Add new position
                named_pos_df.loc[len(named_pos_df)] = [pos_name, pos_value]
                self.console.print(
                    f"[green]Added position '{pos_name}' with coordinates {pos_value}"
                )

            else:  # del
                existing = named_pos_df[named_pos_df["pos_name"] == pos_name]
                if existing.empty:
                    self.console.print(f"[yellow]Position '{pos_name}' does not exist")
                    return

                # Remove the position
                self.minecraft_server.named_pos_df = named_pos_df[
                    named_pos_df["pos_name"] != pos_name
                ]
                self.console.print(f"[green]Removed position '{pos_name}'")

            # Save to database
            conn = sqlite3.connect("data.sqlite")
            if action == "add":
                conn.execute(
                    "INSERT INTO named_pos (pos_name, pos_value) VALUES (?, ?)",
                    (pos_name, pos_value),
                )
            else:  # del
                conn.execute("DELETE FROM named_pos WHERE pos_name = ?", (pos_name,))
            conn.commit()
            conn.close()

        except Exception as e:
            self.console.print(f"[red]Error managing named positions: {e}")

    async def player_command(self, cmd_line: str) -> None:
        """Manage players list."""
        parts = cmd_line.split()
        if len(parts) < 2:
            self.console.print(
                "[yellow]Usage: player list | player add|del <playername>"
            )
            return

        action = parts[1].lower()
        if action not in ["add", "del", "list"]:
            self.console.print("[yellow]Action must be either 'add', 'del', or 'list'")
            return

        try:
            settings_df = self.minecraft_server.settings_df
            if settings_df is None:
                settings_df = pd.DataFrame(columns=["setting", "value"])
                self.minecraft_server.settings_df = settings_df

            # Get current players list or create it if it doesn't exist
            players_setting = settings_df[settings_df["setting"] == "players"]
            current_players = set()

            if not players_setting.empty:
                current_players = (
                    set(players_setting.iloc[0]["value"].split(","))
                    if players_setting.iloc[0]["value"]
                    else set()
                )

            if action == "list":
                if not current_players:
                    self.console.print("[yellow]No players in the list")
                else:
                    self.console.print("\n[green]Current players:")
                    for player in sorted(current_players):
                        self.console.print(f"  - {player}")
                    self.console.print()
                return

            if len(parts) < 3:
                self.console.print("[yellow]Usage: player add|del <playername>")
                return

            playername = parts[2]

            if action == "add":
                if playername in current_players:
                    self.console.print(
                        f"[yellow]Player '{playername}' is already in the list"
                    )
                    return
                current_players.add(playername)
                self.console.print(f"[green]Added player '{playername}' to the list")
            else:  # del
                if playername not in current_players:
                    self.console.print(
                        f"[yellow]Player '{playername}' is not in the list"
                    )
                    return
                current_players.remove(playername)
                self.console.print(
                    f"[green]Removed player '{playername}' from the list"
                )

            # Update or insert the players setting
            new_value = ",".join(sorted(current_players))
            if players_setting.empty:
                settings_df.loc[len(settings_df)] = ["players", new_value]
            else:
                settings_df.loc[players_setting.index[0], "value"] = new_value

            # Save to database
            conn = sqlite3.connect("data.sqlite")
            if not players_setting.empty:
                conn.execute(
                    "UPDATE settings SET value = ? WHERE setting = 'players'",
                    (new_value,),
                )
            else:
                conn.execute(
                    "INSERT INTO settings (setting, value) VALUES ('players', ?)",
                    (new_value,),
                )
            conn.commit()
            conn.close()

        except Exception as e:
            self.console.print(f"[red]Error managing players list: {e}")

    async def tp_command(self, cmd_line: str) -> None:
        """Teleport a player to coordinates, named position, or another player."""
        parts = cmd_line.split()
        if len(parts) < 3:
            self.console.print(
                "[yellow]Usage: tp <playername> <x y z | named_pos | @playername>"
            )
            return

        player = parts[1]
        destination = " ".join(parts[2:])

        try:
            # Check if it's teleporting to another player
            if destination.startswith("@"):
                target_player = destination[1:]  # Remove @ symbol
                mc_command = f"tp {player} {target_player}"
                result = await self.minecraft_server.send_command(mc_command)
                self.console.print(f"[green]{result}")
                return

            # Check if it's a named position
            if self.minecraft_server.named_pos_df is not None:
                pos_match = self.minecraft_server.named_pos_df[
                    self.minecraft_server.named_pos_df["pos_name"] == destination
                ]
                if not pos_match.empty:
                    destination = pos_match.iloc[0]["pos_value"]

            # Clean up the coordinates by replacing commas with spaces
            coords = destination.replace(",", " ")
            # Split by whitespace and filter out empty strings
            coord_parts = [x for x in coords.split() if x]

            if len(coord_parts) != 3:
                self.console.print("[yellow]Position must be three coordinates (x y z)")
                return

            # Validate each coordinate - allow numbers or tilde notation
            for coord in coord_parts:
                if (
                    coord != "~"
                    and not coord.startswith("~-")
                    and not coord.startswith("~+")
                ):
                    try:
                        float(coord)
                    except ValueError:
                        if coord.startswith("~"):
                            try:
                                # Try to parse the relative offset after the ~
                                float(coord[1:])
                            except ValueError:
                                self.console.print(
                                    "[yellow]Invalid relative coordinate format. Use ~ or ~<number>"
                                )
                                return
                        else:
                            self.console.print(
                                "[yellow]Position coordinates must be numbers or use tilde notation (~)"
                            )
                            return

            # Format position value consistently
            pos_value = " ".join(coord_parts)
            mc_command = f"tp {player} {pos_value}"
            result = await self.minecraft_server.send_command(mc_command)
            self.console.print(f"[green]{result}")

        except Exception as e:
            self.console.print(f"[red]Error teleporting player: {e}")

    async def quickgive_command(self, cmd_line: str) -> None:
        """Quickly give items to default player."""
        parts = cmd_line.split()
        if len(parts) < 2:
            self.console.print("[yellow]Usage: qg <item> [quantity]")
            return

        # Get default player from settings
        settings_df = self.minecraft_server.settings_df
        if (
            settings_df is None
            or settings_df[settings_df["setting"] == "default_player"].empty
        ):
            self.console.print(
                "[yellow]No default player set. Use 'player add <name>' to add a player first."
            )
            return

        default_player = settings_df[settings_df["setting"] == "default_player"].iloc[
            0
        ]["value"]
        item = parts[1]
        quantity = parts[2] if len(parts) > 2 else "1"

        # Reconstruct command line for give_command
        give_cmd = f"give {default_player} {item} {quantity}"
        await self.give_command(give_cmd)
