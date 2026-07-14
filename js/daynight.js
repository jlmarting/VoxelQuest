class DayNightCycle {
    constructor(scene) {
        this.scene = scene;

        // Time settings
        this.dayDuration = 600;
        this.timeOfDay = 0.35; // Start at morning

        // Hemisphere light (sky top / ground bottom gradient)
        this.hemiLight = new THREE.HemisphereLight(0x87ceeb, 0x5d8c3e, 0.6);
        this.scene.add(this.hemiLight);

        // Main sun directional light with shadows
        this.sunLight = new THREE.DirectionalLight(0xfff5e0, 1.0);
        this.sunLight.position.set(100, 150, 80);
        this.sunLight.castShadow = true;
        this.sunLight.shadow.mapSize.width = 2048;
        this.sunLight.shadow.mapSize.height = 2048;
        this.sunLight.shadow.camera.near = 0.5;
        this.sunLight.shadow.camera.far = 500;
        this.sunLight.shadow.camera.left = -80;
        this.sunLight.shadow.camera.right = 80;
        this.sunLight.shadow.camera.top = 80;
        this.sunLight.shadow.camera.bottom = -80;
        this.sunLight.shadow.bias = -0.0005;
        this.scene.add(this.sunLight);

        // Ambient fill light
        this.ambientLight = new THREE.AmbientLight(0x404060, 0.3);
        this.scene.add(this.ambientLight);

        // Moon light (cool blue tint)
        this.moonLight = new THREE.DirectionalLight(0x6688cc, 0.15);
        this.scene.add(this.moonLight);

        // Sky / fog
        this.scene.background = new THREE.Color(0x87ceeb);
        this.scene.fog = new THREE.FogExp2(0x87ceeb, 0.008);

        // Stars
        this.stars = this.createStars();

        // Sun / Moon
        this.sun = this.createCelestialBody(0xffee88, 12);
        this.moon = this.createCelestialBody(0xccddff, 9);
    }

    createStars() {
        const geo = new THREE.BufferGeometry();
        const pos = [];
        for (let i = 0; i < 1500; i++) {
            const theta = Math.random() * Math.PI * 2;
            const phi = Math.acos(Math.random() * 2 - 1);
            const r = 600;
            pos.push(
                r * Math.sin(phi) * Math.cos(theta),
                r * Math.sin(phi) * Math.sin(theta),
                r * Math.cos(phi)
            );
        }
        geo.setAttribute('position', new THREE.Float32BufferAttribute(pos, 3));
        const mat = new THREE.PointsMaterial({ color: 0xffffff, size: 1.5, transparent: true, opacity: 0 });
        const stars = new THREE.Points(geo, mat);
        this.scene.add(stars);
        return stars;
    }

    createCelestialBody(color, size) {
        const geo = new THREE.SphereGeometry(size, 24, 24);
        const mat = new THREE.MeshBasicMaterial({ color });
        const body = new THREE.Mesh(geo, mat);
        this.scene.add(body);
        return body;
    }

    update(deltaTime) {
        this.timeOfDay += deltaTime / this.dayDuration;
        if (this.timeOfDay >= 1) this.timeOfDay -= 1;

        // Sun angle: 0 = midnight, 0.25 = sunrise, 0.5 = noon, 0.75 = sunset
        const sunAngle = this.timeOfDay * Math.PI * 2 - Math.PI / 2;
        const sunX = Math.cos(sunAngle) * 200;
        const sunY = Math.sin(sunAngle) * 200;

        this.sunLight.position.set(sunX, Math.max(sunY, 10), 80);
        this.sun.position.set(sunX * 1.5, sunY * 1.5, -200);

        this.moonLight.position.set(-sunX, Math.max(-sunY, 10), 80);
        this.moon.position.set(-sunX * 1.5, -sunY * 1.5, -200);

        // Day progress: 1 at noon, -1 at midnight
        const dayProgress = Math.sin(this.timeOfDay * Math.PI * 2);
        const isDaytime = dayProgress > -0.1;
        const isSunAbove = sunY > 0;

        // --- Sky colors ---
        const skyDay = new THREE.Color(0x6cb4ee);
        const skySunset = new THREE.Color(0xff8844);
        const skyNight = new THREE.Color(0x0b0d2a);
        const skyColor = new THREE.Color();

        if (dayProgress > 0.3) {
            // Full day
            skyColor.copy(skyDay);
        } else if (dayProgress > -0.1) {
            // Sunrise / sunset transition
            const t = (dayProgress + 0.1) / 0.4;
            skyColor.lerpColors(skySunset, skyDay, t);
        } else {
            // Night
            const t = Math.min(1, (-dayProgress - 0.1) / 0.5);
            skyColor.lerpColors(skySunset, skyNight, t);
        }

        this.scene.background = skyColor;
        this.scene.fog.color.copy(skyColor);

        // --- Sun light ---
        if (isSunAbove) {
            const sunFactor = Math.max(0, Math.min(1, (sunY / 150)));
            this.sunLight.intensity = sunFactor * 1.2;
            // Warm tint near horizon
            const warmth = Math.max(0, 1 - sunY / 80);
            this.sunLight.color.setRGB(1, 1 - warmth * 0.15, 0.9 - warmth * 0.3);
        } else {
            this.sunLight.intensity = 0;
        }

        // --- Moon light ---
        if (!isSunAbove && sunY < -20) {
            this.moonLight.intensity = Math.min(0.25, Math.abs(sunY) / 200);
            this.moon.visible = true;
        } else {
            this.moonLight.intensity = 0;
            this.moon.visible = false;
        }

        // --- Hemisphere light ---
        const skyColorHemi = new THREE.Color();
        const groundColorHemi = new THREE.Color();
        if (isSunAbove) {
            skyColorHemi.copy(skyDay);
            groundColorHemi.setHex(0x5d8c3e);
            this.hemiLight.intensity = 0.5 + dayProgress * 0.3;
        } else {
            skyColorHemi.setHex(0x1a1a3e);
            groundColorHemi.setHex(0x1a1a10);
            this.hemiLight.intensity = 0.15;
        }
        this.hemiLight.color.copy(skyColorHemi);
        this.hemiLight.groundColor.copy(groundColorHemi);

        // --- Ambient ---
        this.ambientLight.intensity = isSunAbove ? 0.25 + dayProgress * 0.15 : 0.1;

        // --- Stars ---
        this.stars.material.opacity = isSunAbove ? 0 : Math.min(0.9, (-dayProgress - 0.1) * 1.5);

        // --- Sun visibility ---
        this.sun.visible = isSunAbove && sunY > 10;
    }

    isNight() {
        return Math.sin(this.timeOfDay * Math.PI * 2) < -0.1;
    }

    getTimeString() {
        const hours = Math.floor(this.timeOfDay * 24);
        const minutes = Math.floor((this.timeOfDay * 24 - hours) * 60);
        return `${hours.toString().padStart(2, '0')}:${minutes.toString().padStart(2, '0')}`;
    }
}

window.DayNightCycle = DayNightCycle;
