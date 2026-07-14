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
        
        sendToGame({ command: 'move_player', player_id: params.player_id, ...player.position });
        return { success: true, position: player.position };
    },

    // Mover relativo (adelante/atrás/izquierda/derecha)
    move_relative: async (params) => {
        const player = gameState.players[params.player_id];
        if (!player) return { error: 'Jugador no encontrado' };
        
        const rotation = player.rotation || { x: 0, y: 0 };
        const distance = params.distance || 1;
        
        // Calcular dirección basada en rotación
        const forward = { x: -Math.sin(rotation.y), z: -Math.cos(rotation.y) };
        const right = { x: Math.cos(rotation.y), z: -Math.sin(rotation.y) };
        
        let dx = 0, dz = 0;
        if (params.forward) { dx += forward.x * distance; dz += forward.z * distance; }
        if (params.backward) { dx -= forward.x * distance; dz -= forward.z * distance; }
        if (params.left) { dx -= right.x * distance; dz -= right.z * distance; }
        if (params.right) { dx += right.x * distance; dz += right.z * distance; }
        
        player.position.x += dx;
        player.position.z += dz;
        
        sendToGame({ command: 'move_player', player_id: params.player_id, ...player.position });
        return { success: true, position: player.position };
    },

    // Saltar
    jump: async (params) => {
        const player = gameState.players[params.player_id];
        if (!player) return { error: 'Jugador no encontrado' };
        
        const height = params.height || 3;
        player.position.y += height;
        player.onGround = false;
        
        // Simular caída
        setTimeout(() => {
            if (gameState.players[params.player_id]) {
                gameState.players[params.player_id].position.y -= height;
                gameState.players[params.player_id].onGround = true;
            }
        }, 500);
        
        sendToGame({ command: 'jump', player_id: params.player_id, height });
        return { success: true, position: player.position };
    },

    // ---- CONTROLES DE VUELO ----

    // Volar arriba
    fly_up: async (params) => {
        const player = gameState.players[params.player_id];
        if (!player) return { error: 'Jugador no encontrado' };
        if (!player.isFlying) return { error: 'Jugador no está volando' };
        
        const distance = params.distance || 1;
        player.position.y += distance;
        
        sendToGame({ command: 'move_player', player_id: params.player_id, ...player.position });
        return { success: true, position: player.position };
    },

    // Volar abajo
    fly_down: async (params) => {
        const player = gameState.players[params.player_id];
        if (!player) return { error: 'Jugador no encontrado' };
        if (!player.isFlying) return { error: 'Jugador no está volando' };
        
        const distance = params.distance || 1;
        player.position.y -= distance;
        
        sendToGame({ command: 'move_player', player_id: params.player_id, ...player.position });
        return { success: true, position: player.position };
    },

    // Alternar modo vuelo
    toggle_fly: async (params) => {
        const player = gameState.players[params.player_id];
        if (!player) return { error: 'Jugador no encontrado' };
        
        player.isFlying = !player.isFlying;
        sendToGame({ command: 'toggle_fly', player_id: params.player_id, isFlying: player.isFlying });
        return { success: true, isFlying: player.isFlying };
    },

    // ---- CONTROLES DE CÁMARA ----

    // Mirar (rotar cámara)
    look: async (params) => {
        const player = gameState.players[params.player_id];
        if (!player) return { error: 'Jugador no encontrado' };
        
        if (!player.rotation) player.rotation = { x: 0, y: 0 };
        
        // Rotación absoluta
        if (params.yaw !== undefined) player.rotation.y = params.yaw;
        if (params.pitch !== undefined) player.rotation.x = Math.max(-Math.PI/2 + 0.1, Math.min(Math.PI/2 - 0.1, params.pitch));
        
        // Rotación relativa
        if (params.yaw_delta) player.rotation.y += params.yaw_delta;
        if (params.pitch_delta) player.rotation.x = Math.max(-Math.PI/2 + 0.1, Math.min(Math.PI/2 - 0.1, player.rotation.x + params.pitch_delta));
        
        sendToGame({ command: 'look', player_id: params.player_id, rotation: player.rotation });
        return { success: true, rotation: player.rotation };
    },

    // Obtener rotación
    get_rotation: async (params) => {
        const player = gameState.players[params.player_id];
        if (!player) return { error: 'Jugador no encontrado' };
        return { rotation: player.rotation || { x: 0, y: 0 } };
    },

    // Alternar modo cámara
    toggle_camera: async (params) => {
        const player = gameState.players[params.player_id];
        if (!player) return { error: 'Jugador no encontrado' };
        
        if (!player.cameraMode) player.cameraMode = 0;
        player.cameraMode = (player.cameraMode + 1) % 3;
        
        const modes = ['first_person', 'third_person_close', 'third_person_far'];
        sendToGame({ command: 'toggle_camera', player_id: params.player_id, cameraMode: player.cameraMode });
        return { success: true, cameraMode: player.cameraMode, modeName: modes[player.cameraMode] };
    },

    // ---- CONTROLES DE INVENTARIO ----

    // Seleccionar slot
    select_slot: async (params) => {
        const player = gameState.players[params.player_id];
        if (!player) return { error: 'Jugador no encontrado' };
        
        const slot = params.slot;
        if (slot < 0 || slot > 8) return { error: 'Slot inválido (0-8)' };
        
        player.selectedSlot = slot;
        sendToGame({ command: 'select_slot', player_id: params.player_id, slot });
        return { success: true, selectedSlot: slot };
    },

    // Seleccionar slot siguiente
    next_slot: async (params) => {
        const player = gameState.players[params.player_id];
        if (!player) return { error: 'Jugador no encontrado' };
        
        if (!player.selectedSlot) player.selectedSlot = 0;
        player.selectedSlot = (player.selectedSlot + 1) % 9;
        
        sendToGame({ command: 'select_slot', player_id: params.player_id, slot: player.selectedSlot });
        return { success: true, selectedSlot: player.selectedSlot };
    },

    // Seleccionar slot anterior
    prev_slot: async (params) => {
        const player = gameState.players[params.player_id];
        if (!player) return { error: 'Jugador no encontrado' };
        
        if (!player.selectedSlot) player.selectedSlot = 0;
        player.selectedSlot = (player.selectedSlot + 8) % 9;
        
        sendToGame({ command: 'select_slot', player_id: params.player_id, slot: player.selectedSlot });
        return { success: true, selectedSlot: player.selectedSlot };
    },

    // ---- CONTROLES DE BLOQUES ----

    // Colocar bloque (como el jugador - en la dirección que mira)
    place_block_as_player: async (params) => {
        const player = gameState.players[params.player_id];
        if (!player) return { error: 'Jugador no encontrado' };
        if (!gameState.world) return { error: 'Mundo no inicializado' };
        
        const rotation = player.rotation || { x: 0, y: 0 };
        const eyeY = player.position.y + 1.6;
        
        // Raycast simplificado hacia adelante
        const dir = { x: -Math.sin(rotation.y) * Math.cos(rotation.x), y: -Math.sin(rotation.x), z: -Math.cos(rotation.y) * Math.cos(rotation.x) };
        const maxDist = 5;
        
        for (let i = 1; i <= maxDist * 10; i++) {
            const px = player.position.x + dir.x * i * 0.1;
            const py = eyeY + dir.y * i * 0.1;
            const pz = player.position.z + dir.z * i * 0.1;
            const bx = Math.floor(px), by = Math.floor(py), bz = Math.floor(pz);
            
            const block = gameState.world.getBlock(bx, by, bz);
            if (block !== 0) {
                // Colocar en la cara opuesta
                const nx = Math.floor(px - dir.x * 0.1);
                const ny = Math.floor(py - dir.y * 0.1);
                const nz = Math.floor(pz - dir.z * 0.1);
                
                gameState.world.setBlock(nx, ny, nz, params.type || 1);
                sendToGame({ command: 'place_block', x: nx, y: ny, z: nz, type: params.type || 1 });
                return { success: true, position: { x: nx, y: ny, z: nz } };
            }
        }
        return { error: 'No hay bloque cerca para colocar' };
    },

    // Romper bloque (como el jugador - en la dirección que mira)
    break_block_as_player: async (params) => {
        const player = gameState.players[params.player_id];
        if (!player) return { error: 'Jugador no encontrado' };
        if (!gameState.world) return { error: 'Mundo no inicializado' };
        
        const rotation = player.rotation || { x: 0, y: 0 };
        const eyeY = player.position.y + 1.6;
        
        const dir = { x: -Math.sin(rotation.y) * Math.cos(rotation.x), y: -Math.sin(rotation.x), z: -Math.cos(rotation.y) * Math.cos(rotation.x) };
        const maxDist = 5;
        
        for (let i = 1; i <= maxDist * 10; i++) {
            const px = player.position.x + dir.x * i * 0.1;
            const py = eyeY + dir.y * i * 0.1;
            const pz = player.position.z + dir.z * i * 0.1;
            const bx = Math.floor(px), by = Math.floor(py), bz = Math.floor(pz);
            
            const block = gameState.world.getBlock(bx, by, bz);
            if (block !== 0 && block !== 10) { // No romper bedrock
                gameState.world.setBlock(bx, by, bz, 0);
                sendToGame({ command: 'break_block', x: bx, y: by, z: bz });
                return { success: true, position: { x: bx, y: by, z: bz }, blockType: block };
            }
        }
        return { error: 'No hay bloque cerca para romper' };
    },

    // Mover jugador
    move_player: async (params) => {
        const player = gameState.players[params.player_id];
        if (!player) return { error: 'Jugador no encontrado' };
        
        player.position = { x: params.x, y: params.y, z: params.z };
        return { success: true, position: player.position };
    },

    // Saltar
    jump: async (params) => {
        const player = gameState.players[params.player_id];
        if (!player) return { error: 'Jugador no encontrado' };
        
        const height = params.height || 3;
        const originalY = player.position.y;
        player.position.y = originalY + height;
        
        // Simular caída después de un breve delay
        setTimeout(() => {
            if (gameState.players[params.player_id]) {
                gameState.players[params.player_id].position.y = originalY;
            }
        }, 500);
        
        return { 
            success: true, 
            position: player.position,
            message: `Jugador ${params.player_id} saltó ${height} bloques`
        };
    },

    // Teletransportar
    teleport: async (params) => {
        const player = gameState.players[params.player_id];
        if (!player) return { error: 'Jugador no encontrado' };
        
        player.position = { x: params.x, y: params.y, z: params.z };
        return { success: true, position: player.position };
    },

    // ---- MUNDO ----

    // Obtener estado del mundo
    get_world_info: async () => {
        return {
            seed: gameState.seed,
            chunkCount: gameState.world ? gameState.world.chunks.size : 0,
            timeOfDay: gameState.dayNight ? gameState.dayNight.timeOfDay : 0,
            isNight: gameState.dayNight ? gameState.dayNight.isNight() : false
        };
    },

    // Colocar bloque
    place_block: async (params) => {
        if (!gameState.world) return { error: 'Mundo no inicializado' };
        gameState.world.setBlock(params.x, params.y, params.z, params.type);
        return { success: true, position: { x: params.x, y: params.y, z: params.z } };
    },

    // Romper bloque
    break_block: async (params) => {
        if (!gameState.world) return { error: 'Mundo no inicializado' };
        const block = gameState.world.getBlock(params.x, params.y, params.z);
        gameState.world.setBlock(params.x, params.y, params.z, 0);
        return { success: true, blockType: block };
    },

    // Obtener bloque
    get_block: async (params) => {
        if (!gameState.world) return { error: 'Mundo no inicializado' };
        return { x: params.x, y: params.y, z: params.z, type: gameState.world.getBlock(params.x, params.y, params.z) };
    },

    // Obtener altura
    get_height: async (params) => {
        if (!gameState.world) return { error: 'Mundo no inicializado' };
        for (let y = 63; y >= 0; y--) {
            const block = gameState.world.getBlock(params.x, y, params.z);
            if (block !== 0) return { x: params.x, y, z: params.z, height: y, blockType: block };
        }
        return { x: params.x, y: 0, z: params.z, height: 0, blockType: 0 };
    },

    // Obtener bloques en área
    get_blocks_in_area: async (params) => {
        if (!gameState.world) return { error: 'Mundo no inicializado' };
        const blocks = [];
        const { x1, y1, z1, x2, y2, z2 } = params;
        for (let x = x1; x <= x2; x++) {
            for (let y = y1; y <= y2; y++) {
                for (let z = z1; z <= z2; z++) {
                    const block = gameState.world.getBlock(x, y, z);
                    if (block !== 0) blocks.push({ x, y, z, type: block });
                }
            }
        }
        return { blocks, count: blocks.length };
    },

    // ---- CONSTRUCCIÓN ----

    // Aplanar terreno
    flat_terrain: async (params) => {
        if (!gameState.world) return { error: 'Mundo no inicializado' };
        const { x, z, width, depth, height = 30, baseY = 0 } = params;
        let removed = 0;
        for (let dx = 0; dx < width; dx++) {
            for (let dz = 0; dz < depth; dz++) {
                for (let dy = 0; dy < height; dy++) {
                    const block = gameState.world.getBlock(x + dx, baseY + dy, z + dz);
                    if (block !== 0 && block !== 7) {
                        gameState.world.setBlock(x + dx, baseY + dy, z + dz, 0);
                        removed++;
                    }
                }
            }
        }
        return { success: true, blocksRemoved: removed };
    },

    // Llenar área
    fill_area: async (params) => {
        if (!gameState.world) return { error: 'Mundo no inicializado' };
        const { x, z, width, depth, height = 1, type, baseY = 20 } = params;
        let placed = 0;
        for (let dx = 0; dx < width; dx++) {
            for (let dz = 0; dz < depth; dz++) {
                for (let dy = 0; dy < height; dy++) {
                    gameState.world.setBlock(x + dx, baseY + dy, z + dz, type);
                    placed++;
                }
            }
        }
        return { success: true, blocksPlaced: placed };
    },

    // Construir estructura
    build_structure: async (params) => {
        if (!gameState.world) return { error: 'Mundo no inicializado' };
        const structure = STRUCTURES[params.structure];
        if (!structure) return { error: `Estructura desconocida: ${params.structure}` };
        
        let placed = 0;
        for (const block of structure.blocks) {
            gameState.world.setBlock(params.x + block.dx, params.y + block.dy, params.z + block.dz, block.type);
            placed++;
        }
        return { success: true, blocksPlaced: placed, structure: structure.name };
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
        if (!gameState.world) return { error: 'Mundo no inicializado' };
        const { x, z, length, height = 3, direction = 'x', type = 1, baseY = 20 } = params;
        let placed = 0;
        for (let i = 0; i < length; i++) {
            for (let dy = 0; dy < height; dy++) {
                const bx = direction === 'x' ? x + i : x;
                const bz = direction === 'z' ? z + i : z;
                gameState.world.setBlock(bx, baseY + dy, bz, type);
                placed++;
            }
        }
        return { success: true, blocksPlaced: placed };
    },

    // Crear suelo
    create_floor: async (params) => {
        if (!gameState.world) return { error: 'Mundo no inicializado' };
        const { x, z, width, depth, type = 4, baseY = 20 } = params;
        let placed = 0;
        for (let dx = 0; dx < width; dx++) {
            for (let dz = 0; dz < depth; dz++) {
                gameState.world.setBlock(x + dx, baseY, z + dz, type);
                placed++;
            }
        }
        return { success: true, blocksPlaced: placed };
    },

    // Plantar árbol
    plant_tree: async (params) => {
        if (!gameState.world) return { error: 'Mundo no inicializado' };
        const { x, z } = params;
        let baseY = 0;
        for (let y = 63; y >= 0; y--) {
            if (gameState.world.getBlock(x, y, z) !== 0) { baseY = y + 1; break; }
        }
        for (let dy = 0; dy < 5; dy++) gameState.world.setBlock(x, baseY + dy, z, 4);
        for (let dx = -2; dx <= 2; dx++) {
            for (let dz = -2; dz <= 2; dz++) {
                for (let dy = 3; dy <= 6; dy++) {
                    if (Math.abs(dx) + Math.abs(dz) + Math.abs(dy - 4) < 4) {
                        gameState.world.setBlock(x + dx, baseY + dy, z + dz, 5);
                    }
                }
            }
        }
        return { success: true, y: baseY };
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
        if (!gameState.world) return { error: 'Mundo no inicializado' };

        const { x, y, z } = player.position;
        const eyeY = y + 1.6;

        // Raycast en la dirección que mira (simplificado: hacia -Z por defecto)
        const dir = { x: 0, y: -0.2, z: -1 }; // Dirección frontal
        const maxDist = params.distance || 8;

        let lastBlock = null;
        for (let i = 0; i < maxDist * 10; i++) {
            const px = x + dir.x * i * 0.1;
            const py = eyeY + dir.y * i * 0.1;
            const pz = z + dir.z * i * 0.1;
            const bx = Math.floor(px), by = Math.floor(py), bz = Math.floor(pz);
            
            const block = gameState.world.getBlock(bx, by, bz);
            if (block !== 0) {
                return {
                    position: { x: bx, y: by, z: bz },
                    blockType: block,
                    distance: i * 0.1,
                    face: lastBlock || { x: bx, y: by + 1, z: bz }
                };
            }
            lastBlock = { x: bx, y: by, z: bz };
        }
        return { position: null, blockType: 0, message: 'No hay bloques visibles' };
    },

    // Obtener mapa 3D de bloques cercanos
    get_nearby_blocks: async (params) => {
        const player = gameState.players[params.player_id];
        if (!player) return { error: 'Jugador no encontrado' };
        if (!gameState.world) return { error: 'Mundo no inicializado' };

        const { x, y, z } = player.position;
        const radius = params.radius || 5;
        const blocks = [];

        for (let dx = -radius; dx <= radius; dx++) {
            for (let dy = -2; dy <= 3; dy++) {
                for (let dz = -radius; dz <= radius; dz++) {
                    const bx = Math.floor(x) + dx;
                    const by = Math.floor(y) + dy;
                    const bz = Math.floor(z) + dz;
                    const block = gameState.world.getBlock(bx, by, bz);
                    if (block !== 0) {
                        blocks.push({ x: bx, y: by, z: bz, type: block });
                    }
                }
            }
        }

        // Convertir a mapa 2D para vista superior
        const map2d = {};
        blocks.forEach(b => {
            const key = `${b.x},${b.z}`;
            if (!map2d[key] || b.y > map2d[key].y) {
                map2d[key] = { x: b.x, y: b.y, z: b.z, type: b.type };
            }
        });

        return {
            blocks,
            map2d: Object.values(map2d),
            count: blocks.length,
            playerPosition: { x: Math.floor(x), y: Math.floor(y), z: Math.floor(z) }
        };
    },

    // Capturar screenshot de la cámara
    get_screenshot: async (params) => {
        const player = gameState.players[params.player_id];
        if (!player) return { error: 'Jugador no encontrado' };
        if (!gameState.scene) return { error: 'Escena no disponible' };

        // Crear cámara temporal para capturar
        const camera = new THREE.PerspectiveCamera(75, 16/9, 0.1, 1000);
        camera.position.set(player.position.x, player.position.y + 1.6, player.position.z);
        camera.lookAt(player.position.x, player.position.y + 1, player.position.z - 10);

        // Renderer temporal
        const canvas = document.createElement('canvas');
        canvas.width = params.width || 640;
        canvas.height = params.height || 360;
        const renderer = new THREE.WebGLRenderer({ canvas, antialias: false });
        renderer.setSize(canvas.width, canvas.height);

        // Renderizar
        renderer.render(gameState.scene, camera);
        
        // Convertir a base64
        const imageData = canvas.toDataURL('image/jpeg', 0.8);
        renderer.dispose();

        return {
            image: imageData,
            width: canvas.width,
            height: canvas.height,
            format: 'jpeg'
        };
    },

    // Obtener entornos cercanos (enemigos, jugadores, etc.)
    get_nearby_entities: async (params) => {
        const player = gameState.players[params.player_id];
        if (!player) return { error: 'Jugador no encontrado' };

        const { x, y, z } = player.position;
        const radius = params.radius || 20;
        const entities = [];

        // Otros jugadores
        Object.entries(gameState.players).forEach(([id, p]) => {
            if (parseInt(id) !== params.player_id) {
                const dist = Math.sqrt(
                    (p.position.x - x) ** 2 + 
                    (p.position.y - y) ** 2 + 
                    (p.position.z - z) ** 2
                );
                if (dist <= radius) {
                    entities.push({
                        type: 'player',
                        id: parseInt(id),
                        name: p.name,
                        position: p.position,
                        distance: Math.round(dist)
                    });
                }
            }
        });

        // Enemigos
        if (gameState.enemyManager) {
            gameState.enemyManager.enemies.forEach((enemy, i) => {
                const dist = Math.sqrt(
                    (enemy.position.x - x) ** 2 + 
                    (enemy.position.y - y) ** 2 + 
                    (enemy.position.z - z) ** 2
                );
                if (dist <= radius) {
                    entities.push({
                        type: 'enemy',
                        enemyType: enemy.type,
                        position: { x: enemy.position.x, y: enemy.position.y, z: enemy.position.z },
                        health: enemy.health,
                        distance: Math.round(dist)
                    });
                }
            });
        }

        return { entities, count: entities.length };
    },

    // Obtener información del entorno (qué hay alrededor)
    get_environment: async (params) => {
        const player = gameState.players[params.player_id];
        if (!player) return { error: 'Jugador no encontrado' };
        if (!gameState.world) return { error: 'Mundo no inicializado' };

        const { x, y, z } = player.position;
        const bx = Math.floor(x), by = Math.floor(y), bz = Math.floor(z);

        const blockBelow = gameState.world.getBlock(bx, by - 1, bz);
        
        const adjacent = {
            north: gameState.world.getBlock(bx, by, bz - 1),
            south: gameState.world.getBlock(bx, by, bz + 1),
            east: gameState.world.getBlock(bx + 1, by, bz),
            west: gameState.world.getBlock(bx - 1, by, bz),
            above: gameState.world.getBlock(bx, by + 1, bz),
            below: blockBelow
        };

        return {
            position: { x: bx, y: by, z: bz },
            blockBelow,
            adjacent,
            timeOfDay: gameState.dayNight ? gameState.dayNight.timeOfDay : 0.5,
            isNight: gameState.dayNight ? gameState.dayNight.isNight() : false
        };
    },

    // Vista top-down del terreno cercano
    get_top_down_view: async (params) => {
        const player = gameState.players[params.player_id];
        if (!player) return { error: 'Jugador no encontrado' };
        if (!gameState.world) return { error: 'Mundo no inicializado' };

        const { x, y, z } = player.position;
        const radius = params.radius || 10;
        const bx = Math.floor(x), bz = Math.floor(z);

        // Colores para representación visual
        const symbolMap = {
            0: ' ',  // Aire
            1: '.',  // Hierba
            2: ',',  // Tierra
            3: '#',  // Piedra
            4: 'T',  // Madera
            5: '*',  // Hojas
            6: '~',  // Arena
            7: '≈',  // Agua
            8: 'O',  // Roca
            9: '=',  // Tablones
            10: 'X'  // Bedrock
        };

        const nameMap = {
            0: 'air', 1: 'grass', 2: 'dirt', 3: 'stone', 4: 'wood',
            5: 'leaves', 6: 'sand', 7: 'water', 8: 'cobble', 9: 'planks', 10: 'bedrock'
        };

        // Construir mapa 2D (vista superior)
        const map = [];
        const blockData = [];
        let playerRow = -1, playerCol = -1;

        for (let dz = -radius; dz <= radius; dz++) {
            let row = '';
            const rowBlocks = [];
            for (let dx = -radius; dx <= radius; dx++) {
                const wx = bx + dx;
                const wz = bz + dz;

                // Encontrar bloque más alto en esta columna
                let topBlock = 0;
                for (let wy = 63; wy >= 0; wy--) {
                    const block = gameState.world.getBlock(wx, wy, wz);
                    if (block !== 0) {
                        topBlock = block;
                        break;
                    }
                }

                // Marcar jugador
                if (dx === 0 && dz === 0) {
                    row += '@';
                    playerRow = map.length;
                    playerCol = row.length - 1;
                } else {
                    row += symbolMap[topBlock] || '?';
                }

                rowBlocks.push({ x: wx, z: wz, topBlock, typeName: nameMap[topBlock] || 'unknown' });
            }
            map.push(row);
            blockData.push(rowBlocks);
        }

        return {
            map,
            blockData,
            playerPosition: { x: bx, y: Math.floor(player.position.y), z: bz },
            size: radius * 2 + 1,
            legend: {
                '@': 'Jugador',
                ' ': 'Aire',
                '.': 'Hierba',
                ',': 'Tierra',
                '#': 'Piedra',
                'T': 'Madera',
                '*': 'Hojas',
                '~': 'Arena',
                '≈': 'Agua',
                'O': 'Roca',
                '=': 'Tablones'
            }
        };
    },

    // Matriz de bloques en visión de cámara (vista frontal)
    get_camera_matrix: async (params) => {
        const player = gameState.players[params.player_id];
        if (!player) return { error: 'Jugador no encontrado' };
        if (!gameState.world) return { error: 'Mundo no inicializado' };

        const { x, y, z } = player.position;
        const eyeY = y + 1.6;
        const width = params.width || 11;  // Ancho delCampo de visión
        const height = params.height || 7; // Altura del campo de visión
        const depth = params.depth || 8;   // Profundidad de escaneo

        const nameMap = {
            0: 'air', 1: 'grass', 2: 'dirt', 3: 'stone', 4: 'wood',
            5: 'leaves', 6: 'sand', 7: 'water', 8: 'cobble', 9: 'planks', 10: 'bedrock'
        };

        // Escanear bloques en el campo de visión (hacia adelante -Z)
        const matrix = [];
        const blockInfo = [];

        for (let row = 0; row < height; row++) {
            const matrixRow = [];
            const infoRow = [];
            for (let col = 0; col < width; col++) {
                // Convertir coordenadas de pantalla a coordenadas del mundo
                const worldX = Math.floor(x) + col - Math.floor(width / 2);
                const worldY = Math.floor(eyeY) + row - Math.floor(height / 2);
                const worldZ = Math.floor(z) - 1; // Un bloque adelante

                // Escanear en profundidad
                let foundBlock = 0;
                let foundDist = depth;
                for (let d = 0; d < depth; d++) {
                    const bz = worldZ - d;
                    const block = gameState.world.getBlock(worldX, worldY, bz);
                    if (block !== 0) {
                        foundBlock = block;
                        foundDist = d;
                        break;
                    }
                }

                const symbol = foundBlock === 0 ? ' ' : '#';
                matrixRow.push(symbol);
                infoRow.push({
                    worldPos: { x: worldX, y: worldY, z: worldZ },
                    blockType: foundBlock,
                    typeName: nameMap[foundBlock] || 'unknown',
                    distance: foundDist
                });
            }
            matrix.push(matrixRow.join(''));
            blockInfo.push(infoRow);
        }

        return {
            matrix,
            blockInfo,
            playerPosition: { x: Math.floor(x), y: Math.floor(eyeY), z: Math.floor(z) },
            fieldOfView: { width, height, depth },
            legend: {
                ' ': 'Aire',
                '#': 'Bloque sólido'
            }
        };
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
            res.writeHead(200, { 'Content-Type': mime });
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
