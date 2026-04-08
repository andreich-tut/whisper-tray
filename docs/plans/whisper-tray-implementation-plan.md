# **WhisperTray Implementation Plan (Revised)**

## **Phase 1: Project Setup**

### **1.1 Create Directory Structure**

Plaintext

whisper-tray/  
├── whisper\_tray/  
│   ├── \_\_init\_\_.py  
│   ├── whisper\_tray.py      \# Main application  
│   ├── requirements.txt     \# Pinned dependencies  
│   └── README.md            \# Setup and usage docs  
├── docs/  
│   └── plans/  
│       └── whisper-tray-implementation-plan.md

### **1.2 Define Dependencies (requirements.txt)**

Pin exact versions for stability:

* faster-whisper \- Whisper inference engine  
* sounddevice \- Audio stream recording  
* numpy \- Audio data manipulation  
* pynput \- Global hotkey detection  
* pystray \- System tray icon  
* Pillow \- Icon image handling  
* pyperclip \- Clipboard operations  
* pyautogui \- Paste simulation

## ---

**Phase 2: Core Application Development**

### **2.1 Configuration Module**

**Location:** Top of whisper\_tray.py

Define editable constants:

| Constant | Default | Description |

| :--- | :--- | :--- |

| MODEL\_SIZE | "large-v3" | Whisper model variant |

| DEVICE | "cuda" | Primary inference device |

| COMPUTE\_TYPE | "float16" | CUDA precision |

| HOTKEY | {Ctrl, Shift, Space} | Recording trigger keys |

| AUTO\_PASTE | True | Enable auto-paste feature |

| PASTE\_DELAY | 0.1 | Seconds before Ctrl+V fires |

| SAMPLE\_RATE | 16000 | Audio sample rate (Hz) |

| MIN\_RECORDING\_DURATION | 0.3 | Minimum recording length (seconds) |

| VAD\_THRESHOLD | 0.5 | Speech probability threshold |

### **2.2 Global State Management**

Track application state safely across threads:

* model: Loaded Whisper model object  
* model\_ready: Boolean flag  
* is\_recording: Boolean flag  
* current\_keys: Set of currently pressed keys (for debouncing Windows auto-repeat)  
* audio\_queue: queue.Queue() for thread-safe audio chunk collection  
* current\_language: String (e.g., "en", "ru", or "auto")

### **2.3 Model Loading & Fallback (Background Thread)**

**Requirements:**

* Load faster-whisper model asynchronously so pystray can render immediately.  
* Show "Loading model…" tooltip during load.  
* **Improvement:** Wrap in try/except. If CUDA initialization fails (e.g., missing cuDNN), catch the error, log to stdout, and dynamically fall back to device="cpu" and compute\_type="int8". Update tray tooltip to indicate CPU mode.

### **2.4 Audio Streaming System**

**Using:** sounddevice.InputStream \+ queue.Queue

**Specifications:**

* Start stream on hotkey trigger.  
* Stream callback pushes float32 chunks into audio\_queue.  
* Stop and close stream on hotkey release.

### **2.5 Transcription Pipeline**

**Steps:**

1. Empty audio\_queue into a flat numpy array.  
2. Calculate duration; abort if \< MIN\_RECORDING\_DURATION.  
3. Pass array to model.transcribe().  
4. **VAD Parameters:** min\_silence\_duration\_ms=500, threshold=VAD\_THRESHOLD.  
5. **Language:** Pass current\_language (unless set to "auto").

### **2.6 Clipboard and Paste System**

**Steps:**

1. Copy transcription to clipboard (pyperclip.copy()).  
2. If AUTO\_PASTE enabled:  
   * Wait PASTE\_DELAY seconds.  
   * **Improvement:** Add a time.sleep(0.05) micro-sleep immediately after the copy action to ensure Windows OS clipboard registration completes.  
   * Simulate Ctrl+V (pyautogui.hotkey('ctrl', 'v')).

### **2.7 Global Hotkey Handler (Debounced)**

**Using:** pynput.keyboard.Listener

**Logic:**

* **On Press:** Add key to current\_keys. If current\_keys matches HOTKEY and not is\_recording: Start stream, set is\_recording \= True, clear old queue data, update icon. *(This debounces the OS key-repeat).*  
* **On Release:** Remove key from current\_keys. If is\_recording and HOTKEY subset is broken: Stop stream, trigger transcription thread, set is\_recording \= False, update icon.

### **2.8 System Tray Icon & UI**

**Using:** pystray \+ Pillow

**Context Menu Structure:**

* **Language (Sub-menu):**  
  * English (Radio button)  
  * Russian (Radio button)  
  * Auto-Detect (Radio button)  
* **Toggle Auto-Paste:** Checkbox/Toggle showing state.  
* **Exit:** Terminates app.

## ---

**Phase 3: Error Handling & Edge Cases**

### **3.1 Error Categories**

| Error Type | Handling |
| :---- | :---- |
| CUDA Unavailable | Fallback to CPU (int8), update tooltip, continue. |
| Key Bouncing | Ignored via current\_keys state tracking. |
| Recording \< 0.3s | Ignored, queue dumped, print warning to stdout. |
| Threading Locks | pystray.Icon.run() blocks main thread; hotkeys/audio/model load run safely in background. |

## ---

**Phase 4 & 5: Documentation and Code Quality**

*(Remains identical to your original plan: standard README setup, strict formatting via black/isort/flake8, manual testing checklist.)*