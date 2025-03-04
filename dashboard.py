import json
import pandas as pd
import streamlit as st
from streamlit_autorefresh import st_autorefresh
import plotly.express as px

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
        fig = px.pie(names=counts.index, values=counts.values, title=title)
        st.plotly_chart(fig)

    def plot_bar_chart(self, column, title, x_label, y_label):
        counts = self.data[column].value_counts()
        fig = px.bar(x=counts.index, y=counts.values, labels={'x': x_label, 'y': y_label}, title=title)
        st.plotly_chart(fig)

    def plot_response_time_chart_with_campus(self):
        avg_response_time = self.data.groupby("Кампус")["response_time"].mean().reset_index()
        fig = px.bar(avg_response_time, x="Кампус", y="response_time", title="Среднее время ответа модели")
        st.plotly_chart(fig)

    def plot_response_time_chart_line(self):
        fig = px.line(self.data, x=self.data.index, y="response_time", markers=True, title="Среднее время ответа модели")
        st.plotly_chart(fig)

    def plot_follow_up_pie_chart(self):
        follow_ups = self.data["has_chat_history"].mean()
        fig = px.pie(names=["Без уточнений", "С уточнениями"], values=[1 - follow_ups, follow_ups],
                     title="Процент уточняющих вопросы пользователей")
        st.plotly_chart(fig)


if __name__ == "__main__":
    if st.button("🔄 Обновить данные"):
        st.rerun()

    data = load_data()
    df = process_data(data)

    graphs = Plots(df)

    st.title("Мониторинг качества чат-бота")
    st.subheader("Распределение запросов по кампусам")
    graphs.plot_pie_chart("Кампус", "Распределение запросов по кампусам")

    st.subheader("Распределение по уровням образования")
    graphs.plot_pie_chart("Уровень образования", "Распределение по уровням образования")

    st.subheader("Категории вопросов")
    graphs.plot_bar_chart("Категория вопроса", "Распределение вопросов по категориям", "Категории", "Количество")

    st.subheader("Среднее время ответа модели")
    graphs.plot_response_time_chart_line()

    st.subheader("Частота уточняющих вопросов")
    graphs.plot_follow_up_pie_chart()
