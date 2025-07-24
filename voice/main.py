import torchaudio
from transformers import SeamlessM4Tv2ForSpeechToText
from transformers import SeamlessM4TTokenizer, SeamlessM4TFeatureExtractor
import time
import torch

torch.cuda.empty_cache()
model = SeamlessM4Tv2ForSpeechToText.from_pretrained("ai4bharat/indic-seamless", torch_dtype=torch.bfloat16, device_map="cuda")
processor = SeamlessM4TFeatureExtractor.from_pretrained("ai4bharat/indic-seamless")
tokenizer = SeamlessM4TTokenizer.from_pretrained("ai4bharat/indic-seamless")

audio, orig_freq = torchaudio.load("./audio.wav")
audio = torchaudio.functional.resample(audio, orig_freq=orig_freq, new_freq=16_000)

start = time.perf_counter()
audio_inputs = processor(audio, sampling_rate=16_000, return_tensors="pt").to("cuda")
text_out = model.generate(**audio_inputs, tgt_lang="hin")[0].cpu().numpy().squeeze()
print(tokenizer.decode(text_out, clean_up_tokenization_spaces=True, skip_special_tokens=True))
end = time.perf_counter()
print(end-start)