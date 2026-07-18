# Protocolo cliente-servidor de VoxelQuest (Python Server)

**Versión:** 0.1  
**Fecha:** 2026-07-18  
**Rama:** `feat/python-server`  
**ADR relacionado:** [ADR-002: Migración a servidor Python autoritativo](./adr/002-python-server.md)  
**Plan relacionado:** [Plan de migración](./python-server-plan.md)

---

## 1. Principios generales

1. El **servidor Python es la única fuente de verdad** del mundo: chunks, entidades, física, inventarios.
2. El **cliente web es un renderizador ligero**: solo envía input y recibe estado.
3. Las acciones de agentes externas van por **MCP HTTP POST `/mcp`**, usando JSON-RPC 2.0.
4. Las actualizaciones de juego en tiempo real van por **WebSocket** (`/ws`).
5. Todos los mensajes son **JSON**.

---

## 2. Constantes compartidas

### 2.1 Tipos de bloque

```json
{
  "AIR": 0,
  "GRASS": 1,
  "DIRT": 2,
  "STONE": 3,
  "WOOD": 4,
  "LEAVES": 5,
  "SAND": 6,
  "WATER": 7,
  "COBBLESTONE": 8,
  "PLANKS": 9,
  "BEDROCK": 10
}
```

**Reglas del servidor:**
- `BEDROCK` (10) no se puede romper.
- `WATER` (7) no es sólido para colisiones.
- `AIR` (0) siempre es transitable.

### 2.2 Constantes del mundo

| Nombre | Valor | Descripción |
|--------|-------|-------------|
| `CHUNK_SIZE` | 16 | Ancho/profundidad de un chunk en bloques. |
| `WORLD_HEIGHT` | 64 | Altura máxima del mundo en bloques. |
| `SEA_LEVEL` | 20 | Nivel del mar. |
| `TICK_RATE` | 20 | Ticks de simulación por segundo. |
| `DT` | 0.05 | Duración de un tick en segundos (`1 / TICK_RATE`). |

### 2.3 Constantes de entidades

| Entidad | Altura | Anchura | Vida máxima | Velocidad | Gravedad |
|---------|--------|---------|-------------|-----------|----------|
| Jugador | 1.8 | 0.6 (radio 0.3) | 20 | 5 m/s | -20 m/s² |
| Zombie | 1.8 | 0.6 | 20 | 2 m/s | -20 m/s² |
| Skeleton | 1.8 | 0.6 | 20 | 2.5 m/s | -20 m/s² |
| Creeper | 1.5 | 0.6 | 20 | 1.5 m/s | -20 m/s² |

### 2.4 Jugadores

- IDs 1 y 2 están reservados para jugadores humanos locales.
- IDs ≥ 3 son avatares/controlados por IA.

---

## 3. Canal WebSocket (`/ws`)

### 3.1 Conexión

El cliente web se conecta por WebSocket a:

```
ws://localhost:9000/ws
```

Tras conectar, el servidor asigna o confirma el `player_id` del cliente. En el futuro se podrá soportar múltiples clientes simultáneos.

### 3.2 Mensajes servidor → cliente

#### 3.2.1 `welcome`

Enviado al conectar. Indica configuración inicial.

```json
{
  "type": "welcome",
  "client_id": "uuid-o-sesion",
  "player_id": 1,
  "tick_rate": 20,
  "world": {
    "seed": 12345,
    "spawn": { "x": 24.5, "y": 25.0, "z": 20.5 }
  },
  "constants": {
    "CHUNK_SIZE": 16,
    "WORLD_HEIGHT": 64,
    "BLOCK_TYPES": { "AIR": 0, "GRASS": 1, ... }
  }
}
```

#### 3.2.2 `state_update`

Mensaje principal de estado del mundo. Enviado a 20 Hz, con interpolación recomendada en el cliente.

```json
{
  "type": "state_update",
  "tick": 1234,
  "timestamp": 1752931200.050,
  "players": {
    "1": {
      "id": 1,
      "name": "Jugador 1",
      "x": 24.5,
      "y": 25.0,
      "z": 20.5,
      "rx": 0.0,
      "ry": 0.0,
      "health": 20,
      "max_health": 20,
      "on_ground": true,
      "is_flying": false,
      "selected_slot": 0,
      "is_ai": false
    },
    "2": { ... }
  },
  "enemies": [
    {
      "id": 1,
      "type": "ZOMBIE",
      "x": 30.0,
      "y": 25.0,
      "z": 30.0,
      "health": 18,
      "max_health": 20,
      "state": "chase"
    }
  ],
  "chunk_deltas": {
    "0,0": {
      "modified": [
        [10, 20, 10, 1],
        [11, 21, 11, 0]
      ],
      "full": false
    }
  },
  "day_time": 0.5,
  "is_night": false,
  "events": [
    { "type": "damage_taken", "target": "player", "id": 2, "amount": 2, "source": "enemy", "source_id": 1 }
  ]
}
```

Campos:

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `tick` | int | Número de tick de simulación. |
| `timestamp` | float | Tiempo del servidor en segundos. |
| `players` | dict | Clave: `player_id` como string. |
| `enemies` | array | Lista de enemigos activos. |
| `chunk_deltas` | dict | Cambios de bloques desde el último estado. Clave: `"cx,cz"`. |
| `day_time` | float | 0.0 = amanecer, 0.5 = mediodía, 1.0 = siguiente amanecer. |
| `is_night` | bool | `true` si es de noche. |
| `events` | array | Eventos ocurridos en este tick (daño, bloques rotos, muertes). |

#### 3.2.3 `chunk_full`

Enviado cuando el cliente entra en una región nueva. Contiene un chunk completo.

```json
{
  "type": "chunk_full",
  "tick": 1234,
  "chunk": {
    "cx": 0,
    "cz": 0,
    "blocks": "base64(...)"
  }
}
```

El campo `blocks` es una representación compacta del chunk. En v0.1 puede ser una lista de `[x, y, z, type]` o un string base64 de bytes. Se define en la implementación.

#### 3.2.4 `pong`

Respuesta a `ping` del cliente.

```json
{
  "type": "pong",
  "server_time": 1752931200.050,
  "client_time": 1752931200.020
}
```

#### 3.2.5 `error`

Errores no fatales del canal de juego.

```json
{
  "type": "error",
  "code": "INVALID_INPUT",
  "message": "player_id desconocido"
}
```

### 3.3 Mensajes cliente → servidor

#### 3.3.1 `input`

Input del jugador humano. Enviado a 60 Hz o según eventos disponibles.

```json
{
  "type": "input",
  "seq": 42,
  "player_id": 1,
  "move": { "x": 0.0, "z": 1.0 },
  "look": { "x": 0.05, "y": -0.02 },
  "jump": false,
  "fly": false,
  "place_block": false,
  "break_block": false,
  "selected_slot": 0,
  "camera_mode": 0
}
```

Reglas:

| Campo | Rango | Significado |
|-------|-------|-------------|
| `move.x` | -1.0 a 1.0 | Lateral: -1 izquierda, +1 derecha. |
| `move.z` | -1.0 a 1.0 | Adelante/atrás: -1 adelante, +1 atrás. |
| `look.x` | -1.0 a 1.0 | Yaw relativo. |
| `look.y` | -1.0 a 1.0 | Pitch relativo. |
| `jump` | bool | Solicitud de salto/vuelo ascendente. |
| `fly` | bool | Toggle de modo vuelo (solo si está habilitado). |
| `place_block` | bool | Colocar bloque donde mira. |
| `break_block` | bool | Romper bloque donde mira. |
| `selected_slot` | 0-8 | Slot activo del inventario. |
| `camera_mode` | 0-2 | Modo de cámara (solo visual). |

El servidor procesa el input en el siguiente tick y aplica física.

#### 3.3.2 `ping`

Para medir latencia.

```json
{
  "type": "ping",
  "client_time": 1752931200.020
}
```

#### 3.3.3 `subscribe_chunks`

Solicita chunks adicionales o cambia el radio de chunks visibles.

```json
{
  "type": "subscribe_chunks",
  "radius": 3,
  "center": { "x": 24.5, "z": 20.5 }
}
```

---

## 4. Canal MCP (`/mcp`)

### 4.1 Transporte

HTTP POST a `/mcp`. Cuerpo JSON-RPC 2.0.

```bash
curl -X POST http://localhost:9000/mcp \
  -H 'Content-Type: application/json' \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"place_block","arguments":{"x":10,"y":25,"z":10,"type":1}}}'
```

### 4.2 Mensajes estándar MCP

#### `initialize`

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "initialize",
  "params": {
    "protocolVersion": "2024-11-05",
    "capabilities": {},
    "clientInfo": { "name": "opencode", "version": "1.0" }
  }
}
```

#### `tools/list`

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "tools/list"
}
```

Respuesta:

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "tools": [
    {
      "name": "place_block",
      "description": "Coloca un bloque en coordenadas absolutas",
      "inputSchema": {
        "type": "object",
        "properties": {
          "x": { "type": "integer" },
          "y": { "type": "integer" },
          "z": { "type": "integer" },
          "type": { "type": "integer", "minimum": 0, "maximum": 10 }
        },
        "required": ["x", "y", "z", "type"]
      }
    }
  ]
}
```

#### `tools/call`

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "tools/call",
  "params": {
    "name": "place_block",
    "arguments": { "x": 10, "y": 25, "z": 10, "type": 1 }
  }
}
```

Respuesta:

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "content": [
    { "type": "text", "text": "{\"success\": true, \"position\": {\"x\": 10, \"y\": 25, \"z\": 10}}" }
  ]
}
```

### 4.3 Catálogo de tools (v0.1)

| Tool | Descripción | Args principales |
|------|-------------|------------------|
| `place_block` | Coloca bloque absoluto | `x, y, z, type` |
| `break_block` | Rompe bloque absoluto | `x, y, z` |
| `get_block` | Consulta bloque | `x, y, z` |
| `get_height` | Altura del terreno | `x, z` |
| `get_player_state` | Estado de jugador | `player_id` |
| `list_players` | Lista jugadores | - |
| `look` | Rota cámara/jugador | `player_id, yaw, pitch` |
| `gamepad_input` | Input virtual para IA | `player_id, input` |
| `attack` | Ataque cuerpo a cuerpo | `player_id, target_id?` |
| `navigate_to` | Navegación A* | `player_id, x, z` |
| `bt_load` | Carga árbol de comportamiento | `tree` |
| `bt_status` | Estado del BT | - |
| `bt_stop` | Detiene BT | - |

### 4.4 Errores MCP

| Código | Significado | Ejemplo |
|--------|-------------|---------|
| `-32600` | Request inválido | JSON mal formado. |
| `-32601` | Método no encontrado | `tools/unknown`. |
| `-32602` | Parámetros inválidos | Faltan args requeridos. |
| `-32603` | Error interno | Excepción no controlada. |
| `WORLD_NOT_INITIALIZED` | Mundo no listo | No se ha generado el mundo. |
| `PLAYER_NOT_FOUND` | Jugador no existe | `player_id` inválido. |
| `BLOCK_INVALID` | Bloque no válido | Tipo fuera de rango. |

---

## 5. Eventos del servidor

Los eventos se envían dentro de `state_update.events`. Son la principal forma de feedback inmediato para agentes y clientes.

### 5.1 Tipos de evento

| Tipo | Campos | Descripción |
|------|--------|-------------|
| `block_placed` | `x, y, z, type, player_id?` | Un bloque fue colocado. |
| `block_broken` | `x, y, z, type, player_id?` | Un bloque fue roto. |
| `damage_taken` | `target, id, amount, source, source_id` | Entidad recibió daño. |
| `entity_died` | `target, id, source, source_id` | Entidad murió. |
| `entity_respawned` | `target, id, position` | Entidad reapareció. |
| `enemy_spawned` | `id, type, position` | Apareció un enemigo. |
| `inventory_changed` | `player_id, slot, item` | Cambió inventario. |
| `tool_result` | `tool, success, error` | Resultado de una tool MCP. |

### 5.2 Ejemplo

```json
{
  "type": "block_broken",
  "x": 10,
  "y": 25,
  "z": 10,
  "type": 1,
  "player_id": 2
}
```

---

## 6. Formato de chunks

### 6.1 Coordenadas

- Mundo: coordenadas absolutas `(x, y, z)` con `y` hacia arriba.
- Chunk: coordenadas de chunk `(cx, cz)` donde `cx = floor(x / CHUNK_SIZE)`.
- Bloque dentro de chunk: `(bx, by, bz)` con `0 <= bx, bz < CHUNK_SIZE`, `0 <= by < WORLD_HEIGHT`.

### 6.2 Serialización `chunk_full`

Opción A (v0.1, simple):

```json
{
  "cx": 0,
  "cz": 0,
  "blocks": [
    [0, 20, 0, 1],
    [1, 20, 0, 1],
    ...
  ]
}
```

Opción B (compacta, futura):

Array de `CHUNK_SIZE * WORLD_HEIGHT * CHUNK_SIZE` bytes en base64, uno por bloque.

### 6.3 Serialización `chunk_deltas`

```json
{
  "0,0": {
    "modified": [
      [10, 20, 10, 1],
      [11, 21, 11, 0]
    ]
  }
}
```

Cada tupla es `[x, y, z, type]`. Coordenadas absolutas del mundo.

---

## 7. Recomendaciones de implementación

### 7.1 En el servidor

- Usar **Starlette** o **FastAPI** para HTTP + WebSocket.
- El game loop debe correr en una tarea aparte, a 20 Hz fijo.
- El WebSocket solo reenvía el estado acumulado en cada tick; no corre física.
- Las tools MCP mutan el estado del servidor; el game loop las aplica en el siguiente tick.

### 7.2 En el cliente

- Recibir `state_update` a 20 Hz.
- Guardar dos estados consecutivos e interpolar visualmente a 60 FPS.
- Enviar `input` a 60 Hz con números de secuencia (`seq`).
- No aplicar física localmente; solo predecir levemente el propio movimiento para reducir latencia percibida.

### 7.3 En agentes MCP

- No enviar input a alta frecuencia: basta con una llamada por decisión.
- Suscribirse a `state_update` vía WebSocket o polling si se necesita feedback continuo.
- Las acciones async (como `navigate_to`) devuelven inmediatamente un `request_id` y luego un evento `tool_result`.

---

## 8. Cambios respecto al protocolo actual (Node)

| Aspecto | Antes (Node) | Ahora (Python) |
|---------|--------------|----------------|
| Fuente de verdad | Navegador | Servidor Python |
| MCP | stdio → bridge → HTTP `/mcp` | HTTP `/mcp` directo + WebSocket MCP |
| Estado | Heartbeat 10 Hz + state_update 1 Hz | state_update 20 Hz con deltas |
| Input de IA | `gamepad_input` relay | `gamepad_input` tool muta estado servidor |
| Input humano | Procesado en navegador | Enviado al servidor, procesado allí |
| Chunks | Generados en navegador | Generados en servidor, enviados por demanda |

---

## 9. Pendientes de definir

1. Serialización binaria eficiente de chunks.
2. Autenticación y rate-limiting para conexiones MCP.
3. Múltiples partidas/rooms simultáneas.
4. Guardado y carga de mundos en disco.
5. Compresión de mensajes WebSocket.

---

## 10. Referencias

- [ADR-002: Migración a servidor Python autoritativo](./adr/002-python-server.md)
- [Plan de migración](./python-server-plan.md)
- Código fuente actual: `js/world.js`, `js/player.js`, `js/enemies.js`, `js/navigation.js`, `js/game-client.js`, `bt-engine.js`, `game-server.js`
