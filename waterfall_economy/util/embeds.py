import datetime as dt

from discord import Embed, Colour, User, Guild


class ErrorEmbed(Embed):
  """An embed for displaying errors."""

  def __init__(
      self,
      message: str = "An error occurred...",
      title: str = "Error",
      colour: Colour = Colour.red(),
      timestamp: dt.datetime = dt.datetime.now()
  ):
    super().__init__(title=title, description=message, colour=colour, timestamp=timestamp)


class AdminEmbed(Embed):
  """An embed for displaying admin messages."""

  def __init__(
      self,
      message: str,
      title: str,
      colour: Colour = Colour.gold(),
      timestamp: dt.datetime = dt.datetime.now(),
      author: User = None
  ):
    super().__init__(title=title, description=message, colour=colour, timestamp=timestamp)

    if author:
      self.set_footer(text=f"Action performed by **{author.display_name}**", icon_url=author.avatar.url)


class SettingChangedEmbed(Embed):
  """An embed for displaying settings changes."""

  def __init__(
      self,
      setting_name: str,
      new_value: str,
      title: str = "Setting Changed",
      colour: Colour = Colour.green(),
      timestamp: dt.datetime = dt.datetime.now(),
  ):
    super().__init__(
      title=title,
      description=f"{setting_name} has been updated to `{new_value}`",
      colour=colour,
      timestamp=timestamp
    )


class OfficialEmbed(Embed):
  """An embed for displaying official messages."""

  def __init__(
      self,
      guild: Guild,
      title: str = "Official Message",
      message: str = "An official message has been sent...",
      colour: Colour = Colour.blue(),
      timestamp: dt.datetime = dt.datetime.now(),
  ):
    super().__init__(title=title, description=message, colour=colour, timestamp=timestamp)

    self.set_author(name=guild.name, icon_url=guild.icon.url)
