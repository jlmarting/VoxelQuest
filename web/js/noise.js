// Simple Perlin noise implementation for terrain generation
class PerlinNoise {
    constructor(seed = 0) {
        this.seed = seed;
        this.permutation = this.generatePermutation();
    }

    generatePermutation() {
        const perm = [];
        for (let i = 0; i < 256; i++) perm[i] = i;
        
        // Shuffle using seed
        for (let i = 255; i > 0; i--) {
            const j = Math.floor(this.seededRandom() * (i + 1));
            [perm[i], perm[j]] = [perm[j], perm[i]];
        }
        
        // Duplicate
        for (let i = 0; i < 256; i++) perm[256 + i] = perm[i];
        return perm;
    }

    seededRandom() {
        this.seed = (this.seed * 16807 + 0) % 2147483647;
        return (this.seed - 1) / 2147483646;
    }

    fade(t) {
        return t * t * t * (t * (t * 6 - 15) + 10);
    }

    lerp(t, a, b) {
        return a + t * (b - a);
    }

    grad(hash, x, y) {
        const h = hash & 3;
        const u = h < 2 ? x : y;
        const v = h < 2 ? y : x;
        return ((h & 1) ? -u : u) + ((h & 2) ? -v : v);
    }

    noise(x, y) {
        const X = Math.floor(x) & 255;
        const Y = Math.floor(y) & 255;
        
        x -= Math.floor(x);
        y -= Math.floor(y);
        
        const u = this.fade(x);
        const v = this.fade(y);
        
        const A = this.permutation[X] + Y;
        const B = this.permutation[X + 1] + Y;
        
        return this.lerp(v,
            this.lerp(u, this.grad(this.permutation[A], x, y),
                         this.grad(this.permutation[B], x - 1, y)),
            this.lerp(u, this.grad(this.permutation[A + 1], x, y - 1),
                         this.grad(this.permutation[B + 1], x - 1, y - 1))
        );
    }

    octaveNoise(x, y, octaves = 4, persistence = 0.5) {
        let total = 0;
        let frequency = 1;
        let amplitude = 1;
        let maxValue = 0;
        
        for (let i = 0; i < octaves; i++) {
            total += this.noise(x * frequency, y * frequency) * amplitude;
            maxValue += amplitude;
            amplitude *= persistence;
            frequency *= 2;
        }
        
        return total / maxValue;
    }
}

window.PerlinNoise = PerlinNoise;
