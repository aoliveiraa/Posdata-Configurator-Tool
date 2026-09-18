# PosData Configurator

Ferramenta desktop para automatizar a preparação, transformação, validação e geração de arquivos PosData usados em ambientes de testes de Performance.

A aplicação analisa o PosData atual e o novo PosData, identifica dinamicamente os nós disponíveis, resolve diferenças de configuração e gera os arquivos adaptados para o laboratório selecionado.

## Status da versão

**Versão:** `1.0.0-RC1`  
**Status:** Release Candidate  
**Objetivo:** Validação no Lab BR

## Mercados

### Mercados homologados

- AU
- CA
- DE
- PT
- UK
- US

### Mercado em homologação

- ES

> ES ainda não faz parte do escopo oficial da ferramenta. Seus arquivos podem ser utilizados para testes de compatibilidade e evolução do processo de homologação.

## Principais funcionalidades

### Configuração por laboratório

A ferramenta permite selecionar a configuração correspondente ao laboratório de execução.

Configurações atualmente suportadas:

- BR
- RIO
- RENEIGH

Cada laboratório possui seu próprio arquivo JSON na pasta `config`.

### Market Readiness

Antes da geração, a ferramenta verifica se os componentes necessários estão disponíveis:

- POS
- KVS
- Itonas
- WAY
- FOE
- COD
- StoreDB

A geração só deve prosseguir quando o resultado for:

```text
READY FOR GENERATION