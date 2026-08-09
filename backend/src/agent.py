import json
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
    UserInputTranscribedEvent,
    llm,
)
from livekit.plugins import murf, silero, google, deepgram, noise_cancellation, openai
from livekit.plugins.turn_detector.multilingual import MultilingualModel

from db import init_db, lookup_caller_in_db, save_caller_in_db

logger = logging.getLogger("agent")

load_dotenv(".env.local")

AGENT_NAME = os.getenv("AGENT_NAME", "my-agent")

# System Prompt with Memory, Consent & Multilingual Instructions
SYSTEM_PROMPT = """You are the official Local Commerce Assistant. Your job is to help customers explore local products, check exact prices, verify stock availability, and answer questions about local market items.

## CALLER MEMORY & RETURNING CALLER INSTRUCTIONS:
0. INITIAL GREETING AT START OF CONVERSATION:
   - When the conversation begins, immediately greet the caller warmly (e.g. "Hello! Welcome to Local Commerce Assistant. May I know your name so I can see if we've spoken before?").

1. CALLER IDENTIFICATION:
   - Early in the conversation or as soon as a caller states their name (e.g. "My name is Amit" / "mera naam Ramesh hai"), IMMEDIATELY call `lookup_caller(user_id_or_name="<caller_name>")` to check if they exist in the persistent database.
   - Sample callers pre-loaded in memory include "Ramesh" (Hindi) and "Priya" (English).

2. GREETING RETURNING CALLERS BY NAME:
   - When `lookup_caller` returns a profile (e.g. Ramesh or Priya):
     - Greet them warmly BY NAME in their preferred language (e.g., "Namaste Ramesh! Welcome back!" or "Welcome back Priya!").
     - Reference specific facts from their profile (such as past orders, usual quantities, preferred delivery slot, or favorite vendor).
     - Example: "Namaste Ramesh! Welcome back to Local Commerce Assistant. Last time we spoke about your order of 5kg Organic Wildflower Honey. Would you like to reorder or check today's prices?"
   - When `lookup_caller` returns no profile (new caller), welcome them warmly to Local Commerce Assistant.

3. EXPLICIT CONSENT BEFORE SAVING ANYTHING (HARD RULE):
   - You MUST ask the caller for permission BEFORE saving any new information, preferences, delivery slots, or orders to memory.
   - Example ask: "May I save your name and preferred delivery slot (Morning 9-11 AM) for future orders?" or "क्या मैं आपकी इस जानकारी को भविष्य के लिए सहेज सकता हूँ?"
   - ONLY IF the caller explicitly says YES ("yes", "sure", "हाँ", "ठीक है"):
     - IMMEDIATELY call `save_caller_memory(user_id="<caller_name_id>", name="<caller_name>", has_user_consent=True, fact_key="...", fact_value="...")`.
     - Confirm to the caller that their details have been saved in memory.
   - IF the caller says NO ("no", "don't save", "नहीं"):
     - DO NOT save anything! You may call `save_caller_memory(..., has_user_consent=False)` or skip calling it.
     - Inform the caller politely: "Understood, I will not save this information."
   - Saving caller information without explicit user consent is STRICTLY PROHIBITED.

### CRITICAL MULTILINGUAL & LANGUAGE MATCHING RULES:
1. ALWAYS DETECT AND MATCH THE USER'S DESIRED LANGUAGE:
   - If the user speaks or asks to speak in HINDI (e.g. "हिंदी में बोलो", "talk in hindi", "speak in hindi", "hindi mein batao"): IMMEDIATELY reply in 100% HINDI using Devanagari script (नमस्ते! मैं आपकी क्या सहायता कर सकता हूँ?).
   - If the user speaks or asks to speak in BENGALI (e.g. "বাংলায় বলুন", "talk in bengali", "speak in bengali", "bangla te bolo"): IMMEDIATELY reply in 100% BENGALI using Bengali script (নমস্কার! আমি আপনাকে কীভাবে সাহায্য করতে পারি?).
   - If the user speaks in ENGLISH: Reply in ENGLISH.
2. SCRIPT REQUIREMENT:
   - Always write Hindi in Devanagari script (नमस्ते), never romanized.
   - Always write Bengali in Bengali script (নমস্কার), never romanized.
3. If the user asks you to switch languages or answer in Hindi or Bengali, ALWAYS obey immediately and respond in that requested language for all subsequent replies.
4. Keep spoken replies polite, friendly, and concise. Do not use special markdown formatting or bullet points in spoken output.

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
        init_db()
        super().__init__(instructions=SYSTEM_PROMPT)

    @llm.function_tool
    async def lookup_caller(self, user_id_or_name: str) -> str:
        """
        Look up a caller's details, language preference, and saved facts (such as past orders, usual quantities, preferred delivery slot) using their name or user ID.
        Call this function whenever the caller states their name or asks about their past history.
        """
        logger.info(f"Looking up caller in database: {user_id_or_name}")
        caller_data = lookup_caller_in_db(user_id_or_name)
        if not caller_data:
            return json.dumps({"found": False, "message": f"No caller profile found for '{user_id_or_name}' in database."})
        return json.dumps({"found": True, "data": caller_data})

    @llm.function_tool
    async def save_caller_memory(
        self,
        user_id: str,
        name: str,
        has_user_consent: bool,
        language_preference: str = "English",
        fact_key: str = "preference",
        fact_value: str = "",
    ) -> str:
        """
        Save or update a caller's profile and facts in the persistent SQLite database.
        IMPORTANT RULES:
        1. Always pass the caller's actual name as the `name` parameter.
        2. HARD RULE: You MUST ask the caller for permission BEFORE calling this tool and set `has_user_consent=True` ONLY IF the caller explicitly agrees.
        """
        logger.info(f"save_caller_memory invoked for name='{name}', user_id='{user_id}' with consent={has_user_consent}")
        result = save_caller_in_db(
            user_id=user_id,
            name=name,
            language_preference=language_preference,
            fact_key=fact_key,
            fact_value=fact_value,
            has_user_consent=has_user_consent,
        )
        return json.dumps(result)


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
    # LLM: Google Gemini
    llm_instance = google.LLM(
        model="gemini-3.5-flash-lite",
        api_key=os.getenv("GOOGLE_API_KEY"),
    )

    session = AgentSession(
        stt=deepgram.STT(model="nova-3", language="multi"),
        llm=llm_instance,
        tts=murf.TTS(
            voice="Anisha", 
            style="Conversation",
            tokenizer=tokenize.basic.SentenceTokenizer(min_sentence_len=2),
            text_pacing=True
        ),
        turn_detection=MultilingualModel(),
        vad=ctx.proc.userdata["vad"],
        preemptive_generation=True,
    )

    @session.on("user_input_transcribed")
    def on_user_input_transcribed(ev: UserInputTranscribedEvent):
        transcript = ev.transcript.strip().lower()
        if not transcript:
            return

        words = set(transcript.split())

        # 1. Check Bengali script (Unicode U+0980 to U+09FF) or keywords
        has_bengali_script = any(0x0980 <= ord(c) <= 0x09FF for c in transcript)
        bengali_keywords = {
            "bengali", "bengal", "bangla", "kemon", "acho", "ami", "bhalo", "daam", "koto", 
            "taka", "khobor", "dokan", "naam", "apni", "tumi", "dada", "didi", "korcho", 
            "bhaio", "shono", "amake", "bolun", "chaie", "pabo", "achhe", "ache"
        }
        has_bengali_words = not words.isdisjoint(bengali_keywords)

        # 2. Check Devanagari script for Hindi (Unicode U+0900 to U+097F) or keywords
        has_devanagari = any(0x0900 <= ord(c) <= 0x097F for c in transcript)
        hindi_keywords = {
            "hindi", "hinglish", "namaste", "shukriya", "kya", "kaise", "kitna", "kitne", 
            "batao", "bataiye", "samjhao", "dhan", "suraksha", "bima", "pension", "mujhe", 
            "mera", "meri", "apna", "apni", "karna", "karo", "bolo"
        }
        has_hindi_words = not words.isdisjoint(hindi_keywords)

        if has_bengali_script or has_bengali_words:
            logger.info(f"Detected Bengali intent: '{ev.transcript}'. Updating TTS locale to bn-IN")
            try:
                session.tts.update_options(locale="bn-IN")
            except Exception as e:
                logger.warning(f"Could not switch to Bengali TTS locale: {e}")
        elif has_devanagari or has_hindi_words:
            logger.info(f"Detected Hindi intent: '{ev.transcript}'. Updating TTS locale to hi-IN")
            try:
                session.tts.update_options(locale="hi-IN")
            except Exception as e:
                logger.warning(f"Could not switch to Hindi TTS locale: {e}")
        else:
            logger.info(f"Detected English speech: '{ev.transcript}'. Updating TTS locale to en-IN")
            try:
                session.tts.update_options(locale="en-IN")
            except Exception as e:
                logger.warning(f"Could not switch to English TTS locale: {e}")

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

    await ctx.connect()

    # Automatically trigger initial greeting when the user joins
    await session.generate_reply()


if __name__ == "__main__":
    cli.run_app(server)
