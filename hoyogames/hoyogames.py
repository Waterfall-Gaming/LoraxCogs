from datetime import datetime, timezone, timedelta

import calendar
import string
import random
import aiohttp

import discord
from redbot.core import Config, commands, modlog
from redbot.core.commands.converter import TimedeltaConverter
from redbot.core.commands.requires import PrivilegeLevel


class HoYoGames(commands.Cog):
  """Waterfall Custom Verification cog, idk how it'll work yet."""

  default_guild_settings = {
    "REDEEM_LINK": {
      "gi": "https://genshin.hoyoverse.com/gift/code?={}",
      "hi3": None,
      "hsr": "https://hsr.hoyoverse.com/gift?code={}",
      "zzz": "https://zenless.hoyoverse.com/redemption?code={}",
    },
    "UPDATE_CHANNELS": {
      "gi": [],
      "hi3": [],
      "hsr": [],
      "zzz": [],
    },
    "SEEN_CODES": {
      "gi": ["GENSHINGIFT"],
      "hi3": [],
      "hsr": [],
      "zzz": [],
    },
    "GAME_ALIASES": {
      "gi": ["genshin", "genshinimpact", "genshin-impact", "gi", "hk4e"],
      "hi3": ["honkai", "honkaiimpact", "honkaiimpact3", "honkaiimpact3rd", "honkai3rd", "bh3", "hi3"],
      "hsr": ["starrail", "star-rail", "hsr", "hkrpg"],
      "zzz": ["zenless", "zenlesszonezero", "zenless-zone-zero", "zzz"],
    },
  }

  default_global_settings = default_guild_settings

  default_member_settings = {
    "redeemed": {
      "gi": [],
      "hi3": [],
      "hsr": [],
      "zzz": [],
    },
    "games": [],
  }

  default_user_settings = default_member_settings

  def __init__(self, bot):
    super().__init__()
    self.bot = bot

    self.config = Config.get_conf(self, 0x77672e687976)  # wg.hyv
    self.config.register_guild(**self.default_guild_settings)
    self.config.register_global(**self.default_global_settings)
    self.config.register_member(**self.default_member_settings)
    self.config.register_user(**self.default_user_settings)

  async def _get_codes(self, game: str = "genshin"):
    """Query the API for all available codes for a game."""
    _API_URL = "https://hoyo-codes.seria.moe/codes?game={}"
    _mappings = {
      "gi": "genshin",
      "hi3": "honkai3rd",
      "hsr": "hkrpg",
      "zzz": "nap",
    }

    async def fetch(url):
      async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
          return await response.json()

    # reverse map the game variable to our internal game names
    game_aliases = await self.config.GAME_ALIASES()
    get_game_key = lambda alias: next((k for k, v in game_aliases.items() if alias in v), None)
    game_key = get_game_key(game)

    api_name = _mappings.get(game_key, None)

    if api_name is None:
      return []

    codes = await fetch(_API_URL.format(api_name))

    return codes["codes"]


  @commands.group(name="genshin", aliases=["gi"])
  async def commands_genshin(self, ctx):
    """Genshin Impact related commands."""
    pass

  @commands_genshin.command(name="codes")
  async def genshin_codes(self, ctx):
    """Get all available codes for Genshin Impact."""
    codes = await self._get_codes("genshin")

    embed = discord.Embed(title="Genshin Impact Codes", color=discord.Color.blue(), timestamp=datetime.now(timezone.utc))

    seen = await self.config.SEEN_CODES()
    user_redeemed = await self.config.user(ctx.author).redeemed()
    redeem_link = (await self.config.REDEEM_LINK())["gi"]

    for code in codes:
      print(code)
      seen["gi"].append(code["code"])

      if code["code"] not in user_redeemed["gi"]:
        link = redeem_link.format(code["code"])

        embed.add_field(name=code["code"], value=f"*{code['rewards']}*\n"
                                                 f"[Click to Redeem]({link})", inline=True)

    await self.config.SEEN_CODES.set(seen)

    await ctx.send(embed=embed)

  @commands.group(name="honkai", aliases=["hi3", "bh3", "honkai3rd"])
  async def commands_honkai(self, ctx):
    """Honkai Impact 3rd related commands."""
    pass

  @commands_honkai.command(name="codes")
  async def honkai_codes(self, ctx):
    """Get all available codes for Honkai Impact 3rd."""
    codes = await self._get_codes("honkai3rd")

    embed = discord.Embed(title="Honkai Impact 3rd Codes", color=discord.Color.blue(), timestamp=datetime.now(timezone.utc))

    seen = await self.config.SEEN_CODES()
    user_redeemed = await self.config.user(ctx.author).redeemed()
    redeem_link = (await self.config.REDEEM_LINK())["hi3"]

    for code in codes:
      seen["hi3"].append(code["code"])

      if code["code"] not in user_redeemed["hi3"]:
        link = redeem_link.format(code["code"])

        embed.add_field(name=code["code"], value=f"*{code['rewards']}*\n", inline=True)

    await self.config.SEEN_CODES.set(seen)

    await ctx.send(embed=embed)

  @commands.group(name="hsr", aliases=["starrail"])
  async def commands_hsr(self, ctx):
    """Star Rail related commands."""
    pass

  @commands_hsr.command(name="codes")
  async def hsr_codes(self, ctx):
    """Get all available codes for Star Rail."""
    codes = await self._get_codes("hkrpg")

    embed = discord.Embed(title="Star Rail Codes", color=discord.Color.blue(), timestamp=datetime.now(timezone.utc))

    seen = await self.config.SEEN_CODES()
    user_redeemed = await self.config.user(ctx.author).redeemed()
    redeem_link = (await self.config.REDEEM_LINK())["hsr"]

    for code in codes:
      seen["hsr"].append(code["code"])

      if code["code"] not in user_redeemed["hsr"]:
        link = redeem_link.format(code["code"])

        embed.add_field(name=code["code"], value=f"*{code['rewards']}*", inline=True)

    await self.config.SEEN_CODES.set(seen)

    await ctx.send(embed=embed)

  @commands.group(name="zzz", aliases=["zenless", "zenlesszonezero"])
  async def commands_zenless(self, ctx):
    """Zenless Zone Zero related commands."""
    pass

  @commands_zenless.command(name="codes")
  async def zzz_codes(self, ctx):
    """Get all available codes for Zenless Zone Zero."""
    codes = await self._get_codes("nap")

    embed = discord.Embed(title="Zenless Zone Zero Codes", color=discord.Color.blue(), timestamp=datetime.now(timezone.utc))

    seen = await self.config.SEEN_CODES()
    user_redeemed = await self.config.user(ctx.author).redeemed()
    redeem_link = (await self.config.REDEEM_LINK())["zzz"]

    for code in codes:
      seen["zzz"].add(code["code"])

      if code["code"] not in user_redeemed["zzz"]:
        link = redeem_link.format(code["code"])

        embed.add_field(name=code["code"], value=f"*{code['rewards'] or ' '}*\n", inline=True)

    await self.config.SEEN_CODES.set(seen)

    await ctx.send(embed=embed)
