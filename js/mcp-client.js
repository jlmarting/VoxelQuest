/**
 * VoxelQuest MCP Client
 * 
 * Sincroniza el estado del juego con el servidor MCP.
 * Permite que agentes IA controlen jugadores remotamente.
 */

class MCPClient {
    constructor(game) {
        this.game = game;
        this.connected = false;
        this.ws = null;
        // Conectar al mismo host que sirve el juego
        this.serverUrl = `ws://${window.location.hostname || 'localhost'}:${window.location.port || 9000}`;
        this.syncInterval = null;
        this.playerStates = {};
    }

    // Conectar al servidor MCP
    async connect() {
        return new Promise((resolve, reject) => {
            try {
                this.ws = new WebSocket(this.serverUrl);
                
                this.ws.onopen = () => {
                    this.connected = true;
                    console.log('[MCP] Conectado al servidor');
                    this.startSync();
                    resolve();
                };
                
                this.ws.onmessage = (event) => {
                    this.handleMessage(JSON.parse(event.data));
                };
                
                this.ws.onclose = () => {
                    this.connected = false;
                    console.log('[MCP] Desconectado');
                    this.stopSync();
                };
                
                this.ws.onerror = (error) => {
                    console.error('[MCP] Error:', error);
                    reject(error);
                };
            } catch (error) {
                reject(error);
            }
        });
    }

    // Manejar mensajes del servidor
    handleMessage(data) {
        console.log('[MCP] Mensaje recibido:', JSON.stringify(data).substring(0, 100));
        
        let response = { id: data.id };

        try {
            if (data.method === 'move_player') {
                console.log('[MCP] Moviendo jugador', data.params.player_id);
                const player = this.game[`player${data.params.player_id}`];
                if (player) {
                    player.position.set(data.params.x, data.params.y, data.params.z);
                    response.success = true;
                    response.position = { x: data.params.x, y: data.params.y, z: data.params.z };
                    console.log('[MCP] Jugador movido a', data.params.x, data.params.y, data.params.z);
                } else {
                    response.error = 'Player not found';
                }
            } else if (data.method === 'list_players') {
                response.players = [
                    { id: 1, name: 'Jugador 1', position: this.game.player1.position },
                    { id: 2, name: 'Jugador 2', position: this.game.player2.position }
                ];
            } else if (data.method === 'place_block') {
                this.game.world.setBlock(data.params.x, data.params.y, data.params.z, data.params.type);
                response.success = true;
            } else if (data.method === 'break_block') {
                this.game.world.setBlock(data.params.x, data.params.y, data.params.z, 0);
                response.success = true;
            } else if (data.method === 'execute_command') {
                if (this.game.gameConsole) {
                    this.game.gameConsole.executeRemoteCommand(data.params.command);
                }
                response.success = true;
            } else {
                response.error = 'Unknown method';
            }
        } catch (e) {
            response.error = e.message;
            console.error('[MCP] Error procesando:', e);
        }

        // Send response back
        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
            console.log('[MCP] Enviando respuesta:', JSON.stringify(response).substring(0, 100));
            this.ws.send(JSON.stringify(response));
        }
    }

    // Ejecutar comando recibido del servidor
    executeCommand(data) {
        const { command, params } = data;
        
        switch (command) {
            case 'move_player':
                this.game[`player${params.player_id}`].position.set(params.x, params.y, params.z);
                break;
            case 'place_block':
                this.game.world.setBlock(params.x, params.y, params.z, params.type);
                break;
            case 'break_block':
                this.game.world.setBlock(params.x, params.y, params.z, 0);
                break;
        }
    }

    // Iniciar sincronización periódica
    startSync() {
        this.syncInterval = setInterval(() => {
            this.syncState();
        }, 1000); // Cada segundo
    }

    // Detener sincronización
    stopSync() {
        if (this.syncInterval) {
            clearInterval(this.syncInterval);
            this.syncInterval = null;
        }
    }

    // Sincronizar estado del juego con el servidor
    syncState() {
        if (!this.connected || !this.game.running) return;

        const state = {
            players: {},
            world: {
                seed: this.game.world.noise.seed,
                chunkCount: this.game.world.chunks.size
            },
            timeOfDay: this.game.dayNight.timeOfDay,
            isNight: this.game.dayNight.isNight()
        };

        // Sincronizar jugadores
        [1, 2].forEach(id => {
            const player = this.game[`player${id}`];
            if (player) {
                state.players[id] = {
                    name: this.game[`playerModel${id}`]?.config?.name || `Jugador ${id}`,
                    position: { x: player.position.x, y: player.position.y, z: player.position.z },
                    health: player.health,
                    isAI: false,
                    inventory: player.inventory.slots.filter(s => s !== null)
                };
            }
        });

        this.playerStates = state.players;
        return state;
    }

    // Obtener estado de un jugador
    getPlayerState(playerId) {
        return this.playerStates[playerId] || null;
    }

    // Enviar estado al servidor
    sendState() {
        if (!this.connected) return;
        
        const state = this.syncState();
        this.ws.send(JSON.stringify({
            type: 'state_update',
            state
        }));
    }

    // Desconectar
    disconnect() {
        this.stopSync();
        if (this.ws) {
            this.ws.close();
        }
    }
}

// Exportar
window.MCPClient = MCPClient;
