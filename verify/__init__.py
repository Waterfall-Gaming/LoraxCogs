from .verify import WaterfallVerification


async def setup(bot):
  await bot.add_cog(WaterfallVerification(bot))