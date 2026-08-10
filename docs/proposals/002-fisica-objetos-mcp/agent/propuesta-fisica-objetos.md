# Propuesta: Física de colisiones, objetos móviles y subvoxel para MCP

**Fecha:** 2026-08-09
**Estado:** Propuesta
**Alcance:** Stack Python (autoritativo) + cliente web compartido (`core/web/`)
**Resumen:** Añadir un sistema de `MobileObject` gestionable vía MCP con física de colisiones entre objetos móviles (y contra el voxel grid), funciones de movimiento programables (cinemática y dinámica), físicas de destrucción reactivas a eventos (colisión, daño acumulado, tiempo), y objetos de tamaño subvoxel para esculturas detalladas creadas por MCP.

---

## 1. Motivación

Hoy `core/python/server/engine/physics.py:15` solo conoce dos familias de cuerpos:

1. **Entidades** (`Entity`, `Player`, `Enemy` en `entities.py:46`) — AABB contra voxel grid, sin colisión entre ellas.
2. **Bloques cayendo** (`falling_blocks` en `physics.py:127`) — caída libre vertical, sin interacción con entidades ni entre sí.

No existe un concepto de "objeto colocable, móvil, programable y destruible". Un agente MCP que quiera crear una estatua que rote, un proyectil que viaje y haga daño al impactar, o una escultura con detalle subvoxel, tiene que emularlo con bloques enteros y scripts ad hoc. Esta propuesta introduce ese contrato de forma nativa.

## 2. Diseño de alto nivel

### 2.1 Nuevo subsistema: `MobileObject`

Nuevo módulo `core/python/server/engine/objects.py` con una clase `MobileObject` y un `ObjectManager` (paralelo a `EnemyManager`).

```
engine/
├── objects.py            # NUEVO: MobileObject, ObjectManager
├── physics.py            # AMPLIADO: colisión obj↔obj, obj↔grid, obj↔entity
├── constants.py          # AMPLIADO: constantes de objetos
├── game_loop.py          # AMPLIADO: tick de ObjectManager
└── ...
```

### 2.2 Modelo de datos

```python
@dataclass
class MobileObject:
    id: int
    kind: str                       # "box" | "sculpture" | "projectile" | "vehicle"
    position: Vec3                  # centro del objeto (no esquina de voxel)
    velocity: Vec3
    rotation: Vec3                  # rotación euler (rad) para render
    angular_velocity: Vec3          # rad/s
    scale: Vec3                     # tamaño en unidades de voxel (subvoxel permitido)
    mass: float                     # kg; 0 = estático (no responde a fuerzas)
    restitution: float = 0.3        # coef. de rebote (0=plástico, 1=elástico)
    friction: float = 0.5
    health: float = 100.0           # si > 0, el objeto es destruible
    max_health: float = 100.0
    destructible: bool = False
    fragile: float = 0.0            # umbral de energía cinética para romperse
    expire_at: float | None = None  # tiempo de vida (proyectiles)
    collision_mask: int = 0xFF      # bitmask de grupos con los que colisiona
    collision_group: int = 0x01
    shape: dict                     # "box" | "sphere" | "sculpture_voxels" + datos
    owner_id: int | None = None     # jugador/entidad que lo creó
    visible: bool = True
    anchored: bool = False          # si True, no responde a física (estatua)
```

`scale` acepta fracciones de voxel (p. ej. `0.25`) → esto habilita subvoxel. El render del cliente dibuja el objeto como mesh `BoxGeometry(scale.x, scale.y, scale.z)` o `InstancedMesh` para esculturas.

### 2.3 Tipos de objetos soportados (fase 1)

| `kind`           | Uso típico                                  | Física                                     |
|------------------|---------------------------------------------|--------------------------------------------|
| `box`            | Cajas, plataformas, proyectiles simples      | AABB dinámica                              |
| `sphere`         | Bolas, proyectiles                           | Esfera (radio = scale.x)                   |
| `sculpture`      | Esculturas subvoxel                          | Estática o dinámica; voxels internos       |
| `projectile`     | Flechas, bolas de fuego                      | Dinámica + expiración + daño on-collision  |
| `vehicle`        | Plataformas móviles, ascensores              | Cinemática programada (path)               |

---

## 3. Física de colisiones

### 3.1 Pipeline de colisión (en `physics.py`)

El `GameLoop.tick()` (`game_loop.py:94`) ya itera entidades y enemigos. Se inserta una fase nueva:

```
1. apply_input(players)            # existente
2. update_entity(players)          # existente: entity↔grid
3. enemy_manager.update()          # existente
4. object_manager.update(dt)       # NUEVO
5. resolve_object_collisions(dt)   # NUEVO: obj↔obj, obj↔entity, obj↔grid
6. update_falling_blocks(dt)       # existente
7. flush events                    # existente
```

### 3.2 Colisión obj↔voxel grid

Reutiliza el AABB sweep existente (`physics.py:58`) generalizado a tamaño arbitrario. Para `shape="sphere"` se usa proyección del centro contra plano de bloque. El resultado de la colisión produce:
- corrección de posición (depenetration),
- evento `object_collided` con `{obj_id, other: "world", normal, impact_speed}`.

### 3.3 Colisión obj↔obj

Broad phase: **grid espacial uniforme** (celda = 2 voxels) reutilizando `Vec3` y un `dict[tuple[int,int,int], list[int]]` por tick. Narrow phase:
- box↔box: SAT simplificado en 3 ejes (suficiente para AABBs alineadas; rotación solo visual en fase 1).
- sphere↔sphere: distancia de centros.
- sphere↔box: clamp del centro al AABB.
- sculpture↔X: usa AABB envolvente + test de voxels internos solo si hay solape de AABB (fase 2).

### 3.4 Colisión obj↔entity

Las entidades (`Player`, `Enemy`) se tratan como `box` con `scale = (PLAYER_WIDTH, PLAYER_HEIGHT, PLAYER_WIDTH)` para el narrow phase. El evento `entity_collided_by_object` se difunde al cliente y dispara lógica de daño si el objeto lo indica.

### 3.5 Resolución impulsiva

```python
def resolve_collision(a: MobileObject, b: MobileObject, normal: Vec3, depth: float):
    if a.mass == 0 and b.mass == 0:
        return
    inv_a = 0.0 if a.mass == 0 else 1.0 / a.mass
    inv_b = 0.0 if b.mass == 0 else 1.0 / b.mass
    # separación
    a.position -= normal * (depth * inv_a / (inv_a + inv_b))
    b.position += normal * (depth * inv_b / (inv_a + inv_b))
    # impulso
    rv = b.velocity - a.velocity
    vn = rv · normal
    if vn > 0: return
    e = min(a.restitution, b.restitution)
    j = -(1 + e) * vn / (inv_a + inv_b)
    impulse = normal * j
    a.velocity -= impulse * inv_a
    b.velocity += impulse * inv_b
```

Esto es física estándar de motores pequeños (Godot/Unity simplificado). Suficiente para colisiones de objetos MCP; no aspiramos a Bullet/PhysX.

---

## 4. Física de destrucción

### 4.1 Causas de destrucción (eventos)

Un `MobileObject` con `destructible=True` puede destruirse por:

| Evento             | Trigger                                              |
|--------------------|------------------------------------------------------|
| `collision`        | `impact_speed * mass` ≥ `fragle`                     |
| `damage`           | llamada MCP `damage_object` o `take_damage()`        |
| `expire`           | `now > expire_at`                                    |
| `health_zero`      | `health <= 0`                                        |
| `manual`           | MCP `destroy_object`                                 |

### 4.2 Comportamiento al destruirse

```python
def destroy(self, cause: str, world: World) -> list[dict]:
    events = []
    if self.kind == "projectile":
        events.append({"type": "object_destroyed", "id": self.id, "cause": cause,
                       "fx": "explosion_small"})
    elif self.kind == "box" and self.destructible:
        # fragmentar en bloques voxel
        for (vx, vy, vz, bt) in self.shape.get("voxels", []):
            wx = int(self.position.x + vx); wy = int(self.position.y + vy); wz = int(self.position.z + vz)
            world.set_block(wx, wy, wz, bt)
        events.append({"type": "object_destroyed", "id": self.id, "cause": cause})
    elif self.kind == "sculpture":
        events.append({"type": "object_destroyed", "id": self.id, "cause": cause,
                       "fx": "poof"})
    return events
```

### 4.3 Reacción encadenada

Cuando dos objetos `destructible` colisionan con energía suficiente, **ambos** se destruyen en el mismo tick. El `ObjectManager` recoge los eventos `object_destroyed` y los difunde vía `_pending_events` (`game_loop.py:38`), igual que ya hacen los enemigos.

---

## 5. Movimientos programables vía MCP

### 5.1 Movimientos cinemáticos (para `vehicle`, estatua que rota, plataforma)

El agente MCP proporciona una **secuencia de waypoints** o una **fórmula**. El `ObjectManager` interpola posición/rotación cada tick.

```json
{
  "motion": {
    "type": "waypoints",
    "loop": true,
    "speed": 2.0,
    "points": [[10, 30, 10], [10, 30, 20], [20, 30, 20]]
  }
}
```

### 5.2 Movimientos dinámicos (proyectiles, bolas)

El agente proporciona **velocidad inicial** y opcionalmente **aceleración** (gravedad, viento). La física resuelve el resto.

```json
{
  "motion": {
    "type": "dynamic",
    "velocity": [5, 10, 0],
    "gravity": true,
    "expire_at": 5.0
  }
}
```

### 5.3 Movimientos orbitales (decoración, satélites)

```json
{
  "motion": {
    "type": "orbit",
    "center": [10, 35, 10],
    "radius": 5,
    "axis": "y",
    "angular_speed": 0.5
  }
}
```

### 5.4 Movimientos paramétricos (scripts Python)

Para máxima flexibilidad, el agente puede pasar una **expresión paramétrica** evaluada cada tick con `t` como tiempo:

```json
{
  "motion": {
    "type": "parametric",
    "x": "10 + 5*sin(t)",
    "y": "35",
    "z": "10 + 5*cos(t)",
    "dt_mul": 1.0
  }
}
```

> **Seguridad:** Las expresiones se evalúan con `eval()` en un namespace restringido (`{"sin","cos","tan","sqrt","pi","t"}`), sin builtins. Documentado en `MANUAL_MCP.md`. Solo para stack Python por ahora.

### 5.5 Catálogo de presets

Para simplificar al agente, presets de movimiento comunes se exponen como tools MCP directas (ver §6):

- `move_linear` — línea recta con velocidad.
- `move_orbit` — órbita circular.
- `move_bounce` — rebote entre dos puntos.
- `move_projectile` — parábola con gravedad.
- `move_rotate` — rotación continua sin traslación.

---

## 6. Objetos subvoxel para esculturas

### 6.1 Modelo `sculpture`

Un `MobileObject` con `kind="sculpture"` y `shape={"type": "sculpture_voxels", "resolution": N, "voxels": [...]}`.

- `resolution`: subdivisiones por voxel (1, 2, 4, 8). `resolution=4` → cada subvoxel = 0.25 unidades.
- `voxels`: lista de `{"x": float, "y": float, "z": float, "color": int, "size": float}` donde coordenadas son locales al `position` del objeto.

### 6.2 Render en cliente

El cliente web (`core/web/js/`) recibe el objeto completo en el `state_update` bajo `objects[]`. Render con `THREE.InstancedMesh`:
- 1 `InstancedMesh` por `color` con matriz por subvoxel.
- Subvoxel más pequeño práctico: `0.125` (resolution 8). Por debajo, rendimiento se degrada.

### 6.3 Creación por MCP

**Opción A — voxels explícitos:**
```json
{
  "kind": "sculpture",
  "position": [10, 40, 10],
  "resolution": 4,
  "voxels": [
    {"x": 0, "y": 0, "z": 0, "color": 0xff0000, "size": 0.25},
    {"x": 0.25, "y": 0, "z": 0, "color": 0xff0000, "size": 0.25}
  ]
}
```

**Opción B — función generadora (script Python):**
```json
{
  "kind": "sculpture",
  "position": [10, 40, 10],
  "resolution": 4,
  "generator": "sphere",
  "params": {"radius": 1.5, "color": 0xff8800}
}
```

Generadores built-in: `sphere`, `cube`, `pyramid`, `helix`, `cross`, `humanoid_bust`. Para detalle arbitrario, el agente pasa `voxels` explícitos (Opción A).

### 6.4 Límites

- Máx 4096 subvoxels por escultura (configurable en constantes).
- Subvoxel no colisiona con voxel grid a nivel individual; solo el AABB envolvente del objeto.
- Esculturas son **estáticas** por defecto (`mass=0, anchored=True`). Se puede hacer dinámica con `mass>0`.

---

## 7. Nuevas tools MCP

Ver `contrato-tools.md` para definición completa. Resumen:

| Tool                  | Descripción                                            |
|-----------------------|--------------------------------------------------------|
| `create_object`       | Crear MobileObject (box/sphere/sculpture/projectile)   |
| `update_object`       | Modificar propiedades en caliente                      |
| `move_object`         | Asignar movimiento (waypoints/dynamic/orbit/parametric)|
| `move_linear`         | Preset: línea recta                                    |
| `move_orbit`          | Preset: órbita                                          |
| `move_bounce`         | Preset: rebote                                         |
| `move_projectile`     | Preset: parábola con gravedad                          |
| `move_rotate`         | Preset: rotación continua                              |
| `stop_motion`         | Detener movimiento de un objeto                        |
| `damage_object`       | Aplicar daño a un objeto destruible                    |
| `destroy_object`      | Destruir manualmente                                   |
| `list_objects`        | Listar objetos activos                                 |
| `get_object`          | Estado de un objeto                                    |
| `create_sculpture`    | Crear escultura subvoxel (wrapper de create_object)    |
| `apply_impulse`       | Aplicar impulso a objeto dinámico                      |

Todas con `servers: ["python"]` (fase 1). Node.js queda fuera hasta que decida paridad.

---

## 8. Formato de eventos al cliente

Se añaden claves a `state_update`:

```json
{
  "objects": [
    {"id": 1, "kind": "box", "position": {...}, "rotation": {...}, "scale": {...}, "health": 80}
  ],
  "events": [
    {"type": "object_collided", "id": 1, "other": {"kind": "world"}, "normal": {...}, "impact_speed": 4.2},
    {"type": "object_destroyed", "id": 2, "cause": "collision", "fx": "explosion_small"}
  ]
}
```

El cliente (`core/web/js/`) necesita un módulo nuevo `objects.js` para render y FX.

---

## 9. Decisión de diseño: ¿por qué no Bullet/PyBullet?

- **Dependencia pesada** (~50MB, requiere build). El proyecto es ligero (FastAPI + Three.js CDN).
- **Overkill:** el gameplay actual es AABB + esferas. Motores completos complican el contrato MCP.
- **Determinismo:** la física casera es reproducible por tick fijo (20 Hz), útil para entrenamiento de IA.

Se deja abierta la puerta a PyBullet como fase futura si se necesita ragdoll/joints.

---

## 10. Fases de implementación

Ver `plan-ejecucion.md` para detalle. Resumen:

| Fase | Entrega                                             | Tiempo |
|------|-----------------------------------------------------|--------|
| 1    | `MobileObject` + `ObjectManager` + render cliente   | 4h     |
| 2    | Colisiones obj↔grid + obj↔obj (AABB/sphere)         | 5h     |
| 3    | Movimientos (waypoints/dynamic/orbit/parametric)    | 3h     |
| 4    | Presets MCP (move_linear, orbit, projectile...)     | 2h     |
| 5    | Destrucción + eventos + FX cliente                  | 3h     |
| 6    | Esculturas subvoxel + InstancedMesh                 | 4h     |
| 7    | Tests + documentación                               | 2h     |

**Total:** ~23h (3 días de trabajo concentrado).

---

## 11. Riesgos y mitigaciones

| Riesgo                                   | Prob | Impacto | Mitigación                                    |
|------------------------------------------|------|---------|-----------------------------------------------|
| Degradación de FPS con muchos objetos    | Med | Alto    | Broad-phase con grid espacial; cap de 100 obj |
| `eval()` paramétrico = vector de ataque  | Bajo| Alto    | Namespace restringido, sin builtins, solo Python |
| Cliente web no renderiza subvoxel bien   | Med | Med     | `InstancedMesh`; cap 4096 subvoxels           |
| Incompatibilidad con stack Node.js       | Alto| Bajo    | Tools marcadas `servers: ["python"]` desde el inicio |
| Colisión obj↔entity rompe gameplay       | Med | Med     | `collision_mask` por grupo; tests con player  |

---

## 12. Criterios de éxito

- [ ] Un agente MCP puede crear, mover y destruir objetos con una sola llamada cada uno.
- [ ] Dos proyectiles que chocan a velocidad suficiente se destruyen ambos en el mismo tick.
- [ ] Una escultura de 2000 subvoxels renderiza a ≥30 FPS en el cliente.
- [ ] Player recibe daño si un proyectil lo impacta.
- [ ] Tests unitarios cubren colisiones AABB/sphere, destrucción por energía, expiración.
- [ ] `definitions.json` y `MANUAL_MCP.md` actualizados.

---

## 13. Próximos pasos (post-implementación)

1. **Joints/constraints:** cadenas, bisagras (requiere motor más potente).
2. **Stack Node.js:** decidir paridad o declarar Python como único backend para objetos.
3. **Persistencia:** guardar objetos en savegame.
4. **Editor de esculturas en cliente:** GUI para esculpir con subvoxel sin MCP.
5. **Ragdoll para enemigos:** requiere PyBullet.