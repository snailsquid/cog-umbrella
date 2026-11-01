from redbot.core.bot import Red

from .umbrella import Umbrella


async def setup(bot: Red) -> None:
    await bot.add_cog(Umbrella(bot))
