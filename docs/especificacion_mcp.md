# Especificación Refactorizada: Arquitectura de Agente Autónomo mediante Árboles de Comportamiento y MCP (Directo en Node.js)

## 1. Descripción General
Esta especificación define la arquitectura para controlar al **Jugador 2** de forma autónoma en un clon de Minecraft en JavaScript (split-screen local) utilizando un **Árbol de Comportamiento (Behavior Tree - BT)** reactivo ejecutado directamente en el servidor MCP en Node.js, eliminando procesos intermedios innecesarios.

La IA actúa únicamente a nivel **Deliberativo** (generando el árbol JSON una sola vez a partir de un prompt del usuario). El servidor MCP en Node.js ejecuta el árbol de forma **Reactiva** en tiempo real ($10\text{ Hz}$) interactuando con las físicas y el renderizado del navegador a través de un WebSocket bidireccional.

---

## 2. Arquitectura del Sistema (Flujo Directo de Baja Latencia)

```
+-----------------------------------------------------------------------------------------+
|                                  JUEGO EN EL NAVEGADOR (JS)                             |
|  - Renderiza el mundo, físicas nativas, colisiones y split-screen                       |
|  - Cuenta con un motor de navegación integrado (A* 2D simplificado)                     |
|  - Mecánica de combate añadida en player.js / enemies.js (fuerza de empuje y daño)       |
+---------------------------------------------------+-------------------------------------+
                                                    ^
                                                    | WebSockets Directos (Baja Latencia)
                                                    v
+---------------------------------------------------+-------------------------------------+
|                              SERVIDOR MCP EN NODE.JS (bt-engine.js)                     |
|  - Mantiene el Blackboard local actualizado en cada tick con la telemetría del juego     |
|  - Mantiene el estado de ejecución de los nodos activos (p. ej. qué hijo devolvió RUNNING) |
|  - Evalúa la estructura del árbol JSON recursivamente a 10 Hz (cada 100ms)              |
+---------------------------------------------------+-------------------------------------+
                                                    ^
                                                    | API de Herramientas MCP
                                                    v
+---------------------------------------------------+-------------------------------------+
|                                 ORQUESTADOR DE IA (LLM)                                 |
|  - Recibe el prompt del usuario ("Persigue zombis pero huye si tienes poca vida")       |
|  - Genera y valida un único JSON del árbol de comportamiento parametrizado              |
+-----------------------------------------------------------------------------------------+
```

---

## 3. El Sistema de Datos Dinámico: Blackboard y API

### 3.1. Estructura del Blackboard (Compartido en Node.js)
Antes de evaluar el árbol, el motor de Node.js actualiza este objeto de contexto con los datos recibidos del cliente de JavaScript:
```json
{
  "self_vida": 10,
  "self_x": 12.5,
  "self_z": -45.0,
  "target_enemigo_id": "zombie_42",
  "target_enemigo_x": 14.0,
  "target_enemigo_z": -43.5,
  "hay_enemigos_cerca": true
}
```

### 3.2. Catálogo de Acciones del Jugador 2 (Efectores expuestos en MCP)
* **`moverse_a(x, z)`**: Delega el cálculo de ruta (A*) al cliente de JavaScript. Retorna `RUNNING` mientras se desplaza, `SUCCESS` al llegar y `FAILURE` si el camino está bloqueado.
* **`golpear(target_id)`**: Ejecuta un golpe melé al enemigo si está en rango de colisión (< 3 bloques). Retorna `SUCCESS` si el golpe impacta y aplica daño/knockback.
* **`equipar(item_id)`**: Cambia el ítem activo en la mano.
* **`idle()`**: Acción de fallback para que el bot mire alrededor de forma pasiva o espere.

---

## 4. Esquema JSON Estricto del Árbol de Comportamiento (Parametrizado)

Para evitar la fragilidad de condiciones basadas en cadenas crudas como `"vida < 5"` o el uso peligroso de `eval()`, el esquema exige parámetros estructurados que pueden hacer referencia a variables del Blackboard.

### 4.1. Definición del Esquema JSON (Borrador de Validación)
```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "BehaviorTree",
  "type": "object",
  "properties": {
    "comportamiento": { "type": "string", "enum": ["Selector", "Secuencia", "Accion", "Condicion"] },
    "nombre": { "type": "string" },
    
    "tipo": { "type": "string" },
    "parametros": {
      "type": "object",
      "additionalProperties": {
        "type": ["string", "number", "boolean"]
      }
    },
    
    "variable": { "type": "string" },
    "comparacion": { "type": "string", "enum": ["menor_que", "mayor_que", "igual_a", "verdadero", "falso"] },
    "valor_comparar": { "type": ["string", "number", "boolean"] },
    
    "hijos": {
      "type": "array",
      "items": { "$ref": "#" }
    }
  },
  "required": ["comportamiento"]
}
```

### 4.2. Ejemplo de Árbol JSON Válido (Resolución Dinámica de Parámetros)
Cuando un parámetro o propiedad de comparación coincide con una clave del Blackboard (p. ej., `"self_vida"` o `"target_enemigo_x"`), el evaluador en Node.js sustituye el valor en tiempo de ejecución.

```json
{
  "comportamiento": "Selector",
  "nombre": "Raiz",
  "hijos": [
    {
      "comportamiento": "Secuencia",
      "nombre": "Autopreservacion",
      "hijos": [
        {
          "comportamiento": "Condicion",
          "nombre": "Vida Critica",
          "variable": "self_vida",
          "comparacion": "menor_que",
          "valor_comparar": 5
        },
        {
          "comportamiento": "Accion",
          "nombre": "Huir de la Posicion de Peligro",
          "tipo": "moverse_a",
          "parametros": {
            "x": -10.0,
            "z": -10.0
          }
        }
      ]
    },
    {
      "comportamiento": "Secuencia",
      "nombre": "Atacar Enemigo",
      "hijos": [
        {
          "comportamiento": "Condicion",
          "nombre": "Enemigo en Rango de Vision",
          "variable": "hay_enemigos_cerca",
          "comparacion": "verdadero"
        },
        {
          "comportamiento": "Accion",
          "nombre": "Aproximarse",
          "tipo": "moverse_a",
          "parametros": {
            "x": "target_enemigo_x",
            "z": "target_enemigo_z"
          }
        },
        {
          "comportamiento": "Accion",
          "nombre": "Atacar",
          "tipo": "golpear",
          "parametros": {
            "target_id": "target_enemigo_id"
          }
        }
      ]
    },
    {
      "comportamiento": "Accion",
      "nombre": "Esperar",
      "tipo": "idle"
    }
  ]
}
```

---

## 5. Ciclo de Vida y Gestión de Errores

1. **Flujo de Petición:** El usuario ingresa una directiva. La IA compila el JSON y el servidor Node.js lo valida contra el esquema estructural. Si falla la estructura o incluye APIs inválidas, el servidor devuelve el error al contexto del LLM para una auto-corrección inmediata.
2. **Ciclo de Ejecución (Ticks a 10Hz):** Node.js lee el árbol guardado de arriba a abajo en cada tick. Si un nodo retorna `RUNNING`, el motor memoriza su posición (es con estado en tiempo de ejecución) y prioriza su re-evaluación en el siguiente frame, a menos que un nodo condicional prioritario en una rama paralela cambie de estado.
3. **Manejo de Fallos:** Si todos los selectores de comportamiento del árbol fallan (por ejemplo, si no hay enemigos ni objetivos de movimiento viables), el motor intercepta el fallo y ejecuta automáticamente la acción por defecto `idle()`, garantizando la estabilidad del bot.

---

## Anexo A: Implementación de Gameplay Base y Navegación en el Cliente (JS)

Este anexo detalla las especificaciones técnicas requeridas para implementar el sistema de combate cuerpo a cuerpo (melee) y la navegación autónoma (pathfinding A*) directamente en el cliente de JavaScript del clon de Minecraft. Estas capacidades físicas son requisitos bloqueantes antes de poder mapear las acciones correspondientes al servidor MCP.

---

### A.1. Sistema de Combate Melee (player.js & enemies.js)

Para que el jugador autónomo (Jugador 2) pueda atacar de forma coherente, el cliente de JavaScript debe verificar la proximidad y la orientación espacial de las entidades enemigas antes de aplicar daño y fuerzas físicas.

#### A.1.1. Algoritmo de Detección en Cono Visual
En lugar de depender de colisiones 3D complejas en cada frame, el método de ataque evalúa la distancia euclidiana y el producto escalar (*dot product*) para proyectar un área de influencia en forma de cuña o cono.

```
                  Enemigo (Fuera de cono)
                    o
                   /
                  /
                 /   Enemigo (En cono)
                /      o
               /     .
              /    .
             /  .  Angulo <= 45º
            /._________________
           [Jugador] ---------> Vector Dirección (Frente)
```

1. **Rango Máximo de Ataque ($R$):** Limitado a $3.0$ bloques/metros.
2. **Ángulo de Ataque ($\theta$):** Cono de $90^\circ$ totales ($45^\circ$ a cada lado del vector de dirección del jugador). Esto equivale a una validación de producto escalar donde:
   $$\text{dotProduct}(\vec{A}, \vec{B}) > 0.707$$
   *(Donde $\vec{A}$ es el vector de dirección normalizado del jugador y $\vec{B}$ es el vector normalizado desde el jugador hacia el enemigo).*

#### A.1.2. Implementación de Daño y Retroceso (Knockback)
Al registrarse un impacto exitoso, se deben ejecutar tres pasos atómicos en el bucle del motor de juego:
* **Daño:** Restar salud en el objeto `Enemy`.
* **Fuerza Horizontal:** Calcular la dirección opuesta al impacto y sumarla al vector de velocidad del enemigo para simular el empuje.
* **Fuerza Vertical:** Sumar un pequeño impulso vertical (e.g., $+0.1$ en el eje Y) para levantar ligeramente al enemigo, facilitando la percepción visual del impacto.

---

### A.2. Sistema de Navegación A* Simplificado (navigation.js)

Dado que el mundo está compuesto por bloques en una cuadrícula regular, implementaremos un A* bidimensional (2D) con lógica de elevación para salvar desniveles de exactamente un bloque de altura.

#### A.2.1. Definición de Celda Transitable (Walkable)
Un nodo en la cuadrícula $(X, Z)$ se considera apto para el tránsito si cumple simultáneamente con las siguientes condiciones físicas en las coordenadas del bloque:
1. **Espacio para el cuerpo:** Bloque a la altura del pie ($Y$) y de la cabeza ($Y+1$) deben ser `Air` (vacíos).
2. **Soporte:** Bloque por debajo de los pies ($Y-1$) debe ser un bloque sólido (tierra, piedra, etc.).
3. **Escalabilidad (Salto):** Si el bloque en $(X, Z)$ a la altura del pie contiene un obstáculo de $1$ bloque de altura, el nodo es transitable únicamente si el bloque superior está libre y se penaliza el coste de la ruta ($G$) para priorizar caminos planos.

#### A.2.2. Algoritmo A* y Cola de Movimiento
El algoritmo calcula la ruta óptima utilizando la distancia Manhattan como heurística ($H$).

```javascript
// Estructura de salida del Pathfinding
const path = [
  { x: 12, z: -45, jump: false },
  { x: 12, z: -44, jump: false },
  { x: 13, z: -44, jump: true } // Indica que al entrar aquí debe simular tecla "Saltar"
];
```

* **Consumo de la Cola:** El script de control del Jugador 2 en JavaScript procesará este array paso a paso. Mientras la cola no esté vacía, apuntará la mirada hacia el siguiente nodo intermedio y simulará la pulsación de avanzar (`moveForward`). Si detecta que no se ha movido al nodo objetivo tras un número determinado de frames (colisión imprevista o caída), la acción reportará `FAILURE` y vaciará la cola para forzar la re-evaluación del Árbol de Comportamiento.

---

### A.3. Hoja de Ruta de Implementación Técnica

```
+-----------------------------------------------------------------------------+
| FASE A: Física y Combate Melee (Lado Cliente JS)                            |
| - Programar Player.prototype.hitEntity(targetId) con cálculo de dot product.|
| - Añadir animación o indicación visual de golpe en el canvas del navegador.|
+-----------------------------------------------------------------------------+
                                      |
                                      v
+-----------------------------------------------------------------------------+
| FASE B: Navegación A* en 2D (Lado Cliente JS)                               |
| - Crear biblioteca navigation.js con el algoritmo y heurística de salto.    |
| - Implementar el actuador que traduce la cola de pasos en inputs de teclado.|
+-----------------------------------------------------------------------------+
                                      |
                                      v
+-----------------------------------------------------------------------------+
| FASE C: Exposición en Servidor WebSocket                                    |
| - Mapear acciones 'moverse_a' y 'golpear' desde el servidor Node.js.         |
| - Actualizar el Blackboard de la spec principal en cada tick.               |
+-----------------------------------------------------------------------------+
```
