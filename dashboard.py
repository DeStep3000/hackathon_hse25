import io
import json

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from streamlit_autorefresh import st_autorefresh

# ---------------------------
# НАСТРОЙКА СТРАНИЦЫ
# ---------------------------
st.set_page_config(page_title="Аналитика Чат-Бота", page_icon="🤖", layout="wide")

# Автоматическая перезагрузка каждые 10 секунд
time_interval = 10
st_autorefresh(interval=time_interval * 1000, key="data_refresh")


# ---------------------------
# ФУНКЦИЯ ДЛЯ ЗАГРУЗКИ ДАННЫХ
# ---------------------------
def load_data(file_name: str):
    with open(file_name, "r", encoding="utf-8") as file:
        return json.load(file)


# ---------------------------
# ПРЕДОБРАБОТКА ДАННЫХ
# ---------------------------
def process_data(data):
    df = pd.DataFrame(data)
    # Если в данных есть ключ "chat_history", используем его, иначе обрабатываем "contexts"
    if "chat_history" in df.columns:
        df["has_chat_history"] = df["chat_history"].apply(lambda x: len(x.get("old_questions", [])) > 0)
        df["conflict_metric"] = df.apply(
            lambda row: 1 if (len(row.get("chat_history", {}).get("old_questions", [])) > 1 and row[
                "response_time"] > 3) else 0,
            axis=1
        )
    elif "contexts" in df.columns:
        # Создаем флаг наличия контекстов
        df["has_contexts"] = df["contexts"].apply(lambda x: len(x) > 0 if isinstance(x, list) else False)
        df["conflict_metric"] = df.apply(
            lambda row: 1 if (
                        row["has_contexts"] and len(row.get("contexts", [])) > 1 and row["response_time"] > 3) else 0,
            axis=1
        )
    else:
        df["has_contexts"] = False
        df["conflict_metric"] = 0

    # Обновляем значение времени ответа, теперь ключ "response_time" уже есть в JSON
    df["response_time"] = pd.to_numeric(df["response_time"], errors="coerce")
    return df


# ---------------------------
# ЭКСПОРТ ДАННЫХ (JSON)
# ---------------------------
def download_json(data):
    json_data = json.dumps(data, indent=4, ensure_ascii=False)
    st.download_button(
        label="📥 Скачать JSON",
        data=json_data,
        file_name="chatbot_logs.json",
        mime="application/json"
    )


# ---------------------------
# ЭКСПОРТ ГРАФИКОВ ЧЕРЕЗ PLOTLY (KALEIDO)
# ---------------------------
def download_plotly_fig(fig, filename: str):
    try:
        # Метод to_image использует Kaleido под капотом (убедитесь, что kaleido установлен)
        img_bytes = fig.to_image(format="png")
        st.download_button(
            label=f"📊 Скачать график «{filename}»",
            data=img_bytes,
            file_name=f"{filename}.png",
            mime="image/png"
        )
    except Exception as e:
        st.error(f"Не удалось экспортировать график в PNG. Убедитесь, что установлен kaleido. Ошибка: {e}")


# ---------------------------
# КЛАСС ДЛЯ ПОСТРОЕНИЯ ГРАФИКОВ (PLOTLY)
# ---------------------------
class Plots:
    def __init__(self, data: pd.DataFrame):
        self.data = data

    def plot_pie_chart(self, column: str, title: str):
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
        download_plotly_fig(fig, title)

    def plot_bar_chart(self, column: str, title: str, x_label: str, y_label: str):
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
        download_plotly_fig(fig, title)

    def plot_response_time_chart_with_campus(self):
        if self.data.empty or "campus" not in self.data.columns or "response_time" not in self.data.columns:
            st.info("Нет данных для построения графика: Среднее время ответа по кампусам")
            return
        group_data = self.data.groupby("campus")["response_time"].mean().reset_index()
        if group_data.empty:
            st.info("Нет данных для построения графика: Среднее время ответа по кампусам")
            return
        fig = px.bar(
            group_data,
            x="campus",
            y="response_time",
            title="Среднее время ответа по кампусам",
            color="campus",
            text_auto=True,
            color_discrete_sequence=px.colors.qualitative.Set3
        )
        st.plotly_chart(fig)
        download_plotly_fig(fig, "Среднее время ответа по кампусам")

    def plot_response_time_chart_line(self):
        if self.data.empty or "response_time" not in self.data.columns:
            st.info("Нет данных для построения графика: Динамика времени ответа модели")
            return

        # Создаем колонку со скользящим средним (окно = 20)
        # min_periods=1 позволяет строить среднее даже если данных меньше 20
        self.data["rolling_avg"] = self.data["response_time"].rolling(window=20, min_periods=1).mean()

        fig = go.Figure()

        # Точки (scatter) для каждого запроса
        fig.add_trace(go.Scatter(
            x=self.data.index,
            y=self.data["response_time"],
            mode='markers',
            name='Время ответа (сырые данные)',
            marker=dict(size=5, color='red')
        ))

        # Линия скользящего среднего
        fig.add_trace(go.Scatter(
            x=self.data.index,
            y=self.data["rolling_avg"],
            mode='lines',
            name='Скользящее среднее (окно=20)',
            line=dict(width=2, color='blue')
        ))

        fig.update_layout(
            title="Динамика времени ответа модели (со скользящим средним)",
            xaxis_title="Запросы",
            yaxis_title="Время ответа (сек)",
            hovermode="x unified"
        )

        st.plotly_chart(fig)
        download_plotly_fig(fig, "Динамика времени ответа (скользящее среднее)")

    def plot_follow_up_pie_chart(self):
        # Здесь используем флаг наличия контекстов, созданный в process_data (если "chat_history" отсутствует)
        if self.data.empty:
            st.info("Нет данных для построения графика: Процент уточняющих вопросов")
            return
        flag = "has_chat_history" if "has_chat_history" in self.data.columns else "has_contexts"
        if self.data[flag].dropna().empty:
            st.info("Нет данных для построения графика: Процент уточняющих вопросов")
            return
        avg_flag = self.data[flag].mean()
        fig = px.pie(
            names=["Без уточнений", "С уточнениями"],
            values=[1 - avg_flag, avg_flag],
            title="Процент уточняющих вопросов",
            hole=0.3,
            color_discrete_sequence=px.colors.qualitative.Pastel
        )
        st.plotly_chart(fig)
        download_plotly_fig(fig, "Процент уточняющих вопросов")

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
        download_plotly_fig(fig, "Конфликтный ответ (%)")


# ---------------------------
# БОКОВАЯ ПАНЕЛЬ (ФИЛЬТРАЦИЯ)
# ---------------------------
def sidebar_layout(df: pd.DataFrame):
    st.sidebar.title("Фильтры")

    # Используем ключи из нового JSON
    campuses = df["campus"].dropna().unique().tolist()
    categories = df["question_category"].dropna().unique().tolist()
    education_levels = df["education_level"].dropna().unique().tolist()

    selected_campus = st.sidebar.multiselect("Выберите кампус", campuses, default=campuses)
    selected_category = st.sidebar.multiselect("Выберите категорию вопроса", categories, default=categories)
    selected_edu_level = st.sidebar.multiselect("Выберите уровень образования", education_levels,
                                                default=education_levels)

    st.sidebar.subheader("Экспорт данных")
    download_json(df.to_dict(orient="records"))

    filtered_df = df[
        (df["campus"].isin(selected_campus)) &
        (df["question_category"].isin(selected_category)) &
        (df["education_level"].isin(selected_edu_level))
        ]
    return filtered_df


# ---------------------------
# ОСНОВНАЯ ЧАСТЬ ПРИЛОЖЕНИЯ
# ---------------------------
def main():
    # Загрузка и подготовка данных из нового JSON
    data = load_data("output_last.json")
    df = process_data(data)

    # Боковая панель с фильтрами и экспортом
    filtered_df = sidebar_layout(df)
    if filtered_df.empty:
        st.info("Нет данных для отображения. Попробуйте изменить фильтры.")
        return

    graphs = Plots(filtered_df)

    st.markdown("<h1 style='text-align: center;'>Мониторинг качества чат-бота</h1>", unsafe_allow_html=True)

    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Распределение запросов по кампусам")
        graphs.plot_pie_chart("campus", "Распределение запросов по кампусам")
    with col2:
        st.subheader("Распределение по уровням образования")
        graphs.plot_pie_chart("education_level", "Распределение по уровням образования")

    st.subheader("Категории вопросов")
    graphs.plot_bar_chart("question_category", "Распределение вопросов по категориям", "Категории", "Количество")

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
