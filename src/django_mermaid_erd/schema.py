"""Framework-independent intermediate representation of a data model.

Renderers only ever see these dataclasses, so they never import Django and
can be unit-tested with hand-built schemas.
"""

from dataclasses import dataclass, field
from typing import List, Optional

RELATION_KINDS = ("fk", "o2o", "m2m", "inherit", "proxy", "generic")


@dataclass(frozen=True)
class Attribute:
    name: str  # Django field name
    type: str  # Mermaid type without parameters, e.g. "string", "decimal"
    django_type: str  # original field class name, e.g. "CharField"
    pk: bool = False
    fk: bool = False
    unique: bool = False  # unique=True or OneToOne -> UK
    nullable: bool = False
    comment: str = ""  # always-shown note, e.g. "GenericForeignKey"
    attname: str = ""  # column-ish name (``customer_id`` for FKs); defaults to name
    type_params: str = ""  # e.g. "100" or "10,2"; shown with ``types="full"``
    choices: bool = False
    verbose_name: str = ""  # only set when explicitly given in the model
    references: Optional[str] = None  # "app.Model" an FK points at

    @property
    def column(self) -> str:
        return self.attname or self.name

    @property
    def is_key(self) -> bool:
        return self.pk or self.fk or self.unique


@dataclass(frozen=True)
class Relation:
    source: str  # Entity.key of the side that owns the FK / M2M field
    target: str  # Entity.key of the side being pointed at
    kind: str  # one of RELATION_KINDS
    label: str  # field name; "inherits" / "proxy" for inheritance
    nullable: bool = False
    self_ref: bool = False
    through: Optional[str] = None  # "app.Model" of a custom through model left out of the diagram


@dataclass
class Entity:
    key: str  # identifier used in the diagram
    label: str  # "app_label.ModelName"
    app_label: str
    model_name: str
    attributes: List[Attribute] = field(default_factory=list)
    abstract: bool = False
    proxy: bool = False
    managed: bool = True
    parents: List[str] = field(default_factory=list)  # keys of MTI / proxy parents


@dataclass
class Schema:
    entities: List[Entity]
    relations: List[Relation]
    apps: List[str]

    def entity(self, key: str) -> Entity:
        for entity in self.entities:
            if entity.key == key:
                return entity
        raise KeyError(key)

    def normalized(self) -> "Schema":
        """Return a copy with entities, relations and apps in canonical order."""
        entities = sorted(self.entities, key=lambda e: (e.app_label, e.model_name, e.key))
        order = {e.key: i for i, e in enumerate(entities)}
        kinds = {k: i for i, k in enumerate(RELATION_KINDS)}
        relations = sorted(
            self.relations,
            key=lambda r: (
                order.get(r.source, len(order)),
                order.get(r.target, len(order)),
                kinds.get(r.kind, len(kinds)),
                r.label,
                r.source,
                r.target,
            ),
        )
        apps = sorted({e.app_label for e in entities})
        return Schema(entities=entities, relations=relations, apps=apps)
