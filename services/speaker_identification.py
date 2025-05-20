import re
import logging
import spacy
from collections import defaultdict, Counter

# Configuração de logging
logger = logging.getLogger(__name__)

# Carregar modelo spaCy para processamento de linguagem natural
try:
    nlp = spacy.load("pt_core_news_sm")
except:
    try:
        import os
        os.system("python -m spacy download pt_core_news_sm")
        nlp = spacy.load("pt_core_news_sm")
    except Exception as e:
        logger.error(f"Erro ao carregar modelo spaCy: {e}")
        nlp = None

# Lista de palavras que NÃO são nomes próprios válidos para speakers
INVALID_SPEAKER_NAMES = [
    "sou", "deus", "senhor", "senhora", "cara", "rapaz", "moça", "gente",
    "mulher", "homem", "bom", "boa", "aqui", "exemplo", "favor", "ok", 
    "obrigado", "certo", "então", "assim", "isso", "este", "esta", 
    "nada", "olá", "oi", "tchau", "coisa", "entrevistador", "entrevistado",
    "para", "speaker", "vai", "coloca", "como"
]

# Padrões para identificar auto-referências (quando alguém diz seu próprio nome)
SELF_IDENTIFICATION_PATTERNS = [
    r'[Ee]u (?:me chamo|sou(?: o| a)?|sou,)\.?\s+([A-Z][a-zA-ZÀ-ÿ]+)',
    r'[Mm]e (?:chamo|chamam|chamam de)\.?\s+([A-Z][a-zA-ZÀ-ÿ]+)',
    r'[Mm]eu nome (?:é|e|eh|seria)\.?\s+([A-Z][a-zA-ZÀ-ÿ]+)',
    r'[Aa]s pessoas me chamam de\.?\s+([A-Z][a-zA-ZÀ-ÿ]+)',
    r'[Pp]refiro\.?\s+([A-Z][a-zA-ZÀ-ÿ]+)',
    r'[Aa]qui (?:é|e|eh|quem fala é)\.?\s+(?:o|a)?\s*([A-Z][a-zA-ZÀ-ÿ]+)'
]

def extract_self_identifier(text):
    """
    Extrai o nome com que a pessoa se auto-identifica no texto
    """
    for pattern in SELF_IDENTIFICATION_PATTERNS:
        match = re.search(pattern, text)
        if match:
            name = match.group(1).strip()
            if name and len(name) >= 2 and name.lower() not in INVALID_SPEAKER_NAMES:
                return name
    return None

def preprocess_transcript(transcript):
    """
    Pré-processa a transcrição para identificar problemas e padrões
    """
    if not transcript or not hasattr(transcript, 'utterances'):
        return transcript, {}
    
    # Agrupar falas por falante
    speaker_texts = defaultdict(list)
    for utterance in transcript.utterances:
        speaker_texts[utterance.speaker].append(utterance.text)
    
    # Analisar cada falante para auto-identificação
    speaker_identities = {}
    speaker_index = 1
    
    # Primeiro, procurar por auto-identificações óbvias
    for speaker_tag, texts in speaker_texts.items():
        all_text = " ".join(texts)
        
        # Procurar quando a pessoa diz seu próprio nome
        name = extract_self_identifier(all_text)
        if name:
            speaker_identities[speaker_tag] = name
        else:
            # Se o próprio speaker_tag for um nome válido, manter
            if (speaker_tag.lower() not in INVALID_SPEAKER_NAMES and 
                not speaker_tag.startswith("SPEAKER") and 
                not re.match(r'^[A-Z]+$', speaker_tag)):
                speaker_identities[speaker_tag] = speaker_tag
    
    # Procurar por menções de terceiros
    for speaker_tag, texts in speaker_texts.items():
        all_text = " ".join(texts)
        
        # Procurar quando alguém menciona outro pelo nome
        for other_tag in speaker_texts.keys():
            if other_tag == speaker_tag:
                continue
                
            # Se o outro já foi identificado, verificar se é mencionado
            if other_tag in speaker_identities:
                other_name = speaker_identities[other_tag]
                if other_name.lower() in all_text.lower():
                    # O outro é mencionado por este falante
                    continue
    
    # Atribuir "Pessoa X" para falantes não identificados
    for speaker_tag in speaker_texts.keys():
        if speaker_tag not in speaker_identities:
            # Verificar se o speaker_tag é inválido
            if (speaker_tag.lower() in INVALID_SPEAKER_NAMES or 
                speaker_tag.startswith("SPEAKER") or 
                re.match(r'^[A-Z]+$', speaker_tag)):
                speaker_identities[speaker_tag] = f"Pessoa {speaker_index}"
                speaker_index += 1
            else:
                speaker_identities[speaker_tag] = speaker_tag
    
    return speaker_identities

def process_speakers_identification(transcript):
    """
    Versão completamente revisada para identificação de speakers
    """
    if not transcript or not hasattr(transcript, 'utterances'):
        logger.warning("Transcrição vazia ou sem utterances")
        return transcript, {}
    
    # Identificar padrões de speaker na transcrição
    speaker_identities = preprocess_transcript(transcript)
    
    # Segunda passada: caso específico para detectar nomes explicitamente mencionados
    all_text = " ".join([u.text for u in transcript.utterances])
    
    # Procurar referências ao "Jefferson" ou outros nomes específicos
    for speaker_tag, texts in defaultdict(list).items():
        for utterance in transcript.utterances:
            if utterance.speaker == speaker_tag:
                texts.append(utterance.text)
        
        combined_text = " ".join(texts)
        
        # Se alguém se identifica como um nome específico
        name = extract_self_identifier(combined_text)
        if name:
            speaker_identities[speaker_tag] = name
    
    # Criar uma versão aprimorada do objeto transcrição
    class EnhancedUtterance:
        def __init__(self, original_utterance, new_speaker):
            self.speaker = new_speaker
            self.text = original_utterance.text
            self.start = original_utterance.start if hasattr(original_utterance, 'start') else 0
            self.end = original_utterance.end if hasattr(original_utterance, 'end') else 0
    
    class EnhancedTranscript:
        def __init__(self, original_transcript, speaker_mapping):
            self.utterances = []
            self.text = original_transcript.text if hasattr(original_transcript, 'text') else ""
            self.audio_url = original_transcript.audio_url if hasattr(original_transcript, 'audio_url') else None
            self.json_response = original_transcript.json_response if hasattr(original_transcript, 'json_response') else None
            
            # Copiar os utterances com os novos nomes de speakers
            for utterance in original_transcript.utterances:
                new_speaker = speaker_mapping.get(utterance.speaker, f"Pessoa {utterance.speaker}")
                self.utterances.append(EnhancedUtterance(utterance, new_speaker))
    
    # Criar a versão aprimorada da transcrição
    enhanced_transcript = EnhancedTranscript(transcript, speaker_identities)
    
    logger.info(f"Speakers identificados: {speaker_identities}")
    return enhanced_transcript, speaker_identities

def fix_transcript_speakers(formatted_text):
    """
    Corrige problemas com identificadores de speakers em um texto já formatado
    """
    # Dividir o texto por linhas
    segments = formatted_text.split('\n\n')
    fixed_segments = []
    speaker_mapping = {}
    person_counter = 1
    
    # Primeira passada: identificar nomes inválidos de speakers
    for segment in segments:
        if ':' in segment:
            parts = segment.split(':', 1)
            speaker = parts[0].strip()
            
            # Verificar se é um identificador inválido
            if (speaker.lower() in INVALID_SPEAKER_NAMES or 
                re.match(r'^[A-Z]+$', speaker)):
                if speaker not in speaker_mapping:
                    speaker_mapping[speaker] = f"Pessoa {person_counter}"
                    person_counter += 1
    
    # Segunda passada: procurar auto-identificações
    for i, segment in enumerate(segments):
        if ':' in segment:
            parts = segment.split(':', 1)
            speaker = parts[0].strip()
            text = parts[1].strip()
            
            # Verificar auto-identificação
            name = extract_self_identifier(text)
            if name:
                # Atualizar mapeamento para todos os segments deste speaker
                old_name = speaker_mapping.get(speaker, speaker)
                for s, mapped_name in speaker_mapping.items():
                    if mapped_name == old_name:
                        speaker_mapping[s] = name
    
    # Terceira passada: aplicar correções
    for segment in segments:
        if ':' in segment:
            parts = segment.split(':', 1)
            speaker = parts[0].strip()
            text = parts[1].strip()
            
            if speaker in speaker_mapping:
                fixed_segments.append(f"{speaker_mapping[speaker]}: {text}")
            else:
                fixed_segments.append(segment)
        else:
            fixed_segments.append(segment)
    
    return '\n\n'.join(fixed_segments)