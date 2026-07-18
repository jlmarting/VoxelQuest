"""Bucle principal de simulación del juego."""

from __future__ import annotations

import asyncio
import time
from typing import Callable

from server.engine.constants import DT, TICK_RATE
from server.engine.entities import EnemyManager, Player, Vec3
from server.engine.physics import PhysicsSystem
from server.engine.world import World


class GameLoop:
    """Loop fijo de simulación del mundo."""

    def __init__(self, world: World, tick_rate: int = TICK_RATE):
        self.world = world
        self.tick_rate = tick_rate
        self.dt = 1.0 / tick_rate
        self.running = False
        self.tick_count = 0
        self.start_time = time.time()

        self.physics = PhysicsSystem(world)
        self.enemy_manager = EnemyManager(world)
        self.players: dict[int, Player] = {}
        self.on_state_update: Callable[[dict], None] | None = None

        # Ciclo día/noche simple
        self.day_time = 0.5  # 0.0 = amanecer, 0.5 = mediodía
        self.day_duration = 300.0  # segundos por ciclo completo

    @property
    def is_night(self) -> bool:
        return self.day_time < 0.2 or self.day_time > 0.8

    def add_player(self, player_id: int, name: str = "Jugador", is_ai: bool = False) -> Player:
        player = Player(id=player_id, name=name, is_ai=is_ai)
        spawn_x = 8 if player_id == 1 else 10
        spawn_z = 8
        self.world.update_around(float(spawn_x), float(spawn_z))
        player.position = Vec3(float(spawn_x) + 0.5, float(self.world.get_spawn_height(spawn_x, spawn_z)), float(spawn_z) + 0.5)
        self.players[player_id] = player
        return player

    def remove_player(self, player_id: int) -> None:
        self.players.pop(player_id, None)

    def get_player(self, player_id: int) -> Player | None:
        return self.players.get(player_id)

    def tick(self) -> None:
        now = time.time()
        self.tick_count += 1

        # Avanzar ciclo día/noche
        self.day_time = ((now - self.start_time) % self.day_duration) / self.day_duration

        # Aplicar input + física a jugadores
        for player in self.players.values():
            self.physics.apply_input(player, self.dt)
            self.physics.update_entity(player, self.dt)

        # Actualizar enemigos
        enemy_events = self.enemy_manager.update(self.dt, list(self.players.values()), now, self.is_night)

        # Actualizar bloques cayendo
        falling_events = self.physics.update_falling_blocks(self.dt)

        # Generar chunks alrededor de jugadores
        for player in self.players.values():
            self.world.update_around(player.position.x, player.position.z)

        # Enviar estado a suscriptores
        if self.on_state_update:
            state = self._build_state()
            state["events"] = enemy_events + falling_events
            self.on_state_update(state)

    def _build_state(self) -> dict:
        return {
            "type": "state_update",
            "tick": self.tick_count,
            "timestamp": time.time(),
            "players": {str(pid): p.to_dict() for pid, p in self.players.items()},
            "enemies": self.enemy_manager.get_enemies_state(),
            "chunk_deltas": self.world.get_deltas_since({}),
            "day_time": self.day_time,
            "is_night": self.is_night,
            "events": [],
        }

    async def run(self) -> None:
        self.running = True
        interval = self.dt
        while self.running:
            loop_start = time.time()
            self.tick()
            elapsed = time.time() - loop_start
            sleep_time = max(0.0, interval - elapsed)
            await asyncio.sleep(sleep_time)

    def stop(self) -> None:
        self.running = False
