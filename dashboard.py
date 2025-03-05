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

# Автоперезагрузка каждые 10 секунд (по желанию)
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

    # Если в данных есть "chat_history" - используем его,
    # иначе смотрим "contexts", чтобы заполнить conflict_metric
    if "chat_history" in df.columns:
        df["has_chat_history"] = df["chat_history"].apply(lambda x: len(x.get("old_questions", [])) > 0)
        df["conflict_metric"] = df.apply(
            lambda row: 1 if (len(row.get("chat_history", {}).get("old_questions", [])) > 1
                              and row["response_time"] > 3) else 0,
            axis=1
        )
    elif "contexts" in df.columns:
        df["has_contexts"] = df["contexts"].apply(lambda x: len(x) > 0 if isinstance(x, list) else False)
        df["conflict_metric"] = df.apply(
            lambda row: 1 if (row["has_contexts"] and len(row.get("contexts", [])) > 1
                              and row["response_time"] > 3) else 0,
            axis=1
        )
    else:
        df["conflict_metric"] = 0

    # Убедимся, что response_time - число
    df["response_time"] = pd.to_numeric(df["response_time"], errors="coerce")

    return df


# ---------------------------
# ЭКСПОРТ ДАННЫХ (JSON)
# ---------------------------
def download_json(data):
    # Используем default=str, чтобы сериализовать объекты numpy и другие не стандартные типы
    json_data = json.dumps(data, indent=4, ensure_ascii=False, default=str)
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
        img_bytes = fig.to_image(format="png")
        # Размещаем кнопку скачивания в отдельной колонке, если нужно
        col_btn, _ = st.columns([0.5, 4])
        with col_btn:
            st.download_button(
                label=f"📊 Скачать график «{filename}»",
                data=img_bytes,
                file_name=f"{filename}.png",
                mime="image/png"
            )
    except Exception as e:
        st.error(f"Не удалось экспортировать график: {e}")


# ---------------------------
# КЛАСС ДЛЯ ПОСТРОЕНИЯ ГРАФИКОВ (PLOTLY)
# ---------------------------
class Plots:
    def __init__(self, data: pd.DataFrame):
        self.data = data

    # 1. Пирог: распределение по кампусам/уровням и т.п.
    def plot_pie_chart(self, column: str, title: str):
        if self.data.empty or column not in self.data.columns or self.data[column].dropna().empty:
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
        st.plotly_chart(fig, use_container_width=True)
        download_plotly_fig(fig, title)

    # 2. Бар-чарт: распределение по любому признаку
    def plot_bar_chart(self, column: str, title: str, x_label: str, y_label: str):
        if self.data.empty or column not in self.data.columns or self.data[column].dropna().empty:
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
        st.plotly_chart(fig, use_container_width=True)
        download_plotly_fig(fig, title)

    # 3. Среднее время ответа по кампусам
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
        st.plotly_chart(fig, use_container_width=True)
        download_plotly_fig(fig, "Среднее время ответа по кампусам")

    # 4. УСРЕДНЕНИЕ времени ответа по блокам
    def plot_averaged_response_time_chart(self, bin_size: int = 10):
        if self.data.empty or "response_time" not in self.data.columns:
            st.info("Нет данных для построения графика: Среднее время ответа (усреднение)")
            return
        df_copy = self.data.copy()
        df_copy["group"] = df_copy.index // bin_size
        grouped = df_copy.groupby("group")["response_time"].mean().reset_index()

        fig = px.bar(
            grouped,
            x="group",  # номер группы
            y="response_time",  # среднее время ответа
            title=f"Среднее время ответа (группы по {bin_size} запросов)",
            labels={
                "group": f"Номер группы (по {bin_size} запросов)",
                "response_time": "Среднее время ответа (сек)"
            }
        )
        st.plotly_chart(fig, use_container_width=True)
        download_plotly_fig(fig, f"Среднее время ответа (группы {bin_size})")

    # 5. Процент уточняющих вопросов
    def plot_follow_up_pie_chart(self):
        if self.data.empty:
            st.info("Нет данных для построения графика: Процент уточняющих вопросов")
            return
        flag = "has_chat_history" if "has_chat_history" in self.data.columns else "has_contexts"
        if flag not in self.data.columns or self.data[flag].dropna().empty:
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
        st.plotly_chart(fig, use_container_width=True)
        download_plotly_fig(fig, "Процент уточняющих вопросов")

    # 6. Метрика конфликтных ответов (гейдж)
    def plot_conflict_metric(self):
        if self.data.empty or "conflict_metric" not in self.data.columns:
            st.info("Нет данных для построения графика: Метрика конфликтного ответа")
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
                    {'range': [0, 100], 'color': "lightcoral"}
                ],
            }
        ))
        st.plotly_chart(fig, use_container_width=True)
        download_plotly_fig(fig, "Конфликтный ответ (%)")

    # 7. Сравнение среднего времени ответа по категориям
    def plot_response_time_by_category(self):
        if self.data.empty or "question_category" not in self.data.columns or "response_time" not in self.data.columns:
            st.info("Нет данных для построения графика: Сравнение времени ответа по категориям")
            return
        grouped = self.data.groupby("question_category")["response_time"].mean().reset_index()
        if grouped.empty:
            st.info("Нет данных для построения графика: Сравнение времени ответа по категориям")
            return
        fig = px.bar(
            grouped,
            x="question_category",
            y="response_time",
            title="Среднее время ответа по категориям вопросов",
            labels={
                "question_category": "Категория вопроса",
                "response_time": "Среднее время ответа (сек)"
            },
            color_discrete_sequence=px.colors.qualitative.Pastel
        )
        st.plotly_chart(fig, use_container_width=True)
        download_plotly_fig(fig, "Среднее время ответа по категориям")

    # 8. Боксплот распределения времени ответа
    def plot_response_time_boxplot(self):
        if self.data.empty or "response_time" not in self.data.columns:
            st.info("Нет данных для построения графика: Боксплот времени ответа")
            return
        fig = px.box(
            self.data,
            y="response_time",
            title="Распределение времени ответа (BoxPlot)",
            color_discrete_sequence=["#FF6666"]
        )
        st.plotly_chart(fig, use_container_width=True)
        download_plotly_fig(fig, "Распределение времени ответа (BoxPlot)")

    # 9. Новый график: метрики качества по категориям
    def plot_quality_metrics(self):
        needed_cols = [
            "question_category",
            "context_recall",
            "context_precision",
            "answer_correctness_literal",
            "answer_correctness_neural"
        ]
        for c in needed_cols:
            if c not in self.data.columns:
                st.info(f"Нет столбца '{c}' для построения метрик")
                return

        df_metrics = self.data[needed_cols].copy()
        if df_metrics.empty:
            st.info("Нет данных для метрик качества")
            return

        grouped = df_metrics.groupby("question_category").mean().reset_index()
        df_long = grouped.melt(
            id_vars="question_category",
            var_name="metric",
            value_name="value"
        )
        fig = px.bar(
            df_long,
            x="question_category",
            y="value",
            color="metric",
            barmode="group",
            title="Метрики контекста и корректности по категориям",
            labels={
                "question_category": "Категория вопроса",
                "value": "Среднее значение метрики",
                "metric": "Метрика"
            }
        )
        st.plotly_chart(fig, use_container_width=True)
        download_plotly_fig(fig, "Метрики по категориям")


# ---------------------------
# БОКОВАЯ ПАНЕЛЬ (ФИЛЬТРАЦИЯ + ЛОГО)
# ---------------------------
def sidebar_layout(df: pd.DataFrame):
    st.sidebar.image(
        "https://github.com/X-D-R/hackathon_hse25/raw/main/logo.png",
        use_container_width=True
    )
    st.sidebar.title("Фильтры")

    campuses = df["campus"].dropna().unique().tolist() if "campus" in df.columns else []
    categories = df["question_category"].dropna().unique().tolist() if "question_category" in df.columns else []
    education_levels = df["education_level"].dropna().unique().tolist() if "education_level" in df.columns else []

    selected_campus = st.sidebar.multiselect("Выберите кампус", campuses, default=campuses)
    selected_category = st.sidebar.multiselect("Выберите категорию вопроса", categories, default=categories)
    selected_edu_level = st.sidebar.multiselect("Выберите уровень образования", education_levels,
                                                default=education_levels)

    filtered_df = df.copy()
    if "campus" in df.columns:
        filtered_df = filtered_df[filtered_df["campus"].isin(selected_campus)]
    if "question_category" in df.columns:
        filtered_df = filtered_df[filtered_df["question_category"].isin(selected_category)]
    if "education_level" in df.columns:
        filtered_df = filtered_df[filtered_df["education_level"].isin(selected_edu_level)]

    return filtered_df


# ---------------------------
# ОСНОВНАЯ ЧАСТЬ ПРИЛОЖЕНИЯ
# ---------------------------
def main():
    data = load_data("output_last.json")
    df = process_data(data)
    filtered_df = sidebar_layout(df)
    if filtered_df.empty:
        st.info("Нет данных для отображения. Попробуйте изменить фильтры.")
        return

    graphs = Plots(filtered_df)

    st.markdown("<h1 style='text-align: center;'>Мониторинг качества чат-бота</h1>", unsafe_allow_html=True)

    # Кнопка скачивания JSON (сверху, но не в sidebar)
    st.markdown("### Экспорт данных")
    download_json(filtered_df.to_dict(orient="records"))

    # ----------------------------------------
    # 1) Большой график: метрики качества по категориям
    # ----------------------------------------
    st.markdown("## Метрики контекста и корректности")
    graphs.plot_quality_metrics()

    # ----------------------------------------
    # 2) Строка с тремя графиками
    # ----------------------------------------
    st.markdown("## Основные метрики (три графика в ряд)")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.subheader("Распределение запросов по кампусам")
        if "campus" in filtered_df.columns:
            graphs.plot_pie_chart("campus", "Распределение запросов по кампусам")
        else:
            st.info("Нет столбца 'campus'")
    with col2:
        st.subheader("Распределение по уровням образования")
        if "education_level" in filtered_df.columns:
            graphs.plot_pie_chart("education_level", "Распределение по уровням образования")
        else:
            st.info("Нет столбца 'education_level'")
    with col3:
        st.subheader("Частота уточняющих вопросов")
        graphs.plot_follow_up_pie_chart()

    # ----------------------------------------
    # 3) Большой график: сравнение времени ответа по категориям
    # ----------------------------------------
    st.markdown("## Сравнение времени ответа по категориям (большой график)")
    graphs.plot_response_time_by_category()

    # ----------------------------------------
    # 4) Строка из двух графиков
    # ----------------------------------------
    st.markdown("## Сравнения по времени ответа (две колонки)")
    col4, col5 = st.columns(2)
    with col4:
        st.subheader("Среднее время ответа по кампусам")
        graphs.plot_response_time_chart_with_campus()
    with col5:
        st.subheader("Усреднённое время ответа (по группам)")
        graphs.plot_averaged_response_time_chart(bin_size=10)

    # ----------------------------------------
    # 5) Дополнительные графики: боксплот и гейдж
    # ----------------------------------------
    st.markdown("## Дополнительные графики")
    st.subheader("Распределение времени ответа (BoxPlot)")
    graphs.plot_response_time_boxplot()
    st.subheader("Метрика конфликтного ответа")
    graphs.plot_conflict_metric()


if __name__ == "__main__":
    main()
