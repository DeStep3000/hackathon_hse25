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
    df["has_chat_history"] = df["chat_history"].apply(lambda x: len(x.get("old_questions", [])) > 0)
    df["response_time"] = pd.to_numeric(df["Время ответа модели"], errors="coerce")

    # Доп. метрика: "убедительный, но неверный ответ"
    df["conflict_metric"] = df.apply(
        lambda row: 1 if (len(row.get("chat_history", {}).get("old_questions", [])) > 1 and row["response_time"] > 3)
        else 0,
        axis=1
    )
    return df


# ---------------------------
# ЭКСПОРТ ДАННЫХ (JSON)
# ---------------------------
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
# ЭКСПОРТ ГРАФИКОВ ЧЕРЕЗ PLOTLY (KALEIDO)
# ---------------------------
def download_plotly_fig(fig, filename: str):
    """
    Сохраняет Plotly-график в PNG с помощью Kaleido и даёт кнопку для скачивания.
    """
    try:
        img_bytes = fig.to_image(format="png")
        st.download_button(
            label=f"📊 Скачать график «{filename}»",
            data=img_bytes,
            file_name=f"{filename}.png",
            mime="image/png"
        )
    except Exception as e:
        st.error(f"Не удалось экспортировать график в PNG. Убедитесь, что kaleido установлен. Ошибка: {e}")


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
        download_plotly_fig(fig, "Среднее время ответа по кампусам")

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
        download_plotly_fig(fig, "Динамика времени ответа модели")

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
        download_plotly_fig(fig, "Процент уточняющих вопросов пользователей")

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

    campuses = df["Кампус"].dropna().unique().tolist()
    categories = df["Категория вопроса"].dropna().unique().tolist()
    education_levels = df["Уровень образования"].dropna().unique().tolist()

    selected_campus = st.sidebar.multiselect("Выберите кампус", campuses, default=campuses)
    selected_category = st.sidebar.multiselect("Выберите категорию вопроса", categories, default=categories)
    selected_edu_level = st.sidebar.multiselect("Выберите уровень образования", education_levels,
                                                default=education_levels)

    st.sidebar.subheader("Экспорт данных")
    # Кнопка скачивания JSON
    download_json(df.to_dict(orient="records"))

    filtered_df = df[
        (df["Кампус"].isin(selected_campus)) &
        (df["Категория вопроса"].isin(selected_category)) &
        (df["Уровень образования"].isin(selected_edu_level))
        ]
    return filtered_df


# ---------------------------
# ОСНОВНОЙ БЛОК ПРИЛОЖЕНИЯ
# ---------------------------
def main():
    # 1. Загрузка и подготовка данных
    data = load_data("logs.json")
    df = process_data(data)

    # 2. Боковая панель (фильтрация + экспорт)
    filtered_df = sidebar_layout(df)

    # Если после фильтров нет данных
    if filtered_df.empty:
        st.info("Нет данных для отображения. Попробуйте изменить фильтры.")
        return

    # 3. Инициализация класса для построения графиков
    graphs = Plots(filtered_df)

    # 4. Заголовок
    st.markdown("<h1 style='text-align: center;'>Мониторинг качества чат-бота</h1>", unsafe_allow_html=True)

    # 5. Построение графиков
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


# ---------------------------
# ЗАПУСК
# ---------------------------
if __name__ == "__main__":
    main()
