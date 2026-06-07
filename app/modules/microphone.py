import asyncio
import sounddevice as sd
from .base import BaseModule
from ..core.messages import AudioMessage

class MicrophoneSource(BaseModule):
    """Módulo para capturar audio en tiempo real desde el micrófono del sistema."""
    
    def __init__(self, sample_rate: int = 16000, chunk_size: int = 480):
        super().__init__("MicrophoneSource")
        self.sample_rate = sample_rate
        self.chunk_size = chunk_size
        self._stream: sd.RawInputStream | None = None
        self._loop: asyncio.AbstractEventLoop | None = None

    def _audio_callback(self, indata, frames, time_info, status):
        """Callback invocado por sounddevice en un hilo dedicado por cada bloque de audio capturado."""
        if status:
            print(f"[{self.name}] Estado del stream de audio: {status}")
        
        # indata contiene los bytes PCM crudos ya que usamos RawInputStream.
        # Copiamos los bytes ya que el búfer original de PortAudio se reutiliza.
        data_copy = bytes(indata)
        
        # Enviamos de forma segura la tarea de encolar al hilo de asyncio
        if self._loop and self._is_running:
            asyncio.run_coroutine_threadsafe(
                self.put_output(AudioMessage(data=data_copy, sample_rate=self.sample_rate)),
                self._loop
            )

    async def run(self):
        # Obtenemos el loop de eventos asíncronos activo en este hilo
        self._loop = asyncio.get_running_loop()
        print(f"[{self.name}] Iniciando captura de audio real (16kHz, mono, PCM 16-bit)...")
        
        try:
            # Inicializamos el Stream de entrada crudo
            self._stream = sd.RawInputStream(
                samplerate=self.sample_rate,
                blocksize=self.chunk_size,
                channels=1,
                dtype='int16',
                callback=self._audio_callback
            )
            
            # Activamos el stream usando el administrador de contexto
            with self._stream:
                print(f"[{self.name}] Micrófono activo y transmitiendo chunks.")
                # Mantenemos el bucle activo mientras el módulo deba estar corriendo
                while self._is_running:
                    await asyncio.sleep(0.1)
                    
        except Exception as e:
            print(f"[{self.name}] Error en la captura de audio por hardware: {e}")
        finally:
            print(f"[{self.name}] Deteniendo micrófono y liberando recursos...")
            if self._stream:
                self._stream.close()
                self._stream = None
            self._loop = None

