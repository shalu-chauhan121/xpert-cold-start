"""Synthetic bounded entity coverage and merge regressions."""
import copy
import json
import unittest

import reasoning
from test_reasoning import fixture
from test_reasoning_resolution import extracted, obs


class EntityClient:
    def __init__(self, change=None):
        self.packets = []
        self.change = change

    def request(self, messages, **settings):
        packet = json.loads(messages[1]['content'])
        self.packets.append(packet)
        rows = []
        for category, identifier in packet['required']:
            record = ({'id': identifier, 'circle': 'child'} if category == 'people'
                      else {'chat_id': identifier, 'person': 'P1'})
            rows.append({'category': category, 'id': identifier, 'record': record,
                         'evidence': [o['id'] for o in packet['observations']]})
        if self.change:
            self.change(rows, len(self.packets))
        text = json.dumps({'decisions': rows})
        settings['validate'](text)
        return text


class EntityPartitionTests(unittest.TestCase):
    def setUp(self):
        self.data, _ = fixture()
        self.organisations = {'state': 'succeeded_empty', 'items': []}
        self.observations = []
        for i in range(50):
            item = obs('person', 'o%03d' % i)
            item['meaning'] = 'Synthetic ' + str(i) + 'x' * 300
            item['windows'] = ['window-a', 'window-b']
            self.observations.append(item)

    def resolve(self, client, observations=None, limit=6000):
        return reasoning.resolve_entities(self.data, extracted(self.observations if observations is None else observations),
            self.organisations, client, max_packet_bytes=limit)

    def test_bounded_complete_coverage_and_local_provenance(self):
        before = copy.deepcopy(self.observations)
        client = EntityClient()
        result = self.resolve(client)
        self.assertEqual(result['state'], 'succeeded')
        self.assertGreater(len(client.packets), 1)
        self.assertTrue(all(len(reasoning._encoded(p)) <= 6000 for p in client.packets))
        ids = [o['id'] for p in client.packets for o in p['observations']]
        self.assertEqual(sorted(ids), sorted(o['id'] for o in before))
        self.assertEqual(result['evidence_registry'], {o['id']: o for o in before})
        self.assertEqual(result['required_batches'], result['completed_batches'])
        self.assertEqual(result['provenance']['people:P1'], sorted(ids))
        self.assertEqual(before, self.observations)
        for packet in client.packets:
            for item in packet['observations']:
                self.assertEqual(item['evidence'], result['evidence_registry'][item['id']]['evidence'])
                self.assertNotIn('windows', item)

    def test_deterministic_reversed_observations_and_replies(self):
        first = EntityClient()
        a = self.resolve(first)
        def reverse(rows, index):
            rows.reverse()
            for row in rows:
                row['evidence'].reverse()
        second = EntityClient(reverse)
        b = self.resolve(second, list(reversed(self.observations)))
        self.assertEqual(a['state'], 'succeeded')
        self.assertEqual(a, b)
        self.assertEqual(first.packets, second.packets)

    def test_conflict_remains_pending_not_last_wins(self):
        def conflict(rows, index):
            if index == 2:
                rows[0]['record']['circle'] = 'friend'
        result = self.resolve(EntityClient(conflict))
        self.assertEqual(result['state'], 'incomplete')
        self.assertIn(('people', 'P1'), result['pending'])
        self.assertTrue(result['conflicts'])
        self.assertEqual(result['people'], [])

    def test_missing_middle_partition_and_foreign_citation(self):
        for mode in ('missing', 'citation', 'timeout', 'pending'):
            def change(rows, index):
                if index == 2:
                    if mode == 'missing': rows.pop()
                    if mode == 'citation': rows[0]['evidence'] = ['o000']
                    if mode == 'timeout': raise TimeoutError()
                    if mode == 'pending': rows[0]['record'] = None
            client = EntityClient(change)
            result = self.resolve(client)
            self.assertGreater(len(client.packets), 2)
            self.assertEqual(result['state'], 'incomplete', mode)
            self.assertTrue(result['pending'], mode)

    def test_indivisible_oversize_has_no_dispatch(self):
        self.observations[0]['meaning'] = 'x' * 100000
        client = EntityClient()
        result = self.resolve(client)
        self.assertEqual(result['state'], 'incomplete')
        self.assertEqual(client.packets, [])

    def test_no_contribution_is_distinct_from_pending(self):
        def empty(rows, index):
            if index == 2:
                for row in rows:
                    row['record'] = {}
                    row['evidence'] = []
        result = self.resolve(EntityClient(empty))
        self.assertEqual(result['state'], 'succeeded')

    def test_undated_span_order_and_independent_ids(self):
        self.data.messages_by_id['M0'].timestamp = None
        dated = copy.deepcopy(self.observations[0])
        dated['id'] = 'dated'
        dated['evidence'][0]['message_id'] = 'M1'
        client = EntityClient()
        result = self.resolve(client, [self.observations[0], dated])
        self.assertEqual(result['state'], 'succeeded')
        self.assertEqual([o['id'] for p in client.packets for o in p['observations']], ['dated', 'o000'])

    def test_compatible_relationships_and_cross_chat_consistency(self):
        second = copy.deepcopy(self.data.chat_records[0])
        second.original['chat_id'] = 'C2'
        self.data.chat_records.append(second)
        self.data.chats_by_id['C2'] = second
        self.data.seed = {'circles': {'P1': 'child'}}
        self.organisations = {'state': 'succeeded', 'items': [{'id': 'A'}, {'id': 'B'}]}
        def relationships(rows, index):
            rows[0]['record']['links'] = [{'organisation': 'A' if index % 2 else 'B', 'link': 'supports'}]
        result = self.resolve(EntityClient(relationships))
        self.assertEqual(result['state'], 'succeeded')
        self.assertEqual(len(result['people']), 1)
        self.assertEqual(result['people'][0]['links'], [
            {'organisation': 'A', 'link': 'supports'}, {'organisation': 'B', 'link': 'supports'}])
        self.assertEqual([c['person'] for c in result['chats']], ['P1', 'P1'])
        for partition in result['partitions'].values():
            self.assertEqual(len(partition['targets']), 3)

    def test_seed_and_link_conflicts_never_overwrite(self):
        self.data.seed = {'circles': {'P1': 'child'}}
        def change_seed(rows, index):
            if index == 2:
                rows[0]['record']['circle'] = 'friend'
        self.assertEqual(self.resolve(EntityClient(change_seed))['state'], 'incomplete')
        self.organisations = {'state': 'succeeded', 'items': [{'id': 'A'}]}
        def links(rows, index):
            rows[0]['record']['links'] = [{'organisation': 'A', 'link': 'runs' if index == 2 else 'supports'}]
        result = self.resolve(EntityClient(links))
        self.assertEqual(result['people'], [])
        self.assertEqual(result['conflicts'], ['people:P1'])

    def test_long_message_spans_are_not_expanded_to_full_bodies(self):
        record = self.data.messages_by_id['M0']
        record.original['body'] = 'a' * 150000
        for index, item in enumerate(self.observations):
            item['evidence'] = [{'message_id': 'M0', 'start': index * 100,
                                 'end': (index + 1) * 100, 'text': 'a' * 100}]
        client = EntityClient()
        result = self.resolve(client)
        self.assertEqual(result['state'], 'succeeded')
        self.assertEqual(result['evidence_registry'], {o['id']: o for o in self.observations})
        self.assertNotIn('a' * 1000, json.dumps(client.packets))

    def test_client_budget_deadline_and_retry_safeguards(self):
        import os
        from unittest.mock import patch
        from llm import Client, Budget, Deadline
        from test_llm import Clock, response
        env = {'LLM_BASE_URL': 'https://synthetic.invalid', 'LLM_API_KEY': 'synthetic', 'LLM_MODEL': 'synthetic'}
        for mode in ('budget', 'deadline', 'retry'):
            clock = Clock()
            count = []
            mock = EntityClient()
            def transport(endpoint, wire, key, timeout):
                count.append(1)
                if mode == 'retry':
                    return 503, {}, b'{}'
                body = json.loads(wire)
                answer = mock.request(body['messages'], validate=lambda text: None)
                if mode == 'deadline':
                    clock.now = 1620
                return response(answer)
            budget = Budget(planned_base_calls=1 if mode == 'budget' else 20)
            client = Client(transport=transport, clock=clock, sleep=clock.sleep,
                            deadline=Deadline(clock), budget=budget)
            with patch.dict(os.environ, env):
                result = self.resolve(client)
            self.assertEqual(result['state'], 'incomplete', mode)
            self.assertTrue(result['pending'])
            if mode != 'retry':
                self.assertEqual(len(count), 1)
            self.assertTrue(all(n <= 3 for n in budget.jobs.values()))
            self.assertLessEqual(budget.recoveries, budget.recovery_limit)

    def test_partition_failure_preserves_pipeline_output(self):
        from unittest.mock import patch
        import reasoning
        import test_solution
        fixture = test_solution.IntegrationTests()
        fixture.setUp()
        try:
            original = reasoning.resolve_entities
            def small_partition(data, extraction, organisations, client):
                return original(data, extraction, organisations, client, max_packet_bytes=1)
            with patch.object(reasoning, 'resolve_entities', side_effect=small_partition):
                status, summary = fixture.run_pipeline(test_solution.PipelineTransport())
            self.assertEqual(status, 1)
            self.assertEqual(summary['state'], 'incomplete')
            self.assertEqual(fixture.output.read_text(), 'old output')
        finally:
            fixture.doCleanups()

    def test_failed_second_partition_preserves_pipeline_output(self):
        from unittest.mock import patch
        import test_solution
        fixture = test_solution.IntegrationTests()
        fixture.setUp()
        class Transport(test_solution.PipelineTransport):
            entity_calls = 0
            def __call__(self, endpoint, wire, key, timeout):
                packet = json.loads(json.loads(wire)['messages'][1]['content'])
                if 'entity-3' in packet.get('contract', ''):
                    self.entity_calls += 1
                    if self.entity_calls == 2:
                        return 200, {}, b'{}'
                return super().__call__(endpoint, wire, key, timeout)
        try:
            original = reasoning.resolve_entities
            def small_partition(data, extraction, organisations, client):
                return original(data, extraction, organisations, client, max_packet_bytes=6000)
            transport = Transport()
            with patch.object(reasoning, 'resolve_entities', side_effect=small_partition):
                status, summary = fixture.run_pipeline(transport)
            self.assertGreaterEqual(transport.entity_calls, 2)
            self.assertEqual(status, 1)
            self.assertEqual(summary['state'], 'incomplete')
            self.assertEqual(fixture.output.read_text(), 'old output')
            entities = summary['stages']['entities']
            self.assertIn('0', entities['completed_batches'])
            self.assertNotEqual(entities['required_batches'], entities['completed_batches'])
        finally:
            fixture.doCleanups()


if __name__ == '__main__':
    unittest.main()
