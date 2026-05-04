import asyncio
from .base import BaseModule
from ..core.messages import AudioMessage, TextMessage

class STTProcessor(BaseModule):
    """Módulo Speech-To-Text para transcribir los segmentos de audio."""
    
    def __init__(self):
        super().__init__("STTProcessor")
        self.audio_buffer = bytearray()
        self.tick = 0

    async def run(self):
        while self._is_running:
            item = await self.get_input()
            
            if isinstance(item, AudioMessage):
                self.audio_buffer.extend(item.data)
                
                # Mock: Simular que después de acumular suficiente audio,
                # procesamos el STT (por ejemplo Whisper o Deepgram).
                if len(self.audio_buffer) > 16000 * 2: # 1 segundo acumulado (mock)
                    self.tick += 1
                    text = f"Hola, esta es una transcripción de prueba número {self.tick}."
                    print(f"[{self.name}] Transcrito: '{text}'")
                    
                    # Generamos el texto hacia el LLM
                    await self.put_output(TextMessage(text=text, is_final=True))
                    self.audio_buffer.clear()
