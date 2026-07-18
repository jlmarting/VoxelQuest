/**
 * Captura teclado/ratón y envía input al servidor.
 */

class InputHandler {
    constructor(client) {
        this.client = client;
        this.keys = {};
        this.mouseDelta = { x: 0, y: 0 };
        this.lockRequested = false;

        document.addEventListener('keydown', (e) => {
            this.keys[e.code] = true;
        });
        document.addEventListener('keyup', (e) => {
            this.keys[e.code] = false;
        });

        document.addEventListener('mousemove', (e) => {
            if (document.pointerLockElement) {
                this.mouseDelta.x += e.movementX;
                this.mouseDelta.y += e.movementY;
            }
        });

        document.addEventListener('click', () => {
            if (!document.pointerLockElement) {
                document.body.requestPointerLock();
            }
        });
    }

    buildInput() {
        const move = { x: 0, z: 0 };
        if (this.keys['KeyW']) move.z -= 1;
        if (this.keys['KeyS']) move.z += 1;
        if (this.keys['KeyA']) move.x -= 1;
        if (this.keys['KeyD']) move.x += 1;

        // Normalizar
        const len = Math.hypot(move.x, move.z);
        if (len > 0) {
            move.x /= len;
            move.z /= len;
        }

        const look = {
            x: this.mouseDelta.x * 0.002,
            y: this.mouseDelta.y * 0.002,
        };
        this.mouseDelta.x = 0;
        this.mouseDelta.y = 0;

        return {
            type: 'input',
            move,
            look,
            jump: !!this.keys['Space'],
            fly: !!this.keys['ShiftLeft'],
            place_block: false,
            break_block: false,
        };
    }
}

window.InputHandler = InputHandler;
