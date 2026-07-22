/**
 * Captura teclado/ratón y envía input al servidor.
 */

class InputHandler {
    constructor(client) {
        this.client = client;
        this.keys = {};
        this.mouseDelta = { x: 0, y: 0 };
        this.mouseButtons = { left: false, right: false };
        this.lastLeftClick = false;
        this.lastRightClick = false;

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

        document.addEventListener('mousedown', (e) => {
            if (e.button === 0) this.mouseButtons.left = true;
            if (e.button === 2) this.mouseButtons.right = true;
        });
        document.addEventListener('mouseup', (e) => {
            if (e.button === 0) this.mouseButtons.left = false;
            if (e.button === 2) this.mouseButtons.right = false;
        });

        document.addEventListener('click', () => {
            if (!document.pointerLockElement) {
                document.body.requestPointerLock();
            }
        });
    }

    buildInput() {
        const move = { x: 0, z: 0 };
        if (this.keys['KeyW'] || this.keys['ArrowUp']) move.z -= 1;
        if (this.keys['KeyS'] || this.keys['ArrowDown']) move.z += 1;
        if (this.keys['KeyA'] || this.keys['ArrowLeft']) move.x -= 1;
        if (this.keys['KeyD'] || this.keys['ArrowRight']) move.x += 1;

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

        const leftClick = this.mouseButtons.left && !this.lastLeftClick;
        const rightClick = this.mouseButtons.right && !this.lastRightClick;
        this.lastLeftClick = this.mouseButtons.left;
        this.lastRightClick = this.mouseButtons.right;

        return {
            type: 'input',
            move,
            look,
            jump: !!this.keys['Space'],
            fly: !!this.keys['ShiftLeft'],
            break_block: leftClick,
            place_block: rightClick,
        };
    }
}

window.InputHandler = InputHandler;
