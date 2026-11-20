# Integration audit (source inventory, not runtime verification)

This project does not yet execute every lab from the UI. Lab 7.1/7.2 retain existing routes. Labs 10.1, 10.2, 11.1 and 11.2 have local interactive endpoints and generated test data (not end-to-end verified); Lab 12.1/12.2 have read-only setup checks and manual environment instructions. Other labs still require integration and tests.

| Chapter | Lab 1 | Lab 2 | UI execution |
|---|---|---|---|
| 1 | Source missing | Source missing | Not wired |
| 2 | Source missing | Source missing | Not wired |
| 3 | Source missing | Source missing | Not wired |
| 4 | Source missing | Source missing | Not wired |
| 5 | Source missing | Source missing | Not wired |
| 6 | Source missing | Source missing | Not wired |
| 7 | Source present | Source present | Existing routes (not end-to-end verified) |
| 8 | Source present | Source present | Not wired |
| 9 | Source present | Source present | Not wired |
| 10 | Source present (original implementation) | Source present (original implementation) | Local runner; requires MongoDB/replica set; not E2E verified |
| 11 | Source present (original implementation) | Source present (original implementation) | Local runner; requires MongoDB/replica set; not E2E verified |
| 12 | Source present (original implementation) | Source present (original implementation) | Read-only checks; manual security setup required |
| 13 | Source present | Source present | Not wired |
| 14 | Source present | Source present | Not wired |
| 15 | Source present | Source present | Not wired |
| 16 | Source present | Source present | Not wired |
| 17 | Source present | Source present | Not wired |
| 18 | Source present | Source present | Not wired |

Labs 8.1/8.2 and 9.1/9.2 were incorrectly marked missing in the previous registry; their scripts are present.

Never execute shell, network-partition, backup/restore, Kubernetes or Terraform scripts automatically from an unauthenticated HTTP request. Use explicit sandbox configuration, allowlists, confirmation, and authorization.

Chapter 10–12 source files are **new original implementations** inspired by the assignment descriptions, not downloaded textbook scripts. They generate their own data. See `docs/CHAPTER_10_11_SETUP.md` and `docs/CHAPTER_12_SETUP.md`.
