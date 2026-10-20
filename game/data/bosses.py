"""Touhou-inspired boss roster with character-specific spell-card phases.

Phase design:
- Every phase introduces a new readable attack motif and increases pressure.
- The final phase unlocks one one-time character signature super when the boss is
  below 55% of that phase's HP.
- These are original gameplay implementations inspired by Touhou's danmaku
  language, not copied engine code/assets.
"""

BOSSES = [
    dict(name="CIRNO", sprite="cirno", biome="MISTY LAKE", phases=[
        dict(name='Ice Sign "Icicle Fall"', hp=54, color="#7df9ff",
             skills=[("icicle_fall", 7.0, 1.8), ("frost_fan", 9.0, 4.2), ("frost_patch", 11.0, 7.2)]),
        dict(name='Snow Sign "Diamond Blizzard"', hp=74, color="#bfe9ff",
             skills=[("diamond_blizzard", 7.4, 1.5), ("crystal_prism", 9.4, 4.0), ("perfect_freeze", 10.5, 7.0)]),
        dict(name='Freeze Sign "Perfect Freeze"', hp=98, color="#e7fbff",
             skills=[("perfect_freeze", 8.2, 1.2), ("ice_prison", 10.0, 4.0), ("frozen_stars", 11.0, 6.8)],
             super="absolute_zero", super_threshold=0.55)]),
    dict(name="MARISA KIRISAME", sprite="marisa", biome="FOREST OF MAGIC", phases=[
        dict(name='Magic Sign "Stardust Reverie"', hp=60, color="#ffd34d",
             skills=[("star_dash", 6.5, 1.8), ("stardust_wheel", 8.8, 4.1), ("orrery_sun", 10.5, 7.0)]),
        dict(name='Astral Sign "Orrery Matrix"', hp=84, color="#fff0a8",
             skills=[("orrery_sun", 8.0, 1.5), ("orrery_crossfire", 9.2, 4.0), ("star_dash", 9.0, 6.8)]),
        dict(name='Love Sign "Master Spark"', hp=112, color="#ff7ad9",
             skills=[("master_spark", 8.3, 1.2), ("meteor_streak", 9.0, 3.8), ("star_dash", 10.0, 7.0)],
             super="final_master_spark", super_threshold=0.55)]),
    dict(name="REMILIA SCARLET", sprite="remilia", biome="SCARLET MANSION GROUNDS", phases=[
        dict(name='Scarlet Sign "Red Magic"', hp=66, color="#ff4f6d",
             skills=[("scarlet_shoot", 6.5, 1.7), ("scarlet_fan", 8.4, 4.0), ("bat_warp", 10.0, 7.0)]),
        dict(name='Divine Spear "Spear the Gungnir"', hp=92, color="#ff9aa8",
             skills=[("gungnir", 7.0, 1.5), ("fate_chains", 9.0, 4.0), ("bat_warp", 9.5, 6.7)]),
        dict(name='Night Sign "Demon King Cradle"', hp=122, color="#c91f45",
             skills=[("vampire_kiss", 7.2, 1.2), ("nightless_castle", 8.6, 3.6), ("scarlet_shoot", 7.0, 6.2)],
             super="scarlet_destiny", super_threshold=0.55)]),
    dict(name="FLANDRE SCARLET", sprite="flandre", biome="THE NETHERWORLD", phases=[
        dict(name='Taboo "Lævateinn"', hp=74, color="#ff4f6d",
             skills=[("laevateinn", 7.0, 1.6), ("crumbling_edges", 9.0, 4.2)]),
        dict(name='Taboo "Four of a Kind"', hp=96, color="#ffd34d",
             skills=[("four_of_a_kind", 7.8, 1.4), ("clone_prism", 9.0, 4.0)]),
        dict(name='Forbidden Barrage "Starbow Break"', hp=124, color="#ff7ad9",
             skills=[("starbow_break", 7.0, 1.2), ("rainbow_sawtooth", 8.5, 3.7)]),
        dict(name='Q.E.D. "Ripples of 495 Years"', hp=158, color="#c78bff",
             skills=[("ripples_495", 7.2, 1.1), ("clockwork_prism", 8.6, 3.8), ("four_of_a_kind", 10.0, 6.2)],
             super="destruction_495", super_threshold=0.55)]),
    dict(name="REIMU HAKUREI", sprite="reimu", biome="HAKUREI SHRINE", phases=[
        dict(name='Spirit Sign "Fantasy Seal"', hp=70, color="#ff3c5f",
             skills=[("fantasy_seal", 6.8, 1.7), ("ofuda_spiral", 8.7, 4.1)]),
        dict(name='Dream Sign "Evil-Sealing Circle"', hp=98, color="#ff7a9c",
             skills=[("barrier_ring", 7.8, 1.5), ("barrier_shuffle", 9.0, 3.9), ("fantasy_seal", 9.5, 6.7)]),
        dict(name='Divine Arts "Omnidirectional Oni-Binding Circle"', hp=124, color="#ffb347",
             skills=[("binding_net", 8.0, 1.3), ("binding_cross", 8.8, 3.6), ("yin_yang_orbit", 9.2, 6.3)]),
        dict(name='Last Word "Innate Dream"', hp=168, color="#c78bff",
             skills=[("innate_dream", 6.5, 1.0), ("yin_yang_maze", 8.2, 3.4), ("binding_net", 9.0, 6.0)],
             super="dream_of_hakurei", super_threshold=0.55)]),
]

SKILL_NAMES = dict(
    icicle_fall="Icicle Fall!", frost_fan="Frostblade Fan!", frost_patch="Frozen Ground!",
    perfect_freeze="Perfect Freeze!", diamond_blizzard="Diamond Blizzard!", crystal_prism="Crystal Prism!",
    ice_prison="Ice Prison!", frozen_stars="Frozen Starfall!", absolute_zero="ULTIMATE: Absolute Zero!",
    star_dash="Broom Dash!", stardust_wheel="Stardust Wheel!", orrery_sun="Orreries Sun!",
    orrery_crossfire="Orrery Crossfire!", master_spark="MASTER SPARK!", meteor_streak="Meteoric Streak!",
    final_master_spark="FINAL MASTER SPARK!",
    bat_warp="Bat Transformation!", gungnir="Spear the Gungnir!", vampire_kiss="Demon King Cradle!",
    scarlet_shoot="Scarlet Shoot!", scarlet_fan="Scarlet Fan!", fate_chains="Fate Chain!",
    nightless_castle="Red the Nightless Castle!", scarlet_destiny="LAST WORD: Scarlet Destiny!",
    laevateinn="Lævateinn!", four_of_a_kind="Four of a Kind!", starbow_break="Starbow Break!",
    ripples_495="Ripples of 495 Years!", crumbling_edges="Crumbling Edge!", clone_prism="Clone Prism!",
    rainbow_sawtooth="Rainbow Sawtooth!", clockwork_prism="Clockwork Prism!",
    destruction_495="Q.E.D.: 495 Years of Destruction!",
    fantasy_seal="Fantasy Seal!", barrier_ring="Evil-Sealing Circle!", binding_net="Oni-Binding Circle!",
    warp="Hakurei Warp!", yin_yang_orbit="Yin-Yang Orbit!", innate_dream="Innate Dream!",
    ofuda_spiral="Ofuda Spiral!", barrier_shuffle="Barrier Shuffle!", binding_cross="Binding Cross!",
    yin_yang_maze="Yin-Yang Maze!", dream_of_hakurei="LAST WORD: Dream of Hakurei!",
)
