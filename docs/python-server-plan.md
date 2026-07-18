# Plan de migración a servidor Python autoritativo

**Rama:** `feat/python-server`  
**Fecha:** 2026-07-18  
**ADR relacionado:** [ADR-002: Migración a servidor Python autoritativo](./adr/002-python-server.md)

---

## Objetivos

1. Convertir VoxelQuest en una aplicación cliente-servidor donde el servidor Python sea la fuente de verdad.
2. Exponer el juego como servidor Web MCP para que cualquier cliente (opencode, scripts Python, dashboards) pueda conectarse.
3. Reducir el cliente web a un renderizador ligero de Three.js + input humano.
4. Facilitar el entrenamiento de agentes, tests de regresión y reproducibilidad.
5. Preservar el modo split-screen local (`coop`) y habilitar un futuro coop remoto.

---

## Criterios de éxito

- El juego es jugable completamente desde el navegador conectado al servidor Python.
- opencode puede controlar el juego vía Web MCP sin `mcp-server.js` de stdio.
- Se pueden ejecutar tests del motor (pathfinding, física, combate) sin abrir navegador.
- El servidor puede correr headless y aceptar conexiones de agentes.
- El renderizado se mantiene fluido (≥30 FPS) con interpolación básica.
- El modo `coop` sigue siendo split-screen local por defecto (servidor en `localhost`).

---

## Fases

### Fase 0: Preparación (1-2 semanas)

**Metas**
- Definir contrato de mensajes entre cliente y servidor.
- Establecer estructura de carpetas del servidor Python.
- Crear tests de regresión del motor actual en JS.
- Documentar constantes críticas: tipos de bloques, física, parámetros de enemigos.

**Entregables**
- `docs/python-server-protocol.md`: formato de mensajes WS y HTTP.
- `server/` creado con módulos base.
- `tests/` con primeros tests de colisiones y pathfinding en JS (referencia).

**Punto de no retorno:** ninguno, aún es reversible.

---

### Fase 1: Extraer simulación pura en JavaScript (2-3 semanas)

**Metas**
- Separar en el cliente entre lógica de juego y representación visual.
- Asegurar que `World`, `Physics`, `Entities` no dependan de Three.js.
- Preparar el terreno para un port mecánico a Python.

**Entregables**
- `js/engine/world.js`: chunks, bloques, terreno sin render.
- `js/engine/physics.js`: colisiones y movimiento puro.
- `js/engine/entities.js`: jugadores y enemigos puros.
- `js/engine/navigation.js`: A* puro.
- Tests en `tests/js-engine/` que validen el comportamiento actual.

**Punto de no retorno:** el motor JS puro debe producir los mismos resultados que el motor visual.

---

### Fase 2: Servidor Python mínimo + cliente dual (3-4 semanas)

**Metas**
- Crear servidor Python con FastAPI/Starlette.
- Portar `world.py`, `physics.py`, `entities.py`, `navigation.py`.
- Conectar cliente web al servidor Python.
- Permitir coexistencia de servidor Node actual y servidor Python.

**Entregables**
- `server/main.py`: arranca HTTP, WebSocket, game loop.
- `server/engine/`: world, physics, entities, navigation, enemy_ai, game_loop.
- `server/websocket/game.py`: protocolo de estado e input.
- Cliente web adaptado para recibir estado y enviar input (`js/server-client.js`).
- Script `run.sh` que arranque servidor Python y sirva cliente web automáticamente.
- Scripts `run-python-server.sh` y `run-node-server.sh` (transición).

**Punto de no retorno:** el juego debe ser jugable básicamente contra el servidor Python.

---

### Fase 3: Web MCP nativo (2 semanas)

**Metas**
- Exponer tools MCP desde Python.
- Reescribir el BT engine en Python.
- Validar conexión de opencode vía HTTP/WebSocket.

**Entregables**
- `server/mcp/server.py`: endpoint MCP JSON-RPC 2.0.
- `server/mcp/tools.py`: definición de tools.
- `server/bt/engine.py` y `server/bt/actions.py`.
- Configuración de ejemplo para opencode (`opencode.json.example`).

**Punto de no retorno:** opencode puede controlar el servidor Python igual o mejor que el Node actual.

---

### Fase 4: Adelgazar cliente y retirar Node (2-3 semanas)

**Metas**
- Quitar lógica de simulación del navegador.
- Implementar interpolación y predicción básica.
- Eliminar dependencia de `game-server.js` y `mcp-server.js`.

**Entregables**
- Cliente web solo renderiza e interpola.
- `js/client/` con: renderer, input, netcode, UI.
- `js/engine/` eliminado o reducido a helpers visuales.
- Documentación de migración y guía de despliegue.

**Punto de no retorno:** se borra el servidor Node. Requiere que el Python cubra 100% de funcionalidad.

---

### Fase 5: Escalado y ML (continuo)

**Metas**
- Múltiples partidas/mundos concurrentes.
- Entrenamiento offline de agentes.
- Integración con herramientas de aprendizaje del equipo.

**Entregables**
- `server/rooms.py`: gestión de instancias de juego.
- `server/training/` entorno gym-like para RL.
- Ejemplos de scripts de entrenamiento.

---

## Formato de mensajes cliente-servidor (v0.1)

### Estado del servidor → cliente (`state_update`)

```json
{
  "type": "state_update",
  "tick": 1234,
  "timestamp": 1752931200.0,
  "players": {
    "1": { "x": 24.0, "y": 25.0, "z": 20.0, "ry": 0.0, "rx": 0.0, "health": 20 },
    "2": { "x": 25.0, "y": 25.0, "z": 25.0, "ry": 1.2, "rx": -0.1, "health": 18 }
  },
  "enemies": [
    { "id": 1, "type": "zombie", "x": 30.0, "y": 25.0, "z": 30.0, "health": 10 }
  ],
  "chunk_deltas": {
    "0,0": [[10, 25, 10, 1], [10, 26, 10, 0]]
  },
  "day_time": 0.5,
  "events": [
    { "type": "damage_taken", "target": "player", "id": 2, "amount": 2, "source": "enemy", "source_id": 1 }
  ]
}
```

### Input del cliente → servidor (`input`)

```json
{
  "type": "input",
  "player_id": 1,
  "seq": 42,
  "move": { "x": 0.0, "z": 1.0 },
  "look": { "x": 0.05, "y": -0.02 },
  "jump": false,
  "fly": false,
  "place_block": false,
  "break_block": false,
  "selected_slot": 0
}
```

### Llamada MCP HTTP POST `/mcp`

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

---

## Estructura de carpetas propuesta

```
minecraft-clone/
├── client/                 # Cliente web (actualmente js/)
│   ├── index.html
│   ├── css/
│   ├── js/
│   │   ├── renderer.js
│   │   ├── input.js
│   │   ├── net.js
│   │   └── main.js
│   └── assets/
├── server/                 # Servidor Python nuevo
│   ├── main.py
│   ├── config.py
│   ├── engine/
│   │   ├── __init__.py
│   │   ├── world.py
│   │   ├── chunk.py
│   │   ├── physics.py
│   │   ├── entities.py
│   │   ├── navigation.py
│   │   ├── enemy_ai.py
│   │   └── game_loop.py
│   ├── mcp/
│   │   ├── __init__.py
│   │   ├── server.py
│   │   ├── tools.py
│   │   └── schemas.py
│   ├── bt/
│   │   ├── __init__.py
│   │   ├── engine.py
│   │   ├── nodes.py
│   │   └── actions.py
│   ├── websocket/
│   │   ├── __init__.py
│   │   └── game.py
│   └── tests/
│       ├── test_physics.py
│       ├── test_world.py
│       └── test_navigation.py
├── docs/
│   ├── adr/
│   │   ├── 001-combat-detection.md
│   │   └── 002-python-server.md
│   ├── python-server-plan.md
│   └── python-server-protocol.md
├── pyproject.toml          # Dependencias Python
└── README.md
```

---

## Riesgos y mitigaciones

| Riesgo | Probabilidad | Impacto | Mitigación |
|--------|-------------|---------|--------------|
| Migración larga y agota energía | Media | Alto | Fases cortas con entregables jugables. |
| Bugs de física distintos en Python | Media | Alto | Tests de regresión antes y después del port. |
| Renderizado "pesado" por red | Baja | Medio | Interpolación + predicción básica. |
| Pérdida de funcionalidades visuales | Baja | Medio | Migrar componente a componente, no de golpe. |
| Dependencia de bibliotecas MCP inmaduras | Media | Medio | Usar HTTP JSON-RPC 2.0 primero; Web MCP como evolución. |

---

## Quick wins durante la transición

Acciones que se pueden hacer ya en la rama actual sin esperar al gran refactor:

1. **Heartbeat enriquecido**: incluir eventos de daño, bloques rotos, enemigos vistos.
2. **Caché de chunks en `game-server.js`**: responder `get_block`/`get_blocks_in_area` sin relay siempre que sea posible.
3. **Tests del BT engine**: separar `bt-engine.js` de la conexión real y testearlo con mocks.
4. **Prototipo FastMCP en Python**: crear un servidor MCP mínimo en Python para familiarizarse con la tecnología.

---

## Siguiente acción inmediata

Definir y acordar el protocolo de mensajes (`docs/python-server-protocol.md`) para que Fase 1 y Fase 2 puedan desarrollarse en paralelo.
