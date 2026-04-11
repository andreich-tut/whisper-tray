"""Public app package preserving the `whisper_tray.app` import surface."""

from whisper_tray.adapters.tray import (
    PystrayTrayRuntime,
    QtTrayRuntime,
    TrayRuntime,
    should_use_qt_tray,
)
from whisper_tray.app.bootstrap import create_app
from whisper_tray.app.constants import OVERLAY_INSTALL_MESSAGE
from whisper_tray.app.lifecycle import WhisperTrayApp
from whisper_tray.app.session import AppSessionActions
from whisper_tray.app.ui import AppUiCoordinator
from whisper_tray.app.workflow import AppWorkflowCoordinator

__all__ = [
    "AppSessionActions",
    "AppUiCoordinator",
    "AppWorkflowCoordinator",
    "OVERLAY_INSTALL_MESSAGE",
    "PystrayTrayRuntime",
    "QtTrayRuntime",
    "TrayRuntime",
    "WhisperTrayApp",
    "create_app",
    "should_use_qt_tray",
]
