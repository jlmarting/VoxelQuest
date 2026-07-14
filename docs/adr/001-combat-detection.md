# ADR-001: Detección de Combate con Producto Escalar

**Fecha:** 2026-07-14  
**Estado:** Aceptada  
**Contexto:** Fase 1 - Sistema de Combate Melee

## Contexto

Necesitamos implementar un sistema de combate cuerpo a cuerpo donde el Jugador 2 (controlado por IA) pueda atacar enemigos. El sistema debe:

1. Detectar si un enemigo está dentro del rango de ataque (3 bloques)
2. Validar que el enemigo esté en el cono de visión del jugador (no detrás)
3. Ser eficiente para ejecutarse en cada tick del juego

Opciones consideradas:
- **Bounding box 3D**: Colisiones complejas entre hitboxes
- **Raycast**: Lanzar rayo desde el jugador hacia el enemigo
- **Producto escalar (dot product)**: Validar ángulo entre vectores

## Decisión

Usar **producto escalar normalizado** para validar que el enemigo está dentro de un cono de 90° (45° a cada lado del vector de dirección del jugador).

### Algoritmo

```javascript
// Vector de dirección del jugador (hacia dónde mira)
const playerDir = {
  x: -Math.sin(player.rotation.y),
  z: -Math.cos(player.rotation.y)
};

// Vector hacia el enemigo
const toEnemy = {
  x: enemy.position.x - player.position.x,
  z: enemy.position.z - player.position.z
};

// Normalizar
const distance = Math.hypot(toEnemy.x, toEnemy.z);
toEnemy.x /= distance;
toEnemy.z /= distance;

// Producto escalar
const dot = playerDir.x * toEnemy.x + playerDir.z * toEnemy.z;

// Validar: dot > 0.707 (cos 45°) y distancia < 3
const inCone = dot > 0.707;
const inRange = distance < 3.0;
```

## Consecuencias

### Positivas
- ✅ **Simple y rápido**: Solo operaciones matemáticas básicas
- ✅ **Sin dependencias**: No requiere librerías de física adicionales
- ✅ **Predecible**: Comportamiento consistente y fácil de depurar
- ✅ **Eficiente**: O(1) por enemigo, sin cálculos de colisión complejos

### Negativas
- ❌ **No considera obstáculos**: Un enemigo detrás de una pared sigue siendo "atacable" si está en el cono
- ❌ **Sin feedback visual de colisión**: No hay animación de impacto realista
- ❌ **Cono fijo**: 90° puede no sentirse natural para todos los jugadores

### Mitigaciones
- Para obstáculos: Aceptar limitación inicial, mejorar en iteración futura con raycast opcional
- Para feedback: Añadir flash rojo en enemigo + sonido de golpe
- Para cono: 90° es estándar en juegos de acción, ajustable vía constante

## Alternativas Descartadas

### Bounding Box 3D
- **Por qué no**: Requiere integración con sistema de física existente, más complejo
- **Cuándo considerar**: Si necesitamos precisión milimétrica (ej: esports)

### Raycast
- **Por qué no**: Más costoso computacionalmente, requiere traversar el mundo voxel
- **Cuándo considerar**: Si necesitamos validar línea de visión (obstáculos)

## Referencias

- [Especificación - Anexo A.1](../especificacion_mcp.md#a1-sistema-de-combate-melee-playerjs--enemiesjs)
- Archivos afectados: `js/player.js`, `js/enemies.js`
