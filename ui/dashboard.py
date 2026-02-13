import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd


def render_kpi(total, profit, roi, max_dd, daily_chg, daily_pct):
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Dzisiaj", f"{daily_chg:+,.0f} PLN", f"{daily_pct:+.2f}%")
    c2.metric("Wycena", f"{total:,.0f} PLN")
    c3.metric("Zysk", f"{profit:+,.0f} PLN", f"{roi:+.2f}%")
    c4.metric("Max DD", f"{max_dd:.2f}%")


def render_main_ui(df, equity_map, roi_series, bench_roi):
    t1, t2, t3, t4, t5 = st.tabs(["Wartość", "ROI", "Alokacja", "Dziennik", "Tabela"])

    with t1:
        st.subheader("Wartość portfela w czasie")
        eq_df = pd.DataFrame(equity_map).fillna(0)
        if not eq_df.empty:
            sorted_cols = eq_df.iloc[-1].sort_values(ascending=False).index
            fig = px.area(eq_df[sorted_cols], template="plotly_dark",
                          color_discrete_sequence=px.colors.qualitative.Bold)
            fig.update_layout(height=450, paper_bgcolor='rgba(0,0,0,0)', xaxis_title=None, yaxis_title="PLN",
                              hovermode='x unified')
            st.plotly_chart(fig, use_container_width=True)

    with t2:
        st.subheader("Zwrot z inwestycji (ROI)")
        fig_roi = go.Figure()
        for bn, br in bench_roi.items():
            fig_roi.add_trace(go.Scatter(x=br.index, y=br, mode='lines', name=bn, line=dict(dash='dot', width=1)))
        fig_roi.add_trace(go.Scatter(x=roi_series.index, y=roi_series, mode='lines', name='Twój Portfel',
                                     line=dict(color='#FAFAFA', width=3)))
        fig_roi.update_layout(template="plotly_dark", height=450, paper_bgcolor='rgba(0,0,0,0)', yaxis_title="ROI (%)",
                              hovermode='x unified')
        st.plotly_chart(fig_roi, use_container_width=True)

    with t3:
        st.subheader("Alokacja aktywów")
        alloc = df.groupby('Symbol')['Wartosc_PLN'].sum().reset_index()
        fig = px.pie(alloc, values='Wartosc_PLN', names='Symbol', hole=0.5, template="plotly_dark")
        st.plotly_chart(fig, use_container_width=True)

    with t4:
        st.subheader("Dziennik transakcji")
        for _, row in df.sort_values('Data_Zakupu', ascending=False).iterrows():
            color = "#00E676" if row['Zysk_PLN'] >= 0 else "#FF5252"
            st.markdown(
                f"""<div class="journal-card"><div class="journal-date">{row['Data_Zakupu']}</div><div class="journal-header">{row['Symbol']} <span style="font-weight:normal">({row['Kwota_Poczatkowa_PLN']:.0f} PLN)</span><span style="float:right;color:{color}">{row['Zysk_PLN']:+.0f} PLN ({row['Zysk_Proc']:+.1f}%)</span></div><div class="journal-note">{row['Notatka'] if row['Notatka'] else "Brak notatki."}</div></div>""",
                unsafe_allow_html=True)

    with t5:
        st.subheader("Szczegółowa tabela")
        st.dataframe(df[['Symbol', 'Data_Zakupu', 'Cena_Live', 'Wartosc_PLN', 'Zysk_PLN', 'Zysk_Proc', 'Notatka']],
                     use_container_width=True, hide_index=True)