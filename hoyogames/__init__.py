from .hoyogames import HoYoGames


async def setup(bot):
  await bot.add_cog(HoYoGames(bot))