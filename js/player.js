class Player {
    constructor(id, world, camera, gamepadHandler, physics, sound) {
        this.id = id;
        this.world = world;
        this.camera = camera;
        this.gamepadHandler = gamepadHandler;
        this.physics = physics;
        this.sound = sound;
        this.buildingAssets = null; // Set by Game
        this.gamepadIndex = id - 1; // Gamepad 0 = Player 1, Gamepad 1 = Player 2

        // Position and physics
        this.position = new THREE.Vector3(0, 40, 0);
        this.velocity = new THREE.Vector3(0, 0, 0);
        this.rotation = { x: 0, y: 0 };

        // Player state
        this.health = 20;
        this.maxHealth = 20;
        this.onGround = false;
        this.isFlying = false;
        this.isMoving = false;

        // Double jump for flying toggle
        this.lastJumpTime = 0;
        this.doubleJumpWindow = 300; // ms

        // Movement settings
        this.moveSpeed = 5;
        this.jumpForce = 8;
        this.gravity = -20;
        this.mouseSensitivity = 0.002;
        this.gamepadSensitivity = 0.05;

        // Input state
        this.keys = {};
        this.mouseDelta = { x: 0, y: 0 };

        // Gamepad state
        this.gamepadJumpPressed = false;
        this.gamepadFlyPressed = false;
        this.gamepadBreakPressed = false;
        this.gamepadPlacePressed = false;

        // Inventory
        this.inventory = new Inventory(this);
        this.selectedSlot = 0;

        // Camera mode: 0=first person, 1=third close, 2=third far
        this.cameraMode = 0;
        this.cameraDistances = [0, 3, 8];
        this.cameraHeights = [1.75, 0.5, 1.5];
        this.cameraForwardOffset = 0.3; // avoid seeing own face

        // Setup controls
        this.setupControls();
    }

    setupControls() {
        document.addEventListener('keydown', (e) => {
            const isPlayer1Control = ['KeyW', 'KeyA', 'KeyS', 'KeyD', 'Space', 'ShiftLeft'].includes(e.code);
            const isPlayer2Control = ['ArrowUp', 'ArrowDown', 'ArrowLeft', 'ArrowRight', 'NumpadEnter', 'ShiftRight'].includes(e.code);

            if (this.id === 1 && isPlayer1Control) {
                this.keys[e.code] = true;
            } else if (this.id === 2 && isPlayer2Control) {
                this.keys[e.code] = true;
            }

            if (this.id === 1 && e.code >= 'Digit1' && e.code <= 'Digit9') {
                this.selectedSlot = parseInt(e.code.charAt(5)) - 1;
            }

            if (this.id === 2) {
                if (e.code >= 'Numpad1' && e.code <= 'Numpad9') {
                    this.selectedSlot = parseInt(e.code.charAt(6)) - 1;
                } else if (e.code >= 'Digit0' && e.code <= 'Digit9') {
                    this.selectedSlot = parseInt(e.code.charAt(5));
                    if (this.selectedSlot === 0) this.selectedSlot = 9;
                }
            }

            // V key toggles camera mode (both players)
            if (e.code === 'KeyV') {
                this.cameraMode = (this.cameraMode + 1) % 3;
                console.log('[Camera] Player', this.id, 'mode:', this.cameraMode);
            }
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
    }

    spawn(x, z) {
        this.position.x = x + 0.5;
        this.position.z = z + 0.5;
        this.position.y = this.world.getSpawnHeight(x, z) + 2;
    }

    update(deltaTime) {
        // Handle mouse look
        this.rotation.y -= this.mouseDelta.x * this.mouseSensitivity;
        this.rotation.x -= this.mouseDelta.y * this.mouseSensitivity;
        this.rotation.x = Math.max(-Math.PI / 2 + 0.1, Math.min(Math.PI / 2 - 0.1, this.rotation.x));
        this.mouseDelta.x = 0;
        this.mouseDelta.y = 0;

        // Gamepad look
        if (this.gamepadHandler && this.gamepadHandler.isConnected(this.gamepadIndex)) {
            const look = this.gamepadHandler.getLook(this.gamepadIndex);
            this.rotation.y -= look.x * this.gamepadSensitivity;
            this.rotation.x -= look.y * this.gamepadSensitivity;
            this.rotation.x = Math.max(-Math.PI / 2 + 0.1, Math.min(Math.PI / 2 - 0.1, this.rotation.x));
        }

        // Calculate movement direction
        const forward = new THREE.Vector3(
            -Math.sin(this.rotation.y),
            0,
            -Math.cos(this.rotation.y)
        );
        const right = new THREE.Vector3(
            Math.cos(this.rotation.y),
            0,
            -Math.sin(this.rotation.y)
        );

        // Movement input
        const moveDir = new THREE.Vector3(0, 0, 0);

        // Keyboard input
        if (this.id === 1) {
            if (this.keys['KeyW']) moveDir.add(forward);
            if (this.keys['KeyS']) moveDir.sub(forward);
            if (this.keys['KeyA']) moveDir.sub(right);
            if (this.keys['KeyD']) moveDir.add(right);
        } else {
            if (this.keys['ArrowUp']) moveDir.add(forward);
            if (this.keys['ArrowDown']) moveDir.sub(forward);
            if (this.keys['ArrowLeft']) moveDir.sub(right);
            if (this.keys['ArrowRight']) moveDir.add(right);
        }

        // Gamepad input
        if (this.gamepadHandler && this.gamepadHandler.isConnected(this.gamepadIndex)) {
            const movement = this.gamepadHandler.getMovement(this.gamepadIndex);
            moveDir.add(forward.clone().multiplyScalar(-movement.z));
            moveDir.add(right.clone().multiplyScalar(movement.x));
        }

        if (moveDir.length() > 0) {
            moveDir.normalize();
            this.isMoving = true;
        } else {
            this.isMoving = false;
        }

        // Apply movement
        this.velocity.x = moveDir.x * this.moveSpeed;
        this.velocity.z = moveDir.z * this.moveSpeed;

        // Flying and jumping - keyboard (double jump toggles flying)
        if (this.id === 1) {
            if (this.isFlying) {
                this.velocity.y = 0;
                if (this.keys['Space']) this.velocity.y = this.moveSpeed;
                if (this.keys['ShiftLeft']) this.velocity.y = -this.moveSpeed;
            } else {
                this.velocity.y += this.gravity * deltaTime;
                if (this.keys['Space'] && this.onGround) {
                    const now = Date.now();
                    if (now - this.lastJumpTime < this.doubleJumpWindow) {
                        // Double jump - toggle flying
                        this.isFlying = true;
                        this.velocity.y = 0;
                    } else {
                        this.velocity.y = this.jumpForce;
                    }
                    this.onGround = false;
                    this.lastJumpTime = now;
                    if (this.sound) this.sound.jump();
                }
            }
        } else {
            if (this.isFlying) {
                this.velocity.y = 0;
                if (this.keys['NumpadEnter']) this.velocity.y = this.moveSpeed;
                if (this.keys['ShiftRight']) this.velocity.y = -this.moveSpeed;
            } else {
                this.velocity.y += this.gravity * deltaTime;
                if (this.keys['NumpadEnter'] && this.onGround) {
                    const now = Date.now();
                    if (now - this.lastJumpTime < this.doubleJumpWindow) {
                        this.isFlying = true;
                        this.velocity.y = 0;
                    } else {
                        this.velocity.y = this.jumpForce;
                    }
                    this.onGround = false;
                    this.lastJumpTime = now;
                    if (this.sound) this.sound.jump();
                }
            }
        }

        // Gamepad flying and jumping
        if (this.gamepadHandler && this.gamepadHandler.isConnected(this.gamepadIndex)) {
            const movement = this.gamepadHandler.getMovement(this.gamepadIndex);

            // Toggle fly with left stick press
            if (movement.fly && !this.gamepadFlyPressed) {
                this.isFlying = !this.isFlying;
            }
            this.gamepadFlyPressed = movement.fly;

            if (this.isFlying) {
                this.velocity.y = 0;
                if (movement.jump) this.velocity.y = this.moveSpeed;
                if (this.gamepadHandler.getState(this.gamepadIndex)?.buttons.rs) {
                    this.velocity.y = -this.moveSpeed;
                }
            } else {
                if (movement.jump && !this.gamepadJumpPressed && this.onGround) {
                    this.velocity.y = this.jumpForce;
                    this.onGround = false;
                }
            }
            this.gamepadJumpPressed = movement.jump;
        }

        // Apply velocity with collision
        this.moveWithCollision(deltaTime);

        // Update camera based on mode
        const dist = this.cameraDistances[this.cameraMode];
        const height = this.cameraHeights[this.cameraMode];

        if (dist === 0) {
            // First person - offset forward to avoid seeing own face
            const forwardX = -Math.sin(this.rotation.y) * this.cameraForwardOffset;
            const forwardZ = -Math.cos(this.rotation.y) * this.cameraForwardOffset;
            this.camera.position.set(
                this.position.x + forwardX,
                this.position.y + height,
                this.position.z + forwardZ
            );
        } else {
            // Third person - camera behind player
            const euler = new THREE.Euler(0, this.rotation.y, 0, 'YXZ');
            const offset = new THREE.Vector3(0, height, dist);
            offset.applyEuler(euler);
            this.camera.position.set(
                this.position.x + offset.x,
                this.position.y + offset.y,
                this.position.z + offset.z
            );
        }

        // Camera looks at player (third person) or forward (first person)
        const camEuler = new THREE.Euler(this.rotation.x, this.rotation.y, 0, 'YXZ');
        if (dist > 0) {
            // Third person: look at player
            this.camera.lookAt(this.position.x, this.position.y + 1.0, this.position.z);
        } else {
            // First person: look forward
            this.camera.quaternion.setFromEuler(camEuler);
        }

        // Gamepad block actions
        if (this.gamepadHandler && this.gamepadHandler.isConnected(this.gamepadIndex)) {
            const actions = this.gamepadHandler.getActions(this.gamepadIndex);
            if (actions.breakBlock && !this.gamepadBreakPressed) {
                this.breakBlock();
            }
            this.gamepadBreakPressed = actions.breakBlock;

            if (actions.placeBlock && !this.gamepadPlacePressed) {
                this.placeBlock();
            }
            this.gamepadPlacePressed = actions.placeBlock;

            // Slot selection with D-pad
            const slots = this.gamepadHandler.getSlotSelection(this.gamepadIndex);
            if (slots.dpRight) this.selectedSlot = (this.selectedSlot + 1) % 9;
            if (slots.dpLeft) this.selectedSlot = (this.selectedSlot + 8) % 9;
            if (slots.dpUp) this.selectedSlot = (this.selectedSlot + 3) % 9;
            if (slots.dpDown) this.selectedSlot = (this.selectedSlot + 6) % 9;
        }
    }

    moveWithCollision(deltaTime) {
        const newPos = this.position.clone();

        newPos.x += this.velocity.x * deltaTime;
        if (this.checkCollision(newPos)) {
            newPos.x = this.position.x;
            this.velocity.x = 0;
        }

        newPos.z += this.velocity.z * deltaTime;
        if (this.checkCollision(newPos)) {
            newPos.z = this.position.z;
            this.velocity.z = 0;
        }

        newPos.y += this.velocity.y * deltaTime;
        if (this.checkCollision(newPos)) {
            if (this.velocity.y < 0) {
                this.onGround = true;
                if (this.isFlying) {
                    this.isFlying = false; // Land when hitting ground
                }
            }
            newPos.y = this.position.y;
            this.velocity.y = 0;
        } else {
            this.onGround = false;
        }

        this.position.copy(newPos);
        this.position.y = Math.max(1, Math.min(WORLD_HEIGHT - 2, this.position.y));
    }

    checkCollision(pos) {
        const playerWidth = 0.3;
        const playerHeight = 1.8;

        for (let dx = -1; dx <= 1; dx++) {
            for (let dz = -1; dz <= 1; dz++) {
                for (let dy = 0; dy <= 1; dy++) {
                    const bx = Math.floor(pos.x + dx * playerWidth);
                    const by = Math.floor(pos.y + dy * playerHeight);
                    const bz = Math.floor(pos.z + dz * playerWidth);

                    const block = this.world.getBlock(bx, by, bz);
                    if (block !== BLOCK_TYPES.AIR && block !== BLOCK_TYPES.WATER) {
                        return true;
                    }
                }
            }
        }
        return false;
    }

    getForwardDirection() {
        const dir = new THREE.Vector3(0, 0, -1);
        const euler = new THREE.Euler(this.rotation.x, this.rotation.y, 0, 'YXZ');
        dir.applyEuler(euler);
        return dir;
    }

    getEyePosition() {
        return new THREE.Vector3(this.position.x, this.position.y + 1.6, this.position.z);
    }

    placeBlock() {
        const eyePos = this.getEyePosition();
        const dir = this.getForwardDirection();
        const hit = this.world.raycast(eyePos, dir);

        console.log('[Place] Hit:', !!hit, 'Selected slot:', this.inventory.getSelectedSlot());

        if (hit) {
            const selectedItem = this.inventory.slots[this.inventory.getSelectedSlot()];
            console.log('[Place] Selected item:', selectedItem);

            if (selectedItem && selectedItem.count > 0) {
                const px = hit.position.x + hit.normal.x;
                const py = hit.position.y + hit.normal.y;
                const pz = hit.position.z + hit.normal.z;

                const playerBlockX = Math.floor(this.position.x);
                const playerBlockY = Math.floor(this.position.y);
                const playerBlockZ = Math.floor(this.position.z);

                if (px === playerBlockX && py === playerBlockY && pz === playerBlockZ) return;
                if (px === playerBlockX && py === playerBlockY + 1 && pz === playerBlockZ) return;

                // Determine if block or asset (blocks are numbers, assets are strings)
                const isBlock = typeof selectedItem.type === 'number';
                console.log('[Place] Type:', selectedItem.type, 'isBlock:', isBlock);

                if (isBlock) {
                    this.world.setBlock(px, py, pz, selectedItem.type);
                    console.log('[Place] Block placed at', px, py, pz);
                } else {
                    this.placeAsset(selectedItem.type, px, py, pz);
                }

                this.inventory.removeItem(selectedItem.type, 1);
                if (this.sound) this.sound.blockPlace();
            }
        }
    }

    placeAsset(assetType, x, y, z) {
        // Get rotation based on player facing
        const rotation = Math.round(this.rotation.y / (Math.PI / 2)) * (Math.PI / 2);

        if (this.buildingAssets) {
            switch (assetType) {
                case 'window':
                    this.buildingAssets.createWindow(x, y, z, rotation);
                    break;
                case 'door':
                    this.buildingAssets.createDoor(x, y, z, rotation);
                    break;
                case 'torch':
                    this.buildingAssets.createTorch(x, y, z);
                    break;
                case 'crafting_table':
                    this.buildingAssets.createCraftingTable(x, y, z);
                    break;
                case 'chest':
                    this.buildingAssets.createChest(x, y, z);
                    break;
                case 'bed':
                    this.buildingAssets.createBed(x, y, z);
                    break;
                case 'chair':
                    this.buildingAssets.createChair(x, y, z);
                    break;
                case 'table':
                    this.buildingAssets.createTable(x, y, z);
                    break;
                case 'bookshelf':
                    this.buildingAssets.createBookshelf(x, y, z);
                    break;
                case 'fence':
                    this.buildingAssets.createFence(x, y, z, 1, rotation);
                    break;
                case 'lamp':
                    this.buildingAssets.createLamp(x, y, z);
                    break;
                case 'flower_pot':
                    this.buildingAssets.createFlowerPot(x, y, z);
                    break;
            }
        }
    }

    breakBlock() {
        const eyePos = this.getEyePosition();
        const dir = this.getForwardDirection();
        const hit = this.world.raycast(eyePos, dir);

        if (hit && hit.block !== BLOCK_TYPES.BEDROCK) {
            const brokenBlock = hit.block;
            this.world.setBlock(hit.position.x, hit.position.y, hit.position.z, BLOCK_TYPES.AIR);
            this.inventory.addItem(brokenBlock, 1);
            if (this.sound) this.sound.blockBreak();

            // Trigger physics collapse check
            if (this.physics) {
                this.physics.onBlockBroken(hit.position.x, hit.position.y, hit.position.z);
            }
        }
    }
}

window.Player = Player;
