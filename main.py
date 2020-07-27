from PySide2.QtWidgets import *
from PySide2.QtCore import *
from PySide2.QtGui import *
import sys
from gui import UIMainWindow
import os
import datetime
import pandas
import time
import requests
import json
from bs4 import BeautifulSoup
import math

log_file = f"logs/{datetime.datetime.now().strftime('%m%d%Y - %H%M%S')}.log"
mutex = QMutex()


class ThreadWorker(QThread):
    send_row = Signal(dict)
    send_time = Signal(float)

    def __init__(self, rows):
        self.stopped = False
        self.error = False
        self.rows = rows

        super().__init__()

    def run(self):
        for item in self.rows:
            start_time = time.time()

            index = item["index"]
            data = item["row"]

            if self.stopped:
                return

            timeouts = 0
            while 1:
                if self.stopped:
                    return

                try:
                    q_url = f"http://bots.snpedia.com/api.php?action=query&list=search&srsearch={data[0]}" \
                            f"&format=json"
                    query = json.loads(requests.get(q_url, timeout=10).content)
                    p_url = f"http://bots.snpedia.com/api.php?action=parse&page={data[0]}&prop=text&format=json"
                    page_html = json.loads(requests.get(p_url, timeout=10).content)['parse']['text']['*']
                    break

                except Exception as e:
                    timeouts += 1
                    time.sleep(5 + (timeouts * 2.5))

                    if timeouts == 5:
                        log(e)
                        self.report_error("Can't establish connection to SNPedia!")
                        return

            data = self.get_references(data, page_html)

            gene = f"{data[0].title()}({';'.join(list(data[3]))})"
            if gene in [i['title'] for i in query['query']['search']]:
                p_url = f"http://bots.snpedia.com/api.php?action=parse&page={gene}&prop=text&format=json"

                timeouts = 0
                while 1:
                    if self.stopped:
                        return
                    try:
                        page_html = json.loads(requests.get(p_url, timeout=10).content)['parse']['text']['*']
                        break
                    except Exception as e:
                        timeouts += 1
                        time.sleep(5 + (timeouts * 2.5))

                        if timeouts == 5:
                            log(e)
                            self.report_error("Can't establish connection to SNPedia!")
                            return

                data = self.get_geno_specific_data(data, page_html)

            mutex.lock()
            self.send_row.emit({"index": index, "data": data})
            self.send_time.emit(time.time() - start_time)
            mutex.unlock()

    def get_references(self, row, page_html):
        row[7] = []
        row[8] = []

        for p in BeautifulSoup(page_html, 'lxml').find_all('p'):
            if len(p.getText().strip()):
                for a in BeautifulSoup(str(p), 'lxml').find_all('a', href=True):
                    if "file" not in a['href'].lower():
                        if a['href'][:11] == "/index.php/":
                            link = "https://www.snpedia.com" + a['href']
                        else:
                            link = a['href']

                        row[7].append({"title": a.getText().replace("\n", ""),
                                       "link": link.replace("\n", "")})

                row[8].append(p.getText().replace("\n", ""))

        return row

    def get_geno_specific_data(self, row, page_html):
        for table in BeautifulSoup(page_html, 'lxml').find_all('table', style=True):
            summary = BeautifulSoup(str(table), 'lxml').find('td').getText()
            row[6] = summary

        for tr in BeautifulSoup(page_html, 'lxml').find_all('tr'):
            for a in BeautifulSoup(str(tr), 'lxml').find_all('a'):
                if a.getText() == "Magnitude":
                    magnitude = BeautifulSoup(str(tr), 'lxml').find_all('td')[1].getText()
                    row[4] = float(magnitude)

                elif a.getText() == "Repute":
                    repute = BeautifulSoup(str(tr), 'lxml').find_all('td')[1].getText()
                    row[5] = repute

        return row

    def report_error(self, exception):
        log(exception)
        self.error = True
        self.stopped = True

    def stop_thread(self):
        self.stopped = True


class ThreadProcessData(QThread):
    set_status = Signal(str)
    set_progress = Signal(int)

    def __init__(self, input_file, dataset_name):
        self.stopped = False
        self.error = False
        self.data = None

        self.workers = []
        self.work_done = 0
        self.timings = []

        self.input_file = input_file
        self.dataset_name = dataset_name

        super().__init__()

        log("Background thread started successfully!")

    def run(self):
        try:
            benchmark_start = time.time()

            self.init_dataframe()
            self.spawn_workers()
            self.watch_workers()

            if not self.error and not self.stopped:
                log(f"Saving data to {self.dataset_name}.csv...")
                self.data.to_pickle(f"data/{self.dataset_name}")
                log(f"Data saved successfully!")

                log(f"Background process finished! Execution took {time.time() - benchmark_start}s")
            elif self.stopped:
                log(f"Background process stopped by user... Execution took {time.time() - benchmark_start}s")
            elif self.error:
                log(f"Background process ran into errors... Execution took {time.time() - benchmark_start}s")
        except Exception as e:
            self.report_error(e)
            return

    def watch_workers(self):
        try:
            log("Watching workers...")

            workers_still_running = True
            while workers_still_running:
                time.sleep(.1)

                if True not in [worker.isRunning() for worker in self.workers]:
                    workers_still_running = False
                elif True in [worker.error for worker in self.workers]:
                    while True in [worker.isRunning() for worker in self.workers]:
                        for worker in self.workers:
                            worker.stop_thread()

                    self.report_error("Worker(s) ran into exception...")
                    return
                else:
                    if self.stopped:
                        self.set_status.emit("Stopping background execution...\nPlease wait...")

                        while True in [worker.isRunning() for worker in self.workers]:
                            for worker in self.workers:
                                worker.stop_thread()

                        log("Workers stopped successfully!")
                        return

                    self.set_status.emit(f"Gathering data from SNPedia...\nETA: {self.calc_eta()}")
                    self.set_progress.emit(int(self.work_done / len(self.data) * 100))

            log("Workers done!")
        except Exception as e:
            self.report_error(e)
            return

    def spawn_workers(self):
        try:
            self.set_status.emit("Preparing background execution...")

            num_workers = 30
            worker_data = [{"index": index, "row": list(row)} for index, row in self.data.iterrows()]

            log(f"Dividing workload by {num_workers}...")

            len_work = int(len(worker_data) / num_workers)
            div_work_data = [[] for _ in range(num_workers)]
            for i in range(len(worker_data)):
                if int(i / len_work) < len(div_work_data):
                    div_work_data[int(i / len_work)].append(worker_data[i])
                else:
                    div_work_data[-1].append(worker_data[i])
            worker_data = div_work_data

            log("Workload has been divided successfully!")
            log("Spawning workers...")

            self.workers = [ThreadWorker(work) for work in worker_data]

            log(f"{num_workers} have been spawned!")

            for worker_number, worker in enumerate(self.workers):
                worker.send_row.connect(self.receive_row)
                worker.send_time.connect(self.receive_worker_time)
                worker.start()

                log(f"Worker {worker_number} started!")
        except Exception as e:
            self.report_error(e)

    def receive_row(self, row):
        for col_index, column in enumerate(self.data.columns):
            self.data.at[row["index"], column] = row["data"][col_index]

        self.work_done += 1

    def init_dataframe(self):
        try:
            if os.path.isdir("data"):
                if os.path.isfile(f"data/{self.dataset_name}.csv"):
                    os.remove(f"data/{self.dataset_name}.csv")
            else:
                os.mkdir("data")

            log("Initializing dataframe...")
            self.set_status.emit("Initializing dataframe...")

            self.data = pandas.read_csv(self.input_file, comment="#", sep="\t", low_memory=False,
                                        names=["SNP", "Chromosome", "Position", "Genotype"])
            for header in ["Magnitude", "Repute", "Summary", "References", "Ref_Summaries"]:
                self.data[header] = None

            valid_snps = set([i.replace("\n", "") for i in sorted(open("snps.txt", "r").readlines())])

            self.data = self.data[self.data["SNP"].isin(valid_snps)]
            self.data.sort_values('SNP', inplace=True)
            self.data.reset_index(inplace=True, drop=True)

            log("Dataframe initialization complete!")

        except Exception as e:
            self.report_error(e)
            return

    def report_error(self, exception):
        log(exception)
        self.error = True
        self.stopped = True

    def stop_thread(self):
        self.stopped = True

    def calc_eta(self):
        if self.work_done > 30:
            avg_time = (sum(self.timings) / len(self.timings)) / len(self.workers)
            eta = str(datetime.timedelta(seconds=avg_time * (len(self.data) - self.work_done))).split(":")
            if len(eta) > 3:
                return f"{eta[0]}d - {eta[1]}h - {eta[2]}m - {int(float(eta[3]))}s"
            else:
                return f"{eta[0]}h - {eta[1]}m - {int(float(eta[2]))}s"
        else:
            return f"Calculating{int(self.work_done / 10) * '.'}"

    def receive_worker_time(self, worker_time):
        self.timings.append(worker_time)


class ProgressDialog(QDialog):
    def __init__(self):
        super().__init__()

        self.setFixedWidth(self.width())
        self.setFixedHeight(self.height())

        self.thread = None

        self.setWindowTitle("Operation in progress...")
        self.setFixedSize(300, 120)

        main_layout = QVBoxLayout()
        self.setLayout(main_layout)

        self.status_label = QLabel("Process started!")
        self.status_label.setAlignment(Qt.AlignTop)
        self.progress_bar = QProgressBar()
        cancel_btn = QPushButton("Cancel")

        main_layout.addWidget(self.status_label)
        main_layout.addWidget(self.progress_bar)
        main_layout.addWidget(cancel_btn)

        cancel_btn.clicked.connect(self.cancel)

        thread_clock = QTimer(self)
        thread_clock.timeout.connect(self.wait_for_thread)
        thread_clock.start(100)

    def set_status(self, status):
        self.status_label.setText(status)

    def set_progress(self, progress):
        self.progress_bar.setValue(progress)

    def cancel(self):
        self.thread.stop_thread()

    def wait_for_thread(self):
        if not self.thread.isRunning():
            self.close()


class GetDatasetNameDialog(QDialog):
    def __init__(self):
        super().__init__()

        self.setFixedWidth(self.width())
        self.setFixedHeight(self.height())

        self.dataset_name = None

        self.setWindowTitle("Dataset Name?")
        self.setFixedSize(300, 120)

        main_layout = QVBoxLayout()
        btn_layout = QHBoxLayout()
        self.setLayout(main_layout)

        dataset_name_label = QLabel("Please choose a name for your\ngenome dataset: ")
        self.dataset_name_edit = QLineEdit()
        dataset_name_label.setAlignment(Qt.AlignTop)
        self.dataset_name_edit.setAlignment(Qt.AlignTop)
        self.dataset_name_edit.setValidator(QRegExpValidator("\w{1,30}"))
        self.dataset_confirm_btn = QPushButton("Confirm")
        dataset_cancel_btn = QPushButton("Cancel")

        btn_layout.addWidget(self.dataset_confirm_btn)
        btn_layout.addWidget(dataset_cancel_btn)

        main_layout.addWidget(dataset_name_label)
        main_layout.addWidget(self.dataset_name_edit)
        main_layout.addLayout(btn_layout)

        self.dataset_confirm_btn.clicked.connect(self.confirm)
        dataset_cancel_btn.clicked.connect(lambda: self.close())

        self.clock = QTimer(self)
        self.clock.timeout.connect(self.check_min_chars)
        self.clock.start(100)

    def check_min_chars(self):
        self.dataset_confirm_btn.setDisabled(not len(self.dataset_name_edit.text()))

    def confirm(self):
        overwrite = QMessageBox.Yes

        if os.path.isfile(f"data/{self.dataset_name_edit.text()}.csv"):
            overwrite = QMessageBox.question(self, "Overwrite dataset?", f"Dataset: {self.dataset_name_edit.text()}"
                                                                         f" already exists! Do you wish to overwrite?")

        if overwrite == QMessageBox.Yes:
            self.dataset_name = self.dataset_name_edit.text()
            self.close()


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setFixedHeight(480)
        self.setFixedWidth(1200)

        self.loaded_profile = None

        try:
            self.background_thread = QThread()
            self.background_thread.error = False

            if not os.path.isdir("data"):
                os.mkdir("data")

            log("Setting up UI...")


            self.ui = UIMainWindow()
            self.ui.setupUi(self)

            log("UI Set up successfully!")
        except Exception as e:
            log(e)
            self.error_popup()
            exit()

        log("Starting timer...")

        try:
            self.update_timer = QTimer(self)
            self.connect_functions()
            self.update_timer.start(100)
            log("Timer Started!")
        except Exception as e:
            log(e)
            self.error_popup()
            exit()

        log("Window initialization successful!")

    def connect_functions(self):
        log("Connecting functions...")
        try:
            self.update_timer.timeout.connect(self.updater)
            self.ui.load_data_button.clicked.connect(self.load_and_process_data)
            self.ui.rem_data_button.clicked.connect(self.remove_data)
            self.ui.results_search_button.clicked.connect(self.display_data)

        except Exception as e:
            log(e)
            self.error_popup()
            exit()

    def updater(self):
        # This function is used to automatically update the main window using a clock
        self.ui.data_group.setDisabled(self.background_thread.isRunning())
        self.ui.results_group.setDisabled(not self.ui.data_list.count() and not self.background_thread.isRunning())
        self.ui.attribute_group.setDisabled(not self.ui.data_list.count() and not self.background_thread.isRunning())
        self.ui.rem_data_button.setDisabled(not self.ui.data_list.selectedItems())
        self.ui.results_label.setDisabled(not self.ui.data_list.count())
        self.ui.results_search_bar.setDisabled(not self.ui.data_list.count())
        self.ui.results_search_button.setDisabled(not len(self.ui.data_list.selectedItems()))

        self.ui.mag_min_spin.setMaximum(self.ui.mag_max_spin.value() - .1)

        data_list_items = [self.ui.data_list.item(i).text() for i in range(self.ui.data_list.count())]
        for file in os.listdir('data'):
            columns = list(pandas.read_pickle(f"data/{file}").columns)
            if columns == ['SNP', 'Chromosome', 'Position', 'Genotype', 'Magnitude',
                           'Repute', 'Summary', 'References', 'Ref_Summaries']:
                if file not in data_list_items:
                    self.ui.data_list.addItem(file)

        for index, list_item in enumerate(data_list_items):
            if list_item not in [file for file in os.listdir('data')]:
                self.ui.data_list.takeItem(index)

        if self.background_thread.error:
            self.error_popup()
            self.background_thread.error = False

    def load_and_process_data(self):
        log("Background thread starting...")

        file_dialog = QFileDialog(self)
        options = QFileDialog.Options()
        options |= QFileDialog.DontUseNativeDialog
        filters = "Raw Genome Data (*.txt)"
        load_file = file_dialog.getOpenFileName(self, "Load Raw Genome Data", "", filter=filters, options=options)

        if load_file != ('', ''):
            dataset_dialog = GetDatasetNameDialog()
            dataset_dialog.exec_()

            if dataset_dialog.dataset_name is not None:
                if os.path.isfile(f"data/{dataset_dialog.dataset_name}.csv"):
                    overwrite = QMessageBox.question("File already exists!",
                                                     "File already exists! Do you wish to overwrite?")
                else:
                    overwrite = QMessageBox.Yes

                if overwrite == QMessageBox.Yes:
                    try:
                        self.progress_dialog = ProgressDialog()

                        self.background_thread = ThreadProcessData(load_file[0], dataset_dialog.dataset_name)
                        self.background_thread.set_status.connect(self.progress_dialog.set_status)
                        self.background_thread.set_progress.connect(self.progress_dialog.set_progress)
                        self.background_thread.start()

                        self.progress_dialog.thread = self.background_thread
                        self.progress_dialog.exec_()
                    except Exception as e:
                        log(e)
                        self.error_popup()

    def error_popup(self):
        QMessageBox.warning("Error!", "Process ran into error! Check the latest log file for more details!")

    def remove_data(self):
        remove = QMessageBox.question(self, "Remove data?", f"Are you sure you wish to remove "
                                                            f"{self.ui.data_list.selectedItems()[0].text()}?")
        if remove == QMessageBox.Yes:
            os.remove(f"data/{self.ui.data_list.selectedItems()[0].text()}.csv")

    def display_data(self):
        filters = {"sort": self.ui.sort_combo.currentText(),
                   "mag_range": [self.ui.mag_min_spin.value(), self.ui.mag_max_spin.value()],
                   "repute": self.ui.repute_combo.currentText(),
                   "references": self.ui.ref_spin.value()}
        data = pandas.read_pickle(f"data/{self.ui.data_list.selectedItems()[0].text()}")

        data['Repute'].fillna("Neutral", inplace=True)
        data['Summary'].fillna("None", inplace=True)
        data['Magnitude'].fillna(0.0, inplace=True)

        data_lower = data.apply(lambda x: x.astype(str).str.lower())
        data_lower = data_lower[data_lower['Summary'].str.contains(self.ui.results_search_bar.text())]
        data = data[(data['SNP'].isin(list(data_lower['SNP'])))]

        data = data[(data['Magnitude'] >= filters['mag_range'][0]) &
                    (data['Magnitude'] <= filters['mag_range'][1])]
        if filters['repute'] != "NA":
            data = data[(data['Repute'] == filters['repute'])]
        data = data[(data['References']).map(len) > filters['references']]

        data['Repute'] = data['Repute'].map({'Good': 2, 'Bad': 1, 'Neutral': 0})
        data.sort_values([filters['sort'], 'Magnitude'], ascending=[False, False], inplace=True)
        data['Repute'] = data['Repute'].map({2: 'Good', 1: 'Bad', 0: 'Neutral'})

        data.reset_index(drop=True, inplace=True)

        if not len(data):
            QMessageBox.warning(self, "No results found...", "No results found for the given search...")
            return

        self.ui.good_repute_bar.setValue(0)
        self.ui.bad_repute_bar.setValue(0)
        self.ui.neutral_repute_bar.setValue(0)
        self.ui.results_browser.results = []
        self.ui.results_browser.setHtml("")

        data_per_page = 50
        if len(data) % data_per_page == 0:
            num_pages = len(data) / data_per_page
        else:
            num_pages = int(len(data) / data_per_page) + 1

        paged_data = [[] for i in range(num_pages)]
        for i in range(len(data)):
            if int(i / data_per_page) < len(paged_data):
                paged_data[int(i / data_per_page)].append(data.iloc[i])
            else:
                paged_data[-1].append(data.iloc[i])

        self.ui.results_browser.data = data
        self.ui.results_browser.paged_data = paged_data
        self.ui.results_browser.display_data()

        totals = [len(data[(data['Repute'] == 'Good')]), len(data[(data['Repute'] == 'Bad')]),
                  len((data['Repute'] != "Good") & (data['Repute'] != "Bad")), len(data)]

        try:
            self.ui.good_repute_bar.setValue(int(math.log(totals[0], 10) / math.log(totals[3], 10) * 100))
            self.ui.bad_repute_bar.setValue(int(math.log(totals[1], 10) / math.log(totals[3], 10) * 100))
            self.ui.neutral_repute_bar.setValue(int(math.log(totals[2], 10) / math.log(totals[3], 10) * 100))
            self.ui.total_score_label.setText(str(totals[3]))
        except:
            pass


def log(log_string):
    global log_file

    if not os.path.isdir("logs"):
        os.mkdir("logs")

    if not os.path.isfile(log_file):
        open(log_file, "w+").close()

    with open(log_file, "a+") as file:
        file.write(f"({datetime.datetime.now()}) - {log_string}\n")

    print(f"({datetime.datetime.now()}) - {log_string}")


if __name__ == "__main__":
    app = QApplication(sys.argv)

    window = MainWindow()
    window.show()

    sys.exit(app.exec_())
