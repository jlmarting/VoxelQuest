"""Endpoint MCP JSON-RPC 2.0 para controlar el juego desde agentes."""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from server.engine.game_loop import GameLoop


class McpError(Exception):
    def __init__(self, code: int, message: str):
        self.code = code
        self.message = message
        super().__init__(message)


class McpServer:
    """Implementación mínima de MCP sobre JSON-RPC 2.0 por HTTP."""

    def __init__(self, game_loop: GameLoop):
        self.game_loop = game_loop

    def list_tools(self) -> list[dict]:
        tools_path = Path(__file__).resolve().parent.parent.parent.parent / 'shared' / 'tools' / 'definitions.json'
        try:
            with open(tools_path) as f:
                all_defs = json.load(f)
            return [
                {"name": name, "description": defn["description"], "inputSchema": defn["inputSchema"]}
                for name, defn in all_defs.get("tools", {}).items()
                if "python" in defn.get("servers", [])
            ]
        except (FileNotFoundError, json.JSONDecodeError):
            return []

    async def handle(self, request: dict) -> dict | None:
        if request.get("jsonrpc") != "2.0":
            return self._error(request.get("id"), -32600, "Invalid Request: jsonrpc must be 2.0")

        method = request.get("method")
        req_id = request.get("id")
        params = request.get("params", {})

        try:
            if method == "initialize":
                return self._result(
                    req_id,
                    {
                        "protocolVersion": "2024-11-05",
                        "capabilities": {"tools": {}},
                        "serverInfo": {"name": "VoxelQuest Python Server", "version": "0.1.0"},
                    },
                )
            elif method == "ping":
                return self._result(req_id, {})
            elif method == "tools/list":
                return self._result(req_id, {"tools": self.list_tools()})
            elif method == "tools/call":
                return await self._call_tool(req_id, params)
            elif method == "resources/list":
                return self._result(req_id, {"resources": []})
            elif method == "notifications/initialized":
                return None
            else:
                return self._error(req_id, -32601, f"Method not found: {method}")
        except McpError as e:
            return self._error(req_id, e.code, e.message)
        except Exception as e:
            return self._error(req_id, -32603, str(e))

    async def _call_tool(self, req_id: Any, params: dict) -> dict:
        name = params.get("name")
        args = params.get("arguments", {})
        if not name:
            raise McpError(-32602, "Tool name required")

        handler = getattr(self, f"tool_{name}", None)
        if handler is None:
            raise McpError(-32602, f"Unknown tool: {name}")

        result = await handler(args)
        return self._result(req_id, result)

    # ---- Tools ----

    async def tool_get_config(self, args: dict) -> dict:
        return {
            "players": len(self.game_loop.players),
            "tick_rate": self.game_loop.tick_rate,
            "seed": self.game_loop.world.seed,
        }

    async def tool_list_players(self, args: dict) -> dict:
        return {"players": [p.to_dict() for p in self.game_loop.players.values()]}

    async def tool_get_player_state(self, args: dict) -> dict:
        player_id = int(args.get("player_id", 0))
        player = self.game_loop.get_player(player_id)
        if player is None:
            raise McpError(-32602, f"Player {player_id} not found")
        return player.to_dict()

    async def tool_set_player_position(self, args: dict) -> dict:
        player_id = int(args.get("player_id", 0))
        player = self.game_loop.get_player(player_id)
        if player is None:
            raise McpError(-32602, f"Player {player_id} not found")
        player.position.x = float(args["x"])
        player.position.y = float(args.get("y", player.position.y))
        player.position.z = float(args["z"])
        player.velocity.x = 0.0
        player.velocity.z = 0.0
        player.velocity.y = 0.0
        player.on_ground = False
        return {"success": True, "position": player.position.to_dict(), "player_id": player_id}

    async def tool_place_block(self, args: dict) -> dict:
        x, y, z = int(args["x"]), int(args["y"]), int(args["z"])
        block_type = int(args["type"])
        self.game_loop.world.set_block(x, y, z, block_type)
        return {"success": True, "position": {"x": x, "y": y, "z": z}, "type": block_type}

    async def tool_fill_area(self, args: dict) -> dict:
        x = int(args["x"]); z = int(args["z"])
        width = int(args["width"]); depth = int(args["depth"])
        height = int(args.get("height", 1))
        base_y = int(args.get("baseY", 20))
        block_type = int(args.get("type", 0))
        count = 0
        for dx in range(width):
            for dz in range(depth):
                for dy in range(height):
                    wx, wy, wz = x + dx, base_y + dy, z + dz
                    self.game_loop.world.set_block(wx, wy, wz, block_type)
                    count += 1
        return {"success": True, "blocks_affected": count}

    async def tool_apply_blocks(self, args: dict) -> dict:
        """Aplica una lista de bloques en un solo request (construcciones/destrucciones)."""
        blocks = args.get("blocks") or args.get("block_updates") or []
        count = 0
        for b in blocks:
            self.game_loop.world.set_block(
                int(b["x"]), int(b["y"]), int(b["z"]), int(b.get("type", b.get("block_type", 0)))
            )
            count += 1
        return {"success": True, "blocks_affected": count, "blocks": count}

    async def tool_clear_area(self, args: dict) -> dict:
        """Borra (aire) un área de bloques en un solo request."""
        x = int(args["x"]); z = int(args["z"])
        width = int(args["width"]); depth = int(args["depth"])
        height = int(args.get("height", 64))
        base_y = int(args.get("baseY", 0))
        count = 0
        for dx in range(width):
            for dz in range(depth):
                for dy in range(height):
                    self.game_loop.world.set_block(x + dx, base_y + dy, z + dz, 0)
                    count += 1
        return {"success": True, "blocks_removed": count, "blocks": count}

    async def tool_break_block(self, args: dict) -> dict:
        from server.engine.constants import BlockType

        x, y, z = int(args["x"]), int(args["y"]), int(args["z"])
        block = self.game_loop.world.get_block(x, y, z)
        if block == BlockType.BEDROCK:
            raise McpError(-32602, "Cannot break bedrock")
        self.game_loop.world.set_block(x, y, z, BlockType.AIR)
        return {"success": True, "position": {"x": x, "y": y, "z": z}, "block_type": int(block)}

    async def tool_get_block(self, args: dict) -> dict:
        x, y, z = int(args["x"]), int(args["y"]), int(args["z"])
        block = self.game_loop.world.get_block(x, y, z)
        return {"x": x, "y": y, "z": z, "type": int(block)}

    async def tool_get_height(self, args: dict) -> dict:
        """Altura del terreno en (x,z): Y del primer bloque solido desde arriba.

        Devuelve la Y del bloque solido mas alto (no aire/agua) en la columna.
        Si la columna esta vacia, devuelve 0.
        """
        from server.engine.constants import BlockType, WORLD_HEIGHT

        x, z = int(args["x"]), int(args["z"])
        world = self.game_loop.world
        for y in range(WORLD_HEIGHT - 1, -1, -1):
            block = world.get_block(x, y, z)
            if block not in (BlockType.AIR, BlockType.WATER):
                return {"x": x, "z": z, "height": y, "surface": y + 1, "block_type": int(block)}
        return {"x": x, "z": z, "height": 0, "surface": 0, "block_type": 0}

    async def tool_gamepad_input(self, args: dict) -> dict:
        player_id = int(args.get("player_id", 0))
        player = self.game_loop.get_player(player_id)
        if player is None:
            raise McpError(-32602, f"Player {player_id} not found")

        inp = args.get("input", {})
        move = inp.get("move", {})
        look = inp.get("look", {})
        player.input_move.x = max(-1, min(1, float(move.get("x", 0))))
        player.input_move.z = max(-1, min(1, float(move.get("z", 0))))
        player.input_look.x = max(-1, min(1, float(look.get("x", 0))))
        player.input_look.y = max(-1, min(1, float(look.get("y", 0))))
        if "jump" in inp:
            player.input_jump = bool(inp["jump"])
        if "fly" in inp:
            player.input_fly = bool(inp["fly"])
        return {"success": True}

    async def tool_look(self, args: dict) -> dict:
        import math

        player_id = int(args.get("player_id", 0))
        player = self.game_loop.get_player(player_id)
        if player is None:
            raise McpError(-32602, f"Player {player_id} not found")
        if "yaw" in args:
            player.rotation.y = float(args["yaw"])
        if "pitch" in args:
            player.rotation.x = max(-math.pi / 2 + 0.1, min(math.pi / 2 - 0.1, float(args["pitch"])))
        return {"success": True, "rotation": player.rotation.to_dict()}

    async def tool_bt_load(self, args: dict) -> dict:
        from server.bt.engine import BehaviorTree, create_action_catalog

        tree_json = args.get("tree")
        if not tree_json:
            raise McpError(-32602, "tree required")
        catalog = create_action_catalog(self.game_loop)
        bt = BehaviorTree(tree_json, catalog, self.game_loop.blackboard)
        if bt.error:
            raise McpError(-32602, bt.error)
        self.game_loop.bt_engine = bt
        return {"success": True, "message": "Behavior tree loaded"}

    async def tool_bt_status(self, args: dict) -> dict:
        bt = self.game_loop.bt_engine
        return {
            "running": bt is not None,
            "error": bt.error if bt else None,
            "last_result": bt.last_result.value if bt and bt.last_result else None,
            "blackboard": self.game_loop.blackboard,
        }

    async def tool_bt_stop(self, args: dict) -> dict:
        self.game_loop.bt_engine = None
        return {"success": True, "message": "Behavior tree stopped"}

    # ---- Objects (propuesta 002) ----

    async def tool_create_object(self, args: dict) -> dict:
        from server.engine.objects import ObjectManager

        kwargs = dict(args)
        # position es lista → tupla; validar
        pos = kwargs.get("position")
        if pos is None:
            raise McpError(-32602, "position required")
        kwargs["position"] = tuple(pos)
        for k in ("velocity", "rotation", "angular_velocity", "scale"):
            if k in kwargs and kwargs[k] is not None:
                kwargs[k] = tuple(kwargs[k])
        try:
            obj = self.game_loop.object_manager.create(**kwargs)
        except ValueError as e:
            raise McpError(-32602, str(e))
        return {"success": True, "object_id": obj.id, "object": obj.to_dict()}

    async def tool_list_objects(self, args: dict) -> dict:
        flt = args.get("filter") or {}
        objs = self.game_loop.object_manager.list(flt)
        return {"objects": [o.to_dict() for o in objs]}

    async def tool_get_object(self, args: dict) -> dict:
        oid = int(args["object_id"])
        obj = self.game_loop.object_manager.get(oid)
        if obj is None:
            raise McpError(-32602, f"object {oid} not found")
        return {"object": obj.to_dict()}

    async def tool_update_object(self, args: dict) -> dict:
        oid = int(args["object_id"])
        obj = self.game_loop.object_manager.get(oid)
        if obj is None:
            raise McpError(-32602, f"object {oid} not found")
        patch = dict(args.get("patch", {}))
        for k in ("velocity", "rotation", "angular_velocity", "scale"):
            if k in patch and patch[k] is not None:
                patch[k] = tuple(patch[k])
        if "position" in patch and patch["position"] is not None:
            patch["position"] = tuple(patch["position"])
        obj = self.game_loop.object_manager.update(obj, patch)
        return {"success": True, "object": obj.to_dict()}

    async def tool_destroy_object(self, args: dict) -> dict:
        oid = int(args["object_id"])
        obj = self.game_loop.object_manager.get(oid)
        if obj is None:
            raise McpError(-32602, f"object {oid} not found")
        cause = args.get("cause", "manual")
        events = obj.destroy(cause, self.game_loop.world)
        self.game_loop.object_manager.objects.remove(obj)
        self.game_loop._pending_events.extend(events)
        return {"success": True, "object_id": oid, "events": events}

    async def tool_damage_object(self, args: dict) -> dict:
        """Aplica daño a un objeto destruible. Si health llega a 0, se destruye."""
        oid = int(args["object_id"])
        amount = float(args.get("amount", 0.0))
        source_id = args.get("source_id")
        obj = self.game_loop.object_manager.get(oid)
        if obj is None:
            raise McpError(-32602, f"object {oid} not found")
        if not obj.destructible:
            raise McpError(-32602, f"object {oid} is not destructible")
        obj.health -= amount
        events: list[dict] = []
        if obj.health <= 0:
            events = obj.destroy("damage", self.game_loop.world)
            self.game_loop.object_manager.objects.remove(obj)
        self.game_loop._pending_events.append({
            "type": "object_damaged",
            "id": oid,
            "amount": amount,
            "source_id": source_id,
            "health_remaining": max(0.0, obj.health),
        })
        self.game_loop._pending_events.extend(events)
        return {
            "success": True,
            "object_id": oid,
            "health": max(0.0, obj.health),
            "destroyed": len(events) > 0,
        }

    async def tool_move_object(self, args: dict) -> dict:
        """Asigna un motion a un objeto (waypoints/dynamic/orbit/parametric/rotate/stop)."""
        oid = int(args["object_id"])
        obj = self.game_loop.object_manager.get(oid)
        if obj is None:
            raise McpError(-32602, f"object {oid} not found")
        motion_data = args.get("motion")
        if not motion_data or not isinstance(motion_data, dict):
            raise McpError(-32602, "motion required (dict with type + fields)")
        try:
            obj.motion = self.game_loop.object_manager._build_motion(motion_data)
        except ValueError as e:
            raise McpError(-32602, str(e))
        # Si es 'stop', limpiar motion y velocidad
        if obj.motion.type == "stop":
            obj.set_velocity(0.0, 0.0, 0.0)
            obj.motion = None
            return {"success": True, "motion": None}
        # Para dynamic, aplicar velocity inicial desde el motion
        if obj.motion.type == "dynamic":
            obj.set_velocity(*obj.motion.velocity)
        return {"success": True, "motion": obj.motion.to_dict()}

    # --- Presets de movimiento (Fase 4) ---

    async def tool_move_linear(self, args: dict) -> dict:
        """Línea recta con velocidad constante. Wrapper de dynamic sin gravedad."""
        oid = int(args["object_id"])
        velocity = args.get("velocity", [0, 0, 0])
        loop = bool(args.get("loop", False))
        expire_at = args.get("expire_at")
        return await self.tool_move_object({
            "object_id": oid,
            "motion": {
                "type": "dynamic",
                "velocity": list(velocity),
                "gravity": False,
                "expire_at": expire_at,
            },
        })

    async def tool_move_orbit(self, args: dict) -> dict:
        """Órbita circular alrededor de un centro."""
        oid = int(args["object_id"])
        center = args.get("center", [0, 0, 0])
        radius = float(args.get("radius", 1.0))
        axis = args.get("axis", "y")
        angular_speed = float(args.get("angular_speed", 1.0))
        loop = bool(args.get("loop", True))
        return await self.tool_move_object({
            "object_id": oid,
            "motion": {
                "type": "orbit",
                "center": list(center),
                "radius": radius,
                "axis": axis,
                "angular_speed": angular_speed,
            },
        })

    async def tool_move_bounce(self, args: dict) -> dict:
        """Rebote entre dos puntos a/b. Se implementa como waypoints con loop."""
        oid = int(args["object_id"])
        a = list(args.get("a", [0, 0, 0]))
        b = list(args.get("b", [1, 0, 0]))
        speed = float(args.get("speed", 1.0))
        # easing se ignora en fase 1 (solo linear); aceptado para compat.
        return await self.tool_move_object({
            "object_id": oid,
            "motion": {
                "type": "waypoints",
                "points": [a, b],
                "speed": speed,
                "loop": True,
            },
        })

    async def tool_move_projectile(self, args: dict) -> dict:
        """Parábola con gravedad. Marca el objeto como projectile y destruible."""
        oid = int(args["object_id"])
        obj = self.game_loop.object_manager.get(oid)
        if obj is None:
            raise McpError(-32602, f"object {oid} not found")
        velocity = list(args.get("velocity", [0, 0, 0]))
        gravity = bool(args.get("gravity", True))
        expire_at = args.get("expire_at")
        damage_on_impact = float(args.get("damage_on_impact", 0.0))
        destroy_on_impact = bool(args.get("destroy_on_impact", True))
        # Promocionar a projectile si no lo era
        if obj.kind != "projectile":
            obj.kind = "projectile"
        obj.destructible = True
        obj.fragile = max(obj.fragile, 1.0)  # umbral mínimo para que colisiones lo rompan
        obj.damage_on_impact = damage_on_impact
        obj.destroy_on_impact = destroy_on_impact
        return await self.tool_move_object({
            "object_id": oid,
            "motion": {
                "type": "dynamic",
                "velocity": velocity,
                "gravity": gravity,
                "expire_at": expire_at,
            },
        })

    async def tool_move_rotate(self, args: dict) -> dict:
        """Rotación continua sin traslación."""
        oid = int(args["object_id"])
        angular_velocity = list(args.get("angular_velocity", [0, 1, 0]))
        loop = bool(args.get("loop", True))
        return await self.tool_move_object({
            "object_id": oid,
            "motion": {
                "type": "rotate",
                "angular_velocity": angular_velocity,
                "loop": loop,
            },
        })

    async def tool_stop_motion(self, args: dict) -> dict:
        """Detiene todo movimiento del objeto."""
        oid = int(args["object_id"])
        return await self.tool_move_object({"object_id": oid, "motion": {"type": "stop"}})

    async def tool_apply_impulse(self, args: dict) -> dict:
        """Aplica un impulso instantáneo a un objeto dinámico (mass > 0)."""
        oid = int(args["object_id"])
        obj = self.game_loop.object_manager.get(oid)
        if obj is None:
            raise McpError(-32602, f"object {oid} not found")
        if obj.is_static():
            raise McpError(-32602, f"object {oid} is static (mass=0 or anchored)")
        impulse = args.get("impulse", [0, 0, 0])
        # v += impulse / mass
        m = obj.mass if obj.mass > 0 else 1.0
        obj.add_velocity(impulse[0] / m, impulse[1] / m, impulse[2] / m)
        # Si tenía un motion cinemático, anularlo (pasa a dynamic)
        if obj.motion is not None and obj.motion.type in ("waypoints", "orbit", "parametric", "rotate"):
            obj.motion = None
        # point (relativo al centro) genera torque; fase 1: ignorar torque
        return {"success": True, "velocity": list(obj.velocity)}

    async def tool_attack_enemy(self, args: dict) -> dict:
        """Ataca a un enemigo por su id, aplicando daño. Devuelve si murió."""
        enemy_id = int(args.get("enemy_id", 0))
        amount = float(args.get("amount", 2.0))
        enemy = self.game_loop.enemy_manager.find_enemy_by_id(enemy_id)
        if enemy is None:
            raise McpError(-32602, f"enemy {enemy_id} not found")
        died = enemy.take_damage(amount)
        if died:
            # El EnemyManager lo elimina en su update; forzamos aquí
            if enemy in self.game_loop.enemy_manager.enemies:
                self.game_loop.enemy_manager.enemies.remove(enemy)
            self.game_loop._pending_events.append(
                {"type": "entity_died", "target": "enemy", "id": enemy_id}
            )
        return {
            "success": True,
            "enemy_id": enemy_id,
            "health": max(0.0, enemy.health),
            "died": died,
        }

    async def tool_spawn_enemy(self, args: dict) -> dict:
        """Crear un NPC/enemigo en una posición específica."""
        from server.engine.entities import Vec3
        
        enemy_type = args.get("type")
        if not enemy_type:
            raise McpError(-32602, "type required (ZOMBIE, SKELETON, CREEPER)")
        position = args.get("position")
        if not position or len(position) != 3:
            raise McpError(-32602, "position required as [x, y, z]")
        name = args.get("name")
        
        pos = Vec3(float(position[0]), float(position[1]), float(position[2]))
        
        try:
            enemy = self.game_loop.enemy_manager.spawn_enemy(enemy_type, pos, name)
        except ValueError as e:
            raise McpError(-32602, str(e))
        
        return {
            "success": True,
            "enemy_id": enemy.id,
            "enemy": enemy.to_dict()
        }

    async def tool_create_sculpture(self, args: dict) -> dict:
        """Wrapper de create_object para esculturas subvoxel.

        Dos modos:
          - voxels explícitos: lista de {x,y,z,color,size} (coordenadas locales).
          - generator: 'sphere' | 'cube' | 'pyramid' | 'helix' | 'cross' | 'humanoid_bust'
            con params. Genera los voxels automáticamente.
        """
        from server.engine.objects import generate_sculpture, validate_sculpture, VALID_GENERATORS

        position = args.get("position")
        if position is None:
            raise McpError(-32602, "position required")
        resolution = int(args.get("resolution", 4))
        generator = args.get("generator")
        params = args.get("params", {})

        if generator is not None:
            if generator not in VALID_GENERATORS:
                raise McpError(-32602, f"invalid generator: {generator!r}")
            try:
                voxels = generate_sculpture(generator, params, resolution)
            except ValueError as e:
                raise McpError(-32602, str(e))
        else:
            voxels = args.get("voxels", [])

        try:
            validate_sculpture(voxels, resolution)
        except ValueError as e:
            raise McpError(-32602, str(e))

        # Construir shape: guardamos los voxels completos (dicts con color/size)
        # para que get_object los devuelva al cliente. aabb() usa los coords.
        shape = {
            "type": "sculpture_voxels",
            "resolution": resolution,
            "voxels": voxels,  # lista de dicts {x,y,z,color,size}
        }
        # Determinar scale = AABB envolvente
        if voxels:
            xs = [v["x"] for v in voxels]
            ys = [v["y"] for v in voxels]
            zs = [v["z"] for v in voxels]
            min_size = 1.0 / resolution
            scale = (max(xs) - min(xs) + min_size, max(ys) - min(ys) + min_size,
                     max(zs) - min(zs) + min_size)
        else:
            scale = (1.0, 1.0, 1.0)

        color = int(args.get("color", 0xFF8800))
        anchored = bool(args.get("anchored", True))
        destructible = bool(args.get("destructible", False))
        mass = float(args.get("mass", 0.0 if anchored else 1.0))

        obj = self.game_loop.object_manager.create(
            kind="sculpture",
            position=tuple(position),
            scale=scale,
            shape=shape,
            color=color,
            mass=mass,
            anchored=anchored,
            destructible=destructible,
            owner_id=args.get("owner_id"),
        )
        return {
            "success": True,
            "object_id": obj.id,
            "voxel_count": len(voxels),
            "object": obj.to_dict(),
        }

    def _result(self, req_id: Any, result: Any) -> dict:
        return {"jsonrpc": "2.0", "id": req_id, "content": [{"type": "text", "text": json.dumps(result)}]}

    def _error(self, req_id: Any, code: int, message: str) -> dict:
        return {"jsonrpc": "2.0", "id": req_id, "error": {"code": code, "message": message}}


# evitar import circular de json usado en _result
import json
