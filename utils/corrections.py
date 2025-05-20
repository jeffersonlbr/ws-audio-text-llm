import re
import logging

# Configuração de logging
logger = logging.getLogger(__name__)

# Dicionário de correções ortográficas comuns
CORRECTIONS = {
    "feverê": "fevereiro",
    "causada de um plástico": "acusado de um plágio",
    "compionada": "copiamos nada",
    "contextualizatamente": "contextualize",
    "plagiato": "plagiado",
    "me favor": "me fale por favor",
    "sem avisar os ou partes copiar": "sem avisar, ele optou por copiar partes",
    "é de metil": "é de e-mail",
    "Eu você tinha": "Você tinha",
    "eu só responsável": "eu sou responsável",
    "o seu trabalho é usuário": "o usuário que submeteu o trabalho",
    "sumiu a responsabilidade": "assumiu a responsabilidade",
    "do regime de sequinar": "do regime disciplinar",
    "plático": "plágio",
    "ausado": "acusado",
    "compriamos": "copiamos",
    "copar": "copiar",
    "trebalho": "trabalho",
    "fasemos": "fizemos",
    "ressponsável": "responsável",
    "precisamo": "precisamos",
    "falasse": "falasse",
    "ninguem": "ninguém",
    "antecipademente": "antecipadamente",
    "obrigad": "obrigado",
    "entar": "entrar",
    "falza": "falsa",
    "aqela": "aquela",
    "voce": "você",
    "nao": "não"
}

def correct_text(text):
    """
    Aplica correções ortográficas ao texto transcrito
    """
    try:
        corrected = text
        
        # Aplicar correções do dicionário
        for error, correction in CORRECTIONS.items():
            corrected = re.sub(r'\b' + error + r'\b', correction, corrected, flags=re.IGNORECASE)
        
        # Correções adicionais baseadas em regras
        
        # Corrigir espaçamento após pontuação
        corrected = re.sub(r'([.!?])([A-ZÁÉÍÓÚÀÈÌÒÙÂÊÎÔÛÃÕÑÇ])', r'\1 \2', corrected)
        
        # Corrigir capitalização no início das frases
        sentences = re.split(r'([.!?]\s+)', corrected)
        result = ""
        for i in range(0, len(sentences), 2):
            sentence = sentences[i]
            if i < len(sentences) - 1:
                delimiter = sentences[i+1]
            else:
                delimiter = ""
            
            if sentence and not sentence[0].isupper() and len(sentence) > 1:
                sentence = sentence[0].upper() + sentence[1:]
            
            result += sentence + delimiter
        
        # Corrigir espaços múltiplos
        result = re.sub(r' +', ' ', result)
        
        # Corrigir espaços antes de pontuação
        result = re.sub(r' ([,.!?;:])', r'\1', result)
        
        # Garantir espaços após vírgulas e pontos
        result = re.sub(r'([,.])([^ \n])', r'\1 \2', result)
        
        logger.debug("Texto corrigido com sucesso")
        return result
    except Exception as e:
        logger.error(f"Erro na correção do texto: {e}")
        return text  # Em caso de erro, retorna o texto original

def add_corrections(new_corrections):
    """
    Adiciona novas correções ao dicionário
    """
    try:
        CORRECTIONS.update(new_corrections)
        logger.info(f"Adicionadas {len(new_corrections)} novas correções")
        return True
    except Exception as e:
        logger.error(f"Erro ao adicionar correções: {e}")
        return False