"""Interruptible 200ms transitions, with no timer or repaint while idle."""

import ctypes
import sys

from PySide6.QtCore import (
    QEasingCurve,
    QObject,
    QParallelAnimationGroup,
    QPoint,
    QPropertyAnimation,
    Qt,
)
from PySide6.QtWidgets import QGraphicsOpacityEffect, QLabel


def system_reduces_motion() -> bool:
    if sys.platform != "win32":
        return False
    from ctypes import wintypes

    enabled = wintypes.BOOL(True)
    api = ctypes.windll.user32.SystemParametersInfoW
    api.argtypes = [wintypes.UINT, wintypes.UINT, ctypes.c_void_p, wintypes.UINT]
    api.restype = wintypes.BOOL
    return bool(api(0x1042, 0, ctypes.byref(enabled), 0)) and not enabled.value


class Motion(QObject):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.reduced = False
        self.active = {}
        self._slide_targets = {}

    def configure(self, reduced: bool):
        self.reduced = reduced
        if reduced or system_reduces_motion():
            self.stop()

    def stop(self):
        for widget in list(self.active):
            self._finish(widget)

    def _finish(self, widget):
        entry = self.active.pop(widget, None)
        if entry:
            animation, overlay = entry
            animation.stop()
            slide = self._slide_targets.pop(widget, None)
            if slide:
                slide[0].move(slide[1])
            overlay.hide()
            overlay.deleteLater()
            animation.deleteLater()

    def transition(self, widget, change):
        self._finish(widget)
        animate = not self.reduced and not system_reduces_motion() and widget.isVisible()
        change()
        if not animate:
            return
        # Fade a neutral veil over the new content, never stale clickable rows.
        overlay = QLabel(widget)
        overlay.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        overlay.setStyleSheet("background: " + widget.palette().window().color().name() + ";")
        overlay.setGeometry(widget.rect())
        effect = QGraphicsOpacityEffect(overlay)
        overlay.setGraphicsEffect(effect)
        animation = QPropertyAnimation(effect, b"opacity", self)
        animation.setDuration(220)
        animation.setStartValue(0.65)
        animation.setEndValue(0.0)
        animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        group = QParallelAnimationGroup(self)
        group.addAnimation(animation)
        if hasattr(widget, "currentWidget") and widget.currentWidget() is not None:
            page = widget.currentWidget()
            destination = page.pos()
            slide = QPropertyAnimation(page, b"pos", group)
            slide.setDuration(220)
            slide.setStartValue(destination + QPoint(0, 12))
            slide.setEndValue(destination)
            slide.setEasingCurve(QEasingCurve.Type.OutCubic)
            group.addAnimation(slide)
            self._slide_targets[widget] = (page, destination)
        self.active[widget] = (group, overlay)
        group.finished.connect(lambda: self._finish(widget))
        overlay.show()
        overlay.raise_()
        group.start()
