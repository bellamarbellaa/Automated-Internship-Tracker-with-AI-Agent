from tools.role_queries import ROLE_QUERIES


def test_role_queries_covers_exactly_the_three_roles():
    assert set(ROLE_QUERIES.keys()) == {"Business Analyst", "Data Analyst", "Consultant"}


def test_role_queries_each_role_has_nonempty_query_list():
    for role, queries in ROLE_QUERIES.items():
        assert isinstance(queries, list)
        assert len(queries) > 0
        assert all(isinstance(q, str) and q for q in queries)
