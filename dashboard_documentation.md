# Documentação do Dashboard de Informativos STF (V6 - Integração ChatGPT)

## Visão Geral

Este dashboard interativo, desenvolvido com Streamlit, permite a exploração e análise dos Informativos de Jurisprudência do Supremo Tribunal Federal (STF) compilados a partir do arquivo `Dados_InformativosSTF_2021-2025.xlsx`. O objetivo é fornecer uma ferramenta para estudo e consulta dos julgados, com funcionalidades adicionais **integradas à API OpenAI (GPT-4)** para auxiliar na fixação do conteúdo e organização dos estudos.

**IMPORTANTE:** As funcionalidades de IA (Assertivas, Perguntas, Caso Prático) requerem uma chave de API da OpenAI configurada nos segredos (`secrets`) da sua aplicação no Streamlit Community Cloud. Veja a seção "Configuração da API OpenAI" abaixo.

## Funcionalidades Principais (V6)

O dashboard está organizado em abas e possui uma barra lateral para filtros avançados.

### 1. Carregamento e Processamento de Dados

- Os dados são carregados a partir do arquivo Excel `Dados_InformativosSTF_2021-2025.xlsx` (filtrado para 2021-2025).
- O processo inclui:
    - Identificação e uso da coluna "Tese Julgado" para exibir a "Tese / Notícia Completa".
    - Limpeza de colunas e renomeação.
    - Conversão de tipos de dados (datas).
    - Extração de **Ano** e **Mês/Ano** para filtros.
    - Processamento da coluna "Ramo Direito" (`explode`).
    - Mapeamento (simulado) dos "Ramos do Direito" para "Áreas de Estudo".
    - Tratamento de valores ausentes.

### 2. Barra Lateral: Filtros Avançados

- **Filtrar Data Por:** Ano ou Mês/Ano.
- **Ano do Julgamento:** Seleção múltipla.
- **Mês/Ano do Julgamento:** Seleção múltipla.
- **Área de Estudo (Simulado):** Seleção múltipla.
- **Ramo do Direito (Específico):** Seleção múltipla.
- **Classe Processual:** Seleção múltipla.
- **Número do Informativo:** Seleção única.
- **Repercussão Geral:** Seleção única.
- **Mostrar Apenas Favoritos:** Checkbox.
- **Contador:** Exibe contagem de julgados filtrados.

### 3. Aba "🔍 Informativos"

- **Busca por Palavra-Chave:** Busca em `Título`, `Tese Julgado`, `Resumo`.
- **Modo de Visualização:** Cards ou Tabela.
- **Cards:** Exibem detalhes do julgado, botão de Favoritar (⭐/☆), e botões de ação ("Gerar Assertivas", "Ver Caso Prático").
- **Tabela:** Exibe dados em formato tabular.
- **Funcionalidade Favoritos:** Marcar/desmarcar julgados.
- **Funcionalidade "Caso Prático" (Integrado GPT-4):** Ao clicar no botão "Ver Caso Prático", um caso prático **gerado pela API OpenAI (GPT-4)** baseado no julgado é exibido em um container.

### 4. Aba "📊 Estatísticas"

- Exibe gráficos interativos (Julgados por Ramo, Área, Ano, RG) baseados nos dados filtrados pela barra lateral.

### 5. Aba "✅ Assertivas" (Integrado GPT-4)

- Permite selecionar um julgado na aba "Informativos" (usando o botão "Gerar Assertivas").
- Exibe os detalhes do julgado selecionado.
- **Botão "Gerar 5 Assertivas com IA (GPT-4)":** Ao clicar, envia a tese/notícia do julgado para a **API OpenAI (GPT-4)**, que gera 5 assertivas no formato Certo/Errado com justificativas.

### 6. Aba "❓ Perguntas" (Integrado GPT-4)

- Permite fazer perguntas em linguagem natural sobre os julgados **atualmente filtrados/buscados** na aba "Informativos".
- **Botão "Buscar Resposta com IA (GPT-4)":** Ao clicar, envia a pergunta do usuário e o contexto dos primeiros julgados filtrados para a **API OpenAI (GPT-4)**. A IA é instruída a responder **estritamente com base no contexto fornecido**.

### 7. Aba "🎯 Metas de Estudo"

- Permite ao usuário definir uma meta de leitura.
- **Filtros para Meta:** Permite aplicar filtros (Ano, Área, Ramo) **antes** de gerar a meta.
- **Quantidade de Julgados para Ler:** Campo numérico.
- **Botão "Gerar Meta de Leitura Aleatória":** Seleciona aleatoriamente julgados únicos a partir dos resultados **filtrados para a meta**.
- **Lista de Metas:** Exibe botões para cada julgado da meta.
- **Interatividade:** Clicar em um botão da meta exibe o card completo do julgado correspondente na mesma aba.

## Configuração da API OpenAI (Obrigatório para Funcionalidades de IA)

Para que as funcionalidades "Gerar Assertivas", "Buscar Resposta" e "Ver Caso Prático" funcionem, você **precisa** configurar sua chave de API da OpenAI no Streamlit Community Cloud:

1.  **Obtenha sua Chave:** Crie uma conta na [OpenAI](https://openai.com/) e obtenha sua chave de API secreta.
2.  **Acesse seu App no Streamlit Cloud:** Faça login na sua conta Streamlit e vá para as configurações (Settings) do seu aplicativo implantado.
3.  **Configure os Segredos (Secrets):**
    *   Vá para a seção "Secrets".
    *   Adicione um novo segredo com a seguinte chave (key): `OPENAI_API_KEY`
    *   No valor (value), cole a sua chave de API secreta da OpenAI.
    *   Salve os segredos.
4.  **Reinicie o App:** O Streamlit Cloud geralmente reinicia o aplicativo automaticamente após salvar os segredos. Se não, reinicie manualmente.

Após configurar a chave, as funcionalidades de IA estarão ativas.

## Execução Local

1.  Descompacte o arquivo `.zip` fornecido.
2.  Navegue até a pasta `stf_dashboard` pelo terminal.
3.  Instale as dependências: `pip install -r requirements.txt`
4.  (Opcional, para teste local da IA) Crie um arquivo `.streamlit/secrets.toml` dentro da pasta `stf_dashboard` com o seguinte conteúdo:
    ```toml
    OPENAI_API_KEY="sua_chave_api_openai_aqui"
    ```
5.  Execute o dashboard: `streamlit run app.py`

*Nota: O arquivo de dados `Dados_InformativosSTF_2021-2025.xlsx` deve estar na mesma pasta que `app.py` para a execução funcionar corretamente.*

