"""Sistema de física para entidades y colapso de bloques."""

from __future__ import annotations

import math
from typing import TYPE_CHECKING

from server.engine.constants import (
    BlockType,
    WORLD_HEIGHT,
    DT,
    OBJECT_GRAVITY,
    OBJECT_LINEAR_DAMPING,
    PLAYER_HEIGHT,
    PLAYER_WIDTH,
)
from server.engine.entities import Entity, Player, Vec3
from server.engine.objects import MobileObject

if TYPE_CHECKING:
    from server.engine.world import World


class PhysicsSystem:
    """Aplica movimiento con colisiones AABB sobre el voxel grid."""

    def __init__(self, world: World):
        self.world = world
        self.falling_blocks: list[dict] = []

    def update_entity(self, entity: Entity, dt: float) -> None:
        """Aplica velocidad, gravedad y colisiones a una entidad."""
        if entity.is_flying:
            entity.velocity.y = 0.0
        else:
            entity.velocity.y += -20.0 * dt

        new_pos = entity.position.clone()

        # Eje X
        new_pos.x += entity.velocity.x * dt
        if self._check_collision(new_pos, entity):
            new_pos.x = entity.position.x
            entity.velocity.x = 0.0

        # Eje Z
        new_pos.z += entity.velocity.z * dt
        if self._check_collision(new_pos, entity):
            new_pos.z = entity.position.z
            entity.velocity.z = 0.0

        # Eje Y
        new_pos.y += entity.velocity.y * dt
        if self._check_collision(new_pos, entity):
            if entity.velocity.y < 0:
                entity.on_ground = True
                if entity.is_flying:
                    entity.is_flying = False
            new_pos.y = entity.position.y
            entity.velocity.y = 0.0
        else:
            entity.on_ground = False

        entity.position = new_pos
        entity.position.y = max(1.0, min(float(WORLD_HEIGHT - 2), entity.position.y))

    def _check_collision(self, pos: Vec3, entity: Entity) -> bool:
        radius = entity.width / 2
        height = entity.height

        for dx in (-1, 0, 1):
            for dz in (-1, 0, 1):
                for dy in (0, 1):
                    bx = int(pos.x + dx * radius)
                    by = int(pos.y + dy * height)
                    bz = int(pos.z + dz * radius)
                    block = self.world.get_block(bx, by, bz)
                    if block not in (BlockType.AIR, BlockType.WATER):
                        return True
        return False

    def apply_input(self, player: Player, dt: float) -> None:
        """Convierte input del jugador en velocidad y rotación."""
        # Rotación
        player.rotation.y -= player.input_look.x * 0.05
        player.rotation.x -= player.input_look.y * 0.05
        player.rotation.x = max(-math.pi / 2 + 0.1, min(math.pi / 2 - 0.1, player.rotation.x))

        # Movimiento relativo a la cámara
        yaw = player.rotation.y
        forward = Vec3(-math.sin(yaw), 0.0, -math.cos(yaw))
        right = Vec3(math.cos(yaw), 0.0, -math.sin(yaw))

        move = Vec3()
        move.x += forward.x * -player.input_move.z
        move.z += forward.z * -player.input_move.z
        move.x += right.x * player.input_move.x
        move.z += right.z * player.input_move.x

        length = math.hypot(move.x, move.z)
        if length > 0.001:
            move.x /= length
            move.z /= length
            player.velocity.x = move.x * player.speed
            player.velocity.z = move.z * player.speed
        else:
            player.velocity.x = 0.0
            player.velocity.z = 0.0

        # Salto / vuelo
        if player.is_flying:
            if player.input_jump:
                player.velocity.y = player.speed
        else:
            if player.input_jump and player.on_ground:
                player.velocity.y = 8.0
                player.on_ground = False

    def on_block_broken(self, x: int, y: int, z: int) -> None:
        """Inicia cadena de colapso de bloques flotantes."""
        self._check_unsupported(x, y + 1, z)

    def _check_unsupported(self, x: int, y: int, z: int) -> None:
        if y < 1 or y >= WORLD_HEIGHT:
            return
        block = self.world.get_block(x, y, z)
        if block in (BlockType.AIR, BlockType.WATER):
            return
        below = self.world.get_block(x, y - 1, z)
        if below not in (BlockType.AIR, BlockType.WATER):
            return
        self.world.set_block(x, y, z, BlockType.AIR)
        self.falling_blocks.append({"x": x + 0.5, "y": y + 0.5, "z": z + 0.5, "type": int(block), "vel_y": 0.0})
        self._check_unsupported(x, y + 1, z)

    def update_falling_blocks(self, dt: float) -> list[dict]:
        """Actualiza bloques cayendo y devuelve eventos de colocación."""
        events: list[dict] = []
        dt = min(dt, 0.05)
        for i in range(len(self.falling_blocks) - 1, -1, -1):
            fb = self.falling_blocks[i]
            fb["vel_y"] -= 14.0 * dt
            fb["y"] += fb["vel_y"] * dt

            ground_y = self._get_ground_height(int(fb["x"] - 0.5), int(fb["z"] - 0.5))
            if fb["y"] - 0.45 <= ground_y + 0.5:
                bx, by, bz = int(fb["x"]), int(fb["y"] - 0.45), int(fb["z"])
                if 0 <= by < WORLD_HEIGHT and self.world.get_block(bx, by, bz) == BlockType.AIR:
                    self.world.set_block(bx, by, bz, fb["type"])
                    events.append({"type": "block_placed", "x": bx, "y": by, "z": bz, "block_type": fb["type"]})
                self.falling_blocks.pop(i)
            elif fb["y"] < -10:
                self.falling_blocks.pop(i)
        return events

    def _get_ground_height(self, x: int, z: int) -> int:
        for y in range(WORLD_HEIGHT - 1, -1, -1):
            block = self.world.get_block(x, y, z)
            if block not in (BlockType.AIR, BlockType.WATER):
                return y
        return 0

    # ====================================================================
    # Física de objetos móviles (propuesta 002, Fase 2)
    # ====================================================================

    def update_object(self, obj: MobileObject, dt: float) -> None:
        """Integra un objeto: aplica gravedad si procede y resuelve colisión
        contra el voxel grid por ejes (generalización de update_entity a
        tamaño arbitrario). Solo objetos dinámicos (no estáticos).

        Los objetos con motion cinemático (waypoints/orbit/parametric/rotate)
        no se integran aquí: su posición la fija el motion en ObjectManager.
        Solo 'dynamic' y los que no tienen motion caen por gravedad.
        """
        if obj.is_static():
            return
        # Los motions cinemáticos gestionan su posición fuera de la física
        if obj.motion is not None and obj.motion.type in ("waypoints", "orbit", "parametric", "rotate"):
            return

        # Gravedad: el motion 'dynamic' puede traer gravity=True; si no hay
        # motion y el objeto no está anclado, también aplica gravedad para
        # que las cajas caigan por defecto.
        apply_gravity = True
        if obj.motion is not None:
            apply_gravity = obj.motion.type == "dynamic" and obj.motion.gravity
        if apply_gravity and not obj.anchored:
            vx, vy, vz = obj.velocity
            obj.set_velocity(vx, vy + OBJECT_GRAVITY * dt, vz)

        # Damping lineal: solo X/Z mientras hay gravedad activa (no contrarrestar
        # la caída). Con el objeto en reposo sobre el suelo también amortigua Y
        # para evitar micro-rebotes.
        if not obj.anchored:
            damp = 1.0 - OBJECT_LINEAR_DAMPING
            vx, vy, vz = obj.velocity
            if apply_gravity:
                obj.set_velocity(vx * damp, vy, vz * damp)
            else:
                obj.set_velocity(vx * damp, vy * damp, vz * damp)

        # Substepping para evitar tunneling: el desplazamiento por substep
        # no debe superar la mitad del tamaño del objeto.
        speed = obj.speed()
        min_scale = min(obj.scale) if min(obj.scale) > 0 else 0.5
        max_step = min_scale * 0.5
        steps = max(1, int(math.ceil(speed * dt / max(max_step, 1e-3))))
        steps = min(steps, 16)  # cap para no degradar perf
        sub_dt = dt / steps

        for _ in range(steps):
            self._step_object_axis(obj, sub_dt)

    def _step_object_axis(self, obj: MobileObject, dt: float) -> None:
        """Mueve el objeto por ejes, detectando colisión contra voxel grid."""
        # Eje X
        nx = obj.position[0] + obj.velocity[0] * dt
        if self._object_collides_grid(obj, (nx, obj.position[1], obj.position[2])):
            obj.set_velocity(0.0, obj.velocity[1], obj.velocity[2])
        else:
            obj.position = (nx, obj.position[1], obj.position[2])

        # Eje Z
        nz = obj.position[2] + obj.velocity[2] * dt
        if self._object_collides_grid(obj, (obj.position[0], obj.position[1], nz)):
            obj.set_velocity(obj.velocity[0], obj.velocity[1], 0.0)
        else:
            obj.position = (obj.position[0], obj.position[1], nz)

        # Eje Y
        ny = obj.position[1] + obj.velocity[1] * dt
        if self._object_collides_grid(obj, (obj.position[0], ny, obj.position[2])):
            if obj.velocity[1] < 0:
                # Reposar sobre el bloque: ajustar Y para que el AABB inferior
                # coincida con el techo del bloque sólido.
                top = self._block_top_under(obj, test_y=ny)
                if top is not None:
                    half_y = obj.scale[1] * 0.5 if obj.kind != "sphere" else obj.shape.get("radius", obj.scale[0] * 0.5)
                    obj.position = (obj.position[0], top + half_y, obj.position[2])
            obj.set_velocity(obj.velocity[0], 0.0, obj.velocity[2])
        else:
            obj.position = (obj.position[0], ny, obj.position[2])

    def _object_collides_grid(self, obj: MobileObject, pos: tuple[float, float, float]) -> bool:
        """Test AABB del objeto contra voxel grid en la posición dada."""
        mn, mx = obj.aabb()
        # Traslada el AABB a la posición de prueba
        dx = pos[0] - obj.position[0]
        dy = pos[1] - obj.position[1]
        dz = pos[2] - obj.position[2]
        mn = (mn[0] + dx, mn[1] + dy, mn[2] + dz)
        mx = (mx[0] + dx, mx[1] + dy, mx[2] + dz)

        x0 = int(math.floor(mn[0]))
        x1 = int(math.floor(mx[0]))
        y0 = int(math.floor(mn[1]))
        y1 = int(math.floor(mx[1]))
        z0 = int(math.floor(mn[2]))
        z1 = int(math.floor(mx[2]))
        for bx in range(x0, x1 + 1):
            for by in range(y0, y1 + 1):
                for bz in range(z0, z1 + 1):
                    if by < 0:
                        continue
                    if by >= WORLD_HEIGHT:
                        return True
                    block = self.world.get_block(bx, by, bz)
                    if block not in (BlockType.AIR, BlockType.WATER):
                        return True
        return False

    def _block_top_under(self, obj: MobileObject, test_y: float | None = None) -> float | None:
        """Devuelve la Y del techo del bloque sólido más alto bajo el objeto.

        Busca en toda la columna desde y=0 hasta justo bajo el AABB inferior.
        Así funciona incluso si el objeto cae rápido y atraviesa varias celdas
        en un substep.

        `test_y` permite evaluar el AABB en la posición Y de prueba (la Y
        propuesta del substep) en lugar de la Y actual del objeto. Sin esto,
        un objeto que cae rápido puede posarse a la Y del frame anterior o
        atravesar el suelo (tunneling).
        """
        mn, mx = obj.aabb()
        # Trasladar el AABB en Y a la posición de prueba
        dy = test_y - obj.position[1] if test_y is not None else 0.0
        mn_y = mn[1] + dy
        mx_y = mx[1] + dy
        x0 = int(math.floor(mn[0]))
        x1 = int(math.floor(mx[0]))
        z0 = int(math.floor(mn[2]))
        z1 = int(math.floor(mx[2]))
        y_below = int(math.floor(mn_y))
        if y_below < 0:
            # El AABB ya está por debajo de y=0 → reposar en el suelo del mundo
            return 0.0
        # Buscar el bloque sólido más alto desde y=0 hasta el bloque que el AABB
        # ya está penetrando (y_below). Incluir el bloque penetrado es clave:
        # si el AABB inferior (mn_y) cae dentro de una celda sólida, ese bloque
        # es el techo sobre el que debe reposar.
        top_y = -1.0
        for bx in range(x0, x1 + 1):
            for bz in range(z0, z1 + 1):
                for by in range(y_below, -1, -1):
                    block = self.world.get_block(bx, by, bz)
                    if block not in (BlockType.AIR, BlockType.WATER):
                        top_y = max(top_y, float(by + 1))
                        break  # encontrado el más alto en esta columna
        return top_y if top_y >= 0 else None

    # --- Colisión obj↔obj -------------------------------------------------

    def resolve_object_collisions(self, objects: list[MobileObject], dt: float) -> list[dict]:
        """Resuelve colisiones entre objetos. Devuelve eventos object_collided."""
        events: list[dict] = []
        # Solo considerar objetos vivos y visibles
        dyn = [o for o in objects if o.alive]
        if len(dyn) < 2:
            return events

        # Broad phase: grid espacial uniforme (celda = 2 voxels)
        cell_size = 2.0
        grid: dict[tuple[int, int, int], list[int]] = {}
        for i, o in enumerate(dyn):
            mn, mx = o.aabb()
            cx0 = int(mn[0] // cell_size)
            cx1 = int(mx[0] // cell_size)
            cz0 = int(mn[2] // cell_size)
            cz1 = int(mx[2] // cell_size)
            cy0 = int(mn[1] // cell_size)
            cy1 = int(mx[1] // cell_size)
            for cx in range(cx0, cx1 + 1):
                for cz in range(cz0, cz1 + 1):
                    for cy in range(cy0, cy1 + 1):
                        grid.setdefault((cx, cy, cz), []).append(i)

        seen: set[tuple[int, int]] = set()
        for _, idxs in grid.items():
            if len(idxs) < 2:
                continue
            for a_pos in range(len(idxs)):
                for b_pos in range(a_pos + 1, len(idxs)):
                    ia, ib = idxs[a_pos], idxs[b_pos]
                    key = (min(ia, ib), max(ia, ib))
                    if key in seen:
                        continue
                    seen.add(key)
                    a, b = dyn[ia], dyn[ib]
                    # Filtrar por collision_mask/group: colisionan solo si
                    # cada objeto incluye al grupo del otro en su mask.
                    if not (a.collision_mask & b.collision_group) or not (b.collision_mask & a.collision_group):
                        continue
                    result = self._narrow_phase(a, b)
                    if result is None:
                        continue
                    normal, depth = result
                    impact_speed = self._relative_speed_along(a, b, normal)
                    self._resolve_collision(a, b, normal, depth)
                    events.append({
                        "type": "object_collided",
                        "id": a.id,
                        "other": {"kind": b.kind, "id": b.id},
                        "normal": list(normal),
                        "depth": depth,
                        "impact_speed": abs(impact_speed),
                    })
        return events

    @staticmethod
    def _relative_speed_along(a: MobileObject, b: MobileObject, normal: tuple[float, float, float]) -> float:
        rvx = b.velocity[0] - a.velocity[0]
        rvy = b.velocity[1] - a.velocity[1]
        rvz = b.velocity[2] - a.velocity[2]
        return rvx * normal[0] + rvy * normal[1] + rvz * normal[2]

    def _narrow_phase(self, a: MobileObject, b: MobileObject) -> tuple[tuple[float, float, float], float] | None:
        """Narrow phase: devuelve (normal, depth) o None si no colisionan.

        Soporta box↔box (AABB), sphere↔sphere, sphere↔box (clamp).
        Esculturas usan AABB envolvente en fase 1.
        """
        kinds = (a.kind, b.kind)
        # Tratar sculpture/vehicle/projectile como box para narrow-phase si no son esfera
        a_is_sphere = a.kind == "sphere" or (a.shape.get("type") == "sphere")
        b_is_sphere = b.kind == "sphere" or (b.shape.get("type") == "sphere")
        if a_is_sphere and b_is_sphere:
            return self._sphere_sphere(a, b)
        if a_is_sphere != b_is_sphere:
            sphere_obj = a if a_is_sphere else b
            box_obj = b if a_is_sphere else a
            return self._sphere_box(sphere_obj, box_obj)
        return self._box_box(a, b)

    @staticmethod
    def _box_box(a: MobileObject, b: MobileObject) -> tuple[tuple[float, float, float], float] | None:
        amn, amx = a.aabb()
        bmn, bmx = b.aabb()
        # Solape en los 3 ejes
        ox = min(amx[0], bmx[0]) - max(amn[0], bmn[0])
        oy = min(amx[1], bmx[1]) - max(amn[1], bmn[1])
        oz = min(amx[2], bmx[2]) - max(amn[2], bmn[2])
        if ox <= 0 or oy <= 0 or oz <= 0:
            return None
        # Eje de menor penetración = normal (apunta de a hacia b)
        if ox <= oy and ox <= oz:
            n = (1.0, 0.0, 0.0) if a.position[0] < b.position[0] else (-1.0, 0.0, 0.0)
            depth = ox
        elif oy <= oz:
            n = (0.0, 1.0, 0.0) if a.position[1] < b.position[1] else (0.0, -1.0, 0.0)
            depth = oy
        else:
            n = (0.0, 0.0, 1.0) if a.position[2] < b.position[2] else (0.0, 0.0, -1.0)
            depth = oz
        return (n, depth)

    @staticmethod
    def _sphere_sphere(a: MobileObject, b: MobileObject) -> tuple[tuple[float, float, float], float] | None:
        ra = a.shape.get("radius", a.scale[0] * 0.5)
        rb = b.shape.get("radius", b.scale[0] * 0.5)
        dx = b.position[0] - a.position[0]
        dy = b.position[1] - a.position[1]
        dz = b.position[2] - a.position[2]
        dist2 = dx * dx + dy * dy + dz * dz
        rsum = ra + rb
        if dist2 >= rsum * rsum:
            return None
        dist = math.sqrt(dist2) if dist2 > 1e-9 else 1e-9
        n = (dx / dist, dy / dist, dz / dist)
        return (n, rsum - dist)

    @staticmethod
    def _sphere_box(sphere: MobileObject, box: MobileObject) -> tuple[tuple[float, float, float], float] | None:
        r = sphere.shape.get("radius", sphere.scale[0] * 0.5)
        bmn, bmx = box.aabb()
        # Clamp del centro de la esfera al AABB
        cx = max(bmn[0], min(sphere.position[0], bmx[0]))
        cy = max(bmn[1], min(sphere.position[1], bmx[1]))
        cz = max(bmn[2], min(sphere.position[2], bmx[2]))
        dx = sphere.position[0] - cx
        dy = sphere.position[1] - cy
        dz = sphere.position[2] - cz
        dist2 = dx * dx + dy * dy + dz * dz
        if dist2 >= r * r:
            return None
        dist = math.sqrt(dist2) if dist2 > 1e-9 else 1e-9
        n = (dx / dist, dy / dist, dz / dist)
        return (n, r - dist)

    def _resolve_collision(self, a: MobileObject, b: MobileObject, normal: tuple[float, float, float], depth: float) -> None:
        """Resolución impulsiva estándar. Masa 0 = estático."""
        if a.is_static() and b.is_static():
            return
        inv_a = 0.0 if a.is_static() else 1.0 / a.mass
        inv_b = 0.0 if b.is_static() else 1.0 / b.mass
        inv_sum = inv_a + inv_b
        if inv_sum <= 0:
            return
        # Separación (depenetration)
        a.add_position(-normal[0] * depth * inv_a / inv_sum,
                       -normal[1] * depth * inv_a / inv_sum,
                       -normal[2] * depth * inv_a / inv_sum)
        b.add_position(normal[0] * depth * inv_b / inv_sum,
                       normal[1] * depth * inv_b / inv_sum,
                       normal[2] * depth * inv_b / inv_sum)
        # Impulso
        rvx = b.velocity[0] - a.velocity[0]
        rvy = b.velocity[1] - a.velocity[1]
        rvz = b.velocity[2] - a.velocity[2]
        vn = rvx * normal[0] + rvy * normal[1] + rvz * normal[2]
        if vn > 0:
            return  # ya separándose
        e = min(a.restitution, b.restitution)
        j = -(1 + e) * vn / inv_sum
        ix, iy, iz = normal[0] * j, normal[1] * j, normal[2] * j
        a.add_velocity(-ix * inv_a, -iy * inv_a, -iz * inv_a)
        b.add_velocity(ix * inv_b, iy * inv_b, iz * inv_b)
