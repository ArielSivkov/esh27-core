"""
Phase 1 of the VM + voice plan: does Gemini Live hold a Hebrew conversation and call a tool correctly?

Talk to it from the laptop's microphone (default), or type with --text. One tool, get_site_status,
checks whether an esh27.com site answers. Transcripts of both sides are printed, so the result can
be judged afterwards: 5 out of 5 correct tool calls and natural Hebrew = pass.

Setup (once):
    pip install google-genai pyaudio httpx
    gcloud auth application-default login
    export GOOGLE_CLOUD_PROJECT=<project id>

Run:
    python scripts/gemini_live_hebrew_test.py          # microphone, use headphones to avoid echo
    python scripts/gemini_live_hebrew_test.py --text   # keyboard, Hebrew answers are still spoken

Env: GEMINI_LIVE_MODEL (default gemini-live-2.5-flash-native-audio), GOOGLE_CLOUD_LOCATION (default us-central1).
Not run yet: written without project credentials or audio hardware.
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys

import httpx
from google import genai
from google.genai import types

MODEL = os.getenv("GEMINI_LIVE_MODEL", "gemini-live-2.5-flash-native-audio")
IN_RATE, OUT_RATE, CHUNK = 16000, 24000, 1024

SYSTEM = (
    "אתה CrownBot, העוזר של אריאל. דבר עברית קצרה וטבעית. "
    "כשאריאל שואל אם אתר עובד, קרא לכלי get_site_status ואל תנחש. "
    "אל תבצע שום פעולה אחרת."
)

SITE_STATUS = types.FunctionDeclaration(
    name="get_site_status",
    description="Check whether an esh27.com site answers. site is a subdomain like 'shuru' or 'farms', or 'www' for the main site.",
    parameters={"type": "object", "properties": {"site": {"type": "string"}}, "required": ["site"]},
)


def site_status(site: str) -> dict:
    site = site.strip().lower().removesuffix(".esh27.com")
    if not site.replace("-", "").isalnum():
        return {"error": "bad site name"}
    url = "https://esh27.com" if site in ("", "www") else f"https://{site}.esh27.com"
    try:
        r = httpx.get(url, timeout=8, follow_redirects=True)
        return {"url": url, "status": r.status_code}
    except httpx.HTTPError as exc:
        return {"url": url, "error": type(exc).__name__}


async def receive(session, speaker) -> None:
    async for msg in session.receive():
        if msg.data and speaker:
            await asyncio.to_thread(speaker.write, msg.data)
        sc = msg.server_content
        if sc and sc.input_transcription and sc.input_transcription.text:
            print(f"אריאל: {sc.input_transcription.text}")
        if sc and sc.output_transcription and sc.output_transcription.text:
            print(f"CrownBot: {sc.output_transcription.text}")
        if msg.tool_call:
            responses = []
            for fc in msg.tool_call.function_calls:
                result = site_status(**(fc.args or {})) if fc.name == "get_site_status" else {"error": "unknown tool"}
                print(f"[tool] {fc.name}({fc.args}) -> {result}")
                responses.append(types.FunctionResponse(id=fc.id, name=fc.name, response=result))
            await session.send_tool_response(function_responses=responses)


async def send_mic(session, mic) -> None:
    while True:
        data = await asyncio.to_thread(mic.read, CHUNK, exception_on_overflow=False)
        await session.send_realtime_input(audio=types.Blob(data=data, mime_type=f"audio/pcm;rate={IN_RATE}"))


async def send_text(session) -> None:
    while True:
        line = await asyncio.to_thread(sys.stdin.readline)
        if not line:
            return
        if line.strip():
            await session.send_realtime_input(text=line.strip())


async def main(text_mode: bool) -> None:
    import pyaudio

    client = genai.Client(
        vertexai=True,
        project=os.environ["GOOGLE_CLOUD_PROJECT"],
        location=os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1"),
    )
    config = types.LiveConnectConfig(
        response_modalities=["AUDIO"],
        system_instruction=SYSTEM,
        tools=[types.Tool(function_declarations=[SITE_STATUS])],
        input_audio_transcription=types.AudioTranscriptionConfig(),
        output_audio_transcription=types.AudioTranscriptionConfig(),
    )
    pa = pyaudio.PyAudio()
    speaker = pa.open(format=pyaudio.paInt16, channels=1, rate=OUT_RATE, output=True)
    mic = None if text_mode else pa.open(format=pyaudio.paInt16, channels=1, rate=IN_RATE, input=True,
                                         frames_per_buffer=CHUNK)
    print(f"Connected to {MODEL}. {'Type in Hebrew' if text_mode else 'Speak Hebrew'}; Ctrl+C to stop.")
    try:
        async with client.aio.live.connect(model=MODEL, config=config) as session:
            sender = send_text(session) if text_mode else send_mic(session, mic)
            await asyncio.gather(receive(session, speaker), sender)
    finally:
        for stream in (mic, speaker):
            if stream:
                stream.close()
        pa.terminate()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    parser.add_argument("--text", action="store_true", help="type instead of speaking")
    try:
        asyncio.run(main(parser.parse_args().text))
    except KeyboardInterrupt:
        pass
