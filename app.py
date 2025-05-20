import os
import uuid
import logging
import time
import shutil
from datetime import datetime
from flask import Flask, request, render_template, send_file, redirect, url_for, flash, jsonify
from werkzeug.utils import secure_filename
from pydub import AudioSegment
from models.database import get_db_connection
from pydub.utils import get_encoder_name

# Configuração de logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Inicializar a aplicação
app = Flask(__name__)
app.secret_key = os.urandom(24)  # Para mensagens flash
app.config['UPLOAD_FOLDER'] = "uploads"
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # Limite de 50MB para upload

# Criar pastas necessárias
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs("output", exist_ok=True)

# Importar módulos
from models.database import init_db, save_transcription, get_transcription, get_all_transcriptions, update_transcription
from services.audio_processing import get_audio_info, cleanup_segments
from services.transcribe import transcribe_audio_file
from utils.formatters import create_docx, create_txt, create_transcript_folder, format_file_size, format_timestamp, format_duration

# Inicializar o banco de dados
init_db()

# Adicione após as imports iniciais
if "ffmpeg" not in get_encoder_name():
    raise RuntimeError("FFmpeg não está instalado corretamente. Execute: choco install ffmpeg")

# Rotas do Flask
@app.route("/", methods=["GET", "POST"])
def upload_file():
    if request.method == "POST":
        start_time = time.time()
        logger.info("Iniciando processamento de upload")
        
        # Verificar se o arquivo foi enviado
        if "file" not in request.files:
            flash("Nenhum arquivo enviado", "error")
            return redirect(request.url)
        
        file = request.files["file"]
        project_name = request.form.get("project_name", "")
        description = request.form.get("description", "")
        split_audio = request.form.get("split_audio", "on") == "on"
        
        # Validar o nome do projeto e descrição
        if not project_name or len(project_name) < 10:
            flash("O nome do depoimento deve ter pelo menos 10 caracteres", "error")
            return redirect(request.url)
            
        if not description or len(description) < 10:
            flash("A descrição deve ter pelo menos 10 caracteres", "error")
            return redirect(request.url)
        
        # Simplificar os parâmetros de tempo do áudio
        audio_start = 0
        audio_end = 0
        
        # Verificar se o arquivo tem um nome
        if file.filename == "":
            flash("Nenhum arquivo selecionado", "error")
            return redirect(request.url)
        
        # Salvar o arquivo - usar um nome temporário para reduzir colisões
        filename = secure_filename(file.filename)
        temp_filename = f"temp_{int(time.time())}_{filename}"
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], temp_filename)
        file.save(file_path)
        
        # Log após salvar arquivo
        file_save_time = time.time() - start_time
        logger.info(f"Arquivo salvo em {file_save_time:.2f} segundos")
        
        # Inicializar variáveis com valores padrão
        audio_duration = 0
        estimated_cost = 0.0
        
        # Obter informações do arquivo de forma simplificada
        try:
            file_size = os.path.getsize(file_path)
            # Obter duração de forma simplificada
            audio = AudioSegment.from_file(file_path)
            audio_duration = len(audio) / 1000
            if audio_duration == 0:
                raise ValueError("Duração do áudio não pode ser zero")
            # Calcular custo estimado inicial
            estimated_cost = audio_duration * (0.37 / 3600)
        except Exception as e:
            logger.error(f"Falha crítica no processamento do áudio: {e}")
            flash("Arquivo de áudio inválido ou corrompido", "error")
            return redirect(request.url)
        
        # Gerar ID único para a transcrição
        trans_id = str(uuid.uuid4())
        
        # Criar pasta para a transcrição
        folder_path = create_transcript_folder(trans_id, project_name)
        
        # Processar o áudio
        try:
            # Log antes da transcrição
            pre_transcription_time = time.time() - start_time
            logger.info(f"Pré-processamento completo em {pre_transcription_time:.2f} segundos")
            
            # Transcrever o áudio com parâmetros otimizados
            transcription_options = {}
            if audio_start > 0 or audio_end > 0:
                transcription_options = {
                    'audio_start_from': audio_start,
                    'audio_end_at': audio_end
                }
            
            # Chamar função de transcrição
            transcribe_start = time.time()
            result = transcribe_audio_file(file_path, split=split_audio, transcription_options=transcription_options)
            transcription = result['text']
            speakers_count = result['speakers_count']
            
            # Atualizar a duração e o custo se disponível na API
            if 'audio_duration' in result:
                audio_duration = result['audio_duration']
                estimated_cost = audio_duration * (0.37 / 3600)
                logger.info(f"Duração do áudio obtida da API: {audio_duration} segundos")
            else:
                # Se a API não retornar a duração, usar o valor calculado anteriormente
                logger.info(f"Usando duração do áudio calculada localmente: {audio_duration} segundos")
            
            # Log após transcrição
            transcribe_time = time.time() - transcribe_start
            logger.info(f"Transcrição concluída em {transcribe_time:.2f} segundos")
            
            # Copiar o arquivo de áudio para a pasta da transcrição
            audio_filename = copy_audio_to_transcript_folder(file_path, folder_path, filename)
            
            # Salvar transcrição no banco de dados
            db_start = time.time()
            if not transcription or len(transcription.strip()) == 0:
                logger.error("Transcrição vazia ou inválida")
                flash("Erro: A transcrição está vazia", "error")
                return redirect(request.url)
            
            save_transcription(
                trans_id=trans_id,
                filename=filename,
                project_name=project_name,
                description=description,
                transcription=transcription,
                folder_path=folder_path,
                file_size=file_size,
                speakers_count=speakers_count,
                audio_duration=audio_duration,
                estimated_cost=estimated_cost
            )
            
            # Atualizar o caminho do áudio no banco de dados
            if audio_filename:
                try:
                    with get_db_connection() as conn:
                        cursor = conn.cursor()
                        cursor.execute("UPDATE transcriptions SET audio_path = ? WHERE id = ?", 
                                     (audio_filename, trans_id))
                        conn.commit()
                except Exception as e:
                    logger.warning(f"Não foi possível atualizar o caminho do áudio no banco: {e}")
            
            # Log após salvar no banco
            db_time = time.time() - db_start
            logger.info(f"Salvo no banco em {db_time:.2f} segundos")
            
            # Gerar arquivos para download
            dialogue = transcription.split("\n\n")
            
            # Preparar meta_info
            meta_info = {
                'created_at': format_timestamp(datetime.now()),
                'project': project_name,
                'filename': filename,
                'audio_duration': format_duration(audio_duration),
                'speakers_count': speakers_count
            }
            
            # DOCX
            docx_start = time.time()
            docx_path = os.path.join(folder_path, "transcricao.docx")
            create_docx(dialogue, docx_path, project_name, description, meta_info)
            docx_time = time.time() - docx_start
            logger.info(f"DOCX gerado em {docx_time:.2f} segundos")
            
            # TXT - simplificado e mais rápido
            txt_start = time.time()
            txt_path = os.path.join(folder_path, "transcricao.txt")
            with open(txt_path, 'w', encoding='utf-8') as f:
                f.write(transcription)
            txt_time = time.time() - txt_start
            logger.info(f"TXT gerado em {txt_time:.2f} segundos")
            
            # Limpar arquivos temporários
            try:
                # Remover arquivo de áudio temporário
                if os.path.exists(file_path):
                    os.remove(file_path)
                # Limpar segmentos se houver
                cleanup_segments(app.config['UPLOAD_FOLDER'])
            except Exception as cleanup_error:
                logger.warning(f"Erro na limpeza de arquivos temporários: {cleanup_error}")
            
            # Tempo total de processamento
            total_time = time.time() - start_time
            logger.info(f"Processamento completo em {total_time:.2f} segundos")
            
            flash("Transcrição concluída com sucesso!", "success")
            return redirect(url_for("view_transcription", trans_id=trans_id))
        
        except Exception as e:
            logger.error(f"Erro ao processar arquivo: {e}")
            # Tentar limpar arquivos temporários em caso de erro
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
            except:
                pass
            flash(f"Erro ao processar arquivo: {str(e)}", "error")
            return redirect(request.url)
    
    return render_template("upload.html")

@app.route("/transcriptions")
def list_transcriptions():
    try:
        # Obter filtros de data
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        
        # Obter termo de busca
        search_term = request.args.get('search', '')
        
        # Obter parâmetros de ordenação
        sort_by = request.args.get('sort_by', 'created_at')
        sort_order = request.args.get('sort_order', 'DESC')
        
        # Formatar datas para o formato usado no banco de dados
        if start_date:
            start_date = f"{start_date} 00:00:00"
        if end_date:
            end_date = f"{end_date} 23:59:59"
        
        # Buscar transcrições com filtro e ordenação
        transcriptions = get_all_transcriptions(start_date, end_date, sort_by, sort_order)
        
        # Filtrar por termo de busca, se fornecido
        if search_term:
            transcriptions = [t for t in transcriptions if search_term.lower() in t['project'].lower()]
        
        # Formatar dados para exibição
        for trans in transcriptions:
            # Usar valores padrão seguros para evitar problemas com None
            trans['formatted_date'] = format_timestamp(trans.get('created_at', ''))
            trans['formatted_size'] = format_file_size(trans.get('file_size', 0))
            
            # Verificar se audio_duration é None e fornecer valor padrão
            audio_duration = trans.get('audio_duration')
            if audio_duration is None:
                audio_duration = 0
                # Opcionalmente, atualizar no banco de dados com valor padrão
                update_transcription(trans['id'], audio_duration=0)
            
            trans['formatted_duration'] = format_duration(audio_duration)
            
            # Verificar se estimated_cost é None e fornecer valor padrão
            estimated_cost = trans.get('estimated_cost')
            if estimated_cost is None:
                estimated_cost = 0.0
                # Opcionalmente, atualizar no banco de dados com valor padrão
                update_transcription(trans['id'], estimated_cost=0.0)
            
            trans['formatted_cost'] = f"${estimated_cost:.4f}"
            
            # Verificar speakers_count
            if trans.get('speakers_count') is None:
                trans['speakers_count'] = 0
        
        # Passar parâmetros de ordenação para o template
        return render_template(
            "transcriptions.html", 
            transcriptions=transcriptions,
            current_sort=sort_by,
            current_order=sort_order
        )
    except Exception as e:
        logger.error(f"Erro ao listar transcrições: {e}")
        flash(f"Erro ao listar transcrições: {str(e)}", "error")
        return redirect(url_for("upload_file"))

def format_file_size(size_bytes):
    """
    Formata o tamanho do arquivo para exibição
    """
    try:
        # Garantir que size_bytes seja um número
        size_bytes = float(size_bytes) if size_bytes is not None else 0
        
        # Converter bytes para formato legível
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.2f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.2f} TB"
    except Exception:
        return "Desconhecido"

def format_timestamp(timestamp):
    """
    Formata um timestamp para exibição
    """
    try:
        if not timestamp:
            return "Data desconhecida"
        
        # Se for uma string de data do SQLite
        if isinstance(timestamp, str):
            from datetime import datetime
            try:
                dt = datetime.strptime(timestamp, "%Y-%m-%d %H:%M:%S")
                return dt.strftime("%d/%m/%Y %H:%M")
            except ValueError:
                return timestamp
        
        # Se for um objeto datetime
        if hasattr(timestamp, 'strftime'):
            return timestamp.strftime("%d/%m/%Y %H:%M")
            
        return str(timestamp)
    except Exception:
        return "Data desconhecida"

def format_duration(seconds):
    """
    Formata duração em segundos para exibição (hh:mm:ss)
    """
    try:
        # Garantir que seconds seja um número inteiro
        seconds = int(float(seconds)) if seconds is not None else 0
        
        if seconds < 60:
            return f"{seconds} seg"
        
        minutes = seconds // 60
        remaining_seconds = seconds % 60
        
        if minutes < 60:
            return f"{minutes}m {remaining_seconds}s"
        
        hours = minutes // 60
        remaining_minutes = minutes % 60
        
        return f"{hours}h {remaining_minutes}m {remaining_seconds}s"
    except Exception:
        return "Desconhecido"


def copy_audio_to_transcript_folder(source_path, target_folder, filename):
    """
    Copia o arquivo de áudio para a pasta da transcrição
    """
    try:
        # Garantir que o nome do arquivo seja seguro
        safe_filename = secure_filename(filename)
        
        # Caminho completo do destino
        audio_path = os.path.join(target_folder, safe_filename)
        
        # Copiar o arquivo
        shutil.copy2(source_path, audio_path)
        
        # Converter para MP3 se não for (para garantir compatibilidade com os navegadores)
        if not safe_filename.lower().endswith('.mp3'):
            try:
                # Carregar o áudio
                audio = AudioSegment.from_file(audio_path)
                
                # Caminho do MP3
                mp3_path = os.path.join(target_folder, "audio_playback.mp3")
                
                # Exportar como MP3
                audio.export(mp3_path, format="mp3")
                
                return os.path.basename(mp3_path)
            except Exception as e:
                logger.error(f"Erro ao converter áudio para MP3: {e}")
                return safe_filename
        
        return safe_filename
    except Exception as e:
        logger.error(f"Erro ao copiar arquivo de áudio: {e}")
        return None
    
@app.route("/audio/<trans_id>/<filename>")
def serve_audio(trans_id, filename):
    try:
        # Buscar transcrição para verificar se o arquivo pertence a ela
        transcription = get_transcription(trans_id)
        
        if not transcription:
            flash("Transcrição não encontrada", "error")
            return redirect(url_for("list_transcriptions"))
        
        # Verificar se o arquivo está na pasta da transcrição
        folder_path = transcription.get('folder_path')
        if not folder_path or not os.path.exists(folder_path):
            flash("Pasta da transcrição não encontrada", "error")
            return redirect(url_for("view_transcription", trans_id=trans_id))
        
        # Verificar se o nome do arquivo corresponde
        audio_path = os.path.join(folder_path, filename)
        if not os.path.exists(audio_path):
            flash("Arquivo de áudio não encontrado", "error")
            return redirect(url_for("view_transcription", trans_id=trans_id))
        
        # Detectar o tipo MIME para o arquivo de áudio
        mime_type = "audio/mpeg"  # Padrão para .mp3
        if filename.lower().endswith('.wav'):
            mime_type = "audio/wav"
        elif filename.lower().endswith('.m4a'):
            mime_type = "audio/mp4"
        
        # Enviar o arquivo
        return send_file(audio_path, mimetype=mime_type)
    except Exception as e:
        logger.error(f"Erro ao servir arquivo de áudio: {e}")
        flash(f"Erro ao reproduzir áudio: {str(e)}", "error")
        return redirect(url_for("view_transcription", trans_id=trans_id))
    

@app.route("/transcription/<trans_id>")
def view_transcription(trans_id):
    try:
        # Buscar transcrição
        transcription = get_transcription(trans_id)
        
        if not transcription:
            flash("Transcrição não encontrada", "error")
            return redirect(url_for("list_transcriptions"))
        
        # Extrair nomes dos speakers
        speakers = []
        for line in transcription['transcription'].split('\n\n'):
            if ':' in line:
                speaker = line.split(':', 1)[0].strip()
                if speaker not in speakers:
                    speakers.append(speaker)
        
        # Formatar dados para exibição com tratamento seguro para valores None
        formatted_date = format_timestamp(transcription.get('created_at', ''))
        formatted_size = format_file_size(transcription.get('file_size', 0))
        
        # Verificar e tratar audio_duration
        audio_duration = transcription.get('audio_duration')
        if audio_duration is None or audio_duration == 0:
            # Tentar calcular a duração se o arquivo estiver disponível
            try:
                folder_path = transcription.get('folder_path')
                audio_file = transcription.get('audio_path')
                if folder_path and audio_file and os.path.exists(os.path.join(folder_path, audio_file)):
                    audio = AudioSegment.from_file(os.path.join(folder_path, audio_file))
                    audio_duration = len(audio) / 1000  # em segundos
                    # Atualizar no banco de dados
                    update_transcription(trans_id, audio_duration=audio_duration)
            except Exception as e:
                logger.warning(f"Não foi possível calcular a duração: {e}")
                audio_duration = 0
        
        formatted_duration = format_duration(audio_duration)
        
        # Recalcular o custo baseado na duração correta
        estimated_cost = audio_duration * (0.37 / 3600)  # $0.37 por hora
        if estimated_cost != transcription.get('estimated_cost'):
            # Atualizar no banco de dados
            update_transcription(trans_id, estimated_cost=estimated_cost)
        
        formatted_cost = f"${estimated_cost:.4f}"
        
        # Garantir que speakers_count tenha um valor
        if transcription.get('speakers_count') is None or transcription.get('speakers_count') == 0:
            transcription['speakers_count'] = len(speakers) if speakers else 0
            # Atualizar no banco de dados
            update_transcription(trans_id, speakers_count=transcription['speakers_count'])
        
        return render_template(
            "transcription.html", 
            project=transcription['project'],
            description=transcription['description'],
            filename=transcription['filename'],
            transcription=transcription['transcription'],
            speakers_count=transcription['speakers_count'],
            speakers=speakers,
            formatted_date=formatted_date,
            formatted_size=formatted_size,
            formatted_duration=formatted_duration,
            formatted_cost=formatted_cost,
            trans_id=trans_id,
            audio_path=transcription.get('audio_path'),
            audio_duration=audio_duration
        )
    except Exception as e:
        logger.error(f"Erro ao visualizar transcrição: {e}")
        flash(f"Erro ao visualizar transcrição: {str(e)}", "error")
        return redirect(url_for("list_transcriptions"))
    
@app.route("/download/<trans_id>/<format>")
def download_transcription(trans_id, format):
    try:
        # Buscar transcrição
        transcription = get_transcription(trans_id)
        
        if not transcription:
            flash("Transcrição não encontrada", "error")
            return redirect(url_for("list_transcriptions"))
        
        # Verificar se a pasta existe
        folder_path = transcription.get('folder_path')
        if not folder_path or not os.path.exists(folder_path):
            folder_path = create_transcript_folder(trans_id, transcription['project'])
            update_transcription(trans_id, folder_path=folder_path)
        
        # Processar o diálogo
        dialogue = transcription['transcription'].split("\n\n")
        
        # Preparar metadados para o template
        meta_info = {
            'created_at': format_timestamp(transcription.get('created_at', '')),
            'project': transcription['project'],
            'filename': transcription['filename'],
            'audio_duration': format_duration(transcription.get('audio_duration', 0)),
            'speakers_count': transcription.get('speakers_count', 0)
        }
        
        try:
            # Redirecionar solicitações de PDF para DOCX
            if format == "pdf":
                # Informar o usuário sobre a mudança
                flash("Geração de PDF desativada para reduzir sobrecarga. Fornecendo versão DOCX.", "info")
                format = "docx"  # Mudar o formato para DOCX
                
            if format == "docx":
                output_file = os.path.join(folder_path, "transcricao.docx")
                # Sempre recriar o arquivo para garantir que use o template mais recente
                create_docx(dialogue, output_file, transcription['project'], 
                            transcription.get('description', ''), meta_info)
                return send_file(output_file, as_attachment=True, download_name=f"{transcription['project']}.docx")
                
            elif format == "txt":
                output_file = os.path.join(folder_path, "transcricao.txt")
                # O arquivo TXT pode ser simples
                if not os.path.exists(output_file):
                    create_txt(transcription['transcription'], output_file)
                return send_file(output_file, as_attachment=True, download_name=f"{transcription['project']}.txt")
                
            else:
                flash("Formato de download inválido", "error")
                return redirect(url_for("view_transcription", trans_id=trans_id))
                
        except Exception as e:
            logger.error(f"Erro ao gerar arquivo {format}: {e}")
            flash(f"Erro ao gerar arquivo {format}: {str(e)}", "error")
            return redirect(url_for("view_transcription", trans_id=trans_id))
            
    except Exception as e:
        logger.error(f"Erro ao baixar transcrição: {e}")
        flash(f"Erro ao baixar transcrição: {str(e)}", "error")
        return redirect(url_for("list_transcriptions"))
    

@app.route("/audio-info", methods=["POST"])
def get_audio_info_route():
    try:
        # Verificar se o arquivo foi enviado
        if "file" not in request.files:
            return jsonify({"error": "Nenhum arquivo enviado"}), 400
        
        file = request.files["file"]
        
        # Verificar se o arquivo tem um nome
        if file.filename == "":
            return jsonify({"error": "Nenhum arquivo selecionado"}), 400
        
        # Salvar o arquivo temporariamente
        filename = secure_filename(file.filename)
        temp_path = os.path.join(app.config['UPLOAD_FOLDER'], "temp_" + filename)
        file.save(temp_path)
        
        # Obter informações do arquivo
        audio_info = get_audio_info(temp_path)
        
        # Novo cálculo de custo: $0.37 por hora = $0.0001028 por segundo
        duration_seconds = audio_info['duration_seconds']
        estimated_cost = duration_seconds * (0.37 / 3600)
        
        # Adicionar informações adicionais
        audio_info['estimated_cost'] = round(estimated_cost, 4)
        audio_info['estimated_cost_formatted'] = f"${estimated_cost:.4f}"
        
        
        return jsonify(audio_info)
    except Exception as e:
        logger.error(f"Erro ao processar informações do áudio: {e}")
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)