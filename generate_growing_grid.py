#!/usr/bin/env python3
"""
Generate a growing/shrinking grid screensaver.
Starts with 1 video fullscreen, grows to NxN grid, then shrinks back to 1.
Includes framerate detection and looping clips.
"""

import os
import sys
import json
import random
import subprocess
import math
from pathlib import Path
from collections import Counter

# Configuration (set by user prompts)
OUTPUT_WIDTH = 1920
OUTPUT_HEIGHT = 1080
TOTAL_VIDEO_LENGTH = 120  # seconds
MAX_GRID_SIZE = 10  # e.g., 10x10 grid
CLIP_DURATION = 10  # seconds per clip
TRANSITION_TYPE = "cut"  # cut, fade, zoom
AVOID_EDGES = 10  # avoid first/last N seconds of source videos
TOTAL_CLIPS = 100  # number of unique clips to extract
TARGET_FPS = 30  # Will be set by framerate detection
CROP_TOP = 0  # pixels to crop from top
CROP_RIGHT = 0  # pixels to crop from right
CROP_BOTTOM = 0  # pixels to crop from bottom
CROP_LEFT = 0  # pixels to crop from left
CRT_EFFECT = "off"  # off, light, medium, heavy

VIDEO_EXTENSIONS = {'.mp4', '.mov', '.avi', '.mkv', '.m4v', '.mpg', '.mpeg', '.wmv'}


def get_user_config():
    """Prompt user for configuration parameters."""
    global OUTPUT_WIDTH, OUTPUT_HEIGHT, TOTAL_VIDEO_LENGTH, MAX_GRID_SIZE
    global CLIP_DURATION, TRANSITION_TYPE, TOTAL_CLIPS
    global CROP_TOP, CROP_RIGHT, CROP_BOTTOM, CROP_LEFT, CRT_EFFECT

    print("\n=== Growing/Shrinking Grid Screensaver Generator ===\n")

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

    # Total video length
    print("\nTotal video length:")
    while True:
        length_input = input("Total seconds (default: 120): ").strip()
        if not length_input:
            TOTAL_VIDEO_LENGTH = 120
            break
        try:
            TOTAL_VIDEO_LENGTH = float(length_input)
            if TOTAL_VIDEO_LENGTH > 0:
                break
            else:
                print("Length must be positive.")
        except ValueError:
            print("Please enter a valid number.")

    # Maximum grid size
    print("\nMaximum grid size:")
    print("  (e.g., 10 = grows to 10x10 grid = 100 videos)")
    while True:
        grid_input = input("Max grid dimension (default: 10): ").strip()
        if not grid_input:
            MAX_GRID_SIZE = 10
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
    print(f"  (Max grid size {MAX_GRID_SIZE}x{MAX_GRID_SIZE} = {max_clips_needed} videos)")
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
    print("  (Clips will loop to fill the entire video duration)")
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

    # Transition type
    print("\nTransition type when grid size changes:")
    print("  1) Cut (instant)")
    print("  2) Fade (smooth crossfade)")
    print("  3) Circleopen (expanding circle)")
    print("  4) Circleclose (contracting circle)")
    print("  5) Wipeleft (wipe left)")
    print("  6) Wiperight (wipe right)")
    print("  7) Fadeblack (fade through black)")
    print("  8) Radial (radial wipe)")

    transition_map = {
        "1": "cut",
        "2": "fade",
        "3": "circleopen",
        "4": "circleclose",
        "5": "wipeleft",
        "6": "wiperight",
        "7": "fadeblack",
        "8": "radial"
    }

    while True:
        trans_choice = input("Choose [1-8] (default: 1): ").strip() or "1"
        if trans_choice in transition_map:
            TRANSITION_TYPE = transition_map[trans_choice]
            break
        else:
            print("Invalid choice. Please enter 1-8.")

    # Source video cropping
    print("\nSource video cropping (optional):")
    print("  Use this to remove unwanted areas from source videos")
    print("  (e.g., black bars, UI elements, overlays)")

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

    # CRT effect
    print("\nCRT effect (curved screen + scanlines):")
    print("  1) Off (no effect)")
    print("  2) Light (subtle curve + faint scanlines)")
    print("  3) Medium (moderate curve + visible scanlines)")
    print("  4) Heavy (strong curve + prominent scanlines)")

    crt_map = {
        "1": "off",
        "2": "light",
        "3": "medium",
        "4": "heavy"
    }

    while True:
        crt_choice = input("Choose [1-4] (default: 1): ").strip() or "1"
        if crt_choice in crt_map:
            CRT_EFFECT = crt_map[crt_choice]
            break
        else:
            print("Invalid choice. Please enter 1-4.")

    # Calculate grid sequence
    grid_sequence = []
    for size in range(1, MAX_GRID_SIZE + 1):
        grid_sequence.append(size * size)
    for size in range(MAX_GRID_SIZE - 1, 0, -1):
        grid_sequence.append(size * size)

    total_grid_states = len(grid_sequence)
    time_per_state = TOTAL_VIDEO_LENGTH / total_grid_states

    # Summary
    print("\n=== Configuration Summary ===")
    print(f"Output: {OUTPUT_WIDTH}x{OUTPUT_HEIGHT}")
    print(f"Total video length: {TOTAL_VIDEO_LENGTH}s")
    print(f"Max grid: {MAX_GRID_SIZE}x{MAX_GRID_SIZE} ({MAX_GRID_SIZE * MAX_GRID_SIZE} videos)")
    print(f"Unique clips to extract: {TOTAL_CLIPS}")
    print(f"Clip duration: {CLIP_DURATION}s (will loop)")
    print(f"Transition: {TRANSITION_TYPE}")
    print(f"Grid sequence: 1 → {MAX_GRID_SIZE * MAX_GRID_SIZE} → 1")
    print(f"Total grid states: {total_grid_states}")
    print(f"Time per grid state: {time_per_state:.1f}s")
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


def get_crt_filter():
    """Get CRT effect filter based on preset."""
    if CRT_EFFECT == "off":
        return None
    elif CRT_EFFECT == "light":
        # Subtle curve + faint scanlines
        return "lenscorrection=k1=-0.15:k2=-0.05,geq='lum=lum(X,Y)*if(mod(Y,2),0.9,1):cb=cb(X,Y):cr=cr(X,Y)'"
    elif CRT_EFFECT == "medium":
        # Moderate curve + visible scanlines
        return "lenscorrection=k1=-0.3:k2=-0.15,geq='lum=lum(X,Y)*if(mod(Y,2),0.8,1):cb=cb(X,Y):cr=cr(X,Y)'"
    elif CRT_EFFECT == "heavy":
        # Strong curve + prominent scanlines
        return "lenscorrection=k1=-0.5:k2=-0.25,geq='lum=lum(X,Y)*if(mod(Y,2),0.65,1):cb=cb(X,Y):cr=cr(X,Y)'"
    return None


def extract_clips(video_files, num_clips, output_dir, cell_width, cell_height):
    """Extract random clips from video files."""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    clips = []

    crt_suffix = f" with {CRT_EFFECT} CRT effect" if CRT_EFFECT != "off" else ""
    print(f"\nExtracting {num_clips} clips at {cell_width}x{cell_height}, {TARGET_FPS}fps{crt_suffix}...")

    for i in range(num_clips):
        # Randomly select a source video
        source_video = random.choice(video_files)
        duration = get_video_duration(source_video)

        if duration is None or duration < (CLIP_DURATION + 2 * AVOID_EDGES):
            print(f"Skipping {source_video.name} - too short or invalid")
            # Retry with a different video
            continue

        # Random start time, avoiding edges
        max_start = duration - CLIP_DURATION - AVOID_EDGES
        start_time = random.uniform(AVOID_EDGES, max_start)

        # Output clip filename
        output_clip = output_dir / f"clip_{i:04d}.mp4"

        # Build video filter chain
        vf_filters = []

        # Add crop filter if any crop values are set
        if CROP_TOP or CROP_RIGHT or CROP_BOTTOM or CROP_LEFT:
            # FFmpeg crop format: crop=out_w:out_h:x:y
            # We need to calculate the output dimensions and position
            # crop from: top, right, bottom, left means:
            # x = left, y = top, width = input_w - left - right, height = input_h - top - bottom
            crop_filter = f'crop=in_w-{CROP_LEFT}-{CROP_RIGHT}:in_h-{CROP_TOP}-{CROP_BOTTOM}:{CROP_LEFT}:{CROP_TOP}'
            vf_filters.append(crop_filter)

        # Add scale and crop to cell size
        vf_filters.append(f'scale={cell_width}:{cell_height}:force_original_aspect_ratio=increase')
        vf_filters.append(f'crop={cell_width}:{cell_height}')

        # Add CRT effect if enabled
        crt_filter = get_crt_filter()
        if crt_filter:
            vf_filters.append(crt_filter)

        # Add fps filter
        vf_filters.append(f'fps={TARGET_FPS}')

        vf_string = ','.join(vf_filters)

        # Extract clip using ffmpeg
        cmd = [
            'ffmpeg',
            '-ss', str(start_time),
            '-i', str(source_video),
            '-t', str(CLIP_DURATION),
            '-vf', vf_string,
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


def loop_clip(clip_path, duration, output_path):
    """Loop a clip to fill a specific duration."""
    cmd = [
        'ffmpeg',
        '-stream_loop', '-1',  # Infinite loop
        '-i', str(clip_path),
        '-t', str(duration),
        '-c', 'copy',
        '-y',
        str(output_path)
    ]

    try:
        subprocess.run(cmd, capture_output=True, check=True)
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error looping clip: {e}")
        return False


def generate_grid_sequence():
    """Generate the sequence of grid sizes: 1 -> max -> 1"""
    sequence = []
    # Growing phase
    for size in range(1, MAX_GRID_SIZE + 1):
        sequence.append(size)
    # Shrinking phase
    for size in range(MAX_GRID_SIZE - 1, 0, -1):
        sequence.append(size)
    return sequence


def create_grid_segment(clips, grid_size, duration, output_file):
    """Create a video segment showing a grid of given size."""
    num_videos = grid_size * grid_size

    # Make sure we have enough clips (loop if necessary)
    clips_to_use = []
    for i in range(num_videos):
        clips_to_use.append(clips[i % len(clips)])

    # Create looped versions of clips if needed
    loops_dir = Path("loops_temp")
    loops_dir.mkdir(parents=True, exist_ok=True)

    looped_clips = []
    for idx, clip in enumerate(clips_to_use):
        looped_clip = loops_dir / f"loop_{grid_size}x{grid_size}_{idx:03d}.mp4"
        if loop_clip(clip, duration, looped_clip):
            looped_clips.append(looped_clip)
        else:
            print(f"Failed to loop clip {clip}")
            return False

    if grid_size == 1:
        # Just use the first looped clip, scaled to output size
        cmd = [
            'ffmpeg',
            '-i', str(looped_clips[0]),
            '-vf', f'scale={OUTPUT_WIDTH}:{OUTPUT_HEIGHT}:force_original_aspect_ratio=increase,crop={OUTPUT_WIDTH}:{OUTPUT_HEIGHT}',
            '-c:v', 'libx264',
            '-preset', 'ultrafast',
            '-crf', '23',
            '-r', str(TARGET_FPS),
            '-y',
            str(output_file)
        ]
    else:
        # Create xstack layout
        cell_width = OUTPUT_WIDTH // grid_size
        cell_height = OUTPUT_HEIGHT // grid_size

        # For larger grids, build row by row to avoid xstack limits
        if grid_size > 6:
            # Build rows first, then stack rows vertically
            row_files = []

            for row_idx in range(grid_size):
                row_clips = looped_clips[row_idx * grid_size:(row_idx + 1) * grid_size]
                row_file = loops_dir / f"row_{grid_size}x{grid_size}_{row_idx}.mp4"

                # Build this row using hstack
                input_args = []
                for clip in row_clips:
                    input_args.extend(['-i', str(clip)])

                # Scale and hstack
                scale_filters = []
                for i in range(len(row_clips)):
                    scale_filters.append(f"[{i}:v]scale={cell_width}:{cell_height}:force_original_aspect_ratio=increase,crop={cell_width}:{cell_height}[v{i}]")

                inputs_for_stack = ''.join([f"[v{i}]" for i in range(len(row_clips))])
                hstack_filter = f"{inputs_for_stack}hstack=inputs={len(row_clips)}[out]"

                filter_complex = ';'.join(scale_filters + [hstack_filter])

                cmd = [
                    'ffmpeg',
                    *input_args,
                    '-filter_complex', filter_complex,
                    '-map', '[out]',
                    '-c:v', 'libx264',
                    '-preset', 'ultrafast',
                    '-crf', '23',
                    '-r', str(TARGET_FPS),
                    '-y',
                    str(row_file)
                ]

                try:
                    subprocess.run(cmd, capture_output=True, check=True)
                    row_files.append(row_file)
                except subprocess.CalledProcessError as e:
                    print(f"Error creating row {row_idx}: {e}")
                    return False

            # Now vstack all rows
            input_args = []
            for row_file in row_files:
                input_args.extend(['-i', str(row_file)])

            vstack_inputs = ''.join([f"[{i}:v]" for i in range(len(row_files))])
            vstack_filter = f"{vstack_inputs}vstack=inputs={len(row_files)}[out]"

            cmd = [
                'ffmpeg',
                *input_args,
                '-filter_complex', vstack_filter,
                '-map', '[out]',
                '-c:v', 'libx264',
                '-preset', 'ultrafast',
                '-crf', '23',
                '-r', str(TARGET_FPS),
                '-y',
                str(output_file)
            ]
        else:
            # Original xstack method for smaller grids
            input_args = []
            for clip in looped_clips:
                input_args.extend(['-i', str(clip)])

            # Build xstack layout
            layout_positions = []
            for row in range(grid_size):
                for col in range(grid_size):
                    x = col * cell_width
                    y = row * cell_height
                    layout_positions.append(f"{x}_{y}")
            layout = '|'.join(layout_positions)

            # Scale each input to cell size
            scale_filters = []
            for i in range(num_videos):
                scale_filters.append(f"[{i}:v]scale={cell_width}:{cell_height}:force_original_aspect_ratio=increase,crop={cell_width}:{cell_height}[v{i}]")

            inputs_for_stack = ''.join([f"[v{i}]" for i in range(num_videos)])
            xstack_filter = f"{inputs_for_stack}xstack=inputs={num_videos}:layout={layout}:fill=black[out]"

            filter_complex = ';'.join(scale_filters + [xstack_filter])

            cmd = [
                'ffmpeg',
                *input_args,
                '-filter_complex', filter_complex,
                '-map', '[out]',
                '-c:v', 'libx264',
                '-preset', 'ultrafast',
                '-crf', '23',
                '-r', str(TARGET_FPS),
                '-y',
                str(output_file)
            ]

    try:
        subprocess.run(cmd, capture_output=True, check=True)
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error creating grid segment: {e}")
        return False


def concatenate_segments(segment_files, output_file):
    """Concatenate all segments with optional transitions."""
    segments_dir = Path("segments_temp")

    if TRANSITION_TYPE == "cut":
        # Simple concatenation
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
    else:
        # xfade transitions
        input_args = []
        for segment in segment_files:
            input_args.extend(['-i', str(segment)])

        # Build xfade filter chain
        filter_parts = []
        transition_duration = 0.5  # 0.5 second transition

        # Get duration of first segment
        first_duration = get_video_duration(segment_files[0])

        current_offset = first_duration - transition_duration
        previous_stream = "[0:v]"

        for i in range(1, len(segment_files)):
            if i == len(segment_files) - 1:
                output_stream = "[out]"
            else:
                output_stream = f"[v{i}]"

            # Use the selected transition type
            xfade = f"{previous_stream}[{i}:v]xfade=transition={TRANSITION_TYPE}:duration={transition_duration}:offset={current_offset}{output_stream}"
            filter_parts.append(xfade)

            previous_stream = output_stream

            # Update offset for next transition
            seg_duration = get_video_duration(segment_files[i])
            current_offset += seg_duration - transition_duration

        filter_complex = ';'.join(filter_parts)

        cmd = [
            'ffmpeg',
            *input_args,
            '-filter_complex', filter_complex,
            '-map', '[out]',
            '-c:v', 'libx264',
            '-preset', 'medium',
            '-crf', '23',
            '-pix_fmt', 'yuv420p',
            '-r', str(TARGET_FPS),
            '-y',
            str(output_file)
        ]

    print(f"\nConcatenating segments with '{TRANSITION_TYPE}' transitions...")
    try:
        subprocess.run(cmd, check=True)
        print(f"✓ Final video created: {output_file}")
    except subprocess.CalledProcessError as e:
        print(f"✗ Error concatenating segments: {e}")
        sys.exit(1)


def main():
    if len(sys.argv) < 2:
        print("Usage: python generate_growing_grid.py <video_directory> [output_file]")
        print("\nExample: python generate_growing_grid.py ./games growing_grid.mp4")
        sys.exit(1)

    video_dir = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else "growing_grid.mp4"

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

    # Generate grid sequence
    grid_sequence = generate_grid_sequence()
    print(f"\nGrid sequence: {' → '.join(map(str, [s*s for s in grid_sequence]))} videos")

    # Cell size for the smallest cells (at max grid size)
    min_cell_width = OUTPUT_WIDTH // MAX_GRID_SIZE
    min_cell_height = OUTPUT_HEIGHT // MAX_GRID_SIZE

    # Extract clips at the smallest cell size
    clips_dir = Path("clips_temp")
    clips = extract_clips(video_files, TOTAL_CLIPS, clips_dir, min_cell_width, min_cell_height)

    if not clips:
        print("Error: No clips extracted")
        sys.exit(1)

    print(f"\nSuccessfully extracted {len(clips)} clips")

    # Create segments for each grid size
    segments_dir = Path("segments_temp")
    segments_dir.mkdir(parents=True, exist_ok=True)

    segment_files = []
    time_per_state = TOTAL_VIDEO_LENGTH / len(grid_sequence)

    print(f"\nGenerating {len(grid_sequence)} grid segments...")

    for idx, grid_size in enumerate(grid_sequence):
        segment_file = segments_dir / f"segment_{idx:03d}_{grid_size}x{grid_size}.mp4"
        print(f"Creating segment {idx+1}/{len(grid_sequence)}: {grid_size}x{grid_size} grid ({grid_size*grid_size} videos)")

        if create_grid_segment(clips, grid_size, time_per_state, segment_file):
            segment_files.append(segment_file)
        else:
            print(f"Failed to create segment {idx}")
            sys.exit(1)

    # Concatenate all segments
    concatenate_segments(segment_files, output_file)

    print("\n✓ Done!")
    print(f"\nTo clean up temporary files:")
    print(f"  rm -rf {clips_dir}")
    print(f"  rm -rf {segments_dir}")
    print(f"  rm -rf loops_temp")


if __name__ == '__main__':
    main()
