# CPU-First Cross-Platform Transcription Optimization Prompt

**Date:** 2026-04-09  
**Status:** Draft

## Prompt

### Task

Analyze this Python desktop application and produce a concrete optimization plan to make Whisper-based transcription feel fast on **CPU-first systems** while keeping the app reliable across **Windows, Linux, and macOS**.

This is a push-to-talk tray app built around `faster-whisper`: hold a hotkey, speak for a short utterance, release, transcribe, copy to clipboard, optionally paste.

The system may support GPU acceleration, but GPU must be treated as **optional acceleration only**. The app must perform well on CPU by default, and GPU support must never make CPU behavior worse.

### Important Repo Context

Audit the current implementation, not a hypothetical architecture. In particular, inspect:

- `whisper_tray/config.py`
- `whisper_tray/audio/transcriber.py`
- `whisper_tray/audio/recorder.py`
- `whisper_tray/app.py`
- `whisper_tray/clipboard.py`
- `whisper_tray/input/hotkey.py`
- `whisper_tray/tray/menu.py`
- `README.md`
- `pyproject.toml`
- `tests/`

There are already some known issues in the current codebase that your analysis should confirm or correct:

- Defaults are currently GPU-first and heavy-model-first (`config.py:32-35`: `MODEL_SIZE=large-v3`, `DEVICE=cuda`, `COMPUTE_TYPE=float16`).
- Model loading is started in a background thread, but `run()` immediately calls `self._model_load_complete.wait()` with no timeout (`app.py:226`) — the tray icon never appears until the model is fully loaded, and if model loading hangs the process hangs forever.
- Each transcription currently runs in its own thread after hotkey release (`app.py:103-108`) with no queue, no concurrency guard, and no rejection of overlapping transcriptions. Rapid double-press spawns two concurrent `_model.transcribe()` calls.
- `AudioConfig()` is re-instantiated inside `transcribe()` on every call (`transcriber.py:179-180`), re-reading `os.getenv()` on the hot path. Additionally, VAD ONNX availability is re-checked via `importlib.util.find_spec` + `os.path.exists` on every transcription (`transcriber.py:204-209`).
- Auto-paste is not platform-aware: `clipboard.py:51-53` unconditionally uses `Key.ctrl + v`, which does not work on macOS (requires `Key.cmd + v`). The code even has a comment ("Micro-sleep for Windows clipboard registration") confirming Windows-only assumptions.
- On CPU-only machines with the default `DEVICE=cuda`, model loading attempts CUDA first, waits for it to fail, then reloads with CPU — effectively doubling cold-start time for the most common user configuration.
- `AudioConfig` parameters (`vad_threshold`, `vad_silence_duration_ms`, `min_recording_duration`, `sample_rate`) have no `os.getenv()` bindings — they are hardcoded constants with no user-facing control.
- `app.py:95` hard-codes `16000` as the sample rate instead of reading `self.config.audio.sample_rate`, creating a silent inconsistency if the config value ever changes.

### Goals

1. Make CPU the best-supported default path.
2. Reduce end-to-end latency for short utterances, especially 1-5 second push-to-talk recordings.
3. Keep transcription quality reasonable, with explicit speed vs quality trade-offs.
4. Preserve cross-platform portability for the core app logic.
5. Keep optional GPU acceleration available without adding CPU regressions.

### Deliverables

Provide:

1. A **prioritized list of optimizations**, highest impact first.
2. **Concrete code-level recommendations**, with file-level references where possible.
3. **Configuration changes**: new env vars, default values, presets, and documentation updates.
4. **Trade-offs**: speed vs quality, simplicity vs flexibility, CPU vs GPU behavior.
5. **Risks and regressions** introduced by each major change.
6. A **recommended rollout order**: what should be implemented first, second, third.
7. A short **test plan** covering config, startup, transcription behavior, and cross-platform edge cases.

### Required Analysis Areas

#### 1. Baseline and Measurement Strategy

Before recommending changes, define how to measure real improvement.

Include at least:

- Cold start time
- Time until tray icon becomes visible
- Time until model becomes ready
- First-transcription latency
- Median latency for 1s, 3s, and 5s utterances
- CPU utilization and thread usage during transcription

Focus on real-world push-to-talk latency, not just raw model throughput.

#### 2. Model Defaults and Presets

Recommend CPU-first defaults.

At minimum evaluate:

- Default model: `small` or `base`
- Optional higher-quality model: `medium`
- CPU default `compute_type="int8"`
- CPU default `device="cpu"`
- GPU only when explicitly enabled

Design presets such as:

- `fast`: low latency for short commands
- `balanced`: default general-purpose mode
- `accurate`: better quality for longer dictation

Do not just suggest presets abstractly. Specify which fields each preset should control.

#### 3. Decoding Strategy for Short Utterances

Evaluate decoding settings for push-to-talk usage.

At minimum analyze:

- `beam_size`
- greedy decoding vs beam search
- fixed language vs auto-detection
- `condition_on_previous_text`
- any other decoding flags that affect latency for short independent utterances

Assume most recordings are independent snippets, not one long continuous transcript.

#### 4. CPU Threading and Oversubscription

Recommend how the app should control CPU parallelism.

Include:

- a `CPU_THREADS` setting or equivalent
- interaction with `OMP_NUM_THREADS`
- avoiding oversubscription across model threads and app-created threads
- a portable strategy for choosing a safe default

Do not assume GPU concurrency rules apply to CPU.

#### 5. Concurrency and Work Scheduling

The current app spawns a background thread per transcription. Analyze whether that is correct for CPU-first use.

Evaluate options such as:

- single transcription worker thread with a queue
- reject new transcription while busy
- replace or cancel in-flight work

Be explicit about the user experience trade-off for each choice.

#### 6. Voice Activity Detection

Analyze current Silero VAD usage in the context of push-to-talk.

Because the app already knows when recording starts and stops, determine:

- when VAD adds value
- when VAD adds unnecessary latency
- whether VAD should be preset-based, duration-based, or disabled by default for short utterances

Recommend exact default behavior.

#### 7. Language Handling

Analyze the cost of auto language detection and whether fixed language should be the default.

Recommend:

- when to default to a fixed language
- when auto-detection is still worth keeping
- how the tray menu and config should interact

#### 8. Hot Path Cleanup

Look for avoidable overhead inside the transcription path.

The following are confirmed issues to address — do not just rediscover them, recommend fixes:

- `AudioConfig()` is constructed inside `transcribe()` on every call (`transcriber.py:179-180`), re-reading `os.getenv()` each time. It should be stored once at `Transcriber.__init__` time.
- The VAD ONNX availability check (`importlib.util.find_spec("faster_whisper")` + `os.path.exists`) runs on every transcription call (`transcriber.py:204-209`). The result should be cached as an instance variable when the model loads.
- Evaluate any logging or branching that adds overhead on every short transcription.

Recommend what should be cached at startup or model-load time.

#### 9. Audio Pipeline

Review the recording path for short-utterance latency.

Analyze:

- whether `.copy()` calls are necessary
- how chunks are stored and flattened
- whether concatenation/flattening is efficient enough for typical clip sizes
- whether any audio preprocessing is redundant

Focus on meaningful wins, not micro-optimizations without measurable benefit.

#### 10. Startup and Perceived Latency

The tray icon should appear quickly even if the model is still loading.

The confirmed blocker is `app.py:226`: `self._model_load_complete.wait()` is called unconditionally after starting the background thread, with no timeout. The tray icon is not created until this line returns, so the app is invisible to the user during the entire model load. If model loading hangs or fails silently, the process hangs forever.

Fix this specific call. Evaluate:

- showing tray UI immediately, before model loading begins
- loading the model asynchronously without blocking `run()`
- disabling recording until model is ready (already partially wired via `is_ready` checks)
- user feedback while loading (tooltip or icon state)
- adding a timeout or failure path to the model load so a failed load surfaces to the user

#### 11. Cross-Platform Architecture and Runtime Behavior

Analyze real cross-platform readiness, not just code organization.

Evaluate:

- separation between core logic and platform adapters
- whether OS-specific imports happen too early
- whether clipboard and paste behavior is OS-aware
- whether the hotkey implementation is portable enough
- packaging and dependency issues that differ across Windows, Linux, and macOS

Recommend where abstraction boundaries should be introduced or strengthened.

#### 12. Optional GPU Acceleration

GPU support must remain optional.

The current behavior has a confirmed double-load problem: with the default `DEVICE=cuda`, `load_model()` always attempts CUDA first (`transcriber.py:126-143`), waits for it to fail (which may take several seconds), then reloads the model with CPU. On the most common user configuration (no GPU), cold-start time is roughly doubled because the model is loaded twice.

Analyze and fix:

- how GPU should be enabled explicitly (opt-in, not opt-out)
- how to skip the CUDA attempt entirely when GPU is not requested, avoiding the double-load penalty
- how to keep CPU startup fast when GPU is absent — the goal is one model load, not two
- whether the code path and user-visible behavior stay consistent between CPU and GPU modes

Do not recommend GPU-first defaults.

#### 13. Documentation, Config Surface, and Tests

Recommend the config and documentation changes needed to support the new behavior.

Include:

- `.env` variables and defaults — note that `AudioConfig` currently has **no env var bindings at all**: `VAD_THRESHOLD`, `VAD_SILENCE_DURATION_MS`, `MIN_RECORDING_DURATION`, and `SAMPLE_RATE` are all hardcoded constants with no `os.getenv()` support. Decide which of these should be user-configurable and add bindings.
- README updates
- troubleshooting updates
- tests that should be added or changed

Pay attention to the fact that changing defaults will require updating existing tests and docs.

### Constraints

- Must work efficiently without GPU.
- Must stay portable across Windows, Linux, and macOS.
- GPU is optional acceleration only.
- Prioritize real latency wins for short utterances.
- Prefer practical, incremental improvements over large speculative rewrites.

### Output Format

Structure the answer as:

1. **Top Priorities**
2. **Detailed Recommendations by Area**
3. **Suggested Config Defaults and Presets**
4. **Risks / Trade-offs**
5. **Recommended Implementation Order**
6. **Testing Plan**

Be specific. If you suggest a change, tie it to the current code and explain why it matters for CPU-first latency or cross-platform reliability.
