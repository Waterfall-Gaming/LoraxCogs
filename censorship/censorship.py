import discord
from redbot.core import Config, commands, modlog
from redbot.core.commands.converter import TimedeltaConverter
from redbot.core.commands.requires import PrivilegeLevel

import datetime as dt

class Censorship(commands.Cog):
  """chat censorship"""

  def __init__(self, bot):
    super().__init__()
    self.bot = bot

  @commands.Cog.listener(name="on_message")
  async def listen_for_bad_content(self, message):
    # only work on april fools
    if dt.date.today().day != 1 or dt.date.today().month != 4:
      return

    if message.author.bot:
      return

    if not message.guild:
      return

    author: Member = message.author
    content = message.content.lower().strip()

    skips = (
      author.get_role(1074366074000261191) or # staff role
      author.get_role(1488816255212453938) # verified role
    )

    if skips:
      return

    response: Message = None
    
    for term in ["s", "e", "x"]:
      if term in content:
        response = await message.reply(
          f"## ⚠️ Warning\n"
          f"{author.mention}, your message contains sensitive content! You must verify your "
          f"age before you are allowed to send sensitive content!"
        )
        await message.delete(delay=1.0)
        break
    
    if response:
      await response.delete(delay=6.9)
