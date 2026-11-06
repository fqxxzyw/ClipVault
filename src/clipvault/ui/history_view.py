"""List/grid layout and explicit multi-selection shared by both history windows."""

from PySide6.QtCore import QItemSelectionModel, QSize, Qt, Signal
from PySide6.QtWidgets import QAbstractItemView, QListView


class HistoryView(QListView):
    selection_count_changed = Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.batch_mode = False
        self.grid_mode = False
        self._reset_ids = []
        self.setResizeMode(QListView.ResizeMode.Adjust)

    def setModel(self, model):
        super().setModel(model)
        self.selectionModel().selectionChanged.connect(self._selection_changed)
        model.modelAboutToBeReset.connect(self._remember_selection)
        model.modelReset.connect(self._restore_selection)

    def _selection_changed(self, *_):
        self.selection_count_changed.emit(len(self.selected_ids()))
        self.viewport().update()

    def selected_ids(self):
        if not self.batch_mode:
            return []
        indexes = sorted(self.selectionModel().selectedRows(), key=lambda index: index.row())
        return [index.data(Qt.ItemDataRole.UserRole).id for index in indexes]

    def set_batch_mode(self, enabled):
        self.batch_mode = enabled
        self.setSelectionMode(
            QAbstractItemView.SelectionMode.MultiSelection
            if enabled
            else QAbstractItemView.SelectionMode.SingleSelection
        )
        self.clearSelection()
        if self.itemDelegate():
            self.itemDelegate().batch_mode = enabled
        self._selection_changed()

    def toggle_index(self, index):
        if not index.isValid():
            return
        selection = self.selectionModel()
        selection.setCurrentIndex(index, QItemSelectionModel.SelectionFlag.NoUpdate)
        selection.select(index, QItemSelectionModel.SelectionFlag.Toggle)

    def set_grid_mode(self, enabled):
        self.grid_mode = enabled
        self.setViewMode(QListView.ViewMode.IconMode if enabled else QListView.ViewMode.ListMode)
        self.setFlow(QListView.Flow.LeftToRight if enabled else QListView.Flow.TopToBottom)
        self.setWrapping(enabled)
        self.setMovement(QListView.Movement.Static)
        self.setUniformItemSizes(True)
        if self.itemDelegate():
            self.itemDelegate().grid_mode = enabled
        self._adjust_grid()
        self.viewport().update()

    def _adjust_grid(self):
        if self.grid_mode:
            width = max(1, self.viewport().width() - 4)
            columns = max(1, width // 145)
            self.setGridSize(QSize(width // columns, 154))
        else:
            self.setGridSize(QSize())

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._adjust_grid()

    def _remember_selection(self):
        self._reset_ids = self.selected_ids()

    def _restore_selection(self):
        if self.batch_mode:
            for row in range(self.model().rowCount()):
                index = self.model().index(row, 0)
                if index.data(Qt.ItemDataRole.UserRole).id in self._reset_ids:
                    self.selectionModel().select(index, QItemSelectionModel.SelectionFlag.Select)
        self._reset_ids = []
        self._selection_changed()
