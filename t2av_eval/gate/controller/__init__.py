"""Text-only controller backends (pipeline v4 stage 3): read the stage-1 text output of a flagged item and choose one
observation (or STOP). Two implementations, Gemini and OpenAI (the third-controller experiment). No media argument exists: the
media judge (t2av_eval.judge.media) is Gemini only and never goes through this interface."""
from t2av_eval.gate.controller.base import Controller, STAGE3_SCHEMA, load_config, make  # noqa: F401
