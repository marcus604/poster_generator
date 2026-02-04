/**
 * Canvas Manager - Handles Fabric.js canvas for poster composition
 * Uses overlay-based selection: full frame displayed with draggable 2:3 selection overlay
 */
class CanvasManager {
    constructor(canvasId) {
        this.canvasId = canvasId;

        // Canvas dimensions for different modes
        this.imageModeWidth = 800;
        this.imageModeHeight = 500;
        this.posterModeWidth = 400;   // 2:3 aspect ratio for color/gradient
        this.posterModeHeight = 600;

        // Current canvas dimensions
        this.canvasWidth = this.imageModeWidth;
        this.canvasHeight = this.imageModeHeight;

        // Poster output dimensions (2:3 aspect ratio)
        this.posterWidth = 1000;
        this.posterHeight = 1500;

        // Selection overlay dimensions (2:3 aspect ratio, resizable via zoom)
        this.baseOverlayHeight = 400;  // Base height at 100% zoom
        this.baseOverlayWidth = this.baseOverlayHeight * (2/3);  // ~267
        this.overlayZoom = 1.0;

        this.canvas = new fabric.Canvas(canvasId, {
            width: this.canvasWidth,
            height: this.canvasHeight,
            backgroundColor: '#1a1a2e',
            selection: true,
            preserveObjectStacking: true
        });

        // Frame and overlay elements
        this.frameImage = null;
        this.selectionOverlay = null;
        this.darkMaskRects = [];
        this.frameDisplayInfo = null;  // Tracks frame position/scale in canvas

        // Background settings
        this.backgroundMode = 'image';
        this.backgroundColor = '#000000';
        this.gradientColors = ['#000000', '#333333'];
        this.gradientDirection = 'vertical';
        this.blurAmount = 0;

        // Two-phase workflow
        this.workflowPhase = 'background';  // 'background' | 'elements'
        this.lockedBackgroundData = null;   // Stores rendered background for elements phase

        // Video info
        this.videoBase = null;
        this.videoPath = null;
        this.currentTimestamp = 0;

        this._bindEvents();
    }

    _bindEvents() {
        // Track selection changes for text/line editing
        this.canvas.on('selection:created', (e) => this._onSelectionChange(e));
        this.canvas.on('selection:updated', (e) => this._onSelectionChange(e));
        this.canvas.on('selection:cleared', () => this._onSelectionCleared());

        // Track object modifications
        this.canvas.on('object:modified', () => this._onObjectModified());

        // Update dark mask when overlay moves
        this.canvas.on('object:moving', (e) => {
            if (e.target === this.selectionOverlay) {
                this._constrainOverlay();
                this._updateDarkMask();
            }
        });

        this.canvas.on('object:moved', (e) => {
            if (e.target === this.selectionOverlay) {
                this._constrainOverlay();
                this._updateDarkMask();
            }
        });
    }

    _onSelectionChange(e) {
        const obj = e.selected[0];
        // Support both IText and Textbox types
        if (obj && (obj.type === 'i-text' || obj.type === 'textbox')) {
            window.dispatchEvent(new CustomEvent('textSelected', { detail: obj }));
        } else if (obj && obj.type === 'line') {
            window.dispatchEvent(new CustomEvent('lineSelected', { detail: obj }));
        }
    }

    _onSelectionCleared() {
        window.dispatchEvent(new CustomEvent('selectionCleared'));
    }

    _onObjectModified() {
        window.dispatchEvent(new CustomEvent('canvasModified'));
    }

    setVideo(base, path) {
        this.videoBase = base;
        this.videoPath = path;
    }

    async setFrame(timestamp) {
        if (!this.videoBase || !this.videoPath) return;

        this.currentTimestamp = timestamp;

        if (this.backgroundMode !== 'image') return;

        const frameUrl = api.getPreviewFrameUrl(this.videoBase, this.videoPath, timestamp);

        return new Promise((resolve) => {
            fabric.Image.fromURL(frameUrl, (img) => {
                if (this.frameImage) {
                    this.canvas.remove(this.frameImage);
                }

                // Display full frame maintaining aspect ratio (fit within canvas)
                const frameAspect = img.width / img.height;
                const canvasAspect = this.canvasWidth / this.canvasHeight;

                let displayWidth, displayHeight;
                if (frameAspect > canvasAspect) {
                    // Frame is wider - fit to width
                    displayWidth = this.canvasWidth;
                    displayHeight = this.canvasWidth / frameAspect;
                } else {
                    // Frame is taller - fit to height
                    displayHeight = this.canvasHeight;
                    displayWidth = this.canvasHeight * frameAspect;
                }

                const scale = displayWidth / img.width;

                img.set({
                    scaleX: scale,
                    scaleY: scale,
                    originX: 'center',
                    originY: 'center',
                    left: this.canvasWidth / 2,
                    top: this.canvasHeight / 2,
                    selectable: false,
                    evented: false
                });

                // Store frame display info for coordinate calculations
                this.frameDisplayInfo = {
                    displayWidth,
                    displayHeight,
                    displayLeft: (this.canvasWidth - displayWidth) / 2,
                    displayTop: (this.canvasHeight - displayHeight) / 2,
                    originalWidth: img.width,
                    originalHeight: img.height,
                    scale
                };

                this.frameImage = img;
                this._applyBlurFilter();
                this.canvas.add(img);
                this.canvas.sendToBack(img);

                // Create or update selection overlay and dark mask
                this._createSelectionOverlay();
                this._createDarkMask();

                this.canvas.renderAll();
                resolve();
            }, { crossOrigin: 'anonymous' });
        });
    }

    _createSelectionOverlay() {
        // Remove existing overlay
        if (this.selectionOverlay) {
            this.canvas.remove(this.selectionOverlay);
        }

        // Calculate overlay dimensions based on zoom
        const overlayHeight = this.baseOverlayHeight * this.overlayZoom;
        const overlayWidth = overlayHeight * (2/3);

        // Center the overlay initially
        const overlayLeft = (this.canvasWidth - overlayWidth) / 2;
        const overlayTop = (this.canvasHeight - overlayHeight) / 2;

        // Create selection rectangle with visible border
        this.selectionOverlay = new fabric.Rect({
            left: overlayLeft,
            top: overlayTop,
            width: overlayWidth,
            height: overlayHeight,
            fill: 'transparent',
            stroke: '#e94560',
            strokeWidth: 3,
            strokeDashArray: [8, 4],
            selectable: true,
            hasControls: false,  // No resize handles - use zoom slider
            hasBorders: false,
            lockRotation: true,
            lockScalingX: true,
            lockScalingY: true,
            hoverCursor: 'move',
            moveCursor: 'move'
        });

        // Mark as overlay so we don't export it
        this.selectionOverlay.isOverlay = true;

        this.canvas.add(this.selectionOverlay);
    }

    _createDarkMask() {
        // Remove existing mask rectangles
        this.darkMaskRects.forEach(rect => this.canvas.remove(rect));
        this.darkMaskRects = [];

        if (!this.selectionOverlay) return;

        const overlay = this.selectionOverlay;
        const maskColor = 'rgba(0, 0, 0, 0.6)';

        // Top rectangle (full width, above overlay)
        const topRect = new fabric.Rect({
            left: 0,
            top: 0,
            width: this.canvasWidth,
            height: overlay.top,
            fill: maskColor,
            selectable: false,
            evented: false
        });

        // Bottom rectangle (full width, below overlay)
        const bottomRect = new fabric.Rect({
            left: 0,
            top: overlay.top + overlay.height,
            width: this.canvasWidth,
            height: this.canvasHeight - (overlay.top + overlay.height),
            fill: maskColor,
            selectable: false,
            evented: false
        });

        // Left rectangle (between top and bottom, left of overlay)
        const leftRect = new fabric.Rect({
            left: 0,
            top: overlay.top,
            width: overlay.left,
            height: overlay.height,
            fill: maskColor,
            selectable: false,
            evented: false
        });

        // Right rectangle (between top and bottom, right of overlay)
        const rightRect = new fabric.Rect({
            left: overlay.left + overlay.width,
            top: overlay.top,
            width: this.canvasWidth - (overlay.left + overlay.width),
            height: overlay.height,
            fill: maskColor,
            selectable: false,
            evented: false
        });

        this.darkMaskRects = [topRect, bottomRect, leftRect, rightRect];

        // Add mask rectangles (above frame, below overlay)
        this.darkMaskRects.forEach(rect => {
            rect.isMask = true;  // Mark as mask
            this.canvas.add(rect);
        });

        // Ensure proper z-order: frame -> mask -> overlay -> text/lines
        this._reorderObjects();
    }

    _updateDarkMask() {
        if (!this.selectionOverlay || this.darkMaskRects.length !== 4) return;

        const overlay = this.selectionOverlay;
        const [topRect, bottomRect, leftRect, rightRect] = this.darkMaskRects;

        // Update top
        topRect.set({ height: Math.max(0, overlay.top) });

        // Update bottom
        bottomRect.set({
            top: overlay.top + overlay.height,
            height: Math.max(0, this.canvasHeight - (overlay.top + overlay.height))
        });

        // Update left
        leftRect.set({
            top: overlay.top,
            width: Math.max(0, overlay.left),
            height: overlay.height
        });

        // Update right
        rightRect.set({
            left: overlay.left + overlay.width,
            top: overlay.top,
            width: Math.max(0, this.canvasWidth - (overlay.left + overlay.width)),
            height: overlay.height
        });

        this.canvas.renderAll();
    }

    _constrainOverlay() {
        if (!this.selectionOverlay || !this.frameDisplayInfo) return;

        const overlay = this.selectionOverlay;
        const frame = this.frameDisplayInfo;

        // Constrain overlay to stay within the frame bounds
        let newLeft = overlay.left;
        let newTop = overlay.top;

        // Left boundary
        if (newLeft < frame.displayLeft) {
            newLeft = frame.displayLeft;
        }
        // Right boundary
        if (newLeft + overlay.width > frame.displayLeft + frame.displayWidth) {
            newLeft = frame.displayLeft + frame.displayWidth - overlay.width;
        }
        // Top boundary
        if (newTop < frame.displayTop) {
            newTop = frame.displayTop;
        }
        // Bottom boundary
        if (newTop + overlay.height > frame.displayTop + frame.displayHeight) {
            newTop = frame.displayTop + frame.displayHeight - overlay.height;
        }

        overlay.set({ left: newLeft, top: newTop });
    }

    _reorderObjects() {
        // Ensure z-order: frame (back) -> mask -> overlay -> text/lines (front)
        if (this.frameImage) {
            this.canvas.sendToBack(this.frameImage);
        }

        // Move mask above frame
        this.darkMaskRects.forEach(rect => {
            this.canvas.bringToFront(rect);
        });

        // Move overlay above mask
        if (this.selectionOverlay) {
            this.canvas.bringToFront(this.selectionOverlay);
        }

        // Move text/lines to front
        this.canvas.getObjects().forEach(obj => {
            if (obj.type === 'i-text' || obj.type === 'line') {
                this.canvas.bringToFront(obj);
            }
        });
    }

    setZoom(zoomLevel) {
        // Zoom now controls overlay size (50% to 150% of base)
        this.overlayZoom = Math.max(0.5, Math.min(1.5, zoomLevel / 100));

        if (this.selectionOverlay && this.frameDisplayInfo) {
            const oldCenterX = this.selectionOverlay.left + this.selectionOverlay.width / 2;
            const oldCenterY = this.selectionOverlay.top + this.selectionOverlay.height / 2;

            // Calculate new dimensions
            const newHeight = this.baseOverlayHeight * this.overlayZoom;
            const newWidth = newHeight * (2/3);

            // Keep centered on same point
            let newLeft = oldCenterX - newWidth / 2;
            let newTop = oldCenterY - newHeight / 2;

            this.selectionOverlay.set({
                width: newWidth,
                height: newHeight,
                left: newLeft,
                top: newTop
            });

            this._constrainOverlay();
            this._updateDarkMask();
            this.canvas.renderAll();
        }
    }

    resetOverlayPosition() {
        if (this.selectionOverlay) {
            const overlayWidth = this.selectionOverlay.width;
            const overlayHeight = this.selectionOverlay.height;

            this.selectionOverlay.set({
                left: (this.canvasWidth - overlayWidth) / 2,
                top: (this.canvasHeight - overlayHeight) / 2
            });

            this._constrainOverlay();
            this._updateDarkMask();
            this.canvas.renderAll();
        }
    }

    /**
     * Confirm background selection and switch to elements phase
     * Captures the current background and displays it on a poster-sized canvas
     */
    async confirmBackground() {
        if (this.workflowPhase === 'elements') return;

        // Store the current selection coordinates for export
        this.lockedBackgroundData = {
            mode: this.backgroundMode,
            selectionCoords: this._getSelectionCoords(),
            blur: this.blurAmount,
            backgroundColor: this.backgroundColor,
            gradientColors: [...this.gradientColors],
            gradientDirection: this.gradientDirection,
            videoBase: this.videoBase,
            videoPath: this.videoPath,
            timestamp: this.currentTimestamp
        };

        // For image mode, capture the cropped selection as a data URL
        if (this.backgroundMode === 'image' && this.frameImage && this.selectionOverlay) {
            const capturedImage = await this._captureSelectionAsImage();
            this.lockedBackgroundData.capturedImageUrl = capturedImage;
        }

        // Clear overlay and mask
        if (this.selectionOverlay) {
            this.canvas.remove(this.selectionOverlay);
            this.selectionOverlay = null;
        }
        this.darkMaskRects.forEach(rect => this.canvas.remove(rect));
        this.darkMaskRects = [];

        // Remove the frame image
        if (this.frameImage) {
            this.canvas.remove(this.frameImage);
            this.frameImage = null;
        }
        this.frameDisplayInfo = null;

        // Switch canvas to poster dimensions
        this._resizeCanvas(this.posterModeWidth, this.posterModeHeight);

        // Set the background based on mode
        if (this.backgroundMode === 'image' && this.lockedBackgroundData.capturedImageUrl) {
            // Load the captured image as background
            await this._setImageBackground(this.lockedBackgroundData.capturedImageUrl);
        } else if (this.backgroundMode === 'color') {
            this.canvas.setBackgroundColor(this.backgroundColor, () => {
                this.canvas.renderAll();
            });
        } else if (this.backgroundMode === 'gradient') {
            this._applyGradient();
        }

        this.workflowPhase = 'elements';
        this.canvas.renderAll();
    }

    /**
     * Capture the current selection overlay area as an image
     */
    async _captureSelectionAsImage() {
        return new Promise((resolve) => {
            if (!this.frameImage || !this.selectionOverlay || !this.frameDisplayInfo) {
                resolve(null);
                return;
            }

            // Create a temporary canvas to render the cropped area
            const tempCanvas = document.createElement('canvas');
            tempCanvas.width = this.posterModeWidth;
            tempCanvas.height = this.posterModeHeight;
            const ctx = tempCanvas.getContext('2d');

            // Get the original image element from fabric
            const imgElement = this.frameImage._element;
            if (!imgElement) {
                resolve(null);
                return;
            }

            // Calculate crop coordinates in original image space
            const frame = this.frameDisplayInfo;
            const overlay = this.selectionOverlay;

            // Convert overlay position from canvas space to original image space
            const cropX = ((overlay.left - frame.displayLeft) / frame.displayWidth) * frame.originalWidth;
            const cropY = ((overlay.top - frame.displayTop) / frame.displayHeight) * frame.originalHeight;
            const cropW = (overlay.width / frame.displayWidth) * frame.originalWidth;
            const cropH = (overlay.height / frame.displayHeight) * frame.originalHeight;

            // Draw the cropped region scaled to poster size
            ctx.drawImage(
                imgElement,
                cropX, cropY, cropW, cropH,  // Source rectangle
                0, 0, this.posterModeWidth, this.posterModeHeight  // Destination rectangle
            );

            // Apply blur if needed (simple approximation using CSS filter via another canvas)
            if (this.blurAmount > 0) {
                ctx.filter = `blur(${this.blurAmount / 2}px)`;
                ctx.drawImage(tempCanvas, 0, 0);
                ctx.filter = 'none';
            }

            resolve(tempCanvas.toDataURL('image/jpeg', 0.9));
        });
    }

    /**
     * Set an image as the canvas background
     */
    async _setImageBackground(imageUrl) {
        return new Promise((resolve) => {
            fabric.Image.fromURL(imageUrl, (img) => {
                img.set({
                    scaleX: this.posterModeWidth / img.width,
                    scaleY: this.posterModeHeight / img.height,
                    originX: 'left',
                    originY: 'top',
                    left: 0,
                    top: 0,
                    selectable: false,
                    evented: false
                });

                this.frameImage = img;
                this.canvas.add(img);
                this.canvas.sendToBack(img);
                this.canvas.renderAll();
                resolve();
            }, { crossOrigin: 'anonymous' });
        });
    }

    /**
     * Reset to background selection phase
     * Clears all text/line elements and restores the background selection UI
     */
    resetToBackgroundPhase() {
        if (this.workflowPhase === 'background') return;

        // Clear all text and line objects (including textbox type)
        const objectsToRemove = this.canvas.getObjects().filter(obj =>
            obj.type === 'i-text' || obj.type === 'textbox' || obj.type === 'line'
        );
        objectsToRemove.forEach(obj => this.canvas.remove(obj));

        // Clear the background image if in elements phase
        if (this.frameImage) {
            this.canvas.remove(this.frameImage);
            this.frameImage = null;
        }

        // Reset canvas background
        this.canvas.setBackgroundColor('#1a1a2e', () => {});

        // Restore appropriate canvas size and reload frame if needed
        if (this.backgroundMode === 'image') {
            this._resizeCanvas(this.imageModeWidth, this.imageModeHeight);
            // Reload the frame with selection overlay
            if (this.videoBase && this.videoPath) {
                this.setFrame(this.currentTimestamp);
            }
        } else if (this.backgroundMode === 'color') {
            this._resizeCanvas(this.posterModeWidth, this.posterModeHeight);
            this.canvas.setBackgroundColor(this.backgroundColor, () => {
                this.canvas.renderAll();
            });
        } else if (this.backgroundMode === 'gradient') {
            this._resizeCanvas(this.posterModeWidth, this.posterModeHeight);
            this._applyGradient();
        }

        this.workflowPhase = 'background';
        this.lockedBackgroundData = null;
        this.canvas.renderAll();
    }

    setBlur(amount) {
        this.blurAmount = amount;
        if (this.backgroundMode === 'image' && this.frameImage) {
            this._applyBlurFilter();
        }
    }

    _applyBlurFilter() {
        if (!this.frameImage) return;

        if (this.blurAmount > 0) {
            const blurFilter = new fabric.Image.filters.Blur({
                blur: this.blurAmount / 50
            });
            this.frameImage.filters = [blurFilter];
        } else {
            this.frameImage.filters = [];
        }
        this.frameImage.applyFilters();
        this.canvas.renderAll();
    }

    setBackgroundMode(mode) {
        this.backgroundMode = mode;
        this._updateBackground();
    }

    setBackgroundColor(color) {
        this.backgroundColor = color;
        if (this.backgroundMode === 'color') {
            this._updateBackground();
        }
    }

    setGradientColors(color1, color2) {
        this.gradientColors = [color1, color2];
        if (this.backgroundMode === 'gradient') {
            this._updateBackground();
        }
    }

    setGradientDirection(direction) {
        this.gradientDirection = direction;
        if (this.backgroundMode === 'gradient') {
            this._updateBackground();
        }
    }

    _updateBackground() {
        // Remove frame, overlay, and mask if switching away from image mode
        if (this.backgroundMode !== 'image') {
            if (this.frameImage) {
                this.canvas.remove(this.frameImage);
                this.frameImage = null;
            }
            if (this.selectionOverlay) {
                this.canvas.remove(this.selectionOverlay);
                this.selectionOverlay = null;
            }
            this.darkMaskRects.forEach(rect => this.canvas.remove(rect));
            this.darkMaskRects = [];
            this.frameDisplayInfo = null;
        }

        // Resize canvas based on mode
        if (this.backgroundMode === 'image') {
            this._resizeCanvas(this.imageModeWidth, this.imageModeHeight);
        } else {
            this._resizeCanvas(this.posterModeWidth, this.posterModeHeight);
        }

        if (this.backgroundMode === 'color') {
            this.canvas.setBackgroundColor(this.backgroundColor, () => {
                this.canvas.renderAll();
            });
        } else if (this.backgroundMode === 'gradient') {
            this._applyGradient();
        } else if (this.backgroundMode === 'image') {
            this.canvas.setBackgroundColor('#1a1a2e', () => {
                this.setFrame(this.currentTimestamp);
            });
        }
    }

    _resizeCanvas(width, height) {
        if (this.canvasWidth === width && this.canvasHeight === height) return;

        this.canvasWidth = width;
        this.canvasHeight = height;
        this.canvas.setWidth(width);
        this.canvas.setHeight(height);
        this.canvas.renderAll();
    }

    _applyGradient() {
        // Canvas is now in poster aspect ratio (2:3) for gradient mode
        let coords;
        switch (this.gradientDirection) {
            case 'horizontal':
                coords = { x1: 0, y1: 0, x2: this.canvasWidth, y2: 0 };
                break;
            case 'diagonal':
                coords = { x1: 0, y1: 0, x2: this.canvasWidth, y2: this.canvasHeight };
                break;
            default: // vertical
                coords = { x1: 0, y1: 0, x2: 0, y2: this.canvasHeight };
        }

        const gradient = new fabric.Gradient({
            type: 'linear',
            coords: coords,
            colorStops: [
                { offset: 0, color: this.gradientColors[0] },
                { offset: 1, color: this.gradientColors[1] }
            ]
        });

        this.canvas.setBackgroundColor(gradient, () => {
            this.canvas.renderAll();
        });
    }

    // Get the effective poster area dimensions and position
    _getPosterArea() {
        if (this.backgroundMode === 'image' && this.selectionOverlay) {
            return {
                left: this.selectionOverlay.left,
                top: this.selectionOverlay.top,
                width: this.selectionOverlay.width,
                height: this.selectionOverlay.height
            };
        } else {
            // In color/gradient mode, entire canvas is the poster
            return {
                left: 0,
                top: 0,
                width: this.canvasWidth,
                height: this.canvasHeight
            };
        }
    }

    addText(text = 'New Text') {
        // Add text centered in the poster area
        const posterArea = this._getPosterArea();
        const left = posterArea.left + posterArea.width / 2;
        const top = posterArea.top + posterArea.height / 2;

        // Use Textbox for better multi-line support with text alignment
        const textObj = new fabric.Textbox(text, {
            left: left,
            top: top,
            fontFamily: 'Arial',
            fontSize: 32,
            fill: '#ffffff',
            textAlign: 'center',
            originX: 'center',
            originY: 'center',
            width: posterArea.width * 0.8,  // Default width for text wrapping
            splitByGrapheme: false
        });

        this.canvas.add(textObj);
        this.canvas.setActiveObject(textObj);
        this._reorderObjects();
        this.canvas.renderAll();

        return textObj;
    }

    addLine() {
        // Add line within the poster area
        const posterArea = this._getPosterArea();
        const left = posterArea.left + 30;
        const top = posterArea.top + posterArea.height * 0.1;  // Start 10% from top
        const lineHeight = posterArea.height * 0.8;  // 80% of poster height

        const line = new fabric.Line([left, top, left, top + lineHeight], {
            stroke: '#ffffff',
            strokeWidth: 2,
            selectable: true,
            hasControls: true
        });

        this.canvas.add(line);
        this.canvas.setActiveObject(line);
        this._reorderObjects();
        this.canvas.renderAll();

        return line;
    }

    deleteSelected() {
        const activeObj = this.canvas.getActiveObject();
        if (activeObj && activeObj !== this.frameImage && !activeObj.isOverlay && !activeObj.isMask) {
            this.canvas.remove(activeObj);
            this.canvas.renderAll();
        }
    }

    getActiveObject() {
        return this.canvas.getActiveObject();
    }

    // Calculate selection coordinates relative to original video frame
    _getSelectionCoords() {
        if (!this.frameDisplayInfo || !this.selectionOverlay) {
            return { left: 0, top: 0, width: 1, height: 1 };
        }

        const frame = this.frameDisplayInfo;
        const overlay = this.selectionOverlay;

        // Convert overlay position from canvas space to frame space (0-1 normalized)
        const left = (overlay.left - frame.displayLeft) / frame.displayWidth;
        const top = (overlay.top - frame.displayTop) / frame.displayHeight;
        const width = overlay.width / frame.displayWidth;
        const height = overlay.height / frame.displayHeight;

        return {
            left: Math.max(0, Math.min(1, left)),
            top: Math.max(0, Math.min(1, top)),
            width: Math.max(0, Math.min(1, width)),
            height: Math.max(0, Math.min(1, height))
        };
    }

    // Export poster data for backend generation
    exportPosterData() {
        const objects = this.canvas.getObjects();
        const textLayers = [];
        const lineElements = [];

        // In elements phase, the canvas IS the poster area (simple coordinates)
        // In background phase, we need to use overlay-relative coordinates
        const isElementsPhase = this.workflowPhase === 'elements';

        let selectionCoords;
        let referenceWidth, referenceHeight, referenceLeft, referenceTop;

        if (isElementsPhase && this.lockedBackgroundData) {
            // Use the locked selection coords from when background was confirmed
            selectionCoords = this.lockedBackgroundData.selectionCoords;
            // Canvas dimensions are the reference (poster-sized canvas)
            referenceWidth = this.canvasWidth;
            referenceHeight = this.canvasHeight;
            referenceLeft = 0;
            referenceTop = 0;
        } else {
            // Background phase - use current overlay position
            selectionCoords = this._getSelectionCoords();
            const overlay = this.selectionOverlay;
            referenceWidth = overlay ? overlay.width : this.canvasWidth;
            referenceHeight = overlay ? overlay.height : this.canvasHeight;
            referenceLeft = overlay ? overlay.left : 0;
            referenceTop = overlay ? overlay.top : 0;
        }

        for (const obj of objects) {
            // Skip frame, overlay, and mask
            if (obj === this.frameImage || obj.isOverlay || obj.isMask) continue;

            // Support both IText and Textbox types
            if (obj.type === 'i-text' || obj.type === 'textbox') {
                // Get the actual bounding rectangle from Fabric.js
                // This gives us the TRUE top-left corner regardless of originX/originY
                const bbox = obj.getBoundingRect();

                // Calculate the actual text content position within the textbox
                // For left-aligned text, the text starts at the textbox left edge
                // For center-aligned, it's centered within the textbox
                // For right-aligned, it ends at the textbox right edge
                // We need to export where the actual text content starts, not the textbox container
                let textLeft = bbox.left;
                const textAlign = obj.textAlign || 'center';
                const textboxWidth = obj.width * (obj.scaleX || 1);

                // Measure the actual text width using the canvas context
                const ctx = this.canvas.getContext('2d');
                const fontStyle = (obj.fontStyle || 'normal') + ' ' + (obj.fontWeight || 'normal');
                const fontSize = obj.fontSize * (obj.scaleY || 1);
                ctx.font = `${fontStyle} ${fontSize}px ${obj.fontFamily || 'Arial'}`;

                // Get the widest line for multi-line text
                const lines = obj.text.split('\n');
                let maxLineWidth = 0;
                for (const line of lines) {
                    const metrics = ctx.measureText(line);
                    maxLineWidth = Math.max(maxLineWidth, metrics.width);
                }

                // Adjust textLeft based on alignment
                if (textAlign === 'center') {
                    textLeft = bbox.left + (textboxWidth - maxLineWidth) / 2;
                } else if (textAlign === 'right') {
                    textLeft = bbox.left + textboxWidth - maxLineWidth;
                }
                // For left-aligned, textLeft stays at bbox.left

                textLayers.push({
                    content: obj.text,
                    // Use calculated text position
                    left: (textLeft - referenceLeft) / referenceWidth,
                    top: (bbox.top - referenceTop) / referenceHeight,
                    fontFamily: obj.fontFamily,
                    fontSize: obj.fontSize,
                    fill: obj.fill,
                    fontWeight: obj.fontWeight || 'normal',
                    fontStyle: obj.fontStyle || 'normal',
                    underline: obj.underline || false,
                    textAlign: obj.textAlign || 'center',
                    angle: obj.angle || 0,
                    scaleX: obj.scaleX || 1,
                    scaleY: obj.scaleY || 1,
                    // Use actual text width, not textbox width
                    width: maxLineWidth / referenceWidth,
                    height: bbox.height / referenceHeight
                });
            } else if (obj.type === 'line') {
                // For lines, we need to calculate the actual endpoint positions on the canvas
                // Fabric.js line has x1,y1,x2,y2 as coordinates, and left,top as bounding box position
                // After transformations (scaling, moving), we need the actual screen positions

                // Calculate absolute positions by applying the object's matrix transform
                const points = obj.calcLinePoints();
                const matrix = obj.calcTransformMatrix();

                // Transform the line endpoints to absolute canvas coordinates
                const point1 = fabric.util.transformPoint({ x: points.x1, y: points.y1 }, matrix);
                const point2 = fabric.util.transformPoint({ x: points.x2, y: points.y2 }, matrix);

                lineElements.push({
                    // Export as normalized absolute positions (0-1)
                    x1: (point1.x - referenceLeft) / referenceWidth,
                    y1: (point1.y - referenceTop) / referenceHeight,
                    x2: (point2.x - referenceLeft) / referenceWidth,
                    y2: (point2.y - referenceTop) / referenceHeight,
                    stroke: obj.stroke,
                    strokeWidth: obj.strokeWidth * (obj.scaleX || 1)  // Account for scaling
                });
            }
        }

        // Use locked background data values if in elements phase
        const bgData = isElementsPhase && this.lockedBackgroundData ? this.lockedBackgroundData : null;

        return {
            backgroundMode: bgData ? bgData.mode : this.backgroundMode,
            backgroundColor: bgData ? bgData.backgroundColor : this.backgroundColor,
            gradientColors: bgData ? bgData.gradientColors : this.gradientColors,
            gradientDirection: bgData ? bgData.gradientDirection : this.gradientDirection,
            videoBase: bgData ? bgData.videoBase : this.videoBase,
            videoPath: bgData ? bgData.videoPath : this.videoPath,
            timestamp: bgData ? bgData.timestamp : this.currentTimestamp,
            selectionCoords: selectionCoords,
            blur: bgData ? bgData.blur : this.blurAmount,
            canvasWidth: referenceWidth,
            canvasHeight: referenceHeight,
            textLayers: textLayers,
            lineElements: lineElements
        };
    }
}
