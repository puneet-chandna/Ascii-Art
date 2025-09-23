#!/usr/bin/env python3
"""
MP4 to Insane ASCII Art Converter

"""

import cv2
import numpy as np
import time
import os
import sys
import shutil
from typing import Tuple, Optional, List
import threading
import queue
from collections import deque
from multiprocessing import Pool, cpu_count

# ASCII character sets for different styles
ASCII_CHARS = {
    'standard': ' .:-=+*#%@',
    'detailed': ' .\'`^",:;Il!i><~+_-?][}{1)(|\/tfjrxnuvczXYUJCLQ0OZmwqpdbkhao*#MW&8%B@$',
    'blocks': ' ░▒▓█',
    'simple': ' .oO@',
    'matrix': ' .:-=+*#%@01',
    'crazy': ' ⣀⣤⣶⣿⣿⣶⣤⣀',
    'ultra': ' `.-\':_,^=;><+!rc*/z?sLTv)J7(|Fi{C}fI31tlu[neoZ5Yxjya]2ESwqkP6h9d4VpOGbUAKXHm8RD#$Bg0MNWQ%&@'
}

class VideoToASCII:
    def __init__(self, video_path: str, width: int = None, fps: int = 30, 
                 color: bool = False, style: str = 'ultra', quality: str = 'high'):
        """
        Initialize the converter
        """
        self.video_path = video_path
        self.target_fps = fps
        self.color = color
        self.ascii_chars = ASCII_CHARS.get(style, ASCII_CHARS['ultra'])
        self.cap = None
        self.quality = quality
        self.frame_buffer = deque(maxlen=10)  # Pre-processed frame buffer
        self.processing_times = deque(maxlen=30)  # Track processing times
        
        # Pre-calculate ASCII lookup table for faster conversion
        self.ascii_lookup = self._create_lookup_table()
        
        # Auto-adjust width to terminal if not specified
        if width is None:
            term_width, _ = self.get_terminal_size()
            self.width = int(term_width * 0.95)
        else:
            self.width = width
            
        # Adjust settings based on quality
        if quality == 'ultra':
            self.width = min(self.width, 200)
            self.skip_frames = False
        elif quality == 'high':
            self.width = min(self.width, 150)
            self.skip_frames = False
        elif quality == 'medium':
            self.width = min(self.width, 100)
            self.skip_frames = True
        else:  # low
            self.width = min(self.width, 80)
            self.skip_frames = True
    
    def _create_lookup_table(self):
        """Create a lookup table for faster ASCII conversion"""
        lookup = []
        chars_len = len(self.ascii_chars)
        for i in range(256):
            index = int((i / 255) * (chars_len - 1))
            lookup.append(self.ascii_chars[index])
        return lookup
    
    def initialize_video(self) -> bool:
        """Initialize video capture"""
        self.cap = cv2.VideoCapture(self.video_path)
        if not self.cap.isOpened():
            print(f"❌ Error: Could not open video file {self.video_path}")
            return False
        
        # Get video properties
        self.total_frames = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
        self.video_fps = self.cap.get(cv2.CAP_PROP_FPS)
        self.video_width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        self.video_height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        self.video_duration = self.total_frames / self.video_fps
        
        # Calculate actual frame delay based on video FPS
        self.frame_delay = 1.0 / self.video_fps
        
        return True
    
    def get_terminal_size(self) -> Tuple[int, int]:
        """Get terminal dimensions"""
        size = shutil.get_terminal_size()
        return size.columns, size.lines
    
    def calculate_dimensions(self):
        """Pre-calculate dimensions for all frames"""
        height, width = self.video_height, self.video_width
        aspect_ratio = height / width
        
        # ASCII characters are typically twice as tall as wide
        self.ascii_height = int(self.width * aspect_ratio * 0.55)
        
        # Get terminal size and ensure we don't exceed it
        term_width, term_height = self.get_terminal_size()
        max_height = term_height - 4
        
        if self.ascii_height > max_height:
            self.ascii_height = max_height
            self.width = int(self.ascii_height / aspect_ratio / 0.55)
        
        if self.width > term_width - 2:
            self.width = term_width - 2
            self.ascii_height = int(self.width * aspect_ratio * 0.55)
    
    def frame_to_ascii_fast(self, frame: np.ndarray) -> str:
        """Optimized frame to ASCII conversion"""
        # Convert to grayscale if needed
        if len(frame.shape) == 3:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        else:
            gray = frame
        
        # Resize frame - use INTER_LINEAR for better speed/quality balance
        resized = cv2.resize(gray, (self.width, self.ascii_height), interpolation=cv2.INTER_LINEAR)
        
        # Fast ASCII conversion using lookup table
        ascii_str = ""
        for row in resized:
            row_chars = [self.ascii_lookup[pixel] for pixel in row]
            ascii_str += ''.join(row_chars) + '\n'
        
        return ascii_str
    
    def frame_to_colored_ascii_fast(self, frame: np.ndarray) -> str:
        """Optimized colored ASCII conversion"""
        # Resize frame (keep color)
        resized = cv2.resize(frame, (self.width, self.ascii_height), interpolation=cv2.INTER_LINEAR)
        
        # Pre-allocate list for better performance
        lines = []
        
        for row in resized:
            line = []
            for pixel in row:
                b, g, r = pixel
                gray = int(0.299 * r + 0.587 * g + 0.114 * b)
                char = self.ascii_lookup[gray]
                
                # Use simpler color format for better performance
                if self.quality in ['ultra', 'high']:
                    line.append(f"\033[38;2;{r};{g};{b}m{char}")
                else:
                    # 256 color mode - faster
                    color_code = 16 + (r//51)*36 + (g//51)*6 + (b//51)
                    line.append(f"\033[38;5;{color_code}m{char}")
            
            lines.append(''.join(line) + "\033[0m")
        
        return '\n'.join(lines) + '\n'
    
    def clear_screen(self):
        """Clear the terminal screen"""
        # Use ANSI escape codes for faster clearing
        print("\033[2J\033[H", end='')
    
    def play_ascii_video(self, loop: bool = False, show_info: bool = True):
        """Play the video with proper frame timing"""
        if not self.initialize_video():
            return
        
        # Pre-calculate dimensions
        self.calculate_dimensions()
        
        # Start info
        self.clear_screen()
        print(f"\n{'='*60}")
        print(f"🎬 ASCII VIDEO PLAYER - OPTIMIZED")
        print(f"{'='*60}")
        print(f"📹 Video: {os.path.basename(self.video_path)}")
        print(f"📐 Resolution: {self.width} × {self.ascii_height}")
        print(f"🎨 Quality: {self.quality.upper()}")
        print(f"🔄 Original FPS: {self.video_fps:.1f}")
        print(f"⏱️ Original Duration: {self.video_duration:.1f}s")
        print(f"🌈 Color: {'ON' if self.color else 'OFF'}")
        print(f"{'='*60}")
        print(f"\n⌨️  Press Ctrl+C to stop\n")
        time.sleep(2)
        
        frame_count = 0
        start_time = time.perf_counter()
        dropped_frames = 0
        last_displayed_frame = None
        
        try:
            while True:
                current_time = time.perf_counter()
                elapsed = current_time - start_time
                
                # Check if we've exceeded video duration (with small buffer for precision)
                if elapsed >= self.video_duration + 0.1 and not loop:
                    print("\n\n✅ Video playback completed!")
                    break
                
                # Calculate which frame we should be showing based on elapsed time
                target_frame_num = int(elapsed * self.video_fps)
                
                # If looping and we've exceeded total frames, restart
                if loop and target_frame_num >= self.total_frames:
                    self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                    frame_count = 0
                    start_time = time.perf_counter()
                    dropped_frames = 0
                    continue
                
                # Ensure we don't try to read beyond the video
                if target_frame_num >= self.total_frames:
                    if not loop:
                        print("\n\n✅ Video playback completed!")
                        break
                
                # Read and process frames until we reach the target frame
                while frame_count <= target_frame_num and frame_count < self.total_frames:
                    ret, frame = self.cap.read()
                    
                    if not ret:
                        # End of video reached
                        if loop:
                            self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                            frame_count = 0
                            start_time = time.perf_counter()
                            dropped_frames = 0
                            break
                        else:
                            print("\n\n✅ Video playback completed!")
                            return  # Exit the function completely
                    
                    # Process and display the frame if it's the target
                    if frame_count == target_frame_num:
                        # Time the processing
                        process_start = time.perf_counter()
                        
                        # Convert frame to ASCII
                        if self.color:
                            ascii_art = self.frame_to_colored_ascii_fast(frame)
                        else:
                            ascii_art = self.frame_to_ascii_fast(frame)
                        
                        # Clear and display
                        self.clear_screen()
                        print(ascii_art, end='')
                        last_displayed_frame = frame_count
                        
                        if show_info:
                            # Calculate actual FPS and progress
                            actual_fps = frame_count / elapsed if elapsed > 0 else 0
                            progress = min((frame_count / self.total_frames) * 100, 100.0)
                            
                            # Progress bar
                            bar_length = 50
                            filled_length = min(int(bar_length * frame_count // self.total_frames), bar_length)
                            bar = '█' * filled_length + '░' * (bar_length - filled_length)
                            
                            info = f"[{bar}] {progress:.1f}% | "
                            info += f"Frame {frame_count}/{self.total_frames} | "
                            info += f"FPS: {actual_fps:.1f}/{self.video_fps:.1f} | "
                            info += f"Time: {elapsed:.1f}s/{self.video_duration:.1f}s"
                            if dropped_frames > 0:
                                info += f" | Dropped: {dropped_frames}"
                            
                            print(info, end='', flush=True)
                        
                        process_time = time.perf_counter() - process_start
                        self.processing_times.append(process_time)
                    else:
                        # Frame was skipped
                        dropped_frames += 1
                    
                    frame_count += 1
                
                # Check if we've processed all frames
                if frame_count >= self.total_frames and not loop:
                    print("\n\n✅ Video playback completed!")
                    break
                
                # Calculate how long to sleep to maintain proper timing
                next_frame_time = (frame_count / self.video_fps)
                sleep_duration = next_frame_time - (time.perf_counter() - start_time)
                
                if sleep_duration > 0 and sleep_duration < 1:  # Sanity check on sleep duration
                    time.sleep(sleep_duration)
                
        except KeyboardInterrupt:
            print("\n\n✋ Playback stopped by user")
        except Exception as e:
            print(f"\n\n❌ Error during playback: {e}")
            import traceback
            traceback.print_exc()
        finally:
            self.cap.release()
            
            # Final stats
            total_time = time.perf_counter() - start_time
            if total_time > 0:
                print(f"\n{'='*60}")
                print(f"📊 PLAYBACK STATISTICS:")
                print(f"  • Total playback time: {total_time:.2f}s")
                print(f"  • Original video duration: {self.video_duration:.2f}s")
                print(f"  • Time difference: {abs(total_time - self.video_duration):.2f}s")
                print(f"  • Frames displayed: {last_displayed_frame + 1 if last_displayed_frame is not None else frame_count}")
                print(f"  • Frames dropped: {dropped_frames}")
                if self.processing_times:
                    avg_process = sum(self.processing_times) / len(self.processing_times)
                    print(f"  • Avg processing time: {avg_process*1000:.2f}ms")
                print(f"{'='*60}")

def print_banner():
    """Print cool banner"""
    banner = """
    ╔═══════════════════════════════════════════════════════════════╗
    ║                                                               ║
    ║     █████╗ ███████╗ ██████╗██╗██╗    ██╗   ██╗██╗██████╗    ║
    ║    ██╔══██╗██╔════╝██╔════╝██║██║    ██║   ██║██║██╔══██╗   ║
    ║    ███████║███████╗██║     ██║██║    ██║   ██║██║██║  ██║   ║
    ║    ██╔══██║╚════██║██║     ██║██║    ╚██╗ ██╔╝██║██║  ██║   ║
    ║    ██║  ██║███████║╚██████╗██║██║     ╚████╔╝ ██║██████╔╝   ║
    ║    ╚═╝  ╚═╝╚══════╝ ╚═════╝╚═╝╚═╝      ╚═══╝  ╚═╝╚═════╝    ║
    ║                                                               ║
    ║           🎬 MP4 TO ASCII ART CONVERTER v2.2 🎬              ║
    ║                  PERFECT TIMING & AUTO-EXIT!                 ║
    ╚═══════════════════════════════════════════════════════════════╝
    """
    print(banner)

def get_video_file():
    """Get video file from user"""
    while True:
        print("\n📁 Enter the path to your video file (or 'q' to quit):")
        video_path = input(">>> ").strip()
        
        if video_path.lower() == 'q':
            print("👋 Goodbye!")
            sys.exit(0)
        
        # Remove quotes if present
        video_path = video_path.strip('"\'')
        
        if os.path.isfile(video_path):
            # Check if it's a video file
            valid_extensions = ['.mp4', '.avi', '.mov', '.mkv', '.flv', '.wmv', '.webm', '.m4v', '.mpg', '.mpeg']
            if any(video_path.lower().endswith(ext) for ext in valid_extensions):
                return video_path
            else:
                print("⚠️  This doesn't appear to be a video file. Try again.")
        else:
            print("❌ File not found. Please check the path and try again.")

def select_preset():
    """Show preset options menu"""
    print("\n🎨 SELECT QUALITY PRESET:")
    print("="*50)
    
    presets = {
        '1': {
            'name': '🔥 ULTRA INSANE (Highest Quality)',
            'quality': 'ultra',
            'color': True,
            'style': 'ultra',
            'desc': 'Maximum resolution, perfect sync'
        },
        '2': {
            'name': '⚡ HIGH QUALITY (Recommended)',
            'quality': 'high',
            'color': True,
            'style': 'detailed',
            'desc': 'Great quality, optimized performance'
        },
        '3': {
            'name': '🎮 MEDIUM QUALITY',
            'quality': 'medium',
            'color': False,
            'style': 'detailed',
            'desc': 'Good balance, smooth playback'
        },
        '4': {
            'name': '💾 LOW/FAST',
            'quality': 'low',
            'color': False,
            'style': 'standard',
            'desc': 'Basic ASCII, fastest performance'
        },
        '5': {
            'name': '🔢 MATRIX STYLE',
            'quality': 'high',
            'color': True,
            'style': 'matrix',
            'desc': 'Matrix effect with proper timing'
        },
        '6': {
            'name': '🎨 CUSTOM',
            'quality': None,
            'color': None,
            'style': None,
            'desc': 'Configure everything yourself'
        }
    }
    
    for key, preset in presets.items():
        print(f"\n  [{key}] {preset['name']}")
        print(f"      {preset['desc']}")
    
    print("\n" + "="*50)
    
    while True:
        choice = input("\n👉 Select preset (1-6): ").strip()
        if choice in presets:
            return presets[choice], choice
        print("❌ Invalid choice. Please select 1-6.")

def custom_settings():
    """Get custom settings from user"""
    settings = {}
    
    # Quality
    print("\n📊 Select quality level:")
    print("  [1] Ultra (200 chars, no frame skip)")
    print("  [2] High (150 chars, no frame skip)")
    print("  [3] Medium (100 chars, smart frame skip)")
    print("  [4] Low (80 chars, aggressive frame skip)")
    
    quality_map = {'1': 'ultra', '2': 'high', '3': 'medium', '4': 'low'}
    while True:
        q = input("Choice: ").strip()
        if q in quality_map:
            settings['quality'] = quality_map[q]
            break
        print("Invalid choice!")
    
    # Color
    print("\n🌈 Enable colors? (may impact performance)")
    settings['color'] = input("  [Y/n]: ").strip().lower() != 'n'
    
    # Style
    print("\n🎨 Select character style:")
    styles = list(ASCII_CHARS.keys())
    for i, style in enumerate(styles, 1):
        print(f"  [{i}] {style}")
    
    while True:
        try:
            s = int(input("Choice: ").strip())
            if 1 <= s <= len(styles):
                settings['style'] = styles[s-1]
                break
        except:
            pass
        print("Invalid choice!")
    
    return settings

def main():
    """Main interactive function"""
    try:
        # Clear screen and show banner
        os.system('cls' if os.name == 'nt' else 'clear')
        print_banner()
        
        # Get video file
        video_path = get_video_file()
        
        # Get video info
        cap = cv2.VideoCapture(video_path)
        if cap.isOpened():
            fps = cap.get(cv2.CAP_PROP_FPS)
            frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            duration = frame_count / fps if fps > 0 else 0
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            cap.release()
            
            print(f"\n📹 Video loaded successfully!")
            print(f"   • File: {os.path.basename(video_path)}")
            print(f"   • Resolution: {width}×{height}")
            print(f"   • FPS: {fps:.1f}")
            print(f"   • Duration: {duration:.1f}s ({int(duration//60)}:{int(duration%60):02d})")
            print(f"   • Total frames: {frame_count}")
        else:
            print("⚠️  Warning: Could not read video properties")
        
        # Select preset
        preset, choice = select_preset()
        
        # Get settings
        if choice == '6':  # Custom
            settings = custom_settings()
        else:
            settings = {
                'quality': preset['quality'],
                'color': preset['color'],
                'style': preset['style']
            }
        
        # Additional options
        print("\n⚙️  ADDITIONAL OPTIONS:")
        print("="*50)
        loop = input("🔄 Loop video? [y/N]: ").strip().lower() == 'y'
        show_info = input("📊 Show playback info? [Y/n]: ").strip().lower() != 'n'
        
        # Create converter with settings
        converter = VideoToASCII(
            video_path=video_path,
            width=None,  # Auto-detect
            fps=30,  # This is now just for display, actual sync uses video FPS
            color=settings['color'],
            style=settings['style'],
            quality=settings['quality']
        )
        
        # Final confirmation
        print("\n" + "="*60)
        print("🚀 READY TO START!")
        print("="*60)
        print(f"✅ Quality: {settings['quality'].upper()}")
        print(f"✅ Colors: {'ON' if settings['color'] else 'OFF'}")
        print(f"✅ Style: {settings['style']}")
        print(f"✅ Loop: {'ON' if loop else 'OFF'}")
        print(f"✅ Terminal width: {converter.width} characters")
        print(f"✅ Video will play at original speed: {duration:.1f}s")
        print("="*60)
        
        input("\n🎬 Press ENTER to start playing...")
        
        # Play the video
        converter.play_ascii_video(loop=loop, show_info=show_info)
        
        # Ask if user wants to convert another video
        print("\n" + "="*60)
        again = input("🔄 Convert another video? [y/N]: ").strip().lower() == 'y'
        if again:
            main()
        else:
            print("\n👋 Thanks for using ASCII Video Converter!")
            print("⭐ Have an awesome day! ⭐\n")
            
    except Exception as e:
        print(f"\n❌ An error occurred: {e}")
        import traceback
        traceback.print_exc()
        print("Please try again or check your video file.")
        input("\nPress ENTER to exit...")

if __name__ == "__main__":
    main()