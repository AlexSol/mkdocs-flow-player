# Outbox

The outbox pattern stores an event record in the same database transaction as
the business change, then publishes it asynchronously with retry.
