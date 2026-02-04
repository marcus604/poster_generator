/**
 * API Client for communicating with the backend
 */
class ApiClient {
    constructor(baseUrl = '') {
        this.baseUrl = baseUrl;
    }

    async listVideos(path = null) {
        const url = new URL('/api/videos', window.location.origin);
        if (path) {
            url.searchParams.set('path', path);
        }
        const response = await fetch(url);
        if (!response.ok) throw new Error('Failed to list videos');
        return response.json();
    }

    async getVideoInfo(base, path) {
        const url = new URL('/api/videos/info', window.location.origin);
        url.searchParams.set('base', base);
        url.searchParams.set('path', path);
        const response = await fetch(url);
        if (!response.ok) throw new Error('Failed to get video info');
        return response.json();
    }

    getPreviewFrameUrl(base, path, timestamp) {
        const url = new URL('/api/frames/preview', window.location.origin);
        url.searchParams.set('base', base);
        url.searchParams.set('path', path);
        url.searchParams.set('t', timestamp.toString());
        return url.toString();
    }

    getFullFrameUrl(base, path, timestamp) {
        const url = new URL('/api/frames/full', window.location.origin);
        url.searchParams.set('base', base);
        url.searchParams.set('path', path);
        url.searchParams.set('t', timestamp.toString());
        return url.toString();
    }

    async getThumbnails(base, path, count = 20) {
        const url = new URL('/api/frames/thumbnails', window.location.origin);
        url.searchParams.set('base', base);
        url.searchParams.set('path', path);
        url.searchParams.set('count', count.toString());
        const response = await fetch(url);
        if (!response.ok) throw new Error('Failed to get thumbnails');
        return response.json();
    }

    async generatePoster(posterData) {
        const response = await fetch('/api/posters/generate', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(posterData)
        });
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to generate poster');
        }
        return response.json();
    }
}

// Global instance
const api = new ApiClient();
