"""Upload immutable SD JSONL captures to Bee Link, retrying unacknowledged batches.

Runs on a PC/Pi after copying the SD file; does not implement ESP32 firmware.
Original captures are never changed. Re-running is safe via sequence deduplication.
"""
import argparse
import json
import os
import time
import urllib.request
import urllib.error


def upload_batch(url, samples, retries=5):
    wanted={(s["device_id"],s["capture_id"],s["sequence"]) for s in samples}
    payload=json.dumps({"samples":samples},allow_nan=False).encode()
    for attempt in range(retries):
        try:
            headers={"Content-Type":"application/json"}
            token=os.environ.get("BEELINK_TOKEN")
            if token:headers["Authorization"]="Bearer "+token
            req=urllib.request.Request(url.rstrip("/")+"/api/ingest",data=payload,headers=headers)
            with urllib.request.urlopen(req,timeout=30) as response:reply=json.load(response)
            confirmed={(a["device_id"],a["capture_id"],a["sequence"]) for a in reply["ack"] if a["status"] in {"stored","duplicate"}}
            if wanted!=confirmed:raise ValueError("receiver did not acknowledge the complete batch")
            return
        except urllib.error.HTTPError as e:
            if e.code<500:
                raise ValueError(f"receiver rejected batch ({e.code}): {e.read(500).decode(errors='replace')}") from None
            if attempt+1==retries:raise
        except (OSError,ValueError,KeyError):
            if attempt+1==retries:raise
        time.sleep(min(2**attempt,15))


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("capture")
    p.add_argument("--logger",default="http://127.0.0.1:8765")
    p.add_argument("--batch",type=int,default=50)
    args=p.parse_args()
    if not 1<=args.batch<=200:p.error("batch must be 1–200")
    batch=[];count=0
    with open(args.capture,encoding="utf-8") as source:
        for line in source:
            if not line.strip():continue
            sample=json.loads(line)
            if sample.get("source")=="demo":raise ValueError("Demo captures cannot enter the real logger")
            # Keep serialized upload below receiver's 2 MB cap.
            if batch and len(json.dumps({"samples":batch+[sample]}).encode())>1_900_000:
                upload_batch(args.logger,batch);count+=len(batch);batch=[]
            batch.append(sample)
            if len(batch)>=args.batch:
                upload_batch(args.logger,batch);count+=len(batch);batch=[]
        if batch:upload_batch(args.logger,batch);count+=len(batch)
    print(f"Acknowledged {count} samples. Original capture retained unchanged.")


if __name__=="__main__":main()
