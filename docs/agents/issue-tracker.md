# Issue tracker: Notion

Specs and tickets for this repo live in Notion under **MySpace > Learning > Tech learning > capstone**. Use the Notion MCP tools (`notion-search`, `notion-fetch`, `notion-create-pages`, `notion-update-page`, `notion-query-data-sources`, `notion-create-comment`).

## Locations

- **capstone root page**: https://app.notion.com/p/41663fb2df31819a985dd8a1f5b42b71
- **PRDs page**: https://app.notion.com/p/41663fb2df3181c3b3f0cb77dffaabe3. Create each spec / PRD as a child page of it (parent `page_id` `41663fb2df3181c3b3f0cb77dffaabe3`).
- **Tickets database**: https://app.notion.com/p/c7daca1021d044dd8c8c6a9012b5b4c0
  - Data source: `collection://1b646ee1-362d-47d1-90a5-8177d24ceee5`. Use this as the parent `data_source_id` when creating tickets.

## Tickets schema

| Property            | Type      | Notes                                                        |
| ------------------- | --------- | ------------------------------------------------------------ |
| Name                | title     | Ticket title                                                 |
| Ticket ID           | unique ID | Auto-assigned, prefix `CAPSTONE` (read-only). Creation order, not work order |
| Order               | number    | Work order: a topological sort of the `Blocked by:` lines, 1 = repo scaffolding. The default view sorts by it |
| Status              | status    | Triage roles + workflow, see below                           |
| Epic                | text      | The feature / PRD the ticket belongs to                      |
| Acceptance criteria | text      | What "done" means                                            |
| PR link             | URL       | Pull request that implements the ticket                      |

**Status values:**
- To do: `needs-triage` (default), `needs-info`, `ready-for-agent`, `ready-for-human`
- In progress: `In progress`
- Complete: `Done`, `wontfix`

The ticket's page body holds the full description. Discussion goes in Notion comments on the ticket page.

## When a skill says "publish to the issue tracker"

- **Spec / PRD**: create a child page under the PRDs page.
- **Ticket**: create a row in the Tickets data source. Fill in Name, Epic, Acceptance criteria and Order (after every ticket it is blocked by; renumber later tickets if needed), and put the full description in the page body. Status defaults to `needs-triage` unless the skill says otherwise.

## When a skill says "fetch the relevant ticket"

`notion-fetch` the ticket URL or ID the user gives. With only a `CAPSTONE-N` ID or a title, query the Tickets data source for it.

## Common operations

- **List tickets**: `notion-query-data-sources` on the Tickets data source, filtering on Status or Epic.
- **Change triage state**: update Status.
- **Comment**: `notion-create-comment` on the ticket page.
- **Close**: set Status to `Done` (or `wontfix`) and fill in PR link if there is one.

## Wayfinding operations

Used by `/wayfinder`.

- **Map**: a child page of the capstone root page holding the Notes / Decisions-so-far / Fog body.
- **Child ticket**: a Tickets row whose Epic names the effort, with the question in the body. Put a `Type:` line (`research`/`prototype`/`grilling`/`task`) at the top of the body.
- **Blocking**: a `Blocked by:` line at the top of the body linking the blocking tickets. A ticket is unblocked when every blocker is `Done`.
- **Frontier**: query open tickets for the effort that are unblocked and not `In progress`. The lowest Order wins.
- **Claim**: set Status to `In progress` before any work.
- **Resolve**: append the answer under an `## Answer` heading, set Status to `Done`, then append a context pointer (gist + link) to the map's Decisions-so-far.
