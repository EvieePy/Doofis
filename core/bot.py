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

import logging
import sys

import aiohttp
import discord
from discord.ext import commands

from . import __version__


logger: logging.Logger = logging.getLogger(__name__)


class Bot(commands.Bot):
    def __init__(self) -> None:
        ua: str = f"Doofis Bot/{__version__}, Python/{sys.version}, Discord.py/{discord.__version__}"
        self.session: aiohttp.ClientSession = aiohttp.ClientSession(headers={"User-Agent": ua})

        intents: discord.Intents = discord.Intents.default()
        intents.members = True
        intents.message_content = True

        super().__init__(command_prefix=["d! ", "d!"], intents=intents, case_insensitive=True)

    async def setup_hook(self) -> None:
        await self.load_extension("jishaku")
        await self.load_extension("extensions")

    async def on_ready(self) -> None:
        logger.info("Logged in as: %s", self.user)

    async def close(self) -> None:
        await self.session.close()
        return await super().close()
