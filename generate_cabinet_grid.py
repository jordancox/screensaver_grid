#!/usr/bin/env python3
"""
Generate a cabinet grid screensaver with sliding animations.
Starts with 1 cabinet, adds columns/rows alternately with smoothstep easing.
Each cabinet shows a game clip inside a PNG frame overlay.
"""

import os
import sys
import json
import random
import subprocess
from pathlib import Path
from collections import Counter

# Configuration (set by user prompts)
OUTPUT_WIDTH = 1920
OUTPUT_HEIGHT = 1080
MAX_GRID_SIZE = 5  # e.g., 5x5 grid
CLIP_DURATION = 10  # seconds per clip
HOLD_DURATION = 10  # seconds to hold each grid state
AVOID_EDGES = 10  # avoid first/last N seconds of source videos
TOTAL_CLIPS = 25  # number of unique clips to extract
TARGET_FPS = 30  # Will be set by framerate detection
CROP_TOP = 0
CROP_RIGHT = 0
CROP_BOTTOM = 0
CROP_LEFT = 0
USE_CABINET = True  # Whether to use cabinet PNG overlay
SPACING_MODE = "even"  # "even", "minimal", or "none"

# Cabinet/screen specifications (will be detected from PNG)
CABINET_PNG_WIDTH = 659
CABINET_PNG_HEIGHT = 741
SCREEN_X = 120  # pixels from left edge of PNG
SCREEN_Y = 154  # pixels from top edge of PNG
SCREEN_WIDTH = 420  # 4:3 aspect ratio
SCREEN_HEIGHT = 315

VIDEO_EXTENSIONS = {'.mp4', '.mov', '.avi', '.mkv', '.m4v', '.mpg', '.mpeg', '.wmv'}


def get_user_config():
    """Prompt user for configuration parameters."""
    global OUTPUT_WIDTH, OUTPUT_HEIGHT, MAX_GRID_SIZE, CLIP_DURATION
    global TOTAL_CLIPS, CROP_TOP, CROP_RIGHT, CROP_BOTTOM, CROP_LEFT, USE_CABINET, SPACING_MODE

    print("\n=== Cabinet Grid Screensaver Generator ===\n")

    # Ask about cabinet usage first
    print("Cabinet overlay:")
    cabinet_choice = input("Do you want to use a cabinet PNG overlay? [Y/n]: ").strip().lower()
    USE_CABINET = cabinet_choice != 'n'

    if USE_CABINET:
        print("  Cabinet mode enabled - clips will be composited inside PNG frame")
    else:
        print("  No cabinet - using raw video clips only")
    print()

    # Ask about spacing
    print("Video spacing:")
    print("  1) Even spacing (distributed gaps between and around videos)")
    print("  2) Minimal spacing (small uniform gap)")
    print("  3) No spacing (videos touch edges, maximize size)")

    spacing_map = {
        "1": "even",
        "2": "minimal",
        "3": "none"
    }

    while True:
        spacing_choice = input("Choose [1-3] (default: 1): ").strip() or "1"
        if spacing_choice in spacing_map:
            SPACING_MODE = spacing_map[spacing_choice]
            break
        else:
            print("Invalid choice. Please enter 1-3.")
    print()

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

    # Maximum grid size
    print("\nMaximum grid size:")
    print("  (e.g., 3 = 3x3 grid = 9 cabinets, 5 = 5x5 = 25 cabinets)")
    while True:
        grid_input = input("Max grid dimension (default: 5): ").strip()
        if not grid_input:
            MAX_GRID_SIZE = 5
            break
        try:
            MAX_GRID_SIZE = int(grid_input)
            if MAX_GRID_SIZE > 0:
                break
            else:
                print("Grid size must be positive.")
        except ValueError:
            print("Please enter a valid number.")

    # Number of unique clips
    max_clips_needed = MAX_GRID_SIZE * MAX_GRID_SIZE
    print(f"\nNumber of unique clips to extract:")
    print(f"  (Max grid size {MAX_GRID_SIZE}x{MAX_GRID_SIZE} = {max_clips_needed} cabinets)")
    print(f"  (Clips will loop if you extract fewer than {max_clips_needed})")
    while True:
        clips_input = input(f"Number of clips (default: {max_clips_needed}): ").strip()
        if not clips_input:
            TOTAL_CLIPS = max_clips_needed
            break
        try:
            TOTAL_CLIPS = int(clips_input)
            if TOTAL_CLIPS > 0:
                break
            else:
                print("Must extract at least 1 clip.")
        except ValueError:
            print("Please enter a valid number.")

    # Clip duration
    print("\nClip duration:")
    print("  (Clips will loop continuously while cabinet is visible)")
    while True:
        duration_input = input("Seconds per clip (default: 10): ").strip()
        if not duration_input:
            CLIP_DURATION = 10
            break
        try:
            CLIP_DURATION = float(duration_input)
            if CLIP_DURATION > 0:
                break
            else:
                print("Duration must be positive.")
        except ValueError:
            print("Please enter a valid number.")

    # Source video cropping
    print("\nSource video cropping (optional):")
    print("  Use this to remove unwanted areas from source videos")
    print("  (e.g., black bars, UI elements, watermarks)")

    crop_choice = input("\nDo you want to crop source videos? [y/N]: ").strip().lower()

    if crop_choice == 'y':
        print("\nEnter number of pixels to crop from each edge:")
        print("  (Press Enter to skip/leave at 0)")

        while True:
            try:
                top_input = input("  Top (default: 0): ").strip()
                CROP_TOP = int(top_input) if top_input else 0

                right_input = input("  Right (default: 0): ").strip()
                CROP_RIGHT = int(right_input) if right_input else 0

                bottom_input = input("  Bottom (default: 0): ").strip()
                CROP_BOTTOM = int(bottom_input) if bottom_input else 0

                left_input = input("  Left (default: 0): ").strip()
                CROP_LEFT = int(left_input) if left_input else 0

                if CROP_TOP >= 0 and CROP_RIGHT >= 0 and CROP_BOTTOM >= 0 and CROP_LEFT >= 0:
                    break
                else:
                    print("Crop values must be non-negative.")
            except ValueError:
                print("Please enter valid numbers.")

        if CROP_TOP or CROP_RIGHT or CROP_BOTTOM or CROP_LEFT:
            print(f"  Cropping: top={CROP_TOP}, right={CROP_RIGHT}, bottom={CROP_BOTTOM}, left={CROP_LEFT}")

    # Calculate video length
    # Sequence: 1x1, 2x2, 3x3, ..., NxN
    # Each state just holds (hard cuts between states)
    num_states = MAX_GRID_SIZE
    total_duration = num_states * HOLD_DURATION

    # Summary
    print("\n=== Configuration Summary ===")
    print(f"Output: {OUTPUT_WIDTH}x{OUTPUT_HEIGHT}")
    print(f"Grid sequence: 1x1 → 2x2 → 3x3 → ... → {MAX_GRID_SIZE}x{MAX_GRID_SIZE} (hard cuts)")
    print(f"Max grid: {MAX_GRID_SIZE}x{MAX_GRID_SIZE} ({MAX_GRID_SIZE * MAX_GRID_SIZE} videos)")
    print(f"Unique clips to extract: {TOTAL_CLIPS}")
    print(f"Clip duration: {CLIP_DURATION}s (will loop)")
    print(f"Hold duration: {HOLD_DURATION}s per state")
    print(f"Number of states: {num_states}")
    print(f"Estimated video length: {total_duration}s (~{total_duration/60:.1f} minutes)")
    print()

    confirm = input("Proceed with these settings? [Y/n]: ").strip().lower()
    if confirm and confirm != 'y':
        print("Aborted.")
        sys.exit(0)


def get_video_duration(video_path):
    """Get video duration using ffprobe."""
    cmd = [
        'ffprobe',
        '-v', 'error',
        '-show_entries', 'format=duration',
        '-of', 'json',
        str(video_path)
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        data = json.loads(result.stdout)
        return float(data['format']['duration'])
    except (subprocess.CalledProcessError, KeyError, ValueError, json.JSONDecodeError) as e:
        print(f"Warning: Could not get duration for {video_path}: {e}")
        return None


def get_video_framerate(video_path):
    """Get video framerate using ffprobe."""
    cmd = [
        'ffprobe',
        '-v', 'error',
        '-select_streams', 'v:0',
        '-show_entries', 'stream=r_frame_rate',
        '-of', 'json',
        str(video_path)
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        data = json.loads(result.stdout)
        fps_str = data['streams'][0]['r_frame_rate']
        num, den = map(int, fps_str.split('/'))
        fps = num / den
        return round(fps, 2)
    except (subprocess.CalledProcessError, KeyError, ValueError, json.JSONDecodeError, ZeroDivisionError, IndexError) as e:
        return None


def detect_common_framerate(video_files):
    """Detect the most common framerate among video files."""
    global TARGET_FPS

    print("\nDetecting framerates from source videos...")

    framerates = []
    sample_size = min(len(video_files), 10)

    for video_file in random.sample(video_files, sample_size):
        fps = get_video_framerate(video_file)
        if fps:
            framerates.append(fps)
            print(f"  {video_file.name}: {fps}fps")

    if not framerates:
        print("Warning: Could not detect any framerates, defaulting to 30fps")
        TARGET_FPS = 30
        return

    fps_counts = Counter(framerates)
    most_common_fps = fps_counts.most_common(1)[0][0]

    print(f"\nFramerate summary: {dict(fps_counts)}")
    print(f"Using most common framerate: {most_common_fps}fps")

    TARGET_FPS = most_common_fps


def get_image_dimensions(image_path):
    """Get image dimensions using ffprobe."""
    cmd = [
        'ffprobe',
        '-v', 'error',
        '-select_streams', 'v:0',
        '-show_entries', 'stream=width,height',
        '-of', 'json',
        str(image_path)
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        data = json.loads(result.stdout)
        width = data['streams'][0]['width']
        height = data['streams'][0]['height']
        return width, height
    except (subprocess.CalledProcessError, KeyError, ValueError, json.JSONDecodeError, IndexError) as e:
        print(f"Warning: Could not get dimensions for {image_path}: {e}")
        return None, None


def find_video_files(directory):
    """Find all video files in directory."""
    video_files = []
    for path in Path(directory).rglob('*'):
        if path.is_file() and path.suffix.lower() in VIDEO_EXTENSIONS:
            video_files.append(path)
    return video_files


def extract_clips(video_files, num_clips, output_dir):
    """Extract random clips from video files."""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    clips = []

    if USE_CABINET:
        clip_width, clip_height = SCREEN_WIDTH, SCREEN_HEIGHT
        print(f"\nExtracting {num_clips} clips at {clip_width}x{clip_height} (4:3 for cabinet), {TARGET_FPS}fps...")
    else:
        # Use 16:9 aspect ratio for non-cabinet mode
        clip_width, clip_height = 1920, 1080  # Will be scaled later based on grid
        print(f"\nExtracting {num_clips} clips at {clip_width}x{clip_height} (16:9), {TARGET_FPS}fps...")

    for i in range(num_clips):
        source_video = random.choice(video_files)
        duration = get_video_duration(source_video)

        if duration is None or duration < (CLIP_DURATION + 2 * AVOID_EDGES):
            print(f"Skipping {source_video.name} - too short or invalid")
            continue

        max_start = duration - CLIP_DURATION - AVOID_EDGES
        start_time = random.uniform(AVOID_EDGES, max_start)

        output_clip = output_dir / f"clip_{i:04d}.mp4"

        # Build video filter chain
        vf_filters = []

        # Add source crop if specified
        if CROP_TOP or CROP_RIGHT or CROP_BOTTOM or CROP_LEFT:
            crop_filter = f'crop=in_w-{CROP_LEFT}-{CROP_RIGHT}:in_h-{CROP_TOP}-{CROP_BOTTOM}:{CROP_LEFT}:{CROP_TOP}'
            vf_filters.append(crop_filter)

        # Scale and crop to appropriate aspect ratio
        vf_filters.append(f'scale={clip_width}:{clip_height}:force_original_aspect_ratio=increase')
        vf_filters.append(f'crop={clip_width}:{clip_height}')

        # Add fps filter
        vf_filters.append(f'fps={TARGET_FPS}')

        vf_string = ','.join(vf_filters)

        cmd = [
            'ffmpeg',
            '-ss', str(start_time),
            '-i', str(source_video),
            '-t', str(CLIP_DURATION),
            '-vf', vf_string,
            '-an',
            '-y',
            str(output_clip)
        ]

        print(f"Extracting clip {i+1}/{num_clips} from {source_video.name} at {start_time:.1f}s")

        try:
            subprocess.run(cmd, capture_output=True, check=True)
            clips.append(output_clip)
        except subprocess.CalledProcessError as e:
            print(f"Error extracting clip: {e}")
            continue

    return clips


def generate_grid_sequence():
    """Generate symmetrical grid sequence: 1x1 -> 2x2 -> 3x3 -> 4x4 -> 5x5"""
    sequence = []

    for size in range(1, MAX_GRID_SIZE + 1):
        sequence.append((size, size))

    return sequence


def create_looped_cabinet(video_clip, cabinet_png, output_file, duration):
    """Create a cabinet video (clip inside PNG) that loops for specified duration."""
    cabinets_dir = Path("cabinets_temp")
    cabinets_dir.mkdir(parents=True, exist_ok=True)

    # Step 1: Create a looped version of the clip using concat
    clip_duration = get_video_duration(video_clip)
    if not clip_duration:
        print(f"Error: Could not get duration for {video_clip}")
        return False

    num_loops = int(duration / clip_duration) + 2  # +2 for safety

    # Create concat file
    concat_file = cabinets_dir / f"concat_{Path(video_clip).stem}.txt"
    with open(concat_file, 'w') as f:
        for _ in range(num_loops):
            f.write(f"file '{Path(video_clip).absolute()}'\n")

    # Create looped clip
    looped_clip = cabinets_dir / f"looped_{Path(video_clip).stem}.mp4"

    concat_cmd = [
        'ffmpeg',
        '-f', 'concat',
        '-safe', '0',
        '-i', str(concat_file),
        '-t', str(duration),
        '-c', 'copy',
        '-y',
        str(looped_clip)
    ]

    try:
        subprocess.run(concat_cmd, capture_output=True, check=True)
    except subprocess.CalledProcessError as e:
        print(f"Error looping clip: {e}")
        return False

    # Verify looped clip was created
    if not looped_clip.exists():
        print(f"Error: Looped clip was not created: {looped_clip}")
        return False

    looped_duration = get_video_duration(looped_clip)
    if not looped_duration:
        print(f"Error: Could not verify looped clip duration")
        return False

    print(f"  Looped clip created: {looped_duration:.1f}s")

    # Step 2: Composite looped clip with cabinet PNG
    # Pad the clip to cabinet size first, then overlay PNG
    cmd = [
        'ffmpeg',
        '-i', str(looped_clip),
        '-i', str(cabinet_png),
        '-filter_complex',
        f'[0:v]scale={SCREEN_WIDTH}:{SCREEN_HEIGHT},pad={CABINET_PNG_WIDTH}:{CABINET_PNG_HEIGHT}:{SCREEN_X}:{SCREEN_Y}:black[padded];'
        f'[1:v]scale={CABINET_PNG_WIDTH}:{CABINET_PNG_HEIGHT}[frame];'
        f'[padded][frame]overlay=0:0[out]',
        '-map', '[out]',
        '-c:v', 'libx264',
        '-preset', 'ultrafast',
        '-crf', '23',
        '-r', str(TARGET_FPS),
        '-pix_fmt', 'yuv420p',
        '-t', str(duration),
        '-y',
        str(output_file)
    ]

    try:
        subprocess.run(cmd, capture_output=True, check=True)
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error creating cabinet composite: {e}")
        # Print stderr for debugging
        result = subprocess.run(cmd, capture_output=True, text=True)
        print(f"FFmpeg stderr: {result.stderr[-1000:]}")  # Last 1000 chars
        return False


def calculate_grid_layout(rows, cols):
    """
    Calculate video dimensions and positions for a grid layout.
    Returns: (video_width, video_height, positions_dict)
    where positions_dict maps video_index -> (x, y)
    """
    # Determine base video aspect ratio
    if USE_CABINET:
        video_width = CABINET_PNG_WIDTH
        video_height = CABINET_PNG_HEIGHT
    else:
        video_width = 1920
        video_height = 1080

    # Apply spacing mode to calculate scaled dimensions and gaps
    if SPACING_MODE == "none":
        # Maximize video size, no gaps
        available_width = OUTPUT_WIDTH / cols
        available_height = OUTPUT_HEIGHT / rows
        scale_factor_w = available_width / video_width
        scale_factor_h = available_height / video_height
        scale_factor = min(scale_factor_w, scale_factor_h)
        scaled_video_width = int(video_width * scale_factor)
        scaled_video_height = int(video_height * scale_factor)
        h_gap = 0
        v_gap = 0

    elif SPACING_MODE == "minimal":
        # Small uniform gap (10 pixels)
        gap_size = 10
        total_h_gaps = gap_size * (cols + 1)
        total_v_gaps = gap_size * (rows + 1)
        available_for_videos_w = OUTPUT_WIDTH - total_h_gaps
        available_for_videos_h = OUTPUT_HEIGHT - total_v_gaps
        scale_factor_w = (available_for_videos_w / cols) / video_width
        scale_factor_h = (available_for_videos_h / rows) / video_height
        scale_factor = min(scale_factor_w, scale_factor_h)
        scaled_video_width = int(video_width * scale_factor)
        scaled_video_height = int(video_height * scale_factor)
        h_gap = gap_size
        v_gap = gap_size

    else:  # "even"
        # Maximize video size, then distribute remaining space evenly
        available_width = OUTPUT_WIDTH / cols
        available_height = OUTPUT_HEIGHT / rows
        scale_factor_w = available_width / video_width
        scale_factor_h = available_height / video_height
        scale_factor = min(scale_factor_w, scale_factor_h) * 0.95  # Use 95% to leave room for gaps
        scaled_video_width = int(video_width * scale_factor)
        scaled_video_height = int(video_height * scale_factor)

        # Calculate total space used by videos
        total_video_width = scaled_video_width * cols
        total_video_height = scaled_video_height * rows

        # Calculate remaining space to distribute as gaps
        remaining_width = OUTPUT_WIDTH - total_video_width
        remaining_height = OUTPUT_HEIGHT - total_video_height

        # Distribute space evenly: gaps at edges and between videos
        h_gap = remaining_width / (cols + 1)
        v_gap = remaining_height / (rows + 1)

    # Calculate total grid dimensions
    total_grid_width = scaled_video_width * cols + h_gap * (cols - 1)
    total_grid_height = scaled_video_height * rows + v_gap * (rows - 1)

    # Calculate offset to center the entire grid
    offset_x = (OUTPUT_WIDTH - total_grid_width) / 2
    offset_y = (OUTPUT_HEIGHT - total_grid_height) / 2

    # Calculate positions for all videos in grid (centered)
    positions = {}
    for i in range(rows * cols):
        row = i // cols
        col = i % cols
        x = int(offset_x + col * (scaled_video_width + h_gap))
        y = int(offset_y + row * (scaled_video_height + v_gap))
        positions[i] = (x, y)

    return scaled_video_width, scaled_video_height, positions


def create_grid_segment(grid_videos, rows, cols, segment_duration, output_file, slide_from=None, prev_rows=None, prev_cols=None):
    """
    Create a segment showing a grid of videos with proper spacing and animations.

    Args:
        grid_videos: List of video paths to use (cabinets or raw clips)
        rows, cols: Grid dimensions for this segment
        segment_duration: How long this segment should be
        output_file: Where to save the segment
        slide_from: 'right' or 'bottom' for new videos sliding in, None for static
        prev_rows, prev_cols: Previous grid dimensions (for coordinated animations)
    """
    num_videos = rows * cols

    # Get layout for current and previous grid states
    scaled_video_width, scaled_video_height, positions = calculate_grid_layout(rows, cols)

    # Determine which videos are new vs existing
    prev_num_videos = 0
    prev_positions = {}
    if prev_rows and prev_cols:
        prev_num_videos = prev_rows * prev_cols
        # Get layout with previous grid dimensions
        prev_width, prev_height, prev_positions = calculate_grid_layout(prev_rows, prev_cols)

    # Build filter complex with animations
    filter_parts = []
    input_args = []

    # Create black canvas
    filter_parts.append(f'color=c=black:s={OUTPUT_WIDTH}x{OUTPUT_HEIGHT}:d={segment_duration}:r={TARGET_FPS}[base]')

    # Add videos as inputs
    for i in range(num_videos):
        video_idx = i % len(grid_videos)
        input_args.extend(['-i', str(grid_videos[video_idx])])

    # Scale videos to target size
    # Note: Smooth scale transitions are very difficult in FFmpeg due to expression limitations
    # For now, videos instantly resize but smoothly reposition
    for i in range(num_videos):
        filter_parts.append(f'[{i}:v]scale={scaled_video_width}:{scaled_video_height}[vid{i}]')

    # Overlay videos with position animations
    previous = '[base]'
    for i in range(num_videos):
        end_x, end_y = positions[i]

        if i == num_videos - 1:
            output = '[out]'
        else:
            output = f'[tmp{i}]'

        # Determine if this is a new video or existing one
        is_new = i >= prev_num_videos

        if slide_from is None or not (prev_rows and prev_cols):
            # Static (no animation) - first segment
            filter_parts.append(f'{previous}[vid{i}]overlay={end_x}:{end_y}{output}')
        else:
            # Animated segment
            if is_new:
                # New video slides in from off-screen
                if slide_from == 'right':
                    start_x = OUTPUT_WIDTH  # Off-screen right
                    start_y = end_y
                else:  # 'bottom'
                    start_x = end_x
                    start_y = OUTPUT_HEIGHT  # Off-screen bottom
            else:
                # Existing video moves from old position
                start_x, start_y = prev_positions[i]

            # Smoothstep easing: 3t² - 2t³
            # Expression: start + (end - start) * smoothstep(t / duration)
            t_norm = f't/{SLIDE_DURATION}'
            smoothstep = f'(3*pow({t_norm},2) - 2*pow({t_norm},3))'

            x_expr = f"'if(lt(t,{SLIDE_DURATION}), {start_x} + ({end_x} - {start_x}) * {smoothstep}, {end_x})'"
            y_expr = f"'if(lt(t,{SLIDE_DURATION}), {start_y} + ({end_y} - {start_y}) * {smoothstep}, {end_y})'"

            filter_parts.append(f'{previous}[vid{i}]overlay=x={x_expr}:y={y_expr}{output}')

        previous = output

    filter_complex = ';'.join(filter_parts)

    cmd = [
        'ffmpeg',
        *input_args,
        '-filter_complex', filter_complex,
        '-map', '[out]',
        '-t', str(segment_duration),
        '-c:v', 'libx264',
        '-preset', 'ultrafast',
        '-crf', '23',
        '-r', str(TARGET_FPS),
        '-pix_fmt', 'yuv420p',
        '-y',
        str(output_file)
    ]

    try:
        subprocess.run(cmd, capture_output=True, check=True)
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error creating grid segment: {e}")
        # Print stderr for debugging
        result = subprocess.run(cmd, capture_output=True, text=True)
        print(f"FFmpeg stderr: {result.stderr[-2000:]}")  # Last 2000 chars
        return False


def main():
    if len(sys.argv) < 3:
        print("Usage: python generate_cabinet_grid.py <video_directory> <cabinet_png> [output_file]")
        print("\nExample: python generate_cabinet_grid.py ./games cabinet.png cabinet_grid.mp4")
        sys.exit(1)

    video_dir = sys.argv[1]
    cabinet_png = sys.argv[2]
    output_file = sys.argv[3] if len(sys.argv) > 3 else "cabinet_grid.mp4"

    if not os.path.isdir(video_dir):
        print(f"Error: Directory not found: {video_dir}")
        sys.exit(1)

    if not os.path.isfile(cabinet_png):
        print(f"Error: Cabinet PNG not found: {cabinet_png}")
        sys.exit(1)

    # Detect cabinet PNG dimensions
    global CABINET_PNG_WIDTH, CABINET_PNG_HEIGHT
    png_width, png_height = get_image_dimensions(cabinet_png)
    if png_width and png_height:
        CABINET_PNG_WIDTH = png_width
        CABINET_PNG_HEIGHT = png_height
        print(f"Detected cabinet PNG dimensions: {CABINET_PNG_WIDTH}x{CABINET_PNG_HEIGHT}")
    else:
        print(f"Using default cabinet dimensions: {CABINET_PNG_WIDTH}x{CABINET_PNG_HEIGHT}")

    # Get user configuration
    get_user_config()

    print(f"\nScanning for videos in: {video_dir}")
    video_files = find_video_files(video_dir)

    if not video_files:
        print("Error: No video files found")
        sys.exit(1)

    print(f"Found {len(video_files)} video files")

    # Detect common framerate
    detect_common_framerate(video_files)

    # Extract clips
    clips_dir = Path("clips_temp")
    clips = extract_clips(video_files, TOTAL_CLIPS, clips_dir)

    if not clips:
        print("Error: No clips extracted")
        sys.exit(1)

    print(f"\nSuccessfully extracted {len(clips)} clips")

    # Generate grid sequence
    grid_sequence = generate_grid_sequence()
    print(f"\nGrid sequence: {' → '.join([f'{r}x{c}' for r, c in grid_sequence])}")

    # Calculate total duration for looped videos
    total_duration = len(grid_sequence) * HOLD_DURATION

    if USE_CABINET:
        # Create looped cabinet videos
        cabinets_dir = Path("cabinets_temp")
        cabinets_dir.mkdir(parents=True, exist_ok=True)

        print(f"\nCreating {len(clips)} looped cabinet videos...")
        grid_videos = []

        for i, clip in enumerate(clips):
            cabinet_file = cabinets_dir / f"cabinet_{i:04d}.mp4"
            print(f"Creating cabinet {i+1}/{len(clips)}...")

            if create_looped_cabinet(clip, cabinet_png, cabinet_file, total_duration):
                grid_videos.append(cabinet_file)
            else:
                print(f"Failed to create cabinet {i}")
                sys.exit(1)

        print(f"\n✓ Created {len(grid_videos)} cabinet videos")
    else:
        # Just loop the raw clips without cabinet overlay
        print(f"\nCreating {len(clips)} looped videos (no cabinet)...")
        grid_videos = []

        for i, clip in enumerate(clips):
            looped_file = Path("cabinets_temp") / f"looped_{i:04d}.mp4"
            looped_file.parent.mkdir(parents=True, exist_ok=True)

            clip_duration = get_video_duration(clip)
            if not clip_duration:
                print(f"Error: Could not get duration for {clip}")
                sys.exit(1)

            num_loops = int(total_duration / clip_duration) + 2

            # Create concat file
            concat_file = looped_file.parent / f"concat_{i:04d}.txt"
            with open(concat_file, 'w') as f:
                for _ in range(num_loops):
                    f.write(f"file '{Path(clip).absolute()}'\n")

            # Loop the clip
            cmd = [
                'ffmpeg',
                '-f', 'concat',
                '-safe', '0',
                '-i', str(concat_file),
                '-t', str(total_duration),
                '-c', 'copy',
                '-y',
                str(looped_file)
            ]

            print(f"Looping clip {i+1}/{len(clips)}...")

            try:
                subprocess.run(cmd, capture_output=True, check=True)
                grid_videos.append(looped_file)
            except subprocess.CalledProcessError as e:
                print(f"Error looping clip {i}: {e}")
                sys.exit(1)

        print(f"\n✓ Created {len(grid_videos)} looped videos")

    # Create segments for each grid state
    segments_dir = Path("segments_temp")
    segments_dir.mkdir(parents=True, exist_ok=True)

    print(f"\nGenerating segments for {len(grid_sequence)} grid states...")
    segment_files = []

    for idx, (rows, cols) in enumerate(grid_sequence):
        print(f"Creating segment {idx+1}/{len(grid_sequence)}: {rows}x{cols} grid...")

        # Create segment (static grid, hard cuts between states)
        segment_file = segments_dir / f"segment_{idx:03d}_{rows}x{cols}.mp4"

        if not create_grid_segment(grid_videos, rows, cols, HOLD_DURATION, segment_file, None, None, None):
            print(f"Failed to create segment {idx}")
            sys.exit(1)
        segment_files.append(segment_file)

    print(f"\n✓ Created {len(segment_files)} segments")

    # Concatenate segments
    print("\nConcatenating segments...")
    concat_list = segments_dir / "concat_list.txt"
    with open(concat_list, 'w') as f:
        for segment in segment_files:
            f.write(f"file '{segment.absolute()}'\n")

    cmd = [
        'ffmpeg',
        '-f', 'concat',
        '-safe', '0',
        '-i', str(concat_list),
        '-c', 'copy',
        '-y',
        str(output_file)
    ]

    try:
        subprocess.run(cmd, check=True)
        print(f"\n✓ Final video created: {output_file}")
    except subprocess.CalledProcessError as e:
        print(f"\n✗ Error concatenating segments: {e}")
        sys.exit(1)

    print("\n✓ Done!")
    print(f"\nTo clean up temporary files:")
    print(f"  rm -rf {clips_dir}")
    print(f"  rm -rf cabinets_temp")
    print(f"  rm -rf {segments_dir}")


if __name__ == '__main__':
    main()
