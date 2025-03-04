import json

import pandas as pd
import streamlit as st
from streamlit_autorefresh import st_autorefresh
import plotly.express as px

time_interval = 10
st_autorefresh(interval=time_interval * 1000, key="data_refresh")


def load_data():
    with open("logs.json", "r", encoding="utf-8") as file:
        return json.load(file)  # Читаем JSON-файл целиком


# Функции для анализа данных
def process_data(data):
    df = pd.DataFrame(data)
    df["has_chat_history"] = df["chat_history"].apply(lambda x: len(x.get("old_questions", [])) > 0)
    df["response_time"] = df["Время ответа модели"]
    return df


if __name__ == "__main__":
    data = load_data()
    df = process_data(data)
    # Ручное обновление данных
    if st.button("🔄 Обновить данные"):
        st.rerun()

    # Интерфейс Streamlit
    st.title("Мониторинг качества чат-бота")

    # Визуализация распределения по кампусам
    st.subheader("Распределение запросов по кампусам")
    campus_counts = df["Кампус"].value_counts()
    fig_campus = px.pie(names=campus_counts.index, values=campus_counts.values,
                        title="Распределение запросов по кампусам")
    st.plotly_chart(fig_campus)

    # Визуализация по уровням образования
    st.subheader("Распределение по уровням образования")
    edu_counts = df["Уровень образования"].value_counts()
    fig_edu = px.pie(names=edu_counts.index, values=edu_counts.values, title="Распределение по уровням образования")
    st.plotly_chart(fig_edu)

    # Визуализация категорий вопросов
    st.subheader("Категории вопросов")
    category_counts = df["Категория вопроса"].value_counts()
    fig_category = px.bar(x=category_counts.index, y=category_counts.values,
                          labels={'x': 'Категории', 'y': 'Количество'}, title="Распределение вопросов по категориям")
    st.plotly_chart(fig_category)

    # Время ответа модели
    st.subheader("Среднее время ответа модели")
    st.write(f"Среднее время ответа: {df['response_time'].mean():.2f} сек")
    fig_response_time = px.histogram(df, x="response_time", nbins=20, title="Распределение времени ответа модели")
    st.plotly_chart(fig_response_time)

    # Частота уточняющих вопросов
    st.subheader("Частота уточняющих вопросов")
    follow_ups = df["has_chat_history"].mean()
    st.write(f"Процент пользователей, уточняющих вопрос: {follow_ups * 100:.2f}%")
    fig_follow_ups = px.pie(names=["Без уточнений", "С уточнениями"], values=[1 - follow_ups, follow_ups],
                            title="Процент уточняющих вопросы пользователей")
    st.plotly_chart(fig_follow_ups)
