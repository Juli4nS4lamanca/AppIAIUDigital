import asyncio
import os
from dotenv import load_dotenv
from app.core.pipeline import Pipeline
from app.modules.microphone import MicrophoneSource
from app.modules.vad import VADProcessor
from app.modules.stt import STTProcessor
from app.modules.llm import LLMProcessor
from app.modules.tts import TTSSpeaker

# Cargamos el archivo de configuración .env
load_dotenv()

async def main():
    print("Inicializando Minimal Viable Agent (MVA) Pipeline...")
    
    # Validamos si existe la API Key configurada
    api_key = os.getenv("IA_API_KEY") or os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("[ADVERTENCIA] No se detectó ninguna clave de API en 'IA_API_KEY' o 'OPENAI_API_KEY'. Las llamadas fallarán.")
    
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
