# Qualitative examples

TP/TN are agreements with human GT. FP/FN are disagreements.
FP = Gemini yes / human no. FN = Gemini no / human yes.

## no_tool

### A

#### TP — Sp_Si_So_rel_ord_SoSiSp v1

- Human: `yes` / Gemini: `yes`
- Temporal type: `relative_order`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: The required audio events are present and correct. A sharp slap sound is clearly audible, and the spoken word 'help' is clear with no extra words.
- Gemini evidence: A sharp slap sound is heard at 00:01.000. The spoken word 'help' is clearly heard at 00:03.000.
- Detail file: `analysis_results/details/no_tool_A_TP_Sp_Si_So_rel_ord_SoSiSp_v1.txt`

#### TP — Sp_Si_So_abs_ord_SiSpSo v2

- Human: `yes` / Gemini: `yes`
- Temporal type: `absolute_order`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: The spoken word 'help' is clearly audible with no extra words, and a sharp slap sound is distinctly heard.
- Gemini evidence: The speech 'help' is heard around 2.5 seconds, and a clear slap sound is present exactly at 4.0 seconds.
- Detail file: `analysis_results/details/no_tool_A_TP_Sp_Si_So_abs_ord_SiSpSo_v2.txt`

#### TP — Sp_Si_So_abs_ord_SpSiSo v3

- Human: `yes` / Gemini: `yes`
- Temporal type: `absolute_order`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: The word 'help' is clearly spoken and audible around 1.0 seconds, and a sharp slap sound is heard at 4.0 seconds, matching the prompt's audio requirements.
- Gemini evidence: Audio contains clear speech 'help' at 1.0 seconds and a slap sound at approximately 4.0 seconds. No extra words are spoken.
- Detail file: `analysis_results/details/no_tool_A_TP_Sp_Si_So_abs_ord_SpSiSo_v3.txt`

#### TN — Sp_Si_So_rel_ord_SpSiSo v2

- Human: `no` / Gemini: `no`
- Temporal type: `relative_order`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: The speech 'help' is clearly spoken, but the required sharp slap sound is entirely missing.
- Gemini evidence: The word 'help' is heard at 00:00.000. However, the remainder of the audio track contains no sound of a slap.
- Detail file: `analysis_results/details/no_tool_A_TN_Sp_Si_So_rel_ord_SpSiSo_v2.txt`

#### TN — Sp_Si_So_abs_sync v2

- Human: `no` / Gemini: `no`
- Temporal type: `absolute_synchronization`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: The required speech event 'help' is completely absent from the audio.
- Gemini evidence: A slap sound is heard around 1.2 seconds, but there is no speech audio present at any point in the video.
- Detail file: `analysis_results/details/no_tool_A_TN_Sp_Si_So_abs_sync_v2.txt`

#### TN — Sp_Si_So_abs_sync v3

- Human: `no` / Gemini: `no`
- Temporal type: `absolute_synchronization`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: The audio contains the required speech 'help', but the sharp slap sound is entirely missing.
- Gemini evidence: The word 'help' is heard around 1.0 second, but no slap or impact sound is audible in the audio track.
- Detail file: `analysis_results/details/no_tool_A_TN_Sp_Si_So_abs_sync_v3.txt`

#### FP — Sp_Si_So_abs_sync_cnt v1

- Human: `no` / Gemini: `yes`
- Temporal type: `absolute_sync_count`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: The speech 'help' and the sharp slap sound are both clearly present in the audio track.
- Gemini evidence: The word 'help' is heard around 0.0 seconds to 0.5 seconds. A distinct slap sound is heard at 0.8 seconds.
- Detail file: `analysis_results/details/no_tool_A_FP_Sp_Si_So_abs_sync_cnt_v1.txt`

#### FN — Sp_Si_So_abs_ord_SpSoSi v3

- Human: `yes` / Gemini: `no`
- Temporal type: `absolute_order`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: Without audio tool evidence (Whisper/CLAP) or audible tracks provided, the presence of the spoken word 'help' and the slap sound cannot be verified, and the total lack of visible speech motion strongly suggests the speech audio is absent.
- Gemini evidence: No Whisper ASR or CLAP sound event evidence is provided to confirm the speech or the sharp slap sound.
- Detail file: `analysis_results/details/no_tool_A_FN_Sp_Si_So_abs_ord_SpSoSi_v3.txt`

#### FN — Si_So_abs_sync_cnt v2

- Human: `yes` / Gemini: `no`
- Temporal type: `absolute_sync_count`
- Modality: `Action (silent) + Action (sounding)`
- Gemini reason: Only one slap sound is heard instead of the required two, as the second sound is entirely missing.
- Gemini evidence: A sharp slap sound occurs exactly at 02:00, but there is no subsequent slap sound heard around the required 3.5 seconds or during the second visual action at 04:00-05:00.
- Detail file: `analysis_results/details/no_tool_A_FN_Si_So_abs_sync_cnt_v2.txt`

#### FN — Sp_Si_So_abs_sync_cnt v3

- Human: `yes` / Gemini: `no`
- Temporal type: `absolute_sync_count`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: The required speech event 'help' and the sharp slap sounds do not occur at the specified times; the slap sound is missing entirely.
- Gemini evidence: No clear slap sounds are evident in the expected segments, and speech appears to be misplaced at the very beginning of the video rather than at the 1.5s and 3.5s marks.
- Detail file: `analysis_results/details/no_tool_A_FN_Sp_Si_So_abs_sync_cnt_v3.txt`

### V

#### TP — Sp_Si_So_rel_ord_SoSiSp v3

- Human: `yes` / Gemini: `yes`
- Temporal type: `relative_order`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: The required visual actions are correctly executed: the person's right hand visibly strikes their right thigh, followed by the right hand forming a clear thumbs-up pose, and visible mouth movement occurs for the speech.
- Gemini evidence: The right hand slaps the thigh at 00:00.250. The right hand then raises and holds a thumbs-up pose starting around 00:02.125. The person's mouth visibly moves to speak around 00:03.000.
- Detail file: `analysis_results/details/no_tool_V_TP_Sp_Si_So_rel_ord_SoSiSp_v3.txt`

#### TP — Sp_Si_So_rel_ord_SoSiSp v1

- Human: `yes` / Gemini: `yes`
- Temporal type: `relative_order`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: The visible actions match the prompt. The person slaps their right thigh with their right hand, forms a clear thumbs-up pose with the right hand, and visible lip motion is present for the speech.
- Gemini evidence: The right hand strikes the right thigh at 00:01.000. The right hand forms and holds a thumbs-up pose from approximately 00:01.833 to 00:02.917. Clear mouth motion for speech is visible around 00:03.000.
- Detail file: `analysis_results/details/no_tool_V_TP_Sp_Si_So_rel_ord_SoSiSp_v1.txt`

#### TP — Sp_Si_So_abs_ord_SpSoSi v2

- Human: `yes` / Gemini: `yes`
- Temporal type: `absolute_order`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: The visible actions match the prompt: the mouth moves to speak, the right hand lifts and strikes the right thigh, and then the right hand forms a clear thumbs-up pose.
- Gemini evidence: Visible lip movement occurs at 1.0s. The person's right hand (viewer's left) strikes the thigh around 3.4s, and forms a thumbs-up pose starting around 3.7s, holding it until the end of the video.
- Detail file: `analysis_results/details/no_tool_V_TP_Sp_Si_So_abs_ord_SpSoSi_v2.txt`

#### TN — Sp_Si_rel_sync_cnt v3

- Human: `no` / Gemini: `no`
- Temporal type: `relative_sync_count`
- Modality: `Speech + Action (silent)`
- Gemini reason: The person's mouth remains completely closed and static throughout the entire video, lacking the required visible speaking behavior. Additionally, while the right hand forms a thumbs-up the first time, the second attempt is merely a lifted loose fist without a clear thumb extension.
- Gemini evidence: Video inspection shows the face is entirely still from 00:00.000 to 00:05.000 with no lip movement. The right hand shows a thumbs-up at 00:00.000 but only lifts in a fist around 00:01.000.
- Detail file: `analysis_results/details/no_tool_V_TN_Sp_Si_rel_sync_cnt_v3.txt`

#### TN — Sp_Si_So_abs_sync v1

- Human: `no` / Gemini: `no`
- Temporal type: `absolute_synchronization`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: The right hand forms a thumbs-up pose and strikes the right thigh. However, the prompt explicitly requires the full face and mouth to be clearly visible, but the person's head is cropped out of the frame above the chin, failing the visibility requirement for the speaking action.
- Gemini evidence: The right hand lifts and forms a thumbs-up at 1.83s, then strikes the thigh at 2.04s. The camera framing crops the subject's head entirely, making the full face and mouth invisible throughout the video.
- Detail file: `analysis_results/details/no_tool_V_TN_Sp_Si_So_abs_sync_v1.txt`

#### TN — Sp_So_rel_ord_SpSo v1

- Human: `no` / Gemini: `no`
- Temporal type: `relative_order`
- Modality: `Speech + Action (sounding)`
- Gemini reason: While the visible speaking motion is correct, the visible action of slapping the right thigh is not properly executed; the person slowly raises their right hand and lowers it gently without making a visible striking impact.
- Gemini evidence: Appropriate mouth movement is visible at the beginning of the video. However, from 00:03.042 to 00:04.292, the right hand is raised and then softly placed back on the knee, with no fast striking motion or visible impact observed.
- Detail file: `analysis_results/details/no_tool_V_TN_Sp_So_rel_ord_SpSo_v1.txt`

#### FP — Sp_Si_So_abs_sync_cnt v2

- Human: `no` / Gemini: `yes`
- Temporal type: `absolute_sync_count`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: The visible actions match the prompt. The person forms a right-hand thumbs-up pose and strikes the right thigh while holding the pose.
- Gemini evidence: The right hand forms a thumbs-up pose starting around 0.8 seconds and 2.8 seconds, then comes down to strike the right thigh at 1.4 seconds and 3.4 seconds. Mouth movement is also visible during speech.
- Detail file: `analysis_results/details/no_tool_V_FP_Sp_Si_So_abs_sync_cnt_v2.txt`

#### FP — Sp_Si_So_abs_ord_SoSpSi v1

- Human: `no` / Gemini: `yes`
- Temporal type: `absolute_order`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: The specified visual actions are correctly performed: the person's right hand slaps their right thigh, plausible speaking motion is visible, and the right hand forms a clear thumbs-up.
- Gemini evidence: The right hand visibly strikes the right thigh at 1.1 seconds, the mouth articulates the spoken word at 2.5 seconds, and the right hand forms a thumbs-up starting around 3.5 seconds.
- Detail file: `analysis_results/details/no_tool_V_FP_Sp_Si_So_abs_ord_SoSpSi_v1.txt`

#### FP — Si_So_abs_ord_SoSi v2

- Human: `no` / Gemini: `yes`
- Temporal type: `absolute_order`
- Modality: `Action (silent) + Action (sounding)`
- Gemini reason: The visible actions are accurately depicted. The person uses their right hand to slap their right thigh, and later forms a clear thumbs-up pose with the same hand.
- Gemini evidence: Visible impact of the right hand on the right thigh occurs at 2.0s, and a closed-fist thumbs-up pose with the right hand is formed around 4.2s and held.
- Detail file: `analysis_results/details/no_tool_V_FP_Si_So_abs_ord_SoSi_v2.txt`

#### FN — Sp_Si_So_abs_ord_SpSoSi v1

- Human: `yes` / Gemini: `no`
- Temporal type: `absolute_order`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: The visible speaking motion is mistimed, occurring at the very beginning of the video, and the required thumbs-up gesture is malformed and unclear.
- Gemini evidence: The person's mouth moves between 0.0s and 0.4s, but they are completely still at the required 1.0s mark. At 4.0s, the right hand lifts and forms a loose fist, failing to display a clear upward-extended thumb for the thumbs-up pose. The right hand slapping the right thigh is visible.
- Detail file: `analysis_results/details/no_tool_V_FN_Sp_Si_So_abs_ord_SpSoSi_v1.txt`

#### FN — Sp_Si_rel_ord_SpSi v1

- Human: `yes` / Gemini: `no`
- Temporal type: `relative_order`
- Modality: `Speech + Action (silent)`
- Gemini reason: The prompt explicitly requires the full face and mouth to be clearly visible so that speaking behavior can be seen. However, the camera framing cuts off the person's head, making the face and mouth completely invisible.
- Gemini evidence: Throughout the video (00:00.000 - 00:05.000), the person's head is out of frame. The right-hand thumbs-up action is visible starting around 00:00.667, but the required facial visibility for the speech event is entirely missing.
- Detail file: `analysis_results/details/no_tool_V_FN_Sp_Si_rel_ord_SpSi_v1.txt`

#### FN — Si_So_abs_sync_cnt v1

- Human: `yes` / Gemini: `no`
- Temporal type: `absolute_sync_count`
- Modality: `Action (silent) + Action (sounding)`
- Gemini reason: The prompt explicitly requires the thumbs-up to be a held pose without a separate raising motion, but the person performs a distinct, large upward arm-raising motion before striking the thigh.
- Gemini evidence: From 2.7 to 3.1 seconds, the person significantly raises their right hand high in the air to form the thumbs-up before bringing it down to strike the thigh, directly violating the prompt's visual constraint.
- Detail file: `analysis_results/details/no_tool_V_FN_Si_So_abs_sync_cnt_v1.txt`

### AVB

#### TP — Sp_Si_So_rel_ord_SoSiSp v3

- Human: `yes` / Gemini: `yes`
- Temporal type: `relative_order`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: Both the sounding action and the speech event are correctly synchronized with their respective visual motions.
- Gemini evidence: The slap sound is perfectly aligned with the visible contact of the hand on the thigh at 00:00.250. The spoken word 'help' is synchronized with the lip movements starting at 00:03.000.
- Detail file: `analysis_results/details/no_tool_AVB_TP_Sp_Si_So_rel_ord_SoSiSp_v3.txt`

#### TP — Sp_Si_abs_sync_cnt v3

- Human: `yes` / Gemini: `yes`
- Temporal type: `absolute_sync_count`
- Modality: `Speech + Action (silent)`
- Gemini reason: The audible speech is perfectly synchronized with the visible mouth movements and the execution of the thumbs-up gesture.
- Gemini evidence: Between 2.0 and 2.5 seconds, the audible word 'help' aligns precisely with the person's lip movements and the simultaneous lifting of the right hand into a thumbs-up pose.
- Detail file: `analysis_results/details/no_tool_AVB_TP_Sp_Si_abs_sync_cnt_v3.txt`

#### TP — Sp_Si_So_abs_ord_SpSoSi v2

- Human: `yes` / Gemini: `yes`
- Temporal type: `absolute_order`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: The speech audio is synchronized with the lip movements, and the slap sound aligns perfectly with the visual impact of the hand on the thigh.
- Gemini evidence: Speech audio 'help' syncs with lip motion at 1.0s. The slap sound at 3.4s perfectly aligns with the right hand making contact with the right thigh.
- Detail file: `analysis_results/details/no_tool_AVB_TP_Sp_Si_So_abs_ord_SpSoSi_v2.txt`

#### TN — Sp_Si_So_abs_sync v1

- Human: `no` / Gemini: `no`
- Temporal type: `absolute_synchronization`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: Although the slap sound synchronizes perfectly with the visible impact on the thigh, the required visible speaking behavior (mouth/face) is entirely cropped out of the frame, meaning the speech audio cannot be visually bound to the speaker's mouth as required.
- Gemini evidence: The slap impact and sound align at 2.04s. The word 'help' is spoken at 2.0s, but there is no visible mouth to bind the speech audio to.
- Detail file: `analysis_results/details/no_tool_AVB_TN_Sp_Si_So_abs_sync_v1.txt`

#### TN — Sp_Si_So_abs_ord_SiSoSp v3

- Human: `no` / Gemini: `no`
- Temporal type: `absolute_order`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: Although the slap sound aligns with the visible hand strike, the binding for the speech event fails because both the audio and the visible mouth motion are missing.
- Gemini evidence: The audio and visual components for the thigh slap are synchronized at 2.6 seconds. However, no speech audio is heard, and no mouth is visible to bind it to.
- Detail file: `analysis_results/details/no_tool_AVB_TN_Sp_Si_So_abs_ord_SiSoSp_v3.txt`

#### TN — Sp_So_rel_sync v2

- Human: `no` / Gemini: `no`
- Temporal type: `relative_synchronization`
- Modality: `Speech + Action (sounding)`
- Gemini reason: While the slap sound aligns with the visible slapping action, the required audio-visual binding for the speech event cannot be established because both the speech audio and the visible speaking motion are absent.
- Gemini evidence: The slap visual and sound are synchronized at 00:01.000, but the complete absence of speech audio and lip motion results in a failure to bind the required speech event.
- Detail file: `analysis_results/details/no_tool_AVB_TN_Sp_So_rel_sync_v2.txt`

#### FP — Sp_Si_So_abs_sync_cnt v1

- Human: `no` / Gemini: `yes`
- Temporal type: `absolute_sync_count`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: The visible mouth movements align with the spoken word, and the visible slap action aligns perfectly with the slap sound.
- Gemini evidence: Mouth motion matches the audio 'help' from 0.0 to 0.5 seconds. The hand contact with the thigh at 0.8 seconds exactly matches the audible slap sound.
- Detail file: `analysis_results/details/no_tool_AVB_FP_Sp_Si_So_abs_sync_cnt_v1.txt`

#### FP — Si_So_abs_ord_SoSi v2

- Human: `no` / Gemini: `yes`
- Temporal type: `absolute_order`
- Modality: `Action (silent) + Action (sounding)`
- Gemini reason: The auditory slap sound perfectly aligns temporally with the visual action of the hand striking the thigh.
- Gemini evidence: At exactly 2.0 seconds, the slap sound is heard right as the hand makes visible contact with the thigh.
- Detail file: `analysis_results/details/no_tool_AVB_FP_Si_So_abs_ord_SoSi_v2.txt`

#### FP — Sp_So_rel_ord_SoSp v1

- Human: `no` / Gemini: `yes`
- Temporal type: `relative_order`
- Modality: `Speech + Action (sounding)`
- Gemini reason: Both the speech and the slap sound are correctly synchronized with their corresponding visible candidate actions.
- Gemini evidence: The speech audio 'help' aligns with the visible mouth movements from 00:00.000 to 00:00.400, and the slap sound occurs precisely when the hand visibly strikes the thigh at 00:01.000.
- Detail file: `analysis_results/details/no_tool_AVB_FP_Sp_So_rel_ord_SoSp_v1.txt`

#### FN — Si_So_rel_sync_cnt v3

- Human: `yes` / Gemini: `no`
- Temporal type: `relative_sync_count`
- Modality: `Action (silent) + Action (sounding)`
- Gemini reason: The slap sounds and the visible movements are completely misaligned. The sounds occur exactly as the hands begin to lift off the thighs, while the actual downward visible contact is silent.
- Gemini evidence: The first slap sound is heard at 00:01.000, but the hand's visible downward contact happens around 00:01.458. The second slap sound is heard at 00:04.000, with the visible contact occurring around 00:04.458.
- Detail file: `analysis_results/details/no_tool_AVB_FN_Si_So_rel_sync_cnt_v3.txt`

#### FN — Sp_Si_So_rel_sync v3

- Human: `yes` / Gemini: `no`
- Temporal type: `relative_synchronization`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: While the slap sound aligns temporally with the hand striking the thigh, the speech audio cannot be bound to any visible speaking motion because the mouth is entirely out of frame.
- Gemini evidence: The slap sound at 1.0s matches the visible impact of the right hand on the right thigh, but the speech 'help' at 0.8s-1.0s lacks any corresponding visible lip or mouth motion.
- Detail file: `analysis_results/details/no_tool_AVB_FN_Sp_Si_So_rel_sync_v3.txt`

#### FN — Si_So_abs_sync_cnt v2

- Human: `yes` / Gemini: `no`
- Temporal type: `absolute_sync_count`
- Modality: `Action (silent) + Action (sounding)`
- Gemini reason: The audible sound is severely misaligned with the visual impact, and the second visual action has no corresponding sound.
- Gemini evidence: At 02:00, the loud slap sound is heard while the right hand is lifting off the leg, whereas the actual visual contact with the thigh happens silently around 02:75. The second visual impact around 04:58 is completely silent.
- Detail file: `analysis_results/details/no_tool_AVB_FN_Si_So_abs_sync_cnt_v2.txt`

### TC

#### TP — Sp_Si_rel_ord_SpSi v1

- Human: `yes` / Gemini: `yes`
- Temporal type: `relative_order`
- Modality: `Speech + Action (silent)`
- Gemini reason: The temporal sequence of the events is correct: the speech event occurs and concludes before the physical action begins.
- Gemini evidence: The spoken word 'help' ends by 00:00.500, and the right hand subsequently forms a thumbs-up starting around 00:00.667, maintaining the correct relative order.
- Detail file: `analysis_results/details/no_tool_TC_TP_Sp_Si_rel_ord_SpSi_v1.txt`

#### TP — Sp_Si_rel_sync v3

- Human: `yes` / Gemini: `yes`
- Temporal type: `relative_synchronization`
- Modality: `Speech + Action (silent)`
- Gemini reason: The speech event and the visual action occur simultaneously, satisfying the synchronization requirement.
- Gemini evidence: The word 'help' is spoken at the very beginning of the video, exactly while the right hand forms the thumbs-up pose (00:00.000 - 00:00.125).
- Detail file: `analysis_results/details/no_tool_TC_TP_Sp_Si_rel_sync_v3.txt`

#### TP — Si_So_rel_ord_SiSo v3

- Human: `yes` / Gemini: `yes`
- Temporal type: `relative_order`
- Modality: `Action (silent) + Action (sounding)`
- Gemini reason: The video strictly follows the requested sequence: the silent action (thumbs-up) is fully completed before the sounding action (slapping the thigh) occurs.
- Gemini evidence: The thumbs-up pose is maintained until 00:02.917, and only after releasing this pose does the person proceed to slap their thigh at 00:03.208.
- Detail file: `analysis_results/details/no_tool_TC_TP_Si_So_rel_ord_SiSo_v3.txt`

#### TN — Sp_Si_So_abs_ord_SpSoSi v2

- Human: `no` / Gemini: `no`
- Temporal type: `absolute_order`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: The absolute timing requirement is violated. While the speech occurs correctly at 1.0s, the thigh slap occurs at 3.4s instead of the required 2.5s, significantly delaying the event and disrupting the intended temporal spacing before the thumbs-up.
- Gemini evidence: The prompt requires the thigh strike to occur at 2.5 seconds, but the hand remains still at 2.5s and only strikes the thigh at approximately 3.4s. The thumbs-up follows almost immediately after at 3.7s, rather than preserving the specified temporal structure.
- Detail file: `analysis_results/details/no_tool_TC_TN_Sp_Si_So_abs_ord_SpSoSi_v2.txt`

#### TN — Sp_Si_So_rel_sync v3

- Human: `no` / Gemini: `no`
- Temporal type: `relative_synchronization`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: The video violates the fixed single-event structure by repeatedly showing the target action (striking the thigh) after the required synchronized moment. Additionally, the missing visible speech prevents full verification of synchronization.
- Gemini evidence: After the initial synchronized event around 1.0s, the person raises their hand and strikes their thigh again around 2.1s and 3.4s, violating the constraint that no new target action occurs after the final event.
- Detail file: `analysis_results/details/no_tool_TC_TN_Sp_Si_So_rel_sync_v3.txt`

#### TN — Sp_Si_abs_sync_cnt v3

- Human: `no` / Gemini: `no`
- Temporal type: `absolute_sync_count`
- Modality: `Speech + Action (silent)`
- Gemini reason: The prompt requires the synchronized speech and action bundle to occur twice (at 1.5 seconds and 3.5 seconds). However, only a single delayed occurrence is present, and the required second occurrence is entirely missing.
- Gemini evidence: The first and only occurrence of the 'help' + thumbs-up bundle happens around 2.0 seconds. After this, the person holds the pose in silence until the end of the video, failing to perform the required second repetition at 3.5 seconds.
- Detail file: `analysis_results/details/no_tool_TC_TN_Sp_Si_abs_sync_cnt_v3.txt`

#### FP — Sp_Si_So_rel_ord_SoSiSp v1

- Human: `no` / Gemini: `yes`
- Temporal type: `relative_order`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: The required relative order is satisfied perfectly: the sounding action occurs first, followed by the silent visual action, and finally the speech.
- Gemini evidence: The slap occurs first at 00:01.000, the thumbs-up is held second between 00:01.833 and 00:02.917, and the speech occurs last at 00:03.000.
- Detail file: `analysis_results/details/no_tool_TC_FP_Sp_Si_So_rel_ord_SoSiSp_v1.txt`

#### FP — Si_So_rel_ord_SiSo v1

- Human: `no` / Gemini: `yes`
- Temporal type: `relative_order`
- Modality: `Action (silent) + Action (sounding)`
- Gemini reason: The relative order constraint is satisfied perfectly. The silent thumbs-up action occurs and completes before the sounding thigh strike begins.
- Gemini evidence: The thumbs-up pose concludes by 00:02.500. The right hand then returns to the thigh and performs the subsequent strike action around 00:03.600, following the exact required sequence.
- Detail file: `analysis_results/details/no_tool_TC_FP_Si_So_rel_ord_SiSo_v1.txt`

#### FP — Si_So_abs_ord_SoSi v2

- Human: `no` / Gemini: `yes`
- Temporal type: `absolute_order`
- Modality: `Action (silent) + Action (sounding)`
- Gemini reason: The events occur in the correct absolute order and approximate the requested timings.
- Gemini evidence: The slap action occurs around 2.0s (following the 1.5s requirement closely), and the thumbs-up pose is formed around 4.2s (following the 3.5s requirement), satisfying the specified absolute sequence.
- Detail file: `analysis_results/details/no_tool_TC_FP_Si_So_abs_ord_SoSi_v2.txt`

#### FN — Sp_Si_So_abs_sync_cnt v2

- Human: `yes` / Gemini: `no`
- Temporal type: `absolute_sync_count`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: The prompt requires the speech, thumbs-up pose, and slap to occur simultaneously at 1.5 seconds and 3.5 seconds. However, the events are performed sequentially (speech first, then the slap) and occur earlier than the requested absolute timings.
- Gemini evidence: In the first bundle, speech occurs at 1.0s, but the slap does not happen until 1.4s. In the second bundle, speech occurs at 3.0s, and the slap happens at 3.4s. They are neither simultaneous nor at the exact requested times of 1.5s and 3.5s.
- Detail file: `analysis_results/details/no_tool_TC_FN_Sp_Si_So_abs_sync_cnt_v2.txt`

#### FN — Si_So_rel_sync_cnt v3

- Human: `yes` / Gemini: `no`
- Temporal type: `relative_sync_count`
- Modality: `Action (silent) + Action (sounding)`
- Gemini reason: The temporal constraint requires two synchronized occurrences of the silent action (thumbs-up) and the sounding action (slapping the thigh). Because the audio and visual components are misaligned, the synchronized bundles do not occur.
- Gemini evidence: The slap sounds at 00:01.000 and 00:04.000 are not synchronized with the visible impacts at 00:01.458 and 00:04.458, breaking the required temporal synchronization.
- Detail file: `analysis_results/details/no_tool_TC_FN_Si_So_rel_sync_cnt_v3.txt`

#### FN — Si_So_rel_ord_SoSi v1

- Human: `yes` / Gemini: `no`
- Temporal type: `relative_order`
- Modality: `Action (silent) + Action (sounding)`
- Gemini reason: The specified temporal sequence cannot be fully satisfied because the second required event (a right-hand thumbs-up) is absent, having been substituted by a left-hand thumbs-up.
- Gemini evidence: The first event (right-hand slap) occurs correctly at 00:01.000, but the sequence fails afterward because the right hand does not perform the required thumbs-up.
- Detail file: `analysis_results/details/no_tool_TC_FN_Si_So_rel_ord_SoSi_v1.txt`

### CC

#### TP — Sp_Si_So_abs_ord_SpSiSo v2

- Human: `yes` / Gemini: `yes`
- Temporal type: `absolute_order`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: The video adheres to the scene, camera, and subject constraints. There are no extra sounds, speech, text overlays, or background music.
- Gemini evidence: The video features a static medium shot of a single person seated in a plain indoor room with hands initially resting on their thighs. No extraneous actions follow the final slap, and the specified negative constraints (no subtitles, etc.) are maintained.
- Detail file: `analysis_results/details/no_tool_CC_TP_Sp_Si_So_abs_ord_SpSiSo_v2.txt`

#### TP — Sp_Si_So_rel_ord_SoSiSp v1

- Human: `yes` / Gemini: `yes`
- Temporal type: `relative_order`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: The video complies with all additional constraints. It features a single seated person in a plain indoor room, framed in a static medium shot. There are no subtitles, background music, or extra actions after the final event.
- Gemini evidence: The setting, camera angle, and posture are correct. The person does not speak any extra words, and they remain seated and resting after speaking the target word.
- Detail file: `analysis_results/details/no_tool_CC_TP_Sp_Si_So_rel_ord_SoSiSp_v1.txt`

#### TP — Sp_Si_So_abs_ord_SiSpSo v2

- Human: `yes` / Gemini: `yes`
- Temporal type: `absolute_order`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: The video satisfies all non-core constraints regarding the scene, camera framing, lack of background music, and post-action stillness.
- Gemini evidence: The video features a single seated person in a plain indoor room, captured in a static medium shot. The person starts with hands on thighs, speaks no extra words, and remains entirely still after the final slap event.
- Detail file: `analysis_results/details/no_tool_CC_TP_Sp_Si_So_abs_ord_SiSpSo_v2.txt`

#### TN — Sp_Si_So_rel_ord_SiSoSp v2

- Human: `no` / Gemini: `no`
- Temporal type: `relative_order`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: The video fails several starting pose and specific action constraints, including the initial hand position, the laterality of the thumbs-up, and the target location of the slap.
- Gemini evidence: The prompt requires starting with hands on the thighs, but the video starts at 00:00.000 with both hands already in a thumbs-up. The thumbs-up is performed with both hands instead of just the right. The right hand slaps the left arm/wrist at 00:01.625 instead of the top of the right thigh.
- Detail file: `analysis_results/details/no_tool_CC_TN_Sp_Si_So_rel_ord_SiSoSp_v2.txt`

#### TN — Sp_Si_rel_sync_cnt v2

- Human: `no` / Gemini: `no`
- Temporal type: `relative_sync_count`
- Modality: `Speech + Action (silent)`
- Gemini reason: The video violates the prompt's camera and framing constraints. The prompt requires a 'full face, mouth' to be clearly visible, but the top of the person's head is cropped. Additionally, the video starts with the action already in progress rather than a resting pose.
- Gemini evidence: The person's head is cropped out from 00:00.000 to 00:05.000, and the right hand is already moving upward in the very first frame rather than resting on the thigh.
- Detail file: `analysis_results/details/no_tool_CC_TN_Sp_Si_rel_sync_cnt_v2.txt`

#### TN — Si_So_abs_sync_cnt v2

- Human: `no` / Gemini: `no`
- Temporal type: `absolute_sync_count`
- Modality: `Action (silent) + Action (sounding)`
- Gemini reason: The video fails the camera framing constraint since the face is cut off. Additionally, the hand performs a distinct raising motion instead of just holding the pose while contacting.
- Gemini evidence: The head is not visible in the medium shot, and the person lifts their hand visibly into the air to form the thumbs-up before striking the thigh, contrary to the prompt's instructions prohibiting a separate raising motion.
- Detail file: `analysis_results/details/no_tool_CC_TN_Si_So_abs_sync_cnt_v2.txt`

#### FP — Si_So_abs_sync v3

- Human: `no` / Gemini: `yes`
- Temporal type: `absolute_synchronization`
- Modality: `Action (silent) + Action (sounding)`
- Gemini reason: The video satisfies the scene, camera, and actor constraints, with no background music, extra people, or text, and ends with stillness.
- Gemini evidence: The video features a static medium shot of a single seated person in a plain indoor room. There are no spoken words, background music, or on-screen text, and the actor returns to a resting position after the actions.
- Detail file: `analysis_results/details/no_tool_CC_FP_Si_So_abs_sync_v3.txt`

#### FP — Sp_Si_rel_sync_cnt v3

- Human: `no` / Gemini: `yes`
- Temporal type: `relative_sync_count`
- Modality: `Speech + Action (silent)`
- Gemini reason: The video successfully adheres to the scene and camera constraints, featuring a single seated person in a static medium shot with no extra sounds, speech, or actions.
- Gemini evidence: The person is centered in a plain indoor setting, the shot is a static medium view, and there are no subtitles, background music, or subsequent actions after the second event window.
- Detail file: `analysis_results/details/no_tool_CC_FP_Sp_Si_rel_sync_cnt_v3.txt`

#### FP — Sp_Si_So_rel_ord_SpSoSi v3

- Human: `no` / Gemini: `yes`
- Temporal type: `relative_order`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: The video adheres to all scene, camera, and specific prompt constraints, including correct laterality, initial pose, and post-event stillness.
- Gemini evidence: The setting is a plain indoor room with a static medium shot. The hands start on the thighs, the right hand correctly performs the specified actions, no extra words or sounds are generated, and the person holds the thumbs-up pose until the end.
- Detail file: `analysis_results/details/no_tool_CC_FP_Sp_Si_So_rel_ord_SpSoSi_v3.txt`

#### FN — Si_So_rel_ord_SoSi v3

- Human: `yes` / Gemini: `no`
- Temporal type: `relative_order`
- Modality: `Action (silent) + Action (sounding)`
- Gemini reason: The video violates the static camera and full visibility constraints.
- Gemini evidence: The camera tilts upward significantly between 00:00.000 and 00:01.000. As a result, the face is cut off at the beginning, and the hands/thighs are partially cut off at the end, violating the requirement for a static shot with the full face, hands, and thighs visible simultaneously.
- Detail file: `analysis_results/details/no_tool_CC_FN_Si_So_rel_ord_SoSi_v3.txt`

#### FN — Sp_Si_So_abs_ord_SpSoSi v1

- Human: `yes` / Gemini: `no`
- Temporal type: `absolute_order`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: The person performs an action before the first scheduled event, violating the expected initial resting state.
- Gemini evidence: The prompt dictates that the person begins with hands resting and the first event occurs at 1.0 seconds. The person's mouth moving continuously from 0.0s to 0.4s acts as an unprompted preliminary action.
- Detail file: `analysis_results/details/no_tool_CC_FN_Sp_Si_So_abs_ord_SpSoSi_v1.txt`

#### FN — Si_So_abs_sync v1

- Human: `yes` / Gemini: `no`
- Temporal type: `absolute_synchronization`
- Modality: `Action (silent) + Action (sounding)`
- Gemini reason: The video includes extra, unprompted actions (pumping the arm in the air) and fails the strict instructions not to perform a separate hand-raising motion.
- Gemini evidence: Between 2.5 and 4.0 seconds, the person performs a continuous up-and-down pumping motion in the air with his right hand, which was not specified and violates the action constraints.
- Detail file: `analysis_results/details/no_tool_CC_FN_Si_So_abs_sync_v1.txt`

## mediapipe

### A

#### TP — Sp_Si_So_abs_ord_SpSiSo v3

- Human: `yes` / Gemini: `yes`
- Temporal type: `absolute_order`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: The speech event and the sound effect are both present and correct. The word 'help' is clearly spoken, and a sharp slap sound is produced.
- Gemini evidence: The word 'help' is distinctly heard around 1.0 seconds, and a clear, sharp slap sound is heard exactly at 4.0 seconds.
- Detail file: `analysis_results/details/mediapipe_A_TP_Sp_Si_So_abs_ord_SpSiSo_v3.txt`

#### TP — Sp_So_rel_sync v3

- Human: `yes` / Gemini: `yes`
- Temporal type: `relative_synchronization`
- Modality: `Speech + Action (sounding)`
- Gemini reason: The speech 'help' is clearly audible and intelligible, and a sharp slap sound is heard.
- Gemini evidence: Direct audio inspection reveals the word 'help' spoken clearly from roughly 0.100s to 0.400s, with a distinct slap sound occurring at approximately 0.250s.
- Detail file: `analysis_results/details/mediapipe_A_TP_Sp_So_rel_sync_v3.txt`

#### TP — Sp_Si_So_abs_ord_SoSiSp v1

- Human: `yes` / Gemini: `yes`
- Temporal type: `absolute_order`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: The required audio events are present and correct. A clear slap sound is produced, and the word 'help' is spoken distinctly.
- Gemini evidence: A slap sound is heard around 2.0 seconds, and the spoken word 'help' is clearly audible at 4.0 seconds.
- Detail file: `analysis_results/details/mediapipe_A_TP_Sp_Si_So_abs_ord_SoSiSp_v1.txt`

#### TN — Sp_Si_So_abs_sync_cnt v1

- Human: `no` / Gemini: `no`
- Temporal type: `absolute_sync_count`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: The required speech event 'help' is completely absent from the audio. Only the slap sounds are audible.
- Gemini evidence: Direct audio inspection reveals sharp slap sounds around 1.0 seconds and 3.0 seconds, but no spoken word 'help' can be heard at any point.
- Detail file: `analysis_results/details/mediapipe_A_TN_Sp_Si_So_abs_sync_cnt_v1.txt`

#### TN — Sp_Si_So_abs_sync v2

- Human: `no` / Gemini: `no`
- Temporal type: `absolute_synchronization`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: The video contains no audible speech saying 'help' and no sharp slap sound.
- Gemini evidence: Throughout the video, including around the 2.0-second mark, there is no audio track or audible sound of any kind.
- Detail file: `analysis_results/details/mediapipe_A_TN_Sp_Si_So_abs_sync_v2.txt`

#### TN — Sp_Si_abs_sync_cnt v1

- Human: `no` / Gemini: `no`
- Temporal type: `absolute_sync_count`
- Modality: `Speech + Action (silent)`
- Gemini reason: The required speech event 'help' is completely absent. The audio track is silent.
- Gemini evidence: Direct audio inspection reveals total silence throughout the video.
- Detail file: `analysis_results/details/mediapipe_A_TN_Sp_Si_abs_sync_cnt_v1.txt`

#### FP — Sp_Si_So_rel_ord_SpSiSo v2

- Human: `no` / Gemini: `yes`
- Temporal type: `relative_order`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: The required speech event ('help') and the non-speech sound event (a sharp slap sound) are correctly present in the audio.
- Gemini evidence: The word 'help' is heard at the beginning of the video, and a distinct slap sound is heard around 3.0 seconds.
- Detail file: `analysis_results/details/mediapipe_A_FP_Sp_Si_So_rel_ord_SpSiSo_v2.txt`

#### FP — Sp_So_rel_sync v1

- Human: `no` / Gemini: `yes`
- Temporal type: `relative_synchronization`
- Modality: `Speech + Action (sounding)`
- Gemini reason: The spoken word 'help' and the sharp sound of a slap are both clearly audible and distinct.
- Gemini evidence: Audio features a voice saying 'help' alongside a slap sound around 1.1-1.3 seconds.
- Detail file: `analysis_results/details/mediapipe_A_FP_Sp_So_rel_sync_v1.txt`

#### FN — Sp_Si_So_rel_sync_cnt v2

- Human: `yes` / Gemini: `no`
- Temporal type: `relative_sync_count`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: There is no audio or tool evidence provided to confirm the spoken word 'help' or the sharp slap sounds. Additionally, the lack of visible mouth movement strongly suggests the speech event is absent.
- Gemini evidence: No audio track, Whisper ASR, or CLAP evidence is available. The video shows the person's mouth remaining entirely closed from 00:00.000 to 00:05.000.
- Detail file: `analysis_results/details/mediapipe_A_FN_Sp_Si_So_rel_sync_cnt_v2.txt`

#### FN — Sp_Si_So_rel_ord_SiSpSo v2

- Human: `yes` / Gemini: `no`
- Temporal type: `relative_order`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: There is no indication that the required speech event 'help' occurs, as the person's mouth remains closed and no speech-related tool evidence is present.
- Gemini evidence: Without tool evidence of speech and with the visible evidence showing the mouth completely closed during the required time window, the speech event is judged as missing.
- Detail file: `analysis_results/details/mediapipe_A_FN_Sp_Si_So_rel_ord_SiSpSo_v2.txt`

#### FN — Sp_So_abs_sync_cnt v3

- Human: `yes` / Gemini: `no`
- Temporal type: `absolute_sync_count`
- Modality: `Speech + Action (sounding)`
- Gemini reason: The audio does not contain the required speech 'help' and the sharp slap sound twice at the specified times.
- Gemini evidence: The complete absence of visual speaking motion throughout the video, and the lack of any action at 1.5 seconds, strongly indicate that the target audio events ('help' and slap sound) are not correctly generated at the required intervals.
- Detail file: `analysis_results/details/mediapipe_A_FN_Sp_So_abs_sync_cnt_v3.txt`

### V

#### TP — Sp_Si_So_rel_ord_SpSoSi v3

- Human: `yes` / Gemini: `yes`
- Temporal type: `relative_order`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: The visible speaking motion, striking of the right thigh with the right hand, and the thumbs-up pose with the right hand are all correctly executed and visible.
- Gemini evidence: The person's mouth moves visibly to speak between 00:00.000 and 00:00.600. The person's right hand strikes their right thigh at 00:02.042. At 00:03.400, the person forms a clear thumbs-up pose with their right hand.
- Detail file: `analysis_results/details/mediapipe_V_TP_Sp_Si_So_rel_ord_SpSoSi_v3.txt`

#### TP — Sp_Si_So_rel_ord_SoSpSi v3

- Human: `yes` / Gemini: `yes`
- Temporal type: `relative_order`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: The video successfully shows the right hand striking the right thigh, visible mouth movements corresponding to speech, and the right hand forming and holding a clear thumbs-up pose.
- Gemini evidence: The right hand is seen striking the right thigh at 00:00.083. The mouth visibly moves at 00:01.000. Following this, the right hand forms a thumbs-up pose starting around 00:01.125 and holds it.
- Detail file: `analysis_results/details/mediapipe_V_TP_Sp_Si_So_rel_ord_SoSpSi_v3.txt`

#### TP — Sp_Si_So_rel_ord_SoSpSi v2

- Human: `yes` / Gemini: `yes`
- Temporal type: `relative_order`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: The person visibly speaks, correctly slaps their right thigh with their right hand, and forms a clear thumbs-up pose.
- Gemini evidence: Visible mouth movement occurs from 0.0s to 0.5s. The person's right hand raises and strikes the right thigh making contact around 1.0s, and then raises again to form and hold a closed-fist thumbs-up pose from 1.2s to the end of the video.
- Detail file: `analysis_results/details/mediapipe_V_TP_Sp_Si_So_rel_ord_SoSpSi_v2.txt`

#### TN — Sp_Si_So_abs_ord_SpSiSo v3

- Human: `no` / Gemini: `no`
- Temporal type: `absolute_order`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: The visual events are mostly present, but the thumbs-up action is performed incorrectly. The prompt explicitly requires the thumbs-up to be formed without a separate raising motion, but the person significantly raises their right arm to chest level to form the pose.
- Gemini evidence: Visible speaking motion is seen around 1.0 seconds. The right hand slaps the right thigh at 4.0 seconds. However, between 3.0 and 3.8 seconds, the right arm lifts completely off the thigh to form the thumbs-up pose, contradicting the prompt's instructions.
- Detail file: `analysis_results/details/mediapipe_V_TN_Sp_Si_So_abs_ord_SpSiSo_v3.txt`

#### TN — Si_So_rel_ord_SoSi v2

- Human: `no` / Gemini: `no`
- Temporal type: `relative_order`
- Modality: `Action (silent) + Action (sounding)`
- Gemini reason: The video fails the starting pose requirement and the specific action constraint. The person starts with both hands raised in the air rather than resting on the thighs, and performs a simultaneous two-handed slap instead of the requested isolated right-hand slap.
- Gemini evidence: At 00:00.000, both hands are raised. From 00:00.000 to 00:00.333, both hands come down and strike both thighs simultaneously. The right hand does successfully form a thumbs-up pose starting at 00:01.833, but the initial visual requirements are violated.
- Detail file: `analysis_results/details/mediapipe_V_TN_Si_So_rel_ord_SoSi_v2.txt`

#### TN — Sp_Si_So_rel_ord_SpSoSi v1

- Human: `no` / Gemini: `no`
- Temporal type: `relative_order`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: The prompt specifically requires the person to strike their right thigh with their right hand and form a thumbs-up pose with their right hand. The person incorrectly uses their left hand (on the viewer's right) to perform both actions, while the right hand remains resting.
- Gemini evidence: Video inspection shows the person's left arm (viewer-right) lifting at 2.16s, striking the left thigh at 2.25s, and then forming a thumbs-up pose from 2.50s onward. The person's right hand (viewer-left) does not perform the required actions.
- Detail file: `analysis_results/details/mediapipe_V_TN_Sp_Si_So_rel_ord_SpSoSi_v1.txt`

#### FP — Sp_Si_So_abs_ord_SoSpSi v1

- Human: `no` / Gemini: `yes`
- Temporal type: `absolute_order`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: The required visual events and initial posture are correctly performed: the person starts with hands on thighs, slaps the right thigh with the right hand, shows visible speaking motion, and forms a clear thumbs-up with the right hand.
- Gemini evidence: The person starts seated with hands on thighs. At 1.04 seconds, the right hand clearly strikes the right thigh. At 2.5 seconds, the person's mouth moves to speak. At 4.0 seconds, the person holds a clearly formed thumbs-up with the right hand.
- Detail file: `analysis_results/details/mediapipe_V_FP_Sp_Si_So_abs_ord_SoSpSi_v1.txt`

#### FP — Sp_Si_So_abs_ord_SpSoSi v3

- Human: `no` / Gemini: `yes`
- Temporal type: `absolute_order`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: The person's mouth moves appropriately for speech, their right hand strikes their right thigh, and they form a clear thumbs-up pose with their right hand.
- Gemini evidence: Visible lip/mouth movement occurs around 1.0 seconds. The person's right hand raises and strikes the right thigh making contact around 2.5 seconds. The right hand then raises again and forms a clear thumbs-up pose, fully realized by 4.0 seconds.
- Detail file: `analysis_results/details/mediapipe_V_FP_Sp_Si_So_abs_ord_SpSoSi_v3.txt`

#### FP — Sp_Si_So_abs_ord_SoSiSp v1

- Human: `no` / Gemini: `yes`
- Temporal type: `absolute_order`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: The required visual actions are present and correct. The person strikes their right thigh with their right hand, forms a thumbs-up pose, and displays visible mouth movement for the speech.
- Gemini evidence: The right hand is seen striking the right thigh at 2.0 seconds, a clear right-hand thumbs-up pose is formed around 3.3 seconds, and the mouth moves visibly at 4.0 seconds.
- Detail file: `analysis_results/details/mediapipe_V_FP_Sp_Si_So_abs_ord_SoSiSp_v1.txt`

#### FN — Sp_Si_So_rel_sync v3

- Human: `yes` / Gemini: `no`
- Temporal type: `relative_synchronization`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: The person does not perform a thigh-slapping motion or articulate the word 'help'. While the right hand is raised multiple times, it often points rather than forming a thumbs-up, and simply rests back on the thigh without a forceful strike.
- Gemini evidence: The right hand raises and lowers three times (e.g., around 00:00.750-00:01.500, 00:02.000-00:02.500, and 00:02.833-00:03.500). A thumbs-up is only briefly seen during the second raise, and the hand gently returns to the leg without a slapping impact. The mouth remains mostly static throughout the video.
- Detail file: `analysis_results/details/mediapipe_V_FN_Sp_Si_So_rel_sync_v3.txt`

#### FN — Sp_Si_So_abs_ord_SpSoSi v1

- Human: `yes` / Gemini: `no`
- Temporal type: `absolute_order`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: The person visibly speaks at 1.0 seconds and forms a thumbs-up pose with their right hand around 4.0 seconds, but completely fails to perform the required visual action of striking the right thigh.
- Gemini evidence: Visible mouth movement occurs at 1.0s and a right-hand thumbs-up is formed and held starting around 3.5s. However, the hands remain completely still resting on the thighs around 2.5 seconds, with no visible thigh-slapping motion.
- Detail file: `analysis_results/details/mediapipe_V_FN_Sp_Si_So_abs_ord_SpSoSi_v1.txt`

#### FN — Si_So_abs_sync v1

- Human: `yes` / Gemini: `no`
- Temporal type: `absolute_synchronization`
- Modality: `Action (silent) + Action (sounding)`
- Gemini reason: The right hand forms a thumbs-up and strikes the thigh, but it is performed as a distinct hand-raising and pausing motion before striking, which explicitly contradicts the prompt's requirement.
- Gemini evidence: In the video, the person raises their right hand and pauses to hold the thumbs-up near their chest (visible around 2.5s to 2.9s) before bringing it down to strike the thigh, rather than striking while naturally holding the pose without a separate raise.
- Detail file: `analysis_results/details/mediapipe_V_FN_Si_So_abs_sync_v1.txt`

### AVB

#### TP — Sp_So_rel_sync v3

- Human: `yes` / Gemini: `yes`
- Temporal type: `relative_synchronization`
- Modality: `Speech + Action (sounding)`
- Gemini reason: The audible speech is correctly aligned with the visible mouth movements, and the slap sound perfectly matches the visible impact of the hands on the thighs.
- Gemini evidence: The mouth visibly opens and articulates the word 'help' from 0.125s to 0.292s, matching the speech audio. The hands visually strike the thighs around 0.250s to 0.292s, which aligns precisely with the audible slap sound.
- Detail file: `analysis_results/details/mediapipe_AVB_TP_Sp_So_rel_sync_v3.txt`

#### TP — Sp_So_rel_ord_SoSp v2

- Human: `yes` / Gemini: `yes`
- Temporal type: `relative_order`
- Modality: `Speech + Action (sounding)`
- Gemini reason: Both target events are well-synchronized. The slap sound occurs exactly at the moment of physical contact, and the audible speech perfectly aligns with the visible mouth movement.
- Gemini evidence: The visible contact of the right hand on the right thigh at 00:01.000 matches the slap sound exactly. The visual articulation at 00:02.833 to 00:03.000 corresponds tightly to the audio of the word 'help'.
- Detail file: `analysis_results/details/mediapipe_AVB_TP_Sp_So_rel_ord_SoSp_v2.txt`

#### TP — Sp_Si_So_rel_ord_SiSpSo v3

- Human: `yes` / Gemini: `yes`
- Temporal type: `relative_order`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: The audible speech and the visible mouth movement are well-synchronized, and the slap sound aligns perfectly with the visible impact on the thigh.
- Gemini evidence: Visible lip motion and audible speech both occur synchronously between 00:02.1 and 00:02.5. The visual frame showing contact on the thigh and the sharp slap sound both occur precisely at 00:04.000.
- Detail file: `analysis_results/details/mediapipe_AVB_TP_Sp_Si_So_rel_ord_SiSpSo_v3.txt`

#### TN — Sp_Si_So_abs_sync_cnt v1

- Human: `no` / Gemini: `no`
- Temporal type: `absolute_sync_count`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: Although the slap sounds align with the visible impacts, the required audio-visual binding for the speech event cannot be established because both the spoken audio and the visible lip motion are absent.
- Gemini evidence: Slap sounds correspond to the hand striking the thigh at 1.0s and 3.0s, but there is no speech audio and no corresponding visible mouth motion to bind.
- Detail file: `analysis_results/details/mediapipe_AVB_TN_Sp_Si_So_abs_sync_cnt_v1.txt`

#### TN — Sp_So_rel_sync v1

- Human: `no` / Gemini: `no`
- Temporal type: `relative_synchronization`
- Modality: `Speech + Action (sounding)`
- Gemini reason: The slap sound perfectly aligns with the visible impact on the thigh, but the speech audio cannot be bound to any visible speaking motion because the person's mouth and face are not in the frame.
- Gemini evidence: The slap action and sound are synchronized at 1.2 seconds, but the lack of a visible mouth makes it impossible to bind the spoken word 'help' to a visible speaking event.
- Detail file: `analysis_results/details/mediapipe_AVB_TN_Sp_So_rel_sync_v1.txt`

#### TN — Sp_Si_So_abs_ord_SiSoSp v3

- Human: `no` / Gemini: `no`
- Temporal type: `absolute_order`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: The spoken word 'help' cannot be bound to visible lip motion because the face is not visible. Additionally, the slapping event is missing in both audio and video.
- Gemini evidence: Speech audio occurs at 4.0 seconds without any visible facial or mouth movement due to the framing. There is no visible slap or corresponding slap sound.
- Detail file: `analysis_results/details/mediapipe_AVB_TN_Sp_Si_So_abs_ord_SiSoSp_v3.txt`

#### FP — Sp_So_rel_ord_SpSo v2

- Human: `no` / Gemini: `yes`
- Temporal type: `relative_order`
- Modality: `Speech + Action (sounding)`
- Gemini reason: The visible mouth movement aligns with the speech, and the visible hand clap perfectly synchronizes with the impact sound, even though the visual action itself is incorrect for the prompt.
- Gemini evidence: Visible lip movement occurs synchronously with the audible word 'help' at the start of the video. The sharp impact sound occurs exactly at 1.0s, which is the exact moment the hands visibly strike each other.
- Detail file: `analysis_results/details/mediapipe_AVB_FP_Sp_So_rel_ord_SpSo_v2.txt`

#### FP — Sp_So_rel_sync v2

- Human: `no` / Gemini: `yes`
- Temporal type: `relative_synchronization`
- Modality: `Speech + Action (sounding)`
- Gemini reason: The audible speech and the slap sound are correctly aligned with the visible lip articulation and the hand's impact on the thigh.
- Gemini evidence: The speech audio is perfectly timed with the visible lip motion between 00:01.125 and 00:01.417. The sharp slap sound perfectly matches the moment the right hand visually strikes the thigh at 00:01.292.
- Detail file: `analysis_results/details/mediapipe_AVB_FP_Sp_So_rel_sync_v2.txt`

#### FP — Sp_Si_So_rel_sync v1

- Human: `no` / Gemini: `yes`
- Temporal type: `relative_synchronization`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: Both the speech and the non-speech sound are correctly bound to their corresponding visible actions.
- Gemini evidence: Visible lip movement aligns with the spoken word 'help' early in the video, and the visible impact of the right hand on the thigh perfectly aligns with the slap sound at 0.5s.
- Detail file: `analysis_results/details/mediapipe_AVB_FP_Sp_Si_So_rel_sync_v1.txt`

#### FN — Sp_Si_So_abs_ord_SpSoSi v1

- Human: `yes` / Gemini: `no`
- Temporal type: `absolute_order`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: While the speech audio and visible mouth motion are correctly synchronized, the binding for the sounding action fails because both the slap sound and the visible slapping action are entirely absent.
- Gemini evidence: Speech audio perfectly aligns with the lip movement at 1.0s, but there is neither a visual candidate action nor a corresponding sound for the thigh slap, resulting in an unfulfilled binding requirement.
- Detail file: `analysis_results/details/mediapipe_AVB_FN_Sp_Si_So_abs_ord_SpSoSi_v1.txt`

#### FN — Sp_Si_So_rel_sync_cnt v2

- Human: `yes` / Gemini: `no`
- Temporal type: `relative_sync_count`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: There is no visible speaking motion to align with any speech audio. Furthermore, the required visual actions (thumbs-up and thigh slap) are not performed simultaneously as requested.
- Gemini evidence: The mouth remains static throughout the entire video. The thumbs-up pose is held in the air (e.g., 00:02.125) but released before the hand impacts the thigh (00:02.458), breaking the required synchronization.
- Detail file: `analysis_results/details/mediapipe_AVB_FN_Sp_Si_So_rel_sync_cnt_v2.txt`

#### FN — Sp_So_rel_sync_cnt v3

- Human: `yes` / Gemini: `no`
- Temporal type: `relative_sync_count`
- Modality: `Speech + Action (sounding)`
- Gemini reason: The first slap sound is not synchronized with any visible contact event, and the mouth movements are poorly aligned with the speech.
- Gemini evidence: The first slap sound is heard around 0.6s, but between 0.542s and 0.667s, the person's hands are moving in mid-air without making contact with the body or each other. Therefore, the sound lacks a corresponding visible physical impact.
- Detail file: `analysis_results/details/mediapipe_AVB_FN_Sp_So_rel_sync_cnt_v3.txt`

### TC

#### TP — Si_So_rel_sync_cnt v3

- Human: `yes` / Gemini: `yes`
- Temporal type: `relative_sync_count`
- Modality: `Action (silent) + Action (sounding)`
- Gemini reason: The synchronized bundle of holding a thumbs-up and striking the thigh, although visually flawed by being bilateral, occurs exactly two times as requested, with a clear reset in between.
- Gemini evidence: The first synchronized occurrence happens at 00:01.000. The person then returns to a resting position before performing the second repetition at 00:04.000, making exactly two occurrences.
- Detail file: `analysis_results/details/mediapipe_TC_TP_Si_So_rel_sync_cnt_v3.txt`

#### TP — Si_So_rel_ord_SoSi v2

- Human: `yes` / Gemini: `yes`
- Temporal type: `relative_order`
- Modality: `Action (silent) + Action (sounding)`
- Gemini reason: The relative order of the events is satisfied: the slap action is performed first, followed by the silent thumbs-up action.
- Gemini evidence: The slap action completes at 00:00.333. After a brief rest, the right hand is raised to form a thumbs-up at 00:01.625, satisfying the sequential order constraint.
- Detail file: `analysis_results/details/mediapipe_TC_TP_Si_So_rel_ord_SoSi_v2.txt`

#### TP — Sp_Si_rel_sync v3

- Human: `yes` / Gemini: `yes`
- Temporal type: `relative_synchronization`
- Modality: `Speech + Action (silent)`
- Gemini reason: The speech event and the formation of the thumbs-up pose occur simultaneously as required.
- Gemini evidence: The person's lip movements for 'help' and the right hand's motion to form the thumbs-up both begin at 00:00.000 and conclude around 00:00.125, satisfying the synchronization constraint.
- Detail file: `analysis_results/details/mediapipe_TC_TP_Sp_Si_rel_sync_v3.txt`

#### TN — Sp_Si_So_abs_ord_SpSiSo v3

- Human: `no` / Gemini: `no`
- Temporal type: `absolute_order`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: The absolute timing for the events is not fully satisfied. While the speech and the slap occur at their specified times, the thumbs-up action is significantly delayed.
- Gemini evidence: The speech occurs at 1.0 seconds and the slap occurs exactly at 4.0 seconds. However, the right hand remains still at 2.5 seconds; it does not start moving to form the thumbs-up until 3.0 seconds, completing the pose around 3.5 seconds, which misses the required 2.5-second absolute timing.
- Detail file: `analysis_results/details/mediapipe_TC_TN_Sp_Si_So_abs_ord_SpSiSo_v3.txt`

#### TN — Sp_Si_So_abs_sync_cnt v1

- Human: `no` / Gemini: `no`
- Temporal type: `absolute_sync_count`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: The temporal constraints are not satisfied. The required synchronized bundles are incomplete due to the missing speech event, and the actions that do occur happen at 1.0 seconds and 3.0 seconds instead of the prompted 1.5 seconds and 3.5 seconds.
- Gemini evidence: The physical actions (thumbs-up and slap) occur at 1.0s and 3.0s, deviating from the 1.5s and 3.5s schedule. The speech component of the synchronized bundle is entirely missing at both scheduled times.
- Detail file: `analysis_results/details/mediapipe_TC_TN_Sp_Si_So_abs_sync_cnt_v1.txt`

#### TN — Sp_Si_abs_sync_cnt v2

- Human: `no` / Gemini: `no`
- Temporal type: `absolute_sync_count`
- Modality: `Speech + Action (silent)`
- Gemini reason: The prompt requires a synchronized bundle of saying 'help' and holding a thumbs-up at both 1.5 seconds and 3.5 seconds. The visual action is completely missing during the first scheduled event.
- Gemini evidence: At 1.5 seconds, the person says 'help', but their hands remain resting on their thighs. The right-hand thumbs-up is only performed and synchronized during the second event at 3.5 seconds, violating the absolute schedule and repetition count.
- Detail file: `analysis_results/details/mediapipe_TC_TN_Sp_Si_abs_sync_cnt_v2.txt`

#### FP — Sp_Si_So_abs_ord_SpSoSi v2

- Human: `no` / Gemini: `yes`
- Temporal type: `absolute_order`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: The events occur sequentially in the exact specified order and closely match the requested absolute timestamps without any overlap.
- Gemini evidence: The sequence follows the exact order: speech at 1.0 seconds, the sounding thigh slap around 3.0 seconds (near the 2.5-second target), and the silent thumbs-up pose formed just before 4.0 seconds and held through the 4.0-second mark. Each action completes before the next begins.
- Detail file: `analysis_results/details/mediapipe_TC_FP_Sp_Si_So_abs_ord_SpSoSi_v2.txt`

#### FP — Sp_Si_So_abs_ord_SpSoSi v3

- Human: `no` / Gemini: `yes`
- Temporal type: `absolute_order`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: The events occur in the specified absolute order and at the correct specified times, without overlapping.
- Gemini evidence: Event 1 (speech 'help') happens around 1.0 seconds. Event 3 (sounding action 'slapping the thigh') happens at 2.5 seconds. Event 2 (silent action 'thumbs up') reaches its pose around 4.0 seconds and is held. The order is correct and the timing matches the schedule.
- Detail file: `analysis_results/details/mediapipe_TC_FP_Sp_Si_So_abs_ord_SpSoSi_v3.txt`

#### FP — Sp_Si_So_rel_ord_SiSpSo v3

- Human: `no` / Gemini: `yes`
- Temporal type: `relative_order`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: The events occur in the exact relative order requested: the thumbs-up pose completes, followed by the speech, followed by the thigh slap.
- Gemini evidence: The thumbs-up pose is completed and the hand lowered by 00:02.042. After this, the speech occurs at 00:02.3. After the speech finishes, the sounding action of the slap occurs at 00:04.000.
- Detail file: `analysis_results/details/mediapipe_TC_FP_Sp_Si_So_rel_ord_SiSpSo_v3.txt`

#### FN — Sp_Si_rel_sync v2

- Human: `yes` / Gemini: `no`
- Temporal type: `relative_synchronization`
- Modality: `Speech + Action (silent)`
- Gemini reason: The temporal constraint requires the speech and the forming of the thumbs-up pose to occur simultaneously. Because the speech is missing and the thumbs-up is held statically from the beginning rather than being formed, the synchronization constraint is violated.
- Gemini evidence: The right hand is static in a thumbs-up pose from 00:00.000 through the entire video, and the speech event 'help' never occurs, making simultaneous execution impossible.
- Detail file: `analysis_results/details/mediapipe_TC_FN_Sp_Si_rel_sync_v2.txt`

#### FN — Sp_Si_So_abs_sync_cnt v2

- Human: `yes` / Gemini: `no`
- Temporal type: `absolute_sync_count`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: The video fails the specified synchronized count and absolute timing constraints. The required simultaneous bundle of speech, thumbs-up, and slap does not occur at the targeted times.
- Gemini evidence: The prompt requires synchronized bundles at exactly 1.5s and 3.5s. In the video, the thumbs-up pose occurs once at 1.0s and is held, the speech occurs three times (1.0s, 2.0s, 3.0s), and the slap never occurs. Therefore, the absolute timing and synchronization constraints are completely violated.
- Detail file: `analysis_results/details/mediapipe_TC_FN_Sp_Si_So_abs_sync_cnt_v2.txt`

#### FN — Sp_Si_So_rel_ord_SpSoSi v1

- Human: `yes` / Gemini: `no`
- Temporal type: `relative_order`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: Although candidate actions appear in the correct relative order (speech, slap, thumbs-up), the specified sequence of target events cannot be fully satisfied because the required right-hand actions are entirely absent.
- Gemini evidence: The sequence consists of speech at 0.04s, a left-hand slap at 2.25s, and a left-hand thumbs-up at 2.50s. The absence of the mandated right-hand events breaks the required specific sequence.
- Detail file: `analysis_results/details/mediapipe_TC_FN_Sp_Si_So_rel_ord_SpSoSi_v1.txt`

### CC

#### TP — Sp_So_rel_ord_SoSp v2

- Human: `yes` / Gemini: `yes`
- Temporal type: `relative_order`
- Modality: `Speech + Action (sounding)`
- Gemini reason: All prompt constraints are satisfied. The scene is a plain indoor room, the shot is a static medium shot, the person starts with hands on thighs, and the required body parts are visible. There are no extra actions, sounds, or speech after the final event.
- Gemini evidence: The video shows a single person in a medium shot with a plain background. They begin with hands on their lap, perform only the requested slap and speech, and remain still from 00:03.000 until the end of the video at 00:05.042. No background music, subtitles, or extra events are present.
- Detail file: `analysis_results/details/mediapipe_CC_TP_Sp_So_rel_ord_SoSp_v2.txt`

#### TP — Sp_Si_So_rel_ord_SpSoSi v1

- Human: `yes` / Gemini: `yes`
- Temporal type: `relative_order`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: The video satisfies all non-core constraints, including the setting, camera angle, subject position, initial pose, visibility requirements, and lack of extra actions or speech.
- Gemini evidence: The video features a static medium shot in a plain room. The seated person maintains full visibility of the face, upper body, hands, and thighs. They speak only the word 'help', start with hands resting, and hold the final pose without performing any additional actions before the video ends.
- Detail file: `analysis_results/details/mediapipe_CC_TP_Sp_Si_So_rel_ord_SpSoSi_v1.txt`

#### TP — Sp_So_rel_ord_SoSp v1

- Human: `yes` / Gemini: `yes`
- Temporal type: `relative_order`
- Modality: `Speech + Action (sounding)`
- Gemini reason: The video complies with all environmental, framing, positional, and constraint specifications.
- Gemini evidence: The scene is a plain indoor room, captured in a static medium shot. A single person starts seated with hands resting on both thighs, with upper body, full face, hands, and thighs visible. The person remains still after completing the target actions from 00:02.000 to the end of the video, and there are no extra sounds, text, or background music.
- Detail file: `analysis_results/details/mediapipe_CC_TP_Sp_So_rel_ord_SoSp_v1.txt`

#### TN — Si_So_rel_sync v3

- Human: `no` / Gemini: `no`
- Temporal type: `relative_synchronization`
- Modality: `Action (silent) + Action (sounding)`
- Gemini reason: The video violates multiple constraints: the hands do not start resting on the thighs, there is a separate lifting motion for the thumbs-up pose, and an additional action occurs after the initial event.
- Gemini evidence: At 0.00 seconds, the right hand is already raised near the chest rather than resting on the thigh. Furthermore, the person lifts their hand again at 1.33 seconds to perform a separate thumbs-up action, which violates the constraints regarding no separate lifting motion and no new target actions after the final event.
- Detail file: `analysis_results/details/mediapipe_CC_TN_Si_So_rel_sync_v3.txt`

#### TN — Sp_Si_rel_sync v2

- Human: `no` / Gemini: `no`
- Temporal type: `relative_synchronization`
- Modality: `Speech + Action (silent)`
- Gemini reason: The video fails to follow the starting pose constraint. The prompt specifically requires the person to begin seated with both hands resting on the knees or thighs, but the right hand is already raised in a thumbs-up from the start.
- Gemini evidence: At 00:00.000, the right hand is already raised and positioned near the shoulder in a thumbs-up, completely bypassing the required starting state of resting on the knees or thighs.
- Detail file: `analysis_results/details/mediapipe_CC_TN_Sp_Si_rel_sync_v2.txt`

#### TN — Sp_Si_rel_sync v3

- Human: `no` / Gemini: `no`
- Temporal type: `relative_synchronization`
- Modality: `Speech + Action (silent)`
- Gemini reason: The prompt requires the person to begin with both hands resting on their knees or thighs. However, the video begins with the right hand already raised mid-air. Other constraints such as the static medium shot, plain indoor room, and post-event stillness are satisfied.
- Gemini evidence: At 00:00.000, the left hand is resting on the thigh, but the right hand is visibly lifted in the air and in motion.
- Detail file: `analysis_results/details/mediapipe_CC_TN_Sp_Si_rel_sync_v3.txt`

#### FP — Sp_Si_So_rel_ord_SiSpSo v3

- Human: `no` / Gemini: `yes`
- Temporal type: `relative_order`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: The video follows all scene, camera, and behavior constraints. The person is seated in a medium shot, begins with hands resting on thighs, says no additional words, and performs no extra actions after the final slap.
- Gemini evidence: The video features a static medium shot of a person in a plain room. The initial resting pose is maintained until 00:01.208. Only 'help' is spoken. After the slap at 00:04.000, the subject returns to a resting position and remains still until the end of the video.
- Detail file: `analysis_results/details/mediapipe_CC_FP_Sp_Si_So_rel_ord_SiSpSo_v3.txt`

#### FP — Sp_Si_So_rel_ord_SpSoSi v3

- Human: `no` / Gemini: `yes`
- Temporal type: `relative_order`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: The video complies with all additional constraints, including the static medium shot, plain indoor room, initially resting hands, full visibility of required body parts, no extra words, and post-event stillness.
- Gemini evidence: The camera remains static in a medium shot showing a person in front of a plain grey backdrop. The hands start on the thighs. The person remains still after forming the thumbs-up pose. There are no subtitles, background music, or extra actions.
- Detail file: `analysis_results/details/mediapipe_CC_FP_Sp_Si_So_rel_ord_SpSoSi_v3.txt`

#### FP — Sp_Si_So_abs_sync_cnt v1

- Human: `no` / Gemini: `yes`
- Temporal type: `absolute_sync_count`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: The video satisfies the scene, camera, and layout constraints. There are no extra actions, additional speech, or background music, and the person remains still after the final target action.
- Gemini evidence: The video features a single seated person in a plain indoor room captured in a static medium shot. After the second slap at 3.0s, no further actions occur.
- Detail file: `analysis_results/details/mediapipe_CC_FP_Sp_Si_So_abs_sync_cnt_v1.txt`

#### FN — Sp_Si_So_abs_ord_SpSiSo v3

- Human: `yes` / Gemini: `no`
- Temporal type: `absolute_order`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: The video violates the prompt's constraint by including an extra, explicitly forbidden raising action.
- Gemini evidence: The prompt specified that the thumbs-up should be formed 'without needing a separate raising motion', but the video contains a prominent arm-raising action between 3.0 and 3.8 seconds. Other constraints such as the static medium shot, plain indoor room, lack of extra audio, and post-event stillness are maintained.
- Detail file: `analysis_results/details/mediapipe_CC_FN_Sp_Si_So_abs_ord_SpSiSo_v3.txt`

#### FN — Sp_So_rel_sync v3

- Human: `yes` / Gemini: `no`
- Temporal type: `relative_synchronization`
- Modality: `Speech + Action (sounding)`
- Gemini reason: The video includes an extra unrequested action (the left hand lifting and slapping the left thigh), which violates the constraint against extra gestures or actions.
- Gemini evidence: Throughout the target event window (0.042s to 0.333s), the left hand performs a pronounced lift and slap, completely mirroring the right hand, which was not requested.
- Detail file: `analysis_results/details/mediapipe_CC_FN_Sp_So_rel_sync_v3.txt`

#### FN — Sp_So_abs_ord_SpSo v2

- Human: `yes` / Gemini: `no`
- Temporal type: `absolute_order`
- Modality: `Speech + Action (sounding)`
- Gemini reason: The video fails the constraint that no new target action occurs after the final event, as the person performs multiple repeated slaps.
- Gemini evidence: The right hand visibly strikes the thigh multiple times in rapid succession (e.g., at 4.6, 4.8, and 5.0 seconds) instead of a single impact followed by stillness.
- Detail file: `analysis_results/details/mediapipe_CC_FN_Sp_So_abs_ord_SpSo_v2.txt`

## whisper

### A

#### TP — Sp_Si_So_rel_ord_SoSpSi v2

- Human: `yes` / Gemini: `yes`
- Temporal type: `relative_order`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: The required speech event and the non-speech sound are both present and correct. The word 'help' is clearly spoken, and a sharp slap sound is distinctly audible.
- Gemini evidence: Whisper detects 'Help' from 0.00s to 0.18s, which is confirmed by listening to the audio. A clear slap sound is heard around 1.00s.
- Detail file: `analysis_results/details/whisper_A_TP_Sp_Si_So_rel_ord_SoSpSi_v2.txt`

#### TP — Sp_Si_So_rel_ord_SoSiSp v2

- Human: `yes` / Gemini: `yes`
- Temporal type: `relative_order`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: The audio track contains a clear slap sound and the spoken word 'help', satisfying both required audio events.
- Gemini evidence: A sharp slap sound is heard at 0.29 seconds, and the word 'help' is clearly spoken starting around 2.0 seconds, which is also supported by the Whisper transcription.
- Detail file: `analysis_results/details/whisper_A_TP_Sp_Si_So_rel_ord_SoSiSp_v2.txt`

#### TP — Sp_So_rel_ord_SpSo v1

- Human: `yes` / Gemini: `yes`
- Temporal type: `relative_order`
- Modality: `Speech + Action (sounding)`
- Gemini reason: The speech event 'help' is clearly spoken and intelligible at the beginning of the video. A clear, sharp slap sound is heard later in the video, matching the prompt's requirements.
- Gemini evidence: Whisper detects 'help' between 0.00-0.34s, which is confirmed by listening. A sharp slap sound is clearly audible at 3.00s.
- Detail file: `analysis_results/details/whisper_A_TP_Sp_So_rel_ord_SpSo_v1.txt`

#### TN — Sp_Si_abs_sync_cnt v1

- Human: `no` / Gemini: `no`
- Temporal type: `absolute_sync_count`
- Modality: `Speech + Action (silent)`
- Gemini reason: The required speech event 'help' is not clearly and cleanly spoken; the audio contains a distorted utterance transcribed as 'with help'.
- Gemini evidence: Whisper transcription identifies 'with help' between 1.95s and 3.13s, indicating extra, unclear speech before the target word.
- Detail file: `analysis_results/details/whisper_A_TN_Sp_Si_abs_sync_cnt_v1.txt`

#### TN — Sp_Si_So_abs_sync_cnt v1

- Human: `no` / Gemini: `no`
- Temporal type: `absolute_sync_count`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: The word 'help' is spoken only once instead of the required two times, and the slap sound is completely absent.
- Gemini evidence: Whisper detects 'help' at 0.00-0.36s. No second 'help' is heard, and no sharp slap sounds are audible at any point in the audio.
- Detail file: `analysis_results/details/whisper_A_TN_Sp_Si_So_abs_sync_cnt_v1.txt`

#### TN — Sp_Si_So_rel_ord_SpSiSo v2

- Human: `no` / Gemini: `no`
- Temporal type: `relative_order`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: The spoken word 'help' is correctly present and audible, but the required sharp slap sound for the thigh slap is completely missing.
- Gemini evidence: Whisper and audio inspection confirm 'help' is spoken between 0.00-0.30s. However, there is no audio or slap sound at all when the visible strike occurs around 2.95s.
- Detail file: `analysis_results/details/whisper_A_TN_Sp_Si_So_rel_ord_SpSiSo_v2.txt`

#### FP — Sp_So_rel_sync v1

- Human: `no` / Gemini: `yes`
- Temporal type: `relative_synchronization`
- Modality: `Speech + Action (sounding)`
- Gemini reason: The spoken word 'help' and the sharp slap sound are both present and clearly identifiable in the audio track.
- Gemini evidence: Whisper ASR detects the word 'Help' between 0.00 and 0.28 seconds, and a clear slap sound is audible around 1.4 seconds.
- Detail file: `analysis_results/details/whisper_A_FP_Sp_So_rel_sync_v1.txt`

#### FP — Sp_Si_rel_ord_SiSp v3

- Human: `no` / Gemini: `yes`
- Temporal type: `relative_order`
- Modality: `Speech + Action (silent)`
- Gemini reason: The word 'help' is clearly audible and intelligible.
- Gemini evidence: Audio contains the clear spoken word 'help' at the beginning of the video, supported by Whisper transcription.
- Detail file: `analysis_results/details/whisper_A_FP_Sp_Si_rel_ord_SiSp_v3.txt`

#### FN — Sp_So_rel_sync_cnt v1

- Human: `yes` / Gemini: `no`
- Temporal type: `relative_sync_count`
- Modality: `Speech + Action (sounding)`
- Gemini reason: The word "help" is barely audible as a faint artifact at the beginning of the video and does not occur twice as required. Multiple slap sounds are present, but the speech component is not clearly audible or correct.
- Gemini evidence: Whisper detects 'help' from 0.00-0.28s, but it is extremely faint. Slap sounds occur multiple times throughout the audio (around 1.0s, 1.7s, 2.5s, 3.5s, and 4.4s).
- Detail file: `analysis_results/details/whisper_A_FN_Sp_So_rel_sync_cnt_v1.txt`

#### FN — Sp_So_abs_sync_cnt v3

- Human: `yes` / Gemini: `no`
- Temporal type: `absolute_sync_count`
- Modality: `Speech + Action (sounding)`
- Gemini reason: The required 'sharp slap sound' is completely missing from the audio. The speech event 'help' occurs three times starting around 3 seconds, rather than at the required times, and the prompt specifies no extra words.
- Gemini evidence: The audio is silent until approximately 3 seconds. Whisper transcription and direct listening confirm 'help' is spoken around 3.3s, 4.0s, and 4.6s. No slap sounds are audible at any point.
- Detail file: `analysis_results/details/whisper_A_FN_Sp_So_abs_sync_cnt_v3.txt`

#### FN — Sp_So_rel_sync_cnt v2

- Human: `yes` / Gemini: `no`
- Temporal type: `relative_sync_count`
- Modality: `Speech + Action (sounding)`
- Gemini reason: The word 'help' is spoken only once instead of the required twice, and the slap sound is very weak and muffled rather than sharp. The second required speech and slap sounds are completely missing.
- Gemini evidence: Whisper ASR and audio playback confirm only one instance of the word 'help' occurring between 0:00 and 0:28, and only one faint thud is heard around 0:21.
- Detail file: `analysis_results/details/whisper_A_FN_Sp_So_rel_sync_cnt_v2.txt`

### V

#### TP — Sp_Si_So_rel_ord_SoSiSp v3

- Human: `yes` / Gemini: `yes`
- Temporal type: `relative_order`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: The person visibly strikes their right thigh with their right hand, subsequently forms a clear thumbs-up pose with their right hand, and exhibits proper mouth movements for the spoken word.
- Gemini evidence: The right hand is seen striking the right thigh around 00:00.250. The person then raises their right hand and forms a thumbs-up pose starting around 00:02.000, holding it thereafter. The person's face and mouth are clearly visible and show speaking motions when 'help' is spoken.
- Detail file: `analysis_results/details/whisper_V_TP_Sp_Si_So_rel_ord_SoSiSp_v3.txt`

#### TP — Sp_Si_So_rel_ord_SoSiSp v1

- Human: `yes` / Gemini: `yes`
- Temporal type: `relative_order`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: The visual events are correctly performed according to the prompt: the person's right hand strikes the right thigh, then the right hand forms a clear thumbs-up pose, and finally, the person's mouth clearly moves to speak.
- Gemini evidence: In the video, the person's right hand (viewer's left) strikes the right thigh making visible contact around 1.00s. The right hand then forms a clear thumbs-up pose from 1.83s to 2.83s. At 3.00s, the person's mouth visibly moves to form speech.
- Detail file: `analysis_results/details/whisper_V_TP_Sp_Si_So_rel_ord_SoSiSp_v1.txt`

#### TP — Sp_Si_So_rel_ord_SoSpSi v2

- Human: `yes` / Gemini: `yes`
- Temporal type: `relative_order`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: The required visual actions and speaking motions are present and correctly executed. The person's mouth moves appropriately for the speech, the right hand strikes the right thigh, and then the right hand forms a thumbs-up pose.
- Gemini evidence: Visible lip movement occurs at the beginning of the video. The right hand makes visible contact with the right thigh at 1.00s. The right hand then forms a thumbs-up pose at approximately 1.20s and holds it.
- Detail file: `analysis_results/details/whisper_V_TP_Sp_Si_So_rel_ord_SoSpSi_v2.txt`

#### TN — Sp_Si_rel_ord_SpSi v3

- Human: `no` / Gemini: `no`
- Temporal type: `relative_order`
- Modality: `Speech + Action (silent)`
- Gemini reason: The prompt explicitly requires the full face and mouth to be clearly visible, establishing a requirement for visible speaking motion. However, the person's head is entirely cropped out of the frame, failing this visual speech requirement, even though the right-hand thumbs-up action is correctly performed.
- Gemini evidence: The video only frames the person from the chest down. The face and mouth are never visible to show speaking motion. The person's right hand forms a thumbs-up starting around 0.66s.
- Detail file: `analysis_results/details/whisper_V_TN_Sp_Si_rel_ord_SpSi_v3.txt`

#### TN — Sp_So_rel_ord_SpSo v2

- Human: `no` / Gemini: `no`
- Temporal type: `relative_order`
- Modality: `Speech + Action (sounding)`
- Gemini reason: The required visible lip/mouth motion for the word 'help' is completely absent. Furthermore, the visible action is incorrect, as the person lifts both hands, claps them together, and slaps both thighs, rather than just lifting the right hand to slap the right thigh once.
- Gemini evidence: The person's mouth remains completely closed during the speech audio (0.00-0.25s). At 0.66s, both hands are lifted, they clap together at 1.00s, and then both hands slap down on the thighs at 1.12s.
- Detail file: `analysis_results/details/whisper_V_TN_Sp_So_rel_ord_SpSo_v2.txt`

#### TN — Sp_So_rel_sync_cnt v1

- Human: `no` / Gemini: `no`
- Temporal type: `relative_sync_count`
- Modality: `Speech + Action (sounding)`
- Gemini reason: The visible speaking motion for the word "help" is entirely missing, as the person's mouth remains closed. Additionally, the visible slapping action alternates between the left and right hands, rather than strictly using the right hand to strike the right thigh.
- Gemini evidence: The mouth does not move at the start of the video. The person slaps their left thigh with their left hand at 0.6-1.1s, 1.4-1.8s, and 4.0-4.5s, and their right thigh with their right hand at 2.3-2.7s and 3.2-3.7s.
- Detail file: `analysis_results/details/whisper_V_TN_Sp_So_rel_sync_cnt_v1.txt`

#### FP — Sp_Si_So_abs_ord_SoSpSi v1

- Human: `no` / Gemini: `yes`
- Temporal type: `absolute_order`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: The video correctly shows the person slapping their right thigh with their right hand, clear visible mouth movement for speaking, and the right hand forming a clear thumbs-up.
- Gemini evidence: At 1.0 seconds, the right hand visibly strikes the right thigh. Around 3.5 seconds, the person's mouth moves to speak. Concurrently, the right hand is raised and forms a thumbs-up pose, which is held until the end of the video.
- Detail file: `analysis_results/details/whisper_V_FP_Sp_Si_So_abs_ord_SoSpSi_v1.txt`

#### FP — Si_So_rel_ord_SoSi v1

- Human: `no` / Gemini: `yes`
- Temporal type: `relative_order`
- Modality: `Action (silent) + Action (sounding)`
- Gemini reason: Both required visual actions, slapping the right thigh with the right hand and forming a right-hand thumbs-up pose, are clearly visible and correctly performed.
- Gemini evidence: The video shows the actor's right hand lifting and striking the right thigh at 1.000s. Subsequently, the right hand forms a thumbs-up pose starting around 1.792s and holds it clearly from 1.958s until the end of the video.
- Detail file: `analysis_results/details/whisper_V_FP_Si_So_rel_ord_SoSi_v1.txt`

#### FP — Sp_Si_So_rel_ord_SpSoSi v2

- Human: `no` / Gemini: `yes`
- Temporal type: `relative_order`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: The visual actions are correctly performed: visible speaking motion, striking the right thigh with the right hand, and forming a thumbs-up pose.
- Gemini evidence: The person's mouth moves between 0.00-0.20s. The right hand raises and visibly strikes the right thigh at 1.58s. The right hand then forms a clear thumbs-up pose starting around 3.33s and holds it.
- Detail file: `analysis_results/details/whisper_V_FP_Sp_Si_So_rel_ord_SpSoSi_v2.txt`

#### FN — Sp_Si_So_rel_ord_SoSpSi v3

- Human: `yes` / Gemini: `no`
- Temporal type: `relative_order`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: While the right hand slaps the thigh and forms a thumbs-up pose, the prompt explicitly requires the full face and mouth to remain clearly visible. The person's face is mostly cropped out at the top of the frame, preventing clear observation of the speaking action.
- Gemini evidence: The right hand slaps the right thigh at 0.25s and forms a thumbs-up starting around 1.04s. However, the upper half of the face and the mouth are consistently cut off by the top edge of the frame throughout the video.
- Detail file: `analysis_results/details/whisper_V_FN_Sp_Si_So_rel_ord_SoSpSi_v3.txt`

#### FN — Si_So_abs_sync_cnt v3

- Human: `yes` / Gemini: `no`
- Temporal type: `absolute_sync_count`
- Modality: `Action (silent) + Action (sounding)`
- Gemini reason: The person does not strike the thigh while holding a thumbs-up pose. Instead, the person forms a thumbs-up in the air, then opens the hand before slapping the thigh with an open palm.
- Gemini evidence: At 2.2 seconds and 3.3 seconds, the right hand forms a thumbs-up in the air. The hand then opens up and strikes the right thigh as an open palm at 2.6 seconds and 3.7 seconds, failing the requirement to maintain the thumbs-up pose during the strike.
- Detail file: `analysis_results/details/whisper_V_FN_Si_So_abs_sync_cnt_v3.txt`

#### FN — Sp_Si_rel_ord_SpSi v1

- Human: `yes` / Gemini: `no`
- Temporal type: `relative_order`
- Modality: `Speech + Action (silent)`
- Gemini reason: The video fails to meet two specific visual requirements: the person uses the wrong hand for the thumbs-up gesture, and their full face is not visible.
- Gemini evidence: The prompt requires the right hand to be used, but the person forms the thumbs-up with their left hand (on the viewer's right). Additionally, the prompt explicitly requires the 'full face' to be clearly visible, but the top half of the person's head (including the eyes) is cropped out of the frame.
- Detail file: `analysis_results/details/whisper_V_FN_Sp_Si_rel_ord_SpSi_v1.txt`

### AVB

#### TP — Sp_Si_So_abs_ord_SpSiSo v1

- Human: `yes` / Gemini: `yes`
- Temporal type: `absolute_order`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: The speech audio is temporally aligned with visible lip motion, and the slap sound aligns with the moment the person's right arm makes a striking motion across their body.
- Gemini evidence: Lip movement corresponds with the word 'help' around 1.4-1.8 seconds. The slap sound at 4.7 seconds coincides with the right arm's impact during its swinging motion.
- Detail file: `analysis_results/details/whisper_AVB_TP_Sp_Si_So_abs_ord_SpSiSo_v1.txt`

#### TP — Sp_So_rel_sync v3

- Human: `yes` / Gemini: `yes`
- Temporal type: `relative_synchronization`
- Modality: `Speech + Action (sounding)`
- Gemini reason: The visible mouth movements correspond accurately to the spoken word 'help', and the audible slap sound perfectly matches the visible impact of the hand on the thigh.
- Gemini evidence: Lip motion aligns with the speech audio from 0.00s to 0.30s. The slap sound at approximately 0.35s aligns with the visible contact of the hand on the thigh at 00:00.375.
- Detail file: `analysis_results/details/whisper_AVB_TP_Sp_So_rel_sync_v3.txt`

#### TP — Sp_Si_So_rel_ord_SoSiSp v2

- Human: `yes` / Gemini: `yes`
- Temporal type: `relative_order`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: The required audio events are temporally and causally aligned with their corresponding visual actions.
- Gemini evidence: The slap sound at 0.29s synchronizes exactly with the right hand's visible impact on the thigh. The spoken word 'help' aligns precisely with the visible mouth and lip movements between 2.0s and 2.8s.
- Detail file: `analysis_results/details/whisper_AVB_TP_Sp_Si_So_rel_ord_SoSiSp_v2.txt`

#### TN — Sp_So_rel_sync v1

- Human: `no` / Gemini: `no`
- Temporal type: `relative_synchronization`
- Modality: `Speech + Action (sounding)`
- Gemini reason: While the slap sound is correctly aligned with the visible impact on the thigh, the audio-visual binding for the speech event fails because the mouth and face are not visible.
- Gemini evidence: The slap impact and sound align perfectly around 1.4 seconds. However, due to the framing, there is no visible mouth or lip motion to bind with the speech audio at 0.00-0.28 seconds.
- Detail file: `analysis_results/details/whisper_AVB_TN_Sp_So_rel_sync_v1.txt`

#### TN — Sp_Si_So_rel_sync v1

- Human: `no` / Gemini: `no`
- Temporal type: `relative_synchronization`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: While the slap sound is correctly aligned with the visual impact on the thigh, the speech audio lacks a corresponding visual candidate event because the mouth is entirely cropped out.
- Gemini evidence: The hand strikes the thigh at the same time the slap is heard (around 0.46-0.50s). However, no mouth or lip motion can be seen for the speech from 0.00 to 0.26s.
- Detail file: `analysis_results/details/whisper_AVB_TN_Sp_Si_So_rel_sync_v1.txt`

#### TN — Sp_So_rel_sync v2

- Human: `no` / Gemini: `no`
- Temporal type: `relative_synchronization`
- Modality: `Speech + Action (sounding)`
- Gemini reason: While the speech audio is aligned with the visible mouth motion, the required slapping action and its corresponding sound are both missing, preventing the required audio-visual binding for the sounding action.
- Gemini evidence: Speech is synchronized with lip movement between 0.00 and 0.30 seconds. Neither the visible slap nor the audible slap sound occurs, so their binding is absent.
- Detail file: `analysis_results/details/whisper_AVB_TN_Sp_So_rel_sync_v2.txt`

#### FP — Sp_So_rel_ord_SoSp v1

- Human: `no` / Gemini: `yes`
- Temporal type: `relative_order`
- Modality: `Speech + Action (sounding)`
- Gemini reason: The audio events are correctly synchronized with the visible candidate actions in the video.
- Gemini evidence: The speech audio 'help' perfectly matches the mouth movements at the beginning of the video (00:00.00 - 00:00.20), and the slap sound at 00:01.04 precisely matches the moment the left hand makes contact with the thigh.
- Detail file: `analysis_results/details/whisper_AVB_FP_Sp_So_rel_ord_SoSp_v1.txt`

#### FP — Sp_So_rel_sync_cnt v2

- Human: `no` / Gemini: `yes`
- Temporal type: `relative_sync_count`
- Modality: `Speech + Action (sounding)`
- Gemini reason: For the single occurrence that happens, the spoken word and the slap sound are temporally aligned with the visible mouth motion and hand impact.
- Gemini evidence: The speech audio 'help' aligns with the visible mouth movement from 0:00 to 0:25, and the faint slap sound at 0:21 aligns exactly with the visible hand impact on the thigh.
- Detail file: `analysis_results/details/whisper_AVB_FP_Sp_So_rel_sync_cnt_v2.txt`

#### FP — Si_So_rel_ord_SiSo v1

- Human: `no` / Gemini: `yes`
- Temporal type: `relative_order`
- Modality: `Action (silent) + Action (sounding)`
- Gemini reason: The slap sound is perfectly synchronized with the visible impact of the hand on the thigh.
- Gemini evidence: The audible slap sound at 00:03.042 aligns exactly with the visual frame where the right hand strikes the right thigh.
- Detail file: `analysis_results/details/whisper_AVB_FP_Si_So_rel_ord_SiSo_v1.txt`

#### FN — Sp_So_rel_ord_SpSo v3

- Human: `yes` / Gemini: `no`
- Temporal type: `relative_order`
- Modality: `Speech + Action (sounding)`
- Gemini reason: While the slap sound is correctly synchronized with the visible hand impact, the speech audio cannot be temporally bound to visible lip/mouth motion because the mouth is not clearly visible in the frame.
- Gemini evidence: The slap action and sound align perfectly at 3.00 seconds. However, during the speech audio at 0.00-0.30 seconds, the lack of an in-frame mouth prevents verification of lip synchronization.
- Detail file: `analysis_results/details/whisper_AVB_FN_Sp_So_rel_ord_SpSo_v3.txt`

#### FN — Sp_So_abs_ord_SpSo v2

- Human: `yes` / Gemini: `no`
- Temporal type: `absolute_order`
- Modality: `Speech + Action (sounding)`
- Gemini reason: Neither event is properly bound. The speech audio occurs without any corresponding visible mouth movement, and the visible hand motion occurs without any corresponding slap sound.
- Gemini evidence: Audio of 'help' is heard around 0.5 seconds while the person's mouth is completely still. Visible striking motions begin at 4.2 seconds but are accompanied by silence/noise rather than a slap sound.
- Detail file: `analysis_results/details/whisper_AVB_FN_Sp_So_abs_ord_SpSo_v2.txt`

#### FN — Sp_So_rel_sync_cnt v3

- Human: `yes` / Gemini: `no`
- Temporal type: `relative_sync_count`
- Modality: `Speech + Action (sounding)`
- Gemini reason: The speech audio lacks clear and synchronized visible lip motion, and the slap sound is temporally misaligned with the speech and binds to an incorrect clapping action instead of a thigh slap.
- Gemini evidence: The word 'help' occurs between 0.00s and 0.22s with almost no visible mouth movement. The impact sound at 1.00s aligns with a hand clap, completely separated from the speech, failing the simultaneous binding requirement.
- Detail file: `analysis_results/details/whisper_AVB_FN_Sp_So_rel_sync_cnt_v3.txt`

### TC

#### TP — Sp_Si_So_rel_ord_SoSiSp v2

- Human: `yes` / Gemini: `yes`
- Temporal type: `relative_order`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: The required relative order of the three events is strictly followed.
- Gemini evidence: The slap action occurs first (0.2s - 0.5s), followed by the thumbs-up pose being formed and held (1.3s - 1.6s), and finally the speech event 'help' occurs (2.0s - 2.8s). The sequence is distinctly ordered without overlap or repetition.
- Detail file: `analysis_results/details/whisper_TC_TP_Sp_Si_So_rel_ord_SoSiSp_v2.txt`

#### TP — Si_So_rel_ord_SiSo v2

- Human: `yes` / Gemini: `yes`
- Temporal type: `relative_order`
- Modality: `Action (silent) + Action (sounding)`
- Gemini reason: The required relative order of events is successfully followed: the silent thumbs-up action occurs first, followed by the sounding slap action.
- Gemini evidence: The thumbs-up pose is held throughout the first 4 seconds (00:00.000 to 00:04.000). Only after this pose is completed does the thigh-slapping action occur at 00:04.542.
- Detail file: `analysis_results/details/whisper_TC_TP_Si_So_rel_ord_SiSo_v2.txt`

#### TP — Sp_Si_rel_ord_SpSi v3

- Human: `yes` / Gemini: `yes`
- Temporal type: `relative_order`
- Modality: `Speech + Action (silent)`
- Gemini reason: The relative order constraint is satisfied because the audible speech event finishes before the visible thumbs-up action begins.
- Gemini evidence: The spoken word 'help' ends around 0.26s, and subsequently, the right hand forms the thumbs-up gesture starting at approximately 0.66s.
- Detail file: `analysis_results/details/whisper_TC_TP_Sp_Si_rel_ord_SpSi_v3.txt`

#### TN — Si_So_rel_sync v1

- Human: `no` / Gemini: `no`
- Temporal type: `relative_synchronization`
- Modality: `Action (silent) + Action (sounding)`
- Gemini reason: The prompt requires the thumbs-up pose and the thigh slap to be synchronized as a single simultaneous event. However, the video shows them sequentially: the person holds a thumbs-up in the air, then opens the hand to slap the thigh. Furthermore, this sequence is repeated multiple times instead of occurring as a single event.
- Gemini evidence: The right hand is held in a thumbs-up pose around 0.25s-0.45s, but changes to a flat open hand before striking the thigh at 0.54s. This disjointed, sequential action is repeated at 1.20s-1.54s and 3.16s-3.54s.
- Detail file: `analysis_results/details/whisper_TC_TN_Si_So_rel_sync_v1.txt`

#### TN — Si_So_rel_sync v3

- Human: `no` / Gemini: `no`
- Temporal type: `relative_synchronization`
- Modality: `Action (silent) + Action (sounding)`
- Gemini reason: The video fails the synchronization constraint because the target events occur sequentially rather than simultaneously. The person slaps the thigh with an open hand first, and only forms the thumbs-up pose afterward.
- Gemini evidence: The right hand strikes the thigh with an open palm at 0:01.000. It is only later, starting around 0:01.500, that the right hand is raised into a thumbs-up pose, violating the requirement that the slap occur while the hand is held in a thumbs-up pose.
- Detail file: `analysis_results/details/whisper_TC_TN_Si_So_rel_sync_v3.txt`

#### TN — Sp_Si_abs_sync_cnt v3

- Human: `no` / Gemini: `no`
- Temporal type: `absolute_sync_count`
- Modality: `Speech + Action (silent)`
- Gemini reason: The video fails to satisfy the specified temporal count and schedule. The prompt requires two synchronized occurrences of speech and the thumbs-up action at 1.5s and 3.5s. The video only contains one occurrence of the speech event starting late at 2.3s, and completely misses the second required occurrence.
- Gemini evidence: The first speech event happens at 2.32s instead of 1.5s. At 3.5s, there is no audible speech and no visible speaking motion, meaning the second required synchronized bundle is absent.
- Detail file: `analysis_results/details/whisper_TC_TN_Sp_Si_abs_sync_cnt_v3.txt`

#### FP — Si_So_rel_sync_cnt v2

- Human: `no` / Gemini: `yes`
- Temporal type: `relative_sync_count`
- Modality: `Action (silent) + Action (sounding)`
- Gemini reason: The synchronized bundle of the right hand holding a thumbs-up pose and striking the thigh occurs exactly two times, fulfilling the specified count.
- Gemini evidence: The synchronized occurrences take place exactly twice (at 00:00.250 and 00:01.167), with a brief reset in between, and no additional target actions occur afterward.
- Detail file: `analysis_results/details/whisper_TC_FP_Si_So_rel_sync_cnt_v2.txt`

#### FP — Sp_So_rel_ord_SpSo v3

- Human: `no` / Gemini: `yes`
- Temporal type: `relative_order`
- Modality: `Speech + Action (sounding)`
- Gemini reason: The required temporal order is satisfied, as the speech event concludes entirely before the slapping action occurs.
- Gemini evidence: The speech audio ends around 0.30 seconds. The person then lifts their right hand at 2.37 seconds and slaps their thigh at 3.00 seconds, maintaining the requested sequence.
- Detail file: `analysis_results/details/whisper_TC_FP_Sp_So_rel_ord_SpSo_v3.txt`

#### FP — Sp_So_rel_sync v3

- Human: `no` / Gemini: `yes`
- Temporal type: `relative_synchronization`
- Modality: `Speech + Action (sounding)`
- Gemini reason: The target events (speech and sounding action) occur in tight synchronization as requested.
- Gemini evidence: The speech 'help' and the visible slapping action with its corresponding sound occur simultaneously within the first 0.4 seconds of the video, satisfying the required synchronization.
- Detail file: `analysis_results/details/whisper_TC_FP_Sp_So_rel_sync_v3.txt`

#### FN — Sp_Si_So_rel_ord_SpSoSi v2

- Human: `yes` / Gemini: `no`
- Temporal type: `relative_order`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: The temporal sequence is broken because the sounding action of slapping the thigh is completely desynchronized, failing to form a unified event in the required order.
- Gemini evidence: The requirement is a sequence of Speech -> Synchronized Slap Action -> Thumbs Up. Because the slap sound (1.00s) occurs long before the visual impact (1.58s), the second required sequence element is not successfully executed.
- Detail file: `analysis_results/details/whisper_TC_FN_Sp_Si_So_rel_ord_SpSoSi_v2.txt`

#### FN — Sp_Si_So_abs_sync_cnt v2

- Human: `yes` / Gemini: `no`
- Temporal type: `absolute_sync_count`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: The specified temporal constraint structure is not satisfied because the required target bundle involving the right hand never occurs. Furthermore, the actions that do occur happen earlier than scheduled.
- Gemini evidence: The prompt requires synchronized bundles with the right hand at 1.5 and 3.5 seconds. The video shows actions with the left hand at approximately 1.0 and 3.0 seconds, leaving the right-hand constraint unmet.
- Detail file: `analysis_results/details/whisper_TC_FN_Sp_Si_So_abs_sync_cnt_v2.txt`

#### FN — Si_So_rel_sync_cnt v3

- Human: `yes` / Gemini: `no`
- Temporal type: `relative_sync_count`
- Modality: `Action (silent) + Action (sounding)`
- Gemini reason: Because the required target action (right hand striking right thigh) is not performed, the temporal constraint of this specific synchronized bundle occurring exactly twice is not satisfied.
- Gemini evidence: The right hand never performs the target slapping action, resulting in zero occurrences of the specified target event instead of the required two.
- Detail file: `analysis_results/details/whisper_TC_FN_Si_So_rel_sync_cnt_v3.txt`

### CC

#### TP — Sp_Si_So_abs_ord_SpSoSi v1

- Human: `yes` / Gemini: `yes`
- Temporal type: `absolute_order`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: The video complies with all non-core constraints. The scene, camera shot, and initial pose match the prompt. No extra words, sounds, or actions are present, and the person holds still after the final event.
- Gemini evidence: A static medium shot in a plain room shows one person whose face, torso, hands, and thighs are visible. They begin with hands resting on their thighs. No subtitles or background music are present. After the thumbs-up is formed, the person remains still until the end of the video.
- Detail file: `analysis_results/details/whisper_CC_TP_Sp_Si_So_abs_ord_SpSoSi_v1.txt`

#### TP — Sp_Si_So_rel_ord_SoSiSp v1

- Human: `yes` / Gemini: `yes`
- Temporal type: `relative_order`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: The video adheres to all scene, camera, and specific action constraints, including starting with hands on thighs, no extra sounds/speech, and remaining still after the final event.
- Gemini evidence: The scene is a plain indoor room with a static medium shot. The subject starts with hands resting on the thighs. No additional words are spoken, no background music is heard, and after the speech ends around 3.50s, the subject rests hands on thighs and remains still.
- Detail file: `analysis_results/details/whisper_CC_TP_Sp_Si_So_rel_ord_SoSiSp_v1.txt`

#### TP — Sp_Si_So_rel_ord_SpSiSo v3

- Human: `yes` / Gemini: `yes`
- Temporal type: `relative_order`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: The video adheres to all scene, camera, and specific setting constraints. The person is alone in a plain room, the framing is correct, the initial pose is correct, and there are no extra actions, sounds, or words.
- Gemini evidence: The person is in a plain indoor room, framed in a static medium shot with both hands starting on their thighs. No actions occur after the final slap at 3.00, and no background music or extra events are present.
- Detail file: `analysis_results/details/whisper_CC_TP_Sp_Si_So_rel_ord_SpSiSo_v3.txt`

#### TN — Si_So_abs_ord_SiSo v2

- Human: `no` / Gemini: `no`
- Temporal type: `absolute_order`
- Modality: `Action (silent) + Action (sounding)`
- Gemini reason: The video violates the framing constraints and the post-event stillness constraint.
- Gemini evidence: The person's full face is not visible (the top of the head is cropped out), violating the 'full face' requirement. Furthermore, after the initial slap at 3.66s, the person performs an extra, unprompted tap on the thigh at 4.16s, violating the rule that no new target action occurs after the final event.
- Detail file: `analysis_results/details/whisper_CC_TN_Si_So_abs_ord_SiSo_v2.txt`

#### TN — Sp_Si_So_rel_ord_SiSoSp v2

- Human: `no` / Gemini: `no`
- Temporal type: `relative_order`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: The video violates the starting pose constraint, uses the wrong hand for the initial thumbs-up (both hands instead of just the right), and includes a repeated thumbs-up action after the target events.
- Gemini evidence: The person starts with both hands in a thumbs-up pose instead of resting on their thighs. A second thumbs-up action is performed at the end of the video, violating the 'no new target action' constraint.
- Detail file: `analysis_results/details/whisper_CC_TN_Sp_Si_So_rel_ord_SiSoSp_v2.txt`

#### TN — Sp_Si_So_rel_sync_cnt v2

- Human: `no` / Gemini: `no`
- Temporal type: `relative_sync_count`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: The video violates the framing constraint requiring the full face to stay visible, and it contains an extra action/sound violating the count and post-event stillness constraints.
- Gemini evidence: The top half of the person's head is cropped out of the frame. Additionally, a third slap occurs at 3.5s, which is an extra action beyond the specified two repetitions.
- Detail file: `analysis_results/details/whisper_CC_TN_Sp_Si_So_rel_sync_cnt_v2.txt`

#### FP — Si_So_rel_ord_SiSo v2

- Human: `no` / Gemini: `yes`
- Temporal type: `relative_order`
- Modality: `Action (silent) + Action (sounding)`
- Gemini reason: The video complies with all constraints: the scene is a plain indoor room, the camera is a static medium shot, only one person is present, and no additional actions occur after the final event.
- Gemini evidence: The person remains seated in a static medium shot. After the slap at 00:04.542, the hands rest on the thighs until the end of the video without any extra actions, speech, or sounds.
- Detail file: `analysis_results/details/whisper_CC_FP_Si_So_rel_ord_SiSo_v2.txt`

#### FP — Sp_Si_So_rel_sync_cnt v1

- Human: `no` / Gemini: `yes`
- Temporal type: `relative_sync_count`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: The video respects the negative constraints and setting requirements: it features a plain indoor room, a static medium shot, one person with hands initially on thighs, and no extra words or background music.
- Gemini evidence: Visual inspection confirms the continuous visibility of the required body parts, a plain background, and no extraneous text, music, or extra speech are detected.
- Detail file: `analysis_results/details/whisper_CC_FP_Sp_Si_So_rel_sync_cnt_v1.txt`

#### FP — Sp_So_abs_sync v1

- Human: `no` / Gemini: `yes`
- Temporal type: `absolute_synchronization`
- Modality: `Speech + Action (sounding)`
- Gemini reason: The video adheres to the scene, camera, and subject constraints without any extra actions, speech, or background noise.
- Gemini evidence: A single person sits in a plain indoor room facing the camera in a static medium shot. There is no background music, no subtitles, and no additional actions occur after the final slap event.
- Detail file: `analysis_results/details/whisper_CC_FP_Sp_So_abs_sync_v1.txt`

#### FN — Si_So_abs_sync v2

- Human: `yes` / Gemini: `no`
- Temporal type: `absolute_synchronization`
- Modality: `Action (silent) + Action (sounding)`
- Gemini reason: The video violates constraints by including a large, separate hand-raising motion before the strike, and the right hand temporarily goes out of frame, violating the visibility constraint.
- Gemini evidence: Between 2.6 and 3.2 seconds, the actor raises his right arm high in the air, with the hand leaving the top of the frame, directly violating the prompt's instruction against a separate hand-raising motion and the requirement to keep both hands visible.
- Detail file: `analysis_results/details/whisper_CC_FN_Si_So_abs_sync_v2.txt`

#### FN — Sp_So_abs_ord_SpSo v2

- Human: `yes` / Gemini: `no`
- Temporal type: `absolute_order`
- Modality: `Speech + Action (sounding)`
- Gemini reason: The generated video fails several constraints: the mouth is not visible moving as required, the action consists of multiple extra/glitchy motions rather than a single strike, and the person does not remain still after a single event.
- Gemini evidence: The mouth never moves. The hand performs a continuous looping striking motion from 4.2 seconds to the end of the video, violating the single slap and post-event stillness constraints.
- Detail file: `analysis_results/details/whisper_CC_FN_Sp_So_abs_ord_SpSo_v2.txt`

#### FN — Sp_So_rel_sync v3

- Human: `yes` / Gemini: `no`
- Temporal type: `relative_synchronization`
- Modality: `Speech + Action (sounding)`
- Gemini reason: The prompt specifies that only the right hand should strike the right thigh, but the video shows the person using both hands to strike both thighs simultaneously, which constitutes an extra, unprompted action.
- Gemini evidence: From 00:00.000 to 00:00.375, both the left and right hands lift and strike their respective thighs, violating the unilateral constraint implied by specifying only the right hand.
- Detail file: `analysis_results/details/whisper_CC_FN_Sp_So_rel_sync_v3.txt`

## clap

### A

#### TP — Sp_Si_So_abs_ord_SoSpSi v1

- Human: `yes` / Gemini: `yes`
- Temporal type: `absolute_order`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: A sharp slap sound is clearly audible, and the spoken word 'help' is clearly pronounced and easy to distinguish. No extra words or unrequested sounds are present.
- Gemini evidence: A sharp slap sound occurs at approximately 1.0 second, and the spoken word 'help' is heard around 2.5 seconds.
- Detail file: `analysis_results/details/clap_A_TP_Sp_Si_So_abs_ord_SoSpSi_v1.txt`

#### TP — Sp_So_rel_ord_SpSo v1

- Human: `yes` / Gemini: `yes`
- Temporal type: `relative_order`
- Modality: `Speech + Action (sounding)`
- Gemini reason: The spoken word 'help' is clearly audible with no extra words, and a sharp slap sound is heard later in the audio.
- Gemini evidence: Speech 'help' is heard around 00:00.30, and a distinct slap sound is heard around 00:04.00, supported by the audio track and CLAP window [3.50 - 4.25].
- Detail file: `analysis_results/details/clap_A_TP_Sp_So_rel_ord_SpSo_v1.txt`

#### TP — Si_So_abs_sync v3

- Human: `yes` / Gemini: `yes`
- Temporal type: `absolute_synchronization`
- Modality: `Action (silent) + Action (sounding)`
- Gemini reason: A distinct, sharp slap sound is clearly audible, matching the prompt's requirement for the sounding action.
- Gemini evidence: A slapping sound is heard around 2.0 seconds, which is supported by the CLAP evidence showing increased similarity for 'slapping_the_thigh' around this time.
- Detail file: `analysis_results/details/clap_A_TP_Si_So_abs_sync_v3.txt`

#### TN — Sp_Si_So_abs_sync v2

- Human: `no` / Gemini: `no`
- Temporal type: `absolute_synchronization`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: The required speech event 'help' and the sharp slap sound are completely absent from the audio.
- Gemini evidence: The audio track is effectively silent. There are no spoken words or slap sounds audible, which is consistent with the low CLAP scores for 'slapping_the_thigh' and 'a person speaking'.
- Detail file: `analysis_results/details/clap_A_TN_Sp_Si_So_abs_sync_v2.txt`

#### TN — Sp_Si_So_abs_sync v3

- Human: `no` / Gemini: `no`
- Temporal type: `absolute_synchronization`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: The video is completely silent, meaning neither the spoken word 'help' nor the requested sharp slap sound are present.
- Gemini evidence: Direct audio inspection reveals an entirely silent audio track for the duration of the video.
- Detail file: `analysis_results/details/clap_A_TN_Sp_Si_So_abs_sync_v3.txt`

#### TN — Sp_Si_So_abs_sync_cnt v1

- Human: `no` / Gemini: `no`
- Temporal type: `absolute_sync_count`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: The required speech 'help' and the sharp slap sound are absent from the audio.
- Gemini evidence: No speech is transcribed or audible, and CLAP scores for slapping sounds are extremely low throughout the video.
- Detail file: `analysis_results/details/clap_A_TN_Sp_Si_So_abs_sync_cnt_v1.txt`

#### FP — Sp_Si_abs_sync_cnt v1

- Human: `no` / Gemini: `yes`
- Temporal type: `absolute_sync_count`
- Modality: `Speech + Action (silent)`
- Gemini reason: Speech is present in the audio track, consistent with the person saying 'help'.
- Gemini evidence: CLAP scores show a peak for 'a person speaking' between 1.00 and 1.75 seconds, matching the expected speech event.
- Detail file: `analysis_results/details/clap_A_FP_Sp_Si_abs_sync_cnt_v1.txt`

#### FP — Sp_So_rel_sync v1

- Human: `no` / Gemini: `yes`
- Temporal type: `relative_synchronization`
- Modality: `Speech + Action (sounding)`
- Gemini reason: The audio contains the spoken word 'help' and a clear slap sound.
- Gemini evidence: The word 'help' is heard at the beginning of the audio track, and a distinct slap sound is heard around 1.4 seconds.
- Detail file: `analysis_results/details/clap_A_FP_Sp_So_rel_sync_v1.txt`

#### FP — Sp_Si_So_rel_ord_SpSiSo v2

- Human: `no` / Gemini: `yes`
- Temporal type: `relative_order`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: The speech event 'help' and the sharp slap sound are both clearly audible and intelligible in the audio track.
- Gemini evidence: The word 'help' is heard around 0:00-0:01, and a distinct slap sound is heard at approximately 0:02.9.
- Detail file: `analysis_results/details/clap_A_FP_Sp_Si_So_rel_ord_SpSiSo_v2.txt`

#### FN — Sp_So_abs_sync_cnt v1

- Human: `yes` / Gemini: `no`
- Temporal type: `absolute_sync_count`
- Modality: `Speech + Action (sounding)`
- Gemini reason: The required slap sounds are present, but the speech event 'help' is completely inaudible.
- Gemini evidence: Slap sounds can be heard at approximately 2.0 seconds and 4.0 seconds, which is supported by CLAP scores for 'slapping_the_thigh' peaking in those windows. However, no spoken words are heard at any point in the audio, and CLAP scores for 'a person speaking' are negative during the corresponding intervals.
- Detail file: `analysis_results/details/clap_A_FN_Sp_So_abs_sync_cnt_v1.txt`

#### FN — Sp_So_abs_ord_SpSo v3

- Human: `yes` / Gemini: `no`
- Temporal type: `absolute_order`
- Modality: `Speech + Action (sounding)`
- Gemini reason: A sharp slap sound is clearly audible, but the speech sound at 1.5 seconds is garbled and unintelligible, failing to clearly articulate the required word 'help'.
- Gemini evidence: Audio contains a vocalization around 1.5 seconds that lacks the distinct consonants and vowels of the word 'help', and a sharp slap sound at 3.6 seconds. No ASR transcription detected valid speech.
- Detail file: `analysis_results/details/clap_A_FN_Sp_So_abs_ord_SpSo_v3.txt`

#### FN — Sp_Si_So_rel_sync v2

- Human: `yes` / Gemini: `no`
- Temporal type: `relative_synchronization`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: There is no clear evidence of a sharp slap sound in the audio, as CLAP scores for 'slapping_the_thigh' are very low and dominated by silence/background noise. Additionally, clear and complete speech for 'help' is not evident.
- Gemini evidence: CLAP scores for 'slapping_the_thigh' peak at a very low 0.125, while negative anchors like 'silence' are significantly higher throughout most of the video.
- Detail file: `analysis_results/details/clap_A_FN_Sp_Si_So_rel_sync_v2.txt`

### V

#### TP — Sp_Si_So_rel_ord_SiSpSo v3

- Human: `yes` / Gemini: `yes`
- Temporal type: `relative_order`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: The required visual actions and speaking behaviors are correctly depicted. The person performs a thumbs-up, slaps their thigh, and has visible mouth movements.
- Gemini evidence: The person's mouth moves to articulate speech from 0.00 to 1.00 seconds. A clear right-handed thumbs-up pose is formed and held between 1.25 and 1.87 seconds. The right hand then strikes the top of the right thigh, making visible contact around 4.00 seconds.
- Detail file: `analysis_results/details/clap_V_TP_Sp_Si_So_rel_ord_SiSpSo_v3.txt`

#### TP — Sp_Si_So_abs_ord_SiSpSo v3

- Human: `yes` / Gemini: `yes`
- Temporal type: `absolute_order`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: The person visibly performs the required actions: forming a thumbs-up pose with the right hand, visibly speaking, and striking the right thigh with the right hand.
- Gemini evidence: The right hand forms a thumbs-up pose starting around 2.4 seconds. The person's mouth clearly moves to speak the word 'help' around 3.6 seconds. The right hand moves down and visibly strikes the right thigh around 4.1 seconds.
- Detail file: `analysis_results/details/clap_V_TP_Sp_Si_So_abs_ord_SiSpSo_v3.txt`

#### TP — Sp_Si_So_rel_ord_SpSoSi v3

- Human: `yes` / Gemini: `yes`
- Temporal type: `relative_order`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: The visual actions and sequence match the prompt perfectly: the person starts with hands on thighs, speaks, strikes their right thigh with their right hand, and then forms and holds a thumbs-up with their right hand.
- Gemini evidence: The video shows lip movement corresponding to speech at the beginning, followed by the right hand rising and striking the right thigh at 00:02.208, and then the right hand forming a thumbs-up pose starting around 00:03.333 and holding it until the end of the video.
- Detail file: `analysis_results/details/clap_V_TP_Sp_Si_So_rel_ord_SpSoSi_v3.txt`

#### TN — Si_So_abs_sync_cnt v2

- Human: `no` / Gemini: `no`
- Temporal type: `absolute_sync_count`
- Modality: `Action (silent) + Action (sounding)`
- Gemini reason: The visual actions do not match the prompt's requirements. The person raises their hand to form a thumbs-up without striking the thigh, and a later strike is performed without a clear thumbs-up pose.
- Gemini evidence: Around 2.0-2.4 seconds, the right hand is raised into a thumbs-up pose but does not strike the thigh. Around 4.1-4.5 seconds, the hand strikes the thigh, but it is not in a clear thumbs-up pose. Furthermore, the prompt required the thumbs-up to not be a separate raising motion, which was violated.
- Detail file: `analysis_results/details/clap_V_TN_Si_So_abs_sync_cnt_v2.txt`

#### TN — Sp_Si_So_abs_sync v3

- Human: `no` / Gemini: `no`
- Temporal type: `absolute_synchronization`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: The person does not exhibit any visible speaking motion. Furthermore, the person raises their left hand into a thumbs-up pose instead of using their right hand, and completely fails to perform the required slapping motion on the thigh.
- Gemini evidence: Video inspection shows no lip movement at any point. Starting around 0.8 seconds, the person's left hand is raised in a thumbs-up pose and held in the air, while the right hand remains still on the thigh.
- Detail file: `analysis_results/details/clap_V_TN_Sp_Si_So_abs_sync_v3.txt`

#### TN — Sp_Si_rel_sync_cnt v1

- Human: `no` / Gemini: `no`
- Temporal type: `relative_sync_count`
- Modality: `Speech + Action (silent)`
- Gemini reason: The visual action is incorrect. The person performs a thumbs-up with their left hand instead of the right hand for the first gesture, and the second gesture uses the right hand but fails to form a clear thumbs-up pose.
- Gemini evidence: From 00:00.125 to 00:00.917, the person's left hand (viewer's right) performs a thumbs-up. From 00:02.417 to 00:03.000, the right hand raises but the hand shape is loose and not a recognizable thumbs-up. Additionally, there is no visible mouth motion for speech.
- Detail file: `analysis_results/details/clap_V_TN_Sp_Si_rel_sync_cnt_v1.txt`

#### FP — Sp_Si_So_abs_ord_SoSpSi v1

- Human: `no` / Gemini: `yes`
- Temporal type: `absolute_order`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: The visible actions match the prompt precisely. The right hand strikes the right thigh, the person exhibits visible speaking motion for 'help', and the right hand forms and holds a clear thumbs-up pose.
- Gemini evidence: The right hand lifts and strikes the right thigh making visible contact around 1.0 second. Plausible lip movement occurs around 2.2 to 2.8 seconds. The right hand forms a thumbs-up pose starting around 3.3 seconds and holds it through 4.0 seconds until the end of the video.
- Detail file: `analysis_results/details/clap_V_FP_Sp_Si_So_abs_ord_SoSpSi_v1.txt`

#### FP — Sp_So_abs_sync_cnt v1

- Human: `no` / Gemini: `yes`
- Temporal type: `absolute_sync_count`
- Modality: `Speech + Action (sounding)`
- Gemini reason: The video correctly shows the person's right hand slapping their right thigh twice, accompanied by visible mouth movements.
- Gemini evidence: In the video, the person's right hand (on the left side of the screen) lifts and strikes their right thigh around 2.0 seconds and again around 4.0 seconds. The mouth visibly opens during both actions.
- Detail file: `analysis_results/details/clap_V_FP_Sp_So_abs_sync_cnt_v1.txt`

#### FP — Sp_Si_rel_sync_cnt v2

- Human: `no` / Gemini: `yes`
- Temporal type: `relative_sync_count`
- Modality: `Speech + Action (silent)`
- Gemini reason: The person visibly performs the required thumbs-up action with their right hand, and appropriate mouth movements are shown for the speech event.
- Gemini evidence: From the start of the video (0.000s) until around 0.500s, the right hand forms a closed fist with the thumb extended upward while the mouth simultaneously articulates.
- Detail file: `analysis_results/details/clap_V_FP_Sp_Si_rel_sync_cnt_v2.txt`

#### FN — Si_So_abs_sync_cnt v3

- Human: `yes` / Gemini: `no`
- Temporal type: `absolute_sync_count`
- Modality: `Action (silent) + Action (sounding)`
- Gemini reason: The visible action does not match the prompt. The right hand forms a thumbs-up pose while moving up into the air, rather than holding the thumbs-up pose while striking the top of the right thigh. The actual strikes to the thigh happen separately and without the thumbs-up pose.
- Gemini evidence: At 2.0s, 3.0s, and 4.1s, the right hand raises and forms a thumbs-up in the air. It then subsequently drops and hits the thigh around 2.6s, 3.6s, and 4.7s with a relaxed/open hand.
- Detail file: `analysis_results/details/clap_V_FN_Si_So_abs_sync_cnt_v3.txt`

#### FN — Sp_Si_So_rel_ord_SoSpSi v3

- Human: `yes` / Gemini: `no`
- Temporal type: `relative_order`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: The person incorrectly strikes their left thigh instead of their right thigh. Additionally, the required visible speaking motion for 'help' is absent, and the person's full face is not visible as it is cropped out.
- Gemini evidence: At 00:00.250 - 00:00.400, the person's right hand crosses over and strikes their left leg. The video is cropped above the mouth, cutting off the majority of the face, and the mouth shows no speaking motion. A correct thumbs-up is held starting around 00:01.125.
- Detail file: `analysis_results/details/clap_V_FN_Sp_Si_So_rel_ord_SoSpSi_v3.txt`

#### FN — Sp_Si_rel_ord_SpSi v1

- Human: `yes` / Gemini: `no`
- Temporal type: `relative_order`
- Modality: `Speech + Action (silent)`
- Gemini reason: The prompt explicitly requires the full face and mouth to be clearly visible, but the video is framed such that the subject's head and face are almost entirely cropped out, meaning the required visible speaking behavior cannot be confirmed. The thumbs-up action itself is present and correct.
- Gemini evidence: The right hand forms a thumbs-up starting around 0.6s and holds it, but the person's face and mouth are not visible in the frame during the speech event.
- Detail file: `analysis_results/details/clap_V_FN_Sp_Si_rel_ord_SpSi_v1.txt`

### AVB

#### TP — Sp_So_abs_ord_SpSo v3

- Human: `yes` / Gemini: `yes`
- Temporal type: `absolute_order`
- Modality: `Speech + Action (sounding)`
- Gemini reason: The visible speaking motion and the sounding action are properly synchronized with their corresponding audio events.
- Gemini evidence: The garbled vocal sound aligns perfectly with the mouth movement at 1.5 seconds, and the sharp slap sound occurs exactly at the moment of visible hand-to-thigh impact at 3.6 seconds.
- Detail file: `analysis_results/details/clap_AVB_TP_Sp_So_abs_ord_SpSo_v3.txt`

#### TP — Sp_Si_So_abs_ord_SiSpSo v3

- Human: `yes` / Gemini: `yes`
- Temporal type: `absolute_order`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: The visible speaking motion and the visible action of striking the thigh are perfectly aligned with their corresponding sounds.
- Gemini evidence: The mouth movement from 3.6 to 3.9 seconds aligns perfectly with the audible word 'help'. The hand striking the thigh at 4.1 seconds aligns precisely with the sharp slap sound.
- Detail file: `analysis_results/details/clap_AVB_TP_Sp_Si_So_abs_ord_SiSpSo_v3.txt`

#### TP — Sp_Si_So_rel_ord_SiSpSo v3

- Human: `yes` / Gemini: `yes`
- Temporal type: `relative_order`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: The audio events are correctly synchronized with their corresponding visual actions.
- Gemini evidence: The speech 'help' aligns perfectly with the visible mouth movements at the start of the video (0.00-1.00s). The sharp slap sound at 4.00 seconds aligns exactly with the right hand making contact with the right thigh.
- Detail file: `analysis_results/details/clap_AVB_TP_Sp_Si_So_rel_ord_SiSpSo_v3.txt`

#### TN — Sp_Si_So_abs_sync v1

- Human: `no` / Gemini: `no`
- Temporal type: `absolute_synchronization`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: The slap sound is correctly bound to the visible impact, but the speech audio cannot be bound to any visual lip motion because the face is absent.
- Gemini evidence: While the sharp slap sound syncs perfectly with the visible thigh impact at 2.0 seconds, the spoken word 'help' lacks any visible mouth or lip motion to bind to due to the cropped framing.
- Detail file: `analysis_results/details/clap_AVB_TN_Sp_Si_So_abs_sync_v1.txt`

#### TN — Sp_So_rel_ord_SoSp v1

- Human: `no` / Gemini: `no`
- Temporal type: `relative_order`
- Modality: `Speech + Action (sounding)`
- Gemini reason: While the visible slap aligns with the slap sound, the required binding for the speech event fails because both the speech audio and visible speaking motion are entirely absent.
- Gemini evidence: The slap makes contact at 1.000s, perfectly aligned with the sound. However, since there is neither speech audio nor visible lip movement for the word 'help', the audio-visual binding for the second event cannot be established.
- Detail file: `analysis_results/details/clap_AVB_TN_Sp_So_rel_ord_SoSp_v1.txt`

#### TN — Sp_Si_So_rel_sync v1

- Human: `no` / Gemini: `no`
- Temporal type: `relative_synchronization`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: While the slap sound aligns with the visible hand impact, the severe cropping of the face prevents proper verification and binding of the visible speaking motion to the speech audio.
- Gemini evidence: The slap impact at 00:00.250 aligns with the slap sound, but the missing upper face and mostly obscured mouth make it impossible to properly link the speech audio to visible articulation.
- Detail file: `analysis_results/details/clap_AVB_TN_Sp_Si_So_rel_sync_v1.txt`

#### FP — Sp_So_rel_sync_cnt v2

- Human: `no` / Gemini: `yes`
- Temporal type: `relative_sync_count`
- Modality: `Speech + Action (sounding)`
- Gemini reason: The audible speech and the sound of the slap are accurately synchronized with the visible speaking motion and the physical impact of the hand on the thigh.
- Gemini evidence: The slap sound and the spoken word 'help' coincide precisely with the visual impact of the hand on the thigh and the opening of the mouth around 00:00.300.
- Detail file: `analysis_results/details/clap_AVB_FP_Sp_So_rel_sync_cnt_v2.txt`

#### FP — Si_So_abs_ord_SoSi v2

- Human: `no` / Gemini: `yes`
- Temporal type: `absolute_order`
- Modality: `Action (silent) + Action (sounding)`
- Gemini reason: The visible impact of the hand on the thigh is perfectly synchronized with the audible slap sound.
- Gemini evidence: The slap sound is heard at 2.20 seconds, exactly matching the frame where the right hand impacts the right thigh.
- Detail file: `analysis_results/details/clap_AVB_FP_Si_So_abs_ord_SoSi_v2.txt`

#### FP — Sp_Si_So_rel_ord_SpSiSo v2

- Human: `no` / Gemini: `yes`
- Temporal type: `relative_order`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: Both the speech and the non-speech sound are temporally aligned with their respective visible actions.
- Gemini evidence: The spoken word 'help' aligns precisely with the visible lip movements at the beginning of the video, and the slap sound at 0:02.9 matches the exact moment the right hand makes contact with the right thigh.
- Detail file: `analysis_results/details/clap_AVB_FP_Sp_Si_So_rel_ord_SpSiSo_v2.txt`

#### FN — Sp_Si_So_abs_sync_cnt v2

- Human: `yes` / Gemini: `no`
- Temporal type: `absolute_sync_count`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: While the speech aligns with the visible lip movements, the required binding for the sounding action fails because both the thigh slap sound and the visible slapping motion are missing.
- Gemini evidence: Visible lip motion and audible speech synchronize around 1.0s and 3.0s. However, the absence of both the auditory and visual components of the thigh slap results in a failure to bind the sounding action.
- Detail file: `analysis_results/details/clap_AVB_FN_Sp_Si_So_abs_sync_cnt_v2.txt`

#### FN — Sp_Si_So_rel_ord_SpSiSo v3

- Human: `yes` / Gemini: `no`
- Temporal type: `relative_order`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: While the slapping sound is synchronized with the visible strike to the thigh, the audio-visual binding for the speech event fails because both the speech audio and visible mouth movement are absent.
- Gemini evidence: The visible impact at 00:03.042 aligns perfectly with the slap sound, but the total absence of the spoken word 'help' and corresponding lip motion means the required binding for the speech event is unfulfilled.
- Detail file: `analysis_results/details/clap_AVB_FN_Sp_Si_So_rel_ord_SpSiSo_v3.txt`

#### FN — Sp_Si_So_abs_ord_SoSiSp v2

- Human: `yes` / Gemini: `no`
- Temporal type: `absolute_order`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: While the sounding action (slap) is properly synchronized, the speech event is absent in both the audio and visual modalities, meaning no audio-visual binding can exist for the speech requirement.
- Gemini evidence: The slap sound at 1.0 seconds perfectly aligns with the visible impact on the thigh. However, neither speech audio nor visible lip movement occurs for the 'help' speech event.
- Detail file: `analysis_results/details/clap_AVB_FN_Sp_Si_So_abs_ord_SoSiSp_v2.txt`

### TC

#### TP — Si_So_rel_sync_cnt v3

- Human: `yes` / Gemini: `yes`
- Temporal type: `relative_sync_count`
- Modality: `Action (silent) + Action (sounding)`
- Gemini reason: The synchronized bundle of the right hand holding a thumbs-up and slapping the thigh with an accompanying sound occurs exactly two times, with a complete reset to a resting position between the two occurrences.
- Gemini evidence: The first synchronized action occurs around 1.4 seconds, followed by the hands resting on the thighs, and the second synchronized action occurs around 4.3 seconds. No additional occurrences of the sequence happen afterward.
- Detail file: `analysis_results/details/clap_TC_TP_Si_So_rel_sync_cnt_v3.txt`

#### TP — Si_So_rel_ord_SiSo v3

- Human: `yes` / Gemini: `yes`
- Temporal type: `relative_order`
- Modality: `Action (silent) + Action (sounding)`
- Gemini reason: The events occur in the correct relative order specified by the prompt: first the thumbs-up pose is held, and then the thigh slap occurs.
- Gemini evidence: The thumbs-up pose (Event 1) occurs from 0.500s to 2.917s. The thigh slap (Event 2) occurs afterward at 3.292s, satisfying the required sequential order.
- Detail file: `analysis_results/details/clap_TC_TP_Si_So_rel_ord_SiSo_v3.txt`

#### TP — Si_So_rel_ord_SiSo v2

- Human: `yes` / Gemini: `yes`
- Temporal type: `relative_order`
- Modality: `Action (silent) + Action (sounding)`
- Gemini reason: The actions occur in the correct relative order: the silent thumbs-up pose is held first, followed entirely by the sounding slap action.
- Gemini evidence: The thumbs-up pose concludes around 00:04.000, and the slap sequence immediately follows, completing at 00:04.417, perfectly matching the required sequence.
- Detail file: `analysis_results/details/clap_TC_TP_Si_So_rel_ord_SiSo_v2.txt`

#### TN — Sp_Si_So_rel_ord_SiSpSo v3

- Human: `no` / Gemini: `no`
- Temporal type: `relative_order`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: The events do not follow the required chronological order. The prompt specified that the thumbs-up should occur first, followed by the speech, and then the thigh slap. The generated video plays the speech first, followed by the thumbs-up.
- Gemini evidence: The speech 'help' occurs first (0.00-1.00s), followed by the thumbs-up pose (1.25-1.87s), and finally the sounding thigh slap (4.00s). This violates the required sequence of silent action -> speech -> sounding action.
- Detail file: `analysis_results/details/clap_TC_TN_Sp_Si_So_rel_ord_SiSpSo_v3.txt`

#### TN — Sp_Si_rel_sync_cnt v3

- Human: `no` / Gemini: `no`
- Temporal type: `relative_sync_count`
- Modality: `Speech + Action (silent)`
- Gemini reason: The prompt requires the synchronized bundle (saying 'help' and giving a thumbs-up) to be performed exactly two times, but the visual action only occurs once and the audio is completely missing.
- Gemini evidence: The right hand holds a thumbs-up only once at the very beginning (0.000s - 0.125s) before returning to a resting position. The required second repetition never happens, and the speech event is absent for both required instances.
- Detail file: `analysis_results/details/clap_TC_TN_Sp_Si_rel_sync_cnt_v3.txt`

#### TN — Si_So_abs_ord_SiSo v1

- Human: `no` / Gemini: `no`
- Temporal type: `absolute_order`
- Modality: `Action (silent) + Action (sounding)`
- Gemini reason: The events do not occur at the specified absolute times. The thumbs-up occurs much later than the required 1.5 seconds, and the slap occurs later than the required 3.5 seconds.
- Gemini evidence: The prompt requires the thumbs-up at 1.5 seconds and the thigh slap at 3.5 seconds. In the generated video, the right hand remains still until 3.0 seconds, forms the thumbs-up around 3.5 seconds, and slaps the thigh at 4.4 seconds.
- Detail file: `analysis_results/details/clap_TC_TN_Si_So_abs_ord_SiSo_v1.txt`

#### FP — Sp_Si_So_abs_ord_SoSpSi v1

- Human: `no` / Gemini: `yes`
- Temporal type: `absolute_order`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: The absolute schedule and order of the required events are correctly followed without any missing or out-of-order actions.
- Gemini evidence: The slap occurs precisely at 1.0 second, the speech event 'help' occurs at 2.5 seconds, and the thumbs-up is formed and held by 4.0 seconds, satisfying the temporal schedule.
- Detail file: `analysis_results/details/clap_TC_FP_Sp_Si_So_abs_ord_SoSpSi_v1.txt`

#### FP — Sp_Si_So_abs_sync v1

- Human: `no` / Gemini: `yes`
- Temporal type: `absolute_synchronization`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: The available target events satisfy the absolute timing and synchronization requirements.
- Gemini evidence: The spoken word 'help', the audible slap sound, and the visible thigh slap all happen simultaneously at exactly 2.0 seconds as specified in the schedule.
- Detail file: `analysis_results/details/clap_TC_FP_Sp_Si_So_abs_sync_v1.txt`

#### FP — Si_So_rel_ord_SiSo v1

- Human: `no` / Gemini: `yes`
- Temporal type: `relative_order`
- Modality: `Action (silent) + Action (sounding)`
- Gemini reason: The actions occur in the required relative sequence: the silent thumbs-up is completed before the sounding thigh slap.
- Gemini evidence: The thumbs-up is held until approximately 00:02.375, and then the hand moves down to slap the thigh at 00:03.000. No events overlap improperly or appear out of order.
- Detail file: `analysis_results/details/clap_TC_FP_Si_So_rel_ord_SiSo_v1.txt`

#### FN — Sp_Si_So_abs_sync_cnt v2

- Human: `yes` / Gemini: `no`
- Temporal type: `absolute_sync_count`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: The synchronized bundles do not occur as required. The actions occur at the wrong times, and the bundle is incomplete due to the missing slap action and the use of the wrong hand.
- Gemini evidence: The partial bundles (speech and left-hand thumbs-up) occur around 1.0 and 3.0 seconds instead of the requested 1.5 and 3.5 seconds. Furthermore, the required right-hand slap is missing from both occurrences.
- Detail file: `analysis_results/details/clap_TC_FN_Sp_Si_So_abs_sync_cnt_v2.txt`

#### FN — Sp_Si_So_rel_ord_SoSiSp v3

- Human: `yes` / Gemini: `no`
- Temporal type: `relative_order`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: The required temporal order is not met because the first event (the sounding action of slapping the thigh) fails to properly occur as a cohesive, synchronized audiovisual event.
- Gemini evidence: Although a thumbs-up and speech follow sequentially, the foundational first event is broken due to incorrect visual execution and extreme audiovisual misalignment.
- Detail file: `analysis_results/details/clap_TC_FN_Sp_Si_So_rel_ord_SoSiSp_v3.txt`

#### FN — Si_So_rel_ord_SoSi v3

- Human: `yes` / Gemini: `no`
- Temporal type: `relative_order`
- Modality: `Action (silent) + Action (sounding)`
- Gemini reason: Because the person uses the wrong hand for the thumbs-up, the required right-hand thumbs-up event is completely absent, meaning the specified sequence of events is incomplete.
- Gemini evidence: The sounding action occurs first as required, but the subsequent silent action 'right-hand thumbs-up' is missing, as the left hand performs the pose instead.
- Detail file: `analysis_results/details/clap_TC_FN_Si_So_rel_ord_SoSi_v3.txt`

### CC

#### TP — Sp_So_abs_ord_SpSo v3

- Human: `yes` / Gemini: `yes`
- Temporal type: `absolute_order`
- Modality: `Speech + Action (sounding)`
- Gemini reason: The video satisfies all non-core constraints regarding the scene, camera shot, initial pose, continuous visibility, and lack of extra actions or sounds.
- Gemini evidence: The video features a static medium shot in a plain indoor room. The seated person has their hands on their thighs initially. The face, upper body, hands, and thighs remain visible. The person becomes still after the slap, and no extra words or actions are present.
- Detail file: `analysis_results/details/clap_CC_TP_Sp_So_abs_ord_SpSo_v3.txt`

#### TP — Si_So_rel_ord_SiSo v3

- Human: `yes` / Gemini: `yes`
- Temporal type: `relative_order`
- Modality: `Action (silent) + Action (sounding)`
- Gemini reason: The video satisfies all non-core constraints, including the static medium shot, plain indoor room, starting pose, and post-event stillness.
- Gemini evidence: The video features a single person in a plain indoor room, shot with a static medium camera angle. The person starts with hands on thighs, performs the requested actions, and remains still after the final slap with no extra sounds, speech, or actions.
- Detail file: `analysis_results/details/clap_CC_TP_Si_So_rel_ord_SiSo_v3.txt`

#### TP — Sp_Si_So_abs_ord_SiSpSo v3

- Human: `yes` / Gemini: `yes`
- Temporal type: `absolute_order`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: The video adheres to all non-core constraints, including scene, camera, subject positioning, and post-event stillness.
- Gemini evidence: The video features a single seated person in a plain indoor setting, captured in a static medium shot. Both hands, thighs, and the face are clearly visible. The person starts with hands on thighs, speaks no extra words, and remains still after the final thigh-slap event.
- Detail file: `analysis_results/details/clap_CC_TP_Sp_Si_So_abs_ord_SiSpSo_v3.txt`

#### TN — Sp_Si_rel_sync_cnt v2

- Human: `no` / Gemini: `no`
- Temporal type: `relative_sync_count`
- Modality: `Speech + Action (silent)`
- Gemini reason: The video fails to meet the framing and initial state constraints. The full face is not visible, and the person does not start with their right hand resting on their knee or thigh.
- Gemini evidence: The top half of the person's face (from the nose up) is cropped out of the frame for the entire duration, violating the 'full face clearly visible' requirement. Additionally, at 0.000s, the right hand is already raised in motion rather than starting from a resting position.
- Detail file: `analysis_results/details/clap_CC_TN_Sp_Si_rel_sync_cnt_v2.txt`

#### TN — Si_So_abs_sync_cnt v3

- Human: `no` / Gemini: `no`
- Temporal type: `absolute_sync_count`
- Modality: `Action (silent) + Action (sounding)`
- Gemini reason: The video violates several constraints: the thumbs-up involves a raising motion rather than being a held pose, and there is an extra third occurrence of the action violating the post-event stillness constraint.
- Gemini evidence: The right hand explicitly raises to form the thumbs-up pose each time. An extra unprompted action sequence occurs starting at 4.1 seconds.
- Detail file: `analysis_results/details/clap_CC_TN_Si_So_abs_sync_cnt_v3.txt`

#### TN — Si_So_rel_sync_cnt v1

- Human: `no` / Gemini: `no`
- Temporal type: `relative_sync_count`
- Modality: `Action (silent) + Action (sounding)`
- Gemini reason: The video does not satisfy the starting position constraint and violates post-event stillness.
- Gemini evidence: The right hand is already raised in a thumbs-up pose at the beginning of the video instead of resting on the thigh as requested. Furthermore, a third slap occurs at 00:02.250, violating the 'no new target action occurs' constraint after the second event.
- Detail file: `analysis_results/details/clap_CC_TN_Si_So_rel_sync_cnt_v1.txt`

#### FP — Sp_Si_So_rel_ord_SiSpSo v3

- Human: `no` / Gemini: `yes`
- Temporal type: `relative_order`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: The video satisfies all non-core constraints. The setting, shot type, and subject visibility are correct, and there are no extra unprompted actions or speech.
- Gemini evidence: The video features a single person in a plain indoor room, captured in a static medium shot with the face, upper body, hands, and thighs visible. The person remains still after the final thigh slap action, and no extra sounds or speech are introduced.
- Detail file: `analysis_results/details/clap_CC_FP_Sp_Si_So_rel_ord_SiSpSo_v3.txt`

#### FP — Sp_Si_rel_sync_cnt v3

- Human: `no` / Gemini: `yes`
- Temporal type: `relative_sync_count`
- Modality: `Speech + Action (silent)`
- Gemini reason: The video satisfies the scene, camera, and stillness constraints. There are no extra actions, sounds, or other violations.
- Gemini evidence: The video shows a single seated person in a plain indoor room, filmed in a static medium shot. After the initial movement ends around 0.250s, the person remains completely still until the end of the video, and no background music or extra elements are present.
- Detail file: `analysis_results/details/clap_CC_FP_Sp_Si_rel_sync_cnt_v3.txt`

#### FP — Sp_Si_So_abs_sync_cnt v2

- Human: `no` / Gemini: `yes`
- Temporal type: `absolute_sync_count`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: The non-core constraints regarding the scene, camera shot, and person are met. There is no background music, no on-screen text, and the person remains still after the final event.
- Gemini evidence: The video features a static medium shot of a single person in a plain indoor room starting with hands on thighs. No additional target actions occur after the second spoken word.
- Detail file: `analysis_results/details/clap_CC_FP_Sp_Si_So_abs_sync_cnt_v2.txt`

#### FN — Sp_Si_So_abs_sync v3

- Human: `yes` / Gemini: `no`
- Temporal type: `absolute_synchronization`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: While the video adheres to the scene, camera, and people-count constraints, it introduces an unprompted action by having the person raise their left arm, violating the strict action requirements.
- Gemini evidence: The prompt specifically requires the right hand to act, but the person actively raises and holds their left hand instead, constituting an extra/incorrect gesture.
- Detail file: `analysis_results/details/clap_CC_FN_Sp_Si_So_abs_sync_v3.txt`

#### FN — Sp_So_rel_sync v3

- Human: `yes` / Gemini: `no`
- Temporal type: `relative_synchronization`
- Modality: `Speech + Action (sounding)`
- Gemini reason: The video violates constraints regarding the initial state of the hands and the presence of extra actions.
- Gemini evidence: The prompt requires both hands to initially rest on the knees or thighs, but at 00:00.000 the hands are already lifted in the air. Furthermore, the left hand striking the left thigh is an extra, unrequested action.
- Detail file: `analysis_results/details/clap_CC_FN_Sp_So_rel_sync_v3.txt`

#### FN — Sp_Si_So_abs_ord_SpSoSi v1

- Human: `yes` / Gemini: `no`
- Temporal type: `absolute_order`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: The video violates the negative constraint regarding extra sounds and post-event stillness by including an unexplained extra slap sound.
- Gemini evidence: An additional, prominent slap sound occurs at 4.2 seconds in the audio track, but there is no corresponding visible action being performed at that time, which violates the constraint against extra actions/sounds.
- Detail file: `analysis_results/details/clap_CC_FN_Sp_Si_So_abs_ord_SpSoSi_v1.txt`

## whisper_clap

### A

#### TP — Sp_Si_So_abs_ord_SiSpSo v2

- Human: `yes` / Gemini: `yes`
- Temporal type: `absolute_order`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: The required speech event 'help' and the sounding event of a sharp slap are both clearly present and correct in the audio track.
- Gemini evidence: Whisper detects the word 'Help' between 2.35 and 2.99 seconds, matching the audible speech. A clear, sharp slap sound is heard later in the video around 4.6 seconds, which is also supported by CLAP positive scores for 'slapping_the_thigh'.
- Detail file: `analysis_results/details/whisper_clap_A_TP_Sp_Si_So_abs_ord_SiSpSo_v2.txt`

#### TP — Sp_So_rel_ord_SpSo v2

- Human: `yes` / Gemini: `yes`
- Temporal type: `relative_order`
- Modality: `Speech + Action (sounding)`
- Gemini reason: The word 'help' is clearly spoken at the beginning, and a sharp slap sound is heard afterwards, successfully fulfilling the required audio events.
- Gemini evidence: Whisper transcribes 'Help.' from 0.00 to 0.22, and a distinct slap sound is audible at 1.00, which aligns with CLAP sliding-window scores peaking for 'slapping_the_thigh' around 0.50-1.25.
- Detail file: `analysis_results/details/whisper_clap_A_TP_Sp_So_rel_ord_SpSo_v2.txt`

#### TP — Sp_So_abs_ord_SpSo v2

- Human: `yes` / Gemini: `yes`
- Temporal type: `absolute_order`
- Modality: `Speech + Action (sounding)`
- Gemini reason: The audio contains the required spoken word 'help' and a sharp slap sound.
- Gemini evidence: Whisper detects the word 'help' occurring between 0.00 and 1.10 seconds. A sharp slap sound is clearly audible at approximately 4.6 seconds, which is consistent with the CLAP peak in the 4.00-4.75 seconds window.
- Detail file: `analysis_results/details/whisper_clap_A_TP_Sp_So_abs_ord_SpSo_v2.txt`

#### TN — Sp_Si_So_abs_sync_cnt v1

- Human: `no` / Gemini: `no`
- Temporal type: `absolute_sync_count`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: The required word 'help' is only spoken once at the beginning of the video, and the required sharp slap sound is entirely absent.
- Gemini evidence: Whisper detects 'Help' between 0.00 and 0.36 seconds, with no further speech detected. No slap sound is audible in the audio track, and CLAP scores for 'slapping_the_thigh' remain very low throughout.
- Detail file: `analysis_results/details/whisper_clap_A_TN_Sp_Si_So_abs_sync_cnt_v1.txt`

#### TN — Sp_Si_So_abs_sync v3

- Human: `no` / Gemini: `no`
- Temporal type: `absolute_synchronization`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: The speech event 'help' is present and intelligible, but the required sharp slap sound is completely missing from the audio.
- Gemini evidence: Whisper detects 'help' between 1.42s and 1.94s, which is confirmed by listening. However, CLAP scores for 'slapping_the_thigh' are negative or very low throughout, and no slap sound is audible at any point.
- Detail file: `analysis_results/details/whisper_clap_A_TN_Sp_Si_So_abs_sync_v3.txt`

#### TN — Sp_Si_So_abs_sync v2

- Human: `no` / Gemini: `no`
- Temporal type: `absolute_synchronization`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: The word 'help' is clearly spoken, but the required sharp slap sound is completely missing from the audio track.
- Gemini evidence: Whisper detects 'Help' from 0.00 to 0.36 seconds, and direct audio inspection confirms this. There is no slapping sound heard at any point in the video.
- Detail file: `analysis_results/details/whisper_clap_A_TN_Sp_Si_So_abs_sync_v2.txt`

#### FP — Sp_So_rel_sync v1

- Human: `no` / Gemini: `yes`
- Temporal type: `relative_synchronization`
- Modality: `Speech + Action (sounding)`
- Gemini reason: The required speech event ('help') is clearly audible, and the required sounding action (a sharp slap) is also present without any extra target sounds.
- Gemini evidence: Whisper detects 'Help' from 0.00 to 0.28 seconds. A clear slap sound is heard at approximately 1.3 seconds.
- Detail file: `analysis_results/details/whisper_clap_A_FP_Sp_So_rel_sync_v1.txt`

#### FP — Sp_Si_So_rel_ord_SpSiSo v2

- Human: `no` / Gemini: `yes`
- Temporal type: `relative_order`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: The required speech event 'help' is spoken clearly, and a sharp slap sound is audible.
- Gemini evidence: Whisper ASR confirms 'help' at 0.00-0.30s, and a clear slap sound is heard around 2.7s, matching CLAP positive similarities.
- Detail file: `analysis_results/details/whisper_clap_A_FP_Sp_Si_So_rel_ord_SpSiSo_v2.txt`

#### FP — Sp_Si_abs_sync_cnt v1

- Human: `no` / Gemini: `yes`
- Temporal type: `absolute_sync_count`
- Modality: `Speech + Action (silent)`
- Gemini reason: The word 'help' is clearly spoken in the audio track.
- Gemini evidence: Whisper detects 'help' and direct audio inspection confirms a drawn-out pronunciation of the word.
- Detail file: `analysis_results/details/whisper_clap_A_FP_Sp_Si_abs_sync_cnt_v1.txt`

#### FN — Sp_Si_So_abs_ord_SiSpSo v1

- Human: `yes` / Gemini: `no`
- Temporal type: `absolute_order`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: The speech event 'help' is present and audible, but the required sharp slap sound is completely missing from the audio track.
- Gemini evidence: Whisper ASR and direct audio inspection confirm the word 'help' is spoken around 2.5s. However, there is no sharp slap sound audible at 4.0 seconds or anywhere else in the video.
- Detail file: `analysis_results/details/whisper_clap_A_FN_Sp_Si_So_abs_ord_SiSpSo_v1.txt`

#### FN — Sp_Si_So_abs_sync_cnt v3

- Human: `yes` / Gemini: `no`
- Temporal type: `absolute_sync_count`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: The required speech word 'help' is only spoken once at the beginning of the video and is missing for the required second occurrence.
- Gemini evidence: Whisper ASR transcribes 'help' at 0.00-0.28s. Direct audio inspection confirms speech only occurs then, while the required slap sounds are clearly audible around 2.0s and 4.0s.
- Detail file: `analysis_results/details/whisper_clap_A_FN_Sp_Si_So_abs_sync_cnt_v3.txt`

#### FN — Sp_Si_So_abs_sync v1

- Human: `yes` / Gemini: `no`
- Temporal type: `absolute_synchronization`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: The speech event 'help' is present, but the required sharp slap sound is entirely missing from the audio.
- Gemini evidence: Whisper detects 'Help' around 2.22 seconds, but listening to the audio confirms there is no slapping sound present at any point.
- Detail file: `analysis_results/details/whisper_clap_A_FN_Sp_Si_So_abs_sync_v1.txt`

### V

#### TP — Sp_Si_So_rel_ord_SoSiSp v3

- Human: `yes` / Gemini: `yes`
- Temporal type: `relative_order`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: The person visibly strikes their right thigh with their right hand, subsequently forms and holds a clear thumbs-up pose with the right hand, and exhibits visible speaking motion for the speech event.
- Gemini evidence: Video frames show the right hand making contact with the right thigh at 0.333s, forming a thumbs-up pose from 2.250s onwards, and the mouth moving to speak between 3.000s and 3.750s.
- Detail file: `analysis_results/details/whisper_clap_V_TP_Sp_Si_So_rel_ord_SoSiSp_v3.txt`

#### TP — Si_So_abs_ord_SiSo v2

- Human: `yes` / Gemini: `yes`
- Temporal type: `absolute_order`
- Modality: `Action (silent) + Action (sounding)`
- Gemini reason: The visual actions are correctly executed: the person forms a clear thumbs-up with the right hand and subsequently strikes the right thigh with the right hand.
- Gemini evidence: The right hand is seen lifting and forming a thumbs-up pose from 2.8 seconds to 3.5 seconds. Following this, the right hand strikes the top of the right thigh, making visible contact around 4.0 seconds.
- Detail file: `analysis_results/details/whisper_clap_V_TP_Si_So_abs_ord_SiSo_v2.txt`

#### TP — Sp_So_rel_ord_SoSp v2

- Human: `yes` / Gemini: `yes`
- Temporal type: `relative_order`
- Modality: `Speech + Action (sounding)`
- Gemini reason: The visible actions match the prompt. The person's right hand visibly strikes their right thigh, and their mouth clearly moves to articulate the word 'help'.
- Gemini evidence: Video shows the person's right hand lifting and striking the right thigh at exactly 1.0 seconds, making clear physical contact. The person's mouth is fully visible and moves to articulate 'help' from approximately 2.9 to 3.4 seconds.
- Detail file: `analysis_results/details/whisper_clap_V_TP_Sp_So_rel_ord_SoSp_v2.txt`

#### TN — Si_So_abs_ord_SoSi v1

- Human: `no` / Gemini: `no`
- Temporal type: `absolute_order`
- Modality: `Action (silent) + Action (sounding)`
- Gemini reason: The visible events do not match the prompt's requirements. The person raises their right hand significantly when forming the thumbs-up pose, violating the instruction to do so 'without raising the hand'. Additionally, the person's full face and mouth are not visible as the framing cuts off the top of the head.
- Gemini evidence: From 3.4 seconds onwards, the person raises their right hand up to chest/shoulder height to make the thumbs-up gesture. Throughout the video, the framing only shows the neck and chin, failing the 'full face, mouth' visibility requirement.
- Detail file: `analysis_results/details/whisper_clap_V_TN_Si_So_abs_ord_SoSi_v1.txt`

#### TN — Sp_Si_So_rel_sync v1

- Human: `no` / Gemini: `no`
- Temporal type: `relative_synchronization`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: The person does not maintain the thumbs-up pose while striking the thigh, and the starting position is incorrect. Additionally, the full face is not clearly visible as required.
- Gemini evidence: The right hand is already raised in a thumbs-up pose at the start of the video (violating the requirement to start with both hands resting on the thighs). When the hand strikes the thigh at 0.50 seconds, it flattens out, losing the required thumbs-up pose. The top half of the person's face is also cropped out of the frame.
- Detail file: `analysis_results/details/whisper_clap_V_TN_Sp_Si_So_rel_sync_v1.txt`

#### TN — Sp_Si_So_abs_ord_SoSpSi v2

- Human: `no` / Gemini: `no`
- Temporal type: `absolute_order`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: The visual actions of slapping the thigh and forming a thumbs-up with the right hand are present, but the prompt explicitly requires the full face and mouth to be visible. The person's head is completely cropped out, omitting the required visible speaking behavior.
- Gemini evidence: The right hand slaps the right thigh around 2.2 seconds and forms a thumbs-up around 3.3 seconds. However, the video framing crops out the person's face entirely, failing the requirement for visible facial and mouth features.
- Detail file: `analysis_results/details/whisper_clap_V_TN_Sp_Si_So_abs_ord_SoSpSi_v2.txt`

#### FP — Si_So_rel_ord_SoSi v2

- Human: `no` / Gemini: `yes`
- Temporal type: `relative_order`
- Modality: `Action (silent) + Action (sounding)`
- Gemini reason: The specific required visual actions are present: the right hand is seen striking the right thigh, and subsequently, the right hand forms and holds a clear thumbs-up pose.
- Gemini evidence: The right hand makes contact with the right thigh at 0.37 seconds. Later, the right hand is raised to form a closed fist with the thumb extended upward starting around 1.83 seconds.
- Detail file: `analysis_results/details/whisper_clap_V_FP_Si_So_rel_ord_SoSi_v2.txt`

#### FP — Sp_Si_So_abs_ord_SiSoSp v1

- Human: `no` / Gemini: `yes`
- Temporal type: `absolute_order`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: The required visual events, including the thumbs-up pose, the slapping of the thigh with the right hand, and the visible speaking motion, are all present and clearly visible.
- Gemini evidence: The person forms a thumbs-up with their right hand around 2.5 seconds, visibly speaks during this time, and later strikes their right thigh with their right hand around 3.8 seconds.
- Detail file: `analysis_results/details/whisper_clap_V_FP_Sp_Si_So_abs_ord_SiSoSp_v1.txt`

#### FP — Sp_Si_So_abs_ord_SoSiSp v1

- Human: `no` / Gemini: `yes`
- Temporal type: `absolute_order`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: The visual actions of striking the right thigh, forming a thumbs-up pose, and visible mouth movement during speech are all present and correctly performed.
- Gemini evidence: The right hand is seen striking the right thigh around 2.0 seconds. The person's mouth moves visibly to say 'help' around 3.0 seconds, and the right hand is raised into a clear thumbs-up pose starting at 3.1 seconds and fully formed by 3.4 seconds.
- Detail file: `analysis_results/details/whisper_clap_V_FP_Sp_Si_So_abs_ord_SoSiSp_v1.txt`

#### FN — Si_So_rel_sync v1

- Human: `yes` / Gemini: `no`
- Temporal type: `relative_synchronization`
- Modality: `Action (silent) + Action (sounding)`
- Gemini reason: The visible actions do not meet the prompt's specific requirements. The person raises their hand and forms a thumbs-up in the air, then opens their hand to a flat palm before slapping the thigh. The prompt strictly required the thumbs-up pose to be held while striking the thigh, and prohibited a separate lifting motion.
- Gemini evidence: In the video, between 00:00.250 and 00:00.500 (and repeatedly thereafter), the right hand is lifted and forms a thumbs-up in the air. When the hand descends to strike the thigh at 00:00.542, it is open, not in a thumbs-up pose.
- Detail file: `analysis_results/details/whisper_clap_V_FN_Si_So_rel_sync_v1.txt`

#### FN — Sp_So_abs_sync v2

- Human: `yes` / Gemini: `no`
- Temporal type: `absolute_synchronization`
- Modality: `Speech + Action (sounding)`
- Gemini reason: The subject does not exhibit any visible speaking or mouth motion to produce the word 'help'. Furthermore, the right hand performs a flicking or snapping motion in the air rather than visibly striking the thigh.
- Gemini evidence: Visual inspection shows the mouth remaining closed at the start of the video when the speech is heard. From 2.7 to 3.1 seconds, the right hand lifts and moves downwards but does not make visible contact with the top of the thigh.
- Detail file: `analysis_results/details/whisper_clap_V_FN_Sp_So_abs_sync_v2.txt`

#### FN — Si_So_rel_sync v3

- Human: `yes` / Gemini: `no`
- Temporal type: `relative_synchronization`
- Modality: `Action (silent) + Action (sounding)`
- Gemini reason: The visual action is incorrect. The right hand strikes the left thigh or center lap instead of the right thigh. Furthermore, the hand is not in a thumbs-up pose during the strike; the thumbs-up is formed as a separate, subsequent motion.
- Gemini evidence: In the video, the right hand moves left and strikes the left thigh/lap area around 1.4 seconds. The hand then lifts and forms a thumbs-up pose starting around 1.5 seconds, rather than holding the pose during the strike.
- Detail file: `analysis_results/details/whisper_clap_V_FN_Si_So_rel_sync_v3.txt`

### AVB

#### TP — Sp_Si_So_abs_ord_SiSpSo v2

- Human: `yes` / Gemini: `yes`
- Temporal type: `absolute_order`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: The audio events are temporally synchronized with visible candidate actions, despite the visual actions using the incorrect hand/side.
- Gemini evidence: The speech audio 'help' perfectly aligns with the visible speaking and mouth movements of the person around 2.4-2.8 seconds. The slap sound at approximately 4.6 seconds occurs exactly when the person's left hand makes visible contact with their left thigh.
- Detail file: `analysis_results/details/whisper_clap_AVB_TP_Sp_Si_So_abs_ord_SiSpSo_v2.txt`

#### TP — Sp_Si_So_abs_ord_SpSiSo v1

- Human: `yes` / Gemini: `yes`
- Temporal type: `absolute_order`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: The speech audio is temporally aligned with the visible mouth movement, and the slap sound is synchronized with the hand striking the chest.
- Gemini evidence: Visible mouth motion occurs around 1.3 to 1.9 seconds, aligning with the Whisper transcript timestamps for 'help'. The slap sound at approximately 4.7 seconds aligns perfectly with the visual impact of the right hand on the left chest/shoulder.
- Detail file: `analysis_results/details/whisper_clap_AVB_TP_Sp_Si_So_abs_ord_SpSiSo_v1.txt`

#### TP — Sp_So_abs_sync_cnt v1

- Human: `yes` / Gemini: `yes`
- Temporal type: `absolute_sync_count`
- Modality: `Speech + Action (sounding)`
- Gemini reason: The spoken words 'help' perfectly align with the visible mouth movements, and the slap sounds perfectly align with the visible impacts of the hand on the thigh.
- Gemini evidence: Video and audio observation confirms the first slap impact and mouth opening at 2.0s matches the first slap sound and spoken word. The second occurrence at 4.0s is similarly perfectly synchronized.
- Detail file: `analysis_results/details/whisper_clap_AVB_TP_Sp_So_abs_sync_cnt_v1.txt`

#### TN — Sp_Si_So_abs_sync_cnt v1

- Human: `no` / Gemini: `no`
- Temporal type: `absolute_sync_count`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: Because the thigh slap action and its corresponding sound are entirely missing, the required audio-visual binding for the sounding action cannot occur. Additionally, the second synchronized bundle is missing entirely.
- Gemini evidence: The slap sound is absent from the audio and the slap motion is absent from the video. The only synchronized event is the initial speech and mouth movement, but the complete requested bundles are not bound.
- Detail file: `analysis_results/details/whisper_clap_AVB_TN_Sp_Si_So_abs_sync_cnt_v1.txt`

#### TN — Sp_So_rel_sync v1

- Human: `no` / Gemini: `no`
- Temporal type: `relative_synchronization`
- Modality: `Speech + Action (sounding)`
- Gemini reason: While the slap sound is perfectly synchronized with the visible impact of the hand on the thigh, the audio-visual binding for the speech event fails because the mouth is not visible.
- Gemini evidence: The slap impact and sound align at 1.3 seconds. However, the spoken word 'help' at 0.00-0.28 seconds has no corresponding visible lip motion due to the missing head.
- Detail file: `analysis_results/details/whisper_clap_AVB_TN_Sp_So_rel_sync_v1.txt`

#### TN — Sp_Si_So_abs_sync v2

- Human: `no` / Gemini: `no`
- Temporal type: `absolute_synchronization`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: While the spoken word 'help' is correctly aligned with visible mouth movements, the required binding for the thigh slap is impossible since both the slapping action and the corresponding sound are missing.
- Gemini evidence: Mouth movement matches the audio from 0.00 to 0.40 seconds. Neither a slapping visual motion nor a slap sound occurs, failing the binding requirement for that event.
- Detail file: `analysis_results/details/whisper_clap_AVB_TN_Sp_Si_So_abs_sync_v2.txt`

#### FP — Sp_Si_So_rel_sync v1

- Human: `no` / Gemini: `yes`
- Temporal type: `relative_synchronization`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: The visible speaking motions correspond temporally to the spoken word, and the visible hand impact corresponds directly to the slap sound.
- Gemini evidence: The person's mouth moves as 'help' is heard (0.00-0.26s), and the audible slap sound aligns perfectly with the visual impact of the hand on the thigh at 0.50 seconds.
- Detail file: `analysis_results/details/whisper_clap_AVB_FP_Sp_Si_So_rel_sync_v1.txt`

#### FP — Sp_So_rel_sync_cnt v2

- Human: `no` / Gemini: `yes`
- Temporal type: `relative_sync_count`
- Modality: `Speech + Action (sounding)`
- Gemini reason: The speech audio is temporally aligned with the visible lip motion, and the slap sound corresponds precisely with the visible hand impact on the thigh.
- Gemini evidence: The word 'help' and the visible speaking motion coincide at the start of the video. The slap sound matches the visual impact of the right hand on the right thigh at roughly 0.29 seconds.
- Detail file: `analysis_results/details/whisper_clap_AVB_FP_Sp_So_rel_sync_cnt_v2.txt`

#### FP — Sp_So_rel_sync v2

- Human: `no` / Gemini: `yes`
- Temporal type: `relative_synchronization`
- Modality: `Speech + Action (sounding)`
- Gemini reason: The speech audio is synchronized with the visible mouth movements, and the slap sound is temporally aligned with the slight hand movement.
- Gemini evidence: The word 'help' aligns with the mouth movement at 0.0s-0.3s, and the slap sound aligns with the right hand's slight motion at 2.9s.
- Detail file: `analysis_results/details/whisper_clap_AVB_FP_Sp_So_rel_sync_v2.txt`

#### FN — Sp_Si_So_abs_ord_SiSpSo v1

- Human: `yes` / Gemini: `no`
- Temporal type: `absolute_order`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: While the speech audio 'help' is correctly synchronized with visible mouth movements, the required binding for the thigh slap cannot be satisfied because both the audio and visual components of the event are missing.
- Gemini evidence: The mouth opens and closes in sync with the spoken word 'help' between 2.4s and 3.0s. Because the slap sound and the visible striking motion are completely absent at 4.0s, the required audio-visual binding for the sounding action is not fulfilled.
- Detail file: `analysis_results/details/whisper_clap_AVB_FN_Sp_Si_So_abs_ord_SiSpSo_v1.txt`

#### FN — Sp_Si_So_abs_ord_SoSpSi v2

- Human: `yes` / Gemini: `no`
- Temporal type: `absolute_order`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: While the slap sound aligns with the visual action of the hand striking the thigh, the speech audio cannot be bound to any visible lip or mouth motion because the face is cropped out of the frame.
- Gemini evidence: The slap action and sound synchronize perfectly around 2.2 seconds, but the word 'help' heard between 2.16 and 2.70 seconds has no corresponding visible speaking motion due to the missing face.
- Detail file: `analysis_results/details/whisper_clap_AVB_FN_Sp_Si_So_abs_ord_SoSpSi_v2.txt`

#### FN — Sp_So_rel_ord_SpSo v3

- Human: `yes` / Gemini: `no`
- Temporal type: `relative_order`
- Modality: `Speech + Action (sounding)`
- Gemini reason: The speech audio is not correctly bound to the visible subject, as the required lip motion is entirely absent during the spoken word. The hand slap is correctly synchronized with the impact sound, but all events must be bound.
- Gemini evidence: Whisper detects speech at 0.00s - 0.22s, but there is no corresponding visual articulation in the video at that time or at any other point. The visual slap at 3.000s aligns with the expected CLAP sound window.
- Detail file: `analysis_results/details/whisper_clap_AVB_FN_Sp_So_rel_ord_SpSo_v3.txt`

### TC

#### TP — Si_So_rel_sync_cnt v3

- Human: `yes` / Gemini: `yes`
- Temporal type: `relative_sync_count`
- Modality: `Action (silent) + Action (sounding)`
- Gemini reason: The synchronized bundle of the right hand holding a thumbs-up while striking the thigh and producing a slap sound occurs exactly twice with a clear reset in between.
- Gemini evidence: The first synchronized occurrence happens around 00:01.4, followed by the hand raising back to a ready position, and the second occurrence happens exactly once more around 00:04.3.
- Detail file: `analysis_results/details/whisper_clap_TC_TP_Si_So_rel_sync_cnt_v3.txt`

#### TP — Sp_Si_So_rel_ord_SoSiSp v3

- Human: `yes` / Gemini: `yes`
- Temporal type: `relative_order`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: The specified relative order of the target events (thigh slap, then thumbs-up, then speech) is strictly followed.
- Gemini evidence: The thigh slap occurs first at 0.333s, the thumbs-up is formed and held starting around 2.250s, and the speech event 'help' occurs last at 3.15s.
- Detail file: `analysis_results/details/whisper_clap_TC_TP_Sp_Si_So_rel_ord_SoSiSp_v3.txt`

#### TP — Sp_Si_So_rel_ord_SpSiSo v3

- Human: `yes` / Gemini: `yes`
- Temporal type: `relative_order`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: The events occur in the exact required relative order: first the speech, then the silent action (thumbs-up), and finally the sounding action (slap).
- Gemini evidence: The speech 'help' occurs first (0.00-0.22s), followed by the right hand forming a thumbs-up (held from ~1.9s to 2.5s), and ending with the right hand slapping the right thigh at 3.00 seconds.
- Detail file: `analysis_results/details/whisper_clap_TC_TP_Sp_Si_So_rel_ord_SpSiSo_v3.txt`

#### TN — Sp_Si_So_rel_sync_cnt v1

- Human: `no` / Gemini: `no`
- Temporal type: `relative_sync_count`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: The required synchronized bundle of speech, thumbs-up, and slap fails because the actions are performed sequentially rather than simultaneously. Additionally, the bundle does not happen exactly twice: speech occurs only once, while the slap occurs three times.
- Gemini evidence: Speech 'help' occurs only once at 0.00s. The thumbs-up pose follows the slap sequentially at 0.54s and 1.37s rather than occurring during the contact. A third slap occurs at 2.00s without any speech or subsequent thumbs-up.
- Detail file: `analysis_results/details/whisper_clap_TC_TN_Sp_Si_So_rel_sync_cnt_v1.txt`

#### TN — Si_So_abs_ord_SoSi v2

- Human: `no` / Gemini: `no`
- Temporal type: `absolute_order`
- Modality: `Action (silent) + Action (sounding)`
- Gemini reason: The temporal constraints are violated because the sounding action is not synchronized, and neither the sound nor the visual action occurs at the requested 1.5-second mark.
- Gemini evidence: The prompt requires the thigh slap with simultaneous sound at 1.5 seconds. Instead, the sound occurs at 2.0 seconds and the visual action occurs around 2.9 seconds. The thumbs-up occurs relatively accurately around 3.5 to 4.1 seconds, but the first event's timing failure and desynchronization fail the absolute schedule.
- Detail file: `analysis_results/details/whisper_clap_TC_TN_Si_So_abs_ord_SoSi_v2.txt`

#### TN — Sp_So_abs_sync v2

- Human: `no` / Gemini: `no`
- Temporal type: `absolute_synchronization`
- Modality: `Speech + Action (sounding)`
- Gemini reason: The prompt requires the speech and the slapping action to be exactly synchronized at the 2.0-second mark. However, the speech occurs at the beginning of the video, and the hand action occurs much later, failing both absolute timing and synchronization.
- Gemini evidence: Whisper detects speech at 0.00-0.18 seconds, while the visible hand motion and the corresponding sound occur sequentially around 2.7-3.1 seconds. Neither event happens at 2.0 seconds, and they are temporally disconnected.
- Detail file: `analysis_results/details/whisper_clap_TC_TN_Sp_So_abs_sync_v2.txt`

#### FP — Sp_So_abs_ord_SoSp v2

- Human: `no` / Gemini: `yes`
- Temporal type: `absolute_order`
- Modality: `Speech + Action (sounding)`
- Gemini reason: The absolute ordering and approximate timing requirements are correctly satisfied. The slap occurs before the speech, they do not overlap, and the timings are close to the requested schedule.
- Gemini evidence: The thigh slap occurs first at approximately 1.4 seconds (near the 1.5s requirement), followed by the speech event 'help' which starts around 3.1 seconds (near the 3.5s requirement). There is no overlap, and no new target actions occur after the final event.
- Detail file: `analysis_results/details/whisper_clap_TC_FP_Sp_So_abs_ord_SoSp_v2.txt`

#### FP — Sp_So_abs_sync_cnt v1

- Human: `no` / Gemini: `yes`
- Temporal type: `absolute_sync_count`
- Modality: `Speech + Action (sounding)`
- Gemini reason: The synchronized speech and slapping bundle occurs exactly twice, with the required spacing. Although slightly delayed from the absolute prompt times, the structural and sync requirements are perfectly met.
- Gemini evidence: The prompt requires the events around 1.5s and 3.5s. They occur at exactly 2.0s and 4.0s, preserving the exact count of two, the tight synchronization, and the 2-second interval between the events.
- Detail file: `analysis_results/details/whisper_clap_TC_FP_Sp_So_abs_sync_cnt_v1.txt`

#### FP — Si_So_rel_sync_cnt v1

- Human: `no` / Gemini: `yes`
- Temporal type: `relative_sync_count`
- Modality: `Action (silent) + Action (sounding)`
- Gemini reason: The synchronized bundle of the thumbs-up and thigh slap occurs exactly twice, with a brief reset in between, and no extra occurrences afterwards.
- Gemini evidence: The synchronized events happen at 00:00.125 and 00:02.125, making exactly two occurrences. The hand returns to a resting position between the two actions, and the person remains still after the second event.
- Detail file: `analysis_results/details/whisper_clap_TC_FP_Si_So_rel_sync_cnt_v1.txt`

#### FN — Sp_Si_rel_sync v2

- Human: `yes` / Gemini: `no`
- Temporal type: `relative_synchronization`
- Modality: `Speech + Action (silent)`
- Gemini reason: The temporal constraint requires the person to form the thumbs-up pose simultaneously with saying 'help'. Because the pose is already held before the speech begins, this synchronization is not met.
- Gemini evidence: The thumbs-up is already fully formed at 00:00.000 and is not dynamically formed simultaneously with the speech onset.
- Detail file: `analysis_results/details/whisper_clap_TC_FN_Sp_Si_rel_sync_v2.txt`

#### FN — Si_So_rel_ord_SoSi v3

- Human: `yes` / Gemini: `no`
- Temporal type: `relative_order`
- Modality: `Action (silent) + Action (sounding)`
- Gemini reason: The requested relative order sequence is not satisfied because the specified second event (right-hand thumbs-up) never occurs.
- Gemini evidence: The first action (slapping the thigh) occurs correctly, but because the right-hand thumbs-up is entirely absent (substituted by a left-hand thumbs-up), the specified event sequence cannot be completed.
- Detail file: `analysis_results/details/whisper_clap_TC_FN_Si_So_rel_ord_SoSi_v3.txt`

#### FN — Si_So_rel_ord_SoSi v1

- Human: `yes` / Gemini: `no`
- Temporal type: `relative_order`
- Modality: `Action (silent) + Action (sounding)`
- Gemini reason: The specified sequence cannot be fully satisfied because one of the required events (the right-hand thumbs-up) is absent.
- Gemini evidence: The slap action occurs first as requested, but the subsequent right-hand thumbs-up is missing (substituted by the left hand), leaving the ordered sequence incomplete.
- Detail file: `analysis_results/details/whisper_clap_TC_FN_Si_So_rel_ord_SoSi_v1.txt`

### CC

#### TP — Sp_So_abs_ord_SpSo v3

- Human: `yes` / Gemini: `yes`
- Temporal type: `absolute_order`
- Modality: `Speech + Action (sounding)`
- Gemini reason: The video adheres to all non-core constraints, including the setting, camera shot, visibility requirements, lack of extra sounds or actions, and post-event stillness.
- Gemini evidence: The video features a static medium shot in a plain indoor room. The person starts with hands on their thighs and all required body parts remain visible. There are no extra words spoken or extra actions performed, and the person remains still after the final action.
- Detail file: `analysis_results/details/whisper_clap_CC_TP_Sp_So_abs_ord_SpSo_v3.txt`

#### TP — Sp_So_rel_ord_SoSp v2

- Human: `yes` / Gemini: `yes`
- Temporal type: `relative_order`
- Modality: `Speech + Action (sounding)`
- Gemini reason: The video adheres to all non-core constraints including setting, camera framing, initial pose, and post-event stillness.
- Gemini evidence: The video features a static medium shot in a plain indoor room. The person begins with hands on thighs, performs no extra words or actions, and returns to a resting state after the speech is completed, fulfilling the constraint that no new target action occurs.
- Detail file: `analysis_results/details/whisper_clap_CC_TP_Sp_So_rel_ord_SoSp_v2.txt`

#### TP — Sp_Si_So_abs_ord_SiSpSo v2

- Human: `yes` / Gemini: `yes`
- Temporal type: `absolute_order`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: The video satisfies the scene, framing, and negative constraints. There are no extra words, extra actions, background music, or scene violations.
- Gemini evidence: The video features a single seated person in a plain indoor room using a static medium shot. The actor only says 'help', no subtitles are present, and the person rests after the final slap action.
- Detail file: `analysis_results/details/whisper_clap_CC_TP_Sp_Si_So_abs_ord_SiSpSo_v2.txt`

#### TN — Sp_Si_So_rel_sync v1

- Human: `no` / Gemini: `no`
- Temporal type: `relative_synchronization`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: The video violates several prompt constraints, including the framing of the face, the starting position of the hands, and maintaining the specific hand shape.
- Gemini evidence: The prompt requires the 'full face' to be clearly visible, but the top half is cropped out. It also requires the person to start with 'both hands resting on the knees or thighs,' but the right hand starts raised. Finally, the thumbs-up pose is not maintained during the strike.
- Detail file: `analysis_results/details/whisper_clap_CC_TN_Sp_Si_So_rel_sync_v1.txt`

#### TN — Sp_Si_rel_sync_cnt v1

- Human: `no` / Gemini: `no`
- Temporal type: `relative_sync_count`
- Modality: `Speech + Action (silent)`
- Gemini reason: The video includes visible text on the person's shirt, and there are additional distracting hand movements later in the clip that violate the expected sequence and post-event stillness.
- Gemini evidence: The person's shirt has prominent reversed text ('RCMEY ELIROKN'), and the person makes a noticeable, unrelated hand movement around 2.4 seconds instead of completing a proper second repetition or remaining still.
- Detail file: `analysis_results/details/whisper_clap_CC_TN_Sp_Si_rel_sync_cnt_v1.txt`

#### TN — Sp_Si_So_rel_sync_cnt v2

- Human: `no` / Gemini: `no`
- Temporal type: `relative_sync_count`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: The video violates constraints regarding full face visibility, the strict count of target actions, and post-event stillness.
- Gemini evidence: The top of the person's head is cropped out, violating the 'full face' requirement. Furthermore, a third thigh slap occurs after the second one, violating the constraint that the action should happen exactly twice and that no new target action occurs after the final event.
- Detail file: `analysis_results/details/whisper_clap_CC_TN_Sp_Si_So_rel_sync_cnt_v2.txt`

#### FP — Sp_So_rel_ord_SpSo v3

- Human: `no` / Gemini: `yes`
- Temporal type: `relative_order`
- Modality: `Speech + Action (sounding)`
- Gemini reason: The video complies with the non-core constraints: the setting is a plain indoor room, the camera is a static medium shot, the person starts seated with hands on their thighs, and no extra actions occur after the final event.
- Gemini evidence: The environment and framing match the prompt, the starting pose is correct, and after the hand returns to the thigh at 3.042s, the subject remains still until the end of the video.
- Detail file: `analysis_results/details/whisper_clap_CC_FP_Sp_So_rel_ord_SpSo_v3.txt`

#### FP — Sp_Si_abs_sync_cnt v2

- Human: `no` / Gemini: `yes`
- Temporal type: `absolute_sync_count`
- Modality: `Speech + Action (silent)`
- Gemini reason: The video adheres to the scene, camera, setting, and action constraints. The person remains still after the final action, and no extra words are spoken.
- Gemini evidence: The video features a single person in a plain indoor room facing the camera in a static medium shot. Hands start resting on the thighs, no extra words are spoken, and no new actions occur after the final thumbs-up.
- Detail file: `analysis_results/details/whisper_clap_CC_FP_Sp_Si_abs_sync_cnt_v2.txt`

#### FP — Sp_So_abs_sync v1

- Human: `no` / Gemini: `yes`
- Temporal type: `absolute_synchronization`
- Modality: `Speech + Action (sounding)`
- Gemini reason: The video adheres to all non-core constraints, including the setting, framing, initial pose, and post-event stillness.
- Gemini evidence: The video features a single seated person in a plain indoor room, captured in a static medium shot. Both hands rest on the thighs at the beginning, and no extra actions occur after the final slap.
- Detail file: `analysis_results/details/whisper_clap_CC_FP_Sp_So_abs_sync_v1.txt`

#### FN — Sp_So_abs_sync_cnt v3

- Human: `yes` / Gemini: `no`
- Temporal type: `absolute_sync_count`
- Modality: `Speech + Action (sounding)`
- Gemini reason: The video violates the constraint that no extra words should be spoken and no new target actions should occur after the final scheduled event, as the person performs the speech and slap three times instead of two.
- Gemini evidence: The prompt strictly specifies exactly two occurrences and no extra words. The video features a third repetition of the speech and slap event around 4.3 seconds.
- Detail file: `analysis_results/details/whisper_clap_CC_FN_Sp_So_abs_sync_cnt_v3.txt`

#### FN — Sp_Si_So_rel_ord_SpSiSo v1

- Human: `yes` / Gemini: `no`
- Temporal type: `relative_order`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: The video violates the post-event stillness constraint because a new action (left hand thumbs-up) occurs after the final scheduled event. It also includes an unprompted action (right hand raising/waving).
- Gemini evidence: The prompt specifies 'After the final event, no new target action occurs', but the left hand forms a thumbs-up at 4.7s, after the thigh slap. The right hand's open-hand raise before the slap is also an extra, unprompted gesture.
- Detail file: `analysis_results/details/whisper_clap_CC_FN_Sp_Si_So_rel_ord_SpSiSo_v1.txt`

#### FN — Sp_Si_abs_ord_SiSp v1

- Human: `yes` / Gemini: `no`
- Temporal type: `absolute_order`
- Modality: `Speech + Action (silent)`
- Gemini reason: The prompt's constraint that the thumbs-up pose be kept separate from the speaking moment is violated, as the two events overlap. Furthermore, the wrong hand is used.
- Gemini evidence: The left-hand thumbs-up motion begins at 3.1 seconds and overlapping speech begins at 3.2 seconds, failing the separation constraint.
- Detail file: `analysis_results/details/whisper_clap_CC_FN_Sp_Si_abs_ord_SiSp_v1.txt`

## all_tools

### A

#### TP — Sp_Si_So_abs_ord_SoSiSp v2

- Human: `yes` / Gemini: `yes`
- Temporal type: `absolute_order`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: The required audio events are present. There is a sharp slap sound, and the person clearly says the word 'help'.
- Gemini evidence: A slap sound is heard around 1.0 seconds, supported by CLAP cosine similarity peaking for 'slapping_the_thigh' (0.304) in the 0.75-1.50s window. The word 'help' is heard clearly, supported by Whisper ASR transcribing 'Help' at 2.38-2.94s.
- Detail file: `analysis_results/details/all_tools_A_TP_Sp_Si_So_abs_ord_SoSiSp_v2.txt`

#### TP — Sp_Si_So_rel_ord_SoSpSi v2

- Human: `yes` / Gemini: `yes`
- Temporal type: `relative_order`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: Both the speech event ('help') and the sound event (a sharp slap) are clearly present and audible in the audio track.
- Gemini evidence: Whisper ASR detects the word 'Help' between 0.00s and 0.18s. A distinct slap sound is audible around 0.95s, which aligns with CLAP's positive sliding window scores for 'slapping_the_thigh'.
- Detail file: `analysis_results/details/all_tools_A_TP_Sp_Si_So_rel_ord_SoSpSi_v2.txt`

#### TP — Sp_So_abs_ord_SpSo v3

- Human: `yes` / Gemini: `yes`
- Temporal type: `absolute_order`
- Modality: `Speech + Action (sounding)`
- Gemini reason: The audio clearly contains the spoken word 'help' and a sharp thigh-slapping sound.
- Gemini evidence: Whisper detects the word 'help' from 0.00 to 0.72 seconds. A sharp slap sound is clearly audible around 3.6 seconds, which is consistent with the CLAP peak for 'slapping_the_thigh' in the 3.25 to 4.00 second window.
- Detail file: `analysis_results/details/all_tools_A_TP_Sp_So_abs_ord_SpSo_v3.txt`

#### TN — Sp_Si_So_abs_sync v2

- Human: `no` / Gemini: `no`
- Temporal type: `absolute_synchronization`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: The word 'help' is spoken clearly at the beginning of the video, but the required sharp slap sound is entirely missing.
- Gemini evidence: Whisper detects 'Help.' from 0.00 to 0.36 seconds, which aligns with the audio track. No slap sound is audible at any point.
- Detail file: `analysis_results/details/all_tools_A_TN_Sp_Si_So_abs_sync_v2.txt`

#### TN — Sp_Si_So_abs_sync v3

- Human: `no` / Gemini: `no`
- Temporal type: `absolute_synchronization`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: The required speech 'help' is present, but the specified sharp slap sound is missing entirely.
- Gemini evidence: Whisper detects the word 'help' from 1.42s to 1.94s, and it is clearly audible, but direct audio inspection confirms no slap sound occurs at any point.
- Detail file: `analysis_results/details/all_tools_A_TN_Sp_Si_So_abs_sync_v3.txt`

#### TN — Sp_Si_So_abs_sync_cnt v1

- Human: `no` / Gemini: `no`
- Temporal type: `absolute_sync_count`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: The word 'help' is spoken, but the required sharp slap sound is entirely missing from the audio track.
- Gemini evidence: Whisper detects 'Help' from 0.00s to 0.36s. CLAP shows no strong confidence for 'slapping_the_thigh', and no slap sound can be heard in the audio.
- Detail file: `analysis_results/details/all_tools_A_TN_Sp_Si_So_abs_sync_cnt_v1.txt`

#### FP — Sp_Si_So_rel_ord_SpSiSo v2

- Human: `no` / Gemini: `yes`
- Temporal type: `relative_order`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: The audio contains the spoken word 'help' at the beginning, followed later by a sharp slap sound.
- Gemini evidence: Whisper correctly transcribes 'help' between 0.00 and 0.30 seconds. A clear slap sound is audible at exactly 3.0 seconds.
- Detail file: `analysis_results/details/all_tools_A_FP_Sp_Si_So_rel_ord_SpSiSo_v2.txt`

#### FP — Sp_Si_rel_ord_SiSp v3

- Human: `no` / Gemini: `yes`
- Temporal type: `relative_order`
- Modality: `Speech + Action (silent)`
- Gemini reason: The word 'help' is clearly audible and distinguishable in the audio track.
- Gemini evidence: A voice says the word 'help' from approximately 0.6s to 1.1s.
- Detail file: `analysis_results/details/all_tools_A_FP_Sp_Si_rel_ord_SiSp_v3.txt`

#### FP — Sp_So_rel_sync v1

- Human: `no` / Gemini: `yes`
- Temporal type: `relative_synchronization`
- Modality: `Speech + Action (sounding)`
- Gemini reason: The spoken word 'help' is clearly audible, and a distinct sharp slap sound is heard.
- Gemini evidence: Whisper transcription detects 'Help' from 0.00 to 0.28 seconds. A clear slap sound is audible later in the audio track.
- Detail file: `analysis_results/details/all_tools_A_FP_Sp_So_rel_sync_v1.txt`

#### FN — Sp_Si_So_abs_ord_SiSpSo v1

- Human: `yes` / Gemini: `no`
- Temporal type: `absolute_order`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: The speech event 'help' is clearly audible, but the required sharp slap sound is entirely missing from the audio track.
- Gemini evidence: Whisper detects 'help' between 2.45 and 3.05 seconds, which is verified by listening. However, no slap sound is heard around the 4.0-second mark or anywhere else in the video, and CLAP scores for 'slapping_the_thigh' remain very low.
- Detail file: `analysis_results/details/all_tools_A_FN_Sp_Si_So_abs_ord_SiSpSo_v1.txt`

#### FN — Sp_Si_So_rel_sync_cnt v1

- Human: `yes` / Gemini: `no`
- Temporal type: `relative_sync_count`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: The word 'help' is only spoken once at the very beginning, and the required sharp slap sounds are completely absent.
- Gemini evidence: Whisper detects 'help' only once between 0.00s and 0.22s. No subsequent speech is heard. There is no audible 'sharp slap sound' throughout the video, which is also reflected by low and inconsistent CLAP scores for 'slapping_the_thigh'.
- Detail file: `analysis_results/details/all_tools_A_FN_Sp_Si_So_rel_sync_cnt_v1.txt`

#### FN — Sp_So_abs_sync_cnt v3

- Human: `yes` / Gemini: `no`
- Temporal type: `absolute_sync_count`
- Modality: `Speech + Action (sounding)`
- Gemini reason: The required speech and slap sound at 1.5 seconds are completely missing. Additionally, the word 'help' is spoken multiple times at the end of the video rather than just once at the second scheduled time.
- Gemini evidence: Whisper transcript and audio inspection confirm silence until around 3.0 seconds, after which 'help' is spoken repeatedly at 3.09-3.73s, 3.93-4.19s, and 4.45-4.79s.
- Detail file: `analysis_results/details/all_tools_A_FN_Sp_So_abs_sync_cnt_v3.txt`

### V

#### TP — Sp_Si_So_rel_ord_SoSiSp v3

- Human: `yes` / Gemini: `yes`
- Temporal type: `relative_order`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: The specified visual actions are present and executed correctly: the person strikes their right thigh with their right hand, forms and holds a thumbs-up pose, and visibly speaks the required word.
- Gemini evidence: The right hand is seen striking the right thigh at approximately 0.25s. At 2.25s, the person raises their right hand and holds a clear thumbs-up pose. Starting around 3.2s, their mouth visibly moves to articulate the word 'help'.
- Detail file: `analysis_results/details/all_tools_V_TP_Sp_Si_So_rel_ord_SoSiSp_v3.txt`

#### TP — Sp_So_abs_sync v1

- Human: `yes` / Gemini: `yes`
- Temporal type: `absolute_synchronization`
- Modality: `Speech + Action (sounding)`
- Gemini reason: The person exhibits visible speaking motion corresponding to the required word, and the required slapping action is correctly performed with the correct hand and target location.
- Gemini evidence: The person's mouth visibly articulates the word 'help' around 2.8 to 3.5 seconds. Following this, the right hand raises and strikes the right thigh, making clear visible contact at around 4.5 seconds, while the left hand remains resting.
- Detail file: `analysis_results/details/all_tools_V_TP_Sp_So_abs_sync_v1.txt`

#### TP — Sp_Si_So_rel_ord_SiSpSo v1

- Human: `yes` / Gemini: `yes`
- Temporal type: `relative_order`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: The visible actions are present and correctly performed, including the visible speaking motion, the right-handed thumbs-up, and the right hand slapping the right thigh.
- Gemini evidence: The person's mouth visibly moves at the very beginning of the video. Starting around 0.66 seconds, the right hand forms a thumbs-up pose and holds it. After 2.75 seconds, the hand drops and visibly strikes the right thigh at exactly 3.00 seconds.
- Detail file: `analysis_results/details/all_tools_V_TP_Sp_Si_So_rel_ord_SiSpSo_v1.txt`

#### TN — Si_So_rel_sync_cnt v1

- Human: `no` / Gemini: `no`
- Temporal type: `relative_sync_count`
- Modality: `Action (silent) + Action (sounding)`
- Gemini reason: The right hand does not hold the thumbs-up pose while striking the thigh. Instead, it strikes the thigh flat, and the thumbs-up is performed using an upward hand-raising motion, which explicitly contradicts the prompt's action definition.
- Gemini evidence: The right hand is open and flat during the thigh strikes at 00:00.000, 00:01.000, and 00:02.000. The thumbs-up pose is only visible when the hand is raised in the air around 00:00.292, 00:00.750, and 00:01.792, violating the instruction against a separate hand-raising motion.
- Detail file: `analysis_results/details/all_tools_V_TN_Si_So_rel_sync_cnt_v1.txt`

#### TN — Sp_Si_So_abs_ord_SoSpSi v2

- Human: `no` / Gemini: `no`
- Temporal type: `absolute_order`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: The face and mouth are entirely cropped out of the frame, making visible speaking motion impossible to verify. Furthermore, the slapping and thumbs-up actions are performed by the left hand instead of the requested right hand.
- Gemini evidence: Video frames show the subject's head is completely out of frame. The person's left hand (viewer's right) visibly slaps the left thigh at 2.0s and forms a thumbs-up from 3.3s to 5.0s, while the right hand (viewer's left) remains resting on the thigh throughout.
- Detail file: `analysis_results/details/all_tools_V_TN_Sp_Si_So_abs_ord_SoSpSi_v2.txt`

#### TN — Sp_Si_So_abs_ord_SiSoSp v3

- Human: `no` / Gemini: `no`
- Temporal type: `absolute_order`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: While the right hand correctly performs the thigh slap and the thumbs-up gesture, the required visible speaking behavior is completely missing because the person's full face and mouth are cropped out of the video frame.
- Gemini evidence: The right hand is seen striking the thigh at 2.5 seconds and then forming a thumbs-up at 2.7 seconds. However, the top of the frame cuts off the person's face above the chin, making it impossible to observe the mouth or lip movements when the speech occurs.
- Detail file: `analysis_results/details/all_tools_V_TN_Sp_Si_So_abs_ord_SiSoSp_v3.txt`

#### FP — Sp_Si_So_abs_ord_SoSpSi v1

- Human: `no` / Gemini: `yes`
- Temporal type: `absolute_order`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: The visible actions are correctly performed. The right hand strikes the right thigh, the mouth moves for speech, and the right hand forms a clear thumbs-up.
- Gemini evidence: In the video, the person's right hand raises and strikes the right thigh making contact at 1.1 seconds. Later, the mouth visibly moves to speak, and the right hand forms a thumbs-up starting around 3.4 seconds and holds it.
- Detail file: `analysis_results/details/all_tools_V_FP_Sp_Si_So_abs_ord_SoSpSi_v1.txt`

#### FP — Si_So_rel_ord_SoSi v1

- Human: `no` / Gemini: `yes`
- Temporal type: `relative_order`
- Modality: `Action (silent) + Action (sounding)`
- Gemini reason: The required visual actions are both present. The person's right hand visibly strikes the right thigh, and subsequently forms and holds a clear thumbs-up pose.
- Gemini evidence: The video shows the right hand making contact with the right thigh at 00:01.000, followed by the right hand forming a closed fist with the thumb extended upward at 00:01.875, which is then held until the end of the video.
- Detail file: `analysis_results/details/all_tools_V_FP_Si_So_rel_ord_SoSi_v1.txt`

#### FP — Sp_Si_So_abs_ord_SpSoSi v3

- Human: `no` / Gemini: `yes`
- Temporal type: `absolute_order`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: The person visibly speaks, strikes their right thigh with their right hand, and forms a clear thumbs-up pose with their right hand.
- Gemini evidence: Video clearly shows mouth movement at the beginning, the right hand slapping the right thigh around 2.0 seconds, and the right hand forming and holding a thumbs-up pose starting around 3.5 seconds to the end of the video.
- Detail file: `analysis_results/details/all_tools_V_FP_Sp_Si_So_abs_ord_SpSoSi_v3.txt`

#### FN — Si_So_abs_sync v1

- Human: `yes` / Gemini: `no`
- Temporal type: `absolute_synchronization`
- Modality: `Action (silent) + Action (sounding)`
- Gemini reason: The visible actions do not meet the prompt's specific requirements. The person raises their right hand to form a thumbs-up in the air, and then separately strikes the thigh with an open hand, violating the instruction that the thumbs-up remains recognizable during the contact and is not a separate hand-raising motion.
- Gemini evidence: At 2.5 seconds, the right hand forms a thumbs-up in the air. At 3.1 seconds, the right hand, now open rather than in a thumbs-up pose, strikes the right thigh.
- Detail file: `analysis_results/details/all_tools_V_FN_Si_So_abs_sync_v1.txt`

#### FN — Sp_Si_So_abs_ord_SoSpSi v3

- Human: `yes` / Gemini: `no`
- Temporal type: `absolute_order`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: The visual action for the thigh slap is incorrect. The person's right hand swings downward but completely misses the top of the right thigh, moving to the outside of the leg without making visible contact.
- Gemini evidence: Video inspection shows the right hand swinging down at 1.0s, but it passes down the side of the right leg rather than striking the top of the thigh. The visible speaking motion at 2.5s and the thumbs-up at 4.0s are visually correct.
- Detail file: `analysis_results/details/all_tools_V_FN_Sp_Si_So_abs_ord_SoSpSi_v3.txt`

#### FN — Sp_Si_So_abs_sync_cnt v3

- Human: `yes` / Gemini: `no`
- Temporal type: `absolute_sync_count`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: The person does not display visible speaking motion while performing the hand actions. Additionally, the thumbs-up pose is not held while striking the thigh; the gestures are performed sequentially rather than simultaneously as a single pose-strike.
- Gemini evidence: Video inspection shows the person's mouth only moves at the very beginning (0.0s-0.5s). The right hand forms a thumbs-up around 1.9s and 4.5s, but then opens or relaxes before striking the thigh around 2.1s and 4.7s.
- Detail file: `analysis_results/details/all_tools_V_FN_Sp_Si_So_abs_sync_cnt_v3.txt`

### AVB

#### TP — Sp_So_abs_ord_SpSo v3

- Human: `yes` / Gemini: `yes`
- Temporal type: `absolute_order`
- Modality: `Speech + Action (sounding)`
- Gemini reason: The visible mouth movements are perfectly synchronized with the spoken word 'help', and the audible slap sound aligns exactly with the visible hand-to-thigh impact.
- Gemini evidence: The audible speech and visible lip sync occur simultaneously in the first 0.7 seconds. The hand impact and the sharp slap sound both occur synchronously at roughly 3.6 seconds.
- Detail file: `analysis_results/details/all_tools_AVB_TP_Sp_So_abs_ord_SpSo_v3.txt`

#### TP — Sp_Si_So_rel_ord_SoSiSp v1

- Human: `yes` / Gemini: `yes`
- Temporal type: `relative_order`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: The audible slap perfectly aligns with the visible hand-to-thigh impact, and the spoken word 'help' perfectly synchronizes with the mouth movements.
- Gemini evidence: The visible impact at 00:00.917 aligns with the audible slap sound. Whisper's speech timestamp for 'help' (2.86s-3.50s) aligns with the visible mouth movements from 00:02.917 to 00:03.500.
- Detail file: `analysis_results/details/all_tools_AVB_TP_Sp_Si_So_rel_ord_SoSiSp_v1.txt`

#### TP — Sp_Si_So_rel_ord_SoSpSi v2

- Human: `yes` / Gemini: `yes`
- Temporal type: `relative_order`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: Both the speech audio and the slap sound are properly synchronized with their corresponding visual actions.
- Gemini evidence: The audible word 'help' aligns precisely with the person's mouth movement at the start of the video (0.00s - 0.18s). The audible slap sound occurs at exactly the moment the right hand makes contact with the right thigh (~0.95s).
- Detail file: `analysis_results/details/all_tools_AVB_TP_Sp_Si_So_rel_ord_SoSpSi_v2.txt`

#### TN — Sp_Si_So_abs_sync_cnt v1

- Human: `no` / Gemini: `no`
- Temporal type: `absolute_sync_count`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: While the spoken word 'help' aligns with the visible mouth movement at the start of the video, the audio-visual binding for the slapping action cannot be fulfilled because both the slapping motion and the slap sound are missing.
- Gemini evidence: Video and audio observation show synchronized speech at the very beginning (0.00s-0.40s), but the absence of the slap action and sound results in a failure to bind the second required audio-visual event.
- Detail file: `analysis_results/details/all_tools_AVB_TN_Sp_Si_So_abs_sync_cnt_v1.txt`

#### TN — Sp_Si_So_abs_ord_SiSoSp v3

- Human: `no` / Gemini: `no`
- Temporal type: `absolute_order`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: The audible slap is correctly synchronized with the visible strike, but the spoken word cannot be bound to any visual speaking motion because the person's mouth is not visible.
- Gemini evidence: The slap impact and sound align at 2.5 seconds. When 'help' is spoken at 3.0 seconds, there is no visible mouth to confirm synchronized lip movement.
- Detail file: `analysis_results/details/all_tools_AVB_TN_Sp_Si_So_abs_ord_SiSoSp_v3.txt`

#### TN — Sp_Si_So_rel_sync v1

- Human: `no` / Gemini: `no`
- Temporal type: `relative_synchronization`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: The speech is properly aligned with the visible mouth movement, but the visible action of slapping the thigh has no corresponding sound.
- Gemini evidence: The person's mouth moves as 'help' is heard from 0.00s to 0.26s. However, the right hand visibly strikes the thigh at 0.50s, and the audio is completely silent at this moment of impact.
- Detail file: `analysis_results/details/all_tools_AVB_TN_Sp_Si_So_rel_sync_v1.txt`

#### FP — Sp_Si_So_rel_ord_SpSiSo v2

- Human: `no` / Gemini: `yes`
- Temporal type: `relative_order`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: The spoken word aligns temporally with the visible lip motion, and the slap sound perfectly synchronizes with the hand striking the thigh.
- Gemini evidence: Speech audio and visible lip movement are synchronized at 0.0-0.3 seconds. The sharp slap sound at 3.0 seconds matches the exact moment of physical contact between the right hand and thigh.
- Detail file: `analysis_results/details/all_tools_AVB_FP_Sp_Si_So_rel_ord_SpSiSo_v2.txt`

#### FP — Sp_So_rel_sync v2

- Human: `no` / Gemini: `yes`
- Temporal type: `relative_synchronization`
- Modality: `Speech + Action (sounding)`
- Gemini reason: The speech audio is temporally aligned with the initial visible mouth movement, and the slap sound aligns with the physical motion of the leg lifting and interacting with the hand.
- Gemini evidence: Visible mouth movement aligns with the speech audio at 0.00-0.28s. The slap sound at 1.00s corresponds with the peak of the leg lift.
- Detail file: `analysis_results/details/all_tools_AVB_FP_Sp_So_rel_sync_v2.txt`

#### FP — Sp_So_rel_sync v1

- Human: `no` / Gemini: `yes`
- Temporal type: `relative_synchronization`
- Modality: `Speech + Action (sounding)`
- Gemini reason: Both events are individually well-synchronized between their audio and visual components.
- Gemini evidence: The spoken word 'help' aligns with the mouth movement from 0.0 to 0.3 seconds. The slap sound occurs exactly at the moment of visible impact of the right hand on the right thigh at approximately 1.4 seconds.
- Detail file: `analysis_results/details/all_tools_AVB_FP_Sp_So_rel_sync_v1.txt`

#### FN — Sp_Si_So_abs_ord_SiSpSo v1

- Human: `yes` / Gemini: `no`
- Temporal type: `absolute_order`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: While the audible speech is correctly aligned with the visible mouth movement, the binding for the slapping action fails because both the explicit visual strike and its corresponding impact sound are missing.
- Gemini evidence: The word 'help' heard at 2.5 seconds aligns perfectly with the visible mouth movements. However, the expected sounding action at 4.0 seconds lacks both a distinct visual strike and any slap audio.
- Detail file: `analysis_results/details/all_tools_AVB_FN_Sp_Si_So_abs_ord_SiSpSo_v1.txt`

#### FN — Sp_Si_So_abs_ord_SoSpSi v2

- Human: `yes` / Gemini: `no`
- Temporal type: `absolute_order`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: While the slap sound aligns temporally with the visual slap of the left hand, the spoken word 'help' cannot be bound to any visible speaking motion because the person's mouth is not visible.
- Gemini evidence: Speech audio is heard from 2.16 to 2.70 seconds, but the required face and mouth visibility is absent, preventing any verification of synchronized lip movement.
- Detail file: `analysis_results/details/all_tools_AVB_FN_Sp_Si_So_abs_ord_SoSpSi_v2.txt`

#### FN — Sp_Si_So_rel_sync_cnt v1

- Human: `yes` / Gemini: `no`
- Temporal type: `relative_sync_count`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: The required slap sounds are missing, precluding any binding with a visible slap impact. Additionally, the single spoken word 'help' ends before the first thumbs-up gesture is formed.
- Gemini evidence: Speech 'help' occurs from 0.00s to 0.22s, while the right hand does not fully form the thumbs-up gesture until around 0.50s. No slap sounds are present to align with any thigh contact.
- Detail file: `analysis_results/details/all_tools_AVB_FN_Sp_Si_So_rel_sync_cnt_v1.txt`

### TC

#### TP — Sp_Si_So_rel_ord_SoSiSp v3

- Human: `yes` / Gemini: `yes`
- Temporal type: `relative_order`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: The strict relative sequence of events is perfectly satisfied.
- Gemini evidence: The required sequence occurs exactly in order: the sounding action of slapping the thigh happens first (~0.25s), followed by the silent action of forming a thumbs-up (~2.25s), and finally the speech event 'help' (~3.15s - 3.75s). There is no overlap, and the order is strictly maintained.
- Detail file: `analysis_results/details/all_tools_TC_TP_Sp_Si_So_rel_ord_SoSiSp_v3.txt`

#### TP — Sp_Si_So_rel_ord_SoSiSp v2

- Human: `yes` / Gemini: `yes`
- Temporal type: `relative_order`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: The actions follow the exact required relative order: slapping the thigh, then giving a thumbs-up, and finally speaking.
- Gemini evidence: The sequence is strictly observed: the slap impact occurs at 0.167s, the thumbs-up is held starting around 1.50s, and the speech occurs afterward between 2.26s and 2.80s. There are no repetitions or out-of-order events.
- Detail file: `analysis_results/details/all_tools_TC_TP_Sp_Si_So_rel_ord_SoSiSp_v2.txt`

#### TP — Si_So_rel_ord_SoSi v1

- Human: `yes` / Gemini: `yes`
- Temporal type: `relative_order`
- Modality: `Action (silent) + Action (sounding)`
- Gemini reason: The temporal order is satisfied as the thigh slap happens before the thumbs-up pose is formed.
- Gemini evidence: The sounding action (thigh slap) occurs at 00:01.000, and the silent action (thumbs up) begins forming afterward and is established by 00:01.875, strictly following the required relative order.
- Detail file: `analysis_results/details/all_tools_TC_TP_Si_So_rel_ord_SoSi_v1.txt`

#### TN — Sp_So_rel_sync_cnt v1

- Human: `no` / Gemini: `no`
- Temporal type: `relative_sync_count`
- Modality: `Speech + Action (sounding)`
- Gemini reason: The prompt requires exactly two synchronized occurrences of the person saying 'help' while slapping the thigh. The video fails this temporal relation entirely: the speech occurs only once without a slap, and the slaps occur four times without speech.
- Gemini evidence: The single speech event occurs between 0.00 and 0.28 seconds while the person's hands are resting on their thighs. The first slap does not occur until 1.00 second, and the action repeats at 2.00s, 3.00s, and 4.00s, meaning the speech and slaps are never synchronized, and the repetition count is incorrect.
- Detail file: `analysis_results/details/all_tools_TC_TN_Sp_So_rel_sync_cnt_v1.txt`

#### TN — Sp_So_abs_sync_cnt v2

- Human: `no` / Gemini: `no`
- Temporal type: `absolute_sync_count`
- Modality: `Speech + Action (sounding)`
- Gemini reason: The temporal schedule and count are incorrect. The prompt requires the synchronized bundle exactly twice (at 1.5s and 3.5s), but the action and speech are absent at 1.5s and occur three times starting at approximately 2.4s.
- Gemini evidence: The person sits completely still at 1.5s. The first synchronized slap and speech event does not happen until around 2.5s. The event is then repeated two more times in rapid succession (around 3.1s and 3.5s), failing the two-count and absolute timing requirements.
- Detail file: `analysis_results/details/all_tools_TC_TN_Sp_So_abs_sync_cnt_v2.txt`

#### TN — Si_So_rel_sync_cnt v1

- Human: `no` / Gemini: `no`
- Temporal type: `relative_sync_count`
- Modality: `Action (silent) + Action (sounding)`
- Gemini reason: The video fails both the synchronization and the strict count constraints. The thumbs-up pose and the thigh slap occur sequentially rather than simultaneously, and the actions are repeated three times instead of the required exactly two times.
- Gemini evidence: The thumbs-up poses (e.g., 00:00.292, 00:00.750, 00:01.792) and the thigh slaps (00:00.000, 00:01.000, 00:02.000) are temporally disconnected. Additionally, there are three distinct thigh slaps rather than the two requested.
- Detail file: `analysis_results/details/all_tools_TC_TN_Si_So_rel_sync_cnt_v1.txt`

#### FP — Sp_Si_So_rel_ord_SoSiSp v1

- Human: `no` / Gemini: `yes`
- Temporal type: `relative_order`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: The temporal sequence required by the prompt is correctly followed: the thigh slap happens first, the thumbs-up is formed and held next, and the speech occurs last.
- Gemini evidence: Slap contact is made at 00:00.917. The thumbs-up pose is formed and held starting at 00:01.833. The speech begins around 00:02.860, after the previous actions have been established.
- Detail file: `analysis_results/details/all_tools_TC_FP_Sp_Si_So_rel_ord_SoSiSp_v1.txt`

#### FP — Sp_Si_So_rel_ord_SpSoSi v3

- Human: `no` / Gemini: `yes`
- Temporal type: `relative_order`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: The required sequence of events is perfectly satisfied: the speech occurs first, followed by the sounding slap action, and concludes with the silent thumbs-up action.
- Gemini evidence: Speech occurs from 0.00 to 0.22 seconds, followed by the slap impact at 2.16 seconds, and finally the thumbs-up pose begins at 3.41 seconds and is held, matching the relative order constraint.
- Detail file: `analysis_results/details/all_tools_TC_FP_Sp_Si_So_rel_ord_SpSoSi_v3.txt`

#### FP — Sp_Si_So_abs_ord_SoSpSi v3

- Human: `no` / Gemini: `yes`
- Temporal type: `absolute_order`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: The expected sequence of events occurs at the correct absolute times according to the prompt schedule.
- Gemini evidence: The slap candidate action and sound occur at 1.0s, followed by the speech event at 2.5s, and finally the thumbs-up gesture is formed at 4.0s.
- Detail file: `analysis_results/details/all_tools_TC_FP_Sp_Si_So_abs_ord_SoSpSi_v3.txt`

#### FN — Sp_Si_So_rel_ord_SpSoSi v2

- Human: `yes` / Gemini: `no`
- Temporal type: `relative_order`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: Although there is a sequence of speech, a striking motion, and a thumbs-up, the specific required target events (striking the right thigh with visible contact and forming a thumbs-up with the right hand) are absent or incorrectly executed, meaning the prompt's exact structural sequence is not completed.
- Gemini evidence: The required sequence demands the right hand striking the thigh and the right hand forming a thumbs-up, but the video shows an air-strike and a left-hand thumbs-up, breaking the integrity of the target sequence.
- Detail file: `analysis_results/details/all_tools_TC_FN_Sp_Si_So_rel_ord_SpSoSi_v2.txt`

#### FN — Si_So_rel_ord_SiSo v3

- Human: `yes` / Gemini: `no`
- Temporal type: `relative_order`
- Modality: `Action (silent) + Action (sounding)`
- Gemini reason: The events occur in the correct relative order (thumbs-up followed by thigh slap), but the thigh slap is repeated multiple times, which violates the strict event structure that requires exactly one instance of the final event.
- Gemini evidence: After the first slap at 00:03.250, the right hand lifts and strikes the thigh again around 00:03.750 and 00:04.250, violating the rule that target actions must not have extra occurrences beyond the specified structure.
- Detail file: `analysis_results/details/all_tools_TC_FN_Si_So_rel_ord_SiSo_v3.txt`

#### FN — Sp_Si_So_abs_sync_cnt v2

- Human: `yes` / Gemini: `no`
- Temporal type: `absolute_sync_count`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: The required synchronized bundle of speech, right-hand thumbs-up, and right-hand slap does not occur at the specified absolute times because the core target actions are incorrect or absent.
- Gemini evidence: The person performs a left-hand thumbs-up instead of a right-hand one, starts the gesture too early (around 1.0s and 3.0s), and never performs the requested right-hand slap at 1.5 seconds or 3.5 seconds.
- Detail file: `analysis_results/details/all_tools_TC_FN_Sp_Si_So_abs_sync_cnt_v2.txt`

### CC

#### TP — Sp_Si_So_rel_ord_SoSpSi v2

- Human: `yes` / Gemini: `yes`
- Temporal type: `relative_order`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: The video satisfies all non-core constraints, including the setting, framing, initial pose, continuous visibility of required body parts, absence of extra actions/speech, and post-event stillness.
- Gemini evidence: The scene is a plain indoor room with a static medium shot. Both hands initially rest on the thighs at 0.00s. The face, upper body, hands, and thighs remain visible. No extra words are spoken, and after the thumbs-up is held, the person remains completely still until the end of the video.
- Detail file: `analysis_results/details/all_tools_CC_TP_Sp_Si_So_rel_ord_SoSpSi_v2.txt`

#### TP — Sp_Si_So_rel_ord_SoSiSp v1

- Human: `yes` / Gemini: `yes`
- Temporal type: `relative_order`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: The video adheres to all scene, camera, and post-event stillness constraints. The person is in a static medium shot within a plain indoor room, and no extra actions or speech occur after the final target event.
- Gemini evidence: The shot remains static and framed correctly. Following the spoken word 'help', the person returns to a resting position and stays completely still from 00:03.500 until the end of the video.
- Detail file: `analysis_results/details/all_tools_CC_TP_Sp_Si_So_rel_ord_SoSiSp_v1.txt`

#### TP — Sp_Si_So_rel_ord_SiSpSo v1

- Human: `yes` / Gemini: `yes`
- Temporal type: `relative_order`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: The video adheres to all non-core constraints including setting, camera angle, subject visibility, lack of extra speech, and post-action stillness.
- Gemini evidence: The video features a static medium shot in a plain indoor room. The seated person's face, upper body, hands, and thighs are visible. No additional words are spoken, no extra sounds are heard, and the person remains still after the final slap action.
- Detail file: `analysis_results/details/all_tools_CC_TP_Sp_Si_So_rel_ord_SiSpSo_v1.txt`

#### TN — Sp_Si_So_rel_sync v3

- Human: `no` / Gemini: `no`
- Temporal type: `relative_synchronization`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: The video violates the prompt's framing and post-event stillness constraints. The top half of the person's face is cropped out, and the slap action repeats multiple times instead of ending in stillness.
- Gemini evidence: The prompt asks for 'full face clearly visible', but only the nose and mouth are within the frame. It also specifies 'no new target action occurs' after the final event, but the right hand strikes the thigh three distinct times.
- Detail file: `analysis_results/details/all_tools_CC_TN_Sp_Si_So_rel_sync_v3.txt`

#### TN — Sp_Si_So_rel_ord_SoSiSp v2

- Human: `no` / Gemini: `no`
- Temporal type: `relative_order`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: The video violates the initial state constraint. The prompt requires the person to start with both hands resting on the knees or thighs, but the person's right hand is already raised high at the very first frame.
- Gemini evidence: At 0.000s, the right hand is raised near head-level rather than resting on the thigh. Other constraints such as the static medium shot, absence of extra speech, and post-event stillness are satisfied.
- Detail file: `analysis_results/details/all_tools_CC_TN_Sp_Si_So_rel_ord_SoSiSp_v2.txt`

#### TN — Si_So_rel_sync_cnt v3

- Human: `no` / Gemini: `no`
- Temporal type: `relative_sync_count`
- Modality: `Action (silent) + Action (sounding)`
- Gemini reason: The person maintains a constant thumbs-up with both hands instead of just the right hand forming it during the events, and there are unnatural body movements.
- Gemini evidence: Both hands stay in a thumbs-up pose from 00:00.000 to the end, violating the prompt's instruction for the right hand to form the pose during the strike. Additionally, the person's knees unnaturally raise and bounce between the two events.
- Detail file: `analysis_results/details/all_tools_CC_TN_Si_So_rel_sync_cnt_v3.txt`

#### FP — Sp_Si_rel_ord_SpSi v3

- Human: `no` / Gemini: `yes`
- Temporal type: `relative_order`
- Modality: `Speech + Action (silent)`
- Gemini reason: The video complies with all non-core constraints, including the scene, shot type, starting pose, visibility requirements, and post-event stillness.
- Gemini evidence: The video features a static medium shot in a plain room with the full face, mouth, upper body, both hands, and thighs visible. The person starts with hands on thighs, speaks, performs the thumbs-up, and remains still while holding the pose until the video ends. No background music, subtitles, or extra sounds are present.
- Detail file: `analysis_results/details/all_tools_CC_FP_Sp_Si_rel_ord_SpSi_v3.txt`

#### FP — Sp_Si_abs_sync_cnt v2

- Human: `no` / Gemini: `yes`
- Temporal type: `absolute_sync_count`
- Modality: `Speech + Action (silent)`
- Gemini reason: The video adheres to the non-core constraints: the setting is a plain indoor room, the camera is a static medium shot, the person starts with both hands resting on their knees, and no extra words or unrequested actions are present.
- Gemini evidence: Visual inspection confirms the correct plain background, static framing, and initial resting pose. Whisper ASR detects no extra words beyond 'help'.
- Detail file: `analysis_results/details/all_tools_CC_FP_Sp_Si_abs_sync_cnt_v2.txt`

#### FP — Sp_Si_So_abs_ord_SoSiSp v1

- Human: `no` / Gemini: `yes`
- Temporal type: `absolute_order`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: The video adheres to all scene, camera, and character constraints without any extra unprompted actions or sounds.
- Gemini evidence: The scene is a plain indoor room, shot in a static medium shot showing the required body parts. The person begins with hands resting on their thighs, there are no subtitles, background music, or extra people, and the final pose is held without additional actions.
- Detail file: `analysis_results/details/all_tools_CC_FP_Sp_Si_So_abs_ord_SoSiSp_v1.txt`

#### FN — Sp_Si_So_rel_sync v2

- Human: `yes` / Gemini: `no`
- Temporal type: `relative_synchronization`
- Modality: `Speech + Action (silent) + Action (sounding)`
- Gemini reason: The video fails the post-event stillness constraint by including an extra, unnatural action after the target sequence.
- Gemini evidence: After striking the thigh at 0.33s, the person raises their right hand back into the air at 0.45s and statically holds the thumbs-up pose for the remainder of the video, failing to remain still or return to a resting position.
- Detail file: `analysis_results/details/all_tools_CC_FN_Sp_Si_So_rel_sync_v2.txt`

#### FN — Sp_So_rel_sync v3

- Human: `yes` / Gemini: `no`
- Temporal type: `relative_synchronization`
- Modality: `Speech + Action (sounding)`
- Gemini reason: The video includes an extra unprompted action (the left hand slapping the left thigh), which violates the constraint against extra gestures. However, the scene, camera shot, and post-event stillness constraints are followed.
- Gemini evidence: The left hand actively participates in the slap between 0.00s and 0.375s instead of remaining resting. Post-event stillness is maintained from 0.50s to the end of the video.
- Detail file: `analysis_results/details/all_tools_CC_FN_Sp_So_rel_sync_v3.txt`

#### FN — Sp_So_rel_sync_cnt v1

- Human: `yes` / Gemini: `no`
- Temporal type: `relative_sync_count`
- Modality: `Speech + Action (sounding)`
- Gemini reason: The video violates the exact count and post-event stillness constraints by including extra slaps and continuing the action beyond the specified two repetitions.
- Gemini evidence: The original prompt requires exactly two slap events and stillness afterward. The video features four visible and audible slaps, failing both the strict count and the post-event stillness requirement.
- Detail file: `analysis_results/details/all_tools_CC_FN_Sp_So_rel_sync_cnt_v1.txt`
