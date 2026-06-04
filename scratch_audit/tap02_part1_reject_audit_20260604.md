# Tap 2 Part 1 Image Audit - 2026-06-04

Criteria note: Lam Tich glam/pin-up energy is allowed if the scene still matches the story beat, correct age, correct cast, and stays non-explicit.

## Rejected Scenes
- scene-001.png: duplicate_subject, wrong_subject_count, not_story_specific
- scene-002.png: wrong_cast, military_drift, location_leak
- scene-003.png: duplicate_lam_tich, not_story_specific
- scene-004.png: duplicate_lam_tich, too_explicit_for_story, not_story_specific
- scene-006.png: child_miscast, military_drift, weapon_invented
- scene-008.png: wrong_cast, missing_lam_tich, generic_two_man_frame
- scene-009.png: wrong_subject_count, missing_tieu_ngo_context
- scene-010.png: wrong_subject_count, generic_single_subject
- scene-012.png: generic_single_subject, missing_group_context
- scene-013.png: wrong_age_mix, generic_child_blocking
- scene-014.png: child_scene_wrong_cast, board_not_visible, extra_wrong_child
- scene-019.png: wrong_age_or_cast, generic_standoff
- scene-020.png: wrong_cast, repeated_generic_child_pair
- scene-022.png: wrong_cast, missing_ration_power_dynamic
- scene-024.png: wrong_cast, military_drift, missed_water_scent_beat
- scene-027.png: weapon_invented, child_miscast, military_drift
- scene-030.png: wrong_cast, generic_two_girl_frame
- scene-031.png: generic_single_subject, missing_story_object
- scene-032.png: wrong_cast, adult_woman_plus_child_mismatch, not_story_specific
- scene-034.png: wrong_location, well_missing, wrong_cast
- scene-038.png: child_miscast, wrong_group_composition
- scene-039.png: generic_single_subject, missing_story_action
- scene-040.png: wrong_cast, missing_a_that_specificity
- scene-045.png: generic_single_subject, missing_story_action
- scene-047.png: wrong_location, trade_table_drift, missing_scene_object
- scene-048.png: generic_duo_glam, wrong_cast
- scene-050.png: not_story_specific, too_explicit_for_story
- scene-054.png: weapon_invented, child_miscast
- scene-055.png: wrong_cast, missing_group_balance
- scene-057.png: not_story_specific, single_glam_portrait_instead_of_story_beat
- scene-060.png: too_explicit_for_story, missing_journey_context
- scene-062.png: wrong_cast, military_drift, missing_wheelchair_or_group_context
- scene-063.png: wrong_cast, missing_child, generic_two_men
- scene-064.png: wrong_cast, missing_wheelchair_or_group_column
- scene-065.png: wrong_cast, children_replaced_adults, missing_tan_da_tieu_mai

## Kept Scenes
- scene-005.png, scene-007.png, scene-011.png, scene-015.png, scene-016.png, scene-017.png, scene-018.png, scene-021.png, scene-023.png, scene-025.png, scene-026.png, scene-028.png, scene-029.png, scene-033.png, scene-035.png, scene-036.png, scene-037.png, scene-041.png, scene-042.png, scene-043.png, scene-044.png, scene-046.png, scene-049.png, scene-051.png, scene-052.png, scene-053.png, scene-056.png, scene-058.png, scene-059.png, scene-061.png

## Root Fixes Applied
- Broad pronoun-based subject detection was removed so adult male/female leads are no longer inferred from generic words alone.
- Medical-scene classification was tightened so well, railway, valuation, trade, and water-scent scenes are less likely to be misread as generic injury beats.
- Board-exchange scenes now center on the writing board and the child exchange, instead of generic group-dialogue framing.
- Location pruning was hardened so railway, old well, Gray Station, District 17 fire lanes, and Tunnel 4 stop bleeding into each other.
- Foreground cast pruning was tightened so child scenes, appraisal scenes, trade scenes, and ration scenes carry fewer random extra people.
- Lam Tich styling was re-aligned to allow feminine glam / wasteland pin-up energy when the beat allows it, while still forbidding explicit exposure and off-story fetish framing.
- Tan Da styling was kept strongly adult-male, tall, muscular, and righteous, while reducing the accidental tactical-soldier drift.
- Image prompt negatives now push harder against invented rifles, SWAT/commando posing, military squad blocking, and adult combat styling on child characters.