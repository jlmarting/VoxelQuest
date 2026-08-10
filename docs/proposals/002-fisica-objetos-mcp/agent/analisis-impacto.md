# Análisis de Impacto — Física de objetos MCP

**Fecha:** 2026-08-09
**Estado:** Diagnóstico

---

## 1. Punto de partida

### Motor actual (`core/python/server/engine/`)

| Archivo | Líneas | Responsabilidad |
|---------|--------|-----------------|
| `physics.py` | 152 | Física de entidades contra voxel grid + bloques cayendo |
| `entities.py` | 331 | `Entity`, `Player`, `Enemy`, `EnemyManager` |
| `world.py` | 172 | Mundo voxel: chunks, `get_block`, `set_block`, `raycast` |
| `game_loop.py` | 153 | Tick fijo 20 Hz, día/noche, BT, state_update |
| `constants.py` | 76 | `BlockType`, dimensiones jugador, gravedad, tick rate |
| `navigation.py` | 86* | A* |
| `chunk.py` | ~200 | Chunk y generación |
| `noise.py` | ~80 | Perlin |

(*) estimado.

### Cliente (`core/web/js/`)

| Archivo | Responsabilidad |
|---------|-----------------|
| `physics.js` (110) | Colapso de bloques en cliente (duplica parte del server) |
| `world.js` | Voxel meshing |
| `player.js` | Input local |
| `enemies.js` | Render enemigos |
| `main.js` | Game loop cliente |
| 13 más | UI, sound, navigation, etc. |

### Contrato MCP (`core/shared/tools/definitions.json`)

769 líneas, ~55 tools. Categorías existentes: `config`, `player`, `world`, `building`, `vision`, `inventory`, `combat`, `navigation`, `bt`, `avatar`, `training`, `util`. **No existe categoría `objects`.**

---

## 2. Lo que falta (gap analysis)

| Necesidad del usuario | Estado actual | Gap |
|-----------------------|---------------|-----|
| Colisión entre objetos móviles | No existe el concepto de "objeto móvil" | **Total** |
| Movimientos programables vía MCP | Solo `gamepad_input` (entidades) y `moverse_a` (A*) | **Total** para objetos |
| Destrucción reactiva a eventos | Solo bloques: `on_block_broken` (`physics.py:110`) y colapso en cascada | **Parcial**: solo bloques, no eventos arbitrarios |
| Objetos subvoxel | No existe | **Total** |

### Observaciones clave

1. **`Entity` ya tiene AABB** (`physics.py:58`) pero solo contra voxel grid, no contra otras entidades. La colisión entity↔entity no existe hoy (los enemigos se superponen al player al atacar, ver `entities.py:237`).
2. **`falling_blocks`** (`physics.py:127`) es una física ad hoc de un solo eje (Y). No generalizable a movimientos arbitrarios.
3. **El servidor es autoritativo**: cualquier nuevo objeto debe vivir en Python y difundirse vía `state_update`. El cliente es delgado.
4. **`_pending_events`** (`game_loop.py:38`) ya es el canal de eventos → los eventos de objetos encajan sin nuevo transporte.
5. **`block_changes`** (`world.py:66`) es el canal de cambios de bloques → la fragmentación de objetos destruidos lo reutiliza.

---

## 3. Impacto por archivo

### Nuevos

| Archivo | Líneas est. | Razón |
|---------|-------------|-------|
| `engine/objects.py` | ~350 | `MobileObject`, `ObjectManager`, `Motion`, generadores de escultura |
| `web/js/objects.js` | ~250 | Render de objetos + esculturas + FX |
| `server/tests/test_physics_objects.py` | ~150 | Tests de colisión |
| `server/tests/test_objects_e2e.py` | ~100 | Tests E2E |

### Modificados

| Archivo | Cambio | Riesgo |
|---------|--------|--------|
| `engine/physics.py` | +~150 líneas: `update_object`, `resolve_object_collisions`, broad-phase, narrow-phase, `resolve_collision` | **Alto**: es el corazón físico. Tests e2e existentes deben seguir pasando. |
| `engine/game_loop.py` | +~20 líneas: instanciar `ObjectManager`, llamar `update`, incluir `objects` en state | Bajo: aditivo. |
| `engine/constants.py` | +~10 líneas: constantes de objetos | Bajo. |
| `mcp/server.py` | +~200 líneas: 15 handlers | Bajo: cada handler es función aislada. |
| `shared/tools/definitions.json` | +~250 líneas: 15 tools nuevas | Bajo: aditivo. |
| `web/index.html` | +1 línea: `<script src="js/objects.js">` | Bajo. |
| `docs/MANUAL_MCP.md` | +sección "Objetos y física" | Bajo. |
| `AGENTS.md` | +mención de `objects` y nuevos archivos | Bajo. |
| `CHANGELOG.md` | +entrada Unreleased/Added | Bajo. |

### No tocados (importante)

- `engine/world.py`: **no se toca**. Los objetos usan `world.get_block`/`set_block` solo al fragmentarse.
- `engine/chunk.py`, `engine/noise.py`: no se tocan.
- `engine/navigation.py`: no se toca (los objetos no usan A*; `waypoints` es interpolación directa).
- Stack Node.js: **no se toca** en fase 1. Las tools llevan `servers: ["python"]`.
- Cliente thin de Python (`core/python/client/`, si existe): fuera de alcance; el render se hace en `core/web/` compartido.

---

## 4. Impacto en rendimiento

### Servidor (Python, 20 Hz)

- **Objetos dinámicos:** O(n²) naive para colisión obj↔obj. Con broad-phase grid espacial: O(n) esperado. Cap de 100 objetos → ≤ 100 narrow-phase/tick.
- **Colisión obj↔entity:** +100 entidades (jugadores+enemigos) × 100 objetos = 10k checks naive; con broad-phase, ~200. Despreciable.
- **Parametric `eval`:** 100 objetos × 3 evals/tick = 300 evals/tick. Namespace pequeño, sin builtins. Medible pero < 1ms.
- **Serialización:** 100 objetos × ~200 bytes = 20KB/tick extra en state_update. Asumiendo WS comprimido, OK.

### Cliente (Three.js)

- **Objetos box/sphere:** 100 meshes extra. Trivial para Three.js.
- **Esculturas:** 4096 subvoxels × N esculturas. `InstancedMesh` agrupa por color; 5 esculturas de 2000 voxels = 10k instancias en ~5 draw calls. FPS ≥ 30 realista en GPU media.
- **FX:** `THREE.Points` efímeros, auto-dispose. Sin impacto duradero.

### Memoria

- `MobileObject` ~500 bytes. 100 objetos = 50KB.
- Escultura 4096 voxels × ~32 bytes = 128KB por escultura. 5 esculturas = 640KB. OK.

---

## 5. Impacto en contrato MCP y scripts

### `definitions.json`

Crecimiento: 769 → ~1020 líneas (+33%). Nueva categoría `objects`. Tools existentes **no se modifican** → retrocompatible.

### Scripts de cliente (`core/python/scripts/`)

Los scripts existentes (`chase.py`, `evade.py`, `build_house.py`, etc.) **no se rompen**. Podrán usar las nuevas tools opcionalmente. Ejemplo de extensión natural: `build_house.py` podría crear una puerta como `vehicle` que rote con `move_rotate`.

### Behavior Trees (`core/python/server/bt/`)

El catálogo de acciones BT (`create_action_catalog` en `bt/engine.py`) podría enriquecerse con acciones `spawn_object`, `throw_projectile`. **No se incluye en esta propuesta** pero se documenta como siguiente paso.

---

## 6. Riesgos detallados

| # | Riesgo | Prob | Impacto | Mitigación |
|---|--------|------|---------|------------|
| R1 | Colisión obj↔entity daña gameplay (player empujado por plataforma) | Med | Alto | `collision_mask` por grupo; por defecto los `vehicle` no empujan al player (grupo distinto) |
| R2 | `eval()` paramétrico es vector de ataque | Bajo | Alto | Namespace sin builtins, whitelist de funciones, solo stack Python, documentar en MANUAL |
| R3 | FPS cae con muchas esculturas | Med | Med | Cap 4096 voxels, `InstancedMesh`, test de perf en Fase 6 |
| R4 | Física impulsiva es inestable a alta velocidad (tunneling) | Med | Med | Substepping si `v*dt > scale/2`; cap de velocidad |
| R5 | Stack Node.js queda desincronizado | Alto | Bajo | Tools marcadas `servers:["python"]` desde el inicio; `definitions.json` lo refleja |
| R6 | Serialización de esculturas satura el WS | Bajo | Med | Enviar escultura completa solo al crear; después solo pose/health |
| R7 | Tests existentes dejan de pasar | Bajo | Alto | Fase 1 es aditiva; no se modifica lógica de entidades existente |

---

## 7. Alternativas consideradas y descartadas

### A. PyBullet como motor físico
- **Pros:** ragdoll, joints, convexex hull, solver probado.
- **Cons:** +50MB dependencia, build nativo, curva de aprendizaje, overkill para AABB+sphere.
- **Decisión:** No en fase 1. Se documenta como fase futura si aparecen necesidades de joints/ragdoll.

### B. Reutilizar `Entity` para objetos
- **Pros:** menos código nuevo.
- **Cons:** `Entity` está acoplada a `input_move`, inventario, IA; sus campos no representan "escultura". Herencia múltiple Python es posible pero ensucia.
- **Decisión:** Clase nueva `MobileObject` independiente. Comparte `Vec3` pero no hereda de `Entity`.

### C. Subvoxel como bloque fractional en `Chunk`
- **Pros:** persistencia natural con el mundo.
- **Cons:** rompe el invariante "1 celda = 1 bloque" de `chunk.py`; meshing se complica; generación procedural no lo soporta.
- **Decisión:** Subvoxel solo dentro de `MobileObject` (esculturas). El chunk sigue siendo entero.

### D. Movimientos solo vía scripts Python (sin tools MCP)
- **Pros:** menos superficie MCP.
- **Cons:** el agente MCP no puede crear movimiento sin código Python. Contradice el objetivo.
- **Decisión:** Tools MCP para todo; `parametric` es el escape para casos avanzados.

---

## 8. Compatibilidad con guardado/carga

Hoy no hay sistema de savegame. Cuando se implemente:
- `ObjectManager.serialize()` / `deserialize()` será trivial (dataclass).
- Esculturas se guardan como lista de voxels comprimida (RLE por color).
- **No bloqueante** para esta propuesta.

---

## 9. Conclusión

El impacto es **mayoritariamente aditivo**: un módulo nuevo + extensiones a archivos existentes sin romper contratos. El único archivo "delicado" es `physics.py`, donde se añaden funciones nuevas sin tocar las existentes (`update_entity`, `_check_collision`, `update_falling_blocks` quedan intactas).

El riesgo más real es **R1** (colisión obj↔entity desbalancea gameplay). Se mitiga con `collision_mask` desde el día 1 y tests E2E con player.

La propuesta está dimensionada para el gameplay actual (voxel, 20 Hz, browser) sin introducir dependencias pesadas.