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

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Any, Literal, Self

import discord
import wavelink

from .enums import PlayerEmoji


if TYPE_CHECKING:
    from .bot import Bot


class ConfirmView(discord.ui.View):
    def __init__(self, *, timeout: float | None = 30) -> None:
        self.confirm: bool = False
        super().__init__(timeout=timeout)

    @discord.ui.button(label="Yes", style=discord.ButtonStyle.green)
    async def confirm_button(self, interaction: discord.Interaction[Bot], button: discord.ui.Button[Self]) -> None:
        self.stop()
        self.confirm = True

    @discord.ui.button(label="No", style=discord.ButtonStyle.red)
    async def deny_button(self, interaction: discord.Interaction[Bot], button: discord.ui.Button[Self]) -> None:
        self.stop()


class PlayerView(discord.ui.View):
    def __init__(self, *, timeout: float | None = None, player: Player) -> None:
        self.player: Player = player
        self.stopping: bool = False
        super().__init__(timeout=timeout)

    @discord.ui.button(emoji=PlayerEmoji.VOL_DOWN.value)
    async def vol_down(self, interaction: discord.Interaction[Bot], button: discord.ui.Button[Self]) -> None:
        await interaction.response.defer()

        if not self.player.can_command(interaction.user):  # type: ignore
            return

        vol: int = max(0, self.player.volume - 10)

        await self.player.set_volume(vol)
        self.player.next_payload = None

    @discord.ui.button(emoji=PlayerEmoji.SHUFFLE.value)
    async def shuffle(self, interaction: discord.Interaction[Bot], button: discord.ui.Button[Self]) -> None:
        await interaction.response.defer()

        if not self.player.can_command(interaction.user):  # type: ignore
            return

        self.player.queue.shuffle()
        self.player.auto_queue.shuffle()
        self.player.next_payload = None

    @discord.ui.button(emoji=PlayerEmoji.PAUSE.value)
    async def play_pause(self, interaction: discord.Interaction[Bot], button: discord.ui.Button[Self]) -> None:
        await interaction.response.defer()

        if not self.player.can_command(interaction.user):  # type: ignore
            return

        await self.player.pause(not self.player.paused)

        if self.player.paused:
            self.play_pause.emoji = PlayerEmoji.PLAY.value
        else:
            self.play_pause.emoji = PlayerEmoji.PAUSE.value

        self.player.next_payload = None

    @discord.ui.button(disabled=True, emoji=PlayerEmoji.REPLAY.value)
    async def replay(self, interaction: discord.Interaction[Bot], button: discord.ui.Button[Self]) -> None:
        await interaction.response.defer()

        if not self.player.can_command(interaction.user):  # type: ignore
            return

        if self.player.queue.mode is wavelink.QueueMode.normal:
            self.player.queue.mode = wavelink.QueueMode.loop_all

        elif self.player.queue.mode is wavelink.QueueMode.loop_all:
            self.player.queue.mode = wavelink.QueueMode.loop

        else:
            self.player.queue.mode = wavelink.QueueMode.normal

        self.player.next_payload = None

    @discord.ui.button(emoji=PlayerEmoji.VOL_UP.value)
    async def vol_up(self, interaction: discord.Interaction[Bot], button: discord.ui.Button[Self]) -> None:
        await interaction.response.defer()

        if not self.player.can_command(interaction.user):  # type: ignore
            return

        vol: int = min(100, self.player.volume + 10)

        await self.player.set_volume(vol)
        self.player.next_payload = None

    @discord.ui.button(disabled=True, label="\u200b")
    async def empty_one(self, interaction: discord.Interaction[Bot], button: discord.ui.Button[Self]) -> None:
        await interaction.response.defer()

    @discord.ui.button(disabled=True, emoji=PlayerEmoji.BACKWARD.value)
    async def empty_two(self, interaction: discord.Interaction[Bot], button: discord.ui.Button[Self]) -> None:
        assert self.player.guild
        await interaction.response.defer()

        if not self.player.current:
            return

        track: wavelink.Playable = self.player.current
        extras: dict[str, Any] = dict(track.extras)
        requester: discord.Member | None = self.player.guild.get_member(extras.get("requester_id", 0))

        if not self.player.can_command(interaction.user) and interaction.user != requester:  # type: ignore
            return

        if self.player.position >= 7000:
            await self.player.play(self.player.current, add_history=False)
            return

        assert self.player.queue.history

        try:
            old: wavelink.Playable = self.player.queue.history.get_at(-1)
        except (IndexError, wavelink.QueueEmpty):
            await self.player.play(self.player.current)
        else:
            await self.player.play(old)

    @discord.ui.button(emoji=PlayerEmoji.STOP.value)
    async def stop_button(self, interaction: discord.Interaction[Bot], button: discord.ui.Button[Self]) -> None:
        await interaction.response.defer(ephemeral=True)
        if self.stopping:
            return

        if not self.player.can_command(interaction.user):  # type: ignore
            return

        self.stopping = True

        confirm: ConfirmView = ConfirmView()
        msg: str = f"{interaction.user.mention} - Are you sure you would like to stop the player?"
        followup: discord.WebhookMessage = await interaction.followup.send(content=msg, view=confirm)  # type: ignore

        await confirm.wait()
        await followup.delete()
        self.stopping = False

        if not confirm.confirm:
            return

        await self.player.disconnect()

    @discord.ui.button(emoji=PlayerEmoji.FORWARD.value)
    async def empty_three(self, interaction: discord.Interaction[Bot], button: discord.ui.Button[Self]) -> None:
        assert self.player.guild
        await interaction.response.defer()

        if not self.player.current:
            return

        track: wavelink.Playable = self.player.current
        extras: dict[str, Any] = dict(track.extras)
        requester: discord.Member | None = self.player.guild.get_member(extras.get("requester_id", 0))

        if not self.player.can_command(interaction.user) and interaction.user != requester:  # type: ignore
            return

        await self.player.skip(force=True)

    @discord.ui.button(disabled=True, label="\u200b")
    async def empty_four(self, interaction: discord.Interaction[Bot], button: discord.ui.Button[Self]) -> None:
        await interaction.response.defer()


class Player(wavelink.Player):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        self.home: discord.TextChannel | discord.VoiceChannel = kwargs.pop("home")
        self.message: discord.Message | None = None
        self.view: PlayerView = PlayerView(player=self)
        self.dj: discord.Member | None = kwargs.pop("dj", None)

        self.updater_task: asyncio.Task[None] = asyncio.create_task(self.updater())
        self.next_payload: wavelink.Playable | None | Literal[False] = False

        super().__init__(*args, **kwargs)

    def can_command(self, member: discord.Member) -> bool:
        if member == self.dj:
            return True

        if self.home.permissions_for(member).manage_messages:
            return True

        if member not in self.channel.members:
            return False

        if len(self.channel.members) <= 2:
            return True

        return False

    def build_embed(self, track: wavelink.Playable | None | Literal[False] = None) -> discord.Embed:
        assert self.guild is not None

        embed: discord.Embed = discord.Embed(title="Now Playing", colour=0xB19CD9)
        thumb = "https://static.wikia.nocookie.net/dofus/images/0/08/Dance.png/revision/latest?cb=20150902094744"

        if track is False:
            embed.description = "`Not curerntly playing anything!`"
            embed.set_thumbnail(url=thumb)

        track = track or self.current
        if track:
            track = track or self.current
            extras: dict[str, Any] = dict(track.extras)
            recommended: bool = extras.get("recommended", False)

            embed.description = f"[{track}]({track.uri}) by `{track.author}`"
            embed.set_thumbnail(url=track.artwork or thumb)

            if recommended:
                embed.add_field(name="Requested By", value=f"`AutoPlay via {track.source}`")
            else:
                requester: discord.Member | None = self.guild.get_member(extras.get("requester_id", 0))
                embed.add_field(name="Requested By", value=requester.mention if requester else "Unknown")
        else:
            embed.description = "`Not curerntly playing anything!`"
            embed.set_thumbnail(url=thumb)

        embed.add_field(name="Queue", value=str(len(self.queue)))
        embed.add_field(name="Auto Queue", value=str(len(self.auto_queue)))

        repeat: str = (
            "Off"
            if self.queue.mode is wavelink.QueueMode.normal
            else "All Tracks"
            if self.queue.mode is wavelink.QueueMode.loop_all
            else "One Track"
        )
        autoplay: str = "Enabled" if self.autoplay is wavelink.AutoPlayMode.enabled else "Disabled"

        embed.add_field(name="AutoPlay", value=autoplay)
        embed.add_field(name="Repeat", value=repeat)
        embed.add_field(name="Volume", value=f"`{self.volume}%`")

        if not self.dj:
            embed.set_author(name="No DJ!")
        else:
            embed.set_author(name=f"{self.dj.display_name} (DJ)", icon_url=self.dj.display_avatar.url)

        return embed

    async def send_view(self, track: wavelink.Playable | None | Literal[False] = None) -> None:
        self.next_payload = False

        assert self.guild is not None
        embed: discord.Embed = self.build_embed(track=track)

        if not self.message or not self.home.permissions_for(self.guild.me).read_message_history:
            self.message = await self.home.send(view=self.view, embed=embed)
            return

        async for msg in self.home.history(limit=5):
            if msg.id == self.message.id:
                await msg.edit(view=self.view, embed=embed)
                return

        try:
            await self.message.delete()
        except discord.HTTPException:
            pass

        self.message = await self.home.send(view=self.view, embed=embed)

    async def disconnect(self, **kwargs: Any) -> None:
        if not self.message:
            return

        try:
            self.updater_task.cancel()
        except Exception:
            pass

        try:
            await self.message.delete()
        except discord.HTTPException:
            pass

        return await super().disconnect(**kwargs)

    async def updater(self) -> None:
        while True:
            if self.next_payload is not False:
                await self.send_view(self.next_payload)

            await asyncio.sleep(1)
