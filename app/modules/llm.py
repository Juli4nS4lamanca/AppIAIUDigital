import asyncio
import os
from openai import AsyncOpenAI
from .base import BaseModule
from ..core.messages import TextMessage

class LLMProcessor(BaseModule):
    """Módulo para procesar texto con un LLM en modo streaming utilizando OpenAI o Groq."""
    
    def __init__(self, api_key: str | None = None, base_url: str | None = None, model: str = "gpt-4o-mini"):
        super().__init__("LLMProcessor")
        self.api_key = api_key or os.getenv("IA_API_KEY") or os.getenv("OPENAI_API_KEY")
        self.base_url = base_url or os.getenv("IA_BASE_URL") or "https://api.openai.com/v1"
        self.model = os.getenv("LLM_MODEL") or model
        
        self.client = AsyncOpenAI(api_key=self.api_key, base_url=self.base_url)
        self.history = [
            {
                "role": "system", 
                "content": (
                    "Eres un asistente de voz conversacional altamente eficiente y rápido. "
                    "Responde siempre de forma extremadamente breve y al grano (máximo 1 o 2 oraciones simples). "
                    "Evita listas numeradas o formateo complejo. Mantén el tono natural y coloquial."
                )
            }
        ]

    async def run(self):
        print(f"[{self.name}] Procesador LLM listo (Modelo: {self.model}, Endpoint: {self.base_url}).")
        
        while self._is_running:
            item = await self.get_input()
            
            # Si hay un evento de interrupción activo, saltar el procesamiento
            if self.interruption_event and self.interruption_event.is_set():
                continue
                
            if isinstance(item, TextMessage) and item.is_final:
                print(f"[{self.name}] Procesando prompt: {item.text}")
                
                # Agregamos la entrada del usuario al historial
                self.history.append({"role": "user", "content": item.text})
                
                try:
                    # Invocación en streaming asíncrono
                    response = await self.client.chat.completions.create(
                        model=self.model,
                        messages=self.history,
                        stream=True,
                        max_tokens=150
                    )
                    
                    full_response = ""
                    async for chunk in response:
                        # Chequeo continuo del evento de interrupción (Barge-in)
                        if self.interruption_event and self.interruption_event.is_set():
                            print(f"[{self.name}] Generación interrumpida por el usuario.")
                            break
                        
                        token = chunk.choices[0].delta.content or ""
                        if token:
                            full_response += token
                            # Enviamos cada token de inmediato al TTS
                            await self.put_output(TextMessage(text=token, is_final=False))
                    
                    # Si completamos la generación sin interrupciones, guardamos la respuesta en el historial
                    if not (self.interruption_event and self.interruption_event.is_set()):
                        self.history.append({"role": "assistant", "content": full_response})
                        # Señalamos que terminó el mensaje actual
                        await self.put_output(TextMessage(text="", is_final=True))
                        
                except Exception as e:
                    print(f"[{self.name}] Error en la API de OpenAI (LLM): {e}")

