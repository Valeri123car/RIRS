"""Obvestila o napredku analize prek Redis (pub/sub)."""

import uuid

import fakeredis

from app.analysis.progress import RedisProgressNotifier, RedisProgressWaiter, channel


def test_obvestilo_doseze_narocnika_iste_analize():
    redis = fakeredis.FakeRedis()
    analysis_id = uuid.uuid4()
    pubsub = redis.pubsub(ignore_subscribe_messages=True)
    pubsub.subscribe(channel(analysis_id))
    pubsub.get_message(timeout=0.1)  # potrditev naročila

    RedisProgressNotifier(redis)(analysis_id)

    message = pubsub.get_message(timeout=1)
    assert message is not None
    assert message["channel"] == f"analysis:{analysis_id}".encode()


def test_cakanje_se_konca_ob_obvestilu_ali_izteku():
    redis = fakeredis.FakeRedis()
    analysis_id = uuid.uuid4()
    waiter = RedisProgressWaiter(redis, analysis_id)
    try:
        RedisProgressNotifier(redis)(analysis_id)
        waiter.wait(timeout=1)  # ne obvisi: obvestilo ali iztek
        waiter.wait(timeout=0.05)  # brez obvestila: počaka največ timeout
    finally:
        waiter.close()
    assert redis.pubsub_numsub(channel(analysis_id)) == [(channel(analysis_id).encode(), 0)]
