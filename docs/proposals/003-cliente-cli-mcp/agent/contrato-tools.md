# Contrato de subcomandos y tools virtuales — Cliente CLI `vq`

**Fecha:** 2026-08-09
**Estado:** Propuesta
**Relación con `definitions.json`:** los subcomandos Typer se generan dinámicamente desde `tools/list`. Este documento define el mapeo categoría→subcomando y las tools virtuales (recetas) que `vq chat` expone al LLM.

---

## 1. Mapeo categoría MCP → subcomando Typer

Las categorías de `definitions.json` se mapean a grupos Typer:

| Categoría `definitions.json` | Subcomando `vq` | Archivo |
|-----------------------------|-----------------|---------|
| `config` | `vq config` | `commands/config.py` |
| `player` | `vq player` | `commands/player.py` |
| `world` | `vq block` | `commands/block.py` |
| `building` | `vq build` (recetas) | `commands/build.py` |
| `objects` (propuesta 002) | `vq object` | `commands/object.py` |
| `bt` | `vq bt` | `commands/bt.py` |
| `vision` | `vq world` | `commands/world.py` |
| `navigation` | `vq nav` | `commands/nav.py` |
| `combat` | `vq combat` | `commands/combat.py` |
| `inventory` | `vq inventory` | `commands/inventory.py` |
| `avatar` | `vq avatar` | `commands/avatar.py` |
| `training` | `vq training` | `commands/training.py` |
| `util` | `vq util` | `commands/util.py` |

Las tools de comportamiento (`chase`, `evade`, etc.) no son tools MCP nativas; son bucles de cliente que invocan tools MCP. Se agrupan en `vq ai`.

---

## 2. Subcomandos por grupo

### 2.1 `vq player`

Mapeo desde tools MCP categoría `player`:

| Subcomando | Tool MCP | Args principales |
|------------|----------|-----------------|
| `vq player list` | `list_players` | — |
| `vq player state <id>` | `get_player_state` | `player_id` |
| `vq player move <id> <x> <y> <z>` | `set_player_position` | `player_id, x, y, z` |
| `vq player attack <id> [target]` | `attack` | `player_id, target_id?` |
| `vq player look <id> [--yaw] [--pitch]` | `look` | `player_id, yaw?, pitch?` |
| `vq player teleport <id> <x> <z> [y]` | `teleport` | `player_id, x, z, y?` |
| `vq player gamepad-connect <id>` | `gamepad_connect` | `player_id` |
| `vq player gamepad-input <id> [--move-x] [--move-z] [--look-x] [--look-y] [--jump] [--fly]` | `gamepad_input` | `player_id, input` |
| `vq player gamepad-disconnect <id>` | `gamepad_disconnect` | `player_id` |
| `vq player rotation <id>` | `get_rotation` | `player_id` |
| `vq player camera <id>` | `toggle_camera` | `player_id` |

### 2.2 `vq block`

Mapeo desde tools categoría `world` + `building`:

| Subcomando | Tool MCP | Args |
|------------|----------|------|
| `vq block place <x> <y> <z> <type>` | `place_block` | `x, y, z, type` |
| `vq block break <x> <y> <z>` | `break_block` | `x, y, z` |
| `vq block get <x> <y> <z>` | `get_block` | `x, y, z` |
| `vq block fill <x> <z> --w <W> --d <D> [--type T] [--height H] [--base-y Y]` | `fill_area` | `x, z, width, depth, type?, height?, baseY?` |
| `vq block clear <x> <z> --w <W> --d <D> [--height H] [--base-y Y]` | `clear_area` | `x, z, width, depth, height?, baseY?` |
| `vq block apply --file <json>` | `apply_blocks` | `blocks` (lee de archivo o stdin) |
| `vq block apply-list <x1> <y1> <z1> <x2> <y2> <z2>` | `get_blocks_in_area` | `x1,y1,z1,x2,y2,z2` |

`apply` acepta bloques desde:
- `--file blocks.json`: archivo JSON con lista de `{x,y,z,type}`.
- `--stdin`: lee JSON desde stdin (pipe).
- Args posicionales: JSON inline.

### 2.3 `vq build` (recetas)

No son tools MCP nativas; son secuencias de `apply_blocks` generadas por funciones Python en `cli/recipes/`:

| Subcomando | Receta | Origen |
|------------|--------|--------|
| `vq build house [cx] [cz] [--clear]` | `recipes/house.py` | `build_house.py` |
| `vq build castle [cx] [cz] [--clear]` | `recipes/castle.py` | `build_castle.py` |
| `vq build fortress [cx] [cz] [--clear]` | `recipes/fortress.py` | `build_fortress.py` |
| `vq build maze [cx] [cz] [--size S]` | `recipes/maze.py` | `build_maze.py` |
| `vq build pyramid [cx] [cz] [--size S]` | `recipes/pyramid.py` | `build_pyramid.py` |
| `vq build village [cx] [cz] [--houses N]` | `recipes/village.py` | `build_village.py` |
| `vq build cathedral [cx] [cz]` | `recipes/cathedral.py` | `build_gothic_cathedral.py` |
| `vq build list` | — | Lista recetas disponibles |

Todas las recetas:
1. Calculan la lista de bloques en Python (sin HTTP).
2. Envían en lotes de 400 vía `apply_blocks` (mismo patrón que `build_house.py:150`).
3. Muestran progreso en stderr.

### 2.4 `vq object` (propuesta 002)

Se genera dinámicamente cuando las tools de la propuesta 002 estén en `definitions.json`:

| Subcomando | Tool MCP | Args |
|------------|----------|------|
| `vq object create --kind <kind> --pos <x,y,z> [--scale <sx,sy,sz>] [--mass M] [--color C] [--destructible]` | `create_object` | ver propuesta 002 |
| `vq object move <id> --type <type> [...]` | `move_object` | ver propuesta 002 |
| `vq object linear <id> --vel <x,y,z>` | `move_linear` | |
| `vq object orbit <id> --center <x,y,z> --radius R [--axis y]` | `move_orbit` | |
| `vq object projectile <id> --vel <x,y,z> [--expire T] [--damage D]` | `move_projectile` | |
| `vq object rotate <id> --vel <rx,ry,rz>` | `move_rotate` | |
| `vq object stop <id>` | `stop_motion` | |
| `vq object impulse <id> --impulse <x,y,z>` | `apply_impulse` | |
| `vq object damage <id> --amount A` | `damage_object` | |
| `vq object destroy <id>` | `destroy_object` | |
| `vq object list [--kind K] [--owner O]` | `list_objects` | |
| `vq object get <id>` | `get_object` | |
| `vq object sculpture --pos <x,y,z> --resolution R [--generator G|--file F]` | `create_sculpture` | |

### 2.5 `vq ai` (bucles de comportamiento)

Bucles de cliente que invocan tools MCP repetidamente. Mantiene la lógica de los scripts originales:

| Subcomando | Origen | Descripción |
|------------|--------|-------------|
| `vq ai chase [--target 1] [--iters 40]` | `chase.py` | Persigue al jugador objetivo |
| `vq ai evade [--iters 60]` | `evade.py` | Huye del monstruo más cercano |
| `vq ai evade-chase [--iters 100]` | `evade_chase.py` | Bucle evade+chase con detección de agujeros |
| `vq ai follow [--target 1] [--distance 3]` | `follow_p1_distance.py` | Sigue al objetivo a distancia |

Flags comunes:
- `--player-id N`: ID del jugador IA controlado (default 2).
- `--interval S`: intervalo entre iteraciones en segundos (default 0.15).

### 2.6 `vq bt`

| Subcomando | Tool MCP |
|------------|----------|
| `vq bt load --file <tree.json>` | `bt_load` |
| `vq bt status` | `bt_status` |
| `vq bt stop` | `bt_stop` |

### 2.7 `vq world`

| Subcomando | Tool MCP |
|------------|----------|
| `vq world info` | `get_world_info` |
| `vq world view <player_id> [--distance D]` | `get_view` |
| `vq world top-down <player_id> --radius R` | `get_top_down_view` |
| `vq world nearby-blocks <player_id> [--radius R]` | `get_nearby_blocks` |
| `vq world nearby-entities <player_id> [--radius R]` | `get_nearby_entities` |
| `vq world environment <player_id>` | `get_environment` |
| `vq world height <x> <z>` | `get_height` |

### 2.8 `vq nav`

| Subcomando | Tool MCP |
|------------|----------|
| `vq nav to <player_id> <x> <z>` | `navigate_to` / `moverse_a` |

### 2.9 `vq combat`

| Subcomando | Tool MCP |
|------------|----------|
| `vq combat attack <player_id> [target_id]` | `attack` |
| `vq combat kill-all` | `kill_all_monsters` |

### 2.10 `vq inventory`

| Subcomando | Tool MCP |
|------------|----------|
| `vq inventory select <player_id> <slot>` | `select_slot` |
| `vq inventory next <player_id>` | `next_slot` |
| `vq inventory prev <player_id>` | `prev_slot` |
| `vq inventory get <player_id>` | `get_inventory` |
| `vq inventory add <player_id> <type> [--count N]` | `add_item` |

### 2.11 `vq avatar`

| Subcomando | Tool MCP |
|------------|----------|
| `vq avatar create [--name N] [--gender G] [--spawn-x X] [--spawn-z Z]` | `create_avatar` |
| `vq avatar walk <player_id> --direction <dir> [--steps S]` | `avatar_walk` |
| `vq avatar clear` | `avatars_clear` |
| `vq avatar follow [--activar true]` | `avatars_follow` |
| `vq avatar list` | `get_avatars` |

### 2.12 `vq config`

| Subcomando | Tool MCP |
|------------|----------|
| `vq config get` | `get_config` |
| `vq config approval <mode>` | `set_approval_mode` |
| `vq config requests` | `get_pending_requests` |
| `vq config approve <id> --approved/--rejected` | `approve_request` |

### 2.13 `vq training`

| Subcomando | Tool MCP |
|------------|----------|
| `vq training start --scenario <name>` | `training_start` |
| `vq training stop [--exito true]` | `training_stop` |

### 2.14 `vq util`

| Subcomando | Tool MCP |
|------------|----------|
| `vq util block-types` | `list_block_types` |
| `vq util avatar-colors` | `list_avatar_colors` |
| `vq util msg <player_id> <message>` | `send_message` |

---

## 3. Tools virtuales para `vq chat`

Estas NO son tools MCP; son funciones Python que `vq chat` expone al LLM como tools disponibles. Reducen tokens y errores al agrupar secuencias comunes.

### 3.1 Recetas de construcción

```json
{
  "type": "function",
  "function": {
    "name": "build_house",
    "description": "Construye una casa habitable con suelo, paredes, techo, puerta y ventanas. Usa apply_blocks por lotes.",
    "parameters": {
      "type": "object",
      "properties": {
        "cx": {"type": "integer", "description": "Coordenada X del centro"},
        "cz": {"type": "integer", "description": "Coordenada Z del centro"},
        "clear": {"type": "boolean", "description": "Limpiar sitio antes de construir", "default": false}
      },
      "required": ["cx", "cz"]
    }
  }
}
```

Recetas expuestas como tools virtuales:

| Tool virtual | Receta | Descripción para el LLM |
|--------------|--------|--------------------------|
| `build_house` | `recipes/house.py` | Casa 7x7 con puerta y ventanas |
| `build_castle` | `recipes/castle.py` | Castillo con torres y murallas |
| `build_fortress` | `recipes/fortress.py` | Fortaleza militar |
| `build_maze` | `recipes/maze.py` | Laberinto de tamaño configurable |
| `build_pyramid` | `recipes/pyramid.py` | Pirámide escalonada |
| `build_village` | `recipes/village.py` | Aldea con N casas |
| `build_cathedral` | `recipes/cathedral.py` | Catedral gótica |

### 3.2 Comportamientos de IA

| Tool virtual | Origen | Descripción |
|--------------|--------|-------------|
| `ai_chase` | `commands/ai.py` | Persigue al jugador objetivo |
| `ai_evade` | `commands/ai.py` | Huye del enemigo más cercano |
| `ai_follow` | `commands/ai.py` | Sigue al objetivo a distancia |

### 3.3 Tools MCP nativas (passthrough)

Las tools MCP de `definitions.json` se pasan al LLM con su `inputSchema` convertido al formato OpenAI function-calling:

```python
# Conversión definitions.json → OpenAI tools format
def mcp_tools_to_openai(mcp_tools: list[dict]) -> list[dict]:
    return [
        {
            "type": "function",
            "function": {
                "name": tool["name"],
                "description": tool["description"],
                "parameters": tool["inputSchema"]
            }
        }
        for tool in mcp_tools
    ]
```

El LLM ve tanto las tools MCP nativas como las tools virtuales (recetas). Si elige `build_house`, el CLI ejecuta la receta; si elige `place_block`, hace `POST /mcp` directo.

### 3.4 Resolución de tools virtuales

```python
# cli/commands/chat.py (esquema)
def execute_tool_call(call: ToolCall, client: McpClient) -> dict:
    # ¿Es una tool virtual (receta)?
    if call.name in VIRTUAL_TOOLS:
        return VIRTUAL_TOOLS[call.name](client, **call.arguments)
    # Si no, es tool MCP nativa
    return client.call(call.name, call.arguments)
```

---

## 4. Flags globales

Todos los subcomandos aceptan:

| Flag | Descripción | Default |
|------|-------------|---------|
| `--server-url URL` | URL del servidor MCP | `http://localhost:9000/mcp` |
| `--timeout S` | Timeout HTTP en segundos | `30` |
| `--json` | Output en JSON raw (para scripting) | `false` |
| `--quiet` | Suprime output informativo | `false` |
| `--verbose` | Logs detallados | `false` |

---

## 5. Ejemplos de uso

### 5.1 Comandos

```bash
# Listar jugadores
vq player list

# Mover jugador 2 a (10, 30, 20)
vq player move 2 10 30 20

# Colocar bloque piedra en (10, 25, 10)
vq block place 10 25 10 3

# Construir casa en (10, 8) limpiando antes
vq build house 10 8 --clear

# Aplicar bloques desde archivo
vq block apply --file my_blocks.json

# Crear objeto (propuesta 002)
vq object create --kind box --pos 10,40,10 --mass 1 --destructible

# Perseguir al jugador 1
vq ai chase --target 1 --iters 50

# Estado del BT
vq bt status
```

### 5.2 Chat natural

```bash
# Con Ollama Local
vq chat --provider ollama-local --model qwen2.5-coder:7b

# Conversación:
> construye una casa en (10, 8)
[LLM decide: build_house(cx=10, cz=8)]
[CLI ejecuta receta: 250 bloques colocados]
Casa construida en (10, 8).

> lleva al jugador 2 ahí
[LLM decide: set_player_position(player_id=2, x=10, y=25, z=8)]
[CLI ejecuta: POST /mcp]
Jugador 2 movido a (10, 25, 8).

> hay enemigos cerca?
[LLM decide: get_nearby_entities(player_id=2, radius=20)]
[CLI ejecuta: POST /mcp]
Sí, hay 2 zombis a 8 bloques al norte.

> que los mate
[LLM decide: kill_all_monsters()]
[CLI pide confirmación: --confirm activado]
¿Ejecutar kill_all_monsters? (y/n): y
[CLI ejecuta]
Todos los monstruos eliminados.
```

### 5.3 Dry-run

```bash
vq chat --provider ollama-local --model qwen2.5-coder:7b --dry-run

> construye un castillo en (20, 20)
Plan:
  1. build_castle(cx=20, cz=20)
¿Ejecutar? (y/n): y
[CLI ejecuta receta]
```

### 5.4 Pipe (scripting)

```bash
# JSON output para scripting
vq player list --json | jq '.players[0].position'

# Construir desde archivo
cat my_blocks.json | vq block apply --stdin

# Encadenar comandos
vq block get 10 25 10 --json | jq '.type'
```

---

## 6. Esquema OpenAI tools format (ejemplo completo)

Lo que `vq chat` envía al LLM:

```json
[
  {
    "type": "function",
    "function": {
      "name": "list_players",
      "description": "Listar todos los jugadores",
      "parameters": {"type": "object", "properties": {}}
    }
  },
  {
    "type": "function",
    "function": {
      "name": "place_block",
      "description": "Colocar bloque en coordenadas absolutas",
      "parameters": {
        "type": "object",
        "properties": {
          "x": {"type": "integer"},
          "y": {"type": "integer"},
          "z": {"type": "integer"},
          "type": {"type": "integer", "minimum": 0, "maximum": 10}
        },
        "required": ["x", "y", "z", "type"]
      }
    }
  },
  {
    "type": "function",
    "function": {
      "name": "build_house",
      "description": "Construye una casa habitable. Usa apply_blocks por lotes.",
      "parameters": {
        "type": "object",
        "properties": {
          "cx": {"type": "integer"},
          "cz": {"type": "integer"},
          "clear": {"type": "boolean", "default": false}
        },
        "required": ["cx", "cz"]
      }
    }
  }
]
```

El LLM decide cuál usar según el prompt del usuario. `build_house` es una tool virtual; `place_block` es MCP nativa.