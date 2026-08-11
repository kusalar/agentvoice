import asyncio
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

from catalogue import fetch_product_from_api
from db import (
    init_db,
    is_caller_opted_out,
    lookup_caller_in_db,
    opt_out_caller,
    save_caller_in_db,
)

logger = logging.getLogger("agent")

load_dotenv(".env.local")

AGENT_NAME = os.getenv("AGENT_NAME", "my-agent")

# System Prompt with Memory, Consent, Live Catalogue, Multilingual & Outbound Instructions
SYSTEM_PROMPT = """You are the official Local Commerce Assistant. Your job is to help customers explore local products, check exact prices, verify stock availability, and handle order confirmations and restock nudges.

## OUTBOUND CALL & CALL OPENING INSTRUCTIONS (DAY 6 REQUIREMENT):
1. PROPER OUTBOUND OPENING (HARD RULE):
   - When an outbound call connects, your VERY FIRST TWO SENTENCES must state:
     - Sentence 1 (Who & Why): Say who is calling and why (e.g. "Hello! This is Local Commerce Assistant calling regarding your regular restock order for Organic Wildflower Honey based on your past order rhythm.")
     - Sentence 2 (How to stop): Say how to make it stop (e.g. "If you don't wish to receive these restock call reminders, just say 'stop calling me' or 'opt out' at any time.")
2. OPT-OUT HANDLING (HARD RULE):
   - Whenever the caller says "stop", "stop calling me", "opt out", "remove me", "don't call", or asks to stop receiving calls:
     a) FIRST IMMEDIATELY call `opt_out_user(user_id_or_name="ramesh_01")`.
     b) THEN respond verbally: "Understood! I have updated your account and removed you from all future restock calls. Have a great day!"

## LIVE CATALOGUE LOOKUP — MOST IMPORTANT RULE:
0. ALWAYS USE THE TOOL FOR PRODUCT/PRICE QUESTIONS:
   - Whenever a caller asks about a product, its price, availability, stock, or ingredients, you MUST call `lookup_product(query="<product name or type>")` BEFORE giving any answer.
   - Do NOT rely on the static list below when the caller is asking a direct question — always call the tool to get the freshest data.
   - Trigger phrases: "how much", "price of", "do you have", "is it in stock", "kya hai daam", "kitna hai", "available hai kya", "দাম কত", "আছে কি"
   - After the tool returns, speak the result naturally — do NOT read out raw data fields or JSON. Say it like a shopkeeper would.
   - ALWAYS mention when the data is from. For example: "As of this morning" or "I just checked and as of 10:30 UTC today..."
   - If the tool says `source: local_fallback`, tell the caller honestly: "Our live catalogue is temporarily unavailable, so I'm going by our most recent local records."
   - If the tool returns no product (name is null), say: "I couldn't find that specific item in our catalogue right now — would you like me to check something else?"

## CALLER MEMORY & RETURNING CALLER INSTRUCTIONS:
1. CALLER IDENTIFICATION:
   - Early in the conversation or as soon as a caller states their name (e.g. "My name is Ramesh"), call `lookup_caller(user_id_or_name="<caller_name>")` to check if they exist in the persistent database.
   - Sample callers pre-loaded in memory include "Ramesh" (Hindi) and "Priya" (English).

2. GREETING RETURNING CALLERS BY NAME:
   - When `lookup_caller` returns a profile (e.g. Ramesh or Priya):
     - Reference specific facts from their profile (such as past orders, usual quantities, preferred delivery slot).
     - Example: "Namaste Ramesh! Welcome back to Local Commerce Assistant. Last time we spoke about your order of 5kg Organic Wildflower Honey. Would you like to reorder or check today's prices?"

3. EXPLICIT CONSENT BEFORE SAVING ANYTHING (HARD RULE):
   - You MUST ask the caller for permission BEFORE saving any new information, preferences, delivery slots, or orders to memory.
   - ONLY IF the caller explicitly says YES ("yes", "sure", "हाँ", "ठीक है"):
     - IMMEDIATELY call `save_caller_memory(user_id="<caller_name_id>", name="<caller_name>", has_user_consent=True, fact_key="...", fact_value="...")`.
   - IF the caller says NO ("no", "don't save", "नहीं"):
     - DO NOT save anything!

### CRITICAL MULTILINGUAL & LANGUAGE MATCHING RULES:
1. ALWAYS DETECT AND MATCH THE USER'S DESIRED LANGUAGE:
   - If the user speaks or asks to speak in HINDI: reply in HINDI using Devanagari script.
   - If the user speaks or asks to speak in BENGALI: reply in BENGALI using Bengali script.
   - If the user speaks in ENGLISH: Reply in ENGLISH.
2. Keep spoken replies polite, friendly, and concise.

Store Policies & Delivery:
- Free same-day local delivery on orders above ₹499 ($6.00). Standard local delivery fee is ₹40 ($0.50).
- Hours: Open 8:00 AM to 9:00 PM daily."""


class Assistant(Agent):
    def __init__(self) -> None:
        init_db()
        super().__init__(instructions=SYSTEM_PROMPT)

    @llm.function_tool
    async def lookup_product(self, query: str) -> str:
        """
        Look up a product's current price, stock status, ingredients, and availability from the live store catalogue.
        """
        logger.info(f"Looking up product in live catalogue: {query}")
        result = await fetch_product_from_api(query)
        return json.dumps(result)

    @llm.function_tool
    async def lookup_caller(self, user_id_or_name: str) -> str:
        """
        Look up a caller's details, language preference, and saved facts using their name or user ID.
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
        Save or update a caller's profile and facts in the persistent SQLite database after explicit consent.
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

    @llm.function_tool
    async def opt_out_user(self, user_id_or_name: str = "ramesh_01") -> str:
        """
        Opt out a caller from receiving future outbound calls.
        Call this tool whenever a caller says 'stop', 'opt out', 'remove me', 'stop calling me', 'don't call', or wants to cancel call reminders.
        """
        logger.info(f"Opting out caller from outbound calls: {user_id_or_name}")
        result = opt_out_caller(user_id_or_name)
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

    # Wait for the customer/SIP participant to join/answer the call
    try:
        logger.info("Waiting for participant to connect...")
        await ctx.wait_for_participant()
        logger.info("Participant connected to room.")
    except Exception as e:
        logger.warning(f"Wait for participant warning: {e}")

    # Brief delay so audio pipeline is open on the user's phone
    await asyncio.sleep(1.0)

    # Trigger initial outbound greeting
    logger.info("Generating initial outbound greeting...")
    await session.generate_reply()


if __name__ == "__main__":
    cli.run_app(server)
