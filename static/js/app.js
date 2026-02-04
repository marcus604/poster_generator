/**
 * Main Application - Orchestrates the poster generator
 */
class App {
    constructor() {
        this.canvasManager = new CanvasManager('poster-canvas');
        this.textEditor = new TextEditor(this.canvasManager);
        this.frameSlider = new FrameSlider(this.canvasManager);

        this.currentPath = [];
        this.selectedVideo = null;

        this._bindElements();
        this._bindEvents();
        this._init();
    }

    _bindElements() {
        // File browser
        this.fileList = document.getElementById('file-list');
        this.btnBack = document.getElementById('btn-back');
        this.currentPathDisplay = document.getElementById('current-path');

        // Video info
        this.videoInfo = document.getElementById('video-info');
        this.selectedVideoName = document.getElementById('selected-video-name');
        this.videoResolution = document.getElementById('video-resolution');
        this.videoDuration = document.getElementById('video-duration');

        // Panels
        this.backgroundPanel = document.getElementById('background-panel');
        this.textPanel = document.getElementById('text-panel');
        this.generatePanel = document.getElementById('generate-panel');

        // Background controls
        this.toggleBtns = document.querySelectorAll('.toggle-btn');
        this.imageControls = document.getElementById('image-controls');
        this.colorControls = document.getElementById('color-controls');
        this.gradientControls = document.getElementById('gradient-controls');
        this.bgColor = document.getElementById('bg-color');
        this.gradientColor1 = document.getElementById('gradient-color-1');
        this.gradientColor2 = document.getElementById('gradient-color-2');
        this.gradientDirection = document.getElementById('gradient-direction');
        this.zoomSlider = document.getElementById('zoom-slider');
        this.blurSlider = document.getElementById('image-blur');
        this.blurValue = document.getElementById('blur-value');
        this.btnResetOverlay = document.getElementById('btn-reset-overlay');

        // Text/Line buttons
        this.btnAddText = document.getElementById('btn-add-text');
        this.btnAddLine = document.getElementById('btn-add-line');

        // Workflow phase buttons
        this.btnConfirmBackground = document.getElementById('btn-confirm-background');
        this.btnChangeBackground = document.getElementById('btn-change-background');

        // Generate
        this.outputFilename = document.getElementById('output-filename');
        this.btnGenerate = document.getElementById('btn-generate');
        this.generationStatus = document.getElementById('generation-status');
    }

    _bindEvents() {
        // File browser
        this.btnBack.addEventListener('click', () => this._navigateBack());

        // Background mode toggle
        this.toggleBtns.forEach(btn => {
            btn.addEventListener('click', () => this._setBackgroundMode(btn.dataset.mode));
        });

        // Background controls
        this.bgColor.addEventListener('input', () => {
            this.canvasManager.setBackgroundColor(this.bgColor.value);
        });

        this.gradientColor1.addEventListener('input', () => {
            this.canvasManager.setGradientColors(this.gradientColor1.value, this.gradientColor2.value);
        });

        this.gradientColor2.addEventListener('input', () => {
            this.canvasManager.setGradientColors(this.gradientColor1.value, this.gradientColor2.value);
        });

        this.gradientDirection.addEventListener('change', () => {
            this.canvasManager.setGradientDirection(this.gradientDirection.value);
        });

        this.zoomSlider.addEventListener('input', () => {
            this.canvasManager.setZoom(parseInt(this.zoomSlider.value));
        });

        this.blurSlider.addEventListener('input', () => {
            const blurAmount = parseInt(this.blurSlider.value);
            this.blurValue.textContent = blurAmount;
            this.canvasManager.setBlur(blurAmount);
        });

        this.btnResetOverlay.addEventListener('click', () => {
            this.canvasManager.resetOverlayPosition();
        });

        // Workflow phase buttons
        this.btnConfirmBackground.addEventListener('click', () => this._confirmBackground());
        this.btnChangeBackground.addEventListener('click', () => this._changeBackground());

        // Text/Line buttons
        this.btnAddText.addEventListener('click', () => {
            this.canvasManager.addText('New Text');
        });

        this.btnAddLine.addEventListener('click', () => {
            this.canvasManager.addLine();
        });

        // Generate button
        this.btnGenerate.addEventListener('click', () => this._generatePoster());
    }

    async _init() {
        await this._loadVideos();
    }

    async _loadVideos(path = null) {
        this.fileList.innerHTML = '<li class="loading">Loading...</li>';

        try {
            const items = await api.listVideos(path);

            if (items.length === 0) {
                this.fileList.innerHTML = '<li class="loading">No videos found</li>';
                return;
            }

            this.fileList.innerHTML = '';

            // Sort: folders first, then videos
            items.sort((a, b) => {
                if (a.type !== b.type) {
                    return a.type === 'directory' ? -1 : 1;
                }
                return a.name.localeCompare(b.name);
            });

            items.forEach(item => {
                const li = document.createElement('li');
                li.className = item.type === 'directory' ? 'folder' : 'video';
                li.innerHTML = `<span class="icon"></span>${item.name}`;

                if (item.type === 'directory') {
                    li.addEventListener('click', () => this._navigateTo(item));
                } else {
                    li.addEventListener('click', () => this._selectVideo(item));
                }

                this.fileList.appendChild(li);
            });
        } catch (error) {
            console.error('Failed to load videos:', error);
            this.fileList.innerHTML = '<li class="loading">Error loading videos</li>';
        }
    }

    _navigateTo(folder) {
        this.currentPath.push(folder);
        this._updatePathDisplay();
        this._loadVideos(folder.path);
    }

    _navigateBack() {
        if (this.currentPath.length === 0) return;

        this.currentPath.pop();
        this._updatePathDisplay();

        if (this.currentPath.length === 0) {
            this._loadVideos();
        } else {
            const current = this.currentPath[this.currentPath.length - 1];
            this._loadVideos(current.path);
        }
    }

    _updatePathDisplay() {
        const pathStr = '/' + this.currentPath.map(p => p.name).join('/');
        this.currentPathDisplay.textContent = pathStr;
        this.btnBack.disabled = this.currentPath.length === 0;
    }

    async _selectVideo(video) {
        // Highlight selected
        this.fileList.querySelectorAll('li').forEach(li => li.classList.remove('selected'));
        event.currentTarget.classList.add('selected');

        // Get video info
        try {
            const info = await api.getVideoInfo(video.base, video.path);
            this.selectedVideo = { ...video, ...info };

            // Update video info display
            this.selectedVideoName.textContent = video.name;
            this.videoResolution.textContent = `${info.width}×${info.height}`;
            this.videoDuration.textContent = this._formatDuration(info.duration);
            this.videoInfo.style.display = 'block';

            // Reset canvas before loading new video (clears old text/lines/background)
            this.canvasManager.resetCanvas();

            // Setup canvas for new video
            this.canvasManager.setVideo(video.base, video.path);
            this.frameSlider.setDuration(info.duration);

            // Load thumbnails and first frame
            this.frameSlider.loadThumbnails(video.base, video.path);
            this.canvasManager.setFrame(0);

            // Show background panel only (text/generate shown after background is confirmed)
            this.backgroundPanel.style.display = 'block';
            this.textPanel.style.display = 'none';
            this.generatePanel.style.display = 'none';

            // Set default filename
            const baseName = video.name.replace(/\.[^/.]+$/, '');
            this.outputFilename.value = baseName + '_poster';
        } catch (error) {
            console.error('Failed to get video info:', error);
            alert('Failed to load video information');
        }
    }

    _setBackgroundMode(mode) {
        // Update toggle buttons
        this.toggleBtns.forEach(btn => {
            btn.classList.toggle('active', btn.dataset.mode === mode);
        });

        // Show/hide controls
        this.imageControls.style.display = mode === 'image' ? 'block' : 'none';
        this.colorControls.style.display = mode === 'color' ? 'block' : 'none';
        this.gradientControls.style.display = mode === 'gradient' ? 'block' : 'none';

        // Update canvas
        this.canvasManager.setBackgroundMode(mode);
    }

    async _generatePoster() {
        if (!this.selectedVideo) {
            alert('Please select a video first');
            return;
        }

        const filename = this.outputFilename.value.trim();
        if (!filename) {
            alert('Please enter a filename');
            return;
        }

        this.btnGenerate.disabled = true;
        this.generationStatus.textContent = 'Generating poster...';
        this.generationStatus.className = '';

        try {
            const posterData = this.canvasManager.exportPosterData();
            posterData.filename = filename;

            const result = await api.generatePoster(posterData);

            this.generationStatus.textContent = `✓ Saved: ${result.filename}`;
            this.generationStatus.className = 'success';
        } catch (error) {
            console.error('Failed to generate poster:', error);
            this.generationStatus.textContent = `✗ Error: ${error.message}`;
            this.generationStatus.className = 'error';
        } finally {
            this.btnGenerate.disabled = false;
        }
    }

    _formatDuration(seconds) {
        const mins = Math.floor(seconds / 60);
        const secs = Math.floor(seconds % 60);
        if (mins >= 60) {
            const hours = Math.floor(mins / 60);
            const remainMins = mins % 60;
            return `${hours}:${remainMins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
        }
        return `${mins}:${secs.toString().padStart(2, '0')}`;
    }

    async _confirmBackground() {
        // Confirm background selection and switch to elements phase
        await this.canvasManager.confirmBackground();

        // Hide the entire background panel
        this.backgroundPanel.style.display = 'none';

        // Show text and generate panels
        this.textPanel.style.display = 'block';
        this.generatePanel.style.display = 'block';
    }

    _changeBackground() {
        // Reset to background phase
        this.canvasManager.resetToBackgroundPhase();

        // Show background panel again
        this.backgroundPanel.style.display = 'block';
        this.btnConfirmBackground.style.display = 'block';

        // Hide text and generate panels
        this.textPanel.style.display = 'none';
        this.generatePanel.style.display = 'none';
    }
}

// Initialize app when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    window.app = new App();
});
