from redbot.core import Config, commands, app_commands, bank
from redbot.core.utils.chat_formatting import humanize_number

from datetime import datetime, timezone, timedelta
from random import randint

import discord
import calendar


class StealCommand(commands.Cog):
  """The steal command"""

  def __init__(self, bot):
    super().__init__()
    self.bot = bot
    self.config = None

  @commands.command(name="steal")
  @commands.guild_only()
  async def command_steal(self, ctx, target: discord.Member, amount: int):
    """Attempt to rob a user for a specified amount of credits"""
    author = ctx.author
    guild = ctx.guild

    currency = await bank.get_currency_name(guild)
    # target = await commands.MemberConverter().convert(ctx, target)
    steal_rate = await self.config.STEAL_SUCCESS_RATE()
    steal_immunity = await self.config.STEAL_IMMUNITY()
    steal_cooldown = await self.config.STEAL_COOLDOWN()

    cur_time = calendar.timegm(ctx.message.created_at.utctimetuple())
    next_steal = await self.config.member(author).steal_cooldown() + steal_cooldown
    author_steal_immune = await self.config.member(author).steal_immunity() + steal_immunity
    target_steal_immune = await self.config.member(target).steal_immunity() + steal_immunity

    # check if the user is on cooldown
    if cur_time < next_steal:
      # get the relative time for when the user can rob again
      relative_time = discord.utils.format_dt(
        datetime.now(timezone.utc) + timedelta(seconds=next_steal - cur_time), "R"
      )
      await ctx.send(f"## You are on cooldown!\n You can steal again {relative_time}!")
      return

    if target.id == ctx.author.id:
      await ctx.send("You can't rob yourself!")
      return

    # check if the target is immune to robbing
    if cur_time < target_steal_immune:
      # get the relative time for when target's rob immunity expires
      relative_time = discord.utils.format_dt(
        datetime.now(timezone.utc) + timedelta(seconds=target_steal_immune - cur_time), "R"
      )
      await ctx.send(f"{target.mention} is currently immune to being robbed!\n You will be able to rob them "
                     f"{relative_time}!")
      return

    # check if the author is immune to robbing, and warn them that this will expire if they attempt to rob someone
    if cur_time < target_steal_immune:
      relative_time = discord.utils.format_dt(
        datetime.now(timezone.utc) + timedelta(seconds=author_steal_immune - cur_time), "R"
      )
      await ctx.send(f"## You are currently still immune to being robbed!\n If you proceed with running this command, "
                     f"this immunity will be cancelled and other people will be able to rob you again."
                     f"If you do nothing, it will expire on its own {relative_time}!\n\n"
                     f"If you understand the risks and wish to proceed, say `yes` in chat within the next 10 seconds.")

      try:
        await self.bot.wait_for("message", check=lambda m: m.author == author and m.content.lower() == "yes", timeout=10)
      except TimeoutError:
        return
      else:
        await ctx.send(f"You are no longer immune to being robbed!")
        await self.config.user(author).steal_immunity.set(0)

    if amount < 1:
      await ctx.send(f"You can't steal less than 1 {currency}!")
      return

    if amount > await self.config.STEAL_MAX():
      await ctx.send(f"You can't steal more than {humanize_number(await self.config.STEAL_MAX())} {currency}!")
      return

    if await bank.can_spend(ctx.author, amount//2):
      if await bank.can_spend(target, amount):
        if randint(1, 100) <= steal_rate:
          await bank.transfer_credits(target, ctx.author, amount)
          await ctx.send(f"You successfully stole {humanize_number(amount)} {currency} from {target.mention}!")
          await self.config.user(target).steal_immunity.set(cur_time)
        else:
          await bank.transfer_credits(ctx.author, target, amount//2)
          await ctx.send(f"You failed to rob {target.mention} and lost {humanize_number(amount//2)} {currency}!")

        await self.config.user(author).steal_cooldown.set(cur_time)
      else:
        await ctx.send(f"{target.mention} doesn't have enough {currency} for you to steal that much!")
    else:
      await ctx.send(f"You don't have enough {currency} to steal that much!")
