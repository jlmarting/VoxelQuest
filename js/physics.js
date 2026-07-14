// Physics system - simplified block collapse
class PhysicsSystem {
    constructor(world, scene) {
        this.world = world;
        this.scene = scene;
        this.fallingBlocks = [];
        this.gravity = 14;
        this.maxFallsPerFrame = 5;
    }

    onBlockBroken(x, y, z) {
        this.checkUnsupported(x, y + 1, z);
    }

    checkUnsupported(x, y, z) {
        if (y < 1 || y >= WORLD_HEIGHT) return;

        const block = this.world.getBlock(x, y, z);
        if (block === BLOCK_TYPES.AIR || block === BLOCK_TYPES.WATER) return;

        const below = this.world.getBlock(x, y - 1, z);
        if (below !== BLOCK_TYPES.AIR && below !== BLOCK_TYPES.WATER) return;

        // Block is floating - remove it
        this.world.setBlock(x, y, z, BLOCK_TYPES.AIR);
        this.startFalling(x, y, z, block);

        // Check above
        this.checkUnsupported(x, y + 1, z);
    }

    startFalling(x, y, z, blockType) {
        const colorMap = {
            [BLOCK_TYPES.GRASS]: 0x5d8c3e, [BLOCK_TYPES.DIRT]: 0x8b6942,
            [BLOCK_TYPES.STONE]: 0x808080, [BLOCK_TYPES.WOOD]: 0x6b4423,
            [BLOCK_TYPES.LEAVES]: 0x2d5a1e, [BLOCK_TYPES.SAND]: 0xd4c4a0,
            [BLOCK_TYPES.COBBLESTONE]: 0x6b6b6b, [BLOCK_TYPES.PLANKS]: 0xbc9458
        };

        const geo = new THREE.BoxGeometry(0.9, 0.9, 0.9);
        const mat = new THREE.MeshStandardMaterial({ color: colorMap[blockType] || 0x808080, roughness: 0.85 });
        const mesh = new THREE.Mesh(geo, mat);
        mesh.position.set(x + 0.5, y + 0.5, z + 0.5);
        mesh.castShadow = true;
        this.scene.add(mesh);

        this.fallingBlocks.push({
            mesh, x: x + 0.5, y: y + 0.5, z: z + 0.5,
            velY: 0, blockType, grounded: false
        });
    }

    update(deltaTime) {
        const dt = Math.min(deltaTime, 0.05);

        for (let i = this.fallingBlocks.length - 1; i >= 0; i--) {
            const fb = this.fallingBlocks[i];

            if (fb.grounded) {
                // Place block in world
                const bx = Math.floor(fb.x);
                const by = Math.floor(fb.y - 0.45);
                const bz = Math.floor(fb.z);
                if (by >= 0 && by < WORLD_HEIGHT) {
                    const existing = this.world.getBlock(bx, by, bz);
                    if (existing === BLOCK_TYPES.AIR) {
                        this.world.setBlock(bx, by, bz, fb.blockType);
                    }
                }
                this.scene.remove(fb.mesh);
                fb.mesh.geometry.dispose();
                fb.mesh.material.dispose();
                this.fallingBlocks.splice(i, 1);
                continue;
            }

            fb.velY -= this.gravity * dt;
            fb.y += fb.velY * dt;

            fb.mesh.position.y = fb.y;
            fb.mesh.rotation.x += dt * 2;

            const groundY = this.getGroundHeight(Math.floor(fb.x - 0.5), Math.floor(fb.z - 0.5));
            if (fb.y - 0.45 <= groundY + 0.5) {
                fb.y = groundY + 0.5 + 0.45;
                fb.grounded = true;
                fb.velY = 0;
            }

            if (fb.y < -10) {
                this.scene.remove(fb.mesh);
                fb.mesh.geometry.dispose();
                fb.mesh.material.dispose();
                this.fallingBlocks.splice(i, 1);
            }
        }
    }

    getGroundHeight(x, z) {
        for (let y = WORLD_HEIGHT - 1; y >= 0; y--) {
            const block = this.world.getBlock(x, y, z);
            if (block !== BLOCK_TYPES.AIR && block !== BLOCK_TYPES.WATER) {
                return y;
            }
        }
        return 0;
    }
}

window.PhysicsSystem = PhysicsSystem;
