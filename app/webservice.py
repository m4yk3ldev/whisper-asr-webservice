import importlib.metadata
import os
from os import path
from typing import Annotated, Dict, List, Optional, Union
from urllib.parse import quote

import click
import uvicorn
from fastapi import FastAPI, File, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse, StreamingResponse
from pydantic import BaseModel
from whisper import tokenizer

from app.config import CONFIG
from app.factory.asr_model_factory import ASRModelFactory
from app.utils import load_audio

# Initialize ASR model
asr_model = ASRModelFactory.create_asr_model()
asr_model.load_model()

# Constants
LANGUAGE_CODES = sorted(tokenizer.LANGUAGES.keys())
OUTPUT_FORMATS = ["txt", "vtt", "srt", "tsv", "json"]
TASKS = ["transcribe", "translate"]

# Get project metadata
projectMetadata = importlib.metadata.metadata("whisper-asr-webservice")

# Create FastAPI app
app = FastAPI(
    title=projectMetadata["Name"].title().replace("-", " "),
    description=projectMetadata["Summary"],
    version=projectMetadata["Version"],
    contact={"url": projectMetadata["Home-page"]},
    swagger_ui_parameters={
        "defaultModelsExpandDepth": -1,
        "syntaxHighlight.theme": "obsidian",
        "docExpansion": "none",
    },
    license_info={"name": "MIT License", "url": projectMetadata["License"]},
    docs_url="/docs",
    redoc_url="/redoc",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust this in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# FastAPI includes Swagger UI by default, no additional configuration needed


@app.get("/", response_class=RedirectResponse, include_in_schema=False)
async def index():
    return "/docs"


# Response models
class StatusResponse(BaseModel):
    version: str
    status: str

class LanguageDetectionResponse(BaseModel):
    detected_language: str
    language_code: str
    confidence: float

@app.get("/status", tags=["Endpoints"], response_model=StatusResponse)
async def status() -> Dict[str, str]:
    """Return the status of the service with version information.
    
    This endpoint is compatible with Bazarr for service health checking.
    """
    return {
        "version": projectMetadata["Version"],
        "status": "ok"
    }


@app.post("/asr", tags=["Endpoints"])
async def asr(
    audio_file: UploadFile = File(...),  # noqa: B008
    encode: bool = Query(default=True, description="Encode audio first through ffmpeg"),
    task: str = Query(default="transcribe", enum=TASKS),
    language: Optional[str] = Query(default=None, enum=LANGUAGE_CODES),
    initial_prompt: Optional[str] = Query(default=None),
    vad_filter: Annotated[
        Optional[bool],
        Query(
            description="Enable the voice activity detection (VAD) to filter out parts of the audio without speech",
            include_in_schema=(CONFIG.ASR_ENGINE == "faster_whisper"),
        ),
    ] = False,
    word_timestamps: bool = Query(
        default=False,
        description="Word level timestamps",
        include_in_schema=(CONFIG.ASR_ENGINE == "faster_whisper"),
    ),
    diarize: bool = Query(
        default=False,
        description="Diarize the input",
        include_in_schema=(CONFIG.ASR_ENGINE == "whisperx" and CONFIG.HF_TOKEN != ""),
    ),
    min_speakers: Optional[int] = Query(
        default=None,
        description="Min speakers in this file",
        include_in_schema=(CONFIG.ASR_ENGINE == "whisperx"),
    ),
    max_speakers: Optional[int] = Query(
        default=None,
        description="Max speakers in this file",
        include_in_schema=(CONFIG.ASR_ENGINE == "whisperx"),
    ),
    output: str = Query(default="txt", enum=OUTPUT_FORMATS),
):
    try:
        # Load and process audio
        audio_data = load_audio(audio_file.file, encode)
        
        # Create options dictionary
        options = {
            "diarize": diarize,
            "min_speakers": min_speakers,
            "max_speakers": max_speakers
        }
        
        # Transcribe audio
        result = asr_model.transcribe(
            audio_data,
            task,
            language,
            initial_prompt,
            vad_filter,
            word_timestamps,
            options,
            output,
        )
        
        # Determine appropriate media type based on output format
        media_types = {
            "txt": "text/plain",
            "vtt": "text/vtt",
            "srt": "text/plain",
            "tsv": "text/tab-separated-values",
            "json": "application/json"
        }
        
        # Return streaming response
        return StreamingResponse(
            result,
            media_type=media_types.get(output, "text/plain"),
            headers={
                "Asr-Engine": CONFIG.ASR_ENGINE,
                "Content-Disposition": f'attachment; filename="{quote(audio_file.filename)}.{output}"',
            },
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Transcription error: {str(e)}")


@app.post("/detect-language", tags=["Endpoints"], response_model=LanguageDetectionResponse)
async def detect_language(
    audio_file: UploadFile = File(...),  # noqa: B008
    encode: bool = Query(default=True, description="Encode audio first through FFmpeg"),
):
    """Detect the language of the audio file.
    
    Returns the detected language, its ISO code, and the confidence score.
    """
    try:
        # Load audio and detect language
        audio_data = load_audio(audio_file.file, encode)
        detected_lang_code, confidence = asr_model.language_detection(audio_data)
        
        return {
            "detected_language": tokenizer.LANGUAGES[detected_lang_code],
            "language_code": detected_lang_code,
            "confidence": confidence,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Language detection error: {str(e)}")


@click.command()
@click.option(
    "-h",
    "--host",
    metavar="HOST",
    default="0.0.0.0",
    help="Host for the webservice (default: 0.0.0.0)",
)
@click.option(
    "-p",
    "--port",
    metavar="PORT",
    default=9000,
    help="Port for the webservice (default: 9000)",
)
@click.option(
    "--reload",
    is_flag=True,
    default=False,
    help="Enable auto-reload for development",
)
@click.version_option(version=projectMetadata["Version"])
def start(host: str, port: int = 9000, reload: bool = False):
    """Start the Whisper ASR Webservice."""
    print(f"Starting Whisper ASR Webservice v{projectMetadata['Version']}")
    print(f"Using ASR Engine: {CONFIG.ASR_ENGINE}")
    print(f"Using ASR Model: {CONFIG.MODEL_NAME}")
    print(f"Using Device: {CONFIG.DEVICE}")
    
    uvicorn.run("app.webservice:app", host=host, port=port, reload=reload)


if __name__ == "__main__":
    start()
