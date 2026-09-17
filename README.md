# TREGO — Voice-first AI Computer Agent

> **Tell it. Let it go.**

TREGO is an AI computer agent that turns a user's natural language goal into a verified working result.

Instead of searching tutorials, copying terminal commands, and manually debugging errors, the user simply describes the desired outcome via voice or text.

Example:
> *"Set up my laptop for C++ development."*

TREGO then executes the full closed loop:

$$\text{Understand} \longrightarrow \text{Inspect} \longrightarrow \text{Diagnose} \longrightarrow \text{Clarify} \longrightarrow \text{Plan} \longrightarrow \text{Ask Permission} \longrightarrow \text{Act} \longrightarrow \text{Troubleshoot} \longrightarrow \text{Verify} \longrightarrow \text{Voice Result}$$

---

## 🌟 Key Features

### 1. Goal-Based Automation
Works from high-level objectives rather than manual commands. Converts requests into structured states, requirements, and verification criteria.

### 2. Deep Environment Inspection
Probes system toolchains (C++, Python, Flutter, Git, Android SDK) without blindly reinstalling or breaking existing functioning components.

### 3. Strict Command Policy & Permission Gates
Enterprise-grade security model:
- **Risk Classification**: `READ_ONLY`, `SAFE_MUTATION`, `HIGH_RISK`, `BLOCKED`.
- Gated execution requiring explicit human-in-the-loop approval (*What / Why / Impact*) for sensitive system actions.
- Hard blocklist for destructive commands, dangerous hotkeys, and shell-escape injections.

### 4. Modular Developer Environments
- **C++**: Detection of MinGW/GCC/Clang, PATH configuration, compilation of test programs, and binary execution verification.
- **Python**: Interpreter inspection, venv isolation, and package environment verification.
- **Flutter**: `flutter doctor -v` diagnostic parsing, Android SDK configuration, and real `flutter analyze` / `flutter test` verification.
- **Git & GitHub**: Stack auto-detection, dependency installation, and project onboarding.

### 5. Troubleshooting & Solutions Vector DB
Adaptive diagnostic loop:
$$\text{Error} \longrightarrow \text{Evidence Collection} \longrightarrow \text{Root Cause Diagnosis} \longrightarrow \text{Knowledge Base Search (pgvector)} \longrightarrow \text{Recovery Fix} \longrightarrow \text{Retest}$$

### 6. Mandatory Verification Engine
**TREGO never claims success based solely on command exit codes.** It executes real compilation, analysis, and runtime verification tests before declaring a task complete.

### 7. Voice Interaction Layer
- **Speech-to-Text (STT)**: Browser-based Web Speech API with real-time waveform input.
- **Text-to-Speech (TTS)**: ElevenLabs REST TTS integration for natural, contextual spoken updates.

---

## 🏗️ Architecture

```text
Voice / Text Input
        ↓
Goal Interpreter
        ↓
Environment Inspection
        ↓
Diagnosis
        ↓
Clarification ───────────────► User (when ambiguous)
        ↓
Plan
        ↓
Permission Gate (What / Why / Impact)
        ↓
Computer-Use Core Engine
 ┌──────┴──────────────┐
GUI                 Terminal (Policy-Enforced)
 └──────┬──────────────┘
        ↓
Observe (Screenshots & Process Output)
        ↓
Troubleshoot (Adaptive diagnostics + pgvector Knowledge Base)
        ↓
Retry / Adapt
        ↓
Verification (Mandatory Compile / Run / Test)
        ↓
Verified Result
        ↓
ElevenLabs Voice Response
```

---

## 🚀 Quick Start

### 1. Configure Environment
Copy `.env.example` to `.env` and set your API keys:
```env
LLM_MODEL=gpt-4o
LLM_API_KEY=your_llm_key
ELEVENLABS_API_KEY=your_elevenlabs_key
EXECUTOR_TOKEN=generate_or_set_token
```

### 2. Start Backend Server
```powershell
uvicorn server.app.main:app --host 0.0.0.0 --port 7860 --reload
```
Open `http://localhost:7860` in your browser.

### 3. Launch Windows Client Executor
```powershell
.\client\scripts\dev_all.ps1
```

### 4. Run Automated Test Suite
```powershell
python tests/run_all_tests.py
```

---

## 📂 Project Structure

```text
TREGO/
├── client/                     # Windows Client
│   ├── executor/               # Computer-Use Core Engine & DPI/pyautogui
│   └── scripts/                # Launchers, dev_all.ps1, PyQt5 Assistant
├── server/                     # Backend Services
│   ├── agent/                  # VLM Computer-use reasoning & tools
│   ├── app/                    # FastAPI WebSocket server & Web UI
│   │   └── static/             # TREGO Web UI, Goal Tracker & Voice STT
│   ├── db/                     # PostgreSQL + pgvector Knowledge Base
│   └── trego/                  # TREGO Orchestration Layer
│       ├── modules/            # C++, Python, Flutter, Git, GitHub modules
│       ├── clarification.py    # Intent clarification manager
│       ├── diagnostics.py      # Error pattern matcher
│       ├── goal.py             # Natural language goal interpreter
│       ├── inspector.py        # System environment inspector
│       ├── orchestrator.py     # 10-Phase Pipeline Orchestrator
│       ├── permissions.py      # Sensitive action permission gate
│       ├── troubleshooter.py   # Adaptive recovery engine
│       ├── verifier.py         # Mandatory verification engine
│       └── voice.py            # ElevenLabs TTS voice layer
├── shared/                     # Shared Protocols & Security
│   ├── command_policy.py       # Command allowlist & risk classifier
│   ├── config.py               # Central environment configuration
│   ├── protocol.py             # Wire types & event models
│   └── security.py             # Keystroke inspection & path validation
└── tests/                      # Automated Test Suite
    └── run_all_tests.py        # 14-test verification suite
```

---

## 📜 License
MIT
