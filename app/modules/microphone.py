import asyncio
from .base import BaseModule
from ..core.messages import AudioMessage

class MicrophoneSource(BaseModule):
    """Módulo para capturar audio en chunks desde el micrófono."""
    
    def __init__(self, sample_rate: int = 16000, chunk_size: int = 480):
        super().__init__("MicrophoneSource")
        self.sample_rate = sample_rate
        self.chunk_size = chunk_size

    async def run(self):
        # Implementación mock de streaming de micrófono
        # En el futuro se usará sounddevice para captura real
        print(f"[{self.name}] Comenzando captura de audio (mock)...")
        while self._is_running:
            # Simulamos que tomamos un chunk de ~30ms
            await asyncio.sleep(0.03)
            
            # 16-bit PCM (2 bytes por sample), inicializado con ceros
            dummy_data = b'\x00' * (self.chunk_size * 2) 
            
            # Enviamos el chunk a la cola
            await self.put_output(AudioMessage(data=dummy_data, sample_rate=self.sample_rate))
