// Complete inventory system with UI
class Inventory {
    constructor(player) {
        this.player = player;
        this.slots = new Array(36).fill(null);
        this.hotbarSize = 9;
        this.isOpen = false;
        this.selectedSlot = 0;

        // Item database with names and colors
        this.ITEM_DB = {
            // Blocks
            [BLOCK_TYPES.GRASS]: { name: 'Hierba', color: 0x5d8c3e, type: 'block' },
            [BLOCK_TYPES.DIRT]: { name: 'Tierra', color: 0x8b6942, type: 'block' },
            [BLOCK_TYPES.STONE]: { name: 'Piedra', color: 0x808080, type: 'block' },
            [BLOCK_TYPES.WOOD]: { name: 'Madera', color: 0x6b4423, type: 'block' },
            [BLOCK_TYPES.LEAVES]: { name: 'Hojas', color: 0x2d5a1e, type: 'block' },
            [BLOCK_TYPES.SAND]: { name: 'Arena', color: 0xd4c4a0, type: 'block' },
            [BLOCK_TYPES.COBBLESTONE]: { name: 'Roca', color: 0x6b6b6b, type: 'block' },
            [BLOCK_TYPES.PLANKS]: { name: 'Tablones', color: 0xbc9458, type: 'block' },
            // Assets
            'torch': { name: 'Antorcha', color: 0xff6600, type: 'asset' },
            'window': { name: 'Ventana', color: 0x88ccff, type: 'asset' },
            'door': { name: 'Puerta', color: 0x8b5a2b, type: 'asset' },
            'crafting_table': { name: 'Mesa Crafteo', color: 0xbc9458, type: 'asset' },
            'chest': { name: 'Cofre', color: 0x8b5a2b, type: 'asset' },
            'bed': { name: 'Cama', color: 0xcc3333, type: 'asset' },
            'chair': { name: 'Silla', color: 0x8b5a2b, type: 'asset' },
            'table': { name: 'Mesa', color: 0x8b5a2b, type: 'asset' },
            'bookshelf': { name: 'Estantería', color: 0x6b4423, type: 'asset' },
            'fence': { name: 'Valla', color: 0x8b7355, type: 'asset' },
            'lamp': { name: 'Lámpara', color: 0xffeecc, type: 'asset' },
            'flower_pot': { name: 'Maceta', color: 0xff6688, type: 'asset' }
        };

        // Crafting recipes
        this.recipes = [
            { name: 'Tablones', input: { [BLOCK_TYPES.WOOD]: 1 }, output: { type: BLOCK_TYPES.PLANKS, count: 4 } },
            { name: 'Roca', input: { [BLOCK_TYPES.STONE]: 1 }, output: { type: BLOCK_TYPES.COBBLESTONE, count: 2 } }
        ];

        this.initializeDefaultItems();
    }

    initializeDefaultItems() {
        this.slots[0] = { type: BLOCK_TYPES.GRASS, count: 64 };
        this.slots[1] = { type: BLOCK_TYPES.DIRT, count: 64 };
        this.slots[2] = { type: BLOCK_TYPES.STONE, count: 64 };
        this.slots[3] = { type: BLOCK_TYPES.WOOD, count: 32 };
        this.slots[4] = { type: BLOCK_TYPES.PLANKS, count: 32 };
        this.slots[5] = { type: BLOCK_TYPES.COBBLESTONE, count: 32 };
        this.slots[6] = { type: BLOCK_TYPES.SAND, count: 32 };
        this.slots[7] = { type: BLOCK_TYPES.LEAVES, count: 32 };
        this.slots[8] = { type: 'torch', count: 16 };
        this.addItem('window', 8);
        this.addItem('door', 4);
        this.addItem('crafting_table', 2);
        this.addItem('chest', 2);
        this.addItem('bed', 1);
        this.addItem('lamp', 4);
        this.addItem('chair', 4);
        this.addItem('table', 2);
        this.addItem('bookshelf', 2);
        this.addItem('fence', 16);
    }

    getItemInfo(type) {
        return this.ITEM_DB[type] || { name: type, color: 0x888888, type: 'unknown' };
    }

    getSelectedSlot() {
        return this.selectedSlot;
    }

    getSelectedItem() {
        return this.slots[this.selectedSlot];
    }

    hasItem(type, count = 1) {
        for (const slot of this.slots) {
            if (slot && slot.type === type && slot.count >= count) {
                return true;
            }
        }
        return false;
    }

    addItem(type, count = 1) {
        // Try to stack with existing
        for (const slot of this.slots) {
            if (slot && slot.type === type && slot.count < 64) {
                const canAdd = Math.min(count, 64 - slot.count);
                slot.count += canAdd;
                count -= canAdd;
                if (count <= 0) return true;
            }
        }

        // Find empty slot
        for (let i = 0; i < this.slots.length; i++) {
            if (!this.slots[i]) {
                this.slots[i] = { type, count: Math.min(count, 64) };
                count -= 64;
                if (count <= 0) return true;
            }
        }

        return count <= 0;
    }

    removeItem(type, count = 1) {
        for (let i = 0; i < this.slots.length; i++) {
            if (this.slots[i] && this.slots[i].type === type) {
                const canRemove = Math.min(count, this.slots[i].count);
                this.slots[i].count -= canRemove;
                count -= canRemove;

                if (this.slots[i].count <= 0) {
                    this.slots[i] = null;
                }

                if (count <= 0) return true;
            }
        }
        return count <= 0;
    }

    swapSlots(index1, index2) {
        const temp = this.slots[index1];
        this.slots[index1] = this.slots[index2];
        this.slots[index2] = temp;
    }

    craft(recipe) {
        // Check if we have all inputs
        for (const [type, count] of Object.entries(recipe.input)) {
            if (!this.hasItem(parseInt(type), count)) {
                return false;
            }
        }

        // Remove inputs
        for (const [type, count] of Object.entries(recipe.input)) {
            this.removeItem(parseInt(type), count);
        }

        // Add output
        return this.addItem(recipe.output.type, recipe.output.count);
    }

    getAvailableRecipes() {
        return this.recipes.filter(recipe => {
            for (const [type, count] of Object.entries(recipe.input)) {
                if (!this.hasItem(parseInt(type), count)) {
                    return false;
                }
            }
            return true;
        });
    }
}

// Inventory UI Manager
class InventoryUI {
    constructor(inventory, onUpdate) {
        this.inventory = inventory;
        this.onUpdate = onUpdate;
        this.isOpen = false;
        this.selectedSlot = -1;
        this.dragging = null;

        this.createUI();
    }

    createUI() {
        const overlay = document.getElementById('inventory-overlay');
        overlay.innerHTML = `
            <div class="inventory-header">
                <h2>Inventario</h2>
                <button class="close-btn" onclick="window.gameUI.closeInventory()">×</button>
            </div>
            <div class="inventory-main">
                <div class="inventory-grid" id="inv-grid"></div>
                <div class="inventory-crafting">
                    <h3>Crafteo</h3>
                    <div id="crafting-recipes"></div>
                </div>
            </div>
            <div class="inventory-hotbar" id="inv-hotbar"></div>
        `;

        this.renderGrid();
        this.renderHotbar();
        this.renderCrafting();
    }

    renderGrid() {
        const grid = document.getElementById('inv-grid');
        if (!grid) return;
        grid.innerHTML = '';

        for (let i = 0; i < 36; i++) {
            const slot = document.createElement('div');
            slot.className = 'inventory-slot' + (i === this.selectedSlot ? ' selected' : '');
            slot.dataset.index = i;

            const item = this.inventory.slots[i];
            if (item) {
                const info = this.inventory.getItemInfo(item.type);
                const icon = document.createElement('div');
                icon.className = 'inv-item-icon';
                icon.style.backgroundColor = '#' + info.color.toString(16).padStart(6, '0');
                slot.appendChild(icon);

                if (item.count > 1) {
                    const count = document.createElement('span');
                    count.className = 'inv-item-count';
                    count.textContent = item.count;
                    slot.appendChild(count);
                }

                const name = document.createElement('span');
                name.className = 'inv-item-name';
                name.textContent = info.name;
                slot.appendChild(name);
            }

            slot.addEventListener('click', () => this.onSlotClick(i));
            slot.addEventListener('dragstart', (e) => this.onDragStart(e, i));
            slot.addEventListener('dragover', (e) => e.preventDefault());
            slot.addEventListener('drop', (e) => this.onDrop(e, i));

            grid.appendChild(slot);
        }
    }

    renderHotbar() {
        const hotbar = document.getElementById('inv-hotbar');
        if (!hotbar) return;
        hotbar.innerHTML = '';

        for (let i = 0; i < 9; i++) {
            const slot = document.createElement('div');
            slot.className = 'hotbar-slot' + (i === this.inventory.selectedSlot ? ' selected' : '');

            const item = this.inventory.slots[i];
            if (item) {
                const info = this.inventory.getItemInfo(item.type);
                const icon = document.createElement('div');
                icon.className = 'hotbar-item-icon';
                icon.style.backgroundColor = '#' + info.color.toString(16).padStart(6, '0');
                slot.appendChild(icon);

                if (item.count > 1) {
                    const count = document.createElement('span');
                    count.className = 'hotbar-item-count';
                    count.textContent = item.count;
                    slot.appendChild(count);
                }
            }

            slot.addEventListener('click', () => {
                this.inventory.selectedSlot = i;
                this.renderHotbar();
                this.renderGrid();
            });

            hotbar.appendChild(slot);
        }
    }

    renderCrafting() {
        const container = document.getElementById('crafting-recipes');
        if (!container) return;
        container.innerHTML = '';

        const recipes = this.inventory.getAvailableRecipes();
        if (recipes.length === 0) {
            container.innerHTML = '<p class="no-recipes">No hay recetas disponibles</p>';
            return;
        }

        recipes.forEach(recipe => {
            const recipeEl = document.createElement('div');
            recipeEl.className = 'recipe-item';

            const inputInfo = this.inventory.getItemInfo(parseInt(Object.keys(recipe.input)[0]));
            const outputInfo = this.inventory.getItemInfo(recipe.output.type);

            recipeEl.innerHTML = `
                <div class="recipe-input">
                    <div class="recipe-icon" style="background:#${inputInfo.color.toString(16).padStart(6, '0')}"></div>
                    <span>×${Object.values(recipe.input)[0]}</span>
                </div>
                <div class="recipe-arrow">→</div>
                <div class="recipe-output">
                    <div class="recipe-icon" style="background:#${outputInfo.color.toString(16).padStart(6, '0')}"></div>
                    <span>×${recipe.output.count}</span>
                </div>
            `;

            recipeEl.addEventListener('click', () => {
                if (this.inventory.craft(recipe)) {
                    this.renderGrid();
                    this.renderCrafting();
                    this.renderHotbar();
                    if (this.onUpdate) this.onUpdate();
                }
            });

            container.appendChild(recipeEl);
        });
    }

    onSlotClick(index) {
        if (this.selectedSlot === index) {
            this.selectedSlot = -1;
        } else if (this.selectedSlot >= 0) {
            this.inventory.swapSlots(this.selectedSlot, index);
            this.selectedSlot = -1;
        } else {
            this.selectedSlot = index;
        }
        this.renderGrid();
    }

    onDragStart(e, index) {
        e.dataTransfer.setData('text/plain', index);
    }

    onDrop(e, targetIndex) {
        e.preventDefault();
        const sourceIndex = parseInt(e.dataTransfer.getData('text/plain'));
        if (!isNaN(sourceIndex) && sourceIndex !== targetIndex) {
            this.inventory.swapSlots(sourceIndex, targetIndex);
            this.renderGrid();
            this.renderHotbar();
        }
    }

    open() {
        this.isOpen = true;
        document.getElementById('inventory-overlay').classList.remove('hidden');
        this.renderGrid();
        this.renderHotbar();
        this.renderCrafting();
    }

    close() {
        this.isOpen = false;
        document.getElementById('inventory-overlay').classList.add('hidden');
    }

    toggle() {
        if (this.isOpen) {
            this.close();
        } else {
            this.open();
        }
    }

    update() {
        this.renderGrid();
        this.renderHotbar();
        this.renderCrafting();
    }

    moveSelection(delta) {
        if (this.selectedSlot < 0) {
            this.selectedSlot = 0;
        } else {
            this.selectedSlot += delta;
            // Wrap around
            if (this.selectedSlot < 0) this.selectedSlot += 36;
            if (this.selectedSlot >= 36) this.selectedSlot -= 36;
        }
        this.renderGrid();
    }

    selectCurrent() {
        if (this.selectedSlot >= 0) {
            // Move item to hotbar if clicking from inventory
            if (this.selectedSlot >= 9) {
                // Find empty hotbar slot or swap with current
                const hotbarSlot = this.inventory.selectedSlot;
                this.inventory.swapSlots(this.selectedSlot, hotbarSlot);
            } else {
                // Select this hotbar slot
                this.inventory.selectedSlot = this.selectedSlot;
            }
            this.renderGrid();
            this.renderHotbar();
        }
    }
}

window.Inventory = Inventory;
window.InventoryUI = InventoryUI;
