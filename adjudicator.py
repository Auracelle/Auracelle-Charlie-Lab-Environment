import random
import numpy as np
from datetime import datetime
import sys
sys.path.insert(0, ".")

class AgenticAdjudicator:
    """AI Agentic Adjudicator - Neutral referee with real-world data integration"""

    def __init__(self, mode="neutral"):
        self.mode = mode
        self.event_history = []
        self.tension_index = 0.5
        self.shock_types = [
            "economic_sanctions", "cyber_attack", "public_protest",
            "un_resolution", "trade_disruption", "diplomatic_incident",
            "tech_breakthrough", "alliance_shift", "intel_leak"
        ]
        self.real_world_data = {}

    def integrate_real_world_data(self, country_code, gdp=None, mil_exp=None, internet=None, sanctions=None):
        """Store real-world data for adjudication calculations"""
        self.real_world_data[country_code] = {
            'gdp': gdp,
            'military_expenditure_pct': mil_exp,
            'internet_penetration': internet,
            'sanctioned_entities': sanctions
        }

    def calculate_tension_index(self, actor_positions, power_levels, alignment_graph):
        """Calculate geopolitical tension with real-world data weighting"""
        position_divergence = np.std([hash(p) % 100 for p in actor_positions.values()]) / 100
        power_imbalance = np.std(list(power_levels.values()))
        alignment_factor = 1.0 - (sum(alignment_graph.values()) / (len(alignment_graph) + 1e-6))

        # Add real-world military expenditure factor
        mil_exp_factor = 0.0
        if self.real_world_data:
            mil_exps = [d.get('military_expenditure_pct', 2.0) for d in self.real_world_data.values() if d.get('military_expenditure_pct')]
            if mil_exps:
                mil_exp_factor = (np.mean(mil_exps) - 2.0) / 10.0  # Normalize around 2% baseline

        tension = (position_divergence * 0.3 + power_imbalance * 0.2 + alignment_factor * 0.3 + abs(mil_exp_factor) * 0.2)
        self.tension_index = max(0.0, min(1.0, tension))
        return self.tension_index

    def detect_deception(self, stated_position, historical_actions, power_level):
        """Detect potential deception in actor statements"""
        deception_score = 0.0

        if len(historical_actions) > 0:
            consistency = sum([1 for a in historical_actions if a == stated_position]) / len(historical_actions)
            deception_score += (1.0 - consistency) * 0.5

        if power_level < 0.5 and "aggressive" in stated_position.lower():
            deception_score += 0.3

        return min(1.0, deception_score)

    def inject_shock(self, current_round, tension_level):
        """Inject external shock event based on tension and real-world factors"""
        # Increase shock probability if sanctions are detected
        sanctions_multiplier = 1.0
        if self.real_world_data:
            # Handle None values properly when summing sanctions
            total_sanctions = sum([d.get('sanctioned_entities', 0) for d in self.real_world_data.values() if d.get('sanctioned_entities') is not None])
            if total_sanctions > 0:
                sanctions_multiplier = 1.3

        shock_probability = tension_level * 0.3 * sanctions_multiplier

        if random.random() < shock_probability:
            shock_type = random.choice(self.shock_types)
            impact_magnitude = random.uniform(0.1, 0.5) * tension_level

            event = {
                "round": current_round,
                "type": shock_type,
                "magnitude": impact_magnitude,
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "narrative": self._generate_narrative(shock_type, impact_magnitude),
                "real_world_triggered": sanctions_multiplier > 1.0
            }

            self.event_history.append(event)
            return event

        return None

    def _generate_narrative(self, shock_type, magnitude):
        """Generate narrative text for shock events"""
        severity = "severe" if magnitude > 0.3 else "moderate"
        narratives = {
            "economic_sanctions": f"Breaking: Coalition imposes {severity} economic sanctions",
            "cyber_attack": f"Alert: {severity.capitalize()} cyber incident targets critical infrastructure",
            "public_protest": f"Developing: {severity.capitalize()} public demonstrations challenge policy",
            "un_resolution": f"UN Security Council debates {severity} resolution",
            "trade_disruption": f"Economic shock: {severity.capitalize()} trade route disruption",
            "diplomatic_incident": f"Diplomatic crisis: {severity.capitalize()} incident strains relations",
            "tech_breakthrough": f"Tech update: {severity.capitalize()} AI capability announced",
            "alliance_shift": f"Geopolitical shift: {severity.capitalize()} realignment detected",
            "intel_leak": f"Intelligence alert: {severity.capitalize()} data leak exposed"
        }
        return narratives.get(shock_type, "Unknown event occurred")

    def adjudicate(self, actor_beliefs, power_levels, alignment_graph, current_round):
        """Main adjudication function with real-world data integration"""
        tension = self.calculate_tension_index(actor_beliefs, power_levels, alignment_graph)
        shock_event = self.inject_shock(current_round, tension)

        confidence = 1.0 - (tension * 0.3)

        deception_scores = {}
        for actor, belief in actor_beliefs.items():
            hist = [e.get(actor) for e in self.event_history if actor in e]
            deception_scores[actor] = self.detect_deception(belief, hist, power_levels.get(actor, 0.5))

        return {
            "tension_index": tension,
            "shock_event": shock_event,
            "confidence_score": confidence,
            "deception_scores": deception_scores,
            "narrative": shock_event["narrative"] if shock_event else "Situation stable",
            "round": current_round,
            "real_world_integrated": len(self.real_world_data) > 0
        }
