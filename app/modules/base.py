import asyncio
from abc import ABC, abstractmethod
from typing import Any

class BaseModule(ABC):
    """Clase base para todos los módulos del pipeline."""
    
    def __init__(self, name: str):
        self.name = name
        self.input_queue: asyncio.Queue = asyncio.Queue()
        self.output_queue: asyncio.Queue = asyncio.Queue()
        self.interruption_event: asyncio.Event | None = None
        self._is_running = False
        self._task: asyncio.Task | None = None

    async def start(self):
        """Inicia el ciclo de ejecución asíncrono del módulo."""
        self._is_running = True
        self._task = asyncio.create_task(self.run())
        print(f"[{self.name}] Iniciado.")

    async def stop(self):
        """Detiene el módulo y cancela la tarea en ejecución."""
        self._is_running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        print(f"[{self.name}] Detenido.")

    async def put_output(self, item: Any):
        """Envía un elemento a la cola de salida."""
        await self.output_queue.put(item)

    async def get_input(self) -> Any:
        """Obtiene un elemento de la cola de entrada (bloqueante)."""
        return await self.input_queue.get()

    @abstractmethod
    async def run(self):
        """Ciclo principal de ejecución. Debe ser implementado por subclases."""
        pass
