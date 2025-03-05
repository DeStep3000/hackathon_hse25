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

# ---------------------------
# CSS-ХАК для кнопок скачивания
# ---------------------------
st.markdown("""
<style>
button[data-testid="stDownloadButton"] {
    width: 120px !important;
    height: 35px !important;
    font-size: 12px;
    padding: 0 4px;
    margin-top: 4px;
}
</style>
""", unsafe_allow_html=True)

# Автоперезагрузка (по желанию)
time_interval = 10
st_autorefresh(interval=time_interval * 1000, key="data_refresh")


def load_data(file_name: str):
    with open(file_name, "r", encoding="utf-8") as file:
        return json.load(file)


def process_data(data):
    df = pd.DataFrame(data)
    # Вычисляем conflict_metric
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

    # Преобразуем время ответа в число
    df["response_time"] = pd.to_numeric(df["response_time"], errors="coerce")
    return df


def download_json(data):
    json_data = json.dumps(data, indent=4, ensure_ascii=False, default=str)
    st.download_button(
        label="📥 Скачать JSON",
        data=json_data,
        file_name="chatbot_logs.json",
        mime="application/json"
    )


# ---------------------------
# Функция для вывода графика с кнопкой скачивания, расположенной ПОД графиком
# ---------------------------
def show_plot_with_download_below(fig, filename: str):
    st.plotly_chart(fig, use_container_width=True)
    try:
        img_bytes = fig.to_image(format="png")
        st.download_button(
            label="Скачать график",
            data=img_bytes,
            file_name=f"{filename}.png",
            mime="image/png"
        )
    except Exception as e:
        st.error(f"Ошибка экспорта: {e}")


# ---------------------------
# КЛАСС ДЛЯ ПОСТРОЕНИЯ ГРАФИКОВ
# ---------------------------
class Plots:
    def __init__(self, data: pd.DataFrame):
        self.data = data

    # Пироговая диаграмма
    def plot_pie_chart(self, column: str, _unused_title: str):
        if self.data.empty or column not in self.data.columns or self.data[column].dropna().empty:
            return st.info("Нет данных для построения графика")
        counts = self.data[column].value_counts()
        fig = px.pie(
            names=counts.index,
            values=counts.values,
            hole=0.4,
            color_discrete_sequence=px.colors.sequential.RdBu
        )
        show_plot_with_download_below(fig, f"pie_{column}")

    # Столбчатая диаграмма
    def plot_bar_chart(self, column: str, _unused_title: str, x_label: str, y_label: str):
        if self.data.empty or column not in self.data.columns or self.data[column].dropna().empty:
            return st.info("Нет данных для построения графика")
        counts = self.data[column].value_counts()
        if counts.empty:
            return st.info("Нет данных для построения графика")
        fig = px.bar(
            x=counts.index,
            y=counts.values,
            labels={'x': x_label, 'y': y_label},
            text_auto=True,
            color_discrete_sequence=px.colors.qualitative.Vivid
        )
        show_plot_with_download_below(fig, f"bar_{column}")

    # Среднее время ответа по кампусам
    def plot_response_time_chart_with_campus(self):
        if self.data.empty or "campus" not in self.data.columns or "response_time" not in self.data.columns:
            return st.info("Нет данных для построения графика")
        group_data = self.data.groupby("campus")["response_time"].mean().reset_index()
        if group_data.empty:
            return st.info("Нет данных для построения графика")
        fig = px.bar(
            group_data,
            x="campus",
            y="response_time",
            color="campus",
            text_auto=True,
            color_discrete_sequence=px.colors.qualitative.Set3
        )
        show_plot_with_download_below(fig, "resp_time_by_campus")

    # УСРЕДНЕНИЕ времени ответа (по группам запросов)
    def plot_averaged_response_time_chart(self, bin_size: int = 10):
        if self.data.empty or "response_time" not in self.data.columns:
            return st.info("Нет данных для построения графика")
        df_copy = self.data.copy()
        df_copy["group"] = df_copy.index // bin_size
        grouped = df_copy.groupby("group")["response_time"].mean().reset_index()
        fig = px.bar(
            grouped,
            x="group",
            y="response_time",
            labels={
                "group": f"Номер группы (по {bin_size} запросов)",
                "response_time": "Среднее время ответа (сек)"
            }
        )
        show_plot_with_download_below(fig, "resp_time_averaged")

    # Пирог: процент уточняющих вопросов
    def plot_follow_up_pie_chart(self):
        if self.data.empty:
            return st.info("Нет данных для построения графика")
        flag = "has_chat_history" if "has_chat_history" in self.data.columns else "has_contexts"
        if flag not in self.data.columns or self.data[flag].dropna().empty:
            return st.info("Нет данных для построения графика")
        avg_flag = self.data[flag].mean()
        fig = px.pie(
            names=["Без уточнений", "С уточнениями"],
            values=[1 - avg_flag, avg_flag],
            hole=0.3,
            color_discrete_sequence=px.colors.qualitative.Pastel
        )
        show_plot_with_download_below(fig, "follow_up_pie")

    # Гейдж: метрика конфликтного ответа
    def plot_conflict_metric(self):
        if self.data.empty or "conflict_metric" not in self.data.columns:
            return st.info("Нет данных для построения графика")
        conflict_rate = self.data["conflict_metric"].mean() * 100
        fig = go.Figure(go.Indicator(
            mode="gauge+number",
            value=conflict_rate,
            gauge={
                'axis': {'range': [0, 100]},
                'bar': {'color': "red"},
                'steps': [{'range': [0, 100], 'color': "lightcoral"}],
            }
        ))
        show_plot_with_download_below(fig, "conflict_metric")

    # Среднее время ответа по категориям
    def plot_response_time_by_category(self):
        if self.data.empty or "question_category" not in self.data.columns or "response_time" not in self.data.columns:
            return st.info("Нет данных для построения графика")
        grouped = self.data.groupby("question_category")["response_time"].mean().reset_index()
        if grouped.empty:
            return st.info("Нет данных для построения графика")
        fig = px.bar(
            grouped,
            x="question_category",
            y="response_time",
            color_discrete_sequence=px.colors.qualitative.Pastel
        )
        show_plot_with_download_below(fig, "resp_time_by_category")

    # BoxPlot времени ответа
    def plot_response_time_boxplot(self):
        if self.data.empty or "response_time" not in self.data.columns:
            return st.info("Нет данных для построения графика")
        fig = px.box(
            self.data,
            y="response_time",
            color_discrete_sequence=["#FF6666"]
        )
        show_plot_with_download_below(fig, "resp_time_boxplot")

    # (1) Четыре отдельных графика (по одной метрике на каждый)
    def plot_quality_metrics_separate(self):
        needed_cols = [
            "question_category",
            "context_recall",
            "context_precision",
            "answer_correctness_literal",
            "answer_correctness_neural"
        ]
        for c in needed_cols:
            if c not in self.data.columns:
                return st.info(f"Нет столбца '{c}' для построения метрик.")

        # Список метрик
        metrics = [
            "context_recall",
            "context_precision",
            "answer_correctness_literal",
            "answer_correctness_neural"
        ]

        # Создаём 4 колонки под 4 графика
        cols = st.columns(4)
        for i, metric in enumerate(metrics):
            # Группируем по категориям вопросов
            grouped = self.data.groupby("question_category")[metric].mean().reset_index()

            fig = px.bar(
                grouped,
                x="question_category",
                y=metric,
                labels={
                    "question_category": "Категория вопроса",
                    metric: "Среднее значение"
                },
                title=f"Метрика: {metric}"
            )
            with cols[i]:
                show_plot_with_download_below(fig, f"separate_{metric}")

    # (2) Сводный график, где все 4 метрики на одном полотне (со шкалированием 0-100)
    def plot_quality_metrics_combined(self):
        needed_cols = [
            "question_category",
            "context_recall",
            "context_precision",
            "answer_correctness_literal",
            "answer_correctness_neural"
        ]
        for c in needed_cols:
            if c not in self.data.columns:
                return st.info(f"Нет столбца '{c}' для построения метрик.")

        grouped = self.data.groupby("question_category")[
            ["context_recall", "context_precision", "answer_correctness_literal", "answer_correctness_neural"]
        ].mean().reset_index()

        # Масштабируем каждую метрику к диапазону [0, 100]
        for metric in ["context_recall", "context_precision", "answer_correctness_literal",
                       "answer_correctness_neural"]:
            max_val = grouped[metric].max()
            if max_val > 0:
                grouped[metric] = grouped[metric] / max_val * 100

        # Переводим в длинный формат
        melted = grouped.melt(
            id_vars="question_category",
            value_vars=["context_recall", "context_precision", "answer_correctness_literal",
                        "answer_correctness_neural"],
            var_name="metric",
            value_name="mean_value"
        )

        fig = px.bar(
            melted,
            x="question_category",
            y="mean_value",
            color="metric",
            barmode="group",
            labels={
                "question_category": "Категория вопроса",
                "mean_value": "Среднее (0–100)",
                "metric": "Метрика"
            },
            # Убираем title, чтобы не дублировать заголовок со страницы
            title=""
        )
        show_plot_with_download_below(fig, "combined_quality_metrics")


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


def main():
    data = load_data("output_last.json")
    df = process_data(data)
    filtered_df = sidebar_layout(df)
    if filtered_df.empty:
        st.info("Нет данных для отображения. Попробуйте изменить фильтры.")
        return

    graphs = Plots(filtered_df)

    st.markdown("<h1 style='text-align: center;'>Мониторинг качества чат-бота</h1>", unsafe_allow_html=True)

    # Кнопка скачивания JSON
    st.markdown("### Экспорт данных")
    download_json(filtered_df.to_dict(orient="records"))

    # --- 1) Четыре отдельных графика (каждая метрика отдельно) ---
    st.markdown("## Отдельные метрики качества")
    graphs.plot_quality_metrics_separate()

    # --- 2) Один общий график со всеми метриками (со шкалированием), без повторяющегося заголовка ---
    st.markdown("## Сводный график метрик качества")
    graphs.plot_quality_metrics_combined()

    # --- 3) Основные метрики ---
    st.markdown("## Основные метрики")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.subheader("Распределение запросов по кампусам")
        if "campus" in filtered_df.columns:
            graphs.plot_pie_chart("campus", "unused_title")
        else:
            st.info("Нет столбца 'campus'")

    with col2:
        st.subheader("Распределение по уровням образования")
        if "education_level" in filtered_df.columns:
            graphs.plot_pie_chart("education_level", "unused_title")
        else:
            st.info("Нет столбца 'education_level'")

    with col3:
        st.subheader("Частота уточняющих вопросов")
        graphs.plot_follow_up_pie_chart()

    # --- 4) Сравнение времени ответа по категориям ---
    st.markdown("## Сравнение времени ответа по категориям")
    graphs.plot_response_time_by_category()

    # --- 5) Среднее время ответа (кампусы / группировка) ---
    st.markdown("## Сравнения по времени ответа")
    col4, col5 = st.columns(2)
    with col4:
        st.subheader("Среднее время ответа по кампусам")
        graphs.plot_response_time_chart_with_campus()
    with col5:
        st.subheader("Усреднённое время ответа (по группам)")
        graphs.plot_averaged_response_time_chart(bin_size=10)

    # --- 6) Дополнительные графики ---
    st.markdown("## Дополнительные графики")
    st.subheader("Распределение времени ответа (BoxPlot)")
    graphs.plot_response_time_boxplot()

    st.subheader("Метрика конфликтного ответа")
    graphs.plot_conflict_metric()


if __name__ == "__main__":
    main()
