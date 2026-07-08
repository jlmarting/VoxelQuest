// Physics system - checks vertical AND horizontal neighbors
class PhysicsSystem {
    constructor(world, scene) {
        this.world = world;
        this.scene = scene;
        this.fallingBlocks = [];
        this.gravity = 14;
        this.toCheck = []; // blocks queued for checking
        this.checked = new Set();
    }

    onBlockBroken(x, y, z) {
        this.checked.clear();
        this.toCheck = [];

        // Start checking from the block above
        this.queueCheck(x, y + 1, z);
        // Also check same level neighbors (connected to broken block)
        this.queueCheck(x + 1, y, z);
        this.queueCheck(x - 1, y, z);
        this.queueCheck(x, y, z + 1);
        this.queueCheck(x, y, z - 1);
    }

    queueCheck(x, y, z) {
        const key = `${x},${y},${z}`;
        if (this.checked.has(key)) return;
        this.toCheck.push({ x, y, z });
    }

    processChecks() {
        // Process up to 10 checks per frame to avoid lag
        let count = 0;
        while (this.toCheck.length > 0 && count < 10) {
            const { x, y, z } = this.toCheck.shift();
            const key = `${x},${y},${z}`;
            if (this.checked.has(key)) continue;
            this.checked.add(key);

            if (y < 1 || y >= WORLD_HEIGHT) continue;

            const block = this.world.getBlock(x, y, z);
            if (block === BLOCK_TYPES.AIR || block === BLOCK_TYPES.WATER) continue;

            // Check if this block has support below
            const below = this.world.getBlock(x, y - 1, z);
            if (below !== BLOCK_TYPES.AIR && below !== BLOCK_TYPES.WATER) {
                continue; // supported, skip
            }

            // No support - remove and make fall
            this.world.setBlock(x, y, z, BLOCK_TYPES.AIR);
            this.startFalling(x, y, z, block);
            count++;

            // Now check neighbors of THIS block too (chain reaction)
            this.queueCheck(x, y + 1, z); // above
            this.queueCheck(x + 1, y, z); // sides
            this.queueCheck(x - 1, y, z);
            this.queueCheck(x, y, z + 1);
            this.queueCheck(x, y, z - 1);
        }
    }

    startFalling(x, y, z, blockType) {
        const colorMap = {
            [BLOCK_TYPES.GRASS]: 0x5d8c3e, [BLOCK_TYPES.DIRT]: 0x8b6942,
            [BLOCK_TYPES.STONE]: 0x808080, [BLOCK_TYPES.WOOD]: 0x6b4423,
            [BLOCK_TYPES.LEAVES]: 0x2d5a1e, [BLOCK_TYPES.SAND]: 0xd4c4a0,
            [BLOCK_TYPES.COBBLESTONE]: 0x6b6b6b, [BLOCK_TYPES.PLANKS]: 0xbc9458
        };
        const geo = new THREE.BoxGeometry(0.9, 0.9, 0.9);
        const mat = new THREE.MeshStandardMaterial({ color: colorMap[blockType] || 0x808080 });
        const mesh = new THREE.Mesh(geo, mat);
        mesh.position.set(x + 0.5, y + 0.5, z + 0.5);
        mesh.castShadow = true;
        this.scene.add(mesh);
        this.fallingBlocks.push({ mesh, x, y, z, velY: 0 });
    }

    update(deltaTime) {
        // Process queued checks (spread over frames)
        this.processChecks();

        // Animate falling blocks
        for (let i = this.fallingBlocks.length - 1; i >= 0; i--) {
            const fb = this.fallingBlocks[i];
            fb.velY += this.gravity * deltaTime;
            fb.y -= fb.velY * deltaTime;
            fb.mesh.position.y = fb.y + 0.5;
            fb.mesh.rotation.x += deltaTime * 3;

            const below = this.world.getBlock(fb.x, Math.floor(fb.y) - 1, fb.z);
            if (below !== BLOCK_TYPES.AIR && below !== BLOCK_TYPES.WATER || fb.y < -10) {
                this.particles(fb.mesh.position.x, fb.mesh.position.y, fb.mesh.position.z);
                this.scene.remove(fb.mesh);
                fb.mesh.geometry.dispose();
                fb.mesh.material.dispose();
                this.fallingBlocks.splice(i, 1);
            }
        }
    }

    particles(x, y, z) {
        for (let i = 0; i < 4; i++) {
            const geo = new THREE.BoxGeometry(0.08, 0.08, 0.08);
            const mat = new THREE.MeshStandardMaterial({ color: 0x8b6942, transparent: true });
            const p = new THREE.Mesh(geo, mat);
            p.position.set(x, y, z);
            const vel = new THREE.Vector3((Math.random()-0.5)*3, Math.random()*4+1, (Math.random()-0.5)*3);
            this.scene.add(p);
            let life = 1;
            const anim = () => {
                vel.y -= 8 * 0.016;
                p.position.add(vel.clone().multiplyScalar(0.016));
                life -= 0.04;
                p.material.opacity = Math.max(0, life);
                if (life > 0) requestAnimationFrame(anim);
                else { this.scene.remove(p); p.geometry.dispose(); p.material.dispose(); }
            };
            requestAnimationFrame(anim);
        }
    }
}

window.PhysicsSystem = PhysicsSystem;
