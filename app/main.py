import asyncio
from app.core.pipeline import Pipeline
from app.modules.microphone import MicrophoneSource
from app.modules.vad import VADProcessor
from app.modules.stt import STTProcessor
from app.modules.llm import LLMProcessor
from app.modules.tts import TTSSpeaker

async def main():
    print("Inicializando Minimal Viable Agent (MVA) Pipeline...")
    
    # 1. Crear el pipeline principal
    pipeline = Pipeline()
    
    # 2. Instanciar los módulos
    mic = MicrophoneSource()
    vad = VADProcessor()
    stt = STTProcessor()
    llm = LLMProcessor()
    tts = TTSSpeaker()
    
    # 3. Añadirlos en orden estricto
    pipeline.add_module(mic)
    pipeline.add_module(vad)
    pipeline.add_module(stt)
    pipeline.add_module(llm)
    pipeline.add_module(tts)
    
    # 4. Iniciar el ciclo principal
    try:
        await pipeline.run_forever()
    except KeyboardInterrupt:
        print("\nCerrando pipeline de forma segura...")
        await pipeline.stop()

if __name__ == "__main__":
    # Aseguramos que se ejecuta en el loop de asyncio usando Python 3.11+
    asyncio.run(main())
