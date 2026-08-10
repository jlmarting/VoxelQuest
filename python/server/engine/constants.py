"""Constantes compartidas entre motor, protocolo y cliente."""

from enum import IntEnum


class BlockType(IntEnum):
    AIR = 0
    GRASS = 1
    DIRT = 2
    STONE = 3
    WOOD = 4
    LEAVES = 5
    SAND = 6
    WATER = 7
    COBBLESTONE = 8
    PLANKS = 9
    BEDROCK = 10
    GLOWSTONE = 11
    REDSTONE = 12
    RED_BRICK = 13  # Teja rojo-granate (tejados)


# Compatibilidad: nombres en español para logs/debug
BLOCK_NAMES: dict[BlockType, str] = {
    BlockType.AIR: "Aire",
    BlockType.GRASS: "Hierba",
    BlockType.DIRT: "Tierra",
    BlockType.STONE: "Piedra",
    BlockType.WOOD: "Madera",
    BlockType.LEAVES: "Hojas",
    BlockType.SAND: "Arena",
    BlockType.WATER: "Agua",
    BlockType.COBBLESTONE: "Roca",
    BlockType.PLANKS: "Tablones",
    BlockType.BEDROCK: "Bedrock",
    BlockType.GLOWSTONE: "Glowstone",
    BlockType.REDSTONE: "Redstone",
    BlockType.RED_BRICK: "Ladrillo rojo",
}


# Texturas: índice en atlas [top, side, bottom]
BLOCK_TEXTURES: dict[BlockType, tuple[int, int, int]] = {
    BlockType.GRASS: (0, 1, 2),
    BlockType.DIRT: (2, 2, 2),
    BlockType.STONE: (3, 3, 3),
    BlockType.WOOD: (5, 4, 5),
    BlockType.LEAVES: (6, 6, 6),
    BlockType.SAND: (7, 7, 7),
    BlockType.WATER: (8, 8, 8),
    BlockType.COBBLESTONE: (9, 9, 9),
    BlockType.PLANKS: (10, 10, 10),
    BlockType.BEDROCK: (11, 11, 11),
    BlockType.GLOWSTONE: (12, 12, 12),
    BlockType.RED_BRICK: (14, 14, 14),
}


CHUNK_SIZE = 16
WORLD_HEIGHT = 64
SEA_LEVEL = 20
TEX_SIZE = 16
ATLAS_COLS = 16

# Física / entidades
PLAYER_HEIGHT = 1.8
PLAYER_WIDTH = 0.6  # ancho total; radio de colisión = 0.3
PLAYER_MAX_HEALTH = 20
PLAYER_SPEED = 5.0
PLAYER_JUMP_FORCE = 8.0
GRAVITY = -20.0
TICK_RATE = 20
DT = 1.0 / TICK_RATE

# Render
RENDER_DISTANCE = 32  # 32*16=512 → área visible ~1000 bloques para entrenamiento IA

# Objetos móviles (propuesta 002)
MAX_OBJECTS = 100
MAX_SCULPTURE_VOXELS = 30000
SUBVOXEL_MIN_SIZE = 0.125
DEFAULT_RESTITUTION = 0.3
DEFAULT_FRICTION = 0.5
OBJECT_GRAVITY = -20.0  # misma magnitud que GRAVITY; separado para poder afinar
DEFAULT_OBJECT_HEALTH = 100.0
OBJECT_LINEAR_DAMPING = 0.02  # pérdida del 2% por tick (≈33%/s a 20Hz)
OBJECT_ANGULAR_DAMPING = 0.0
