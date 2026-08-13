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
    log_call_outcome,
)
from escalations import (
    build_caller_summary,
    create_escalation as db_create_escalation,
    get_escalation,
    init_escalations_db,
)

logger = logging.getLogger("agent")

load_dotenv(".env.local")

AGENT_NAME = os.getenv("AGENT_NAME", "my-agent")

# System Prompt with Memory, Consent, Live Catalogue, Multilingual, Outbound & Escalation Instructions
SYSTEM_PROMPT = """You are the official Local Commerce Assistant. Your job is to help customers explore local products, check exact prices, verify stock availability, and handle order confirmations and restock nudges.

## OUTBOUND CALL & CALL OPENING INSTRUCTIONS (HARD RULE):
1. PROPER OPENING & ASKING FOR NAME:
   - When the call connects, your VERY FIRST action MUST be to greet the customer warmly and ask for their name so you can check their previous profile:
     - Sentence 1 (Who & Why): Say who is calling and ask for their name (e.g. "Hello! Welcome to Local Commerce Assistant. May I please know your name so I can check your account profile?")
     - Sentence 2 (How to stop): Mention opt-out instructions (e.g. "If you don't wish to receive call reminders, just say 'stop calling me' or 'opt out' at any time.")
   - Do NOT guess or assume the caller's identity before they state their name.

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
1. CALLER IDENTIFICATION & LOOKUP:
   - As soon as a caller states their name (e.g. "My name is Ramesh", "I'm Priya", "Mera naam Ramesh hai"):
     a) IMMEDIATELY call `lookup_caller(user_id_or_name="<caller_name>")` to check if they exist in the persistent database.
     b) Sample callers pre-loaded in memory include "Ramesh" (Hindi) and "Priya" (English).

2. GREETING RETURNING CALLERS WITH "WELCOME BACK":
   - When `lookup_caller` returns `found: True` (profile exists):
     - You MUST say "Welcome back, [Name]!" (or "Namaste [Name]! Welcome back to Local Commerce Assistant.").
     - Reference specific facts from their profile (such as past orders, usual quantities, preferred delivery slot).
     - Example: "Welcome back, Ramesh! Last time we spoke about your order of 5kg Organic Wildflower Honey. Would you like to reorder or check today's prices?"
   - When `lookup_caller` returns `found: False` (new caller / no profile):
     - Say "Nice to meet you, [Name]! Welcome to Local Commerce Assistant. How can I help you today?"

3. EXPLICIT CONSENT BEFORE SAVING ANYTHING (HARD RULE):
   - You MUST ask the caller for permission BEFORE saving any new information, preferences, delivery slots, or orders to memory.
   - ONLY IF the caller explicitly says YES ("yes", "sure", "हाँ", "ठीक है"):
     - IMMEDIATELY call `save_caller_memory(user_id="<caller_name_id>", name="<caller_name>", has_user_consent=True, fact_key="...", fact_value="...")`.
   - IF the caller says NO ("no", "don't save", "नहीं"):
     - DO NOT save anything!

## HUMAN ESCALATION RULES (DAY 7 — CRITICAL):

### WHEN TO ESCALATE (Two Trigger Situations):

TRIGGER 1 — PAYMENT / REFUND DISPUTE:
   Escalate when the caller says ANY of:
   - "I was charged twice" / "double charge" / "charged incorrectly"
   - "I want a refund" / "refund nahi mila" / "paise wapas"
   - "payment failed but money deducted" / "transaction dispute"
   - "I didn't receive my refund" / "refund pending"
   → Set issue_type = "payment_refund"
   → Default urgency = "high"
   → Emergency if amount is large (>₹5000 mentioned) or caller seems very distressed

TRIGGER 2 — ORDER COMPLAINT:
   Escalate when the caller says ANY of:
   - "wrong item delivered" / "galat cheez aayi"
   - "item is damaged" / "product damaged" / "broken"
   - "order is very late" / "order nahi aaya" / "3 din ho gaye"
   - "I never received my order" / "delivery missing"
   - "I want to complain" about a specific order
   → Set issue_type = "order_complaint"
   → Default urgency = "medium" ("high" if item was damaged or order >2 days late)

### HOW TO ESCALATE — STEP BY STEP (HARD RULES):

Step A — DETECT the trigger. Attempt to resolve it yourself first. Only escalate if you truly cannot fix it.

Step B — ASK FOR CONSENT before sharing anything:
   Say EXACTLY: "I'd like to create a support request for a human agent. I'll include your name, a brief description of the issue, and what I've already checked. I won't include any payment details or sensitive information. May I go ahead?"

   - If caller says YES → proceed to Step C
   - If caller says NO → DO NOT call create_escalation. Instead say:
     "Understood! I won't create a request. For payment or order issues, you can also reach our support team directly during business hours (8 AM–9 PM). Is there anything else I can help you with?"

Step C — CALL create_escalation(...) with:
   - caller_name: caller's name
   - issue_type: "payment_refund" OR "order_complaint"
   - what_happened: 1–2 sentence factual summary of what the caller said (NO card numbers, PINs, OTPs)
   - what_agent_checked: what you already looked up (catalogue, caller profile, etc.)
   - urgency: "low" | "medium" | "high" | "emergency"
   - caller_language: the language being used (e.g. "Hindi", "English", "Bengali")
   - preferred_follow_up: "call" | "email" | "sms" (ask caller if unclear)
   - has_caller_consent: MUST be True (only call this after getting YES)

Step D — GIVE THE CALLER A CLEAR NEXT STEP:
   After the tool returns a ref_id, say:
   "Your support request has been logged. Your reference number is [REF_ID]. A human agent will follow up with you. You can check the status any time by asking me 'What is the status of [REF_ID]?'"

### ESCALATION DONT'S:
   - NEVER call create_escalation without explicit caller consent
   - NEVER include card numbers, OTPs, PINs, account numbers, or passwords in what_happened
   - NEVER promise an immediate human response unless you are certain
   - NEVER create a new ticket if the caller already has an open one — check_escalation_status first

### URGENCY GUIDE:
   - emergency: caller says "urgent"/"emergency", large refund (>₹5000), or very distressed
   - high:      payment dispute, damaged goods, order missing >2 days
   - medium:    wrong item, delivery delay <2 days, general order complaint
   - low:       minor preference issue, general query agent couldn't resolve

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
        init_escalations_db()
        super().__init__(instructions=SYSTEM_PROMPT)
        self.call_outcome = "failed"
        self.call_reason = "Incomplete Task"
        self.start_time = asyncio.get_event_loop().time()
        self.language = "English"
        self.caller_user_id = "Anonymous Caller"
        self.caller_channel = "browser"


    @llm.function_tool
    async def mark_call_successful(self, reason: str) -> str:
        """
        Call this tool when you have successfully helped the caller (e.g. they found a product, completed an enquiry, or successfully opted out).
        Do this right before ending the call or saying goodbye.
        """
        logger.info(f"Marking call as successful: {reason}")
        self.call_outcome = "success"
        self.call_reason = reason
        return "Call marked as successful."

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

    @llm.function_tool
    async def create_escalation(
        self,
        caller_name: str,
        issue_type: str,
        what_happened: str,
        what_agent_checked: str,
        urgency: str,
        caller_language: str,
        preferred_follow_up: str,
        has_caller_consent: bool,
        caller_user_id: str = "",
    ) -> str:
        """
        Create a human escalation ticket when the agent cannot resolve a payment/refund dispute
        or order complaint on its own.

        IMPORTANT: Only call this tool AFTER the caller has explicitly given consent.
        Set has_caller_consent=True only if the caller said yes.

        Parameters:
            caller_name: Caller's name (from memory or from the conversation)
            issue_type: 'payment_refund' or 'order_complaint'
            what_happened: 1-2 sentence factual summary — NO card numbers, PINs, OTPs
            what_agent_checked: What tools the agent already used (e.g. 'checked catalogue, looked up caller profile')
            urgency: 'low' | 'medium' | 'high' | 'emergency'
            caller_language: Language used (e.g. 'Hindi', 'English', 'Bengali')
            preferred_follow_up: 'call' | 'email' | 'sms'
            has_caller_consent: MUST be True — only call this after caller says yes
            caller_user_id: Optional caller user_id from the DB (for outbound callback)
        """
        if not has_caller_consent:
            logger.warning("create_escalation called without caller consent — refusing.")
            return json.dumps({
                "success": False,
                "message": "Escalation NOT created. Caller consent was not granted."
            })

        logger.info(
            f"Creating escalation: caller='{caller_name}', issue='{issue_type}', urgency='{urgency}'"
        )
        result = db_create_escalation(
            caller_name=caller_name,
            issue_type=issue_type,
            what_happened=what_happened,
            what_agent_checked=what_agent_checked,
            urgency=urgency,
            caller_language=caller_language,
            preferred_follow_up=preferred_follow_up,
            caller_user_id=caller_user_id,
        )
        ref_id = result.get("ref_id", "")
        verbal_summary = build_caller_summary(ref_id) if ref_id else "Your request has been logged."
        result["verbal_summary"] = verbal_summary
        return json.dumps(result)

    @llm.function_tool
    async def check_escalation_status(self, ref_id: str) -> str:
        """
        Check the current status of an escalation ticket by its reference ID.
        Use this when the caller asks 'What is the status of my ticket ESC-...'.

        Parameters:
            ref_id: The escalation reference ID (e.g. 'ESC-20260812-4721')
        """
        logger.info(f"Checking escalation status for ref_id='{ref_id}'")
        ticket = get_escalation(ref_id.upper())
        if not ticket:
            return json.dumps({
                "found": False,
                "message": f"No ticket found with reference ID '{ref_id}'. Please double-check the number."
            })
        status_phrases = {
            "open": "open and waiting to be assigned to a human agent",
            "in_progress": "in progress — a human agent is currently reviewing it",
            "resolved": "resolved. If you still have an issue, please let me know.",
        }
        status_text = status_phrases.get(ticket["status"], ticket["status"])
        return json.dumps({
            "found": True,
            "ref_id": ticket["ref_id"],
            "status": ticket["status"],
            "status_description": status_text,
            "issue_type": ticket["issue_type"],
            "urgency": ticket["urgency"],
            "created_at": ticket["created_at"],
            "updated_at": ticket["updated_at"],
        })


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

    assistant = Assistant()
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
            assistant.language = "Bengali"
            try:
                session.tts.update_options(locale="bn-IN")
            except Exception as e:
                logger.warning(f"Could not switch to Bengali TTS locale: {e}")
        elif has_devanagari or has_hindi_words:
            logger.info(f"Detected Hindi intent: '{ev.transcript}'. Updating TTS locale to hi-IN")
            assistant.language = "Hindi"
            try:
                session.tts.update_options(locale="hi-IN")
            except Exception as e:
                logger.warning(f"Could not switch to Hindi TTS locale: {e}")
        else:
            logger.info(f"Detected English speech: '{ev.transcript}'. Updating TTS locale to en-IN")
            assistant.language = "English"
            try:
                session.tts.update_options(locale="en-IN")
            except Exception as e:
                logger.warning(f"Could not switch to English TTS locale: {e}")

    await session.start(
        agent=assistant,
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

    @ctx.room.on("participant_connected")
    def on_participant_connected(participant: rtc.RemoteParticipant):
        """Capture caller identity and channel when they join — before disconnect clears the list."""
        if participant.kind == rtc.ParticipantKind.PARTICIPANT_KIND_SIP:
            assistant.caller_channel = "sip"
            assistant.caller_user_id = participant.identity or "SIP Caller"
        elif participant.identity:
            assistant.caller_channel = "browser"
            assistant.caller_user_id = participant.identity
        logger.info(f"Participant joined: identity={participant.identity}, kind={participant.kind}, channel={assistant.caller_channel}")

    @ctx.room.on("disconnected")
    def on_disconnect(*args, **kwargs):
        duration = int(asyncio.get_event_loop().time() - assistant.start_time)
        # Use identity captured at join time via participant_connected event
        # (ctx.room.remote_participants is empty by the time disconnected fires)
        channel = assistant.caller_channel
        user_id = assistant.caller_user_id

        # Final fallback: job metadata
        if user_id == "Anonymous Caller":
            try:
                meta = json.loads(ctx.job.metadata or "{}")
                user_id = meta.get("user_id") or meta.get("caller_id") or "Anonymous Caller"
            except Exception:
                pass

        logger.info(f"Room disconnected. Logging call outcome: {assistant.call_outcome}, {duration}s, {channel}, user={user_id}")
        log_call_outcome(
            outcome=assistant.call_outcome,
            reason=assistant.call_reason,
            channel=channel,
            language=assistant.language,
            duration=duration,
            user_id=user_id
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
