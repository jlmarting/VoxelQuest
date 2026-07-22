/**
 * Gamepad handler para controllers Xbox 360 / Xbox One.
 * Detección automática, deadzone, botones mapeados.
 */

class GamepadHandler {
    constructor() {
        this.deadzone = 0.15;
        this.previousState = [null, null];

        window.addEventListener('gamepadconnected', (e) => {
            console.log('[Gamepad] Conectado: ' + e.gamepad.id);
        });
        window.addEventListener('gamepaddisconnected', (e) => {
            console.log('[Gamepad] Desconectado: ' + e.gamepad.id);
        });
    }

    _buttonPressed(btn) {
        if (!btn) return false;
        if (typeof btn.pressed === 'boolean') return btn.pressed;
        if (typeof btn === 'boolean') return btn;
        return false;
    }

    _buttonValue(btn) {
        if (!btn) return 0;
        if (typeof btn.value === 'number') return btn.value;
        if (typeof btn === 'number') return btn;
        return 0;
    }

    getState(gamepadIndex) {
        const gamepads = navigator.getGamepads();
        const gp = gamepads[gamepadIndex] || this._findFirstConnected(gamepads);
        if (!gp) return null;

        return {
            leftStick: {
                x: Math.abs(gp.axes[0]) > this.deadzone ? gp.axes[0] : 0,
                y: Math.abs(gp.axes[1]) > this.deadzone ? gp.axes[1] : 0,
            },
            rightStick: this._detectRightStick(gp),
            buttons: {
                a: this._buttonPressed(gp.buttons[0]),
                b: this._buttonPressed(gp.buttons[1]),
                x: this._buttonPressed(gp.buttons[2]),
                y: this._buttonPressed(gp.buttons[3]),
                lb: this._buttonPressed(gp.buttons[4]),
                rb: this._buttonPressed(gp.buttons[5]),
                lt: this._buttonValue(gp.buttons[6]),
                rt: this._buttonValue(gp.buttons[7]),
                back: this._buttonPressed(gp.buttons[8]),
                start: this._buttonPressed(gp.buttons[9]),
                ls: this._buttonPressed(gp.buttons[10]),
                rs: this._buttonPressed(gp.buttons[11]),
                dpUp: this._buttonPressed(gp.buttons[12]),
                dpDown: this._buttonPressed(gp.buttons[13]),
                dpLeft: this._buttonPressed(gp.buttons[14]),
                dpRight: this._buttonPressed(gp.buttons[15]),
            },
        };
    }

    _findFirstConnected(gamepads) {
        for (let i = 0; i < gamepads.length; i++) {
            if (gamepads[i]) return gamepads[i];
        }
        return null;
    }

    _detectRightStick(gp) {
        // Probar pares de ejes comunes para el stick derecho de Xbox
        const candidates = [
            [2, 3],
            [3, 4],
            [2, 5],
            [4, 5],
        ];
        for (const [ax, ay] of candidates) {
            const x = gp.axes[ax] || 0;
            const y = gp.axes[ay] || 0;
            if (Math.abs(x) > this.deadzone || Math.abs(y) > this.deadzone) {
                return {
                    x: Math.abs(x) > this.deadzone ? x : 0,
                    y: Math.abs(y) > this.deadzone ? y : 0,
                };
            }
        }
        // Fallback: usar ejes 2/3
        return {
            x: Math.abs(gp.axes[2]) > this.deadzone ? gp.axes[2] : 0,
            y: Math.abs(gp.axes[3]) > this.deadzone ? gp.axes[3] : 0,
        };
    }

    update() {
        for (let i = 0; i < 2; i++) {
            this.previousState[i] = this.getState(i);
        }
    }

    isConnected(gamepadIndex) {
        return navigator.getGamepads()[gamepadIndex] !== null;
    }
}

window.GamepadHandler = GamepadHandler;
