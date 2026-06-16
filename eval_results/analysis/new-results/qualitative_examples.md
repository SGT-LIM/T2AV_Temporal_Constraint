# Qualitative examples

TP/TN are agreements with human GT. FP/FN are disagreements.
FP = Gemini yes / human no. FN = Gemini no / human yes.

## no_tool

### A

#### TP — Sp_Si_So_rel_ord_SiSpSo v1

- Human: `yes` / Gemini: `yes`
- Temporal type: `relative_order`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: Both required audio events are present: the word 'help' is spoken clearly, and a slap sound is audible.
- Gemini evidence: The speech 'help' is heard at 0:00.000, and a distinct slap sound is heard around 0:03.000.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/no_tool_A_TP_Sp_Si_So_rel_ord_SiSpSo_v1.txt`

#### TP — Sp_So_rel_sync_cnt v1

- Human: `yes` / Gemini: `yes`
- Temporal type: `relative_sync_count`
- Modality: `Speech + Action (sounding)`
- Gemini reason: The required speech ('help') and thigh-slapping sounds are both present and clearly audible.
- Gemini evidence: The word 'help' is heard at the beginning of the video, and multiple distinct slap sounds are heard subsequently.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/no_tool_A_TP_Sp_So_rel_sync_cnt_v1.txt`

#### TP — Sp_Si_So_rel_sync v1

- Human: `yes` / Gemini: `yes`
- Temporal type: `relative_synchronization`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: The word 'help' and a clear slap sound are both audible in the generated audio.
- Gemini evidence: Audio contains the spoken word 'help' followed by a slapping sound.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/no_tool_A_TP_Sp_Si_So_rel_sync_v1.txt`

#### TN — Sp_So_rel_ord_SoSp v1

- Human: `no` / Gemini: `no`
- Temporal type: `relative_order`
- Modality: `Speech + Action (sounding)`
- Gemini reason: The required speech audio for the word 'help' is completely missing.
- Gemini evidence: A slap sound is audible at 00:01.000, but no speech is heard throughout the video.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/no_tool_A_TN_Sp_So_rel_ord_SoSp_v1.txt`

#### FP — Sp_So_rel_sync v1

- Human: `no` / Gemini: `yes`
- Temporal type: `relative_synchronization`
- Modality: `Speech + Action (sounding)`
- Gemini reason: The required speech and slap sound are both present in the audio.
- Gemini evidence: The audio track contains the spoken word "help" and a sharp slap sound.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/no_tool_A_FP_Sp_So_rel_sync_v1.txt`

#### FN — Sp_Si_So_rel_sync_cnt v1

- Human: `yes` / Gemini: `no`
- Temporal type: `relative_sync_count`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: The speech 'help' is spoken twice, but the required sharp slap sound is entirely missing from the audio track.
- Gemini evidence: Audio contains the word 'help' at roughly 00:00.6 and 00:01.2, but no slapping sounds are audible at any point.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/no_tool_A_FN_Sp_Si_So_rel_sync_cnt_v1.txt`

#### FN — Sp_Si_So_rel_ord_SoSpSi v1

- Human: `yes` / Gemini: `no`
- Temporal type: `relative_order`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: The word 'help' is spoken clearly, but the required sharp slap sound is missing from the audio track.
- Gemini evidence: Speech 'help' is heard at the start of the video, but no thigh slap sound occurs anywhere.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/no_tool_A_FN_Sp_Si_So_rel_ord_SoSpSi_v1.txt`

#### FN — Sp_Si_rel_sync_cnt v1

- Human: `yes` / Gemini: `no`
- Temporal type: `relative_sync_count`
- Modality: `Speech + Action (silent)`
- Gemini reason: The audio track is completely silent. The required word 'help' is not spoken.
- Gemini evidence: No speech audio is heard throughout the video.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/no_tool_A_FN_Sp_Si_rel_sync_cnt_v1.txt`

### V

#### TP — Sp_Si_So_rel_ord_SpSiSo v1

- Human: `yes` / Gemini: `yes`
- Temporal type: `relative_order`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: The visible speaking motion, the thigh slap, and the thumbs-up pose are all clearly visible and performed with the correct body parts.
- Gemini evidence: Visible mouth movement occurs around 00:00.5. The right hand slaps the right thigh at 00:03.542, and the right hand forms a thumbs-up pose at 00:04.708.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/no_tool_V_TP_Sp_Si_So_rel_ord_SpSiSo_v1.txt`

#### TP — Sp_Si_So_rel_ord_SoSiSp v1

- Human: `yes` / Gemini: `yes`
- Temporal type: `relative_order`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: The visible actions of the right hand slapping the right thigh, forming a thumbs-up, and the mouth moving to speak are correctly presented.
- Gemini evidence: The right hand visually strikes the right thigh at 00:01.000 and 00:01.375, a thumbs-up is formed at 00:02.000, and mouth motion is visible at 00:03.000.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/no_tool_V_TP_Sp_Si_So_rel_ord_SoSiSp_v1.txt`

#### TP — Si_So_rel_sync_cnt v1

- Human: `yes` / Gemini: `yes`
- Temporal type: `relative_sync_count`
- Modality: `Action (silent) + Action (sounding)`
- Gemini reason: The right hand forms a clear thumbs-up pose and visibly strikes the right thigh.
- Gemini evidence: Visible hand-to-thigh impacts occur with a thumbs-up pose.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/no_tool_V_TP_Si_So_rel_sync_cnt_v1.txt`

#### TN — Sp_Si_So_rel_ord_SpSoSi v1

- Human: `no` / Gemini: `no`
- Temporal type: `relative_order`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: The prompt requires the right hand for both the slap and the thumbs-up, but the person uses their left hand.
- Gemini evidence: The person's right hand (viewer's left) remains on the knee throughout. The person's left hand (viewer's right) performs the slap at 00:02.375 and the thumbs-up at 00:02.667.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/no_tool_V_TN_Sp_Si_So_rel_ord_SpSoSi_v1.txt`

#### TN — Sp_Si_rel_sync_cnt v1

- Human: `no` / Gemini: `no`
- Temporal type: `relative_sync_count`
- Modality: `Speech + Action (silent)`
- Gemini reason: The person performs the thumbs-up gesture with their left hand instead of the required right hand, and there is no visible mouth movement corresponding to the word 'help'.
- Gemini evidence: From 00:00.125 to 00:01.000, the subject's left hand (viewer's right) forms a thumbs-up while the right hand (viewer's left) remains down. The mouth remains closed.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/no_tool_V_TN_Sp_Si_rel_sync_cnt_v1.txt`

#### TN — Sp_Si_So_rel_ord_SoSpSi v1

- Human: `no` / Gemini: `no`
- Temporal type: `relative_order`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: The thumbs-up pose and visible speaking motion are present, but the visible action of striking the thigh is not performed; the hand only returns to rest.
- Gemini evidence: The person visibly says 'help' and forms a thumbs-up pose later, but no striking action on the thigh is visible.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/no_tool_V_TN_Sp_Si_So_rel_ord_SoSpSi_v1.txt`

#### FP — Si_So_rel_ord_SiSo v1

- Human: `no` / Gemini: `yes`
- Temporal type: `relative_order`
- Modality: `Action (silent) + Action (sounding)`
- Gemini reason: The required visible actions are correctly performed: the person's right hand forms a thumbs-up pose and subsequently strikes the right thigh.
- Gemini evidence: A thumbs-up with the right hand is visible from approximately 00:01.000 to 00:02.500, followed by the right hand moving down and making visible contact with the right thigh at 00:03.042.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/no_tool_V_FP_Si_So_rel_ord_SiSo_v1.txt`

#### FP — Sp_So_rel_sync_cnt v1

- Human: `no` / Gemini: `yes`
- Temporal type: `relative_sync_count`
- Modality: `Speech + Action (sounding)`
- Gemini reason: The required visible actions for speaking and thigh slapping are present and correctly executed.
- Gemini evidence: The person's mouth moves visibly at the start, and the right hand is seen striking the right thigh multiple times.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/no_tool_V_FP_Sp_So_rel_sync_cnt_v1.txt`

#### FP — Si_So_rel_ord_SoSi v1

- Human: `no` / Gemini: `yes`
- Temporal type: `relative_order`
- Modality: `Action (silent) + Action (sounding)`
- Gemini reason: The visible actions match the prompt: the right hand strikes the right thigh, followed by a clear right-hand thumbs-up pose.
- Gemini evidence: Video shows the right hand striking the thigh around 0.95s, returning to rest, and then forming a thumbs-up pose from 1.8s onwards.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/no_tool_V_FP_Si_So_rel_ord_SoSi_v1.txt`

#### FN — Sp_Si_So_rel_ord_SiSpSo v1

- Human: `yes` / Gemini: `no`
- Temporal type: `relative_order`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: The required visual speaking motion is completely absent. While the right-handed thumbs-up and the thigh slap are visibly performed, the person's mouth does not move when the speech occurs.
- Gemini evidence: At 0:00.000, when the word 'help' is heard, the person's mouth is fully closed and static. The thumbs-up pose is held from ~0:00.800 to 0:02.800, and the slap occurs at 0:03.000.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/no_tool_V_FN_Sp_Si_So_rel_ord_SiSpSo_v1.txt`

#### FN — Si_So_rel_sync v1

- Human: `yes` / Gemini: `no`
- Temporal type: `relative_synchronization`
- Modality: `Action (silent) + Action (sounding)`
- Gemini reason: The visible actions do not match the prompt's strict definition; the person performs a thumbs-up with a separate lifting motion in the air, then opens the hand to slap the thigh, rather than striking the thigh while maintaining the thumbs-up pose.
- Gemini evidence: The right hand raises into a thumbs-up (e.g., 00:00.292 - 00:00.458), then loses the pose as it comes down to slap the thigh (e.g., impact at 00:00.583).
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/no_tool_V_FN_Si_So_rel_sync_v1.txt`

#### FN — Sp_Si_So_rel_sync_cnt v1

- Human: `yes` / Gemini: `no`
- Temporal type: `relative_sync_count`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: The person forms a thumbs-up in the air rather than striking the top of the right thigh while holding the pose. The thigh-slapping motion is missing.
- Gemini evidence: Video shows the right hand lifting into a thumbs-up pose around 00:00.5 and 00:01.2, but the hand never makes visible contact with the right thigh to perform the required striking action.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/no_tool_V_FN_Sp_Si_So_rel_sync_cnt_v1.txt`

### AVB

#### TP — Si_So_rel_sync_cnt v1

- Human: `yes` / Gemini: `yes`
- Temporal type: `relative_sync_count`
- Modality: `Action (silent) + Action (sounding)`
- Gemini reason: The audible slap sounds temporally align with the first and fourth visible strikes.
- Gemini evidence: The sound at 0.3s aligns with the first visual strike, and the sound at 2.2s aligns with the final visual strike.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/no_tool_AVB_TP_Si_So_rel_sync_cnt_v1.txt`

#### TP — Sp_Si_So_rel_ord_SpSiSo v1

- Human: `yes` / Gemini: `yes`
- Temporal type: `relative_order`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: The audio and visual components of both the speech and the sounding action are temporally aligned.
- Gemini evidence: The spoken word 'help' aligns with the visible mouth motion, and the slap sound occurs exactly at the moment of visible impact on the thigh at 00:03.542.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/no_tool_AVB_TP_Sp_Si_So_rel_ord_SpSiSo_v1.txt`

#### TP — Sp_Si_So_rel_ord_SoSiSp v1

- Human: `yes` / Gemini: `yes`
- Temporal type: `relative_order`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: The audio and visual components for both the slaps and the speech are temporally aligned.
- Gemini evidence: The slap sounds align exactly with the visible hand-to-thigh contacts at 00:01.000 and 00:01.375. The speech audio 'help' syncs with the visible mouth movements at 00:03.000.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/no_tool_AVB_TP_Sp_Si_So_rel_ord_SoSiSp_v1.txt`

#### TN — Sp_So_rel_sync v1

- Human: `no` / Gemini: `no`
- Temporal type: `relative_synchronization`
- Modality: `Speech + Action (sounding)`
- Gemini reason: The visual component of the speech event is absent, failing the prerequisite for binding evaluation.
- Gemini evidence: The lack of visible lip motion makes it impossible to verify the binding between the spoken word and the visible speech action.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/no_tool_AVB_TN_Sp_So_rel_sync_v1.txt`

#### TN — Sp_Si_So_rel_sync v1

- Human: `no` / Gemini: `no`
- Temporal type: `relative_synchronization`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: The visual component for the speech event is missing, so audio-visual binding cannot be evaluated.
- Gemini evidence: The face is out of frame, preventing verification of lip synchronization.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/no_tool_AVB_TN_Sp_Si_So_rel_sync_v1.txt`

#### TN — Sp_Si_So_rel_ord_SpSoSi v1

- Human: `no` / Gemini: `no`
- Temporal type: `relative_order`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: The visual component is incorrect due to the wrong hand being used, so audio-visual binding fails the precondition and is not evaluable.
- Gemini evidence: Visual event correctness is 'no'.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/no_tool_AVB_TN_Sp_Si_So_rel_ord_SpSoSi_v1.txt`

#### FP — Sp_So_rel_sync_cnt v1

- Human: `no` / Gemini: `yes`
- Temporal type: `relative_sync_count`
- Modality: `Speech + Action (sounding)`
- Gemini reason: The audio and visual components for both events are correctly aligned with each other.
- Gemini evidence: The spoken word 'help' matches the visible mouth movement (0.0s-0.5s), and each slap sound precisely aligns with the hand's impact on the thigh (around 0.9s, 1.6s, 2.4s, and 3.3s).
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/no_tool_AVB_FP_Sp_So_rel_sync_cnt_v1.txt`

#### FP — Si_So_rel_ord_SiSo v1

- Human: `no` / Gemini: `yes`
- Temporal type: `relative_order`
- Modality: `Action (silent) + Action (sounding)`
- Gemini reason: The slap sound is correctly synchronized with the visible impact of the hand on the thigh.
- Gemini evidence: The audible slap and the visible contact of the right hand striking the right thigh both occur simultaneously at 00:03.042.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/no_tool_AVB_FP_Si_So_rel_ord_SiSo_v1.txt`

#### FP — Si_So_rel_ord_SoSi v1

- Human: `no` / Gemini: `yes`
- Temporal type: `relative_order`
- Modality: `Action (silent) + Action (sounding)`
- Gemini reason: The slap sound aligns perfectly with the visual impact of the hand on the thigh.
- Gemini evidence: The audible slap synchronizes with the visible hand-thigh contact around 0.95s-1.00s.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/no_tool_AVB_FP_Si_So_rel_ord_SoSi_v1.txt`

#### FN — Si_So_rel_sync v1

- Human: `yes` / Gemini: `no`
- Temporal type: `relative_synchronization`
- Modality: `Action (silent) + Action (sounding)`
- Gemini reason: The visual event is incorrect, so binding is not evaluable. Additionally, the audio and visual components are entirely out of sync.
- Gemini evidence: The slap sounds occur at 0.0s, 1.0s, and 3.0s when the hand is merely resting on the thigh, whereas the visible impacts occur later at approximately 0.583s, 1.542s, and 3.542s without corresponding audio.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/no_tool_AVB_FN_Si_So_rel_sync_v1.txt`

#### FN — Sp_Si_So_rel_ord_SiSpSo v1

- Human: `yes` / Gemini: `no`
- Temporal type: `relative_order`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: The visual component of the speech event is missing (no mouth motion), so audio-visual binding for the speech event fails.
- Gemini evidence: The spoken word 'help' at 0:00.000 has no corresponding visible lip movement to bind to.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/no_tool_AVB_FN_Sp_Si_So_rel_ord_SiSpSo_v1.txt`

#### FN — Sp_Si_So_rel_sync_cnt v1

- Human: `yes` / Gemini: `no`
- Temporal type: `relative_sync_count`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: Both the visual and audio components of the thigh slap are missing, making audio-visual binding not evaluable.
- Gemini evidence: The required thigh-slapping motion and its corresponding slap sound do not occur.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/no_tool_AVB_FN_Sp_Si_So_rel_sync_cnt_v1.txt`

### TC_REL

#### TP — Si_So_rel_sync_cnt v1

- Human: `yes` / Gemini: `yes`
- Temporal type: `relative_sync_count`
- Modality: `Action (silent) + Action (sounding)`
- Gemini reason: The required co-occurring audio and visual components are tightly synchronized during the two main events.
- Gemini evidence: Synchronization is present for the pairs at ~0.3s and ~2.2s.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/no_tool_TC_REL_TP_Si_So_rel_sync_cnt_v1.txt`

#### TP — Sp_So_rel_ord_SpSo v1

- Human: `yes` / Gemini: `yes`
- Temporal type: `relative_order`
- Modality: `Speech + Action (sounding)`
- Gemini reason: The required events occur in the correct relative order.
- Gemini evidence: The speech event completes before the right-hand slapping action begins.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/no_tool_TC_REL_TP_Sp_So_rel_ord_SpSo_v1.txt`

#### TP — Sp_Si_rel_ord_SiSp v1

- Human: `yes` / Gemini: `yes`
- Temporal type: `relative_order`
- Modality: `Speech + Action (silent)`
- Gemini reason: The events occur in the correct sequential order.
- Gemini evidence: The right-hand thumbs-up is formed and held at 00:01.000, and the speech event 'help' occurs afterward at 00:02.000.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/no_tool_TC_REL_TP_Sp_Si_rel_ord_SiSp_v1.txt`

#### TN — Sp_Si_So_rel_ord_SiSpSo v1

- Human: `no` / Gemini: `no`
- Temporal type: `relative_order`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: Fails hierarchical precondition due to the missing visual speech component. Additionally, the sequence is incorrect: the speech occurs before the thumbs-up, rather than after.
- Gemini evidence: Hierarchical failure. Furthermore, the audio 'help' happens at the very start (0:00.000), preceding the thumbs-up (0:00.800), violating the requested relative order.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/no_tool_TC_REL_TN_Sp_Si_So_rel_ord_SiSpSo_v1.txt`

#### TN — Si_So_rel_sync v1

- Human: `no` / Gemini: `no`
- Temporal type: `relative_synchronization`
- Modality: `Action (silent) + Action (sounding)`
- Gemini reason: Hierarchical preconditions failed (visual and binding failed). Furthermore, the thumbs-up and the thigh slap are performed sequentially rather than simultaneously.
- Gemini evidence: The video shows a thumbs-up gesture followed by a separate downward slapping motion, rather than one synchronized event.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/no_tool_TC_REL_TN_Si_So_rel_sync_v1.txt`

#### TN — Sp_Si_So_rel_sync v1

- Human: `no` / Gemini: `no`
- Temporal type: `relative_synchronization`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: Hierarchical preconditions failed because the visual event correctness and audio-visual binding failed. Furthermore, the events are sequential, not synchronized.
- Gemini evidence: Speech occurs near the beginning of the clip, while the visible hand slap occurs later around 0.45s.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/no_tool_TC_REL_TN_Sp_Si_So_rel_sync_v1.txt`

#### FP — Si_So_rel_ord_SiSo v1

- Human: `no` / Gemini: `yes`
- Temporal type: `relative_order`
- Modality: `Action (silent) + Action (sounding)`
- Gemini reason: The events occur in the correct relative order, with the silent action completed before the sounding action begins.
- Gemini evidence: The thumbs-up pose is held and completed by 00:02.500, and the thigh slap occurs afterward at 00:03.042.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/no_tool_TC_REL_FP_Si_So_rel_ord_SiSo_v1.txt`

#### FP — Si_So_rel_ord_SoSi v1

- Human: `no` / Gemini: `yes`
- Temporal type: `relative_order`
- Modality: `Action (silent) + Action (sounding)`
- Gemini reason: The sequential order of events is correct.
- Gemini evidence: The thigh slap completes before the thumbs-up pose is formed.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/no_tool_TC_REL_FP_Si_So_rel_ord_SoSi_v1.txt`

#### FN — Sp_Si_So_rel_ord_SiSoSp v1

- Human: `yes` / Gemini: `no`
- Temporal type: `relative_order`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: The required sequential order cannot be satisfied because the final speech event is missing.
- Gemini evidence: The sequence is broken as the person never says 'help' after the thumbs-up and thigh-slapping actions.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/no_tool_TC_REL_FN_Sp_Si_So_rel_ord_SiSoSp_v1.txt`

#### FN — Sp_Si_rel_ord_SpSi v1

- Human: `yes` / Gemini: `no`
- Temporal type: `relative_order`
- Modality: `Speech + Action (silent)`
- Gemini reason: Preconditions not met; visual event correctness and audio-visual binding failed.
- Gemini evidence: Temporal relation cannot be established without all individual events being visually correct and bound.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/no_tool_TC_REL_FN_Sp_Si_rel_ord_SpSi_v1.txt`

### TC_COUNT

#### TP — Sp_Si_rel_ord_SiSp v1

- Human: `yes` / Gemini: `yes`
- Temporal type: `relative_order`
- Modality: `Speech + Action (silent)`
- Gemini reason: Each target event occurs exactly once.
- Gemini evidence: The video contains one thumbs-up action and one spoken instance of 'help', with no extra repetitions.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/no_tool_TC_COUNT_TP_Sp_Si_rel_ord_SiSp_v1.txt`

#### TN — Si_So_rel_sync_cnt v1

- Human: `no` / Gemini: `no`
- Temporal type: `relative_sync_count`
- Modality: `Action (silent) + Action (sounding)`
- Gemini reason: The right hand visually strikes the thigh four times in total instead of the required exactly two times.
- Gemini evidence: Visible strikes occur at approximately 0.25s, 0.50s, 0.83s, and 2.20s, with the middle two lacking corresponding audio, failing the exact count constraint.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/no_tool_TC_COUNT_TN_Si_So_rel_sync_cnt_v1.txt`

#### TN — Sp_Si_So_rel_sync_cnt v1

- Human: `no` / Gemini: `no`
- Temporal type: `relative_sync_count`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: Preconditions failed; the correct synchronized bundle never occurs, so the required count of 2 is not met.
- Gemini evidence: The correct synchronized bundle of speech, thumbs-up, and thigh slap does not appear.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/no_tool_TC_COUNT_TN_Sp_Si_So_rel_sync_cnt_v1.txt`

#### TN — Si_So_rel_sync v1

- Human: `no` / Gemini: `no`
- Temporal type: `relative_synchronization`
- Modality: `Action (silent) + Action (sounding)`
- Gemini reason: Hierarchical preconditions failed. Additionally, the required synchronized bundle does not occur exactly once as instructed.
- Gemini evidence: The sequential thumbs-up and slap actions repeat three times throughout the video.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/no_tool_TC_COUNT_TN_Si_So_rel_sync_v1.txt`

#### FP — Si_So_rel_ord_SiSo v1

- Human: `no` / Gemini: `yes`
- Temporal type: `relative_order`
- Modality: `Action (silent) + Action (sounding)`
- Gemini reason: Both the thumbs-up action and the thigh slap occur exactly once, matching the prompt's structural requirement.
- Gemini evidence: There is only one thumbs-up gesture and one single thigh slap observed and heard in the video, with no extra occurrences.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/no_tool_TC_COUNT_FP_Si_So_rel_ord_SiSo_v1.txt`

#### FP — Sp_Si_So_rel_ord_SpSiSo v1

- Human: `no` / Gemini: `yes`
- Temporal type: `relative_order`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: Each of the three required events occurs exactly once.
- Gemini evidence: The speech, the slap, and the thumbs-up each happen only one time, with no spurious repetitions.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/no_tool_TC_COUNT_FP_Sp_Si_So_rel_ord_SpSiSo_v1.txt`

#### FP — Si_So_rel_ord_SoSi v1

- Human: `no` / Gemini: `yes`
- Temporal type: `relative_order`
- Modality: `Action (silent) + Action (sounding)`
- Gemini reason: Each required action occurs exactly once with no spurious repetitions.
- Gemini evidence: One visible thigh slap is followed by one continuous thumbs-up pose.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/no_tool_TC_COUNT_FP_Si_So_rel_ord_SoSi_v1.txt`

#### FN — Sp_Si_So_rel_ord_SiSpSo v1

- Human: `yes` / Gemini: `no`
- Temporal type: `relative_order`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: Fails hierarchical precondition because the visual speech component is incorrect.
- Gemini evidence: Hierarchical failure.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/no_tool_TC_COUNT_FN_Sp_Si_So_rel_ord_SiSpSo_v1.txt`

#### FN — Sp_Si_rel_sync v1

- Human: `yes` / Gemini: `no`
- Temporal type: `relative_synchronization`
- Modality: `Speech + Action (silent)`
- Gemini reason: The required synchronized bundle does not occur.
- Gemini evidence: Because the events occur sequentially rather than simultaneously, the specified synchronized occurrence count of exactly once is not met.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/no_tool_TC_COUNT_FN_Sp_Si_rel_sync_v1.txt`

#### FN — Sp_Si_rel_ord_SpSi v1

- Human: `yes` / Gemini: `no`
- Temporal type: `relative_order`
- Modality: `Speech + Action (silent)`
- Gemini reason: Preconditions not met; visual event correctness and audio-visual binding failed.
- Gemini evidence: Event counts cannot be verified due to missing visual components.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/no_tool_TC_COUNT_FN_Sp_Si_rel_ord_SpSi_v1.txt`

### CC

#### TP — Sp_Si_So_rel_ord_SiSpSo v1

- Human: `yes` / Gemini: `yes`
- Temporal type: `relative_order`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: The video adheres to the scene and camera constraints, and no extraneous actions or sounds occur. The person becomes still after the final event.
- Gemini evidence: The shot is a static medium shot in a plain indoor room, and the actor remains still after the thigh slap without adding extra speech or movements.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/no_tool_CC_TP_Sp_Si_So_rel_ord_SiSpSo_v1.txt`

#### TP — Sp_Si_So_rel_ord_SpSoSi v1

- Human: `yes` / Gemini: `yes`
- Temporal type: `relative_order`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: Non-core constraints such as the static medium shot, plain room, and absence of extra speech or actions are satisfied.
- Gemini evidence: The video maintains a static shot in a plain room, with no additional unprompted actions or words occurring after the final event.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/no_tool_CC_TP_Sp_Si_So_rel_ord_SpSoSi_v1.txt`

#### TP — Sp_Si_So_rel_ord_SpSiSo v1

- Human: `yes` / Gemini: `yes`
- Temporal type: `relative_order`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: The video complies with the scene, camera, and starting pose constraints, and contains no extra unprompted actions, speech, or background music.
- Gemini evidence: The scene is a plain indoor room, the camera is a static medium shot, the person starts with hands on thighs, and no extraneous sounds or actions occur.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/no_tool_CC_TP_Sp_Si_So_rel_ord_SpSiSo_v1.txt`

#### TN — Sp_Si_So_rel_sync_cnt v1

- Human: `no` / Gemini: `no`
- Temporal type: `relative_sync_count`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: The person performs an additional unprompted right-hand gesture after the second 'help', violating the post-event stillness constraint.
- Gemini evidence: From 00:01.7 to 00:02.2, the person lifts their right hand again in an open-palm gesture.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/no_tool_CC_TN_Sp_Si_So_rel_sync_cnt_v1.txt`

#### TN — Sp_Si_So_rel_ord_SoSpSi v1

- Human: `no` / Gemini: `no`
- Temporal type: `relative_order`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: The person's right hand is already in motion at the start of the video instead of initially resting on the thigh, and an unprompted hand gesture occurs during the speech.
- Gemini evidence: At 0.00s, the right hand is already moving upward to gesture while speaking.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/no_tool_CC_TN_Sp_Si_So_rel_ord_SoSpSi_v1.txt`

#### TN — Sp_Si_So_rel_sync v1

- Human: `no` / Gemini: `no`
- Temporal type: `relative_synchronization`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: The prompt explicitly requires the full face and mouth to be clearly visible, but the shot is framed from the neck down.
- Gemini evidence: The head is not visible in any frame of the video.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/no_tool_CC_TN_Sp_Si_So_rel_sync_v1.txt`

#### FP — Si_So_rel_sync_cnt v1

- Human: `no` / Gemini: `yes`
- Temporal type: `relative_sync_count`
- Modality: `Action (silent) + Action (sounding)`
- Gemini reason: Scene, camera, starting pose, and post-event stillness constraints are fully met.
- Gemini evidence: The video maintains a static medium shot in a plain room, hands start resting, and the person stays still from 2.5s to 5.0s.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/no_tool_CC_FP_Si_So_rel_sync_cnt_v1.txt`

#### FP — Sp_Si_rel_sync v1

- Human: `no` / Gemini: `yes`
- Temporal type: `relative_synchronization`
- Modality: `Speech + Action (silent)`
- Gemini reason: The non-core constraints are met.
- Gemini evidence: The person is seated in a plain indoor room, the camera is a static medium shot, no extra words are spoken, and no extra actions occur.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/no_tool_CC_FP_Sp_Si_rel_sync_v1.txt`

#### FN — Si_So_rel_ord_SiSo v1

- Human: `yes` / Gemini: `no`
- Temporal type: `relative_order`
- Modality: `Action (silent) + Action (sounding)`
- Gemini reason: The prompt explicitly requires the full face and mouth to be visible, but the video framing crops them out entirely.
- Gemini evidence: Throughout the entire video, the person's head and face are outside the camera frame, violating the static medium shot requirement that specified full face visibility.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/no_tool_CC_FN_Si_So_rel_ord_SiSo_v1.txt`

#### FN — Si_So_rel_sync v1

- Human: `yes` / Gemini: `no`
- Temporal type: `relative_synchronization`
- Modality: `Action (silent) + Action (sounding)`
- Gemini reason: The video violates the post-event stillness constraint and the instruction against a separate lifting motion.
- Gemini evidence: The actor repeats the sequence three times instead of remaining still after the first occurrence, and the thumbs-up involves a distinct upward arm movement.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/no_tool_CC_FN_Si_So_rel_sync_v1.txt`

#### FN — Sp_So_rel_sync_cnt v1

- Human: `yes` / Gemini: `no`
- Temporal type: `relative_sync_count`
- Modality: `Speech + Action (sounding)`
- Gemini reason: The video contains extra actions and sounds, violating the prompt's strict constraints.
- Gemini evidence: The person performs four thigh slaps instead of the requested two, violating the 'no extra slap sounds' and 'no new target action' constraints.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/no_tool_CC_FN_Sp_So_rel_sync_cnt_v1.txt`

## mediapipe

### A

#### TP — Sp_Si_So_rel_sync_cnt v1

- Human: `yes` / Gemini: `yes`
- Temporal type: `relative_sync_count`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: The spoken word 'help' is clearly audible and intelligible, and a sharp slap sound is clearly heard, matching the prompt requirements.
- Gemini evidence: The word 'help' is heard clearly around 00:00.500 and 00:01.100. Simultaneous sharp slap sounds are also heard at these times.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/mediapipe_A_TP_Sp_Si_So_rel_sync_cnt_v1.txt`

#### TP — Sp_Si_So_rel_ord_SpSoSi v1

- Human: `yes` / Gemini: `yes`
- Temporal type: `relative_order`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: The required speech and the non-speech sound are both present and clearly audible.
- Gemini evidence: The spoken word 'help' is heard at the beginning of the video, and a distinct, sharp slap sound is heard around 2.2-2.3 seconds.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/mediapipe_A_TP_Sp_Si_So_rel_ord_SpSoSi_v1.txt`

#### TP — Sp_Si_rel_ord_SpSi v1

- Human: `yes` / Gemini: `yes`
- Temporal type: `relative_order`
- Modality: `Speech + Action (silent)`
- Gemini reason: The required speech event, saying the word 'help', is clearly audible and distinguishable in the audio track.
- Gemini evidence: Audio contains the clear spoken word 'help' starting around 0.0 seconds.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/mediapipe_A_TP_Sp_Si_rel_ord_SpSi_v1.txt`

#### TN — Sp_So_rel_ord_SoSp v1

- Human: `no` / Gemini: `no`
- Temporal type: `relative_order`
- Modality: `Speech + Action (sounding)`
- Gemini reason: The audio contains the slap sound, but the required speech ('help') is missing entirely.
- Gemini evidence: A slap sound is heard around 00:01.000, followed by silence. No spoken words are present in the audio track.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/mediapipe_A_TN_Sp_So_rel_ord_SoSp_v1.txt`

#### TN — Sp_So_rel_sync v1

- Human: `no` / Gemini: `no`
- Temporal type: `relative_synchronization`
- Modality: `Speech + Action (sounding)`
- Gemini reason: The required speech event 'help' is missing from the audio track.
- Gemini evidence: While a slap sound is audible around 1.38s, there is no spoken word 'help' heard at any point in the video.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/mediapipe_A_TN_Sp_So_rel_sync_v1.txt`

#### FN — Sp_Si_So_rel_sync v1

- Human: `yes` / Gemini: `no`
- Temporal type: `relative_synchronization`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: The required speech 'help' is completely missing from the audio track.
- Gemini evidence: No spoken words are audible in the video; only a slap sound is heard at approximately 0.5 seconds.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/mediapipe_A_FN_Sp_Si_So_rel_sync_v1.txt`

#### FN — Sp_Si_rel_sync_cnt v1

- Human: `yes` / Gemini: `no`
- Temporal type: `relative_sync_count`
- Modality: `Speech + Action (silent)`
- Gemini reason: The required speech event 'help' is not present in the audio.
- Gemini evidence: Throughout the video, only faint breath sounds or sighs are heard; the word 'help' is never spoken.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/mediapipe_A_FN_Sp_Si_rel_sync_cnt_v1.txt`

#### FN — Sp_Si_So_rel_ord_SpSiSo v1

- Human: `yes` / Gemini: `no`
- Temporal type: `relative_order`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: Audio evidence is missing, so speech and slap sounds cannot be verified.
- Gemini evidence: No Whisper or CLAP tool outputs provided.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/mediapipe_A_FN_Sp_Si_So_rel_ord_SpSiSo_v1.txt`

### V

#### TP — Sp_Si_So_rel_sync_cnt v1

- Human: `yes` / Gemini: `yes`
- Temporal type: `relative_sync_count`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: The person visibly moves their mouth to say the required word, the right hand forms a clear thumbs-up pose, and the right hand visibly strikes the right thigh.
- Gemini evidence: Visible lip movement occurs around 00:00.500 and 00:01.100. Concurrently, the right hand forms a fist with the thumb extended upward and strikes the right thigh at 00:00.542 and 00:01.125.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/mediapipe_V_TP_Sp_Si_So_rel_sync_cnt_v1.txt`

#### TP — Sp_Si_rel_ord_SpSi v1

- Human: `yes` / Gemini: `yes`
- Temporal type: `relative_order`
- Modality: `Speech + Action (silent)`
- Gemini reason: The person visibly speaks and then correctly performs a right-hand thumbs-up gesture with a closed fist and thumb extended upward.
- Gemini evidence: Visible mouth movements match speaking at the beginning of the video, followed by the right hand forming and holding a clear thumbs-up pose from approximately 0.75 seconds to the end of the video.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/mediapipe_V_TP_Sp_Si_rel_ord_SpSi_v1.txt`

#### TP — Sp_Si_So_rel_ord_SoSiSp v1

- Human: `yes` / Gemini: `yes`
- Temporal type: `relative_order`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: The video shows the person slapping their right thigh with their right hand, forming a right-hand thumbs-up pose, and visibly speaking the word 'help'.
- Gemini evidence: Right hand raises and strikes right thigh at 00:00.958. Right hand forms a clear thumbs-up pose at 00:02.000. Mouth moves to say 'help' starting at 00:02.958.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/mediapipe_V_TP_Sp_Si_So_rel_ord_SoSiSp_v1.txt`

#### TN — Sp_Si_rel_sync_cnt v1

- Human: `no` / Gemini: `no`
- Temporal type: `relative_sync_count`
- Modality: `Speech + Action (silent)`
- Gemini reason: The person performs the thumbs-up gesture with the incorrect hand.
- Gemini evidence: The video shows the person raising their left hand (viewer's right) to form a thumbs-up at 00:00.125 and again at 00:02.417. The prompt explicitly required the right hand to perform the action, but the right hand remains resting on the thigh.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/mediapipe_V_TN_Sp_Si_rel_sync_cnt_v1.txt`

#### TN — Sp_Si_So_rel_sync v1

- Human: `no` / Gemini: `no`
- Temporal type: `relative_synchronization`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: The person does not visibly speak, and the thumbs-up pose is not maintained while striking the thigh.
- Gemini evidence: There is no visible mouth movement for the word 'help'. The right hand forms a thumbs-up around 0.25s but the fingers open up before the hand strikes the thigh at 0.5s.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/mediapipe_V_TN_Sp_Si_So_rel_sync_v1.txt`

#### TN — Sp_So_rel_ord_SoSp v1

- Human: `no` / Gemini: `no`
- Temporal type: `relative_order`
- Modality: `Speech + Action (sounding)`
- Gemini reason: The person visibly slaps his right thigh, but the required visible speaking motion for the word 'help' does not occur.
- Gemini evidence: The person's right hand swings out and slaps his right thigh at 00:01.000. Afterward, his mouth remains closed for the rest of the video.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/mediapipe_V_TN_Sp_So_rel_ord_SoSp_v1.txt`

#### FP — Sp_Si_So_rel_ord_SpSoSi v1

- Human: `no` / Gemini: `yes`
- Temporal type: `relative_order`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: All required visual actions and speaking motions are present and correctly performed.
- Gemini evidence: The person's mouth moves at the beginning of the video; the right hand visibly strikes the right thigh around 00:02.292; and the right hand then forms a clear thumbs-up pose by 00:02.500, holding it until the end.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/mediapipe_V_FP_Sp_Si_So_rel_ord_SpSoSi_v1.txt`

#### FP — Sp_Si_So_rel_ord_SoSpSi v1

- Human: `no` / Gemini: `yes`
- Temporal type: `relative_order`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: The visible speaking motion, the right hand striking the right thigh, and the right hand forming and holding a clear thumbs-up pose are all clearly visible and correctly performed.
- Gemini evidence: The person's mouth moves at the start of the video, the right hand visibly strikes the thigh around 00:00.417, and then the right hand forms a thumbs-up pose at 00:01.750 and holds it until the end of the video.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/mediapipe_V_FP_Sp_Si_So_rel_ord_SoSpSi_v1.txt`

#### FP — Si_So_rel_ord_SoSi v1

- Human: `no` / Gemini: `yes`
- Temporal type: `relative_order`
- Modality: `Action (silent) + Action (sounding)`
- Gemini reason: The right hand visibly strikes the right thigh, and subsequently forms a clear thumbs-up pose.
- Gemini evidence: Visible contact is made between the right hand and right thigh at 00:01.000. A clear right-hand thumbs-up pose is formed at 00:01.958 and held.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/mediapipe_V_FP_Si_So_rel_ord_SoSi_v1.txt`

#### FN — Si_So_rel_sync v1

- Human: `yes` / Gemini: `no`
- Temporal type: `relative_synchronization`
- Modality: `Action (silent) + Action (sounding)`
- Gemini reason: The prompt specifies that the thumbs-up should be the pose held while striking the thigh, without a separate upward lifting motion. The video shows the person performing a separate upward motion to form a thumbs-up in the air, and then striking the thigh with an open hand.
- Gemini evidence: The right hand is raised into a thumbs-up in the air at 00:00.292, 00:01.292, and 00:03.250. When the hand strikes the thigh at 00:00.542, 00:01.542, and 00:03.542, it is open rather than in the required thumbs-up pose.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/mediapipe_V_FN_Si_So_rel_sync_v1.txt`

#### FN — Sp_So_rel_sync v1

- Human: `yes` / Gemini: `no`
- Temporal type: `relative_synchronization`
- Modality: `Speech + Action (sounding)`
- Gemini reason: The visible speaking motion for the word 'help' is absent.
- Gemini evidence: The video shows the right hand slapping the right thigh, but the person's mouth remains completely closed and static throughout the entire video.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/mediapipe_V_FN_Sp_So_rel_sync_v1.txt`

### AVB

#### TP — Sp_Si_So_rel_sync_cnt v1

- Human: `yes` / Gemini: `yes`
- Temporal type: `relative_sync_count`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: The audio and visual components of the events are correctly bound. The spoken audio aligns with the visible lip movements, and the slap sounds perfectly align with the visible impacts on the thigh.
- Gemini evidence: The spoken 'help' matches the lip movements starting at 00:00.500 and 00:01.100. The slap sounds coincide exactly with the visible right hand strikes on the thigh at 00:00.542 and 00:01.125.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/mediapipe_AVB_TP_Sp_Si_So_rel_sync_cnt_v1.txt`

#### TP — Sp_So_rel_ord_SpSo v1

- Human: `yes` / Gemini: `yes`
- Temporal type: `relative_order`
- Modality: `Speech + Action (sounding)`
- Gemini reason: Both events are correctly synchronized. The spoken audio aligns with the visible mouth movements, and the slap sound aligns precisely with the hand's impact on the thigh.
- Gemini evidence: The speech and lip motion align seamlessly at the beginning of the video. The right hand visibly strikes the thigh exactly as the slap sound is heard at 00:04.042-00:04.083.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/mediapipe_AVB_TP_Sp_So_rel_ord_SpSo_v1.txt`

#### TP — Sp_Si_rel_ord_SpSi v1

- Human: `yes` / Gemini: `yes`
- Temporal type: `relative_order`
- Modality: `Speech + Action (silent)`
- Gemini reason: The spoken word 'help' is correctly synchronized with the corresponding visible lip and mouth movements.
- Gemini evidence: The audible word 'help' from 0.0s to 0.4s aligns perfectly with the visible opening and articulation of the person's mouth.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/mediapipe_AVB_TP_Sp_Si_rel_ord_SpSi_v1.txt`

#### TN — Sp_So_rel_ord_SoSp v1

- Human: `no` / Gemini: `no`
- Temporal type: `relative_order`
- Modality: `Speech + Action (sounding)`
- Gemini reason: Audio-Visual Binding is not evaluable for the speech event because both the audio and visual components are missing.
- Gemini evidence: While the slap sound aligns with the visible thigh impact at 00:01.000, the absence of the 'help' speech in both modalities forces a failure for binding.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/mediapipe_AVB_TN_Sp_So_rel_ord_SoSp_v1.txt`

#### TN — Sp_Si_rel_sync_cnt v1

- Human: `no` / Gemini: `no`
- Temporal type: `relative_sync_count`
- Modality: `Speech + Action (silent)`
- Gemini reason: Both the required audio speech component and the visual action component are incorrect or missing, so binding is not evaluable.
- Gemini evidence: The audio lacks the word 'help', and the visual action is performed with the left hand instead of the right.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/mediapipe_AVB_TN_Sp_Si_rel_sync_cnt_v1.txt`

#### TN — Sp_So_rel_sync v1

- Human: `no` / Gemini: `no`
- Temporal type: `relative_synchronization`
- Modality: `Speech + Action (sounding)`
- Gemini reason: The required audio and visual components for the speech event are missing, so binding cannot be evaluated.
- Gemini evidence: Neither the audio for the word 'help' nor the corresponding visible mouth motion is present.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/mediapipe_AVB_TN_Sp_So_rel_sync_v1.txt`

#### FP — Sp_Si_So_rel_ord_SpSoSi v1

- Human: `no` / Gemini: `yes`
- Temporal type: `relative_order`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: The audio and visual components for both the speech and the slapping action are correctly aligned and synchronized.
- Gemini evidence: The visible mouth motion perfectly aligns with the spoken word 'help' at the start, and the audible slap sound occurs exactly at the moment the right hand visually strikes the thigh around 00:02.292.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/mediapipe_AVB_FP_Sp_Si_So_rel_ord_SpSoSi_v1.txt`

#### FP — Sp_So_rel_sync_cnt v1

- Human: `no` / Gemini: `yes`
- Temporal type: `relative_sync_count`
- Modality: `Speech + Action (sounding)`
- Gemini reason: The audio components perfectly align with their corresponding visual motions within each event.
- Gemini evidence: Speech and slap audio coincide exactly with the visible lip motion and hand-to-thigh impact at 1.0s, 3.0s, and 5.0s.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/mediapipe_AVB_FP_Sp_So_rel_sync_cnt_v1.txt`

#### FP — Si_So_rel_ord_SoSi v1

- Human: `no` / Gemini: `yes`
- Temporal type: `relative_order`
- Modality: `Action (silent) + Action (sounding)`
- Gemini reason: The slap sound is perfectly synchronized with the visible impact of the hand on the thigh.
- Gemini evidence: The slap sound and the visible strike both occur exactly at 00:01.000.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/mediapipe_AVB_FP_Si_So_rel_ord_SoSi_v1.txt`

#### FN — Si_So_rel_sync v1

- Human: `yes` / Gemini: `no`
- Temporal type: `relative_synchronization`
- Modality: `Action (silent) + Action (sounding)`
- Gemini reason: The visual component of the event is incorrect, so audio-visual binding is not evaluable and fails by hierarchical dependency.
- Gemini evidence: Although the open-hand slaps are synchronized with the slap sounds, the required visual action (striking the thigh while maintaining a thumbs-up pose) is missing.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/mediapipe_AVB_FN_Si_So_rel_sync_v1.txt`

#### FN — Sp_Si_So_rel_ord_SpSiSo v1

- Human: `yes` / Gemini: `no`
- Temporal type: `relative_order`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: Audio component is unverified, so binding is not evaluable.
- Gemini evidence: Audio event correctness is marked no.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/mediapipe_AVB_FN_Sp_Si_So_rel_ord_SpSiSo_v1.txt`

### TC_REL

#### TP — Sp_Si_rel_ord_SpSi v1

- Human: `yes` / Gemini: `yes`
- Temporal type: `relative_order`
- Modality: `Speech + Action (silent)`
- Gemini reason: The events occur in the correct relative sequence: the speech event completely finishes before the thumbs-up gesture begins.
- Gemini evidence: The speech 'help' concludes around 0.4s. The person's right hand then initiates the thumbs-up motion around 0.7s and completes the pose by 0.8s, strictly following the required order.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/mediapipe_TC_REL_TP_Sp_Si_rel_ord_SpSi_v1.txt`

#### TP — Sp_So_rel_ord_SpSo v1

- Human: `yes` / Gemini: `yes`
- Temporal type: `relative_order`
- Modality: `Speech + Action (sounding)`
- Gemini reason: The events occur in the correct relative order, with the speech ending completely before the sounding slap action takes place.
- Gemini evidence: The speech event concludes by 00:00.500. The person then pauses before the sounding slap event occurs at 00:04.083, satisfying the sequential order.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/mediapipe_TC_REL_TP_Sp_So_rel_ord_SpSo_v1.txt`

#### TP — Sp_Si_So_rel_ord_SoSiSp v1

- Human: `yes` / Gemini: `yes`
- Temporal type: `relative_order`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: The events occur in the correct relative sequence: slap, then thumbs-up, then speech.
- Gemini evidence: Slap at 00:01.000, followed by thumbs-up at 00:02.000, followed by speech at 00:03.000.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/mediapipe_TC_REL_TP_Sp_Si_So_rel_ord_SoSiSp_v1.txt`

#### TN — Si_So_rel_sync v1

- Human: `no` / Gemini: `no`
- Temporal type: `relative_synchronization`
- Modality: `Action (silent) + Action (sounding)`
- Gemini reason: The required visual event is incorrect and audio-visual binding failed, so the temporal relation precondition is not met. Furthermore, the thumbs-up and the slap are performed sequentially rather than simultaneously.
- Gemini evidence: Visual event correctness failed. The video shows the thumbs-up pose occurring in the air before the hand opens and moves down to slap the thigh, violating the simultaneous synchronization requirement.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/mediapipe_TC_REL_TN_Si_So_rel_sync_v1.txt`

#### TN — Sp_Si_So_rel_ord_SoSpSi v1

- Human: `no` / Gemini: `no`
- Temporal type: `relative_order`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: The required sequence of events is incorrect. The prompt requires the thigh slap to occur first, followed by the speech. However, the video shows the speech occurring before the thigh slap.
- Gemini evidence: The person says 'help' between 00:00.000 and 00:00.167, and only strikes the thigh afterward around 00:00.417. The thumbs-up follows correctly, but the initial order is reversed.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/mediapipe_TC_REL_TN_Sp_Si_So_rel_ord_SoSpSi_v1.txt`

#### TN — Sp_Si_So_rel_ord_SiSpSo v1

- Human: `no` / Gemini: `no`
- Temporal type: `relative_order`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: The required order of events is violated. The speech occurs before the thumbs-up, rather than after it as specified.
- Gemini evidence: The person says 'help' at the very beginning (0.0s), before forming the thumbs-up pose (0.6s). The sequence should have been thumbs-up, then 'help', then slap.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/mediapipe_TC_REL_TN_Sp_Si_So_rel_ord_SiSpSo_v1.txt`

#### FP — Sp_Si_So_rel_sync_cnt v1

- Human: `no` / Gemini: `yes`
- Temporal type: `relative_sync_count`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: The prompt requires the speech, the silent visual action (thumbs-up), and the sounding action (slap) to be tightly synchronized, which is successfully achieved.
- Gemini evidence: For both occurrences, the speech, the formation of the thumbs-up pose, and the strike on the thigh happen simultaneously at roughly 00:00.500 and 00:01.100.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/mediapipe_TC_REL_FP_Sp_Si_So_rel_sync_cnt_v1.txt`

#### FP — Sp_Si_So_rel_ord_SpSoSi v1

- Human: `no` / Gemini: `yes`
- Temporal type: `relative_order`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: The events occur in the exact relative order specified by the prompt.
- Gemini evidence: The sequence is strictly followed: first the speech event ends (by ~0.5s), then the right hand slaps the thigh (at ~2.3s), and finally the right hand forms the thumbs-up pose (~2.5s onwards).
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/mediapipe_TC_REL_FP_Sp_Si_So_rel_ord_SpSoSi_v1.txt`

#### FP — Si_So_rel_ord_SoSi v1

- Human: `no` / Gemini: `yes`
- Temporal type: `relative_order`
- Modality: `Action (silent) + Action (sounding)`
- Gemini reason: The sounding action is completed before the silent action begins, satisfying the relative order constraint.
- Gemini evidence: The slap occurs at 00:01.000, and the thumbs-up pose is formed later at 00:01.958.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/mediapipe_TC_REL_FP_Si_So_rel_ord_SoSi_v1.txt`

### TC_COUNT

#### TP — Sp_Si_rel_ord_SpSi v1

- Human: `yes` / Gemini: `yes`
- Temporal type: `relative_order`
- Modality: `Speech + Action (silent)`
- Gemini reason: Both the speech event and the visual action occur exactly once as required.
- Gemini evidence: The word 'help' is spoken exactly one time, and the right-hand thumbs-up is performed exactly once without any repeated or spurious actions.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/mediapipe_TC_COUNT_TP_Sp_Si_rel_ord_SpSi_v1.txt`

#### TP — Sp_Si_So_rel_ord_SiSpSo v1

- Human: `yes` / Gemini: `yes`
- Temporal type: `relative_order`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: Each of the three required events occurs exactly once without spurious repetitions.
- Gemini evidence: One instance of speech, one thumbs-up pose, and one thigh slap are observed.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/mediapipe_TC_COUNT_TP_Sp_Si_So_rel_ord_SiSpSo_v1.txt`

#### TP — Sp_Si_rel_ord_SiSp v1

- Human: `yes` / Gemini: `yes`
- Temporal type: `relative_order`
- Modality: `Speech + Action (silent)`
- Gemini reason: The target events occur exactly once as required.
- Gemini evidence: There is exactly one thumbs-up gesture and exactly one utterance of the word 'help', with no extra occurrences.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/mediapipe_TC_COUNT_TP_Sp_Si_rel_ord_SiSp_v1.txt`

#### TN — Sp_So_rel_ord_SpSo v1

- Human: `no` / Gemini: `no`
- Temporal type: `relative_order`
- Modality: `Speech + Action (sounding)`
- Gemini reason: The person performs an extra, spurious slapping motion before the main sounding slap, violating the requirement to perform the action exactly once.
- Gemini evidence: At 00:03.417, the person lifts both hands and brings them down on the thighs in a soundless slapping motion. The intended right-hand slap occurs later at 00:04.083, resulting in multiple slap actions.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/mediapipe_TC_COUNT_TN_Sp_So_rel_ord_SpSo_v1.txt`

#### TN — Si_So_rel_sync v1

- Human: `no` / Gemini: `no`
- Temporal type: `relative_synchronization`
- Modality: `Action (silent) + Action (sounding)`
- Gemini reason: The preconditions for temporal evaluation failed. Additionally, the prompt requires the event to occur exactly once, but the video repeats the action sequence multiple times.
- Gemini evidence: The required event components are incorrect. The sequential lifting and slapping actions occur three times throughout the video.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/mediapipe_TC_COUNT_TN_Si_So_rel_sync_v1.txt`

#### TN — Sp_So_rel_sync v1

- Human: `no` / Gemini: `no`
- Temporal type: `relative_synchronization`
- Modality: `Speech + Action (sounding)`
- Gemini reason: Preconditions failed; the required synchronized bundle is incomplete.
- Gemini evidence: The required synchronized occurrence of the speech and sounding action does not happen because the speech event is missing.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/mediapipe_TC_COUNT_TN_Sp_So_rel_sync_v1.txt`

#### FP — Sp_Si_So_rel_sync_cnt v1

- Human: `no` / Gemini: `yes`
- Temporal type: `relative_sync_count`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: The synchronized bundle of the three target events occurs exactly twice, as required, with no extra or spurious occurrences of the target actions.
- Gemini evidence: The first synchronized bundle occurs at 00:00.500-00:00.600, followed by a brief reset, and the second bundle occurs at 00:01.100-00:01.200. No further target events occur after the second repetition.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/mediapipe_TC_COUNT_FP_Sp_Si_So_rel_sync_cnt_v1.txt`

#### FP — Sp_Si_So_rel_ord_SpSoSi v1

- Human: `no` / Gemini: `yes`
- Temporal type: `relative_order`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: Each required event occurs exactly once with no spurious or repeated actions.
- Gemini evidence: The word 'help' is spoken exactly once, a single thigh slap is performed, and one thumbs-up is formed and held. There are no extra words, slaps, or gestures.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/mediapipe_TC_COUNT_FP_Sp_Si_So_rel_ord_SpSoSi_v1.txt`

#### FP — Si_So_rel_ord_SoSi v1

- Human: `no` / Gemini: `yes`
- Temporal type: `relative_order`
- Modality: `Action (silent) + Action (sounding)`
- Gemini reason: Both the slap and the thumbs-up pose occur exactly once as required.
- Gemini evidence: There is only one slap event and one transition into the final thumbs-up pose.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/mediapipe_TC_COUNT_FP_Si_So_rel_ord_SoSi_v1.txt`

#### FN — Sp_Si_rel_sync v1

- Human: `yes` / Gemini: `no`
- Temporal type: `relative_synchronization`
- Modality: `Speech + Action (silent)`
- Gemini reason: The required synchronized bundle of speaking and gesturing does not occur.
- Gemini evidence: Because the speech and the hand pose are temporally disconnected, the requested simultaneous bundle occurs zero times.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/mediapipe_TC_COUNT_FN_Sp_Si_rel_sync_v1.txt`

### CC

#### TP — Si_So_rel_ord_SoSi v1

- Human: `yes` / Gemini: `yes`
- Temporal type: `relative_order`
- Modality: `Action (silent) + Action (sounding)`
- Gemini reason: The scene is a plain indoor room in a static medium shot, the person starts in the correct seated position, and holds still without new target actions after the final event.
- Gemini evidence: The video maintains a static medium shot of a seated person in a plain room. After forming the thumbs-up at 00:01.958, the person holds the pose until the video ends without performing any other actions.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/mediapipe_CC_TP_Si_So_rel_ord_SoSi_v1.txt`

#### TP — Sp_Si_So_rel_ord_SpSoSi v1

- Human: `yes` / Gemini: `yes`
- Temporal type: `relative_order`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: The video follows all non-core prompt constraints, including scene, camera, initial pose, and post-event stillness.
- Gemini evidence: The video is a static medium shot in a plain indoor room; the seated person begins with both hands resting on the thighs; and after the thumbs-up is formed, the person holds the pose and remains still until the end.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/mediapipe_CC_TP_Sp_Si_So_rel_ord_SpSoSi_v1.txt`

#### TP — Sp_Si_So_rel_ord_SoSiSp v1

- Human: `yes` / Gemini: `yes`
- Temporal type: `relative_order`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: The video satisfies all scene, camera, and specific action constraints.
- Gemini evidence: The scene is a plain indoor room with a static medium shot. The person starts with hands on thighs. No extra words or sounds are produced. The person remains mostly still after the final speech event.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/mediapipe_CC_TP_Sp_Si_So_rel_ord_SoSiSp_v1.txt`

#### TN — Sp_Si_rel_sync v1

- Human: `no` / Gemini: `no`
- Temporal type: `relative_synchronization`
- Modality: `Speech + Action (silent)`
- Gemini reason: The video includes a distinct hand-raising motion to form the thumbs-up, which violates the negative constraint.
- Gemini evidence: The right hand is visibly lifted from the thigh to the chest level starting at 3.250 to form the pose, contradicting the prompt's instruction that it should be a pose rather than a separate hand-raising motion.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/mediapipe_CC_TN_Sp_Si_rel_sync_v1.txt`

#### TN — Sp_So_rel_sync v1

- Human: `no` / Gemini: `no`
- Temporal type: `relative_synchronization`
- Modality: `Speech + Action (sounding)`
- Gemini reason: The prompt requires the person's full face to remain clearly visible, but the top half of the face is cropped out of the frame.
- Gemini evidence: The camera framing cuts off the person's face above the nose for the duration of the video.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/mediapipe_CC_TN_Sp_So_rel_sync_v1.txt`

#### TN — Si_So_rel_sync_cnt v1

- Human: `no` / Gemini: `no`
- Temporal type: `relative_sync_count`
- Modality: `Action (silent) + Action (sounding)`
- Gemini reason: The right hand does not start resting on the knee/thigh as requested, and extra target actions occur.
- Gemini evidence: At 00:00.000, the right hand is already raised in a thumbs-up near the chest rather than resting on the thigh. Additionally, the third and fourth slaps violate the post-event stillness constraint.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/mediapipe_CC_TN_Si_So_rel_sync_cnt_v1.txt`

#### FP — Sp_Si_So_rel_sync_cnt v1

- Human: `no` / Gemini: `yes`
- Temporal type: `relative_sync_count`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: The video complies with the scene, camera, and initial pose constraints. Although the person makes some additional non-target right-hand gestures after the second repetition, no extra target actions, words, or sounds occur, which strictly satisfies the prompt's instruction.
- Gemini evidence: The video features a static medium shot in a plain indoor room. The person starts with hands on thighs. While the right hand gestures mildly between 00:01.600 and 00:03.000, it does not form a thumbs-up, slap the thigh, or produce extra words or sounds.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/mediapipe_CC_FP_Sp_Si_So_rel_sync_cnt_v1.txt`

#### FP — Sp_Si_rel_ord_SpSi v1

- Human: `no` / Gemini: `yes`
- Temporal type: `relative_order`
- Modality: `Speech + Action (silent)`
- Gemini reason: The video complies with all provided scene, camera, and specific action constraints.
- Gemini evidence: The video features a plain indoor room, static medium shot, seated person with hands initially on thighs, no background music, no extra words spoken, and the person holds the final pose without performing any additional actions.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/mediapipe_CC_FP_Sp_Si_rel_ord_SpSi_v1.txt`

#### FP — Sp_Si_So_rel_ord_SoSpSi v1

- Human: `no` / Gemini: `yes`
- Temporal type: `relative_order`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: The video adheres to all non-core constraints, including scene, camera, initial pose, and post-event stillness.
- Gemini evidence: The video features a static medium shot in a plain indoor room. The person starts with hands on thighs, speaks no extra words, makes no extra sounds, and holds the thumbs-up pose completely still until the end of the video.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/mediapipe_CC_FP_Sp_Si_So_rel_ord_SoSpSi_v1.txt`

#### FN — Sp_So_rel_ord_SpSo v1

- Human: `yes` / Gemini: `no`
- Temporal type: `relative_order`
- Modality: `Speech + Action (sounding)`
- Gemini reason: The person performs extra, unprompted actions, including lifting the left arm and making an initial soundless slap with both hands, violating the constraint against extra gestures.
- Gemini evidence: Between 00:03.000 and 00:03.500, the left hand lifts and slaps the left thigh, which is not part of the prompted action. The early double-hand slap is an extra gesture.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/mediapipe_CC_FN_Sp_So_rel_ord_SpSo_v1.txt`

#### FN — Si_So_rel_ord_SiSo v1

- Human: `yes` / Gemini: `no`
- Temporal type: `relative_order`
- Modality: `Action (silent) + Action (sounding)`
- Gemini reason: The prompt requires the person's full face and mouth to be visible, but the framing cuts off the top of the person's head.
- Gemini evidence: Throughout the video, the person's head is partially cropped out of the top of the frame (supported by MediaPipe nose y-coordinates being negative), violating the 'full face visible' constraint.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/mediapipe_CC_FN_Si_So_rel_ord_SiSo_v1.txt`

#### FN — Si_So_rel_sync v1

- Human: `yes` / Gemini: `no`
- Temporal type: `relative_synchronization`
- Modality: `Action (silent) + Action (sounding)`
- Gemini reason: The prompt requires that no new target action occurs after the final event, but the video repeats the actions multiple times.
- Gemini evidence: The person performs the sequence of raising the hand and slapping the thigh three distinct times instead of remaining still after the first occurrence.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/mediapipe_CC_FN_Si_So_rel_sync_v1.txt`

## whisper

### A

#### TP — Sp_So_rel_ord_SpSo v1

- Human: `yes` / Gemini: `yes`
- Temporal type: `relative_order`
- Modality: `Speech + Action (sounding)`
- Gemini reason: The speech event and the non-speech sound event are both present and correct in the audio track.
- Gemini evidence: The word 'help' is clearly audible (Whisper detects it at 0.00-0.34s), and a sharp slap-like sound is heard at exactly 4.00s.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/whisper_A_TP_Sp_So_rel_ord_SpSo_v1.txt`

#### TP — Sp_Si_So_rel_ord_SiSoSp v1

- Human: `yes` / Gemini: `yes`
- Temporal type: `relative_order`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: The required slap sound and the spoken word 'help' are both clearly present in the audio track.
- Gemini evidence: A sharp slap sound is audible at 00:02.0, and the word 'help' is spoken at 00:03.5, which is also confirmed by Whisper ASR timestamps.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/whisper_A_TP_Sp_Si_So_rel_ord_SiSoSp_v1.txt`

#### TP — Si_So_rel_sync_cnt v1

- Human: `yes` / Gemini: `yes`
- Temporal type: `relative_sync_count`
- Modality: `Action (silent) + Action (sounding)`
- Gemini reason: Sharp slap sounds are clearly audible and match the target sound profile.
- Gemini evidence: Three distinct slap sounds are heard at approximately 0:00.100, 0:00.900, and 0:02.100.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/whisper_A_TP_Si_So_rel_sync_cnt_v1.txt`

#### TN — Sp_So_rel_sync v1

- Human: `no` / Gemini: `no`
- Temporal type: `relative_synchronization`
- Modality: `Speech + Action (sounding)`
- Gemini reason: The speech 'help' is audible, but the required sharp slap sound is missing.
- Gemini evidence: Whisper detects 'help' from 0.00s to 0.28s, but no slap sound is heard in the audio track, even when the visual impact occurs later.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/whisper_A_TN_Sp_So_rel_sync_v1.txt`

#### FP — Sp_So_rel_ord_SoSp v1

- Human: `no` / Gemini: `yes`
- Temporal type: `relative_order`
- Modality: `Speech + Action (sounding)`
- Gemini reason: Both the spoken word 'help' and the sound of a slap are clearly audible and correct.
- Gemini evidence: Whisper ASR confirms the word 'Help' from 0.00 to 0.22s. A distinct sharp slap sound is heard around 1.04s.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/whisper_A_FP_Sp_So_rel_ord_SoSp_v1.txt`

#### FN — Sp_Si_So_rel_sync_cnt v1

- Human: `yes` / Gemini: `no`
- Temporal type: `relative_sync_count`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: The word 'help' is only spoken once instead of the required twice, and the sharp slap sound is entirely missing.
- Gemini evidence: Whisper detects 'help' only from 0.00 to 0.22 seconds, and direct audio inspection confirms no second 'help' or any slap sounds occur.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/whisper_A_FN_Sp_Si_So_rel_sync_cnt_v1.txt`

#### FN — Sp_Si_So_rel_ord_SpSiSo v1

- Human: `yes` / Gemini: `no`
- Temporal type: `relative_order`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: The speech 'help' is audible, but the required sharp slap sound is completely missing.
- Gemini evidence: Whisper detects 'help' at 0.00-0.28. The remainder of the audio track is silent, with no slap sound corresponding to the thigh strike.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/whisper_A_FN_Sp_Si_So_rel_ord_SpSiSo_v1.txt`

### V

#### TP — Sp_So_rel_ord_SpSo v1

- Human: `yes` / Gemini: `yes`
- Temporal type: `relative_order`
- Modality: `Speech + Action (sounding)`
- Gemini reason: The required visible actions are present, including speaking motions and the right hand striking the right thigh.
- Gemini evidence: The person's mouth visibly moves at the start of the video. Later, the right hand (viewer's left) lifts up and then makes visible contact with the right thigh at 4.29s.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/whisper_V_TP_Sp_So_rel_ord_SpSo_v1.txt`

#### TP — Sp_Si_So_rel_ord_SoSiSp v1

- Human: `yes` / Gemini: `yes`
- Temporal type: `relative_order`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: The right hand striking the right thigh, the right-hand thumbs-up pose, and the visible mouth motion for speaking are all clearly shown and correct.
- Gemini evidence: The video shows the right hand striking the right thigh at 1.0s, a clear right-hand thumbs-up pose starting at 1.8s, and visible mouth movement corresponding to 'help' at 2.8s.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/whisper_V_TP_Sp_Si_So_rel_ord_SoSiSp_v1.txt`

#### TP — Sp_Si_So_rel_ord_SiSoSp v1

- Human: `yes` / Gemini: `yes`
- Temporal type: `relative_order`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: The required visible actions (thumbs-up, thigh slap, and speaking motion) are all clearly performed.
- Gemini evidence: The person forms a right-hand thumbs-up around 00:00.5, slaps the right thigh with the right hand at 00:02.0, and has visible lip movement corresponding to speech at 00:03.5.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/whisper_V_TP_Sp_Si_So_rel_ord_SiSoSp_v1.txt`

#### TN — Sp_Si_So_rel_sync v1

- Human: `no` / Gemini: `no`
- Temporal type: `relative_synchronization`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: The actions are performed by the wrong hand. The left hand (viewer's right) performs the thumbs-up and the slap, while the required right hand remains resting. Furthermore, the thumbs-up pose is not maintained during the slap.
- Gemini evidence: From 0.00s to 0.50s, the person's left hand is raised in a thumbs-up and then slaps the left thigh; the right hand (viewer's left) does not move.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/whisper_V_TN_Sp_Si_So_rel_sync_v1.txt`

#### TN — Sp_So_rel_sync_cnt v1

- Human: `no` / Gemini: `no`
- Temporal type: `relative_sync_count`
- Modality: `Speech + Action (sounding)`
- Gemini reason: The person strikes their left thigh with their left hand instead of using the right hand and right thigh as specified. Additionally, there is no clear visible mouth movement corresponding to the spoken word when the slaps occur.
- Gemini evidence: The video shows the person's left hand (viewer's right) moving to strike the left thigh at 1.00s, 3.00s, and 4.58s.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/whisper_V_TN_Sp_So_rel_sync_cnt_v1.txt`

#### TN — Sp_Si_So_rel_ord_SoSpSi v1

- Human: `no` / Gemini: `no`
- Temporal type: `relative_order`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: The slapping action is performed using the incorrect hand and body side.
- Gemini evidence: The video shows the person's left hand slapping their left thigh, instead of the required right hand and right thigh. The right hand does correctly perform a thumbs-up later.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/whisper_V_TN_Sp_Si_So_rel_ord_SoSpSi_v1.txt`

#### FP — Si_So_rel_ord_SiSo v1

- Human: `no` / Gemini: `yes`
- Temporal type: `relative_order`
- Modality: `Action (silent) + Action (sounding)`
- Gemini reason: The person's right hand correctly forms a thumbs-up pose and then visibly strikes the right thigh.
- Gemini evidence: A clear thumbs-up pose is held from approximately 00:01.000 to 00:02.500 by the person's right hand. The same hand then strikes the right thigh at 00:03.000.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/whisper_V_FP_Si_So_rel_ord_SiSo_v1.txt`

#### FP — Sp_Si_So_rel_ord_SpSoSi v1

- Human: `no` / Gemini: `yes`
- Temporal type: `relative_order`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: The visible speaking motion, the right hand slapping the right thigh, and the right hand forming a thumbs-up are all clearly present and correct.
- Gemini evidence: The person's mouth moves during the first 0.5s. The right hand then strikes the right thigh around 2.37s and forms a clear thumbs-up pose from 2.50s onwards.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/whisper_V_FP_Sp_Si_So_rel_ord_SpSoSi_v1.txt`

#### FP — Si_So_rel_ord_SoSi v1

- Human: `no` / Gemini: `yes`
- Temporal type: `relative_order`
- Modality: `Action (silent) + Action (sounding)`
- Gemini reason: The visible actions match the prompt, with the right hand slapping the right thigh and then forming a thumbs-up pose.
- Gemini evidence: The right hand is seen moving down to strike the right thigh at 00:01.292, and subsequently forms a clear thumbs-up pose at 00:01.875, holding it for the rest of the video.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/whisper_V_FP_Si_So_rel_ord_SoSi_v1.txt`

#### FN — Si_So_rel_sync_cnt v1

- Human: `yes` / Gemini: `no`
- Temporal type: `relative_sync_count`
- Modality: `Action (silent) + Action (sounding)`
- Gemini reason: The right hand starts raised rather than resting on the thigh, and it fails to maintain the required thumbs-up pose during the thigh strikes.
- Gemini evidence: At 0:00.000, the right hand is already raised in a thumbs-up. During the thigh contacts at 0:00.125, 0:00.875, and 0:02.042, the hand flattens instead of keeping the thumb extended upward.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/whisper_V_FN_Si_So_rel_sync_cnt_v1.txt`

#### FN — Sp_So_rel_sync v1

- Human: `yes` / Gemini: `no`
- Temporal type: `relative_synchronization`
- Modality: `Speech + Action (sounding)`
- Gemini reason: The visible physical action of slapping the thigh occurs, but the person's face and mouth are not visible, preventing verification of the speaking motion.
- Gemini evidence: The right hand strikes the thigh at 00:01.458, but the person's head is cropped out of the frame for the entire video, violating the requirement that the full face and mouth remain clearly visible.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/whisper_V_FN_Sp_So_rel_sync_v1.txt`

#### FN — Sp_Si_So_rel_sync_cnt v1

- Human: `yes` / Gemini: `no`
- Temporal type: `relative_sync_count`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: The visible speaking motion for 'help' only occurs once, and the right-hand thigh slap motion is missing entirely.
- Gemini evidence: The person forms a thumbs-up pose at 0.04s and again at 1.00s, but never strikes the thigh. Visible mouth motion for speech only occurs during the first thumbs-up.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/whisper_V_FN_Sp_Si_So_rel_sync_cnt_v1.txt`

### AVB

#### TP — Sp_Si_So_rel_ord_SiSoSp v1

- Human: `yes` / Gemini: `yes`
- Temporal type: `relative_order`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: The audio and visual components for both the sounding action and the speech event are correctly synchronized.
- Gemini evidence: The slap sound at 00:02.0 perfectly aligns with the visual impact of the hand on the thigh, and the spoken word 'help' aligns with the visible mouth movements at 00:03.5.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/whisper_AVB_TP_Sp_Si_So_rel_ord_SiSoSp_v1.txt`

#### TP — Sp_Si_So_rel_ord_SoSiSp v1

- Human: `yes` / Gemini: `yes`
- Temporal type: `relative_order`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: The audio and visual components for both the sounding action and the speech are correctly synchronized.
- Gemini evidence: The slap sound at 1.0s aligns precisely with the visible hand impact, and the spoken word 'help' matches the visible lip movements starting at 2.86s.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/whisper_AVB_TP_Sp_Si_So_rel_ord_SoSiSp_v1.txt`

#### TP — Sp_Si_So_rel_ord_SiSpSo v1

- Human: `yes` / Gemini: `yes`
- Temporal type: `relative_order`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: Both the speech and the slapping action are correctly bound to their respective visible motions.
- Gemini evidence: The audible 'help' aligns precisely with the visible lip movement at the beginning, and the slap sound aligns with the hand striking the thigh at 3.0s.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/whisper_AVB_TP_Sp_Si_So_rel_ord_SiSpSo_v1.txt`

#### TN — Sp_So_rel_sync v1

- Human: `no` / Gemini: `no`
- Temporal type: `relative_synchronization`
- Modality: `Speech + Action (sounding)`
- Gemini reason: Both the required slap sound and the visible speaking motion are missing, meaning binding cannot be evaluated.
- Gemini evidence: The absence of the slap sound in the audio and the out-of-frame mouth in the video force this axis to fail.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/whisper_AVB_TN_Sp_So_rel_sync_v1.txt`

#### TN — Si_So_rel_ord_SoSi v1

- Human: `no` / Gemini: `no`
- Temporal type: `relative_order`
- Modality: `Action (silent) + Action (sounding)`
- Gemini reason: The slap sound is not synchronized with the visible hand-to-thigh contact.
- Gemini evidence: The slap sound occurs at 00:01.000 while the right hand is still raised in the air. The visual impact on the thigh happens significantly later, around 00:01.292.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/whisper_AVB_TN_Si_So_rel_ord_SoSi_v1.txt`

#### TN — Sp_So_rel_sync_cnt v1

- Human: `no` / Gemini: `no`
- Temporal type: `relative_sync_count`
- Modality: `Speech + Action (sounding)`
- Gemini reason: The visual component of the sounding action is incorrect (wrong hand and side), and the visible speaking motion is absent during the slaps, so binding is not evaluable and fails.
- Gemini evidence: Fails visual event correctness precondition.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/whisper_AVB_TN_Sp_So_rel_sync_cnt_v1.txt`

#### FP — Sp_So_rel_ord_SoSp v1

- Human: `no` / Gemini: `yes`
- Temporal type: `relative_order`
- Modality: `Speech + Action (sounding)`
- Gemini reason: The audio and visual components of both events are correctly synchronized.
- Gemini evidence: The spoken word 'help' aligns perfectly with the visible lip movements at 0.00s, and the slap sound occurs precisely at the moment of physical impact on the thigh at 1.04s.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/whisper_AVB_FP_Sp_So_rel_ord_SoSp_v1.txt`

#### FP — Sp_Si_So_rel_ord_SpSoSi v1

- Human: `no` / Gemini: `yes`
- Temporal type: `relative_order`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: The audio and visual components of both the speech and the sounding action are correctly synchronized.
- Gemini evidence: The spoken 'help' perfectly aligns with the visible mouth movement, and the slap sound occurs exactly at the moment the right hand strikes the thigh (approx 2.37s).
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/whisper_AVB_FP_Sp_Si_So_rel_ord_SpSoSi_v1.txt`

#### FP — Si_So_rel_ord_SiSo v1

- Human: `no` / Gemini: `yes`
- Temporal type: `relative_order`
- Modality: `Action (silent) + Action (sounding)`
- Gemini reason: The slap sound is perfectly synchronized with the visible impact of the hand on the thigh.
- Gemini evidence: The visible hand contact on the thigh and the sharp slap sound both occur simultaneously exactly at 00:03.000.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/whisper_AVB_FP_Si_So_rel_ord_SiSo_v1.txt`

#### FN — Sp_So_rel_ord_SpSo v1

- Human: `yes` / Gemini: `no`
- Temporal type: `relative_order`
- Modality: `Speech + Action (sounding)`
- Gemini reason: The slap sound is entirely misaligned with the visual contact of the hand on the thigh.
- Gemini evidence: The sharp slap sound occurs at 4.00s, precisely when the right hand is raised high in the air. The hand does not visibly strike the thigh until 4.29s, at which point there is no accompanying sound.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/whisper_AVB_FN_Sp_So_rel_ord_SpSo_v1.txt`

#### FN — Si_So_rel_sync_cnt v1

- Human: `yes` / Gemini: `no`
- Temporal type: `relative_sync_count`
- Modality: `Action (silent) + Action (sounding)`
- Gemini reason: The visual component is incorrect, so audio-visual binding is not evaluable.
- Gemini evidence: The required synchronized visual pose (thumbs-up during the slap) is missing, failing the precondition for binding.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/whisper_AVB_FN_Si_So_rel_sync_cnt_v1.txt`

#### FN — Sp_Si_So_rel_sync_cnt v1

- Human: `yes` / Gemini: `no`
- Temporal type: `relative_sync_count`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: The required audio and visual components are missing or incomplete, so binding is not evaluable.
- Gemini evidence: The slap sound, thigh slap motion, and the second 'help' speech event are absent.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/whisper_AVB_FN_Sp_Si_So_rel_sync_cnt_v1.txt`

### TC_REL

#### TP — Sp_Si_So_rel_ord_SiSoSp v1

- Human: `yes` / Gemini: `yes`
- Temporal type: `relative_order`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: The events occur in the correct sequence as specified by the prompt.
- Gemini evidence: The silent thumbs-up is completed first, followed by the thigh slap at 00:02.0, and then the speech event at 00:03.5.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/whisper_TC_REL_TP_Sp_Si_So_rel_ord_SiSoSp_v1.txt`

#### TP — Sp_Si_rel_ord_SpSi v1

- Human: `yes` / Gemini: `yes`
- Temporal type: `relative_order`
- Modality: `Speech + Action (silent)`
- Gemini reason: The specified sequence is satisfied, with the speech fully concluding before the silent action begins.
- Gemini evidence: The spoken word ends at 0.30s, and the right-hand thumbs-up action starts subsequently at 0.70s.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/whisper_TC_REL_TP_Sp_Si_rel_ord_SpSi_v1.txt`

#### TP — Sp_Si_So_rel_ord_SoSiSp v1

- Human: `yes` / Gemini: `yes`
- Temporal type: `relative_order`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: The events follow the strict sequential order specified by the prompt.
- Gemini evidence: The slap occurs first at 1.0s, followed by the thumbs-up at 1.8s, and finally the speech event starting at 2.86s.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/whisper_TC_REL_TP_Sp_Si_So_rel_ord_SoSiSp_v1.txt`

#### TN — Sp_So_rel_sync v1

- Human: `no` / Gemini: `no`
- Temporal type: `relative_synchronization`
- Modality: `Speech + Action (sounding)`
- Gemini reason: The events are not synchronized, and the temporal preconditions failed due to missing event components.
- Gemini evidence: The speech is heard at 0.00s, while the visual slap impact occurs at 00:01.458. Furthermore, the missing audio and visual components force this sub-axis to fail.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/whisper_TC_REL_TN_Sp_So_rel_sync_v1.txt`

#### TN — Sp_So_rel_sync_cnt v1

- Human: `no` / Gemini: `no`
- Temporal type: `relative_sync_count`
- Modality: `Speech + Action (sounding)`
- Gemini reason: Audio-visual binding and visual correctness preconditions failed. Furthermore, the speech and slaps are not synchronized.
- Gemini evidence: Fails AVB precondition. The spoken word 'help' occurs early (0.00-0.28s), while the slaps occur sequentially afterward at 1.00s, 3.00s, and 4.60s.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/whisper_TC_REL_TN_Sp_So_rel_sync_cnt_v1.txt`

#### TN — Sp_So_rel_ord_SoSp v1

- Human: `no` / Gemini: `no`
- Temporal type: `relative_order`
- Modality: `Speech + Action (sounding)`
- Gemini reason: The prompt required the thigh slap to occur first, followed by the spoken word 'help'. The generated video reverses this order.
- Gemini evidence: The speech 'help' occurs at 0.00s, before the thigh slap which happens at 1.04s.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/whisper_TC_REL_TN_Sp_So_rel_ord_SoSp_v1.txt`

#### FP — Si_So_rel_ord_SiSo v1

- Human: `no` / Gemini: `yes`
- Temporal type: `relative_order`
- Modality: `Action (silent) + Action (sounding)`
- Gemini reason: The actions occur in the correct relative sequence as requested.
- Gemini evidence: The silent thumbs-up action is fully completed before the hand descends to strike the thigh for the sounding action.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/whisper_TC_REL_FP_Si_So_rel_ord_SiSo_v1.txt`

#### FP — Sp_Si_rel_sync_cnt v1

- Human: `no` / Gemini: `yes`
- Temporal type: `relative_sync_count`
- Modality: `Speech + Action (silent)`
- Gemini reason: The single occurrence of the spoken word and the thumbs-up action are synchronized.
- Gemini evidence: The word 'help' (0.00s-0.26s) and the right-hand thumbs-up action happen simultaneously at the start of the video.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/whisper_TC_REL_FP_Sp_Si_rel_sync_cnt_v1.txt`

#### FP — Sp_Si_So_rel_ord_SpSoSi v1

- Human: `no` / Gemini: `yes`
- Temporal type: `relative_order`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: The specified order of events (speech, then slap, then thumbs-up) is strictly followed.
- Gemini evidence: Speech completes by 0.5s, the slap occurs at 2.37s, and the thumbs-up is formed directly after the slap at 2.50s.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/whisper_TC_REL_FP_Sp_Si_So_rel_ord_SpSoSi_v1.txt`

#### FN — Sp_So_rel_ord_SpSo v1

- Human: `yes` / Gemini: `no`
- Temporal type: `relative_order`
- Modality: `Speech + Action (sounding)`
- Gemini reason: Audio-visual binding failed for the sounding action, making the temporal relation unfulfilled.
- Gemini evidence: Because the visual contact and the slap sound are disconnected, a valid coordinated sounding action event does not occur in sequence.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/whisper_TC_REL_FN_Sp_So_rel_ord_SpSo_v1.txt`

#### FN — Si_So_rel_sync_cnt v1

- Human: `yes` / Gemini: `no`
- Temporal type: `relative_sync_count`
- Modality: `Action (silent) + Action (sounding)`
- Gemini reason: Precondition failed: visual event correctness is 'no'.
- Gemini evidence: Cannot evaluate temporal synchronization because the core visual action is performed incorrectly.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/whisper_TC_REL_FN_Si_So_rel_sync_cnt_v1.txt`

### TC_COUNT

#### TP — Sp_Si_rel_ord_SpSi v1

- Human: `yes` / Gemini: `yes`
- Temporal type: `relative_order`
- Modality: `Speech + Action (silent)`
- Gemini reason: Each required event occurs exactly once as requested.
- Gemini evidence: The video contains exactly one spoken 'help' and one continuous thumbs-up action, with no extra occurrences.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/whisper_TC_COUNT_TP_Sp_Si_rel_ord_SpSi_v1.txt`

#### TP — Sp_Si_rel_ord_SiSp v1

- Human: `yes` / Gemini: `yes`
- Temporal type: `relative_order`
- Modality: `Speech + Action (silent)`
- Gemini reason: Each required event occurs exactly once with no repetitions.
- Gemini evidence: One thumbs-up action and one spoken instance of 'help' are present.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/whisper_TC_COUNT_TP_Sp_Si_rel_ord_SiSp_v1.txt`

#### TP — Sp_Si_So_rel_ord_SiSpSo v1

- Human: `yes` / Gemini: `yes`
- Temporal type: `relative_order`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: Each of the three required events occurs exactly once.
- Gemini evidence: The video contains a single utterance of 'help', one thumbs-up pose, and one thigh slap, with no extra occurrences.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/whisper_TC_COUNT_TP_Sp_Si_So_rel_ord_SiSpSo_v1.txt`

#### TN — Sp_So_rel_ord_SpSo v1

- Human: `no` / Gemini: `no`
- Temporal type: `relative_order`
- Modality: `Speech + Action (sounding)`
- Gemini reason: Audio-visual binding failed, preventing the required target bundle from being correctly counted.
- Gemini evidence: The temporal misalignment between the slap sound and visual contact means the sounding action event was not properly completed.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/whisper_TC_COUNT_TN_Sp_So_rel_ord_SpSo_v1.txt`

#### TN — Sp_So_rel_sync v1

- Human: `no` / Gemini: `no`
- Temporal type: `relative_synchronization`
- Modality: `Speech + Action (sounding)`
- Gemini reason: Evaluation preconditions failed because the necessary audio and visual event components are incomplete.
- Gemini evidence: Failed audio event correctness, visual event correctness, and audio-visual binding prevent counting the synchronized bundles.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/whisper_TC_COUNT_TN_Sp_So_rel_sync_v1.txt`

#### TN — Sp_Si_rel_sync_cnt v1

- Human: `no` / Gemini: `no`
- Temporal type: `relative_sync_count`
- Modality: `Speech + Action (silent)`
- Gemini reason: The synchronized bundle occurs only once instead of the required two times.
- Gemini evidence: The prompt requires the action and speech bundle to be performed twice, but only one repetition occurs between 0.00s and 0.70s, followed by stillness.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/whisper_TC_COUNT_TN_Sp_Si_rel_sync_cnt_v1.txt`

#### FP — Sp_So_rel_ord_SoSp v1

- Human: `no` / Gemini: `yes`
- Temporal type: `relative_order`
- Modality: `Speech + Action (sounding)`
- Gemini reason: Both the speech event and the slapping action occur exactly once, matching the prompt's requirements.
- Gemini evidence: There is only one utterance of 'help' and one thigh slap. No extra or repeated actions are present.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/whisper_TC_COUNT_FP_Sp_So_rel_ord_SoSp_v1.txt`

#### FP — Si_So_rel_ord_SiSo v1

- Human: `no` / Gemini: `yes`
- Temporal type: `relative_order`
- Modality: `Action (silent) + Action (sounding)`
- Gemini reason: Both required actions occur exactly once.
- Gemini evidence: The thumbs-up is formed once, and the thigh is slapped exactly once, with no additional or repeated target events.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/whisper_TC_COUNT_FP_Si_So_rel_ord_SiSo_v1.txt`

#### FP — Sp_Si_So_rel_ord_SpSoSi v1

- Human: `no` / Gemini: `yes`
- Temporal type: `relative_order`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: Each required event occurs exactly once, with no spurious repetitions.
- Gemini evidence: The word 'help' is said once, the slap occurs once, and the thumbs-up is formed and held without repetition.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/whisper_TC_COUNT_FP_Sp_Si_So_rel_ord_SpSoSi_v1.txt`

#### FN — Sp_Si_rel_sync v1

- Human: `yes` / Gemini: `no`
- Temporal type: `relative_synchronization`
- Modality: `Speech + Action (silent)`
- Gemini reason: The required synchronized bundle of speech and action occurs zero times instead of exactly once.
- Gemini evidence: Because the events are disjointed rather than simultaneous, the synchronized event structure is entirely missing.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/whisper_TC_COUNT_FN_Sp_Si_rel_sync_v1.txt`

### CC

#### TP — Si_So_rel_ord_SiSo v1

- Human: `yes` / Gemini: `yes`
- Temporal type: `relative_order`
- Modality: `Action (silent) + Action (sounding)`
- Gemini reason: The video satisfies all non-core prompt constraints, including scene, camera, and post-event stillness.
- Gemini evidence: The video shows a single seated person in a plain indoor room via a static medium shot. No extra actions, gestures, speech, or sounds occur after the final event.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/whisper_CC_TP_Si_So_rel_ord_SiSo_v1.txt`

#### TP — Sp_So_rel_ord_SoSp v1

- Human: `yes` / Gemini: `yes`
- Temporal type: `relative_order`
- Modality: `Speech + Action (sounding)`
- Gemini reason: The video adheres to all scene, camera, and stillness constraints.
- Gemini evidence: The video features a static medium shot in a plain indoor room. The person starts with hands on thighs and remains relatively still after the final event.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/whisper_CC_TP_Sp_So_rel_ord_SoSp_v1.txt`

#### TP — Sp_Si_So_rel_ord_SpSoSi v1

- Human: `yes` / Gemini: `yes`
- Temporal type: `relative_order`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: All scene, camera, and state constraints are satisfied.
- Gemini evidence: The video features a static medium shot in a plain indoor room. The person is seated, hands initially on thighs, and holds the final pose with no extra words, actions, or sounds.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/whisper_CC_TP_Sp_Si_So_rel_ord_SpSoSi_v1.txt`

#### TN — Si_So_rel_sync_cnt v1

- Human: `no` / Gemini: `no`
- Temporal type: `relative_sync_count`
- Modality: `Action (silent) + Action (sounding)`
- Gemini reason: The right hand does not start resting on the thigh, and an extra sequence occurs, violating the strict exact-count and post-event stillness constraints.
- Gemini evidence: The right hand starts raised at the beginning of the video. A third, unrequested sequence of a thumbs-up and slap occurs between 0:01.833 and 0:02.100.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/whisper_CC_TN_Si_So_rel_sync_cnt_v1.txt`

#### TN — Sp_So_rel_sync v1

- Human: `no` / Gemini: `no`
- Temporal type: `relative_synchronization`
- Modality: `Speech + Action (sounding)`
- Gemini reason: The prompt strict constraint that the full face and mouth remain clearly visible is violated.
- Gemini evidence: The framing of the static medium shot cuts off the person's head and face completely.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/whisper_CC_TN_Sp_So_rel_sync_v1.txt`

#### TN — Sp_Si_rel_ord_SpSi v1

- Human: `no` / Gemini: `no`
- Temporal type: `relative_order`
- Modality: `Speech + Action (silent)`
- Gemini reason: The video violates the camera framing constraints regarding visibility.
- Gemini evidence: The prompt explicitly requires the 'full face' to be clearly visible, but the person's head is largely cropped out above the mouth.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/whisper_CC_TN_Sp_Si_rel_ord_SpSi_v1.txt`

#### FP — Sp_Si_So_rel_sync_cnt v1

- Human: `no` / Gemini: `yes`
- Temporal type: `relative_sync_count`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: The video maintains the correct setting, camera angle, and stillness constraints without introducing prohibited elements.
- Gemini evidence: The scene is a plain indoor room with a static medium shot. No extra people, text, or background music are present, and the person remains still after the final thumbs-up.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/whisper_CC_FP_Sp_Si_So_rel_sync_cnt_v1.txt`

#### FP — Sp_Si_rel_sync_cnt v1

- Human: `no` / Gemini: `yes`
- Temporal type: `relative_sync_count`
- Modality: `Speech + Action (silent)`
- Gemini reason: The video satisfies the scene and camera constraints, with no extra actions, sounds, or people present.
- Gemini evidence: A single person is shown in a static medium shot in a plain room. After the single event, the person remains still with no spurious actions or audio.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/whisper_CC_FP_Sp_Si_rel_sync_cnt_v1.txt`

#### FP — Sp_Si_So_rel_ord_SiSoSp v1

- Human: `no` / Gemini: `yes`
- Temporal type: `relative_order`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: All scene, camera, start-state, and post-event stillness constraints are satisfied.
- Gemini evidence: The video is a static medium shot in a plain indoor room, the person starts with hands resting on thighs, and remains still after speaking the required word.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/whisper_CC_FP_Sp_Si_So_rel_ord_SiSoSp_v1.txt`

#### FN — Sp_So_rel_ord_SpSo v1

- Human: `yes` / Gemini: `no`
- Temporal type: `relative_order`
- Modality: `Speech + Action (sounding)`
- Gemini reason: The video contains an unprompted extra action that violates the constraints.
- Gemini evidence: At 3.00s, the person's left hand (viewer's right) drops off the thigh and disappears from view, which is an extra gesture not requested by the prompt.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/whisper_CC_FN_Sp_So_rel_ord_SpSo_v1.txt`

#### FN — Si_So_rel_sync v1

- Human: `yes` / Gemini: `no`
- Temporal type: `relative_synchronization`
- Modality: `Action (silent) + Action (sounding)`
- Gemini reason: The person performs extra hand motions and silent slaps after the initial event, violating the post-event stillness constraint.
- Gemini evidence: The right hand continues to lift and tap the thigh at 0.54s and 1.04s, defying the 'no new target action' rule.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/whisper_CC_FN_Si_So_rel_sync_v1.txt`

#### FN — Sp_So_rel_sync_cnt v1

- Human: `yes` / Gemini: `no`
- Temporal type: `relative_sync_count`
- Modality: `Speech + Action (sounding)`
- Gemini reason: The prompt requires exactly two repetitions with no extra sounds or actions and no new target actions after the final event, but a third slap occurs.
- Gemini evidence: A third striking motion and sound occur around 4.58s, violating the exact count and post-event stillness constraints.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/whisper_CC_FN_Sp_So_rel_sync_cnt_v1.txt`

## clap

### A

#### TP — Si_So_rel_sync v1

- Human: `yes` / Gemini: `yes`
- Temporal type: `relative_synchronization`
- Modality: `Action (silent) + Action (sounding)`
- Gemini reason: The required sharp slap sounds corresponding to the thigh slaps are clearly audible in the video.
- Gemini evidence: Clear slap sounds are heard around 0.5s, 1.5s, and 3.5s, which aligns with the positive CLAP similarities for 'slapping_the_thigh' in the corresponding time windows.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/clap_A_TP_Si_So_rel_sync_v1.txt`

#### TP — Sp_Si_So_rel_ord_SpSoSi v1

- Human: `yes` / Gemini: `yes`
- Temporal type: `relative_order`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: Both the speech event and the sounding action's audio are correctly present.
- Gemini evidence: The spoken word 'help' is clearly heard around 0.5s, and a distinct slap sound is heard near 2.4s, supported by the CLAP sliding-window peak for 'slapping_the_thigh'.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/clap_A_TP_Sp_Si_So_rel_ord_SpSoSi_v1.txt`

#### TP — Sp_Si_So_rel_ord_SpSiSo v1

- Human: `yes` / Gemini: `yes`
- Temporal type: `relative_order`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: The spoken word 'help' is clearly heard, and a distinct slap sound occurs near the end of the video, matching the prompt requirements.
- Gemini evidence: Speech 'help' is audible at the beginning of the audio. CLAP correctly indicates a slap sound in the [4.25 - 5.00] window, which matches the heard slap.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/clap_A_TP_Sp_Si_So_rel_ord_SpSiSo_v1.txt`

#### TN — Sp_So_rel_ord_SoSp v1

- Human: `no` / Gemini: `no`
- Temporal type: `relative_order`
- Modality: `Speech + Action (sounding)`
- Gemini reason: The required speech event 'help' is completely missing from the audio track.
- Gemini evidence: A slap sound is audible between 0.5s and 1.0s, but there is no spoken word 'help' or any other speech present at any point in the video's audio.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/clap_A_TN_Sp_So_rel_ord_SoSp_v1.txt`

#### FP — Sp_So_rel_sync v1

- Human: `no` / Gemini: `yes`
- Temporal type: `relative_synchronization`
- Modality: `Speech + Action (sounding)`
- Gemini reason: The required spoken word and slap sound are both present in the audio.
- Gemini evidence: The word 'help' and a slap sound are clearly heard around 1.3 to 1.4 seconds.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/clap_A_FP_Sp_So_rel_sync_v1.txt`

#### FN — Sp_Si_So_rel_ord_SiSoSp v1

- Human: `yes` / Gemini: `no`
- Temporal type: `relative_order`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: The required speech event 'help' is completely absent from the audio track.
- Gemini evidence: The audio contains a slap sound around 02:20, but remains silent afterward with no spoken words heard.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/clap_A_FN_Sp_Si_So_rel_ord_SiSoSp_v1.txt`

#### FN — Sp_Si_So_rel_sync_cnt v1

- Human: `yes` / Gemini: `no`
- Temporal type: `relative_sync_count`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: There is no evidence of the required speech 'help' being spoken.
- Gemini evidence: No Whisper ASR transcription is present to indicate speech, and CLAP scores for 'a person speaking' are very low or negative throughout the video.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/clap_A_FN_Sp_Si_So_rel_sync_cnt_v1.txt`

#### FN — Sp_Si_rel_ord_SpSi v1

- Human: `yes` / Gemini: `no`
- Temporal type: `relative_order`
- Modality: `Speech + Action (silent)`
- Gemini reason: The required speech event 'help' is completely absent; the audio track is silent.
- Gemini evidence: Direct audio inspection reveals no speech, and CLAP negative anchors for silence dominate throughout the video.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/clap_A_FN_Sp_Si_rel_ord_SpSi_v1.txt`

### V

#### TP — Si_So_rel_sync_cnt v1

- Human: `yes` / Gemini: `yes`
- Temporal type: `relative_sync_count`
- Modality: `Action (silent) + Action (sounding)`
- Gemini reason: The actor forms a thumbs-up with the right hand and visibly strikes the right thigh twice, separated by a brief reset.
- Gemini evidence: Visible contact of the right fist (with thumb extended) against the right thigh is seen at 00:00.750 and 00:02.200.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/clap_V_TP_Si_So_rel_sync_cnt_v1.txt`

#### TP — Sp_Si_rel_ord_SpSi v1

- Human: `yes` / Gemini: `yes`
- Temporal type: `relative_order`
- Modality: `Speech + Action (silent)`
- Gemini reason: The person visibly moves their mouth as if speaking, and subsequently forms and holds a clear thumbs-up with their right hand.
- Gemini evidence: Video shows mouth movement from 0.00s to 0.41s, followed by the right hand forming a thumbs-up at 0.83s which is held until the end of the video.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/clap_V_TP_Sp_Si_rel_ord_SpSi_v1.txt`

#### TP — Sp_Si_So_rel_ord_SoSiSp v1

- Human: `yes` / Gemini: `yes`
- Temporal type: `relative_order`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: The visible actions correctly correspond to the prompt: a right thigh slap, a right-hand thumbs-up, and speaking motion.
- Gemini evidence: The right hand slaps the thigh at 00:01.000, holds a thumbs-up pose from 00:01.833 to 00:02.917, and lip movement is visible at 00:03.000.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/clap_V_TP_Sp_Si_So_rel_ord_SoSiSp_v1.txt`

#### TN — Sp_So_rel_ord_SoSp v1

- Human: `no` / Gemini: `no`
- Temporal type: `relative_order`
- Modality: `Speech + Action (sounding)`
- Gemini reason: The person uses their left hand to slap their left thigh instead of the required right hand and right thigh, and there is no visible mouth movement for the required speech event.
- Gemini evidence: At 0.5s-1.0s, the person lifts the arm on the viewer's right (their left arm) and slaps the thigh on the viewer's right (their left thigh). The person's mouth remains closed throughout the entire video, with no speaking motion.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/clap_V_TN_Sp_So_rel_ord_SoSp_v1.txt`

#### TN — Sp_Si_So_rel_sync v1

- Human: `no` / Gemini: `no`
- Temporal type: `relative_synchronization`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: The person performs the thumbs-up and striking action with the left hand instead of the requested right hand, and the full face is not visible.
- Gemini evidence: Video inspection shows the hand on the viewer's right (the person's left hand) holding the thumbs-up and moving, while the person's right hand rests passively. Additionally, the camera framing cuts off the top half of the face.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/clap_V_TN_Sp_Si_So_rel_sync_v1.txt`

#### TN — Sp_Si_So_rel_ord_SpSoSi v1

- Human: `no` / Gemini: `no`
- Temporal type: `relative_order`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: The person performs the slap and the thumbs-up with their left hand on their left thigh, failing the explicit prompt requirement to use the right hand and right thigh.
- Gemini evidence: Starting around 2.1s, the arm on the viewer's right (the person's left arm) moves to strike the thigh and then forms the thumbs-up pose.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/clap_V_TN_Sp_Si_So_rel_ord_SpSoSi_v1.txt`

#### FP — Sp_Si_So_rel_ord_SoSpSi v1

- Human: `no` / Gemini: `yes`
- Temporal type: `relative_order`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: The visible actions match the prompt: the right hand slaps the right thigh, mouth movement corresponds to speaking, and a correct right-hand thumbs-up pose is formed and held.
- Gemini evidence: The right hand is seen striking the right thigh at 0.5s, the person's mouth moves right after, and at 1.7s the right hand forms a thumbs-up pose and holds it.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/clap_V_FP_Sp_Si_So_rel_ord_SoSpSi_v1.txt`

#### FP — Si_So_rel_ord_SoSi v1

- Human: `no` / Gemini: `yes`
- Temporal type: `relative_order`
- Modality: `Action (silent) + Action (sounding)`
- Gemini reason: The person's right hand clearly strikes the right thigh once, followed by a clear thumbs-up pose.
- Gemini evidence: The person's right hand (viewer's left) raises and strikes the right thigh at 1.00s. Afterwards, the right hand forms a closed fist with the thumb extended upwards, holding the pose from 1.87s to the end.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/clap_V_FP_Si_So_rel_ord_SoSi_v1.txt`

#### FP — Si_So_rel_ord_SiSo v1

- Human: `no` / Gemini: `yes`
- Temporal type: `relative_order`
- Modality: `Action (silent) + Action (sounding)`
- Gemini reason: Both visual actions are clearly and correctly performed by the specified body parts.
- Gemini evidence: The person forms and holds a clear right-hand thumbs-up from 00:01.000 to 00:02.500, then brings the right hand down to visibly strike the right thigh at 00:03.000.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/clap_V_FP_Si_So_rel_ord_SiSo_v1.txt`

#### FN — Si_So_rel_sync v1

- Human: `yes` / Gemini: `no`
- Temporal type: `relative_synchronization`
- Modality: `Action (silent) + Action (sounding)`
- Gemini reason: The visual event is incorrect. The prompt requires the right hand to strike the thigh while held in a thumbs-up pose as one simultaneous event without a separate lifting motion. Instead, the actor performs sequential motions: lifting the hand, forming a thumbs-up, and then lowering it to slap the thigh.
- Gemini evidence: In the video, the right hand lifts and forms a thumbs-up between 0.2s and 0.4s, and then moves down to slap the thigh at 0.5s. The pose is not held during the slap, and the actions are sequential rather than simultaneous.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/clap_V_FN_Si_So_rel_sync_v1.txt`

#### FN — Sp_Si_So_rel_sync_cnt v1

- Human: `yes` / Gemini: `no`
- Temporal type: `relative_sync_count`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: The person's mouth remains closed throughout the entire video with no visible speaking motion. Furthermore, the right hand raises the thumbs-up in the air rather than simultaneously striking the thigh.
- Gemini evidence: Video frames show the lips firmly closed from 00:00.000 to 00:05.000. The right hand performs a thumbs-up at 00:00.583 and 00:01.375 but does not strike the thigh simultaneously as required.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/clap_V_FN_Sp_Si_So_rel_sync_cnt_v1.txt`

#### FN — Sp_So_rel_ord_SpSo v1

- Human: `yes` / Gemini: `no`
- Temporal type: `relative_order`
- Modality: `Speech + Action (sounding)`
- Gemini reason: The visible slapping motion is incorrect. Instead of the right hand slapping the right thigh, the right hand crosses the body to slap the left thigh.
- Gemini evidence: From 03.000 to 03.375, the right hand (viewer's left) moves across the chest and strikes the opposite (left) thigh. This violates the prompt's requirement for the right hand to strike the right thigh.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/clap_V_FN_Sp_So_rel_ord_SpSo_v1.txt`

### AVB

#### TP — Si_So_rel_sync_cnt v1

- Human: `yes` / Gemini: `yes`
- Temporal type: `relative_sync_count`
- Modality: `Action (silent) + Action (sounding)`
- Gemini reason: The audible slap sounds are perfectly aligned with the visible thigh impacts.
- Gemini evidence: The physical strikes and the sharp slap sounds occur simultaneously at 00:00.750 and 00:02.200.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/clap_AVB_TP_Si_So_rel_sync_cnt_v1.txt`

#### TP — Sp_Si_So_rel_ord_SoSiSp v1

- Human: `yes` / Gemini: `yes`
- Temporal type: `relative_order`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: Both the sounding action and the speech event are temporally synchronized across audio and video modalities.
- Gemini evidence: The slap impact visually aligns with the slap sound at 00:01.000, and the mouth movement aligns with the spoken word 'help' at 00:03.000.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/clap_AVB_TP_Sp_Si_So_rel_ord_SoSiSp_v1.txt`

#### TP — Sp_Si_rel_ord_SiSp v1

- Human: `yes` / Gemini: `yes`
- Temporal type: `relative_order`
- Modality: `Speech + Action (silent)`
- Gemini reason: The spoken audio is correctly synchronized with the visible mouth movement.
- Gemini evidence: The audible word 'help' matches the lip articulation precisely at 2.0s.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/clap_AVB_TP_Sp_Si_rel_ord_SiSp_v1.txt`

#### TN — Sp_So_rel_ord_SoSp v1

- Human: `no` / Gemini: `no`
- Temporal type: `relative_order`
- Modality: `Speech + Action (sounding)`
- Gemini reason: The required speech components (both audio and visible mouth movement) are missing, and the visual slap action is incorrect, making binding inevaluable.
- Gemini evidence: Because the speech event is absent and the slap action occurs on the incorrect body side, the hierarchical preconditions for Audio-Visual Binding are not met.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/clap_AVB_TN_Sp_So_rel_ord_SoSp_v1.txt`

#### TN — Sp_Si_So_rel_ord_SpSoSi v1

- Human: `no` / Gemini: `no`
- Temporal type: `relative_order`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: The visual component of the sounding action and silent action is incorrect (wrong hand/side), meaning the required visual events are not met, so binding is not evaluable.
- Gemini evidence: Fails the hierarchical precondition due to the Visual Event Correctness failure.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/clap_AVB_TN_Sp_Si_So_rel_ord_SpSoSi_v1.txt`

#### TN — Sp_Si_So_rel_sync v1

- Human: `no` / Gemini: `no`
- Temporal type: `relative_synchronization`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: The visual component is incorrect, so audio-visual binding is not evaluable and fails.
- Gemini evidence: The wrong hand was used for the required visual actions, forcing a failure in visual event correctness.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/clap_AVB_TN_Sp_Si_So_rel_sync_v1.txt`

#### FP — Si_So_rel_ord_SiSo v1

- Human: `no` / Gemini: `yes`
- Temporal type: `relative_order`
- Modality: `Action (silent) + Action (sounding)`
- Gemini reason: The slap sound is perfectly synchronized with the visible impact.
- Gemini evidence: The sharp slap sound heard at 00:03.000 precisely aligns with the visual contact between the right hand and the right thigh.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/clap_AVB_FP_Si_So_rel_ord_SiSo_v1.txt`

#### FP — Sp_Si_So_rel_ord_SoSpSi v1

- Human: `no` / Gemini: `yes`
- Temporal type: `relative_order`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: The audio and visual components for both the thigh slap and the speech are correctly synchronized.
- Gemini evidence: The visual hand impact and the slap sound occur simultaneously at exactly 0.5s. The spoken word 'help' aligns precisely with the visible mouth movements around 0.7s.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/clap_AVB_FP_Sp_Si_So_rel_ord_SoSpSi_v1.txt`

#### FP — Si_So_rel_ord_SoSi v1

- Human: `no` / Gemini: `yes`
- Temporal type: `relative_order`
- Modality: `Action (silent) + Action (sounding)`
- Gemini reason: The slap sound is perfectly synchronized with the visible impact on the thigh.
- Gemini evidence: The visual contact of the hand striking the thigh and the sharp slap sound both occur exactly at 1.00s.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/clap_AVB_FP_Si_So_rel_ord_SoSi_v1.txt`

#### FN — Si_So_rel_sync v1

- Human: `yes` / Gemini: `no`
- Temporal type: `relative_synchronization`
- Modality: `Action (silent) + Action (sounding)`
- Gemini reason: The required visual component is incorrect, so audio-visual binding is not evaluable and fails by default.
- Gemini evidence: Visual Event Correctness is 'no' because the simultaneous thumbs-up and slap action is missing.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/clap_AVB_FN_Si_So_rel_sync_v1.txt`

#### FN — Sp_Si_So_rel_ord_SiSoSp v1

- Human: `yes` / Gemini: `no`
- Temporal type: `relative_order`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: Both the audio and visual components for the speech event are missing, so binding cannot be evaluated.
- Gemini evidence: No speech audio or visible lip movement is present.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/clap_AVB_FN_Sp_Si_So_rel_ord_SiSoSp_v1.txt`

#### FN — Sp_Si_rel_ord_SpSi v1

- Human: `yes` / Gemini: `no`
- Temporal type: `relative_order`
- Modality: `Speech + Action (silent)`
- Gemini reason: The audio component of the speech event is missing, so audio-visual binding cannot be evaluated and fails.
- Gemini evidence: The mouth moves between 0.00s and 0.41s, but there is no spoken audio to bind it to.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/clap_AVB_FN_Sp_Si_rel_ord_SpSi_v1.txt`

### TC_REL

#### TP — Si_So_rel_sync_cnt v1

- Human: `yes` / Gemini: `yes`
- Temporal type: `relative_sync_count`
- Modality: `Action (silent) + Action (sounding)`
- Gemini reason: The thumbs-up pose and the sounding action are properly synchronized as the hand maintains the pose while striking the thigh.
- Gemini evidence: During both impacts (00:00.750 and 00:02.200), the right hand clearly holds a thumbs-up gesture.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/clap_TC_REL_TP_Si_So_rel_sync_cnt_v1.txt`

#### TP — Sp_Si_So_rel_ord_SoSiSp v1

- Human: `yes` / Gemini: `yes`
- Temporal type: `relative_order`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: The required chronological sequence of events is strictly followed.
- Gemini evidence: The thigh slap (00:01.000) precedes the thumbs-up pose (00:01.833-00:02.917), which precedes the spoken word 'help' (00:03.000).
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/clap_TC_REL_TP_Sp_Si_So_rel_ord_SoSiSp_v1.txt`

#### TP — Sp_Si_rel_ord_SiSp v1

- Human: `yes` / Gemini: `yes`
- Temporal type: `relative_order`
- Modality: `Speech + Action (silent)`
- Gemini reason: The events occur in the requested sequence.
- Gemini evidence: The thumbs-up gesture is fully formed by 1.0s, preceding the spoken word at 2.0s.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/clap_TC_REL_TP_Sp_Si_rel_ord_SiSp_v1.txt`

#### TN — Sp_So_rel_ord_SoSp v1

- Human: `no` / Gemini: `no`
- Temporal type: `relative_order`
- Modality: `Speech + Action (sounding)`
- Gemini reason: The required relative sequence of events cannot be evaluated because the second event (speech) is entirely missing.
- Gemini evidence: The prompt requires the sounding action to be followed by the speech event, but only the sounding action (with incorrect visual laterality) occurs.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/clap_TC_REL_TN_Sp_So_rel_ord_SoSp_v1.txt`

#### TN — Sp_Si_So_rel_ord_SpSoSi v1

- Human: `no` / Gemini: `no`
- Temporal type: `relative_order`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: Hierarchical precondition not met; temporal relation cannot be evaluated because the required visual events and binding failed.
- Gemini evidence: Fails the hierarchical precondition due to Audio-Visual Binding being 'no'.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/clap_TC_REL_TN_Sp_Si_So_rel_ord_SpSoSi_v1.txt`

#### TN — Si_So_rel_sync v1

- Human: `no` / Gemini: `no`
- Temporal type: `relative_synchronization`
- Modality: `Action (silent) + Action (sounding)`
- Gemini reason: Preconditions failed; the required visual event and audio-visual binding are incorrect. Furthermore, the events are performed sequentially rather than synchronized.
- Gemini evidence: Audio-Visual Binding is 'no'.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/clap_TC_REL_TN_Si_So_rel_sync_v1.txt`

#### FP — Sp_Si_So_rel_ord_SoSpSi v1

- Human: `no` / Gemini: `yes`
- Temporal type: `relative_order`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: The events occur in the exact required relative order: thigh slap, then speech, then thumbs-up.
- Gemini evidence: The sounding action (thigh slap) occurs at 0.5s, followed by the speech ('help') at 0.7s, and finally the silent action (thumbs-up) begins at 1.7s.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/clap_TC_REL_FP_Sp_Si_So_rel_ord_SoSpSi_v1.txt`

#### FP — Si_So_rel_ord_SiSo v1

- Human: `no` / Gemini: `yes`
- Temporal type: `relative_order`
- Modality: `Action (silent) + Action (sounding)`
- Gemini reason: The events occur in the exact sequential order requested.
- Gemini evidence: The thumbs-up pose is fully completed and released before the right hand moves down to slap the thigh.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/clap_TC_REL_FP_Si_So_rel_ord_SiSo_v1.txt`

#### FP — Si_So_rel_ord_SoSi v1

- Human: `no` / Gemini: `yes`
- Temporal type: `relative_order`
- Modality: `Action (silent) + Action (sounding)`
- Gemini reason: The specified order is correctly followed.
- Gemini evidence: The sounding action (slapping the thigh) occurs first at 1.00s, and is subsequently followed by the silent action (thumbs-up pose) starting at 1.87s.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/clap_TC_REL_FP_Si_So_rel_ord_SoSi_v1.txt`

#### FN — Sp_Si_So_rel_ord_SiSoSp v1

- Human: `yes` / Gemini: `no`
- Temporal type: `relative_order`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: Preconditions failed; the sequence cannot be completed because the final speech event is missing.
- Gemini evidence: The thumbs-up and thigh-slapping actions occur in order, but the required subsequent speech event never happens.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/clap_TC_REL_FN_Sp_Si_So_rel_ord_SiSoSp_v1.txt`

#### FN — Sp_Si_rel_ord_SpSi v1

- Human: `yes` / Gemini: `no`
- Temporal type: `relative_order`
- Modality: `Speech + Action (silent)`
- Gemini reason: Audio-visual binding failed due to missing audio, so temporal relation cannot be evaluated.
- Gemini evidence: The hierarchical precondition for temporal evaluation is not met.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/clap_TC_REL_FN_Sp_Si_rel_ord_SpSi_v1.txt`

#### FN — Sp_So_rel_ord_SpSo v1

- Human: `yes` / Gemini: `no`
- Temporal type: `relative_order`
- Modality: `Speech + Action (sounding)`
- Gemini reason: Audio-visual binding failed, so temporal relation cannot be evaluated.
- Gemini evidence: Audio-visual binding is 'no'.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/clap_TC_REL_FN_Sp_So_rel_ord_SpSo_v1.txt`

### TC_COUNT

#### TP — Sp_Si_rel_ord_SiSp v1

- Human: `yes` / Gemini: `yes`
- Temporal type: `relative_order`
- Modality: `Speech + Action (silent)`
- Gemini reason: Both the gesture and speech events occur exactly once.
- Gemini evidence: No repeated actions or extra speech events are observed.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/clap_TC_COUNT_TP_Sp_Si_rel_ord_SiSp_v1.txt`

#### TN — Si_So_rel_sync v1

- Human: `no` / Gemini: `no`
- Temporal type: `relative_synchronization`
- Modality: `Action (silent) + Action (sounding)`
- Gemini reason: Preconditions failed; the required binding is incorrect. Additionally, the actor repeats the sequential actions multiple times instead of performing the target event exactly once.
- Gemini evidence: Audio-Visual Binding is 'no'. The video shows the sequential thumbs-up and slap motion occurring three times (around 0.5s, 1.5s, and 3.5s).
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/clap_TC_COUNT_TN_Si_So_rel_sync_v1.txt`

#### TN — Sp_So_rel_sync_cnt v1

- Human: `no` / Gemini: `no`
- Temporal type: `relative_sync_count`
- Modality: `Speech + Action (sounding)`
- Gemini reason: The slapping action occurs five times instead of the required exactly two times, and the speech event does not occur at all.
- Gemini evidence: Visual and audio evidence shows thigh-slaps at approximately 1.0s, 1.8s, 2.7s, 3.6s, and 4.4s, which exceeds the exact count of 2.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/clap_TC_COUNT_TN_Sp_So_rel_sync_cnt_v1.txt`

#### TN — Sp_Si_So_rel_ord_SpSoSi v1

- Human: `no` / Gemini: `no`
- Temporal type: `relative_order`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: Hierarchical precondition not met; event count cannot be evaluated because the required visual events and binding failed.
- Gemini evidence: Fails the hierarchical precondition due to Audio-Visual Binding being 'no'.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/clap_TC_COUNT_TN_Sp_Si_So_rel_ord_SpSoSi_v1.txt`

#### FP — Si_So_rel_ord_SiSo v1

- Human: `no` / Gemini: `yes`
- Temporal type: `relative_order`
- Modality: `Action (silent) + Action (sounding)`
- Gemini reason: Each required event occurs the exact requested number of times.
- Gemini evidence: The right-hand thumbs-up and the subsequent thigh slap both happen exactly once, with no spurious repetitions or extra actions.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/clap_TC_COUNT_FP_Si_So_rel_ord_SiSo_v1.txt`

#### FP — Si_So_rel_sync_cnt v1

- Human: `no` / Gemini: `yes`
- Temporal type: `relative_sync_count`
- Modality: `Action (silent) + Action (sounding)`
- Gemini reason: The synchronized thumbs-up and thigh slap action occurs exactly two times.
- Gemini evidence: The action sequence happens exactly twice (at 00:00.750 and 00:02.200) with no additional occurrences.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/clap_TC_COUNT_FP_Si_So_rel_sync_cnt_v1.txt`

#### FP — Si_So_rel_ord_SoSi v1

- Human: `no` / Gemini: `yes`
- Temporal type: `relative_order`
- Modality: `Action (silent) + Action (sounding)`
- Gemini reason: Each required event occurs exactly once, with no extra occurrences.
- Gemini evidence: There is exactly one slap and one continuous thumbs-up pose held until the end of the video, as requested.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/clap_TC_COUNT_FP_Si_So_rel_ord_SoSi_v1.txt`

#### FN — Sp_Si_rel_ord_SpSi v1

- Human: `yes` / Gemini: `no`
- Temporal type: `relative_order`
- Modality: `Speech + Action (silent)`
- Gemini reason: Audio-visual binding failed due to missing audio, so temporal count cannot be evaluated.
- Gemini evidence: The hierarchical precondition for temporal evaluation is not met.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/clap_TC_COUNT_FN_Sp_Si_rel_ord_SpSi_v1.txt`

#### FN — Sp_Si_So_rel_ord_SiSpSo v1

- Human: `yes` / Gemini: `no`
- Temporal type: `relative_order`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: The count requirement precondition fails because the required speech event does not occur.
- Gemini evidence: The speech event occurs zero times instead of the required exactly once.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/clap_TC_COUNT_FN_Sp_Si_So_rel_ord_SiSpSo_v1.txt`

#### FN — Sp_Si_rel_sync v1

- Human: `yes` / Gemini: `no`
- Temporal type: `relative_synchronization`
- Modality: `Speech + Action (silent)`
- Gemini reason: Preconditions failed; the target synchronized bundle does not occur.
- Gemini evidence: Missing speech event prevents the evaluation of the occurrence count.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/clap_TC_COUNT_FN_Sp_Si_rel_sync_v1.txt`

### CC

#### TP — Sp_So_rel_ord_SoSp v1

- Human: `yes` / Gemini: `yes`
- Temporal type: `relative_order`
- Modality: `Speech + Action (sounding)`
- Gemini reason: The video adheres to the non-core constraints regarding the scene, camera shot, people count, and absence of extra elements.
- Gemini evidence: The scene is a plain indoor room, filmed in a static medium shot with one person. There are no subtitles, background music, or extra gestures after the initial action.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/clap_CC_TP_Sp_So_rel_ord_SoSp_v1.txt`

#### TP — Sp_Si_So_rel_ord_SpSoSi v1

- Human: `yes` / Gemini: `yes`
- Temporal type: `relative_order`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: The video satisfies the scene, camera, and stillness constraints without introducing extra actions or sounds.
- Gemini evidence: The background is a plain indoor room, the camera is a static medium shot, and the final thumbs-up pose is held still until the video ends.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/clap_CC_TP_Sp_Si_So_rel_ord_SpSoSi_v1.txt`

#### TP — Sp_Si_So_rel_ord_SpSiSo v1

- Human: `yes` / Gemini: `yes`
- Temporal type: `relative_order`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: The video adheres to the scene, camera, and content constraints without introducing extra actions or speech.
- Gemini evidence: The video features a single seated person in a plain indoor room with a static medium shot. No extra words are spoken, and no non-target actions are performed.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/clap_CC_TP_Sp_Si_So_rel_ord_SpSiSo_v1.txt`

#### TN — Sp_Si_So_rel_sync_cnt v1

- Human: `no` / Gemini: `no`
- Temporal type: `relative_sync_count`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: The person performs extra unprompted hand gestures after the required actions, violating the constraint that no new actions occur after the final event.
- Gemini evidence: Both hands make an outward gesture between 00:01.750 and 00:02.167, which was not requested.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/clap_CC_TN_Sp_Si_So_rel_sync_cnt_v1.txt`

#### TN — Sp_Si_So_rel_sync v1

- Human: `no` / Gemini: `no`
- Temporal type: `relative_synchronization`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: The prompt requires the full face to be clearly visible, but the video framing cuts off the upper half of the face.
- Gemini evidence: The video is cropped around the nose, failing to show the eyes or top of the head.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/clap_CC_TN_Sp_Si_So_rel_sync_v1.txt`

#### TN — Sp_So_rel_sync v1

- Human: `no` / Gemini: `no`
- Temporal type: `relative_synchronization`
- Modality: `Speech + Action (sounding)`
- Gemini reason: The video violates the constraint requiring the person's full face and mouth to remain clearly visible.
- Gemini evidence: The framing cuts off the head entirely throughout the video.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/clap_CC_TN_Sp_So_rel_sync_v1.txt`

#### FP — Si_So_rel_sync_cnt v1

- Human: `no` / Gemini: `yes`
- Temporal type: `relative_sync_count`
- Modality: `Action (silent) + Action (sounding)`
- Gemini reason: All scene, camera, and behavioral constraints are followed, including post-event stillness.
- Gemini evidence: The video features a static medium shot in a plain room. Both hands start on the thighs, the subject resets between strikes, and remains completely still from 00:02.500 until the end of the video.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/clap_CC_FP_Si_So_rel_sync_cnt_v1.txt`

#### FP — Sp_Si_So_rel_ord_SoSpSi v1

- Human: `no` / Gemini: `yes`
- Temporal type: `relative_order`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: The video satisfies all scene, camera, and specific action constraints, including remaining still after the final event.
- Gemini evidence: The video features a static medium shot in a plain indoor room. The seated person performs no extra actions or speech, and after forming the thumbs-up, he holds the pose and remains still until the video ends.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/clap_CC_FP_Sp_Si_So_rel_ord_SoSpSi_v1.txt`

#### FP — Sp_Si_So_rel_ord_SiSoSp v1

- Human: `no` / Gemini: `yes`
- Temporal type: `relative_order`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: The video satisfies the scene, camera, and negative constraints.
- Gemini evidence: The video features a single seated person in a plain indoor room, shot in a static medium shot, with no background music, extra actions, or on-screen text.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/clap_CC_FP_Sp_Si_So_rel_ord_SiSoSp_v1.txt`

#### FN — Si_So_rel_sync v1

- Human: `yes` / Gemini: `no`
- Temporal type: `relative_synchronization`
- Modality: `Action (silent) + Action (sounding)`
- Gemini reason: The video violates the 'no separate lifting motion' constraint and the post-event stillness constraint ('no new target action occurs') by repeating the sequence multiple times.
- Gemini evidence: The actor lifts their hand to form the thumbs-up and repeats the entire sequence three times throughout the 5-second video, failing to remain still after the first event.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/clap_CC_FN_Si_So_rel_sync_v1.txt`

#### FN — Sp_So_rel_sync_cnt v1

- Human: `yes` / Gemini: `no`
- Temporal type: `relative_sync_count`
- Modality: `Speech + Action (sounding)`
- Gemini reason: The video contains extra slaps beyond the allowed two, violating the constraints against extra target actions and post-event stillness.
- Gemini evidence: The person strikes their thigh five times, continuing the action until the end of the video.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/clap_CC_FN_Sp_So_rel_sync_cnt_v1.txt`

#### FN — Sp_So_rel_ord_SpSo v1

- Human: `yes` / Gemini: `no`
- Temporal type: `relative_order`
- Modality: `Speech + Action (sounding)`
- Gemini reason: The video contains extra unprompted actions, violating the constraint that no new actions should occur.
- Gemini evidence: At 03.833 to the end of the video, the person raises their left hand high into the air, which is an unprompted extra gesture.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/clap_CC_FN_Sp_So_rel_ord_SpSo_v1.txt`

## mediapipe_whisper

### A

#### TP — Sp_Si_So_rel_ord_SoSiSp v1

- Human: `yes` / Gemini: `yes`
- Temporal type: `relative_order`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: The required audio components are present and correct. A sharp slap sound is heard, and the spoken word 'help' is distinct and intelligible.
- Gemini evidence: Slap sounds are heard at approximately 1.00s and 1.41s. Whisper ASR transcribes the single word 'help' between 2.86s and 3.50s with high confidence.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/mediapipe_whisper_A_TP_Sp_Si_So_rel_ord_SoSiSp_v1.txt`

#### TP — Sp_Si_So_rel_ord_SiSoSp v1

- Human: `yes` / Gemini: `yes`
- Temporal type: `relative_order`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: Both required audio events are correct: a sharp slap sound is heard, and the single word 'help' is clearly spoken.
- Gemini evidence: A clear slap sound is audible at 00:02.20, and the Whisper ASR correctly transcribes the word 'help' occurring from 00:03.54 to 00:04.10.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/mediapipe_whisper_A_TP_Sp_Si_So_rel_ord_SiSoSp_v1.txt`

#### TP — Sp_So_rel_ord_SpSo v1

- Human: `yes` / Gemini: `yes`
- Temporal type: `relative_order`
- Modality: `Speech + Action (sounding)`
- Gemini reason: The required speech event 'help' and the sharp slap sound are present and correct in the audio.
- Gemini evidence: Whisper detects the word 'help' at 0.00-0.34s, and a corresponding slap sound is audible later in the track.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/mediapipe_whisper_A_TP_Sp_So_rel_ord_SpSo_v1.txt`

#### FP — Sp_So_rel_sync v1

- Human: `no` / Gemini: `yes`
- Temporal type: `relative_synchronization`
- Modality: `Speech + Action (sounding)`
- Gemini reason: The required speech and sound are both present. The word 'help' is clearly spoken at the very beginning, and a sharp slap sound is heard later in the video.
- Gemini evidence: Whisper ASR and audio inspection confirm the word 'help' is spoken between 0.00s and 0.28s. A distinct slap sound is heard around 1.16s.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/mediapipe_whisper_A_FP_Sp_So_rel_sync_v1.txt`

#### FP — Sp_So_rel_ord_SoSp v1

- Human: `no` / Gemini: `yes`
- Temporal type: `relative_order`
- Modality: `Speech + Action (sounding)`
- Gemini reason: The word 'help' is clearly spoken, and a sharp slap sound is audible.
- Gemini evidence: Whisper detects 'Help' from 0.00s to 0.22s, and a distinct slap sound is heard around 1.00s.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/mediapipe_whisper_A_FP_Sp_So_rel_ord_SoSp_v1.txt`

#### FN — Sp_Si_So_rel_sync v1

- Human: `yes` / Gemini: `no`
- Temporal type: `relative_synchronization`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: The spoken word 'help' is present, but the sharp slap sound of the hand striking the thigh is completely missing from the audio track.
- Gemini evidence: Whisper detects 'Help' from 0.00s to 0.26s, and direct audio inspection confirms the speech, but there is absolutely no slap sound heard at any point in the video.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/mediapipe_whisper_A_FN_Sp_Si_So_rel_sync_v1.txt`

#### FN — Sp_Si_So_rel_ord_SoSpSi v1

- Human: `yes` / Gemini: `no`
- Temporal type: `relative_order`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: The speech 'help' is clearly audible, but the required sharp slap sound is missing when the hand contacts the thigh.
- Gemini evidence: Whisper detects speech at 0.00-0.24 seconds, but there is no distinct sharp slap sound heard around 0.50 seconds when the hand hits the thigh.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/mediapipe_whisper_A_FN_Sp_Si_So_rel_ord_SoSpSi_v1.txt`

#### FN — Sp_Si_So_rel_ord_SpSiSo v1

- Human: `yes` / Gemini: `no`
- Temporal type: `relative_order`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: The speech event 'help' is clearly audible, but the required sharp slap sound is entirely missing from the audio track.
- Gemini evidence: Whisper detects 'help' at 0.00-0.28s, which is confirmed by listening. However, the audio remains silent for the rest of the video, with no slap sound heard when the hand strikes the thigh around 4.7s.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/mediapipe_whisper_A_FN_Sp_Si_So_rel_ord_SpSiSo_v1.txt`

### V

#### TP — Sp_Si_So_rel_ord_SoSiSp v1

- Human: `yes` / Gemini: `yes`
- Temporal type: `relative_order`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: The required visual components for all events are present and correct. The video shows the right hand striking the right thigh, the right hand forming a thumbs-up pose, and visible mouth movement for speech.
- Gemini evidence: The right hand is seen striking the right thigh at 1.00s and 1.41s. A clear thumbs-up pose is held by the right hand from 1.83s to 3.00s. The person's mouth visibly moves to speak starting around 2.86s.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/mediapipe_whisper_V_TP_Sp_Si_So_rel_ord_SoSiSp_v1.txt`

#### TP — Sp_Si_So_rel_ord_SiSoSp v1

- Human: `yes` / Gemini: `yes`
- Temporal type: `relative_order`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: All required visual components are present and correct: the right hand forms a clear thumbs-up pose, the right hand strikes the right thigh, and the mouth moves visibly to speak.
- Gemini evidence: In the video, the person forms a right-hand thumbs-up from 00:00.50 to 00:01.83. The right hand then visibly strikes the right thigh at 00:02.20. Finally, visible lip motion for speaking occurs from 00:03.54 to 00:04.10.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/mediapipe_whisper_V_TP_Sp_Si_So_rel_ord_SiSoSp_v1.txt`

#### TP — Sp_Si_rel_ord_SpSi v1

- Human: `yes` / Gemini: `yes`
- Temporal type: `relative_order`
- Modality: `Speech + Action (silent)`
- Gemini reason: The person visibly moves their mouth to speak and subsequently forms and holds a clear thumbs-up gesture with their right hand.
- Gemini evidence: Video inspection shows the person's mouth moving at the start, followed by the right hand raising from the thigh to form a closed fist with the thumb extended upward at around 0.66s, holding it for the rest of the video.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/mediapipe_whisper_V_TP_Sp_Si_rel_ord_SpSi_v1.txt`

#### TN — Sp_Si_So_rel_sync v1

- Human: `no` / Gemini: `no`
- Temporal type: `relative_synchronization`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: While the speaking motion and initial thumbs-up pose are visible, the striking of the thigh is not properly executed. The hand drops but loses the thumbs-up pose before contact, violating the requirement that the pose remains clearly recognizable during the action.
- Gemini evidence: The right hand is in a thumbs-up pose until around 0.375s, after which it drops and opens up. By 0.500s, the hand is resting flat on the thigh with the thumbs-up pose entirely gone, and no distinct striking action is clearly visible.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/mediapipe_whisper_V_TN_Sp_Si_So_rel_sync_v1.txt`

#### TN — Sp_Si_rel_sync_cnt v1

- Human: `no` / Gemini: `no`
- Temporal type: `relative_sync_count`
- Modality: `Speech + Action (silent)`
- Gemini reason: The required visual action is not correctly performed. The person raises their right hand, but it does not form a recognizable thumbs-up pose (the fingers are not closed into a fist and the thumb is not clearly extended upward).
- Gemini evidence: Direct video inspection shows the right hand raised with an ambiguous, open hand shape from 0.00s to 0.50s. The hand is then lowered, and the action is not repeated.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/mediapipe_whisper_V_TN_Sp_Si_rel_sync_cnt_v1.txt`

#### TN — Sp_So_rel_sync_cnt v1

- Human: `no` / Gemini: `no`
- Temporal type: `relative_sync_count`
- Modality: `Speech + Action (sounding)`
- Gemini reason: The visible slapping motion is present, but there is no visible mouth movement for the speech.
- Gemini evidence: The person's mouth remains closed during the spoken word 'help'.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/mediapipe_whisper_V_TN_Sp_So_rel_sync_cnt_v1.txt`

#### FP — Sp_Si_So_rel_ord_SoSpSi v1

- Human: `no` / Gemini: `yes`
- Temporal type: `relative_order`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: The video correctly displays visible mouth motion for speech, the right hand contacting the right thigh, and the right hand subsequently forming and holding a thumbs-up pose.
- Gemini evidence: Mouth movement is visible at the start, the right hand makes contact with the right thigh around 0.50 seconds, and a clear right-hand thumbs-up is held starting from approximately 1.66 seconds.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/mediapipe_whisper_V_FP_Sp_Si_So_rel_ord_SoSpSi_v1.txt`

#### FP — Sp_So_rel_ord_SoSp v1

- Human: `no` / Gemini: `yes`
- Temporal type: `relative_order`
- Modality: `Speech + Action (sounding)`
- Gemini reason: The person's mouth visibly moves to form the word 'help', and the right hand is shown lifting and striking the right thigh.
- Gemini evidence: Visible mouth movement occurs from 0.00s to 0.20s. The right arm lifts starting around 0.50s, swings back, and the hand makes visible contact with the right thigh at 1.00s.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/mediapipe_whisper_V_FP_Sp_So_rel_ord_SoSp_v1.txt`

#### FP — Sp_Si_So_rel_ord_SpSoSi v1

- Human: `no` / Gemini: `yes`
- Temporal type: `relative_order`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: The person visibly speaks, performs the sounding action of slapping the right thigh, and successfully forms and holds a thumbs-up pose.
- Gemini evidence: Visible mouth movement at the start of the video. The right hand lifts and strikes the right thigh at approximately 2.4s, followed by forming a thumbs-up pose starting around 2.5s and holding it until the end of the video.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/mediapipe_whisper_V_FP_Sp_Si_So_rel_ord_SpSoSi_v1.txt`

#### FN — Sp_So_rel_sync v1

- Human: `yes` / Gemini: `no`
- Temporal type: `relative_synchronization`
- Modality: `Speech + Action (sounding)`
- Gemini reason: The prompt explicitly requires the person's full face and mouth to remain clearly visible, but the video crops out the upper half of the head and mostly obscures the mouth. This makes the visual speaking component incomplete and unclear.
- Gemini evidence: The video framing cuts off the person's head from the nose up. The mouth is barely visible at the very top edge of the frame, failing the core visual requirement for the speech event. The visual action of the right hand striking the right thigh is clearly visible around 1.16s.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/mediapipe_whisper_V_FN_Sp_So_rel_sync_v1.txt`

#### FN — Sp_Si_So_rel_sync_cnt v1

- Human: `yes` / Gemini: `no`
- Temporal type: `relative_sync_count`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: The person visibly speaks only once, and while the right hand forms a thumbs-up pose, it does not perform a clear downward striking motion onto the thigh.
- Gemini evidence: Visible mouth movement occurs only at the very beginning of the video. The right hand forms a thumbs-up but only gently lowers or gestures rather than executing a distinct slapping motion.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/mediapipe_whisper_V_FN_Sp_Si_So_rel_sync_cnt_v1.txt`

#### FN — Sp_Si_rel_sync v1

- Human: `yes` / Gemini: `no`
- Temporal type: `relative_synchronization`
- Modality: `Speech + Action (silent)`
- Gemini reason: The visual component is incorrect because the person uses the wrong hand for the requested action.
- Gemini evidence: The prompt specifies the right hand should form the thumbs-up pose, but the video shows the person's left hand (on the viewer's right) performing the action, while the right hand remains resting on the thigh.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/mediapipe_whisper_V_FN_Sp_Si_rel_sync_v1.txt`

### AVB

#### TP — Sp_Si_So_rel_ord_SoSiSp v1

- Human: `yes` / Gemini: `yes`
- Temporal type: `relative_order`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: The audio and visual components of the events are correctly temporally aligned.
- Gemini evidence: The visible impacts of the right hand on the thigh at 1.00s and 1.41s align perfectly with the audible slap sounds. The visible mouth movement from 2.86s to 3.50s perfectly matches the timing of the spoken word 'help'.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/mediapipe_whisper_AVB_TP_Sp_Si_So_rel_ord_SoSiSp_v1.txt`

#### TP — Sp_So_rel_ord_SpSo v1

- Human: `yes` / Gemini: `yes`
- Temporal type: `relative_order`
- Modality: `Speech + Action (sounding)`
- Gemini reason: The audio and visual components for both the speech and the target sounding action are correctly synchronized.
- Gemini evidence: The spoken word 'help' aligns with the visible mouth movement from 0.00-0.34s. The slap sound aligns with the right hand's impact on the thigh at ~4.25s.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/mediapipe_whisper_AVB_TP_Sp_So_rel_ord_SpSo_v1.txt`

#### TP — Sp_Si_So_rel_ord_SiSpSo v1

- Human: `yes` / Gemini: `yes`
- Temporal type: `relative_order`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: The audio and visual components of each event are correctly synchronized. The mouth movement aligns with the spoken word 'help', and the visible hand impact aligns exactly with the slap sound.
- Gemini evidence: The spoken word 'help' matches the lip movement from 0.00s to 0.22s. The audible slap at 3.04s perfectly aligns with the visible impact of the right hand on the right thigh.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/mediapipe_whisper_AVB_TP_Sp_Si_So_rel_ord_SiSpSo_v1.txt`

#### TN — Sp_So_rel_sync v1

- Human: `no` / Gemini: `no`
- Temporal type: `relative_synchronization`
- Modality: `Speech + Action (sounding)`
- Gemini reason: The visual component of the speech event is incomplete and unclear due to the cropped framing, forcing audio-visual binding to fail by hierarchical dependency.
- Gemini evidence: Because the required full face and mouth visibility is missing, the visual preconditions are not met, so binding cannot be fully evaluated.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/mediapipe_whisper_AVB_TN_Sp_So_rel_sync_v1.txt`

#### TN — Sp_Si_So_rel_sync v1

- Human: `no` / Gemini: `no`
- Temporal type: `relative_synchronization`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: The required audio and visual components for the slapping action are incorrect or missing, so binding is not evaluable.
- Gemini evidence: The required slap sound is absent, and the visual action fails to maintain the required thumbs-up pose during the downward motion.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/mediapipe_whisper_AVB_TN_Sp_Si_So_rel_sync_v1.txt`

#### TN — Sp_Si_rel_sync_cnt v1

- Human: `no` / Gemini: `no`
- Temporal type: `relative_sync_count`
- Modality: `Speech + Action (silent)`
- Gemini reason: The visual component (thumbs-up gesture) is incorrect, so audio-visual binding is not evaluable and fails.
- Gemini evidence: Visual Event Correctness is 'no' because the thumbs-up pose is missing/distorted.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/mediapipe_whisper_AVB_TN_Sp_Si_rel_sync_cnt_v1.txt`

#### FP — Sp_So_rel_ord_SoSp v1

- Human: `no` / Gemini: `yes`
- Temporal type: `relative_order`
- Modality: `Speech + Action (sounding)`
- Gemini reason: The speech audio is correctly synchronized with the visible mouth movements, and the slap sound aligns perfectly with the visual impact on the thigh.
- Gemini evidence: The speech 'help' matches the lip motion precisely at the beginning of the video, and the slap sound at 1.00s corresponds exactly to the right hand striking the right thigh.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/mediapipe_whisper_AVB_FP_Sp_So_rel_ord_SoSp_v1.txt`

#### FP — Sp_Si_So_rel_ord_SpSoSi v1

- Human: `no` / Gemini: `yes`
- Temporal type: `relative_order`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: The audio and visual components for both the speech and the sounding action are perfectly synchronized.
- Gemini evidence: The spoken word 'help' aligns with the visible mouth movements, and the slap sound is heard exactly at the moment of impact when the right hand hits the thigh at 2.41s.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/mediapipe_whisper_AVB_FP_Sp_Si_So_rel_ord_SpSoSi_v1.txt`

#### FP — Si_So_rel_ord_SiSo v1

- Human: `no` / Gemini: `yes`
- Temporal type: `relative_order`
- Modality: `Action (silent) + Action (sounding)`
- Gemini reason: The impact sound is perfectly synchronized with the visible hand-thigh contact.
- Gemini evidence: The sharp slap sound occurs exactly at 3.000s, matching the visual contact of the right hand striking the thigh.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/mediapipe_whisper_AVB_FP_Si_So_rel_ord_SiSo_v1.txt`

#### FN — Sp_Si_rel_sync v1

- Human: `yes` / Gemini: `no`
- Temporal type: `relative_synchronization`
- Modality: `Speech + Action (silent)`
- Gemini reason: The visual component of the required action is incorrect (wrong hand used), so audio-visual binding cannot be fully evaluated and fails.
- Gemini evidence: Since the required right-hand thumbs-up is absent, binding for the required events is not satisfied.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/mediapipe_whisper_AVB_FN_Sp_Si_rel_sync_v1.txt`

#### FN — Sp_Si_So_rel_sync_cnt v1

- Human: `yes` / Gemini: `no`
- Temporal type: `relative_sync_count`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: Both the required audio and visual components are missing or incorrect, so binding is not evaluable.
- Gemini evidence: The missing second speech occurrence, absent slap sound, and incomplete slap motion force this axis to fail.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/mediapipe_whisper_AVB_FN_Sp_Si_So_rel_sync_cnt_v1.txt`

#### FN — Sp_Si_So_rel_ord_SpSiSo v1

- Human: `yes` / Gemini: `no`
- Temporal type: `relative_order`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: Audio-Visual Binding is not evaluable because both the visual component (thumbs-up) and the audio component (slap sound) are incorrect or missing.
- Gemini evidence: The failure to produce the correct thumbs-up gesture and the missing slap sound force this axis to fail.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/mediapipe_whisper_AVB_FN_Sp_Si_So_rel_ord_SpSiSo_v1.txt`

### TC_REL

#### TP — Sp_Si_So_rel_ord_SoSiSp v1

- Human: `yes` / Gemini: `yes`
- Temporal type: `relative_order`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: The specified relative order of events is followed: the sounding action occurs first, followed by the silent visual action, and concluding with the speech.
- Gemini evidence: The slapping actions occur first (0.41s to 1.41s). After they are completed, the thumbs-up pose is formed and held (1.83s to 3.00s). The speech 'help' begins at 2.86s, occurring at the end of the sequence.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/mediapipe_whisper_TC_REL_TP_Sp_Si_So_rel_ord_SoSiSp_v1.txt`

#### TP — Sp_Si_rel_ord_SpSi v1

- Human: `yes` / Gemini: `yes`
- Temporal type: `relative_order`
- Modality: `Speech + Action (silent)`
- Gemini reason: The required relative order is satisfied: the speech event occurs first and ends before the thumbs-up action begins.
- Gemini evidence: The speech 'help' concludes around 0.30 seconds, and the person begins to raise their right hand for the thumbs-up gesture at roughly 0.66 seconds, correctly placing the silent action after the speech.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/mediapipe_whisper_TC_REL_TP_Sp_Si_rel_ord_SpSi_v1.txt`

#### TP — Sp_Si_So_rel_ord_SiSoSp v1

- Human: `yes` / Gemini: `yes`
- Temporal type: `relative_order`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: The events occur in the exact sequential order specified by the prompt: thumbs-up, then slapping the thigh, then saying 'help'.
- Gemini evidence: The right-hand thumbs-up is held until around 00:01.83. Following this, the thigh slap occurs at 00:02.20. Finally, the spoken word 'help' occurs from 00:03.54 to 00:04.10, confirming the correct sequence.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/mediapipe_whisper_TC_REL_TP_Sp_Si_So_rel_ord_SiSoSp_v1.txt`

#### TN — Si_So_rel_sync v1

- Human: `no` / Gemini: `no`
- Temporal type: `relative_synchronization`
- Modality: `Action (silent) + Action (sounding)`
- Gemini reason: The prompt requires the thumbs-up pose and the thigh slap to be synchronized as one simultaneous event (slapping the thigh while the hand is in a thumbs-up pose). However, the video shows them occurring sequentially: an open-palmed slap followed by a separate upward lifting motion to form the thumbs-up.
- Gemini evidence: At 0.042s and 1.042s, the hand strikes the thigh with an open palm. It is not until 0.250s and 1.250s that the hand is lifted and forms the thumbs-up pose, failing the synchronization requirement.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/mediapipe_whisper_TC_REL_TN_Si_So_rel_sync_v1.txt`

#### TN — Sp_So_rel_sync v1

- Human: `no` / Gemini: `no`
- Temporal type: `relative_synchronization`
- Modality: `Speech + Action (sounding)`
- Gemini reason: Hierarchical preconditions failed. Additionally, the speech and the hand slap are not synchronized; they occur sequentially with a significant delay.
- Gemini evidence: The speech event happens at the start of the video (0.00s - 0.28s), while the visible thigh slap and its corresponding sound do not occur until approximately 1.16s, completely violating the synchronization requirement.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/mediapipe_whisper_TC_REL_TN_Sp_So_rel_sync_v1.txt`

#### TN — Sp_So_rel_ord_SoSp v1

- Human: `no` / Gemini: `no`
- Temporal type: `relative_order`
- Modality: `Speech + Action (sounding)`
- Gemini reason: The sequence of events is reversed. The prompt requires the sounding action (slapping the thigh) to occur first, followed by the speech event ('help'), but the video shows the speech occurring before the slap.
- Gemini evidence: The person says 'help' from 0.00s to 0.22s, and then slaps the right thigh at 1.00s, failing the required relative order constraint.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/mediapipe_whisper_TC_REL_TN_Sp_So_rel_ord_SoSp_v1.txt`

#### FP — Si_So_rel_ord_SoSi v1

- Human: `no` / Gemini: `yes`
- Temporal type: `relative_order`
- Modality: `Action (silent) + Action (sounding)`
- Gemini reason: The required sequence of events is followed: the slap occurs first, followed by the thumbs-up pose.
- Gemini evidence: The thigh slap concludes around 00:01.000, after which the person transitions into the thumbs-up pose, establishing it by 00:01.917.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/mediapipe_whisper_TC_REL_FP_Si_So_rel_ord_SoSi_v1.txt`

#### FP — Si_So_rel_ord_SiSo v1

- Human: `no` / Gemini: `yes`
- Temporal type: `relative_order`
- Modality: `Action (silent) + Action (sounding)`
- Gemini reason: The relative order of events exactly matches the prompt.
- Gemini evidence: The thumbs-up pose is completed first (1.000s - 2.500s), followed by the thigh slap (3.000s).
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/mediapipe_whisper_TC_REL_FP_Si_So_rel_ord_SiSo_v1.txt`

#### FP — Sp_Si_So_rel_ord_SpSoSi v1

- Human: `no` / Gemini: `yes`
- Temporal type: `relative_order`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: The required sequence of events is strictly followed.
- Gemini evidence: Speech occurs first (0.00-0.30s), followed by the thigh slap (approx 2.4s), and finally the thumbs-up pose (2.5s onwards).
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/mediapipe_whisper_TC_REL_FP_Sp_Si_So_rel_ord_SpSoSi_v1.txt`

#### FN — Si_So_rel_sync_cnt v1

- Human: `yes` / Gemini: `no`
- Temporal type: `relative_sync_count`
- Modality: `Action (silent) + Action (sounding)`
- Gemini reason: The required audio and visual components failed, so the temporal relation of synchronization cannot be evaluated.
- Gemini evidence: The missing slap sound and visible slap action prevent the evaluation of synchronization with the thumbs-up gesture.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/mediapipe_whisper_TC_REL_FN_Si_So_rel_sync_cnt_v1.txt`

### TC_COUNT

#### TP — Sp_Si_rel_ord_SpSi v1

- Human: `yes` / Gemini: `yes`
- Temporal type: `relative_order`
- Modality: `Speech + Action (silent)`
- Gemini reason: Both the speech event and the silent visual action occur exactly once as required, with no repetitions.
- Gemini evidence: The word 'help' is spoken once, and the thumbs-up is formed and held once without any extra or repeated occurrences throughout the video.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/mediapipe_whisper_TC_COUNT_TP_Sp_Si_rel_ord_SpSi_v1.txt`

#### TP — Sp_Si_So_rel_ord_SiSpSo v1

- Human: `yes` / Gemini: `yes`
- Temporal type: `relative_order`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: Each required event occurs exactly once, with no extra repetitions.
- Gemini evidence: The person says 'help' once, forms a thumbs-up once, and slaps the thigh exactly once.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/mediapipe_whisper_TC_COUNT_TP_Sp_Si_So_rel_ord_SiSpSo_v1.txt`

#### TP — Sp_Si_rel_ord_SiSp v1

- Human: `yes` / Gemini: `yes`
- Temporal type: `relative_order`
- Modality: `Speech + Action (silent)`
- Gemini reason: Both required events occur exactly once, with no extra occurrences.
- Gemini evidence: The right-hand thumbs-up is formed once and held. The word 'help' is spoken exactly once.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/mediapipe_whisper_TC_COUNT_TP_Sp_Si_rel_ord_SiSp_v1.txt`

#### TN — Sp_So_rel_ord_SpSo v1

- Human: `no` / Gemini: `no`
- Temporal type: `relative_order`
- Modality: `Speech + Action (sounding)`
- Gemini reason: The person performs an extra, spurious slapping action with the left hand, violating the requirement that target actions occur exactly once with no extra occurrences.
- Gemini evidence: Between the required speech and the target right-hand slap, the person visibly raises their left hand (viewer's right) and slaps their left thigh around 3.12s-3.37s. The count is therefore violated by this extra action.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/mediapipe_whisper_TC_COUNT_TN_Sp_So_rel_ord_SpSo_v1.txt`

#### TN — Sp_Si_So_rel_ord_SoSiSp v1

- Human: `no` / Gemini: `no`
- Temporal type: `relative_order`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: The temporal count requirement is violated because the prompt explicitly requires the person to strike their thigh exactly once, but the action is performed twice.
- Gemini evidence: The video and audio clearly show two distinct slapping actions and sounds at 1.00s and 1.41s, failing the requirement that the right hand strikes the top of the right thigh exactly once.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/mediapipe_whisper_TC_COUNT_TN_Sp_Si_So_rel_ord_SoSiSp_v1.txt`

#### TN — Sp_Si_rel_sync_cnt v1

- Human: `no` / Gemini: `no`
- Temporal type: `relative_sync_count`
- Modality: `Speech + Action (silent)`
- Gemini reason: Preconditions failed; the visual component is incorrect. Additionally, the bundle is only attempted once instead of the required two times.
- Gemini evidence: The person only says 'help' once (0.00s-0.26s) and only raises their hand once at the beginning of the video, failing the count requirement of 2.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/mediapipe_whisper_TC_COUNT_TN_Sp_Si_rel_sync_cnt_v1.txt`

#### FP — Sp_So_rel_ord_SoSp v1

- Human: `no` / Gemini: `yes`
- Temporal type: `relative_order`
- Modality: `Speech + Action (sounding)`
- Gemini reason: Both the speech event and the sounding action occur exactly once, with no spurious repetitions.
- Gemini evidence: The word 'help' is spoken once at the start, and the right hand slaps the right thigh once at 1.00s, with no further actions or speech in the remainder of the video.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/mediapipe_whisper_TC_COUNT_FP_Sp_So_rel_ord_SoSp_v1.txt`

#### FP — Sp_Si_So_rel_ord_SiSoSp v1

- Human: `no` / Gemini: `yes`
- Temporal type: `relative_order`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: Each target event occurs exactly once, with no extra or spurious repetitions.
- Gemini evidence: The video shows exactly one thumbs-up gesture, one thigh slap, and one instance of saying 'help'.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/mediapipe_whisper_TC_COUNT_FP_Sp_Si_So_rel_ord_SiSoSp_v1.txt`

#### FP — Si_So_rel_ord_SiSo v1

- Human: `no` / Gemini: `yes`
- Temporal type: `relative_order`
- Modality: `Action (silent) + Action (sounding)`
- Gemini reason: Each required event occurs exactly once with no extra repetitions.
- Gemini evidence: The video shows one continuous thumbs-up hold and exactly one thigh slap, with no extraneous actions.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/mediapipe_whisper_TC_COUNT_FP_Si_So_rel_ord_SiSo_v1.txt`

#### FN — Sp_Si_rel_sync v1

- Human: `yes` / Gemini: `no`
- Temporal type: `relative_synchronization`
- Modality: `Speech + Action (silent)`
- Gemini reason: The required synchronized bundle does not occur.
- Gemini evidence: The visual component is incorrect and the events are disjointed temporally, so there are zero valid occurrences of the synchronized target bundle.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/mediapipe_whisper_TC_COUNT_FN_Sp_Si_rel_sync_v1.txt`

### CC

#### TP — Sp_Si_So_rel_ord_SoSiSp v1

- Human: `yes` / Gemini: `yes`
- Temporal type: `relative_order`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: The video adheres to all non-core constraints regarding the scene, camera framing, lack of extra words, and post-event stillness.
- Gemini evidence: The video uses a static medium shot in a plain indoor room. Whisper ASR confirms 'help' is the only word spoken, and the person returns to a resting position without new target actions after the speech concludes at 3.50s.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/mediapipe_whisper_CC_TP_Sp_Si_So_rel_ord_SoSiSp_v1.txt`

#### TP — Sp_So_rel_ord_SoSp v1

- Human: `yes` / Gemini: `yes`
- Temporal type: `relative_order`
- Modality: `Speech + Action (sounding)`
- Gemini reason: The video adheres to all scene, camera, starting pose, and post-event stillness constraints.
- Gemini evidence: The video is a static medium shot in a plain indoor room. The person starts with both hands resting on their thighs, and after the slap is completed, returns to a resting position and remains still for the rest of the duration.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/mediapipe_whisper_CC_TP_Sp_So_rel_ord_SoSp_v1.txt`

#### TP — Sp_Si_So_rel_ord_SiSpSo v1

- Human: `yes` / Gemini: `yes`
- Temporal type: `relative_order`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: The video satisfies all non-core constraints: the setting is a plain room in a static medium shot, the person starts seated with hands on thighs, speaks no extra words, and remains still after the final event.
- Gemini evidence: The background is a plain gray backdrop. The camera remains static. The person starts with hands on thighs, does not perform any extra actions or speech, and remains completely still after the slap at 3.04s.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/mediapipe_whisper_CC_TP_Sp_Si_So_rel_ord_SiSpSo_v1.txt`

#### TN — Sp_So_rel_sync v1

- Human: `no` / Gemini: `no`
- Temporal type: `relative_synchronization`
- Modality: `Speech + Action (sounding)`
- Gemini reason: The video fails the framing and camera constraints. The prompt requires the person's full face to remain clearly visible, but the head is heavily cropped.
- Gemini evidence: The top half of the person's head is completely outside the frame, violating the 'full face' and 'medium shot' constraints.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/mediapipe_whisper_CC_TN_Sp_So_rel_sync_v1.txt`

#### TN — Sp_Si_So_rel_ord_SoSpSi v1

- Human: `no` / Gemini: `no`
- Temporal type: `relative_order`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: The prompt requires both hands to initially rest on the knees or thighs, but the right hand is already raised in the air at the very beginning of the video.
- Gemini evidence: At 0.00 seconds, the right hand is visibly lifted instead of resting on the thigh.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/mediapipe_whisper_CC_TN_Sp_Si_So_rel_ord_SoSpSi_v1.txt`

#### TN — Sp_Si_So_rel_sync v1

- Human: `no` / Gemini: `no`
- Temporal type: `relative_synchronization`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: The video fails the starting constraint, as the person does not start with both hands resting on the knees or thighs.
- Gemini evidence: At 0.00s, the right hand is already raised in a thumbs-up pose rather than resting on the thigh as instructed.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/mediapipe_whisper_CC_TN_Sp_Si_So_rel_sync_v1.txt`

#### FP — Sp_Si_So_rel_ord_SiSoSp v1

- Human: `no` / Gemini: `yes`
- Temporal type: `relative_order`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: All non-core constraints are satisfied. The person is in a plain indoor room, shot with a static medium shot, starts with hands resting on thighs, and remains still after the final event.
- Gemini evidence: The background is plain, the camera remains still, no subtitles or background music are present, and the person stops all actions after saying 'help' at 00:04.10.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/mediapipe_whisper_CC_FP_Sp_Si_So_rel_ord_SiSoSp_v1.txt`

#### FP — Sp_Si_rel_ord_SpSi v1

- Human: `no` / Gemini: `yes`
- Temporal type: `relative_order`
- Modality: `Speech + Action (silent)`
- Gemini reason: All scene, camera, posture, and negative constraints are satisfied.
- Gemini evidence: The video features a plain indoor room, a static medium shot, and the person begins with hands on their thighs. The correct body side (right hand) is used. No extra text, speech, music, or post-event actions occur.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/mediapipe_whisper_CC_FP_Sp_Si_rel_ord_SpSi_v1.txt`

#### FP — Sp_Si_So_rel_sync_cnt v1

- Human: `no` / Gemini: `yes`
- Temporal type: `relative_sync_count`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: The video maintains the plain indoor room, static medium shot, and continuous visibility constraints without introducing extra words or sounds.
- Gemini evidence: The camera remains static, the subject's required body parts remain in frame, and no background music or extra speech is present.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/mediapipe_whisper_CC_FP_Sp_Si_So_rel_sync_cnt_v1.txt`

#### FN — Si_So_rel_sync v1

- Human: `yes` / Gemini: `no`
- Temporal type: `relative_synchronization`
- Modality: `Action (silent) + Action (sounding)`
- Gemini reason: The video violates the post-event stillness constraint, which specifies that no new target action should occur after the final event. The repeated actions break this rule.
- Gemini evidence: After the first sequence is completed around 0.4s, the person repeats the slapping and thumbs-up actions multiple times instead of remaining still.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/mediapipe_whisper_CC_FN_Si_So_rel_sync_v1.txt`

#### FN — Sp_So_rel_ord_SpSo v1

- Human: `yes` / Gemini: `no`
- Temporal type: `relative_order`
- Modality: `Speech + Action (sounding)`
- Gemini reason: The video contains an extra, unprompted slapping action, violating the constraint against extra actions/gestures.
- Gemini evidence: The person performs a slap with their left hand on their left thigh at ~3.25s, which was not requested.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/mediapipe_whisper_CC_FN_Sp_So_rel_ord_SpSo_v1.txt`

#### FN — Si_So_rel_ord_SiSo v1

- Human: `yes` / Gemini: `no`
- Temporal type: `relative_order`
- Modality: `Action (silent) + Action (sounding)`
- Gemini reason: The prompt requires the full face and mouth to be visible, but the person's head is cropped out of the frame.
- Gemini evidence: The framing only shows the person from the neck down, omitting the face entirely.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/mediapipe_whisper_CC_FN_Si_So_rel_ord_SiSo_v1.txt`

## mediapipe_clap

### A

#### TP — Sp_Si_So_rel_ord_SoSiSp v1

- Human: `yes` / Gemini: `yes`
- Temporal type: `relative_order`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: The required non-speech sound and speech event are both present and correct. A sharp slap sound is clearly audible, and the person clearly says the single word 'help' with no extra words.
- Gemini evidence: A sharp slap sound occurs at exactly 1.000s, and the spoken word 'help' is heard clearly around 3.000s.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/mediapipe_clap_A_TP_Sp_Si_So_rel_ord_SoSiSp_v1.txt`

#### TP — Sp_Si_So_rel_sync_cnt v1

- Human: `yes` / Gemini: `yes`
- Temporal type: `relative_sync_count`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: The spoken word 'help' and a sharp slap sound are both clearly audible multiple times in the audio track.
- Gemini evidence: Audio contains 'help' and a slap sound repeating approximately every second starting at 00:00.000.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/mediapipe_clap_A_TP_Sp_Si_So_rel_sync_cnt_v1.txt`

#### TP — Si_So_rel_ord_SiSo v1

- Human: `yes` / Gemini: `yes`
- Temporal type: `relative_order`
- Modality: `Action (silent) + Action (sounding)`
- Gemini reason: The required sharp slap sound is clearly audible and matches the prompt description.
- Gemini evidence: A distinct slap sound is heard at 00:03.000, supported by CLAP window similarities peaking between 2.50s and 3.50s.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/mediapipe_clap_A_TP_Si_So_rel_ord_SiSo_v1.txt`

#### TN — Sp_So_rel_ord_SoSp v1

- Human: `no` / Gemini: `no`
- Temporal type: `relative_order`
- Modality: `Speech + Action (sounding)`
- Gemini reason: A slap sound is clearly audible, but the required speech 'help' is completely missing from the audio.
- Gemini evidence: Audio contains a slap sound around 00:01.000, but there is no spoken word 'help' heard at any point in the video.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/mediapipe_clap_A_TN_Sp_So_rel_ord_SoSp_v1.txt`

#### TN — Sp_So_rel_sync v1

- Human: `no` / Gemini: `no`
- Temporal type: `relative_synchronization`
- Modality: `Speech + Action (sounding)`
- Gemini reason: The required speech 'help' is completely missing from the audio.
- Gemini evidence: A clear slap sound is heard around 1.4 seconds, but no spoken words are audible at any point in the video.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/mediapipe_clap_A_TN_Sp_So_rel_sync_v1.txt`

#### FN — Sp_Si_So_rel_ord_SiSoSp v1

- Human: `yes` / Gemini: `no`
- Temporal type: `relative_order`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: The required sharp slap sound is audible, but the required spoken word 'help' is completely absent from the audio track.
- Gemini evidence: A clear slap sound is heard at 2.0s. However, there is no speech audio present at any point in the video.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/mediapipe_clap_A_FN_Sp_Si_So_rel_ord_SiSoSp_v1.txt`

#### FN — Sp_Si_So_rel_ord_SpSiSo v1

- Human: `yes` / Gemini: `no`
- Temporal type: `relative_order`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: The required speech event 'help' is not present in the audio (no Whisper ASR transcription detected).
- Gemini evidence: No Whisper transcription evidence is available to confirm the spoken word 'help'. While CLAP shows a mild peak for 'slapping_the_thigh' near the end of the video ([4.25 - 5.00] = 0.244), the missing speech fails this axis.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/mediapipe_clap_A_FN_Sp_Si_So_rel_ord_SpSiSo_v1.txt`

#### FN — Sp_Si_rel_ord_SiSp v1

- Human: `yes` / Gemini: `no`
- Temporal type: `relative_order`
- Modality: `Speech + Action (silent)`
- Gemini reason: The required speech event 'help' is completely missing from the audio track; the video is entirely silent.
- Gemini evidence: Direct audio inspection reveals no speech or sound at any point during the video.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/mediapipe_clap_A_FN_Sp_Si_rel_ord_SiSp_v1.txt`

### V

#### TP — Sp_Si_So_rel_ord_SoSiSp v1

- Human: `yes` / Gemini: `yes`
- Temporal type: `relative_order`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: The required visual actions are clearly performed by the correct body parts. The right hand visibly strikes the right thigh, then forms a clear thumbs-up pose, and visible mouth movements accompany the speech.
- Gemini evidence: The person's right hand strikes the right thigh at 1.000s. The right hand then raises and forms a thumbs-up pose starting at 1.833s. The mouth visibly moves at 3.000s.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/mediapipe_clap_V_TP_Sp_Si_So_rel_ord_SoSiSp_v1.txt`

#### TP — Si_So_rel_sync_cnt v1

- Human: `yes` / Gemini: `yes`
- Temporal type: `relative_sync_count`
- Modality: `Action (silent) + Action (sounding)`
- Gemini reason: The person visibly forms a thumbs-up pose with his right hand and visibly strikes his right thigh with his right hand.
- Gemini evidence: A clear thumbs-up is formed around 00:00.333 and 00:01.875. The right hand makes visible contact with the right thigh around 00:00.625 and 00:02.042.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/mediapipe_clap_V_TP_Si_So_rel_sync_cnt_v1.txt`

#### TP — Sp_Si_rel_sync v1

- Human: `yes` / Gemini: `yes`
- Temporal type: `relative_synchronization`
- Modality: `Speech + Action (silent)`
- Gemini reason: The person performs the required silent action, forming and holding a thumbs-up pose with their right hand.
- Gemini evidence: Video inspection shows the person resting their hands on their thighs initially, then at 3.250s, the right hand forms a thumbs-up pose, holding it until the end of the video.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/mediapipe_clap_V_TP_Sp_Si_rel_sync_v1.txt`

#### TN — Sp_Si_rel_sync_cnt v1

- Human: `no` / Gemini: `no`
- Temporal type: `relative_sync_count`
- Modality: `Speech + Action (silent)`
- Gemini reason: The visible components of the required events are incorrect. The person's mouth remains closed, showing no articulation of the word 'help'. Furthermore, while the right hand is raised, it does not form a recognizable thumbs-up pose (the thumb is not clearly extended upward).
- Gemini evidence: Video inspection shows the mouth is entirely static. The right hand raises between 0:00-0:01 and 0:02-0:03, but the fingers form a loose grip without an upward-extended thumb.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/mediapipe_clap_V_TN_Sp_Si_rel_sync_cnt_v1.txt`

#### TN — Sp_So_rel_ord_SoSp v1

- Human: `no` / Gemini: `no`
- Temporal type: `relative_order`
- Modality: `Speech + Action (sounding)`
- Gemini reason: The visible action of the right hand slapping the right thigh is performed correctly, but there is no visible mouth movement for the required speech event.
- Gemini evidence: The right hand is seen lifting and striking the right thigh at 00:01.000, but the person's mouth remains closed for the rest of the video with no speaking motion.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/mediapipe_clap_V_TN_Sp_So_rel_ord_SoSp_v1.txt`

#### TN — Sp_So_rel_sync_cnt v1

- Human: `no` / Gemini: `no`
- Temporal type: `relative_sync_count`
- Modality: `Speech + Action (sounding)`
- Gemini reason: There is no visible speaking motion; the person's mouth remains closed for the entire duration of the video.
- Gemini evidence: Video inspection shows the person's mouth never opens to say 'help'. The visible action of the right hand slapping the right thigh is present, but the visible speech component is missing.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/mediapipe_clap_V_TN_Sp_So_rel_sync_cnt_v1.txt`

#### FP — Sp_Si_So_rel_sync v1

- Human: `no` / Gemini: `yes`
- Temporal type: `relative_synchronization`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: The visible actions are correctly performed: the person exhibits visible mouth motion for speech, forms a thumbs-up pose with the right hand, and strikes the right thigh while maintaining the pose.
- Gemini evidence: Visible mouth movement begins at 0.0s. The right hand forms a thumbs-up pose and strikes the top of the right thigh at 0.500s, with the thumbs-up clearly recognizable during the impact.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/mediapipe_clap_V_FP_Sp_Si_So_rel_sync_v1.txt`

#### FP — Si_So_rel_ord_SiSo v1

- Human: `no` / Gemini: `yes`
- Temporal type: `relative_order`
- Modality: `Action (silent) + Action (sounding)`
- Gemini reason: The required thumbs-up pose and the subsequent thigh-slapping action are both clearly visible and correctly performed by the correct body parts.
- Gemini evidence: The person's right hand forms a thumbs-up pose from 00:01.000 to 00:02.500. Afterward, the right hand strikes the top of the right thigh, making clear visible contact at 00:03.000.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/mediapipe_clap_V_FP_Si_So_rel_ord_SiSo_v1.txt`

#### FP — Si_So_rel_ord_SoSi v1

- Human: `no` / Gemini: `yes`
- Temporal type: `relative_order`
- Modality: `Action (silent) + Action (sounding)`
- Gemini reason: The video clearly displays the required visual motions: the right hand striking the thigh and the subsequent formation of a thumbs-up pose.
- Gemini evidence: The right hand makes visible downward contact with the right thigh at 1.000s. Later, a clear right-hand thumbs-up pose is formed and held from 1.875s to the end of the video.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/mediapipe_clap_V_FP_Si_So_rel_ord_SoSi_v1.txt`

#### FN — Sp_Si_So_rel_ord_SiSoSp v1

- Human: `yes` / Gemini: `no`
- Temporal type: `relative_order`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: The visible actions of holding a thumbs-up and slapping the thigh are correctly performed, but the required visible mouth and lip motion for saying 'help' is missing.
- Gemini evidence: The person forms a thumbs-up with the right hand from 0.5s to 1.8s, and then visibly slaps their right thigh around 2.0s. Following this, the person remains still and their mouth remains closed for the rest of the video, showing no visible speaking behavior.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/mediapipe_clap_V_FN_Sp_Si_So_rel_ord_SiSoSp_v1.txt`

#### FN — Sp_Si_So_rel_sync_cnt v1

- Human: `yes` / Gemini: `no`
- Temporal type: `relative_sync_count`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: The required synchronized visual actions are not correctly performed. The person never strikes their thigh while holding a thumbs-up pose.
- Gemini evidence: During the first movement (00:00.083 - 00:00.167), the right hand forms a fist rather than a thumbs-up before striking the thigh. During the second movement (00:01.000 - 00:01.500), the right hand forms a thumbs-up but remains in the air and does not strike the thigh.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/mediapipe_clap_V_FN_Sp_Si_So_rel_sync_cnt_v1.txt`

#### FN — Si_So_rel_sync v1

- Human: `yes` / Gemini: `no`
- Temporal type: `relative_synchronization`
- Modality: `Action (silent) + Action (sounding)`
- Gemini reason: The visual event does not match the strict prompt instructions. The person lifts their hand to form a thumbs-up in the air and then opens their hand to slap the thigh, rather than striking the thigh while holding the thumbs-up pose as a single synchronized event.
- Gemini evidence: In the video, the right hand forms a thumbs-up in the air around 00:00.250 to 00:00.458, then opens and strikes the thigh flat at 00:00.583. This separation of the thumbs-up and the slap violates the prompt's requirement for a simultaneous strike in a thumbs-up pose.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/mediapipe_clap_V_FN_Si_So_rel_sync_v1.txt`

### AVB

#### TP — Sp_Si_So_rel_ord_SoSiSp v1

- Human: `yes` / Gemini: `yes`
- Temporal type: `relative_order`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: Both events have correctly synchronized audio and visual components.
- Gemini evidence: The slap sound at 1.000s is perfectly aligned with the visible impact of the right hand on the right thigh. The spoken word 'help' at 3.000s aligns with the visible speaking motion.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/mediapipe_clap_AVB_TP_Sp_Si_So_rel_ord_SoSiSp_v1.txt`

#### TP — Si_So_rel_sync_cnt v1

- Human: `yes` / Gemini: `yes`
- Temporal type: `relative_sync_count`
- Modality: `Action (silent) + Action (sounding)`
- Gemini reason: The slap sounds in the audio align perfectly with the visible impacts of the hand striking the thigh.
- Gemini evidence: The visible thigh strikes at 00:00.625 and 00:02.042 temporally coincide with the slap sounds heard at 00:00.600 and 00:02.000.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/mediapipe_clap_AVB_TP_Si_So_rel_sync_cnt_v1.txt`

#### TP — Sp_So_rel_ord_SpSo v1

- Human: `yes` / Gemini: `yes`
- Temporal type: `relative_order`
- Modality: `Speech + Action (sounding)`
- Gemini reason: The audio and visual components for both events are correctly synchronized.
- Gemini evidence: The spoken audio 'help' perfectly matches the timing of the visible lip movements. Later, the sharp slap sound occurs exactly at the moment the right hand makes contact with the right thigh.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/mediapipe_clap_AVB_TP_Sp_So_rel_ord_SpSo_v1.txt`

#### TN — Sp_So_rel_sync v1

- Human: `no` / Gemini: `no`
- Temporal type: `relative_synchronization`
- Modality: `Speech + Action (sounding)`
- Gemini reason: The speech event is completely missing from both the audio and visual tracks, making audio-visual binding not evaluable.
- Gemini evidence: No speech audio and no visible speaking motion are present.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/mediapipe_clap_AVB_TN_Sp_So_rel_sync_v1.txt`

#### TN — Sp_Si_rel_sync_cnt v1

- Human: `no` / Gemini: `no`
- Temporal type: `relative_sync_count`
- Modality: `Speech + Action (silent)`
- Gemini reason: Both the required audio component (spoken word) and the required visual components (visible speaking motion, thumbs-up pose) are missing or incorrect, so binding cannot be evaluated.
- Gemini evidence: No audible speech or recognizable thumbs-up pose occurs in the video.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/mediapipe_clap_AVB_TN_Sp_Si_rel_sync_cnt_v1.txt`

#### TN — Sp_So_rel_ord_SoSp v1

- Human: `no` / Gemini: `no`
- Temporal type: `relative_order`
- Modality: `Speech + Action (sounding)`
- Gemini reason: The audio and visual components for the speech event are missing, so binding is not evaluable.
- Gemini evidence: Both the spoken word 'help' and the corresponding lip motion are absent.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/mediapipe_clap_AVB_TN_Sp_So_rel_ord_SoSp_v1.txt`

#### FP — Sp_Si_So_rel_sync v1

- Human: `no` / Gemini: `yes`
- Temporal type: `relative_synchronization`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: The audio and visual components of each respective event are correctly synchronized.
- Gemini evidence: The spoken word 'help' aligns with the visible lip movement between 0.0s and 0.2s. The slap sound is perfectly timed with the right hand's visible impact on the thigh exactly at 0.500s.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/mediapipe_clap_AVB_FP_Sp_Si_So_rel_sync_v1.txt`

#### FP — Sp_Si_So_rel_ord_SpSoSi v1

- Human: `no` / Gemini: `yes`
- Temporal type: `relative_order`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: The spoken audio aligns perfectly with the mouth movements, and the slap sound aligns exactly with the visual impact on the thigh.
- Gemini evidence: Speech audio 'help' perfectly coincides with the mouth movement from 00:00.000 to 00:00.500. The sharp slap sound is heard exactly at 00:02.417, synchronized with the visual impact of the right hand on the right thigh.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/mediapipe_clap_AVB_FP_Sp_Si_So_rel_ord_SpSoSi_v1.txt`

#### FP — Si_So_rel_ord_SoSi v1

- Human: `no` / Gemini: `yes`
- Temporal type: `relative_order`
- Modality: `Action (silent) + Action (sounding)`
- Gemini reason: The audio and visual components of the slapping event are correctly and tightly synchronized.
- Gemini evidence: The visible impact of the right hand on the right thigh occurs at 1.000s, which exactly matches the onset of the sharp slap sound.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/mediapipe_clap_AVB_FP_Si_So_rel_ord_SoSi_v1.txt`

#### FN — Sp_Si_So_rel_sync_cnt v1

- Human: `yes` / Gemini: `no`
- Temporal type: `relative_sync_count`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: The visual component of the required events is incorrect, so binding is not evaluable. Furthermore, slap sounds are heard while the hand is visibly not making contact with the thigh.
- Gemini evidence: Because the visual event correctness failed, this axis must be 'no'. Additionally, during the second occurrence (00:01.000), a slap sound is heard while the thumbs-up hand is in mid-air.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/mediapipe_clap_AVB_FN_Sp_Si_So_rel_sync_cnt_v1.txt`

#### FN — Sp_Si_So_rel_ord_SiSoSp v1

- Human: `yes` / Gemini: `no`
- Temporal type: `relative_order`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: Both the audio and visual components for the speech event 'help' are missing, so Audio-Visual Binding is not evaluable and fails by hierarchical precondition.
- Gemini evidence: While the slap sound is correctly bound to the visible thigh slap at 2.0s, the absence of both speech audio and visible mouth movement forces a failure for the speech event's binding.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/mediapipe_clap_AVB_FN_Sp_Si_So_rel_ord_SiSoSp_v1.txt`

#### FN — Sp_Si_rel_ord_SpSi v1

- Human: `yes` / Gemini: `no`
- Temporal type: `relative_order`
- Modality: `Speech + Action (silent)`
- Gemini reason: The audio and visual components for the speech event failed, so binding is not evaluable.
- Gemini evidence: Missing speech audio and unclear visual articulation prevent the evaluation of audiovisual synchronization for the speech event.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/mediapipe_clap_AVB_FN_Sp_Si_rel_ord_SpSi_v1.txt`

### TC_REL

#### TP — Sp_Si_So_rel_ord_SoSiSp v1

- Human: `yes` / Gemini: `yes`
- Temporal type: `relative_order`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: The events occur in the exact relative order required by the prompt.
- Gemini evidence: The sequence correctly follows the prompt: the right hand slaps the thigh first (1.000s), followed by the right-hand thumbs-up pose (1.833s), and finally the speech 'help' (3.000s).
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/mediapipe_clap_TC_REL_TP_Sp_Si_So_rel_ord_SoSiSp_v1.txt`

#### TP — Sp_So_rel_ord_SpSo v1

- Human: `yes` / Gemini: `yes`
- Temporal type: `relative_order`
- Modality: `Speech + Action (sounding)`
- Gemini reason: The temporal order of the events matches the sequence specified in the prompt.
- Gemini evidence: The speech event ('help') is fully completed before the person initiates the action of lifting their hand to slap their thigh, satisfying the relative order requirement.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/mediapipe_clap_TC_REL_TP_Sp_So_rel_ord_SpSo_v1.txt`

#### TN — Sp_Si_So_rel_sync v1

- Human: `no` / Gemini: `no`
- Temporal type: `relative_synchronization`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: The original prompt requires all events to occur at one synchronized moment, but they happen sequentially in the video.
- Gemini evidence: The speech event 'help' occurs and concludes between 0.0s and 0.25s, whereas the striking of the thigh and the corresponding slap sound do not occur until 0.5s, violating the synchronization constraint.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/mediapipe_clap_TC_REL_TN_Sp_Si_So_rel_sync_v1.txt`

#### TN — Sp_Si_So_rel_sync_cnt v1

- Human: `no` / Gemini: `no`
- Temporal type: `relative_sync_count`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: The audio-visual binding precondition failed, meaning the synchronized relation of the specified bundle cannot be evaluated.
- Gemini evidence: Because the visual actions are incorrect and audio-visual binding is 'no', this axis is forced to 'no'.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/mediapipe_clap_TC_REL_TN_Sp_Si_So_rel_sync_cnt_v1.txt`

#### TN — Si_So_rel_sync v1

- Human: `no` / Gemini: `no`
- Temporal type: `relative_synchronization`
- Modality: `Action (silent) + Action (sounding)`
- Gemini reason: Audio-visual binding failed, so the temporal relation cannot be evaluated. Additionally, the actions were sequential rather than synchronized.
- Gemini evidence: The thumbs-up pose and the thigh slap occur at different times (e.g., thumbs-up in the air at 00:00.375, flat-hand slap at 00:00.583) instead of being a single simultaneous event.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/mediapipe_clap_TC_REL_TN_Si_So_rel_sync_v1.txt`

#### FP — Si_So_rel_ord_SiSo v1

- Human: `no` / Gemini: `yes`
- Temporal type: `relative_order`
- Modality: `Action (silent) + Action (sounding)`
- Gemini reason: The relative order constraint is satisfied. The thumbs-up pose is completed before the thigh-slapping action begins.
- Gemini evidence: The thumbs-up is held until 00:02.500, after which the right hand moves downward, striking the thigh at 00:03.000. This perfectly follows the required sequential order.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/mediapipe_clap_TC_REL_FP_Si_So_rel_ord_SiSo_v1.txt`

#### FP — Sp_Si_So_rel_ord_SpSoSi v1

- Human: `no` / Gemini: `yes`
- Temporal type: `relative_order`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: The events occur in the correct relative sequence: speech first, followed by the slapping action, and ending with the silent thumbs-up pose.
- Gemini evidence: The speech 'help' completes around 00:00.500. The right hand slaps the right thigh at 00:02.417. Finally, the thumbs-up pose is formed immediately after the slap and held until the video ends, strictly following the required order.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/mediapipe_clap_TC_REL_FP_Sp_Si_So_rel_ord_SpSoSi_v1.txt`

#### FP — Si_So_rel_ord_SoSi v1

- Human: `no` / Gemini: `yes`
- Temporal type: `relative_order`
- Modality: `Action (silent) + Action (sounding)`
- Gemini reason: The specified relative order of the events is satisfied.
- Gemini evidence: The slapping action (occurring at 1.000s) correctly precedes the thumbs-up pose (starting at 1.875s).
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/mediapipe_clap_TC_REL_FP_Si_So_rel_ord_SoSi_v1.txt`

#### FN — Si_So_rel_sync_cnt v1

- Human: `yes` / Gemini: `no`
- Temporal type: `relative_sync_count`
- Modality: `Action (silent) + Action (sounding)`
- Gemini reason: The prompt requires the thumbs-up pose and the thigh slap to be a synchronized pair occurring at the same moment. However, the actions are performed sequentially: the person raises his hand to form a thumbs-up, then drops his hand to slap his thigh, losing the thumbs-up pose upon impact.
- Gemini evidence: In the first repetition, the thumbs-up is shown in the air around 00:00.333, followed by the thigh strike at 00:00.625 without the thumbs-up pose. This sequential pattern repeats for the second occurrence.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/mediapipe_clap_TC_REL_FN_Si_So_rel_sync_cnt_v1.txt`

#### FN — Sp_Si_So_rel_ord_SiSoSp v1

- Human: `yes` / Gemini: `no`
- Temporal type: `relative_order`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: The relation sub-axis fails because the required speech event 'help' is completely missing, violating the preconditions for temporal evaluation.
- Gemini evidence: The right-hand thumbs-up and thigh slap occur in the correct relative order, but the sequence cannot be completed because the final scheduled event (saying 'help') does not happen.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/mediapipe_clap_TC_REL_FN_Sp_Si_So_rel_ord_SiSoSp_v1.txt`

#### FN — Sp_Si_rel_ord_SiSp v1

- Human: `yes` / Gemini: `no`
- Temporal type: `relative_order`
- Modality: `Speech + Action (silent)`
- Gemini reason: The speech event fails to occur, preventing the evaluation of the required order between the thumbs-up and the speech.
- Gemini evidence: Missing audio and visual components for the speech event make it impossible to satisfy the temporal sequence.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/mediapipe_clap_TC_REL_FN_Sp_Si_rel_ord_SiSp_v1.txt`

### TC_COUNT

#### TN — Si_So_rel_ord_SoSi v1

- Human: `no` / Gemini: `no`
- Temporal type: `relative_order`
- Modality: `Action (silent) + Action (sounding)`
- Gemini reason: The prompt requires the right hand to strike the thigh exactly once, but a spurious second visual striking motion occurs.
- Gemini evidence: After the correct initial strike at 1.000s, the right hand raises to head level and performs a second rapid downward striking motion onto the lap around 1.292s, violating the strict count constraint.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/mediapipe_clap_TC_COUNT_TN_Si_So_rel_ord_SoSi_v1.txt`

#### TN — Si_So_rel_sync_cnt v1

- Human: `no` / Gemini: `no`
- Temporal type: `relative_sync_count`
- Modality: `Action (silent) + Action (sounding)`
- Gemini reason: The prompt requires the synchronized bundle (thumbs-up while slapping) to occur exactly two times. Because the actions are performed sequentially rather than simultaneously, the required synchronized bundle occurs 0 times.
- Gemini evidence: The constituent actions occur twice, but they are never synchronized as specified.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/mediapipe_clap_TC_COUNT_TN_Si_So_rel_sync_cnt_v1.txt`

#### TN — Sp_Si_So_rel_ord_SiSoSp v1

- Human: `no` / Gemini: `no`
- Temporal type: `relative_order`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: The count sub-axis fails because the required speech event does not occur, violating the requirement that each target event occurs exactly once.
- Gemini evidence: The speech event has zero occurrences, while the thumbs-up and slap events each occur once.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/mediapipe_clap_TC_COUNT_TN_Sp_Si_So_rel_ord_SiSoSp_v1.txt`

#### FP — Sp_Si_So_rel_sync v1

- Human: `no` / Gemini: `yes`
- Temporal type: `relative_synchronization`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: The required components of the target bundle occur exactly once, with no spurious repetitions.
- Gemini evidence: The person says the word 'help' exactly once and slaps the thigh exactly once; no extra speech or striking actions occur.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/mediapipe_clap_TC_COUNT_FP_Sp_Si_So_rel_sync_v1.txt`

#### FP — Si_So_rel_ord_SiSo v1

- Human: `no` / Gemini: `yes`
- Temporal type: `relative_order`
- Modality: `Action (silent) + Action (sounding)`
- Gemini reason: The required events occur exactly the specified number of times with no spurious repetitions.
- Gemini evidence: The video contains exactly one thumbs-up pose and one thigh slap. No extra sounds or actions occur after the final target event.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/mediapipe_clap_TC_COUNT_FP_Si_So_rel_ord_SiSo_v1.txt`

#### FP — Sp_Si_So_rel_ord_SoSiSp v1

- Human: `no` / Gemini: `yes`
- Temporal type: `relative_order`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: Each required event occurs exactly once, with no extra or spurious occurrences.
- Gemini evidence: There is exactly one slap, one thumbs-up pose, and one instance of the word 'help'.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/mediapipe_clap_TC_COUNT_FP_Sp_Si_So_rel_ord_SoSiSp_v1.txt`

#### FN — Sp_Si_rel_ord_SpSi v1

- Human: `yes` / Gemini: `no`
- Temporal type: `relative_order`
- Modality: `Speech + Action (silent)`
- Gemini reason: Audio and visual preconditions for the speech event failed, so event counts cannot be evaluated.
- Gemini evidence: The missing speech event means the required single occurrence of each event is not satisfied.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/mediapipe_clap_TC_COUNT_FN_Sp_Si_rel_ord_SpSi_v1.txt`

#### FN — Sp_Si_rel_sync v1

- Human: `yes` / Gemini: `no`
- Temporal type: `relative_synchronization`
- Modality: `Speech + Action (silent)`
- Gemini reason: Audio-Visual Binding is incorrect, so temporal count cannot be evaluated.
- Gemini evidence: The hierarchical precondition failed because the complete event bundle is not present.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/mediapipe_clap_TC_COUNT_FN_Sp_Si_rel_sync_v1.txt`

#### FN — Sp_Si_rel_ord_SiSp v1

- Human: `yes` / Gemini: `no`
- Temporal type: `relative_order`
- Modality: `Speech + Action (silent)`
- Gemini reason: The speech event does not occur the required one time.
- Gemini evidence: The word 'help' is never audibly spoken.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/mediapipe_clap_TC_COUNT_FN_Sp_Si_rel_ord_SiSp_v1.txt`

### CC

#### TP — Sp_Si_So_rel_ord_SoSiSp v1

- Human: `yes` / Gemini: `yes`
- Temporal type: `relative_order`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: The video satisfies all scene, camera, and specific action constraints. The setting is plain, the shot is a static medium shot, the left hand remains resting, and no extra actions occur after the final event.
- Gemini evidence: The person starts with hands on thighs, only the right hand performs the actions while the left remains still, the background is neutral, the camera remains static, and after the hand returns to the lap at 3.250s, the person stays still until the video ends.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/mediapipe_clap_CC_TP_Sp_Si_So_rel_ord_SoSiSp_v1.txt`

#### TP — Sp_Si_So_rel_ord_SpSoSi v1

- Human: `yes` / Gemini: `yes`
- Temporal type: `relative_order`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: The video satisfies all non-core constraints including setting, camera angle, posture, visibility, and post-event stillness.
- Gemini evidence: The scene is a plain indoor room with a static medium shot. One seated person faces the camera with hands initially resting on the thighs. The specified body parts are fully visible. No extra words are spoken, and no new target actions occur after the final thumbs-up pose is formed and held.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/mediapipe_clap_CC_TP_Sp_Si_So_rel_ord_SpSoSi_v1.txt`

#### TP — Sp_Si_rel_ord_SiSp v1

- Human: `yes` / Gemini: `yes`
- Temporal type: `relative_order`
- Modality: `Speech + Action (silent)`
- Gemini reason: The scene is a plain indoor room, the shot is a static medium shot, the initial pose constraints are met, and there are no extra actions or sounds.
- Gemini evidence: The video maintains the specified camera angle and scene without introducing extra elements or violating constraints.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/mediapipe_clap_CC_TP_Sp_Si_rel_ord_SiSp_v1.txt`

#### TN — Sp_Si_So_rel_sync_cnt v1

- Human: `no` / Gemini: `no`
- Temporal type: `relative_sync_count`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: The video violates constraints regarding the number of repetitions and the inclusion of extra actions and sounds.
- Gemini evidence: The prompt requires exactly two occurrences and no extra sounds/actions. However, the 'help' speech and slap sound repeat five times in a loop, and the person performs an extra open-palm gesture around 00:02.000.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/mediapipe_clap_CC_TN_Sp_Si_So_rel_sync_cnt_v1.txt`

#### TN — Sp_So_rel_sync v1

- Human: `no` / Gemini: `no`
- Temporal type: `relative_synchronization`
- Modality: `Speech + Action (sounding)`
- Gemini reason: The prompt requires the person's full face to remain clearly visible, but the framing crops out the eyes and upper head.
- Gemini evidence: The top half of the person's face is cut off by the top edge of the frame throughout the entire video.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/mediapipe_clap_CC_TN_Sp_So_rel_sync_v1.txt`

#### TN — Sp_Si_So_rel_ord_SoSpSi v1

- Human: `no` / Gemini: `no`
- Temporal type: `relative_order`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: The prompt requires both hands to initially rest on the knees or thighs, but the right hand is already raised in mid-air at the start.
- Gemini evidence: At 00:00.000, the right hand is visibly lifted above the leg, initiating the slap motion instead of resting.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/mediapipe_clap_CC_TN_Sp_Si_So_rel_ord_SoSpSi_v1.txt`

#### FP — Sp_Si_So_rel_sync v1

- Human: `no` / Gemini: `yes`
- Temporal type: `relative_synchronization`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: The video satisfies all non-core constraints, including the setting, camera shot, starting posture, speech restriction, and post-action stillness.
- Gemini evidence: The video is set in a plain indoor room with a static medium shot. The person starts with hands resting on their thighs. Only the single word 'help' is spoken, and no further actions occur after the slap at 0.5s.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/mediapipe_clap_CC_FP_Sp_Si_So_rel_sync_v1.txt`

#### FP — Si_So_rel_sync_cnt v1

- Human: `no` / Gemini: `yes`
- Temporal type: `relative_sync_count`
- Modality: `Action (silent) + Action (sounding)`
- Gemini reason: The video satisfies the scene, camera, and actor constraints. There are no extraneous actions, speech, or music, and the actor remains still after the final action.
- Gemini evidence: The video is a static medium shot of one seated person in a plain room. Both hands start on the thighs, and no actions occur after the second thigh slap.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/mediapipe_clap_CC_FP_Si_So_rel_sync_cnt_v1.txt`

#### FP — Sp_Si_So_rel_ord_SiSoSp v1

- Human: `no` / Gemini: `yes`
- Temporal type: `relative_order`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: The video complies with all scene, camera, and negative constraints.
- Gemini evidence: The video features a single seated person in a plain indoor room captured in a static medium shot. The person starts with hands resting on their thighs. There are no subtitles, background music, extra actions, or extra sounds present.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/mediapipe_clap_CC_FP_Sp_Si_So_rel_ord_SiSoSp_v1.txt`

#### FN — Si_So_rel_ord_SoSi v1

- Human: `yes` / Gemini: `no`
- Temporal type: `relative_order`
- Modality: `Action (silent) + Action (sounding)`
- Gemini reason: The video contains a salient, unprompted action that breaks the expected clean execution of the actions.
- Gemini evidence: Between the required slap and thumbs-up events, the person's right hand wildly flails up to the side of the head (1.083s-1.208s) before striking the lap again, introducing an extra gesture not requested by the prompt.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/mediapipe_clap_CC_FN_Si_So_rel_ord_SoSi_v1.txt`

#### FN — Si_So_rel_ord_SiSo v1

- Human: `yes` / Gemini: `no`
- Temporal type: `relative_order`
- Modality: `Action (silent) + Action (sounding)`
- Gemini reason: The framing of the video violates the requirement that the person's full face must be visible.
- Gemini evidence: The top half of the person's head, including the eyes and forehead, is cropped out of the top of the frame throughout the video (corroborated by negative y-coordinates for the nose in the MediaPipe data).
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/mediapipe_clap_CC_FN_Si_So_rel_ord_SiSo_v1.txt`

#### FN — Sp_Si_So_rel_ord_SpSiSo v1

- Human: `yes` / Gemini: `no`
- Temporal type: `relative_order`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: The video contains extra unprompted actions and lacks post-event stillness.
- Gemini evidence: The person raises and lowers their right hand multiple times (e.g., around 02.500-03.500 and 04.200-04.600) rather than following the strict single sequence requested, violating the constraint of no extra gestures.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/mediapipe_clap_CC_FN_Sp_Si_So_rel_ord_SpSiSo_v1.txt`

## whisper_clap

### A

#### TP — Sp_Si_So_rel_ord_SpSiSo v1

- Human: `yes` / Gemini: `yes`
- Temporal type: `relative_order`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: The speech event 'help' and the sharp slap sound are both clearly present in the audio track.
- Gemini evidence: Whisper detects 'help' at 0.00-0.28s, and a clear slap sound is heard around 4.5s, consistent with CLAP similarities.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/whisper_clap_A_TP_Sp_Si_So_rel_ord_SpSiSo_v1.txt`

#### TP — Sp_Si_So_rel_ord_SoSiSp v1

- Human: `yes` / Gemini: `yes`
- Temporal type: `relative_order`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: Both required audio events are correct. A sharp slap sound is heard, and the word 'help' is clearly spoken.
- Gemini evidence: A slap sound is audible around 0.9 seconds. Whisper detects the word 'help' between 2.86 and 3.50 seconds.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/whisper_clap_A_TP_Sp_Si_So_rel_ord_SoSiSp_v1.txt`

#### TP — Sp_Si_So_rel_sync v1

- Human: `yes` / Gemini: `yes`
- Temporal type: `relative_synchronization`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: The speech 'help' and a sharp slap sound are both present and clearly audible in the track.
- Gemini evidence: The word 'help' is heard between 0.00s and 0.25s (matching Whisper transcripts), followed by a clear slap sound around 0.45s.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/whisper_clap_A_TP_Sp_Si_So_rel_sync_v1.txt`

#### FP — Sp_So_rel_ord_SoSp v1

- Human: `no` / Gemini: `yes`
- Temporal type: `relative_order`
- Modality: `Speech + Action (sounding)`
- Gemini reason: The required speech ('help') and the required sharp slap sound are both clearly audible.
- Gemini evidence: Whisper ASR transcribes 'Help.' at 0.00-0.22s, and a distinct slap sound is heard around 1.0s.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/whisper_clap_A_FP_Sp_So_rel_ord_SoSp_v1.txt`

#### FP — Sp_So_rel_sync v1

- Human: `no` / Gemini: `yes`
- Temporal type: `relative_synchronization`
- Modality: `Speech + Action (sounding)`
- Gemini reason: The speech 'help' and the slap sound are both present in the audio.
- Gemini evidence: Whisper detects 'Help' from 0.00s to 0.28s. A distinct slap sound is heard around 1.41s.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/whisper_clap_A_FP_Sp_So_rel_sync_v1.txt`

#### FN — Sp_Si_So_rel_sync_cnt v1

- Human: `yes` / Gemini: `no`
- Temporal type: `relative_sync_count`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: The speech 'help' occurs only once instead of twice, and the required thigh slap sound is completely absent.
- Gemini evidence: Whisper detects 'help' only at 0.00-0.22s. CLAP scores show no strong evidence of a slap sound, and none can be heard in the audio.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/whisper_clap_A_FN_Sp_Si_So_rel_sync_cnt_v1.txt`

### V

#### TP — Sp_Si_So_rel_ord_SiSpSo v1

- Human: `yes` / Gemini: `yes`
- Temporal type: `relative_order`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: The person forms a clear right-handed thumbs-up, moves their mouth to speak, and visibly strikes their right thigh with their right hand.
- Gemini evidence: The video shows the mouth moving at the start, followed by the right hand forming a thumbs-up from 0.66s to 2.50s, and then striking the right thigh at 3.00s.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/whisper_clap_V_TP_Sp_Si_So_rel_ord_SiSpSo_v1.txt`

#### TP — Sp_Si_So_rel_ord_SiSoSp v1

- Human: `yes` / Gemini: `yes`
- Temporal type: `relative_order`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: The person visibly performs a right-hand thumbs-up, a right-hand strike to the right thigh, and visible speaking motion.
- Gemini evidence: Thumbs-up pose is held from 0.45s to 1.95s, the right hand strikes the thigh at 2.25s, and the mouth moves at 3.54s to 4.10s.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/whisper_clap_V_TP_Sp_Si_So_rel_ord_SiSoSp_v1.txt`

#### TP — Sp_Si_So_rel_ord_SoSiSp v1

- Human: `yes` / Gemini: `yes`
- Temporal type: `relative_order`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: All required visual events are correct. The right hand strikes the right thigh, forms a clear thumbs-up, and the mouth visibly moves to speak.
- Gemini evidence: The right hand slaps the thigh making contact at 1.0s, forms a thumbs-up from 1.7s to 2.8s, and the mouth moves at 2.8s.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/whisper_clap_V_TP_Sp_Si_So_rel_ord_SoSiSp_v1.txt`

#### TN — Sp_So_rel_ord_SoSp v1

- Human: `no` / Gemini: `no`
- Temporal type: `relative_order`
- Modality: `Speech + Action (sounding)`
- Gemini reason: The visible slap action is present, but the person's mouth remains completely closed with no visible speaking motion when the speech is heard.
- Gemini evidence: Video inspection shows the right hand slapping the right thigh at 1.0s, but the lips do not move during the spoken word 'help' from 0.00s to 0.22s.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/whisper_clap_V_TN_Sp_So_rel_ord_SoSp_v1.txt`

#### TN — Sp_So_rel_sync_cnt v1

- Human: `no` / Gemini: `no`
- Temporal type: `relative_sync_count`
- Modality: `Speech + Action (sounding)`
- Gemini reason: The visible slapping action is performed with the wrong hand and on the wrong body side.
- Gemini evidence: The video shows the hand on the viewer's right (the person's left hand) repeatedly lifting and striking the left thigh at 1.00s, 2.00s, 3.00s, and 4.00s. The person's right hand remains resting on the right thigh, contradicting the prompt's requirement for the right hand to strike the right thigh.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/whisper_clap_V_TN_Sp_So_rel_sync_cnt_v1.txt`

#### TN — Sp_Si_So_rel_sync v1

- Human: `no` / Gemini: `no`
- Temporal type: `relative_synchronization`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: The person uses their left hand instead of the required right hand for the thumbs-up and slapping actions. Additionally, the full face is not visible.
- Gemini evidence: The hand on the viewer's right (the person's left hand) performs the thumbs-up and strikes the thigh. The video frame also crops out the top half of the person's face.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/whisper_clap_V_TN_Sp_Si_So_rel_sync_v1.txt`

#### FP — Si_So_rel_ord_SoSi v1

- Human: `no` / Gemini: `yes`
- Temporal type: `relative_order`
- Modality: `Action (silent) + Action (sounding)`
- Gemini reason: The actor correctly performs a visible right-hand strike to the right thigh, followed by a clear right-hand thumbs-up pose.
- Gemini evidence: The right hand is raised and strikes the right thigh at 1.00s. Subsequently, the right hand forms a thumbs-up pose at 1.83s and holds it.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/whisper_clap_V_FP_Si_So_rel_ord_SoSi_v1.txt`

#### FP — Sp_Si_So_rel_ord_SpSoSi v1

- Human: `no` / Gemini: `yes`
- Temporal type: `relative_order`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: The person's mouth moves appropriately for speech, the right hand strikes the right thigh, and then forms a clear thumbs-up pose.
- Gemini evidence: Visible lip movement at the start, hand impacts thigh at 2.41s, and a thumbs-up is formed and held from 2.75s to the end.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/whisper_clap_V_FP_Sp_Si_So_rel_ord_SpSoSi_v1.txt`

#### FP — Si_So_rel_ord_SiSo v1

- Human: `no` / Gemini: `yes`
- Temporal type: `relative_order`
- Modality: `Action (silent) + Action (sounding)`
- Gemini reason: The person's right hand visibly forms a clear thumbs-up pose, holds it, and subsequently strikes the right thigh.
- Gemini evidence: Video shows the right hand forming a thumbs-up between 0.6s and 2.5s, then striking the thigh at 3.0s.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/whisper_clap_V_FP_Si_So_rel_ord_SiSo_v1.txt`

#### FN — Sp_Si_So_rel_ord_SpSiSo v1

- Human: `yes` / Gemini: `no`
- Temporal type: `relative_order`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: The person fails to perform the required thumbs-up action; the right hand is raised but remains open and relaxed instead of forming a closed fist with the thumb extended.
- Gemini evidence: Video inspection from 03:00 to 04:00 shows the right hand raised with open fingers, never forming a thumbs-up pose, before proceeding to slap the thigh.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/whisper_clap_V_FN_Sp_Si_So_rel_ord_SpSiSo_v1.txt`

#### FN — Sp_So_rel_sync v1

- Human: `yes` / Gemini: `no`
- Temporal type: `relative_synchronization`
- Modality: `Speech + Action (sounding)`
- Gemini reason: The person's head and face are completely cropped out of the frame, making it impossible to observe the required visible mouth and lip motion for the speech event.
- Gemini evidence: The video framing shows only the torso and legs throughout the entire duration; the face is never visible.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/whisper_clap_V_FN_Sp_So_rel_sync_v1.txt`

#### FN — Sp_Si_So_rel_sync_cnt v1

- Human: `yes` / Gemini: `no`
- Temporal type: `relative_sync_count`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: The person forms a thumbs-up pose but never strikes their thigh; the required visible slapping action is entirely missing.
- Gemini evidence: Video shows the right hand raising into a thumbs-up pose twice (at 0.00s and 1.00s) but it never strikes the thigh.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/whisper_clap_V_FN_Sp_Si_So_rel_sync_cnt_v1.txt`

### AVB

#### TP — Sp_Si_So_rel_ord_SiSpSo v1

- Human: `yes` / Gemini: `yes`
- Temporal type: `relative_order`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: Both the speech and the slap action are correctly synchronized with their respective visual movements.
- Gemini evidence: The audible word 'help' aligns with the visible mouth movements at the beginning, and the slap sound aligns precisely with the right hand hitting the thigh at 3.00s.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/whisper_clap_AVB_TP_Sp_Si_So_rel_ord_SiSpSo_v1.txt`

#### TP — Sp_Si_So_rel_ord_SoSiSp v1

- Human: `yes` / Gemini: `yes`
- Temporal type: `relative_order`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: The audio and visual components for both sounding and speech events are perfectly synchronized.
- Gemini evidence: The slap sound at 0.9s perfectly aligns with the visible hand impact on the thigh. The spoken word 'help' from 2.86s to 3.50s aligns with the visible mouth movements.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/whisper_clap_AVB_TP_Sp_Si_So_rel_ord_SoSiSp_v1.txt`

#### TP — Sp_So_rel_ord_SpSo v1

- Human: `yes` / Gemini: `yes`
- Temporal type: `relative_order`
- Modality: `Speech + Action (sounding)`
- Gemini reason: Both the speech and the slapping actions are correctly synchronized with their corresponding audio.
- Gemini evidence: The audible 'help' aligns with the visible mouth movements at the beginning, and the slap sounds perfectly match the moments of physical impact at 3.12s and 4.04s.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/whisper_clap_AVB_TP_Sp_So_rel_ord_SpSo_v1.txt`

#### TN — Sp_So_rel_sync v1

- Human: `no` / Gemini: `no`
- Temporal type: `relative_synchronization`
- Modality: `Speech + Action (sounding)`
- Gemini reason: The visual component for the speech event is missing (face not visible), so binding cannot be evaluated.
- Gemini evidence: Audio-Visual Binding requires both audio and visual components to be correct. Since the mouth is not visible, this axis automatically fails.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/whisper_clap_AVB_TN_Sp_So_rel_sync_v1.txt`

#### TN — Sp_Si_So_rel_sync v1

- Human: `no` / Gemini: `no`
- Temporal type: `relative_synchronization`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: Visual event correctness failed because the wrong hand was used and the face was cropped, so audio-visual binding is not evaluable.
- Gemini evidence: The person's left hand is used instead of the right hand, violating the visual requirement and causing binding to fail by default.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/whisper_clap_AVB_TN_Sp_Si_So_rel_sync_v1.txt`

#### TN — Sp_So_rel_ord_SoSp v1

- Human: `no` / Gemini: `no`
- Temporal type: `relative_order`
- Modality: `Speech + Action (sounding)`
- Gemini reason: Because the visual component for the speech event is absent (no lip movement), audio-visual binding fails.
- Gemini evidence: The audible speech at 0.00-0.22s lacks any corresponding visible articulation in the video.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/whisper_clap_AVB_TN_Sp_So_rel_ord_SoSp_v1.txt`

#### FP — Sp_Si_So_rel_ord_SpSoSi v1

- Human: `no` / Gemini: `yes`
- Temporal type: `relative_order`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: The audio and visual components of the speech and slap events are correctly synchronized.
- Gemini evidence: Speech audio matches lip motion perfectly (0.00-0.30s), and the slap sound coincides precisely with the visual impact on the thigh at 2.41s.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/whisper_clap_AVB_FP_Sp_Si_So_rel_ord_SpSoSi_v1.txt`

#### FP — Si_So_rel_ord_SoSi v1

- Human: `no` / Gemini: `yes`
- Temporal type: `relative_order`
- Modality: `Action (silent) + Action (sounding)`
- Gemini reason: The slap sound is perfectly synchronized with the visible impact of the hand on the thigh.
- Gemini evidence: The sharp slap sound occurs exactly at 1.00s, which matches the visual frame where the right hand contacts the right thigh.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/whisper_clap_AVB_FP_Si_So_rel_ord_SoSi_v1.txt`

#### FP — Si_So_rel_ord_SiSo v1

- Human: `no` / Gemini: `yes`
- Temporal type: `relative_order`
- Modality: `Action (silent) + Action (sounding)`
- Gemini reason: The visual impact of the hand striking the thigh is properly synchronized with the audible slap sound.
- Gemini evidence: The visible contact on the thigh and the sharp slap sound both occur precisely at 3.0s.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/whisper_clap_AVB_FP_Si_So_rel_ord_SiSo_v1.txt`

#### FN — Sp_Si_So_rel_ord_SiSoSp v1

- Human: `yes` / Gemini: `no`
- Temporal type: `relative_order`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: The slap sound and the visible slapping motion are temporally disconnected.
- Gemini evidence: The right hand visibly strikes the thigh at 2.25s, but the slap sound is not heard until 3.00s, while the person is sitting completely still.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/whisper_clap_AVB_FN_Sp_Si_So_rel_ord_SiSoSp_v1.txt`

#### FN — Sp_Si_So_rel_sync_cnt v1

- Human: `yes` / Gemini: `no`
- Temporal type: `relative_sync_count`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: Both the audio and visual components of the thigh slap are missing, and the speech event is missing its second occurrence, so binding is not evaluable.
- Gemini evidence: Audio and visual preconditions failed.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/whisper_clap_AVB_FN_Sp_Si_So_rel_sync_cnt_v1.txt`

#### FN — Sp_Si_So_rel_ord_SpSiSo v1

- Human: `yes` / Gemini: `no`
- Temporal type: `relative_order`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: The visual component for the thumbs-up event is incorrect, so audio-visual binding is not evaluable and fails by default.
- Gemini evidence: Missing thumbs-up visual action forces this axis to 'no'.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/whisper_clap_AVB_FN_Sp_Si_So_rel_ord_SpSiSo_v1.txt`

### TC_REL

#### TP — Sp_Si_So_rel_ord_SoSiSp v1

- Human: `yes` / Gemini: `yes`
- Temporal type: `relative_order`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: The required relative order is satisfied. The thigh slap occurs first, followed by the thumbs-up, and finally the speech.
- Gemini evidence: The slap is completed by 1.0s, the thumbs-up is held between 1.7s and 2.8s, and the speech starts at 2.86s.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/whisper_clap_TC_REL_TP_Sp_Si_So_rel_ord_SoSiSp_v1.txt`

#### TP — Sp_Si_rel_ord_SiSp v1

- Human: `yes` / Gemini: `yes`
- Temporal type: `relative_order`
- Modality: `Speech + Action (silent)`
- Gemini reason: The visual action is completed before the speech begins, satisfying the required relative order.
- Gemini evidence: The right-hand thumbs-up is formed and held starting around 1.00s, and the speech event 'help' occurs afterward, beginning at 1.87s.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/whisper_clap_TC_REL_TP_Sp_Si_rel_ord_SiSp_v1.txt`

#### TP — Sp_So_rel_ord_SpSo v1

- Human: `yes` / Gemini: `yes`
- Temporal type: `relative_order`
- Modality: `Speech + Action (sounding)`
- Gemini reason: The required relative order is satisfied, as the speech event is completed before the slapping action begins.
- Gemini evidence: The speech 'help' occurs from 0.00-0.34s, and the right hand starts to lift for the slap only after 3.0s.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/whisper_clap_TC_REL_TP_Sp_So_rel_ord_SpSo_v1.txt`

#### TN — Sp_So_rel_ord_SoSp v1

- Human: `no` / Gemini: `no`
- Temporal type: `relative_order`
- Modality: `Speech + Action (sounding)`
- Gemini reason: Fails hierarchical preconditions due to the missing visual speech component. Furthermore, the observed order is reversed compared to the prompt.
- Gemini evidence: The prompt requires the slap to occur first, followed by the speech. In the video, the speech is heard at 0.00s, before the slap at 1.0s.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/whisper_clap_TC_REL_TN_Sp_So_rel_ord_SoSp_v1.txt`

#### TN — Sp_So_rel_sync v1

- Human: `no` / Gemini: `no`
- Temporal type: `relative_synchronization`
- Modality: `Speech + Action (sounding)`
- Gemini reason: Audio-Visual Binding failed, so temporal relation cannot be evaluated. Additionally, the speech and slap events are not synchronized.
- Gemini evidence: Speech occurs at 0.00s-0.28s, while the visible slap and sound occur around 1.41s, violating the synchronization requirement.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/whisper_clap_TC_REL_TN_Sp_So_rel_sync_v1.txt`

#### TN — Sp_Si_So_rel_sync v1

- Human: `no` / Gemini: `no`
- Temporal type: `relative_synchronization`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: Audio-visual binding failed, so temporal relation cannot be satisfied. Moreover, the required events are sequential rather than synchronized.
- Gemini evidence: The speech 'help' and upward hand movement occur first (0.00s - 0.25s), and the slap occurs afterward (0.45s), failing the synchronization requirement.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/whisper_clap_TC_REL_TN_Sp_Si_So_rel_sync_v1.txt`

#### FP — Si_So_rel_ord_SoSi v1

- Human: `no` / Gemini: `yes`
- Temporal type: `relative_order`
- Modality: `Action (silent) + Action (sounding)`
- Gemini reason: The events occur in the exact required relative order: the thigh slap happens first, followed by the thumbs-up pose.
- Gemini evidence: The sounding slap occurs at 1.00s, and the silent thumbs-up pose is formed at 1.83s, satisfying the order requirement.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/whisper_clap_TC_REL_FP_Si_So_rel_ord_SoSi_v1.txt`

#### FP — Sp_Si_So_rel_ord_SpSoSi v1

- Human: `no` / Gemini: `yes`
- Temporal type: `relative_order`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: The events occur in the exact specified relative sequence without overlap.
- Gemini evidence: The speech finishes by 0.30s, the thigh slap occurs at 2.41s, followed sequentially by the thumbs-up pose starting at 2.75s.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/whisper_clap_TC_REL_FP_Sp_Si_So_rel_ord_SpSoSi_v1.txt`

#### FP — Si_So_rel_ord_SiSo v1

- Human: `no` / Gemini: `yes`
- Temporal type: `relative_order`
- Modality: `Action (silent) + Action (sounding)`
- Gemini reason: The ordered sequence of events is correctly executed as specified.
- Gemini evidence: The thumbs-up pose is completed first (0.6s to 2.5s), followed by the thigh slap at 3.0s.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/whisper_clap_TC_REL_FP_Si_So_rel_ord_SiSo_v1.txt`

#### FN — Sp_Si_So_rel_ord_SiSoSp v1

- Human: `yes` / Gemini: `no`
- Temporal type: `relative_order`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: Audio-Visual Binding failed for the slapping event, so temporal relation cannot be satisfied.
- Gemini evidence: The slap event is temporally fragmented, making relation evaluation fail as a downward cascade.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/whisper_clap_TC_REL_FN_Sp_Si_So_rel_ord_SiSoSp_v1.txt`

#### FN — Si_So_rel_sync_cnt v1

- Human: `yes` / Gemini: `no`
- Temporal type: `relative_sync_count`
- Modality: `Action (silent) + Action (sounding)`
- Gemini reason: The thumbs-up and thigh slap are performed sequentially rather than simultaneously.
- Gemini evidence: The person raises their hand to chest level to form a thumbs-up, then brings it down to slap the thigh, rather than striking the thigh while maintaining the pose.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/whisper_clap_TC_REL_FN_Si_So_rel_sync_cnt_v1.txt`

### TC_COUNT

#### TP — Sp_Si_So_rel_ord_SiSpSo v1

- Human: `yes` / Gemini: `yes`
- Temporal type: `relative_order`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: Each required event (thumbs-up, speech, and slap) occurs exactly once with no repetitions.
- Gemini evidence: The video displays one instance of the word 'help', one thumbs-up, and one slap.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/whisper_clap_TC_COUNT_TP_Sp_Si_So_rel_ord_SiSpSo_v1.txt`

#### TP — Sp_Si_rel_ord_SiSp v1

- Human: `yes` / Gemini: `yes`
- Temporal type: `relative_order`
- Modality: `Speech + Action (silent)`
- Gemini reason: Both the thumbs-up action and the speech event occur exactly once, with no spurious occurrences.
- Gemini evidence: The video displays a single thumbs-up action and a single utterance of 'help'.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/whisper_clap_TC_COUNT_TP_Sp_Si_rel_ord_SiSp_v1.txt`

#### TP — Sp_Si_rel_ord_SpSi v1

- Human: `yes` / Gemini: `yes`
- Temporal type: `relative_order`
- Modality: `Speech + Action (silent)`
- Gemini reason: Each required event occurs exactly once without spurious repetitions.
- Gemini evidence: The word 'help' is spoken once, and the thumbs-up is formed and held once for the remainder of the video.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/whisper_clap_TC_COUNT_TP_Sp_Si_rel_ord_SpSi_v1.txt`

#### TN — Sp_Si_rel_sync_cnt v1

- Human: `no` / Gemini: `no`
- Temporal type: `relative_sync_count`
- Modality: `Speech + Action (silent)`
- Gemini reason: Preconditions failed. Additionally, the required synchronized bundle does not occur the requested 2 times.
- Gemini evidence: The audio event 'help' only occurs once (0.00-0.26), and the visual action is performed with the wrong hand.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/whisper_clap_TC_COUNT_TN_Sp_Si_rel_sync_cnt_v1.txt`

#### TN — Sp_So_rel_ord_SpSo v1

- Human: `no` / Gemini: `no`
- Temporal type: `relative_order`
- Modality: `Speech + Action (sounding)`
- Gemini reason: The prompt specifies the person should slap the thigh exactly once, but the video shows two distinct slapping actions.
- Gemini evidence: The person strikes their right thigh with their right hand at 3.12s, then raises their hand and strikes it a second time at 4.04s.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/whisper_clap_TC_COUNT_TN_Sp_So_rel_ord_SpSo_v1.txt`

#### TN — Sp_So_rel_ord_SoSp v1

- Human: `no` / Gemini: `no`
- Temporal type: `relative_order`
- Modality: `Speech + Action (sounding)`
- Gemini reason: Fails hierarchical preconditions due to the missing visual speech component.
- Gemini evidence: Because visual speech is missing, the count evaluation cannot be fully satisfied.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/whisper_clap_TC_COUNT_TN_Sp_So_rel_ord_SoSp_v1.txt`

#### FP — Sp_Si_So_rel_ord_SpSoSi v1

- Human: `no` / Gemini: `yes`
- Temporal type: `relative_order`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: Each required event occurs exactly once, with no spurious occurrences.
- Gemini evidence: The video contains a single utterance of 'help', one clear thigh slap, and one sustained thumbs-up.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/whisper_clap_TC_COUNT_FP_Sp_Si_So_rel_ord_SpSoSi_v1.txt`

#### FP — Sp_Si_So_rel_ord_SoSiSp v1

- Human: `no` / Gemini: `yes`
- Temporal type: `relative_order`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: Each required event occurs exactly once, as specified.
- Gemini evidence: There is exactly one thigh slap, one thumbs-up gesture, and one utterance of the word 'help'.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/whisper_clap_TC_COUNT_FP_Sp_Si_So_rel_ord_SoSiSp_v1.txt`

#### FP — Si_So_rel_ord_SoSi v1

- Human: `no` / Gemini: `yes`
- Temporal type: `relative_order`
- Modality: `Action (silent) + Action (sounding)`
- Gemini reason: Each required event occurs exactly once with no extra or spurious occurrences.
- Gemini evidence: There is only one slap and one thumbs-up pose in the video.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/whisper_clap_TC_COUNT_FP_Si_So_rel_ord_SoSi_v1.txt`

#### FN — Sp_Si_rel_sync v1

- Human: `yes` / Gemini: `no`
- Temporal type: `relative_synchronization`
- Modality: `Speech + Action (silent)`
- Gemini reason: Because the events are not synchronized, the required synchronized bundle occurs zero times.
- Gemini evidence: The temporal offset between the speech (0.00s-0.32s) and the action (3.25s-5.00s) means the specified simultaneous event bundle is absent.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/whisper_clap_TC_COUNT_FN_Sp_Si_rel_sync_v1.txt`

### CC

#### TP — Si_So_rel_ord_SoSi v1

- Human: `yes` / Gemini: `yes`
- Temporal type: `relative_order`
- Modality: `Action (silent) + Action (sounding)`
- Gemini reason: The video complies with all constraints: a single seated person in a plain indoor room, static medium shot, no extra actions or sounds, and stillness after the final event.
- Gemini evidence: The shot is a static medium shot in a plain room. After the thumbs-up pose is formed at 1.83s, the person holds the pose without any additional actions.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/whisper_clap_CC_TP_Si_So_rel_ord_SoSi_v1.txt`

#### TP — Sp_Si_So_rel_ord_SoSiSp v1

- Human: `yes` / Gemini: `yes`
- Temporal type: `relative_order`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: The video complies with all constraints, including the scene, camera shot, starting position, and lack of extra actions or speech.
- Gemini evidence: The subject is in a plain indoor room, shot in a static medium shot. They start with hands on thighs, speak no extra words, and remain still after the final event. No text or extra sounds are present.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/whisper_clap_CC_TP_Sp_Si_So_rel_ord_SoSiSp_v1.txt`

#### TP — Sp_Si_So_rel_ord_SpSiSo v1

- Human: `yes` / Gemini: `yes`
- Temporal type: `relative_order`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: The video satisfies the scene, camera, single-person, and post-event stillness constraints without introducing extra speech or background music.
- Gemini evidence: The setting is a plain indoor room, the shot is static medium, only one person is present, only the word 'help' is spoken, and the person remains still after the final slap.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/whisper_clap_CC_TP_Sp_Si_So_rel_ord_SpSiSo_v1.txt`

#### TN — Sp_So_rel_sync v1

- Human: `no` / Gemini: `no`
- Temporal type: `relative_synchronization`
- Modality: `Speech + Action (sounding)`
- Gemini reason: The prompt explicitly requires the person's full face, mouth, and upper body to remain clearly visible, which is violated by the camera framing.
- Gemini evidence: The head is cropped out of the video entirely, violating the specified scene constraints.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/whisper_clap_CC_TN_Sp_So_rel_sync_v1.txt`

#### TN — Sp_Si_So_rel_sync_cnt v1

- Human: `no` / Gemini: `no`
- Temporal type: `relative_sync_count`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: The person performs additional unprompted open-palm gestures after the target actions, violating the post-event stillness constraint.
- Gemini evidence: Video shows the person making open-palm gestures with both hands starting around 1.79s.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/whisper_clap_CC_TN_Sp_Si_So_rel_sync_cnt_v1.txt`

#### TN — Sp_Si_So_rel_sync v1

- Human: `no` / Gemini: `no`
- Temporal type: `relative_synchronization`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: The video violates the prompt's camera and framing constraints, as the full face is not clearly visible.
- Gemini evidence: The top half of the person's head and face is cut off by the top edge of the frame throughout the video.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/whisper_clap_CC_TN_Sp_Si_So_rel_sync_v1.txt`

#### FP — Sp_Si_So_rel_ord_SiSoSp v1

- Human: `no` / Gemini: `yes`
- Temporal type: `relative_order`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: The scene, framing, starting pose, and other constraints are met, and no extra actions occur after the final event.
- Gemini evidence: The video shows a single seated person in a plain room in a static medium shot, with the requested anatomy visible. The person remains still after saying 'help'.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/whisper_clap_CC_FP_Sp_Si_So_rel_ord_SiSoSp_v1.txt`

#### FP — Sp_Si_rel_sync_cnt v1

- Human: `no` / Gemini: `yes`
- Temporal type: `relative_sync_count`
- Modality: `Speech + Action (silent)`
- Gemini reason: The scene, camera, and initial pose constraints are satisfied without any prohibited background music or on-screen subtitles.
- Gemini evidence: The video features a static medium shot of a seated person in a plain indoor room, starting with hands resting on thighs.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/whisper_clap_CC_FP_Sp_Si_rel_sync_cnt_v1.txt`

#### FP — Sp_Si_So_rel_ord_SoSpSi v1

- Human: `no` / Gemini: `yes`
- Temporal type: `relative_order`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: The video maintains the required plain room setting, static medium shot, and post-event stillness without extra speech or background sounds.
- Gemini evidence: The scene and camera setup match the prompt, both hands start on the thighs, and the person holds the final pose with no further actions.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/whisper_clap_CC_FP_Sp_Si_So_rel_ord_SoSpSi_v1.txt`

#### FN — Sp_So_rel_ord_SpSo v1

- Human: `yes` / Gemini: `no`
- Temporal type: `relative_order`
- Modality: `Speech + Action (sounding)`
- Gemini reason: The prompt dictates that no new target action occurs after the final event, but the person performs an extra slapping action.
- Gemini evidence: After the first complete slap at 3.12s, the person repeats the target action with a second slap at 4.04s, violating the post-event stillness constraint.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/whisper_clap_CC_FN_Sp_So_rel_ord_SpSo_v1.txt`

#### FN — Sp_So_rel_sync_cnt v1

- Human: `yes` / Gemini: `no`
- Temporal type: `relative_sync_count`
- Modality: `Speech + Action (sounding)`
- Gemini reason: The video contains extra slapping actions and fails the post-event stillness constraint.
- Gemini evidence: The person performs four slapping motions instead of the required two, and does not remain still after the required events are supposed to conclude.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/whisper_clap_CC_FN_Sp_So_rel_sync_cnt_v1.txt`

#### FN — Si_So_rel_sync v1

- Human: `yes` / Gemini: `no`
- Temporal type: `relative_synchronization`
- Modality: `Action (silent) + Action (sounding)`
- Gemini reason: The target actions repeat multiple times, violating the constraint that no new target action should occur after the final event.
- Gemini evidence: Additional lifting and slapping motions occur repeatedly after the initial sequence.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/whisper_clap_CC_FN_Si_So_rel_sync_v1.txt`

## all_tools

### A

#### TP — Sp_Si_So_rel_ord_SpSiSo v1

- Human: `yes` / Gemini: `yes`
- Temporal type: `relative_order`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: The word 'help' is clearly spoken at the beginning of the video, and a sharp slap sound is clearly audible near the end.
- Gemini evidence: Audio analysis and Whisper ASR confirm the word 'help' from 0.00s to 0.28s. A distinct slap sound is heard around 4.75s, which is also supported by CLAP sliding-window similarities for 'slapping_the_thigh' peaking at the end of the video.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/all_tools_A_TP_Sp_Si_So_rel_ord_SpSiSo_v1.txt`

#### TP — Sp_So_rel_ord_SpSo v1

- Human: `yes` / Gemini: `yes`
- Temporal type: `relative_order`
- Modality: `Speech + Action (sounding)`
- Gemini reason: The spoken word 'help' is clearly audible at the beginning of the video, and a distinct slap sound is heard later.
- Gemini evidence: Whisper detects 'help' from 0.00s to 0.34s. A clear slap sound is audible at approximately 4.1s, which is also supported by CLAP similarity peaks for 'slapping_the_thigh' in the 3.50s to 4.50s windows.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/all_tools_A_TP_Sp_So_rel_ord_SpSo_v1.txt`

#### TP — Sp_Si_rel_sync_cnt v1

- Human: `yes` / Gemini: `yes`
- Temporal type: `relative_sync_count`
- Modality: `Speech + Action (silent)`
- Gemini reason: The required speech event 'help' is present and clearly spoken in the audio.
- Gemini evidence: Whisper ASR transcribes the word 'help' between 0.00 and 0.26 seconds, and direct audio inspection confirms it is clearly audible.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/all_tools_A_TP_Sp_Si_rel_sync_cnt_v1.txt`

#### TN — Sp_So_rel_sync v1

- Human: `no` / Gemini: `no`
- Temporal type: `relative_synchronization`
- Modality: `Speech + Action (sounding)`
- Gemini reason: The required speech 'help' is completely absent from the audio track. Although a slap sound is audible, the lack of speech makes the audio events incorrect.
- Gemini evidence: A sharp slap sound is heard around 1.00s, but there is no audible speech anywhere in the video.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/all_tools_A_TN_Sp_So_rel_sync_v1.txt`

#### FP — Sp_So_rel_ord_SoSp v1

- Human: `no` / Gemini: `yes`
- Temporal type: `relative_order`
- Modality: `Speech + Action (sounding)`
- Gemini reason: The spoken word 'help' and the sharp thigh slap sound are both clearly audible in the audio track.
- Gemini evidence: Whisper detects 'Help' at 0.00-0.22s, and a clear slap sound is heard at approximately 1.04s.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/all_tools_A_FP_Sp_So_rel_ord_SoSp_v1.txt`

#### FN — Sp_So_rel_sync_cnt v1

- Human: `yes` / Gemini: `no`
- Temporal type: `relative_sync_count`
- Modality: `Speech + Action (sounding)`
- Gemini reason: The audio is missing the required second instance of the word 'help' and lacks the sharp slap sounds entirely.
- Gemini evidence: Whisper ASR detects 'help' only once between 0.00s and 0.28s. Direct audio inspection confirms no slap sounds are audible throughout the video.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/all_tools_A_FN_Sp_So_rel_sync_cnt_v1.txt`

#### FN — Sp_Si_So_rel_ord_SoSpSi v1

- Human: `yes` / Gemini: `no`
- Temporal type: `relative_order`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: The speech 'help' is heard, but the required sharp slap sound is entirely missing from the audio.
- Gemini evidence: Whisper detects 'Help' at 0.00-0.24s, but listening to the audio confirms there is no sharp slap sound present at any point.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/all_tools_A_FN_Sp_Si_So_rel_ord_SoSpSi_v1.txt`

#### FN — Si_So_rel_sync v1

- Human: `yes` / Gemini: `no`
- Temporal type: `relative_synchronization`
- Modality: `Action (silent) + Action (sounding)`
- Gemini reason: The required sharp slap sound is missing from the audio track.
- Gemini evidence: CLAP scores for 'slapping_the_thigh' remain very low throughout, and negative anchors like 'silence' are high, confirming the absence of a slap sound.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/all_tools_A_FN_Si_So_rel_sync_v1.txt`

### V

#### TP — Sp_So_rel_ord_SpSo v1

- Human: `yes` / Gemini: `yes`
- Temporal type: `relative_order`
- Modality: `Speech + Action (sounding)`
- Gemini reason: The person visibly speaks at the start, and later correctly lifts their right hand to slap their right thigh.
- Gemini evidence: The video shows the person's mouth moving from 0.00s to 0.3s. The person then raises their right hand and brings it down onto their right thigh, making visible contact at 4.1s. MediaPipe also tracks the right wrist moving upwards and then down, while the left hand remains stationary.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/all_tools_V_TP_Sp_So_rel_ord_SpSo_v1.txt`

#### TP — Sp_Si_So_rel_sync_cnt v1

- Human: `yes` / Gemini: `yes`
- Temporal type: `relative_sync_count`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: The video contains visible mouth movement for speech, a clearly formed thumbs-up pose with the right hand, and visible strikes to the right thigh by the right hand.
- Gemini evidence: The person's mouth visibly moves at the beginning of the video, a clear right-hand thumbs-up pose is shown at 00:01.125, and the right hand slaps the thigh at 00:00.125 and 00:02.208.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/all_tools_V_TP_Sp_Si_So_rel_sync_cnt_v1.txt`

#### TP — Sp_Si_So_rel_ord_SoSiSp v1

- Human: `yes` / Gemini: `yes`
- Temporal type: `relative_order`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: The required visual actions (slapping the thigh, a thumbs-up pose, and speaking) are clearly visible and correctly performed.
- Gemini evidence: The person's right hand raises and visibly strikes the right thigh at 00:01.000. The right hand then forms a clear thumbs-up pose from 00:01.875 to 00:03.000. Following that, the person's mouth clearly moves to articulate the word 'help'.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/all_tools_V_TP_Sp_Si_So_rel_ord_SoSiSp_v1.txt`

#### TN — Sp_Si_So_rel_ord_SoSpSi v1

- Human: `no` / Gemini: `no`
- Temporal type: `relative_order`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: The visual actions are incorrect. The person uses their left hand instead of the requested right hand, and the left hand performs a waving motion rather than a clear thigh strike.
- Gemini evidence: Video inspection and MediaPipe tracking show the person's right arm (viewer's left) remains stationary on the thigh throughout the video. The person's left arm (viewer's right) raises up and down between 0.00s and 0.50s without striking the thigh, and then forms a thumbs-up pose at 1.50s.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/all_tools_V_TN_Sp_Si_So_rel_ord_SoSpSi_v1.txt`

#### TN — Sp_Si_So_rel_sync v1

- Human: `no` / Gemini: `no`
- Temporal type: `relative_synchronization`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: The visible thumbs-up pose is missing. While the person speaks and slaps their thigh, they do not form a recognizable thumbs-up pose when raising their hand.
- Gemini evidence: The video shows the person's mouth moving for speech and the right hand lifting before striking the thigh. However, during the hand raise (0.25s - 0.41s), the hand is clenched or blurred without the thumb extended upward as required.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/all_tools_V_TN_Sp_Si_So_rel_sync_v1.txt`

#### TN — Sp_So_rel_sync_cnt v1

- Human: `no` / Gemini: `no`
- Temporal type: `relative_sync_count`
- Modality: `Speech + Action (sounding)`
- Gemini reason: The visible speaking motion occurs only once instead of the required twice.
- Gemini evidence: The person's mouth visibly moves to speak only at the very beginning of the video. Two right-hand slap motions are visible (impacts around 0.8s and 1.6s), but they occur without any accompanying visible speaking motion.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/all_tools_V_TN_Sp_So_rel_sync_cnt_v1.txt`

#### FP — Sp_Si_rel_sync_cnt v1

- Human: `no` / Gemini: `yes`
- Temporal type: `relative_sync_count`
- Modality: `Speech + Action (silent)`
- Gemini reason: The visual components of the events are present: the person's right hand forms a thumbs-up pose and the mouth visibly moves to speak.
- Gemini evidence: Video inspection shows the right hand in a recognizable thumbs-up pose from 0.00 to 0.66 seconds, accompanied by clear mouth and lip movement.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/all_tools_V_FP_Sp_Si_rel_sync_cnt_v1.txt`

#### FP — Si_So_rel_ord_SiSo v1

- Human: `no` / Gemini: `yes`
- Temporal type: `relative_order`
- Modality: `Action (silent) + Action (sounding)`
- Gemini reason: The right hand clearly forms a thumbs-up pose, holds it, and then strikes the right thigh.
- Gemini evidence: The video shows the right hand raising and forming a thumbs-up from roughly 0.6s to 1.0s, holding it until 2.1s, and then moving downward to make visible contact with the right thigh at 3.0s.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/all_tools_V_FP_Si_So_rel_ord_SiSo_v1.txt`

#### FP — Sp_Si_So_rel_ord_SpSoSi v1

- Human: `no` / Gemini: `yes`
- Temporal type: `relative_order`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: The visible actions match the prompt: speaking mouth motion, a visible right-hand strike to the right thigh, and a clear right-hand thumbs-up pose.
- Gemini evidence: Video shows lip movement at 0.00-0.30s, the right hand striking the right thigh at 2.3s, and forming a thumbs-up pose starting around 2.7s and holding it.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/all_tools_V_FP_Sp_Si_So_rel_ord_SpSoSi_v1.txt`

#### FN — Sp_So_rel_sync v1

- Human: `yes` / Gemini: `no`
- Temporal type: `relative_synchronization`
- Modality: `Speech + Action (sounding)`
- Gemini reason: The person does not exhibit clear visible mouth or lip motion for speaking the word 'help'. The right hand does perform a visible strike on the right thigh, but the missing speech motion fails the overall visual correctness.
- Gemini evidence: The person's mouth slightly opens at the very beginning (0.00s - 0.12s) but without clear speaking motion. The right hand visibly lifts and strikes the right thigh, making contact around 1.41s.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/all_tools_V_FN_Sp_So_rel_sync_v1.txt`

#### FN — Sp_Si_So_rel_ord_SpSiSo v1

- Human: `yes` / Gemini: `no`
- Temporal type: `relative_order`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: The person fails to perform the required thumbs-up action, instead raising their right hand with an open palm and extended fingers before the slap.
- Gemini evidence: The video shows the person visibly mouthing 'help' at the start and later slapping their right thigh with their right hand at 4.66s. However, between 3.00s and 4.00s, the raised right hand has its fingers fully extended rather than forming the required closed-fist thumbs-up pose.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/all_tools_V_FN_Sp_Si_So_rel_ord_SpSiSo_v1.txt`

#### FN — Sp_Si_rel_sync v1

- Human: `yes` / Gemini: `no`
- Temporal type: `relative_synchronization`
- Modality: `Speech + Action (silent)`
- Gemini reason: The required visual component is incorrect because the person performs the thumbs-up pose using their left hand rather than the requested right hand.
- Gemini evidence: Video inspection shows the visible speaking motion at the beginning, but the thumbs-up action starting around 3.25s is performed by the person's left hand (viewer's right side) while the right hand remains resting on the thigh.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/all_tools_V_FN_Sp_Si_rel_sync_v1.txt`

### AVB

#### TP — Sp_Si_So_rel_sync_cnt v1

- Human: `yes` / Gemini: `yes`
- Temporal type: `relative_sync_count`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: The audio components are correctly bound to their respective visual actions: the speech aligns with the mouth movement, and the initial slap sound aligns with the visible thigh strike.
- Gemini evidence: The spoken word 'help' matches the mouth movement around 00:00.083, and the initial slap sound coincides with the first right-hand strike on the thigh at the same timestamp.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/all_tools_AVB_TP_Sp_Si_So_rel_sync_cnt_v1.txt`

#### TP — Sp_So_rel_ord_SpSo v1

- Human: `yes` / Gemini: `yes`
- Temporal type: `relative_order`
- Modality: `Speech + Action (sounding)`
- Gemini reason: Both events are correctly bound: the visible lip movement aligns with the spoken word 'help', and the visible thigh slap precisely aligns with the slap sound.
- Gemini evidence: The speech audio (0.00s-0.34s) perfectly aligns with the visible speaking motion. The sharp slap sound at 4.1s occurs exactly at the moment the right hand strikes the thigh in the video.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/all_tools_AVB_TP_Sp_So_rel_ord_SpSo_v1.txt`

#### TP — Sp_Si_So_rel_ord_SoSiSp v1

- Human: `yes` / Gemini: `yes`
- Temporal type: `relative_order`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: The audio and visual components of both the sounding action and the speech event are temporally aligned.
- Gemini evidence: The visible impact of the right hand on the thigh occurs exactly at the time of the slap sound at 00:01.000. The visible mouth movement corresponds perfectly with the speech audio 'help' between 00:03.000 and 00:03.500.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/all_tools_AVB_TP_Sp_Si_So_rel_ord_SoSiSp_v1.txt`

#### TN — Sp_So_rel_sync v1

- Human: `no` / Gemini: `no`
- Temporal type: `relative_synchronization`
- Modality: `Speech + Action (sounding)`
- Gemini reason: The binding is not evaluable for speech because both the audio and visual components are missing. Furthermore, the binding for the slapping action fails because the audible slap sound occurs approximately 0.4 seconds before the visible hand strike.
- Gemini evidence: The audible slap sound is clearly heard at 1.00s, but the visible impact of the right hand striking the thigh does not occur until 1.41s.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/all_tools_AVB_TN_Sp_So_rel_sync_v1.txt`

#### TN — Sp_Si_So_rel_sync v1

- Human: `no` / Gemini: `no`
- Temporal type: `relative_synchronization`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: Because the visual component of the thumbs-up event is missing/incorrect, audio-visual binding cannot be fully evaluated and must fail.
- Gemini evidence: Although the speech aligns with the visible mouth movement (0.00s - 0.25s) and the slap sound aligns with the hand striking the thigh (around 0.45s), the required visual thumbs-up gesture is absent, failing the precondition for binding evaluation.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/all_tools_AVB_TN_Sp_Si_So_rel_sync_v1.txt`

#### TN — Sp_So_rel_sync_cnt v1

- Human: `no` / Gemini: `no`
- Temporal type: `relative_sync_count`
- Modality: `Speech + Action (sounding)`
- Gemini reason: Both the audio and visual components of the required events are incomplete or missing (no slap sounds, only one speech instance), so full audio-visual binding cannot be evaluated.
- Gemini evidence: Missing slap sound and missing second spoken 'help' fail the preconditions for evaluating binding.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/all_tools_AVB_TN_Sp_So_rel_sync_cnt_v1.txt`

#### FP — Sp_Si_rel_sync_cnt v1

- Human: `no` / Gemini: `yes`
- Temporal type: `relative_sync_count`
- Modality: `Speech + Action (silent)`
- Gemini reason: The audio and visual components of the single occurrence are correctly bound, with the spoken word temporally and causally aligned with the mouth movement and the thumbs-up gesture.
- Gemini evidence: The spoken word 'help' (0.00-0.26s) occurs exactly while the mouth is visibly moving and the right hand is holding the thumbs-up pose.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/all_tools_AVB_FP_Sp_Si_rel_sync_cnt_v1.txt`

#### FP — Si_So_rel_ord_SiSo v1

- Human: `no` / Gemini: `yes`
- Temporal type: `relative_order`
- Modality: `Action (silent) + Action (sounding)`
- Gemini reason: The slap sound is perfectly synchronized with the visible impact of the hand on the thigh.
- Gemini evidence: The visual contact at 3.0 seconds exactly matches the sharp slap sound heard at the same time.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/all_tools_AVB_FP_Si_So_rel_ord_SiSo_v1.txt`

#### FP — Sp_Si_So_rel_ord_SpSoSi v1

- Human: `no` / Gemini: `yes`
- Temporal type: `relative_order`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: Both the speech and the slap action are correctly synchronized with their respective audio tracks.
- Gemini evidence: Lip movement corresponds precisely to the word 'help' (0.00-0.30s), and the visible hand impact at 2.3s aligns exactly with the sharp slap sound.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/all_tools_AVB_FP_Sp_Si_So_rel_ord_SpSoSi_v1.txt`

#### FN — Sp_Si_rel_sync v1

- Human: `yes` / Gemini: `no`
- Temporal type: `relative_synchronization`
- Modality: `Speech + Action (silent)`
- Gemini reason: The visual component of the thumbs-up event is incorrect (wrong hand), so audio-visual binding is not evaluable and must be marked 'no'.
- Gemini evidence: As established in Visual Event Correctness, the correct right-hand thumbs-up is missing. Furthermore, the speech and the left-hand thumbs-up are entirely disconnected.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/all_tools_AVB_FN_Sp_Si_rel_sync_v1.txt`

#### FN — Sp_Si_So_rel_ord_SpSiSo v1

- Human: `yes` / Gemini: `no`
- Temporal type: `relative_order`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: The required visual component for the thumbs-up action is incorrect, so audio-visual binding cannot be fully evaluated.
- Gemini evidence: Because Visual Event Correctness fails for the thumbs-up event, this axis must be marked 'no' according to the hierarchical dependency.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/all_tools_AVB_FN_Sp_Si_So_rel_ord_SpSiSo_v1.txt`

#### FN — Si_So_rel_sync v1

- Human: `yes` / Gemini: `no`
- Temporal type: `relative_synchronization`
- Modality: `Action (silent) + Action (sounding)`
- Gemini reason: Both the required audio and visual components are missing or incorrect, making binding not evaluable.
- Gemini evidence: Neither the thigh-slap motion nor the sharp slap sound occurs.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/all_tools_AVB_FN_Si_So_rel_sync_v1.txt`

### TC_REL

#### TP — Sp_So_rel_ord_SpSo v1

- Human: `yes` / Gemini: `yes`
- Temporal type: `relative_order`
- Modality: `Speech + Action (sounding)`
- Gemini reason: The relative order is satisfied: the speech event occurs first, followed by the sounding action event.
- Gemini evidence: The speech event ('help') concludes by 0.34s, and the thigh slap occurs afterward at approximately 4.1s, fulfilling the required sequence.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/all_tools_TC_REL_TP_Sp_So_rel_ord_SpSo_v1.txt`

#### TP — Sp_Si_So_rel_ord_SoSiSp v1

- Human: `yes` / Gemini: `yes`
- Temporal type: `relative_order`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: The required sequential order of events is successfully followed without overlap.
- Gemini evidence: The events occur in strict sequence: first the slap (00:00.000 - 00:01.000), then the thumbs-up pose (00:01.875 - 00:03.000), and finally the speech 'help' (00:03.000 - 00:03.500).
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/all_tools_TC_REL_TP_Sp_Si_So_rel_ord_SoSiSp_v1.txt`

#### TP — Sp_Si_rel_ord_SpSi v1

- Human: `yes` / Gemini: `yes`
- Temporal type: `relative_order`
- Modality: `Speech + Action (silent)`
- Gemini reason: The required order is clearly satisfied: the person speaks first, and only after the speech ends do they perform the thumbs-up.
- Gemini evidence: The speech event concludes around 0.30 seconds. The right-hand thumbs-up begins its motion at 0.66 seconds, well after the speech has finished, fulfilling the sequence.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/all_tools_TC_REL_TP_Sp_Si_rel_ord_SpSi_v1.txt`

#### TN — Sp_Si_So_rel_sync_cnt v1

- Human: `no` / Gemini: `no`
- Temporal type: `relative_sync_count`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: The requested events are not synchronized as required. The speech and the first thigh strike occur together, but the right hand does not form a thumbs-up pose during this time. The thumbs-up occurs entirely separately.
- Gemini evidence: At 00:00.083, the speech and slap occur with a loosely open hand, not a thumbs-up. The thumbs-up is formed sequentially later at 00:01.125 without any accompanying speech or slap. A second open-hand slap happens at 00:02.208 without speech or a thumbs-up.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/all_tools_TC_REL_TN_Sp_Si_So_rel_sync_cnt_v1.txt`

#### TN — Sp_Si_So_rel_sync v1

- Human: `no` / Gemini: `no`
- Temporal type: `relative_synchronization`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: The precondition for temporal relation evaluation failed due to the missing visual event. Furthermore, the events are performed sequentially rather than synchronously.
- Gemini evidence: The prompt requires the speech, thumbs-up, and thigh slap to occur at one synchronized moment. In the video, the speech 'help' happens first (0.00s - 0.25s), the hand is raised afterward (0.25s - 0.41s), and the slap happens last (0.45s - 0.50s).
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/all_tools_TC_REL_TN_Sp_Si_So_rel_sync_v1.txt`

#### TN — Sp_Si_So_rel_ord_SiSpSo v1

- Human: `no` / Gemini: `no`
- Temporal type: `relative_order`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: The sequence of events is incorrect. The prompt requires the thumbs-up pose to be completed before the speech 'help', but the video shows the person speaking first, followed by the thumbs-up.
- Gemini evidence: The video sequence is: 1) saying 'help' at 0.00s, 2) forming the thumbs-up pose at 0.83s, and 3) slapping the thigh at 3.00s. The required order was thumbs-up, then speech, then slap.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/all_tools_TC_REL_TN_Sp_Si_So_rel_ord_SiSpSo_v1.txt`

#### FP — Sp_Si_rel_sync_cnt v1

- Human: `no` / Gemini: `yes`
- Temporal type: `relative_sync_count`
- Modality: `Speech + Action (silent)`
- Gemini reason: The single occurrence of the speech and visual action is correctly synchronized as a bundle.
- Gemini evidence: The start of the video (0.00s) shows simultaneous execution of both saying 'help' and holding the thumbs-up pose.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/all_tools_TC_REL_FP_Sp_Si_rel_sync_cnt_v1.txt`

#### FP — Si_So_rel_ord_SiSo v1

- Human: `no` / Gemini: `yes`
- Temporal type: `relative_order`
- Modality: `Action (silent) + Action (sounding)`
- Gemini reason: The sequential order is correctly executed.
- Gemini evidence: The thumbs-up pose is completed and held first (ending around 2.1s), followed by the hand moving down to slap the thigh (impact at 3.0s).
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/all_tools_TC_REL_FP_Si_So_rel_ord_SiSo_v1.txt`

#### FP — Sp_Si_So_rel_ord_SpSoSi v1

- Human: `no` / Gemini: `yes`
- Temporal type: `relative_order`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: The events occur in the exact specified relative order: speech, then thigh slap, then thumbs-up.
- Gemini evidence: Speech ends by 0.3s, the slap impact occurs at 2.3s, and the thumbs-up is formed afterward at 2.7s.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/all_tools_TC_REL_FP_Sp_Si_So_rel_ord_SpSoSi_v1.txt`

### TC_COUNT

#### TP — Sp_Si_So_rel_ord_SiSpSo v1

- Human: `yes` / Gemini: `yes`
- Temporal type: `relative_order`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: Each required target event (the speech, the thumbs-up, and the slap) occurs exactly once with no extra or spurious occurrences.
- Gemini evidence: The video contains exactly one instance of the word 'help', one thumbs-up pose, and one slap action. No other target actions are repeated.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/all_tools_TC_COUNT_TP_Sp_Si_So_rel_ord_SiSpSo_v1.txt`

#### TP — Sp_Si_rel_ord_SiSp v1

- Human: `yes` / Gemini: `yes`
- Temporal type: `relative_order`
- Modality: `Speech + Action (silent)`
- Gemini reason: Each required event occurs exactly once, with no extra or spurious occurrences.
- Gemini evidence: The person forms the thumbs-up once and speaks the word 'help' exactly once. No repetitions are observed.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/all_tools_TC_COUNT_TP_Sp_Si_rel_ord_SiSp_v1.txt`

#### TP — Sp_Si_rel_ord_SpSi v1

- Human: `yes` / Gemini: `yes`
- Temporal type: `relative_order`
- Modality: `Speech + Action (silent)`
- Gemini reason: Both the speech event and the visual action occur exactly once with no spurious repetitions.
- Gemini evidence: The word 'help' is spoken a single time, and the thumbs-up pose is formed once and held until the end of the video.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/all_tools_TC_COUNT_TP_Sp_Si_rel_ord_SpSi_v1.txt`

#### TN — Sp_Si_So_rel_sync_cnt v1

- Human: `no` / Gemini: `no`
- Temporal type: `relative_sync_count`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: The synchronized bundle of speech, thumbs-up, and slap does not occur the required exactly two times; in fact, the full combination never occurs. Furthermore, the spoken word 'help' is only performed once.
- Gemini evidence: The video features one speech event, one isolated thumbs-up, and two asynchronous slaps, completely failing the requirement for exactly two fully synchronized bundles.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/all_tools_TC_COUNT_TN_Sp_Si_So_rel_sync_cnt_v1.txt`

#### TN — Sp_Si_rel_sync_cnt v1

- Human: `no` / Gemini: `no`
- Temporal type: `relative_sync_count`
- Modality: `Speech + Action (silent)`
- Gemini reason: The synchronized bundle occurs only once, failing the strict prompt requirement of exactly two repetitions.
- Gemini evidence: The person performs the target bundle at the very beginning of the video (0.00-0.66s), but after returning to the resting position, they do not repeat the word 'help' or the thumbs-up gesture for the remainder of the video.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/all_tools_TC_COUNT_TN_Sp_Si_rel_sync_cnt_v1.txt`

#### TN — Sp_So_rel_sync_cnt v1

- Human: `no` / Gemini: `no`
- Temporal type: `relative_sync_count`
- Modality: `Speech + Action (sounding)`
- Gemini reason: Hierarchical preconditions failed. The target synchronized bundle of speech and sounding action occurs 0 times instead of the required 2 times.
- Gemini evidence: The video contains 1 speech event and 2 silent visual slap events, with no synchronized occurrences.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/all_tools_TC_COUNT_TN_Sp_So_rel_sync_cnt_v1.txt`

#### FP — Sp_So_rel_ord_SpSo v1

- Human: `no` / Gemini: `yes`
- Temporal type: `relative_order`
- Modality: `Speech + Action (sounding)`
- Gemini reason: Both the speech event and the sounding action event occur exactly once, as required.
- Gemini evidence: The person says 'help' only once and slaps the thigh exactly once. There are no spurious or repeated target actions or sounds.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/all_tools_TC_COUNT_FP_Sp_So_rel_ord_SpSo_v1.txt`

#### FP — Si_So_rel_ord_SiSo v1

- Human: `no` / Gemini: `yes`
- Temporal type: `relative_order`
- Modality: `Action (silent) + Action (sounding)`
- Gemini reason: Each required event occurs exactly once with no repetitions.
- Gemini evidence: There is exactly one thumbs-up gesture and exactly one slap on the thigh visible in the video.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/all_tools_TC_COUNT_FP_Si_So_rel_ord_SiSo_v1.txt`

#### FP — Sp_Si_So_rel_ord_SoSiSp v1

- Human: `no` / Gemini: `yes`
- Temporal type: `relative_order`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: Each target event occurs exactly once as required, with no repetitions.
- Gemini evidence: There is exactly one slap, one thumbs-up pose, and one utterance of the word 'help'.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/all_tools_TC_COUNT_FP_Sp_Si_So_rel_ord_SoSiSp_v1.txt`

#### FN — Sp_Si_rel_sync v1

- Human: `yes` / Gemini: `no`
- Temporal type: `relative_synchronization`
- Modality: `Speech + Action (silent)`
- Gemini reason: Preceding axes failed (incorrect visual event and binding), forcing the count to 'no'.
- Gemini evidence: The required synchronized bundle of saying 'help' while performing a right-hand thumbs-up never occurs.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/all_tools_TC_COUNT_FN_Sp_Si_rel_sync_v1.txt`

### CC

#### TP — Sp_So_rel_ord_SpSo v1

- Human: `yes` / Gemini: `yes`
- Temporal type: `relative_order`
- Modality: `Speech + Action (sounding)`
- Gemini reason: All prompt constraints are met, including the plain indoor room, static medium shot, starting posture, lack of extra speech/sounds, and post-action stillness.
- Gemini evidence: The video is a static medium shot in a plain room. The person starts with hands on thighs, speaks no extra words, makes no extra actions, and remains still after the slap is completed at 4.2s.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/all_tools_CC_TP_Sp_So_rel_ord_SpSo_v1.txt`

#### TP — Sp_Si_So_rel_ord_SpSiSo v1

- Human: `yes` / Gemini: `yes`
- Temporal type: `relative_order`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: The video complies with the non-core constraints, including the scene, shot, starting pose, lack of extra speech, and post-event stillness.
- Gemini evidence: The video features a single seated person in a plain indoor room facing the camera in a static medium shot. The person starts with hands resting on thighs, speaks no extra words, and remains still after the final action.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/all_tools_CC_TP_Sp_Si_So_rel_ord_SpSiSo_v1.txt`

#### TP — Sp_Si_So_rel_ord_SiSpSo v1

- Human: `yes` / Gemini: `yes`
- Temporal type: `relative_order`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: The video adheres to all non-core constraints, including the scene, camera, initial state, and post-event stillness.
- Gemini evidence: The video shows a single person in a plain indoor room facing the camera in a static medium shot. They start with their hands resting on their legs, no extra speech or actions occur, and they remain still after the final slap.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/all_tools_CC_TP_Sp_Si_So_rel_ord_SiSpSo_v1.txt`

#### TN — Sp_Si_So_rel_sync_cnt v1

- Human: `no` / Gemini: `no`
- Temporal type: `relative_sync_count`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: The video fails to follow the strict sequence constraints, resulting in extra standalone actions (an isolated thumbs-up and an isolated second slap) that violate the instruction that no extra target actions should occur outside the requested synchronized bundles.
- Gemini evidence: Because the actions are disjointed, the standalone thumbs-up at 00:01.125 and the second open-hand slap at 00:02.208 act as extra target actions, violating the prompt's structural constraints.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/all_tools_CC_TN_Sp_Si_So_rel_sync_cnt_v1.txt`

#### TN — Sp_Si_rel_sync_cnt v1

- Human: `no` / Gemini: `no`
- Temporal type: `relative_sync_count`
- Modality: `Speech + Action (silent)`
- Gemini reason: The video fails the initial state constraint. The prompt requires the person to begin seated with both hands resting on the knees or thighs, but the person starts with the right hand already raised in a thumbs-up.
- Gemini evidence: At 0.00s, the right hand is already in the target pose rather than resting on the knee. Additionally, there is a slight, non-target hand lift around 2.25s.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/all_tools_CC_TN_Sp_Si_rel_sync_cnt_v1.txt`

#### TN — Sp_Si_So_rel_ord_SoSpSi v1

- Human: `no` / Gemini: `no`
- Temporal type: `relative_order`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: The person performs extra unprompted movements with the left hand rather than using the right hand as specified, violating the prompt's constraints.
- Gemini evidence: The prompt specifically required the right hand to act while the person remained otherwise still, but the left hand performs all the observed gestures.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/all_tools_CC_TN_Sp_Si_So_rel_ord_SoSpSi_v1.txt`

#### FP — Sp_So_rel_sync v1

- Human: `no` / Gemini: `yes`
- Temporal type: `relative_synchronization`
- Modality: `Speech + Action (sounding)`
- Gemini reason: The video satisfies the scene, camera, and setting constraints, and there are no extra unprompted actions or sounds after the final event.
- Gemini evidence: The video shows a plain indoor room with a static medium shot. The person remains seated and still after the delayed hand strike, with no background music or extra speech present.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/all_tools_CC_FP_Sp_So_rel_sync_v1.txt`

#### FP — Sp_Si_rel_ord_SpSi v1

- Human: `no` / Gemini: `yes`
- Temporal type: `relative_order`
- Modality: `Speech + Action (silent)`
- Gemini reason: The video complies with all scene, camera, and specific action constraints.
- Gemini evidence: The video is a static medium shot in a plain indoor room. The subject starts seated with hands on thighs. Only the right hand performs the action while the left hand remains still. No extra actions, speech, text, or background music are present.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/all_tools_CC_FP_Sp_Si_rel_ord_SpSi_v1.txt`

#### FP — Sp_Si_So_rel_sync v1

- Human: `no` / Gemini: `yes`
- Temporal type: `relative_synchronization`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: The video satisfies the non-core prompt constraints regarding the scene, camera shot, and post-event stillness.
- Gemini evidence: The setting is a plain indoor room with a static medium shot. After the slap at 0.50s, the person remains entirely still with no extra speech, background music, or spurious actions.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/all_tools_CC_FP_Sp_Si_So_rel_sync_v1.txt`

#### FN — Si_So_rel_ord_SiSo v1

- Human: `yes` / Gemini: `no`
- Temporal type: `relative_order`
- Modality: `Action (silent) + Action (sounding)`
- Gemini reason: The prompt requires the full face to be visible, but the person's head is partially cropped out of the frame.
- Gemini evidence: Throughout the video, only the lower portion of the face (mouth and chin) is visible; the eyes and forehead are outside the camera's field of view.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/all_tools_CC_FN_Si_So_rel_ord_SiSo_v1.txt`

#### FN — Si_So_rel_sync v1

- Human: `yes` / Gemini: `no`
- Temporal type: `relative_synchronization`
- Modality: `Action (silent) + Action (sounding)`
- Gemini reason: The person repeats the thumbs-up action multiple times, violating the constraint that no new target action occurs after the final event.
- Gemini evidence: Video shows repeated thumbs-up lifting motions at 00:01.208 and 00:03.250 after the initial action, failing the post-event stillness requirement.
- Detail file: `/home/coder/T2AV/eval_results/analysis/new-results/details/all_tools_CC_FN_Si_So_rel_sync_v1.txt`
