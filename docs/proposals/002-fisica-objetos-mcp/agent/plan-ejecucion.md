# Plan de Ejecución — Física de objetos MCP

**Fecha:** 2026-08-09
**Estado:** Pendiente aprobación
**Estimación total:** ~23h (3 días)

---

## Fase 1 — Modelo `MobileObject` + `ObjectManager` + render mínimo (4h)

### Objetivo
Tener objetos creables por MCP que se vean en el cliente, sin física todavía.

### Tareas

1. **`core/python/server/engine/objects.py`** (NUEVO)
   - `@dataclass MobileObject` con todos los campos de la propuesta.
   - `class ObjectManager` con `create()`, `get()`, `list()`, `update()`, `destroy()`.
   - Serialización `to_dict()` para `state_update`.
   - Generador de IDs (`next_object_id`).

2. **`core/python/server/engine/constants.py`** (AMPLIAR)
   - `MAX_OBJECTS = 100`
   - `MAX_SCULPTURE_VOXELS = 4096`
   - `SUBVOXEL_MIN_SIZE = 0.125`
   - `DEFAULT_RESTITUTION = 0.3`, `DEFAULT_FRICTION = 0.5`

3. **`core/python/server/engine/game_loop.py`** (AMPLIAR)
   - `self.object_manager = ObjectManager(world)` en `__init__`.
   - En `tick()`: `self.object_manager.update(self.dt)` (no-op en fase 1).
   - En `_build_state()`: añadir `"objects": self.object_manager.get_state()`.

4. **`core/python/server/mcp/server.py`** (AMPLIAR)
   - Handlers: `tool_create_object`, `tool_list_objects`, `tool_get_object`, `tool_update_object`, `tool_destroy_object`.

5. **`core/shared/tools/definitions.json`** (AMPLIAR)
   - Añadir 5 tools con `category: "objects"`, `servers: ["python"]`.

6. **`core/web/js/objects.js`** (NUEVO)
   - Clase `ObjectRenderer` que procesa `state_update.objects[]`.
   - Render provisional: `THREE.Mesh` con `BoxGeometry` por objeto.
   - Limpieza de meshes de objetos eliminados.

7. **`core/web/index.html`**
   - Cargar `objects.js` después de `physics.js`.

### Verificación
- [ ] `curl POST /mcp tools/call create_object` devuelve `object_id`.
- [ ] El navegador muestra una caja en la posición indicada.
- [ ] `list_objects` devuelve el objeto creado.
- [ ] `destroy_object` lo elimina del render.

---

## Fase 2 — Colisiones obj↔grid + obj↔obj (5h)

### Objetivo
Física de colisiones real. Los objetos dejan de atravesar el suelo y se empujan entre sí.

### Tareas

1. **`core/python/server/engine/physics.py`** (AMPLIAR)
   - `PhysicsSystem.update_object(obj, dt)`: mueve por velocidad, detecta colisión contra voxel grid (generalización de `_check_collision` a tamaño arbitrario).
   - `PhysicsSystem.resolve_object_collisions(dt)`: broad-phase con grid espacial + narrow-phase box/sphere.
   - `PhysicsSystem._broadphase(objects) -> list[tuple[int,int]]`: devuelve pares candidatos.
   - `PhysicsSystem._narrow_phase(a, b) -> (normal, depth) | None`.
   - `resolve_collision(a, b, normal, depth)` (impulso, ver propuesta §3.5).
   - `PhysicsSystem.collide_object_entity(obj, entity)`: tratamiento de entidades como AABB.

2. **`core/python/server/engine/objects.py`**
   - `MobileObject.aabb() -> (min, max)` en coordenadas mundo.
   - `MobileObject.is_static() -> bool` (`mass == 0 or anchored`).

3. **`core/python/server/engine/game_loop.py`**
   - En `tick()`, después de `update_entity` de jugadores:
     ```python
     self.physics.resolve_object_collisions(self.object_manager.objects, list(self.players.values()), self.enemy_manager.enemies, self.dt)
     ```
   - Recolectar eventos `object_collided` en `_pending_events`.

4. **Tests** (`core/python/server/tests/test_physics_objects.py`, NUEVO)
   - box contra suelo: la caja se detiene en y=ground.
   - dos cajas que caen una sobre otra: la inferior se aplasta o reposa.
   - esfera contra caja: rebote con `restitution=0.5`.
   - objeto estático (`mass=0`): no se mueve al ser golpeado.

### Verificación
- [ ] `create_object` con `mass=1` y `position=[10, 50, 10]` cae y reposa en el suelo.
- [ ] Dos objetos en colisión se separan y responden con impulso.
- [ ] Evento `object_collided` llega al cliente.
- [ ] Tests pasan.

---

## Fase 3 — Movimientos programables (3h)

### Objetivo
Que un agente MCP pueda asignar motion: waypoints, dynamic, orbit, parametric, rotate.

### Tareas

1. **`core/python/server/engine/objects.py`**
   - `Motion` dataclass con `type` y campos según tipo.
   - `MobileObject.motion: Motion | None`.
   - `ObjectManager.update_motions(dt, now)`: aplica el motion según tipo.
     - `waypoints`: interpola entre puntos a `speed`. `loop` reinicia.
     - `dynamic`: integra velocidad + gravedad opcional.
     - `orbit`: `pos = center + R*(cos(ωt), 0, sin(ωt))` con eje configurable.
     - `parametric`: `eval(expr, {"sin","cos","tan","sqrt","pi","t"}, {})` en namespace seguro.
     - `rotate`: integra `angular_velocity`.
     - `stop`: noop.
   - `expire_at`: si `now > expire_at`, destruir objeto (emite `object_destroyed cause=expire`).

2. **`core/python/server/engine/game_loop.py`**
   - Llamar `object_manager.update_motions(dt, now)` antes de `resolve_object_collisions`.

3. **`core/python/server/mcp/server.py`**
   - `tool_move_object` (genérico).

4. **`core/shared/tools/definitions.json`**
   - Añadir `move_object`.

5. **Tests**
   - waypoint A→B en 1s llega a B.
   - orbit regresa al punto inicial tras `2π/ω`.
   - parametric `x=10+5*sin(t)` oscila entre 5 y 15.
   - `expire_at=1` destruye a los 1s.

### Verificación
- [ ] `move_object` con waypoints mueve el objeto visible en cliente.
- [ ] `parametric` con seno produce oscilación.
- [ ] `expire_at` elimina el objeto.

---

## Fase 4 — Presets de movimiento (2h)

### Objetivo
Atajos MCP: `move_linear`, `move_orbit`, `move_bounce`, `move_projectile`, `move_rotate`, `stop_motion`, `apply_impulse`.

### Tareas

1. **`core/python/server/mcp/server.py`**
   - Cada preset construye el `motion` apropiado y llama a `tool_move_object` interno.
   - `move_projectile` además marca `kind=projectile`, `destructible=true`, `fragile` mínimo, y guarda `damage_on_impact` en el objeto para que la colisión aplique daño.
   - `apply_impulse`: `obj.velocity += impulse / obj.mass`.

2. **`core/shared/tools/definitions.json`**
   - Añadir 7 tools.

3. **Tests**
   - `move_linear` con `velocity=[3,0,0]` mueve 3 unidades en 1s.
   - `move_projectile` con `velocity=[5,10,0]` y gravedad: toca suelo a la distancia esperada.
   - `apply_impulse` a masa 2 con `[0,10,0]`: `velocity.y = 5`.

### Verificación
- [ ] Los 5 presets mueven el objeto como se espera.
- [ ] `apply_impulse` modifica velocidad.
- [ ] `stop_motion` detiene todo.

---

## Fase 5 — Destrucción + eventos + FX cliente (3h)

### Objetivo
Objetos que se rompen al colisionar, al recibir daño, al expirar o manualmente. FX visuales.

### Tareas

1. **`core/python/server/engine/objects.py`**
   - `MobileObject.destroy(cause, world) -> list[event]`.
   - Fragmentación: si `kind=box` y `destructible`, genera bloques voxel en `world` (usando `shape.voxels` o por defecto el AABB).
   - `ObjectManager.check_destruction(dt, events)`: recorre eventos `object_collided`, calcula energía cinética `0.5*m*v²`, si supera `fragile` destruye.

2. **`core/python/server/engine/physics.py`**
   - En `resolve_object_collisions`, tras resolver, emite `object_collided` con `impact_speed` para que el manager decida destrucción.

3. **`core/python/server/mcp/server.py`**
   - `tool_damage_object`, `tool_destroy_object`.

4. **`core/shared/tools/definitions.json`**
   - Añadir `damage_object`, `destroy_object`.

5. **`core/web/js/objects.js`** (AMPLIAR)
   - Procesar eventos `object_destroyed`:
     - `fx=explosion_small`: `THREE.Points` con sprite de humo, 1s, fade out.
     - `fx=poof`: escala decreciente.
   - Eliminar mesh del objeto del scene.

6. **Tests**
   - dos proyectiles chocando a alta v: ambos se destruyen.
   - `damage_object` hasta `health=0`: emite `object_destroyed`.
   - `fragile=10` con `impact_speed=5, mass=1` (KE=12.5): se rompe.

### Verificación
- [ ] Proyectil contra suelo a alta velocidad se destruye con FX.
- [ ] `damage_object` con amount=100 destruye.
- [ ] Cliente muestra FX de explosión.

---

## Fase 6 — Esculturas subvoxel (4h)

### Objetivo
Creación de esculturas con voxels de tamaño < 1, render con `InstancedMesh`.

### Tareas

1. **`core/python/server/engine/objects.py`**
   - `Sculpture` helper: valida `resolution` (1,2,4,8), `voxels` count ≤ `MAX_SCULPTURE_VOXELS`.
   - Generadores: `sphere`, `cube`, `pyramid`, `helix`, `cross`, `humanoid_bust`.
   - `MobileObject.shape = {"type":"sculpture_voxels","resolution":N,"voxels":[...]}`.
   - AABB envolvente calculado de los voxels (para colisión).

2. **`core/python/server/mcp/server.py`**
   - `tool_create_sculpture` (wrapper de `create_object`).

3. **`core/shared/tools/definitions.json`**
   - Añadir `create_sculpture`.

4. **`core/web/js/objects.js`** (AMPLIAR)
   - Render sculptures: agrupar voxels por color, crear `THREE.InstancedMesh` por color, setear matrices.
   - Rebuild solo cuando el objeto cambia (no cada frame).

5. **Tests**
   - generator sphere radio 1.5 con resolution 4 genera ~X voxels esperados.
   - sculpture con 2000 voxels: serialización y render sin error.
   - sculpture anchored: no cae.

6. **Performance**
   - Probar 5 esculturas de 2000 voxels en cliente: FPS ≥ 30.

### Verificación
- [ ] `create_sculpture` con generator `sphere` produce bola visible.
- [ ] Voxels de `size=0.25` se ven como detalle fino.
- [ ] FPS se mantiene ≥ 30 con varias esculturas.

---

## Fase 7 — Documentación y tests finales (2h)

### Tareas

1. **`core/docs/MANUAL_MCP.md`** (AMPLIAR)
   - Sección "Objetos y física" con ejemplos de cada tool.
   - Nota de seguridad sobre `parametric`.

2. **`core/AGENTS.md`** (AMPLIAR)
   - Mencionar nueva categoría `objects` y archivos relevantes.

3. **`core/CHANGELOG.md`**
   - Entrada bajo `[Unreleased] / Added`.

4. **Tests E2E** (`core/python/server/tests/test_objects_e2e.py`)
   - Escenario: crear proyectil, lanzar, impacta enemigo, enemigo recibe daño, proyectil se destruye.
   - Escenario: crear escultura, rotar, destruir por daño.

5. **Linter/typecheck**
   - `ruff check core/python`
   - `mypy core/python/server/engine/objects.py` (si está configurado).

### Verificación
- [ ] Manual actualizado con ejemplos que funcionan.
- [ ] Tests E2E pasan.
- [ ] CHANGELOG actualizado.

---

## Resumen de archivos tocados

| Archivo | Acción |
|---------|--------|
| `core/python/server/engine/objects.py` | NUEVO |
| `core/python/server/engine/physics.py` | AMPLIAR |
| `core/python/server/engine/constants.py` | AMPLIAR |
| `core/python/server/engine/game_loop.py` | AMPLIAR |
| `core/python/server/mcp/server.py` | AMPLIAR |
| `core/python/server/tests/test_physics_objects.py` | NUEVO |
| `core/python/server/tests/test_objects_e2e.py` | NUEVO |
| `core/shared/tools/definitions.json` | AMPLIAR (15 tools) |
| `core/web/js/objects.js` | NUEVO |
| `core/web/index.html` | AMPLIAR (cargar objects.js) |
| `core/docs/MANUAL_MCP.md` | AMPLIAR |
| `core/AGENTS.md` | AMPLIAR |
| `core/CHANGELOG.md` | AMPLIAR |

---

## Dependencias entre fases

```
Fase 1 ──► Fase 2 ──► Fase 3 ──► Fase 4
                │           │
                └──► Fase 5 ┘
                │
                └──► Fase 6
                         │
                         └──► Fase 7
```

Fase 5 y 6 pueden ir en paralelo una vez completadas Fases 2 y 3.