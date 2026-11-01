from typing import Any, Dict, Optional, Tuple

import aiohttp
import discord
from redbot.core import Config, commands
from redbot.core.bot import Red

GEOCODE_URL = "https://geocoding-api.open-meteo.com/v1/search"
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
# Rain chance (%) at which we say "take one".
TAKE_IT_AT = 40


class Umbrella(commands.Cog):
    """Tells you whether to take an umbrella today (Open-Meteo, no API key)."""

    def __init__(self, bot: Red) -> None:
        self.bot = bot
        self.config = Config.get_conf(self, identifier=935349165196, force_registration=True)
        self.config.register_user(home=None)
        self.session = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10))

    async def cog_unload(self) -> None:
        await self.session.close()

    async def red_delete_data_for_user(self, *, requester: str, user_id: int) -> None:
        await self.config.user_from_id(user_id).clear()

    async def _get_json(self, url: str, params: Dict[str, Any]) -> Dict[str, Any]:
        async with self.session.get(url, params=params) as resp:
            resp.raise_for_status()
            return await resp.json()

    async def _geocode(self, place: str) -> Optional[Tuple[str, float, float]]:
        data = await self._get_json(GEOCODE_URL, {"name": place, "count": 1, "format": "json"})
        results = data.get("results") or []
        if not results:
            return None
        r = results[0]
        label = ", ".join(p for p in (r.get("name"), r.get("admin1"), r.get("country")) if p)
        return label, r["latitude"], r["longitude"]

    async def _today(self, lat: float, lon: float) -> Dict[str, Any]:
        data = await self._get_json(
            FORECAST_URL,
            {
                "latitude": lat,
                "longitude": lon,
                "daily": "precipitation_probability_max,precipitation_sum,temperature_2m_max",
                "hourly": "precipitation_probability",
                "timezone": "auto",
                "forecast_days": 1,
            },
        )
        daily = data["daily"]
        hourly = data["hourly"]
        wet_hours = [
            t[-5:]
            for t, p in zip(hourly["time"], hourly["precipitation_probability"])
            if p is not None and p >= TAKE_IT_AT
        ]
        return {
            "chance": daily["precipitation_probability_max"][0] or 0,
            "mm": daily["precipitation_sum"][0] or 0.0,
            "max_temp": daily["temperature_2m_max"][0],
            "wet_hours": wet_hours,
        }

    @commands.group(name="umbrella", invoke_without_command=True)
    async def umbrella(self, ctx: commands.Context, *, place: Optional[str] = None) -> None:
        """Do I need an umbrella today? Uses your home city if no place is given."""
        place = place or await self.config.user(ctx.author).home()
        if not place:
            await ctx.send(
                f"Where? Try `{ctx.clean_prefix}umbrella Bandung` or save a default with "
                f"`{ctx.clean_prefix}umbrella home <city>`."
            )
            return
        async with ctx.typing():
            try:
                found = await self._geocode(place)
                if found is None:
                    await ctx.send(f"I couldn't find a place called **{place}**.")
                    return
                label, lat, lon = found
                today = await self._today(lat, lon)
            except (aiohttp.ClientError, KeyError, IndexError):
                await ctx.send("The weather service didn't answer properly; try again in a bit.")
                return

        chance = today["chance"]
        if chance >= TAKE_IT_AT:
            verdict = "☔ **Take an umbrella.**"
        elif chance >= 20:
            verdict = "🌦️ Probably fine, but a small umbrella wouldn't hurt."
        else:
            verdict = "☀️ **No umbrella needed.**"
        lines = [
            verdict,
            f"Rain chance today: **{chance}%** · expected {today['mm']:.1f} mm"
            f" · high {today['max_temp']:.0f}°C",
        ]
        if today["wet_hours"]:
            hours = today["wet_hours"]
            span = hours[0] if len(hours) == 1 else f"{hours[0]}–{hours[-1]}"
            lines.append(f"Wettest stretch: {span} (local time)")
        embed = discord.Embed(
            title=f"Umbrella check · {label}",
            description="\n".join(lines),
            colour=discord.Colour.blue() if chance >= TAKE_IT_AT else discord.Colour.gold(),
        )
        embed.set_footer(text="Forecast: open-meteo.com")
        await ctx.send(embed=embed)
        self.bot.dispatch("umbrella_forecast", ctx.author, label, chance)

    @umbrella.command(name="home")
    async def umbrella_home(self, ctx: commands.Context, *, place: Optional[str] = None) -> None:
        """Save (or clear, with no argument) your default city."""
        if place is None:
            await self.config.user(ctx.author).home.clear()
            await ctx.send("Cleared your home city.")
            return
        try:
            found = await self._geocode(place)
        except aiohttp.ClientError:
            await ctx.send("The weather service didn't answer; try again in a bit.")
            return
        if found is None:
            await ctx.send(f"I couldn't find a place called **{place}**.")
            return
        await self.config.user(ctx.author).home.set(place)
        await ctx.send(f"Home city set to **{found[0]}**.")
