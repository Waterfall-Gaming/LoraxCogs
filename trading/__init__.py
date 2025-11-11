from .trading import Trading


async def setup(bot):
  await bot.add_cog(Trading(bot))