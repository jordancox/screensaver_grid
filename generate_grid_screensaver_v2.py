#!/usr/bin/env python3
"""
Generate a grid screensaver with staggered clip changes.
Each clip plays for CLIP_DURATION seconds, grid positions change left-to-right,
top-to-bottom every CHANGE_INTERVAL seconds.

V2: Adds automatic framerate detection - uses the most common framerate from source videos.
"""

import os
import sys
import json
import random
import subprocess
from pathlib import Path
from collections import Counter

# Configuration (set by user prompts or defaults)
USE_PRECUT_CLIPS = False  # Mode 2: use pre-cut clips instead of extracting from long videos
CLIP_DURATION = 10  # seconds
CHANGE_INTERVAL = 2  # seconds between position changes
GRID_ROWS = 4
GRID_COLS = 4
TOTAL_POSITIONS = GRID_ROWS * GRID_COLS  # 16
OUTPUT_WIDTH = 1920
OUTPUT_HEIGHT = 1080
CELL_WIDTH = OUTPUT_WIDTH // GRID_COLS  # 480
CELL_HEIGHT = OUTPUT_HEIGHT // GRID_ROWS  # 270
AVOID_EDGES = 10  # avoid first/last N seconds of source videos
TOTAL_CLIPS = 300
TARGET_FPS = 30  # Will be set by framerate detection

VIDEO_EXTENSIONS = {'.mp4', '.mov', '.avi', '.mkv', '.m4v', '.mpg', '.mpeg', '.wmv'}


def get_user_config():
    """Prompt user for configuration parameters."""
    global OUTPUT_WIDTH, OUTPUT_HEIGHT, GRID_ROWS, GRID_COLS, TOTAL_POSITIONS
    global CELL_WIDTH, CELL_HEIGHT, TOTAL_CLIPS, CLIP_DURATION, CHANGE_INTERVAL
    global USE_PRECUT_CLIPS

    print("\n=== Grid Screensaver Generator V2 ===\n")

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
    print("  Examples: 2x2 (4 videos), 3x3 (9 videos), 4x4 (16 videos), 5x5 (25 videos)")
    while True:
        grid_input = input("Enter grid size (e.g., 4x4) (default: 4x4): ").strip() or "4x4"
        try:
            rows, cols = grid_input.lower().split('x')
            GRID_ROWS = int(rows)
            GRID_COLS = int(cols)
            if GRID_ROWS > 0 and GRID_COLS > 0:
                TOTAL_POSITIONS = GRID_ROWS * GRID_COLS
                break
            else:
                print("Grid dimensions must be positive numbers.")
        except (ValueError, AttributeError):
            print("Invalid format. Please use format like '4x4'")

    CELL_WIDTH = OUTPUT_WIDTH // GRID_COLS
    CELL_HEIGHT = OUTPUT_HEIGHT // GRID_ROWS

    # Mode selection
    print("\nClip mode:")
    print("  1) Extract from long videos (random segments)")
    print("  2) Use pre-cut clips (e.g. from Resolve scene cuts)")
    while True:
        mode_choice = input("Choose [1-2] (default: 1): ").strip() or "1"
        if mode_choice == "1":
            USE_PRECUT_CLIPS = False
            break
        elif mode_choice == "2":
            USE_PRECUT_CLIPS = True
            break
        else:
            print("Invalid choice. Please enter 1 or 2.")

    if USE_PRECUT_CLIPS:
        # Pre-cut clips mode: only need max clip duration
        print("\nMax clip duration:")
        print("  (Clips longer than this will be trimmed; shorter clips will be skipped)")
        while True:
            duration_input = input("Seconds (default: 10): ").strip()
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

        # Summary for pre-cut mode
        print("\n=== Configuration Summary ===")
        print(f"Mode: Pre-cut clips")
        print(f"Output: {OUTPUT_WIDTH}x{OUTPUT_HEIGHT}")
        print(f"Grid: {GRID_ROWS}x{GRID_COLS} ({TOTAL_POSITIONS} positions)")
        print(f"Cell size: {CELL_WIDTH}x{CELL_HEIGHT}")
        print(f"Max clip duration: {CLIP_DURATION}s")
        print(f"Total clips: determined by source directory")
        print()

        confirm = input("Proceed with these settings? [Y/n]: ").strip().lower()
        if confirm and confirm != 'y':
            print("Aborted.")
            sys.exit(0)
    else:
        # Original mode: extract from long videos
        # Total clips
        print(f"\nTotal number of clips to extract:")
        print(f"  (Grid has {TOTAL_POSITIONS} positions. Suggest multiples of {TOTAL_POSITIONS} for complete cycles)")
        while True:
            clips_input = input(f"Enter number of clips (default: {TOTAL_POSITIONS * 5}): ").strip()
            if not clips_input:
                TOTAL_CLIPS = TOTAL_POSITIONS * 5
                break
            try:
                TOTAL_CLIPS = int(clips_input)
                if TOTAL_CLIPS >= TOTAL_POSITIONS:
                    break
                else:
                    print(f"Need at least {TOTAL_POSITIONS} clips for one full cycle.")
            except ValueError:
                print("Please enter a valid number.")

        # Clip duration and change interval with validation
        while True:
            # Clip duration
            print("\nClip duration:")
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

            # Change interval
            print("\nChange interval:")
            print("  (Time between each grid position changing)")
            while True:
                interval_input = input("Seconds between changes (default: 2): ").strip()
                if not interval_input:
                    CHANGE_INTERVAL = 2
                    break
                try:
                    CHANGE_INTERVAL = float(interval_input)
                    if CHANGE_INTERVAL > 0:
                        break
                    else:
                        print("Interval must be positive.")
                except ValueError:
                    print("Please enter a valid number.")

            # Validate timing
            full_cycle_time = TOTAL_POSITIONS * CHANGE_INTERVAL

            if CLIP_DURATION < full_cycle_time:
                print(f"\n⚠️  WARNING: Timing issue detected!")
                print(f"   Grid has {TOTAL_POSITIONS} positions")
                print(f"   Full cycle time: {full_cycle_time}s ({TOTAL_POSITIONS} positions × {CHANGE_INTERVAL}s)")
                print(f"   Clip duration: {CLIP_DURATION}s")
                print(f"\n   Problem: Clips will end before the next clip arrives in that position.")
                print(f"   Each position will show black/frozen frames for {full_cycle_time - CLIP_DURATION:.1f}s")
                print(f"\n   Solutions:")
                print(f"   1) Increase clip duration to at least {full_cycle_time}s")
                print(f"   2) Decrease change interval to at most {CLIP_DURATION / TOTAL_POSITIONS:.2f}s")
                print(f"   3) Use a smaller grid")

                choice = input("\nDo you want to adjust these values? [Y/n]: ").strip().lower()
                if not choice or choice == 'y':
                    continue  # Loop back to re-enter clip duration and interval
                else:
                    print("Proceeding anyway (you'll see gaps in playback)...")
                    break
            else:
                # Timing is good
                break

        # Summary
        num_cycles = TOTAL_CLIPS // TOTAL_POSITIONS
        cycle_duration = TOTAL_POSITIONS * CHANGE_INTERVAL
        total_duration = num_cycles * cycle_duration

        print("\n=== Configuration Summary ===")
        print(f"Mode: Extract from long videos")
        print(f"Output: {OUTPUT_WIDTH}x{OUTPUT_HEIGHT}")
        print(f"Grid: {GRID_ROWS}x{GRID_COLS} ({TOTAL_POSITIONS} positions)")
        print(f"Cell size: {CELL_WIDTH}x{CELL_HEIGHT}")
        print(f"Total clips: {TOTAL_CLIPS}")
        print(f"Clip duration: {CLIP_DURATION}s")
        print(f"Change interval: {CHANGE_INTERVAL}s")
        print(f"Complete cycles: {num_cycles}")
        print(f"Full cycle duration: {cycle_duration}s")
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
        # Parse fraction like "30000/1001" or "30/1"
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
    sample_size = min(len(video_files), 10)  # Sample up to 10 files for speed

    for video_file in random.sample(video_files, sample_size):
        fps = get_video_framerate(video_file)
        if fps:
            framerates.append(fps)
            print(f"  {video_file.name}: {fps}fps")

    if not framerates:
        print("Warning: Could not detect any framerates, defaulting to 30fps")
        TARGET_FPS = 30
        return

    # Count occurrences of each framerate
    fps_counts = Counter(framerates)
    most_common_fps = fps_counts.most_common(1)[0][0]

    print(f"\nFramerate summary: {dict(fps_counts)}")
    print(f"Using most common framerate: {most_common_fps}fps")

    TARGET_FPS = most_common_fps


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

    print(f"\nExtracting {num_clips} clips at {TARGET_FPS}fps...")

    for i in range(num_clips):
        # Randomly select a source video
        source_video = random.choice(video_files)
        duration = get_video_duration(source_video)

        if duration is None or duration < (CLIP_DURATION + 2 * AVOID_EDGES):
            print(f"Skipping {source_video.name} - too short or invalid")
            continue

        # Random start time, avoiding edges
        max_start = duration - CLIP_DURATION - AVOID_EDGES
        start_time = random.uniform(AVOID_EDGES, max_start)

        # Output clip filename
        output_clip = output_dir / f"clip_{i:04d}.mp4"

        # Extract clip using ffmpeg with target framerate
        cmd = [
            'ffmpeg',
            '-ss', str(start_time),
            '-i', str(source_video),
            '-t', str(CLIP_DURATION),
            '-vf', f'scale={CELL_WIDTH}:{CELL_HEIGHT}:force_original_aspect_ratio=increase,crop={CELL_WIDTH}:{CELL_HEIGHT},fps={TARGET_FPS}',
            '-an',  # no audio
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


def prepare_precut_clips(video_files, output_dir):
    """Prepare pre-cut clips by trimming to max duration and scaling to cell size."""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    clips = []
    skipped = 0

    print(f"\nPreparing pre-cut clips (max {CLIP_DURATION}s each) at {TARGET_FPS}fps...")

    for i, source_video in enumerate(sorted(video_files)):
        duration = get_video_duration(source_video)

        if duration is None:
            print(f"  Skipping {source_video.name} - could not read duration")
            skipped += 1
            continue

        if duration < CLIP_DURATION:
            print(f"  Skipping {source_video.name} - too short ({duration:.1f}s < {CLIP_DURATION}s)")
            skipped += 1
            continue

        output_clip = output_dir / f"clip_{len(clips):04d}.mp4"

        cmd = [
            'ffmpeg',
            '-i', str(source_video),
            '-t', str(CLIP_DURATION),
            '-vf', f'scale={CELL_WIDTH}:{CELL_HEIGHT}:force_original_aspect_ratio=increase,crop={CELL_WIDTH}:{CELL_HEIGHT},fps={TARGET_FPS}',
            '-an',
            '-y',
            str(output_clip)
        ]

        print(f"  [{len(clips)+1}] {source_video.name} ({duration:.1f}s) -> trimmed to {CLIP_DURATION}s")

        try:
            subprocess.run(cmd, capture_output=True, check=True)
            clips.append(output_clip)
        except subprocess.CalledProcessError as e:
            print(f"  Error processing {source_video.name}: {e}")
            skipped += 1
            continue

    print(f"\nPrepared {len(clips)} clips, skipped {skipped}")

    if len(clips) < TOTAL_POSITIONS:
        print(f"WARNING: Only {len(clips)} clips available but grid has {TOTAL_POSITIONS} positions.")
        print(f"  Some grid cells will be empty/black.")

    return clips


def concatenate_position_clips(clips, position_clips_dir):
    """Concatenate clips for each grid position into 16 longer videos.
    This avoids hitting file descriptor limits."""

    position_clips_dir = Path(position_clips_dir)
    position_clips_dir.mkdir(parents=True, exist_ok=True)

    # For each grid position, determine which clips go there
    position_clips = [[] for _ in range(TOTAL_POSITIONS)]

    for clip_idx, clip_path in enumerate(clips):
        position = clip_idx % TOTAL_POSITIONS
        position_clips[position].append(clip_path)

    position_videos = []

    print(f"\nConcatenating clips for each of the {TOTAL_POSITIONS} grid positions...")

    for pos in range(TOTAL_POSITIONS):
        clips_for_position = position_clips[pos]

        if not clips_for_position:
            print(f"Warning: No clips for position {pos}")
            continue

        position_video = position_clips_dir / f"position_{pos:02d}.mp4"

        # Create concat file list
        concat_list = position_clips_dir / f"concat_list_{pos:02d}.txt"
        with open(concat_list, 'w') as f:
            for clip in clips_for_position:
                f.write(f"file '{clip.absolute()}'\n")

        # Concatenate all clips for this position
        cmd = [
            'ffmpeg',
            '-f', 'concat',
            '-safe', '0',
            '-i', str(concat_list),
            '-c', 'copy',
            '-y',
            str(position_video)
        ]

        print(f"Position {pos}: concatenating {len(clips_for_position)} clips...")

        try:
            subprocess.run(cmd, capture_output=True, check=True)
            position_videos.append(position_video)
        except subprocess.CalledProcessError as e:
            print(f"Error concatenating position {pos}: {e}")
            sys.exit(1)

    return position_videos


def generate_grid_video(position_videos, output_file):
    """Generate the staggered grid video using FFmpeg.
    Uses overlay filters with timing to avoid padding issues."""

    print(f"\nGenerating final grid video from {len(position_videos)} position streams...")

    # Calculate total video duration
    # We need to know how long the final video should be
    # The longest position stream determines this
    # Position 0 starts at 0s, position 15 starts at 30s
    # Each position plays its concatenated clips
    # We need the duration of the longest position video

    # Get duration of first position video (they should all be similar length)
    first_duration = get_video_duration(position_videos[0])
    if first_duration is None:
        print("Error: Could not determine position video duration")
        sys.exit(1)

    # All positions start simultaneously, so duration matches the position videos
    total_duration = first_duration

    print(f"Total output duration: {total_duration:.1f}s")

    # New approach: Use a black canvas as base, then overlay each position with timing
    filter_parts = []
    input_args = []

    # Create a black base canvas with target framerate
    base_canvas = f"color=c=black:s={OUTPUT_WIDTH}x{OUTPUT_HEIGHT}:d={total_duration}:r={TARGET_FPS}[base]"
    filter_parts.append(base_canvas)

    # Add position videos as inputs
    for pos_video in position_videos:
        input_args.extend(['-i', str(pos_video)])

    # Overlay each position at the correct location and time
    previous_stream = "[base]"

    for pos in range(len(position_videos)):
        row = pos // GRID_COLS
        col = pos % GRID_COLS
        x = col * CELL_WIDTH
        y = row * CELL_HEIGHT
        if pos < len(position_videos) - 1:
            output_stream = f"[tmp{pos}]"
        else:
            output_stream = "[out]"

        overlay_filter = f"{previous_stream}[{pos}:v]overlay=x={x}:y={y}{output_stream}"
        filter_parts.append(overlay_filter)
        previous_stream = output_stream

    # Combine all filter parts
    filter_complex = ';'.join(filter_parts)

    # Build final ffmpeg command
    cmd = [
        'ffmpeg',
        *input_args,
        '-filter_complex', filter_complex,
        '-map', '[out]',
        '-t', str(total_duration),
        '-c:v', 'libx264',
        '-preset', 'medium',
        '-crf', '23',
        '-pix_fmt', 'yuv420p',
        '-r', str(TARGET_FPS),  # Set output framerate
        '-y',
        str(output_file)
    ]

    print(f"\nRunning final FFmpeg render at {TARGET_FPS}fps (this will take a while)...")

    # Write command to file for debugging
    with open('ffmpeg_command.txt', 'w') as f:
        f.write(' '.join(cmd))
    print("FFmpeg command saved to ffmpeg_command.txt")

    try:
        subprocess.run(cmd, check=True)
        print(f"\n✓ Grid video created: {output_file}")
    except subprocess.CalledProcessError as e:
        print(f"\n✗ Error creating grid video: {e}")
        sys.exit(1)


def main():
    if len(sys.argv) < 2:
        print("Usage: python generate_grid_screensaver_v2.py <video_directory> [output_file]")
        print("\nExample: python generate_grid_screensaver_v2.py ./movies screensaver.mp4")
        sys.exit(1)

    video_dir = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else "screensaver_grid.mp4"

    if not os.path.isdir(video_dir):
        print(f"Error: Directory not found: {video_dir}")
        sys.exit(1)

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

    # Extract or prepare clips
    clips_dir = Path("clips_temp")

    if USE_PRECUT_CLIPS:
        clips = prepare_precut_clips(video_files, clips_dir)
    else:
        clips = extract_clips(video_files, TOTAL_CLIPS, clips_dir)

    if len(clips) < TOTAL_POSITIONS:
        print(f"Error: Only got {len(clips)} clips, need at least {TOTAL_POSITIONS}")
        sys.exit(1)

    print(f"\nSuccessfully prepared {len(clips)} clips")

    # Concatenate clips for each position
    position_clips_dir = Path("position_videos_temp")
    position_videos = concatenate_position_clips(clips, position_clips_dir)

    # Generate grid video
    generate_grid_video(position_videos, output_file)

    print("\n✓ Done!")
    print(f"\nTo clean up temporary files:")
    print(f"  rm -rf {clips_dir}")
    print(f"  rm -rf {position_clips_dir}")


if __name__ == '__main__':
    main()
