class ServerBridge {
    constructor(game) {
        this.game = game;
        this.ws = null;
        this.connected = false;
        this.playerId = null;
        this.seq = 0;
        this._pendingBreak = false;
        this._pendingPlace = false;
    }

    connect(url) {
        return new Promise((resolve, reject) => {
            this.ws = new WebSocket(url);

            this.ws.onopen = () => {
                this.connected = true;
                console.log('[Bridge] Conectado al servidor Python');
            };

            this.ws.onmessage = (event) => {
                const data = JSON.parse(event.data);
                this._handleMessage(data);
            };

            this.ws.onclose = () => {
                this.connected = false;
                console.log('[Bridge] Desconectado del servidor');
            };

            this.ws.onerror = (err) => {
                console.error('[Bridge] Error WS:', err);
                reject(err);
            };

            const check = setInterval(() => {
                if (this.playerId !== null || !this.connected) {
                    clearInterval(check);
                    if (this.connected) resolve();
                }
            }, 50);
        });
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
            const myState = state.players[String(this.playerId)];
            if (myState) {
                const dx = myState.x - g.player1.position.x;
                const dz = myState.z - g.player1.position.z;
                if (Math.abs(dx) > 5 || Math.abs(dz) > 5) {
                    g.player1.applyServerState(myState);
                }
            }
            for (const [pid, ps] of Object.entries(state.players)) {
                if (Number(pid) !== this.playerId) {
                    g.player2.applyServerState(ps);
                    break;
                }
            }
        }

        if (state.chunk_deltas) {
            g.world.applyServerDeltas(state.chunk_deltas);
        }

        if (state.enemies) {
            g.enemyManager.syncFromServer(state.enemies, g.scene);
        }

        if (typeof state.day_time === 'number') {
            g.dayNight.timeOfDay = state.day_time;
        }

        if (state.events) {
            for (const ev of state.events) {
                if (ev.type === 'entity_died' && ev.target === 'enemy') {
                    g.enemyManager.removeById(ev.id, g.scene);
                }
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
