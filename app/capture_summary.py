"""Bounded, read-only overview of uploaded captures for one device."""
from datetime import datetime


def capture_summaries(db, device: str, limit: int = 50) -> list[dict]:
    """Return capture spans and holes within observed sample sequence ranges.

    Spans include stops and gaps, so they are not riding time. Sequence holes
    describe uploads only; they do not establish that CAN frames were lost.
    The connection stays owned by the caller, and payloads are never loaded.
    """
    limit = max(1, min(100, int(limit)))
    cursor = db.execute('''
        SELECT capture_id, COUNT(*) AS sample_count,
               MIN(timestamp) AS first_timestamp, MAX(timestamp) AS last_timestamp,
               MIN(sequence) AS first_sequence, MAX(sequence) AS last_sequence
        FROM samples WHERE device_id = ?
        GROUP BY capture_id
        ORDER BY last_timestamp DESC, capture_id ASC LIMIT ?
    ''', (device, limit))
    names = [column[0] for column in cursor.description]
    try:
        summaries = []
        for row in cursor:
            item = dict(zip(names, row))
            first = datetime.fromisoformat(item['first_timestamp'].replace('Z', '+00:00'))
            last = datetime.fromisoformat(item['last_timestamp'].replace('Z', '+00:00'))
            item['duration_seconds'] = max(0, (last-first).total_seconds())
            item['missing_sequences'] = max(0, item['last_sequence']-item['first_sequence']+1-item['sample_count'])
            summaries.append(item)
        return summaries
    finally:
        cursor.close()
