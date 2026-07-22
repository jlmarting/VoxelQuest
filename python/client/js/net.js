/**
 * Cliente WebSocket para VoxelQuest Server Python.
 * Conecta a /ws, recibe estado y envía input.
 */

class GameClient {
    constructor() {
        this.ws = null;
        this.connected = false;
        this.playerId = null;
        this.currentState = null;
        this.previousState = null;
        this.onWelcome = null;
        this.onState = null;
        this.seq = 0;
    }

    connect(url) {
        return new Promise((resolve, reject) => {
            try {
                this.ws = new WebSocket(url);

                this.ws.onopen = () => {
                    this.connected = true;
                    console.log('[WS] Conectado');
                };

                this.ws.onmessage = (event) => {
                    const data = JSON.parse(event.data);
                    this._handleMessage(data);
                };

                this.ws.onclose = () => {
                    this.connected = false;
                    console.log('[WS] Desconectado');
                };

                this.ws.onerror = (err) => {
                    console.error('[WS] Error:', err);
                    reject(err);
                };

                const checkWelcome = setInterval(() => {
                    if (this.playerId !== null || !this.connected) {
                        clearInterval(checkWelcome);
                        if (this.connected) resolve();
                    }
                }, 50);
            } catch (err) {
                reject(err);
            }
        });
    }

    _handleMessage(data) {
        if (data.type === 'welcome') {
            this.playerId = data.player_id;
            console.log('[WS] Bienvenida. player_id:', this.playerId);
            if (this.onWelcome) this.onWelcome(data);
            return;
        }

        if (data.type === 'state_update') {
            this.previousState = this.currentState;
            this.currentState = data;
            if (this.onState) this.onState(data);
        }
    }

    sendInput(input) {
        if (!this.connected || !this.ws) return;
        this.seq++;
        input.seq = this.seq;
        input.player_id = this.playerId;
        this.ws.send(JSON.stringify(input));
    }
}

window.GameClient = GameClient;
