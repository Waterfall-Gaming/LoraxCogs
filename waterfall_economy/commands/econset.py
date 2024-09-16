"""
Economy settings command.
"""

from redbot.core import Config, commands, app_commands, bank
from redbot.core.commands.converter import TimedeltaConverter
from redbot.core.utils.chat_formatting import humanize_number
from redbot.core.commands.requires import PrivilegeLevel

from datetime import datetime, timezone, timedelta

import discord
import calendar

from random import randint, randrange


class EconomySettingsCog(commands.Cog):
  """
  All the economy configuration subcommands
  """

  def __init___(self, bot):
    """Initialise the cog."""
    self.bot = bot
    self.config = None  # make the config field, but it gets overridden so it's fine

  @commands.group(name="econset")
  @commands.admin()
  async def command_econset(self, ctx):
    """Set Waterfall Economy settings"""
    pass

  @command_econset.group(name="steal")
  async def command_econset_steal(self, ctx):
    """Set steal settings"""
    pass

  @command_econset_steal.command(name="rate")
  async def command_econset_steal_rate(self, ctx, rate: int):
    """Set the success rate for the steal command"""
    if rate < 0 or rate > 100:
      await ctx.send("The steal rate must be between 0 and 100!")
      return

    await self.config.STEAL_SUCCESS_RATE.set(rate)
    await ctx.send(f"The steal success rate has been set to {rate}%!")

  @command_econset_steal.command(name="cooldown")
  async def command_econset_steal_cooldown(self, ctx, cooldown: TimedeltaConverter):
    """Set the cooldown for the steal command"""
    await self.config.STEAL_COOLDOWN.set(cooldown.total_seconds())
    await ctx.send(f"The steal cooldown has been set to {cooldown}!")

  @command_econset_steal.command(name="max")
  async def command_econset_steal_max(self, ctx, max_amount: int):
    """Set the maximum amount that can be stolen"""
    if max_amount < 1:
      await ctx.send("The maximum amount that can be stolen must be at least 1!")
      return
    await self.config.STEAL_MAX.set(max_amount)
    await ctx.send(f"The maximum amount that can be stolen has been set to {humanize_number(max)}!")

  @command_econset_steal.command(name="immunity")
  async def command_econset_steal_immunity(self, ctx, immunity: TimedeltaConverter):
    """Set the immunity duration for the steal command"""
    await self.config.STEAL_IMMUNITY.set(immunity.total_seconds())
    await ctx.send(f"The steal immunity duration has been set to {immunity}!")

  @command_econset_steal.group(name="clear")
  async def command_econset_steal_clear(self):
    """Clear users' cooldowns and immunities"""
    pass

  @command_econset_steal_clear.group(name="cooldown")
  async def command_econset_steal_clear_cooldown(self):
    """Clear steal cooldown."""
    pass

  @command_econset_steal_clear_cooldown.command(name="user")
  async def command_econset_steal_clear_cooldown_user(self, ctx, target: discord.Member):
    """Clear the cooldown for a user's steal command"""
    await self.config.member(target).steal_cooldown.set(0)
    await ctx.send(f"{target.mention}'s steal cooldown has been reset!")

  @command_econset_steal_clear_cooldown.command(name="all")
  async def command_econset_steal_clear_cooldown_all(self, ctx):
    """Clear everyone's steal cooldown"""
    for member in ctx.guild.members:
      await self.config.member(target).steal_cooldown.set(0)

