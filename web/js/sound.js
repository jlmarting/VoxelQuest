// Sound manager using Web Audio API - procedural sounds
class SoundManager {
    constructor() {
        this.ctx = null;
        this.enabled = true;
        this.masterVolume = 0.3;
    }

    init() {
        if (this.ctx) return;
        try {
            this.ctx = new (window.AudioContext || window.webkitAudioContext)();
        } catch (e) {
            console.warn('Web Audio not supported');
            this.enabled = false;
        }
    }

    // Play a noise burst (for block sounds)
    playNoise(duration, frequency, type, volume) {
        if (!this.enabled || !this.ctx) return;
        if (this.ctx.state === 'suspended') this.ctx.resume();

        const osc = this.ctx.createOscillator();
        const gain = this.ctx.createGain();
        const filter = this.ctx.createBiquadFilter();

        osc.type = type || 'square';
        osc.frequency.value = frequency;

        filter.type = 'lowpass';
        filter.frequency.value = frequency * 2;

        gain.gain.setValueAtTime((volume || 0.3) * this.masterVolume, this.ctx.currentTime);
        gain.gain.exponentialRampToValueAtTime(0.001, this.ctx.currentTime + duration);

        osc.connect(filter);
        filter.connect(gain);
        gain.connect(this.ctx.destination);

        osc.start(this.ctx.currentTime);
        osc.stop(this.ctx.currentTime + duration);
    }

    // Block break sound
    blockBreak() {
        this.playNoise(0.15, 200, 'square', 0.2);
        setTimeout(() => this.playNoise(0.1, 150, 'square', 0.15), 50);
    }

    // Block place sound
    blockPlace() {
        this.playNoise(0.1, 300, 'square', 0.25);
        this.playNoise(0.08, 400, 'sine', 0.15);
    }

    // Footstep sound
    footstep() {
        const freq = 80 + Math.random() * 40;
        this.playNoise(0.08, freq, 'square', 0.1);
    }

    // Jump sound
    jump() {
        if (!this.enabled || !this.ctx) return;
        if (this.ctx.state === 'suspended') this.ctx.resume();

        const osc = this.ctx.createOscillator();
        const gain = this.ctx.createGain();

        osc.type = 'sine';
        osc.frequency.setValueAtTime(200, this.ctx.currentTime);
        osc.frequency.exponentialRampToValueAtTime(400, this.ctx.currentTime + 0.15);

        gain.gain.setValueAtTime(0.2 * this.masterVolume, this.ctx.currentTime);
        gain.gain.exponentialRampToValueAtTime(0.001, this.ctx.currentTime + 0.15);

        osc.connect(gain);
        gain.connect(this.ctx.destination);

        osc.start(this.ctx.currentTime);
        osc.stop(this.ctx.currentTime + 0.15);
    }

    // Damage/hurt sound
    hurt() {
        this.playNoise(0.2, 150, 'sawtooth', 0.3);
        setTimeout(() => this.playNoise(0.15, 100, 'sawtooth', 0.2), 100);
    }

    // Fall/land sound
    land() {
        this.playNoise(0.12, 100, 'square', 0.2);
    }

    // Menu click sound
    click() {
        this.playNoise(0.05, 800, 'sine', 0.15);
    }

    // Toggle sound on/off
    toggle() {
        this.enabled = !this.enabled;
        return this.enabled;
    }
}

window.SoundManager = SoundManager;
