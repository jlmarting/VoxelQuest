# VoxelQuest

Un juego de construcción y exploración de mundos voxel con soporte para pantalla partida.

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

### Opción 1: Servidor Python
```bash
cd minecraft-clone
python3 server.py
```

### Opción 2: Script de ejecución
```bash
cd minecraft-clone
./run.sh
```

### Opción 3: Abrir directamente
Simplemente abre `index.html` en tu navegador.

## Tipos de Bloques

| Bloque | Color |
|--------|-------|
| Hierba | Verde |
| Tierra | Marrón |
| Piedra | Gris |
| Madera | Marrón oscuro |
| Hojas | Verde oscuro |
| Arena | Beige |
| Agua | Azul |
| Roca | Gris oscuro |
| Tablones | Beige claro |
| Bedrock | Negro |

## Estructura del Proyecto

```
minecraft-clone/
├── index.html          # HTML principal
├── css/
│   └── style.css       # Estilos
├── js/
│   ├── main.js         # Juego principal
│   ├── world.js        # Generación de mundo
│   ├── player.js       # Controles del jugador
│   ├── inventory.js    # Sistema de inventario
│   ├── enemies.js      # IA de enemigos
│   ├── daynight.js     # Ciclo día/noche
│   ├── ui.js           # Interfaz de usuario
│   └── noise.js        # Generador de ruido
├── server.py           # Servidor local
└── run.sh              # Script de ejecución
```

## Notas

- El juego usa Three.js para renderizado 3D
- El mundo se genera proceduralmente usando ruido Perlin
- Los enemigos aparecen durante la noche
- El crafteo es automático al tener los materiales
