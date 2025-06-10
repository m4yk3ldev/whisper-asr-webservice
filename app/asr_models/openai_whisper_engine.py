import time
from io import StringIO
from threading import Thread
from typing import BinaryIO, Union

import torch
import whisper
from whisper.utils import ResultWriter, WriteJSON, WriteSRT, WriteTSV, WriteTXT, WriteVTT

from app.asr_models.asr_model import ASRModel
from app.config import CONFIG


class OpenAIWhisperASR(ASRModel):

    def load_model(self):

        if torch.cuda.is_available():
            self.model = whisper.load_model(name=CONFIG.MODEL_NAME, download_root=CONFIG.MODEL_PATH).cuda()
        else:
            self.model = whisper.load_model(name=CONFIG.MODEL_NAME, download_root=CONFIG.MODEL_PATH)

        Thread(target=self.monitor_idleness, daemon=True).start()

    def transcribe(
        self,
        audio,
        task: Union[str, None],
        language: Union[str, None],
        initial_prompt: Union[str, None],
        vad_filter: Union[bool, None],
        word_timestamps: Union[bool, None],
        options: Union[dict, None],
        output,
    ):
        self.last_activity_time = time.time()

        with self.model_lock:
            if self.model is None:
                self.load_model()

        options_dict = {"task": task}
        if language:
            options_dict["language"] = language
        if initial_prompt:
            options_dict["initial_prompt"] = initial_prompt
        if word_timestamps:
            options_dict["word_timestamps"] = word_timestamps
        with self.model_lock:
            result = self.model.transcribe(audio, **options_dict)

        output_file = StringIO()
        self.write_result(result, output_file, output)
        output_file.seek(0)

        return output_file

    def language_detection(self, audio):

        self.last_activity_time = time.time()

        with self.model_lock:
            if self.model is None:
                self.load_model()

        # load audio and pad/trim it to fit 30 seconds
        audio = whisper.pad_or_trim(audio)

        # make log-Mel spectrogram and move to the same device as the model
        mel = whisper.log_mel_spectrogram(audio, self.model.dims.n_mels).to(self.model.device)

        # detect the spoken language
        with self.model_lock:
            _, probs = self.model.detect_language(mel)
        detected_lang_code = max(probs, key=probs.get)

        return detected_lang_code, probs[max(probs)]
        
    def _improve_spanish_sync(self, result):
        """Apply Spanish-specific improvements to the transcription result."""
        if not result.get("segments"):
            return
            
        # Apply offset to start and end times for better sync
        offset_sec = CONFIG.SPANISH_SUBTITLE_OFFSET / 1000.0
        threshold_sec = CONFIG.SPANISH_SEGMENT_THRESHOLD / 1000.0
        
        # Adjust timing for each segment
        for segment in result["segments"]:
            # Apply offset to improve synchronization
            segment["start"] = max(0, segment["start"] + offset_sec)
            segment["end"] = segment["end"] + offset_sec
            
            # Adjust word-level timestamps if available
            if "words" in segment and segment["words"]:
                for word in segment["words"]:
                    word["start"] = max(0, word["start"] + offset_sec)
                    word["end"] = word["end"] + offset_sec
        
        # Optimize segment breaks for Spanish
        # Spanish often needs shorter segments for better sync
        new_segments = []
        for i, segment in enumerate(result["segments"]):
            if i > 0 and segment["start"] - result["segments"][i-1]["end"] < threshold_sec:
                # If segments are close, ensure there's a small gap
                segment["start"] = result["segments"][i-1]["end"] + 0.1
            new_segments.append(segment)
            
        result["segments"] = new_segments

    def write_result(self, result: dict, file: BinaryIO, output: Union[str, None]):
        options = {
            "max_line_width": CONFIG.SUBTITLE_MAX_LINE_WIDTH, 
            "max_line_count": CONFIG.SUBTITLE_MAX_LINE_COUNT, 
            "highlight_words": CONFIG.SUBTITLE_HIGHLIGHT_WORDS
        }
        
        # Apply Spanish-specific improvements if enabled and language is Spanish
        if CONFIG.IMPROVE_SPANISH_SYNC and result.get("language") == "es":
            self._improve_spanish_sync(result)
            
        if output == "srt":
            WriteSRT(ResultWriter).write_result(result, file=file, options=options)
        elif output == "vtt":
            WriteVTT(ResultWriter).write_result(result, file=file, options=options)
        elif output == "tsv":
            WriteTSV(ResultWriter).write_result(result, file=file, options=options)
        elif output == "json":
            WriteJSON(ResultWriter).write_result(result, file=file, options=options)
        else:
            WriteTXT(ResultWriter).write_result(result, file=file, options=options)
