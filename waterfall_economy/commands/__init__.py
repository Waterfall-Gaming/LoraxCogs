from redbot.core import commands
from .econset import EconomySettingsCommand
from .steal import StealCommand


class EconomyCommands(
  EconomySettingsCommand,
  StealCommand,
):
  def __init__(self, bot):
    super().__init__(bot)
    self.bot = bot
    self.config = None  # make the config field, but it gets overridden so it's fine

