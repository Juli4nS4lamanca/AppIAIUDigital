import asyncio
from typing import List
from ..modules.base import BaseModule

class Pipeline:
    """Gestiona y orquesta la conexión entre los diferentes módulos."""
    
    def __init__(self):
        self.modules: List[BaseModule] = []
        self.interruption_event = asyncio.Event()

    def add_module(self, module: BaseModule):
        """Añade un módulo al final del pipeline."""
        self.modules.append(module)

    def link_modules(self):
        """Conecta la cola de salida de cada módulo a la de entrada del siguiente."""
        for i in range(len(self.modules) - 1):
            self.modules[i].output_queue = self.modules[i+1].input_queue

    async def start(self):
        """Inicia todos los módulos del pipeline."""
        self.link_modules()
        
        for module in self.modules:
            # Compartimos el evento de interrupción (Barge-in) entre todos los módulos
            module.interruption_event = self.interruption_event
            await module.start()
            
        print("[Pipeline] Todos los módulos iniciados.")

    async def stop(self):
        """Detiene todos los módulos del pipeline."""
        for module in reversed(self.modules):
            await module.stop()
        print("[Pipeline] Todos los módulos detenidos.")
        
    async def run_forever(self):
        """Mantiene el pipeline en ejecución."""
        await self.start()
        try:
            while True:
                await asyncio.sleep(0.5)
                # Aquí se puede añadir lógica para resetear el evento de interrupción
                # después de que haya sido procesado correctamente.
                if self.interruption_event.is_set():
                    # Para simplificar en esta fase, lo limpiamos tras detectarlo
                    print("[Pipeline] Evento de interrupción procesado, limpiando estado.")
                    self.interruption_event.clear()
        except asyncio.CancelledError:
            await self.stop()
