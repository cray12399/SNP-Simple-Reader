from PySide2.QtCore import (QCoreApplication, QDate, QDateTime, QMetaObject,
    QObject, QPoint, QRect, QSize, QTime, QUrl, Qt)
from PySide2.QtGui import (QBrush, QColor, QConicalGradient, QCursor, QFont,
    QFontDatabase, QIcon, QKeySequence, QLinearGradient, QPalette, QPainter,
    QPixmap, QRadialGradient)
from PySide2.QtWidgets import *
from PySide2.QtCore import*
from bs4 import BeautifulSoup
from textwrap import TextWrapper
import webbrowser


class ResultsBrowser(QTextBrowser):
    def __init__(self):
        super().__init__()

        self.setMouseTracking(True)

        self.line_height = 25
        self.text_size = 13

        self.data = None
        self.paged_data = None
        self.page_changed = False
        self.current_results = []
        self.current_page = 0

        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.check_update)
        self.update_timer.start(10)

    def mouseMoveEvent(self, event):
        self.mouse_pos = (event.x(), self.verticalScrollBar().value() + event.y())
        self.current_row = round(self.mouse_pos[1] / self.line_height) - 1

        if self.current_results:
            if self.mouse_pos[0] <= 20 <= self.mouse_pos[1]:
                QApplication.setOverrideCursor(Qt.PointingHandCursor)
            else:
                QApplication.setOverrideCursor(Qt.ArrowCursor)

        try:
            highlight = "#e3e6fc"
            if "#ffffff" in self.current_results[self.current_row]:
                if "id=\"top-level-item\"" in self.current_results[self.current_row]:
                    for index, row in enumerate(self.current_results):
                        if highlight in row:
                            self.current_results[index] = self.current_results[index] \
                                .replace(highlight, "#ffffff")
                    self.current_results[self.current_row] = self.current_results[self.current_row]\
                        .replace("#ffffff", highlight)

                    prev_scrollbar_value = self.verticalScrollBar().value()
                    html_top = f"<table width=\"100%\" style=\"border-collapse:collapse\">"
                    self.setHtml(html_top + "".join(self.current_results) + "</table>")
                    self.verticalScrollBar().setValue(prev_scrollbar_value)
        except:
            pass

    def mousePressEvent(self, event):
        try:
            snp = BeautifulSoup(str(self.current_results[self.current_row]), 'lxml').find_all('td')[1].text
            html_top = f"<table width=\"100%\" style=\"border-collapse:collapse\">"

            if self.mouse_pos[0] <= 20:
                if "▶" in str(self.current_results[self.current_row]):
                    prev_scrollbar_value = self.verticalScrollBar().value()

                    self.current_results[self.current_row] = str(self.current_results[self.current_row])\
                        .replace("▶", "▼")
                    self.display_data_details(snp)
                    self.setHtml(html_top + "".join(self.current_results) + "</table>")

                    self.verticalScrollBar().setValue(prev_scrollbar_value)

                elif "▼" in str(self.current_results[self.current_row]):
                    prev_scrollbar_value = self.verticalScrollBar().value()

                    self.current_results[self.current_row] = str(self.current_results[self.current_row])\
                        .replace("▼", "▶")

                    for row in self.current_results[self.current_row:]:
                        if f"class=\"{snp}-summary\"" in row:
                            self.current_results.remove(row)

                    self.setHtml(html_top + "".join(self.current_results) + "</table>")

                    self.verticalScrollBar().setValue(prev_scrollbar_value)
        except:
            pass

    def check_update(self):
        if self.page_changed and self.verticalScrollBar().value() not in [0, self.verticalScrollBar().maximum()]:
            self.page_changed = False

        if self.verticalScrollBar().value() == 0:
            if not self.page_changed:
                if self.current_page != 0:
                    self.current_page -= 1
                    self.display_data()
                    self.verticalScrollBar().setValue(self.verticalScrollBar().maximum())
        elif self.verticalScrollBar().value() == self.verticalScrollBar().maximum():
            if not self.page_changed:
                if self.current_page != len(self.paged_data) - 1:
                    self.current_page += 1
                    self.display_data()
                    self.verticalScrollBar().setValue(0)

    def display_data(self):
        if self.data is not None:
            col_title_style = f"font: bold {self.text_size}px Arial, sans-serif;text-align: left;" \
                              " border-bottom: 1px solid black; line-height: 20px"
            html = f"<table width=\"100%\" style=\"border-collapse:collapse; table-layout:fixed;\">" \
                   f"<tr id=\"headerRow\">" \
                   f"<th width=\"5%\" style=\"{col_title_style}\">{self.current_page + 1}</th>" \
                   f"<th width=\"65%\" style=\"{col_title_style}\">SNP</th>" \
                   f"<th width=\"15%\" style=\"{col_title_style}\">REPUTE</th>" \
                   f"<th width=\"15%\" style=\"{col_title_style}\">MAGNITUDE</th>" \
                   f"</tr>"

            for index, row in enumerate(self.paged_data[self.current_page]):
                col_style = f"font: {self.text_size}px Arial, sans-serif; text-align: left; padding-top: 0px;" \
                            f" padding-bottom: 0px; background: #ffffff; line-height: {self.line_height}px;"

                if row['Repute'] == "Good":
                    repute_row_style = f"font: bold {self.text_size}px Arial, sans-serif; text-align: left;" \
                                       f"padding-top: 0px; color: #00db2f; background: #ffffff;" \
                                       f"line-height: {self.line_height}px;"
                elif row['Repute'] == "Bad":
                    repute_row_style = f"font: bold {self.text_size}px Arial, sans-serif; text-align: left;" \
                                       f"padding-top: 0px; color: #db1900; background: #ffffff;" \
                                       f"line-height: {self.line_height}px;"
                else:
                    repute_row_style = f"font: bold {self.text_size}px Arial, sans-serif; text-align: left;" \
                                       f"padding-top: 0px; color: #000000; background: #ffffff;" \
                                       f"line-height: {self.line_height}px;"

                link = f"https://www.snpedia.com/index.php/{row['SNP']}"
                html += f"<tr id=\"top-level-item\">" \
                        f"<td style=\"{col_style}\"><p style=\"font-size: 9px;\">▶</p></th>" \
                        f"<td style=\"{col_style}\"><a href=\"{link}\">{row['SNP']}</a></th>" \
                        f"<td style=\"{repute_row_style}\">{row['Repute']}</th>" \
                        f"<td style=\"{col_style}\">{row['Magnitude']}</th>" \
                        "</tr>"
            html += "</table>"

            self.setHtml(html)
            self.current_results = [str(row) for row in BeautifulSoup(html, 'lxml').find_all('tr')]
            
            self.page_changed = True

    def display_data_details(self, snp):
        references = self.data[(self.data['SNP'] == snp)].iloc[0]['References']
        references = [dict(_tuple) for _tuple in {tuple(_dict.items()) for _dict in references}]

        reference_summaries = list(self.data[(self.data['SNP'] == snp)].iloc[0]['Ref_Summaries'])
        reference_summaries[0] = "<b>Reference(s): </b>" + str(reference_summaries[0])
        reference_style = f"font: {self.text_size}px Arial, sans-serif; text-align: left; padding-top: 0px; " \
                          f"padding-bottom: 0px; background: #aff7af; line-height: {self.line_height}px;"

        for index, reference_summary in enumerate(reversed(reference_summaries)):
            if index != 0:
                self.current_results.insert(self.current_row + 1, f"<tr class=\"{snp}-summary\"><td><td colspan=\"3\""
                                                                  f" style=\"{reference_style}\"></td></tr>")

            for line in reversed(TextWrapper(width=80).wrap(reference_summary)):
                for reference in references:
                    if reference['title'] in line:
                        ref_link = f"<a href=\"{reference['link']}\">{reference['title']}</a>"
                        line = line.replace(reference['title'], ref_link)

                reference_line = f"<tr class=\"{snp}-summary\"><td><td colspan=\"3\"" \
                                 f" style=\"{reference_style}\">{line}</td></tr>"
                self.current_results.insert(self.current_row + 1, reference_line)

        summary = "<b>Summary: </b>" + str(self.data[(self.data['SNP'] == snp)].iloc[0]['Summary']).capitalize()
        summary_style = f"font: {self.text_size}px Arial, sans-serif; text-align: left; padding-top: 0px; " \
                        f"padding-bottom: 0px; background: #fcdab0; line-height: {self.line_height}px;"
        for line in reversed(TextWrapper(width=80).wrap(summary)):
            summary_line = f"<tr class=\"{snp}-summary\"><td><td colspan=\"3\"" \
                           f" style=\"{summary_style}\">{line}</td></tr>"
            self.current_results.insert(self.current_row + 1, summary_line)

    def setSource(self, name):
        webbrowser.open(name.url())


class UIMainWindow(object):
    def setupUi(self, MainWindow):
        if not MainWindow.objectName():
            MainWindow.setObjectName(u"MainWindow")
        MainWindow.setWindowModality(Qt.NonModal)
        MainWindow.resize(1112, 519)
        MainWindow.setStyleSheet(u"")
        MainWindow.setTabShape(QTabWidget.Rounded)
        self.centralwidget = QWidget(MainWindow)
        self.centralwidget.setObjectName(u"centralwidget")
        self.horizontalLayout = QHBoxLayout(self.centralwidget)
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.main_layout = QHBoxLayout()
        self.main_layout.setObjectName(u"main_layout")
        self.main_layout.setSizeConstraint(QLayout.SetMinAndMaxSize)
        self.main_layout.setContentsMargins(-1, -1, 0, -1)
        self.data_group = QGroupBox(self.centralwidget)
        self.data_group.setObjectName(u"data_group")
        self.data_group.setMaximumSize(QSize(250, 16777215))
        self.data_group.setStyleSheet(u"QGroupBox {background-color:rgba(0,0,0,0); border: 0px}")
        self.data_layout = QVBoxLayout(self.data_group)
        self.data_layout.setObjectName(u"data_layout")
        self.data_layout.setContentsMargins(15, -1, 15, -1)
        self.data_label = QLabel(self.data_group)
        self.data_label.setObjectName(u"data_label")
        self.data_label.setStyleSheet(u"font: bold 15px arial, sans-serif;")

        self.data_layout.addWidget(self.data_label, 0, Qt.AlignHCenter)

        self.verticalSpacer = QSpacerItem(20, 10, QSizePolicy.Minimum, QSizePolicy.Fixed)

        self.data_layout.addItem(self.verticalSpacer)

        self.data_list = QListWidget(self.data_group)
        self.data_list.setObjectName(u"data_list")
        self.data_list.setMinimumSize(QSize(200, 300))
        self.data_list.setMaximumSize(QSize(300, 16777215))
        self.data_list.setStyleSheet(u"")

        self.data_layout.addWidget(self.data_list)

        self.data_btn_layout = QHBoxLayout()
        self.data_btn_layout.setObjectName(u"data_btn_layout")
        self.load_data_button = QPushButton(self.data_group)
        self.load_data_button.setObjectName(u"del_data_btn")
        self.load_data_button.setMinimumSize(QSize(100, 0))
        self.load_data_button.setMaximumSize(QSize(150, 16777215))
        self.load_data_button.setStyleSheet(u"")

        self.data_btn_layout.addWidget(self.load_data_button)

        self.rem_data_button = QPushButton(self.data_group)
        self.rem_data_button.setObjectName(u"load_data_btn")
        self.rem_data_button.setMinimumSize(QSize(100, 0))
        self.rem_data_button.setMaximumSize(QSize(150, 16777215))
        self.rem_data_button.setAutoFillBackground(False)
        self.rem_data_button.setStyleSheet(u"")

        self.data_btn_layout.addWidget(self.rem_data_button)


        self.data_layout.addLayout(self.data_btn_layout)


        self.main_layout.addWidget(self.data_group)

        self.results_group = QGroupBox(self.centralwidget)
        self.results_group.setObjectName(u"results_group")
        self.results_group.setStyleSheet(u"QGroupBox {background-color:rgba(0,0,0,0); border: 0px}")
        self.results_layout = QVBoxLayout(self.results_group)
        self.results_layout.setObjectName(u"results_layout")
        self.results_layout.setContentsMargins(15, -1, 15, -1)
        self.results_label = QLabel(self.results_group)
        self.results_label.setObjectName(u"results_label")
        self.results_label.setStyleSheet(u"font: bold 15px arial, sans-serif;")

        self.results_layout.addWidget(self.results_label, 0, Qt.AlignHCenter)

        self.verticalSpacer_2 = QSpacerItem(20, 10, QSizePolicy.Minimum, QSizePolicy.Fixed)

        self.results_layout.addItem(self.verticalSpacer_2)

        self.results_search_layout = QHBoxLayout()
        self.results_search_bar = QLineEdit(self.results_group)
        self.results_search_bar.setObjectName(u"results_search_bar")
        self.results_search_bar.setStyleSheet(u"")

        self.results_search_button = QPushButton("Search")

        self.results_search_layout.addWidget(self.results_search_bar)
        self.results_search_layout.addWidget(self.results_search_button)
        self.results_layout.addLayout(self.results_search_layout)

        self.results_browser = ResultsBrowser()
        self.results_layout.addWidget(self.results_browser)

        font = QFont()
        font.setFamily(u"Arial")
        font.setPointSize(9)
        font.setBold(True)
        font.setWeight(75)
        __qtreewidgetitem = QTreeWidgetItem()
        __qtreewidgetitem.setFont(1, font)
        __qtreewidgetitem.setFont(0, font)
        # self.results_tree.setHeaderItem(__qtreewidgetitem)
        # self.results_tree.setObjectName(u"treeWidget")
        sizePolicy = QSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        sizePolicy.setHorizontalStretch(100)
        sizePolicy.setVerticalStretch(0)
        # sizePolicy.setHeightForWidth(self.results_tree.sizePolicy().hasHeightForWidth())
        # self.results_tree.setSizePolicy(sizePolicy)
        # self.results_tree.setMinimumSize(QSize(500, 0))
        # self.results_tree.setStyleSheet(u"")
        #
        # self.results_tree.header().resizeSection(0, 440)
        # self.results_tree.header().resizeSection(1, 10)

        # self.results_layout.addWidget(self.results_tree)

        self.main_layout.addWidget(self.results_group)

        self.attribute_group = QGroupBox(self.centralwidget)
        self.attribute_group.setObjectName(u"attribute_group")
        sizePolicy1 = QSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
        sizePolicy1.setHorizontalStretch(0)
        sizePolicy1.setVerticalStretch(0)
        sizePolicy1.setHeightForWidth(self.attribute_group.sizePolicy().hasHeightForWidth())
        self.attribute_group.setSizePolicy(sizePolicy1)
        self.attribute_group.setAutoFillBackground(False)
        self.attribute_group.setStyleSheet(u"QGroupBox {background-color:rgba(0,0,0,0); border: 0px}")
        self.attribute_layout = QVBoxLayout(self.attribute_group)
        self.attribute_layout.setSpacing(6)
        self.attribute_layout.setObjectName(u"attribute_layout")
        self.attribute_layout.setSizeConstraint(QLayout.SetFixedSize)
        self.attribute_layout.setContentsMargins(15, -1, 15, 100)
        self.filter_layout = QVBoxLayout()
        self.filter_layout.setObjectName(u"filter_layout")
        self.filter_label = QLabel(self.attribute_group)
        self.filter_label.setObjectName(u"filter_label")
        self.filter_label.setStyleSheet(u"font: bold 15px arial, sans-serif;")

        self.filter_layout.addWidget(self.filter_label, 0, Qt.AlignHCenter|Qt.AlignBottom)

        self.verticalSpacer_3 = QSpacerItem(20, 10, QSizePolicy.Minimum, QSizePolicy.Fixed)

        self.filter_layout.addItem(self.verticalSpacer_3)

        self.filter_form_layout = QFormLayout()
        self.filter_form_layout.setObjectName(u"filter_form_layout")
        self.sort_label = QLabel(self.attribute_group)
        self.sort_label.setObjectName(u"sort_label")
        self.sort_label.setStyleSheet(u"font: bold 13px arial, sans-serif;")

        self.filter_form_layout.setWidget(1, QFormLayout.LabelRole, self.sort_label)

        self.sort_combo = QComboBox(self.attribute_group)
        self.sort_combo.addItem("")
        self.sort_combo.addItem("")
        self.sort_combo.addItem("")
        self.sort_combo.setObjectName(u"sort_combo")
        self.sort_combo.setMaximumSize(QSize(130, 16777215))
        self.sort_combo.setStyleSheet(u"")

        self.filter_form_layout.setWidget(1, QFormLayout.FieldRole, self.sort_combo)

        self.mag_label = QLabel(self.attribute_group)
        self.mag_label.setObjectName(u"mag_label")
        self.mag_label.setStyleSheet(u"font: bold 13px arial, sans-serif;")

        self.filter_form_layout.setWidget(2, QFormLayout.LabelRole, self.mag_label)

        self.mag_range_layout = QHBoxLayout()
        self.mag_range_layout.setObjectName(u"mag_range_layout")
        self.mag_min_spin = QDoubleSpinBox(self.attribute_group)
        self.mag_min_spin.setObjectName(u"mag_min_spin")
        self.mag_min_spin.setMaximumSize(QSize(62, 16777215))
        self.mag_min_spin.setStyleSheet(u"")
        self.mag_min_spin.setMaximum(4.000000000000000)
        self.mag_min_spin.setSingleStep(0.100000000000000)

        self.mag_range_layout.addWidget(self.mag_min_spin)

        self.mag_max_spin = QDoubleSpinBox(self.attribute_group)
        self.mag_max_spin.setObjectName(u"mag_max_spin")
        self.mag_max_spin.setMaximumSize(QSize(62, 16777215))
        self.mag_max_spin.setStyleSheet(u"")
        self.mag_max_spin.setMaximum(10.000000000000000)
        self.mag_max_spin.setSingleStep(0.100000000000000)
        self.mag_max_spin.setValue(10.000000000000000)

        self.mag_range_layout.addWidget(self.mag_max_spin)

        self.filter_form_layout.setLayout(2, QFormLayout.FieldRole, self.mag_range_layout)

        self.repute_label = QLabel(self.attribute_group)
        self.repute_label.setObjectName(u"repute_label")
        self.repute_label.setStyleSheet(u"font: bold 13px arial, sans-serif;")

        self.filter_form_layout.setWidget(3, QFormLayout.LabelRole, self.repute_label)

        self.repute_combo = QComboBox(self.attribute_group)
        self.repute_combo.addItem("")
        self.repute_combo.addItem("")
        self.repute_combo.addItem("")
        self.repute_combo.addItem("")
        self.repute_combo.setObjectName(u"repute_combo")
        self.repute_combo.setMaximumSize(QSize(130, 16777215))
        self.repute_combo.setStyleSheet(u"")

        self.filter_form_layout.setWidget(3, QFormLayout.FieldRole, self.repute_combo)

        self.ref_label = QLabel(self.attribute_group)
        self.ref_label.setObjectName(u"ref_label")
        self.ref_label.setStyleSheet(u"font: bold 13px arial, sans-serif;")

        self.filter_form_layout.setWidget(5, QFormLayout.LabelRole, self.ref_label)

        self.ref_spin = QSpinBox(self.attribute_group)
        self.ref_spin.setObjectName(u"ref_spin")
        self.ref_spin.setMaximumSize(QSize(130, 16777215))
        self.ref_spin.setStyleSheet(u"")

        self.filter_form_layout.setWidget(5, QFormLayout.FieldRole, self.ref_spin)


        self.filter_layout.addLayout(self.filter_form_layout)


        self.attribute_layout.addLayout(self.filter_layout)

        self.verticalSpacer_4 = QSpacerItem(20, 15, QSizePolicy.Minimum, QSizePolicy.Fixed)

        self.attribute_layout.addItem(self.verticalSpacer_4)

        self.horiz_line_1 = QFrame(self.attribute_group)
        self.horiz_line_1.setObjectName(u"horiz_line_1")
        self.horiz_line_1.setMaximumSize(QSize(250, 1))
        self.horiz_line_1.setStyleSheet(u"background-color: #3b355e; ")
        self.horiz_line_1.setFrameShape(QFrame.HLine)
        self.horiz_line_1.setFrameShadow(QFrame.Sunken)

        self.attribute_layout.addWidget(self.horiz_line_1)

        self.repute_layout = QVBoxLayout()
        self.repute_layout.setObjectName(u"repute_layout")
        self.verticalSpacer_7 = QSpacerItem(20, 10, QSizePolicy.Minimum, QSizePolicy.Fixed)

        self.repute_layout.addItem(self.verticalSpacer_7)

        self.repute_form_layout = QFormLayout()
        self.repute_form_layout.setObjectName(u"repute_form_layout")
        self.repute_form_layout.setLabelAlignment(Qt.AlignLeading|Qt.AlignLeft|Qt.AlignTop)
        self.repute_form_layout.setVerticalSpacing(15)
        self.repute_good_label = QLabel(self.attribute_group)
        self.repute_good_label.setObjectName(u"repute_good_label")
        self.repute_good_label.setStyleSheet(u"font: bold 13px arial, sans-serif;")

        self.repute_form_layout.setWidget(0, QFormLayout.LabelRole, self.repute_good_label)

        self.repute_bad_label = QLabel(self.attribute_group)
        self.repute_bad_label.setObjectName(u"repute_bad_label")
        self.repute_bad_label.setStyleSheet(u"font: bold 13px arial, sans-serif;")

        self.repute_form_layout.setWidget(1, QFormLayout.LabelRole, self.repute_bad_label)

        self.bad_repute_bar = QProgressBar(self.attribute_group)
        self.bad_repute_bar.setObjectName(u"bad_repute_bar")
        self.bad_repute_bar.setMinimumSize(QSize(0, 8))
        self.bad_repute_bar.setMaximumSize(QSize(185, 8))
        self.bad_repute_bar.setStyleSheet(u"QProgressBar{margin-top:  5px; background-color: rgba(0,0,0,0); margin-left: 50px; color: #00000000;} QProgressBar:horizontal{background-color:rgba(0,0,0,0); text-align: center;}  QProgressBar::chunk:horizontal {background: qlineargradient(x1: 0, y1: 0.5, x2: 1, y2: 0.5, stop: 0 #910d01, stop: 1 #db1900);}")
        self.bad_repute_bar.setValue(0)

        self.repute_form_layout.setWidget(1, QFormLayout.FieldRole, self.bad_repute_bar)

        self.repute_neutral_label = QLabel(self.attribute_group)
        self.repute_neutral_label.setObjectName(u"repute_neutral_label")
        self.repute_neutral_label.setStyleSheet(u"font: bold 13px arial, sans-serif;")

        self.repute_form_layout.setWidget(2, QFormLayout.LabelRole, self.repute_neutral_label)

        self.neutral_repute_bar = QProgressBar(self.attribute_group)
        self.neutral_repute_bar.setObjectName(u"neutral_repute_bar")
        self.neutral_repute_bar.setMinimumSize(QSize(0, 5))
        self.neutral_repute_bar.setMaximumSize(QSize(185, 8))
        self.neutral_repute_bar.setStyleSheet(u"QProgressBar{margin-top:  5px; background-color: rgba(0,0,0,0); margin-left: 50px; color: #00000000;} QProgressBar:horizontal{background-color:rgba(0,0,0,0); text-align: center; }  QProgressBar::chunk:horizontal {background: qlineargradient(x1: 0, y1: 0.5, x2: 1, y2: 0.5, stop: 0 #913f01, stop: 1 #db5f00);}")
        self.neutral_repute_bar.setValue(0)

        self.repute_form_layout.setWidget(2, QFormLayout.FieldRole, self.neutral_repute_bar)

        self.good_repute_bar = QProgressBar(self.attribute_group)
        self.good_repute_bar.setObjectName(u"good_repute_bar")
        self.good_repute_bar.setMinimumSize(QSize(185, 5))
        self.good_repute_bar.setMaximumSize(QSize(130, 8))
        self.good_repute_bar.setStyleSheet(u"QProgressBar{margin-top:  5px; background-color: rgba(0,0,0,0); margin-left: 50px; color: #00000000;} QProgressBar:horizontal{text-align: center; } QProgressBar::chunk:horizontal {background: qlineargradient(x1: 0, y1: 0.5, x2: 1, y2: 0.5, stop: 0 #019120, stop: 1 #00db2f);}")
        self.good_repute_bar.setValue(0)

        self.repute_form_layout.setWidget(0, QFormLayout.FieldRole, self.good_repute_bar)

        log_label = QLabel("LOG 10*")
        log_label.setStyleSheet("margin-left: 220px; font-size: 8px")
        self.repute_form_layout.addRow(log_label)

        self.repute_layout.addLayout(self.repute_form_layout)

        self.line = QFrame(self.attribute_group)
        self.line.setObjectName(u"line")
        self.line.setMaximumSize(QSize(16777215, 1))
        self.line.setStyleSheet(u"background-color: #3b355e; ")
        self.line.setFrameShape(QFrame.HLine)
        self.line.setFrameShadow(QFrame.Sunken)

        self.repute_layout.addWidget(self.line)

        self.verticalSpacer_6 = QSpacerItem(20, 10, QSizePolicy.Minimum, QSizePolicy.Fixed)

        self.repute_layout.addItem(self.verticalSpacer_6)

        self.tot_layout = QHBoxLayout()
        self.tot_layout.setObjectName(u"tot_layout")
        self.tot_label = QLabel(self.attribute_group)
        self.tot_label.setObjectName(u"tot_label")
        self.tot_label.setStyleSheet(u"font: bold 13px arial, sans-serif;")

        self.tot_layout.addWidget(self.tot_label)

        self.total_score_label = QLabel(self.attribute_group)
        self.total_score_label.setObjectName(u"label")
        self.total_score_label.setStyleSheet(u"font: bold 13px arial, sans-serif;")

        self.tot_layout.addWidget(self.total_score_label, 0, Qt.AlignRight)


        self.repute_layout.addLayout(self.tot_layout)


        self.attribute_layout.addLayout(self.repute_layout)


        self.main_layout.addWidget(self.attribute_group, 0, Qt.AlignTop)


        self.horizontalLayout.addLayout(self.main_layout)

        MainWindow.setCentralWidget(self.centralwidget)

        self.retranslateUi(MainWindow)

        QMetaObject.connectSlotsByName(MainWindow)
    # setupUi

    def retranslateUi(self, MainWindow):
        MainWindow.setWindowTitle(QCoreApplication.translate("MainWindow", u"SNP Simple Reader", None))
#if QT_CONFIG(statustip)
        MainWindow.setStatusTip(QCoreApplication.translate("MainWindow", u"", None))
#endif // QT_CONFIG(statustip)
        self.data_label.setText(QCoreApplication.translate("MainWindow", u"DATA", None))
        self.load_data_button.setText(QCoreApplication.translate("MainWindow", u"Load...", None))
        self.rem_data_button.setText(QCoreApplication.translate("MainWindow", u"Remove...", None))
        self.results_label.setText(QCoreApplication.translate("MainWindow", u"RESULTS", None))
        self.results_search_bar.setPlaceholderText(QCoreApplication.translate("MainWindow", u"Summary contains...", None))
        # ___qtreewidgetitem = self.results_tree.headerItem()
        # ___qtreewidgetitem.setText(1, QCoreApplication.translate("MainWindow", u"Mag", None));
        # ___qtreewidgetitem.setText(0, QCoreApplication.translate("MainWindow", u"Gene", None));

#if QT_CONFIG(accessibility)
        self.attribute_group.setAccessibleName("")
#endif // QT_CONFIG(accessibility)
        self.filter_label.setText(QCoreApplication.translate("MainWindow", u"FILTERS", None))
        self.sort_label.setText(QCoreApplication.translate("MainWindow", u"SORT", None))
        self.sort_combo.setItemText(0, QCoreApplication.translate("MainWindow", u"Magnitude", None))
        self.sort_combo.setItemText(1, QCoreApplication.translate("MainWindow", u"Repute", None))
        self.sort_combo.setItemText(2, QCoreApplication.translate("MainWindow", u"SNP", None))

        self.mag_label.setText(QCoreApplication.translate("MainWindow", u"MAGNITUDE", None))
        self.repute_label.setText(QCoreApplication.translate("MainWindow", u"REPUTE", None))
        self.repute_combo.setItemText(0, QCoreApplication.translate("MainWindow", u"NA", None))
        self.repute_combo.setItemText(1, QCoreApplication.translate("MainWindow", u"Good", None))
        self.repute_combo.setItemText(2, QCoreApplication.translate("MainWindow", u"Neutral", None))
        self.repute_combo.setItemText(3, QCoreApplication.translate("MainWindow", u"Bad", None))

        # self.chromo_label.setText(QCoreApplication.translate("MainWindow", u"CHROMOSOME", None))
        self.ref_label.setText(QCoreApplication.translate("MainWindow", u"MIN REFERENCES", None))
        self.repute_good_label.setText(QCoreApplication.translate("MainWindow", u"GOOD", None))
        self.repute_bad_label.setText(QCoreApplication.translate("MainWindow", u"BAD", None))
        self.repute_neutral_label.setText(QCoreApplication.translate("MainWindow", u"NEUTRAL", None))
        self.tot_label.setText(QCoreApplication.translate("MainWindow", u"TOTAL", None))
        self.total_score_label.setText(QCoreApplication.translate("MainWindow", u"0", None))
    # retranslateUi

