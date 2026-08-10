class ServerBridge {
    constructor(game) {
        this.game = game;
        this.ws = null;
        this.connected = false;
        this.playerId = null;
        this.seq = 0;
        this._pendingBreak = false;
        this._pendingPlace = false;
        this._lastInputSent = 0;
        this._lastActivityNotice = 0;
        this._wsUrl = null;
        this._reconnectDelay = 1000;
        this._reconnectTimer = null;
        this._objectCount = 0;
    }

    connect(url) {
        this._wsUrl = url;
        return this._connectInternal(url);
    }

    _connectInternal(url) {
        return new Promise((resolve, reject) => {
            try {
                console.log('[Bridge] Conectando a', url);
                this.ws = new WebSocket(url);

                this.ws.onopen = () => {
                    this.connected = true;
                    this._reconnectDelay = 1000; // reset backoff
                    console.log('[Bridge] WebSocket conectado');
                };

                this.ws.onmessage = (event) => {
                    const data = JSON.parse(event.data);
                    this._handleMessage(data);
                };

                this.ws.onclose = (e) => {
                    this.connected = false;
                    console.log('[Bridge] Desconectado:', e.code, e.reason, '— reintentando en', this._reconnectDelay, 'ms');
                    this._scheduleReconnect();
                };

                this.ws.onerror = (err) => {
                    console.error('[Bridge] Error WS:', err);
                    reject(err);
                };

                const check = setInterval(() => {
                    if (this.playerId !== null || !this.connected) {
                        clearInterval(check);
                        if (this.connected) {
                            console.log('[Bridge] Player ID:', this.playerId);
                            resolve();
                        }
                    }
                }, 50);
            } catch (err) {
                reject(err);
            }
        });
    }

    _scheduleReconnect() {
        if (this._reconnectTimer) clearTimeout(this._reconnectTimer);
        this._reconnectTimer = setTimeout(() => {
            console.log('[Bridge] Reintentando conexión...');
            this._connectInternal(this._wsUrl).catch(() => {
                this._reconnectDelay = Math.min(this._reconnectDelay * 1.5, 5000);
                this._scheduleReconnect();
            });
        }, this._reconnectDelay);
    }

    _handleMessage(data) {
        if (data.type === 'welcome') {
            this.playerId = data.player_id;
            console.log('[Bridge] Welcome — player_id:', this.playerId);
            if (this.game._onServerReady) this.game._onServerReady(data);
            return;
        }

        if (data.type === 'state_update') {
            this._applyState(data);
        }
    }

    _applyState(state) {
        const g = this.game;

        if (state.players) {
            // No sincronizar player 1 desde el servidor (controlado localmente)
            for (const [pid, ps] of Object.entries(state.players)) {
                if (Number(pid) !== this.playerId) {
                    const dx = ps.x - g.player2.position.x;
                    const dz = ps.z - g.player2.position.z;
                    if (Math.abs(dx) > 3 || Math.abs(dz) > 3) {
                        g.player2.applyServerState(ps);
                    }
                    break;
                }
            }
        }

        if (state.chunk_deltas) {
            g.world.applyServerDeltas(state.chunk_deltas);
        }

        if (state.block_updates && state.block_updates.length) {
            g.world.applyBlockUpdates(state.block_updates);
            this._notifyActivity('🛠️ El servidor está modificando el mundo...');
        }

        if (state.enemies) {
            g.enemyManager.syncFromServer(state.enemies, g.scene);
        }

        if (state.objects) {
            if (!g.objectRenderer) g.objectRenderer = new ObjectRenderer();
            const mcpUrl = `http://${window.location.hostname || 'localhost'}:${window.location.port || 9000}/mcp`;
            g.objectRenderer.syncFromServer(state.objects, g.scene, mcpUrl);
            if (state.objects.length !== this._objectCount) {
                this._objectCount = state.objects.length;
                console.log('[Bridge] Objetos en escena:', this._objectCount,
                    state.objects.map(o => `#${o.id}:${o.kind}`).join(', '));
            }
        }

        if (typeof state.day_time === 'number') {
            g.dayNight.timeOfDay = state.day_time;
        }

        if (state.events) {
            for (const ev of state.events) {
                if (ev.type === 'block_update') {
                    g.world.setBlock(ev.x, ev.y, ev.z, ev.block_type);
                }
                if (ev.type === 'fill_area') {
                    for (let dx = 0; dx < ev.width; dx++) {
                        for (let dz = 0; dz < ev.depth; dz++) {
                            for (let dy = 0; dy < ev.height; dy++) {
                                g.world.setBlock(ev.x + dx, ev.baseY + dy, ev.z + dz, ev.block_type);
                            }
                        }
                    }
                }
                if (ev.type === 'entity_died' && ev.target === 'enemy') {
                    g.enemyManager.removeById(ev.id, g.scene);
                }
                // Eventos de objetos (Fase 5: FX visuales)
                if (ev.type === 'object_destroyed') {
                    if (g.objectRenderer) g.objectRenderer.handleDestroyedEvent(ev, g.scene);
                    console.log('[Objects] destruido id=' + ev.id + ' cause=' + ev.cause + ' fx=' + (ev.fx||'none'));
                }
                if (ev.type === 'object_collided') {
                    if (g.objectRenderer) g.objectRenderer.handleCollidedEvent(ev, g.scene);
                }
                if (ev.type === 'object_damaged') {
                    console.log('[Objects] dañado id=' + ev.id + ' amount=' + ev.amount);
                }
            }
        }
    }

    _notifyActivity(message) {
        const now = Date.now();
        if (!this._lastActivityNotice || now - this._lastActivityNotice > 1500) {
            this._lastActivityNotice = now;
            if (this.game.ui && this.game.ui.showNotification) {
                this.game.ui.showNotification(message);
            }
        }
    }

    sendMessage(msg) {
        if (!this.connected || !this.ws) return;
        this.seq++;
        msg.seq = this.seq;
        msg.player_id = this.playerId;
        this.ws.send(JSON.stringify(msg));
    }

    collectAndSendInput() {
        const g = this.game;
        const p = g.player1;
        if (!p) return;

        // Throttle: no mandar más de ~10 msgs/s salvo acciones
        const now = Date.now();
        if (now - this._lastInputSent < 100) {
            return;
        }
        this._lastInputSent = now;

        // Movement from keyboard
        const move = { x: 0, z: 0 };
        if (p.keys['KeyW']) move.z -= 1;
        if (p.keys['KeyS']) move.z += 1;
        if (p.keys['KeyA']) move.x -= 1;
        if (p.keys['KeyD']) move.x += 1;

        // Gamepad movement (overrides keyboard)
        const gpState = this._getGamepadState(0);
        if (gpState) {
            move.x = gpState.leftStick.x;
            move.z = gpState.leftStick.y;
        }

        const len = Math.hypot(move.x, move.z);
        if (len > 1) { move.x /= len; move.z /= len; }

        // Look from mouse delta + gamepad
        const look = {
            x: p.mouseDelta.x * 0.04,
            y: p.mouseDelta.y * 0.04,
        };
        if (gpState && gpState.rightStick) {
            look.x += gpState.rightStick.x * 3;
            look.y += gpState.rightStick.y * 3;
        }

        // Double-space fly toggle
        const spaceDown = !!p.keys['Space'];
        if (spaceDown && !this._lastSpace) {
            const now = Date.now();
            if (now - this._lastSpaceTime < 300) {
                p.isFlying = !p.isFlying;
            }
            this._lastSpaceTime = now;
        }
        this._lastSpace = spaceDown;

        // Break/Place (consumed once)
        // Update isMoving for player model animation
        p.isMoving = (move.x !== 0 || move.z !== 0);

        const breakBlock = !!p._pendingBreak;
        const placeBlock = !!p._pendingPlace;
        p._pendingBreak = false;
        p._pendingPlace = false;

        this.sendMessage({
            type: 'input',
            move,
            look,
            jump: spaceDown,
            fly: p.isFlying,
            break_block: breakBlock,
            place_block: placeBlock,
            selected_slot: p.selectedSlot,
        });
    }

    _getGamepadState(index) {
        const gps = navigator.getGamepads ? navigator.getGamepads() : [];
        const gp = gps[index];
        if (!gp) return null;
        return {
            leftStick: { x: gp.axes[0] || 0, y: gp.axes[1] || 0 },
            rightStick: { x: gp.axes[2] || 0, y: gp.axes[3] || 0 },
            buttons: {
                a: gp.buttons[0]?.pressed || false,
                b: gp.buttons[1]?.pressed || false,
                ls: gp.buttons[10]?.pressed || false,
                rt: gp.buttons[7]?.value || 0,
                lt: gp.buttons[6]?.value || 0,
            }
        };
    }

    disconnect() {
        if (this.ws) {
            this.ws.close();
            this.ws = null;
        }
        this.connected = false;
        this.playerId = null;
    }
}

window.ServerBridge = ServerBridge;
