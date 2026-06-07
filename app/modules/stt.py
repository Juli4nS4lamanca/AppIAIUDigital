import io
import wave
import asyncio
import os
from openai import AsyncOpenAI
from .base import BaseModule
from ..core.messages import AudioMessage, TextMessage

class STTProcessor(BaseModule):
    """Módulo Speech-To-Text para transcribir los segmentos de audio utilizando OpenAI o Groq."""
    
    def __init__(self, api_key: str | None = None, base_url: str | None = None, model: str = "whisper-1"):
        super().__init__("STTProcessor")
        # Priorizar variables de entorno de proveedor genérico (ej. Groq), luego OpenAI estándar
        self.api_key = api_key or os.getenv("IA_API_KEY") or os.getenv("OPENAI_API_KEY")
        self.base_url = base_url or os.getenv("IA_BASE_URL") or "https://api.openai.com/v1"
        self.model = os.getenv("STT_MODEL") or model
        
        self.client = AsyncOpenAI(api_key=self.api_key, base_url=self.base_url)

    async def run(self):
        print(f"[{self.name}] Procesador STT listo (Modelo: {self.model}, Endpoint: {self.base_url}).")
        
        while self._is_running:
            item = await self.get_input()
            
            # Si fuimos interrumpidos por el usuario, omitimos el procesamiento
            if self.interruption_event and self.interruption_event.is_set():
                continue
                
            if isinstance(item, AudioMessage):
                # Convertimos el búfer PCM crudo (16kHz, mono, 16-bit) a formato WAV en memoria
                wav_buffer = io.BytesIO()
                try:
                    with wave.open(wav_buffer, "wb") as wav_file:
                        wav_file.setnchannels(1)       # Mono
                        wav_file.setsampwidth(2)       # 16-bit (2 bytes por muestra)
                        wav_file.setframerate(item.sample_rate)
                        wav_file.writeframes(item.data)
                    
                    wav_buffer.seek(0)
                    wav_buffer.name = "audio.wav"  # Nombre virtual requerido por la API
                    
                    audio_seconds = len(item.data) / (item.sample_rate * 2)
                    print(f"[{self.name}] Transcribiendo fragmento de {audio_seconds:.2f} segundos de audio...")
                    
                    # Llamada asíncrona compatible con OpenAI y Groq
                    transcription = await self.client.audio.transcriptions.create(
                        model=self.model,
                        file=wav_buffer,
                        language="es"  # Idioma predeterminado
                    )
                    
                    text = transcription.text.strip()
                    if text:
                        print(f"[{self.name}] Transcripción finalizada: '{text}'")
                        # Emitimos el texto hacia el LLM
                        await self.put_output(TextMessage(text=text, is_final=True))
                    else:
                        print(f"[{self.name}] Transcripción vacía, omitiendo.")
                        
                except Exception as e:
                    print(f"[{self.name}] Error en la API de STT ({self.model}): {e}")
                finally:
                    wav_buffer.close()
