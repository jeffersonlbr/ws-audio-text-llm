import os
import logging
from pydub import AudioSegment

# Configuração de logging
logger = logging.getLogger(__name__)

def convert_audio(file_path, output_format="wav"):
    """
    Converte o arquivo para o formato desejado
    """
    try:
        logger.info(f"Convertendo áudio para {output_format.upper()}: {file_path}")
        audio = AudioSegment.from_file(file_path)
        
        # Determinar o caminho de saída
        output_path = f"{file_path}.{output_format}"
        
        # Exportar o arquivo
        audio.export(output_path, format=output_format)
        
        logger.info(f"Áudio convertido: {output_path}")
        return output_path
    except Exception as e:
        logger.error(f"Erro ao converter áudio: {e}")
        return file_path

def split_audio(file_path, segment_length=30):
    """
    Divide o áudio em segmentos menores para processamento
    """
    try:
        logger.info(f"Dividindo áudio em segmentos de {segment_length} segundos")
        audio = AudioSegment.from_file(file_path)
        
        # Criar diretório para segmentos
        segment_dir = os.path.join(os.path.dirname(file_path), "segments")
        os.makedirs(segment_dir, exist_ok=True)
        
        segment_paths = []
        segment_length_ms = segment_length * 1000  # Converter para milissegundos
        
        for i, start in enumerate(range(0, len(audio), segment_length_ms)):
            end = min(start + segment_length_ms, len(audio))
            segment = audio[start:end]
            
            segment_path = os.path.join(segment_dir, f"segment_{i}.wav")
            segment.export(segment_path, format="wav")
            segment_paths.append(segment_path)
            
        logger.info(f"Áudio dividido em {len(segment_paths)} segmentos")
        return segment_paths
    except Exception as e:
        logger.error(f"Erro ao dividir áudio: {e}")
        return [file_path]  # Retorna o arquivo original em caso de erro

def get_audio_info(file_path):
    """
    Obtém informações sobre o arquivo de áudio
    """
    try:
        audio = AudioSegment.from_file(file_path)
        
        # Calcular tamanho do arquivo em MB
        file_size_bytes = os.path.getsize(file_path)
        file_size_mb = file_size_bytes / (1024 * 1024)
        
        # Calcular duração em segundos
        duration_seconds = len(audio) / 1000
        
        # Calcular minutos e segundos
        minutes = int(duration_seconds // 60)
        seconds = int(duration_seconds % 60)
        
        return {
            'file_size_bytes': file_size_bytes,
            'file_size_mb': round(file_size_mb, 2),
            'duration_seconds': duration_seconds,
            'duration_formatted': f"{minutes}m {seconds}s",
            'channels': audio.channels,
            'sample_width': audio.sample_width,
            'frame_rate': audio.frame_rate
        }
    except Exception as e:
        logger.error(f"Erro ao obter informações do áudio: {e}")
        return {
            'file_size_bytes': os.path.getsize(file_path),
            'file_size_mb': round(os.path.getsize(file_path) / (1024 * 1024), 2),
            'duration_seconds': 0,
            'duration_formatted': "Desconhecido",
            'channels': 0,
            'sample_width': 0,
            'frame_rate': 0
        }

def cleanup_segments(directory):
    """
    Limpa os arquivos temporários de segmentos
    """
    try:
        segment_dir = os.path.join(directory, "segments")
        if os.path.exists(segment_dir):
            for file in os.listdir(segment_dir):
                if file.startswith("segment_") and file.endswith(".wav"):
                    os.remove(os.path.join(segment_dir, file))
            logger.info(f"Segmentos temporários removidos de {segment_dir}")
            return True
        return False
    except Exception as e:
        logger.error(f"Erro ao limpar segmentos: {e}")
        return False