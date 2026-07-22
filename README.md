# VoxelQuest

Un juego de construcción y exploración de mundos voxel con soporte para pantalla partida,
control por IA y protocolo MCP (Model Context Protocol).

## Características

- **Mundo voxel** con generación procedural de terreno
- **Pantalla partida** para 2 jugadores locales
- **Modo solitario** y **coop**
- **Personalización de personajes** con preview 3D
- **Ciclo día/noche** con iluminación dinámica
- **Sistema de bloques** con diferentes tipos
- **Assets de construcción**: ventanas, puertas, muebles, antorchas
- **Inventario completo** con drag & drop y crafteo
- **Enemigos** con IA (zombies, esqueletos, creepers)
- **Física** con derrumbe de bloques
- **Modo vuelo** (doble salto)
- **Soporte gamepad** Xbox 360
- **Control por IA** vía MCP (Model Context Protocol)
- **Gamepad virtual** para control con físicas reales
- **Behavior Trees** para comportamientos autónomos

## Controles

### Jugador 1 (Lado izquierdo)
| Acción | Tecla |
|--------|-------|
| Mover | WASD |
| Mirar | Ratón |
| Romper bloque | Click izquierdo |
| Colocar bloque | Click derecho |
| Saltar | ESPACIO |
| Vuelo | ESPACIO + SHIFT |
| Seleccionar slot | 1-9 |
| Inventario | E |
| Craftear | Q |

### Jugador 2 (Lado derecho)
| Acción | Tecla |
|--------|-------|
| Mover | Flechas |
| Mirar | Ratón (al hacer clic en tu viewport) |
| Romper bloque | Click izquierdo |
| Colocar bloque | Click derecho |
| Saltar | ENTER |
| Vuelo | ENTER + RSHIFT |
| Seleccionar slot | 0-9 |
| Inventario | P |

## Ejecutar

### Opción 1: Servidor Node.js (juego + API)
```bash
cd core/node
npm install
node game-server.js
```
Abre el navegador automáticamente en `http://localhost:9000`.

### Opción 2: Con control por IA (MCP - Stack Node.js)
```bash
# Terminal 1: servidor del juego
cd core/node && node game-server.js

# Terminal 2: adaptador MCP (para opencode o clientes MCP)
cd core/node && node mcp-server.js
```

### Opción 3: Servidor Python (autoritativo)
```bash
cd core/python && uv run python -m server.main
```
Cliente web en `client/index.html`.

### Opción 4: Abrir directamente (sin servidor)
Simplemente abre `core/web/index.html` en tu navegador.

> **Nota:** El modo MCP requiere seleccionar un modo de juego (solitario/cooperativo) en el navegador.

## Arquitectura del Sistema

```
┌─────────────┐   stdio    ┌────────────────┐   WebSocket   ┌──────────────┐
│  opencode   │ ←───────→ │  mcp-server.js  │ ←───────────→ │ game-server  │
│  (cliente   │   MCP      │  (adaptador)    │    JSON-RPC   │  (juego)     │
│   MCP)      │   stdio    │                 │               │              │
└─────────────┘            └────────────────┘               └──────┬───────┘
                                                                   │ WebSocket
                                                                   ▼
                                                           ┌──────────────┐
                                                           │  Navegador   │
                                                           │  (Three.js)  │
                                                           └──────────────┘
```

### Componentes

| Archivo | Función |
|---------|---------|
| `game-server.js` | Sirve el juego (HTTP), WebSocket relay al navegador, API JSON-RPC 2.0, motor BT |
| `mcp-server.js` | Adaptador MCP puro: traduce stdio ↔ WebSocket. Sin lógica de juego |
| `bt-engine.js` | Motor de Árboles de Comportamiento (Behavior Tree) |

## Control por IA (MCP)

El servidor expone ~51 herramientas (tools) vía JSON-RPC 2.0.

### Uso con HTTP directo (scripts)
```bash
curl -X POST http://localhost:9000/mcp -H 'Content-Type: application/json' \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"list_players","arguments":{}}}'
```

### Gamepad virtual (recomendado para mover al P2)
El Jugador 2 solo puede moverse a través del **gamepad virtual**, que simula un mando
Xbox 360. Esto garantiza que todos los movimientos pasen por las físicas reales del juego
(gravedad, colisiones, terreno).

| Método | Descripción |
|--------|-------------|
| `gamepad_connect` | Activa el gamepad virtual para un jugador |
| `gamepad_input` | Inyecta entrada: movimiento, mirada, salto, vuelo, romper/colocar |
| `gamepad_disconnect` | Desactiva el gamepad virtual |

#### Parámetros de gamepad_input
```json
{
  "player_id": 2,
  "input": {
    "move": { "x": 0, "z": -1 },     // x: +/-1 lateral, z: +/-1 adelante/atrás
    "look": { "x": 0.1, "y": 0 },    // x: yaw (giro), y: pitch (elevación)
    "jump": true,                     // salto momentáneo
    "fly": true,                      // activar/desactivar vuelo
    "break": true,                    // romper bloque apuntado
    "place": true                     // colocar bloque apuntado
  }
}
```

### Behavior Tree (BT)
Comportamientos autónomos declarativos en JSON evaluados a 10Hz:

```bash
# Cargar árbol de ejemplo (si vida<5 huye, si enemigos cerca ataca, sino idle)
curl -X POST http://localhost:9000/mcp -H 'Content-Type: application/json' \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"bt_load_example","arguments":{}}}'

# Ver estado y blackboard
curl -X POST http://localhost:9000/mcp -H 'Content-Type: application/json' \
  -d '{"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"bt_status","arguments":{}}}'

# Detener
curl -X POST http://localhost:9000/mcp -H 'Content-Type: application/json' \
  -d '{"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"bt_stop","arguments":{}}}'
```

### Navegación A*
```bash
curl -X POST http://localhost:9000/mcp -H 'Content-Type: application/json' \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"moverse_a","arguments":{"player_id":2,"x":30,"z":30}}}'
```

### Combate
```bash
curl -X POST http://localhost:9000/mcp -H 'Content-Type: application/json' \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"attack","arguments":{"player_id":2}}}'
```

### Construcción
```bash
# Colocar casa predefinida
curl -X POST ... -d '{"name":"build_structure","arguments":{"structure":"house","x":20,"y":30,"z":20}}'

# Llenar área
curl -X POST ... -d '{"name":"fill_area","arguments":{"x":10,"z":10,"width":5,"depth":5,"type":3}}'
```

> Referencia completa de herramientas: [`docs/MANUAL_MCP.md`](docs/MANUAL_MCP.md)

## Variables del Blackboard (BT)

Actualizadas cada 100ms desde el navegador:

| Variable | Descripción |
|----------|-------------|
| `self_vida` | Vida del Jugador 2 |
| `self_x`, `self_z` | Posición del Jugador 2 |
| `p1_x`, `p1_z`, `p1_y` | Posición del Jugador 1 |
| `hay_enemigos_cerca` | ¿Hay enemigos en rango? |
| `target_enemigo_id` | ID del enemigo más cercano |
| `target_enemigo_x`, `target_enemigo_z` | Posición del enemigo más cercano |

## Scripts de Agente

En `scripts/`:

| Script | Descripción |
|--------|-------------|
| `chase.py` | Persigue al Jugador 1 |
| `evade.py` | Huye del monstruo más cercano (~100s) |
| `evade_chase.py` | Bucle infinito evade+chase con detección de obstáculos |
| `update_changelog.py` | Clasifica commits para CHANGELOG.md |

## Tipos de Bloques

| ID | Bloque | Color |
|----|--------|-------|
| 0 | Aire | — |
| 1 | Hierba | Verde |
| 2 | Tierra | Marrón |
| 3 | Piedra | Gris |
| 4 | Madera | Marrón oscuro |
| 5 | Hojas | Verde oscuro |
| 6 | Arena | Beige |
| 7 | Agua | Azul |
| 8 | Roca | Gris oscuro |
| 9 | Tablones | Beige claro |
| 10 | Bedrock | Negro (irrompible) |

## Estructura del Proyecto

```
core/                          # Código del juego
├── shared/tools/              # Contrato MCP compartido
│   └── definitions.json       # Tool definitions (ambos servidores)
├── node/                      # Stack Node.js
│   ├── game-server.js         # Servidor (web + WS + API JSON-RPC)
│   ├── mcp-server.js          # Adaptador stdio MCP
│   ├── bt-engine.js           # Behavior Tree engine
│   └── web/                   # Cliente web completo (18 JS)
│       ├── index.html
│       ├── css/
│       └── js/
├── python/                    # Stack Python (autoritativo)
│   ├── server/                # FastAPI (engine, mcp, ws, bt)
│   ├── client/                # Cliente thin (7 JS)
│   ├── scripts/               # chase, evade, build...
│   ├── training/              # Episodios de entrenamiento
│   ├── pyproject.toml
│   └── run.sh
├── docs/                      # Documentación compartida
│   ├── proposals/             # Propuestas en formato human/agent
│   └── MANUAL_MCP.md
├── CHANGELOG.md
└── README.md
```

## Notas

- El juego usa **Three.js r128** desde CDN
- El mundo se genera proceduralmente usando **ruido Perlin**
- Los enemigos aparecen durante la noche
- El crafteo es automático al tener los materiales
- El servidor requiere **Node.js 14+**
- Las herramientas de movimiento (move_player, teleport, jump, fly, move_relative)
  están deshabilitadas. P2 solo se mueve mediante gamepad virtual (físicas reales).
- `@modelcontextprotocol/sdk` solo es necesario para `mcp-server.js`. El juego base
  funciona sin él.
