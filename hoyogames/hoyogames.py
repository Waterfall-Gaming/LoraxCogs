from datetime import datetime, timezone, timedelta
from collections.abc import Callable
from typing import Annotated

import calendar
import string
import random
import aiohttp

import discord
from redbot.core import Config, commands, bot
from discord.ext import tasks

from hoyogames.util import Games, Game, GameConverter, CodeRedeemView


class HoYoGames(commands.Cog):
  """Cog for HoYoVerse games"""

  default_guild_settings = {
    "UPDATE_CHANNELS": {
      Games.GENSHIN_IMPACT.identifier: [],
      Games.HONKAI_IMPACT_3RD.identifier: [],
      Games.HONKAI_STAR_RAIL.identifier: [],
      Games.ZENLESS_ZONE_ZERO.identifier: [],
    },
    "SEEN_CODES": {
      Games.GENSHIN_IMPACT.identifier: ["GENSHINGIFT"],
      Games.HONKAI_IMPACT_3RD.identifier: [],
      Games.HONKAI_STAR_RAIL.identifier: [],
      Games.ZENLESS_ZONE_ZERO.identifier: [],
    },
    "INVALID_CODES": {
      Games.GENSHIN_IMPACT.identifier: {},
      Games.HONKAI_IMPACT_3RD.identifier: {},
      Games.HONKAI_STAR_RAIL.identifier: {},
      Games.ZENLESS_ZONE_ZERO.identifier: {},
    },
    # "GAME_ALIASES": {
    #   "gi": ["genshin", "genshinimpact", "genshin-impact", "gi", "hk4e"],
    #   "hi3": ["honkai", "honkaiimpact", "honkaiimpact3", "honkaiimpact3rd", "honkai3rd", "bh3", "hi3"],
    #   "hsr": ["starrail", "star-rail", "hsr", "hkrpg"],
    #   "zzz": ["zenless", "zenlesszonezero", "zenless-zone-zero", "zzz"],
    # },
  }

  default_global_settings = default_guild_settings

  default_member_settings = {
    "redeemed": {
      Games.GENSHIN_IMPACT.identifier: [],
      Games.HONKAI_IMPACT_3RD.identifier: [],
      Games.HONKAI_STAR_RAIL.identifier: [],
      Games.ZENLESS_ZONE_ZERO.identifier: [],
    },
    # "games": [],
  }

  default_user_settings = default_member_settings

  def __init__(self, bot):
    super().__init__()
    self.session = None
    self.bot = bot

    self.config = Config.get_conf(self, 0x77672e687976)  # wg.hyv
    self.config.register_guild(**self.default_guild_settings)
    self.config.register_global(**self.default_global_settings)
    self.config.register_member(**self.default_member_settings)
    self.config.register_user(**self.default_user_settings)

  async def cog_load(self):
    # create a http request session object on load
    self.session = aiohttp.ClientSession()

    # register update tasks for each game
    self.check_codes.start()

  async def cog_unload(self) -> None:
    # close the http request session object on unload
    if self.session:
      await self.session.close()

    # wrap up tasks
    self.check_codes.cancel()


  @staticmethod
  def _format_rewards(rewards: str) -> str:
    """
    Takes a list of semicolon-delimited rewards, and turns them into bullet points
    """
    rewards = rewards.strip()

    if len(rewards) == 0:
      return "*Unknown Rewards*\n*Try redeem it yourself ;)*"

    rewards_list = rewards.split(";")
    formatted_rewards = "\n".join(f"- {reward.strip().replace('*', '×')}" for reward in rewards_list if reward.strip())

    return formatted_rewards

  @commands.group(name="codes", invoke_without_command=False)
  async def commands_codes(self, ctx):
    """Commands for managing codes for HoYoVerse games."""
    pass

  @commands_codes.command(name="view", aliases=["list", "show", "for"])
  async def codes_view(self, ctx, game: Annotated[Games, GameConverter]):
    """Get all available codes for a specific HoYoVerse game."""

    codes = await game.get_codes(self.session)

    embed = discord.Embed(title=f"{game.human_name} Codes", color=discord.Colour.blue(),
                          timestamp=datetime.now(timezone.utc))

    user_redeemed = await self.config.user(ctx.author).redeemed()

    reported_codes = await self.config.guild(ctx.guild).INVALID_CODES.get_raw(game.identifier, default={})

    is_valid = lambda code: (
      (code["code"] not in user_redeemed[game.identifier]) and
      (code["code"] not in reported_codes or len(reported_codes[code["code"]]) < 3)
    )

    valid_codes = [c for c in codes if is_valid(c)]

    for code in valid_codes:
      link = game.generate_redeem_link(code["code"])

      rewards = self._format_rewards(code["rewards"])

      embed.add_field(name=code["code"], value=f"{rewards}\n"
                                               f"[Click to Redeem]({link})", inline=True)

    if not valid_codes:
      embed.description = "There are no valid codes available for this game at the moment.\nPlease check back again later!"
      embed.colour = discord.Colour.dark_purple()

    await ctx.send(embed=embed)


  @commands_codes.command(name="use", aliases=["claim", "redeem"])
  async def codes_redeem(self, ctx, game: Annotated[Games, GameConverter], code: str):
    """Allows marking a code as redeemed, and shows the rewards for that code if it is valid."""

    code = code.strip().upper()

    codes = await game.get_codes(self.session)

    if not any(c["code"] == code for c in codes):
      await ctx.send(f"The code `{code}` is not valid for {game.human_name}. Please check the available codes and try again.")
      return

    user_redeemed = await self.config.user(ctx.author).redeemed()

    if code in user_redeemed[game.identifier]:
      await ctx.send(f"You have already redeemed the code `{code}` for {game.human_name}.")
      return

    for c in codes:
      if c["code"] == code:
        rewards = self._format_rewards(c["rewards"])

        embed = discord.Embed(title=f"Redeem Code • {game.human_name}", color=discord.Colour.green(),
                              timestamp=datetime.now(timezone.utc))
        embed.add_field(name="Code", value=f"`{code}`", inline=False)
        embed.add_field(name="Rewards", value=rewards, inline=False)
        # embed.add_field(name="Redeem Link", value=f"[Click to Redeem]({link})", inline=False)

        await ctx.send(embed=embed, view=CodeRedeemView(self.config, game, c["code"]))
        return

    await ctx.send(f"The code `{code}` is not valid for {game.human_name}. Please check the available codes and try again.")


  @commands.guild_only()
  @commands.admin_or_can_manage_channel()
  @commands_codes.command(name="follow", aliases=["subscribe", "sub", "updates"])
  async def codes_follow(self, ctx: commands.Context, game: Annotated[Games, GameConverter], channel: discord.TextChannel = None):
    """Subscribe to code updates for a specific HoYoVerse game in this channel."""

    if channel is None:
      channel = ctx.channel
    elif not channel.permissions_for(ctx.author).manage_channels:
      await ctx.send("You do not have permission to manage that channel.")
      return
    elif channel.guild != ctx.guild:
      await ctx.send("You can only subscribe channels from this server.")
      return

    update_channels = await self.config.guild(ctx.guild).UPDATE_CHANNELS()

    if ctx.channel.id in update_channels.get(game.identifier, []):
      await ctx.send(f"This channel is already subscribed to {game.human_name} code updates.")
      return

    update_channels.setdefault(game.identifier, []).append(ctx.channel.id)
    await self.config.guild(ctx.guild).UPDATE_CHANNELS.set(update_channels)

    await ctx.send(f"This channel has been subscribed to {game.human_name} code updates.")


  @commands.guild_only()
  @commands.admin_or_can_manage_channel()
  @commands_codes.command(name="unfollow", aliases=["unsubscribe", "unsub"])
  async def codes_unfollow(
      self, ctx: commands.Context, game: Annotated[Games, GameConverter], channel: discord.TextChannel = None):
    """Unsubscribe from code updates for a specific HoYoVerse game in this channel."""

    if channel is None:
      channel = ctx.channel
    elif not channel.permissions_for(ctx.author).manage_channels:
      await ctx.send("You do not have permission to manage that channel.")
      return

    if channel.guild != ctx.guild:
      await ctx.send("You can only unsubscribe channels from this server.")
      return

    update_channels = await self.config.guild(ctx.guild).UPDATE_CHANNELS()

    if channel.id in update_channels.get(game.identifier, []):
      await ctx.send(f"This channel is not subscribed to {game.human_name} code updates.")
      return

    # remove channel from list
    update_channels = [channel_id for channel_id in update_channels.get(game.identifier, []) if channel_id != channel.id]

    # update config
    await self.config.guild(ctx.guild).UPDATE_CHANNELS.set(update_channels)

    await ctx.send(f"This channel has been unsubscribed from {game.human_name} code updates.")


  @tasks.loop(minutes=30)
  async def check_codes(self):
    """
    Run scheduled task for channels
    """

    for guild in self.bot.guilds:
      update_channels = await self.config.guild(guild).UPDATE_CHANNELS()

      for game in Games:
        # Skip if there are no channels subscribed to this game
        if len(update_channels.get(game.identifier, [])) == 0:
          continue


        channels = [guild.get_channel(channel_id) for channel_id in update_channels[game.identifier]]
        channels = [channel for channel in channels if channel is not None]

        if not channels:
          continue

        codes = await game.get_codes(self.session)

        seen_codes = await self.config.guild(guild).SEEN_CODES.get_raw(game.identifier, default=[])

        new_codes = [code for code in codes if code["code"] not in seen_codes]

        if new_codes:
          # Update the seen codes
          seen_codes.extend(code["code"] for code in new_codes)
          await self.config.guild(guild).SEEN_CODES.set_raw(game.identifier, value=seen_codes)

          # Send the new codes to the channels
          for channel in channels:
            for code in new_codes:
              rewards = self._format_rewards(code["rewards"])

              embed = discord.Embed(title=f"New Redeem Code! • {game.human_name}", color=discord.Colour.purple(),
                                    timestamp=datetime.now(timezone.utc))
              embed.add_field(name="Code", value=f"`{code['code']}`", inline=False)
              embed.add_field(name="Rewards", value=rewards)
              # embed.add_field(name="Redeem Link", value=f"[Click to Redeem]({link})", inline=False)

              await channel.send(embed=embed, view=CodeRedeemView(self.config, game, code["code"]))


  @check_codes.before_loop
  async def before_check_codes(self):
    await self.bot.wait_until_ready()