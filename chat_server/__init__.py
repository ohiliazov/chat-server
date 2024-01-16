import asyncio
import uuid
from collections import defaultdict
from enum import StrEnum
from typing import Annotated, Any

from fastapi import Depends, FastAPI, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, ValidationError

app = FastAPI(title="Chat Server")


class Action(StrEnum):
    LOGIN = "login"
    MESSAGE = "message"
    ENTER_ROOM = "enter_room"
    EXIT_ROOM = "exit_room"
    LIST_ROOMS = "list_rooms"


class Message(BaseModel):
    action: Action
    room_id: str | None = None
    payload: Any = None


class Manager:
    clients: dict[str, WebSocket] = {}
    rooms: dict[str, set[str]] = defaultdict(set)

    def __init__(self):
        self.user_id = f"{uuid.uuid4()}"

    async def send_to_user(self, user_id: str, message: Message):
        await self.clients[user_id].send_json(message.model_dump_json())

    async def send_to_self(self, message: Message):
        await self.send_to_user(self.user_id, message)

    async def broadcast(self, message: Message):
        tasks = [
            self.send_to_user(user_id, message)
            for user_id in self.rooms[message.room_id]
        ]
        await asyncio.gather(*tasks)

    async def enter_room(self, room_id: str):
        self.rooms[room_id].add(self.user_id)
        msg = Message.model_construct(
            action=Action.ENTER_ROOM,
            room_id=room_id,
            payload=self.user_id,
        )
        await self.broadcast(msg)

    async def exit_room(self, room_id: str):
        self.rooms[room_id].discard(self.user_id)
        if self.rooms[room_id]:
            msg = Message.model_construct(
                action=Action.EXIT_ROOM,
                room_id=room_id,
                payload=self.user_id,
            )
            await self.broadcast(msg)
        else:
            del self.rooms[room_id]

    async def login(self, websocket: WebSocket):
        self.clients[self.user_id] = websocket

        message = Message.model_construct(
            action=Action.LOGIN,
            payload=self.user_id,
        )
        await self.send_to_self(message)

    async def list_rooms(self):
        message = Message(
            action=Action.LIST_ROOMS,
            payload=",".join(self.rooms),
        )
        await self.send_to_self(message)

    async def logout(self):
        del self.clients[self.user_id]
        tasks = [self.exit_room(room_id) for room_id in self.rooms]
        await asyncio.gather(*tasks)

    async def handle(self, message: Message):
        match message.action:
            case Action.LIST_ROOMS:
                await self.list_rooms()
            case Action.ENTER_ROOM:
                await self.enter_room(message.room_id)
            case Action.EXIT_ROOM:
                await self.exit_room(message.room_id)
            case Action.MESSAGE:
                await self.broadcast(message)

    async def run(self, ws: WebSocket):
        await self.login(ws)

        try:
            while True:
                data = await ws.receive_text()
                if data == "ping":
                    await ws.send_text("pong")
                    continue

                try:
                    message = Message.model_validate_json(data)
                except ValidationError:
                    continue
                await self.handle(message)
        except WebSocketDisconnect:
            print("client disconnected")
        finally:
            await self.logout()


@app.websocket("/websocket")
async def websocket_endpoint(
    websocket: WebSocket, manager: Annotated[Manager, Depends(Manager)]
):
    await websocket.accept()
    await manager.run(websocket)
