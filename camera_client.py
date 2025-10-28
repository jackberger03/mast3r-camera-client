#!/usr/bin/env python3
"""
MASt3R Camera Client for Raspberry Pi Camera Module 3

Captures images from Raspberry Pi Camera Module 3, converts to PNG,
and uploads to MASt3R-SLAM server via HTTP POST.

Usage:
    python camera_client.py
    python camera_client.py --host linux-2 --port 5050 --fps 1
"""

import argparse
import io
import logging
import sys
import time
from datetime import datetime
from pathlib import Path

try:
    from picamera2 import Picamera2
    from picamera2.configuration import CameraConfiguration
except ImportError:
    print("ERROR: picamera2 not found. This must be run on a Raspberry Pi.")
    print("Install with: sudo apt install -y python3-picamera2")
    sys.exit(1)

try:
    import requests
except ImportError:
    print("ERROR: requests not found. Install with: pip install requests")
    sys.exit(1)


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class CameraClient:
    """Client for capturing and uploading camera images."""

    def __init__(self, host: str, port: int, fps: float = 1.0, save_local: bool = False):
        """
        Initialize camera client.

        Args:
            host: Hostname or IP of MASt3R-SLAM server
            port: Port number of MASt3R-SLAM server
            fps: Frames per second to capture (default: 1.0)
            save_local: Save images locally as well (default: False)
        """
        self.host = host
        self.port = port
        self.fps = fps
        self.interval = 1.0 / fps
        self.save_local = save_local
        self.upload_url = f"http://{host}:{port}/upload"

        # Create local save directory if needed
        if self.save_local:
            self.save_dir = Path("captured_images")
            self.save_dir.mkdir(exist_ok=True)

        # Initialize camera
        logger.info("Initializing Raspberry Pi Camera Module 3...")
        try:
            self.camera = Picamera2()

            # Configure camera for still capture
            config = self.camera.create_still_configuration(
                main={"size": (4608, 2592)},  # Camera Module 3 max resolution
                buffer_count=2
            )
            self.camera.configure(config)
            self.camera.start()

            # Give camera time to warm up
            time.sleep(2)

            logger.info("Camera initialized successfully")
            logger.info(f"Resolution: {config['main']['size']}")

        except Exception as e:
            logger.error(f"Failed to initialize camera: {e}")
            raise

        # Test connection to server
        self._test_connection()

    def _test_connection(self):
        """Test connection to MASt3R-SLAM server."""
        try:
            test_url = f"http://{self.host}:{self.port}/status"
            response = requests.get(test_url, timeout=5)
            if response.status_code == 200:
                logger.info(f"✓ Connected to MASt3R-SLAM server at {self.host}:{self.port}")
                logger.info(f"Server status: {response.json()}")
            else:
                logger.warning(f"Server returned status code: {response.status_code}")
        except requests.exceptions.RequestException as e:
            logger.error(f"⚠ Cannot connect to server at {self.host}:{self.port}")
            logger.error(f"Error: {e}")
            logger.warning("Will attempt to upload anyway...")

    def capture_and_convert(self) -> tuple[bytes, str]:
        """
        Capture image from camera as JPEG (server will convert to PNG).

        Returns:
            Tuple of (jpeg_bytes, filename)
        """
        # Capture image directly as JPEG
        jpeg_buffer = io.BytesIO()
        self.camera.capture_file(jpeg_buffer, format='jpeg')
        jpeg_bytes = jpeg_buffer.getvalue()

        # Generate filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        filename = f"raspi_cam_{timestamp}.jpg"

        return jpeg_bytes, filename

    def upload_image(self, jpeg_bytes: bytes, filename: str) -> bool:
        """
        Upload JPEG image to MASt3R-SLAM server.

        Args:
            jpeg_bytes: JPEG image as bytes
            filename: Filename for the image

        Returns:
            True if upload successful, False otherwise
        """
        try:
            files = {'file': (filename, jpeg_bytes, 'image/jpeg')}
            response = requests.post(self.upload_url, files=files, timeout=30)

            if response.status_code == 200:
                data = response.json()
                logger.info(f"✓ Uploaded: {filename} (Total images: {data.get('total_images', '?')})")
                return True
            else:
                logger.error(f"✗ Upload failed: {response.status_code}")
                logger.error(f"Response: {response.text}")
                return False

        except requests.exceptions.RequestException as e:
            logger.error(f"✗ Upload failed: {e}")
            return False

    def save_local_copy(self, jpeg_bytes: bytes, filename: str):
        """Save local copy of image."""
        save_path = self.save_dir / filename
        with open(save_path, 'wb') as f:
            f.write(jpeg_bytes)
        logger.debug(f"Saved local copy: {save_path}")

    def run(self):
        """Main capture and upload loop."""
        logger.info(f"Starting capture loop at {self.fps} FPS")
        logger.info(f"Uploading to: {self.upload_url}")
        logger.info("Press Ctrl+C to stop")

        frame_count = 0
        success_count = 0
        fail_count = 0

        try:
            while True:
                start_time = time.time()

                try:
                    # Capture as JPEG
                    jpeg_bytes, filename = self.capture_and_convert()
                    frame_count += 1

                    # Save local copy if enabled
                    if self.save_local:
                        self.save_local_copy(jpeg_bytes, filename)

                    # Upload to server
                    if self.upload_image(jpeg_bytes, filename):
                        success_count += 1
                    else:
                        fail_count += 1

                except Exception as e:
                    logger.error(f"Error processing frame: {e}")
                    fail_count += 1

                # Calculate sleep time to maintain FPS
                elapsed = time.time() - start_time
                sleep_time = max(0, self.interval - elapsed)

                if sleep_time > 0:
                    time.sleep(sleep_time)
                else:
                    logger.warning(f"Frame processing took {elapsed:.2f}s, longer than interval {self.interval:.2f}s")

        except KeyboardInterrupt:
            logger.info("\nStopping camera client...")
            logger.info(f"Statistics:")
            logger.info(f"  Total frames: {frame_count}")
            logger.info(f"  Successful uploads: {success_count}")
            logger.info(f"  Failed uploads: {fail_count}")

        finally:
            self.cleanup()

    def cleanup(self):
        """Clean up camera resources."""
        logger.info("Cleaning up...")
        if hasattr(self, 'camera'):
            self.camera.stop()
            self.camera.close()
        logger.info("Camera client stopped")


def main():
    parser = argparse.ArgumentParser(
        description="MASt3R Camera Client for Raspberry Pi Camera Module 3",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Default settings (1 FPS to linux-2:5050)
  python camera_client.py

  # Custom host and port
  python camera_client.py --host 192.168.1.100 --port 5050

  # Faster capture rate (2 FPS)
  python camera_client.py --fps 2

  # Save local copies
  python camera_client.py --save-local

  # Verbose logging
  python camera_client.py --verbose
        """
    )

    parser.add_argument(
        '--host',
        default='linux-2',
        help='Hostname or IP of MASt3R-SLAM server (default: linux-2)'
    )
    parser.add_argument(
        '--port',
        type=int,
        default=5050,
        help='Port of MASt3R-SLAM server (default: 5050)'
    )
    parser.add_argument(
        '--fps',
        type=float,
        default=1.0,
        help='Frames per second to capture (default: 1.0)'
    )
    parser.add_argument(
        '--save-local',
        action='store_true',
        help='Save images locally as well'
    )
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Enable verbose logging'
    )

    args = parser.parse_args()

    # Set logging level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Create and run client
    try:
        client = CameraClient(
            host=args.host,
            port=args.port,
            fps=args.fps,
            save_local=args.save_local
        )
        client.run()
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
