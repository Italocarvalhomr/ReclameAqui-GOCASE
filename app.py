import streamlit as st
import pandas as pd
import plotly.graph_objects as go

# Configuração da página
st.set_page_config(page_title="Dashboard Reclame Aqui - GoCase", layout="wide")

# --- CARREGAMENTO DE DADOS ---
@st.cache_data
def load_data():
    # Transformando o link de edição em link de exportação CSV
    # O link abaixo é o seu link já convertido para formato de exportação direta
    SHEET_ID = "1Yvh10bGlAOb_7Zd6X5y83rVaYOsWpMcoAZ2eGT82CRM"
    GID = "1454011321"
    url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid={GID}"
    
    # Lendo os dados
    df = pd.read_csv(url)
    
    # Tratamento de datas
    df['Data da entrada'] = pd.to_datetime(df['Data da entrada'], dayfirst=True, errors='coerce')
    
    # Garantindo que a nota seja numérica
    df['Nota do consumidor'] = pd.to_numeric(df['Nota do consumidor'], errors='coerce')
    
    return df

# Tenta carregar os dados
try:
    df = load_data()
except Exception as e:
    st.error(f"Erro ao conectar com o Google Sheets. Verifique se a planilha está 'Publicada na Web'. Erro: {e}")
    st.stop()

st.title("📊 Monitoramento de Reputação - Reclame Aqui")

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

# --- SEÇÃO 2: ANÁLISE DE PARETO ---
st.markdown("---")
st.header("📉 Análise de Pareto: Motivos de Notas Baixas")

# Filtrando notas ruins (menores ou iguais a 5)
df_ruim = df[df['Nota do consumidor'] <= 5].copy()

if not df_ruim.empty:
    # Contagem por Causa do Problema
    pareto_df = df_ruim['Causa do problema'].value_counts().reset_index()
    pareto_df.columns = ['Causa', 'Frequencia']
    
    # Cálculo do percentual acumulado
    pareto_df['Percentual_Acumulado'] = (pareto_df['Frequencia'].cumsum() / pareto_df['Frequencia'].sum()) * 100

    fig = go.Figure()
    
    # Barras
    fig.add_trace(go.Bar(x=pareto_df['Causa'], y=pareto_df['Frequencia'], name="Qtd Reclamações"))
    
    # Linha de Pareto
    fig.add_trace(go.Scatter(x=pareto_df['Causa'], y=pareto_df['Percentual_Acumulado'], 
                             name="% Acumulado", yaxis="y2", line=dict(color="#FF4B4B", width=3)))

    fig.update_layout(
        title="20% das causas que geram 80% das notas ruins",
        yaxis=dict(title="Número de Reclamações"),
        yaxis2=dict(title="Percentual Acumulado", overlaying="y", side="right", range=[0, 105]),
        xaxis=dict(tickangle=-45),
        showlegend=False
    )
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("Nenhuma nota baixa registrada para análise.")

# --- SEÇÃO 3: ALERTA PREDITIVO ---
st.markdown("---")
st.header("🚨 Sistema de Alerta Preditivo (Risco de Nota Baixa)")

hoje = pd.Timestamp.now()
df['Atraso_Dias'] = (hoje - df['Data da entrada']).dt.days

# Consideramos risco chamados não finalizados com mais de 2 dias de atraso
risco_critico = df[(df['Status'] != 'Finalizada') & (df['Atraso_Dias'] > 2)].copy()

c1, c2 = st.columns([1, 2])
with c1:
    st.warning(f"Existem {len(risco_critico)} casos pendentes há mais de 48h.")
    st.write("Ação semanal: Resolver estes casos antes que o cliente publique a avaliação final.")

with c2:
    if not risco_critico.empty:
        st.dataframe(risco_critico[['ID', 'Data da entrada', 'Causa do problema', 'Atraso_Dias']].sort_values('Atraso_Dias', ascending=False))