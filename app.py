import streamlit as st
import pandas as pd
import altair as alt
import re # Import regex for search
from datetime import datetime # For date filtering
import random # For study blocks

import openai

# --- OpenAI API Key Configuration ---
openai_api_key = None
try:
    openai_api_key = st.secrets["OPENAI_API_KEY"]
    openai.api_key = openai_api_key
    print("OpenAI API Key loaded from secrets.") # Add print for debugging
except KeyError:
    print("OpenAI API Key not found in st.secrets.") # Add print for debugging
    # No st.error here yet, handle it within features that need the key
except Exception as e:
    print(f"An error occurred loading OpenAI API Key: {e}") # Add print for debugging

# Configuração inicial da página
st.set_page_config(
    page_title="Informativos STF | Mentoria de Resultado",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Título do Dashboard
st.title("Informativos STF - 2021 a 2025")
st.caption("Mentoria de Resultado - Prof. Leonardo Aquino")

# --- Gerenciamento de Estado --- 
if 'selected_julgado_id_assertiva' not in st.session_state:
    st.session_state.selected_julgado_id_assertiva = None
if 'selected_julgado_id_caso' not in st.session_state:
    st.session_state.selected_julgado_id_caso = None
if 'show_caso_pratico_dialog' not in st.session_state:
    st.session_state.show_caso_pratico_dialog = False
if 'favorites' not in st.session_state:
    st.session_state.favorites = set()
if 'selected_meta_julgado_id' not in st.session_state: # For clickable study blocks
    st.session_state.selected_meta_julgado_id = None
if 'current_study_meta_ids' not in st.session_state: # Store current meta list
    st.session_state.current_study_meta_ids = []
# Add state for meta filters
if 'meta_filter_anos' not in st.session_state:
    st.session_state.meta_filter_anos = []
if 'meta_filter_ramos' not in st.session_state:
    st.session_state.meta_filter_ramos = []
if 'meta_filter_areas' not in st.session_state:
    st.session_state.meta_filter_areas = []

# --- Mapeamento Simulado (Ramo -> Área de Estudo) --- 
RAMO_TO_AREA_MAP = {
    'Direito Constitucional': 'Direito Público',
    'Direito Administrativo': 'Direito Público',
    'Direito Tributário': 'Direito Público',
    'Direito Financeiro': 'Direito Público',
    'Direito Eleitoral': 'Direito Público',
    'Direito Ambiental': 'Direito Público',
    'Direito Urbanístico': 'Direito Público',
    'Direito Penal': 'Direito Penal',
    'Direito Processual Penal': 'Direito Penal',
    'Direito Civil': 'Direito Privado',
    'Direito Empresarial': 'Direito Privado',
    'Direito Comercial': 'Direito Privado',
    'Direito do Consumidor': 'Direito Privado',
    'Direito Processual Civil': 'Direito Processual',
    'Direito do Trabalho': 'Direito Social / Trabalho',
    'Direito Processual do Trabalho': 'Direito Social / Trabalho',
    'Direito Previdenciário': 'Direito Social / Previdenciário',
    'Direito Internacional Público': 'Direito Internacional',
    'Direito Internacional Privado': 'Direito Internacional',
}
DEFAULT_AREA = 'Outras Áreas'

# --- Carregamento e Preparação dos Dados (Atualizado V5 - Filtered Excel) ---
@st.cache_data
def load_data(excel_path):
    try:
        # Read from the filtered Excel file
        df = pd.read_excel(excel_path)
        print(f"Colunas lidas do Excel: {df.columns.tolist()}")

        # Rename columns based on the Excel structure
        rename_map = {
            'Numero do informativo': 'numero_informativo',
            'Classe Processo': 'classe_processo',
            'Data Julgamento': 'data_julgamento',
            'Tese Julgado': 'tese_julgamento', # 'Notícia Completa'
            'Ramo Direito': 'ramo_direito',
            'Repercussão Geral': 'repercussao_geral',
            'Título': 'Título',
            'Resumo': 'Resumo',
            'Legislação': 'Legislação'
        }
        existing_cols_map = {k: v for k, v in rename_map.items() if k in df.columns}
        df.rename(columns=existing_cols_map, inplace=True)
        print(f"Colunas após renomear: {df.columns.tolist()}")

        # Ensure essential columns exist
        essential_cols = ['Título', 'tese_julgamento', 'ramo_direito', 'classe_processo', 'Resumo', 'Legislação', 'numero_informativo', 'repercussao_geral', 'data_julgamento']
        for col in essential_cols:
            if col not in df.columns:
                # If data_julgamento is missing, we can't filter by year, raise error
                if col == 'data_julgamento':
                     raise ValueError(f"Erro Crítico: Coluna essencial '{col}' não encontrada no Excel.")
                df[col] = ''
                print(f"Aviso: Coluna '{col}' não encontrada, criada vazia.")

        # Process 'Data Julgamento'
        df['data_julgamento'] = pd.to_datetime(df['data_julgamento'], errors='coerce')
        df.dropna(subset=['data_julgamento'], inplace=True) # Remove rows where date conversion failed
        df['ano_julgamento'] = df['data_julgamento'].dt.year
        df['mes_julgamento'] = df['data_julgamento'].dt.month
        df['ano_mes_julgamento'] = df['data_julgamento'].dt.strftime('%Y-%m')

        # Fill NaNs in text columns
        text_cols = ['Título', 'tese_julgamento', 'ramo_direito', 'classe_processo', 'Resumo', 'Legislação']
        for col in text_cols:
            if col in df.columns:
                df[col] = df[col].fillna('')

        # Process 'numero_informativo'
        if 'numero_informativo' in df.columns:
             df['numero_informativo'] = pd.to_numeric(df['numero_informativo'], errors='coerce')
             df['numero_informativo'] = df['numero_informativo'].astype('Int64').astype(str).replace('<NA>', '')

        # Process 'repercussao_geral'
        if 'repercussao_geral' in df.columns:
            df['repercussao_geral'] = df['repercussao_geral'].fillna('Não Informado')
            df['repercussao_geral'] = df['repercussao_geral'].replace({'Sim': 'Sim', 'Não': 'Não'}, regex=False)
            df.loc[~df['repercussao_geral'].isin(['Sim', 'Não']), 'repercussao_geral'] = 'Não Informado'
        else:
            df['repercussao_geral'] = 'Não Informado'

        # Add unique ID
        if 'id' not in df.columns:
            df['id'] = range(len(df))
        df['id'] = df['id'].astype(str)

        # Process 'Ramo Direito' (Split and Explode)
        if 'ramo_direito' in df.columns:
            df['ramo_direito'] = df['ramo_direito'].astype(str).str.split(';').apply(lambda x: [item.strip() for item in x if item.strip()])
            df_exploded = df.explode('ramo_direito')
        else:
            df['ramo_direito'] = ''
            df_exploded = df
            
        # Map 'Ramo Direito' to 'Área de Estudo'
        if 'ramo_direito' in df_exploded.columns:
            df_exploded['area_estudo'] = df_exploded['ramo_direito'].map(RAMO_TO_AREA_MAP).fillna(DEFAULT_AREA)
        else:
            df_exploded['area_estudo'] = DEFAULT_AREA

        print(f"Colunas finais: {df_exploded.columns.tolist()}")
        print(f"Número de linhas final: {len(df_exploded)}")
        
        # Ensure data is within 2021-2025 (redundant if input file is already filtered, but safe)
        df_exploded = df_exploded[(df_exploded['ano_julgamento'] >= 2021) & (df_exploded['ano_julgamento'] <= 2025)]
        print(f"Número de linhas após filtro final 2021-2025: {len(df_exploded)}")
        
        return df_exploded

    except FileNotFoundError:
        st.error(f"Erro: Arquivo Excel não encontrado em {excel_path}")
        return None
    except ValueError as ve:
        st.error(f"Erro de Valor: {ve}")
        return None
    except Exception as e:
        st.error(f"Erro ao carregar ou processar os dados do Excel: {e}")
        return None

# --- Funções de Callback --- 
def select_julgado_for_assertiva(julgado_id):
    st.session_state.selected_julgado_id_assertiva = julgado_id
    st.session_state.selected_julgado_id_caso = None
    st.session_state.show_caso_pratico_dialog = False
    st.toast(f"Julgado ID {julgado_id} selecionado. Verifique a aba 'Assertivas'.")

def select_julgado_for_caso(julgado_id):
    st.session_state.selected_julgado_id_caso = julgado_id
    st.session_state.selected_julgado_id_assertiva = None
    st.session_state.show_caso_pratico_dialog = True
    st.toast(f"Julgado ID {julgado_id} selecionado para 'Caso Prático'. Veja abaixo.")

def toggle_favorite(julgado_id):
    if julgado_id in st.session_state.favorites:
        st.session_state.favorites.remove(julgado_id)
        st.toast(f"Julgado ID {julgado_id} removido dos favoritos.")
    else:
        st.session_state.favorites.add(julgado_id)
        st.toast(f"Julgado ID {julgado_id} adicionado aos favoritos.")

def select_meta_julgado(julgado_id):
    st.session_state.selected_meta_julgado_id = julgado_id
    st.toast(f"Exibindo detalhes do julgado ID {julgado_id} da meta.")

# --- Componentes de Visualização (Atualizado V5) ---
def render_card(row, context="informativos"):
    date_str = row['data_julgamento'].strftime('%d/%m/%Y') if pd.notna(row['data_julgamento']) else 'Data Indisponível'
    card_title = f"**{row['Título']}** (Inf. {row['numero_informativo']} - {date_str})"
    is_favorite = row['id'] in st.session_state.favorites
    favorite_icon = "⭐" if is_favorite else "☆"
    
    key_prefix = f"{context}_{row['id']}"
    expanded_default = (context == 'meta')

    with st.expander(card_title, expanded=expanded_default):
        st.button(f"{favorite_icon} Favorito", key=f"fav_{key_prefix}", on_click=toggle_favorite, args=(row['id'],), help="Adicionar/Remover dos Favoritos")
        st.markdown(f"**Classe:** {row['classe_processo']}")
        # Get all ramos/areas for the original julgado ID from the main dataframe
        all_ramos = df_informativos_exploded[df_informativos_exploded['id'] == row['id']]['ramo_direito'].unique()
        all_areas = df_informativos_exploded[df_informativos_exploded['id'] == row['id']]['area_estudo'].unique()
        st.markdown(f"**Ramo(s) do Direito:** {', '.join(all_ramos)}")
        st.markdown(f"**Área(s) de Estudo:** {', '.join(all_areas)}")
        
        st.markdown("**Tese / Notícia Completa:**")
        st.markdown(row['tese_julgamento'])
        
        if row['Resumo'] and row['Resumo'] != row['tese_julgamento']:
            st.markdown("**Resumo:**")
            st.markdown(row['Resumo'])
            
        if row['Legislação']:
            st.markdown(f"**Legislação:** {row['Legislação']}")
        st.markdown(f"**Repercussão Geral:** {row['repercussao_geral']}")
        
        if context == "informativos":
            col1, col2 = st.columns(2)
            with col1:
                st.button("Gerar Assertivas", key=f"assertiva_{key_prefix}", on_click=select_julgado_for_assertiva, args=(row['id'],))
            with col2:
                st.button("Ver Caso Prático", key=f"caso_{key_prefix}", on_click=select_julgado_for_caso, args=(row['id'],))

def render_table(df):
    cols_to_show = {
        'numero_informativo': 'Informativo',
        'data_julgamento': 'Data',
        'Título': 'Título',
        'classe_processo': 'Classe',
        'ramo_direito': 'Ramo Direito',
        'area_estudo': 'Área Estudo',
        'repercussao_geral': 'RG'
    }
    existing_cols = [col for col in cols_to_show.keys() if col in df.columns]
    df_display = df[existing_cols].rename(columns=cols_to_show)
    if 'Data' in df_display.columns:
        df_display['Data'] = df_display['Data'].dt.strftime('%d/%m/%Y')
    st.dataframe(df_display, use_container_width=True)

# --- Carregar Dados ---
data_path = "Dados_InformativosSTF_2021-2025.xlsx" # Use the filtered Excel file path
df_informativos_exploded = load_data(data_path)

# --- Estrutura Principal do App (Atualizado V5) ---
if df_informativos_exploded is not None:
    st.success(f"{df_informativos_exploded['id'].nunique()} julgados únicos ({len(df_informativos_exploded)} linhas/ramos) carregados (2021-2025).")

    # --- Barra Lateral (Sidebar) --- Filters for main view
    st.sidebar.header("Filtros Principais")
    anos_disponiveis = sorted(df_informativos_exploded['ano_julgamento'].dropna().unique().astype(int), reverse=True)
    meses_anos_disponiveis = sorted(df_informativos_exploded['ano_mes_julgamento'].dropna().unique(), reverse=True)
    ramos_disponiveis = sorted(df_informativos_exploded['ramo_direito'].dropna().unique())
    areas_disponiveis = sorted(df_informativos_exploded['area_estudo'].dropna().unique())
    classes_disponiveis = sorted(df_informativos_exploded['classe_processo'].dropna().unique())
    informativos_disponiveis = sorted(df_informativos_exploded.drop_duplicates(subset=['id'])['numero_informativo'].dropna().unique())
    rg_options = ['Todos', 'Sim', 'Não', 'Não Informado']

    date_filter_type = st.sidebar.radio("Filtrar Data Por:", ["Ano", "Mês/Ano"], index=0, key="sidebar_date_filter")
    selected_anos = []
    selected_meses_anos = []
    if date_filter_type == "Ano":
        selected_anos = st.sidebar.multiselect("Ano do Julgamento", anos_disponiveis, default=anos_disponiveis, key="sidebar_ano")
    else:
        selected_meses_anos = st.sidebar.multiselect("Mês/Ano do Julgamento", meses_anos_disponiveis, default=[], key="sidebar_mes_ano")

    selected_areas = st.sidebar.multiselect("Área de Estudo (Simulado IA)", areas_disponiveis, default=[], key="sidebar_area")
    selected_ramos = st.sidebar.multiselect("Ramo do Direito (Específico)", ramos_disponiveis, default=[], key="sidebar_ramo")
    selected_classes = st.sidebar.multiselect("Classe Processual", classes_disponiveis, default=[], key="sidebar_classe")
    selected_informativo = st.sidebar.selectbox("Número do Informativo (opcional)", ["Todos"] + informativos_disponiveis, index=0, key="sidebar_inf")
    selected_rg = st.sidebar.radio("Repercussão Geral", rg_options, index=0, key="sidebar_rg")
    show_favorites_only = st.sidebar.checkbox("Mostrar Apenas Favoritos", value=False, key="sidebar_fav")

    # Aplicar Filtros da Sidebar
    df_filtered_sidebar = df_informativos_exploded.copy()
    if date_filter_type == "Ano" and selected_anos:
        df_filtered_sidebar = df_filtered_sidebar[df_filtered_sidebar['ano_julgamento'].isin(selected_anos)]
    elif date_filter_type == "Mês/Ano" and selected_meses_anos:
        df_filtered_sidebar = df_filtered_sidebar[df_filtered_sidebar['ano_mes_julgamento'].isin(selected_meses_anos)]
    if selected_areas:
        df_filtered_sidebar = df_filtered_sidebar[df_filtered_sidebar['area_estudo'].isin(selected_areas)]
    if selected_ramos:
        df_filtered_sidebar = df_filtered_sidebar[df_filtered_sidebar['ramo_direito'].isin(selected_ramos)]
    if selected_classes:
        df_filtered_sidebar = df_filtered_sidebar[df_filtered_sidebar['classe_processo'].isin(selected_classes)]
    if selected_informativo != "Todos":
        df_filtered_sidebar = df_filtered_sidebar[df_filtered_sidebar['numero_informativo'] == selected_informativo]
    if selected_rg != "Todos":
        df_filtered_sidebar = df_filtered_sidebar[df_filtered_sidebar['repercussao_geral'] == selected_rg]
    if show_favorites_only:
        df_filtered_sidebar = df_filtered_sidebar[df_filtered_sidebar['id'].isin(st.session_state.favorites)]

    st.sidebar.metric("Julgados Filtrados (Ramos Individuais)", len(df_filtered_sidebar))
    st.sidebar.metric("Julgados Únicos Filtrados", df_filtered_sidebar['id'].nunique())

    # --- Abas --- 
    tabs = ["🔍 Informativos", "📊 Estatísticas", "✅ Assertivas", "❓ Perguntas", "🎯 Metas de Estudo"]
    tab1, tab2, tab3, tab4, tab5 = st.tabs(tabs)

    with tab1:
        st.header("Consulta aos Informativos")
        search_query = st.text_input("Buscar por palavra-chave", placeholder="Digite termos para buscar no Título, Tese/Notícia ou Resumo...")
        df_final_filtered = df_filtered_sidebar.copy()
        if search_query:
            search_mask = (df_final_filtered['Título'].str.contains(search_query, case=False, regex=True, na=False) |
                           df_final_filtered['tese_julgamento'].str.contains(search_query, case=False, regex=True, na=False) |
                           df_final_filtered['Resumo'].str.contains(search_query, case=False, regex=True, na=False))
            df_final_filtered = df_final_filtered[search_mask]
            st.write(f"Mostrando {df_final_filtered['id'].nunique()} julgados únicos ({len(df_final_filtered)} linhas/ramos) que correspondem à busca ")
        else:
            st.write(f"Mostrando {df_final_filtered['id'].nunique()} julgados únicos ({len(df_final_filtered)} linhas/ramos) com base nos filtros.")
        
        view_mode = st.radio("Modo de Visualização:", ["Cards", "Tabela"], horizontal=True, label_visibility="collapsed")

        # --- Diálogo/Modal para Caso Prático ---
        if st.session_state.show_caso_pratico_dialog and st.session_state.selected_julgado_id_caso:
            try:
                julgado_caso = df_final_filtered[df_final_filtered['id'] == st.session_state.selected_julgado_id_caso].iloc[0]

                # --- Integration Point for GPT-4 Case Study ---
                with st.container(border=True):
                    st.subheader(f"Caso Prático (Gerado por IA - GPT-4) - {julgado_caso['Título']}")
                    st.markdown(f"**Baseado no Informativo:** {julgado_caso['numero_informativo']} | **Data:** {julgado_caso['data_julgamento'].strftime('%d/%m/%Y') if pd.notna(julgado_caso['data_julgamento']) else 'N/A'}")
                    st.divider() # Divider inside container header

                    # Check API Key and make call
                    if not openai_api_key:
                        st.error("Chave da API OpenAI não configurada. Configure-a nos segredos do Streamlit (st.secrets) para usar esta funcionalidade.")
                    else:
                        # Use a session state variable to store the generated case to avoid re-generation on every interaction
                        session_key_caso = f"caso_pratico_{st.session_state.selected_julgado_id_caso}"
                        if session_key_caso not in st.session_state:
                            st.session_state[session_key_caso] = None # Initialize

                        if st.session_state[session_key_caso] is None: # Only generate if not already generated
                            st.info("Gerando caso prático com a API OpenAI (GPT-4)... Por favor, aguarde.")
                            try:
                                prompt = f"""
                                Com base na seguinte tese/notícia de julgado do Supremo Tribunal Federal (STF), crie um caso prático realista e detalhado, adequado para estudo de concursos públicos. O caso deve ilustrar a aplicação da tese em uma situação concreta. Inclua personagens, um cenário e uma pergunta final sobre como o julgado do STF se aplica à situação.

                                **Texto do Julgado:**
                                {julgado_caso['tese_julgamento']}

                                **Formato da Resposta Esperado (use markdown):**

                                **Situação Hipotética:**
                                [Descrição detalhada do cenário e dos personagens envolvidos]

                                **Pergunta:**
                                [Pergunta clara sobre a aplicação do julgado STF ao caso]
                                """

                                response = openai.chat.completions.create(
                                    model="gpt-4",
                                    messages=[{{"role": "user", "content": prompt}}],
                                    temperature=0.7 # More creative for case studies
                                )
                                st.session_state[session_key_caso] = response.choices[0].message.content
                            except openai.AuthenticationError:
                                 st.error("Erro de autenticação com a API OpenAI. Verifique se sua chave de API está correta e configurada nos segredos do Streamlit.")
                                 st.session_state[session_key_caso] = "ERROR" # Mark as error to prevent retry loop
                            except openai.RateLimitError:
                                 st.error("Limite de taxa da API OpenAI excedido. Tente novamente mais tarde.")
                                 st.session_state[session_key_caso] = "ERROR"
                            except Exception as e:
                                st.error(f"Erro ao chamar a API OpenAI: {str(e)}")
                                st.session_state[session_key_caso] = "ERROR"

                        # Display the generated case (or error message if generation failed)
                        if st.session_state[session_key_caso] and st.session_state[session_key_caso] != "ERROR":
                            st.markdown(st.session_state[session_key_caso])
                        elif st.session_state[session_key_caso] == "ERROR":
                            st.warning("Não foi possível gerar o caso prático devido a um erro na API.")


                    # Close button remains the same
                    if st.button("Fechar Caso Prático", key=f"close_caso_{st.session_state.selected_julgado_id_caso}"):
                        st.session_state.show_caso_pratico_dialog = False
                        # Clear the generated case from session state when closing
                        session_key_caso_to_clear = f"caso_pratico_{st.session_state.selected_julgado_id_caso}"
                        if session_key_caso_to_clear in st.session_state:
                             del st.session_state[session_key_caso_to_clear]
                        st.session_state.selected_julgado_id_caso = None # Clear selected ID *after* using it to clear the cache
                        st.rerun()
                # --- End Integration ---

            except IndexError:
                st.warning("Julgado selecionado para caso prático não encontrado nos dados filtrados/buscados.")
                st.session_state.show_caso_pratico_dialog = False
                st.session_state.selected_julgado_id_caso = None

        # --- Exibição dos Resultados ---
        df_display_unique = df_final_filtered.drop_duplicates(subset=['id'])
        if view_mode == "Cards":
            st.write("**Resultados em Cards:**")
            if not df_display_unique.empty:
                limit = 10
                for index, row in df_display_unique.head(limit).iterrows():
                    render_card(row, context="informativos")
                if len(df_display_unique) > limit:
                    st.caption(f"Mostrando os primeiros {limit} de {len(df_display_unique)} julgados únicos.")
            else:
                st.info("Nenhum informativo encontrado com os filtros e busca aplicados.")
        else:
            st.write("**Resultados em Tabela (Ramos Individuais):**")
            if not df_final_filtered.empty:
                render_table(df_final_filtered)
            else:
                st.info("Nenhum informativo encontrado com os filtros e busca aplicados.")

    with tab2:
        st.header("Estatísticas Gerais")
        st.write(f"Visualizações sobre os {df_filtered_sidebar['id'].nunique()} julgados únicos ({len(df_filtered_sidebar)} linhas/ramos) filtrados pela barra lateral.")
        if not df_filtered_sidebar.empty:
            col1, col2 = st.columns(2)
            with col1:
                st.subheader("Julgados por Ramo do Direito")
                chart_ramo = alt.Chart(df_filtered_sidebar).mark_bar().encode(
                    x=alt.X('count()', title='Quantidade'),
                    y=alt.Y('ramo_direito', title='Ramo do Direito', sort='-x')
                ).properties(
                    height=alt.Step(15) # Adjust step for better readability
                )
                st.altair_chart(chart_ramo, use_container_width=True)
                
                st.subheader("Julgados Únicos por Ano")
                df_anos_unicos = df_filtered_sidebar.drop_duplicates(subset=['id']).groupby('ano_julgamento').size().reset_index(name='count')
                chart_ano = alt.Chart(df_anos_unicos).mark_line(point=True).encode(
                    x=alt.X('ano_julgamento', title='Ano', axis=alt.Axis(format='d')), # Format as integer
                    y=alt.Y('count', title='Quantidade de Julgados Únicos'),
                    tooltip=['ano_julgamento', 'count']
                ).interactive()
                st.altair_chart(chart_ano, use_container_width=True)

            with col2:
                st.subheader("Julgados por Área de Estudo")
                chart_area = alt.Chart(df_filtered_sidebar).mark_bar().encode(
                    x=alt.X('count()', title='Quantidade'),
                    y=alt.Y('area_estudo', title='Área de Estudo', sort='-x')
                ).properties(
                    height=alt.Step(15) # Adjust step for better readability
                )
                st.altair_chart(chart_area, use_container_width=True)
                
                st.subheader("Repercussão Geral (Julgados Únicos)")
                df_rg_unicos = df_filtered_sidebar.drop_duplicates(subset=['id'])['repercussao_geral'].value_counts().reset_index()
                df_rg_unicos.columns = ['repercussao_geral', 'count']
                chart_rg = alt.Chart(df_rg_unicos).mark_arc(innerRadius=50).encode(
                    theta=alt.Theta(field="count", type="quantitative"),
                    color=alt.Color(field="repercussao_geral", type="nominal", title="RG"),
                    tooltip=['repercussao_geral', 'count']
                ).properties(
                    title='Distribuição de RG'
                )
                st.altair_chart(chart_rg, use_container_width=True)
        else:
            st.info("Não há dados filtrados (sidebar) para exibir estatísticas.")

    with tab3:
        st.header("Gerador de Assertivas")
        if st.session_state.selected_julgado_id_assertiva:
            try:
                julgado_assertiva = df_informativos_exploded[df_informativos_exploded['id'] == st.session_state.selected_julgado_id_assertiva].iloc[0]
                st.subheader(f"Julgado Selecionado: {julgado_assertiva['Título']}")
                st.markdown(f"**Informativo:** {julgado_assertiva['numero_informativo']} | **Data:** {julgado_assertiva['data_julgamento'].strftime('%d/%m/%Y') if pd.notna(julgado_assertiva['data_julgamento']) else 'N/A'}")
                st.markdown("**Tese / Notícia:**")
                st.markdown(julgado_assertiva['tese_julgamento'])
                st.divider()
                # --- Integração API GPT-4 para Assertivas ---
                if st.button("Gerar 5 Assertivas com a Result", key=f"gen_assert_{st.session_state.selected_julgado_id_assertiva}"):
                    if not openai_api_key: # Check if key is loaded from secrets
                        st.error("Chave da API OpenAI não configurada. Configure-a nos segredos do Streamlit (st.secrets) para usar esta funcionalidade.")
                    else:
                        st.info("Gerando assertivas com a Result... Por favor, aguarde.")
                        try:
                            prompt = f"""
                            Com base na seguinte tese/notícia de julgado do Supremo Tribunal Federal (STF), gere exatamente 5 (cinco) assertivas distintas e relevantes no formato 'Certo/Errado' para fins de estudo para concursos públicos. Para cada assertiva, indique claramente o gabarito ('Certo' ou 'Errado') e uma breve justificativa concisa (máximo 1-2 frases) baseada **exclusivamente** no texto fornecido.

                            **Texto do Julgado:**
                            {julgado_assertiva['tese_julgamento']}

                            **Formato da Resposta Esperado (use markdown):**

                            **1. Assertiva:** [Texto da assertiva 1]
                               **Gabarito:** [Certo/Errado]
                               **Justificativa:** [Breve justificativa 1]

                            **2. Assertiva:** [Texto da assertiva 2]
                               **Gabarito:** [Certo/Errado]
                               **Justificativa:** [Breve justificativa 2]

                            **3. Assertiva:** [Texto da assertiva 3]
                               **Gabarito:** [Certo/Errado]
                               **Justificativa:** [Breve justificativa 3]

                            **4. Assertiva:** [Texto da assertiva 4]
                               **Gabarito:** [Certo/Errado]
                               **Justificativa:** [Breve justificativa 4]

                            **5. Assertiva:** [Texto da assertiva 5]
                               **Gabarito:** [Certo/Errado]
                               **Justificativa:** [Breve justificativa 5]
                            """

                            response = openai.ChatCompletion.create(
                                model="gpt-4", # Use GPT-4 as requested
                                messages=[{{"role": "user", "content": prompt}}],
                                temperature=0.5 # Slightly creative but mostly factual
                            )

                            resposta_texto = response.choices[0].message.content
                            st.markdown("---")
                            st.markdown("**Assertivas Geradas (GPT-4):**")
                            st.markdown(resposta_texto) # Display the raw response formatted by the prompt

                        except openai.AuthenticationError:
                             st.error("Erro de autenticação com a API OpenAI. Verifique se sua chave de API está correta e configurada nos segredos do Streamlit.")
                        except openai.RateLimitError:
                             st.error("Limite de taxa da API OpenAI excedido. Tente novamente mais tarde.")
                        except Exception as e:
                            st.error(f"Erro ao chamar a API OpenAI: {str(e)}")
                # --- Fim Integração API ---
            except IndexError:
                st.warning("Julgado selecionado para assertivas não encontrado.")
                st.session_state.selected_julgado_id_assertiva = None
        else:
            st.info("Selecione um julgado na aba '🔍 Informativos' usando o botão 'Gerar Assertivas'.")

    with tab4:
        st.header("Perguntas sobre os Julgados")
        st.info("Faça uma pergunta sobre os julgados atualmente filtrados/buscados na aba '🔍 Informativos'.")
        user_question = st.text_input("Sua pergunta:", key="user_q")
        if st.button("Buscar Resposta com a Result", key="ask_q"):
            if user_question:
                if not openai_api_key:
                    st.error("Chave da API OpenAI não configurada. Configure-a nos segredos do Streamlit (st.secrets) para usar esta funcionalidade.")
                else:
                    st.info("Buscando resposta com a Result... Por favor, aguarde.")
                    try:
                        # Preparar contexto (ex: 5 primeiras teses únicas filtradas)
                        # Using drop_duplicates on ID before head to avoid sending near-identical context due to ramo explosion
                        contexto_df = df_final_filtered.drop_duplicates(subset=["id"]).head(5)
                        contexto_list = contexto_df["tese_julgamento"].tolist()
                        contexto_str = "\n\n---\n\n".join([f"**Julgado {i+1} (ID: {contexto_df.iloc[i]["id"]})**:\n{tese}" for i, tese in enumerate(contexto_list)])

                        if not contexto_str:
                            contexto_str = "Nenhum julgado relevante encontrado nos filtros atuais."

                        prompt = f"""
                        Você é um assistente especialista em jurisprudência do STF. Responda à pergunta do usuário baseando-se **estrita e exclusivamente** nos trechos de julgados do STF fornecidos abaixo como contexto. Não adicione informações externas ou opiniões.

                        **Pergunta do Usuário:**
                        {user_question}

                        **Contexto (Julgados Filtrados):**
                        {contexto_str}

                        **Instruções para Resposta:**
                        1. Analise a pergunta e o contexto fornecido.
                        2. Se a resposta puder ser encontrada diretamente no contexto, forneça-a de forma clara e concisa, citando qual julgado (se possível) contém a informação.
                        3. Se a resposta não puder ser encontrada no contexto fornecido, responda **exclusivamente**: "Não foi possível encontrar a resposta para esta pergunta no contexto dos julgados fornecidos."
                        4. Não invente informações nem faça suposições.
                        """

                        response = openai.chat.completions.create(
                            model="gpt-4",
                            messages=[{{"role": "user", "content": prompt}}],
                            temperature=0.2 # Low temperature for factual answers based on context
                        )
                        resposta_texto = response.choices[0].message.content
                        st.markdown("---")
                        st.markdown("**Resposta (GPT-4):**")
                        st.markdown(resposta_texto)

                    except openai.AuthenticationError:
                         st.error("Erro de autenticação com a API OpenAI. Verifique se sua chave de API está correta e configurada nos segredos do Streamlit.")
                    except openai.RateLimitError:
                         st.error("Limite de taxa da API OpenAI excedido. Tente novamente mais tarde.")
                    except Exception as e:
                        st.error(f"Erro ao chamar a API OpenAI: {e}")
            else:
                st.warning("Por favor, digite sua pergunta.")
        # --- Fim Integração API ---
            
    with tab5: # Metas de Estudo Tab (Atualizado V5 - Filtered Metas)
        st.header("🎯 Metas de Estudo")
        st.write("Defina filtros e a quantidade de julgados aleatórios para sua meta de leitura.")
        
        # --- Filtros para Metas ---
        st.subheader("Filtrar Julgados para a Meta (Opcional)")
        meta_col1, meta_col2 = st.columns(2)
        with meta_col1:
            # Use session state to store filter selections
            st.session_state.meta_filter_anos = st.multiselect("Ano(s) para Meta", anos_disponiveis, default=st.session_state.meta_filter_anos, key="meta_ano")
            st.session_state.meta_filter_areas = st.multiselect("Área(s) para Meta", areas_disponiveis, default=st.session_state.meta_filter_areas, key="meta_area")
        with meta_col2:
            st.session_state.meta_filter_ramos = st.multiselect("Ramo(s) para Meta", ramos_disponiveis, default=st.session_state.meta_filter_ramos, key="meta_ramo")
            # Add more filters here if needed (e.g., Classe, RG)
        
        # Apply Meta Filters
        df_meta_filtered = df_informativos_exploded.copy()
        if st.session_state.meta_filter_anos:
            df_meta_filtered = df_meta_filtered[df_meta_filtered['ano_julgamento'].isin(st.session_state.meta_filter_anos)]
        if st.session_state.meta_filter_areas:
            df_meta_filtered = df_meta_filtered[df_meta_filtered['area_estudo'].isin(st.session_state.meta_filter_areas)]
        if st.session_state.meta_filter_ramos:
            df_meta_filtered = df_meta_filtered[df_meta_filtered['ramo_direito'].isin(st.session_state.meta_filter_ramos)]
            
        num_julgados_disponiveis = df_meta_filtered['id'].nunique()
        st.caption(f"{num_julgados_disponiveis} julgados únicos disponíveis com os filtros de meta aplicados.")
        st.divider()
        
        # --- Geração da Meta ---
        st.subheader("Gerar Meta")
        num_blocos = st.number_input("Quantidade de Julgados para Ler:", min_value=1, max_value=max(1, num_julgados_disponiveis), value=min(5, max(1, num_julgados_disponiveis)), step=1, key="meta_num")
        
        if st.button("Gerar Meta de Leitura Aleatória", key="meta_gen"):
            st.info(f"Gerando {num_blocos} julgados aleatórios com base nos filtros de meta...")
            available_julgados = df_meta_filtered.drop_duplicates(subset=['id'])
            if len(available_julgados) >= num_blocos:
                sampled_ids = random.sample(available_julgados['id'].tolist(), num_blocos)
                st.session_state.current_study_meta_ids = sampled_ids
                st.session_state.selected_meta_julgado_id = None
            elif not available_julgados.empty():
                 st.warning(f"Não há {num_blocos} julgados únicos disponíveis com os filtros de meta. Mostrando {len(available_julgados)}.")
                 st.session_state.current_study_meta_ids = available_julgados['id'].tolist()
                 st.session_state.selected_meta_julgado_id = None
            else:
                st.warning("Nenhum julgado disponível com os filtros de meta aplicados.")
                st.session_state.current_study_meta_ids = []
                st.session_state.selected_meta_julgado_id = None
            st.rerun()

        # --- Exibição da Meta e Detalhes ---
        if st.session_state.current_study_meta_ids:
            st.subheader("Sua Meta de Leitura Atual:")
            # Get the details for the selected meta IDs from the original (exploded) dataframe
            meta_julgados_df = df_informativos_exploded[df_informativos_exploded['id'].isin(st.session_state.current_study_meta_ids)].drop_duplicates(subset=['id'])
            
            # Display buttons horizontally
            cols = st.columns(len(meta_julgados_df))
            for i, (index, row) in enumerate(meta_julgados_df.iterrows()):
                date_str = row['data_julgamento'].strftime('%d/%m/%Y') if pd.notna(row['data_julgamento']) else 'N/A'
                button_label = f"Inf. {row['numero_informativo']} ({date_str})"
                with cols[i]:
                     if st.button(button_label, key=f"meta_select_{row['id']}", on_click=select_meta_julgado, args=(row['id'],), use_container_width=True):
                         pass

            st.divider()
            # Display the selected julgado's card
            if st.session_state.selected_meta_julgado_id:
                try:
                    selected_row = meta_julgados_df[meta_julgados_df['id'] == st.session_state.selected_meta_julgado_id].iloc[0]
                    st.subheader("Detalhes do Julgado Selecionado:")
                    render_card(selected_row, context="meta")
                except IndexError:
                    st.warning("Julgado selecionado não encontrado na meta atual.")
                    st.session_state.selected_meta_julgado_id = None

else:
    st.warning("Não foi possível carregar os dados dos informativos. Verifique o arquivo Excel e as mensagens de erro acima.")

