from dataclasses import dataclass
from enum import Enum
import re
from typing import ClassVar

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

class MarkRedeemedButton(discord.ui.DynamicItem[discord.ui.Button],
                         template=r"code:mark_redeemed:(?P<game>[\w-]+):(?P<code>[\w-]+)"):
  config: ClassVar[Config]  # set by the cog on load

  def __init__(self, game: Games, code: str):
    super().__init__(
        discord.ui.Button(
            label="Mark as Redeemed",
            emoji="✅",
            style=discord.ButtonStyle.success,
            custom_id=f"code:mark_redeemed:{game.identifier}:{code}",
            row=0,
        )
    )
    self.game = game
    self.code = code

  @classmethod
  async def from_custom_id(cls, interaction: discord.Interaction, item: discord.ui.Button, match: re.Match[str]):
    game = next(g for g in Games if g.identifier == match["game"])
    return cls(game, match["code"])

  async def callback(self, interaction: discord.Interaction):
    user_cfg = await self.config.user(interaction.user).all()
    user_cfg.setdefault("redeemed", {}).setdefault(self.game.identifier, []).append(self.code)
    await self.config.user(interaction.user).set(user_cfg)

    await interaction.response.send_message(
        f"Marked code `{self.code}` as redeemed for **{self.game.human_name}**.", ephemeral=True
    )


class ReportInvalidButton(discord.ui.DynamicItem[discord.ui.Button],
                          template=r"code:report_invalid:(?P<game>[\w-]+):(?P<code>[\w-]+)"):
  config: ClassVar[Config]  # set by the cog on load

  def __init__(self, game: Games, code: str):
    super().__init__(
        discord.ui.Button(
            label="Report Invalid",
            emoji="⚠️",
            style=discord.ButtonStyle.danger,
            custom_id=f"code:report_invalid:{game.identifier}:{code}",
            row=0,
        )
    )
    self.game = game
    self.code = code

  @classmethod
  async def from_custom_id(cls, interaction: discord.Interaction, item: discord.ui.Button, match: re.Match[str]):
    game = next(g for g in Games if g.identifier == match["game"])
    return cls(game, match["code"])

  async def callback(self, interaction: discord.Interaction):
    user_id = interaction.user.id
    global_cfg = await self.config.all()

    reported = global_cfg.setdefault("INVALID_CODES", {}).setdefault(self.game.identifier, {})

    if self.code not in reported:
      reported[self.code] = [user_id]
    elif user_id not in reported[self.code]:
      reported[self.code].append(user_id)
    else:
      await interaction.response.send_message(
          f"You have already reported code `{self.code}` as invalid for **{self.game.human_name}**.", ephemeral=True
      )
      return

    await self.config.set(global_cfg)

    await interaction.response.send_message(
        f"Reported code `{self.code}` as invalid for **{self.game.human_name}**.", ephemeral=True
    )


class CodeRedeemView(discord.ui.View):
  def __init__(self, game: Games, code: str, persistent: bool = False):
    super().__init__(timeout=None if persistent else 120)

    url = game.generate_redeem_link(code)
    if url:
      self.add_item(discord.ui.Button(
          label="Redeem!",
          style=discord.ButtonStyle.primary,
          url=url,
          emoji="🎁",
          row=1,
      ))

    self.add_item(MarkRedeemedButton(game, code))
    self.add_item(ReportInvalidButton(game, code))



