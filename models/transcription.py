import os
import logging
from models.database import get_db_connection

# Configuração de logging
logger = logging.getLogger(__name__)

class Transcription:
    """
    Classe para representar uma transcrição
    """
    def __init__(self, id=None, filename=None, project=None, description=None, 
                 transcription=None, created_at=None, folder_path=None, 
                 file_size=None, speakers_count=None):
        self.id = id
        self.filename = filename
        self.project = project
        self.description = description
        self.transcription = transcription
        self.created_at = created_at
        self.folder_path = folder_path
        self.file_size = file_size
        self.speakers_count = speakers_count
    
    @classmethod
    def from_dict(cls, data):
        """
        Cria uma instância a partir de um dicionário
        """
        return cls(**data)
    
    @classmethod
    def from_id(cls, trans_id):
        """
        Carrega uma transcrição do banco de dados pelo ID
        """
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM transcriptions WHERE id = ?", (trans_id,))
                data = cursor.fetchone()
                
                if data:
                    return cls.from_dict(dict(data))
                return None
        except Exception as e:
            logger.error(f"Erro ao buscar transcrição: {e}")
            return None
    
    def save(self):
        """
        Salva a transcrição no banco de dados
        """
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                
                if self.id:
                    # Atualizar existente
                    cursor.execute(
                        """UPDATE transcriptions SET
                           filename = ?,
                           project = ?,
                           description = ?,
                           transcription = ?,
                           folder_path = ?,
                           file_size = ?,
                           speakers_count = ?
                           WHERE id = ?""",
                        (self.filename, self.project, self.description, 
                         self.transcription, self.folder_path, self.file_size,
                         self.speakers_count, self.id)
                    )
                else:
                    # Inserir novo
                    cursor.execute(
                        """INSERT INTO transcriptions 
                           (id, filename, project, description, transcription, 
                            created_at, folder_path, file_size, speakers_count) 
                           VALUES (?, ?, ?, ?, ?, datetime('now'), ?, ?, ?)""",
                        (self.id, self.filename, self.project, self.description,
                         self.transcription, self.folder_path, self.file_size,
                         self.speakers_count)
                    )
                
                conn.commit()
                logger.info(f"Transcrição {self.id} salva com sucesso")
                return True
        except Exception as e:
            logger.error(f"Erro ao salvar transcrição: {e}")
            return False
    
    def delete(self):
        """
        Exclui a transcrição do banco de dados e seus arquivos
        """
        try:
            # Remover arquivos
            if self.folder_path and os.path.exists(self.folder_path):
                for file in os.listdir(self.folder_path):
                    file_path = os.path.join(self.folder_path, file)
                    if os.path.isfile(file_path):
                        os.remove(file_path)
                
                # Remover a pasta
                os.rmdir(self.folder_path)
            
            # Remover do banco de dados
            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM transcriptions WHERE id = ?", (self.id,))
                conn.commit()
                
            logger.info(f"Transcrição {self.id} excluída com sucesso")
            return True
        except Exception as e:
            logger.error(f"Erro ao excluir transcrição: {e}")
            return False
    
    def to_dict(self):
        """
        Converte a instância para um dicionário
        """
        return {
            'id': self.id,
            'filename': self.filename,
            'project': self.project,
            'description': self.description,
            'transcription': self.transcription,
            'created_at': self.created_at,
            'folder_path': self.folder_path,
            'file_size': self.file_size,
            'speakers_count': self.speakers_count
        }
    
    def get_speakers(self):
        """
        Obtém a lista de speakers mencionados na transcrição
        """
        if not self.transcription:
            return []
            
        speakers = set()
        for line in self.transcription.split('\n\n'):
            if ':' in line:
                speaker = line.split(':', 1)[0].strip()
                speakers.add(speaker)
        
        return list(speakers)