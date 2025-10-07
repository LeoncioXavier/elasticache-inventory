# ElastiCache Inventory

**📄 [English Version](README.md)** | **📄 Versão em Português**

Uma ferramenta Python modular para inventariar recursos ElastiCache Redis através de perfis e regiões AWS com varredura paralela, atualizações incrementais e relatórios abrangentes.

Índice
- [Visão Geral](#visão-geral)
- [Funcionalidades](#funcionalidades)
- [Instalação](#instalação)
- [Exemplos de uso](#exemplos-de-uso)
- [Opções do CLI](#opções-do-cli)
- [Configuração](#configuração)  
- [Saídas e relatórios](#saídas-e-relatórios)
- [Detalhes do relatório HTML](#detalhes-do-relatório-html)
- [Tratamento de credenciais](#tratamento-de-credenciais)
- [Testes e desenvolvimento](#testes-e-desenvolvimento)
- [Migração da v0.x](#migração-da-v0x)
- [Changelog](#changelog)
- [Contribuindo](#contribuindo)

## Visão Geral

Esta ferramenta faz varredura de contas AWS (perfis) e coleta metadados sobre recursos ElastiCache Redis (grupos de replicação e clusters de cache) através de regiões configuráveis. Projetada para gerenciamento de inventário, revisões de segurança e relatórios de conformidade.

**Principais melhorias na v1.0:**
- **Regiões configuráveis** (não mais hard-coded)
- **Tags configuráveis** (não mais limitadas a CC, Email, Team)
- **Varredura paralela de perfis** para melhor performance
- **Varredura incremental** para detectar mudanças desde a última execução
- **Codebase modular** com separação adequada de responsabilidades
- **Setup abrangente de linting e formatação**

## Funcionalidades

- **Varredura multi-perfil** — descobre perfis em `~/.aws/config` / `~/.aws/credentials` ou varre perfis específicos
- **Regiões configuráveis** — especifique qualquer região AWS para varrer (parâmetro obrigatório)
- **Tags configuráveis** — especifique quais tags coletar (padrão: Team)
- **Varredura paralela** — varra múltiplos perfis simultaneamente para melhor performance
- **Modo incremental** — apenas varre recursos que mudaram desde a última execução
- **Formatos de exportação** — CSV, Excel e relatório HTML interativo com filtros e gráficos
- **Tratamento amigável de credenciais** — sessões AWS expiradas/inválidas mostram orientações acionáveis

## Instalação

Requisitos:
- Python 3.8 ou mais recente
- Configuração AWS CLI / credenciais em `~/.aws` para os perfis que você quer varrer

### Setup rápido (macOS / Linux)

```bash
cd ~/elasticache_scanner
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Setup de desenvolvimento

```bash
cd ~/elasticache_scanner
make install-dev
```

Isso instala dependências de desenvolvimento (black, flake8, mypy, pre-commit) e configura hooks de pre-commit.

### Setup com Docker

```bash
# Construir a imagem Docker
docker build -t elasticache-inventory .

# Executar com credenciais AWS e diretório de saída montados
docker run --rm \
  -v ~/.aws:/root/.aws:ro \
  -v $(pwd)/output:/app/output \
  elasticache-inventory --regions us-east-1 sa-east-1
```

## Exemplos de uso

**Varredura básica** (especificar regiões - obrigatório):

```bash
python3 -m elasticache_scanner --regions us-east-1 sa-east-1
```

**Varredura com tags customizadas:**

```bash
python3 -m elasticache_scanner --regions us-east-1 --tags Team Environment Owner
```

**Varredura paralela com grupos de replicação:**

```bash
python3 -m elasticache_scanner --regions us-east-1 sa-east-1 --include-replication-groups --parallel-profiles 8
```

**Varredura incremental (apenas recursos alterados):**

```bash
python3 -m elasticache_scanner --regions us-east-1 --incremental
```

**Execução a seco para teste de UI:**

```bash
python3 -m elasticache_scanner --dry-run --sample-file elasticache_report.csv --regions us-east-1
```

**Varrer perfis específicos:**

```bash
python3 -m elasticache_scanner --regions us-east-1 --profile prod-profile --profile staging-profile
```

## Opções do CLI

### Obrigatório
- `--regions REGIONS [REGIONS ...]` — Regiões AWS para varrer (ex.: us-east-1 sa-east-1)

### Configuração opcional
- `--tags TAGS [TAGS ...]` — Tags para coletar dos recursos (padrão: Team)
- `--profile PROFILE` — Perfil(s) AWS para varrer (pode ser usado múltiplas vezes)

### Opções de varredura
- `--include-replication-groups` — Incluir recursos de grupos de replicação (padrão: apenas clusters)
- `--node-info` — Buscar informações detalhadas de nós (aumenta chamadas de API)
- `--incremental` — Apenas varrer recursos que mudaram desde a última execução
- `--parallel-profiles N` — Número de perfis para varrer em paralelo (padrão: 4)

### Opções de saída
- `--output-dir DIR` — Diretório de saída (padrão: diretório atual)
- `--out-csv`, `--out-xlsx`, `--out-html` — Sobrescrever nomes de arquivos de saída
- `--dry-run` — Gerar relatórios a partir de CSV existente sem chamadas AWS
- `--sample-file PATH` — Arquivo CSV para usar na execução a seco

## Configuração

A ferramenta usa uma dataclass `ScanConfig` para gerenciamento de configuração. Configurações principais:

- **Regiões**: Devem ser especificadas via `--regions` (não mais hard-coded)
- **Tags**: Padrão para `["Team"]` mas pode ser customizado via `--tags`
- **Perfis paralelos**: Padrão para 4 varreduras de perfis simultâneas
- **Estado incremental**: Armazenado em `scan_state.json` para detecção de mudanças

## Saídas e relatórios

- `elasticache_report.csv` — Exportação CSV bruta de todos os recursos encontrados
- `elasticache_report.xlsx` — Planilha Excel dos mesmos dados
- `elasticache_report.html` — Relatório HTML interativo com filtros e gráficos
- `scan_errors.log` — Saída de logging (avisos e erros)
- `scan_failures.json` — Resumo JSON de perfis falhados com mensagens amigáveis
- `scan_state.json` — Arquivo de estado para varredura incremental (auto-gerado)

## Detalhes do relatório HTML

O relatório HTML gerado inclui:

- **Tabela interativa**: Paginação (30 linhas/página), alternância de visibilidade de colunas, ordenação
- **Filtros multi-seleção**: Região, Conta, Team, Tipo de Recurso e tags customizadas
- **Correspondência fuzzy de engine**: Filtro de Engine Groups suporta agrupamento estilo `7.x`
- **Capacidades de exportação**: Exportar linhas filtradas para CSV
- **Gráficos**: Versões de engine, status de criptografia, regiões e principais teams
- **Sem dependências externas**: Todos os assets são baseados em CDN, nenhum arquivo local necessário

## Tratamento de credenciais

A ferramenta detecta problemas comuns de credenciais e fornece orientações acionáveis:

```
Profile default: AWS session token appears invalid or expired. 
Please run 'aws sso login --profile default' or refresh your credentials and try again.
```

Perfis falhados são resumidos em `scan_failures.json` para fácil solução de problemas.

## Testes e desenvolvimento

### Executar testes
```bash
make test
# ou
pytest tests/ -v
```

### Formatação e linting de código
```bash
make format  # Executar black e isort
make lint    # Executar flake8, mypy e verificações de formatação
```

### Fluxo de desenvolvimento
```bash
make install-dev  # Instalar dependências de dev e hooks de pre-commit
make run-example  # Executar varredura de exemplo
make dry-run      # Testar mudanças de UI sem chamadas AWS
```

### Targets make disponíveis
Execute `make help` para ver todos os targets disponíveis incluindo exemplos para diferentes modos de varredura.

## Migração da v0.x

Se você está migrando do `scan_elasticache.py` original:

### Mudanças de comando
**Antigo:**
```bash
python scan_elasticache.py
```

**Novo:**
```bash
python3 -m elasticache_scanner --regions us-east-1 sa-east-1
```

### Principais diferenças
1. **Regiões agora obrigatórias**: Deve especificar `--regions` (não mais hard-coded para us-east-1, sa-east-1)
2. **Tags configuráveis**: Use `--tags Team Environment` ao invés de CC, Email, Team hard-coded
3. **Estrutura modular**: Execute como `python3 -m elasticache_scanner` ao invés de script direto
4. **Novas funcionalidades**: `--incremental`, `--parallel-profiles`, melhor tratamento de erros

### Migração de configuração
- Atualize scripts/automação para incluir parâmetro `--regions`
- Considere usar `--tags` para especificar o esquema de tags da sua organização
- Aproveite `--parallel-profiles` para varredura mais rápida
- Use `--incremental` para monitoramento regular com detecção de mudanças

## Changelog

### v1.0.0 (2025-10-06)
- **BREAKING**: Regiões agora são configuráveis e obrigatórias (use `--regions`)
- **BREAKING**: Estrutura modular - execute como `python3 -m elasticache_scanner`
- **NOVO**: Tags configuráveis via parâmetro `--tags`
- **NOVO**: Varredura paralela de perfis com `--parallel-profiles`
- **NOVO**: Varredura incremental com `--incremental` e rastreamento de estado
- **NOVO**: Codebase modular dividido em módulos lógicos
- **NOVO**: Setup abrangente de linting/formatação (black, flake8, mypy)
- **NOVO**: CLI aprimorado com melhor ajuda e exemplos
- **MELHORADO**: Tratamento amigável de erros de credencial com mensagens acionáveis
- **MELHORADO**: Melhor cobertura de testes com chamadas AWS mockadas

### v0.x (Anterior)
- Varredura básica com regiões hard-coded (us-east-1, sa-east-1)
- Tags hard-coded (CC, Email, Team)
- Estrutura monolítica de arquivo único
- Varredura sequencial de perfis

## Contribuindo

1. **Configure ambiente de desenvolvimento:**
   ```bash
   make install-dev
   ```

2. **Faça mudanças e teste:**
   ```bash
   make format
   make lint
   make test
   ```

3. **Teste com dados AWS reais:**
   ```bash
   make run-example
   ```

4. **Submeta PR** com uma descrição clara das mudanças

### Estilo de código
- Use `black` para formatação (comprimento de linha: 120)
- Siga regras de linting do `flake8`
- Type hints com validação `mypy`
- Hooks de pre-commit garantem padrões

## License

Este projeto está licenciado sob a Licença MIT - veja o arquivo [LICENSE](LICENSE) para detalhes.

---

Para perguntas ou problemas, verifique os arquivos `scan_errors.log` e `scan_failures.json` para informações detalhadas de erro.