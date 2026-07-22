# Análisis Arquitectónico - VoxelQuest

**Fecha:** 2026-07-22  
**Estado:** Diagnóstico completo

## Situación actual: 3 sistemas paralelos

### Sistema 1: Web Standalone
- **Ubicación:** `minecraft-clone/index.html` + `js/` (18 módulos)
- **Motor de juego:** Browser (world, physics, enemies, player, building, sound, UI completo)
- **Cliente:** `index.html` con features completas
- **MCP:** No
- **Servidor:** Solo HTTP estático (`server.py` o `run.sh`)
- **Estado:** Maduro, feature-complete

### Sistema 2: Node.js Server
- **Ubicación:** `game-server.js` + `mcp-server.js` + `bt-engine.js`
- **Motor de juego:** Browser (relay WebSocket)
- **Cliente:** Mismo `index.html` que Sistema 1
- **MCP:** Sí (~51 tools via `mcp-server.js` adaptador stdio)
- **Servidor:** Node.js en puerto 9000
- **Estado:** Funcional, pero duplica lógica del browser

### Sistema 3: Python Server
- **Ubicación:** `server/` + `client/`
- **Motor de juego:** Server-side autoritativo (FastAPI, world, physics, entities, navigation, noise, BT)
- **Cliente:** `client/index.html` (7 módulos JS, thin client)
- **MCP:** Sí (~14 tools integrados nativamente)
- **Servidor:** Python FastAPI en puerto 9000
- **Estado:** Reescritura parcial, cliente incompleto

## Problemas identificados

### 1. Lógica triplicada
El motor de juego existe en:
- JS-browser: `js/world.js`, `js/physics.js`, `js/enemies.js`, `js/player.js`, etc.
- Python: `server/engine/world.py`, `physics.py`, `entities.py`, `navigation.py`
- Node.js: relay pasivo (no tiene lógica propia)

Cada cambio de gameplay requiere replicar en 2-3 sitios.

### 2. Dos clientes web incompatibles
- `index.html`: 18 scripts, sound, inventory, player models, building, UI completo
- `client/index.html`: 7 scripts, renderizado thin, sin sound/inventory/building

El cliente Python está muy por detrás en features.

### 3. Conflicto de puertos
Ambos servidores (Node.js y Python) compiten por el puerto 9000.

### 4. Dos filosofías opuestas
- **Node.js:** El navegador es la fuente de verdad, el servidor es un relay
- **Python:** El servidor es autoritativo, el cliente solo renderiza

### 5. Scripts acoplados al API Node.js
Los scripts en `scripts/` (chase.py, evade.py, build_house.py, etc.) usan métodos MCP como:
- `get_top_down_view`, `get_nearby_entities`, `get_environment`
- `gamepad_connect`, `break_block_as_player`, `teleport`, `get_height`

Estos tools **solo existen en el servidor Node.js** (~51 tools). El servidor Python solo tiene ~14 tools. Si mañana solo corre Python, la mayoría de scripts dejan de funcionar.

### 6. Mantenimiento insostenible
- ~1196 líneas en `game-server.js`
- ~428 líneas en `server/mcp/server.py`
- Lógica duplicada en múltiples sitios
- Sin contrato compartido de tools

## Métricas comparativas

| Aspecto | Web Standalone | Node.js Server | Python Server |
|---------|---------------|----------------|---------------|
| Módulos JS cliente | 18 | 18 (mismo) | 7 |
| Tools MCP | 0 | ~51 | ~14 |
| Motor de juego | Browser | Browser (relay) | Server-side |
| Física | JS (`physics.js`) | JS (browser) | Python (`physics.py`) |
| Enemigos | JS (`enemies.js`) | JS (browser) | Python (`entities.py`) |
| Navegación A* | JS (`navigation.js`) | JS (browser) | Python (`navigation.py`) |
| Behavior Tree | No | Sí (`bt-engine.js`) | Sí (`bt/engine.py`) |
| Sound | Sí (`sound.js`) | Sí (browser) | No |
| Inventory | Sí (`inventory.js`) | Sí (browser) | No |
| Building | Sí (`building.js`) | Sí (browser) | No |
| Player models | Sí (`playermodel.js`) | Sí (browser) | No |
| Puerto | N/A | 9000 | 9000 |

## Conclusión

La arquitectura actual es insostenible. Hay tres sistemas paralelos con lógica duplicada, clientes incompatibles, y scripts acoplados a un API específico. Se necesita una reorganización que:

1. Separe claramente los dos stacks (Node.js y Python)
2. Establezca un contrato compartido de tools MCP
3. Permita que cada stack evolucione independientemente
4. Facilite la migración gradual de Node.js a Python si se desea
