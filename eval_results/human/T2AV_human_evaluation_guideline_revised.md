# T2AV Human Evaluation Guideline

## 1. Event

An **event** is a prompt-specified unit that may contain an audio component, a visual action or state, or both.

We use three event types:

- **Speech:** spoken audio and the corresponding visible speaking behavior  
  - Example: saying “help”
- **Silent action:** a visual action without a required sound  
  - Example: a thumbs-up
- **Sounding action:** a visual action and its corresponding sound  
  - Example: slapping the thigh

---

## 2. Evaluation axes

The evaluation consists of six axes.

**Hierarchy:**  
`A / V → AVB → TC_REL and TC_COUNT`

- A and V are evaluated first.
- AVB is evaluated only for events that contain both audio and visual components.
- For such events, AVB fails if either the required audio or visual component fails.
- TC_REL and TC_COUNT fail if any event required for the temporal judgment fails A, V, or its applicable AVB.


| Axis | Definition |
|---|---|
| **A — Audio Event Correctness** | Whether the required speech or sound event is present and correct in the audio. |
| **V — Visual Event Correctness** | Whether the required visual event is present and correct in the video. For speech events, this evaluates visible speaking behavior, such as mouth or lip motion, not the spoken content itself. |
| **AVB — Audio–Visual Binding** | Whether the audio and visual components within the same event are correctly synchronized and causally aligned. |
| **TC_REL — Temporal Relation Satisfaction** | Whether the specified temporal relationship between events is satisfied, including synchronization, order, and absolute timing. |
| **TC_COUNT — Temporal Count Satisfaction** | Whether each required event occurs the specified number of times, without missing or extra occurrences. |
| **CC — Constraint Compliance** | Whether non-core prompt constraints are satisfied, such as scene, camera condition, subject count, absence of subtitles or background music, no extra actions or sounds, and post-event stillness when explicitly required. |

---

## 3. A — Audio event correctness

PASS when every required speech or sound component is present, clear, and correct.

FAIL when:

- a required audio event is missing;
- the spoken content or sound type is incorrect;
- the audio is too unclear to identify.

Examples:

- Required speech is “help,” but the person says “it helps” → **A FAIL**
- The required speech is correct, followed by a separate extra speech or cough → **A PASS; CC FAIL**
- A sounding action is visible, but its required sound is absent → **A FAIL, V PASS**

---

## 4. V — Visual event correctness

PASS when every required visual component is present, visible, and correct with respect to actor, action, side, body part, object, and contact target.

FAIL when:

- the required visual event is missing;
- the wrong actor, side, body part, object, or action is used;
- occlusion, cropping, or blur prevents verification.
- for speech, the mouth movement is absent or visibly inconsistent with the required utterance.

### General examples

- The required visual event is performed correctly and remains clearly visible, but an unrelated action is added → **V PASS; CC FAIL**
- The extra action disrupts, replaces, or hides the required visual event → **V FAIL; CC FAIL**
- The target action is performed by the wrong actor or with the wrong body part → **V FAIL**
- The actor appears to speak, but the lip movement does not match the required utterance → **V FAIL**
- The lip movement matches the required utterance, but the spoken audio is incorrect → **V PASS; A FAIL**

---

## 5. AVB — Audio–visual binding

AVB evaluates the temporal alignment of the **audio and visual components within the same event.**

PASS when the sound is synchronized with the corresponding visible action, impact, or mouth movement.

FAIL when:

- A or V fails;
- the audio and visual components are clearly temporally misaligned.

Temporal relations **between different events** are evaluated under TC_REL, not AVB.

---

## 6. TC_REL — Temporal relation

TC_REL is evaluated by comparing the defined start times of the required events.

Each event’s start time is defined as follows:

- **Speech or sound:** when the target audio begins
- **Held pose or state:** when the target pose or state first becomes clearly established
- **Contact or impact:** the actual contact moment
- **Other action:** when the required action visibly begins

For a sounding contact or impact action, such as a slap, the contact or impact moment is used as the event start time.

If any event required for the temporal relation fails A, V, or AVB, TC_REL is **FAIL**.

### Synchronization

PASS when the relevant events appear to begin at the same moment.

Simple overlap is not sufficient.

Example: a pose is already held for a while and speech begins later → **Sync FAIL**

### Order

PASS when the relevant events clearly begin in the required order.

The earlier event does not need to end before the next event begins. Overlap is allowed.

Example: the events appear to begin simultaneously, or their order is wrong, or their order cannot be clearly distinguished → **Order FAIL**

### Absolute timing

PASS when the event starts within about **±0.3 seconds** of the required timestamp.

---

## 7. TC_COUNT — Temporal count

PASS when every required event occurs exactly the specified number of times.

If any event required for counting fails A, V, or its applicable AVB, TC_COUNT is **FAIL**.

If no count is explicitly given, the expected count is **one**.

- A continuously held pose counts as one occurrence.
- Releasing and forming the pose again creates another occurrence.
- Each distinct speech utterance, sound, contact, or action repetition counts separately.

Extra or missing repetitions of any target event → **TC_COUNT FAIL**

The same repetition error should not also be counted as an unrelated extra action under CC.

---

## 8. CC — Constraint compliance

CC covers prompt requirements not already evaluated by A, V, AVB, TC_REL, or TC_COUNT.

Examples include:

- scene and camera conditions;
- number and identity of subjects;
- initial pose and required visibility;
- absence of subtitles, on-screen text, or background music;
- absence of additional deliberate actions, speech, or salient sounds;
- post-event stillness, only when explicitly required.

Allowed natural motion includes blinking, breathing, minor posture adjustment, necessary preparation, and natural reset motion.

---

## 9. Evaluation order

1. Check whether each required event is present and correct.
2. Evaluate A and V.
3. Apply the hierarchy and evaluate AVB.
4. Evaluate TC_REL.
5. Evaluate TC_COUNT.
6. Evaluate CC for remaining non-core constraints and unrelated extra events.