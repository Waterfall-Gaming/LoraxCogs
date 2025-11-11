from redbot.core import Config, commands, app_commands, bank
from redbot.core.commands.converter import TimedeltaConverter
from redbot.core.utils.chat_formatting import humanize_number
from redbot.core.commands.requires import PrivilegeLevel

from datetime import datetime, timezone, timedelta

import discord
import calendar

from random import randint, randrange

from .commands import EconomyCommands
from .util.gambling import Bet


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
    "STEAL_COOLDOWN": 14_400,
    "STEAL_MIN": 1,
    "STEAL_MAX": 10_000,
    "STEAL_IMMUNITY": 86_400,
    "STEAL_SUCCESS_RATE": 50,
    "JOB_COOLDOWN": 43_200,  # 12h
    "JOB_APPLY_COOLDOWN": 86_400,  # 24h
    "JOBS": {
      "wcdonalds": {
        "name": "WcDonald's",
        "description": "Work at WcDonald's to earn credits!",
        "emoji": "🍔",
        "min_times_worked": 0,
        "tiers": [
          {"name": "Cashier", "rate": 100, "min_hours": 4, "max_hours": 8, "times_worked": 0},
          {"name": "Cook", "rate": 150, "min_hours": 6, "max_hours": 8, "times_worked": 8},
          {"name": "Manager", "rate": 200, "min_hours": 8, "max_hours": 10, "times_worked": 16},
        ],
      },
    },
    "GAMBLING": {
      "ROULETTE": {
        "MIN_BET": 10,
        "MAX_BET": 10_000,
        "MAX_DURATION": 600,
        "MIN_DURATION": 30,
        "OPEN_TABLES": [],
        "TABLE_OPEN_COST": None,
      },
      "RUSSIAN_ROULETTE": {
        "MIN_BET": 100,
        "MAX_BET": 10_000,
        "BULLETS": 6,
      }
    }
  }

  default_global_settings = default_guild_settings

  default_member_settings = {
    "job_last_worked": 0,
    "job": None,
    "job_tier": 0,
    "job_times_worked": 0,
    "job_global_times_worked": 0,
    "job_last_quit": 0,
    "steal_cooldown": 0,
    "steal_immunity": 0
  }

  default_role_settings = {
    "MONEY_MULTIPLIER": 1.0
  }

  default_user_settings = default_member_settings

  def __init__(self, bot):
    super().__init__(bot)
    self.bot = bot

    self.config = Config.get_conf(self, 0x77672e65636f6e6f6d79)  # wg.economy
    self.config.register_guild(**self.default_guild_settings)
    self.config.register_global(**self.default_global_settings)
    self.config.register_member(**self.default_member_settings)
    self.config.register_role(**self.default_role_settings)
    self.config.register_user(**self.default_user_settings)

