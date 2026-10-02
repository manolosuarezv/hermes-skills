#!/usr/bin/env python3
"""Scrub a leaked secret from Hermes state.db (chat history) and rebuild FTS index.

Usage:
    redact_secret.py <state.db path> <SECRET> [REPLACEMENT]

The SECRET is passed on argv (not hardcoded) so it is not persisted in this file.
Steps: backup db -> redact secret from message/delivery/async tables -> drop+recreate
FTS5 virtual tables and rebuild them.

Covers the leak class where a token pasted in chat is persisted to state.db and can
be re-emitted by the gateway's failure-recovery path. See references/secret-leak-recovery.md.
"""
import sys, os, shutil, sqlite3

TABLES = [
    ("messages", "content"), ("messages", "api_content"),
    ("delivery_obligations", "content"), ("gateway_routing", "entry_json"),
    ("async_delegations", "event_json"), ("async_delegations", "result_json"),
    ("async_delegations", "task_json"),
]


def main():
    if len(sys.argv) < 3:
        print("usage: redact_secret.py <state.db> <SECRET> [REPLACEMENT]", file=sys.stderr)
        sys.exit(2)
    db, secret = sys.argv[1], sys.argv[2]
    repl = sys.argv[3] if len(sys.argv) > 3 else "[REDACTED_SECRET]"
    if not os.path.exists(db):
        print("db not found:", db, file=sys.stderr); sys.exit(1)

    bak = db + ".bak_preredact"
    if not os.path.exists(bak):
        shutil.copy2(db, bak)

    prefix = secret[:24]          # LIKE-safe: secrets may contain '%'
    like = prefix + "%"

    con = sqlite3.connect(db); cur = con.cursor()
    for tbl, col in TABLES:
        try:
            cur.execute(f"UPDATE {tbl} SET {col}=REPLACE({col},?,?) WHERE {col} LIKE ?",
                        (secret, repl, like))
        except sqlite3.OperationalError as e:
            print("skip", tbl, col, e)
    con.commit()
    cur.execute("SELECT COUNT(*) FROM messages WHERE content LIKE ? OR api_content LIKE ?", (like, like))
    remain = cur.fetchone()[0]
    con.close()

    # Rebuild FTS5 virtual tables + shadow tables (a 'delete' insert corrupts them).
    con = sqlite3.connect(db); cur = con.cursor()
    for base in ("messages_fts", "messages_fts_trigram"):
        for suf in ("", "_data", "_idx", "_docsize", "_config"):
            cur.execute(f"DROP TABLE IF EXISTS {base}{suf}")
    cur.execute("CREATE VIRTUAL TABLE messages_fts USING fts5(content, tool_name, tool_calls, content='messages', content_rowid='id')")
    cur.execute("CREATE VIRTUAL TABLE messages_fts_trigram USING fts5(content, tool_name, tool_calls, content='messages', content_rowid='id', tokenize='trigram')")
    cur.execute("INSERT INTO messages_fts(messages_fts) VALUES('rebuild')")
    cur.execute("INSERT INTO messages_fts_trigram(messages_fts_trigram) VALUES('rebuild')")
    con.commit(); con.close()

    print(f"redacted. remaining token matches in messages: {remain}")
    print(f"FTS rebuilt. backup at {bak}")
    if remain:
        print("WARNING: secret still present (uncovered column?) — inspect manually", file=sys.stderr)


if __name__ == "__main__":
    main()
