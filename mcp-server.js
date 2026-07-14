#!/usr/bin/env node
/**
 * VoxelQuest MCP Server v2.0
 * 
 * Servidor MCP completo para control de jugadores por agentes de IA.
 * 
 * Características:
 * - Control de jugadores existentes
 * - Creación de nuevos avatros bajo control IA
 * - Sistema de aprobación (auto/humano)
 * - Personalización de avatros
 * - Acciones: mover, construir, recolectar, etc.
 * 
 * Uso:
 *   node mcp-server.js
 */

const http = require('http');
const WebSocket = require('ws');
const fs = require('fs');
const path = require('path');
const webbrowser = require('child_process').webbrowser || null;

// Estado global del juego
let gameState = {
    players: {
        1: { name: 'Jugador 1', isAI: false, position: { x: 24, y: 25, z: 20 }, rotation: { x: 0, y: 0 }, health: 20, onGround: true, isFlying: false, selectedSlot: 0, inventory: [] },
        2: { name: 'Jugador 2', isAI: false, position: { x: 25, y: 25, z: 25 }, rotation: { x: 0, y: 0 }, health: 20, onGround: true, isFlying: false, selectedSlot: 0, inventory: [] }
    },
    world: null,
    scene: null,
    enemyManager: null,
    dayNight: null,
    running: false,
    seed: null,
    // Configuración de aprobación
    approvalMode: 'auto', // 'auto' o 'human'
    pendingApprovals: []
};

// IDs de jugadores
let nextPlayerId = 3; // 1 y 2 son locales

// WebSocket clients conectados
let gameClients = [];

// Enviar comando al juego via WebSocket
function sendToGame(data) {
    const message = JSON.stringify(data);
    gameClients.forEach(client => {
        if (client.readyState === 1) { // WebSocket.OPEN
            client.send(message);
        }
    });
}

// Mapa de peticiones relay pendientes (correlación por id)
const pendingMcp = {};

// Reenvía un comando al navegador (fuente de verdad) y espera su respuesta.
function relayToGame(method, params, timeoutMs = 5000) {
    if (!gameClients.length) return Promise.resolve({ error: 'Juego no conectado' });
    const id = Date.now().toString() + '_' + Math.random().toString(36).slice(2);
    return new Promise((resolve) => {
        const timer = setTimeout(() => {
            delete pendingMcp[id];
            resolve({ error: 'Timeout: el juego no respondió', method });
        }, timeoutMs);
        pendingMcp[id] = { resolve, timer };
        sendToGame({ id, method, params });
    });
}

// Colores para nuevos avatros
const AVATAR_COLORS = [
    { name: 'Rojo', shirt: 0xcc4444, pants: 0x882222 },
    { name: 'Azul', shirt: 0x4444cc, pants: 0x222288 },
    { name: 'Verde', shirt: 0x44cc44, pants: 0x228822 },
    { name: 'Amarillo', shirt: 0xcccc44, pants: 0x888822 },
    { name: 'Morado', shirt: 0xcc44cc, pants: 0x882288 },
    { name: 'Naranja', shirt: 0xcc8844, pants: 0x886622 },
    { name: 'Cian', shirt: 0x44cccc, pants: 0x228888 },
    { name: 'Rosa', shirt: 0xff88aa, pants: 0xcc6688 }
];

// Estructuras predefinidas
const STRUCTURES = {
    house: {
        name: 'Casa pequeña',
        blocks: [
            // Foundation
            { dx: 0, dy: 0, dz: 0, type: 3 }, { dx: 1, dy: 0, dz: 0, type: 3 },
            { dx: 2, dy: 0, dz: 0, type: 3 }, { dx: 3, dy: 0, dz: 0, type: 3 },
            { dx: 0, dy: 0, dz: 3, type: 3 }, { dx: 1, dy: 0, dz: 3, type: 3 },
            { dx: 2, dy: 0, dz: 3, type: 3 }, { dx: 3, dy: 0, dz: 3, type: 3 },
            { dx: 0, dy: 0, dz: 1, type: 3 }, { dx: 0, dy: 0, dz: 2, type: 3 },
            { dx: 3, dy: 0, dz: 1, type: 3 }, { dx: 3, dy: 0, dz: 2, type: 3 },
            // Walls
            ...Array.from({length: 4}, (_, i) => ({ dx: i, dy: 1, dz: 0, type: 1 })),
            ...Array.from({length: 4}, (_, i) => ({ dx: i, dy: 2, dz: 0, type: 1 })),
            ...Array.from({length: 4}, (_, i) => ({ dx: i, dy: 1, dz: 3, type: 1 })),
            ...Array.from({length: 4}, (_, i) => ({ dx: i, dy: 2, dz: 3, type: 1 })),
            { dx: 0, dy: 1, dz: 1, type: 1 }, { dx: 0, dy: 2, dz: 1, type: 1 },
            { dx: 3, dy: 1, dz: 1, type: 1 }, { dx: 3, dy: 2, dz: 1, type: 1 },
            { dx: 0, dy: 1, dz: 2, type: 1 }, { dx: 0, dy: 2, dz: 2, type: 1 },
            { dx: 3, dy: 1, dz: 2, type: 1 }, { dx: 3, dy: 2, dz: 2, type: 1 },
            // Roof
            ...Array.from({length: 5}, (_, i) => ({ dx: i, dy: 3, dz: 0, type: 5 })),
            ...Array.from({length: 5}, (_, i) => ({ dx: i, dy: 3, dz: 1, type: 5 })),
            ...Array.from({length: 5}, (_, i) => ({ dx: i, dy: 3, dz: 2, type: 5 })),
            ...Array.from({length: 5}, (_, i) => ({ dx: i, dy: 3, dz: 3, type: 5 })),
        ]
    },
    tower: {
        name: 'Torre',
        blocks: Array.from({length: 20}, (_, i) => {
            const level = Math.floor(i / 4);
            const pos = i % 4;
            const sides = [
                { dx: pos, dy: level, dz: 0, type: 3 },
                { dx: pos, dy: level, dz: 4, type: 3 },
                { dx: 0, dy: level, dz: pos, type: 3 },
                { dx: 4, dy: level, dz: pos, type: 3 }
            ];
            return sides;
        }).flat()
    },
    farm: {
        name: 'Granja',
        blocks: [
            ...Array.from({length: 7}, (_, i) => ({ dx: i, dy: 0, dz: 0, type: 2 })),
            ...Array.from({length: 7}, (_, i) => ({ dx: i, dy: 0, dz: 6, type: 2 })),
            ...Array.from({length: 5}, (_, i) => ({ dx: 0, dy: 0, dz: i+1, type: 2 })),
            ...Array.from({length: 5}, (_, i) => ({ dx: 6, dy: 0, dz: i+1, type: 2 })),
            ...Array.from({length: 5}, (_, i) => ({ dx: i+1, dy: 0, dz: 2, type: 5 })),
            ...Array.from({length: 5}, (_, i) => ({ dx: i+1, dy: 0, dz: 4, type: 5 })),
        ]
    }
};

// ============================================================
// HANDLERS MCP
// ============================================================
const mcpHandlers = {
    // ---- CONFIGURACIÓN ----
    
    // Obtener configuración actual
    get_config: async () => {
        return {
            approvalMode: gameState.approvalMode,
            playerCount: Object.keys(gameState.players).length,
            players: Object.entries(gameState.players).map(([id, p]) => ({
                id, name: p.name, isAI: p.isAI, position: p.position
            }))
        };
    },

    // Cambiar modo de aprobación
    set_approval_mode: async (params) => {
        gameState.approvalMode = params.mode; // 'auto' o 'human'
        return { success: true, approvalMode: gameState.approvalMode };
    },

    // ---- GESTIÓN DE JUGADORES ----

    // Listar jugadores
    list_players: async () => {
        return {
            players: Object.entries(gameState.players).map(([id, p]) => ({
                id: parseInt(id),
                name: p.name,
                isAI: p.isAI,
                position: p.position,
                rotation: p.rotation || { x: 0, y: 0 },
                health: p.health,
                onGround: p.onGround || false,
                isFlying: p.isFlying || false,
                selectedSlot: p.selectedSlot || 0
            }))
        };
    },

    // Crear nuevo avatar (bajo control IA)
    create_avatar: async (params) => {
        const { name, gender = 'male', hairStyle = 'short', hairColor = 0x3d2314,
                eyeColor = 0x4a90d9, shirtColor = 0x2266cc, pantsColor = 0x333366,
                spawnX = 0, spawnZ = 0 } = params;

        // Verificar si requiere aprobación
        if (gameState.approvalMode === 'human') {
            const approvalId = Date.now().toString();
            gameState.pendingApprovals.push({
                id: approvalId,
                type: 'create_avatar',
                params,
                status: 'pending'
            });
            
            // Notificar al juego
            if (gameState.onApprovalRequest) {
                gameState.onApprovalRequest({
                    id: approvalId,
                    type: 'create_avatar',
                    message: `Agente IA quiere crear avatar "${name}" (${gender})`
                });
            }
            
            return { 
                pending: true, 
                approvalId,
                message: 'Esperando aprobación del jugador humano' 
            };
        }

        // Auto-aprobado - crear avatar directamente
        return createAvatar(params);
    },

    // Aprobar solicitud (cuando modo = human)
    approve_request: async (params) => {
        const { approvalId, approved } = params;
        const request = gameState.pendingApprovals.find(r => r.id === approvalId);
        
        if (!request) {
            return { error: 'Solicitud no encontrada' };
        }

        if (approved) {
            request.status = 'approved';
            const result = await createAvatar(request.params);
            return { success: true, result };
        } else {
            request.status = 'rejected';
            return { success: true, message: 'Solicitud rechazada' };
        }
    },

    // Obtener solicitudes pendientes
    get_pending_requests: async () => {
        return {
            requests: gameState.pendingApprovals.filter(r => r.status === 'pending')
        };
    },

    // Obtener estado de un jugador
    get_player_state: async (params) => {
        const player = gameState.players[params.player_id];
        if (!player) {
            return { error: `Jugador ${params.player_id} no encontrado` };
        }
        return {
            id: params.player_id,
            name: player.name,
            isAI: player.isAI,
            position: player.position,
            rotation: player.rotation || { x: 0, y: 0 },
            health: player.health,
            onGround: player.onGround || false,
            isFlying: player.isFlying || false,
            selectedSlot: player.selectedSlot || 0,
            inventory: player.inventory || []
        };
    },

    // ---- CONTROLES DE MOVIMIENTO ----

    // Mover jugador (teletransportar)
    move_player: async (params) => {
        const player = gameState.players[params.player_id];
        if (!player) return { error: 'Jugador no encontrado' };
        
        if (params.x !== undefined) player.position.x = params.x;
        if (params.y !== undefined) player.position.y = params.y;
        if (params.z !== undefined) player.position.z = params.z;
        
        return relayToGame('move_player', { player_id: params.player_id, x: player.position.x, y: player.position.y, z: player.position.z });
    },

    // Mover relativo (adelante/atrás/izquierda/derecha)
    move_relative: async (params) => {
        const player = gameState.players[params.player_id];
        if (!player) return { error: 'Jugador no encontrado' };
        return relayToGame('move_relative', { player_id: params.player_id, forward: params.forward, backward: params.backward, left: params.left, right: params.right, distance: params.distance });
    },

    // Ráfaga de movimientos relativos (más fluido/rápido que uno a uno)
    move_burst: async (params) => {
        const player = gameState.players[params.player_id];
        if (!player) return { error: 'Jugador no encontrado' };
        return relayToGame('move_burst', {
            player_id: params.player_id,
            forward: params.forward, backward: params.backward,
            left: params.left, right: params.right,
            distance: params.distance, steps: params.steps,
            stepDelay: params.stepDelay, target_id: params.target_id
        });
    },

    // Gamepad virtual: activar para un jugador
    gamepad_connect: async (params) => {
        const player = gameState.players[params.player_id];
        if (!player) return { error: 'Jugador no encontrado' };
        return relayToGame('gamepad_connect', { player_id: params.player_id });
    },

    // Gamepad virtual: inyectar entradas (move/look/jump/fly/break/place/dpad)
    gamepad_input: async (params) => {
        const player = gameState.players[params.player_id];
        if (!player) return { error: 'Jugador no encontrado' };
        return relayToGame('gamepad_input', { player_id: params.player_id, input: params.input });
    },

    // Gamepad virtual: desactivar
    gamepad_disconnect: async (params) => {
        const player = gameState.players[params.player_id];
        if (!player) return { error: 'Jugador no encontrado' };
        return relayToGame('gamepad_disconnect', { player_id: params.player_id });
    },

    // Saltar
    jump: async (params) => {
        const player = gameState.players[params.player_id];
        if (!player) return { error: 'Jugador no encontrado' };
        return relayToGame('jump', { player_id: params.player_id, height: params.height });
    },

    // ---- CONTROLES DE VUELO ----

    // Volar arriba
    fly_up: async (params) => {
        const player = gameState.players[params.player_id];
        if (!player) return { error: 'Jugador no encontrado' };
        return relayToGame('fly_up', { player_id: params.player_id, distance: params.distance });
    },

    // Volar abajo
    fly_down: async (params) => {
        const player = gameState.players[params.player_id];
        if (!player) return { error: 'Jugador no encontrado' };
        return relayToGame('fly_down', { player_id: params.player_id, distance: params.distance });
    },

    // Alternar modo vuelo
    toggle_fly: async (params) => {
        const player = gameState.players[params.player_id];
        if (!player) return { error: 'Jugador no encontrado' };
        return relayToGame('toggle_fly', { player_id: params.player_id });
    },

    // ---- CONTROLES DE CÁMARA ----

    // Mirar (rotar cámara)
    look: async (params) => {
        const player = gameState.players[params.player_id];
        if (!player) return { error: 'Jugador no encontrado' };
        return relayToGame('look', { player_id: params.player_id, yaw: params.yaw, pitch: params.pitch, yaw_delta: params.yaw_delta, pitch_delta: params.pitch_delta });
    },

    // Obtener rotación
    get_rotation: async (params) => {
        const player = gameState.players[params.player_id];
        if (!player) return { error: 'Jugador no encontrado' };
        return relayToGame('get_rotation', { player_id: params.player_id });
    },

    // Alternar modo cámara
    toggle_camera: async (params) => {
        const player = gameState.players[params.player_id];
        if (!player) return { error: 'Jugador no encontrado' };
        return relayToGame('toggle_camera', { player_id: params.player_id });
    },

    // ---- CONTROLES DE INVENTARIO ----

    // Seleccionar slot
    select_slot: async (params) => {
        const player = gameState.players[params.player_id];
        if (!player) return { error: 'Jugador no encontrado' };
        
        const slot = params.slot;
        if (slot < 0 || slot > 8) return { error: 'Slot inválido (0-8)' };
        
        player.selectedSlot = slot;
        return relayToGame('select_slot', { player_id: params.player_id, slot });
    },

    // Seleccionar slot siguiente
    next_slot: async (params) => {
        const player = gameState.players[params.player_id];
        if (!player) return { error: 'Jugador no encontrado' };
        return relayToGame('next_slot', { player_id: params.player_id });
    },

    // Seleccionar slot anterior
    prev_slot: async (params) => {
        const player = gameState.players[params.player_id];
        if (!player) return { error: 'Jugador no encontrado' };
        return relayToGame('prev_slot', { player_id: params.player_id });
    },

    // ---- CONTROLES DE BLOQUES ----

    // Colocar bloque (como el jugador - en la dirección que mira)
    place_block_as_player: async (params) => {
        const player = gameState.players[params.player_id];
        if (!player) return { error: 'Jugador no encontrado' };
        return relayToGame('place_block_as_player', { player_id: params.player_id, type: params.type });
    },

    // Romper bloque (como el jugador - en la dirección que mira)
    break_block_as_player: async (params) => {
        const player = gameState.players[params.player_id];
        if (!player) return { error: 'Jugador no encontrado' };
        return relayToGame('break_block_as_player', { player_id: params.player_id });
    },

    // Teletransportar
    teleport: async (params) => {
        const player = gameState.players[params.player_id];
        if (!player) return { error: 'Jugador no encontrado' };
        
        player.position = { x: params.x, y: params.y, z: params.z };
        return relayToGame('move_player', { player_id: params.player_id, x: params.x, y: params.y, z: params.z });
    },

    // ---- MUNDO ----

    // Obtener estado del mundo
    get_world_info: async () => {
        return relayToGame('get_world_info', {});
    },

    // Colocar bloque
    place_block: async (params) => {
        return relayToGame('place_block', { x: params.x, y: params.y, z: params.z, type: params.type });
    },

    // Romper bloque
    break_block: async (params) => {
        return relayToGame('break_block', { x: params.x, y: params.y, z: params.z });
    },

    // Obtener bloque
    get_block: async (params) => {
        return relayToGame('get_block', { x: params.x, y: params.y, z: params.z });
    },

    // Obtener altura
    get_height: async (params) => {
        return relayToGame('get_height', { x: params.x, z: params.z });
    },

    // Obtener bloques en área
    get_blocks_in_area: async (params) => {
        return relayToGame('get_blocks_in_area', { x1: params.x1, y1: params.y1, z1: params.z1, x2: params.x2, y2: params.y2, z2: params.z2 });
    },

    // ---- CONSTRUCCIÓN ----

    // Aplanar terreno
    flat_terrain: async (params) => {
        return relayToGame('flat_terrain', { x: params.x, z: params.z, width: params.width, depth: params.depth, height: params.height, baseY: params.baseY });
    },

    // Llenar área
    fill_area: async (params) => {
        const { x, z, width, depth, height = 1, type, baseY = 20 } = params;
        const blocks = [];
        for (let dx = 0; dx < width; dx++) {
            for (let dz = 0; dz < depth; dz++) {
                for (let dy = 0; dy < height; dy++) {
                    blocks.push({ x: x + dx, y: baseY + dy, z: z + dz, type });
                }
            }
        }
        return relayToGame('apply_blocks', { blocks });
    },

    // Construir estructura
    build_structure: async (params) => {
        const structure = STRUCTURES[params.structure];
        if (!structure) return { error: `Estructura desconocida: ${params.structure}` };
        
        const blocks = structure.blocks.map(b => ({
            x: params.x + b.dx, y: params.y + b.dy, z: params.z + b.dz, type: b.type
        }));
        return relayToGame('apply_blocks', { blocks });
    },

    // Listar estructuras
    list_structures: async () => {
        return {
            structures: Object.entries(STRUCTURES).map(([key, s]) => ({
                id: key,
                name: s.name,
                blocks: s.blocks.length
            }))
        };
    },

    // Crear pared
    create_wall: async (params) => {
        const { x, z, length, height = 3, direction = 'x', type = 1, baseY = 20 } = params;
        const blocks = [];
        for (let i = 0; i < length; i++) {
            for (let dy = 0; dy < height; dy++) {
                const bx = direction === 'x' ? x + i : x;
                const bz = direction === 'z' ? z + i : z;
                blocks.push({ x: bx, y: baseY + dy, z: bz, type });
            }
        }
        return relayToGame('apply_blocks', { blocks });
    },

    // Crear suelo
    create_floor: async (params) => {
        const { x, z, width, depth, type = 4, baseY = 20 } = params;
        const blocks = [];
        for (let dx = 0; dx < width; dx++) {
            for (let dz = 0; dz < depth; dz++) {
                blocks.push({ x: x + dx, y: baseY, z: z + dz, type });
            }
        }
        return relayToGame('apply_blocks', { blocks });
    },

    // Plantar árbol
    plant_tree: async (params) => {
        return relayToGame('plant_tree', { x: params.x, z: params.z });
    },

    // ---- INVENTARIO ----

    // Obtener inventario
    get_inventory: async (params) => {
        const player = gameState.players[params.player_id];
        if (!player) return { error: 'Jugador no encontrado' };
        return { inventory: player.inventory || [] };
    },

    // Añadir item
    add_item: async (params) => {
        const player = gameState.players[params.player_id];
        if (!player) return { error: 'Jugador no encontrado' };
        if (!player.inventory) player.inventory = [];
        player.inventory.push({ type: params.type, count: params.count || 1 });
        return { success: true };
    },

    // ---- VISIÓN ----

    // Ver qué bloque está mirando el jugador
    get_view: async (params) => {
        const player = gameState.players[params.player_id];
        if (!player) return { error: 'Jugador no encontrado' };
        return relayToGame('get_view', { player_id: params.player_id, distance: params.distance });
    },

    // Obtener mapa 3D de bloques cercanos
    get_nearby_blocks: async (params) => {
        const player = gameState.players[params.player_id];
        if (!player) return { error: 'Jugador no encontrado' };
        return relayToGame('get_nearby_blocks', { player_id: params.player_id, radius: params.radius });
    },

    // Capturar screenshot de la cámara (lo renderiza el navegador)
    get_screenshot: async (params) => {
        const player = gameState.players[params.player_id];
        if (!player) return { error: 'Jugador no encontrado' };
        return relayToGame('get_screenshot', { player_id: params.player_id, width: params.width, height: params.height });
    },

    // Obtener entornos cercanos (enemigos, jugadores, etc.)
    get_nearby_entities: async (params) => {
        const player = gameState.players[params.player_id];
        if (!player) return { error: 'Jugador no encontrado' };
        return relayToGame('get_nearby_entities', { player_id: params.player_id, radius: params.radius });
    },

    // Obtener información del entorno (qué hay alrededor)
    get_environment: async (params) => {
        const player = gameState.players[params.player_id];
        if (!player) return { error: 'Jugador no encontrado' };
        return relayToGame('get_environment', { player_id: params.player_id });
    },

    // Vista top-down del terreno cercano
    get_top_down_view: async (params) => {
        const player = gameState.players[params.player_id];
        if (!player) return { error: 'Jugador no encontrado' };
        return relayToGame('get_top_down_view', { player_id: params.player_id, radius: params.radius });
    },

    // Matriz de bloques en visión de cámara (vista frontal)
    get_camera_matrix: async (params) => {
        const player = gameState.players[params.player_id];
        if (!player) return { error: 'Jugador no encontrado' };
        return relayToGame('get_camera_matrix', { player_id: params.player_id, width: params.width, height: params.height, depth: params.depth });
    },

    // ---- UTILIDADES ----

    // Listar tipos de bloques
    list_block_types: async () => {
        return {
            blocks: [
                { id: 0, name: 'Aire' },
                { id: 1, name: 'Hierba' },
                { id: 2, name: 'Tierra' },
                { id: 3, name: 'Piedra' },
                { id: 4, name: 'Madera' },
                { id: 5, name: 'Hojas' },
                { id: 6, name: 'Arena' },
                { id: 7, name: 'Agua' },
                { id: 8, name: 'Roca' },
                { id: 9, name: 'Tablones' }
            ]
        };
    },

    // Listar colores de avatar
    list_avatar_colors: async () => {
        return { colors: AVATAR_COLORS };
    },

    // Chat/mensaje
    send_message: async (params) => {
        const { player_id, message } = params;
        if (gameState.onChatMessage) {
            gameState.onChatMessage({ player_id, message });
        }
        return { success: true };
    }
};

// Función auxiliar para crear avatar
function createAvatar(params) {
    const { name, gender, hairStyle, hairColor, eyeColor, shirtColor, pantsColor, spawnX, spawnZ } = params;
    const id = nextPlayerId++;

    gameState.players[id] = {
        name: name || `IA_${id}`,
        isAI: true,
        gender: gender || 'male',
        position: { x: spawnX || 0, y: 30, z: spawnZ || 0 },
        rotation: { x: 0, y: 0 },
        health: 20,
        onGround: false,
        isFlying: false,
        selectedSlot: 0,
        inventory: [],
        config: { gender, hairStyle, hairColor, eyeColor, shirtColor, pantsColor }
    };

    return {
        success: true,
        playerId: id,
        name: gameState.players[id].name,
        message: `Avatar "${gameState.players[id].name}" creado con ID ${id}`
    };
}

// ============================================================
// SERVIDOR HTTP (sirve juego + MCP API)
// ============================================================
const MIME_TYPES = {
    '.html': 'text/html',
    '.js': 'application/javascript',
    '.css': 'text/css',
    '.json': 'application/json',
    '.png': 'image/png',
    '.jpg': 'image/jpeg',
    '.gif': 'image/gif',
    '.svg': 'image/svg+xml',
    '.ico': 'image/x-icon',
    '.woff': 'font/woff',
    '.woff2': 'font/woff2',
    '.mp3': 'audio/mpeg',
    '.ogg': 'audio/ogg',
    '.wav': 'audio/wav'
};

const ROOT_DIR = __dirname;

const server = http.createServer((req, res) => {
    res.setHeader('Access-Control-Allow-Origin', '*');
    res.setHeader('Access-Control-Allow-Methods', 'POST, OPTIONS, GET');
    res.setHeader('Access-Control-Allow-Headers', 'Content-Type');

    if (req.method === 'OPTIONS') {
        res.writeHead(200);
        res.end();
        return;
    }

    // === API Endpoints ===

    if (req.method === 'GET' && req.url === '/health') {
        res.writeHead(200, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify({ status: 'ok', players: Object.keys(gameState.players).length }));
        return;
    }

    if (req.method === 'GET' && req.url === '/tools') {
        res.writeHead(200, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify({ tools: Object.keys(mcpHandlers) }));
        return;
    }

    if (req.method === 'POST' && req.url === '/mcp') {
        let body = '';
        req.on('data', chunk => body += chunk);
        req.on('end', async () => {
            try {
                const request = JSON.parse(body);
                const handler = mcpHandlers[request.method];
                if (!handler) {
                    res.writeHead(400, { 'Content-Type': 'application/json' });
                    res.end(JSON.stringify({ error: `Método desconocido: ${request.method}` }));
                    return;
                }
                const result = await handler(request.params || {});
                res.writeHead(200, { 'Content-Type': 'application/json' });
                res.end(JSON.stringify(result));
            } catch (error) {
                res.writeHead(500, { 'Content-Type': 'application/json' });
                res.end(JSON.stringify({ error: error.message }));
            }
        });
        return;
    }

    // === Static file serving (juego) ===

    if (req.method === 'GET') {
        let urlPath = req.url.split('?')[0];
        if (urlPath === '/') urlPath = '/index.html';

        const filePath = path.join(ROOT_DIR, urlPath);
        const ext = path.extname(filePath).toLowerCase();

        // Security: prevent directory traversal
        if (!filePath.startsWith(ROOT_DIR)) {
            res.writeHead(403);
            res.end('Forbidden');
            return;
        }

        fs.readFile(filePath, (err, data) => {
            if (err) {
                res.writeHead(404);
                res.end('Not found');
                return;
            }
            const mime = MIME_TYPES[ext] || 'application/octet-stream';
            res.writeHead(200, { 'Content-Type': mime, 'Cache-Control': 'no-store' });
            res.end(data);
        });
        return;
    }

    res.writeHead(404);
    res.end('Not found');
});

// ============================================================
// WEBSOCKET SERVER
// ============================================================
const wss = new WebSocket.Server({ server });

wss.on('connection', (ws) => {
    console.log('[WS] Juego conectado');
    gameClients.push(ws);

    ws.on('message', (message) => {
        try {
            const data = JSON.parse(message.toString());

            // Respuesta de un comando relay (correlación por id)
            if (data.id && pendingMcp[data.id]) {
                const { resolve, timer } = pendingMcp[data.id];
                clearTimeout(timer);
                delete pendingMcp[data.id];
                const { id, ...rest } = data;
                resolve(rest);
                return;
            }

            // Actualizar estado desde el juego
            if (data.type === 'state_update' && data.state && data.state.players) {
                Object.entries(data.state.players).forEach(([id, p]) => {
                    if (gameState.players[id]) {
                        if (p.position) gameState.players[id].position = p.position;
                        if (p.health !== undefined) gameState.players[id].health = p.health;
                        if (p.rotation) gameState.players[id].rotation = p.rotation;
                        if (p.onGround !== undefined) gameState.players[id].onGround = p.onGround;
                        if (p.isFlying !== undefined) gameState.players[id].isFlying = p.isFlying;
                    }
                });
            }
        } catch (e) {
            // Silently ignore parse errors from game
        }
    });

    ws.on('close', () => {
        gameClients = gameClients.filter(c => c !== ws);
    });

    ws.on('error', () => {
        gameClients = gameClients.filter(c => c !== ws);
    });
});

// ============================================================
// GLOBAL ERROR HANDLER
// ============================================================
process.on('uncaughtException', (err) => {
    console.error('[FATAL]', err.message);
});

process.on('unhandledRejection', (err) => {
    console.error('[REJECT]', err);
});

// ============================================================
// EXPORTS
// ============================================================
module.exports = { gameState, mcpHandlers, STRUCTURES, AVATAR_COLORS, server };

if (require.main === module) {
    const PORT = process.env.PORT || 9000;
    server.listen(PORT, () => {
        const url = `http://localhost:${PORT}`;
        console.log(`\n🎮 VoxelQuest - Servidor unificado v4.0`);
        console.log(`   Juego:     ${url}`);
        console.log(`   MCP API:   ${url}/mcp`);
        console.log(`   WebSocket: ws://localhost:${PORT}`);
        console.log(`   Health:    ${url}/health`);
        console.log(`   Tools:     ${url}/tools\n`);

        // Abrir navegador automáticamente
        try {
            const { exec } = require('child_process');
            const cmd = process.platform === 'darwin' ? 'open' : process.platform === 'win32' ? 'start' : 'xdg-open';
            exec(`${cmd} ${url}`);
        } catch (e) {}
    });
}
