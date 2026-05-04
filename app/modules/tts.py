import asyncio
from .base import BaseModule
from ..core.messages import TextMessage, InterruptionMessage

class TTSSpeaker(BaseModule):
    """Módulo Text-to-Speech con soporte para streaming y cancelación."""
    
    def __init__(self):
        super().__init__("TTSSpeaker")
        self.text_buffer = ""
        self.playback_task: asyncio.Task | None = None

    async def _play_audio(self, text: str):
        """Simula la síntesis y la reproducción del audio."""
        print(f"[{self.name}] Sintetizando y reproduciendo: '{text}'")
        try:
            # Mock de delay de síntesis y reproducción por chunks
            for _ in range(5):
                await asyncio.sleep(0.2)
        except asyncio.CancelledError:
            print(f"[{self.name}] Reproducción de audio cancelada debido a interrupción.")
            raise
        print(f"[{self.name}] Reproducción finalizada.")

    async def run(self):
        while self._is_running:
            item = await self.get_input()
            
            if isinstance(item, InterruptionMessage):
                # Detenemos inmediatamente cualquier reproducción en curso
                if self.playback_task and not self.playback_task.done():
                    self.playback_task.cancel()
                self.text_buffer = ""  # Limpiamos el buffer
                
            elif isinstance(item, TextMessage):
                # Si estamos interrumpidos globalmente, ignoramos
                if self.interruption_event and self.interruption_event.is_set():
                    continue

                if item.is_final:
                    # Sintetizar el buffer final acumulado
                    if self.text_buffer:
                        # Creamos una tarea independiente para la reproducción
                        # Así podemos cancelarla si entra un InterruptionMessage
                        self.playback_task = asyncio.create_task(self._play_audio(self.text_buffer))
                        self.text_buffer = ""
                else:
                    self.text_buffer += item.text
                    
                    # En una implementación avanzada, aquí verificaríamos si el buffer
                    # tiene una frase completa para ir reproduciéndola en streaming
                    # y no esperar al mensaje final.
