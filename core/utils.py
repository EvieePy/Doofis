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

from types_.portals import SERVER_T


__all__ = ("SERVERS", "ServerIter")


SERVERS: list[SERVER_T] = ["Tal Kasha", "Draconiros", "Hell Mina"]


class ServerIter:
    def __init__(self) -> None:
        self.data: list[SERVER_T] = SERVERS
        self.index: int = -1
        self.max: int = len(self.data)

    def __len__(self) -> int:
        return len(self.data)

    def __next__(self) -> SERVER_T:
        self.index += 1
        if self.index + 1 > self.max:
            self.index = 0

        return self.data[self.index]
