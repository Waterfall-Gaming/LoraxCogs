from discord import Embed, Colour


class ErrorEmbed(Embed):
  """An embed for displaying errors."""
  def __init__(self, title: str = "Error", message: str = "An error occurred...", colour: Colour = Colour.red()):
    super().__init__(title=title, description=message, colour=colour)
    self.set_footer()

