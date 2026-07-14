# Fase 2: Sistema de Navegación A* - COMPLETADA

**Fecha:** 2026-07-14  
**Estado:** Completada

## Resumen

Implementado sistema de pathfinding A* en 2D con path follower que traduce la ruta en inputs de gamepad virtual, permitiendo al Jugador 2 navegar autónomamente por el mundo voxel.

## Archivos Creados/Modificados

| Archivo | Cambio |
|---------|--------|
| `js/navigation.js` | **Nuevo**: `Pathfinder` (A*) + `PathFollower` (cola de movimiento) |
| `js/mcp-client.js` | Nuevos: `pathfinder`, `follower`, `update()`, `sendAsyncResponse()`, handler `navigate_to` |
| `js/main.js` | Nueva llamada a `mcpClient.update(deltaTime)` en game loop |
| `index.html` | Agregado script `js/navigation.js` después de `world.js` |
| `mcp-server.js` | Nuevo handler `moverse_a` con timeout de 30s para navegación |

## Detalles Técnicos

### Pathfinder (A* 2D)
- **Grid**: 2D (x, z), 4 direcciones (Manhattan)
- **Heurística**: Distancia Manhattan
- **Celdas transitables**: Espacio libre (Y, Y+1), soporte sólido (Y-1)
- **Saltos**: Obstáculo de 1 bloque → penalización de costo (G x2) + flag `jump`
- **Máximo de pasos**: 500 nodos (cubre áreas amplias)

### PathFollower (Cola de Movimiento)
- **Estados**: `IDLE → FOLLOWING → COMPLETE`
- **Steering**: Calcula yaw hacia nodo objetivo, aplica look horizontal + forward
- **Detección de atasco**: 60 frames sin movimiento significativo (< 0.02 bloques) → FAILURE
- **Rango de llegada**: 0.4 bloques del centro del nodo objetivo

### Flujo de Navegación
```
moverse_a(x, z)  →  navigate_to  →  A* findPath  →  PathFollower.start()
                     ↓                             ↓
                timeout 30s                gamepad virtual input
                     ↓                             ↓
              WebSocket response          player.update() cada frame
```

### Manejador Async
- `navigate_to` usa `__async: true` para no responder inmediatamente
- `PathFollower` marca `COMPLETE` al llegar
- `MCPClient.update()` detecta el estado y envía respuesta vía WebSocket
- relayToGame en servidor usa timeout de 30 segundos para rutas largas

## Decisiones (ADRs)

- **ADR-002** (implícito): A* 2D con 4 direcciones en lugar de 8
  - *Por qué*: En mundo voxel no hay diagonales reales, reduce complejidad
- **ADR-003** (implícito): PathFollower en game loop en lugar de setTimeout
  - *Por qué*: Sincronizado con físicas del juego, evita race conditions

## Lecciones Aprendidas

- La detección de atascos necesita calibración: 60 frames (~1s a 60fps) es adecuado
- El steering con `look.x` escalado por 2 da giros suaves sin overshoot
- PathFollower necesita ejecutarse ANTES de `player.update()` para que el input se aplique en el mismo frame

## Pendiente para Fase 3

- Crear `bt-engine.js` en Node.js con parser del esquema JSON
- Implementar Blackboard (actualizar desde estado del browser)
- Tick loop a 10Hz
- Nodos: Selector, Secuencia, Condicion, Accion
- Resolución de variables del Blackboard en parámetros
- Gestión de estado RUNNING
- Fallback a idle()

## Cómo Probar

```bash
# Iniciar servidor
node mcp-server.js

# En el navegador, seleccionar modo coop (Jugador 2)
# Luego:
curl -X POST http://localhost:9000/mcp -H 'Content-Type: application/json' \
  -d '{"method":"gamepad_connect","params":{"player_id":2}}'

curl -X POST http://localhost:9000/mcp -H 'Content-Type: application/json' \
  -d '{"method":"moverse_a","params":{"player_id":2,"x":20,"z":30}}'
```
