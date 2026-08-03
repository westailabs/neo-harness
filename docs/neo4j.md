# Neo4j

Neo4j is the **single source of truth** for sessions and typed memory.

## Connection

| Env | Default | Notes |
|-----|---------|-------|
| `NEO4J_URI` | `bolt://localhost:7687` | Bolt URL |
| `NEO4J_USER` | `neo4j` | |
| `NEO4J_PASSWORD` | `password` | **Must match the server** |
| `NEO4J_DATABASE` | `neo4j` | |

Client: `neo_harness.neo4j.client.Neo4jClient`  
Schema setup: `neo_harness.neo4j.schema.setup_schema` via `neo init-db`.

## Node labels

| Label | Purpose |
|-------|---------|
| `Session` | Work unit: task, status, harness state, counters |
| `Episode` | Timeline event (plan, action, observation, reflection, …) |
| `Reflection` | Structured reflection payload |
| `Decision` | Semantic durable decision statements |
| `Artifact` | Produced outputs (file/url/text refs) |

## Relationships

| Rel | Meaning |
|-----|---------|
| `HAS_EPISODE` | Session → Episode |
| `HAS_REFLECTION` | Session → Reflection |
| `MADE_DECISION` | Session → Decision |
| `PRODUCED` | Session → Artifact |
| `RELATED_TO` | Session → Session (optional linking) |

Reflections are also mirrored as `Episode` nodes (`kind=reflection`) for unified timelines.

## Constraints and indexes

Applied by `neo init-db` (idempotent), defined in `neo4j/schema.py`:

- Unique `id` on Session, Episode, Reflection, Decision, Artifact  
- Indexes on status/state/updated_at, session_id, kind, created_at  
- Full-text: `episode_summary_ft`, `decision_statement_ft`

## Session properties (high level)

`id`, `task`, `status` (`active|paused|completed|failed|blocked`),  
`state` (harness state string), `goal`, `step_count`, `action_count`,
`reflection_count`, timestamps, `metadata`, `last_error`.

## Browser (http://localhost:7474)

### Session overview

```cypher
MATCH (s:Session)
RETURN s.id, s.task, s.status, s.state, s.action_count, s.reflection_count, s.updated_at
ORDER BY s.updated_at DESC
LIMIT 20
```

### Timeline for one session

```cypher
MATCH (s:Session {id: $sessionId})-[:HAS_EPISODE]->(e:Episode)
RETURN e.kind, e.state, e.summary, e.created_at, e.success
ORDER BY e.created_at ASC
```

### Reflections

```cypher
MATCH (s:Session {id: $sessionId})-[:HAS_REFLECTION]->(r:Reflection)
RETURN r.trigger, r.next_action, r.confidence, r.what_happened, r.created_at
ORDER BY r.created_at
```

### Graph neighborhood

```cypher
MATCH (s:Session {id: $sessionId})
OPTIONAL MATCH (s)-[r]->(n)
RETURN s, r, n
```

### Counts

```cypher
MATCH (s:Session {id: $sessionId})
OPTIONAL MATCH (s)-[:HAS_EPISODE]->(e)
OPTIONAL MATCH (s)-[:HAS_REFLECTION]->(ref)
RETURN s.task, s.state, s.status,
       count(DISTINCT e) AS episodes,
       count(DISTINCT ref) AS reflections
```

## Lab topology notes

On shurtugal you may have **multiple** Neo4j instances:

| Instance | Typical ports | Role |
|----------|---------------|------|
| `neo4j` (lab compose) | 7474 / **7687** | Default for neo-harness |
| `copilot-memory-neo4j` | 17474 / 17687 | Other stacks (OAP/copilot) |

Point `NEO4J_URI` at the instance you intend. Do not assume password `password`.

## Dev wipe (dangerous)

`schema.drop_all_harness_data` deletes harness labels only (Session/Episode/…).  
Not exposed on the CLI by default — use only in disposable DBs.
