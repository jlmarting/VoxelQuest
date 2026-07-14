# Fase 1: Sistema de Combate Melee - COMPLETADA

**Fecha:** 2026-07-14  
**Estado:** Completada

## Resumen

Implementado sistema de combate cuerpo a cuerpo con detección de cono visual (dot product), knockback, y feedback visual. Jugador 2 puede atacar enemigos vía MCP.

## Archivos Modificados

| Archivo | Cambio |
|---------|--------|
| `js/player.js` | Nuevo `Player.prototype.hitEntity(enemy)` con validación de cono 90° y distancia < 3 bloques |
| `js/enemies.js` | `Enemy` ahora tiene `id` único + `maxHealth` |
| `js/enemies.js` | `takeDamage(amount, attackerPos)` aplica knockback horizontal (x8) + vertical (+6) |
| `js/enemies.js` | Nuevo `hitFlash()`: flash rojo 100ms en material del mesh |
| `js/enemies.js` | Nuevo `EnemyManager.nextEnemyId` contador estático |
| `js/enemies.js` | Nuevo `findEnemyById(id)` para búsqueda por ID |
| `js/enemies.js` | Nuevo `findNearestInCone(pos, dir, maxDist, dot)` para detección automática |
| `js/mcp-client.js` | Nuevo handler `attack`: soporta `target_id` o auto-detección del enemigo más cercano en cono |
| `mcp-server.js` | Nuevo handler MCP `attack` con relay al browser |

## Decisiones (ADRs)

- **ADR-001**: Dot product > 0.707 para cono de 90° (aceptada)

## Detalles Técnicos

### Player.hitEntity(enemy)
```javascript
// Validaciones en orden:
1. enemy existe y health > 0
2. distancia < 3.0 bloques
3. dot product > 0.707 (cono 90°)
4. Aplica daño (4 HP) + knockback
```

### Enemy.takeDamage(amount, attackerPos)
```javascript
1. Resta health
2. Calcula vector knockback: normalize(enemy.pos - attacker.pos) * 8
3. Aplica knockback vertical (+6)
4. Flash rojo en mesh por 100ms
```

### MCP Attack Handler
- Con `target_id`: busca enemigo por ID en EnemyManager
- Sin `target_id`: auto-detecta el enemigo más cercano en el cono
- Retorna: `{ success, damaged, enemyDead, enemyId? }`

## Pruebas Realizadas

- [ ] Prueba manual: curl POST /mcp con method attack
- [ ] Verificar que knockback empuja al enemigo hacia atrás
- [ ] Verificar flash rojo en enemigo al recibir daño
- [ ] Verificar que fuera del cono no se detecta

## Lecciones Aprendidas

- `Enemy` no tenía campo `id`; fue necesario agregar contador estático en `EnemyManager`
- El daño de 4 HP (2 golpes para matar zombie de 20 HP) balancea bien
- Knockback de 8 horizontal + 6 vertical da feedback claro sin descontrolar al enemigo

## Pendiente para Fase 2

- Crear `js/navigation.js` con A* 2D simplificado
- Implementar `isWalkable()` con detección de saltos de 1 bloque
- Integrar cola de movimiento con gamepad virtual
- Handler MCP `navigate_to` / `moverse_a`
