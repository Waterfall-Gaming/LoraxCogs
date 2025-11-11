from redbot.core import commands
from .roulette import RouletteCommands


class GamblingCommands(
  RouletteCommands
):
  def __init__(self, bot):
    super().__init__(bot)
    self.bot = bot
    self.config = None  # make the config field, but it gets overridden so it's fine
