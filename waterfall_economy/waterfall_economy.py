from redbot.core import Config, commands, app_commands, bank
from redbot.core.commands.converter import TimedeltaConverter
from redbot.core.utils.chat_formatting import humanize_number
from redbot.core.commands.requires import PrivilegeLevel

from datetime import datetime, timezone, timedelta

import discord
import calendar

from random import randint, randrange

from .commands import EconomyCommands


def guild_only():
  async def predicate(ctx):
    if await bank.is_global():
      return True
    elif ctx.guild is not None and not await bank.is_global():
      return True
    else:
      return False

  return commands.check(predicate)


class WaterfallEconomy(
  EconomyCommands
):
  """Waterfall Custom Economy cog, featuring jobs, gambling, and more!"""

  default_guild_settings = {
    "JOB_COOLDOWN": 43_200,
    "STEAL_COOLDOWN": 14_400,
    "STEAL_MAX": 10_000,
    "STEAL_IMMUNITY": 86_400,
    "STEAL_SUCCESS_RATE": 50
  }

  default_global_settings = default_guild_settings

  default_member_settings = {
    "job_cooldown": 0,
    "job": None,
    "job_times_worked": 0,
    "steal_cooldown": 0,
    "steal_immunity": 0
  }

  default_role_settings = {
    "MONEY_MULTIPLIER": 1.0
  }

  default_user_settings = default_member_settings

  def __init__(self, bot):
    super().__init__()
    self.bot = bot

    self.config = Config.get_conf(self, 0x77672e65636f6e6f6d79)  # wg.economy
    self.config.register_guild(**self.default_guild_settings)
    self.config.register_global(**self.default_global_settings)
    self.config.register_member(**self.default_member_settings)
    self.config.register_role(**self.default_role_settings)
    self.config.register_user(**self.default_user_settings)

