"""
Test script to verify pystray works on Windows.
Run this FIRST to check if tray icon appears.
"""

import logging
import sys

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler("test_tray.log"), logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)

try:
    import pystray
    from PIL import Image, ImageDraw

    logger.info("pystray and PIL imported successfully")
except Exception as e:
    logger.error(f"Failed to import dependencies: {e}")
    input("Press Enter to exit...")
    sys.exit(1)


def create_test_icon():
    """Create a simple blue test icon."""
    size = 64
    image = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    draw.ellipse([4, 4, 60, 60], fill="blue")
    draw.ellipse([4, 4, 60, 60], outline="white", width=2)
    return image


def on_exit(icon, item=None):
    logger.info("Exit clicked")
    icon.stop()


def main():
    logger.info("Creating test tray icon...")
    print("\n" + "=" * 60)
    print("TEST TRAY ICON")
    print("=" * 60)
    print("\nIf you see a BLUE icon in the system tray, pystray works!")
    print("Click the ^ arrow in the system tray if you don't see it.")
    print("\nRight-click the icon and select 'Exit' to close.\n")

    menu = pystray.Menu(pystray.MenuItem("Exit", on_exit))

    icon = pystray.Icon(
        "TestTray",
        create_test_icon(),
        "Test Tray Icon - Click ^ arrow if not visible",
        menu,
    )

    logger.info("Starting tray icon event loop...")
    print("Tray icon should appear now...")
    icon.run()

    logger.info("Tray icon closed")
    print("\nTray icon closed. Test complete!")
    input("\nPress Enter to exit...")


if __name__ == "__main__":
    main()
