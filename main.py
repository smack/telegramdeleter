import asyncio

from telethon import TelegramClient
from telethon.tl.functions.messages import DeleteHistoryRequest
from telethon.tl.functions.channels import LeaveChannelRequest
from telethon.tl.functions.contacts import GetContactsRequest, DeleteContactsRequest
from telethon.tl.types import User, Chat, Channel, InputUser
from telethon.errors import FloodWaitError, UserNotParticipantError

# 
# Config
#

API_ID = 123
API_HASH = ""
SESSION_NAME = ""
CONCURRENCY = 8

#
#
#


client = TelegramClient(SESSION_NAME, API_ID, API_HASH)
sem = asyncio.Semaphore(CONCURRENCY)


async def safe_leave(entity, name):
    async with sem:
        try:
            if isinstance(entity, Channel):
                await client(LeaveChannelRequest(entity))
            else:
                await client.delete_dialog(entity)
            print(f"Left: {name}")
        except UserNotParticipantError:
            print(f"Already left: {name}")
        except FloodWaitError as e:
            print(f"FloodWait {e.seconds}s on {name}")
            await asyncio.sleep(e.seconds)
        except Exception as e:
            print(f"Could not leave {name}: {e}")


async def safe_delete_dm(entity, name):
    async with sem:
        try:
            await client(
                DeleteHistoryRequest(
                    peer=entity, max_id=0, just_clear=False, revoke=True
                )
            )
            await client.delete_dialog(entity)
            print(f"Deleted chat: {name}")
        except FloodWaitError as e:
            print(f"FloodWait {e.seconds}s on {name}")
            await asyncio.sleep(e.seconds)
        except Exception as e:
            print(f"Could not delete {name}: {e}")


async def delete_all_contacts():
    print("Deleting all contacts")
    try:
        result = await client(GetContactsRequest(hash=0))
        contacts = result.users

        if not contacts:
            print("No contacts found.")
            return

        print(f"Found {len(contacts)} contacts. Deleting...")

        input_users = []
        for user in contacts:
            input_users.append(InputUser(user_id=user.id, access_hash=user.access_hash))

        await client(DeleteContactsRequest(id=input_users))
        print(f"Deleted {len(input_users)} contacts")

    except FloodWaitError as e:
        print(f"FloodWait {e.seconds}s while deleting contacts")
        await asyncio.sleep(e.seconds)
    except Exception as e:
        print(f"Error deleting contacts: {e}")


async def main():
    await client.start(
        phone=lambda: input("Enter your phone number (with country code): ")
    )

    print("\nLogged in successfully :D\n")

    await delete_all_contacts()
    print()

    print("Fetching dialogs...")
    dialogs = await client.get_dialogs()
    print(f"Found {len(dialogs)} dialogs.\n")

    tasks = []

    for d in dialogs:
        entity = d.entity
        name = d.name or "Unknown"

        if isinstance(entity, User):
            tasks.append(safe_delete_dm(entity, name))
        elif isinstance(entity, (Chat, Channel)):
            tasks.append(safe_leave(entity, name))

    print(f"Starting {len(tasks)} chat actions (concurrency={CONCURRENCY})...\n")
    await asyncio.gather(*tasks)

    print("\nDone! ^w^")


if __name__ == "__main__":
    asyncio.run(main())
