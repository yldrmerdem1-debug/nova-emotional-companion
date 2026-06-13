# Emotional Companion MVP

## Positioning

Nova is a Turkish emotional companion for daily check-ins, reflective listening, and mood journaling. It is not a therapist and should not be marketed as a replacement for professional mental health care.

## Core Promise

A Turkish-first AI companion that listens without judgment, reflects the user's emotional state before giving advice, remembers support preferences, and stays calm during difficult moments.

## Demo Scenario

1. User opens the app and selects a mode: `Sadece dinle`, `Beraber düşün`, or `Kısa cevap`.
2. User writes: "I feel bad today, I do not want solutions."
3. Nova reflects the feeling and stays in listen-first mode.
4. The mood journal records the latest mood, intensity, and support preference.
5. User gives feedback if the answer felt too cold, too pushy, or too long.

## Safe Marketing Copy

- "A Turkish AI companion that listens without judgment."
- "A private space for daily mood tracking and emotional reflection."
- "A calm support assistant that encourages real human help when it matters."

Avoid:

- "Provides therapy."
- "Cures depression."
- "Replaces a psychologist."

## First Paid Use Cases

- Individual premium: longer history, mood journal, memory, weekly emotional summary.
- Student and young adult support: stress check-ins, low-pressure listening, study-life balance reflection.
- Institutional pilot: dorms, education centers, or counseling teams using opt-in, privacy-first anonymous trend reports.

## Pricing Sketch

- Free: limited daily messages and basic mood journal.
- Premium: unlimited personal history, weekly summary, voice conversation, stronger personalization.
- B2B pilot: institution dashboard, anonymized emotional trend summaries, privacy controls, onboarding support.

## MVP Guardrails

- Keep Ollama off by default on low-end PCs.
- Keep debug/mind workspace hidden from the normal user flow.
- Ask before problem-solving when the user is venting.
- Show crisis-safe language when self-harm or urgent risk appears.
- Make memory and deletion behavior clear before launch.
