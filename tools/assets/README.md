# Asset-generation utilities

These scripts generate source assets; they are not required to run the game because the generated assets are already included under `game/assets/`.

Run them from the repository root so their relative output paths resolve correctly. Optional Python dependencies are listed in `requirements-tools.txt`:

```sh
python -m pip install -r requirements-tools.txt
python tools/assets/make_bullets.py
```

Review the script before running an audio-generation script because outputs may overwrite files under `game/assets/`.
