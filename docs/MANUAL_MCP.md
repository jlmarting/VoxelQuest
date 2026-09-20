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
| `build_csg` | Aplicar árbol CSG declarativo (grid o sculpture) | `tree`, `position`, `target`, `resolution`, `color`, `material` |
| `preview_csg` | Dry-run de build_csg (métricas sin tocar el mundo) | `tree`, `target`, `resolution`, `color`, `material` |
| `list_csg_structures` | Listar estructuras CSG nombradas | ninguno |
| `build_csg_named` | Aplicar estructura CSG nombrada | `name`, `position`, `target`, `resolution`, `color`, `material` |

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

## Estructuras Declarativas CSG

El stack Python expone un **lenguaje declarativo CSG** (Constructive Solid Geometry) para construir estructuras como datos, sin generar scripts. Un árbol CSG se compone de primitivas, operaciones booleanas, transformaciones y repeticiones. Ver `docs/LEARN-csg.md` para el concepto.

### Primitivas

| `op` | Parámetros | Descripción |
|---|---|---|
| `box` | `size: [w,h,d]`, `material` | Caja centrada en el origen |
| `sphere` | `radius`, `material` | Esfera |
| `cylinder` | `radius`, `height`, `material` | Cilindro vertical |
| `pyramid` | `base` (int o `[w,d]`), `height`, `material` | Pirámide |

### Operaciones y transformaciones

| `op` | Parámetros | Descripción |
|---|---|---|
| `union` | `children` (≥2) | Une; materiales posteriores sobrescriben |
| `subtract` | `children` (≥2) | Elimina el segundo operando del primero |
| `intersect` | `children` (≥2) | Conserva solo el solape (material del primero) |
| `at` | `at: [dx,dy,dz]`, `children` | Traslada |
| `rotate` | `axis` (x/y/z), `angle` (múltiplos de 90°), `children` | Rota |
| `array` | `count`, `step: [dx,dy,dz]`, `children` | Repite linealmente |
| `radial` | `count`, `radius`, `children` | Repite alrededor del eje Y |

### Materiales

- **target=grid**: nombre (`"cobblestone"`, `"planks"`, `"red_brick"`...) o id (0-13).
- **target=sculpture**: color (int) + `resolution` (1/2/4/8), reutiliza el motor de esculturas subvoxel.

### Ejemplo

```json
{
  "op": "subtract",
  "children": [
    {"op": "box", "size": [7, 3, 7], "material": "cobblestone"},
    {"op": "box", "size": [5, 3, 5], "material": "air"}
  ]
}
```

```bash
# Dry-run (no toca el mundo)
curl -X POST http://localhost:9000/mcp -H 'Content-Type: application/json' \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"preview_csg","arguments":{"tree":{"op":"box","size":[3,3,3],"material":"stone"}}}}'

# Aplicar
curl -X POST http://localhost:9000/mcp -H 'Content-Type: application/json' \
  -d '{"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"build_csg","arguments":{"tree":{"op":"box","size":[3,3,3],"material":"stone"},"position":[10,20,10]}}}'

# Estructuras nombradas
curl -X POST http://localhost:9000/mcp -H 'Content-Type: application/json' \
  -d '{"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"list_csg_structures","arguments":{}}}'
curl -X POST http://localhost:9000/mcp -H 'Content-Type: application/json' \
  -d '{"jsonrpc":"2.0","id":4,"method":"tools/call","params":{"name":"build_csg_named","arguments":{"name":"house","position":[10,20,10]}}}'
```

### Biblioteca de estructuras

`core/shared/structures/*.json` contiene estructuras nombradas reutilizables:

| Archivo | Descripción |
|---|---|
| `house.json` | Casa 7x7 con puerta, interior hueco y techo con voladizo |
| `tower.json` | Torre de vigilancia con almenas |
| `castle_walls.json` | Sección de muralla con merlones y torreones |
| `cathedral_nave.json` | Nave central gótica con columnas y bóveda |

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

---

## Objetos y física (categoría `objects`)

La categoría `objects` introduce un subsistema de **objetos móviles** gestionables
vía MCP con física de colisiones, movimientos programables, destrucción reactiva
y esculturas subvoxel. Disponible **solo en el stack Python** (`servers: ["python"]`).

### Modelo

Un `MobileObject` tiene: `id`, `kind` (`box`/`sphere`/`sculpture`/`projectile`/`vehicle`),
`position` (centro, en unidades de voxel), `velocity`, `rotation`, `scale` (admite
fracciones para subvoxel), `mass` (0 = estático), `restitution`, `health`,
`destructible`, `fragile` (umbral de energía cinética para romperse por colisión),
`collision_group`/`collision_mask` (bitmasks; dos objetos colisionan si cada uno
tiene al grupo del otro en su mask), `anchored` (no responde a física), `owner_id`,
`color` (RGB entero), `motion`, `shape`, `expire_at` (segundos de vida), y
`damage_on_impact`/`destroy_on_impact` (para proyectiles).

### Tools de creación y consulta

| Tool | Descripción |
|------|--------------|
| `create_object` | Crear un MobileObject. Requeridos: `kind`, `position`. |
| `create_sculpture` | Wrapper para esculturas subvoxel (generador o voxels explícitos). |
| `list_objects` | Listar objetos activos. `filter` opcional (`kind`, `owner_id`, …). |
| `get_object` | Estado completo de un objeto. |
| `update_object` | Modificar propiedades en caliente (`patch`). |
| `destroy_object` | Destrucción manual inmediata. Emite `object_destroyed`. |
| `damage_object` | Aplicar daño a un objeto destruible. Si `health <= 0`, se destruye. |

### Tools de movimiento

`move_object` asigna un motion genérico. Hay presets de atajo:

| Preset | Tipo de motion interno | Notas |
|--------|------------------------|------|
| `move_linear` | `dynamic` sin gravedad | Línea recta con `velocity`. |
| `move_orbit` | `orbit` | `center` + `radius` + `axis` + `angular_speed`. |
| `move_bounce` | `waypoints` con `loop` | Rebote entre `a` y `b` a `speed`. |
| `move_projectile` | `dynamic` con gravedad | Promociona a `projectile`, marca `destructible`, guarda `damage_on_impact`/`destroy_on_impact`. |
| `move_rotate` | `rotate` | Rotación continua con `angular_velocity`. |
| `stop_motion` | — | Detiene todo (motion + velocity). |
| `apply_impulse` | — | `v += impulse / mass`. Anula motion cinemático. |

**Motions cinemáticos** (`waypoints`/`orbit`/`parametric`/`rotate`): la posición la
fija el motion cada tick; la física de colisión contra el voxel grid **no** aplica
(el objeto no cae). **`dynamic`**: la física integra velocidad + gravedad y resuelve
colisiones contra el grid. Un objeto **sin motion** y con `mass > 0` cae por gravedad.

### Movimientos paramétricos (seguridad)

El motion `parametric` evalúa expresiones `x(t)`, `y(t)`, `z(t)` con un **namespace
restringido**: `sin`, `cos`, `tan`, `sqrt`, `pi`, `abs`, `min`, `max`, `t` y **sin
builtins**. Si una expresión falla (sintaxis o intento de acceso a builtins), el
motion se anula silenciosamente para no spamear errores. Esto mitiga el riesgo de
`eval()` pero **solo se debe usar en stack Python controlado**, no exponer a
clientes no confiables.

### Ejemplos

```bash
# Crear una caja que cae por gravedad y reposa en el suelo
curl -X POST http://localhost:9000/mcp -H 'Content-Type: application/json' \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"create_object","arguments":{"kind":"box","position":[10,40,10],"mass":1,"color":16744448}}}'

# Crear un proyectil que vuela y expira a los 3s
curl -X POST http://localhost:9000/mcp -H 'Content-Type: application/json' \
  -d '{"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"create_object","arguments":{"kind":"projectile","position":[0,30,0],"velocity":[5,10,0],"expire_at":3,"damage_on_impact":5}}'

# Hacer orbitar una caja
curl -X POST http://localhost:9000/mcp -H 'Content-Type: application/json' \
  -d '{"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"move_orbit","arguments":{"object_id":1,"center":[10,35,10],"radius":5,"axis":"y","angular_speed":0.5}}}'

# Crear una escultura esfera de subvoxels
curl -X POST http://localhost:9000/mcp -H 'Content-Type: application/json' \
  -d '{"jsonrpc":"2.0","id":4,"method":"tools/call","params":{"name":"create_sculpture","arguments":{"position":[20,40,20],"resolution":4,"generator":"sphere","params":{"radius":1.5,"color":16744576}}}}'

# Dañar un objeto hasta destruirlo
curl -X POST http://localhost:9000/mcp -H 'Content-Type: application/json' \
  -d '{"jsonrpc":"2.0","id":5,"method":"tools/call","params":{"name":"damage_object","arguments":{"object_id":2,"amount":100}}}'
```

### Eventos al cliente

El `state_update` incluye ahora `objects[]` (lista de objetos serializados) y
eventos adicionales en `events[]`:

| Evento | Campos | Cuándo |
|--------|--------|--------|
| `object_collided` | `id`, `other` (`{kind,id}`), `normal`, `depth`, `impact_speed` | Colisión obj↔obj. |
| `object_destroyed` | `id`, `cause` (`collision`/`damage`/`expire`/`manual`), `fx` (`explosion_small`/`break`/`poof`), `position`, `kind` | Destrucción. |
| `object_damaged` | `id`, `amount`, `source_id`, `health_remaining` | Daño aplicado. |
| `entity_damaged` | `target`=`entity`, `id`, `amount`, `by_object` | Proyectil impacta entidad. |

El cliente (`core/web/js/objects.js`) renderiza objetos con `THREE.Mesh`
(box/sphere/vehicle/projectile) o `THREE.InstancedMesh` agrupado por color
(sculpture), y lanza FX visuales (explosión/poof) al recibir `object_destroyed`.

### Límites

- `MAX_OBJECTS = 100` (configurable en `constants.py`).
- `MAX_SCULPTURE_VOXELS = 4096` por escultura.
- `SUBVOXEL_MIN_SIZE = 0.125` (resolution 8).
- Colisión obj↔obj: broad-phase con grid espacial (celda 2 voxels) → O(n) esperado.
- Substepping anti-tunneling: hasta 8 substeps por tick, desplazamiento por substep
  ≤ mitad del tamaño del objeto.

### Archivos relevantes

| Archivo | Rol |
|---------|-----|
| `core/python/server/engine/objects.py` | `MobileObject`, `ObjectManager`, `Motion`, generadores de escultura. |
| `core/python/server/engine/physics.py` | `update_object`, `resolve_object_collisions`, narrow-phase box/sphere, `resolve_collision` impulsivo. |
| `core/python/server/engine/game_loop.py` | Integra `ObjectManager` en el tick y en `state_update`. |
| `core/python/server/mcp/server.py` | Handlers `tool_create_object` … `tool_create_sculpture`. |
| `core/shared/tools/definitions.json` | Contrato: 15 tools con `category: "objects"`. |
| `core/web/js/objects.js` | `ObjectRenderer` (render + FX). |
| `core/web/js/server-bridge.js` | Aplica `state.objects[]` y eventos al cliente. |
