"""Copyright 2024 Mysty<evieepy@gmail.com>

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""

import asyncio
import datetime
import logging
import re
from typing import TYPE_CHECKING

import discord
import requests
from discord.ext import commands, tasks

import core
from types_.portals import SERVER_T


if TYPE_CHECKING:
    from types_.portals import PortalPayload, UnitMapping, Units


logger: logging.Logger = logging.getLogger(__name__)


URL: str = "https://www.vulbis.com/portal.php"
PORTAL_RE: re.Pattern[str] = re.compile(r"\[(?P<pos>.*)\](.*?)(?P<updated>[0-9]{1,4})\s(?P<unit>h|m|s|d{1})?")


class Portals(commands.Cog):
    def __init__(self, bot: core.Bot) -> None:
        self.bot: core.Bot = bot

        self._last_payload: dict[SERVER_T, dict[str, PortalPayload]] = {name: {} for name in core.SERVERS}

        self._server_iter: core.ServerIter = core.ServerIter()
        self._portals: list[str] = ["Xélorium", "Ecaflipus", "Enutrosor", "Srambad"]

        self.unit_mapping: UnitMapping = {"d": "days", "h": "hours", "m": "minutes", "s": "seconds"}
        self._english_names: dict[str, str] = {
            "Xélorium": "Xelorium",
            "Ecaflipus": "Ecaflipus",
            "Enutrosor": "Enurado",
            "Srambad": "Srambad",
        }

        self.emojis: dict[str, str] = {
            "Xelorium": "<:Xelorium:1259811660223352864>",
            "Ecaflipus": "<:Ecaflipus:1259811654133092382>",
            "Srambad": "<:Srambad:1259811657077624893>",
            "Enurado": "<:Enutrosor:1259811658302488678>",
        }

    @property
    def cookies(self) -> dict[str, str]:
        return {
            "XÃ©loriumServer": "Tal%20Kasha",
            "SrambadServer": "Tal%20Kasha",
            "EnutrosorServer": "Tal%20Kasha",
            "EcaflipusServer": "Tal%20Kasha",
            "SERVER_CHOICE": "Tal%20Kasha",
            "PERCENT_CHOICE": "0",
            "BUY_QTY": "1",
            "SELL_QTY": "1",
            "PERCENT_SELL_CHOICE": "0",
            "TYPE": "-1",
            "cf_clearance": core.CONFIG["SCRAPER"]["cf_clearance"],
        }

    @property
    def headers(self) -> dict[str, str]:
        return {
            "accept": "*/*",
            "accept-language": "en-AU,en-US;q=0.9,en;q=0.8",
            "content-type": "application/x-www-form-urlencoded; charset=UTF-8",
            "origin": "https://www.vulbis.com",
            "priority": "u=1, i",
            "referer": "https://www.vulbis.com/?server=Tal%20Kasha&gids=&percent=0&craftableonly=false&select-type=-1&sellchoice=false&buyqty=1&sellqty=1&percentsell=0",
            "sec-ch-ua": '"Google Chrome";v="125", "Chromium";v="125", "Not.A/Brand";v="24"',
            "sec-ch-ua-arch": '"x86"',
            "sec-ch-ua-bitness": '"64"',
            "sec-ch-ua-full-version": '"125.0.6422.141"',
            "sec-ch-ua-full-version-list": '"Google Chrome";v="125.0.6422.141", "Chromium";v="125.0.6422.141", "Not.A/Brand";v="24.0.0.0"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-model": '""',
            "sec-ch-ua-platform": '"Windows"',
            "sec-ch-ua-platform-version": '"15.0.0"',
            "sec-fetch-dest": "empty",
            "sec-fetch-mode": "cors",
            "sec-fetch-site": "same-origin",
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
            "x-requested-with": "XMLHttpRequest",
        }

    async def cog_load(self) -> None:
        self.dip_updater.start()

    def _parse_data(self, server: SERVER_T, *, portal: str, data: str) -> None:
        match: re.Match[str] | None = PORTAL_RE.search("".join(data.splitlines()))
        if not match:
            return

        pos: list[int] = [int(p) for p in match.group("pos").split(",")]
        updated: int = int(match.group("updated"))
        unit: Units = self.unit_mapping.get(match.group("unit"), "unknown")

        self._last_payload[server][portal] = {"pos": pos, "updated": updated, "unit": unit}

    def _convert_time(self, *, unit: str, updated: int) -> str:
        if unit == "unknown":
            return "Unknown"

        seconds: float = (
            updated * 86400
            if unit == "days"
            else updated * 3600
            if unit == "hours"
            else updated * 60
            if unit == "minutes"
            else updated
        )
        delta: datetime.datetime = datetime.datetime.now() - datetime.timedelta(seconds=seconds)

        return f"<t:{int(delta.timestamp())}:R>"

    def _fetch_portals(self, server: SERVER_T) -> None:
        for portal in self._portals:
            data: bytes = f"portal={portal}&server={server}".encode()

            resp = requests.post(URL, cookies=self.cookies, headers=self.headers, data=data)
            if resp.status_code != 200:
                logger.warning("Unable to fetch portal position for: %s | %s", portal, resp.status_code)
                return

            html: str = resp.text
            self._parse_data(server, portal=self._english_names.get(portal, portal), data=html)

    def generate_embed(self, server: SERVER_T) -> discord.Embed:
        embed: discord.Embed = discord.Embed(title=f"{server} - Portals", color=0xF7B5C2)
        embed.set_thumbnail(url=self.bot.user.avatar.url)  # type: ignore

        if not self._last_payload:
            embed.description = "No portal data available!"
            return embed

        data: dict[str, PortalPayload] = self._last_payload[server]

        for key, value in data.items():
            position: str = str(value.get("pos", "Unknown"))
            unit: str = value.get("unit", "unknown")
            updated: int = value.get("updated", 0)
            name: str = key

            stamp: str = self._convert_time(unit=unit, updated=updated)
            embed.add_field(name=f"{name} Dimension", value=f"`{position}`\n{self.emojis[name]} {stamp}", inline=False)

        return embed

    @commands.hybrid_command()
    async def portals(self, ctx: commands.Context[core.Bot], *, server: SERVER_T) -> None:
        """Fetch the last known positions of the dimension portals.

        Parameters
        ----------
        server: str
            The server to get Portal Positions for.
        """
        await ctx.defer(ephemeral=True)

        embed: discord.Embed = self.generate_embed(server)
        await ctx.send(embed=embed, ephemeral=True)

    async def _update_dip(self, server: SERVER_T) -> None:
        embed: discord.Embed = self.generate_embed(server)
        channel: discord.TextChannel | None = self.bot.get_channel(1250936053603242167)  # type: ignore

        if not channel:
            logger.warning("Unable to find the Discord International Pub channel for auto-updates.")
            return

        history: list[discord.Message] = [m async for m in channel.history()]

        try:
            previous: discord.Message = history[self._server_iter.index]
        except IndexError:
            await channel.send(embed=embed)
        else:
            await previous.edit(embed=embed)

    @tasks.loop(minutes=10)
    async def dip_updater(self) -> None:
        server: SERVER_T = next(self._server_iter)
        await asyncio.to_thread(self._fetch_portals, server)

        await self._update_dip(server)

    @dip_updater.before_loop
    async def dip_updater_before(self) -> None:
        await self.bot.wait_until_ready()


async def setup(bot: core.Bot) -> None:
    await bot.add_cog(Portals(bot))
