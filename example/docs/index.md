# MkDocs Flow Player

This page uses Mermaid topologies with execution scenarios.

## CDC replication

::: interactive-flow
title: CDC replication
diagram: flows/cdc.mmd
scenarios:
  - flows/cdc-normal.yaml
  - flows/cdc-target-offline.yaml
:::

## Typical CDC fan-out

::: interactive-flow
diagram: flows/cdc-use-case.mmd
scenario: flows/cdc-use-case.yaml
:::

## Outbox pattern

::: interactive-flow
title: Outbox pattern
diagram: flows/outbox.mmd
scenarios:
  - flows/outbox-dual-write-failure.yaml
  - flows/outbox-atomic-publish.yaml
  - flows/outbox-broker-retry.yaml
:::
