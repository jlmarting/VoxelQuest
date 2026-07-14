class PathNode {
    constructor(x, z, parent, g, h) {
        this.x = x;
        this.z = z;
        this.parent = parent;
        this.g = g;
        this.h = h;
        this.f = g + h;
    }
}

class Pathfinder {
    constructor(world) {
        this.world = world;
        this.maxSteps = 500;
    }

    findPath(startX, startZ, goalX, goalZ, startY) {
        const open = [];
        const closed = new Set();

        const start = new PathNode(
            Math.floor(startX), Math.floor(startZ), null, 0, 0
        );
        start.h = this.heuristic(start.x, start.z, goalX, goalZ);
        start.f = start.g + start.h;
        open.push(start);

        let steps = 0;

        while (open.length > 0 && steps < this.maxSteps) {
            steps++;
            open.sort((a, b) => a.f - b.f);
            const current = open.shift();

            if (current.x === Math.floor(goalX) && current.z === Math.floor(goalZ)) {
                return this.reconstructPath(current);
            }

            const key = `${current.x},${current.z}`;
            if (closed.has(key)) continue;
            closed.add(key);

            const neighbors = this.getNeighbors(current, goalX, goalZ, startY);

            for (const n of neighbors) {
                const nKey = `${n.x},${n.z}`;
                if (closed.has(nKey)) continue;

                const existing = open.find(o => o.x === n.x && o.z === n.z);
                if (existing) {
                    if (n.g < existing.g) {
                        existing.g = n.g;
                        existing.f = existing.g + existing.h;
                        existing.parent = current;
                    }
                } else {
                    open.push(n);
                }
            }
        }

        return null;
    }

    getNeighbors(node, goalX, goalZ, startY) {
        const dirs = [
            { dx: 0, dz: -1 }, { dx: 0, dz: 1 },
            { dx: -1, dz: 0 }, { dx: 1, dz: 0 }
        ];
        const neighbors = [];
        const baseY = Math.floor(startY);
        const baseYCheck = baseY - 1;

        for (const d of dirs) {
            const nx = node.x + d.dx;
            const nz = node.z + d.dz;

            if (this.isWalkable(nx, nz, baseY, baseYCheck)) {
                const jump = this.requiresJump(nx, nz, baseY);
                const cost = jump ? 2 : 1;
                const g = node.g + cost;
                const h = this.heuristic(nx, nz, Math.floor(goalX), Math.floor(goalZ));
                const n = new PathNode(nx, nz, node, g, h);
                n.jump = jump;
                neighbors.push(n);
            }
        }

        return neighbors;
    }

    isWalkable(x, z, baseY, checkY) {
        const foot = this.world.getBlock(x, baseY, z);
        const head = this.world.getBlock(x, baseY + 1, z);
        if (foot === BLOCK_TYPES.AIR || head !== BLOCK_TYPES.AIR) return false;

        const support = this.world.getBlock(x, checkY, z);
        if (support === BLOCK_TYPES.AIR || support === BLOCK_TYPES.WATER) return false;

        return true;
    }

    requiresJump(x, z, baseY) {
        const foot = this.world.getBlock(x, baseY, z);
        return foot !== BLOCK_TYPES.AIR;
    }

    heuristic(x1, z1, x2, z2) {
        return Math.abs(x1 - x2) + Math.abs(z1 - z2);
    }

    reconstructPath(node) {
        const path = [];
        let current = node;
        while (current) {
            path.unshift({ x: current.x, z: current.z, jump: !!current.jump });
            current = current.parent;
        }
        return path;
    }
}

window.Pathfinder = Pathfinder;

class PathFollower {
    constructor() {
        this.state = 'IDLE';
        this.path = [];
        this.stepIndex = 0;
        this.playerId = null;
        this.gamepadHandler = null;
        this.player = null;
        this.response = null;
        this.lastPosition = null;
        this.stuckFrames = 0;
        this.maxStuckFrames = 60;
    }

    start(path, playerId, player, gamepadHandler, response) {
        this.state = 'FOLLOWING';
        this.path = path;
        this.stepIndex = 0;
        this.playerId = playerId;
        this.player = player;
        this.gamepadHandler = gamepadHandler;
        this.response = response;
        this.lastPosition = player.position.clone();
        this.stuckFrames = 0;
        this.gamepadHandler.enableVirtual(playerId - 1);
    }

    stop() {
        this.state = 'IDLE';
        this.path = [];
        this.resetInput();
    }

    resetInput() {
        if (this.gamepadHandler) {
            this.gamepadHandler.setVirtualInput(this.playerId - 1, {
                move: { x: 0, z: 0 },
                look: { x: 0, y: 0 },
                jump: false
            });
        }
    }

    tick() {
        if (this.state !== 'FOLLOWING' || !this.player || !this.gamepadHandler) return;

        const target = this.path[this.stepIndex];
        if (!target) {
            this.finish('SUCCESS');
            return;
        }

        const dx = target.x + 0.5 - this.player.position.x;
        const dz = target.z + 0.5 - this.player.position.z;
        const dist = Math.hypot(dx, dz);

        if (dist < 0.4) {
            this.stepIndex++;
            this.stuckFrames = 0;
            if (this.stepIndex >= this.path.length) {
                this.finish('SUCCESS');
                return;
            }
            return;
        }

        const desiredYaw = Math.atan2(-dx, -dz);
        let yawDiff = desiredYaw - this.player.rotation.y;
        while (yawDiff > Math.PI) yawDiff -= Math.PI * 2;
        while (yawDiff < -Math.PI) yawDiff += Math.PI * 2;
        const lookX = Math.max(-1, Math.min(1, yawDiff * 2));

        this.gamepadHandler.setVirtualInput(this.playerId - 1, {
            move: { x: 0, z: -1 },
            look: { x: lookX, y: 0 },
            jump: !!target.jump
        });

        const moved = Math.hypot(
            this.player.position.x - this.lastPosition.x,
            this.player.position.z - this.lastPosition.z
        );
        if (moved < 0.02) {
            this.stuckFrames++;
            if (this.stuckFrames > this.maxStuckFrames) {
                this.finish('FAILURE');
                return;
            }
        } else {
            this.stuckFrames = 0;
        }

        this.lastPosition.copy(this.player.position);
    }

    finish(status) {
        this.state = 'COMPLETE';
        this.resetInput();
        if (this.response) {
            this.response.status = status;
            this.response.success = status === 'SUCCESS';
            this.response.pathLength = this.path.length;
            this.response.stepsCompleted = this.stepIndex;
        }
    }
}

window.PathFollower = PathFollower;
