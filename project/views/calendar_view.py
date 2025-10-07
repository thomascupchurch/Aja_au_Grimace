from project.qt_bindings import *
from project.helpers import resolve_resource_path

class CalendarView(QCalendarWidget):
    def __init__(self, parent=None):
        super(CalendarView, self).__init__(parent)
        # Set the default view to the month view
        self.setFirstDayOfWeek(Qt.Monday)
        self.setVerticalHeaderFormat(QCalendarWidget.NoVerticalHeader)
        self.setHorizontalHeaderFormat(QCalendarWidget.ShortDayNames)
        self.setNavigationBarVisible(True)
        self.setGridVisible(True)
        self.setSelectionMode(QCalendarWidget.SingleSelection)
        self.setDateTextFormat(QDate.currentDate(), QTextCharFormat())
        self.setCurrentPage(QDate.currentDate().year(), QDate.currentDate().month())

    def mousePressEvent(self, event):
        super(CalendarView, self).mousePressEvent(event)
        if event.button() == Qt.LeftButton:
            date = self.selectedDate()
            self.emit_date_clicked(date)

    def emit_date_clicked(self, date):
        self.dateClicked.emit(date)

    def keyPressEvent(self, event):
        super(CalendarView, self).keyPressEvent(event)
        if event.key() == Qt.Key_Space:
            date = self.selectedDate()
            self.emit_date_clicked(date)