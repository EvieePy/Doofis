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

from typing import cast

import discord
import wavelink
from discord.ext import commands

import core


class Music(commands.Cog):
    def __init__(self, bot: core.Bot) -> None:
        self.bot: core.Bot = bot

    async def cog_load(self) -> None:
        uri: str = core.CONFIG["WAVELINK"]["host"]
        password: str = core.CONFIG["WAVELINK"]["password"]

        node: wavelink.Node = wavelink.Node(uri=uri, password=password)
        await wavelink.Pool.connect(nodes=[node], cache_capacity=200, client=self.bot)

    @commands.Cog.listener()
    async def on_wavelink_track_start(self, payload: wavelink.TrackStartEventPayload) -> None:
        vc: core.Player | None = cast(core.Player | None, payload.player)
        if not vc:
            return

        track: wavelink.Playable = payload.track
        if payload.original:
            track.extras.recommended = payload.original.recommended
            vc.current.extras.recommended = payload.original.recommended  # type: ignore

        await vc.send_view(track=track)

    @commands.Cog.listener()
    async def on_wavelink_inactive_player(self, player: core.Player) -> None:
        await player.disconnect()
        await player.home.send("Disconnecting due to inactivity. Bye!", delete_after=20)

    @commands.Cog.listener()
    async def on_voice_state_update(
        self,
        member: discord.Member,
        before: discord.VoiceState,
        after: discord.VoiceState,
    ) -> None:
        guild: discord.Guild = member.guild
        vc: core.Player | None = cast(core.Player | None, guild.voice_client)

        if not vc:
            return

        if member == guild.me:
            return

        channel: discord.VoiceChannel | None = vc.channel  # type: ignore
        if not channel:
            return

        members: list[discord.Member] = [m for m in channel.members if not m.bot]
        try:
            new: discord.Member = members[0]
        except IndexError:
            new = guild.me

        if before.channel == channel and after.channel != channel:
            if member != vc.dj:
                return

            vc.dj = new
            vc.next_payload = None
            return

        elif after.channel == channel and before.channel != channel:
            if vc.dj == guild.me:
                vc.dj = new
                vc.next_payload = None
                return

    async def connect(self, ctx: commands.Context[core.Bot]) -> core.Player:
        assert isinstance(ctx.author, discord.Member)

        if not ctx.author.voice or not ctx.author.voice.channel:
            raise ValueError("Please join a voice channel first!")

        player: core.Player = core.Player(home=ctx.channel, dj=ctx.author)
        vc: core.Player = await ctx.author.voice.channel.connect(cls=player)  # type: ignore

        vc.autoplay = wavelink.AutoPlayMode.enabled
        await vc.set_volume(50)

        return vc

    @commands.hybrid_command()
    @commands.guild_only()
    async def play(self, ctx: commands.Context[core.Bot], *, song: str) -> None:
        """Request a song to play via search, YouTube/Music, Spotify, SoundCloud or Twitch.

        Parameters
        ----------
        song: str
            A search or URL from YouTube, Spotify, SoundCloud or Twitch.
        """
        assert isinstance(ctx.author, discord.Member)
        await ctx.defer()

        try:
            await ctx.message.delete()
        except discord.HTTPException:
            pass

        if not ctx.voice_client:
            try:
                vc: core.Player = await self.connect(ctx)
            except Exception as e:
                await ctx.send(f"Could not connect: `{e}`")
                return
        else:
            vc: core.Player = cast(core.Player, ctx.voice_client)

        if not ctx.author.voice or ctx.author.voice.channel != vc.channel:
            await ctx.send(f"You must be in: {vc.channel.mention} to request a song.")
            return

        if ctx.channel != vc.home:
            await ctx.send(f"You must request songs in {vc.home.mention}!", delete_after=20)
            return

        try:
            search: wavelink.Search = await wavelink.Playable.search(song)
        except wavelink.LavalinkLoadException as e:
            await ctx.send(f"There was an error requesting this song: `{e}`. Please try again!")
            return

        if not search:
            await ctx.send(f"Could not find any songs with the query: `{song}`")
            return

        extras: wavelink.ExtrasNamespace = wavelink.ExtrasNamespace({"requester_id": ctx.author.id})

        if isinstance(search, wavelink.Playlist):
            search.extras = extras

            msg = f"Added the playlist: [{search.name}](<{search.url}>) with `{len(search.tracks)}` to the queue."
            await vc.queue.put_wait(search)
        else:
            track: wavelink.Playable = search[0]
            track.extras = extras

            msg = f"Added the song: [{track.title}](<{track.uri}>) to the queue."
            vc.queue.put(track)

        if not vc.playing:
            await vc.play(vc.queue.get(), populate=True)
        else:
            await vc.send_view()

        await ctx.send(f"{ctx.author.mention} {msg}", delete_after=30, silent=True)

    @commands.hybrid_command()
    @commands.guild_only()
    async def queue(self, ctx: commands.Context[core.Bot]) -> None:
        """View the upcoming songs."""
        await ctx.defer(ephemeral=True)
        assert ctx.guild

        vc: core.Player | None = cast(core.Player | None, ctx.voice_client)

        if not vc:
            await ctx.send("I am not currently playing anything!", ephemeral=True)
            return

        upcoming: list[wavelink.Playable] = vc.queue[:10] + vc.auto_queue[:10]
        upcoming = upcoming[:10]

        if not upcoming:
            await ctx.send("No upcoming songs yet!", ephemeral=True)
            return

        msg: str = ""
        for index, track in enumerate(upcoming, 1):
            if track.recommended:
                msg += f"{index}. [{track}](<{track.uri}>) - `AutoPlay via {track.source}`\n"
            else:
                requester: discord.Member | None = ctx.guild.get_member(track.extras.get("requester_id", 0))
                msg += f"{index}. [{track}](<{track.uri}>) - {requester.mention if requester else 'Unknown'}\n"

        await ctx.send(msg, ephemeral=True, silent=True)


async def setup(bot: core.Bot) -> None:
    await bot.add_cog(Music(bot))
