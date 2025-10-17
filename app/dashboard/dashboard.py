import tkinter as tk
from tkinter import scrolledtext
from tkinter import ttk, messagebox

import matplotlib.pyplot as plt
import pandas as pd
import psycopg2
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg


class PostgreSQLVisualizer:
    def __init__(self, root):
        self.root = root
        self.root.title("PostgreSQL Data Visualizer")
        self.root.geometry("1200x800")
        self.root.minsize(1000, 700)

        # Переменные для подключения
        self.host = tk.StringVar(value="localhost")
        self.port = tk.StringVar(value="5432")
        self.database = tk.StringVar(value="postgres")
        self.username = tk.StringVar(value="postgres")
        self.password = tk.StringVar()

        # Переменные для запроса и визуализации
        self.sql_query = tk.StringVar()
        self.chart_type = tk.StringVar(value="line")
        self.x_column = tk.StringVar()
        self.y_column = tk.StringVar()
        self.title = tk.StringVar(value="Data Visualization")
        self.x_label = tk.StringVar(value="X Axis")
        self.y_label = tk.StringVar(value="Y Axis")

        # Соединение и данные
        self.connection = None
        self.data = None

        # Создание интерфейса
        self.create_connection_panel()
        self.create_query_panel()
        self.create_visualization_panel()
        self.create_control_panel()

        # Настройка стилей
        self.setup_styles()

    def setup_styles(self):
        style = ttk.Style()
        style.configure("TFrame", background="#f0f0f0")
        style.configure("TLabel", background="#f0f0f0", font=('Arial', 10))
        style.configure("TButton", font=('Arial', 10), padding=5)
        style.configure("TEntry", font=('Arial', 10), padding=5)
        style.configure("TCombobox", font=('Arial', 10))

    def create_connection_panel(self):
        frame = ttk.LabelFrame(self.root, text="Подключение к PostgreSQL", padding=10)
        frame.grid(row=0, column=0, padx=10, pady=5, sticky="nsew")

        # Поля для ввода
        ttk.Label(frame, text="Хост:").grid(row=0, column=0, sticky="w", pady=2)
        ttk.Entry(frame, textvariable=self.host).grid(row=0, column=1, sticky="ew", pady=2)

        ttk.Label(frame, text="Порт:").grid(row=1, column=0, sticky="w", pady=2)
        ttk.Entry(frame, textvariable=self.port).grid(row=1, column=1, sticky="ew", pady=2)

        ttk.Label(frame, text="База данных:").grid(row=2, column=0, sticky="w", pady=2)
        ttk.Entry(frame, textvariable=self.database).grid(row=2, column=1, sticky="ew", pady=2)

        ttk.Label(frame, text="Пользователь:").grid(row=3, column=0, sticky="w", pady=2)
        ttk.Entry(frame, textvariable=self.username).grid(row=3, column=1, sticky="ew", pady=2)

        ttk.Label(frame, text="Пароль:").grid(row=4, column=0, sticky="w", pady=2)
        ttk.Entry(frame, textvariable=self.password, show="*").grid(row=4, column=1, sticky="ew", pady=2)

        # Кнопки подключения/отключения
        btn_frame = ttk.Frame(frame)
        btn_frame.grid(row=5, column=0, columnspan=2, pady=5)

        ttk.Button(btn_frame, text="Подключиться", command=self.connect_db).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="Отключиться", command=self.disconnect_db).pack(side="left", padx=5)

        # Индикатор подключения
        self.connection_status = ttk.Label(frame, text="Не подключено", foreground="red")
        self.connection_status.grid(row=6, column=0, columnspan=2, pady=5)

        frame.columnconfigure(1, weight=1)

    def create_query_panel(self):
        frame = ttk.LabelFrame(self.root, text="SQL Запрос", padding=10)
        frame.grid(row=1, column=0, padx=10, pady=5, sticky="nsew")

        # Текстовое поле для SQL запроса
        self.query_text = scrolledtext.ScrolledText(frame, wrap=tk.WORD, width=60, height=8, font=('Arial', 10))
        self.query_text.grid(row=0, column=0, sticky="nsew")

        # Кнопка выполнения запроса
        ttk.Button(frame, text="Выполнить запрос", command=self.execute_query).grid(row=1, column=0, pady=5)

        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(0, weight=1)

    def create_visualization_panel(self):
        frame = ttk.LabelFrame(self.root, text="Визуализация данных", padding=10)
        frame.grid(row=0, column=1, rowspan=3, padx=10, pady=5, sticky="nsew")

        # Фигура для графика
        self.figure = plt.figure(figsize=(10, 6), dpi=100)
        self.canvas = FigureCanvasTkAgg(self.figure, master=frame)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        # Таблица с данными
        self.table_frame = ttk.Frame(frame)
        self.tree_scroll = ttk.Scrollbar(self.table_frame)
        self.tree_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        self.tree = ttk.Treeview(self.table_frame, yscrollcommand=self.tree_scroll.set, selectmode="extended")
        self.tree.pack(fill=tk.BOTH, expand=True)
        self.tree_scroll.config(command=self.tree.yview)

        self.table_frame.pack_forget()

        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(0, weight=1)

    def create_control_panel(self):
        frame = ttk.LabelFrame(self.root, text="Настройки визуализации", padding=10)
        frame.grid(row=2, column=0, padx=10, pady=5, sticky="nsew")

        # Выбор типа графика
        ttk.Label(frame, text="Тип графика:").grid(row=0, column=0, sticky="w", pady=2)
        chart_types = ["line", "bar", "barh", "hist", "box", "kde", "area", "pie", "scatter"]
        ttk.Combobox(frame, textvariable=self.chart_type, values=chart_types).grid(row=0, column=1, sticky="ew", pady=2)

        # Выбор колонок
        ttk.Label(frame, text="Ось X:").grid(row=1, column=0, sticky="w", pady=2)
        self.x_combobox = ttk.Combobox(frame, textvariable=self.x_column)
        self.x_combobox.grid(row=1, column=1, sticky="ew", pady=2)

        ttk.Label(frame, text="Ось Y:").grid(row=2, column=0, sticky="w", pady=2)
        self.y_combobox = ttk.Combobox(frame, textvariable=self.y_column)
        self.y_combobox.grid(row=2, column=1, sticky="ew", pady=2)

        # Настройки графика
        ttk.Label(frame, text="Заголовок:").grid(row=3, column=0, sticky="w", pady=2)
        ttk.Entry(frame, textvariable=self.title).grid(row=3, column=1, sticky="ew", pady=2)

        ttk.Label(frame, text="Метка X:").grid(row=4, column=0, sticky="w", pady=2)
        ttk.Entry(frame, textvariable=self.x_label).grid(row=4, column=1, sticky="ew", pady=2)

        ttk.Label(frame, text="Метка Y:").grid(row=5, column=0, sticky="w", pady=2)
        ttk.Entry(frame, textvariable=self.y_label).grid(row=5, column=1, sticky="ew", pady=2)

        # Кнопки управления
        btn_frame = ttk.Frame(frame)
        btn_frame.grid(row=6, column=0, columnspan=2, pady=5)

        ttk.Button(btn_frame, text="Построить график", command=self.plot_data).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="Показать данные", command=self.show_data_table).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="Экспорт в PNG", command=self.export_plot).pack(side="left", padx=5)

        frame.columnconfigure(1, weight=1)

    def connect_db(self):
        try:
            self.connection = psycopg2.connect(
                host=self.host.get(),
                port=self.port.get(),
                database=self.database.get(),
                user=self.username.get(),
                password=self.password.get()
            )
            self.connection_status.config(text="Подключено", foreground="green")
            messagebox.showinfo("Успех", "Подключение к базе данных установлено!")
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось подключиться к базе данных:\n{str(e)}")
            self.connection_status.config(text="Ошибка подключения", foreground="red")

    def disconnect_db(self):
        if self.connection:
            try:
                self.connection.close()
                self.connection = None
                self.connection_status.config(text="Не подключено", foreground="red")
                messagebox.showinfo("Информация", "Соединение с базой данных закрыто")
            except Exception as e:
                messagebox.showerror("Ошибка", f"Ошибка при отключении:\n{str(e)}")
        else:
            messagebox.showinfo("Информация", "Нет активного соединения с БД")

    def execute_query(self):
        if not self.connection:
            messagebox.showerror("Ошибка", "Сначала подключитесь к базе данных")
            return

        query = self.query_text.get("1.0", tk.END).strip()
        if not query:
            messagebox.showerror("Ошибка", "Введите SQL запрос")
            return

        try:
            self.data = pd.read_sql_query(query, self.connection)

            # Обновляем выпадающие списки с колонками
            columns = self.data.columns.tolist()
            self.x_combobox['values'] = columns
            self.y_combobox['values'] = columns

            if columns:
                self.x_column.set(columns[0])
                if len(columns) > 1:
                    self.y_column.set(columns[1])

            messagebox.showinfo("Успех", f"Запрос выполнен. Получено {len(self.data)} строк.")
        except Exception as e:
            messagebox.showerror("Ошибка", f"Ошибка при выполнении запроса:\n{str(e)}")

    def plot_data(self):
        if self.data is None or self.data.empty:
            messagebox.showerror("Ошибка", "Нет данных для визуализации")
            return

        chart_type = self.chart_type.get()
        x_col = self.x_column.get()
        y_col = self.y_column.get()

        try:
            self.figure.clear()
            ax = self.figure.add_subplot(111)

            # Настройки графика
            ax.set_title(self.title.get())
            ax.set_xlabel(self.x_label.get())

            if chart_type != "pie":
                ax.set_ylabel(self.y_label.get())

            # Построение графика в зависимости от типа
            if chart_type == "line":
                if not y_col:
                    messagebox.showerror("Ошибка", "Для линейного графика нужна ось Y")
                    return
                self.data.plot(x=x_col, y=y_col, kind="line", ax=ax, legend=True)
            elif chart_type == "bar":
                if not y_col:
                    messagebox.showerror("Ошибка", "Для столбчатой диаграммы нужна ось Y")
                    return
                self.data.plot(x=x_col, y=y_col, kind="bar", ax=ax, legend=True)
            elif chart_type == "barh":
                if not y_col:
                    messagebox.showerror("Ошибка", "Для горизонтальной диаграммы нужна ось Y")
                    return
                self.data.plot(x=x_col, y=y_col, kind="barh", ax=ax, legend=True)
            elif chart_type == "hist":
                self.data[x_col].plot(kind="hist", ax=ax, legend=True)
            elif chart_type == "box":
                self.data.plot(y=y_col if y_col else x_col, kind="box", ax=ax)
            elif chart_type == "kde":
                self.data.plot(y=y_col if y_col else x_col, kind="kde", ax=ax, legend=True)
            elif chart_type == "area":
                if not y_col:
                    messagebox.showerror("Ошибка", "Для графика области нужна ось Y")
                    return
                self.data.plot(x=x_col, y=y_col, kind="area", ax=ax, legend=True)
            elif chart_type == "pie":
                if not y_col:
                    messagebox.showerror("Ошибка", "Для круговой диаграммы нужны значения")
                    return
                self.data.plot(y=y_col, kind="pie", labels=self.data[x_col], ax=ax, legend=False)
            elif chart_type == "scatter":
                if not y_col:
                    messagebox.showerror("Ошибка", "Для точечного графика нужна ось Y")
                    return
                self.data.plot(x=x_col, y=y_col, kind="scatter", ax=ax, legend=True)

            ax.grid(True)
            self.figure.tight_layout()
            self.canvas.draw()

            # Скрываем таблицу при показе графика
            self.table_frame.pack_forget()
        except Exception as e:
            messagebox.showerror("Ошибка", f"Ошибка при построении графика:\n{str(e)}")

    def show_data_table(self):
        if self.data is None:
            messagebox.showerror("Ошибка", "Нет данных для отображения")
            return

        # Очищаем таблицу
        for item in self.tree.get_children():
            self.tree.delete(item)

        # Устанавливаем колонки
        self.tree["columns"] = list(self.data.columns)
        self.tree.column("#0", width=0, stretch=tk.NO)

        for col in self.data.columns:
            self.tree.column(col, anchor=tk.W, width=100)
            self.tree.heading(col, text=col, anchor=tk.W)

        # Добавляем данные (первые 100 строк для производительности)
        for i, row in self.data.head(100).iterrows():
            self.tree.insert("", tk.END, values=list(row))

        # Показываем таблицу
        self.canvas.get_tk_widget().pack_forget()
        self.table_frame.pack(fill=tk.BOTH, expand=True)

    def export_plot(self):
        if not hasattr(self, 'figure') or not self.figure.axes:
            messagebox.showerror("Ошибка", "Нет графика для экспорта")
            return

        from tkinter import filedialog
        file_path = filedialog.asksaveasfilename(
            defaultextension=".png",
            filetypes=[("PNG Image", "*.png"), ("All Files", "*.*")],
            title="Сохранить график как"
        )

        if file_path:
            try:
                self.figure.savefig(file_path, dpi=300, bbox_inches='tight')
                messagebox.showinfo("Успех", f"График успешно сохранен в:\n{file_path}")
            except Exception as e:
                messagebox.showerror("Ошибка", f"Не удалось сохранить график:\n{str(e)}")


if __name__ == "__main__":
    root = tk.Tk()
    app = PostgreSQLVisualizer(root)

    # Настройка весов строк и столбцов для правильного масштабирования
    root.grid_rowconfigure(0, weight=1)
    root.grid_rowconfigure(1, weight=1)
    root.grid_rowconfigure(2, weight=1)
    root.grid_columnconfigure(0, weight=1)
    root.grid_columnconfigure(1, weight=3)

    root.mainloop()