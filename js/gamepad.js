// Gamepad handler for Xbox 360 controllers
class GamepadHandler {
    constructor() {
        this.gamepads = [null, null];
        this.previousState = [{}, {}];
        this.deadzone = 0.15;
        this.callbacks = {
            leftStick: [null, null],
            rightStick: [null, null],
            button: [null, null]
        };

        this.setupListeners();
    }

    setupListeners() {
        window.addEventListener('gamepadconnected', (e) => {
            console.log(`Gamepad conectado: ${e.gamepad.id}`);
            this.gamepads[e.gamepad.index] = e.gamepad;
        });

        window.addEventListener('gamepaddisconnected', (e) => {
            console.log(`Gamepad desconectado: ${e.gamepad.id}`);
            this.gamepads[e.gamepad.index] = null;
        });
    }

    // Get current state of a gamepad
    getState(gamepadIndex) {
        const gamepad = navigator.getGamepads()[gamepadIndex];
        if (!gamepad) return null;

        const state = {
            // Sticks
            leftStick: {
                x: Math.abs(gamepad.axes[0]) > this.deadzone ? gamepad.axes[0] : 0,
                y: Math.abs(gamepad.axes[1]) > this.deadzone ? gamepad.axes[1] : 0
            },
            rightStick: {
                x: Math.abs(gamepad.axes[2]) > this.deadzone ? gamepad.axes[2] : 0,
                y: Math.abs(gamepad.axes[3]) > this.deadzone ? gamepad.axes[3] : 0
            },
            // Buttons (Xbox 360 layout)
            buttons: {
                a: gamepad.buttons[0]?.pressed || false,      // A (bottom)
                b: gamepad.buttons[1]?.pressed || false,      // B (right)
                x: gamepad.buttons[2]?.pressed || false,      // X (left)
                y: gamepad.buttons[3]?.pressed || false,      // Y (top)
                lb: gamepad.buttons[4]?.pressed || false,     // Left bumper
                rb: gamepad.buttons[5]?.pressed || false,     // Right bumper
                lt: gamepad.buttons[6]?.value || 0,           // Left trigger (0-1)
                rt: gamepad.buttons[7]?.value || 0,           // Right trigger (0-1)
                back: gamepad.buttons[8]?.pressed || false,   // Back/Select
                start: gamepad.buttons[9]?.pressed || false,  // Start
                ls: gamepad.buttons[10]?.pressed || false,    // Left stick press
                rs: gamepad.buttons[11]?.pressed || false,    // Right stick press
                dpUp: gamepad.buttons[12]?.pressed || false,  // D-pad up
                dpDown: gamepad.buttons[13]?.pressed || false,// D-pad down
                dpLeft: gamepad.buttons[14]?.pressed || false,// D-pad left
                dpRight: gamepad.buttons[15]?.pressed || false// D-pad right
            }
        };

        return state;
    }

    // Check if button was just pressed (not held)
    justPressed(gamepadIndex, button) {
        const current = this.getState(gamepadIndex);
        const prev = this.previousState[gamepadIndex];

        if (!current || !prev) return false;

        let currentValue, prevValue;

        // Handle both button objects and axis values
        if (typeof current.buttons[button] === 'boolean') {
            currentValue = current.buttons[button];
            prevValue = prev.buttons?.[button] || false;
        } else {
            currentValue = current.buttons[button] > 0.5;
            prevValue = (prev.buttons?.[button] || 0) > 0.5;
        }

        return currentValue && !prevValue;
    }

    // Update previous state (call each frame)
    update() {
        for (let i = 0; i < 2; i++) {
            const state = this.getState(i);
            if (state) {
                this.previousState[i] = JSON.parse(JSON.stringify(state));
            }
        }
    }

    // Check if any gamepad is connected
    isConnected(gamepadIndex = -1) {
        if (gamepadIndex >= 0) {
            return this.gamepads[gamepadIndex] !== null;
        }
        return this.gamepads[0] !== null || this.gamepads[1] !== null;
    }

    // Get movement input for a player
    getMovement(gamepadIndex) {
        const state = this.getState(gamepadIndex);
        if (!state) return { x: 0, z: 0, jump: false, fly: false };

        return {
            x: state.leftStick.x,
            z: state.leftStick.y,
            jump: state.buttons.a,
            fly: state.buttons.ls // Left stick press to toggle fly
        };
    }

    // Get camera/look input for a player
    getLook(gamepadIndex) {
        const state = this.getState(gamepadIndex);
        if (!state) return { x: 0, y: 0 };

        return {
            x: state.rightStick.x * 3, // Sensitivity multiplier
            y: state.rightStick.y * 3
        };
    }

    // Get action input (break/place blocks)
    getActions(gamepadIndex) {
        const state = this.getState(gamepadIndex);
        if (!state) return { breakBlock: false, placeBlock: false, inventory: false, craft: false };

        return {
            breakBlock: state.buttons.rt > 0.5,   // Right trigger = break
            placeBlock: state.buttons.lt > 0.5,   // Left trigger = place
            inventory: this.justPressed(gamepadIndex, 'start'),
            craft: this.justPressed(gamepadIndex, 'back')
        };
    }

    // Get slot selection from D-pad or bumpers
    getSlotSelection(gamepadIndex) {
        return {
            dpLeft: this.justPressed(gamepadIndex, 'dpLeft'),
            dpRight: this.justPressed(gamepadIndex, 'dpRight'),
            dpUp: this.justPressed(gamepadIndex, 'dpUp'),
            dpDown: this.justPressed(gamepadIndex, 'dpDown'),
            lb: this.justPressed(gamepadIndex, 'lb'),
            rb: this.justPressed(gamepadIndex, 'rb')
        };
    }

    // Get inventory navigation input
    getInventoryNav(gamepadIndex) {
        return {
            up: this.justPressed(gamepadIndex, 'dpUp'),
            down: this.justPressed(gamepadIndex, 'dpDown'),
            left: this.justPressed(gamepadIndex, 'dpLeft'),
            right: this.justPressed(gamepadIndex, 'dpRight'),
            select: this.justPressed(gamepadIndex, 'a'),
            close: this.justPressed(gamepadIndex, 'b') || this.justPressed(gamepadIndex, 'start')
        };
    }
}

window.GamepadHandler = GamepadHandler;
