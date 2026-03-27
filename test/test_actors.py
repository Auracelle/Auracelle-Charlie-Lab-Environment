"""
tests/test_actors.py — Unit tests for engine/actors.py and config/actors.yaml

Run: pytest tests/test_actors.py -v
"""
import pytest

from engine.actors import (
    load_actor_profiles,
    get_actor_names,
    get_iso3_map,
    build_rl_actor_profiles,
)


class TestLoadActorProfiles:
    def test_returns_dict(self):
        profiles = load_actor_profiles()
        assert isinstance(profiles, dict)

    def test_expected_actor_count(self):
        profiles = load_actor_profiles()
        assert len(profiles) == 13, f"Expected 13 actors, got {len(profiles)}"

    def test_required_keys_present(self):
        profiles = load_actor_profiles()
        required = {"gdp", "influence", "position", "mil_exp", "internet", "cultural_alignment"}
        for name, data in profiles.items():
            missing = required - set(data.keys())
            assert not missing, f"Actor '{name}' missing keys: {missing}"

    def test_influence_in_unit_interval(self):
        for name, data in load_actor_profiles().items():
            inf = float(data["influence"])
            assert 0.0 <= inf <= 1.0, f"Actor '{name}' influence {inf} out of [0, 1]"

    def test_gdp_positive(self):
        for name, data in load_actor_profiles().items():
            assert float(data["gdp"]) >= 0.0, f"Actor '{name}' has negative GDP"


class TestGetActorNames:
    def test_returns_list_of_strings(self):
        names = get_actor_names()
        assert isinstance(names, list)
        assert all(isinstance(n, str) for n in names)

    def test_count_matches_profiles(self):
        assert len(get_actor_names()) == len(load_actor_profiles())

    def test_is_sorted(self):
        names = get_actor_names()
        assert names == sorted(names)


class TestGetISO3Map:
    def test_returns_dict(self):
        iso_map = get_iso3_map()
        assert isinstance(iso_map, dict)

    def test_nato_excluded(self):
        # NATO has null iso3 in YAML
        iso_map = get_iso3_map()
        assert "NATO" not in iso_map

    def test_usa_present(self):
        iso_map = get_iso3_map()
        assert "United States" in iso_map
        assert iso_map["United States"] == "USA"

    def test_all_values_are_3_chars(self):
        for actor, iso3 in get_iso3_map().items():
            assert len(iso3) == 3, f"ISO3 for {actor} is '{iso3}' (not 3 chars)"


class TestBuildRLActorProfiles:
    def test_returns_dict(self):
        profiles = build_rl_actor_profiles(["United States", "China"])
        assert isinstance(profiles, dict)

    def test_contains_requested_actors(self):
        requested = ["United States", "China", "India"]
        profiles = build_rl_actor_profiles(requested)
        assert set(profiles.keys()) == set(requested)

    def test_required_rl_keys(self):
        profiles = build_rl_actor_profiles(["United States"])
        p = profiles["United States"]
        for k in ("centrality", "institutional_capacity"):
            assert k in p, f"Missing RL key: {k}"

    def test_unknown_actor_gets_defaults(self):
        profiles = build_rl_actor_profiles(["NonexistentActor"])
        p = profiles["NonexistentActor"]
        assert p["centrality"] == 0.5
        assert p["institutional_capacity"] == 0.55

    def test_centrality_in_unit_interval(self):
        profiles = build_rl_actor_profiles(get_actor_names())
        for name, p in profiles.items():
            c = float(p["centrality"])
            assert 0.0 <= c <= 1.0, f"Centrality for {name} = {c} out of [0, 1]"
