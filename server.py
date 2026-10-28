"""같은 워크스페이스의 문서를 브라우저와 CLI에서 함께 수정하는 예제."""

import os
from contextlib import asynccontextmanager
from uuid import UUID, uuid4

import httpx
import psycopg
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field


@asynccontextmanager
async def lifespan(app):
    async with await psycopg.AsyncConnection.connect(os.environ["DATABASE_URL"]) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS demo_document(id integer PRIMARY KEY, title text NOT NULL);
            INSERT INTO demo_document VALUES(1,'함께 편집하는 문서') ON CONFLICT DO NOTHING;
            CREATE TABLE IF NOT EXISTS demo_saves(
                action_id uuid PRIMARY KEY, title text NOT NULL, actor_label text NOT NULL,
                notified boolean NOT NULL DEFAULT false);
        """)
    yield


app = FastAPI(lifespan=lifespan)


class Save(BaseModel):
    action_id: UUID
    title: str = Field(min_length=1, max_length=200)
    actor_label: str = Field(default="Agent", min_length=1, max_length=80)


@app.get("/state")
async def state():
    async with await psycopg.AsyncConnection.connect(os.environ["DATABASE_URL"]) as db:
        row = await (await db.execute("SELECT title FROM demo_document WHERE id=1")).fetchone()
    return {
        "document": {"id": "document:1", "title": row[0]},
        "actions": [
            {
                "id": "save",
                "endpoint": "save",
                "method": "PUT",
                "target": "document:1",
                "input": ["action_id", "title", "actor_label"],
            }
        ],
    }


@app.put("/save")
async def save(body: Save):
    async with await psycopg.AsyncConnection.connect(os.environ["DATABASE_URL"]) as db:
        # 변경과 발행 대기를 같은 트랜잭션에 기록합니다. 재시도에는 같은 action_id를 사용합니다.
        inserted = await (
            await db.execute(
                "INSERT INTO demo_saves(action_id,title,actor_label) VALUES(%s,%s,%s) "
                "ON CONFLICT DO NOTHING RETURNING action_id",
                (body.action_id, body.title, body.actor_label),
            )
        ).fetchone()
        previous = await (
            await db.execute(
                "SELECT title,actor_label,notified FROM demo_saves WHERE action_id=%s",
                (body.action_id,),
            )
        ).fetchone()
        if previous[:2] != (body.title, body.actor_label):
            raise HTTPException(409, "같은 action_id의 입력을 바꿀 수 없습니다.")
        if inserted:
            await db.execute("UPDATE demo_document SET title=%s WHERE id=1", (body.title,))
    # 실제 DB 커밋 후 완료 이벤트를 발행합니다. 실패해도 저장을 다시 실행하지 않습니다.
    pending = not previous[2]
    if pending:
        try:
            if await notify(body):
                async with await psycopg.AsyncConnection.connect(os.environ["DATABASE_URL"]) as db:
                    await db.execute(
                        "UPDATE demo_saves SET notified=true WHERE action_id=%s", (body.action_id,)
                    )
                pending = False
        except httpx.HTTPError:
            pass  # 같은 요청을 재시도하면 저장은 유지하고 미발행 알림만 다시 전송합니다.
    return {"saved": True, "activity_pending": pending, "action_id": str(body.action_id)}


async def notify(body):
    async with httpx.AsyncClient(base_url=os.environ["CODERS_URL"], timeout=10) as core:
        response = await core.post(
            "/v1/invoke/coders-activity",
            json={
                "action_id": str(body.action_id),
                "target": "document:1",
                "action": "save",
                "status": "completed",
                "changed": True,
                "actor_label": body.actor_label,
            },
            headers={"Coders-Budget": "2", "Idempotency-Key": str(uuid4())},
        )
    return response.is_success
