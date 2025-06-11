![Licence](https://img.shields.io/github/license/m4yk3ldev/whisper-asr-webservice.svg)
![Docker Pulls](https://img.shields.io/docker/pulls/hanibal920915/whisper-asr-webservice.svg)

# Whisper ASR Box - Fork by m4yk3ldev

Whisper ASR Box is a general-purpose speech recognition service. Whisper models are trained on a large dataset of diverse audio and are also multitask models that can perform multilingual speech recognition as well as speech translation and language identification.

This fork adds support for Bazarr, multi-platform compatibility (Linux, Mac, Raspberry Pi), improved Spanish subtitle synchronization, and other enhancements.

## Features

This fork supports the following whisper models:

- [openai/whisper](https://github.com/openai/whisper)@[v20240930](https://github.com/openai/whisper/releases/tag/v20240930)
- [SYSTRAN/faster-whisper](https://github.com/SYSTRAN/faster-whisper)@[v1.1.0](https://github.com/SYSTRAN/faster-whisper/releases/tag/v1.1.0)
- [whisperX](https://github.com/m-bain/whisperX)@[v3.1.1](https://github.com/m-bain/whisperX/releases/tag/v3.1.1)

### Platform Support

- **CPU Version**: Linux (AMD64, ARM64, ARMv7), Raspberry Pi
- **GPU Version**:
  - Linux with NVIDIA GPUs

## Quick Usage

### CPU

```shell
docker run -d -p 9000:9000 \
  -e ASR_MODEL=base \
  -e ASR_ENGINE=openai_whisper \
  hanibal920915/whisper-asr-webservice:latest
```

### GPU

#### Linux with NVIDIA GPU

```shell
docker run -d --gpus all -p 9000:9000 \
  -e ASR_MODEL=base \
  -e ASR_ENGINE=openai_whisper \
  hanibal920915/whisper-asr-webservice:latest-gpu
```



#### Cache

To reduce container startup time by avoiding repeated downloads, you can persist the cache directory:

```shell
docker run -d -p 9000:9000 \
  -v $PWD/cache:/root/.cache/ \
  hanibal920915/whisper-asr-webservice:latest
```

## Key Features

- Multiple ASR engines support (OpenAI Whisper, Faster Whisper, WhisperX)
- Multiple output formats (text, JSON, VTT, SRT, TSV)
- Word-level timestamps support
- Voice activity detection (VAD) filtering
- Speaker diarization (with WhisperX)
- FFmpeg integration for broad audio/video format support
- GPU acceleration support (NVIDIA CUDA for Linux)
- Multi-platform support (Linux, Raspberry Pi)
- Improved Spanish subtitle synchronization
- Configurable model loading/unloading
- REST API with integrated Swagger UI documentation
- **Bazarr support** through the `/status` endpoint
- Ready-to-use Docker Compose

## Environment Variables

Key configuration options:

- `ASR_ENGINE`: Engine selection (openai_whisper, faster_whisper, whisperx)
- `ASR_MODEL`: Model selection (tiny, base, small, medium, large-v3, etc.)
- `ASR_MODEL_PATH`: Custom path to store/load models
- `ASR_DEVICE`: Device selection (cuda, cpu, mps)
- `MODEL_IDLE_TIMEOUT`: Timeout for model unloading
- `IMPROVE_SPANISH_SYNC`: Enable Spanish subtitle synchronization improvements (default: true)
- `SPANISH_SUBTITLE_OFFSET`: Time offset in milliseconds for Spanish subtitles (default: -200)
- `SPANISH_SEGMENT_THRESHOLD`: Threshold in milliseconds for merging Spanish subtitle segments (default: 1000)

## Documentation

For complete documentation of the original project, visit:
[https://ahmetoner.github.io/whisper-asr-webservice](https://ahmetoner.github.io/whisper-asr-webservice)

## Using Docker Compose

This fork includes enhanced Docker Compose files for easy deployment:

### Standard CPU Version

```yaml
# docker-compose.yml
services:
  whisper-asr-webservice:
    image: hanibal920915/whisper-asr-webservice
    build:
      context: .
      dockerfile: Dockerfile
    ports:
      - "9000:9000"
    environment:
      - ASR_MODEL=base # Model to use (tiny, base, small, medium, large-v3)
      - ASR_ENGINE=openai_whisper # Engine to use (openai_whisper, faster_whisper, whisperx)
      - MODEL_IDLE_TIMEOUT=300 # Idle timeout to unload model (in seconds)
      - IMPROVE_SPANISH_SYNC=true # Improve Spanish subtitle synchronization
      - SPANISH_SUBTITLE_OFFSET=-200 # Time offset in milliseconds for Spanish subtitles
      - SPANISH_SEGMENT_THRESHOLD=1000 # Threshold in milliseconds for merging Spanish segments
    volumes:
      - ./cache:/root/.cache/ # Persist cache to avoid repeated downloads
    restart: unless-stopped
```

### GPU Version

```yaml
# docker-compose.gpu.yml
services:
  whisper-asr-webservice:
    image: hanibal920915/whisper-asr-webservice:latest-gpu
    build:
      context: .
      dockerfile: Dockerfile.gpu
    ports:
      - "9000:9000"
    environment:
      - ASR_MODEL=base
      - ASR_ENGINE=openai_whisper
      - ASR_DEVICE=cuda
    volumes:
      - ./cache:/root/.cache/
    restart: unless-stopped
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]
```

### Usage

```shell
# For CPU version
docker compose up -d

# For GPU version
docker compose -f docker-compose.gpu.yml up -d
```

## Bazarr Support

This fork adds a `/status` endpoint that is compatible with Bazarr for service health checking. The endpoint returns:

```json
{
  "version": "1.8.2",
  "status": "ok"
}
```

This allows Bazarr to verify the availability of the service for subtitle processing.

## Development

```shell
# Install poetry
pip3 install poetry

# Install dependencies
poetry install

# Run service
poetry run whisper-asr-webservice --host 0.0.0.0 --port 9000
```

After starting the service, visit `http://localhost:9000/docs` or `http://0.0.0.0:9000/docs` in your browser to access the Swagger UI documentation and try out the API endpoints. Alternatively, you can use `http://localhost:9000/redoc` for the ReDoc documentation interface.

## Credits

- This fork is based on the [whisper-asr-webservice](https://github.com/ahmetoner/whisper-asr-webservice) project by [ahmetoner](https://github.com/ahmetoner)
- This software uses libraries from the [FFmpeg](http://ffmpeg.org) project under the [LGPLv2.1](http://www.gnu.org/licenses/old-licenses/lgpl-2.1.html)

## Recent Improvements

- **Python 3.10 Compatibility**: Compatible with Python 3.10 for better stability and wider support
- **Multi-platform Support**: Added support for Raspberry Pi and various Linux architectures
- **GPU Acceleration**: NVIDIA CUDA support for Linux
- **Spanish Subtitle Synchronization**: Improved timing and segmentation for Spanish audio
- **Bazarr Integration**: Added `/status` endpoint for Bazarr compatibility
- **Integrated Swagger UI**: Removed Docker dependency for API documentation
- **CORS Support**: Added Cross-Origin Resource Sharing for better frontend integration
- **Enhanced Error Handling**: Better error responses and validation
- **Type Annotations**: Improved code quality with proper type hints
- **Documentation**: Updated API documentation with examples
# Actualización ter 10 jun 2025 18:42:40 -03
