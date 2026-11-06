"""Prepare a self-contained rich clipboard payload in visual selection order."""

import base64
import html
import shutil
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path

from clipvault.core.text_cleanup import clean_text
from clipvault.database.models import Clip


@dataclass(frozen=True)
class BatchPayload:
    ids: tuple[int, ...]
    text: str
    html: str
    images: tuple[bytes, ...]
    image_files: tuple[str, ...] = ()


def prepare_batch(items: list[tuple[Clip, bytes | None]], cache: Path, *, clean=False):
    texts, parts, images = [], [], []
    for clip, png in items:
        if clip.content_type == "image":
            if not png:
                raise ValueError("Missing image")
            images.append(png)
            encoded = base64.b64encode(png).decode("ascii")
            parts.append(f'<div><img src="data:image/png;base64,{encoded}"></div>')
        else:
            text = (
                clean_text(clip.content) if clean and clip.content_type != "files" else clip.content
            )
            texts.append(text)
            escaped = html.escape(text).replace("\n", "<br>")
            parts.append(f'<div style="white-space:pre-wrap">{escaped}</div>')

    paths = []
    if len(images) > 1 and not texts:
        # CF_HDROP lets file-oriented applications paste each image separately.
        # Keep the files for a week, including across app exits, so delayed pastes work.
        cache.mkdir(parents=True, exist_ok=True)
        for old in cache.glob("batch-*"):
            if old.is_symlink() or not old.is_dir():
                continue
            try:
                if time.time() - old.stat().st_mtime > 7 * 24 * 60 * 60:
                    shutil.rmtree(old)
            except OSError:
                pass
        batch_dir = Path(tempfile.mkdtemp(prefix="batch-", dir=cache))
        try:
            for index, png in enumerate(images, 1):
                path = batch_dir / f"ClipVault-{index:03}.png"
                path.write_bytes(png)
                paths.append(str(path))
        except OSError:
            shutil.rmtree(batch_dir, ignore_errors=True)
            raise

    return BatchPayload(
        tuple(clip.id for clip, _ in items),
        "\n\n".join(texts),
        "<html><body>" + '<div style="height:1em"></div>'.join(parts) + "</body></html>",
        tuple(images),
        tuple(paths),
    )
