# Security Policy

To report a vulnerability, open a GitHub issue marked [SECURITY].

## Notes

- Do not commit real `.env` files, API keys, tokens, passwords, or secrets.
- This project is a local CLI and does not expose HTTP endpoints, accept file uploads, run SQL, or perform web scraping.
- If you add server features later, add strict CORS, rate limiting, content-type checks, request size limits, and sanitized error responses before release.
