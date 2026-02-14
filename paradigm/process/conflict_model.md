# Conflict Model

ABD assumes parallel work causes hidden conflicts.

## Conflict Inputs

Each task must declare:
- touched files or modules
- behavior surface
- data surface
- dependencies

## Conflict Score

Scores range from 0 to 100.

High score means:
- high risk of collision
- reduced agent reliability

## Thresholds

0 to 29: safe
30 to 59: caution
60 and above: replan required

## Replan Options

- split tasks
- merge ownership
- add enabling task
- reorder execution
