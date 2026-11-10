"""Synthetic semantic decisions test bookkeeping, never model accuracy."""
import copy
from datetime import timezone, timedelta
import unittest
from data import InputRecord, InputData, INPUT_FILES, build_windows
from reasoning import (resolve_organisations, resolve_entities, resolve_goals,
                       rank_goals, extract_windows, ReasoningError)
from test_reasoning import fixture, observation, FakeClient


def extracted(obs):
    return {"state": "succeeded", "required": ["w"], "completed": ["w"],
            "failures": [], "observations": obs}


def obs(kind, identifier):
    return dict(observation(), kind=kind, id=identifier, windows=["w"])


class ResolutionTests(unittest.TestCase):
    def test_review_independent_identical_wording_and_duplicate_windows(self):
        self.data.messages_by_id["M1"].timestamp = 86401
        a, group = self.goal("a", role="pursuit")
        b, other = self.goal("b", "M1", "pursuit")
        group["members"] = ["a", "b"]
        group["support"] += other["support"]
        observations = {"a": a, "b": b}
        baseline = rank_goals(self.data, [group], observations, timezone.utc)
        self.assertEqual(baseline["ranking"][0]["rank"][:3], (-2, -2, -86401))
        self.assertEqual(baseline["items"][0]["evidence"], ["M0", "M1"])
        group["support"] += copy.deepcopy(group["support"])
        group["support"].reverse()
        self.assertEqual(rank_goals(self.data, [group], observations, timezone.utc), baseline)
        group["support"] = group["support"][:2]
        for support in group["support"]:
            if support["span"]["message_id"] == "M1":
                support["role"] = "copy"
        self.assertEqual(rank_goals(self.data, [group], observations, timezone.utc)["items"], [])

    def test_review_undated_unused_evidence_does_not_affect_tie_break(self):
        a, group = self.goal()
        b, other = self.goal("b", "M1", "mention")
        self.data.messages_by_id["M1"].timestamp = None
        baseline = rank_goals(self.data, [group], {"g": a}, timezone.utc)
        group["members"].append("b")
        group["support"] += other["support"]
        result = rank_goals(self.data, [group], {"g": a, "b": b}, timezone.utc)
        self.assertEqual(result["ranking"][0]["rank"], baseline["ranking"][0]["rank"])
        group["members"].reverse()
        group["support"].reverse()
        self.assertEqual(rank_goals(self.data, [group], {"b": b, "g": a}, timezone.utc), result)

    def test_review_undated_positive_support_fails_without_guessing(self):
        candidate, group = self.goal()
        self.data.messages_by_id["M0"].timestamp = None
        with self.assertRaisesRegex(ReasoningError, "Undated goal support"):
            rank_goals(self.data, [group], {"g": candidate}, timezone.utc)
        reply = {"groups": [group], "pending": [], "rejected": []}
        self.assertEqual(resolve_goals(self.data, extracted([candidate]), FakeClient([reply]))["state"], "incomplete")
        self.assertIsNone(self.data.messages_by_id["M0"].timestamp)

    def test_review_rejection_vocabularies_are_category_specific(self):
        candidate, _ = self.goal()
        reply = {"groups": [], "pending": [], "rejected": [{"id": "g", "reason": "not_organisation"}]}
        result = resolve_goals(self.data, extracted([candidate]), FakeClient([reply]))
        self.assertEqual(result["state"], "incomplete")
        self.assertEqual(result["pending"], ["g"])
        for reason in ("promotion", "ordinary_task", "other_person", "not_organisation", "insufficient_evidence"):
            with self.subTest(reason=reason):
                reply["rejected"][0]["reason"] = reason
                result = resolve_organisations(self.data, extracted([obs("organisation", "g")]), FakeClient([reply]))
                self.assertEqual(result["state"], "succeeded_empty" if reason in
                                 ("not_organisation", "insufficient_evidence") else "incomplete")

    def test_review_me_attribution_cannot_supply_tier_one(self):
        a, group = self.goal(role="corroboration")
        observations = {"g": a}
        for index in range(2):
            mid = "A" + str(index)
            source = dict(self.data.messages_by_id["M0"].original, id=mid, body="Attributed " + mid)
            self.data.messages_by_id[mid] = InputRecord("messages.jsonl", index, b"", source, True, 10 + index)
            candidate, other = self.goal(mid, mid, "attribution")
            observations[mid] = candidate
            group["members"].append(mid)
            group["support"] += other["support"]
        with self.assertRaisesRegex(ReasoningError, "Attribution must originate"):
            rank_goals(self.data, [group], observations, timezone.utc)
        for mid in ("A0", "A1"):
            self.data.messages_by_id[mid].original["sender_id"] = "P1"
        self.assertEqual(rank_goals(self.data, [group], observations, timezone.utc)["ranking"][0]["rank"][0], -1)
        group["support"] = group["support"][1:]
        self.assertEqual(rank_goals(self.data, [group], observations, timezone.utc)["items"], [])

    def setUp(self):
        self.data, self.plan = fixture()

    def org_group(self, members):
        return {"members": members, "record": {"name": "Walk", "type": "company",
                "side": "work", "role": "owner"},
                "aliases": [{"name": "Walk", "evidence": members}]}

    def orgs(self, groups):
        return resolve_organisations(self.data, extracted([obs("organisation", "a"), obs("organisation", "b")]),
                                    FakeClient([{"groups": groups, "pending": [], "rejected": []}]))

    def test_alias_merge_and_shared_participant_distinction(self):
        merged = self.orgs([self.org_group(["a", "b"])])
        self.assertEqual(merged["state"], "succeeded")
        self.assertEqual(len(merged["items"]), 1)
        separate = self.orgs([self.org_group(["a"]), self.org_group(["b"])])
        self.assertEqual(len(separate["items"]), 2)
        self.assertEqual(len(set(o["id"] for o in separate["items"])), 2)

    def test_alias_fabrication_and_omitted_candidates_fail(self):
        group = self.org_group(["a", "b"])
        group["aliases"][0]["name"] = "Invented"
        self.assertEqual(self.orgs([group])["state"], "incomplete")
        self.assertEqual(self.orgs([self.org_group(["a"])])["state"], "incomplete")

    def entity_reply(self):
        return {"decisions": [
            {"category": "people", "id": "P1", "record": {"id": "P1", "circle": "child"}, "evidence": ["p"]},
            {"category": "chats", "id": "C1", "record": {"chat_id": "C1", "person": "P1"}, "evidence": ["p"]}]}

    def entities(self, replies, **kwargs):
        return resolve_entities(self.data, extracted([obs("person", "p")]),
                                {"state": "succeeded_empty", "items": []}, FakeClient(replies), **kwargs)

    def test_seed_circle_group_to_person_and_consistent_multiple_chats(self):
        self.data.seed = {"circles": {"P1": "child"}}
        self.data.chats_by_id["C1"].original["is_group"] = True
        second = copy.deepcopy(self.data.chat_records[0])
        second.original["chat_id"] = "C2"
        self.data.chat_records.append(second)
        self.data.chats_by_id["C2"] = second
        reply = self.entity_reply()
        reply["decisions"].append({"category": "chats", "id": "C2", "record": {"chat_id": "C2", "person": "P1"}, "evidence": ["p"]})
        result = self.entities([reply])
        self.assertEqual(result["state"], "succeeded")
        self.assertEqual(len(result["people"]), 1)
        self.assertEqual(len(result["chats"]), 2)
        reply["decisions"][0]["record"]["circle"] = "friend"
        self.assertEqual(self.entities([reply])["state"], "incomplete")

    def test_partial_failed_and_pending_entity_batches(self):
        reply = self.entity_reply()
        self.assertEqual(self.entities([{"decisions": reply["decisions"][:1]}])["state"], "incomplete")
        result = self.entities([{"decisions": reply["decisions"][:1]}, TimeoutError()], batch_size=1)
        self.assertEqual(result["completed_batches"], ["0"])
        self.assertEqual(result["required_batches"], ["0", "1"])
        self.assertEqual(result["pending"], [("chats", "C1")])
        reply["decisions"][0]["record"] = None
        self.assertEqual(self.entities([reply])["state"], "incomplete")

    def goal(self, identifier="g", mid="M0", role="explicit"):
        span = {"message_id": mid, "start": 0, "end": len(self.data.messages_by_id[mid].original["body"]),
                "text": self.data.messages_by_id[mid].original["body"]}
        candidate = dict(obs("goal", identifier), evidence=[span])
        group = {"members": [identifier], "record": {"title": identifier, "area": "health", "type": "habit", "horizon": "1yr"},
                 "support": [{"span": span, "role": role, "episode": mid, "antecedent": None}]}
        return candidate, group

    def test_exact_top_ten_and_permutation(self):
        observations, groups = {}, []
        for i in range(12):
            mid = "S%02d" % i
            source = dict(self.data.messages_by_id["M0"].original, id=mid, body="Intention " + str(i), ts=100 + i)
            self.data.messages_by_id[mid] = InputRecord("messages.jsonl", i, b"", source, True, 100 + i)
            candidate, group = self.goal(mid, mid)
            observations[mid] = candidate
            groups.append(group)
        first = rank_goals(self.data, groups, observations, timezone.utc)
        other = rank_goals(self.data, list(reversed(groups)), observations, timezone.utc)
        self.assertEqual(first["items"], other["items"])
        self.assertEqual([g["title"] for g in first["items"]], ["S%02d" % i for i in range(11, 1, -1)])

    def test_goal_rejections_pending_and_failed_search(self):
        candidate, group = self.goal()
        for reason in ("promotion", "ordinary_task", "other_person", "insufficient_evidence"):
            result = resolve_goals(self.data, extracted([candidate]), FakeClient([
                {"groups": [], "pending": [], "rejected": [{"id": "g", "reason": reason}]}]))
            self.assertEqual(result["state"], "succeeded_empty")
        for reply in (TimeoutError(), {"groups": [], "pending": ["g"], "rejected": []}):
            self.assertEqual(resolve_goals(self.data, extracted([candidate]), FakeClient([reply]))["state"], "incomplete")

    def test_distinct_same_area_goals_and_semantic_merge(self):
        a, ga = self.goal("a")
        b, gb = self.goal("b", "M1")
        result = rank_goals(self.data, [ga, gb], {"a": a, "b": b}, timezone.utc)
        self.assertEqual(len(result["items"]), 2)
        ga["members"] = ["a", "b"]
        ga["support"] += gb["support"]
        result = rank_goals(self.data, [ga], {"a": a, "b": b}, timezone.utc)
        self.assertEqual(len(result["items"]), 1)

    def test_timezone_pursuit_tier_and_explicit_precedence(self):
        self.data.messages_by_id["M0"].timestamp = 3600
        self.data.messages_by_id["M1"].timestamp = 80000
        self.data.messages_by_id["M1"].original["body"] = "Another practice"
        a, ga = self.goal("a", role="pursuit")
        b, gb = self.goal("b", "M1", "pursuit")
        ga["members"] += ["b"]
        ga["support"] += gb["support"]
        observations = {"a": a, "b": b}
        self.assertEqual(rank_goals(self.data, [ga], observations, timezone.utc)["items"], [])
        ranked = rank_goals(self.data, [ga], observations, timezone(timedelta(hours=5, minutes=30)))
        self.assertEqual(ranked["ranking"][0]["rank"][0], -2)
        ga["support"][0]["role"] = "explicit"
        self.assertEqual(rank_goals(self.data, [ga], observations, timezone.utc)["ranking"][0]["rank"][0], -3)

    def test_adoption_requires_both_messages_and_copies_do_not_refresh(self):
        a, group = self.goal(role="adoption")
        with self.assertRaises(ReasoningError):
            rank_goals(self.data, [group], {"g": a}, timezone.utc)
        b, gb = self.goal("b", "M1")
        group = gb
        group["members"] = ["g", "b"]
        group["support"][0].update(role="adoption", antecedent="M0")
        result = rank_goals(self.data, [group], {"g": a, "b": b}, timezone.utc)
        self.assertEqual(result["items"][0]["evidence"], ["M0", "M1"])
        group["support"][0]["role"] = "copy"
        self.assertEqual(rank_goals(self.data, [group], {"g": a, "b": b}, timezone.utc)["items"], [])

    def test_empty_input_and_long_message_spans(self):
        empty = InputData(seed={}, files_read_complete={n: True for n in INPUT_FILES})
        result = extract_windows(empty, build_windows(empty), FakeClient([]))
        self.assertEqual(result["state"], "succeeded_empty")
        self.assertEqual(resolve_entities(empty, result, {"state": "succeeded_empty", "items": []}, FakeClient([]))["state"], "succeeded_empty")
        from dataclasses import asdict
        plan = build_windows(self.data, max_primary_chars=3)
        replies = [{"covered": [asdict(s) for s in w.primary], "observations": []} for w in plan.windows]
        result = extract_windows(self.data, plan, FakeClient(replies))
        self.assertEqual(result["completed"], result["required"])

    def test_oversized_packet_and_incomplete_prerequisite(self):
        self.assertEqual(self.entities([], max_packet_bytes=1)["state"], "incomplete")
        extraction = extracted([])
        extraction["state"] = "incomplete"
        self.assertEqual(resolve_goals(self.data, extraction, FakeClient([]))["state"], "incomplete")

    def test_relationship_links_require_existing_targets_and_evidence(self):
        reply = self.entity_reply()
        reply["decisions"][0]["record"]["looks_after"] = ["ME"]
        self.assertEqual(self.entities([reply])["state"], "succeeded")
        reply["decisions"][0]["record"]["links"] = [{"organisation": "invented", "link": "supports"}]
        self.assertEqual(self.entities([reply])["state"], "incomplete")

    def test_indirect_tier_requires_two_episodes_and_me_corroboration(self):
        a, group = self.goal(role="corroboration")
        observations = {"g": a}
        for index in range(2):
            mid = "T" + str(index)
            source = dict(self.data.messages_by_id["M0"].original, id=mid, sender_id="P1", body="Attribution " + mid)
            self.data.messages_by_id[mid] = InputRecord("messages.jsonl", index, b"", source, True, 10 + index)
            candidate, extra = self.goal(mid, mid, "attribution")
            observations[mid] = candidate
            group["members"].append(mid)
            group["support"] += extra["support"]
        result = rank_goals(self.data, [group], observations, timezone.utc)
        self.assertEqual(result["ranking"][0]["rank"][0], -1)
        group["support"] = group["support"][1:]
        self.assertEqual(rank_goals(self.data, [group], observations, timezone.utc)["items"], [])

    def test_ties_use_stable_title_and_duplicate_keys_rejected(self):
        a, ga = self.goal("a")
        b, gb = self.goal("b")
        ga["record"]["title"] = "Z"
        gb["record"]["title"] = "A"
        observations = {"a": a, "b": b}
        result = rank_goals(self.data, [ga, gb], observations, timezone.utc)
        self.assertEqual([g["title"] for g in result["items"]], ["A", "Z"])
        ga["record"]["title"] = "A"
        with self.assertRaises(ReasoningError):
            rank_goals(self.data, [ga, gb], observations, timezone.utc)

    def test_successful_goal_resolution_and_unknown_evidence_rejection(self):
        candidate, group = self.goal()
        reply = {"groups": [group], "pending": [], "rejected": []}
        self.assertEqual(resolve_goals(self.data, extracted([candidate]), FakeClient([reply]))["state"], "succeeded")
        group["support"][0]["span"]["message_id"] = "invented"
        self.assertEqual(resolve_goals(self.data, extracted([candidate]), FakeClient([reply]))["state"], "incomplete")
