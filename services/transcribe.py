import os
import time
import logging
from dotenv import load_dotenv
import assemblyai as aai
from utils.corrections import correct_text
from services.speaker_identification import process_speakers_identification

# Carregar variáveis de ambiente do arquivo .env
load_dotenv()

# Configuração de logging
logger = logging.getLogger(__name__)

# Configuração da API AssemblyAI
api_key = os.getenv("ASSEMBLYAI_API_KEY")
if not api_key:
    logger.error("ASSEMBLYAI_API_KEY não encontrada no ambiente. Verifique o arquivo .env")
    raise ValueError("ASSEMBLYAI_API_KEY não configurada")

aai.settings.api_key = api_key

def transcribe_with_assemblyai(file_path, options=None):
    """
    Transcreve o áudio usando a API da AssemblyAI (versão atualizada)
    """
    try:
        # Configurar as opções de transcrição
        config = aai.TranscriptionConfig(
            speaker_labels=True,         # Ativar identificação de speakers
            # language_code="pt",          # Definir idioma como português
            punctuate=True,              # Adicionar pontuação automática
            format_text=True,            # Formatar o texto automaticamente
            # speech_recognizer removido pois não existe mais na API atual
            language_detection=True      # Usar detecção automática de idioma
        )
        
        # Aplicar opções avançadas se fornecidas
        if options:
            if 'audio_start_from' in options and options['audio_start_from'] > 0:
                config.audio_start_from = options['audio_start_from']
                logger.info(f"Iniciando transcrição a partir de {options['audio_start_from']} segundos")
                
            if 'audio_end_at' in options and options['audio_end_at'] > 0:
                config.audio_end_at = options['audio_end_at']
                logger.info(f"Terminando transcrição em {options['audio_end_at']} segundos")
                
            if 'word_boost' in options and options['word_boost']:
                config.word_boost = options['word_boost']
                logger.info(f"Palavras enfatizadas: {options['word_boost']}")
                
            if 'webhook_url' in options and options['webhook_url']:
                config.webhook_url = options['webhook_url']
                logger.info(f"Webhook configurado: {options['webhook_url']}")
        
        # Criar o objeto transcriber
        transcriber = aai.Transcriber()
        
        logger.info(f"Iniciando transcrição com AssemblyAI: {file_path}")
        start_time = time.time()
        
        # Verificar se o arquivo existe
        if not os.path.exists(file_path):
            logger.error(f"Arquivo não encontrado: {file_path}")
            return None
        
        # Iniciar a transcrição (método atualizado)
        transcript = transcriber.transcribe(
            file_path,
            config=config
        )
        
        if transcript.status == aai.TranscriptStatus.error:
            logger.error(f"Erro na transcrição: {transcript.error}")
            return None
        
        elapsed_time = time.time() - start_time
        logger.info(f"Transcrição concluída em {elapsed_time:.2f} segundos")
        
        # Processar identificação de speakers
        enhanced_transcript, speaker_names = process_speakers_identification(transcript)
        logger.info(f"Identificação de speakers concluída: {speaker_names}")
        
        return enhanced_transcript
        
    except Exception as e:
        logger.error(f"Erro na transcrição com AssemblyAI: {e}")
        return None

def format_assemblyai_transcript(transcript):
    """
    Formata a saída da API AssemblyAI para o formato esperado pelo sistema
    com correção robusta de identificação de speakers
    """
    from services.speaker_identification import fix_transcript_speakers
    
    if not transcript or not hasattr(transcript, 'utterances'):
        return {
            'text': "Erro: Transcrição falhou ou não contém dados de speakers.",
            'speakers_count': 0,
            'speakers': []
        }
    
    # Processar cada utterance para criar o formato esperado
    formatted_lines = []
    speakers = set()
    
    for utterance in transcript.utterances:
        speaker = utterance.speaker
        speakers.add(speaker)
        text = correct_text(utterance.text) 
        formatted_lines.append(f"{speaker}: {text}")
    
    # Juntar em texto formatado
    formatted_text = "\n\n".join(formatted_lines)
    
    # Aplicar correção avançada de identificação de speakers
    fixed_text = fix_transcript_speakers(formatted_text)
    
    # Recalcular speakers após correção
    corrected_speakers = set()
    for line in fixed_text.split('\n\n'):
        if ':' in line:
            speaker = line.split(':', 1)[0].strip()
            corrected_speakers.add(speaker)
    
    return {
        'text': fixed_text,
        'speakers_count': len(corrected_speakers),
        'speakers': list(corrected_speakers)
    }

def transcribe_audio_file(file_path, split=True, segment_length=30, transcription_options=None):
    """
    Versão otimizada da função para processamento de áudio
    """
    try:
        # Limitar a criação de arquivos temporários e reduzir as operações de I/O
        # Log com timestamp para medir o tempo
        start_time = time.time()
        logger.info(f"Iniciando transcrição: {file_path}")
        
        # Transcrever com AssemblyAI - configurando opções mais simples quando possível
        config_options = {}
        if transcription_options:
            # Copiar apenas as opções necessárias para reduzir overhead
            if 'audio_start_from' in transcription_options and transcription_options['audio_start_from'] > 0:
                config_options['audio_start_from'] = transcription_options['audio_start_from']
            if 'audio_end_at' in transcription_options and transcription_options['audio_end_at'] > 0:
                config_options['audio_end_at'] = transcription_options['audio_end_at']
        
        # Usar diretamente a API, pulando validações extras quando possível
        transcript = transcribe_with_assemblyai(file_path, config_options)
        
        if not transcript:
            logger.error("A transcrição falhou.")
            return {
                'text': "Erro na transcrição do áudio.",
                'speakers_count': 0,
                'speakers': []
            }
        
        # Medir e logar o tempo da transcrição
        transcription_time = time.time() - start_time
        logger.info(f"Transcrição básica concluída em {transcription_time:.2f} segundos")
        
        # Formatar a saída de forma mais eficiente
        result = format_assemblyai_transcript(transcript)
        
        # Medir e logar o tempo total
        total_time = time.time() - start_time
        logger.info(f"Processamento completo em {total_time:.2f} segundos")
        
        return result
        
    except Exception as e:
        logger.error(f"Erro no processamento de áudio: {e}")
        return {
            'text': f"Erro no processamento de áudio: {str(e)}",
            'speakers_count': 0,
            'speakers': []
        }

def process_transcription_text(text):
    """
    Função mantida para compatibilidade
    Como o AssemblyAI já faz a diarização, esta função
    é simplificada para apenas retornar o texto formatado
    """
    try:
        # Dividir o texto em linhas
        lines = text.split('\n\n')
        speakers = set()
        
        for line in lines:
            if ':' in line:
                speaker = line.split(':', 1)[0].strip()
                speakers.add(speaker)
        
        return {
            'text': text,
            'speakers_count': len(speakers),
            'speakers': list(speakers)
        }
    except Exception as e:
        logger.error(f"Erro ao processar texto: {e}")
        return {
            'text': text,
            'speakers_count': 0,
            'speakers': []
        }