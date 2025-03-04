import streamlit as st
import pandas as pd
import json
import plotly.express as px
from collections import Counter


# Загружаем данные (пример логов)
@st.cache_data
def load_data():
    with open("logs.json", "r", encoding="utf-8") as file:
        return json.load(file)  # Читаем JSON-файл целиком


data = load_data()


# Функции для анализа данных
def process_data(data):
    df = pd.DataFrame(data)
    df["has_chat_history"] = df["chat_history"].apply(lambda x: len(x.get("old_questions", [])) > 0)
    df["response_time"] = df["Время ответа модели"]
    return df


df = process_data(data)

# Интерфейс Streamlit
st.title("Мониторинг качества чат-бота")

# Визуализация распределения по кампусам
st.subheader("Распределение запросов по кампусам")
campus_counts = df["Кампус"].value_counts()
st.bar_chart(campus_counts)

# Визуализация по уровням образования
st.subheader("Распределение по уровням образования")
edu_counts = df["Уровень образования"].value_counts()
st.bar_chart(edu_counts)

# Визуализация категорий вопросов
st.subheader("Категории вопросов")
category_counts = df["Категория вопроса"].value_counts()
st.bar_chart(category_counts)

# Время ответа модели
st.subheader("Среднее время ответа модели")
st.write(f"Среднее время ответа: {df['response_time'].mean():.2f} сек")

# Частота уточняющих вопросов
st.subheader("Частота уточняющих вопросов")
follow_ups = df["has_chat_history"].mean()
st.write(f"Процент пользователей, уточняющих вопрос: {follow_ups * 100:.2f}%")
