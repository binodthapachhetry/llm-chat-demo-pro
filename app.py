import gradio as gr
import requests, os, uuid, json, re, time, boto3, io
import datetime
from datetime import timezone

from pathlib import Path
from dotenv import load_dotenv
load_dotenv()

# ---------- Logging / Endpoint setup ----------
LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)

endpoint_specs = json.loads(Path("endpoints.json").read_text())["endpoints"]
ENDPOINTS = []
for spec in endpoint_specs:
    url = os.getenv(spec["env"], "").strip()
    if url:
        ENDPOINTS.append({"name": spec["name"], "url": url})

assert ENDPOINTS, "No endpoints resolved – check your environment variables!"
ENDPOINT_MAP   = {e["name"]: e["url"] for e in ENDPOINTS}
DEFAULT_ENDPOINT = ENDPOINTS[0]["name"]

CW_LOG_GROUP = os.getenv("CLOUDWATCH_LOG_GROUP")
CW_CLIENT = boto3.client("logs") if CW_LOG_GROUP else None
if CW_CLIENT:
    try: CW_CLIENT.create_log_group(logGroupName=CW_LOG_GROUP)
    except CW_CLIENT.exceptions.ResourceAlreadyExistsException: pass
    LOG_STREAM = datetime.datetime.now(timezone.utc).strftime("%Y-%m-%d")
    try: CW_CLIENT.create_log_stream(logGroupName=CW_LOG_GROUP, logStreamName=LOG_STREAM)
    except CW_CLIENT.exceptions.ResourceAlreadyExistsException: pass

PII_REGEX = re.compile(r"(\b\d{3}[-.]?\d{2}[-.]?\d{4}\b|\b\d{10}\b|[\w\.-]+@[\w\.-]+)")
def scrub(text): return PII_REGEX.sub("[REDACTED]", text)

def write_log(entry: dict):
    day_file = LOG_DIR / f"{datetime.datetime.now(timezone.utc).date()}.jsonl"
    day_file.open("a", encoding="utf-8").write(json.dumps(entry, ensure_ascii=False) + "\n")
    if CW_CLIENT:
        CW_CLIENT.put_log_events(
            logGroupName=CW_LOG_GROUP,
            logStreamName=LOG_STREAM,
            logEvents=[{"timestamp": int(time.time()*1000), "message": json.dumps(entry)}]
        )

# ---------- Helper to parse uploaded JSON ----------
def load_timeseries(file):
    if file is None:           # nothing uploaded
        return {}
    try:
        with io.open(file.name, "r", encoding="utf-8") as f:
            return json.load(f)          # parsed dict
    except Exception as e:
        return {"_error": f"Failed to parse JSON: {e}"}

# ---------- Chat handler ----------
def chat(user_input, history, endpoint_choice, ts_dict):
    timestamp = datetime.datetime.now(timezone.utc).isoformat()
    user_id   = str(uuid.uuid4())[:8]

    formatted_history = []
    for turn in history:
        if turn[0]:
            formatted_history.append({"role": "user",      "content": scrub(turn[0])})
        if len(turn) > 1 and turn[1]:
            formatted_history.append({"role": "assistant", "content": scrub(turn[1])})

    payload = {
        "user_id":   user_id,
        "timestamp": timestamp,
        "query":     scrub(user_input),
        "history":   formatted_history,
        "timeseries": ts_dict                 
    }

    endpoint_url = ENDPOINT_MAP.get(endpoint_choice)
    start = time.perf_counter()
    try:
        resp = requests.post(endpoint_url, json=payload, timeout=60).json()
        answer        = resp.get("answer", "")
        model_version = resp.get("model",  "unknown")
        usage         = resp.get("usage",  {})
    except Exception as e:
        answer, model_version, usage = f"Error contacting backend: {e}", "error", {}
    latency_ms = (time.perf_counter() - start) * 1000

    history.append((user_input, answer))

    write_log({
        "timestamp":    timestamp,
        "endpoint":     endpoint_url,
        "model_version":model_version,
        "latency_ms":   latency_ms,
        "token_usage":  usage,
        "payload":      payload,
        "answer":       answer,
        "rating":       None
    })
    return "", history, gr.update(value=None)

# ---------- Rating handler ----------
def rate_fn(rating, history):
    if rating and history:
        write_log({
            "timestamp": datetime.datetime.now(timezone.utc).isoformat(),
            "rating":    rating,
            "turn_index":len(history) - 1
        })
    return gr.update(value=None)

# ---------- UI ----------
with gr.Blocks(theme=gr.themes.Soft()) as demo:
    gr.Markdown("# 🦉 LLM Chat Demo and Eval")

    endpoint_dd = gr.Dropdown([e["name"] for e in ENDPOINTS],
                              value=DEFAULT_ENDPOINT, label="Endpoint")

    file_upload = gr.File(label="Upload Time-series JSON",file_types=[".json"])
    timeseries_state = gr.State({})

    chatbot = gr.Chatbot()
    with gr.Row():
        txt      = gr.Textbox(placeholder="Type your message", scale=8)
        send_btn = gr.Button("Send", scale=1)

    rating_radio = gr.Radio(["👍", "👎", "🤷"], label="Rate last answer")
    rate_btn     = gr.Button("Submit Rating")

    # Load / update timeseries state when file changes
    file_upload.change(fn=load_timeseries, inputs=file_upload, outputs=timeseries_state)

    # Send message
    send_btn.click(
        fn=chat,
        inputs=[txt, chatbot, endpoint_dd, timeseries_state],
        outputs=[txt, chatbot, rating_radio]
    )
    rate_btn.click(rate_fn, inputs=[rating_radio, chatbot], outputs=[rating_radio])

if __name__ == "__main__":
    demo.launch()
