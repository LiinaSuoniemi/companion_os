# Companion OS

An educational AI companion built for people who need more than a chatbot.

## What it is

Companion OS is a structured educational cognitive support tool. It teaches coping skills, grounding techniques, and self-awareness to people whose brains work differently under stress. It does not replace professional help. It fills the gap between having nothing and having everything. Structure when there is none. Grounding when things get overwhelming. Practical tools for daily life that most people pick up without ever being taught.

It runs on 16 modes. Each mode activates based on what the user says. The user does not need to know which mode they need.

## Who it is for

Some people never received the basics. Not because they lacked the ability. Because the systems around them failed to deliver: structure, stability, a framework for thinking through hard things, someone who does not panic when you say something difficult.

Others lost these things. A life disruption that removed the scaffolding. A period of time that replaced personal routine with someone else's rules. A health event that damaged internal systems most people rely on without thinking. A long season of isolation that eroded everything.

Companion OS is built for them first. The tools are not remedial. They are fundamental. The same tools work for anyone who wants them.

## The modes

Each mode solves a specific problem. None of them are decorative. Modes activate automatically based on what the user says. One mode at a time.

| Mode | What it does |
|------|-------------|
| Calm | Gets you grounded when overwhelmed or in crisis. Brings you back to now. |
| Mindfulness | Guides breathing and grounding when you need to slow down. |
| Steady | Supports you through strong impulses without judgment. Helps you ride them out. |
| Reality Check | Catches when you are building a story and about to act on it instead of facts. |
| Focus | Helps you start and finish tasks. Breaks work into steps when you are stuck. |
| Planning | Helps structure your day, week, or project. Cuts through competing demands. |
| Decision | Helps you choose between options. Externalises the decision so you can see it clearly. |
| Study | Helps you learn without overwhelm. Breaks complex topics into pieces. |
| Read | Helps you process texts, articles, or messages when reading feels hard. |
| Daily Companion | Daily check-ins and gentle routine support. Keeps you on track. |
| Reflection | Helps you understand your own patterns. Makes sense of what keeps happening. |
| Boundary | Supports you in setting or holding limits in relationships and situations. |
| Listen | Prepares you to be truly present in a conversation. |
| Express | Helps you say what you actually mean, clearly, without shutting down. |
| Feedback | Helps you receive criticism and praise accurately. |
| Habit and Aim | Identifies what you are trying to become, audits what you are doing daily, and builds the system to close the gap. |

Every mode has a safety ceiling. If crisis indicators appear in any mode, the system shifts to Calm Mode. A permanent crisis banner with local numbers in the user's language is always visible. A one-tap emergency button is always one step away. The AI does not go cold. The conversation continues. The safety layer is in the interface.

## What is behind each mode

Every mode draws on established psychology and behaviour research. Nothing here is invented by me. The thinking behind each mode can be traced to its sources.

Staying present in distress draws on trauma-informed approaches. Distress is a physiological response, not a character flaw. The body needs to come first.

Separating facts from stories draws on cognitive approaches to thinking clearly under pressure. We build narratives around events. Acting on the narrative instead of the facts is where things go wrong.

Getting through difficult moments draws on behaviour change research. Strong impulses follow predictable patterns. Knowing that changes how you wait them out.

Listening and expression draw on person-centred approaches. Genuine presence without premature judgment is itself useful. Saying what you actually mean starts with knowing what it is.

Habit and Aim work draws on habit formation frameworks, meaning-centred psychology, and growth mindset research. Identity matters more than willpower. An aim transforms the experience of daily effort. How feedback is framed shapes whether people grow or shut down.

## Philosophy

No mode advises, diagnoses, treats, or replaces professional care. Companion OS teaches skills and provides structure only.

The AI never pastes a hotline number and goes quiet. When someone says something difficult, the response is to stay present, not to exit. Safety and warmth are not opposites.

80% human. 20% AI. The person is always in charge.

## About the model

Companion OS runs on Claude. The choice is deliberate.

Safety in Companion OS comes from several layers: the user interface (crisis banner, kill switch, account deletion), the data layer (encryption, GDPR compliance), the prompt layer (mode behaviour, refusals, warmth in crisis), and the model itself.

The prompts assume a model capable enough to follow nuanced safety guidance under pressure. Early testing on smaller open models (4 billion parameters) showed significant safety degradation. The prompts read fine, but the model did not actually follow them when it mattered.

Until prompts and architecture can make smaller models safe enough, the model is part of the safety stack. Self-hosting on a smaller model is at your own risk and not recommended for vulnerable users.

This is a real constraint, not a marketing position. Making smaller open models safe enough is on the long-term roadmap.

## Status

Deployed on Railway with Django backend and PostgreSQL.

Live as of April 2026:
- 16 modes, each grounded in established psychology and behaviour research
- Trilingual crisis detection (Finnish, Estonian, English)
- Conversation persistence with encryption at rest
- Permanent crisis banner with verified helplines, present on every page
- Session limits: 2 new conversations per day, 30 per month
- Helps users read patterns of grooming and sextortion in messages they share
- Explicit consent under GDPR Article 9, separated from optional usage tracking
- Optional impact survey at signup and after 4 weeks
- Account deletion with full database removal (GDPR Article 17)

Currently in private pilot preparation, opening in May 2026. Not yet open to the public. Invite-only access.

## Built by

Liina Suoniemi / [InkNCode Solutions](https://www.linkedin.com/in/liina-suoniemi)

## License

Licensed under the MIT License. See `LICENSE` for details.
