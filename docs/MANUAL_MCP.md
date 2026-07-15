# VoxelQuest - Manual de Uso MCP para Terceros

## Tabla de Contenidos

1. [Introducción](#introducción)
2. [Requisitos Previos](#requisitos-previos)
3. [Instalación y Arranque](#instalación-y-arranque)
4. [Arquitectura del Sistema](#arquitectura-del-sistema)
5. [Conexión al Servidor](#conexión-al-servidor)
6. [Referencia de Herramientas MCP](#referencia-de-herramientas-mcp)
7. [Ejemplos de Uso](#ejemplos-de-uso)
8. [Modo de Aprobación](#modo-de-aprobación)
9. [Estructuras Predefinidas](#estructuras-predefinidas)
10. [Solución de Problemas](#solución-de-problemas)

---

## Introducción

VoxelQuest es un juego de construcción y exploración de mundos voxel que integra un **servidor MCP (Model Context Protocol)**. Este servidor permite que agentes de IA controlen jugadores remotamente, realizando acciones como moverse, construir, explorar y interactuar con el mundo.

### Capacidades principales

- Controlar jugadores existentes o crear nuevos avatares bajo control IA
- Mover jugadores (teletransportación y movimiento relativo)
- Construir y destruir bloques en el mundo
- Consultar el estado del mundo y entorno
- Ejecutar comandos en la consola del juego
- Sistema de aprobación para control humano opcional

---

## Requisitos Previos

- **Node.js** 14 o superior
- **npm** para instalar dependencias
- Un navegador web moderno (Chrome, Firefox, Edge)
- (Opcional) Un agente MCP compatible para conectar

---

## Instalación y Arranque

### 1. Instalar dependencias

```bash
cd minecraft-clone
npm install
```

### 2. Iniciar el servidor

El servidor unificado sirve tanto el juego como la API MCP:

```bash
node voxelquest-server.js
```

El servidor arranca en el puerto **9000** por defecto. Verás en consola:

```
🎮 VoxelQuest - Servidor unificado v4.0
   Juego:     http://localhost:9000
   MCP API:   http://localhost:9000/mcp
   WebSocket: ws://localhost:9000
   Health:    http://localhost:9000/health
   Tools:     http://localhost:9000/tools
```

### 3. Abrir el juego

El navegador se abrirá automáticamente. Si no, visita `http://localhost:9000`.

---

## Arquitectura del Sistema

```
┌─────────────────────────────────────────────────────────┐
│                    Navegador (Juego)                     │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐  │
│  │   Jugador   │    │    Mundo    │    │ Game Client │  │
│  │  (Player)   │    │   (World)   │    │  (WebSocket)│  │
│  └──────┬──────┘    └──────┬──────┘    └──────┬──────┘  │
│         │                  │                  │         │
│         └──────────────────┴──────────────────┘         │
└─────────────────────────────┬───────────────────────────┘
                              │ WebSocket
                              ▼
┌─────────────────────────────────────────────────────────┐
│               Servidor MCP (voxelquest-server.js)               │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐  │
│  │ HTTP API    │    │  WebSocket  │    │  Handlers   │  │
│  │  /mcp       │    │   Server    │    │    MCP      │  │
│  └─────────────┘    └─────────────┘    └─────────────┘  │
└─────────────────────────────────────────────────────────┘
                              ▲
                              │ HTTP POST
                              │
┌─────────────────────────────┴───────────────────────────┐
│              Cliente MCP (Agente IA / Script)             │
│         Envía comandos JSON a http://localhost:9000/mcp  │
└─────────────────────────────────────────────────────────┘
```

### Flujo de comunicación

1. El **cliente MCP** envía un POST JSON a `http://localhost:9000/mcp`
2. El **servidor MCP** procesa el comando y actualiza el estado del juego
3. El servidor envía la actualización al **juego** vía WebSocket
4. El juego ejecuta la acción y responde con el resultado
5. El servidor retorna la respuesta al cliente MCP

---

## Conexión al Servidor

### Método HTTP (recomendado)

Envía comandos POST al endpoint `/mcp`:

```
POST http://localhost:9000/mcp
Content-Type: application/json

{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "tools/call",
  "params": {
    "name": "nombre_del_metodo",
    "arguments": { ... }
  }
}
```

### Método WebSocket (en tiempo real)

Conecta vía WebSocket para comunicación bidireccional:

```javascript
const ws = new WebSocket('ws://localhost:9000');
ws.onopen = () => {
  ws.send(JSON.stringify({
    jsonrpc: '2.0',
    id: 1,
    method: 'tools/call',
    params: { name: 'list_players', arguments: {} }
  }));
};
ws.onmessage = (event) => {
  const response = JSON.parse(event.data);
  console.log(response);
};
```

### Verificar conexión

```bash
curl http://localhost:9000/health
# Respuesta: {"status":"ok","players":2}
```

---

## Referencia de Herramientas MCP

### Configuración

| Método | Descripción | Parámetros |
|--------|-------------|------------|
| `get_config` | Obtiene configuración actual | ninguno |
| `set_approval_mode` | Cambia modo de aprobación | `mode`: "auto" o "human" |

### Gestión de Jugadores

| Método | Descripción | Parámetros |
|--------|-------------|------------|
| `list_players` | Lista todos los jugadores | ninguno |
| `get_player_state` | Estado detallado de un jugador | `player_id` |
| `create_avatar` | Crea nuevo avatar controlado por IA | `name`, `gender`, `hairStyle`, `hairColor`, `eyeColor`, `shirtColor`, `pantsColor`, `spawnX`, `spawnZ` |
| `get_pending_requests` | Solicitudes de aprobación pendientes | ninguno |
| `approve_request` | Aprobar/rechazar solicitud | `approvalId`, `approved` |

### Movimiento

| Método | Descripción | Parámetros |
|--------|-------------|------------|
| `move_player` | Teletransportar jugador | `player_id`, `x`, `y`, `z` |
| `move_relative` | Mover relativo a dirección actual | `player_id`, `forward`, `backward`, `left`, `right`, `distance` |
| `jump` | Hacer saltar al jugador | `player_id`, `height` (default: 3) |

### Vuelo

| Método | Descripción | Parámetros |
|--------|-------------|------------|
| `toggle_fly` | Activar/desactivar modo vuelo | `player_id` |
| `fly_up` | Volar hacia arriba | `player_id`, `distance` |
| `fly_down` | Volar hacia abajo | `player_id`, `distance` |

### Cámara

| Método | Descripción | Parámetros |
|--------|-------------|------------|
| `look` | Rotar cámara del jugador | `player_id`, `yaw`, `pitch`, `yaw_delta`, `pitch_delta` |
| `get_rotation` | Obtener rotación actual | `player_id` |
| `toggle_camera` | Alternar modo cámara | `player_id` |

### Inventario

| Método | Descripción | Parámetros |
|--------|-------------|------------|
| `select_slot` | Seleccionar slot específico | `player_id`, `slot` (0-8) |
| `next_slot` | Slot siguiente | `player_id` |
| `prev_slot` | Slot anterior | `player_id` |

### Bloques

| Método | Descripción | Parámetros |
|--------|-------------|------------|
| `place_block` | Colocar bloque en coordenada exacta | `x`, `y`, `z`, `type` |
| `place_block_as_player` | Colocar bloque donde mira el jugador | `player_id`, `type` |
| `break_block` | Romper bloque en coordenada | `x`, `y`, `z` |
| `break_block_as_player` | Romper bloque donde mira el jugador | `player_id` |
| `get_block` | Obtener tipo de bloque | `x`, `y`, `z` |
| `get_height` | Obtener altura del terreno | `x`, `z` |
| `get_blocks_in_area` | Obtener bloques en volumen | `x1`, `y1`, `z1`, `x2`, `y2`, `z2` |

### Construcción

| Método | Descripción | Parámetros |
|--------|-------------|------------|
| `build_structure` | Construir estructura predefinida | `x`, `y`, `z`, `structure` (house, tower, farm) |
| `list_structures` | Listar estructuras disponibles | ninguno |
| `create_wall` | Crear pared | `x`, `z`, `length`, `height`, `direction`, `type`, `baseY` |
| `create_floor` | Crear suelo | `x`, `z`, `width`, `depth`, `type`, `baseY` |
| `fill_area` | Llenar área con bloques | `x`, `z`, `width`, `depth`, `height`, `type`, `baseY` |
| `flat_terrain` | Aplanar terreno | `x`, `z`, `width`, `depth`, `height`, `baseY` |
| `plant_tree` | Plantar árbol | `x`, `z` |

### Mundo

| Método | Descripción | Parámetros |
|--------|-------------|------------|
| `get_world_info` | Información del mundo | ninguno |

### Visión y Percepción

| Método | Descripción | Parámetros |
|--------|-------------|------------|
| `get_view` | Bloque que mira el jugador | `player_id`, `distance` |
| `get_nearby_blocks` | Bloques cercanos al jugador | `player_id`, `radius` |
| `get_nearby_entities` | Entidades cercanas (otros jugadores, enemigos) | `player_id`, `radius` |
| `get_environment` | Información del entorno inmediato | `player_id` |
| `get_top_down_view` | Vista aérea del terreno | `player_id`, `radius` |
| `get_camera_matrix` | Matriz de bloques en visión de cámara | `player_id`, `width`, `height`, `depth` |

### Utilidades

| Método | Descripción | Parámetros |
|--------|-------------|------------|
| `list_block_types` | Listar tipos de bloques | ninguno |
| `list_avatar_colors` | Listar colores de avatar | ninguno |
| `send_message` | Enviar mensaje de chat | `player_id`, `message` |
| `get_inventory` | Obtener inventario del jugador | `player_id` |
| `add_item` | Añadir item al inventario | `player_id`, `type`, `count` |

---

## Ejemplos de Uso

### Listar jugadores

```bash
curl -X POST http://localhost:9000/mcp \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"list_players","arguments":{}}}'
```

### Mover jugador 1 a posición específica

```bash
curl -X POST http://localhost:9000/mcp \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"move_player","arguments":{"player_id":1,"x":50,"y":30,"z":50}}}'
```

### Crear avatar controlado por IA

```bash
curl -X POST http://localhost:9000/mcp \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"create_avatar","arguments":{"name":"Explorador_IA","gender":"female","hairStyle":"long","hairColor":0x8B4513,"eyeColor":0x228B22,"shirtColor":0x4169E1,"pantsColor":0x2F4F4F,"spawnX":20,"spawnZ":20}}}'
```

### Construir una casa

```bash
curl -X POST http://localhost:9000/mcp \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"build_structure","arguments":{"x":30,"y":20,"z":30,"structure":"house"}}}'
```

### Obtener vista del jugador

```bash
curl -X POST http://localhost:9000/mcp \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"get_top_down_view","arguments":{"player_id":1,"radius":10}}}'
```

### Ejemplo en Python

```python
import requests
import json

MCP_URL = "http://localhost:9000/mcp"

def mcp_call(name, arguments=None):
    response = requests.post(MCP_URL, json={"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": {"name": name, "arguments": arguments or {}}})
    return response.json()

# Listar jugadores
players = mcp_call("list_players")
print(json.dumps(players, indent=2))

# Mover jugador 2 hacia adelante
mcp_call("move_relative", {"player_id": 2, "forward": True, "distance": 5})

# Construir torre
mcp_call("build_structure", {"x": 100, "y": 20, "z": 100, "structure": "tower"})
```

### Ejemplo en JavaScript

```javascript
async function mcpCall(name, arguments = {}) {
  const response = await fetch('http://localhost:9000/mcp', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ jsonrpc: '2.0', id: 1, method: 'tools/call', params: { name, arguments } })
  });
  return response.json();
}

// Crear avatar y moverlo
async function crearExplorador() {
  const result = await mcpCall('create_avatar', {
    name: 'Explorador',
    gender: 'male',
    spawnX: 50,
    spawnZ: 50
  });
  
  console.log(`Avatar creado: ID ${result.playerId}`);
  
  // Mover el nuevo avatar
  await mcpCall('move_player', {
    player_id: result.playerId,
    x: 60,
    y: 25,
    z: 60
  });
}
```

---

## Modo de Aprobación

El sistema tiene dos modos de control:

### Modo Auto (por defecto)

Las acciones se ejecutan automáticamente sin confirmación humana.

```bash
curl -X POST http://localhost:9000/mcp \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"set_approval_mode","arguments":{"mode":"auto"}}}'
```

### Modo Humano

Requiere aprobación de un jugador humano antes de ejecutar acciones sensibles (como crear avatares).

```bash
# Activar modo humano
curl -X POST http://localhost:9000/mcp \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"set_approval_mode","arguments":{"mode":"human"}}}'

# Cuando un agente IA quiere crear un avatar, queda en cola
# El humano puede aprobarlo:
curl -X POST http://localhost:9000/mcp \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"approve_request","arguments":{"approvalId":"1234567890","approved":true}}}'
```

---

## Estructuras Predefinidas

| ID | Nombre | Bloques | Descripción |
|----|--------|---------|-------------|
| `house` | Casa pequeña | ~50 | Casa de 4x4 con paredes y techo |
| `tower` | Torre | ~80 | Estructura vertical alta |
| `farm` | Granja | ~40 | Terreno cercado para cultivo |

### Tipos de bloques disponibles

| ID | Nombre |
|----|--------|
| 0 | Aire |
| 1 | Hierba |
| 2 | Tierra |
| 3 | Piedra |
| 4 | Madera |
| 5 | Hojas |
| 6 | Arena |
| 7 | Agua |
| 8 | Roca |
| 9 | Tablones |
| 10 | Bedrock |

---

## Solución de Problemas

### El servidor no arranca

**Error: `EADDRINUSE`** - El puerto 9000 está en uso.

```bash
# Encontrar proceso en el puerto
lsof -i :9000

# Matar el proceso
kill -9 <PID>

# O usar otro puerto
PORT=9001 node voxelquest-server.js
```

### El juego no recibe comandos MCP

1. Verificar que el juego esté abierto en el navegador
2. Verificar conexión WebSocket:
   ```bash
   curl http://localhost:9000/health
   ```
3. Revisar consola del navegador (F12) para errores

### Error "Jugador no encontrado"

Asegúrate de que el `player_id` sea correcto. Los jugadores locales son 1 y 2. Los avatares IA comienzan desde 3.

### Error "Mundo no inicializado"

El mundo se inicializa cuando el juego comienza. Asegúrate de haber seleccionado un modo de juego (solitario o cooperativo).

---

## Endpoints HTTP Disponibles

| Método | URL | Descripción |
|--------|-----|-------------|
| GET | `/health` | Estado del servidor |
| GET | `/tools` | Lista de herramientas MCP disponibles (JSON-RPC 2.0) |
| POST | `/mcp` | Ejecutar comando MCP |
| GET | `/*` | Archivos estáticos del juego |

---

## Notas para Desarrolladores

- El servidor usa `ws` (WebSocket) para comunicación en tiempo real con el juego
- El estado del juego se mantiene sincronizado entre servidor MCP y navegador
- Los comandos MCP son procesados de forma asíncrona
- El servidor incluye CORS habilitado para desarrollo local
- La estructura del proyecto está en `js/` para el cliente y raíz para el servidor
