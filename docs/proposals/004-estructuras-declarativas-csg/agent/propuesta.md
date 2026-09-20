# Propuesta: Estructuras declarativas CSG

**Fecha:** 2026-09-06
**Estado:** Implementado
**Alcance:** Stack Python. Añade un evaluador CSG declarativo (`server/engine/csg.py`), 4 tools MCP nuevas (categoría `building`) y una biblioteca inicial de estructuras en `core/shared/structures/`.
**Resumen:** Sustituye el patrón "el agente genera un script Python por estructura" por "el agente emite un árbol CSG JSON" a través de tools MCP. El conocimiento de las estructuras pasa de código procedural a datos validables.

---

## 1. Motivación

### 1.1 Situación actual

El repertorio de construcciones del juego vive en ~61 scripts de `core/python/scripts/` (casas, castillos, catedrales, esculturas, efectos). Cada script:

- Reimplementa su propio cliente MCP (`mcp()`, `mcp_call()`) con `urllib`.
- Recalcula la geometría bloque a bloque con bucles, `math.sin/cos` y lógica procedural.
- Duplica utilidades (`detect_ground`, `send_batch`, patrón "aire gana" con `block_map`).

Consecuencias: boilerplate duplicado, conocimiento atrapado en código difícil de validar/reutilizar, y un LLM genera JSON mucho más fiablemente que código procedural con bucles anidados.

### 1.2 Objetivos

1. **Formato declarativo CSG**: primitivas + operaciones booleanas + transformaciones + repeticiones, expresado como JSON.
2. **Tools MCP**: `build_csg`, `preview_csg` (dry-run), `list_csg_structures`, `build_csg_named`.
3. **Biblioteca de estructuras**: archivos JSON en `core/shared/structures/`, listables y versionables.
4. **Sin tocar los scripts existentes**: siguen funcionando; la biblioteca crece incrementalmente.

---

## 2. Formato del árbol CSG

```json
{
  "op": "subtract",
  "children": [
    {"op": "box", "size": [7, 3, 7], "material": "cobblestone"},
    {"op": "box", "size": [1, 2, 1], "at": [0, 1, -3]}
  ]
}
```

### 2.1 Nodos

| Tipo | `op` | Parámetros |
|---|---|---|
| Primitivas | `box`, `sphere`, `cylinder`, `pyramid` | `size`/`radius`/`height`/`base`, `material` |
| Booleanas | `union`, `subtract`, `intersect` | `children` (≥2) |
| Transformación | `at` | `at: [dx,dy,dz]`, `children` |
| Rotación | `rotate` | `axis` (x/y/z), `angle` (múltiplos de 90°), `children` |
| Repetición lineal | `array` | `count`, `step: [dx,dy,dz]`, `children` |
| Repetición radial | `radial` | `count`, `radius`, `children` |

### 2.2 Materiales

- **target=grid**: nombre (`"cobblestone"`, `"planks"`, `"red_brick"`...) o id (0-13), resueltos contra `constants.py`.
- **target=sculpture**: color (int) + `resolution` (1/2/4/8), reutiliza el motor de esculturas subvoxel.

### 2.3 Semántica

- **Última escritura gana**: en `union`, los materiales de hijos posteriores sobrescriben.
- **`subtract`** elimina los bloques del segundo operando (patrón "aire gana" de los scripts).
- **`intersect`** conserva el material del primer operando.
- **Guardas**: máx 20.000 bloques por llamada, altura de mundo 64, `MAX_SCULPTURE_VOXELS=30000`.

---

## 3. Arquitectura

```
Agente (opencode) ──tools/call build_csg──► MCP Server ──► CSG Evaluator ──► world.set_block
                       {tree, position}         (server.py)    (csg.py)        (apply en lotes)
```

| Componente | Archivo | Responsabilidad |
|---|---|---|
| Evaluador | `core/python/server/engine/csg.py` | Funciones puras: `validate_tree`, `evaluate_tree`, `aabb` |
| Tools MCP | `core/python/server/mcp/server.py` | `tool_build_csg`, `tool_preview_csg`, `tool_list_csg_structures`, `tool_build_csg_named` |
| Contrato | `core/shared/tools/definitions.json` | 4 tools nuevas, categoría `building`, `servers: ["python"]` |
| Biblioteca | `core/shared/structures/*.json` | Estructuras nombradas (house, tower, castle_walls, cathedral_nave) |

### 3.1 Tools MCP

| Tool | Función |
|---|---|
| `build_csg` | Evalúa árbol CSG y aplica al mundo (grid o sculpture) |
| `preview_csg` | Dry-run: valida y devuelve nº bloques, AABB y materiales sin tocar el mundo |
| `list_csg_structures` | Lista estructuras nombradas en `core/shared/structures/` |
| `build_csg_named` | Aplica una estructura nombrada por su nombre en una posición |

---

## 4. Fases

| Fase | Entrega | Estado |
|---|---|---|
| 1 | Evaluador CSG + tests unitarios (`test_csg.py`, 21 tests) | ✅ |
| 2 | Tools MCP + tests e2e (`test_csg_e2e.py`, 11 tests) | ✅ |
| 3 | Biblioteca inicial: house, tower, castle_walls, cathedral_nave | ✅ |
| 4 | Documentación (esta propuesta, MANUAL_MCP, AGENTS, CHANGELOG) | ✅ |

---

## 5. Sinergias

- **Propuesta 003 (CLI `vq`)**: las recetas de construcción podrían delegar en `build_csg`/`build_csg_named` en vez de reimplementar geometría.
- **Agente constructor in-game (propuesta 005)**: el agente usa `build_csg`/`preview_csg` como "manos" — CSG compacto, ideal para contexto LLM pequeño.
- **LEARN**: `docs/LEARN-csg.md` documenta el concepto CSG para el agente.

---

## 6. Criterios de éxito

- [x] `preview_csg` valida y devuelve métricas sin tocar el mundo.
- [x] `build_csg` aplica árboles grid y sculpture correctamente.
- [x] `list_csg_structures` / `build_csg_named` funcionan con la biblioteca.
- [x] Las 4 tools aparecen en `tools/list` del stack Python.
- [x] Tests unitarios y e2e pasan (32 tests nuevos).
- [x] Los 61 scripts existentes siguen funcionando sin cambios.
