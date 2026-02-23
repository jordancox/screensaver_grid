# Video Grid Screensaver Generator

A collection of Python scripts that generate dynamic video grid screensavers from source videos using FFmpeg. Create stunning mosaic-style videos with multiple clips playing simultaneously in various grid layouts and animations.

## Overview

This project provides several screensaver generation modes:

- **Static Grid**: Simple grid where each video loops independently in place
- **Staggered Grid**: Grid positions change sequentially, creating a wave effect
- **Growing/Shrinking Grid**: Starts with 1 video, expands to NxN grid, then shrinks back
- **Cabinet Grid**: Arcade cabinet-style with PNG frame overlays (perfect for retro gaming videos)

All scripts automatically detect optimal framerate from source videos and support extensive customization options.

## Features

- Static grid mode with independent video looping
- Automatic framerate detection from source videos
- Configurable grid sizes (2x2, 3x3, 4x4, 5x5, up to 10x10)
- Multiple output resolutions (1080p, 4K)
- Adjustable spacing between grid cells
- Aspect ratio preservation with black padding
- Source video cropping to remove unwanted areas (black bars, watermarks, etc.)
- CRT effects (curved screen + scanlines) for retro aesthetics
- Multiple transition types (fade, wipe, radial, etc.)
- Customizable clip duration and timing
- Cabinet mode with PNG frame overlays
- Looping clips to fill desired duration

## Requirements

### System Requirements
- Python 3.6 or higher
- FFmpeg (with libx264 codec support)
- FFprobe (included with FFmpeg)

### Installation

1. Install FFmpeg:
   ```bash
   # macOS (using Homebrew)
   brew install ffmpeg

   # Ubuntu/Debian
   sudo apt-get install ffmpeg

   # Windows (using Chocolatey)
   choco install ffmpeg
   ```

2. Verify installation:
   ```bash
   ffmpeg -version
   ffprobe -version
   ```

## Scripts

### 1. generate_grid_screensaver.py

Creates a grid screensaver with staggered clip changes. Each position in the grid changes sequentially, creating a smooth wave-like transition effect.

**Usage:**
```bash
python generate_grid_screensaver.py <video_directory> [output_file]
```

**Example:**
```bash
python generate_grid_screensaver.py ./movies screensaver.mp4
```

**Features:**
- Sequential position changes (left-to-right, top-to-bottom)
- Configurable clip duration and change interval
- Timing validation to prevent playback gaps
- Automatic black canvas with timed overlays

### 2. generate_grid_screensaver_v2.py

Enhanced version with automatic framerate detection for smoother playback.

**Usage:**
```bash
python generate_grid_screensaver_v2.py <video_directory> [output_file]
```

**Example:**
```bash
python generate_grid_screensaver_v2.py ./movies screensaver_v2.mp4
```

**Additional Features:**
- Detects most common framerate from source videos (samples up to 10 files)
- Normalizes all clips to detected framerate
- Better compatibility with mixed-framerate source material

### 3. generate_growing_grid.py

Creates a dynamic screensaver that starts with a single fullscreen video and progressively adds videos in a growing grid pattern, then shrinks back to 1.

**Usage:**
```bash
python generate_growing_grid.py <video_directory> [output_file]
```

**Example:**
```bash
python generate_growing_grid.py ./movies growing_grid.mp4
```

**Special Features:**
- **Growing sequence**: 1 → 4 → 9 → 16 → ... → N² → ... → 4 → 1
- **CRT effects**: Light, medium, or heavy (curved screen + scanlines)
- **Source video cropping**: Remove black bars, UI elements, or watermarks
- **8 transition types**: cut, fade, circleopen, circleclose, wipeleft, wiperight, fadeblack, radial
- **Clip looping**: Automatically loops clips to fill entire video duration
- Handles large grids efficiently (up to 10x10 = 100 videos)

### 4. generate_cabinet_grid.py

Creates an arcade cabinet-style grid screensaver where video clips are composited inside PNG frame overlays, perfect for retro gaming content.

**Usage:**
```bash
python generate_cabinet_grid.py <video_directory> <cabinet_png> [output_file]
```

**Example:**
```bash
python generate_cabinet_grid.py ./games cabinet.png cabinet_grid.mp4
```

**Special Features:**
- **Cabinet PNG overlay**: Composite clips inside arcade cabinet frames
- **Automatic PNG detection**: Reads cabinet PNG dimensions automatically
- **Flexible spacing modes**: Even, minimal, or no spacing between cabinets
- **Progressive sequence**: 1x1 → 2x2 → 3x3 → ... → NxN
- **Non-cabinet mode**: Can also work without PNG overlay for standard grid
- Configurable screen position within cabinet frame

### 5. generate_static_grid.py

Creates a simple static grid screensaver where each video loops independently in its own cell. No transitions, animations, or effects - just a clean grid layout with configurable spacing.

**Usage:**
```bash
python generate_static_grid.py
```

**Example:**
```bash
python generate_static_grid.py
# Follow prompts for resolution, grid size, spacing, and video directory
```

**Special Features:**
- **Static looping**: Each video loops continuously in its position
- **Aspect ratio preservation**: Videos maintain their aspect ratio with black padding
- **Configurable spacing**: Adjust pixel spacing between grid cells
- **No temporary files**: Direct rendering without intermediate clip extraction
- **Automatic looping**: Videos loop seamlessly to match the longest video duration
- **Flexible grid sizes**: Any rows × columns configuration
- Perfect for simple, clean video walls or ambient displays

## Configuration Options

All scripts provide interactive prompts for configuration:

### Common Options
- **Output resolution**: 1080p (1920x1080) or 4K (3840x2160)
- **Grid size**: From 2x2 up to 10x10 (depending on script)
- **Clip duration**: How long each clip plays (seconds)
- **Number of clips**: Total unique clips to extract from source videos

### Advanced Options
- **Change interval**: Time between position changes (staggered grid)
- **Hold duration**: Time to display each grid state (growing/cabinet)
- **Source cropping**: Remove pixels from top/right/bottom/left of source videos
- **CRT effect**: Add retro curved screen + scanline effects (growing grid)
- **Transition type**: Choose from 8 different transition effects (growing grid)
- **Spacing mode**: Control gap size between videos (cabinet grid)

## How It Works

### Processing Pipeline

1. **Scan for videos**: Recursively finds all video files in specified directory
2. **Detect framerate**: Samples source videos to determine optimal framerate
3. **Extract clips**: Randomly extracts clips from source videos
   - Avoids first/last 10 seconds (configurable)
   - Scales and crops to appropriate dimensions
   - Applies CRT effects or source cropping if configured
4. **Process clips**:
   - Concatenates clips for each grid position (staggered)
   - Creates looped versions for specified duration (growing/cabinet)
   - Composites with PNG overlays if using cabinet mode
5. **Generate grid**: Uses FFmpeg filter_complex to create final grid layout
6. **Render output**: Encodes final video with libx264 codec

### Technical Details

- **Codec**: H.264 (libx264)
- **Preset**: ultrafast for intermediate files, medium for final output
- **CRF**: 23 (balanced quality/size)
- **Pixel format**: yuv420p (universal compatibility)
- **Aspect ratio handling**: Scales to fill, then crops excess

## Examples

### Basic 4x4 Grid
```bash
python generate_grid_screensaver.py ./movies output.mp4
# Follow prompts: 1080p, 4x4 grid, 80 clips, 10s clips, 2s intervals
```

### Growing Grid with CRT Effect
```bash
python generate_growing_grid.py ./retro_games crt_screensaver.mp4
# Choose: 1080p, 5x5 max grid, heavy CRT effect, fade transitions
```

### Arcade Cabinet Grid
```bash
python generate_cabinet_grid.py ./arcade_footage cabinet.png arcade.mp4
# Place cabinet.png in project directory first
# Choose: 1080p, 3x3 grid, even spacing, 9 clips
```

### Static Looping Grid
```bash
python generate_static_grid.py
# Follow prompts: 1080p, 3x3 grid, 10px spacing, ./movies directory
# Creates a clean video wall where each video loops independently
```

## Tips and Best Practices

### Choosing the Right Script

- **generate_static_grid.py**: Best for simple video walls, ambient displays, or when you want each video to loop continuously without effects. Fastest to render, no temporary files needed.
- **generate_grid_screensaver.py / v2.py**: Best for dynamic screensavers where you want content to change position-by-position with a wave effect.
- **generate_growing_grid.py**: Best for eye-catching presentations with animated transitions, CRT effects, or progressive grid expansion.
- **generate_cabinet_grid.py**: Best for retro gaming content with arcade cabinet aesthetics.

### Source Video Selection
- Use high-quality source videos (at least 720p)
- Mix of different content creates more interesting results
- Ensure videos are long enough (> 30 seconds recommended)
- For cabinet mode, 4:3 aspect ratio sources work best
- For static grid, use complete video files you want to display (no random clip extraction)

### Performance Optimization
- Use smaller grid sizes (3x3 or 4x4) for faster rendering
- Set preset to "ultrafast" in code for quicker iterations during testing
- Extract fewer clips if you just want to preview the effect
- Use SSD storage for temporary files

### Timing Guidelines

For **staggered grid** scripts:
- Clip duration should be ≥ (grid_size² × change_interval)
- Example: 4x4 grid with 2s intervals needs ≥32s clip duration
- Scripts will warn you if timing causes gaps

For **growing/cabinet** scripts:
- Clips automatically loop, so any duration works
- Longer clips (15-30s) create more variety before looping

### Temporary Files

Most scripts create temporary directories (except `generate_static_grid.py`):
- `clips_temp/`: Extracted video clips
- `position_videos_temp/`: Concatenated position streams
- `segments_temp/`: Individual grid state videos
- `cabinets_temp/`: Cabinet composites and loops
- `loops_temp/`: Looped clip files

**Note**: `generate_static_grid.py` does not create any temporary files - it renders directly.

**Cleanup:**
```bash
rm -rf clips_temp position_videos_temp segments_temp cabinets_temp loops_temp
```

Or follow cleanup instructions printed by each script after completion.

## Troubleshooting

### FFmpeg not found
```
Error: ffmpeg/ffprobe not found in PATH
```
**Solution**: Install FFmpeg and ensure it's in your system PATH

### File descriptor limits (large grids)
```
Error: Too many open files
```
**Solution**: Scripts automatically handle this by concatenating position clips. If issues persist, use smaller grid sizes.

### Timing warnings (staggered grid)
```
WARNING: Timing issue detected!
```
**Solution**: Either increase clip duration or decrease change interval as suggested by the script.

### Out of memory errors
```
Error: FFmpeg killed / out of memory
```
**Solution**:
- Reduce grid size
- Lower output resolution
- Use faster preset to reduce memory usage
- Close other applications

## Project Structure

```
screensaver_grid/
├── generate_grid_screensaver.py       # Original staggered grid
├── generate_grid_screensaver_v2.py    # Enhanced with framerate detection
├── generate_growing_grid.py           # Growing/shrinking animation
├── generate_cabinet_grid.py           # Arcade cabinet style
├── generate_static_grid.py            # Static looping grid
├── cabinet.png                        # Example cabinet frame overlay
├── ffmpeg_command.txt                 # Last FFmpeg command (for debugging)
├── movies/                            # Source video directory (example)
└── README.md                          # This file
```

## Cabinet PNG Format

For `generate_cabinet_grid.py`, provide a PNG with transparency showing an arcade cabinet frame.

**Requirements:**
- PNG with alpha channel (transparency)
- Screen area should be transparent (where video appears)
- Any resolution (will be auto-detected)

**Default screen position** (can be customized in script):
- X offset: 120px from left
- Y offset: 154px from top
- Size: 420x315px (4:3 ratio)

See `cabinet.png` for an example.

## Output Examples

Generated videos are perfect for:
- Digital art installations
- Stream backgrounds
- Desktop wallpapers (with Wallpaper Engine)
- Waiting room displays
- Retro gaming showcases
- Social media content
- Video DJ performances

## Performance Notes

**Rendering time** depends on:
- Grid size (4x4 ≈ 16 streams, 5x5 = 25 streams)
- Output resolution (4K takes ~4x longer than 1080p)
- Video duration
- CPU performance
- Number of clips

**Typical rendering times** (4x4 grid, 1080p, 2-minute output, modern CPU):
- Clip extraction: 2-5 minutes
- Grid composition: 5-15 minutes
- **Total**: 10-20 minutes

## License

This project is provided as-is for personal and commercial use.

## Credits

Created using:
- Python 3
- FFmpeg for video processing
- FFprobe for media analysis

## Contributing

Feel free to modify and extend these scripts for your needs. Common enhancements:
- Custom transition effects
- Audio mixing from source videos
- Text overlays (titles, timestamps)
- Color grading filters
- Dynamic grid sizing within single video
- Interactive controls

## Support

For FFmpeg issues, consult: https://ffmpeg.org/documentation.html

For Python issues, ensure you're using Python 3.6+

---

**Enjoy creating dynamic video mosaics!**
