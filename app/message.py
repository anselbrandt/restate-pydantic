import random
from datetime import timedelta

import restate
from pydantic import BaseModel
from restate import RunOptions


def send_notification(message_id: str, name: str):
    if random.random() < 0.7 and name == "Alice":  # 70% chance of failure
        print(f"[👻 SIMULATED] Failed to send notification: {message_id} - {name}")
        # raise Exception(
        #     f"[👻 SIMULATED] Failed to send notification: {message_id} - {name}"
        # )
    print(f"Notification sent: {message_id} - {name}")


def send_reminder(message_id: str, name: str):
    if random.random() < 0.7 and name == "Alice":  # 70% chance of failure
        print(f"[👻 SIMULATED] Failed to send reminder: {message_id}")
        # raise Exception(f"[👻 SIMULATED] Failed to send reminder: {message_id}")
    print(f"Reminder sent: {message_id}")


example_recipient = "Alice"


class MessageRequest(BaseModel):
    name: str = example_recipient


class Message(BaseModel):
    message: str


message_service = restate.Service("Message_Service")


@message_service.handler()
async def send_message(ctx: restate.Context, req: MessageRequest) -> Message:
    message_id = str(ctx.uuid())
    await ctx.sleep(timedelta(seconds=10))
    await ctx.run_typed(
        "notification",
        send_notification,
        RunOptions(max_attempts=3),
        message_id=message_id,
        name=req.name,
    )
    await ctx.sleep(timedelta(seconds=10))
    await ctx.run_typed(
        "reminder",
        send_reminder,
        RunOptions(max_attempts=3),
        message_id=message_id,
        name=req.name,
    )

    return Message(message=f"You said hi to {req.name}!")
