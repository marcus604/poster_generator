/**
 * Frame Slider - Handles video frame navigation
 */
class FrameSlider {
    constructor(canvasManager) {
        this.canvasManager = canvasManager;
        this.duration = 0;
        this.thumbnails = [];
        this.debounceTimer = null;
        this.debounceDelay = 150; // ms to wait after slider stops moving
        this.pendingTimestamp = null;
        this.isLoading = false;

        this._bindElements();
        this._bindEvents();
    }

    _bindElements() {
        this.slider = document.getElementById('frame-slider');
        this.timestampDisplay = document.getElementById('timestamp-display');
        this.thumbnailStrip = document.getElementById('thumbnail-strip');
        this.btnPrevFrame = document.getElementById('btn-prev-frame');
        this.btnNextFrame = document.getElementById('btn-next-frame');
    }

    _bindEvents() {
        this.slider.addEventListener('input', () => this._onSliderChange());

        // Button navigation
        this.btnPrevFrame.addEventListener('click', () => this._stepFrame(-1));
        this.btnNextFrame.addEventListener('click', () => this._stepFrame(1));

        // Hold button for continuous stepping
        let holdInterval = null;
        const startHold = (direction) => {
            holdInterval = setInterval(() => this._stepFrame(direction), 100);
        };
        const stopHold = () => {
            if (holdInterval) {
                clearInterval(holdInterval);
                holdInterval = null;
            }
        };

        this.btnPrevFrame.addEventListener('mousedown', () => startHold(-1));
        this.btnNextFrame.addEventListener('mousedown', () => startHold(1));
        document.addEventListener('mouseup', stopHold);

        // Keyboard navigation
        document.addEventListener('keydown', (e) => {
            if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') return;

            if (e.key === 'ArrowLeft') {
                this._stepFrame(-1);
                e.preventDefault();
            } else if (e.key === 'ArrowRight') {
                this._stepFrame(1);
                e.preventDefault();
            }
        });
    }

    setDuration(duration) {
        this.duration = duration;
        this.slider.max = duration;
        this.slider.value = 0;
        this._updateTimestampDisplay(0);
    }

    async loadThumbnails(base, path) {
        this.thumbnailStrip.innerHTML = '<span style="color: var(--text-secondary); font-size: 0.8rem;">Loading thumbnails...</span>';

        try {
            const data = await api.getThumbnails(base, path, 15);
            this.thumbnails = data.thumbnails;
            this._renderThumbnails();
        } catch (error) {
            console.error('Failed to load thumbnails:', error);
            this.thumbnailStrip.innerHTML = '';
        }
    }

    _renderThumbnails() {
        this.thumbnailStrip.innerHTML = '';

        const interval = this.duration / this.thumbnails.length;

        this.thumbnails.forEach((thumb, index) => {
            const img = document.createElement('img');
            img.src = `data:image/jpeg;base64,${thumb}`;
            img.alt = `Frame ${index + 1}`;
            img.title = this._formatTime(index * interval);
            img.addEventListener('click', () => {
                const timestamp = index * interval;
                this.slider.value = timestamp;
                this._onSliderChange();
            });
            this.thumbnailStrip.appendChild(img);
        });
    }

    _onSliderChange() {
        const timestamp = parseFloat(this.slider.value);
        this._updateTimestampDisplay(timestamp);

        // Debounce: wait for slider to stop moving before fetching frame
        this.pendingTimestamp = timestamp;

        if (this.debounceTimer) {
            clearTimeout(this.debounceTimer);
        }

        this.debounceTimer = setTimeout(() => {
            this._fetchFrame(this.pendingTimestamp);
        }, this.debounceDelay);
    }

    async _fetchFrame(timestamp) {
        // Skip if already loading or timestamp changed
        if (this.isLoading) return;

        this.isLoading = true;
        await this.canvasManager.setFrame(timestamp);
        this.isLoading = false;

        // If timestamp changed while loading, fetch the new one
        if (this.pendingTimestamp !== timestamp) {
            this._fetchFrame(this.pendingTimestamp);
        }
    }

    _stepFrame(direction) {
        if (this.duration === 0) return;

        // Step by 1/30th of a second (roughly one frame at 30fps)
        const step = direction * (1 / 30);
        let newValue = parseFloat(this.slider.value) + step;
        newValue = Math.max(0, Math.min(this.duration, newValue));

        this.slider.value = newValue;
        this._updateTimestampDisplay(newValue);

        // For button/key steps, fetch immediately (no debounce)
        this.pendingTimestamp = newValue;
        this._fetchFrame(newValue);
    }

    _updateTimestampDisplay(seconds) {
        this.timestampDisplay.textContent = this._formatTime(seconds);
    }

    _formatTime(seconds) {
        const mins = Math.floor(seconds / 60);
        const secs = Math.floor(seconds % 60);
        return `${mins}:${secs.toString().padStart(2, '0')}`;
    }

    getCurrentTimestamp() {
        return parseFloat(this.slider.value);
    }
}
