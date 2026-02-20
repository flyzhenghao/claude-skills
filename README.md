# Claude Skills by flyzhenghao

A collection of Claude Code skills for skill ecosystem monitoring and analysis.

## Available Skills

### [skill-trending-monitor-cskill](skills/skill-trending-monitor-cskill/)

Claude Code skill ecosystem monitoring with dual-source architecture. Fetches from claude-plugins.dev API (53,759+ skills, hourly updates) and skill-manager local DB (41,502 skills, offline fallback with Chinese descriptions). Calculates GitHub star growth rates, discovers new skills, finds similar alternatives using TF-IDF similarity, and generates weekly reports with security evaluations.

**Install:**
```bash
npx skills-installer install @flyzhenghao/claude-skills/skill-trending-monitor-cskill
```

**Trigger phrases:**
- "What are the trending Claude skills this week?"
- "Discover new high-quality skills"
- "Which of my skills should I replace?"
- "Generate weekly skill report"
- "Security evaluation of my skills"

## Installation

```bash
npx skills-installer install @flyzhenghao/claude-skills/<skill-name>
```

## License

MIT
