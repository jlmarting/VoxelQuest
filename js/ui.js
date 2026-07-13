class UIManager {
    constructor() {
        this.elements = {};
        this.inventoryOpen = false;
    }

    initialize(player1, player2) {
        this.player1 = player1;
        this.player2 = player2;
        
        // Create hotbar slots
        this.createHotbar('hotbar-p1', player1);
        this.createHotbar('hotbar-p2', player2);
        
        // Inventory
        this.setupInventory();
    }

    createHotbar(containerId, player) {
        const container = document.getElementById(containerId);
        container.innerHTML = '';
        
        for (let i = 0; i < 9; i++) {
            const slot = document.createElement('div');
            slot.className = 'hotbar-slot' + (i === player.selectedSlot ? ' selected' : '');
            slot.dataset.slot = i;
            
            const item = player.inventory.slots[i];
            if (item) {
                const icon = document.createElement('div');
                icon.className = 'block-icon';
                // Get color based on item type
                let color = 0x888888;
                if (item.itemType === 'block' && BLOCK_COLORS[item.type]) {
                    color = BLOCK_COLORS[item.type];
                } else if (item.itemType === 'asset') {
                    const assetColors = {
                        'torch': 0xff6600, 'window': 0x88ccff, 'door': 0x8b5a2b,
                        'crafting_table': 0xbc9458, 'chest': 0x8b5a2b, 'bed': 0xcc3333,
                        'chair': 0x8b5a2b, 'table': 0x8b5a2b, 'bookshelf': 0x6b4423,
                        'fence': 0x8b7355, 'lamp': 0xffeecc, 'flower_pot': 0xff6688
                    };
                    color = assetColors[item.type] || 0x888888;
                }
                icon.style.backgroundColor = '#' + color.toString(16).padStart(6, '0');
                slot.appendChild(icon);
                
                if (item.count > 1) {
                    const count = document.createElement('span');
                    count.textContent = item.count;
                    count.style.position = 'absolute';
                    count.style.bottom = '2px';
                    count.style.right = '2px';
                    count.style.fontSize = '10px';
                    slot.appendChild(count);
                }
            }
            
            slot.addEventListener('click', () => {
                player.selectedSlot = i;
                this.updateHotbar(containerId, player);
            });
            
            container.appendChild(slot);
        }
    }

    updateHotbar(containerId, player) {
        const container = document.getElementById(containerId);
        const slots = container.querySelectorAll('.hotbar-slot');
        
        slots.forEach((slot, i) => {
            slot.className = 'hotbar-slot' + (i === player.selectedSlot ? ' selected' : '');
            
            const item = player.inventory.slots[i];
            slot.innerHTML = '';
            
            if (item) {
                const icon = document.createElement('div');
                icon.className = 'block-icon';
                // Get color based on item type
                let color = 0x888888;
                if (item.itemType === 'block' && BLOCK_COLORS[item.type]) {
                    color = BLOCK_COLORS[item.type];
                } else if (item.itemType === 'asset') {
                    const assetColors = {
                        'torch': 0xff6600, 'window': 0x88ccff, 'door': 0x8b5a2b,
                        'crafting_table': 0xbc9458, 'chest': 0x8b5a2b, 'bed': 0xcc3333,
                        'chair': 0x8b5a2b, 'table': 0x8b5a2b, 'bookshelf': 0x6b4423,
                        'fence': 0x8b7355, 'lamp': 0xffeecc, 'flower_pot': 0xff6688
                    };
                    color = assetColors[item.type] || 0x888888;
                }
                icon.style.backgroundColor = '#' + color.toString(16).padStart(6, '0');
                slot.appendChild(icon);
                
                if (item.count > 1) {
                    const count = document.createElement('span');
                    count.textContent = item.count;
                    count.style.position = 'absolute';
                    count.style.bottom = '2px';
                    count.style.right = '2px';
                    count.style.fontSize = '10px';
                    slot.appendChild(count);
                }
            }
        });
    }

    updateHealth(playerId, health) {
        const healthBar = document.getElementById(`health-p${playerId}`);
        if (healthBar) {
            healthBar.textContent = `❤️ ${health}`;
        }
    }

    updateDebugInfo(playerId, info) {
        const debugInfo = document.getElementById(`debug-p${playerId}`);
        if (debugInfo) {
            debugInfo.innerHTML = info;
        }
    }

    setupInventory() {
        const overlay = document.getElementById('inventory-overlay');
        const grid = document.getElementById('inventory-grid-p1');
        
        // Create inventory grid
        for (let i = 0; i < 36; i++) {
            const slot = document.createElement('div');
            slot.className = 'inventory-slot';
            slot.dataset.slot = i;
            grid.appendChild(slot);
        }
    }

    toggleInventory(playerId) {
        const overlay = document.getElementById('inventory-overlay');
        this.inventoryOpen = !this.inventoryOpen;
        overlay.classList.toggle('hidden', !this.inventoryOpen);
        
        if (this.inventoryOpen) {
            this.updateInventoryDisplay(playerId);
        }
    }

    updateInventoryDisplay(playerId) {
        const player = playerId === 1 ? this.player1 : this.player2;
        const grid = document.getElementById('inventory-grid-p1');
        const slots = grid.querySelectorAll('.inventory-slot');
        
        slots.forEach((slot, i) => {
            const item = player.inventory.slots[i];
            slot.innerHTML = '';
            
            if (item) {
                const icon = document.createElement('div');
                icon.className = 'block-icon';
                // Get color based on item type
                let color = 0x888888;
                if (item.itemType === 'block' && BLOCK_COLORS[item.type]) {
                    color = BLOCK_COLORS[item.type];
                } else if (item.itemType === 'asset') {
                    const assetColors = {
                        'torch': 0xff6600, 'window': 0x88ccff, 'door': 0x8b5a2b,
                        'crafting_table': 0xbc9458, 'chest': 0x8b5a2b, 'bed': 0xcc3333,
                        'chair': 0x8b5a2b, 'table': 0x8b5a2b, 'bookshelf': 0x6b4423,
                        'fence': 0x8b7355, 'lamp': 0xffeecc, 'flower_pot': 0xff6688
                    };
                    color = assetColors[item.type] || 0x888888;
                }
                icon.style.backgroundColor = '#' + color.toString(16).padStart(6, '0');
                icon.style.width = '30px';
                icon.style.height = '30px';
                slot.appendChild(icon);
                
                if (item.count > 1) {
                    const count = document.createElement('span');
                    count.textContent = item.count;
                    count.style.position = 'absolute';
                    count.style.bottom = '2px';
                    count.style.right = '2px';
                    slot.appendChild(count);
                }
            }
            
            // Click to select
            slot.onclick = () => {
                if (i < 9) {
                    player.selectedSlot = i;
                    this.updateHotbar(`hotbar-p${playerId}`, player);
                }
            };
        });
    }

    showCraftingMenu(playerId) {
        const player = playerId === 1 ? this.player1 : this.player2;
        const recipes = player.inventory.getAvailableRecipes();
        
        // Simple crafting notification
        if (recipes.length > 0) {
            const recipe = recipes[0];
            const inputName = BLOCK_NAMES[Object.keys(recipe.input)[0]];
            const outputName = BLOCK_NAMES[recipe.output];
            
            // Auto-craft for simplicity
            if (player.inventory.craft(recipe.output)) {
                this.showNotification(`Crafted ${recipe.outputCount} ${outputName}`);
                this.updateHotbar(`hotbar-p${playerId}`, player);
            }
        }
    }

    showNotification(message) {
        const notification = document.createElement('div');
        notification.style.cssText = `
            position: fixed;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            background: rgba(0, 0, 0, 0.8);
            color: white;
            padding: 20px 40px;
            border-radius: 8px;
            font-size: 18px;
            z-index: 200;
            animation: fadeInOut 2s forwards;
        `;
        notification.textContent = message;
        document.body.appendChild(notification);
        
        setTimeout(() => notification.remove(), 2000);
    }
}

window.UIManager = UIManager;
