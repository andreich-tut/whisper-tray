"""
WhisperTray - Global speech-to-text system tray application.

Hold Ctrl+Space to record, release to transcribe.
Transcription is copied to clipboard and auto-pasted.

Uses faster-whisper with local model for transcription.
"""

from __future__ import annotations

import importlib.util
import io
import logging
import os
import queue
import shutil
import sys
import threading
import time
from typing import Optional

import numpy as np
import pyperclip
import pystray
import sounddevice as sd
from faster_whisper import WhisperModel
from PIL import Image, ImageDraw
from pynput import keyboard
from pynput.keyboard import Controller as KeyboardController

# Try to load .env file if python-dotenv is available
try:
    from dotenv import load_dotenv

    # Load .env from current directory or parent directory
    load_dotenv()
except ImportError:
    pass  # python-dotenv not installed, rely on environment variables only

# Setup logging to file
logging.basicConfig(
    filename="whisper_tray.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# =============================================================================
# PyInstaller Runtime Data Path Fix
# =============================================================================
# When bundled with PyInstaller, data files are extracted to _internal folder.
# We need to ensure faster-whisper can find its ONNX models.


def ensure_faster_whisper_assets() -> None:
    """
    Ensure faster-whisper can find its ONNX model files.

    When bundled with PyInstaller, data files may be extracted to different locations.
    This function verifies the ONNX file exists and attempts to locate it if missing.
    """
    try:
        # Find faster-whisper package location
        fw_spec = importlib.util.find_spec("faster_whisper")
        if not fw_spec or not fw_spec.origin:
            logger.warning("Could not find faster_whisper package location")
            return

        fw_dir = os.path.dirname(fw_spec.origin)
        assets_dir = os.path.join(fw_dir, "assets")
        onnx_file = os.path.join(assets_dir, "silero_vad_v6.onnx")

        # Check if ONNX file already exists (common when running as script)
        if os.path.exists(onnx_file):
            logger.info(f"ONNX file found at: {onnx_file}")
            return

        # File doesn't exist - only try to copy when bundled with PyInstaller
        if not getattr(sys, "frozen", False):
            logger.warning(
                f"ONNX file not found at {onnx_file} and not running as bundled app"
            )
            return

        logger.info(f"ONNX file not found at {onnx_file}, attempting to locate it...")

        # When bundled, PyInstaller extracts to _MEIPASS temp directory
        # Files are placed in faster_whisper/assets/ relative to _MEIPASS
        meipass = getattr(sys, "_MEIPASS", os.path.dirname(sys.executable))
        exe_dir = os.path.dirname(sys.executable)

        # Search in multiple possible locations
        possible_sources = [
            # PyInstaller _MEIPASS location (most common)
            os.path.join(meipass, "faster_whisper", "assets"),
            # _internal folder structure (onedir mode)
            os.path.join(exe_dir, "_internal", "faster_whisper", "assets"),
            os.path.join(exe_dir, "faster_whisper", "assets"),
            # Alternative naming
            os.path.join(meipass, "faster_whisper_assets"),
            os.path.join(exe_dir, "_internal", "faster_whisper_assets"),
        ]

        # Create assets directory if needed
        os.makedirs(assets_dir, exist_ok=True)

        # Try to find and copy ONNX files from possible source locations
        for source_dir in possible_sources:
            source_onnx = os.path.join(source_dir, "silero_vad_v6.onnx")
            if os.path.exists(source_onnx):
                shutil.copy2(source_onnx, onnx_file)
                logger.info(f"Copied ONNX file from {source_dir} to {assets_dir}")
                return

        # Also try to find any .onnx files in source directories
        for source_dir in possible_sources:
            if os.path.exists(source_dir):
                for f in os.listdir(source_dir):
                    if f.endswith(".onnx"):
                        dest_onnx = os.path.join(assets_dir, f)
                        shutil.copy2(os.path.join(source_dir, f), dest_onnx)
                        logger.info(f"Copied {f} from {source_dir} to {assets_dir}")
                        return

        logger.warning(f"Could not find ONNX files. Checked: {possible_sources}")
        logger.warning("VAD filter may not work. Consider reinstalling faster-whisper.")

    except Exception as e:
        logger.error(f"Error setting up faster-whisper assets: {e}")


# Call this early in module load
ensure_faster_whisper_assets()


# =============================================================================
# Configuration
# =============================================================================

# Local mode settings
MODEL_SIZE: str = "large-v3"
DEVICE: str = os.getenv("DEVICE", "cuda")
COMPUTE_TYPE: str = os.getenv("COMPUTE_TYPE", "float16")

# Hotkey and behavior settings
HOTKEY: set[str] = {"ctrl", "space"}  # Simpler 2-key combo for better reliability
AUTO_PASTE: bool = True
PASTE_DELAY: float = 0.1
SAMPLE_RATE: int = 16000
MIN_RECORDING_DURATION: float = 0.3
VAD_THRESHOLD: float = 0.5
VAD_SILENCE_DURATION_MS: int = 500

# =============================================================================
# Global State
# =============================================================================

model: Optional[WhisperModel] = None
model_ready: bool = False
model_device: str = DEVICE  # Track actual device (may fallback to cpu)
is_recording: bool = False
current_keys: set[str] = set()
audio_queue: queue.Queue = queue.Queue()
current_language: str = "auto"  # "en", "ru", or "auto"
auto_paste_enabled: bool = AUTO_PASTE


# =============================================================================
# Model Loading
# =============================================================================

# No tkinter - it conflicts with pystray. Use logging for progress.


# =============================================================================
# Audio Streaming
# =============================================================================


def audio_callback(
    indata: np.ndarray, frames: int, time_info: dict, status: sd.CallbackFlags
) -> None:
    """Callback for audio stream - pushes chunks to queue."""
    if status:
        logger.info(f"Audio stream status: {status}")
    # indata is shape (frames, channels) - we want float32 mono
    audio_queue.put(indata.copy())


def start_recording() -> None:
    """Start audio recording stream."""
    global audio_queue, _current_stream

    # Clear any old data
    while not audio_queue.empty():
        try:
            audio_queue.get_nowait()
        except queue.Empty:
            break

    # Start stream
    try:
        _current_stream = sd.InputStream(
            samplerate=SAMPLE_RATE,
            channels=1,
            dtype="float32",
            callback=audio_callback,
        )
        _current_stream.start()
        logger.info("Audio recording stream started successfully")
    except Exception as e:
        logger.error(f"Failed to start audio recording: {e}")
        raise


def stop_recording() -> np.ndarray:
    """
    Stop recording and return concatenated audio.

    Returns:
        Flat numpy array of all recorded audio samples.
    """
    global _current_stream

    # Stop and close stream
    _current_stream.stop()
    _current_stream.close()

    # Collect all chunks
    chunks = []
    while not audio_queue.empty():
        try:
            chunk = audio_queue.get_nowait()
            chunks.append(chunk)
        except queue.Empty:
            break

    # Concatenate into single array
    if chunks:
        audio_data = np.concatenate(chunks, axis=0)
        return audio_data.flatten()
    else:
        return np.array([], dtype=np.float32)


# =============================================================================
# Transcription
# =============================================================================


def transcribe_audio(audio_data: np.ndarray) -> Optional[str]:
    """
    Transcribe audio data using faster-whisper.

    Args:
        audio_data: Flat numpy array of audio samples (float32, 16kHz)

    Returns:
        Transcribed text or None if failed/too short
    """
    global model, model_device, model_ready, current_language

    # Check duration
    duration = len(audio_data) / SAMPLE_RATE
    if duration < MIN_RECORDING_DURATION:
        logger.info(f"Recording too short: {duration:.2f}s < {MIN_RECORDING_DURATION}s")
        return None

    if model is None:
        logger.info("Error: Model not loaded")
        return None

    # Determine language parameter
    language_param = None if current_language == "auto" else current_language

    try:
        # Check if VAD ONNX file exists
        fw_spec = importlib.util.find_spec("faster_whisper")
        vad_onnx_exists = False
        if fw_spec and fw_spec.origin:
            fw_dir = os.path.dirname(fw_spec.origin)
            vad_onnx_path = os.path.join(fw_dir, "assets", "silero_vad_v6.onnx")
            vad_onnx_exists = os.path.exists(vad_onnx_path)

        # Use VAD if available, otherwise fall back to no VAD
        if vad_onnx_exists:
            # Transcribe with VAD filter
            segments, info = model.transcribe(
                audio_data,
                language=language_param,
                vad_filter=True,
                vad_parameters=dict(
                    min_silence_duration_ms=VAD_SILENCE_DURATION_MS,
                    threshold=VAD_THRESHOLD,
                ),
            )
        else:
            # Fallback: transcribe without VAD
            logger.warning(
                "VAD ONNX file not found, transcribing without VAD filter"
            )
            segments, info = model.transcribe(
                audio_data,
                language=language_param,
                vad_filter=False,
            )

        # Collect all segments
        text_parts = []
        for segment in segments:
            text_parts.append(segment.text)

        result_text = " ".join(text_parts).strip()

        if not result_text:
            if vad_onnx_exists:
                logger.info("No speech detected (VAD filtered everything)")
            else:
                logger.info("No speech detected")
            return None

        logger.info(f"Transcription ({info.language}): {result_text}")
        return result_text

    except Exception as e:
        error_msg = str(e)
        logger.error(f"Transcription error: {error_msg}")

        # Detect CUDA DLL missing error
        if "dll is not found" in error_msg or "cublas" in error_msg.lower():
            logger.warning(
                "CUDA DLL missing! This executable was built without CUDA DLLs.\n"
                "Options:\n"
                "  1. Rebuild with updated .spec file (bundles CUDA DLLs automatically)\n"
                "  2. Set DEVICE=cpu in environment to force CPU mode\n"
                "  3. Install CUDA Toolkit and rebuild"
            )
            # Try to reload model with CPU
            if model_device != "cpu":
                logger.info("Attempting to reload model with CPU...")
                try:
                    language_param = None if current_language == "auto" else current_language
                    model = WhisperModel(
                        MODEL_SIZE, device="cpu", compute_type="int8"
                    )
                    model_device = "cpu"
                    model_ready = True
                    logger.info("Model reloaded with CPU mode. Retrying transcription...")
                    # Retry transcription with CPU
                    segments, info = model.transcribe(
                        audio_data,
                        language=language_param,
                        vad_filter=False,
                    )
                    text_parts = []
                    for segment in segments:
                        text_parts.append(segment.text)
                    result_text = " ".join(text_parts).strip()
                    if result_text:
                        logger.info(f"Transcription (CPU fallback): {result_text}")
                        return result_text
                except Exception as retry_error:
                    logger.error(f"CPU fallback also failed: {retry_error}")

        return None


# =============================================================================
# Clipboard and Paste
# =============================================================================


# Keyboard controller for paste simulation
_keyboard_controller = KeyboardController()


def copy_and_paste(text: str) -> None:
    """
    Copy text to clipboard and optionally auto-paste.

    Args:
        text: Text to copy and paste
    """
    global auto_paste_enabled, PASTE_DELAY

    # Copy to clipboard
    pyperclip.copy(text)
    logger.info("Text copied to clipboard")

    # Auto-paste if enabled
    if auto_paste_enabled:
        time.sleep(PASTE_DELAY)
        # Micro-sleep for Windows clipboard registration
        time.sleep(0.05)
        # Simulate Ctrl+V using pynput
        with _keyboard_controller.pressed(keyboard.Key.ctrl):
            _keyboard_controller.press("v")
            _keyboard_controller.release("v")
        logger.info("Text auto-pasted")


# =============================================================================
# Hotkey Handler
# =============================================================================


def get_key_name(key: keyboard.Key | keyboard.KeyCode) -> str:
    """Extract key name from pynput key object."""
    if hasattr(key, "char") and key.char is not None:
        return key.char.lower()
    elif hasattr(key, "name"):
        key_name = key.name.lower()
        # Normalize modifier keys (ctrl_l/ctrl_r -> ctrl, etc.)
        if key_name.startswith("ctrl"):
            return "ctrl"
        elif key_name.startswith("shift"):
            return "shift"
        elif key_name.startswith("alt"):
            return "alt"
        elif key_name.startswith("cmd") or key_name.startswith("win"):
            return "cmd"
        elif "space" in key_name:
            return "space"
        return key_name
    else:
        # Handle special keys
        key_str = str(key).lower()
        if "ctrl" in key_str:
            return "ctrl"
        elif "shift" in key_str:
            return "shift"
        elif "space" in key_str or "bar" in key_str:
            return "space"
        elif "alt" in key_str:
            return "alt"
        elif "cmd" in key_str or "win" in key_str:
            return "cmd"
        return key_str


def on_press(key: keyboard.Key | keyboard.KeyCode) -> None:
    """Handle key press events."""
    global current_keys, is_recording

    key_name = get_key_name(key)
    current_keys.add(key_name)
    logger.info(
        f"Key pressed: {key_name}, current_keys: {current_keys}, is_recording: {is_recording}, model_ready: {model_ready}"
    )

    # Check if hotkey combination is pressed and not already recording
    if HOTKEY.issubset(current_keys) and not is_recording:
        logger.info("Hotkey combination detected!")
        start_transcription_flow()


def on_release(key: keyboard.Key | keyboard.KeyCode) -> None:
    """Handle key release events."""
    global current_keys, is_recording

    key_name = get_key_name(key)
    current_keys.discard(key_name)

    # Check if hotkey combination is broken and we were recording
    if is_recording and not HOTKEY.issubset(current_keys):
        finish_transcription_flow()


def start_transcription_flow() -> None:
    """Start recording when hotkey is pressed."""
    global is_recording

    if not model_ready:
        logger.info("Model not ready, ignoring hotkey")
        return

    is_recording = True
    start_recording()
    logger.info("Recording started...")

    # Update tray icon if possible
    update_tray_icon()


def finish_transcription_flow() -> None:
    """Stop recording and transcribe when hotkey is released."""
    global is_recording

    is_recording = False
    audio_data = stop_recording()
    logger.info(f"Recording stopped. Captured {len(audio_data)} samples.")

    # Transcribe in a separate thread to not block hotkey listener
    threading.Thread(
        target=process_transcription, args=(audio_data,), daemon=True
    ).start()

    # Update tray icon
    update_tray_icon()


def process_transcription(audio_data: np.ndarray) -> None:
    """Process transcription in background thread."""
    text = transcribe_audio(audio_data)
    if text:
        logger.info(f"Recognized text: {text}")
        copy_and_paste(text)


# =============================================================================
# Tray Icon
# =============================================================================

_current_icon: Optional[pystray.Icon] = None


def create_icon_image(color: str, size: int = 64) -> Image.Image:
    """
    Create a circular icon with specified color.

    Args:
        color: Color name (e.g., "gray", "red")
        size: Icon size in pixels

    Returns:
        PIL Image with circular icon
    """
    image = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)

    # Draw circle
    margin = 4
    draw.ellipse([margin, margin, size - margin, size - margin], fill=color)

    # Add border
    draw.ellipse(
        [margin, margin, size - margin, size - margin], outline="white", width=2
    )

    return image


def get_icon_image() -> Image.Image:
    """Get current icon image based on state."""
    if is_recording:
        return create_icon_image("red")
    elif not model_ready:
        return create_icon_image("yellow")
    else:
        return create_icon_image("gray")


def update_tray_icon() -> None:
    """Update the tray icon to reflect current state."""
    global _current_icon

    if _current_icon is not None:
        try:
            _current_icon.icon = get_icon_image()
        except Exception as e:
            logger.info(f"Error updating icon: {e}")


def on_tray_clicked(icon: pystray.Icon, item: pystray.MenuItem | None = None) -> None:
    """Handle tray icon clicks."""
    pass


def toggle_auto_paste(icon: pystray.Icon, item: pystray.MenuItem | None = None) -> None:
    """Toggle auto-paste setting."""
    global auto_paste_enabled
    auto_paste_enabled = not auto_paste_enabled
    status = "enabled" if auto_paste_enabled else "disabled"
    logger.info(f"Auto-paste {status}")
    icon.notify(f"Auto-paste {status}")


def set_language_en(icon: pystray.Icon, item: pystray.MenuItem | None = None) -> None:
    """Set transcription language to English."""
    global current_language
    current_language = "en"
    icon.notify("Language: English")


def set_language_ru(icon: pystray.Icon, item: pystray.MenuItem | None = None) -> None:
    """Set transcription language to Russian."""
    global current_language
    current_language = "ru"
    icon.notify("Language: Russian")


def set_language_auto(icon: pystray.Icon, item: pystray.MenuItem | None = None) -> None:
    """Set transcription language to auto-detect."""
    global current_language
    current_language = "auto"
    icon.notify("Language: Auto-detect")


def get_language_checked(lang: str) -> bool:
    """Check if a language is currently selected."""
    return current_language == lang


def exit_app(icon: pystray.Icon, item: pystray.MenuItem | None = None) -> None:
    """Exit the application."""
    icon.stop()


def create_menu() -> tuple:
    """Create tray icon context menu."""
    # Create language submenu items
    language_menu = pystray.Menu(
        pystray.MenuItem(
            "English",
            set_language_en,
            checked=lambda _: get_language_checked("en"),
        ),
        pystray.MenuItem(
            "Russian",
            set_language_ru,
            checked=lambda _: get_language_checked("ru"),
        ),
        pystray.MenuItem(
            "Auto-Detect",
            set_language_auto,
            checked=lambda _: get_language_checked("auto"),
        ),
    )

    return (
        pystray.MenuItem("Language", language_menu),
        pystray.MenuItem(
            "Toggle Auto-Paste",
            toggle_auto_paste,
            checked=lambda _: auto_paste_enabled,
        ),
        pystray.MenuItem("Exit", exit_app),
    )


def get_tooltip() -> str:
    """Get current tooltip text."""
    if not model_ready:
        return "Loading model..."
    elif is_recording:
        return "Recording..."
    elif model_device == "cpu":
        return "WhisperTray (CPU mode) - Ready"
    else:
        return "WhisperTray (GPU mode) - Ready"


# =============================================================================
# Main Entry Point
# =============================================================================

_keyboard_listener: Optional[keyboard.Listener] = None
_model_load_complete = threading.Event()


def load_model_in_background() -> None:
    """Load model in background thread and signal when complete."""
    global model, model_ready, model_device

    try:
        logger.info(f"Loading Whisper model ({MODEL_SIZE})...")

        # Try CUDA first
        try:
            logger.info(f"Loading model with CUDA ({DEVICE}, {COMPUTE_TYPE})...")
            loaded_model = WhisperModel(
                MODEL_SIZE, device=DEVICE, compute_type=COMPUTE_TYPE
            )
            model_device = DEVICE
            logger.info("Model loaded successfully with CUDA.")
        except Exception as e:
            logger.info(f"CUDA failed: {e}, falling back to CPU...")
            loaded_model = WhisperModel(MODEL_SIZE, device="cpu", compute_type="int8")
            model_device = "cpu"
            logger.info("Model loaded successfully with CPU.")

        model = loaded_model
        model_ready = True
        logger.info(f"Model ready (device: {model_device})")
    except Exception as e:
        logger.info(f"Critical error loading model: {e}")
        model_ready = False

    _model_load_complete.set()


def main() -> None:
    """Main entry point for WhisperTray application."""
    global _keyboard_listener, model_ready

    logger.info("Starting WhisperTray...")
    logger.info(f"Hotkey: {'+'.join(sorted(HOTKEY))}")
    logger.info(f"Auto-paste: {AUTO_PASTE}")

    # Start model loading in background thread
    threading.Thread(
        target=load_model_in_background,
        daemon=True,
    ).start()

    # Wait for model to be ready
    _model_load_complete.wait()

    # Create tray icon after model is loaded
    icon_image = create_icon_image("gray" if model_ready else "yellow")

    # Determine tooltip based on device
    if model_device == "cpu":
        tooltip = "WhisperTray (CPU mode) - Ready"
    else:
        tooltip = "WhisperTray (GPU mode) - Ready"

    # Create tray icon
    icon = pystray.Icon(
        "WhisperTray",
        icon_image,
        tooltip,
        create_menu(),
    )

    # Start keyboard listener
    _keyboard_listener = keyboard.Listener(on_press=on_press, on_release=on_release)
    _keyboard_listener.start()
    logger.info("Keyboard listener started")

    # Run tray icon (blocks main thread)
    icon.run()

    # Cleanup
    if _keyboard_listener:
        _keyboard_listener.stop()
    logger.info("WhisperTray exited.")


if __name__ == "__main__":
    main()
