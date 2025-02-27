"""
Economy settings command.
"""
from ..util.embeds import SettingChangedEmbed, ErrorEmbed, AdminEmbed

from redbot.core import Config, commands, app_commands, bank
from redbot.core.commands.converter import TimedeltaConverter
from redbot.core.utils.chat_formatting import humanize_number
from redbot.core.commands.requires import PrivilegeLevel

from datetime import datetime, timezone, timedelta

import discord
import calendar

from random import randint, randrange


class EconomySettingsCommand(commands.Cog):
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
      await ctx.send(embed=ErrorEmbed("The success rate must be between 0 and 100!"))
      return

    await self.config.STEAL_SUCCESS_RATE.set(rate)
    await ctx.send(embed=SettingChangedEmbed("Steal Success Rate", rate))

  @command_econset_steal.command(name="cooldown")
  async def command_econset_steal_cooldown(self, ctx, cooldown: TimedeltaConverter):
    """Set the cooldown for the steal command"""
    await self.config.STEAL_COOLDOWN.set(cooldown.total_seconds())
    await ctx.send(embed=SettingChangedEmbed("Steal Cooldown", str(cooldown)))

  @command_econset_steal.command(name="max")
  async def command_econset_steal_max(self, ctx, max_amount: int):
    """Set the maximum amount that can be stolen"""
    if max_amount < 1:
      await ctx.send(embed=ErrorEmbed("The maximum amount that can be stolen must be at least 1!"))
      return
    await self.config.STEAL_MAX.set(max_amount)
    await ctx.send(embed=SettingChangedEmbed("Max Steal Amount", humanize_number(max_amount)))

  @command_econset_steal.command(name="immunity")
  async def command_econset_steal_immunity(self, ctx, immunity: TimedeltaConverter):
    """Set the immunity duration for the steal command"""
    await self.config.STEAL_IMMUNITY.set(immunity.total_seconds())
    await ctx.send(embed=SettingChangedEmbed("Steal Immunity Duration", str(immunity)))

  @command_econset_steal.group(name="clear")
  async def command_econset_steal_clear(self):
    """Clear steal cooldowns and immunities"""
    pass

  @command_econset_steal_clear.group(name="cooldown")
  async def command_econset_steal_clear_cooldown(self):
    """Clear steal cooldown."""
    pass

  @command_econset_steal_clear_cooldown.command(name="user")
  async def command_econset_steal_clear_cooldown_user(self, ctx, target: discord.Member):
    """Clear the cooldown for a user's steal command"""
    await self.config.member(target).steal_cooldown.set(0)
    await ctx.send(embed=AdminEmbed(
      message="{target.mention}'s steal cooldown has been reset!",
      author=ctx.author,
      title="Steal Cooldown Reset"
    ))

  @command_econset_steal_clear_cooldown.command(name="all")
  async def command_econset_steal_clear_cooldown_all(self, ctx):
    """Clear everyone's steal cooldown"""
    i = 0
    for member in ctx.guild.members:
      await self.config.member(member).steal_cooldown.set(0)
      i += 1

    await ctx.send(embed=AdminEmbed(
      message=f"Steal cooldown has been reset for **{i}** users!",
      author=ctx.author,
      title="Steal Cooldowns Reset"
    ))

  @command_econset_steal_clear.group(name="immunity")
  async def command_econset_steal_clear_immunity(self):
    """Clear steal immunity."""
    pass

  @command_econset_steal_clear_immunity.command(name="user")
  async def command_econset_steal_clear_immunity_user(self, ctx, target: discord.Member):
    """Clear the immunity for a user's steal command"""
    await self.config.member(target).steal_immunity.set(0)
    await ctx.send(embed=AdminEmbed(
      message=f"{target.mention}'s steal immunity has been reset!",
      author=ctx.author,
      title="Steal Immunity Reset"
    ))

  @command_econset_steal_clear_immunity.command(name="all")
  async def command_econset_steal_clear_immunity_all(self, ctx):
    """Clear everyone's steal immunity"""
    i = 0
    for member in ctx.guild.members:
      await self.config.member(member).steal_immunity.set(0)
      i += 1

    await ctx.send(embed=AdminEmbed(
      message=f"Steal immunity has been reset for **{i}** users!",
      author=ctx.author,
      title="Steal Immunities Reset"
    ))