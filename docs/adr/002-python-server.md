# ADR-002: Migración a servidor Python autoritativo con cliente web ligero y Web MCP

**Fecha:** 2026-07-18  
**Estado:** Aceptada  
**Contexto:** Fase de consolidación arquitectónica de VoxelQuest

## Contexto

VoxelQuest está construido actualmente como una aplicación web monolítica donde el navegador es la fuente de verdad del mundo. El servidor Node.js (`game-server.js`) solo hace relay de comandos MCP al navegador, que es quien ejecuta la física, mantiene el terreno, gestiona enemigos y renderiza.

Esto crea varios problemas para el objetivo del proyecto, que incluye entrenar agentes de IA y ofrecer una plataforma estable de aprendizaje:

1. **No hay estado reproducible**: sin un navegador conectado no existe el mundo; no se pueden hacer tests ni entrenar offline.
2. **Latencia doble para el agente**: cada acción viaja por MCP → bridge stdio → WebSocket → navegador → WebSocket → servidor → MCP.
3. **Código duplicado**: lógica de enemigos, movimiento y pathfinding existe tanto en el servidor como en el cliente.
4. **Acoplamiento a Node.js**: el ecosistema actual dificulta aprovechar las últimas herramientas de aprendizaje automático que el equipo está construyendo en Python.
5. **Clientes limitados**: hoy solo opencode (vía `mcp-server.js` stdio) puede controlar el juego de forma estándar.

## Decisión

Migrar VoxelQuest a una arquitectura **cliente-servidor** con las siguientes características:

1. **Servidor autoritativo en Python**: la simulación del mundo, la física, los enemigos, los jugadores y la lógica de juego residen en el servidor. Es la única fuente de verdad.
2. **Cliente web de renderizado ligero**: el navegador solo recibe estado, renderiza con Three.js, captura input humano y lo envía al servidor. No simula por su cuenta.
3. **Web MCP nativo**: el servidor expone MCP sobre HTTP/WebSocket, permitiendo que cualquier cliente (opencode, scripts Python, dashboards, otros navegadores) se conecte directamente.
4. **Motor de Behavior Tree en Python**: el BT engine actual (`bt-engine.js`) se reescribe/ports a Python y corre contra el estado autoritativo del servidor.
5. **Servidor local por defecto para juego local**: para preservar la experiencia de "abrir y jugar", el servidor Python corre en `localhost` y se arranca automáticamente junto con el cliente (similar a cómo hoy `node game-server.js` abre el navegador).

### Sobre el modo split-screen

El split-screen no desaparece. El cliente web sigue soportando dos viewports (`solo` y `coop`) y usa un único renderer para ambas cámaras. La diferencia es que ahora ambos jugadores son entidades simuladas por el servidor Python, no por el navegador. El modo `coop` seguirá siendo local por defecto, pero la arquitectura cliente-servidor también habilita un futuro **coop remoto** (dos navegadores conectados al mismo servidor).

## Diagrama objetivo

```
┌─────────────────────────────────────────────────────────────┐
│                       Navegador (cliente)                  │
│  Three.js + input humano + renderizado + Web MCP cliente     │
└──────────────┬──────────────────────────────────────────────┘
               │ WebSocket / HTTP
               ▼
┌─────────────────────────────────────────────────────────────┐
│                Servidor Python (autoritativo)                │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────────────┐     │
│  │ World Engine│ │ Physics     │ │ Enemy AI            │     │
│  │ (chunks,    │ │ (movement,  │ │ (spawn, pathfinding)│     │
│  │ terrain)    │ │ collision)  │ │                     │     │
│  └─────────────┘ └─────────────┘ └─────────────────────┘     │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────────────┐     │
│  │ Web MCP     │ │ Behavior    │ │ Game Loop (fixed)   │     │
│  │ endpoint    │ │ Tree Engine │ │                     │     │
│  └─────────────┘ └─────────────┘ └─────────────────────┘     │
└─────────────────────────────────────────────────────────────┘
```

## Alternativas consideradas

### A. Mantener arquitectura actual y solo mejorar feedback
- **Por qué no**: no resuelve la reproducibilidad, la latencia doble ni el acoplamiento a Node. Además, seguiría siendo imposible entrenar agentes sin un navegador abierto.

### B. Servidor autoritativo, pero seguir en Node.js
- **Por qué no**: posible técnica, pero no aprovecha las herramientas de aprendizaje en Python del equipo y no mejora la legibilidad del código para ese ecosistema.

### C. Headless browser con el motor actual
- **Por qué no**: da reproducibilidad sin reescribir el motor, pero sigue consumiendo un navegador por instancia, es frágil y difícil de escalar para entrenamiento masivo.

### D. Modo split-screen offline sin servidor
- **Por qué no**: se descarta por ahora. Requeriría mantener una simulación local adicional en JS (doble implementación) o usar Pyodide/embebido, lo que complica el desarrollo y contradice el objetivo de un único motor Python.

## Consecuencias

### Positivas
- ✅ **Estado reproducible y testeable**: tests sin navegador, episodios determinísticos.
- ✅ **Mejor rendimiento para agentes**: feedback inmediato desde el servidor, sin relay al browser.
- ✅ **Ecosistema Python**: integración directa con RL, ML, FastAPI, Pydantic, etc.
- ✅ **Clientes múltiples y remotos**: Web MCP permite conectar opencode, scripts, dashboards y más jugadores.
- ✅ **Código más fácil de entender**: separación clara entre simulación, renderizado y protocolo.
- ✅ **Escalabilidad**: múltiples agentes, partidas y mundos en paralelo.
- ✅ **Coop remoto habilitado**: la misma arquitectura permite jugar desde varios navegadores.

### Negativas
- ❌ **Migración costosa**: hay que portar `js/world.js`, `js/physics.js`, `js/player.js`, `js/enemies.js`, `js/navigation.js` y `bt-engine.js` a Python.
- ❌ **Sincronización cliente-servidor**: requiere técnicas de interpolación, predicción y delta compression para que el movimiento se sienta fluido.
- ❌ **Cambio de cultura del equipo**: deja de ser una app web JS para convertirse en un sistema Python + cliente web.
- ❌ **Riesgo de romper funcionalidad actual**: renderizado, audio, UI del navegador deben adaptarse.
- ❌ **No es offline puro**: requiere que el servidor Python esté corriendo, aunque sea local.

### Mitigaciones
- Migración incremental: primero extraer simulación pura en JS, luego portar a Python, luego adelgazar cliente.
- Usar FastAPI/Starlette para el servidor MCP y WebSocket.
- Mantener funcionalidad de game-server.js actual operativa durante la transición.
- Crear tests de regresión antes de mover lógica crítica (pathfinding, colisiones, terreno).
- Proveer script `run.sh` / `run.py` que arranque automáticamente servidor Python + cliente web para juego local.

## Referencias
- ADR-001: Detección de combate con producto escalar
- Especificación MCP: `docs/especificacion_mcp.md`
- LEARN de transportes MCP: `docs/LEARN-mcp-transport.md`
- Plan detallado: `docs/python-server-plan.md`
- Archivos afectados principales: `js/world.js`, `js/physics.js`, `js/player.js`, `js/enemies.js`, `js/navigation.js`, `js/game-client.js`, `bt-engine.js`, `game-server.js`, `mcp-server.js`
