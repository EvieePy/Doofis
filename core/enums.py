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

import enum


__all__ = ("PlayerEmoji",)


class PlayerEmoji(enum.Enum):
    REPLAY = "<:replay:1256553358341312532>"
    SHUFFLE = "<:shuffle:1256553359981150289>"
    FORWARD = "<:forward:1256553367929622579>"
    BACKWARD = "<:backward:1256553366167752704>"
    STOP = "<:stop:1256553361445228646>"
    PAUSE = "<:pause:1256553371075346432>"
    PLAY = "<:play:1256553369447698542>"
    VOL_DOWN = "<:vol_down:1256553486842335322>"
    VOL_UP = "<:vol_up:1256553364364333057>"
    OPTIONS = "<:options:1256553356575375412>"
