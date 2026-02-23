#!/usr/bin/env python3
"""
Generate a grid screensaver with staggered clip changes.
Each clip plays for CLIP_DURATION seconds, grid positions change left-to-right,
top-to-bottom every CHANGE_INTERVAL seconds.
"""

import os
import sys
import json
import random
import subprocess
from pathlib import Path

# Configuration (set by user prompts or defaults)
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

VIDEO_EXTENSIONS = {'.mp4', '.mov', '.avi', '.mkv', '.m4v', '.mpg', '.mpeg', '.wmv'}


def get_user_config():
    """Prompt user for configuration parameters."""
    global OUTPUT_WIDTH, OUTPUT_HEIGHT, GRID_ROWS, GRID_COLS, TOTAL_POSITIONS
    global CELL_WIDTH, CELL_HEIGHT, TOTAL_CLIPS, CLIP_DURATION, CHANGE_INTERVAL

    print("\n=== Grid Screensaver Generator ===\n")

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

    print(f"Extracting {num_clips} clips...")

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

        # Extract clip using ffmpeg
        cmd = [
            'ffmpeg',
            '-ss', str(start_time),
            '-i', str(source_video),
            '-t', str(CLIP_DURATION),
            '-vf', f'scale={CELL_WIDTH}:{CELL_HEIGHT}:force_original_aspect_ratio=increase,crop={CELL_WIDTH}:{CELL_HEIGHT}',
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

    # Total duration = last position delay + clip duration
    max_delay = (TOTAL_POSITIONS - 1) * CHANGE_INTERVAL
    total_duration = max_delay + first_duration

    print(f"Total output duration: {total_duration:.1f}s")

    # New approach: Use a black canvas as base, then overlay each position with timing
    filter_parts = []
    input_args = []

    # Create a black base canvas
    base_canvas = f"color=c=black:s={OUTPUT_WIDTH}x{OUTPUT_HEIGHT}:d={total_duration}:r=30[base]"
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
        delay = pos * CHANGE_INTERVAL

        if pos < len(position_videos) - 1:
            output_stream = f"[tmp{pos}]"
        else:
            output_stream = "[out]"

        # Overlay with enable expression to start at the right time
        overlay_filter = f"{previous_stream}[{pos}:v]overlay=x={x}:y={y}:enable='gte(t,{delay})'{output_stream}"
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
        '-y',
        str(output_file)
    ]

    print(f"\nRunning final FFmpeg render (this will take a while)...")

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
        print("Usage: python generate_grid_screensaver.py <video_directory> [output_file]")
        print("\nExample: python generate_grid_screensaver.py ./movies screensaver.mp4")
        sys.exit(1)

    video_dir = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else "screensaver_grid.mp4"

    if not os.path.isdir(video_dir):
        print(f"Error: Directory not found: {video_dir}")
        sys.exit(1)

    # Get user configuration
    get_user_config()

    print(f"Scanning for videos in: {video_dir}")
    video_files = find_video_files(video_dir)

    if not video_files:
        print("Error: No video files found")
        sys.exit(1)

    print(f"Found {len(video_files)} video files")

    # Extract clips
    clips_dir = Path("clips_temp")
    clips = extract_clips(video_files, TOTAL_CLIPS, clips_dir)

    if len(clips) < TOTAL_POSITIONS:
        print(f"Error: Only extracted {len(clips)} clips, need at least {TOTAL_POSITIONS}")
        sys.exit(1)

    print(f"\nSuccessfully extracted {len(clips)} clips")

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
