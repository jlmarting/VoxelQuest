"""Bucle principal de simulación del juego."""

from __future__ import annotations

import asyncio
import time
from typing import Callable

from server.engine.constants import DT, TICK_RATE
from server.engine.entities import EnemyManager, Player, Vec3
from server.engine.objects import ObjectManager
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
        self.object_manager = ObjectManager(world)
        self.players: dict[int, Player] = {}
        self.on_state_update: Callable[[dict], None] | None = None

        # Ciclo día/noche simple
        self.day_time = 0.5  # 0.0 = amanecer, 0.5 = mediodía
        self.day_duration = 300.0  # segundos por ciclo completo

        # Blackboard para Behavior Trees
        self.blackboard: dict = {}
        self.bt_engine: Any = None
        self._pending_events: list[dict] = []

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

    def update_blackboard(self) -> None:
        """Actualiza blackboard con datos del jugador 2 (IA por defecto)."""
        p2 = self.players.get(2)
        p1 = self.players.get(1)
        self.blackboard.update(
            {
                "self_vida": p2.health if p2 else 20,
                "self_x": p2.position.x if p2 else 0,
                "self_y": p2.position.y if p2 else 0,
                "self_z": p2.position.z if p2 else 0,
                "self_rot_y": p2.rotation.y if p2 else 0,
                "p1_x": p1.position.x if p1 else 0,
                "p1_y": p1.position.y if p1 else 0,
                "p1_z": p1.position.z if p1 else 0,
                "hay_enemigos_cerca": False,
                "target_enemigo_id": None,
                "target_enemigo_x": None,
                "target_enemigo_z": None,
                "on_ground": p2.on_ground if p2 else True,
            }
        )
        if p2 and self.enemy_manager.enemies:
            nearest = None
            nearest_dist = float("inf")
            for enemy in self.enemy_manager.enemies:
                dist = ((enemy.position.x - p2.position.x) ** 2 + (enemy.position.z - p2.position.z) ** 2) ** 0.5
                if dist < nearest_dist:
                    nearest_dist = dist
                    nearest = enemy
            if nearest and nearest_dist < 20:
                self.blackboard["hay_enemigos_cerca"] = True
                self.blackboard["target_enemigo_id"] = nearest.id
                self.blackboard["target_enemigo_x"] = nearest.position.x
                self.blackboard["target_enemigo_z"] = nearest.position.z

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
        # El servidor es la fuente de verdad: integrar física (gravedad +
        # colisiones) de los enemigos para que sus posiciones sean reales.
        for enemy in self.enemy_manager.enemies:
            self.physics.update_entity(enemy, self.dt)

        # Actualizar bloques cayendo
        falling_events = self.physics.update_falling_blocks(self.dt)

        # Actualizar objetos móviles (motions + expiraciones; física en Fase 2)
        object_events = self.object_manager.update_motions(self.dt, now)

        # Física de objetos: integrar cada objeto y resolver colisiones obj↔obj
        for obj in self.object_manager.objects:
            self.physics.update_object(obj, self.dt)
        obj_collision_events = self.physics.resolve_object_collisions(
            self.object_manager.objects, self.dt
        )
        # Procesar daño/destrucción a partir de las colisiones
        all_entities = list(self.players.values()) + self.enemy_manager.enemies
        destruction_events = self.object_manager.check_destruction(
            obj_collision_events, all_entities
        )
        object_events.extend(obj_collision_events)
        object_events.extend(destruction_events)

        # Generar chunks alrededor de jugadores
        for player in self.players.values():
            self.world.update_around(player.position.x, player.position.z)

        # Behavior Tree
        self.update_blackboard()
        if self.bt_engine:
            self.bt_engine.tick()

        # Enviar estado a suscriptores
        if self.on_state_update:
            state = self._build_state()
            state["events"] = enemy_events + falling_events + object_events + self._pending_events
            self._pending_events = []
            state["block_updates"] = self.world.take_block_updates(500)
            self.on_state_update(state)

    def _build_state(self) -> dict:
        return {
            "type": "state_update",
            "tick": self.tick_count,
            "timestamp": time.time(),
            "players": {str(pid): p.to_dict() for pid, p in self.players.items()},
            "enemies": self.enemy_manager.get_enemies_state(),
            "objects": self.object_manager.get_state(),
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
            try:
                self.tick()
            except Exception as e:
                # Una excepción en un tick NO debe congelar la simulación en
                # silencio: se loguea y se continúa al siguiente tick.
                import logging
                logging.getLogger("game_loop").exception("Error en tick(): %s", e)
            elapsed = time.time() - loop_start
            sleep_time = max(0.0, interval - elapsed)
            await asyncio.sleep(sleep_time)

    def stop(self) -> None:
        self.running = False
