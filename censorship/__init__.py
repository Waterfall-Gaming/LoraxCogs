from .censorship import Censorship


async def setup(bot):
  await bot.add_cog(Censorship(bot))