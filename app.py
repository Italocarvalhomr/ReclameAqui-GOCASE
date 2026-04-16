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
    
    # Tratamento de datas e números
    df['Data da entrada'] = pd.to_datetime(df['Data da entrada'], dayfirst=True, errors='coerce')
    df['Nota do consumidor'] = pd.to_numeric(df['Nota do consumidor'], errors='coerce')
    
    # Cálculo de atraso em dias
    hoje = pd.Timestamp.now()
    df['Atraso_Dias'] = (hoje - df['Data da entrada']).dt.days
    
    return df

try:
    df = load_data()
except Exception as e:
    st.error(f"Erro ao ligar à folha de cálculo: {e}")
    st.stop()

st.title("📊 Monitoramento Estratégico - Reclame Aqui")

# --- SEÇÃO 1: MÉTRICAS TOTAIS (Volumes Absolutos e Índices) ---
st.header("🎯 Visão Geral do Atendimento")

# Cálculos Base
total_reclamacoes = len(df)
total_avaliacoes = df['Nota do consumidor'].dropna().shape[0]
total_utilizadores = df['E-mail'].nunique()
resolvidas_abs = df[df['Seu problema foi resolvido?'] == 'Sim'].shape[0]
voltariam_abs = df[df['Voltaria a fazer negócio?'] == 'Sim'].shape[0]
respondidas = df[df['Status'].str.contains('Respondida', na=False, case=False)].shape[0]

# Linha 1: Volumes Absolutos
st.subheader("📊 Volumes Totais")
c1, c2, c3, c4 = st.columns(4)
with c1:
    st.metric("Total de Avaliações", total_avaliacoes)
with c2:
    st.metric("Utilizadores Únicos", total_utilizadores)
with c3:
    st.metric("Problemas Resolvidos", resolvidas_abs)
with c4:
    st.metric("Voltariam a Comprar", voltariam_abs)

# Linha 2: Índices Percentuais
st.subheader("📈 Índices de Reputação")
col1, col2, col3, col4 = st.columns(4)
with col1:
    indice_resp = (respondidas / total_reclamacoes) * 100 if total_reclamacoes > 0 else 0
    st.metric("Índice de Resposta", f"{indice_resp:.1f}%", delta="Meta: 100%")
with col2:
    indice_solu = (resolvidas_abs / total_avaliacoes) * 100 if total_avaliacoes > 0 else 0
    st.metric("Índice de Solução", f"{indice_solu:.1f}%", delta="Meta: > 90%")
with col3:
    nota_media = df['Nota do consumidor'].mean()
    st.metric("Média das Notas", f"{nota_media:.2f}/10")
with col4:
    indice_negocios = (voltariam_abs / total_avaliacoes) * 100 if total_avaliacoes > 0 else 0
    st.metric("Novos Negócios", f"{indice_negocios:.1f}%")

# --- NOVO: ALERTA DE RISCO CRÍTICO (> 7 DIAS) ---
st.markdown("---")
st.header("🚨 Alerta de Blindagem: Zona Crítica")

# Filtramos quem NÃO foi respondido E tem mais de 7 dias
zona_critica = df[(df['Status'] != 'Respondida') & (df['Atraso_Dias'] > 7)].copy()
zona_alerta = df[(df['Status'] != 'Respondida') & (df['Atraso_Dias'] > 2) & (df['Atraso_Dias'] <= 7)].copy()

col_crit, col_alert = st.columns(2)

with col_crit:
    if not zona_critica.empty:
        st.error(f"🔥 **URGENTE:** {len(zona_critica)} casos sem resposta há mais de 7 dias!")
        st.dataframe(zona_critica[['ID', 'Causa do problema', 'Atraso_Dias']].sort_values('Atraso_Dias', ascending=False), use_container_width=True)
    else:
        st.success("✅ Nenhum caso na Zona Crítica (> 7 dias).")

with col_alert:
    if not zona_alerta.empty:
        st.warning(f"⚠️ **ATENÇÃO:** {len(zona_alerta)} casos entre 2 e 7 dias sem resposta.")
        st.dataframe(zona_alerta[['ID', 'Causa do problema', 'Atraso_Dias']].sort_values('Atraso_Dias', ascending=False), use_container_width=True)

# --- SEÇÃO 2: ANÁLISE DE PARETO ---
st.markdown("---")
st.header("📉 Análise de Pareto: Causas de Notas Baixas")

df_ruim = df[df['Nota do consumidor'] <= 5].copy()

if not df_ruim.empty:
    pareto_df = df_ruim['Causa do problema'].value_counts().reset_index()
    pareto_df.columns = ['Causa', 'Frequencia']
    pareto_df['Percentual_Acumulado'] = (pareto_df['Frequencia'].cumsum() / pareto_df['Frequencia'].sum()) * 100

    fig = go.Figure()
    fig.add_trace(go.Bar(x=pareto_df['Causa'], y=pareto_df['Frequencia'], name="Qtd Reclamações"))
    fig.add_trace(go.Scatter(x=pareto_df['Causa'], y=pareto_df['Percentual_Acumulado'], name="% Acumulado", yaxis="y2", line=dict(color="#FF4B4B", width=4)))

    # Linha de corte 80%
    fig.add_shape(type="line", x0=0, x1=1, xref="paper", y0=80, y1=80, yref="y2", line=dict(color="orange", width=2, dash="dash"))
    fig.add_annotation(x=0.01, xref="paper", y=81, yref="y2", text="Corte 80% (Lei de Pareto)", showarrow=False, font=dict(color="orange"))

    fig.update_layout(
        yaxis=dict(title="Número de Reclamações"),
        yaxis2=dict(title="Percentual Acumulado", overlaying="y", side="right", range=[0, 105]),
        xaxis=dict(tickangle=-45),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    st.plotly_chart(fig, use_container_width=True)
    
    # Destaque das principais causas
    top_causas = pareto_df[pareto_df['Percentual_Acumulado'] <= 85]['Causa'].tolist()
    st.info(f"💡 **Foco Prioritário:** Resolver as causas **{', '.join(top_causas)}** reduzirá 80% das notas negativas.")

# --- SEÇÃO 3: TABELAS DE ATRASO ---
st.markdown("---")
st.header("🐢 Diagnóstico de Lentidão")
atraso_por_causa = df.groupby('Causa do problema').agg({
    'Atraso_Dias': 'mean',
    'ID': 'count'
}).rename(columns={'Atraso_Dias': 'Média Dias Aberto', 'ID': 'Total Casos'}).sort_values('Média Dias Aberto', ascending=False)

st.dataframe(atraso_por_causa.style.background_gradient(subset=['Média Dias Aberto'], cmap='YlOrRd'), use_container_width=True)