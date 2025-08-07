---
title: LLM Chat Demo and Eval
emoji: 🦉
colorFrom: indigo
colorTo: purple
sdk: gradio             # IMPORTANT
sdk_version: "4.15.0"   # or omit to use latest
app_file: app.py        # entry point
pinned: false
---

# LLM Chat Demo — Pro
Gradio-based chat UI with telemetry for evaluation & fine-tuning.

## Features
- Endpoint switcher (`endpoints.json`)
- JSONL logging with latency, token usage, model version
- PII scrubbing
- User rating widget
- Optional CloudWatch streaming via `CLOUDWATCH_LOG_GROUP`
- GitHub Action deploy + daily log sync to private HF dataset
