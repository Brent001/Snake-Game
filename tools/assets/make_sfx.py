import wave, numpy as np, os, shutil
RAW='raw'; OUT='game_src/game/assets/sfx'
# game name: (source, max_seconds, peak)
M = {
 'player_shot':('t_shot1',.18,.55), 'player_volley':('t_shot3',.25,.6), 'player_spit':('t_shot2',.34,.6),
 'player_strike':('p_hit_slash',.40,.7), 'knife_attack':('p_hit_stab',.35,.6), 'dash':('p_miss',.45,.6),
 'player_hurt':('t_hit0',.50,.8), 'player_death':('t_death',1.4,.8), 'skill':('t_shot_special1',.6,.6),
 'rattle':('p_bones',.7,.6), 'enemy_shot':('t_generic_shot',.1,.4), 'enemy_die':('t_enemydeath',.6,.6),
 'enemy_charge':('t_charge_generic',.9,.6), 'enemy_bomb':('t_boom',.9,.7), 'enemy_hit':('p_hit',.15,.5),
 'boss_hit':('t_hit',.14,.55), 'ice_attack':('p_hit_magic',.5,.6), 'freeze_ring':('p_shatter',.65,.65),
 'star_attack':('p_atk_spiritbow',.5,.6), 'amulet_attack':('p_atk_crossbow',.5,.6), 'butterfly_attack':('p_charms',.8,.55),
 'spell_attack':('t_discharge',.7,.65), 'laser_charge':('p_chargeup',1.3,.65), 'master_spark':('p_master_spark_ray',2.6,.75),
 'boss_warning':('p_alert',.5,.65), 'boss_start':('p_boss',2.2,.75), 'boss_defeat':('t_bossdeath',2.6,.85),
 'spell_break':('t_spellend',.93,.8), 'portal_enter':('t_warp',1.1,.8), 'portal_exit':('p_teleport',.9,.7),
 'portal_locked':('p_chains',.6,.65), 'eat':('p_eat',.5,.6), 'pickup':('p_item',.5,.6), 'heal':('p_dewdrop',.6,.55),
 'charge_get':('t_powerup',.8,.65), 'oculus':('p_badge',1.2,.65), 'levelup':('p_levelup',1.6,.75),
 'save':('t_boon',1.2,.7), 'bump':('p_hit_crush',.4,.7), 'menu_move':('p_click',.05,.45), 'menu_select':('p_unlock',.1,.55),
}
for name,(src,mx,pk) in M.items():
    w=wave.open(f'{RAW}/{src}.wav'); sr=w.getframerate(); d=np.frombuffer(w.readframes(w.getnframes()),dtype=np.int16).astype(np.float32)/32768
    loud=np.where(np.abs(d)>0.01)[0]
    if len(loud): d=d[loud[0]:]
    d=d[:int(mx*sr)]
    f=min(len(d)//4,int(.04*sr)); d[-f:]*=np.linspace(1,0,f)
    m=np.abs(d).max() or 1; d=d/m*pk
    o=wave.open(f'{OUT}/{name}.wav','wb'); o.setnchannels(1); o.setsampwidth(2); o.setframerate(sr); o.writeframes((d*32767).astype(np.int16).tobytes()); o.close()
print(len(M),'written'); print(sum(os.path.getsize(f'{OUT}/{n}.wav') for n in M)//1024,'KB')
