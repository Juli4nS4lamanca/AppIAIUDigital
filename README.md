# AppIAIUDigital: Agente de Voz Conversacional (Minimal Viable Agent)

Un Agente de Voz Conversacional asíncrono y de baja latencia construido en **Python 3.11+**, diseñado con una arquitectura orientada a pipelines (inspirada en Pipecat). Este proyecto forma parte de la materia de Ingeniería de Software / UI Digital.

El objetivo principal es establecer un flujo de audio bidireccional asíncrono, permitiendo la comunicación en tiempo real con modelos de inteligencia artificial mediante el uso estricto de la librería `asyncio`.

## 🚀 Arquitectura del Sistema

El sistema implementa una **Arquitectura de Pipeline de Streaming**, comunicando múltiples módulos completamente independientes a través de estructuras `asyncio.Queue`. Se ha evitado el uso de variables globales, encapsulando y manejando correctamente el ciclo de vida de cada tarea asíncrona.

### Módulos Principales

1. **MicrophoneSource** 🎙️
   - Captura continua de audio desde el micrófono en bloques o *chunks* (PCM a 16kHz).
   
2. **VADProcessor (Voice Activity Detection)** 🗣️
   - Implementa detección de actividad de voz (ej. `webrtcvad`) para segmentar el audio en ráfagas coherentes antes de enviarlas al motor STT.
   - Es el responsable primario de iniciar la lógica de interrupción (*Barge-In*) al detectar audio del usuario.

3. **STTProcessor (Speech-to-Text)** 📝
   - Procesa los segmentos de audio para transcribirlos a texto.
   - Expone una interfaz agnóstica preparada para integrarse con proveedores como OpenAI Whisper, Azure o Deepgram.

4. **LLMProcessor (Large Language Model)** 🧠
   - Invocación de modelos generativos en **modo streaming**.
   - Procesa y emite tokens a medida que se van generando en red para reducir significativamente la latencia percibida.

5. **TTSSpeaker (Text-to-Speech)** 🔊
   - Convierte el texto de respuesta nuevamente en audio, soportando la reproducción en *streaming* (fragmento a fragmento).

## ⚡ Características Clave

- **Concurrencia Estricta**: Construido 100% sobre `asyncio` para garantizar un alto rendimiento I/O sin bloqueos.
- **Baja Latencia**: El flujo mediante *chunks* y la respuesta en cascada reducen drásticamente los tiempos de espera entre la entrada del usuario y la respuesta del agente.
- **Barge-In (Lógica de Interrupción)**: El sistema es capaz de detectar cuando el usuario interrumpe al agente durante la fase de salida (playback). Automáticamente emite un evento que cancela de forma inmediata las tareas pendientes de síntesis/reproducción de TTS y el flujo en curso del LLM, reiniciando el ciclo natural.
- **Modularidad**: Arquitectura basada completamente en clases orientadas a objetos (`BaseModule`), promoviendo la fácil mantenibilidad e integración de distintos proveedores.

## 🛠️ Requisitos Técnicos

- **Python 3.11** o superior.
- Dependencias principales (ver `requirements.txt`):
  - `asyncio`
  - `sounddevice`
  - `numpy`
  - `openai`
  - `python-dotenv`
  - `webrtcvad`

## ⚙️ Instalación y Ejecución

1. Clona el repositorio e ingresa a la carpeta del proyecto.
2. Crea un entorno virtual e instala las dependencias:
   ```bash
   python -m venv venv
   # En Windows:
   venv\Scripts\activate
   # En macOS/Linux:
   source venv/bin/activate
   
   pip install -r requirements.txt
   ```
3. Ejecuta el pipeline principal (actualmente contiene una estructura de *mocks* para validación del ciclo de vida):
   ```bash
   python -m app.main
   ```

## 📂 Estructura del Código

```text
app/
├── __init__.py
├── main.py                # Punto de entrada; inicializa el pipeline
├── core/
│   ├── messages.py        # Clases de datos (AudioMessage, TextMessage, InterruptionMessage)
│   └── pipeline.py        # Orquestador de colas asyncio y manejo de eventos
└── modules/
    ├── base.py            # Clase abstracta BaseModule (gestión de Task y Queue)
    ├── microphone.py      # Captura de audio
    ├── vad.py             # Detección de actividad y Barge-in
    ├── stt.py             # Transcripción a texto
    ├── llm.py             # Invocación al modelo generativo
    └── tts.py             # Síntesis y reproducción de voz
```
