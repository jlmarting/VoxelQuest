"""Objetos móviles gestionables vía MCP con física de colisiones y destrucción.

Propuesta 002. Convive con `entities.py` (Entidades/Jugadores/Enemigos) sin heredar
de `Entity`. El render se hace en `core/web/js/objects.js` desde el campo
`objects[]` del `state_update`.

Fase 1: modelo + manager + serialización. Sin física todavía (update es no-op).
Fase 2: colisiones obj↔grid/obj↔obj (en `physics.py`).
Fase 3+: movimientos, destrucción, esculturas.
"""

from __future__ import annotations

import math
import time
from dataclasses import dataclass, field
from typing import Any, TYPE_CHECKING

from server.engine.constants import (
    MAX_OBJECTS,
    MAX_SCULPTURE_VOXELS,
    SUBVOXEL_MIN_SIZE,
    DEFAULT_RESTITUTION,
    DEFAULT_FRICTION,
    DEFAULT_OBJECT_HEALTH,
    WORLD_HEIGHT,
)

if TYPE_CHECKING:
    from server.engine.world import World


# ---------------------------------------------------------------------------
# Tipos básicos
# ---------------------------------------------------------------------------

VALID_KINDS = ("box", "sphere", "sculpture", "projectile", "vehicle")
VALID_MOTION_TYPES = ("waypoints", "dynamic", "orbit", "parametric", "rotate", "stop")
VALID_GENERATORS = ("sphere", "cube", "pyramid", "helix", "cross", "humanoid_bust")
VALID_ORBIT_AXES = ("x", "y", "z")


@dataclass
class Motion:
    """Movimiento programable asignable a un MobileObject.

    `type` determina qué campos se consumen:
      - waypoints: points, speed, loop, _idx, _t
      - dynamic:   velocity, gravity, expire_at
      - orbit:     center, radius, axis, angular_speed, _phase
      - parametric: x, y, z (expr strings), dt_mul, _t
      - rotate:    angular_velocity, loop
      - stop:      (sin campos)
    """

    type: str = "stop"
    # waypoints
    points: list[list[float]] = field(default_factory=list)
    speed: float = 1.0
    loop: bool = False
    _idx: int = 0  # índice del segmento actual
    _t: float = 0.0  # progreso dentro del segmento (0..1) o tiempo acumulado
    # dynamic
    velocity: tuple[float, float, float] = (0.0, 0.0, 0.0)
    gravity: bool = False
    expire_at: float | None = None
    # orbit
    center: tuple[float, float, float] = (0.0, 0.0, 0.0)
    radius: float = 1.0
    axis: str = "y"
    angular_speed: float = 1.0
    _phase: float = 0.0
    # parametric
    x_expr: str | None = None
    y_expr: str | None = None
    z_expr: str | None = None
    dt_mul: float = 1.0
    # rotate
    angular_velocity: tuple[float, float, float] = (0.0, 0.0, 0.0)

    def to_dict(self) -> dict:
        d = {"type": self.type}
        if self.type == "waypoints":
            d.update({"points": self.points, "speed": self.speed, "loop": self.loop})
        elif self.type == "dynamic":
            d.update({"velocity": list(self.velocity), "gravity": self.gravity,
                      "expire_at": self.expire_at})
        elif self.type == "orbit":
            d.update({"center": list(self.center), "radius": self.radius,
                      "axis": self.axis, "angular_speed": self.angular_speed})
        elif self.type == "parametric":
            d.update({"x": self.x_expr, "y": self.y_expr, "z": self.z_expr, "dt_mul": self.dt_mul})
        elif self.type == "rotate":
            d.update({"angular_velocity": list(self.angular_velocity), "loop": self.loop})
        return d


# ---------------------------------------------------------------------------
# MobileObject
# ---------------------------------------------------------------------------

@dataclass
class MobileObject:
    """Cuerpo físico independiente de Entity. Posición = centro del objeto."""

    id: int
    kind: str
    position: tuple[float, float, float] = (0.0, 0.0, 0.0)
    velocity: tuple[float, float, float] = (0.0, 0.0, 0.0)
    rotation: tuple[float, float, float] = (0.0, 0.0, 0.0)
    angular_velocity: tuple[float, float, float] = (0.0, 0.0, 0.0)
    scale: tuple[float, float, float] = (1.0, 1.0, 1.0)
    mass: float = 1.0
    restitution: float = DEFAULT_RESTITUTION
    friction: float = DEFAULT_FRICTION
    health: float = DEFAULT_OBJECT_HEALTH
    max_health: float = DEFAULT_OBJECT_HEALTH
    destructible: bool = False
    fragile: float = 0.0
    expire_at: float | None = None
    collision_mask: int = 0xFF
    collision_group: int = 0x01
    shape: dict[str, Any] = field(default_factory=dict)
    owner_id: int | None = None
    visible: bool = True
    anchored: bool = False
    color: int = 0xFFFFFF
    emissive: bool = False  # si True, el cliente añade un PointLight (emite luz)
    motion: Motion | None = None
    # Interno
    alive: bool = True
    _spawn_time: float = 0.0
    _voxels_sent: bool = False  # sculpture: ¿se han enviado los voxels completos?
    # Para proyectiles: daño a aplicar al impactar
    damage_on_impact: float = 0.0
    destroy_on_impact: bool = False

    # --- Helpers -------------------------------------------------------------

    def is_static(self) -> bool:
        """Un objeto estático no responde a fuerzas/impulsos."""
        return self.mass == 0.0 or self.anchored

    def aabb(self) -> tuple[tuple[float, float, float], tuple[float, float, float]]:
        """AABB alineada al mundo (sin rotación) en coordenadas mundo.

        Para `box`/`vehicle`: usa scale como tamaño completo.
        Para `sphere`: cubo envolvente de lado 2*radius.
        Para `sculpture`: AABB envolvente de los subvoxels si existe, si no scale.
        """
        sx, sy, sz = self.scale
        px, py, pz = self.position
        if self.kind == "sphere":
            r = self.shape.get("radius", sx * 0.5)
            half = (r, r, r)
        else:
            # sculpture: envolvente de voxels si está disponible
            voxels = self.shape.get("voxels") if self.shape else None
            if self.kind == "sculpture" and voxels:
                # Los voxels pueden ser tuplas (x,y,z) o dicts {x,y,z,color,size}
                xs = [v[0] if isinstance(v, (tuple, list)) else v["x"] for v in voxels]
                ys = [v[1] if isinstance(v, (tuple, list)) else v["y"] for v in voxels]
                zs = [v[2] if isinstance(v, (tuple, list)) else v["z"] for v in voxels]
                min_l = (min(xs), min(ys), min(zs))
                max_l = (max(xs) + SUBVOXEL_MIN_SIZE, max(ys) + SUBVOXEL_MIN_SIZE,
                         max(zs) + SUBVOXEL_MIN_SIZE)
                return ((px + min_l[0], py + min_l[1], pz + min_l[2]),
                        (px + max_l[0], py + max_l[1], pz + max_l[2]))
            half = (sx * 0.5, sy * 0.5, sz * 0.5)
        return ((px - half[0], py - half[1], pz - half[2]),
                (px + half[0], py + half[1], pz + half[2]))

    def kinetic_energy(self) -> float:
        vx, vy, vz = self.velocity
        return 0.5 * self.mass * (vx * vx + vy * vy + vz * vz)

    def speed(self) -> float:
        vx, vy, vz = self.velocity
        return math.sqrt(vx * vx + vy * vy + vz * vz)

    # --- Mutación in-place (las tuplas son inmutables) -----------------------

    def set_position(self, x: float, y: float, z: float) -> None:
        self.position = (x, y, z)

    def set_velocity(self, x: float, y: float, z: float) -> None:
        self.velocity = (x, y, z)

    def add_position(self, dx: float, dy: float, dz: float) -> None:
        self.position = (self.position[0] + dx, self.position[1] + dy, self.position[2] + dz)

    def add_velocity(self, dx: float, dy: float, dz: float) -> None:
        self.velocity = (self.velocity[0] + dx, self.velocity[1] + dy, self.velocity[2] + dz)

    def set_rotation(self, x: float, y: float, z: float) -> None:
        self.rotation = (x, y, z)

    # --- Destrucción (Fase 5) -----------------------------------------------

    def destroy(self, cause: str, world: "World") -> list[dict]:
        """Destruye el objeto. Devuelve eventos a difundir.

        Comportamiento según kind:
          - projectile: explosión pequeña (fx), sin fragmentación.
          - box destructible: fragmenta en bloques voxel del tipo indicado en
            shape.voxels (o COBBLESTONE por defecto) usando world.set_block.
          - sculpture: efecto 'poof' sin fragmentación (los subvoxels no son
            bloques enteros del mundo).
          - vehicle/sphere: poof.
        Siempre emite object_destroyed.
        """
        events: list[dict] = []
        fx: str | None = None
        if self.kind == "projectile":
            fx = "explosion_small"
        elif self.kind == "box" and self.destructible:
            fx = "break"
            # Fragmentar en bloques voxel
            voxels = self.shape.get("voxels") if self.shape else None
            if not voxels:
                # Sin voxels explícitos: un único bloque bajo el centro
                voxels = [(0.0, 0.0, 0.0)]
            block_type = self.shape.get("block_type", 8)  # COBBLESTONE por defecto
            for v in voxels:
                bx = int(self.position[0] + v[0])
                by = int(self.position[1] + v[1])
                bz = int(self.position[2] + v[2])
                if 0 <= by < WORLD_HEIGHT:
                    world.set_block(bx, by, bz, block_type)
        elif self.kind == "sculpture":
            fx = "poof"
        else:
            fx = "poof"
        events.append({
            "type": "object_destroyed",
            "id": self.id,
            "cause": cause,
            "fx": fx,
            "position": list(self.position),
            "kind": self.kind,
        })
        self.alive = False
        return events

    # --- Serialización -------------------------------------------------------

    def to_dict(self) -> dict:
        d = {
            "id": self.id,
            "kind": self.kind,
            "position": list(self.position),
            "velocity": list(self.velocity),
            "rotation": list(self.rotation),
            "angular_velocity": list(self.angular_velocity),
            "scale": list(self.scale),
            "mass": self.mass,
            "restitution": self.restitution,
            "friction": self.friction,
            "health": self.health,
            "max_health": self.max_health,
            "destructible": self.destructible,
            "fragile": self.fragile,
            "collision_group": self.collision_group,
            "collision_mask": self.collision_mask,
            "owner_id": self.owner_id,
            "visible": self.visible,
            "anchored": self.anchored,
            "color": self.color,
            "emissive": self.emissive,
            "alive": self.alive,
        }
        if self.shape:
            # Solo enviar voxels la primera vez (al crear) para no saturar WS.
            # El manager decide cuándo incluirlos via _full_snapshot.
            d["shape"] = self.shape
        if self.expire_at is not None:
            d["expire_at"] = self.expire_at
        if self.motion is not None:
            d["motion"] = self.motion.to_dict()
        if self.damage_on_impact:
            d["damage_on_impact"] = self.damage_on_impact
        return d


# ---------------------------------------------------------------------------
# ObjectManager
# ---------------------------------------------------------------------------

class ObjectManager:
    """Gestiona el ciclo de vida de los MobileObject.

    En fase 1 `update()` es no-op. A partir de fase 2+ se añaden
    `update_motions`, comprobación de destrucción, etc. (se implementan en
    sus fases correspondientes).
    """

    def __init__(self, world: World, max_objects: int = MAX_OBJECTS):
        self.world = world
        self.objects: list[MobileObject] = []
        self.max_objects = max_objects
        self._next_id = 1

    # --- API básica ----------------------------------------------------------

    def get(self, object_id: int) -> MobileObject | None:
        for o in self.objects:
            if o.id == object_id:
                return o
        return None

    def list(self, filter_: dict | None = None) -> list[MobileObject]:
        if not filter_:
            return list(self.objects)
        out = []
        for o in self.objects:
            ok = True
            for k, v in filter_.items():
                if getattr(o, k, None) != v:
                    ok = False
                    break
            if ok:
                out.append(o)
        return out

    def create(self, **kwargs: Any) -> MobileObject:
        if len(self.objects) >= self.max_objects:
            raise ValueError(f"max_objects reached ({self.max_objects})")
        kind = kwargs.get("kind")
        if kind not in VALID_KINDS:
            raise ValueError(f"invalid kind: {kind!r} (valid: {VALID_KINDS})")

        # Valores por defecto según kind
        scale = tuple(kwargs.get("scale", (1.0, 1.0, 1.0)))
        shape = dict(kwargs.get("shape") or {})
        if not shape:
            if kind == "sphere":
                shape = {"type": "sphere", "radius": scale[0] * 0.5}
            elif kind == "projectile":
                shape = {"type": "sphere", "radius": 0.2}
                if "scale" not in kwargs:
                    scale = (0.4, 0.4, 0.4)
            elif kind == "sculpture":
                shape = {"type": "sculpture_voxels", "resolution": kwargs.get("resolution", 4),
                         "voxels": kwargs.get("voxels", [])}
            else:
                shape = {"type": "box"}
        else:
            # Asegurar type coherente con kind
            if "type" not in shape:
                shape["type"] = "sphere" if kind == "sphere" else "box"

        motion_dict = kwargs.get("motion")
        motion = self._build_motion(motion_dict) if motion_dict else None

        obj = MobileObject(
            id=self._next_id,
            kind=kind,
            position=tuple(kwargs.get("position", (0.0, 0.0, 0.0))),
            velocity=tuple(kwargs.get("velocity", (0.0, 0.0, 0.0))),
            rotation=tuple(kwargs.get("rotation", (0.0, 0.0, 0.0))),
            angular_velocity=tuple(kwargs.get("angular_velocity", (0.0, 0.0, 0.0))),
            scale=scale,
            mass=float(kwargs.get("mass", 1.0)),
            restitution=float(kwargs.get("restitution", DEFAULT_RESTITUTION)),
            friction=float(kwargs.get("friction", DEFAULT_FRICTION)),
            health=float(kwargs.get("health", DEFAULT_OBJECT_HEALTH)),
            max_health=float(kwargs.get("max_health", kwargs.get("health", DEFAULT_OBJECT_HEALTH))),
            destructible=bool(kwargs.get("destructible", False)),
            fragile=float(kwargs.get("fragile", 0.0)),
            expire_at=kwargs.get("expire_at"),
            collision_mask=int(kwargs.get("collision_mask", 0xFF)),
            collision_group=int(kwargs.get("collision_group", 0x01)),
            shape=shape,
            owner_id=kwargs.get("owner_id"),
            visible=bool(kwargs.get("visible", True)),
            anchored=bool(kwargs.get("anchored", False)),
            color=int(kwargs.get("color", 0xFFFFFF)),
            emissive=bool(kwargs.get("emissive", False)),
            motion=motion,
            damage_on_impact=float(kwargs.get("damage_on_impact", 0.0)),
            destroy_on_impact=bool(kwargs.get("destroy_on_impact", False)),
            _spawn_time=time.time(),
        )
        self._next_id += 1
        self.objects.append(obj)
        return obj

    def update(self, obj: MobileObject, patch: dict) -> MobileObject:
        for k, v in patch.items():
            if k == "id":
                continue
            if k == "motion":
                obj.motion = self._build_motion(v) if v else None
                continue
            if hasattr(obj, k):
                setattr(obj, k, v)
        return obj

    def destroy(self, obj: MobileObject) -> None:
        if obj in self.objects:
            obj.alive = False
            self.objects.remove(obj)

    # --- Serialización para state_update ------------------------------------

    def get_state(self, full: bool = False) -> list[dict]:
        """Serializa todos los objetos.

        Para esculturas, el snapshot incremental NO incluye los voxels
        (demasiado pesado para 20 Hz). El cliente los pide vía `get_object`
        la primera vez que ve la escultura. `full=True` incluye los voxels
        completos (para snapshots puntuales o debugging).
        """
        out = []
        for o in self.objects:
            d = o.to_dict()
            if not full and o.kind == "sculpture" and "voxels" in o.shape:
                d_shape = dict(o.shape)
                d_shape["voxels"] = None  # señal al cliente: pídelos vía get_object
                d_shape["voxel_count"] = len(o.shape["voxels"])
                d["shape"] = d_shape
            out.append(d)
        return out

    # --- Tick ----------------------------------------------------------------

    def update_motions(self, dt: float, now: float) -> list[dict]:
        """Aplica motions y comprueba expiraciones. Devuelve eventos.

        Tipos soportados:
          - waypoints: interpola entre puntos a `speed`. `loop` reinicia.
          - dynamic: integra velocidad + gravedad opcional. La física de
            colisiones contra el grid se aplica después en `physics.update_object`.
          - orbit: pos = center + R*(cos(ωt), 0, sin(ωt)) con eje configurable.
          - parametric: eval(expr, namespace_seguro, {}) con `t` = tiempo acumulado.
          - rotate: integra angular_velocity.
          - stop: noop.

        Los objetos con motion 'waypoints'/'orbit'/'parametric' son cinemáticos:
        su velocidad se ignora para colisión contra el grid (no caen). El
        motion 'dynamic' sí interactúa con la física (gravedad + colisiones).
        """
        events: list[dict] = []
        # Namespace seguro para parametric
        safe_ns = {"sin": math.sin, "cos": math.cos, "tan": math.tan,
                   "sqrt": math.sqrt, "pi": math.pi, "abs": abs, "min": min, "max": max}
        for i in range(len(self.objects) - 1, -1, -1):
            obj = self.objects[i]
            # Expiración por tiempo de vida
            if obj.expire_at is not None and now - obj._spawn_time >= obj.expire_at:
                events.append({"type": "object_destroyed", "id": obj.id, "cause": "expire"})
                obj.alive = False
                self.objects.pop(i)
                continue
            motion = obj.motion
            if motion is None or motion.type == "stop":
                continue
            if motion.type == "waypoints":
                self._update_waypoints(obj, motion, dt)
            elif motion.type == "dynamic":
                self._update_dynamic(obj, motion, dt)
            elif motion.type == "orbit":
                self._update_orbit(obj, motion, dt)
            elif motion.type == "parametric":
                self._update_parametric(obj, motion, dt, safe_ns)
            elif motion.type == "rotate":
                self._update_rotate(obj, motion, dt)
        return events

    @staticmethod
    def _update_waypoints(obj: MobileObject, m: Motion, dt: float) -> None:
        if len(m.points) < 2:
            return
        n = len(m.points)
        # Avanzar tiempo dentro del segmento actual
        a = m.points[m._idx]
        b = m.points[(m._idx + 1) % n]
        seg_len = math.sqrt(sum((b[k] - a[k]) ** 2 for k in range(3)))
        if seg_len < 1e-6:
            m._idx = (m._idx + 1) % n
            return
        seg_time = seg_len / m.speed if m.speed > 0 else float("inf")
        m._t += dt
        if m._t >= seg_time:
            # ¿Fin del trayecto? (último segmento completado y sin loop)
            if m._idx == n - 2 and not m.loop:
                obj.position = tuple(m.points[n - 1])
                obj.motion = None
                return
            # Avanzar al siguiente segmento
            m._idx = (m._idx + 1) % n
            m._t = 0.0
            a = m.points[m._idx]
            b = m.points[(m._idx + 1) % n]
            seg_len = math.sqrt(sum((b[k] - a[k]) ** 2 for k in range(3)))
            seg_time = seg_len / m.speed if m.speed > 0 else float("inf")
        alpha = min(1.0, m._t / seg_time) if seg_time > 0 else 1.0
        obj.position = tuple(a[k] + (b[k] - a[k]) * alpha for k in range(3))

    @staticmethod
    def _update_dynamic(obj: MobileObject, m: Motion, dt: float) -> None:
        # La integración de velocidad + gravedad la hace physics.update_object
        # (que comprueba obj.motion.type == 'dynamic' y m.gravity). Aquí solo
        # marcamos la velocidad inicial si es la primera vez.
        # Nada que hacer: physics.update_object integra velocity + gravedad y
        # resuelve colisiones contra el grid.
        pass

    @staticmethod
    def _update_orbit(obj: MobileObject, m: Motion, dt: float) -> None:
        m._phase += m.angular_speed * dt
        c = m.center
        r = m.radius
        if m.axis == "y":
            obj.position = (c[0] + r * math.cos(m._phase), c[1], c[2] + r * math.sin(m._phase))
        elif m.axis == "x":
            obj.position = (c[0], c[1] + r * math.cos(m._phase), c[2] + r * math.sin(m._phase))
        else:  # z
            obj.position = (c[0] + r * math.cos(m._phase), c[1] + r * math.sin(m._phase), c[2])

    @staticmethod
    def _update_parametric(obj: MobileObject, m: Motion, dt: float, ns: dict) -> None:
        m._t += dt * m.dt_mul
        t = m._t
        try:
            if m.x_expr is not None:
                x = float(eval(m.x_expr, {"__builtins__": {}}, {**ns, "t": t}))
            else:
                x = obj.position[0]
            if m.y_expr is not None:
                y = float(eval(m.y_expr, {"__builtins__": {}}, {**ns, "t": t}))
            else:
                y = obj.position[1]
            if m.z_expr is not None:
                z = float(eval(m.z_expr, {"__builtins__": {}}, {**ns, "t": t}))
            else:
                z = obj.position[2]
            obj.position = (x, y, z)
        except Exception:
            # Expresión inválida: detener motion para no spamear errores
            obj.motion = None

    @staticmethod
    def _update_rotate(obj: MobileObject, m: Motion, dt: float) -> None:
        av = m.angular_velocity
        rx, ry, rz = obj.rotation
        obj.rotation = (rx + av[0] * dt, ry + av[1] * dt, rz + av[2] * dt)

    # --- Destrucción (Fase 5) ----------------------------------------------

    def check_destruction(self, collision_events: list[dict], entities: list) -> list[dict]:
        """Procesa eventos object_collided y aplica daño/destrucción.

        Para cada colisión:
          - Si un objeto es destructible y la energía cinética del impacto
            supera su `fragile`, se destruye (cause=collision).
          - Si un objeto tiene damage_on_impact > 0 y la otra parte es una
            entidad (Player/Enemy), aplica daño a la entidad.
          - Si destroy_on_impact y el proyectil es destructible, se destruye.

        `entities` es una lista de objetos con `id` y `take_damage(amount)`.
        Los eventos de colisión llevan `id` (objeto A), `other` ({kind, id})
        y `impact_speed`.

        Devuelve nuevos eventos object_destroyed + entity_damaged.
        """
        out: list[dict] = []
        destroyed_ids: set[int] = set()
        for ev in collision_events:
            if ev.get("type") != "object_collided":
                continue
            a = self.get(ev["id"])
            if a is None or a.id in destroyed_ids:
                continue
            other_id = ev.get("other", {}).get("id")
            b = self.get(other_id) if other_id is not None else None
            impact_speed = ev.get("impact_speed", 0.0)
            # Energía cinética de cada objeto por separado (aproximación).
            ke_a = 0.5 * a.mass * impact_speed * impact_speed
            ke_b = 0.5 * b.mass * impact_speed * impact_speed if b is not None else 0.0
            # Fragmentación por umbral fragile: A
            if a.destructible and a.fragile > 0 and ke_a >= a.fragile and a.id not in destroyed_ids:
                out.extend(a.destroy("collision", self.world))
                destroyed_ids.add(a.id)
            # Fragmentación por umbral fragile: B
            if b is not None and b.destructible and b.fragile > 0 and ke_b >= b.fragile and b.id not in destroyed_ids:
                out.extend(b.destroy("collision", self.world))
                destroyed_ids.add(b.id)
            # Daño a entidad por proyectil
            if a.damage_on_impact > 0 and b is None:
                # other.kind == "world" o "entity": buscar entidad cercana
                # (el evento no incluye la entidad; la detectamos por posición)
                for ent in entities:
                    if not hasattr(ent, "take_damage"):
                        continue
                    ep = ent.position
                    ex = getattr(ep, "x", ep[0] if isinstance(ep, (list, tuple)) else 0)
                    ey = getattr(ep, "y", ep[1] if isinstance(ep, (list, tuple)) else 0)
                    ez = getattr(ep, "z", ep[2] if isinstance(ep, (list, tuple)) else 0)
                    dx = ex - a.position[0]
                    dy = ey - a.position[1]
                    dz = ez - a.position[2]
                    dist = (dx * dx + dy * dy + dz * dz) ** 0.5
                    if dist < max(a.scale) * 0.5 + 1.0:
                        ent.take_damage(a.damage_on_impact)
                        out.append({
                            "type": "entity_damaged",
                            "target": "entity",
                            "id": getattr(ent, "id", None),
                            "amount": a.damage_on_impact,
                            "by_object": a.id,
                        })
                        if a.destroy_on_impact and a.id not in destroyed_ids:
                            out.extend(a.destroy("collision", self.world))
                            destroyed_ids.add(a.id)
                        break
            # Colisión obj↔obj con daño (proyectil vs otro objeto)
            if a.damage_on_impact > 0 and b is not None and b.id not in destroyed_ids:
                # El proyectil daña al otro objeto si este es destructible
                if b.destructible:
                    b.health -= a.damage_on_impact
                    out.append({
                        "type": "object_damaged",
                        "id": b.id,
                        "amount": a.damage_on_impact,
                        "by_object": a.id,
                    })
                    if b.health <= 0:
                        out.extend(b.destroy("damage", self.world))
                        destroyed_ids.add(b.id)
                if a.destroy_on_impact and a.id not in destroyed_ids:
                    out.extend(a.destroy("collision", self.world))
                    destroyed_ids.add(a.id)
        # Limpiar objetos destruidos del manager
        for oid in destroyed_ids:
            o = self.get(oid)
            if o is not None:
                self.objects.remove(o)
        return out

    # --- Construcción de Motion desde dict ----------------------------------

    @staticmethod
    def _build_motion(data: dict) -> Motion:
        mtype = data.get("type", "stop")
        if mtype not in VALID_MOTION_TYPES:
            raise ValueError(f"invalid motion type: {mtype!r}")
        m = Motion(type=mtype)
        if mtype == "waypoints":
            pts = data.get("points", [])
            m.points = [list(p) for p in pts]
            m.speed = float(data.get("speed", 1.0))
            m.loop = bool(data.get("loop", False))
        elif mtype == "dynamic":
            m.velocity = tuple(data.get("velocity", (0.0, 0.0, 0.0)))
            m.gravity = bool(data.get("gravity", False))
            m.expire_at = data.get("expire_at")
        elif mtype == "orbit":
            m.center = tuple(data.get("center", (0.0, 0.0, 0.0)))
            m.radius = float(data.get("radius", 1.0))
            ax = data.get("axis", "y")
            if ax not in VALID_ORBIT_AXES:
                raise ValueError(f"invalid orbit axis: {ax!r}")
            m.axis = ax
            m.angular_speed = float(data.get("angular_speed", 1.0))
        elif mtype == "parametric":
            m.x_expr = data.get("x")
            m.y_expr = data.get("y")
            m.z_expr = data.get("z")
            m.dt_mul = float(data.get("dt_mul", 1.0))
        elif mtype == "rotate":
            m.angular_velocity = tuple(data.get("angular_velocity", (0.0, 0.0, 0.0)))
            m.loop = bool(data.get("loop", True))
        return m


# ---------------------------------------------------------------------------
# Validación de esculturas (Fase 6, pero se define aquí para centralizar)
# ---------------------------------------------------------------------------

def validate_sculpture(voxels: list[dict], resolution: int) -> None:
    """Valida que una escultura cumpla los límites."""
    if resolution not in (1, 2, 4, 8):
        raise ValueError(f"resolution must be 1, 2, 4 or 8, got {resolution}")
    if len(voxels) > MAX_SCULPTURE_VOXELS:
        raise ValueError(f"too many voxels: {len(voxels)} > {MAX_SCULPTURE_VOXELS}")
    min_size = 1.0 / resolution
    if min_size < SUBVOXEL_MIN_SIZE:
        raise ValueError(f"subvoxel size {min_size} < {SUBVOXEL_MIN_SIZE}")


# ---------------------------------------------------------------------------
# Generadores de esculturas (Fase 6)
# ---------------------------------------------------------------------------

def generate_sculpture(generator: str, params: dict, resolution: int) -> list[dict]:
    """Genera la lista de subvoxels para una escultura con un generador built-in.

    Cada subvoxel: {"x": float, "y": float, "z": float, "color": int, "size": float}
    Coordenadas locales al `position` del MobileObject (centro = 0,0,0).
    """
    if generator not in VALID_GENERATORS:
        raise ValueError(f"invalid generator: {generator!r} (valid: {VALID_GENERATORS})")
    size = 1.0 / resolution
    color = int(params.get("color", 0xFF8800))
    if generator == "sphere":
        radius = float(params.get("radius", 1.5))
        return _gen_sphere(radius, size, color)
    elif generator == "cube":
        side = float(params.get("side", 2.0))
        return _gen_cube(side, size, color)
    elif generator == "pyramid":
        height = float(params.get("height", 2.0))
        base = float(params.get("base", 2.0))
        return _gen_pyramid(height, base, size, color)
    elif generator == "helix":
        height = float(params.get("height", 3.0))
        radius = float(params.get("radius", 1.0))
        turns = float(params.get("turns", 2.0))
        return _gen_helix(height, radius, turns, size, color)
    elif generator == "cross":
        arm = float(params.get("arm", 1.5))
        return _gen_cross(arm, size, color)
    elif generator == "humanoid_bust":
        return _gen_humanoid_bust(size, color)
    return []


def _gen_sphere(radius: float, size: float, color: int) -> list[dict]:
    voxels = []
    r2 = radius * radius
    steps = int(math.ceil(radius / (size * 0.5)))
    for ix in range(-steps, steps + 1):
        for iy in range(-steps, steps + 1):
            for iz in range(-steps, steps + 1):
                x = ix * size
                y = iy * size
                z = iz * size
                if x * x + y * y + z * z <= r2:
                    voxels.append({"x": x, "y": y, "z": z, "color": color, "size": size})
    return voxels


def _gen_cube(side: float, size: float, color: int) -> list[dict]:
    voxels = []
    half = side * 0.5
    steps = int(math.ceil(half / size))
    for ix in range(-steps, steps):
        for iy in range(-steps, steps):
            for iz in range(-steps, steps):
                x = ix * size + size * 0.5
                y = iy * size + size * 0.5
                z = iz * size + size * 0.5
                if abs(x) <= half and abs(y) <= half and abs(z) <= half:
                    voxels.append({"x": x, "y": y, "z": z, "color": color, "size": size})
    return voxels


def _gen_pyramid(height: float, base: float, size: float, color: int) -> list[dict]:
    voxels = []
    half_base = base * 0.5
    steps_y = int(math.ceil(height / size))
    for iy in range(steps_y):
        y = iy * size + size * 0.5
        # Fracción de altura: 0 abajo, 1 arriba
        frac = 1.0 - (y / height) if height > 0 else 1.0
        cur_half = half_base * frac
        steps_x = int(math.ceil(cur_half / size))
        for ix in range(-steps_x, steps_x):
            for iz in range(-steps_x, steps_x):
                x = ix * size + size * 0.5
                z = iz * size + size * 0.5
                if abs(x) <= cur_half and abs(z) <= cur_half:
                    voxels.append({"x": x, "y": y, "z": z, "color": color, "size": size})
    return voxels


def _gen_helix(height: float, radius: float, turns: float, size: float, color: int) -> list[dict]:
    voxels = []
    # Recorrer la hélice en pasos de `size`
    step = size * 0.5
    total = turns * 2 * math.pi
    t = 0.0
    y = 0.0
    while y <= height:
        x = radius * math.cos(t)
        z = radius * math.sin(t)
        voxels.append({"x": x, "y": y, "z": z, "color": color, "size": size})
        t += step / max(radius, 0.01)
        y += (height / max(total, 0.01)) * (step / max(radius, 0.01))
    return voxels


def _gen_cross(arm: float, size: float, color: int) -> list[dict]:
    voxels = []
    steps = int(math.ceil(arm / size))
    for i in range(-steps, steps + 1):
        v = i * size
        if abs(v) <= arm:
            # Brazo X
            voxels.append({"x": v, "y": 0.0, "z": 0.0, "color": color, "size": size})
            # Brazo Y
            voxels.append({"x": 0.0, "y": v, "z": 0.0, "color": color, "size": size})
            # Brazo Z
            voxels.append({"x": 0.0, "y": 0.0, "z": v, "color": color, "size": size})
    # Deduplicar el centro (0,0,0) que aparece 3 veces
    seen = set()
    unique = []
    for v in voxels:
        key = (round(v["x"], 4), round(v["y"], 4), round(v["z"], 4))
        if key not in seen:
            seen.add(key)
            unique.append(v)
    return unique


def _gen_humanoid_bust(size: float, color: int) -> list[dict]:
    """Bust simplificado: cabeza (esfera) + torso (cubo)."""
    voxels = []
    # Cabeza: esfera radio 0.6 centrada en y=1.6
    head_r = 0.6
    head_center_y = 1.6
    r2 = head_r * head_r
    steps = int(math.ceil(head_r / (size * 0.5)))
    for ix in range(-steps, steps + 1):
        for iy in range(-steps, steps + 1):
            for iz in range(-steps, steps + 1):
                x = ix * size
                y = iy * size + head_center_y
                z = iz * size
                dy = y - head_center_y
                if x * x + dy * dy + z * z <= r2:
                    voxels.append({"x": x, "y": y, "z": z, "color": color, "size": size})
    # Torso: cubo 1.2 x 1.4 x 0.6 centrado en y=0.5
    torso_half = (0.6, 0.7, 0.3)
    torso_center_y = 0.5
    steps_x = int(math.ceil(torso_half[0] / size))
    steps_y = int(math.ceil(torso_half[1] / size))
    steps_z = int(math.ceil(torso_half[2] / size))
    for ix in range(-steps_x, steps_x):
        for iy in range(-steps_y, steps_y):
            for iz in range(-steps_z, steps_z):
                x = ix * size + size * 0.5
                y = iy * size + size * 0.5 + torso_center_y
                z = iz * size + size * 0.5
                if abs(x) <= torso_half[0] and abs(y - torso_center_y) <= torso_half[1] and abs(z) <= torso_half[2]:
                    voxels.append({"x": x, "y": y, "z": z, "color": color, "size": size})
    # Deduplicar
    seen = set()
    unique = []
    for v in voxels:
        key = (round(v["x"], 4), round(v["y"], 4), round(v["z"], 4))
        if key not in seen:
            seen.add(key)
            unique.append(v)
    return unique