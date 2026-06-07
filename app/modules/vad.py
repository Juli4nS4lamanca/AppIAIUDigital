import asyncio
import collections
import struct
from .base import BaseModule
from ..core.messages import AudioMessage, InterruptionMessage

try:
    import webrtcvad
except ImportError:
    webrtcvad = None

class VADProcessor(BaseModule):
    """Módulo Voice Activity Detection (VAD) para segmentar el audio y detectar barge-in."""
    
    def __init__(
        self, 
        aggressiveness: int = 3, 
        sample_rate: int = 16000, 
        frame_duration_ms: int = 30,
        window_duration_ms: int = 300,
        speech_threshold_ratio: float = 0.8,
        silence_threshold_ratio: float = 0.9
    ):
        super().__init__("VADProcessor")
        self.sample_rate = sample_rate
        self.frame_duration_ms = frame_duration_ms
        self.frame_size = int(sample_rate * frame_duration_ms / 1000)  # e.g., 480 para 30ms a 16kHz
        self.frame_bytes_size = self.frame_size * 2  # 16-bit PCM = 2 bytes por muestra
        
        # Inicializar webrtcvad si está disponible
        if webrtcvad:
            self.vad = webrtcvad.Vad(aggressiveness)
            print(f"[{self.name}] webrtcvad cargado con agresividad: {aggressiveness}")
        else:
            self.vad = None
            print(f"[{self.name}] ADVERTENCIA: 'webrtcvad' no instalado. Usando fallback de energía RMS.")
            
        # Parámetros de ventana deslizante (Debouncing)
        self.window_size = int(window_duration_ms / frame_duration_ms)
        self.ring_buffer = collections.deque(maxlen=self.window_size)
        
        # Umbrales
        self.speech_threshold = int(self.window_size * speech_threshold_ratio)
        self.silence_threshold = int(self.window_size * silence_threshold_ratio)
        
        self.is_speaking = False
        self.speech_buffer = bytearray()
        self.audio_accumulator = bytearray()

    def _is_speech(self, frame_bytes: bytes) -> bool:
        """Determina si un frame de audio contiene habla utilizando webrtcvad o fallback RMS."""
        if self.vad:
            try:
                return self.vad.is_speech(frame_bytes, self.sample_rate)
            except Exception as e:
                print(f"[{self.name}] Error evaluando frame con webrtcvad: {e}")
                
        # Fallback basado en energía RMS (Root Mean Square)
        count = len(frame_bytes) // 2
        if count == 0:
            return False
        shorts = struct.unpack(f"{count}h", frame_bytes)
        sum_squares = sum(s * s for s in shorts)
        rms = (sum_squares / count) ** 0.5
        
        # Un valor superior a 800 en un rango de 16-bit signed PCM (~32768) representa habla/ruido notable
        return rms > 800

    async def run(self):
        print(f"[{self.name}] Procesador VAD activo. Ventana: {self.window_size} frames ({self.frame_duration_ms * self.window_size}ms).")
        
        while self._is_running:
            item = await self.get_input()
            
            if isinstance(item, AudioMessage):
                if item.sample_rate != self.sample_rate:
                    # En una versión avanzada, aquí se incorporaría un resampler
                    pass
                
                # Acumulamos los bytes recibidos
                self.audio_accumulator.extend(item.data)
                
                # Extraemos y procesamos frames de tamaño exacto
                while len(self.audio_accumulator) >= self.frame_bytes_size:
                    frame_bytes = bytes(self.audio_accumulator[:self.frame_bytes_size])
                    del self.audio_accumulator[:self.frame_bytes_size]
                    
                    is_speech_frame = self._is_speech(frame_bytes)
                    self.ring_buffer.append((frame_bytes, is_speech_frame))
                    
                    # Contamos cuántos frames con voz hay en la ventana deslizante
                    speech_frames_count = sum(1 for _, is_speech in self.ring_buffer if is_speech)
                    
                    if not self.is_speaking:
                        # Transición Silencio -> Habla (Barge-in)
                        if speech_frames_count >= self.speech_threshold:
                            self.is_speaking = True
                            print(f"[{self.name}] >>> ¡Voz detectada! (Barge-in). Interrumpiendo reproducción...")
                            
                            # Disparamos la interrupción a nivel del Pipeline
                            if self.interruption_event:
                                self.interruption_event.set()
                                
                            # Notificamos de forma inmediata a los demás módulos del pipeline
                            await self.put_output(InterruptionMessage())
                            
                            # Iniciamos el buffer de habla.
                            # Para evitar cortar el inicio del habla, agregamos los frames que ya están en la ventana deslizante
                            self.speech_buffer.clear()
                            for fb, _ in self.ring_buffer:
                                self.speech_buffer.extend(fb)
                    else:
                        # Si ya se encuentra hablando, seguimos acumulando el frame actual
                        self.speech_buffer.extend(frame_bytes)
                        
                        # Transición Habla -> Silencio (Fin de frase)
                        silence_frames_count = self.window_size - speech_frames_count
                        if silence_frames_count >= self.silence_threshold:
                            self.is_speaking = False
                            print(f"[{self.name}] <<< Silencio prolongado detectado. Enviando audio para transcripción ({len(self.speech_buffer) / (self.sample_rate * 2):.2f}s).")
                            
                            # Enviamos el buffer consolidado hacia el STT
                            if len(self.speech_buffer) > 0:
                                await self.put_output(AudioMessage(
                                    data=bytes(self.speech_buffer),
                                    sample_rate=self.sample_rate
                                ))
                                self.speech_buffer.clear()
                                self.ring_buffer.clear()

