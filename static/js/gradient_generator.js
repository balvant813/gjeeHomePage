/**
 * CSS Gradient Generator
 * Generates custom CSS gradients with live preview and export functionality
 */

class GradientGenerator {
    constructor() {
        this.colorStops = [
            { color: '#667eea', position: 0 },
            { color: '#764ba2', position: 100 }
        ];
        this.gradientType = 'linear';
        this.direction = 'to right';
        this.customAngle = 90;
        this.radialShape = 'circle';
        this.radialPosition = 'center';
        this.isRepeating = false;
        
        this.presets = [
            { name: 'Sunset', colors: [{ color: '#f093fb', position: 0 }, { color: '#f5576c', position: 100 }] },
            { name: 'Ocean', colors: [{ color: '#4facfe', position: 0 }, { color: '#00f2fe', position: 100 }] },
            { name: 'Forest', colors: [{ color: '#11998e', position: 0 }, { color: '#38ef7d', position: 100 }] },
            { name: 'Purple', colors: [{ color: '#667eea', position: 0 }, { color: '#764ba2', position: 100 }] },
            { name: 'Fire', colors: [{ color: '#f12711', position: 0 }, { color: '#f5af19', position: 100 }] },
            { name: 'Night', colors: [{ color: '#0f0c29', position: 0 }, { color: '#302b63', position: 50 }, { color: '#24243e', position: 100 }] },
            { name: 'Peach', colors: [{ color: '#ffecd2', position: 0 }, { color: '#fcb69f', position: 100 }] },
            { name: 'Cool', colors: [{ color: '#a1c4fd', position: 0 }, { color: '#c2e9fb', position: 100 }] },
            { name: 'Warm', colors: [{ color: '#fa709a', position: 0 }, { color: '#fee140', position: 100 }] },
            { name: 'Mint', colors: [{ color: '#84fab0', position: 0 }, { color: '#8fd3f4', position: 100 }] },
            { name: 'Berry', colors: [{ color: '#a18cd1', position: 0 }, { color: '#fbc2eb', position: 100 }] },
            { name: 'Cosmic', colors: [{ color: '#ff0844', position: 0 }, { color: '#ffb199', position: 100 }] }
        ];

        this.init();
    }

    init() {
        this.cacheElements();
        this.bindEvents();
        this.renderColorStops();
        this.renderPresets();
        this.updateGradient();
    }

    cacheElements() {
        this.preview = document.getElementById('gradient-preview');
        this.typeSelect = document.getElementById('gradient-type');
        this.directionSelect = document.getElementById('gradient-direction');
        this.angleSlider = document.getElementById('gradient-angle');
        this.angleValue = document.getElementById('angle-value');
        this.radialShapeSelect = document.getElementById('radial-shape');
        this.radialPositionSelect = document.getElementById('radial-position');
        this.repeatingCheckbox = document.getElementById('repeating-gradient');
        this.colorStopsContainer = document.getElementById('color-stops-container');
        this.addColorStopBtn = document.getElementById('add-color-stop');
        this.cssOutput = document.getElementById('css-output');
        this.copyBtn = document.getElementById('copy-css');
        this.classNameInput = document.getElementById('class-name');
        this.includePrefixesCheckbox = document.getElementById('include-prefixes');
        this.exportCssBtn = document.getElementById('export-css');
        this.exportScssBtn = document.getElementById('export-scss');
        this.presetsGrid = document.getElementById('presets-grid');
        
        // Control groups for showing/hiding
        this.directionControl = document.getElementById('direction-control');
        this.angleControl = document.getElementById('angle-control');
        this.radialShapeControl = document.getElementById('radial-shape-control');
        this.radialPositionControl = document.getElementById('radial-position-control');
    }

    bindEvents() {
        // Gradient type change
        this.typeSelect.addEventListener('change', (e) => {
            this.gradientType = e.target.value;
            this.updateControlsVisibility();
            this.updateGradient();
        });

        // Direction change
        this.directionSelect.addEventListener('change', (e) => {
            this.direction = e.target.value;
            if (this.direction === 'custom') {
                this.angleControl.style.display = 'block';
            } else {
                this.angleControl.style.display = 'none';
            }
            this.updateGradient();
        });

        // Angle slider
        this.angleSlider.addEventListener('input', (e) => {
            this.customAngle = parseInt(e.target.value);
            this.angleValue.textContent = `${this.customAngle}°`;
            this.updateGradient();
        });

        // Radial shape
        this.radialShapeSelect.addEventListener('change', (e) => {
            this.radialShape = e.target.value;
            this.updateGradient();
        });

        // Radial position
        this.radialPositionSelect.addEventListener('change', (e) => {
            this.radialPosition = e.target.value;
            this.updateGradient();
        });

        // Repeating gradient
        this.repeatingCheckbox.addEventListener('change', (e) => {
            this.isRepeating = e.target.checked;
            this.updateGradient();
        });

        // Add color stop
        this.addColorStopBtn.addEventListener('click', () => {
            this.addColorStop();
        });

        // Copy CSS
        this.copyBtn.addEventListener('click', () => {
            this.copyToClipboard();
        });

        // Export buttons
        this.exportCssBtn.addEventListener('click', () => {
            this.exportCSS();
        });

        this.exportScssBtn.addEventListener('click', () => {
            this.exportSCSS();
        });
    }

    updateControlsVisibility() {
        // Hide all type-specific controls first
        this.directionControl.style.display = 'none';
        this.angleControl.style.display = 'none';
        this.radialShapeControl.style.display = 'none';
        this.radialPositionControl.style.display = 'none';

        switch (this.gradientType) {
            case 'linear':
                this.directionControl.style.display = 'block';
                if (this.direction === 'custom') {
                    this.angleControl.style.display = 'block';
                }
                break;
            case 'radial':
                this.radialShapeControl.style.display = 'block';
                this.radialPositionControl.style.display = 'block';
                break;
            case 'conic':
                this.radialPositionControl.style.display = 'block';
                break;
        }
    }

    renderColorStops() {
        this.colorStopsContainer.innerHTML = '';
        
        this.colorStops.forEach((stop, index) => {
            const stopElement = document.createElement('div');
            stopElement.className = 'color-stop';
            stopElement.dataset.index = index;
            
            stopElement.innerHTML = `
                <input type="color" class="color-picker" value="${stop.color}" title="Select color" aria-label="Color picker">
                <input type="number" class="stop-position" min="0" max="100" value="${stop.position}" placeholder="%">
                <span class="position-label">%</span>
                <button class="remove-stop" title="Remove color stop">×</button>
            `;

            // Bind events for this color stop
            const colorPicker = stopElement.querySelector('.color-picker');
            const positionInput = stopElement.querySelector('.stop-position');
            const removeBtn = stopElement.querySelector('.remove-stop');

            colorPicker.addEventListener('input', (e) => {
                this.colorStops[index].color = e.target.value;
                this.updateGradient();
            });

            positionInput.addEventListener('input', (e) => {
                let value = parseInt(e.target.value) || 0;
                value = Math.max(0, Math.min(100, value));
                this.colorStops[index].position = value;
                this.updateGradient();
            });

            removeBtn.addEventListener('click', () => {
                this.removeColorStop(index);
            });

            this.colorStopsContainer.appendChild(stopElement);
        });
    }

    addColorStop() {
        // Calculate a position between existing stops
        const lastPosition = this.colorStops[this.colorStops.length - 1]?.position || 0;
        const newPosition = Math.min(100, lastPosition + 10);
        
        // Generate a random color or interpolate
        const randomColor = this.generateRandomColor();
        
        this.colorStops.push({
            color: randomColor,
            position: newPosition
        });

        this.renderColorStops();
        this.updateGradient();
    }

    removeColorStop(index) {
        if (this.colorStops.length <= 2) {
            this.showToast('Minimum 2 color stops required', 'error');
            return;
        }
        
        this.colorStops.splice(index, 1);
        this.renderColorStops();
        this.updateGradient();
    }

    generateRandomColor() {
        const letters = '0123456789ABCDEF';
        let color = '#';
        for (let i = 0; i < 6; i++) {
            color += letters[Math.floor(Math.random() * 16)];
        }
        return color;
    }

    buildGradientString(includeBackground = false) {
        // Sort color stops by position
        const sortedStops = [...this.colorStops].sort((a, b) => a.position - b.position);
        
        // Build color stops string
        const stopsString = sortedStops
            .map(stop => `${stop.color} ${stop.position}%`)
            .join(', ');

        let gradientFunction = '';
        const prefix = this.isRepeating ? 'repeating-' : '';

        switch (this.gradientType) {
            case 'linear':
                const direction = this.direction === 'custom' 
                    ? `${this.customAngle}deg` 
                    : this.direction;
                gradientFunction = `${prefix}linear-gradient(${direction}, ${stopsString})`;
                break;
            case 'radial':
                gradientFunction = `${prefix}radial-gradient(${this.radialShape} at ${this.radialPosition}, ${stopsString})`;
                break;
            case 'conic':
                gradientFunction = `${prefix}conic-gradient(from 0deg at ${this.radialPosition}, ${stopsString})`;
                break;
        }

        if (includeBackground) {
            return `background: ${gradientFunction};`;
        }
        
        return gradientFunction;
    }

    updateGradient() {
        const gradient = this.buildGradientString();
        this.preview.style.background = gradient;
        this.updateCSSOutput();
    }

    updateCSSOutput() {
        const className = this.classNameInput.value || 'gradient-bg';
        const gradient = this.buildGradientString();
        const includePrefixes = this.includePrefixesCheckbox.checked;

        let css = `.${className} {\n`;
        
        if (includePrefixes) {
            // Add vendor prefixes
            css += `  background: -webkit-${gradient};\n`;
            css += `  background: -moz-${gradient};\n`;
            css += `  background: -o-${gradient};\n`;
        }
        
        css += `  background: ${gradient};\n`;
        css += `}`;

        this.cssOutput.textContent = css;
    }

    copyToClipboard() {
        const text = this.cssOutput.textContent;
        
        navigator.clipboard.writeText(text).then(() => {
            this.showToast('CSS copied to clipboard!', 'success');
        }).catch(() => {
            // Fallback for older browsers
            const textarea = document.createElement('textarea');
            textarea.value = text;
            document.body.appendChild(textarea);
            textarea.select();
            document.execCommand('copy');
            document.body.removeChild(textarea);
            this.showToast('CSS copied to clipboard!', 'success');
        });
    }

    exportCSS() {
        const className = this.classNameInput.value || 'gradient-bg';
        const gradient = this.buildGradientString();
        const includePrefixes = this.includePrefixesCheckbox.checked;

        let css = `/* Generated by CSS Gradient Generator */\n`;
        css += `/* ${new Date().toISOString()} */\n\n`;
        css += `.${className} {\n`;
        
        if (includePrefixes) {
            css += `  background: -webkit-${gradient};\n`;
            css += `  background: -moz-${gradient};\n`;
            css += `  background: -o-${gradient};\n`;
        }
        
        css += `  background: ${gradient};\n`;
        css += `}\n`;

        this.downloadFile(`${className}.css`, css, 'text/css');
        this.showToast('CSS file downloaded!', 'success');
    }

    exportSCSS() {
        const className = this.classNameInput.value || 'gradient-bg';
        const gradient = this.buildGradientString();
        const includePrefixes = this.includePrefixesCheckbox.checked;

        // Extract colors for SCSS variables
        const sortedStops = [...this.colorStops].sort((a, b) => a.position - b.position);
        
        let scss = `// Generated by CSS Gradient Generator\n`;
        scss += `// ${new Date().toISOString()}\n\n`;
        scss += `// Color Variables\n`;
        
        sortedStops.forEach((stop, index) => {
            scss += `$gradient-color-${index + 1}: ${stop.color};\n`;
        });
        
        scss += `\n// Gradient Mixin\n`;
        scss += `@mixin ${className}() {\n`;
        
        if (includePrefixes) {
            scss += `  background: -webkit-${gradient};\n`;
            scss += `  background: -moz-${gradient};\n`;
            scss += `  background: -o-${gradient};\n`;
        }
        
        scss += `  background: ${gradient};\n`;
        scss += `}\n\n`;
        
        scss += `// Usage\n`;
        scss += `.${className} {\n`;
        scss += `  @include ${className}();\n`;
        scss += `}\n`;

        this.downloadFile(`_${className}.scss`, scss, 'text/x-scss');
        this.showToast('SCSS file downloaded!', 'success');
    }

    downloadFile(filename, content, mimeType) {
        const blob = new Blob([content], { type: mimeType });
        const url = URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.download = filename;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        URL.revokeObjectURL(url);
    }

    renderPresets() {
        this.presetsGrid.innerHTML = '';
        
        this.presets.forEach((preset, index) => {
            const presetElement = document.createElement('div');
            presetElement.className = 'preset-item';
            presetElement.title = preset.name;
            
            // Build gradient for preset
            const stopsString = preset.colors
                .map(stop => `${stop.color} ${stop.position}%`)
                .join(', ');
            presetElement.style.background = `linear-gradient(to right, ${stopsString})`;
            
            presetElement.addEventListener('click', () => {
                this.applyPreset(index);
            });
            
            this.presetsGrid.appendChild(presetElement);
        });
    }

    applyPreset(index) {
        const preset = this.presets[index];
        this.colorStops = JSON.parse(JSON.stringify(preset.colors));
        this.renderColorStops();
        this.updateGradient();
        
        // Update active state
        document.querySelectorAll('.preset-item').forEach((item, i) => {
            item.classList.toggle('active', i === index);
        });
        
        this.showToast(`Applied "${preset.name}" preset`, 'success');
    }

    showToast(message, type = 'success') {
        // Remove existing toast
        const existingToast = document.querySelector('.toast');
        if (existingToast) {
            existingToast.remove();
        }

        const toast = document.createElement('div');
        toast.className = `toast ${type}`;
        toast.textContent = message;
        document.body.appendChild(toast);

        // Trigger animation
        setTimeout(() => toast.classList.add('show'), 10);

        // Remove after delay
        setTimeout(() => {
            toast.classList.remove('show');
            setTimeout(() => toast.remove(), 300);
        }, 3000);
    }
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    window.gradientGenerator = new GradientGenerator();
});
