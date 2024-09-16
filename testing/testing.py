from datetime import datetime, timezone, timedelta

import calendar
import string
import random

import discord
from redbot.core import Config, commands
from redbot.core.commands.requires import PrivilegeLevel


class TestModal(discord.ui.Modal):

  text_input = discord.ui.TextInput(label="Test", placeholder="Test", min_length=1, max_length=10)

  def __init__(self):
    super().__init__(title="Test Modal")
    self.value = None


  async def on_submit(self, interaction):
    await interaction.response.send_message(f"{interaction.user.mention} said: {self.text_input.value}", ephemeral=False)

class TestOpenModal(discord.ui.View):
  def __init__(self):
    super().__init__()
    self.value = None

  @discord.ui.button(label="Test", style=discord.ButtonStyle.red)
  async def test(self, interaction, button):
    self.value = "test"
    modal = TestModal()
    await interaction.response.send_modal(modal)


class TestingCog(commands.Cog):
  """Waterfall Custom Verification cog, idk how it'll work yet."""

  def __init__(self, bot):
    super().__init__()
    self.bot = bot

  @commands.group(name="test")
  @commands.is_owner()
  async def command_test(self, ctx):
    """Test command group."""
    pass

  @command_test.command(name="embed")
  async def command_test_embed(self, ctx, title: str, description: str):
    """Test embed."""
    embed = discord.Embed(title=title, description=title, color=discord.Color.blue())
    await ctx.send(embed=embed)

  @command_test.command(name="time")
  async def command_test_time(self, ctx):
    """Test time."""
    now = datetime.now(timezone.utc)
    await ctx.send(f"Time: {now}")

  @command_test.command(name="modal")
  async def command_test_modal(self, ctx, title: str):
    """Test modal."""
    await ctx.send("surprise!", view=TestOpenModal())

  @command_test.command(name="roles")
  async def command_test_roles_modal(self, ctx):
    """Test roles modal."""
    roles = await ctx.guild.fetch_roles()
    role_select = discord.ui.RoleSelect(placeholder="gIB ROLes")
    view = discord.ui.View()
    view.add_item(role_select)

    await ctx.send("surprise!", view=view)

