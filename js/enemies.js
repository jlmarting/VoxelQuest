const ENEMY_TYPES = {
    ZOMBIE: {
        name: 'Zombie',
        health: 20,
        damage: 2,
        speed: 2,
        color: 0x2d5a27,
        height: 1.8,
        followDistance: 16,
        attackDistance: 2,
        attackCooldown: 1000
    },
    SKELETON: {
        name: 'Skeleton',
        health: 20,
        damage: 2,
        speed: 2.5,
        color: 0xdcdcdc,
        height: 1.8,
        followDistance: 16,
        attackDistance: 12,
        attackCooldown: 2000,
        ranged: true
    },
    CREEPER: {
        name: 'Creeper',
        health: 20,
        damage: 0,
        speed: 1.5,
        color: 0x00ff00,
        height: 1.5,
        followDistance: 16,
        attackDistance: 3,
        explodeRadius: 4
    }
};

class Enemy {
    constructor(type, position, world) {
        this.type = type;
        this.config = ENEMY_TYPES[type];
        this.world = world;
        
        this.position = position.clone();
        this.velocity = new THREE.Vector3(0, 0, 0);
        this.health = this.config.health;
        this.onGround = false;
        this.lastAttackTime = 0;
        
        // AI state
        this.target = null;
        this.state = 'idle'; // idle, chase, attack
        
        // Create mesh
        this.createMesh();
    }

    createMesh() {
        const geometry = new THREE.BoxGeometry(0.6, this.config.height, 0.6);
        const material = new THREE.MeshStandardMaterial({ color: this.config.color, roughness: 0.8 });
        this.mesh = new THREE.Mesh(geometry, material);
        this.mesh.castShadow = true;
        this.mesh.receiveShadow = true;
        this.mesh.position.copy(this.position);
        this.mesh.position.y += this.config.height / 2;

        // Eerie glow light
        this.light = new THREE.PointLight(0x44ff44, 0.5, 8, 2);
        this.light.position.set(0, 0, 0);
        this.mesh.add(this.light);
    }

    update(deltaTime, players) {
        // Find nearest player
        let nearestPlayer = null;
        let nearestDistance = Infinity;
        
        for (const player of players) {
            const dist = this.position.distanceTo(player.position);
            if (dist < nearestDistance) {
                nearestDistance = dist;
                nearestPlayer = player;
            }
        }
        
        // AI behavior
        if (nearestPlayer && nearestDistance < this.config.followDistance) {
            this.target = nearestPlayer;
            
            if (nearestDistance <= this.config.attackDistance) {
                this.state = 'attack';
                this.attack(nearestPlayer);
            } else {
                this.state = 'chase';
                this.moveToward(nearestPlayer.position, deltaTime);
            }
        } else {
            this.state = 'idle';
            this.velocity.x = 0;
            this.velocity.z = 0;
        }
        
        // Apply gravity
        this.velocity.y += -20 * deltaTime;
        
        // Move with collision
        this.moveWithCollision(deltaTime);
        
        // Update mesh position
        this.mesh.position.copy(this.position);
        this.mesh.position.y += this.config.height / 2;
    }

    moveToward(target, deltaTime) {
        const direction = new THREE.Vector3(
            target.x - this.position.x,
            0,
            target.z - this.position.z
        ).normalize();
        
        this.velocity.x = direction.x * this.config.speed;
        this.velocity.z = direction.z * this.config.speed;
        
        // Jump over obstacles
        if (this.onGround) {
            const frontBlock = this.world.getBlock(
                Math.floor(this.position.x + direction.x),
                Math.floor(this.position.y),
                Math.floor(this.position.z + direction.z)
            );
            if (frontBlock !== BLOCK_TYPES.AIR) {
                this.velocity.y = 8;
            }
        }
    }

    attack(player) {
        const now = Date.now();
        if (now - this.lastAttackTime < this.config.attackCooldown) return;
        
        this.lastAttackTime = now;
        
        if (this.config.ranged) {
            // Ranged attack - just damage for simplicity
            player.health -= this.config.damage;
        } else {
            // Melee attack
            player.health -= this.config.damage;
        }
        
        if (player.health <= 0) {
            player.health = player.maxHealth;
            // Respawn at spawn
            player.position.set(0, 40, 0);
        }
    }

    moveWithCollision(deltaTime) {
        const newPos = this.position.clone();
        
        // Move X
        newPos.x += this.velocity.x * deltaTime;
        if (this.checkCollision(newPos)) {
            newPos.x = this.position.x;
            this.velocity.x = 0;
        }
        
        // Move Z
        newPos.z += this.velocity.z * deltaTime;
        if (this.checkCollision(newPos)) {
            newPos.z = this.position.z;
            this.velocity.z = 0;
        }
        
        // Move Y
        newPos.y += this.velocity.y * deltaTime;
        if (this.checkCollision(newPos)) {
            if (this.velocity.y < 0) {
                this.onGround = true;
            }
            newPos.y = this.position.y;
            this.velocity.y = 0;
        } else {
            this.onGround = false;
        }
        
        this.position.copy(newPos);
        this.position.y = Math.max(1, this.position.y);
    }

    checkCollision(pos) {
        const width = 0.3;
        const height = this.config.height;
        
        for (let dx = -1; dx <= 1; dx++) {
            for (let dz = -1; dz <= 1; dz++) {
                for (let dy = 0; dy <= 1; dy++) {
                    const bx = Math.floor(pos.x + dx * width);
                    const by = Math.floor(pos.y + dy * height);
                    const bz = Math.floor(pos.z + dz * width);
                    
                    const block = this.world.getBlock(bx, by, bz);
                    if (block !== BLOCK_TYPES.AIR && block !== BLOCK_TYPES.WATER) {
                        return true;
                    }
                }
            }
        }
        return false;
    }

    takeDamage(amount) {
        this.health -= amount;
        return this.health <= 0;
    }

    dispose() {
        if (this.mesh) {
            this.mesh.geometry.dispose();
            this.mesh.material.dispose();
        }
    }
}

class EnemyManager {
    constructor(world) {
        this.world = world;
        this.enemies = [];
        this.maxEnemies = 10;
        this.spawnRadius = 20;
        this.spawnCooldown = 5000;
        this.lastSpawnTime = 0;
    }

    update(deltaTime, players, scene, isNight) {
        const now = Date.now();

        // Only spawn enemies at night
        if (isNight) {
            for (const player of players) {
                if (now - this.lastSpawnTime > this.spawnCooldown &&
                    this.enemies.length < this.maxEnemies) {
                    this.trySpawn(player, scene);
                    this.lastSpawnTime = now;
                }
            }
        }
        
        // Update existing enemies
        for (let i = this.enemies.length - 1; i >= 0; i--) {
            const enemy = this.enemies[i];
            enemy.update(deltaTime, players);
            
            // Remove if too far or dead
            if (enemy.health <= 0) {
                this.removeEnemy(enemy, scene, i);
            }
        }
    }

    trySpawn(player, scene) {
        const angle = Math.random() * Math.PI * 2;
        const distance = 15 + Math.random() * 10;
        
        const spawnX = player.position.x + Math.cos(angle) * distance;
        const spawnZ = player.position.z + Math.sin(angle) * distance;
        const spawnY = this.world.getSpawnHeight(Math.floor(spawnX), Math.floor(spawnZ));
        
        if (spawnY < 1 || spawnY > 50) return;
        
        // Random enemy type
        const types = Object.keys(ENEMY_TYPES);
        const type = types[Math.floor(Math.random() * types.length)];
        
        const enemy = new Enemy(type, new THREE.Vector3(spawnX, spawnY, spawnZ), this.world);
        this.enemies.push(enemy);
        scene.add(enemy.mesh);
    }

    removeEnemy(enemy, scene, index) {
        scene.remove(enemy.mesh);
        enemy.dispose();
        this.enemies.splice(index, 1);
    }

    checkProjectileHit(position, radius, damage, scene) {
        for (let i = this.enemies.length - 1; i >= 0; i--) {
            const enemy = this.enemies[i];
            const dist = position.distanceTo(enemy.position);
            
            if (dist < radius) {
                if (enemy.takeDamage(damage)) {
                    this.removeEnemy(enemy, scene, i);
                    return true;
                }
            }
        }
        return false;
    }
}

window.ENEMY_TYPES = ENEMY_TYPES;
window.Enemy = Enemy;
window.EnemyManager = EnemyManager;
