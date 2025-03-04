import json
import pandas as pd
import streamlit as st
from streamlit_autorefresh import st_autorefresh
import plotly.express as px
import plotly.graph_objects as go

st.set_page_config(page_title="Аналитика Чат-Бота", page_icon="🤖", layout="wide")

time_interval = 10
st_autorefresh(interval=time_interval * 1000, key="data_refresh")

def load_data():
    with open("logs.json", "r", encoding="utf-8") as file:
        return json.load(file)

def process_data(data):
    df = pd.DataFrame(data)
    df["has_chat_history"] = df["chat_history"].apply(lambda x: len(x.get("old_questions", [])) > 0)
    df["response_time"] = pd.to_numeric(df["Время ответа модели"], errors="coerce")
    return df

class Plots:
    def __init__(self, data):
        self.data = data

    def plot_pie_chart(self, column, title):
        counts = self.data[column].value_counts()
        fig = px.pie(names=counts.index, values=counts.values, title=title, hole=0.4, color_discrete_sequence=px.colors.sequential.RdBu)
        st.plotly_chart(fig)

    def plot_bar_chart(self, column, title, x_label, y_label):
        counts = self.data[column].value_counts()
        fig = px.bar(x=counts.index, y=counts.values, labels={'x': x_label, 'y': y_label}, title=title, text_auto=True, color_discrete_sequence=px.colors.qualitative.Vivid)
        st.plotly_chart(fig)

    def plot_response_time_chart_with_campus(self):
        avg_response_time = self.data.groupby("Кампус")["response_time"].mean().reset_index()
        fig = px.bar(avg_response_time, x="Кампус", y="response_time", title="Среднее время ответа по кампусам", color="Кампус", text_auto=True, color_discrete_sequence=px.colors.qualitative.Set3)
        st.plotly_chart(fig)

    def plot_response_time_chart_line(self):
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=self.data.index, y=self.data["response_time"], mode='lines+markers', name='Время ответа', line=dict(width=2)))
        fig.update_layout(title="Динамика времени ответа модели", xaxis_title="Запросы", yaxis_title="Время ответа (сек)")
        st.plotly_chart(fig)

    def plot_follow_up_pie_chart(self):
        follow_ups = self.data["has_chat_history"].mean()
        fig = px.pie(names=["Без уточнений", "С уточнениями"], values=[1 - follow_ups, follow_ups], title="Процент уточняющих вопросы пользователей", hole=0.3, color_discrete_sequence=px.colors.qualitative.Pastel)
        st.plotly_chart(fig)

if __name__ == "__main__":
    data = load_data()
    df = process_data(data)

    graphs = Plots(df)

    st.markdown("""
        <h1 style='text-align: center;'>Мониторинг качества чат-бота</h1>
    """, unsafe_allow_html=True)

    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Распределение запросов по кампусам")
        graphs.plot_pie_chart("Кампус", "Распределение запросов по кампусам")
    with col2:
        st.subheader("Распределение по уровням образования")
        graphs.plot_pie_chart("Уровень образования", "Распределение по уровням образования")

    st.subheader("Категории вопросов")
    graphs.plot_bar_chart("Категория вопроса", "Распределение вопросов по категориям", "Категории", "Количество")

    col3, col4 = st.columns(2)
    with col3:
        st.subheader("Среднее время ответа по кампусам")
        graphs.plot_response_time_chart_with_campus()
    with col4:
        st.subheader("Динамика времени ответа")
        graphs.plot_response_time_chart_line()

    st.subheader("Частота уточняющих вопросов")
    graphs.plot_follow_up_pie_chart()
