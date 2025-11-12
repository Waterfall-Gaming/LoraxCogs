from sys import prefix

from redbot.core import Config, commands, app_commands, bank
from redbot.core.commands.converter import TimedeltaConverter
from redbot.core.utils.chat_formatting import humanize_number

from datetime import datetime, timezone, timedelta
from random import randint, choice
import asyncio
import discord
import re

from ...util.gambling import RouletteBetType, RouletteBet
from ...util.embeds import ErrorEmbed, OfficialEmbed


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
    "zero": ["zero", "green"],
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

  open_tables = {}

  close_tasks = set()

  def __init__(self, bot):
    # super().__init__()
    self.bot = bot
    self.config = None

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
    bet_split = re.split(r"[ \-–_+&,]|(?:, )|(?:,? (?:to|and) )", ' '.join(bet_type).strip().lower())
    bet_split = [x for x in bet_split if x]

    # print(bet_split)

    # length 1
    if len(bet_split) == 1:
      # straight bet
      if bet_split[0].isdigit() and bet_split[0] != "0":
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
          name="0️⃣ Zero Bet",
          payout=35.0,
          condition=lambda result: result == 0
        )
      elif bet_split[0] in self.bet_names["red"]:
        return RouletteBetType(
          name="🔴 Red Bet",
          payout=1.0,
          condition=lambda result: result in self.reds
        )
      elif bet_split[0] in self.bet_names["black"]:
        return RouletteBetType(
          name="⚫ Black Bet",
          payout=1.0,
          condition=lambda result: result in self.blacks
        )
      elif bet_split[0] in self.bet_names["even"]:
        return RouletteBetType(
          name="Evens Bet",
          payout=1.0,
          condition=lambda result: result != 0 and result % 2 == 0
        )
      elif bet_split[0] in self.bet_names["odd"]:
        return RouletteBetType(
          name="Odds Bet",
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
        if not 1 <= column_num <= 3:
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
    _table = self.open_tables.get(str(table.id))
    if _table is None or not _table["is_open"]:
      return
    if table.id in self.close_tasks and delay != 0:
      return

    self.close_tasks.add(table.id)
    await asyncio.sleep(delay)

    # table was already spun manually
    if not (await table.guild.fetch_channel(table.id)):
      return

    # mark the table as closed
    self.open_tables[str(table.id)]["is_open"] = False

    async with table.typing():
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
    bets = self.open_tables[str(table.id)]['bets']
    currency_name = await bank.get_currency_name(table.guild)

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
    await table.edit(archived=True, locked=True)
    await asyncio.sleep(5)

    # close the table
    await table.delete()
    del self.open_tables[str(table.id)]

  @commands.group(name="roulette", aliases=["roul", "rol"])
  @commands.guild_only()
  async def command_roulette(self, ctx: commands.Context):
    """Roulette gambling commands"""
    pass

  @command_roulette.command(name="open", aliases=["start", "create"])
  async def command_roulette_open(
      self, ctx: commands.Context,
      table_type: str = "standard",
      timeout: TimedeltaConverter = timedelta(seconds=300),
      table_name: str = "{user}'s Roulette Table ({time})"
  ):
    """Open a roulette table"""

    # check if the user already has an open table
    for table_id, table_data in self.open_tables.items():
      if table_data["owner"] == ctx.author.id and table_data["is_open"]:
        await ctx.send(embed=ErrorEmbed(
          title="Too Many Open Tables",
          message="You already have an open roulette table!\nPlease finish the current game before opening a new one."
        ))
        return

    # validate min and max bet, or set them to defaults
    max_bet_cfg = await self.config.guild(ctx.guild).GAMBLING.ROULETTE.MAX_BET()
    min_bet_cfg = await self.config.guild(ctx.guild).GAMBLING.ROULETTE.MIN_BET()
    currency_name = await bank.get_currency_name(ctx.guild)

    # get table types
    table_types = await self.config.guild(ctx.guild).GAMBLING.ROULETTE.TABLE_TYPES()
    # min bet validation
    if table_type not in table_types.keys():
      await ctx.send(embed=ErrorEmbed(
        title="Invalid Table Type",
        message=f"The table type '{table_type}' does not exist. Available types: "
                f"`{'`, `'.join(table_types.keys())}`."
      ))
      return

    if bank.can_spend(ctx.author, table_types[table_type]["FEE"]):
      await bank.withdraw_credits(ctx.author, table_types[table_type]["FEE"])
    else:
      await ctx.send(embed=ErrorEmbed(
        title="Insufficient Funds",
        message=f"You do not have enough {currency_name} to open this table. "
                f"Opening a '{table_type}' table costs "
                f"{humanize_number(table_types[table_type]['FEE'])} {currency_name}."
      ))
      return

    min_bet = table_types[table_type]["MIN_BET"]
    max_bet = table_types[table_type]["MAX_BET"]

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

    if ctx.channel.type in [discord.ChannelType.public_thread, discord.ChannelType.private_thread]:
      await ctx.send(embed=ErrorEmbed(
        title="Invalid Channel",
        message="Roulette tables cannot be opened inside threads."
      ))
      return

    # now that we've validated stuff, create the table and thread and stuff

    table_name = table_name.format(user=ctx.author.display_name, time=datetime.now().strftime('%H:%M on %d/%m/%Y'))

    # create a thread for the table
    table = await ctx.channel.create_thread(
        message=ctx.message,
        name=table_name, auto_archive_duration=60
    )

    # write the table's thread into config
    self.open_tables[str(table.id)] = {
      "owner": ctx.author.id,
      "min_bet": min_bet,
      "max_bet": max_bet,
      "duration": timeout.total_seconds(),
      "bets": [],
      "is_open": True,
    }

    # when the table closes
    table_closes = int(datetime.now().timestamp() + timeout.total_seconds())

    await table.send(
      f"# {table_name}\n"
      f"{ctx.author.mention} has opened a roulette table!\n"
      f"> Minimum Bet: {humanize_number(min_bet)} {currency_name}\n"
      f"> Maximum Bet: {humanize_number(max_bet)} {currency_name}\n"
      f"*Betting closes <t:{table_closes}:R>*.\n"
    )

    self.bot.loop.create_task(self._close_table(table, int(timeout.total_seconds())))

  @command_roulette.command(name="bet")
  async def command_roulette_bet(
      self, ctx: commands.Context,
      amount: int | str,
      *bet_type: str
  ):
    """Place a bet on the current roulette table"""
    # Implementation of placing a bet

    # print(self.tables.keys(), ctx.channel.id)

    if str(ctx.channel.id) not in self.open_tables.keys():
      await ctx.send(embed=ErrorEmbed(
        title="No Open Table",
        message="There is no open roulette table in this channel."
      ))
      return

    table_data = self.open_tables[str(ctx.channel.id)]

    if not table_data["is_open"]:
      await ctx.send(embed=ErrorEmbed(
        title="Table Closed",
        message="The roulette table in this channel is closed for betting."
      ))
      return

    # going all in
    if isinstance(amount, str):
      if amount.lower() in ["all", "max", "everything", "all_in"]:
        user_balance = await bank.get_balance(ctx.author)
        amount = user_balance
      else:
        await ctx.send(embed=ErrorEmbed(
          title="Invalid Bet Amount",
          message="Please specify a valid bet amount."
        ))
        return

    # validate bet amount
    if not (table_data["min_bet"] <= amount <= table_data["max_bet"]):
      currency_name = await bank.get_currency_name(ctx.guild)
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
      currency_name = await bank.get_currency_name(ctx.guild)
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

    self.open_tables[str(ctx.channel.id)]["bets"].append(bet)

    await ctx.send(
      f"{ctx.author.mention}, your **{parsed_bet_type.name}** of {humanize_number(amount)} has been placed!"
    )

  @command_roulette.command(name="spin", aliases=["roll", "play", "close"])
  async def command_roulette_spin(self, ctx: commands.Context):
    """Spin the roulette wheel. Closes betting."""

    # check if it's a roulette table
    if str(ctx.channel.id) not in self.open_tables.keys():
      await ctx.send(embed=ErrorEmbed(
        title="No Open Table",
        message="There is no open roulette table in this channel."
      ))
      return

    # are you allowed to do that?
    if (ctx.author.id != self.open_tables[str(ctx.channel.id)]["owner"]
        and not ctx.author.guild_permissions.administrator):
      await ctx.send(embed=ErrorEmbed(
        title="Permission Denied",
        message="Only the table owner can spin the roulette wheel."
      ))
      return

    await self._close_table(ctx.channel)

  @command_roulette.group(name="help", aliases=["?"])
  async def command_roulette_help(self, ctx: commands.Context):
    """Roulette help commands"""
    pass

  @command_roulette_help.command(name="bets", aliases=["bettypes", "types"])
  async def command_roulette_help_bets(self, ctx: commands.Context):
    """Help with bet types"""
    prefix = (await self.bot.get_valid_prefixes())[0]

    embed = OfficialEmbed(
      title="Roulette Bet Types",
      message=(
        "Here are the available bet types you can place in roulette:\n"
      ),
      guild=ctx.guild
    )

    bet_types = [
      ("Straight Bet", "A bet on a single number (payout: 35:1).", "17"),
      ("Red/Black Bet", "A bet on all red or black numbers (payout: 1:1).", "red"),
      ("Even/Odd Bet", "A bet on all even or odd numbers (payout: 1:1).", "even"),
      ("Low/High Bet", "A bet on low (1-18) or high (19-36) numbers (payout: 1:1).", "low|1-18"),
      ("Dozen Bet", "A bet on one of the three dozens: 1-12, 13-24, or 25-36 (payout: 2:1).", "1st dozen|dozen 1|first dozen"),
      ("Column Bet", "A bet on one of the three columns of numbers (payout: 2:1).", "1st col|column 1|first column"),
      ("Split Bet", "A bet on two adjacent numbers (payout: 17:1).", "17 18"),
      ("Street Bet", "A bet on three numbers in a horizontal line (payout: 11:1).", "1 2 3|1-3"),
      ("Corner Bet", "A bet on four numbers that form a square (payout: 8:1).", "1 2 4 5|corner 1"),
      ("Double Street Bet", "A bet on six numbers in two horizontal lines (payout: 5:1).", "1-6"),
      ("Top Line Bet", "A bet on 0, 1, 2, and 3 (payout: 8:1).", "top|top line"),
      ("Snake Bet", "A bet on a snaking pattern of numbers (payout: 2:1).", "snake"),
      ("Zero Bet", "A bet specifically on 0 (payout: 35:1).", "zero|green"),
    ]

    for name, description, example in bet_types:
      embed.add_field(
        name=f"**{name}**",
        value=(
          f"{description}\n"
          f"*Example:* `{prefix}roulette bet 100 <{example}>`"
        ),
        inline=True
      )

    embed.add_field(
        name="Placing a Bet",
        value=(
          "To place a bet, use the command:\n"
          f"`{prefix}roulette bet <amount> <bet type>`\n"
        ),
        inline=False
    )

    await ctx.send(embed=embed)

  @command_roulette_help.command(name="table", aliases=["tables", "tabletypes"])
  async def command_roulette_help_table(self, ctx: commands.Context):
    """Help with roulette table types"""
    prefix = (await self.bot.get_valid_prefixes())[0]
    table_types = await self.config.guild(ctx.guild).GAMBLING.ROULETTE.TABLE_TYPES()

    embed = OfficialEmbed(
      title="Roulette Table Types",
      message="These are the available roulette table types:",
      guild=ctx.guild
    )

    for table_type, settings in table_types.items():
      embed.add_field(
        name=f"**{' '.join(table_type.split('_')).capitalize()} Table**",
        value=(
          f"- Minimum Bet: `{humanize_number(settings['MIN_BET'])}`\n"
          f"- Maximum Bet: `{humanize_number(settings['MAX_BET'])}`\n"
          f"- Opening Fee: `{humanize_number(settings['FEE'])}`\n"
          f"*To open: `{prefix}roulette open {table_type}`*"
        ),
        inline=True
      )

    await ctx.send(embed=embed)

  @command_roulette_help.command(name="play", aliases=["start", "create"])
  async def command_roulette_help_play(self, ctx: commands.Context):
    """Help with opening a roulette table"""
    prefix = (await self.bot.get_valid_prefixes())[0]

    embed = OfficialEmbed(
      title="Opening a Roulette Table",
      message=(
        "To open a roulette table, use the command:\n"
        f"`{prefix}roulette open [table_type] [timeout] [table_name]`\n\n"
        "**Parameters:**\n"
        "- `table_type`: The type of table to open (default: standard). Different types may have different min/max bets.\n"
        "- `timeout`: Duration before betting closes (default: 300s). Specify in seconds or using time format (e.g., 5m for 5 minutes).\n"
        "- `table_name`: Custom name for the table thread (default: \"{user}'s Roulette Table ({time})\").\n\n"
        "Example:\n"
        f"- `{prefix}roulette open`\n"
        f"- `{prefix}roulette open standard 10m \"My First Roulette Table\"`\n\n"
        "**Note**:\n"
        "> You will be charged a fee to open the table based on the table type.\n"
        "> The game will start in a separate thread, and players can place bets until the timeout expires, or until the "
        "table owner (or an admin) manually spins the wheel."
      ),
      guild=ctx.guild
    )
    await ctx.send(embed=embed)


