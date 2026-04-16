import streamlit as st
import pandas as pd
import plotly.graph_objects as go

# Configuração da página
st.set_page_config(page_title="Dashboard Reclame Aqui - GoCase", layout="wide")

# --- CARREGAMENTO DE DADOS ---
@st.cache_data
def load_data():
    # Link de exportação do Google Sheets
    SHEET_ID = "1Yvh10bGlAOb_7Zd6X5y83rVaYOsWpMcoAZ2eGT82CRM"
    GID = "1454011321"
    url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid={GID}"
    
    # Lendo os dados
    df = pd.read_csv(url)
    
    # Tratamento de datas
    df['Data da entrada'] = pd.to_datetime(df['Data da entrada'], dayfirst=True, errors='coerce')
    
    # Garantindo que a nota seja numérica
    df['Nota do consumidor'] = pd.to_numeric(df['Nota do consumidor'], errors='coerce')
    
    # Cálculo de atraso em dias (coluna auxiliar)
    hoje = pd.Timestamp.now()
    df['Atraso_Dias'] = (hoje - df['Data da entrada']).dt.days
    
    return df

# Tenta carregar os dados
try:
    df = load_data()
except Exception as e:
    st.error(f"Erro ao conectar com o Google Sheets. Verifique se a planilha está 'Publicada na Web'. Erro: {e}")
    st.stop()

st.title("📊 Monitoramento Estratégico - Reclame Aqui")

# --- SEÇÃO 1: MÉTRICAS RECLAME AQUI ---
st.header("🎯 Visão Geral do Atendimento")

# Cálculos Base
total_reclamacoes = len(df)
total_avaliacoes = df['Nota do consumidor'].dropna().shape[0]
total_usuarios = df['E-mail'].nunique() # Conta e-mails únicos para saber o real número de clientes
resolvidas_abs = df[df['Seu problema foi resolvido?'] == 'Sim'].shape[0]
voltariam_abs = df[df['Voltaria a fazer negócio?'] == 'Sim'].shape[0]
respondidas = df[df['Status'].str.contains('Respondida', na=False, case=False)].shape[0]

# --- Linha 1: Números Absolutos ---
st.subheader("📊 Volumes Totais")
c1, c2, c3, c4 = st.columns(4)

with c1:
    st.metric("Total de Avaliações", total_avaliacoes, help=f"De um total de {total_reclamacoes} reclamações recebidas.")
with c2:
    st.metric("Usuários Únicos", total_usuarios, help="Calculado com base nos e-mails únicos da planilha.")
with c3:
    st.metric("Problemas Resolvidos", resolvidas_abs)
with c4:
    st.metric("Voltariam a Comprar", voltariam_abs)

# --- Linha 2: Índices Percentuais ---
st.subheader("🎯 Índices de Reputação")
col1, col2, col3, col4 = st.columns(4)

with col1:
    indice_resp = (respondidas / total_reclamacoes) * 100 if total_reclamacoes > 0 else 0
    st.metric("Índice de Resposta", f"{indice_resp:.1f}%", delta="Meta: 100%")

with col2:
    indice_solu = (resolvidas_abs / total_avaliacoes) * 100 if total_avaliacoes > 0 else 0
    st.metric("Índice de Solução", f"{indice_solu:.1f}%", delta="Meta: > 90%")

with col3:
    nota_media = df['Nota do consumidor'].mean()
    st.metric("Média das Avaliações", f"{nota_media:.2f}/10")

with col4:
    indice_negocios = (voltariam_abs / total_avaliacoes) * 100 if total_avaliacoes > 0 else 0
    st.metric("Novos Negócios", f"{indice_negocios:.1f}%")

# --- SEÇÃO 2: ANÁLISE DE PARETO COM LINHA DE CORTE ---
st.markdown("---")
st.header("📉 Análise de Pareto: Causas das Notas Baixas")

# Filtrando notas ruins (menores ou iguais a 5)
df_ruim = df[df['Nota do consumidor'] <= 5].copy()

if not df_ruim.empty:
    # Contagem por Causa do Problema
    pareto_df = df_ruim['Causa do problema'].value_counts().reset_index()
    pareto_df.columns = ['Causa', 'Frequencia']
    
    # Cálculo do percentual acumulado
    pareto_df['Percentual_Acumulado'] = (pareto_df['Frequencia'].cumsum() / pareto_df['Frequencia'].sum()) * 100

    fig = go.Figure()
    
    # Barras (Frequência)
    fig.add_trace(go.Bar(
        x=pareto_df['Causa'], 
        y=pareto_df['Frequencia'], 
        name="Qtd Reclamações", 
        marker_color='#1f77b4'
    ))
    
    # Linha (Acumulado)
    fig.add_trace(go.Scatter(
        x=pareto_df['Causa'], 
        y=pareto_df['Percentual_Acumulado'], 
        name="% Acumulado", 
        yaxis="y2", 
        line=dict(color="#FF4B4B", width=4)
    ))

    # Adicionando a linha de corte dos 80% de forma segura (Correção aplicada aqui)
    fig.add_shape(
        type="line", 
        x0=0, x1=1, xref="paper", 
        y0=80, y1=80, yref="y2",
        line=dict(color="orange", width=2, dash="dash")
    )
    
    fig.add_annotation(
        x=0.01, xref="paper", 
        y=80, yref="y2",
        text="Corte 80% (Lei de Pareto)",
        showarrow=False, 
        yanchor="bottom", 
        font=dict(color="orange", size=12)
    )

    fig.update_layout(
        title="Quais motivos causam 80% das avaliações negativas?",
        yaxis=dict(title="Número de Reclamações"),
        yaxis2=dict(title="Percentual Acumulado", overlaying="y", side="right", range=[0, 105]),
        xaxis=dict(tickangle=-45),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    st.plotly_chart(fig, use_container_width=True)
    
    # Texto explicativo dinâmico (pega os itens até ~85% para ter uma margem de segurança na visualização)
    top_causas = pareto_df[pareto_df['Percentual_Acumulado'] <= 85]['Causa'].tolist()
    if top_causas:
        st.info(f"💡 **Foco de Atuação:** Resolver as causas **{', '.join(top_causas)}** eliminará a grande maioria (cerca de 80%) das suas notas baixas.")
else:
    st.info("Nenhuma nota baixa registrada para análise.")

# --- SEÇÃO 3: ANÁLISE DE ATRASO POR PRODUTO/MOTIVO ---
st.markdown("---")
col_a, col_b = st.columns([1, 1])

with col_a:
    st.header("🐢 Maiores Atrasos por Causa")
    # Agrupando por causa para ver o tempo médio de espera
    atraso_por_causa = df.groupby('Causa do problema').agg({
        'Atraso_Dias': 'mean',
        'ID': 'count'
    }).rename(columns={'Atraso_Dias': 'Média de Dias Aberto', 'ID': 'Total de Casos'}).sort_values('Média de Dias Aberto', ascending=False)
    
    # Exibe a tabela com gradiente de cor no atraso
    st.dataframe(atraso_por_causa.style.background_gradient(subset=['Média de Dias Aberto'], cmap='YlOrRd'), use_container_width=True)

with col_b:
    st.header("🚨 Chamados Críticos (> 10 dias)")
    # Tabela focada em quem está esquecido no sistema
    casos_criticos = df[df['Status'] != 'Finalizada'].sort_values('Atraso_Dias', ascending=False).head(10)
    
    if not casos_criticos.empty:
        st.table(casos_criticos[['ID', 'Causa do problema', 'Atraso_Dias']])
    else:
        st.success("Não há chamados críticos na fila!")

# --- SEÇÃO 4: ALERTA PREDITIVO ---
st.markdown("---")
st.header("🔔 Alerta de Blindagem de Nota")


# Alerta tudo que passou de 2 dias, exceto as "Respondidas"
risco_critico = df[(df['Status'] != 'Respondida') & (df['Atraso_Dias'] > 2)].copy()

if not risco_critico.empty:
    st.error(f"⚠️ Existem {len(risco_critico)} reclamações com mais de 48h em aberto. Elas têm alto risco de virarem detração pública!")
    with st.expander("Ver lista completa de IDs em risco para atuar hoje"):
        st.dataframe(risco_critico[['ID', 'Data da entrada', 'Causa do problema', 'Atraso_Dias']].sort_values('Atraso_Dias', ascending=False), use_container_width=True)
else:
    st.success("✅ Excelente! Nenhum chamado recente correndo o risco de atraso crítico.")