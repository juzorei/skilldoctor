# skilldoctor

[English](README.md) | [Русский](README.ru.md)

Скилл и CLI для аудита установленных скиллов ИИ-агентов: сломанные SKILL.md и дубли, затеняющие друг друга в разных каталогах установки.

Агенты собирают скиллы из нескольких каталогов, у каждого своя приоритетность. Один скилл, установленный дважды — классический тихий фейл: правишь одну копию, агент грузит другую — и «починка не работает». Сломанный скилл (битый frontmatter, несовпадение имени, пустое описание) вообще не триггерится, и модель его просто не использует — без единой ошибки где-либо. `skilldoctor` отображает все каталоги скиллов и репортит оба класса проблем:

```text
$ skilldoctor scan
scanned 4 skill directories, found 48 skills

DUPLICATES / SHADOWING
  brainstorming
  -> wins  project zcode   C:\proj\.zcode\skills\brainstorming
           user   zcode   C:\Users\me\.zcode\skills\brainstorming
     project-level skills shadow user-level ones in agents that document precedence
```

(Первый же прогон на живой машине нашёл 48 скиллов, 13 сломанных, 14 конфликтов-дублей — этот класс отказов есть везде, где скиллы ставят из нескольких источников.)

## Что в репозитории

- **[skills/skill-hygiene-audit](skills/skill-hygiene-audit)** — процесс чистки для агентов: сначала прочитай причину конфликта (затенение проект-над-пользователем или недокументированный дубль в одном scope), сделай diff перед удалением любой из копий, почини сломанный frontmatter, пересканируй после каждой установки. Предлагает план дедупликации; никогда не удаляет молча.
- **tools/skilldoctor** — CLI ([README](tools/skilldoctor/README.md)): `scan` (все известные layout'ы, project + user, exit 1 при любой проблеме) и `check` (валидация одного скилла). Честность про приоритеты: победитель помечается только там, где агент документирует приоритет; в остальных случаях дубль репортится без угадываний. `--json`, только stdlib.

## Установка

```bash
pip install agent-skilldoctor
npx skills add juzorei/skilldoctor
```

## Ещё из портфеля

Один из серии прицельных наборов «скилл + CLI» одного автора:

- [game-re-skills](https://github.com/juzorei/game-re-skills) — самая большая коллекция, на которой обкатаны эти аудиты
- [ci-autopsy](https://github.com/juzorei/ci-autopsy) — запускай аудит скиллов в CI по той же схеме
- [loglens](https://github.com/juzorei/loglens) — триаж любых логов, включая транскрипты агентов

Остальные — в [профиле juzorei](https://github.com/juzorei?tab=repositories).

## Рамки

Аудит каталогов скиллов на своих машинах; удаление — только решение владельца.

Лицензия MIT.
