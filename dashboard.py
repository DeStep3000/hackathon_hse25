import io
import json

import matplotlib.pyplot as plt
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from streamlit_autorefresh import st_autorefresh

# ---------------------------
# НАСТРОЙКА СТРАНИЦЫ
# ---------------------------
st.set_page_config(page_title="Аналитика Чат-Бота", page_icon="🤖", layout="wide")

# ---------------------------
# АВТОПЕРЕЗАГРУЗКА (напр. каждые 10 секунд)
# ---------------------------
time_interval = 10
st_autorefresh(interval=time_interval * 1000, key="data_refresh")


# ---------------------------
# ЗАГРУЗКА И ПРЕДОБРАБОТКА ДАННЫХ
# ---------------------------
def load_data(file_name):
    """
    Загружает JSON-файл с логами.
    Предполагается, что файл лежит в корне проекта под именем logs.json.
    """
    with open(file_name, "r", encoding="utf-8") as file:
        return json.load(file)


def process_data(data):
    """
    Преобразует JSON в DataFrame, добавляет столбцы:
    - has_chat_history: флаг, есть ли уточняющие вопросы
    - response_time: numeric-колонка с временем ответа
    - conflict_metric: пример кастомной метрики
    """
    df = pd.DataFrame(data)
    df["has_chat_history"] = df["chat_history"].apply(lambda x: len(x.get("old_questions", [])) > 0)
    df["response_time"] = pd.to_numeric(df["Время ответа модели"], errors="coerce")

    # Доп. метрика: "убедительный, но неверный ответ"
    # Пример условия: если много контекстов (или несколько вопросов) + время ответа больше 3 секунд => конфликт
    df["conflict_metric"] = df.apply(
        lambda row: 1 if (len(row.get("chat_history", {}).get("old_questions", [])) > 1
                          and row["response_time"] > 3) else 0,
        axis=1
    )
    return df


def download_json(data):
    """
    Кнопка для скачивания исходного JSON (логов).
    """
    json_data = json.dumps(data, indent=4, ensure_ascii=False)
    st.download_button(
        label="📥 Скачать JSON",
        data=json_data,
        file_name="chatbot_logs.json",
        mime="application/json"
    )


# ---------------------------
# КЛАСС ДЛЯ ЭКСПОРТА ГРАФИКОВ (MATPLOTLIB)
# ---------------------------
class Exports:
    @staticmethod
    def export_pie_chart_matplotlib(data, column, title):
        counts = data[column].value_counts()
        if counts.empty:
            return
        fig, ax = plt.subplots()
        ax.pie(counts.values, labels=counts.index, autopct='%1.1f%%', startangle=90)
        ax.axis('equal')
        plt.title(title)
        buffer = io.BytesIO()
        plt.savefig(buffer, format="png")
        plt.close(fig)
        buffer.seek(0)
        st.download_button(
            label=f"📊 Скачать график «{title}» (Matplotlib)",
            data=buffer.getvalue(),
            file_name=f"{title}.png",
            mime="image/png"
        )

    @staticmethod
    def export_bar_chart_matplotlib(data, column, title, xlabel, ylabel):
        counts = data[column].value_counts()
        if counts.empty:
            return
        fig, ax = plt.subplots()
        ax.bar(counts.index, counts.values)
        ax.set_title(title)
        ax.set_xlabel(xlabel)
        ax.set_ylabel(ylabel)
        for i, v in enumerate(counts.values):
            ax.text(i, v + 0.1, str(v), ha='center')
        buffer = io.BytesIO()
        plt.savefig(buffer, format="png")
        plt.close(fig)
        buffer.seek(0)
        st.download_button(
            label=f"📊 Скачать график «{title}» (Matplotlib)",
            data=buffer.getvalue(),
            file_name=f"{title}.png",
            mime="image/png"
        )

    @staticmethod
    def export_response_time_by_campus_matplotlib(data):
        if data.empty or "Кампус" not in data.columns or "response_time" not in data.columns:
            return
        group_data = data.groupby("Кампус")["response_time"].mean().reset_index()
        if group_data.empty:
            return
        fig, ax = plt.subplots()
        ax.bar(group_data["Кампус"], group_data["response_time"])
        ax.set_title("Среднее время ответа по кампусам")
        ax.set_xlabel("Кампус")
        ax.set_ylabel("Время ответа (сек)")
        for i, v in enumerate(group_data["response_time"]):
            ax.text(i, v + 0.1, f"{v:.2f}", ha='center')
        buffer = io.BytesIO()
        plt.savefig(buffer, format="png")
        plt.close(fig)
        buffer.seek(0)
        st.download_button(
            label="📊 Скачать график «Среднее время ответа по кампусам» (Matplotlib)",
            data=buffer.getvalue(),
            file_name="Среднее_время_ответа_по_кампусам.png",
            mime="image/png"
        )

    @staticmethod
    def export_line_chart_matplotlib(data):
        if data.empty or "response_time" not in data.columns:
            return
        fig, ax = plt.subplots()
        ax.plot(data.index, data["response_time"], marker='o', linestyle='-')
        ax.set_title("Динамика времени ответа модели")
        ax.set_xlabel("Запросы")
        ax.set_ylabel("Время ответа (сек)")
        buffer = io.BytesIO()
        plt.savefig(buffer, format="png")
        plt.close(fig)
        buffer.seek(0)
        st.download_button(
            label="📊 Скачать график «Динамика времени ответа модели» (Matplotlib)",
            data=buffer.getvalue(),
            file_name="Динамика_времени_ответа_модели.png",
            mime="image/png"
        )

    @staticmethod
    def export_conflict_metric_matplotlib(data):
        if data.empty or "conflict_metric" not in data.columns:
            return
        conflict_rate = data["conflict_metric"].mean() * 100
        fig, ax = plt.subplots()
        ax.bar(["Конфликтный ответ"], [conflict_rate], color="red")
        ax.set_ylim(0, 100)
        ax.set_ylabel("Процент")
        ax.set_title("Конфликтный ответ (%)")
        buffer = io.BytesIO()
        plt.savefig(buffer, format="png")
        plt.close(fig)
        buffer.seek(0)
        st.download_button(
            label="📊 Скачать график «Конфликтный ответ (%)» (Matplotlib)",
            data=buffer.getvalue(),
            file_name="Конфликтный_ответ.png",
            mime="image/png"
        )


# ---------------------------
# КЛАСС ДЛЯ ПОСТРОЕНИЯ ГРАФИКОВ (PLOTLY) + ВЫЗОВ ЭКСПОРТА
# ---------------------------
class Plots:
    def __init__(self, data):
        self.data = data

    def plot_pie_chart(self, column, title):
        if self.data.empty or self.data[column].dropna().empty:
            st.info(f"Нет данных для построения графика: {title}")
            return
        counts = self.data[column].value_counts()
        fig = px.pie(
            names=counts.index,
            values=counts.values,
            title=title,
            hole=0.4,
            color_discrete_sequence=px.colors.sequential.RdBu
        )
        st.plotly_chart(fig)
        Exports.export_pie_chart_matplotlib(self.data, column, title)

    def plot_bar_chart(self, column, title, x_label, y_label):
        if self.data.empty or self.data[column].dropna().empty:
            st.info(f"Нет данных для построения графика: {title}")
            return
        counts = self.data[column].value_counts()
        if counts.empty:
            st.info(f"Нет данных для построения графика: {title}")
            return
        fig = px.bar(
            x=counts.index,
            y=counts.values,
            labels={'x': x_label, 'y': y_label},
            title=title,
            text_auto=True,
            color_discrete_sequence=px.colors.qualitative.Vivid
        )
        st.plotly_chart(fig)
        Exports.export_bar_chart_matplotlib(self.data, column, title, x_label, y_label)

    def plot_response_time_chart_with_campus(self):
        if self.data.empty or "Кампус" not in self.data.columns or "response_time" not in self.data.columns:
            st.info("Нет данных для построения графика: Среднее время ответа по кампусам")
            return
        group_data = self.data.groupby("Кампус")["response_time"].mean().reset_index()
        if group_data.empty:
            st.info("Нет данных для построения графика: Среднее время ответа по кампусам")
            return
        fig = px.bar(
            group_data,
            x="Кампус",
            y="response_time",
            title="Среднее время ответа по кампусам",
            color="Кампус",
            text_auto=True,
            color_discrete_sequence=px.colors.qualitative.Set3
        )
        st.plotly_chart(fig)
        Exports.export_response_time_by_campus_matplotlib(self.data)

    def plot_response_time_chart_line(self):
        if self.data.empty or "response_time" not in self.data.columns:
            st.info("Нет данных для построения графика: Динамика времени ответа модели")
            return
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=self.data.index,
            y=self.data["response_time"],
            mode='lines+markers',
            name='Время ответа',
            marker=dict(size=15, symbol='circle', color='red', line=dict(width=2, color='black')),
            line=dict(width=2, color='yellow')
        ))
        fig.update_layout(
            title="Динамика времени ответа модели",
            xaxis_title="Запросы",
            yaxis_title="Время ответа (сек)",
            hovermode="x unified"
        )
        st.plotly_chart(fig)
        Exports.export_line_chart_matplotlib(self.data)

    def plot_follow_up_pie_chart(self):
        if self.data.empty or "has_chat_history" not in self.data.columns:
            st.info("Нет данных для построения графика: Процент уточняющих вопросов пользователей")
            return
        follow_ups = self.data["has_chat_history"].mean()
        fig = px.pie(
            names=["Без уточнений", "С уточнениями"],
            values=[1 - follow_ups, follow_ups],
            title="Процент уточняющих вопросов пользователей",
            hole=0.3,
            color_discrete_sequence=px.colors.qualitative.Pastel
        )
        st.plotly_chart(fig)
        Exports.export_pie_chart_matplotlib(self.data, "has_chat_history", "Процент уточняющих вопросов пользователей")

    def plot_conflict_metric(self):
        if self.data.empty or "conflict_metric" not in self.data.columns:
            st.info("Нет данных для построения графика: Метрика убедительного, но неверного ответа")
            return
        conflict_rate = self.data["conflict_metric"].mean() * 100
        fig = go.Figure(go.Indicator(
            mode="gauge+number",
            value=conflict_rate,
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
        Exports.export_conflict_metric_matplotlib(self.data)


# ---------------------------
# ФУНКЦИЯ ДЛЯ ФИЛЬТРАЦИИ (БОКОВАЯ ПАНЕЛЬ)
# ---------------------------
def sidebar_layout(df):
    """
    Создает элементы боковой панели:
    - Заголовок "Фильтры"
    - Фильтры (кампус, категория, уровень)
    - Подзаголовок "Экспорт данных" + кнопка скачивания JSON
    Возвращает отфильтрованный датафрейм.
    """
    st.sidebar.title("Фильтры")

    campuses = df["Кампус"].dropna().unique().tolist()
    categories = df["Категория вопроса"].dropna().unique().tolist()
    education_levels = df["Уровень образования"].dropna().unique().tolist()

    selected_campus = st.sidebar.multiselect("Выберите кампус", campuses, default=campuses)
    selected_category = st.sidebar.multiselect("Выберите категорию вопроса", categories, default=categories)
    selected_edu_level = st.sidebar.multiselect("Выберите уровень образования", education_levels,
                                                default=education_levels)

    # Подзаголовок и кнопка для экспорта JSON
    st.sidebar.subheader("Экспорт данных")
    # Кнопка для скачивания JSON (вызывает download_json, которая объявлена выше)
    download_json(df.to_dict(orient="records"))

    filtered_df = df[
        (df["Кампус"].isin(selected_campus)) &
        (df["Категория вопроса"].isin(selected_category)) &
        (df["Уровень образования"].isin(selected_edu_level))
        ]
    return filtered_df


# ---------------------------
# ОСНОВНАЯ ЧАСТЬ ПРИЛОЖЕНИЯ
# ---------------------------
def main():
    data = load_data('logs.json')  # Загрузка исходного JSON
    df = process_data(data)  # Предобработка (DataFrame + новые колонки)

    # Получаем отфильтрованный DataFrame через боковую панель
    filtered_df = sidebar_layout(df)

    # Если после фильтров данных нет — предупредим
    if filtered_df.empty:
        st.info("Нет данных для отображения. Попробуйте изменить фильтры.")
        return

    # Инициализируем класс для построения графиков
    graphs = Plots(filtered_df)

    # Заголовок дашборда (в центре)
    st.markdown("""
        <h1 style='text-align: center;'>Мониторинг качества чат-бота</h1>
    """, unsafe_allow_html=True)

    # Построение графиков
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


if __name__ == "__main__":
    main()
