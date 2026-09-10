"""Keine periodischen Jobs im TaskBuddy-MVP."""

from __future__ import annotations

from telegram.ext import Application


def schedule_jobs(application: Application) -> None:
    return
