import torchaudio
from transformers import SeamlessM4Tv2ForSpeechToText
from transformers import SeamlessM4TTokenizer, SeamlessM4TFeatureExtractor
import time
import torch
import io
import numpy as np
from typing import Dict, Union
import warnings

torch.cuda.empty_cache()

class STTModel():
    model = SeamlessM4Tv2ForSpeechToText.from_pretrained("ai4bharat/indic-seamless", torch_dtype=torch.bfloat16, device_map="cuda" if torch.cuda.is_available() else "cpu")
    processor = SeamlessM4TFeatureExtractor.from_pretrained("ai4bharat/indic-seamless")
    tokenizer = SeamlessM4TTokenizer.from_pretrained("ai4bharat/indic-seamless")

    @classmethod
    def transcribe_from_bytes(cls, audio_bytes: bytes, sample_rate: int = 16000, format: str = "wav") -> Dict[str, Union[str, float, bool]]:
        """
        Transcribe audio from byte array
        
        Args:
            audio_bytes: Audio data as bytes
            sample_rate: Sample rate of the audio (default: 16000)
            format: Audio format (default: "wav")
            
        Returns:
            Dict with keys: 'text', 'success', 'error', 'processing_time'
        """
        start_time = time.perf_counter()
        
        try:
            # Convert bytes to audio tensor
            audio_buffer = io.BytesIO(audio_bytes)
            audio, orig_freq = torchaudio.load(audio_buffer, format=format)
            
            # Resample to 16kHz if needed
            if orig_freq != sample_rate:
                audio = torchaudio.functional.resample(audio, orig_freq=orig_freq, new_freq=sample_rate)
            
            # Ensure mono audio (take first channel if stereo)
            if audio.shape[0] > 1:
                audio = audio[0:1, :]
            
            # Process audio
            device = "cuda" if torch.cuda.is_available() else "cpu"
            audio_inputs = cls.processor(audio, sampling_rate=sample_rate, return_tensors="pt").to(device)
            
            # Generate transcription
            with torch.no_grad():
                text_out = cls.model.generate(**audio_inputs, tgt_lang="eng")[0].cpu().numpy().squeeze()
                hindi_text_out = cls.model.generate(**audio_inputs, tgt_lang="hin")[0].cpu().numpy().squeeze()
            
            # Decode text
            transcribed_text = cls.tokenizer.decode(text_out, clean_up_tokenization_spaces=True, skip_special_tokens=True)
            transcribed_hindi_text = cls.tokenizer.decode(hindi_text_out, clean_up_tokenization_spaces=True, skip_special_tokens=True)
            
            processing_time = time.perf_counter() - start_time
            
            return {
                "text": transcribed_text.strip(),
                "hindi_text": transcribed_hindi_text.strip(),
                "success": True,
                "error": None,
                "processing_time": processing_time
            }
            
        except Exception as e:
            processing_time = time.perf_counter() - start_time
            return {
                "text": "",
                "success": False,
                "error": str(e),
                "processing_time": processing_time
            }

    @classmethod
    def transcribe_from_numpy(cls, audio_array: np.ndarray, sample_rate: int = 16000) -> Dict[str, Union[str, float, bool]]:
        """
        Transcribe audio from numpy array
        
        Args:
            audio_array: Audio data as numpy array
            sample_rate: Sample rate of the audio (default: 16000)
            
        Returns:
            Dict with keys: 'text', 'success', 'error', 'processing_time'
        """
        start_time = time.perf_counter()
        
        try:
            # Convert numpy array to torch tensor
            if audio_array.ndim == 1:
                audio = torch.from_numpy(audio_array).float().unsqueeze(0)
            else:
                audio = torch.from_numpy(audio_array).float()
                
            # Ensure mono audio (take first channel if stereo)
            if audio.shape[0] > 1:
                audio = audio[0:1, :]
            
            # Process audio
            device = "cuda" if torch.cuda.is_available() else "cpu"
            audio_inputs = cls.processor(audio, sampling_rate=sample_rate, return_tensors="pt").to(device)
            
            # Generate transcription
            with torch.no_grad():
                text_out = cls.model.generate(**audio_inputs, tgt_lang="eng")[0].cpu().numpy().squeeze()
                hindi_text_out = cls.model.generate(**audio_inputs, tgt_lang="hin")[0].cpu().numpy().squeeze()
            # Decode text
            transcribed_text = cls.tokenizer.decode(text_out, clean_up_tokenization_spaces=True, skip_special_tokens=True)
            transcribed_hindi_text = cls.tokenizer.decode(hindi_text_out, clean_up_tokenization_spaces=True, skip_special_tokens=True)
            
            processing_time = time.perf_counter() - start_time
            
            return {
                "text": transcribed_text.strip(),
                "hindi_text": transcribed_hindi_text.strip(),
                "success": True,
                "error": None,
                "processing_time": processing_time
            }
            
        except Exception as e:
            processing_time = time.perf_counter() - start_time
            return {
                "text": "",
                "success": False,
                "error": str(e),
                "processing_time": processing_time
            }

    @classmethod
    def transcribe(cls) -> str:
        """Legacy method for backward compatibility"""
        warnings.warn("transcribe() is deprecated. Use transcribe_from_bytes() or transcribe_from_numpy()", DeprecationWarning)
        audio, orig_freq = torchaudio.load("/home/ishant-gupta/Downloads/input.ogg", format="ogg")
        audio = torchaudio.functional.resample(audio, orig_freq=orig_freq, new_freq=16_000)
        start = time.perf_counter()
        audio_inputs = cls.processor(audio, sampling_rate=16_000, return_tensors="pt").to("cuda")
        text_out = cls.model.generate(**audio_inputs, tgt_lang="eng")[0].cpu().numpy().squeeze()
        hindi_text_out = cls.model.generate(**audio_inputs, tgt_lang="hin")[0].cpu().numpy().squeeze()
        end = time.perf_counter()
        print(end-start)
        return cls.tokenizer.decode(text_out, clean_up_tokenization_spaces=True, skip_special_tokens=True), cls.tokenizer.decode(hindi_text_out, clean_up_tokenization_spaces=True, skip_special_tokens=True)


# Convenience function for easy import
def transcribe_audio_bytes(audio_bytes: bytes, sample_rate: int = 16000, format: str = "wav") -> Dict[str, Union[str, float, bool]]:
    """Convenience function to transcribe audio from bytes"""
    return STTModel.transcribe_from_bytes(audio_bytes, sample_rate, format)

def transcribe_audio_numpy(audio_array: np.ndarray, sample_rate: int = 16000) -> Dict[str, Union[str, float, bool]]:
    """Convenience function to transcribe audio from numpy array"""
    return STTModel.transcribe_from_numpy(audio_array, sample_rate)

