import torchaudio
from transformers import SeamlessM4Tv2ForSpeechToText
from transformers import SeamlessM4TTokenizer, SeamlessM4TFeatureExtractor
import time
import torch

torch.cuda.empty_cache()

class STTModel():
    model = SeamlessM4Tv2ForSpeechToText.from_pretrained("ai4bharat/indic-seamless", torch_dtype=torch.bfloat16, device_map="cuda" if torch.cuda.is_available() else "cpu")
    processor = SeamlessM4TFeatureExtractor.from_pretrained("ai4bharat/indic-seamless")
    tokenizer = SeamlessM4TTokenizer.from_pretrained("ai4bharat/indic-seamless")

    @classmethod
    def transcribe(cls) -> str:
        audio, orig_freq = torchaudio.load("/home/ishant-gupta/Downloads/input.ogg", format="ogg")
        audio = torchaudio.functional.resample(audio, orig_freq=orig_freq, new_freq=16_000)
        start = time.perf_counter()
        audio_inputs = cls.processor(audio, sampling_rate=16_000, return_tensors="pt").to("cuda")
        text_out = cls.model.generate(**audio_inputs, tgt_lang="eng")[0].cpu().numpy().squeeze()
        end = time.perf_counter()
        print(end-start)
        return cls.tokenizer.decode(text_out, clean_up_tokenization_spaces=True, skip_special_tokens=True)

