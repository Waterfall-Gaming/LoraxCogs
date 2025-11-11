from redbot.core import bank
import discord


class RouletteBetType:
  def __init__(self, name: str, payout: float, condition):
    self.name = name
    self.payout = payout
    self.condition = condition  # A function that takes the winning number and returns True if the bet wins

  def check_win(self, result: int) -> bool:
    return self.condition(result)


class RouletteBet:
  def __init__(self, bettor: discord.User, bet_type: RouletteBetType, amount: int):
    self.bettor = bettor
    self.bet_type = bet_type
    self.amount = amount

  def check_bet_win(self, result: int) -> bool:
    return self.bet_type.check_win(result)
