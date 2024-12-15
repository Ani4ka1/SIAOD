import ttkbootstrap as tb
from ttkbootstrap.constants import *
from tkinter import messagebox
from tkinter import ttk
import pandas as pd
import random
from datetime import datetime, timedelta

class RouteScheduler:
    def __init__(self, root):
        self.root = root
        self.root.title("Route Scheduler")
        self.root.geometry("1920x1080")
        self.root.resizable(False, False)
        self.type_a_drivers = []
        self.type_b_drivers = []
        self.route_options = ['до конечной и обратно', 'до конечной']
        self.shift_duration_a = 8
        self.shift_duration_b = 12
        self.travel_duration_minutes = 60
        self.workday_start = '06:00'
        self.workday_end = '03:00'
        self.theme_style = tb.Style()
        self.theme_style.theme_use('superhero')
        self.primary_frame = tb.Frame(self.root)
        self.primary_frame.pack(fill=BOTH, expand=True)
        self.build_navigation_panel()
        self.main_content = tb.Frame(self.primary_frame)
        self.main_content.pack(side=LEFT, fill=BOTH, expand=True)
        self.setup_driver_registration()
        self.setup_route_configuration()
        self.setup_timetable_creation()
        self.display_section("registration")
        self.status_label = tb.Label(self.root, text="", font=("Helvetica", 14), bootstyle=INFO)
        self.status_label.pack(pady=10)
    
    def is_weekend(self, selected_day):
        return selected_day in ['Суббота', 'Воскресенье']
    
    def calculate_route_completion(self, start_time, route_time):
        start_time_obj = datetime.strptime(start_time, "%H:%M")
        end_time_obj = start_time_obj + timedelta(minutes=route_time)
        return end_time_obj.strftime("%H:%M")
    
    def standardize_time_interval(self, start_str, end_str):
        start = datetime.strptime(start_str, "%H:%M")
        end = datetime.strptime(end_str, "%H:%M")
        if end < start:
            end += timedelta(days=1)
        return start, end
    
    def detect_time_overlap(self, start_time, end_time, busy_times):
        s, e = self.standardize_time_interval(start_time, end_time)
        for (bs, be) in busy_times:
            b_s, b_e = self.standardize_time_interval(bs, be)
            if s < b_e and e > b_s:
                return True
        return False
    
    def find_free_periods(self, driver_busy_times, route_time, break_time):
        free_slots = []
        for driver, periods in driver_busy_times.items():
            normalized_periods = []
            for (st, ft) in periods:
                s_t, f_t = self.standardize_time_interval(st, ft)
                normalized_periods.append((s_t, f_t))
            normalized_periods.sort(key=lambda x: x[0])
            current = datetime.strptime("06:00", "%H:%M")
            work_end = datetime.strptime("03:00", "%H:%M") + timedelta(days=1)
            for (st, et) in normalized_periods:
                if (st - current).total_seconds() / 60 >= route_time + break_time:
                    free_slots.append((current.strftime("%H:%M"), st.strftime("%H:%M")))
                current = et
            if (work_end - current).total_seconds() / 60 >= route_time + break_time:
                free_slots.append((current.strftime("%H:%M"), work_end.strftime("%H:%M")))
        return free_slots
    
    def calculate_additional_driver_needs(self, num_routes, driver_list, shift_duration):
        max_routes_per_driver = int(shift_duration * 60 / self.travel_duration_minutes)
        required_drivers = (num_routes + max_routes_per_driver - 1) // max_routes_per_driver
        if len(driver_list) >= required_drivers:
            return 0
        else:
            return required_drivers - len(driver_list)
    
    def can_assign_route(self, candidate_start_time, route_time, driver, driver_busy_times, driver_worked_hours, driver_route_counts, min_break_time):
        candidate_end_time = self.calculate_route_completion(candidate_start_time, route_time)
        if self.detect_time_overlap(candidate_start_time, candidate_end_time, driver_busy_times[driver]):
            return False
        if driver_busy_times[driver]:
            last_start, last_end = driver_busy_times[driver][-1]
            last_end_obj = datetime.strptime(last_end, "%H:%M")
            last_start_obj = datetime.strptime(last_start, "%H:%M")
            if last_end_obj < last_start_obj:
                last_end_obj += timedelta(days=1)
            candidate_start_obj = datetime.strptime(candidate_start_time, "%H:%M")
            if candidate_start_obj < last_end_obj:
                return False
            if (candidate_start_obj - last_end_obj).total_seconds() / 60 < min_break_time:
                return False
        worked_hours = driver_worked_hours[driver]
        if driver in self.type_a_drivers and worked_hours >= self.shift_duration_a:
            return False
        if driver in self.type_b_drivers and worked_hours >= self.shift_duration_b:
            return False
        candidate_end_obj = datetime.strptime(candidate_end_time, "%H:%M")
        if candidate_end_obj < datetime.strptime(candidate_start_time, "%H:%M"):
            candidate_end_obj += timedelta(days=1)
        end_work_obj = datetime.strptime("03:00", "%H:%M") + timedelta(days=1)
        if candidate_end_obj > end_work_obj:
            return False
        return True
    
    def allocate_driver_to_route(self, route_time, break_time, min_break_time, driver_list, driver_busy_times, driver_worked_hours, selected_day, driver_route_counts):
        for _ in range(50):
            free_slots = self.find_free_periods(driver_busy_times, route_time, break_time)
            if not free_slots:
                return None
            slot_start, slot_end = random.choice(free_slots)
            slot_start_obj = datetime.strptime(slot_start, "%H:%M")
            slot_end_obj = datetime.strptime(slot_end, "%H:%M")
            if slot_end_obj < slot_start_obj:
                slot_end_obj += timedelta(days=1)
            max_start = (slot_end_obj - slot_start_obj).total_seconds() / 60 - route_time
            if max_start < 0:
                continue
            offset = random.randint(0, int(max_start))
            candidate_start_obj = slot_start_obj + timedelta(minutes=offset)
            candidate_start = candidate_start_obj.strftime("%H:%M")
            random.shuffle(driver_list)
            for driver in driver_list:
                if driver in self.type_a_drivers and self.is_weekend(selected_day):
                    continue
                if self.can_assign_route(candidate_start, route_time, driver, driver_busy_times, driver_worked_hours, driver_route_counts, min_break_time):
                    return (driver, candidate_start)
        return None
    
    def generate_genetic_schedule_attempt(self, driver_list, shift_duration, num_routes, selected_day, break_time=10, min_break_time=30):
        available_drivers = list(driver_list)
        random.shuffle(available_drivers)
        driver_busy_times = {driver: [] for driver in available_drivers}
        driver_worked_hours = {driver: 0 for driver in available_drivers}
        driver_route_counts = {driver: 0 for driver in available_drivers}
        schedule = []
        start_time = datetime.strptime("06:00", "%H:%M")
        end_work_time = datetime.strptime("03:00", "%H:%M") + timedelta(days=1)
        for _ in range(num_routes):
            placed = False
            candidate_start_time = start_time
            candidate_end_time = candidate_start_time + timedelta(minutes=self.travel_duration_minutes)
            if candidate_end_time > end_work_time:
                route_type_selected = random.choice(self.route_options)
                route_type = f"{route_type_selected} (доп рейс)"
            else:
                route_type = random.choice(self.route_options)
            for driver in available_drivers:
                if self.can_assign_route(candidate_start_time.strftime("%H:%M"), self.travel_duration_minutes, driver, driver_busy_times, driver_worked_hours, driver_route_counts, min_break_time):
                    schedule.append({
                        'Водитель': driver,
                        'Тип маршрута': route_type,
                        'Время начала': candidate_start_time.strftime("%H:%M"),
                        'Время окончания': candidate_end_time.strftime("%H:%M"),
                        'Маршрутов за смену': driver_route_counts[driver] + 1
                    })
                    driver_busy_times[driver].append((candidate_start_time.strftime("%H:%M"), candidate_end_time.strftime("%H:%M")))
                    driver_route_counts[driver] += 1
                    driver_worked_hours[driver] += self.travel_duration_minutes / 60
                    placed = True
                    break
            if not placed:
                break
            start_time = candidate_end_time + timedelta(minutes=break_time)
            if start_time >= end_work_time:
                start_time = datetime.strptime("06:00", "%H:%M")
                route_type = f"{random.choice(self.route_options)} (доп рейс)"
        return schedule, len(schedule)
    
    def assess_schedule_quality(self, schedule):
        return len(schedule)
    
    def execute_crossover(self, parent1, parent2):
        if not parent1 or not parent2:
            return parent1, parent2
        crossover_point = len(parent1) // 2
        child1 = parent1[:crossover_point] + parent2[crossover_point:]
        child2 = parent2[:crossover_point] + parent1[crossover_point:]
        return child1, child2
    
    def execute_mutation(self, schedule, driver_list, break_time=10):
        if not schedule:
            return schedule
        mutated_schedule = schedule.copy()
        mutation_point = random.randint(0, len(mutated_schedule) - 1)
        new_driver = random.choice(driver_list)
        mutated_schedule[mutation_point]['Водитель'] = new_driver
        if random.random() < 0.5:
            original_start = mutated_schedule[mutation_point]['Время начала']
            original_end = mutated_schedule[mutation_point]['Время окончания']
            try:
                start_obj = datetime.strptime(original_start, "%H:%M") + timedelta(minutes=random.randint(-15, 15))
                end_obj = datetime.strptime(original_end, "%H:%M") + timedelta(minutes=random.randint(-15, 15))
                mutated_schedule[mutation_point]['Время начала'] = start_obj.strftime("%H:%M")
                mutated_schedule[mutation_point]['Время окончания'] = end_obj.strftime("%H:%M")
            except ValueError:
                pass
        return mutated_schedule
    
    def display_generated_timetable(self, result_window, schedule_df, title_text="Итоговое расписание"):
        result_window.title(title_text)
        if not schedule_df.empty:
            frame = tb.Frame(result_window)
            frame.pack(fill='both', expand=True, padx=20, pady=20)
            scrollbar = ttk.Scrollbar(frame, orient="vertical")
            scrollbar.pack(side='right', fill='y')
            columns = list(schedule_df.columns)
            tree = ttk.Treeview(frame, columns=columns, show='headings', yscrollcommand=scrollbar.set)
            for col in columns:
                tree.heading(col, text=col)
                tree.column(col, width=150, anchor='center')
            for index, row in schedule_df.iterrows():
                tree.insert("", "end", values=list(row))
            scrollbar.config(command=tree.yview)
            tree.pack(fill='both', expand=True)
        else:
            message = "Не удалось сгенерировать расписание.\nНужно добавить водителей или уменьшить число рейсов."
            messagebox.showerror("Ошибка", message)
    
    def build_optimized_timetable(self, driver_list, shift_duration, num_routes, selected_day, parent_window, break_time=10, min_break_time=30):
        additional_needed = self.calculate_additional_driver_needs(num_routes, driver_list, shift_duration)
        if additional_needed > 0:
            message = f"Нехватка сотрудников.\nНужно добавить ещё {additional_needed} водителей или уменьшить число рейсов."
            messagebox.showerror("Ошибка", message)
            return
        schedule = []
        driver_busy_times = {d: [] for d in driver_list}
        driver_worked_hours = {d: 0 for d in driver_list}
        driver_route_counts = {d: 0 for d in driver_list}
        current_time = datetime.strptime("06:00", "%H:%M")
        work_end = datetime.strptime("03:00", "%H:%M") + timedelta(days=1)
        for _ in range(num_routes):
            route_type = random.choice(self.route_options)
            actual_time = self.travel_duration_minutes * 2 if 'обратно' in route_type else self.travel_duration_minutes
            candidate_start_str = current_time.strftime("%H:%M")
            candidate_end_str = self.calculate_route_completion(candidate_start_str, actual_time)
            candidate_end_obj = datetime.strptime(candidate_end_str, "%H:%M")
            if candidate_end_obj < current_time:
                candidate_end_obj += timedelta(days=1)
            if candidate_end_obj > work_end:
                final_type = f"{route_type} (доп рейс)"
                result = self.allocate_driver_to_route(actual_time, break_time, min_break_time, driver_list, driver_busy_times, driver_worked_hours, selected_day, driver_route_counts)
                if result is None:
                    message = "Расписание не утверждено.\nНужно добавить сотрудников или уменьшить число рейсов."
                    messagebox.showerror("Ошибка", message)
                    return
                else:
                    driver, slot_start = result
                    cend = self.calculate_route_completion(slot_start, actual_time)
                    worked_minutes = (datetime.strptime(cend, "%H:%M") - datetime.strptime(slot_start, "%H:%M")).seconds / 60
                    schedule.append({
                        'Водитель': driver,
                        'Тип маршрута': final_type,
                        'Время начала': slot_start,
                        'Время окончания': cend,
                        'Маршрутов за смену': driver_route_counts[driver] + 1
                    })
                    driver_busy_times[driver].append((slot_start, cend))
                    driver_worked_hours[driver] += worked_minutes / 60
            else:
                placed = False
                copy_drivers = list(driver_list)
                random.shuffle(copy_drivers)
                for driver in copy_drivers:
                    if driver in self.type_a_drivers and self.is_weekend(selected_day):
                        continue
                    if self.can_assign_route(candidate_start_str, actual_time, driver, driver_busy_times, driver_worked_hours, driver_route_counts, min_break_time):
                        worked_minutes = (candidate_end_obj - datetime.strptime(candidate_start_str, "%H:%M")).seconds / 60
                        schedule.append({
                            'Водитель': driver,
                            'Тип маршрута': route_type,
                            'Время начала': candidate_start_str,
                            'Время окончания': candidate_end_str,
                            'Маршрутов за смену': driver_route_counts[driver] + 1
                        })
                        driver_busy_times[driver].append((candidate_start_str, candidate_end_str))
                        driver_route_counts[driver] += 1
                        driver_worked_hours[driver] += worked_minutes / 60
                        placed = True
                        current_time = candidate_end_obj + timedelta(minutes=break_time + min_break_time)
                        break
                if not placed:
                    result = self.allocate_driver_to_route(actual_time, break_time, min_break_time, driver_list, driver_busy_times, driver_worked_hours, selected_day, driver_route_counts)
                    if result is None:
                        message = "Расписание не утверждено.\nНужно добавить сотрудников или уменьшить число рейсов."
                        messagebox.showerror("Ошибка", message)
                        return
                    else:
                        driver, slot_start = result
                        cend = self.calculate_route_completion(slot_start, actual_time)
                        worked_minutes = (datetime.strptime(cend, "%H:%M") - datetime.strptime(slot_start, "%H:%M")).seconds / 60
                        final_type = f"{route_type} (доп рейс)"
                        schedule.append({
                            'Водитель': driver,
                            'Тип маршрута': final_type,
                            'Время начала': slot_start,
                            'Время окончания': cend,
                            'Маршрутов за смену': driver_route_counts[driver] + 1
                        })
                        driver_busy_times[driver].append((slot_start, cend))
                        driver_worked_hours[driver] += worked_minutes / 60
        result_window = tb.Toplevel(parent_window)
        df = pd.DataFrame(schedule)
        if not df.empty:
            self.display_generated_timetable(result_window, df, "Итоговое расписание:")
        else:
            self.display_generated_timetable(result_window, pd.DataFrame(), "Расписание не сформировано.")
    
    def execute_genetic_algorithm(self, driver_list, shift_duration, num_routes, selected_day, generations=50, population_size=20, mutation_rate=0.1, break_time=10, min_break_time=30):
        population = []
        for _ in range(population_size):
            schedule, score = self.generate_genetic_schedule_attempt(driver_list, shift_duration, num_routes, selected_day, break_time, min_break_time)
            population.append({'schedule': schedule, 'fitness': self.assess_schedule_quality(schedule)})
        best_schedule = None
        best_fitness = -1
        for _ in range(generations):
            population = sorted(population, key=lambda x: x['fitness'], reverse=True)
            current_best = population[0]
            if current_best['fitness'] > best_fitness:
                best_fitness = current_best['fitness']
                best_schedule = current_best['schedule']
            if best_fitness >= num_routes:
                break
            parents = population[:population_size // 2]
            new_population = parents.copy()
            while len(new_population) < population_size:
                parent1, parent2 = random.sample(parents, 2)
                child1_schedule, child2_schedule = self.execute_crossover(parent1['schedule'], parent2['schedule'])
                child1 = {'schedule': child1_schedule, 'fitness': self.assess_schedule_quality(child1_schedule)}
                child2 = {'schedule': child2_schedule, 'fitness': self.assess_schedule_quality(child2_schedule)}
                new_population.extend([child1, child2])
            for individual in new_population:
                if random.random() < mutation_rate:
                    mutated_schedule = self.execute_mutation(individual['schedule'], driver_list, break_time)
                    individual['schedule'] = mutated_schedule
                    individual['fitness'] = self.assess_schedule_quality(mutated_schedule)
            population = new_population[:population_size]
        result_window = tb.Toplevel(self.root)
        if best_fitness >= num_routes:
            title_text = "Генетический алгоритм завершен. Лучшее расписание"
        else:
            title_text = "Генетический алгоритм завершен. Лучшее найденное расписание"
        if best_schedule and best_fitness > 0:
            df = pd.DataFrame(best_schedule)
            self.display_generated_timetable(result_window, df, f"{title_text} ({best_fitness} рейсов):")
        else:
            self.display_generated_timetable(result_window, pd.DataFrame(), title_text)
    
    def start_genetic_schedule(self):
        try:
            num_routes = int(self.total_routes_entry.get())
            selected_day = self.selected_day_var.get()
            all_drivers = self.type_a_drivers + self.type_b_drivers
            shift_duration = max(self.shift_duration_a, self.shift_duration_b)
            additional_needed = self.calculate_additional_driver_needs(num_routes, all_drivers, shift_duration)
            if additional_needed > 0:
                message = f"Недостаточно водителей.\nДобавьте минимум {additional_needed} водителей или уменьшите число рейсов."
                messagebox.showerror("Ошибка", message)
                return
            if not self.type_a_drivers and not self.type_b_drivers:
                messagebox.showerror("Ошибка", "Нет водителей.")
                return
            if self.is_weekend(selected_day) and not self.type_b_drivers:
                message = "Выходной: Тип A не работает, а типа B нет."
                messagebox.showerror("Ошибка", message)
                return
            if self.is_weekend(selected_day) and not self.type_a_drivers and self.type_b_drivers:
                additional_b = self.calculate_additional_driver_needs(num_routes, self.type_b_drivers, self.shift_duration_b)
                if additional_b > 0:
                    message = f"Недостаточно водителей B на выходной. Нужно {additional_b}."
                    messagebox.showerror("Ошибка", message)
                    return
            self.execute_genetic_algorithm(all_drivers, shift_duration, num_routes, selected_day, generations=50, population_size=20, mutation_rate=0.1, break_time=10, min_break_time=30)
        except ValueError:
            messagebox.showerror("Ошибка", "Не удалось сгенерировать: нужно добавить ещё водителей или уменьшить число рейсов.")
    
    def start_schedule_creation(self):
        try:
            num_routes = int(self.total_routes_entry.get())
            selected_day = self.selected_day_var.get()
            all_drivers = self.type_a_drivers + self.type_b_drivers
            if not self.type_a_drivers and not self.type_b_drivers:
                messagebox.showerror("Ошибка", "Нет водителей.")
                return
            if self.is_weekend(selected_day) and not self.type_b_drivers:
                messagebox.showerror("Ошибка", "Выходной: Тип A не работает, а типа B нет.")
                return
            if self.is_weekend(selected_day) and not self.type_a_drivers and self.type_b_drivers:
                additional_b = self.calculate_additional_driver_needs(num_routes, self.type_b_drivers, self.shift_duration_b)
                if additional_b > 0:
                    message = f"Недостаточно водителей B на выходной. Нужно {additional_b}."
                    messagebox.showerror("Ошибка", message)
                    return
                self.build_optimized_timetable(self.type_b_drivers, self.shift_duration_b, num_routes, selected_day, self.root)
                return
            max_shift = max(self.shift_duration_a, self.shift_duration_b)
            self.build_optimized_timetable(all_drivers, max_shift, num_routes, selected_day, self.root)
        except ValueError:
            messagebox.showerror("Ошибка", "Проверьте введенные данные.")
    
    def build_navigation_panel(self):
        sidebar_width = 200
        self.navigation_panel = tb.Frame(self.primary_frame, width=sidebar_width, bootstyle=SECONDARY)
        self.navigation_panel.pack(side=LEFT, fill=Y)
        logo_title = tb.Label(self.navigation_panel, text="Маршрутник", font=("Helvetica", 18, "bold"), bootstyle=INFO, anchor=CENTER)
        logo_title.pack(pady=20, padx=10, fill=X)
        buttons = [
            {"text": "Запись", "command": lambda: self.display_section("registration")},
            {"text": "Конфигурация", "command": lambda: self.display_section("route_settings")},
            {"text": "Сформировать", "command": lambda: self.display_section("timetable_creation")}
        ]
        for btn in buttons:
            button = tb.Button(
                self.navigation_panel,
                text=btn["text"],
                command=btn["command"],
                bootstyle=INFO,
                width=20,
                compound=LEFT
            )
            button.pack(pady=10, padx=10, fill=X)
            self.hover_effect_button(button, bootstyle_default=INFO, bootstyle_hover=SUCCESS)
    
    def setup_driver_registration(self):
        self.driver_registration_frame = tb.Frame(self.main_content)
        registration_title = tb.Label(self.driver_registration_frame, text="Зарегистрировать водителя", font=("Helvetica", 24, "bold"), bootstyle=INFO)
        registration_title.pack(pady=20)
        registration_input_frame = tb.Frame(self.driver_registration_frame)
        registration_input_frame.pack(pady=10)
        tb.Label(registration_input_frame, text="Имя водителя:", font=("Helvetica", 14)).grid(row=0, column=0, padx=10, pady=10, sticky='e')
        self.driver_name_entry = tb.Entry(registration_input_frame, width=40, font=("Helvetica", 14))
        self.driver_name_entry.grid(row=0, column=1, padx=10, pady=10)
        tb.Label(registration_input_frame, text="Категория водителя:", font=("Helvetica", 14)).grid(row=1, column=0, padx=10, pady=10, sticky='e')
        self.driver_type_var = tb.StringVar(value="A")
        self.driver_type_menu = tb.Combobox(registration_input_frame, textvariable=self.driver_type_var, values=["A", "B"], state="readonly", width=38, font=("Helvetica", 14))
        self.driver_type_menu.grid(row=1, column=1, padx=10, pady=10)
        register_driver_button = tb.Button(self.driver_registration_frame, text="Зарегистрировать", command=self.register_driver, bootstyle=INFO, width=20, compound=LEFT)
        register_driver_button.pack(pady=20)
        self.hover_effect_button(register_driver_button, bootstyle_default=INFO, bootstyle_hover=SUCCESS)
    
    def setup_route_configuration(self):
        self.route_configuration_frame = tb.Frame(self.main_content)
        route_configuration_title = tb.Label(self.route_configuration_frame, text="Настроить маршруты", font=("Helvetica", 24, "bold"), bootstyle=INFO)
        route_configuration_title.pack(pady=20)
        route_configuration_input_frame = tb.Frame(self.route_configuration_frame)
        route_configuration_input_frame.pack(pady=10)
        tb.Label(route_configuration_input_frame, text="Число маршрутов за день:", font=("Helvetica", 14)).grid(row=0, column=0, padx=10, pady=10, sticky='e')
        self.total_routes_entry = tb.Entry(route_configuration_input_frame, width=40, font=("Helvetica", 14))
        self.total_routes_entry.grid(row=0, column=1, padx=10, pady=10)
        tb.Label(route_configuration_input_frame, text="Продолжительность маршрута (мин):", font=("Helvetica", 14)).grid(row=1, column=0, padx=10, pady=10, sticky='e')
        self.route_length_entry = tb.Entry(route_configuration_input_frame, width=40, font=("Helvetica", 14))
        self.route_length_entry.grid(row=1, column=1, padx=10, pady=10)
        apply_route_config_button = tb.Button(self.route_configuration_frame, text="Применить параметры", command=self.set_route_parameters, bootstyle=INFO, width=20, compound=LEFT)
        apply_route_config_button.pack(pady=20)
        self.hover_effect_button(apply_route_config_button, bootstyle_default=INFO, bootstyle_hover=SUCCESS)
        clear_data_button = tb.Button(self.route_configuration_frame, text="Очистить данные", command=self.clear_all_records, bootstyle=WARNING, width=20, compound=LEFT)
        clear_data_button.pack(pady=10)
        self.hover_effect_button(clear_data_button, bootstyle_default=WARNING, bootstyle_hover=INFO)
    
    def setup_timetable_creation(self):
        self.timetable_creation_frame = tb.Frame(self.main_content)
        timetable_creation_title = tb.Label(self.timetable_creation_frame, text="Выбор вида расписания", font=("Helvetica", 24, "bold"), bootstyle=INFO)
        timetable_creation_title.pack(pady=20)
        timetable_creation_input_frame = tb.Frame(self.timetable_creation_frame)
        timetable_creation_input_frame.pack(pady=10)
        tb.Label(timetable_creation_input_frame, text="Выберите день:", font=("Helvetica", 14)).grid(row=0, column=0, padx=10, pady=10, sticky='e')
        self.selected_day_var = tb.StringVar(value="Понедельник")
        self.selected_day_menu = tb.Combobox(timetable_creation_input_frame, textvariable=self.selected_day_var, values=["Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота", "Воскресенье"], state="readonly", width=38, font=("Helvetica", 14))
        self.selected_day_menu.grid(row=0, column=1, padx=10, pady=10)
        generate_timetable_button = tb.Button(self.timetable_creation_frame, text="Прямое расписание", command=self.start_schedule_creation, bootstyle=SUCCESS, width=25, compound=LEFT)
        generate_timetable_button.pack(pady=10)
        self.hover_effect_button(generate_timetable_button, bootstyle_default=SUCCESS, bootstyle_hover=DANGER)
        generate_genetic_timetable_button = tb.Button(self.timetable_creation_frame, text="Генетическое расписания", command=self.start_genetic_schedule, bootstyle=DANGER, width=30, compound=LEFT)
        generate_genetic_timetable_button.pack(pady=10)
        self.hover_effect_button(generate_genetic_timetable_button, bootstyle_default=DANGER, bootstyle_hover=WARNING)
    
    def display_section(self, section_name):
        self.driver_registration_frame.pack_forget()
        self.route_configuration_frame.pack_forget()
        self.timetable_creation_frame.pack_forget()
        if section_name == "registration":
            self.driver_registration_frame.pack(fill=BOTH, expand=True)
        elif section_name == "route_settings":
            self.route_configuration_frame.pack(fill=BOTH, expand=True)
        elif section_name == "timetable_creation":
            self.timetable_creation_frame.pack(fill=BOTH, expand=True)
    
    def hover_effect_button(self, button, bootstyle_default=INFO, bootstyle_hover=SUCCESS):
        def on_enter(e):
            button.configure(bootstyle=bootstyle_hover)
        def on_leave(e):
            button.configure(bootstyle=bootstyle_default)
        button.bind("<Enter>", on_enter)
        button.bind("<Leave>", on_leave)
    
    def register_driver(self):
        name = self.driver_name_entry.get().strip()
        driver_type = self.driver_type_var.get()
        if not name:
            messagebox.showerror("Ошибка", "Введите имя водителя.")
            return
        if driver_type == "A":
            self.type_a_drivers.append(name)
        else:
            self.type_b_drivers.append(name)
        self.driver_name_entry.delete(0, tb.END)
        self.refresh_main_status(f"Водитель '{name}' зарегистрирован.", SUCCESS)
    
    def clear_all_records(self):
        self.total_routes_entry.delete(0, tb.END)
        self.route_length_entry.delete(0, tb.END)
        self.driver_name_entry.delete(0, tb.END)
        self.type_a_drivers.clear()
        self.type_b_drivers.clear()
        self.refresh_main_status("Данные очищены.", WARNING)
    
    def set_route_parameters(self):
        try:
            self.travel_duration_minutes = int(self.route_length_entry.get())
            self.refresh_main_status(f"Продолжительность маршрута установлена на {self.travel_duration_minutes} минут.", SUCCESS)
        except ValueError:
            messagebox.showerror("Ошибка", "Введите корректное число для продолжительности маршрута.")
    
    def refresh_main_status(self, message, color=INFO):
        self.status_label.config(text=message, bootstyle=color)
        self.status_label.after(3000, lambda: self.status_label.config(text=""))
    
if __name__ == "__main__":
    root = tb.Window(themename="superhero")
    app = RouteScheduler(root)
    root.mainloop()

