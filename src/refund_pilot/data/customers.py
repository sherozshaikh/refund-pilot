"""15 synthetic customer profiles"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class CustomerSeed:
    id: str
    name: str
    email: str
    phone: str
    tier: str


CUSTOMERS: list[CustomerSeed] = [
    CustomerSeed(
        "a1000000-0000-0000-0000-000000000001",
        "Alice Chen",
        "alice.chen@example.com",
        "+1-555-0101",
        "standard",
    ),
    CustomerSeed(
        "a1000000-0000-0000-0000-000000000002",
        "Bob Martinez",
        "bob.martinez@example.com",
        "+1-555-0102",
        "premium",
    ),
    CustomerSeed(
        "a1000000-0000-0000-0000-000000000003",
        "Carol White",
        "carol.white@example.com",
        "+1-555-0103",
        "standard",
    ),
    CustomerSeed(
        "a1000000-0000-0000-0000-000000000004",
        "David Kim",
        "david.kim@example.com",
        "+1-555-0104",
        "standard",
    ),
    CustomerSeed(
        "a1000000-0000-0000-0000-000000000005",
        "Emma Davis",
        "emma.davis@example.com",
        "+1-555-0105",
        "vip",
    ),
    CustomerSeed(
        "a1000000-0000-0000-0000-000000000006",
        "Frank Nguyen",
        "frank.nguyen@example.com",
        "+1-555-0106",
        "standard",
    ),
    CustomerSeed(
        "a1000000-0000-0000-0000-000000000007",
        "Grace Lee",
        "grace.lee@example.com",
        "+1-555-0107",
        "standard",
    ),
    CustomerSeed(
        "a1000000-0000-0000-0000-000000000008",
        "Henry Park",
        "henry.park@example.com",
        "+1-555-0108",
        "standard",
    ),
    CustomerSeed(
        "a1000000-0000-0000-0000-000000000009",
        "Isabella Roy",
        "isabella.roy@example.com",
        "+1-555-0109",
        "standard",
    ),
    CustomerSeed(
        "a1000000-0000-0000-0000-000000000010",
        "James Wilson",
        "james.wilson@example.com",
        "+1-555-0110",
        "premium",
    ),
    CustomerSeed(
        "a1000000-0000-0000-0000-000000000011",
        "Karen Scott",
        "karen.scott@example.com",
        "+1-555-0111",
        "standard",
    ),
    CustomerSeed(
        "a1000000-0000-0000-0000-000000000012",
        "Liam Brown",
        "liam.brown@example.com",
        "+1-555-0112",
        "standard",
    ),
    CustomerSeed(
        "a1000000-0000-0000-0000-000000000013",
        "Maya Patel",
        "maya.patel@example.com",
        "+1-555-0113",
        "standard",
    ),
    CustomerSeed(
        "a1000000-0000-0000-0000-000000000014",
        "Noah Clark",
        "noah.clark@example.com",
        "+1-555-0114",
        "standard",
    ),
    CustomerSeed(
        "a1000000-0000-0000-0000-000000000015",
        "Olivia Hall",
        "olivia.hall@example.com",
        "+1-555-0115",
        "standard",
    ),
]
