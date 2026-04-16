import streamlit as st
import pandas as pd
import plotly.graph_objects as go

# Configuração da página
st.set_page_config(page_title="Dashboard Reclame Aqui - GoCase", layout="wide")

# --- CARREGAMENTO DE DADOS ---
@st.cache_data
def load_data():
    SHEET_ID = "1Yvh10bGlAOb_7Zd6X5y83rVaYOsWpMcoAZ2eGT82CRM"
    GID = "1454011321"
    url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid={GID}"
    
    df = pd.read_csv(url)
    df['Data da entrada'] = pd.to_datetime(df['Data da entrada'], dayfirst=True, errors='coerce')
    df['Nota do consumidor'] = pd.to_numeric(df['Nota do consumidor'], errors='coerce')
    
    # Cálculo de atraso em dias (coluna auxiliar)
    hoje = pd.Timestamp.now()
    df['Atraso_Dias'] = (hoje - df['Data da entrada']).dt.days
    
    return df

try:
    df = load_data()
except Exception as e:
    st.error(f"Erro ao conectar com o Google Sheets: {e}")
    st.stop()

st.title("📊 Monitoramento Estratégico - Reclame Aqui")

# --- SEÇÃO 1: MÉTRICAS RECLAME AQUI ---
st.header("🎯 Índices de Reputação")
col1, col2, col3, col4 = st.columns(4)

total_reclamacoes = len(df)
respondidas = df[df['Status'].str.contains('Respondida', na=False, case=False)].shape[0]
resolvidas = df[df['Seu problema foi resolvido?'] == 'Sim'].shape[0]
voltariam = df[df['Voltaria a fazer negócio?'] == 'Sim'].shape[0]
avaliadas = df['Nota do consumidor'].dropna().shape[0]

with col1:
    indice_resp = (respondidas / total_reclamacoes) * 100 if total_reclamacoes > 0 else 0
    st.metric("Índice de Resposta", f"{indice_resp:.1f}%", delta="Meta: 100%")
with col2:
    indice_solu = (resolvidas / avaliadas) * 100 if avaliadas > 0 else 0
    st.metric("Índice de Solução", f"{indice_solu:.1f}%", delta="Meta: > 90%")
with col3:
    nota_media = df['Nota do consumidor'].mean()
    st.metric("Média das Avaliações", f"{nota_media:.2f}/10")
with col4:
    indice_negocios = (voltariam / avaliadas) * 100 if avaliadas > 0 else 0
    st.metric("Novos Negócios", f"{indice_negocios:.1f}%")

# --- SEÇÃO 2: ANÁLISE DE PARETO COM LINHA DE CORTE ---
st.markdown("---")
st.header("📉 Análise de Pareto: Causas das Notas Baixas")

df_ruim = df[df['Nota do consumidor'] <= 5].copy()

if not df_ruim.empty:
    pareto_df = df_ruim['Causa do problema'].value_counts().reset_index()
    pareto_df.columns = ['Causa', 'Frequencia']
    pareto_df['Percentual_Acumulado'] = (pareto_df['Frequencia'].cumsum() / pareto_df['Frequencia'].sum()) * 100

    # Identificar onde atinge os 80% para marcar no gráfico
    causas_80 = pareto_df[pareto_df['Percentual_Acumulado'] <= 85] # Margem para visualização

    fig = go.Figure()
    fig.add_trace(go.Bar(x=pareto_df['Causa'], y=pareto_df['Frequencia'], name="Qtd Reclamações", marker_color='#1f77b4'))
    fig.add_trace(go.Scatter(x=pareto_df['Causa'], y=pareto_df['Percentual_Acumulado'], name="% Acumulado", yaxis="y2", line=dict(color="#FF4B4B", width=4)))

    # Adicionando a linha de corte dos 80%
    fig.add_hline(y=80, line_dash="dash", line_color="orange", annotation_text="Corte 80% (Lei de Pareto)", yaxis="y2")

    fig.update_layout(
        title="Quais motivos causam 80% das avaliações negativas?",
        yaxis=dict(title="Número de Reclamações"),
        yaxis2=dict(title="Percentual Acumulado", overlaying="y", side="right", range=[0, 105]),
        xaxis=dict(tickangle=-45),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    st.plotly_chart(fig, use_container_width=True)
    
    # Texto explicativo dinâmico
    top_causas = pareto_df[pareto_df['Percentual_Acumulado'] <= 81]['Causa'].tolist()
    st.info(f"💡 **Foco de Atuação:** Resolver as causas **{', '.join(top_causas)}** eliminará aproximadamente 80% das suas notas baixas.")
else:
    st.info("Nenhuma nota baixa registrada.")

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
    
    st.dataframe(atraso_por_causa.style.background_gradient(subset=['Média de Dias Aberto'], cmap='YlOrRd'), use_container_width=True)

with col_b:
    st.header("🚨 Chamados Críticos (> 10 dias)")
    # Tabela focada em quem está "esquecido" no sistema
    casos_criticos = df[df['Status'] != 'Finalizada'].sort_values('Atraso_Dias', ascending=False).head(10)
    st.table(casos_criticos[['ID', 'Causa do problema', 'Atraso_Dias']])

# --- SEÇÃO 4: ALERTA PREDITIVO ---
st.markdown("---")
st.header("🔔 Alerta de Blindagem de Nota")
risco_critico = df[(df['Status'] != 'Finalizada') & (df['Atraso_Dias'] > 2)]

if not risco_critico.empty:
    st.error(f"⚠️ Existem {len(risco_critico)} reclamações que podem virar nota baixa se não forem respondidas hoje!")
    with st.expander("Ver lista completa de IDs em risco"):
        st.write(risco_critico[['ID', 'Data da entrada', 'Causa do problema', 'Atraso_Dias']])
else:
    st.success("✅ Nenhum chamado em risco iminente de atraso crítico.")