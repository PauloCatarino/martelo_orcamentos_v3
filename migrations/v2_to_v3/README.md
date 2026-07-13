# V2 to V3 migrations

Reserved for a future migration path from Martelo V2 to Martelo Orcamentos V3.

No V2 migration is implemented in this foundation stage.

## Read-only archive consultation

Historical budgets are not migrated into V3. The application now contains a
separate read-only adapter and the **Orçamentos > Arquivo V2** page. Configure
`V2_DB_*` (preferably a MySQL account granted only `SELECT`) as documented in
`.env.example`. The real V2 schema still requires discovery and validation in
an environment with credentials.
