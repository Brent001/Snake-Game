# v26 — Class-Specific Snake Head Animation

The non-Cobra player heads have been redesigned and animated so the four classes no longer share the same generic recolored snake head.

## Viper
- Narrower angular venom-head silhouette.
- Animated cheek markings and breathing/sway.
- Eye blink/pupil motion.
- Fast forked tongue flick.
- Fangs appear during lunge/bite.

## Python
- Wider heavy wedge-shaped head.
- Slower, weightier idle motion.
- Broad brow/cheek markings.
- Animated eyelids and vertical pupils.
- Opening lower jaw and slower tongue cycle.
- More pronounced jaw opening during lunge.

## Mamba
- Sleek elongated assassin head.
- Fast head sway and breathing motion.
- Red slit eyes with bright eye highlights.
- Rapid forked tongue flick.
- Animated cheek/center stripe.
- Small electric crackle accents while moving/dashing.
- Fangs during lunge.

## Cobra
- Kept the existing hooded silhouette and rendering path unchanged, per request.

## Validation
- `python -m compileall -q game`
- `python -m py_compile main.py game/app.py game/render/entities.py`
- Head rendering smoke test under Xvfb for all four classes and multiple animation timestamps.
