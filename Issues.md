# Registro de Issues: Conversational Voice Agent

Este documento detalla el estado e historial de resolución de las tareas prioritarias para el Minimal Viable Agent (MVA). Todos los issues se encuentran actualmente **cerrados y completados**.

---

## 🛠️ Issue 1: [Feature] Integrar captura de audio real con `sounddevice` en `MicrophoneSource`
**Estado: Completado ✅ (Cerrado)**

### Descripción
Reemplazar la simulación de captura de audio (bytes vacíos `b'\x00'`) por hardware real del dispositivo a través de `sounddevice` de forma asíncrona.

### Pasos Completados
- [x] **1. Configurar el Stream de Entrada Asíncrono**
  - Configurado `sd.RawInputStream` con muestreo a 16kHz, mono, PCM de 16 bits y bloque de 30ms (480 frames) compatible con VAD.
- [x] **2. Implementar el Puente Asíncrono en el Callback**
  - Callback no bloqueante en hilo independiente que traslada los datos al event loop principal de forma segura mediante `asyncio.run_coroutine_threadsafe()`.
- [x] **3. Manejar el Ciclo de Vida y Liberación de Recursos**
  - Implementado control robusto con gestores de contexto y try-finally para cerrar y liberar el dispositivo de grabación al apagar el pipeline.

---

## 🗣️ Issue 2: [Feature] Implementar Detección de Actividad de Voz (VAD) usando `webrtcvad`
**Estado: Completado ✅ (Cerrado)**

### Descripción
Implementar segmentación inteligente de audio y control de interrupción de playback (*Barge-in*) utilizando detección de actividad de voz.

### Pasos Completados
- [x] **1. Inicializar y Validar Frames con `webrtcvad` (con Fallback RMS)**
  - Carga dinámica de `webrtcvad`. Se integró un fallback matemático de raíz cuadrática media (RMS) para permitir la detección de voz nativa sin requerir herramientas de compilación C++ en Windows.
- [x] **2. Desarrollar Algoritmo de Ventana Deslizante (Debouncing)**
  - Implementación de un búfer circular de 300ms de histórico (`collections.deque`) para prevenir falsos positivos y cortes abruptos durante pequeñas pausas al hablar.
- [x] **3. Orquestar el Barge-In y Encolar Segmentos**
  - Envío automático de `InterruptionMessage` y activación de `interruption_event` para interrumpir al robot en cuanto empieza el habla. El bloque completo se consolida para su posterior envío al STT.

---

## 🧠 Issue 3: [Feature] Integrar APIs reales en modo Streaming (Whisper STT, OpenAI/Groq LLM y TTS)
**Estado: Completado ✅ (Cerrado)**

### Descripción
Conectar las interfaces semánticas a APIs reales en streaming. Optimizado para usar **Groq** (para STT y LLM) y **Edge TTS** (síntesis de voz libre y gratuita).

### Pasos Completados
- [x] **1. Integrar Transcripción Asíncrona en `STTProcessor`**
  - Integrada la API de Whisper (ej. `whisper-large-v3` en Groq) empaquetando el audio dinámicamente como archivo WAV virtual en memoria (`io.BytesIO`) evitando I/O de disco.
- [x] **2. Consumir Tokens del LLM en Modo Streaming**
  - Conexión al streaming de chat de Groq (`llama-3.1-8b-instant`) evaluando en tiempo real si el usuario interrumpe la respuesta para cancelar la generación al instante.
- [x] **3. Sintetizar y Reproducir Streaming de Audio en `TTSSpeaker`**
  - Migración a `edge-tts` (Microsoft Edge) y reproducción nativa en segundo plano mediante `winmm.dll` (MCI de Windows) usando `ctypes`. Soporta cancelación inmediata en hardware al recibir la señal de Barge-in y elimina dependencias de compilación como Pygame.
