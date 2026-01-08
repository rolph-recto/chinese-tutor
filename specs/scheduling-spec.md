# Exercise Scheduling 

## 1. Mode Management and Transition Logic

* **Ubiquitous:** The System shall maintain two distinct exercise pools: the **Learning Mode** (for unmastered skills) and the **Retention Mode** (for skills that have reached the mastery threshold).
* **When** a session is initialized, the System shall compose the exercise queue based on a configurable ratio of Learning Mode items to Retention Mode items.
* **When** the Learning Mode contains no eligible skills, the System shall populate the session entirely with items from the Retention Mode.
* **When** a skill’s Probability of Mastery () first exceeds 0.95, the System shall permanently move that skill from the Learning Mode to the Retention Mode.

---

## 2. Learning Mode Logic (BKT and Practice Scheduling)

* **Ubiquitous:** The System shall update the Probability of Mastery () for every skill in the Learning Mode using the Bayesian Knowledge Tracing algorithm after every response.
* **When** the student selects a skill cluster from the menu, the System shall activate **Blocked Practice** for that specific cluster.
* While Blocked Practice is active, the System shall only generate exercises for skills belonging to the selected cluster.
* **When** all skills within the current blocked cluster reach a , the System shall present the Topic Selection Menu and activate **Interleaved Practice**.
* While Interleaved Practice is active, the System shall select exercises from the pool of all skills currently in Learning Mode across all eligible clusters.
* **When** the student selects a new skill cluster from the menu while in Interleaved Practice, the System shall reactivate Blocked Practice for the newly selected cluster.

---

## 3. Retention Mode Logic (FSRS)

* While selecting exercises from the Retention Mode, the System shall rank skills according to the **FSRS (Free Spaced Repetition Scheduler)** algorithm, targeting skills with the lowest **Retrievability ()**.
* **When** a retention exercise is completed, the System shall update the FSRS **Stability ()** and **Difficulty ()** parameters for that skill.
* **When** a retention exercise is answered incorrectly, the System shall update the FSRS parameters to shorten the next review interval but **the System shall NOT** move the skill back to the Learning Mode.

---

## 4. Multi-Skill Exercise Handling

* **When** a multi-skill exercise is answered correctly, the System shall apply an upward BKT update to the  of all associated skills.
* **When** a multi-skill exercise is answered incorrectly, the System shall apply a downward BKT update to the  of all associated skills.

---

## 5. Student Agency and Menu Generation

* While generating the Topic Selection Menu, the System shall only include skill clusters that contain at least one unmastered skill () and where all prerequisite skills have been mastered ().
* The System shall NOT include clusters in the Topic Selection Menu where all constituent skills have already been moved to Retention Mode.
* The System shall restrict the Topic Selection Menu functionality exclusively to exercises delivered within the Learning Mode.