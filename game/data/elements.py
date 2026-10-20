"""Elements, reactions, resonances and stat labels."""

ELEMS = ["geo", "dendro", "hydro", "pyro", "cryo", "electro", "anemo", "abyss", "light"]
ECOL = dict(geo="#f5c542", dendro="#7ddb4a", hydro="#4aa8ff", pyro="#ff6a3a", cryo="#9fefff",
    electro="#c18bff", anemo="#6fffd0", abyss="#a64dff", light="#fff3b0", pulse="#cfe2ff", quicken="#8affc0",
    tank="#ffa23c", ranged="#ff5da2", mamba="#e6ff4a")

# Genshin-style reactions (see the reference notes):
#  Amplifying   : Vaporize / Melt multiply the hit (x2.0 or x1.5 depending on who triggers), boosted by Elemental Mastery
#  Transformative: Overload, Electro-Charged, Superconduct, Swirl, Shatter, Bloom, Burgeon, Hyperbloom
#                  ignore Attack and Crit; they scale with your LEVEL and Elemental Mastery only
#  Quicken      : Dendro + Electro leaves a Quicken aura -> Dendro hits Spread, Electro hits Aggravate (flat bonus damage)
# anemo = swirl and geo = crystallize with ANY aura.
REACT = {
    frozenset(("pyro", "hydro")): "vaporize", frozenset(("pyro", "cryo")): "melt",
    frozenset(("hydro", "cryo")): "freeze", frozenset(("pyro", "electro")): "overload",
    frozenset(("hydro", "electro")): "electro-charged", frozenset(("cryo", "electro")): "superconduct",
    frozenset(("dendro", "pyro")): "burning", frozenset(("dendro", "hydro")): "bloom",
    frozenset(("dendro", "electro")): "quicken", frozenset(("abyss", "light")): "eclipse",
}

# Elemental Resonance: allocate RESON_NODES nodes of one element to switch it on
RESON = dict(
    pyro=("Fervent Flames", "+25% damage"),
    hydro=("Soothing Water", "+25% Max HP"),
    cryo=("Shattering Ice", "+15% crit rate vs Cryo / frozen enemies"),
    electro=("High Voltage", "Electro reactions restore 12 stamina"),
    geo=("Enduring Rock", "+15% shield strength, +15% damage while shielded"),
    anemo=("Impetuous Winds", "+10% move speed, -15% stamina costs"),
    dendro=("Sprawling Greenery", "+50 Elemental Mastery"),
    abyss=("Void Communion", "+3% lifesteal"),
    light=("Radiant Accord", "+10% XP gain"))

LABEL = dict(hp="Max HP", regen="HP regen /s", dmg="% Shot damage", melee="% Strike damage", stam="Max stamina",
    stamr="% Stamina regen", dashcd="s Dash cooldown reduction", dashlen="Dash length", armor="% Damage reduction",
    hp_pct="% Max HP", regen_pct="% Max HP regenerated /s", energy_recharge="% Energy recharge rate",
    energy_max="Max energy", energy_on_kill="% chance to restore energy on kill", life_on_hit="Life gained on hit",
    life_on_kill="Life gained on kill", less_damage="% Less damage taken", shield_pct="% Shield strength",
    ammo="Pulse capacity", charges="Charges per pickup", speed="% Move speed", xp="% XP gain", venom="Venom DPS",
    steal="% Lifesteal", pierce="Shot pierce", burn="Burn DPS", freeze="s Freeze time", chain="Chain damage",
    aoe="Blast radius", coil="Coil DPS", shed="% Shed Skin heal", heat="s Heat Sense time", lunge="Strike reach",
    iframe="s Dash i-frames", crystal="Crystallize shield", swirl="Swirl power", bloom="Bloom power",
    eclipse="Eclipse power", em="Elemental Mastery", crit="% Crit rate", cdmg="% Crit damage",
    wallres="% Wall impact reduction", rng="% Ranged bolt damage", volley="Volley bolts", bulwark="% Bulwark strength",
    foodhp="Max HP per food", foodheal="HP per food", form_tank="Tank Form", form_ranged="Ranged Form",
    form_mamba="Mamba Form", class_skill="Class skill power", strike_width="Strike width", strike_stun="Strike stun",
    strike_venom="Strike venom DPS", coil_dps="Coil DPS bonus", coil_slow="Coil slow time", coil_guard="Coil damage reduction",
    shed_heal="Shed heal", shed_iframe="Shed invulnerability", shed_decoy="Decoy duration", heat_bonus="Heat Sense duration",
    heat_mult="Heat Sense damage", scent_time="Scent duration", scent_range="Scent range", spit_reach="Spit reach",
    spit_stun="Spit stun", spit_damage="Spit damage", rattle_radius="Rattle radius", rattle_stun="Rattle stun",
    rattle_force="Rattle knockback", camo_time="Camouflage duration", camo_range="Camouflage proximity",
    volley_count="Volley bolts", volley_damage="Volley damage", volley_pierce="Volley pierce", bulwark_time="Bulwark duration",
    bulwark_shield="Bulwark shield", bulwark_radius="Bulwark radius", dash_bonus="Dash length bonus")
