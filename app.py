import streamlit as st
import pandas as pd
import plotly.graph_objects as go

# Configuração da página
st.set_page_config(page_title="Dashboard Reclame Aqui", layout="wide")

# Carregamento de dados (substitua pelo nome do seu arquivo)
@st.cache_data
def load_data():
    df = pd.read_csv("sua_planilha.csv") # Ou st.secrets para carregar do Google Sheets
    # Tratamento de datas
    df['Data da entrada'] = pd.to_datetime(df['Data da entrada'], dayfirst=True)
    return df

df = load_data()

st.title("📊 Monitoramento de Reputação - Reclame Aqui")

# --- SEÇÃO 1: MÉTRICAS RECLAME AQUI ---
st.header("🎯 Índices de Reputação")
col1, col2, col3, col4 = st.columns(4)

# Cálculos das métricas
total_reclamacoes = len(df)
respondidas = df[df['Status'] == 'Respondida'].shape[0]
resolvidas = df[df['Seu problema foi resolvido?'] == 'Sim'].shape[0]
voltariam = df[df['Voltaria a fazer negócio?'] == 'Sim'].shape[0]
avaliadas = df['Nota do consumidor'].dropna().shape[0]

with col1:
    indice_resp = (respondidas / total_reclamacoes) * 100
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

# --- SEÇÃO 2: ANÁLISE DE PARETO ---
st.markdown("---")
st.header("📉 Análise de Pareto: Causas de Notas Baixas")

# Filtrando notas ruins (abaixo de 5)
df_ruim = df[df['Nota_do_consumidor'] <= 5].copy()
pareto_df = df_ruim['Causa do problema'].value_counts().reset_index()
pareto_df.columns = ['Causa', 'Frequencia']
pareto_df['Percentual_Acumulado'] = (pareto_df['Frequencia'].cumsum() / pareto_df['Frequencia'].sum()) * 100

fig = go.Figure()
# Barras
fig.add_trace(go.Bar(x=pareto_df['Causa'], y=pareto_df['Frequencia'], name="Frequência"))
# Linha de acumulado
fig.add_trace(go.Scatter(x=pareto_df['Causa'], y=pareto_df['Percentual_Acumulado'], 
                         name="% Acumulado", yaxis="y2", line=dict(color="#FF4B4B", width=3)))

fig.update_layout(
    title="Onde estão os 20% que geram 80% dos problemas?",
    yaxis=dict(title="Número de Reclamações"),
    yaxis2=dict(title="Percentual Acumulado", overlaying="y", side="right", range=[0, 105]),
    showlegend=False
)
st.plotly_chart(fig, use_container_width=True)

# --- SEÇÃO 3: ALERTA PREDITIVO (O Diferencial) ---
st.markdown("---")
st.header("🚨 Sistema de Alerta Preditivo (Blindagem da Nota)")

# Simulando lógica de risco: Reclamações que ainda não foram fechadas ou sem solução rápida
# Aqui usamos a 'Data da entrada' e verificamos se há 'Data de fechamento'
df['Atraso_Dias'] = (pd.Timestamp.now() - df['Data da entrada']).dt.days
risco_critico = df[(df['Status'] != 'Finalizada') & (df['Atraso_Dias'] > 2)]

c1, c2 = st.columns([1, 2])
with c1:
    st.warning(f"Existem {len(risco_critico)} casos em risco de virar detração pública.")
    st.info("Ação Recomendada: Priorizar tratativa desses IDs nas próximas 24h para manter a nota 9,2.")

with c2:
    st.dataframe(risco_critico[['ID', 'Causa do problema', 'Atraso_Dias']].sort_values('Atraso_Dias', ascending=False))