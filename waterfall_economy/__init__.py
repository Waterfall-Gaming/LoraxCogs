from .waterfall_economy import WaterfallEconomy


async def setup(bot):
  await bot.add_cog(WaterfallEconomy(bot))
