"""CLI도 브라우저와 동일한 state/save 엔드포인트를 사용합니다."""

import argparse
import json
import os
import uuid
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


def call(path, *, method="GET", data=None, key=None):
    headers = {
        "Coders-Grant": os.environ["CODERS_GRANT"],
        "Coders-Budget": "4",
        "Idempotency-Key": key or str(uuid.uuid4()),
        "Content-Type": "application/json",
    }
    if resource := os.getenv("CODERS_RESOURCE"):
        headers["Coders-Resource"] = resource
    request = Request(
        os.environ["CODERS_APP_URL"].rstrip("/") + path,
        method=method,
        headers=headers,
        data=json.dumps(data).encode() if data else None,
    )
    with urlopen(request, timeout=30) as response:
        return json.load(response)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--connection", default=os.getenv("CODERS_AGENT_CONNECTION"))
    parser.add_argument("command", choices=["state", "save", "watch"])
    parser.add_argument("title", nargs="?")
    parser.add_argument("--action-id", default=str(uuid.uuid4()))
    parser.add_argument("--request-id")
    args = parser.parse_args()
    if args.connection:
        with open(args.connection) as source:
            credentials = json.load(source)
        os.environ["CODERS_APP_URL"] = credentials["app_url"]
        os.environ["CODERS_GRANT"] = credentials["account_key"]
        os.environ["CODERS_RESOURCE"] = credentials["resource_id"]
    if args.command == "state":
        print(json.dumps(call("/state"), ensure_ascii=False))
    elif args.command == "save":
        if not args.title:
            parser.error("save에는 문서 제목이 필요합니다.")
        print("action_id=" + args.action_id, flush=True)
        result = call(
            "/save",
            method="PUT",
            data={"action_id": args.action_id, "title": args.title, "actor_label": "Agent"},
            key=args.request_id or args.action_id,
        )
        print(json.dumps(result, ensure_ascii=False))
    else:
        after = None
        while True:
            batch = call("/_activity" + ("?after=" + str(after) if after is not None else ""))
            if batch["reset"]:
                print(
                    json.dumps({"reset": True, "state": call("/state")}, ensure_ascii=False),
                    flush=True,
                )
            for event in batch["events"]:
                print(json.dumps(event, ensure_ascii=False), flush=True)
            after = batch["cursor"]


if __name__ == "__main__":
    try:
        main()
    except HTTPError as error:
        raise SystemExit(
            f"요청 실패: HTTP {error.code}. action_id와 request_id를 유지하고 결과를 확인하세요."
        ) from None
    except URLError:
        raise SystemExit(
            "응답을 확인하지 못했습니다. 같은 action_id와 request_id로 다시 확인하세요."
        ) from None
    except KeyboardInterrupt:
        pass
