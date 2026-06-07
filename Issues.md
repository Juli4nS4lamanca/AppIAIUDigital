# Issues Pendientes del Proyecto: Conversational Voice Agent

Este documento detalla las tres tareas o *issues* prioritarias para llevar el Minimal Viable Agent (MVA) de una estructura con mocks a una implementación completamente funcional utilizando hardware y APIs en la nube de forma asíncrona.

---

## 🛠️ Issue 1: [Feature] Integrar captura de audio real con `sounddevice` en `MicrophoneSource`

### Descripción
Actualmente, el módulo `MicrophoneSource` (`app/modules/microphone.py`) simula la captura del micrófono enviando continuamente bloques llenos de bytes vacíos (`b'\x00'`). Es necesario conectarlo al hardware del dispositivo mediante la librería `sounddevice` para obtener audio real en tiempo real.

### Pasos para solucionarlo

1. **Configurar el Stream de Entrada Asíncrono**
   - Instanciar un `sd.InputStream` de `sounddevice` con los parámetros técnicos correctos: tasa de muestreo de 16000Hz (16kHz), 1 canal (mono), y formato de datos adecuado (16-bit PCM o float32).
   - Definir un tamaño de bloque (chunk) compatible con VAD (por ejemplo, 480 frames, lo que equivale a 30ms de audio a 16kHz).

2. **Implementar el Puente Asíncrono en el Callback**
   - Diseñar una función de *callback* no bloqueante para el `InputStream` que recoja los datos de audio capturados en tiempo real.
   - Utilizar el bucle de eventos asíncronos (`asyncio.get_running_loop()`) para invocar de forma segura y en el hilo principal (`call_soon_threadsafe`) el método que encola el `AudioMessage` en `output_queue`.

3. **Manejar el Ciclo de Vida y Liberación de Recursos**
   - Gestionar adecuadamente el encendido (`start()`) y apagado (`stop()`) del stream de grabación.
   - Capturar excepciones potenciales (como la ausencia de un micrófono conectado o errores de PortAudio) de forma limpia para evitar que el pipeline principal falle de manera abrupta.

---

## 🗣️ Issue 2: [Feature] Implementar Detección de Actividad de Voz (VAD) usando `webrtcvad`

### Descripción
El `VADProcessor` (`app/modules/vad.py`) cuenta con una lógica estática que siempre evalúa `is_speech = False`. Para poder operar en entornos reales, se debe incorporar la librería `webrtcvad` que permita segmentar la voz y enviar únicamente audio con contenido de voz a los motores de transcripción, además de detectar cuándo interrumpir al robot.

### Pasos para solucionarlo

1. **Inicializar y Validar Frames con `webrtcvad`**
   - Crear una instancia de `webrtcvad.Vad` y establecer su modo de agresividad (un entero entre 0 y 3, siendo 3 el más agresivo filtrando ruido).
   - Validar que cada frame binario recibido en el buffer de entrada de audio sea de exactamente 10, 20 o 30 milisegundos de duración (ej. 160, 320 o 480 muestras a 16kHz), ya que son los únicos tamaños permitidos por la librería C subyacente.

2. **Desarrollar Algoritmo de Ventana Deslizante (Debouncing)**
   - Implementar un búfer de estado histórico (ventana deslizante) que almacene los últimos *N* frames de audio.
   - Determinar que el usuario empezó a hablar si un porcentaje alto (ej. 80%) de los frames en la ventana es marcado como voz, y determinar que terminó de hablar si ocurre lo opuesto. Esto previene que silencios diminutos a mitad de una frase corten la transcripción anticipadamente.

3. **Orquestar el Barge-In y Encolar Segmentos**
   - Al detectar que la voz ha comenzado, activar inmediatamente el `interruption_event` global y emitir un `InterruptionMessage` para frenar la síntesis de voz actual del TTS y la generación del LLM.
   - Acumular todos los frames válidos del segmento de habla actual en un búfer en memoria y, en cuanto el algoritmo detecte el fin del habla, enviar dicho bloque consolidado al `STTProcessor`.

---

## 🧠 Issue 3: [Feature] Integrar APIs reales en modo Streaming (Whisper STT, OpenAI LLM y TTS)

### Descripción
Los tres módulos finales (`stt.py`, `llm.py`, `tts.py`) operan con respuestas predefinidas. Se requiere la integración de servicios cognitivos dinámicos y en streaming (preferiblemente OpenAI) para transcribir el audio, generar respuestas contextuales e interpretarlas en voz en tiempo real con mínima latencia.

### Pasos para solucionarlo

1. **Integrar Transcripción Asíncrona en `STTProcessor`**
   - Recibir el búfer acumulado de audio PCM crudo enviado por el VAD.
   - Utilizar el módulo estándar `wave` e `io.BytesIO` para empaquetar en memoria los datos binarios en un archivo formato `.wav` válido y realizar la llamada asíncrona a la API de OpenAI Whisper (`client.audio.transcriptions.create`) para obtener el texto transcrito.

2. **Consumir Tokens del LLM en Modo Streaming**
   - Configurar `LLMProcessor` para conectarse con la API de OpenAI de forma asíncrona usando `client.chat.completions.create` con `stream=True`.
   - Implementar un bucle asíncrono (`async for chunk in response`) que procese y envíe cada fragmento textual individual (`TextMessage`) hacia el TTS en cuanto sea generado, monitoreando continuamente si se ha establecido el `interruption_event` para frenar la iteración al instante.

3. **Sintetizar y Reproducir Streaming de Audio en `TTSSpeaker`**
   - Conectar el `TTSSpeaker` con un servicio de síntesis de voz que admita streaming o generar audio a partir de pequeños grupos de oraciones recibidas.
   - Enviar las tramas de audio resultantes a un `sd.OutputStream` activo de `sounddevice`. Asegurar que si llega un `InterruptionMessage` de VAD, la reproducción asíncrona se detenga de golpe llamando a `.cancel()` en la tarea del reproductor y vaciando cualquier búfer pendiente.
