from .testing import TestingCog


async def setup(bot):
  await bot.add_cog(TestingCog(bot))