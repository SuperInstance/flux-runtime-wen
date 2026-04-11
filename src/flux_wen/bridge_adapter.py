"""
FLUX-WEN Bridge Adapter — 文境/易經 Bridge Adapter

Exposes the Classical Chinese context system (文境) and I Ching
hexagram/trigram encoding to the A2A type-safe cross-language bridge.

Classical Chinese is the ultimate context-dependent language:
以文意定義 — meaning determined by textual intent.
同字異義 — same character, different meaning, by context.

The adapter maps:
  - 8 context domains (六域 + extras) → universal scoping levels
  - 8 trigrams (八卦) → universal execution patterns
  - Context depth → universal nesting levels

Interface:
    adapter = WenBridgeAdapter()
    types = adapter.export_types()
    local = adapter.import_type(universal)
    cost = adapter.bridge_cost("zho")
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from flux_wen.context import ContextDomain, ContextStack, ContextFrame
from flux_wen.iching import Trigram, _TRIGRAM_NATURE, HEXAGRAMS_KING_WEN


# ══════════════════════════════════════════════════════════════════════
# Common bridge types
# ══════════════════════════════════════════════════════════════════════

@dataclass
class BridgeCost:
    numeric_cost: float
    information_loss: list[str] = field(default_factory=list)
    ambiguity_warnings: list[str] = field(default_factory=list)


@dataclass
class UniversalType:
    paradigm: str
    category: str
    constraints: dict[str, Any] = field(default_factory=dict)
    confidence: float = 1.0


class BridgeAdapter(ABC):
    @abstractmethod
    def export_types(self) -> list[UniversalType]: ...

    @abstractmethod
    def import_type(self, universal: UniversalType) -> Any: ...

    @abstractmethod
    def bridge_cost(self, target_lang: str) -> BridgeCost: ...


# ══════════════════════════════════════════════════════════════════════
# WenTypeSignature — Classical Chinese type representation
# ══════════════════════════════════════════════════════════════════════

@dataclass
class WenTypeSignature:
    """Represents a Classical Chinese type for bridge export/import.

    Classical Chinese meaning emerges entirely from context:
      - context_depth: nesting depth of interpretation context
      - context_domain: which knowledge domain is active (算/儒/兵/等)
      - glyph_category: what type of character operation this is
      - iching_trigram: which of the 8 trigrams guides execution
      - hexagram_address: which of the 64 hexagrams (0-63) this maps to

    Attributes:
        context_depth: depth of the context stack
        context_domain: active knowledge domain
        glyph_category: type of character operation
        iching_trigram: associated I Ching trigram
        hexagram_address: associated hexagram address (0-63)
        confidence: mapping confidence
    """
    context_depth: int = 0
    context_domain: ContextDomain = ContextDomain.GENERAL
    glyph_category: str = "neutral"
    iching_trigram: Trigram | None = None
    hexagram_address: int = 0
    confidence: float = 1.0

    @property
    def domain_char(self) -> str:
        return self.context_domain.value

    @property
    def trigram_name(self) -> str:
        if self.iching_trigram is None:
            return "None"
        return self.iching_trigram.chinese

    @property
    def trigram_nature(self) -> str:
        if self.iching_trigram is None:
            return "None"
        return _TRIGRAM_NATURE[self.iching_trigram]


# ══════════════════════════════════════════════════════════════════════
# Context Domain → Universal Scoping Level Mapping
# ══════════════════════════════════════════════════════════════════════

_DOMAIN_TO_UNIVERSAL: dict[ContextDomain, tuple[str, str, float]] = {
    ContextDomain.MATHEMATICS: ("Computation", "算 — arithmetic/calculation operations", 0.95),
    ContextDomain.CONFUCIAN:   ("Ethical",     "儒 — ethical/philosophical operations", 0.90),
    ContextDomain.MILITARY:    ("Strategic",   "兵 — strategic/competitive operations", 0.90),
    ContextDomain.GENERAL:     ("Default",     "常 — default/general purpose", 0.80),
    ContextDomain.AGENT:       ("Communicative", "使 — inter-agent communication", 0.95),
    ContextDomain.CONTROL:     ("Structural",  "制 — program flow control", 0.90),
    ContextDomain.PHILOSOPHY:  ("Ontological", "理 — philosophical/Daoist ontology", 0.85),
    ContextDomain.COMPUTING:   ("Algorithmic", "機 — algorithmic/data processing", 0.95),
}

# I Ching Trigram → Universal Execution Pattern Mapping
_TRIGRAM_TO_UNIVERSAL: dict[Trigram, tuple[str, str, float]] = {
    Trigram.QIAN: ("Pure",    "Heaven/天 — pure yang, sovereign execution", 0.95),
    Trigram.KUN:  ("Grounded","Earth/坤 — pure yin, receptive execution", 0.95),
    Trigram.KAN:  ("Flowing", "Water/坎 — flowing, adaptive execution", 0.90),
    Trigram.LI:   ("Radiant", "Fire/離 — radiant, illuminating execution", 0.90),
    Trigram.ZHEN: ("Arousing","Thunder/震 — arousing, sudden execution", 0.90),
    Trigram.XUN:  ("Gentle",  "Wind/巽 — gentle, penetrating execution", 0.90),
    Trigram.GEN:  ("Still",   "Mountain/艮 — still, stabilizing execution", 0.90),
    Trigram.DUI:  ("Joyous",  "Lake/兌 — joyous, converging execution", 0.90),
}

# Context depth → universal scoping
_DEPTH_TO_SCOPE: dict[int, str] = {
    0: "Root",
    1: "Frame",
    2: "Nested",
    3: "Deep",
    4: "Profound",
}

# Reverse maps
_UNIVERSAL_TO_DOMAIN: dict[str, ContextDomain] = {
    "Computation":  ContextDomain.MATHEMATICS,
    "Ethical":      ContextDomain.CONFUCIAN,
    "Strategic":    ContextDomain.MILITARY,
    "Default":      ContextDomain.GENERAL,
    "Communicative": ContextDomain.AGENT,
    "Structural":   ContextDomain.CONTROL,
    "Ontological":  ContextDomain.PHILOSOPHY,
    "Algorithmic":  ContextDomain.COMPUTING,
}

_UNIVERSAL_TO_TRIGRAM: dict[str, Trigram] = {
    "Pure":     Trigram.QIAN,
    "Grounded": Trigram.KUN,
    "Flowing":  Trigram.KAN,
    "Radiant":  Trigram.LI,
    "Arousing": Trigram.ZHEN,
    "Gentle":   Trigram.XUN,
    "Still":    Trigram.GEN,
    "Joyous":   Trigram.DUI,
}


# ══════════════════════════════════════════════════════════════════════
# Language affinity
# ══════════════════════════════════════════════════════════════════════

_LANG_AFFINITY: dict[str, dict[str, Any]] = {
    "wen": {"cost": 0.0, "loss": [], "ambiguity": []},
    "zho": {"cost": 0.20, "loss": ["Classical vs Simplified distinction",
            "Some domain nuances"],
            "ambiguity": ["Modern Chinese loses character-level polymorphism"]},
    "san": {"cost": 0.55, "loss": ["Context-dependent polymorphism",
            "All inflectional morphology differences"],
            "ambiguity": ["Sanskrit is heavily inflected — opposite of analytic Chinese"]},
    "lat": {"cost": 0.55, "loss": ["Context-dependent meaning",
            "All grammatical inflection"],
            "ambiguity": ["Latin grammar is synthetic — fundamentally different paradigm"]},
    "deu": {"cost": 0.50, "loss": ["Character polymorphism", "Context-only meaning"],
            "ambiguity": ["German uses inflection, Chinese uses context"]},
    "kor": {"cost": 0.45, "loss": ["Character polymorphism",
            "Domain-based dispatch"],
            "ambiguity": ["Korean has particles and honorifics — partial overlap"]},
}


# ══════════════════════════════════════════════════════════════════════
# WenBridgeAdapter
# ══════════════════════════════════════════════════════════════════════

class WenBridgeAdapter(BridgeAdapter):
    """Bridge adapter for Classical Chinese (文言) context/trigram system.

    Exports all 8 context domains and 8 I Ching trigrams as UniversalType
    instances for cross-language type-safe bridging.

    Usage:
        adapter = WenBridgeAdapter()
        types = adapter.export_types()
        cost = adapter.bridge_cost("zho")
    """

    PARADIGM = "wen"

    def export_types(self) -> list[UniversalType]:
        """Export all Classical Chinese context domains and trigrams.

        Returns:
            List of UniversalType covering:
            - 8 context domains (Computation, Ethical, Strategic, etc.)
            - 8 I Ching trigrams (Pure, Grounded, Flowing, etc.)
            - Context depth scoping levels
        """
        exported: list[UniversalType] = []

        # Export context domains
        for domain, (cat, desc, conf) in _DOMAIN_TO_UNIVERSAL.items():
            exported.append(UniversalType(
                paradigm=self.PARADIGM,
                category=cat,
                constraints={
                    "context_domain": domain.value,
                    "domain_char": domain.value,
                    "description": desc,
                    "type_kind": "context_domain",
                },
                confidence=conf,
            ))

        # Export I Ching trigrams
        for trigram, (cat, desc, conf) in _TRIGRAM_TO_UNIVERSAL.items():
            exported.append(UniversalType(
                paradigm=self.PARADIGM,
                category=cat,
                constraints={
                    "trigram": trigram.name,
                    "chinese": trigram.chinese,
                    "nature": _TRIGRAM_NATURE[trigram],
                    "binary": trigram.binary_str,
                    "description": desc,
                    "type_kind": "iching_trigram",
                },
                confidence=conf,
            ))

        # Export context depth scoping levels
        for depth, scope in _DEPTH_TO_SCOPE.items():
            exported.append(UniversalType(
                paradigm=self.PARADIGM,
                category="Scope",
                constraints={
                    "context_depth": depth,
                    "scope_level": scope,
                    "description": f"Context depth {depth} → {scope} scoping",
                    "type_kind": "context_depth",
                },
                confidence=0.8,
            ))

        return exported

    def import_type(self, universal: UniversalType) -> WenTypeSignature:
        """Import a universal type into the Classical Chinese context system.

        Args:
            universal: A UniversalType from another runtime

        Returns:
            WenTypeSignature with best-matching domain and trigram
        """
        category = universal.category
        constraints = universal.constraints

        # Resolve context domain
        domain = _UNIVERSAL_TO_DOMAIN.get(category)
        if domain is None and "context_domain" in constraints:
            for d in ContextDomain:
                if d.value == constraints["context_domain"]:
                    domain = d
                    break
        if domain is None:
            domain = ContextDomain.GENERAL

        # Resolve trigram
        trigram = _UNIVERSAL_TO_TRIGRAM.get(category)
        if trigram is None and "trigram" in constraints:
            for t in Trigram:
                if t.name == constraints["trigram"]:
                    trigram = t
                    break
        if trigram is None and "binary" in constraints:
            try:
                trigram = Trigram.from_binary(int(constraints["binary"], 2))
            except (ValueError, TypeError):
                pass

        # Determine glyph category from category
        glyph_category = "neutral"
        cat_lower = category.lower()
        if "computation" in cat_lower or "algorithmic" in cat_lower:
            glyph_category = "arithmetic"
        elif "ethical" in cat_lower or "ontological" in cat_lower:
            glyph_category = "philosophical"
        elif "strategic" in cat_lower:
            glyph_category = "military"
        elif "structural" in cat_lower:
            glyph_category = "control"
        elif "communicative" in cat_lower:
            glyph_category = "agent"

        # Context depth from constraints
        depth = 0
        if "context_depth" in constraints:
            depth = int(constraints["context_depth"])

        # Hexagram address from trigram
        hex_addr = 0
        if trigram is not None:
            hex_addr = trigram.value

        return WenTypeSignature(
            context_depth=depth,
            context_domain=domain,
            glyph_category=glyph_category,
            iching_trigram=trigram,
            hexagram_address=hex_addr,
            confidence=universal.confidence * 0.85,
        )

    def bridge_cost(self, target_lang: str) -> BridgeCost:
        """Estimate bridge cost to another runtime.

        Args:
            target_lang: Target language code

        Returns:
            BridgeCost with estimated difficulty
        """
        target = target_lang.lower().strip()

        if target == self.PARADIGM:
            return BridgeCost(numeric_cost=0.0)

        affinity = _LANG_AFFINITY.get(target, {
            "cost": 0.6,
            "loss": ["Context-dependent polymorphism", "Domain dispatch"],
            "ambiguity": ["Unknown target language"],
        })

        return BridgeCost(
            numeric_cost=affinity["cost"],
            information_loss=list(affinity["loss"]),
            ambiguity_warnings=list(affinity["ambiguity"]),
        )

    def resolve_context(self, char: str, domain: ContextDomain | None = None) -> WenTypeSignature:
        """Resolve a character in a given context domain.

        Args:
            char: A single Chinese character
            domain: Optional context domain (defaults to GENERAL)

        Returns:
            WenTypeSignature with resolved domain and associated trigram
        """
        if domain is None:
            domain = ContextDomain.GENERAL

        stack = ContextStack()
        stack.push(domain)
        opcode = stack.resolve(char)

        # Determine glyph category from opcode
        glyph_category = "neutral"
        if opcode and opcode != char:
            glyph_category = "mapped"

        # Map domain to a trigram for execution guidance
        domain_trigram_map = {
            ContextDomain.MATHEMATICS: Trigram.QIAN,  # Heaven — pure calculation
            ContextDomain.PHILOSOPHY:  Trigram.KUN,   # Earth — grounding
            ContextDomain.MILITARY:    Trigram.ZHEN,  # Thunder — sudden action
            ContextDomain.COMPUTING:   Trigram.LI,    # Fire — illumination
            ContextDomain.CONFUCIAN:   Trigram.XUN,   # Wind — gentle penetration
            ContextDomain.AGENT:       Trigram.KAN,   # Water — flowing communication
            ContextDomain.CONTROL:     Trigram.GEN,   # Mountain — stability
            ContextDomain.GENERAL:     Trigram.DUI,   # Lake — convergence
        }

        trigram = domain_trigram_map.get(domain, Trigram.QIAN)

        return WenTypeSignature(
            context_depth=stack.depth,
            context_domain=domain,
            glyph_category=glyph_category,
            iching_trigram=trigram,
            hexagram_address=trigram.value,
            confidence=0.85,
        )
