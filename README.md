# Movie Poster Generator

A web application for creating custom Movie posters from video frames with text overlays and decorative elements.

![Preview](https://img.shields.io/badge/Output-1000x1500px-blue) ![Docker](https://img.shields.io/badge/Docker-Ready-green)

## Features

- **Video Frame Selection**: Browse your media library and extract frames at any timestamp
- **Flexible Backgrounds**: Use video frames, solid colors, or gradients
- **Frame Cropping**: Drag-to-position overlay for selecting the perfect 2:3 crop area
- **Background Blur**: Apply blur effects to frame backgrounds
- **Text Overlays**: Add multiple text layers with customizable fonts, sizes, colors, and alignment
- **Decorative Lines**: Add vertical/horizontal lines for styling
- **Multi-line Text**: Support for multiple lines with left/center/right alignment
- **Live Preview**: See your poster design in real-time before generating

## Quick Start

### Using Docker Compose

1. Create a `.env` file:

```env
VIDEO_PATH_1=/path/to/your/movies
OUTPUT_PATH=./output
WEB_PORT=8080
```

2. Run the container:

```bash
docker compose up -d
```

3. Open http://localhost:8080 in your browser

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `VIDEO_PATH_1` | Path to your video library | Required |
| `VIDEO_PATH_2` | Additional video path (optional) | - |
| `OUTPUT_PATH` | Where generated posters are saved | `./output` |
| `WEB_PORT` | Web interface port | `8080` |
| `FONTS_PATH` | Custom fonts directory (optional) | - |

## Usage

### 1. Select a Video
Browse your mounted video directories and select a video file.

### 2. Configure Background
- **Image**: Scrub through the video to find the perfect frame, then drag the selection overlay to crop
- **Color**: Choose a solid background color
- **Gradient**: Select two colors and a direction (vertical, horizontal, diagonal)

Use the blur slider to add background blur if desired.

### 3. Add Text & Elements
Click "Confirm Background" to lock in your selection, then:
- **Add Text**: Click "+ Add Text" to add text layers
- **Add Line**: Click "+ Add Line" to add decorative lines

For text, you can customize:
- Font family and size
- Color
- Bold, italic, underline
- Multi-line with alignment (left, center, right)

### 4. Generate
Enter a filename and click "Generate Poster". The poster will be saved to your output directory as a 1000x1500px PNG.

## Custom Fonts

To use custom fonts, mount a fonts directory:

```yaml
volumes:
  - /path/to/fonts:/app/static/fonts:ro
```

Place `.ttf` or `.otf` files in the directory. Font variants should be named:
- `FontName.ttf`
- `FontName-Bold.ttf`
- `FontName-Italic.ttf`
- `FontName-BoldItalic.ttf`

## Development

### Project Structure

```
poster_generator/
├── app/
│   ├── api/routes/      # FastAPI endpoints
│   ├── services/        # Business logic
│   └── utils/           # FFmpeg utilities
├── static/
│   ├── js/              # Frontend JavaScript
│   └── css/             # Styles
├── Dockerfile
└── docker-compose.yml
```

### Running Locally

```bash
# Install dependencies
pip install -r requirements.txt

# Run the server
uvicorn app.main:app --host 0.0.0.0 --port 8080 --reload
```

### Tech Stack

- **Backend**: FastAPI, Pillow, FFmpeg
- **Frontend**: Vanilla JS, Fabric.js
- **Container**: Docker with multi-arch support (amd64/arm64)

## License

MIT
