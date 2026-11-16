/** Java1.2.0 ModEffects: Forge c4ec1880 / NeoForge a1afba34.
 * This is the built-in registration source, including the existing adapters.
 * mode describes direct application, matching Java isInstantenous(). It does
 * not bypass a MobEffectInstance duration on the separate add_status path.
 * Availability means wired behaviour; it does not promise complete Java parity.
 */
export const TAVERN_EFFECT_DEFINITIONS=Object.freeze([
 ['bloody_mary','beneficial','timed','kill_heal'],
 ['xp_drain','beneficial','timed','orb_attraction_adapter'],
 ['zenith','beneficial','instant','safe_surface_teleport_adapter'],
 ['shriek_attack','beneficial','instant','sonic_ray_pve_adapter'],
 ['upside_down','neutral','instant','grumm_radius_name_adapter'],
 ['vision','beneficial','timed','glowing_radius_adapter'],
 ['tomb_raider','beneficial','timed','disarm_drop_adapter'],
 ['ardent_heat','beneficial','timed','sprint_break_adapter'],
 ['high_heels','beneficial','timed','one_block_auto_step_adapter'],
 ['grass_stealth','beneficial','timed','grass_exhaustion_and_invisibility_adapter'],
 ['long_reach','beneficial','timed','routed_item_use_9m_adapter'],
 ['slightly_tipsy','neutral','timed','opt_in_yaw_adapter_unverified']
].map(([name,category,mode,implementation])=>Object.freeze({id:'kaleidoscope_tavern:'+name,source:'kaleidoscope_tavern',category,mode,implementation,available:true})));
