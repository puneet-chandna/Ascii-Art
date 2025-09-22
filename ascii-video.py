#!/usr/bin/env python3
"""
MP4 to Insane ASCII Art Converter - Interactive Version
Converts video files into animated ASCII art in your terminal
"""

import cv2
import numpy as np
import time
import os
import sys
import shutil
from typing import Tuple, Optional
import threading
import queue

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
        self.fps = fps
        self.color = color
        self.ascii_chars = ASCII_CHARS.get(style, ASCII_CHARS['ultra'])
        self.cap = None
        self.quality = quality
        
        # Auto-adjust width to terminal if not specified
        if width is None:
            term_width, _ = self.get_terminal_size()
            # Use 95% of terminal width for better fit
            self.width = int(term_width * 0.95)
        else:
            self.width = width
            
        # Adjust settings based on quality
        if quality == 'ultra':
            self.width = min(self.width, 200)  # Cap at 200 for performance
            self.fps = 30
        elif quality == 'high':
            self.width = min(self.width, 150)
            self.fps = 24
        elif quality == 'medium':
            self.width = min(self.width, 100)
            self.fps = 20
        else:  # low
            self.width = min(self.width, 80)
            self.fps = 15
        
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
        
        return True
    
    def get_terminal_size(self) -> Tuple[int, int]:
        """Get terminal dimensions"""
        size = shutil.get_terminal_size()
        return size.columns, size.lines
    
    def resize_frame(self, frame: np.ndarray) -> np.ndarray:
        """Resize frame to fit ASCII dimensions"""
        height, width = frame.shape[:2]
        
        # Calculate aspect ratio
        aspect_ratio = height / width
        
        # ASCII characters are typically twice as tall as wide
        ascii_height = int(self.width * aspect_ratio * 0.55)
        
        # Get terminal size and ensure we don't exceed it
        term_width, term_height = self.get_terminal_size()
        
        # Leave some space for UI elements
        max_height = term_height - 4
        
        if ascii_height > max_height:
            ascii_height = max_height
            self.width = int(ascii_height / aspect_ratio / 0.55)
        
        # Ensure width doesn't exceed terminal
        if self.width > term_width - 2:
            self.width = term_width - 2
            ascii_height = int(self.width * aspect_ratio * 0.55)
        
        # Resize the frame
        resized = cv2.resize(frame, (self.width, ascii_height), interpolation=cv2.INTER_AREA)
        return resized
    
    def pixel_to_ascii(self, pixel_value: int) -> str:
        """Convert pixel brightness to ASCII character"""
        chars_len = len(self.ascii_chars)
        index = int((pixel_value / 255) * (chars_len - 1))
        return self.ascii_chars[index]
    
    def frame_to_ascii(self, frame: np.ndarray) -> str:
        """Convert a single frame to ASCII art"""
        if len(frame.shape) == 3:
            gray_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        else:
            gray_frame = frame
        
        resized = self.resize_frame(gray_frame)
        
        ascii_frame = ""
        for row in resized:
            for pixel in row:
                ascii_frame += self.pixel_to_ascii(pixel)
            ascii_frame += "\n"
        
        return ascii_frame
    
    def frame_to_colored_ascii(self, frame: np.ndarray) -> str:
        """Convert frame to colored ASCII art"""
        resized = self.resize_frame(frame)
        
        ascii_frame = ""
        for row in resized:
            for pixel in row:
                b, g, r = pixel
                gray = int(0.299 * r + 0.587 * g + 0.114 * b)
                char = self.pixel_to_ascii(gray)
                
                # Use simplified color for better performance
                if self.quality in ['ultra', 'high']:
                    ascii_frame += f"\033[38;2;{r};{g};{b}m{char}\033[0m"
                else:
                    # Use 256 color mode for better performance
                    color_code = 16 + (r//51)*36 + (g//51)*6 + (b//51)
                    ascii_frame += f"\033[38;5;{color_code}m{char}\033[0m"
            
            ascii_frame += "\n"
        
        return ascii_frame
    
    def clear_screen(self):
        """Clear the terminal screen"""
        os.system('cls' if os.name == 'nt' else 'clear')
    
    def play_ascii_video(self, loop: bool = False, show_info: bool = True):
        """Play the video as ASCII art in the terminal"""
        if not self.initialize_video():
            return
        
        frame_delay = 1.0 / self.fps
        frame_count = 0
        paused = False
        
        self.clear_screen()
        print(f"\n{'='*60}")
        print(f"🎬 ASCII VIDEO PLAYER - INSANE MODE")
        print(f"{'='*60}")
        print(f"📹 Video: {os.path.basename(self.video_path)}")
        print(f"📐 Resolution: {self.width} × AUTO (Terminal Adapted)")
        print(f"🎨 Quality: {self.quality.upper()}")
        print(f"🔄 FPS: {self.fps}")
        print(f"🎯 Style: {[k for k, v in ASCII_CHARS.items() if v == self.ascii_chars][0]}")
        print(f"🌈 Color: {'ON' if self.color else 'OFF'}")
        print(f"{'='*60}")
        print(f"\n⌨️  Controls: [SPACE] Pause/Resume | [Q] Quit\n")
        time.sleep(3)
        
        try:
            while True:
                ret, frame = self.cap.read()
                
                if not ret:
                    if loop:
                        self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                        frame_count = 0
                        continue
                    else:
                        break
                
                self.clear_screen()
                
                # Convert frame to ASCII
                if self.color:
                    ascii_art = self.frame_to_colored_ascii(frame)
                else:
                    ascii_art = self.frame_to_ascii(frame)
                
                # Display the frame
                print(ascii_art, end='')
                
                if show_info:
                    # Show playback info with progress bar
                    progress = (frame_count / self.total_frames) * 100
                    bar_length = 50
                    filled_length = int(bar_length * frame_count // self.total_frames)
                    bar = '█' * filled_length + '░' * (bar_length - filled_length)
                    
                    print(f"\n[{bar}] {progress:.1f}% | Frame {frame_count}/{self.total_frames} | {self.fps} FPS", end='')
                
                frame_count += 1
                time.sleep(frame_delay)
                
        except KeyboardInterrupt:
            print("\n\n✋ Playback stopped")
        finally:
            self.cap.release()

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
    ║              🎬 MP4 TO ASCII ART CONVERTER 🎬                ║
    ║                    TERMINAL EDITION v2.0                     ║
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
            valid_extensions = ['.mp4', '.avi', '.mov', '.mkv', '.flv', '.wmv', '.webm']
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
            'name': '🔥 ULTRA INSANE (Best Quality)',
            'quality': 'ultra',
            'color': True,
            'style': 'ultra',
            'desc': 'Maximum resolution, colors, best characters'
        },
        '2': {
            'name': '⚡ HIGH QUALITY (Recommended)',
            'quality': 'high',
            'color': True,
            'style': 'detailed',
            'desc': 'Great quality with good performance'
        },
        '3': {
            'name': '🎮 MEDIUM QUALITY',
            'quality': 'medium',
            'color': False,
            'style': 'detailed',
            'desc': 'Balanced quality and performance'
        },
        '4': {
            'name': '💾 LOW/RETRO',
            'quality': 'low',
            'color': False,
            'style': 'standard',
            'desc': 'Classic ASCII, fast performance'
        },
        '5': {
            'name': '🔢 MATRIX STYLE',
            'quality': 'high',
            'color': True,
            'style': 'matrix',
            'desc': 'Green matrix-like characters'
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
    print("  [1] Ultra (200 chars wide)")
    print("  [2] High (150 chars wide)")
    print("  [3] Medium (100 chars wide)")
    print("  [4] Low (80 chars wide)")
    
    quality_map = {'1': 'ultra', '2': 'high', '3': 'medium', '4': 'low'}
    while True:
        q = input("Choice: ").strip()
        if q in quality_map:
            settings['quality'] = quality_map[q]
            break
        print("Invalid choice!")
    
    # Color
    print("\n🌈 Enable colors? (requires 24-bit color terminal)")
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
            duration = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) / cap.get(cv2.CAP_PROP_FPS))
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            cap.release()
            
            print(f"\n📹 Video loaded successfully!")
            print(f"   • File: {os.path.basename(video_path)}")
            print(f"   • Resolution: {width}×{height}")
            print(f"   • Duration: {duration//60}:{duration%60:02d}")
        
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
        
        # FPS option
        print("\n🎯 Playback speed:")
        print("  [1] Normal")
        print("  [2] Fast (1.5x)")
        print("  [3] Slow (0.5x)")
        speed = input("Choice [1]: ").strip() or '1'
        
        fps_multiplier = {'1': 1.0, '2': 1.5, '3': 0.5}.get(speed, 1.0)
        
        # Create converter with settings
        converter = VideoToASCII(
            video_path=video_path,
            width=None,  # Auto-detect
            fps=int(30 * fps_multiplier),
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
        print("Please try again or check your video file.")
        input("\nPress ENTER to exit...")

if __name__ == "__main__":
    main()