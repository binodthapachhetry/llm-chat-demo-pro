# LLM Chat Demo — Pro

Gradio-based chat UI with telemetry for evaluation & fine-tuning.

## Features
- Endpoint switcher (`endpoints.json`)
- JSONL logging with latency, token usage, model version
- PII scrubbing
- User rating widget
- Optional CloudWatch streaming via env var `CLOUDWATCH_LOG_GROUP`
- GitHub Action deploy + daily log sync to private HF dataset
