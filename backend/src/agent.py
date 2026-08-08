import logging
import os

from dotenv import load_dotenv
from livekit import rtc
from livekit.agents import (
    Agent,
    AgentServer,
    AgentSession,
    JobContext,
    JobProcess,
    cli,
    inference,
    tokenize,
    room_io,
    UserInputTranscribedEvent
)
from livekit.plugins import murf, silero, google, deepgram, noise_cancellation, openai
from livekit.plugins.turn_detector.multilingual import MultilingualModel

logger = logging.getLogger("agent")

load_dotenv(".env.local")

AGENT_NAME = os.getenv("AGENT_NAME", "my-agent")

# Change this prompt to change what your voice agent does.
SYSTEM_PROMPT = """You are the official Local Commerce Assistant. Your job is to help customers explore local products, check exact prices, verify stock availability, and answer questions about local market items.

CRITICAL LANGUAGE MATCHING RULES:
1. ALWAYS EXAMINE THE USER'S INPUT LANGUAGE AND REPLY IN THE EXACT SAME LANGUAGE:
   - ENGLISH INPUT -> REPLY IN 100% ENGLISH ONLY. (Example: "What is the price of sourdough bread?" -> Reply in English).
   - BENGALI INPUT (বাংলা / Banglish) -> REPLY IN 100% BENGALI ONLY (বাংলা). (Example: "ব্রেডের দাম কত?" or "bread er daam koto?" -> Reply in Bengali).
   - HINDI INPUT (हिंदी / Hinglish) -> REPLY IN 100% HINDI ONLY (हिंदी). (Example: "ब्रेड का दाम कितना है?" or "bread ka daam kitna hai?" -> Reply in Hindi).
2. DO NOT CROSS LANGUAGES. Never answer in Hindi if asked in Bengali or English. Never answer in Bengali if asked in English.
3. Keep spoken replies polite, friendly, and concise. Do not use special markdown formatting or bullet points in spoken output.

Here is your current Local Product Catalog & Price List:
1. Fresh Organic Wildflower Honey (500g) — Price: ₹450 ($5.99) — Vendor: Local Apiary Farms — In Stock (Pure, raw, 100% natural organic honey).
2. Handcrafted Sourdough Bread (750g) — Price: ₹220 ($2.99) — Vendor: Artisan Local Bakery — Baked Fresh Daily (Naturally fermented sourdough).
3. Artisanal Roasted Coffee Beans (250g) — Price: ₹580 ($7.50) — Vendor: Mountain Roast Co. — In Stock (Single-origin medium roast, whole bean or ground).
4. Handmade Ceramic Tea Mug (350ml) — Price: ₹350 ($4.50) — Vendor: Heritage Pottery Crafts — Limited Stock (Hand-painted pottery).
5. Organic Cold-Pressed Coconut Oil (1 Litre) — Price: ₹650 ($8.25) — Vendor: Green Harvest Organics — In Stock (Pure unrefined extra virgin oil).
6. Handwoven Cotton Tote Bag — Price: ₹399 ($4.99) — Vendor: EcoWeave Local — In Stock (100% eco-friendly organic cotton).

Store Policies & Delivery:
- Free same-day local delivery on orders above ₹499 ($6.00). Standard local delivery fee is ₹40 ($0.50).
- Hours: Open 8:00 AM to 9:00 PM daily.
- Return Policy: 7-day hassle-free exchange at any local partner store."""


class Assistant(Agent):
    def __init__(self) -> None:
        super().__init__(instructions=SYSTEM_PROMPT)


server = AgentServer()


def prewarm(proc: JobProcess):
    proc.userdata["vad"] = silero.VAD.load()


server.setup_fnc = prewarm


@server.rtc_session(agent_name=AGENT_NAME)
async def my_agent(ctx: JobContext):
    # Logging setup
    ctx.log_context_fields = {
        "room": ctx.room.name,
    }
    # LLM: Groq (using Llama 3.3 70B via OpenAI-compatible endpoint)
    llm_instance = openai.LLM(
        model="llama-3.3-70b-versatile",
        base_url="https://api.groq.com/openai/v1",
        api_key=os.getenv("GROQ_API_KEY"),
    )

    # Set up a voice AI pipeline using Murf Falcon, Gemini, Deepgram, and the LiveKit turn detector
    session = AgentSession(
        # Speech-to-text (STT) is your agent's ears, turning the user's speech into text that the LLM can understand
        # See all available models at https://docs.livekit.io/agents/models/stt/
        stt=deepgram.STT(model="nova-3", language="multi"),
        # A Large Language Model (LLM) is your agent's brain, processing user input and generating a response
        # See all available models at https://docs.livekit.io/agents/models/llm/
        llm=llm_instance,
        # Text-to-speech (TTS) is your agent's voice, turning the LLM's text into speech that the user can hear
        # See all available models as well as voice selections at https://docs.livekit.io/agents/models/tts/
        tts=murf.TTS(
            voice="Anisha", 
            style="Conversation",
            tokenizer=tokenize.basic.SentenceTokenizer(min_sentence_len=2),
            text_pacing=True
        ),
        # VAD and turn detection are used to determine when the user is speaking and when the agent should respond
        # See more at https://docs.livekit.io/agents/build/turns
        turn_detection=MultilingualModel(),
        vad=ctx.proc.userdata["vad"],
        # allow the LLM to generate a response while waiting for the end of turn
        # See more at https://docs.livekit.io/agents/build/audio/#preemptive-generation
        preemptive_generation=True,
    )

    @session.on("user_input_transcribed")
    def on_user_input_transcribed(ev: UserInputTranscribedEvent):
        transcript = ev.transcript.strip().lower()
        if not transcript:
            return

        words = set(transcript.split())

        # 1. Check Bengali script (Unicode U+0980 to U+09FF)
        has_bengali_script = any(0x0980 <= ord(c) <= 0x09FF for c in transcript)
        # Distinctive Bengali keywords (excluding common English words)
        bengali_keywords = {
            "kemon", "acho", "ami", "bhalo", "daam", "koto", "taka", "khobor", 
            "dokan", "naam", "apni", "tumi", "dada", "didi", "korcho", "bhaio", 
            "shono", "amake", "bolun", "chaie", "pabo", "achhe", "ache", "bangla"
        }
        has_bengali_words = not words.isdisjoint(bengali_keywords)

        # 2. Check Devanagari script for Hindi (Unicode U+0900 to U+097F)
        has_devanagari = any(0x0900 <= ord(c) <= 0x097F for c in transcript)
        # Distinctive Hindi keywords (ONLY distinctive Hindi words, NO English words like 'the', 'is', 'in')
        hindi_keywords = {
            "namaste", "shukriya", "kya", "kaise", "kitna", "kitne", "batao", 
            "bataiye", "samjhao", "dhan", "suraksha", "bima", "pension", 
            "mujhe", "mera", "meri", "apna", "apni", "karna", "karo", "hindi", "hinglish"
        }
        has_hindi_words = not words.isdisjoint(hindi_keywords)

        if has_bengali_script or has_bengali_words:
            logger.info(f"Detected Bengali speech: '{ev.transcript}'. Switching TTS voice to bn-IN-anisha")
            try:
                session.tts.update_options(voice="bn-IN-anisha")
            except Exception as e:
                logger.warning(f"Could not switch to Bengali TTS voice: {e}")
        elif has_devanagari or has_hindi_words:
            logger.info(f"Detected Hindi speech: '{ev.transcript}'. Switching TTS voice to hi-IN-anisha")
            try:
                session.tts.update_options(voice="hi-IN-anisha")
            except Exception as e:
                logger.warning(f"Could not switch to Hindi TTS voice: {e}")
        else:
            logger.info(f"Detected English speech: '{ev.transcript}'. Switching TTS voice to en-IN-anisha")
            try:
                session.tts.update_options(voice="en-IN-anisha")
            except Exception as e:
                logger.warning(f"Could not switch to English TTS voice: {e}")

    # To use a realtime model instead of a voice pipeline, use the following session setup instead.
    # (Note: This is for the OpenAI Realtime API. For other providers, see https://docs.livekit.io/agents/models/realtime/))
    # 1. Install livekit-agents[openai]
    # 2. Set OPENAI_API_KEY in .env.local
    # 3. Add `from livekit.plugins import openai` to the top of this file
    # 4. Use the following session setup instead of the version above
    # session = AgentSession(
    #     llm=openai.realtime.RealtimeModel(voice="marin")
    # )

    # # Add a virtual avatar to the session, if desired
    # # For other providers, see https://docs.livekit.io/agents/models/avatar/
    # avatar = hedra.AvatarSession(
    #   avatar_id="...",  # See https://docs.livekit.io/agents/models/avatar/plugins/hedra
    # )
    # # Start the avatar and wait for it to join
    # await avatar.start(session, room=ctx.room)

    # Start the session, which initializes the voice pipeline and warms up the models
    await session.start(
        agent=Assistant(),
        room=ctx.room,
        room_options=room_io.RoomOptions(
            audio_input=room_io.AudioInputOptions(
                noise_cancellation=lambda params: (
                    noise_cancellation.BVCTelephony()
                    if params.participant.kind
                    == rtc.ParticipantKind.PARTICIPANT_KIND_SIP
                    else noise_cancellation.BVC()
                ),
            ),
        ),
    )

    # Join the room and connect to the user
    await ctx.connect()


if __name__ == "__main__":
    cli.run_app(server)
