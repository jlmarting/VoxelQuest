# Phase 0: Estado Inicial del Proyecto

**Fecha:** 2026-07-14  
**Estado:** Completada (preparación)

## Resumen

Estado base del proyecto VoxelQuest antes de iniciar la implementación del sistema de agente autónomo con Behavior Trees.

## Arquitectura Actual

```
┌─────────────────────────────────────────────────────────────┐
│  Browser (JS)                                               │
│  ├── player.js          → Físicas, movimiento, inventario   │
│  ├── enemies.js         → IA de enemigos (zombie, skeleton) │
│  ├── gamepad.js         → Input virtual                     │
│  ├── mcp-client.js      → WebSocket relay al servidor       │
│  └── world.js           → Mundo voxel procedural            │
└─────────────────────────────────────────────────────────────┘
                          ↕ WebSocket
┌─────────────────────────────────────────────────────────────┐
│  Node.js (mcp-server.js)                                    │
│  ├── HTTP API           → POST /mcp (comandos)              │
│  ├── WebSocket Server   → Relay bidireccional               │
│  └── Game State Mirror  → Estado de jugadores (1, 2, AI)    │
└─────────────────────────────────────────────────────────────┘
```

## Componentes Existentes

### ✅ Implementado

**Servidor MCP (mcp-server.js)**
- 50+ handlers MCP: `move_player`, `gamepad_input`, `get_nearby_entities`, etc.
- Sistema de aprobación (auto/human) para crear avatares
- Relay WebSocket bidireccional con correlación por ID
- Sincronización de estado cada 1 segundo

**Cliente MCP (js/mcp-client.js)**
- Handler de comandos relay (move, look, place_block, etc.)
- Sincronización periódica de estado (1 Hz)
- Raycast desde jugador para interacción con bloques

**Sistema de Enemigos (js/enemies.js)**
- 3 tipos: Zombie (melee), Skeleton (ranged), Creeper (explosivo)
- IA básica: idle → chase → attack
- Detección de jugador más cercano (16 bloques)
- Sistema de daño y respawn

**Gamepad Virtual (js/gamepad.js)**
- Input programático vía `gamepad_input` MCP
- Movimiento con físicas reales (gravedad, colisiones)
- Usado por scripts Python (`evade_chase.py`)

### ❌ Pendiente (Requisitos de Spec)

**Combate Melee**
- No hay método `Player.hitEntity()`
- `Enemy.takeDamage()` existe pero no se invoca desde jugador
- Sin knockback ni feedback visual de impacto

**Navegación A***
- No existe `navigation.js`
- `gamepad_input` solo mueve en línea recta
- Scripts Python usan heurísticas ad-hoc (saltar, romper bloques)

**Motor de Behavior Trees**
- No existe `bt-engine.js`
- Sin sistema de blackboard
- Sin tick loop a 10Hz

**Orquestador LLM**
- Sin integración con APIs de IA
- Sin generación de árboles JSON desde prompts

## Archivos Clave

| Archivo | Líneas | Propósito |
|---------|--------|-----------|
| `mcp-server.js` | 849 | Servidor MCP + HTTP + WebSocket |
| `js/mcp-client.js` | 601 | Cliente MCP en browser |
| `js/player.js` | 469 | Físicas y controles del jugador |
| `js/enemies.js` | 304 | IA y lógica de enemigos |
| `js/gamepad.js` | ~200 | Input virtual para IA |
| `scripts/evade_chase.py` | 310 | Script Python de ejemplo |

## Decisiones Tomadas

- **ADR-001**: Usar dot product para detección de combate (cono de 90°)

## Siguiente Paso

**Fase 1: Sistema de Combate Melee**
1. Implementar `Player.prototype.hitEntity(targetId)` en `js/player.js`
2. Añadir knockback a `Enemy.takeDamage()` en `js/enemies.js`
3. Crear handler MCP `attack` en `js/mcp-client.js` y `mcp-server.js`
4. Añadir feedback visual (flash rojo)

**Criterios de Éxito:**
- Jugador 2 puede atacar zombies con comando MCP
- Enemigo recibe daño y knockback realista
- Cono de ataque de 90° respeta dirección del jugador

## Notas para IA

- El proyecto usa **Three.js** para renderizado 3D
- El mundo es voxel-based con chunks procedurales
- Los enemigos ya tienen `health`, `takeDamage()`, y `velocity`
- El gamepad virtual es el método preferido para movimiento de IA
- La sincronización browser→server es cada 1s (debe aumentarse a 100ms para BT)
