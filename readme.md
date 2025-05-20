# Sistema de AudioTranscrição Insper

Um sistema completo para transcrição de arquivos de áudio com identificação automática de falantes (diarização), correção ortográfica e geração de documentos formatados para o Insper.

## 📋 Funcionalidades

- **Transcrição de Áudio**: Converte arquivos de áudio em texto usando a API AssemblyAI
- **Diarização**: Identifica automaticamente os diferentes falantes na conversa
- **Correção Ortográfica**: Corrige erros comuns de transcrição
- **Geração de Documentos**: Cria arquivos DOCX e TXT formatados
- **Interface Web**: Interface amigável para upload, visualização e download
- **Banco de Dados**: Armazenamento das transcrições em SQLite
- **Organização por Pastas**: Cada transcrição é armazenada em sua própria pasta
- **Filtro e Busca**: Possibilidade de filtrar transcrições por período e termos

## 🚀 Instalação

### Pré-requisitos

- Python 3.11.4
- Dependências listadas em `requirements.txt`
- Chave de API da AssemblyAI

### Passos para Instalação

1. Clone o repositório:
   ```bash
   git clone https://insperedu.visualstudio.com/TranscricaoAudioLLM/_git/TranscricaoAudioLLM
   cd audiotranscricao
   ```

2. Crie e ative um ambiente virtual:
   ```bash
   python -m venv venv
   source venv/bin/activate  # No Windows: venv\Scripts\activate
   ```

3. Instale as dependências:
   ```bash
   pip install -r requirements.txt
   ```

4. Instale o modelo spaCy para português:
   ```bash
   python -m spacy download pt_core_news_sm
   ```

5. Configure sua chave de API da AssemblyAI em `services/transcribe.py` ou como variável de ambiente

6. Execute a aplicação:
   ```bash
   python app.py
   ```

7. Acesse a aplicação no navegador:
   ```
   http://localhost:5000
   ```

## 📂 Estrutura do Projeto

```
insper-audiotranscription/
├── app.py                      # Aplicação principal Flask
├── requirements.txt            # Dependências do projeto
├── depoimento_template.docx    # Template para exportação DOCX
├── static/                     # Arquivos estáticos (CSS, JS, imagens)
├── templates/                  # Templates HTML
│   ├── upload.html             # Página de upload
│   ├── transcriptions.html     # Listagem de transcrições
│   └── transcription.html      # Visualização individual de transcrição
│
├── models/                     # Modelos de dados
│   └── database.py             # Gerenciamento de banco de dados SQLite
│
├── services/                   # Serviços principais
│   ├── audio_processing.py     # Processamento de arquivos de áudio
│   ├── diarization.py          # Identificação de falantes
│   ├── speaker_identification.py  # Identificação avançada de falantes
│   └── transcribe.py           # Interface com AssemblyAI
│
└── utils/                      # Utilidades
    ├── corrections.py          # Correções de texto
    └── formatters.py           # Formatação e exportação de documentos
```

## 🧭 Guia de Uso

### 1. Upload de Áudio

1. Acesse a página inicial
2. Preencha o nome do depoimento e a descrição (ambos com mínimo de 10 caracteres)
3. Selecione um arquivo de áudio (formatos suportados: mp3, wav, m4a)
4. Mantenha marcada a opção "Dividir áudio em segmentos" para melhor processamento
5. Clique em "Enviar para Transcrição"
6. Aguarde o processamento (um indicador mostrará o progresso das etapas)

### 2. Lista de Transcrições

1. Acesse a página "Histórico"
2. Use os filtros de data para encontrar transcrições específicas
3. Busque por nome de depoimento no campo de busca
4. Ordene as colunas clicando nos cabeçalhos
5. Veja informações como data/hora, tamanho do arquivo, duração, quantidade de falantes e custo estimado
6. Clique no nome do projeto para visualizar a transcrição completa
7. Use os links diretos (DOCX, TXT) para baixar os arquivos

### 3. Visualização da Transcrição

1. Veja as informações básicas na barra de informações (arquivo, data, tamanho, duração, speakers)
2. Leia a descrição completa no box superior
3. Use os botões para download dos diferentes formatos
4. A transcrição será exibida com cores diferentes para cada falante:
   - Cinza para o Entrevistador
   - Vermelho para o Entrevistado/Outros speakers

## 🔍 Componentes Principais

### Modelos de Dados

#### `database.py`
Gerencia todas as operações do banco de dados SQLite que armazena as transcrições:
- Inicialização e criação de tabelas
- Persistência das transcrições e metadados
- Consultas para recuperação e listagem de dados
- Gerenciamento de atualizações e migrações do esquema

O banco de dados armazena:
- Metadados dos arquivos (nome, tamanho, duração)
- Texto transcrito com marcação de falantes
- Informações de projeto e descrição
- Estatísticas como número de falantes e custo estimado

### Serviços

#### `audio_processing.py`
Responsável pelo processamento de arquivos de áudio:
- Conversão entre formatos de áudio
- Divisão em segmentos para processamento mais eficiente
- Extração de metadados (duração, tamanho, canais)
- Limpeza de arquivos temporários

#### `diarization.py`
Módulo de compatibilidade para identificação de falantes:
- Mantido para compatibilidade com o sistema existente
- A maior parte da funcionalidade agora é delegada à API AssemblyAI

#### `speaker_identification.py`
Fornece identificação avançada de falantes usando processamento de linguagem natural:
- Extração de nomes próprios do texto
- Identificação de padrões de entrevistador vs. entrevistado
- Melhoria da marcação de falantes usando spaCy para NER (Named Entity Recognition)
- Processamento de formato específico para entrevistas

#### `transcribe.py`
Interface principal com a API AssemblyAI para transcrição:
- Configuração e envio de arquivos para a API
- Processamento de respostas e resultados
- Formatação de texto transcrito com marcação de falantes
- Aplicação de correções ortográficas

### Utilitários

#### `corrections.py`
Fornece correções ortográficas e de formatação ao texto transcrito:
- Correção de palavras comumente mal interpretadas
- Ajustes de pontuação e capitalização
- Correção de espaçamento e formatação geral
- Sistema extensível para adição de novas correções

#### `formatters.py`
Gerencia a exportação das transcrições em diferentes formatos:
- Criação de documentos DOCX formatados usando templates
- Exportação para TXT com formatação apropriada
- Funções utilitárias para formatação de datas, tamanhos e durações
- Gestão de pastas e arquivos de saída

## ⚙️ Configuração e Personalização

### Ajuste da Diarização

Para melhorar a identificação dos falantes, edite o arquivo `services/speaker_identification.py`:

1. Ajuste os padrões nas listas `NAME_PATTERNS` e `INTERVIEWER_INDICATORS`
2. Modifique as funções de processamento de nomes próprios
3. Ajuste os parâmetros de identificação automática

### Correções Ortográficas

Para adicionar novas correções ortográficas, edite o dicionário `CORRECTIONS` no arquivo `utils/corrections.py`:

```python
CORRECTIONS = {
    "termo_incorreto": "termo_correto",
    # Adicione mais correções aqui
}
```

Ou use a função auxiliar:

```python
add_corrections({
    "novo_erro": "correção",
    "outro_erro": "outra_correção"
})
```

### Configuração da API AssemblyAI

Ajuste as configurações da API em `services/transcribe.py`:

```python
config = aai.TranscriptionConfig(
    speaker_labels=True,         # Ativar identificação de speakers
    language_code="pt",          # Definir idioma como português
    punctuate=True,              # Adicionar pontuação automática
    format_text=True             # Formatar o texto automaticamente
)
```

## 🔧 Manutenção

### Limpeza de Arquivos Temporários

Os segmentos temporários são limpos automaticamente após o processamento. Para forçar uma limpeza:

```python
from services.audio_processing import cleanup_segments
cleanup_segments("uploads")
```

### Backup do Banco de Dados

Recomenda-se fazer backup regular do banco de dados:

```bash
cp transcriptions.db transcriptions.db.backup
```

## 🚨 Solução de Problemas

### Erros de Transcrição

Se a transcrição não estiver reconhecendo corretamente as palavras:
- Verifique a qualidade do áudio
- Adicione correções específicas em `utils/corrections.py`
- Verifique a conexão com a API AssemblyAI

### Problemas de Diarização

Se a identificação de falantes não estiver precisa:
- Adicione padrões específicos em `services/speaker_identification.py`
- Ajuste os indicadores de entrevistador/entrevistado
- Verifique se o áudio tem uma boa separação entre os falantes

### Problemas de Armazenamento

Os arquivos de áudio e transcrições podem ocupar bastante espaço:
- Verifique o espaço disponível regularmente
- Considere uma política de retenção para transcrições antigas
- Use o filtro por data para identificar transcrições que podem ser arquivadas

## 🔄 Fluxo de Processamento

1. **Upload**: O usuário faz upload de um arquivo de áudio com nome e descrição do projeto
2. **Pré-processamento**: O sistema extrai metadados e prepara o arquivo
3. **Transcrição**: O arquivo é enviado para a API AssemblyAI
4. **Processamento**: A transcrição é processada para identificação de falantes
5. **Armazenamento**: Os resultados são salvos no banco de dados
6. **Exportação**: Arquivos DOCX e TXT são gerados para download
7. **Visualização**: O usuário pode visualizar a transcrição formatada na interface web

## ⚠️ Limitações Atuais

- Exportação para PDF desativada para reduzir sobrecarga do sistema
- Limite de tamanho de arquivo de 50MB
- Conexão com internet necessária para transcrição (API externa)

## 🔮 Desenvolvimento Futuro

- Implementação de processamento offline usando modelos locais
- Melhoria nas capacidades de correção de texto específicas para português
- Interface para edição manual das transcrições
- Integração com sistemas de armazenamento em nuvem

## 📝 Licença

Este projeto é propriedade do Insper e está disponível para uso interno.

## 👥 Contribuições

Para contribuir com o projeto, entre em contato com a equipe responsável.

## 🙏 Agradecimentos

- [AssemblyAI](https://www.assemblyai.com/) pela API de transcrição
- [Flask](https://flask.palletsprojects.com/) pelo framework web
- [spaCy](https://spacy.io/) pelas ferramentas de processamento de linguagem natural
- [python-docx](https://python-docx.readthedocs.io/) pela geração de documentos
