from project.qt_bindings import QCalendarWidget, QDate, Qt, QTextCharFormat

class CalendarView(QCalendarWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
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
        super().mousePressEvent(event)
        if event.button() == Qt.LeftButton:
            self.dateClicked.emit(self.selectedDate())

    def keyPressEvent(self, event):
        super().keyPressEvent(event)
        if event.key() == Qt.Key_Space:
            self.dateClicked.emit(self.selectedDate())

__all__ = ["CalendarView"]