/**
 * Text Editor - Manages text formatting controls
 */
class TextEditor {
    constructor(canvasManager) {
        this.canvasManager = canvasManager;
        this.activeText = null;
        this.activeLine = null;

        this._bindElements();
        this._bindEvents();
    }

    _bindElements() {
        // Text controls
        this.textEditor = document.getElementById('text-editor');
        this.textContent = document.getElementById('text-content');
        this.fontFamily = document.getElementById('font-family');
        this.fontSize = document.getElementById('font-size');
        this.textColor = document.getElementById('text-color');
        this.btnBold = document.getElementById('btn-bold');
        this.btnItalic = document.getElementById('btn-italic');
        this.btnUnderline = document.getElementById('btn-underline');
        this.btnDeleteText = document.getElementById('btn-delete-text');

        // Alignment controls
        this.btnAlignLeft = document.getElementById('btn-align-left');
        this.btnAlignCenter = document.getElementById('btn-align-center');
        this.btnAlignRight = document.getElementById('btn-align-right');

        // Line controls
        this.lineEditor = document.getElementById('line-editor');
        this.lineColor = document.getElementById('line-color');
        this.lineWidth = document.getElementById('line-width');
        this.btnDeleteLine = document.getElementById('btn-delete-line');
    }

    _bindEvents() {
        // Canvas selection events
        window.addEventListener('textSelected', (e) => this._onTextSelected(e.detail));
        window.addEventListener('lineSelected', (e) => this._onLineSelected(e.detail));
        window.addEventListener('selectionCleared', () => this._onSelectionCleared());

        // Text controls
        this.textContent.addEventListener('input', () => this._updateText());
        this.fontFamily.addEventListener('change', () => this._updateStyle('fontFamily', this.fontFamily.value));
        this.fontSize.addEventListener('input', () => this._updateStyle('fontSize', parseInt(this.fontSize.value)));
        this.textColor.addEventListener('input', () => this._updateStyle('fill', this.textColor.value));

        this.btnBold.addEventListener('click', () => this._toggleFormat('bold'));
        this.btnItalic.addEventListener('click', () => this._toggleFormat('italic'));
        this.btnUnderline.addEventListener('click', () => this._toggleFormat('underline'));
        this.btnDeleteText.addEventListener('click', () => this._deleteSelected());

        // Alignment controls
        if (this.btnAlignLeft) {
            this.btnAlignLeft.addEventListener('click', () => this._setAlignment('left'));
        }
        if (this.btnAlignCenter) {
            this.btnAlignCenter.addEventListener('click', () => this._setAlignment('center'));
        }
        if (this.btnAlignRight) {
            this.btnAlignRight.addEventListener('click', () => this._setAlignment('right'));
        }

        // Line controls
        this.lineColor.addEventListener('input', () => this._updateLineStyle('stroke', this.lineColor.value));
        this.lineWidth.addEventListener('input', () => this._updateLineStyle('strokeWidth', parseInt(this.lineWidth.value)));
        this.btnDeleteLine.addEventListener('click', () => this._deleteSelected());

        // Update on canvas object modification
        this.canvasManager.canvas.on('text:changed', (e) => {
            if (e.target === this.activeText) {
                this.textContent.value = e.target.text;
            }
        });
    }

    _onTextSelected(textObj) {
        this.activeText = textObj;
        this.activeLine = null;

        // Show text editor, hide line editor
        this.textEditor.style.display = 'block';
        this.lineEditor.style.display = 'none';

        // Populate controls with current values
        this.textContent.value = textObj.text;
        this.fontFamily.value = textObj.fontFamily;
        this.fontSize.value = textObj.fontSize;
        this.textColor.value = textObj.fill;

        // Update format buttons
        this._updateFormatButtons();
        this._updateAlignmentButtons();
    }

    _onLineSelected(lineObj) {
        this.activeLine = lineObj;
        this.activeText = null;

        // Show line editor, hide text editor
        this.lineEditor.style.display = 'block';
        this.textEditor.style.display = 'none';

        // Populate controls
        this.lineColor.value = lineObj.stroke;
        this.lineWidth.value = lineObj.strokeWidth;
    }

    _onSelectionCleared() {
        this.activeText = null;
        this.activeLine = null;
        this.textEditor.style.display = 'none';
        this.lineEditor.style.display = 'none';
    }

    _updateText() {
        if (!this.activeText) return;
        this.activeText.set('text', this.textContent.value);
        this.canvasManager.canvas.renderAll();
    }

    _updateStyle(property, value) {
        if (!this.activeText) return;
        this.activeText.set(property, value);
        this.canvasManager.canvas.renderAll();
    }

    _updateLineStyle(property, value) {
        if (!this.activeLine) return;
        this.activeLine.set(property, value);
        this.canvasManager.canvas.renderAll();
    }

    _toggleFormat(format) {
        if (!this.activeText) return;

        let property, activeValue, inactiveValue;

        switch (format) {
            case 'bold':
                property = 'fontWeight';
                activeValue = 'bold';
                inactiveValue = 'normal';
                break;
            case 'italic':
                property = 'fontStyle';
                activeValue = 'italic';
                inactiveValue = 'normal';
                break;
            case 'underline':
                property = 'underline';
                activeValue = true;
                inactiveValue = false;
                break;
        }

        const currentValue = this.activeText.get(property);
        const newValue = currentValue === activeValue ? inactiveValue : activeValue;
        this.activeText.set(property, newValue);
        this.canvasManager.canvas.renderAll();
        this._updateFormatButtons();
    }

    _updateFormatButtons() {
        if (!this.activeText) return;

        this.btnBold.classList.toggle('active', this.activeText.fontWeight === 'bold');
        this.btnItalic.classList.toggle('active', this.activeText.fontStyle === 'italic');
        this.btnUnderline.classList.toggle('active', this.activeText.underline === true);
    }

    _deleteSelected() {
        this.canvasManager.deleteSelected();
        this._onSelectionCleared();
    }

    _setAlignment(align) {
        if (!this.activeText) return;
        this.activeText.set('textAlign', align);
        this.canvasManager.canvas.renderAll();
        this._updateAlignmentButtons();
    }

    _updateAlignmentButtons() {
        if (!this.activeText) return;
        const align = this.activeText.textAlign || 'center';
        this.btnAlignLeft.classList.toggle('active', align === 'left');
        this.btnAlignCenter.classList.toggle('active', align === 'center');
        this.btnAlignRight.classList.toggle('active', align === 'right');
    }
}
