"""Neo4j driver wrapper."""

from __future__ import annotations

import logging
import os
from contextlib import contextmanager
from typing import Any, Generator, Iterator

from neo4j import Driver, GraphDatabase, ManagedTransaction, Session as NeoSession

logger = logging.getLogger(__name__)


class Neo4jClient:
    """Thin, typed-ish wrapper around the official neo4j driver."""

    def __init__(
        self,
        uri: str | None = None,
        user: str | None = None,
        password: str | None = None,
        database: str | None = None,
    ) -> None:
        self.uri = uri or os.environ.get("NEO4J_URI", "bolt://localhost:7687")
        self.user = user or os.environ.get("NEO4J_USER", "neo4j")
        self.password = password or os.environ.get("NEO4J_PASSWORD", "password")
        self.database = database or os.environ.get("NEO4J_DATABASE", "neo4j")
        self._driver: Driver | None = None

    def connect(self) -> Neo4jClient:
        if self._driver is None:
            self._driver = GraphDatabase.driver(
                self.uri,
                auth=(self.user, self.password),
            )
            logger.info("Connected to Neo4j at %s", self.uri)
        return self

    def close(self) -> None:
        if self._driver is not None:
            self._driver.close()
            self._driver = None

    def __enter__(self) -> Neo4jClient:
        return self.connect()

    def __exit__(self, *args: object) -> None:
        self.close()

    @property
    def driver(self) -> Driver:
        if self._driver is None:
            self.connect()
        assert self._driver is not None
        return self._driver

    def verify(self) -> bool:
        try:
            self.driver.verify_connectivity()
            return True
        except Exception as exc:  # noqa: BLE001
            logger.error("Neo4j connectivity failed: %s", exc)
            return False

    @contextmanager
    def session(self) -> Generator[NeoSession, None, None]:
        sess = self.driver.session(database=self.database)
        try:
            yield sess
        finally:
            sess.close()

    def run(
        self,
        cypher: str,
        parameters: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> list[dict[str, Any]]:
        params = {**(parameters or {}), **kwargs}
        with self.session() as sess:
            result = sess.run(cypher, params)
            return [dict(record) for record in result]

    def write(
        self,
        cypher: str,
        parameters: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> list[dict[str, Any]]:
        params = {**(parameters or {}), **kwargs}

        def _work(tx: ManagedTransaction) -> list[dict[str, Any]]:
            result = tx.run(cypher, params)
            return [dict(record) for record in result]

        with self.session() as sess:
            return list(sess.execute_write(_work))

    def read(
        self,
        cypher: str,
        parameters: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> list[dict[str, Any]]:
        params = {**(parameters or {}), **kwargs}

        def _work(tx: ManagedTransaction) -> list[dict[str, Any]]:
            result = tx.run(cypher, params)
            return [dict(record) for record in result]

        with self.session() as sess:
            return list(sess.execute_read(_work))

    def execute_many(self, statements: Iterator[str] | list[str]) -> None:
        with self.session() as sess:
            for stmt in statements:
                stmt = stmt.strip()
                if stmt:
                    sess.run(stmt)
