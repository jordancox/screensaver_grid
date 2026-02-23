#!/usr/bin/env python3
"""
Generate a static grid screensaver where each video loops in place.
Videos maintain aspect ratio with black padding, adjustable spacing.
"""

import os
import sys
import json
import subprocess
from pathlib import Path

# Configuration
OUTPUT_WIDTH = 1920
OUTPUT_HEIGHT = 1080
GRID_ROWS = 3
GRID_COLS = 3
SPACING = 10  # pixels between videos
CROP_LEFT = 0
CROP_RIGHT = 0
CROP_TOP = 0
CROP_BOTTOM = 0
SKIP_START = 0  # seconds to skip at the start of each video
CUSTOM_DURATION = None  # None = use longest video, or set to seconds
VIDEO_EXTENSIONS = {'.mp4', '.mov', '.avi', '.mkv', '.m4v', '.mpg', '.mpeg', '.wmv'}


def get_user_config():
    """Prompt user for configuration parameters."""
    global OUTPUT_WIDTH, OUTPUT_HEIGHT, GRID_ROWS, GRID_COLS, SPACING, CROP_LEFT, CROP_RIGHT, CROP_TOP, CROP_BOTTOM, SKIP_START, CUSTOM_DURATION

    print("\n=== Static Grid Screensaver Generator ===\n")

    # Output resolution
    print("Output resolution:")
    print("  1) 1080p (1920x1080)")
    print("  2) 4K (3840x2160)")
    while True:
        choice = input("Choose [1-2] (default: 1): ").strip() or "1"
        if choice == "1":
            OUTPUT_WIDTH, OUTPUT_HEIGHT = 1920, 1080
            break
        elif choice == "2":
            OUTPUT_WIDTH, OUTPUT_HEIGHT = 3840, 2160
            break
        else:
            print("Invalid choice. Please enter 1 or 2.")

    # Grid size
    print("\nGrid size:")
    while True:
        try:
            rows = input("Number of rows (default: 3): ").strip() or "3"
            cols = input("Number of columns (default: 3): ").strip() or "3"
            GRID_ROWS = int(rows)
            GRID_COLS = int(cols)
            if GRID_ROWS > 0 and GRID_COLS > 0:
                break
            print("Rows and columns must be positive numbers.")
        except ValueError:
            print("Please enter valid numbers.")

    # Spacing
    print("\nSpacing between videos:")
    while True:
        try:
            spacing = input("Spacing in pixels (default: 10): ").strip() or "10"
            SPACING = int(spacing)
            if SPACING >= 0:
                break
            print("Spacing must be non-negative.")
        except ValueError:
            print("Please enter a valid number.")

    # Crop settings
    print("\nCrop settings (crop pixels from each edge):")
    while True:
        try:
            left = input("Crop from left (default: 0): ").strip() or "0"
            right = input("Crop from right (default: 0): ").strip() or "0"
            top = input("Crop from top (default: 0): ").strip() or "0"
            bottom = input("Crop from bottom (default: 0): ").strip() or "0"
            CROP_LEFT = int(left)
            CROP_RIGHT = int(right)
            CROP_TOP = int(top)
            CROP_BOTTOM = int(bottom)
            if CROP_LEFT >= 0 and CROP_RIGHT >= 0 and CROP_TOP >= 0 and CROP_BOTTOM >= 0:
                break
            print("Crop values must be non-negative.")
        except ValueError:
            print("Please enter valid numbers.")

    # Skip intro/start
    print("\nSkip intro (trim start of each video):")
    while True:
        try:
            skip = input("Seconds to skip at start (default: 0): ").strip() or "0"
            SKIP_START = float(skip)
            if SKIP_START >= 0:
                break
            print("Skip value must be non-negative.")
        except ValueError:
            print("Please enter a valid number.")

    # Duration settings
    print("\nVideo duration:")
    print("  1) Use longest video duration")
    print("  2) Set custom duration")
    while True:
        choice = input("Choose [1-2] (default: 1): ").strip() or "1"
        if choice == "1":
            CUSTOM_DURATION = None
            break
        elif choice == "2":
            while True:
                try:
                    duration = input("Enter duration in seconds: ").strip()
                    CUSTOM_DURATION = float(duration)
                    if CUSTOM_DURATION > 0:
                        break
                    print("Duration must be positive.")
                except ValueError:
                    print("Please enter a valid number.")
            break
        else:
            print("Invalid choice. Please enter 1 or 2.")

    print(f"\nConfiguration:")
    print(f"  Resolution: {OUTPUT_WIDTH}x{OUTPUT_HEIGHT}")
    print(f"  Grid: {GRID_ROWS}x{GRID_COLS}")
    print(f"  Spacing: {SPACING}px")
    if CROP_LEFT > 0 or CROP_RIGHT > 0 or CROP_TOP > 0 or CROP_BOTTOM > 0:
        print(f"  Crop: L:{CROP_LEFT}px R:{CROP_RIGHT}px T:{CROP_TOP}px B:{CROP_BOTTOM}px")
    if SKIP_START > 0:
        print(f"  Skip start: {SKIP_START}s")
    if CUSTOM_DURATION:
        print(f"  Duration: {CUSTOM_DURATION}s (custom)")
    else:
        print(f"  Duration: Use longest video")
    print()


def find_videos(directory):
    """Find all video files in the given directory."""
    video_files = []
    path = Path(directory)

    if not path.exists():
        print(f"Error: Directory '{directory}' does not exist.")
        return []

    for file in sorted(path.iterdir()):
        if file.is_file() and file.suffix.lower() in VIDEO_EXTENSIONS:
            video_files.append(str(file))

    return video_files


def get_video_info(video_path):
    """Get video duration and dimensions using ffprobe."""
    cmd = [
        'ffprobe',
        '-v', 'error',
        '-select_streams', 'v:0',
        '-show_entries', 'stream=width,height,duration,r_frame_rate',
        '-show_entries', 'format=duration',
        '-of', 'json',
        video_path
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        data = json.loads(result.stdout)

        stream = data.get('streams', [{}])[0]
        format_data = data.get('format', {})

        width = stream.get('width', 0)
        height = stream.get('height', 0)

        # Try to get duration from stream first, then format
        duration = stream.get('duration')
        if not duration:
            duration = format_data.get('duration')

        duration = float(duration) if duration else 0

        # Parse frame rate
        fps_str = stream.get('r_frame_rate', '30/1')
        fps_parts = fps_str.split('/')
        fps = float(fps_parts[0]) / float(fps_parts[1]) if len(fps_parts) == 2 else 30.0

        return {
            'width': width,
            'height': height,
            'duration': duration,
            'fps': fps
        }
    except Exception as e:
        print(f"Error getting info for {video_path}: {e}")
        return None


def generate_grid():
    """Generate the static grid video."""
    get_user_config()

    # Find video files
    video_dir = input("Enter video directory (default: ./movies): ").strip() or "./movies"
    videos = find_videos(video_dir)

    if not videos:
        print(f"No videos found in '{video_dir}'")
        return

    total_positions = GRID_ROWS * GRID_COLS
    print(f"\nFound {len(videos)} videos")
    print(f"Grid has {total_positions} positions")

    if len(videos) < total_positions:
        print(f"\n⚠️  Warning: Only {len(videos)} videos available for {total_positions} grid positions!")
        print(f"You need {total_positions - len(videos)} more video(s) to fill the {GRID_ROWS}x{GRID_COLS} grid.\n")

        # Suggest better grid sizes
        import math
        sqrt_videos = int(math.sqrt(len(videos)))
        print("Suggested grid sizes that would use all your videos:")

        suggestions = []
        # Try to find grid dimensions that are close to the number of videos
        for rows in range(1, len(videos) + 1):
            if len(videos) % rows == 0:
                cols = len(videos) // rows
                suggestions.append((rows, cols))

        # Show up to 5 suggestions that make sense
        shown = 0
        for rows, cols in suggestions:
            if shown >= 5:
                break
            if abs(rows - cols) <= max(rows, cols) // 2:  # Not too rectangular
                print(f"  - {rows}x{cols} grid")
                shown += 1

        choice = input(f"\nContinue with partially filled {GRID_ROWS}x{GRID_COLS} grid? (y/n): ").strip().lower()
        if choice != 'y':
            print("Exiting. Please run again and choose a smaller grid size.")
            return

    # Get info for all videos
    print("\nAnalyzing videos...")
    video_info = {}
    max_duration = 0

    for i, video in enumerate(videos[:total_positions]):
        info = get_video_info(video)
        if info:
            video_info[video] = info
            max_duration = max(max_duration, info['duration'])
            print(f"  {i+1}/{min(len(videos), total_positions)}: {Path(video).name} - {info['duration']:.1f}s")

    if not video_info:
        print("Error: Could not get info for any videos")
        return

    print(f"\nLongest video: {max_duration:.1f}s")

    # Calculate cell dimensions
    total_spacing_x = SPACING * (GRID_COLS + 1)
    total_spacing_y = SPACING * (GRID_ROWS + 1)
    cell_width = (OUTPUT_WIDTH - total_spacing_x) // GRID_COLS
    cell_height = (OUTPUT_HEIGHT - total_spacing_y) // GRID_ROWS

    print(f"Cell size: {cell_width}x{cell_height}")

    # Build ffmpeg filter complex
    filter_parts = []
    video_inputs = []

    # Prepare each video input with looping and scaling
    for i, (row, col) in enumerate((r, c) for r in range(GRID_ROWS) for c in range(GRID_COLS)):
        if i < len(videos):
            video = videos[i]
            info = video_info.get(video)
            if not info:
                continue

            video_inputs.append(video)
            input_idx = len(video_inputs) - 1

            # Calculate position
            x_pos = SPACING + col * (cell_width + SPACING)
            y_pos = SPACING + row * (cell_height + SPACING)

            # Build filter chain: crop (if needed), loop, scale, and pad
            filter_chain = f"[{input_idx}:v]"

            # Apply crop if any crop values are set
            if CROP_LEFT > 0 or CROP_RIGHT > 0 or CROP_TOP > 0 or CROP_BOTTOM > 0:
                crop_w = info['width'] - CROP_LEFT - CROP_RIGHT
                crop_h = info['height'] - CROP_TOP - CROP_BOTTOM
                filter_chain += f"crop={crop_w}:{crop_h}:{CROP_LEFT}:{CROP_TOP},"

            # Scale and pad (looping handled by -stream_loop input option)
            filter_chain += (
                f"scale=w={cell_width}:h={cell_height}:force_original_aspect_ratio=decrease:force_divisible_by=2,"
                f"pad={cell_width}:{cell_height}:-1:-1:black[v{i}]"
            )

            filter_parts.append(filter_chain)

    # Create base black canvas
    filter_complex = f"color=c=black:s={OUTPUT_WIDTH}x{OUTPUT_HEIGHT}:r=30[base]"

    # Add scaled videos
    if filter_parts:
        filter_complex += ";" + ";".join(filter_parts)

    # Overlay all videos onto the base
    overlay_chain = "[base]"
    for i in range(len(video_inputs)):
        row = i // GRID_COLS
        col = i % GRID_COLS
        x_pos = SPACING + col * (cell_width + SPACING)
        y_pos = SPACING + row * (cell_height + SPACING)

        if i == len(video_inputs) - 1:
            # Last overlay outputs directly
            filter_complex += f";{overlay_chain}[v{i}]overlay={x_pos}:{y_pos}:shortest=0[outv]"
        else:
            filter_complex += f";{overlay_chain}[v{i}]overlay={x_pos}:{y_pos}:shortest=0[tmp{i}]"
            overlay_chain = f"[tmp{i}]"

    # Determine output filename
    output_file = f"static_grid_{GRID_ROWS}x{GRID_COLS}_{OUTPUT_WIDTH}x{OUTPUT_HEIGHT}.mp4"

    # Build ffmpeg command
    cmd = ['ffmpeg', '-y']

    # Add all video inputs with stream looping and start skip
    for video in video_inputs:
        if SKIP_START > 0:
            cmd.extend(['-ss', str(SKIP_START), '-stream_loop', '-1', '-i', video])
        else:
            cmd.extend(['-stream_loop', '-1', '-i', video])

    # Determine output duration
    output_duration = CUSTOM_DURATION if CUSTOM_DURATION else max_duration

    # Add filter complex
    cmd.extend([
        '-filter_complex', filter_complex,
        '-map', '[outv]',
        '-t', str(output_duration),
        '-c:v', 'libx264',
        '-preset', 'medium',
        '-crf', '23',
        '-pix_fmt', 'yuv420p',
        '-r', '30',
        output_file
    ])

    print(f"\nGenerating grid video: {output_file}")
    print(f"Output duration: {output_duration:.1f}s")
    print("This may take a while...\n")

    # Run ffmpeg
    try:
        subprocess.run(cmd, check=True)
        print(f"\n✓ Successfully created {output_file}")
        print(f"  Duration: {output_duration:.1f}s")
        print(f"  Resolution: {OUTPUT_WIDTH}x{OUTPUT_HEIGHT}")
    except subprocess.CalledProcessError as e:
        print(f"\n✗ Error generating video: {e}")
        return
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
        return


if __name__ == '__main__':
    try:
        generate_grid()
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
        sys.exit(0)
