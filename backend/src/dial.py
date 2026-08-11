"""
dial.py — Script to make outbound calls via LiveKit SIP trunk (Linphone / Twilio)

Usage:
  uv run python src/dial.py [user_id] [phone_or_sip_uri]

Examples:
  uv run python src/dial.py ramesh_01
  uv run python src/dial.py priya_02 sip:kagent.linphone.org@sip.linphone.org
"""

import asyncio
import os
import sys
import time
from dotenv import load_dotenv
from livekit import api

# Load environment variables
backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
env_path = os.path.join(backend_dir, ".env.local")
load_dotenv(env_path)

LIVEKIT_URL = os.getenv("LIVEKIT_URL")
LIVEKIT_API_KEY = os.getenv("LIVEKIT_API_KEY")
LIVEKIT_API_SECRET = os.getenv("LIVEKIT_API_SECRET")
SIP_OUTBOUND_TRUNK_ID = os.getenv("SIP_OUTBOUND_TRUNK_ID", "ST_ciTbMXSrF7W8")
SIP_DESTINATION = os.getenv("SIP_DESTINATION", "sip:kagent.linphone.org@sip.linphone.org")


async def make_outbound_call(user_id: str = "ramesh_01", destination: str | None = None):
    raw_destination = destination or SIP_DESTINATION

    # LiveKit sip_call_to expects phone number or SIP username (e.g. "kagent.linphone.org")
    call_to = raw_destination.replace("sip:", "").split("@")[0]

    if not LIVEKIT_URL or not LIVEKIT_API_KEY or not LIVEKIT_API_SECRET:
        print("❌ Error: LIVEKIT_URL, LIVEKIT_API_KEY, or LIVEKIT_API_SECRET missing in .env.local")
        return

    room_name = f"outbound-call-{int(time.time())}"
    print(f"[CALL] Initiating outbound call to '{call_to}' (raw: '{raw_destination}')...")
    print(f"       Trunk ID : {SIP_OUTBOUND_TRUNK_ID}")
    print(f"       Room     : {room_name}")
    print(f"       Customer : {user_id}")

    async with api.LiveKitAPI(
        url=LIVEKIT_URL,
        api_key=LIVEKIT_API_KEY,
        api_secret=LIVEKIT_API_SECRET,
    ) as lk:
        req = api.CreateSIPParticipantRequest(
            sip_trunk_id=SIP_OUTBOUND_TRUNK_ID,
            sip_call_to=call_to,
            room_name=room_name,
            participant_identity=f"sip_user_{user_id}",
            participant_name="Customer",
            participant_attributes={
                "outbound": "true",
                "user_id": user_id,
            },
        )
        AGENT_NAME = os.getenv("AGENT_NAME")
        if AGENT_NAME:
            try:
                import json
                dispatch_req = api.CreateAgentDispatchRequest(
                    agent_name=AGENT_NAME,
                    room=room_name,
                    metadata=json.dumps({"outbound": True, "user_id": user_id}),
                )
                await lk.agent_dispatch.create_dispatch(dispatch_req)
                print(f"       Agent Dispatch created for agent '{AGENT_NAME}' in room '{room_name}'")
            except Exception as dispatch_err:
                print(f"       [Info] Agent dispatch note: {dispatch_err}")

        try:
            participant = await lk.sip.create_sip_participant(req)
            print("[SUCCESS] Outbound call placed successfully!")
            print(f"          SIP Participant ID : {getattr(participant, 'sip_participant_id', getattr(participant, 'participant_id', participant))}")
            print("\nMake sure your agent worker (`uv run python src/agent.py dev` or `uv run python src/telephony/outbound/agent.py dev`) is running!")
        except Exception as e:
            print(f"[ERROR] Failed to create SIP participant: {e}")


if __name__ == "__main__":
    target_user = sys.argv[1] if len(sys.argv) > 1 else "ramesh_01"
    target_dest = sys.argv[2] if len(sys.argv) > 2 else SIP_DESTINATION
    asyncio.run(make_outbound_call(target_user, target_dest))
