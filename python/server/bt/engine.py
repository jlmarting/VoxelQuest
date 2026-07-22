"""Motor de Behavior Trees para VoxelQuest Python."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable


class NodeStatus(str, Enum):
    SUCCESS = "SUCCESS"
    FAILURE = "FAILURE"
    RUNNING = "RUNNING"


ActionFn = Callable[[dict, "BehaviorTree"], NodeStatus]


@dataclass
class BTNode:
    type: str
    config: dict
    tree: "BehaviorTree"
    children: list["BTNode"] = field(default_factory=list)
    last_running_child: int | None = None

    def tick(self) -> NodeStatus:
        if self.type == "Selector":
            return self._tick_selector()
        if self.type == "Secuencia":
            return self._tick_sequence()
        if self.type == "Condicion":
            return self._tick_condition()
        if self.type == "Accion":
            return self._tick_action()
        return NodeStatus.FAILURE

    def _tick_selector(self) -> NodeStatus:
        start = self.last_running_child or 0
        self.last_running_child = None
        for i in range(start, len(self.children)):
            result = self.children[i].tick()
            if result == NodeStatus.RUNNING:
                self.last_running_child = i
                return NodeStatus.RUNNING
            if result == NodeStatus.SUCCESS:
                return NodeStatus.SUCCESS
        return NodeStatus.FAILURE

    def _tick_sequence(self) -> NodeStatus:
        start = self.last_running_child or 0
        self.last_running_child = None
        for i in range(start, len(self.children)):
            result = self.children[i].tick()
            if result == NodeStatus.RUNNING:
                self.last_running_child = i
                return NodeStatus.RUNNING
            if result == NodeStatus.FAILURE:
                return NodeStatus.FAILURE
        return NodeStatus.SUCCESS

    def _tick_condition(self) -> NodeStatus:
        value = self.tree.resolve_value(self.config.get("variable"))
        compare = self.tree.resolve_value(self.config.get("valor_comparar"))
        op = self.config.get("comparacion")

        if op == "menor_que":
            return NodeStatus.SUCCESS if value < compare else NodeStatus.FAILURE
        if op == "mayor_que":
            return NodeStatus.SUCCESS if value > compare else NodeStatus.FAILURE
        if op == "igual_a":
            return NodeStatus.SUCCESS if value == compare else NodeStatus.FAILURE
        if op == "verdadero":
            return NodeStatus.SUCCESS if value is True else NodeStatus.FAILURE
        if op == "falso":
            return NodeStatus.SUCCESS if value is False else NodeStatus.FAILURE
        return NodeStatus.FAILURE

    def _tick_action(self) -> NodeStatus:
        action_type = self.config.get("tipo")
        action_fn = self.tree.catalog.get(action_type)
        if action_fn is None:
            return NodeStatus.FAILURE

        params = self.tree.resolve_params(self.config.get("parametros", {}))
        return action_fn(params, self.tree)


class BehaviorTree:
    """Árbol de comportamiento reactivo."""

    def __init__(self, json_tree: dict, catalog: dict[str, ActionFn], blackboard: dict | None = None):
        self.catalog = catalog
        self.blackboard = blackboard or {}
        self.running_action: str | None = None
        self.last_result: NodeStatus | None = None
        self.error: str | None = None

        error = self._validate(json_tree)
        if error:
            self.error = error
            self.root = None
        else:
            self.root = self._build(json_tree)

    def _validate(self, node: dict, depth: int = 0) -> str | None:
        if depth > 50:
            return "Tree depth exceeds 50"
        if not isinstance(node, dict):
            return "Node must be an object"
        node_type = node.get("comportamiento")
        if node_type not in ("Selector", "Secuencia", "Accion", "Condicion"):
            return f"Invalid comportamiento: {node_type}"

        if node_type == "Condicion" and not node.get("variable"):
            return "Condicion missing variable"

        if node_type == "Accion":
            action_type = node.get("tipo")
            if not action_type:
                return "Accion missing tipo"
            if action_type not in self.catalog:
                return f"Unknown action tipo: {action_type}"

        if node_type in ("Selector", "Secuencia"):
            hijos = node.get("hijos")
            if not isinstance(hijos, list) or len(hijos) == 0:
                return f"{node_type} must have at least one hijo"
            for child in hijos:
                err = self._validate(child, depth + 1)
                if err:
                    return err
        return None

    def _build(self, node: dict) -> BTNode:
        children = []
        if node["comportamiento"] in ("Selector", "Secuencia"):
            children = [self._build(c) for c in node.get("hijos", [])]
        return BTNode(type=node["comportamiento"], config=node, tree=self, children=children)

    def tick(self) -> NodeStatus:
        if self.error or self.root is None:
            return NodeStatus.FAILURE
        self.last_result = self.root.tick()
        return self.last_result

    def resolve_params(self, params: dict | None) -> dict:
        if params is None:
            return {}
        resolved = {}
        for key, value in params.items():
            if isinstance(value, str) and value in self.blackboard:
                resolved[key] = self.blackboard[value]
            else:
                resolved[key] = value
        return resolved

    def resolve_value(self, variable: Any) -> Any:
        if isinstance(variable, str) and variable in self.blackboard:
            return self.blackboard[variable]
        return variable


def create_action_catalog(game_loop: "GameLoop") -> dict[str, ActionFn]:
    """Crea el catálogo de acciones del BT contra el estado del servidor."""
    import math

    from server.engine.constants import BlockType
    from server.engine.entities import Vec3
    from server.engine.navigation import Pathfinder

    pathfinder = Pathfinder(game_loop.world)
    active_paths: dict[int, list[dict]] = {}

    def gamepad_input(params: dict, tree: BehaviorTree) -> NodeStatus:
        player_id = int(params.get("player_id", 2))
        player = game_loop.get_player(player_id)
        if player is None:
            return NodeStatus.FAILURE
        inp = params.get("input", {})
        move = inp.get("move", {})
        look = inp.get("look", {})
        player.input_move.x = max(-1, min(1, float(move.get("x", 0))))
        player.input_move.z = max(-1, min(1, float(move.get("z", 0))))
        player.input_look.x = max(-1, min(1, float(look.get("x", 0)))) * 3
        player.input_look.y = max(-1, min(1, float(look.get("y", 0)))) * 3
        if "jump" in inp:
            player.input_jump = bool(inp["jump"])
        if "fly" in inp:
            player.input_fly = bool(inp["fly"])
        return NodeStatus.SUCCESS

    def moverse_a(params: dict, tree: BehaviorTree) -> NodeStatus:
        player_id = int(params.get("player_id", 2))
        player = game_loop.get_player(player_id)
        if player is None:
            return NodeStatus.FAILURE
        target_x = float(params.get("x", player.position.x))
        target_z = float(params.get("z", player.position.z))
        dx = player.position.x - target_x
        dz = player.position.z - target_z
        if math.hypot(dx, dz) < 1.0:
            active_paths.pop(player_id, None)
            return NodeStatus.SUCCESS

        if player_id not in active_paths:
            path = pathfinder.find_path(player.position.x, player.position.z, target_x, target_z, player.position.y)
            if not path or len(path) < 2:
                return NodeStatus.FAILURE
            active_paths[player_id] = path

        path = active_paths[player_id]
        if not path:
            return NodeStatus.SUCCESS

        next_node = path[0]
        ndx = next_node["x"] + 0.5 - player.position.x
        ndz = next_node["z"] + 0.5 - player.position.z
        dist = math.hypot(ndx, ndz)
        if dist < 0.4:
            path.pop(0)
            if not path:
                return NodeStatus.SUCCESS
            return NodeStatus.RUNNING

        desired_yaw = math.atan2(-ndx, -ndz)
        yaw_diff = desired_yaw - player.rotation.y
        while yaw_diff > math.pi:
            yaw_diff -= 2 * math.pi
        while yaw_diff < -math.pi:
            yaw_diff += 2 * math.pi

        player.input_move = Vec3(0, 0, -1)
        player.input_look = Vec3(max(-1, min(1, yaw_diff * 2)), 0)
        if next_node.get("jump"):
            player.input_jump = True
        return NodeStatus.RUNNING

    def golpear(params: dict, tree: BehaviorTree) -> NodeStatus:
        player_id = int(params.get("player_id", 2))
        player = game_loop.get_player(player_id)
        if player is None:
            return NodeStatus.FAILURE
        target_id = params.get("target_id")
        enemy = None
        if target_id is not None:
            enemy = game_loop.enemy_manager.find_enemy_by_id(int(target_id))
        else:
            direction = player.get_forward_direction()
            enemy = game_loop.enemy_manager.find_nearest_in_cone(
                player.position, direction, max_dist=3.0, cone_dot=0.707
            )
        if enemy is None:
            return NodeStatus.FAILURE
        dead = enemy.take_damage(4, player.position)
        if dead:
            events = game_loop.enemy_manager.update(0, list(game_loop.players.values()), 0, game_loop.is_night)
            game_loop._pending_events.extend(events)
        return NodeStatus.SUCCESS

    def equipar(params: dict, tree: BehaviorTree) -> NodeStatus:
        player_id = int(params.get("player_id", 2))
        player = game_loop.get_player(player_id)
        if player is None:
            return NodeStatus.FAILURE
        player.selected_slot = max(0, min(8, int(params.get("slot", 0))))
        return NodeStatus.SUCCESS

    def idle(params: dict, tree: BehaviorTree) -> NodeStatus:
        return NodeStatus.SUCCESS

    def mirar_a(params: dict, tree: BehaviorTree) -> NodeStatus:
        player_id = int(params.get("player_id", 2))
        player = game_loop.get_player(player_id)
        if player is None:
            return NodeStatus.FAILURE
        target_x = tree.resolve_value(params.get("x"))
        target_z = tree.resolve_value(params.get("z"))
        if target_x is None or target_z is None:
            return NodeStatus.FAILURE
        dx = target_x - player.position.x
        dz = target_z - player.position.z
        desired_yaw = math.atan2(-dx, -dz)
        diff = desired_yaw - player.rotation.y
        while diff > math.pi:
            diff -= 2 * math.pi
        while diff < -math.pi:
            diff += 2 * math.pi
        player.input_look.x = max(-1, min(1, diff * 2))
        return NodeStatus.SUCCESS if abs(diff) < 0.05 else NodeStatus.RUNNING

    def huir(params: dict, tree: BehaviorTree) -> NodeStatus:
        player_id = int(params.get("player_id", 2))
        player = game_loop.get_player(player_id)
        if player is None:
            return NodeStatus.FAILURE
        target_x = tree.blackboard.get("target_enemigo_x")
        target_z = tree.blackboard.get("target_enemigo_z")
        if target_x is None or target_z is None:
            return NodeStatus.FAILURE
        dx = player.position.x - target_x
        dz = player.position.z - target_z
        dist = math.hypot(dx, dz)
        if dist < 0.1:
            return NodeStatus.FAILURE
        speed = float(params.get("velocidad", -1))
        player.input_move.x = (dx / dist) * speed
        player.input_move.z = (dz / dist) * speed
        return NodeStatus.SUCCESS

    return {
        "gamepad_input": gamepad_input,
        "moverse_a": moverse_a,
        "golpear": golpear,
        "equipar": equipar,
        "idle": idle,
        "mirar_a": mirar_a,
        "huir": huir,
    }


# imports tardíos para evitar ciclos
from server.engine.game_loop import GameLoop
