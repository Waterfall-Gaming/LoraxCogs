from redbot.core import Config, commands, app_commands, bank
from redbot.core.commands.converter import TimedeltaConverter
from redbot.core.utils.chat_formatting import humanize_number

from datetime import datetime, timezone, timedelta
from random import randint, choice
import asyncio
import discord
import re

from ...util.gambling import RouletteBetType, RouletteBet
from ...util.embeds import ErrorEmbed


class RouletteCommands(commands.Cog):
  """Roulette gambling commands"""

  roulette_numbers = [
    0, 32, 15, 19, 4, 21, 2, 25, 17, 34, 6, 27,
    13, 36, 11, 30, 8, 23, 10, 5, 24, 16, 33, 1,
    20, 14, 31, 9, 22, 18, 2, -7, 28, 12, 35, 3, 26
  ]

  reds = [
    32, 19, 21, 25, 34, 27, 36, 30, 23, 5,
    16, 1, 14, 9, 18, 7, 12, 3
  ]

  blacks = [
    15, 4, 2, 17, 6, 13, 11, 8, 10, 24,
    33, 20, 31, 22, 2, 28, 35, 26
  ]

  bet_names = {
    "straight": ["straight", "number", "num", "single"],
    "zero": ["zero"],
    "red": ["red", "reds"],
    "black": ["black", "blacks"],
    "even": ["even", "evens"],
    "odd": ["odd", "odds"],
    "low": ["low", "lows"],
    "high": ["high", "highs"],
    "snake": ["snake"],
    "dozen": ["dozen", "12"],
    "corner": ["corner"],
    "top": ["top"],
    "column": ["column", "col"]
  }

  def __init__(self, bot):
    # super().__init__()
    self.bot = bot
    self.config = None
    self._close_tasks = set()

  @staticmethod
  def __build_dozen_bet(dozen_num: int):
    """Builds a dozen bet for the number"""
    if dozen_num == 1:
      return RouletteBetType(
        name="Dozen Bet on 1 to 12",
        payout=2.0,
        condition=lambda result: 1 <= result <= 12
      )
    elif dozen_num == 2:
      return RouletteBetType(
        name="Dozen Bet on 13 to 24",
        payout=2.0,
        condition=lambda result: 13 <= result <= 24
      )
    elif dozen_num == 3:
      return RouletteBetType(
        name="Dozen Bet on 25 to 36",
        payout=2.0,
        condition=lambda result: 25 <= result <= 36
      )
    else:
      raise ValueError("Invalid dozen bet specification.")

  def _parse_bet(self, bet_type: str) -> RouletteBetType:
    """Parse a bet type string into a RouletteBet object"""
    bet_split = re.split(r"([ \-–_+&,]|(, )|(,? (to|and) ))", bet_type.strip().lower())

    # length 1
    if len(bet_split) == 1:
      # straight bet
      if bet_split[0].isdigit():
        number = int(bet_split[0])
        if 0 <= number <= 36:
          return RouletteBetType(
            name=f"Straight Bet on {number}",
            payout=35.0,
            condition=lambda result: result == number
          )
        else:
          raise ValueError("Straight bets must be on numbers between 0 and 36.")
      elif bet_split[0] in self.bet_names["zero"]:
        return RouletteBetType(
          name="0️⃣ Zero",
          payout=35.0,
          condition=lambda result: result == 0
        )
      elif bet_split[0] in self.bet_names["red"]:
        return RouletteBetType(
          name="🔴 Red",
          payout=1.0,
          condition=lambda result: result in self.reds
        )
      elif bet_split[0] in self.bet_names["black"]:
        return RouletteBetType(
          name="⚫ Black",
          payout=1.0,
          condition=lambda result: result in self.blacks
        )
      elif bet_split[0] in self.bet_names["even"]:
        return RouletteBetType(
          name="Evens",
          payout=1.0,
          condition=lambda result: result != 0 and result % 2 == 0
        )
      elif bet_split[0] in self.bet_names["odd"]:
        return RouletteBetType(
          name="Odds",
          payout=1.0,
          condition=lambda result: result % 2 == 1
        )
      elif bet_split[0] in self.bet_names["low"]:
        return RouletteBetType(
          name="⬇️ Low (1-18) Bet",
          payout=1.0,
          condition=lambda result: 1 <= result <= 18
        )
      elif bet_split[0] in self.bet_names["high"]:
        return RouletteBetType(
          name="⬆️ High (19-36) Bet",
          payout=1.0,
          condition=lambda result: 19 <= result <= 36
        )
      elif bet_split[0] in self.bet_names["snake"]:
        return RouletteBetType(
          name="🐍 Snake Bet",
          payout=2.0,
          condition=lambda result: result in [1, 5, 9, 12, 14, 16, 19, 23, 27, 30, 32, 34]
        )
      elif bet_split[0] in self.bet_names["top"]:
        return RouletteBetType(
          name="🔝 Top Line Bet on 0, 1, 2, and 3",
          payout=8.0,
          condition=lambda result: result in [0, 1, 2, 3]
        )
      raise ValueError("Invalid bet type specified.")
    # all the special ones
    elif len(bet_split) == 2:
      # ranges
      if bet_split[0].isdigit() and bet_split[1].isdigit():
        low = int(bet_split[0])
        high = int(bet_split[1])

        if 0 <= low <= 36 and 0 <= high <= 36:
          if low > high:
            low, high = high, low
        else:
          raise ValueError("Bets must be on numbers between 0 and 36.")

        # split bet, 2 adjacent nums
        if (high == low + 1) or (high-low == 3) and (low != 0 and high != 0):
          return RouletteBetType(
            name=f"Split Bet on {low} and {high}",
            payout=17.0,
            condition=lambda result: result == low or result == high
          )
        # street bet, 3 nums in a row
        elif (high - low == 2) and (low % 3 == 1):
          return RouletteBetType(
            name=f"Street Bet on {low}, {low+1}, and {high}",
            payout=11.0,
            condition=lambda result: low <= result <= high
          )
        # double street bet, 6 nums in two rows
        elif (high - low == 5) and (low % 3 == 1):
          return RouletteBetType(
            name=f"Double Street Bet on {low} to {high}",
            payout=5.0,
            condition=lambda result: low <= result <= high
          )
        # dozen bet 12 nums
        elif (high - low == 11) and (low in [1, 13, 25]):
          return RouletteBetType(
            name=f"Dozen Bet on {low} to {high}",
            payout=2.0,
            condition=lambda result: low <= result <= high
          )
        # high/low bet 18 nums
        elif (high - low == 17) and (low in [1, 19]):
          return RouletteBetType(
            name=f"{'⬇️ Low (1-18)' if low == 1 else '⬆️ High (19-36)'} Bet",
            payout=1.0,
            condition=lambda result: low <= result <= high
          )
      # dozen (dozen 1 style)
      elif bet_split[0] in self.bet_names["dozen"] and bet_split[1].isdigit():
        dozen_num = int(bet_split[1])
        return self.__build_dozen_bet(dozen_num)
      # dozen alternate notation - i.e. first dozen, 2nd dozen, middle dozen, last dozen
      elif bet_split[1] in self.bet_names["dozen"] and bet_split[0][-2:] in ["st", "nd", "rd", "le"]:
        if bet_split[0][0].isdigit():
          dozen_num = int(bet_split[0][0])
        elif bet_split[0] == "first":
          dozen_num = 1
        elif bet_split[0] in ["second", "middle"]:
          dozen_num = 2
        elif bet_split[0] in ["third", "last"]:
          dozen_num = 3
        else:
          raise ValueError("Invalid dozen bet specification.")
        return self.__build_dozen_bet(dozen_num)
      # column (column 1 style)
      elif bet_split[0] in self.bet_names["column"] and bet_split[1].isdigit():
        column_num = int(bet_split[1])
        if 1 <= column_num <= 3:
          raise ValueError("Column bets must be on columns 1, 2, or 3.")
        return RouletteBetType(
          name=f"Column Bet on Column {column_num}",
          payout=2.0,
          condition=lambda result: result != 0 and (result - column_num) % 3 == 0
        )
      # column alternate notation - i.e. first column, 2nd column, middle column, last column
      elif bet_split[1] in self.bet_names["column"] and bet_split[0][-2:] in ["st", "nd", "rd", "le"]:
        if bet_split[0][0].isdigit():
          column_num = int(bet_split[0][0])
        elif bet_split[0] == "first":
          column_num = 1
        elif bet_split[0] in ["second", "middle"]:
          column_num = 2
        elif bet_split[0] in ["third", "last"]:
          column_num = 3
        else:
          raise ValueError("Invalid column bet specification.")
        return RouletteBetType(
          name=f"Column Bet on Column {column_num}",
          payout=2.0,
          condition=lambda result: result != 0 and (result - column_num) % 3 == 0
        )
      # corner bet
      elif bet_split[0] in self.bet_names["corner"] and bet_split[1].isdigit():
        corner_num = int(bet_split[1])
        if not (1 <= corner_num <= 32) or (corner_num % 3 == 0):
          raise ValueError("Corner bets can't be made on numbers in the last row/column.")
        return RouletteBetType(
          name=f"Corner Bet on {corner_num}, {corner_num+1}, {corner_num+3}, and {corner_num+4}",
          payout=8.0,
          condition=lambda result: result in [corner_num, corner_num+1, corner_num+3, corner_num+4]
        )
      # top line
      elif bet_split[0] in self.bet_names["top"] and bet_split[1] == "line":
        return RouletteBetType(
          name="🔝 Top Line Bet on 0, 1, 2, and 3",
          payout=8.0,
          condition=lambda result: result in [0, 1, 2, 3]
        )
    # length 3 (rows)
    elif len(bet_split) == 3:
      # street bet alternate notation like 1, 2, 3
      if bet_split[0].isdigit() and bet_split[1].isdigit() and bet_split[2].isdigit():
        nums = sorted([int(bet_split[0]), int(bet_split[1]), int(bet_split[2])])
        if nums[0] < 1 or nums[2] > 36:
          raise ValueError("Bets must be on numbers between 0 and 36.")
        if nums[2] - nums[0] == 2 and nums[0] % 3 == 1:
          return RouletteBetType(
            name=f"Street Bet on {nums[0]}, {nums[1]}, and {nums[2]}",
            payout=11.0,
            condition=lambda result: nums[0] <= result <= nums[2]
          )
      raise ValueError("Invalid bet type specified.")
    # length 4 (corners)
    elif len(bet_split) == 4:
      # corner bet alternate notation like 1,2,4,5
      if all(part.isdigit() for part in bet_split):
        nums = sorted([int(part) for part in bet_split])
        if nums[0] < 1 or nums[3] > 36:
          raise ValueError("Bets must be on numbers between 0 and 36.")
        if nums[1] == nums[0] + 1 and nums[2] == nums[0] + 3 and nums[3] == nums[0] + 4:
          return RouletteBetType(
            name=f"Corner Bet on {nums[0]}, {nums[1]}, {nums[2]}, and {nums[3]}",
            payout=8.0,
            condition=lambda result: result in nums
          )
      elif [int(part) for part in bet_split if part.isdigit()] == [0, 1, 2, 3]:
        return RouletteBetType(
          name="🔝 Top Line Bet on 0, 1, 2, and 3",
          payout=8.0,
          condition=lambda result: result in [0, 1, 2, 3]
        )
      raise ValueError("Invalid bet type specified.")
    # too long, fuck you
    raise ValueError("Bet definition too long.")

  async def _close_table(self, table: discord.Thread, delay: int = 0):
    """Close a roulette table and determine winners"""
    # Implementation of closing the table
    table = await self.config.guild(table.guild).GAMBLING.ROULETTE.OPEN_TABLES.get(table.id)
    if table is None or not table["is_open"]:
      return
    if table.id in self._close_tasks:
      return

    self._close_tasks.add(table.id)
    await asyncio.sleep(delay)

    # mark the table as closed
    await self.config.guild(table.guild).GAMBLING.ROULETTE.OPEN_TABLES[table.id].is_open.set(False)

    with table.typing():
      spinning_msg = await table.send("Spinning the roulette wheel... 🎡")
      await asyncio.sleep(5)  # simulate spinning time

    # determine winning number
    winning_number = choice(self.roulette_numbers)
    colour = '🔴' if winning_number in self.reds else ('⚫' if winning_number in self.blacks else '🟢')

    await spinning_msg.edit(
      content=f"The roulette wheel has stopped! The winning number is {colour} **{winning_number}**! 🎉"
    )

    # calculate winners
    await self._calculate_winners(table, winning_number)

  async def _calculate_winners(self, table: discord.Thread, winning_number: int):
    """Calculate winners for a given roulette table and winning number"""
    # Implementation of calculating winners
    bets = await self.config.guild(table.guild).GAMBLING.ROULETTE.OPEN_TABLES[table.id].bets()
    currency_name = await bank.get_currency_name()

    async with table.typing():
      for bet in bets:
        user = bet.bettor
        if bet.check_bet_win(winning_number):
          payout = int(bet.amount * (bet.bet_type.payout + 1))
          await bank.deposit_credits(user, payout)

          await table.send(
            f"Congratulations {user.mention}! Your bet on **{bet.bet_type.name}** won! "
            f"You won {humanize_number(payout)} {currency_name}."
          )
    # wait to close
    await asyncio.sleep(5)
    await table.send("This table is now closed. Thank you for playing!")

    # close the table
    await table.edit(archived=True)
    await self.config.guild(table.guild).GAMBLING.ROULETTE.OPEN_TABLES[table.id].clear()

  @commands.group(name="roulette", aliases=["roul", "rol"])
  @commands.guild_only()
  async def command_roulette(self, ctx: commands.Context):
    """Roulette gambling commands"""
    pass

  @command_roulette.command(name="open", aliases=["start", "create"])
  async def command_roulette_open(
      self, ctx: commands.Context,
      min_bet: int = None, max_bet: int = None,
      timeout: TimedeltaConverter = timedelta(seconds=300),
      table_name: str = "{}'s Roulette Table"
  ):
    """Open a roulette table"""

    # check if the user already has an open table
    open_tables = await self.config.guild(ctx.guild).GAMBLING.ROULETTE.OPEN_TABLES()
    for table_id, table_data in open_tables.items():
      if table_data["owner"] == ctx.author.id and table_data["is_open"]:
        await ctx.send(embed=ErrorEmbed(
          title="Too Many Open Tables",
          message="You already have an open roulette table!\nPlease finish the current game before opening a new one."
        ))
        return

    # validate min and max bet, or set them to defaults
    max_bet_cfg = await self.config.guild(ctx.guild).GAMBLING.ROULETTE.MAX_BET()
    min_bet_cfg = await self.config.guild(ctx.guild).GAMBLING.ROULETTE.MIN_BET()
    currency_name = await bank.get_currency_name()

    # min bet validation
    if min_bet is None:
      min_bet = await self.config.guild(ctx.guild).GAMBLING.ROULETTE.MIN_BET()
    elif min_bet < min_bet_cfg:
      await ctx.send(embed=ErrorEmbed(
        title="Invalid Minimum Bet",
        message=f"The minimum allowed bet for roulette is {humanize_number(min_bet_cfg)} {currency_name}."
      ))
      return

    # max bet validation
    if max_bet is None:
      max_bet = await self.config.guild(ctx.guild).GAMBLING.ROULETTE.MAX_BET()
    elif max_bet > max_bet_cfg:
      await ctx.send(embed=ErrorEmbed(
        title="Invalid Maximum Bet",
        message=f"The maximum allowed bet for roulette is {humanize_number(max_bet_cfg)} {currency_name}."
      ))
      return

    # validate timeout
    max_duration_cfg = await self.config.guild(ctx.guild).GAMBLING.ROULETTE.MAX_DURATION()
    min_duration_cfg = await self.config.guild(ctx.guild).GAMBLING.ROULETTE.MIN_DURATION()

    if not (min_duration_cfg <= timeout.total_seconds() <= max_duration_cfg):
      await ctx.send(embed=ErrorEmbed(
        title="Invalid Timeout Duration",
        message=f"The timeout duration must be between {min_duration_cfg}s and {max_duration_cfg}s."
      ))
      return

    # validate permissions in current channel
    user_perms = ctx.channel.permissions_for(ctx.author)
    bot_perms = ctx.channel.permissions_for(ctx.guild.me)

    if not user_perms.create_public_threads:
      await ctx.send(embed=ErrorEmbed(
        title="Insufficient Permissions",
        message="You do not have permission to create threads in this channel."
      ))
      return

    if not bot_perms.create_public_threads:
      await ctx.send(embed=ErrorEmbed(
        title="Bot Permission Error",
        message="I do not have permission to create threads in this channel."
      ))
      return

    # now that we've validated stuff, create the table and thread and stuff

    # create a thread for the table
    table = await ctx.channel.create_thread(name=table_name.format(ctx.author.display_name), auto_archive_duration=60)

    # write the table's thread into config
    await self.config.guild(ctx.guild).GAMBLING.ROULETTE.OPEN_TABLES[table.id].set({
      "owner": ctx.author.id,
      "min_bet": min_bet,
      "max_bet": max_bet,
      "duration": timeout.total_seconds(),
      "bets": [],
      "is_open": True,
    })

    # when the table closes
    table_closes = datetime.now() + timedelta(seconds=timeout.total_seconds())

    await table.send(
      f"# {table_name.format(ctx.author.display_name)}\n"
      f"{ctx.author.mention} has opened a roulette table!\n"
      f"> Minimum Bet: {humanize_number(min_bet)} {currency_name}\n"
      f"> Maximum Bet: {humanize_number(max_bet)} {currency_name}\n"
      f"*Betting closes <t:{datetime.now() + timedelta(seconds=timeout.total_seconds())}:R>*.\n"
    )

    self.bot.loop.create_task(self._close_table(table, int(timeout.total_seconds())))

  @command_roulette.command(name="bet")
  async def command_roulette_bet(
      self, ctx: commands.Context,
      amount: int,
      bet_type: str
  ):
    """Place a bet on the current roulette table"""
    # Implementation of placing a bet
    tables = await self.config.guild(ctx.guild).GAMBLING.ROULETTE.OPEN_TABLES()

    if ctx.channel.id not in tables:
      await ctx.send(embed=ErrorEmbed(
        title="No Open Table",
        message="There is no open roulette table in this channel."
      ))
      return

    table_data = tables[ctx.channel.id]

    if not table_data["is_open"]:
      await ctx.send(embed=ErrorEmbed(
        title="Table Closed",
        message="The roulette table in this channel is closed for betting."
      ))
      return

    # validate bet amount
    if not (table_data["min_bet"] <= amount <= table_data["max_bet"]):
      currency_name = await bank.get_currency_name()
      await ctx.send(embed=ErrorEmbed(
        title="Invalid Bet Amount",
        message=f"Your bet must be between {humanize_number(table_data['min_bet'])} and "
                f"{humanize_number(table_data['max_bet'])} {currency_name}."
      ))
      return

    # parse bet type
    try:
      parsed_bet_type = self._parse_bet(bet_type)
    except ValueError as e:
      await ctx.send(embed=ErrorEmbed(
        title="Invalid Bet Type",
        message=str(e)
      ))
      return

    # withdraw bet amount
    if await bank.can_spend(ctx.author, amount):
      await bank.withdraw_credits(ctx.author, amount)
    else:
      currency_name = await bank.get_currency_name()
      await ctx.send(embed=ErrorEmbed(
        title="Insufficient Funds",
        message=f"You do not have enough {currency_name} to place this bet."
      ))
      return

    # record the bet
    bet = RouletteBet(
      bettor=ctx.author,
      bet_type=parsed_bet_type,
      amount=amount
    )

    await self.config.guild(ctx.guild).GAMBLING.ROULETTE.OPEN_TABLES[ctx.channel.id].bets.append(bet)

    await ctx.send(
      f"{ctx.author.mention}, your bet of {humanize_number(amount)} on **{parsed_bet_type.name}** has been placed!"
    )

  @command_roulette.command(name="spin", aliases=["roll", "play", "close"])
  async def command_roulette_spin(self, ctx: commands.Context):
    """Spin the roulette wheel. Closes betting."""
    # Implementation of spinning the roulette wheel
    await self._close_table(ctx.channel)
