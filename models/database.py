import os
import sqlite3
import logging
from datetime import datetime

# Configuração de logging
logger = logging.getLogger(__name__)

# Caminho do banco de dados
DB_FILE = "transcriptions.db"

def get_db_connection():
    """Cria e retorna uma conexão com o banco de dados"""
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row  # Para acessar colunas pelo nome
    return conn

def init_db():
    """Inicializa o banco de dados com as tabelas necessárias"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        # Verificar se a tabela já existe
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='transcriptions'")
        table_exists = cursor.fetchone() is not None
        
        if not table_exists:
            # Criar a tabela do zero se não existir
            cursor.execute('''CREATE TABLE transcriptions (
                                id TEXT PRIMARY KEY,
                                filename TEXT,
                                project TEXT,
                                description TEXT,
                                transcription TEXT,
                                created_at TIMESTAMP,
                                folder_path TEXT,
                                file_size INTEGER,
                                speakers_count INTEGER,
                                audio_duration INTEGER,
                                estimated_cost REAL,
                                audio_path TEXT)''')
        else:
            # Verificar colunas existentes
            cursor.execute("PRAGMA table_info(transcriptions)")
            columns = [column[1] for column in cursor.fetchall()]
            
            # Adicionar colunas que não existem
            if 'created_at' not in columns:
                cursor.execute("ALTER TABLE transcriptions ADD COLUMN created_at TIMESTAMP")
            
            if 'folder_path' not in columns:
                cursor.execute("ALTER TABLE transcriptions ADD COLUMN folder_path TEXT")
                
            if 'file_size' not in columns:
                cursor.execute("ALTER TABLE transcriptions ADD COLUMN file_size INTEGER")
                
            if 'speakers_count' not in columns:
                cursor.execute("ALTER TABLE transcriptions ADD COLUMN speakers_count INTEGER")
                
            if 'audio_duration' not in columns:
                cursor.execute("ALTER TABLE transcriptions ADD COLUMN audio_duration INTEGER")
                
            if 'estimated_cost' not in columns:
                cursor.execute("ALTER TABLE transcriptions ADD COLUMN estimated_cost REAL")
                
            if 'audio_path' not in columns:
                cursor.execute("ALTER TABLE transcriptions ADD COLUMN audio_path TEXT")
        
        conn.commit()
        logger.info("Banco de dados inicializado com sucesso")

def save_transcription(trans_id, filename, project_name, description, transcription, folder_path, file_size, speakers_count=0, audio_duration=0, estimated_cost=0.0):
    """Salva uma transcrição no banco de dados"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            cursor.execute(
                """INSERT INTO transcriptions 
                   (id, filename, project, description, transcription, created_at, folder_path, file_size, speakers_count, audio_duration, estimated_cost) 
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (trans_id, filename, project_name, description, transcription, current_time, folder_path, file_size, speakers_count, audio_duration, estimated_cost)
            )
            conn.commit()
            logger.info(f"Transcrição {trans_id} salva com sucesso")
            return True
    except Exception as e:
        logger.error(f"Erro ao salvar transcrição: {e}")
        return False

def update_transcription(trans_id, transcription=None, folder_path=None, speakers_count=None, audio_duration=None, estimated_cost=None):
    """Atualiza uma transcrição existente"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            updates = []
            params = []
            
            if transcription is not None:
                updates.append("transcription = ?")
                params.append(transcription)
            
            if folder_path is not None:
                updates.append("folder_path = ?")
                params.append(folder_path)
                
            if speakers_count is not None:
                updates.append("speakers_count = ?")
                params.append(speakers_count)
                
            if audio_duration is not None:
                updates.append("audio_duration = ?")
                params.append(audio_duration)
                
            if estimated_cost is not None:
                updates.append("estimated_cost = ?")
                params.append(estimated_cost)
                
            if not updates:
                logger.warning("Nenhum campo para atualizar")
                return False
                
            params.append(trans_id)
            cursor.execute(
                f"UPDATE transcriptions SET {', '.join(updates)} WHERE id = ?",
                params
            )
            conn.commit()
            logger.info(f"Transcrição {trans_id} atualizada com sucesso")
            return True
    except Exception as e:
        logger.error(f"Erro ao atualizar transcrição: {e}")
        return False

def get_transcription(trans_id):
    """Obtém uma transcrição pelo ID"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM transcriptions WHERE id = ?", (trans_id,))
            result = cursor.fetchone()
            
            if result:
                return dict(result)  # Converter para dicionário
            return None
    except Exception as e:
        logger.error(f"Erro ao buscar transcrição: {e}")
        return None

def get_all_transcriptions(start_date=None, end_date=None, sort_by=None, sort_order=None):
    """Obtém todas as transcrições com filtro opcional por data e ordenação"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            query = "SELECT * FROM transcriptions"
            params = []
            
            if start_date or end_date:
                query += " WHERE "
                
                if start_date:
                    query += "created_at >= ?"
                    params.append(start_date)
                    
                if start_date and end_date:
                    query += " AND "
                    
                if end_date:
                    query += "created_at <= ?"
                    params.append(end_date)
            
            # Adicionar ordenação
            if sort_by:
                valid_columns = [
                    'created_at', 'project', 'filename', 'file_size', 
                    'speakers_count', 'audio_duration', 'estimated_cost'
                ]
                
                # Validar coluna de ordenação
                if sort_by in valid_columns:
                    query += f" ORDER BY {sort_by}"
                    
                    # Adicionar direção da ordenação (ASC ou DESC)
                    if sort_order and sort_order.upper() in ['ASC', 'DESC']:
                        query += f" {sort_order.upper()}"
                    else:
                        # Padrão é descendente para datas, ascendente para o resto
                        if sort_by == 'created_at':
                            query += " DESC"
                        else:
                            query += " ASC"
                else:
                    # Ordenação padrão por data de criação descendente
                    query += " ORDER BY created_at DESC"
            else:
                # Ordenação padrão por data de criação descendente
                query += " ORDER BY created_at DESC"
            
            cursor.execute(query, params)
            rows = cursor.fetchall()
            
            # Converter para lista de dicionários
            result = []
            for row in rows:
                result.append(dict(row))
            
            return result
    except Exception as e:
        logger.error(f"Erro ao listar transcrições: {e}")
        return []

def delete_transcription(trans_id):
    """Exclui uma transcrição pelo ID"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM transcriptions WHERE id = ?", (trans_id,))
            conn.commit()
            logger.info(f"Transcrição {trans_id} excluída com sucesso")
            return True
    except Exception as e:
        logger.error(f"Erro ao excluir transcrição: {e}")
        return False

def count_speakers_in_transcription(transcription):
    """Conta quantos speakers diferentes existem na transcrição"""
    try:
        speakers = set()
        for line in transcription.split('\n\n'):
            if ':' in line:
                speaker = line.split(':', 1)[0].strip()
                speakers.add(speaker)
        return len(speakers)
    except Exception as e:
        logger.error(f"Erro ao contar speakers: {e}")
        return 0