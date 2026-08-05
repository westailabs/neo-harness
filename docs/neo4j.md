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

## Multiple Neo4j instances

You may run more than one Neo4j on a machine (different host ports). Point
`NEO4J_URI` at the instance intended for **harness session memory**. Do not
assume password `password` unless you started the container that way.

| Example | Typical ports | Notes |
|---------|---------------|------|
| Default Docker (`neo4j:5`) | 7474 / **7687** | Matches `.env.example` |
| Custom compose / remapped ports | e.g. 17474 / **17687** | Host port ≠ container 7687 |

**Tip:** Docker maps *host*→*container*. If you see `17687->7687/tcp`, clients
must use **`bolt://localhost:17687`**, not `7687`. A timeout on 7687 almost
always means “nothing listening there,” not a failed schema install.

```bash
docker ps --format '{{.Names}} {{.Ports}}' | grep -i neo4j
```

`neo init-db` only applies constraints/indexes to the URI in env — it does **not**
start Neo4j. See [troubleshooting.md](./troubleshooting.md#faq--tip-init-db-times-out-on-localhost7687).

Keep harness memory separate from unrelated app graphs unless you design schema isolation.

## Dev wipe (dangerous)

`schema.drop_all_harness_data` deletes harness labels only (Session/Episode/…).  
Not exposed on the CLI by default — use only in disposable DBs.
