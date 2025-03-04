import io
import json

import matplotlib.pyplot as plt
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from streamlit_autorefresh import st_autorefresh

st.set_page_config(page_title="Аналитика Чат-Бота", page_icon="🤖", layout="wide")

# Автоматическая перезагрузка каждые 10 секунд для обновления дашборда
time_interval = 10
st_autorefresh(interval=time_interval * 1000, key="data_refresh")


def load_data():
    with open("logs.json", "r", encoding="utf-8") as file:
        return json.load(file)


def process_data(data):
    df = pd.DataFrame(data)
    # Флаг наличия уточняющих вопросов
    df["has_chat_history"] = df["chat_history"].apply(lambda x: len(x.get("old_questions", [])) > 0)
    df["response_time"] = pd.to_numeric(df["Время ответа модели"], errors="coerce")
    # Дополнительная метрика для оценки ситуации, когда модель выдает «убедительный, но неверный» ответ.
    # Пример: если в chat_history несколько вопросов и время ответа больше 3 секунд, то считаем это конфликтной ситуацией.
    df["conflict_metric"] = df.apply(
        lambda row: 1 if (
                    len(row.get("chat_history", {}).get("old_questions", [])) > 1 and row["response_time"] > 3) else 0,
        axis=1
    )
    return df


def download_json(data):
    json_data = json.dumps(data, indent=4, ensure_ascii=False)
    st.download_button(
        label="📥 Скачать JSON",
        data=json_data,
        file_name="chatbot_logs.json",
        mime="application/json"
    )


def download_plot(fig, filename):
    # Функция для скачивания графика (Plotly) в формате PNG
    try:
        buffer = io.BytesIO()
        fig.write_image(buffer, format="png")
        buffer.seek(0)
        st.download_button(
            label=f"📊 Скачать график «{filename}»",
            data=buffer.getvalue(),
            file_name=f"{filename}.png",
            mime="image/png"
        )
    except Exception as e:
        st.error("Экспорт графика недоступен. Убедитесь, что установлен пакет kaleido.")


def download_matplotlib_plot(fig, filename):
    buffer = io.BytesIO()
    fig.savefig(buffer, format="png")
    buffer.seek(0)
    st.download_button(
        label=f"📊 Скачать график «{filename}»",
        data=buffer.getvalue(),
        file_name=f"{filename}.png",
        mime="image/png"
    )


def filter_data(df):
    campuses = df["Кампус"].unique().tolist()
    categories = df["Категория вопроса"].unique().tolist()
    education_levels = df["Уровень образования"].unique().tolist()

    selected_campus = st.sidebar.multiselect("Выберите кампус", campuses, default=campuses)
    selected_category = st.sidebar.multiselect("Выберите категорию вопроса", categories, default=categories)
    selected_edu_level = st.sidebar.multiselect("Выберите уровень образования", education_levels,
                                                default=education_levels)

    filtered_df = df[
        (df["Кампус"].isin(selected_campus)) &
        (df["Категория вопроса"].isin(selected_category)) &
        (df["Уровень образования"].isin(selected_edu_level))
        ]
    return filtered_df


class Plots:
    def __init__(self, data):
        self.data = data

    def plot_pie_chart(self, column, title):
        counts = self.data[column].value_counts()
        fig = px.pie(names=counts.index, values=counts.values, title=title, hole=0.4,
                     color_discrete_sequence=px.colors.sequential.RdBu)
        st.plotly_chart(fig)
        download_plot(fig, title)

    def plot_bar_chart(self, column, title, x_label, y_label):
        counts = self.data[column].value_counts()
        fig = px.bar(x=counts.index, y=counts.values, labels={'x': x_label, 'y': y_label},
                     title=title, text_auto=True, color_discrete_sequence=px.colors.qualitative.Vivid)
        st.plotly_chart(fig)
        download_plot(fig, title)

    def plot_response_time_chart_with_campus(self):
        avg_response_time = self.data.groupby("Кампус")["response_time"].mean().reset_index()
        fig = px.bar(avg_response_time, x="Кампус", y="response_time",
                     title="Среднее время ответа по кампусам", color="Кампус", text_auto=True,
                     color_discrete_sequence=px.colors.qualitative.Set3)
        st.plotly_chart(fig)
        download_plot(fig, "Среднее время ответа по кампусам")

    def plot_response_time_chart_line(self):
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=self.data.index,
            y=self.data["response_time"],
            mode='lines+markers',
            name='Время ответа',
            marker=dict(size=8, symbol='circle', color='red', line=dict(width=2, color='black')),
            line=dict(width=2, color='blue')
        ))
        fig.update_layout(
            title="Динамика времени ответа модели",
            xaxis_title="Запросы",
            yaxis_title="Время ответа (сек)",
            hovermode="x unified"
        )
        st.plotly_chart(fig)
        download_plot(fig, "Динамика времени ответа модели")

    def plot_follow_up_pie_chart(self):
        follow_ups = self.data["has_chat_history"].mean()
        fig = px.pie(names=["Без уточнений", "С уточнениями"],
                     values=[1 - follow_ups, follow_ups],
                     title="Процент уточняющих вопросов пользователей", hole=0.3,
                     color_discrete_sequence=px.colors.qualitative.Pastel)
        st.plotly_chart(fig)
        download_plot(fig, "Процент уточняющих вопросов пользователей")

    def plot_conflict_metric(self):
        # Визуализация дополнительной метрики: процент конфликтных ответов
        conflict_rate = self.data["conflict_metric"].mean()
        fig = go.Figure(go.Indicator(
            mode="gauge+number",
            value=conflict_rate * 100,
            title={"text": "Конфликтный ответ (%)"},
            gauge={
                'axis': {'range': [0, 100]},
                'bar': {'color': "red"},
                'steps': [
                    {'range': [0, 50], 'color': "lightgreen"},
                    {'range': [50, 100], 'color': "lightcoral"}
                ],
            }
        ))
        st.plotly_chart(fig)
        download_plot(fig, "Конфликтный ответ")


if __name__ == "__main__":
    st.sidebar.title("Фильтры и экспорт")
    st.sidebar.subheader("Экспорт данных")
    # Экспорт исходных логов
    data = load_data()
    download_json(data)

    df = process_data(data)
    # Применяем фильтрацию данных через боковую панель
    filtered_df = filter_data(df)
    graphs = Plots(filtered_df)

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

    st.subheader("Метрика убедительного, но неверного ответа")
    graphs.plot_conflict_metric()
