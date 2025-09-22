#!/usr/bin/env python3
"""
MP4 to Insane ASCII Art Converter
Converts video files into animated ASCII art in your terminal
"""

import cv2
import numpy as np
import time
import os
import sys
import argparse
from typing import Tuple, Optional
import shutil

# ASCII character sets for different styles
ASCII_CHARS = {
    'standard': ' .:-=+*#%@',
    'detailed': ' .\'`^",:;Il!i><~+_-?][}{1)(|\/tfjrxnuvczXYUJCLQ0OZmwqpdbkhao*#MW&8%B@$',
    'blocks': ' ░▒▓█',
    'simple': ' .oO@',
    'matrix': ' .:-=+*#%@01',
    'crazy': ' ⣀⣤⣶⣿⣿⣶⣤⣀'
}

class VideoToASCII:
    def __init__(self, video_path: str, width: int = 100, fps: int = 30, 
                 color: bool = False, style: str = 'detailed'):
        """
        Initialize the converter
        
        Args:
            video_path: Path to the input video file
            width: Width of ASCII output in characters
            fps: Frames per second for playback
            color: Enable colored ASCII output
            style: ASCII character set style
        """
        self.video_path = video_path
        self.width = width
        self.fps = fps
        self.color = color
        self.ascii_chars = ASCII_CHARS.get(style, ASCII_CHARS['detailed'])
        self.cap = None
        
    def initialize_video(self) -> bool:
        """Initialize video capture"""
        self.cap = cv2.VideoCapture(self.video_path)
        if not self.cap.isOpened():
            print(f"Error: Could not open video file {self.video_path}")
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
        # So we need to adjust for this
        ascii_height = int(self.width * aspect_ratio * 0.55)
        
        # Get terminal size and ensure we don't exceed it
        term_width, term_height = self.get_terminal_size()
        
        if self.width > term_width - 2:
            self.width = term_width - 2
            ascii_height = int(self.width * aspect_ratio * 0.55)
        
        if ascii_height > term_height - 2:
            ascii_height = term_height - 2
            self.width = int(ascii_height / aspect_ratio / 0.55)
        
        # Resize the frame
        resized = cv2.resize(frame, (self.width, ascii_height))
        return resized
    
    def pixel_to_ascii(self, pixel_value: int) -> str:
        """Convert pixel brightness to ASCII character"""
        chars_len = len(self.ascii_chars)
        index = int((pixel_value / 255) * (chars_len - 1))
        return self.ascii_chars[index]
    
    def frame_to_ascii(self, frame: np.ndarray) -> str:
        """Convert a single frame to ASCII art"""
        # Convert to grayscale if not already
        if len(frame.shape) == 3:
            gray_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        else:
            gray_frame = frame
        
        # Resize frame
        resized = self.resize_frame(gray_frame)
        
        # Convert to ASCII
        ascii_frame = ""
        for row in resized:
            for pixel in row:
                ascii_frame += self.pixel_to_ascii(pixel)
            ascii_frame += "\n"
        
        return ascii_frame
    
    def frame_to_colored_ascii(self, frame: np.ndarray) -> str:
        """Convert frame to colored ASCII art"""
        # Resize frame (keep color)
        resized = self.resize_frame(frame)
        
        # Convert to ASCII with ANSI color codes
        ascii_frame = ""
        for row in resized:
            for pixel in row:
                # Get RGB values (OpenCV uses BGR)
                b, g, r = pixel
                
                # Convert to grayscale for character selection
                gray = int(0.299 * r + 0.587 * g + 0.114 * b)
                
                # Get ASCII character
                char = self.pixel_to_ascii(gray)
                
                # Add ANSI color code
                ascii_frame += f"\033[38;2;{r};{g};{b}m{char}\033[0m"
            
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
        
        print(f"\n🎬 Starting ASCII Video Player...")
        print(f"📹 Video: {os.path.basename(self.video_path)}")
        print(f"📐 Resolution: {self.width} chars wide")
        print(f"🎨 Style: {[k for k, v in ASCII_CHARS.items() if v == self.ascii_chars][0]}")
        print(f"🔄 FPS: {self.fps}")
        print(f"\nPress Ctrl+C to stop\n")
        time.sleep(2)
        
        try:
            while True:
                ret, frame = self.cap.read()
                
                if not ret:
                    if loop:
                        # Reset video to beginning
                        self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                        frame_count = 0
                        continue
                    else:
                        break
                
                # Clear screen for smooth animation
                self.clear_screen()
                
                # Convert frame to ASCII
                if self.color:
                    ascii_art = self.frame_to_colored_ascii(frame)
                else:
                    ascii_art = self.frame_to_ascii(frame)
                
                # Display the frame
                print(ascii_art, end='')
                
                if show_info:
                    # Show playback info
                    progress = (frame_count / self.total_frames) * 100
                    print(f"\n[Frame {frame_count}/{self.total_frames} | {progress:.1f}% | FPS: {self.fps}]", end='')
                
                frame_count += 1
                
                # Control playback speed
                time.sleep(frame_delay)
                
        except KeyboardInterrupt:
            print("\n\n✋ Playback stopped by user")
        finally:
            self.cap.release()
            print("\n🎬 Video playback complete!")
    
    def export_to_file(self, output_path: str = None):
        """Export ASCII frames to a text file"""
        if not self.initialize_video():
            return
        
        if output_path is None:
            output_path = os.path.splitext(self.video_path)[0] + "_ascii.txt"
        
        print(f"📝 Exporting ASCII frames to {output_path}")
        
        with open(output_path, 'w', encoding='utf-8') as f:
            frame_count = 0
            
            while True:
                ret, frame = self.cap.read()
                if not ret:
                    break
                
                # Convert frame
                if self.color:
                    # For file export, we can't use ANSI codes, so just do grayscale
                    ascii_art = self.frame_to_ascii(frame)
                else:
                    ascii_art = self.frame_to_ascii(frame)
                
                # Write frame separator and content
                f.write(f"=== FRAME {frame_count} ===\n")
                f.write(ascii_art)
                f.write("\n")
                
                frame_count += 1
                
                # Show progress
                if frame_count % 10 == 0:
                    progress = (frame_count / self.total_frames) * 100
                    print(f"Progress: {progress:.1f}% ({frame_count}/{self.total_frames} frames)", end='\r')
        
        self.cap.release()
        print(f"\n✅ Export complete! {frame_count} frames written to {output_path}")

def main():
    parser = argparse.ArgumentParser(
        description='Convert MP4 videos to insane ASCII art animations!',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s video.mp4                    # Basic conversion
  %(prog)s video.mp4 -w 150 -f 60       # High resolution, 60 FPS
  %(prog)s video.mp4 --color            # Colored ASCII (requires 24-bit color terminal)
  %(prog)s video.mp4 --style matrix     # Matrix-style characters
  %(prog)s video.mp4 --export           # Export to text file
  
Available styles: standard, detailed, blocks, simple, matrix, crazy
        """
    )
    
    parser.add_argument('video', help='Path to input video file')
    parser.add_argument('-w', '--width', type=int, default=100, 
                        help='Width of ASCII output in characters (default: 100)')
    parser.add_argument('-f', '--fps', type=int, default=30,
                        help='Playback FPS (default: 30)')
    parser.add_argument('-c', '--color', action='store_true',
                        help='Enable colored ASCII output (requires 24-bit color terminal)')
    parser.add_argument('-s', '--style', choices=ASCII_CHARS.keys(), default='detailed',
                        help='ASCII character style (default: detailed)')
    parser.add_argument('-l', '--loop', action='store_true',
                        help='Loop video playback')
    parser.add_argument('-e', '--export', action='store_true',
                        help='Export ASCII frames to text file')
    parser.add_argument('-o', '--output', type=str,
                        help='Output file path for export')
    parser.add_argument('--no-info', action='store_true',
                        help='Hide playback information')
    
    args = parser.parse_args()
    
    # Check if video file exists
    if not os.path.isfile(args.video):
        print(f"❌ Error: Video file '{args.video}' not found!")
        sys.exit(1)
    
    # Create converter
    converter = VideoToASCII(
        video_path=args.video,
        width=args.width,
        fps=args.fps,
        color=args.color,
        style=args.style
    )
    
    # Export or play
    if args.export:
        converter.export_to_file(args.output)
    else:
        converter.play_ascii_video(loop=args.loop, show_info=not args.no_info)

if __name__ == "__main__":
    main()