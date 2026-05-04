import asyncio
from .base import BaseModule
from ..core.messages import TextMessage, InterruptionMessage

class LLMProcessor(BaseModule):
    """Módulo para procesar texto con un LLM en modo streaming."""
    
    def __init__(self):
        super().__init__("LLMProcessor")

    async def run(self):
        while self._is_running:
            item = await self.get_input()
            
            # Si hay un evento de interrupción activo, saltar el procesamiento
            if self.interruption_event and self.interruption_event.is_set():
                continue
                
            if isinstance(item, TextMessage) and item.is_final:
                print(f"[{self.name}] Procesando prompt: {item.text}")
                
                # Mock de generación de respuesta en streaming del LLM
                response_tokens = ["¡Claro!", " Aquí", " tienes", " la", " respuesta", " que", " pediste", "."]
                
                for token in response_tokens:
                    # Chequeo continuo del evento de interrupción (Barge-in)
                    if self.interruption_event and self.interruption_event.is_set():
                        print(f"[{self.name}] Generación interrumpida.")
                        break
                        
                    await asyncio.sleep(0.1)  # Simulamos retraso por generación de token
                    
                    # Enviamos el token en streaming hacia el TTS
                    await self.put_output(TextMessage(text=token, is_final=False))
                
                # Señalamos que terminó el mensaje actual si no fue interrumpido
                if not (self.interruption_event and self.interruption_event.is_set()):
                    await self.put_output(TextMessage(text="", is_final=True))
