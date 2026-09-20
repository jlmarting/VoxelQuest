# LEARN: CSG — construye formas complejas combinando piezas simples

## Concepto

**CSG (Constructive Solid Geometry)** es una técnica para describir un sólido *como datos*: en vez de enumerar píxel a píxel (o voxel a voxel) qué bloques forman un objeto, partes de primitivas simples y las combinas con **operaciones booleanas**:

| Operación | Símbolo | Resultado |
|---|---|---|
| **Unión** | `A ∪ B` | Todo lo de A y todo lo de B juntos |
| **Resta** | `A − B` | Lo de A que no está dentro de B (taladrar/ahuecar) |
| **Intersección** | `A ∩ B` | Solo la parte que comparten A y B |

A las primitivas (caja, esfera, cilindro, pirámide...) se les aplican además **transformaciones** (trasladar, rotar, escalar) y **repeticiones** (patrones de copias).

## Por qué es importante

En VoxelQuest, cada estructura nueva (una casa, una catedral, una escultura) se genera hoy con un **script Python** que recalcula la geometría bloque a bloque con bucles, `math.sin/cos` y lógica procedural. Consecuencias:

- Cada script duplica el cliente MCP, `detect_ground`, `send_batch`... (~61 scripts con el mismo boilerplate).
- El "conocimiento" de cómo se construye algo queda atrapado en código difícil de validar y reutilizar.
- Un **LLM** genera JSON mucho más fiablemente que código procedural con bucles anidados.

CSG convierte la construcción en **datos declarativos**: primitivas + operaciones. Resultado: estructuras validables con un schema, listables, versionables, y generables por IA con menos errores. Es la evolución natural del **VRML**: escena declarativa de primitivas, pero pensada para voxel y para que la lea un modelo.

## Explicación sencilla

Imagina que construyes con **plastilina**:

- **Primitivas** son tus moldes: una bola (`sphere`), un ladrillo (`box`), una rueda (`cylinder`).
- **Unión** = juntar dos bolas apretándolas hasta que son una sola pieza.
- **Resta** = meter un molde en la pieza, sacarlo, y queda el hueco (así haces la puerta de una casa o el agujero de una rosquilla).
- **Intersección** = superponer dos moldes y quedarte solo con la parte que se solapa.

```
UNION        SUBTRACT       INTERSECT
  ██            ██             ██
 ████          ████           ██████
██  ██        ██  ██          ██  ██
 ██████        ████            ████
  ██            ██             ██
 dos piezas   el círculo     solo el solape
 juntas       hace un hueco  de ambos
```

El orden importa: `hueco − esfera` no es lo mismo que `esfera − hueco`. La resta **quita**, no añade.

## Ejemplo práctico

### Una casa con CSG declarativo

```json
{
  "name": "casa",
  "target": "grid",
  "children": [
    {
      "op": "union",
      "children": [
        { "op": "box", "size": [7, 3, 7], "material": "cobblestone" },
        { "op": "box", "size": [5, 1, 5], "at": [0, -1, 0], "material": "planks" }
      ]
    },
    {
      "op": "subtract",
      "children": [
        { "op": "box", "size": [7, 3, 7], "material": "cobblestone" },
        { "op": "box", "size": [5, 3, 5], "at": [0, 0, 0] }
      ]
    },
    {
      "op": "subtract",
      "children": [
        { "op": "box", "size": [7, 3, 7], "material": "cobblestone" },
        { "op": "box", "size": [1, 2, 1], "at": [0, 1, -3] }
      ]
    }
  ]
}
```

**Léelo como una receta:**

1. **Unión** → caja de 7×3×7 de roca **+** cimentación de 5×1×5 de tablones (un paso más abajo).
2. **Resta 1** → a la misma caja de 7×3×7, llévala con un cubo de 5×3×5 centrado: queda el **interior hueco** (paredes de 1 de grosor).
3. **Resta 2** → en la fachada, resta un cubo de 1×2×1: es la **puerta**.

### El runner lo convierte en voxels

Un interpretador recorre el árbol y resuelve:

```python
def csg_to_blocks(node, grid):
    if node["op"] in ("union", "subtract", "intersect"):
        a = csg_to_blocks(node["children"][0], grid)
        b = csg_to_blocks(node["children"][1], grid)
        return combine(a, b, node["op"])   # booleano por voxel
    if node["op"] == "box":
        return fill_box(size, material)     # primitiva → lista de bloques
```

El resultado final se envía con la tool MCP **`apply_blocks`** (voxel grid) o **`create_sculpture`** (subvoxel con color), reutilizando el motor que ya existe.

## Consejo pro

**Piensa en CSG como una receta de cocina:** primero los ingredientes (primitivas), luego las operaciones (booleanas) — y **el orden de resta importa**. Si te sale una estructura rara, revisa qué se resta contra qué.

- Usa **`union`** para *añadir* masa (muros, columnas, tejados).
- Usa **`subtract`** para *esculpir* (puertas, ventanas, interiores, fosos).
- Usa **`array`** para repetir (columnas de nave, almenas de muralla, pináculos).
- **Composición jerárquica**: construye una "columna" como sub-árbol reutilizable y luego repítela. Un solo `array` de columnas vale por 50 `place_block`.

Para el caso VoxelQuest, lo más potente de CSG es que un LLM puede generar la estructura entera como **JSON puro** — validable contra un schema *antes* de tocar el mundo — y que el conocimiento de "cómo se hace una casa" queda en un archivo de datos, no en código procedural imposible de auditar.
