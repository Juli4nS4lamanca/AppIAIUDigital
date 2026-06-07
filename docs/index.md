# Bitácora de Desarrollo: Journey de Software del Agente de Voz

Este documento detalla la trayectoria técnica, decisiones de diseño y reflexiones de arquitectura tomadas durante el desarrollo del Agente de Voz Conversacional asíncrono (MVA) de baja latencia en Python 3.11+, desarrollado en colaboración con el agente de IA **Antigravity**.

---

## 🎯 Sección 1: La Bala Trazadora (Tracer Bullet) y el Enrutamiento de las Skills

### El Árbol de Diseño y /grill-me
Antes de escribir la primera línea de código, la ejecución y el desglose de los requerimientos a través de un riguroso análisis de diseño (equivalente a la skill `/grill-me`) refinaron significativamente nuestras asunciones iniciales sobre el problema. 

Originalmente, asumíamos que el flujo de procesamiento de voz podía estructurarse de manera secuencial y lineal directa en un único bucle. Sin embargo, el análisis del árbol de diseño reveló que la combinación de **baja latencia** y la necesidad de **Barge-in (interrupción inmediata)** requería desacoplar totalmente las fases. Esto nos obligó a plantear:
1. Una comunicación basada estrictamente en colas asíncronas (`asyncio.Queue`) para procesar el streaming en cascada sin bloqueos.
2. Un evento de interrupción compartido y un mensaje fuera de banda (`InterruptionMessage`) para poder saltarse la cola e indicar a los consumidores activos que debían cancelar sus tareas inmediatamente.

### La Analogía de la Bala Trazadora (Tracer Bullet)
En lugar de construir el sistema completo con mocks genéricos y luego intentar integrar el hardware, aplicamos el concepto de **Bala Trazadora (Tracer Bullet)**: tirar una línea vertical de código real a través de todo el sistema para validar la arquitectura lo antes posible.

Identificamos que el punto más arriesgado y de mayor incertidumbre era la **captura de audio en tiempo real desde el micrófono y su puente de hilos hacia el loop de eventos asíncronos**. Si el callback de hardware de PortAudio bloqueaba el event loop de `asyncio`, todo el pipeline fallaría por latencia.

Forzamos a resolver este problema primero:
* Implementamos el módulo `MicrophoneSource` utilizando `sounddevice.RawInputStream`.
* Construimos el puente thread-safe mediante `asyncio.run_coroutine_threadsafe()` desde el callback de C hacia la cola asíncrona.
* Al validar que los bloques de audio de 30ms llegaban de manera fluida y sin bloqueos al primer receptor, obtuvimos feedback temprano y la certeza absoluta de que el cimiento asíncrono del pipeline era robusto antes de integrar APIs en la nube.

---

## 🧠 Sección 2: Anatomía de la Complejidad (Módulos Profundos vs. Superficiales)

### Módulos Profundos (Deep Modules)
Un buen diseño arquitectónico favorece los módulos "profundos": aquellos que ocultan una enorme complejidad detrás de una interfaz extremadamente minimalista y sencilla. En nuestro diseño, destacan dos componentes:

#### 1. `TTSSpeaker` ([app/modules/tts.py](file:///c:/Users/JULIAN/Documents/Universidad/Ingenieria%20de%20Software/AppIAIUDigital/app/modules/tts.py))
Su interfaz externa es ridículamente simple: solo hereda de `BaseModule` y consume `TextMessage` o `InterruptionMessage` de su cola. Sin embargo, por dentro oculta:
* El consumo asíncrono del servicio de Microsoft Edge TTS.
* La segmentación inteligente de oraciones en tiempo real para reducir la latencia de respuesta (TTFA).
* El manejo de archivos temporales únicos para evitar bloqueos del sistema de archivos.
* El mapeo por `ctypes` de la API nativa de Windows `winmm.dll` (MCI) para reproducir audio MP3 de forma no bloqueante y asíncrona.
* El monitoreo constante del estado de reproducción en segundo plano a nivel de sistema operativo para poder ejecutar una interrupción inmediata.

```python
# Fragmento del corazón de reproducción nativa oculta en TTSSpeaker
open_command = f'open "{temp_file_path}" type mpegvideo alias {alias}'
self._mci_send(open_command)
self._mci_send(f'play {alias}')

while True:
    buf = ctypes.create_unicode_buffer(128)
    self.winmm.mciSendStringW(f"status {alias} mode", buf, 127, 0)
    status = buf.value.strip()
    if status != "playing":
        break
    if self.interruption_event and self.interruption_event.is_set():
        self._mci_send(f'stop {alias}')
        break
    await asyncio.sleep(0.05)
```

#### 2. `VADProcessor` ([app/modules/vad.py](file:///c:/Users/JULIAN/Documents/Universidad/Ingenieria%20de%20Software/AppIAIUDigital/app/modules/vad.py))
Determina si hay habla o silencio. A nivel externo, solo recibe audio y emite mensajes. Internamente oculta:
* Re-ensamblado de bloques de audio de tamaño variable en tramas exactas de 30ms.
* Detección por el algoritmo C++ de `webrtcvad`.
* Un fallback matemático nativo de raíz cuadrática media (RMS) para cuando no hay compilador de C++ en la máquina de ejecución.
* Un algoritmo de debouncing con una ventana deslizante de 300ms a través de un buffer circular (`collections.deque`) para suavizar el estado de voz del usuario.

```python
# Fallback RMS matemático e independiente programado nativamente en el VAD
count = len(frame_bytes) // 2
shorts = struct.unpack(f"{count}h", frame_bytes)
sum_squares = sum(s * s for s in shorts)
rms = (sum_squares / count) ** 0.5
return rms > 800
```

### Módulos Superficiales (Shallow Modules) y Refactorización de la IA
Durante las primeras iteraciones, el agente de IA intentó atomizar en exceso el sistema. Propuso dividir el TTS en varios sub-módulos y scripts superficiales: un `MCIPlayer` independiente, un `TTSFileHandler` y un `SentenceSegmenter`. Esto provocaba una explosión de archivos pequeños y vacíos que requerían complejas llamadas y dependencias entre sí (módulos superficiales).

La directriz humana del desarrollador fue contundente: **unificar la funcionalidad relacionada dentro de abstracciones cohesivas**. Al consolidar estas tareas bajo la interfaz del `TTSSpeaker`, ensanchamos su profundidad, logrando que el módulo sea autocontenido, fácil de entender y con menos acoplamiento externo.

### Fuga de Información (Information Leakage)
Para evitar que los detalles internos de red o de hardware se "fugaran" hacia otros componentes, definimos un contrato estricto a través de clases de datos en [messages.py](file:///c:/Users/JULIAN/Documents/Universidad/Ingenieria%20de%20Software/AppIAIUDigital/app/core/messages.py):
* `AudioMessage`
* `TextMessage`
* `InterruptionMessage`

El orquestador del pipeline y los módulos intermedios no conocen los detalles internos sobre tramas de PortAudio, formatos MP3, ni APIs REST de Groq. El ocultamiento de información garantizó que si se cambia el motor de reproducción o de transcripción, las firmas de las interfaces y la UI permanezcan intactas.

---

## ⚖️ Sección 3: El Veredicto Retrospectivo de los Sub-Agentes

### El Debate Arquitectónico y la Velocidad de Desarrollo
En retrospectiva, el debate arquitectónico (al estilo de la skill `/improve-codebase-architecture`) donde se contrastaban paradigmas de enrutamiento (como un Event-Broker centralizado vs. Pipelines Asíncronos Desacoplados) fue determinante. 

Aunque resolver este debate al inicio consumió tiempo de análisis, **multiplicó la velocidad de desarrollo en la segunda mitad del proyecto**. Al elegir un enfoque de Pipeline Desacoplado basado en `BaseModule` con colas y un canal de interrupción reactivo, pudimos avanzar en paralelo implementando cada módulo sin temor a romper el resto del sistema.

### Elasticidad frente al Cambio (Buen Gusto Arquitectónico)
El verdadero veredicto del "buen gusto" de esta arquitectura se demostró cuando el entorno de ejecución (Python 3.14 en Windows) arrojó errores críticos de compilación de C++ con `pygame` y `webrtcvad`.

Gracias al diseño elástico y al bajo acoplamiento:
* **Cero Amplificación del Cambio (Change Amplification):** Pudimos remover `pygame`, reescribir por completo la reproducción en el módulo `tts.py` para usar `winmm.dll` nativo, e implementar el fallback RMS en `vad.py` **sin modificar una sola línea** de `main.py`, `pipeline.py`, `stt.py` ni `llm.py`. 
* La interfaz demostró ser sumamente elástica frente al cambio drástico de dependencias y de infraestructura de bajo nivel.
