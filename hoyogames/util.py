from dataclasses import dataclass
from enum import Enum
import re

from redbot.core import commands, Config
import discord.ui

import aiohttp


@dataclass
class Game:
  """
  Class representing a game and all its associated info, see the fields for more info
  """

  identifier: str
  """The identifier for the game, used in the config, for commands, and querying the codes API"""

  human_name: str
  """The human-readable name of the game, used in embeds and messages"""

  aliases: list[str]
  """A list of aliases for the game, used for command parsing and user input"""

  redeem_url: str | None = None
  """
  The redeem URL for the game, used for generating redeem links in embeds and messages.
  The code can be substituted in via the `{}` placeholder, e.g. `redeem_url.format(code)`.
  """

  async def get_codes(self, session: aiohttp.ClientSession) -> list:
    """
    Query the API for all available codes for this game.

    Returns:
        list[str]: A list of available codes for the game.
    """

    _API_URL = "https://hoyo-codes.seria.moe/codes?game={}"

    # use existing session to fetch from the endpoint
    async with session.get(_API_URL.format(self.identifier)) as response:
      if response.status == 200:
        data = await response.json()
        return data.get("codes", [])
      else:
        return []

  def generate_redeem_link(self, code: str) -> str | None:
    """
    Generate a redeem link for the game using the provided code.

    Args:
        code (str): The code to be used in the redeem link.

    Returns:
        str: The generated redeem link.
    """
    if self.redeem_url:
      return self.redeem_url.format(code)
    return None

class Games(Enum):
  # enum keys
  GENSHIN_IMPACT = Game("genshin", "Genshin Impact", ["genshin", "genshin impact", "gi", "hk4e"], "https://genshin.hoyoverse.com/en/gift?code={}")
  HONKAI_IMPACT_3RD = Game("honkai3rd", "Honkai Impact 3rd", ["honkai", "honkai impact", "honkai impact 3rd", "hi3", "bh3"])
  HONKAI_STAR_RAIL = Game("hkrpg", "Honkai: Star Rail", ["honkai star rail", "star rail", "hsr", "hkrpg"], "https://hsr.hoyoverse.com/gift?code={}")
  ZENLESS_ZONE_ZERO = Game("nap", "Zenless Zone Zero", ["zenless", "zenless zone zero", "zzz"], "https://zenless.hoyoverse.com/redemption?code={}")

  @property
  def identifier(self) -> str:
    return self.value.identifier

  @property
  def human_name(self) -> str:
    return self.value.human_name

  @property
  def aliases(self) -> list[str]:
    return self.value.aliases

  @property
  def redeem_url(self) -> str | None:
    return self.value.redeem_url

  async def get_codes(self, session: aiohttp.ClientSession) -> list:
    return await self.value.get_codes(session)

  def generate_redeem_link(self, code: str) -> str | None:
    return self.value.generate_redeem_link(code)

class GameConverter(commands.Converter):
  async def convert(self, ctx: commands.Context, argument: str) -> Games:
    # normalise the argument to lowercase and replace hyphens and underscores with spaces
    arg = re.sub(r"[\-_+]", " ", argument.lower()).strip()  # normalise hyphens and underscores

    for game in Games:
      if arg == game.value.identifier or arg in game.value.aliases:
        return game

    raise commands.BadArgument(f"'{argument}' isn't a recognised game.")

class CodeRedeemView(discord.ui.View):
  def __init__(self, config: Config, game: Games, code: str, persistent: bool = False):
    super().__init__(timeout=None if persistent else 120)
    self.game = game
    self.code = code
    self.config = config

    url = self.game.generate_redeem_link(self.code)

    if url:
      self.add_item(discord.ui.Button(
          label="Redeem!",
          style=discord.ButtonStyle.primary,
          url=url,
          emoji="🎁",
          row=1
      ))

  @discord.ui.button(label="Mark as Redeemed", emoji="✅", style=discord.ButtonStyle.success, custom_id="code:mark_redeemed", row=0)
  async def mark_redeemed(self, interaction: discord.Interaction, button: discord.ui.Button):
    # mark the code as redeemed for the user
    user_cfg = await self.config.user(interaction.user).all()
    user_cfg["redeemed"][self.game.identifier].append(self.code)
    await self.config.user(interaction.user).set(user_cfg)

    await interaction.response.send_message(
        f"Marked code `{self.code}` as redeemed for **{self.game.human_name}**.", ephemeral=True
    )

  @discord.ui.button(label="Report Invalid", emoji="⚠️", style=discord.ButtonStyle.danger, custom_id="code:report_invalid", row=0)
  async def report_invalid(self, interaction: discord.Interaction, button: discord.ui.Button):
    # report the code as invalid on the bot
    user_id = interaction.user.id

    global_cfg = await self.config.all()

    game_reported_codes = global_cfg["INVALID_CODES"][self.game.identifier]

    if self.code not in game_reported_codes:
      game_reported_codes += { self.code: [user_id] }
    elif user_id not in game_reported_codes[self.code]:
      game_reported_codes[self.code] += user_id
    else:
      await interaction.response.send_message(
          f"You have already reported code `{self.code}` as invalid for **{self.game.human_name}**.", ephemeral=True
      )
      return

    global_cfg["INVALID_CODES"][self.game.identifier] = game_reported_codes

    await self.config.set(global_cfg)

    await interaction.response.send_message(
        f"Reported code `{self.code}` as invalid for **{self.game.human_name}****.", ephemeral=True
    )




