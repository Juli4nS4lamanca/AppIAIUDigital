import asyncio
import os
import tempfile
import ctypes
from ctypes import windll
import edge_tts
from .base import BaseModule
from ..core.messages import TextMessage, InterruptionMessage

class TTSSpeaker(BaseModule):
    """Módulo Text-to-Speech con soporte para streaming gratuito usando Microsoft Edge TTS y Windows MCI nativo (ctypes)."""
    
    def __init__(self, voice: str = "es-MX-JorgeNeural"):
        super().__init__("TTSSpeaker")
        # Permitir configurar la voz mediante variable de entorno
        self.voice = os.getenv("TTS_VOICE") or voice
        self.text_buffer = ""
        
        # Gestión de cola de reproducción para reducir latencia (Sentence segmenting)
        self.playback_queue: asyncio.Queue[str] = asyncio.Queue()
        self.playback_task: asyncio.Task | None = None
        self._worker_task: asyncio.Task | None = None
        self.play_counter = 0
        
        # Cargar winmm.dll
        try:
            self.winmm = windll.winmm
            print(f"[{self.name}] Biblioteca winmm.dll (MCI) cargada correctamente para reproducción de audio nativa.")
        except Exception as e:
            self.winmm = None
            print(f"[{self.name}] ERROR: No se pudo cargar winmm.dll. La reproducción fallará. Detalles: {e}")

    def _mci_send(self, command: str):
        """Envía un comando MCI a Windows de manera segura."""
        if not self.winmm:
            return
        # Usamos la versión Unicode (W) para evitar problemas de codificación en las rutas
        self.winmm.mciSendStringW(command, None, 0, 0)

    async def _play_audio(self, text: str):
        """Sintetiza texto con Edge TTS (MP3), lo escribe a un archivo temporal y lo reproduce usando MCI de Windows."""
        if not self.winmm:
            print(f"[{self.name}] No se puede reproducir audio (winmm.dll no disponible).")
            return
            
        print(f"[{self.name}] Sintetizando y reproduciendo con Edge-TTS (MCI): '{text}'")
        
        # Crear un archivo temporal único para evitar conflictos de bloqueo de archivos
        self.play_counter += 1
        temp_dir = tempfile.gettempdir()
        temp_file_path = os.path.join(temp_dir, f"mva_tts_{self.play_counter}.mp3")
        alias = f"tts_{self.play_counter}"
        
        try:
            # 1. Comunicar con el servicio gratuito de Microsoft Edge TTS
            communicate = edge_tts.Communicate(text, self.voice)
            mp3_data = bytearray()
            
            async for chunk in communicate.stream():
                # Comprobamos si fuimos interrumpidos a mitad del streaming
                if self.interruption_event and self.interruption_event.is_set():
                    print(f"[{self.name}] Streaming de audio cancelado por interrupción.")
                    return
                
                if chunk["type"] == "audio":
                    mp3_data.extend(chunk["data"])
            
            if not mp3_data:
                return

            # Comprobamos interrupción antes de escribir y reproducir
            if self.interruption_event and self.interruption_event.is_set():
                return

            # 2. Guardar los bytes de MP3 en el archivo temporal
            with open(temp_file_path, "wb") as f:
                f.write(mp3_data)

            # 3. Reproducir usando comandos de Windows MCI
            self._mci_send(f'close {alias}')  # Asegurar alias cerrado
            
            # Abrir archivo. Usamos comillas dobles en la ruta por si tiene espacios
            open_command = f'open "{temp_file_path}" type mpegvideo alias {alias}'
            self._mci_send(open_command)
            
            # Iniciar reproducción en segundo plano (sin bloquear el hilo de Python)
            self._mci_send(f'play {alias}')
            
            # 4. Monitorear el estado de la reproducción en segundo plano de manera asíncrona
            # Mientras MCI nos reporte que está reproduciendo ("playing")
            while True:
                # Comprobar estado
                buf = ctypes.create_unicode_buffer(128)
                self.winmm.mciSendStringW(f"status {alias} mode", buf, 127, 0)
                status = buf.value.strip()
                
                if status != "playing":
                    break
                    
                # Si entra una interrupción, detenemos la reproducción de inmediato
                if self.interruption_event and self.interruption_event.is_set():
                    print(f"[{self.name}] Interrupción detectada. Deteniendo audio MCI.")
                    self._mci_send(f'stop {alias}')
                    break
                    
                await asyncio.sleep(0.05)
                    
        except asyncio.CancelledError:
            print(f"[{self.name}] Tarea de reproducción cancelada.")
            self._mci_send(f'stop {alias}')
            raise
        except Exception as e:
            print(f"[{self.name}] Error en reproducción MCI: {e}")
        finally:
            # 5. Liberar recursos de MCI y borrar el archivo temporal
            self._mci_send(f'close {alias}')
            try:
                if os.path.exists(temp_file_path):
                    os.remove(temp_file_path)
            except Exception as e:
                # Silencioso por si Windows aún retiene el archivo unos milisegundos
                pass

    async def _playback_worker(self):
        """Procesa de forma secuencial las oraciones encoladas para reproducción."""
        while True:
            try:
                sentence = await self.playback_queue.get()
                
                # Creamos y esperamos la tarea de reproducción
                self.playback_task = asyncio.create_task(self._play_audio(sentence))
                await self.playback_task
                
                self.playback_queue.task_done()
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"[{self.name}] Error en el worker de reproducción: {e}")

    async def run(self):
        print(f"[{self.name}] Procesador TTS listo (Voz: {self.voice}).")
        
        # Iniciamos el worker secundario que se encarga de escuchar la cola de reproducción
        self._worker_task = asyncio.create_task(self._playback_worker())
        
        try:
            while self._is_running:
                item = await self.get_input()
                
                if isinstance(item, InterruptionMessage):
                    print(f"[{self.name}] Mensaje de interrupción. Deteniendo reproducción...")
                    
                    # 1. Enviar comando stop a todos los alias activos del contador actual
                    if self.winmm:
                        self._mci_send(f'stop tts_{self.play_counter}')
                    
                    # 2. Cancelar la tarea asíncrona de reproducción actual si está activa
                    if self.playback_task and not self.playback_task.done():
                        self.playback_task.cancel()
                        
                    # 3. Vaciar la cola de reproducción recreándola
                    self.playback_queue = asyncio.Queue()
                    
                    # 4. Limpiar el acumulador de texto
                    self.text_buffer = ""
                    
                elif isinstance(item, TextMessage):
                    # Si ya estamos en estado de interrupción global, ignoramos nuevos tokens
                    if self.interruption_event and self.interruption_event.is_set():
                        continue

                    if item.is_final:
                        # Al recibir el fin de flujo, forzamos la síntesis de lo que quede en el búfer
                        remaining_text = self.text_buffer.strip()
                        if remaining_text:
                            await self.playback_queue.put(remaining_text)
                            self.text_buffer = ""
                    else:
                        self.text_buffer += item.text
                        
                        # Segmentación de oraciones en tiempo real para reducir la latencia (TTFA)
                        for punctuation in [".", "?", "!"]:
                            if punctuation in self.text_buffer:
                                parts = self.text_buffer.split(punctuation, 1)
                                sentence = parts[0] + punctuation
                                self.text_buffer = parts[1]
                                
                                sentence_clean = sentence.strip()
                                if sentence_clean:
                                    await self.playback_queue.put(sentence_clean)
                                break
                                
        finally:
            # Aseguramos la limpieza de las tareas en segundo plano al detener el módulo
            if self._worker_task:
                self._worker_task.cancel()
            if self.playback_task and not self.playback_task.done():
                self.playback_task.cancel()
            if self.winmm:
                self._mci_send(f'stop tts_{self.play_counter}')
                self._mci_send(f'close tts_{self.play_counter}')
            print(f"[{self.name}] Módulo de TTS apagado y recursos de Windows MCI liberados.")

