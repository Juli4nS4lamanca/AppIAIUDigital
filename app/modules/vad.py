import asyncio
from .base import BaseModule
from ..core.messages import AudioMessage, InterruptionMessage

class VADProcessor(BaseModule):
    """Módulo Voice Activity Detection (VAD) para segmentar el audio y detectar barge-in."""
    
    def __init__(self):
        super().__init__("VADProcessor")
        # En el futuro se integrará webrtcvad aquí
        self.is_speaking = False

    async def run(self):
        while self._is_running:
            item = await self.get_input()
            
            if isinstance(item, AudioMessage):
                # Implementación mock de VAD
                # Simular que de vez en cuando el usuario habla
                is_speech = False # Aquí iría la lógica webrtcvad
                
                if is_speech and not self.is_speaking:
                    self.is_speaking = True
                    print(f"[{self.name}] Actividad de voz detectada!")
                    
                    # Logica de interrupción (Barge-in)
                    if self.interruption_event:
                        self.interruption_event.set()
                        # Se envía un mensaje especial en el pipeline para notificar 
                        await self.put_output(InterruptionMessage())
                        
                elif not is_speech and self.is_speaking:
                    self.is_speaking = False
                    
                # Pasar el chunk hacia el STT si es que estamos en medio del habla
                # Por ahora para demostración, siempre lo pasamos (o solo si is_speaking)
                if True:  # En realidad: if self.is_speaking o si estamos capturando buffer
                    await self.put_output(item)
