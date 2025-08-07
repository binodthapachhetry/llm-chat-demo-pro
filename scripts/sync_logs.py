import os, datetime, pathlib, datasets, json
LOG_DIR = pathlib.Path("logs")
day = datetime.date.today() - datetime.timedelta(days=1)
f = LOG_DIR / f"{day}.jsonl"
if not f.exists():
    print("No logs for", day)
else:
    ds = datasets.load_dataset("json", data_files=str(f), split="train")
    ds.push_to_hub(os.environ["HF_DATASET_NAME"], token=os.environ["HF_TOKEN"], split="train", private=True)
